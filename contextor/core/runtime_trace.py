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
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from contextor.core.paths import atomic_write, runtime_logs_dir

TRACE_SCHEMA = "contextor-runtime-trace/v1"
_POINTER_NAME = "contextor_runtime_active.json"
_CHECK_INTERVAL = 0.1
_MAX_TEXT = 500

_lock = threading.RLock()
_active_meta: dict[str, object] | None = None
_active_path: Path | None = None
_active_sid: str | None = None
_active_fd: int | None = None
_last_pointer_check = 0.0
_counter = 0
_AUTHORITY_STATE_NAME = "authority_event_state.json"
_AUTHORITY_RECOVERY_WINDOW = 1024 * 1024
_AUTHORITY_APPEND_LOCATE_WINDOW = 1024 * 1024
_AUTHORITY_PENDING_LIMIT = 10_000
_authority_emitters: dict[tuple[str, str], "AuthorityEventEmitter"] = {}
_authority_lock = threading.RLock()
_operation_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "contextor_trace_operation", default=None
)


AUTHORITY_EVENT_SCHEMA = "contextor-authority-event/v1"


class AuthorityEventRecoveryError(RuntimeError):
    """Durable authority-event state cannot be recovered safely."""


@dataclass(frozen=True)
class RecordIndex:
    sequence: int
    event_id: str
    trace_path: str
    offset: int
    end_offset: int


@dataclass(frozen=True)
class AuthorityEvent:
    """The immutable, bounded representation shared by JSONL and LIVE."""

    event_id: str
    timestamp: str
    sequence: int
    event_type: str
    repo_id: str | None = None
    runtime_domain_id: str | None = None
    service_instance_id: str | None = None
    lease_generation: int | None = None
    process_id: int | None = None
    operation_id: str | None = None
    request_type: str | None = None
    source: str | None = None
    queue_order: int | None = None
    base_revision: int | None = None
    candidate_revision: int | None = None
    final_revision: int | None = None
    state_id: str | None = None
    decision: str | None = None
    status: str | None = None
    reason: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "repo_id": self.repo_id,
            "runtime_domain_id": self.runtime_domain_id,
            "service_instance_id": self.service_instance_id,
            "lease_generation": self.lease_generation,
            "process_id": self.process_id,
            "operation_id": self.operation_id,
            "request_type": self.request_type,
            "source": self.source,
            "queue_order": self.queue_order,
            "base_revision": self.base_revision,
            "candidate_revision": self.candidate_revision,
            "final_revision": self.final_revision,
            "state_id": self.state_id,
            "decision": self.decision,
            "status": self.status,
            "reason": self.reason,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "AuthorityEvent":
        required = {
            "event_id", "timestamp", "sequence", "event_type", "repo_id",
            "runtime_domain_id", "service_instance_id", "lease_generation",
            "process_id", "operation_id", "request_type", "source", "queue_order",
            "base_revision", "candidate_revision", "final_revision", "state_id",
            "decision", "status", "reason", "error",
        }
        if set(payload) != required:
            raise AuthorityEventRecoveryError("authority event fields do not match schema")
        text_fields = {"event_id", "timestamp", "event_type", "runtime_domain_id", "repo_id", "service_instance_id", "operation_id", "request_type", "source", "state_id", "decision", "status", "reason", "error"}
        numeric_fields = {"sequence", "lease_generation", "process_id", "queue_order", "base_revision", "candidate_revision", "final_revision"}
        for field in text_fields:
            value = payload[field]
            if value is not None and (not isinstance(value, str) or not value):
                raise AuthorityEventRecoveryError(f"authority {field} is invalid")
        for field in numeric_fields:
            value = payload[field]
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise AuthorityEventRecoveryError(f"authority {field} is invalid")
        if not isinstance(payload["sequence"], int) or payload["sequence"] < 1:
            raise AuthorityEventRecoveryError("authority sequence is invalid")
        for field in {"queue_order", "base_revision", "candidate_revision", "final_revision"}:
            if payload[field] is not None and payload[field] < 0:
                raise AuthorityEventRecoveryError(f"authority {field} is invalid")
        for field in {"lease_generation", "process_id"}:
            if payload[field] is not None and payload[field] < 1:
                raise AuthorityEventRecoveryError(f"authority {field} is invalid")
        if not isinstance(payload["runtime_domain_id"], str) or not payload["runtime_domain_id"]:
            raise AuthorityEventRecoveryError("authority runtime_domain_id is invalid")
        return cls(**{key: payload[key] for key in required})  # type: ignore[arg-type]


def authority_event_state_path(logs_root: str | Path | None = None) -> Path:
    """Stable bounded replay metadata location (never a process/session path)."""
    return (Path(logs_root) if logs_root is not None else runtime_logs_dir()) / _AUTHORITY_STATE_NAME


def _authority_default_domain(domain_id: str) -> dict[str, object]:
    return {
        "runtime_domain_id": domain_id,
        "durable_high_water_sequence": 0,
        "durable_high_water_event_id": None,
        "durable_high_water_trace_path": None,
        "durable_high_water_offset": None,
        "durable_high_water_end_offset": None,
        "live_handoff_cursor": 0,
        "live_handoff_epoch": None,
        "pending_start_sequence": None,
        "pending_end_sequence": None,
        "pending_index": [],
        "delivery_conflicts": [],
    }


