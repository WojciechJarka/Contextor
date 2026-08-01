"""
contextor/core/reference/resolution.py

Heuristics for resolving and identifying AST symbols
for the reference building engine.
"""

import ast

IGNORED_AMBIGUOUS_METHODS = {
    "visit",
    "get",
    "add",
    "update",
    "append",
    "extend",
    "insert",
    "pop",
    "remove",
    "clear",
    "copy",
    "items",
    "keys",
    "values",
    "visit_FunctionDef",
    "visit_ClassDef",
    "visit_AsyncFunctionDef",
    "visit_Call",
    "visit_Import",
    "visit_Assign",
    "visit_Name",
    "visit_Attribute",
}


def _attribute_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _attribute_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr

    return None


def _resolve_alias(name, aliases):
    if not name:
        return None
    return aliases.get(name, name)


def _match_symbol(value, symbols):
    if not value:
        return None

    if value in symbols:
        return value

    short = value.split(".")[-1]
    candidates = [symbol for symbol in symbols if symbol.split(".")[-1] == short]

    if len(candidates) == 1:
        return candidates[0]

    return None


def _classify_match(name, resolved, target_symbols, aliases):
    if not resolved:
        return None, None

    if resolved in target_symbols:
        return "confirmed", resolved

    if name in aliases:
        return None, None

    match = _match_symbol(resolved, target_symbols)
    if match:
        short = match.split(".")[-1]

        if short in IGNORED_AMBIGUOUS_METHODS:
            return None, None

        if short.startswith("__") and short.endswith("__"):
            return None, None

        return "ambiguous", match

    return None, None
