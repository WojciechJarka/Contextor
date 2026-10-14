"""Deterministic, iterative SCC evidence from an unchanged hard-import graph.

Structural membership is not import-execution evidence or a safety verdict.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CyclicImportComponent:
    members: tuple[str, ...]
    internal_edges: tuple[tuple[str, str], ...]
    kind: str


@dataclass(frozen=True)
class ImportCycleTopology:
    node_count: int
    hard_edge_count: int
    total_scc_count: int
    cyclic_components: tuple[CyclicImportComponent, ...]
    evidence_scope: str = "STRUCTURAL_HARD_IMPORT_GRAPH"


def analyze_import_cycle_topology(
    hard_edges: Mapping[
        str,
        set[str] | frozenset[str] | list[str] | tuple[str, ...],
    ],
) -> ImportCycleTopology:
    """Find all cyclic SCCs without mutating input or enumerating simple cycles.

    A self-loop is cyclic, and multiple cycle paths inside an SCC still count
    as one cyclic component. Edges to target-only nodes remain represented.
    """
    if not isinstance(hard_edges, Mapping):
        raise TypeError("hard_edges must be a mapping")

    adjacency_sets: dict[str, set[str]] = {}
    for source, targets in hard_edges.items():
        if not isinstance(source, str) or not source:
            raise ValueError("invalid source module")
        if not isinstance(targets, (set, frozenset, tuple, list)):
            raise TypeError("targets must be an explicit collection")
        normalized: set[str] = set()
        for target in targets:
            if not isinstance(target, str) or not target:
                raise ValueError("invalid target module")
            normalized.add(target)
        adjacency_sets[source] = normalized

    for targets in tuple(adjacency_sets.values()):
        for target in targets:
            adjacency_sets.setdefault(target, set())

    adjacency = {
        node: tuple(sorted(targets))
        for node, targets in sorted(adjacency_sets.items())
    }
    predecessors: dict[str, list[str]] = {node: [] for node in adjacency}
    for source, targets in adjacency.items():
        for target in targets:
            predecessors[target].append(source)
    reverse = {node: tuple(sorted(pred)) for node, pred in predecessors.items()}

    visited: set[str] = set()
    finish_order: list[str] = []
    for source in adjacency:
        if source in visited:
            continue
        visited.add(source)
        stack: list[tuple[str, int]] = [(source, 0)]
        while stack:
            node, index = stack[-1]
            successors = adjacency[node]
            if index == len(successors):
                finish_order.append(node)
                stack.pop()
                continue
            stack[-1] = (node, index + 1)
            next_node = successors[index]
            if next_node not in visited:
                visited.add(next_node)
                stack.append((next_node, 0))

    visited.clear()
    cyclic: list[CyclicImportComponent] = []
    all_scc_count = 0
    for source in reversed(finish_order):
        if source in visited:
            continue
        all_scc_count += 1
        members: list[str] = []
        stack = [source]
        visited.add(source)
        while stack:
            node = stack.pop()
            members.append(node)
            for predecessor in reverse[node]:
                if predecessor not in visited:
                    visited.add(predecessor)
                    stack.append(predecessor)

        ordered_members = tuple(sorted(members))
        if len(ordered_members) == 1:
            only = ordered_members[0]
            if only not in adjacency[only]:
                continue

        member_set = set(ordered_members)
        internal_edges = tuple(
            (node, target)
            for node in ordered_members
            for target in adjacency[node]
            if target in member_set
        )
        cyclic.append(CyclicImportComponent(
            members=ordered_members,
            internal_edges=internal_edges,
            kind="SELF_LOOP" if len(ordered_members) == 1 else "MULTI_MODULE",
        ))

    return ImportCycleTopology(
        node_count=len(adjacency),
        hard_edge_count=sum(len(targets) for targets in adjacency.values()),
        total_scc_count=all_scc_count,
        cyclic_components=tuple(sorted(cyclic, key=lambda item: item.members)),
    )
