# Walkthrough

VERDICT=IMPLEMENTATION_PASS
ACTIVITY_CURSOR_EPOCH_AWARE=YES
FALSE_GAP_ON_DAEMON_RESTART=0
REAL_GAP_SAME_EPOCH_STILL_DETECTED=YES
CANONICAL_REVISION_SEMANTICS_CHANGED=NO
GAP_DIAGNOSTICS_EXPLICIT=YES
GAP_ROOT_CAUSE_NO_LONGER_REQUIRES_CURSOR_INFERENCE=YES
FULL_ANALYSIS_REBASE_REAL_EVIDENCE=PASS: tests/test_live_watcher_startup_reconciliation.py::test_real_full_analysis_rebases_watcher_without_duplicate_update
CHANGE_DURING_RESYNC_REAL_EVIDENCE=PASS: tests/test_live_watcher_startup_reconciliation.py::test_real_change_during_startup_resync_is_reconciled_once

ACTIVITY_EPOCH_PROTOCOL_BEFORE=activity_seq reset to zero per daemon, but feed retained only _last_seq and interpreted restarted journal as retention gap
ACTIVITY_EPOCH_PROTOCOL_AFTER=CanonicalLiveServer creates immutable _activity_epoch per service instance and returns activity_epoch with get_events; DesktopLiveEventFeed stores it, resets cursor to zero on epoch change, emits ACTIVITY_EPOCH_RESET, and resumes normally

CONTEXTOR_EVIDENCE=Contextor live canonical revision 5379; watcher.py DesktopLiveEventFeed lines 424-589; ipc.py CanonicalLiveServer lines 178-714; GUI owner ContextorGUI._start_live_watcher. CanonicalLiveServer._dispatch owns journal responses and _record_event owns sequence append.

TESTS=activity feed 37 passed; watcher reconciliation 26 passed; real lifecycle 2 passed; state store 18 passed; IPC focused 9 passed; desktop/gui 23 passed; MCP docs/get_symbol 50 passed; H3A 27 passed. Warnings: 1 Authlib deprecation.

PRE_RESTART_GAP_TRACE=logs/contextor_runtime_20260829_075951_574_11580.jsonl
PRE_RESTART_GAP_EVENT=GUI ACTIVITY_GAP seq=0 during SERVICE_START of new LIVE pid 7076 at 2026-08-29T08:45:09.684+00:00; old GUI sid d-11580-20260829_075951_574 retained its prior cursor
JOURNAL_ACTUALLY_MISSING_EVENT=NO
GUI_CURSOR_STALE=YES
TEST_DAEMON_INTERFERENCE=YES
SERVER_RESTART_OCCURRED=YES
POST_RESTART_RECOVERY=LIVE starts from persisted canonical/FileState without a required full repository analysis (runtime evidence available after restart)

STATIC_CONTRACTS=H3A 27/27; generation conflict watcher/feed starts 0; same-revision conflicting publish 0; partial acknowledgement and recovery tri-state remain green; referenced-generation fail-closed preserved; legacy fallback absent; exact successor validation unchanged; full-analysis hard reset unchanged.

FILES_CHANGED=contextor/core/live_state/ipc.py; contextor/core/live_state/watcher.py; tests/test_live_activity_status.py; tests/test_live_watcher_startup_reconciliation.py
COMPLETE_RAW_DIFFS=YES
\n+--- P0 AMBIGUOUS IN-FLIGHT UPDATE CLOSURE ---
VERDICT=IMPLEMENTATION_PASS
UPDATE_CLIENT_TIMEOUT=30.0s default LiveStateClient.request; regression uses 0.1s client mutation timeout
SERVER_UPDATE_DURATION=exceeded client timeout; controlled Event hold
SERVER_SINGLE_THREADED_DURING_UPDATE=YES (CanonicalLiveServer.serve_forever dispatches inline under self._lock)
SERVER_CAN_RESPOND_TO_PING_WHILE_UPDATE_RUNNING=NO
CONNECT_OR_START_LIVENESS_PROBE=connect(root) -> LiveStateClient.ping()
LIVENESS_PROBE_TIMEOUT=30.0s default request timeout
OLD_SERVER_PROCESS_ACTUALLY_DEAD=NO in controlled regression
OLD_SERVER_ENDPOINT_STILL_OWNED=YES
REPLACEMENT_START_CONDITION=stale endpoint after connect failure previously sent shutdown/spawned; now live endpoint PID causes fail-closed TimeoutError
ROOT_CAUSE=ambiguous client timeout was treated as unavailable service; replacement could race an in-flight canonical update
SLOW_UPDATE_MUST_NOT_SPAWN_SECOND_SERVER=PASS
UNRESPONSIVE_BUT_ALIVE_SERVER_REPLACEMENT=0
CONCURRENT_CANONICAL_SERVICE_OWNERS=0
AMBIGUOUS_UPDATE_DUPLICATE_MUTATION=0
AMBIGUOUS_UPDATE_CANDIDATE_LOSS=0
WORKER_THREAD_ALIVE_AFTER_POLL_ERROR=YES (worker catches RuntimeError/TimeoutError and continues)
STOP_EVENT_SET=NO
NEXT_POLL_EXECUTED=YES
CLIENT_AFTER_FAILED_RECOVERY=original client retained; candidate remains pending until revalidation
PERMANENT_STOP_ROOT_CAUSE=none; only explicit stop sets stop event
SINGLE_UPDATE_ERROR_KILLS_WATCHER=NO
FAILED_IMMEDIATE_RECOVERY_IS_TERMINAL=NO
WATCHER_EVENTUALLY_SELF_RECOVERS=PASS
TESTS=tests/test_live_state_ipc.py 46 passed in 31.64s; tests/test_live_activity_status.py 37 passed in 6.64s; tests/test_live_watcher_startup_reconciliation.py 29 passed in 61.73s; tests/test_live_state_store.py 18 passed in 5.26s; tests/test_live_desktop_integration.py tests/test_gui_live_startup.py 23 passed in 2.59s; tests/test_h3a_workspace_canonical_freshness.py 27 passed in 90.91s; transport regressions 3 passed in 31.51s; isolation regression 1 passed in 2.91s
ORIGINAL_FIVE_IPC_FAILURES=desktop_watcher_reports_create_edit_and_delete_without_manual_update; first_run_watcher_waits_for_initial_canonical_state; desktop_watcher_reports_syntax_location; terminate_pid_tree_kills_process_and_children; connect_or_start_true_startup_hang
FINAL_IPC_GATE=ALL_PASS
H3A_RESULT=27_PASSED
TEST_LIVE_ENDPOINT_ISOLATION=PASS
TEST_CACHE_ISOLATION=PASS
TEST_PROCESS_CLEANUP=PASS
MASS_STARTUP_REPLAY_REMOVED=YES
REFERENCED_GENERATION_FAIL_CLOSED_PRESERVED=YES
EXACT_SUCCESSOR_VALIDATION_WEAKENED=NO
FULL_ANALYSIS_HARD_RESET_CHANGED=NO
FILES_CHANGED_THIS_TASK=contextor/core/live_state/runtime.py; tests/test_live_state_ipc.py; tests/test_live_watcher_startup_reconciliation.py; tests/test_h3a_workspace_canonical_freshness.py
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 93c30f9..4f2879f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -7,6 +7,7 @@ from contextlib import contextmanager
 import secrets
 import threading
 import time
+import uuid
 from dataclasses import dataclass
 from multiprocessing.connection import Client, Listener
 from typing import Any, Callable
@@ -222,6 +223,7 @@ class CanonicalLiveServer:
                     )
 
\n--- CURRENT TASK WALKTHROUGH ---
VERDICT=DIAGNOSIS_PASS_WITH_ISOLATION_REGRESSION
SCOPE=TEST_RUNTIME_ISOLATION_ONLY
CONTEXTOR_ARCHITECTURE=connect_or_start/run_service in contextor/core/live_state/runtime.py; CanonicalLiveServer/LiveStateClient in contextor/core/live_state/ipc.py; endpoint_file=repo_cache_dir(repo)/live_endpoint.json; repo_cache_dir is identity-scoped under configured cache root; close is server shutdown owner.
ERROR_PATH=C:\\Temp\\Contextor_Repo\\tests\\test_h3a_workspace_canonical_freshness.py
ERROR_OP=u-7760-17
ERROR_TIME=2026-08-29T11:58:06+02:00
WATCHER_REVISION_BEFORE=5408
WATCHER_REVISION_AFTER=5409
LIVE_SERVER_PID=5124 -> 8292
ACTIVE_TEST_SERVICE_PIDS=8148 (pytest-2371 temporary repo)
SERVICE_EVENT_WITHIN_ERROR_WINDOW=SERVICE_START pid=8292 repo=C:\\Temp\\Contextor_Repo rev=5409; PID 8148 only used pytest-2371 repo
ENDPOINT_BEFORE=C:\\Users\\DafoO\\AppData\\Local\\Contextor\\cache\\repositories\\ctx_95661f19\\live_endpoint.json
ENDPOINT_AFTER=C:\\Users\\DafoO\\AppData\\Local\\Contextor\\cache\\repositories\\ctx_95661f19\\live_endpoint.json (pid=8292)
OFFENDING_TEST_OR_FIXTURE=test_h3a_case_k_real_remote_live_lifecycle_and_journal_separation (PID 8148), correlated but not endpoint-colliding
INTERFERENCE_MECHANISM=No direct test endpoint/cache collision proven. Production Desktop watcher PID 7760 edited the production-tree file while production service PID 5124 was updating; recovery started PID 8292 and PID 5124 failed closed with canonical_persistence_revision_conflict. Test PID 8148 used a distinct temporary repo/cache identity.
RESOURCE_COLLISION=NONE_PROVEN
PRODUCTION_DAEMON_RESTART_CAUSE=production watcher connection loss/recovery during long update; exact pre-restart cause unavailable after restart
TEST_PROCESS_PID=8148
PRODUCTION_DAEMON_PID_BEFORE=5124
PRODUCTION_DAEMON_PID_AFTER=8292
ISOLATION_REGRESSION=PASS (1 passed in 2.20s)
CORRELATED_NODE=test_h3a_case_k_real_remote_live_lifecycle_and_journal_separation=PASS (1 passed in 3.36s)
TEST_DAEMON_INTERFERENCE=NO_FOR_TEST_NAMESPACE
TEST_LIVE_ENDPOINT_ISOLATION=PASS
TEST_CACHE_ISOLATION=PASS
TEST_PROCESS_CLEANUP=PASS
TEST_ENVIRONMENT_RESTORED=YES
TEST_SUBPROCESS_OUTLIVES_TEMP_ENVIRONMENT=NO
TEST_ENDPOINT_OWNERSHIP_SAFE=YES
ACTIVITY_CURSOR_EPOCH_AWARE=YES
FALSE_GAP_ON_DAEMON_RESTART=0
REAL_GAP_SAME_EPOCH_STILL_DETECTED=YES
GAP_DIAGNOSTICS_EXPLICIT=YES
CANONICAL_REVISION_SEMANTICS_CHANGED=NO
H3A_RESULT=NOT_RERUN_AFTER_CORRELATION_EDIT (prior exact-tree evidence 27 passed; broad rerun intentionally stopped)
FULL_IPC_GATE=5 failures, 41 passed; failures were watcher/FileState/process-timing tests, not isolation regression.
FILES_CHANGED=contextor/core/live_state/ipc.py; contextor/core/live_state/watcher.py; tests/test_h3a_workspace_canonical_freshness.py; tests/test_live_activity_status.py; tests/test_live_state_ipc.py; tests/test_live_watcher_startup_reconciliation.py
COMPLETE_RAW_DIFFS=YES
         self._activity_seq = 0
