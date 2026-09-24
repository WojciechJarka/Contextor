# CPA10M4B_INDEXER_CRITICAL_PATH_TELEMETRY

STATUS=BLOCKED_TEST_FAILURE
TASK=CPA10M4B_INDEXER_CRITICAL_PATH_TELEMETRY
IMPLEMENTATION=APPLIED_LITERAL_SPEC
FIX_DESIGNED_BY_AGENT=NO

## TIMING CONTRACT

WORKER_TASK_TOTAL_TIMED=YES
SOURCE_READ_TIMED=YES
IMPORT_EXTRACTION_TIMED=YES
SYMBOL_EXTRACTION_TIMED=YES
REFERENCE_EXTRACTION_TIMED=YES
COLLISION_EXTRACTION_TIMED=YES
TEST_EXTRACTION_TIMED=YES
CACHE_SET_TIMED=YES

FILE_DISCOVERY_TIMED=YES
POOL_ENTER_TIMED=YES
POOL_SUBMIT_TIMED=YES
PARENT_FUTURE_WAIT_TIMED=YES
PARENT_FUTURE_RESULT_TIMED=YES
PARENT_MERGE_TIMED=YES
PARENT_PROGRESS_TIMED=YES
POOL_SHUTDOWN_TIMED=YES
POOL_SCOPE_TIMED=YES

EXISTING_INDEX_EVIDENCE_SCHEMA_CHANGED=NO
EXISTING_LINEAGE_EVIDENCE_SCHEMA_CHANGED=NO
NEW_EVENTS_ADDITIVE_ONLY=YES

## VALIDATION

PY_COMPILE=PASS
FIRST_TEST_GATE=FAIL
FIRST_TEST_GATE_COMMAND=.venv\Scripts\python.exe -m pytest -q tests/test_indexer_profile_evidence.py
FIRST_TEST_GATE_FAILURE_COUNT=3
FIRST_TEST_GATE_FAILURE_1=test_warm_index_cache_evidence_proves_ast_parse_is_skipped; KeyError: worker_task_sum_ms
FIRST_TEST_GATE_FAILURE_2=test_index_lineage_extraction_event_is_explicitly_noncritical; KeyError: source_read_calls
FIRST_TEST_GATE_FAILURE_3=test_process_pool_parent_timing_evidence_is_explicit; KeyError: index_internal_ms
TARGETED_TESTS=NOT_RUN_AFTER_FIRST_TEST_GATE_FAILURE
FULL_SUITE_RUN=NO
STOP_RULE=First test gate failed; stopped without independent repair or further tests.

## RUN_CONTROL

FULL_ANALYSIS_RUN_COUNT=0
PROFILE_RUN_COUNT=0
WORKSPACE_SYNC=verified (pre-edit, both allowed files); post-edit=not_checked after first-test-gate stop
NAME_COLLISIONS=0 (pre-edit canonical state; post-edit=not_refreshed)
SYNTAX_ERRORS=0 (pre-edit canonical state; post-edit=not_refreshed)
CYCLES=0 (pre-edit canonical state; post-edit=not_refreshed)
PRODUCTION_CODE_CHANGED=YES
TEST_CODE_CHANGED=YES
MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED=NO
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO
GIT_MUTATION=NO
GIT_HEAD=2dd1c4bccb88c57cbf1659aa86327c05d7fa9173
PRE_EDIT_SOURCE_GATE=PASS
ALLOWED_SOURCE_HASHES_MATCHED_DESIGN_BLOBS=YES
FILES_CHANGED=
C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py
C:\Temp\Contextor_Repo\tests\test_indexer_profile_evidence.py

FULL_DIFFS_BEGIN
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 5ff9f4e..42ac3b4 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -322,10 +322,64 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
     source_key = rel.as_posix()
     module_id = ".".join(rel.with_suffix("").parts)
 
