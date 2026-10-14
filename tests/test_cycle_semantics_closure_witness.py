import json
from dataclasses import FrozenInstanceError, asdict, replace

import pytest

from contextor.core.cycle_semantics.scc import analyze_import_cycle_topology
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


D = ("MODULE_TOP_LEVEL", "FROM_BASE", 1)
F = ("FUNCTION_SCOPED", "FROM_BASE", 23)
G = ("GUARDED_TOP_LEVEL", "FROM_BASE", 9)
I = ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER", 5)


def _make(graph, specs):
    topology = analyze_import_cycle_topology(graph)
    components = []

    for component in topology.cyclic_components:
        edges = []

        for source, target in component.internal_edges:
            specification = specs.get((source, target), None)

            if specification is None:
                edges.append(
                    HardEdgeSiteEvidence(
                        source,
                        target,
                        "SOURCE_MISSING_OR_INVALID",
                        (),
                    )
                )
            elif not specification:
                edges.append(
                    HardEdgeSiteEvidence(
                        source,
                        target,
                        "NO_MATCHING_LEXICAL_SITE",
                        (),
                    )
                )
            else:
                sites = tuple(
                    LexicalEdgeSite(
                        ordinal,
                        line,
                        0,
                        "IMPORT_FROM",
                        kind,
                        target,
                        None,
                        (),
                        (),
                        scope,
                    )
                    for ordinal, (scope, kind, line)
                    in enumerate(specification)
                )
                edges.append(
                    HardEdgeSiteEvidence(
                        source,
                        target,
                        "LEXICAL_CANDIDATES",
                        sites,
                    )
                )

        components.append(
            SCCImportSiteEvidence(
                component.members,
                tuple(edges),
                sum(
                    edge.status == "LEXICAL_CANDIDATES"
                    for edge in edges
                ),
                sum(
                    edge.status != "LEXICAL_CANDIDATES"
                    for edge in edges
                ),
            )
        )

    evidence = CyclicImportSiteReport(
        topology,
        tuple(components),
    )
    return analyze_cycle_activation_view(evidence), evidence


def _examine(graph, specifications):
    activation, evidence = _make(graph, specifications)
    return analyze_single_edge_cycle_closures(
        activation,
        evidence,
    )


def test_function_single_closure():
    result = _examine(
        {"a": {"b"}, "b": {"c"}, "c": {"a"}},
        {
            ("a", "b"): [D],
            ("b", "c"): [D],
            ("c", "a"): [F],
        },
    )
    component = result.components[0]
    assert component.direct_edge_count == 2
    assert component.non_direct_edge_count == 1
    witness = component.single_edge_witnesses[0]
    assert witness.closed_walk == ("c", "a", "b", "c")
    assert witness.direct_return_path == ("a", "b", "c")
    assert witness.non_direct_sites[0].line == 23
    assert component.direct_cyclic_scc_count == 0


def test_two_separate_closures():
    graph = {
        "a": {"b"},
        "b": {"c", "d"},
        "c": {"a"},
        "d": {"a"},
    }
    specifications = {
        ("a", "b"): [D],
        ("b", "c"): [D],
        ("b", "d"): [D],
        ("c", "a"): [F],
        ("d", "a"): [F],
    }
    component = _examine(graph, specifications).components[0]
    assert {
        (witness.source, witness.target)
        for witness in component.single_edge_witnesses
    } == {
        ("c", "a"),
        ("d", "a"),
    }
    assert component.non_direct_without_direct_return == ()


def test_two_non_direct_needed():
    component = _examine(
        {"a": {"b"}, "b": {"c"}, "c": {"a"}},
        {
            ("a", "b"): [D],
            ("b", "c"): [F],
            ("c", "a"): [F],
        },
    ).components[0]
    assert component.single_edge_witnesses == ()
    assert component.non_direct_without_direct_return == (
        ("b", "c"),
        ("c", "a"),
    )


def test_direct_cycle_kept():
    component = _examine(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [D],
            ("b", "a"): [D],
        },
    ).components[0]
    assert component.direct_cyclic_scc_count == 1
    assert component.single_edge_witnesses == ()


def test_shortest_lexical_tie():
    graph = {
        "a": {"b", "c"},
        "b": {"z"},
        "c": {"z"},
        "z": {"a"},
    }
    specs = {
        ("a", "b"): [D],
        ("a", "c"): [D],
        ("b", "z"): [D],
        ("c", "z"): [D],
        ("z", "a"): [F],
    }
    component = _examine(graph, specs).components[0]
    assert (
        component.single_edge_witnesses[0].direct_return_path
        == ("a", "b", "z")
    )


