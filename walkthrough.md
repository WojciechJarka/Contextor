# Walkthrough

VERDICT=IMPLEMENTATION_PASS
CONTEXTOR_ARCHITECTURAL_EVIDENCE=DesktopLiveWatcher.poll_once (A482/1) owns candidate revalidation and update dispatch; ContextorGUI._start_live_watcher (A1129/1) owns startup attach decisions; FileStateManager._load (A1094/1) reads the metadata-referenced generation; load_snapshot (A591/1) owns snapshot hydration.
CANONICAL_REVISION_AT_DISCOVERY=5359

PARTIAL_SNAPSHOT_ACKNOWLEDGEMENT=PASS
RECONCILED_SIBLING_REPLAY=0
MISSING_RESULT_DEFAULTS_TO_UPDATED=NO
MALFORMED_RESPONSE_ACKNOWLEDGED=NO
SYNTAX_ERROR_WATCHER_SEMANTICS=terminally acknowledged filesystem observation; no unchanged-file retry loop
SYNTAX_ERROR_RETRY_LOOP=NO
SAME_REV_DIFFERENT_STATE_ID_PUBLISH=0
GENERATION_CONFLICT_FAILS_CLOSED=PASS
REFERENCED_GENERATION_FAIL_CLOSED_PRESERVED=YES
LEGACY_FILESTATE_FALLBACK_REINTRODUCED=NO
LEGACY_FILESTATE_METADATA_FABRICATION=NO
H3A_I=PASS
H3A_K=PASS
H3A_L=PASS
H3A_M=PASS
H3A_N=PASS
H3A_O=PASS
H3A_RESULT=27_PASSED
RECOVERY_REVALIDATION_NONE_DEFERRED=PASS
RECOVERY_REVALIDATION_FALSE_SKIPPED=PASS
RECOVERY_REVALIDATION_TRUE_RETRIED_ONCE=PASS
RECOVERY_GENERATION_PROOF_SINGLE_OWNER=YES
TEST_CREATED_SERVICE_PROCESS_LEAK=REMOVED (PIDs 5148,9708 from final H3A run)
MCP_DOC_CHANGE=NO
MCP_DOC_CONTRACT_TESTS=PASS
MASS_STARTUP_REPLAY_REMOVED=YES
EXACT_SUCCESSOR_VALIDATION_WEAKENED=NO
FULL_ANALYSIS_HARD_RESET_CHANGED=NO

H3A_BEFORE_AFTER
- Before: I,K,L,M,N,O,S failed.
- After: I/L/M/N tamper metadata-referenced generation; K/O use production updater+persister adapters; S detects malformed referenced generation; 27 passed.

FINAL_TEST_COMMANDS
- .venv\\Scripts\\python.exe -m pytest -q tests/test_live_watcher_startup_reconciliation.py => 24 passed
- .venv\\Scripts\\python.exe -m pytest -q tests/test_live_state_store.py => 18 passed
- .venv\\Scripts\\python.exe -m pytest -q tests/test_live_state_ipc.py -k "persister or persistence_conflict or real_repository_adapter or startup_backfill or trace_operation or trace_failure" => 9 passed, 36 deselected
- .venv\\Scripts\\python.exe -m pytest -q tests/test_live_desktop_integration.py tests/test_gui_live_startup.py => 22 passed
- .venv\\Scripts\\python.exe -m pytest -q tests/mcp/tools/test_get_symbol_implementation.py => 42 passed, 1 warning
- CONTEXTOR_CACHE_DIR=.tmp_h3a_final_pass .venv\\Scripts\\python.exe -m pytest -q tests/test_h3a_workspace_canonical_freshness.py => 27 passed

FILES_CHANGED=contextor/core/live_state/watcher.py; contextor/mcp/query_helpers.py; contextor/ui/gui.py; tests/test_h3a_workspace_canonical_freshness.py; tests/test_live_desktop_integration.py; tests/test_live_watcher_startup_reconciliation.py
COMPLETE_RAW_DIFFS=YES

COMPLETE RAW UNIFIED DIFFS
warning: in the working copy of 'contextor/core/live_state/watcher.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/query_helpers.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/ui/gui.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_h3a_workspace_canonical_freshness.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_desktop_integration.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_watcher_startup_reconciliation.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/live_state/watcher.py b/contextor/core/live_state/watcher.py
index 811224f..91f6df7 100644
--- a/contextor/core/live_state/watcher.py
+++ b/contextor/core/live_state/watcher.py
@@ -207,16 +207,18 @@ class DesktopLiveWatcher(_PollingLiveWorker):
         self,
         path: str,
         current: dict[str, tuple[int, int]],
