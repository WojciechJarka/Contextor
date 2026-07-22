# -*- coding: utf-8 -*-

# Kolizja: ta sama zmienna globalna zdefiniowana inaczej w tej samej przestrzeni nazw
GLOBAL_CONFIG = {"version": "2.0", "mode": "beta"}

def process_data(data):
    """Kolizja: duplikat nazwy funkcji w tym samym module/kontekście."""
    return [x * 3 for x in data]

class DataProcessor:
    def __init__(self):
        # Kolizja: konflikt nazwy klasy i niezgodny typ w tej samej ścieżce
        self.type = "TypeB"

    def run(self, value):
        return value * 20
