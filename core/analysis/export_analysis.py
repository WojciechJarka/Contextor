# -*- coding: utf-8 -*-
"""
repo_guardian/core/export_analysis.py

Module exports extraction (Fast Path - optimized Batch 4).
Extracts API names exposed by the given source code.
"""

import ast

def _is_public(name: str) -> bool:
    return bool(name) and not name.startswith("_")

def extract_exports(tree: ast.Module) -> dict:
    """Extracts module exports ignoring `__all__` logic."""
    funcs, classes, consts, aliases = set(), set(), set(), []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
            funcs.add(node.name)
        elif isinstance(node, ast.ClassDef) and _is_public(node.name):
            classes.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and _is_public(t.id):
                    consts.add(t.id)
                    if isinstance(node.value, ast.Name) and node.value.id != t.id:
                        aliases.append({"name": t.id, "target": node.value.id})

    return {
        "symbols": sorted(funcs | classes | consts),
        "functions": sorted(funcs),
        "classes": sorted(classes),
        "constants": sorted(consts),
        "aliases": sorted(aliases, key=lambda x: (x["name"], x["target"])),
    }

def find_unused_public_api(symbols: list, usage: dict = None, exports: dict = None, local_calls: set = None, references: dict = None) -> list:
    """Finds potentially unused symbols based on set operations while preserving top performance."""
    # Fast fusion of declared local and foreign usages
    used_elements = set((usage or {}).keys()) | set(local_calls or [])
    
    # Fast fusion of detected exports
    exported_elements = set((exports or {}).get("symbols", [])) | {
        alias["name"] for alias in (exports or {}).get("aliases", []) if alias.get("name")
    }

    references = references or {}
    candidates = []

    for symbol in symbols:
        if symbol in used_elements or symbol in exported_elements:
            continue
        
        # Filter based on semantic references if present
        ref = references.get(symbol, {})
        if ref.get("event_bound_by") or ref.get("imported_from"):
            continue
            
        candidates.append(symbol)

    return sorted(set(candidates))


def summarize_exports(exports: dict) -> dict:
    """Creates a simple, compressed dictionary summarizing the size of the exported API."""
    if not exports:
        return {"symbol_count": 0, "public_api": False}

    return {
        "symbol_count": len(exports.get("symbols", [])),
        "function_count": len(exports.get("functions", [])),
        "class_count": len(exports.get("classes", [])),
        "constant_count": len(exports.get("constants", [])),
        "alias_count": len(exports.get("aliases", [])),
        "public_api": bool(exports.get("symbols")),
    }

find_unused_symbols = find_unused_public_api
find_unreferenced_symbols = find_unused_public_api
