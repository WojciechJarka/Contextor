# Stage 1F.3 watchdog focused gate

STATUS=PASS

## FIX

- Added a non-waking internal deferred requeue path: _requeue_paths() retains paths with wake=False.
- Added _has_pending_paths() under the pending-path lock.
- Minimally rewired _run_event_worker(): watchdog signals receive the existing interval debounce; timeout ticks perform observer health checks; queued deferred work retries at the 1 Hz wait boundary.
- Preserved wake signals raised by new filesystem events during processing.
- Cleared _startup_pending after startup/reconciliation paths transfer to the event queue.
- Migrated the three legacy IPC watcher tests to explicit enqueue semantics.
- Added a regression test proving unavailable LIVE deferral retains the path, leaves _wake cleared, and emits exactly one waiting status.

## TEST_RESULTS

Focused command:

    .\.venv\Scripts\python.exe -m pytest -q tests/test_live_watcher_watchdog.py tests/test_live_activity_status.py tests/test_live_state_ipc.py tests/test_collisions_live_lifecycle.py tests/test_refresh_plan_execution.py

Result: 139 passed, 1 warning in 130.79s.

Additional verification:

    .\.venv\Scripts\python.exe -m py_compile contextor\core\live_state\watcher.py tests\test_live_watcher_watchdog.py tests\test_live_state_ipc.py

Result: passed.

    git diff --check

Result: passed. Git reported only LF/CRLF working-copy warnings.

## FILES_CHANGED

- contextor/core/live_state/watcher.py
- tests/test_live_state_ipc.py
- tests/test_live_watcher_watchdog.py

## PREEXISTING_WORKTREE_CHANGES

- No additional uncommitted changes were present outside this task when verified.
- Requirements.txt, pyproject.toml, and run_contextor.bat were not modified by this task and are clean relative to HEAD.
- walkthrough.md is the requested report and is excluded from FILES_CHANGED.

## COMPLETE FULL_DIFF

diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 3eeeba2..8d18fe9 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -159,6 +159,7 @@ class DesktopLiveWatcher:
             add(path)
         for path in paths:
             self._enqueue_path(path)
+        self._startup_pending = []
 
     def _start_native_observer(self):
         observer = None
@@ -249,22 +250,27 @@ class DesktopLiveWatcher:
 
     def _run_event_worker(self) -> None:
         while not self._stop.is_set():
-            if not self._wake.wait(1.0):
+            signaled = self._wake.wait(1.0)
+            if self._stop.is_set():
+                break
+            if signaled:
+                if self._stop.wait(self.interval):
+                    break
+            else:
                 try:
                     self._check_observer_health()
                 except (OSError, RuntimeError, EOFError) as exc:
                     self._handle_poll_error(exc)
-                continue
-            if self._stop.wait(self.interval):
-                break
-            try:
-                self.poll_once()
-            except (OSError, RuntimeError, EOFError) as exc:
-                self._handle_poll_error(exc)
-            try:
-                self._check_observer_health()
-            except (OSError, RuntimeError, EOFError) as exc:
-                self._handle_poll_error(exc)
+            if self._has_pending_paths():
+                try:
+                    self.poll_once()
+                except (OSError, RuntimeError, EOFError) as exc:
+                    self._handle_poll_error(exc)
+                if signaled:
+                    try:
+                        self._check_observer_health()
+                    except (OSError, RuntimeError, EOFError) as exc:
+                        self._handle_poll_error(exc)
 
     def stop(self) -> None:
         self._stop.set()
@@ -386,7 +392,7 @@ class DesktopLiveWatcher:
             return None
         return str(path)
 
-    def _enqueue_path(self, raw_path: str | Path) -> None:
+    def _enqueue_path(self, raw_path: str | Path, *, wake: bool = True) -> None:
         path = self._normalize_watch_path(raw_path)
         if path is None:
             return
@@ -395,7 +401,8 @@ class DesktopLiveWatcher:
                 return
             self._pending_paths.append(path)
             self._pending_set.add(path)
-            self._wake.set()
+            if wake:
+                self._wake.set()
 
     def _drain_pending(self) -> list[str]:
         with self._pending_lock:
@@ -405,9 +412,13 @@ class DesktopLiveWatcher:
             self._wake.clear()
             return paths
 
