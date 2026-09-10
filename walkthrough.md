# Stale fusion-test parser instrumentation repair

## Scope and architectural verification

Mode: `TEST_ONLY`.

Contextor MCP verified `contextor/core/symbol_engine/indexer.py` as the fresh canonical `runtime` module (LIVE revision `581`; no syntax diagnostics). The repair intentionally leaves production untouched and updates repository-index parser instrumentation to delegate to and count `indexer.parse_source_with_fingerprint`.

## Exact stale-test inventory

All repository-index parser hooks in the three requested files were audited.

| File | Stale `indexer.parse_source` hooks replaced | Result |
| --- | ---: | --- |
| `tests/test_collision_facts_fusion.py` | 3 | Migration and source-change paths count one canonical parse; warm current-schema test was renamed and counts one lineage parse while collision extraction remains forbidden. |
| `tests/test_reference_fusion_integration.py` | 2 | Legacy migration, schema remigration, and warm cache count one canonical parse; warm reference extraction remains forbidden. |
| `tests/test_test_context_fusion.py` | 2 | Non-candidate migration counts one canonical parse; warm test facts assert one parse for each of its three indexed sources and zero test-fact visitor calls. |

No remaining `indexer.parse_source` reference exists in these three files. The direct `test_context_module.parse_source` unit-test usage was deliberately preserved because it does not exercise `index_repository`.

## Results

Passed:

```text
.venv\Scripts\python.exe -m pytest tests/test_collision_facts_fusion.py tests/test_reference_fusion_integration.py tests/test_test_context_fusion.py tests/test_index_fusion.py -q
36 passed in 9.11s

.venv\Scripts\python.exe -m pytest tests/test_no_double_parse.py -q
4 passed in 13.77s

git diff --check
exit 0 (Git emitted only configured LF-to-CRLF conversion warnings)
```

## FILES_CHANGED

- `tests/test_collision_facts_fusion.py`
- `tests/test_reference_fusion_integration.py`
- `tests/test_test_context_fusion.py`
- `walkthrough.md`

## COMPLETE FULL_DIFF

