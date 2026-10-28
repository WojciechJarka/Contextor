# CONTEXTOR P1D3-D2B-7 — implementer report

## 1. IMPLEMENTER OBSERVATION

**DIRECT_EVIDENCE:** Literal bounded D2B-7 implementation completed in authorized paths; architectural acceptance remains with ChatGPT.

## 2. INITIAL / FINAL HEAD

**DIRECT_EVIDENCE:** Initial and final HEAD `aa503d38534fe2bae47625e377fcceb9008fffd1`.

## 3. INITIAL / FINAL WORKTREE STATUS

**DIRECT_EVIDENCE:** Initial clean. Final modified: `contextor/core/symbol_engine/indexer.py`, `tests/test_p1d3_d2b2_type_only.py`, `tests/test_p1d3_package_cycle_integration.py`, and this report.

## 4. VERIFIED PRODUCTION BASELINE

**CODE_PATH_PROVED:** Pre-edit version 8, binary suffix collection, one `root_path.rglob("*")`, real-file guard, global `unindexed_import_artifacts_present` veto, and no ordinary-pycache exemption.

## 5. ROOT CAUSE — ALTERNATIVE SOURCE SUFFIX

**CODE_PATH_PROVED:** Version 8 did not recognize platform-supported non-`.py` source suffixes. Windows CPython recognizes `.pyw`.

## 6. PLATFORM AND SOURCE_SUFFIXES

**DIRECT_EVIDENCE:** Windows, `os.name=nt`, CPython 3.10.9, `SOURCE_SUFFIXES=['.py', '.pyw']`.

## 7. EXACT PRODUCTION CHANGE

**DIRECT_EVIDENCE:** Imported `SOURCE_SUFFIXES`, added sole `_ALTERNATIVE_SOURCE_SUFFIXES` excluding `.py`, extended existing suffix match, and changed semantics 8 to 9.

## 8. SINGLE-PASS DISCOVERY EVIDENCE

**CODE_PATH_PROVED:** Existing single `rglob("*")` traversal and `.py` indexing branch remain. Non-`.py` matching now checks binary and alternative source suffixes.

## 9. GLOBAL VETO REUSE

**CODE_PATH_PROVED:** Existing real-file guard sets existing `unindexed_import_artifacts_present`; existing global veto handles ignored directories.

## 10. CACHE SEMANTICS 8 -> 9

**CONTRACT_PROVED:** Current version assertions require 9; stale matrix now includes 8; focused tests passed.

## 11. REAL WINDOWS LOADER EVIDENCE OR EXPLICIT SKIP

**DIRECT_EVIDENCE:** Real `.pyw` loader test ran and passed on Windows, without importlib or suffix monkeypatch.

## 12. ACTUAL CPYTHON spec.origin

**DIRECT_EVIDENCE:** Passed assertions: `pkg.launcher` spec origin changes from `pkg/launcher.py` to `pkg/launcher/__init__.pyw`.

## 13. ACTUAL CPYTHON IMPORT DIFFERENTIAL

**DIRECT_EVIDENCE:** Passed fresh subprocess imports: launcher succeeds before artifact; independent `pkg.a` and `pkg.c` succeed during; launcher fails with partially initialized `pkg.a`.

## 14. SOFT -> HARD -> SOFT

**DIRECT_EVIDENCE:** Real-loader and synthetic tests passed SOFT/no SCC → HARD/real SCC → SOFT/no SCC assertions.

## 15. SYNTHETIC SCANNER TEST

**DIRECT_EVIDENCE:** Separate scanner test monkeypatches only `_ALTERNATIVE_SOURCE_SUFFIXES=(".pyw",)` and exercises actual indexer.

## 16. IGNORED-DIRECTORY ALTERNATIVE-SOURCE TESTS

**DIRECT_EVIDENCE:** Scanner cases for root, `build/`, `.venv/` passed.

## 17. UNCHANGED INDEXED SOURCES / FINGERPRINTS

**DIRECT_EVIDENCE:** Transition tests compare module ID sets, fingerprint maps, and original `.py` bytes. `.pyw` remains unindexed.

## 18. WARM CACHE AND NO FORCED REPARSE

**DIRECT_EVIDENCE:** Real-loader transition patched `parse_source_snapshot` to raise on reparse; warm-cache reindexes passed without cache deletion. Version 9 asserted in all states.

## 19. INLINE / PROCESS-POOL PARITY

