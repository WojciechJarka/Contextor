# CONTEXTOR P1D3-D2B-6-R1 — implementer report

## 1. IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal untrusted-pycache fail-closed repair implemented in the allowlist. No architectural GO is claimed.

## 2. INITIAL/FINAL HEAD
DIRECT_EVIDENCE: Initial and final HEAD `0d11e9b399e1e0668b294ec206b4a07afc61ca55`; no Git mutation.

## 3. INITIAL/FINAL WORKTREE STATUS
DIRECT_EVIDENCE: Initially clean. Final: three allowlisted production/test files modified, plus this report.

## 4. ROOT CAUSE A — PACKAGE PYCACHE
DIRECT_EVIDENCE: Isolated CPython resolves `__pycache__/__init__.pyc` as a package initializer over indexed `__pycache__.py`; the former can activate the guarded import before `pkg.a` finishes initializing.

## 5. ROOT CAUSE B — TAGGED PYCACHE
DIRECT_EVIDENCE: A correctly tagged unchecked-hash `.pyc`, compiled from different source into `cache_from_source(pkg/launcher.py)`, executes despite unchanged indexed `launcher.py` under `-I -B`.

## 6. PREVIOUS D2B-6 CONTRACT CORRECTION
CONTRACT_PROVED: Architect explicitly superseded the previous C02-C04 soft expectation. C01 remains soft; normal py_compile C02-C04 now retain hard guarded edges.

## 7. EXACT PRODUCTION DIFF
CODE_PATH_PROVED: Only the specified pycache exemption block was replaced by unconditional `unindexed_import_artifacts_present = True` for importable files. Enclosing single-pass discovery and finalizer remain unchanged.

## 8. CACHE SEMANTIC VERSION 7 -> 8
DIRECT_EVIDENCE: `IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 8`; other semantic versions unchanged.

## 9. NO WORKER FACT CHANGE
CODE_PATH_PROVED: No worker result or cache field changed; initializer passivity, marker mutation and opaque-effect facts retain their prior meaning and SHA binding.

## 10. NO BINARY READ
CODE_PATH_PROVED: Production change uses file existence/suffix only; no pyc header/content read or bytecode execution was added.

## 11. NO EXTRA DISCOVERY PASS
CODE_PATH_PROVED: One existing `rglob('*')` traversal remains; no additional scan was added.

## 12. K01 SYNTHETIC FIXTURE
DIRECT_EVIDENCE: Fixture contains indexed `__pycache__.py` and generated sourceless `__pycache__/__init__.pyc`, compiled from a temporary source outside the synthetic repository. No `__pycache__/__init__.py` exists.

## 13. K01 CPYTHON LOADER EVIDENCE
DIRECT_EVIDENCE: Fresh isolated `find_spec('__pycache__').origin` points to sourceless initializer. Before pyc, `pkg.launcher` succeeds; after pyc, `pkg.a` and `pkg.c` succeed independently while `pkg.launcher` fails with partially initialized `pkg.a`.

## 14. K01 REAL SCC
DIRECT_EVIDENCE: With pyc present, final guarded import is hard, `pkg.a -> pkg.c` and `pkg.c -> pkg.a` are hard, corresponding soft edge absent, real two-member SCC retained.

## 15. K01 SOFT/HARD/SOFT
DIRECT_EVIDENCE: Same synthetic repo changes soft → hard → soft with pyc addition/removal; `.py` bytes, indexed module IDs and source SHA values remain unchanged. No worker cache deletion or forced reparse; version 8 throughout.

## 16. K02 SYNTHETIC FIXTURE
DIRECT_EVIDENCE: Indexed `pkg/launcher.py` remains `import pkg.a`; only a tagged pyc under `pkg/__pycache__` is added, compiled from temporary dangerous source outside the synthetic repo.

## 17. K02 UNCHECKED_HASH
DIRECT_EVIDENCE: Test uses actual `importlib.util.cache_from_source` target and `py_compile.PycInvalidationMode.UNCHECKED_HASH`.

