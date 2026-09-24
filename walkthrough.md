# CPA10M4B1_TRACE_SCHEMA_AND_CACHE_MISS_TELEMETRY_FIX

STATUS=FINAL_PASS

## Scope and source state

FILES_CHANGED:
- `contextor/core/runtime_trace.py`
- `contextor/core/symbol_engine/indexer.py`
- `tests/test_runtime_trace.py`
- `tests/test_indexer_profile_evidence.py`

REPORT_FILE=C:\Temp\Contextor_Repo\walkthrough.md
BASELINE_HEAD=6e781ef735d42734df033009e3da4bf36ff8d650
M4B_WORKER_AND_PARENT_TELEMETRY_PRESENT_IN_BASELINE_HEAD=YES
M4B1_WORKING_TREE_DIFF_CONTAINS_ONLY_THIS_TASK=YES

The pre-edit gate found the M4B worker and parent timing events and their existing tests in the baseline. The baseline `runtime_trace.py` contained `TRACE_SCHEMA = "contextor-runtime-trace/v1"` and the required old whitelist sequence. The working tree was clean before M4B1 edits. Therefore the complete current working-tree diff is the M4B1 correction; the prior M4B implementation is already part of HEAD.

## Findings and evidence

DIRECT_EVIDENCE:
- `trace_event` uses an explicit key map; the M4B timing field names were absent from that map before this correction.
- The correction registers the specified timing fields in both the runtime trace header descriptions and `trace_event` key map, and registers all three event names in the ANALYSIS header.
- The per-cache-miss event follows `cache_miss_slowest.append(...)` inside the existing cache-miss branch. Its payload contains the exact task wall and nested subphase fields specified by the task.
- Desktop watcher published all four modified files at revisions 1387–1390. The event origin was `desktop_watcher`; no MCP `update_file` call was made.

CODE_PATH_PROVED:
- The cache-miss event is emitted only in the existing branch requiring `cache_get_called is True` and `cache_hit is not True`; complete hits and cached incomplete hits are excluded by that existing condition.

CONTRACT_PROVED:
- The added cold-miss assertions verify exactly two events for `a.py` and `b.py` and nonnegative values for each required timing field.
- The trace contract test checks every specified new field and the three new event names.

INFERENCE=NONE
UNKNOWN=NONE

## Required classifications

ROOT_CAUSE_TRACE_FIELD_WHITELIST=YES
WORKER_EVENT_FIELDS_REGISTERED=YES
PARENT_EVENT_FIELDS_REGISTERED=YES
CACHE_MISS_EVENT_FIELDS_REGISTERED=YES
TRACE_HEADER_FIELDS_REGISTERED=YES
TRACE_HEADER_EVENTS_REGISTERED=YES
PER_CACHE_MISS_EVENT_ADDED=YES

TELEMETRY_ONLY=YES
INDEXING_BEHAVIOR_CHANGED=NO
CACHE_BEHAVIOR_CHANGED=NO
PROCESS_POOL_BEHAVIOR_CHANGED=NO

## Validation

PY_COMPILE=PASS
PY_COMPILE_COMMAND=`.venv\Scripts\python.exe -m py_compile contextor\core\runtime_trace.py contextor\core\symbol_engine\indexer.py tests\test_runtime_trace.py tests\test_indexer_profile_evidence.py`

FIRST_TEST_GATE=PASS
FIRST_TEST_GATE_COMMAND=`.venv\Scripts\python.exe -m pytest -q tests/test_indexer_profile_evidence.py tests/test_runtime_trace.py::test_canonical_writer_analysis_trace_is_self_describing_and_durable`
FIRST_TEST_GATE_RESULT=`4 passed in 1.82s`

TARGETED_TESTS=PASS
TARGETED_TEST_COMMAND=`.venv\Scripts\python.exe -m pytest -q tests/test_index_fusion.py tests/test_indexer_profile_evidence.py tests/test_process_pool_lifecycle.py tests/test_runtime_trace.py tests/analysis/test_cache_manager_content_hash.py`
TARGETED_TEST_RESULT=`32 passed in 16.77s`

FULL_SUITE_RUN=NO
FULL_ANALYSIS_RUN_COUNT=0
PROFILE_RUN_COUNT=0

## Contextor LIVE verification

LIVE_PUBLICATION_REVISIONS=1387,1388,1389,1390
LIVE_PUBLICATION_ORIGIN=desktop_watcher
WORKSPACE_SYNC=verified
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0
CANONICAL_REVISION=1390
All four `get_file_edit_context` responses reported `workspace_sync=verified`, fresh canonical state, no warnings, fresh diagnostics, zero syntax errors, zero name collisions, and zero cycles.

