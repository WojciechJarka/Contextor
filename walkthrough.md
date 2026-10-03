STATUS=PASS
FILES_CHANGED=contextor/core/symbol_engine/indexer.py; tests/test_index_fusion.py

FULL_DIFFS=
```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 2bd8a2e..b98ac9d 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -39,7 +39,7 @@ from contextor.core.domain.module import (
     Module,
 )
 from contextor.core.errors import AnalysisCancelled, checkpoint
-from contextor.core.paths import DEFAULT_IGNORED_DIRS
+from contextor.core.paths import DEFAULT_IGNORED_DIRS, repo_cache_dir
 from contextor.core.reference.index import extract_compact_reference_facts
 from contextor.core.runtime_trace import trace_event
 from contextor.core.source import (
@@ -305,11 +305,26 @@ _CACHE_MANAGERS: dict[str, CacheManager] = {}
 _WORKER_LAST_BATCH_TOKEN_BY_PID: dict[int, str] = {}
 
 
-def _cache_manager(root_str: str) -> CacheManager:
+def _cache_manager(
+    root_str: str,
+    cache_dir_str: str | None = None,
+) -> CacheManager:
+    requested_cache_dir = (
+        Path(cache_dir_str)
+        if cache_dir_str is not None
+        else repo_cache_dir(root_str)
+    )
+
     manager = _CACHE_MANAGERS.get(root_str)
 
-    if manager is None:
-        manager = CacheManager(root_str)
+    if (
+        manager is None
+        or manager.cache_dir != requested_cache_dir
+    ):
+        manager = CacheManager(
+            root_str,
+            cache_dir=requested_cache_dir,
+        )
         _CACHE_MANAGERS[root_str] = manager
 
     return manager
@@ -320,6 +335,7 @@ def _process_single_file(
     root_str: str,
     submitted_monotonic_ns: int | None = None,
     batch_token: str | None = None,
+    cache_dir_str: str | None = None,
 ) -> dict:
     """Funkcja pomocnicza dla wieloprocesowości."""
     path = Path(path_str)
@@ -471,7 +487,10 @@ def _process_single_file(
         - source_read_started
     ) * 1000.0
 
-    cache = _cache_manager(root_str)
+    cache = _cache_manager(
+        root_str,
+        cache_dir_str,
+    )
     cache_get_started = time.monotonic()
     cached_data = cache.get(path, source_bytes=source_snapshot.raw)
     cache_get_ms = (time.monotonic() - cache_get_started) * 1000.0
@@ -955,6 +974,10 @@ def index_repository(
     if not root_path.is_dir():
         raise ValueError(f"Repository root is not directory: {root_path}")
 
+    resolved_cache_dir = str(
+        repo_cache_dir(root_path)
+    )
+
     modules: dict[str, Module] = {}
     skipped: list[SkippedFile] = []
     symbol_facts_by_module: dict[str, dict] = {}
@@ -1683,7 +1706,11 @@ def index_repository(
     completed = 0
     if os.environ.get("CONTEXTOR_DISABLE_PROCESS_POOL") == "1":
         for path in files_to_process:
-            res = _process_single_file(str(path), str(root_path))
+            res = _process_single_file(
+                str(path),
+                str(root_path),
+                cache_dir_str=resolved_cache_dir,
+            )
             record_file_task_evidence(res)
             if res["error"]:
                 line_number, column_number = _syntax_error_location(res["error"])
@@ -1769,6 +1796,7 @@ def index_repository(
                 str(root_path),
                 time.monotonic_ns(),
                 worker_batch_token,
+                resolved_cache_dir,
             ): p
             for p in files_to_process
         }
diff --git a/tests/test_index_fusion.py b/tests/test_index_fusion.py
index d586cb9..0489a65 100644
--- a/tests/test_index_fusion.py
+++ b/tests/test_index_fusion.py
@@ -1,6 +1,9 @@
 import json
 
 from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
 from contextor.core.reporting_layer.artifact_usage_report import collect_module_artifacts
 from contextor.core.symbol_engine import indexer
 
@@ -24,6 +27,103 @@ def test_index_cache_miss_stores_symbol_facts(tmp_path, isolated_dirs):
     assert record["facts"]["functions"] == ["hello"]
     assert _cache_payload(root, source)["data"]["symbol_facts"] == record
 
 
+def test_reused_indexer_pool_uses_current_parent_cache_root(
+    tmp_path,
+    monkeypatch,
+):
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+
+    first_cache = tmp_path / "cache-a"
+    second_cache = tmp_path / "cache-b"
+
+    monkeypatch.delenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL",
+        raising=False,
+    )
+
+    terminate_active_process_pools(
+        timeout=1.0,
+    )
+
+    try:
+        monkeypatch.setenv(
+            "CONTEXTOR_CACHE_DIR",
+            str(first_cache),
+        )
+
+        source.write_text(
+            "def first():\n    return 1\n",
+            encoding="utf-8",
+        )
+
+        first = indexer.index_repository(
+            str(root)
+        )
+
+        assert (
+            first
+            .symbol_facts_by_module["module"]
+            ["facts"]["functions"]
+            == ["first"]
+        )
+
+        first_payload = (
+            CacheManager(str(root))
+            ._get_cache_file_path(source)
+        )
+
+        assert first_payload.is_file()
+
+        monkeypatch.setenv(
+            "CONTEXTOR_CACHE_DIR",
+            str(second_cache),
+        )
+
+        source.write_text(
+            "def second():\n    return 2\n",
+            encoding="utf-8",
+        )
+
+        second = indexer.index_repository(
+            str(root)
+        )
+
+        assert (
+            second
+            .symbol_facts_by_module["module"]
+            ["facts"]["functions"]
+            == ["second"]
+        )
+
+        second_manager = CacheManager(
+            str(root)
+        )
+        second_payload = (
+            second_manager
+            ._get_cache_file_path(source)
+        )
+
+        assert second_payload.is_file()
+
+        cached = json.loads(
+            second_payload.read_text()
+        )
+
+        assert (
+            cached["data"]["symbol_facts"]
+            == second.symbol_facts_by_module[
+                "module"
+            ]
+        )
+
+    finally:
+        terminate_active_process_pools(
+            timeout=1.0,
+        )
```

