"""
contextor/core/reference/shared.py

Pure shared lower-level reference helpers, normalization utilities, and
re-export analysis used by both reference.index and reference.engine.

Dependency Invariant:
This module must NOT depend on reference.engine or reference.index.
"""

from __future__ import annotations

import ast
from typing import Any, Mapping

from .resolution import _absolute_import_module

MAX_USAGE_DETAILS = 15

_REEXPORT_CACHE: dict = {}
_REEXPORT_FACT_KEYS = frozenset(
    {
        "exporter",
        "explicit_all",
        "bindings",
        "star_sources",
    }
)


def reset_reexport_cache() -> None:
    """Clear cached re-export maps."""
    _REEXPORT_CACHE.clear()


def _export_module_name(module_id: str) -> str:
    """Normalize package __init__ module ID to parent package identity."""
    return module_id.removesuffix(".__init__")


def _is_valid_reexport_fact(
    module_id: str,
    fact: Any,
) -> bool:
    if not isinstance(module_id, str) or not module_id:
        return False

    if not isinstance(fact, dict):
        return False

    if set(fact) != _REEXPORT_FACT_KEYS:
        return False

    if fact.get("exporter") != _export_module_name(module_id):
        return False

    explicit_all = fact.get("explicit_all")
    if explicit_all is not None:
        if not isinstance(explicit_all, list):
            return False
        if not all(
            isinstance(item, str)
            for item in explicit_all
        ):
            return False

    bindings = fact.get("bindings")
    if not isinstance(bindings, dict):
        return False
    if not all(
        isinstance(local, str)
        and isinstance(target, str)
        for local, target in bindings.items()
    ):
        return False

    star_sources = fact.get("star_sources")
    if not isinstance(star_sources, list):
        return False
    if not all(
        isinstance(source, str)
        for source in star_sources
    ):
        return False

    return True


def validate_reexport_facts_by_module(
    facts_by_module: Any,
    modules: Any,
) -> bool:
    if not isinstance(facts_by_module, dict):
        return False

    if not isinstance(modules, dict):
        return False

    if set(facts_by_module) != set(modules):
        return False

    return all(
        _is_valid_reexport_fact(
            module_id,
            facts_by_module[module_id],
        )
        for module_id in modules
    )


def materialize_reexport_facts_by_module(
    modules: dict,
    compact_reference_facts: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    compact_facts = compact_reference_facts or {}

    for module_id, module in modules.items():
        envelope = compact_facts.get(module_id)
        fact = None
        if isinstance(envelope, Mapping) and envelope.get("status") == "available":
            facts = envelope.get("facts")
            if isinstance(facts, Mapping):
                compact_fact = facts.get("reexports")
                if _is_valid_reexport_fact(module_id, compact_fact):
                    fact = compact_fact

        if fact is None:
            tree = getattr(module, "ast_tree", None)
            if tree is None:
                raise RuntimeError(
                    "Canonical re-export facts unavailable for module "
                    f"'{module_id}'."
                )
            fact = _extract_reexport_facts(module_id, tree)
            if not _is_valid_reexport_fact(module_id, fact):
                raise RuntimeError(
                    "Canonical re-export facts unavailable for module "
                    f"'{module_id}'."
                )

        result[module_id] = {
            "exporter": fact["exporter"],
            "explicit_all": (
                None
                if fact["explicit_all"] is None
                else list(fact["explicit_all"])
            ),
            "bindings": dict(fact["bindings"]),
            "star_sources": list(fact["star_sources"]),
        }

    if not validate_reexport_facts_by_module(
        result,
        modules,
    ):
        raise RuntimeError(
            "Canonical re-export facts do not cover the current module domain."
        )

    return result


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


def _assemble_export_surface_state(
    reexport_facts_by_module: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """
    Assemble visible module exports and their raw re-export identities.

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

    return module_exports, raw


def _assemble_module_export_surfaces(
    reexport_facts_by_module: dict[str, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """Assemble visible local exports and their source target identities."""
    module_exports, _raw = _assemble_export_surface_state(
        reexport_facts_by_module
    )
    return module_exports


def _assemble_reexport_map(
    reexport_facts_by_module: dict[str, dict[str, Any]],
) -> dict[str, str]:
    """Assemble cycle-safe transitive re-export identities from source facts."""
    _module_exports, raw = _assemble_export_surface_state(
        reexport_facts_by_module
    )

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