```diff
diff --git a/tests/test_collision_facts_fusion.py b/tests/test_collision_facts_fusion.py
index 4cefe56..b3c8899 100644
--- a/tests/test_collision_facts_fusion.py
+++ b/tests/test_collision_facts_fusion.py
@@ -54,7 +54,7 @@ def test_cold_index_facts_match_repository_extraction_and_materialize_all_fields
         assert isinstance(fact["code"], str)


-def test_warm_current_schema_has_zero_parse_and_collision_extraction(
+def test_warm_current_schema_parses_once_for_lineage_and_zero_collision_extraction(
     tmp_path, isolated_dirs, monkeypatch
 ):
     _serial(monkeypatch)
@@ -62,14 +62,22 @@ def test_warm_current_schema_has_zero_parse_and_collision_extraction(
     indexer.index_repository(str(root))
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

+    parse_calls = []
+    original_parse = indexer.parse_source_with_fingerprint
+
     def forbidden(*args, **kwargs):
         raise AssertionError("unexpected warm extraction")

-    monkeypatch.setattr(indexer, "parse_source", forbidden)
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_with_fingerprint",
+        lambda path: (parse_calls.append(path) or original_parse(path)),
+    )
     monkeypatch.setattr(indexer, "extract_module_collision_facts", forbidden)
     warm = indexer.index_repository(str(root))

     assert warm.collision_facts_by_module["module"][0]["name"] == "public"
+    assert len(parse_calls) == 1


 def test_missing_collision_field_migrates_once_and_preserves_other_fact_families(
@@ -85,9 +93,13 @@ def test_missing_collision_field_migrates_once_and_preserves_other_fact_families

     parse_calls = []
     collision_calls = []
-    real_parse = indexer.parse_source
+    real_parse = indexer.parse_source_with_fingerprint
     real_extract = indexer.extract_module_collision_facts
-    monkeypatch.setattr(indexer, "parse_source", lambda path: (parse_calls.append(path) or real_parse(path)))
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_with_fingerprint",
+        lambda path: (parse_calls.append(path) or real_parse(path)),
+    )
     monkeypatch.setattr(
         indexer,
         "extract_module_collision_facts",
@@ -150,8 +162,12 @@ def test_schema_mismatch_and_source_change_reextract_once(tmp_path, isolated_dir
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

     parse_calls = []
-    real_parse = indexer.parse_source
-    monkeypatch.setattr(indexer, "parse_source", lambda path: (parse_calls.append(path) or real_parse(path)))
+    real_parse = indexer.parse_source_with_fingerprint
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_with_fingerprint",
+        lambda path: (parse_calls.append(path) or real_parse(path)),
+    )
     mismatched = indexer.index_repository(str(root))
     assert len(parse_calls) == 1
     assert mismatched.collision_facts_by_module["module"][0]["name"] == "old_name"
diff --git a/tests/test_reference_fusion_integration.py b/tests/test_reference_fusion_integration.py
index 421f845..7101279 100644
--- a/tests/test_reference_fusion_integration.py
+++ b/tests/test_reference_fusion_integration.py
@@ -41,7 +41,7 @@ def test_cold_index_emits_json_safe_reference_facts_into_combined_cache(
     assert _payload(root, source)["reference_facts"] == record


-def test_warm_reference_hit_performs_zero_parse_and_zero_extraction(
+def test_warm_reference_hit_parses_once_for_lineage_and_zero_reference_extraction(
     tmp_path, isolated_dirs, monkeypatch
 ):
     monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
@@ -52,8 +52,12 @@ def test_warm_reference_hit_performs_zero_parse_and_zero_extraction(
     indexer.index_repository(str(root))
     _reset_worker_cache(root)

+    parse_calls = []
+    original_parse = indexer.parse_source_with_fingerprint
     monkeypatch.setattr(
-        indexer, "parse_source", lambda path: (_ for _ in ()).throw(AssertionError(path))
+        indexer,
+        "parse_source_with_fingerprint",
+        lambda path: (parse_calls.append(path) or original_parse(path)),
     )
     monkeypatch.setattr(
         indexer,
@@ -63,6 +67,7 @@ def test_warm_reference_hit_performs_zero_parse_and_zero_extraction(

     result = indexer.index_repository(str(root))
     assert result.reference_facts_by_module["module"]["status"] == "available"
+    assert len(parse_calls) == 1


 def test_reference_legacy_and_schema_migrations_parse_once_then_hit_warm(
@@ -75,10 +80,12 @@ def test_reference_legacy_and_schema_migrations_parse_once_then_hit_warm(
     source.write_text("def current(): return 1\n", encoding="utf-8")
     CacheManager(str(root)).set(source, {"imports": [], "error": None})
     _reset_worker_cache(root)
-    original_parse = indexer.parse_source
+    original_parse = indexer.parse_source_with_fingerprint
     calls = []
     monkeypatch.setattr(
-        indexer, "parse_source", lambda path: (calls.append(path) or original_parse(path))
+        indexer,
+        "parse_source_with_fingerprint",
+        lambda path: (calls.append(path) or original_parse(path)),
     )

     migrated = indexer.index_repository(str(root))
@@ -97,7 +104,7 @@ def test_reference_legacy_and_schema_migrations_parse_once_then_hit_warm(
     _reset_worker_cache(root)
     calls.clear()
     indexer.index_repository(str(root))
-    assert calls == []
+    assert len(calls) == 1


 def test_source_change_invalidates_reference_facts_and_reassembles_reexports(
diff --git a/tests/test_test_context_fusion.py b/tests/test_test_context_fusion.py
index b93663a..9e50808 100644
--- a/tests/test_test_context_fusion.py
+++ b/tests/test_test_context_fusion.py
@@ -86,7 +86,7 @@ def test_case():
     assert facts["has_assertions"] is expected[2]


-def test_cold_then_current_schema_warm_has_zero_test_fact_parse_and_visitor(
+def test_cold_then_current_schema_warm_has_one_lineage_parse_per_source_and_zero_test_fact_visitor(
     tmp_path, isolated_dirs, monkeypatch
 ):
     root = tmp_path / "repo"
@@ -96,13 +96,22 @@ def test_cold_then_current_schema_warm_has_zero_test_fact_parse_and_visitor(
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
     parse_calls = []
     visitor_calls = []
-    original_parse = indexer.parse_source
+    original_parse = indexer.parse_source_with_fingerprint
     original_extract = indexer._extract_test_file_facts
-    monkeypatch.setattr(indexer, "parse_source", lambda path: (parse_calls.append(path) or original_parse(path)))
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_with_fingerprint",
+        lambda path: (parse_calls.append(path) or original_parse(path)),
+    )
     monkeypatch.setattr(indexer, "_extract_test_file_facts", lambda tree: (visitor_calls.append(tree) or original_extract(tree)))

     warm = indexer.index_repository(str(root))
-    assert parse_calls == []
+    assert set(parse_calls) == {
+        root / "pkg" / "mod.py",
+        root / "tests" / "conftest.py",
+        source,
+    }
+    assert all(parse_calls.count(path) == 1 for path in parse_calls)
     assert visitor_calls == []
     assert str(source.resolve()) in warm.test_facts_by_path

@@ -120,8 +129,12 @@ def test_non_candidate_cache_record_is_not_migrated(tmp_path, isolated_dirs, mon
     CacheManager(str(root)).set(source, {"imports": [], "error": None})
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
     calls = []
-    original = indexer.parse_source
-    monkeypatch.setattr(indexer, "parse_source", lambda path: (calls.append(path) or original(path)))
+    original = indexer.parse_source_with_fingerprint
+    monkeypatch.setattr(
+        indexer,
+        "parse_source_with_fingerprint",
+        lambda path: (calls.append(path) or original(path)),
+    )

     result = indexer.index_repository(str(root))
     assert str(source.resolve()) not in result.test_facts_by_path
```
