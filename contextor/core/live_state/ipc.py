"""Authenticated localhost IPC for the single in-RAM canonical LIVE owner."""

from __future__ import annotations

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

    @property
    def address(self) -> tuple[str, int]:
        return self.host, self.port

    @property
    def authkey(self) -> bytes:
        return bytes.fromhex(self.authkey_hex)


class CanonicalLiveServer:
    """Own one canonical state instance and expose revisioned operations over IPC."""

    def __init__(
        self,
        state: Any = None,
        *,
        revision: int = 0,
        updater: Callable[[Any, str], Any] | None = None,
        authkey: bytes | None = None,
    ):
        self._state = state
        self._revision = revision
        self._updater = updater
        self._events: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._authkey = authkey or secrets.token_bytes(32)
        self._listener = Listener(("127.0.0.1", 0), family="AF_INET", authkey=self._authkey)
        host, port = self._listener.address
        self.endpoint = LiveEndpoint(str(host), int(port), self._authkey.hex())

    def _record_event(self, operation: str, request: dict[str, Any], result: Any = None) -> None:
        """Keep a small, JSON-safe event journal for MCP polling."""
        event = {
            "revision": self._revision,
            "operation": operation,
            "origin": str(request.get("origin", "unknown")),
            "status": getattr(result, "status", "PUBLISHED"),
            "file_path": getattr(result, "file_path", request.get("file_path")),
        }
        for name in ("error", "line_number", "column_number"):
            value = getattr(result, name, None)
            if value is not None:
                event[name] = value
        if request.get("message") is not None:
            event["message"] = str(request["message"])
        self._events.append(event)
        del self._events[:-100]

    def serve_forever(self) -> None:
        while not self._stop.is_set():
            connection = self._listener.accept()
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
                self._state = request.get("state")
                self._revision += 1
                self._record_event("publish", request)
                return {"status": "ok", "revision": self._revision}
            if operation == "status":
                self._revision += 1
                self._record_event("status", request)
                return {"status": "ok", "revision": self._revision}
            if operation == "update_file":
                if self._state is None or self._updater is None:
                    return {"status": "error", "error": "live_state_unavailable"}
                result = self._updater(self._state, str(request.get("file_path", "")))
                self._revision += 1
                self._record_event("update_file", request, result)
                return {"status": "ok", "revision": self._revision, "result": result}
            if operation == "get_events":
                after_revision = request.get("after_revision")
                limit = request.get("limit", 20)
                events = self._events
                if isinstance(after_revision, int) and not isinstance(after_revision, bool):
                    events = [event for event in events if event["revision"] > after_revision]
                total = len(events)
                selected = events if limit is None else events[:max(0, int(limit))]
                return {
                    "status": "ok", "revision": self._revision,
                    "events": selected, "total": total,
                    "truncated": len(selected) < total,
                }
            if operation == "shutdown":
                self._stop.set()
                return {"status": "ok", "revision": self._revision}
            return {"status": "error", "error": "unknown_operation"}

    def close(self) -> None:
        if self._stop.is_set():
            return
        try:
            LiveStateClient(self.endpoint).request("shutdown")
        finally:
            self._stop.set()
            self._listener.close()


class LiveStateClient:
    """Small synchronous client used by desktop watcher and MCP adapters."""

    def __init__(self, endpoint: LiveEndpoint):
        self.endpoint = endpoint

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

    def get_events(self, *, after_revision: int | None = None, limit: int | None = 20) -> dict[str, Any]:
        return self.request("get_events", after_revision=after_revision, limit=limit)

    def status(self, message: str, *, origin: str = "unknown") -> dict[str, Any]:
        return self.request("status", message=message, origin=origin)
