# CONTEXTOR_P1D2D_REAL_INDEX_TO_PREPARED_MANIFEST

## PREFLIGHT_RESULT

- DIRECT_EVIDENCE: Required symbols (`index_repository`, `build_graph`, `materialize_cycle_semantics`, `prepare_original_worker_cycle_manifest`) existed at preflight. The new test path did not exist. Initial worktree was clean at HEAD `f1694a22bd9c36bdc95962cb400928323e721624`.
- CODE_PATH_PROVED: Contextor MCP resolved all four symbols at canonical revision 676 before editing.

## NATIVE_CODEX_EDIT

- DIRECT_EVIDENCE: Created only `tests/test_original_worker_real_pipeline_preparation.py` with the native Codex editing tool. Read-only comparison with attachment reported `EXACT_MATCH` (254 lines). No production code or existing test was modified.

## FILES_CHANGED

- `tests/test_original_worker_real_pipeline_preparation.py` (new)
- `walkthrough.md` (this report)

## ACTUAL_NEW_FILE_CONTENT

Complete unified diff of the new test file:

```diff
diff --git a/tests/test_original_worker_real_pipeline_preparation.py b/tests/test_original_worker_real_pipeline_preparation.py
new file mode 100644
index 0000000..dae7182
--- /dev/null
+++ b/tests/test_original_worker_real_pipeline_preparation.py
@@ -0,0 +1,254 @@
+"""P1D2D: real analysis components to prepared-only worker manifest."""
+
+from __future__ import annotations
+
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.analysis.process_pool_lifecycle import (
+    terminate_active_process_pools,
+)
+from contextor.core.cycle_semantics.contracts import (
+    fingerprint_hard_edges,
+)
+from contextor.core.cycle_semantics.materialization import (
+    materialize_cycle_semantics,
+)
+from contextor.core.cycle_semantics.original_worker_preparation import (
+    prepare_original_worker_cycle_manifest,
+)
+from contextor.core.graph.graph import build_graph
+from contextor.core.symbol_engine.indexer import index_repository
+
+
+_SELECTED = frozenset({
+    "pkg.__init__",
+    "pkg.a",
+    "pkg.b",
+    "pkg.helper",
+})
+
+
+@pytest.fixture(autouse=True)
+def _inline_by_default(monkeypatch):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+
+
+def _repo(tmp_path):
+    root = tmp_path / "repo"
+    pkg = root / "pkg"
+    pkg.mkdir(parents=True)
+
+    (pkg / "__init__.py").write_bytes(b"")
+    (pkg / "a.py").write_bytes(
+        b"import pkg.b\n"
+        b"import pkg.helper\n"
+        b"def fa():\n"
+        b"    return 1\n"
+    )
+    (pkg / "b.py").write_bytes(
+        b"import pkg.a\n"
+        b"def fb():\n"
+        b"    return 2\n"
+    )
+    (pkg / "helper.py").write_bytes(b"value = 1\n")
+    (pkg / "unrelated.py").write_bytes(b"value = 999\n")
+
+    return root
+
+
+def _analyze_components(root, selected=_SELECTED):
+    index = index_repository(
+        str(root),
+        source_capture_module_ids=selected,
+    )
+    graph = build_graph(index.modules)
+    snapshot = materialize_cycle_semantics(
+        root,
+        graph.hard_edges,
+        {
+            module_id: module.path
+            for module_id, module in index.modules.items()
+        },
+        index.source_fingerprints_by_module,
+    )
+    return index, graph, snapshot
+
+
+def _prepare(index, graph, snapshot):
+    return prepare_original_worker_cycle_manifest(
+        index,
+        graph.hard_edges,
+        snapshot,
+    )
+
+
+def test_p1d2d_t01_real_component_chain_prepares_only(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, graph, snapshot = _analyze_components(root)
+
+    assert index.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+    assert snapshot.coverage_status == (
+        "FILESYSTEM_STABLE_NON_ATOMIC"
+    )
+    assert snapshot.cyclic_modules == ("pkg.a", "pkg.b")
+    assert snapshot.graph_sha256 == fingerprint_hard_edges(
+        graph.hard_edges
+    )
+
+    result = _prepare(index, graph, snapshot)
+
+    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert result.reason is None
+    assert result.manifest is not None
+    assert result.manifest.authority == (
+        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
+    )
+    assert result.manifest.source_manifest_sha256 is not None
+    assert result.manifest.components[0].members == (
+        "pkg.a",
+        "pkg.b",
+    )
+    assert {
+        "pkg.a",
+        "pkg.b",
+        "pkg.helper",
+    }.issubset(result.source_modules)
+    assert "pkg.unrelated" not in result.source_modules
+
+
+def test_p1d2d_t02_warm_cache_keeps_preparation_valid(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index_repository(str(root))
+
+    index, graph, snapshot = _analyze_components(root)
+
+    assert set(index.original_worker_ast_modes.values()) == {
+        "CACHE_SHA256_EQUIVALENT"
+    }
+
+    result = _prepare(index, graph, snapshot)
+
+    assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
+    assert result.manifest is not None
+
+
+def test_p1d2d_t03_default_index_cannot_prepare_manifest(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+    index, graph, snapshot = _analyze_components(
+        root,
+        selected=None,
+    )
+
+    result = _prepare(index, graph, snapshot)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == "BINDING_INDEX_CAPTURE_NOT_COMPLETE"
+    assert result.manifest is None
+
+
+def test_p1d2d_t04_missing_reachable_capture_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+
+    selected = frozenset({
+        "pkg.__init__",
+        "pkg.a",
+        "pkg.b",
+    })
+    index, graph, snapshot = _analyze_components(
+        root,
+        selected=selected,
+    )
+
+    result = _prepare(index, graph, snapshot)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "BINDING_CLOSURE_CAPTURE_MISSING:pkg.helper"
+    )
+    assert result.manifest is None
+    assert result.source_modules == ()
+
+
+def test_p1d2d_t05_cyclic_source_drift_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = _repo(tmp_path)
+
+    index = index_repository(
+        str(root),
+        source_capture_module_ids=_SELECTED,
+    )
+    graph = build_graph(index.modules)
+
+    (root / "pkg" / "a.py").write_bytes(
+        b"import pkg.b\n"
+        b"import pkg.helper\n"
+        b"def fa():\n"
+        b"    return 99\n"
+    )
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
+    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"
+
+    result = _prepare(index, graph, snapshot)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.manifest is None
+
+
+def test_p1d2d_t06_graph_identity_mismatch_rejected(
+    tmp_path, isolated_dirs,
+):
+    index, graph, snapshot = _analyze_components(_repo(tmp_path))
+
+    altered = replace(snapshot, graph_sha256="0" * 64)
+    result = _prepare(index, graph, altered)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.manifest is None
+
+
+def test_p1d2d_t07_real_process_pool_component_chain(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    monkeypatch.delenv(
+        "CONTEXTOR_DISABLE_PROCESS_POOL",
+        raising=False,
+    )
+
+    terminate_active_process_pools(timeout=1.0)
+    try:
+        index, graph, snapshot = _analyze_components(root)
+        result = _prepare(index, graph, snapshot)
+
+        assert index.original_worker_capture_status == (
+            "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+        )
+        assert result.status == (
+            "PREPARED_UNPUBLISHED_NON_ATOMIC"
+        )
+        assert result.manifest is not None
+    finally:
+        terminate_active_process_pools(timeout=1.0)
```

