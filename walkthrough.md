# CPA10M6A1_TRUE_FIRST_WORKER_TASK_TELEMETRY

STATUS=FINAL_PASS
PRE_EDIT_GATE=PASS
SOURCE_DRIFT=NO
PRE_EDIT_CONTEXTOR_REVISION=1398
BASE_HEAD=f802f6e87fdad80fdb4c33a3768ae62dd325707f

FIRST_TASK_SEMANTICS=ACTUAL_FIRST_PROCESS_LOCAL_TASK
MINIMUM_DELAY_PROXY_REMOVED=YES
WORKER_FIRST_START_COUNT_RECORDED=YES

PROCESS_POOL_BEHAVIOR_CHANGED=NO
PROCESS_POOL_MAX_WORKERS_CHANGED=NO
TASK_ORDERING_CHANGED=NO
CACHE_BEHAVIOR_CHANGED=NO
INDEX_RESULT_CHANGED=NO

PY_COMPILE=PASS
FIRST_TEST_GATE=PASS
FIRST_TEST_GATE_RESULT=4 passed in 2.01s
TARGETED_TESTS=PASS
TARGETED_TEST_RESULT=32 passed in 6.48s
FULL_SUITE_RUN=NO

ANALYZE_PROJECT_RUN_COUNT=0
PROFILE_RUN_COUNT=0

WORKSPACE_SYNC=verified
WORKSPACE_SYNC_REVISION=1402
NAME_COLLISIONS=0
SYNTAX_ERRORS=0
CYCLES=0

MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED_BEFORE_M6B=YES
FIX_DESIGNED_BY_AGENT=NO

GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO

FILES_CHANGED:
- contextor/core/symbol_engine/indexer.py
- contextor/core/runtime_trace.py
- tests/test_indexer_profile_evidence.py
- tests/test_runtime_trace.py

REPORT_FILE=C:\Temp\Contextor_Repo\walkthrough.md
GIT_DIFF_SCOPE=complete working-tree diff against BASE_HEAD for all four task-modified source/test files; includes pre-existing M6A changes because they were already uncommitted at this checkpoint

## DIRECT_EVIDENCE

- Contextor `get_file_edit_context` verified all four files at revision 1398 before editing; `workspace_sync=verified` and syntax diagnostics were fresh with zero errors.
- The M6A pre-edit anchors were present: process-pool worker delay map, minimum-delay comparison, `worker_pid=os.getpid()` result field, and all exact insertion/replacement anchors.
- Desktop watcher emitted `UPDATED` events for the four changed files at revisions 1399–1402. `get_live_events(after_revision=1398)` reported continuous event history and `resync_required=false`.
- Post-publication Contextor contexts verified all four files at revision 1402 with `workspace_sync=verified`; fresh syntax diagnostics, name collisions, and cycles each reported zero.
- `py_compile` completed with exit code 0. The required first test gate passed 4 tests; the targeted regression set passed 32 tests.

## CODE_PATH_PROVED

- `_process_single_file` increments `_WORKER_TASK_ORDINAL_BY_PID` at worker entry, records `worker_is_first_task` in returned timing evidence, and returns the existing worker PID.
- `record_file_task_evidence` stores the start delay only for a result whose `worker_is_first_task` is exactly `True`; the minimum-delay proxy comparison was removed.
- `emit_worker_timing_evidence` emits `worker_first_start_count` from the number of worker PIDs with observed first tasks. The trace schema header and key map include this field.
- The process-pool test asserts `worker_first_start_count == worker_process_count`; the trace contract test requires the field in the persisted trace schema.

## CONTRACT_PROVED

The only production additions are diagnostic ordinal/timing evidence and its trace field. The existing executor construction, max-worker setting, task submission/ordering, cache operations, and indexing result path were not changed in the complete diff. The requested focused tests pass.

## INFERENCE

The PID-keyed ordinal distinguishes the first `_process_single_file` entry in each process from whichever returned task happens to have the smallest submit-to-entry delay. The task-local flag is carried with that task's result to the parent aggregation.

## UNKNOWN

None for the requested first-task telemetry contract. No full-suite result is claimed.

## ACTIONS

