"""P1D2B: optional byte and model replay without LIVE authority."""

import hashlib
from dataclasses import replace
from pathlib import Path

from contextor.core.source import SourceSnapshot
from contextor.core.cycle_semantics.contracts import (
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from contextor.core.cycle_semantics.edge_sites import (
    analyze_cyclic_import_sites,
)
from contextor.core.cycle_semantics.conditional_discovery import (
    ConditionalDiscoveryReport,
)
from contextor.core.cycle_semantics.source_proof import (
    assess_optional_scc_source_bytes,
    assess_scc_source_bytes,
)
from tests.test_cycle_semantics_optional_child_scenarios import (
    FILES,
    _case,
)
from tests.test_cycle_semantics_optional_child_evidence import (
    _inputs,
    _build,
)


def _fixture(tmp_path, *, files=None):
    case = _case(tmp_path, files=files)
    parsed, _ = _inputs(tmp_path, case)
    graph, _, imports, root, closures = case
    evidence = _build(case, parsed)

    index = {
        name: source.source_fingerprint
        for name, source in parsed.items()
    }
    members = tuple(sorted({
        name
        for row in closures
        for name in row.members
    }))

    snapshot = CycleSemanticsSnapshot(
        graph_sha256=fingerprint_hard_edges(graph.hard_edges),
        cyclic_modules=members,
        observed_source_fingerprints=tuple(
            (name, index[name]) for name in members
        ),
        source_issues=(),
        coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
        source_snapshot_binding="NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY",
        runtime_execution_status="UNKNOWN_NOT_EVALUATED",
        import_sites=analyze_cyclic_import_sites(
            graph.hard_edges, parsed
        ),
        conditional_discovery=ConditionalDiscoveryReport(
            (), 0, (), 0, "COMPLETE",
        ),
    )

    selected = {
        name
        for row in closures
        for name in row.evidence_source_modules
    }

    source_snapshots = {}
    for name in selected:
        path = (
            tmp_path / "repo"
            / Path(*name.split(".")).with_suffix(".py")
        )
        raw = path.read_bytes()
        source_snapshots[name] = SourceSnapshot(
            raw, hashlib.sha256(raw).hexdigest()
        )

    return (
        graph.hard_edges,
        index,
        snapshot,
        evidence,
        source_snapshots,
        imports,
        root,
        closures,
    )


def _verify(case):
    hard, index, snap, evidence, sources, imports, root, closures = case
    return assess_optional_scc_source_bytes(
        hard,
        index,
        snap,
        evidence,
        sources,
        imports,
        package_root=root,
        source_closures=closures,
    )


def test_optional_bytes_and_model_replay(tmp_path):
    case = _fixture(tmp_path)
    result = _verify(case)

    assert len(result) == 1
    assert result[0].bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
    assert result[0].model_classification == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    )
    assert result[0].authority == (
        "CALLER_SUPPLIED_BYTES_NOT_ATOMICALLY_BOUND_TO_LIVE"
    )
    assert result == _verify(case)


def test_missing_selected_child_is_unavailable(tmp_path):
    case = list(_fixture(tmp_path))
    case[4] = dict(case[4])
    case[4].pop("pkg.child")

    result = _verify(case)
    assert result[0].model_classification == "INDETERMINATE"
    assert result[0].bytes_state == "UNAVAILABLE"
    assert result[0].reason == "OPTIONAL_CAPTURE_SET_MISMATCH"


def test_changed_raw_bytes_rejected(tmp_path):
    case = list(_fixture(tmp_path))
    case[4] = dict(case[4])
    original = case[4]["pkg.child"]
    case[4]["pkg.child"] = SourceSnapshot(
        original.raw + b"# modified\n",
        original.source_fingerprint,
    )

    result = _verify(case)
    assert result[0].reason == (
        "SOURCE_SNAPSHOT_HASH_MISMATCH:pkg.child"
    )
    assert result[0].bytes_state == "EVIDENCE_MISMATCH"


def test_changed_index_fingerprint_rejected(tmp_path):
    case = list(_fixture(tmp_path))
    case[1] = dict(case[1])
    case[1]["pkg.child"] = "0" * 64

    result = _verify(case)
    assert result[0].reason == (
        "SOURCE_INDEX_BYTES_MISMATCH:pkg.child"
    )


