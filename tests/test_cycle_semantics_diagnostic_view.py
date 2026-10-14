"""Structural/lexical evidence digest regressions, never safety verdicts."""

import json
from dataclasses import FrozenInstanceError, asdict, replace

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


C17_DIRECT_SITE = ("MODULE_TOP_LEVEL", "FROM_BASE")
C17_FUNCTION_SITE = ("FUNCTION_SCOPED", "FROM_BASE")
C17_GUARDED_SITE = ("GUARDED_TOP_LEVEL", "FROM_BASE")
C17_INDIRECT_SITE = ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER")


def _pipeline(graph, specs):
    topology = analyze_import_cycle_topology(graph)
    components = []

    for structural in topology.cyclic_components:
        edges = []

        for source, target in structural.internal_edges:
            specification = specs.get((source, target), None)

            if specification is None:
                edges.append(
                    HardEdgeSiteEvidence(
                        source, target,
                        "SOURCE_MISSING_OR_INVALID", (),
                    )
                )
            elif not specification:
                edges.append(
                    HardEdgeSiteEvidence(
                        source, target,
                        "NO_MATCHING_LEXICAL_SITE", (),
                    )
                )
            else:
                lexical = tuple(
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
                    for ordinal, (scope, kind) in enumerate(specification)
                )
                edges.append(
                    HardEdgeSiteEvidence(
                        source, target,
                        "LEXICAL_CANDIDATES", lexical,
                    )
                )

        components.append(
            SCCImportSiteEvidence(
                members=structural.members,
                internal_edges=tuple(edges),
                matched_edge_count=sum(
                    item.status == "LEXICAL_CANDIDATES"
                    for item in edges
                ),
                unresolved_edge_count=sum(
                    item.status != "LEXICAL_CANDIDATES"
                    for item in edges
                ),
            )
        )

    sites = CyclicImportSiteReport(
        topology, tuple(components),
    )
    activation = analyze_cycle_activation_view(sites)
    closures = analyze_single_edge_cycle_closures(
        activation, sites,
    )
    return sites, activation, closures


def _digest(graph, specs):
    return build_cycle_evidence_digest(
        *_pipeline(graph, specs)
    )


def test_direct_cycle_is_still_structural():
    result = _digest(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_DIRECT_SITE]},
    )
    component = result.components[0]

    assert component.category == (
        "UNGUARDED_DIRECT_CYCLIC_SUBGRAPH"
    )
    assert component.structural_edge_count == 2
    assert component.direct_candidate_edge_count == 2
    assert len(component.direct_cyclic_components) == 1
    assert len(component.edges) == 2
    assert component.single_edge_closures == ()


def test_function_local_edge_retains_closure_and_sites():
    result = _digest(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
    )
    component = result.components[0]

    assert component.category == (
        "ACYCLIC_DIRECT_SUBGRAPH_WITH_SINGLE_EDGE_CLOSURES"
    )
    assert component.direct_candidate_edge_count == 1
    assert component.non_direct_candidate_edge_count == 1

    row = next(
        item for item in component.edges
        if (item.source, item.target) == ("b", "a")
    )
    assert not row.in_direct_candidate_graph
    assert row.activation.classification == (
        "CALL_DEPENDENT_CANDIDATE"
    )
    assert row.lexical.sites[0].activation_scope == (
        "FUNCTION_SCOPED"
    )
    assert row.single_edge_closure.closed_walk == (
        "b", "a", "b"
    )


def test_multiple_nondirect_edges_without_one_edge_return():
    component = _digest(
        {"a": {"b"}, "b": {"c"}, "c": {"a"}},
        {
            ("a", "b"): [C17_DIRECT_SITE],
            ("b", "c"): [C17_FUNCTION_SITE],
            ("c", "a"): [C17_FUNCTION_SITE],
        },
    ).components[0]

    assert component.category == (
        "ACYCLIC_DIRECT_SUBGRAPH_NO_SINGLE_EDGE_CLOSURE"
    )
    assert component.structural_edge_count == 3
    assert component.single_edge_closures == ()
    assert component.non_direct_candidate_edge_count == 2
    assert component.non_direct_without_direct_return == (
        ("b", "c"), ("c", "a")
    )


def test_guarded_candidate_keeps_uncertainty():
    component = _digest(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_GUARDED_SITE]},
    ).components[0]

    witness = component.single_edge_closures[0]
    assert witness.classification == (
        "GUARDED_TOP_LEVEL_CANDIDATE"
    )
    assert component.runtime_execution_status == (
        "UNKNOWN_NOT_EVALUATED"
    )


def test_indirect_package_candidate_keeps_uncertainty():
    component = _digest(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_INDIRECT_SITE]},
    ).components[0]

    assert component.single_edge_closures[0].classification == (
        "INDIRECT_TOP_LEVEL_CANDIDATE"
    )
    assert component.direct_candidate_edge_count == 1


