"""Desktop-side file watcher that submits changed Python files to LIVE IPC."""

from __future__ import annotations

import threading
from pathlib import Path

from .ipc import LiveStateClient


class DesktopLiveWatcher:
    def __init__(self, root: str | Path, client: LiveStateClient, *, interval: float = 0.75):
        self.root = Path(root).resolve()
        self.client = client
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshot = self._scan()

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
            return []
        changed = sorted(
            path for path in set(self._snapshot) | set(current)
            if self._snapshot.get(path) != current.get(path)
        )
        for path in changed:
            response = self.client.update_file(path, origin="desktop_watcher")
            if response.get("status") != "ok":
                raise RuntimeError(f"LIVE update failed for {path}: {response.get('error')}")
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
            except (OSError, RuntimeError, EOFError):
                continue

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(2.0, self.interval * 2))
