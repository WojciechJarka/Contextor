"""Desktop-side file watcher that submits changed Python files to LIVE IPC."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from .ipc import LiveStateClient


class _PollingLiveWorker:
    """Shared lifecycle for small, fault-tolerant desktop LIVE pollers.

    Subclasses implement :meth:`poll_once` and may override
    :meth:`_handle_poll_error`.  The worker intentionally owns no IPC or GUI
    policy, so the file watcher and MCP event feed retain their distinct
    behaviour while sharing the threading contract.
    """

    def __init__(self, *, interval: float, thread_name: str):
        self.interval = interval
        self._thread_name = thread_name
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def poll_once(self) -> object:
        """Perform one polling iteration."""
        raise NotImplementedError

    def _handle_poll_error(self, _exc: OSError | RuntimeError | EOFError) -> None:
        """Keep polling after a transient failure by default."""

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=self._thread_name, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.poll_once()
            except (OSError, RuntimeError, EOFError) as exc:
                self._handle_poll_error(exc)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(2.0, self.interval * 2))


class DesktopLiveWatcher(_PollingLiveWorker):
    def __init__(
        self,
        root: str | Path,
        client: LiveStateClient,
        *,
        owner_pid: int | None = None,
        owner_token: str | None = None,
        interval: float = 0.75,
        on_status: Callable[[str], None] | None = None,
        on_reconnect: Callable[[LiveStateClient], None] | None = None,
    ):
        self.root = Path(root).resolve()
        self.client = client
        self.owner_pid = owner_pid
        self.owner_token = owner_token
        super().__init__(interval=interval, thread_name="contextor-live-watcher")
        self.on_status = on_status
        self.on_reconnect = on_reconnect
        self._excluded_paths, self._ignored_dirs = self._load_watch_filters()
        self._snapshot = self._scan()
        self._startup_pending = self._startup_reconciliation_paths(self._snapshot)

    def _emit(self, message: str) -> None:
        """Forward a compact status message without assuming a GUI exists."""
        if self.on_status is not None:
            self.on_status(message)

    def _recover_client(self) -> LiveStateClient | None:
        """Attempt to reconnect or restart LIVE on genuine connection failure."""
        try:
            from .runtime import connect_or_start

            new_client = connect_or_start(
                self.root,
                owner_pid=self.owner_pid,
                owner_token=self.owner_token,
                timeout=10.0,
            )
            self.client = new_client
            if self.on_reconnect is not None:
                self.on_reconnect(new_client)
            return new_client
        except Exception as exc:
            self._emit(f"LIVE recovery failed: {exc}")
            return None

    def _scan(self) -> dict[str, tuple[int, int]]:
        result = {}
        for path in self.root.rglob("*.py"):
            relative = path.relative_to(self.root)
            if any(part in self._ignored_dirs for part in relative.parts):
                continue
            relative_path = relative.as_posix()
            if any(
                relative_path == excluded
                or relative_path.startswith(excluded + "/")
                for excluded in self._excluded_paths
            ):
                continue
            try:
                stat = path.stat()
                result[str(path)] = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue
        return result

    def _load_watch_filters(self) -> tuple[tuple[str, ...], frozenset[str]]:
        from contextor.core.api.facade import _analysis_filters

        excluded, ignored_dirs = _analysis_filters(str(self.root))
        normalized = tuple(
            sorted(
                str(item).replace("\\", "/").removeprefix("./").strip("/")
                for item in excluded
                if str(item).strip()
            )
        )
        return normalized, frozenset(ignored_dirs)

    def _startup_reconciliation_paths(
        self, current: dict[str, tuple[int, int]]
    ) -> list[str]:
        try:
            response = self.client.snapshot()
        except (OSError, EOFError, TimeoutError, ConnectionError):
            return []
        if response.get("status") != "ok" or response.get("state") is None:
            return []

        state = response["state"]
        modules = getattr(state, "modules", None)
        if not isinstance(modules, dict):
            return []

        from contextor.core.analysis.state_manager import FileStateManager
        from contextor.core.paths import repo_cache_dir

        manager = FileStateManager(str(repo_cache_dir(self.root)))
        pending = {
            path
            for path in current
            if manager.has_changed(path)
            or self._module_name(Path(path)) not in modules
        }
        for tracked_path in manager.tracked_paths():
            path = Path(tracked_path)
            try:
                relative = path.resolve().relative_to(self.root)
            except ValueError:
                continue
            relative_path = relative.as_posix()
            if (
                path.suffix == ".py"
                and tracked_path not in current
                and not any(part in self._ignored_dirs for part in relative.parts)
                and not any(
                    relative_path == excluded
                    or relative_path.startswith(excluded + "/")
                    for excluded in self._excluded_paths
                )
            ):
                pending.add(tracked_path)
        return sorted(pending)

    def _module_name(self, path: Path) -> str:
        relative = path.resolve().relative_to(self.root).with_suffix("")
        return ".".join(relative.parts)

    def poll_once(self) -> list[str]:
        current = self._scan()
        try:
            status = self.client.ping()
        except (OSError, EOFError, TimeoutError, ConnectionError):
            self._emit("LIVE: connection lost; recovering...")
            if self._recover_client() is None:
                raise
            status = self.client.ping()

        if not status.get("available"):
            self._snapshot = current
            self._emit("LIVE: no snapshot; waiting for analysis")
            return []
        startup_pending = set(self._startup_pending)
        if startup_pending:
            startup_pending &= set(self._startup_reconciliation_paths(current))
        changed = sorted(
            startup_pending
            | {
                path
                for path in set(self._snapshot) | set(current)
                if self._snapshot.get(path) != current.get(path)
            }
        )
        for path in changed:
            self._emit(f"Updating LIVE: {Path(path).name}")
            try:
                response = self.client.update_file(path, origin="desktop_watcher")
            except (OSError, EOFError, TimeoutError, ConnectionError):
                self._emit("LIVE: connection lost during update; recovering...")
                if self._recover_client() is None:
                    raise
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
            elif result_status == "RECOVERED":
                self._emit(f"LIVE syntax recovery: {Path(path).name}")
            elif result_status in {"UPDATED", "DELETED", "UNCHANGED"}:
                self._emit(f"LIVE update successful: {Path(path).name}")
            else:
                self._emit(f"LIVE update error: {Path(path).name}: {result_status}")
        self._snapshot = current
        self._startup_pending = []
        return changed

    def _handle_poll_error(self, exc: OSError | RuntimeError | EOFError) -> None:
        self._emit(f"LIVE connection error: {exc}")


class DesktopLiveEventFeed(_PollingLiveWorker):
    """Forward queued MCP-origin LIVE events to the desktop status callback."""

    def __init__(
        self,
        client: LiveStateClient,
        on_status: Callable[[str], None],
        *,
        interval: float = 0.75,
    ):
        self.client = client
        self.on_status = on_status
        super().__init__(interval=interval, thread_name="contextor-live-event-feed")
        try:
            self._revision = int(client.ping().get("revision", 0))
        except (OSError, EOFError, TimeoutError, ConnectionError):
            self._revision = 0

    def _message(self, event: dict) -> str | None:
        if event.get("origin") not in {"mcp", "mcp_analysis"}:
            return None
        if event.get("operation") == "status":
            return str(event.get("message", "MCP: LIVE activity"))
        if event.get("operation") == "publish" and event.get("origin") == "mcp_analysis":
            return "MCP: analysis published shared LIVE state"
        return None

    def poll_once(self) -> None:
        try:
            response = self.client.get_events(after_revision=self._revision, limit=100)
        except (OSError, EOFError, TimeoutError, ConnectionError):
            return
        if response.get("status") != "ok":
            return
        for event in response.get("events", []):
            message = self._message(event)
            if message:
                self.on_status(message)
        self._revision = int(response.get("revision", self._revision))