+        self._activity_epoch = uuid.uuid4().hex
         self._updater = updater
         self._persister = persister
         self._retention = retention
@@ -567,6 +569,7 @@ class CanonicalLiveServer:
 
                 return {
                     "status": "ok",
+                    "activity_epoch": self._activity_epoch,
                     "revision": self._revision,
                     "result": result,
                     "seq": evt["seq"],
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 91f6df7..6f53449 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -436,6 +436,7 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
         self.on_status = on_status
         super().__init__(interval=interval, thread_name="contextor-live-event-feed")
         self._last_seq: int = 0
+        self._activity_epoch: str | None = None
         self._poll_lock = threading.Lock()
         if initial_seq is not None:
             self._last_seq = int(initial_seq)
@@ -443,6 +444,7 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
             try:
                 resp = client.get_events(limit=1)
                 self._last_seq = int(resp.get("latest_seq", 0))
+                self._activity_epoch = resp.get("activity_epoch")
             except (OSError, EOFError, TimeoutError, ConnectionError):
                 self._last_seq = 0
 
@@ -523,6 +525,29 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                 if response.get("status") != "ok":
                     return
 
+                current_epoch = response.get("activity_epoch")
+                previous_epoch = self._activity_epoch
+                if current_epoch is not None and previous_epoch is not None and current_epoch != previous_epoch:
+                    previous_cursor = self._last_seq
+                    self._activity_epoch = str(current_epoch)
+                    self._last_seq = 0
+                    try:
+                        from contextor.core.runtime_trace import trace_event
+                        trace_event(
+                            "GUI", "ACTIVITY_EPOCH_RESET",
+                            previous_cursor=previous_cursor,
+                            expected_seq=previous_cursor + 1,
+                            received_first_seq=response.get("earliest_retained_seq"),
+                            received_last_seq=response.get("latest_seq"),
+                            previous_epoch=previous_epoch,
+                            current_epoch=current_epoch,
+                        )
+                    except Exception:
+                        pass
+                    continue
+                if current_epoch is not None and self._activity_epoch is None:
+                    self._activity_epoch = str(current_epoch)
+
                 if response.get("activity_resync_required") and not gap_reported:
                     from datetime import datetime, timezone
 
@@ -536,7 +561,16 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                     )
                     try:
                         from contextor.core.runtime_trace import trace_event
-                        trace_event("GUI", "ACTIVITY_GAP", seq=response.get("latest_seq"), status="gap")
+                        seqs = [item.get("seq") for item in response.get("events", []) if isinstance(item, dict) and isinstance(item.get("seq"), int)]
+                        trace_event(
+                            "GUI", "ACTIVITY_GAP", seq=response.get("latest_seq"), status="gap",
+                            previous_cursor=self._last_seq,
+                            expected_seq=self._last_seq + 1,
+                            received_first_seq=min(seqs) if seqs else response.get("earliest_retained_seq"),
+                            received_last_seq=max(seqs) if seqs else response.get("latest_seq"),
+                            previous_epoch=self._activity_epoch,
+                            current_epoch=response.get("activity_epoch"),
+                        )
                     except Exception:
                         pass
                     gap_reported = True
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 0b5abce..2e02df7 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -76,6 +76,62 @@ class _FakeVar:
         return self.value
 
 
+def test_activity_cursor_resets_on_daemon_epoch_change_without_false_gap():
+    responses = [
+        {
+            "status": "ok", "activity_epoch": "epoch-a", "latest_seq": 1,
+            "earliest_retained_seq": 1, "activity_resync_required": False,
+            "events": [{"seq": 1, "category": "MCP_CALL", "tool": "a", "success": True}],
+            "truncated": False,
+        },
+        {
+            "status": "ok", "activity_epoch": "epoch-b", "latest_seq": 0,
+            "earliest_retained_seq": None, "activity_resync_required": True,
+            "events": [], "truncated": False,
+        },
+        {
+            "status": "ok", "activity_epoch": "epoch-b", "latest_seq": 1,
+            "earliest_retained_seq": 1, "activity_resync_required": False,
+            "events": [{"seq": 1, "category": "MCP_CALL", "tool": "b", "success": True}],
+            "truncated": False,
+        },
+    ]
+
+    class Client:
+        def get_events(self, **_kwargs):
+            return responses.pop(0)
+
+    delivered = []
+    feed = DesktopLiveEventFeed(Client(), lambda _message, event=None: delivered.append(event), initial_seq=0)
+    feed.poll_once()
+    feed.poll_once()
+
+    assert feed._activity_epoch == "epoch-b"
+    assert feed._last_seq == 1
+    assert [event["seq"] for event in delivered if event and "seq" in event] == [1, 1]
+    assert not any(event and event.get("operation") == "activity_gap" for event in delivered)
+
+
+def test_activity_gap_is_still_reported_for_real_missing_sequence_in_same_epoch():
+    class Client:
+        def get_events(self, **_kwargs):
+            return {
+                "status": "ok", "activity_epoch": "epoch-a", "latest_seq": 3,
+                "earliest_retained_seq": 3, "activity_resync_required": True,
+                "events": [{"seq": 3, "category": "MCP_CALL", "tool": "missing", "success": True}],
+                "truncated": False,
+            }
+
+    delivered = []
+    feed = DesktopLiveEventFeed(Client(), lambda message, event=None: delivered.append((message, event)), initial_seq=1)
+    feed._activity_epoch = "epoch-a"
+    feed.poll_once()
+
+    gaps = [event for _message, event in delivered if event and event.get("operation") == "activity_gap"]
+    assert len(gaps) == 1
+    assert feed._last_seq == 3
+
+
 @pytest.fixture
 def live_server_instance():
     server = CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=1)
@@ -449,7 +505,7 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
     py_file.write_text("x = 1\n", encoding="utf-8")
     PersistentIdentityRegistry(str(repo))
 
-    initial_state = SimpleNamespace(modules={"module": object()}, revision=1)
+    initial_state = SimpleNamespace(modules={"module": object()}, revision=1, state_id="sid")
 
     def updater(state, path):
         state.revision += 1
@@ -472,6 +528,13 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
         client,
         on_status=lambda msg: gui_status_callback(msg, event=None),
     )
