"""P1D1C — compare worker bytes with committed prepared claims."""

from __future__ import annotations

from dataclasses import replace

import pytest

from contextor.core.cycle_semantics.worker_claim_binding import (
    assess_worker_capture_committed_claim as assess,
)
from contextor.core.cycle_semantics.selective_worker_capture import (
    iter_selective_scc_worker_captures,
)
from contextor.core.graph.graph import build_graph
from contextor.core.live_state.store import (
    load_snapshot,
    save_snapshot,
)
from contextor.core.source import SourceSnapshot
from contextor.core.symbol_engine.indexer import index_repository
from tests.test_cycle_semantics_evidence import PASS
from tests.test_cycle_semantics_publication_binding import _case


@pytest.fixture
def bound_case(tmp_path, isolated_dirs, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")

    root = tmp_path / "repo"
    root.mkdir()
    for name, text in PASS.items():
        (root / (name + ".py")).write_bytes(
            text.encode("utf-8")
        )

    index = index_repository(str(root))
    graph = build_graph(index.modules)

    state, prepared = _case()
    cache = tmp_path / "cache"

    save_snapshot(
        state,
        cache,
        "cycle-state",
        repo_id="test-repo",
        root_path=str(root.resolve()),
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "cycle-state",
                "revision": 1,
            },
            "files": {},
        },
        prepared_cycle_manifest=prepared,
    )

    committed, metadata = load_snapshot(
        cache, "cycle-state"
    )

    (captured,) = tuple(
        iter_selective_scc_worker_captures(
            root, graph.hard_edges, index
        )
    )

    return committed, metadata, captured


def test_p1d1c_t01_real_committed_claim_matches(bound_case):
    state, meta, captured = bound_case
    result = assess(state, meta, captured)

    assert result.binding_state == (
        "DECLARED_BYTES_MATCH_COMMITTED_PREPARED_CLAIMS"
    )
    assert result.reason is None
    assert result.members == ("a", "b")
    assert result.canonical_revision == 1
    assert result.state_id == "cycle-state"
    assert result.graph_sha256 == (
        state.cycle_source_publication
        .prepared_manifest.graph_sha256
    )
    assert "NOT_RUNTIME_SAFETY" in result.authority
    assert "NOT_SOURCE_OR_LIVE_ORIGIN_AUTHENTICATED" in (
        result.authority
    )


def test_p1d1c_t02_missing_receipt_unavailable(bound_case):
    state, meta, captured = bound_case
    state.cycle_source_publication = None
    result = assess(state, meta, captured)
    assert result.binding_state == "UNAVAILABLE"
    assert result.reason == "CO_PUBLISHED_RECEIPT_UNAVAILABLE"


def test_p1d1c_t03_wrong_revision_rejected(bound_case):
    state, meta, captured = bound_case
    result = assess(
        state, replace(meta, revision=meta.revision + 1),
        captured,
    )
    assert result.binding_state == "UNAVAILABLE"
    assert result.reason == "GENERATION_IDENTITY_MISMATCH"


def test_p1d1c_t04_wrong_state_id_rejected(bound_case):
    state, meta, captured = bound_case
    result = assess(
        state, replace(meta, state_id="foreign-state"),
        captured,
    )
    assert result.reason == "GENERATION_IDENTITY_MISMATCH"


def test_p1d1c_t05_foreign_repo_rejected(bound_case):
    state, meta, captured = bound_case
    result = assess(
        state, replace(meta, repo_id="foreign-repo"),
        captured,
    )
    assert result.reason == "CO_PUBLISHED_RECEIPT_INVALID"


def test_p1d1c_t06_foreign_root_rejected(bound_case):
    state, meta, captured = bound_case
    result = assess(
        state, replace(meta, root_path="foreign-root"),
        captured,
    )
    assert result.reason == "CO_PUBLISHED_RECEIPT_INVALID"


def test_p1d1c_t07_stale_semantics_rejected(bound_case):
    state, meta, captured = bound_case
    state.cycle_semantics_state = "stale"
    result = assess(state, meta, captured)
    assert result.reason == "CO_PUBLISHED_RECEIPT_INVALID"


