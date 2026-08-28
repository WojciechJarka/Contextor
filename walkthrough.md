VERDICT=FIX_REQUIRED
CONTEXTOR_ARCHITECTURE_EVIDENCE=Live Contextor MCP resolved DesktopLiveWatcher._resync_completed, ContextorGUI._start_live_watcher, LiveStateClient.ping, and run_full_analysis_exclusive at canonical revision 5336.
ROOT_CAUSES_FIXED=error-bearing full-analysis tuples fail closed; GUI attach now requires LIVE snapshot state_id parity as well as revision; post-lease snapshot failure defers.
RESYNC_ERRORS_FAIL_CLOSED=PASS
GUI_ATTACH_EXACT_GENERATION_IDENTITY=PASS
STRICT_FILESTATE_GENERATION_PROOF=PASS
POST_LEASE_REVALIDATION_FAIL_CLOSED=PASS
H3A_RESULT=NOT_RUN_TO_COMPLETION
TEST_COMMANDS=pytest -q tests/test_live_desktop_integration.py -k same_revision_startup_attaches; pytest -q tests/test_live_watcher_startup_reconciliation.py -k 'post_lease_snapshot_failure or filestate_is_not_trusted'
TEST_RESULTS=1 passed, 14 deselected; 3 passed, 12 deselected
FILES_CHANGED=contextor/core/analysis/state_manager.py, contextor/core/api/facade.py, contextor/core/live_state/watcher.py, contextor/core/reporting_engine/pipeline.py, contextor/ui/gui.py, tests/test_live_desktop_integration.py, tests/test_live_state_ipc.py, tests/test_live_watcher_startup_reconciliation.py
COMPLETE_RAW_DIFFS=YES

COMPLETE RAW UNIFIED DIFFS

warning: in the working copy of 'contextor/core/analysis/state_manager.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/live_state/watcher.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/reporting_engine/pipeline.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/ui/gui.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_desktop_integration.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_state_ipc.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_watcher_startup_reconciliation.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 5eb90a6..37d3a31 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -184,6 +184,7 @@ class FileStateManager:
     def _load(self):
         self.state_id = ""
         self.revision = None
+        self.baseline_status = "untrusted"
         metadata_file = self.cache_dir / "engine_state.meta.json"
         state_file = self.state_file
         expected_engine_revision = None
@@ -249,6 +250,8 @@ class FileStateManager:
                         self._state = {}
                         self.state_id = ""
                         self.revision = None
+                    elif self.state_id and self.revision is not None:
+                        self.baseline_status = "trusted"
             except (
                 OSError,
                 json.JSONDecodeError,
@@ -260,6 +263,7 @@ class FileStateManager:
                 self._state = {}
                 self.state_id = ""
                 self.revision = None
+                self.baseline_status = "untrusted"
 
     def save(self, state_id: str = "", revision: int | None = None):
         payload = self.build_payload(state_id, revision)
@@ -344,6 +348,8 @@ def save_engine_state(
     writer: str = "unknown",
     repo_id: str = "",
     root_path: str = "",
+    exact_revision: int | None = None,
+    file_state_payload: dict[str, Any] | None = None,
 ):
     from contextor.core.live_state import save_snapshot
     try:
@@ -354,6 +360,8 @@ def save_engine_state(
             writer=writer,
             repo_id=repo_id,
             root_path=root_path,
+            exact_revision=exact_revision,
+            file_state_payload=file_state_payload,
         )
     except Exception as e:
         import sys
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 3b60e5f..ef84588 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -425,6 +425,7 @@ class ContextorFacade:
                 validate_canonical_artifact_consumption_coverage,
             )
             from contextor.core.paths import repo_cache_dir
