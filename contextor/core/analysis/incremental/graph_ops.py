"""
contextor/core/analysis/incremental/graph_ops.py

Pure incremental graph operations and delta calculations:
- calculate_affected_set (reverse transitive closure / blast radius)
- calculate_degree_deltas (local node degree deltas from hard edges)
- LocalDegreeDeltaResult (domain data contract)
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional, Set, Dict, Iterable, Tuple

from contextor.core.domain.graph import ProjectGraph


@dataclass(frozen=True)
class LocalDegreeDeltaResult:
    """Represents exact local graph degree updates derived from an OLD->NEW hard-edge graph delta."""
    complete: bool
    fan_in_updates: Dict[str, int] = field(default_factory=dict)
    fan_out_updates: Dict[str, int] = field(default_factory=dict)
    added_modules: Set[str] = field(default_factory=set)
    removed_modules: Set[str] = field(default_factory=set)


def calculate_affected_set(
    changed_module: str,
    old_graph: Optional[ProjectGraph] = None,
    new_graph: Optional[ProjectGraph] = None,
) -> Set[str]:
    """
    Calculates the reverse transitive closure (blast radius) of the change.
    A module is affected if it directly or transitively depends on changed_module
    in either the old or candidate new dependency graph (hard and soft edges).
    """
    graphs = [g for g in (old_graph, new_graph) if g is not None]
    if not graphs:
        return {changed_module}

    reverse_edges = build_reverse_adjacency(*graphs)
    return calculate_affected_set_from_reverse(changed_module, reverse_edges)


def build_reverse_adjacency(
    *graphs: Optional[ProjectGraph],
) -> dict[str, set[str]]:
    """Build one deterministic reverse adjacency map from dependency graphs.

    Both hard and soft edges participate, matching ``calculate_affected_set``.
    Passing multiple graphs unions their edges; ``None`` graphs are ignored.
    """
    reverse_edges: dict[str, set[str]] = defaultdict(set)
    for graph in graphs:
        if graph is None:
            continue
        for edge_map in (graph.hard_edges, graph.soft_edges):
            for source, targets in edge_map.items():
                for target in targets:
                    reverse_edges[target].add(source)
    return dict(reverse_edges)


def calculate_affected_set_from_reverse(
    changed_module: str,
    reverse_adjacency: dict[str, set[str]],
) -> Set[str]:
    """Calculate reverse transitive closure from a prepared adjacency map."""
    affected: Set[str] = {changed_module}
    queue = deque([changed_module])
    while queue:
        curr = queue.popleft()
        for consumer in sorted(reverse_adjacency.get(curr, set())):
            if consumer not in affected:
                affected.add(consumer)
                queue.append(consumer)

    return affected


def calculate_degree_deltas(
    old_graph: Optional[ProjectGraph] = None,
    new_graph: Optional[ProjectGraph] = None,
    old_modules: Optional[Iterable[str]] = None,
    new_modules: Optional[Iterable[str]] = None,
) -> LocalDegreeDeltaResult:
    """
    Calculates exact local graph degree changes (fan_in, fan_out) from hard-edge deltas
    between old_graph and new_graph.

    - fan_in / fan_out use hard_edges ONLY (soft_edges do not participate).
    - Values are recomputed from candidate new_graph.
    - Missing either old_graph or new_graph marks complete=False.
    - Newly added isolated modules receive fan_in=0, fan_out=0.
    - Deleted modules are reported in removed_modules and excluded from active degree updates.
    - Unrelated unchanged nodes are not included in update sets.
    """
    if old_graph is None or new_graph is None:
        return LocalDegreeDeltaResult(complete=False)

    old_mod_set = set(old_modules) if old_modules is not None else set(old_graph.hard_edges.keys())
    new_mod_set = set(new_modules) if new_modules is not None else set(new_graph.hard_edges.keys())

    added_modules = new_mod_set - old_mod_set
    removed_modules = old_mod_set - new_mod_set

    old_edges: Set[Tuple[str, str]] = {
        (source, target)
        for source, targets in old_graph.hard_edges.items()
        for target in targets
    }
    new_edges: Set[Tuple[str, str]] = {
        (source, target)
        for source, targets in new_graph.hard_edges.items()
        for target in targets
    }

    added_edges = new_edges - old_edges
    removed_edges = old_edges - new_edges

    fan_out_changed = {source for source, _ in (added_edges | removed_edges)} | added_modules
    fan_in_changed = {target for _, target in (added_edges | removed_edges)} | added_modules

    # Surviving / newly active modules to update
    surviving_fan_out = fan_out_changed - removed_modules
    surviving_fan_in = fan_in_changed - removed_modules

    fan_out_updates: Dict[str, int] = {}
    for m in sorted(surviving_fan_out):
        fan_out_updates[m] = len(new_graph.hard_edges.get(m, set()))

    fan_in_updates: Dict[str, int] = {}
    for m in sorted(surviving_fan_in):
        fan_in_updates[m] = sum(
            1 for _, targets in new_graph.hard_edges.items() if m in targets
        )

    return LocalDegreeDeltaResult(
        complete=True,
        fan_in_updates=fan_in_updates,
        fan_out_updates=fan_out_updates,
        added_modules=added_modules,
        removed_modules=removed_modules,
    )
