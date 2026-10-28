# CONTEXTOR P1D3-D2B-6 — implementer report

## 1. IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal alternative import-loader artifact veto implemented in the allowlist. No architectural GO is claimed.

## 2. INITIAL/FINAL HEAD
DIRECT_EVIDENCE: Initial and final HEAD `3ceac7b6ead3447605e86c83c46d0581bf4af0d3`; no Git mutation.

## 3. INITIAL/FINAL WORKTREE STATUS
DIRECT_EVIDENCE: Initially clean. Final: three allowlisted source/test files modified, plus this report.

## 4. ROOT CAUSE
CODE_PATH_PROVED: Previous discovery enumerated `.py` only. A sourceless package or native extension could be selected by CPython while the worker audited an indexed `.py` file.

## 5. CPYTHON LOADER PRECEDENCE
DIRECT_EVIDENCE: Fresh isolated CPython `find_spec('pkg.launcher').origin` resolves to `pkg/launcher/__init__.pyc` over `pkg/launcher.py`; launcher import fails with partially initialized `pkg.a`.

## 6. PLATFORM SUFFIX DISCOVERY
CODE_PATH_PROVED: `_IMPORTABLE_BINARY_SUFFIXES` derives from current interpreter `BYTECODE_SUFFIXES` and `EXTENSION_SUFFIXES`; no hardcoded platform extension list.

## 7. EXACT SINGLE-PASS DISCOVERY DIFF
CODE_PATH_PROVED: Existing discovery loop replaced by one `rglob('*')` pass. It detects directory symlinks and importable binary suffixes without reading contents, then applies the existing ignored-directory and excludes policy to `.py` sources.

## 8. NEW PRIVATE ARTIFACT BOOL
CODE_PATH_PROVED: `unindexed_import_artifacts_present` is initialized False and recomputed for every index invocation. No worker/cache/public field was added.

## 9. STANDARD __pycache__ EXCEPTION
DIRECT_EVIDENCE: Ordinary `.pyc` under an ancestor named `__pycache__` leaves eligible candidate soft; C01-C04 pass. Bytecode elsewhere triggers the veto.

## 10. GLOBAL FINALIZER INTEGRATION
CODE_PATH_PROVED: Existing `project_effects_closed` now additionally requires `not unindexed_import_artifacts_present`; no other predicate, finalizer call site or graph operation changed.

## 11. PRIMARY BYTECODE FIXTURE
DIRECT_EVIDENCE: Authored synthetic `.py` sources remained unchanged. Dangerous initializer was compiled from a temporary source outside the synthetic repo to `pkg/launcher/__init__.pyc`; temporary source was removed. No `pkg/launcher/__init__.py` exists.

## 12. CPYTHON DIFFERENTIAL
DIRECT_EVIDENCE: Fresh isolated `pkg.a` and `pkg.c` imports succeed; `pkg.launcher` fails with partially initialized `pkg.a`. Actual `find_spec` origin identifies the sourceless initializer.

## 13. HARD/SOFT THREE-STATE TRANSITION
DIRECT_EVIDENCE: Same synthetic repository yields SOFT → HARD → SOFT as bytecode is added then removed. Indexed module IDs, `.py` bytes and source fingerprints remain equal; no worker cache deletion or forced parse. Cache version 7 throughout.

## 14. NATIVE EXTENSION SHADOW
DIRECT_EVIDENCE: An invalid binary placeholder named `pkg/a` plus `EXTENSION_SUFFIXES[0]` retains hard `pkg.a -> pkg.b` and real SCC; `.py` inventory remains indexed. No native code was compiled or executed.

## 15. ACTUAL spec.origin EVIDENCE
DIRECT_EVIDENCE: A separate isolated CPython `find_spec('pkg.a').origin` points to the native extension placeholder rather than `pkg/a.py`. This establishes loader selection only.

## 16. ARTIFACT NEGATIVE MATRIX
DIRECT_EVIDENCE: A01-A08 all clear the eligible type_only flag and retain hard SCC, including unrelated artifacts and artifacts under `build` or `.venv`. Ordinary `.py` worker opaque facts remain unchanged.

