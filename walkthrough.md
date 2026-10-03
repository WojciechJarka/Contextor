STATUS=PASS
FILES_CHANGED=contextor/core/runtime_trace.py, tests/test_runtime_trace.py

FULL_DIFFS=BEGIN
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 759555d..2ebfcaf 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1532,6 +1532,26 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
             "owner": "canonical writer owner",
             "writer_kind": "canonical writer kind",
             "origin": "LIVE update origin",
+            "snapshot_loaded": "whether a canonical snapshot was loaded during LIVE startup",
+            "materialization_required": "whether module-usage materialization was required during LIVE startup",
+            "migrate_legacy_snapshot_ms": "legacy snapshot migration wall milliseconds",
+            "load_snapshot_ms": "canonical snapshot load wall milliseconds",
+            "materialization_import_ms": "incremental materialization import wall milliseconds",
+            "module_usages_require_materialization_ms": "module-usage materialization check wall milliseconds",
+            "file_state_manager_import_ms": "FileStateManager import wall milliseconds",
+            "file_state_manager_load_ms": "FileStateManager construction wall milliseconds",
+            "ensure_module_usages_ms": "module-usage materialization wall milliseconds",
+            "file_state_build_payload_ms": "file-state payload build wall milliseconds",
+            "backfill_save_snapshot_ms": "backfill snapshot save wall milliseconds",
+            "read_metadata_ms": "canonical metadata read wall milliseconds",
+            "canonical_live_server_construct_ms": "CanonicalLiveServer construction wall milliseconds",
+            "service_thread_construct_ms": "LIVE service thread construction wall milliseconds",
+            "service_thread_start_ms": "LIVE service thread start wall milliseconds",
+            "service_bootstrap_wait_ms": "LIVE service bootstrap wait wall milliseconds",
+            "authority_endpoint_build_ms": "authority endpoint construction wall milliseconds",
+            "endpoint_atomic_write_ms": "endpoint atomic write wall milliseconds",
+            "bind_endpoint_ms": "runtime lease endpoint bind wall milliseconds",
+            "pre_endpoint_total_ms": "total measured LIVE startup wall milliseconds through endpoint lease bind",
             "diagnostic_kind": "canonical diagnostic family",
             "diagnostic_key": "stable canonical diagnostic identity",
             "collision_kind": "canonical collision kind",
