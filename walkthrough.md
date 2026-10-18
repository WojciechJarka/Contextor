# TASK
CONTEXTOR_B0G4C38B_INDEXER_SOURCE_FINGERPRINT_HANDOFF — controlled indexer data-contract implementation. No cycle-semantics FULL integration.

## HEAD_BEFORE / HEAD_AFTER / GIT_STATUS
HEAD_BEFORE=77e348c40615c0a48e6ed5a297e58986a26c34f4
HEAD_AFTER=77e348c40615c0a48e6ed5a297e58986a26c34f4
GIT_STATUS before: clean. After: `M contextor/core/symbol_engine/indexer.py`, `M tests/test_index_fusion.py`, plus this walkthrough report. Previous C38A/C38A1 files were already present in HEAD and were not changed. No staging, commit, reset or checkout.

## PRECHECK
DIRECT_EVIDENCE: Contextor MCP first and documentation read. `get_symbol_implementation` resolved complete current `_process_single_file` (`C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py:333-906`), `RepositoryIndex` (937-961), `index_repository` (964-1999), `SourceSnapshot` (`C:\Temp\Contextor_Repo\contextor\core\source.py:39-42`), `CacheManager` (`C:\Temp\Contextor_Repo\contextor\core\analysis\cache_manager.py:33-217`), all `workspace_sync=verified` at LIVE 485. Contextor source ranges confirmed warm success at indexer.py:532-581, final worker return at 878-906, inline merge/return at 1718-1768, process-pool merge/return at 1853-1999, and test anchors in `C:\Temp\Contextor_Repo\tests\test_index_fusion.py`. Contextor module context identified 34 inbound consumers of indexer, including facade and incremental preparation, and 14 outbound dependencies. Literal Git/source check after Contextor found exact approved anchors and clean HEAD. No material drift.
Before edit: LIVE revision 485, activity epoch `bbd40ce1942841df94718acedc12561f`, continuous events, resync_required=false, fresh syntax 0, collisions 0, structural cycle paths 16. Authority checked with read-only endpoint and `LiveStateClient(is_owner=False)`; no owner operation.

## FILES_CHANGED
- `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py`
- `C:\Temp\Contextor_Repo\tests\test_index_fusion.py`
- `walkthrough.md` report overwritten, excluded from source/test list.

## WORKER_COLD_RETURN / WORKER_WARM_RETURN / SOURCE_HASH_IDENTITY
CONTRACT_PROVED: Both successful `_process_single_file` dictionaries now carry `source_fingerprint=source_snapshot.source_fingerprint` (indexer.py:548 and 882 after edit). Read and parse error dictionaries remain errors and do not carry successful module evidence. Warm-cache success returns at the early branch without invoking `parse_source_snapshot`; cold/partial-cache final return reuses the same `SourceSnapshot`. `read_source_snapshot` in `source.py:60-71` hashes exact bytes with `hashlib.sha256(raw).hexdigest()`. `CacheManager.get` already receives `source_snapshot.raw` at indexer.py:498. No new hash, read or parse call added.

## REPOSITORY_INDEX_SCHEMA / INLINE_COLLECTION / PROCESS_POOL_COLLECTION
`RepositoryIndex` remains `@dataclasses.dataclass(frozen=True)` and appends only optional `source_fingerprints_by_module: dict[str,str]` after existing fields (indexer.py:969). Existing positional and keyword constructors retain their field order and default. `index_repository` initializes a local mapping and `record_indexed_source_fingerprint` validates nonempty exact string module ID and lowercase 64-character SHA-256; missing/invalid successful-worker evidence raises ValueError. Inline and process-pool success branches each invoke helper once after `res["error"]` check, independent of optional fact availability. Both returns sort the mapping and preserve the exact `modules` key domain. Process-pool worker transport contains only the fingerprint string, not raw bytes, SourceSnapshot or AST.

