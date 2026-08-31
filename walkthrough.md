# 0J7 automatic test-context map reuse

## Final verdict

`IMPLEMENTATION_VERDICT=FAIL`. Semantic parity and local work removal pass, but the required whole-analysis performance outcome is not trustworthy: baseline-first A/B improved by 99.300 ms, while the required reversed-order A/B regressed by 524.937 ms. The order effect exceeds the target; it is not credited to 0J7. The attempted implementation remains in the working tree for the requested follow-up decision.

## Contextor preflight and post-change evidence

Before editing, Contextor MCP at revision 93 (`canonical_state=fresh`, `workspace_sync=verified`) established the exact private path: `ContextorFacade.analyze_project` owns `RepositoryIndex` -> `execute_global_pipeline` -> `build_artifact_pipeline` -> `generate_artifact_usage_report`; the last function performed normal `discover_test_dirs(... allowed_python_paths=[module.path ...])` before `build_test_context_index`.

`index_repository` already assembles the selected successful current-run result domain in both serial and ProcessPool paths. `_process_single_file` already computes `test_candidate` for 0J4 test facts. Legacy allowed-path discovery starts with an empty root entry, lists all selected root Python names, and lists selected immediate `tests`/`test` directory names. `TestContextIndex.build` then applies root naming while preserving caller-supplied non-root mappings, including custom `specs`.

At post-change revision 107, watcher events from 93 are continuous (`resync_required=false`) and contain matching desktop-watcher updates for every changed production file and new test. `indexer`, `facade`, and `artifact_usage_report` report fresh canonical/workspace state (`workspace_sync=verified`), fresh module/graph/topology/artifact/cycle/collision families, no cycles/collisions, and no new layer violation. No restart was required. Top-level action/debt/hotspot families are deferred due no fresh producer; this is not workspace divergence.

## Implementation and semantics

`_process_single_file` exposes only an ephemeral current-run directory marker derived from its existing `test_candidate`, plus the root exception required by legacy raw listing. `index_repository` records it while already assembling successful results and creates deterministic `RepositoryIndex.automatic_test_dirs: Path -> frozenset[str]`. The map is neither cached nor persisted nor published in LIVE/canonical/report/MCP state.

The facade forwards it through the existing private report path. The artifact report uses it if supplied; missing-map callers still execute the old discovery fallback. Explicit `test_dirs` is never inferred from mapping contents and remains authoritative. No AST/source parsing, filesystem walk, rglob, additional module-domain pass, test-fact extraction, reverse lookup, artifact collection, or public schema changed.

## Validation

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q tests/test_test_context_discovery_map_0j7.py tests/test_test_discovery.py tests/test_test_context_fusion.py tests/test_test_context_reverse_index_0j6.py tests/test_artifact_report.py tests/test_index_fusion.py tests/test_pipeline.py
```

`57 passed in 27.42s`.

New coverage verifies empty root, root conventional/non-test names, `tests`, `test`, `conftest.py`, nested/custom/ignored/excluded/outside paths, relative and absolute paths, deterministic frozensets, serial/ProcessPool parity, 0J4 test-fact domain, supplied-map zero discovery, missing-map fallback, unchanged traceability, and explicit custom `specs` parity.

`py_compile` passed for all changed production/test files; `git diff --check` passed (CRLF warnings only).

## External A/B

External-only harness: `C:\Temp\Contextor_Benchmarks\0J7_discovery_map_20260831\harness.py`. It used disposable same-snapshot source copies, isolated cache/state/output/registry, ProcessPool enabled, detached LIVE, one cold plus six warm full analyses per group. A restored exact pre-0J7 source; B used current 0J7 source. It independently counted discovery, map assembly, index build, TestContextIndex build, whole analysis, directories/files, and equality.

Baseline-first raw warm whole ms: `8029.984, 6837.712, 7115.016, 6698.625, 7498.089, 7419.794`; median `7267.405`.

Candidate-first raw warm whole ms: `8324.863, 7216.405, 7119.804, 6749.803, 7668.310, 6309.352`; median `7168.104`; delta `-99.300`.

Baseline discovery raw ms: `190.883, 236.801, 169.303, 241.084, 210.287, 233.486`; median `221.886`. Candidate map raw ms: `5.786, 7.653, 7.245, 12.879, 7.501, 7.839`; median `7.577`. Baseline discovery calls `[1,1,1,1,1,1]`; candidate `[0,0,0,0,0,0]`; candidate map parity `[true,true,true,true,true,true]`; domain `2` directories / `107` raw files.

Required reverse order raw whole medians: baseline `6755.270`, candidate `7280.207`, delta `+524.937`; baseline discovery median `200.575`, candidate map median `6.750`. Thus local removed work is stable but total-wall reduction is not certified.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py`
- `C:\Temp\Contextor_Repo\contextor\core\api\facade.py`
- `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py`
- `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py`
- `C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py`
- `C:\Temp\Contextor_Repo\tests\test_test_context_discovery_map_0j7.py`

