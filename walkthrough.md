## CPA10I_REGRESSION_TEST_CONTRACT_MIGRATION

STATUS=PARTIAL_REGRESSION_BLOCKED
HEAD_BEFORE=832cf884af9c01fecdac94c6cda4d26f637b0934
HEAD_AFTER=832cf884af9c01fecdac94c6cda4d26f637b0934
FILES_CHANGED=tests/analysis/test_lineage_extraction.py; tests/test_collision_facts_fusion.py; tests/test_test_context_fusion.py

DISCOVERY=Contextor LIVE revision 1170 resolved parse_source_snapshot, CacheManager.get/set, and index_repository with workspace_sync=verified. Cache get/set require keyword-only source_bytes. Complete current-schema cache returns before parse; cache-miss/incomplete paths call indexer.parse_source_snapshot(snapshot, path).

TESTS_CHANGED_FILES=PASS (217 passed in 10.34s)
REGRESSION_SELECTION=BLOCKED (224 passed, 2 failed in 13.81s)
REGRESSION_COMMAND=& .\.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_collision_facts_fusion.py tests/test_reference_fusion_integration.py tests/test_test_context_fusion.py
REGRESSION_BLOCKER=tests/test_reference_fusion_integration.py has two remaining stale indexer.parse_source_with_fingerprint monkeypatch seams: test_warm_reference_hit_parses_once_for_lineage_and_zero_reference_extraction; test_reference_legacy_and_schema_migrations_parse_once_then_hit_warm. This file is outside FILES_TO_CHANGE_EXACTLY and was not edited.
PROFILE_RUN=NOT_RUN
GIT_DIFF_CHECK=PASS (no whitespace errors; only CRLF conversion warnings)
PRODUCTION_DIFF_EXTENDED=NO (git diff --name-only HEAD contains only the three allowed test files and walkthrough.md)

