import asyncio
import json
import os
from pathlib import Path

import pytest

from contextor import mcp_server
from contextor.mcp import analysis_jobs, documentation
from contextor.mcp.tools.get_analysis_status import get_analysis_status


def _create_job(
    root: Path,
    job_id_suffix: int,
    *,
    status: str = "completed",
    operation: str = "project",
    target: str | None = None,
    owner_pid: int | None = None,
    created_at: str = "2026-08-26T12:00:00Z",
    started_at: str | None = "2026-08-26T12:00:01Z",
    completed_at: str | None = "2026-08-26T12:00:10Z",
    message: str | None = "Done",
    error: str | None = None,
    live_publish_status: str = "success",
    live_publish_revision: int = 1,
    live_publish_warning: str | None = None,
    mtime_ns: int | None = None,
) -> dict:
    job_id = f"{job_id_suffix:032x}"
    effective_owner_pid = os.getpid() if owner_pid is None else owner_pid
    payload = {
        "job_id": job_id,
        "operation": operation,
        "repo_path": str(root),
        "target": target,
        "status": status,
        "created_at": created_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "updated_at": completed_at or created_at,
        "message": message,
        "error": error,
        "live_publish_status": live_publish_status,
        "live_publish_revision": live_publish_revision,
        "live_publish_warning": live_publish_warning,
        "owner_pid": effective_owner_pid,
    }
    analysis_jobs._write_analysis_job(root, payload)

    job_file = analysis_jobs._job_path(root, job_id)
    if mtime_ns is not None:
        os.utime(job_file, ns=(mtime_ns, mtime_ns))

    return payload


def _pending_publication_job(root: Path, suffix: int = 980) -> dict:
    from contextor.core.live_state.publication_receipt import committed_publication_key

    job = _create_job(
        root,
        suffix,
        live_publish_status="pending_verification",
        live_publish_revision=None,
    )
    job.update({
        "live_publish_job_id": None,
        "live_publish_idempotency_key": committed_publication_key(
            "repo-id", "sid", 7
        ),
        "live_publish_service_instance_id": "service",
        "live_publish_process_start_identity": "process",
        "live_publish_expected_state_id": "sid",
        "live_publish_expected_revision": 7,
    })
    analysis_jobs._write_analysis_job(root, job)
    return job


def _patch_reconciliation_diagnostics(monkeypatch) -> None:
    import contextor.mcp.tools.get_analysis_status as status_module

    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
    monkeypatch.setattr(
        status_module,
        "diagnostics_summary_for_completed_job",
        lambda _summary, _job: {"attention_required": False},
    )


def _status_response(root: Path, job: dict) -> dict:
    return json.loads(get_analysis_status(str(root), job_id=job["job_id"]))


def _r3_reconcile(
    tmp_path, monkeypatch, *,
    authority_sequence, receipt_state="completed", response=None,
    durable_job_id="mu-exact", lookup_job_id="mu-exact",
):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module

    _patch_reconciliation_diagnostics(monkeypatch)
    job = _pending_publication_job(tmp_path)
    job["live_publish_job_id"] = durable_job_id
    analysis_jobs._write_analysis_job(tmp_path, job)
    calls = []
    replies = iter(authority_sequence)
    expected_authority = {
        "status": "ok", "service_instance_id": "service",
        "process_start_identity": "process", "repo_id": "repo-id",
    }

    class Client:
        endpoint = SimpleNamespace(
            service_instance_id="service", process_start_identity="process"
        )

        def authority_status(self):
            calls.append("authority")
            reply = next(replies)
            if isinstance(reply, BaseException):
                raise reply
            return expected_authority if reply == "same" else reply

        def lookup_committed_publish(self, **kwargs):
            calls.append("lookup")
            assert kwargs == {
                "idempotency_key": job["live_publish_idempotency_key"],
                "state_id": "sid", "revision": 7,
            }
            return {
                "status": "ok", "job_id": lookup_job_id,
                "requested_state_id": "sid", "requested_revision": 7,
            }

        def mutation_status(self, mutation_job_id):
            calls.append("mutation")
            assert mutation_job_id == "mu-exact"
            return {
                "status": "ok", "job_id": mutation_job_id,
                "requested_state_id": "sid", "requested_revision": 7,
                "state": receipt_state,
                "response": response if response is not None else {
                    "status": "ok", "revision": 7,
                },
            }

        def submit_committed_publish(self, **kwargs):
            raise AssertionError("read-only reconciliation must not publish")

    monkeypatch.setattr(
        live_state_module, "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
    )
    result = _status_response(tmp_path, job)
    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
    return job, result, stored, calls


def _r3_assert_identity_preserved(job, stored):
    assert stored["live_publish_idempotency_key"] == job["live_publish_idempotency_key"]
    assert stored["live_publish_service_instance_id"] == "service"
    assert stored["live_publish_process_start_identity"] == "process"
    assert stored["live_publish_expected_state_id"] == "sid"
    assert stored["live_publish_expected_revision"] == 7


def test_r3_t01_matching_final_authority_allows_success(tmp_path, monkeypatch):
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same", "same"]
    )
    assert calls == ["authority", "mutation", "authority"]
    assert result["live_publish_status"] == stored["live_publish_status"] == "success"
    assert result["live_publish_revision"] == stored["live_publish_revision"] == 7
    _r3_assert_identity_preserved(job, stored)