**DIRECT_EVIDENCE:** Existing parity matrix extended with alternative source; focused suite passed module IDs, fingerprints, import signatures, hard/soft graph, and SCC comparisons for inline and pool.

## 20. ORIGINAL-WORKER SECOND REINDEX

**DIRECT_EVIDENCE:** Real first index and second `source_capture_module_ids` index passed. Planner READY and capture `ALL_SELECTED_CAPTURED_NON_ATOMIC`; topology and fingerprints match.

## 21. SOURCE CHECKER FAIL-CLOSED

**DIRECT_EVIDENCE:** Checker produced `INDETERMINATE / GRAPH_SOURCE_IMPORT_MISMATCH`.

## 22. P0 / P1B

**DIRECT_EVIDENCE:** Test rejects positive `DECLARED_INPUTS_CONSISTENT` and `BYTE_AST_CONSISTENT_NON_ATOMIC` for mismatch.

## 23. MANIFEST V2

**DIRECT_EVIDENCE:** Mismatched case yields `prepared.manifest is None`; schema unchanged.

## 24. RECEIPT V2

**CONTRACT_PROVED:** Existing focused receipt regressions passed; receipt code/schema unchanged.

## 25. D2B-6/R1 REGRESSION PRESERVATION

**DIRECT_EVIDENCE:** Focused eight-module suite: 538 passed, 1 symlink privilege skip, zero failures.

## 26. CACHE V8 INVALIDATION

**DIRECT_EVIDENCE:** Stale matrix includes version 8; passed under version 9.

## 27. PY_COMPILE RESULT

**DIRECT_EVIDENCE:** `py_compile` exit 0, 0.2723678 s.

## 28. FOCUSED PYTEST RESULTS

**DIRECT_EVIDENCE:** Explicit new tests: 5 passed in 10.79 s, exit 0. Eight-module suite: 538 passed, 1 skipped in 93.91 s, exit 0.

## 29. EXACT COMMANDS / EXIT CODES / DURATIONS

**DIRECT_EVIDENCE:** Commands: `.\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py` (exit 0, 0.2723678 s); `.\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py::test_p1d3_d2b7_real_windows_alternative_source_loader tests/test_p1d3_d2b2_type_only.py::test_p1d3_d2b7_synthetic_scanner_detection tests/test_p1d3_package_cycle_integration.py::test_p1d3_d2b7_alternative_source_original_worker_fails_closed -x` (exit 0, 5 passed, 10.79 s); `.\.venv\Scripts\python.exe -m pytest -q -rs tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py` (exit 0, 538 passed, 1 skipped, pytest 93.91 s, outer 95.4566236 s); `git diff --check -- contextor/core/symbol_engine/indexer.py tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py` (exit 0).

## 30. PLATFORM SKIPS AND REASONS

**DIRECT_EVIDENCE:** One skip at `tests/test_p1d3_d2b2_type_only.py:973`: directory symlink unavailable, `[WinError 1314] A required privilege is not held by the client`. Real `.pyw` loader test ran.

## 31. FILES_CHANGED

**DIRECT_EVIDENCE:** `contextor/core/symbol_engine/indexer.py`; `tests/test_p1d3_d2b2_type_only.py`; `tests/test_p1d3_package_cycle_integration.py`; `walkthrough.md` (report only).

## 32. FULL ACTUAL_DIFF

**DIRECT_EVIDENCE:** Complete source/test diff inserted below.

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index 2c6dc03..2790e9e 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -20,6 +20,7 @@ from concurrent.futures import as_completed
 from importlib.machinery import (
     BYTECODE_SUFFIXES,
     EXTENSION_SUFFIXES,
+    SOURCE_SUFFIXES,
 )
 from pathlib import Path
 
@@ -77,13 +78,20 @@ SYMBOL_FACTS_SCHEMA_VERSION = 2
 REFERENCE_FACTS_SCHEMA_VERSION = 1
 COLLISION_FACTS_SCHEMA_VERSION = 1
 TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 8
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 9
 _IMPORTABLE_BINARY_SUFFIXES = tuple(
     sorted(
         frozenset(BYTECODE_SUFFIXES)
         | frozenset(EXTENSION_SUFFIXES)
     )
 )
