# Collision-fact fusion correction closure

## Scope and verdict basis

This is a correction/audit-closure pass for the existing collision-fact fusion task. No unrelated refactor, collision semantic change, API/MCP change, LIVE behavior change, cache freshness weakening, or canonical-state change was introduced.

The correction removes only the stale invalid collision envelope during a parse-success migration when collision extraction fails. Valid symbol/reference/import/error data remains in the existing CacheManager record. A successful migration writes the current-schema envelope; a valid current-schema warm hit does not enter migration and remains unchanged. No negative collision cache entry is written.

## Correction rationale and regression

Before the correction, the migration path started with `rewritten = dict(cached_data)`. If a cached collision envelope was missing, invalid, or schema-mismatched and the current AST collision extraction raised, the later validity guard did not overwrite the field, so the original invalid envelope could be persisted unchanged.

The production correction in `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py` is the narrow removal:

```python
if collision_facts is None:
    rewritten.pop("collision_facts", None)
```

It executes immediately after the migration copy and before valid fact-family writes. A successful extraction sets a valid envelope afterward. An ordinary valid warm hit has non-None valid collision facts and does not execute this rewrite block.

The focused regression in `C:\Temp\Contextor_Repo\tests\test_collision_facts_fusion.py` seeds a schema-mismatched envelope, preserves the seeded valid symbol/reference records, forces the index-worker collision extractor to fail, asserts the side table is incomplete and the persisted record has no `collision_facts` field, then restores extraction and verifies a subsequent run repopulates the current-schema envelope.

## Focused verification

Command:

```
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' -m pytest -q -s tests/test_collision_facts_fusion.py tests/test_index_fusion.py
```

Result:

```
................
16 passed in 3.70s
```

The directly affected focused suite includes the new stale-envelope regression, cold parity/materialization, current-schema warm no-extraction behavior, missing-field migration, schema mismatch/source invalidation, valid empty facts, extraction failure/fallback selection, complete-coverage gating, serial/ProcessPool side-table parity, facade single-source consumption, and existing index-fusion coverage.

Commands:

```
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' -m py_compile contextor/core/symbol_engine/indexer.py tests/test_collision_facts_fusion.py
git diff --check -- contextor/core/api/facade.py contextor/core/symbol_engine/indexer.py
git diff --no-index --check -- /dev/null tests/test_collision_facts_fusion.py
```

Results: `py_compile` passed. Production/test diff checks passed; the no-index check returned its normal difference status and was normalized to success after reporting no whitespace errors. A repository-wide `git diff --check` includes the intentional single-space blank-context markers preserved inside the embedded raw unified diff; the production/test-file checks above are clean.

## Cache and coverage invariant

- Current-schema valid collision envelope: accepted unchanged on ordinary warm hit.
- Missing/invalid/schema-mismatched envelope: one current parse and one index-worker extraction attempt, using the already-live AST.
- Successful migration: existing valid symbol/reference/import/error data is preserved and collision facts are replaced by the validated current-schema envelope.
- Failed migration after parse: existing invalid/missing `collision_facts` is removed from the rewritten record; no failure/negative collision envelope is persisted.
- Source change: CacheManager source-fingerprint validation invalidates the record; the current AST path repopulates all successful fact families.
- Valid empty facts: stored as an available current-schema envelope with `facts=[]`, so empty is distinguishable from incomplete.
- Incomplete or invalid side table: never merged with fallback. The facade calls `assemble_collision_facts_or_fallback`; only an exact module-key domain with valid per-module facts is accepted. Otherwise the authoritative `extract_repository_collision_facts` path runs.
- `compute_collisions_from_facts` remains the aggregation/classification authority.
- Maximum normal affected-file AST traversal remains one parse shared by symbol/reference/collision extraction; normal current-schema warm traversal is zero.

## Benchmark protocol

The controlled benchmark used the existing external location `C:\Temp\Contextor_Benchmarks\0J3_collision_fusion`; no benchmark structure was created in the repository. It used a clean isolated cache/state/output directory, the copied repository source, the real `ContextorFacade.analyze_project()` path, six warm runs after one cold seed, and ProcessPool mode.

