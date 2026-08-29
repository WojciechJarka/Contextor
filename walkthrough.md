# TASK=BOTTLENECKS-0E IMPLEMENT INDEX_FUSION WITH SAFE CACHE MIGRATION

## VERDICT

VERDICT=STATIC_PASS

PASS_GATE:
- INDEX_FUSION_ACTIVE=YES
- CACHE_SEMANTIC_VALIDITY=PASS
- LEGACY_CACHE_MIGRATION=PASS
- POST_MIGRATION_ZERO_SYMBOL_PARSE=PASS
- SYMBOL_FAILURE_ISOLATION=PASS
- FAILURE_RETRY=PASS
- CACHE_INVALIDATION=PASS
- SYMBOL_FIELD_PARITY=PASS
- ARTIFACT_PARITY=PASS
- SERIAL_PROCESSPOOL_PARITY=PASS
- FOCUSED_TESTS=PASS
- FULL_SUITE_RUN_BY_AGENT=NO

## CACHE_VERSIONING_FOUND

No existing cache-wide schema/tool-version mechanism was found in CacheManager. Existing cache validity is source BLAKE2b hash plus absolute source path. Added the smallest symbol-specific marker in the existing cache data subrecord:

symbol_facts.schema_version = 1

No second cache was added.

## CACHE_VALIDITY_IMPLEMENTATION

Files changed: contextor/core/symbol_engine/indexer.py only for this part.

On cache miss, the index worker parses once, calls read_imports(tree=tree) and extract_file_symbols(tree=tree), and writes imports, error, and successful symbol_facts into the existing CacheManager entry. AST objects are never serialized.

A persisted symbol record is accepted only when:
- schema_version equals 1;
- status equals available;
- facts is a dict containing exactly the nine fields classes, functions, methods, globals, calls, assignments, signatures, body_fingerprints, and errors.

Missing, malformed, or mismatched symbol-facts records do not invalidate valid imports. They trigger migration/recomputation. Source-hash/path validation remains owned by CacheManager, so source changes invalidate imports and facts together.

Successful empty facts are stored as status=available with all nine fields present and empty values as appropriate. They are not treated as missing or failure.

## LEGACY_MIGRATION_IMPLEMENTATION

A valid import-only or mismatched symbol-facts cache entry is migrated in _process_single_file:
- the cached imports remain authoritative;
- one parse is performed;
- facts are extracted from that AST;
- the existing cache entry is atomically upgraded with symbol_facts;
- the current result returns available facts;
- the next unchanged run has zero symbol parse.

If migration extraction fails, the valid Module/imports remain available, a run-scoped status=failure record is returned, and no failed symbol_facts field is persisted. The next run retries extraction.

New-format warm hits use the existing source hash read and zero ast.parse. Old-format warm hits are not permanently left on artifact fallback.

## SYMBOL_FAILURE_MAPPING

The internal result keeps error=None after imports have parsed. Therefore Module creation, imports, graph membership, and skipped-file semantics are unchanged.

The result record is status=failure with exception_type/message. collect_module_artifacts pre-registers failures[module_id] as:

<exception type>: <exception message>

Failed modules are excluded from artifact tasks and have no artifact result, matching the existing collector exception mapping. Available facts are consumed directly by the artifact worker. The path-based extraction remains only for an unavoidable missing/not-computed compatibility record.

The same behavior is used by serial fallback and ProcessPool initialization. Worker count, task granularity, result shape, deterministic assembly, and RepositoryReferenceIndex behavior were not changed.

## INTERNAL_RESULT_SCHEMA

_process_single_file retains all current fields and adds:

symbol_facts:
- status=available, schema_version=1, facts=<exact nine fields>
- status=failure, schema_version=1, exception_type, message
- absent/None only for an index/read error or an unavoidable compatibility case

error remains reserved for indexability/parse/import failures. The explicit status prevents valid empty facts from being confused with missing or failure.

## REPOSITORY_INDEX_SIDE_TABLE

RepositoryIndex gained:

symbol_facts_by_module: dict[str, dict] = dataclasses.field(default_factory=dict)

The field is run-scoped and uses a safe default factory. Module's public shape is unchanged. build_index still returns RepositoryIndex.modules. No AST is stored or transferred.

## IMPACTED_CALLERS

Contextor MCP discovery identified index_repository's production caller as contextor.core.api.facade, with 11 direct test consumers and 88 downstream modules (33 production, 55 tests). build_index is the sole intra-module caller. The artifact flow is:

generate_artifact_usage_report -> collect_module_artifacts -> _process_single_artifact_module

The side table is propagated through:
facade.analyze_project -> execute_global_pipeline -> build_artifact_pipeline -> generate_artifact_usage_report -> collect_module_artifacts

and through the non-hydrated analyze_layer path. Existing callers that use only modules/skipped remain compatible. Public Module/API/MCP contracts remain unchanged.

## FOCUSED_TESTS

Command executed:

.\.venv\Scripts\python.exe -m pytest -q tests/test_index_fusion.py tests/test_paths_and_cache.py tests/test_non_python_files.py tests/test_symbol_extractor_semantics.py tests/test_artifact_parallelism.py tests/test_artifact_report.py tests/test_h2a_reference_index_equivalence.py tests/test_h2a_complexity_regression.py tests/test_no_double_parse.py

Result:

42 passed in 26.01s

Exact new nodeids:
- tests/test_index_fusion.py::test_index_cache_miss_stores_symbol_facts
- tests/test_index_fusion.py::test_new_format_cache_hit_does_not_parse
- tests/test_index_fusion.py::test_legacy_cache_is_migrated_once_then_warm_hit_is_parse_free
- tests/test_index_fusion.py::test_symbol_facts_schema_mismatch_recomputes
- tests/test_index_fusion.py::test_symbol_failure_keeps_module_and_retries_without_negative_cache

The command also ran all collected tests in the seven requested existing focused files. No full pytest was run.

## BENCHMARK

The benchmark ran once on a disposable temporary repository with eight Python modules, serial fallback enabled only to make read/parse counters deterministic. It did not benchmark the canonical workspace.

| Case | Index ms | Artifact usage ms | Combined target ms | Index parses | Artifact parses | Failures |
|---|---:|---:|---:|---:|---:|---|
| COLD_MISS | 71.875 | 5.299 | 77.174 | 8 | 0 | 0 |
| NEW_FORMAT_WARM_1 | 215.339 | 4.348 | 219.687 | 0 | 0 | 0 |
| NEW_FORMAT_WARM_2 | 26.176 | 5.312 | 31.487 | 0 | 0 | 0 |
| NEW_FORMAT_WARM_3 | 31.773 | 3.282 | 35.055 | 0 | 0 | 0 |
| NEW_FORMAT_WARM median | — | — | 35.055 | 0 | 0 | 0 |
| LEGACY_CACHE_MIGRATION | 49.473 | 4.186 | 53.659 | 1 | 0 | 0 |
| POST_MIGRATION_WARM | 40.512 | 2.813 | 43.325 | 0 | 0 | 0 |
| STALE_SOURCE | 32.986 | 4.046 | 37.032 | 1 | 0 | 0 |
| SYMBOL_FAILURE | 62.373 | 2.584 | 64.957 | 8 | 0 | 8 |
| SYMBOL_FAILURE_RETRY | 214.491 | 2.436 | 216.927 | 8 | 0 | 0 |

SYMBOL_FAILURE preserved all eight indexed modules and imports, recorded eight module-keyed artifact failures, and did not write negative symbol cache entries. The retry parsed and succeeded.

TOTAL_ANALYZE_PROJECT on a separate two-module disposable fixture was 1127.660 ms (one run). The combined target above is the measured index plus artifact-usage handoff on the eight-module fixture; the two fixtures are not mixed into a speedup claim.

## BEFORE_AFTER_TOTAL