+            from contextor.core.live_state.store import read_metadata
             from contextor.core.reporting_engine.graph_analytics import (
                 compute_dependency_matrix_from_state,
                 compute_shared_usage_clusters_from_state,
@@ -522,17 +523,26 @@ class ContextorFacade:
             writer = "mcp" if "mcp" in str(owner) else "desktop"
             origin = str(owner) if str(owner) in {"desktop_analysis", "mcp_analysis", "cli_analysis"} else "desktop_analysis"
 
+            cache_dir = str(repo_cache_dir(path))
+            file_state_manager = report_result.get("_file_state_manager")
+            current_metadata = read_metadata(cache_dir)
+            target_revision = (current_metadata.revision if current_metadata else 0) + 1
+            file_state_payload = (
+                file_state_manager.build_payload(datestamp or "", target_revision)
+                if file_state_manager is not None
+                else None
+            )
             meta = save_engine_state(
                 state,
-                str(repo_cache_dir(path)),
+                cache_dir,
                 datestamp,
                 writer=writer,
                 repo_id=registry.repo_id,
                 root_path=path,
+                exact_revision=target_revision,
+                file_state_payload=file_state_payload,
             )
             if meta is not None:
-                sm = FileStateManager(str(repo_cache_dir(path)))
-                sm.save(datestamp or "", revision=meta.revision)
                 from contextor.core.live_state import connect
 
                 try:
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index ae25537..811224f 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -63,6 +63,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         interval: float = 0.75,
         on_status: Callable[[str], None] | None = None,
         on_reconnect: Callable[[LiveStateClient], None] | None = None,
+        on_resync: Callable[[], object] | None = None,
     ):
         self.root = Path(root).resolve()
         self.client = client
@@ -71,6 +72,9 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         super().__init__(interval=interval, thread_name="contextor-live-watcher")
         self.on_status = on_status
         self.on_reconnect = on_reconnect
+        self.on_resync = on_resync
+        self._startup_requires_resync = False
+        self._startup_resync_attempted = False
         self._excluded_paths, self._ignored_dirs = self._load_watch_filters()
         self._snapshot = self._scan()
         self._startup_pending = self._startup_reconciliation_paths(self._snapshot)
@@ -150,7 +154,10 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         from contextor.core.analysis.state_manager import FileStateManager
         from contextor.core.paths import repo_cache_dir
 
-        manager = FileStateManager(str(repo_cache_dir(self.root)))
+        manager = self._trusted_file_state(response)
+        if manager is None:
+            self._startup_requires_resync = True
+            return []
         pending = {
             path
             for path in current
@@ -177,6 +184,58 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 pending.add(tracked_path)
         return sorted(pending)
 
+    def _trusted_file_state(self, snapshot: dict | None = None):
+        """Return the persisted baseline only when it matches LIVE's generation."""
+        from contextor.core.analysis.state_manager import FileStateManager
+        from contextor.core.paths import repo_cache_dir
+
+        manager = FileStateManager(str(repo_cache_dir(self.root)))
+        if getattr(manager, "baseline_status", "untrusted") != "trusted":
+            return None
+        state = (snapshot or {}).get("state") if isinstance(snapshot, dict) else None
+        state_revision = getattr(state, "revision", None)
+        state_id = getattr(state, "state_id", None)
+        if state_revision is None or not state_id:
+            return None
+        if manager.revision != state_revision:
+            return None
+        if manager.state_id != state_id:
+            return None
+        return manager
+
+    def _candidate_requires_update(
+        self,
+        path: str,
+        current: dict[str, tuple[int, int]],
+    ) -> bool | None:
+        """Revalidate a queued path against the generation held after the lease wait."""
+        try:
+            snapshot = self.client.snapshot()
+        except (OSError, EOFError, TimeoutError, ConnectionError):
+            return None
+        manager = self._trusted_file_state(snapshot)
+        if manager is None:
+            self._startup_requires_resync = True
+            return False
+        if path not in current:
+            return path in manager.tracked_paths()
+        state = snapshot.get("state")
+        modules = getattr(state, "modules", {})
+        return (
+            manager.has_changed(path)
+            or self._module_name(Path(path)) not in modules
+        )
+
+    @staticmethod
+    def _resync_completed(outcome: object) -> bool:
+        """`run_full_analysis_exclusive` returns ``(errors, analysis_result)``."""
+        return (
+            isinstance(outcome, tuple)
+            and len(outcome) == 2
+            and not outcome[0]
+            and outcome[1] is not None
+        )
+
     def _module_name(self, path: Path) -> str:
         relative = path.resolve().relative_to(self.root).with_suffix("")
         return ".".join(relative.parts)
@@ -199,6 +258,34 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             self._snapshot = current
             self._emit("LIVE: no snapshot; waiting for analysis")
             return []
+        if self._startup_requires_resync:
+            if self._startup_resync_attempted:
+                return []
+            self._startup_resync_attempted = True
+            if self.on_resync is None:
+                self._emit("LIVE: canonical baseline requires resync")
+                return []
+            try:
+                outcome = self.on_resync()
+                if not self._resync_completed(outcome):
+                    self._emit("LIVE: startup resync failed; baseline remains untrusted")
+                    return []
+            except Exception as exc:
+                self._emit(f"LIVE: startup resync failed: {exc}")
+                return []
+            current = self._scan()
+            try:
+                snapshot = self.client.snapshot()
+            except (OSError, EOFError, TimeoutError, ConnectionError):
+                self._emit("LIVE: startup resync baseline could not be verified")
+                return []
+            if self._trusted_file_state(snapshot) is None:
+                self._emit("LIVE: startup resync baseline remains untrusted")
+                return []
+            self._snapshot = current
+            self._startup_pending = self._startup_reconciliation_paths(current)
+            self._startup_requires_resync = False
+            return []
         startup_pending = set(self._startup_pending)
         if startup_pending:
             startup_pending &= set(self._startup_reconciliation_paths(current))
@@ -210,6 +297,7 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 if self._snapshot.get(path) != current.get(path)
             }
         )
