from pathlib import Path
import pytest
from contextor.core.analysis import profile_runner
from contextor.core.analysis.full_analysis_coordinator import FullAnalysisBusyError
from contextor.core.analysis.profile_analysis import PROFILE_SCHEMA
from contextor.core.runtime_trace import trace_event
def test_profile_runner_scopes_capture_and_uses_nonblocking_coordinator(
    tmp_path: Path,
    monkeypatch,
):
    observed: dict[str, object] = {}
    def fake_run(path, **kwargs):
        observed["path"] = path
        observed["kwargs"] = kwargs
        trace_event(
            "ANALYSIS",
            "PROFILE_RUNNER_PROBE",
            operation="runner_probe",
        )
        return "ignored"
    def fake_build(events, *, operation_id):
        observed["events"] = list(events)
        observed["operation_id"] = operation_id
        return {
            "schema": PROFILE_SCHEMA,
            "status": "ok",
            "operation_id": operation_id,
        }
    monkeypatch.setattr(
        profile_runner,
        "run_full_analysis_exclusive",
        fake_run,
    )
    monkeypatch.setattr(
        profile_runner,
        "build_analysis_profile",
        fake_build,
    )
    result = profile_runner.run_analysis_profile(
        tmp_path,
        exclude_paths=["generated"],
    )
    assert Path(observed["path"]) == tmp_path.resolve()
    assert observed["kwargs"] == {
        "owner": "mcp_analysis",
        "timeout": 0.0,
        "additional_excludes": ["generated"],
    }
    operation_id = observed["operation_id"]
    assert isinstance(operation_id, str)
    assert operation_id.startswith("profile-")
    events = observed["events"]
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0]["ev"] == "PROFILE_RUNNER_PROBE"
    assert events[0]["op"] == operation_id
    assert result == {
        "schema": PROFILE_SCHEMA,
        "status": "ok",
        "operation_id": operation_id,
    }
def test_profile_runner_returns_busy_without_aggregating(
    tmp_path: Path,
    monkeypatch,
):
    observed: dict[str, object] = {}
    def fake_busy(path, **kwargs):
        observed["path"] = path
        observed["kwargs"] = kwargs
        raise FullAnalysisBusyError("busy")
    def forbidden_build(*args, **kwargs):
        raise AssertionError("busy profile must not be aggregated")
    monkeypatch.setattr(
        profile_runner,
        "run_full_analysis_exclusive",
        fake_busy,
    )
    monkeypatch.setattr(
        profile_runner,
        "build_analysis_profile",
        forbidden_build,
    )
    result = profile_runner.run_analysis_profile(tmp_path)
    assert Path(observed["path"]) == tmp_path.resolve()
    assert observed["kwargs"] == {
        "owner": "mcp_analysis",
        "timeout": 0.0,
        "additional_excludes": None,
    }
    assert result["schema"] == PROFILE_SCHEMA
    assert result["status"] == "busy"
    assert result["reason_code"] == "full_analysis_busy"
    assert isinstance(result["operation_id"], str)
    assert result["operation_id"].startswith("profile-")
def test_profile_runner_does_not_swallow_unexpected_analysis_errors(
    tmp_path: Path,
    monkeypatch,
):
    def fake_failure(path, **kwargs):
        raise RuntimeError("analysis failed")
    monkeypatch.setattr(
        profile_runner,
        "run_full_analysis_exclusive",
        fake_failure,
    )
    with pytest.raises(RuntimeError, match="analysis failed"):
        profile_runner.run_analysis_profile(tmp_path)