ACTUAL_DIFF=
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index b98527a..1a6877d 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -1227,8 +1227,8 @@ def test_full_index_transports_transient_lineage_on_cache_miss_and_hit(tmp_path,
     source.write_text("value = 1\n", encoding="utf-8")
     class FakeCache:
         def __init__(self): self.data = None
-        def get(self, _path): return self.data
-        def set(self, _path, data): self.data = data
+        def get(self, _path, *, source_bytes): return self.data
+        def set(self, _path, data, *, source_bytes): self.data = data
     cache = FakeCache()
     monkeypatch.setattr(indexer_module, "_cache_manager", lambda _root: cache)
     first = indexer_module._process_single_file(str(source), str(tmp_path))
@@ -1242,8 +1242,8 @@ def test_repository_index_collects_source_keyed_transient_lineage(tmp_path, monk
     (tmp_path / "pkg.py").write_text("value = 1\n", encoding="utf-8")
     monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
     class FakeCache:
-        def get(self, _path): return None
-        def set(self, _path, _data): return None
+        def get(self, _path, *, source_bytes): return None
+        def set(self, _path, _data, *, source_bytes): return None
     monkeypatch.setattr(indexer_module, "_cache_manager", lambda _root: FakeCache())
     result = indexer_module.index_repository(str(tmp_path))
     assert set(result.lineage_facts_by_source) == {"pkg.py"}
diff --git a/tests/test_collision_facts_fusion.py b/tests/test_collision_facts_fusion.py
index b3c8899..14a75ac 100644
--- a/tests/test_collision_facts_fusion.py
+++ b/tests/test_collision_facts_fusion.py
@@ -54,7 +54,7 @@ def test_cold_index_facts_match_repository_extraction_and_materialize_all_fields
         assert isinstance(fact["code"], str)
 
 
-def test_warm_current_schema_parses_once_for_lineage_and_zero_collision_extraction(
+def test_warm_current_schema_skips_ast_parse_and_collision_extraction(
     tmp_path, isolated_dirs, monkeypatch
 ):
     _serial(monkeypatch)
@@ -63,21 +63,19 @@ def test_warm_current_schema_parses_once_for_lineage_and_zero_collision_extracti
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
 
     parse_calls = []
-    original_parse = indexer.parse_source_with_fingerprint
-
     def forbidden(*args, **kwargs):
         raise AssertionError("unexpected warm extraction")
 
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (parse_calls.append(path) or original_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or (_ for _ in ()).throw(AssertionError("unexpected warm AST parse"))),
     )
     monkeypatch.setattr(indexer, "extract_module_collision_facts", forbidden)
     warm = indexer.index_repository(str(root))
 
     assert warm.collision_facts_by_module["module"][0]["name"] == "public"
-    assert len(parse_calls) == 1
+    assert parse_calls == []
 
 
 def test_missing_collision_field_migrates_once_and_preserves_other_fact_families(
@@ -93,12 +91,12 @@ def test_missing_collision_field_migrates_once_and_preserves_other_fact_families
 
     parse_calls = []
     collision_calls = []
-    real_parse = indexer.parse_source_with_fingerprint
+    real_parse = indexer.parse_source_snapshot
     real_extract = indexer.extract_module_collision_facts
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (parse_calls.append(path) or real_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or real_parse(snapshot, path)),
     )
     monkeypatch.setattr(
         indexer,
@@ -162,11 +160,11 @@ def test_schema_mismatch_and_source_change_reextract_once(tmp_path, isolated_dir
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
 
     parse_calls = []
-    real_parse = indexer.parse_source_with_fingerprint
+    real_parse = indexer.parse_source_snapshot
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (parse_calls.append(path) or real_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or real_parse(snapshot, path)),
     )
     mismatched = indexer.index_repository(str(root))
     assert len(parse_calls) == 1
diff --git a/tests/test_test_context_fusion.py b/tests/test_test_context_fusion.py
index 9e50808..54bec75 100644
--- a/tests/test_test_context_fusion.py
+++ b/tests/test_test_context_fusion.py
@@ -86,7 +86,7 @@ def test_case():
     assert facts["has_assertions"] is expected[2]
 
 
-def test_cold_then_current_schema_warm_has_one_lineage_parse_per_source_and_zero_test_fact_visitor(
+def test_cold_then_current_schema_warm_skips_ast_parse_and_test_fact_visitor(
     tmp_path, isolated_dirs, monkeypatch
 ):
     root = tmp_path / "repo"
@@ -96,22 +96,16 @@ def test_cold_then_current_schema_warm_has_one_lineage_parse_per_source_and_zero
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
     parse_calls = []
     visitor_calls = []
-    original_parse = indexer.parse_source_with_fingerprint
     original_extract = indexer._extract_test_file_facts
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (parse_calls.append(path) or original_parse(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or (_ for _ in ()).throw(AssertionError("unexpected warm AST parse"))),
     )
     monkeypatch.setattr(indexer, "_extract_test_file_facts", lambda tree: (visitor_calls.append(tree) or original_extract(tree)))
 
     warm = indexer.index_repository(str(root))
-    assert set(parse_calls) == {
-        root / "pkg" / "mod.py",
-        root / "tests" / "conftest.py",
-        source,
-    }
-    assert all(parse_calls.count(path) == 1 for path in parse_calls)
+    assert parse_calls == []
     assert visitor_calls == []
     assert str(source.resolve()) in warm.test_facts_by_path
 
@@ -129,11 +123,11 @@ def test_non_candidate_cache_record_is_not_migrated(tmp_path, isolated_dirs, mon
     CacheManager(str(root)).set(source, {"imports": [], "error": None})
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
     calls = []
-    original = indexer.parse_source_with_fingerprint
+    original = indexer.parse_source_snapshot
     monkeypatch.setattr(
         indexer,
-        "parse_source_with_fingerprint",
-        lambda path: (calls.append(path) or original(path)),
+        "parse_source_snapshot",
+        lambda snapshot, path: (calls.append(path) or original(snapshot, path)),
     )
 
     result = indexer.index_repository(str(root))
@@ -151,13 +145,23 @@ def test_missing_schema_and_source_change_invalidate_test_facts(tmp_path, isolat
     data["test_facts"]["schema_version"] = 0
     CacheManager(str(root)).set(source, data)
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls = []
+    original_parse = indexer.parse_source_snapshot
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_snapshot",
+        lambda snapshot, path: (parse_calls.append(path) or original_parse(snapshot, path)),
+    )
     migrated = indexer.index_repository(str(root))
+    assert parse_calls == [source]
     assert migrated.test_facts_by_path[str(source.resolve())]["has_assertions"] is True
     assert _cache_data(root, source)["test_facts"]["schema_version"] == indexer.TEST_FACTS_SCHEMA_VERSION
 
     source.write_text("from pkg.mod import Target\nassert Target\nvalue = 2\n", encoding="utf-8")
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls.clear()
     changed = indexer.index_repository(str(root))
+    assert parse_calls == [source]
     assert changed.test_facts_by_path[str(source.resolve())]["names"]
     assert first.test_facts_by_path[str(source.resolve())] != changed.test_facts_by_path[str(source.resolve())]