`walkthrough.md` is not counted. Accepted 0J6 changes in `test_context.py` and its untracked test are pre-existing and excluded.

## Complete raw unified diffs

```diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
@@ -416,6 +416,7 @@ class ContextorFacade:
             test_facts_by_path=index.test_facts_by_path,
+            automatic_test_dirs=index.automatic_test_dirs,
diff --git a/contextor/core/reporting_engine/pipeline.py b/contextor/core/reporting_engine/pipeline.py
@@ -50,6 +50,7 @@ def execute_global_pipeline(
+    automatic_test_dirs=None,
@@ -219,6 +220,7 @@ def execute_global_pipeline(
+        automatic_test_dirs=automatic_test_dirs,
diff --git a/contextor/core/reporting_engine/artifact_pipeline.py b/contextor/core/reporting_engine/artifact_pipeline.py
@@ -52,6 +52,7 @@ def build_artifact_pipeline(
+    automatic_test_dirs=None,
@@ -66,6 +67,7 @@ def build_artifact_pipeline(
+        automatic_test_dirs=automatic_test_dirs,
diff --git a/contextor/core/reporting_layer/artifact_usage_report.py b/contextor/core/reporting_layer/artifact_usage_report.py
@@ -706,6 +706,7 @@ def generate_artifact_usage_report(
+    automatic_test_dirs: dict | None = None,
@@ -801,10 +802,13 @@ def generate_artifact_usage_report(
-    test_dirs = discover_test_dirs(root_path, allowed_python_paths=[module.path for module in modules.values()])
+    if automatic_test_dirs is None:
+        test_dirs = discover_test_dirs(root_path, allowed_python_paths=[module.path for module in modules.values()])
+    else:
+        test_dirs = automatic_test_dirs
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
@@ -494,6 +494,11 @@ def _process_single_file(path_str: str, root_str: str) -> dict:
+        "automatic_test_context_directory": (str(path.parent) if test_candidate or path.parent == Path(root_str) else None),
@@ -547,6 +552,8 @@ class RepositoryIndex:
+    automatic_test_dirs: dict[Path, frozenset[str]] = dataclasses.field(default_factory=dict)
@@ -569,6 +576,20 @@ def index_repository(
+    automatic_test_dir_entries: dict[Path, set[str]] = {root_path: set()}
+    def record_automatic_test_context_path(result: dict) -> None:
+        directory = result.get("automatic_test_context_directory")
+        if directory is not None:
+            automatic_test_dir_entries.setdefault(Path(directory), set()).add(result["filename"])
+    def automatic_test_dirs() -> dict[Path, frozenset[str]]:
+        return {directory: frozenset(automatic_test_dir_entries[directory]) for directory in sorted(automatic_test_dir_entries)}
@@ -630,6 +651,7 @@ def index_repository(
+                record_automatic_test_context_path(res)
@@ -639,6 +661,7 @@ def index_repository(
+            automatic_test_dirs=automatic_test_dirs(),
@@ -676,6 +699,7 @@ def index_repository(
+                record_automatic_test_context_path(res)
@@ -691,6 +715,7 @@ def index_repository(
+        automatic_test_dirs=automatic_test_dirs(),
```

### Audit closure: complete raw unified diff for the 0J7 test file

