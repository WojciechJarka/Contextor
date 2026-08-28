import json
from types import SimpleNamespace

from contextor import mcp_server
from contextor.mcp.diagnostics import (
    diagnostics_summary,
    diagnostics_summary_for_completed_job,
    diagnostics_summary_for_state,
    inject_diagnostics_summary,
)
from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools.get_name_collisions import get_name_collisions
from contextor.mcp.tools.get_analysis_status import get_analysis_status


def _collision(kind="NAME_COLLISION", identical=False, module="pkg.a"):
    return SimpleNamespace(
        kind=kind,
        message=f"{kind} foo",
        nodes=[module, "pkg.b"],
        artifact_type="function",
        is_identical=identical,
        symbol_details=[],
        code_snippets={module: "def foo():\n    return 1", "pkg.b": "def foo():\n    return 2"},
    )


def test_diagnostics_summary_does_not_fabricate_unavailable_counts():
    summary = diagnostics_summary_for_state(SimpleNamespace(
        collisions_state="deferred", cycles_state="unavailable", collisions=None, cycles=None
    ))
    assert summary["name_collisions"]["count"] is None
    assert summary["cycles"]["count"] is None
    assert summary["availability"]["name_collisions"] == "deferred"


def test_get_name_collisions_filters_without_invented_ids(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    state = SimpleNamespace(
        collisions_state="fresh", collisions=[_collision(), _collision("IDENTICAL_DEFINITION_DUPLICATE", True, "pkg.c")],
        cycles_state="fresh", cycles=[], summary_data={}
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    first = json.loads(get_name_collisions(str(repo), conflicting_only=True))
    second = json.loads(get_name_collisions(str(repo), conflicting_only=True))
    assert first["matched"] == 1
    assert "collision_id" not in first["details"][0]
    assert first["conflicting"] == 1


def test_attention_required_tracks_each_available_family():
    clean = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
    assert diagnostics_summary_for_state(clean)["attention_required"] is False
    result = diagnostics_summary_for_state(clean)
    assert result["syntax_errors"] == {"count": None, "availability": "unavailable"}
    syntax_result = diagnostics_summary_for_completed_job(result, {"status": "completed", "operation": "project", "skipped_python_files": [{"reason": "not valid Python"}]})
    assert syntax_result["syntax_errors"] == {"count": 1, "availability": "fresh"}
    assert syntax_result["attention_required"] is True
    zero_result = diagnostics_summary_for_completed_job(result, {"status": "completed", "operation": "project", "skipped_python_files": []})
    assert zero_result["syntax_errors"] == {"count": 0, "availability": "fresh"}
    assert zero_result["attention_required"] is False
    assert diagnostics_summary_for_state(SimpleNamespace(collisions_state="fresh", collisions=[_collision()], cycles_state="fresh", cycles=[]))["attention_required"] is True
    assert diagnostics_summary_for_state(SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[["a", "b", "a"]]))["attention_required"] is True


def test_historical_job_does_not_promote_global_syntax_freshness(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
    monkeypatch.setattr("contextor.mcp.analysis_jobs._latest_analysis_job", lambda _root: {"status": "completed", "skipped_python_files": [{"reason": "not valid Python"}]})
    summary = diagnostics_summary(repo)
    assert summary["syntax_errors"] == {"count": None, "availability": "unavailable"}
    assert diagnostics_summary_for_completed_job(summary, {"status": "completed", "operation": "project", "skipped_python_files": [{"reason": "not valid Python"}]})["syntax_errors"] == {"count": 1, "availability": "fresh"}


def test_analysis_status_uses_only_the_exact_completed_project_job_for_syntax(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".contextor" / "analysis_jobs").mkdir(parents=True)
    job_id = "a" * 32
    (repo / ".contextor" / "analysis_jobs" / f"{job_id}.json").write_text(json.dumps({
        "job_id": job_id, "operation": "project", "repo_path": str(repo), "status": "completed",
        "skipped_python_files": [{"reason": "not valid Python"}], "live_publish_status": "success",
    }), encoding="utf-8")
    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
    result = json.loads(get_analysis_status(str(repo), job_id))
    assert result["diagnostics_summary"]["syntax_errors"] == {"count": 1, "availability": "fresh"}


def test_wrapper_injects_health_for_analytical_not_found(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
    wrapped = mcp_server._instrument_mcp_tool(lambda repo_path: json.dumps({"status": "not_found", "repo_path": repo_path}), "synthetic_query")
    result = json.loads(wrapped(str(repo)))
    assert "diagnostics_summary" in result


def test_wrapper_applies_shared_guard_after_diagnostics_injection(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    state = SimpleNamespace(collisions_state="fresh", collisions=[], cycles_state="fresh", cycles=[])
    monkeypatch.setitem(mcp_runtime._live_engines, str(repo.resolve()), SimpleNamespace(state=state))
    before = LARGE_OUTPUT_WARNING_BYTES - 40
    wrapped = mcp_server._instrument_mcp_tool(lambda repo_path: json.dumps({"status": "ok", "payload": "x" * before}), "synthetic_query")
    raw = wrapped(str(repo))
    assert len(raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES
    result = json.loads(raw)
    assert "diagnostics_summary" in result
    assert result["status"] == "confirmation_required"
    large = mcp_server._instrument_mcp_tool(lambda repo_path, allow_large_output=False: json.dumps({"status": "ok", "payload": "x" * (LARGE_OUTPUT_WARNING_BYTES + 100)}), "synthetic_query")
    bounded_raw = large(str(repo))
    assert len(bounded_raw.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES
    bounded = json.loads(bounded_raw)
    assert "diagnostics_summary" in bounded
    unbounded_raw = large(str(repo), allow_large_output=True)
    assert len(unbounded_raw.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES
    unbounded = json.loads(unbounded_raw)
    assert "diagnostics_summary" in unbounded
    pre_injection = json.dumps({"status": "ok", "payload": "x" * before})
    post_injection = inject_diagnostics_summary(pre_injection, repo, "synthetic_query", allow_large_output=True)
    assert len(pre_injection.encode("utf-8")) < LARGE_OUTPUT_WARNING_BYTES
    assert len(post_injection.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES


def test_get_name_collisions_indexed_representation_is_bounded(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    errors = [_collision(module=f"pkg.mod{i}") for i in range(30)]
    state = SimpleNamespace(collisions_state="fresh", collisions=errors, cycles_state="fresh", cycles=[], summary_data={})
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    result = json.loads(get_name_collisions(str(repo), representation="indexed", limit=3))
    assert result["returned"] == 3
    assert result["truncated"] is True
    assert all("conflicting_code" not in item for item in result["details"])


def test_registered_name_collision_tool_and_shared_summary_wrapper():
    assert "get_name_collisions" in mcp_server.REGISTERED_MCP_TOOL_NAMES
    assert len(mcp_server.REGISTERED_MCP_TOOL_NAMES) == 25