## EXCLUDED_AND_SKIPPED_POLICY / OPTIONAL_FACT_FAILURE_POLICY
File discovery excludes paths before tasks (indexer.py:1680-1705). Read/parse failures append `SkippedFile` after `res["error"]` and never record a fingerprint. Successful modules are recorded regardless of symbol/reference/lineage optional extraction output. Targeted failure test preserves existing symbol-failure status and no negative symbol cache, while asserting the module's fingerprint remains present.

## SOURCE_GENERATION_LIMITATION / NO_ADDITIONAL_SOURCE_IO / NO_AST_TRANSPORT
The map proves exact bytes read by each successful indexing worker, including cache hits. It is not an atomic repository-wide generation, does not prove simultaneous existence of all files, does not bind a future cycle cohort, and does not certify LIVE publication or runtime safety. `NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY` was not changed. NO_ADDITIONAL_SOURCE_IO=PASS by source diff: no new reader/hash/parse call. NO_AST_TRANSPORT=PASS by source diff: only primitive string added to worker result and mapping.

## TARGETED_TEST_RESULTS / WARM_CACHE_PARSE_EVIDENCE / PROCESS_POOL_TEST_EVIDENCE
Targeted command: `.venv\Scripts\python.exe -B -m pytest -q tests/test_index_fusion.py tests/test_indexer_profile_evidence.py tests/analysis/test_cache_manager_content_hash.py tests/test_cycle_semantics_source_cohort.py tests/test_cycle_semantics_contracts.py` → 61 passed in 8.64s. No full suite or real Contextor repository FULL analysis.
New tests cover exact CRLF/LF raw-byte SHA on cold and warm inline index, body-only source change with unchanged imports and subsequent warm index, skipped parse failure/excluded path absence, valid fingerprint despite optional symbol extraction failure, and legacy positional construction. Existing `test_reused_indexer_pool_uses_current_parent_cache_root` asserts exact first/second hashes and differing content across real process-pool reuse. WARM_CACHE_PARSE_EVIDENCE=PASS: new cold/warm test monkeypatches `parse_source_snapshot` to fail if called; warm index succeeds. Existing profile/cache tests passed. PROCESS_POOL_TEST_EVIDENCE=PASS in that named existing test and full targeted run.

## LIVE_AUTHORITY_BEFORE_AFTER / LIVE_REVISION_BEFORE_AFTER / ACTIVITY_EPOCH_BEFORE_AFTER / EVENT_CONTINUITY / WORKSPACE_SYNC
Read-only authority before/after identical: repo_id `ctx_8efc50d8`; root `C:\Temp\Contextor_Repo`; runtime_domain_id `rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654`; service_instance_id `6f13273feccb46cb9c23fbbfee03afe1`; lease_generation 31; service_pid 11632; process_start_identity 134367226998365614; endpoint_fingerprint `1367eadf1a11448d1a74eec69518da568d80ee42be8f16ce15e54998e989fcbd`. No secrets printed. LIVE_REVISION_BEFORE_AFTER=485→487. ACTIVITY_EPOCH_BEFORE_AFTER=`bbd40ce1942841df94718acedc12561f` unchanged. Contextor `get_live_events(after_revision=485)` observed desktop_watcher UPDATED indexer.py at 486 and test_index_fusion.py at 487; continuity continuous, resync_required=false. Both modules at revision 487 `workspace_sync=verified`, canonical_state=fresh, graph/topology/cycles/collisions fresh.

## COLLISIONS_BEFORE_AFTER / STRUCTURAL_CYCLES_BEFORE_AFTER / NEW_DEPENDENCY_CYCLES
Collisions 0→0; structural cycle paths 16→16, both fresh. No new production import added; Contextor LIVE graph/cycle diagnostics after watcher remain fresh and unchanged. NEW_DEPENDENCY_CYCLES=0 observed in current structural cycle count; no new dependency cycle indicated.

