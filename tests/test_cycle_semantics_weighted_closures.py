"""Minimum non-direct cycle cost regressions.

Exhaustive simple-path enumeration is used only as a tiny-graph
test oracle, never in the production weighted cycle algorithm.
"""

import json
from dataclasses import FrozenInstanceError, asdict, replace
from itertools import product

import pytest

from contextor.core.cycle_semantics.scc import (
    analyze_import_cycle_topology,
)
from contextor.core.cycle_semantics.edge_sites import (
    CyclicImportSiteReport,
    SCCImportSiteEvidence,
    HardEdgeSiteEvidence,
    LexicalEdgeSite,
)
from contextor.core.cycle_semantics.activation_view import (
    analyze_cycle_activation_view,
)
from contextor.core.cycle_semantics.closure_witness import (
    analyze_single_edge_cycle_closures,
)
from contextor.core.cycle_semantics.diagnostic_view import (
    build_cycle_evidence_digest,
)
from contextor.core.cycle_semantics.weighted_closures import (
    analyze_weighted_cycle_closures,
)


C19_DIRECT_SITE = ("MODULE_TOP_LEVEL", "FROM_BASE")
C19_FUNCTION_SITE = ("FUNCTION_SCOPED", "FROM_BASE")
C19_GUARDED_SITE = ("GUARDED_TOP_LEVEL", "FROM_BASE")
C19_INDIRECT_SITE = ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER")


def _digest(graph, specs):
    topology = analyze_import_cycle_topology(graph)
    components = []

    for structural in topology.cyclic_components:
        edges = []

        for source, target in structural.internal_edges:
            specification = specs.get(
                (source, target),
            )

            if specification is None:
                edge = HardEdgeSiteEvidence(
                    source,
                    target,
                    "SOURCE_MISSING_OR_INVALID",
                    (),
                )

            elif not specification:
                edge = HardEdgeSiteEvidence(
                    source,
                    target,
                    "NO_MATCHING_LEXICAL_SITE",
                    (),
                )

            else:
                sites = tuple(
                    LexicalEdgeSite(
                        ordinal=ordinal,
                        line=ordinal + 1,
                        column=0,
                        form="IMPORT_FROM",
                        match_kind=kind,
                        requested_name=target,
                        matched_member=None,
                        scopes=(),
                        controls=(),
                        activation_scope=scope,
                    )
                    for ordinal, (scope, kind)
                    in enumerate(specification)
                )

                edge = HardEdgeSiteEvidence(
                    source,
                    target,
                    "LEXICAL_CANDIDATES",
                    sites,
                )

            edges.append(edge)

        components.append(
            SCCImportSiteEvidence(
                members=structural.members,
                internal_edges=tuple(edges),
                matched_edge_count=sum(
                    edge.status == "LEXICAL_CANDIDATES"
                    for edge in edges
                ),
                unresolved_edge_count=sum(
                    edge.status != "LEXICAL_CANDIDATES"
                    for edge in edges
                ),
            )
        )

    sites = CyclicImportSiteReport(
        topology,
        tuple(components),
    )

    activation = analyze_cycle_activation_view(sites)

    closures = analyze_single_edge_cycle_closures(
        activation,
        sites,
    )

    return build_cycle_evidence_digest(
        sites,
        activation,
        closures,
    )


def _weighted(graph, specs):
    return analyze_weighted_cycle_closures(
        _digest(graph, specs)
    )


def test_one_non_direct_matches_c12():
    result = _weighted(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [C19_DIRECT_SITE],
            ("b", "a"): [C19_FUNCTION_SITE],
        },
    )
    component = result.components[0]
    witness = component.witnesses[0]

    assert component.single_non_direct_witness_count == 1
    assert component.multiple_non_direct_witness_count == 0
    assert witness.minimum_non_direct_edge_count == 1
    assert witness.closed_walk == ("b", "a", "b")
    assert witness.non_direct_edges == (("b", "a"),)
    assert witness.direct_edges == (("a", "b"),)


def test_two_non_direct_edges_required():
    result = _weighted(
        {
            "a": {"b"},
            "b": {"c"},
            "c": {"a"},
        },
        {
            ("a", "b"): [C19_DIRECT_SITE],
            ("b", "c"): [C19_FUNCTION_SITE],
            ("c", "a"): [C19_FUNCTION_SITE],
        },
    )
    component = result.components[0]

    assert component.single_non_direct_witness_count == 0
    assert component.multiple_non_direct_witness_count == 2

    assert all(
        witness.minimum_non_direct_edge_count == 2
        for witness in component.witnesses
    )


