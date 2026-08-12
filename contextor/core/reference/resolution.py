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
    """
    Resolve an identifier or an attribute rooted at an imported alias.

    Examples:

        aliases = {
            "SymbolFacts":
                "contextor.core.symbol_engine.domain.SymbolFacts"
        }

        _resolve_alias("SymbolFacts", aliases)
        -> "contextor.core.symbol_engine.domain.SymbolFacts"

        _resolve_alias("SymbolFacts.all_symbols", aliases)
        -> "contextor.core.symbol_engine.domain.SymbolFacts.all_symbols"

    A direct alias match still takes precedence.  If no alias applies,
    the original name is returned unchanged.
    """
    if not name:
        return None

    direct = aliases.get(name)
    if direct is not None:
        return direct

    parts = name.split(".")

    # Find the longest alias prefix.  This matters when aliases contain
    # nested names or when a short imported name is used as the root of
    # an attribute chain.
    for index in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:index])
        alias = aliases.get(prefix)

        if alias is not None:
            suffix = ".".join(parts[index:])
            return f"{alias}.{suffix}" if suffix else alias

    return name


def _absolute_import_module(current_module, imported_module, level=0):
    """Resolve an AST ImportFrom module against its importing module."""

    if not level:
        return imported_module or ""
    parts = str(current_module or "").split(".")
    if parts[-1:] == ["__init__"]:
        parts.pop()
    elif parts:
        parts.pop()
    climb = max(0, int(level) - 1)
    if climb:
        parts = parts[:-climb] if climb <= len(parts) else []
    if imported_module:
        parts.extend(str(imported_module).split("."))
    return ".".join(part for part in parts if part)


def _resolve_reexport(name, reexports):
    """Resolve a full name through the longest known re-export prefix."""

    if not name or not reexports:
        return name
    direct = reexports.get(name)
    if direct is not None:
        return direct
    parts = name.split(".")
    for index in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:index])
        target = reexports.get(prefix)
        if target is not None:
            suffix = ".".join(parts[index:])
            return f"{target}.{suffix}" if suffix else target
    return name


def _match_symbol(value, symbols):
    if not value:
        return None

    if value in symbols:
        return value

    short = value.split(".")[-1]
    candidates = [
        symbol
        for symbol in symbols
        if symbol.split(".")[-1] == short
    ]

    if len(candidates) == 1:
        return candidates[0]

    return None


def _classify_match(name, resolved, target_symbols, aliases):
    if not resolved:
        return None, None

    # Fully resolved names are authoritative.
    if resolved in target_symbols:
        return "confirmed", resolved

    # If the original expression is rooted in an alias but the alias
    # could not be resolved to a target, do not downgrade it to a
    # short-name ambiguous match.
    if name:
        parts = name.split(".")

        for index in range(len(parts), 0, -1):
            prefix = ".".join(parts[:index])
            if prefix in aliases:
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