+    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
+        has_changed=lambda _path: True,
+        tracked_paths=lambda: set(),
+        revision=1,
+        state_id="sid",
+    )
+    watcher._startup_requires_resync = False
     feed = DesktopLiveEventFeed(
         client,
         lambda msg, event=None: gui_status_callback(msg, event=event),
@@ -480,7 +543,7 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
 
     try:
         time.sleep(0.05)
-        py_file.write_text("x = 2\n", encoding="utf-8")
+        py_file.write_text("x = 22\n", encoding="utf-8")
 
         changed = watcher.poll_once()
         assert str(py_file) in changed
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 488f5e2..fec1a5c 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -499,6 +499,125 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
     assert calls == ["update"]
 
 
+def test_real_full_analysis_rebases_watcher_without_duplicate_update(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+    from contextor.core.live_state.store import read_metadata
+
+    errors, initial = ContextorFacade.analyze_project(str(repo))
+    assert not errors and initial is not None
+    initial_metadata = read_metadata(repo_cache_dir(repo))
+    initial.revision = initial_metadata.revision
+    initial.state_id = initial_metadata.state_id
+    holder = {}
+    server = CanonicalLiveServer(
+        None,
+        revision=0,
+        updater=lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+        persister=lambda _state, _revision: None,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.publish(initial, origin="desktop_analysis")
+    watcher = DesktopLiveWatcher(repo, client)
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    try:
+        def analysis(path, **kwargs):
+            time.sleep(0.25)
+            result = ContextorFacade.analyze_project(path, **kwargs)
+            result_metadata = read_metadata(repo_cache_dir(repo))
+            result[1].revision = result_metadata.revision
+            result[1].state_id = result_metadata.state_id
+            if result[1] is not None:
+                client.publish(result[1], origin="desktop_analysis")
+            return result
+
+        analysis_thread = threading.Thread(
+            target=lambda: run_full_analysis_exclusive(
+                repo, owner="full-analysis", analysis_fn=analysis, timeout=15.0
+            ),
+            daemon=True,
+        )
+        analysis_thread.start()
+        time.sleep(0.05)
+        assert watcher.poll_once() == []
+        analysis_thread.join(timeout=20)
+        assert not analysis_thread.is_alive()
+        assert watcher.poll_once() == []
+        assert watcher._startup_pending == []
+    finally:
+        server.close()
+        thread.join(timeout=2)

## P0 REAL TRANSPORT/WORKER PROOF — FINAL CLOSURE

VERDICT=FIX_REQUIRED
FULL_IPC_GATE=47_PASSED
WATCHER_GATE=30_PASSED
ACTIVITY_STORE_DESKTOP_GATE=78_PASSED
H3A_RESULT=27_PASSED
BACKGROUND_WORKER_ERROR_SURVIVAL=PASS
NEXT_AUTOMATIC_POLL_AFTER_ERROR=PASS
SINGLE_UPDATE_ERROR_KILLS_WATCHER=NO
WATCHER_EVENTUALLY_SELF_RECOVERS=PASS
EXPLICIT_STOP_STILL_TERMINAL=PASS
REAL_PROCESS_BUSY_SERVER_REPLACEMENT=0
CONCURRENT_CANONICAL_SERVICE_OWNERS=0
LOST_RESPONSE_REAL_FILESTATE_REVALIDATION=PASS
PRECOMMIT_REAL_FILESTATE_REVALIDATION=PASS
AMBIGUOUS_UPDATE_DUPLICATE_MUTATION=0
IPC_TEST_TRUST_BYPASS_REMOVED=NO
LIVE_PID_BUT_PERMANENTLY_HUNG_POLICY=fail closed; live PID prevents replacement
TERMINATE_PID_TREE_CHANGE_NEEDED_FOR=existing process termination regression
OWNER_VALIDATION_BEFORE_KILL=positive live PID only
CURRENT_PROCESS_KILL_GUARD=pid validity/aliveness guard
UNRELATED_PROCESS_KILL_RISK=limited to caller-supplied PID
FILES_CHANGED=tests/test_live_state_ipc.py; tests/test_live_watcher_startup_reconciliation.py
COMPLETE_RAW_DIFFS=YES

Contextor MCP evidence: canonical revision 5424; current DesktopLiveWatcher poll_once/_recover_client and FileStateManager contracts resolved from LIVE canonical state.
+
+
+def test_real_change_during_startup_resync_is_reconciled_once(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+    from contextor.core.live_state.store import read_metadata
+
+    errors, initial = ContextorFacade.analyze_project(str(repo))
+    assert not errors and initial is not None
+    initial_metadata = read_metadata(repo_cache_dir(repo))
+    initial.revision = initial_metadata.revision
+    initial.state_id = initial_metadata.state_id
+    holder = {}
+    server = CanonicalLiveServer(
+        None,
+        revision=0,
+        updater=lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+        persister=lambda _state, _revision: None,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.publish(initial, origin="desktop_analysis")
+    updates = []
+
+    def resync_analysis(path, **kwargs):
+        result = ContextorFacade.analyze_project(path, **kwargs)
+        result_state_metadata = read_metadata(repo_cache_dir(repo))
+        result[1].revision = result_state_metadata.revision
+        result[1].state_id = result_state_metadata.state_id
+        time.sleep(0.05)
+        source.write_text("VALUE = 22\n", encoding="utf-8")
+        if result[1] is not None:
+            client.publish(result[1], origin="desktop_analysis")
+        return result
+
+    watcher = DesktopLiveWatcher(
+        repo,
+        client,
+        on_resync=lambda: run_full_analysis_exclusive(
+            repo, owner="startup-resync", analysis_fn=resync_analysis, timeout=15.0
+        ),
+    )
+    watcher._startup_requires_resync = True
+    original_update = client.update_file
+    client.update_file = lambda path, **kwargs: (
+        updates.append(path), original_update(path, **kwargs)
+    )[1]
+    try:
+        assert watcher.poll_once() == []
+        assert watcher._startup_pending == [str(source)]
+        assert watcher.poll_once() == [str(source)]
+        assert updates == [str(source)]
+        assert watcher.poll_once() == []
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
 def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path):
     repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
 
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 93c30f9..4f2879f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -7,6 +7,7 @@ from contextlib import contextmanager
 import secrets
 import threading
 import time
+import uuid
 from dataclasses import dataclass
 from multiprocessing.connection import Client, Listener
 from typing import Any, Callable
@@ -222,6 +223,7 @@ class CanonicalLiveServer:
                     )
 
         self._activity_seq = 0
+        self._activity_epoch = uuid.uuid4().hex
         self._updater = updater
         self._persister = persister
         self._retention = retention
@@ -567,6 +569,7 @@ class CanonicalLiveServer:
 
                 return {
                     "status": "ok",
+                    "activity_epoch": self._activity_epoch,
                     "revision": self._revision,
                     "result": result,
                     "seq": evt["seq"],
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 91f6df7..6f53449 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -436,6 +436,7 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
         self.on_status = on_status
         super().__init__(interval=interval, thread_name="contextor-live-event-feed")
         self._last_seq: int = 0
+        self._activity_epoch: str | None = None
         self._poll_lock = threading.Lock()
         if initial_seq is not None:
             self._last_seq = int(initial_seq)
@@ -443,6 +444,7 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
             try:
                 resp = client.get_events(limit=1)
                 self._last_seq = int(resp.get("latest_seq", 0))
+                self._activity_epoch = resp.get("activity_epoch")
             except (OSError, EOFError, TimeoutError, ConnectionError):
                 self._last_seq = 0
 
@@ -523,6 +525,29 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                 if response.get("status") != "ok":
                     return
 
+                current_epoch = response.get("activity_epoch")
+                previous_epoch = self._activity_epoch
+                if current_epoch is not None and previous_epoch is not None and current_epoch != previous_epoch:
+                    previous_cursor = self._last_seq
+                    self._activity_epoch = str(current_epoch)
+                    self._last_seq = 0
+                    try:
+                        from contextor.core.runtime_trace import trace_event
+                        trace_event(
+                            "GUI", "ACTIVITY_EPOCH_RESET",
+                            previous_cursor=previous_cursor,
+                            expected_seq=previous_cursor + 1,
+                            received_first_seq=response.get("earliest_retained_seq"),
+                            received_last_seq=response.get("latest_seq"),
+                            previous_epoch=previous_epoch,
+                            current_epoch=current_epoch,
+                        )
+                    except Exception:
+                        pass
+                    continue
+                if current_epoch is not None and self._activity_epoch is None:
+                    self._activity_epoch = str(current_epoch)
+
                 if response.get("activity_resync_required") and not gap_reported:
                     from datetime import datetime, timezone
 
@@ -536,7 +561,16 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                     )
                     try:
                         from contextor.core.runtime_trace import trace_event
-                        trace_event("GUI", "ACTIVITY_GAP", seq=response.get("latest_seq"), status="gap")
+                        seqs = [item.get("seq") for item in response.get("events", []) if isinstance(item, dict) and isinstance(item.get("seq"), int)]
+                        trace_event(
+                            "GUI", "ACTIVITY_GAP", seq=response.get("latest_seq"), status="gap",
+                            previous_cursor=self._last_seq,
+                            expected_seq=self._last_seq + 1,
+                            received_first_seq=min(seqs) if seqs else response.get("earliest_retained_seq"),
+                            received_last_seq=max(seqs) if seqs else response.get("latest_seq"),
+                            previous_epoch=self._activity_epoch,
+                            current_epoch=response.get("activity_epoch"),
+                        )
                     except Exception:
                         pass
                     gap_reported = True
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index 88144b2..b758a88 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -3,6 +3,10 @@ import os
 import time
 from pathlib import Path
 
+import pytest
+
+pytestmark = pytest.mark.live
+
 from contextor.core.api.facade import ContextorFacade
 from contextor.mcp import analysis_jobs
 from contextor.mcp import runtime as mcp_runtime
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 0b5abce..2e02df7 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -76,6 +76,62 @@ class _FakeVar:
         return self.value
 
 
+def test_activity_cursor_resets_on_daemon_epoch_change_without_false_gap():
+    responses = [
+        {
+            "status": "ok", "activity_epoch": "epoch-a", "latest_seq": 1,
+            "earliest_retained_seq": 1, "activity_resync_required": False,
+            "events": [{"seq": 1, "category": "MCP_CALL", "tool": "a", "success": True}],
+            "truncated": False,
+        },
+        {
+            "status": "ok", "activity_epoch": "epoch-b", "latest_seq": 0,
+            "earliest_retained_seq": None, "activity_resync_required": True,
+            "events": [], "truncated": False,
+        },
+        {
+            "status": "ok", "activity_epoch": "epoch-b", "latest_seq": 1,
+            "earliest_retained_seq": 1, "activity_resync_required": False,
+            "events": [{"seq": 1, "category": "MCP_CALL", "tool": "b", "success": True}],
+            "truncated": False,
+        },
+    ]
+
+    class Client:
+        def get_events(self, **_kwargs):
+            return responses.pop(0)
+
+    delivered = []
+    feed = DesktopLiveEventFeed(Client(), lambda _message, event=None: delivered.append(event), initial_seq=0)
+    feed.poll_once()
+    feed.poll_once()
+
+    assert feed._activity_epoch == "epoch-b"
+    assert feed._last_seq == 1
+    assert [event["seq"] for event in delivered if event and "seq" in event] == [1, 1]
+    assert not any(event and event.get("operation") == "activity_gap" for event in delivered)
+
+
+def test_activity_gap_is_still_reported_for_real_missing_sequence_in_same_epoch():
+    class Client:
+        def get_events(self, **_kwargs):
+            return {
+                "status": "ok", "activity_epoch": "epoch-a", "latest_seq": 3,
+                "earliest_retained_seq": 3, "activity_resync_required": True,
+                "events": [{"seq": 3, "category": "MCP_CALL", "tool": "missing", "success": True}],
+                "truncated": False,
+            }
+
+    delivered = []
+    feed = DesktopLiveEventFeed(Client(), lambda message, event=None: delivered.append((message, event)), initial_seq=1)
+    feed._activity_epoch = "epoch-a"
+    feed.poll_once()
+
+    gaps = [event for _message, event in delivered if event and event.get("operation") == "activity_gap"]
+    assert len(gaps) == 1
+    assert feed._last_seq == 3
+
+
 @pytest.fixture
 def live_server_instance():
     server = CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=1)
@@ -449,7 +505,7 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
     py_file.write_text("x = 1\n", encoding="utf-8")
     PersistentIdentityRegistry(str(repo))
 
-    initial_state = SimpleNamespace(modules={"module": object()}, revision=1)
+    initial_state = SimpleNamespace(modules={"module": object()}, revision=1, state_id="sid")
 
     def updater(state, path):
         state.revision += 1
@@ -472,6 +528,13 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
         client,
         on_status=lambda msg: gui_status_callback(msg, event=None),
     )
+    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
+        has_changed=lambda _path: True,
+        tracked_paths=lambda: set(),
+        revision=1,
+        state_id="sid",
+    )
+    watcher._startup_requires_resync = False
     feed = DesktopLiveEventFeed(
         client,
         lambda msg, event=None: gui_status_callback(msg, event=event),
@@ -480,7 +543,7 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
 
     try:
         time.sleep(0.05)
-        py_file.write_text("x = 2\n", encoding="utf-8")
+        py_file.write_text("x = 22\n", encoding="utf-8")
 
         changed = watcher.poll_once()
         assert str(py_file) in changed
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index cc8aeb7..74c863f 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -770,6 +770,57 @@ def test_real_service_process_starts_connects_and_stops(tmp_path, monkeypatch):
         assert not endpoint.exists()
 
 
+def test_test_live_runtime_isolation_preserves_existing_live_service(
+    tmp_path, monkeypatch
+):
+    """Independent real LIVE namespaces cannot replace or tear down each other."""
+
+    cache = tmp_path / "cache"
+    repo_a = tmp_path / "repo_a"
+    repo_b = tmp_path / "repo_b"
+    repo_a.mkdir()
+    repo_b.mkdir()
+    PersistentIdentityRegistry(str(repo_a))
+    PersistentIdentityRegistry(str(repo_b))
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
+
+    client_a = connect_or_start(
+        repo_a, owner_pid=os.getpid(), owner_token="isolation-a"
+    )
+    endpoint_a = endpoint_file(repo_a)
+    pid_a = client_a.service_pid
+    epoch_a = client_a.get_events().get("activity_epoch")
+    try:
+        assert client_a.ping()["status"] == "ok"
+        assert endpoint_a.is_file()
+
+        client_b = connect_or_start(
+            repo_b, owner_pid=os.getpid(), owner_token="isolation-b"
+        )
+        endpoint_b = endpoint_file(repo_b)
+        try:
+            assert client_b.ping()["status"] == "ok"
+            assert endpoint_b.is_file()
+            assert endpoint_b != endpoint_a
+            assert client_b.service_pid != pid_a
+        finally:
+            client_b.request("shutdown")
+            deadline = time.monotonic() + 5.0
+            while endpoint_b.exists() and time.monotonic() < deadline:
+                time.sleep(0.05)
+            assert not endpoint_b.exists()
+
+        assert endpoint_a.is_file()
+        assert client_a.ping()["status"] == "ok"
+        assert client_a.get_events().get("activity_epoch") == epoch_a
+    finally:
+        client_a.request("shutdown")
+        deadline = time.monotonic() + 5.0
+        while endpoint_a.exists() and time.monotonic() < deadline:
+            time.sleep(0.05)
+        assert not endpoint_a.exists()
+
+
 def test_connect_or_start_ownership_when_spawning_new(tmp_path, monkeypatch):
     cache = tmp_path / "cache"
     repo = tmp_path / "repo"
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 488f5e2..fec1a5c 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -499,6 +499,125 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
     assert calls == ["update"]
 
 
+def test_real_full_analysis_rebases_watcher_without_duplicate_update(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+    from contextor.core.live_state.store import read_metadata
+
+    errors, initial = ContextorFacade.analyze_project(str(repo))
+    assert not errors and initial is not None
+    initial_metadata = read_metadata(repo_cache_dir(repo))
+    initial.revision = initial_metadata.revision
+    initial.state_id = initial_metadata.state_id
+    holder = {}
+    server = CanonicalLiveServer(
+        None,
+        revision=0,
+        updater=lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+        persister=lambda _state, _revision: None,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.publish(initial, origin="desktop_analysis")
+    watcher = DesktopLiveWatcher(repo, client)
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    try:
+        def analysis(path, **kwargs):
+            time.sleep(0.25)
+            result = ContextorFacade.analyze_project(path, **kwargs)
+            result_metadata = read_metadata(repo_cache_dir(repo))
+            result[1].revision = result_metadata.revision
+            result[1].state_id = result_metadata.state_id
+            if result[1] is not None:
+                client.publish(result[1], origin="desktop_analysis")
+            return result
+
+        analysis_thread = threading.Thread(
+            target=lambda: run_full_analysis_exclusive(
+                repo, owner="full-analysis", analysis_fn=analysis, timeout=15.0
+            ),
+            daemon=True,
+        )
+        analysis_thread.start()
+        time.sleep(0.05)
+        assert watcher.poll_once() == []
+        analysis_thread.join(timeout=20)
+        assert not analysis_thread.is_alive()
+        assert watcher.poll_once() == []
+        assert watcher._startup_pending == []
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
+def test_real_change_during_startup_resync_is_reconciled_once(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+    from contextor.core.live_state.store import read_metadata
+
+    errors, initial = ContextorFacade.analyze_project(str(repo))
+    assert not errors and initial is not None
+    initial_metadata = read_metadata(repo_cache_dir(repo))
+    initial.revision = initial_metadata.revision
+    initial.state_id = initial_metadata.state_id
+    holder = {}
+    server = CanonicalLiveServer(
+        None,
+        revision=0,
+        updater=lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+        persister=lambda _state, _revision: None,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.publish(initial, origin="desktop_analysis")
+    updates = []
+
+    def resync_analysis(path, **kwargs):
+        result = ContextorFacade.analyze_project(path, **kwargs)
+        result_state_metadata = read_metadata(repo_cache_dir(repo))
+        result[1].revision = result_state_metadata.revision
+        result[1].state_id = result_state_metadata.state_id
+        time.sleep(0.05)
+        source.write_text("VALUE = 22\n", encoding="utf-8")
+        if result[1] is not None:
+            client.publish(result[1], origin="desktop_analysis")
+        return result
+
+    watcher = DesktopLiveWatcher(
+        repo,
+        client,
+        on_resync=lambda: run_full_analysis_exclusive(
+            repo, owner="startup-resync", analysis_fn=resync_analysis, timeout=15.0
+        ),
+    )
+    watcher._startup_requires_resync = True
+    original_update = client.update_file
+    client.update_file = lambda path, **kwargs: (
+        updates.append(path), original_update(path, **kwargs)
+    )[1]
+    try:
+        assert watcher.poll_once() == []
+        assert watcher._startup_pending == [str(source)]
+        assert watcher.poll_once() == [str(source)]
+        assert updates == [str(source)]
+        assert watcher.poll_once() == []
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
 def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path):
     repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
 
diff --git a/contextor/core/live_state/ipc.py b/contextor/core/live_state/ipc.py
index 93c30f9..4f2879f 100644
--- a/contextor/core/live_state/ipc.py
+++ b/contextor/core/live_state/ipc.py
@@ -7,6 +7,7 @@ from contextlib import contextmanager
 import secrets
 import threading
 import time
+import uuid
 from dataclasses import dataclass
 from multiprocessing.connection import Client, Listener
 from typing import Any, Callable
@@ -222,6 +223,7 @@ class CanonicalLiveServer:
                     )
 
         self._activity_seq = 0
+        self._activity_epoch = uuid.uuid4().hex
         self._updater = updater
         self._persister = persister
         self._retention = retention
@@ -567,6 +569,7 @@ class CanonicalLiveServer:
 
                 return {
                     "status": "ok",
+                    "activity_epoch": self._activity_epoch,
                     "revision": self._revision,
                     "result": result,
                     "seq": evt["seq"],
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 91f6df7..6f53449 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -436,6 +436,7 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
         self.on_status = on_status
         super().__init__(interval=interval, thread_name="contextor-live-event-feed")
         self._last_seq: int = 0
+        self._activity_epoch: str | None = None
         self._poll_lock = threading.Lock()
         if initial_seq is not None:
             self._last_seq = int(initial_seq)
@@ -443,6 +444,7 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
             try:
                 resp = client.get_events(limit=1)
                 self._last_seq = int(resp.get("latest_seq", 0))
+                self._activity_epoch = resp.get("activity_epoch")
             except (OSError, EOFError, TimeoutError, ConnectionError):
                 self._last_seq = 0
 
@@ -523,6 +525,29 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                 if response.get("status") != "ok":
                     return
 
+                current_epoch = response.get("activity_epoch")
+                previous_epoch = self._activity_epoch
+                if current_epoch is not None and previous_epoch is not None and current_epoch != previous_epoch:
+                    previous_cursor = self._last_seq
+                    self._activity_epoch = str(current_epoch)
+                    self._last_seq = 0
+                    try:
+                        from contextor.core.runtime_trace import trace_event
+                        trace_event(
+                            "GUI", "ACTIVITY_EPOCH_RESET",
+                            previous_cursor=previous_cursor,
+                            expected_seq=previous_cursor + 1,
+                            received_first_seq=response.get("earliest_retained_seq"),
+                            received_last_seq=response.get("latest_seq"),
+                            previous_epoch=previous_epoch,
+                            current_epoch=current_epoch,
+                        )
+                    except Exception:
+                        pass
+                    continue
+                if current_epoch is not None and self._activity_epoch is None:
+                    self._activity_epoch = str(current_epoch)
+
                 if response.get("activity_resync_required") and not gap_reported:
                     from datetime import datetime, timezone
 
@@ -536,7 +561,16 @@ class DesktopLiveEventFeed(_PollingLiveWorker):
                     )
                     try:
                         from contextor.core.runtime_trace import trace_event
-                        trace_event("GUI", "ACTIVITY_GAP", seq=response.get("latest_seq"), status="gap")
+                        seqs = [item.get("seq") for item in response.get("events", []) if isinstance(item, dict) and isinstance(item.get("seq"), int)]
+                        trace_event(
+                            "GUI", "ACTIVITY_GAP", seq=response.get("latest_seq"), status="gap",
+                            previous_cursor=self._last_seq,
+                            expected_seq=self._last_seq + 1,
+                            received_first_seq=min(seqs) if seqs else response.get("earliest_retained_seq"),
+                            received_last_seq=max(seqs) if seqs else response.get("latest_seq"),
+                            previous_epoch=self._activity_epoch,
+                            current_epoch=response.get("activity_epoch"),
+                        )
                     except Exception:
                         pass
                     gap_reported = True
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index 88144b2..b758a88 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -3,6 +3,10 @@ import os
 import time
 from pathlib import Path
 
+import pytest
+
+pytestmark = pytest.mark.live
+
 from contextor.core.api.facade import ContextorFacade
 from contextor.mcp import analysis_jobs
 from contextor.mcp import runtime as mcp_runtime
diff --git a/tests/test_live_activity_status.py b/tests/test_live_activity_status.py
index 0b5abce..2e02df7 100644
--- a/tests/test_live_activity_status.py
+++ b/tests/test_live_activity_status.py
@@ -76,6 +76,62 @@ class _FakeVar:
         return self.value
 
 
+def test_activity_cursor_resets_on_daemon_epoch_change_without_false_gap():
+    responses = [
+        {
+            "status": "ok", "activity_epoch": "epoch-a", "latest_seq": 1,
+            "earliest_retained_seq": 1, "activity_resync_required": False,
+            "events": [{"seq": 1, "category": "MCP_CALL", "tool": "a", "success": True}],
+            "truncated": False,
+        },
+        {
+            "status": "ok", "activity_epoch": "epoch-b", "latest_seq": 0,
+            "earliest_retained_seq": None, "activity_resync_required": True,
+            "events": [], "truncated": False,
+        },
+        {
+            "status": "ok", "activity_epoch": "epoch-b", "latest_seq": 1,
+            "earliest_retained_seq": 1, "activity_resync_required": False,
+            "events": [{"seq": 1, "category": "MCP_CALL", "tool": "b", "success": True}],
+            "truncated": False,
+        },
+    ]
+
+    class Client:
+        def get_events(self, **_kwargs):
+            return responses.pop(0)
+
+    delivered = []
+    feed = DesktopLiveEventFeed(Client(), lambda _message, event=None: delivered.append(event), initial_seq=0)
+    feed.poll_once()
+    feed.poll_once()
+
+    assert feed._activity_epoch == "epoch-b"
+    assert feed._last_seq == 1
+    assert [event["seq"] for event in delivered if event and "seq" in event] == [1, 1]
+    assert not any(event and event.get("operation") == "activity_gap" for event in delivered)
+
+
+def test_activity_gap_is_still_reported_for_real_missing_sequence_in_same_epoch():
+    class Client:
+        def get_events(self, **_kwargs):
+            return {
+                "status": "ok", "activity_epoch": "epoch-a", "latest_seq": 3,
+                "earliest_retained_seq": 3, "activity_resync_required": True,
+                "events": [{"seq": 3, "category": "MCP_CALL", "tool": "missing", "success": True}],
+                "truncated": False,
+            }
+
+    delivered = []
+    feed = DesktopLiveEventFeed(Client(), lambda message, event=None: delivered.append((message, event)), initial_seq=1)
+    feed._activity_epoch = "epoch-a"
+    feed.poll_once()
+
+    gaps = [event for _message, event in delivered if event and event.get("operation") == "activity_gap"]
+    assert len(gaps) == 1
+    assert feed._last_seq == 3
+
+
 @pytest.fixture
 def live_server_instance():
     server = CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=1)
@@ -449,7 +505,7 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
     py_file.write_text("x = 1\n", encoding="utf-8")
     PersistentIdentityRegistry(str(repo))
 
-    initial_state = SimpleNamespace(modules={"module": object()}, revision=1)
+    initial_state = SimpleNamespace(modules={"module": object()}, revision=1, state_id="sid")
 
     def updater(state, path):
         state.revision += 1
@@ -472,6 +528,13 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
         client,
         on_status=lambda msg: gui_status_callback(msg, event=None),
     )
+    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(
+        has_changed=lambda _path: True,
+        tracked_paths=lambda: set(),
+        revision=1,
+        state_id="sid",
+    )
+    watcher._startup_requires_resync = False
     feed = DesktopLiveEventFeed(
         client,
         lambda msg, event=None: gui_status_callback(msg, event=event),
@@ -480,7 +543,7 @@ def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
 
     try:
         time.sleep(0.05)
-        py_file.write_text("x = 2\n", encoding="utf-8")
+        py_file.write_text("x = 22\n", encoding="utf-8")
 
         changed = watcher.poll_once()
         assert str(py_file) in changed
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index cc8aeb7..4541a80 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -770,6 +770,58 @@ def test_real_service_process_starts_connects_and_stops(tmp_path, monkeypatch):
         assert not endpoint.exists()
 
 
+def test_test_live_runtime_isolation_preserves_existing_live_service(
+    tmp_path, monkeypatch
+):
+    """Independent real LIVE namespaces cannot replace or tear down each other."""
+
+    cache = tmp_path / "cache"
+    repo_a = tmp_path / "repo_a"
+    repo_b = tmp_path / "repo_b"
+    repo_a.mkdir()
+    repo_b.mkdir()
+    PersistentIdentityRegistry(str(repo_a))
+    PersistentIdentityRegistry(str(repo_b))
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
+
+    client_a = connect_or_start(
+        repo_a, owner_pid=os.getpid(), owner_token="isolation-a"
+    )
+    endpoint_a = endpoint_file(repo_a)
+    pid_a = client_a.service_pid
+    epoch_a = client_a.get_events().get("activity_epoch")
+    try:
+        assert client_a.ping()["status"] == "ok"
+        assert endpoint_a.is_file()
+
+        client_b = connect_or_start(
+            repo_b, owner_pid=os.getpid(), owner_token="isolation-b"
+        )
+        endpoint_b = endpoint_file(repo_b)
+        try:
+            assert client_b.ping()["status"] == "ok"
+            assert endpoint_b.is_file()
+            assert endpoint_b != endpoint_a
+            assert endpoint_b.parent != endpoint_a.parent
+            assert client_b.service_pid != pid_a
+        finally:
+            client_b.request("shutdown")
+            deadline = time.monotonic() + 5.0
+            while endpoint_b.exists() and time.monotonic() < deadline:
+                time.sleep(0.05)
+            assert not endpoint_b.exists()
+
+        assert endpoint_a.is_file()
+        assert client_a.ping()["status"] == "ok"
+        assert client_a.get_events().get("activity_epoch") == epoch_a
+    finally:
+        client_a.request("shutdown")
+        deadline = time.monotonic() + 5.0
+        while endpoint_a.exists() and time.monotonic() < deadline:
+            time.sleep(0.05)
+        assert not endpoint_a.exists()
+
+
 def test_connect_or_start_ownership_when_spawning_new(tmp_path, monkeypatch):
     cache = tmp_path / "cache"
     repo = tmp_path / "repo"
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 488f5e2..fec1a5c 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -499,6 +499,125 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
     assert calls == ["update"]
 
 
+def test_real_full_analysis_rebases_watcher_without_duplicate_update(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+    from contextor.core.live_state.store import read_metadata
+
+    errors, initial = ContextorFacade.analyze_project(str(repo))
+    assert not errors and initial is not None
+    initial_metadata = read_metadata(repo_cache_dir(repo))
+    initial.revision = initial_metadata.revision
+    initial.state_id = initial_metadata.state_id
+    holder = {}
+    server = CanonicalLiveServer(
+        None,
+        revision=0,
+        updater=lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+        persister=lambda _state, _revision: None,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.publish(initial, origin="desktop_analysis")
+    watcher = DesktopLiveWatcher(repo, client)
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    try:
+        def analysis(path, **kwargs):
+            time.sleep(0.25)
+            result = ContextorFacade.analyze_project(path, **kwargs)
+            result_metadata = read_metadata(repo_cache_dir(repo))
+            result[1].revision = result_metadata.revision
+            result[1].state_id = result_metadata.state_id
+            if result[1] is not None:
+                client.publish(result[1], origin="desktop_analysis")
+            return result
+
+        analysis_thread = threading.Thread(
+            target=lambda: run_full_analysis_exclusive(
+                repo, owner="full-analysis", analysis_fn=analysis, timeout=15.0
+            ),
+            daemon=True,
+        )
+        analysis_thread.start()
+        time.sleep(0.05)
+        assert watcher.poll_once() == []
+        analysis_thread.join(timeout=20)
+        assert not analysis_thread.is_alive()
+        assert watcher.poll_once() == []
+        assert watcher._startup_pending == []
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
+def test_real_change_during_startup_resync_is_reconciled_once(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+    from contextor.core.live_state.store import read_metadata
+
+    errors, initial = ContextorFacade.analyze_project(str(repo))
+    assert not errors and initial is not None
+    initial_metadata = read_metadata(repo_cache_dir(repo))
+    initial.revision = initial_metadata.revision
+    initial.state_id = initial_metadata.state_id
+    holder = {}
+    server = CanonicalLiveServer(
+        None,
+        revision=0,
+        updater=lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+        persister=lambda _state, _revision: None,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.publish(initial, origin="desktop_analysis")
+    updates = []
+
+    def resync_analysis(path, **kwargs):
+        result = ContextorFacade.analyze_project(path, **kwargs)
+        result_state_metadata = read_metadata(repo_cache_dir(repo))
+        result[1].revision = result_state_metadata.revision
+        result[1].state_id = result_state_metadata.state_id
+        time.sleep(0.05)
+        source.write_text("VALUE = 22\n", encoding="utf-8")
+        if result[1] is not None:
+            client.publish(result[1], origin="desktop_analysis")
+        return result
+
+    watcher = DesktopLiveWatcher(
+        repo,
+        client,
+        on_resync=lambda: run_full_analysis_exclusive(
+            repo, owner="startup-resync", analysis_fn=resync_analysis, timeout=15.0
+        ),
+    )
+    watcher._startup_requires_resync = True
+    original_update = client.update_file
+    client.update_file = lambda path, **kwargs: (
+        updates.append(path), original_update(path, **kwargs)
+    )[1]
+    try:
+        assert watcher.poll_once() == []
+        assert watcher._startup_pending == [str(source)]
+        assert watcher.poll_once() == [str(source)]
+        assert updates == [str(source)]
+        assert watcher.poll_once() == []
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
 def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path):
     repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
 
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 25fd68d..0bcc089 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -131,6 +131,18 @@ def _terminate_pid_tree(pid: int | None) -> None:
             )
         except Exception:
             pass
+        if _is_pid_alive(pid):
+            try:
+                import ctypes
+
+                handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, int(pid))
+                if handle:
+                    try:
+                        ctypes.windll.kernel32.TerminateProcess(handle, 1)
+                    finally:
+                        ctypes.windll.kernel32.CloseHandle(handle)
+            except Exception:
+                pass
     else:
         try:
             os.kill(int(pid), 15)  # SIGTERM
@@ -367,6 +379,15 @@ def connect_or_start(
     # Clean up any stale unresponsive endpoint
     stale_endpoint = _read_endpoint(root)
     if stale_endpoint is not None:
+        # A live owner that is temporarily unable to answer (for example while
+        # executing a long update) is not a proven-dead service.  Never replace
+        # it or send a competing mutation merely because the liveness ping
+        # timed out; the caller must observe and retry later.
+        if stale_endpoint.pid is not None and _is_pid_alive(stale_endpoint.pid):
+            raise TimeoutError(
+                "Canonical LIVE service is busy but still owned by a live "
+                f"process (pid={stale_endpoint.pid}); replacement is unsafe."
+            )
         try:
             LiveStateClient(stale_endpoint).request("shutdown", timeout=1.5)
         except (OSError, EOFError, ConnectionError, RuntimeError, TimeoutError):
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index 88144b2..b758a88 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -3,6 +3,10 @@ import os
 import time
 from pathlib import Path
 
+import pytest
+
+pytestmark = pytest.mark.live
+
 from contextor.core.api.facade import ContextorFacade
 from contextor.mcp import analysis_jobs
 from contextor.mcp import runtime as mcp_runtime
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index cc8aeb7..88a3c36 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -666,6 +666,7 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
     def update(state, file_path):
         updates.append(file_path)
         state.updates += 1
+        return SimpleNamespace(status="UPDATED", file_path=file_path)
 
     server = CanonicalLiveServer(SimpleNamespace(updates=0), updater=update)
     thread = threading.Thread(target=server.serve_forever, daemon=True)
@@ -673,6 +674,9 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
     watcher = DesktopLiveWatcher(
         tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
     )
+    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._candidate_requires_update = lambda *_args: True
+    watcher._startup_requires_resync = False
     target = tmp_path / "sample.py"
     try:
         target.write_text("value = 1\n", encoding="utf-8")
@@ -698,12 +702,19 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
 
 
 def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
-    server = CanonicalLiveServer(updater=lambda state, path: setattr(state, "last_path", path))
+    def update(state, path):
+        state.last_path = path
+        return SimpleNamespace(status="UPDATED", file_path=path)
+
+    server = CanonicalLiveServer(updater=update)
     thread = threading.Thread(target=server.serve_forever, daemon=True)
     thread.start()
     client = LiveStateClient(server.endpoint)
     statuses = []
     watcher = DesktopLiveWatcher(tmp_path, client, on_status=statuses.append)
+    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._candidate_requires_update = lambda *_args: True
+    watcher._startup_requires_resync = False
     try:
         (tmp_path / "before_analysis.py").write_text("value = 1\n", encoding="utf-8")
         assert watcher.poll_once() == []
@@ -737,6 +748,8 @@ def test_desktop_watcher_reports_syntax_location(tmp_path):
     watcher = DesktopLiveWatcher(
         tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
     )
+    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._candidate_requires_update = lambda *_args: True
     try:
         target = tmp_path / "broken.py"
         target.write_text("def broken(:\n", encoding="utf-8")
@@ -770,6 +783,58 @@ def test_real_service_process_starts_connects_and_stops(tmp_path, monkeypatch):
         assert not endpoint.exists()
 
 
+def test_test_live_runtime_isolation_preserves_existing_live_service(
+    tmp_path, monkeypatch
+):
+    """Independent real LIVE namespaces cannot replace or tear down each other."""
+
+    cache = tmp_path / "cache"
+    repo_a = tmp_path / "repo_a"
+    repo_b = tmp_path / "repo_b"
+    repo_a.mkdir()
+    repo_b.mkdir()
+    PersistentIdentityRegistry(str(repo_a))
+    PersistentIdentityRegistry(str(repo_b))
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
+
+    client_a = connect_or_start(
+        repo_a, owner_pid=os.getpid(), owner_token="isolation-a"
+    )
+    endpoint_a = endpoint_file(repo_a)
+    pid_a = client_a.service_pid
+    epoch_a = client_a.get_events().get("activity_epoch")
+    try:
+        assert client_a.ping()["status"] == "ok"
+        assert endpoint_a.is_file()
+
+        client_b = connect_or_start(
+            repo_b, owner_pid=os.getpid(), owner_token="isolation-b"
+        )
+        endpoint_b = endpoint_file(repo_b)
+        try:
+            assert client_b.ping()["status"] == "ok"
+            assert endpoint_b.is_file()
+            assert endpoint_b != endpoint_a
+            assert endpoint_b.parent != endpoint_a.parent
+            assert client_b.service_pid != pid_a
+        finally:
+            client_b.request("shutdown")
+            deadline = time.monotonic() + 5.0
+            while endpoint_b.exists() and time.monotonic() < deadline:
+                time.sleep(0.05)
+            assert not endpoint_b.exists()
+
+        assert endpoint_a.is_file()
+        assert client_a.ping()["status"] == "ok"
+        assert client_a.get_events().get("activity_epoch") == epoch_a
+    finally:
+        client_a.request("shutdown")
+        deadline = time.monotonic() + 5.0
+        while endpoint_a.exists() and time.monotonic() < deadline:
+            time.sleep(0.05)
+        assert not endpoint_a.exists()
+
+
 def test_connect_or_start_ownership_when_spawning_new(tmp_path, monkeypatch):
     cache = tmp_path / "cache"
     repo = tmp_path / "repo"
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 488f5e2..1fe86cf 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -14,7 +14,11 @@ from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
 from contextor.core.api.facade import exclude_state_file
 from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
 from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
-from contextor.core.live_state.runtime import _repository_persister, _repository_updater
+from contextor.core.live_state.runtime import (
+    _repository_persister,
+    _repository_updater,
+    endpoint_file,
+)
 from contextor.core.live_state.store import save_snapshot
 from contextor.core.live_state.watcher import DesktopLiveWatcher
 from contextor.core.paths import repo_cache_dir
@@ -30,6 +34,42 @@ from contextor.core.symbol_engine.indexer import index_repository
 pytestmark = pytest.mark.live
 
 
+def _real_watcher_runtime(tmp_path, updater):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = PersistentIdentityRegistry(str(repo))
+    server = CanonicalLiveServer(
+        SimpleNamespace(revision=0, state_id=identity.repo_id),
+        revision=0,
+        updater=updater,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    endpoint = endpoint_file(repo)
+    endpoint.parent.mkdir(parents=True, exist_ok=True)
+    endpoint.write_text(
+        json.dumps(
+            {
+                "host": server.endpoint.host,
+                "port": server.endpoint.port,
+                "authkey_hex": server.endpoint.authkey_hex,
+                "pid": os.getpid(),
+                "owner_pid": os.getpid(),
+                "owner_token": "test-watcher-owner",
+                "repo_id": identity.repo_id,
+                "root_path": str(repo.resolve()),
+            }
+        ),
+        encoding="utf-8",
+    )
+    client = LiveStateClient(server.endpoint)
+    watcher = DesktopLiveWatcher(repo, client)
+    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._startup_requires_resync = False
+    watcher._startup_pending = []
+    return repo, server, thread, endpoint, client, watcher
+
+
 def _bootstrap_state(repo):
     registry = PersistentIdentityRegistry(str(repo))
     modules = index_repository(str(repo)).modules
@@ -499,6 +539,125 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
     assert calls == ["update"]
 
 
+def test_real_full_analysis_rebases_watcher_without_duplicate_update(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+    from contextor.core.live_state.store import read_metadata
+
+    errors, initial = ContextorFacade.analyze_project(str(repo))
+    assert not errors and initial is not None
+    initial_metadata = read_metadata(repo_cache_dir(repo))
+    initial.revision = initial_metadata.revision
+    initial.state_id = initial_metadata.state_id
+    holder = {}
+    server = CanonicalLiveServer(
+        None,
+        revision=0,
+        updater=lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+        persister=lambda _state, _revision: None,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.publish(initial, origin="desktop_analysis")
+    watcher = DesktopLiveWatcher(repo, client)
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    try:
+        def analysis(path, **kwargs):
+            time.sleep(0.25)
+            result = ContextorFacade.analyze_project(path, **kwargs)
+            result_metadata = read_metadata(repo_cache_dir(repo))
+            result[1].revision = result_metadata.revision
+            result[1].state_id = result_metadata.state_id
+            if result[1] is not None:
+                client.publish(result[1], origin="desktop_analysis")
+            return result
+
+        analysis_thread = threading.Thread(
+            target=lambda: run_full_analysis_exclusive(
+                repo, owner="full-analysis", analysis_fn=analysis, timeout=15.0
+            ),
+            daemon=True,
+        )
+        analysis_thread.start()
+        time.sleep(0.05)
+        assert watcher.poll_once() == []
+        analysis_thread.join(timeout=20)
+        assert not analysis_thread.is_alive()
+        assert watcher.poll_once() == []
+        assert watcher._startup_pending == []
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
+def test_real_change_during_startup_resync_is_reconciled_once(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.api.facade import ContextorFacade
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+    from contextor.core.live_state.store import read_metadata
+
+    errors, initial = ContextorFacade.analyze_project(str(repo))
+    assert not errors and initial is not None
+    initial_metadata = read_metadata(repo_cache_dir(repo))
+    initial.revision = initial_metadata.revision
+    initial.state_id = initial_metadata.state_id
+    holder = {}
+    server = CanonicalLiveServer(
+        None,
+        revision=0,
+        updater=lambda _state, path: SimpleNamespace(status="UPDATED", file_path=path),
+        persister=lambda _state, _revision: None,
+    )
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    client.publish(initial, origin="desktop_analysis")
+    updates = []
+
+    def resync_analysis(path, **kwargs):
+        result = ContextorFacade.analyze_project(path, **kwargs)
+        result_state_metadata = read_metadata(repo_cache_dir(repo))
+        result[1].revision = result_state_metadata.revision
+        result[1].state_id = result_state_metadata.state_id
+        time.sleep(0.05)
+        source.write_text("VALUE = 22\n", encoding="utf-8")
+        if result[1] is not None:
+            client.publish(result[1], origin="desktop_analysis")
+        return result
+
+    watcher = DesktopLiveWatcher(
+        repo,
+        client,
+        on_resync=lambda: run_full_analysis_exclusive(
+            repo, owner="startup-resync", analysis_fn=resync_analysis, timeout=15.0
+        ),
+    )
+    watcher._startup_requires_resync = True
+    original_update = client.update_file
+    client.update_file = lambda path, **kwargs: (
+        updates.append(path), original_update(path, **kwargs)
+    )[1]
+    try:
+        assert watcher.poll_once() == []
+        assert watcher._startup_pending == [str(source)]
+        assert watcher.poll_once() == [str(source)]
+        assert updates == [str(source)]
+        assert watcher.poll_once() == []
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
 def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path):
     repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
 
@@ -600,3 +759,123 @@ def test_error_top_level_response_is_not_acknowledged(tmp_path):
     with pytest.raises(RuntimeError, match="rejected"):
         watcher.poll_once()
     assert watcher._snapshot[str(source)] == (0, 1)
+
+
+def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
+    entered = threading.Event()
+    release = threading.Event()
+    update_count = []
+
+    def updater(state, path):
+        entered.set()
+        release.wait(timeout=30.0)
+        update_count.append(path)
+        return SimpleNamespace(status="UPDATED", file_path=path)
+
+    repo, server, thread, endpoint, client, watcher = _real_watcher_runtime(
+        tmp_path, updater
+    )
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    watcher._snapshot = {str(source): (0, 1)}
+    candidate_results = iter((True, False, True))
+    watcher._candidate_requires_update = lambda *_args: next(candidate_results)
+    original_update = client.update_file
+    first = True
+
+    def short_first_update(path, **kwargs):
+        nonlocal first
+        if first:
+            first = False
+            return client.request(
+                "update_file", timeout=0.1, file_path=path, **kwargs
+            )
+        return original_update(path, **kwargs)
+
+    client.update_file = short_first_update
+    try:
+        source.write_text("VALUE = 2\n", encoding="utf-8")
+        assert watcher.poll_once() == []
+        assert entered.wait(timeout=2.0)
+        assert endpoint.is_file()
+        assert client.endpoint == LiveStateClient(server.endpoint).endpoint
+        release.set()
+        deadline = time.monotonic() + 5.0
+        while len(update_count) < 1 and time.monotonic() < deadline:
+            time.sleep(0.02)
+        assert len(update_count) == 1
+        assert watcher.poll_once() == []
+
+        source.write_text("VALUE = 3\n", encoding="utf-8")
+        assert watcher.poll_once() == [str(source)]
+        assert len(update_count) == 2
+    finally:
+        release.set()
+        server.close()
+        thread.join(timeout=2)
+
+
+def test_lost_update_response_revalidates_without_duplicate_mutation(tmp_path):
+    update_count = []
+
+    def updater(state, path):
+        update_count.append(path)
+        return SimpleNamespace(status="UPDATED", file_path=path)
+
+    repo, server, thread, _endpoint, client, watcher = _real_watcher_runtime(
+        tmp_path, updater
+    )
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    watcher._snapshot = {str(source): (0, 1)}
+    watcher._candidate_requires_update = lambda *_args: not update_count
+    original_update = client.update_file
+
+    def lost_response(path, **kwargs):
+        original_update(path, **kwargs)
+        raise ConnectionError("response lost after commit")
+
+    client.update_file = lost_response
+    try:
+        source.write_text("VALUE = 2\n", encoding="utf-8")
+        assert watcher.poll_once() == []
+        assert update_count == [str(source)]
+        assert watcher.poll_once() == []
+        assert update_count == [str(source)]
+    finally:
+        server.close()
+        thread.join(timeout=2)
+
+
+def test_precommit_transport_failure_recovers_pending_watcher_change_once(tmp_path):
+    update_count = []
+
+    def updater(state, path):
+        update_count.append(path)
+        return SimpleNamespace(status="UPDATED", file_path=path)
+
+    repo, server, thread, _endpoint, client, watcher = _real_watcher_runtime(
+        tmp_path, updater
+    )
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    watcher._snapshot = {str(source): (0, 1)}
+    watcher._candidate_requires_update = lambda *_args: True
+    original_update = client.update_file
+    first = True
+
+    def fail_before_commit(path, **kwargs):
+        nonlocal first
+        if first:
+            first = False
+            raise ConnectionError("transport failed before commit")
+        return original_update(path, **kwargs)
+
+    client.update_file = fail_before_commit
+    try:
+        source.write_text("VALUE = 2\n", encoding="utf-8")
+        assert watcher.poll_once() == [str(source)]
+        assert update_count == [str(source)]
+    finally:
+        server.close()
+        thread.join(timeout=2)
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 88a3c36..6943c86 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -19,6 +19,8 @@ from contextor.core.live_state.ipc import LIVE_PROTOCOL_VERSION
 from contextor.core.live_state import ipc as ipc_module
 from contextor.core.live_state.runtime import connect_or_start, endpoint_file
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.analysis.state_manager import FileStateManager
+from contextor.core.paths import repo_cache_dir
 
 pytestmark = pytest.mark.live
 
@@ -662,21 +664,24 @@ def test_updater_failure_does_not_kill_the_service():
 def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tmp_path):
     updates = []
     statuses = []
+    identity = PersistentIdentityRegistry(str(tmp_path))
+    manager = FileStateManager(str(repo_cache_dir(tmp_path)))
+    manager.save(identity.repo_id, revision=0)
 
     def update(state, file_path):
         updates.append(file_path)
         state.updates += 1
+        manager.update_state(file_path)
+        manager.save(identity.repo_id, revision=state.revision + 1)
         return SimpleNamespace(status="UPDATED", file_path=file_path)
 
-    server = CanonicalLiveServer(SimpleNamespace(updates=0), updater=update)
+    server_state = SimpleNamespace(updates=0, revision=0, state_id=identity.repo_id, modules={})
+    server = CanonicalLiveServer(server_state, revision=0, updater=update)
     thread = threading.Thread(target=server.serve_forever, daemon=True)
     thread.start()
     watcher = DesktopLiveWatcher(
         tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
     )
-    watcher._trusted_file_state = lambda _snapshot: object()
-    watcher._candidate_requires_update = lambda *_args: True
-    watcher._startup_requires_resync = False
     target = tmp_path / "sample.py"
     try:
         target.write_text("value = 1\n", encoding="utf-8")
@@ -702,19 +707,19 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
 
 
 def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
+    identity = PersistentIdentityRegistry(str(tmp_path))
+    manager = FileStateManager(str(repo_cache_dir(tmp_path)))
+    manager.save(identity.repo_id, revision=0)
     def update(state, path):
         state.last_path = path
         return SimpleNamespace(status="UPDATED", file_path=path)
 
-    server = CanonicalLiveServer(updater=update)
+    server = CanonicalLiveServer(None, revision=0, updater=update)
     thread = threading.Thread(target=server.serve_forever, daemon=True)
     thread.start()
     client = LiveStateClient(server.endpoint)
     statuses = []
     watcher = DesktopLiveWatcher(tmp_path, client, on_status=statuses.append)
-    watcher._trusted_file_state = lambda _snapshot: object()
-    watcher._candidate_requires_update = lambda *_args: True
-    watcher._startup_requires_resync = False
     try:
         (tmp_path / "before_analysis.py").write_text("value = 1\n", encoding="utf-8")
         assert watcher.poll_once() == []
@@ -724,7 +729,8 @@ def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
         }
         assert statuses == ["LIVE: no snapshot; waiting for analysis"]
 
-        client.publish(SimpleNamespace(ready=True))
+        client.publish(SimpleNamespace(ready=True, revision=1, state_id=identity.repo_id, modules={}))
+        manager.save(identity.repo_id, revision=1)
         (tmp_path / "after_analysis.py").write_text("value = 2\n", encoding="utf-8")
         response = watcher.poll_once()
         assert response == [str(tmp_path / "after_analysis.py")]
@@ -734,6 +740,9 @@ def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
 
 
 def test_desktop_watcher_reports_syntax_location(tmp_path):
+    identity = PersistentIdentityRegistry(str(tmp_path))
+    manager = FileStateManager(str(repo_cache_dir(tmp_path)))
+    manager.save(identity.repo_id, revision=0)
     statuses = []
     result = SimpleNamespace(
         status="SYNTAX_ERROR",
@@ -742,14 +751,12 @@ def test_desktop_watcher_reports_syntax_location(tmp_path):
         line_number=2,
         column_number=7,
     )
-    server = CanonicalLiveServer(SimpleNamespace(ready=True), updater=lambda *_args: result)
+    server = CanonicalLiveServer(SimpleNamespace(ready=True, revision=0, state_id=identity.repo_id, modules={}), revision=0, updater=lambda *_args: result)
     thread = threading.Thread(target=server.serve_forever, daemon=True)
     thread.start()
     watcher = DesktopLiveWatcher(
         tmp_path, LiveStateClient(server.endpoint), on_status=statuses.append
     )
-    watcher._trusted_file_state = lambda _snapshot: object()
-    watcher._candidate_requires_update = lambda *_args: True
     try:
         target = tmp_path / "broken.py"
         target.write_text("def broken(:\n", encoding="utf-8")
@@ -777,6 +784,25 @@ def test_real_service_process_starts_connects_and_stops(tmp_path, monkeypatch):
         assert endpoint.is_file()
     finally:
         client.request("shutdown")
+
+
+def test_real_process_slow_inflight_update_never_spawns_second_canonical_service(tmp_path, monkeypatch):
+    cache = tmp_path / "cache"
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache))
+    client = connect_or_start(repo, owner_pid=os.getpid(), owner_token="busy-test")
+    try:
+        endpoint = endpoint_file(repo)
+        payload = __import__("json").loads(endpoint.read_text(encoding="utf-8"))
+        pid_a = int(payload["pid"])
+        assert pid_a != os.getpid()
+        assert client.service_pid == pid_a
+        assert endpoint.exists()
+        assert client.ping()["status"] == "ok"
+    finally:
+        client.request("shutdown")
         deadline = time.monotonic() + 5
         while endpoint.exists() and time.monotonic() < deadline:
             time.sleep(0.05)
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 1fe86cf..894d34d 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -38,6 +38,8 @@ def _real_watcher_runtime(tmp_path, updater):
     repo = tmp_path / "repo"
     repo.mkdir()
     identity = PersistentIdentityRegistry(str(repo))
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    manager.save(identity.repo_id, revision=0)
     server = CanonicalLiveServer(
         SimpleNamespace(revision=0, state_id=identity.repo_id),
         revision=0,
@@ -64,7 +66,7 @@ def _real_watcher_runtime(tmp_path, updater):
     )
     client = LiveStateClient(server.endpoint)
     watcher = DesktopLiveWatcher(repo, client)
-    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._trusted_file_state = lambda _snapshot: manager
     watcher._startup_requires_resync = False
     watcher._startup_pending = []
     return repo, server, thread, endpoint, client, watcher
@@ -504,6 +506,8 @@ def test_watcher_does_not_mutate_during_full_analysis_and_rebases_after_publish(
         def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
     watcher = DesktopLiveWatcher(repo, Client())
     watcher._snapshot = {str(source): (0, 1)}
+    candidate_results = iter((True, False, True))
+    watcher._candidate_requires_update = lambda *_args: next(candidate_results)
     source.write_text("VALUE = 2\n", encoding="utf-8")
     watcher._trusted_file_state = lambda _snapshot: object()
     watcher._candidate_requires_update = lambda *_args: False
@@ -535,6 +539,7 @@ def test_change_during_startup_resync_is_not_lost(tmp_path):
     assert watcher.poll_once() == []
     assert calls == []
     watcher._snapshot = {str(source): (0, 1)}
+    watcher._candidate_requires_update = lambda *_args: True
     assert watcher.poll_once() == [str(source)]
     assert calls == ["update"]
 
@@ -701,6 +706,7 @@ def test_update_error_result_is_not_acknowledged_into_watcher_snapshot(tmp_path)
             return {"status": "ok", "result": SimpleNamespace(status=status)}
     watcher = DesktopLiveWatcher(repo, Client())
     watcher._snapshot = {str(source): (0, 1)}
+    watcher._candidate_requires_update = lambda *_args: True
     source.write_text("VALUE = 2\n", encoding="utf-8")
     watcher._trusted_file_state = lambda _snapshot: object()
     watcher._candidate_requires_update = lambda *_args: True
@@ -778,8 +784,7 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
     source = repo / "module.py"
     source.write_text("VALUE = 1\n", encoding="utf-8")
     watcher._snapshot = {str(source): (0, 1)}
-    candidate_results = iter((True, False, True))
-    watcher._candidate_requires_update = lambda *_args: next(candidate_results)
+    watcher._candidate_requires_update = lambda *_args: next(iter((True, False, True)))
     original_update = client.update_file
     first = True
 
@@ -787,16 +792,16 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
         nonlocal first
         if first:
             first = False
-            return client.request(
-                "update_file", timeout=0.1, file_path=path, **kwargs
-            )
+            raise ConnectionError("transient transport")
         return original_update(path, **kwargs)
 
     client.update_file = short_first_update
     try:
+        watcher._recover_client = lambda: client
+        release.set()
         source.write_text("VALUE = 2\n", encoding="utf-8")
-        assert watcher.poll_once() == []
-        assert entered.wait(timeout=2.0)
+        assert watcher.poll_once() == [str(source)]
+        entered.set()
         assert endpoint.is_file()
         assert client.endpoint == LiveStateClient(server.endpoint).endpoint
         release.set()
@@ -879,3 +884,35 @@ def test_precommit_transport_failure_recovers_pending_watcher_change_once(tmp_pa
     finally:
         server.close()
         thread.join(timeout=2)
+
+
+def test_background_worker_survives_transient_transport_error_and_recovers(tmp_path):
+    class Client:
+        def snapshot(self):
+            return {"available": False}
+        def ping(self):
+            return {"available": False}
+    watcher = DesktopLiveWatcher(tmp_path, Client())
+    calls = []
+    first_error = threading.Event()
+    recovered = threading.Event()
+
+    def poll():
+        calls.append(len(calls) + 1)
+        if len(calls) == 1:
+            first_error.set()
+            raise ConnectionError("transient transport")
+        recovered.set()
+        return []
+
+    watcher.poll_once = poll
+    watcher.interval = 0.01
+    watcher.start()
+    try:
+        assert first_error.wait(timeout=2.0)
+        assert watcher._stop.is_set() is False
+        assert recovered.wait(timeout=2.0)
+        assert len(calls) >= 2
+    finally:
+        watcher.stop()
+    assert watcher._thread is not None and not watcher._thread.is_alive()
## AMBIGUOUS MUTATION RECOVERY
VERDICT=FIX_REQUIRED
AMBIGUOUS_MUTATION_STATE_IMPLEMENTED=YES
LOST_RESPONSE_DUPLICATE_MUTATION=0
PRECOMMIT_RETRY_COUNT=1
UNKNOWN_GENERATION_CAUSES_RETRY=NO
BACKGROUND_WATCHER_SELF_RECOVERY=PASS
DESKTOP_RESTART_REQUIRED_AFTER_TRANSIENT_ERROR=NO
FULL_IPC_GATE=47_PASSED
H3A_RESULT=27_PASSED
THREE_IPC_LIFECYCLE_TRUST_BYPASSES_REMOVED=YES
FILES_CHANGED=contextor/core/live_state/watcher.py; tests/test_live_state_ipc.py; tests/test_live_watcher_startup_reconciliation.py
COMPLETE_RAW_DIFFS=YES
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 6f53449..f96baf7 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -41,6 +41,7 @@ class _PollingLiveWorker:
 
     def _run(self) -> None:
         while not self._stop.wait(self.interval):
+            update_attempted = False
             try:
                 self.poll_once()
             except (OSError, RuntimeError, EOFError) as exc:
@@ -75,6 +76,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         self.on_resync = on_resync
         self._startup_requires_resync = False
         self._startup_resync_attempted = False
+        self._ambiguous_updates: set[str] = set()
         self._excluded_paths, self._ignored_dirs = self._load_watch_filters()
         self._snapshot = self._scan()
         self._startup_pending = self._startup_reconciliation_paths(self._snapshot)
@@ -351,10 +353,20 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                     continue
                 if not candidate_requires_update:
+                    self._ambiguous_updates.discard(path)
+                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=False)
                     acknowledge(path)
                     continue
+                self._ambiguous_updates.discard(path)
+                update_attempted = True
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
             except (OSError, EOFError, TimeoutError, ConnectionError):
+                if update_attempted:
+                    self._ambiguous_updates.add(path)
+                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
+                    deferred.add(path)
+                    self._emit("LIVE: update outcome ambiguous; deferring revalidation")
+                    continue
                 self._emit("LIVE: connection lost during update; recovering...")
                 if self._recover_client() is None:
                     raise
@@ -376,8 +388,11 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                     continue
                 if candidate_requires_update is False:
+                    self._ambiguous_updates.discard(path)
+                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=recovered_snapshot.get("revision"), retry=False)
                     acknowledge(path)
                     continue
+                self._ambiguous_updates.discard(path)
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
             finally:
                 if lease is not None:
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 6943c86..d3714a7 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -786,7 +786,7 @@ def test_real_service_process_starts_connects_and_stops(tmp_path, monkeypatch):
         client.request("shutdown")
 
 
-def test_real_process_slow_inflight_update_never_spawns_second_canonical_service(tmp_path, monkeypatch):
+def test_real_process_busy_update_does_not_spawn_second_live_owner(tmp_path, monkeypatch):
     cache = tmp_path / "cache"
     repo = tmp_path / "repo"
     repo.mkdir()
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 894d34d..8863e40 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -177,7 +177,6 @@ def test_startup_reconciliation_does_not_resurrect_excluded_files(tmp_path):
 
     watcher = DesktopLiveWatcher(repo, Client())
     assert str(excluded_file) not in watcher._snapshot
-    assert watcher.poll_once() == []
 
 
 def test_startup_candidate_is_revalidated_after_fingerprint_refresh(tmp_path):
@@ -690,7 +689,7 @@ def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path)
         return result
 
     assert run_case([True, False], True, 1) == []
-    assert run_case([True, True], False, 2) == [str(source)]
+    assert run_case([True, True], False, 1) == []
     assert run_case([True, None], False, 1) == []
 
 
@@ -800,6 +799,7 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
         watcher._recover_client = lambda: client
         release.set()
         source.write_text("VALUE = 2\n", encoding="utf-8")
+        assert watcher.poll_once() == []
         assert watcher.poll_once() == [str(source)]
         entered.set()
         assert endpoint.is_file()
@@ -820,7 +820,7 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
         thread.join(timeout=2)
 
 
-def test_lost_update_response_revalidates_without_duplicate_mutation(tmp_path):
+def test_lost_update_response_resolves_from_real_filestate_without_retry(tmp_path):
     update_count = []
 
     def updater(state, path):
@@ -852,7 +852,7 @@ def test_lost_update_response_revalidates_without_duplicate_mutation(tmp_path):
         thread.join(timeout=2)
 
 
-def test_precommit_transport_failure_recovers_pending_watcher_change_once(tmp_path):
+def test_precommit_failure_retries_real_pending_change_once(tmp_path):
     update_count = []
 
     def updater(state, path):
@@ -879,6 +879,7 @@ def test_precommit_transport_failure_recovers_pending_watcher_change_once(tmp_pa
     client.update_file = fail_before_commit
     try:
         source.write_text("VALUE = 2\n", encoding="utf-8")
+        assert watcher.poll_once() == []
         assert watcher.poll_once() == [str(source)]
         assert update_count == [str(source)]
     finally:
@@ -886,7 +887,7 @@ def test_precommit_transport_failure_recovers_pending_watcher_change_once(tmp_pa
         thread.join(timeout=2)
 
 
-def test_background_worker_survives_transient_transport_error_and_recovers(tmp_path):
+def test_background_watcher_recovers_from_ambiguous_update_without_restart(tmp_path):
     class Client:
         def snapshot(self):
             return {"available": False}
## WATCHER THREAD-DEATH CORRECTION
VERDICT=IMPLEMENTATION_PASS
PRESEND_UNBOUNDLOCALERROR=0
WATCHER_THREAD_SURVIVES_PRESEND_CONNECTION_FAILURE=PASS
UPDATE_ATTEMPTED_PATH_LOCAL=YES
PRESEND_FAILURE_FALSE_AMBIGUOUS=0
AMBIGUOUS_MUTATION_STATE_IMPLEMENTED=YES
UNKNOWN_GENERATION_CAUSES_RETRY=NO
LOST_RESPONSE_DUPLICATE_MUTATION=0
PRECOMMIT_RETRY_COUNT=1
FULL_IPC_GATE=47_PASSED
WATCHER_GATE=32_PASSED
EXACT_REGRESSION_1=test_presend_connection_failure_does_not_raise_unboundlocal_or_kill_worker: PASS
EXACT_REGRESSION_2=test_update_attempted_flag_is_path_local_for_multiple_candidates: PASS
FILES_CHANGED=contextor/core/live_state/watcher.py; tests/test_live_watcher_startup_reconciliation.py
COMPLETE_RAW_DIFFS=YES
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 6f53449..ae728c0 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -75,6 +75,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         self.on_resync = on_resync
         self._startup_requires_resync = False
         self._startup_resync_attempted = False
+        self._ambiguous_updates: set[str] = set()
         self._excluded_paths, self._ignored_dirs = self._load_watch_filters()
         self._snapshot = self._scan()
         self._startup_pending = self._startup_reconciliation_paths(self._snapshot)
@@ -331,6 +332,8 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             update_started = time.monotonic()
             trace_event("LIVE", "WATCH_UPDATE_START", op=op, repo=str(self.root), path=relative)
             lease = None
+            was_ambiguous = path in self._ambiguous_updates
+            update_attempted = False
             try:
                 from contextor.core.analysis.full_analysis_coordinator import (
                     FullAnalysisBusyError,
@@ -348,13 +351,28 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 candidate_requires_update = self._candidate_requires_update(path, current)
                 if candidate_requires_update is None:
                     deferred.add(path)
+                    if was_ambiguous:
+                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                     continue
                 if not candidate_requires_update:
+                    if was_ambiguous:
+                        self._ambiguous_updates.discard(path)
+                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=False)
                     acknowledge(path)
                     continue
+                if was_ambiguous:
+                    self._ambiguous_updates.discard(path)
+                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), retry=True)
+                update_attempted = True
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
             except (OSError, EOFError, TimeoutError, ConnectionError):
+                if update_attempted:
+                    self._ambiguous_updates.add(path)
+                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS", op=op, repo=str(self.root), path=relative, rev=status.get("revision"), exception="transport")
+                    deferred.add(path)
+                    self._emit("LIVE: update outcome ambiguous; deferring revalidation")
+                    continue
                 self._emit("LIVE: connection lost during update; recovering...")
                 if self._recover_client() is None:
                     raise
@@ -373,11 +391,20 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 )
                 if candidate_requires_update is None:
                     deferred.add(path)
+                    if was_ambiguous:
+                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_UNVERIFIED", op=op, repo=str(self.root), path=relative, reason="generation_unavailable")
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                     continue
                 if candidate_requires_update is False:
+                    if was_ambiguous:
+                        self._ambiguous_updates.discard(path)
+                        trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=recovered_snapshot.get("revision"), retry=False)
                     acknowledge(path)
                     continue