MCP_SERVER_RESTART_REQUIRED=NO
DESKTOP_LIVE_RESTART_REQUIRED=NO

## FINAL_VERDICT
B0G4C38B_PASS. Complete successful-module fingerprint map across cold/warm/inline/process-pool paths, focused tests PASS, stable authority and diagnostics, and both files synchronized. No extra source I/O or AST transport. STOP; await `proceduj`.

## FULL_DIFFS
Exact current-task diffs for every modified source/test file follow. No historical C38A/C38A1 diffs included.

### contextor/core/symbol_engine/indexer.py
```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index f900ee7..5e86ec5 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -545,6 +545,9 @@ def _process_single_file(
         ):
             return {
                 "module_id": module_id,
+                "source_fingerprint": (
+                    source_snapshot.source_fingerprint
+                ),
                 "path": str(rel),
                 "absolute_path": str(path.resolve()),
                 "imports": imports,
@@ -876,6 +879,9 @@ def _process_single_file(
 
     return {
         "module_id": module_id,
+        "source_fingerprint": (
+            source_snapshot.source_fingerprint
+        ),
         "path": str(rel),
         "absolute_path": str(path.resolve()),
         "imports": imports,
@@ -960,6 +966,10 @@ class RepositoryIndex:
 
     automatic_test_dirs: dict[Path, frozenset[str]] = dataclasses.field(default_factory=dict)
 
+    source_fingerprints_by_module: dict[str, str] = (
+        dataclasses.field(default_factory=dict)
+    )
+
 
 def index_repository(
     root: str, excludes: list[str] = None, extra_ignored_dirs: set = None, progress_callback=None
@@ -986,6 +996,7 @@ def index_repository(
     symbol_facts_by_module: dict[str, dict] = {}
     reference_facts_by_module: dict[str, dict] = {}
     lineage_facts_by_source: dict[str, ExtractedLineageSourceFacts] = {}
+    source_fingerprints_by_module: dict[str, str] = {}
     file_tasks = 0
     source_parse_calls = 0
     source_parse_failures = 0
@@ -1078,6 +1089,36 @@ def index_repository(
             for directory in sorted(automatic_test_dir_entries)
         }
 
+    def record_indexed_source_fingerprint(
+        result: dict,
+    ) -> None:
+        module_id = result.get("module_id")
+        fingerprint = result.get("source_fingerprint")
+
+        if (
+            type(module_id) is not str
+            or not module_id
+        ):
+            raise ValueError(
+                "Indexed module identity is invalid"
+            )
+
+        if (
+            type(fingerprint) is not str
+            or len(fingerprint) != 64
+            or any(
+                character not in "0123456789abcdef"
+                for character in fingerprint
+            )
+        ):
+            raise ValueError(
+                "Indexed source fingerprint is missing or invalid"
+            )
+
+        source_fingerprints_by_module[
+            module_id
+        ] = fingerprint
+
     def record_file_task_evidence(
         result: dict,
         *,
@@ -1731,6 +1772,7 @@ def index_repository(
                     absolute_path=res.get("absolute_path", res["path"]),
                     imports=res["imports"],
                 )
+                record_indexed_source_fingerprint(res)
                 if res.get("symbol_facts") is not None:
                     symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
                 if res.get("reference_facts") is not None:
@@ -1759,6 +1801,11 @@ def index_repository(
             collision_facts_by_module=collision_facts_by_module,
             test_facts_by_path=test_facts_by_path,
             automatic_test_dirs=automatic_test_dirs(),
+            source_fingerprints_by_module=dict(
+                sorted(
+                    source_fingerprints_by_module.items()
+                )
+            ),
         )
 
     pool_scope_started = time.monotonic()
@@ -1874,6 +1921,7 @@ def index_repository(
                     ),
                     imports=res["imports"],
                 )
+                record_indexed_source_fingerprint(res)
 
                 if res.get("symbol_facts") is not None:
                     symbol_facts_by_module[
@@ -1996,6 +2044,11 @@ def index_repository(
         collision_facts_by_module=collision_facts_by_module,
         test_facts_by_path=test_facts_by_path,
         automatic_test_dirs=automatic_test_dirs(),
+        source_fingerprints_by_module=dict(
+            sorted(
+                source_fingerprints_by_module.items()
+            )
+        ),
     )
 
 
```
### tests/test_index_fusion.py
```diff
diff --git a/tests/test_index_fusion.py b/tests/test_index_fusion.py
index 0489a65..bc892dc 100644
--- a/tests/test_index_fusion.py
+++ b/tests/test_index_fusion.py
@@ -1,3 +1,4 @@
+import hashlib
 import json
 
 from contextor.core.analysis.cache_manager import CacheManager
@@ -53,15 +54,16 @@ def test_reused_indexer_pool_uses_current_parent_cache_root(
             str(first_cache),
         )
 
-        source.write_text(
-            "def first():\n    return 1\n",
-            encoding="utf-8",
-        )
+        first_bytes = b"def first():\n    return 1\n"
+        source.write_bytes(first_bytes)
 
         first = indexer.index_repository(
             str(root)
         )
 
+        first_fingerprint = hashlib.sha256(first_bytes).hexdigest()
+        assert first.source_fingerprints_by_module["module"] == first_fingerprint
+
         assert (
             first
             .symbol_facts_by_module["module"]
@@ -81,15 +83,17 @@ def test_reused_indexer_pool_uses_current_parent_cache_root(
             str(second_cache),
         )
 
-        source.write_text(
-            "def second():\n    return 2\n",
-            encoding="utf-8",
-        )
+        second_bytes = b"def second():\n    return 2\n"
+        source.write_bytes(second_bytes)
 
         second = indexer.index_repository(
             str(root)
         )
 
+        second_fingerprint = hashlib.sha256(second_bytes).hexdigest()
+        assert second.source_fingerprints_by_module["module"] == second_fingerprint
+        assert first_fingerprint != second_fingerprint
+
         assert (
             second
             .symbol_facts_by_module["module"]
@@ -354,3 +358,142 @@ def test_symbol_failure_keeps_module_and_retries_without_negative_cache(
     indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
     retried = indexer.index_repository(str(root))
     assert retried.symbol_facts_by_module["module"]["status"] == "available"
+
+
+def test_index_source_fingerprint_cold_warm_raw_bytes(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    first = root / "alpha.py"
+    second = root / "beta.py"
+    first_bytes = b"import beta\r\ndef alpha():\r\n    return beta.value\r\n"
+    second_bytes = b"value = 7\n"
+    first.write_bytes(first_bytes)
+    second.write_bytes(second_bytes)
+
+    cold = indexer.index_repository(str(root))
+    expected = {
+        "alpha": hashlib.sha256(first_bytes).hexdigest(),
+        "beta": hashlib.sha256(second_bytes).hexdigest(),
+    }
+    assert set(cold.modules) == set(expected)
+    assert cold.source_fingerprints_by_module == expected
+    assert list(cold.source_fingerprints_by_module) == sorted(expected)
+
+    def forbidden_parse(*_args, **_kwargs):
+        raise AssertionError("warm index reparsed a source")
+
+    with monkeypatch.context() as scoped:
+        scoped.setattr(indexer, "parse_source_snapshot", forbidden_parse)
+        warm = indexer.index_repository(str(root))
+
+    assert warm.source_fingerprints_by_module == expected
+    assert [item.module for item in warm.modules["alpha"].imports] == ["beta"]
+    assert warm.symbol_facts_by_module["alpha"]["status"] == "available"
+    assert warm.reference_facts_by_module["alpha"]["status"] == "available"
+
+
+def test_index_source_fingerprint_body_only_change(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "alpha.py"
+    other = root / "beta.py"
+    original_bytes = b"import beta\ndef answer():\n    return 1\n"
+    changed_bytes = b"import beta\ndef answer():\n    return 2\n"
+    other_bytes = b"value = 7\n"
+    source.write_bytes(original_bytes)
+    other.write_bytes(other_bytes)
+
+    initial = indexer.index_repository(str(root))
+    source.write_bytes(changed_bytes)
+    changed = indexer.index_repository(str(root))
+
+    assert changed.source_fingerprints_by_module["alpha"] == hashlib.sha256(changed_bytes).hexdigest()
+    assert changed.source_fingerprints_by_module["alpha"] != initial.source_fingerprints_by_module["alpha"]
+    assert changed.source_fingerprints_by_module["beta"] == initial.source_fingerprints_by_module["beta"]
+    assert changed.source_fingerprints_by_module["beta"] == hashlib.sha256(other_bytes).hexdigest()
+    assert changed.modules["alpha"].imports == initial.modules["alpha"].imports
+
+    warm = indexer.index_repository(str(root))
+    assert warm.source_fingerprints_by_module == changed.source_fingerprints_by_module
+
+
+def test_index_source_fingerprint_skipped_and_excluded(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    valid_bytes = b"value = 1\n"
+    (root / "valid.py").write_bytes(valid_bytes)
+    (root / "invalid.py").write_bytes(b"def broken(:\n")
+    (root / "excluded.py").write_bytes(b"value = 2\n")
+
+    result = indexer.index_repository(str(root), excludes=["excluded.py"])
+
+    assert set(result.modules) == {"valid"}
+    assert {item.path for item in result.skipped} == {"invalid.py"}
+    assert list(result.source_fingerprints_by_module) == ["valid"]
+    assert result.source_fingerprints_by_module["valid"] == hashlib.sha256(valid_bytes).hexdigest()
+    assert set(result.source_fingerprints_by_module) == set(result.modules)
+
+
+def test_index_source_fingerprint_survives_optional_fact_failure(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    root = tmp_path / "repo"
+    root.mkdir()
+    source = root / "module.py"
+    source_bytes = b"import os\ndef hello():\n    return os.name\n"
+    source.write_bytes(source_bytes)
+
+    def fail_symbols(path, *, tree=None):
+        raise RuntimeError("visitor failed")
+
+    monkeypatch.setattr(indexer, "extract_file_symbols", fail_symbols)
+    result = indexer.index_repository(str(root))
+
+    assert "module" in result.modules
+    assert [item.module for item in result.modules["module"].imports] == ["os"]
+    assert result.symbol_facts_by_module["module"]["status"] == "failure"
+    assert "symbol_facts" not in _cache_payload(root, source)["data"]
+    assert result.source_fingerprints_by_module == {
+        "module": hashlib.sha256(source_bytes).hexdigest()
+    }
+
+
+def test_repository_index_legacy_construction():
+    modules = {}
+    skipped = []
+    symbol_facts = {"symbol": {"status": "available"}}
+    reference_facts = {"reference": {"status": "available"}}
+    lineage_facts = {}
+    collision_facts = {}
+    test_facts = {}
+    test_dirs = {}
+    result = indexer.RepositoryIndex(
+        modules,
+        skipped,
+        symbol_facts,
+        reference_facts,
+        lineage_facts,
+        collision_facts,
+        test_facts,
+        test_dirs,
+    )
+
+    assert result.modules is modules
+    assert result.skipped is skipped
+    assert result.symbol_facts_by_module is symbol_facts
+    assert result.reference_facts_by_module is reference_facts
+    assert result.lineage_facts_by_source is lineage_facts
+    assert result.collision_facts_by_module is collision_facts
+    assert result.test_facts_by_path is test_facts
+    assert result.automatic_test_dirs is test_dirs
+    assert result.source_fingerprints_by_module == {}
```