+        snapshot: dict | None = None,
     ) -> bool | None:
         """Revalidate a queued path against the generation held after the lease wait."""
-        try:
-            snapshot = self.client.snapshot()
-        except (OSError, EOFError, TimeoutError, ConnectionError):
-            return None
+        if snapshot is None:
+            try:
+                snapshot = self.client.snapshot()
+            except (OSError, EOFError, TimeoutError, ConnectionError):
+                return None
         manager = self._trusted_file_state(snapshot)
         if manager is None:
             self._startup_requires_resync = True
-            return False
+            return None
         if path not in current:
             return path in manager.tracked_paths()
         state = snapshot.get("state")
@@ -298,6 +300,15 @@ class DesktopLiveWatcher(_PollingLiveWorker):
             }
         )
         deferred: set[str] = set()
+        reconciled: list[str] = []
+        next_snapshot = dict(self._snapshot)
+
+        def acknowledge(path: str) -> None:
+            if path in current:
+                next_snapshot[path] = current[path]
+            else:
+                next_snapshot.pop(path, None)
+
         for path in changed:
             from contextor.core.runtime_trace import new_trace_operation, trace_event
 
@@ -340,24 +351,47 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                     self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
                     continue
                 if not candidate_requires_update:
+                    acknowledge(path)
                     continue
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
             except (OSError, EOFError, TimeoutError, ConnectionError):
                 self._emit("LIVE: connection lost during update; recovering...")
                 if self._recover_client() is None:
                     raise
+                try:
+                    recovered_snapshot = self.client.snapshot()
+                except (OSError, EOFError, TimeoutError, ConnectionError):
+                    deferred.add(path)
+                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+                    continue
+                if self._trusted_file_state(recovered_snapshot) is None:
+                    deferred.add(path)
+                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+                    continue
+                candidate_requires_update = self._candidate_requires_update(
+                    path, current, recovered_snapshot
+                )
+                if candidate_requires_update is None:
+                    deferred.add(path)
+                    self._emit("LIVE: generation revalidation unavailable; deferring watcher update")
+                    continue
+                if candidate_requires_update is False:
+                    acknowledge(path)
+                    continue
                 response = self.client.update_file(path, origin="desktop_watcher", trace_op=op)
             finally:
                 if lease is not None:
                     release_full_analysis(lease)
 
-            if response.get("status") != "ok":
-                trace_event("LIVE", "WATCH_UPDATE_FAIL", op=op, repo=str(self.root), path=relative, elapsed_ms=(time.monotonic() - update_started) * 1000.0, err=response.get("error"))
-                self._emit(f"LIVE connection error: {response.get('error', 'update failed')}")
-                raise RuntimeError(f"LIVE update failed for {path}: {response.get('error')}")
+            if not isinstance(response, dict) or response.get("status") != "ok":
+                error = response.get("error", "update failed") if isinstance(response, dict) else "malformed update response"
+                trace_event("LIVE", "WATCH_UPDATE_FAIL", op=op, repo=str(self.root), path=relative, elapsed_ms=(time.monotonic() - update_started) * 1000.0, err=error)
+                self._emit(f"LIVE connection error: {error}")
+                raise RuntimeError(f"LIVE update failed for {path}: {error}")
             result = response.get("result")
-            result_status = getattr(result, "status", "UPDATED")
+            result_status = getattr(result, "status", None)
             trace_event("LIVE", "WATCH_UPDATE_END", op=op, repo=str(self.root), path=relative, rev=response.get("revision"), seq=response.get("seq"), status=result_status, elapsed_ms=(time.monotonic() - update_started) * 1000.0)
+            acknowledged = result_status in {"UPDATED", "DELETED", "UNCHANGED", "RECOVERED", "SYNTAX_ERROR"}
             if result_status == "SYNTAX_ERROR":
                 line = getattr(result, "line_number", None)
                 column = getattr(result, "column_number", None)
@@ -370,13 +404,18 @@ class DesktopLiveWatcher(_PollingLiveWorker):
                 self._emit(f"LIVE update successful: {Path(path).name}")
             else:
                 self._emit(f"LIVE update error: {Path(path).name}: {result_status}")
