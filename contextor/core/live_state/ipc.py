"""Authenticated localhost IPC for the single in-RAM canonical LIVE owner."""

from __future__ import annotations

import copy
from collections import OrderedDict, deque
from contextlib import contextmanager
import hashlib
import json
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from multiprocessing.connection import Client, Listener
from typing import Any, Callable, Mapping

from contextor.core.live_state.runtime_lease import ProcessIdentity


LIVE_PROTOCOL_VERSION = 3
LIVE_ENDPOINT_SCHEMA_VERSION = 2
_AUTHORITY_FINGERPRINT_LIMIT = 10_000


@dataclass(frozen=True)
class LiveEndpoint:
    host: str
    port: int
    authkey_hex: str
    pid: int | None = None
    service_pid: int | None = None
    owner_pid: int | None = None
    owner_token: str | None = None
    repo_id: str | None = None
    root_path: str | None = None
    runtime_domain_id: str | None = None
    service_instance_id: str | None = None
    lease_generation: int | None = None
    process_start_identity: str | None = None
    desktop_instance_id: str | None = None
    schema_version: int = LIVE_ENDPOINT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.service_pid is None:
            object.__setattr__(self, "service_pid", self.pid)
        elif self.pid is None:
            object.__setattr__(self, "pid", self.service_pid)
        elif self.pid != self.service_pid:
            raise ValueError("LIVE endpoint pid and service_pid disagree")

    @property
    def address(self) -> tuple[str, int]:
        return self.host, self.port

    @property
    def authkey(self) -> bytes:
        return bytes.fromhex(self.authkey_hex)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "host": self.host,
            "port": self.port,
            "authkey_hex": self.authkey_hex,
            "pid": self.pid,
            "service_pid": self.service_pid,
            "repo_id": self.repo_id,
            "root_path": self.root_path,
            "runtime_domain_id": self.runtime_domain_id,
            "service_instance_id": self.service_instance_id,
            "lease_generation": self.lease_generation,
            "process_start_identity": self.process_start_identity,
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.identity_payload(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "owner_pid": self.owner_pid,
            "owner_token": self.owner_token,
            "desktop_instance_id": self.desktop_instance_id,
        }


ACTIVITY_EVENT_RETENTION = 10_000
_DIAGNOSTIC_JOURNAL_LIMIT = 3
_MUTATION_JOB_RETENTION = 256
_MUTATION_WORKER_JOIN_TIMEOUT = 2.0


_MISSING_REVISION = object()


class CanonicalPersistenceConflict(RuntimeError):
    def __init__(self, current_revision: int | None, requested_revision: int):
        self.current_revision = current_revision
        self.requested_revision = requested_revision
        super().__init__(
            f"Canonical persistence revision conflict: current={current_revision}, requested={requested_revision}."
        )


@dataclass
class _MutationJob:
    job_id: str
    queue_order: int
    request: dict[str, Any]
    accepted_revision: int
    idempotency_key: str
    state: str = "queued"
    started_revision: int | None = None
    final_revision: int | None = None
    response: dict[str, Any] | None = None
    error: str | None = None


class CanonicalMutationCoordinator:
    def __init__(
        self,
        executor: Callable[[dict[str, Any]], dict[str, Any]],
        revision_reader: Callable[[], int],
        *,
        retention: int = _MUTATION_JOB_RETENTION,
    ):
        self._executor = executor
        self._revision_reader = revision_reader
        self._retention = retention
        self._condition = threading.Condition()
        self._queue: deque[str] = deque()
        self._jobs: OrderedDict[str, _MutationJob] = OrderedDict()
        self._idempotency_jobs: dict[str, str] = {}
        self._thread: threading.Thread | None = None
        self._accepting = True
        self._stop = False
        self._queue_order = 0

    def _ensure_started_locked(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._run,
                name="contextor-live-mutation-worker",
                daemon=True,
            )
            self._thread.start()

    def submit(self, request: Mapping[str, Any]) -> dict[str, Any]:
        try:
            request_dict = dict(request)
        except (TypeError, ValueError):
            request_dict = {}
        file_path = request_dict.get("file_path")
        if not isinstance(file_path, str) or not file_path:
            return {"status": "error", "error": "invalid_file_path"}
        idempotency_key = request_dict.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            return {"status": "error", "error": "invalid_idempotency_key"}

        with self._condition:
            existing_job_id = self._idempotency_jobs.get(idempotency_key)
            if existing_job_id is not None:
                existing_job = self._jobs.get(existing_job_id)
                if existing_job is not None:
                    return {
                        "status": "accepted",
                        "accepted": True,
                        "job_id": existing_job.job_id,
                        "queue_order": existing_job.queue_order,
                        "accepted_revision": existing_job.accepted_revision,
                        "state": existing_job.state,
                    }
                del self._idempotency_jobs[idempotency_key]
            if not self._accepting:
                return {
                    "status": "error",
                    "error": "canonical_mutation_queue_closed",
                }

            self._queue_order += 1
            job_id = "mu-" + uuid.uuid4().hex
            accepted_revision = int(self._revision_reader())
            job = _MutationJob(
                job_id=job_id,
                queue_order=self._queue_order,
                request=request_dict,
                accepted_revision=accepted_revision,
                idempotency_key=idempotency_key,
            )
            self._jobs[job_id] = job
            self._idempotency_jobs[idempotency_key] = job_id
            self._queue.append(job_id)
            self._ensure_started_locked()
            self._condition.notify_all()
            return {
                "status": "accepted",
                "accepted": True,
                "job_id": job_id,
                "queue_order": job.queue_order,
                "accepted_revision": accepted_revision,
                "state": job.state,
            }

    def status(self, job_id: Any) -> dict[str, Any]:
        if not isinstance(job_id, str) or not job_id:
            return {"status": "error", "error": "invalid_mutation_job_id"}

        with self._condition:
            job = self._jobs.get(job_id)
            if job is None:
                return {
                    "status": "error",
                    "error": "unknown_mutation_job",
                    "job_id": job_id,
                }
            response: dict[str, Any] = {
                "status": "ok",
                "job_id": job.job_id,
                "queue_order": job.queue_order,
                "accepted_revision": job.accepted_revision,
                "state": job.state,
            }
            if job.started_revision is not None:
                response["started_revision"] = job.started_revision
            if job.final_revision is not None:
                response["final_revision"] = job.final_revision
            if job.error is not None:
                response["error"] = job.error
            if job.response is not None:
                response["response"] = copy.deepcopy(job.response)
            return response

    def _prune_terminal_locked(self) -> None:
        terminal = {"completed", "failed", "cancelled"}
        while sum(job.state in terminal for job in self._jobs.values()) > self._retention:
            for job_id, job in self._jobs.items():
                if job.state in terminal:
                    del self._jobs[job_id]
                    if self._idempotency_jobs.get(job.idempotency_key) == job_id:
                        del self._idempotency_jobs[job.idempotency_key]
                    break
            else:
                break

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._queue and not self._stop:
                    self._condition.wait()
                if self._stop and not self._queue:
                    return
                job_id = self._queue.popleft()
                job = self._jobs.get(job_id)
                if job is None:
                    continue
                if job.state == "cancelled":
                    self._prune_terminal_locked()
                    self._condition.notify_all()
                    continue
                job.state = "running"
                job.started_revision = int(self._revision_reader())

            try:
                response = self._executor(job.request)
            except Exception as exc:
                response = {
                    "status": "error",
                    "error": "canonical_mutation_execution_failed",
                    "detail": str(exc),
                }
                with self._condition:
                    job.state = "failed"
                    job.response = response
                    job.error = str(exc)
                    self._prune_terminal_locked()
                    self._condition.notify_all()
                continue

            with self._condition:
                if isinstance(response, dict) and response.get("status") == "ok":
                    job.state = "completed"
                    job.response = response
                else:
                    job.state = "failed"
                    if isinstance(response, dict):
                        job.response = response
                        error = response.get("error")
                        job.error = str(error) if error is not None else "canonical_mutation_invalid_response"
                    else:
                        job.response = {
                            "status": "error",
                            "error": "canonical_mutation_invalid_response",
                        }
                        job.error = "canonical_mutation_invalid_response"
                final_revision = job.response.get("revision") if job.response else None
                if isinstance(final_revision, int) and not isinstance(final_revision, bool):
                    job.final_revision = final_revision
                self._prune_terminal_locked()
                self._condition.notify_all()

    def close(self, *, join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT) -> bool:
        with self._condition:
            self._accepting = False
            self._stop = True
            for job_id in self._queue:
                job = self._jobs.get(job_id)
                if job is None or job.state != "queued":
                    continue
                job.state = "cancelled"
                job.error = "canonical_mutation_queue_closed"
                job.response = {
                    "status": "error",
                    "error": "canonical_mutation_queue_closed",
                    "job_id": job_id,
                }
            self._queue.clear()
            self._prune_terminal_locked()
            self._condition.notify_all()
            thread = self._thread

        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=join_timeout)
        return thread is None or not thread.is_alive()


