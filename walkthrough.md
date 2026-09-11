# Watchdog-backed DesktopLiveWatcher

STATUS=IMPLEMENTATION_PARTIAL
PASS_GATE=NOT_MET

## IMPLEMENTATION

- Replaced DesktopLiveWatcher steady-state repository polling with watchdog filesystem events.
- Added native Observer startup with explicit PollingObserver fallback.
- Added bounded startup/fallback reconciliation scan only; idle poll_once() does not scan.
- Coalesced and filtered accepted paths; MOVE queues source before destination.
- Preserved the existing update_file(origin="desktop_watcher") incremental LIVE update path, lease/recovery handling, deferred requeue, and diagnostic publication ownership.
- Kept _PollingLiveWorker unchanged for DesktopLiveEventFeed.

## INVARIANTS_PRESERVED

- Filesystem events still route through the canonical incremental LIVE update path before acknowledgement.
- Watcher does not compute syntax, collision, or dependency-cycle diagnostics.
- Existing syntax error/recovery status and event semantics are covered by the watchdog adapter test.
- No update_file, analyze_project, Desktop automation, full analysis, or full pytest was used.

## TEST_RESULTS

Required focused command:

    .\.venv\Scripts\python.exe -m pytest -q tests/test_live_watcher_watchdog.py tests/test_live_activity_status.py tests/test_live_state_ipc.py tests/test_collisions_live_lifecycle.py tests/test_refresh_plan_execution.py

Result: 135 passed, 3 failed, 1 warning in 129.38s.

The 3 failures are existing tests in the unallowed tests/test_live_state_ipc.py that call poll_once() after filesystem writes without enqueueing a watchdog event. They expect the removed steady-state repository scan and cannot be changed under this task's allowed-file boundary.

Additional verification:

- tests/test_live_watcher_watchdog.py: 10 passed.
- Targeted activity test: 1 passed.
- Watchdog/activity/collision/refresh subset: 37 passed, 1 warning.
- py_compile for changed Python files: passed.
- git diff --check: passed; Git emitted only LF/CRLF working-copy warnings.

## FILES_CHANGED

- contextor/core/live_state/watcher.py
- tests/test_live_activity_status.py
- tests/test_live_watcher_watchdog.py

## PREEXISTING_WORKTREE_CHANGES

- Requirements.txt
- pyproject.toml
- run_contextor.bat
- walkthrough.md

The dependency/launcher files above were pre-existing changes and were not modified in this task. walkthrough.md is excluded from FILES_CHANGED.

## COMPLETE FULL_DIFF

diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 50550eb..3eeeba2 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -4,9 +4,14 @@ from __future__ import annotations
 
 import threading
 import time
+from collections import deque
 from collections.abc import Callable
 from pathlib import Path
 
+from watchdog.events import FileSystemEventHandler
+from watchdog.observers import Observer
+from watchdog.observers.polling import PollingObserver
+
 from .ipc import LiveStateClient
 
 
@@ -52,7 +57,30 @@ class _PollingLiveWorker:
             self._thread.join(timeout=max(2.0, self.interval * 2))
 
 
-class DesktopLiveWatcher(_PollingLiveWorker):
+class _LiveFilesystemEventHandler(FileSystemEventHandler):
+    def __init__(self, enqueue: Callable[[str], None]):
+        super().__init__()
+        self._enqueue = enqueue
+
+    def on_created(self, event) -> None:
+        if not event.is_directory:
+            self._enqueue(event.src_path)
+
+    def on_modified(self, event) -> None:
+        if not event.is_directory:
+            self._enqueue(event.src_path)
+
+    def on_deleted(self, event) -> None:
+        if not event.is_directory:
+            self._enqueue(event.src_path)
+
+    def on_moved(self, event) -> None:
+        if not event.is_directory:
+            self._enqueue(event.src_path)
+            self._enqueue(event.dest_path)
+
+
+class DesktopLiveWatcher:
     def __init__(
         self,
         root: str | Path,
@@ -61,17 +89,31 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         owner_pid: int | None = None,
         owner_token: str | None = None,
         desktop_instance_id: str | None = None,
-        interval: float = 0.75,
+        interval: float = 0.10,
         on_status: Callable[[str], None] | None = None,
         on_reconnect: Callable[[LiveStateClient], None] | None = None,
         on_resync: Callable[[], object] | None = None,
     ):
