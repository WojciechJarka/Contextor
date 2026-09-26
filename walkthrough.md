STATUS=EDIT_COMPLETE_WAITING_FOR_PROCEDUJ
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
ACTUAL_DIFF=ONE_FILE_INSTRUMENTATION_DIFF_IN_FULL_DIFFS_BELOW

PRE_EDIT_LIVE_REVISION=1431
POST_EDIT_LIVE_REVISION=1432
WORKSPACE_SYNC=verified
DESKTOP_WATCHER_PUBLICATION=YES; get_live_events returned status=ok, revision=1432, latest_revision=1432, origin=desktop_watcher, operation=update_file, status=UPDATED, file_path=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py, resync_required=false
POST_EDIT_CONTEXTOR=canonical_state=fresh; workspace_sync=verified; provenance=live; canonical_revision=1432; syntax_errors=0 fresh; name_collisions=0 fresh; cycles=0 fresh
POST_EDIT_BLAST_RADIUS=run_service A2526/1; direct static consumers remain the 2 test modules tests.test_live_authority_bootstrap and tests.test_live_state_ipc; no direct production consumers reported

TELEMETRY_EVENT=LIVE_SERVICE_PRE_ENDPOINT_TIMING
MEASURED_FIELDS=migrate_legacy_snapshot_ms, load_snapshot_ms, materialization_import_ms, module_usages_require_materialization_ms, file_state_manager_import_ms, file_state_manager_load_ms, ensure_module_usages_ms, file_state_build_payload_ms, backfill_save_snapshot_ms, read_metadata_ms, canonical_live_server_construct_ms, service_thread_construct_ms, service_thread_start_ms, service_bootstrap_wait_ms, authority_endpoint_build_ms, endpoint_atomic_write_ms, bind_endpoint_ms, pre_endpoint_total_ms
SEMANTIC_ORDER_CHANGED=NO
TIMEOUTS_CHANGED=NO
PUBLIC_API_CHANGED=NO
PERSISTENCE_SCHEMA_CHANGED=NO

PY_COMPILE=NOT_RUN; checkpoint stop before validation
TARGETED_TESTS=NOT_RUN; Contextor-indicated candidates:
tests.test_live_authority_bootstrap::test_run_service_reconciles_bind_split_before_release_and_next_generation_bootstraps
tests.test_live_state_ipc::test_run_service_fails_closed_when_service_thread_dies_before_ready
tests.test_live_state_ipc::test_run_service_fails_closed_when_service_thread_raises_before_endpoint
tests.test_live_state_ipc::test_run_service_fingerprint_diagnostic_failure_does_not_mask_service_failure
tests.test_live_state_ipc::test_run_service_rejects_stop_and_return_before_ready
tests.test_live_state_ipc::test_run_service_trace_emitter_failure_does_not_mask_service_failure

MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_RUNTIME_RESTART_REQUIRED=YES
FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
RESTART_PERFORMED=NO
PROCESS_TERMINATION_PERFORMED=NO
FIX_DESIGNED_BY_AGENT=NO

FINDINGS=
All requested monotonic fields are measured around the existing synchronous calls. Materialization-only fields are added only in their branch. The predicate is evaluated exactly once. read_metadata is now one call. The bootstrap wait remains one call with timeout=0.25. One aggregate _safe_trace_event is placed immediately after bind_endpoint and before current_endpoint readback. No per-step trace event was added.
Only authorized source file changed. The report file is excluded from source diffs. No compile, tests, restart, process termination, or analyze_project has run. The agent did not call MCP update_file; desktop_watcher published the authorized file change.

ACTIONS=
Applied only the literal requested telemetry changes in runtime.py. Reviewed the complete diff. Confirmed desktop_watcher publication and re-queried Contextor module context and run_service blast radius.

EVIDENCE=
The complete diff below is the actual current-task diff for runtime.py. Pre-edit revision was 1431; desktop_watcher published the file at revision 1432. Contextor reports the post-edit module and source fresh with verified workspace sync.

TEST_RESULT=
Not run at this checkpoint.

NEXT_STEP=
Await the user's next proceduj before py_compile and the six targeted tests. No restart will be performed by the agent.

FULL_DIFFS_BEGIN
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 920f866..506d3ce 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1338,30 +1338,79 @@ def run_service(
                 desktop_instance_id,
                 ProcessIdentity(owner_pid, desktop_process_start_identity),
             )
+        startup_timing_started = time.monotonic()
+        startup_timings_ms: dict[str, float] = {}
+        materialization_required = False
+
+        step_started = time.monotonic()
         cache = migrate_legacy_snapshot(root)