+    task_started = time.monotonic()
+
+    source_read_called = False
+    source_read_ms = 0.0
+
+    import_extract_called = False
+    import_extract_ms = 0.0
+
+    symbol_extract_called = False
+    symbol_extract_ms = 0.0
+
+    reference_extract_called = False
+    reference_extract_ms = 0.0
+
+    collision_extract_called = False
+    collision_extract_ms = 0.0
+
+    test_extract_called = False
+    test_extract_ms = 0.0
+
+    cache_set_called = False
+    cache_set_ms = 0.0
+
+    def timing_evidence() -> dict[str, object]:
+        return {
+            "task_total_ms": (
+                time.monotonic()
+                - task_started
+            )
+            * 1000.0,
+            "source_read_called": source_read_called,
+            "source_read_ms": source_read_ms,
+            "import_extract_called": import_extract_called,
+            "import_extract_ms": import_extract_ms,
+            "symbol_extract_called": symbol_extract_called,
+            "symbol_extract_ms": symbol_extract_ms,
+            "reference_extract_called": reference_extract_called,
+            "reference_extract_ms": reference_extract_ms,
+            "collision_extract_called": collision_extract_called,
+            "collision_extract_ms": collision_extract_ms,
+            "test_extract_called": test_extract_called,
+            "test_extract_ms": test_extract_ms,
+            "cache_set_called": cache_set_called,
+            "cache_set_ms": cache_set_ms,
+        }
+
     test_candidate = is_test_context_candidate(root_str, path)
+
+    source_read_called = True
+    source_read_started = time.monotonic()
+
     try:
         source_snapshot = read_source_snapshot(path)
     except SourceError as exc:
+        source_read_ms = (
+            time.monotonic()
+            - source_read_started
+        ) * 1000.0
         return {
             "module_id": module_id,
             "path": str(rel),
@@ -355,7 +409,14 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                 or path.parent == Path(root_str)
                 else None
             ),
+            **timing_evidence(),
         }
+
+    source_read_ms = (
+        time.monotonic()
+        - source_read_started
+    ) * 1000.0
+
     cache = _cache_manager(root_str)
     cache_get_started = time.monotonic()
     cached_data = cache.get(path, source_bytes=source_snapshot.raw)
@@ -434,6 +495,7 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                     if test_candidate or path.parent == Path(root_str)
                     else None
                 ),
+                **timing_evidence(),
             }
 
     source_parse_started = time.monotonic()
@@ -457,6 +519,7 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                 str(path.parent) if test_candidate or path.parent == Path(root_str)
                 else None
             ),
+            **timing_evidence(),
         }
 
     source_parse_ms = (time.monotonic() - source_parse_started) * 1000.0
@@ -504,6 +567,8 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                     collision_facts_status = "failure"
             else:
                 if symbol_facts is None:
+                    symbol_extract_called = True
+                    symbol_extract_started = time.monotonic()
                     try:
                         migrated_facts = extract_file_symbols(path, tree=tree)
                     except Exception as exc:
@@ -519,18 +584,37 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                             "status": _SYMBOL_FACTS_AVAILABLE,
                             "facts": migrated_facts,
                         }
+                    finally:
+                        symbol_extract_ms += (
+                            time.monotonic()
+                            - symbol_extract_started
+                        ) * 1000.0
                 if reference_facts is None:
-                    extracted_reference = extract_compact_reference_facts(
-                        module_id, tree=tree, imports=imports
-                    )
+                    reference_extract_called = True
+                    reference_extract_started = time.monotonic()
+                    try:
+                        extracted_reference = extract_compact_reference_facts(
+                            module_id,
+                            tree=tree,
+                            imports=imports,
+                        )
+                    finally:
+                        reference_extract_ms += (
+                            time.monotonic()
+                            - reference_extract_started
+                        ) * 1000.0
                     reference_facts = {
                         "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                         **extracted_reference,
-                        }
+                    }
                 if collision_facts is None:
+                    collision_extract_called = True
+                    collision_extract_started = time.monotonic()
                     try:
                         extracted_collision_facts = _extract_collision_facts(
-                            tree, module_id, path
+                            tree,
+                            module_id,
+                            path,
                         )
                     except Exception:
                         collision_facts_status = "failure"
@@ -541,13 +625,25 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                             "facts": extracted_collision_facts,
                         }
                         collision_facts_status = _COLLISION_FACTS_AVAILABLE
+                    finally:
+                        collision_extract_ms += (
+                            time.monotonic()
+                            - collision_extract_started
+                        ) * 1000.0
                 if test_candidate and test_facts is None:
+                    test_extract_called = True
+                    test_extract_started = time.monotonic()
                     try:
                         test_facts = _extract_test_facts(tree)
                     except Exception:
                         test_facts_status = "failure"
                     else:
                         test_facts_status = _TEST_FACTS_AVAILABLE
