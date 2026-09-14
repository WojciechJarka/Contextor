import asyncio
import json
from pathlib import Path

import contextor.mcp.tools.contextor_profile_analysis as profile_tool


def test_contextor_profile_analysis_offloads_runner_and_serializes_profile(tmp_path: Path, monkeypatch):
    observed: dict[str, object] = {}
    def fake_runner(repo_path, *, exclude_paths=None):
        raise AssertionError("runner must be invoked through asyncio.to_thread")
    async def fake_to_thread(func, *args, **kwargs):
        observed["func"] = func
        observed["args"] = args
        observed["kwargs"] = kwargs
        return {"schema": "contextor-profile-analysis/v1", "status": "ok", "operation_id": "profile-test"}
    monkeypatch.setattr(profile_tool, "run_analysis_profile", fake_runner)
    monkeypatch.setattr(profile_tool.asyncio, "to_thread", fake_to_thread)
    raw = asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path), exclude_paths=["generated"]))
    payload = json.loads(raw)
    assert observed["func"] is fake_runner
    assert observed["args"] == (tmp_path.resolve(),)
    assert observed["kwargs"] == {"exclude_paths": ["generated"]}
    assert payload == {"schema": "contextor-profile-analysis/v1", "status": "ok", "operation_id": "profile-test"}


def test_contextor_profile_analysis_rejects_missing_repository_before_runner(tmp_path: Path, monkeypatch):
    missing = tmp_path / "missing"
    def forbidden_runner(*args, **kwargs):
        raise AssertionError("invalid repository must not start profiler")
    monkeypatch.setattr(profile_tool, "run_analysis_profile", forbidden_runner)
    result = asyncio.run(profile_tool.contextor_profile_analysis(str(missing)))
    assert result == f"Error: Repository path '{missing.resolve()}' does not exist."