## Restart and Git

MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED_BEFORE_M4C=YES
FIX_DESIGNED_BY_AGENT=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO

## ACTUAL_DIFF / FULL_DIFF

The following is the complete current working-tree diff for every file listed in `FILES_CHANGED`. M4B worker/parent code is already in `BASELINE_HEAD`; no M4B source/test working-tree changes remain to include separately.
```diff
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 4f8dafd..94bced1 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1562,6 +1562,58 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
             "source_parse_sum_ms": "aggregate per-file task milliseconds; not critical-path wall",
             "cache_get_sum_ms": "aggregate per-file task milliseconds; not critical-path wall",
             "lineage_extract_sum_ms": "aggregate per-file task milliseconds; not critical-path wall",
+
+            "worker_task_sum_ms": "aggregate worker task wall milliseconds; overlapping across processes and not critical-path additive",
+            "worker_task_max_ms": "maximum single worker task wall milliseconds",
+            "worker_task_top10": "bounded slowest worker task path/time summary",
+
+            "source_read_calls": "worker source-read call count",
+            "source_read_sum_ms": "aggregate worker source-read milliseconds; not critical-path additive",
+
+            "import_extract_calls": "worker import extraction call count",
+            "import_extract_sum_ms": "aggregate worker import extraction milliseconds; not critical-path additive",
+
+            "symbol_extract_calls": "worker symbol extraction call count",
+            "symbol_extract_sum_ms": "aggregate worker symbol extraction milliseconds; not critical-path additive",
+
+            "reference_extract_calls": "worker reference extraction call count",
+            "reference_extract_sum_ms": "aggregate worker reference extraction milliseconds; not critical-path additive",
+
+            "collision_extract_calls": "worker collision extraction call count",
+            "collision_extract_sum_ms": "aggregate worker collision extraction milliseconds; not critical-path additive",
+
+            "test_extract_calls": "worker test-fact extraction call count",
+            "test_extract_sum_ms": "aggregate worker test-fact extraction milliseconds; not critical-path additive",
+
+            "cache_set_calls": "worker cache-set call count",
+            "cache_set_sum_ms": "aggregate worker cache-set milliseconds; not critical-path additive",
+
+            "cache_miss_task_count": "worker cold cache-miss task count",
+            "cache_miss_top10": "bounded cold cache-miss timing summary",
+
+            "task_total_ms": "single worker task wall milliseconds",
+            "source_read_ms": "single worker task source-read milliseconds",
+            "cache_get_ms": "single worker task cache-get milliseconds",
+            "source_parse_ms": "single worker task source-parse milliseconds",
+            "lineage_extract_ms": "single worker task lineage-extraction milliseconds",
+            "import_extract_ms": "single worker task import-extraction milliseconds",
+            "symbol_extract_ms": "single worker task symbol-extraction milliseconds",
+            "reference_extract_ms": "single worker task reference-extraction milliseconds",
+            "collision_extract_ms": "single worker task collision-extraction milliseconds",
+            "test_extract_ms": "single worker task test-fact extraction milliseconds",
+            "cache_set_ms": "single worker task cache-set milliseconds",
+
+            "index_internal_ms": "index_repository internal wall milliseconds",
+            "file_discovery_ms": "repository Python-file discovery wall milliseconds",
+            "pool_scope_ms": "managed process-pool scope wall milliseconds",
+            "pool_enter_ms": "managed process-pool context entry milliseconds",
+            "pool_submit_ms": "process-pool task submission milliseconds",
+            "parent_future_wait_ms": "parent critical-path time waiting for as_completed yields",
+            "parent_future_result_ms": "parent future.result retrieval milliseconds",
+            "parent_merge_ms": "parent result merge milliseconds",
+            "parent_progress_ms": "parent progress checkpoint milliseconds",
+            "pool_shutdown_ms": "managed process-pool context shutdown milliseconds",
+
             "reuse_sources": "lineage sources reused without rematerialization",
             "reresolve_sources": "lineage sources reresolved against changed global resolution",
             "materialize_sources": "lineage sources fully materialized",
@@ -1579,6 +1631,9 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
     records[4]["events"]["ANALYSIS"].extend(
         [
             "FULL_ANALYSIS_INDEX_EVIDENCE",
+            "FULL_ANALYSIS_INDEX_WORKER_TIMING",
+            "FULL_ANALYSIS_INDEX_PARENT_TIMING",
+            "FULL_ANALYSIS_INDEX_CACHE_MISS_TIMING",
             "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
             "FULL_ANALYSIS_STAGE_COMPONENT_END",
             "FULL_ANALYSIS_STAGE_END",
@@ -1762,6 +1817,59 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
                 "source_parse_sum_ms": "source_parse_sum_ms",
                 "cache_get_sum_ms": "cache_get_sum_ms",
                 "lineage_extract_sum_ms": "lineage_extract_sum_ms",
+
+                "worker_task_sum_ms": "worker_task_sum_ms",
+                "worker_task_max_ms": "worker_task_max_ms",
+                "worker_task_top10": "worker_task_top10",
+
+                "source_read_calls": "source_read_calls",
+                "source_read_sum_ms": "source_read_sum_ms",
+
+                "import_extract_calls": "import_extract_calls",
+                "import_extract_sum_ms": "import_extract_sum_ms",
+
+                "symbol_extract_calls": "symbol_extract_calls",
+                "symbol_extract_sum_ms": "symbol_extract_sum_ms",
+
+                "reference_extract_calls": "reference_extract_calls",
+                "reference_extract_sum_ms": "reference_extract_sum_ms",
+
+                "collision_extract_calls": "collision_extract_calls",
+                "collision_extract_calls": "collision_extract_calls",
+                "collision_extract_sum_ms": "collision_extract_sum_ms",
+
+                "test_extract_calls": "test_extract_calls",
+                "test_extract_sum_ms": "test_extract_sum_ms",
+
+                "cache_set_calls": "cache_set_calls",
+                "cache_set_sum_ms": "cache_set_sum_ms",
+
+                "cache_miss_task_count": "cache_miss_task_count",
+                "cache_miss_top10": "cache_miss_top10",
+
+                "task_total_ms": "task_total_ms",
+                "source_read_ms": "source_read_ms",
+                "cache_get_ms": "cache_get_ms",
+                "source_parse_ms": "source_parse_ms",
+                "lineage_extract_ms": "lineage_extract_ms",
+                "import_extract_ms": "import_extract_ms",
+                "symbol_extract_ms": "symbol_extract_ms",
+                "reference_extract_ms": "reference_extract_ms",
+                "collision_extract_ms": "collision_extract_ms",
+                "test_extract_ms": "test_extract_ms",
+                "cache_set_ms": "cache_set_ms",
+
+                "index_internal_ms": "index_internal_ms",
+                "file_discovery_ms": "file_discovery_ms",
+                "pool_scope_ms": "pool_scope_ms",
+                "pool_enter_ms": "pool_enter_ms",
+                "pool_submit_ms": "pool_submit_ms",
+                "parent_future_wait_ms": "parent_future_wait_ms",
+                "parent_future_result_ms": "parent_future_result_ms",
+                "parent_merge_ms": "parent_merge_ms",
+                "parent_progress_ms": "parent_progress_ms",
+                "pool_shutdown_ms": "pool_shutdown_ms",
+
                 "reuse_sources": "reuse_sources",
                 "reresolve_sources": "reresolve_sources",
                 "materialize_sources": "materialize_sources",
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 42ac3b4..106baf6 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -1156,6 +1156,77 @@ def index_repository(
                 )
             )
 
+            trace_event(
+                "ANALYSIS",
+                "FULL_ANALYSIS_INDEX_CACHE_MISS_TIMING",
+                operation="indexing_cache_miss_timing",
+                timing_semantics=(
+                    "single_file_task_wall_and_nested_subphases"
+                ),
+                path=result["path"],
+                task_total_ms=task_total_ms,
+                source_read_ms=float(
+                    result.get(
+                        "source_read_ms",
+                        0.0,
+                    )
+                ),
+                cache_get_ms=float(
+                    result.get(
+                        "cache_get_ms",
+                        0.0,
+                    )
+                ),
+                source_parse_ms=float(
+                    result.get(
+                        "source_parse_ms",
+                        0.0,
+                    )
+                ),
+                lineage_extract_ms=float(
+                    result.get(
+                        "lineage_extract_ms",
+                        0.0,
+                    )
+                ),
+                import_extract_ms=float(
+                    result.get(
+                        "import_extract_ms",
+                        0.0,
+                    )
+                ),
+                symbol_extract_ms=float(
+                    result.get(
+                        "symbol_extract_ms",
+                        0.0,
+                    )
+                ),
+                reference_extract_ms=float(
+                    result.get(
+                        "reference_extract_ms",
+                        0.0,
+                    )
+                ),
+                collision_extract_ms=float(
+                    result.get(
+                        "collision_extract_ms",
+                        0.0,
+                    )
+                ),
+                test_extract_ms=float(
+                    result.get(
+                        "test_extract_ms",
+                        0.0,
+                    )
+                ),
+                cache_set_ms=float(
+                    result.get(
+                        "cache_set_ms",
+                        0.0,
+                    )
+                ),
+            )
+
     def emit_index_profile_evidence(execution_mode: str) -> None:
         trace_event(
             "ANALYSIS",
diff --git a/tests/test_indexer_profile_evidence.py b/tests/test_indexer_profile_evidence.py
index 911fc31..acdc781 100644
--- a/tests/test_indexer_profile_evidence.py
+++ b/tests/test_indexer_profile_evidence.py
@@ -143,6 +143,43 @@ def test_index_lineage_extraction_event_is_explicitly_noncritical(tmp_path, monk
         "cache_miss_top10"
     ]
 
+    miss_events = [
+        event
+        for event in events
+        if event["ev"]
+        == "FULL_ANALYSIS_INDEX_CACHE_MISS_TIMING"
+    ]
+
+    assert len(miss_events) == 2
+
+    assert {
+        event["path"]
+        for event in miss_events
+    } == {
+        "a.py",
+        "b.py",
+    }
+
+    for miss_event in miss_events:
+        assert (
+            miss_event["timing_semantics"]
+            == (
+                "single_file_task_wall_and_nested_subphases"
+            )
+        )
+
+        assert miss_event["task_total_ms"] >= 0.0
+        assert miss_event["source_read_ms"] >= 0.0
+        assert miss_event["cache_get_ms"] >= 0.0
+        assert miss_event["source_parse_ms"] >= 0.0
+        assert miss_event["lineage_extract_ms"] >= 0.0
+        assert miss_event["import_extract_ms"] >= 0.0
+        assert miss_event["symbol_extract_ms"] >= 0.0
+        assert miss_event["reference_extract_ms"] >= 0.0
+        assert miss_event["collision_extract_ms"] >= 0.0
+        assert miss_event["test_extract_ms"] >= 0.0
+        assert miss_event["cache_set_ms"] >= 0.0
+
 
 def test_process_pool_parent_timing_evidence_is_explicit(
     tmp_path,
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index ef224fc..963d852 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -79,7 +79,29 @@ def test_canonical_writer_analysis_trace_is_self_describing_and_durable():
         "file_tasks", "source_parse_calls", "source_parse_failures",
         "cache_get_calls", "cache_hits", "cache_misses", "lineage_cache_hits",
         "lineage_extract_calls", "source_parse_sum_ms", "cache_get_sum_ms",
-        "lineage_extract_sum_ms", "reuse_sources", "reresolve_sources",
+        "lineage_extract_sum_ms",
+
+        "worker_task_sum_ms", "worker_task_max_ms", "worker_task_top10",
+        "source_read_calls", "source_read_sum_ms",
+        "import_extract_calls", "import_extract_sum_ms",
+        "symbol_extract_calls", "symbol_extract_sum_ms",
+        "reference_extract_calls", "reference_extract_sum_ms",
+        "collision_extract_calls", "collision_extract_sum_ms",
+        "test_extract_calls", "test_extract_sum_ms",
+        "cache_set_calls", "cache_set_sum_ms",
+        "cache_miss_task_count", "cache_miss_top10",
+
+        "task_total_ms", "source_read_ms", "cache_get_ms",
+        "source_parse_ms", "lineage_extract_ms", "import_extract_ms",
+        "symbol_extract_ms", "reference_extract_ms",
+        "collision_extract_ms", "test_extract_ms", "cache_set_ms",
+
+        "index_internal_ms", "file_discovery_ms", "pool_scope_ms",
+        "pool_enter_ms", "pool_submit_ms", "parent_future_wait_ms",
+        "parent_future_result_ms", "parent_merge_ms",
+        "parent_progress_ms", "pool_shutdown_ms",
+
+        "reuse_sources", "reresolve_sources",
         "materialize_sources", "reresolve_fallback_sources",
         "reuse_gate_ms", "reresolve_calls_ms", "materialize_calls_ms",
         "lineage_sources", "lineage_anchors", "lineage_flows",
@@ -87,6 +109,9 @@ def test_canonical_writer_analysis_trace_is_self_describing_and_durable():
     } <= set(records[1]["fields"])
     assert {
         "FULL_ANALYSIS_INDEX_EVIDENCE",
+        "FULL_ANALYSIS_INDEX_WORKER_TIMING",
+        "FULL_ANALYSIS_INDEX_PARENT_TIMING",
+        "FULL_ANALYSIS_INDEX_CACHE_MISS_TIMING",
         "FULL_ANALYSIS_LINEAGE_MATERIALIZATION",
         "FULL_ANALYSIS_STAGE_COMPONENT_END",
         "FULL_ANALYSIS_STAGE_END",
```

