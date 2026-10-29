"""Installed partial SCC claims are checked against isolated LIVE state."""

from __future__ import annotations

import copy
from contextlib import contextmanager
from dataclasses import replace
from threading import Thread

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
from tests.test_original_worker_full_partial_receipt_optin import _persisted
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS, _repo,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _full(root, *, partial=True, complete=False):
    errors, result = ContextorFacade.analyze_project(
        str(root),
        cycle_source_preparation_preview=True,
        cycle_partial_source_publication_opt_in=partial,
        cycle_source_publication_opt_in=complete,
    )
    assert isinstance(errors, list)
    assert result is not None
    return result


@contextmanager
def _owner(state, metadata):
    authority = {
        "repo_id": metadata.repo_id,
        "root_path": metadata.root_path,
        "service_instance_id": "isolated-partial-service",
        "process_start_identity": "isolated-partial-process",
    }
    server = CanonicalLiveServer(
        state, revision=metadata.revision, authority_identity=authority,
    )
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    client = LiveStateClient(server.endpoint)
    try:
        assert client.ping()["status"] == "ok"
        yield server, client
    finally:
        assert server.close() is True
        worker.join(timeout=5.0)
        assert not worker.is_alive()


def _expected(state, metadata):
    receipt = state.cycle_partial_source_publication
    return {
        "expected_revision": metadata.revision,
        "expected_state_id": metadata.state_id,
        "expected_repo_id": metadata.repo_id,
        "expected_root_path": metadata.root_path,
        "expected_graph_sha256": state.cycle_semantics.graph_sha256,
        "expected_claims_sha256": receipt.claims_sha256,
    }


def _check(client, state, metadata, **changes):
    return client.verify_installed_partial_scc_generation(
        **{**_expected(state, metadata), **changes},
    )


def _fixture(tmp_path, sources=PASS_AND_UNKNOWN, *, partial=True, complete=False):
    root = _repo(tmp_path, sources)
    _full(root, partial=partial, complete=complete)
    state, metadata = _persisted(root)
    return root, state, metadata


def test_t01_t24_mixed_installed_response_preserves_both_sccs(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, client):
        response = _check(client, state, metadata)
        assert response["status"] == "ok"
        assert response["binding_state"] == (
            "INSTALLED_PARTIAL_SCC_CLAIMS_MATCH_EXPECTED_GENERATION"
        )
        assert tuple(item["model_classification"] for item in response["components"]) == (
            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS", "INDETERMINATE",
        )
        assert all(
            set(item) == {"members", "preparation_state", "model_classification"}
            for item in response["components"]
        )
        assert response["activity_epoch"] == server._activity_epoch
        assert response["service_instance_id"] == server.endpoint.service_instance_id
        assert response["process_start_identity"] == server.endpoint.process_start_identity


def test_t02_hazard_classification_is_distinct(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path, PASS_AND_HAZARD)
    with _owner(state, metadata) as (_, client):
        response = _check(client, state, metadata)
        assert response["status"] == "ok"
        assert tuple(item["model_classification"] for item in response["components"]) == (
            "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
            "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
        )


def test_t03_durable_receipt_without_installation_fails(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path)
    with _owner(None, metadata) as (_, client):
        assert _check(client, state, metadata)["status"] == "unavailable"


@pytest.mark.parametrize("change", [
    {"expected_revision": 99},
    {"expected_state_id": "foreign"},
    {"expected_repo_id": "foreign"},
    {"expected_root_path": "foreign"},
    {"expected_graph_sha256": "0" * 64},
    {"expected_claims_sha256": "0" * 64},
])
def test_t04_t05_t06_t09_t10_foreign_expected_generation(
    tmp_path, isolated_dirs, change,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (_, client):
        assert _check(client, state, metadata, **change)["status"] == "unavailable"


@pytest.mark.parametrize("field", [
    "expected_service_instance_id", "expected_process_start_identity",
])
def test_t07_t08_foreign_owner_identity(tmp_path, isolated_dirs, field):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, _):
        request = {
            "operation": "verify_installed_partial_scc_generation",
            **_expected(state, metadata),
            "expected_service_instance_id": server.endpoint.service_instance_id,
            "expected_process_start_identity": server.endpoint.process_start_identity,
        }
        request[field] = "foreign"
        assert server._dispatch(request)["status"] == "unavailable"


@pytest.mark.parametrize("mutation", ["missing", "classification", "digest", "version"])
def test_t11_t12_t14_invalid_receipt(tmp_path, isolated_dirs, mutation):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)
    if mutation == "missing":
        state.cycle_partial_source_publication = None
    else:
        receipt = state.cycle_partial_source_publication
        if mutation == "classification":
            items = list(receipt.preparation.component_preparations)
            items[0] = replace(items[0], model_classification="FORGED")
            state.cycle_partial_source_publication = replace(
                receipt,
                preparation=replace(
                    receipt.preparation, component_preparations=tuple(items),
                ),
            )
        elif mutation == "digest":
            state.cycle_partial_source_publication = replace(
                receipt, claims_sha256="0" * 64,
            )
        else:
            state.cycle_partial_source_publication = replace(
                receipt, version="unsupported",
            )
    with _owner(state, metadata) as (_, client):
        assert client.verify_installed_partial_scc_generation(**expected)["status"] == "unavailable"