def test_r3_t02_final_service_replacement_fences_success(tmp_path, monkeypatch):
    replacement = {
        "status": "ok", "service_instance_id": "other",
        "process_start_identity": "process",
    }
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same", replacement]
    )
    assert calls == ["authority", "mutation", "authority"]
    assert result["live_publish_status"] == "unverified_authority_changed"
    assert result["live_publish_revision"] is None
    assert stored["live_publish_status"] == "pending_verification"
    assert stored["live_publish_revision"] is None
    _r3_assert_identity_preserved(job, stored)


def test_r3_t03_final_process_replacement_fences_success(tmp_path, monkeypatch):
    replacement = {
        "status": "ok", "service_instance_id": "service",
        "process_start_identity": "other",
    }
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same", replacement]
    )
    assert calls == ["authority", "mutation", "authority"]
    assert result["live_publish_status"] == "unverified_authority_changed"
    assert result["live_publish_revision"] is None
    assert stored["live_publish_status"] == "pending_verification"
    assert stored["live_publish_revision"] is None
    _r3_assert_identity_preserved(job, stored)


def test_r3_t04_final_authority_timeout_stays_pending(tmp_path, monkeypatch):
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same", TimeoutError("timeout")]
    )
    assert calls == ["authority", "mutation", "authority"]
    assert result["live_publish_status"] == stored["live_publish_status"] == "pending_verification"
    assert result["live_publish_revision"] is None
    assert stored["live_publish_revision"] is None
    _r3_assert_identity_preserved(job, stored)


@pytest.mark.parametrize("final_authority", [
    None, "malformed", {"status": "ok", "service_instance_id": "service"},
    {"status": "unavailable"},
], ids=["none", "malformed", "missing-identity", "not-ok"])
def test_r3_t05_unknown_final_authority_stays_pending(
    tmp_path, monkeypatch, final_authority
):
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same", final_authority]
    )
    assert calls == ["authority", "mutation", "authority"]
    assert result["live_publish_status"] == stored["live_publish_status"] == "pending_verification"
    assert result["live_publish_revision"] is None
    assert stored["live_publish_revision"] is None
    _r3_assert_identity_preserved(job, stored)


@pytest.mark.parametrize("receipt_state,response,expected", [
    ("failed", None, "failed"),
    ("completed", {"status": "ok", "revision": 7, "resync_required": True}, "recovery_required"),
])
@pytest.mark.parametrize("final_authority,accepted", [
    ("same", True),
    ({"status": "ok", "service_instance_id": "other",
      "process_start_identity": "process"}, False),
    (None, False),
])
def test_r3_t06_other_terminal_states_require_final_authority(
    tmp_path, monkeypatch, receipt_state, response, expected, final_authority, accepted
):
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same", final_authority],
        receipt_state=receipt_state, response=response,
    )
    assert calls == ["authority", "mutation", "authority"]
    if accepted:
        assert result["live_publish_status"] == stored["live_publish_status"] == expected
    else:
        assert result["live_publish_status"] == (
            "pending_verification" if final_authority is None
            else "unverified_authority_changed"
        )
        assert stored["live_publish_status"] == "pending_verification"
        assert stored["live_publish_revision"] is None
    _r3_assert_identity_preserved(job, stored)


def test_r3_t07_empty_durable_job_id_recovers_by_lookup(tmp_path, monkeypatch):
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same", "same"], durable_job_id=""
    )
    assert calls == ["authority", "lookup", "mutation", "authority"]
    assert result["live_publish_status"] == stored["live_publish_status"] == "success"
    assert result["live_publish_job_id"] == stored["live_publish_job_id"] == "mu-exact"
    _r3_assert_identity_preserved(job, stored)


def test_r3_t08_whitespace_durable_job_id_recovers_by_lookup(tmp_path, monkeypatch):
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same", "same"], durable_job_id="  "
    )
    assert calls == ["authority", "lookup", "mutation", "authority"]
    assert result["live_publish_status"] == stored["live_publish_status"] == "success"
    assert result["live_publish_job_id"] == stored["live_publish_job_id"] == "mu-exact"
    _r3_assert_identity_preserved(job, stored)


@pytest.mark.parametrize("lookup_job_id", ["", "  "], ids=["empty", "whitespace"])
def test_r3_t09_invalid_lookup_job_id_is_not_persisted(
    tmp_path, monkeypatch, lookup_job_id
):
    job, result, stored, calls = _r3_reconcile(
        tmp_path, monkeypatch, authority_sequence=["same"],
        durable_job_id="", lookup_job_id=lookup_job_id,
    )
    assert calls == ["authority", "lookup"]
    assert result["live_publish_status"] == stored["live_publish_status"] == "pending_verification"
    assert result["live_publish_job_id"] == stored["live_publish_job_id"] == ""
    _r3_assert_identity_preserved(job, stored)


