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


def _export_module_name(module_id: str) -> str:
    """Normalize package __init__ module ID to parent package identity."""
    return module_id.removesuffix(".__init__")


def _extract_reexport_facts(
    module_id: str,
    tree: Any,
) -> dict[str, Any]:
    """
    Extract source-local inputs required for global re-export assembly.

    Top-level __all__ follows Python execution order: when assigned
    repeatedly, the last supported assignment is authoritative.
    """
    exporter = _export_module_name(module_id)
    explicit_all: list[str] | None = None
    bindings: dict[str, str] = {}
    star_sources: list[str] = []

    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id == "__all__"
            for target in node.targets
        ):
            if isinstance(
                node.value,
                (
                    ast.List,
                    ast.Tuple,
                    ast.Set,
                ),
            ):
                explicit_all = [
                    item.value
                    for item in node.value.elts
                    if isinstance(item, ast.Constant)
                    and isinstance(item.value, str)
                ]
            else:
                explicit_all = []

        if isinstance(node, ast.ImportFrom):
            source = _absolute_import_module(
                module_id,
                node.module,
                node.level or 0,
            )

            for item in node.names:
                if item.name == "*":
                    star_sources.append(source)
                else:
                    bindings[
                        item.asname or item.name
                    ] = f"{source}.{item.name}"

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            bindings[node.name] = (
                f"{exporter}.{node.name}"
            )

        elif isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
            ),
        ):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
            )
            value = node.value

            for target in targets:
                if (
                    not isinstance(target, ast.Name)
                    or target.id == "__all__"
                ):
                    continue

                if (
                    isinstance(value, ast.Name)
                    and value.id in bindings
                ):
                    bindings[target.id] = bindings[
                        value.id
                    ]
                else:
                    bindings[target.id] = (
                        f"{exporter}.{target.id}"
                    )

    return {
        "exporter": exporter,
        "explicit_all": explicit_all,
        "bindings": bindings,
        "star_sources": star_sources,
    }


def _assemble_reexport_map(
    reexport_facts_by_module: dict[str, dict[str, Any]],
) -> dict[str, str]:
    """
    Assemble cycle-safe transitive re-export identities from complete
    source-local re-export facts.

    Performs no source or filesystem I/O.
    """
    raw: dict[str, str] = {}
    module_exports: dict[str, dict[str, str]] = {}
    star_imports: list[
        tuple[str, str, set[str] | None]
    ] = []

    for reexport in reexport_facts_by_module.values():
        exporter = reexport["exporter"]
        explicit_all = reexport["explicit_all"]
        allowed = (
            None
            if explicit_all is None
            else set(explicit_all)
        )

        visible_bindings: dict[str, str] = {}

        for local, target in reexport[
            "bindings"
        ].items():
            if (
                allowed is not None
                and local not in allowed
            ):
                continue

            if (
                allowed is None
                and local.startswith("_")
            ):
                continue

            visible_bindings[local] = target

            key = f"{exporter}.{local}"

            if key != target:
                raw[key] = target

        module_exports[exporter] = (
            visible_bindings
        )

        for source in reexport[
            "star_sources"
        ]:
            star_imports.append(
                (
                    exporter,
                    source,
                    allowed,
                )
            )

    changed = True

    while changed:
        changed = False

        for exporter, source, allowed in star_imports:
            for local, target in list(
                module_exports.get(
                    source,
                    {},
                ).items()
            ):
                if (
                    allowed is not None
                    and local not in allowed
                ):
                    continue

                if (
                    allowed is None
                    and local.startswith("_")
                ):
                    continue

                key = f"{exporter}.{local}"

                if key not in raw:
                    raw[key] = target
                    module_exports.setdefault(
                        exporter,
                        {},
                    )[local] = target
                    changed = True

    resolved: dict[str, str] = {}

    for key, initial in raw.items():
        target = initial
        visited = {key}

        while (
            target in raw
            and target not in visited
        ):
            visited.add(target)
            target = raw[target]

        if target not in visited:
            resolved[key] = target

    return resolved


def _build_reexport_map(
    modules: dict,
) -> dict[str, str]:
    """Build cycle-safe transitive identities for top-level re-exports."""
    cache_key = (
        id(modules),
        len(modules),
    )

    cached = _REEXPORT_CACHE.get(
        cache_key
    )

    if cached is not None:
        return cached

    reexport_facts_by_module = {}

    for module_id, module in modules.items():
        tree = getattr(
            module,
            "ast_tree",
            None,
        )

        if tree is None:
            continue

        reexport_facts_by_module[
            module_id
        ] = _extract_reexport_facts(
            module_id,
            tree,
        )

    resolved = _assemble_reexport_map(
        reexport_facts_by_module
    )

    _REEXPORT_CACHE[
        cache_key
    ] = resolved

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
