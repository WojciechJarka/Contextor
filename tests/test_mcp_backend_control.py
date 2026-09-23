from __future__ import annotations

import subprocess
import sys
import threading
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import contextor.mcp_backend_control as control
from contextor.mcp_backend_state import PersistentBackendRecord


@pytest.fixture
def backend_record(tmp_path: Path) -> PersistentBackendRecord:
    return PersistentBackendRecord(
        schema_version=1,
        instance_id="test-backend-instance",
        server_role="persistent-backend",
        transport="streamable-http",
        host="127.0.0.1",
        port=8765,
        pid=12345,
        executable=sys.executable,
        creation_time=987654321,
        process_registry=str((tmp_path / "registry").resolve()),
        started_at=1.0,
    )


def _status(
    state: control.BackendState,
    *,
    ready: bool = False,
    record: PersistentBackendRecord | None = None,
) -> control.BackendStatus:
    return control.BackendStatus(
        state=state,
        ready=ready,
        detail=state,
        record=record,
    )


class _FakeClient:
    def __init__(
        self,
        url: str,
        *,
        auth: str,
        timeout: float,
        init_timeout: float,
        server_name: str = "Contextor",
        ping_result: bool = True,
        enter_error: Exception | None = None,
        ping_error: Exception | None = None,
    ) -> None:
        self.url = url
        self.auth = auth
        self.timeout = timeout
        self.init_timeout = init_timeout
        self.initialize_result = SimpleNamespace(
            serverInfo=SimpleNamespace(name=server_name)
        )
        self.ping_result = ping_result
        self.enter_error = enter_error
        self.ping_error = ping_error
        self.ping_called = False

    async def __aenter__(self) -> _FakeClient:
        if self.enter_error is not None:
            raise self.enter_error
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def ping(self) -> bool:
        self.ping_called = True
        if self.ping_error is not None:
            raise self.ping_error
        return self.ping_result


