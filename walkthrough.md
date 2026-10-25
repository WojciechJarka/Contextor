# CONTEXTOR_P1D2D_FLAT_MODULE_FIX

## ROOT_CAUSE_DIAGNOSTIC

- DIRECT_EVIDENCE: The required single diagnostic test failed at the expected positive-status assertion. The local `result` was `OriginalWorkerManifestPreparation(status='UNAVAILABLE', reason='P1C0_SOURCE_EVIDENCE_UNAVAILABLE', manifest=None, source_modules=())`.
- DIRECT_EVIDENCE: Its graph contained `pkg.a`/`pkg.b` with `pkg.helper`; captured indexing and filesystem-stable semantic cohort assertions passed before preparation returned unavailable.
- INFERENCE: This matches the architect-specified restricted flat-module P1C0 model boundary. No production contract was broadened.

## CONFIRMED_PRE_EDIT_FAILURE_REASON

- DIRECT_EVIDENCE: Exact reason: `P1C0_SOURCE_EVIDENCE_UNAVAILABLE`.
- Diagnostic test: 1 failed in 1.83s. The failure was the expected diagnostic, not treated as a stop condition by the correction instructions.

## NATIVE_CODEX_LITERAL_CORRECTIONS

- DIRECT_EVIDENCE: Applied only the supplied literal replacements to `tests/test_original_worker_real_pipeline_preparation.py`: flat module IDs and source fixtures, matching positive/missing/drift assertions, the model-only classification assertion, plus T08 dotted-import and T09 function-definition fail-closed tests.
- CODE_PATH_PROVED: No production file was changed. The original bounded P1C0 model remains in force.

## FILES_CHANGED

- `tests/test_original_worker_real_pipeline_preparation.py`
- `walkthrough.md` (this report)

## ACTUAL_TEST_FILE_DIFF

Full actual diff against the pre-correction file:

```diff
diff --git a/tests/test_original_worker_real_pipeline_preparation.py b/tests/test_original_worker_real_pipeline_preparation.py
index dae7182..7e8f0b2 100644
--- a/tests/test_original_worker_real_pipeline_preparation.py
+++ b/tests/test_original_worker_real_pipeline_preparation.py
@@ -23,10 +23,9 @@ from contextor.core.symbol_engine.indexer import index_repository
 
 
 _SELECTED = frozenset({
-    "pkg.__init__",
-    "pkg.a",
-    "pkg.b",
-    "pkg.helper",
+    "a",
+    "b",
+    "helper",
 })
 
 
@@ -37,23 +36,19 @@ def _inline_by_default(monkeypatch):
 
 def _repo(tmp_path):
     root = tmp_path / "repo"
-    pkg = root / "pkg"
-    pkg.mkdir(parents=True)
+    root.mkdir()
 
-    (pkg / "__init__.py").write_bytes(b"")
-    (pkg / "a.py").write_bytes(
-        b"import pkg.b\n"
-        b"import pkg.helper\n"
-        b"def fa():\n"
-        b"    return 1\n"
+    (root / "a.py").write_bytes(
+        b"import b\n"
+        b"import helper\n"
+        b"value = 1\n"
     )
-    (pkg / "b.py").write_bytes(
-        b"import pkg.a\n"
-        b"def fb():\n"
-        b"    return 2\n"
+    (root / "b.py").write_bytes(
+        b"import a\n"
+        b"value = 2\n"
     )
-    (pkg / "helper.py").write_bytes(b"value = 1\n")
-    (pkg / "unrelated.py").write_bytes(b"value = 999\n")
+    (root / "helper.py").write_bytes(b"value = 3\n")
+    (root / "unrelated.py").write_bytes(b"value = 999\n")
 
     return root
 
@@ -96,7 +91,7 @@ def test_p1d2d_t01_real_component_chain_prepares_only(
     assert snapshot.coverage_status == (
         "FILESYSTEM_STABLE_NON_ATOMIC"
     )
-    assert snapshot.cyclic_modules == ("pkg.a", "pkg.b")
+    assert snapshot.cyclic_modules == ("a", "b")
     assert snapshot.graph_sha256 == fingerprint_hard_edges(
         graph.hard_edges
     )
@@ -111,15 +106,18 @@ def test_p1d2d_t01_real_component_chain_prepares_only(
     )
     assert result.manifest.source_manifest_sha256 is not None
     assert result.manifest.components[0].members == (
-        "pkg.a",
-        "pkg.b",
+        "a",
+        "b",
+    )
+    assert result.manifest.components[0].model_classification == (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
     )
     assert {
-        "pkg.a",
-        "pkg.b",
-        "pkg.helper",
+        "a",
+        "b",
+        "helper",
     }.issubset(result.source_modules)
-    assert "pkg.unrelated" not in result.source_modules
+    assert "unrelated" not in result.source_modules
 
 
 def test_p1d2d_t02_warm_cache_keeps_preparation_valid(
@@ -162,9 +160,8 @@ def test_p1d2d_t04_missing_reachable_capture_fails_closed(
     root = _repo(tmp_path)
 
     selected = frozenset({
-        "pkg.__init__",
-        "pkg.a",
-        "pkg.b",
+        "a",
+        "b",
     })
     index, graph, snapshot = _analyze_components(
         root,
@@ -175,7 +172,7 @@ def test_p1d2d_t04_missing_reachable_capture_fails_closed(
 
     assert result.status == "UNAVAILABLE"
     assert result.reason == (
-        "BINDING_CLOSURE_CAPTURE_MISSING:pkg.helper"
+        "BINDING_CLOSURE_CAPTURE_MISSING:helper"
     )
     assert result.manifest is None
     assert result.source_modules == ()
@@ -192,11 +189,10 @@ def test_p1d2d_t05_cyclic_source_drift_fails_closed(
     )
     graph = build_graph(index.modules)
 
-    (root / "pkg" / "a.py").write_bytes(
-        b"import pkg.b\n"
-        b"import pkg.helper\n"
-        b"def fa():\n"
-        b"    return 99\n"
+    (root / "a.py").write_bytes(
+        b"import b\n"
+        b"import helper\n"
+        b"value = 99\n"
     )
 
     snapshot = materialize_cycle_semantics(
@@ -252,3 +248,71 @@ def test_p1d2d_t07_real_process_pool_component_chain(
         assert result.manifest is not None
     finally:
         terminate_active_process_pools(timeout=1.0)
+
+
+def test_p1d2d_t08_dotted_imports_remain_fail_closed(
+    tmp_path, isolated_dirs,
+):
+    root = tmp_path / "package_repo"
+    package = root / "pkg"
+    package.mkdir(parents=True)
+
+    (package / "__init__.py").write_bytes(b"")
+    (package / "a.py").write_bytes(
+        b"import pkg.b\n"
+    )
+    (package / "b.py").write_bytes(
+        b"import pkg.a\n"
+    )
+
+    index = index_repository(
+        str(root),
+        source_capture_module_ids=frozenset({
+            "pkg.__init__",
+            "pkg.a",
+            "pkg.b",
+        }),
+    )
+
+    graph = build_graph(index.modules)
+
+    snapshot = materialize_cycle_semantics(
+        root,
+        graph.hard_edges,
+        {
+            module_id: module.path
+            for module_id, module in index.modules.items()
+        },
+        index.source_fingerprints_by_module,
+    )
+
+    result = _prepare(index, graph, snapshot)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    )
+    assert result.manifest is None
+
+
+def test_p1d2d_t09_function_definition_remains_fail_closed(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+
+    (root / "a.py").write_bytes(
+        b"import b\n"
+        b"import helper\n"
+        b"def fa():\n"
+        b"    return 1\n"
+    )
+
+    index, graph, snapshot = _analyze_components(root)
+
+    result = _prepare(index, graph, snapshot)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
+    )
+    assert result.manifest is None
```