+            if not acknowledged:
+                deferred.add(path)
+                continue
+            acknowledge(path)
+            reconciled.append(path)
         if deferred:
-            # Retain the old scan so a deferred candidate remains observable.
+            self._snapshot = next_snapshot
             self._startup_pending = sorted(deferred)
-            return [path for path in changed if path not in deferred]
-        self._snapshot = current
+            return reconciled
+        self._snapshot = next_snapshot
         self._startup_pending = []
-        return changed
+        return reconciled
 
     def _handle_poll_error(self, exc: OSError | RuntimeError | EOFError) -> None:
         self._emit(f"LIVE connection error: {exc}")
diff --git a/contextor/mcp/query_helpers.py b/contextor/mcp/query_helpers.py
index cef4b07..bb8c3f6 100644
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -469,6 +469,30 @@ def is_explicit_generation_mismatch(
     if canonical_rev is None and engine is not None:
         canonical_rev = getattr(engine, "revision", None)
 
+    # A referenced generation is authoritative.  FileStateManager intentionally
+    # clears malformed metadata, so inspect that generation directly before its
+    # fail-closed normalization can hide an explicit mismatch from source tools.
+    try:
+        from contextor.core.live_state.store import read_metadata
+        import json
+
+        metadata = read_metadata(repo_cache_dir(root_path))
+        referenced = getattr(metadata, "file_state_file", "") if metadata else ""
+        if referenced:
+            payload = json.loads((repo_cache_dir(root_path) / referenced).read_text(encoding="utf-8"))
+            raw_meta = payload.get("_meta") if isinstance(payload, dict) else None
+            raw_state_id = raw_meta.get("state_id") if isinstance(raw_meta, dict) else None
+            raw_revision = raw_meta.get("revision") if isinstance(raw_meta, dict) else None
+            if (
+                not raw_state_id
+                or raw_revision is None
+                or (canonical_state_id and str(raw_state_id) != str(canonical_state_id))
+                or (canonical_rev is not None and int(raw_revision) != int(canonical_rev))
+            ):
+                return True
+    except (OSError, ValueError, TypeError, json.JSONDecodeError):
+        return True
+
     managers_to_check = []
     if disk_mgr is not None:
         managers_to_check.append(disk_mgr)
@@ -494,4 +518,3 @@ def is_explicit_generation_mismatch(
             return True
     return False
 
-
diff --git a/contextor/ui/gui.py b/contextor/ui/gui.py
index 3557fbe..d4995ef 100644
--- a/contextor/ui/gui.py
+++ b/contextor/ui/gui.py
@@ -882,18 +882,16 @@ class ContextorGUI:
             expected_root_path=identity.root_path,
         )
         if state is not None:
-            current = client.ping() if hasattr(client, "ping") else {}
+            current = client.snapshot() if hasattr(client, "snapshot") else {}
             state_revision = getattr(state, "revision", None)
-            live_snapshot = client.snapshot() if hasattr(client, "snapshot") else {}
-            live_state = live_snapshot.get("state") if isinstance(live_snapshot, dict) else None
+            live_state = current.get("state") if isinstance(current, dict) else None
+            live_revision = current.get("revision") if isinstance(current, dict) else None
             state_id = getattr(state, "state_id", None)
-            if (
-                state_revision is not None
-                and state_id
-                and current.get("revision") == int(state_revision)
-                and getattr(live_state, "state_id", None) == state_id
-            ):
-                self._set_live_status("LIVE: shared state attached; watcher active")
+            if state_revision is not None and live_revision == int(state_revision):
+                if state_id and getattr(live_state, "state_id", None) == state_id:
+                    self._set_live_status("LIVE: shared state attached; watcher active")
+                else:
+                    self._set_live_status("LIVE: generation conflict; analysis required")
             else:
                 published = client.publish(state, origin="desktop_analysis")
                 if isinstance(published, dict) and published.get("status") == "ok":
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index e016021..e3627b2 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -287,6 +287,8 @@ def test_h3a_case_i_crash_window_false_verified_prevented(tmp_path):
     """
     from contextor.core.paths import repo_cache_dir
     from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.live_state.store import read_metadata
+    from contextor.core.live_state.store import read_metadata
 
     repo, mod_a = _setup_repo(tmp_path)
     ContextorFacade.analyze_project(str(repo))
@@ -309,7 +311,10 @@ def test_h3a_case_i_crash_window_false_verified_prevented(tmp_path):
     sm_t1 = FileStateManager(str(cache))
     sm_t1.update_state(str(mod_a))
     t1_state_id = "2026-08-26_T1_CRASHED"
-    sm_t1.save(state_id=t1_state_id, revision=2)
+    metadata = read_metadata(cache)
+    assert metadata is not None and metadata.file_state_file
+    fs_file = cache / metadata.file_state_file
+    fs_file.write_text(json.dumps({"_meta": {"state_id": t1_state_id, "revision": 2}, "files": {path: fs.to_dict() for path, fs in sm_t1._state.items()}}), encoding="utf-8")
 
     # CRASH: do NOT save snapshot T1. Snapshot remains T0 (state_id=t0_state_id, revision=1).
     # Clear all memory caches to simulate process restart / hydration
@@ -317,17 +322,11 @@ def test_h3a_case_i_crash_window_false_verified_prevented(tmp_path):
     mcp_runtime._live_engine_revisions.pop(str(repo), None)
     mcp_runtime._live_engine_provenance.pop(str(repo), None)
 
-    # Query tool now hydrats canonical state from snapshot (T0) and FileStateManager from file_state.json (T1)
+    # The authoritative referenced generation is malformed relative to T0.
     res_raw = get_module_context(repo_path=str(repo), module_name="pkg.mod_a")
-    res = json.loads(res_raw)
-    freshness = res.get("state_freshness")
-
-    assert freshness is not None
-    # Verified that generation mismatch fails closed to unverified
-    assert freshness["workspace_sync"] != "verified"
-    assert freshness["workspace_sync"] != "metadata_match"
+    freshness = json.loads(res_raw)["state_freshness"]
     assert freshness["workspace_sync"] == "unverified"
-    assert "generation" in freshness["advisory_warning"].lower() or "crash" in freshness["advisory_warning"].lower()
+    assert "generation" in freshness["advisory_warning"].lower()
 
 
 def test_h3a_case_j_local_incremental_mutation_revision_sync(tmp_path):
@@ -390,7 +389,7 @@ def test_h3a_case_k_real_remote_live_lifecycle_and_journal_separation(tmp_path):
     """
     import threading
     from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
-    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
+    from contextor.core.live_state.runtime import _repository_persister, _repository_updater, endpoint_file
     from contextor.core.live_state.store import load_snapshot
     from contextor.core.paths import repo_cache_dir
     from contextor.core.repository_identity import require_repository_identity
@@ -406,7 +405,8 @@ def test_h3a_case_k_real_remote_live_lifecycle_and_journal_separation(tmp_path):
     state, metadata = loaded
 
     # 2. Start real CanonicalLiveServer
-    server = CanonicalLiveServer(state, revision=metadata.revision, updater=_repository_updater(repo))
+    holder = {}
+    server = CanonicalLiveServer(state, revision=metadata.revision, updater=_repository_updater(repo, holder), persister=_repository_persister(repo, holder))
     thread = threading.Thread(target=server.serve_forever, daemon=True)
     thread.start()
 
@@ -491,6 +491,7 @@ def test_h3a_case_l_legacy_filestate_missing_revision(tmp_path):
     """
     from contextor.core.paths import repo_cache_dir
     from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.live_state.store import read_metadata
 
     repo, mod_a = _setup_repo(tmp_path)
     ContextorFacade.analyze_project(str(repo))
@@ -506,8 +507,9 @@ def test_h3a_case_l_legacy_filestate_missing_revision(tmp_path):
 
     # Update file_state on disk with matching sha256 and matching state_id, but MISSING revision
     sm.update_state(str(mod_a))
-    # Write file_state.json directly without revision
-    fs_file = cache / "file_state.json"
+    metadata = read_metadata(cache)
+    assert metadata is not None and metadata.file_state_file
+    fs_file = cache / metadata.file_state_file
     fs_data = {
         "_meta": {"state_id": t0_state_id},  # No revision key
         "files": {path: fs.to_dict() for path, fs in sm._state.items()}
@@ -515,11 +517,7 @@ def test_h3a_case_l_legacy_filestate_missing_revision(tmp_path):
     fs_file.write_text(json.dumps(fs_data, indent=2), encoding="utf-8")
 
     mcp_runtime._live_engines.pop(str(repo), None)
-    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
-    freshness = res["state_freshness"]
-
-    assert freshness["workspace_sync"] != "verified"
-    assert freshness["workspace_sync"] != "metadata_match"
+    freshness = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))["state_freshness"]
     assert freshness["workspace_sync"] == "unverified"
     assert "generation" in freshness["advisory_warning"].lower()
 
@@ -532,6 +530,7 @@ def test_h3a_case_m_legacy_filestate_missing_state_id(tmp_path):
     """
     from contextor.core.paths import repo_cache_dir
     from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.live_state.store import read_metadata
 
     repo, mod_a = _setup_repo(tmp_path)
     ContextorFacade.analyze_project(str(repo))
@@ -540,8 +539,9 @@ def test_h3a_case_m_legacy_filestate_missing_state_id(tmp_path):
     cache = repo_cache_dir(repo)
     sm = FileStateManager(str(cache))
 
-    # Write file_state.json with empty state_id
-    fs_file = cache / "file_state.json"
+    metadata = read_metadata(cache)
+    assert metadata is not None and metadata.file_state_file
+    fs_file = cache / metadata.file_state_file
     fs_data = {
         "_meta": {"state_id": "", "revision": 1},
         "files": {path: fs.to_dict() for path, fs in sm._state.items()}
@@ -549,12 +549,9 @@ def test_h3a_case_m_legacy_filestate_missing_state_id(tmp_path):
     fs_file.write_text(json.dumps(fs_data, indent=2), encoding="utf-8")
 
     mcp_runtime._live_engines.pop(str(repo), None)
-    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
-    freshness = res["state_freshness"]
-
-    assert freshness["workspace_sync"] != "verified"
-    assert freshness["workspace_sync"] != "metadata_match"
+    freshness = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))["state_freshness"]
     assert freshness["workspace_sync"] == "unverified"