+                    finally:
+                        test_extract_ms += (
+                            time.monotonic()
+                            - test_extract_started
+                        ) * 1000.0
                 rewritten = dict(cached_data)
                 rewritten["lineage_facts"] = serialize_extracted_lineage_source_facts(
                     lineage_facts
@@ -565,21 +661,46 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                         rewritten["test_facts"] = test_facts
                     else:
                         rewritten.pop("test_facts", None)
-                cache.set(
-                    path,
-                    rewritten,
-                    source_bytes=source_snapshot.raw,
-                )
+                cache_set_called = True
+                cache_set_started = time.monotonic()
+                try:
+                    cache.set(
+                        path,
+                        rewritten,
+                        source_bytes=source_snapshot.raw,
+                    )
+                finally:
+                    cache_set_ms += (
+                        time.monotonic()
+                        - cache_set_started
+                    ) * 1000.0
     else:
         try:
             tree = parsed_input.tree
         except SourceError as exc:
             imports, error = None, str(exc)
         else:
-            imports, error = read_imports(path, tree=tree)
+            import_extract_called = True
+            import_extract_started = time.monotonic()
+            try:
+                imports, error = read_imports(
+                    path,
+                    tree=tree,
+                )
+            finally:
+                import_extract_ms += (
+                    time.monotonic()
+                    - import_extract_started
+                ) * 1000.0
+
             if error is None:
+                symbol_extract_called = True
+                symbol_extract_started = time.monotonic()
                 try:
-                    extracted_facts = extract_file_symbols(path, tree=tree)
+                    extracted_facts = extract_file_symbols(
+                        path,
+                        tree=tree,
+                    )
                     symbol_facts = {
                         "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
                         "status": _SYMBOL_FACTS_AVAILABLE,
@@ -592,16 +713,35 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                         "exception_type": type(exc).__name__,
                         "message": str(exc),
                     }
-                extracted_reference = extract_compact_reference_facts(
-                    module_id, tree=tree, imports=imports
-                )
+                finally:
+                    symbol_extract_ms += (
+                        time.monotonic()
+                        - symbol_extract_started
+                    ) * 1000.0
+                reference_extract_called = True
+                reference_extract_started = time.monotonic()
+                try:
+                    extracted_reference = extract_compact_reference_facts(
+                        module_id,
+                        tree=tree,
+                        imports=imports,
+                    )
+                finally:
+                    reference_extract_ms += (
+                        time.monotonic()
+                        - reference_extract_started
+                    ) * 1000.0
                 reference_facts = {
                     "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                     **extracted_reference,
                 }
+                collision_extract_called = True
+                collision_extract_started = time.monotonic()
                 try:
                     extracted_collision_facts = _extract_collision_facts(
-                        tree, module_id, path
+                        tree,
+                        module_id,
+                        path,
                     )
                 except Exception:
                     collision_facts_status = "failure"
@@ -612,13 +752,25 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                         "facts": extracted_collision_facts,
                     }
                     collision_facts_status = _COLLISION_FACTS_AVAILABLE
+                finally:
+                    collision_extract_ms += (
+                        time.monotonic()
+                        - collision_extract_started
+                    ) * 1000.0
                 if test_candidate:
+                    test_extract_called = True
+                    test_extract_started = time.monotonic()
                     try:
                         test_facts = _extract_test_facts(tree)
                     except Exception:
                         test_facts_status = "failure"
                     else:
                         test_facts_status = _TEST_FACTS_AVAILABLE
+                    finally:
+                        test_extract_ms += (
+                            time.monotonic()
+                            - test_extract_started
+                        ) * 1000.0
         cache_data = {
             "imports": [dataclasses.asdict(imp) for imp in imports or []],
             "error": error,
@@ -632,11 +784,19 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
             cache_data["collision_facts"] = collision_facts
         if _valid_test_facts(test_facts):
             cache_data["test_facts"] = test_facts
-        cache.set(
-            path,
-            cache_data,
-            source_bytes=source_snapshot.raw,
-        )
+        cache_set_called = True
+        cache_set_started = time.monotonic()
+        try:
+            cache.set(
+                path,
+                cache_data,
+                source_bytes=source_snapshot.raw,
+            )
+        finally:
+            cache_set_ms += (
+                time.monotonic()
+                - cache_set_started
+            ) * 1000.0
 
     return {
         "module_id": module_id,
@@ -666,6 +826,7 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
             if test_candidate or path.parent == Path(root_str)
             else None
         ),
+        **timing_evidence(),
     }
 
 