```diff
diff --git a/tests/test_test_context_discovery_map_0j7.py b/tests/test_test_context_discovery_map_0j7.py
new file mode 100644
index 0000000..69d8f0c
--- /dev/null
+++ b/tests/test_test_context_discovery_map_0j7.py
@@ -0,0 +1,156 @@
+"""Parity coverage for RepositoryIndex automatic test-directory reuse."""
+
+from pathlib import Path
+
+from contextor.core.analysis import test_context as test_context_module
+from contextor.core.analysis.test_context import TestContextIndex, discover_test_dirs
+from contextor.core.reporting_layer import artifact_usage_report
+from contextor.core.symbol_engine import indexer
+
+
+def _write_fixture(root: Path) -> None:
+    files = {
+        "pkg/module.py": "class Target: pass\n",
+        "test_root.py": "from pkg.module import Target\nassert Target\n",
+        "root_test.py": "assert True\n",
+        "root_helper.py": "value = 1\n",
+        "tests/test_module.py": "from pkg.module import Target\nassert Target\n",
+        "tests/conftest.py": "fixture = 1\n",
+        "test/test_other.py": "assert True\n",
+        "tests/nested/test_nested.py": "assert True\n",
+        "specs/test_spec.py": "assert True\n",
+        "excluded/test_excluded.py": "assert True\n",
+        ".venv/tests/test_vendor.py": "assert True\n",
+    }
+    for relative, content in files.items():
+        path = root / relative
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_text(content, encoding="utf-8")
+
+
+def _legacy_dirs(root: Path, indexed: indexer.RepositoryIndex):
+    return discover_test_dirs(
+        str(root), allowed_python_paths=[module.path for module in indexed.modules.values()]
+    )
+
+
+def test_repository_index_map_matches_automatic_allowed_path_discovery_contract(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    root = tmp_path / "repo"
+    _write_fixture(root)
+    outside = tmp_path / "outside.py"
+    outside.write_text("assert True\n", encoding="utf-8")
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+    indexed = indexer.index_repository(str(root), excludes=["excluded"])
+    legacy = _legacy_dirs(root, indexed)
+    relative_legacy = discover_test_dirs(
+        str(root),
+        allowed_python_paths=[module.path for module in indexed.modules.values()]
+        + [str(outside)],
+    )
+    absolute_legacy = discover_test_dirs(
+        str(root),
+        allowed_python_paths=[module.absolute_path for module in indexed.modules.values()]
+        + [str(outside)],
+    )
+
+    assert indexed.automatic_test_dirs == legacy
+    assert relative_legacy == legacy
+    assert absolute_legacy == legacy
+    assert list(indexed.automatic_test_dirs) == sorted(indexed.automatic_test_dirs)
+    assert indexed.automatic_test_dirs[root] == frozenset(
+        {"test_root.py", "root_test.py", "root_helper.py"}
+    )
+    assert indexed.automatic_test_dirs[root / "tests"] == frozenset(
+        {"test_module.py", "conftest.py"}
+    )
+    assert indexed.automatic_test_dirs[root / "test"] == frozenset({"test_other.py"})
+    assert root / "tests" / "nested" not in indexed.automatic_test_dirs
+    assert root / "specs" not in indexed.automatic_test_dirs
+    assert root / "excluded" not in indexed.automatic_test_dirs
+    assert root / ".venv" / "tests" not in indexed.automatic_test_dirs
+    assert all(outside.name not in names for names in indexed.automatic_test_dirs.values())
+
+    context = TestContextIndex.build(root, test_dirs=indexed.automatic_test_dirs)
+    assert str(root / "root_helper.py") not in context.files_info
+    assert str(root / "test_root.py") in context.files_info
+    assert str(root / "root_test.py") in context.files_info
+    assert str(root / "tests" / "conftest.py") in context.files_info
+    assert str(root / "tests" / "nested" / "test_nested.py") not in context.files_info
+
+
+def test_repository_index_map_preserves_empty_root_entry(tmp_path, isolated_dirs, monkeypatch):
+    root = tmp_path / "empty"
+    root.mkdir()
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+    indexed = indexer.index_repository(str(root))
+
+    assert indexed.modules == {}
+    assert indexed.automatic_test_dirs == {root.resolve(): frozenset()}
+
+
+def test_repository_index_map_is_identical_for_serial_and_process_pool(tmp_path, isolated_dirs, monkeypatch):
+    root = tmp_path / "repo"
+    _write_fixture(root)
+
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    serial = indexer.index_repository(str(root), excludes=["excluded"])
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL")
+    pooled = indexer.index_repository(str(root), excludes=["excluded"])
+
+    assert pooled.automatic_test_dirs == serial.automatic_test_dirs
+    assert list(pooled.automatic_test_dirs) == list(serial.automatic_test_dirs)
+    assert set(pooled.test_facts_by_path) == {
+        str((directory / name).resolve())
+        for directory, names in pooled.automatic_test_dirs.items()
+        for name in names
+        if test_context_module.is_test_context_candidate(root, directory / name)
+    }
+
+
+def test_report_uses_supplied_automatic_map_and_missing_map_keeps_discovery_fallback(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    root = tmp_path / "repo"
+    _write_fixture(root)
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    indexed = indexer.index_repository(str(root), excludes=["excluded"])
+    original_discover = artifact_usage_report.discover_test_dirs
+    calls = []
+
+    def tracked_discover(*args, **kwargs):
+        calls.append((args, kwargs))
+        return original_discover(*args, **kwargs)
+
+    monkeypatch.setattr(artifact_usage_report, "discover_test_dirs", tracked_discover)
+    reused = artifact_usage_report.generate_artifact_usage_report(
+        indexed.modules,
+        str(root),
+        test_facts_by_path=indexed.test_facts_by_path,
+        automatic_test_dirs=indexed.automatic_test_dirs,
+    )
+    assert calls == []
+
+    fallback = artifact_usage_report.generate_artifact_usage_report(
+        indexed.modules,
+        str(root),
+        test_facts_by_path=indexed.test_facts_by_path,
+    )
+    assert len(calls) == 1
+    assert reused["test_traceability"] == fallback["test_traceability"]
+
+
+def test_explicit_custom_test_dirs_remain_authoritative(tmp_path):
+    root = tmp_path / "repo"
+    custom = root / "specs"
+    custom.mkdir(parents=True)
+    source = custom / "custom_case.py"
+    source.write_text("from pkg.module import Target\nassert Target\n", encoding="utf-8")
+
+    context = TestContextIndex.build(root, test_dirs={custom: frozenset({source.name})})
+
+    assert str(source) in context.files_info
+    assert context.find_test_files("pkg.module") == [str(source)]
```

