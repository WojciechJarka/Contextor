# P1B3 — Stale lineage schema migration

## STATUS

SUCCESS

Added the requested regression only. A cache entry with stale lineage_facts schema performs exactly one fallback extraction, is rewritten with the current schema, and the following warm run skips the extractor. No production files changed.

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
index 32f92d1..c318946 100644
--- a/tests/test_lineage_index_cache.py
+++ b/tests/test_lineage_index_cache.py
@@ -1,6 +1,9 @@
 from pathlib import Path
 
 import contextor.core.symbol_engine.indexer as indexer
+from contextor.core.analysis.lineage_extraction import (
+    LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION,
+)
 
 
 def test_warm_index_reuses_cached_lineage(
@@ -78,6 +81,75 @@ def test_legacy_cache_without_lineage_is_migrated_once(
 
     indexer.index_repository(str(repo))
 
+
+def test_stale_lineage_schema_is_migrated_once(
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
+
+    stale_data = dict(cached_data)
+    stale_lineage = dict(stale_data["lineage_facts"])
+    stale_lineage["schema_version"] = (
+        LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION + 1
+    )
+    stale_data["lineage_facts"] = stale_lineage
+    cache.set(source, stale_data)
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
+    assert (
+        migrated_data["lineage_facts"]["schema_version"]
+        == LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION
+    )
+
+    def fail_extract(*args, **kwargs):
+        raise AssertionError("current-schema lineage cache must skip extraction")
+
+    monkeypatch.setattr(
+        indexer,
+        "extract_lineage_source_facts",
+        fail_extract,
+    )
+
+    indexer.index_repository(str(repo))
+
     assert calls == 1
 
     migrated_data = cache.get(source)

\`\`\`

