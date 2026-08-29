"""Desktop-side file watcher that submits changed Python files to LIVE IPC."""

from __future__ import annotations

import threading
import time
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
        on_resync: Callable[[], object] | None = None,
    ):
        self.root = Path(root).resolve()
        self.client = client
        self.owner_pid = owner_pid
        self.owner_token = owner_token
        super().__init__(interval=interval, thread_name="contextor-live-watcher")
        self.on_status = on_status
        self.on_reconnect = on_reconnect
        self.on_resync = on_resync
        self._startup_requires_resync = False
        self._startup_resync_attempted = False
        self._ambiguous_updates: set[str] = set()
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

        manager = self._trusted_file_state(response)
        if manager is None:
            self._startup_requires_resync = True
            return []
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

    def _trusted_file_state(self, snapshot: dict | None = None):
        """Return the persisted baseline only when it matches LIVE's generation."""
        from contextor.core.analysis.state_manager import FileStateManager
        from contextor.core.paths import repo_cache_dir

        manager = FileStateManager(str(repo_cache_dir(self.root)))
        if getattr(manager, "baseline_status", "untrusted") != "trusted":
            return None
        state = (snapshot or {}).get("state") if isinstance(snapshot, dict) else None
        state_revision = getattr(state, "revision", None)
        state_id = getattr(state, "state_id", None)
        if state_revision is None or not state_id:
            return None
        if manager.revision != state_revision:
            return None
        if manager.state_id != state_id:
            return None
        return manager

    def _candidate_requires_update(
        self,
        path: str,
        current: dict[str, tuple[int, int]],
        snapshot: dict | None = None,
    ) -> bool | None:
        """Revalidate a queued path against the generation held after the lease wait."""
        if snapshot is None:
            try:
                snapshot = self.client.snapshot()
            except (OSError, EOFError, TimeoutError, ConnectionError):
                return None
        manager = self._trusted_file_state(snapshot)
        if manager is None:
            self._startup_requires_resync = True
            return None
        if path not in current:
            return path in manager.tracked_paths()
        state = snapshot.get("state")
        modules = getattr(state, "modules", {})
        return (
            manager.has_changed(path)
            or self._module_name(Path(path)) not in modules
        )

    @staticmethod
    def _resync_completed(outcome: object) -> bool:
        """`run_full_analysis_exclusive` returns ``(errors, analysis_result)``."""
        return (
            isinstance(outcome, tuple)
            and len(outcome) == 2
            and not outcome[0]
            and outcome[1] is not None
        )

    def _module_name(self, path: Path) -> str:
        relative = path.resolve().relative_to(self.root).with_suffix("")
        return ".".join(relative.parts)

    def poll_once(self) -> list[str]:
        scan_started = time.monotonic()
        current = self._scan()
        scan_ms = (time.monotonic() - scan_started) * 1000.0
        ping_started = time.monotonic()
        try:
            status = self.client.ping()
        except (OSError, EOFError, TimeoutError, ConnectionError):
            self._emit("LIVE: connection lost; recovering...")
            if self._recover_client() is None:
                raise
            status = self.client.ping()
        ping_ms = (time.monotonic() - ping_started) * 1000.0

        if not status.get("available"):
            self._snapshot = current
            self._emit("LIVE: no snapshot; waiting for analysis")
            return []
        if self._startup_requires_resync:
            if self._startup_resync_attempted:
                return []
            self._startup_resync_attempted = True
            if self.on_resync is None:
                self._emit("LIVE: canonical baseline requires resync")
                return []
            try:
                outcome = self.on_resync()
                if not self._resync_completed(outcome):
                    self._emit("LIVE: startup resync failed; baseline remains untrusted")
                    return []
            except Exception as exc:
                self._emit(f"LIVE: startup resync failed: {exc}")
                return []
            current = self._scan()
            try:
                snapshot = self.client.snapshot()
            except (OSError, EOFError, TimeoutError, ConnectionError):
                self._emit("LIVE: startup resync baseline could not be verified")
                return []
            if self._trusted_file_state(snapshot) is None:
                self._emit("LIVE: startup resync baseline remains untrusted")
                return []
            self._snapshot = current
            self._startup_pending = self._startup_reconciliation_paths(current)
            self._startup_requires_resync = False
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
        deferred: set[str] = set()
        reconciled: list[str] = []
        next_snapshot = dict(self._snapshot)

        def acknowledge(path: str) -> None:
            if path in current:
                next_snapshot[path] = current[path]
            else:
                next_snapshot.pop(path, None)

        for path in changed:
            from contextor.core.runtime_trace import new_trace_operation, trace_event

            op = new_trace_operation("u")
            old_present = path in self._snapshot
            current_present = path in current
            kind = "create" if not old_present and current_present else "delete" if old_present and not current_present else "modify"
            relative = None
            try:
                relative = Path(path).resolve().relative_to(self.root).as_posix()
            except ValueError:
                pass
            mtime_ns = current.get(path, (None, None))[0]
            trace_event(
                "LIVE", "FS_CHANGE_DETECTED", op=op, repo=str(self.root),
                path=relative, kind=kind, rev=status.get("revision"),
                scan_ms=scan_ms, ping_ms=ping_ms, mtime_ns=mtime_ns,
            )
            self._emit(f"Updating LIVE: {Path(path).name}")
            update_started = time.monotonic()
            trace_event("LIVE", "WATCH_UPDATE_START", op=op, repo=str(self.root), path=relative)
            lease = None
            was_ambiguous = path in self._ambiguous_updates
            update_attempted = False
            try:
                from contextor.core.analysis.full_analysis_coordinator import (
                    FullAnalysisBusyError,
                    acquire_full_analysis,
                    release_full_analysis,
                )
                lease = acquire_full_analysis(self.root, owner="desktop_watcher", timeout=10.0)
            except FullAnalysisBusyError:
                deferred.add(path)
                self._emit("LIVE: repository mutation busy; deferring watcher update")
                continue
            try:
                # A full analysis may have completed while this watcher waited.
                # Re-read its exact FileState generation before mutating LIVE.
                candidate_requires_update = self._candidate_requires_update(path, current)
                if candidate_requires_update is None:
                    deferred.add(path)
                    if was_ambiguous:
                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                    continue
                if not candidate_requires_update:
                    if was_ambiguous:
                        self._ambiguous_updates.discard(path)
                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=False)
                    acknowledge(path)
                    continue
                if was_ambiguous:
                    self._ambiguous_updates.discard(path)
                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=True)
                update_attempted = True
                response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
            except (OSError, EOFError, TimeoutError, ConnectionError):
                if update_attempted:
                    self._ambiguous_updates.add(path)
                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
                    deferred.add(path)
                    self._emit("LIVE: update outcome ambiguous; deferring revalidation")
                    continue
                self._emit("LIVE: connection lost during update; recovering...")
                if self._recover_client() is None:
                    # Earlier candidates in this poll may already have received
                    # an acknowledged canonical response.  Preserve those
                    # per-path advances before surfacing the later pre-send
                    # transport failure.
                    self._snapshot = next_snapshot
                    raise
                try:
                    recovered_snapshot = self.client.snapshot()
                except (OSError, EOFError, TimeoutError, ConnectionError):
                    deferred.add(path)
                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                    continue
                if self._trusted_file_state(recovered_snapshot) is None:
                    deferred.add(path)
                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                    continue
                candidate_requires_update = self._candidate_requires_update(
                    path, current, recovered_snapshot
                )
                if candidate_requires_update is None:
                    deferred.add(path)
                    if was_ambiguous:
                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                    continue
                if candidate_requires_update is False:
                    if was_ambiguous:
                        self._ambiguous_updates.discard(path)
                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=recovered_snapshot.get("revision"), retry=False)
                    acknowledge(path)
                    continue
                if was_ambiguous:
                    self._ambiguous_updates.discard(path)
                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=recovered_snapshot.get("revision"), retry=True)
                update_attempted = True
                response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
            finally:
                if lease is not None:
                    release_full_analysis(lease)

            if not isinstance(response, dict) or response.get("status") != "ok":
                error = response.get("error", "update failed") if isinstance(response, dict) else "malformed update response"
                trace_event("LIVE", "WATCH_UPDATE_FAIL", op=op, repo=str(self.root), path=relative, elapsed_ms=(time.monotonic() - update_started) * 1000.0, err=error)
                self._emit(f"LIVE connection error: {error}")
                raise RuntimeError(f"LIVE update failed for {path}: {error}")
            result = response.get("result")
            result_status = getattr(result, "status", None)
            trace_event("LIVE", "WATCH_UPDATE_END", op=op, repo=str(self.root), path=relative, rev=response.get("revision"), seq=response.get("seq"), status=result_status, elapsed_ms=(time.monotonic() - update_started) * 1000.0)
            acknowledged = result_status in {"UPDATED", "DELETED", "UNCHANGED", "RECOVERED", "SYNTAX_ERROR"}
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
            if not acknowledged:
                deferred.add(path)
                continue
            acknowledge(path)
            reconciled.append(path)
        if deferred:
            self._snapshot = next_snapshot
            self._startup_pending = sorted(deferred)
            return reconciled
        self._snapshot = next_snapshot
        self._startup_pending = []
        return reconciled

    def _handle_poll_error(self, exc: OSError | RuntimeError | EOFError) -> None:
        self._emit(f"LIVE connection error: {exc}")


