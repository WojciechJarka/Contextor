import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

import orjson

class CacheManager:
    """Zarządza cache'owaniem wyników analizy pojedynczych plików."""
    
    def __init__(self, root_dir: str, cache_dir_name: str = ".contextor_cache"):
        self.root_dir = Path(root_dir)
        self.cache_dir = self.root_dir / cache_dir_name
        
        # Tworzymy katalog, jeśli nie istnieje
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
    def _compute_hash(self, file_path: str | Path) -> Optional[str]:
        """Zwraca hash zawartości pliku."""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return None
            
        hasher = hashlib.md5()
        try:
            with open(p, "rb") as f:
                # Wczytywanie po kawałku dla dużych plików
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def _get_cache_file_path(self, original_file_path: str | Path) -> Path:
        """Generuje unikalną nazwę pliku cache bazującą na względnej ścieżce."""
        rel_path = Path(original_file_path).relative_to(self.root_dir)
        # Zastępujemy separatory ścieżki znakami bezpiecznymi dla nazwy pliku
        safe_name = str(rel_path).replace("\\", "_").replace("/", "_") + ".json"
        return self.cache_dir / safe_name

    def get(self, file_path: str | Path) -> Optional[Dict[str, Any]]:
        """
        Pobiera zbuforowane dane, jeśli plik się nie zmienił.
        Zwraca dane jako słownik (dict) lub None, jeśli brak cache lub cache jest nieaktualny.
        """
        current_hash = self._compute_hash(file_path)
        if not current_hash:
            return None

        cache_file = self._get_cache_file_path(file_path)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "rb") as f:
                cached_data = orjson.loads(f.read())
                
            if cached_data.get("_file_hash") == current_hash:
                return cached_data.get("data")
            else:
                return None
        except Exception:
            return None

    def set(self, file_path: str | Path, data: Dict[str, Any]) -> None:
        """
        Zapisuje dane do cache'u. 'data' musi być serializowalne przez orjson.
        """
        current_hash = self._compute_hash(file_path)
        if not current_hash:
            return

        cache_file = self._get_cache_file_path(file_path)
        
        cache_wrapper = {
            "_file_hash": current_hash,
            "data": data
        }
        
        try:
            with open(cache_file, "wb") as f:
                # orjson.dumps zwraca od razu bajty
                f.write(orjson.dumps(cache_wrapper))
        except Exception:
            pass

    def clear(self) -> None:
        """Czyści cały katalog cache'u."""
        if self.cache_dir.exists():
            for p in self.cache_dir.iterdir():
                if p.is_file():
                    try:
                        p.unlink()
                    except Exception:
                        pass