IMPLEMENTATION_VERDICT=FAIL
AUTOMATIC_DISCOVERY_PARITY=PASS
EXPLICIT_TEST_DIRS_PARITY=PASS
BASELINE_DISCOVER_CALL_COUNT=1
CANDIDATE_DISCOVER_CALL_COUNT=0
CANDIDATE_MAP_BUILD_MEDIAN_MS=7.576809
BASELINE_DISCOVER_MEDIAN_MS=221.885906
CANDIDATE_TEST_FILE_COUNT=107
SAME_SNAPSHOT_BASELINE_MEDIAN_MS=7267.404656
SAME_SNAPSHOT_CANDIDATE_MEDIAN_MS=7168.104465
SAME_SNAPSHOT_DELTA_MS=-99.300191
CONTEXTOR_WORKSPACE_SYNC=verified; canonical_revision=107; continuous; resync_required=false
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py;C:\Temp\Contextor_Repo\contextor\core\api\facade.py;C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py;C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py;C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py;C:\Temp\Contextor_Repo\tests\test_test_context_discovery_map_0j7.py

## 0J7 paired performance-certification closure

No repository production or test file was modified for this closure. The existing source snapshot and external root `C:\Temp\Contextor_Benchmarks\0J7_discovery_map_20260831` were used. A was exact pre-0J7 source restoration (no map construction/transport; legacy discovery); B was the unchanged current 0J7 source. Both variants had independently warmed isolated cache/state/output/registry. ProcessPool was enabled; LIVE was detached. Decision observations were 12 interleaved full `ContextorFacade.analyze_project()` pairs with alternating order; no pair was discarded.