## P1D2D_TEST_RESULTS

- DIRECT_EVIDENCE: All nine tests in `tests/test_original_worker_real_pipeline_preparation.py` passed: `9 passed in 8.93s`.

## FOCUSED_NON_REGRESSION

- DIRECT_EVIDENCE: Exact focused suite passed: `173 passed in 27.60s` across the nine P1D2D cases and the seven specified existing test files.

## PY_COMPILE_RESULT

- DIRECT_EVIDENCE: `py_compile tests/test_original_worker_real_pipeline_preparation.py` returned exit 0.
- DIRECT_EVIDENCE: `git diff --check -- tests/test_original_worker_real_pipeline_preparation.py` returned exit 0. Git emitted only an LF-to-CRLF checkout warning. Repo-wide `git diff --check` reports trailing spaces in blank context lines inside the mandatory ACTUAL_TEST_FILE_DIFF block in `walkthrough.md`.

## P1C0_MODEL_RESTRICTIONS_PRESERVED

- CONTRACT_PROVED by passing tests: the flat import and assignment fixture reaches `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`, which remains model-only. New T08 preserves fail-closed behavior for dotted imports; T09 preserves fail-closed behavior for function definitions.
- No production scenario or initialization-model code was modified.

## SOURCE_PROVENANCE_AUTHORITY_LIMITS

- CODE_PATH_PROVED: Tests use isolated temporary repositories, real index/graph/materialization components, and the preparation bridge. Successful output remains `PREPARED_UNPUBLISHED_NON_ATOMIC`; no receipt or canonical publication is produced.
- No claim of cross-file atomicity, source freshness after preparation, canonical generation certification, installed LIVE adoption or runtime import safety.

## UNVERIFIED_RUNTIME_BEHAVIOR

- UNKNOWN: Active runtime loaded-code adoption was not tested. No FULL analysis of the user's repository, LIVE restart/reload, publication, receipt sealing or manual `update_file` was performed.

## FINAL_VERDICT

P1D2D correction completed. The diagnostic reason matched the architect's expectation; the literal flat-fixture corrections and two fail-closed regression tests passed. The requested focused suite passed 173/173. Watcher and canonical read results follow below.

### CANONICAL_WATCHER_OBSERVATIONS

- DIRECT_EVIDENCE: Before correction the canonical revision was 676. Watcher emitted revision 677 `UPDATED` for the test file (`blast_radius_state=fresh`), then revision 678 `UPDATED` for the same file (`blast_radius_state=deferred`), continuous with `resync_required=false`.
- DIRECT_EVIDENCE: At revision 678, Contextor `get_symbol_implementation(mode=preview)` resolved T01 with `workspace_sync=verified`. Structural cycles were fresh, count 16; `cycle_semantics` remained stale. No forced refresh or manual update was used.