def _authority_default_sidecar(trace_path: Path, tail_offset: int) -> dict[str, object]:
    return {
        "schema_version": 3,
        "active_trace_path": str(trace_path),
        "durable_tail_offset": tail_offset,
        "domains": {},
    }


def _record_index_from_payload(payload: Mapping[str, object]) -> RecordIndex:
    required = {"sequence", "event_id", "trace_path", "offset", "end_offset"}
    if set(payload) != required:
        raise AuthorityEventRecoveryError("authority pending index fields do not match schema")
    sequence, event_id, trace_path, offset, end_offset = (payload[key] for key in ("sequence", "event_id", "trace_path", "offset", "end_offset"))
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise AuthorityEventRecoveryError("authority pending sequence is invalid")
    if not isinstance(event_id, str) or not event_id:
        raise AuthorityEventRecoveryError("authority pending event_id is invalid")
    if not isinstance(trace_path, str) or not trace_path:
        raise AuthorityEventRecoveryError("authority pending trace_path is invalid")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (offset, end_offset)) or offset < 0 or end_offset <= offset:
        raise AuthorityEventRecoveryError("authority pending offsets are invalid")
    return RecordIndex(sequence, event_id, trace_path, offset, end_offset)


def _validate_authority_domain_state(
    owner_domain_id: str,
    raw_state: Mapping[str, object],
    *,
    logs_root: Path,
) -> dict[str, object]:
    expected_keys = set(_authority_default_domain(owner_domain_id))
    if set(raw_state) != expected_keys:
        raise AuthorityEventRecoveryError("authority domain sidecar fields do not match schema")

    state = dict(raw_state)
    if state.get("runtime_domain_id") != owner_domain_id:
        raise AuthorityEventRecoveryError("authority domain identity does not match sidecar key")

    high = state.get("durable_high_water_sequence")
    cursor = state.get("live_handoff_cursor")
    if (
        isinstance(high, bool) or not isinstance(high, int) or high < 0
        or isinstance(cursor, bool) or not isinstance(cursor, int)
        or cursor < 0 or cursor > high
    ):
        raise AuthorityEventRecoveryError("authority high-water/cursor is invalid")

    high_id = state.get("durable_high_water_event_id")
    high_path = state.get("durable_high_water_trace_path")
    high_offset = state.get("durable_high_water_offset")
    high_end = state.get("durable_high_water_end_offset")
    if high == 0:
        if any(value is not None for value in (high_id, high_path, high_offset, high_end)):
            raise AuthorityEventRecoveryError("zero authority high-water has identity")
    else:
        index = _record_index_from_payload({"sequence": high, "event_id": high_id, "trace_path": high_path, "offset": high_offset, "end_offset": high_end})
        event = _read_authority_record_at(_validated_segment_path(index.trace_path, logs_root), index.offset, index.end_offset)
        if event.runtime_domain_id != owner_domain_id or event.sequence != high or event.event_id != high_id:
            raise AuthorityEventRecoveryError("authority high-water record does not match sidecar")

    pending_raw = state.get("pending_index")
    if not isinstance(pending_raw, list) or len(pending_raw) > _AUTHORITY_PENDING_LIMIT:
        raise AuthorityEventRecoveryError("authority pending index is invalid")
    pending: list[RecordIndex] = []
    for raw in pending_raw:
        if not isinstance(raw, Mapping):
            raise AuthorityEventRecoveryError("authority pending index entry is invalid")
        pending.append(_record_index_from_payload(raw))

    start, end = state.get("pending_start_sequence"), state.get("pending_end_sequence")
    if (start is None) != (end is None):
        raise AuthorityEventRecoveryError("authority pending range is incomplete")
    if not pending:
        if start is not None or end is not None:
            raise AuthorityEventRecoveryError("authority empty pending index has range")
    else:
        expected_sequences = list(range(cursor + 1, high + 1))
        actual_sequences = [item.sequence for item in pending]
        if actual_sequences != expected_sequences or start != expected_sequences[0] or end != expected_sequences[-1]:
            raise AuthorityEventRecoveryError("authority pending index contains a sequence hole")
        for item in pending:
            event = _read_authority_record_at(_validated_segment_path(item.trace_path, logs_root), item.offset, item.end_offset)
            if event.runtime_domain_id != owner_domain_id or event.sequence != item.sequence or event.event_id != item.event_id:
                raise AuthorityEventRecoveryError("authority pending record does not match sidecar")

    conflicts = state.get("delivery_conflicts")
    if not isinstance(conflicts, list) or len(conflicts) > _AUTHORITY_PENDING_LIMIT:
        raise AuthorityEventRecoveryError("authority delivery conflict metadata is invalid")
    pending_identities = {(owner_domain_id, item.sequence, item.event_id) for item in pending}
    for marker in conflicts:
        if not isinstance(marker, Mapping) or set(marker) != {"runtime_domain_id", "sequence", "event_id"}:
            raise AuthorityEventRecoveryError("authority delivery conflict marker is invalid")
        marker_domain, marker_sequence, marker_event_id = marker.get("runtime_domain_id"), marker.get("sequence"), marker.get("event_id")
        if (
            marker_domain != owner_domain_id or isinstance(marker_sequence, bool)
            or not isinstance(marker_sequence, int) or marker_sequence < 1
            or not isinstance(marker_event_id, str) or not marker_event_id
            or (owner_domain_id, marker_sequence, marker_event_id) not in pending_identities
        ):
            raise AuthorityEventRecoveryError("authority delivery conflict marker does not match pending event")
    return state


