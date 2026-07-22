# -*- coding: utf-8 -*-
"""
repo_guardian/core/name_collision.py

Moduł do wykrywania semantycznych kolizji nazw (np. gdy ta sama nazwa
jest używana przez różne typy artefaktów lub niezależne definicje).
"""

from collections import defaultdict

def detect_name_collisions(modules):
    """
    Analizuje zindeksowane moduły i znajduje sytuacje, w których
    ta sama nazwa definiuje różne semantycznie elementy w różnych plikach.
    """
    name_map = defaultdict(list)

    for module_path, module_info in modules.items():
        classes = module_info.get("classes", [])
        functions = module_info.get("functions", [])
        variables = module_info.get("variables", [])

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
            # Sprawdzamy, czy mamy do czynienia z różnymi typami (np. klasa vs funkcja)
            # lub różnymi niezależnymi definicjami semantycznymi
            types_found = {occ["type"] for occ in occurrences}
            
            # Kolizja semantyczna występuje, gdy:
            # 1. Ta sama nazwa to raz klasa, a raz funkcja/zmienna.
            # 2. Lub występuje w wielu miejscach, co w zależności od projektu może wymagać uwagi.
            if len(types_found) > 1 or len(occurrences) > len(unique_files):
                semantic_collisions[name] = occurrences

    return semantic_collisions
