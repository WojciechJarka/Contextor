import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
from contextor.core.live_state.ipc import CanonicalMutationCoordinator
from contextor.core.live_state.store import SnapshotRevisionConflict


pytestmark = pytest.mark.live


def _diagnostic_state():
    return SimpleNamespace(
        revision=0,
        syntax_diagnostics_state="fresh",
        syntax_diagnostics_by_path={},
        collisions_state="fresh",
        collisions=[],
        cycles_state="fresh",
        cycles=[],
    )


@contextmanager
def _running_server(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield LiveStateClient(server.endpoint)
    finally:
        server.close()
        thread.join(timeout=3)
        assert not thread.is_alive()


def _wait_for_terminal(client, job_id, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.mutation_status(job_id)
        if status.get("state") in {"completed", "failed", "cancelled"}:
            return status
        time.sleep(0.01)
    raise AssertionError(f"mutation job did not become terminal: {job_id}")


def test_submit_ack_is_immediate_and_does_not_publish_revision():
    started = threading.Event()
    release = threading.Event()

    def updater(state, path):
        started.set()
        assert release.wait(timeout=3)
        state.files.append(path)
        return {"status": "UPDATED", "file_path": path}

    server = CanonicalLiveServer(SimpleNamespace(files=[], revision=0), updater=updater)
    with _running_server(server) as client:
        assert server._mutation_coordinator._thread is None
        started_at = time.monotonic()
        accepted = client.submit_update_file("blocked.py", origin="test")
        elapsed = time.monotonic() - started_at

        assert elapsed < 0.5
        assert accepted["status"] == "accepted"
        assert accepted["accepted"] is True
        assert accepted["state"] == "queued"
        assert accepted["accepted_revision"] == 0
        assert accepted["job_id"].startswith("mu-")
        assert started.wait(timeout=1)
        assert server._revision == 0
        assert server._activity_seq == 0
        assert client.get_events(after_revision=0)["total"] == 0

        release.set()
        terminal = _wait_for_terminal(client, accepted["job_id"])
        assert terminal["state"] == "completed"
        assert terminal["final_revision"] == 1


def test_read_only_ipc_remains_responsive_while_queued_mutation_runs():
    started = threading.Event()
    release = threading.Event()
    authority = {
        "repo_id": "repo-id",
        "root_path": "C:/repo",
        "runtime_domain_id": "domain-id",
        "service_instance_id": "service-id",
        "lease_generation": 3,
        "service_pid": 123,
        "process_start_identity": "start-id",
    }

    def updater(state, path):
        started.set()
        assert release.wait(timeout=3)
        state.files.append(path)
        return {"status": "UPDATED", "file_path": path}

    server = CanonicalLiveServer(
        SimpleNamespace(files=[], revision=0),
        updater=updater,
        authority_identity=authority,
    )
    with _running_server(server) as client:
        accepted = client.submit_update_file("slow.py", origin="test")
        assert started.wait(timeout=1)
        reader = LiveStateClient(server.endpoint)

        calls = [
            ("ping", reader.ping),
            ("snapshot", reader.snapshot),
            ("authority_status", reader.authority_status),
            ("get_events", lambda: reader.get_events(after_revision=0)),
        ]
        for name, call in calls:
            started_at = time.monotonic()
            response = call()
            elapsed = time.monotonic() - started_at
            assert elapsed < 1.0, name
            assert response["status"] == "ok"
            if name == "snapshot":
                assert response["revision"] == 0
                assert response["state"].files == []
            if name == "get_events":
                assert response["revision"] == 0
                assert response["events"] == []

        release.set()
        terminal = _wait_for_terminal(reader, accepted["job_id"])
        assert terminal["state"] == "completed"
        assert terminal["final_revision"] == 1
        assert reader.snapshot()["state"].files == ["slow.py"]
        assert reader.get_events(after_revision=0)["total"] == 1


def test_queued_mutations_are_fifo_and_strictly_serial():
    first_started = threading.Event()
    release_first = threading.Event()
    active = 0
    max_active = 0
    active_lock = threading.Lock()
    start_order = []

    def updater(state, path):
        nonlocal active, max_active
        with active_lock:
            active += 1
            max_active = max(max_active, active)
            start_order.append(path)
        try:
            if path == "a.py":
                first_started.set()
                assert release_first.wait(timeout=3)
            state.files.append(path)
            return {"status": "UPDATED", "file_path": path}
        finally:
            with active_lock:
                active -= 1

    server = CanonicalLiveServer(SimpleNamespace(files=[], revision=0), updater=updater)
    with _running_server(server) as client:
        first = client.submit_update_file("a.py", origin="test")
        assert first_started.wait(timeout=1)
        second = client.submit_update_file("b.py", origin="test")
        release_first.set()

        first_status = _wait_for_terminal(client, first["job_id"])
        second_status = _wait_for_terminal(client, second["job_id"])
        assert first_status["state"] == "completed"
        assert second_status["state"] == "completed"
        assert start_order == ["a.py", "b.py"]
        assert max_active == 1
        assert first_status["final_revision"] == 1
        assert second_status["final_revision"] == 2
        assert client.snapshot()["state"].files == ["a.py", "b.py"]


def test_candidate_is_invisible_during_slow_persistence():
    persist_started = threading.Event()
    release_persist = threading.Event()

    def updater(state, path):
        state.files.append(path)
        return {"status": "UPDATED", "file_path": path}

    def persister(state, revision):
        assert state.files == ["persist.py"]
        assert revision == 1
        persist_started.set()
        assert release_persist.wait(timeout=3)

    server = CanonicalLiveServer(
        SimpleNamespace(files=[], revision=0),
        updater=updater,
        persister=persister,
    )
    with _running_server(server) as client:
        accepted = client.submit_update_file("persist.py", origin="test")
        assert persist_started.wait(timeout=1)
        snapshot = LiveStateClient(server.endpoint).snapshot()
        assert snapshot["revision"] == 0
        assert snapshot["state"].files == []
        assert server._activity_seq == 0

        release_persist.set()
        terminal = _wait_for_terminal(client, accepted["job_id"])
        assert terminal["state"] == "completed"
        snapshot = client.snapshot()
        assert snapshot["revision"] == 1
        assert snapshot["state"].files == ["persist.py"]


def test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnostics_unchanged(monkeypatch):
    import contextor.core.runtime_trace as runtime_trace

    trace_events = []
    monkeypatch.setattr(
        runtime_trace,
        "trace_event",
        lambda *args, **kwargs: trace_events.append((args, kwargs)),
    )

    initial = _diagnostic_state()

    def updater(state, _path):
        state.syntax_diagnostics_by_path = {
            "bad.py": {
                "status": "checked_with_errors",
                "errors": [{"message": "bad", "line_number": 1, "column_number": 0}],
            }
        }
        return {"status": "UPDATED", "file_path": "bad.py"}

    def persister(_state, revision):
        raise SnapshotRevisionConflict(9, revision)

    server = CanonicalLiveServer(initial, updater=updater, persister=persister)
    with _running_server(server) as client:
        accepted = client.submit_update_file("bad.py", origin="test")
        terminal = _wait_for_terminal(client, accepted["job_id"])
        assert terminal["state"] == "failed"
        assert terminal["response"]["error"] == "canonical_persistence_revision_conflict"
        assert server._state is initial
        assert server._revision == 0
        assert server._activity_seq == 0
        assert client.get_events(after_revision=0)["events"] == []
        assert not any(
            args[1].startswith("LIVE_DIAGNOSTIC_") for args, _kwargs in trace_events
        )


def test_worker_survives_failed_job_and_executes_next_job():
    first_started = threading.Event()

    def updater(state, path):
        if path == "bad.py":
            first_started.set()
            raise RuntimeError("first failed")
        state.files.append(path)
        return {"status": "UPDATED", "file_path": path}

    server = CanonicalLiveServer(SimpleNamespace(files=[], revision=0), updater=updater)
    with _running_server(server) as client:
        first = client.submit_update_file("bad.py", origin="test")
        assert first_started.wait(timeout=1)
        second = client.submit_update_file("good.py", origin="test")
        first_status = _wait_for_terminal(client, first["job_id"])
        second_status = _wait_for_terminal(client, second["job_id"])

        assert first_status["state"] == "failed"
        assert first_status["response"]["error"] == "canonical_mutation_execution_failed"
        assert "first failed" in first_status["error"]
        assert second_status["state"] == "completed"
        assert second_status["final_revision"] == 1
        assert client.snapshot()["state"].files == ["good.py"]


def test_publish_and_queued_update_are_single_writer_serialized():
    update_started = threading.Event()
    release_update = threading.Event()
    publish_done = threading.Event()
    publish_response = []

    def updater(state, path):
        update_started.set()
        assert release_update.wait(timeout=3)
        state.value = 1
        state.files.append(path)
        return {"status": "UPDATED", "file_path": path}

    server = CanonicalLiveServer(
        SimpleNamespace(value=0, files=[], revision=0), updater=updater
    )
    try:
        accepted = server._mutation_coordinator.submit({"file_path": "update.py"})
        assert update_started.wait(timeout=1)

        def publish():
            publish_response.append(
                server._execute_publish(
                    {"operation": "publish", "state": SimpleNamespace(value=2, files=[])}
                )
            )
            publish_done.set()

        publish_thread = threading.Thread(target=publish)
        publish_thread.start()
        assert not publish_done.wait(timeout=0.1)

        release_update.set()
        deadline = time.monotonic() + 2
        update_status = server._mutation_coordinator.status(accepted["job_id"])
        while (
            update_status.get("state") not in {"completed", "failed", "cancelled"}
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
            update_status = server._mutation_coordinator.status(accepted["job_id"])
        publish_thread.join(timeout=2)
        assert not publish_thread.is_alive()
        assert update_status["state"] == "completed"
        assert update_status["final_revision"] == 1
        assert publish_response == [{"status": "ok", "revision": 2, "seq": 2}]
        assert server._revision == 2
        assert server._state.value == 2
    finally:
        server.close()


def test_coordinator_close_cancels_queued_not_active_job():
    first_started = threading.Event()
    release_first = threading.Event()

    def executor(request):
        if request["file_path"] == "first.py":
            first_started.set()
            assert release_first.wait(timeout=3)
        return {"status": "ok", "revision": 1}

    coordinator = CanonicalMutationCoordinator(lambda request: executor(request), lambda: 0)
    first = coordinator.submit({"file_path": "first.py"})
    assert first_started.wait(timeout=1)
    second = coordinator.submit({"file_path": "second.py"})

    coordinator.close(join_timeout=0.05)
    cancelled = coordinator.status(second["job_id"])
    assert cancelled["state"] == "cancelled"
    assert cancelled["error"] == "canonical_mutation_queue_closed"
    assert cancelled["response"] == {
        "status": "error",
        "error": "canonical_mutation_queue_closed",
        "job_id": second["job_id"],
    }
    assert coordinator.submit({"file_path": "third.py"}) == {
        "status": "error",
        "error": "canonical_mutation_queue_closed",
    }

    release_first.set()
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if coordinator.status(first["job_id"]).get("state") == "completed":
            break
        time.sleep(0.01)
    assert coordinator.status(first["job_id"])["state"] == "completed"
    coordinator.close(join_timeout=0.1)


def test_unknown_and_invalid_mutation_job_status_fail_closed():
    coordinator = CanonicalMutationCoordinator(lambda _request: {"status": "ok"}, lambda: 0)
    try:
        assert coordinator.status(None) == {
            "status": "error",
            "error": "invalid_mutation_job_id",
        }
        assert coordinator.status("") == {
            "status": "error",
            "error": "invalid_mutation_job_id",
        }
        assert coordinator.status("mu-missing") == {
            "status": "error",
            "error": "unknown_mutation_job",
            "job_id": "mu-missing",
        }
        assert coordinator.submit({"file_path": ""}) == {
            "status": "error",
            "error": "invalid_file_path",
        }
    finally:
        coordinator.close()


def test_legacy_update_file_contract_remains_synchronous_and_unchanged():
    started = threading.Event()
    release = threading.Event()

    def updater(state, path):
        started.set()
        assert release.wait(timeout=3)
        state.files.append(path)
        return {"status": "UPDATED", "file_path": path}

    server = CanonicalLiveServer(SimpleNamespace(files=[], revision=0), updater=updater)
    with _running_server(server) as client:
        response_box = []
        call_thread = threading.Thread(
            target=lambda: response_box.append(client.update_file("legacy.py"))
        )
        call_thread.start()
        assert started.wait(timeout=1)
        assert not response_box
        assert server._revision == 0
        release.set()
        call_thread.join(timeout=2)
        assert not call_thread.is_alive()
        assert response_box == [{
            "status": "ok",
            "activity_epoch": response_box[0]["activity_epoch"],
            "revision": 1,
            "result": {"status": "UPDATED", "file_path": "legacy.py"},
            "seq": 1,
        }]
