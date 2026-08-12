"""Regression tests for MCP subprocess handling and single-file reports."""

import asyncio
import json
import os
import subprocess
from pathlib import Path

from contextor import mcp_process_registry, mcp_server
from contextor.core.analysis import git_context
from contextor.core.api.facade import ContextorFacade


def test_git_never_inherits_mcp_stdin_and_unregisters_after_exit(tmp_path, monkeypatch):
    registry = tmp_path / "registry"
    monkeypatch.setenv("CONTEXTOR_MCP_PROCESS_REGISTRY", str(registry))
    monkeypatch.setattr(git_context.shutil, "which", lambda _: "C:/Git/bin/git.exe")

    popen_call = {}

    class FakeProcess:
        pid = 4321
        returncode = 0

        def __init__(self, command, **kwargs):
            popen_call["command"] = command
            popen_call["kwargs"] = kwargs

        def communicate(self):
            return "abc123\n", ""

    registered = []
    removed = []

    def fake_register(directory, **record):
        registered.append((directory, record))
        return directory / "git-4321.json"

    monkeypatch.setattr(git_context.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(git_context, "register_process", fake_register)
    monkeypatch.setattr(git_context, "remove_record", removed.append)

    result = git_context._run_git(["rev-parse", "HEAD"], str(tmp_path))

    assert result == "abc123"
    assert popen_call["command"][0] == "C:/Git/bin/git.exe"
    assert popen_call["kwargs"]["stdin"] is subprocess.DEVNULL
    assert popen_call["kwargs"]["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert popen_call["kwargs"]["env"]["GIT_PAGER"] == "cat"
    assert registered[0][0] == registry
    assert registered[0][1]["parent_pid"] == os.getpid()
    assert removed == [registry / "git-4321.json"]


def test_git_unregisters_even_when_communication_fails(tmp_path, monkeypatch):
    registry = tmp_path / "registry"
    monkeypatch.setenv("CONTEXTOR_MCP_PROCESS_REGISTRY", str(registry))

    class BrokenProcess:
        pid = 9876

        def __init__(self, *_args, **_kwargs):
            pass

        def communicate(self):
            raise OSError("simulated pipe failure")

    record = registry / "git-9876.json"
    removed = []
    monkeypatch.setattr(git_context.subprocess, "Popen", BrokenProcess)
    monkeypatch.setattr(git_context, "register_process", lambda *_args, **_kwargs: record)
    monkeypatch.setattr(git_context, "remove_record", removed.append)

    assert git_context._run_git(["status"], str(tmp_path)) is None
    assert removed == [record]


def test_registry_rejects_reused_pid(monkeypatch):
    record = {
        "pid": 123,
        "executable": "C:/Git/bin/git.exe",
        "creation_time": 100,
    }
    monkeypatch.setattr(
        mcp_process_registry,
        "process_identity",
        lambda _pid: ("C:/Git/bin/git.exe", 200, True),
    )

    assert not mcp_process_registry.record_matches_process(record)


def _write_process_record(directory: Path, name: str, **values) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def test_startup_cleanup_stops_only_orphaned_registered_processes(tmp_path, monkeypatch):
    directory = tmp_path / "registry"
    orphan = _write_process_record(
        directory, "git-10", pid=10, parent_pid=20, kind="git"
    )
    live = _write_process_record(
        directory, "git-11", pid=11, parent_pid=21, kind="git"
    )
    stopped = []

    monkeypatch.setattr(mcp_server, "record_matches_process", lambda _record: True)
    monkeypatch.setattr(
        mcp_server,
        "process_identity",
        lambda pid: ("python.exe", None, pid == 21),
    )
    monkeypatch.setattr(
        mcp_server,
        "terminate_registered_process",
        lambda record: stopped.append(record["pid"]) or True,
    )

    mcp_server._cleanup_orphaned_processes(directory)

    assert stopped == [10]
    assert not orphan.exists()
    assert live.exists()


def test_shutdown_cleanup_stops_only_children_owned_by_server(tmp_path, monkeypatch):
    directory = tmp_path / "registry"
    owned = _write_process_record(
        directory, "git-30", pid=30, parent_pid=100, kind="git"
    )
    foreign = _write_process_record(
        directory, "git-31", pid=31, parent_pid=200, kind="git"
    )
    stopped = []
    monkeypatch.setattr(
        mcp_server,
        "terminate_registered_process",
        lambda record: stopped.append(record["pid"]) or True,
    )

    mcp_server._cleanup_owned_processes(directory, owner_pid=100)

    assert stopped == [30]
    assert not owned.exists()
    assert foreign.exists()


def test_mcp_single_file_worker_uses_registry_and_restores_environment(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    target = repo / "module.py"
    repo.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    calls = []

    def fake_analysis(file_path, repo_path, log=None):
        calls.append((file_path, repo_path, log))
        assert os.environ["CONTEXTOR_DISABLE_PROCESS_POOL"] == "1"
        assert os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] == str(
            mcp_process_registry.registry_dir(repo)
        )

    monkeypatch.setattr(ContextorFacade, "analyze_single_file", fake_analysis)
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", "original-cache")
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    monkeypatch.delenv("CONTEXTOR_MCP_PROCESS_REGISTRY", raising=False)

    asyncio.run(mcp_server._run_analysis_worker("single_file", repo, target))

    assert calls == [(str(target), str(repo), mcp_server._stderr_log)]
    assert os.environ["CONTEXTOR_CACHE_DIR"] == "original-cache"
    assert "CONTEXTOR_DISABLE_PROCESS_POOL" not in os.environ
    assert "CONTEXTOR_MCP_PROCESS_REGISTRY" not in os.environ


def test_single_file_report_is_written_end_to_end(sample_repo, isolated_dirs):
    target = sample_repo / "core" / "alpha.py"

    output = Path(ContextorFacade.analyze_single_file(str(target), str(sample_repo)))

    assert output.is_file()
    assert output.name == "single_core.alpha.json"
    assert output.with_name("single_core.alpha_graph_analytics.json").is_file()
    assert output.with_name("single_core.alpha_llm_context.md").is_file()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert Path(report["file"]).resolve() == target.resolve()
    assert report["module_id"]
    assert report["generated_at"]
