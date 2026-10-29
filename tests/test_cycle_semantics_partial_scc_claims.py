"""Prepared partial SCC declarations have no publication authority."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.cycle_semantics.partial_scc_claims import (
    PARTIAL_SCC_CLAIMS_AUTHORITY,
    PARTIAL_SCC_CLAIMS_VERSION,
    PreparedPartialSCCClaims,
    validate_partial_scc_claims,
)
from contextor.core.cycle_semantics.warning_eligibility import (
    _verified_model_pass_cycle_paths,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.live_state.store import save_snapshot
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD,
    PASS_AND_UNKNOWN,
    TWO_PASS,
    _prepare,
    _real_pipeline,
    _repo,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _case(tmp_path, sources=PASS_AND_UNKNOWN, selected=None):
    root = _repo(tmp_path, sources)
    if selected is None:
        index, graph, snapshot = _real_pipeline(root)
    else:
        index, graph, snapshot = _real_pipeline(root, selected=selected)
    preparation = _prepare(index, graph, snapshot)
    return graph.hard_edges, snapshot, preparation


def _validated(edges, snapshot, preparation):
    return validate_partial_scc_claims(edges, snapshot, preparation)


def _replace_component(preparation, position, **changes):
    items = list(preparation.component_preparations)
    items[position] = replace(items[position], **changes)
    return replace(preparation, component_preparations=tuple(items))


def test_t01_real_pass_indeterminate_preserves_both_claims(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    result = _validated(edges, snapshot, preparation)
    assert type(result) is PreparedPartialSCCClaims
    assert result.graph_sha256 == snapshot.graph_sha256
    assert result.components == preparation.component_preparations
    assert result.version == PARTIAL_SCC_CLAIMS_VERSION
    assert result.authority == PARTIAL_SCC_CLAIMS_AUTHORITY
    assert tuple(item.preparation_state for item in result.components) == (
        "PREPARED_UNPUBLISHED", "UNAVAILABLE",
    )


def test_t02_real_pass_hazard_keeps_distinct_complete_claims(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path, PASS_AND_HAZARD)
    result = _validated(edges, snapshot, preparation)
    assert type(result) is PreparedPartialSCCClaims
    assert tuple(item.model_classification for item in result.components) == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
    )


def test_t03_real_two_pass_keeps_canonical_order(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path, TWO_PASS)
    result = _validated(edges, snapshot, preparation)
    assert type(result) is PreparedPartialSCCClaims
    assert tuple(item.members for item in result.components) == (
        ("a", "b"), ("x", "y"),
    )


def test_t04_missing_original_capture_cannot_infer_claim(tmp_path, isolated_dirs):
    root = _repo(tmp_path, TWO_PASS)
    index, graph, snapshot = _real_pipeline(root, selected=frozenset())
    preparation = _prepare(index, graph, snapshot)
    assert preparation.component_preparations == ()
    assert _validated(graph.hard_edges, snapshot, preparation) is None


def test_t05_graph_sha_mismatch_rejected(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    assert _validated(edges, replace(snapshot, graph_sha256="0" * 64), preparation) is None


def test_t06_changed_internal_hard_edge_rejected(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    changed = {name: set(targets) for name, targets in edges.items()}
    changed["a"].add("a")
    assert _validated(changed, snapshot, preparation) is None


@pytest.mark.parametrize("mutation", ["reordered", "missing", "duplicated"])
def test_t07_invalid_scc_component_sequence_rejected(
    tmp_path, isolated_dirs, mutation,
):
    edges, snapshot, preparation = _case(tmp_path)
    items = preparation.component_preparations
    changed = {
        "reordered": tuple(reversed(items)),
        "missing": items[:1],
        "duplicated": (items[0], items[0]),
    }[mutation]
    assert _validated(edges, snapshot, replace(
        preparation, component_preparations=changed,
    )) is None


@pytest.mark.parametrize("status,reason", [
    ("PREPARED_UNPUBLISHED_NON_ATOMIC", None),
    ("UNAVAILABLE", "OTHER"),
])
def test_t08_incomplete_forged_status_or_reason_rejected(
    tmp_path, isolated_dirs, status, reason,
):
    edges, snapshot, preparation = _case(tmp_path)
    assert _validated(edges, snapshot, replace(
        preparation, status=status, reason=reason,
    )) is None


def test_t09_missing_prepared_closure_signature_rejected(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    rows = preparation.component_preparations[0].source_signatures
    changed = _replace_component(preparation, 0, source_signatures=rows[:-1])
    assert _validated(edges, snapshot, changed) is None


@pytest.mark.parametrize("mutation", ["duplicate", "reorder"])
def test_t10_duplicate_or_reordered_source_rows_rejected(
    tmp_path, isolated_dirs, mutation,
):
    edges, snapshot, preparation = _case(tmp_path)
    rows = preparation.component_preparations[0].source_signatures
    changed_rows = rows + rows[:1] if mutation == "duplicate" else tuple(reversed(rows))
    changed = _replace_component(preparation, 0, source_signatures=changed_rows)
    assert _validated(edges, snapshot, changed) is None


def test_t11_cyclic_source_fingerprint_mismatch_rejected(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    rows = list(preparation.component_preparations[0].source_signatures)
    rows[0] = (rows[0][0], "0" * 64, rows[0][2])
    changed = _replace_component(preparation, 0, source_signatures=tuple(rows))
    assert _validated(edges, snapshot, changed) is None


def test_t12_conflicting_shared_source_signatures_rejected(tmp_path, isolated_dirs):
    sources = {
        "a": "import b\nimport shared\n",
        "b": "import a\n",
        "x": "import y\nimport shared\n",
        "y": "import x\n",
        "shared": "value = 1\n",
    }
    root = _repo(tmp_path, sources)
    index, graph, snapshot = _real_pipeline(
        root, selected=frozenset(sources),
    )
    preparation = _prepare(index, graph, snapshot)
    assert preparation.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
    assert _validated(graph.hard_edges, snapshot, preparation) is not None
    rows = list(preparation.component_preparations[1].source_signatures)
    shared_position = next(i for i, row in enumerate(rows) if row[0] == "shared")
    rows[shared_position] = ("shared", "0" * 64, rows[shared_position][2])
    changed = _replace_component(preparation, 1, source_signatures=tuple(rows))
    assert _validated(graph.hard_edges, snapshot, changed) is None


@pytest.mark.parametrize("change", [
    {"model_classification": "UNKNOWN"},
    {"preparation_state": "OTHER"},
])
def test_t13_unsupported_model_or_state_rejected(tmp_path, isolated_dirs, change):
    edges, snapshot, preparation = _case(tmp_path)
    assert _validated(edges, snapshot, _replace_component(
        preparation, 0, **change,
    )) is None


def test_t14_malformed_model_evidence_hash_rejected(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    changed = _replace_component(
        preparation, 0, model_evidence_sha256="NOT_SHA256",
    )
    assert _validated(edges, snapshot, changed) is None


def test_t15_unavailable_scc_does_not_erase_prepared_scc(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    result = _validated(edges, snapshot, preparation)
    assert result is not None
    assert result.components[0].preparation_state == "PREPARED_UNPUBLISHED"
    assert result.components[1].preparation_state == "UNAVAILABLE"


def test_t16_inputs_and_signatures_are_unchanged(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    before = copy.deepcopy((edges, snapshot, preparation))
    assert _validated(edges, snapshot, preparation) is not None
    assert (edges, snapshot, preparation) == before


def test_t17_repeated_calls_are_deterministic(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    assert _validated(edges, snapshot, preparation) == _validated(
        edges, snapshot, preparation,
    )


def test_t18_prepared_claims_are_not_manifest_or_receipt(tmp_path, isolated_dirs):
    edges, snapshot, preparation = _case(tmp_path)
    claims = _validated(edges, snapshot, preparation)
    assert type(claims) is PreparedPartialSCCClaims
    state = RepositoryAnalysisState(
        dependency_graph=ProjectGraph(
            hard_edges={name: set(targets) for name, targets in edges.items()},
            soft_edges={},
        ),
        cycles=[["a", "b", "a"], ["x", "y", "x"]],
        cycles_state="fresh",
        cycle_semantics=snapshot,
        cycle_semantics_state="fresh",
    )
    with pytest.raises((TypeError, ValueError)):
        save_snapshot(
            state, tmp_path, "partial-claims", exact_revision=1,
            file_state_payload={
                "_meta": {"state_id": "partial-claims", "revision": 1},
                "files": {},
            },
            prepared_cycle_manifest=claims,
        )
    assert state.cycle_source_publication is None
    assert _verified_model_pass_cycle_paths(
        state,
        expected_revision=1,
        expected_state_id="partial-claims",
        expected_repo_id="repo",
        expected_root_path="root",
    ) == frozenset()
