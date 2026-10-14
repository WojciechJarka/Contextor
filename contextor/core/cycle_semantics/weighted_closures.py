"""Minimum non-direct-edge witnesses for structural import cycles.

Edge weights express membership in the approved direct lexical
projection, never runtime risk or Python import execution.

No simple-cycle enumeration or canonical graph mutation occurs.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush

from .diagnostic_view import CycleEvidenceDigest


_Edge = tuple[str, str]


@dataclass(frozen=True)
class WeightedNonDirectCycleWitness:
    closing_edge: _Edge
    closing_classification: str
    minimum_non_direct_edge_count: int
    total_cycle_edge_count: int
    return_path: tuple[str, ...]
    closed_walk: tuple[str, ...]
    non_direct_edges: tuple[_Edge, ...]
    direct_edges: tuple[_Edge, ...]
    unresolved_source_edges: tuple[_Edge, ...]
    evidence_coverage: str


@dataclass(frozen=True)
class SCCWeightedCycleClosures:
    members: tuple[str, ...]
    structural_edge_count: int
    direct_candidate_edge_count: int
    non_direct_candidate_edge_count: int
    direct_cyclic_component_count: int
    single_non_direct_witness_count: int
    multiple_non_direct_witness_count: int
    witnesses: tuple[WeightedNonDirectCycleWitness, ...]
    evidence_scope: str = (
        "MINIMUM_NON_DIRECT_STRUCTURAL_CYCLE_COST"
    )


@dataclass(frozen=True)
class WeightedCycleClosureReport:
    components: tuple[SCCWeightedCycleClosures, ...]
    evidence_scope: str = (
        "WEIGHTED_STRUCTURAL_WITNESSES_NOT_RUNTIME_EXECUTION"
    )


def _minimum_return_path(
    start: str,
    end: str,
    adjacency: dict[
        str,
        tuple[tuple[str, bool], ...],
    ],
    closing_edge: _Edge,
) -> tuple[int, int, tuple[str, ...]] | None:
    """Minimum (non-direct cost, hops, lexical path).

    Dijkstra's algorithm uses a deterministic tuple priority.
    The positive hop count prevents cyclic detours from improving
    a result, including zero-cost direct-edge detours.
    """
    initial = (0, 0, (start,))
    best = {start: initial}

    queue = [
        (0, 0, (start,), start)
    ]

    while queue:
        cost, hops, path, current = heappop(queue)

        if (cost, hops, path) != best.get(current):
            continue

        if current == end:
            return cost, hops, path

        for target, is_direct in adjacency[current]:
            if (current, target) == closing_edge:
                continue

            candidate = (
                cost + (0 if is_direct else 1),
                hops + 1,
                path + (target,),
            )

            previous = best.get(target)

            if previous is None or candidate < previous:
                best[target] = candidate

                heappush(
                    queue,
                    (
                        candidate[0],
                        candidate[1],
                        candidate[2],
                        target,
                    ),
                )

    return None


def analyze_weighted_cycle_closures(
    digest: CycleEvidenceDigest,
) -> WeightedCycleClosureReport:
    """Find minimum-cost cycles containing each non-direct edge.

    A structural return path does not establish whether its imports
    execute in a single Python initialization sequence.
    """
    if not isinstance(digest, CycleEvidenceDigest):
        raise TypeError("digest must be CycleEvidenceDigest")

    if (
        digest.evidence_scope
        != "STRUCTURAL_AND_LEXICAL_NOT_RUNTIME"
    ):
        raise ValueError("unsupported digest evidence scope")

    if (
        len(digest.structural_topology.cyclic_components)
        != len(digest.components)
    ):
        raise ValueError("structural SCC cardinality differs")

    output: list[SCCWeightedCycleClosures] = []

    for structural, component in zip(
        digest.structural_topology.cyclic_components,
        digest.components,
    ):
        if structural.members != component.members:
            raise ValueError("SCC member identities differ")

        rows = component.edges

        row_ids = tuple(
            (row.source, row.target)
            for row in rows
        )

        if row_ids != structural.internal_edges:
            raise ValueError("structural edge identities differ")

        if component.structural_edge_count != len(rows):
            raise ValueError("structural edge count differs")

        members = set(component.members)

        direct: set[_Edge] = set()
        non_direct: set[_Edge] = set()

        indexed = {}

        adjacency_lists: dict[
            str,
            list[tuple[str, bool]],
        ] = {
            member: []
            for member in component.members
        }

        for row in rows:
            pair = (row.source, row.target)

            if (
                row.source not in members
                or row.target not in members
            ):
                raise ValueError("edge escapes structural SCC")

            if (
                (row.lexical.source, row.lexical.target)
                != pair
                or (
                    row.activation.source,
                    row.activation.target,
                ) != pair
            ):
                raise ValueError("edge source evidence differs")

            is_direct = row.in_direct_candidate_graph

            if (
                is_direct
                != (row.activation.unguarded_direct_count > 0)
            ):
                raise ValueError("direct membership differs")

            indexed[pair] = row

            adjacency_lists[row.source].append(
                (row.target, is_direct)
            )

            if is_direct:
                direct.add(pair)
            else:
                non_direct.add(pair)

        if (
            len(indexed) != len(rows)
            or len(direct) != component.direct_candidate_edge_count
            or len(non_direct)
            != component.non_direct_candidate_edge_count
        ):
            raise ValueError("edge partition differs")

        single = {
            (item.source, item.target): item
            for item in component.single_edge_closures
        }

        without_single = set(
            component.non_direct_without_direct_return
        )

        if (
            len(single) != len(component.single_edge_closures)
            or len(without_single)
            != len(component.non_direct_without_direct_return)
            or single.keys() & without_single
            or set(single) | without_single != non_direct
        ):
            raise ValueError("single-edge closure partition differs")

        adjacency = {
            member: tuple(sorted(adjacency_lists[member]))
            for member in component.members
        }

        witnesses: list[WeightedNonDirectCycleWitness] = []
        one_edge_count = 0
        multiple_count = 0

        for row in rows:
            closing_edge = (row.source, row.target)

            if closing_edge in direct:
                continue

            result = _minimum_return_path(
                row.target,
                row.source,
                adjacency,
                closing_edge,
            )

            if result is None:
                raise ValueError(
                    "non-direct edge has no structural return path"
                )

            return_cost, return_hops, return_path = result

            closed_walk = (row.source,) + return_path

            walk_edges = tuple(
                zip(closed_walk, closed_walk[1:])
            )

            non_direct_edges = tuple(
                edge
                for edge in walk_edges
                if edge in non_direct
            )

            direct_edges = tuple(
                edge
                for edge in walk_edges
                if edge in direct
            )

            unresolved_edges = tuple(
                edge
                for edge in walk_edges
                if indexed[edge].lexical.status
                != "LEXICAL_CANDIDATES"
            )

            minimum_count = 1 + return_cost

            if (
                len(walk_edges) != return_hops + 1
                or len(non_direct_edges) != minimum_count
                or len(direct_edges) + len(non_direct_edges)
                != len(walk_edges)
                or non_direct_edges[0] != closing_edge
            ):
                raise ValueError("weighted walk accounting differs")

            old_single = single.get(closing_edge)

            if minimum_count == 1:
                one_edge_count += 1

                if (
                    old_single is None
                    or old_single.direct_return_path
                    != return_path
                    or old_single.closed_walk != closed_walk
                ):
                    raise ValueError(
                        "single-edge C12 witness disagrees"
                    )

            else:
                multiple_count += 1

                if (
                    old_single is not None
                    or closing_edge not in without_single
                ):
                    raise ValueError(
                        "non-direct C12 partition disagrees"
                    )

            witnesses.append(
                WeightedNonDirectCycleWitness(
                    closing_edge=closing_edge,
                    closing_classification=(
                        row.activation.classification
                    ),
                    minimum_non_direct_edge_count=(
                        minimum_count
                    ),
                    total_cycle_edge_count=len(walk_edges),
                    return_path=return_path,
                    closed_walk=closed_walk,
                    non_direct_edges=non_direct_edges,
                    direct_edges=direct_edges,
                    unresolved_source_edges=unresolved_edges,
                    evidence_coverage=(
                        "INCOMPLETE_LEXICAL_EVIDENCE"
                        if unresolved_edges
                        else "ALL_EDGES_HAVE_LEXICAL_CANDIDATES"
                    ),
                )
            )

        if (
            one_edge_count != len(single)
            or multiple_count != len(without_single)
            or len(witnesses) != len(non_direct)
        ):
            raise ValueError("closure witness accounting differs")

        output.append(
            SCCWeightedCycleClosures(
                members=component.members,
                structural_edge_count=len(rows),
                direct_candidate_edge_count=len(direct),
                non_direct_candidate_edge_count=len(non_direct),
                direct_cyclic_component_count=len(
                    component.direct_cyclic_components
                ),
                single_non_direct_witness_count=one_edge_count,
                multiple_non_direct_witness_count=multiple_count,
                witnesses=tuple(witnesses),
            )
        )

    return WeightedCycleClosureReport(tuple(output))