## PY_COMPILE_RESULT

- DIRECT_EVIDENCE: `py_compile tests/test_original_worker_real_pipeline_preparation.py` returned exit 0.

## P1D2D_TEST_RESULTS

- DIRECT_EVIDENCE: Exact requested pytest command completed with **3 failed, 168 passed in 29.91s**.
- Failed cases: `test_p1d2d_t01_real_component_chain_prepares_only`, `test_p1d2d_t02_warm_cache_keeps_preparation_valid`, `test_p1d2d_t07_real_process_pool_component_chain`. Each failed because expected status `PREPARED_UNPUBLISHED_NON_ATOMIC`, actual `UNAVAILABLE`.
- Other 168 tests passed. No test was repeated and no implementation was changed after failure.

### Exact failure output

```text
================================== FAILURES ===================================
______________ test_p1d2d_t01_real_component_chain_prepares_only ______________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-834/test_p1d2d_t01_real_component_0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-834/test_p1d2d_t01_real_component_0')

    def test_p1d2d_t01_real_component_chain_prepares_only(
        tmp_path, isolated_dirs,
    ):
        root = _repo(tmp_path)
        index, graph, snapshot = _analyze_components(root)

        assert index.original_worker_capture_status == (
            "ALL_SELECTED_CAPTURED_NON_ATOMIC"
        )
        assert snapshot.coverage_status == (
            "FILESYSTEM_STABLE_NON_ATOMIC"
        )
        assert snapshot.cyclic_modules == ("pkg.a", "pkg.b")
        assert snapshot.graph_sha256 == fingerprint_hard_edges(
            graph.hard_edges
        )

        result = _prepare(index, graph, snapshot)

>       assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
E       AssertionError: assert 'UNAVAILABLE' == 'PREPARED_UNP...ED_NON_ATOMIC'
E         
E         - PREPARED_UNPUBLISHED_NON_ATOMIC
E         + UNAVAILABLE

tests\test_original_worker_real_pipeline_preparation.py:106: AssertionError
______________ test_p1d2d_t02_warm_cache_keeps_preparation_valid ______________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-834/test_p1d2d_t02_warm_cache_keep0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-834/test_p1d2d_t02_warm_cache_keep0')

    def test_p1d2d_t02_warm_cache_keeps_preparation_valid(
        tmp_path, isolated_dirs,
    ):
        root = _repo(tmp_path)
        index_repository(str(root))

        index, graph, snapshot = _analyze_components(root)

        assert set(index.original_worker_ast_modes.values()) == {
            "CACHE_SHA256_EQUIVALENT"
        }

        result = _prepare(index, graph, snapshot)

>       assert result.status == "PREPARED_UNPUBLISHED_NON_ATOMIC"
E       AssertionError: assert 'UNAVAILABLE' == 'PREPARED_UNP...ED_NON_ATOMIC'
E         
E         - PREPARED_UNPUBLISHED_NON_ATOMIC
E         + UNAVAILABLE

tests\test_original_worker_real_pipeline_preparation.py:139: AssertionError
______________ test_p1d2d_t07_real_process_pool_component_chain ______________

tmp_path = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-834/test_p1d2d_t07_real_process_po0')
isolated_dirs = WindowsPath('C:/Users/DafoO/AppData/Local/Temp/pytest-of-DafoO/pytest-834/test_p1d2d_t07_real_process_po0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000019241B0E710>

    def test_p1d2d_t07_real_process_pool_component_chain(
        tmp_path, isolated_dirs, monkeypatch,
    ):
        root = _repo(tmp_path)
        monkeypatch.delenv(
            "CONTEXTOR_DISABLE_PROCESS_POOL",
            raising=False,
        )

        terminate_active_process_pools(timeout=1.0)
        try:
            index, graph, snapshot = _analyze_components(root)
            result = _prepare(index, graph, snapshot)

            assert index.original_worker_capture_status == (
                "ALL_SELECTED_CAPTURED_NON_ATOMIC"
            )
>           assert result.status == (
                "PREPARED_UNPUBLISHED_NON_ATOMIC"
            )
E           AssertionError: assert 'UNAVAILABLE' == 'PREPARED_UNP...ED_NON_ATOMIC'
E             
E             - PREPARED_UNPUBLISHED_NON_ATOMIC
E             + UNAVAILABLE

tests\test_original_worker_real_pipeline_preparation.py:249: AssertionError
=========================== short test summary info ============================
FAILED tests/test_original_worker_real_pipeline_preparation.py::test_p1d2d_t01_real_component_chain_prepares_only
FAILED tests/test_original_worker_real_pipeline_preparation.py::test_p1d2d_t02_warm_cache_keeps_preparation_valid
FAILED tests/test_original_worker_real_pipeline_preparation.py::test_p1d2d_t07_real_process_pool_component_chain
3 failed, 168 passed in 29.91s
```