def test_p1d1c_t08_changed_graph_rejected(bound_case):
    state, meta, captured = bound_case
    state.dependency_graph.hard_edges["a"] = set()
    result = assess(state, meta, captured)
    assert result.reason == "CO_PUBLISHED_RECEIPT_INVALID"


def test_p1d1c_t09_missing_closure_member(bound_case):
    state, meta, captured = bound_case
    sources = dict(captured.source_snapshots)
    sources.pop("b")
    changed = replace(captured, source_snapshots=sources)
    result = assess(state, meta, changed)
    assert result.reason == (
        "SCC_CLOSURE_INCOMPLETE_OR_MISMATCHED"
    )


def test_p1d1c_t10_mutated_bytes_rejected(bound_case):
    state, meta, captured = bound_case
    sources = dict(captured.source_snapshots)
    original = sources["a"]
    sources["a"] = SourceSnapshot(
        raw=original.raw + b"\n",
        source_fingerprint=original.source_fingerprint,
    )
    result = assess(
        state, meta,
        replace(captured, source_snapshots=sources),
    )
    assert result.reason == "SOURCE_BYTES_CLAIM_MISMATCH:a"


def test_p1d1c_t11_invalid_capture_authority(bound_case):
    state, meta, captured = bound_case
    changed = replace(captured, authority="FORGED")
    assert assess(state, meta, changed).reason == (
        "WORKER_CAPTURE_NOT_ACCEPTED"
    )


def test_p1d1c_t12_failed_worker_capture_rejected(bound_case):
    state, meta, captured = bound_case
    changed = replace(
        captured,
        status="UNAVAILABLE",
        reason="WORKER_EXECUTION_FAILED:a",
    )
    assert assess(state, meta, changed).reason == (
        "WORKER_CAPTURE_NOT_ACCEPTED"
    )


def test_p1d1c_t13_wrong_scc_membership(bound_case):
    state, meta, captured = bound_case
    changed = replace(captured, members=("foreign",))
    assert assess(state, meta, changed).reason == (
        "SCC_NOT_IN_COMMITTED_MANIFEST"
    )


def test_p1d1c_t14_byte_limit_fails_closed(bound_case):
    state, meta, captured = bound_case
    result = assess(
        state, meta, captured,
        max_source_bytes=1,
    )
    assert result.binding_state == "UNAVAILABLE"
    assert result.reason.startswith(
        "SOURCE_BYTE_BUDGET_EXCEEDED:"
    )


def test_p1d1c_t15_invalid_budget_rejected(bound_case):
    state, meta, captured = bound_case
    for options in (
        {"max_source_bytes": 0},
        {"max_source_bytes": True},
        {"max_closure_bytes": 0},
        {"max_closure_bytes": 257 * 1024 * 1024},
    ):
        with pytest.raises(ValueError):
            assess(state, meta, captured, **options)


def test_p1d1c_t16_byte_accounting_mismatch(bound_case):
    state, meta, captured = bound_case
    changed = replace(
        captured,
        retained_raw_bytes=captured.retained_raw_bytes + 1,
    )
    assert assess(state, meta, changed).reason == (
        "CAPTURE_BYTE_ACCOUNTING_MISMATCH"
    )


def test_p1d1c_t17_ast_mode_domain_mismatch(bound_case):
    state, meta, captured = bound_case
    changed = replace(
        captured,
        ast_modes=(("a", "INVALID"), ("b", "INVALID")),
    )
    assert assess(state, meta, changed).reason == (
        "SCC_CLOSURE_INCOMPLETE_OR_MISMATCHED"
    )


def test_p1d1c_t18_no_source_reread_or_live_ipc(
    bound_case, monkeypatch,
):
    from pathlib import Path

    state, meta, captured = bound_case

    def forbidden(*args, **kwargs):
        raise AssertionError("filesystem read forbidden")

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_bytes", forbidden)
        scoped.setattr(Path, "read_text", forbidden)
        result = assess(state, meta, captured)

    assert result.binding_state == (
        "DECLARED_BYTES_MATCH_COMMITTED_PREPARED_CLAIMS"
    )