Two independent counters were instrumented in the external benchmark copy only:

1. index-worker `_extract_collision_facts` / `extract_module_collision_facts` execution, recorded as `COLLISION_VISITOR_COUNT`;
2. authoritative `extract_repository_collision_facts` entry, recorded as `COLLISION_FALLBACK_COUNT`.

The facade's `index_repository` call was timed separately from whole-analysis wall time. No counter was inferred from the other counter.

Raw runs (milliseconds):

| run | whole analyze_project | index_repository | collision visitor count | authoritative fallback count | errors | result |
|---|---:|---:|---:|---:|---:|---|
| cold_seed | 16112.713557 | 9304.706115 | 318 | 0 | 0 | true |
| warm_1 | 9511.558942 | 3808.670794 | 0 | 0 | 0 | true |
| warm_2 | 7837.482907 | 1958.364471 | 0 | 0 | 0 | true |
| warm_3 | 7555.671670 | 1742.857333 | 0 | 0 | 0 | true |
| warm_4 | 7407.669830 | 1793.355650 | 0 | 0 | 0 | true |
| warm_5 | 8252.386826 | 2367.972256 | 0 | 0 | 0 | true |
| warm_6 | 7568.814473 | 1963.386827 | 0 | 0 | 0 | true |

Candidate warm whole-analysis median: 7703.148690 ms; range 7407.669830-9511.558942 ms.

Candidate warm index median: 1960.875649 ms; range 1742.857333-3808.670794 ms.

Warm visitor counts: [0, 0, 0, 0, 0, 0].
Warm authoritative fallback counts: [0, 0, 0, 0, 0, 0].

Cold worker count 318 is expected extraction on the clean seed. Cold fallback count 0 confirms the complete worker side table was used even on the seed. The warm outlier (warm_1) is retained and not hidden; the median and full range include it.

Accepted post-0J2 baseline retained in the thread: whole-analysis warm median 8496.942524 ms. Current candidate delta is 7703.148690 - 8496.942524 = -793.793834 ms, a 9.34% reduction. The reduced cost is from eliminating the duplicated authoritative collision AST traversal on the complete warm path; it is not relocation into indexing, as shown by the independent index timings and zero fallback counter.

## Contextor post-change freshness and architecture evidence

Initial status inspection before the normal incremental path reported the prior completed job as `status=completed`, `live_publish_status=failed`, `live_publish_revision=null`, warning `non_monotonic_canonical_revision`. A broad live-event request required confirmation because its estimated output was 21.18 KiB, so it was not treated as evidence.

The normal Contextor incremental path was then used for both changed production files:

- `update_file(repo_path="C:\Temp\Contextor_Repo", file_path="C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py")`: `status=UNCHANGED`, `graph_state=fresh`, `dependencies_state=fresh`, `artifact_consumption_state=fresh`, `live_state_persisted=true`, `runtime_restart_required=false`.
- `update_file(repo_path="C:\Temp\Contextor_Repo", file_path="C:\Temp\Contextor_Repo\contextor\core\api\facade.py")`: same result and freshness fields.

Post-change Contextor queries consistently reported `canonical_state=fresh`, `workspace_sync=verified`, `canonical_revision=47`, `provenance=live`, and fresh module/graph/topology/artifact-consumption/cycles/collisions families for the indexer, facade, and collisions modules. No MCP restart was performed or required.

Contextor evidence:

