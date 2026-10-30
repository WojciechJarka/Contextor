from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace

import pytest

import contextor.mcp_backend_job as guard
import contextor.mcp_main as entry
import contextor.mcp_server as server
import contextor.core.live_state.runtime as live_runtime


class _Function:
    def __init__(self, callback):
        self.callback = callback
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return self.callback(*args)


class _Kernel:
    def __init__(self):
        self.limits = None
        self.member = False
        self.assign_ok = True
        self.set_ok = True

        self.CreateJobObjectW = _Function(
            lambda *_args: 71
        )
        self.SetInformationJobObject = _Function(
            self._set_limits
        )
        self.GetCurrentProcess = _Function(
            lambda: 333
        )
        self.AssignProcessToJobObject = _Function(
            lambda *_args: int(self.assign_ok)
        )
        self.IsProcessInJob = _Function(
            self._is_member
        )
        self.CloseHandle = _Function(
            lambda *_args: 1
        )

    def _set_limits(
        self,
        handle,
        info_class,
        info_ptr,
        size,
    ):
        self.limits = ctypes.cast(
            info_ptr,
            ctypes.POINTER(guard._EXTENDED_LIMITS),
        ).contents.BasicLimitInformation.LimitFlags

        return int(self.set_ok)

    def _is_member(self, process, job, result):
        value = ctypes.cast(
            result,
            ctypes.POINTER(wintypes.BOOL),
        )
        value.contents.value = int(self.member)
        return 1