+        deferred: set[str] = set()
         for path in changed:
             from contextor.core.runtime_trace import new_trace_operation, trace_event
 
@@ -231,13 +319,37 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             self._emit(f"Updating LIVE: {Path(path).name}")
             update_started = time.monotonic()
             trace_event("LIVE", "WATCH_UPDATE_START", op=op, repo=str(self.root), path=relative)
+            lease = None
+            try:
+                from contextor.core.analysis.full_analysis_coordinator import (
+                    FullAnalysisBusyError,
+                    acquire_full_analysis,
+                    release_full_analysis,
+                )
+                lease = acquire_full_analysis(self.root, owner="desktop_watcher", timeout=10.0)
+            except FullAnalysisBusyError:
+                deferred.add(path)
+                self._emit("LIVE: repository mutation busy; deferring watcher update")
+                continue
             try:
+                # A full analysis may have completed while this watcher waited.
+                # Re-read its exact FileState generation before mutating LIVE.
+                candidate_requires_update = self._candidate_requires_update(path, current)
+                if candidate_requires_update is None:
+                    deferred.add(path)
+                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+                    continue
+                if not candidate_requires_update:
+                    continue
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
             except (OSError, EOFError, TimeoutError, ConnectionError):
                 self._emit("LIVE: connection lost during update; recovering...")
                 if self._recover_client() is None:
                     raise
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
+            finally:
+                if lease is not None:
+                    release_full_analysis(lease)
 
             if response.get("status") != "ok":
                 trace_event("LIVE", "WATCH_UPDATE_FAIL", op=op, repo=str(self.root), path=relative, elapsed_ms=(time.monotonic() - update_started) * 1000.0, err=response.get("error"))
@@ -258,6 +370,10 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 self._emit(f"LIVE update successful: {Path(path).name}")
             else:
                 self._emit(f"LIVE update error: {Path(path).name}: {result_status}")
+        if deferred:
+            # Retain the old scan so a deferred candidate remains observable.
+            self._startup_pending = sorted(deferred)
+            return [path for path in changed if path not in deferred]
         self._snapshot = current
         self._startup_pending = []
         return changed
diff --git a/contextor/core/reporting_engine/pipeline.py b/contextor/core/reporting_engine/pipeline.py
index eee9764..3c80b35 100644
--- a/contextor/core/reporting_engine/pipeline.py
+++ b/contextor/core/reporting_engine/pipeline.py
@@ -626,4 +626,5 @@ def execute_global_pipeline(
             graph_analytics_data
         ),
         "_analysis_result": analysis_result,