def test_three_non_direct_edges_required():
    graph = {
        "a": {"b"},
        "b": {"c"},
        "c": {"a"},
    }
    specs = {
        pair: [C19_FUNCTION_SITE]
        for source, targets in graph.items()
        for target in targets
        for pair in [(source, target)]
    }
    component = _weighted(graph, specs).components[0]

    assert len(component.witnesses) == 3
    assert {
        witness.minimum_non_direct_edge_count
        for witness in component.witnesses
    } == {3}


def test_four_non_direct_edges_required():
    graph = {
        "a": {"b"},
        "b": {"c"},
        "c": {"d"},
        "d": {"a"},
    }
    specs = {
        (source, target): [C19_FUNCTION_SITE]
        for source, targets in graph.items()
        for target in targets
    }
    component = _weighted(graph, specs).components[0]

    assert len(component.witnesses) == 4
    assert {
        witness.minimum_non_direct_edge_count
        for witness in component.witnesses
    } == {4}


def test_fewer_non_direct_beats_shorter_hop_path():
    graph = {
        "a": {"b", "x"},
        "b": {"c"},
        "c": {"d"},
        "d": {"z"},
        "x": {"z"},
        "z": {"a"},
    }
    specs = {
        (source, target): [C19_DIRECT_SITE]
        for source, targets in graph.items()
        for target in targets
    }
    specs[("x", "z")] = [C19_FUNCTION_SITE]
    specs[("z", "a")] = [C19_FUNCTION_SITE]

    component = _weighted(graph, specs).components[0]
    witness = next(
        item for item in component.witnesses
        if item.closing_edge == ("z", "a")
    )

    assert witness.minimum_non_direct_edge_count == 1
    assert witness.return_path == (
        "a", "b", "c", "d", "z"
    )


def test_shortest_hops_break_equal_cost_ties():
    graph = {
        "a": {"b", "c"},
        "b": {"z"},
        "c": {"d"},
        "d": {"z"},
        "z": {"a"},
    }
    specs = {
        (source, target): [C19_DIRECT_SITE]
        for source, targets in graph.items()
        for target in targets
    }
    specs[("z", "a")] = [C19_FUNCTION_SITE]

    component = _weighted(graph, specs).components[0]
    witness = component.witnesses[0]

    assert witness.return_path == ("a", "b", "z")


def test_lexical_order_breaks_equal_cost_and_hop_ties():
    graph = {
        "a": {"b", "c"},
        "b": {"z"},
        "c": {"z"},
        "z": {"a"},
    }
    specs = {
        (source, target): [C19_DIRECT_SITE]
        for source, targets in graph.items()
        for target in targets
    }
    specs[("z", "a")] = [C19_FUNCTION_SITE]

    component = _weighted(graph, specs).components[0]

    assert component.witnesses[0].return_path == (
        "a", "b", "z"
    )


def test_non_direct_self_loop():
    component = _weighted(
        {"a": {"a"}},
        {("a", "a"): [C19_FUNCTION_SITE]},
    ).components[0]

    witness = component.witnesses[0]

    assert witness.minimum_non_direct_edge_count == 1
    assert witness.total_cycle_edge_count == 1
    assert witness.return_path == ("a",)
    assert witness.closed_walk == ("a", "a")


def test_direct_cycle_and_other_scc_remain_distinct():
    component_one, component_two = _weighted(
        {
            "a": {"b"},
            "b": {"a"},
            "x": {"y"},
            "y": {"x"},
        },
        {
            ("a", "b"): [C19_DIRECT_SITE],
            ("b", "a"): [C19_DIRECT_SITE],
            ("x", "y"): [C19_DIRECT_SITE],
            ("y", "x"): [C19_FUNCTION_SITE],
        },
    ).components

    assert component_one.members == ("a", "b")
    assert component_one.direct_cyclic_component_count == 1
    assert component_one.witnesses == ()

    assert component_two.members == ("x", "y")
    assert component_two.single_non_direct_witness_count == 1


def test_unresolved_lexical_evidence_is_retained():
    component = _weighted(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C19_DIRECT_SITE]},
    ).components[0]

    witness = component.witnesses[0]

    assert witness.closing_edge == ("b", "a")
    assert witness.minimum_non_direct_edge_count == 1
    assert witness.unresolved_source_edges == (
        ("b", "a"),
    )
    assert witness.evidence_coverage == (
        "INCOMPLETE_LEXICAL_EVIDENCE"
    )