PY_COMPILE=PASS
TARGETED_TESTS=PASS
TARGETED_TEST_COUNT=4
TARGETED_FAILURES=NONE
TARGETED_COMMAND=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_index_fusion.py::test_index_cache_miss_stores_symbol_facts tests/test_index_fusion.py::test_reused_indexer_pool_uses_current_parent_cache_root tests/test_index_fusion.py::test_new_format_cache_hit_reuses_cached_facts_without_ast_parse tests/test_index_fusion.py::test_source_change_invalidates_symbol_facts_then_complete_warm_hit_skips_ast_parse

PARENT_RESOLVES_CACHE_DIR=YES
WORKER_RECEIVES_CACHE_DIR=YES
WORKER_ENV_CACHE_ROOT_DEPENDENCY_REMOVED=YES
SAME_ROOT_CACHE_MANAGER_ROTATES_ON_CACHE_DIR_CHANGE=YES
REUSABLE_POOL_ROTATED_FOR_CACHE_CHANGE=NO
CACHEMANAGER_SET_CHANGED=NO

FAMILY_C_FAILURE_TARGETED_VALIDATED=YES

CONTEXTOR_REVISION=1450
WORKSPACE_SYNC=verified
CANONICAL_STATE=fresh

FULL_SUITE_RUN=NO
ANALYZE_PROJECT_RUN_COUNT=0
UPDATE_FILE_CALLED=NO
RESTART_PERFORMED=NO
PROCESS_TERMINATION_PERFORMED=TEST_OWNED_POOL_ONLY
FIX_DESIGNED_BY_AGENT=NO