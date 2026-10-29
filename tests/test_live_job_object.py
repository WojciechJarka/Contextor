"""Deterministic tests for Windows Job Object isolation, breakaway spawn, and fallback."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from contextor.core.live_state.ipc import LiveEndpoint, LiveStateClient
from contextor.core.live_state.runtime import (
    CREATE_BREAKAWAY_FROM_JOB,
    _spawn_runtime_subprocess,
    connect_or_start,
    endpoint_file,
)
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def test_windows_primary_spawn_flags_contain_breakaway_and_no_window(monkeypatch):
    calls = []

    def mock_popen(cmd, cwd, env, stdin, stdout, stderr, creationflags):
        calls.append({"cmd": cmd, "cwd": cwd, "creationflags": creationflags})
        return MagicMock(pid=12345)

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(sys, "platform", "win32")

    proc = _spawn_runtime_subprocess(["python.exe"], Path("."), {})

    assert len(calls) == 1
    expected_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | CREATE_BREAKAWAY_FROM_JOB
    assert calls[0]["creationflags"] == expected_flags
    assert calls[0]["creationflags"] & CREATE_BREAKAWAY_FROM_JOB
    assert calls[0]["creationflags"] & 0x08000000
    assert proc.pid == 12345


def test_non_windows_spawn_flags_are_zero(monkeypatch):
    calls = []

    def mock_popen(cmd, cwd, env, stdin, stdout, stderr, creationflags):
        calls.append({"cmd": cmd, "cwd": cwd, "creationflags": creationflags})
        return MagicMock(pid=54321)

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(sys, "platform", "linux")

    proc = _spawn_runtime_subprocess(["python"], Path("."), {})

    assert len(calls) == 1
    assert calls[0]["creationflags"] == 0
    assert proc.pid == 54321


def test_breakaway_denied_creation_performs_exactly_one_legacy_fallback(monkeypatch):
    calls = []

    def mock_popen(cmd, cwd, env, stdin, stdout, stderr, creationflags):
        calls.append(creationflags)
        if creationflags & CREATE_BREAKAWAY_FROM_JOB:
            err = PermissionError("Access is denied")
            err.winerror = 5
            raise err
        return MagicMock(pid=9999)

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(sys, "platform", "win32")

    proc = _spawn_runtime_subprocess(["python.exe"], Path("."), {})

    assert len(calls) == 2
    primary_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | CREATE_BREAKAWAY_FROM_JOB
    fallback_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    assert calls[0] == primary_flags
    assert calls[1] == fallback_flags
    assert proc.pid == 9999


def test_unrelated_spawn_error_is_not_swallowed(monkeypatch):
    calls = []

    def mock_popen(cmd, cwd, env, stdin, stdout, stderr, creationflags):
        calls.append(creationflags)
        raise FileNotFoundError("Executable not found")

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(FileNotFoundError, match="Executable not found"):
        _spawn_runtime_subprocess(["nonexistent.exe"], Path("."), {})

    assert len(calls) == 1


def test_arbitrary_permission_error_without_winerror_5_does_not_trigger_fallback(monkeypatch):
    calls = []

    def mock_popen(cmd, cwd, env, stdin, stdout, stderr, creationflags):
        calls.append(creationflags)
        err = PermissionError("Generic permission error without winerror 5")
        err.winerror = 13  # Not winerror 5
        raise err

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(PermissionError, match="Generic permission error"):
        _spawn_runtime_subprocess(["python.exe"], Path("."), {})

    assert len(calls) == 1


def test_failed_fallback_propagates_original_context(monkeypatch):
    calls = []

    def mock_popen(cmd, cwd, env, stdin, stdout, stderr, creationflags):
        calls.append(creationflags)
        if creationflags & CREATE_BREAKAWAY_FROM_JOB:
            err = PermissionError("Access is denied")
            err.winerror = 5
            raise err
        raise RuntimeError("Secondary fallback failure")

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(RuntimeError, match="Secondary fallback failure") as exc_info:
        _spawn_runtime_subprocess(["python.exe"], Path("."), {})

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, PermissionError)
    assert len(calls) == 2


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object integration test")
def test_real_windows_job_object_breakaway_integration(tmp_path, monkeypatch):
    """Prove that a helper in a KILL_ON_JOB_CLOSE Job Object spawns a surviving breakaway LIVE."""
    import ctypes
    import ctypes.wintypes

    kernel32 = ctypes.windll.kernel32

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.wintypes.DWORD),
            ("SchedulingClass", ctypes.wintypes.DWORD),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryLimit", ctypes.c_size_t),
            ("PeakJobMemoryLimit", ctypes.c_size_t),
        ]

    cache = tmp_path / "cache"
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))

    keeper_pid = os.getpid()
    keeper_token = "job-keeper-token-123"

    # Create Windows Job Object with KILL_ON_JOB_CLOSE (0x2000) and BREAKAWAY_OK (0x0800)
    hJob = kernel32.CreateJobObjectW(None, None)
    assert hJob, f"Failed to create Job Object: {ctypes.GetLastError()}"
    helper = None
    live_client = None
    ready_path = tmp_path / "live-helper-ready"
    try:
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x2000 | 0x0800
        res = kernel32.SetInformationJobObject(hJob, 9, ctypes.byref(info), ctypes.sizeof(info))
        assert res != 0, f"Failed to set Job Object info: {ctypes.GetLastError()}"

        # Helper process assigned to that Job Object
        helper_code = f"""
