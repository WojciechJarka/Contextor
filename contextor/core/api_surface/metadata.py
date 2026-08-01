"""
contextor/core/api_surface/metadata.py

Metadata and statistics collected based on AST.
"""

from .engine import extract_api_surface


def extract_api_metadata(module) -> dict:
    """
    Module API statistics.

    Purpose:
    - LLM context
    - refactor analysis
    - API pressure models
    """
    api = extract_api_surface(module)

    functions = api.get("functions", {})
    methods = api.get("methods", {})
    classes = api.get("classes", {})

    all_symbols = list(functions.values()) + list(methods.values()) + list(classes.values())

    public_count = sum(1 for item in all_symbols if item.get("visibility") == "public")
    private_count = sum(1 for item in all_symbols if item.get("visibility") == "private")
    classmethod_count = sum(1 for item in methods.values() if item.get("classmethod"))
    staticmethod_count = sum(1 for item in methods.values() if item.get("staticmethod"))

    return {
        "total_symbols": len(all_symbols),
        "functions": len(functions),
        "methods": len(methods),
        "classes": len(classes),
        "public_symbols": public_count,
        "private_symbols": private_count,
        "classmethods": classmethod_count,
        "staticmethods": staticmethod_count,
    }


def extract_flat_api_surface(module) -> dict:
    """
    Compact API view for LLM reports.

    Combines: functions, methods, classes using {**a, **b} idiom.
    """
    raw = extract_api_surface(module)
    return {**raw.get("functions", {}), **raw.get("methods", {}), **raw.get("classes", {})}
