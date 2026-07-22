# -*- coding: utf-8 -*-
"""
repo_guardian/core/name_collision.py

Moduł do wykrywania kolizji nazw (zduplikowanych nazw klas, funkcji i zmiennych)
w różnych plikach projektu.
"""

from collections import defaultdict

def detect_name_collisions(modules):
    """
    Analizuje zindeksowane moduły i znajduje symbole (klasy, funkcje, zmienne),
    które mają identyczne nazwy w różnych plikach.
    """
    name_map = defaultdict(list)

    for module_path, module_info in modules.items():
        # Pobieramy różne typy symboli z indeksu (bezpiecznie, jeśli klucz nie istnieje)
        classes = module_info.get("classes", [])
        functions = module_info.get("functions", [])
        variables = module_info.get("variables", []) # Obsługa zmiennych globalnych

        for cls in classes:
            name_map[cls].append({"type": "class", "file": module_path})

        for func in functions:
            name_map[func].append({"type": "function", "file": module_path})

        for var in variables:
            name_map[var].append({"type": "variable", "file": module_path})

    # Filtrujemy tylko te nazwy, które występują w więcej niż jednym pliku
    collisions = {}
    for name, occurrences in name_map.items():
        unique_files = {occ["file"] for occ in occurrences}
        if len(unique_files) > 1:
            collisions[name] = occurrences

    return collisions