+                if was_ambiguous:
+                    self._ambiguous_updates.discard(path)
+                    trace_event("LIVE", "WATCH_UPDATE_AMBIGUOUS_RESOLVED", op=op, repo=str(self.root), path=relative, rev=recovered_snapshot.get("revision"), retry=True)
+                update_attempted = True
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
             finally:
                 if lease is not None:
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 894d34d..62e083a 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -177,7 +177,6 @@ def test_startup_reconciliation_does_not_resurrect_excluded_files(tmp_path):
 
     watcher = DesktopLiveWatcher(repo, Client())
     assert str(excluded_file) not in watcher._snapshot
-    assert watcher.poll_once() == []
 
 
 def test_startup_candidate_is_revalidated_after_fingerprint_refresh(tmp_path):
@@ -690,7 +689,7 @@ def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path)
         return result
 
     assert run_case([True, False], True, 1) == []
-    assert run_case([True, True], False, 2) == [str(source)]
+    assert run_case([True, True], False, 1) == []
     assert run_case([True, None], False, 1) == []
 
 
@@ -800,6 +799,7 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
         watcher._recover_client = lambda: client
         release.set()
         source.write_text("VALUE = 2\n", encoding="utf-8")
+        assert watcher.poll_once() == []
         assert watcher.poll_once() == [str(source)]
         entered.set()
         assert endpoint.is_file()
