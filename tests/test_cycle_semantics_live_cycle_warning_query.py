"""Read-only canonical LIVE cycle-warning projection, no user service access."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from contextor.core.api.facade import ContextorFacade
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture, _full, _owner, _persisted,
)
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS, _repo,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


@pytest.mark.parametrize("sources,expected_accepted", [
    (PASS_AND_UNKNOWN, 1),
    (PASS_AND_HAZARD, 1),
    (TWO_PASS, 2),
])
def test_t01_t03_real_installed_partial_projection(
    tmp_path, isolated_dirs, sources, expected_accepted,
):
    _, state, metadata = _fixture(tmp_path, sources)
    with _owner(state, metadata) as (server, client):
        before = copy.deepcopy((server._events, server._activity_seq, state.cycles))
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "ok"
        assert answer["binding_state"] == "INSTALLED_CYCLE_WARNING_PROJECTION"
        assert answer["revision"] == metadata.revision
        assert answer["structural_count"] == 2
        assert answer["model_pass_count"] == expected_accepted
        assert answer["active_warning_count"] == 2 - expected_accepted
        assert answer["structural_paths"] == tuple(tuple(path) for path in state.cycles)
        assert answer["model_pass_paths"] == tuple(
            tuple(path) for path in state.cycles[:expected_accepted]
        )
        assert answer["active_warning_paths"] == tuple(
            tuple(path) for path in state.cycles[expected_accepted:]
        )
        assert answer["activity_epoch"] == server._activity_epoch
        assert answer["service_instance_id"] == server.endpoint.service_instance_id
        assert answer["process_start_identity"] == server.endpoint.process_start_identity
        assert (server._events, server._activity_seq, state.cycles) == before
        assert client.get_installed_cycle_warning_projection() == answer


def test_t04_default_full_has_all_structural_cycles_active(tmp_path, isolated_dirs):
    root = _repo(tmp_path, TWO_PASS)
    errors, result = ContextorFacade.analyze_project(str(root))
    assert isinstance(errors, list) and result is not None
    state, metadata = _persisted(root)
    assert state.cycle_partial_source_publication is None
    with _owner(state, metadata) as (_, client):
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "ok"
        assert answer["structural_count"] == answer["active_warning_count"] == 2
        assert answer["model_pass_paths"] == ()


def test_t05_v2_only_receipt_does_not_accept_partial(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(
        tmp_path, TWO_PASS, partial=False, complete=True,
    )
    assert state.cycle_source_publication is not None
    with _owner(state, metadata) as (_, client):
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "ok"
        assert answer["structural_count"] == answer["active_warning_count"] == 2
        assert answer["model_pass_count"] == 0


def test_t06_valid_fresh_acyclic_generation(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path, {"a": "value = 1\n"})
    with _owner(state, metadata) as (_, client):
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "ok"
        assert answer["structural_paths"] == ()
        assert answer["model_pass_paths"] == ()
        assert answer["active_warning_paths"] == ()
        assert answer["structural_count"] == answer["active_warning_count"] == 0


def test_t07_missing_partial_receipt_reactivates_all(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    state.cycle_partial_source_publication = None
    with _owner(state, metadata) as (_, client):
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "ok"
        assert answer["model_pass_count"] == 0
        assert answer["active_warning_count"] == 2


def test_t08_forged_receipt_fails_closed_without_hiding_paths(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    receipt = state.cycle_partial_source_publication
    state.cycle_partial_source_publication = replace(receipt, claims_sha256="0" * 64)
    with _owner(state, metadata) as (_, client):
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "ok"
        assert answer["model_pass_count"] == 0
        assert answer["active_warning_count"] == 2


@pytest.mark.parametrize("mutation", ["stale", "resync", "duplicate"])
def test_t09_unavailable_structural_inventory_is_not_zero(
    tmp_path, isolated_dirs, mutation,
):
    _, state, metadata = _fixture(tmp_path)
    if mutation == "stale":
        state.cycles_state = "stale"
    elif mutation == "resync":
        state.resync_required = True
    else:
        state.cycles.append(list(state.cycles[0]))
    with _owner(state, metadata) as (_, client):
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "unavailable"
        assert answer["reason"] == "STRUCTURAL_CYCLE_INVENTORY_UNAVAILABLE"
        assert "active_warning_count" not in answer


def test_t10_durable_receipt_without_installed_state_is_not_accepted(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(None, metadata) as (_, client):
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "unavailable"
        assert answer["reason"] == "INSTALLED_STATE_UNAVAILABLE"


def test_t11_wrong_loaded_revision_fails_closed(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (_, client):
        state.revision += 1
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "unavailable"
        assert answer["reason"] == "INSTALLED_GENERATION_MISMATCH"


def test_t12_foreign_or_incomplete_authority_fails_closed(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        server._authority_identity["process_start_identity"] = None
        answer = client.get_installed_cycle_warning_projection()
        assert answer["status"] == "unavailable"
        assert answer["reason"] == "LIVE_AUTHORITY_UNAVAILABLE"


def test_t13_extra_request_keys_are_rejected(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (_, client):
        for extra in ("state", "receipt", "source_bytes", "expected_revision"):
            answer = client.request("get_installed_cycle_warning_projection", **{extra: "forbidden"})
            assert answer["status"] == "unavailable"
            assert answer["reason"] == "INVALID_CYCLE_WARNING_PROJECTION_PAYLOAD"


@pytest.mark.parametrize("readiness", ["pending", "degraded"])
def test_t14_recovery_not_ready_returns_unavailable(tmp_path, isolated_dirs, readiness):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, client):
        try:
            if readiness == "pending":
                server._pending_recovery_certificate = {"certificate_id": "synthetic"}
            else:
                server._recovery_release_degraded = True
            answer = client.get_installed_cycle_warning_projection()
            assert answer["status"] == "unavailable"
            assert answer["reason"] == "LIVE_OWNER_NOT_READY"
        finally:
            server._pending_recovery_certificate = None
            server._recovery_release_degraded = False


def test_t15_new_installed_generation_restores_warnings(tmp_path, isolated_dirs):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    with _owner(state, metadata) as (server, client):
        first = client.get_installed_cycle_warning_projection()
        assert first["active_warning_count"] == 0
        _full(root, partial=False)
        newer, newer_metadata = _persisted(root)
        assert newer_metadata.revision == metadata.revision + 1
        assert server._execute_publish({
            "state": newer, "origin": "isolated_test",
        })["status"] == "ok"
        second = client.get_installed_cycle_warning_projection()
        assert second["status"] == "ok"
        assert second["revision"] == newer_metadata.revision
        assert second["structural_paths"] == first["structural_paths"]
        assert second["model_pass_count"] == 0
        assert second["active_warning_count"] == 2
        assert second["activity_epoch"] == first["activity_epoch"]


def test_t16_valid_result_has_no_receipt_or_source_bytes(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (_, client):
        answer = client.get_installed_cycle_warning_projection()
        assert set(answer) == {
            "status", "binding_state", "revision", "state_id", "repo_id",
            "root_path", "service_instance_id", "process_start_identity",
            "activity_epoch", "graph_sha256", "structural_paths",
            "model_pass_paths", "active_warning_paths", "structural_count",
            "model_pass_count", "active_warning_count", "authority",
        }
