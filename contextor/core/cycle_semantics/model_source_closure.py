"""Deterministic source closure for a cyclic SCC's restricted import model.

This does not add edges to the canonical structural graph.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

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
            implicit_initializer_modules=tuple(sorted(evidence - hard)),
        ))
    return tuple(rows)
