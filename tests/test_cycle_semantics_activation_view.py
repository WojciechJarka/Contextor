from dataclasses import asdict, FrozenInstanceError
import json

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
    analyze_cycle_activation_view as analyze,
)


def _site(
    activation="MODULE_TOP_LEVEL",
    kind="FROM_BASE",
    ordinal=0,
):
    return LexicalEdgeSite(
        ordinal,
        ordinal + 1,
        0,
        "IMPORT_FROM",
        kind,
        "b",
        None,
        (),
        (),
        activation,
    )


def _report(graph, data):
    topology = analyze_import_cycle_topology(graph)
    components = []

    for scc in topology.cyclic_components:
        edges = []

        for src, dst in scc.internal_edges:
            specs = data.get((src, dst))

            if specs is None:
                edges.append(
                    HardEdgeSiteEvidence(
                        src,
                        dst,
                        "SOURCE_MISSING_OR_INVALID",
                        (),
                    )
                )

            elif specs:
                sites = tuple(
                    _site(*item)
                    for item in specs
                )

                edges.append(
                    HardEdgeSiteEvidence(
                        src,
                        dst,
                        "LEXICAL_CANDIDATES",
                        sites,
                    )
                )

            else:
                edges.append(
                    HardEdgeSiteEvidence(
                        src,
                        dst,
                        "NO_MATCHING_LEXICAL_SITE",
                        (),
                    )
                )

        components.append(
            SCCImportSiteEvidence(
                scc.members,
                tuple(edges),
                sum(
                    x.status == "LEXICAL_CANDIDATES"
                    for x in edges
                ),
                sum(
                    x.status != "LEXICAL_CANDIDATES"
                    for x in edges
                ),
            )
        )

    return CyclicImportSiteReport(
        topology,
        tuple(components),
    )


def test_direct_two_node_cycle_remains_candidate():
    result = analyze(
        _report(
            {"a": {"b"}, "b": {"a"}},
            {
                ("a", "b"): [()],
                ("b", "a"): [()],
            },
        )
    )

    component = result.components[0]

    assert len(
        component.unguarded_direct_topology.cyclic_components
    ) == 1

    assert component.unguarded_direct_edges == (
        ("a", "b"),
        ("b", "a"),
    )

    assert all(
        edge.classification == "UNGUARDED_DIRECT_CANDIDATE"
        for edge in component.edges
    )


def test_function_scoped_reverse_does_not_enter_direct_subgraph():
    result = analyze(
        _report(
            {"a": {"b"}, "b": {"a"}},
            {
                ("a", "b"): [
                    ("FUNCTION_SCOPED", "FROM_BASE", 0)
                ],
                ("b", "a"): [()],
            },
        )
    )

    component = result.components[0]

    assert len(result.structural_topology.cyclic_components) == 1

    assert len(
        component.unguarded_direct_topology.cyclic_components
    ) == 0

    assert (
        component.edges[0].classification
        == "CALL_DEPENDENT_CANDIDATE"
    )

    assert result.evidence_scope.endswith(
        "NOT_RUNTIME_SAFETY"
    )


def test_call_dependent_cycle_not_certified_safe():
    result = analyze(
        _report(
            {"a": {"b"}, "b": {"a"}},
            {
                ("a", "b"): [
                    ("FUNCTION_SCOPED", "FROM_BASE", 0)
                ],
                ("b", "a"): [()],
            },
        )
    )

    assert "SAFE" not in [
        edge.classification
        for edge in result.components[0].edges
    ]

    assert len(result.components[0].edges) == 2


def test_indirect_parent_candidate_is_not_unguarded_direct():
    result = analyze(
        _report(
            {"p": {"c"}, "c": {"p"}},
            {
                ("p", "c"): [
                    ("MODULE_TOP_LEVEL", "OPTIONAL_FROM_CHILD", 0)
                ],
                ("c", "p"): [
                    ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER", 0)
                ],
            },
        )
    )

    component = result.components[0]

    assert all(
        edge.classification == "INDIRECT_TOP_LEVEL_CANDIDATE"
        for edge in component.edges
    )

    assert not component.unguarded_direct_edges

    assert all(
        edge.indirect_candidate_count == 1
        for edge in component.edges
    )


