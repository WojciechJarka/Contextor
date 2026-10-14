import ast
import hashlib
import json
from dataclasses import asdict

import pytest

from contextor.core.source import ParsedSourceInput
from contextor.core.cycle_semantics.evidence import (
    build_source_bound_cycle_evidence as build,
    compare_source_bound_cycle_evidence as compare,
)


def _sources(**source_map):
    return {
        name: ParsedSourceInput(
            ast.parse(text),
            hashlib.sha256(text.encode()).hexdigest(),
        )
        for name, text in source_map.items()
    }


def _fixture(order=False):
    edges = {"a": {"b"}, "b": {"a"}}
    if order:
        return build(edges, _sources(
            a="value=1\nimport b\n",
            b="import a\nx=a.value\n",
        ))
    return build(edges, _sources(
        a="import b\nvalue=1\n",
        b="import a\nx=a.value\n",
    ))


def test_unmodified_deterministic_and_immutable():
    a = _fixture()
    assert a == _fixture()
    assert compare(a, a) == ()
    assert a.components[0].classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
    with pytest.raises(Exception):
        a.components[0].classification = "fake"
    json.dumps(asdict(a))


def test_same_graph_semantic_flip_visible():
    a, b = _fixture(), _fixture(True)
    assert a.graph_fingerprint == b.graph_fingerprint
    assert a.source_manifest_fingerprint != b.source_manifest_fingerprint
    assert a.components[0].evidence_token != b.components[0].evidence_token
    changes = compare(a, b)
    assert len(changes) == 1
    assert changes[0].members == ("a", "b")
    assert changes[0].change == "MODEL_CLASSIFICATION_CHANGED"
    assert changes[0].before == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
    assert changes[0].after == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert all(c.change != "RESOLVED" for c in changes)
    assert compare(b, a)[0].change == "MODEL_CLASSIFICATION_CHANGED"


def test_comment_only_edit_revises_evidence_not_outcome():
    edges = {"a": {"b"}, "b": {"a"}}
    before = build(edges, _sources(a="import b\nx=1\n", b="import a\ny=2\n"))
    after = build(edges, _sources(a="import b\nx=1\n# note\n", b="import a\ny=2\n"))
    assert before.components[0].classification == after.components[0].classification
    assert compare(before, after)[0].change == "EVIDENCE_REVISED"


def test_unrelated_source_edit_does_not_spam_scc_evidence():
    edges = {"a": {"b"}, "b": {"a"}, "unrelated": set()}
    old = build(edges, _sources(a="import b", b="import a", unrelated="x=1"))
    new = build(edges, _sources(a="import b", b="import a", unrelated="x=2"))
    assert old.source_manifest_fingerprint != new.source_manifest_fingerprint
    assert old.components[0].evidence_token == new.components[0].evidence_token
    assert compare(old, new) == ()


def test_reachable_dependency_change_revises_evidence():
    edges = {"a": {"b", "dep"}, "b": {"a"}, "dep": set()}
    old = build(edges, _sources(a="import b\nimport dep", b="import a", dep="x=1"))
    new = build(edges, _sources(a="import b\nimport dep", b="import a", dep="x=2"))
    assert compare(old, new)[0].change == "EVIDENCE_REVISED"


def test_graph_source_mismatch_fails_closed_and_transition():
    edges = {"a": {"b"}, "b": {"a"}}
    old = build(edges, _sources(a="import b", b="import a"))
    new = build(edges, _sources(a="import b\nimport unknown", b="import a"))
    assert new.components[0].classification == "INDETERMINATE"
    assert new.components[0].reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
    assert compare(old, new)[0].change == "MODEL_CLASSIFICATION_CHANGED"


def test_missing_source_and_addition():
    edges = {"a": {"b"}, "b": {"a"}}
    old = build(edges, _sources(a="import b"))
    new = build(edges, _sources(a="import b", b="import a"))
    assert old.components[0].source_signatures[1] == ("b", "MISSING", "MISSING")
    assert old.components[0].classification == "INDETERMINATE"
    assert new.components[0].classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert compare(old, new)[0].change == "MODEL_CLASSIFICATION_CHANGED"


def test_graph_internal_edge_change_reclassifies():
    sources = _sources(a="import b", b="import a")
    before = build({"a": {"b"}, "b": {"a"}}, sources)
    after = build({"a": {"b"}, "b": set()}, sources)
    c = compare(before, after)[0]
    assert c.change == "STRUCTURE_REMOVED"


def test_two_independent_sccs_only_one_changed():
    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
    old = build(edges, _sources(
        a="import b", b="import a", x="import y", y="import x",
    ))
    new = build(edges, _sources(
        a="import b\n# extra", b="import a", x="import y", y="import x",
    ))
    changes = compare(old, new)
    assert len(changes) == 1 and changes[0].members == ("a", "b")


def test_ast_tamper_even_if_spoofed_same_raw_hash():
    edges = {"a": {"b"}, "b": {"a"}}
    sources = _sources(a="import b", b="import a")
    before = build(edges, sources)
    sources["a"].tree.body[0].lineno = 12
    after = build(edges, sources)
    assert before.source_manifest_fingerprint != after.source_manifest_fingerprint
    assert compare(before, after)[0].change == "EVIDENCE_REVISED"


def test_no_components():
    e = build(
        {"a": {"b"}, "b": set()},
        _sources(a="import b", b="pass"),
    )
    assert e.components == () and compare(e, e) == ()


def test_bad_input_fail_closed():
    with pytest.raises(TypeError):
        build({"a": {"a"}}, None)
    with pytest.raises(TypeError):
        build({"a": {"a"}}, {"a": ast.parse("import a")})
    with pytest.raises(ValueError):
        build({"a": {"a"}}, {
            "a": ParsedSourceInput(ast.parse("import a"), "foo")
        })
    with pytest.raises(TypeError):
        compare(None, None)


def test_snapshot_only_authority_no_warning_action():
    x = _fixture()
    assert x.authority == "SNAPSHOT_ONLY_NOT_LIVE_FRESHNESS"
    assert x.scenarios.evidence_scope == "SCENARIO_MODEL_NOT_RUNTIME_CERTIFICATION"
    assert "SAFE" not in x.components[0].classification