+        """Watch one repository and route filesystem changes through LIVE.
+
+        ``interval`` is the event debounce/coalescing interval, not a
+        filesystem polling cadence.
+        """
         self.root = Path(root).resolve()
         self.client = client
         self.owner_pid = owner_pid
         self.owner_token = owner_token
         self.desktop_instance_id = desktop_instance_id
-        super().__init__(interval=interval, thread_name="contextor-live-watcher")
+        self.interval = max(0.0, float(interval))
+        self._stop = threading.Event()
+        self._wake = threading.Event()
+        self._thread: threading.Thread | None = None
+        self._observer = None
+        self._observer_lock = threading.Lock()
+        self._pending_lock = threading.Lock()
+        self._pending_paths: deque[str] = deque()
+        self._pending_set: set[str] = set()
+        self._using_polling_fallback = False
         self.on_status = on_status
         self.on_reconnect = on_reconnect
         self.on_resync = on_resync
@@ -81,6 +123,172 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         self._excluded_paths, self._ignored_dirs = self._load_watch_filters()
         self._snapshot = self._scan()
         self._startup_pending = self._startup_reconciliation_paths(self._snapshot)
+        self._event_handler = _LiveFilesystemEventHandler(self._enqueue_path)
+
+    def _observer_timeout(self) -> float:
+        return max(2.0, self.interval * 2)
+
+    def _dispose_observer(self, observer) -> None:
+        if observer is None:
+            return
+        try:
+            observer.stop()
+        except (OSError, RuntimeError):
+            pass
+        try:
+            observer.join(timeout=self._observer_timeout())
+        except (OSError, RuntimeError):
+            pass
+
+    def _reconcile_observer_start(self) -> None:
+        current = self._scan()
+        paths: list[str] = []
+        seen: set[str] = set()
+
+        def add(path: str) -> None:
+            if path not in seen:
+                seen.add(path)
+                paths.append(path)
+
+        for path in self._startup_pending:
+            add(path)
+        for path in list(self._snapshot) + list(current):
+            if self._snapshot.get(path) != current.get(path):
+                add(path)
+        for path in self._startup_reconciliation_paths(current):
+            add(path)
+        for path in paths:
+            self._enqueue_path(path)
+
+    def _start_native_observer(self):
+        observer = None
+        try:
+            observer = Observer()
+            observer.schedule(self._event_handler, str(self.root), recursive=True)
+            observer.start()
+        except (OSError, RuntimeError) as exc:
+            self._dispose_observer(observer)
+            try:
+                observer = PollingObserver(timeout=max(1.0, self.interval))
+                observer.schedule(self._event_handler, str(self.root), recursive=True)
+                observer.start()
+            except (OSError, RuntimeError) as fallback_exc:
+                self._dispose_observer(observer)
+                self._emit(
+                    "LIVE filesystem observer unavailable; polling fallback failed: "
+                    f"{fallback_exc}"
+                )
+                raise
+            self._using_polling_fallback = True
+            self._emit("LIVE filesystem observer unavailable; using polling fallback")
+        else:
+            self._using_polling_fallback = False
+        with self._observer_lock:
+            self._observer = observer
+
+    def _switch_to_polling_fallback(self, reason: str) -> None:
+        if self._stop.is_set() or self._using_polling_fallback:
+            return
+        with self._observer_lock:
+            observer = self._observer
+            self._observer = None
+        self._dispose_observer(observer)
+        try:
+            fallback = PollingObserver(timeout=max(1.0, self.interval))
+            fallback.schedule(self._event_handler, str(self.root), recursive=True)
+            fallback.start()
+        except (OSError, RuntimeError) as exc:
+            self._dispose_observer(locals().get("fallback"))
+            self._emit(
+                "LIVE filesystem observer unavailable; polling fallback failed: "
+                f"{exc}"
+            )
+            raise
+        with self._observer_lock:
+            self._observer = fallback
+        self._using_polling_fallback = True
+        self._emit(
+            "LIVE filesystem observer stopped; using polling fallback: "
+            f"{reason}"
+        )
+        self._reconcile_observer_start()
+
+    def _check_observer_health(self) -> None:
+        if self._stop.is_set() or self._using_polling_fallback:
+            return
+        with self._observer_lock:
+            observer = self._observer
+        if observer is None:
+            return
+        try:
+            alive = observer.is_alive()
+        except (OSError, RuntimeError):
+            alive = False
+        if not alive:
+            self._switch_to_polling_fallback("native observer stopped unexpectedly")
+
+    def start(self) -> None:
+        if self._thread and self._thread.is_alive():
+            return
+        self._stop.clear()
+        try:
+            self._start_native_observer()
+            self._reconcile_observer_start()
+        except Exception:
+            with self._observer_lock:
+                observer = self._observer
+                self._observer = None
+            self._dispose_observer(observer)
+            raise
+        self._thread = threading.Thread(
+            target=self._run_event_worker,
+            name="contextor-live-watcher",
+            daemon=True,
+        )
+        self._thread.start()
+
+    def _run_event_worker(self) -> None:
+        while not self._stop.is_set():
+            if not self._wake.wait(1.0):
+                try:
+                    self._check_observer_health()
+                except (OSError, RuntimeError, EOFError) as exc:
+                    self._handle_poll_error(exc)
+                continue
+            if self._stop.wait(self.interval):
+                break
+            try:
+                self.poll_once()
+            except (OSError, RuntimeError, EOFError) as exc:
+                self._handle_poll_error(exc)
+            try:
+                self._check_observer_health()
+            except (OSError, RuntimeError, EOFError) as exc:
+                self._handle_poll_error(exc)
+
+    def stop(self) -> None:
+        self._stop.set()
+        self._wake.set()
+        timeout = self._observer_timeout()
+        with self._observer_lock:
+            observer = self._observer
+        if observer is not None:
+            try:
+                observer.stop()
+            except (OSError, RuntimeError):
+                pass
+            try:
+                observer.join(timeout=timeout)
+            except (OSError, RuntimeError):
+                pass
+        thread = self._thread
+        if thread and thread is not threading.current_thread():
+            thread.join(timeout=timeout)
+        with self._observer_lock:
+            if self._observer is observer:
+                self._observer = None
+        self._thread = None
+        self._using_polling_fallback = False
 
     def _emit(self, message: str) -> None:
         """Forward a compact status message without assuming a GUI exists."""