@@ -1663,6 +1683,7 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
     )
     records[4]["events"]["LIVE"].extend(
         [
+            "LIVE_SERVICE_PRE_ENDPOINT_TIMING",
             "LIVE_DIAGNOSTIC_SYNTAX_ERROR",
             "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED",
             "LIVE_DIAGNOSTIC_COLLISION_ADDED",
@@ -1804,6 +1825,26 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
         key_map.update(
             {
                 "origin": "origin",
+                "snapshot_loaded": "snapshot_loaded",
+                "materialization_required": "materialization_required",
+                "migrate_legacy_snapshot_ms": "migrate_legacy_snapshot_ms",
+                "load_snapshot_ms": "load_snapshot_ms",
+                "materialization_import_ms": "materialization_import_ms",
+                "module_usages_require_materialization_ms": "module_usages_require_materialization_ms",
+                "file_state_manager_import_ms": "file_state_manager_import_ms",
+                "file_state_manager_load_ms": "file_state_manager_load_ms",
+                "ensure_module_usages_ms": "ensure_module_usages_ms",
+                "file_state_build_payload_ms": "file_state_build_payload_ms",
+                "backfill_save_snapshot_ms": "backfill_save_snapshot_ms",
+                "read_metadata_ms": "read_metadata_ms",
+                "canonical_live_server_construct_ms": "canonical_live_server_construct_ms",
+                "service_thread_construct_ms": "service_thread_construct_ms",
+                "service_thread_start_ms": "service_thread_start_ms",
+                "service_bootstrap_wait_ms": "service_bootstrap_wait_ms",
+                "authority_endpoint_build_ms": "authority_endpoint_build_ms",
+                "endpoint_atomic_write_ms": "endpoint_atomic_write_ms",
+                "bind_endpoint_ms": "bind_endpoint_ms",
+                "pre_endpoint_total_ms": "pre_endpoint_total_ms",
                 "job_id": "job_id",
                 "idempotency_key": "idempotency_key",
                 "queue_order": "queue_order",
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index a5b4940..1b1d4f0 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -52,6 +52,80 @@ def test_desktop_trace_session_headers_and_finish(tmp_path, monkeypatch):
     assert {"LIVE_CONNECT_ATTEMPT", "LIVE_CONNECT_REJECT", "LIVE_CONNECT_RESULT", "LIVE_LIVENESS_RESULT", "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT", "LIVE_IPC_FAILURE", "LIVE_SERVICE_THREAD_FAILURE"} <= set(events)
 
 
+def test_live_service_pre_endpoint_timing_is_self_describing_and_durable():
+    path = trace.start_desktop_trace_session()
+
+    payload = {
+        "snapshot_loaded": True,
+        "materialization_required": False,
+        "migrate_legacy_snapshot_ms": 10.0,
+        "load_snapshot_ms": 20.0,
+        "materialization_import_ms": 30.0,
+        "module_usages_require_materialization_ms": 40.0,
+        "file_state_manager_import_ms": 50.0,
+        "file_state_manager_load_ms": 60.0,
+        "ensure_module_usages_ms": 70.0,
+        "file_state_build_payload_ms": 80.0,
+        "backfill_save_snapshot_ms": 90.0,
+        "read_metadata_ms": 100.0,
+        "canonical_live_server_construct_ms": 110.0,
+        "service_thread_construct_ms": 120.0,
+        "service_thread_start_ms": 130.0,
+        "service_bootstrap_wait_ms": 140.0,
+        "authority_endpoint_build_ms": 150.0,
+        "endpoint_atomic_write_ms": 160.0,
+        "bind_endpoint_ms": 170.0,
+        "pre_endpoint_total_ms": 180.0,
+    }
+
+    trace.trace_event(
+        "LIVE",
+        "LIVE_SERVICE_PRE_ENDPOINT_TIMING",
+        **payload,
+    )
+
+    trace.finish_desktop_trace_session()
+
+    records = [
+        json.loads(line)
+        for line in path.read_text(
+            encoding="utf-8"
+        ).splitlines()
+    ]
+
+    fields = records[1]["fields"]
+    events = records[4]["events"]["LIVE"]
+
+    assert (
+        "LIVE_SERVICE_PRE_ENDPOINT_TIMING"
+        in events
+    )
+
+    assert set(payload) <= set(fields)
+
+    record = next(
+        item
+        for item in records
+        if item.get("ev")
+        == "LIVE_SERVICE_PRE_ENDPOINT_TIMING"
+    )
+
+    assert {
+        key: record[key]
+        for key in payload
+    } == payload
+
+    assert record["snapshot_loaded"] is True
+    assert (
+        record["materialization_required"]
+        is False
+    )
+    assert (
+        record["pre_endpoint_total_ms"]
+        == 180.0
+    )
+
+
 def test_canonical_writer_analysis_trace_is_self_describing_and_durable():
     path = trace.start_desktop_trace_session()
     trace.trace_event(
FULL_DIFFS=END

PY_COMPILE=PASS
PY_COMPILE_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m py_compile C:\Temp\Contextor_Repo\contextor\core\runtime_trace.py C:\Temp\Contextor_Repo\tests\test_runtime_trace.py
TARGETED_TESTS=PASS
TARGETED_TEST_COUNT=2
TARGETED_FAILURES=NONE
TARGETED_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_runtime_trace.py::test_live_service_pre_endpoint_timing_is_self_describing_and_durable tests/test_runtime_trace.py::test_desktop_trace_session_headers_and_finish

PRE_ENDPOINT_EVENT_IN_HEADER=YES
PRE_ENDPOINT_ALL_20_FIELDS_IN_HEADER=YES
PRE_ENDPOINT_ALL_20_FIELDS_DURABLE=YES
EMITTER_CHANGED=NO
TRACE_SCHEMA_CHANGED=NO
WORKSPACE_SYNC=verified
CANONICAL_STATE=fresh
CONTEXTOR_REVISION=1454
MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_RUNTIME_RESTART_REQUIRED=YES
RESTART_PERFORMED=NO
FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
PROCESS_TERMINATION_PERFORMED=NO
FIX_DESIGNED_BY_AGENT=NO
PATCH_FIRST_ATTEMPT=APPLY_PATCH_VERIFICATION_FAILED
NO_PARTIAL_CHANGE_FROM_FIRST_ATTEMPT=YES