- `contextor.core.symbol_engine.indexer`: runtime layer, fan-in 21, fan-out 9; outbound dependencies include the new hard dependency on `contextor.core.validator.collisions`; inbound facade dependency is present.
- `contextor.core.validator.collisions`: runtime layer; inbound hard dependency from `contextor.core.symbol_engine.indexer` is present; facade and existing reporting/validation consumers remain present.
- `contextor.core.api.facade`: contract layer; imports include `contextor.core.validator.collisions`; existing consumer/test reachability remains available.
- Exact Contextor source ranges confirmed the production migration removal, facade selection of `assemble_collision_facts_or_fallback` followed by `compute_collisions_from_facts`, and the authoritative full-domain extractor.
- Exact symbol implementations resolved `_process_single_file`, `assemble_collision_facts_or_fallback`, and `extract_repository_collision_facts` with complete AST-bounded implementations and the same verified revision.
- `get_project_architecture` reported fresh cycles with count 0. Nested `runtime` and `contract` layer-isolation calls had no dedicated report, so no fabricated isolation metric is claimed. The available fresh graph and cycle evidence shows no new cycle or layer violation attributable to this correction.

## Changed-file scope

Production/test files changed by the entire collision-fusion task:

- `C:\Temp\Contextor_Repo\contextor\core\api\facade.py`
- `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py`
- `C:\Temp\Contextor_Repo\tests\test_collision_facts_fusion.py`

The external benchmark harness and copied source under `C:\Temp\Contextor_Benchmarks\0J3_collision_fusion` are measurement-only artifacts outside the repository and are not task files. Runtime log changes and `walkthrough.md` are excluded from `FILES_CHANGED`.

## Complete raw unified diff

The following is the complete raw unified diff for every production/test file changed by the entire collision-fusion task. `walkthrough.md` is intentionally excluded.

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 1351d48..3832e1d 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -44,11 +44,14 @@ from contextor.core.reporting_layer.reporting_single_file import (
 )
 from contextor.core.single_file.single_file_analysis import collect_all_contexts
 
-from contextor.core.symbol_engine.indexer import build_index, index_repository
+from contextor.core.symbol_engine.indexer import (
+    assemble_collision_facts_or_fallback,
+    build_index,
+    index_repository,
+)
 from contextor.core.validator import validate
 from contextor.core.validator.collisions import (
     compute_collisions_from_facts,
-    extract_repository_collision_facts,
     validate_name_collisions,
 )
 from contextor.core.live_state import hydrate_repository_engine
@@ -341,9 +344,11 @@ class ContextorFacade:
             modules, path, index.reference_facts_by_module
         )
 
-        # Compute collision facts once from current-run modules
-        from contextor.core.validator.collisions import compute_collisions_from_facts, extract_repository_collision_facts
-        collision_facts = extract_repository_collision_facts(modules)
+        # Accept only complete index-worker facts; otherwise preserve the
+        # existing authoritative full-domain AST fallback.
+        collision_facts = assemble_collision_facts_or_fallback(
+            modules, index.collision_facts_by_module
+        )
         all_collisions = compute_collisions_from_facts(collision_facts)
 
         from contextor.core.graph.resolver import build_trie, detect_package_root
@@ -445,8 +450,6 @@ class ContextorFacade:
             topology_analytics = compute_topology_analytics(hard_edges, soft_edges, metrics) if hard_edges else {}
 
             from contextor.core.analysis.incremental.materialization import _validate_collision_facts_dict
-            from contextor.core.validator.collisions import compute_collisions_from_facts
-
             cf = getattr(analysis_result, "collision_facts", None)
             mods = getattr(analysis_result, "modules", {})
             is_collision_complete = _validate_collision_facts_dict(cf, mods)
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index f83f987..37a080e 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -29,13 +29,22 @@ from contextor.core.paths import DEFAULT_IGNORED_DIRS
 from contextor.core.reference.index import extract_compact_reference_facts
 from contextor.core.source import SourceError, parse_source
 from contextor.core.symbol_engine.extractor import extract_file_symbols
+from contextor.core.validator.collisions import (
+    COLLISION_FACT_KEYS,
+    extract_module_collision_facts,
+    extract_repository_collision_facts,
+)
 
 
 SYMBOL_FACTS_SCHEMA_VERSION = 1
 REFERENCE_FACTS_SCHEMA_VERSION = 1
+COLLISION_FACTS_SCHEMA_VERSION = 1
 _SYMBOL_FACTS_AVAILABLE = "available"
 _SYMBOL_FACTS_FAILURE = "failure"
 _SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
