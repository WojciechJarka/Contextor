# -*- coding: utf-8 -*-
"""
repo_guardian/core/name_collision.py

Moduł do wykrywania semantycznych kolizji nazw (np. gdy ta sama nazwa
jest używana przez różne typy artefaktów lub niezależne definicje).
"""

import ast
from collections import defaultdict
from pathlib import Path

def detect_name_collisions(modules):
    """
    Analizuje zindeksowane moduły, pobiera ścieżki do plików,
    parsuje ich zawartość i znajduje sytuacje, w których
    ta sama nazwa definiuje różne elementy w różnych plikach.
    """
    name_map = defaultdict(list)

    for module_path, module_info in modules.items():
        # Pobieramy fizyczną ścieżkę do pliku z obiektu Module
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

        # Zbieramy definicje bezpośrednio z AST tego pliku
        classes = []
        functions = []
        variables = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.append(target.id)

        for cls in classes:
            name_map[cls].append({"type": "class", "file": module_path})

        for func in functions:
            name_map[func].append({"type": "function", "file": module_path})

        for var in variables:
            name_map[var].append({"type": "variable", "file": module_path})

    # Filtrujemy tylko te nazwy, które występują w wielu plikach
    semantic_collisions = {}

    for name, occurrences in name_map.items():
        unique_files = {occ["file"] for occ in occurrences}
        
        # Jeśli nazwa występuje w więcej niż jednym pliku...
        if len(unique_files) > 1:
            types_found = {occ["type"] for occ in occurrences}
            
            if len(types_found) > 1 or len(occurrences) > len(unique_files):
                semantic_collisions[name] = occurrences

    return semantic_collisions
