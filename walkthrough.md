# TASK=BOTTLENECKS-0E1

VERDICT=FINAL_STATIC_PERF_PASS

## TEST_HARNESS_FIXED

YES. Added CONTEXTOR_DISABLE_PROCESS_POOL=1 to tests/test_index_fusion.py::test_new_format_cache_hit_does_not_parse. The assertion remains that the new-format cache hit performs zero parse calls. This is test-only.

## CACHE_INVALIDATION_PROOF

Added tests/test_index_fusion.py::test_source_change_invalidates_symbol_facts_then_warm_hit_is_parse_free.

It proves: old facts are not reused after source content changes; the changed source produces NEW facts; the changed run performs one parse; the unchanged follow-up warm run performs zero parses.

## FOCUSED_TESTS

Command:
.\.venv\Scripts\python.exe -m pytest -q tests/test_index_fusion.py tests/test_paths_and_cache.py tests/test_non_python_files.py tests/test_symbol_extractor_semantics.py tests/test_artifact_parallelism.py tests/test_artifact_report.py tests/test_h2a_reference_index_equivalence.py tests/test_h2a_complexity_regression.py tests/test_no_double_parse.py

Result:
43 passed in 38.28s

No production files changed. No full pytest was run.

## REAL_BENCHMARK

Protocol: disposable copy of the current source tree, exactly 317 Python modules after excluding scratch and benchmark helper files; isolated cache/state/output/registry; LIVE disconnected; default Windows ProcessPool, no serial fallback for primary comparison; worker count unchanged at 4.

The first attempted run was discarded because helper files inside the copy made the count 319. It is recorded as CONTAMINATED_RUN=1 and is not used in any result.

The accepted run used one cold ProcessPool run followed by three uncontaminated new-format warm ProcessPool runs on the same unchanged checkout.

| Case | TOTAL_ANALYZE_PROJECT ms | INDEX_REPOSITORY ms | ARTIFACT_USAGE_COLLECTION ms | ARTIFACT_PIPELINE_TOTAL ms | GLOBAL_PIPELINE_TOTAL ms | ast.parse count |
|---|---:|---:|---:|---:|---:|---:|
| COLD | 36308.379 | 7768.438 | 10387.436 | 20927.084 | 21726.278 | 317 |
| NEW_FORMAT_WARM_1 | 22794.387 | 7252.848 | 10808.966 | 11661.815 | 12334.995 | 0 |
| NEW_FORMAT_WARM_2 | 22431.252 | 7355.657 | 10144.544 | 11155.237 | 11871.450 | 0 |
| NEW_FORMAT_WARM_3 | 20982.300 | 6813.342 | 9510.481 | 10656.358 | 11335.210 | 0 |
| WARM_MEDIAN | 22431.252 | 7252.848 | 10144.544 | 11155.237 | 11871.450 | 0 |

MODULE_COUNT=317
WORKER_COUNT=4
PAYLOAD_SIZE=3563882 bytes initializer payload (modules, root, RepositoryReferenceIndex)

## BASELINE_TO_NEW

Baseline 0C:
TOTAL=25839.631 ms
INDEX_REPOSITORY=3272.821 ms
ARTIFACT_USAGE_COLLECTION=12115.656 ms
ARTIFACT_PIPELINE_TOTAL=15582.821 ms

Warm median deltas:
- TOTAL: -3408.379 ms (-13.19%)
- INDEX_REPOSITORY: +3980.027 ms (+121.61%)
- ARTIFACT_USAGE_COLLECTION: -1971.112 ms (-16.27%)
- ARTIFACT_PIPELINE_TOTAL: -4427.584 ms (-28.41%)

The index became heavier because SymbolVisitor work moved into index workers. The full warm total still achieved a meaningful 13.19% reduction, and focused artifact parity tests passed.

## READ_COUNTS

Accepted ProcessPool benchmark:
- COLD: 317 ast.parse calls; 317 cache hash/source-content reads; parse path adds one source read per module.
- Each NEW_FORMAT_WARM run: 0 ast.parse calls; 317 existing cache hash/source-content reads; 0 artifact-worker source reads/parses for available facts.
- Warm facts were available for all 317 parseable modules.
- The cache hash read is legitimate source validation and was not treated as a parse regression.

The earlier 0E disposable migration probe also established one parse for a legacy entry and zero parses on its post-migration warm run.

## CACHE_AND_PARITY_STATUS

INDEX_FUSION_ACTIVE=YES
CACHE_SEMANTIC_VALIDITY=PASS
LEGACY_CACHE_MIGRATION=PASS
POST_MIGRATION_ZERO_SYMBOL_PARSE=PASS
CACHE_INVALIDATION=PASS
SYMBOL_FIELD_PARITY=PASS
ARTIFACT_PARITY=PASS
SERIAL_PROCESSPOOL_PARITY=PASS
SYMBOL_FAILURE_ISOLATION=PASS
FAILURE_RETRY=PASS

## FILES_CHANGED

Production files: NONE
Test files: tests/test_index_fusion.py
walkthrough.md is the reporting artifact and is excluded from this count. Runtime logs are environment-generated and were not touched.

## COMPLETE_RAW_UNIFIED_DIFF

DIFF_BEGIN

diff --git a/tests/test_index_fusion.py b/tests/test_index_fusion.py
index f615ddf..7c8614d 100644
--- a/tests/test_index_fusion.py
+++ b/tests/test_index_fusion.py
@@ -25,6 +25,7 @@ def test_index_cache_miss_stores_symbol_facts(tmp_path, isolated_dirs):
 
 
 def test_new_format_cache_hit_does_not_parse(tmp_path, isolated_dirs, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
     root = tmp_path / "repo"
     root.mkdir()
     source = root / "module.py"
@@ -43,6 +44,38 @@ def test_new_format_cache_hit_does_not_parse(tmp_path, isolated_dirs, monkeypatc
     assert result.symbol_facts_by_module["module"]["status"] == "available"
 
 
+def test_source_change_invalidates_symbol_facts_then_warm_hit_is_parse_free(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text("def old():\n    return 1\n", encoding="utf-8")
+    indexer.index_repository(str(root))
+
+    source.write_text("def new():\n    return 2\n", encoding="utf-8")
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls = []
+    original_parse = indexer.parse_source
+    monkeypatch.setattr(
+        indexer,
+        "parse_source",
+        lambda path: (parse_calls.append(path) or original_parse(path)),
+    )
+
+    changed = indexer.index_repository(str(root))
+
+    assert len(parse_calls) == 1
+    assert changed.symbol_facts_by_module["module"]["facts"]["functions"] == ["new"]
+
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls.clear()
+    warm = indexer.index_repository(str(root))
+    assert parse_calls == []
+    assert warm.symbol_facts_by_module["module"]["facts"]["functions"] == ["new"]
+
+
 def test_legacy_cache_is_migrated_once_then_warm_hit_is_parse_free(
     tmp_path, isolated_dirs, monkeypatch
 ):

DIFF_END

FULL_SUITE_RUN_BY_AGENT=NO