def test_r3_t10_later_read_only_recovery_after_final_timeout(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module

    _patch_reconciliation_diagnostics(monkeypatch)
    job = _pending_publication_job(tmp_path)
    job["live_publish_job_id"] = "mu-exact"
    analysis_jobs._write_analysis_job(tmp_path, job)
    calls = []
    replies = iter(["same", TimeoutError("timeout"), "same", "same"])

    class Client:
        endpoint = SimpleNamespace(
            service_instance_id="service", process_start_identity="process"
        )

        def authority_status(self):
            calls.append("authority")
            reply = next(replies)
            if isinstance(reply, BaseException):
                raise reply
            return {
                "status": "ok", "service_instance_id": "service",
                "process_start_identity": "process", "repo_id": "repo-id",
            }

        def mutation_status(self, mutation_job_id):
            calls.append("mutation")
            assert mutation_job_id == "mu-exact"
            return {
                "status": "ok", "job_id": mutation_job_id, "state": "completed",
                "requested_state_id": "sid", "requested_revision": 7,
                "response": {"status": "ok", "revision": 7},
            }

        def submit_committed_publish(self, **kwargs):
            raise AssertionError("status must never publish")

        def lookup_committed_publish(self, **kwargs):
            raise AssertionError("valid durable job ID needs no lookup")

    monkeypatch.setattr(
        live_state_module, "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
    )
    first = _status_response(tmp_path, job)
    first_stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
    assert first["live_publish_status"] == first_stored["live_publish_status"] == "pending_verification"
    assert first["live_publish_revision"] is None
    _r3_assert_identity_preserved(job, first_stored)

    second = _status_response(tmp_path, job)
    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
    assert calls == ["authority", "mutation", "authority", "authority", "mutation", "authority"]
    assert second["live_publish_status"] == stored["live_publish_status"] == "success"
    assert second["live_publish_revision"] == stored["live_publish_revision"] == 7
    _r3_assert_identity_preserved(job, stored)


@pytest.mark.parametrize(
    "authority_result",
    [
        TimeoutError("authority timeout"),
        ConnectionError("authority transport failed"),
        None,
        {"status": "unavailable"},
        {"status": "error", "error": "authority_unavailable"},
    ],
    ids=["timeout", "transport-error", "non-object", "unavailable", "error-status"],
)
def test_authority_status_uncertainty_retains_pending_without_lookup(
    tmp_path, monkeypatch, authority_result
):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module

    _patch_reconciliation_diagnostics(monkeypatch)
    job = _pending_publication_job(tmp_path)
    calls = []

    class Client:
        endpoint = SimpleNamespace(
            service_instance_id="service", process_start_identity="process"
        )

        def authority_status(self):
            if isinstance(authority_result, BaseException):
                raise authority_result
            return authority_result

        def lookup_committed_publish(self, **kwargs):
            calls.append(("lookup", kwargs))
            raise AssertionError("uncertain authority must not trigger lookup")

        def mutation_status(self, job_id):
            calls.append(("status", job_id))
            raise AssertionError("uncertain authority must not trigger status")

    monkeypatch.setattr(
        live_state_module,
        "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=True: Client(),
    )

    result = _status_response(tmp_path, job)
    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
    assert result["live_publish_status"] == "pending_verification"
    assert stored["live_publish_status"] == "pending_verification"
    assert stored["live_publish_job_id"] is None
    assert calls == []


def test_missing_client_retains_pending_without_mutation_lookup(tmp_path, monkeypatch):
    import contextor.core.live_state as live_state_module

    _patch_reconciliation_diagnostics(monkeypatch)
    job = _pending_publication_job(tmp_path)
    connect_calls = []

    def connect(_root, *, reconcile_missing_endpoint_binding=True):
        connect_calls.append(reconcile_missing_endpoint_binding)
        return None

    monkeypatch.setattr(live_state_module, "connect", connect)
    result = _status_response(tmp_path, job)
    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
    assert connect_calls == [False]
    assert result["live_publish_status"] == "pending_verification"
    assert stored["live_publish_status"] == "pending_verification"
    assert stored["live_publish_job_id"] is None


def test_missing_authority_identity_is_uncertain_not_replacement(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module

    _patch_reconciliation_diagnostics(monkeypatch)
    job = _pending_publication_job(tmp_path)
    lookup_calls = []

    class Client:
        endpoint = SimpleNamespace(
            service_instance_id="service", process_start_identity="process"
        )

        def authority_status(self):
            return {"status": "ok", "repo_id": "repo-id"}

        def lookup_committed_publish(self, **kwargs):
            lookup_calls.append(kwargs)

    monkeypatch.setattr(
        live_state_module,
        "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=True: Client(),
    )
    result = _status_response(tmp_path, job)
    assert result["live_publish_status"] == "pending_verification"
    assert lookup_calls == []


def test_explicit_authority_service_mismatch_is_unverified(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module

    _patch_reconciliation_diagnostics(monkeypatch)
    job = _pending_publication_job(tmp_path)
    lookup_calls = []

    class Client:
        endpoint = SimpleNamespace(
            service_instance_id="service", process_start_identity="process"
        )

        def authority_status(self):
            return {
                "status": "ok",
                "service_instance_id": "replacement",
                "process_start_identity": "process",
                "repo_id": "repo-id",
            }

        def lookup_committed_publish(self, **kwargs):
            lookup_calls.append(kwargs)

    monkeypatch.setattr(
        live_state_module,
        "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=True: Client(),
    )
    result = _status_response(tmp_path, job)
    assert result["live_publish_status"] == "unverified_authority_changed"
    assert lookup_calls == []


@pytest.mark.parametrize(
    "lookup_result",
    [
        {"status": "ok", "job_id": "mu-bad", "requested_state_id": "other",
         "requested_revision": 7},
        {"status": "ok", "job_id": "mu-bad", "requested_state_id": "sid",
         "requested_revision": 8},
        {"status": "ok", "job_id": "mu-bad", "requested_state_id": "sid",
         "requested_revision": True},
    ],
    ids=["wrong-state-id", "wrong-revision", "boolean-revision"],
)
def test_invalid_lookup_identity_is_not_persisted(
    tmp_path, monkeypatch, lookup_result
):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module

    _patch_reconciliation_diagnostics(monkeypatch)
    job = _pending_publication_job(tmp_path)
    calls = []

    class Client:
        endpoint = SimpleNamespace(
            service_instance_id="service", process_start_identity="process"
        )

        def authority_status(self):
            return {
                "status": "ok",
                "service_instance_id": "service",
                "process_start_identity": "process",
                "repo_id": "repo-id",
            }

        def lookup_committed_publish(self, **kwargs):
            calls.append(("lookup", kwargs))
            return lookup_result

        def mutation_status(self, mutation_job_id):
            calls.append(("status", mutation_job_id))
            raise AssertionError("invalid lookup must not reach mutation status")

        def submit_committed_publish(self, **kwargs):
            calls.append(("submit", kwargs))
            raise AssertionError("status recovery must never submit")

        def publish(self, **kwargs):
            calls.append(("publish", kwargs))
            raise AssertionError("status recovery must never publish")

        def update_file(self, **kwargs):
            calls.append(("update_file", kwargs))
            raise AssertionError("status recovery must never update_file")

        def analyze_project(self, **kwargs):
            calls.append(("full", kwargs))
            raise AssertionError("status recovery must never run FULL")

    monkeypatch.setattr(
        live_state_module,
        "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=True: Client(),
    )
    result = _status_response(tmp_path, job)
    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
    assert result["live_publish_status"] == "pending_verification"
    assert result["live_publish_job_id"] is None
    assert stored["live_publish_status"] == "pending_verification"
    assert stored["live_publish_job_id"] is None
    assert stored["live_publish_idempotency_key"] == job[
        "live_publish_idempotency_key"
    ]
    assert [name for name, _ in calls] == ["lookup"]


def test_invalid_lookup_then_valid_lookup_recovers_original_publication(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module

    _patch_reconciliation_diagnostics(monkeypatch)
    job = _pending_publication_job(tmp_path)
    calls = []

    class Client:
        endpoint = SimpleNamespace(
            service_instance_id="service", process_start_identity="process"
        )

        def authority_status(self):
            return {
                "status": "ok",
                "service_instance_id": "service",
                "process_start_identity": "process",
                "repo_id": "repo-id",
            }

        def lookup_committed_publish(self, **kwargs):
            calls.append(("lookup", kwargs))
            if sum(name == "lookup" for name, _ in calls) == 1:
                return {
                    "status": "ok", "job_id": "mu-wrong",
                    "requested_state_id": "other", "requested_revision": 7,
                }
            return {
                "status": "ok", "job_id": "mu-exact",
                "requested_state_id": "sid", "requested_revision": 7,
            }

        def mutation_status(self, mutation_job_id):
            calls.append(("status", mutation_job_id))
            return {
                "status": "ok", "job_id": mutation_job_id, "state": "completed",
                "requested_state_id": "sid", "requested_revision": 7,
                "response": {"status": "ok", "revision": 7},
            }

        def submit_committed_publish(self, **kwargs):
            raise AssertionError("recovery retry must never submit")

        def publish(self, **kwargs):
            raise AssertionError("recovery retry must never publish")

        def update_file(self, **kwargs):
            raise AssertionError("recovery retry must never update_file")

        def analyze_project(self, **kwargs):
            raise AssertionError("recovery retry must never run FULL")

    connect_flags = []

    def connect(_root, *, reconcile_missing_endpoint_binding=True):
        connect_flags.append(reconcile_missing_endpoint_binding)
        return Client()

    monkeypatch.setattr(live_state_module, "connect", connect)
    first = _status_response(tmp_path, job)
    after_invalid = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
    assert first["live_publish_status"] == "pending_verification"
    assert after_invalid["live_publish_job_id"] is None
    assert after_invalid["live_publish_idempotency_key"] == job[
        "live_publish_idempotency_key"
    ]

    second = _status_response(tmp_path, job)
    stored = analysis_jobs._read_analysis_job(tmp_path, job["job_id"])
    assert second["live_publish_status"] == "success"
    assert second["live_publish_job_id"] == "mu-exact"
    assert stored["live_publish_status"] == "success"
    assert stored["live_publish_job_id"] == "mu-exact"
    assert [name for name, _ in calls] == ["lookup", "lookup", "status"]
    assert connect_flags == [False, False]


def test_pending_publication_reconciles_only_exact_job_on_same_authority(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module

    root = tmp_path
    job = _create_job(root, 990, live_publish_status="pending_verification",
                      live_publish_revision=None)
    job.update({
        "live_publish_job_id": "mu-exact",
        "live_publish_service_instance_id": "service",
        "live_publish_process_start_identity": "process",
        "live_publish_expected_state_id": "sid",
        "live_publish_expected_revision": 7,
    })
    analysis_jobs._write_analysis_job(root, job)
    calls = []

    class Client:
        endpoint = SimpleNamespace(service_instance_id="replacement",
                                   process_start_identity="process")

        def authority_status(self):
            return {"status": "ok", "service_instance_id": self.endpoint.service_instance_id,
                    "process_start_identity": self.endpoint.process_start_identity,
                    "repo_id": "repo-id"}

        def mutation_status(self, job_id):
            calls.append(job_id)
            return {"status": "ok", "job_id": job_id, "state": "completed",
                    "requested_state_id": "sid", "requested_revision": 7,
                    "response": {"status": "ok", "revision": 7}}

    def connect(_root, *, reconcile_missing_endpoint_binding=True):
        if reconcile_missing_endpoint_binding:
            return None
        return Client()

    monkeypatch.setattr(live_state_module, "connect", connect)
    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
    assert result["live_publish_status"] == "unverified_authority_changed"
    assert result["live_publish_revision"] is None
    assert calls == []
    assert analysis_jobs._read_analysis_job(root, job["job_id"])["live_publish_status"] == "pending_verification"

    Client.endpoint.service_instance_id = "service"
    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
    assert result["live_publish_status"] == "success"
    assert result["live_publish_revision"] == 7
    assert calls == ["mu-exact"]
    assert analysis_jobs._read_analysis_job(root, job["job_id"])["live_publish_status"] == "success"


def test_pending_publication_without_job_id_recovers_by_canonical_key_read_only(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module
    from contextor.core.live_state.publication_receipt import committed_publication_key

    root = tmp_path
    import contextor.mcp.tools.get_analysis_status as status_module
    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
    monkeypatch.setattr(status_module, "diagnostics_summary_for_completed_job",
                        lambda _summary, _job: {"attention_required": False})
    job = _create_job(root, 991, live_publish_status="pending_verification",
                      live_publish_revision=None)
    key = committed_publication_key("repo-id", "sid", 7)
    job.update({
        "live_publish_job_id": None,
        "live_publish_idempotency_key": key,
        "live_publish_service_instance_id": "service",
        "live_publish_process_start_identity": "process",
        "live_publish_expected_state_id": "sid",
        "live_publish_expected_revision": 7,
    })
    analysis_jobs._write_analysis_job(root, job)
    calls = []

    class Client:
        endpoint = SimpleNamespace(service_instance_id="service",
                                   process_start_identity="process")

        def authority_status(self):
            return {"status": "ok", "service_instance_id": "service",
                    "process_start_identity": "process", "repo_id": "repo-id"}

        def lookup_committed_publish(self, *, idempotency_key, state_id, revision):
            calls.append(("lookup", idempotency_key, state_id, revision))
            return {"status": "ok", "job_id": "mu-recovered", "state": "completed",
                    "requested_state_id": "sid", "requested_revision": 7,
                    "response": {"status": "ok", "revision": 7}}

        def mutation_status(self, recovered_job_id):
            calls.append(("status", recovered_job_id))
            return {"status": "ok", "job_id": recovered_job_id, "state": "completed",
                    "requested_state_id": "sid", "requested_revision": 7,
                    "response": {"status": "ok", "revision": 7}}

    def connect(_root, *, reconcile_missing_endpoint_binding=True):
        assert reconcile_missing_endpoint_binding is False
        return Client()

    monkeypatch.setattr(live_state_module, "connect", connect)
    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
    assert calls == [("lookup", key, "sid", 7), ("status", "mu-recovered")]
    assert result["live_publish_status"] == "success"
    assert result["live_publish_job_id"] == "mu-recovered"
    stored = analysis_jobs._read_analysis_job(root, job["job_id"])
    assert stored["live_publish_job_id"] == "mu-recovered"
    assert stored["live_publish_idempotency_key"] == key


def test_pending_publication_missing_or_replaced_authority_stays_unverified(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module
    from contextor.core.live_state.publication_receipt import committed_publication_key

    root = tmp_path
    import contextor.mcp.tools.get_analysis_status as status_module
    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
    monkeypatch.setattr(status_module, "diagnostics_summary_for_completed_job",
                        lambda _summary, _job: {"attention_required": False})
    job = _create_job(root, 992, live_publish_status="pending_verification",
                      live_publish_revision=None)
    job.update({
        "live_publish_job_id": None,
        "live_publish_idempotency_key": committed_publication_key("repo-id", "sid", 7),
        "live_publish_service_instance_id": "service",
        "live_publish_process_start_identity": "process",
        "live_publish_expected_state_id": "sid",
        "live_publish_expected_revision": 7,
    })
    analysis_jobs._write_analysis_job(root, job)
    lookup_calls = []

    class Client:
        endpoint = SimpleNamespace(service_instance_id="replacement",
                                   process_start_identity="process")

        def authority_status(self):
            return {"status": "ok", "service_instance_id": "replacement",
                    "process_start_identity": "process", "repo_id": "repo-id"}

        def lookup_committed_publish(self, **kwargs):
            lookup_calls.append(kwargs)
            return {"status": "error", "error": "unknown_publication_job"}

    monkeypatch.setattr(
        live_state_module, "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
    )
    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
    assert result["live_publish_status"] == "unverified_authority_changed"
    assert result["live_publish_revision"] is None
    assert lookup_calls == []
    assert analysis_jobs._read_analysis_job(root, job["job_id"])["live_publish_status"] == "pending_verification"


def test_pending_publication_unknown_key_lookup_remains_pending(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module
    from contextor.core.live_state.publication_receipt import committed_publication_key

    root = tmp_path
    import contextor.mcp.tools.get_analysis_status as status_module
    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
    monkeypatch.setattr(status_module, "diagnostics_summary_for_completed_job",
                        lambda _summary, _job: {"attention_required": False})
    job = _create_job(root, 993, live_publish_status="pending_verification",
                      live_publish_revision=None)
    job.update({
        "live_publish_job_id": None,
        "live_publish_idempotency_key": committed_publication_key("repo-id", "sid", 7),
        "live_publish_service_instance_id": "service",
        "live_publish_process_start_identity": "process",
        "live_publish_expected_state_id": "sid",
        "live_publish_expected_revision": 7,
    })
    analysis_jobs._write_analysis_job(root, job)

    class Client:
        endpoint = SimpleNamespace(service_instance_id="service",
                                   process_start_identity="process")

        def authority_status(self):
            return {"status": "ok", "service_instance_id": "service",
                    "process_start_identity": "process", "repo_id": "repo-id"}

        def lookup_committed_publish(self, **kwargs):
            return {"status": "error", "error": "unknown_publication_job"}

    monkeypatch.setattr(
        live_state_module, "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
    )
    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
    assert result["live_publish_status"] == "pending_verification"
    assert result["live_publish_job_id"] is None
    assert result["live_publish_revision"] is None
    stored = analysis_jobs._read_analysis_job(root, job["job_id"])
    assert stored["live_publish_status"] == "pending_verification"
    assert stored["live_publish_job_id"] is None


def test_running_publication_recovery_persists_job_id_and_stays_pending(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import contextor.core.live_state as live_state_module
    import contextor.mcp.tools.get_analysis_status as status_module
    from contextor.core.live_state.publication_receipt import committed_publication_key

    root = tmp_path
    monkeypatch.setattr(status_module, "diagnostics_summary", lambda _root: {})
    monkeypatch.setattr(status_module, "diagnostics_summary_for_completed_job",
                        lambda _summary, _job: {"attention_required": False})
    job = _create_job(root, 994, live_publish_status="pending_verification",
                      live_publish_revision=None)
    job.update({
        "live_publish_job_id": None,
        "live_publish_idempotency_key": committed_publication_key("repo-id", "sid", 7),
        "live_publish_service_instance_id": "service",
        "live_publish_process_start_identity": "process",
        "live_publish_expected_state_id": "sid",
        "live_publish_expected_revision": 7,
    })
    analysis_jobs._write_analysis_job(root, job)

    class Client:
        endpoint = SimpleNamespace(service_instance_id="service",
                                   process_start_identity="process")

        def authority_status(self):
            return {"status": "ok", "service_instance_id": "service",
                    "process_start_identity": "process", "repo_id": "repo-id"}

        def lookup_committed_publish(self, **kwargs):
            return {"status": "ok", "job_id": "mu-running", "state": "running",
                    "requested_state_id": "sid", "requested_revision": 7}

        def mutation_status(self, mutation_job_id):
            assert mutation_job_id == "mu-running"
            return {"status": "ok", "job_id": mutation_job_id, "state": "running",
                    "requested_state_id": "sid", "requested_revision": 7}

    monkeypatch.setattr(
        live_state_module, "connect",
        lambda _root, *, reconcile_missing_endpoint_binding=False: Client(),
    )
    result = json.loads(get_analysis_status(str(root), job_id=job["job_id"]))
    assert result["live_publish_status"] == "pending_verification"
    assert result["live_publish_job_id"] == "mu-running"
    assert result["live_publish_revision"] is None
    stored = analysis_jobs._read_analysis_job(root, job["job_id"])
    assert stored["live_publish_status"] == "pending_verification"
    assert stored["live_publish_job_id"] == "mu-running"


def test_analysis_status_concurrency__multiple_active_without_job_id_returns_ambiguity(tmp_path):
    root = tmp_path
    foreign_owner = os.getpid() + 100000
    _create_job(root, 1, status="queued", owner_pid=foreign_owner, mtime_ns=1_000_000_000)
    _create_job(root, 2, status="running", owner_pid=foreign_owner, mtime_ns=2_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    assert res["job_id"] is None
    assert res["repo_path"] == str(root)
    assert res["active_job_count"] == 2
    assert len(res["active_jobs"]) == 2
    assert res["truncated"] is False
    assert "Multiple queued/running analysis jobs exist." in res["message"]
    assert "analysis_coverage" not in res


def test_analysis_status_concurrency__explicit_job_id_bypasses_ambiguity(tmp_path, monkeypatch):
    root = tmp_path
    j1 = _create_job(root, 1, status="queued", mtime_ns=1_000_000_000)
    _create_job(root, 2, status="running", mtime_ns=2_000_000_000)

    def fail_if_active_called(*_args, **_kwargs):
        raise AssertionError("_active_analysis_jobs MUST NOT be called when explicit job_id is passed!")

    monkeypatch.setattr(analysis_jobs, "_active_analysis_jobs", fail_if_active_called)
    monkeypatch.setattr(
        analysis_jobs,
        "_is_current_process_analysis_task_active",
        lambda _job_id: True,
    )

    raw = get_analysis_status(str(root), job_id=j1["job_id"])
    res = json.loads(raw)

    assert res["status"] == "queued"
    assert res["job_id"] == j1["job_id"]


def test_analysis_status_concurrency__single_active_does_not_override_newer_completed_latest(tmp_path):
    root = tmp_path
    _create_job(
        root,
        1,
        status="running",
        owner_pid=os.getpid() + 100000,
        mtime_ns=1_000_000_000,
    )
    j2 = _create_job(root, 2, status="completed", mtime_ns=2_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "completed"
    assert res["job_id"] == j2["job_id"]


def test_analysis_status_concurrency__zero_active_preserves_latest_terminal(tmp_path):
    root = tmp_path
    _create_job(root, 1, status="failed", mtime_ns=1_000_000_000)
    j2 = _create_job(root, 2, status="completed", mtime_ns=2_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "completed"
    assert res["job_id"] == j2["job_id"]


def test_analysis_status_concurrency__completed_jobs_do_not_count_as_active(tmp_path):
    root = tmp_path
    _create_job(
        root,
        1,
        status="queued",
        owner_pid=os.getpid() + 100000,
        mtime_ns=1_000_000_000,
    )
    _create_job(root, 2, status="failed", mtime_ns=2_000_000_000)
    j3 = _create_job(root, 3, status="completed", mtime_ns=3_000_000_000)

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    # active_count is 1 (job 1), so no ambiguity; latest mtime is job 3 (completed)
    assert res["status"] == "completed"
    assert res["job_id"] == j3["job_id"]


def test_analysis_status_concurrency__active_candidates_are_deterministic_newest_first(tmp_path):
    root = tmp_path
    foreign_owner = os.getpid() + 100000
    j1 = _create_job(
        root,
        1,
        status="queued",
        owner_pid=foreign_owner,
        mtime_ns=1_000_000_000,
    )
    j2 = _create_job(
        root,
        2,
        status="running",
        owner_pid=foreign_owner,
        mtime_ns=3_000_000_000,
    )
    j3 = _create_job(
        root,
        3,
        status="running",
        owner_pid=foreign_owner,
        mtime_ns=2_000_000_000,
    )

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    returned_ids = [item["job_id"] for item in res["active_jobs"]]
    assert returned_ids == [j2["job_id"], j3["job_id"], j1["job_id"]]


def test_analysis_status_concurrency__equal_mtime_uses_job_id_tiebreak(tmp_path):
    root = tmp_path
    foreign_owner = os.getpid() + 100000
    j1 = _create_job(
        root,
        1,
        status="queued",
        owner_pid=foreign_owner,
        mtime_ns=1_000_000_000,
    )
    j2 = _create_job(
        root,
        2,
        status="running",
        owner_pid=foreign_owner,
        mtime_ns=1_000_000_000,
    )

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    returned_ids = [item["job_id"] for item in res["active_jobs"]]
    assert returned_ids == [j1["job_id"], j2["job_id"]]


def test_analysis_status_concurrency__candidate_list_is_bounded_to_five(tmp_path):
    root = tmp_path
    foreign_owner = os.getpid() + 100000
    for i in range(1, 8):
        _create_job(
            root,
            i,
            status="running",
            owner_pid=foreign_owner,
            mtime_ns=i * 1_000_000_000,
        )

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "ambiguous_job"
    assert res["active_job_count"] == 7
    assert len(res["active_jobs"]) == 5
    assert res["truncated"] is True
    # Newest first: jobs 7, 6, 5, 4, 3
    assert res["active_jobs"][0]["job_id"] == f"{7:032x}"
    assert res["active_jobs"][4]["job_id"] == f"{3:032x}"


def test_analysis_status_concurrency__ambiguity_response_does_not_mutate_jobs(tmp_path):
    root = tmp_path
    j1 = _create_job(root, 1, status="queued", owner_pid=999999, mtime_ns=1_000_000_000)
    j2 = _create_job(root, 2, status="running", owner_pid=999999, mtime_ns=2_000_000_000)

    before_1 = analysis_jobs._read_analysis_job(root, j1["job_id"])
    before_2 = analysis_jobs._read_analysis_job(root, j2["job_id"])

    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)
    assert res["status"] == "ambiguous_job"

    after_1 = analysis_jobs._read_analysis_job(root, j1["job_id"])
    after_2 = analysis_jobs._read_analysis_job(root, j2["job_id"])

    assert before_1 == after_1
    assert before_2 == after_2


def test_analysis_status_concurrency__explicit_stale_owner_interruption_is_preserved(tmp_path):
    root = tmp_path
    stale_pid = os.getpid() + 100000
    j1 = _create_job(root, 1, status="running", owner_pid=stale_pid, mtime_ns=1_000_000_000)

    raw = get_analysis_status(str(root), job_id=j1["job_id"])
    res = json.loads(raw)

    assert res["status"] == "interrupted"
    assert res["error"] == "owner_process_changed"

    persisted = analysis_jobs._read_analysis_job(root, j1["job_id"])
    assert persisted["status"] == "interrupted"
    assert persisted["error"] == "owner_process_changed"


def test_analysis_status_concurrency__no_jobs_still_returns_not_found(tmp_path):
    root = tmp_path
    raw = get_analysis_status(str(root), job_id=None)
    res = json.loads(raw)

    assert res["status"] == "not_found"
    assert res["job_id"] is None
    assert res["repo_path"] == str(root)


def test_analysis_status_concurrency__runtime_description_is_index_backed():
    tool = mcp_server.mcp._tool_manager._tools["get_analysis_status"]
    index = documentation.load_documentation_index()
    entry = next(
        item for item in index["tools"]
        if item["tool"] == "get_analysis_status"
    )

    assert tool.description == entry["short_description"]
    assert tool.fn.__doc__ is None

    description = tool.description.lower()
    assert "explicit job_id" in description
    assert "multiple" in description
    assert "queued/running" in description
    assert "ambiguous_job" in description


def test_analysis_job_write__retries_permission_error_only_on_replace(
    tmp_path, monkeypatch
):
    real_replace = analysis_jobs.os.replace
    replace_calls = []
    sleep_calls = []

    def flaky_replace(source, target):
        replace_calls.append((source, target))
        if len(replace_calls) < 3:
            raise PermissionError("replace temporarily blocked")
        real_replace(source, target)

    monkeypatch.setattr(analysis_jobs.os, "replace", flaky_replace)
    monkeypatch.setattr(analysis_jobs.time, "sleep", sleep_calls.append)

    job_id = f"{101:032x}"
    analysis_jobs._write_analysis_job(
        tmp_path,
        {"job_id": job_id, "status": "queued"},
    )

    assert len(replace_calls) == 3
    assert sleep_calls == [
        analysis_jobs._ANALYSIS_JOB_REPLACE_RETRY_SECONDS,
        analysis_jobs._ANALYSIS_JOB_REPLACE_RETRY_SECONDS,
    ]
    persisted = analysis_jobs._read_analysis_job(tmp_path, job_id)
    assert persisted is not None
    assert persisted["status"] == "queued"


def test_analysis_job_write__does_not_retry_generic_oserror(
    tmp_path, monkeypatch
):
    replace_calls = []
    sleep_calls = []

    def failing_replace(source, target):
        replace_calls.append((source, target))
        raise OSError("replace failed")

    monkeypatch.setattr(analysis_jobs.os, "replace", failing_replace)
    monkeypatch.setattr(analysis_jobs.time, "sleep", sleep_calls.append)

    with pytest.raises(OSError, match="replace failed"):
        analysis_jobs._write_analysis_job(
            tmp_path,
            {"job_id": f"{102:032x}", "status": "queued"},
        )

    assert len(replace_calls) == 1
    assert sleep_calls == []


def test_analysis_job_execution__progress_persistence_failure_does_not_abort(
    tmp_path, monkeypatch, capsys
):
    job = _create_job(
        tmp_path,
        103,
        status="queued",
        operation="layer",
        started_at=None,
        completed_at=None,
        live_publish_status="not_applicable",
        live_publish_revision=None,
    )
    writes = []

    async def fake_worker(
        operation,
        root,
        target=None,
        exclude_paths=None,
        log=None,
    ):
        assert operation == "layer"
        assert log is not None
        log("progress")
        return {}

    def flaky_write(root, payload):
        writes.append(dict(payload))
        if payload.get("message") == "progress":
            raise OSError("progress persistence failed")

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(analysis_jobs, "_write_analysis_job", flaky_write)

    asyncio.run(
        analysis_jobs._execute_analysis_job(
            tmp_path,
            job,
            None,
            None,
        )
    )

    assert any(item.get("status") == "completed" for item in writes)
    stderr = capsys.readouterr().err
    assert "[analysis-job-persistence] phase=progress" in stderr
    assert "progress persistence failed" in stderr


def test_analysis_job_execution__primary_failure_survives_failed_persistence(
    tmp_path, monkeypatch, capsys
):
    job = _create_job(
        tmp_path,
        104,
        status="queued",
        operation="layer",
        started_at=None,
        completed_at=None,
        live_publish_status="not_applicable",
        live_publish_revision=None,
    )
    job_id = job["job_id"]
    writes = []

    async def failing_worker(*args, **kwargs):
        raise ValueError("primary boom")

    def flaky_write(root, payload):
        writes.append(dict(payload))
        if payload.get("status") == "failed":
            raise OSError("secondary persistence boom")

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", failing_worker)
    monkeypatch.setattr(analysis_jobs, "_write_analysis_job", flaky_write)
    monkeypatch.setitem(analysis_jobs._analysis_tasks, job_id, object())
    monkeypatch.setitem(
        analysis_jobs._analysis_jobs_by_repo,
        str(tmp_path),
        job_id,
    )

    asyncio.run(
        analysis_jobs._execute_analysis_job(
            tmp_path,
            job,
            None,
            None,
        )
    )

    failed_payloads = [
        item for item in writes if item.get("status") == "failed"
    ]
    assert len(failed_payloads) == 1
    assert failed_payloads[0]["error"] == "ValueError: primary boom"
    assert job_id not in analysis_jobs._analysis_tasks
    assert str(tmp_path) not in analysis_jobs._analysis_jobs_by_repo

    stderr = capsys.readouterr().err
    assert "[analysis-job-persistence] phase=failed" in stderr
    assert "secondary persistence boom" in stderr


def test_analysis_status_concurrency__same_process_dead_worker_is_interrupted(
    tmp_path, monkeypatch
):
    job = _create_job(
        tmp_path,
        105,
        status="running",
        owner_pid=os.getpid(),
    )
    monkeypatch.delitem(
        analysis_jobs._analysis_tasks,
        job["job_id"],
        raising=False,
    )

    res = json.loads(
        get_analysis_status(str(tmp_path), job_id=job["job_id"])
    )

    assert res["status"] == "interrupted"
    assert res["error"] == "worker_not_active"

    persisted = analysis_jobs._read_analysis_job(
        tmp_path,
        job["job_id"],
    )
    assert persisted["status"] == "interrupted"
    assert persisted["error"] == "worker_not_active"


def test_analysis_status_concurrency__reconciliation_write_failure_returns_interrupted(
    tmp_path, monkeypatch
):
    job = _create_job(
        tmp_path,
        106,
        status="running",
        owner_pid=os.getpid(),
    )
    monkeypatch.delitem(
        analysis_jobs._analysis_tasks,
        job["job_id"],
        raising=False,
    )

    def fail_write(*args, **kwargs):
        raise OSError("cannot persist reconciliation")

    monkeypatch.setattr(
        analysis_jobs,
        "_write_analysis_job",
        fail_write,
    )

    res = json.loads(
        get_analysis_status(str(tmp_path), job_id=job["job_id"])
    )

    assert res["status"] == "interrupted"
    assert res["error"] == "worker_not_active"
    assert "Durable reconciliation persistence failed" in res["message"]
    assert "cannot persist reconciliation" in res["message"]


def test_active_analysis_jobs__excludes_dead_same_process_worker(
    tmp_path, monkeypatch
):
    current = _create_job(
        tmp_path,
        107,
        status="running",
        owner_pid=os.getpid(),
        mtime_ns=2_000_000_000,
    )
    foreign = _create_job(
        tmp_path,
        108,
        status="running",
        owner_pid=os.getpid() + 100000,
        mtime_ns=1_000_000_000,
    )
    monkeypatch.delitem(
        analysis_jobs._analysis_tasks,
        current["job_id"],
        raising=False,
    )

    active = analysis_jobs._active_analysis_jobs(tmp_path)

    assert [job["job_id"] for job in active] == [foreign["job_id"]]