def test_authenticated_probe_accepts_contextor_identity_and_ping(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "supplied-test-bearer-token"
    clients: list[_FakeClient] = []

    def make_client(url: str, **kwargs) -> _FakeClient:
        client = _FakeClient(url, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(control, "Client", make_client)

    assert control._probe_backend(
        backend_record,
        token,
        timeout=1.0,
    ) is True
    assert len(clients) == 1
    assert clients[0].url == "http://127.0.0.1:8765/mcp"
    assert clients[0].auth == token
    assert clients[0].ping_called is True


def test_authenticated_probe_rejects_wrong_server_identity(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[_FakeClient] = []

    def make_client(url: str, **kwargs) -> _FakeClient:
        client = _FakeClient(
            url,
            **kwargs,
            server_name="NotContextor",
        )
        clients.append(client)
        return client

    monkeypatch.setattr(control, "Client", make_client)

    assert control._probe_backend(
        backend_record,
        "test-token",
        timeout=1.0,
    ) is False
    assert clients[0].ping_called is False


def test_authenticated_probe_rejects_failed_ping(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control,
        "Client",
        lambda url, **kwargs: _FakeClient(
            url,
            **kwargs,
            ping_result=False,
        ),
    )

    assert control._probe_backend(
        backend_record,
        "test-token",
        timeout=1.0,
    ) is False


def test_authenticated_probe_fails_closed_on_client_exception(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control,
        "Client",
        lambda url, **kwargs: _FakeClient(
            url,
            **kwargs,
            enter_error=RuntimeError("initialize failed"),
        ),
    )

    assert control._probe_backend(
        backend_record,
        "test-token",
        timeout=1.0,
    ) is False


def test_status_without_record_is_stopped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(control, "read_backend_record", lambda: None)

    result = control.get_backend_status()

    assert result.state == "stopped"
    assert result.ready is False
    assert result.record is None


def test_status_stale_record_never_probes_http(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control,
        "read_backend_record",
        lambda: backend_record,
    )
    monkeypatch.setattr(control, "_record_process_matches", lambda record: False)
    monkeypatch.setattr(
        control,
        "_probe_backend",
        lambda *args, **kwargs: pytest.fail("stale owner must not be probed"),
    )

    result = control.get_backend_status()

    assert result.state == "stale"
    assert result.ready is False


def test_status_live_owner_requires_authenticated_readiness(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control,
        "read_backend_record",
        lambda: backend_record,
    )
    monkeypatch.setattr(control, "_record_process_matches", lambda record: True)
    monkeypatch.setattr(control, "read_backend_token", lambda: "stored-token")
    probe_results = iter((False, True))
    monkeypatch.setattr(
        control,
        "_probe_backend",
        lambda record, token, *, timeout: next(probe_results),
    )

    unready = control.get_backend_status()
    ready = control.get_backend_status()

    assert unready.state == "unready"
    assert unready.ready is False
    assert ready.state == "running"
    assert ready.ready is True


def test_backend_environment_contains_role_transport_registry_and_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = tmp_path / "process-registry"
    monkeypatch.setattr(
        control,
        "backend_process_registry_dir",
        lambda: registry,
    )

    env = control._backend_environment("secret")

    assert env["CONTEXTOR_MCP_TRANSPORT"] == "streamable-http"
    assert env["CONTEXTOR_MCP_SERVER_ROLE"] == "persistent-backend"
    assert env["CONTEXTOR_MCP_HOST"] == "127.0.0.1"
    assert env["CONTEXTOR_MCP_PORT"] == "8765"
    assert env["CONTEXTOR_MCP_PROCESS_REGISTRY"] == str(registry.resolve())
    assert env["CONTEXTOR_MCP_TOKEN"] == "secret"


def test_backend_spawn_never_places_token_in_argv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "unique-backend-token-sentinel"
    calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(control, "_backend_python", lambda: tmp_path / "python.exe")
    monkeypatch.setattr(control, "package_root", lambda: tmp_path)
    monkeypatch.setattr(
        control,
        "backend_process_registry_dir",
        lambda: tmp_path / "registry",
    )

    def fake_popen(cmd: list[str], **kwargs) -> SimpleNamespace:
        calls.append((cmd, kwargs))
        return SimpleNamespace(pid=12345)

    monkeypatch.setattr(control.subprocess, "Popen", fake_popen)

    control._spawn_backend_process(token)

    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert token not in " ".join(cmd)
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["CONTEXTOR_MCP_TOKEN"] == token
    assert all(
        token not in value
        for key, value in env.items()
        if key != "CONTEXTOR_MCP_TOKEN"
    )
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["stdout"] == subprocess.DEVNULL
    assert kwargs["stderr"] == subprocess.DEVNULL


def test_windows_backend_spawn_uses_breakaway_and_no_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(control.sys, "platform", "win32")
    monkeypatch.setattr(control, "_backend_python", lambda: tmp_path / "python.exe")
    monkeypatch.setattr(control, "package_root", lambda: tmp_path)
    monkeypatch.setattr(control, "backend_process_registry_dir", lambda: tmp_path)

    def fake_popen(cmd: list[str], **kwargs) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(pid=12345)

    monkeypatch.setattr(control.subprocess, "Popen", fake_popen)

    control._spawn_backend_process("test-token")

    assert len(calls) == 1
    flags = calls[0]["creationflags"]
    assert flags & control.CREATE_BREAKAWAY_FROM_JOB
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if create_no_window:
        assert flags & create_no_window


def test_windows_breakaway_denied_has_exactly_one_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(control.sys, "platform", "win32")
    monkeypatch.setattr(control, "_backend_python", lambda: tmp_path / "python.exe")
    monkeypatch.setattr(control, "package_root", lambda: tmp_path)
    monkeypatch.setattr(control, "backend_process_registry_dir", lambda: tmp_path)

    def denied_then_succeed(cmd: list[str], **kwargs) -> SimpleNamespace:
        calls.append(kwargs)
        if len(calls) == 1:
            exc = OSError("breakaway denied")
            exc.winerror = 5
            raise exc
        return SimpleNamespace(pid=12345)

    monkeypatch.setattr(control.subprocess, "Popen", denied_then_succeed)

    control._spawn_backend_process("test-token")

    assert len(calls) == 2
    assert calls[0]["creationflags"] & control.CREATE_BREAKAWAY_FROM_JOB
    assert not calls[1]["creationflags"] & control.CREATE_BREAKAWAY_FROM_JOB

    other_error = OSError("unrelated process creation failure")
    other_error.winerror = 87
    other_calls = 0

    def fail_unrelated(cmd: list[str], **kwargs) -> None:
        nonlocal other_calls
        other_calls += 1
        raise other_error

    monkeypatch.setattr(control.subprocess, "Popen", fail_unrelated)
    with pytest.raises(OSError) as raised:
        control._spawn_backend_process("test-token")

    assert raised.value is other_error
    assert other_calls == 1


def test_start_returns_existing_ready_backend_without_spawn(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready = _status("running", ready=True, record=backend_record)
    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(control, "get_or_create_backend_token", lambda: "stored-token")
    monkeypatch.setattr(control, "get_backend_status", lambda **kwargs: ready)
    monkeypatch.setattr(
        control,
        "_spawn_backend_process",
        lambda token: pytest.fail("ready backend must not be spawned again"),
    )

    assert control.start_backend() is ready


def test_start_removes_stale_record_before_spawn(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []
    stale = _status("stale", record=backend_record)
    ready = _status("running", ready=True, record=backend_record)
    process = SimpleNamespace(pid=12345)
    identity = {"pid": 12345, "executable": sys.executable, "creation_time": 1}
    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(
        control,
        "get_or_create_backend_token",
        lambda: calls.append("token") or "stored-token",
    )
    monkeypatch.setattr(
        control,
        "get_backend_status",
        lambda **kwargs: calls.append("status") or stale,
    )
    monkeypatch.setattr(
        control,
        "remove_backend_record_if_exact",
        lambda record: calls.append(("remove", record)) or True,
    )
    monkeypatch.setattr(
        control,
        "_spawn_backend_process",
        lambda token: calls.append(("spawn", token)) or process,
    )
    monkeypatch.setattr(
        control,
        "_spawn_identity_record",
        lambda spawned: calls.append(("identity", spawned)) or identity,
    )
    monkeypatch.setattr(
        control,
        "_wait_for_ready_backend",
        lambda spawned, **kwargs: calls.append(("wait", spawned)) or ready,
    )

    assert control.start_backend() is ready
    names = [item if isinstance(item, str) else item[0] for item in calls]
    assert names.index("remove") < names.index("spawn")
    assert names == ["token", "status", "remove", "spawn", "identity", "wait"]


def test_failed_start_terminates_only_exact_spawn_identity(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = SimpleNamespace(pid=54321)
    identity = {
        "pid": 54321,
        "executable": r"C:\Contextor\.venv\Scripts\python.exe",
        "creation_time": 123456789,
    }
    terminated: list[dict[str, object]] = []
    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(control, "get_or_create_backend_token", lambda: "stored-token")
    monkeypatch.setattr(control, "get_backend_status", lambda **kwargs: _status("stopped"))
    monkeypatch.setattr(control, "_spawn_backend_process", lambda token: process)
    monkeypatch.setattr(control, "_spawn_identity_record", lambda spawned: identity)
    monkeypatch.setattr(
        control,
        "_wait_for_ready_backend",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            control.BackendControlError("cold start failed")
        ),
    )
    monkeypatch.setattr(
        control,
        "terminate_registered_process",
        lambda record: terminated.append(record) or True,
    )

    with pytest.raises(control.BackendControlError, match="cold start failed"):
        control.start_backend()

    assert terminated == [identity]


def test_stop_without_record_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(control, "read_backend_record", lambda: None)
    monkeypatch.setattr(
        control,
        "terminate_registered_process",
        lambda record: pytest.fail("no owner record means no termination"),
    )

    result = control.stop_backend()

    assert result.state == "stopped"
    assert result.ready is False


def test_stop_stale_record_removes_metadata_without_termination(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed: list[PersistentBackendRecord] = []
    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(control, "read_backend_record", lambda: backend_record)
    monkeypatch.setattr(control, "_backend_owner_identity_matches", lambda record: False)
    monkeypatch.setattr(
        control,
        "remove_backend_record_if_exact",
        lambda record: removed.append(record) or True,
    )
    monkeypatch.setattr(
        control,
        "terminate_registered_process",
        lambda record: pytest.fail("stale record must not terminate a process"),
    )

    result = control.stop_backend()

    assert result.state == "stopped"
    assert removed == [backend_record]


def test_windows_stop_refuses_missing_creation_identity(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = replace(backend_record, creation_time=None)
    monkeypatch.setattr(control.sys, "platform", "win32")
    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(control, "read_backend_record", lambda: record)
    monkeypatch.setattr(control, "_backend_owner_identity_matches", lambda owner: True)
    monkeypatch.setattr(
        control,
        "terminate_registered_process",
        lambda owner: pytest.fail("missing Windows creation identity forbids termination"),
    )

    with pytest.raises(control.BackendControlError, match="creation identity"):
        control.stop_backend()


def test_windows_stop_uses_exact_backend_record_for_termination(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = replace(backend_record, creation_time=555000111)
    terminated: list[dict[str, object]] = []
    cleaned: list[PersistentBackendRecord] = []
    removed: list[PersistentBackendRecord] = []
    monkeypatch.setattr(control.sys, "platform", "win32")
    monkeypatch.setattr(control, "_BackendControlLock", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(control, "read_backend_record", lambda: record)
    monkeypatch.setattr(control, "_backend_owner_identity_matches", lambda owner: True)
    monkeypatch.setattr(
        control,
        "terminate_registered_process",
        lambda owner: terminated.append(owner) or True,
    )
    monkeypatch.setattr(control, "_wait_for_owner_exit", lambda owner, *, timeout: True)
    monkeypatch.setattr(
        control,
        "_cleanup_owned_registry_children",
        lambda owner: cleaned.append(owner),
    )
    monkeypatch.setattr(
        control,
        "remove_backend_record_if_exact",
        lambda owner: removed.append(owner) or True,
    )

    result = control.stop_backend()

    assert result.state == "stopped"
    assert terminated == [record.to_dict()]
    assert terminated[0]["pid"] == record.pid
    assert terminated[0]["executable"] == record.executable
    assert terminated[0]["creation_time"] == record.creation_time
    assert cleaned == [record]
    assert removed == [record]


def test_owned_registry_child_cleanup_is_parent_identity_scoped(
    backend_record: PersistentBackendRecord,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    good_path = Path(backend_record.process_registry) / "good.json"
    wrong_creation_path = Path(backend_record.process_registry) / "wrong-creation.json"
    other_parent_path = Path(backend_record.process_registry) / "other-parent.json"
    good = {
        "pid": 20001,
        "parent_pid": backend_record.pid,
        "parent_creation_time": backend_record.creation_time,
    }
    wrong_creation = {
        "pid": 20002,
        "parent_pid": backend_record.pid,
        "parent_creation_time": backend_record.creation_time + 1,
    }
    other_parent = {
        "pid": 20003,
        "parent_pid": backend_record.pid + 1,
        "parent_creation_time": backend_record.creation_time,
    }
    terminated: list[dict[str, object]] = []
    removed: list[Path] = []
    monkeypatch.setattr(
        control,
        "read_records",
        lambda directory: [
            (good_path, good),
            (wrong_creation_path, wrong_creation),
            (other_parent_path, other_parent),
        ],
    )
    monkeypatch.setattr(
        control,
        "terminate_registered_process",
        lambda child: terminated.append(child) or True,
    )
    monkeypatch.setattr(control, "remove_record", lambda path: removed.append(path))

    control._cleanup_owned_registry_children(backend_record)

    assert terminated == [good]
    assert removed == [good_path]


def test_control_lock_same_process_is_exclusive(
    tmp_path: Path,
) -> None:
    path = tmp_path / "control.lock"
    holder_entered = threading.Event()
    release_holder = threading.Event()
    holder_errors: list[Exception] = []

    def hold_lock() -> None:
        try:
            with control._BackendControlLock(path, timeout=2.0):
                holder_entered.set()
                if not release_holder.wait(timeout=2.0):
                    holder_errors.append(TimeoutError("test release event was not set"))
        except Exception as exc:  # pragma: no cover - asserted after joining
            holder_errors.append(exc)

    thread = threading.Thread(target=hold_lock)
    thread.start()
    try:
        assert holder_entered.wait(timeout=2.0)
        with pytest.raises(control.BackendControlError, match="lock is busy"):
            with control._BackendControlLock(path, timeout=0.0):
                pytest.fail("second same-process holder must not acquire the lock")
    finally:
        release_holder.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert holder_errors == []
