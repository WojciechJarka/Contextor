"""
contextor/core/analysis/cache_manager.py

PER-FILE ANALYSIS CACHE

Caches deterministic per-file extraction results keyed by file content.

Guarantees:

- nothing is ever written inside the analyzed repository
- cache entries cannot collide between different source files
- a stale entry is never returned (content hash is verified on read)
"""

import hashlib
from pathlib import Path
from typing import Any

import orjson

from contextor.core.paths import repo_cache_dir

# Content hashing only - not a security boundary.
# blake2b is faster than md5 and available under FIPS-restricted builds,
# where md5 raises ValueError.
_HASH = hashlib.blake2b

_HASH_DIGEST_SIZE = 16

_CHUNK_SIZE = 65536


class CacheManager:
    """
    Zarządza cache'owaniem wyników analizy pojedynczych plików.
    """

    def __init__(self, root_dir: str, cache_dir: str | Path | None = None):
        self.root_dir = Path(root_dir).resolve()

        # Cache lives in the user cache directory, namespaced by the
        # absolute path of the analyzed repository. The analyzed project
        # is never touched.
        self.cache_dir = Path(cache_dir) if cache_dir is not None else repo_cache_dir(self.root_dir)

        self._dir_ready = False

        # Avoids re-reading a file to hash it twice (get() then set()).
        self._hash_cache: dict[str, str | None] = {}

    # ------------------------------------------------------
    # INTERNALS
    # ------------------------------------------------------

    def _ensure_dir(self) -> None:
        """
        Creates the cache directory on first write only.
        """

        if self._dir_ready:
            return

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._dir_ready = True

    def _compute_hash(self, file_path: str | Path) -> str | None:
        """
        Zwraca hash zawartości pliku.
        """

        key = str(file_path)

        if key in self._hash_cache:
            return self._hash_cache[key]

        digest: str | None = None

        path = Path(file_path)

        if path.is_file():
            hasher = _HASH(digest_size=_HASH_DIGEST_SIZE)

            try:
                with open(path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
                        hasher.update(chunk)

                digest = hasher.hexdigest()

            except OSError:
                digest = None

        self._hash_cache[key] = digest

        return digest

    def _get_cache_file_path(self, original_file_path: str | Path) -> Path:
        """
        Generuje unikalną nazwę pliku cache bazującą na względnej ścieżce.

        The relative path is hashed rather than flattened: replacing path
        separators would map 'core/graph.py' and 'core_graph.py' onto the
        same cache entry.
        """

        resolved = Path(original_file_path).resolve()

        try:
            rel_path = resolved.relative_to(self.root_dir).as_posix()
        except ValueError:
            rel_path = resolved.as_posix()

        digest = _HASH(
            rel_path.encode("utf-8"),
            digest_size=_HASH_DIGEST_SIZE,
        ).hexdigest()

        return self.cache_dir / f"{digest}.json"

    # ------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------

    def get(self, file_path: str | Path) -> dict[str, Any] | None:
        """
        Pobiera zbuforowane dane, jeśli plik się nie zmienił.

        Zwraca dane jako słownik (dict) lub None, jeśli brak cache
        lub cache jest nieaktualny.
        """

        current_hash = self._compute_hash(file_path)

        if not current_hash:
            return None

        cache_file = self._get_cache_file_path(file_path)

        try:
            with open(cache_file, "rb") as handle:
                cached_data = orjson.loads(handle.read())

        except (OSError, orjson.JSONDecodeError):
            return None

        if cached_data.get("_file_hash") != current_hash:
            return None

        # Guards against a hash collision on the cache file name.
        if cached_data.get("_source") != str(Path(file_path).resolve()):
            return None

        return cached_data.get("data")

    def set(self, file_path: str | Path, data: dict[str, Any]) -> None:
        """
        Zapisuje dane do cache'u. 'data' musi być serializowalne przez orjson.
        """

        current_hash = self._compute_hash(file_path)

        if not current_hash:
            return

        cache_wrapper = {
            "_file_hash": current_hash,
            "_source": str(Path(file_path).resolve()),
            "data": data,
        }

        cache_file = self._get_cache_file_path(file_path)

        try:
            self._ensure_dir()

            # Atomic publish: a crash mid-write must not leave a
            # truncated entry that later reads would choke on.
            temp_file = cache_file.with_suffix(".json.tmp")

            with open(temp_file, "wb") as handle:
                handle.write(orjson.dumps(cache_wrapper))

            temp_file.replace(cache_file)

        except OSError:
            pass

    def clear(self) -> None:
        """
        Czyści cały katalog cache'u.
        """

        if not self.cache_dir.exists():
            return

        for entry in self.cache_dir.iterdir():
            if entry.is_file():
                try:
                    entry.unlink()
                except OSError:
                    pass
