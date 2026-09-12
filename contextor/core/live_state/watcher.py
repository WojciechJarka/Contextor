"""Desktop-side file watcher that submits changed Python files to LIVE IPC."""

from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from .ipc import LiveStateClient


@dataclass(frozen=True)
class _PendingMutationIntent:
    idempotency_key: str
    path: str
    trace_op: str
    observed_state: tuple[int, int] | None
    started_at: float


@dataclass(frozen=True)
class _WatcherMutationJob:
    job_id: str
    path: str
    trace_op: str
    idempotency_key: str
    observed_state: tuple[int, int] | None
    started_at: float


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


class _LiveFilesystemEventHandler(FileSystemEventHandler):
    def __init__(self, enqueue: Callable[[str], None]):
        super().__init__()
        self._enqueue = enqueue

    def on_created(self, event) -> None:
        if not event.is_directory:
            self._enqueue(event.src_path)

    def on_modified(self, event) -> None:
        if not event.is_directory:
            self._enqueue(event.src_path)

    def on_deleted(self, event) -> None:
        if not event.is_directory:
            self._enqueue(event.src_path)

    def on_moved(self, event) -> None:
        if not event.is_directory:
            self._enqueue(event.src_path)
            self._enqueue(event.dest_path)


class DesktopLiveWatcher:
    def __init__(
        self,
        root: str | Path,
        client: LiveStateClient,
        *,
        owner_pid: int | None = None,
        owner_token: str | None = None,
        desktop_instance_id: str | None = None,
        interval: float = 0.10,
        on_status: Callable[[str], None] | None = None,
        on_reconnect: Callable[[LiveStateClient], None] | None = None,
        on_resync: Callable[[], object] | None = None,
    ):
        """Watch one repository and route filesystem changes through LIVE.

        ``interval`` is the event debounce/coalescing interval, not a
        filesystem polling cadence.
        """
        self.root = Path(root).resolve()
        self.client = client
        self.owner_pid = owner_pid
        self.owner_token = owner_token
        self.desktop_instance_id = desktop_instance_id
        self.interval = max(0.0, float(interval))
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._observer = None
        self._observer_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._pending_paths: deque[str] = deque()
        self._pending_set: set[str] = set()
        self._using_polling_fallback = False
        self.on_status = on_status
        self.on_reconnect = on_reconnect
        self.on_resync = on_resync
        self._startup_requires_resync = False
        self._startup_resync_attempted = False
        self._ambiguous_updates: set[str] = set()
        self._pending_intents: dict[str, _PendingMutationIntent] = {}
        self._inflight_updates: OrderedDict[str, _WatcherMutationJob] = OrderedDict()
        self._excluded_paths, self._ignored_dirs = self._load_watch_filters()
        self._snapshot = self._scan()
        self._startup_pending = self._startup_reconciliation_paths(self._snapshot)
        self._event_handler = _LiveFilesystemEventHandler(self._enqueue_path)

    def _observer_timeout(self) -> float:
        return max(2.0, self.interval * 2)

    def _dispose_observer(self, observer) -> None:
        if observer is None:
            return
        try:
            observer.stop()
        except (OSError, RuntimeError):
            pass
        try:
            observer.join(timeout=self._observer_timeout())
        except (OSError, RuntimeError):
            pass

    def _reconcile_observer_start(self) -> None:
        current = self._scan()
        paths: list[str] = []
        seen: set[str] = set()

        def add(path: str) -> None:
            if path not in seen:
                seen.add(path)
                paths.append(path)

        for path in self._startup_pending:
            add(path)
        for path in list(self._snapshot) + list(current):
            if self._snapshot.get(path) != current.get(path):
                add(path)
        for path in self._startup_reconciliation_paths(current):
            add(path)
        for path in paths:
            self._enqueue_path(path)
        self._startup_pending = []

    def _start_native_observer(self):
        observer = None
        try:
            observer = Observer()
            observer.schedule(self._event_handler, str(self.root), recursive=True)
            observer.start()
        except (OSError, RuntimeError) as exc:
            self._dispose_observer(observer)
            try:
                observer = PollingObserver(timeout=max(1.0, self.interval))
                observer.schedule(self._event_handler, str(self.root), recursive=True)
                observer.start()
            except (OSError, RuntimeError) as fallback_exc:
                self._dispose_observer(observer)
                self._emit(
                    "LIVE filesystem observer unavailable; polling fallback failed: "
                    f"{fallback_exc}"
                )
                raise
            self._using_polling_fallback = True
            self._emit("LIVE filesystem observer unavailable; using polling fallback")
        else:
            self._using_polling_fallback = False
        with self._observer_lock:
            self._observer = observer

    def _switch_to_polling_fallback(self, reason: str) -> None:
        if self._stop.is_set() or self._using_polling_fallback:
            return
        with self._observer_lock:
            observer = self._observer
            self._observer = None
        self._dispose_observer(observer)
        try:
            fallback = PollingObserver(timeout=max(1.0, self.interval))
            fallback.schedule(self._event_handler, str(self.root), recursive=True)
            fallback.start()
        except (OSError, RuntimeError) as exc:
            self._dispose_observer(locals().get("fallback"))
            self._emit(
                "LIVE filesystem observer unavailable; polling fallback failed: "
                f"{exc}"
            )
            raise
        with self._observer_lock:
            self._observer = fallback
        self._using_polling_fallback = True
        self._emit(
            "LIVE filesystem observer stopped; using polling fallback: "
            f"{reason}"
        )
        self._reconcile_observer_start()

    def _check_observer_health(self) -> None:
        if self._stop.is_set() or self._using_polling_fallback:
            return
        with self._observer_lock:
            observer = self._observer
        if observer is None:
            return
        try:
            alive = observer.is_alive()
        except (OSError, RuntimeError):
            alive = False
        if not alive:
            self._switch_to_polling_fallback("native observer stopped unexpectedly")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        try:
            self._start_native_observer()
            self._reconcile_observer_start()
        except Exception:
            with self._observer_lock:
                observer = self._observer
                self._observer = None
            self._dispose_observer(observer)
            raise
        self._thread = threading.Thread(
            target=self._run_event_worker,
            name="contextor-live-watcher",
            daemon=True,
        )
        self._thread.start()

    def _run_event_worker(self) -> None:
        while not self._stop.is_set():
            signaled = self._wake.wait(1.0)
            if self._stop.is_set():
                break
            if signaled:
                if self._stop.wait(self.interval):
                    break
            else:
                try:
                    self._check_observer_health()
                except (OSError, RuntimeError, EOFError) as exc:
                    self._handle_poll_error(exc)
            if self._has_pending_paths() or self._has_inflight_updates():
                try:
                    self.poll_once()
                except (OSError, RuntimeError, EOFError) as exc:
                    self._handle_poll_error(exc)
                if signaled:
                    try:
                        self._check_observer_health()
                    except (OSError, RuntimeError, EOFError) as exc:
                        self._handle_poll_error(exc)

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        timeout = self._observer_timeout()
        with self._observer_lock:
            observer = self._observer
        if observer is not None:
            try:
                observer.stop()
            except (OSError, RuntimeError):
                pass
            try:
                observer.join(timeout=timeout)
            except (OSError, RuntimeError):
                pass
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        with self._observer_lock:
            if self._observer is observer:
                self._observer = None
        self._thread = None
        self._using_polling_fallback = False

    def _emit(self, message: str) -> None:
        """Forward a compact status message without assuming a GUI exists."""
        if self.on_status is not None:
            self.on_status(message)

    def _recover_client(self, trigger_exc: BaseException | None = None) -> LiveStateClient | None:
        """Attempt to reconnect or restart LIVE on genuine connection failure."""
        started = time.monotonic()
        prior_endpoint = getattr(self.client, "endpoint", None)
        try:
            from contextor.core.runtime_trace import new_trace_operation, trace_event

            recovery_operation_id = new_trace_operation("wr")
            trace_event(
                "LIVE", "LIVE_WATCHER_RECOVERY_START", op=recovery_operation_id,
                reason="connection_failure",
                prior_endpoint_fingerprint=(prior_endpoint.fingerprint() if prior_endpoint is not None else None),
                prior_service_pid=getattr(prior_endpoint, "pid", None),
                recovery_operation_id=recovery_operation_id,
                exception_class=(type(trigger_exc).__name__ if trigger_exc is not None else None),
                errno=(getattr(trigger_exc, "errno", None) if trigger_exc is not None else None),
                winerror=(getattr(trigger_exc, "winerror", None) if trigger_exc is not None else None),
                error=(str(trigger_exc)[:500] if trigger_exc is not None else None),
            )
        except Exception:
            recovery_operation_id = None
        try:
            from .runtime import connect_or_start

            new_client = connect_or_start(
                self.root,
                owner_pid=self.owner_pid,
                owner_token=self.owner_token,
                desktop_instance_id=self.desktop_instance_id,
                client_kind="desktop" if self.desktop_instance_id is not None else "protocol",
                timeout=10.0,
            )
            self.client = new_client
            if self.on_reconnect is not None:
                self.on_reconnect(new_client)
            try:
                from contextor.core.runtime_trace import trace_event

                new_endpoint = new_client.endpoint
                trace_event(
                    "LIVE", "LIVE_WATCHER_RECOVERY_RESULT", op=recovery_operation_id,
                    result=(
                        "reconnected_same_endpoint"
                        if prior_endpoint is not None and new_endpoint == prior_endpoint
                        else "connected_changed_endpoint"
                    ),
                    new_endpoint_fingerprint=new_endpoint.fingerprint(),
                    new_service_pid=new_endpoint.pid,
                    lease_generation=new_endpoint.lease_generation,
                    elapsed_ms=(time.monotonic() - started) * 1000.0,
                    recovery_operation_id=recovery_operation_id,
                )
            except Exception:
                pass
            return new_client
        except Exception as exc:
            try:
                from contextor.core.runtime_trace import trace_event

                trace_event(
                    "LIVE", "LIVE_WATCHER_RECOVERY_RESULT", op=recovery_operation_id,
                    result="failed",
                    elapsed_ms=(time.monotonic() - started) * 1000.0,
                    exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
                    winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
                    recovery_operation_id=recovery_operation_id,
                )
            except Exception:
                pass
            self._emit(f"LIVE recovery failed: {exc}")
            return None

    def _normalize_watch_path(self, raw_path: str | Path) -> str | None:
        try:
            path = Path(raw_path).resolve()
            relative = path.relative_to(self.root)
        except (OSError, ValueError):
            return None
        if path.suffix != ".py":
            return None
        if any(part in self._ignored_dirs for part in relative.parts):
            return None
        relative_path = relative.as_posix()
        if any(
            relative_path == excluded
            or relative_path.startswith(excluded + "/")
            for excluded in self._excluded_paths
        ):
            return None
        return str(path)

    def _enqueue_path(self, raw_path: str | Path, *, wake: bool = True) -> None:
        path = self._normalize_watch_path(raw_path)
        if path is None:
            return
        with self._pending_lock:
            if path in self._pending_set:
                return
            self._pending_paths.append(path)
            self._pending_set.add(path)
            if wake:
                self._wake.set()

    def _drain_pending(self) -> list[str]:
        with self._pending_lock:
            paths = list(self._pending_paths)
            self._pending_paths.clear()
            self._pending_set.clear()
            self._wake.clear()
            return paths

    def _has_pending_paths(self) -> bool:
        with self._pending_lock:
            return bool(self._pending_paths)

    def _has_inflight_updates(self) -> bool:
        return bool(self._inflight_updates)

    def _requeue_paths(self, paths: list[str] | set[str]) -> None:
        for path in paths:
            self._enqueue_path(path, wake=False)

    def _scan(self) -> dict[str, tuple[int, int]]:
        result = {}
        for path in self.root.rglob("*.py"):
            normalized = self._normalize_watch_path(path)
            if normalized is None:
                continue
            try:
                stat = Path(normalized).stat()
                result[normalized] = (stat.st_mtime_ns, stat.st_size)
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
            normalized = self._normalize_watch_path(tracked_path)
            if normalized is not None and normalized not in current:
                pending.add(normalized)
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
        trusted_manager=None,
    ) -> bool | None:
        """Revalidate a queued path against the generation held after the lease wait."""
        if snapshot is None:
            try:
                snapshot = self.client.snapshot()
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                return None
        manager = trusted_manager if trusted_manager is not None else self._trusted_file_state(snapshot)
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

    def _poll_inflight_updates(self) -> list[str]:
        completed: list[str] = []
        for job_id, job in list(self._inflight_updates.items()):
            try:
                status = self.client.mutation_status(job_id)
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                recovered = self._recover_client(exc)
                if recovered is None:
                    continue
                try:
                    status = self.client.mutation_status(job_id)
                except (OSError, EOFError, TimeoutError, ConnectionError):
                    continue
            state = status.get("state") if isinstance(status, dict) else None
            if state in {"queued", "running"}:
                continue
            self._inflight_updates.pop(job_id, None)
            if state == "completed":
                response = status.get("response")
                result = response.get("result") if isinstance(response, dict) else None
                result_status = getattr(result, "status", None)
                if isinstance(response, dict) and response.get("status") == "ok" and result_status in {"UPDATED", "DELETED", "UNCHANGED", "RECOVERED", "SYNTAX_ERROR"}:
                    if job.observed_state is None:
                        self._snapshot.pop(job.path, None)
                    else:
                        self._snapshot[job.path] = job.observed_state
                    completed.append(job.path)
                    from contextor.core.runtime_trace import trace_event
                    try:
                        relative = Path(job.path).resolve().relative_to(self.root).as_posix()
                    except ValueError:
                        relative = job.path
                    trace_event("LIVE", "WATCH_UPDATE_END", op=job.trace_op, repo=str(self.root), path=relative, rev=response.get("revision"), seq=response.get("seq"), status=result_status, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0)
                    if result_status == "SYNTAX_ERROR":
                        line = getattr(result, "line_number", None)
                        column = getattr(result, "column_number", None)
                        position = f" line {line}, column {column}" if line and column else ""
                        self._emit(f"LIVE syntax error: {Path(job.path).name}{position}: {getattr(result, 'error', 'syntax error')}")
                    elif result_status == "RECOVERED":
                        self._emit(f"LIVE syntax recovery: {Path(job.path).name}")
                    else:
                        self._emit(f"LIVE update successful: {Path(job.path).name}")
                    continue
            if isinstance(status, dict) and status.get("error") in {"unknown_mutation_job", "invalid_mutation_job_id"}:
                self._ambiguous_updates.add(job.path)
                self._pending_intents.setdefault(
                    job.path,
                    _PendingMutationIntent(
                        idempotency_key=job.idempotency_key,
                        path=job.path,
                        trace_op=job.trace_op,
                        observed_state=job.observed_state,
                        started_at=job.started_at,
                    ),
                )
            from contextor.core.runtime_trace import trace_event
            try:
                relative = Path(job.path).resolve().relative_to(self.root).as_posix()
            except ValueError:
                relative = job.path
            trace_event(
                "LIVE", "WATCH_UPDATE_FAIL", op=job.trace_op, repo=str(self.root),
                path=relative, elapsed_ms=(time.monotonic() - job.started_at) * 1000.0,
                err=(status.get("error", "malformed mutation status") if isinstance(status, dict) else "malformed mutation status"),
            )
            self._requeue_paths([job.path])
            self._emit(f"LIVE update failed; deferring watcher update: {Path(job.path).name}")
        return completed

    def poll_once(self) -> list[str]:
        reconciled = self._poll_inflight_updates()
        changed = self._drain_pending()
        if not changed and self._startup_pending:
            changed = list(self._startup_pending)
            self._startup_pending = []
        if not changed and not self._startup_requires_resync:
            return reconciled
        current: dict[str, tuple[int, int]] = {}
        for path in changed:
            try:
                stat = Path(path).stat()
                current[path] = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue
        ping_started = time.monotonic()
        try:
            status = self.client.ping()
        except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
            self._emit("LIVE: connection lost; recovering...")
            if self._recover_client(exc) is None:
                raise
            status = self.client.ping()
        ping_ms = (time.monotonic() - ping_started) * 1000.0

        if not status.get("available"):
            self._requeue_paths(changed)
            self._emit("LIVE: no snapshot; waiting for analysis")
            return reconciled
        if self._startup_requires_resync:
            if self._startup_resync_attempted:
                return reconciled
            self._startup_resync_attempted = True
            if self.on_resync is None:
                self._emit("LIVE: canonical baseline requires resync")
                return reconciled
            try:
                outcome = self.on_resync()
                if not self._resync_completed(outcome):
                    self._emit("LIVE: startup resync failed; baseline remains untrusted")
                    return []
            except Exception as exc:
                self._emit(f"LIVE: startup resync failed: {exc}")
                return reconciled
            current = self._scan()
            try:
                snapshot = self.client.snapshot()
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                self._emit("LIVE: startup resync baseline could not be verified")
                return reconciled
            if self._trusted_file_state(snapshot) is None:
                self._emit("LIVE: startup resync baseline remains untrusted")
                return []
            self._snapshot = current
            self._startup_pending = self._startup_reconciliation_paths(current)
            self._startup_requires_resync = False
            self._requeue_paths(self._startup_pending)
            return reconciled
        deferred: list[str] = []
        try:
            batch_snapshot = self.client.snapshot()
        except (OSError, EOFError, TimeoutError, ConnectionError):
            self._requeue_paths(changed)
            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
            return reconciled
        batch_manager = self._trusted_file_state(batch_snapshot)
        if batch_manager is None:
            self._requeue_paths(changed)
            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
            return reconciled

        try:
            candidate_decisions = {
                path: self._candidate_requires_update(
                    path, current, batch_snapshot, batch_manager
                )
                for path in changed
            }
        except (OSError, EOFError, TimeoutError, ConnectionError):
            self._requeue_paths(changed)
            self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
            return reconciled

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
                discovery="watchdog", ping_ms=ping_ms, mtime_ns=mtime_ns,
            )
            self._emit(f"Updating LIVE: {Path(path).name}")
            update_started = time.monotonic()
            trace_event("LIVE", "WATCH_UPDATE_START", op=op, repo=str(self.root), path=relative)
            was_ambiguous = path in self._ambiguous_updates
            try:
                candidate_requires_update = candidate_decisions[path]
                if candidate_requires_update is None:
                    deferred.append(path)
                    if was_ambiguous:
                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                    continue
                if not candidate_requires_update:
                    self._pending_intents.pop(path, None)
                    if was_ambiguous:
                        self._ambiguous_updates.discard(path)
                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=False)
                    if path in current:
                        self._snapshot[path] = current[path]
                    else:
                        self._snapshot.pop(path, None)
                    reconciled.append(path)
                    continue
                if any(
                    job.path == path and job.observed_state == current.get(path)
                    for job in self._inflight_updates.values()
                ):
                    continue
                pending_intent = self._pending_intents.get(path)
                if pending_intent is None:
                    pending_intent = _PendingMutationIntent(
                        idempotency_key=uuid.uuid4().hex,
                        path=path,
                        trace_op=op,
                        observed_state=current.get(path),
                        started_at=update_started,
                    )
                    self._pending_intents[path] = pending_intent
                if was_ambiguous:
                    self._ambiguous_updates.discard(path)
                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=pending_intent.trace_op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=True)
                response = self.client.submit_update_file(
                    path,
                    origin="desktop_watcher",
                    trace_op=pending_intent.trace_op,
                    idempotency_key=pending_intent.idempotency_key,
                )
            except (OSError, EOFError, TimeoutError, ConnectionError) as exc:
                self._ambiguous_updates.add(path)
                trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
                deferred.append(path)
                continue
            job_id = response.get("job_id") if isinstance(response, dict) else None
            if (
                not isinstance(response, dict)
                or response.get("status") != "accepted"
                or response.get("accepted") is not True
                or not isinstance(job_id, str)
                or not job_id
            ):
                deferred.append(path)
                self._emit("LIVE: update submission was not accepted; deferring watcher update")
                continue
            self._pending_intents.pop(path, None)
            self._inflight_updates[job_id] = _WatcherMutationJob(
                job_id,
                pending_intent.path,
                pending_intent.trace_op,
                pending_intent.idempotency_key,
                pending_intent.observed_state,
                pending_intent.started_at,
            )
            if current.get(path) != pending_intent.observed_state:
                deferred.append(path)
        if deferred:
            self._requeue_paths(deferred)
        self._startup_pending = []
        return reconciled + self._poll_inflight_updates()

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
        self._replayed_authority_keys: set[tuple[str, int, str]] = set()
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

    def replay_authority_events(self) -> None:
        """Show bounded durable authority history before advancing the live cursor."""
        try:
            response = self.client.get_events(
                after_seq=0,
                category="AUTHORITY",
                limit=None,
            )
        except (OSError, EOFError, TimeoutError, ConnectionError):
            return
        if response.get("status") != "ok":
            return
        for event in response.get("events", []):
            if not isinstance(event, dict):
                continue
            message = self._message(event)
            if message:
                self._emit_status(message, event)
            key = self._authority_key(event)
            if key is not None:
                self._replayed_authority_keys.add(key)
        current_epoch = response.get("activity_epoch")
        if current_epoch is not None:
            self._activity_epoch = str(current_epoch)

    @staticmethod
    def _authority_key(event: dict) -> tuple[str, int, str] | None:
        domain, sequence, event_id = event.get("runtime_domain_id"), event.get("sequence"), event.get("event_id")
        if isinstance(domain, str) and isinstance(sequence, int) and isinstance(event_id, str):
            return domain, sequence, event_id
        return None

    @staticmethod
    def _diagnostic_detail(item: object) -> str | None:
        if not isinstance(item, dict):
            return None
        action = item.get("action")
        kind = item.get("diagnostic_kind")
        if action not in {"ADDED", "RESOLVED"}:
            return None
        verb = "added" if action == "ADDED" else "resolved"
        if kind == "syntax":
            source_path = item.get("source_path")
            line = item.get("line_number")
            column = item.get("column_number")
            if (
                not isinstance(source_path, str)
                or not source_path
                or (line is not None and (not isinstance(line, int) or isinstance(line, bool)))
                or (column is not None and (not isinstance(column, int) or isinstance(column, bool)))
            ):
                return None
            return f"syntax error {verb}: {source_path}:{line}:{column}"
        if kind == "collision":
            symbol = item.get("collision_symbol")
            nodes = item.get("collision_nodes")
            if (
                not isinstance(symbol, str)
                or not symbol
                or not isinstance(nodes, (list, tuple))
                or not nodes
                or not all(isinstance(node, str) and node for node in nodes)
            ):
                return None
            return f"collision {verb}: {symbol} [{', '.join(nodes)}]"
        if kind == "cycle":
            nodes = item.get("cycle_nodes")
            if (
                not isinstance(nodes, (list, tuple))
                or not nodes
                or not all(isinstance(node, str) and node for node in nodes)
            ):
                return None
            return f"cycle {verb}: {' -> '.join(nodes)}"
        return None

    @classmethod
    def _format_diagnostic_payload(
        cls, payload: object, *, suppress_syntax: bool = False
    ) -> str | None:
        if not isinstance(payload, dict):
            return None
        items = payload.get("items")
        total = payload.get("total")
        if (
            not isinstance(items, (list, tuple))
            or not isinstance(total, int)
            or isinstance(total, bool)
            or total < len(items)
        ):
            return None
        details = []
        for item in items:
            if suppress_syntax and isinstance(item, dict) and item.get("diagnostic_kind") == "syntax":
                continue
            detail = cls._diagnostic_detail(item)
            if detail is not None:
                details.append(detail)
        if total > len(items):
            details.append(f"+{total - len(items)} more")
        return "; ".join(details) if details else None

    def _message(self, event: dict) -> str | None:
        category = event.get("category", "LIVE_STATE")
        if category == "AUTHORITY":
            event_type = str(event.get("event_type") or event.get("operation") or "AUTHORITY_EVENT")
            status = event.get("status") or "DURABLE_COMMITTED"
            sequence = event.get("sequence")
            suffix = f" (event {sequence})" if isinstance(sequence, int) else ""
            return f"[LIVE] Authority {event_type}: {status}{suffix}"
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
            diagnostic_payload = event.get("diagnostic_changes")
            if status == "SYNTAX_ERROR":
                err = event.get("error", "syntax error")
                line = event.get("line_number")
                col = event.get("column_number")
                pos = f" line {line}, column {col}" if line and col else ""
                message = f"[LIVE] Syntax error in {file_name}{pos}: {err}"
            elif status == "RECOVERED":
                message = f"[LIVE] Syntax recovered in {file_name}{rev_str}"
            else:
                message = None
            if message is not None:
                details = self._format_diagnostic_payload(
                    diagnostic_payload, suppress_syntax=True
                )
                return f"{message}; {details}" if details else message
            details = self._format_diagnostic_payload(diagnostic_payload)
            if details:
                return f"[LIVE] Diagnostics after {file_name} (rev {rev}): {details}"
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

                    key = self._authority_key(event) if event.get("category") == "AUTHORITY" else None
                    message = None if key is not None and key in self._replayed_authority_keys else self._message(event)
                    if message:
                        self._emit_status(message, event)

                    if isinstance(seq, int):
                        self._last_seq = seq
                        if key is not None:
                            self._replayed_authority_keys.discard(key)

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
