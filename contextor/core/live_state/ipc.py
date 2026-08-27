"""Authenticated localhost IPC for the single in-RAM canonical LIVE owner."""

from __future__ import annotations

import copy
import secrets
import threading
from dataclasses import dataclass
from multiprocessing.connection import Client, Listener
from typing import Any, Callable


LIVE_PROTOCOL_VERSION = 3


@dataclass(frozen=True)
class LiveEndpoint:
    host: str
    port: int
    authkey_hex: str
    pid: int | None = None
    owner_pid: int | None = None
    owner_token: str | None = None
    repo_id: str | None = None
    root_path: str | None = None

    @property
    def address(self) -> tuple[str, int]:
        return self.host, self.port

    @property
    def authkey(self) -> bytes:
        return bytes.fromhex(self.authkey_hex)


ACTIVITY_EVENT_RETENTION = 10_000


_MISSING_REVISION = object()


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


class CanonicalLiveServer:
    """In-RAM coordinator for one repository's shared LIVE state."""

    def __init__(
        self,
        state: Any = None,
        *,
        revision: int | None = None,
        updater: Callable[[Any, str], Any] | None = None,
        authkey: bytes | None = None,
        retention: int = ACTIVITY_EVENT_RETENTION,
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
        self._updater = updater
        self._retention = retention
        self._events: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._authkey = authkey or secrets.token_bytes(32)
        self._listener = Listener(("127.0.0.1", 0), family="AF_INET", authkey=self._authkey)
        host, port = self._listener.address
        self.endpoint = LiveEndpoint(str(host), int(port), self._authkey.hex())

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
            if request.get("message") is not None:
                event["message"] = str(request["message"])

        self._events.append(event)
        del self._events[:-self._retention]
        return event

    def serve_forever(self) -> None:
        while not self._stop.is_set():
            try:
                connection = self._listener.accept()
            except OSError:
                if self._stop.is_set():
                    break
                raise
            try:
                request = connection.recv()
                response = self._dispatch(request)
                connection.send(response)
            except Exception as exc:
                try:
                    connection.send({"status": "error", "error": str(exc)})
                except (EOFError, OSError):
                    pass
            finally:
                connection.close()

    def _dispatch(self, request: Any) -> dict[str, Any]:
        if not isinstance(request, dict) or not isinstance(request.get("operation"), str):
            return {"status": "error", "error": "invalid_request"}
        operation = request["operation"]
        with self._lock:
            if operation == "ping":
                return {
                    "status": "ok",
                    "protocol_version": LIVE_PROTOCOL_VERSION,
                    "revision": self._revision,
                    "available": self._state is not None,
                }
            if operation == "snapshot":
                return {"status": "ok", "revision": self._revision, "state": self._state}
            if operation == "publish":
                state = request.get("state")
                try:
                    state_rev = _extract_state_revision(state)
                except ValueError as exc:
                    return {
                        "status": "error",
                        "error": "invalid_canonical_revision",
                        "revision": self._revision,
                        "candidate_revision": _raw_state_revision(state),
                    }
                expected_revision = self._revision + 1

                if state_rev is not None:
                    if state_rev < expected_revision:
                        return {
                            "status": "error",
                            "error": "non_monotonic_canonical_revision",
                            "revision": self._revision,
                            "candidate_revision": state_rev,
                            "expected_revision": expected_revision,
                        }
                    if state_rev > expected_revision:
                        return {
                            "status": "error",
                            "error": "canonical_revision_discontinuity",
                            "revision": self._revision,
                            "candidate_revision": state_rev,
                            "expected_revision": expected_revision,
                        }
                else:
                    if not _bind_state_revision(state, expected_revision):
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
                return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
            if operation in {"status", "record_activity", "mcp_call"}:
                cat = request.get("category", "MCP_CALL" if operation == "mcp_call" else "LIVE_STATE")
                evt = self._record_event(operation, request, category=cat)
                return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
            if operation == "update_file":
                if self._state is None or self._updater is None:
                    return {
                        "status": "error",
                        "error": "live_state_unavailable",
                    }

                previous_state = self._state
                previous_revision = self._revision
                expected_revision = previous_revision + 1
                file_path = str(request.get("file_path", ""))

                try:
                    candidate_state = _clone_state_for_update(previous_state)
                except Exception as exc:
                    return {
                        "status": "error",
                        "error": "canonical_state_clone_failed",
                        "revision": previous_revision,
                        "expected_revision": expected_revision,
                        "detail": str(exc),
                    }

                # IMPORTANT: updater operates ONLY on candidate_state.
                # It must never receive previous_state/self._state directly.
                result = self._updater(
                    candidate_state,
                    file_path,
                )

                try:
                    state_rev = _extract_state_revision(candidate_state)
                except ValueError:
                    return {
                        "status": "error",
                        "error": "invalid_canonical_revision",
                        "revision": previous_revision,
                        "candidate_revision": _raw_state_revision(candidate_state),
                        "expected_revision": expected_revision,
                    }

                if state_rev is None:
                    if not _bind_state_revision(candidate_state, expected_revision):
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
                        return {
                            "status": "error",
                            "error": "canonical_revision_binding_failed",
                            "revision": previous_revision,
                            "candidate_revision": state_rev,
                            "expected_revision": expected_revision,
                        }
                    state_rev = expected_revision

                elif state_rev < previous_revision:
                    return {
                        "status": "error",
                        "error": "non_monotonic_canonical_revision",
                        "revision": previous_revision,
                        "candidate_revision": state_rev,
                        "expected_revision": expected_revision,
                    }

                elif state_rev > expected_revision:
                    return {
                        "status": "error",
                        "error": "canonical_revision_discontinuity",
                        "revision": previous_revision,
                        "candidate_revision": state_rev,
                        "expected_revision": expected_revision,
                    }

                elif state_rev != expected_revision:
                    return {
                        "status": "error",
                        "error": "canonical_revision_discontinuity",
                        "revision": previous_revision,
                        "candidate_revision": state_rev,
                        "expected_revision": expected_revision,
                    }

                # Final parity proof before commit.
                if _extract_state_revision(candidate_state) != expected_revision:
                    return {
                        "status": "error",
                        "error": "canonical_revision_binding_failed",
                        "revision": previous_revision,
                        "candidate_revision": _raw_state_revision(candidate_state),
                        "expected_revision": expected_revision,
                    }

                # ATOMIC COMMIT BOUNDARY.
                # Nothing above this line may replace/mutate active canonical ownership.
                self._state = candidate_state
                self._revision = expected_revision

                evt = self._record_event(
                    "update_file",
                    request,
                    result,
                    category="LIVE_STATE",
                )

                return {
                    "status": "ok",
                    "revision": self._revision,
                    "result": result,
                    "seq": evt["seq"],
                }
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
                        for name in ("error", "line_number", "column_number", "blast_radius_state", "affected_modules", "message"):
                            if e.get(name) is not None:
                                item[name] = e[name]
                        formatted_selected.append(item)
                    selected = formatted_selected

                return {
                    "status": "ok",
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

    def close(self) -> None:
        if not self._stop.is_set():
            self._stop.set()
            try:
                self._listener.close()
            except OSError:
                pass

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

    def request(
        self, operation: str, *, timeout: float = 30.0, **payload: Any
    ) -> dict[str, Any]:
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
        if not isinstance(response, dict):
            raise RuntimeError("Canonical LIVE service returned an invalid response.")
        return response

    def ping(self) -> dict[str, Any]:
        return self.request("ping")

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

    def update_file(self, file_path: str, *, origin: str = "unknown") -> dict[str, Any]:
        return self.request("update_file", file_path=file_path, origin=origin)

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
