# CPA10M7B2_WIRE_INDEXER_TO_REUSABLE_POOL_AND_BATCH_TELEMETRY

## STATUS
STATUS=BLOCKED_CONTEXTOR_SYNC
BLOCK_REASON=INDEXER_WORKSPACE_SYNC_OUT_OF_SYNC
FINAL_PASS=NO
RUNTIME_GATE=PASS
SOURCE_GATE=PASS
SOURCE_DRIFT=NO

## RUNTIME_GATE
PRE_M7B1_MCP_PID=4768
PRE_M7B1_DESKTOP_PID=15508
CURRENT_MCP_PID=5756
CURRENT_DESKTOP_PID=5748
CURRENT_MCP_PID_EVIDENCE=Contextor runtime lease process_id plus live Win32 process identity for contextor.core.live_state.runtime
CURRENT_DESKTOP_PID_EVIDENCE=Contextor desktop claim process_id plus live Win32 process identity for main.py --gui
CURRENT_MCP_PID_DIFFERENT_FROM_PREVIOUS=YES
CURRENT_DESKTOP_PID_DIFFERENT_FROM_PREVIOUS=YES

## SOURCE_GATE
PRE_EDIT_CANONICAL_REVISION=1406
PRE_EDIT_WORKSPACE_SYNC=verified for all four allowed files
PRE_EDIT_ALLOWED_FILES_GIT_CLEAN=YES
REQUIRED_LITERAL_ANCHORS=PASS
MANAGED_REUSABLE_PROCESS_POOL_EXISTS=YES
PRE_EDIT_MANAGED_REUSABLE_DIRECT_CONSUMERS=tests.test_process_pool_lifecycle only
PRE_EDIT_LEGACY_MANAGED_DIRECT_CONSUMERS=contextor.core.symbol_engine.indexer; contextor.core.reporting_layer.artifact_usage_report; tests.test_process_pool_lifecycle

## IMPLEMENTATION
ARTIFACT_USAGE_POOL_CHANGED=NO
LEGACY_MANAGED_POOL_IMPLEMENTATION_CHANGED=NO
ARTIFACT_USAGE_REPORT_FILE_CHANGED=NO

## REUSABLE_POOL_WIRING
INDEXER_USES_REUSABLE_POOL=YES
REUSABLE_POOL_KEY=indexer
INDEXER_IS_ONLY_PRODUCTION_CALLER_MIGRATED=YES
NORMAL_SUCCESSFUL_INDEX_RUN_TERMINATES_WORKERS=NO
ABNORMAL_EXCEPTION_INVALIDATES_WORKER_GENERATION=YES
REGISTRY_SCOPE_CHANGE_ROTATES_GENERATION=YES

## BATCH_TELEMETRY
PROCESS_POOL_REUSED_FIELD_ADDED=YES
PROCESS_POOL_GENERATION_FIELD_ADDED=YES
FIRST_TASK_SEMANTICS=FIRST_TASK_PER_WORKER_PER_INDEX_REPOSITORY_BATCH
FIRST_TASK_PROCESS_LIFETIME_SEMANTICS_REMOVED=YES
REAL_TWO_RUN_REUSE_TEST=PASS

## CANCELLATION
CANCELLATION_DOUBLE_TERMINATION_REMOVED=YES
CANCELLATION_INVALIDATES_WORKER_GENERATION=YES

## VALIDATION
PY_COMPILE=PASS
PY_COMPILE_COMMAND=.venv\Scripts\python.exe -m py_compile contextor\core\symbol_engine\indexer.py contextor\core\runtime_trace.py tests\test_indexer_profile_evidence.py tests\test_runtime_trace.py
FIRST_TEST_GATE=PASS
FIRST_TEST_GATE_RESULT=13 passed in 3.90s
TARGETED_TESTS=PASS
TARGETED_TEST_COMMAND=.venv\Scripts\python.exe -m pytest -q tests/test_process_pool_lifecycle.py tests/test_indexer_profile_evidence.py tests/test_index_fusion.py tests/test_collision_facts_fusion.py tests/test_reference_fusion_integration.py tests/test_test_context_discovery_map_0j7.py tests/test_mcp_child_process_cleanup.py tests/test_full_analysis_coordination.py tests/test_runtime_trace.py tests/analysis/test_cache_manager_content_hash.py
TARGETED_TEST_RESULT=85 passed, 1 dependency deprecation warning in 45.86s
TARGETED_TEST_EXECUTIONS=2
TARGETED_TEST_EXECUTION_NOTE=First invocation did not surface its exit summary through the tool session; one exact rerun captured the passing result above.
FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
PROFILE_RUN_COUNT=0
PROCESS_COUNT_EXPERIMENT_RUN=NO
GIT_DIFF_CHECK=PASS