def test_guarded_and_indirect_candidates_not_promoted():
    components = _weighted(
        {
            "a": {"b"},
            "b": {"a"},
            "x": {"y"},
            "y": {"x"},
        },
        {
            ("a", "b"): [C19_DIRECT_SITE],
            ("b", "a"): [C19_GUARDED_SITE],
            ("x", "y"): [C19_DIRECT_SITE],
            ("y", "x"): [C19_INDIRECT_SITE],
        },
    ).components

    assert components[0].witnesses[0].closing_classification == (
        "GUARDED_TOP_LEVEL_CANDIDATE"
    )
    assert components[1].witnesses[0].closing_classification == (
        "INDIRECT_TOP_LEVEL_CANDIDATE"
    )


def test_inconsistent_c12_witness_rejected():
    digest = _digest(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [C19_DIRECT_SITE],
            ("b", "a"): [C19_FUNCTION_SITE],
        },
    )

    changed = replace(
        digest.components[0],
        single_edge_closures=(),
    )
    invalid = replace(
        digest,
        components=(changed,),
    )

    with pytest.raises(ValueError):
        analyze_weighted_cycle_closures(invalid)


def test_invalid_structural_edge_identity_rejected():
    digest = _digest(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [C19_DIRECT_SITE],
            ("b", "a"): [C19_FUNCTION_SITE],
        },
    )

    changed = replace(
        digest.components[0],
        edges=tuple(reversed(digest.components[0].edges)),
    )
    invalid = replace(
        digest,
        components=(changed,),
    )

    with pytest.raises(ValueError):
        analyze_weighted_cycle_closures(invalid)


def _small_graph_oracle(
    start,
    end,
    adjacency,
    closing_edge,
):
    """Enumerate paths ONLY in tiny synthetic test graphs."""
    candidates = []

    def walk(current, visited, path, cost):
        if current == end:
            candidates.append(
                (cost, len(path) - 1, path)
            )
            return

        for target, direct in adjacency[current]:
            if (
                (current, target) == closing_edge
                or target in visited
            ):
                continue

            walk(
                target,
                visited | {target},
                path + (target,),
                cost + (0 if direct else 1),
            )

    walk(start, {start}, (start,), 0)

    return min(candidates) if candidates else None


def test_exhaustive_three_node_graph_oracle():
    nodes = ("a", "b", "c")
    possible = tuple(
        (source, target)
        for source in nodes
        for target in nodes
        if source != target
    )

    for values in product((0, 1, 2), repeat=len(possible)):
        graph = {
            member: set()
            for member in nodes
        }
        specs = {}
        adjacency = {
            member: []
            for member in nodes
        }

        for (source, target), kind in zip(
            possible, values
        ):
            if kind == 0:
                continue

            graph[source].add(target)

            direct = kind == 1

            specs[(source, target)] = [
                C19_DIRECT_SITE
                if direct else C19_FUNCTION_SITE
            ]

            adjacency[source].append(
                (target, direct)
            )

        adjacency = {
            member: tuple(sorted(edges))
            for member, edges in adjacency.items()
        }

        result = _weighted(graph, specs)

        for component in result.components:
            for witness in component.witnesses:
                source, target = witness.closing_edge

                expected = _small_graph_oracle(
                    target,
                    source,
                    adjacency,
                    witness.closing_edge,
                )

                assert expected is not None

                assert (
                    witness.minimum_non_direct_edge_count,
                    witness.total_cycle_edge_count,
                    witness.return_path,
                ) == (
                    1 + expected[0],
                    1 + expected[1],
                    expected[2],
                )


def test_long_chain_without_recursion():
    size = 140

    graph = {
        f"n{i:03d}": {f"n{i+1:03d}"}
        for i in range(size - 1)
    }
    graph[f"n{size-1:03d}"] = {"n000"}

    specs = {
        (source, target): [C19_DIRECT_SITE]
        for source, targets in graph.items()
        for target in targets
    }

    specs[(f"n{size-1:03d}", "n000")] = [
        C19_FUNCTION_SITE
    ]

    component = _weighted(graph, specs).components[0]

    assert len(component.witnesses) == 1
    assert component.witnesses[0].total_cycle_edge_count == size
    assert component.witnesses[0].minimum_non_direct_edge_count == 1


def test_determinism_immutability_empty_and_invalid_type():
    digest = _digest(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [C19_DIRECT_SITE],
            ("b", "a"): [C19_FUNCTION_SITE],
        },
    )

    before = repr(digest)

    first = analyze_weighted_cycle_closures(digest)
    second = analyze_weighted_cycle_closures(digest)

    assert first == second
    assert before == repr(digest)

    json.dumps(asdict(first))

    with pytest.raises(FrozenInstanceError):
        first.components[0].structural_edge_count = 99

    empty = _weighted(
        {"a": {"b"}, "b": set()},
        {},
    )
    assert empty.components == ()

    with pytest.raises(TypeError):
        analyze_weighted_cycle_closures(None)