## 18. K02 CPYTHON EXECUTION EVIDENCE
DIRECT_EVIDENCE: Fresh `-I -B` launcher succeeds before pyc and fails with partially initialized `pkg.a` after pyc. `find_spec` still points to `launcher.py`, so actual import behavior is the decisive evidence.

## 19. K02 REAL SCC
DIRECT_EVIDENCE: Tagged pyc retains hard `pkg.a -> pkg.c`, hard `pkg.c -> pkg.a`, no matching soft edge, and real `{pkg.a,pkg.c}` SCC.

## 20. K02 SOFT/HARD/SOFT
DIRECT_EVIDENCE: Same repository returns soft → hard → soft after pyc addition/removal, with unchanged `.py` bytes, module IDs and source fingerprints; no cache deletion or forced parse, version 8 throughout.

## 21. NORMAL PYCACHE MATRIX C01-C04
DIRECT_EVIDENCE: Renamed test retains exact C01-C04 fixture construction. C01 has type_only=True and soft edge; C02-C04 have type_only=False and real hard SCC. All assert cache version 8.

## 22. NESTED PYCACHE NEGATIVES
DIRECT_EVIDENCE: N01-N07 all trigger hard guarded edge and SCC, including `__init__.pyc`, unrelated pyc, ignored directories, interpreter tagged and optimization-tagged filenames. Ordinary worker opaque facts and source fingerprints remain unchanged.

## 23. EXISTING BINARY REGRESSIONS
CONTRACT_PROVED: Existing A01-A08, sourceless package and native extension tests remain in the focused suite and pass.

## 24. ARTIFACT-FREE POSITIVES
CONTRACT_PROVED: Existing D2B name/attribute, D2B3 typed-side, mixed active, safe prefix/parent and D2B5 complete ImportFrom tests remain in focused suite and pass.

## 25. CACHE V7 INVALIDATION
DIRECT_EVIDENCE: Stale-version matrix now includes absent, 0-7; all are invalidated by the version-8 worker contract. Existing forged-cache regressions pass.

## 26. COLD/WARM PARITY
DIRECT_EVIDENCE: K01/K02 warm source cache remains valid across binary toggles; only repository-wide final classification changes. Existing focused cold/warm regressions pass.

## 27. INLINE/PROCESS-POOL PARITY
DIRECT_EVIDENCE: Real inline/pool parity includes safe baseline, K01, K02, normal a/init pycache, native shadow and previous binary cases; ordered ImportRefs, fingerprints, graph and SCC topology match.

## 28. ORIGINAL-WORKER REINDEX
DIRECT_EVIDENCE: K01/K02 READY planners perform second index with pyc still present. Hard/soft graph, source fingerprints and selected original-worker captures match first pass.

## 29. SOURCE CHECKER FAIL-CLOSED
DIRECT_EVIDENCE: K01/K02 checker returns `INDETERMINATE/GRAPH_SOURCE_IMPORT_MISMATCH`; no positive prepared manifest. No binary AST or source closure was fabricated.

## 30. P0/P1B
DIRECT_EVIDENCE: K01/K02 tests assert no positive P0/P1B state. Existing artifact-free positive P0/P1B tests pass; no production evidence code changed.

## 31. MANIFEST V2
CONTRACT_PROVED: Existing manifest v2 tests pass. K01/K02 do not prepare positive manifests; schema unchanged.

## 32. OFFICIAL ISOLATED FULL
DIRECT_EVIDENCE: Existing artifact-free D2B3 official isolated FULL test passes in the focused suite. No active Contextor FULL.

## 33. RECEIPT V2
CONTRACT_PROVED: Existing isolated receipt v2 regression passes; no binary-artifact receipt fabricated and schema unchanged.

## 34. FOCUSED PYTEST RESULTS
DIRECT_EVIDENCE: Specified eight-module suite: 531 passed, 1 skipped in 95.47s; exit 0, stopwatch 98.03s. No global suite.

