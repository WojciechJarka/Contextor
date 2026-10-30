import ast
import json
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.scenarios import (
    analyze_cycle_scenarios,
    MAX_COMPONENT_ENTRIES,
)


def _assess(sources, edges):
    return analyze_cycle_scenarios(edges, {k: ast.parse(v) for k, v in sources.items()})


def test_hazard_same_edges_safe_reordering():
    graph = {"a": {"b"}, "b": {"a"}}
    x = _assess(
        {"a": "import b\nvalue=1\n", "b": "import a\nx=a.value\n"}, graph
    )
    assert x.components[0].classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
    assert [s.outcome for s in x.components[0].entry_assessments] == [
        "EARLY_BINDING_HAZARD", "MODEL_PASS"
    ]
    y = _assess(
        {"a": "value=1\nimport b\n", "b": "import a\nx=a.value\n"}, graph
    )
    assert y.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert x.topology == y.topology
    assert y.components[0].coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"


def test_two_independent_sccs():
    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
    sources = {
        "a": "import b\nvalue=1",
        "b": "import a\nx=a.value",
        "x": "import y\na=1",
        "y": "import x\nb=2",
    }
    r = _assess(sources, edges)
    assert [c.classification for c in r.components] == [
        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
    ]


def test_unsupported_inside_component_is_unknown():
    r = _assess(
        {"a": "if True:\n    import b", "b": "import a"},
        {"a": {"b"}, "b": {"a"}},
    )
    assert r.components[0].classification == "INDETERMINATE"
    assert r.components[0].coverage == "PARTIAL_FRESH_MEMBER_ENTRIES"


def test_graph_source_discrepancy_fails_closed():
    r = _assess(
        {"a": "import b\nimport c", "b": "import a", "c": "pass"},
        {"a": {"b"}, "b": {"a"}, "c": set()},
    )
    assert r.components[0].reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
    assert r.components[0].entry_assessments == ()


def test_missing_imported_source_fails_closed():
    r = _assess(
        {"a": "import b", "b": "import a\nimport c"},
        {"a": {"b"}, "b": {"a", "c"}},
    )
    assert r.components[0].reason == "MISSING_OR_INVALID_SOURCE"


def test_unrelated_unsupported_module_is_not_contamination():
    r = _assess(
        {"a": "import b", "b": "import a", "z": "class Dangerous:\n    pass"},
        {"a": {"b"}, "b": {"a"}, "z": set()},
    )
    assert r.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"


def test_external_error_not_mislabeled_internal_cycle():
    r = _assess(
        {
            "a": "import b\nimport c",
            "b": "import a",
            "c": "from d import missing",
            "d": "pass",
        },
        {"a": {"b", "c"}, "b": {"a"}, "c": {"d"}, "d": set()},
    )
    assert r.components[0].classification == "INDETERMINATE"
    assert all(
        x.outcome == "MISSING_EXPORT"
        for x in r.components[0].entry_assessments
    )


def test_acyclic_no_components():
    r = _assess(
        {"a": "import b", "b": "pass"},
        {"a": {"b"}, "b": set()},
    )
    assert r.components == ()
    assert r.topology.total_scc_count == 2


def test_self_loop_is_not_error():
    r = _assess({"a": "import a\nx=1"}, {"a": {"a"}})
    assert r.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"


def test_large_scc_budget_unknown():
    n = MAX_COMPONENT_ENTRIES + 1
    edges = {f"m{i}": {f"m{(i+1)%n}"} for i in range(n)}
    sources = {k: "import " + next(iter(targets)) for k, targets in edges.items()}
    r = _assess(sources, edges)
    assert r.components[0].classification == "INDETERMINATE"
    assert r.components[0].reason == "ENTRY_BUDGET_EXCEEDED"


def test_budget_statements():
    n = 4097
    s = "import b\n" + "pass\n" * n
    r = _assess({"a": s, "b": "import a"}, {"a": {"b"}, "b": {"a"}})
    assert r.components[0].reason == "STATEMENT_BUDGET_EXCEEDED"


def test_determinism_immutability_serialization():
    src = {"a": "import b", "b": "import a"}
    edges = {"a": {"b"}, "b": {"a"}}
    r = _assess(src, edges)
    assert r == _assess(src, edges)
    json.dumps(asdict(r))
    with pytest.raises(Exception):
        r.components[0].classification = "fake"
    assert edges == {"a": {"b"}, "b": {"a"}}


def test_invalid_modules_fail_type_check():
    with pytest.raises(TypeError):
        analyze_cycle_scenarios({"a": {"a"}}, None)


def test_dependency_on_successful_noncyclic_module():
    r = _assess(
        {"a": "import b\nimport c", "b": "import a", "c": "x=1"},
        {"a": {"b", "c"}, "b": {"a"}, "c": set()},
    )
    assert r.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"


def test_downstream_scc_hazard_not_attributed_to_upstream_scc():
    r = _assess(
        {
            "a": "import b\nimport x",
            "b": "import a",
            "x": "import y\nvalue=1",
            "y": "import x\nobserved=x.value",
        },
        {"a": {"b", "x"}, "b": {"a"}, "x": {"y"}, "y": {"x"}},
    )
    assert [c.classification for c in r.components] == [
        "INDETERMINATE",
        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
    ]


def test_ast_budget_one_large_statement(monkeypatch):
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.scenarios.MAX_CLOSURE_AST_NODES",
        256,
    )
    literal = ",".join("1" for _ in range(260))
    r = _assess(
        {"a": "import b\nx=[" + literal + "]", "b": "import a"},
        {"a": {"b"}, "b": {"a"}},
    )
    assert r.components[0].reason == "AST_NODE_BUDGET_EXCEEDED"


def test_expanded_ast_capacity_does_not_accept_unsupported_source():
    literal = ",".join("1" for _ in range(17000))
    r = _assess(
        {"a": "import b\nx=[" + literal + "]", "b": "import a"},
        {"a": {"b"}, "b": {"a"}},
    )
    component = r.components[0]

    assert component.reason != "AST_NODE_BUDGET_EXCEEDED"
    assert component.classification == "INDETERMINATE"
