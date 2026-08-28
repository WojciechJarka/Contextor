import json
import multiprocessing
import os
from pathlib import Path

import contextor.core.runtime_trace as trace


def _reset_trace_state():
    trace.finish_desktop_trace_session()
    trace._active_meta = None
    trace._active_path = None
    trace._active_sid = None
    trace._last_pointer_check = 0.0


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