def test_guarded_closure_candidate_only():
    result = _examine(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [D],
            ("b", "a"): [G],
        },
    )
    witness = result.components[0].single_edge_witnesses[0]
    assert witness.classification == "GUARDED_TOP_LEVEL_CANDIDATE"
    assert "NOT_RUNTIME" in result.evidence_scope


def test_indirect_closure_candidate_only():
    component = _examine(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [D],
            ("b", "a"): [I],
        },
    ).components[0]
    assert (
        component.single_edge_witnesses[0].classification
        == "INDIRECT_TOP_LEVEL_CANDIDATE"
    )


def test_missing_source_closure_with_empty_sites():
    component = _examine(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [D],
        },
    ).components[0]
    witness = component.single_edge_witnesses[0]
    assert witness.classification == "UNRESOLVED_SOURCE_SITE"
    assert witness.non_direct_sites == ()


def test_self_loop_non_direct():
    component = _examine(
        {"a": {"a"}},
        {("a", "a"): [F]},
    ).components[0]
    witness = component.single_edge_witnesses[0]
    assert witness.closed_walk == ("a", "a")
    assert witness.direct_return_path == ("a",)


def test_two_sccs_independent():
    graph = {
        "a": {"b"},
        "b": {"a"},
        "x": {"y"},
        "y": {"x"},
    }
    specifications = {
        ("a", "b"): [D],
        ("b", "a"): [F],
        ("x", "y"): [D],
        ("y", "x"): [D],
    }
    components = _examine(graph, specifications).components
    assert len(components) == 2
    assert len(components[0].single_edge_witnesses) == 1
    assert components[1].direct_cyclic_scc_count == 1


def test_mismatched_topologies():
    activation, _ = _make(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [D],
            ("b", "a"): [D],
        },
    )
    _, other_sources = _make(
        {"x": {"y"}, "y": {"x"}},
        {
            ("x", "y"): [D],
            ("y", "x"): [D],
        },
    )
    with pytest.raises(ValueError):
        analyze_single_edge_cycle_closures(
            activation,
            other_sources,
        )


def test_mismatched_internal_edge_order():
    activation, evidence = _make(
        {"a": {"b"}, "b": {"a"}},
        {
            ("a", "b"): [D],
            ("b", "a"): [D],
        },
    )
    component = replace(
        evidence.components[0],
        internal_edges=tuple(
            reversed(evidence.components[0].internal_edges)
        ),
    )
    modified = replace(evidence, components=(component,))

    with pytest.raises(ValueError):
        analyze_single_edge_cycle_closures(
            activation,
            modified,
        )


def test_determinism_json_and_no_mutation():
    graph = {"a": {"b"}, "b": {"a"}}
    activation, evidence = _make(
        graph,
        {
            ("a", "b"): [D],
            ("b", "a"): [F],
        },
    )

    before = (repr(activation), repr(evidence), repr(graph))

    first = analyze_single_edge_cycle_closures(
        activation,
        evidence,
    )
    second = analyze_single_edge_cycle_closures(
        activation,
        evidence,
    )

    assert first == second
    json.dumps(asdict(first))

    with pytest.raises(FrozenInstanceError):
        first.components[0].direct_edge_count = 3

    assert (repr(activation), repr(evidence), repr(graph)) == before


def test_empty_no_cycle():
    result = _examine(
        {"a": {"b"}, "b": set()},
        {("a", "b"): [D]},
    )
    assert result.components == ()


def test_long_direct_chain_iterative():
    size = 140
    graph = {
        f"n{i:03d}": {f"n{i+1:03d}"}
        for i in range(size - 1)
    }
    graph[f"n{size-1:03d}"] = {"n000"}

    specifications = {
        (source, target): [D]
        for source, targets in graph.items()
        for target in targets
    }
    specifications[(f"n{size-1:03d}", "n000")] = [F]

    component = _examine(
        graph,
        specifications,
    ).components[0]

    assert len(component.single_edge_witnesses) == 1
    assert len(
        component.single_edge_witnesses[0].closed_walk
    ) == size + 1


def test_invalid_type():
    with pytest.raises(TypeError):
        analyze_single_edge_cycle_closures(None, None)
