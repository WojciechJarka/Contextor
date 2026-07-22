# -*- coding: utf-8 -*-

GLOBAL_CONFIG = {"version": "1.0", "mode": "alpha"}

def process_data(data):
    """Przetwarza dane w trybie A."""
    return [x * 2 for x in data]

class DataProcessor:
    def __init__(self):
        self.type = "TypeA"

    def run(self, value):
        return value + 10
