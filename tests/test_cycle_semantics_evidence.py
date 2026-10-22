import ast
import hashlib
import json
from dataclasses import asdict, replace

import pytest

from contextor.core.source import ParsedSourceInput
from contextor.core.cycle_semantics.evidence import (
    SCCModelEvidenceAssessment,
    assess_index_bound_scc_models as assess,
    build_source_bound_cycle_evidence as build,
    compare_source_bound_cycle_evidence as compare,
)
from contextor.core.cycle_semantics.contracts import (
    CycleSemanticsSnapshot, fingerprint_hard_edges,
)
from contextor.core.cycle_semantics.edge_sites import analyze_cyclic_import_sites
from contextor.core.cycle_semantics.conditional_discovery import ConditionalDiscoveryReport


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


def _bound(edges, sources):
    parsed = _sources(**sources)
    evidence = build(edges, parsed)
    topology = evidence.scenarios.topology
    cyclic = tuple(sorted(
        name for component in topology.cyclic_components for name in component.members
    ))
    index = {name: source.source_fingerprint for name, source in parsed.items()}
    snapshot = CycleSemanticsSnapshot(
        graph_sha256=fingerprint_hard_edges(edges),
        cyclic_modules=cyclic,
        observed_source_fingerprints=tuple(
            (name, index[name]) for name in cyclic
        ),
        source_issues=(),
        coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
        source_snapshot_binding="NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY",
        runtime_execution_status="UNKNOWN_NOT_EVALUATED",
        import_sites=analyze_cyclic_import_sites(edges, parsed),
        conditional_discovery=ConditionalDiscoveryReport(
            (), 0, (), 0, "COMPLETE",
        ),
    )
    return index, snapshot, evidence


PAIR = {"a": {"b"}, "b": {"a"}}
PASS = {"a": "import b\nx=1", "b": "import a\ny=2"}
HAZARD = {"a": "import b\nvalue=1", "b": "from a import value"}


def _one(edges=PAIR, sources=PASS):
    index, snapshot, evidence = _bound(edges, sources)
    result = assess(edges, index, snapshot, evidence)
    return result, index, snapshot, evidence


def test_p0_t01_mutual_import_all_entries_pass():
    result, _, _, _ = _one()
    assert result == (SCCModelEvidenceAssessment(
        ("a", "b"), "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
        "DECLARED_INPUTS_CONSISTENT", None,
    ),)
    assert result[0].authority == "SNAPSHOT_MODEL_ONLY_NOT_LIVE_CERTIFIED"


