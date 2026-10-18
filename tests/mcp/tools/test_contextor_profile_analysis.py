import asyncio
import json
from pathlib import Path

import pytest

import contextor.mcp.tools.contextor_profile_analysis as profile_tool


class _FakeProfileProcess:
    def __init__(self, payload: object, *, returncode: int = 0, stderr: bytes = b"", raw_stdout: bytes | None = None):
        self._stdout = raw_stdout if raw_stdout is not None else json.dumps(payload).encode("utf-8")
        self._stderr = stderr
        self.returncode = returncode
        self.request: bytes | None = None
    async def communicate(self, request: bytes):
        self.request = request
        return self._stdout, self._stderr


def test_contextor_profile_analysis_uses_isolated_worker_process(tmp_path: Path, monkeypatch):
    observed: dict[str, object] = {}
    fake_process = _FakeProfileProcess({"schema": "contextor-profile-analysis/v1", "status": "ok", "operation_id": "profile-test"})
    async def fake_create_subprocess_exec(*args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return fake_process
    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    raw = asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path), exclude_paths=["generated"]))
    payload = json.loads(raw)
    assert observed["args"] == (profile_tool.sys.executable, "-u", "-m", "contextor.core.analysis.profile_worker")
    assert observed["kwargs"] == {"stdin": asyncio.subprocess.PIPE, "stdout": asyncio.subprocess.PIPE, "stderr": asyncio.subprocess.PIPE}
    assert json.loads(fake_process.request.decode("utf-8")) == {"repo_path": str(tmp_path.resolve()), "exclude_paths": ["generated"]}
    assert payload == {"schema": "contextor-profile-analysis/v1", "status": "ok", "operation_id": "profile-test"}


def test_contextor_profile_analysis_rejects_missing_repository_before_worker(tmp_path: Path, monkeypatch):
    missing = tmp_path / "missing"
    async def forbidden_create_subprocess_exec(*args, **kwargs):
        raise AssertionError("invalid repository must not start profile worker")
    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", forbidden_create_subprocess_exec)
    result = asyncio.run(profile_tool.contextor_profile_analysis(str(missing)))
    assert result == f"Error: Repository path '{missing.resolve()}' does not exist."


def test_profile_worker_failure_propagates_as_runtime_error(tmp_path: Path, monkeypatch):
    fake_process = _FakeProfileProcess({}, returncode=1, stderr=b"worker exploded")
    async def fake_create_subprocess_exec(*args, **kwargs): return fake_process
    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    with pytest.raises(RuntimeError, match="^Contextor profile worker failed: worker exploded$"):
        asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path)))

def test_profile_worker_invalid_json_propagates_as_runtime_error(tmp_path: Path, monkeypatch):
    fake_process = _FakeProfileProcess({}, raw_stdout=b"not-json")
    async def fake_create_subprocess_exec(*args, **kwargs): return fake_process
    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    with pytest.raises(RuntimeError, match="^Contextor profile worker returned invalid JSON\\.$"):
        asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path)))


def test_profile_worker_non_object_payload_propagates_as_runtime_error(tmp_path: Path, monkeypatch):
    fake_process = _FakeProfileProcess(["unexpected"])
    async def fake_create_subprocess_exec(*args, **kwargs): return fake_process
    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    with pytest.raises(RuntimeError, match="^Contextor profile worker returned a non-object payload\\.$"):
        asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path)))


def test_catalog_and_invalid_input_never_spawn(tmp_path, monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail("worker spawned")
    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", forbidden)
    catalog = json.loads(asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path), mode="catalog")))
    assert catalog["mode"] == "catalog"
    for kwargs in [
        {"mode": "proeb"}, {"mode": "probe", "scope": "live.png", "presets": ["ping"]},
        {"mode": "probe", "scope": "live.ping", "presets": ["read_bytes"]},
        {"mode": "probe", "scope": "live.ping", "presets": ["ping", "ping"]},
        {"mode": "probe", "scope": "live.ping", "presets": []},
        {"mode": "probe", "scope": "live.ping", "presets": ["ping"], "samples": True},
        {"mode": "catalog", "scope": "live.ping"},
    ]:
        result = json.loads(asyncio.run(profile_tool.contextor_profile_analysis(str(tmp_path), **kwargs)))
        assert result["status"] == "invalid_profile_request"
    wrong = json.loads(asyncio.run(profile_tool.contextor_profile_analysis(
        str(tmp_path), mode="probe", scope="live.ping", presets=["read_bytes"])))
    assert wrong["owning_scope"] == "reports.summary"


def test_probe_request_payload(tmp_path, monkeypatch):
    process = _FakeProfileProcess({"schema": "contextor-atomic-profile/v1", "status": "ok"})
    async def create(*args, **kwargs):
        return process
    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", create)
    asyncio.run(profile_tool.contextor_profile_analysis(
        str(tmp_path), mode="probe", scope="live.ping", presets=["ping"]))
    assert json.loads(process.request) == {
        "repo_path": str(tmp_path.resolve()), "mode": "probe", "scope": "live.ping",
        "presets": ["ping"], "samples": 1, "warmup": 0, "result_view": "summary"}


def test_fuzzy_guidance_uses_shared_helper_without_execution(tmp_path, monkeypatch):
    seen = []
    def shared(value, choices):
        seen.append((value, choices))
        return [{"value": "live.ping", "score": 0.9}]
    monkeypatch.setattr(profile_tool, "fuzzy_choice_candidates", shared)
    async def forbidden(*args, **kwargs):
        pytest.fail("worker spawned")
    monkeypatch.setattr(profile_tool.asyncio, "create_subprocess_exec", forbidden)
    result = json.loads(asyncio.run(profile_tool.contextor_profile_analysis(
        str(tmp_path), mode="probe", scope="live.png", presets=["ping"])))
    assert result["similar_candidates"] == [{"value": "live.ping", "score": 0.9}]
    assert seen[0][0] == "live.png"