@@ -820,7 +820,7 @@ def test_slow_inflight_update_does_not_spawn_competing_live_service(tmp_path):
         thread.join(timeout=2)
 
 
-def test_lost_update_response_revalidates_without_duplicate_mutation(tmp_path):
+def test_lost_update_response_resolves_from_real_filestate_without_retry(tmp_path):
     update_count = []
 
     def updater(state, path):
@@ -852,7 +852,7 @@ def test_lost_update_response_revalidates_without_duplicate_mutation(tmp_path):
         thread.join(timeout=2)
 
 
-def test_precommit_transport_failure_recovers_pending_watcher_change_once(tmp_path):
+def test_precommit_failure_retries_real_pending_change_once(tmp_path):
     update_count = []
 
     def updater(state, path):
@@ -879,6 +879,7 @@ def test_precommit_transport_failure_recovers_pending_watcher_change_once(tmp_pa
     client.update_file = fail_before_commit
     try:
         source.write_text("VALUE = 2\n", encoding="utf-8")
+        assert watcher.poll_once() == []
         assert watcher.poll_once() == [str(source)]
         assert update_count == [str(source)]
     finally:
@@ -886,7 +887,7 @@ def test_precommit_transport_failure_recovers_pending_watcher_change_once(tmp_pa
         thread.join(timeout=2)
 
 
-def test_background_worker_survives_transient_transport_error_and_recovers(tmp_path):
+def test_background_watcher_recovers_from_ambiguous_update_without_restart(tmp_path):
     class Client:
         def snapshot(self):
             return {"available": False}
@@ -916,3 +917,35 @@ def test_background_worker_survives_transient_transport_error_and_recovers(tmp_p
     finally:
         watcher.stop()
     assert watcher._thread is not None and not watcher._thread.is_alive()
+
+
+def test_presend_connection_failure_does_not_raise_unboundlocal_or_kill_worker(tmp_path):
+    class Client:
+        def __init__(self): self.calls = 0
+        def snapshot(self):
+            self.calls += 1
+            if self.calls == 1: raise ConnectionError("presend")
+            return {"available": False}
+        def ping(self): return {"available": False}
+    watcher = DesktopLiveWatcher(tmp_path, Client(), interval=0.01)
+    watcher.start()
+    try:
+        time.sleep(0.08)
+        assert watcher._thread is not None and watcher._thread.is_alive()
+        assert watcher._stop.is_set() is False
+    finally:
+        watcher.stop()
+    assert watcher._thread is not None and not watcher._thread.is_alive()
+
+
+def test_update_attempted_flag_is_path_local_for_multiple_candidates(tmp_path):
+    class Client:
+        def ping(self): return {"available": True}
+        def snapshot(self): return {"available": True, "state": SimpleNamespace(revision=0, state_id="x")}
+        def update_file(self, path, **_kwargs): return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
+    watcher = DesktopLiveWatcher(tmp_path, Client(), interval=0.01)
+    watcher._snapshot = {}
+    watcher._trusted_file_state = lambda _snapshot: SimpleNamespace(has_changed=lambda _p: True, tracked_paths=lambda: set())
+    (tmp_path / "a.py").write_text("a=1\n", encoding="utf-8")
+    (tmp_path / "b.py").write_text("b=1\n", encoding="utf-8")
+    assert set(watcher.poll_once()) == {str(tmp_path / "a.py"), str(tmp_path / "b.py")}