```text
PAIR=1 ORDER=AB A_WHOLE_MS=9339.174742 B_WHOLE_MS=8654.714077 DELTA_MS=-684.460665 A_DISCOVER_MS=228.117051 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=7.694630 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=2 ORDER=BA A_WHOLE_MS=5933.173909 B_WHOLE_MS=5577.625997 DELTA_MS=-355.547912 A_DISCOVER_MS=202.727581 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=5.722445 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=3 ORDER=AB A_WHOLE_MS=6642.276044 B_WHOLE_MS=6005.428274 DELTA_MS=-636.847770 A_DISCOVER_MS=206.229004 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=6.797005 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=4 ORDER=BA A_WHOLE_MS=7049.902851 B_WHOLE_MS=6574.945768 DELTA_MS=-474.957083 A_DISCOVER_MS=170.798244 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=10.894402 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=5 ORDER=AB A_WHOLE_MS=6872.532961 B_WHOLE_MS=5784.935445 DELTA_MS=-1087.597516 A_DISCOVER_MS=286.024969 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=9.324091 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=6 ORDER=BA A_WHOLE_MS=6137.067491 B_WHOLE_MS=6182.709674 DELTA_MS=45.642183 A_DISCOVER_MS=181.469224 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=8.341917 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=7 ORDER=AB A_WHOLE_MS=6134.390334 B_WHOLE_MS=6166.707360 DELTA_MS=32.317026 A_DISCOVER_MS=173.636244 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=7.973292 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=8 ORDER=BA A_WHOLE_MS=6535.633718 B_WHOLE_MS=6996.308889 DELTA_MS=460.675171 A_DISCOVER_MS=185.593490 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=5.594859 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=9 ORDER=AB A_WHOLE_MS=7149.884063 B_WHOLE_MS=5732.968506 DELTA_MS=-1416.915557 A_DISCOVER_MS=192.602203 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=5.533231 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=10 ORDER=BA A_WHOLE_MS=6255.770217 B_WHOLE_MS=6342.416494 DELTA_MS=86.646277 A_DISCOVER_MS=168.853444 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=7.165635 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=11 ORDER=AB A_WHOLE_MS=6369.704320 B_WHOLE_MS=6522.725584 DELTA_MS=153.021264 A_DISCOVER_MS=205.202826 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=6.896763 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
PAIR=12 ORDER=BA A_WHOLE_MS=6890.520653 B_WHOLE_MS=7093.754234 DELTA_MS=203.233581 A_DISCOVER_MS=251.218032 A_DISCOVER_COUNT=1 B_DISCOVER_COUNT=0 B_MAP_BUILD_MS=6.014808 MAP_PARITY=TRUE MODULE_COUNT=323 ERRORS_A=0 ERRORS_B=0
```

Paired median `B-A=-161.615443 ms`; paired mean `-306.232583 ms`; B was faster in `6/12` pairs. Legacy discovery median was `197.664892 ms`; candidate map-build median was `7.031199 ms`; stable local removed work was `190.633693 ms`. Parity was true, counts were A=1/B=0, module count was 323, and errors were zero in every pair.

However, the whole-wall effect remains order-correlated: AB pairs have four negative and two positive deltas (median -660.654218 ms), while BA pairs have two negative and four positive deltas (median +66.144230 ms). Per the certification rule, that correlation prevents converting the local causal evidence into a certified whole-analysis reduction. This is a measurement-certification outcome only, not a semantic/code failure; retain/revert requires explicit direction.

FINAL_VERDICT=PERFORMANCE_NOT_CERTIFIED
PAIRED_RUN_COUNT=12
PAIRS_CANDIDATE_FASTER=6/12
PAIRED_MEDIAN_DELTA_MS=-161.615443
PAIRED_MEAN_DELTA_MS=-306.232583
LEGACY_DISCOVER_MEDIAN_MS=197.664892
CANDIDATE_MAP_BUILD_MEDIAN_MS=7.031199
LOCAL_REMOVED_MS=190.633693
AUTOMATIC_DISCOVERY_PARITY=PASS
FILES_CHANGED=NONE
DIFFS=NONE

## 0J7 final owner-stage cost accounting closure

The earlier paired artifact did not contain raw `index_repository` timings, so the same external interleaved paired protocol was rerun solely to instrument that owner boundary: `C:\Temp\Contextor_Benchmarks\0J7_discovery_map_20260831\paired_index_results.json`. A was exact pre-0J7 source restoration; B was unchanged 0J7. Both variants had independent warm-ups, isolated warmed runtime state, ProcessPool enabled, and detached LIVE. No repository production/test file was changed, and no pytest, compilation, diff check, or Contextor discovery was rerun.