@@ -159,22 +367,57 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             self._emit(f"LIVE recovery failed: {exc}")
             return None
 
+    def _normalize_watch_path(self, raw_path: str | Path) -> str | None:
+        try:
+            path = Path(raw_path).resolve()
+            relative = path.relative_to(self.root)
+        except (OSError, ValueError):
+            return None
+        if path.suffix != ".py":
+            return None
+        if any(part in self._ignored_dirs for part in relative.parts):
+            return None
+        relative_path = relative.as_posix()
+        if any(
+            relative_path == excluded
+            or relative_path.startswith(excluded + "/")
+            for excluded in self._excluded_paths
+        ):
+            return None
+        return str(path)
+
+    def _enqueue_path(self, raw_path: str | Path) -> None:
+        path = self._normalize_watch_path(raw_path)
+        if path is None:
+            return
+        with self._pending_lock:
+            if path in self._pending_set:
+                return
+            self._pending_paths.append(path)
+            self._pending_set.add(path)
+            self._wake.set()
+
+    def _drain_pending(self) -> list[str]:
+        with self._pending_lock:
+            paths = list(self._pending_paths)
+            self._pending_paths.clear()
+            self._pending_set.clear()
+            self._wake.clear()
+            return paths
+
+    def _requeue_paths(self, paths: list[str] | set[str]) -> None:
+        for path in paths:
+            self._enqueue_path(path)
+
     def _scan(self) -> dict[str, tuple[int, int]]:
         result = {}
         for path in self.root.rglob("*.py"):
