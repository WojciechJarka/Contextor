import os
import subprocess
import sys
import threading
import time
import multiprocessing.connection as mpc
from types import SimpleNamespace

import pytest

from contextor.core.live_state import (
    CanonicalLiveServer,
    DesktopLiveEventFeed,
    DesktopLiveWatcher,
    LiveStateClient,
)
from contextor.core.live_state.ipc import LIVE_PROTOCOL_VERSION
from contextor.core.live_state import ipc as ipc_module
from contextor.core.live_state.runtime import connect_or_start, endpoint_file
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

pytestmark = pytest.mark.live


def test_client_request_timeout_closes_connection(monkeypatch):
    sent = []

    class Connection:
        closed = False

        def send(self, payload):
            sent.append(payload)

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(ipc_module, "Client", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(mpc, "wait", lambda _connections, timeout: [])
    client = LiveStateClient(SimpleNamespace(address=("127.0.0.1", 1), authkey=b"x"))

    with pytest.raises(TimeoutError, match="0.01s.*op=ping"):
        client.request("ping", timeout=0.01)

    assert sent == [{"operation": "ping"}]
    assert connection.closed is True


@pytest.fixture
def live_server():
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
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
    assert first.publish(SimpleNamespace(files=["a.py"]))["revision"] == 1
    snap = second.snapshot()
    assert snap["status"] == "ok"
    assert snap["revision"] == 1
    assert snap["state"].files == ["a.py"]
    assert snap["state"].revision == 1


def test_update_runs_inside_the_live_owner_and_is_visible_to_other_clients():
    def update(state, file_path):
        state.files.append(file_path)
        return {"updated": file_path}

    server = CanonicalLiveServer(SimpleNamespace(files=[]), updater=update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        writer = LiveStateClient(server.endpoint)
        reader = LiveStateClient(server.endpoint)
        response = writer.update_file("new.py")

        assert response["status"] == "ok"
        assert response["revision"] == 1
        assert reader.snapshot()["state"].files == ["new.py"]
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


def test_live_events_record_blast_radius_state_and_bounded_affected_modules(live_server):
    server, client = live_server

    modules = [f"mod_{i}" for i in range(25)]
    result = SimpleNamespace(
        status="UPDATED",
        file_path="provider.py",
        blast_radius_state="fresh",
        affected_modules=modules,
    )
    server._updater = lambda _state, _path: result
    response = client.update_file("provider.py", origin="desktop_watcher")
    events = client.get_events(after_revision=0, limit=20)

    assert response["revision"] == 1
    assert events["total"] == 1
    assert events["events"][0]["blast_radius_state"] == "fresh"
    assert events["events"][0]["affected_modules"] == {
        "total": 25,
        "truncated": True,
        "items": modules[:20],
    }



def test_desktop_event_feed_forwards_only_mcp_status_messages(live_server):
    _server, client = live_server
    statuses = []
    feed = DesktopLiveEventFeed(client, statuses.append)

    client.status("MCP: reading symbol demo", origin="mcp")
    client.status("desktop-only", origin="desktop_watcher")
    client.publish({"ready": True}, origin="mcp_analysis")
    feed.poll_once()

    assert statuses == [
        "MCP: reading symbol demo",
        "MCP: analysis published shared LIVE state (rev 1)",
    ]


def test_desktop_event_feed_background_worker_starts_and_stops(live_server):
    _server, client = live_server
    delivered = threading.Event()
    statuses = []

    def receive(message):
        statuses.append(message)
        delivered.set()

    feed = DesktopLiveEventFeed(client, receive, interval=0.01)
    try:
        feed.start()
        client.status("MCP: background status", origin="mcp")
        assert delivered.wait(timeout=1)
        assert statuses == ["MCP: background status"]
    finally:
        feed.stop()
    assert feed._thread is not None
    assert not feed._thread.is_alive()


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

    server = CanonicalLiveServer(SimpleNamespace(), updater=broken_update)
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
    statuses = []

    def update(state, file_path):
        updates.append(file_path)
        state.updates += 1

    server = CanonicalLiveServer(SimpleNamespace(updates=0), updater=update)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    watcher = DesktopLiveWatcher(
        tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
    )
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
        assert snapshot["state"].updates == 3
        assert updates == [str(target)] * 3
        assert statuses == [
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
            "Updating LIVE: sample.py", "LIVE update successful: sample.py",
        ]
    finally:
        server.close()
        thread.join(timeout=2)


def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
    server = CanonicalLiveServer(updater=lambda state, path: setattr(state, "last_path", path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    statuses = []
    watcher = DesktopLiveWatcher(tmp_path, client, on_status=statuses.append)
    try:
        (tmp_path / "before_analysis.py").write_text("value = 1\n", encoding="utf-8")
        assert watcher.poll_once() == []
        assert client.ping() == {
            "status": "ok", "protocol_version": LIVE_PROTOCOL_VERSION,
            "revision": 0, "available": False,
        }
        assert statuses == ["LIVE: no snapshot; waiting for analysis"]

        client.publish(SimpleNamespace(ready=True))
        (tmp_path / "after_analysis.py").write_text("value = 2\n", encoding="utf-8")
        response = watcher.poll_once()
        assert response == [str(tmp_path / "after_analysis.py")]
    finally:
        server.close()
        thread.join(timeout=2)


def test_desktop_watcher_reports_syntax_location(tmp_path):
    statuses = []
    result = SimpleNamespace(
        status="SYNTAX_ERROR",
        file_path=str(tmp_path / "broken.py"),
        error="invalid syntax",
        line_number=2,
        column_number=7,
    )
    server = CanonicalLiveServer(SimpleNamespace(ready=True), updater=lambda *_args: result)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    watcher = DesktopLiveWatcher(
        tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
    )
    try:
        target = tmp_path / "broken.py"
        target.write_text("def broken(:\n", encoding="utf-8")
        assert watcher.poll_once() == [str(target)]
        assert statuses == [
            "Updating LIVE: broken.py",
            "LIVE syntax error: broken.py line 2, column 7: invalid syntax",
        ]
    finally:
        server.close()
        thread.join(timeout=2)


def test_real_service_process_starts_connects_and_stops(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
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


def test_connect_or_start_ownership_when_spawning_new(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    import os
    my_pid = os.getpid()
    client = connect_or_start(repo, owner_pid=my_pid, owner_token="new-owner-token")
    try:
        assert client.is_owner is True
        assert client.owner_token == "new-owner-token"
        assert client.owner_pid == my_pid
        assert client.service_pid is not None
        assert client.service_pid > 0
    finally:
        client.request("shutdown")


def test_owner_pid_match_without_owner_token_is_not_owner(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    # Calling connect_or_start without owner_token must NEVER grant is_owner=True
    client = connect_or_start(repo, owner_pid=os.getpid(), owner_token=None)
    try:
        assert client.is_owner is False
        assert client.owner_token is None
    finally:
        client.request("shutdown")


def test_responsive_token_only_endpoint_matching_and_differing_tokens(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    import json
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": 54321,
        "owner_token": "token-xyz",
        # Note: owner_pid is None
    }
    ep_file.write_text(json.dumps(payload), encoding="utf-8")

    try:
        # Caller with matching token -> is_owner is True
        matching_client = connect_or_start(repo, owner_token="token-xyz")
        assert matching_client.is_owner is True
        assert matching_client.owner_token == "token-xyz"

        # Caller with differing token -> is_owner is False
        different_client = connect_or_start(repo, owner_token="token-other")
        assert different_client.is_owner is False
        assert different_client.owner_token == "token-xyz"

        # Caller with no token -> is_owner is False
        no_token_client = connect_or_start(repo, owner_token=None)
        assert no_token_client.is_owner is False
        assert no_token_client.owner_token == "token-xyz"
    finally:
        server.close()
        thread.join(timeout=2)


def test_post_popen_token_match_with_different_pid_is_not_owner_and_cleans_proc(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    import json
    # Start a genuine server with PID 54321 and token "race-token"
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": 54321,
        "owner_token": "race-token",
    }
    ep_file.write_text(json.dumps(payload), encoding="utf-8")

    # Mock subprocess.Popen so it spawns a dummy real process that is alive
    import subprocess
    import sys
    from contextor.core.live_state.runtime import _is_pid_alive
    dummy_proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    dummy_pid = dummy_proc.pid

    spawned = [False]

    def mock_popen(*args, **kwargs):
        spawned[0] = True
        return dummy_proc

    # Monkeypatch subprocess.Popen in connect_or_start
    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    # Remove the endpoint file before calling connect_or_start to force the startup path
    ep_file.unlink()

    # Re-write the endpoint file right before connect connects in post-Popen
    from contextor.core.live_state.ipc import LiveEndpoint

    def mock_connect(r):
        if not spawned[0]:
            return None
        ep_file.write_text(json.dumps(payload), encoding="utf-8")
        return LiveStateClient(LiveEndpoint(server.endpoint.host, server.endpoint.port, server.endpoint.authkey_hex, pid=54321, owner_token="race-token"))

    # When connect_or_start runs, post-Popen sees ep.pid (54321) != proc.pid (dummy_pid)
    monkeypatch.setattr("contextor.core.live_state.runtime.connect", mock_connect)

    try:
        client = connect_or_start(repo, owner_token="race-token")
        # Invariant 1: ep.pid != proc.pid -> is_owner must be False
        assert client.is_owner is False
        assert client.service_pid == 54321

        # Invariant 1: losing spawned proc (dummy_pid) must be terminated
        time.sleep(0.2)
        assert _is_pid_alive(dummy_pid) is False
    finally:
        server.close()
        thread.join(timeout=2)
        try:
            dummy_proc.kill()
        except OSError:
            pass


def test_connect_or_start_ownership_when_reconnecting_existing(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    first_client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="first-token")
    try:
        # Second caller with a different owner_token connects to existing service
        second_client = connect_or_start(repo, owner_pid=99999999, owner_token="second-token")
        assert second_client.is_owner is False
        assert second_client.owner_token == "first-token"
        assert second_client.service_pid == first_client.service_pid
    finally:
        first_client.request("shutdown")


def test_connect_or_start_replaces_proven_orphan_with_dead_owner(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    # Spawn a service with owner_pid = 99999999 (which is dead)
    import subprocess
    import sys
    env = dict(os.environ)
    proc = subprocess.Popen(
        [sys.executable, "-m", "contextor.core.live_state.runtime", "--repo", str(repo), "--owner-pid", "99999999"],
        cwd=str(repo),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    from contextor.core.live_state.runtime import connect
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if connect(repo):
            break
        time.sleep(0.05)
    orphan_pid = proc.pid
    try:
        # connect_or_start detects owner 99999999 is dead -> stops orphan and spawns fresh owned runtime
        client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="orphan-replacer")
        assert client.is_owner is True
        assert client.owner_token == "orphan-replacer"
        assert client.owner_pid == os.getpid()
        assert client.service_pid != orphan_pid
    finally:
        client.request("shutdown")
        try:
            proc.kill()
        except OSError:
            pass


def test_connect_or_start_preserves_legacy_endpoint_without_owner_pid(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    import json
    server = CanonicalLiveServer(SimpleNamespace(files=[]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ep_file = endpoint_file(repo)
    ep_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_payload = {
        "host": server.endpoint.host,
        "port": server.endpoint.port,
        "authkey_hex": server.endpoint.authkey_hex,
        "pid": 54321,
        # Note: no owner_pid, no owner_token
    }
    ep_file.write_text(json.dumps(legacy_payload), encoding="utf-8")

    try:
        client = connect_or_start(repo, owner_pid=12345, owner_token="caller-token")
        # Should reuse legacy service without killing it, marked as unowned
        assert client.is_owner is False
        assert client.owner_pid is None
        assert client.owner_token is None
        assert client.service_pid == 54321
    finally:
        server.close()
        thread.join(timeout=2)


def test_terminate_pid_tree_kills_process_and_children(tmp_path):
    """Explicit process tree termination test proving _terminate_pid_tree behavior."""
    import subprocess
    import sys
    from contextor.core.live_state.runtime import _is_pid_alive, _terminate_pid_tree

    # Spawn a sleeping python process
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid = proc.pid
    try:
        assert _is_pid_alive(pid) is True
        _terminate_pid_tree(pid)
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if not _is_pid_alive(pid):
                break
            time.sleep(0.05)
        assert _is_pid_alive(pid) is False
    finally:
        try:
            proc.kill()
        except OSError:
            pass


def test_endpoint_cleanup_does_not_delete_newer_pid_endpoint(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    client = connect_or_start(repo)
    ep_file = endpoint_file(repo)
    assert ep_file.is_file()

    # Simulate a newer service replacing the endpoint file with a new PID
    import json
    payload = json.loads(ep_file.read_text(encoding="utf-8"))
    payload["pid"] = 99999998
    ep_file.write_text(json.dumps(payload), encoding="utf-8")

    try:
        # Request shutdown of original client - its finally block must NOT unlink the newer endpoint!
        client.request("shutdown")
        time.sleep(0.3)
        assert ep_file.is_file()
    finally:
        try:
            ep_file.unlink()
        except OSError:
            pass


def test_owner_token_identity_grants_ownership_only_to_token_holder(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    token_a = "token-alpha-12345"
    token_b = "token-beta-67890"

    client_a = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_a)
    try:
        assert client_a.is_owner is True
        assert client_a.owner_token == token_a
        assert client_a.owner_pid == os.getpid()

        # Caller B connects with different token -> is_owner must be False
        client_b = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_b)
        assert client_b.is_owner is False
        assert client_b.owner_token == token_a
        assert client_b.service_pid == client_a.service_pid

        # Caller A reconnects with same token A -> is_owner must be True
        client_a_reconnected = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_a)
        assert client_a_reconnected.is_owner is True
        assert client_a_reconnected.owner_token == token_a
        assert client_a_reconnected.service_pid == client_a.service_pid
    finally:
        client_a.request("shutdown")


def test_owner_pid_reuse_or_mismatched_token_does_not_grant_ownership(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    token_original = "token-original-owner"
    token_recycled = "token-recycled-owner"

    client = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_original)
    try:
        # Simulate another process that coincidentally shares the same PID (or PID reuse)
        # but has a different owner_token
        recycled_client = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token_recycled)
        assert recycled_client.is_owner is False
        assert recycled_client.owner_token == token_original
    finally:
        client.request("shutdown")


def test_concurrent_connect_or_start_creates_single_service(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    results = []
    barrier = threading.Barrier(3)

    def worker(idx):
        barrier.wait()
        token = f"worker-token-{idx}"
        client = connect_or_start(repo, owner_pid=os.getpid(), owner_token=token)
        results.append((token, client))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15.0)

    assert len(results) == 3
    # Exactly one client should be the owner, and all 3 must share the same service_pid
    service_pids = {client.service_pid for _, client in results}
    assert len(service_pids) == 1
    owners = [token for token, client in results if client.is_owner]
    assert len(owners) == 1

    # Cleanup the service using the owner client
    owner_client = [c for _, c in results if c.is_owner][0]
    owner_client.request("shutdown")


def test_watchdog_terminates_runtime_when_owner_process_dies(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    from contextor.core.live_state.runtime import _is_pid_alive, connect

    # Spawn a short-lived parent process that starts the live runtime with its own PID
    script = (
        "import sys, os, time, subprocess; "
        f"repo = {repr(str(repo))}; "
        f"cache = {repr(str(cache))}; "
        "os.environ['CONTEXTOR_CACHE_DIR'] = cache; "
        "cmd = [sys.executable, '-m', 'contextor.core.live_state.runtime', '--repo', repo, '--owner-pid', str(os.getpid())]; "
        "proc = subprocess.Popen(cmd, cwd=repo, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
        "time.sleep(1.0); "
        "sys.exit(0)"
    )
    parent = subprocess.Popen([sys.executable, "-c", script])
    parent.wait(timeout=5)
    assert not _is_pid_alive(parent.pid)

    # Watchdog inside runtime.py should detect owner parent is dead and terminate itself within bounded time
    deadline = time.monotonic() + 5.0
    terminated = False
    while time.monotonic() < deadline:
        if connect(repo) is None:
            terminated = True
            break
        time.sleep(0.1)

    assert terminated is True


def test_watchdog_keeps_runtime_alive_while_owner_lives(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    # Spawn with our own current PID which stays alive
    client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="test-alive")
    try:
        time.sleep(1.5)  # Longer than the 0.75s watchdog interval
        status = client.ping()
        assert status.get("status") == "ok"
    finally:
        client.request("shutdown")


def test_get_events_continuity_gap_detection_and_retention_contract():
    server = CanonicalLiveServer(state=None, revision=0, retention=100)

    # Case 1: Initial empty buffer
    r_empty_none = server._dispatch({"operation": "get_events", "after_revision": None})
    assert r_empty_none["status"] == "ok"
    assert r_empty_none["latest_revision"] == 0
    assert r_empty_none["earliest_retained_revision"] is None
    assert r_empty_none["continuity"] == "not_requested"
    assert r_empty_none["resync_required"] is False
    assert r_empty_none["resync_reason"] is None
    assert r_empty_none["events"] == []
    assert r_empty_none["total"] == 0
    assert r_empty_none["truncated"] is False

    # Empty buffer with after_revision == 0 (latest)
    r_empty_zero = server._dispatch({"operation": "get_events", "after_revision": 0})
    assert r_empty_zero["continuity"] == "continuous"
    assert r_empty_zero["resync_required"] is False
    assert r_empty_zero["resync_reason"] is None

    # Empty buffer with after_revision < latest_revision (simulating buffer cleared with latest=150)
    server_cleared = CanonicalLiveServer(state=None, revision=150)
    r_cleared_gap = server_cleared._dispatch({"operation": "get_events", "after_revision": 120})
    assert r_cleared_gap["latest_revision"] == 150
    assert r_cleared_gap["earliest_retained_revision"] is None
    assert r_cleared_gap["continuity"] == "gap"
    assert r_cleared_gap["resync_required"] is True
    assert r_cleared_gap["resync_reason"] == "event_retention_gap"

    # Populate 150 events to test retention cap (100) and eviction of 1..50
    for i in range(1, 151):
        server._revision += 1
        server._record_event(
            "update_file",
            {"origin": "desktop_watcher", "file_path": f"src/mod_{i}.py"},
            type(
                "Result",
                (),
                {
                    "status": "UPDATED",
                    "file_path": f"src/mod_{i}.py",
                    "affected_modules": [f"pkg.consumer_{j}" for j in range(30)],
                },
            )(),
        )

    assert len(server._events) == 100
    assert server._revision == 150
    assert server._events[0]["revision"] == 51
    assert server._events[-1]["revision"] == 150

    # 1. after_revision=None -> continuity="not_requested", resync_required=False
    r_none = server._dispatch({"operation": "get_events", "after_revision": None, "limit": 20})
    assert r_none["latest_revision"] == 150
    assert r_none["earliest_retained_revision"] == 51
    assert r_none["continuity"] == "not_requested"
    assert r_none["resync_required"] is False
    assert r_none["resync_reason"] is None
    assert len(r_none["events"]) == 20
    assert r_none["total"] == 100
    assert r_none["truncated"] is True

    # 2. after_revision=50 (earliest - 1) -> continuity="continuous", resync_required=False
    r_cont = server._dispatch({"operation": "get_events", "after_revision": 50, "limit": 20})
    assert r_cont["continuity"] == "continuous"
    assert r_cont["resync_required"] is False
    assert r_cont["resync_reason"] is None
    assert r_cont["events"][0]["revision"] == 51

    # 3. after_revision=20 (gap: events 21..50 evicted) -> continuity="gap", resync_required=True
    r_gap = server._dispatch({"operation": "get_events", "after_revision": 20, "limit": 20})
    assert r_gap["continuity"] == "gap"
    assert r_gap["resync_required"] is True
    assert r_gap["resync_reason"] == "event_retention_gap"
    assert r_gap["earliest_retained_revision"] == 51

    # 4. Same gap with limit=1 -> gap is still detected against buffer, not first slice
    r_gap_l1 = server._dispatch({"operation": "get_events", "after_revision": 20, "limit": 1})
    assert r_gap_l1["continuity"] == "gap"
    assert r_gap_l1["resync_required"] is True
    assert r_gap_l1["resync_reason"] == "event_retention_gap"
    assert len(r_gap_l1["events"]) == 1
    assert r_gap_l1["total"] == 100
    assert r_gap_l1["truncated"] is True

    # 5. after_revision=150 (latest) -> continuous, empty events
    r_uptodate = server._dispatch({"operation": "get_events", "after_revision": 150})
    assert r_uptodate["continuity"] == "continuous"
    assert r_uptodate["resync_required"] is False
    assert r_uptodate["resync_reason"] is None
    assert r_uptodate["events"] == []
    assert r_uptodate["total"] == 0
    assert r_uptodate["truncated"] is False

    # 8. after_revision > latest_revision (e.g. 155 > 150) -> gap + revision_discontinuity
    r_regr = server._dispatch({"operation": "get_events", "after_revision": 155})
    assert r_regr["continuity"] == "gap"
    assert r_regr["resync_required"] is True
    assert r_regr["resync_reason"] == "revision_discontinuity"

    # 10. limit=None -> returns all 100 retained events (max 100)
    r_all = server._dispatch({"operation": "get_events", "after_revision": None, "limit": None})
    assert len(r_all["events"]) == 100
    assert r_all["total"] == 100
    assert r_all["truncated"] is False

    # 11. affected_modules completeness disclosure preserved
    first_event = r_none["events"][0]
    assert first_event["affected_modules"]["total"] == 30
    assert first_event["affected_modules"]["truncated"] is True
    assert len(first_event["affected_modules"]["items"]) == 20

    # 12. Invalid non-integer or bool after_revision values return controlled error without exception
    for invalid_val in ["1", 1.5, True, False, [1], {"rev": 1}]:
        err_res = server._dispatch({"operation": "get_events", "after_revision": invalid_val})
        assert err_res == {"status": "error", "error": "invalid_after_revision"}

    # 13. Negative after_revision is a valid integer cursor (evaluated against retained window)
    r_neg = server._dispatch({"operation": "get_events", "after_revision": -1})
    assert r_neg["status"] == "ok"
    assert r_neg["continuity"] == "gap"
    assert r_neg["resync_required"] is True
    assert r_neg["resync_reason"] == "event_retention_gap"
    assert len(r_neg["events"]) == 20


def test_connect_or_start_slow_healthy_startup(tmp_path, monkeypatch):
    """Regression: Slow healthy startup where endpoint appears after normal connection timeout
    but within cold-start initialization budget.
    EXPECT:
    - Child process is NOT terminated prematurely.
    - connect_or_start succeeds.
    """
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    # Helper script that sleeps 0.25s before writing endpoint and serving
    helper = tmp_path / "delayed_server.py"
    helper.write_text(
        "import sys, time, json, os, pathlib\n"
        "from contextor.core.live_state import CanonicalLiveServer\n"
        "from contextor.core.live_state.runtime import endpoint_file\n"
        "time.sleep(0.25)\n"
        "server = CanonicalLiveServer(None, revision=1)\n"
        "ep_file = endpoint_file(pathlib.Path(sys.argv[1]))\n"
        "ep_file.parent.mkdir(parents=True, exist_ok=True)\n"
        "ep_file.write_text(json.dumps({\n"
        "    'host': server.endpoint.host,\n"
        "    'port': server.endpoint.port,\n"
        "    'authkey_hex': server.endpoint.authkey_hex,\n"
        "    'pid': os.getpid(),\n"
        "    'repo_id': 'test_repo',\n"
        "    'root_path': sys.argv[1],\n"
        "    'owner_token': 'delayed_token',\n"
        "}), encoding='utf-8')\n"
        "server.serve_forever()\n",
        encoding="utf-8",
    )

    # Monkeypatch _spawn_runtime_subprocess to run our delayed server
    from contextor.core.live_state import runtime as runtime_mod
    orig_spawn = runtime_mod._spawn_runtime_subprocess

    def mock_spawn(cmd, cwd, env):
        delayed_cmd = [sys.executable, str(helper), str(repo)]
        return orig_spawn(delayed_cmd, cwd, env)

    monkeypatch.setattr(runtime_mod, "_spawn_runtime_subprocess", mock_spawn)

    # Normal connect timeout is short (0.08s), but cold start timeout is 2.0s
    t0 = time.monotonic()
    client = runtime_mod.connect_or_start(
        repo,
        owner_token="delayed_token",
        timeout=0.08,
        cold_start_timeout=2.0,
    )
    elapsed = time.monotonic() - t0

    assert client is not None
    assert elapsed >= 0.20  # Verified it waited past 0.08s without killing the child
    status = client.ping()
    assert status.get("status") == "ok"
    client.request("shutdown")


def test_connect_or_start_dead_child_fast_failure(tmp_path, monkeypatch):
    """Regression: Dead child process fails fast with exit code rather than waiting for timeout.
    """
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    from contextor.core.live_state import runtime as runtime_mod
    orig_spawn = runtime_mod._spawn_runtime_subprocess

    # Mock subprocess that immediately exits with code 42
    def mock_spawn(cmd, cwd, env):
        exit_cmd = [sys.executable, "-c", "import sys; sys.exit(42)"]
        return orig_spawn(exit_cmd, cwd, env)

    monkeypatch.setattr(runtime_mod, "_spawn_runtime_subprocess", mock_spawn)

    t0 = time.monotonic()
    import pytest
    with pytest.raises(RuntimeError) as exc_info:
        runtime_mod.connect_or_start(
            repo,
            timeout=0.05,
            cold_start_timeout=10.0,
        )
    elapsed = time.monotonic() - t0

    assert "exited prematurely with code 42" in str(exc_info.value)
    assert elapsed < 1.0  # Fast failure (did not wait 10s)


def test_connect_or_start_true_startup_hang(tmp_path, monkeypatch):
    """Regression: True startup hang terminates child and raises TimeoutError upon hard cold_start_timeout.
    """
    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))

    from contextor.core.live_state import runtime as runtime_mod
    orig_spawn = runtime_mod._spawn_runtime_subprocess

    spawned_pids = []

    # Mock subprocess that hangs (sleeps 30s) without publishing endpoint
    def mock_spawn(cmd, cwd, env):
        hang_cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        proc = orig_spawn(hang_cmd, cwd, env)
        spawned_pids.append(proc.pid)
        return proc

    monkeypatch.setattr(runtime_mod, "_spawn_runtime_subprocess", mock_spawn)

    import pytest
    with pytest.raises(TimeoutError) as exc_info:
        runtime_mod.connect_or_start(
            repo,
            timeout=0.05,
            cold_start_timeout=0.25,
        )

    assert "timed out after 0.25s" in str(exc_info.value)
    assert len(spawned_pids) == 1
    child_pid = spawned_pids[0]

    # Verify child was killed by connect_or_start
    time.sleep(0.1)
    assert not runtime_mod._is_pid_alive(child_pid)



