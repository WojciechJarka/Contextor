"""P1D1E: active LIVE-owner installed-generation gates."""

from __future__ import annotations

import threading
from dataclasses import replace

import pytest

from contextor.core.cycle_semantics import (
    live_installed_claims,
)
from contextor.core.live_state.ipc import (
    CanonicalLiveServer,
    LiveStateClient,
)
from contextor.core.live_state.store import (
    load_snapshot,
    save_snapshot,
)
from tests.test_cycle_semantics_publication_binding import (
    _case,
)


@pytest.fixture
def owner(tmp_path):
    state, prepared = _case()
    root_path = str(tmp_path.resolve())
    repo_id = "ctx_p1d1e_test"
    instance = "p1d1e-service-instance"

    save_snapshot(
        state,
        tmp_path,
        "p1d1e-state",
        repo_id=repo_id,
        root_path=root_path,
        exact_revision=1,
        file_state_payload={
            "_meta": {
                "state_id": "p1d1e-state",
                "revision": 1,
            },
            "files": {},
        },
        prepared_cycle_manifest=prepared,
    )

    loaded, metadata = load_snapshot(
        tmp_path,
        "p1d1e-state",
        expected_repo_id=repo_id,
        expected_root_path=root_path,
    )

    server = CanonicalLiveServer(
        loaded,
        revision=1,
        authority_identity={
            "repo_id": repo_id,
            "root_path": root_path,
            "service_instance_id": instance,
        },
    )

    request = {
        "operation": "verify_installed_cycle_generation",
        "expected_revision": metadata.revision,
        "expected_state_id": metadata.state_id,
        "expected_repo_id": repo_id,
        "expected_root_path": root_path,
        "expected_graph_sha256": prepared.graph_sha256,
        "expected_service_instance_id": instance,
    }

    try:
        yield server, request
    finally:
        server.close()


def _check(server, request, **changes):
    return server._dispatch({**request, **changes})


def test_p1d1e_t01_installed_committed_claim_matches(owner):
    server, request = owner
    answer = _check(server, request)

    assert answer["status"] == "ok"
    assert answer["binding_state"] == (
        "INSTALLED_PREPARED_CLAIMS_MATCH_EXPECTED_GENERATION"
    )
    assert answer["revision"] == 1
    assert answer["state_id"] == "p1d1e-state"
    assert answer["repo_id"] == "ctx_p1d1e_test"
    assert answer["activity_epoch"] == server.activity_epoch
    assert len(answer["source_manifest_sha256"]) == 64
    assert len(answer["model_claims_sha256"]) == 64
    assert "NOT_STABLE_AFTER_REPLY" in answer["authority"]
    assert "NOT_RUNTIME_SAFETY" in answer["authority"]
    assert "state" not in answer


def test_p1d1e_t02_stale_expected_revision(owner):
    server, request = owner
    answer = _check(
        server, request, expected_revision=2
    )
    assert answer["status"] == "unavailable"
    assert answer["reason"] == (
        "INSTALLED_GENERATION_MISMATCH"
    )


def test_p1d1e_t03_wrong_state_id(owner):
    server, request = owner
    answer = _check(
        server, request, expected_state_id="foreign-state"
    )
    assert answer["reason"] == (
        "INSTALLED_GENERATION_MISMATCH"
    )


def test_p1d1e_t04_foreign_repo(owner):
    server, request = owner
    answer = _check(
        server, request, expected_repo_id="ctx_foreign"
    )
    assert answer["reason"] == "LIVE_REPOSITORY_MISMATCH"


def test_p1d1e_t05_foreign_root(owner):
    server, request = owner
    answer = _check(
        server, request, expected_root_path="foreign-root"
    )
    assert answer["reason"] == "LIVE_REPOSITORY_MISMATCH"


def test_p1d1e_t06_foreign_service_instance(owner):
    server, request = owner
    answer = _check(
        server,
        request,
        expected_service_instance_id="stale-instance",
    )
    assert answer["reason"] == "LIVE_INSTANCE_MISMATCH"


def test_p1d1e_t07_graph_claim_mismatch(owner):
    server, request = owner
    answer = _check(
        server,
        request,
        expected_graph_sha256="f" * 64,
    )
    assert answer["reason"] == (
        "INSTALLED_GRAPH_IDENTITY_MISMATCH"
    )


def test_p1d1e_t08_missing_receipt(owner):
    server, request = owner
    server._state.cycle_source_publication = None
    answer = _check(server, request)
    assert answer["reason"] == (
        "CO_PUBLISHED_RECEIPT_UNAVAILABLE"
    )