@pytest.mark.parametrize("mutation", ["semantic", "cycles", "resync"])
def test_t13_stale_or_resync(tmp_path, isolated_dirs, mutation):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)
    if mutation == "semantic":
        state.cycle_semantics_state = "stale"
    elif mutation == "cycles":
        state.cycles_state = "stale"
    else:
        state.resync_required = True
    with _owner(state, metadata) as (_, client):
        assert client.verify_installed_partial_scc_generation(**expected)["status"] == "unavailable"


@pytest.mark.parametrize("extra", [
    "state", "receipt", "source_bytes", "preparation",
    "captured_index", "prepared_manifest",
])
def test_t15_extra_caller_object_rejected(tmp_path, isolated_dirs, extra):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, client):
        request = {
            **_expected(state, metadata),
            "expected_service_instance_id": server.endpoint.service_instance_id,
            "expected_process_start_identity": server.endpoint.process_start_identity,
            extra: "not accepted",
        }
        response = client.request("verify_installed_partial_scc_generation", **request)
        assert response["reason"] == "INVALID_GENERATION_CHECK_PAYLOAD"
        del request[extra]
        del request["expected_revision"]
        assert client.request("verify_installed_partial_scc_generation", **request)["reason"] == (
            "INVALID_GENERATION_CHECK_PAYLOAD"
        )


@pytest.mark.parametrize("readiness", ["pending", "degraded"])
def test_t16_recovery_not_ready(tmp_path, isolated_dirs, readiness):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, client):
        if readiness == "pending":
            server._pending_recovery_certificate = {"certificate_id": "isolated"}
        else:
            server._recovery_release_degraded = True
        assert _check(client, state, metadata)["reason"] == "LIVE_OWNER_NOT_READY"
        server._pending_recovery_certificate = None
        server._recovery_release_degraded = False


def test_t17_newer_committed_generation_invalidates_old_expected_identity(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    old_expected = _expected(state, metadata)
    with _owner(state, metadata) as (server, client):
        assert client.verify_installed_partial_scc_generation(**old_expected)["status"] == "ok"
        _full(root)
        newer, newer_metadata = _persisted(root)
        assert newer_metadata.revision == metadata.revision + 1
        assert server._execute_publish({
            "state": newer,
            "origin": "isolated_test",
        })["status"] == "ok"
        assert client.verify_installed_partial_scc_generation(**old_expected)["status"] == "unavailable"


def test_t18_v2_only_does_not_satisfy_partial(tmp_path, isolated_dirs):
    _, state, metadata = _fixture(tmp_path, TWO_PASS, partial=False, complete=True)
    assert state.cycle_source_publication is not None
    assert state.cycle_partial_source_publication is None
    with _owner(state, metadata) as (server, client):
        request = {
            "operation": "verify_installed_partial_scc_generation",
            "expected_revision": metadata.revision,
            "expected_state_id": metadata.state_id,
            "expected_repo_id": metadata.repo_id,
            "expected_root_path": metadata.root_path,
            "expected_graph_sha256": state.cycle_semantics.graph_sha256,
            "expected_claims_sha256": "0" * 64,
            "expected_service_instance_id": server.endpoint.service_instance_id,
            "expected_process_start_identity": server.endpoint.process_start_identity,
        }
        assert client.request(**request)["status"] == "unavailable"
        assert client.verify_installed_cycle_generation(
            expected_revision=metadata.revision,
            expected_state_id=metadata.state_id,
            expected_repo_id=metadata.repo_id,
            expected_root_path=metadata.root_path,
            expected_graph_sha256=state.cycle_semantics.graph_sha256,
        )["status"] == "ok"


def test_t19_t20_t23_response_is_bounded_read_only_deterministic(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path)
    with _owner(state, metadata) as (server, client):
        before_edges = copy.deepcopy(state.dependency_graph.hard_edges)
        before_sccs = copy.deepcopy(state.cycle_semantics.import_sites.topology.cyclic_components)
        before_cycles = copy.deepcopy(state.cycles)
        before_events = copy.deepcopy(server._events)
        first = _check(client, state, metadata)
        second = _check(client, state, metadata)
        assert first == second
        assert first["status"] == "ok"
        assert set(first) == {
            "status", "binding_state", "revision", "state_id", "repo_id",
            "root_path", "service_instance_id", "process_start_identity",
            "activity_epoch", "graph_sha256", "claims_sha256", "components",
            "authority",
        }
        assert state.dependency_graph.hard_edges == before_edges
        assert state.cycle_semantics.import_sites.topology.cyclic_components == before_sccs
        assert state.cycles == before_cycles
        assert server._events == before_events