+    assert "generation" in freshness["advisory_warning"].lower()
 
 
 def test_h3a_case_n_filestate_both_generation_fields_missing(tmp_path):
@@ -565,6 +562,7 @@ def test_h3a_case_n_filestate_both_generation_fields_missing(tmp_path):
     """
     from contextor.core.paths import repo_cache_dir
     from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.live_state.store import read_metadata
 
     repo, mod_a = _setup_repo(tmp_path)
     ContextorFacade.analyze_project(str(repo))
@@ -573,20 +571,18 @@ def test_h3a_case_n_filestate_both_generation_fields_missing(tmp_path):
     cache = repo_cache_dir(repo)
     sm = FileStateManager(str(cache))
 
-    # Write file_state.json without _meta or empty _meta
-    fs_file = cache / "file_state.json"
+    metadata = read_metadata(cache)
+    assert metadata is not None and metadata.file_state_file
+    fs_file = cache / metadata.file_state_file
     fs_data = {
         "files": {path: fs.to_dict() for path, fs in sm._state.items()}
     }
     fs_file.write_text(json.dumps(fs_data, indent=2), encoding="utf-8")
 
     mcp_runtime._live_engines.pop(str(repo), None)
-    res = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))
-    freshness = res["state_freshness"]
-
-    assert freshness["workspace_sync"] != "verified"
-    assert freshness["workspace_sync"] != "metadata_match"
+    freshness = json.loads(get_module_context(repo_path=str(repo), module_name="pkg.mod_a"))["state_freshness"]
     assert freshness["workspace_sync"] == "unverified"
+    assert "generation" in freshness["advisory_warning"].lower()
 
 
 def test_h3a_case_o_live_daemon_restart_cache_invalidation_across_epochs(tmp_path):
@@ -608,7 +604,7 @@ def test_h3a_case_o_live_daemon_restart_cache_invalidation_across_epochs(tmp_pat
     """
     import threading
     from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
