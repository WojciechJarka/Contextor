FILES_CHANGED=
contextor/core/runtime_trace.py
contextor/core/live_state/runtime_lease.py
contextor/core/live_state/runtime.py
contextor/core/live_state/ipc.py
contextor/core/live_state/watcher.py
contextor/ui/gui.py
tests/test_runtime_authority_events.py

TESTS_RUN=
.\.venv\Scripts\python.exe -m pytest -q tests/test_runtime_authority_events.py tests/test_runtime_trace.py tests/test_live_state_ipc.py tests/test_live_authority_bootstrap.py tests/live_state/test_runtime_lease.py tests/test_live_watcher_startup_reconciliation.py tests/test_gui_live_startup.py tests/test_live_activity_status.py
.\.venv\Scripts\python.exe -m py_compile contextor/core/runtime_trace.py contextor/core/live_state/runtime.py contextor/core/live_state/ipc.py contextor/core/live_state/runtime_lease.py contextor/core/live_state/watcher.py

TEST_RESULTS=
202 passed, 1 warning in 151.11s (0:02:31)
PYTEST_EXIT_CODE=0
PYCOMPILE_EXIT_CODE=0

RUNTIME_RESTART_REQUIRED=YES

ACTUAL_DIFF=
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index f5fccec..32fb532 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -12,8 +12,11 @@ import json
 import os
 import threading
 import time
+import uuid
+from dataclasses import dataclass
 from datetime import datetime, timezone
 from pathlib import Path
+from typing import Any, Callable, Mapping
 
 from contextor.core.paths import atomic_write, runtime_logs_dir
 
@@ -29,11 +32,694 @@ _active_sid: str | None = None
 _active_fd: int | None = None
 _last_pointer_check = 0.0
 _counter = 0
+_AUTHORITY_STATE_NAME = "authority_event_state.json"
+_AUTHORITY_RECOVERY_WINDOW = 1024 * 1024
+_AUTHORITY_PENDING_LIMIT = 10_000
+_authority_emitters: dict[tuple[str, str], "AuthorityEventEmitter"] = {}
+_authority_lock = threading.RLock()
 _operation_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
     "contextor_trace_operation", default=None
 )
 
 
