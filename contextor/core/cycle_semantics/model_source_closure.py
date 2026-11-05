"""Deterministic source closure for a cyclic SCC's restricted import model.

This does not add edges to the canonical structural graph.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.domain.imports import ImportRef

from .model_identity import indexed_to_logical_module, logical_to_indexed_module
from .scc import analyze_import_cycle_topology


MODEL_SOURCE_CLOSURE_VERSION = "cycle-model-source-closure/1"


@dataclass(frozen=True)
class CycleModelSourceClosure:
    members: tuple[str, ...]
    hard_reachable_modules: tuple[str, ...]
    evidence_source_modules: tuple[str, ...]
    implicit_initializer_modules: tuple[str, ...]


def compute_cycle_model_source_closures(
    hard_edges: Mapping[str, object],
) -> tuple[CycleModelSourceClosure, ...]:
    """Close each cyclic SCC over hard targets and indexed parent initializers."""
    topology = analyze_import_cycle_topology(hard_edges)
    adjacency = {
        source: tuple(sorted(set(targets)))
        for source, targets in hard_edges.items()
    }
    for targets in tuple(adjacency.values()):
        for target in targets:
            adjacency.setdefault(target, ())
    indexed = frozenset(adjacency)

    def initializers(module_id: str) -> tuple[str, ...]:
        parts = module_id.split(".")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return tuple(
            ".".join(parts[:length]) + ".__init__"
            for length in range(1, len(parts))
            if ".".join(parts[:length]) + ".__init__" in indexed
        )

    rows: list[CycleModelSourceClosure] = []
    for component in topology.cyclic_components:
        hard = set(component.members)
        pending = list(component.members)
        while pending:
            for target in adjacency[pending.pop()]:
                if target not in hard:
                    hard.add(target)
                    pending.append(target)

        evidence = set(component.members)
        pending = list(component.members)
        while pending:
            module_id = pending.pop()
            for target in (*adjacency[module_id], *initializers(module_id)):
                if target not in evidence:
                    evidence.add(target)
                    pending.append(target)

        rows.append(CycleModelSourceClosure(
            members=component.members,
            hard_reachable_modules=tuple(sorted(hard)),
            evidence_source_modules=tuple(sorted(evidence)),
            implicit_initializer_modules=tuple(sorted(
                module_id for module_id in evidence - hard
                if module_id.endswith(".__init__")
            )),
        ))
    return tuple(rows)


def compute_cycle_model_source_closures_with_optional_children(
    hard_edges: Mapping[str, object],
    indexed_imports_by_module: Mapping[str, object],
    *,
    package_root: str | None = None,
) -> tuple[CycleModelSourceClosure, ...]:
    """Select a bounded index-backed candidate source cohort, without certifying it."""
    if not isinstance(hard_edges, Mapping) or not isinstance(indexed_imports_by_module, Mapping):
        raise ValueError("Graph and import facts must be mappings")
    if package_root is not None and (
        type(package_root) is not str
        or not package_root
        or any(not part.isidentifier() for part in package_root.split("."))
    ):
        raise ValueError("Invalid package root")
    indexed = frozenset(hard_edges)
    if indexed != frozenset(indexed_imports_by_module):
        raise ValueError("Indexed import facts must cover the exact hard graph domain")
    if any(type(module) is not str or not module or
           any(not part.isidentifier() for part in module.split(".")) for module in indexed):
        raise ValueError("Invalid indexed module identity")
    adjacency: dict[str, tuple[str, ...]] = {}
    facts: dict[str, tuple[ImportRef, ...]] = {}
    for module in sorted(indexed):
        targets = hard_edges[module]
        if not isinstance(targets, (set, frozenset, tuple, list)) or any(
            type(target) is not str or target not in indexed for target in targets
        ):
            raise ValueError("Invalid hard graph targets")
        adjacency[module] = tuple(sorted(set(targets)))
        imports = indexed_imports_by_module[module]
        if not isinstance(imports, (tuple, list)):
            raise ValueError("Invalid indexed import facts")
        for imp in imports:
            if (
                type(imp) is not ImportRef
                or (imp.module is not None and (
                    type(imp.module) is not str
                    or not imp.module
                    or any(not part.isidentifier() for part in imp.module.split("."))
                ))
                or type(imp.level) is not int or imp.level < 0
                or type(imp.names) is not list
                or any(type(name) is not str or not name or
                       (name != "*" and not name.isidentifier()) for name in imp.names)
                or any(type(getattr(imp, flag)) is not bool for flag in (
                    "is_from_import", "is_local", "type_only", "is_lazy"
                ))
                or (imp.level == 0 and imp.module is None)
            ):
                raise ValueError("Invalid indexed import fact")
        facts[module] = tuple(imports)

    def ancestors(module: str) -> tuple[str, ...]:
        parts = module.split(".")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return tuple(
            ".".join(parts[:length]) + ".__init__"
            for length in range(1, len(parts))
            if ".".join(parts[:length]) + ".__init__" in indexed
        )

    def optional_children(module: str) -> tuple[str, ...]:
        found: set[str] = set()
        for imp in facts[module]:
            if not imp.is_from_import:
                continue
            if imp.level:
                logical = indexed_to_logical_module(module)
                context = logical if module.endswith(".__init__") else logical.rpartition(".")[0]
                parts = context.split(".") if context else []
                if imp.level > len(parts):
                    raise ValueError("Invalid relative import target")
                base = ".".join(parts[:len(parts) - imp.level + 1])
                if imp.module:
                    base += "." + imp.module
            else:
                base = imp.module
                if package_root and base and base.startswith(package_root + "."):
                    base = base[len(package_root) + 1:]
            if not base:
                raise ValueError("Unresolved import base")
            direct = base in indexed
            initializer = base + ".__init__" in indexed
            if direct and initializer:
                raise ValueError("Ambiguous module and initializer identity")
            if not initializer:
                continue
            for name in imp.names:
                if name == "*":
                    raise ValueError("Unsupported star package member import")
                child_name = base + "." + name
                direct = child_name in indexed
                initializer = child_name + ".__init__" in indexed
                if direct and initializer:
                    raise ValueError("Ambiguous module and initializer identity")
                child = logical_to_indexed_module(child_name, indexed)
                if child is not None:
                    found.add(child)
        return tuple(sorted(found))

    rows: list[CycleModelSourceClosure] = []
    selected_all: set[str] = set()
    for original in compute_cycle_model_source_closures(hard_edges):
        evidence = set(original.evidence_source_modules)
        if len(evidence) > 256:
            raise ValueError("Selected source capacity exceeded")
        pending = list(sorted(evidence, reverse=True))
        while pending:
            module = pending.pop()
            for child in optional_children(module):
                to_visit = [child]
                while to_visit:
                    item = to_visit.pop()
                    if item in evidence:
                        continue
                    evidence.add(item)
                    if len(evidence) > 256:
                        raise ValueError("Selected source capacity exceeded")
                    pending.append(item)
                    to_visit.extend((*adjacency[item], *ancestors(item)))
        selected_all.update(evidence)
        if len(selected_all) > 256:
            raise ValueError("Selected source capacity exceeded")
        rows.append(CycleModelSourceClosure(
            members=original.members,
            hard_reachable_modules=original.hard_reachable_modules,
            evidence_source_modules=tuple(sorted(evidence)),
            implicit_initializer_modules=original.implicit_initializer_modules,
        ))
    return tuple(rows)
