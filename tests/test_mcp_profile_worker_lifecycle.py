import asyncio
import os
from pathlib import Path

import pytest

from contextor.mcp.tools import (
    contextor_profile_analysis as profile_module,
)


class _FakeProcess:
    def __init__(
        self,
        *,
        pid=1234,
        returncode=None,
        stdout=b'{"status":"ok"}',
        stderr=b"",
        communicate_error=None,
    ):
        self.pid = pid
        self.returncode = returncode
        self.stdout_payload = stdout
        self.stderr_payload = stderr
        self.communicate_error = communicate_error
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls = 0

    async def communicate(self, _request):
        if self.communicate_error is not None:
            raise self.communicate_error
        self.returncode = 0
        return (
            self.stdout_payload,
            self.stderr_payload,
        )

    async def wait(self):
        self.wait_calls += 1
        if self.returncode is None:
            self.returncode = -15
        return self.returncode

    def terminate(self):
        self.terminate_calls += 1
        self.returncode = -15

    def kill(self):
        self.kill_calls += 1
        self.returncode = -9


def test_profile_worker_registers_and_removes_record(
    tmp_path,
    monkeypatch,
):
    process = _FakeProcess()
    central = tmp_path / "mcp-processes"
    registered = []
    removed = []

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(
        profile_module.asyncio,
        "create_subprocess_exec",
        fake_create,
    )
    monkeypatch.setattr(
        profile_module,
        "register_process",
        lambda directory, **kwargs: (
            registered.append(
                (Path(directory), kwargs)
            )
            or central / "profile-worker-1234.json"
        ),
    )
    monkeypatch.setattr(
        profile_module,
        "remove_record",
        lambda path: removed.append(path),
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(central),
    )

    result = asyncio.run(
        profile_module._run_profile_subprocess(
            tmp_path,
            exclude_paths=None,
        )
    )

    assert result == {"status": "ok"}
    assert registered == [
        (
            central,
            {
                "pid": 1234,
                "parent_pid": os.getpid(),
                "kind": "profile-worker",
                "executable": profile_module.sys.executable,
            },
        )
    ]
    assert removed == [
        central / "profile-worker-1234.json"
    ]


def test_profile_worker_without_registry_keeps_normal_contract(
    tmp_path,
    monkeypatch,
):
    process = _FakeProcess()

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(
        profile_module.asyncio,
        "create_subprocess_exec",
        fake_create,
    )
    monkeypatch.delenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        raising=False,
    )
    monkeypatch.setattr(
        profile_module,
        "register_process",
        lambda *_args, **_kwargs: (
            pytest.fail(
                "profile worker must not register "
                "without registry environment"
            )
        ),
    )

    result = asyncio.run(
        profile_module._run_profile_subprocess(
            tmp_path,
            exclude_paths=[],
        )
    )

    assert result == {"status": "ok"}


def test_profile_worker_exception_terminates_registered_tree(
    tmp_path,
    monkeypatch,
):
    process = _FakeProcess(
        communicate_error=RuntimeError(
            "communication failed"
        )
    )
    central = tmp_path / "mcp-processes"
    record = central / "profile-worker-1234.json"
    terminated = []
    removed = []

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(
        profile_module.asyncio,
        "create_subprocess_exec",
        fake_create,
    )
    monkeypatch.setattr(
        profile_module,
        "register_process",
        lambda *_args, **_kwargs: record,
    )
    monkeypatch.setattr(
        profile_module,
        "terminate_registered_record",
        lambda path: (
            terminated.append(path)
            or True
        ),
    )
    monkeypatch.setattr(
        profile_module,
        "remove_record",
        lambda path: removed.append(path),
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(central),
    )

    with pytest.raises(
        RuntimeError,
        match="communication failed",
    ):
        asyncio.run(
            profile_module._run_profile_subprocess(
                tmp_path,
                exclude_paths=None,
            )
        )

    assert terminated == [record]
    assert removed == [record]


def test_profile_worker_cancellation_uses_same_cleanup_path(
    tmp_path,
    monkeypatch,
):
    started = asyncio.Event()
    release = asyncio.Event()
    central = tmp_path / "mcp-processes"
    record = central / "profile-worker-1234.json"
    terminated = []

    class _BlockingProcess(_FakeProcess):
        async def communicate(self, _request):
            started.set()
            await release.wait()
            self.returncode = 0
            return (
                self.stdout_payload,
                self.stderr_payload,
            )

    process = _BlockingProcess()

    async def fake_create(*_args, **_kwargs):
        return process

    monkeypatch.setattr(
        profile_module.asyncio,
        "create_subprocess_exec",
        fake_create,
    )
    monkeypatch.setattr(
        profile_module,
        "register_process",
        lambda *_args, **_kwargs: record,
    )
    monkeypatch.setattr(
        profile_module,
        "terminate_registered_record",
        lambda path: (
            terminated.append(path)
            or True
        ),
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(central),
    )

    async def scenario():
        task = asyncio.create_task(
            profile_module._run_profile_subprocess(
                tmp_path,
                exclude_paths=None,
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    assert terminated == [record]


def test_profile_worker_nonzero_exit_keeps_existing_error_contract(
    tmp_path,
    monkeypatch,
):
    process = _FakeProcess(
        returncode=1,
        stderr=b"profile failed",
    )

    async def fake_create(*_args, **_kwargs):
        return process

    async def fake_communicate(_request):
        return (
            b"",
            b"profile failed",
        )

    process.communicate = fake_communicate
    monkeypatch.setattr(
        profile_module.asyncio,
        "create_subprocess_exec",
        fake_create,
    )
    monkeypatch.delenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Contextor profile worker failed: profile failed",
    ):
        asyncio.run(
            profile_module._run_profile_subprocess(
                tmp_path,
                exclude_paths=None,
            )
        )