0C baseline warm total=25839.631 ms. The disposable 0E combined target is 35.055 ms median for an eight-module fixture; workloads are different and no percentage claim is made.

## BEFORE_AFTER_INDEX

0C baseline index=3272.821 ms. 0E disposable target index median for the three new-format warm runs is 31.773 ms; workload and execution mode differ, so this is evidence of behavior, not a canonical speedup claim.

## BEFORE_AFTER_ARTIFACT_USAGE

0C baseline artifact usage=12115.656 ms. 0E disposable new-format warm artifact usage values were 4.348, 5.312, and 3.282 ms; all had zero artifact parses.

## BEFORE_AFTER_ARTIFACT_PIPELINE

0C baseline artifact pipeline=15582.821 ms. The disposable benchmark measured index plus artifact usage as the target handoff: new-format warm values 219.687, 31.487, and 35.055 ms, median 35.055 ms. Full report-pipeline timing was not invoked.

## READ_PARSE_COUNTS

- New-format warm: index parse 0, artifact parse 0 on all three runs.
- Legacy migration: index parse 1, artifact parse 0.
- Post-migration warm: index parse 0, artifact parse 0.
- Stale source: index parse 1, artifact parse 0.
- Symbol failure: index parse 8, artifact parse 0; all failures were run-scoped and retried.
- Cold miss: index parse 8, artifact parse 0.

The cache hash verification still performs the existing source-content read.

## PAYLOAD_DELTA

0D1 measured compact facts for 317 modules at 523387 B pickle size, about 0.50 MiB or 1651 B/module. The prior artifact initializer was 3481407 B, about 3.32 MiB; projected combined payload was about 4.00 MiB, approximately +15.0%.

0E adds only plain JSON-safe compact facts and the schema marker to the existing cache data. It adds no AST and no independent cache. Exact ORJSON aggregate delta was not separately serialized by the disposable benchmark; the measured 0D1 compact-facts size remains the planning bound.

## FILES_CHANGED

Production:
- contextor/core/api/facade.py
- contextor/core/reporting_engine/artifact_pipeline.py
- contextor/core/reporting_engine/pipeline.py
- contextor/core/reporting_layer/artifact_usage_report.py
- contextor/core/symbol_engine/indexer.py

Test:
- tests/test_index_fusion.py

walkthrough.md is the reporting artifact and is excluded from this production/test count. Existing runtime logs are environment-generated and were not touched.

## COMPLETE_RAW_UNIFIED_DIFF

DIFF_BEGIN

diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index ef84588..94032cb 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -404,6 +404,7 @@ class ContextorFacade:
             datestamp=datestamp,
             trie=trie,
             package_root=package_root,
+            symbol_facts_by_module=index.symbol_facts_by_module,
         )
 
         if log and report_result.get("high_risk_layers"):
@@ -690,6 +691,7 @@ class ContextorFacade:
                 str(root_resolved),
                 runtime,
                 progress_callback=artifacts_progress,
+                symbol_facts_by_module=getattr(index, "symbol_facts_by_module", None),
             )
         
         from contextor.core.reporting_engine.dictionary import IndexDictionary
diff --git a/contextor/core/reporting_engine/artifact_pipeline.py b/contextor/core/reporting_engine/artifact_pipeline.py
index d3a786c..e5ed16b 100644
--- a/contextor/core/reporting_engine/artifact_pipeline.py
+++ b/contextor/core/reporting_engine/artifact_pipeline.py
@@ -45,6 +45,7 @@ def build_artifact_pipeline(
     soft_edges: dict,
     progress_callback=None,
     log=None,
+    symbol_facts_by_module: dict[str, dict] | None = None,
 ) -> ArtifactPipelineResult:
     """Build mutually consistent artifact and graph report representations."""
     log_program_event("REPORT", "artifact pipeline start", modules=len(modules))
