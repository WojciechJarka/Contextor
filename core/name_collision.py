# -*- coding: utf-8 -*-
"""
repo_guardian/core/name_collision.py
"""

from collections import defaultdict
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum

class CollisionKind(Enum):
    IMPORT_IMPORT = "import_import"
    SEMANTIC_COLLISION = "semantic_collision"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class CollisionReport:
    name: str
    kind: CollisionKind
    symbols: List[str]
    risk_score: int
    risk_level: RiskLevel
    explanation: str
    nodes: List[str] = field(default_factory=list)
    artifact_type: str = "unknown"
    conflicting_code: Dict[str, str] = field(default_factory=dict)

# Ignorowane idiomy Pythona oraz nazwy lokalne, które naturalnie powtarzają się w plikach
IGNORED_ARTIFACTS = {
    "__init__",
    "__all__",
    "path",
    "modules",
    "errors",
    "metrics",
    "cycles",
    "debt",
    "repo_name",
}

def validate_name_collisions(symbol_registry_or_modules) -> List[CollisionReport]:
    """
    Dynamicznie analizuje rejestr symboli lub moduły w poszukiwaniu rzeczywistych,
    globalnych kolizji semantycznych (np. duplikacja nazw klas/funkcji w przestrzeni publicznej),
    pomijając lokalne zmienne oraz standardowe idiomy Pythona.
    Nie zawiera żadnych zahardkodowanych ścieżek ani nazw modułów.
    """
    reports: List[CollisionReport] = []
    
    # Słownik do grupowania definicji po nazwie symbolu i typie artefaktu
    # Klucz: (artifact_type, name) -> { module_id: code_snippet }
    definitions_map = defaultdict(dict)

    # Uniwersalne przejście po strukturze projektu bez odwoływania się do konkretnych nazw
    # Obsługujemy zarówno strukturę zindeksowaną, jak i surowe kolekcje modułów
    modules_iter = []
    if hasattr(symbol_registry_or_modules, "modules"):
        modules_iter = symbol_registry_or_modules.modules.values()
    elif isinstance(symbol_registry_or_modules, dict):
        modules_iter = symbol_registry_or_modules.values()
    elif isinstance(symbol_registry_or_modules, list):
        modules_iter = symbol_registry_or_modules

    for module in modules_iter:
        module_id = getattr(module, "name", getattr(module, "id", str(module)))
        
        # Pobieranie artefaktów/symboli zdefiniowanych w module (funkcje, klasy, zmienne globalne)
        artifacts = []
        if hasattr(module, "artifacts"):
            artifacts = module.artifacts
        elif hasattr(module, "symbols"):
            artifacts = module.symbols
        elif isinstance(module, dict) and "artifacts" in module:
            artifacts = module["artifacts"]

        for art in artifacts:
            name = getattr(art, "name", art.get("name") if isinstance(art, dict) else None)
            art_type = getattr(art, "kind", getattr(art, "type", "variable"))
            if isinstance(art_type, Enum):
                art_type = art_type.value
                
            code = getattr(art, "code", getattr(art, "source", ""))

            if not name:
                continue

            # Pomijanie idiomów Pythona oraz zmiennych lokalnych/tymczasowych
            if name in IGNORED_ARTIFACTS:
                continue

            # Interesują nas głównie konflikty globalne struktur (funkcje, klasy, stałe)
            # Zmienne lokalne/jednoliniowce wewnątrz funkcji nie powinny być tu raportowane
            if art_type in ("function", "class", "constant") or name.isupper():
                definitions_map[(str(art_type), name)][str(module_id)] = str(code)

    # Generowanie raportów kolizji na podstawie zebranych danych
    for (art_type, name), nodes_dict in definitions_map.items():
        # Kolizja występuje, gdy ten sam symbol (np. klasa lub funkcja) jest zdefiniowany
        # w więcej niż jednym niezależnym module/pliku
        if len(nodes_dict) > 1:
            nodes_list = list(nodes_dict.keys())
            
            reports.append(
                CollisionReport(
                    name=name,
                    kind=CollisionKind.SEMANTIC_COLLISION,
                    symbols=nodes_list,
                    risk_score=75,
                    risk_level=RiskLevel.MEDIUM,
                    explanation=f"Semantic name collision for {art_type} '{name}' across multiple modules.",
                    nodes=nodes_list,
                    artifact_type=art_type,
                    conflicting_code=nodes_dict
                )
            )

    return reports not file_path.exists():
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            continue

        # Przechodzimy przez drzewo AST w poszukiwaniu klas, funkcji i zmiennych
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                name = node.name
                # Ignorujemy metody/klasy specjalne
                if name.startswith("__") and name.endswith("__"):
                    continue
                
                name_map[(name, "class")].append({
                    "type": "class",
                    "file": module_path
                })
                
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                # Ignorujemy metody specjalne (np. __init__, __str__ itp.)
                if name.startswith("__") and name.endswith("__"):
                    continue
                
                name_map[(name, "function")].append({
                    "type": "function",
                    "file": module_path
                })
                
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if name.startswith("__") and name.endswith("__"):
                            continue
                            
                        name_map[(name, "variable")].append({
                            "type": "variable",
                            "file": module_path
                        })

    collisions = {}
    
    # Filtrujemy pary (nazwa, typ), które występują w więcej niż jednym pliku
    for (name, obj_type), occurrences in name_map.items():
        unique_files = {occ["file"] for occ in occurrences}
        if len(unique_files) > 1:
            # Jeśli nazwa nie istnieje jeszcze w słowniku kolizji, inicjalizujemy listę
            if name not in collisions:
                collisions[name] = []
            collisions[name].extend(occurrences)

    return collisions