def test_forged_component_token_rejected(tmp_path):
    case = list(_fixture(tmp_path))
    evidence = case[3]
    component = replace(
        evidence.components[0],
        evidence_token="0" * 64,
    )
    case[3] = replace(
        evidence, components=(component,)
    )

    result = _verify(case)
    assert result[0].reason == (
        "OPTIONAL_MODEL_OR_TOKEN_REPLAY_MISMATCH"
    )


def test_legacy_evidence_cannot_enter_optional_replay(tmp_path):
    case = list(_fixture(tmp_path))
    case[3] = replace(case[3], source_selection="HARD_ONLY")

    result = _verify(case)
    assert result[0].reason == (
        "OPTIONAL_EVIDENCE_IDENTITY_MISMATCH"
    )


def test_snapshot_lexical_evidence_must_match_bytes(tmp_path):
    case = list(_fixture(tmp_path))

    original_sites = case[2].import_sites
    component = original_sites.components[0]

    assert component.internal_edges
    assert component.internal_edges[0].sites

    forged_edge = replace(
        component.internal_edges[0],
        sites=(),
    )

    forged_component = replace(
        component,
        internal_edges=(
            forged_edge,
            *component.internal_edges[1:],
        ),
    )

    forged_sites = replace(
        original_sites,
        components=(
            forged_component,
            *original_sites.components[1:],
        ),
    )

    case[2] = replace(
        case[2],
        import_sites=forged_sites,
    )

    result = _verify(case)

    assert result[0].reason == (
        "OPTIONAL_LEXICAL_EVIDENCE_MISMATCH"
    )
    assert result[0].bytes_state == "EVIDENCE_MISMATCH"
    assert result[0].model_classification == "INDETERMINATE"


def test_wrong_import_facts_fail_closed(tmp_path):
    case = list(_fixture(tmp_path))
    case[5] = dict(case[5])
    case[5]["pkg.b"] = []

    result = _verify(case)
    assert result[0].model_classification == "INDETERMINATE"
    assert result[0].bytes_state != (
        "BYTE_AST_CONSISTENT_NON_ATOMIC"
    )


def test_existing_byte_verifier_still_rejects_optional(tmp_path):
    case = _fixture(tmp_path)
    hard, index, snap, evidence, sources, _, _, _ = case

    result = assess_scc_source_bytes(
        hard, index, snap, evidence, sources,
    )

    assert all(
        row.bytes_state != "BYTE_AST_CONSISTENT_NON_ATOMIC"
        for row in result
    )


def test_forged_global_source_manifest_fingerprint_rejected(tmp_path):
    case = list(_fixture(tmp_path))
    evidence = case[3]

    case[3] = replace(
        evidence,
        source_manifest_fingerprint="0" * 64,
    )

    result = _verify(case)

    assert len(result) == 1
    assert result[0].model_classification == "INDETERMINATE"
    assert result[0].bytes_state == "EVIDENCE_MISMATCH"
    assert result[0].reason == (
        "OPTIONAL_MODEL_OR_TOKEN_REPLAY_MISMATCH"
    )


def test_unrelated_source_does_not_change_optional_manifest(tmp_path):
    first = _fixture(
        tmp_path / "first",
        files={
            **FILES,
            "pkg/unrelated.py": "value = 1\n",
        },
    )

    second = _fixture(
        tmp_path / "second",
        files={
            **FILES,
            "pkg/unrelated.py": "value = 2\n",
        },
    )

    assert "pkg.unrelated" in first[1]
    assert "pkg.unrelated" in second[1]

    assert "pkg.unrelated" not in first[4]
    assert "pkg.unrelated" not in second[4]

    assert _verify(first)[0].bytes_state == (
        "BYTE_AST_CONSISTENT_NON_ATOMIC"
    )
    assert _verify(second)[0].bytes_state == (
        "BYTE_AST_CONSISTENT_NON_ATOMIC"
    )

    assert (
        first[3].source_manifest_fingerprint
        == second[3].source_manifest_fingerprint
    )

    assert (
        first[3].components[0].evidence_token
        == second[3].components[0].evidence_token
    )