def test_guarded_top_level_not_promoted():
    result = analyze(
        _report(
            {"a": {"b"}, "b": {"a"}},
            {
                ("a", "b"): [
                    ("GUARDED_TOP_LEVEL", "FROM_BASE", 0)
                ],
                ("b", "a"): [()],
            },
        )
    )

    assert (
        result.components[0].edges[0].classification
        == "GUARDED_TOP_LEVEL_CANDIDATE"
    )

    assert len(
        result.components[0]
        .unguarded_direct_topology.cyclic_components
    ) == 0


def test_other_scoped_class_body_not_mistaken_for_deferral():
    result = analyze(
        _report(
            {"a": {"b"}, "b": {"a"}},
            {
                ("a", "b"): [
                    ("OTHER_SCOPED", "FROM_BASE", 0)
                ],
                ("b", "a"): [()],
            },
        )
    )

    assert (
        result.components[0].edges[0].classification
        == "OTHER_SCOPE_CANDIDATE"
    )


def test_mixed_eager_and_function_sites_preserved():
    result = analyze(
        _report(
            {"a": {"b"}, "b": {"a"}},
            {
                ("a", "b"): [
                    (),
                    ("FUNCTION_SCOPED", "FROM_BASE", 1),
                ],
                ("b", "a"): [()],
            },
        )
    )

    component = result.components[0]
    edge = component.edges[0]

    assert (
        edge.site_count,
        edge.unguarded_direct_count,
        edge.function_scoped_count,
    ) == (2, 1, 1)

    assert (
        edge.classification
        == "UNGUARDED_DIRECT_CANDIDATE"
    )

    assert len(
        component.unguarded_direct_topology.cyclic_components
    ) == 1


def test_missing_source_and_unmatched_remain_explicit():
    result = analyze(
        _report(
            {"a": {"b"}, "b": {"a"}},
            {
                ("a", "b"): [],
                ("b", "a"): None,
            },
        )
    )

    component = result.components[0]

    assert len(component.edges) == 2
    assert component.unresolved_edges == 2

    assert {
        edge.source_status
        for edge in component.edges
    } == {
        "NO_MATCHING_LEXICAL_SITE",
        "SOURCE_MISSING_OR_INVALID",
    }


def test_indirect_function_counts_as_call_dependent():
    result = analyze(
        _report(
            {"a": {"b"}, "b": {"a"}},
            {
                ("a", "b"): [
                    ("FUNCTION_SCOPED", "PARENT_INITIALIZER", 0)
                ],
                ("b", "a"): [()],
            },
        )
    )

    edge = result.components[0].edges[0]

    assert (
        edge.function_scoped_count,
        edge.indirect_candidate_count,
    ) == (1, 1)

    assert (
        edge.classification
        == "CALL_DEPENDENT_CANDIDATE"
    )


def test_multiple_sccs_preserved_separately():
    graph = {
        "a": {"b"},
        "b": {"a"},
        "x": {"y"},
        "y": {"x"},
    }

    data = {
        ("a", "b"): [()],
        ("b", "a"): [
            ("FUNCTION_SCOPED", "FROM_BASE", 0)
        ],
        ("x", "y"): [()],
        ("y", "x"): [()],
    }

    result = analyze(_report(graph, data))

    assert len(result.components) == 2

    assert tuple(
        component.members
        for component in result.components
    ) == (
        ("a", "b"),
        ("x", "y"),
    )

    assert [
        len(
            component.unguarded_direct_topology.cyclic_components
        )
        for component in result.components
    ] == [0, 1]


def test_self_loop_supported():
    result = analyze(
        _report(
            {"a": {"a"}},
            {("a", "a"): [()]},
        )
    )

    assert len(
        result.components[0]
        .unguarded_direct_topology.cyclic_components
    ) == 1


def test_empty_no_cycles():
    result = analyze(
        _report(
            {"a": {"b"}, "b": set()},
            {},
        )
    )

    assert result.components == ()


def test_deterministic_serializable_immutable_input_unchanged():
    graph = {
        "a": {"b"},
        "b": {"a"},
    }

    projection = _report(
        graph,
        {
            ("a", "b"): [()],
            ("b", "a"): [()],
        },
    )

    first = analyze(projection)
    second = analyze(projection)

    assert first == second

    json.dumps(asdict(first))

    with pytest.raises(FrozenInstanceError):
        first.components[0].unresolved_edges = 99

    assert graph == {
        "a": {"b"},
        "b": {"a"},
    }

    assert projection == _report(
        graph,
        {
            ("a", "b"): [()],
            ("b", "a"): [()],
        },
    )


def test_invalid_input():
    with pytest.raises(TypeError):
        analyze(None)
