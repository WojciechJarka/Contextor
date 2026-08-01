"""
contextor/core/api_surface/engine.py

Główny punkt wejścia wyciągania publicznego API z węzła drzewa (Module).
Wykorzystuje pre-kalkulowany cache (ast_tree) by zaoszczędzić I/O.
"""

from pathlib import Path

from contextor.core.source import SourceError, parse_source

from .visitor import APISurfaceVisitor


def extract_api_surface(module) -> dict:
    tree = getattr(module, "ast_tree", None)

    if tree is None:
        # Fallback for manual or raw cases where ast_tree is missing.
        path_obj = getattr(module, "path", None)
        if not path_obj and isinstance(module, (str, Path)):
            path_obj = module

        if not path_obj:
            return {"functions": {}, "methods": {}, "classes": {}}

        try:
            tree = parse_source(path_obj)
        except SourceError:
            return {"functions": {}, "methods": {}, "classes": {}}

    visitor = APISurfaceVisitor()
    visitor.visit(tree)

    return {
        "functions": visitor.functions,
        "methods": visitor.methods,
        "classes": visitor.classes,
    }