## 17. NORMAL CACHE POSITIVE MATRIX
DIRECT_EVIDENCE: C01 no artifact and C02-C04 standard `__pycache__` bytecode retain type_only=True, soft edge and no hard guarded SCC; cache semantic version is 7.

## 18. SYMLINK DIRECTORY TEST
DIRECT_EVIDENCE: Test was skipped only after actual Windows symlink creation failed with `[WinError 1314] A required privilege is not held by the client`. No elevation, settings change or substitute artifact.

## 19. CACHE VERSION 6 -> 7
DIRECT_EVIDENCE: `IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 7`; stale values absent and 0-6 are covered. Existing worker facts and source-SHA binding are unchanged.

## 20. COLD/WARM PARITY
DIRECT_EVIDENCE: Primary SOFT → HARD → SOFT sequence uses unchanged warm per-file cache. Existing focused cache regressions pass.

## 21. INLINE/PROCESS-POOL PARITY
DIRECT_EVIDENCE: Five real isolated inline/pool pairs pass module inventory, ordered ImportRefs/type_only, source fingerprints, hard/soft graph and SCC signatures.

## 22. ORIGINAL-WORKER REINDEX
DIRECT_EVIDENCE: Sourceless-shadow planner is READY; second real index retains artifact, captures selected original worker sources, and matches canonical hard/soft graph and selected fingerprints.

## 23. SOURCE CHECKER FAIL-CLOSED
DIRECT_EVIDENCE: Sourceless-shadow source checker returns `INDETERMINATE/GRAPH_SOURCE_IMPORT_MISMATCH`; no binary AST was invented and no positive manifest prepared.

## 24. P0/P1B
CONTRACT_PROVED: Existing positive P0/P1B regressions pass in the focused suite. No P0/P1B code or alternate-artifact positive evidence was added.

## 25. MANIFEST V2
CONTRACT_PROVED: Existing manifest v2 tests pass; sourceless-shadow case yields no positive manifest. No schema change.

## 26. OFFICIAL ISOLATED FULL
DIRECT_EVIDENCE: Existing D2B3 official isolated FULL test passes in focused suite. No FULL on active Contextor.

## 27. RECEIPT V2
CONTRACT_PROVED: Existing isolated receipt v2 regression passes. No receipt schema change or fabricated sourceless-shadow receipt.

## 28. FOCUSED PYTEST RESULTS
DIRECT_EVIDENCE: Specified eight-module suite: 516 passed, 1 skipped in 99.92s; exit 0, stopwatch 102.40s. Skip reason is recorded in Section 18. No global suite.

## 29. EXACT COMMANDS/EXIT CODES
DIRECT_EVIDENCE: `.\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py`: exit 0, 0.37s. `.\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py`: exit 0, stopwatch 102.40s. `git diff --check --` for three source/test paths: exit 0.

## 30. FILES_CHANGED
DIRECT_EVIDENCE: `contextor/core/symbol_engine/indexer.py`; `tests/test_p1d3_d2b2_type_only.py`; `tests/test_p1d3_package_cycle_integration.py`. `walkthrough.md` is the report and excluded from the production/test changed-file list.

## 31. FULL ACTUAL_DIFF
Complete unabridged `git diff --no-color` for every FILES_CHANGED path:

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 2ac3a7b..e6bc43a 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -17,6 +17,10 @@ import os
 import re
 import time
 from concurrent.futures import as_completed
+from importlib.machinery import (
+    BYTECODE_SUFFIXES,
+    EXTENSION_SUFFIXES,
+)
 from pathlib import Path
 
 from contextor.core.analysis.cache_manager import CacheManager
@@ -73,7 +77,13 @@ SYMBOL_FACTS_SCHEMA_VERSION = 2
 REFERENCE_FACTS_SCHEMA_VERSION = 1
 COLLISION_FACTS_SCHEMA_VERSION = 1
 TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 6
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 7
+_IMPORTABLE_BINARY_SUFFIXES = tuple(
+    sorted(
+        frozenset(BYTECODE_SUFFIXES)
+        | frozenset(EXTENSION_SUFFIXES)
+    )
+)
 _SYMBOL_FACTS_AVAILABLE = "available"
 _SYMBOL_FACTS_FAILURE = "failure"
 _SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
