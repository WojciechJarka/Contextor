import json
import multiprocessing
import os
from pathlib import Path

import pytest

import contextor.core.runtime_trace as trace
from contextor.core.paths import runtime_logs_dir


def _reset_trace_state():
    trace.finish_desktop_trace_session()
    trace._active_meta = None
    trace._active_path = None
    trace._active_sid = None
    trace._last_pointer_check = 0.0


@pytest.fixture(autouse=True)
def isolate_runtime_trace_storage(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: logs)
    trace.finish_desktop_trace_session()
    trace._authority_emitters.clear()
    trace._sidecar_rollovers.clear()
    yield logs
    trace.finish_desktop_trace_session()
    trace._authority_emitters.clear()
    trace._sidecar_rollovers.clear()


def test_desktop_trace_session_headers_and_finish(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path / "logs")
    _reset_trace_state()
    path = trace.start_desktop_trace_session()
    assert path is not None and path.parent == tmp_path / "logs"
    trace.trace_event("LIVE", "TEST", err="x" * 1000, rev_before=1, rev_after=2)
    trace.finish_desktop_trace_session()
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert all(isinstance(item, dict) for item in records)
    assert [item["_type"] for item in records[:5]] == ["header", "fields", "domains", "revision_semantics", "events"]
    assert records[5]["ev"] == "SESSION_START"
    assert records[-1]["ev"] == "SESSION_END"
    assert trace.active_trace_path(force_refresh=True) is None
    assert not (tmp_path / "logs" / "contextor_runtime_active.json").exists()
    assert len(records[6]["err"]) == 500
    fields, events = records[1]["fields"], records[4]["events"]["LIVE"]
    assert {"attempt", "attempts", "attempts_used", "retry_delay", "runtime_domain_id", "repo_id", "endpoint_fingerprint", "service_pid", "lease_generation", "service_instance_id", "reason_code", "exception_class", "errno", "winerror", "error", "pid_alive", "endpoint_changed", "process_alive", "process_identity_matches", "endpoint_available", "endpoint_matches", "reason", "result", "side", "operation_or_request_type", "prior_endpoint_fingerprint", "prior_service_pid", "new_endpoint_fingerprint", "new_service_pid", "recovery_operation_id"} <= set(fields)
    assert {"LIVE_CONNECT_ATTEMPT", "LIVE_CONNECT_REJECT", "LIVE_CONNECT_RESULT", "LIVE_LIVENESS_RESULT", "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT", "LIVE_IPC_FAILURE", "LIVE_SERVICE_THREAD_FAILURE"} <= set(events)


def test_default_trace_session_uses_external_runtime_logs_root(tmp_path, monkeypatch):
    state = tmp_path / "user-state"
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(state))
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: state / "logs")
    _reset_trace_state()
    path = trace.start_desktop_trace_session()
    try:
        assert path is not None
        assert path.parent == runtime_logs_dir()
        assert path.parent == (state / "logs").resolve()
        assert not path.parent.is_relative_to(tmp_path / "repo")
    finally:
        trace.finish_desktop_trace_session()


def test_trace_noop_on_malformed_pointer(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path / "logs")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "contextor_runtime_active.json").write_text("{}", encoding="utf-8")
    _reset_trace_state()
    trace.trace_event("MCP", "CALL_START")
    assert trace.active_trace_path(force_refresh=True) is None


def test_operation_ids_and_monotonic_records(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path / "logs")
    _reset_trace_state()
    path = trace.start_desktop_trace_session()
    ops = [trace.new_trace_operation("m") for _ in range(3)]
    assert len(set(ops)) == 3 and all(item.startswith("m-") for item in ops)
    for op in ops:
        trace.trace_event("MCP", "CALL_END", op=op)
    trace.finish_desktop_trace_session()
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if json.loads(line).get("_type") is None]
    assert all(a["mono_ms"] <= b["mono_ms"] for a, b in zip(records, records[1:]))


def _append_worker(path, sid):
    trace._active_path = Path(path)
    trace._active_sid = sid
    trace._active_meta = {"sid": sid}
    trace._last_pointer_check = trace.time.monotonic()
    trace.trace_event("MCP", "APPEND", status="ok")


def test_multiprocess_append_is_valid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path / "logs")
    _reset_trace_state()
    path = trace.start_desktop_trace_session()
    ctx = multiprocessing.get_context("spawn")
    processes = [ctx.Process(target=_append_worker, args=(str(path), trace._active_sid)) for _ in range(4)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0
    trace.finish_desktop_trace_session()
    for line in path.read_text(encoding="utf-8").splitlines():
        json.loads(line)


def test_clean_shutdown_archives_runtime_active_pointer_before_delete(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: logs)
    _reset_trace_state()
    path = trace.start_desktop_trace_session()
    sid = trace._active_sid
    trace.finish_desktop_trace_session()
    assert not (logs / trace._POINTER_NAME).exists()
    snapshots = list(logs.glob(f"contextor_runtime_active.sid-{sid}.*.json"))
    assert len(snapshots) == 1
    assert json.loads(snapshots[0].read_text(encoding="utf-8"))["file"] == path.name


def test_missing_runtime_active_pointer_cleanup_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path / "logs")
    _reset_trace_state()
    trace.finish_desktop_trace_session()
    assert not list((tmp_path / "logs").glob("contextor_runtime_active*.json")) if (tmp_path / "logs").exists() else True


def test_runtime_trace_fixture_never_touches_forbidden_production_like_root(tmp_path, monkeypatch):
    forbidden = tmp_path / "forbidden-production-logs"
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path / "logs")
    path = trace.start_desktop_trace_session()
    emitter = trace.AuthorityEventEmitter(runtime_domain_id="fixture-domain")
    emitter.emit("FIXTURE_ISOLATION")
    assert path.parent == tmp_path / "logs"
    assert (tmp_path / "logs" / trace._POINTER_NAME).exists()
    assert list((tmp_path / "logs").glob("contextor_runtime_*.jsonl"))
    assert (tmp_path / "logs" / "authority_event_state.json").exists()
    assert not forbidden.exists()