class DesktopLiveEventFeed(_PollingLiveWorker):
    """Forward queued MCP-origin and canonical LIVE events to the desktop status callback."""

    def __init__(
        self,
        client: LiveStateClient,
        on_status: Callable[..., None],
        *,
        interval: float = 0.75,
        initial_seq: int | None = None,
    ):
        self.client = client
        self.on_status = on_status
        super().__init__(interval=interval, thread_name="contextor-live-event-feed")
        self._last_seq: int = 0
        self._activity_epoch: str | None = None
        self._poll_lock = threading.Lock()
        if initial_seq is not None:
            self._last_seq = int(initial_seq)
        else:
            try:
                resp = client.get_events(limit=1)
                self._last_seq = int(resp.get("latest_seq", 0))
                self._activity_epoch = resp.get("activity_epoch")
            except (OSError, EOFError, TimeoutError, ConnectionError):
                self._last_seq = 0

    def _emit_status(self, message: str, event: dict | None = None) -> None:
        import inspect
        try:
            sig = inspect.signature(self.on_status)
            if len(sig.parameters) >= 2 or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            ):
                self.on_status(message, event=event)
            else:
                self.on_status(message)
        except (TypeError, ValueError):
            self.on_status(message)

    def _message(self, event: dict) -> str | None:
        category = event.get("category", "LIVE_STATE")
        if category == "MCP_CALL":
            tool = event.get("tool", "")
            success = event.get("success", True)
            if not success:
                err = event.get("error", "failed")
                return f"[MCP] {tool} (failed: {err})"
            return f"[MCP] {tool}"

        origin = event.get("origin") or event.get("source")
        if origin not in {"mcp", "mcp_analysis", "desktop_analysis", "desktop_watcher", "desktop"}:
            return None
        if event.get("operation") == "status":
            if origin in {"mcp", "mcp_analysis"}:
                return str(event.get("message", "MCP: LIVE activity"))
            return None
        if event.get("operation") == "publish":
            rev = event.get("canonical_revision")
            rev_str = f" (rev {rev})" if rev is not None else ""
            if origin == "mcp_analysis":
                return f"MCP: analysis published shared LIVE state{rev_str}"
            elif origin == "desktop_analysis":
                return f"[LIVE] Desktop analysis published shared LIVE state{rev_str}"
            return f"[LIVE] Analysis published shared LIVE state{rev_str}"
        if event.get("operation") == "update_file":
            file_name = Path(event.get("file_path", "")).name
            rev = event.get("canonical_revision")
            rev_str = f" (rev {rev})" if rev is not None else ""
            status = event.get("status", "UPDATED")
            if status == "SYNTAX_ERROR":
                err = event.get("error", "syntax error")
                line = event.get("line_number")
                col = event.get("column_number")
                pos = f" line {line}, column {col}" if line and col else ""
                return f"[LIVE] Syntax error in {file_name}{pos}: {err}"
            elif status == "RECOVERED":
                return f"[LIVE] Syntax recovered in {file_name}{rev_str}"
            elif origin in {"desktop_watcher", "desktop"}:
                return f"[LIVE] Watcher updated {file_name}{rev_str}"
            elif origin in {"mcp", "mcp_update"}:
                return f"[LIVE] MCP updated {file_name}{rev_str}"
            return f"[LIVE] Updated {file_name}{rev_str}"
        return None

    def poll_once(self) -> None:
        if not self._poll_lock.acquire(blocking=False):
            return

        try:
            gap_reported = False

            while True:
                try:
                    response = self.client.get_events(
                        after_seq=self._last_seq,
                        limit=100,
                    )
                except (OSError, EOFError, TimeoutError, ConnectionError):
                    return

                if response.get("status") != "ok":
                    return

                current_epoch = response.get("activity_epoch")
                previous_epoch = self._activity_epoch
                if current_epoch is not None and previous_epoch is not None and current_epoch != previous_epoch:
                    previous_cursor = self._last_seq
                    self._activity_epoch = str(current_epoch)
                    self._last_seq = 0
                    try:
                        from contextor.core.runtime_trace import trace_event
                        trace_event(
                            "GUI", "ACTIVITY_EPOCH_RESET",
                            previous_cursor=previous_cursor,
                            expected_seq=previous_cursor + 1,
                            received_first_seq=response.get("earliest_retained_seq"),
                            received_last_seq=response.get("latest_seq"),
                            previous_epoch=previous_epoch,
                            current_epoch=current_epoch,
                        )
                    except Exception:
                        pass
                    continue
                if current_epoch is not None and self._activity_epoch is None:
                    self._activity_epoch = str(current_epoch)

                if response.get("activity_resync_required") and not gap_reported:
                    from datetime import datetime, timezone

                    self._emit_status(
                        "[LIVE] Activity stream gap detected; some status events were not retained",
                        event={
                            "category": "ACTIVITY",
                            "operation": "activity_gap",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    try:
                        from contextor.core.runtime_trace import trace_event
                        seqs = [item.get("seq") for item in response.get("events", []) if isinstance(item, dict) and isinstance(item.get("seq"), int)]
                        trace_event(
                            "GUI", "ACTIVITY_GAP", seq=response.get("latest_seq"), status="gap",
                            previous_cursor=self._last_seq,
                            expected_seq=self._last_seq + 1,
                            received_first_seq=min(seqs) if seqs else response.get("earliest_retained_seq"),
                            received_last_seq=max(seqs) if seqs else response.get("latest_seq"),
                            previous_epoch=self._activity_epoch,
                            current_epoch=response.get("activity_epoch"),
                        )
                    except Exception:
                        pass
                    gap_reported = True

                events = response.get("events", [])
                if events:
                    try:
                        from contextor.core.runtime_trace import trace_event
                        seqs = [item.get("seq") for item in events if isinstance(item, dict) and isinstance(item.get("seq"), int)]
                        trace_event("GUI", "EVENT_BATCH_RECEIVED", count=len(events), rev=response.get("revision"), seq=response.get("latest_seq"), first_seq=min(seqs) if seqs else None, last_seq=max(seqs) if seqs else None)
                    except Exception:
                        pass

                previous_cursor = self._last_seq

                for event in events:
                    seq = event.get("seq")

                    # Defensive duplicate protection.
                    if isinstance(seq, int) and seq <= self._last_seq:
                        continue

                    message = self._message(event)
                    if message:
                        self._emit_status(message, event)

                    if isinstance(seq, int):
                        self._last_seq = seq

                # No more pages.
                if not response.get("truncated", False):
                    break

                # Fail closed against an impossible/non-progressing page.
                # Never spin forever and never jump to latest_seq.
                if self._last_seq == previous_cursor:
                    from datetime import datetime, timezone

                    self._emit_status(
                        "[LIVE] Activity stream pagination stalled",
                        event={
                            "category": "ACTIVITY",
                            "operation": "activity_pagination_stalled",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    break

        finally:
            self._poll_lock.release()
