# -*- coding: utf-8 -*-
"""
repo_guardian/core/name_collision.py

Wersja tymczasowa (zahardkodowana) do testu poprawności całego systemu.
"""

def detect_name_collisions(modules):
    """
    Zwraca zahardkodowaną kolizję dla test_module_a oraz test_module_b,
    aby zweryfikować czy plik JSON i interfejs poprawnie ją odbierają.
    """
    # Sprawdzamy czy nasze pliki testowe w ogóle są w indeksie
    keys = list(modules.keys())
    print("DEBUG TEST KEYS:", keys)

    # Zahardkodowana kolizja dla GLOBAL_CONFIG, process_data i DataProcessor
    return {
        "GLOBAL_CONFIG": [
            {"type": "variable", "file": "test_module_a"},
            {"type": "variable", "file": "test_module_b"}
        ],
        "process_data": [
            {"type": "function", "file": "test_module_a"},
            {"type": "function", "file": "test_module_b"}
        ],
        "DataProcessor": [
            {"type": "class", "file": "test_module_a"},
            {"type": "class", "file": "test_module_b"}
        ]
    }