## CONTEXTOR_LIVE
PRE_EDIT_LIVE_REVISION=1406
LATEST_OBSERVED_CANONICAL_REVISION=1409
LIVE_EVENT_CONTINUITY=continuous
LIVE_RESYNC_REQUIRED=NO
DESKTOP_WATCHER_PUBLICATION=PARTIAL
INDEXER_DESKTOP_WATCHER_EVENT=NOT_OBSERVED_WITHIN_BOUNDED_POLLS
RUNTIME_TRACE_WORKSPACE_SYNC=verified
TEST_INDEXER_PROFILE_EVIDENCE_WORKSPACE_SYNC=verified
TEST_RUNTIME_TRACE_WORKSPACE_SYNC=verified
INDEXER_WORKSPACE_SYNC=out_of_sync
WORKSPACE_SYNC=partial; indexer=out_of_sync; other_three=verified
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0
DIAGNOSTIC_FAMILIES=FRESH_AT_CANONICAL_REVISION_1409
NO_UPDATE_FILE=YES
LIVE_POLLING_LIMIT=FOUR_POLLS_PER_EDIT_BATCH_REACHED

## CONSUMER_VERIFICATION
POST_EDIT_CONTEXTOR_CONSUMER_VERIFICATION=BLOCKED_BY_INDEXER_WORKSPACE_SYNC
POST_EDIT_MANAGED_REUSABLE_DIRECT_CONSUMERS=tests.test_process_pool_lifecycle only
INDEXER_DIRECT_CONSUMER_IN_CONTEXTOR=NOT_OBSERVED
POST_EDIT_MANAGED_PROCESS_POOL_DIRECT_CONSUMERS=contextor.core.reporting_layer.artifact_usage_report; contextor.core.symbol_engine.indexer; tests.test_process_pool_lifecycle
LEGACY_CONSUMER_PROJECTION_LIMITATION=Indexer source remains out_of_sync at canonical revision 1409; these are not current post-edit consumers.
ARTIFACT_USAGE_REPORT_WORKSPACE_SYNC=verified
ARTIFACT_USAGE_REPORT_CHANGED=NO

## RESTART
MCP_SERVER_RESTART_REQUIRED_BEFORE_M7C=YES
DESKTOP_LIVE_RESTART_REQUIRED_BEFORE_M7C=YES
MCP_SERVER_RESTART_PERFORMED=NO
DESKTOP_LIVE_RESTART_PERFORMED=NO

## PROCESS_COUNT
PROCESS_COUNT_EXPERIMENT_RUN=NO
M7C_PROCESS_COUNT_CERTIFICATION=NOT_RUN

## CHANGE_CONTROL
FILES_CHANGED=contextor/core/symbol_engine/indexer.py; contextor/core/runtime_trace.py; tests/test_indexer_profile_evidence.py; tests/test_runtime_trace.py
REPORT_FILE=walkthrough.md
ACTUAL_DIFF=COMPLETE_FULL_DIFFS_INCLUDED
FIX_DESIGNED_BY_AGENT=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO
GIT_MUTATION_PERFORMED=NO
FORBIDDEN_FILES_CHANGED=NO