@@ -2465,15 +2475,68 @@ def index_repository(
         ignored_dirs.update(extra_ignored_dirs)
 
     unindexed_python_sources_present = False
+    unindexed_import_artifacts_present = False
     file_discovery_started = time.monotonic()
 
     files_to_process = []
-    for path in root_path.rglob("*.py"):
-        # rglob matches directories too, and a directory named 'foo.py'
-        # was becoming a module in its own right.
+    for path in root_path.rglob("*"):
+        if (
+            path.is_symlink()
+            and path.is_dir()
+        ):
+            unindexed_import_artifacts_present = True
+            continue
+
+        name = path.name
+
+        is_python_source = (
+            name.casefold().endswith(".py")
+            if os.name == "nt"
+            else name.endswith(".py")
+        )
+
+        if not is_python_source:
+            binary_name = (
+                name.casefold()
+                if os.name == "nt"
+                else name
+            )
+
+            importable_artifact = any(
+                binary_name.endswith(
+                    suffix.casefold()
+                    if os.name == "nt"
+                    else suffix
+                )
+                for suffix
+                in _IMPORTABLE_BINARY_SUFFIXES
+            )
+
+            if importable_artifact and path.is_file():
+                rel = path.relative_to(root_path)
+
+                is_bytecode = (
+                    binary_name.endswith(".pyc")
+                )
+
+                in_pycache = any(
+                    part.casefold() == "__pycache__"
+                    for part in rel.parts[:-1]
+                )
+
+                if not (
+                    is_bytecode
+                    and in_pycache
+                ):
+                    unindexed_import_artifacts_present = True
+
+            continue
+
         if not path.is_file():
             continue
+
         rel = path.relative_to(root_path)
+
         if any(
             part in ignored_dirs
             for part in rel.parts
@@ -2483,14 +2546,23 @@ def index_repository(
         if excludes:
             rel_str = rel.as_posix()
             is_excluded = False
+
             for ex in excludes:
                 ex_norm = ex.replace("\\", "/")
-                if rel_str == ex_norm or rel_str.startswith(ex_norm + "/"):
+
+                if (
+                    rel_str == ex_norm
+                    or rel_str.startswith(
+                        ex_norm + "/"
+                    )
+                ):
                     is_excluded = True
                     break
+
             if is_excluded:
                 unindexed_python_sources_present = True
                 continue
+
         files_to_process.append(path)
 
     file_discovery_ms = (
@@ -2539,6 +2611,7 @@ def index_repository(
         project_effects_closed = (
             not skipped
             and not unindexed_python_sources_present
+            and not unindexed_import_artifacts_present
             and len(opaque_effects_by_module)
             == len(modules)
             and all(
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 1b384a2..e7bcbf3 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4,9 +4,11 @@ from __future__ import annotations
 
 import ast
 import json
+import py_compile
 import subprocess
 import sys
 from dataclasses import replace
+from importlib.machinery import EXTENSION_SUFFIXES
 from pathlib import Path
 
 import pytest
@@ -89,6 +91,18 @@ D2B5_EXCLUDED_CHILD = {
     "pkg/launcher.py": "from pkg import hidden\nimport pkg.a\n",
 }
 
+D2B6_SOURCE_SHADOW = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/launcher.py": "pass\n",
+}
+
 D2B2_R1_GLOBALS_MUTATION = {
     "pkg/__init__.py": "pass\n",
     "pkg/a.py": (
@@ -470,6 +484,242 @@ def _cache_data(root: Path, source: Path) -> dict:
     )["data"]
 
 
+def _d2b6_spec_origin(root: Path, module: str) -> Path:
+    program = (
+        "import importlib.util,sys;"
+        "sys.path.insert(0,sys.argv[1]);"
+        "print(importlib.util.find_spec(sys.argv[2]).origin)"
+    )
+    result = subprocess.run(
+        [sys.executable, "-I", "-B", "-c", program, str(root.resolve()), module],
+        capture_output=True, text=True, timeout=8, check=False,
+    )
+    assert result.returncode == 0, result.stderr
+    return Path(result.stdout.strip()).resolve()
+
+
+def test_p1d3_d2b6_sourceless_package_preempts_python_module(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B6_SOURCE_SHADOW)
+    source_local, error = indexer.read_imports(root / "pkg" / "a.py")
+    assert error is None
+    assert next(item for item in source_local if item.module == "pkg.c").type_only
+    sources = {relative: (root / relative).read_bytes() for relative in D2B6_SOURCE_SHADOW}
+
+    before, before_graph = _index_graph(root)
+    assert set(before.modules) == {"pkg.__init__", "pkg.a", "pkg.c", "pkg.launcher"}
+    assert "pkg.c" in before_graph.soft_edges["pkg.a"]
+    assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
+    assert not any(
+        set(members) == {"pkg.a", "pkg.c"}
+        for members in _scc_signature(before, before_graph)
+    )
+    cached = _cache_data(root, root / "pkg" / "a.py")
+    assert cached["import_classification_semantics_version"] == 7
+
+    compiled_source = tmp_path / "launcher_init_source.py"
+    compiled_source.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+        encoding="utf-8",
+    )
+    package_directory = root / "pkg" / "launcher"
+    package_directory.mkdir()
+    bytecode = package_directory / "__init__.pyc"
+    py_compile.compile(str(compiled_source), cfile=str(bytecode), doraise=True)
+    compiled_source.unlink()
+    assert (root / "pkg" / "launcher.py").is_file()
+    assert bytecode.is_file()
+    assert not (package_directory / "__init__.py").exists()
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("artifact transition must not reparse unchanged source")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    during, during_graph = _index_graph(root)
+    assert set(during.modules) == set(before.modules)
+    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
+    assert not during.skipped
+    _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 7
+    assert _d2b6_spec_origin(root, "pkg.launcher") == bytecode.resolve()
+    assert run_synthetic_import(root, "pkg.a").returncode == 0
+    assert run_synthetic_import(root, "pkg.c").returncode == 0
+    failed = run_synthetic_import(root, "pkg.launcher")
+    assert failed.returncode != 0
+    assert "partially initialized module" in failed.stderr
+    assert "pkg.a" in failed.stderr
+
+    bytecode.unlink()
+    package_directory.rmdir()
+    after, after_graph = _index_graph(root)
+    assert set(after.modules) == set(before.modules)
+    assert after.source_fingerprints_by_module == before.source_fingerprints_by_module
+    assert "pkg.c" in after_graph.soft_edges["pkg.a"]
+    assert "pkg.c" not in after_graph.hard_edges["pkg.a"]
+    assert not any(
+        set(members) == {"pkg.a", "pkg.c"}
+        for members in _scc_signature(after, after_graph)
+    )
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 7
+    assert {relative: (root / relative).read_bytes() for relative in sources} == sources
+
+
+def test_p1d3_d2b6_native_extension_shadow_veto(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    original, original_graph = _index_graph(root)
+    assert "pkg.b" in original_graph.soft_edges["pkg.a"]
+    placeholder = root / "pkg" / ("a" + EXTENSION_SUFFIXES[0])
+    placeholder.write_bytes(b"not-a-real-extension")
+    index, graph = _index_graph(root)
+    assert set(index.modules) == set(original.modules)
+    assert not index.skipped
+    _assert_d2b5_hard_scc(index, graph, "pkg.b")
+    assert _d2b6_spec_origin(root, "pkg.a") == placeholder.resolve()
+
+
+@pytest.mark.parametrize(
+    "case,relative",
+    [
+        ("A01", "unrelated.pyc"),
+        ("A02", "pkg/hidden.pyc"),
+        ("A03", "pkg/launcher/__init__.pyc"),
+        ("A04", "pkg/native" + EXTENSION_SUFFIXES[0]),
+        ("A05", "pkg/other" + EXTENSION_SUFFIXES[-1]),
+        ("A06", "build/hidden.pyc"),
+        ("A07", ".venv/hidden.pyc"),
+        ("A08", "build/unrelated" + EXTENSION_SUFFIXES[0]),
+    ],
+)
+def test_p1d3_d2b6_alternative_artifact_matrix(
+    tmp_path, isolated_dirs, case, relative,
+):
+    root = write_synthetic_repository(tmp_path / case, D2B_NAME_SAFE)
+    before, before_graph = _index_graph(root)
+    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
+    before_facts = {
+        source: _cache_data(root, root / source)["typing_guard_opaque_effects"]
+        for source in D2B_NAME_SAFE
+    }
+    artifact = root / relative
+    artifact.parent.mkdir(parents=True, exist_ok=True)
+    artifact.write_bytes(b"not-an-executable-artifact")
+    index, graph = _index_graph(root)
+    assert set(index.modules) == set(before.modules)
+    assert index.source_fingerprints_by_module == before.source_fingerprints_by_module
+    assert {
+        source: _cache_data(root, root / source)["typing_guard_opaque_effects"]
+        for source in D2B_NAME_SAFE
+    } == before_facts
+    _assert_d2b5_hard_scc(index, graph, "pkg.b")
+
+
+@pytest.mark.parametrize(
+    "case,relative",
+    [
+        ("C01", None),
+        ("C02", "pkg/a.py"),
+        ("C03", "pkg/b.py"),
+        ("C04", "pkg/__init__.py"),
+    ],
+)
+def test_p1d3_d2b6_standard_pycache_remains_soft(
+    tmp_path, isolated_dirs, case, relative,
+):
+    root = write_synthetic_repository(tmp_path / case, D2B_NAME_SAFE)
+    if relative is not None:
+        py_compile.compile(str(root / relative), doraise=True)
+    index, graph = _index_graph(root)
+    assert next(
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    ).type_only is True
+    assert "pkg.b" in graph.soft_edges["pkg.a"]
+    assert "pkg.b" not in graph.hard_edges["pkg.a"]
+    assert _scc_signature(index, graph) == ()
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 7
+
+
+def test_p1d3_d2b6_symlinked_directory_veto(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    target = tmp_path / "symlink-target"
+    target.mkdir()
+    link = root / "linked"
+    try:
+        link.symlink_to(target, target_is_directory=True)
+    except OSError as exc:
+        pytest.skip(f"directory symlink unavailable: {exc}")
+    assert link.is_symlink() and link.is_dir()
+    index, graph = _index_graph(root)
+    assert set(index.modules) == {"pkg.__init__", "pkg.a", "pkg.b"}
+    _assert_d2b5_hard_scc(index, graph, "pkg.b")
+
+
+@pytest.mark.parametrize(
+    "case",
+    ["safe", "sourceless-shadow", "native-shadow", "pycache", "ignored-bytecode"],
+)
+def test_p1d3_d2b6_inline_process_pool_parity(
+    tmp_path, isolated_dirs, monkeypatch, case,
+):
+    fixture = D2B6_SOURCE_SHADOW if case == "sourceless-shadow" else D2B_NAME_SAFE
+
+    def prepare(root, label):
+        if case == "sourceless-shadow":
+            source = tmp_path / (label + "_init.py")
+            source.write_text(
+                "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+                encoding="utf-8",
+            )
+            package_directory = root / "pkg" / "launcher"
+            package_directory.mkdir()
+            py_compile.compile(
+                str(source),
+                cfile=str(package_directory / "__init__.pyc"),
+                doraise=True,
+            )
+            source.unlink()
+        elif case == "native-shadow":
+            (root / "pkg" / ("a" + EXTENSION_SUFFIXES[0])).write_bytes(
+                b"not-a-real-extension"
+            )
+        elif case == "pycache":
+            py_compile.compile(str(root / "pkg" / "a.py"), doraise=True)
+        elif case == "ignored-bytecode":
+            artifact = root / "build" / "hidden.pyc"
+            artifact.parent.mkdir()
+            artifact.write_bytes(b"not-executable-bytecode")
+
+    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
+    prepare(inline_root, "inline")
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline_index, inline_graph = _index_graph(inline_root)
+
+    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
+    prepare(pool_root, "pool")
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pool_index, pool_graph = _index_graph(pool_root)
+
+    assert set(pool_index.modules) == set(inline_index.modules)
+    assert pool_index.source_fingerprints_by_module == (
+        inline_index.source_fingerprints_by_module
+    )
+    assert _import_signature(pool_index) == _import_signature(inline_index)
+    assert _graph_signature(pool_index, pool_graph) == (
+        _graph_signature(inline_index, inline_graph)
+    )
+
+
 def _assert_d2b5_hard_scc(index, graph, target):
     guarded = next(
         item for item in index.modules["pkg.a"].imports
@@ -599,7 +849,7 @@ def test_p1d3_d2b5_source_visibility_toggle(
         ))
         assert _cache_data(root, root / "pkg" / "a.py")[
             "import_classification_semantics_version"
-        ] == 6
+        ] == 7
     assert states == [(True, False, True), (False, True, False), (True, False, True)]
     assert (root / "pkg" / "a.py").read_bytes() == original_a
     assert (root / "pkg" / "b.py").read_bytes() == original_b
@@ -870,7 +1120,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 6
+    assert cached["import_classification_semantics_version"] == 7
     assert cached["typing_guard_marker_mutation"] is True
     cached["import_classification_semantics_version"] = 3
     cached["typing_guard_marker_mutation"] = False
@@ -879,7 +1129,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 6
+    assert rewritten["import_classification_semantics_version"] == 7
     assert rewritten["typing_guard_marker_mutation"] is True
 
 
@@ -1067,7 +1317,7 @@ def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 6
+    assert cached["import_classification_semantics_version"] == 7
     assert cached["typing_guard_marker_mutation"] is False
     assert cached["typing_guard_opaque_effects"] is True
     cached["import_classification_semantics_version"] = 4
@@ -1077,7 +1327,7 @@ def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 6
+    assert rewritten["import_classification_semantics_version"] == 7
     assert rewritten["typing_guard_opaque_effects"] is True
 
 
@@ -1160,7 +1410,7 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
     cold_graph_signature = _graph_signature(cold_index, cold_graph)
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 6
+    assert cached["import_classification_semantics_version"] == 7
     assert next(
         item for item in cached["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -1178,8 +1428,8 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
 
 
 @pytest.mark.parametrize(
-    "stored_version", [None, 0, 1, 2, 3, 4, 5],
-    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5"],
+    "stored_version", [None, 0, 1, 2, 3, 4, 5, 6],
+    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5", "version-6"],
 )
 def test_stale_import_classification_cache_reparses_same_snapshot(
     tmp_path, isolated_dirs, stored_version, monkeypatch,
@@ -1223,7 +1473,7 @@ def test_stale_import_classification_cache_reparses_same_snapshot(
         for item in result.modules["pkg.a"].imports
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 6
+    assert rewritten["import_classification_semantics_version"] == 7
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -1527,7 +1777,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
 
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 6
+    assert cached["import_classification_semantics_version"] == 7
     forged_imports = [
         item for item in cached["imports"] if item["module"] == "pkg.b"
     ]
@@ -1549,7 +1799,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 6
+    assert rewritten["import_classification_semantics_version"] == 7
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is False
@@ -1761,7 +2011,7 @@ def test_d2b2_r2_worker_success_returns_and_warm_cache(
     ]
     assert warm["source_fingerprint"] == cold["source_fingerprint"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 6
+    assert cached["import_classification_semantics_version"] == 7
     assert type(cached["typing_guard_initializer_passive"]) is bool
     assert cached["typing_guard_initializer_passive"] is expected_passive
     assert cached["typing_guard_marker_mutation"] is cold[
@@ -1780,7 +2030,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     parent = root / "pkg" / "__init__.py"
     original_fingerprint = original.source_fingerprints_by_module["pkg.__init__"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 6
+    assert cached["import_classification_semantics_version"] == 7
     assert cached["typing_guard_initializer_passive"] is False
     cached["typing_guard_initializer_passive"] = True
     cached["import_classification_semantics_version"] = 2
@@ -1798,7 +2048,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     assert graph.hard_edges["pkg.a"] == {"pkg.b"}
     assert graph.hard_edges["pkg.b"] == {"pkg.a"}
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 6
+    assert rewritten["import_classification_semantics_version"] == 7
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
@@ -1816,7 +2066,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
     _index_graph(root)
     parent = root / "pkg" / "__init__.py"
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 6
+    assert cached["import_classification_semantics_version"] == 7
     if case == "missing":
         cached.pop("typing_guard_initializer_passive")
     else:
@@ -1854,7 +2104,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 6
+    assert rewritten["import_classification_semantics_version"] == 7
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index ad1aa4b..42ba920 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -4,6 +4,7 @@ from __future__ import annotations
 
 import ast
 import copy
+import py_compile
 from dataclasses import replace
 from pathlib import Path
 
@@ -283,6 +284,18 @@ D2B5_EXCLUDED_CHILD = {
     "pkg/launcher.py": "from pkg import hidden\nimport pkg.a\n",
 }
 
+D2B6_SOURCE_SHADOW = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/launcher.py": "pass\n",
+}
+
 D2B3_SOURCE_BOUND_NEGATIVES = [
     (
         "N01-no-marker",
@@ -1284,6 +1297,64 @@ def test_p1d3_d2b5_excluded_child_source_checker_fails_closed(
     assert prepared.manifest is None
 
 
+def test_p1d3_d2b6_sourceless_shadow_original_worker_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B6_SOURCE_SHADOW)
+    compiled_source = tmp_path / "launcher_init_source.py"
+    compiled_source.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+        encoding="utf-8",
+    )
+    package_directory = root / "pkg" / "launcher"
+    package_directory.mkdir()
+    py_compile.compile(
+        str(compiled_source),
+        cfile=str(package_directory / "__init__.pyc"),
+        doraise=True,
+    )
+    compiled_source.unlink()
+
+    index, graph = _d2a_canonical_index_graph(root)
+    assert graph.hard_edges["pkg.a"] == {"pkg.c"}
+    assert graph.hard_edges["pkg.c"] == {"pkg.a"}
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    assert plan.selected_module_ids
+    captured, captured_graph = _d2a_canonical_index_graph(
+        root, source_capture_module_ids=plan.selected_module_ids,
+    )
+    assert captured.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+    assert captured_graph.hard_edges == graph.hard_edges
+    assert captured_graph.soft_edges == graph.soft_edges
+    assert captured.source_fingerprints_by_module == (
+        index.source_fingerprints_by_module
+    )
+    for module_id in plan.selected_module_ids:
+        assert captured.original_worker_source_snapshots[
+            module_id
+        ].source_fingerprint == index.source_fingerprints_by_module[module_id]
+    parsed = {
+        module: parse_source_snapshot(snapshot, module)
+        for module, snapshot in captured.original_worker_source_snapshots.items()
+    }
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    consistency = assess_package_graph_consistency(
+        graph.hard_edges,
+        {module_id: source.tree for module_id, source in parsed.items()},
+        closure[0].evidence_source_modules,
+    )
+    assert consistency.status == "INDETERMINATE"
+    assert consistency.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    prepared = prepare_original_worker_cycle_manifest(
+        captured, graph.hard_edges, _snapshot(root, index, graph),
+    )
+    assert prepared.manifest is None
+
+
 def test_p1d3_d2b4_r1_opaque_source_checker_fails_closed(
     tmp_path, isolated_dirs,
 ):
```

## 32. CONTRACT_CONFLICTS
DIRECT_EVIDENCE: None encountered; production anchors matched.

## 33. DESIGN_GAPS
DIRECT_EVIDENCE: None encountered for the literal D2B-6 implementation.

## 34. UNKNOWN / UNSUPPORTED
UNKNOWN: Directory-symlink behavior is unverified on this Windows host because creation was denied. Active LIVE loaded-code adoption, arbitrary import-hook safety and global-suite status were not established.

## 35. FINAL IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal D2B-6 implementation and focused validation complete with one platform skip; architectural acceptance remains with ChatGPT. STOP after D2B-6.