def _safe_trace_op(request: dict[str, Any], prefix: str) -> str | None:
    existing = request.get("trace_op")
    if existing is not None:
        try:
            return str(existing)
        except Exception:
            return None
    try:
        from contextor.core.runtime_trace import new_trace_operation

        return new_trace_operation(prefix)
    except Exception:
        return None


def _safe_trace_event(domain: str, event: str, **fields: Any) -> None:
    try:
        from contextor.core.runtime_trace import trace_event

        trace_event(domain, event, **fields)
    except Exception:
        pass


@contextmanager
def _trace_operation_context(op: str | None):
    if op is None:
        yield
        return
    try:
        from contextor.core.runtime_trace import trace_operation
        manager = trace_operation(op)
    except Exception:
        yield
        return

    entered = False
    try:
        try:
            manager.__enter__()
            entered = True
        except Exception:
            yield
            return

        try:
            yield
        except BaseException:
            import sys

            exc_info = sys.exc_info()
            if entered:
                try:
                    manager.__exit__(*exc_info)
                except Exception:
                    pass
            raise
        else:
            if entered:
                try:
                    manager.__exit__(None, None, None)
                except Exception:
                    pass
    finally:
        pass


def _raw_state_revision(state: Any) -> Any:
    if state is None:
        return _MISSING_REVISION
    if isinstance(state, dict):
        return state.get("revision", _MISSING_REVISION)
    return getattr(state, "revision", _MISSING_REVISION)


def _extract_state_revision(state: Any) -> int | None:
    value = _raw_state_revision(state)

    if value is _MISSING_REVISION or value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise ValueError(
            f"Invalid canonical state revision: {value!r}"
        )

    return value


def _bind_state_revision(state: Any, revision: int) -> bool:
    if state is None:
        return False
    if isinstance(state, dict):
        try:
            state["revision"] = revision
            return state.get("revision") == revision
        except Exception:
            return False
    try:
        state.revision = revision
    except Exception:
        return False
    return getattr(state, "revision", None) == revision


def _clone_state_for_update(state: Any) -> Any:
    if state is None:
        raise ValueError("canonical state unavailable")

    clone_method = getattr(state, "clone_for_update", None)
    if callable(clone_method):
        candidate = clone_method()
    else:
        candidate = copy.deepcopy(state)

    if candidate is state:
        raise ValueError("canonical state clone returned original object")

    return candidate


def _state_value(state: Any, name: str, default: Any = None) -> Any:
    """Read one canonical-state field without assuming an object shape."""
    try:
        if isinstance(state, Mapping):
            return state.get(name, default)
        return getattr(state, name, default)
    except Exception:
        return default


def _family_is_fresh(state: Any, field_name: str) -> bool:
    return _state_value(state, field_name) == "fresh"