- Applied only the exact process-local task ordinal, telemetry field, aggregation condition/count, trace schema mapping, and corresponding test assertions.
- Did not call `update_file`; natural Desktop LIVE watcher publication supplied the fresh Contextor revision.
- Did not restart MCP/Desktop, run full pytest, run full analysis, or run profiler.

## NEXT_STEP

Stop at the M6A1 checkpoint. Desktop LIVE restart remains required before M6B, as requested.

## ACTUAL_DIFF / COMPLETE FULL_DIFF
``diff
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 56e1ef2b77fd4c9761bde4f91bf12282dd1b8782..7a038c6a0ff5ca2f58fae05c6afda563cce22fbd 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1567,6 +1567,26 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
             "worker_task_max_ms": "maximum single worker task wall milliseconds",
             "worker_task_top10": "bounded slowest worker task path/time summary",
 
+            "worker_process_count": "distinct process-pool worker PIDs observed in returned file tasks",
+            "worker_first_start_count": "worker processes for which the actual first executed task start was observed",
+            "worker_tasks_per_process": "bounded worker PID to completed-task-count summary",
+
+            "worker_start_delay_sum_ms": "aggregate submit-to-worker-entry milliseconds; overlaps across tasks and is not critical-path additive",
+            "worker_start_delay_max_ms": "maximum submit-to-worker-entry milliseconds",
+            "worker_start_delay_top10": "bounded slowest submit-to-worker-entry path/time summary",
+
+            "worker_first_start_delay_min_ms": "minimum per-worker first-task submit-to-entry delay",
+            "worker_first_start_delay_max_ms": "maximum per-worker first-task submit-to-entry delay",
+            "worker_first_start_delay_mean_ms": "mean per-worker first-task submit-to-entry delay",
+
+            "worker_result_transport_sum_ms": "aggregate worker-result-ready to parent-received milliseconds; overlaps and is not critical-path additive",
+            "worker_result_transport_max_ms": "maximum worker-result-ready to parent-received milliseconds",
+            "worker_result_transport_top10": "bounded slowest worker-result transport path/time summary",
+
+            "executor_max_workers": "ProcessPoolExecutor configured max worker count",
+            "executor_process_count_after_submit": "executor process count observed immediately after all submissions",
+            "executor_process_count_before_shutdown": "executor process count observed after all results and before context shutdown",
+
             "source_read_calls": "worker source-read call count",
             "source_read_sum_ms": "aggregate worker source-read milliseconds; not critical-path additive",
 
