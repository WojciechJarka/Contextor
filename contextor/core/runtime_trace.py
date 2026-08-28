"""Best-effort cross-process JSONL runtime diagnostics.

The trace is deliberately independent from canonical LIVE state and the
existing program log.  Nothing in this module may affect correctness paths.
"""

from __future__ import annotations

import contextlib
import contextvars
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from contextor.core.paths import atomic_write, runtime_logs_dir

TRACE_SCHEMA = "contextor-runtime-trace/v1"
_POINTER_NAME = "contextor_runtime_active.json"
_CHECK_INTERVAL = 0.1
_MAX_TEXT = 500

_lock = threading.RLock()
_active_meta: dict[str, object] | None = None
_active_path: Path | None = None
_active_sid: str | None = None
_last_pointer_check = 0.0
_counter = 0
_operation_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "contextor_trace_operation", default=None
)


def _pointer_path() -> Path:
    return runtime_logs_dir() / _POINTER_NAME


def _now() -> tuple[str, str]:
    current = datetime.now(timezone.utc)
    return current.isoformat(timespec="milliseconds"), current.strftime("%Y%m%d_%H%M%S") + f"_{current.microsecond // 1000:03d}"


def _bounded(value: object) -> object:
    if isinstance(value, str):
        return value[:_MAX_TEXT]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)[:_MAX_TEXT]
    return str(value)[:_MAX_TEXT]


def _read_pointer() -> tuple[dict[str, object], Path] | None:
    try:
        pointer = _pointer_path()
        data = json.loads(pointer.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("schema") != TRACE_SCHEMA:
            return None
        sid = data.get("sid")
        file_name = data.get("file")
        pid = data.get("desktop_pid")
        started = data.get("started_at")
        if not all(isinstance(item, str) and item for item in (sid, file_name, started)):
            return None
        if not isinstance(pid, int):
            return None
        path = (runtime_logs_dir() / file_name).resolve()
        if path.parent != runtime_logs_dir().resolve() or path.suffix != ".jsonl":
            return None
        return data, path
    except Exception:
        return None


def _refresh_pointer(*, force: bool = False) -> Path | None:
    global _active_meta, _active_path, _active_sid, _last_pointer_check
    now = time.monotonic()
    with _lock:
        if not force and now - _last_pointer_check < _CHECK_INTERVAL:
            return _active_path
        _last_pointer_check = now
        resolved = _read_pointer()
        if resolved is None:
            _active_meta = None
            _active_path = None
            _active_sid = None
            return None
        meta, path = resolved
        if meta != _active_meta or path != _active_path:
            _active_meta = meta
            _active_path = path
            _active_sid = str(meta["sid"])
        return _active_path


def active_trace_path(*, force_refresh: bool = False) -> Path | None:
    """Return the currently published trace path, or ``None``."""
    try:
        return _refresh_pointer(force=force_refresh)
    except Exception:
        return None


def _append(record: dict[str, object], path: Path) -> None:
    try:
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        with open(path, "ab", buffering=0) as handle:
            handle.write(payload.encode("utf-8"))
    except Exception:
        pass


def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str) -> list[dict[str, object]]:
    return [
        {"_type": "header", "schema": TRACE_SCHEMA, "purpose": "chronological Contextor Desktop/LIVE/MCP runtime diagnostics; one JSON object per line", "sid": sid, "started_at": started_at, "desktop_pid": desktop_pid, "file": file_name},
        {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
        {"_type": "domains", "domains": ["DESKTOP", "LIVE", "MCP", "GUI"], "reserved": ["OPS"], "ops_note": "Reserved for future repository-operation coordination; not implemented here."},
        {"_type": "revision_semantics", "rev": "observed authoritative canonical revision", "rev0": "authoritative canonical revision before transition", "rev1": "authoritative canonical revision after transition", "seq": "independent activity-journal sequence", "logger_rule": "The logger never calculates or increments canonical revision or activity sequence."},
        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
    ]


def start_desktop_trace_session() -> Path | None:
    """Create and publish one trace for this Desktop lifetime."""
    global _active_meta, _active_path, _active_sid, _last_pointer_check
    try:
        logs = runtime_logs_dir()
        logs.mkdir(parents=True, exist_ok=True)
        started_at, stamp = _now()
        pid = os.getpid()
        sid = f"d-{pid}-{stamp}"
        file_name = f"contextor_runtime_{stamp}_{pid}.jsonl"
        path = logs / file_name
        records = _header_records(sid, started_at, pid, file_name)
        with open(path, "xb", buffering=0) as handle:
            for record in records:
                handle.write((json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
        pointer = {"schema": TRACE_SCHEMA, "sid": sid, "file": file_name, "desktop_pid": pid, "started_at": started_at}
        atomic_write(_pointer_path(), json.dumps(pointer, ensure_ascii=False, separators=(",", ":")))
        with _lock:
            _active_meta, _active_path, _active_sid = pointer, path.resolve(), sid
            _last_pointer_check = time.monotonic()
        trace_event("DESKTOP", "SESSION_START", op=new_trace_operation("d"))
        return path
    except Exception:
        return None


def finish_desktop_trace_session() -> None:
    global _active_meta, _active_path, _active_sid, _last_pointer_check
    try:
        sid = _active_sid
        path = _active_path
        if sid and path:
            trace_event("DESKTOP", "SESSION_END", op=new_trace_operation("d"))
        current = _read_pointer()
        if current is not None and sid and path and current[0].get("sid") == sid and current[1] == path:
            try:
                _pointer_path().unlink()
            except FileNotFoundError:
                pass
        with _lock:
            _active_meta = _active_path = _active_sid = None
            _last_pointer_check = 0.0
    except Exception:
        pass


def new_trace_operation(prefix: str) -> str:
    global _counter
    with _lock:
        _counter += 1
        return f"{prefix}-{os.getpid()}-{_counter}"


def current_trace_operation() -> str | None:
    return _operation_var.get()


@contextlib.contextmanager
def trace_operation(op: str):
    token = _operation_var.set(op)
    try:
        yield op
    finally:
        _operation_var.reset(token)


def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | None = None, rev_before: int | None = None, rev_after: int | None = None, seq: int | None = None, **fields: object) -> None:
    """Best-effort one-line diagnostic append; never raises."""
    try:
        path = active_trace_path()
        if path is None:
            return
        with _lock:
            sid = _active_sid
        if sid is None:
            return
        ts, _ = _now()
        record: dict[str, object] = {"ts": ts, "mono_ms": int(time.monotonic() * 1000), "sid": sid, "pid": os.getpid(), "tid": threading.get_ident(), "d": domain, "ev": event}
        actual_op = op or current_trace_operation()
        if actual_op is not None:
            record["op"] = _bounded(actual_op)
        for key, value in (("rev", rev), ("rev0", rev_before), ("rev1", rev_after), ("seq", seq)):
            if value is not None:
                record[key] = value
        key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq"}
        for key, value in fields.items():
            target = key_map.get(key)
            if target is not None and value is not None:
                record[target] = _bounded(value)
        _append(record, path)
    except Exception:
        pass


__all__ = ["TRACE_SCHEMA", "start_desktop_trace_session", "finish_desktop_trace_session", "active_trace_path", "new_trace_operation", "trace_event", "current_trace_operation", "trace_operation"]