+    def _has_pending_paths(self) -> bool:
+        with self._pending_lock:
+            return bool(self._pending_paths)
+
     def _requeue_paths(self, paths: list[str] | set[str]) -> None:
         for path in paths:
-            self._enqueue_path(path)
+            self._enqueue_path(path, wake=False)
 
     def _scan(self) -> dict[str, tuple[int, int]]:
         result = {}
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 62b0676..d47293c 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -1166,12 +1166,15 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
     target = tmp_path / "sample.py"
     try:
         target.write_text("value = 1\n", encoding="utf-8")
+        watcher._enqueue_path(str(target))
         assert watcher.poll_once() == [str(target)]
 
         target.write_text("value = 22\n", encoding="utf-8")
+        watcher._enqueue_path(str(target))
         assert watcher.poll_once() == [str(target)]
 
         target.unlink()
+        watcher._enqueue_path(str(target))
         assert watcher.poll_once() == [str(target)]
         snapshot = LiveStateClient(server.endpoint).snapshot()
         assert snapshot["revision"] == 3
@@ -1202,7 +1205,9 @@ def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
     statuses = []
     watcher = DesktopLiveWatcher(tmp_path, client, on_status=statuses.append)
     try:
-        (tmp_path / "before_analysis.py").write_text("value = 1\n", encoding="utf-8")
+        before_analysis = tmp_path / "before_analysis.py"
+        before_analysis.write_text("value = 1\n", encoding="utf-8")
+        watcher._enqueue_path(str(before_analysis))
         assert watcher.poll_once() == []
         assert client.ping() == {
             "status": "ok", "protocol_version": LIVE_PROTOCOL_VERSION,
@@ -1210,11 +1215,19 @@ def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
         }
         assert statuses == ["LIVE: no snapshot; waiting for analysis"]
 
-        client.publish(SimpleNamespace(ready=True, revision=1, state_id=identity.repo_id, modules={}))
+        manager.update_state(str(before_analysis))
+        client.publish(SimpleNamespace(
+            ready=True,
+            revision=1,
+            state_id=identity.repo_id,
+            modules={"before_analysis": object()},
+        ))
         manager.save(identity.repo_id, revision=1)
-        (tmp_path / "after_analysis.py").write_text("value = 2\n", encoding="utf-8")
+        after_analysis = tmp_path / "after_analysis.py"
+        after_analysis.write_text("value = 2\n", encoding="utf-8")
+        watcher._enqueue_path(str(after_analysis))
         response = watcher.poll_once()
-        assert response == [str(tmp_path / "after_analysis.py")]
+        assert response == [str(after_analysis)]
     finally:
         server.close()
         thread.join(timeout=2)
@@ -1241,6 +1254,7 @@ def test_desktop_watcher_reports_syntax_location(tmp_path):
     try:
         target = tmp_path / "broken.py"
         target.write_text("def broken(:\n", encoding="utf-8")
+        watcher._enqueue_path(str(target))
         assert watcher.poll_once() == [str(target)]
         assert statuses == [
             "Updating LIVE: broken.py",
diff --git a/tests/test_live_watcher_watchdog.py b/tests/test_live_watcher_watchdog.py
new file mode 100644
index 0000000..45401aa
--- /dev/null
+++ b/tests/test_live_watcher_watchdog.py
@@ -0,0 +1,290 @@
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
+def test_internal_deferred_requeue_does_not_hot_wake(tmp_path):
+    repo, watcher, client, _updates = _make_watcher(tmp_path)
+    statuses = []
+    watcher.on_status = statuses.append
+    path = repo / "module.py"
+    path.write_text("VALUE = 1\n", encoding="utf-8")
+    client.ping = lambda: {"status": "ok", "available": False, "revision": 1}
+
+    watcher._enqueue_path(str(path))
+
+    assert watcher.poll_once() == []
+    assert watcher._has_pending_paths() is True
+    assert watcher._wake.is_set() is False
+    assert statuses == ["LIVE: no snapshot; waiting for analysis"]
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

Focused gate is PASS. The deferred/unavailable path remains queued without immediate wake, idle poll_once() performs no repository scan, event-triggered paths still route through canonical client.update_file, and the focused suite is fully green. No Desktop, analyze_project, full repository analysis, MCP update_file, or full pytest was run.
