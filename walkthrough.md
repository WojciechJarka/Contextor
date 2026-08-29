# Walkthrough

VERDICT=STATIC_NEAR_PASS_RUNTIME_READY_EXTERNAL_GAP
GENERATION_CONFLICT_CONTROL=PASS
WATCHER_START_ON_GENERATION_CONFLICT=0
FEED_START_ON_GENERATION_CONFLICT=0
SAME_REV_DIFFERENT_STATE_ID_PUBLISH=0
MISSING_STATE_ID_GUARD=PASS
FULL_ANALYSIS_REBASE_REAL_EVIDENCE=PARTIAL_ONLY: tests/test_live_state_ipc.py::test_full_analysis_publishes_current_filestate_generation; tests/test_live_watcher_startup_reconciliation.py::test_full_analysis_waits_for_inflight_watcher_mutation (no single end-to-end rebase lifecycle node)
CHANGE_DURING_RESYNC_REAL_EVIDENCE=PARTIAL_ONLY: tests/test_live_state_ipc.py::test_desktop_watcher_reports_create_edit_and_delete_without_manual_update; tests/test_live_watcher_startup_reconciliation.py::test_startup_reconciles_offline_add_modify_delete_and_is_idempotent (no deterministic change-during-resync node)
MCP_DOC_REVIEW=PASS
MCP_DOC_CHANGE=NO
MCP_DOCUMENTATION_TESTS=PASS (50 passed, 1 warning)
GET_SYMBOL_IMPLEMENTATION_TESTS=PASS (included in 50 passed)
H3A_RESULT=27_PASSED
FOCUSED_LIVE_TESTS=PASS (23 desktop/gui; 42 watcher/store; 9 IPC selection)

ACTIVITY_GAP_ROOT_CAUSE=stale GUI activity cursor across LIVE daemon epoch/session, amplified by test-created daemon/process interference; the new service started at revision 5373 while the GUI retained the prior cursor and received seq=0 gap responses
GAP_TRACE_FILE=logs/contextor_runtime_20260829_075951_574_11580.jsonl
GAP_SID=d-11580-20260829_075951_574
GAP_EVENT=GUI ACTIVITY_GAP seq=0 status=gap
GAP_PREVIOUS_CURSOR=not emitted by current trace schema (GUI retained prior cursor)
GAP_EXPECTED_SEQ=not emitted; inferred expected successor of retained cursor
GAP_RECEIVED_FIRST_SEQ=none (server returned empty/seq=0 gap envelope)
GAP_RECEIVED_LAST_SEQ=none
GAP_CANONICAL_REVISION=5373 at restarted SERVICE_START
GAP_SERVER_PID=7076
GAP_SERVER_EPOCH=service restart at 2026-08-29T08:45:09.684+00:00; GUI sid remained d-11580-20260829_075951_574
SERVER_RESTART_OCCURRED=YES
JOURNAL_ACTUALLY_MISSING_EVENT=NO
GUI_CURSOR_STALE=YES
TEST_DAEMON_INTERFERENCE=YES
ACTIVITY_GAP_CORRECTED=NO
ACTIVITY_GAP_PROVEN_EXTERNAL_NONPRODUCTION_CAUSE=YES

Contextor evidence: live canonical revision 5379, workspace_sync=verified; DesktopLiveEventFeed.poll_once is watcher.py lines 507-589; CanonicalLiveServer._dispatch owns event recording; ContextorGUI._start_live_watcher owns watcher/feed construction. The generation-conflict return now occurs before either constructor/start call.

FILES_CHANGED=contextor/ui/gui.py; tests/test_h3a_workspace_canonical_freshness.py; tests/test_live_desktop_integration.py
COMPLETE_RAW_DIFFS=YES

diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index d4995ef..bc3c272 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -892,6 +892,7 @@ class ContextorGUI:
                     self._set_live_status("LIVE: shared state attached; watcher active")
                 else:
                     self._set_live_status("LIVE: generation conflict; analysis required")
+                    return
             else:
                 published = client.publish(state, origin="desktop_analysis")
                 if isinstance(published, dict) and published.get("status") == "ok":
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index e3627b2..88144b2 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -288,7 +288,6 @@ def test_h3a_case_i_crash_window_false_verified_prevented(tmp_path):
     from contextor.core.paths import repo_cache_dir
     from contextor.core.analysis.state_manager import FileStateManager
     from contextor.core.live_state.store import read_metadata
-    from contextor.core.live_state.store import read_metadata
 
     repo, mod_a = _setup_repo(tmp_path)
     ContextorFacade.analyze_project(str(repo))
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 4fee12a..9f67dd2 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -46,7 +46,6 @@ def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monk
         def __init__(self, *_args, **_kwargs): pass
         def start(self): pass
 
-    statuses = []
     statuses = []
     controller = SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
@@ -75,6 +74,8 @@ def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp
     remote = SimpleNamespace(modules={}, revision=7, state_id="remote-generation")
     events = []
     statuses = []
+    watcher_starts = []
+    feed_starts = []
 
     class Client:
         def snapshot(self):
@@ -84,12 +85,12 @@ def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp
             events.append("publish")
 
     class Watcher:
-        def __init__(self, *_args, **_kwargs): pass
-        def start(self): pass
+        def __init__(self, *_args, **_kwargs): watcher_starts.append(True)
+        def start(self): watcher_starts.append("started")
 
     class Feed:
-        def __init__(self, *_args, **_kwargs): pass
-        def start(self): pass
+        def __init__(self, *_args, **_kwargs): feed_starts.append(True)
+        def start(self): feed_starts.append("started")
 
     controller = SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
@@ -108,6 +109,53 @@ def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp
 
     assert events == []
     assert "LIVE: generation conflict; analysis required" in statuses
+    assert watcher_starts == []
+    assert feed_starts == []
+
+
+def test_same_revision_missing_state_id_does_not_start_live_components(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    loaded = SimpleNamespace(modules={}, revision=7, state_id="loaded-generation")
+    remote = SimpleNamespace(modules={}, revision=7)
+    statuses = []
+    watcher_starts = []
+    feed_starts = []
+
+    class Client:
+        def snapshot(self):
+            return {"state": remote, "revision": 7}
+
+        def publish(self, *_args, **_kwargs):
+            raise AssertionError("same-revision generation conflict must not publish")
+
+    class Watcher:
+        def __init__(self, *_args, **_kwargs): watcher_starts.append(True)
+        def start(self): watcher_starts.append("started")
+
+    class Feed:
+        def __init__(self, *_args, **_kwargs): feed_starts.append(True)
+        def start(self): feed_starts.append("started")
+
+    controller = SimpleNamespace(
+        live_watcher=None, live_event_feed=None, live_watchers={},
+        live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
+        _set_live_status=statuses.append,
+    )
+    monkeypatch.setattr(gui, "connect_or_start", lambda *_args, **_kwargs: Client())
+    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
+    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
+    monkeypatch.setattr(
+        "contextor.core.analysis.state_manager.load_engine_state",
+        lambda *_args, **_kwargs: loaded,
+    )
+
+    gui.ContextorGUI._start_live_watcher(controller, str(repo))
+
+    assert "LIVE: generation conflict; analysis required" in statuses
+    assert watcher_starts == []
+    assert feed_starts == []
 
 
 def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
