# -*- coding: utf-8 -*-
"""
repo_guardian/core/name_collision.py
"""

import ast
from collections import defaultdict
from pathlib import Path


def detect_name_collisions(modules: dict) -> dict:
    """
    Wykrywa kolizje nazw w zindeksowanych modułach na podstawie analizy AST.
    """
    name_map = defaultdict(list)

    for module_path, module_info in modules.items():
        # Pobieramy fizyczną ścieżkę do pliku
        file_path_str = getattr(module_info, "absolute_path", None) or getattr(module_info, "path", None)
        if not file_path_str:
            continue

        file_path = Path(file_path_str)
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
                name_map[node.name].append({
                    "type": "class",
                    "file": module_path
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name_map[node.name].append({
                    "type": "function",
                    "file": module_path
                })
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_map[target.id].append({
                            "type": "variable",
                            "file": module_path
                        })

    collisions = {}
    
    # Filtrujemy nazwy, które występują w więcej niż jednym pliku
    for name, occurrences in name_map.items():
        unique_files = {occ["file"] for occ in occurrences}
        if len(unique_files) > 1:
            collisions[name] = occurrences

    return collisions