## 35. EXACT COMMANDS/EXIT CODES
DIRECT_EVIDENCE: `.\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py`: exit 0, 0.39s. `.\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py`: exit 0, stopwatch 98.03s. `git diff --check --` for three source/test paths: exit 0. Separate skip-reason query: exit 0.

## 36. FILES_CHANGED
DIRECT_EVIDENCE: `contextor/core/symbol_engine/indexer.py`; `tests/test_p1d3_d2b2_type_only.py`; `tests/test_p1d3_package_cycle_integration.py`. `walkthrough.md` is the report, excluded from the production/test changed-file list.

## 37. FULL ACTUAL_DIFF
Complete unabridged `git diff --no-color` for every FILES_CHANGED path:

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index e6bc43a..2c6dc03 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -77,7 +77,7 @@ SYMBOL_FACTS_SCHEMA_VERSION = 2
 REFERENCE_FACTS_SCHEMA_VERSION = 1
 COLLISION_FACTS_SCHEMA_VERSION = 1
 TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 7
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 8
 _IMPORTABLE_BINARY_SUFFIXES = tuple(
     sorted(
         frozenset(BYTECODE_SUFFIXES)
@@ -2513,22 +2513,7 @@ def index_repository(
             )
 
             if importable_artifact and path.is_file():
-                rel = path.relative_to(root_path)
-
-                is_bytecode = (
-                    binary_name.endswith(".pyc")
-                )
-
-                in_pycache = any(
-                    part.casefold() == "__pycache__"
-                    for part in rel.parts[:-1]
-                )
-
-                if not (
-                    is_bytecode
-                    and in_pycache
-                ):
-                    unindexed_import_artifacts_present = True
+                unindexed_import_artifacts_present = True
 
             continue
 
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index e7bcbf3..4851dd6 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -3,6 +3,7 @@
 from __future__ import annotations
 
 import ast
+import importlib.util
 import json
 import py_compile
 import subprocess
@@ -103,6 +104,31 @@ D2B6_SOURCE_SHADOW = {
     "pkg/launcher.py": "pass\n",
 }
 
+D2B6_R1_PYCACHE_PACKAGE = {
+    "__pycache__.py": "pass\n",
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/launcher.py": "import __pycache__\nimport pkg.a\n",
+}
+
+D2B6_R1_FORGED_TAGGED_CACHE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/launcher.py": "import pkg.a\n",
+}
+
 D2B2_R1_GLOBALS_MUTATION = {
     "pkg/__init__.py": "pass\n",
     "pkg/a.py": (
@@ -498,6 +524,143 @@ def _d2b6_spec_origin(root: Path, module: str) -> Path:
     return Path(result.stdout.strip()).resolve()
 
 
+def test_p1d3_d2b6_r1_pycache_package_precedence(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B6_R1_PYCACHE_PACKAGE)
+    original_bytes = {
+        relative: (root / relative).read_bytes()
+        for relative in D2B6_R1_PYCACHE_PACKAGE
+    }
+    before, before_graph = _index_graph(root)
+    assert "pkg.c" in before_graph.soft_edges["pkg.a"]
+    assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 8
+    assert run_synthetic_import(root, "pkg.launcher").returncode == 0
+
+    temporary_source = tmp_path / "dangerous_pycache_initializer.py"
+    temporary_source.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\n", encoding="utf-8",
+    )
+    package_directory = root / "__pycache__"
+    package_directory.mkdir()
+    bytecode = package_directory / "__init__.pyc"
+    py_compile.compile(str(temporary_source), cfile=str(bytecode), doraise=True)
+    temporary_source.unlink()
+    assert not (package_directory / "__init__.py").exists()
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("binary presence must not reparse unchanged source")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    during, during_graph = _index_graph(root)
+    assert set(during.modules) == set(before.modules)
+    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
+    _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 8
+    assert _d2b6_spec_origin(root, "__pycache__") == bytecode.resolve()
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
+    assert {
+        relative: (root / relative).read_bytes() for relative in original_bytes
+    } == original_bytes
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 8
+
+
+def test_p1d3_d2b6_r1_forged_tagged_unchecked_hash_cache(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B6_R1_FORGED_TAGGED_CACHE)
+    original_bytes = {
+        relative: (root / relative).read_bytes()
+        for relative in D2B6_R1_FORGED_TAGGED_CACHE
+    }
+    before, before_graph = _index_graph(root)
+    assert "pkg.c" in before_graph.soft_edges["pkg.a"]
+    assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 8
+    assert run_synthetic_import(root, "pkg.launcher").returncode == 0
+
+    temporary_source = tmp_path / "forged_launcher_source.py"
+    temporary_source.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+        encoding="utf-8",
+    )
+    target_cache_path = Path(
+        importlib.util.cache_from_source(str(root / "pkg" / "launcher.py"))
+    )
+    target_cache_path.parent.mkdir()
+    py_compile.compile(
+        str(temporary_source),
+        cfile=str(target_cache_path),
+        doraise=True,
+        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
+    )
+    temporary_source.unlink()
+    assert target_cache_path.parent == root / "pkg" / "__pycache__"
+
+    def unexpected_parse(*args, **kwargs):
+        raise AssertionError("binary presence must not reparse unchanged source")
+
+    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
+    during, during_graph = _index_graph(root)
+    assert set(during.modules) == set(before.modules)
+    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
+    _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 8
+    assert _d2b6_spec_origin(root, "pkg.launcher") == (
+        root / "pkg" / "launcher.py"
+    ).resolve()
+    failed = run_synthetic_import(root, "pkg.launcher")
+    assert failed.returncode != 0
+    assert "partially initialized module" in failed.stderr
+    assert "pkg.a" in failed.stderr
+
+    target_cache_path.unlink()
+    target_cache_path.parent.rmdir()
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
+        relative: (root / relative).read_bytes() for relative in original_bytes
+    } == original_bytes
+    assert _cache_data(root, root / "pkg" / "a.py")[
+        "import_classification_semantics_version"
+    ] == 8
+
+
 def test_p1d3_d2b6_sourceless_package_preempts_python_module(
     tmp_path, isolated_dirs, monkeypatch,
 ):
