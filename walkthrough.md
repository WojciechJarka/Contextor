# P1B2 — Legacy lineage cache migration

## STATUS

SUCCESS

A valid legacy per-file cache record without lineage_facts now performs exactly one fallback extraction and publishes it through the existing rewritten cache entry. No dedicated lineage cache.set path was added.

## VALIDATION

.\\.venv\\Scripts\\python.exe -m pytest -q tests\\test_lineage_index_cache.py tests\\analysis\\test_lineage_cache_codec.py tests\\analysis\\test_lineage_extraction_equivalence.py

18 passed in 1.20s

git diff --check -- contextor/core/symbol_engine/indexer.py tests/test_lineage_index_cache.py passed.

## FILES_CHANGED

- contextor/core/symbol_engine/indexer.py
- tests/test_lineage_index_cache.py

## FULL_DIFFS

\`\`\`diff
warning: in the working copy of 'contextor/core/symbol_engine/indexer.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_lineage_index_cache.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 2fe8191..9d86e29 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -349,12 +349,14 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
     cached_data = cache.get(path)
 
     lineage_facts = None
+    cached_lineage_valid = False
     if cached_data is not None:
         lineage_facts = deserialize_extracted_lineage_source_facts(
             cached_data.get("lineage_facts"),
             source_key=source_key,
             source_fingerprint=parsed_input.source_fingerprint,
         )
+        cached_lineage_valid = lineage_facts is not None
 
     lineage_extract_ms = 0.0
     if lineage_facts is None:
@@ -393,7 +395,8 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
             test_facts_status = _TEST_FACTS_AVAILABLE
 
         if not error and (
-            symbol_facts is None
+            not cached_lineage_valid
+            or symbol_facts is None
             or reference_facts is None
             or collision_facts is None
             or (test_candidate and test_facts is None)
diff --git a/tests/test_lineage_index_cache.py b/tests/test_lineage_index_cache.py
index bf2dc47..32f92d1 100644
--- a/tests/test_lineage_index_cache.py
+++ b/tests/test_lineage_index_cache.py
@@ -31,3 +31,66 @@ def test_warm_index_reuses_cached_lineage(
     second = indexer.index_repository(str(repo))
 
     assert second.lineage_facts_by_source["mod.py"] == first_lineage
+
+
+def test_legacy_cache_without_lineage_is_migrated_once(
+    tmp_path: Path,
+    monkeypatch,
+) -> None:
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    source = repo / "mod.py"
+    source.write_text(
+        "def f(value):\n"
+        "    return value + 1\n",
+        encoding="utf-8",
+    )
+
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    indexer._CACHE_MANAGERS.clear()
+
+    indexer.index_repository(str(repo))
+
+    root_str = str(repo.resolve())
+    cache = indexer._CACHE_MANAGERS[root_str]
+    cached_data = cache.get(source)
+    assert cached_data is not None
+    assert "lineage_facts" in cached_data
+
+    legacy_data = dict(cached_data)
+    legacy_data.pop("lineage_facts")
+    cache.set(source, legacy_data)
+
+    original_extract = indexer.extract_lineage_source_facts
+    calls = 0
+
+    def counted_extract(*args, **kwargs):
+        nonlocal calls
+        calls += 1
+        return original_extract(*args, **kwargs)
+
+    monkeypatch.setattr(
+        indexer,
+        "extract_lineage_source_facts",
+        counted_extract,
+    )
+
+    indexer.index_repository(str(repo))
+
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

\`\`\`