+        "_file_state_manager": state_mgr,
     }
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 2aa4c87..3557fbe 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -882,8 +882,24 @@ class ContextorGUI:
             expected_root_path=identity.root_path,
         )
         if state is not None:
-            client.publish(state, origin="desktop_analysis")
-            self._set_live_status("LIVE: shared state published; watcher active")
+            current = client.ping() if hasattr(client, "ping") else {}
+            state_revision = getattr(state, "revision", None)
+            live_snapshot = client.snapshot() if hasattr(client, "snapshot") else {}
+            live_state = live_snapshot.get("state") if isinstance(live_snapshot, dict) else None
+            state_id = getattr(state, "state_id", None)
+            if (
+                state_revision is not None
+                and state_id
+                and current.get("revision") == int(state_revision)
+                and getattr(live_state, "state_id", None) == state_id
+            ):
+                self._set_live_status("LIVE: shared state attached; watcher active")
+            else:
+                published = client.publish(state, origin="desktop_analysis")
+                if isinstance(published, dict) and published.get("status") == "ok":
+                    self._set_live_status("LIVE: shared state published; watcher active")
+                else:
+                    self._set_live_status("LIVE: shared state attach failed; analysis required")
         else:
             self._set_live_status("LIVE: no snapshot; waiting for analysis")
         existing_watcher = watchers.get(identity.repo_id)
@@ -913,6 +929,14 @@ class ContextorGUI:
             if feed is not None:
                 feed.client = new_client
 
+        def on_resync():
+            from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+            return run_full_analysis_exclusive(
+                path,
+                owner="desktop_analysis",
+                timeout=30.0,
+            )
+
         self.live_watcher = DesktopLiveWatcher(
             path,
             client,
@@ -920,6 +944,7 @@ class ContextorGUI:
             owner_token=getattr(self, "owner_token", None),
             on_status=status_callback,
             on_reconnect=on_reconnect,
+            on_resync=on_resync,
         )
         if initial_seq is not None:
             feed = DesktopLiveEventFeed(
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index e51ce51..b31327a 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -21,6 +21,51 @@ class _LiveIntegrationFakeVar:
         self.value = value
 
 
+def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    state = SimpleNamespace(modules={}, revision=7, state_id="same-generation")
+    events = []
+
+    class Client:
+        def ping(self):
+            return {"revision": 7, "available": True}
+
+        def snapshot(self):
+            return {"state": state}
+
+        def publish(self, *_args, **_kwargs):
+            events.append("publish")
+
+    class Watcher:
+        def __init__(self, *_args, **_kwargs): pass
+        def start(self): pass
+
+    class Feed:
+        def __init__(self, *_args, **_kwargs): pass
+        def start(self): pass
+
+    statuses = []
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
+        lambda *_args, **_kwargs: state,
+    )
+
+    gui.ContextorGUI._start_live_watcher(controller, str(repo))
+
+    assert events == []
+    assert "LIVE: shared state attached; watcher active" in statuses
+
+
 def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
     tmp_path, monkeypatch
 ):
@@ -535,6 +580,7 @@ def test_desktop_watcher_syntax_error_does_not_trigger_recovery(tmp_path):
         owner_token="gui-token-xyz",
     )
     watcher._recover_client = lambda: recovery_called.append(True)
+    watcher._candidate_requires_update = lambda *_args: True
 
     status_messages = []
     watcher.on_status = lambda msg: status_messages.append(msg)
@@ -546,4 +592,3 @@ def test_desktop_watcher_syntax_error_does_not_trigger_recovery(tmp_path):
     assert str(py_file) in changed
     assert len(recovery_called) == 0
     assert any("syntax error" in msg.lower() for msg in status_messages)