def test_p1d1e_t09_stale_cycle_family(owner):
    server, request = owner
    server._state.cycle_semantics_state = "stale"
    answer = _check(server, request)
    assert answer["reason"] == (
        "REQUIRED_CYCLE_FAMILY_NOT_FRESH"
    )


def test_p1d1e_t10_resync_required(owner):
    server, request = owner
    server._state.resync_required = True
    answer = _check(server, request)
    assert answer["reason"] == "CANONICAL_RESYNC_REQUIRED"


def test_p1d1e_t11_unrelated_payload_rejected(owner):
    server, request = owner
    answer = _check(
        server,
        request,
        source_capture_bytes=b"not-permitted",
    )
    assert answer["status"] == "unavailable"
    assert answer["reason"] == (
        "INVALID_GENERATION_CHECK_PAYLOAD"
    )


def test_p1d1e_t12_invalid_expected_generation(owner):
    server, request = owner

    for changed in (
        {"expected_revision": True},
        {"expected_revision": 0},
        {"expected_state_id": ""},
        {"expected_graph_sha256": "bad"},
    ):
        answer = _check(server, request, **changed)
        assert answer["status"] == "unavailable"
        assert answer["reason"] == (
            "INVALID_EXPECTED_GENERATION"
        )


def test_p1d1e_t13_recovery_pending_rejected(owner):
    server, request = owner
    server._pending_recovery_certificate = {
        "certificate_id": "test-only",
    }
    try:
        answer = _check(server, request)
        assert answer["reason"] == "LIVE_OWNER_NOT_READY"
    finally:
        server._pending_recovery_certificate = None


def test_p1d1e_t14_generation_change_is_serialized(
    owner, monkeypatch,
):
    server, request = owner
    original = (
        live_installed_claims
        .verify_co_published_cycle_manifest
    )
    entered = threading.Event()
    release = threading.Event()
    mutation_started = threading.Event()
    mutation_done = threading.Event()
    observed = {}

    def delayed_verification(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    def check():
        observed["check"] = _check(server, request)

    candidate = server._state.clone_for_update()
    candidate.revision = 2

    def publish():
        mutation_started.set()
        observed["publish"] = server._dispatch({
            "operation": "publish",
            "state": candidate,
            "origin": "p1d1e_concurrency_test",
        })
        mutation_done.set()

    monkeypatch.setattr(
        live_installed_claims,
        "verify_co_published_cycle_manifest",
        delayed_verification,
    )

    checker = threading.Thread(target=check)
    publisher = threading.Thread(target=publish)

    try:
        checker.start()
        assert entered.wait(timeout=5)

        publisher.start()
        assert mutation_started.wait(timeout=5)

        # The mutation cannot commit while the owner-side
        # receipt verification holds the LIVE state lock.
        assert not mutation_done.wait(timeout=0.1)
    finally:
        release.set()
        checker.join(timeout=5)
        if publisher.ident is not None:
            publisher.join(timeout=5)

    assert not checker.is_alive()
    assert not publisher.is_alive()
    assert observed["check"]["status"] == "ok"
    assert observed["check"]["revision"] == 1
    assert observed["publish"]["status"] == "ok"
    assert observed["publish"]["revision"] == 2

    # The earlier successful response only describes
    # the instant at which revision 1 was installed.
    later = _check(server, request)
    assert later["status"] == "unavailable"
    assert later["reason"] == (
        "INSTALLED_GENERATION_MISMATCH"
    )


def test_p1d1e_t15_client_uses_endpoint_instance(owner):
    server, request = owner
    client = LiveStateClient(server.endpoint)
    seen = {}

    def recorded(operation, **payload):
        seen["operation"] = operation
        seen["payload"] = payload
        return {"status": "unavailable"}

    client.request = recorded
    client.verify_installed_cycle_generation(
        expected_revision=request["expected_revision"],
        expected_state_id=request["expected_state_id"],
        expected_repo_id=request["expected_repo_id"],
        expected_root_path=request["expected_root_path"],
        expected_graph_sha256=(
            request["expected_graph_sha256"]
        ),
    )

    assert seen["operation"] == (
        "verify_installed_cycle_generation"
    )
    assert seen["payload"][
        "expected_service_instance_id"
    ] == server.endpoint.service_instance_id


def test_p1d1e_t16_owner_without_authority_fails_closed(
    owner,
):
    server, request = owner
    server._authority_identity = {}
    answer = _check(server, request)
    assert answer["status"] == "unavailable"
    assert answer["reason"] == (
        "LIVE_AUTHORITY_UNAVAILABLE"
    )
