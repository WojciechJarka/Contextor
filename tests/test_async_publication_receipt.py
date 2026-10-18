"""Focused safety contracts for queued committed publication receipts."""

from types import SimpleNamespace
import time

from contextor.core.live_state.ipc import CanonicalMutationCoordinator
from contextor.core.live_state.publication_receipt import (
    classify_publication_receipt,
    committed_publication_key,
    publish_committed_and_wait,
)


def _request(state_id="sid", revision=1, operation="submit_committed_publish"):
    return {
        "operation": operation,
        "repo_id": "repo",
        "state_id": state_id,
        "revision": revision,
        "idempotency_key": "fixed",
    }


def test_publication_idempotency_binds_exact_generation_without_conflict_execution():
    executed = []
    coordinator = CanonicalMutationCoordinator(
        lambda request: executed.append(request) or {"status": "ok", "revision": 1},
        lambda: 0,
    )
    try:
        first = coordinator.submit(_request())
        assert first["accepted"] is True
        assert coordinator.submit(_request())["job_id"] == first["job_id"]
        for conflicting in (_request(state_id="other"), _request(revision=2)):
            assert coordinator.submit(conflicting) == {
                "status": "error", "error": "publication_idempotency_conflict",
            }
        status = coordinator.status(first["job_id"])
        assert status["requested_state_id"] == "sid"
        assert status["requested_revision"] == 1
        deadline = time.monotonic() + 2
        while status["state"] not in {"completed", "failed", "cancelled"} and time.monotonic() < deadline:
            time.sleep(0.01)
            status = coordinator.status(first["job_id"])
        coordinator.close()
        assert len(executed) == 1
        assert executed[0]["state_id"] == "sid"
    finally:
        coordinator.close()


def test_update_file_duplicate_preserves_existing_key_behavior():
    coordinator = CanonicalMutationCoordinator(lambda _: {"status": "ok"}, lambda: 0)
    try:
        first = coordinator.submit({"file_path": "one.py", "idempotency_key": "fixed"})
        second = coordinator.submit({"file_path": "two.py", "idempotency_key": "fixed"})
        assert first["job_id"] == second["job_id"]
    finally:
        coordinator.close()


def _terminal(state_id="sid", revision=1):
    return {
        "status": "ok", "job_id": "mu-1", "state": "completed",
        "requested_state_id": state_id, "requested_revision": revision,
        "response": {"status": "ok", "revision": 1},
    }


def _classify(receipt):
    return classify_publication_receipt(
        receipt, job_id="mu-1", service_instance_id="service",
        process_start_identity="process", state_id="sid", revision=1,
    )


def test_receipt_requires_exact_job_generation_and_installed_revision():
    assert _classify(_terminal())["live_publish_status"] == "success"
    for receipt in (
        {**_terminal(), "job_id": "mu-other"},
        _terminal(state_id="other"),
        _terminal(revision=2),
        {**_terminal(), "response": {"status": "ok", "revision": 2}},
        {"status": "error", "error": "unknown_mutation_job", "revision": 1},
    ):
        result = _classify(receipt)
        assert result["live_publish_status"] != "success"
        assert result["live_publish_revision"] is None


def test_generation_key_is_deterministic_and_identity_sensitive():
    key = committed_publication_key("repo", "sid", 1)
    assert key.startswith("cp-") and len(key) == 67
    assert key == committed_publication_key("repo", "sid", 1)
    assert key != committed_publication_key("repo", "sid", 2)
    assert key != committed_publication_key("repo", "other", 1)


def test_receipt_uses_verified_service_identity_from_client():
    class Client:
        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")

        def submit_committed_publish(self, **kwargs):
            self.submitted = kwargs
            return {"status": "accepted", "accepted": True, "job_id": "mu-1"}

        def mutation_status(self, job_id):
            assert job_id == "mu-1"
            return _terminal()

        def authority_status(self):
            return {"status": "ok", "service_instance_id": "service",
                    "process_start_identity": "process"}

    client = Client()
    result = publish_committed_and_wait(
        client, repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
    )
    assert result["live_publish_status"] == "success"
    assert result["live_publish_service_instance_id"] == "service"
    assert result["live_publish_process_start_identity"] == "process"
    assert client.submitted["idempotency_key"] == committed_publication_key("repo", "sid", 1)


def test_changed_service_instance_rejects_completion():
    class Client:
        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")

        def submit_committed_publish(self, **kwargs):
            return {"status": "accepted", "accepted": True, "job_id": "mu-1"}

        def mutation_status(self, job_id):
            return _terminal()

        def authority_status(self):
            return {"status": "ok", "service_instance_id": "replacement",
                    "process_start_identity": "process"}

    result = publish_committed_and_wait(
        Client(), repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
    )
    assert result["live_publish_status"] == "unverified_authority_changed"
    assert result["live_publish_revision"] is None


def test_lost_first_admission_response_reuses_same_generation_job():
    class Client:
        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")

        def __init__(self):
            self.submissions = []

        def submit_committed_publish(self, **kwargs):
            self.submissions.append(kwargs)
            if len(self.submissions) == 1:
                raise TimeoutError("response lost")
            return {"status": "accepted", "accepted": True, "job_id": "mu-original"}

        def mutation_status(self, job_id):
            assert job_id == "mu-original"
            return {**_terminal(), "job_id": job_id}

        def authority_status(self):
            return {"status": "ok", "service_instance_id": "service",
                    "process_start_identity": "process"}

    client = Client()
    result = publish_committed_and_wait(
        client, repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
    )
    assert result["live_publish_status"] == "success"
    assert result["live_publish_job_id"] == "mu-original"
    assert len(client.submissions) == 2
    assert client.submissions[0]["idempotency_key"] == client.submissions[1]["idempotency_key"]


def test_lost_both_admission_responses_recovers_original_receipt_read_only():
    key = committed_publication_key("repo", "sid", 1)

    class Client:
        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")

        def __init__(self):
            self.submissions = 0
            self.lookups = 0

        def submit_committed_publish(self, **kwargs):
            self.submissions += 1
            raise TimeoutError("response lost")

        def lookup_committed_publish(self, *, idempotency_key, state_id, revision):
            self.lookups += 1
            assert (idempotency_key, state_id, revision) == (key, "sid", 1)
            return {**_terminal(), "job_id": "mu-original"}

        def mutation_status(self, job_id):
            assert job_id == "mu-original"
            return {**_terminal(), "job_id": job_id}

        def authority_status(self):
            return {"status": "ok", "service_instance_id": "service",
                    "process_start_identity": "process"}

    client = Client()
    result = publish_committed_and_wait(
        client, repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
    )
    assert client.submissions == 2
    assert client.lookups == 1
    assert result["live_publish_status"] == "success"
    assert result["live_publish_job_id"] == "mu-original"
    assert result["live_publish_idempotency_key"] == key


def test_lost_admission_and_missing_lookup_remain_pending_with_key():
    class Client:
        endpoint = SimpleNamespace(service_instance_id="service", process_start_identity="process")

        def submit_committed_publish(self, **kwargs):
            raise TimeoutError("response lost")

        def lookup_committed_publish(self, **kwargs):
            return {"status": "error", "error": "unknown_publication_job"}

    result = publish_committed_and_wait(
        Client(), repo_id="repo", state_id="sid", revision=1, origin="mcp_analysis",
    )
    assert result["live_publish_status"] == "pending_verification"
    assert result["live_publish_job_id"] is None
    assert result["live_publish_idempotency_key"] == committed_publication_key("repo", "sid", 1)