def _diagnostic_key_text(kind: str, parts: tuple[Any, ...]) -> str:
    try:
        return json.dumps(
            [kind, *parts], ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
    except (TypeError, ValueError):
        return ""


def _valid_optional_int(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


def _syntax_diagnostic_map(state: Any) -> dict[str, dict[str, Any]] | None:
    if not _family_is_fresh(state, "syntax_diagnostics_state"):
        return None
    facts = _state_value(state, "syntax_diagnostics_by_path")
    if not isinstance(facts, Mapping):
        return None

    result: dict[str, dict[str, Any]] = {}
    source_paths = sorted(path for path in facts if isinstance(path, str) and path)
    for source_path in source_paths:
        fact = facts.get(source_path)
        if not isinstance(fact, Mapping) or fact.get("status") != "checked_with_errors":
            continue
        errors = fact.get("errors")
        if not isinstance(errors, (list, tuple)):
            continue
        for error in errors:
            if not isinstance(error, Mapping):
                continue
            message = error.get("message")
            line_number = error.get("line_number")
            column_number = error.get("column_number")
            if (
                not isinstance(message, str)
                or not message
                or not _valid_optional_int(line_number)
                or not _valid_optional_int(column_number)
            ):
                continue
            key = _diagnostic_key_text(
                "syntax", (source_path, line_number, column_number)
            )
            if not key:
                continue
            candidate = {
                "source_path": source_path,
                "message": message,
                "line_number": line_number,
                "column_number": column_number,
            }
            existing = result.get(key)
            if existing is None or candidate["message"] < existing["message"]:
                result[key] = candidate
    return result


def _collision_diagnostic_map(state: Any) -> dict[str, dict[str, Any]] | None:
    if not _family_is_fresh(state, "collisions_state"):
        return None
    collisions = _state_value(state, "collisions")
    if not isinstance(collisions, (list, tuple)):
        return None

    result: dict[str, dict[str, Any]] = {}
    for collision in collisions:
        kind = _state_value(collision, "kind")
        artifact_type = _state_value(collision, "artifact_type")
        is_identical = _state_value(collision, "is_identical")
        nodes = _state_value(collision, "nodes")
        symbol_details = _state_value(collision, "symbol_details")
        if (
            not isinstance(kind, str)
            or not kind
            or not isinstance(artifact_type, str)
            or not artifact_type
            or type(is_identical) is not bool
            or not isinstance(nodes, (list, tuple, set))
            or not isinstance(symbol_details, (list, tuple))
            or not symbol_details
        ):
            continue
        if not all(isinstance(node, str) and node for node in nodes):
            continue
        normalized_nodes = sorted(set(nodes))
        if not normalized_nodes:
            continue

        names: set[str] = set()
        malformed = False
        for detail in symbol_details:
            if not isinstance(detail, Mapping):
                malformed = True
                break
            name = detail.get("name")
            if isinstance(name, str) and name:
                names.add(name)
            detail_type = detail.get("artifact_type")
            if detail_type:
                if not isinstance(detail_type, str) or detail_type != artifact_type:
                    malformed = True
                    break
        if malformed or len(names) != 1:
            continue
        collision_symbol = next(iter(names))
        key = _diagnostic_key_text(
            "collision",
            (kind, artifact_type, is_identical, collision_symbol, *normalized_nodes),
        )
        if not key:
            continue
        result.setdefault(
            key,
            {
                "collision_kind": kind,
                "collision_artifact_type": artifact_type,
                "collision_symbol": collision_symbol,
                "collision_is_identical": is_identical,
                "collision_nodes": normalized_nodes,
            },
        )
    return result


def _cycle_diagnostic_map(state: Any) -> dict[str, dict[str, Any]] | None:
    if not _family_is_fresh(state, "cycles_state"):
        return None
    cycles = _state_value(state, "cycles")
    if not isinstance(cycles, (list, tuple)):
        return None

    result: dict[str, dict[str, Any]] = {}
    for cycle in cycles:
        if (
            not isinstance(cycle, (list, tuple))
            or len(cycle) < 2
            or not all(isinstance(node, str) and node for node in cycle)
            or cycle[0] != cycle[-1]
        ):
            continue
        key = _diagnostic_key_text("cycle", tuple(cycle))
        if key:
            result.setdefault(key, {"cycle_nodes": list(cycle)})
    return result


def _build_diagnostic_delta(previous_state: Any, current_state: Any) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    families = (
        ("syntax", _syntax_diagnostic_map),
        ("collision", _collision_diagnostic_map),
        ("cycle", _cycle_diagnostic_map),
    )
    for kind, normalizer in families:
        previous = normalizer(previous_state)
        current = normalizer(current_state)
        if previous is None or current is None:
            continue
        for key in sorted(set(current) - set(previous)):
            changes.append(
                {"action": "ADDED", "diagnostic_kind": kind, "diagnostic_key": key, **current[key]}
            )
        for key in sorted(set(previous) - set(current)):
            changes.append(
                {"action": "RESOLVED", "diagnostic_kind": kind, "diagnostic_key": key, **previous[key]}
            )
    kind_rank = {"syntax": 0, "collision": 1, "cycle": 2}
    action_rank = {"ADDED": 0, "RESOLVED": 1}
    return sorted(
        changes,
        key=lambda item: (
            kind_rank[item["diagnostic_kind"]],
            action_rank[item["action"]],
            item["diagnostic_key"],
        ),
    )


def _bounded_diagnostic_payload(changes: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not changes:
        return None
    return {
        "total": len(changes),
        "truncated": len(changes) > _DIAGNOSTIC_JOURNAL_LIMIT,
        "items": copy.deepcopy(changes[:_DIAGNOSTIC_JOURNAL_LIMIT]),
    }


def _diagnostic_trace_event_name(change: Mapping[str, Any]) -> str | None:
    names = {
        ("syntax", "ADDED"): "LIVE_DIAGNOSTIC_SYNTAX_ERROR",
        ("syntax", "RESOLVED"): "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED",
        ("collision", "ADDED"): "LIVE_DIAGNOSTIC_COLLISION_ADDED",
        ("collision", "RESOLVED"): "LIVE_DIAGNOSTIC_COLLISION_RESOLVED",
        ("cycle", "ADDED"): "LIVE_DIAGNOSTIC_CYCLE_ADDED",
        ("cycle", "RESOLVED"): "LIVE_DIAGNOSTIC_CYCLE_RESOLVED",
    }
    return names.get((change.get("diagnostic_kind"), change.get("action")))


class CanonicalLiveServer:
    """In-RAM coordinator for one repository's shared LIVE state."""

    def __init__(
        self,
        state: Any = None,
        *,
        revision: int | None = None,
        updater: Callable[[Any, str], Any] | None = None,
        persister: Callable[[Any, int], Any] | None = None,
        authkey: bytes | None = None,
        retention: int = ACTIVITY_EVENT_RETENTION,
        authority_identity: Mapping[str, Any] | None = None,
        desktop_claim: Mapping[str, Any] | None = None,
        desktop_claim_reader: Callable[[], Mapping[str, Any] | None] | None = None,
        desktop_claim_acquirer: Callable[[str, int, str], Mapping[str, Any]] | None = None,
        desktop_claim_releaser: Callable[[str, int, str], None] | None = None,
        mutation_guard: Callable[[Mapping[str, Any], threading.Event], Any] | None = None,
    ):
        if revision is not None and (
            isinstance(revision, bool)
            or not isinstance(revision, int)
            or revision < 0
        ):
            raise ValueError(
                f"Invalid canonical revision: {revision!r}"
            )

        self._state = state
        state_rev = _extract_state_revision(state)

        if isinstance(state_rev, int) and state_rev >= 0:
            if revision is not None and int(revision) != state_rev:
                raise ValueError(
                    f"Constructor canonical revision mismatch: explicit revision={revision} != state.revision={state_rev}"
                )
            self._revision = state_rev
        elif revision is not None:
            self._revision = int(revision)
            if self._state is not None:
                if not _bind_state_revision(self._state, self._revision):
                    raise ValueError(
                        f"Failed to bind explicit canonical revision={self._revision} into state"
                    )
        else:
            self._revision = 0
            if self._state is not None:
                if not _bind_state_revision(self._state, 0):
                    raise ValueError(
                        "Failed to bind default canonical revision=0 into state"
                    )

        self._activity_seq = 0
        self._activity_epoch = uuid.uuid4().hex
        self._updater = updater
        self._persister = persister
        self._retention = retention
        self._events: list[dict[str, Any]] = []
        self._authority_event_fingerprints: OrderedDict[tuple[str, int, str], str] = OrderedDict()
        self._lock = threading.RLock()
        self._mutation_execution_lock = threading.Lock()
        self._mutation_guard = mutation_guard
        self._mutation_coordinator = CanonicalMutationCoordinator(
            self._execute_queued_update_file,
            self._read_revision,
        )
        self._stop = threading.Event()
        self._authkey = authkey or secrets.token_bytes(32)
        self._authority_identity = dict(authority_identity or {})
        self._desktop_claim = dict(desktop_claim) if desktop_claim is not None else None
        self._desktop_claim_reader = desktop_claim_reader
        self._desktop_claim_acquirer = desktop_claim_acquirer
        self._desktop_claim_releaser = desktop_claim_releaser
        self._listener = Listener(("127.0.0.1", 0), family="AF_INET", authkey=self._authkey)
        host, port = self._listener.address
        self.endpoint = LiveEndpoint(
            str(host),
            int(port),
            self._authkey.hex(),
            pid=self._authority_identity.get("service_pid"),
            owner_pid=self._authority_identity.get("owner_pid"),
            owner_token=self._authority_identity.get("owner_token"),
            repo_id=self._authority_identity.get("repo_id"),
            root_path=self._authority_identity.get("root_path"),
            runtime_domain_id=self._authority_identity.get("runtime_domain_id"),
            service_instance_id=self._authority_identity.get("service_instance_id"),
            lease_generation=self._authority_identity.get("lease_generation"),
            process_start_identity=self._authority_identity.get("process_start_identity"),
            desktop_instance_id=self._authority_identity.get("desktop_instance_id"),
        )

    def _read_revision(self) -> int:
        with self._lock:
            return self._revision

    def _record_event(
        self,
        operation: str,
        request: dict[str, Any],
        result: Any = None,
        *,
        category: str = "LIVE_STATE",
    ) -> dict[str, Any]:
        """Keep a small, JSON-safe event journal for Desktop status and MCP polling."""
        from datetime import datetime, timezone

        self._activity_seq += 1
        source = str(request.get("origin") or request.get("source") or "unknown")

        canonical_rev = self._revision if category == "LIVE_STATE" else None

        event: dict[str, Any] = {
            "seq": self._activity_seq,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "operation": operation,
            "source": source,
            "origin": source,
            "canonical_revision": canonical_rev,
            "revision": self._revision,
            "status": (
                getattr(result, "status", "PUBLISHED")
                if not isinstance(result, dict)
                else result.get("status", "PUBLISHED")
            ) if category == "LIVE_STATE" else ("SUCCESS" if request.get("success", True) else "FAILED"),
        }
        trace_op = request.get("trace_op")
        if trace_op is not None:
            event["trace_op"] = str(trace_op)

        if category == "MCP_CALL":
            event["tool"] = str(request.get("tool", ""))
            event["success"] = bool(request.get("success", True))
            if request.get("error"):
                event["error"] = str(request["error"])
            event["message"] = request.get("message") or f"MCP tool: {event['tool']}"
        else:
            file_path = getattr(result, "file_path", request.get("file_path")) if not isinstance(result, dict) else result.get("file_path", request.get("file_path"))
            if file_path is not None:
                event["file_path"] = str(file_path)
            for name in ("error", "line_number", "column_number"):
                value = getattr(result, name, None) if not isinstance(result, dict) else result.get(name)
                if value is not None:
                    event[name] = value
            blast_radius_state = (
                getattr(result, "blast_radius_state", None)
                if not isinstance(result, dict)
                else result.get("blast_radius_state")
            )
            if blast_radius_state is not None:
                event["blast_radius_state"] = blast_radius_state
            affected = (
                getattr(result, "affected_modules", None)
                if not isinstance(result, dict)
                else result.get("affected_modules")
            )
            if affected is not None:
                total = len(affected)
                event["affected_modules"] = {
                    "total": total,
                    "truncated": total > 20,
                    "items": list(affected[:20]),
                }
            diagnostic_changes = request.get("diagnostic_changes")
            if isinstance(diagnostic_changes, Mapping):
                event["diagnostic_changes"] = copy.deepcopy(diagnostic_changes)
            if request.get("message") is not None:
                event["message"] = str(request["message"])

        self._events.append(event)
        del self._events[:-self._retention]
        _safe_trace_event(
            "LIVE", "ACTIVITY_APPEND", op=trace_op,
            rev=self._revision, seq=self._activity_seq,
            category=category, operation=operation,
            status=event.get("status"),
        )
        return event

    @property
    def activity_epoch(self) -> str:
        return self._activity_epoch

    def record_authority_event(self, event: Mapping[str, Any]) -> dict[str, Any]:
        """Project one already-durable authority event into the existing LIVE journal.

        The durable emitter owns event identity and ordering.  This method only
        creates the GUI/MCP projection and is idempotent on the canonical
        ``(runtime_domain_id, sequence, event_id)`` key.
        """
        if not isinstance(event, Mapping):
            return {"accepted": False, "activity_epoch": self._activity_epoch}
        event_id = event.get("event_id")
        domain_id = event.get("runtime_domain_id")
        sequence = event.get("sequence")
        if not isinstance(event_id, str) or not event_id:
            return {"accepted": False, "activity_epoch": self._activity_epoch}
        if not isinstance(domain_id, str) or not domain_id:
            return {"accepted": False, "activity_epoch": self._activity_epoch}
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            return {"accepted": False, "activity_epoch": self._activity_epoch}
        expected_domain = self._authority_identity.get("runtime_domain_id")
        if expected_domain is not None and domain_id != expected_domain:
            return {"accepted": False, "activity_epoch": self._activity_epoch}
        key = (domain_id, sequence, event_id)
        fingerprint = hashlib.sha256(json.dumps(dict(event), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
        with self._lock:
            existing = self._authority_event_fingerprints.get(key)
            if existing is not None:
                if existing == fingerprint:
                    return {"accepted": True, "duplicate": True, "activity_epoch": self._activity_epoch}
                return {"accepted": False, "conflict": True, "activity_epoch": self._activity_epoch}
            self._authority_event_fingerprints[key] = fingerprint
            self._authority_event_fingerprints.move_to_end(key)
            if len(self._authority_event_fingerprints) > _AUTHORITY_FINGERPRINT_LIMIT:
                self._authority_event_fingerprints.popitem(last=False)
            self._activity_seq += 1
            projected = dict(event)
            projected.update(
                {
                    "seq": self._activity_seq,
                    "category": "AUTHORITY",
                    "operation": str(event.get("event_type") or "AUTHORITY_EVENT"),
                    "source": event.get("source") or "authority",
                    "origin": event.get("source") or "authority",
                    "canonical_revision": event.get("final_revision"),
                    "revision": self._revision,
                    "status": event.get("status") or "DURABLE_COMMITTED",
                }
            )
            self._events.append(projected)
            del self._events[:-self._retention]
            return {"accepted": True, "duplicate": False, "activity_epoch": self._activity_epoch}

    def _claim_identity_matches_request(self, request: Mapping[str, Any]) -> bool:
        for field in (
            "runtime_domain_id",
            "service_instance_id",
            "lease_generation",
        ):
            if request.get(field) != self._authority_identity.get(field):
                return False
        return True

    def _current_desktop_claim(self) -> dict[str, Any] | None:
        # External claim readers may participate in RuntimeLease/authority
        # callbacks. Never invoke them while holding the server state lock.
        if self._desktop_claim_reader is not None:
            claim = self._desktop_claim_reader()
            normalized = dict(claim) if claim is not None else None
            with self._lock:
                self._desktop_claim = normalized
                return copy.deepcopy(normalized) if normalized is not None else None

        with self._lock:
            return (
                copy.deepcopy(self._desktop_claim)
                if self._desktop_claim is not None
                else None
            )

    def _dispatch_desktop_claim_status(self) -> dict[str, Any]:
        try:
            claim = self._current_desktop_claim()
        except Exception as exc:
            return {
                "status": "error",
                "error": f"desktop_claim_unavailable: {exc}",
            }
        return {"status": "ok", "desktop_claim": claim}

    def _dispatch_claim_desktop(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if request.get("client_kind") != "desktop":
            return {
                "status": "error",
                "error": "desktop_claim_requires_desktop_client",
            }

        desktop_id = request.get("desktop_instance_id")
        if not isinstance(desktop_id, str) or not desktop_id.strip():
            return {
                "status": "error",
                "error": "desktop_instance_id_required",
            }
        desktop_id = desktop_id.strip()

        desktop_pid = request.get("desktop_pid")
        desktop_start = request.get("desktop_process_start_identity")
        if (
            isinstance(desktop_pid, bool)
            or not isinstance(desktop_pid, int)
            or desktop_pid <= 0
            or not isinstance(desktop_start, str)
            or not desktop_start.strip()
        ):
            return {
                "status": "error",
                "error": "desktop_process_identity_required",
            }
        desktop_start = desktop_start.strip()

        if not self._claim_identity_matches_request(request):
            return {
                "status": "error",
                "error": "desktop_claim_identity_mismatch",
            }

        try:
            if self._desktop_claim_acquirer is not None:
                # External authority callback outside self._lock.
                claim = self._desktop_claim_acquirer(
                    desktop_id,
                    desktop_pid,
                    desktop_start,
                )
            else:
                current = self._current_desktop_claim()
                if (
                    current is not None
                    and current.get("desktop_instance_id") != desktop_id
                ):
                    return {
                        "status": "error",
                        "error": "second_desktop_active",
                        "desktop_claim": current,
                    }
                claim = current or {
                    "runtime_domain_id": self._authority_identity.get(
                        "runtime_domain_id"
                    ),
                    "service_instance_id": self._authority_identity.get(
                        "service_instance_id"
                    ),
                    "lease_generation": self._authority_identity.get(
                        "lease_generation"
                    ),
                    "desktop_instance_id": desktop_id,
                    "desktop_pid": desktop_pid,
                    "desktop_process_start_identity": desktop_start,
                }
        except Exception as exc:
            if exc.__class__.__name__ == "DesktopClaimAlreadyHeld":
                try:
                    current = self._current_desktop_claim()
                except Exception:
                    current = None
                return {
                    "status": "error",
                    "error": "second_desktop_active",
                    "desktop_claim": current,
                }
            return {"status": "error", "error": str(exc)}

        with self._lock:
            self._desktop_claim = dict(claim)
            result_claim = copy.deepcopy(self._desktop_claim)

        return {
            "status": "ok",
            "claimed": True,
            "desktop_claim": result_claim,
        }

    def _dispatch_release_desktop_claim(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if request.get("client_kind") != "desktop":
            return {
                "status": "error",
                "error": "desktop_claim_requires_desktop_client",
            }

        desktop_id = request.get("desktop_instance_id")
        if not isinstance(desktop_id, str) or not desktop_id.strip():
            return {
                "status": "error",
                "error": "desktop_instance_id_required",
            }
        desktop_id = desktop_id.strip()

        desktop_pid = request.get("desktop_pid")
        desktop_start = request.get("desktop_process_start_identity")
        if (
            isinstance(desktop_pid, bool)
            or not isinstance(desktop_pid, int)
            or desktop_pid <= 0
            or not isinstance(desktop_start, str)
            or not desktop_start.strip()
        ):
            return {
                "status": "error",
                "error": "desktop_process_identity_required",
            }
        desktop_start = desktop_start.strip()

        if not self._claim_identity_matches_request(request):
            return {
                "status": "error",
                "error": "desktop_claim_identity_mismatch",
            }

        try:
            if self._desktop_claim_releaser is not None:
                # External authority callback outside self._lock.
                self._desktop_claim_releaser(
                    desktop_id,
                    desktop_pid,
                    desktop_start,
                )
            else:
                current = self._current_desktop_claim()
                if (
                    current is not None
                    and current.get("desktop_instance_id") != desktop_id
                ):
                    return {
                        "status": "error",
                        "error": "desktop_claim_not_owned",
                    }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

        with self._lock:
            self._desktop_claim = None

        return {
            "status": "ok",
            "released": True,
            "desktop_claim": None,
        }

    def serve_forever(self) -> None:
        while not self._stop.is_set():
            accept_started = time.monotonic()
            try:
                connection = self._listener.accept()
            except OSError as exc:
                if self._stop.is_set():
                    break
                _safe_trace_event(
                    "LIVE", "LIVE_IPC_FAILURE", side="server",
                    operation_or_request_type="accept", host=self.endpoint.host,
                    port=self.endpoint.port, exception_class=type(exc).__name__,
                    errno=getattr(exc, "errno", None),
                    winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                    elapsed_ms=(time.monotonic() - accept_started) * 1000.0,
                )
                raise
            request_type = "recv"
            request_started = time.monotonic()
            try:
                try:
                    request = connection.recv()
                except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
                    _safe_trace_event(
                        "LIVE", "LIVE_IPC_FAILURE", side="server",
                        operation_or_request_type="recv", host=self.endpoint.host,
                        port=self.endpoint.port, exception_class=type(exc).__name__,
                        errno=getattr(exc, "errno", None),
                        winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                        elapsed_ms=(time.monotonic() - request_started) * 1000.0,
                    )
                    try:
                        connection.send({"status": "error", "error": str(exc)})
                    except (EOFError, OSError):
                        pass
                    continue
                if isinstance(request, dict) and isinstance(request.get("operation"), str):
                    request_type = request["operation"]
                try:
                    response = self._dispatch(request)
                except Exception as exc:
                    try:
                        connection.send({"status": "error", "error": str(exc)})
                    except (EOFError, OSError):
                        pass
                    continue
                try:
                    connection.send(response)
                except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
                    _safe_trace_event(
                        "LIVE", "LIVE_IPC_FAILURE", side="server",
                        operation_or_request_type=(request_type if request_type != "recv" else "send"),
                        host=self.endpoint.host, port=self.endpoint.port,
                        exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
                        winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                        elapsed_ms=(time.monotonic() - request_started) * 1000.0,
                    )
                    try:
                        connection.send({"status": "error", "error": str(exc)})
                    except (EOFError, OSError):
                        pass
            finally:
                connection.close()

    def _execute_publish(self, request: dict[str, Any]) -> dict[str, Any]:
        with self._mutation_execution_lock:
            with self._lock:
                previous_revision = self._revision
                trace_op = _safe_trace_op(request, "p")
                if trace_op is not None:
                    request = {**request, "trace_op": trace_op}
                _safe_trace_event("LIVE", "PUBLISH_RECEIVED", op=trace_op, rev=previous_revision)
                state = request.get("state")
                try:
                    state_rev = _extract_state_revision(state)
                except ValueError as exc:
                    _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(state))
                    return {
                        "status": "error",
                        "error": "invalid_canonical_revision",
                        "revision": self._revision,
                        "candidate_revision": _raw_state_revision(state),
                    }
                expected_revision = self._revision + 1

                if state_rev is not None:
                    if state_rev < expected_revision:
                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
                        return {
                            "status": "error",
                            "error": "non_monotonic_canonical_revision",
                            "revision": self._revision,
                            "candidate_revision": state_rev,
                            "expected_revision": expected_revision,
                        }
                    if state_rev > expected_revision:
                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                        return {
                            "status": "error",
                            "error": "canonical_revision_discontinuity",
                            "revision": self._revision,
                            "candidate_revision": state_rev,
                            "expected_revision": expected_revision,
                        }
                else:
                    if not _bind_state_revision(state, expected_revision):
                        _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
                        return {
                            "status": "error",
                            "error": "canonical_revision_binding_failed",
                            "revision": self._revision,
                            "candidate_revision": None,
                        }
                    state_rev = expected_revision

                self._state = state
                self._revision = state_rev
                evt = self._record_event("publish", request, category="LIVE_STATE")
                _safe_trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=previous_revision, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
                return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}

    def _execute_queued_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
        if self._mutation_guard is None:
            return self._execute_update_file(request)
        with self._mutation_guard(request, self._stop):
            return self._execute_update_file(request)

    def _execute_update_file(self, request: dict[str, Any]) -> dict[str, Any]:
        with self._mutation_execution_lock:
            with self._lock:
                if self._state is None or self._updater is None:
                    return {
                        "status": "error",
                        "error": "live_state_unavailable",
                    }
                previous_state = self._state
                previous_revision = self._revision
                expected_revision = previous_revision + 1
                updater = self._updater
                persister = self._persister

            file_path = str(request.get("file_path", ""))
            trace_op = _safe_trace_op(request, "u")
            if trace_op is not None:
                request = {**request, "trace_op": trace_op}
            _safe_trace_event("LIVE", "UPDATE_RECEIVED", op=trace_op, path=file_path, rev=previous_revision)

            try:
                candidate_state = _clone_state_for_update(previous_state)
            except Exception as exc:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_state_clone_failed", err=exc)
                return {
                    "status": "error",
                    "error": "canonical_state_clone_failed",
                    "revision": previous_revision,
                    "expected_revision": expected_revision,
                    "detail": str(exc),
                }
            _safe_trace_event("LIVE", "CLONE_END", op=trace_op, path=file_path, rev=previous_revision)

            # IMPORTANT: updater operates ONLY on candidate_state.
            # It must never receive previous_state/self._state directly.
            _safe_trace_event("LIVE", "UPDATER_START", op=trace_op, path=file_path)
            updater_started = time.monotonic()
            try:
                with _trace_operation_context(trace_op):
                    result = updater(candidate_state, file_path)
            except Exception as exc:
                _safe_trace_event("LIVE", "UPDATER_FAIL", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, err=exc)
                raise
            _safe_trace_event("LIVE", "UPDATER_END", op=trace_op, path=file_path, elapsed_ms=(time.monotonic() - updater_started) * 1000.0, status=getattr(result, "status", None))

            try:
                state_rev = _extract_state_revision(candidate_state)
            except ValueError:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(candidate_state))
                return {
                    "status": "error",
                    "error": "invalid_canonical_revision",
                    "revision": previous_revision,
                    "candidate_revision": _raw_state_revision(candidate_state),
                    "expected_revision": expected_revision,
                }

            if state_rev is None:
                if not _bind_state_revision(candidate_state, expected_revision):
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
                    return {
                        "status": "error",
                        "error": "canonical_revision_binding_failed",
                        "revision": previous_revision,
                        "candidate_revision": None,
                        "expected_revision": expected_revision,
                    }
                state_rev = expected_revision

            elif state_rev == previous_revision:
                if not _bind_state_revision(candidate_state, expected_revision):
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=state_rev)
                    return {
                        "status": "error",
                        "error": "canonical_revision_binding_failed",
                        "revision": previous_revision,
                        "candidate_revision": state_rev,
                        "expected_revision": expected_revision,
                    }
                state_rev = expected_revision

            elif state_rev < previous_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "non_monotonic_canonical_revision",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            elif state_rev > expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "canonical_revision_discontinuity",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            elif state_rev != expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
                return {
                    "status": "error",
                    "error": "canonical_revision_discontinuity",
                    "revision": previous_revision,
                    "candidate_revision": state_rev,
                    "expected_revision": expected_revision,
                }

            # Final parity proof before commit.
            if _extract_state_revision(candidate_state) != expected_revision:
                _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=_raw_state_revision(candidate_state))
                return {
                    "status": "error",
                    "error": "canonical_revision_binding_failed",
                    "revision": previous_revision,
                    "candidate_revision": _raw_state_revision(candidate_state),
                    "expected_revision": expected_revision,
                }

            if persister is not None:
                _safe_trace_event("LIVE", "PERSIST_START", op=trace_op, path=file_path, rev=expected_revision)
                try:
                    with _trace_operation_context(trace_op):
                        persister(candidate_state, expected_revision)
                except Exception as exc:
                    from .store import SnapshotRevisionConflict

                    status = (
                        "canonical_persistence_revision_conflict"
                        if isinstance(exc, (CanonicalPersistenceConflict, SnapshotRevisionConflict))
                        else "canonical_persistence_failed"
                    )
                    _safe_trace_event("LIVE", "UPDATE_FAIL", op=trace_op, path=file_path, rev=previous_revision, status=status, err=exc)
                    response = {
                        "status": "error",
                        "error": status,
                        "revision": previous_revision,
                        "expected_revision": expected_revision,
                    }
                    persisted_revision = getattr(exc, "current_revision", None)
                    if persisted_revision is not None:
                        response["persisted_revision"] = persisted_revision
                        response["resync_required"] = True
                    return response
                _safe_trace_event("LIVE", "PERSIST_END", op=trace_op, path=file_path, rev=expected_revision)

            with self._lock:
                if self._revision != previous_revision or self._state is not previous_state:
                    _safe_trace_event(
                        "LIVE",
                        "UPDATE_FAIL",
                        op=trace_op,
                        path=file_path,
                        rev=self._revision,
                        status="canonical_revision_changed_during_update",
                        expected_revision=expected_revision,
                    )
                    return {
                        "status": "error",
                        "error": "canonical_revision_changed_during_update",
                        "revision": self._revision,
                        "expected_revision": expected_revision,
                    }

                # ATOMIC COMMIT BOUNDARY.
                # Nothing above this line may replace/mutate active canonical ownership.
                self._state = candidate_state
                self._revision = expected_revision
                _safe_trace_event("LIVE", "CANONICAL_COMMIT", op=trace_op, path=file_path, rev_before=previous_revision, rev_after=expected_revision)

                try:
                    diagnostic_delta = _build_diagnostic_delta(
                        previous_state, self._state
                    )
                except Exception:
                    diagnostic_delta = []
                diagnostic_payload = _bounded_diagnostic_payload(diagnostic_delta)
                event_request = dict(request)
                # Request payload is untrusted metadata: only the committed-state
                # comparison may publish diagnostic evidence.
                event_request.pop("diagnostic_changes", None)
                if diagnostic_payload is not None:
                    event_request["diagnostic_changes"] = diagnostic_payload

                evt = self._record_event(
                    "update_file",
                    event_request,
                    result,
                    category="LIVE_STATE",
                )
                committed_revision = self._revision
                committed_seq = evt["seq"]

            _safe_trace_event("LIVE", "UPDATE_PUBLISHED", op=trace_op, path=file_path, rev=committed_revision, seq=committed_seq, status=getattr(result, "status", None))
            origin = str(event_request.get("origin") or event_request.get("source") or "unknown")
            trace_common = {
                "repo": self._authority_identity.get("root_path"),
                "repo_id": self._authority_identity.get("repo_id"),
                "origin": origin,
                "diagnostic_total": len(diagnostic_delta),
                "diagnostic_truncated": len(diagnostic_delta) > _DIAGNOSTIC_JOURNAL_LIMIT,
            }
            for change in diagnostic_delta:
                event_name = _diagnostic_trace_event_name(change)
                if event_name is None:
                    continue
                trace_fields = {
                    **trace_common,
                    "diagnostic_kind": change["diagnostic_kind"],
                    "diagnostic_key": change["diagnostic_key"],
                }
                if "source_path" in change:
                    trace_fields["path"] = change["source_path"]
                if change["diagnostic_kind"] == "syntax":
                    trace_fields.update(
                        error=change["message"],
                        line_number=change["line_number"],
                        column_number=change["column_number"],
                    )
                elif change["diagnostic_kind"] == "collision":
                    for field in (
                        "collision_kind",
                        "collision_artifact_type",
                        "collision_symbol",
                        "collision_is_identical",
                        "collision_nodes",
                    ):
                        trace_fields[field] = change[field]
                else:
                    trace_fields["cycle_nodes"] = change["cycle_nodes"]
                _safe_trace_event(
                    "LIVE", event_name, op=trace_op, rev=committed_revision, **trace_fields
                )

            return {
                "status": "ok",
                "activity_epoch": self._activity_epoch,
                "revision": committed_revision,
                "result": result,
                "seq": committed_seq,
            }

    def _dispatch(self, request: Any) -> dict[str, Any]:
        if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
            return {"status": "error", "error": "invalid_request"}
        operation = request["operation"]

        # Desktop authority callbacks cross the RuntimeLease/observability
        # boundary and may synchronously emit back into record_authority_event.
        # Dispatch them outside the server state lock.
        if operation == "desktop_claim_status":
            return self._dispatch_desktop_claim_status()
        if operation == "claim_desktop":
            return self._dispatch_claim_desktop(request)
        if operation == "release_desktop_claim":
            return self._dispatch_release_desktop_claim(request)
        if operation == "submit_update_file":
            return self._mutation_coordinator.submit(request)
        if operation == "mutation_status":
            return self._mutation_coordinator.status(request.get("job_id"))
        if operation == "update_file":
            return self._execute_update_file(request)
        if operation == "publish":
            return self._execute_publish(request)

        with self._lock:
            if operation == "ping":
                return {
                    "status": "ok",
                    "protocol_version": LIVE_PROTOCOL_VERSION,
                    "revision": self._revision,
                    "available": self._state is not None,
                }
            if operation == "authority_status":
                if not self._authority_identity:
                    return {"status": "error", "error": "authority_identity_unavailable"}
                return {
                    "status": "ok",
                    "protocol_version": LIVE_PROTOCOL_VERSION,
                    "revision": self._revision,
                    "repo_id": self._authority_identity.get("repo_id"),
                    "root_path": self._authority_identity.get("root_path"),
                    "runtime_domain_id": self._authority_identity.get("runtime_domain_id"),
                    "service_instance_id": self._authority_identity.get("service_instance_id"),
                    "lease_generation": self._authority_identity.get("lease_generation"),
                    "service_pid": self._authority_identity.get("service_pid"),
                    "process_start_identity": self._authority_identity.get("process_start_identity"),
                    "endpoint_fingerprint": self.endpoint.fingerprint(),
                }
            if operation == "snapshot":
                return {"status": "ok", "revision": self._revision, "state": self._state}
            if operation in {"status", "record_activity", "mcp_call"}:
                cat = request.get("category", "MCP_CALL" if operation == "mcp_call" else "LIVE_STATE")
                evt = self._record_event(operation, request, category=cat)
                return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
            if operation == "get_events":
                after_revision = request.get("after_revision")
                after_seq = request.get("after_seq")
                category = request.get("category")
                limit = request.get("limit", 20)

                if after_revision is not None and (
                    isinstance(after_revision, bool)
                    or not isinstance(after_revision, int)
                ):
                    return {"status": "error", "error": "invalid_after_revision"}

                if after_seq is not None and (
                    isinstance(after_seq, bool)
                    or not isinstance(after_seq, int)
                ):
                    return {"status": "error", "error": "invalid_after_seq"}

                earliest_retained_seq = self._events[0]["seq"] if self._events else None

                if after_seq is None:
                    activity_continuity = "not_requested"
                    activity_resync_required = False
                elif after_seq == self._activity_seq:
                    activity_continuity = "continuous"
                    activity_resync_required = False
                elif earliest_retained_seq is None:
                    activity_continuity = "gap"
                    activity_resync_required = True
                elif after_seq < earliest_retained_seq - 1:
                    activity_continuity = "gap"
                    activity_resync_required = True
                else:
                    activity_continuity = "continuous"
                    activity_resync_required = False

                canonical_events = [
                    e for e in self._events
                    if e.get("category") == "LIVE_STATE" and e.get("operation") in {"publish", "update_file"}
                ]
                earliest_retained_revision = canonical_events[0]["canonical_revision"] if canonical_events else None
                latest_revision = self._revision
                latest_seq = self._activity_seq

                if after_revision is None:
                    continuity = "not_requested"
                    resync_required = False
                    resync_reason = None
                elif after_revision > latest_revision:
                    continuity = "gap"
                    resync_required = True
                    resync_reason = "revision_discontinuity"
                elif not canonical_events:
                    if after_revision == latest_revision:
                        continuity = "continuous"
                        resync_required = False
                        resync_reason = None
                    else:
                        continuity = "gap"
                        resync_required = True
                        resync_reason = "event_retention_gap"
                else:
                    if earliest_retained_revision is not None and after_revision < earliest_retained_revision - 1:
                        continuity = "gap"
                        resync_required = True
                        resync_reason = "event_retention_gap"
                    else:
                        continuity = "continuous"
                        resync_required = False
                        resync_reason = None

                events = self._events
                if category is not None:
                    events = [e for e in events if e.get("category") == category]
                if after_seq is not None:
                    events = [e for e in events if e.get("seq", 0) > after_seq]
                elif after_revision is not None:
                    events = [
                        e
                        for e in events
                        if (
                            e.get("category") == "LIVE_STATE"
                            and e.get("operation") in {"publish", "update_file"}
                            and isinstance(e.get("canonical_revision"), int)
                            and e["canonical_revision"] > after_revision
                        )
                    ]

                total = len(events)
                selected = events if limit is None else events[:max(0, int(limit))]

                if after_revision is not None and after_seq is None:
                    formatted_selected = []
                    for e in selected:
                        item = {
                            "revision": e["revision"],
                            "operation": e["operation"],
                            "origin": e["origin"],
                            "status": e["status"],
                            "file_path": e.get("file_path"),
                        }
                        for name in ("error", "line_number", "column_number", "blast_radius_state", "affected_modules", "diagnostic_changes", "message"):
                            if e.get(name) is not None:
                                item[name] = copy.deepcopy(e[name])
                        formatted_selected.append(item)
                    selected = formatted_selected

                return {
                    "status": "ok",
                    "activity_epoch": self._activity_epoch,
                    "revision": self._revision,
                    "latest_revision": latest_revision,
                    "latest_seq": latest_seq,
                    "earliest_retained_revision": earliest_retained_revision,
                    "earliest_retained_seq": earliest_retained_seq,
                    "continuity": continuity,
                    "resync_required": resync_required,
                    "resync_reason": resync_reason,
                    "activity_continuity": activity_continuity,
                    "activity_resync_required": activity_resync_required,
                    "events": selected,
                    "total": total,
                    "truncated": len(selected) < total,
                }
            if operation == "shutdown":
                self._stop.set()
                return {"status": "ok", "revision": self._revision}
            return {"status": "error", "error": "unknown_operation"}

    def close(
        self, *, mutation_join_timeout: float = _MUTATION_WORKER_JOIN_TIMEOUT
    ) -> bool:
        self._stop.set()
        try:
            self._listener.close()
        except OSError:
            pass
        return self._mutation_coordinator.close(join_timeout=mutation_join_timeout)

    def __enter__(self) -> "CanonicalLiveServer":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class LiveStateClient:
    """Small synchronous client used by desktop watcher and MCP adapters."""

    def __init__(
        self,
        endpoint: LiveEndpoint,
        *,
        is_owner: bool = False,
        service_pid: int | None = None,
        owner_pid: int | None = None,
        owner_token: str | None = None,
    ):
        self.endpoint = endpoint
        self.is_owner = is_owner
        self.service_pid = service_pid if service_pid is not None else getattr(endpoint, "pid", None)
        self.owner_pid = owner_pid if owner_pid is not None else getattr(endpoint, "owner_pid", None)
        self.owner_token = owner_token if owner_token is not None else getattr(endpoint, "owner_token", None)
        self.desktop_instance_id = getattr(endpoint, "desktop_instance_id", None)
        self.desktop_process_identity: ProcessIdentity | None = None

    def request(
        self, operation: str, *, timeout: float = 30.0, **payload: Any
    ) -> dict[str, Any]:
        started = time.monotonic()
        try:
            connection = Client(
                self.endpoint.address,
                family="AF_INET",
                authkey=self.endpoint.authkey,
            )
            try:
                connection.send({"operation": operation, **payload})
                import multiprocessing.connection as mpc
                ready = mpc.wait([connection], timeout=timeout)
                if not ready:
                    raise TimeoutError(
                        "Canonical LIVE service did not respond within "
                        f"{timeout:g}s for op={operation}"
                    )
                response = connection.recv()
            finally:
                connection.close()
        except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
            _safe_trace_event(
                "LIVE", "LIVE_IPC_FAILURE",
                side="client", operation_or_request_type=operation,
                host=getattr(self.endpoint, "host", self.endpoint.address[0]),
                port=getattr(self.endpoint, "port", self.endpoint.address[1]),
                exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
                winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                elapsed_ms=(time.monotonic() - started) * 1000.0,
            )
            raise
        if not isinstance(response, dict):
            raise RuntimeError("Canonical LIVE service returned an invalid response.")
        return response

    def ping(self) -> dict[str, Any]:
        return self.request("ping")

    def authority_status(self) -> dict[str, Any]:
        return self.request("authority_status")

    def desktop_claim_status(self) -> dict[str, Any]:
        return self.request("desktop_claim_status")

    def claim_desktop(
        self,
        desktop_instance_id: str,
        desktop_process_identity: ProcessIdentity,
    ) -> dict[str, Any]:
        return self.request(
            "claim_desktop",
            client_kind="desktop",
            desktop_instance_id=desktop_instance_id,
            desktop_pid=desktop_process_identity.pid,
            desktop_process_start_identity=desktop_process_identity.process_start_identity,
            runtime_domain_id=self.endpoint.runtime_domain_id,
            service_instance_id=self.endpoint.service_instance_id,
            lease_generation=self.endpoint.lease_generation,
        )

    def release_desktop_claim(
        self,
        desktop_instance_id: str,
        desktop_process_identity: ProcessIdentity,
    ) -> dict[str, Any]:
        return self.request(
            "release_desktop_claim",
            client_kind="desktop",
            desktop_instance_id=desktop_instance_id,
            desktop_pid=desktop_process_identity.pid,
            desktop_process_start_identity=desktop_process_identity.process_start_identity,
            runtime_domain_id=self.endpoint.runtime_domain_id,
            service_instance_id=self.endpoint.service_instance_id,
            lease_generation=self.endpoint.lease_generation,
        )

    def snapshot(self) -> dict[str, Any]:
        return self.request("snapshot")

    def publish(
        self,
        state: Any,
        *,
        origin: str = "unknown",
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        return self.request(
            "publish", timeout=timeout, state=state, origin=origin
        )

    def update_file(self, file_path: str, *, origin: str = "unknown", trace_op: str | None = None) -> dict[str, Any]:
        return self.request("update_file", file_path=file_path, origin=origin, trace_op=trace_op)

    def submit_update_file(
        self,
        file_path: str,
        *,
        origin: str = "unknown",
        trace_op: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "submit_update_file",
            file_path=file_path,
            origin=origin,
            trace_op=trace_op,
            idempotency_key=idempotency_key,
        )

    def mutation_status(self, job_id: str) -> dict[str, Any]:
        return self.request("mutation_status", job_id=job_id)

    def get_events(
        self,
        *,
        after_revision: int | None = None,
        after_seq: int | None = None,
        limit: int | None = 20,
        category: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "get_events",
            after_revision=after_revision,
            after_seq=after_seq,
            limit=limit,
            category=category,
        )

    def status(self, message: str, *, origin: str = "unknown") -> dict[str, Any]:
        return self.request("status", message=message, origin=origin, category="ACTIVITY")

    def record_activity(
        self,
        category: str,
        *,
        tool: str | None = None,
        message: str | None = None,
        source: str = "mcp",
        success: bool = True,
        error: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.request(
            "record_activity",
            category=category,
            tool=tool,
            message=message,
            source=source,
            success=success,
            error=error,
            **kwargs,
        )