def test_p0_t02_early_from_import_hazard():
    result, _, _, _ = _one(sources=HAZARD)
    assert result[0].model_classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
    assert result[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"


def test_p0_t03_symbol_bound_before_read():
    sources = {"a": "value=1\nimport b", "b": "import a\nx=a.value"}
    result, _, _, _ = _one(sources=sources)
    assert result[0].model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    assert result[0].evidence_state == "DECLARED_INPUTS_CONSISTENT"


def test_p0_t04_same_graph_changed_binding_order():
    bad = _one(sources={"a": "import b\nvalue=1", "b": "import a\nx=a.value"})[0]
    good = _one(sources={"a": "value=1\nimport b", "b": "import a\nx=a.value"})[0]
    assert bad[0].model_classification == "MODEL_INTERNAL_EARLY_BINDING_HAZARD"
    assert good[0].model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"


def test_p0_t05_raw_source_fingerprint_mismatch():
    _, index, snapshot, evidence = _one()
    index["a"] = "0" * 64
    result = assess(PAIR, index, snapshot, evidence)
    assert result[0].model_classification == "INDETERMINATE"
    assert result[0].evidence_state == "EVIDENCE_MISMATCH"
    assert result[0].reason == "SOURCE_INDEX_FINGERPRINT_MISMATCH:a"
    malformed = replace(evidence.components[0],
                        source_signatures=(("a",),))
    bad_evidence = replace(evidence, components=(malformed,))
    assert assess(PAIR, index, snapshot, bad_evidence)[0].reason == "MALFORMED_SOURCE_SIGNATURES"


def test_p0_t06_missing_closure_fingerprint():
    _, index, snapshot, evidence = _one()
    del index["b"]
    result = assess(PAIR, index, snapshot, evidence)
    assert result[0].evidence_state == "EVIDENCE_MISMATCH"
    assert result[0].reason == "SOURCE_INDEX_FINGERPRINT_MISMATCH:b"


def test_p0_t07_graph_fingerprint_mismatch():
    _, index, snapshot, evidence = _one()
    bad = replace(snapshot, graph_sha256="0" * 64)
    assert assess(PAIR, index, bad, evidence)[0].reason == "SNAPSHOT_GRAPH_FINGERPRINT_MISMATCH"
    bad_evidence = replace(evidence, graph_fingerprint="0" * 64)
    assert assess(PAIR, index, snapshot, bad_evidence)[0].reason == "SOURCE_GRAPH_FINGERPRINT_MISMATCH"


def test_p0_t08_scc_membership_and_internal_edge_identity():
    _, index, snapshot, evidence = _one()
    component = evidence.scenarios.components[0]
    altered = replace(component, internal_edges=())
    bad_report = replace(evidence.scenarios, components=(altered,))
    result = assess(PAIR, index, snapshot, replace(evidence, scenarios=bad_report))
    assert result[0].reason == "SCENARIO_INTERNAL_EDGES_MISMATCH"
    duplicate = replace(evidence, components=(evidence.components[0], evidence.components[0]))
    assert assess(PAIR, index, snapshot, duplicate)[0].reason == "SCC_COMPONENT_IDENTITY_MISMATCH"
    tampered_token = replace(evidence.components[0], evidence_token="0" * 64)
    assert assess(PAIR, index, snapshot, replace(evidence, components=(tampered_token,)))[0].reason == "COMPONENT_EVIDENCE_TOKEN_MISMATCH"


def test_p0_t09_partial_source_cohort():
    _, index, snapshot, evidence = _one()
    partial = replace(snapshot,
        observed_source_fingerprints=(snapshot.observed_source_fingerprints[0],),
        coverage_status="PARTIAL_SOURCE_EVIDENCE",
    )
    result = assess(PAIR, index, partial, evidence)
    assert result[0].model_classification == "INDETERMINATE"
    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"


def test_p0_t10_source_issue_cannot_pass():
    _, index, snapshot, evidence = _one()
    issue = replace(snapshot, source_issues=(("a", "SOURCE_CHANGED_DURING_READ"),),
                    coverage_status="PARTIAL_SOURCE_EVIDENCE")
    result = assess(PAIR, index, issue, evidence)
    assert result[0].model_classification == "INDETERMINATE"
    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"


def test_p0_t11_unknown_entry_in_scc():
    _, index, snapshot, evidence = _one()
    component = evidence.scenarios.components[0]
    entries = (replace(component.entry_assessments[0], outcome="UNKNOWN"),
               component.entry_assessments[1])
    changed = replace(component, entry_assessments=entries)
    report = replace(evidence.scenarios, components=(changed,))
    source = replace(evidence, scenarios=report)
    result = assess(PAIR, index, snapshot, source)
    assert result[0].model_classification == "INDETERMINATE"
    assert result[0].evidence_state == "INCOMPLETE_EVIDENCE"


def test_p0_t12_independent_sccs_do_not_share_pass():
    edges = {"a": {"b"}, "b": {"a"}, "x": {"y"}, "y": {"x"}}
    sources = dict(PASS, x="import y\nvalue=1", y="from x import value")
    result, _, _, _ = _one(edges, sources)
    assert [(r.members, r.model_classification) for r in result] == [
        (("a", "b"), "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"),
        (("x", "y"), "MODEL_INTERNAL_EARLY_BINDING_HAZARD"),
    ]


def test_p0_t13_self_loop():
    result, _, _, _ = _one({"a": {"a"}}, {"a": "import a\nx=1"})
    assert result[0].members == ("a",)
    assert result[0].model_classification == "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"


def test_p0_t14_no_cyclic_scc():
    result, _, _, _ = _one({"a": {"b"}, "b": set()}, {"a": "import b", "b": "pass"})
    assert result == ()


def test_p0_t15_deterministic_without_input_mutation():
    edges = {"a": {"b"}, "b": {"a"}}
    _, index, snapshot, evidence = _one(edges)
    before = (repr(edges), repr(index), repr(snapshot), repr(evidence))
    first = assess(edges, index, snapshot, evidence)
    assert first == assess(edges, index, snapshot, evidence)
    assert before == (repr(edges), repr(index), repr(snapshot), repr(evidence))
    json.dumps(asdict(first[0]))


def test_p0_t16_no_warning_suppression_or_public_api_change():
    result, _, _, _ = _one()
    assert result[0].authority == "SNAPSHOT_MODEL_ONLY_NOT_LIVE_CERTIFIED"
    assert set(asdict(result[0])) == {
        "members", "model_classification", "evidence_state", "reason", "authority",
    }
    assert not any("SAFE" in value or "warning" in value.lower()
                   for value in asdict(result[0]).values() if isinstance(value, str))
