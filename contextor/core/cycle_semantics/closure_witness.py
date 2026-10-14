"""Single non-direct-edge closure witnesses over lexical activation views.

These witnesses do not establish execution, import-time reachability or safety.
They do not enumerate arbitrary simple cycles or mutate canonical graph state.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .activation_view import CycleActivationViewReport
from .edge_sites import CyclicImportSiteReport, LexicalEdgeSite


@dataclass(frozen=True)
class NonDirectClosureWitness:
    source: str
    target: str
    classification: str
    non_direct_sites: tuple[LexicalEdgeSite, ...]
    direct_return_path: tuple[str, ...]
    closed_walk: tuple[str, ...]


@dataclass(frozen=True)
class SCCSingleEdgeClosure:
    members: tuple[str, ...]
    structural_edge_count: int
    direct_edge_count: int
    non_direct_edge_count: int
    direct_cyclic_scc_count: int
    single_edge_witnesses: tuple[NonDirectClosureWitness, ...]
    non_direct_without_direct_return: tuple[tuple[str, str], ...]
    evidence_scope: str = "ONE_NON_DIRECT_EDGE_PLUS_DIRECT_LEXICAL_PATH"


@dataclass(frozen=True)
class SingleEdgeClosureReport:
    components: tuple[SCCSingleEdgeClosure, ...]
    evidence_scope: str = "LEXICAL_CLOSURE_WITNESSES_NOT_RUNTIME_EXECUTION"


def _shortest_direct_path(
    start: str,
    end: str,
    adjacency: dict[str, tuple[str, ...]],
) -> tuple[str, ...] | None:
    """Shortest direct path with deterministic lexical tie resolution."""
    queue = deque([start])
    previous: dict[str, str | None] = {start: None}

    while queue:
        current = queue.popleft()
        if current == end:
            path: list[str] = []
            while current is not None:
                path.append(current)
                current = previous[current]
            return tuple(reversed(path))

        for neighbor in adjacency[current]:
            if neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)

    return None


def analyze_single_edge_cycle_closures(
    activation: CycleActivationViewReport,
    sites: CyclicImportSiteReport,
) -> SingleEdgeClosureReport:
    """Find each non-direct edge that alone closes a direct lexical path.

    Absence of a witness does not mean absence of runtime cycles. Multiple
    non-direct edges may jointly close a cycle; calls may run during imports.
    """
    if not isinstance(activation, CycleActivationViewReport):
        raise TypeError("activation must be CycleActivationViewReport")
    if not isinstance(sites, CyclicImportSiteReport):
        raise TypeError("sites must be CyclicImportSiteReport")

    if (
        activation.structural_topology != sites.topology
        or len(activation.components) != len(sites.components)
    ):
        raise ValueError("activation and site topology differ")

    output: list[SCCSingleEdgeClosure] = []

    for view, site_component in zip(
        activation.components, sites.components
    ):
        if view.members != site_component.members:
            raise ValueError("SCC member identities differ")

        view_ids = tuple((e.source, e.target) for e in view.edges)
        site_ids = tuple(
            (e.source, e.target) for e in site_component.internal_edges
        )
        if view_ids != site_ids:
            raise ValueError("SCC internal edge identities differ")

        indexed_sites = {
            (e.source, e.target): e
            for e in site_component.internal_edges
        }
        direct = set(view.unguarded_direct_edges)
        adjacency_sets: dict[str, set[str]] = {
            member: set() for member in view.members
        }

        for edge in view.edges:
            pair = (edge.source, edge.target)
            if edge.site_count != len(indexed_sites[pair].sites):
                raise ValueError("site counts differ")
            if (edge.unguarded_direct_count > 0) != (pair in direct):
                raise ValueError("direct edge membership differs")
            if pair in direct:
                adjacency_sets[edge.source].add(edge.target)

        if len(direct) != sum(
            e.unguarded_direct_count > 0 for e in view.edges
        ):
            raise ValueError("direct edge count differs")

        adjacency = {
            member: tuple(sorted(adjacency_sets[member]))
            for member in view.members
        }

        witnesses: list[NonDirectClosureWitness] = []
        no_return: list[tuple[str, str]] = []

        for edge in view.edges:
            pair = (edge.source, edge.target)
            if pair in direct:
                continue

            return_path = _shortest_direct_path(
                edge.target, edge.source, adjacency
            )
            if return_path is None:
                no_return.append(pair)
                continue

            witnesses.append(
                NonDirectClosureWitness(
                    source=edge.source,
                    target=edge.target,
                    classification=edge.classification,
                    non_direct_sites=indexed_sites[pair].sites,
                    direct_return_path=return_path,
                    closed_walk=(edge.source,) + return_path,
                )
            )

        output.append(
            SCCSingleEdgeClosure(
                members=view.members,
                structural_edge_count=len(view.edges),
                direct_edge_count=len(direct),
                non_direct_edge_count=len(view.edges) - len(direct),
                direct_cyclic_scc_count=len(
                    view.unguarded_direct_topology.cyclic_components
                ),
                single_edge_witnesses=tuple(witnesses),
                non_direct_without_direct_return=tuple(no_return),
            )
        )

    return SingleEdgeClosureReport(tuple(output))
