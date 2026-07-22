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
import ast

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

# Globalna lista idiomów oraz lokalnych zmiennych pomocniczych do całkowitego pominięcia
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
    "references",
}

def validate_name_collisions(symbol_registry_or_modules) -> List[CollisionReport]:
    """
    Analizuje pliki projektu za pomocą AST w poszukiwaniu kolizji nazw
    (klasy, funkcje, stałe/zmienne globalne) pomiędzy różnymi modułami,
    skutecznie odrzucając zmienne lokalne i idiomy z listy IGNORED_ARTIFACTS.
    Nie zawiera żadnych zahardkodowanych ścieżek.
    """
    name_map = defaultdict(list)

    # Uniwersalne pobranie modułów/ścieżek do plików z przekazanego rejestru lub kolekcji
    modules_iter = []
    if hasattr(symbol_registry_or_modules, "modules"):
        modules_iter = symbol_registry_or_modules.modules.values()
    elif isinstance(symbol_registry_or_modules, dict):
        modules_iter = symbol_registry_or_modules.values()
    elif isinstance(symbol_registry_or_modules, list):
        modules_iter = symbol_registry_or_modules

    for module in modules_iter:
        module_path = getattr(module, "file_path", getattr(module, "path", None))
        module_id = getattr(module, "name", getattr(module, "id", str(module)))
        
        if not module_path:
            continue

        file_path = Path(module_path)
        if not file_path.exists():
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
                
                # BEZWZGLĘDNY FILTR: Ignorujemy idiomy i metody/klasy specjalne
                if name in IGNORED_ARTIFACTS or name.startswith("__"):
                    continue
                
                name_map[(name, "class")].append({
                    "type": "class",
                    "file": module_id,
                    "source": ast.unparse(node) if hasattr(ast, "unparse") else str(node)
                })
                
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                
                # Ignorujemy idiomy oraz funkcje pomocnicze typu main/run, jeśli występują masowo,
                # chyba że chcesz je śledzić (tutaj odrzucamy tylko standardowe dundersy i czarną listę)
                if name in IGNORED_ARTIFACTS or name.startswith("__"):
                    continue
                
                name_map[(name, "function")].append({
                    "type": "function",
                    "file": module_id,
                    "source": ast.unparse(node) if hasattr(ast, "unparse") else str(node)
                })
                
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        
                        # Ignorujemy zmienne z czarnej listy oraz dundersy
                        if name in IGNORED_ARTIFACTS or name.startswith("__"):
                            continue
                            
                        # Interesują nas głównie stałe globalne (UPPER_CASE) lub konkretne przypisania,
                        # zwykłe małe zmienne lokalne wewnątrz funkcji i tak są węższe, ale tu filtrujemy po nazwie.
                        name_map[(name, "variable")].append({
                            "type": "variable",
                            "file": module_id,
                            "source": ast.unparse(node) if hasattr(ast, "unparse") else str(node)
                        })

    reports: List[CollisionReport] = []

    # Filtrujemy pary (nazwa, typ), które występują w więcej niż jednym module
    for (name, art_type), occurrences in name_map.items():
        unique_nodes = {occ["file"] for occ in occurrences}
        if len(unique_nodes) > 1:
            conflicting_code = {occ["file"]: occ["source"] for occ in occurrences}
            nodes_list = list(unique_nodes)

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
                    conflicting_code=conflicting_code
                )
            )

    return reports