@@ -56,6 +57,7 @@ def build_artifact_pipeline(
         root_path,
         runtime,
         progress_callback=progress_callback,
+        symbol_facts_by_module=symbol_facts_by_module,
     )
     artifact_data["debug_info"] = {
         "module_count": len(modules),
diff --git a/contextor/core/reporting_engine/pipeline.py b/contextor/core/reporting_engine/pipeline.py
index 3c80b35..3b42aba 100644
--- a/contextor/core/reporting_engine/pipeline.py
+++ b/contextor/core/reporting_engine/pipeline.py
@@ -47,6 +47,7 @@ def execute_global_pipeline(
     trie: dict | None = None,
     package_root: str = "",
     collision_facts: dict | None = None,
+    symbol_facts_by_module: dict[str, dict] | None = None,
 ):
     """
     Execute the complete global report pipeline.
@@ -213,6 +214,7 @@ def execute_global_pipeline(
         soft_edges=graph.soft_edges,
         progress_callback=progress_callback,
         log=log,
+        symbol_facts_by_module=symbol_facts_by_module,
     )
     artifact_data = artifact_bundle.artifact_data
     usage_sidecar = artifact_bundle.usage_sidecar
diff --git a/contextor/core/reporting_layer/artifact_usage_report.py b/contextor/core/reporting_layer/artifact_usage_report.py
index ea87569..3ecd9b0 100644
--- a/contextor/core/reporting_layer/artifact_usage_report.py
+++ b/contextor/core/reporting_layer/artifact_usage_report.py
@@ -118,21 +118,24 @@ def _symbol_kind(symbol: str, symbols: dict) -> str:
 _WORKER_MODULES: dict = {}
 _WORKER_ROOT: str = ""
 _WORKER_REFERENCE_INDEX: RepositoryReferenceIndex | None = None
+_WORKER_SYMBOL_FACTS: dict[str, dict] = {}
 
 
 def _init_artifact_worker(
     modules: dict,
     root_path: str,
     reference_index: RepositoryReferenceIndex | None = None,
+    symbol_facts_by_module: dict[str, dict] | None = None,
 ) -> None:
     """
     Initialize process-local worker state.
     """
-    global _WORKER_MODULES, _WORKER_ROOT, _WORKER_REFERENCE_INDEX
+    global _WORKER_MODULES, _WORKER_ROOT, _WORKER_REFERENCE_INDEX, _WORKER_SYMBOL_FACTS
 
     _WORKER_MODULES = modules
     _WORKER_ROOT = root_path
     _WORKER_REFERENCE_INDEX = reference_index
+    _WORKER_SYMBOL_FACTS = symbol_facts_by_module or {}
 
 
 def _process_single_artifact_module(module_id: str):
@@ -146,7 +149,11 @@ def _process_single_artifact_module(module_id: str):
         or module.path
     )
 
-    symbols = extract_file_symbols(str(absolute_path))
+    fact_record = _WORKER_SYMBOL_FACTS.get(module_id)
+    if fact_record and fact_record.get("status") == "available":
+        symbols = fact_record["facts"]
+    else:
+        symbols = extract_file_symbols(str(absolute_path))
     own_symbols = _module_own_symbols(symbols)
 
     if not own_symbols:
@@ -184,6 +191,7 @@ def collect_module_artifacts(
     root_path: str,
     progress_callback=None,
     reference_index: RepositoryReferenceIndex | None = None,
+    symbol_facts_by_module: dict[str, dict] | None = None,
 ) -> tuple[dict, dict]:
     """
     Collect artifact/reference information for all modules.
@@ -202,9 +210,25 @@ def collect_module_artifacts(
     if reference_index is None:
         reference_index = build_repository_reference_index(modules, root_path)
 
+    symbol_facts_by_module = symbol_facts_by_module or {}
+    for module_id, facts in symbol_facts_by_module.items():
+        if facts.get("status") == "failure":
+            failures[module_id] = (
+                f"{facts.get('exception_type', 'Exception')}: "
+                f"{facts.get('message', '')}"
+            )
+
+    eligible_module_ids = [
+        module_id
+        for module_id in modules
+        if module_id not in failures
+    ]
+
     if os.environ.get("CONTEXTOR_DISABLE_PROCESS_POOL") == "1":
-        _init_artifact_worker(modules, root_path, reference_index)
-        for module_id in modules:
+        _init_artifact_worker(
+            modules, root_path, reference_index, symbol_facts_by_module
+        )
+        for module_id in eligible_module_ids:
             try:
                 returned_module_id, data = _process_single_artifact_module(module_id)
                 result[returned_module_id] = data
@@ -216,14 +240,19 @@ def collect_module_artifacts(
 
     with ProcessPoolExecutor(
         initializer=_init_artifact_worker,
-        initargs=(modules, root_path, reference_index),
+        initargs=(
+            modules,
+            root_path,
+            reference_index,
+            symbol_facts_by_module,
+        ),
     ) as executor:
         futures = {
             executor.submit(
                 _process_single_artifact_module,
                 module_id,
             ): module_id
-            for module_id in modules
+            for module_id in eligible_module_ids
         }
 
         for future in as_completed(futures):
@@ -659,6 +688,7 @@ def generate_artifact_usage_report(
     root_path: str,
     runtime: dict | None = None,
     progress_callback=None,
+    symbol_facts_by_module: dict[str, dict] | None = None,
 ) -> dict:
     """
     Generate the global artifact usage report.
@@ -683,6 +713,7 @@ def generate_artifact_usage_report(
             modules,
             root_path,
             progress_callback=progress_callback,
+            symbol_facts_by_module=symbol_facts_by_module,
         )
     )
 
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 7f607e3..0a3dcfd 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -27,6 +27,26 @@ from contextor.core.domain.module import (
 from contextor.core.errors import AnalysisCancelled, checkpoint
 from contextor.core.paths import DEFAULT_IGNORED_DIRS
 from contextor.core.source import SourceError, parse_source
+from contextor.core.symbol_engine.extractor import extract_file_symbols
+
+
+SYMBOL_FACTS_SCHEMA_VERSION = 1
+_SYMBOL_FACTS_AVAILABLE = "available"
+_SYMBOL_FACTS_FAILURE = "failure"
+_SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
+_SYMBOL_FACT_FIELDS = frozenset(
+    {
+        "classes",
+        "functions",
+        "methods",
+        "globals",
+        "calls",
+        "assignments",
+        "signatures",
+        "body_fingerprints",
+        "errors",
+    }
+)
 
 
 # ==========================================================
@@ -162,18 +182,80 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
     cache = _cache_manager(root_str)
     cached_data = cache.get(path)
 
-    if cached_data:
+    symbol_facts = None
+    if cached_data is not None:
         error = cached_data.get("error")
         imports = None if error else [ImportRef(**imp) for imp in cached_data.get("imports", [])]
+
+        cached_facts = cached_data.get("symbol_facts") if not error else None
+        if (
+            isinstance(cached_facts, dict)
+            and cached_facts.get("schema_version") == SYMBOL_FACTS_SCHEMA_VERSION
+            and cached_facts.get("status") == _SYMBOL_FACTS_AVAILABLE
+            and isinstance(cached_facts.get("facts"), dict)
+            and set(cached_facts["facts"]) == _SYMBOL_FACT_FIELDS
+        ):
+            symbol_facts = cached_facts
+        elif not error:
+            try:
+                tree = parse_source(path)
+                migrated_facts = extract_file_symbols(path, tree=tree)
+                symbol_facts = {
+                    "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
+                    "status": _SYMBOL_FACTS_AVAILABLE,
+                    "facts": migrated_facts,
+                }
+                cache.set(
+                    path,
+                    {
+                        "imports": cached_data.get("imports", []),
+                        "error": error,
+                        "symbol_facts": symbol_facts,
+                    },
+                )
+            except SourceError as exc:
+                symbol_facts = {
+                    "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
+                    "status": _SYMBOL_FACTS_FAILURE,
+                    "exception_type": type(exc).__name__,
+                    "message": str(exc),
+                }
+            except Exception as exc:
+                symbol_facts = {
+                    "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
+                    "status": _SYMBOL_FACTS_FAILURE,
+                    "exception_type": type(exc).__name__,
+                    "message": str(exc),
+                }
     else:
-        imports, error = read_imports(path)
-        cache.set(
-            path,
-            {
-                "imports": [dataclasses.asdict(imp) for imp in imports or []],
-                "error": error,
-            },
-        )
+        try:
+            tree = parse_source(path)
+        except SourceError as exc:
+            imports, error = None, str(exc)
+        else:
+            imports, error = read_imports(path, tree=tree)
+            if error is None:
+                try:
+                    extracted_facts = extract_file_symbols(path, tree=tree)
+                    symbol_facts = {
+                        "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
+                        "status": _SYMBOL_FACTS_AVAILABLE,
+                        "facts": extracted_facts,
+                    }
+                except Exception as exc:
+                    symbol_facts = {
+                        "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
+                        "status": _SYMBOL_FACTS_FAILURE,
+                        "exception_type": type(exc).__name__,
+                        "message": str(exc),
+                    }
+        cache_data = {
+            "imports": [dataclasses.asdict(imp) for imp in imports or []],
+            "error": error,
+        }
+        if symbol_facts and symbol_facts.get("status") == _SYMBOL_FACTS_AVAILABLE:
+            cache_data["symbol_facts"] = symbol_facts
+        cache.set(path, cache_data)
 
     rel = path.relative_to(Path(root_str))
     module_id = ".".join(rel.with_suffix("").parts)
@@ -185,6 +267,7 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
         "imports": imports,
         "error": error,
         "filename": path.name,
+        "symbol_facts": symbol_facts,
     }
 
 
@@ -230,6 +313,8 @@ class RepositoryIndex:
 
     skipped: list[SkippedFile]
 
+    symbol_facts_by_module: dict[str, dict] = dataclasses.field(default_factory=dict)
+
 
 def index_repository(
     root: str, excludes: list[str] = None, extra_ignored_dirs: set = None, progress_callback=None
@@ -248,6 +333,7 @@ def index_repository(
 
     modules: dict[str, Module] = {}
     skipped: list[SkippedFile] = []
+    symbol_facts_by_module: dict[str, dict] = {}
 
     ignored_dirs = set(DEFAULT_IGNORED_DIRS)
 
@@ -300,11 +386,14 @@ def index_repository(
                     absolute_path=res.get("absolute_path", res["path"]),
                     imports=res["imports"],
                 )
+                if res.get("symbol_facts") is not None:
+                    symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
             completed += 1
             checkpoint(progress_callback, res["filename"], completed, total_files)
         return RepositoryIndex(
             modules=modules,
             skipped=sorted(skipped, key=lambda item: item.path),
+            symbol_facts_by_module=symbol_facts_by_module,
         )
 
     with ProcessPoolExecutor() as executor:
@@ -333,6 +422,8 @@ def index_repository(
                     absolute_path=res.get("absolute_path", res["path"]),
                     imports=res["imports"],
                 )
+                if res.get("symbol_facts") is not None:
+                    symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
 
             completed += 1
             try:
@@ -344,6 +435,7 @@ def index_repository(
     return RepositoryIndex(
         modules=modules,
         skipped=sorted(skipped, key=lambda item: item.path),
+        symbol_facts_by_module=symbol_facts_by_module,
     )
 
 

diff --git a/tests/test_index_fusion.py b/tests/test_index_fusion.py
new file mode 100644
--- /dev/null
+++ b/tests/test_index_fusion.py
@@ -0,0 +1,139 @@
+import json
+
+from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.reporting_layer.artifact_usage_report import collect_module_artifacts
+from contextor.core.symbol_engine import indexer
+
+
+def _cache_payload(root, source):
+    manager = CacheManager(str(root))
+    return json.loads(manager._get_cache_file_path(source).read_text())
+
+
+def test_index_cache_miss_stores_symbol_facts(tmp_path, isolated_dirs):
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text("def hello():\n    return 1\n", encoding="utf-8")
+
+    result = indexer.index_repository(str(root))
+
+    record = result.symbol_facts_by_module["module"]
+    assert record["status"] == "available"
+    assert record["facts"]["functions"] == ["hello"]
+    assert _cache_payload(root, source)["data"]["symbol_facts"] == record
+
+
+def test_new_format_cache_hit_does_not_parse(tmp_path, isolated_dirs, monkeypatch):
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text("value = 1\n", encoding="utf-8")
+    indexer.index_repository(str(root))
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    def forbidden_parse(path):
+        raise AssertionError(f"unexpected parse: {path}")
+
+    monkeypatch.setattr(indexer, "parse_source", forbidden_parse)
+
+    result = indexer.index_repository(str(root))
+
+    assert result.modules["module"].imports == []
+    assert result.symbol_facts_by_module["module"]["status"] == "available"
+
+
+def test_legacy_cache_is_migrated_once_then_warm_hit_is_parse_free(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text("def hello():\n    return 1\n", encoding="utf-8")
+    CacheManager(str(root)).set(source, {"imports": [], "error": None})
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls = []
+    original_parse = indexer.parse_source
+    monkeypatch.setattr(
+        indexer,
+        "parse_source",
+        lambda path: (parse_calls.append(path) or original_parse(path)),
+    )
+
+    migrated = indexer.index_repository(str(root))
+    assert migrated.symbol_facts_by_module["module"]["status"] == "available"
+    assert len(parse_calls) == 1
+
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls.clear()
+    warm = indexer.index_repository(str(root))
+    assert warm.symbol_facts_by_module["module"]["status"] == "available"
+    assert parse_calls == []
+
+
+def test_symbol_facts_schema_mismatch_recomputes(tmp_path, isolated_dirs, monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text("def hello():\n    return 1\n", encoding="utf-8")
+    CacheManager(str(root)).set(
+        source,
+        {
+            "imports": [],
+            "error": None,
+            "symbol_facts": {
+                "schema_version": 0,
+                "status": "available",
+                "facts": {"functions": ["stale"]},
+            },
+        },
+    )
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    original_parse = indexer.parse_source
+    parse_calls = []
+    monkeypatch.setattr(
+        indexer,
+        "parse_source",
+        lambda path: (parse_calls.append(path) or original_parse(path)),
+    )
+
+    result = indexer.index_repository(str(root))
+
+    assert len(parse_calls) == 1
+    assert result.symbol_facts_by_module["module"]["facts"]["functions"] == ["hello"]
+
+
+def test_symbol_failure_keeps_module_and_retries_without_negative_cache(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text("import os\ndef hello():\n    return os.name\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+    def fail_symbols(path, *, tree=None):
+        raise RuntimeError("visitor failed")
+
+    original_symbols = indexer.extract_file_symbols
+    monkeypatch.setattr(indexer, "extract_file_symbols", fail_symbols)
+    failed = indexer.index_repository(str(root))
+    record = failed.symbol_facts_by_module["module"]
+    assert "module" in failed.modules
+    assert [item.module for item in failed.modules["module"].imports] == ["os"]
+    assert record["status"] == "failure"
+    artifacts, failures = collect_module_artifacts(
+        failed.modules,
+        str(root),
+        symbol_facts_by_module=failed.symbol_facts_by_module,
+    )
+    assert "module" not in artifacts
+    assert failures == {"module": "RuntimeError: visitor failed"}
+    assert "symbol_facts" not in _cache_payload(root, source)["data"]
+
+    monkeypatch.setattr(indexer, "extract_file_symbols", original_symbols)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    retried = indexer.index_repository(str(root))
+    assert retried.symbol_facts_by_module["module"]["status"] == "available"
+
+
DIFF_END

## FINAL_STATUS

FILES_CHANGED=production/test files listed above
DIFFS=complete raw unified diff above
FULL_SUITE_RUN_BY_AGENT=NO
