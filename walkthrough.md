STATUS=PASS
FILES_CHANGED=contextor/core/symbol_engine/indexer.py

FULL_DIFFS=
```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index b98ac9d..f900ee7 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -487,10 +487,13 @@ def _process_single_file(
         - source_read_started
     ) * 1000.0
 
-    cache = _cache_manager(
-        root_str,
-        cache_dir_str,
-    )
+    if cache_dir_str is None:
+        cache = _cache_manager(root_str)
+    else:
+        cache = _cache_manager(
+            root_str,
+            cache_dir_str,
+        )
     cache_get_started = time.monotonic()
     cached_data = cache.get(path, source_bytes=source_snapshot.raw)
     cache_get_ms = (time.monotonic() - cache_get_started) * 1000.0
@@ -1709,7 +1712,6 @@ def index_repository(
             res = _process_single_file(
                 str(path),
                 str(root_path),
-                cache_dir_str=resolved_cache_dir,
             )
             record_file_task_evidence(res)
             if res["error"]:
```

TARGETED_TESTS=PASS
TARGETED_TEST_COUNT=6
TARGETED_FAILURES=NONE
TARGETED_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/analysis/test_lineage_extraction.py::test_full_index_transports_transient_lineage_on_cache_miss_and_hit tests/analysis/test_lineage_extraction.py::test_repository_index_collects_source_keyed_transient_lineage tests/test_index_fusion.py::test_index_cache_miss_stores_symbol_facts tests/test_index_fusion.py::test_reused_indexer_pool_uses_current_parent_cache_root tests/test_index_fusion.py::test_new_format_cache_hit_reuses_cached_facts_without_ast_parse tests/test_index_fusion.py::test_source_change_invalidates_symbol_facts_then_complete_warm_hit_skips_ast_parse

DIRECT_INLINE_ONE_ARG_CACHE_MANAGER_COMPATIBILITY=YES
PROCESS_POOL_PARENT_CACHE_DIR_PRESERVED=YES
FAMILY_C_FIX_PRESERVED=YES

CONTEXTOR_REVISION=1452
WORKSPACE_SYNC=verified
CANONICAL_STATE=fresh