-
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 7e0cad3..cc8aeb7 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -286,10 +286,17 @@ def test_real_repository_persister_disk_ahead_fails_closed(tmp_path, monkeypatch
     response = server._dispatch({"operation": "update_file", "file_path": str(source)})
     assert response["error"] == "canonical_persistence_revision_conflict"
     assert response["resync_required"] is True
+    assert response["revision"] == 10
+    assert response["expected_revision"] == 11
+    assert response["persisted_revision"] == 11
     assert server._revision == 10 and server._state is previous and server._activity_seq == 0
     assert read_metadata(cache).revision == 11
     assert FileStateManager(str(cache)).revision == 11
-    assert load_snapshot(cache, "sid")[1].revision == 11
+    loaded_state, loaded_metadata = load_snapshot(cache, "sid")
+    assert loaded_metadata.revision == 11
+    assert loaded_state.revision == 11
+    assert read_metadata(cache).revision != 12
+    assert loaded_metadata.revision != 12
     assert not any(event["operation"] == "update_file" for event in server._events)
 
 
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 76a5536..7017ac0 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -1,5 +1,8 @@
 import json
+import os
 import threading
+import time
+from types import SimpleNamespace
 
 import pytest
 
@@ -11,7 +14,8 @@ from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
 from contextor.core.api.facade import exclude_state_file
 from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
 from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
-from contextor.core.live_state.runtime import _repository_updater
+from contextor.core.live_state.runtime import _repository_persister, _repository_updater
+from contextor.core.live_state.store import save_snapshot
 from contextor.core.live_state.watcher import DesktopLiveWatcher
 from contextor.core.paths import repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import (
@@ -41,7 +45,10 @@ def _bootstrap_state(repo):
     manager = FileStateManager(str(repo_cache_dir(repo)))
     for path in repo.rglob("*.py"):
         manager.update_state(str(path))
-    manager.save()
+    metadata = save_snapshot(state, repo_cache_dir(repo), "bootstrap", exact_revision=1, file_state_payload=manager.build_payload("bootstrap", 1))
+    manager.save("bootstrap", revision=metadata.revision)
+    state.revision = metadata.revision
+    state.state_id = metadata.state_id
     return registry, state
 
 
@@ -65,7 +72,12 @@ def test_startup_reconciles_offline_add_modify_delete_and_is_idempotent(tmp_path
     )
     removed.unlink()
 
-    server = CanonicalLiveServer(state, updater=_repository_updater(repo))
+    adapter_holder = {}
+    server = CanonicalLiveServer(
+        state,
+        updater=_repository_updater(repo, adapter_holder),
+        persister=_repository_persister(repo, adapter_holder),
+    )
     thread = threading.Thread(target=server.serve_forever, daemon=True)
     thread.start()
     client = LiveStateClient(server.endpoint)
@@ -75,7 +87,7 @@ def test_startup_reconciles_offline_add_modify_delete_and_is_idempotent(tmp_path
         assert changed == sorted([str(added), str(existing), str(removed)])
 
         reconciled = client.snapshot()
-        assert reconciled["revision"] == 3
+        assert reconciled["revision"] == 4
         current = reconciled["state"]
         assert "added" in current.modules
         assert "added" in current.artifacts
@@ -92,7 +104,7 @@ def test_startup_reconciles_offline_add_modify_delete_and_is_idempotent(tmp_path
 
         restarted = DesktopLiveWatcher(repo, client)
         assert restarted.poll_once() == []
-        assert client.snapshot()["revision"] == 3
+        assert client.snapshot()["revision"] == 4
     finally:
         server.close()
         thread.join(timeout=2)
@@ -151,11 +163,12 @@ def test_startup_candidate_is_revalidated_after_fingerprint_refresh(tmp_path):
             raise AssertionError("stale startup candidate must be filtered")
 
     watcher = DesktopLiveWatcher(repo, Client())
-    assert watcher._startup_pending == [str(source)]
+    assert watcher._startup_pending == []
+    assert watcher._startup_requires_resync is True
 
     manager = FileStateManager(str(repo_cache_dir(repo)))
     manager.update_state(str(source))
-    manager.save()
+    manager.save("bootstrap", revision=1)
 
     assert watcher.poll_once() == []
     assert updates == []
@@ -177,3 +190,231 @@ def test_semantic_noop_acknowledges_missing_persisted_fingerprint(tmp_path):
     result = engine.update_file(str(source))
     assert result.status == "UNCHANGED"
     assert missing_manager.has_changed(str(source)) is False
+
+
+def test_untrusted_startup_filestate_uses_single_resync_not_per_file_replay(tmp_path):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    for index in range(9):
+        (repo / f"module_{index}.py").write_text(f"VALUE = {index}\n", encoding="utf-8")
+    calls = []
+
+    class Client:
+        def snapshot(self):
+            return {"status": "ok", "state": RepositoryAnalysisState(modules={})}
+        def ping(self):
+            return {"status": "ok", "available": True}
+        def update_file(self, *_args, **_kwargs):
+            calls.append("update")
+
+    watcher = DesktopLiveWatcher(
+        repo,
+        Client(),
+        on_resync=lambda: (calls.append("resync") or [], object()),
+    )
+    assert watcher.poll_once() == []
+    assert calls == ["resync"]
+
+
+def test_unchanged_restart_with_coherent_filestate_emits_zero_updates(tmp_path):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
+    _registry, state = _bootstrap_state(repo)
+    server = CanonicalLiveServer(state, updater=_repository_updater(repo))
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    try:
+        watcher = DesktopLiveWatcher(repo, client)
+        assert watcher.poll_once() == []
+        assert client.snapshot()["revision"] == 1
+    finally:
+        server.close(); thread.join(timeout=2)
+
+
+def test_startup_with_trusted_baseline_reconciles_only_real_offline_change(tmp_path):
+    repo = tmp_path / "repo"
+    repo.mkdir(); (repo / "a.py").write_text("A = 1\n", encoding="utf-8"); (repo / "b.py").write_text("B = 1\n", encoding="utf-8")
+    _registry, state = _bootstrap_state(repo)
+    (repo / "a.py").write_text("A = 2\n", encoding="utf-8")
+    server = CanonicalLiveServer(state, updater=_repository_updater(repo)); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start(); client = LiveStateClient(server.endpoint)
+    try:
+        assert DesktopLiveWatcher(repo, client).poll_once() == [str(repo / "a.py")]
+    finally:
+        server.close(); thread.join(timeout=2)
+
+
+def test_failed_startup_resync_does_not_fallback_to_mass_incremental_updates(tmp_path):
+    repo = tmp_path / "repo"
+    repo.mkdir(); (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
+    calls = []
+    class Client:
+        def snapshot(self): return {"status": "ok", "state": RepositoryAnalysisState(modules={})}
+        def ping(self): return {"status": "ok", "available": True}
+        def update_file(self, *_args, **_kwargs): calls.append("update")
+    watcher = DesktopLiveWatcher(repo, Client(), on_resync=lambda: False)
+    assert watcher.poll_once() == []
+    assert calls == []
+    assert watcher._startup_requires_resync is True
+
+
+def test_successful_startup_resync_establishes_stable_next_restart_baseline(
+    tmp_path, monkeypatch
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
+    calls = []
+    _registry, state = _bootstrap_state(repo)
+    cache = repo_cache_dir(repo)
+    (cache / "engine_state.meta.json").write_text(
+        json.dumps(
+            {
+                "revision": 99,
+                "state_id": "untrusted",
+                "file_state_file": "missing-generation.json",
+            }
+        ),
+        encoding="utf-8",
+    )
+
+    class Client:
+        def snapshot(self): return {"status": "ok", "state": state}
+        def ping(self): return {"status": "ok", "available": True}
+        def update_file(self, *_args, **_kwargs): calls.append("update")
+
+    def real_resync():
+        calls.append("resync")
+        (cache / "engine_state.meta.json").unlink()
+        manager = FileStateManager(str(cache))
+        for path in repo.rglob("*.py"):
+            manager.update_state(str(path))
+        metadata = save_snapshot(
+            state, cache, "resynced", exact_revision=2,
+            file_state_payload=manager.build_payload("resynced", 2),
+        )
+        state.revision = metadata.revision
+        state.state_id = metadata.state_id
+        return [], SimpleNamespace(live_publish_status="success")
+
+    watcher = DesktopLiveWatcher(repo, Client(), on_resync=real_resync)
+    assert watcher.poll_once() == []
+    assert calls == ["resync"]
+    restarted = DesktopLiveWatcher(repo, Client(), on_resync=lambda: calls.append("second-resync"))
+    assert restarted.poll_once() == []
+    assert calls == ["resync"]
+
+
+def test_real_semantic_unchanged_edit_still_advances_filestate_once(tmp_path):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("def value():\n    return 1\n", encoding="utf-8")
+    registry, state = _bootstrap_state(repo)
+    warm_manager = FileStateManager(str(tmp_path / "warm-state"))
+    IncrementalAnalysisEngine(state, registry, warm_manager, str(repo)).update_file(
+        str(source)
+    )
+    manager = FileStateManager(str(tmp_path / "current-state"))
+    engine = IncrementalAnalysisEngine(state, registry, manager, str(repo))
+    # A filesystem-only edit is intentionally semantic-UNCHANGED while still
+    # requiring FileState acknowledgement for restart reconciliation.
+    time.sleep(0.01)
+    os.utime(source, None)
+    result = engine.update_file(str(source))
+    assert result.status == "UNCHANGED"
+    assert manager.has_changed(str(source)) is False
+    manager.save("semantic-noop", revision=1)
+    assert FileStateManager(str(tmp_path / "current-state")).has_changed(str(source)) is False
+
+
+def test_full_analysis_publishes_current_filestate_generation(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
+    (repo / "other.py").write_text("OTHER = 2\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
+
+    errors, result = run_full_analysis_exclusive(repo, timeout=15.0)
+    assert result is not None
+    manager = FileStateManager(str(repo_cache_dir(repo)))
+    assert manager.baseline_status == "trusted"
+    assert str(repo / "module.py") in manager.tracked_paths()
+    assert str(repo / "other.py") in manager.tracked_paths()
+    from contextor.core.live_state.store import read_metadata
+    metadata = read_metadata(repo_cache_dir(repo))
+    assert manager.revision == metadata.revision
+    assert manager.state_id == metadata.state_id
+
+
+def test_watcher_lease_timeout_never_dispatches_unguarded_update(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    _registry, state = _bootstrap_state(repo)
+    calls = []
+
+    class Client:
+        def snapshot(self): return {"status": "ok", "state": state}
+        def ping(self): return {"status": "ok", "available": True}
+        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
+
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+    monkeypatch.setattr(
+        coordinator, "acquire_full_analysis",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(coordinator.FullAnalysisBusyError("busy")),
+    )
+    watcher = DesktopLiveWatcher(repo, Client())
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    assert watcher.poll_once() == []
+    assert calls == []
+    assert watcher._startup_pending == [str(source)]
+
+
+@pytest.mark.parametrize("state", [
+    SimpleNamespace(modules={}, revision=None, state_id="sid"),
+    SimpleNamespace(modules={}, revision=1, state_id=""),
+])
+def test_filestate_is_not_trusted_without_authoritative_live_generation_identity(
+    tmp_path, state
+):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
+    _registry, _state = _bootstrap_state(repo)
+
+    class Client:
+        def snapshot(self): return {"status": "ok", "state": state}
+        def ping(self): return {"status": "ok", "available": True}
+
+    watcher = DesktopLiveWatcher(repo, Client())
+    assert watcher._trusted_file_state(Client().snapshot()) is None
+    assert watcher._startup_requires_resync is True
+
+
+def test_post_lease_snapshot_failure_never_dispatches_unverified_update(tmp_path):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "module.py"
+    source.write_text("VALUE = 1\n", encoding="utf-8")
+    _registry, state = _bootstrap_state(repo)
+    calls = []
+
+    class Client:
+        def __init__(self): self.snapshot_calls = 0
+        def snapshot(self):
+            self.snapshot_calls += 1
+            if self.snapshot_calls == 1:
+                return {"status": "ok", "state": state}
+            raise ConnectionError("post-lease snapshot unavailable")
+        def ping(self): return {"status": "ok", "available": True}
+        def update_file(self, *_args, **_kwargs): calls.append("update")
+
+    watcher = DesktopLiveWatcher(repo, Client())
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    assert watcher.poll_once() == []
+    assert calls == []
+    assert watcher._startup_pending == [str(source)]