+_ALTERNATIVE_SOURCE_SUFFIXES = tuple(
+    sorted(
+        suffix
+        for suffix in SOURCE_SUFFIXES
+        if suffix.casefold() != ".py"
+    )
+)
 _SYMBOL_FACTS_AVAILABLE = "available"
 _SYMBOL_FACTS_FAILURE = "failure"
 _SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
@@ -2508,8 +2516,11 @@ def index_repository(
                     if os.name == "nt"
                     else suffix
                 )
-                for suffix
-                in _IMPORTABLE_BINARY_SUFFIXES
+                for suffixes in (
+                    _IMPORTABLE_BINARY_SUFFIXES,
+                    _ALTERNATIVE_SOURCE_SUFFIXES,
+                )
+                for suffix in suffixes
             )
 
             if importable_artifact and path.is_file():
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 4851dd6..1258d3b 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -9,7 +9,7 @@ import py_compile
 import subprocess
 import sys
 from dataclasses import replace
-from importlib.machinery import EXTENSION_SUFFIXES
+from importlib.machinery import EXTENSION_SUFFIXES, SOURCE_SUFFIXES
 from pathlib import Path
 
 import pytest
@@ -524,6 +524,115 @@ def _d2b6_spec_origin(root: Path, module: str) -> Path:
     return Path(result.stdout.strip()).resolve()
 
 
+def test_p1d3_d2b7_real_windows_alternative_source_loader(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    if ".pyw" not in SOURCE_SUFFIXES:
+        pytest.skip(f"real .pyw loader unavailable: SOURCE_SUFFIXES={SOURCE_SUFFIXES!r}")
+
+    root = write_synthetic_repository(tmp_path / "repo", D2B6_SOURCE_SHADOW)
+    source_bytes = {
+        relative: (root / relative).read_bytes()
+        for relative in D2B6_SOURCE_SHADOW
+    }
+    before, before_graph = _index_graph(root)
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 9
+    assert _d2b6_spec_origin(root, "pkg.launcher") == (
+        root / "pkg" / "launcher.py"
+    ).resolve()
+    assert run_synthetic_import(root, "pkg.launcher").returncode == 0
+    assert "pkg.c" in before_graph.soft_edges["pkg.a"]
+    assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
+    assert not any(
+        set(members) == {"pkg.a", "pkg.c"}
+        for members in _scc_signature(before, before_graph)
+    )
+
+    package_directory = root / "pkg" / "launcher"
+    package_directory.mkdir()
+    alternative_source = package_directory / "__init__.pyw"
+    alternative_source.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+        encoding="utf-8",
+    )
+    assert not (package_directory / "__init__.py").exists()
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("alternative source presence must not reparse indexed source")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    during, during_graph = _index_graph(root)
+    assert set(during.modules) == set(before.modules)
+    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
+    _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 9
+    assert _d2b6_spec_origin(root, "pkg.launcher") == alternative_source.resolve()
+    assert run_synthetic_import(root, "pkg.a").returncode == 0
+    assert run_synthetic_import(root, "pkg.c").returncode == 0
+    failed = run_synthetic_import(root, "pkg.launcher")
+    assert failed.returncode != 0
+    assert "partially initialized module" in failed.stderr
+    assert "pkg.a" in failed.stderr
+
+    alternative_source.unlink()
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
+    assert {
+        relative: (root / relative).read_bytes() for relative in source_bytes
+    } == source_bytes
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 9
+
+
+@pytest.mark.parametrize(
+    "relative",
+    ["unrelated.pyw", "build/unrelated.pyw", ".venv/unrelated.pyw"],
+)
+def test_p1d3_d2b7_synthetic_scanner_detection(
+    tmp_path, isolated_dirs, monkeypatch, relative,
+):
+    monkeypatch.setattr(indexer, "_ALTERNATIVE_SOURCE_SUFFIXES", (".pyw",))
+    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
+    source_bytes = {
+        source: (root / source).read_bytes()
+        for source in D2B_NAME_SAFE
+    }
+    before, before_graph = _index_graph(root)
+    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
+    assert "pkg.b" not in before_graph.hard_edges["pkg.a"]
+    assert _scc_signature(before, before_graph) == ()
+    artifact = root / relative
+    artifact.parent.mkdir(parents=True, exist_ok=True)
+    artifact.write_text("pass\n", encoding="utf-8")
+    during, during_graph = _index_graph(root)
+    assert set(during.modules) == set(before.modules)
+    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
+    _assert_d2b5_hard_scc(during, during_graph, "pkg.b")
+    artifact.unlink()
+    after, after_graph = _index_graph(root)
+    assert set(after.modules) == set(before.modules)
+    assert after.source_fingerprints_by_module == before.source_fingerprints_by_module
+    assert "pkg.b" in after_graph.soft_edges["pkg.a"]
+    assert "pkg.b" not in after_graph.hard_edges["pkg.a"]
+    assert _scc_signature(after, after_graph) == ()
+    assert {
+        source: (root / source).read_bytes() for source in source_bytes
+    } == source_bytes
+
+
 def test_p1d3_d2b6_r1_pycache_package_precedence(
     tmp_path, isolated_dirs, monkeypatch,
 ):