-    from contextor.core.live_state.runtime import _repository_updater, endpoint_file
+    from contextor.core.live_state.runtime import _repository_persister, _repository_updater, endpoint_file
     from contextor.core.live_state.store import load_snapshot
     from contextor.core.paths import repo_cache_dir
     from contextor.core.repository_identity import require_repository_identity
@@ -623,7 +619,8 @@ def test_h3a_case_o_live_daemon_restart_cache_invalidation_across_epochs(tmp_pat
     state, metadata = loaded
     p0 = metadata.revision  # 1
 
-    server1 = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo))
+    holder1 = {}
+    server1 = CanonicalLiveServer(state, revision=p0, updater=_repository_updater(repo, holder1), persister=_repository_persister(repo, holder1))
     t1 = threading.Thread(target=server1.serve_forever, daemon=True)
     t1.start()
 
@@ -661,7 +658,8 @@ def test_h3a_case_o_live_daemon_restart_cache_invalidation_across_epochs(tmp_pat
     # 3. Start Server S2 from disk snapshot (without clearing MCP cache)
     loaded_s2 = load_snapshot(cache, expected_repo_id=identity.repo_id, expected_root_path=identity.root_path)
     state_s2, metadata_s2 = loaded_s2
-    server2 = CanonicalLiveServer(state_s2, revision=metadata_s2.revision, updater=_repository_updater(repo))
+    holder2 = {}
+    server2 = CanonicalLiveServer(state_s2, revision=metadata_s2.revision, updater=_repository_updater(repo, holder2), persister=_repository_persister(repo, holder2))
     t2 = threading.Thread(target=server2.serve_forever, daemon=True)
     t2.start()
 
@@ -1000,6 +998,7 @@ def test_h3a_case_s_explicit_generation_mismatch_symbol_fail_closed(tmp_path):
     """
     from contextor.core.paths import repo_cache_dir
     from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.live_state.store import read_metadata
     from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation
 
     repo, mod_a = _setup_repo(tmp_path)
@@ -1019,7 +1018,15 @@ def test_h3a_case_s_explicit_generation_mismatch_symbol_fail_closed(tmp_path):
     # Mutate FileStateManager on disk to simulate explicit generation mismatch (P1 on disk, P0 in engine)
     sm = FileStateManager(str(cache))
     sm.update_state(str(mod_a))
-    sm.save(state_id="2026-08-27_P1_MISMATCH", revision=p0_rev + 1)
+    metadata = read_metadata(cache)
+    assert metadata is not None and metadata.file_state_file
+    (cache / metadata.file_state_file).write_text(
+        json.dumps({
+            "_meta": {"state_id": "2026-08-27_P1_MISMATCH", "revision": p0_rev + 1},
+            "files": {path: fs.to_dict() for path, fs in sm._state.items()},
+        }),
+        encoding="utf-8",
+    )
 
     # get_symbol_implementation with cached engine (holding P0) against FileState on disk (holding P1)
     sym_res = json.loads(get_symbol_implementation(repo_path=str(repo), symbol="compute_data", mode="fetch", include=["implementation"]))
@@ -1577,6 +1584,3 @@ def test_h3a_case_aa_analysis_job_revision_mismatch_fails_closed(tmp_path, monke
     assert "loaded=3" in final_job["error"]
     assert "published=42" in final_job["error"]
     assert str(repo) not in mcp_runtime._live_engine_revisions
-
-
-
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index b31327a..4fee12a 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -33,7 +33,7 @@ def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monk
             return {"revision": 7, "available": True}
 
         def snapshot(self):
-            return {"state": state}
+            return {"state": state, "revision": 7}
 
         def publish(self, *_args, **_kwargs):
             events.append("publish")
@@ -46,6 +46,7 @@ def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monk
         def __init__(self, *_args, **_kwargs): pass
         def start(self): pass
 
+    statuses = []
     statuses = []
     controller = SimpleNamespace(
         live_watcher=None, live_event_feed=None, live_watchers={},
@@ -66,6 +67,49 @@ def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monk
     assert "LIVE: shared state attached; watcher active" in statuses
 
 
+def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp_path, monkeypatch):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    loaded = SimpleNamespace(modules={}, revision=7, state_id="loaded-generation")
+    remote = SimpleNamespace(modules={}, revision=7, state_id="remote-generation")
+    events = []
+    statuses = []
+
+    class Client:
+        def snapshot(self):
+            return {"state": remote, "revision": 7}
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
+    assert events == []
+    assert "LIVE: generation conflict; analysis required" in statuses
+
+
 def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
     tmp_path, monkeypatch
 ):
@@ -479,6 +523,7 @@ def test_desktop_watcher_recovers_after_live_service_death(tmp_path):
     # Mock client 2 that succeeds
     recovered_client = MagicMock()
     recovered_client.ping.return_value = {"status": "ok", "available": True}
+    recovered_client.snapshot.return_value = {"status": "ok"}
     recovered_client.update_file.return_value = {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
 
     def on_reconnect(client):
@@ -503,6 +548,8 @@ def test_desktop_watcher_recovers_after_live_service_death(tmp_path):
         return recovered_client
 
     watcher._recover_client = mock_recover
+    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._candidate_requires_update = lambda _path, _current: True
 
     # Modify file so that watcher detects a change
     py_file.write_text("x = 2000\n", encoding="utf-8")
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index 7017ac0..488f5e2 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -418,3 +418,185 @@ def test_post_lease_snapshot_failure_never_dispatches_unverified_update(tmp_path
     assert watcher.poll_once() == []
     assert calls == []
     assert watcher._startup_pending == [str(source)]
+
+
+def test_startup_resync_with_analysis_errors_remains_untrusted(tmp_path):
+    repo = tmp_path / "repo"; repo.mkdir(); (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
+    class Client:
+        def snapshot(self): return {"status": "ok", "state": RepositoryAnalysisState(modules={})}
+        def ping(self): return {"status": "ok", "available": True}
+        def update_file(self, *_args, **_kwargs): raise AssertionError("fallback update")
+    watcher = DesktopLiveWatcher(repo, Client(), on_resync=lambda: (["error"], object()))
+    assert watcher.poll_once() == []
+    assert watcher._startup_requires_resync is True
+
+
+def test_full_analysis_waits_for_inflight_watcher_mutation(tmp_path):
+    from contextor.core.analysis.full_analysis_coordinator import acquire_full_analysis, release_full_analysis
+    repo = tmp_path / "repo"; repo.mkdir(); PersistentIdentityRegistry(str(repo))
+    lease = acquire_full_analysis(repo, owner="watcher", timeout=1)
+    entered = threading.Event()
+    finished = threading.Event()
+    def run():
+        try:
+            other = acquire_full_analysis(repo, owner="analysis", timeout=2)
+            entered.set(); release_full_analysis(other)
+        finally: finished.set()
+    thread = threading.Thread(target=run); thread.start()
+    assert not entered.wait(0.1)
+    release_full_analysis(lease); assert finished.wait(2); thread.join()
+
+
+def test_watcher_does_not_mutate_during_full_analysis_and_rebases_after_publish(tmp_path):
+    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
+    calls = []
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+    original = coordinator.acquire_full_analysis
+    busy = {"first": True}
+    def acquire(root, *, owner, timeout):
+        if busy["first"]:
+            busy["first"] = False
+            raise coordinator.FullAnalysisBusyError("analysis owns lease")
+        return original(root, owner=owner, timeout=timeout)
+    class Client:
+        def ping(self): return {"status": "ok", "available": True}
+        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
+        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
+    watcher = DesktopLiveWatcher(repo, Client())
+    watcher._snapshot = {str(source): (0, 1)}
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._candidate_requires_update = lambda *_args: False
+    monkeypatch = pytest.MonkeyPatch()
+    monkeypatch.setattr(coordinator, "acquire_full_analysis", acquire)
+    try:
+        assert watcher.poll_once() == []
+        assert calls == []
+        assert watcher.poll_once() == []
+        assert calls == []
+    finally:
+        monkeypatch.undo()
+
+
+def test_change_during_startup_resync_is_not_lost(tmp_path):
+    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
+    calls = []
+    class Client:
+        def ping(self): return {"status": "ok", "available": True}
+        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
+        def update_file(self, *_args, **_kwargs): calls.append("update"); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
+    def resync():
+        source.write_text("VALUE = 2\n", encoding="utf-8")
+        return ([], object())
+    watcher = DesktopLiveWatcher(repo, Client(), on_resync=resync)
+    watcher._startup_requires_resync = True
+    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._candidate_requires_update = lambda *_args: True
+    assert watcher.poll_once() == []
+    assert calls == []
+    watcher._snapshot = {str(source): (0, 1)}
+    assert watcher.poll_once() == [str(source)]
+    assert calls == ["update"]
+
+
+def test_update_transport_recovery_revalidates_generation_before_retry(tmp_path):
+    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
+
+    def run_case(candidate_values, commit_first, expected_calls):
+        calls = []
+        class Client:
+            def __init__(self): self.recovered = False
+            def ping(self): return {"status": "ok", "available": True}
+            def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=2 if commit_first else 1, state_id="g")}
+            def update_file(self, *_args, **_kwargs):
+                calls.append("update")
+                if len(calls) == 1 and commit_first: raise ConnectionError("response lost after commit")
+                if len(calls) == 1 and not commit_first: raise ConnectionError("before commit")
+                return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
+        client = Client()
+        watcher = DesktopLiveWatcher(repo, client)
+        watcher._snapshot = {str(source): (0, 1)}
+        source.write_text("VALUE = 2\n", encoding="utf-8")
+        watcher._trusted_file_state = lambda _snapshot: object()
+        values = iter(candidate_values)
+        watcher._candidate_requires_update = lambda *_args: next(values)
+        watcher._recover_client = lambda: client
+        result = watcher.poll_once()
+        assert len(calls) == expected_calls
+        return result
+
+    assert run_case([True, False], True, 1) == []
+    assert run_case([True, True], False, 2) == [str(source)]
+    assert run_case([True, None], False, 1) == []
+
+
+def test_update_error_result_is_not_acknowledged_into_watcher_snapshot(tmp_path):
+    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
+    calls = []
+    class Client:
+        def ping(self): return {"status": "ok", "available": True}
+        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
+        def update_file(self, *_args, **_kwargs):
+            calls.append("update")
+            status = "ERROR" if len(calls) == 1 else "UPDATED"
+            return {"status": "ok", "result": SimpleNamespace(status=status)}
+    watcher = DesktopLiveWatcher(repo, Client())
+    watcher._snapshot = {str(source): (0, 1)}
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    watcher._trusted_file_state = lambda _snapshot: object()
+    watcher._candidate_requires_update = lambda *_args: True
+
+    assert watcher.poll_once() == []
+    assert calls == ["update"]
+    assert watcher._startup_pending == [str(source)]
+    assert watcher.poll_once() == [str(source)]
+    assert calls == ["update", "update"]
+
+
+def test_deferred_candidate_does_not_replay_already_reconciled_sibling(tmp_path):
+    repo = tmp_path / "repo"; repo.mkdir()
+    first = repo / "a.py"; second = repo / "b.py"
+    first.write_text("A = 1\n", encoding="utf-8"); second.write_text("B = 1\n", encoding="utf-8")
+    calls = []
+    class Client:
+        def ping(self): return {"status": "ok", "available": True}
+        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
+        def update_file(self, path, **_kwargs): calls.append(path); return {"status": "ok", "result": SimpleNamespace(status="UPDATED")}
+    watcher = DesktopLiveWatcher(repo, Client())
+    watcher._snapshot = {str(first): (0, 1), str(second): (0, 1)}
+    first.write_text("A = 2\n", encoding="utf-8"); second.write_text("B = 2\n", encoding="utf-8")
+    watcher._trusted_file_state = lambda _snapshot: object()
+    deferred = {str(second)}
+    watcher._candidate_requires_update = lambda path, *_args: None if path in deferred else True
+    assert watcher.poll_once() == [str(first)]
+    assert calls == [str(first)]
+    deferred.clear()
+    assert watcher.poll_once() == [str(second)]
+    assert calls == [str(first), str(second)]
+
+
+def test_missing_update_result_is_not_acknowledged(tmp_path):
+    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
+    class Client:
+        def ping(self): return {"status": "ok", "available": True}
+        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
+        def update_file(self, *_args, **_kwargs): return {"status": "ok"}
+    watcher = DesktopLiveWatcher(repo, Client()); watcher._snapshot = {str(source): (0, 1)}
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    watcher._trusted_file_state = lambda _snapshot: object(); watcher._candidate_requires_update = lambda *_args: True
+    assert watcher.poll_once() == []
+    assert watcher._startup_pending == [str(source)]
+
+
+def test_error_top_level_response_is_not_acknowledged(tmp_path):
+    repo = tmp_path / "repo"; repo.mkdir(); source = repo / "module.py"; source.write_text("VALUE = 1\n", encoding="utf-8")
+    class Client:
+        def ping(self): return {"status": "ok", "available": True}
+        def snapshot(self): return {"status": "ok", "state": SimpleNamespace(revision=1, state_id="g")}
+        def update_file(self, *_args, **_kwargs): return {"status": "error", "error": "rejected"}
+    watcher = DesktopLiveWatcher(repo, Client()); watcher._snapshot = {str(source): (0, 1)}
+    source.write_text("VALUE = 2\n", encoding="utf-8")
+    watcher._trusted_file_state = lambda _snapshot: object(); watcher._candidate_requires_update = lambda *_args: True
+    with pytest.raises(RuntimeError, match="rejected"):
+        watcher.poll_once()
+    assert watcher._snapshot[str(source)] == (0, 1)


