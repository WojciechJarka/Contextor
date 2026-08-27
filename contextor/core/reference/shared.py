"""
contextor/core/reference/shared.py

Pure shared lower-level reference helpers, normalization utilities, and
re-export analysis used by both reference.index and reference.engine.

Dependency Invariant:
This module must NOT depend on reference.engine or reference.index.
"""

from __future__ import annotations

import ast
from typing import Any

from .resolution import _absolute_import_module

MAX_USAGE_DETAILS = 15

_REEXPORT_CACHE: dict = {}


def reset_reexport_cache() -> None:
    """Clear cached re-export maps."""
    _REEXPORT_CACHE.clear()


def _explicit_all(tree: Any) -> set[str] | None:
    """Extract explicit __all__ string sequence if defined in AST root."""
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            continue
        if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
            return {
                item.value
                for item in node.value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
        return set()
    return None


def _export_module_name(module_id: str) -> str:
    """Normalize package __init__ module ID to parent package identity."""
    return module_id.removesuffix(".__init__")


def _build_reexport_map(modules: dict) -> dict[str, str]:
    """Build cycle-safe transitive identities for top-level ImportFrom re-exports."""
    cache_key = (id(modules), len(modules))
    cached = _REEXPORT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    raw: dict[str, str] = {}
    module_exports: dict[str, dict[str, str]] = {}
    star_imports: list[tuple[str, str, set[str] | None]] = []

    for module_id, module in modules.items():
        tree = getattr(module, "ast_tree", None)
        if tree is None:
            continue
        exporter = _export_module_name(module_id)
        allowed = _explicit_all(tree)
        bindings: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                source = _absolute_import_module(
                    module_id, node.module, node.level or 0
                )
                for item in node.names:
                    if item.name == "*":
                        star_imports.append((exporter, source, allowed))
                        continue
                    bindings[item.asname or item.name] = f"{source}.{item.name}"
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bindings[node.name] = f"{exporter}.{node.name}"
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value
                for target in targets:
                    if not isinstance(target, ast.Name) or target.id == "__all__":
                        continue
                    if isinstance(value, ast.Name) and value.id in bindings:
                        bindings[target.id] = bindings[value.id]
                    else:
                        bindings[target.id] = f"{exporter}.{target.id}"

        visible_bindings = {}
        for local, target in bindings.items():
            if allowed is not None and local not in allowed:
                continue
            if allowed is None and local.startswith("_"):
                continue
            visible_bindings[local] = target
            key = f"{exporter}.{local}"
            if key != target:
                raw[key] = target
        module_exports[exporter] = visible_bindings

    changed = True
    while changed:
        changed = False
        for exporter, source, allowed in star_imports:
            for local, target in list(module_exports.get(source, {}).items()):
                if allowed is not None and local not in allowed:
                    continue
                if allowed is None and local.startswith("_"):
                    continue
                key = f"{exporter}.{local}"
                if key not in raw:
                    raw[key] = target
                    module_exports.setdefault(exporter, {})[local] = target
                    changed = True

    resolved = {}
    for key, initial in raw.items():
        target = initial
        visited = {key}
        while target in raw and target not in visited:
            visited.add(target)
            target = raw[target]
        if target not in visited:
            resolved[key] = target

    _REEXPORT_CACHE[cache_key] = resolved
    return resolved


def _empty_reference() -> dict[str, list]:
    """
    Creates an empty reference record.

    Each usage category is represented explicitly so downstream
    consumers do not need to infer semantics from missing keys.
    """
    return {
        "called_by": [],
        "called_by_detail": [],
        "callback_called": [],
        "callback_called_detail": [],
        "called_by_ambiguous": [],
        "called_by_ambiguous_detail": [],
        "event_bound_by": [],
        "event_bound_by_detail": [],
        "imported_from": [],
        "inherited_by": [],
        "inherited_by_detail": [],
        "qualified_refs": [],
        "qualified_refs_detail": [],
        "runtime_calls": [],
    }


def _normalize_references(references: dict[str, Any]) -> dict[str, Any]:
    """
    Deduplicates scalar consumer lists and caps detail lists.

    Detail records remain dictionaries and therefore are not
    converted through set().
    """
    for data in references.values():
        for key, values in data.items():
            if not isinstance(values, list):
                continue

            if key.endswith("_detail"):
                data[key] = values[:MAX_USAGE_DETAILS]
                continue

            if all(isinstance(value, str) for value in values):
                data[key] = sorted(set(values))

    return references