-            relative = path.relative_to(self.root)
-            if any(part in self._ignored_dirs for part in relative.parts):
-                continue
-            relative_path = relative.as_posix()
-            if any(
-                relative_path == excluded
-                or relative_path.startswith(excluded + "/")
-                for excluded in self._excluded_paths
-            ):
+            normalized = self._normalize_watch_path(path)
+            if normalized is None:
                 continue
             try:
-                stat = path.stat()
-                result[str(path)] = (stat.st_mtime_ns, stat.st_size)
+                stat = Path(normalized).stat()
+                result[normalized] = (stat.st_mtime_ns, stat.st_size)
             except OSError:
                 continue
         return result
@@ -221,23 +464,9 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             or self._module_name(Path(path)) not in modules
         }
         for tracked_path in manager.tracked_paths():
-            path = Path(tracked_path)
-            try:
-                relative = path.resolve().relative_to(self.root)
-            except ValueError:
-                continue
-            relative_path = relative.as_posix()
-            if (
-                path.suffix == ".py"
-                and tracked_path not in current
-                and not any(part in self._ignored_dirs for part in relative.parts)
-                and not any(
-                    relative_path == excluded
-                    or relative_path.startswith(excluded + "/")
-                    for excluded in self._excluded_paths
-                )
-            ):
-                pending.add(tracked_path)
+            normalized = self._normalize_watch_path(tracked_path)
+            if normalized is not None and normalized not in current:
+                pending.add(normalized)
         return sorted(pending)
 
     def _trusted_file_state(self, snapshot: dict | None = None):
@@ -299,9 +528,16 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         return ".".join(relative.parts)
 
     def poll_once(self) -> list[str]:
-        scan_started = time.monotonic()
-        current = self._scan()
-        scan_ms = (time.monotonic() - scan_started) * 1000.0
+        changed = self._drain_pending()
+        if not changed:
+            return []
+        current: dict[str, tuple[int, int]] = {}
+        for path in changed:
+            try:
+                stat = Path(path).stat()
+                current[path] = (stat.st_mtime_ns, stat.st_size)
+            except OSError:
+                continue
         ping_started = time.monotonic()
         try:
             status = self.client.ping()
@@ -313,7 +549,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         ping_ms = (time.monotonic() - ping_started) * 1000.0
 
         if not status.get("available"):
-            self._snapshot = current
+            self._requeue_paths(changed)
             self._emit("LIVE: no snapshot; waiting for analysis")
             return []
         if self._startup_requires_resync:
@@ -343,19 +579,9 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             self._snapshot = current
             self._startup_pending = self._startup_reconciliation_paths(current)
             self._startup_requires_resync = False
+            self._requeue_paths(self._startup_pending)
             return []
-        startup_pending = set(self._startup_pending)
-        if startup_pending:
-            startup_pending &= set(self._startup_reconciliation_paths(current))
-        changed = sorted(
-            startup_pending
-            | {
-                path
-                for path in set(self._snapshot) | set(current)
-                if self._snapshot.get(path) != current.get(path)
-            }
-        )
-        deferred: set[str] = set()
+        deferred: list[str] = []
         reconciled: list[str] = []
         next_snapshot = dict(self._snapshot)
 
@@ -381,7 +607,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             trace_event(
                 "LIVE", "FS_CHANGE_DETECTED", op=op, repo=str(self.root),
                 path=relative, kind=kind, rev=status.get("revision"),
-                scan_ms=scan_ms, ping_ms=ping_ms, mtime_ns=mtime_ns,
+                discovery="watchdog", ping_ms=ping_ms, mtime_ns=mtime_ns,
             )
             self._emit(f"Updating LIVE: {Path(path).name}")
             update_started = time.monotonic()
@@ -397,7 +623,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 )
                 lease = acquire_full_analysis(self.root, owner="desktop_watcher", timeout=10.0)
             except FullAnalysisBusyError:
