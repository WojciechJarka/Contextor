"""Desktop-side file watcher that submits changed Python files to LIVE IPC."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from .ipc import LiveStateClient


class DesktopLiveWatcher:
    def __init__(
        self,
        root: str | Path,
        client: LiveStateClient,
        *,
        interval: float = 0.75,
        on_status: Callable[[str], None] | None = None,
    ):
        self.root = Path(root).resolve()
        self.client = client
        self.interval = interval
        self.on_status = on_status
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshot = self._scan()

    def _emit(self, message: str) -> None:
        """Forward a compact status message without assuming a GUI exists."""
        if self.on_status is not None:
            self.on_status(message)

    def _scan(self) -> dict[str, tuple[int, int]]:
        result = {}
        for path in self.root.rglob("*.py"):
            if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
                continue
            try:
                stat = path.stat()
                result[str(path)] = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue
        return result

    def poll_once(self) -> list[str]:
        current = self._scan()
        status = self.client.ping()
        if not status.get("available"):
            self._snapshot = current
            self._emit("LIVE: no snapshot; waiting for analysis")
            return []
        changed = sorted(
            path for path in set(self._snapshot) | set(current)
            if self._snapshot.get(path) != current.get(path)
        )
        for path in changed:
            self._emit(f"Updating LIVE: {Path(path).name}")
            response = self.client.update_file(path, origin="desktop_watcher")
            if response.get("status") != "ok":
                self._emit(f"LIVE connection error: {response.get('error', 'update failed')}")
                raise RuntimeError(f"LIVE update failed for {path}: {response.get('error')}")
            result = response.get("result")
            result_status = getattr(result, "status", "UPDATED")
            if result_status == "SYNTAX_ERROR":
                line = getattr(result, "line_number", None)
                column = getattr(result, "column_number", None)
                error = getattr(result, "error", "syntax error")
                position = f" line {line}, column {column}" if line and column else ""
                self._emit(f"LIVE syntax error: {Path(path).name}{position}: {error}")
            elif result_status in {"UPDATED", "DELETED", "UNCHANGED"}:
                self._emit(f"LIVE update successful: {Path(path).name}")
            else:
                self._emit(f"LIVE update error: {Path(path).name}: {result_status}")
        self._snapshot = current
        return changed

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="contextor-live-watcher", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.poll_once()
            except (OSError, RuntimeError, EOFError) as exc:
                self._emit(f"LIVE connection error: {exc}")
                continue

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(2.0, self.interval * 2))


class DesktopLiveEventFeed:
    """Forward queued MCP-origin LIVE events to the desktop status callback."""

    def __init__(self, client: LiveStateClient, on_status: Callable[[str], None], *, interval: float = 0.75):
        self.client = client
        self.on_status = on_status
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._revision = int(client.ping().get("revision", 0))

    def _message(self, event: dict) -> str | None:
        if event.get("origin") not in {"mcp", "mcp_analysis"}:
            return None
        if event.get("operation") == "status":
            return str(event.get("message", "MCP: LIVE activity"))
        if event.get("operation") == "publish" and event.get("origin") == "mcp_analysis":
            return "MCP: analysis published shared LIVE state"
        return None

    def poll_once(self) -> None:
        response = self.client.get_events(after_revision=self._revision, limit=100)
        if response.get("status") != "ok":
            return
        for event in response.get("events", []):
            message = self._message(event)
            if message:
                self.on_status(message)
        self._revision = int(response.get("revision", self._revision))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="contextor-live-event-feed", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.poll_once()
            except (OSError, RuntimeError, EOFError):
                continue

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(2.0, self.interval * 2))
