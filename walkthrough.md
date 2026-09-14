# P1B1 — Indexer lineage warm cache

## STATUS

SUCCESS

The existing extracted-lineage codec is wired into the per-file cache. A newly written cache entry now lets the next warm index skip extract_lineage_source_facts. The parser remains before CacheManager.get; no parse fast path, legacy migration, CacheManager change, or ProcessPool change was added.

## VALIDATION

.\\.venv\\Scripts\\python.exe -m pytest -q tests\\test_lineage_index_cache.py tests\\analysis\\test_lineage_cache_codec.py tests\\analysis\\test_lineage_extraction_equivalence.py

17 passed in 24.22s

git diff --check -- contextor/core/symbol_engine/indexer.py tests/test_lineage_index_cache.py passed.

## FILES_CHANGED

- contextor/core/symbol_engine/indexer.py
- tests/test_lineage_index_cache.py

## FULL_DIFFS

\`\`\`diff
warning: in the working copy of 'contextor/core/symbol_engine/indexer.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index df741c0..2fe8191 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -19,7 +19,11 @@ from concurrent.futures import ProcessPoolExecutor, as_completed
 from pathlib import Path
 
 from contextor.core.analysis.cache_manager import CacheManager
-from contextor.core.analysis.lineage_extraction import extract_lineage_source_facts
+from contextor.core.analysis.lineage_extraction import (
+    deserialize_extracted_lineage_source_facts,
+    extract_lineage_source_facts,
+    serialize_extracted_lineage_source_facts,
+)
 from contextor.core.analysis.test_context import (
     _extract_test_file_facts,
     is_test_context_candidate,
@@ -339,18 +343,29 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
             ),
         }
     tree = parsed_input.tree
-    lineage_extract_started = time.monotonic()
-    lineage_facts = extract_lineage_source_facts(
-        tree,
-        source_key=source_key,
-        source_fingerprint=parsed_input.source_fingerprint,
-    )
-    lineage_extract_ms = (time.monotonic() - lineage_extract_started) * 1000.0
 
     # Próba odczytu z cache
     cache = _cache_manager(root_str)
     cached_data = cache.get(path)
 
+    lineage_facts = None
+    if cached_data is not None:
+        lineage_facts = deserialize_extracted_lineage_source_facts(
+            cached_data.get("lineage_facts"),
+            source_key=source_key,
+            source_fingerprint=parsed_input.source_fingerprint,
+        )
+
+    lineage_extract_ms = 0.0
+    if lineage_facts is None:
+        lineage_extract_started = time.monotonic()
+        lineage_facts = extract_lineage_source_facts(
+            tree,
+            source_key=source_key,
+            source_fingerprint=parsed_input.source_fingerprint,
+        )
+        lineage_extract_ms = (time.monotonic() - lineage_extract_started) * 1000.0
+
     symbol_facts = None
     reference_facts = None
     collision_facts = None
@@ -450,6 +465,9 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                     else:
                         test_facts_status = _TEST_FACTS_AVAILABLE
                 rewritten = dict(cached_data)
+                rewritten["lineage_facts"] = serialize_extracted_lineage_source_facts(
+                    lineage_facts
+                )
                 if collision_facts is None:
                     rewritten.pop("collision_facts", None)
                 if _valid_symbol_facts(symbol_facts):
@@ -516,6 +534,7 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
         cache_data = {
             "imports": [dataclasses.asdict(imp) for imp in imports or []],
             "error": error,
+            "lineage_facts": serialize_extracted_lineage_source_facts(lineage_facts),
         }
         if symbol_facts and symbol_facts.get("status") == _SYMBOL_FACTS_AVAILABLE:
             cache_data["symbol_facts"] = symbol_facts

\`\`\`