@pytest.fixture
def fake_job(monkeypatch):
    kernel = _Kernel()

    monkeypatch.setattr(
        guard.ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: kernel,
        raising=False,
    )
    monkeypatch.setattr(
        guard.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(
        guard,
        "_active_handle",
        None,
    )
    monkeypatch.setattr(
        guard,
        "_active_pid",
        None,
    )
    monkeypatch.delenv(
        "CONTEXTOR_BACKEND_JOB_GUARD",
        raising=False,
    )

    return kernel


def test_backend_job_owns_descendant_lifetime(
    fake_job,
):
    guard.protect_persistent_backend()

    assert fake_job.limits == 0x2800
    assert fake_job.CreateJobObjectW.calls == [
        (None, None)
    ]
    assert fake_job.AssignProcessToJobObject.calls == [
        (71, 333)
    ]
    assert fake_job.CloseHandle.calls == []
    assert guard._active_handle == 71
    assert guard._active_pid == os.getpid()
    assert guard.backend_job_active_for_current_process()
    assert "CONTEXTOR_BACKEND_JOB_GUARD" not in os.environ


def test_guard_install_is_idempotent(fake_job):
    guard.protect_persistent_backend()
    guard.protect_persistent_backend()

    assert len(fake_job.CreateJobObjectW.calls) == 1
    assert len(
        fake_job.AssignProcessToJobObject.calls
    ) == 1


def test_assignment_failure_closes_unowned_job(
    fake_job,
):
    fake_job.assign_ok = False

    with pytest.raises(
        guard.BackendJobError,
        match="AssignProcessToJobObject",
    ):
        guard.protect_persistent_backend()

    assert fake_job.CloseHandle.calls == [(71,)]
    assert guard._active_handle is None
    assert (
        "CONTEXTOR_BACKEND_JOB_GUARD"
        not in os.environ
    )


def test_limit_failure_blocks_assignment(fake_job):
    fake_job.set_ok = False

    with pytest.raises(
        guard.BackendJobError,
        match="SetInformationJobObject",
    ):
        guard.protect_persistent_backend()

    assert fake_job.AssignProcessToJobObject.calls == []
    assert fake_job.CloseHandle.calls == [(71,)]


def test_missing_guard_refuses_live_verification(
    fake_job,
):
    with pytest.raises(
        guard.BackendJobError,
        match="not installed",
    ):
        guard.require_live_outside_backend_job(
            SimpleNamespace(_handle=99)
        )


def test_live_outside_job_is_accepted(fake_job):
    guard.protect_persistent_backend()
    fake_job.member = False

    guard.require_live_outside_backend_job(
        SimpleNamespace(_handle=99)
    )

    assert fake_job.IsProcessInJob.calls
    assert fake_job.IsProcessInJob.calls[0][:2] == (
        99,
        71,
    )


def test_live_inside_job_is_rejected(fake_job):
    guard.protect_persistent_backend()
    fake_job.member = True

    with pytest.raises(
        guard.BackendJobError,
        match="did not break away",
    ):
        guard.require_live_outside_backend_job(
            SimpleNamespace(_handle=99)
        )


def test_mcp_entry_installs_guard_before_server(
    monkeypatch,
):
    events = []

    monkeypatch.setattr(
        entry.sys,
        "platform",
        "win32",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "persistent-backend",
    )
    monkeypatch.setattr(
        guard,
        "protect_persistent_backend",
        lambda: events.append("guard"),
    )
    monkeypatch.setattr(
        server,
        "main",
        lambda: events.append("server"),
    )

    entry.main()

    assert events == ["guard", "server"]


def test_mcp_entry_refuses_server_after_guard_failure(
    monkeypatch,
):
    monkeypatch.setattr(
        entry.sys,
        "platform",
        "win32",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "persistent-backend",
    )

    def fail_guard():
        raise guard.BackendJobError(
            "assignment unavailable"
        )

    monkeypatch.setattr(
        guard,
        "protect_persistent_backend",
        fail_guard,
    )
    monkeypatch.setattr(
        server,
        "main",
        lambda: pytest.fail(
            "unprotected server startup"
        ),
    )

    with pytest.raises(
        guard.BackendJobError,
        match="assignment unavailable",
    ):
        entry.main()


def test_nonpersistent_mcp_skips_guard(
    monkeypatch,
):
    events = []

    monkeypatch.setattr(
        entry.sys,
        "platform",
        "win32",
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_SERVER_ROLE",
        "host-owned",
    )
    monkeypatch.setattr(
        guard,
        "protect_persistent_backend",
        lambda: pytest.fail(
            "nonpersistent MCP entered backend job"
        ),
    )
    monkeypatch.setattr(
        server,
        "main",
        lambda: events.append("server"),
    )

    entry.main()

    assert events == ["server"]


def test_guarded_live_refuses_breakaway_fallback(
    monkeypatch,
):
    calls = []

    def denied(*_args, **_kwargs):
        calls.append("spawn")
        error = PermissionError(
            "Access is denied"
        )
        error.winerror = 5
        raise error

    monkeypatch.setattr(
        live_runtime.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(
        guard,
        "backend_job_active_for_current_process",
        lambda: True,
    )
    monkeypatch.setattr(
        live_runtime.subprocess,
        "Popen",
        denied,
    )

    with pytest.raises(
        RuntimeError,
        match="LIVE breakaway failed",
    ):
        live_runtime._spawn_runtime_subprocess(
            ["python.exe"],
            Path("."),
            {},
        )

    assert calls == ["spawn"]


def test_guarded_live_verifies_spawn_before_return(
    monkeypatch,
):
    process = SimpleNamespace(_handle=99)
    verified = []

    monkeypatch.setattr(
        live_runtime.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(
        guard,
        "backend_job_active_for_current_process",
        lambda: True,
    )
    monkeypatch.setattr(
        live_runtime.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        guard,
        "require_live_outside_backend_job",
        lambda actual: verified.append(actual),
    )

    result = live_runtime._spawn_runtime_subprocess(
        ["python.exe"],
        Path("."),
        {},
    )

    assert result is process
    assert verified == [process]


def test_guarded_live_rejects_membership_and_terminates(
    monkeypatch,
):
    calls = []

    class _Process:
        _handle = 99

        def terminate(self):
            calls.append("terminate")

        def wait(self, timeout):
            calls.append(("wait", timeout))
            return 1

    process = _Process()

    monkeypatch.setattr(
        live_runtime.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(
        guard,
        "backend_job_active_for_current_process",
        lambda: True,
    )
    monkeypatch.setattr(
        live_runtime.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )

    def fail_membership(actual):
        assert actual is process
        raise guard.BackendJobError(
            "LIVE did not break away"
        )

    monkeypatch.setattr(
        guard,
        "require_live_outside_backend_job",
        fail_membership,
    )

    with pytest.raises(
        guard.BackendJobError,
        match="did not break away",
    ):
        live_runtime._spawn_runtime_subprocess(
            ["python.exe"],
            Path("."),
            {},
        )

    assert calls == [
        "terminate",
        ("wait", 2.0),
    ]