@@ -537,7 +646,7 @@ def test_p1d3_d2b6_r1_pycache_package_precedence(
     assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
     assert run_synthetic_import(root, "pkg.launcher").returncode == 0
 
     temporary_source = tmp_path / "dangerous_pycache_initializer.py"
@@ -561,7 +670,7 @@ def test_p1d3_d2b6_r1_pycache_package_precedence(
     _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
     assert _d2b6_spec_origin(root, "__pycache__") == bytecode.resolve()
     assert run_synthetic_import(root, "pkg.a").returncode == 0
     assert run_synthetic_import(root, "pkg.c").returncode == 0
@@ -586,7 +695,7 @@ def test_p1d3_d2b6_r1_pycache_package_precedence(
     } == original_bytes
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
 
 
 def test_p1d3_d2b6_r1_forged_tagged_unchecked_hash_cache(
@@ -602,7 +711,7 @@ def test_p1d3_d2b6_r1_forged_tagged_unchecked_hash_cache(
     assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
     assert run_synthetic_import(root, "pkg.launcher").returncode == 0
 
     temporary_source = tmp_path / "forged_launcher_source.py"
@@ -633,7 +742,7 @@ def test_p1d3_d2b6_r1_forged_tagged_unchecked_hash_cache(
     _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
     assert _d2b6_spec_origin(root, "pkg.launcher") == (
         root / "pkg" / "launcher.py"
     ).resolve()
@@ -658,7 +767,7 @@ def test_p1d3_d2b6_r1_forged_tagged_unchecked_hash_cache(
     } == original_bytes
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
 
 
 def test_p1d3_d2b6_sourceless_package_preempts_python_module(
@@ -679,7 +788,7 @@ def test_p1d3_d2b6_sourceless_package_preempts_python_module(
         for members in _scc_signature(before, before_graph)
     )
     cached = _cache_data(root, root / "pkg" / "a.py")
-    assert cached["import_classification_semantics_version"] == 8
+    assert cached["import_classification_semantics_version"] == 9
 
     compiled_source = tmp_path / "launcher_init_source.py"
     compiled_source.write_text(
@@ -706,7 +815,7 @@ def test_p1d3_d2b6_sourceless_package_preempts_python_module(
     _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
     assert _d2b6_spec_origin(root, "pkg.launcher") == bytecode.resolve()
     assert run_synthetic_import(root, "pkg.a").returncode == 0
     assert run_synthetic_import(root, "pkg.c").returncode == 0
@@ -728,7 +837,7 @@ def test_p1d3_d2b6_sourceless_package_preempts_python_module(
     )
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
     assert {relative: (root / relative).read_bytes() for relative in sources} == sources
 
 
@@ -813,7 +922,7 @@ def test_p1d3_d2b6_r1_standard_pycache_conservative_veto(
         _assert_d2b5_hard_scc(index, graph, "pkg.b")
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 8
+    ] == 9
 
 
 @pytest.mark.parametrize("case", ["N01", "N02", "N03", "N04", "N05", "N06", "N07"])
@@ -873,13 +982,14 @@ def test_p1d3_d2b6_symlinked_directory_veto(
     [
         "safe", "sourceless-shadow", "native-shadow", "pycache",
         "ignored-bytecode", "pycache-package", "forged-tagged", "pycache-init",
+        "alternative-source",
     ],
 )
 def test_p1d3_d2b6_inline_process_pool_parity(
     tmp_path, isolated_dirs, monkeypatch, case,
 ):
     fixture = (
-        D2B6_SOURCE_SHADOW if case == "sourceless-shadow"
+        D2B6_SOURCE_SHADOW if case in {"sourceless-shadow", "alternative-source"}
         else D2B6_R1_PYCACHE_PACKAGE if case == "pycache-package"
         else D2B6_R1_FORGED_TAGGED_CACHE if case == "forged-tagged"
         else D2B_NAME_SAFE
@@ -900,6 +1010,13 @@ def test_p1d3_d2b6_inline_process_pool_parity(
                 doraise=True,
             )
             source.unlink()
+        elif case == "alternative-source":
+            package_directory = root / "pkg" / "launcher"
+            package_directory.mkdir()
+            (package_directory / "__init__.pyw").write_text(
+                "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+                encoding="utf-8",
+            )
         elif case == "native-shadow":
             (root / "pkg" / ("a" + EXTENSION_SUFFIXES[0])).write_bytes(
                 b"not-a-real-extension"
@@ -940,6 +1057,9 @@ def test_p1d3_d2b6_inline_process_pool_parity(
             artifact.parent.mkdir()
             artifact.write_bytes(b"not-executable-bytecode")
 
+    if case == "alternative-source" and ".pyw" not in SOURCE_SUFFIXES:
+        monkeypatch.setattr(indexer, "_ALTERNATIVE_SOURCE_SUFFIXES", (".pyw",))
+
     inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
     prepare(inline_root, "inline")
     monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
@@ -1089,7 +1209,7 @@ def test_p1d3_d2b5_source_visibility_toggle(
         ))
         assert _cache_data(root, root / "pkg" / "a.py")[
             "import_classification_semantics_version"
-        ] == 8
+        ] == 9
     assert states == [(True, False, True), (False, True, False), (True, False, True)]
     assert (root / "pkg" / "a.py").read_bytes() == original_a
     assert (root / "pkg" / "b.py").read_bytes() == original_b
@@ -1360,7 +1480,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 8
+    assert cached["import_classification_semantics_version"] == 9
     assert cached["typing_guard_marker_mutation"] is True
     cached["import_classification_semantics_version"] = 3
     cached["typing_guard_marker_mutation"] = False
@@ -1369,7 +1489,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 8
+    assert rewritten["import_classification_semantics_version"] == 9
     assert rewritten["typing_guard_marker_mutation"] is True
 
 
@@ -1557,7 +1677,7 @@ def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 8
+    assert cached["import_classification_semantics_version"] == 9
     assert cached["typing_guard_marker_mutation"] is False
     assert cached["typing_guard_opaque_effects"] is True
     cached["import_classification_semantics_version"] = 4
@@ -1567,7 +1687,7 @@ def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 8
+    assert rewritten["import_classification_semantics_version"] == 9
     assert rewritten["typing_guard_opaque_effects"] is True
 
 
@@ -1650,7 +1770,7 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
     cold_graph_signature = _graph_signature(cold_index, cold_graph)
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 8
+    assert cached["import_classification_semantics_version"] == 9
     assert next(
         item for item in cached["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -1668,8 +1788,8 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
 
 
 @pytest.mark.parametrize(
-    "stored_version", [None, 0, 1, 2, 3, 4, 5, 6, 7],
-    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5", "version-6", "version-7"],
+    "stored_version", [None, 0, 1, 2, 3, 4, 5, 6, 7, 8],
+    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5", "version-6", "version-7", "version-8"],
 )
 def test_stale_import_classification_cache_reparses_same_snapshot(
     tmp_path, isolated_dirs, stored_version, monkeypatch,
@@ -1713,7 +1833,7 @@ def test_stale_import_classification_cache_reparses_same_snapshot(
         for item in result.modules["pkg.a"].imports
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 8
+    assert rewritten["import_classification_semantics_version"] == 9
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -2017,7 +2137,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
 
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 8
+    assert cached["import_classification_semantics_version"] == 9
     forged_imports = [
         item for item in cached["imports"] if item["module"] == "pkg.b"
     ]
@@ -2039,7 +2159,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 8
+    assert rewritten["import_classification_semantics_version"] == 9
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is False
@@ -2251,7 +2371,7 @@ def test_d2b2_r2_worker_success_returns_and_warm_cache(
     ]
     assert warm["source_fingerprint"] == cold["source_fingerprint"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 8
+    assert cached["import_classification_semantics_version"] == 9
     assert type(cached["typing_guard_initializer_passive"]) is bool
     assert cached["typing_guard_initializer_passive"] is expected_passive
     assert cached["typing_guard_marker_mutation"] is cold[
@@ -2270,7 +2390,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     parent = root / "pkg" / "__init__.py"
     original_fingerprint = original.source_fingerprints_by_module["pkg.__init__"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 8
+    assert cached["import_classification_semantics_version"] == 9
     assert cached["typing_guard_initializer_passive"] is False
     cached["typing_guard_initializer_passive"] = True
     cached["import_classification_semantics_version"] = 2
@@ -2288,7 +2408,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     assert graph.hard_edges["pkg.a"] == {"pkg.b"}
     assert graph.hard_edges["pkg.b"] == {"pkg.a"}
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 8
+    assert rewritten["import_classification_semantics_version"] == 9
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
@@ -2306,7 +2426,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
     _index_graph(root)
     parent = root / "pkg" / "__init__.py"
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 8
+    assert cached["import_classification_semantics_version"] == 9
     if case == "missing":
         cached.pop("typing_guard_initializer_passive")
     else:
@@ -2344,7 +2464,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 8
+    assert rewritten["import_classification_semantics_version"] == 9
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index f7b1f3d..8f21a76 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -7,6 +7,7 @@ import copy
 import importlib.util
 import py_compile
 from dataclasses import replace
+from importlib.machinery import SOURCE_SUFFIXES
 from pathlib import Path
 
 import pytest
@@ -1381,6 +1382,79 @@ def test_p1d3_d2b6_sourceless_shadow_original_worker_fails_closed(
     assert prepared.manifest is None
 
 
+def test_p1d3_d2b7_alternative_source_original_worker_fails_closed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    if ".pyw" not in SOURCE_SUFFIXES:
+        monkeypatch.setattr(indexer, "_ALTERNATIVE_SOURCE_SUFFIXES", (".pyw",))
+    root = write_synthetic_repository(tmp_path / "repo", D2B6_SOURCE_SHADOW)
+    package_directory = root / "pkg" / "launcher"
+    package_directory.mkdir()
+    alternative_source = package_directory / "__init__.pyw"
+    alternative_source.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+        encoding="utf-8",
+    )
+    index, graph = _d2a_canonical_index_graph(root)
+    assert alternative_source.is_file()
+    assert graph.hard_edges["pkg.a"] == {"pkg.c"}
+    assert graph.hard_edges["pkg.c"] == {"pkg.a"}
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    assert plan.selected_module_ids
+    captured, captured_graph = _d2a_canonical_index_graph(
+        root, source_capture_module_ids=plan.selected_module_ids,
+    )
+    assert alternative_source.is_file()
+    assert captured.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+    assert captured_graph.hard_edges == graph.hard_edges
+    assert captured_graph.soft_edges == graph.soft_edges
+    assert captured.source_fingerprints_by_module == (
+        index.source_fingerprints_by_module
+    )
+    assert all(Path(module.absolute_path).suffix == ".py" for module in captured.modules.values())
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
+    snapshot = _snapshot(root, index, graph)
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    p0 = assess_index_bound_scc_models(
+        graph.hard_edges,
+        captured.source_fingerprints_by_module,
+        snapshot,
+        evidence,
+    )
+    p1b = assess_scc_source_bytes(
+        graph.hard_edges,
+        captured.source_fingerprints_by_module,
+        snapshot,
+        evidence,
+        captured.original_worker_source_snapshots,
+    )
+    assert all(item.evidence_state != "DECLARED_INPUTS_CONSISTENT" for item in p0)
+    assert all(item.bytes_state != "BYTE_AST_CONSISTENT_NON_ATOMIC" for item in p1b)
+    prepared = prepare_original_worker_cycle_manifest(
+        captured, graph.hard_edges, snapshot,
+    )
+    assert prepared.manifest is None
+
+
 @pytest.mark.parametrize(
     "case,fixture",
     [
```

## 33. CONTRACT_CONFLICTS

**DIRECT_EVIDENCE:** None encountered.

## 34. DESIGN_GAPS

**DIRECT_EVIDENCE:** None encountered.

## 35. UNKNOWN / UNSUPPORTED

**UNKNOWN:** Active LIVE adoption, global pytest, and non-Windows `.pyw` loader behavior. Isolated FULL regression is not active LIVE proof.

## 36. FINAL IMPLEMENTER OBSERVATION

**DIRECT_EVIDENCE:** Bounded change and focused checks completed; stop after D2B-7. No architectural GO.