```text
PAIR=1 ORDER=AB A_INDEX_REPOSITORY_MS=5364.058282 B_INDEX_REPOSITORY_MS=4901.755600 INDEX_DELTA_MS=-462.302682 A_DISCOVER_MS=203.380248 B_MAP_BUILD_MS=7.104527 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=2 ORDER=BA A_INDEX_REPOSITORY_MS=2259.552820 B_INDEX_REPOSITORY_MS=2346.870342 INDEX_DELTA_MS=87.317522 A_DISCOVER_MS=232.418785 B_MAP_BUILD_MS=5.813873 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=3 ORDER=AB A_INDEX_REPOSITORY_MS=2725.357412 B_INDEX_REPOSITORY_MS=2139.995516 INDEX_DELTA_MS=-585.361896 A_DISCOVER_MS=199.342514 B_MAP_BUILD_MS=5.917996 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=4 ORDER=BA A_INDEX_REPOSITORY_MS=2166.588142 B_INDEX_REPOSITORY_MS=2393.092348 INDEX_DELTA_MS=226.504206 A_DISCOVER_MS=249.974787 B_MAP_BUILD_MS=6.000619 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=5 ORDER=AB A_INDEX_REPOSITORY_MS=2199.276724 B_INDEX_REPOSITORY_MS=2129.214537 INDEX_DELTA_MS=-70.062187 A_DISCOVER_MS=182.687046 B_MAP_BUILD_MS=9.010723 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=6 ORDER=BA A_INDEX_REPOSITORY_MS=2777.502308 B_INDEX_REPOSITORY_MS=2888.291878 INDEX_DELTA_MS=110.789570 A_DISCOVER_MS=253.752432 B_MAP_BUILD_MS=8.158093 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=7 ORDER=AB A_INDEX_REPOSITORY_MS=2471.372758 B_INDEX_REPOSITORY_MS=2264.381577 INDEX_DELTA_MS=-206.991181 A_DISCOVER_MS=166.252554 B_MAP_BUILD_MS=5.492176 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=8 ORDER=BA A_INDEX_REPOSITORY_MS=2496.433694 B_INDEX_REPOSITORY_MS=2275.968245 INDEX_DELTA_MS=-220.465449 A_DISCOVER_MS=215.675805 B_MAP_BUILD_MS=5.485811 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=9 ORDER=AB A_INDEX_REPOSITORY_MS=2443.889377 B_INDEX_REPOSITORY_MS=2670.971451 INDEX_DELTA_MS=227.082074 A_DISCOVER_MS=175.256911 B_MAP_BUILD_MS=6.611740 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=10 ORDER=BA A_INDEX_REPOSITORY_MS=2740.334525 B_INDEX_REPOSITORY_MS=2625.247622 INDEX_DELTA_MS=-115.086903 A_DISCOVER_MS=234.929718 B_MAP_BUILD_MS=5.514176 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=11 ORDER=AB A_INDEX_REPOSITORY_MS=1876.879394 B_INDEX_REPOSITORY_MS=2708.493188 INDEX_DELTA_MS=831.613794 A_DISCOVER_MS=168.394866 B_MAP_BUILD_MS=5.953203 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
PAIR=12 ORDER=BA A_INDEX_REPOSITORY_MS=2615.012732 B_INDEX_REPOSITORY_MS=2346.523720 INDEX_DELTA_MS=-268.489012 A_DISCOVER_MS=211.192693 B_MAP_BUILD_MS=5.991834 MAP_PARITY=TRUE ERRORS_A=0 ERRORS_B=0
```

The paired index delta median is `-92.574545 ms` and mean is `-37.121012 ms`. AB paired index deltas have median `-138.526684 ms`; BA paired index deltas have median `-13.884691 ms`. Both are negative, so `INDEX_ORDER_CORRELATION=NO` (there is normal magnitude variance but no sign-reversing order effect).

Map construction is within the `index_repository` boundary: the parent records it while assembling worker results, and the measured B index timer includes the worker-result marker, ProcessPool serialization/IPC, string/Path handling, parent assembly, and map construction. Therefore the non-double-counting equation applies:

`LOCAL_NET_DELTA_MS = PAIRED_MEDIAN_INDEX_DELTA_MS - LEGACY_DISCOVER_MEDIAN_MS`

`= -92.574545 - 207.286470 = -299.861015 ms`.

`CANDIDATE_MAP_BUILD_MEDIAN_MS=5.972518` is reported only as a decomposition of the already-measured B index cost, not added again. All parity values were true; A discovery count was one and B was zero in every pair; errors were zero. The measured B index cost does not consume the removed legacy discovery work; it is lower at the paired median. 0J7 is certified to keep on narrow owner-stage accounting, independent of noisy whole-analysis wall time.

FINAL_VERDICT=PASS
PAIR_COUNT=12
PAIRED_MEDIAN_INDEX_DELTA_MS=-92.574545
PAIRED_MEAN_INDEX_DELTA_MS=-37.121012
LEGACY_DISCOVER_MEDIAN_MS=207.286470
CANDIDATE_MAP_BUILD_MEDIAN_MS=5.972518
LOCAL_NET_DELTA_MS=-299.861015
INDEX_ORDER_CORRELATION=NO
AUTOMATIC_DISCOVERY_PARITY=PASS
FILES_CHANGED=NONE
DIFFS=NONE

REPORT_COMPLETENESS=PASS
MISSING_DIFFS=NONE
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py;C:\Temp\Contextor_Repo\contextor\core\api\facade.py;C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py;C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py;C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py;C:\Temp\Contextor_Repo\tests\test_test_context_discovery_map_0j7.py