-                deferred.add(path)
+                deferred.append(path)
                 self._emit("LIVE: repository mutation busy; deferring watcher update")
                 continue
             try:
@@ -405,7 +631,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 # Re-read its exact FileState generation before mutating LIVE.
                 candidate_requires_update = self._candidate_requires_update(path, current)
                 if candidate_requires_update is None:
-                    deferred.add(path)
+                    deferred.append(path)
                     if was_ambiguous:
                         trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
@@ -425,7 +651,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 if update_attempted:
                     self._ambiguous_updates.add(path)
                     trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
-                    deferred.add(path)
+                    deferred.append(path)
                     self._emit("LIVE: update outcome ambiguous; deferring revalidation")
                     continue
                 self._emit("LIVE: connection lost during update; recovering...")
@@ -439,18 +665,18 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 try:
                     recovered_snapshot = self.client.snapshot()
                 except (OSError, EOFError, TimeoutError, ConnectionError):
-                    deferred.add(path)
+                    deferred.append(path)
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                     continue
                 if self._trusted_file_state(recovered_snapshot) is None:
-                    deferred.add(path)
+                    deferred.append(path)
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                     continue
                 candidate_requires_update = self._candidate_requires_update(
                     path, current, recovered_snapshot
                 )
                 if candidate_requires_update is None:
-                    deferred.add(path)
+                    deferred.append(path)
                     if was_ambiguous:
                         trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
@@ -492,13 +718,13 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             else:
                 self._emit(f"LIVE update error: {Path(path).name}: {result_status}")
             if not acknowledged:
-                deferred.add(path)
+                deferred.append(path)
                 continue
             acknowledge(path)
             reconciled.append(path)
         if deferred:
             self._snapshot = next_snapshot
-            self._startup_pending = sorted(deferred)
+            self._requeue_paths(deferred)
             return reconciled
         self._snapshot = next_snapshot
         self._startup_pending = []
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 379ced9..7f9a9ab 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -544,6 +544,7 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
     try:
         time.sleep(0.05)
         py_file.write_text("x = 22\n", encoding="utf-8")
+        watcher._enqueue_path(str(py_file))
 
         changed = watcher.poll_once()
         assert str(py_file) in changed
