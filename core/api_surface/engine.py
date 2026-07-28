# -*- coding: utf-8 -*-

"""
repo_guardian/core/api_surface/engine.py

Główny punkt wejścia wyciągania publicznego API z węzła drzewa (Module).
Wykorzystuje pre-kalkulowany cache (ast_tree) by zaoszczędzić I/O.
"""

import ast
from pathlib import Path
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
            tree = ast.parse(Path(path_obj).read_text(encoding="utf-8"))
        except Exception:
            return {"functions": {}, "methods": {}, "classes": {}}

    visitor = APISurfaceVisitor()
    visitor.visit(tree)

    return {
        "functions": visitor.functions,
        "methods": visitor.methods,
        "classes": visitor.classes,
    }
