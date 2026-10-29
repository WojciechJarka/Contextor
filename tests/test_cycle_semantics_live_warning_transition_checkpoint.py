"""WARN-4D: owner-owned warning transitions survive generation installation."""

from __future__ import annotations

import copy
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture, _full, _owner, _persisted,
)
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _installed_next(root, server, *, partial=False):
    _full(root, partial=partial)
    state, metadata = _persisted(root)
    assert server._execute_publish({
        "state": state, "origin": "isolated_test",
    })["status"] == "ok"
    return state, metadata


def _transition(client):
    result = client.get_installed_cycle_warning_transitions()
    assert result["status"] == "ok"
    assert result["binding_state"] == "INSTALLED_WARNING_TRANSITION_CHECKPOINT"
    return result


def test_t01_t04_two_pass_loses_proof_and_reactivates_both(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        assert client.get_installed_cycle_warning_transitions()["status"] == "unavailable"
        next_state, newer = _installed_next(root, server, partial=False)
        answer = _transition(client)
        assert answer["from_revision"] == metadata.revision
        assert answer["to_revision"] == newer.revision
        assert answer["activity_epoch"] == server._activity_epoch
        assert len(answer["transitions"]) == 2
        assert tuple(item["action"] for item in answer["transitions"]) == (
            "WARNING_REACTIVATED", "WARNING_REACTIVATED",
        )
        assert all(item["previous_state"] == "MODEL_PASS" for item in answer["transitions"])
        assert all(item["current_state"] == "ACTIVE" for item in answer["transitions"])
        assert tuple(item["path"] for item in answer["transitions"]) == (
            ("a", "b", "a"), ("x", "y", "x"),
        )
        assert next_state.cycles == state.cycles
        assert client.get_installed_cycle_warning_transitions() == answer


def test_t02_mixed_pass_unknown_only_one_reactivated(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, PASS_AND_UNKNOWN)
    with _owner(state, metadata) as (server, client):
        _installed_next(root, server, partial=False)
        answer = _transition(client)
        assert tuple(item["path"] for item in answer["transitions"]) == (("a", "b", "a"),)
        assert answer["transitions"][0]["action"] == "WARNING_REACTIVATED"


def test_t03_mixed_pass_hazard_does_not_suppress_hazard(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, PASS_AND_HAZARD)
    with _owner(state, metadata) as (server, client):
        _installed_next(root, server, partial=False)
        answer = _transition(client)
        assert tuple(item["path"] for item in answer["transitions"]) == (("a", "b", "a"),)
        assert answer["transitions"][0]["action"] == "WARNING_REACTIVATED"


def test_t05_persisted_full_without_receipt_then_partial_accepts(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS, partial=False)
    with _owner(state, metadata) as (server, client):
        _installed_next(root, server, partial=True)
        answer = _transition(client)
        assert len(answer["transitions"]) == 2
        assert {item["action"] for item in answer["transitions"]} == {"MODEL_ACCEPTED"}


def test_t06_stale_before_is_unavailable_without_zero_transition_claim(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    state.cycles_state = "stale"
    with _owner(state, metadata) as (server, client):
        _installed_next(root, server, partial=True)
        answer = client.get_installed_cycle_warning_transitions()
        assert answer["status"] == "unavailable"
        assert "transitions" not in answer


def test_t07_stale_after_is_unavailable(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        _full(root, partial=False)
        newer, _ = _persisted(root)
        newer.cycles_state = "stale"
        assert server._execute_publish({"state": newer, "origin": "isolated_test"})["status"] == "ok"
        answer = client.get_installed_cycle_warning_transitions()
        assert answer["status"] == "unavailable"
        assert "transitions" not in answer


def test_t08_query_read_only_does_not_emit_events(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        _installed_next(root, server, partial=False)
        before = copy.deepcopy((server._events, server._activity_seq, server._activity_epoch))
        _transition(client)
        _transition(client)
        assert (server._events, server._activity_seq, server._activity_epoch) == before


def test_t09_newer_commit_replaces_previous_checkpoint(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        _, first = _installed_next(root, server, partial=False)
        assert len(_transition(client)["transitions"]) == 2
        _, second = _installed_next(root, server, partial=False)
        answer = _transition(client)
        assert answer["from_revision"] == first.revision
        assert answer["to_revision"] == second.revision
        assert answer["transitions"] == ()


def test_t10_current_state_drift_hides_cached_positive(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        newest, _ = _installed_next(root, server, partial=False)
        assert _transition(client)["status"] == "ok"
        newest.cycles_state = "stale"
        answer = client.get_installed_cycle_warning_transitions()
        assert answer["status"] == "unavailable"
        assert "transitions" not in answer


def test_t11_no_caller_payload_allowed(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        for extra in ("state", "receipt", "previous_projection", "expected_revision"):
            answer = client.request("get_installed_cycle_warning_transitions", **{extra: "bad"})
            assert answer["reason"] == "INVALID_WARNING_TRANSITION_PAYLOAD"


def test_t12_recovery_blocks_transition_query(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        _installed_next(root, server, partial=False)
        try:
            server._recovery_release_degraded = True
            answer = client.get_installed_cycle_warning_transitions()
            assert answer["reason"] == "LIVE_OWNER_NOT_READY"
        finally:
            server._recovery_release_degraded = False


def test_t13_committed_snapshot_publish_uses_same_checkpoint(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        _full(root, partial=False)
        newer, new_meta = _persisted(root)
        @contextmanager
        def _reader():
            yield newer, new_meta
        server._committed_snapshot_reader = _reader
        response = server._execute_publish({
            "state": SimpleNamespace(revision=new_meta.revision, state_id=new_meta.state_id),
            "origin": "isolated_test",
        })
        assert response["status"] == "ok"
        answer = _transition(client)
        assert answer["from_revision"] == metadata.revision
        assert answer["to_revision"] == new_meta.revision
        assert len(answer["transitions"]) == 2
        assert all(item["action"] == "WARNING_REACTIVATED" for item in answer["transitions"])


def test_t14_incremental_commit_reactivates_without_topology_change(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        before_cycles = copy.deepcopy(state.cycles)
        server._updater = lambda candidate, path: SimpleNamespace(
            status="ok", file_path=path, affected_modules=(),
        )
        result = server._execute_update_file({
            "operation": "update_file", "file_path": str(root / "a.py"),
            "origin": "isolated_test",
        })
        assert result["status"] == "ok"
        answer = _transition(client)
        assert answer["from_revision"] == metadata.revision
        assert answer["to_revision"] == metadata.revision + 1
        assert tuple(item["action"] for item in answer["transitions"]) == (
            "WARNING_REACTIVATED", "WARNING_REACTIVATED",
        )
        assert server._state.cycles == before_cycles
        assert server._state.cycle_partial_source_publication is None