diff --git a/tests/test_live_watcher_watchdog.py b/tests/test_live_watcher_watchdog.py
new file mode 100644
index 0000000..ceadb63
--- /dev/null
+++ b/tests/test_live_watcher_watchdog.py
@@ -0,0 +1,274 @@
+from __future__ import annotations
+
+import threading
+from types import SimpleNamespace
+
+import pytest
+
+from contextor.core.live_state import CanonicalLiveServer, DesktopLiveWatcher, LiveStateClient
+import contextor.core.live_state.watcher as watcher_module
+
+
+pytestmark = pytest.mark.live
+
+
+def _event(path: str, *, directory: bool = False, dest_path: str | None = None):
+    values = {"is_directory": directory, "src_path": path}
+    if dest_path is not None:
+        values["dest_path"] = dest_path
+    return SimpleNamespace(**values)
+
+
+def _make_watcher(tmp_path, *, result_status: str = "UPDATED"):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    updates = []
+
+    class Client:
+        def snapshot(self):
+            return {
+                "status": "ok",
+                "state": SimpleNamespace(modules={}, revision=1, state_id="sid"),
+            }
+
+        def ping(self):
+            return {"status": "ok", "available": True, "revision": 1}
+
+        def update_file(self, path, **kwargs):
+            updates.append((path, kwargs))
+            return {
+                "status": "ok",
+                "revision": len(updates) + 1,
+                "seq": len(updates),
+                "result": SimpleNamespace(status=result_status, file_path=path),
+            }
+
+    client = Client()
+    watcher = DesktopLiveWatcher(repo, client, interval=0)
+    watcher._startup_requires_resync = False
+    watcher._startup_pending = []
+    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
+        has_changed=lambda _path: True,
+        tracked_paths=lambda: {item[0] for item in updates},
+        revision=1,
+        state_id="sid",
+    )
+    return repo, watcher, client, updates
+
+
+class _FakeObserver:
+    def __init__(self, records, *, fail_start=False):
+        self.records = records
+        self.fail_start = fail_start
+        self.alive = True
+
+    def schedule(self, handler, path, recursive=False):
+        self.records.append(("schedule", handler, path, recursive))
+
+    def start(self):
+        self.records.append(("start",))
+        if self.fail_start:
+            self.alive = False
+            raise OSError("native observer unavailable")
+
+    def is_alive(self):
+        return self.alive
+
+    def stop(self):
+        self.records.append(("stop",))
+        self.alive = False
+
+    def join(self, timeout=None):
+        self.records.append(("join", timeout))
+
+
+def test_idle_poll_once_never_scans_repository(tmp_path, monkeypatch):
+    _repo, watcher, _client, _updates = _make_watcher(tmp_path)
+    monkeypatch.setattr(watcher, "_scan", lambda: (_ for _ in ()).throw(AssertionError("steady-state scan")))
+
+    assert watcher.poll_once() == []
+
+
+def test_duplicate_modify_events_coalesce_to_one_pending_path(tmp_path):
+    repo, watcher, _client, _updates = _make_watcher(tmp_path)
+    path = str(repo / "module.py")
+
+    watcher._event_handler.on_modified(_event(path))
+    watcher._event_handler.on_modified(_event(path))
+
+    assert watcher._drain_pending() == [path]
+
+
+def test_non_python_ignored_and_excluded_events_are_rejected(tmp_path):
+    repo, watcher, _client, _updates = _make_watcher(tmp_path)
+    watcher._ignored_dirs = frozenset({"ignored"})
+    watcher._excluded_paths = ("excluded.py", "excluded_dir")
+
+    for path in (
+        repo / "notes.txt",
+        repo / "ignored" / "module.py",
+        repo / "excluded.py",
+        repo / "excluded_dir" / "module.py",
+    ):
+        watcher._event_handler.on_modified(_event(str(path)))
+
+    assert watcher._drain_pending() == []
+
+
+def test_move_enqueues_old_then_new(tmp_path):
+    repo, watcher, _client, _updates = _make_watcher(tmp_path)
+    old_path = str(repo / "old.py")
+    new_path = str(repo / "new.py")
+
+    watcher._event_handler.on_moved(_event(old_path, dest_path=new_path))
+
+    assert watcher._drain_pending() == [old_path, new_path]
+
+
+def test_event_path_routes_through_existing_client_update_file(tmp_path):
+    repo, watcher, _client, updates = _make_watcher(tmp_path)
+    path = repo / "module.py"
+    path.write_text("VALUE = 1\n", encoding="utf-8")
+    watcher._enqueue_path(str(path))
+
+    assert watcher.poll_once() == [str(path.resolve())]
+    assert updates == [(str(path.resolve()), {"origin": "desktop_watcher", "trace_op": updates[0][1]["trace_op"]})]
+
+
+def test_delete_event_routes_missing_path_as_delete_candidate(tmp_path):
+    repo, watcher, _client, updates = _make_watcher(tmp_path)
+    path = repo / "module.py"
+    path.write_text("VALUE = 1\n", encoding="utf-8")
+    watcher._snapshot[str(path.resolve())] = (1, 10)
+    path.unlink()
+    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
+        has_changed=lambda _path: True,
+        tracked_paths=lambda: {str(path.resolve())},
+        revision=1,
+        state_id="sid",
+    )
+    watcher._enqueue_path(str(path))
+
+    assert watcher.poll_once() == [str(path.resolve())]
+    assert updates[0][0] == str(path.resolve())
+    assert str(path.resolve()) not in watcher._snapshot
+
+
+def test_syntax_error_and_recovery_contract_survives_watchdog_adapter(tmp_path):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / "broken.py"
+    target.write_text("def broken(:\n", encoding="utf-8")
+    results = [
+        SimpleNamespace(
+            status="SYNTAX_ERROR",
+            file_path=str(target),
+            error="invalid syntax",
+            line_number=1,
+            column_number=12,
+        ),
+        SimpleNamespace(status="RECOVERED", file_path=str(target)),
+    ]
+    state = SimpleNamespace(revision=0, state_id="sid", modules={})
+
+    def updater(_candidate, path):
+        return results.pop(0)
+
+    server = CanonicalLiveServer(state, revision=0, updater=updater)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    statuses = []
+    watcher = DesktopLiveWatcher(
+        repo,
+        LiveStateClient(server.endpoint),
+        interval=0,
+        on_status=statuses.append,
+    )
+    watcher._startup_requires_resync = False
+    watcher._startup_pending = []
+    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
+        has_changed=lambda _path: True,
+        tracked_paths=lambda: {str(target.resolve())},
+        revision=0,
+        state_id="sid",
+    )
+
+    try:
+        watcher._enqueue_path(str(target))
+        assert watcher.poll_once() == [str(target.resolve())]
+
+        target.write_text("def repaired():\n    return 1\n", encoding="utf-8")
+        watcher._enqueue_path(str(target))
+        assert watcher.poll_once() == [str(target.resolve())]
+
+        events = watcher.client.get_events(after_seq=0, limit=None)["events"]
+        update_events = [event for event in events if event.get("operation") == "update_file"]
+        assert [event["status"] for event in update_events] == ["SYNTAX_ERROR", "RECOVERED"]
+        assert all(event["origin"] == "desktop_watcher" for event in update_events)
+        assert update_events[0]["line_number"] == 1
+        assert update_events[0]["column_number"] == 12
+        assert statuses == [
+            "Updating LIVE: broken.py",
+            "LIVE syntax error: broken.py line 1, column 12: invalid syntax",
+            "Updating LIVE: broken.py",
+            "LIVE syntax recovery: broken.py",
+        ]
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
+def test_native_observer_start_failure_uses_explicit_polling_fallback(tmp_path, monkeypatch):
+    records = []
+    fallback_records = []
+    monkeypatch.setattr(watcher_module, "Observer", lambda: _FakeObserver(records, fail_start=True))
+    monkeypatch.setattr(watcher_module, "PollingObserver", lambda timeout: _FakeObserver(fallback_records))
+    _repo, watcher, _client, _updates = _make_watcher(tmp_path)
+    statuses = []
+    watcher.on_status = statuses.append
+
+    try:
+        watcher.start()
+        assert watcher._using_polling_fallback is True
+        assert any("using polling fallback" in message for message in statuses)
+        assert fallback_records[0][0] == "schedule"
+        assert fallback_records[0][3] is True
+    finally:
+        watcher.stop()
+
+
+def test_start_stop_owns_observer_lifecycle(tmp_path, monkeypatch):
+    records = []
+    monkeypatch.setattr(watcher_module, "Observer", lambda: _FakeObserver(records))
+    _repo, watcher, _client, _updates = _make_watcher(tmp_path)
+
+    watcher.start()
+    watcher.start()
+    watcher.stop()
+
+    assert [record[0] for record in records] == ["schedule", "start", "stop", "join"]
+    assert records[0][3] is True
+    assert watcher._observer is None
+    assert watcher._thread is None
+
+
+def test_startup_reconciliation_scan_is_not_steady_state_polling(tmp_path, monkeypatch):
+    records = []
+    monkeypatch.setattr(watcher_module, "Observer", lambda: _FakeObserver(records))
+    _repo, watcher, _client, _updates = _make_watcher(tmp_path)
+    scan_calls = []
+    original_scan = watcher._scan
+    monkeypatch.setattr(
+        watcher,
+        "_scan",
+        lambda: (scan_calls.append("scan") or original_scan()),
+    )
+
+    try:
+        watcher.start()
+        assert len(scan_calls) == 1
+        assert watcher.poll_once() == []
+        assert watcher.poll_once() == []
+        assert len(scan_calls) == 1
+    finally:
+        watcher.stop()


## CONCLUSION

Watchdog implementation is complete within the allowed files and the watchdog-specific/related tests pass. The required focused gate is not met because three legacy IPC tests outside the allowed edit boundary still assume repository polling. No PASS claim is made.