def _validated_segment_path(value: str, logs_root: Path) -> Path:
    path = Path(value).resolve()
    if path.parent != logs_root.resolve() or path.suffix != ".jsonl":
        raise AuthorityEventRecoveryError("authority trace segment is foreign")
    return path


def _read_authority_sidecar(path: Path, domain_id: str, logs_root: Path, trace_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        initial = _authority_default_sidecar(trace_path, trace_path.stat().st_size)
        return _authority_default_domain(domain_id), initial
    except (OSError, ValueError, TypeError) as exc:
        raise AuthorityEventRecoveryError(f"malformed authority sidecar: {path}") from exc
    if not isinstance(payload, dict):
        raise AuthorityEventRecoveryError("authority sidecar must be an object")
    # Upgrade the previous bounded format without resetting any sequence.
    if payload.get("schema_version") == 2 and set(payload) == {"schema_version", "trace_path", "durable_tail_offset", "domains"}:
        old_path = payload["trace_path"]
        if not isinstance(old_path, str) or not old_path:
            raise AuthorityEventRecoveryError("authority trace_path is invalid")
        upgraded = _authority_default_sidecar(Path(old_path).resolve(), int(payload["durable_tail_offset"]))
        upgraded["domains"] = payload["domains"]
        for domain in upgraded["domains"].values():
            if isinstance(domain, dict):
                high = domain.get("durable_high_water_sequence")
                if isinstance(high, bool) or not isinstance(high, int) or high < 0:
                    raise AuthorityEventRecoveryError("schema2 authority high-water is invalid")
                domain["durable_high_water_trace_path"] = old_path if high > 0 else None
                domain["pending_index"] = [dict(item, trace_path=old_path) for item in domain.get("pending_index", []) if isinstance(item, dict)]
                domain["delivery_conflicts"] = []
        payload = upgraded
    if set(payload) != {"schema_version", "active_trace_path", "durable_tail_offset", "domains"} or payload.get("schema_version") != 3:
        raise AuthorityEventRecoveryError("unsupported authority sidecar schema_version")
    active = payload.get("active_trace_path")
    if not isinstance(active, str) or not active:
        raise AuthorityEventRecoveryError("authority active_trace_path is invalid")
    active_path = Path(active).resolve()
    if active_path.parent != logs_root.resolve() or active_path.suffix != ".jsonl":
        raise AuthorityEventRecoveryError("authority active trace is foreign")
    current_size = trace_path.stat().st_size
    tail = payload.get("durable_tail_offset")
    if isinstance(tail, bool) or not isinstance(tail, int) or tail < 0:
        raise AuthorityEventRecoveryError("authority durable_tail_offset is invalid")
    if active_path == trace_path.resolve() and tail > current_size:
        raise AuthorityEventRecoveryError("authority durable_tail_offset is invalid")
    domains = payload.get("domains")
    if not isinstance(domains, dict):
        raise AuthorityEventRecoveryError("authority sidecar domains is invalid")
    validated_domains: dict[str, object] = {}
    for owner_domain_id, raw_domain in domains.items():
        if not isinstance(owner_domain_id, str) or not owner_domain_id:
            raise AuthorityEventRecoveryError("authority sidecar domain key is invalid")
        if not isinstance(raw_domain, Mapping):
            raise AuthorityEventRecoveryError("authority domain sidecar is invalid")
        validated_domains[owner_domain_id] = _validate_authority_domain_state(owner_domain_id, raw_domain, logs_root=logs_root)
    payload = dict(payload)
    payload["domains"] = validated_domains
    state = dict(validated_domains.get(domain_id) or _authority_default_domain(domain_id))
    return state, payload


def _write_authority_sidecar(path: Path, domain_id: str, state: Mapping[str, object], existing: Mapping[str, object]) -> None:
    payload = dict(existing)
    domains = dict(payload["domains"])
    domains[domain_id] = dict(state)
    payload["domains"] = domains
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        try:
            directory_fd = os.open(str(path.parent), os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _authority_envelope(event: AuthorityEvent) -> dict[str, object]:
    return {"_type": "authority_event", "schema": AUTHORITY_EVENT_SCHEMA, **event.to_dict()}


def _append_authority_record_locked(path: Path, event: AuthorityEvent) -> RecordIndex:
    data = (
        json.dumps(
            _authority_envelope(event),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    fd = os.open(
        str(path),
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        before = os.fstat(fd).st_size
        written = os.write(fd, data)
        if written != len(data):
            raise AuthorityEventRecoveryError("short authority JSONL append")
        os.fsync(fd)
        end = os.fstat(fd).st_size
    finally:
        os.close(fd)
    if end < before + written:
        raise AuthorityEventRecoveryError("authority JSONL append size is inconsistent")
    span = end - before
    if span > max(_AUTHORITY_APPEND_LOCATE_WINDOW, written):
        raise AuthorityEventRecoveryError(
            "authority append location exceeds bounded interleaving window"
        )
    with path.open("rb") as stream:
        stream.seek(before)
        window = stream.read(span)
    relative = window.find(data)
    if relative < 0:
        raise AuthorityEventRecoveryError("authority JSONL append cannot be located exactly")
    if window.find(data, relative + 1) >= 0:
        raise AuthorityEventRecoveryError("authority JSONL append identity is ambiguous")
    start = before + relative
    end = start + written
    recovered = _read_authority_record_at(path, start, end)
    if recovered.event_id != event.event_id or recovered.sequence != event.sequence or recovered.runtime_domain_id != event.runtime_domain_id:
        raise AuthorityEventRecoveryError("authority JSONL append identity verification failed")
    return RecordIndex(event.sequence, event.event_id, str(path.resolve()), start, end)


def _read_authority_record_at(path: Path, offset: int, end_offset: int) -> AuthorityEvent:
    try:
        size = path.stat().st_size
        if offset < 0 or end_offset <= offset or end_offset > size:
            raise AuthorityEventRecoveryError("authority record offsets are invalid")
        with path.open("rb") as stream:
            stream.seek(offset)
            raw = stream.read(end_offset - offset)
    except FileNotFoundError as exc:
        raise AuthorityEventRecoveryError("observability_recovery_required: authority trace segment is missing") from exc
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise AuthorityEventRecoveryError("authority record is not one complete JSONL line")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise AuthorityEventRecoveryError("authority record is malformed") from exc
    if not isinstance(payload, dict) or payload.get("_type") != "authority_event" or payload.get("schema") != AUTHORITY_EVENT_SCHEMA:
        raise AuthorityEventRecoveryError("authority record envelope is invalid")
    event_payload = {key: payload.get(key) for key in AuthorityEvent.__dataclass_fields__}
    if set(payload) != {"_type", "schema", *AuthorityEvent.__dataclass_fields__}:
        raise AuthorityEventRecoveryError("authority record has unknown fields")
    return AuthorityEvent.from_dict(event_payload)


class _AuthorityFileLock(contextlib.AbstractContextManager):
    """Cross-process lock for the bounded sidecar and its JSONL append order."""

    def __init__(self, path: Path, timeout: float = 10.0) -> None:
        self.path = path
        self.timeout = timeout
        self._file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self._file.write(b"0")
            self._file.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self._file.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    self._file.close()
                    self._file = None
                    raise AuthorityEventRecoveryError("timed out waiting for authority event durability lock")
                time.sleep(0.01)

    def __exit__(self, exc_type, exc, tb):
        if self._file is not None:
            try:
                self._file.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self._file.close()
            self._file = None




class AuthorityEventEmitter:
    """Durable-first authority event pipeline with bounded crash recovery."""

    def __init__(
        self,
        *,
        runtime_domain_id: str,
        repo_id: str | None = None,
        logs_root: str | Path | None = None,
        process_id: int | None = None,
    ) -> None:
        if not isinstance(runtime_domain_id, str) or not runtime_domain_id:
            raise ValueError("runtime_domain_id is required")
        self.runtime_domain_id = runtime_domain_id
        self.repo_id = repo_id
        self.logs_root = (Path(logs_root) if logs_root is not None else runtime_logs_dir()).resolve()
        self.sidecar_path = authority_event_state_path(self.logs_root)
        self._lock_path = self.sidecar_path.with_name(f".{self.sidecar_path.name}.lock")
        self.log_path = _ensure_runtime_trace_session(logs_root=self.logs_root).resolve()
        if self.log_path.parent != self.logs_root or self.log_path.suffix != ".jsonl":
            raise AuthorityEventRecoveryError("authority trace session is outside runtime logs root")
        self.live_sink: Callable[[dict[str, object]], object] | None = None
        self.live_handoff_epoch: str | None = None
        self.process_id = os.getpid() if process_id is None else process_id
        self._lock = _authority_lock
        with self._lock:
            with _AuthorityFileLock(self._lock_path):
                self._recover_locked()

    def _recover_locked(self) -> tuple[dict[str, object], dict[str, object]]:
        sidecar_missing = not self.sidecar_path.exists()
        state, payload = _read_authority_sidecar(self.sidecar_path, self.runtime_domain_id, self.logs_root, self.log_path)
        previous = _validated_segment_path(str(payload["active_trace_path"]), self.logs_root)
        tail = int(payload["durable_tail_offset"])
        if previous != self.log_path:
            try:
                previous_size = previous.stat().st_size
            except FileNotFoundError as exc:
                raise AuthorityEventRecoveryError(
                    "observability_recovery_required: authority trace segment is missing"
                ) from exc
            payload = self._recover_unindexed_range_locked(previous, tail, previous_size, payload)
            payload["active_trace_path"] = str(self.log_path.resolve())
            payload["durable_tail_offset"] = self.log_path.stat().st_size
            state = dict(payload["domains"].get(self.runtime_domain_id) or _authority_default_domain(self.runtime_domain_id))
            _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
            return state, payload
        payload = self._recover_unindexed_range_locked(self.log_path, tail, self.log_path.stat().st_size, payload)
        state = dict(payload["domains"].get(self.runtime_domain_id) or _authority_default_domain(self.runtime_domain_id))
        if sidecar_missing or int(payload["durable_tail_offset"]) != tail:
            _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
        return state, payload

    def _recover_unindexed_range_locked(self, path: Path, start: int, end: int, payload: dict[str, object]) -> dict[str, object]:
        if end < start:
            raise AuthorityEventRecoveryError("authority trace shrank below durable tail offset")
        if end == start:
            return payload
        if end - start > _AUTHORITY_RECOVERY_WINDOW:
            raise AuthorityEventRecoveryError("observability_recovery_required: unindexed trace range exceeds bound")
        with path.open("rb") as stream:
            stream.seek(start)
            chunk = stream.read(end - start)
        if not chunk.endswith(b"\n"):
            raise AuthorityEventRecoveryError("observability_recovery_required: truncated unindexed trace range")
        domains = dict(payload["domains"])
        tail = start
        for line in chunk.splitlines(keepends=True):
            start, end = tail, tail + len(line)
            tail = end
            try:
                raw = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError, TypeError) as exc:
                raise AuthorityEventRecoveryError("observability_recovery_required: malformed trace record") from exc
            if not isinstance(raw, dict):
                raise AuthorityEventRecoveryError("observability_recovery_required: trace record is not an object")
            if raw.get("_type") != "authority_event":
                continue
            if raw.get("schema") != AUTHORITY_EVENT_SCHEMA:
                raise AuthorityEventRecoveryError("observability_recovery_required: authority schema mismatch")
            event = AuthorityEvent.from_dict({key: raw.get(key) for key in AuthorityEvent.__dataclass_fields__})
            domain = dict(domains.get(event.runtime_domain_id) or _authority_default_domain(event.runtime_domain_id))
            expected = int(domain["durable_high_water_sequence"]) + 1
            if event.sequence != expected:
                raise AuthorityEventRecoveryError("observability_recovery_required: authority sequence discontinuity")
            index = RecordIndex(event.sequence, event.event_id, str(path.resolve()), start, end)
            domain.update(durable_high_water_sequence=event.sequence, durable_high_water_event_id=event.event_id, durable_high_water_trace_path=str(path.resolve()), durable_high_water_offset=start, durable_high_water_end_offset=end)
            pending = list(domain["pending_index"])
            if len(pending) >= _AUTHORITY_PENDING_LIMIT:
                raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
            pending.append(index.__dict__)
            domain["pending_index"] = pending
            if domain["pending_start_sequence"] is None:
                domain["pending_start_sequence"] = int(domain["live_handoff_cursor"]) + 1
            domain["pending_end_sequence"] = event.sequence
            if event.event_type == "AUTHORITY_EVENT_DELIVERY_CONFLICT":
                if event.request_type != "authority_delivery_conflict" or not isinstance(event.operation_id, str) or not event.operation_id or isinstance(event.queue_order, bool) or not isinstance(event.queue_order, int) or event.queue_order < 1:
                    raise AuthorityEventRecoveryError("authority delivery conflict lacks exact machine identity")
                marker = {"runtime_domain_id": event.runtime_domain_id, "sequence": event.queue_order, "event_id": event.operation_id}
                if marker not in domain["delivery_conflicts"]:
                    domain["delivery_conflicts"] = list(domain["delivery_conflicts"]) + [marker]
            domains[event.runtime_domain_id] = domain
        payload = dict(payload)
        payload["durable_tail_offset"] = end
        payload["domains"] = domains
        return payload

    def _event_from_record(self, record: Mapping[str, object]) -> AuthorityEvent:
        event_id = uuid.uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        sequence = int(record.get("sequence", 0))
        if sequence <= 0:
            raise AuthorityEventRecoveryError("invalid authority sequence allocation")
        values = {key: record.get(key) for key in AuthorityEvent.__dataclass_fields__}
        values.update(event_id=event_id, timestamp=timestamp, sequence=sequence)
        if values.get("runtime_domain_id") is None:
            values["runtime_domain_id"] = self.runtime_domain_id
        if values.get("repo_id") is None:
            values["repo_id"] = self.repo_id
        if values.get("process_id") is None:
            values["process_id"] = self.process_id
        values["event_type"] = str(record.get("event_type") or "AUTHORITY_EVENT")
        if values.get("status") is None:
            values["status"] = "DURABLE_COMMITTED"
        return AuthorityEvent(**values)  # type: ignore[arg-type]

    def attach_live_sink(self, sink: Callable[[dict[str, object]], object], *, handoff_epoch: str) -> None:
        if not callable(sink) or not isinstance(handoff_epoch, str) or not handoff_epoch:
            raise ValueError("live sink and real activity_epoch are required")
        self.live_sink = sink
        self.live_handoff_epoch = handoff_epoch

    def detach_live_sink(self) -> None:
        self.live_sink = None
        self.live_handoff_epoch = None

    def _deliver(self, event: AuthorityEvent, state: dict[str, object], payload: dict[str, object]) -> bool:
        if self.live_sink is None:
            return False
        cursor = int(state.get("live_handoff_cursor") or 0)
        if event.sequence != cursor + 1:
            # Never acknowledge a later event while an earlier durable event
            # is still pending; replay must preserve the durable order.
            return False
        try:
            result = self.live_sink(event.to_dict())
        except Exception:
            return False
        if not isinstance(result, Mapping):
            return False
        if result.get("conflict"):
            key = (event.runtime_domain_id or "", event.sequence, event.event_id)
            known = {
                (item.get("runtime_domain_id"), item.get("sequence"), item.get("event_id"))
                for item in state.get("delivery_conflicts", [])
                if isinstance(item, Mapping)
            }
            if key not in known and event.event_type != "AUTHORITY_EVENT_DELIVERY_CONFLICT":
                state["delivery_conflicts"] = list(state.get("delivery_conflicts", [])) + [{"runtime_domain_id": key[0], "sequence": key[1], "event_id": key[2]}]
                self._append_delivery_conflict_locked(event, state, payload, key)
            return False
        if result.get("accepted") is not True or result.get("activity_epoch") != self.live_handoff_epoch:
            return False
        state = dict(state)
        state["live_handoff_cursor"] = event.sequence
        state["live_handoff_epoch"] = self.live_handoff_epoch
        if state.get("pending_end_sequence") is not None and event.sequence >= int(state["pending_end_sequence"]):
            state["pending_start_sequence"] = None
            state["pending_end_sequence"] = None
        else:
            state["pending_start_sequence"] = event.sequence + 1
        pending = [item for item in state["pending_index"] if item["sequence"] != event.sequence]
        state["pending_index"] = pending
        state["delivery_conflicts"] = [item for item in state.get("delivery_conflicts", []) if item.get("sequence") != event.sequence]
        if pending:
            state["pending_start_sequence"] = pending[0]["sequence"]
            state["pending_end_sequence"] = pending[-1]["sequence"]
        else:
            state["pending_start_sequence"] = state["pending_end_sequence"] = None
        try:
            _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
        except Exception:
            # Durable event and canonical correctness are already committed;
            # an acknowledgement write failure leaves the event pending for a
            # later bounded replay and must not abort the authority service.
            return False
        return True

    def _append_delivery_conflict_locked(
        self,
        conflicted: AuthorityEvent,
        state: Mapping[str, object],
        payload: Mapping[str, object],
        key: tuple[str, int, str],
    ) -> None:
        """Persist one diagnostic without recursively attempting LIVE delivery."""
        sequence = int(state["durable_high_water_sequence"]) + 1
        event = self._event_from_record(
            {
                "event_type": "AUTHORITY_EVENT_DELIVERY_CONFLICT",
                "sequence": sequence,
                "source": "runtime_trace",
                "operation_id": conflicted.event_id,
                "request_type": "authority_delivery_conflict",
                "queue_order": conflicted.sequence,
                "decision": "CONFLICT",
                "status": "SECONDARY_DELIVERY_PENDING",
                "reason": f"conflicted event identity={key}",
            }
        )
        index = _append_authority_record_locked(self.log_path, event)
        updated = dict(state)
        updated.update(
            durable_high_water_sequence=sequence,
            durable_high_water_event_id=event.event_id,
            durable_high_water_offset=index.offset,
            durable_high_water_end_offset=index.end_offset,
            durable_high_water_trace_path=index.trace_path,
            pending_start_sequence=int(updated.get("live_handoff_cursor") or 0) + 1,
            pending_end_sequence=sequence,
        )
        pending = list(updated["pending_index"])
        if len(pending) >= _AUTHORITY_PENDING_LIMIT:
            raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
        pending.append(index.__dict__)
        updated["pending_index"] = pending
        next_payload = dict(payload)
        next_payload["active_trace_path"] = str(self.log_path.resolve())
        next_payload["durable_tail_offset"] = index.end_offset
        _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, updated, next_payload)

    def replay_pending(self) -> int:
        with self._lock:
            with _AuthorityFileLock(self._lock_path):
                return self._replay_pending_locked()

    def _replay_pending_locked(self) -> int:
        delivered = 0
        state, payload = self._recover_locked()
        start = state.get("pending_start_sequence")
        end = state.get("pending_end_sequence")
        if not isinstance(start, int) or not isinstance(end, int) or start > end:
            return 0
        for item in state["pending_index"]:
            index = _record_index_from_payload(item)
            event = _read_authority_record_at(Path(index.trace_path), index.offset, index.end_offset)
            if self._deliver(event, state, payload):
                delivered += 1
                state, payload = self._recover_locked()
        return delivered

    def emit(self, event_type: str, **fields: object) -> AuthorityEvent:
        with self._lock:
            with _AuthorityFileLock(self._lock_path):
                if self.live_sink is not None:
                    self._replay_pending_locked()
                state, payload = self._recover_locked()
                # A failed secondary delivery never blocks the next durable event.
                sequence = int(state["durable_high_water_sequence"]) + 1
                event = self._event_from_record({**fields, "event_type": event_type, "sequence": sequence})
                index = _append_authority_record_locked(self.log_path, event)
                state = dict(state)
                state.update(
                    durable_high_water_sequence=sequence,
                    durable_high_water_event_id=event.event_id,
                    durable_high_water_trace_path=index.trace_path,
                    durable_high_water_offset=index.offset,
                    durable_high_water_end_offset=index.end_offset,
                )
                cursor = int(state.get("live_handoff_cursor") or 0)
                if cursor >= sequence:
                    state["pending_start_sequence"] = None
                    state["pending_end_sequence"] = None
                else:
                    pending_start = state.get("pending_start_sequence")
                    state["pending_start_sequence"] = sequence if not isinstance(pending_start, int) else min(pending_start, sequence)
                    state["pending_end_sequence"] = sequence
                pending = list(state["pending_index"])
                if len(pending) >= _AUTHORITY_PENDING_LIMIT:
                    raise AuthorityEventRecoveryError("observability_recovery_required: pending index retention exceeded")
                pending.append(index.__dict__)
                state["pending_index"] = pending
                payload = dict(payload)
                payload["active_trace_path"] = str(self.log_path.resolve())
                payload["durable_tail_offset"] = index.end_offset
                _write_authority_sidecar(self.sidecar_path, self.runtime_domain_id, state, payload)
                self._deliver(event, state, payload)
                return event


def get_authority_event_emitter(
    runtime_domain_id: str,
    *,
    repo_id: str | None = None,
    logs_root: str | Path | None = None,
    live_sink: Callable[[dict[str, object]], object] | None = None,
) -> AuthorityEventEmitter:
    root = (Path(logs_root) if logs_root is not None else runtime_logs_dir()).resolve()
    key = (str(root), runtime_domain_id)
    with _authority_lock:
        emitter = _authority_emitters.get(key)
        if emitter is None:
            emitter = AuthorityEventEmitter(runtime_domain_id=runtime_domain_id, repo_id=repo_id, logs_root=root)
            _authority_emitters[key] = emitter
        elif live_sink is not None:
            raise ValueError("attach_live_sink requires a real activity epoch")
        return emitter


def emit_authority_event(event_type: str, *, runtime_domain_id: str, repo_id: str | None = None, emitter: AuthorityEventEmitter | None = None, **fields: object) -> AuthorityEvent:
    pipeline = emitter or get_authority_event_emitter(runtime_domain_id, repo_id=repo_id)
    return pipeline.emit(event_type, repo_id=repo_id, runtime_domain_id=runtime_domain_id, **fields)


def _resolved_logs_root(logs_root: str | Path | None = None) -> Path:
    return (Path(logs_root) if logs_root is not None else runtime_logs_dir()).resolve()


def _pointer_path(logs_root: str | Path | None = None) -> Path:
    return _resolved_logs_root(logs_root) / _POINTER_NAME


def _active_trace_path_for_root(logs_root: Path) -> Path | None:
    pointer = _pointer_path(logs_root)
    try:
        payload = json.loads(pointer.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError) as exc:
        raise AuthorityEventRecoveryError(f"malformed runtime trace pointer: {pointer}") from exc
    if not isinstance(payload, dict):
        raise AuthorityEventRecoveryError("runtime trace pointer must be an object")
    file_name = payload.get("file")
    if not isinstance(file_name, str) or not file_name:
        raise AuthorityEventRecoveryError("runtime trace pointer file is invalid")
    candidate = (logs_root / file_name).resolve()
    if candidate.parent != logs_root.resolve() or candidate.suffix != ".jsonl":
        raise AuthorityEventRecoveryError("runtime trace pointer escapes logs_root")
    return candidate if candidate.exists() else None


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
    global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
    now = time.monotonic()
    with _lock:
        if not force and now - _last_pointer_check < _CHECK_INTERVAL:
            return _active_path
        _last_pointer_check = now
        resolved = _read_pointer()
        if resolved is None:
            if _active_fd is not None:
                try:
                    os.close(_active_fd)
                except OSError:
                    pass
                _active_fd = None
            _active_meta = None
            _active_path = None
            _active_sid = None
            return None
        meta, path = resolved
        if meta != _active_meta or path != _active_path:
            if _active_fd is not None:
                try:
                    os.close(_active_fd)
                except OSError:
                    pass
                _active_fd = None
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
    global _active_fd
    try:
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        encoded = payload.encode("utf-8")
        with _lock:
            if _active_fd is None:
                flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
                if hasattr(os, "O_BINARY"):
                    flags |= os.O_BINARY
                _active_fd = os.open(str(path), flags)
            os.write(_active_fd, encoded)
    except Exception:
        pass


def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str) -> list[dict[str, object]]:
    return [
        {"_type": "header", "schema": TRACE_SCHEMA, "purpose": "chronological Contextor Desktop/LIVE/MCP runtime diagnostics; one JSON object per line", "sid": sid, "started_at": started_at, "desktop_pid": desktop_pid, "file": file_name},
        {"_type": "fields", "fields": {"ts": "UTC ISO-8601 milliseconds", "mono_ms": "host monotonic milliseconds", "sid": "desktop trace session", "pid": "process id", "tid": "thread id", "d": "domain", "ev": "event", "op": "operation correlation id", "repo": "repository", "path": "repository-relative path", "kind": "change kind", "tool": "MCP tool", "rev": "observed canonical revision", "rev0": "canonical revision before transition", "rev1": "canonical revision after transition", "candidate_rev": "rejected candidate canonical revision", "seq": "activity-journal sequence", "q": "GUI queue size", "count": "count", "bytes": "byte count", "wait_ms": "queue wait milliseconds", "elapsed_ms": "elapsed milliseconds", "scan_ms": "watcher scan milliseconds", "ping_ms": "watcher ping milliseconds", "status": "compact status", "err": "bounded error", "mtime_ns": "observed file mtime"}},
        {"_type": "domains", "domains": ["DESKTOP", "LIVE", "MCP", "GUI"], "reserved": ["OPS"], "ops_note": "Reserved for future repository-operation coordination; not implemented here."},
        {"_type": "revision_semantics", "rev": "observed authoritative canonical revision", "rev0": "authoritative canonical revision before transition", "rev1": "authoritative canonical revision after transition", "seq": "independent activity-journal sequence", "logger_rule": "The logger never calculates or increments canonical revision or activity sequence."},
        {"_type": "events", "events": {"DESKTOP": ["SESSION_START", "SESSION_END"], "LIVE": ["FS_CHANGE_DETECTED", "WATCH_UPDATE_START", "WATCH_UPDATE_END", "WATCH_UPDATE_FAIL", "UPDATE_RECEIVED", "UPDATE_FAIL", "CLONE_END", "UPDATER_START", "UPDATER_END", "UPDATER_FAIL", "ENGINE_READY", "INCREMENTAL_END", "PERSIST_START", "SNAPSHOT_SAVE_END", "FILE_STATE_SAVE_END", "PERSIST_END", "CANONICAL_COMMIT", "UPDATE_PUBLISHED", "PUBLISH_RECEIVED", "CANONICAL_PUBLISH", "PUBLISH_FAIL", "ACTIVITY_APPEND", "SERVICE_START", "SERVICE_END"], "MCP": ["CALL_START", "IMPLEMENTATION_END", "DIAGNOSTICS_END", "TELEMETRY_END", "CALL_END", "CALL_FAIL"], "GUI": ["EVENT_BATCH_RECEIVED", "ACTIVITY_GAP", "STATUS_QUEUED", "STATUS_RENDERED"]}},
    ]


def _open_runtime_trace_session(*, logs_root: str | Path | None = None) -> Path:
    """Open and publish the sole runtime-trace JSONL session."""
    global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
    logs = _resolved_logs_root(logs_root)
    production_logs = runtime_logs_dir().resolve()
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
        handle.flush()
        os.fsync(handle.fileno())
    pointer = {"schema": TRACE_SCHEMA, "sid": sid, "file": file_name, "desktop_pid": pid, "started_at": started_at}
    atomic_write(_pointer_path(logs), json.dumps(pointer, ensure_ascii=False, separators=(",", ":")))
    if logs == production_logs:
        with _lock:
            _active_meta, _active_path, _active_sid = pointer, path.resolve(), sid
            _active_fd = None
            _last_pointer_check = time.monotonic()
    return path.resolve()


def _ensure_runtime_trace_session(*, logs_root: str | Path | None = None) -> Path:
    logs = _resolved_logs_root(logs_root)
    current = active_trace_path(force_refresh=True) if logs == runtime_logs_dir().resolve() else _active_trace_path_for_root(logs)
    if current is not None:
        current = current.resolve()
        if current.parent != logs:
            raise AuthorityEventRecoveryError("runtime trace session is outside requested logs_root")
        return current
    return _open_runtime_trace_session(logs_root=logs)


def start_desktop_trace_session() -> Path | None:
    """Create and publish one trace for this Desktop lifetime."""
    try:
        path = _ensure_runtime_trace_session()
        trace_event("DESKTOP", "SESSION_START", op=new_trace_operation("d"))
        return path
    except Exception:
        return None


def finish_desktop_trace_session() -> None:
    global _active_meta, _active_path, _active_sid, _active_fd, _last_pointer_check
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
            if _active_fd is not None:
                try:
                    os.close(_active_fd)
                except OSError:
                    pass
                _active_fd = None
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
        key_map = {"repo": "repo", "path": "path", "kind": "kind", "tool": "tool", "q": "q", "count": "count", "bytes": "bytes", "wait_ms": "wait_ms", "elapsed_ms": "elapsed_ms", "scan_ms": "scan_ms", "ping_ms": "ping_ms", "status": "status", "err": "err", "mtime_ns": "mtime_ns", "category": "category", "operation": "operation", "first_seq": "first_seq", "last_seq": "last_seq", "candidate_rev": "candidate_rev"}
        for key, value in fields.items():
            target = key_map.get(key)
            if target is not None and value is not None:
                record[target] = _bounded(value)
        _append(record, path)
    except Exception:
        pass


__all__ = [
    "TRACE_SCHEMA",
    "AUTHORITY_EVENT_SCHEMA",
    "AuthorityEvent",
    "AuthorityEventEmitter",
    "AuthorityEventRecoveryError",
    "authority_event_state_path",
    "get_authority_event_emitter",
    "emit_authority_event",
    "start_desktop_trace_session",
    "finish_desktop_trace_session",
    "active_trace_path",
    "new_trace_operation",
    "trace_event",
    "current_trace_operation",
    "trace_operation",
]