def test_missing_lexical_evidence_is_not_dropped():
    component = _digest(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE]},
    ).components[0]

    assert component.structural_edge_count == 2
    assert component.matched_edge_count == 1
    assert component.unresolved_edge_count == 1
    assert len(component.edges) == 2

    missing = next(
        item for item in component.edges
        if item.source == "b"
    )
    assert missing.lexical.status == (
        "SOURCE_MISSING_OR_INVALID"
    )
    assert missing.single_edge_closure is not None


def test_unmatched_lexical_site_preserved():
    component = _digest(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): []},
    ).components[0]

    assert any(
        row.lexical.status == "NO_MATCHING_LEXICAL_SITE"
        for row in component.edges
    )
    assert component.unresolved_edge_count == 1


def test_two_independent_sccs_remain_distinct():
    component_one, component_two = _digest(
        {
            "a": {"b"}, "b": {"a"},
            "x": {"y"}, "y": {"x"},
        },
        {
            ("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE],
            ("x", "y"): [C17_DIRECT_SITE], ("y", "x"): [C17_DIRECT_SITE],
        },
    ).components

    assert component_one.members == ("a", "b")
    assert component_two.members == ("x", "y")
    assert len(component_one.single_edge_closures) == 1
    assert len(component_two.direct_cyclic_components) == 1


@pytest.mark.parametrize(
    "site",
    [C17_DIRECT_SITE, C17_FUNCTION_SITE],
)
def test_self_loop_preserved(site):
    component = _digest(
        {"a": {"a"}},
        {("a", "a"): [site]},
    ).components[0]

    assert component.structural_kind == "SELF_LOOP"
    assert component.structural_edge_count == 1
    assert len(component.edges) == 1


def test_mismatched_activation_rejected():
    sites, activation, closures = _pipeline(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
    )

    view = activation.components[0]
    changed_edge = replace(
        view.edges[0],
        classification="CALL_DEPENDENT_CANDIDATE",
    )
    changed_view = replace(
        view,
        edges=(changed_edge,) + view.edges[1:],
    )
    invalid = replace(
        activation,
        components=(changed_view,),
    )

    with pytest.raises(ValueError):
        build_cycle_evidence_digest(
            sites, invalid, closures,
        )


def test_mismatched_closure_rejected():
    sites, activation, closures = _pipeline(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
    )

    component = closures.components[0]
    witness = component.single_edge_witnesses[0]
    wrong = replace(
        witness,
        direct_return_path=("a",),
    )
    invalid_component = replace(
        component,
        single_edge_witnesses=(wrong,),
    )
    invalid = replace(
        closures,
        components=(invalid_component,),
    )

    with pytest.raises(ValueError):
        build_cycle_evidence_digest(
            sites, activation, invalid,
        )


def test_mismatched_site_topology_rejected():
    sites, activation, closures = _pipeline(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
    )

    wrong_component = replace(
        sites.components[0],
        internal_edges=tuple(
            reversed(sites.components[0].internal_edges)
        ),
    )
    invalid = replace(
        sites,
        components=(wrong_component,),
    )

    with pytest.raises(ValueError):
        build_cycle_evidence_digest(
            invalid, activation, closures,
        )


def test_mismatched_site_counts_rejected():
    sites, activation, closures = _pipeline(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
    )
    wrong = replace(
        sites.components[0],
        matched_edge_count=0,
    )
    invalid = replace(
        sites,
        components=(wrong,),
    )

    with pytest.raises(ValueError):
        build_cycle_evidence_digest(
            invalid, activation, closures,
        )


def test_determinism_immutability_and_json():
    inputs = _pipeline(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
    )
    before = tuple(repr(item) for item in inputs)

    first = build_cycle_evidence_digest(*inputs)
    second = build_cycle_evidence_digest(*inputs)

    assert first == second
    json.dumps(asdict(first))

    with pytest.raises(FrozenInstanceError):
        first.components[0].structural_edge_count = 9

    assert before == tuple(repr(item) for item in inputs)
    assert first.source_snapshot_binding == (
        "NOT_VERIFIED_BY_DIGEST"
    )


def test_no_cycles_empty_digest():
    result = _digest(
        {"a": {"b"}, "b": set()},
        {},
    )
    assert result.components == ()
    assert result.structural_topology.cyclic_components == ()


def test_bad_argument_types():
    with pytest.raises(TypeError):
        build_cycle_evidence_digest(None, None, None)

    sites, activation, closures = _pipeline(
        {"a": {"b"}, "b": {"a"}},
        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
    )

    with pytest.raises(TypeError):
        build_cycle_evidence_digest(
            sites, None, closures,
        )

    with pytest.raises(TypeError):
        build_cycle_evidence_digest(
            sites, activation, None,
        )
