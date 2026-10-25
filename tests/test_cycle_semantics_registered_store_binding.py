"""P1D1D registered durable-generation binding regressions."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace

import pytest

from contextor.core.cycle_semantics import (
    registered_store_binding as binding,
)
from contextor.core.cycle_semantics.selective_worker_capture import (
    iter_selective_scc_worker_captures,
)
from contextor.core.graph.graph import build_graph
from contextor.core.live_state.store import (
    load_snapshot,
    save_snapshot,
)
from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import (
    ensure_repository_identity,
    read_repository_identity,
)
from contextor.core.symbol_engine.indexer import index_repository
from tests.test_cycle_semantics_evidence import PASS
from tests.test_cycle_semantics_publication_binding import _case


@pytest.fixture
def committed(tmp_path, isolated_dirs, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")

    root = tmp_path / "repo"
    root.mkdir()
    for name, source in PASS.items():
        (root / (name + ".py")).write_bytes(
            source.encode("utf-8")
        )

    identity, _ = ensure_repository_identity(root)
    cache = repo_cache_dir(root)

    index = index_repository(str(root))
    graph = build_graph(index.modules)
    (capture,) = tuple(
        iter_selective_scc_worker_captures(
            root, graph.hard_edges, index
        )
    )

    state, prepared = _case()
    save_snapshot(
        state,
        cache,
        "cycle-state",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
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

    return root, cache, identity, capture


def _assess(root, capture, **kwargs):
    options = {
        "expected_revision": 1,
        "expected_state_id": "cycle-state",
    }
    options.update(kwargs)
    return binding.assess_registered_committed_worker_capture(
        root, capture, **options
    )


def _supersede(root, cache, identity):
    state, metadata = load_snapshot(
        cache,
        expected_repo_id=identity.repo_id,
        expected_root_path=identity.root_path,
    )
    assert metadata.revision == 1

    save_snapshot(
        state,
        cache,
        "cycle-state",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
        exact_revision=2,
        file_state_payload={
            "_meta": {
                "state_id": "cycle-state",
                "revision": 2,
            },
            "files": {},
        },
    )


def test_p1d1d_t01_real_registered_committed_match(committed):
    root, _, identity, capture = committed
    result = _assess(root, capture)

    assert result.binding_state == (
        "REGISTERED_COMMITTED_GENERATION_CLAIMS_MATCH_WORKER_BYTES"
    )
    assert result.reason is None
    assert result.canonical_revision == 1
    assert result.state_id == "cycle-state"
    assert result.repo_id == identity.repo_id
    assert result.root_path == identity.root_path
    assert result.members == ("a", "b")
    assert result.graph_sha256
    assert "NOT_CURRENT_LIVE" in result.authority
    assert "NOT_RUNTIME_SAFETY" in result.authority


def test_p1d1d_t02_unregistered_repo_is_not_created(
    committed, tmp_path,
):
    _, _, _, capture = committed
    root = tmp_path / "unregistered"
    root.mkdir()

    assert read_repository_identity(root) is None

    result = _assess(root, capture)

    assert result.binding_state == "UNAVAILABLE"
    assert result.reason == "REPOSITORY_NOT_REGISTERED"
    assert read_repository_identity(root) is None
    assert list(root.iterdir()) == []


def test_p1d1d_t03_missing_store_fails_closed(
    committed, tmp_path,
):
    _, _, _, capture = committed
    root = tmp_path / "other"
    root.mkdir()
    ensure_repository_identity(root)

    result = _assess(root, capture)
    assert result.reason == "COMMITTED_GENERATION_UNAVAILABLE"


def test_p1d1d_t04_wrong_expected_revision(committed):
    root, _, _, capture = committed
    result = _assess(root, capture, expected_revision=2)
    assert result.reason == "COMMITTED_EXPECTATION_MISMATCH"


def test_p1d1d_t05_wrong_expected_state_id(committed):
    root, _, _, capture = committed
    result = _assess(
        root, capture, expected_state_id="foreign-state"
    )
    assert result.reason == "COMMITTED_EXPECTATION_MISMATCH"


def test_p1d1d_t06_foreign_registered_repo_isolated(
    committed, tmp_path,
):
    _, _, _, capture = committed
    other = tmp_path / "foreign"
    other.mkdir()
    ensure_repository_identity(other)

    result = _assess(other, capture)
    assert result.binding_state == "UNAVAILABLE"
    assert result.reason == "COMMITTED_GENERATION_UNAVAILABLE"


def test_p1d1d_t07_superseded_generation_rejected(committed):
    root, cache, identity, capture = committed
    _supersede(root, cache, identity)

    result = _assess(root, capture)
    assert result.binding_state == "UNAVAILABLE"
    assert result.reason == "COMMITTED_EXPECTATION_MISMATCH"
    assert result.canonical_revision == 2


def test_p1d1d_t08_new_revision_has_no_inherited_receipt(
    committed,
):
    root, cache, identity, capture = committed
    _supersede(root, cache, identity)

    result = _assess(root, capture, expected_revision=2)
    assert result.binding_state == "UNAVAILABLE"
    assert result.reason == "CO_PUBLISHED_RECEIPT_UNAVAILABLE"


def test_p1d1d_t09_bad_worker_capture_fails_closed(committed):
    root, _, _, capture = committed
    changed = replace(capture, authority="FORGED")

    result = _assess(root, changed)
    assert result.binding_state == "UNAVAILABLE"
    assert result.reason == "WORKER_CAPTURE_NOT_ACCEPTED"


def test_p1d1d_t10_missing_root_fails_closed(
    committed, tmp_path,
):
    _, _, _, capture = committed
    result = _assess(tmp_path / "does-not-exist", capture)
    assert result.reason == "REPOSITORY_ROOT_UNAVAILABLE"


def test_p1d1d_t11_invalid_expected_generation(
    committed,
):
    root, _, _, capture = committed

    for options in (
        {"expected_revision": True},
        {"expected_revision": 0},
        {"expected_state_id": ""},
        {"expected_state_id": None},
    ):
        with pytest.raises(ValueError):
            _assess(root, capture, **options)


def test_p1d1d_t12_invalid_byte_limits(committed):
    root, _, _, capture = committed
    for options in (
        {"max_source_bytes": 0},
        {"max_source_bytes": True},
        {"max_closure_bytes": 0},
        {"max_closure_bytes": 257 * 1024 * 1024},
    ):
        with pytest.raises(ValueError):
            _assess(root, capture, **options)


def test_p1d1d_t13_foreign_loader_metadata_rejected(
    committed, monkeypatch,
):
    root, cache, identity, capture = committed
    state, metadata = load_snapshot(
        cache,
        expected_repo_id=identity.repo_id,
        expected_root_path=identity.root_path,
    )

    @contextmanager
    def forged_reader(*args, **kwargs):
        yield state, replace(
            metadata, repo_id="foreign-repo"
        )

    monkeypatch.setattr(
        binding, "locked_committed_snapshot",
        forged_reader,
    )
    result = _assess(root, capture)
    assert result.reason == "COMMITTED_REPOSITORY_MISMATCH"


def test_p1d1d_t14_lock_released_before_ast_verification(
    committed, monkeypatch,
):
    root, _, _, capture = committed
    original_reader = binding.locked_committed_snapshot
    original_assess = (
        binding.assess_worker_capture_committed_claim
    )
    lock_state = {"open": False, "compared": False}

    @contextmanager
    def observed_reader(*args, **kwargs):
        with original_reader(*args, **kwargs) as loaded:
            lock_state["open"] = True
            try:
                yield loaded
            finally:
                lock_state["open"] = False

    def observed_assess(*args, **kwargs):
        assert lock_state["open"] is False
        lock_state["compared"] = True
        return original_assess(*args, **kwargs)

    monkeypatch.setattr(
        binding,
        "locked_committed_snapshot",
        observed_reader,
    )
    monkeypatch.setattr(
        binding,
        "assess_worker_capture_committed_claim",
        observed_assess,
    )

    result = _assess(root, capture)
    assert result.binding_state.startswith(
        "REGISTERED_COMMITTED_GENERATION_CLAIMS_MATCH"
    )
    assert lock_state["compared"]
    assert not lock_state["open"]


def test_p1d1d_t15_no_worker_execution(
    committed, monkeypatch,
):
    from contextor.core.cycle_semantics import (
        selective_worker_capture,
    )

    root, _, _, capture = committed

    def forbidden(*args, **kwargs):
        raise AssertionError("worker must not be invoked")

    monkeypatch.setattr(
        selective_worker_capture,
        "_process_single_file",
        forbidden,
    )

    result = _assess(root, capture)
    assert result.binding_state == (
        "REGISTERED_COMMITTED_GENERATION_CLAIMS_MATCH_WORKER_BYTES"
    )


def test_p1d1d_t16_byte_budget_does_not_promote(
    committed,
):
    root, _, _, capture = committed
    result = _assess(
        root, capture, max_source_bytes=1
    )
    assert result.binding_state == "UNAVAILABLE"
    assert result.reason.startswith(
        "SOURCE_BYTE_BUDGET_EXCEEDED:"
    )
