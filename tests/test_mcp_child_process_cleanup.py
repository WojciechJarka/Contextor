import asyncio
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import contextor.mcp_process_registry as registry
import contextor.mcp_server as mcp_server
from contextor.mcp import analysis_jobs


def test_windows_registered_process_termination_uses_tree_kill(
    monkeypatch,
):
    calls = []
    identities = iter(
        [
            ("C:/Python/python.exe", 100, True),
            (None, None, False),
        ]
    )
    monkeypatch.setattr(
        registry,
        "sys_platform_is_windows",
        lambda: True,
    )
    monkeypatch.setattr(
        registry,
        "process_identity",
        lambda _pid: next(identities),
    )

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        registry.subprocess,
        "run",
        lambda command, **_kwargs: (
            calls.append(command)
            or _Result()
        ),
    )
    record = {
        "pid": 1234,
        "executable": "C:/Python/python.exe",
        "creation_time": 100,
    }
    assert registry.terminate_registered_process(
        record
    ) is True
    assert calls == [
        [
            "taskkill",
            "/F",
            "/T",
            "/PID",
            "1234",
        ]
    ]


def test_analysis_worker_preserves_preconfigured_server_registry(
    tmp_path,
    monkeypatch,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "module.py"
    target.write_text(
        "x = 1\n",
        encoding="utf-8",
    )
    central = tmp_path / "central-registry"
    seen = []

    def fake_analysis(
        file_path,
        repo_root,
        log=None,
        progress_callback=None,
        additional_excludes=None,
    ):
        seen.append(
            os.environ.get(
                "CONTEXTOR_MCP_PROCESS_REGISTRY"
            )
        )
        return None

    monkeypatch.setattr(
        analysis_jobs.ContextorFacade,
        "analyze_single_file",
        staticmethod(fake_analysis),
    )
    monkeypatch.setenv(
        "CONTEXTOR_MCP_PROCESS_REGISTRY",
        str(central),
    )
    asyncio.run(
        analysis_jobs._run_analysis_worker(
            "single_file",
            repo,
            target,
        )
    )
    assert seen == [str(central)]
    assert (
        os.environ[
            "CONTEXTOR_MCP_PROCESS_REGISTRY"
        ]
        == str(central)
    )


def test_request_analysis_shutdown_cooperatively_joins_task():
    analysis_jobs._analysis_shutdown_event.clear()
    analysis_jobs._analysis_tasks.clear()
    analysis_jobs._analysis_jobs_by_repo.clear()
    exited = threading.Event()

    def worker():
        while (
            not analysis_jobs
            ._analysis_shutdown_event
            .is_set()
        ):
            time.sleep(0.01)
        exited.set()

    task = threading.Thread(
        target=worker,
        daemon=True,
    )
    task.start()
    analysis_jobs._analysis_tasks["test"] = task
    try:
        survivors = (
            analysis_jobs.request_analysis_shutdown(
                timeout=1.0,
            )
        )
        assert survivors == 0
        assert exited.is_set()
        assert not task.is_alive()
    finally:
        analysis_jobs._analysis_shutdown_event.clear()
        analysis_jobs._analysis_tasks.clear()
        analysis_jobs._analysis_jobs_by_repo.clear()


def test_mcp_shutdown_order_is_analysis_pool_owned_orphan(
    tmp_path,
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        analysis_jobs,
        "request_analysis_shutdown",
        lambda *, timeout: (
            calls.append(("analysis", timeout))
            or 0
        ),
    )
    monkeypatch.setattr(
        mcp_server,
        "terminate_active_process_pools",
        lambda *, timeout: (
            calls.append(("pools", timeout))
            or 0
        ),
    )
    monkeypatch.setattr(
        mcp_server,
        "_cleanup_owned_processes",
        lambda directory, owner_pid: calls.append(
            (
                "owned",
                Path(directory),
                owner_pid,
            )
        ),
    )
    monkeypatch.setattr(
        mcp_server,
        "_cleanup_orphaned_processes",
        lambda directory: calls.append(
            (
                "orphaned",
                Path(directory),
            )
        ),
    )
    directory = tmp_path / "registry"
    mcp_server._shutdown_mcp_owned_processes(
        directory,
        777,
        timeout=0.25,
    )
    assert calls == [
        ("analysis", 0.25),
        ("pools", 0.25),
        ("analysis", 0.25),
        ("owned", directory, 777),
        ("orphaned", directory),
    ]