+_COLLISION_FACTS_AVAILABLE = "available"
+_COLLISION_TYPES = frozenset({"class", "function", "variable"})
+_COLLISION_FACT_FIELDS = frozenset(COLLISION_FACT_KEYS)
 _SYMBOL_FACT_FIELDS = frozenset(
     {
         "classes",
@@ -70,6 +79,58 @@ def _valid_reference_facts(value: object) -> bool:
     )
 
 
+def _valid_collision_fact_list(value: object, module_id: str) -> bool:
+    if not isinstance(value, list):
+        return False
+    for fact in value:
+        if not isinstance(fact, dict) or set(fact) != _COLLISION_FACT_FIELDS:
+            return False
+        if fact.get("name") is None or not isinstance(fact.get("name"), str):
+            return False
+        if fact.get("type") not in _COLLISION_TYPES:
+            return False
+        if fact.get("file") != module_id:
+            return False
+        if not isinstance(fact.get("file_path"), str) or not isinstance(fact.get("code"), str):
+            return False
+        if not all(
+            isinstance(fact.get(field), int) or fact.get(field) is None
+            for field in ("line_start", "line_end", "col_start", "col_end")
+        ):
+            return False
+    return True
+
+
+def _valid_collision_facts(value: object, module_id: str) -> bool:
+    return (
+        isinstance(value, dict)
+        and value.get("schema_version") == COLLISION_FACTS_SCHEMA_VERSION
+        and value.get("status") == _COLLISION_FACTS_AVAILABLE
+        and _valid_collision_fact_list(value.get("facts"), module_id)
+    )
+
+
+def _extract_collision_facts(tree: ast.AST, module_id: str, path: Path) -> list[dict]:
+    """Return cache/IPC-safe collision facts while the current AST is live."""
+    return [
+        fact.copy()
+        for fact in extract_module_collision_facts(tree, module_id, str(path.resolve()))
+    ]
+
+
+def assemble_collision_facts_or_fallback(
+    modules: dict[str, Module], collision_facts_by_module: dict[str, list[dict]] | None
+) -> dict[str, list[dict]]:
+    """Accept only complete indexed facts; otherwise preserve AST fallback semantics."""
+    facts = collision_facts_by_module or {}
+    if set(facts) == set(modules) and all(
+        _valid_collision_fact_list(facts.get(module_id), module_id)
+        for module_id in modules
+    ):
+        return facts
+    return extract_repository_collision_facts(modules)
+
+
 # ==========================================================
 # IMPORT EXTRACTION
 # ==========================================================
@@ -208,18 +269,28 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
 
     symbol_facts = None
     reference_facts = None
+    collision_facts = None
+    collision_facts_status = None
     if cached_data is not None:
         error = cached_data.get("error")
         imports = None if error else [ImportRef(**imp) for imp in cached_data.get("imports", [])]
 
         cached_facts = cached_data.get("symbol_facts") if not error else None
         cached_reference_facts = cached_data.get("reference_facts") if not error else None
+        cached_collision_facts = cached_data.get("collision_facts") if not error else None
         if _valid_symbol_facts(cached_facts):
             symbol_facts = cached_facts
         if _valid_reference_facts(cached_reference_facts):
             reference_facts = cached_reference_facts
-
-        if not error and (symbol_facts is None or reference_facts is None):
+        if _valid_collision_facts(cached_collision_facts, module_id):
+            collision_facts = cached_collision_facts
+            collision_facts_status = _COLLISION_FACTS_AVAILABLE
+
+        if not error and (
+            symbol_facts is None
+            or reference_facts is None
+            or collision_facts is None
+        ):
             try:
                 tree = parse_source(path)
             except SourceError as exc:
@@ -238,6 +309,8 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                         "error_type": type(exc).__name__,
                         "message": str(exc),
                     }
+                if collision_facts is None:
+                    collision_facts_status = "failure"
             else:
                 if symbol_facts is None:
                     try:
