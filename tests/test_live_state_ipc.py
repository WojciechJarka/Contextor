"""Real-socket integration tests for the canonical LIVE IPC boundary."""

import threading
import time
from types import SimpleNamespace

import pytest

from contextor.core.live_state import CanonicalLiveServer, DesktopLiveWatcher, LiveStateClient
from contextor.core.live_state.ipc import LIVE_PROTOCOL_VERSION
from contextor.core.live_state.runtime import connect_or_start, endpoint_file

pytestmark = pytest.mark.live


@pytest.fixture
def live_server():
    server = CanonicalLiveServer({"files": []})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, LiveStateClient(server.endpoint)
    server.close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def test_two_clients_observe_one_in_ram_state_and_revision(live_server):
    server, first = live_server
    second = LiveStateClient(server.endpoint)

    assert first.ping() == {
        "status": "ok", "protocol_version": LIVE_PROTOCOL_VERSION,
        "revision": 0, "available": True,
    }
    assert first.publish({"files": ["a.py"]})["revision"] == 1
    assert second.snapshot() == {
        "status": "ok",
        "revision": 1,
        "state": {"files": ["a.py"]},
    }


def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
    def update(state, file_path):
        state["files"].append(file_path)
        return {"updated": file_path}

    server = CanonicalLiveServer({"files": []}, updater=update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        writer = LiveStateClient(server.endpoint)
        reader = LiveStateClient(server.endpoint)
        response = writer.update_file("new.py")

        assert response["status"] == "ok"
        assert response["revision"] == 1
        assert reader.snapshot()["state"] == {"files": ["new.py"]}
    finally:
        server.close()
        thread.join(timeout=2)


def test_live_events_preserve_desktop_origin_and_syntax_diagnostic(live_server):
    server, client = live_server

    result = SimpleNamespace(
        status="SYNTAX_ERROR",
        file_path="broken.py",
        error="invalid syntax",
        line_number=2,
        column_number=9,
    )
    server._updater = lambda _state, _path: result
    response = client.update_file("broken.py", origin="desktop_watcher")
    events = client.get_events(after_revision=0, limit=20)

    assert response["revision"] == 1
    assert events["total"] == 1
    assert events["truncated"] is False
    assert events["events"] == [{
        "revision": 1,
        "operation": "update_file",
        "origin": "desktop_watcher",
        "status": "SYNTAX_ERROR",
        "file_path": "broken.py",
        "error": "invalid syntax",
        "line_number": 2,
        "column_number": 9,
    }]


def test_invalid_and_unavailable_operations_return_structured_errors():
    server = CanonicalLiveServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = LiveStateClient(server.endpoint)
        assert client.request("unknown")["error"] == "unknown_operation"
        assert client.update_file("x.py")["error"] == "live_state_unavailable"
    finally:
        server.close()
        thread.join(timeout=2)


def test_updater_failure_does_not_kill_the_service():
    def broken_update(_state, _file_path):
        raise ValueError("broken update")

    server = CanonicalLiveServer({}, updater=broken_update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = LiveStateClient(server.endpoint)
        assert "broken update" in client.update_file("x.py")["error"]
        assert client.ping()["status"] == "ok"
        assert thread.is_alive()
    finally:
        server.close()
        thread.join(timeout=2)


def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tmp_path):
    updates = []

    def update(state, file_path):
        updates.append(file_path)
        state["updates"] += 1

    server = CanonicalLiveServer({"updates": 0}, updater=update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    watcher = DesktopLiveWatcher(tmp_path, LiveStateClient(server.endpoint))
    target = tmp_path / "sample.py"
    try:
        target.write_text("value = 1\n", encoding="utf-8")
        assert watcher.poll_once() == [str(target)]

        target.write_text("value = 22\n", encoding="utf-8")
        assert watcher.poll_once() == [str(target)]

        target.unlink()
        assert watcher.poll_once() == [str(target)]
        snapshot = LiveStateClient(server.endpoint).snapshot()
        assert snapshot["revision"] == 3
        assert snapshot["state"] == {"updates": 3}
        assert updates == [str(target)] * 3
    finally:
        server.close()
        thread.join(timeout=2)


def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
    server = CanonicalLiveServer(updater=lambda state, path: state.update(last_path=path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    watcher = DesktopLiveWatcher(tmp_path, client)
    try:
        (tmp_path / "before_analysis.py").write_text("value = 1\n", encoding="utf-8")
        assert watcher.poll_once() == []
        assert client.ping() == {
            "status": "ok", "protocol_version": LIVE_PROTOCOL_VERSION,
            "revision": 0, "available": False,
        }

        client.publish({"ready": True})
        (tmp_path / "after_analysis.py").write_text("value = 2\n", encoding="utf-8")
        response = watcher.poll_once()
        assert response == [str(tmp_path / "after_analysis.py")]
    finally:
        server.close()
        thread.join(timeout=2)


def test_real_service_process_starts_connects_and_stops(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    client = connect_or_start(repo)
    endpoint = endpoint_file(repo)
    try:
        assert client.ping()["status"] == "ok"
        assert endpoint.is_file()
    finally:
        client.request("shutdown")
        deadline = time.monotonic() + 5
        while endpoint.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not endpoint.exists()
