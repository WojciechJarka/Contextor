# P1B3 Fix — Test boundary

## STATUS

SUCCESS

Restored the complete legacy-cache migration assertion sequence inside test_legacy_cache_without_lineage_is_migrated_once and removed its duplicate from the stale-schema test. Both tests now independently prove their required migration and subsequent warm-cache reuse contracts.

## VALIDATION

.\\.venv\\Scripts\\python.exe -m pytest -q tests\\test_lineage_index_cache.py tests\\analysis\\test_lineage_cache_codec.py tests\\analysis\\test_lineage_extraction_equivalence.py

19 passed in 1.29s

git diff --check -- tests/test_lineage_index_cache.py passed.

## FILES_CHANGED

- tests/test_lineage_index_cache.py

## FULL_DIFFS

\`\`\`diff
warning: in the working copy of 'tests/test_lineage_index_cache.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/test_lineage_index_cache.py b/tests/test_lineage_index_cache.py
index c318946..afba342 100644
--- a/tests/test_lineage_index_cache.py
+++ b/tests/test_lineage_index_cache.py
@@ -81,6 +81,23 @@ def test_legacy_cache_without_lineage_is_migrated_once(
 
     indexer.index_repository(str(repo))
 
+    assert calls == 1
+
+    migrated_data = cache.get(source)
+    assert migrated_data is not None
+    assert "lineage_facts" in migrated_data
+
+    def fail_extract(*args, **kwargs):
+        raise AssertionError("migrated lineage cache must skip extraction")
+
+    monkeypatch.setattr(
+        indexer,
+        "extract_lineage_source_facts",
+        fail_extract,
+    )
+
+    indexer.index_repository(str(repo))
+
 
 def test_stale_lineage_schema_is_migrated_once(
     tmp_path: Path,
@@ -149,20 +166,3 @@ def test_stale_lineage_schema_is_migrated_once(
     )
 
     indexer.index_repository(str(repo))
-
-    assert calls == 1
-
-    migrated_data = cache.get(source)
-    assert migrated_data is not None
-    assert "lineage_facts" in migrated_data
-
-    def fail_extract(*args, **kwargs):
-        raise AssertionError("migrated lineage cache must skip extraction")
-
-    monkeypatch.setattr(
-        indexer,
-        "extract_lineage_source_facts",
-        fail_extract,
-    )
-
-    indexer.index_repository(str(repo))

\`\`\`

