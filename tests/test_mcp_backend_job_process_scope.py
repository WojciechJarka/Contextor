from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import contextor.mcp_backend_job as guard
import contextor.core.live_state.runtime as runtime


def test_inherited_environment_cannot_fake_job_guard(
    monkeypatch,
):
    monkeypatch.setattr(
        runtime.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(guard, "_active_handle", None)
    monkeypatch.setattr(guard, "_active_pid", None)
    monkeypatch.setenv(
        "CONTEXTOR_BACKEND_JOB_GUARD",
        "1",
    )

    process = SimpleNamespace(_handle=42)

    monkeypatch.setattr(
        runtime.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        guard,
        "require_live_outside_backend_job",
        lambda *_args: pytest.fail(
            "inherited environment marker was trusted"
        ),
    )

    result = runtime._spawn_runtime_subprocess(
        ["python.exe"],
        Path("."),
        {},
    )

    assert result is process
    assert not guard.backend_job_active_for_current_process()


def test_stale_process_local_guard_refuses_spawn(
    monkeypatch,
):
    monkeypatch.setattr(
        runtime.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(guard, "_active_handle", 77)
    monkeypatch.setattr(
        guard,
        "_active_pid",
        os.getpid() + 1,
    )

    monkeypatch.setattr(
        runtime.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail(
            "spawn occurred with stale Job owner"
        ),
    )

    with pytest.raises(
        guard.BackendJobError,
        match="different process",
    ):
        runtime._spawn_runtime_subprocess(
            ["python.exe"],
            Path("."),
            {},
        )


def test_inconsistent_guard_state_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        guard.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(guard, "_active_handle", None)
    monkeypatch.setattr(
        guard,
        "_active_pid",
        os.getpid(),
    )

    with pytest.raises(
        guard.BackendJobError,
        match="inconsistent",
    ):
        guard.backend_job_active_for_current_process()


def test_untrusted_marker_does_not_disable_legacy_fallback(
    monkeypatch,
):
    monkeypatch.setattr(
        runtime.sys,
        "platform",
        "win32",
    )
    monkeypatch.setattr(guard, "_active_handle", None)
    monkeypatch.setattr(guard, "_active_pid", None)
    monkeypatch.setenv(
        "CONTEXTOR_BACKEND_JOB_GUARD",
        "1",
    )

    calls = []
    process = SimpleNamespace(_handle=92)

    def fake_spawn(*_args, **kwargs):
        calls.append(kwargs["creationflags"])
        if len(calls) == 1:
            error = PermissionError(
                "Access denied"
            )
            error.winerror = 5
            raise error
        return process

    monkeypatch.setattr(
        runtime.subprocess,
        "Popen",
        fake_spawn,
    )

    result = runtime._spawn_runtime_subprocess(
        ["python.exe"],
        Path("."),
        {},
    )

    assert result is process
    assert len(calls) == 2
    assert calls[0] & runtime.CREATE_BREAKAWAY_FROM_JOB
    assert not (
        calls[1] & runtime.CREATE_BREAKAWAY_FROM_JOB
    )


def test_non_windows_guard_is_inactive(
    monkeypatch,
):
    monkeypatch.setattr(
        guard.sys,
        "platform",
        "linux",
    )
    monkeypatch.setattr(guard, "_active_handle", None)
    monkeypatch.setattr(guard, "_active_pid", None)

    assert not guard.backend_job_active_for_current_process()