+AUTHORITY_EVENT_SCHEMA = "contextor-authority-event/v1"
+
+
+class AuthorityEventRecoveryError(RuntimeError):
+    """Durable authority-event state cannot be recovered safely."""
+
+
+@dataclass(frozen=True)
+class RecordIndex:
+    sequence: int
+    event_id: str
+    trace_path: str
+    offset: int
+    end_offset: int
+
+
+@dataclass(frozen=True)
+class AuthorityEvent:
+    """The immutable, bounded representation shared by JSONL and LIVE."""
+
+    event_id: str
+    timestamp: str
+    sequence: int
+    event_type: str
+    repo_id: str | None = None
+    runtime_domain_id: str | None = None
+    service_instance_id: str | None = None
+    lease_generation: int | None = None
+    process_id: int | None = None
+    operation_id: str | None = None
+    request_type: str | None = None
+    source: str | None = None
+    queue_order: int | None = None
+    base_revision: int | None = None
+    candidate_revision: int | None = None
+    final_revision: int | None = None
+    state_id: str | None = None
+    decision: str | None = None
+    status: str | None = None
+    reason: str | None = None
+    error: str | None = None
+
+    def to_dict(self) -> dict[str, object]:
+        return {
+            "event_id": self.event_id,
+            "timestamp": self.timestamp,
+            "sequence": self.sequence,
+            "event_type": self.event_type,
+            "repo_id": self.repo_id,
+            "runtime_domain_id": self.runtime_domain_id,
+            "service_instance_id": self.service_instance_id,
+            "lease_generation": self.lease_generation,
+            "process_id": self.process_id,
+            "operation_id": self.operation_id,
+            "request_type": self.request_type,
+            "source": self.source,
+            "queue_order": self.queue_order,
+            "base_revision": self.base_revision,
+            "candidate_revision": self.candidate_revision,
+            "final_revision": self.final_revision,
+            "state_id": self.state_id,
+            "decision": self.decision,
+            "status": self.status,
+            "reason": self.reason,
+            "error": self.error,
+        }
+
+    @classmethod
+    def from_dict(cls, payload: Mapping[str, object]) -> "AuthorityEvent":
+        required = {
+            "event_id", "timestamp", "sequence", "event_type", "repo_id",
+            "runtime_domain_id", "service_instance_id", "lease_generation",
+            "process_id", "operation_id", "request_type", "source", "queue_order",
+            "base_revision", "candidate_revision", "final_revision", "state_id",
+            "decision", "status", "reason", "error",
+        }
+        if set(payload) != required:
+            raise AuthorityEventRecoveryError("authority event fields do not match schema")
+        text_fields = {"event_id", "timestamp", "event_type", "runtime_domain_id", "repo_id", "service_instance_id", "operation_id", "request_type", "source", "state_id", "decision", "status", "reason", "error"}
+        numeric_fields = {"sequence", "lease_generation", "process_id", "queue_order", "base_revision", "candidate_revision", "final_revision"}
+        for field in text_fields:
+            value = payload[field]
+            if value is not None and (not isinstance(value, str) or not value):
+                raise AuthorityEventRecoveryError(f"authority {field} is invalid")
+        for field in numeric_fields:
+            value = payload[field]
+            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
+                raise AuthorityEventRecoveryError(f"authority {field} is invalid")
+        if not isinstance(payload["sequence"], int) or payload["sequence"] < 1:
+            raise AuthorityEventRecoveryError("authority sequence is invalid")
+        for field in {"queue_order", "base_revision", "candidate_revision", "final_revision"}:
+            if payload[field] is not None and payload[field] < 0:
+                raise AuthorityEventRecoveryError(f"authority {field} is invalid")
+        for field in {"lease_generation", "process_id"}:
+            if payload[field] is not None and payload[field] < 1:
+                raise AuthorityEventRecoveryError(f"authority {field} is invalid")
+        if not isinstance(payload["runtime_domain_id"], str) or not payload["runtime_domain_id"]:
+            raise AuthorityEventRecoveryError("authority runtime_domain_id is invalid")
+        return cls(**{key: payload[key] for key in required})  # type: ignore[arg-type]
+
+
+def authority_event_state_path(logs_root: str | Path | None = None) -> Path:
+    """Stable bounded replay metadata location (never a process/session path)."""
+    return (Path(logs_root) if logs_root is not None else runtime_logs_dir()) / _AUTHORITY_STATE_NAME
+
+
+def _authority_default_domain(domain_id: str) -> dict[str, object]:
+    return {
+        "runtime_domain_id": domain_id,
+        "durable_high_water_sequence": 0,
+        "durable_high_water_event_id": None,
+        "durable_high_water_trace_path": None,
+        "durable_high_water_offset": None,
+        "durable_high_water_end_offset": None,
+        "live_handoff_cursor": 0,
+        "live_handoff_epoch": None,
+        "pending_start_sequence": None,
+        "pending_end_sequence": None,
+        "pending_index": [],
+        "delivery_conflicts": [],
+    }
+
+
+def _authority_default_sidecar(trace_path: Path, tail_offset: int) -> dict[str, object]:
+    return {
+        "schema_version": 3,
+        "active_trace_path": str(trace_path),
+        "durable_tail_offset": tail_offset,
+        "domains": {},
+    }
+
+
+def _record_index_from_payload(payload: Mapping[str, object]) -> RecordIndex:
+    required = {"sequence", "event_id", "trace_path", "offset", "end_offset"}
+    if set(payload) != required:
+        raise AuthorityEventRecoveryError("authority pending index fields do not match schema")
+    sequence, event_id, trace_path, offset, end_offset = (payload[key] for key in ("sequence", "event_id", "trace_path", "offset", "end_offset"))
+    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
+        raise AuthorityEventRecoveryError("authority pending sequence is invalid")
+    if not isinstance(event_id, str) or not event_id:
+        raise AuthorityEventRecoveryError("authority pending event_id is invalid")
+    if not isinstance(trace_path, str) or not trace_path:
+        raise AuthorityEventRecoveryError("authority pending trace_path is invalid")
+    if any(isinstance(value, bool) or not isinstance(value, int) for value in (offset, end_offset)) or offset < 0 or end_offset <= offset:
+        raise AuthorityEventRecoveryError("authority pending offsets are invalid")
+    return RecordIndex(sequence, event_id, trace_path, offset, end_offset)
+
+
+def _validated_segment_path(value: str, logs_root: Path) -> Path:
+    path = Path(value).resolve()
+    if path.parent != logs_root.resolve() or path.suffix != ".jsonl":
+        raise AuthorityEventRecoveryError("authority trace segment is foreign")
+    return path
+
+
+def _read_authority_sidecar(path: Path, domain_id: str, logs_root: Path, trace_path: Path) -> tuple[dict[str, object], dict[str, object]]:
+    try:
+        payload = json.loads(path.read_text(encoding="utf-8"))
+    except FileNotFoundError:
+        initial = _authority_default_sidecar(trace_path, trace_path.stat().st_size)
+        return _authority_default_domain(domain_id), initial
+    except (OSError, ValueError, TypeError) as exc:
+        raise AuthorityEventRecoveryError(f"malformed authority sidecar: {path}") from exc
+    if not isinstance(payload, dict):
+        raise AuthorityEventRecoveryError("authority sidecar must be an object")
+    # Upgrade the previous bounded format without resetting any sequence.
+    if payload.get("schema_version") == 2 and set(payload) == {"schema_version", "trace_path", "durable_tail_offset", "domains"}:
+        old_path = payload["trace_path"]
+        if not isinstance(old_path, str) or not old_path:
+            raise AuthorityEventRecoveryError("authority trace_path is invalid")
+        upgraded = _authority_default_sidecar(Path(old_path).resolve(), int(payload["durable_tail_offset"]))
+        upgraded["domains"] = payload["domains"]
+        for domain in upgraded["domains"].values():
+            if isinstance(domain, dict):
+                domain["durable_high_water_trace_path"] = old_path
+                domain["pending_index"] = [dict(item, trace_path=old_path) for item in domain.get("pending_index", []) if isinstance(item, dict)]
+                domain["delivery_conflicts"] = []
+        payload = upgraded
+    if set(payload) != {"schema_version", "active_trace_path", "durable_tail_offset", "domains"} or payload.get("schema_version") != 3:
+        raise AuthorityEventRecoveryError("unsupported authority sidecar schema_version")
+    active = payload.get("active_trace_path")
+    if not isinstance(active, str) or not active:
+        raise AuthorityEventRecoveryError("authority active_trace_path is invalid")
+    active_path = Path(active).resolve()
+    if active_path.parent != logs_root.resolve() or active_path.suffix != ".jsonl":
+        raise AuthorityEventRecoveryError("authority active trace is foreign")
+    current_size = trace_path.stat().st_size
+    tail = payload.get("durable_tail_offset")
+    if isinstance(tail, bool) or not isinstance(tail, int) or tail < 0:
+        raise AuthorityEventRecoveryError("authority durable_tail_offset is invalid")
+    if active_path == trace_path.resolve() and tail > current_size:
+        raise AuthorityEventRecoveryError("authority durable_tail_offset is invalid")
+    domains = payload.get("domains")
+    if not isinstance(domains, dict):
+        raise AuthorityEventRecoveryError("authority sidecar domains is invalid")
+    state = dict(_authority_default_domain(domain_id))
+    if domain_id in domains:
+        if not isinstance(domains[domain_id], dict) or set(domains[domain_id]) != set(state):
+            raise AuthorityEventRecoveryError("authority domain sidecar fields do not match schema")
+        state.update(domains[domain_id])
+    if state.get("runtime_domain_id") != domain_id:
+        raise AuthorityEventRecoveryError("authority sidecar belongs to another runtime domain")
+    for key in ("durable_high_water_sequence", "live_handoff_cursor"):
+        value = state.get(key)
+        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
+            raise AuthorityEventRecoveryError(f"invalid authority sidecar {key}")
+    high = int(state["durable_high_water_sequence"])
+    cursor = int(state["live_handoff_cursor"])
+    if cursor > high:
+        raise AuthorityEventRecoveryError("authority handoff cursor exceeds high-water")
+    high_id = state.get("durable_high_water_event_id")
+    high_path = state.get("durable_high_water_trace_path")
+    high_offset, high_end = state.get("durable_high_water_offset"), state.get("durable_high_water_end_offset")
+    if high == 0:
+        if any(value is not None for value in (high_id, high_path, high_offset, high_end)):
+            raise AuthorityEventRecoveryError("zero authority high-water has identity")
+    else:
+        if not isinstance(high_path, str) or not high_path:
+            raise AuthorityEventRecoveryError("authority high-water trace path is missing")
+        _record_index_from_payload({"sequence": high, "event_id": high_id, "trace_path": high_path, "offset": high_offset, "end_offset": high_end})
+        high_event = _read_authority_record_at(_validated_segment_path(high_path, logs_root), int(high_offset), int(high_end))
+        if high_event.sequence != high or high_event.event_id != high_id or high_event.runtime_domain_id != domain_id:
+            raise AuthorityEventRecoveryError("authority high-water record does not match sidecar")
+    pending_raw = state.get("pending_index")
+    if not isinstance(pending_raw, list) or len(pending_raw) > _AUTHORITY_PENDING_LIMIT:
+        raise AuthorityEventRecoveryError("authority pending index is invalid")
+    pending = [_record_index_from_payload(item) for item in pending_raw if isinstance(item, Mapping)]
+    start, end = state.get("pending_start_sequence"), state.get("pending_end_sequence")
+    if len(pending) != len(pending_raw) or any(a.sequence >= b.sequence for a, b in zip(pending, pending[1:])):
+        raise AuthorityEventRecoveryError("authority pending index ordering is invalid")
+    if (start is None) != (end is None) or (start is None and pending) or (start is not None and (not pending or pending[0].sequence != start or pending[-1].sequence != end or start != cursor + 1 or end > high)):
+        raise AuthorityEventRecoveryError("authority pending range is invalid")
+    for item in pending:
+        event = _read_authority_record_at(_validated_segment_path(item.trace_path, logs_root), item.offset, item.end_offset)
+        if event.sequence != item.sequence or event.event_id != item.event_id or event.runtime_domain_id != domain_id:
+            raise AuthorityEventRecoveryError("observability_recovery_required: pending record does not match sidecar")
+    conflicts = state.get("delivery_conflicts")
+    if not isinstance(conflicts, list) or len(conflicts) > _AUTHORITY_PENDING_LIMIT:
+        raise AuthorityEventRecoveryError("authority delivery conflict metadata is invalid")
+    for marker in conflicts:
+        if not isinstance(marker, Mapping) or set(marker) != {"runtime_domain_id", "sequence", "event_id"}:
+            raise AuthorityEventRecoveryError("authority delivery conflict marker is invalid")
+        if not isinstance(marker["runtime_domain_id"], str) or not marker["runtime_domain_id"] or isinstance(marker["sequence"], bool) or not isinstance(marker["sequence"], int) or marker["sequence"] < 1 or not isinstance(marker["event_id"], str) or not marker["event_id"]:
+            raise AuthorityEventRecoveryError("authority delivery conflict marker is invalid")
+    return state, payload
+
+
+def _write_authority_sidecar(path: Path, domain_id: str, state: Mapping[str, object], existing: Mapping[str, object]) -> None:
+    payload = dict(existing)
+    domains = dict(payload["domains"])
+    domains[domain_id] = dict(state)
+    payload["domains"] = domains
+    path.parent.mkdir(parents=True, exist_ok=True)
+    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
+    try:
+        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
+            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
+            stream.flush()
+            os.fsync(stream.fileno())
+        os.replace(temporary, path)
+        try:
+            directory_fd = os.open(str(path.parent), os.O_RDONLY)
+        except OSError:
+            directory_fd = None
+        if directory_fd is not None:
+            try:
+                os.fsync(directory_fd)
+            finally:
+                os.close(directory_fd)
+    finally:
+        try:
+            temporary.unlink()
+        except FileNotFoundError:
+            pass
+
+
+def _authority_envelope(event: AuthorityEvent) -> dict[str, object]:
+    return {"_type": "authority_event", "schema": AUTHORITY_EVENT_SCHEMA, **event.to_dict()}
+
+
+def _append_authority_record_locked(path: Path, event: AuthorityEvent) -> RecordIndex:
+    line = json.dumps(_authority_envelope(event), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
+    with path.open("ab") as stream:
+        start = stream.tell()
+        stream.write(line.encode("utf-8"))
+        stream.flush()
+        os.fsync(stream.fileno())
+        end = stream.tell()
+    return RecordIndex(event.sequence, event.event_id, str(path.resolve()), start, end)
+
+
+def _read_authority_record_at(path: Path, offset: int, end_offset: int) -> AuthorityEvent:
+    try:
+        size = path.stat().st_size
+        if offset < 0 or end_offset <= offset or end_offset > size:
+            raise AuthorityEventRecoveryError("authority record offsets are invalid")
+        with path.open("rb") as stream:
+            stream.seek(offset)
+            raw = stream.read(end_offset - offset)
+    except FileNotFoundError as exc:
+        raise AuthorityEventRecoveryError("observability_recovery_required: authority trace segment is missing") from exc
+    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
+        raise AuthorityEventRecoveryError("authority record is not one complete JSONL line")
+    try:
+        payload = json.loads(raw.decode("utf-8"))
+    except (UnicodeDecodeError, ValueError, TypeError) as exc:
+        raise AuthorityEventRecoveryError("authority record is malformed") from exc
+    if not isinstance(payload, dict) or payload.get("_type") != "authority_event" or payload.get("schema") != AUTHORITY_EVENT_SCHEMA:
+        raise AuthorityEventRecoveryError("authority record envelope is invalid")
+    event_payload = {key: payload.get(key) for key in AuthorityEvent.__dataclass_fields__}
+    if set(payload) != {"_type", "schema", *AuthorityEvent.__dataclass_fields__}:
+        raise AuthorityEventRecoveryError("authority record has unknown fields")
+    return AuthorityEvent.from_dict(event_payload)
+
+
+class _AuthorityFileLock(contextlib.AbstractContextManager):
+    """Cross-process lock for the bounded sidecar and its JSONL append order."""
+
+    def __init__(self, path: Path, timeout: float = 10.0) -> None:
+        self.path = path
+        self.timeout = timeout
+        self._file = None
+
+    def __enter__(self):
+        self.path.parent.mkdir(parents=True, exist_ok=True)
+        self._file = self.path.open("a+b")
+        if self.path.stat().st_size == 0:
+            self._file.write(b"0")
+            self._file.flush()
+        deadline = time.monotonic() + self.timeout
+        while True:
+            try:
+                self._file.seek(0)
+                if os.name == "nt":
+                    import msvcrt
+
+                    msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
+                else:
+                    import fcntl
+
+                    fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
+                return self
+            except (OSError, BlockingIOError):
+                if time.monotonic() >= deadline:
+                    self._file.close()
+                    self._file = None
+                    raise AuthorityEventRecoveryError("timed out waiting for authority event durability lock")
+                time.sleep(0.01)
+
+    def __exit__(self, exc_type, exc, tb):
+        if self._file is not None:
+            try:
+                self._file.seek(0)
+                if os.name == "nt":
+                    import msvcrt
+
+                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
+                else:
+                    import fcntl
+
+                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
+            except OSError:
+                pass
+            self._file.close()
+            self._file = None
+
+
+
+
+class AuthorityEventEmitter:
+    """Durable-first authority event pipeline with bounded crash recovery."""
+
+    def __init__(
+        self,
+        *,
+        runtime_domain_id: str,
+        repo_id: str | None = None,
+        logs_root: str | Path | None = None,
+        process_id: int | None = None,
+    ) -> None:
+        if not isinstance(runtime_domain_id, str) or not runtime_domain_id:
+            raise ValueError("runtime_domain_id is required")
+        self.runtime_domain_id = runtime_domain_id
+        self.repo_id = repo_id
+        self.logs_root = (Path(logs_root) if logs_root is not None else runtime_logs_dir()).resolve()
+        self.sidecar_path = authority_event_state_path(self.logs_root)
+        self._lock_path = self.sidecar_path.with_name(f".{self.sidecar_path.name}.lock")
+        self.log_path = _ensure_runtime_trace_session().resolve()
+        if self.log_path.parent != self.logs_root or self.log_path.suffix != ".jsonl":
+            raise AuthorityEventRecoveryError("authority trace session is outside runtime logs root")
+        self.live_sink: Callable[[dict[str, object]], object] | None = None
+        self.live_handoff_epoch: str | None = None
+        self.process_id = os.getpid() if process_id is None else process_id
+        self._lock = _authority_lock
+        with self._lock:
+            with _AuthorityFileLock(self._lock_path):
+                self._recover_locked()
+
+    def _recover_locked(self) -> tuple[dict[str, object], dict[str, object]]:
+        sidecar_missing = not self.sidecar_path.exists()
+        state, payload = _read_authority_sidecar(self.sidecar_path, self.runtime_domain_id, self.logs_root, self.log_path)
+        previous = _validated_segment_path(str(payload["active_trace_path"]), self.logs_root)
+        tail = int(payload["durable_tail_offset"])
+        if previous != self.log_path:
+            previous_size = previous.stat().st_size
+            payload = self._recover_unindexed_range_locked(previous, tail, previous_size, payload)
+            payload["active_trace_path"] = str(self.log_path.resolve())
+            payload["durable_tail_offset"] = self.log_path.stat().st_size
+            state = dict(payload["domains"].get(self.runtime_domain_id) or _authority_default_domain(self.runtime_domain_id))
+            _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
+            return state, payload
+        payload = self._recover_unindexed_range_locked(self.log_path, tail, self.log_path.stat().st_size, payload)
+        state = dict(payload["domains"].get(self.runtime_domain_id) or _authority_default_domain(self.runtime_domain_id))
+        if sidecar_missing or int(payload["durable_tail_offset"]) != tail:
+            _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
+        return state, payload
+
+    def _recover_unindexed_range_locked(self, path: Path, start: int, end: int, payload: dict[str, object]) -> dict[str, object]:
+        if end < start:
+            raise AuthorityEventRecoveryError("authority trace shrank below durable tail offset")
+        if end == start:
+            return payload
+        if end - start > _AUTHORITY_RECOVERY_WINDOW:
+            raise AuthorityEventRecoveryError("observability_recovery_required: unindexed trace range exceeds bound")
+        with path.open("rb") as stream:
+            stream.seek(start)
+            chunk = stream.read(end - start)
+        if not chunk.endswith(b"\n"):
+            raise AuthorityEventRecoveryError("observability_recovery_required: truncated unindexed trace range")
+        domains = dict(payload["domains"])
+        tail = start
+        for line in chunk.splitlines(keepends=True):
+            start, end = tail, tail + len(line)
+            tail = end
+            try:
+                raw = json.loads(line.decode("utf-8"))
+            except (UnicodeDecodeError, ValueError, TypeError) as exc:
+                raise AuthorityEventRecoveryError("observability_recovery_required: malformed trace record") from exc
+            if not isinstance(raw, dict):
+                raise AuthorityEventRecoveryError("observability_recovery_required: trace record is not an object")
+            if raw.get("_type") != "authority_event":
+                continue
+            if raw.get("schema") != AUTHORITY_EVENT_SCHEMA:
+                raise AuthorityEventRecoveryError("observability_recovery_required: authority schema mismatch")
+            event = AuthorityEvent.from_dict({key: raw.get(key) for key in AuthorityEvent.__dataclass_fields__})
+            domain = dict(domains.get(event.runtime_domain_id) or _authority_default_domain(event.runtime_domain_id))
+            expected = int(domain["durable_high_water_sequence"]) + 1
+            if event.sequence != expected:
+                raise AuthorityEventRecoveryError("observability_recovery_required: authority sequence discontinuity")
+            index = RecordIndex(event.sequence, event.event_id, str(path.resolve()), start, end)
+            domain.update(durable_high_water_sequence=event.sequence, durable_high_water_event_id=event.event_id, durable_high_water_trace_path=str(path.resolve()), durable_high_water_offset=start, durable_high_water_end_offset=end)
+            pending = list(domain["pending_index"])
+            if len(pending) >= _AUTHORITY_PENDING_LIMIT:
+                raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
+            pending.append(index.__dict__)
+            domain["pending_index"] = pending
+            if domain["pending_start_sequence"] is None:
+                domain["pending_start_sequence"] = int(domain["live_handoff_cursor"]) + 1
+            domain["pending_end_sequence"] = event.sequence
+            if event.event_type == "AUTHORITY_EVENT_DELIVERY_CONFLICT":
+                if not event.operation_id or not isinstance(event.queue_order, int) or event.queue_order < 1:
+                    raise AuthorityEventRecoveryError("authority delivery conflict lacks machine identity")
+                marker = {"runtime_domain_id": event.runtime_domain_id, "sequence": event.queue_order, "event_id": event.operation_id}
+                if marker not in domain["delivery_conflicts"]:
+                    domain["delivery_conflicts"] = list(domain["delivery_conflicts"]) + [marker]
+            domains[event.runtime_domain_id] = domain
+        payload = dict(payload)
+        payload["durable_tail_offset"] = end
+        payload["domains"] = domains
+        return payload
+
+    def _event_from_record(self, record: Mapping[str, object]) -> AuthorityEvent:
+        event_id = uuid.uuid4().hex
+        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
+        sequence = int(record.get("sequence", 0))
+        if sequence <= 0:
+            raise AuthorityEventRecoveryError("invalid authority sequence allocation")
+        values = {key: record.get(key) for key in AuthorityEvent.__dataclass_fields__}
+        values.update(event_id=event_id, timestamp=timestamp, sequence=sequence)
+        if values.get("runtime_domain_id") is None:
+            values["runtime_domain_id"] = self.runtime_domain_id
+        if values.get("repo_id") is None:
+            values["repo_id"] = self.repo_id
+        if values.get("process_id") is None:
+            values["process_id"] = self.process_id
+        values["event_type"] = str(record.get("event_type") or "AUTHORITY_EVENT")
+        if values.get("status") is None:
+            values["status"] = "DURABLE_COMMITTED"
+        return AuthorityEvent(**values)  # type: ignore[arg-type]
+
+    def attach_live_sink(self, sink: Callable[[dict[str, object]], object], *, handoff_epoch: str) -> None:
+        if not callable(sink) or not isinstance(handoff_epoch, str) or not handoff_epoch:
+            raise ValueError("live sink and real activity_epoch are required")
+        self.live_sink = sink
+        self.live_handoff_epoch = handoff_epoch
+
+    def detach_live_sink(self) -> None:
+        self.live_sink = None
+        self.live_handoff_epoch = None
+
+    def _deliver(self, event: AuthorityEvent, state: dict[str, object], payload: dict[str, object]) -> bool:
+        if self.live_sink is None:
+            return False
+        cursor = int(state.get("live_handoff_cursor") or 0)
+        if event.sequence != cursor + 1:
+            # Never acknowledge a later event while an earlier durable event
+            # is still pending; replay must preserve the durable order.
+            return False
+        try:
+            result = self.live_sink(event.to_dict())
+        except Exception:
+            return False
+        if not isinstance(result, Mapping):
+            return False
+        if result.get("conflict"):
+            key = (event.runtime_domain_id or "", event.sequence, event.event_id)
+            known = {
+                (item.get("runtime_domain_id"), item.get("sequence"), item.get("event_id"))
+                for item in state.get("delivery_conflicts", [])
+                if isinstance(item, Mapping)
+            }
+            if key not in known and event.event_type != "AUTHORITY_EVENT_DELIVERY_CONFLICT":
+                state["delivery_conflicts"] = list(state.get("delivery_conflicts", [])) + [{"runtime_domain_id": key[0], "sequence": key[1], "event_id": key[2]}]
+                self._append_delivery_conflict_locked(event, state, payload, key)
+            return False
+        if result.get("accepted") is not True or result.get("activity_epoch") != self.live_handoff_epoch:
+            return False
+        state = dict(state)
+        state["live_handoff_cursor"] = event.sequence
+        state["live_handoff_epoch"] = self.live_handoff_epoch
+        if state.get("pending_end_sequence") is not None and event.sequence >= int(state["pending_end_sequence"]):
+            state["pending_start_sequence"] = None
+            state["pending_end_sequence"] = None
+        else:
+            state["pending_start_sequence"] = event.sequence + 1
+        pending = [item for item in state["pending_index"] if item["sequence"] != event.sequence]
+        state["pending_index"] = pending
+        state["delivery_conflicts"] = [item for item in state.get("delivery_conflicts", []) if item.get("sequence") != event.sequence]
+        if pending:
+            state["pending_start_sequence"] = pending[0]["sequence"]
+            state["pending_end_sequence"] = pending[-1]["sequence"]
+        else:
+            state["pending_start_sequence"] = state["pending_end_sequence"] = None
+        try:
+            _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
+        except Exception:
+            # Durable event and canonical correctness are already committed;
+            # an acknowledgement write failure leaves the event pending for a
+            # later bounded replay and must not abort the authority service.
+            return False
+        return True
+
+    def _append_delivery_conflict_locked(
+        self,
+        conflicted: AuthorityEvent,
+        state: Mapping[str, object],
+        payload: Mapping[str, object],
+        key: tuple[str, int, str],
+    ) -> None:
+        """Persist one diagnostic without recursively attempting LIVE delivery."""
+        sequence = int(state["durable_high_water_sequence"]) + 1
+        event = self._event_from_record(
+            {
+                "event_type": "AUTHORITY_EVENT_DELIVERY_CONFLICT",
+                "sequence": sequence,
+                "source": "runtime_trace",
+                "operation_id": conflicted.event_id,
+                "request_type": "authority_delivery_conflict",
+                "queue_order": conflicted.sequence,
+                "decision": "CONFLICT",
+                "status": "SECONDARY_DELIVERY_PENDING",
+                "reason": f"conflicted event identity={key}",
+            }
+        )
+        index = _append_authority_record_locked(self.log_path, event)
+        updated = dict(state)
+        updated.update(
+            durable_high_water_sequence=sequence,
+            durable_high_water_event_id=event.event_id,
+            durable_high_water_offset=index.offset,
+            durable_high_water_end_offset=index.end_offset,
+            durable_high_water_trace_path=index.trace_path,
+            pending_start_sequence=int(updated.get("live_handoff_cursor") or 0) + 1,
+            pending_end_sequence=sequence,
+        )
+        pending = list(updated["pending_index"])
+        if len(pending) >= _AUTHORITY_PENDING_LIMIT:
+            raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
+        pending.append(index.__dict__)
+        updated["pending_index"] = pending
+        next_payload = dict(payload)
+        next_payload["active_trace_path"] = str(self.log_path.resolve())
+        next_payload["durable_tail_offset"] = index.end_offset
+        _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, updated, next_payload)
+
+    def replay_pending(self) -> int:
+        with self._lock:
+            with _AuthorityFileLock(self._lock_path):
+                return self._replay_pending_locked()
+
+    def _replay_pending_locked(self) -> int:
+        delivered = 0
+        state, payload = self._recover_locked()
+        start = state.get("pending_start_sequence")
+        end = state.get("pending_end_sequence")
+        if not isinstance(start, int) or not isinstance(end, int) or start > end:
+            return 0
+        for item in state["pending_index"]:
+            index = _record_index_from_payload(item)
+            event = _read_authority_record_at(Path(index.trace_path), index.offset, index.end_offset)
+            if self._deliver(event, state, payload):
+                delivered += 1
+                state, payload = self._recover_locked()
+        return delivered
+
+    def emit(self, event_type: str, **fields: object) -> AuthorityEvent:
+        with self._lock:
+            with _AuthorityFileLock(self._lock_path):
+                if self.live_sink is not None:
+                    self._replay_pending_locked()
+                state, payload = self._recover_locked()
+                # A failed secondary delivery never blocks the next durable event.
+                sequence = int(state["durable_high_water_sequence"]) + 1
+                event = self._event_from_record({**fields, "event_type": event_type, "sequence": sequence})
+                index = _append_authority_record_locked(self.log_path, event)
+                state = dict(state)
+                state.update(
+                    durable_high_water_sequence=sequence,
+                    durable_high_water_event_id=event.event_id,
+                    durable_high_water_trace_path=index.trace_path,
+                    durable_high_water_offset=index.offset,
+                    durable_high_water_end_offset=index.end_offset,
+                )
+                cursor = int(state.get("live_handoff_cursor") or 0)
+                if cursor >= sequence:
+                    state["pending_start_sequence"] = None
+                    state["pending_end_sequence"] = None
+                else:
+                    pending_start = state.get("pending_start_sequence")
+                    state["pending_start_sequence"] = sequence if not isinstance(pending_start, int) else min(pending_start, sequence)
+                    state["pending_end_sequence"] = sequence
+                pending = list(state["pending_index"])
+                if len(pending) >= _AUTHORITY_PENDING_LIMIT:
+                    raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
+                pending.append(index.__dict__)
+                state["pending_index"] = pending
+                payload = dict(payload)
+                payload["active_trace_path"] = str(self.log_path.resolve())
+                payload["durable_tail_offset"] = index.end_offset
+                _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
+                self._deliver(event, state, payload)
+                return event
+
+
+def get_authority_event_emitter(
+    runtime_domain_id: str,
+    *,
+    repo_id: str | None = None,
+    logs_root: str | Path | None = None,
+    live_sink: Callable[[dict[str, object]], object] | None = None,
+) -> AuthorityEventEmitter:
+    root = (Path(logs_root) if logs_root is not None else runtime_logs_dir()).resolve()
+    key = (str(root), runtime_domain_id)
+    with _authority_lock:
+        emitter = _authority_emitters.get(key)
+        if emitter is None:
+            emitter = AuthorityEventEmitter(runtime_domain_id=runtime_domain_id, repo_id=repo_id, logs_root=root)
+            _authority_emitters[key] = emitter
+        elif live_sink is not None:
+            raise ValueError("attach_live_sink requires a real activity epoch")
+        return emitter
+
+
+def emit_authority_event(event_type: str, *, runtime_domain_id: str, repo_id: str | None = None, emitter: AuthorityEventEmitter | None = None, **fields: object) -> AuthorityEvent:
+    pipeline = emitter or get_authority_event_emitter(runtime_domain_id, repo_id=repo_id)
+    return pipeline.emit(event_type, repo_id=repo_id, runtime_domain_id=runtime_domain_id, **fields)
+
+
 def _pointer_path() -> Path:
     return runtime_logs_dir() / _POINTER_NAME
 