@@ -1822,6 +1842,26 @@ def trace_event(domain: str, event: str, *, op: str | None = None, rev: int | No
                 "worker_task_max_ms": "worker_task_max_ms",
                 "worker_task_top10": "worker_task_top10",
 
+                "worker_process_count": "worker_process_count",
+                "worker_first_start_count": "worker_first_start_count",
+                "worker_tasks_per_process": "worker_tasks_per_process",
+
+                "worker_start_delay_sum_ms": "worker_start_delay_sum_ms",
+                "worker_start_delay_max_ms": "worker_start_delay_max_ms",
+                "worker_start_delay_top10": "worker_start_delay_top10",
+
+                "worker_first_start_delay_min_ms": "worker_first_start_delay_min_ms",
+                "worker_first_start_delay_max_ms": "worker_first_start_delay_max_ms",
+                "worker_first_start_delay_mean_ms": "worker_first_start_delay_mean_ms",
+
+                "worker_result_transport_sum_ms": "worker_result_transport_sum_ms",
+                "worker_result_transport_max_ms": "worker_result_transport_max_ms",
+                "worker_result_transport_top10": "worker_result_transport_top10",
+
+                "executor_max_workers": "executor_max_workers",
+                "executor_process_count_after_submit": "executor_process_count_after_submit",
+                "executor_process_count_before_shutdown": "executor_process_count_before_shutdown",
+
                 "source_read_calls": "source_read_calls",
                 "source_read_sum_ms": "source_read_sum_ms",
 
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 106baf6a1e15823a0e8b6fdaf55050bd12a165cc..cd0a4adad969e107c7faf029dcbfe0e95e3c0c58 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -303,6 +303,8 @@ def extract_imports(file_path: Path) -> list[ImportRef]:
 # directory check for every source file in the repository.
 _CACHE_MANAGERS: dict[str, CacheManager] = {}
 
+_WORKER_TASK_ORDINAL_BY_PID: dict[int, int] = {}
+
 
 def _cache_manager(root_str: str) -> CacheManager:
     manager = _CACHE_MANAGERS.get(root_str)
@@ -314,7 +316,11 @@ def _cache_manager(root_str: str) -> CacheManager:
     return manager
 
 
-def _process_single_file(path_str: str, root_str: str) -> dict:
+def _process_single_file(
+    path_str: str,
+    root_str: str,
+    submitted_monotonic_ns: int | None = None,
+) -> dict:
     """Funkcja pomocnicza dla wieloprocesowości."""
     path = Path(path_str)
 
@@ -322,7 +328,41 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
     source_key = rel.as_posix()
     module_id = ".".join(rel.with_suffix("").parts)
 
-    task_started = time.monotonic()
+    worker_pid = os.getpid()
+
+    worker_task_ordinal = (
+        _WORKER_TASK_ORDINAL_BY_PID.get(
+            worker_pid,
+            0,
+        )
+        + 1
+    )
+
+    _WORKER_TASK_ORDINAL_BY_PID[
+        worker_pid
+    ] = worker_task_ordinal
+
+    worker_is_first_task = (
+        worker_task_ordinal == 1
+    )
+
+    worker_started_monotonic_ns = time.monotonic_ns()
+
+    task_started = (
+        worker_started_monotonic_ns
+        / 1_000_000_000.0
+    )
+
+    worker_start_delay_ms = (
+        max(
+            0,
+            worker_started_monotonic_ns
+            - submitted_monotonic_ns,
+        )
+        / 1_000_000.0
+        if submitted_monotonic_ns is not None
+        else 0.0
+    )
 
     source_read_called = False
     source_read_ms = 0.0
@@ -346,12 +386,26 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
     cache_set_ms = 0.0
 
     def timing_evidence() -> dict[str, object]:
+        worker_result_ready_monotonic_ns = (
+            time.monotonic_ns()
+        )
+
         return {
             "task_total_ms": (
-                time.monotonic()
-                - task_started
+                worker_result_ready_monotonic_ns
+                - worker_started_monotonic_ns
             )
-            * 1000.0,
+            / 1_000_000.0,
+            "worker_pid": worker_pid,
+            "worker_is_first_task": (
+                worker_is_first_task
+            ),
+            "worker_start_delay_ms": (
+                worker_start_delay_ms
+            ),
+            "worker_result_ready_monotonic_ns": (
+                worker_result_ready_monotonic_ns
+            ),
             "source_read_called": source_read_called,
             "source_read_ms": source_read_ms,
             "import_extract_called": import_extract_called,
@@ -922,6 +976,26 @@ def index_repository(
     worker_task_slowest: list[tuple[float, str]] = []
     cache_miss_slowest: list[tuple[float, str]] = []
 
+    worker_process_ids: set[int] = set()
+    worker_tasks_by_pid: dict[int, int] = {}
+
+    worker_start_delay_sum_ms = 0.0
+    worker_start_delay_max_ms = 0.0
+    worker_start_delay_slowest: list[
+        tuple[float, str]
+    ] = []
+
+    worker_first_start_delay_by_pid: dict[
+        int,
+        float,
+    ] = {}
+
+    worker_result_transport_sum_ms = 0.0
+    worker_result_transport_max_ms = 0.0
+    worker_result_transport_slowest: list[
+        tuple[float, str]
+    ] = []
+
     source_read_calls = 0
     source_read_sum_ms = 0.0
 
@@ -954,6 +1028,10 @@ def index_repository(
     parent_progress_ms = 0.0
     pool_shutdown_ms = 0.0
 
+    executor_max_workers = 0
+    executor_process_count_after_submit = 0
+    executor_process_count_before_shutdown = 0
+
     collision_facts_by_module: dict[str, list[dict]] = {}
     test_facts_by_path: dict[str, dict] = {}
     automatic_test_dir_entries: dict[Path, set[str]] = {root_path: set()}
@@ -971,7 +1049,11 @@ def index_repository(
             for directory in sorted(automatic_test_dir_entries)
         }
 
-    def record_file_task_evidence(result: dict) -> None:
+    def record_file_task_evidence(
+        result: dict,
+        *,
+        parent_result_received_monotonic_ns: int | None = None,
+    ) -> None:
         nonlocal file_tasks
         nonlocal source_parse_calls
         nonlocal source_parse_failures
@@ -984,6 +1066,11 @@ def index_repository(
         nonlocal lineage_extract_sum_ms
 
         nonlocal worker_task_sum_ms
+        nonlocal worker_start_delay_sum_ms
+        nonlocal worker_start_delay_max_ms
+        nonlocal worker_result_transport_sum_ms
+        nonlocal worker_result_transport_max_ms
+
         nonlocal source_read_calls
         nonlocal source_read_sum_ms
         nonlocal import_extract_calls
@@ -1015,6 +1102,103 @@ def index_repository(
             )
         )
 
+        worker_start_delay_ms = float(
+            result.get(
+                "worker_start_delay_ms",
+                0.0,
+            )
+        )
+
+        worker_start_delay_sum_ms += (
+            worker_start_delay_ms
+        )
+
+        worker_start_delay_max_ms = max(
+            worker_start_delay_max_ms,
+            worker_start_delay_ms,
+        )
+
+        worker_start_delay_slowest.append(
+            (
+                worker_start_delay_ms,
+                result["path"],
+            )
+        )
+
+        if (
+            parent_result_received_monotonic_ns
+            is not None
+        ):
+            worker_pid = int(
+                result.get(
+                    "worker_pid",
+                    0,
+                )
+            )
+
+            if worker_pid > 0:
+                worker_process_ids.add(
+                    worker_pid
+                )
+
+                worker_tasks_by_pid[
+                    worker_pid
+                ] = (
+                    worker_tasks_by_pid.get(
+                        worker_pid,
+                        0,
+                    )
+                    + 1
+                )
+
+                if (
+                    result.get(
+                        "worker_is_first_task"
+                    )
+                    is True
+                ):
+                    worker_first_start_delay_by_pid[
+                        worker_pid
+                    ] = worker_start_delay_ms
+
+            result_ready_ns = result.get(
+                "worker_result_ready_monotonic_ns"
+            )
+
+            if (
+                isinstance(
+                    result_ready_ns,
+                    int,
+                )
+                and result_ready_ns > 0
+            ):
+                worker_result_transport_ms = (
+                    max(
+                        0,
+                        (
+                            parent_result_received_monotonic_ns
+                            - result_ready_ns
+                        ),
+                    )
+                    / 1_000_000.0
+                )
+
+                worker_result_transport_sum_ms += (
+                    worker_result_transport_ms
+                )
+
+                worker_result_transport_max_ms = max(
+                    worker_result_transport_max_ms,
+                    worker_result_transport_ms,
+                )
+
+                worker_result_transport_slowest.append(
+                    (
+                        worker_result_transport_ms,
+                        result["path"],
+                    )
+                )
+
         elapsed_ms = float(
             result.get(
                 "lineage_extract_ms",
@@ -1294,6 +1478,54 @@ def index_repository(
             for _elapsed_ms, detail in slowest_misses
         )
 
+        first_start_delays = list(
+            worker_first_start_delay_by_pid.values()
+        )
+
+        worker_first_start_delay_min_ms = (
+            min(first_start_delays)
+            if first_start_delays
+            else 0.0
+        )
+
+        worker_first_start_delay_max_ms = (
+            max(first_start_delays)
+            if first_start_delays
+            else 0.0
+        )
+
+        worker_first_start_delay_mean_ms = (
+            sum(first_start_delays)
+            / len(first_start_delays)
+            if first_start_delays
+            else 0.0
+        )
+
+        worker_start_delay_top10 = ",".join(
+            f"{path}:{elapsed_ms:.3f}"
+            for elapsed_ms, path
+            in sorted(
+                worker_start_delay_slowest,
+                reverse=True,
+            )[:10]
+        )
+
+        worker_result_transport_top10 = ",".join(
+            f"{path}:{elapsed_ms:.3f}"
+            for elapsed_ms, path
+            in sorted(
+                worker_result_transport_slowest,
+                reverse=True,
+            )[:10]
+        )
+
+        worker_tasks_per_process = ",".join(
+            f"{pid}:{worker_tasks_by_pid[pid]}"
+            for pid in sorted(
+                worker_tasks_by_pid
+            )
+        )
+
         trace_event(
             "ANALYSIS",
             "FULL_ANALYSIS_INDEX_WORKER_TIMING",
@@ -1306,6 +1538,42 @@ def index_repository(
             worker_task_sum_ms=worker_task_sum_ms,
             worker_task_max_ms=worker_task_max_ms,
             worker_task_top10=worker_task_top10,
+            worker_process_count=len(
+                worker_process_ids
+            ),
+            worker_first_start_count=len(
+                worker_first_start_delay_by_pid
+            ),
+            worker_tasks_per_process=(
+                worker_tasks_per_process
+            ),
+            worker_start_delay_sum_ms=(
+                worker_start_delay_sum_ms
+            ),
+            worker_start_delay_max_ms=(
+                worker_start_delay_max_ms
+            ),
+            worker_start_delay_top10=(
+                worker_start_delay_top10
+            ),
+            worker_first_start_delay_min_ms=(
+                worker_first_start_delay_min_ms
+            ),
+            worker_first_start_delay_max_ms=(
+                worker_first_start_delay_max_ms
+            ),
+            worker_first_start_delay_mean_ms=(
+                worker_first_start_delay_mean_ms
+            ),
+            worker_result_transport_sum_ms=(
+                worker_result_transport_sum_ms
+            ),
+            worker_result_transport_max_ms=(
+                worker_result_transport_max_ms
+            ),
+            worker_result_transport_top10=(
+                worker_result_transport_top10
+            ),
             source_read_calls=source_read_calls,
             source_read_sum_ms=source_read_sum_ms,
             import_extract_calls=import_extract_calls,
@@ -1355,6 +1623,15 @@ def index_repository(
             parent_merge_ms=parent_merge_ms,
             parent_progress_ms=parent_progress_ms,
             pool_shutdown_ms=pool_shutdown_ms,
+            executor_max_workers=(
+                executor_max_workers
+            ),
+            executor_process_count_after_submit=(
+                executor_process_count_after_submit
+            ),
+            executor_process_count_before_shutdown=(
+                executor_process_count_before_shutdown
+            ),
         )
 
     ignored_dirs = set(DEFAULT_IGNORED_DIRS)
@@ -1452,6 +1729,15 @@ def index_repository(
     with managed_process_pool(
         ProcessPoolExecutor,
     ) as executor:
+        executor_max_workers = int(
+            getattr(
+                executor,
+                "_max_workers",
+                0,
+            )
+            or 0
+        )
+
         pool_enter_ms = (
             time.monotonic()
             - pool_enter_started
@@ -1464,6 +1750,7 @@ def index_repository(
                 _process_single_file,
                 str(p),
                 str(root_path),
+                time.monotonic_ns(),
             ): p
             for p in files_to_process
         }
@@ -1473,6 +1760,21 @@ def index_repository(
             - pool_submit_started
         ) * 1000.0
 
+        raw_processes_after_submit = getattr(
+            executor,
+            "_processes",
+            None,
+        )
+
+        executor_process_count_after_submit = (
+            len(raw_processes_after_submit)
+            if isinstance(
+                raw_processes_after_submit,
+                dict,
+            )
+            else 0
+        )
+
         wait_started = time.monotonic()
 
         for future in as_completed(futures):
@@ -1483,6 +1785,9 @@ def index_repository(
 
             future_result_started = time.monotonic()
             res = future.result()
+            parent_result_received_monotonic_ns = (
+                time.monotonic_ns()
+            )
             parent_future_result_ms += (
                 time.monotonic()
                 - future_result_started
@@ -1490,7 +1795,12 @@ def index_repository(
 
             parent_merge_started = time.monotonic()
 
-            record_file_task_evidence(res)
+            record_file_task_evidence(
+                res,
+                parent_result_received_monotonic_ns=(
+                    parent_result_received_monotonic_ns
+                ),
+            )
 
             if res["error"]:
                 line_number, column_number = (
@@ -1596,6 +1906,21 @@ def index_repository(
 
             wait_started = time.monotonic()
 
+        raw_processes_before_shutdown = getattr(
+            executor,
+            "_processes",
+            None,
+        )
+
+        executor_process_count_before_shutdown = (
+            len(raw_processes_before_shutdown)
+            if isinstance(
+                raw_processes_before_shutdown,
+                dict,
+            )
+            else 0
+        )
+
         pool_body_end = time.monotonic()
 
     pool_scope_end = time.monotonic()
diff --git a/tests/test_indexer_profile_evidence.py b/tests/test_indexer_profile_evidence.py
index acdc781a1a5395d4d6c3b785bd8d04308ad9aa65..5e2dd48a5c7583ac3d24df3c277b162e0b593174 100644
--- a/tests/test_indexer_profile_evidence.py
+++ b/tests/test_indexer_profile_evidence.py
@@ -238,6 +238,85 @@ def test_process_pool_parent_timing_evidence_is_explicit(
     assert event["parent_progress_ms"] >= 0.0
     assert event["pool_shutdown_ms"] >= 0.0
 
+    assert event["executor_max_workers"] >= 1
+
+    assert (
+        event["executor_process_count_after_submit"]
+        >= 1
+    )
+
+    assert (
+        event[
+            "executor_process_count_before_shutdown"
+        ]
+        >= 1
+    )
+
+    worker_events = [
+        item
+        for item in events
+        if item["ev"]
+        == "FULL_ANALYSIS_INDEX_WORKER_TIMING"
+    ]
+
+    assert len(worker_events) == 1
+
+    worker_event = worker_events[0]
+
+    assert worker_event["execution_mode"] == "process_pool"
+
+    assert worker_event["worker_process_count"] >= 1
+    assert (
+        worker_event["worker_first_start_count"]
+        == worker_event["worker_process_count"]
+    )
+
+    assert (
+        worker_event["worker_process_count"]
+        <= event["executor_max_workers"]
+    )
+
+    assert worker_event["worker_tasks_per_process"]
+
+    assert worker_event["worker_start_delay_sum_ms"] >= 0.0
+    assert worker_event["worker_start_delay_max_ms"] >= 0.0
+
+    assert (
+        worker_event["worker_first_start_delay_min_ms"]
+        >= 0.0
+    )
+
+    assert (
+        worker_event["worker_first_start_delay_max_ms"]
+        >= worker_event[
+            "worker_first_start_delay_min_ms"
+        ]
+    )
+
+    assert (
+        worker_event["worker_first_start_delay_mean_ms"]
+        >= worker_event[
+            "worker_first_start_delay_min_ms"
+        ]
+    )
+
+    assert (
+        worker_event["worker_first_start_delay_mean_ms"]
+        <= worker_event[
+            "worker_first_start_delay_max_ms"
+        ]
+    )
+
+    assert (
+        worker_event["worker_result_transport_sum_ms"]
+        >= 0.0
+    )
+
+    assert (
+        worker_event["worker_result_transport_max_ms"]
+        >= 0.0
+    )
+
     assert (
         event["pool_scope_ms"]
         >= event["pool_enter_ms"]
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 963d85270e9f6566adf86c99359ae28df2277d10..782ab1e3f635275463277dc415d3ea84d89a0ae8 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -82,6 +82,21 @@ def test_canonical_writer_analysis_trace_is_self_describing_and_durable():
         "lineage_extract_sum_ms",
 
         "worker_task_sum_ms", "worker_task_max_ms", "worker_task_top10",
+        "worker_process_count",
+        "worker_first_start_count",
+        "worker_tasks_per_process",
+        "worker_start_delay_sum_ms",
+        "worker_start_delay_max_ms",
+        "worker_start_delay_top10",
+        "worker_first_start_delay_min_ms",
+        "worker_first_start_delay_max_ms",
+        "worker_first_start_delay_mean_ms",
+        "worker_result_transport_sum_ms",
+        "worker_result_transport_max_ms",
+        "worker_result_transport_top10",
+        "executor_max_workers",
+        "executor_process_count_after_submit",
+        "executor_process_count_before_shutdown",
         "source_read_calls", "source_read_sum_ms",
         "import_extract_calls", "import_extract_sum_ms",
         "symbol_extract_calls", "symbol_extract_sum_ms",
``