@@ -262,12 +335,30 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                     reference_facts = {
                         "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                         **extracted_reference,
-                    }
+                        }
+                if collision_facts is None:
+                    try:
+                        extracted_collision_facts = _extract_collision_facts(
+                            tree, module_id, path
+                        )
+                    except Exception:
+                        collision_facts_status = "failure"
+                    else:
+                        collision_facts = {
+                            "schema_version": COLLISION_FACTS_SCHEMA_VERSION,
+                            "status": _COLLISION_FACTS_AVAILABLE,
+                            "facts": extracted_collision_facts,
+                        }
+                        collision_facts_status = _COLLISION_FACTS_AVAILABLE
                 rewritten = dict(cached_data)
+                if collision_facts is None:
+                    rewritten.pop("collision_facts", None)
                 if _valid_symbol_facts(symbol_facts):
                     rewritten["symbol_facts"] = symbol_facts
                 if _valid_reference_facts(reference_facts):
                     rewritten["reference_facts"] = reference_facts
+                if _valid_collision_facts(collision_facts, module_id):
+                    rewritten["collision_facts"] = collision_facts
                 cache.set(path, rewritten)
     else:
         try:
@@ -298,6 +389,19 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
                     "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                     **extracted_reference,
                 }
+                try:
+                    extracted_collision_facts = _extract_collision_facts(
+                        tree, module_id, path
+                    )
+                except Exception:
+                    collision_facts_status = "failure"
+                else:
+                    collision_facts = {
+                        "schema_version": COLLISION_FACTS_SCHEMA_VERSION,
+                        "status": _COLLISION_FACTS_AVAILABLE,
+                        "facts": extracted_collision_facts,
+                    }
+                    collision_facts_status = _COLLISION_FACTS_AVAILABLE
         cache_data = {
             "imports": [dataclasses.asdict(imp) for imp in imports or []],
             "error": error,
@@ -306,6 +410,8 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
             cache_data["symbol_facts"] = symbol_facts
         if _valid_reference_facts(reference_facts):
             cache_data["reference_facts"] = reference_facts
+        if _valid_collision_facts(collision_facts, module_id):
+            cache_data["collision_facts"] = collision_facts
         cache.set(path, cache_data)
 
     return {
@@ -317,6 +423,8 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
         "filename": path.name,
         "symbol_facts": symbol_facts,
         "reference_facts": reference_facts,
+        "collision_facts": collision_facts,
+        "collision_facts_status": collision_facts_status,
     }
 
 
@@ -366,6 +474,8 @@ class RepositoryIndex:
 
     reference_facts_by_module: dict[str, dict] = dataclasses.field(default_factory=dict)
 
+    collision_facts_by_module: dict[str, list[dict]] = dataclasses.field(default_factory=dict)
+
 
 def index_repository(
     root: str, excludes: list[str] = None, extra_ignored_dirs: set = None, progress_callback=None
@@ -386,6 +496,7 @@ def index_repository(
     skipped: list[SkippedFile] = []
     symbol_facts_by_module: dict[str, dict] = {}
     reference_facts_by_module: dict[str, dict] = {}
+    collision_facts_by_module: dict[str, list[dict]] = {}
 
     ignored_dirs = set(DEFAULT_IGNORED_DIRS)
 
@@ -442,6 +553,9 @@ def index_repository(
                     symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
                 if res.get("reference_facts") is not None:
                     reference_facts_by_module[res["module_id"]] = res["reference_facts"]
+                cached_collision_facts = res.get("collision_facts")
+                if _valid_collision_facts(cached_collision_facts, res["module_id"]):
+                    collision_facts_by_module[res["module_id"]] = cached_collision_facts["facts"]
             completed += 1
             checkpoint(progress_callback, res["filename"], completed, total_files)
         return RepositoryIndex(
@@ -449,6 +563,7 @@ def index_repository(
             skipped=sorted(skipped, key=lambda item: item.path),
             symbol_facts_by_module=symbol_facts_by_module,
             reference_facts_by_module=reference_facts_by_module,
+            collision_facts_by_module=collision_facts_by_module,
         )
 
     with ProcessPoolExecutor() as executor:
@@ -481,6 +596,9 @@ def index_repository(
                     symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
                 if res.get("reference_facts") is not None:
                     reference_facts_by_module[res["module_id"]] = res["reference_facts"]
+                cached_collision_facts = res.get("collision_facts")
+                if _valid_collision_facts(cached_collision_facts, res["module_id"]):
+                    collision_facts_by_module[res["module_id"]] = cached_collision_facts["facts"]
 
             completed += 1
             try:
@@ -494,6 +612,7 @@ def index_repository(
         skipped=sorted(skipped, key=lambda item: item.path),
         symbol_facts_by_module=symbol_facts_by_module,
         reference_facts_by_module=reference_facts_by_module,
+        collision_facts_by_module=collision_facts_by_module,
     )
 
 
diff --git a/tests/test_collision_facts_fusion.py b/tests/test_collision_facts_fusion.py
new file mode 100644
index 0000000..4cefe56
--- /dev/null
+++ b/tests/test_collision_facts_fusion.py
@@ -0,0 +1,263 @@
+import json
+
+from contextor.core.analysis.cache_manager import CacheManager
+from contextor.core.domain.module import Module
+from contextor.core.symbol_engine import indexer
+from contextor.core.validator.collisions import (
+    compute_collisions_from_facts,
+    extract_repository_collision_facts,
+)
+
+
+def _cache_data(root, source):
+    manager = CacheManager(str(root))
+    return json.loads(manager._get_cache_file_path(source).read_text(encoding="utf-8"))["data"]
+
+
+def _serial(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _repo(tmp_path, text):
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source.write_text(text, encoding="utf-8")
+    return root, source
+
+
+def test_cold_index_facts_match_repository_extraction_and_materialize_all_fields(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    _serial(monkeypatch)
+    root, _ = _repo(
+        tmp_path,
+        "class Public:\n    def method(self):\n        pass\n\n"
+        "async def async_public():\n    return 1\n\n"
+        "MAXIMUM = 2\n\n"
+        "def main():\n    pass\n\n"
+        "def _private():\n    pass\n",
+    )
+
+    result = indexer.index_repository(str(root))
+    indexed = result.collision_facts_by_module
+    legacy = extract_repository_collision_facts(result.modules)
+
+    assert indexed == legacy
+    assert [fact["name"] for fact in indexed["module"]] == ["Public", "async_public", "MAXIMUM"]
+    for fact in indexed["module"]:
+        assert list(fact) == [
+            "name", "type", "file", "file_path", "code", "line_start", "line_end", "col_start", "col_end"
+        ]
+        assert fact["file"] == "module"
+        assert fact["file_path"] == str((root / "module.py").resolve())
+        assert isinstance(fact["code"], str)
+
+
+def test_warm_current_schema_has_zero_parse_and_collision_extraction(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    _serial(monkeypatch)
+    root, _ = _repo(tmp_path, "def public():\n    return 1\n")
+    indexer.index_repository(str(root))
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    def forbidden(*args, **kwargs):
+        raise AssertionError("unexpected warm extraction")
+
+    monkeypatch.setattr(indexer, "parse_source", forbidden)
+    monkeypatch.setattr(indexer, "extract_module_collision_facts", forbidden)
+    warm = indexer.index_repository(str(root))
+
+    assert warm.collision_facts_by_module["module"][0]["name"] == "public"
+
+
+def test_missing_collision_field_migrates_once_and_preserves_other_fact_families(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    _serial(monkeypatch)
+    root, source = _repo(tmp_path, "def public():\n    return 1\n")
+    seeded = indexer.index_repository(str(root))
+    data = _cache_data(root, source)
+    data.pop("collision_facts")
+    CacheManager(str(root)).set(source, data)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    parse_calls = []
+    collision_calls = []
+    real_parse = indexer.parse_source
+    real_extract = indexer.extract_module_collision_facts
+    monkeypatch.setattr(indexer, "parse_source", lambda path: (parse_calls.append(path) or real_parse(path)))
+    monkeypatch.setattr(
+        indexer,
+        "extract_module_collision_facts",
+        lambda *args, **kwargs: (collision_calls.append(args[1]) or real_extract(*args, **kwargs)),
+    )
+
+    migrated = indexer.index_repository(str(root))
+
+    assert len(parse_calls) == len(collision_calls) == 1
+    assert migrated.symbol_facts_by_module == seeded.symbol_facts_by_module
+    assert migrated.reference_facts_by_module == seeded.reference_facts_by_module
+    assert _cache_data(root, source)["collision_facts"]["status"] == "available"
+
+
+def test_failed_collision_migration_drops_invalid_envelope_and_retry_populates(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    _serial(monkeypatch)
+    root, source = _repo(tmp_path, "def public():\n    return 1\n")
+    seeded = indexer.index_repository(str(root))
+    data = _cache_data(root, source)
+    data["collision_facts"]["schema_version"] = 0
+    CacheManager(str(root)).set(source, data)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    real_extract = indexer.extract_module_collision_facts
+    monkeypatch.setattr(
+        indexer,
+        "extract_module_collision_facts",
+        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("transient")),
+    )
+    failed = indexer.index_repository(str(root))
+
+    persisted = _cache_data(root, source)
+    assert set(failed.modules) != set(failed.collision_facts_by_module)
+    assert failed.collision_facts_by_module == {}
+    assert "collision_facts" not in persisted
+    assert persisted["symbol_facts"] == seeded.symbol_facts_by_module["module"]
+    assert persisted["reference_facts"] == seeded.reference_facts_by_module["module"]
+
+    monkeypatch.setattr(
+        indexer,
+        "extract_module_collision_facts",
+        real_extract,
+    )
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    retried = indexer.index_repository(str(root))
+
+    assert retried.collision_facts_by_module["module"][0]["name"] == "public"
+    assert _cache_data(root, source)["collision_facts"]["status"] == "available"
+
+
+def test_schema_mismatch_and_source_change_reextract_once(tmp_path, isolated_dirs, monkeypatch):
+    _serial(monkeypatch)
+    root, source = _repo(tmp_path, "def old_name():\n    return 1\n")
+    indexer.index_repository(str(root))
+    data = _cache_data(root, source)
+    data["collision_facts"]["schema_version"] = 0
+    CacheManager(str(root)).set(source, data)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+
+    parse_calls = []
+    real_parse = indexer.parse_source
+    monkeypatch.setattr(indexer, "parse_source", lambda path: (parse_calls.append(path) or real_parse(path)))
+    mismatched = indexer.index_repository(str(root))
+    assert len(parse_calls) == 1
+    assert mismatched.collision_facts_by_module["module"][0]["name"] == "old_name"
+
+    source.write_text("def new_name():\n    return 2\n", encoding="utf-8")
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    parse_calls.clear()
+    changed = indexer.index_repository(str(root))
+    assert len(parse_calls) == 1
+    assert changed.collision_facts_by_module["module"][0]["name"] == "new_name"
+
+
+def test_valid_empty_collision_facts_persist_and_cover_module(tmp_path, isolated_dirs, monkeypatch):
+    _serial(monkeypatch)
+    root, source = _repo(tmp_path, "def _private():\n    pass\n")
+    result = indexer.index_repository(str(root))
+
+    assert result.collision_facts_by_module == {"module": []}
+    envelope = _cache_data(root, source)["collision_facts"]
+    assert envelope == {
+        "schema_version": indexer.COLLISION_FACTS_SCHEMA_VERSION,
+        "status": "available",
+        "facts": [],
+    }
+
+
+def test_collision_failure_is_not_cached_and_uses_full_domain_fallback(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    _serial(monkeypatch)
+    root, source = _repo(tmp_path, "def public():\n    return 1\n")
+
+    real_extract = indexer.extract_module_collision_facts
+    monkeypatch.setattr(
+        indexer,
+        "extract_module_collision_facts",
+        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("transient")),
+    )
+    failed = indexer.index_repository(str(root))
+
+    assert failed.collision_facts_by_module == {}
+    assert "collision_facts" not in _cache_data(root, source)
+
+    fallback_calls = []
+    monkeypatch.setattr(indexer, "extract_repository_collision_facts", lambda modules: (fallback_calls.append(modules) or {"module": []}))
+    assert indexer.assemble_collision_facts_or_fallback(failed.modules, failed.collision_facts_by_module) == {"module": []}
+    assert fallback_calls == [failed.modules]
+
+    monkeypatch.setattr(indexer, "extract_module_collision_facts", real_extract)
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    retried = indexer.index_repository(str(root))
+    assert retried.collision_facts_by_module["module"][0]["name"] == "public"
+
+
+def test_incomplete_or_invalid_side_table_never_merges_with_fallback(tmp_path, isolated_dirs, monkeypatch):
+    root, a = _repo(tmp_path, "def one():\n    return 1\n")
+    b = root / "other.py"
+    b.write_text("def two():\n    return 2\n", encoding="utf-8")
+    modules = {
+        "module": Module("module", "module.py", str(a), []),
+        "other": Module("other", "other.py", str(b), []),
+    }
+    fallback = {"module": [], "other": []}
+    monkeypatch.setattr(indexer, "extract_repository_collision_facts", lambda got: fallback)
+
+    assert indexer.assemble_collision_facts_or_fallback(modules, {"module": []}) is fallback
+    assert indexer.assemble_collision_facts_or_fallback(modules, {"module": [{"bad": "fact"}], "other": []}) is fallback
+
+
+def test_serial_and_process_pool_side_tables_match(tmp_path, isolated_dirs, monkeypatch):
+    root, _ = _repo(tmp_path, "def first():\n    return 1\n")
+    (root / "other.py").write_text("VALUE = 3\n", encoding="utf-8")
+    _serial(monkeypatch)
+    serial = indexer.index_repository(str(root))
+    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL")
+    pooled = indexer.index_repository(str(root))
+
+    assert pooled.collision_facts_by_module == serial.collision_facts_by_module
+    assert compute_collisions_from_facts(pooled.collision_facts_by_module) == []
+
+
+def test_full_facade_uses_complete_indexed_facts_without_repository_fallback(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    from contextor.core.api.facade import ContextorFacade
+    import contextor.core.api.facade as facade_module
+
+    _serial(monkeypatch)
+    root, _ = _repo(tmp_path, "def public():\n    return 1\n")
+    observed = []
+    real_assemble = facade_module.assemble_collision_facts_or_fallback
+
+    def track_assemble(modules, facts):
+        observed.append((set(modules), set(facts)))
+        return real_assemble(modules, facts)
+
+    monkeypatch.setattr(facade_module, "assemble_collision_facts_or_fallback", track_assemble)
+    monkeypatch.setattr(
+        indexer,
+        "extract_repository_collision_facts",
+        lambda modules: (_ for _ in ()).throw(AssertionError("unexpected fallback")),
+    )
+
+    errors, analysis_result = ContextorFacade.analyze_project(str(root))
+
+    assert errors == []
+    assert analysis_result.collision_facts == {"module": analysis_result.collision_facts["module"]}
+    assert observed == [({"module"}, {"module"})]
```

FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\api\facade.py
C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py
C:\Temp\Contextor_Repo\tests\test_collision_facts_fusion.py
DIFFS=SEE_COMPLETE_RAW_UNIFIED_DIFF_SECTION
FINAL_VERDICT=PASS
WARM_COLLISION_VISITOR_COUNT=0
WARM_COLLISION_FALLBACK_COUNT=0
WHOLE_ANALYSIS_BASELINE_MEDIAN_MS=8496.942524
WHOLE_ANALYSIS_CANDIDATE_MEDIAN_MS=7703.148690
WHOLE_ANALYSIS_DELTA_MS=-793.793834
CONTEXTOR_WORKSPACE_SYNC=verified
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\api\facade.py; C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py; C:\Temp\Contextor_Repo\tests\test_collision_facts_fusion.py