## FOCUSED_NON_REGRESSION

- DIRECT_EVIDENCE: This exact focused set ran once. Result: 3 failed, 168 passed. No broader test run was made.
- DIRECT_EVIDENCE: `git diff --check` reported only three trailing-space lines (`walkthrough.md:324,350,382`) inside the verbatim pytest traceback above. The new test file itself has no reported whitespace diagnostics.

## CANONICAL_WATCHER_OBSERVATIONS

- NOT PERFORMED: The instruction says to stop immediately after any test failure. Therefore no post-edit Contextor watcher/read check was made. No LIVE freshness is claimed.

## SOURCE_CAPTURE_AND_SEMANTIC_CONSISTENCY

- DIRECT_EVIDENCE: In the three failing tests, execution reached the assertion after successful indexing and graph/materialization setup; T01 explicitly passed its capture status, stable cohort, cyclic module and graph fingerprint assertions; T02 passed its warm-cache AST mode assertion; T07 passed its index capture status assertion. The preparation result was `UNAVAILABLE` in each case.
- UNKNOWN: The precise internal reason for `UNAVAILABLE`; no diagnostic probe or code change was performed after the mandated stop.

## PREPARED_ONLY_AUTHORITY_LIMITS

- CODE_PATH_PROVED: The supplied test is intended to exercise isolated components only. No facade FULL, persistence, receipt sealing or LIVE publication is invoked by the test code. Since three positive-path assertions failed, this stage does not establish a real component chain that prepares a manifest.
- No claim of cross-file atomicity, current filesystem freshness after preparation, durable receipt, canonical generation certification, active LIVE adoption or runtime import safety.

## UNVERIFIED_RUNTIME_BEHAVIOR

- UNKNOWN: Active runtime behavior and loaded-code adoption were not tested. No restart, publication or LIVE operation occurred.

## FINAL_VERDICT

P1D2D is incomplete. The architect-supplied test file matches the attachment and compiles, but its three positive-path cases fail with `UNAVAILABLE`; 168 other tests in the requested set pass. No code was adjusted. STOP and await the architect's correction.