## COMPLETE_FULL_DIFFS
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 7a038c6..759555d 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1571 +1571 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
-            "worker_first_start_count": "worker processes for which the actual first executed task start was observed",
+            "worker_first_start_count": "worker processes for which the first task of the current index_repository batch was observed",
@@ -1578,3 +1578,3 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
-            "worker_first_start_delay_min_ms": "minimum per-worker first-task submit-to-entry delay",
-            "worker_first_start_delay_max_ms": "maximum per-worker first-task submit-to-entry delay",
-            "worker_first_start_delay_mean_ms": "mean per-worker first-task submit-to-entry delay",
+            "worker_first_start_delay_min_ms": "minimum per-worker current-batch first-task submit-to-entry delay",
+            "worker_first_start_delay_max_ms": "maximum per-worker current-batch first-task submit-to-entry delay",
+            "worker_first_start_delay_mean_ms": "mean per-worker current-batch first-task submit-to-entry delay",
@@ -1585,0 +1586,2 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
+            "process_pool_reused": "whether this index_repository process-pool lease reused an existing process-local reusable generation",
+            "process_pool_generation": "process-local reusable indexer pool generation identifier; zero for non-reusable or inline execution",
@@ -1588 +1590 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
-            "executor_process_count_before_shutdown": "executor process count observed after all results and before context shutdown",
+            "executor_process_count_before_shutdown": "executor process count observed after all results and before pool context exit; field name retained for compatibility and reusable normal exit does not shut workers down",
@@ -1635 +1637 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
-            "pool_shutdown_ms": "managed process-pool context shutdown milliseconds",
+            "pool_shutdown_ms": "managed process-pool context-exit milliseconds; legacy pool exit includes shutdown while successful reusable-pool exit preserves workers",
@@ -1860,0 +1863,2 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
+                "process_pool_reused": "process_pool_reused",
+                "process_pool_generation": "process_pool_generation",
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index cd0a4ad..2bd8a2e 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -18 +18 @@ import time
-from concurrent.futures import ProcessPoolExecutor, as_completed
+from concurrent.futures import as_completed
@@ -23,2 +23 @@ from contextor.core.analysis.process_pool_lifecycle import (
-    managed_process_pool,
-    terminate_process_pool,
+    managed_reusable_process_pool,
@@ -306 +305 @@ _CACHE_MANAGERS: dict[str, CacheManager] = {}
-_WORKER_TASK_ORDINAL_BY_PID: dict[int, int] = {}
+_WORKER_LAST_BATCH_TOKEN_BY_PID: dict[int, str] = {}
@@ -322,0 +322 @@ def _process_single_file(
+    batch_token: str | None = None,
@@ -333,4 +333,3 @@ def _process_single_file(
-    worker_task_ordinal = (
-        _WORKER_TASK_ORDINAL_BY_PID.get(
-            worker_pid,
-            0,
+    previous_batch_token = (
+        _WORKER_LAST_BATCH_TOKEN_BY_PID.get(
+            worker_pid
@@ -338 +336,0 @@ def _process_single_file(
-        + 1
@@ -341,4 +338,0 @@ def _process_single_file(
-    _WORKER_TASK_ORDINAL_BY_PID[
-        worker_pid
-    ] = worker_task_ordinal
-
@@ -346 +340,2 @@ def _process_single_file(
-        worker_task_ordinal == 1
+        batch_token is not None
+        and previous_batch_token != batch_token
@@ -348,0 +344,5 @@ def _process_single_file(
+    if batch_token is not None:
+        _WORKER_LAST_BATCH_TOKEN_BY_PID[
+            worker_pid
+        ] = batch_token
+
@@ -1030,0 +1031,3 @@ def index_repository(
+    process_pool_reused = False
+    process_pool_generation = 0
+
@@ -1625,0 +1629,6 @@ def index_repository(
+            process_pool_reused=(
+                process_pool_reused
+            ),
+            process_pool_generation=(
+                process_pool_generation
+            ),
@@ -1729,3 +1738,7 @@ def index_repository(
-    with managed_process_pool(
-        ProcessPoolExecutor,
-    ) as executor:
+    with managed_reusable_process_pool(
+        "indexer",
+    ) as (
+        executor,
+        process_pool_reused,
+        process_pool_generation,
+    ):
@@ -1747,0 +1761,4 @@ def index_repository(
+        worker_batch_token = (
+            f"{os.getpid()}:{time.monotonic_ns()}"
+        )
+
@@ -1753,0 +1771 @@ def index_repository(
+                worker_batch_token,
@@ -1899 +1916,0 @@ def index_repository(
-                terminate_process_pool(executor)
diff --git a/tests/test_indexer_profile_evidence.py b/tests/test_indexer_profile_evidence.py
index 5e2dd48..9122f6d 100644
--- a/tests/test_indexer_profile_evidence.py
+++ b/tests/test_indexer_profile_evidence.py
@@ -0,0 +1,3 @@
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
@@ -239,0 +243,9 @@ def test_process_pool_parent_timing_evidence_is_explicit(
+    assert isinstance(
+        event["process_pool_reused"],
+        bool,
+    )
+
+    assert (
+        event["process_pool_generation"]
+        >= 1
+    )
@@ -328,0 +341,144 @@ def test_process_pool_parent_timing_evidence_is_explicit(
+
+
+def test_index_repository_reuses_pool_and_resets_first_task_per_batch(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv(
+        "CONTEXTOR_STATE_DIR",
+        str(
+            tmp_path
+            / "state"
+        ),
+    )
+
+    monkeypatch.delenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL",
+        raising=False,
+    )
+
+    repo = _write_two_file_repo(
+        tmp_path
+    )
+
+    terminate_active_process_pools(
+        timeout=2.0,
+    )
+
+    try:
+        with capture_trace_events() as first_events:
+            index_repository(
+                str(repo)
+            )
+
+        with capture_trace_events() as second_events:
+            index_repository(
+                str(repo)
+            )
+
+        first_parent = [
+            event
+            for event in first_events
+            if event["ev"]
+            == "FULL_ANALYSIS_INDEX_PARENT_TIMING"
+        ]
+
+        second_parent = [
+            event
+            for event in second_events
+            if event["ev"]
+            == "FULL_ANALYSIS_INDEX_PARENT_TIMING"
+        ]
+
+        assert len(first_parent) == 1
+        assert len(second_parent) == 1
+
+        first_parent_event = first_parent[0]
+        second_parent_event = second_parent[0]
+
+        assert (
+            first_parent_event[
+                "process_pool_reused"
+            ]
+            is False
+        )
+
+        assert (
+            second_parent_event[
+                "process_pool_reused"
+            ]
+            is True
+        )
+
+        assert (
+            first_parent_event[
+                "process_pool_generation"
+            ]
+            >= 1
+        )
+
+        assert (
+            second_parent_event[
+                "process_pool_generation"
+            ]
+            == first_parent_event[
+                "process_pool_generation"
+            ]
+        )
+
+        first_worker = [
+            event
+            for event in first_events
+            if event["ev"]
+            == "FULL_ANALYSIS_INDEX_WORKER_TIMING"
+        ]
+
+        second_worker = [
+            event
+            for event in second_events
+            if event["ev"]
+            == "FULL_ANALYSIS_INDEX_WORKER_TIMING"
+        ]
+
+        assert len(first_worker) == 1
+        assert len(second_worker) == 1
+
+        first_worker_event = first_worker[0]
+        second_worker_event = second_worker[0]
+
+        assert (
+            first_worker_event[
+                "worker_process_count"
+            ]
+            >= 1
+        )
+
+        assert (
+            second_worker_event[
+                "worker_process_count"
+            ]
+            >= 1
+        )
+
+        assert (
+            first_worker_event[
+                "worker_first_start_count"
+            ]
+            == first_worker_event[
+                "worker_process_count"
+            ]
+        )
+
+        assert (
+            second_worker_event[
+                "worker_first_start_count"
+            ]
+            == second_worker_event[
+                "worker_process_count"
+            ]
+        )
+
+    finally:
+        terminate_active_process_pools(
+            timeout=2.0,
+        )
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 782ab1e..a5b4940 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -96,0 +97,2 @@ def test_canonical_writer_analysis_trace_is_self_describing_and_durable():
+        "process_pool_reused",
+        "process_pool_generation",