@@ -731,6 +892,7 @@ def index_repository(
     Buduje indeks modułów projektu wraz z listą pominiętych plików.
     """
 
+    index_started = time.monotonic()
     root_path = Path(root).resolve()
 
     if not root_path.exists():
@@ -755,6 +917,43 @@ def index_repository(
     cache_get_sum_ms = 0.0
     lineage_extract_sum_ms = 0.0
     lineage_extract_slowest: list[tuple[float, str]] = []
+
+    worker_task_sum_ms = 0.0
+    worker_task_slowest: list[tuple[float, str]] = []
+    cache_miss_slowest: list[tuple[float, str]] = []
+
+    source_read_calls = 0
+    source_read_sum_ms = 0.0
+
+    import_extract_calls = 0
+    import_extract_sum_ms = 0.0
+
+    symbol_extract_calls = 0
+    symbol_extract_sum_ms = 0.0
+
+    reference_extract_calls = 0
+    reference_extract_sum_ms = 0.0
+
+    collision_extract_calls = 0
+    collision_extract_sum_ms = 0.0
+
+    test_extract_calls = 0
+    test_extract_sum_ms = 0.0
+
+    cache_set_calls = 0
+    cache_set_sum_ms = 0.0
+
+    file_discovery_ms = 0.0
+
+    pool_scope_ms = 0.0
+    pool_enter_ms = 0.0
+    pool_submit_ms = 0.0
+    parent_future_wait_ms = 0.0
+    parent_future_result_ms = 0.0
+    parent_merge_ms = 0.0
+    parent_progress_ms = 0.0
+    pool_shutdown_ms = 0.0
+
     collision_facts_by_module: dict[str, list[dict]] = {}
     test_facts_by_path: dict[str, dict] = {}
     automatic_test_dir_entries: dict[Path, set[str]] = {root_path: set()}
@@ -773,27 +972,189 @@ def index_repository(
         }
 
     def record_file_task_evidence(result: dict) -> None:
-        nonlocal file_tasks, source_parse_calls, source_parse_failures
-        nonlocal cache_get_calls, cache_hits, lineage_cache_hits, lineage_extract_calls
-        nonlocal source_parse_sum_ms, cache_get_sum_ms, lineage_extract_sum_ms
+        nonlocal file_tasks
+        nonlocal source_parse_calls
+        nonlocal source_parse_failures
+        nonlocal cache_get_calls
+        nonlocal cache_hits
+        nonlocal lineage_cache_hits
+        nonlocal lineage_extract_calls
+        nonlocal source_parse_sum_ms
+        nonlocal cache_get_sum_ms
+        nonlocal lineage_extract_sum_ms
+
+        nonlocal worker_task_sum_ms
+        nonlocal source_read_calls
+        nonlocal source_read_sum_ms
+        nonlocal import_extract_calls
+        nonlocal import_extract_sum_ms
+        nonlocal symbol_extract_calls
+        nonlocal symbol_extract_sum_ms
+        nonlocal reference_extract_calls
+        nonlocal reference_extract_sum_ms
+        nonlocal collision_extract_calls
+        nonlocal collision_extract_sum_ms
+        nonlocal test_extract_calls
+        nonlocal test_extract_sum_ms
+        nonlocal cache_set_calls
+        nonlocal cache_set_sum_ms
+
         file_tasks += 1
-        elapsed_ms = float(result.get("lineage_extract_ms", 0.0))
+
+        task_total_ms = float(
+            result.get(
+                "task_total_ms",
+                0.0,
+            )
+        )
+        worker_task_sum_ms += task_total_ms
+        worker_task_slowest.append(
+            (
+                task_total_ms,
+                result["path"],
+            )
+        )
+
+        elapsed_ms = float(
+            result.get(
+                "lineage_extract_ms",
+                0.0,
+            )
+        )
         lineage_extract_sum_ms += elapsed_ms
-        lineage_extract_slowest.append((elapsed_ms, result["path"]))
+        lineage_extract_slowest.append(
+            (
+                elapsed_ms,
+                result["path"],
+            )
+        )
+
         if result.get("source_parse_called") is True:
             source_parse_calls += 1
+
         if result.get("source_parse_failed") is True:
             source_parse_failures += 1
+
         if result.get("cache_get_called") is True:
             cache_get_calls += 1
+
         if result.get("cache_hit") is True:
             cache_hits += 1
+
         if result.get("lineage_cache_hit") is True:
             lineage_cache_hits += 1
+
         if result.get("lineage_extract_called") is True:
             lineage_extract_calls += 1
-        source_parse_sum_ms += float(result.get("source_parse_ms", 0.0))
-        cache_get_sum_ms += float(result.get("cache_get_ms", 0.0))
+
+        source_parse_sum_ms += float(
+            result.get(
+                "source_parse_ms",
+                0.0,
+            )
+        )
+
+        cache_get_sum_ms += float(
+            result.get(
+                "cache_get_ms",
+                0.0,
+            )
+        )
+
+        if result.get("source_read_called") is True:
+            source_read_calls += 1
+
+        source_read_sum_ms += float(
+            result.get(
+                "source_read_ms",
+                0.0,
+            )
+        )
+
+        if result.get("import_extract_called") is True:
+            import_extract_calls += 1
+
+        import_extract_sum_ms += float(
+            result.get(
+                "import_extract_ms",
+                0.0,
+            )
+        )
+
+        if result.get("symbol_extract_called") is True:
+            symbol_extract_calls += 1
+
+        symbol_extract_sum_ms += float(
+            result.get(
+                "symbol_extract_ms",
+                0.0,
+            )
+        )
+
+        if result.get("reference_extract_called") is True:
+            reference_extract_calls += 1
+
+        reference_extract_sum_ms += float(
+            result.get(
+                "reference_extract_ms",
+                0.0,
+            )
+        )
+
+        if result.get("collision_extract_called") is True:
+            collision_extract_calls += 1
+
+        collision_extract_sum_ms += float(
+            result.get(
+                "collision_extract_ms",
+                0.0,
+            )
+        )
+
+        if result.get("test_extract_called") is True:
+            test_extract_calls += 1
+
+        test_extract_sum_ms += float(
+            result.get(
+                "test_extract_ms",
+                0.0,
+            )
+        )
+
+        if result.get("cache_set_called") is True:
+            cache_set_calls += 1
+
+        cache_set_sum_ms += float(
+            result.get(
+                "cache_set_ms",
+                0.0,
+            )
+        )
+
+        if (
+            result.get("cache_get_called") is True
+            and result.get("cache_hit") is not True
+        ):
+            detail = (
+                f"{result['path']}"
+                f"|task={task_total_ms:.3f}"
+                f"|source_read={float(result.get('source_read_ms', 0.0)):.3f}"
+                f"|cache_get={float(result.get('cache_get_ms', 0.0)):.3f}"
+                f"|source_parse={float(result.get('source_parse_ms', 0.0)):.3f}"
+                f"|lineage={float(result.get('lineage_extract_ms', 0.0)):.3f}"
+                f"|imports={float(result.get('import_extract_ms', 0.0)):.3f}"
+                f"|symbols={float(result.get('symbol_extract_ms', 0.0)):.3f}"
+                f"|references={float(result.get('reference_extract_ms', 0.0)):.3f}"
+                f"|collisions={float(result.get('collision_extract_ms', 0.0)):.3f}"
+                f"|tests={float(result.get('test_extract_ms', 0.0)):.3f}"
+                f"|cache_set={float(result.get('cache_set_ms', 0.0)):.3f}"
+            )
+            cache_miss_slowest.append(
+                (
+                    task_total_ms,
+                    detail,
+                )
+            )
 
     def emit_index_profile_evidence(execution_mode: str) -> None:
         trace_event(
@@ -833,11 +1194,105 @@ def index_repository(
             ),
         )
 
+    def emit_worker_timing_evidence(
+        execution_mode: str,
+    ) -> None:
+        slowest_tasks = sorted(
+            worker_task_slowest,
+            reverse=True,
+        )[:10]
+
+        worker_task_max_ms = (
+            slowest_tasks[0][0]
+            if slowest_tasks
+            else 0.0
+        )
+
+        worker_task_top10 = ",".join(
+            f"{path}:{elapsed_ms:.3f}"
+            for elapsed_ms, path in slowest_tasks
+        )
+
+        slowest_misses = sorted(
+            cache_miss_slowest,
+            reverse=True,
+        )[:10]
+
+        cache_miss_top10 = ";".join(
+            detail
+            for _elapsed_ms, detail in slowest_misses
+        )
+
+        trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_INDEX_WORKER_TIMING",
+            operation="indexing_worker_timing",
+            execution_mode=execution_mode,
+            timing_semantics=(
+                "aggregate_file_task_not_critical_path"
+            ),
+            file_tasks=file_tasks,
+            worker_task_sum_ms=worker_task_sum_ms,
+            worker_task_max_ms=worker_task_max_ms,
+            worker_task_top10=worker_task_top10,
+            source_read_calls=source_read_calls,
+            source_read_sum_ms=source_read_sum_ms,
+            import_extract_calls=import_extract_calls,
+            import_extract_sum_ms=import_extract_sum_ms,
+            symbol_extract_calls=symbol_extract_calls,
+            symbol_extract_sum_ms=symbol_extract_sum_ms,
+            reference_extract_calls=reference_extract_calls,
+            reference_extract_sum_ms=reference_extract_sum_ms,
+            collision_extract_calls=collision_extract_calls,
+            collision_extract_sum_ms=collision_extract_sum_ms,
+            test_extract_calls=test_extract_calls,
+            test_extract_sum_ms=test_extract_sum_ms,
+            cache_set_calls=cache_set_calls,
+            cache_set_sum_ms=cache_set_sum_ms,
+            cache_miss_task_count=len(
+                cache_miss_slowest
+            ),
+            cache_miss_top10=cache_miss_top10,
+        )
+
+    def emit_parent_timing_evidence(
+        execution_mode: str,
+    ) -> None:
+        trace_event(
+            "ANALYSIS",
+            "FULL_ANALYSIS_INDEX_PARENT_TIMING",
+            operation="indexing_parent_timing",
+            execution_mode=execution_mode,
+            timing_semantics=(
+                "critical_path_parent_subphases_partial"
+            ),
+            index_internal_ms=(
+                time.monotonic()
+                - index_started
+            )
+            * 1000.0,
+            file_discovery_ms=file_discovery_ms,
+            pool_scope_ms=pool_scope_ms,
+            pool_enter_ms=pool_enter_ms,
+            pool_submit_ms=pool_submit_ms,
+            parent_future_wait_ms=(
+                parent_future_wait_ms
+            ),
+            parent_future_result_ms=(
+                parent_future_result_ms
+            ),
+            parent_merge_ms=parent_merge_ms,
+            parent_progress_ms=parent_progress_ms,
+            pool_shutdown_ms=pool_shutdown_ms,
+        )
+
     ignored_dirs = set(DEFAULT_IGNORED_DIRS)
 
     if extra_ignored_dirs:
         ignored_dirs.update(extra_ignored_dirs)
 
+    file_discovery_started = time.monotonic()
+
     files_to_process = []
     for path in root_path.rglob("*.py"):
         # rglob matches directories too, and a directory named 'foo.py'
@@ -859,6 +1314,11 @@ def index_repository(
                 continue
         files_to_process.append(path)
 
+    file_discovery_ms = (
+        time.monotonic()
+        - file_discovery_started
+    ) * 1000.0
+
     total_files = len(files_to_process)
     if progress_callback:
         progress_callback(0, total_files, "Start...")
@@ -901,6 +1361,8 @@ def index_repository(
             completed += 1
             checkpoint(progress_callback, res["filename"], completed, total_files)
         emit_index_profile_evidence("inline")
+        emit_worker_timing_evidence("inline")
+        emit_parent_timing_evidence("inline")
         emit_lineage_extract_timing()
         return RepositoryIndex(
             modules=modules,
@@ -913,20 +1375,58 @@ def index_repository(
             automatic_test_dirs=automatic_test_dirs(),
         )
 
+    pool_scope_started = time.monotonic()
+    pool_enter_started = pool_scope_started
+
     with managed_process_pool(
         ProcessPoolExecutor,
     ) as executor:
+        pool_enter_ms = (
+            time.monotonic()
+            - pool_enter_started
+        ) * 1000.0
+
+        pool_submit_started = time.monotonic()
+
         futures = {
-            executor.submit(_process_single_file, str(p), str(root_path)): p
+            executor.submit(
+                _process_single_file,
+                str(p),
+                str(root_path),
+            ): p
             for p in files_to_process
         }
 
+        pool_submit_ms = (
+            time.monotonic()
+            - pool_submit_started
+        ) * 1000.0
+
+        wait_started = time.monotonic()
+
         for future in as_completed(futures):
+            parent_future_wait_ms += (
+                time.monotonic()
+                - wait_started
+            ) * 1000.0
+
+            future_result_started = time.monotonic()
             res = future.result()
+            parent_future_result_ms += (
+                time.monotonic()
+                - future_result_started
+            ) * 1000.0
+
+            parent_merge_started = time.monotonic()
+
             record_file_task_evidence(res)
 
             if res["error"]:
-                line_number, column_number = _syntax_error_location(res["error"])
+                line_number, column_number = (
+                    _syntax_error_location(
+                        res["error"]
+                    )
+                )
                 skipped.append(
                     SkippedFile(
                         path=res["path"],
@@ -939,31 +1439,109 @@ def index_repository(
                 modules[res["module_id"]] = Module(
                     module_id=res["module_id"],
                     path=res["path"],
-                    absolute_path=res.get("absolute_path", res["path"]),
+                    absolute_path=res.get(
+                        "absolute_path",
+                        res["path"],
+                    ),
                     imports=res["imports"],
                 )
+
                 if res.get("symbol_facts") is not None:
-                    symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
+                    symbol_facts_by_module[
+                        res["module_id"]
+                    ] = res["symbol_facts"]
+
                 if res.get("reference_facts") is not None:
-                    reference_facts_by_module[res["module_id"]] = res["reference_facts"]
-                extracted_lineage = res.get("lineage_facts")
+                    reference_facts_by_module[
+                        res["module_id"]
+                    ] = res["reference_facts"]
+
+                extracted_lineage = res.get(
+                    "lineage_facts"
+                )
+
                 if extracted_lineage is not None:
-                    lineage_facts_by_source[extracted_lineage.source_key] = extracted_lineage
-                cached_collision_facts = res.get("collision_facts")
-                if _valid_collision_facts(cached_collision_facts, res["module_id"]):
-                    collision_facts_by_module[res["module_id"]] = cached_collision_facts["facts"]
-                if _valid_test_facts(res.get("test_facts")):
-                    test_facts_by_path[str(Path(res["absolute_path"]).resolve())] = res["test_facts"]["facts"]
-                record_automatic_test_context_path(res)
+                    lineage_facts_by_source[
+                        extracted_lineage.source_key
+                    ] = extracted_lineage
+
+                cached_collision_facts = res.get(
+                    "collision_facts"
+                )
+
+                if _valid_collision_facts(
+                    cached_collision_facts,
+                    res["module_id"],
+                ):
+                    collision_facts_by_module[
+                        res["module_id"]
+                    ] = cached_collision_facts[
+                        "facts"
+                    ]
+
+                if _valid_test_facts(
+                    res.get(
+                        "test_facts"
+                    )
+                ):
+                    test_facts_by_path[
+                        str(
+                            Path(
+                                res["absolute_path"]
+                            ).resolve()
+                        )
+                    ] = res["test_facts"][
+                        "facts"
+                    ]
+
+                record_automatic_test_context_path(
+                    res
+                )
+
+            parent_merge_ms += (
+                time.monotonic()
+                - parent_merge_started
+            ) * 1000.0
 
             completed += 1
+
+            progress_started = time.monotonic()
+
             try:
-                checkpoint(progress_callback, res["filename"], completed, total_files)
+                checkpoint(
+                    progress_callback,
+                    res["filename"],
+                    completed,
+                    total_files,
+                )
             except AnalysisCancelled:
                 terminate_process_pool(executor)
                 raise
+            finally:
+                parent_progress_ms += (
+                    time.monotonic()
+                    - progress_started
+                ) * 1000.0
+
+            wait_started = time.monotonic()
+
+        pool_body_end = time.monotonic()
+
+    pool_scope_end = time.monotonic()
+
+    pool_scope_ms = (
+        pool_scope_end
+        - pool_scope_started
+    ) * 1000.0
+
+    pool_shutdown_ms = (
+        pool_scope_end
+        - pool_body_end
+    ) * 1000.0
 
     emit_index_profile_evidence("process_pool")
+    emit_worker_timing_evidence("process_pool")
+    emit_parent_timing_evidence("process_pool")
     emit_lineage_extract_timing()
 
     return RepositoryIndex(

diff --git a/tests/test_indexer_profile_evidence.py b/tests/test_indexer_profile_evidence.py
index ebce70b..911fc31 100644
--- a/tests/test_indexer_profile_evidence.py
+++ b/tests/test_indexer_profile_evidence.py
@@ -40,6 +40,42 @@ def test_warm_index_cache_evidence_proves_ast_parse_is_skipped(tmp_path, monkeyp
     assert event["lineage_extract_sum_ms"] == 0.0
     assert "elapsed_ms" not in event
 
+    worker_events = [
+        event
+        for event in events
+        if event["ev"]
+        == "FULL_ANALYSIS_INDEX_WORKER_TIMING"
+    ]
+
+    assert len(worker_events) == 1
+
+    worker_event = worker_events[0]
+
+    assert (
+        worker_event["timing_semantics"]
+        == "aggregate_file_task_not_critical_path"
+    )
+
+    assert worker_event["execution_mode"] == "inline"
+    assert worker_event["file_tasks"] == 2
+    assert worker_event["worker_task_sum_ms"] >= 0.0
+    assert worker_event["worker_task_max_ms"] >= 0.0
+
+    assert worker_event["source_read_calls"] == 2
+    assert worker_event["source_read_sum_ms"] >= 0.0
+
+    assert worker_event["import_extract_calls"] == 0
+    assert worker_event["symbol_extract_calls"] == 0
+    assert worker_event["reference_extract_calls"] == 0
+    assert worker_event["collision_extract_calls"] == 0
+    assert worker_event["test_extract_calls"] == 0
+
+    assert worker_event["cache_set_calls"] == 0
+    assert worker_event["cache_set_sum_ms"] == 0.0
+
+    assert worker_event["cache_miss_task_count"] == 0
+    assert worker_event["cache_miss_top10"] == ""
+
 
 def test_index_lineage_extraction_event_is_explicitly_noncritical(tmp_path, monkeypatch):
     monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
@@ -58,3 +94,119 @@ def test_index_lineage_extraction_event_is_explicitly_noncritical(tmp_path, monk
     assert event["timing_semantics"] == "aggregate_file_task_not_critical_path"
     assert event["lineage_extract_calls"] == 2
     assert event["lineage_cache_hits"] == 0
+
+    worker_events = [
+        event
+        for event in events
+        if event["ev"]
+        == "FULL_ANALYSIS_INDEX_WORKER_TIMING"
+    ]
+
+    assert len(worker_events) == 1
+
+    worker_event = worker_events[0]
+
+    assert worker_event["execution_mode"] == "inline"
+
+    assert (
+        worker_event["timing_semantics"]
+        == "aggregate_file_task_not_critical_path"
+    )
+
+    assert worker_event["file_tasks"] == 2
+
+    assert worker_event["source_read_calls"] == 2
+    assert worker_event["source_read_sum_ms"] >= 0.0
+
+    assert worker_event["import_extract_calls"] == 2
+    assert worker_event["import_extract_sum_ms"] >= 0.0
+
+    assert worker_event["symbol_extract_calls"] == 2
+    assert worker_event["symbol_extract_sum_ms"] >= 0.0
+
+    assert worker_event["reference_extract_calls"] == 2
+    assert worker_event["reference_extract_sum_ms"] >= 0.0
+
+    assert worker_event["collision_extract_calls"] == 2
+    assert worker_event["collision_extract_sum_ms"] >= 0.0
+
+    assert worker_event["cache_set_calls"] == 2
+    assert worker_event["cache_set_sum_ms"] >= 0.0
+
+    assert worker_event["cache_miss_task_count"] == 2
+
+    assert "a.py|task=" in worker_event[
+        "cache_miss_top10"
+    ]
+
+    assert "b.py|task=" in worker_event[
+        "cache_miss_top10"
+    ]
+
+
+def test_process_pool_parent_timing_evidence_is_explicit(
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
+    with capture_trace_events() as events:
+        index_repository(
+            str(
+                repo
+            )
+        )
+
+    parent_events = [
+        event
+        for event in events
+        if event["ev"]
+        == "FULL_ANALYSIS_INDEX_PARENT_TIMING"
+    ]
+
+    assert len(parent_events) == 1
+
+    event = parent_events[0]
+
+    assert event["execution_mode"] == "process_pool"
+
+    assert (
+        event["timing_semantics"]
+        == "critical_path_parent_subphases_partial"
+    )
+
+    assert event["index_internal_ms"] >= 0.0
+    assert event["file_discovery_ms"] >= 0.0
+    assert event["pool_scope_ms"] >= 0.0
+    assert event["pool_enter_ms"] >= 0.0
+    assert event["pool_submit_ms"] >= 0.0
+    assert event["parent_future_wait_ms"] >= 0.0
+    assert event["parent_future_result_ms"] >= 0.0
+    assert event["parent_merge_ms"] >= 0.0
+    assert event["parent_progress_ms"] >= 0.0
+    assert event["pool_shutdown_ms"] >= 0.0
+
+    assert (
+        event["pool_scope_ms"]
+        >= event["pool_enter_ms"]
+    )
+
+    assert (
+        event["pool_scope_ms"]
+        >= event["pool_shutdown_ms"]
+    )

FULL_DIFFS_END