@@ -516,7 +679,7 @@ def test_p1d3_d2b6_sourceless_package_preempts_python_module(
         for members in _scc_signature(before, before_graph)
     )
     cached = _cache_data(root, root / "pkg" / "a.py")
-    assert cached["import_classification_semantics_version"] == 7
+    assert cached["import_classification_semantics_version"] == 8
 
     compiled_source = tmp_path / "launcher_init_source.py"
     compiled_source.write_text(
@@ -543,7 +706,7 @@ def test_p1d3_d2b6_sourceless_package_preempts_python_module(
     _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 7
+    ] == 8
     assert _d2b6_spec_origin(root, "pkg.launcher") == bytecode.resolve()
     assert run_synthetic_import(root, "pkg.a").returncode == 0
     assert run_synthetic_import(root, "pkg.c").returncode == 0
@@ -565,7 +728,7 @@ def test_p1d3_d2b6_sourceless_package_preempts_python_module(
     )
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 7
+    ] == 8
     assert {relative: (root / relative).read_bytes() for relative in sources} == sources
 
 
@@ -629,23 +792,63 @@ def test_p1d3_d2b6_alternative_artifact_matrix(
         ("C04", "pkg/__init__.py"),
     ],
 )
-def test_p1d3_d2b6_standard_pycache_remains_soft(
+def test_p1d3_d2b6_r1_standard_pycache_conservative_veto(
     tmp_path, isolated_dirs, case, relative,
 ):
     root = write_synthetic_repository(tmp_path / case, D2B_NAME_SAFE)
     if relative is not None:
         py_compile.compile(str(root / relative), doraise=True)
     index, graph = _index_graph(root)
-    assert next(
+    guarded = next(
         item for item in index.modules["pkg.a"].imports
         if item.module == "pkg.b"
-    ).type_only is True
-    assert "pkg.b" in graph.soft_edges["pkg.a"]
-    assert "pkg.b" not in graph.hard_edges["pkg.a"]
-    assert _scc_signature(index, graph) == ()
+    )
+    if case == "C01":
+        assert guarded.type_only is True
+        assert "pkg.b" in graph.soft_edges["pkg.a"]
+        assert "pkg.b" not in graph.hard_edges["pkg.a"]
+        assert _scc_signature(index, graph) == ()
+    else:
+        assert guarded.type_only is False
+        _assert_d2b5_hard_scc(index, graph, "pkg.b")
     assert _cache_data(root, root / "pkg" / "a.py")[
         "import_classification_semantics_version"
-    ] == 7
+    ] == 8
+
+
+@pytest.mark.parametrize("case", ["N01", "N02", "N03", "N04", "N05", "N06", "N07"])
+def test_p1d3_d2b6_r1_nested_pycache_negatives(
+    tmp_path, isolated_dirs, case,
+):
+    root = write_synthetic_repository(tmp_path / case, D2B_NAME_SAFE)
+    before, before_graph = _index_graph(root)
+    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
+    before_facts = {
+        relative: _cache_data(root, root / relative)["typing_guard_opaque_effects"]
+        for relative in D2B_NAME_SAFE
+    }
+    paths = {
+        "N01": root / "__pycache__" / "__init__.pyc",
+        "N02": root / "pkg" / "__pycache__" / "__init__.pyc",
+        "N03": root / "pkg" / "__pycache__" / "unrelated.pyc",
+        "N04": root / "build" / "__pycache__" / "hidden.pyc",
+        "N05": root / ".venv" / "__pycache__" / "hidden.pyc",
+        "N06": Path(importlib.util.cache_from_source(str(root / "pkg" / "a.py"))),
+        "N07": Path(importlib.util.cache_from_source(
+            str(root / "pkg" / "a.py"), optimization="1",
+        )),
+    }
+    artifact = paths[case]
+    artifact.parent.mkdir(parents=True, exist_ok=True)
+    artifact.write_bytes(b"not-executable-bytecode")
+    index, graph = _index_graph(root)
+    assert set(index.modules) == set(before.modules)
+    assert index.source_fingerprints_by_module == before.source_fingerprints_by_module
+    assert {
+        relative: _cache_data(root, root / relative)["typing_guard_opaque_effects"]
+        for relative in D2B_NAME_SAFE
+    } == before_facts
+    _assert_d2b5_hard_scc(index, graph, "pkg.b")
 
 
 def test_p1d3_d2b6_symlinked_directory_veto(
@@ -667,12 +870,20 @@ def test_p1d3_d2b6_symlinked_directory_veto(
 
 @pytest.mark.parametrize(
     "case",
-    ["safe", "sourceless-shadow", "native-shadow", "pycache", "ignored-bytecode"],
+    [
+        "safe", "sourceless-shadow", "native-shadow", "pycache",
+        "ignored-bytecode", "pycache-package", "forged-tagged", "pycache-init",
+    ],
 )
 def test_p1d3_d2b6_inline_process_pool_parity(
     tmp_path, isolated_dirs, monkeypatch, case,
 ):
-    fixture = D2B6_SOURCE_SHADOW if case == "sourceless-shadow" else D2B_NAME_SAFE
+    fixture = (
+        D2B6_SOURCE_SHADOW if case == "sourceless-shadow"
+        else D2B6_R1_PYCACHE_PACKAGE if case == "pycache-package"
+        else D2B6_R1_FORGED_TAGGED_CACHE if case == "forged-tagged"
+        else D2B_NAME_SAFE
+    )
 
     def prepare(root, label):
         if case == "sourceless-shadow":
@@ -695,6 +906,35 @@ def test_p1d3_d2b6_inline_process_pool_parity(
             )
         elif case == "pycache":
             py_compile.compile(str(root / "pkg" / "a.py"), doraise=True)
+        elif case == "pycache-init":
+            py_compile.compile(str(root / "pkg" / "__init__.py"), doraise=True)
+        elif case == "pycache-package":
+            source = tmp_path / (label + "_pycache_package.py")
+            source.write_text(
+                "import typing\ntyping.TYPE_CHECKING = True\n", encoding="utf-8",
+            )
+            package_directory = root / "__pycache__"
+            package_directory.mkdir()
+            py_compile.compile(
+                str(source), cfile=str(package_directory / "__init__.pyc"),
+                doraise=True,
+            )
+            source.unlink()
+        elif case == "forged-tagged":
+            source = tmp_path / (label + "_forged_tagged.py")
+            source.write_text(
+                "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+                encoding="utf-8",
+            )
+            target = Path(importlib.util.cache_from_source(
+                str(root / "pkg" / "launcher.py")
+            ))
+            target.parent.mkdir()
+            py_compile.compile(
+                str(source), cfile=str(target), doraise=True,
+                invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
+            )
+            source.unlink()
         elif case == "ignored-bytecode":
             artifact = root / "build" / "hidden.pyc"
             artifact.parent.mkdir()
@@ -849,7 +1089,7 @@ def test_p1d3_d2b5_source_visibility_toggle(
         ))
         assert _cache_data(root, root / "pkg" / "a.py")[
             "import_classification_semantics_version"
-        ] == 7
+        ] == 8
     assert states == [(True, False, True), (False, True, False), (True, False, True)]
     assert (root / "pkg" / "a.py").read_bytes() == original_a
     assert (root / "pkg" / "b.py").read_bytes() == original_b