@@ -144,27 +830,42 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
     ]
 
 
+def _open_runtime_trace_session() -> Path:
+    """Open and publish the sole runtime-trace JSONL session."""
+    global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
+    logs = runtime_logs_dir()
+    logs.mkdir(parents=True, exist_ok=True)
+    started_at, stamp = _now()
+    pid = os.getpid()
+    sid = f"d-{pid}-{stamp}"
+    file_name = f"contextor_runtime_{stamp}_{pid}.jsonl"
+    path = logs / file_name
+    records = _header_records(sid, started_at, pid, file_name)
+    with open(path, "xb", buffering=0) as handle:
+        for record in records:
+            handle.write((json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
+        handle.flush()
+        os.fsync(handle.fileno())
+    pointer = {"schema": TRACE_SCHEMA, "sid": sid, "file": file_name, "desktop_pid": pid, "started_at": started_at}
+    atomic_write(_pointer_path(), json.dumps(pointer, ensure_ascii=False, separators=(",", ":")))
+    with _lock:
+        _active_meta, _active_path, _active_sid = pointer, path.resolve(), sid
+        _active_fd = None
+        _last_pointer_check = time.monotonic()
+    return path.resolve()
+
+
+def _ensure_runtime_trace_session() -> Path:
+    current = active_trace_path(force_refresh=True)
+    if current is not None:
+        return current
+    return _open_runtime_trace_session()
+
+
 def start_desktop_trace_session() -> Path | None:
     """Create and publish one trace for this Desktop lifetime."""
-    global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
     try:
-        logs = runtime_logs_dir()
-        logs.mkdir(parents=True, exist_ok=True)
-        started_at, stamp = _now()
-        pid = os.getpid()
-        sid = f"d-{pid}-{stamp}"
-        file_name = f"contextor_runtime_{stamp}_{pid}.jsonl"
-        path = logs / file_name
-        records = _header_records(sid, started_at, pid, file_name)
-        with open(path, "xb", buffering=0) as handle:
-            for record in records:
-                handle.write((json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
-        pointer = {"schema": TRACE_SCHEMA, "sid": sid, "file": file_name, "desktop_pid": pid, "started_at": started_at}
-        atomic_write(_pointer_path(), json.dumps(pointer, ensure_ascii=False, separators=(",", ":")))
-        with _lock:
-            _active_meta, _active_path, _active_sid = pointer, path.resolve(), sid
-            _active_fd = None
-            _last_pointer_check = time.monotonic()
+        path = _ensure_runtime_trace_session()
         trace_event("DESKTOP", "SESSION_START", op=new_trace_operation("d"))
         return path
     except Exception:
@@ -245,4 +946,20 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
         pass
 
 
-__all__ = ["TRACE_SCHEMA", "start_desktop_trace_session", "finish_desktop_trace_session", "active_trace_path", "new_trace_operation", "trace_event", "current_trace_operation", "trace_operation"]
+__all__ = [
+    "TRACE_SCHEMA",
+    "AUTHORITY_EVENT_SCHEMA",
+    "AuthorityEvent",
+    "AuthorityEventEmitter",
+    "AuthorityEventRecoveryError",
+    "authority_event_state_path",
+    "get_authority_event_emitter",
+    "emit_authority_event",
+    "start_desktop_trace_session",
+    "finish_desktop_trace_session",
+    "active_trace_path",
+    "new_trace_operation",
+    "trace_event",
+    "current_trace_operation",
+    "trace_operation",
+]

diff --git a/contextor/core/live_state/runtime_lease.py b/contextor/core/live_state/runtime_lease.py
index 08672ca..b295cce 100644
--- a/contextor/core/live_state/runtime_lease.py
+++ b/contextor/core/live_state/runtime_lease.py
@@ -837,6 +837,25 @@ class _DomainFileLock(AbstractContextManager["_DomainFileLock"]):
 FailureInjector = Callable[[str], None]
 
 
+class _LeaseEmissionLock(AbstractContextManager):
+    """Release the domain lock before emitting durable observability events."""
+
+    def __init__(self, manager: "RuntimeLeaseManager", inner: _DomainFileLock) -> None:
+        self.manager = manager
+        self.inner = inner
+
+    def __enter__(self):
+        self.inner.__enter__()
+        self.manager._lease_lock_depth += 1
+        return self
+
+    def __exit__(self, exc_type, exc, tb) -> None:
+        self.manager._lease_lock_depth -= 1
+        self.inner.__exit__(exc_type, exc, tb)
+        if self.manager._lease_lock_depth == 0:
+            self.manager._drain_deferred_authority_events()
+
+
 class RuntimeLeaseManager:
     """Acquire, fence, refresh, bind, and release one RuntimeDomain authority."""
 
@@ -851,6 +870,7 @@ class RuntimeLeaseManager:
         lock_timeout: float = 10.0,
         clock: Callable[[], float] = time.time,
         failure_injector: FailureInjector | None = None,
+        authority_event_emitter: Callable[..., object] | None = None,
     ) -> None:
         _validate_domain_input(
             domain,
@@ -865,9 +885,13 @@ class RuntimeLeaseManager:
         self.lock_timeout = lock_timeout
         self.clock = clock
         self.failure_injector = failure_injector
+        self.authority_event_emitter = authority_event_emitter
+        self._lease_lock_depth = 0
+        self._deferred_authority_events: list[tuple[str, dict[str, object]]] = []
+        self._deferred_authority_lock = threading.Lock()
 
-    def _lock(self) -> _DomainFileLock:
-        return _DomainFileLock(domain_lock_path(self.domain), timeout=self.lock_timeout)
+    def _lock(self):
+        return _LeaseEmissionLock(self, _DomainFileLock(domain_lock_path(self.domain), timeout=self.lock_timeout))
 
     def _now(self) -> float:
         return _timestamp(self.clock(), field="clock")
@@ -876,6 +900,36 @@ class RuntimeLeaseManager:
         if self.failure_injector is not None:
             self.failure_injector(point)
 
+    def _emit_authority(self, event_type: str, **fields: object) -> None:
+        if self._lease_lock_depth:
+            with self._deferred_authority_lock:
+                self._deferred_authority_events.append((event_type, dict(fields)))
+            return
+        emitter = self.authority_event_emitter
+        if emitter is None:
+            return
+        try:
+            emitter(
+                event_type,
+                repo_id=self.domain.repo_id,
+                runtime_domain_id=self.domain.domain_id,
+                source="runtime_lease",
+                **fields,
+            )
+        except Exception:
+            # Observability is secondary to the lease correctness contract.
+            return
+
+    def _emit_authority_events(self, events: list[tuple[str, dict[str, object]]]) -> None:
+        for event_type, fields in events:
+            self._emit_authority(event_type, **fields)
+
+    def _drain_deferred_authority_events(self) -> None:
+        with self._deferred_authority_lock:
+            events = self._deferred_authority_events
+            self._deferred_authority_events = []
+        self._emit_authority_events(events)
+
     def read_generation(self) -> AuthorityGenerationRecord:
         with self._lock():
             return self._read_generation()
@@ -1012,6 +1066,15 @@ class RuntimeLeaseManager:
                         "desktop_process_start_identity": desktop_process_identity.process_start_identity,
                     }
                     _atomic_write_json(desktop_claim_path(self.domain), new_claim)
+                    self._emit_authority(
+                        "DESKTOP_CLAIM_ACQUIRE",
+                        service_instance_id=current.service_instance_id,
+                        lease_generation=current.lease_generation,
+                        process_id=desktop_process_identity.pid,
+                        decision="ACQUIRE",
+                        status="ACTIVE",
+                        reason="desktop claim created",
+                    )
                     return new_claim
                 if (
                     claim["service_instance_id"] == current.service_instance_id
@@ -1020,6 +1083,15 @@ class RuntimeLeaseManager:
                     and claim["desktop_pid"] == desktop_process_identity.pid
                     and claim["desktop_process_start_identity"] == desktop_process_identity.process_start_identity
                 ):
+                    self._emit_authority(
+                        "DESKTOP_CLAIM_ACQUIRE",
+                        service_instance_id=current.service_instance_id,
+                        lease_generation=current.lease_generation,
+                        process_id=desktop_process_identity.pid,
+                        decision="IDEMPOTENT",
+                        status="ACTIVE",
+                        reason="desktop claim already owned by requester",
+                    )
                     return claim
                 observed_claim = dict(claim)
                 observed_authority = (
@@ -1035,16 +1107,53 @@ class RuntimeLeaseManager:
             try:
                 _image, creation_time, alive = _process_identity(observed_claim["desktop_pid"])
             except Exception as exc:
+                self._emit_authority(
+                    "DESKTOP_CLAIM_REJECT",
+                    service_instance_id=observed_claim.get("service_instance_id"),
+                    lease_generation=observed_claim.get("lease_generation"),
+                    process_id=observed_claim.get("desktop_pid"),
+                    decision="REJECT_UNKNOWN",
+                    status="UNKNOWN",
+                    reason="desktop claim process identity is unknown",
+                    error=str(exc),
+                )
                 raise LeaseLivenessUnknown("desktop claim process identity is unknown") from exc
             if alive and creation_time is not None and str(creation_time) == observed_claim["desktop_process_start_identity"]:
+                self._emit_authority(
+                    "DESKTOP_CLAIM_REJECT",
+                    service_instance_id=observed_claim.get("service_instance_id"),
+                    lease_generation=observed_claim.get("lease_generation"),
+                    process_id=observed_claim.get("desktop_pid"),
+                    decision="REJECT",
+                    status="LIVE",
+                    reason="desktop claim process is live",
+                )
                 raise DesktopClaimAlreadyHeld("repository already active in another Contextor Desktop")
             if alive and creation_time is None:
+                self._emit_authority(
+                    "DESKTOP_CLAIM_REJECT",
+                    service_instance_id=observed_claim.get("service_instance_id"),
+                    lease_generation=observed_claim.get("lease_generation"),
+                    process_id=observed_claim.get("desktop_pid"),
+                    decision="REJECT_UNKNOWN",
+                    status="UNKNOWN",
+                    reason="desktop claim process start identity is unknown",
+                )
                 raise LeaseLivenessUnknown("desktop claim process start identity is unknown")
             if alive:
                 claim_is_stale = True
             elif alive is False:
                 claim_is_stale = True
             else:
+                self._emit_authority(
+                    "DESKTOP_CLAIM_REJECT",
+                    service_instance_id=observed_claim.get("service_instance_id"),
+                    lease_generation=observed_claim.get("lease_generation"),
+                    process_id=observed_claim.get("desktop_pid"),
+                    decision="REJECT_UNKNOWN",
+                    status="UNKNOWN",
+                    reason="desktop claim process liveness is unknown",
+                )
                 raise LeaseLivenessUnknown("desktop claim process liveness is unknown")
 
             with self._lock():
@@ -1069,7 +1178,22 @@ class RuntimeLeaseManager:
                         desktop_process_start_identity=desktop_process_identity.process_start_identity,
                     )
                     _atomic_write_json(desktop_claim_path(self.domain), replacement)
+                    self._emit_authority(
+                        "DESKTOP_CLAIM_REPLACE",
+                        service_instance_id=current.service_instance_id,
+                        lease_generation=current.lease_generation,
+                        process_id=desktop_process_identity.pid,
+                        decision="REPLACE_STALE",
+                        status="ACTIVE",
+                        reason="previous desktop claim is stale or PID identity mismatched",
+                    )
                     return replacement
+        self._emit_authority(
+            "DESKTOP_CLAIM_REJECT",
+            decision="REJECT_RACE",
+            status="UNKNOWN",
+            reason="desktop claim changed during liveness verification",
+        )
         raise LeaseLivenessUnknown("desktop claim changed during liveness verification")
 
     def release_desktop_claim(
@@ -1098,6 +1222,15 @@ class RuntimeLeaseManager:
                 desktop_claim_path(self.domain).unlink()
             except FileNotFoundError:
                 pass
+            self._emit_authority(
+                "DESKTOP_CLAIM_RELEASE",
+                service_instance_id=current.service_instance_id,
+                lease_generation=current.lease_generation,
+                process_id=desktop_process_identity.pid,
+                decision="RELEASE",
+                status="RELEASED",
+                reason="exact desktop claim owner released",
+            )
 
     def _remove_desktop_claim_if_owner(self, lease: RuntimeLease) -> None:
         try:
@@ -1161,6 +1294,14 @@ class RuntimeLeaseManager:
         self._inject("after_fence_persist")
         self._remove_desktop_claim_if_owner(lease)
         self._remove_live_lease()
+        self._emit_authority(
+            "RUNTIME_LEASE_FENCE",
+            service_instance_id=lease.service_instance_id,
+            lease_generation=lease.lease_generation,
+            decision="FENCE_STALE",
+            status="FENCED",
+            reason="confirmed_stale_authority",
+        )
         return fenced
 
     @staticmethod
@@ -1201,15 +1342,43 @@ class RuntimeLeaseManager:
         active = replace(reserved, status="active", updated_at=self._now())
         self._write_generation(active)
         self._inject("after_generation_activation")
+        self._emit_authority(
+            "RUNTIME_LEASE_RESERVATION",
+            service_instance_id=lease.service_instance_id,
+            lease_generation=lease.lease_generation,
+            decision="ALLOCATE",
+            status="RESERVED",
+            reason="durable_generation_reserved",
+        )
+        self._emit_authority(
+            "RUNTIME_LEASE_ACTIVATION",
+            service_instance_id=lease.service_instance_id,
+            lease_generation=lease.lease_generation,
+            decision="ACTIVATE",
+            status="ACTIVE",
+            reason="durable_generation_active",
+        )
         return lease
 
     def acquire(self) -> RuntimeLease:
+        self._emit_authority(
+            "RUNTIME_LEASE_ACQUIRE",
+            decision="REQUEST",
+            status="REQUESTED",
+            reason="authority lease acquisition requested",
+        )
         while True:
             with self._lock():
                 record = self._read_generation()
                 live = self._read_live_lease()
                 if live is None:
                     if record.status == "active":
+                        self._emit_authority(
+                            "RUNTIME_LEASE_RECOVERY_REQUIRED",
+                            decision="REJECT_TAKEOVER",
+                            status="RECOVERY_REQUIRED",
+                            reason="active durable authority has no live lease",
+                        )
                         raise LeaseRecoveryRequired(
                             "active durable authority has no live lease; recovery is required before takeover"
                         )
@@ -1245,8 +1414,26 @@ class RuntimeLeaseManager:
                 if current_record != observed_record or current_live != observed_live:
                     continue
                 if evidence.status is LivenessStatus.LIVE:
+                    self._emit_authority(
+                        "RUNTIME_LEASE_TAKEOVER_REJECT",
+                        service_instance_id=observed_live.service_instance_id,
+                        lease_generation=observed_live.lease_generation,
+                        process_id=observed_live.service_pid,
+                        decision="REJECT_LIVE",
+                        status="LIVE",
+                        reason=evidence.reason,
+                    )
                     raise LeaseAlreadyHeld(evidence.reason)
                 if not evidence.confirmed_stale:
+                    self._emit_authority(
+                        "RUNTIME_LEASE_TAKEOVER_REJECT",
+                        service_instance_id=observed_live.service_instance_id,
+                        lease_generation=observed_live.lease_generation,
+                        process_id=observed_live.service_pid,
+                        decision="REJECT_AMBIGUOUS",
+                        status=evidence.status.value.upper(),
+                        reason=evidence.reason,
+                    )
                     raise LeaseLivenessUnknown(
                         f"authority takeover rejected: {evidence.status.value}: {evidence.reason}"
                     )
@@ -1289,6 +1476,14 @@ class RuntimeLeaseManager:
             bound = replace(current, endpoint_fingerprint=endpoint)
             self._write_live_lease(bound)
             self._write_generation(replace(record, endpoint_fingerprint=endpoint, updated_at=self._now()))
+            self._emit_authority(
+                "RUNTIME_ENDPOINT_BIND",
+                service_instance_id=current.service_instance_id,
+                lease_generation=current.lease_generation,
+                decision="BIND",
+                status="DURABLE",
+                reason="endpoint fingerprint bound to active lease",
+            )
             return bound
 
     def reconcile_endpoint_binding(self, lease: RuntimeLease, endpoint_fingerprint: str) -> RuntimeLease:
@@ -1309,6 +1504,14 @@ class RuntimeLeaseManager:
                 raise EndpointBindingError("durable generation endpoint binding conflicts")
             if record.endpoint_fingerprint is None:
                 self._write_generation(replace(record, endpoint_fingerprint=endpoint, updated_at=self._now()))
+            self._emit_authority(
+                "RUNTIME_ENDPOINT_RECONCILE",
+                service_instance_id=current.service_instance_id,
+                lease_generation=current.lease_generation,
+                decision="RECONCILE",
+                status="DURABLE",
+                reason="endpoint/live lease parity reconciled",
+            )
             return current
 
     def fence_owner(self, lease: RuntimeLease) -> AuthorityGenerationRecord:
@@ -1336,6 +1539,14 @@ class RuntimeLeaseManager:
                 self._remove_desktop_claim_if_owner(lease)
                 if current is not None:
                     self._remove_live_lease()
+                self._emit_authority(
+                    "RUNTIME_LEASE_FENCE",
+                    service_instance_id=lease.service_instance_id,
+                    lease_generation=lease.lease_generation,
+                    decision="FENCE_ALREADY_RESOLVED",
+                    status=record.status.upper(),
+                    reason="authority generation was already resolved",
+                )
                 return record
             if record.status not in {"reserved", "active"}:
                 raise LeaseNotOwner("authority generation is not fenceable")
@@ -1350,6 +1561,14 @@ class RuntimeLeaseManager:
             self._remove_desktop_claim_if_owner(lease)
             if current is not None:
                 self._remove_live_lease()
+            self._emit_authority(
+                "RUNTIME_LEASE_FENCE",
+                service_instance_id=lease.service_instance_id,
+                lease_generation=lease.lease_generation,
+                decision="FENCE_OWNER",
+                status="FENCED",
+                reason="bootstrap failure fenced exact owner",
+            )
             return fenced
 
     def release(self, lease: RuntimeLease) -> AuthorityGenerationRecord:
@@ -1366,6 +1585,14 @@ class RuntimeLeaseManager:
             self._remove_desktop_claim_if_owner(lease)
             self._inject("before_release_live_remove")
             self._remove_live_lease()
+            self._emit_authority(
+                "RUNTIME_LEASE_RELEASE",
+                service_instance_id=current.service_instance_id,
+                lease_generation=current.lease_generation,
+                decision="RELEASE",
+                status="RELEASED",
+                reason="clean authority shutdown",
+            )
             return fenced
 
 

diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 1a599d8..24619ee 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -260,7 +260,25 @@ def _read_endpoint(repo_path: str | Path, *, strict: bool = False) -> LiveEndpoi
 
 
 def _production_domain(identity) -> RuntimeDomain:
-    return RuntimeDomain.from_identity(identity, mode="production")
+    try:
+        return RuntimeDomain.from_identity(identity, mode="production")
+    except Exception as exc:
+        try:
+            from contextor.core.runtime_trace import emit_authority_event
+
+            emit_authority_event(
+                "RUNTIME_DOMAIN_REJECT",
+                runtime_domain_id=f"repo:{identity.repo_id}",
+                repo_id=identity.repo_id,
+                source="runtime_domain",
+                status="REJECTED",
+                decision="FAIL_CLOSED",
+                reason="production RuntimeDomain admission rejected",
+                error=str(exc),
+            )
+        except Exception:
+            pass
+        raise
 
 
 def _endpoint_matches_domain(endpoint: LiveEndpoint, domain: RuntimeDomain) -> bool:
@@ -985,16 +1003,35 @@ def run_service(
     root = Path(repo_path).expanduser().resolve()
     identity = require_repository_identity(root)
     domain = _production_domain(identity)
-    manager = RuntimeLeaseManager(
-        domain,
-        liveness_verifier=AuthorityLivenessVerifier(domain),
-    )
+    manager = None
     lease = None
     server = None
     published_endpoint = None
     desktop_claim = None
+    authority_emitter = None
     ownership_resolved = False
     try:
+        from contextor.core.runtime_trace import AuthorityEventEmitter, _ensure_runtime_trace_session
+
+        # Authority/domain/lease events must enter the same trace session that
+        # GUI and LIVE later consume, including bootstrap failures.
+        _ensure_runtime_trace_session()
+        authority_emitter = AuthorityEventEmitter(
+            runtime_domain_id=domain.domain_id,
+            repo_id=identity.repo_id,
+        )
+        authority_emitter.emit(
+            "RUNTIME_AUTHORITY_START",
+            source="runtime",
+            status="STARTING",
+            decision="START",
+            reason="authority service bootstrap started",
+        )
+        manager = RuntimeLeaseManager(
+            domain,
+            liveness_verifier=AuthorityLivenessVerifier(domain),
+            authority_event_emitter=authority_emitter.emit,
+        )
         lease = manager.acquire()
         if desktop_instance_id is not None:
             if owner_pid is None or desktop_process_start_identity is None:
@@ -1071,6 +1108,12 @@ def run_service(
                 ProcessIdentity(desktop_pid, desktop_start),
             ),
         )
+        if authority_emitter is not None and hasattr(server, "record_authority_event") and hasattr(server, "activity_epoch"):
+            authority_emitter.attach_live_sink(
+                server.record_authority_event,
+                handoff_epoch=server.activity_epoch,
+            )
+            authority_emitter.replay_pending()
         published_endpoint = _authority_endpoint_from_server(
             server,
             identity,
@@ -1096,14 +1139,16 @@ def run_service(
             or current_record.endpoint_fingerprint != published_endpoint.fingerprint()
         ):
             raise RuntimeError("LIVE endpoint and RuntimeLease identity parity verification failed")
-        _safe_trace_event(
-            "LIVE",
-            "AUTHORITY_READY",
-            repo=str(root),
-            domain_id=domain.domain_id,
-            service_instance_id=lease.service_instance_id,
-            lease_generation=lease.lease_generation,
-        )
+        if authority_emitter is not None:
+            authority_emitter.emit(
+                "RUNTIME_AUTHORITY_READY",
+                source="runtime",
+                service_instance_id=lease.service_instance_id,
+                lease_generation=lease.lease_generation,
+                status="READY",
+                decision="READY",
+                reason="endpoint, lease and authority identity parity verified",
+            )
 
         if owner_pid is not None and owner_pid > 0:
             if sys.platform == "win32":
@@ -1143,16 +1188,24 @@ def run_service(
             ).start()
         server.serve_forever()
     except Exception as exc:
-        _safe_trace_event(
-            "LIVE",
-            "AUTHORITY_BOOTSTRAP_FAIL",
-            repo=str(root),
-            error=str(exc),
-            service_instance_id=getattr(lease, "service_instance_id", None),
-            lease_generation=getattr(lease, "lease_generation", None),
-        )
+        if authority_emitter is not None:
+            try:
+                authority_emitter.emit(
+                    "RUNTIME_AUTHORITY_BOOTSTRAP_FAIL",
+                    source="runtime",
+                    service_instance_id=getattr(lease, "service_instance_id", None),
+                    lease_generation=getattr(lease, "lease_generation", None),
+                    status="FAILED",
+                    decision="FAIL_CLOSED",
+                    reason="authority bootstrap failed",
+                    error=str(exc),
+                )
+            except Exception:
+                pass
         raise
     finally:
+        if authority_emitter is not None:
+            authority_emitter.detach_live_sink()
         if server is not None:
             server.close()
         if lease is not None:
@@ -1160,38 +1213,64 @@ def run_service(
                 try:
                     manager.reconcile_endpoint_binding(lease, published_endpoint.fingerprint())
                 except Exception as exc:
-                    _safe_trace_event(
-                        "LIVE",
-                        "AUTHORITY_BIND_RECONCILE_FAIL",
-                        repo=str(root),
-                        error=str(exc),
-                        service_instance_id=lease.service_instance_id,
-                        lease_generation=lease.lease_generation,
-                    )
+                    if authority_emitter is not None:
+                        authority_emitter.emit(
+                            "RUNTIME_ENDPOINT_RECONCILE_FAIL",
+                            source="runtime",
+                            service_instance_id=lease.service_instance_id,
+                            lease_generation=lease.lease_generation,
+                            status="FAILED",
+                            decision="FAIL_CLOSED",
+                            reason="endpoint reconciliation failed during shutdown",
+                            error=str(exc),
+                        )
             try:
                 manager.release(lease)
                 ownership_resolved = True
             except Exception as exc:
-                _safe_trace_event(
-                    "LIVE",
-                    "AUTHORITY_RELEASE_FAIL",
-                    repo=str(root),
-                    error=str(exc),
-                    service_instance_id=lease.service_instance_id,
-                    lease_generation=lease.lease_generation,
-                )
+                if authority_emitter is not None:
+                    authority_emitter.emit(
+                        "RUNTIME_LEASE_RELEASE_FAIL",
+                        source="runtime",
+                        service_instance_id=lease.service_instance_id,
+                        lease_generation=lease.lease_generation,
+                        status="FAILED",
+                        decision="FENCE_REQUIRED",
+                        reason="clean release failed; fencing required",
+                        error=str(exc),
+                    )
                 try:
                     manager.fence_owner(lease)
                     ownership_resolved = True
                 except Exception as fence_exc:
-                    _safe_trace_event(
-                        "LIVE",
-                        "AUTHORITY_FENCE_FAIL",
-                        repo=str(root),
-                        error=str(fence_exc),
-                        service_instance_id=lease.service_instance_id,
-                        lease_generation=lease.lease_generation,
-                    )
+                    if authority_emitter is not None:
+                        authority_emitter.emit(
+                            "RUNTIME_LEASE_FENCE_FAIL",
+                            source="runtime",
+                            service_instance_id=lease.service_instance_id,
+                            lease_generation=lease.lease_generation,
+                            status="FAILED",
+                            decision="FAIL_CLOSED",
+                            reason="authority fence failed",
+                            error=str(fence_exc),
+                        )
+        if authority_emitter is not None and lease is not None:
+            try:
+                authority_emitter.emit(
+                    "RUNTIME_AUTHORITY_SHUTDOWN",
+                    source="runtime",
+                    service_instance_id=lease.service_instance_id,
+                    lease_generation=lease.lease_generation,
+                    status="STOPPED" if ownership_resolved else "UNRESOLVED",
+                    decision="SHUTDOWN" if ownership_resolved else "FAIL_CLOSED",
+                    reason=(
+                        "authority service shutdown completed"
+                        if ownership_resolved
+                        else "authority shutdown could not resolve exact ownership"
+                    ),
+                )
+            except Exception:
+                pass
         if published_endpoint is not None and ownership_resolved:
             _remove_endpoint_if_exact(root, published_endpoint)
 

diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index dd247c1..579481d 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -3,6 +3,7 @@
 from __future__ import annotations
 
 import copy
+from collections import OrderedDict
 from contextlib import contextmanager
 import hashlib
 import json
@@ -19,6 +20,7 @@ from contextor.core.live_state.runtime_lease import ProcessIdentity
 
 LIVE_PROTOCOL_VERSION = 3
 LIVE_ENDPOINT_SCHEMA_VERSION = 2
+_AUTHORITY_FINGERPRINT_LIMIT = 10_000
 
 
 @dataclass(frozen=True)
@@ -283,6 +285,7 @@ class CanonicalLiveServer:
         self._persister = persister
         self._retention = retention
         self._events: list[dict[str, Any]] = []
+        self._authority_event_fingerprints: OrderedDict[tuple[str, int, str], str] = OrderedDict()
         self._lock = threading.RLock()
         self._stop = threading.Event()
         self._authkey = authkey or secrets.token_bytes(32)
@@ -390,6 +393,61 @@ class CanonicalLiveServer:
         )
         return event
 
+    @property
+    def activity_epoch(self) -> str:
+        return self._activity_epoch
+
+    def record_authority_event(self, event: Mapping[str, Any]) -> dict[str, Any]:
+        """Project one already-durable authority event into the existing LIVE journal.
+
+        The durable emitter owns event identity and ordering.  This method only
+        creates the GUI/MCP projection and is idempotent on the canonical
+        ``(runtime_domain_id, sequence, event_id)`` key.
+        """
+        if not isinstance(event, Mapping):
+            return {"accepted": False, "activity_epoch": self._activity_epoch}
+        event_id = event.get("event_id")
+        domain_id = event.get("runtime_domain_id")
+        sequence = event.get("sequence")
+        if not isinstance(event_id, str) or not event_id:
+            return {"accepted": False, "activity_epoch": self._activity_epoch}
+        if not isinstance(domain_id, str) or not domain_id:
+            return {"accepted": False, "activity_epoch": self._activity_epoch}
+        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
+            return {"accepted": False, "activity_epoch": self._activity_epoch}
+        expected_domain = self._authority_identity.get("runtime_domain_id")
+        if expected_domain is not None and domain_id != expected_domain:
+            return {"accepted": False, "activity_epoch": self._activity_epoch}
+        key = (domain_id, sequence, event_id)
+        fingerprint = hashlib.sha256(json.dumps(dict(event), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
+        with self._lock:
+            existing = self._authority_event_fingerprints.get(key)
+            if existing is not None:
+                if existing == fingerprint:
+                    return {"accepted": True, "duplicate": True, "activity_epoch": self._activity_epoch}
+                return {"accepted": False, "conflict": True, "activity_epoch": self._activity_epoch}
+            self._authority_event_fingerprints[key] = fingerprint
+            self._authority_event_fingerprints.move_to_end(key)
+            if len(self._authority_event_fingerprints) > _AUTHORITY_FINGERPRINT_LIMIT:
+                self._authority_event_fingerprints.popitem(last=False)
+            self._activity_seq += 1
+            projected = dict(event)
+            projected.update(
+                {
+                    "seq": self._activity_seq,
+                    "category": "AUTHORITY",
+                    "operation": str(event.get("event_type") or "AUTHORITY_EVENT"),
+                    "source": event.get("source") or "authority",
+                    "origin": event.get("source") or "authority",
+                    "canonical_revision": event.get("final_revision"),
+                    "revision": self._revision,
+                    "status": event.get("status") or "DURABLE_COMMITTED",
+                }
+            )
+            self._events.append(projected)
+            del self._events[:-self._retention]
+            return {"accepted": True, "duplicate": False, "activity_epoch": self._activity_epoch}
+
     def _claim_identity_matches_request(self, request: Mapping[str, Any]) -> bool:
         for field in (
             "runtime_domain_id",

diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 391621d..4de19ae 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -473,6 +473,7 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
         super().__init__(interval=interval, thread_name="contextor-live-event-feed")
         self._last_seq: int = 0
         self._activity_epoch: str | None = None
+        self._replayed_authority_keys: set[tuple[str, int, str]] = set()
         self._poll_lock = threading.Lock()
         if initial_seq is not None:
             self._last_seq = int(initial_seq)
@@ -497,8 +498,46 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
         except (TypeError, ValueError):
             self.on_status(message)
 
+    def replay_authority_events(self) -> None:
+        """Show bounded durable authority history before advancing the live cursor."""
+        try:
+            response = self.client.get_events(
+                after_seq=0,
+                category="AUTHORITY",
+                limit=None,
+            )
+        except (OSError, EOFError, TimeoutError, ConnectionError):
+            return
+        if response.get("status") != "ok":
+            return
+        for event in response.get("events", []):
+            if not isinstance(event, dict):
+                continue
+            message = self._message(event)
+            if message:
+                self._emit_status(message, event)
+            key = self._authority_key(event)
+            if key is not None:
+                self._replayed_authority_keys.add(key)
+        current_epoch = response.get("activity_epoch")
+        if current_epoch is not None:
+            self._activity_epoch = str(current_epoch)
+
+    @staticmethod
+    def _authority_key(event: dict) -> tuple[str, int, str] | None:
+        domain, sequence, event_id = event.get("runtime_domain_id"), event.get("sequence"), event.get("event_id")
+        if isinstance(domain, str) and isinstance(sequence, int) and isinstance(event_id, str):
+            return domain, sequence, event_id
+        return None
+
     def _message(self, event: dict) -> str | None:
         category = event.get("category", "LIVE_STATE")
+        if category == "AUTHORITY":
+            event_type = str(event.get("event_type") or event.get("operation") or "AUTHORITY_EVENT")
+            status = event.get("status") or "DURABLE_COMMITTED"
+            sequence = event.get("sequence")
+            suffix = f" (event {sequence})" if isinstance(sequence, int) else ""
+            return f"[LIVE] Authority {event_type}: {status}{suffix}"
         if category == "MCP_CALL":
             tool = event.get("tool", "")
             success = event.get("success", True)
@@ -629,12 +668,15 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                     if isinstance(seq, int) and seq <= self._last_seq:
                         continue
 
-                    message = self._message(event)
+                    key = self._authority_key(event) if event.get("category") == "AUTHORITY" else None
+                    message = None if key is not None and key in self._replayed_authority_keys else self._message(event)
                     if message:
                         self._emit_status(message, event)
 
                     if isinstance(seq, int):
                         self._last_seq = seq
+                        if key is not None:
+                            self._replayed_authority_keys.discard(key)
 
                 # No more pages.
                 if not response.get("truncated", False):

diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 4687200..377e0e6 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -979,6 +979,8 @@ class ContextorGUI:
         self.live_event_feed = feed
         watchers[identity.repo_id] = self.live_watcher
         feeds[identity.repo_id] = feed
+        if hasattr(feed, "replay_authority_events"):
+            feed.replay_authority_events()
         self.live_watcher.start()
         feed.start()
 

diff --git a/tests/test_runtime_authority_events.py b/tests/test_runtime_authority_events.py
new file mode 100644
index 0000000..096be9e
--- /dev/null
+++ b/tests/test_runtime_authority_events.py
@@ -0,0 +1,392 @@
+import json
+import os
+
+import pytest
+
+import contextor.core.runtime_trace as trace
+from contextor.core.live_state.ipc import CanonicalLiveServer
+from contextor.core.live_state.runtime_domain import RuntimeDomain
+from contextor.core.live_state.runtime_lease import ProcessIdentity, RuntimeLeaseManager
+
+
+@pytest.fixture
+def trace_logs(tmp_path, monkeypatch):
+    trace.finish_desktop_trace_session()
+    trace._authority_emitters.clear()
+    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: tmp_path)
+    yield tmp_path
+    trace.finish_desktop_trace_session()
+    trace._authority_emitters.clear()
+
+
+def _records(emitter):
+    return [json.loads(line) for line in emitter.log_path.read_text(encoding="utf-8").splitlines()
+            if json.loads(line).get("_type") == "authority_event"]
+
+
+def _state(logs):
+    return json.loads((logs / "authority_event_state.json").read_text(encoding="utf-8"))
+
+
+def _lease_domain(tmp_path):
+    context = tmp_path / "context"
+    return RuntimeDomain.create(
+        repo_id="repo",
+        repo_root=tmp_path / "repo",
+        mode="test",
+        cache_root=context / "cache",
+        logs_root=context / "logs",
+        lock_root=context / "cache" / "runtime",
+        ipc_endpoint_root=context / "cache" / "ipc",
+        test_context_root=context,
+        test_run_id="run",
+        known_production_roots=(tmp_path / "production-cache", tmp_path / "production-logs"),
+    )
+
+
+def test_authority_events_share_runtime_trace_and_have_strict_envelope(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", repo_id="repo", logs_root=trace_logs)
+    first = emitter.emit("RUNTIME_AUTHORITY_START", source="test")
+    second = emitter.emit("RUNTIME_AUTHORITY_READY", source="test")
+    records = _records(emitter)
+    assert emitter.log_path.parent == trace_logs
+    assert (first.sequence, second.sequence) == (1, 2)
+    assert [item["event_id"] for item in records] == [first.event_id, second.event_id]
+    assert all(item["_type"] == "authority_event" and item["schema"] == trace.AUTHORITY_EVENT_SCHEMA for item in records)
+
+
+def test_jsonl_fsync_precedes_sidecar_high_water(trace_logs, monkeypatch):
+    order = []
+    original_fsync, original_write = trace.os.fsync, trace._write_authority_sidecar
+
+    def fsync(fd):
+        order.append("fsync")
+        return original_fsync(fd)
+
+    def write(*args, **kwargs):
+        order.append("sidecar")
+        return original_write(*args, **kwargs)
+
+    monkeypatch.setattr(trace.os, "fsync", fsync)
+    monkeypatch.setattr(trace, "_write_authority_sidecar", write)
+    trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs).emit("TEST")
+    assert order.index("fsync") < order.index("sidecar")
+
+
+def test_crash_after_jsonl_before_sidecar_recovers_same_sequence(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    original = trace._write_authority_sidecar
+    monkeypatch.setattr(trace, "_write_authority_sidecar", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("crash")))
+    with pytest.raises(OSError):
+        emitter.emit("CRASH_POINT")
+    monkeypatch.setattr(trace, "_write_authority_sidecar", original)
+    recovered = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    assert recovered.emit("AFTER_RECOVERY").sequence == 2
+
+
+def test_pending_replay_keeps_identity_and_requires_mapping_ack(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    event = emitter.emit("PENDING")
+    emitter.attach_live_sink(lambda _event: True, handoff_epoch="epoch-a")
+    assert emitter.replay_pending() == 0
+    delivered = []
+    emitter.attach_live_sink(lambda value: delivered.append(value) or {"accepted": True, "activity_epoch": "epoch-a"}, handoff_epoch="epoch-a")
+    assert emitter.replay_pending() == 1
+    assert delivered[0]["event_id"] == event.event_id
+    assert _state(trace_logs)["domains"]["domain-a"]["live_handoff_cursor"] == 1
+
+
+def test_server_duplicate_and_conflicting_identity(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    event = emitter.emit("EVENT")
+    server = CanonicalLiveServer(None, revision=0, authority_identity={"runtime_domain_id": "domain-a"})
+    try:
+        assert server.record_authority_event(event.to_dict())["accepted"] is True
+        assert server.record_authority_event(event.to_dict()) == {"accepted": True, "duplicate": True, "activity_epoch": server.activity_epoch}
+        changed = event.to_dict()
+        changed["status"] = "ALTERED"
+        result = server.record_authority_event(changed)
+        assert result["accepted"] is False and result["conflict"] is True
+    finally:
+        server.close()
+
+
+def test_delivery_conflict_is_durable_once_without_recursive_delivery(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
+    emitter.emit("EVENT")
+    assert [record["event_type"] for record in _records(emitter)] == ["EVENT", "AUTHORITY_EVENT_DELIVERY_CONFLICT"]
+
+
+def test_malformed_or_truncated_unindexed_tail_fails_closed(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("VALID")
+    with emitter.log_path.open("ab") as stream:
+        stream.write(b'{"event_id":"truncated"')
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+
+def test_two_runtime_domains_have_independent_sequences(trace_logs):
+    left = trace.AuthorityEventEmitter(runtime_domain_id="domain-left", logs_root=trace_logs)
+    right = trace.AuthorityEventEmitter(runtime_domain_id="domain-right", logs_root=trace_logs)
+    assert left.emit("LEFT").sequence == 1
+    assert right.emit("RIGHT").sequence == 1
+    assert left.emit("LEFT_AGAIN").sequence == 2
+
+
+def test_runtimelease_emitter_actually_called_after_outer_lock_release(tmp_path):
+    domain = _lease_domain(tmp_path)
+    events = []
+    manager = None
+
+    def callback(event_type, **fields):
+        events.append(event_type)
+        manager.read_generation()
+
+    manager = RuntimeLeaseManager(domain, process_identity=ProcessIdentity(os.getpid(), "test-start"), authority_event_emitter=callback)
+    manager.acquire()
+    assert {"RUNTIME_LEASE_ACQUIRE", "RUNTIME_LEASE_RESERVATION", "RUNTIME_LEASE_ACTIVATION"} <= set(events)
+
+
+def test_runtimelease_bind_release_desktop_events_are_emitted_outside_lock(tmp_path):
+    domain = _lease_domain(tmp_path)
+    events = []
+    manager = RuntimeLeaseManager(domain, process_identity=ProcessIdentity(os.getpid(), "test-start"), authority_event_emitter=lambda event_type, **fields: events.append(event_type))
+    lease = manager.acquire()
+    manager.bind_endpoint(lease, "endpoint")
+    manager.claim_desktop(lease, "desktop", ProcessIdentity(os.getpid(), "desktop-start"))
+    manager.release_desktop_claim(lease, "desktop", ProcessIdentity(os.getpid(), "desktop-start"))
+    manager.release(lease)
+    assert {"RUNTIME_ENDPOINT_BIND", "DESKTOP_CLAIM_ACQUIRE", "DESKTOP_CLAIM_RELEASE", "RUNTIME_LEASE_RELEASE"} <= set(events)
+
+
+def test_trace_session_rollover_preserves_domain_sequence(trace_logs):
+    first = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    event = first.emit("FIRST")
+    old_path = first.log_path
+    trace.finish_desktop_trace_session()
+    second = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    assert second.log_path != old_path
+    assert second.emit("SECOND").sequence == event.sequence + 1
+
+
+def test_pending_event_from_previous_trace_segment_replays_after_rollover(trace_logs):
+    first = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    event = first.emit("PENDING")
+    old_path = first.log_path
+    trace.finish_desktop_trace_session()
+    second = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    delivered = []
+    second.attach_live_sink(lambda value: delivered.append(value) or {"accepted": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
+    assert second.replay_pending() == 1
+    assert delivered[0]["event_id"] == event.event_id and delivered[0]["sequence"] == event.sequence
+    assert delivered[0]["timestamp"] == event.timestamp and old_path.exists()
+
+
+def test_missing_old_pending_segment_fails_closed(trace_logs):
+    first = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    first.emit("PENDING")
+    old_path = first.log_path
+    trace.finish_desktop_trace_session()
+    old_path.unlink()
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+
+def test_quiet_domain_survives_other_domain_beyond_recovery_window(trace_logs, monkeypatch):
+    first = trace.AuthorityEventEmitter(runtime_domain_id="quiet", logs_root=trace_logs)
+    assert first.emit("QUIET").sequence == 1
+    other = trace.AuthorityEventEmitter(runtime_domain_id="busy", logs_root=trace_logs)
+    monkeypatch.setattr(trace, "_AUTHORITY_RECOVERY_WINDOW", 64)
+    for index in range(20):
+        other.emit(f"BUSY_{index}")
+    assert first.emit("QUIET_NEXT").sequence == 2
+
+
+def test_sidecar_cursor_ahead_of_highwater_fails_closed(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("EVENT")
+    sidecar = _state(trace_logs)
+    sidecar["domains"]["domain-a"]["live_handoff_cursor"] = 2
+    (trace_logs / "authority_event_state.json").write_text(json.dumps(sidecar), encoding="utf-8")
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+
+def test_sidecar_broken_pending_range_fails_closed(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("EVENT")
+    sidecar = _state(trace_logs)
+    sidecar["domains"]["domain-a"]["pending_end_sequence"] = None
+    (trace_logs / "authority_event_state.json").write_text(json.dumps(sidecar), encoding="utf-8")
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+
+def test_pending_index_over_limit_fails_closed(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("EVENT")
+    sidecar = _state(trace_logs)
+    sidecar["domains"]["domain-a"]["pending_index"] = sidecar["domains"]["domain-a"]["pending_index"] * 2
+    monkeypatch.setattr(trace, "_AUTHORITY_PENDING_LIMIT", 1)
+    (trace_logs / "authority_event_state.json").write_text(json.dumps(sidecar), encoding="utf-8")
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+
+@pytest.mark.parametrize("ack", [lambda _event: None, lambda _event: True])
+def test_none_or_truthy_nonmapping_sink_does_not_ack(trace_logs, ack):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("EVENT")
+    emitter.attach_live_sink(ack, handoff_epoch="epoch")
+    assert emitter.replay_pending() == 0
+    assert _state(trace_logs)["domains"]["domain-a"]["live_handoff_cursor"] == 0
+
+
+def test_handoff_epoch_mismatch_does_not_ack(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("EVENT")
+    emitter.attach_live_sink(lambda _event: {"accepted": True, "activity_epoch": "foreign"}, handoff_epoch="attached")
+    assert emitter.replay_pending() == 0
+
+
+def test_conflict_dedupe_survives_emitter_restart(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
+    emitter.emit("EVENT")
+    assert [x["event_type"] for x in _records(emitter)].count("AUTHORITY_EVENT_DELIVERY_CONFLICT") == 1
+    restarted = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    restarted.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
+    restarted.replay_pending()
+    assert [x["event_type"] for x in _records(restarted)].count("AUTHORITY_EVENT_DELIVERY_CONFLICT") == 1
+
+
+def test_detached_sink_keeps_shutdown_event_pending(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.attach_live_sink(lambda _event: {"accepted": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
+    emitter.detach_live_sink()
+    emitter.emit("RUNTIME_SHUTDOWN")
+    assert _state(trace_logs)["domains"]["domain-a"]["pending_start_sequence"] == 1
+
+
+def test_pending_shutdown_replays_on_next_server_with_original_identity(trace_logs):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    event = emitter.emit("RUNTIME_SHUTDOWN")
+    received = []
+    restarted = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    restarted.attach_live_sink(lambda value: received.append(value) or {"accepted": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
+    assert restarted.replay_pending() == 1
+    assert received[0]["event_id"] == event.event_id
+
+
+def test_unresolved_shutdown_not_reported_as_stopped():
+    assert "UNRESOLVED" in __import__("contextor.core.live_state.runtime", fromlist=["run_service"]).__dict__.get("run_service").__code__.co_consts
+
+
+def test_crash_after_authority_jsonl_fsync_then_trace_rollover_recovers_old_segment(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.emit("FIRST")
+    original = trace._write_authority_sidecar
+    monkeypatch.setattr(trace, "_write_authority_sidecar", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("crash")))
+    with pytest.raises(OSError):
+        emitter.emit("CRASHED")
+    monkeypatch.setattr(trace, "_write_authority_sidecar", original)
+    old_path = emitter.log_path
+    crashed = _records(emitter)[-1]
+    trace.finish_desktop_trace_session()
+    recovered = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    assert recovered.log_path != old_path
+    assert recovered.emit("THIRD").sequence == 3
+    pending = _state(trace_logs)["domains"]["domain-a"]["pending_index"]
+    assert any(item["event_id"] == crashed["event_id"] and item["sequence"] == 2 and item["trace_path"] == str(old_path) for item in pending)
+
+
+def test_old_segment_unindexed_range_over_recovery_bound_fails_closed(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    original = trace._write_authority_sidecar
+    monkeypatch.setattr(trace, "_write_authority_sidecar", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("crash")))
+    with pytest.raises(OSError):
+        emitter.emit("CRASHED", reason="x" * 500)
+    monkeypatch.setattr(trace, "_write_authority_sidecar", original)
+    trace.finish_desktop_trace_session()
+    monkeypatch.setattr(trace, "_AUTHORITY_RECOVERY_WINDOW", 32)
+    with pytest.raises(trace.AuthorityEventRecoveryError):
+        trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+
+
+def test_authority_duplicate_remains_idempotent_after_projection_evicted():
+    server = CanonicalLiveServer(None, revision=0, retention=2, authority_identity={"runtime_domain_id": "domain-a"})
+    try:
+        event = trace.AuthorityEvent("id", "2026-01-01T00:00:00+00:00", 1, "EVENT", runtime_domain_id="domain-a").to_dict()
+        assert server.record_authority_event(event)["accepted"]
+        for index in range(3):
+            server._record_event("status", {"origin": "desktop", "status": str(index)})
+        assert server.record_authority_event(event)["duplicate"] is True
+    finally:
+        server.close()
+
+
+def test_authority_conflict_detected_after_projection_evicted():
+    server = CanonicalLiveServer(None, revision=0, retention=2, authority_identity={"runtime_domain_id": "domain-a"})
+    try:
+        event = trace.AuthorityEvent("id", "2026-01-01T00:00:00+00:00", 1, "EVENT", runtime_domain_id="domain-a").to_dict()
+        server.record_authority_event(event)
+        for index in range(3):
+            server._record_event("status", {"origin": "desktop", "status": str(index)})
+        event["status"] = "changed"
+        assert server.record_authority_event(event)["conflict"] is True
+    finally:
+        server.close()
+
+
+def test_conflict_jsonl_fsync_crash_before_sidecar_dedupe_survives_restart(trace_logs, monkeypatch):
+    emitter = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    emitter.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
+    original, calls = trace._write_authority_sidecar, 0
+    def crash_after_primary(*args, **kwargs):
+        nonlocal calls
+        calls += 1
+        if calls == 2:
+            raise OSError("crash")
+        return original(*args, **kwargs)
+    monkeypatch.setattr(trace, "_write_authority_sidecar", crash_after_primary)
+    with pytest.raises(OSError):
+        emitter.emit("EVENT")
+    monkeypatch.setattr(trace, "_write_authority_sidecar", original)
+    restarted = trace.AuthorityEventEmitter(runtime_domain_id="domain-a", logs_root=trace_logs)
+    restarted.attach_live_sink(lambda _event: {"accepted": False, "conflict": True, "activity_epoch": "epoch"}, handoff_epoch="epoch")
+    restarted.replay_pending()
+    assert [x["event_type"] for x in _records(restarted)].count("AUTHORITY_EVENT_DELIVERY_CONFLICT") == 1
+
+
+def test_authority_startup_replay_does_not_skip_live_or_mcp_events():
+    from contextor.core.live_state.watcher import DesktopLiveEventFeed
+    events = [
+        {"seq": 1, "category": "LIVE_STATE", "operation": "update_file", "origin": "desktop", "file_path": "a.py"},
+        {"seq": 2, "category": "AUTHORITY", "runtime_domain_id": "d", "sequence": 1, "event_id": "a", "event_type": "AUTH", "status": "OK"},
+        {"seq": 3, "category": "MCP_CALL", "tool": "x", "success": True},
+        {"seq": 4, "category": "AUTHORITY", "runtime_domain_id": "d", "sequence": 2, "event_id": "b", "event_type": "AUTH", "status": "OK"},
+    ]
+    class Client:
+        def get_events(self, **kwargs):
+            chosen = [e for e in events if kwargs.get("category") is None or e["category"] == kwargs["category"]]
+            return {"status": "ok", "events": chosen, "latest_seq": 4, "activity_epoch": "epoch", "truncated": False}
+    shown = []
+    feed = DesktopLiveEventFeed(Client(), lambda message, **kwargs: shown.append(message), initial_seq=0)
+    feed.replay_authority_events()
+    assert feed._last_seq == 0
+    feed.poll_once()
+    assert feed._last_seq == 4
+    assert len([x for x in shown if "Authority" in x]) == 2
+    assert any("MCP" in x for x in shown) and any("Watcher updated" in x for x in shown)
+
+
+def test_filtered_get_events_latest_seq_is_never_used_as_feed_cursor():
+    from contextor.core.live_state.watcher import DesktopLiveEventFeed
+    class Client:
+        def get_events(self, **kwargs):
+            return {"status": "ok", "events": [], "latest_seq": 99, "activity_epoch": "epoch", "truncated": False}
+    feed = DesktopLiveEventFeed(Client(), lambda *_args, **_kwargs: None, initial_seq=7)
+    feed.replay_authority_events()
+    assert feed._last_seq == 7