import os, sys, time
from pathlib import Path
from contextor.core.live_state.runtime import connect_or_start

os.environ["CONTEXTOR_CACHE_DIR"] = {repr(str(cache))}
repo = Path({repr(str(repo))})
client = connect_or_start(repo, owner_pid={keeper_pid}, owner_token={repr(keeper_token)})
Path({repr(str(ready_path))}).write_text(str(client.service_pid), encoding="ascii")
time.sleep(60)
"""

        helper = subprocess.Popen(
            [sys.executable, "-c", helper_code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        assigned = kernel32.AssignProcessToJobObject(hJob, int(helper._handle))
        assert assigned != 0, f"Failed to assign helper to Job Object: {ctypes.GetLastError()}"

        deadline = time.monotonic() + 15.0
        while not ready_path.is_file():
            if helper.poll() is not None:
                pytest.fail("LIVE helper exited before readiness")
            if time.monotonic() >= deadline:
                pytest.fail("LIVE helper readiness timed out after 15 seconds")
            time.sleep(0.05)
        service_pid = int(ready_path.read_text(encoding="ascii"))

        # Close the Job Object handle and terminate the helper process
        kernel32.CloseHandle(hJob)
        hJob = None
        try:
            helper.terminate()
            helper.wait(timeout=2)
        except Exception:
            pass

        # Since keeper_pid is alive and LIVE broke away from helper's Job Object, LIVE must survive!
        time.sleep(0.5)
        from contextor.core.live_state.runtime import connect

        live_client = connect(repo)
        assert live_client is not None, "LIVE process died when helper Job Object closed!"
        status = live_client.ping()
        assert status.get("status") == "ok"
        assert live_client.service_pid == service_pid
        assert live_client.owner_token == keeper_token
        assert live_client.owner_pid == keeper_pid
    finally:
        try:
            if hJob is not None:
                kernel32.CloseHandle(hJob)
        finally:
            try:
                if live_client is None:
                    from contextor.core.live_state.runtime import connect

                    try:
                        live_client = connect(repo)
                    except Exception:
                        pass
                if live_client is not None:
                    try:
                        live_client.request("shutdown", timeout=2.0)
                    except Exception:
                        pass
            finally:
                if helper is not None:
                    try:
                        if helper.poll() is None:
                            helper.terminate()
                    except Exception:
                        pass
                    try:
                        helper.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        if helper.poll() is None:
                            helper.kill()
                        helper.wait(timeout=5.0)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object cleanup regression")
@pytest.mark.parametrize("failure", ["assignment", "readiness_timeout", "shutdown"])
def test_windows_job_object_cleanup_regression(tmp_path, monkeypatch, failure):
    import ctypes
    import contextor.core.live_state.runtime as runtime

    events = []

    class Helper:
        _handle = 123
        alive = True

        def poll(self):
            return None if self.alive else 0

        def terminate(self):
            events.append("terminate")
            self.alive = False

        def wait(self, timeout):
            events.append(("wait", timeout))
            return 0

        def kill(self):
            events.append("kill")
            self.alive = False

    helper = Helper()
    kernel32 = SimpleNamespace(
        CreateJobObjectW=lambda *_: 77,
        SetInformationJobObject=lambda *_: 1,
        AssignProcessToJobObject=lambda *_: 0 if failure == "assignment" else 1,
        CloseHandle=lambda handle: events.append(("close", handle)),
    )
    monkeypatch.setattr(ctypes.windll, "kernel32", kernel32)

    def fake_popen(*_args, **_kwargs):
        if failure == "shutdown":
            (tmp_path / "live-helper-ready").write_text("456", encoding="ascii")
        return helper

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    client = SimpleNamespace(
        service_pid=456,
        owner_token="job-keeper-token-123",
        owner_pid=os.getpid(),
        ping=lambda: {"status": "ok"},
        request=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("shutdown failed")),
    )
    monkeypatch.setattr(runtime, "connect", lambda root: client if failure == "shutdown" else None)

    if failure == "readiness_timeout":
        import itertools

        ticks = itertools.count()
        monkeypatch.setattr(time, "monotonic", lambda: next(ticks) * 20.0)

    if failure == "assignment":
        with pytest.raises(AssertionError, match="Failed to assign helper"):
            test_real_windows_job_object_breakaway_integration(tmp_path, monkeypatch)
    elif failure == "readiness_timeout":
        with pytest.raises(pytest.fail.Exception, match="readiness timed out"):
            test_real_windows_job_object_breakaway_integration(tmp_path, monkeypatch)
    else:
        test_real_windows_job_object_breakaway_integration(tmp_path, monkeypatch)

    assert ("close", 77) in events
    assert "terminate" in events
    assert ("wait", 5.0) in events or ("wait", 2) in events
    assert helper.poll() is not None