@@ -1120,7 +1360,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 7
+    assert cached["import_classification_semantics_version"] == 8
     assert cached["typing_guard_marker_mutation"] is True
     cached["import_classification_semantics_version"] = 3
     cached["typing_guard_marker_mutation"] = False
@@ -1129,7 +1369,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 7
+    assert rewritten["import_classification_semantics_version"] == 8
     assert rewritten["typing_guard_marker_mutation"] is True
 
 
@@ -1317,7 +1557,7 @@ def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 7
+    assert cached["import_classification_semantics_version"] == 8
     assert cached["typing_guard_marker_mutation"] is False
     assert cached["typing_guard_opaque_effects"] is True
     cached["import_classification_semantics_version"] = 4
@@ -1327,7 +1567,7 @@ def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 7
+    assert rewritten["import_classification_semantics_version"] == 8
     assert rewritten["typing_guard_opaque_effects"] is True
 
 
@@ -1410,7 +1650,7 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
     cold_graph_signature = _graph_signature(cold_index, cold_graph)
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 7
+    assert cached["import_classification_semantics_version"] == 8
     assert next(
         item for item in cached["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -1428,8 +1668,8 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
 
 
 @pytest.mark.parametrize(
-    "stored_version", [None, 0, 1, 2, 3, 4, 5, 6],
-    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5", "version-6"],
+    "stored_version", [None, 0, 1, 2, 3, 4, 5, 6, 7],
+    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5", "version-6", "version-7"],
 )
 def test_stale_import_classification_cache_reparses_same_snapshot(
     tmp_path, isolated_dirs, stored_version, monkeypatch,
@@ -1473,7 +1713,7 @@ def test_stale_import_classification_cache_reparses_same_snapshot(
         for item in result.modules["pkg.a"].imports
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 7
+    assert rewritten["import_classification_semantics_version"] == 8
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -1777,7 +2017,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
 
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 7
+    assert cached["import_classification_semantics_version"] == 8
     forged_imports = [
         item for item in cached["imports"] if item["module"] == "pkg.b"
     ]
@@ -1799,7 +2039,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 7
+    assert rewritten["import_classification_semantics_version"] == 8
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is False
@@ -2011,7 +2251,7 @@ def test_d2b2_r2_worker_success_returns_and_warm_cache(
     ]
     assert warm["source_fingerprint"] == cold["source_fingerprint"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 7
+    assert cached["import_classification_semantics_version"] == 8
     assert type(cached["typing_guard_initializer_passive"]) is bool
     assert cached["typing_guard_initializer_passive"] is expected_passive
     assert cached["typing_guard_marker_mutation"] is cold[
@@ -2030,7 +2270,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     parent = root / "pkg" / "__init__.py"
     original_fingerprint = original.source_fingerprints_by_module["pkg.__init__"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 7
+    assert cached["import_classification_semantics_version"] == 8
     assert cached["typing_guard_initializer_passive"] is False
     cached["typing_guard_initializer_passive"] = True
     cached["import_classification_semantics_version"] = 2
@@ -2048,7 +2288,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     assert graph.hard_edges["pkg.a"] == {"pkg.b"}
     assert graph.hard_edges["pkg.b"] == {"pkg.a"}
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 7
+    assert rewritten["import_classification_semantics_version"] == 8
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
@@ -2066,7 +2306,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
     _index_graph(root)
     parent = root / "pkg" / "__init__.py"
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 7
+    assert cached["import_classification_semantics_version"] == 8
     if case == "missing":
         cached.pop("typing_guard_initializer_passive")
     else:
@@ -2104,7 +2344,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 7
+    assert rewritten["import_classification_semantics_version"] == 8
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index 42ba920..f7b1f3d 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -4,6 +4,7 @@ from __future__ import annotations
 
 import ast
 import copy
+import importlib.util
 import py_compile
 from dataclasses import replace
 from pathlib import Path
@@ -296,6 +297,31 @@ D2B6_SOURCE_SHADOW = {
     "pkg/launcher.py": "pass\n",
 }
 
+D2B6_R1_PYCACHE_PACKAGE = {
+    "__pycache__.py": "pass\n",
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/launcher.py": "import __pycache__\nimport pkg.a\n",
+}
+
+D2B6_R1_FORGED_TAGGED_CACHE = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/launcher.py": "import pkg.a\n",
+}
+
 D2B3_SOURCE_BOUND_NEGATIVES = [
     (
         "N01-no-marker",
@@ -1355,6 +1381,95 @@ def test_p1d3_d2b6_sourceless_shadow_original_worker_fails_closed(
     assert prepared.manifest is None
 
 
+@pytest.mark.parametrize(
+    "case,fixture",
+    [
+        ("K01", D2B6_R1_PYCACHE_PACKAGE),
+        ("K02", D2B6_R1_FORGED_TAGGED_CACHE),
+    ],
+)
+def test_p1d3_d2b6_r1_pycache_original_worker_fails_closed(
+    tmp_path, isolated_dirs, case, fixture,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    temporary_source = tmp_path / "dangerous_source.py"
+    temporary_source.write_text(
+        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
+        encoding="utf-8",
+    )
+    if case == "K01":
+        package_directory = root / "__pycache__"
+        package_directory.mkdir()
+        target = package_directory / "__init__.pyc"
+        py_compile.compile(str(temporary_source), cfile=str(target), doraise=True)
+    else:
+        target = Path(importlib.util.cache_from_source(
+            str(root / "pkg" / "launcher.py")
+        ))
+        target.parent.mkdir()
+        py_compile.compile(
+            str(temporary_source), cfile=str(target), doraise=True,
+            invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
+        )
+    temporary_source.unlink()
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
 def test_p1d3_d2b4_r1_opaque_source_checker_fails_closed(
     tmp_path, isolated_dirs,
 ):
```

## 38. CONTRACT_CONFLICTS
DIRECT_EVIDENCE: None encountered; exact production anchor matched. C02-C04 expectation revision was explicitly authorized by the architect.

## 39. DESIGN_GAPS
DIRECT_EVIDENCE: None encountered for the literal R1 implementation.

## 40. UNKNOWN / UNSUPPORTED
UNKNOWN: Directory symlink behavior remains unverified on this Windows host. The symlink test skips on `[WinError 1314] A required privilege is not held by the client`. Active LIVE adoption, arbitrary import-hook safety, pre-entry mutation and global-suite status were not established.

## 41. FINAL IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal D2B-6-R1 repair and focused validation complete with one platform skip; architectural acceptance remains with ChatGPT. STOP after D2B-6-R1.