+        startup_timings_ms["migrate_legacy_snapshot_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
+        step_started = time.monotonic()
         loaded = load_snapshot(
             cache,
             expected_repo_id=identity.repo_id,
             expected_root_path=identity.root_path,
         )
+        startup_timings_ms["load_snapshot_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
         state = loaded[0] if loaded else None
         if state is not None:
+            step_started = time.monotonic()
             from contextor.core.analysis.incremental.materialization import (
                 ensure_module_usages,
                 module_usages_require_materialization,
             )
+            startup_timings_ms["materialization_import_ms"] = round(
+                (time.monotonic() - step_started) * 1000.0,
+                3,
+            )
+
+            step_started = time.monotonic()
+            materialization_required = module_usages_require_materialization(state)
+            startup_timings_ms[
+                "module_usages_require_materialization_ms"
+            ] = round(
+                (time.monotonic() - step_started) * 1000.0,
+                3,
+            )
 
-            if module_usages_require_materialization(state):
+            if materialization_required:
                 loaded_metadata = loaded[1]
+                step_started = time.monotonic()
                 from contextor.core.analysis.state_manager import FileStateManager
+                startup_timings_ms["file_state_manager_import_ms"] = round(
+                    (time.monotonic() - step_started) * 1000.0,
+                    3,
+                )
 
+                step_started = time.monotonic()
                 file_state_manager = FileStateManager(str(cache))
+                startup_timings_ms["file_state_manager_load_ms"] = round(
+                    (time.monotonic() - step_started) * 1000.0,
+                    3,
+                )
+                step_started = time.monotonic()
                 ensure_module_usages(state)
+                startup_timings_ms["ensure_module_usages_ms"] = round(
+                    (time.monotonic() - step_started) * 1000.0,
+                    3,
+                )
                 target_revision = loaded_metadata.revision + 1
+                step_started = time.monotonic()
                 file_state_payload = file_state_manager.build_payload(
                     loaded_metadata.state_id,
                     target_revision,
                 )
+                startup_timings_ms["file_state_build_payload_ms"] = round(
+                    (time.monotonic() - step_started) * 1000.0,
+                    3,
+                )
+                step_started = time.monotonic()
                 save_snapshot(
                     state,
                     cache,
@@ -1372,7 +1421,17 @@ def run_service(
                     exact_revision=target_revision,
                     file_state_payload=file_state_payload,
                 )
-        revision = read_metadata(cache).revision if read_metadata(cache) else 0
+                startup_timings_ms["backfill_save_snapshot_ms"] = round(
+                    (time.monotonic() - step_started) * 1000.0,
+                    3,
+                )
+        step_started = time.monotonic()
+        startup_metadata = read_metadata(cache)
+        startup_timings_ms["read_metadata_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
+        revision = startup_metadata.revision if startup_metadata else 0
         adapter_holder: dict[str, object] = {}
         authority_identity = {
             "repo_id": identity.repo_id,
@@ -1386,6 +1445,7 @@ def run_service(
             "owner_token": owner_token,
             "desktop_instance_id": desktop_instance_id,
         }
+        step_started = time.monotonic()
         server = CanonicalLiveServer(
             state,
             revision=revision,
@@ -1413,19 +1473,40 @@ def run_service(
                 ProcessIdentity(desktop_pid, desktop_start),
             ),
         )
+        startup_timings_ms["canonical_live_server_construct_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
         # The listener is bound by CanonicalLiveServer construction, but it is
         # not client-usable until its accept loop runs.  Start that loop before
         # endpoint publication; the endpoint remains private until all durable
         # authority bindings below are verified.
+        step_started = time.monotonic()
         server_thread = threading.Thread(
             target=_serve_service,
             name="contextor-live-service",
             daemon=True,
         )
+        startup_timings_ms["service_thread_construct_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
+        step_started = time.monotonic()
         server_thread.start()
-        if not service_bootstrap_entered.wait(timeout=0.25):
+        startup_timings_ms["service_thread_start_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
+        step_started = time.monotonic()
+        bootstrap_entered = service_bootstrap_entered.wait(timeout=0.25)
+        startup_timings_ms["service_bootstrap_wait_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
+        if not bootstrap_entered:
             raise RuntimeError("Canonical LIVE service thread did not enter bootstrap")
         _raise_if_service_terminated("pre-endpoint bootstrap")
+        step_started = time.monotonic()
         published_endpoint = _authority_endpoint_from_server(
             server,
             identity,
@@ -1435,9 +1516,38 @@ def run_service(
             owner_token=owner_token,
             desktop_instance_id=desktop_instance_id,
         )
+        startup_timings_ms["authority_endpoint_build_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
         server.endpoint = published_endpoint
+        step_started = time.monotonic()
         _write_endpoint_atomic(published_endpoint, root)
+        startup_timings_ms["endpoint_atomic_write_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
+        step_started = time.monotonic()
         manager.bind_endpoint(lease, published_endpoint.fingerprint())
+        startup_timings_ms["bind_endpoint_ms"] = round(
+            (time.monotonic() - step_started) * 1000.0,
+            3,
+        )
+        pre_endpoint_total_ms = round(
+            (time.monotonic() - startup_timing_started) * 1000.0,
+            3,
+        )
+        _safe_trace_event(
+            "LIVE",
+            "LIVE_SERVICE_PRE_ENDPOINT_TIMING",
+            repo_id=identity.repo_id,
+            service_instance_id=lease.service_instance_id,
+            lease_generation=lease.lease_generation,
+            snapshot_loaded=loaded is not None,
+            materialization_required=materialization_required,
+            pre_endpoint_total_ms=pre_endpoint_total_ms,
+            **startup_timings_ms,
+        )
         current_endpoint = _read_endpoint(root, strict=True)
         current_lease = manager.read_live_lease()
         current_record = manager.read_generation()
FULL_DIFFS_END
