# CONTEXTOR P1D3-D2B-5 — implementer report

## 1. IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal D2B-5 excluded-source and ImportFrom child closure implemented within the allowlist. No architectural GO is claimed.

## 2. INITIAL/FINAL HEAD
DIRECT_EVIDENCE: Initial and final HEAD `00684f7975ffee66aba69443bd379cd16200c560`; no Git mutation.

## 3. WORKTREE STATUS
DIRECT_EVIDENCE: Initially clean. Final source/test status: three allowlisted files modified; this report is also modified.

## 4. ROOT CAUSE A — EXCLUDED SOURCE
CODE_PATH_PROVED: Discovery previously continued past ignored/excluded `.py` without recording an incomplete domain. The new private bool records such omissions without reading excluded source.

## 5. ROOT CAUSE B — IMPLICIT CHILD
CODE_PATH_PROVED: Prior import-domain helper accepted `from pkg import hidden` when `pkg.__init__` was indexed even if `pkg.hidden` was not. The exact replacement checks each package child.

## 6. EXACT DISCOVERY DIFF
CODE_PATH_PROVED: One existing `rglob("*.py")` remains. Its ignored-directory and user-exclude branches set the private bool before continuing. Matching order and progress counters are unchanged.

## 7. PRIVATE INCOMPLETENESS BOOL
CODE_PATH_PROVED: `unindexed_python_sources_present = False` is initialized immediately before discovery timing and recomputed on each index invocation. It is not a worker/cache/public field.

## 8. GLOBAL FINALIZER INTEGRATION
CODE_PATH_PROVED: `project_effects_closed` additionally requires `not unindexed_python_sources_present`; previous project marker, typing shadow and parent predicates remain.

## 9. EXACT IMPORTFROM CLOSURE
CODE_PATH_PROVED: The helper distinguishes indexed ordinary modules from indexed packages and requires each package-imported member to be an indexed child module or child package. Trusted exact typing exception remains.

## 10. EXCLUDED CHILD FIXTURE
DIRECT_EVIDENCE: With `pkg/hidden.py` excluded, `pkg.hidden` is absent, no SkippedFile is needed, the guarded edge remains hard, no matching soft edge exists, and real `{pkg.a,pkg.c}` SCC survives. Import-domain helper returns False.

## 11. EXCLUDED TYPING SHADOW
DIRECT_EVIDENCE: With local `typing.py` excluded, source-local guarded candidate is recognized but final `pkg.a -> pkg.b` remains hard with real two-member SCC and no matching soft edge.

## 12. CLEAN CPYTHON DIFFERENTIAL
DIRECT_EVIDENCE: Separate fresh synthetic imports of `pkg.a` and `pkg.c` succeed; excluded-child launcher fails with partially initialized `pkg.a`. The local-typing fixture fails in a separate `sys.executable -I -S -B -c` interpreter after asserting typing is absent from `sys.modules`.

## 13. EXCLUSION MATRIX
DIRECT_EVIDENCE: X01 typing.py, X02 hidden child, X03 extra ignored directory and X04 default build directory veto eligible promotion. X05 nonexistent exclude leaves soft promotion. X06 uses prescribed existing matcher spelling `pkg` and omits an existing `.py`, vetoing an unrelated eligible candidate.

## 14. EXCLUSION TOGGLE
DIRECT_EVIDENCE: Same unchanged repository yields soft → hard → soft across no exclude → exclude unrelated.py → no exclude. Per-file cache remains semantic version 6; source bytes of guarded modules remain unchanged.

## 15. IMPORTFROM NEGATIVE MATRIX
DIRECT_EVIDENCE: F01-F06 yield closed-domain False, clear the eligible guarded candidate, preserve active imports, retain hard SCC, and match cold/warm ImportRefs and graph.

## 16. IMPORTFROM POSITIVE MATRIX
DIRECT_EVIDENCE: P01-P06 yield closed-domain True and retain the guarded soft edge; indexed ordinary module attributes, indexed package children, alias, multiple children, nested child and exact typing exception are covered.

## 17. HARD/SOFT GRAPH
DIRECT_EVIDENCE: Veto cases retain hard guarded edges and remove only candidate soft classification. Positive cases retain soft guarded edges; normal active imports remain in ordered ImportRefs.

## 18. SCC TOPOLOGY
DIRECT_EVIDENCE: Excluded child and excluded typing cases retain genuine hard two-member SCCs. ImportFrom negative and positive matrix cold/warm SCC signatures match.

## 19. CACHE VERSION 5 -> 6
DIRECT_EVIDENCE: Import classification semantic version is 6. Missing and versions 0 through 5 are stale in the focused cache test. Existing three worker fact fields and source-SHA cache binding are unchanged.

## 20. COLD/WARM PARITY
DIRECT_EVIDENCE: ImportFrom matrices and the three-state exclusion toggle run repeated indices with unchanged bytes. Existing cache regressions remain passing.

## 21. INLINE/PROCESS-POOL PARITY
DIRECT_EVIDENCE: Six real isolated inline/pool pairs pass module inventory, source fingerprints, ordered ImportRefs/type_only, hard/soft graph and SCC signature comparisons.

## 22. ORIGINAL-WORKER REINDEX
DIRECT_EVIDENCE: Excluded-child and incomplete-child SCCs yield READY planner results. The selected second pass uses identical excludes; captured fingerprints and canonical hard/soft graphs equal the first pass.

## 23. SOURCE-CHECKER FAIL-CLOSED
DIRECT_EVIDENCE: Excluded-child source closure excludes `pkg.hidden`. Independent checker returns `INDETERMINATE/GRAPH_SOURCE_IMPORT_MISMATCH`; no positive manifest is prepared.

## 24. P0/P1B
CONTRACT_PROVED: Existing positive source-evidence and P0/P1B regressions pass in the focused suite. No P0/P1B code or excluded-source positive proof was added.

## 25. MANIFEST V2
CONTRACT_PROVED: Existing manifest v2 tests pass; the excluded-child case has no positive manifest. No manifest schema changed.

## 26. OFFICIAL ISOLATED FULL
DIRECT_EVIDENCE: Existing D2B3 official isolated FULL regression passes in the focused suite. No FULL on active Contextor.

## 27. RECEIPT V2
CONTRACT_PROVED: Existing isolated receipt v2 regression passes; no receipt schema changed and no excluded-source receipt was fabricated.

## 28. FOCUSED PYTEST RESULTS
DIRECT_EVIDENCE: Specified eight-module focused suite: 495 passed in 87.54s; exit 0, stopwatch 90.05s. No global suite run.

## 29. EXACT COMMANDS/EXIT CODES
DIRECT_EVIDENCE: `.\.venv\Scripts\python.exe -m py_compile contextor/core/symbol_engine/indexer.py`: exit 0, 0.31s. `.\.venv\Scripts\python.exe -m pytest -q tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_evidence.py tests/test_original_worker_full_preparation_optin.py tests/test_original_worker_full_receipt_optin.py tests/test_original_worker_official_full_live_publication.py`: exit 0, stopwatch 90.05s. `git diff --check --` for the three source/test paths: exit 0.

## 30. FILES_CHANGED
DIRECT_EVIDENCE: `contextor/core/symbol_engine/indexer.py`; `tests/test_p1d3_d2b2_type_only.py`; `tests/test_p1d3_package_cycle_integration.py`. `walkthrough.md` is the report and excluded from the production/test file list.

## 31. FULL ACTUAL_DIFF
Complete unabridged `git diff --no-color` for every FILES_CHANGED path:

```diff
diff --git a/contextor/core/symbol_engine/indexer.py b/contextor/core/symbol_engine/indexer.py
index e6df35a..2ac3a7b 100644
--- a/contextor/core/symbol_engine/indexer.py
+++ b/contextor/core/symbol_engine/indexer.py
@@ -73,7 +73,7 @@ SYMBOL_FACTS_SCHEMA_VERSION = 2
 REFERENCE_FACTS_SCHEMA_VERSION = 1
 COLLISION_FACTS_SCHEMA_VERSION = 1
 TEST_FACTS_SCHEMA_VERSION = 1
-IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 5
+IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 6
 _SYMBOL_FACTS_AVAILABLE = "available"
 _SYMBOL_FACTS_FAILURE = "failure"
 _SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
@@ -567,20 +567,49 @@ def _project_typing_imports_closed(
                 or not target_name
                 or not all(
                     part.isidentifier()
-                    for part
-                    in target_name.split(".")
+                    for part in target_name.split(".")
                 )
             ):
                 return False
 
-            if (
-                target_name not in indexed
-                and (
-                    target_name + ".__init__"
-                ) not in indexed
+            indexed_module = (
+                target_name in indexed
+            )
+
+            indexed_package = (
+                target_name + ".__init__"
+            ) in indexed
+
+            if not (
+                indexed_module
+                or indexed_package
             ):
                 return False
 
+            if (
+                import_ref.is_from_import
+                and indexed_package
+            ):
+                for member in import_ref.names:
+                    if (
+                        type(member) is not str
+                        or not member.isidentifier()
+                        or member.startswith("__")
+                    ):
+                        return False
+
+                    child_name = (
+                        target_name + "." + member
+                    )
+
+                    if (
+                        child_name not in indexed
+                        and (
+                            child_name + ".__init__"
+                        ) not in indexed
+                    ):
+                        return False
+
     return True
 
 
@@ -2435,6 +2464,7 @@ def index_repository(
     if extra_ignored_dirs:
         ignored_dirs.update(extra_ignored_dirs)
 
+    unindexed_python_sources_present = False
     file_discovery_started = time.monotonic()
 
     files_to_process = []
@@ -2444,7 +2474,11 @@ def index_repository(
         if not path.is_file():
             continue
         rel = path.relative_to(root_path)
-        if any(part in ignored_dirs for part in rel.parts):
+        if any(
+            part in ignored_dirs
+            for part in rel.parts
+        ):
+            unindexed_python_sources_present = True
             continue
         if excludes:
             rel_str = rel.as_posix()
@@ -2455,6 +2489,7 @@ def index_repository(
                     is_excluded = True
                     break
             if is_excluded:
+                unindexed_python_sources_present = True
                 continue
         files_to_process.append(path)
 
@@ -2503,6 +2538,7 @@ def index_repository(
         )
         project_effects_closed = (
             not skipped
+            and not unindexed_python_sources_present
             and len(opaque_effects_by_module)
             == len(modules)
             and all(
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 72f476e..1b384a2 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4,6 +4,8 @@ from __future__ import annotations
 
 import ast
 import json
+import subprocess
+import sys
 from dataclasses import replace
 from pathlib import Path
 
@@ -74,6 +76,19 @@ D2B4_R1_LAUNCHERS = [
     ),
 ]
 
+D2B5_EXCLUDED_CHILD = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/hidden.py": "import typing\ntyping.TYPE_CHECKING = True\n",
+    "pkg/launcher.py": "from pkg import hidden\nimport pkg.a\n",
+}
+
 D2B2_R1_GLOBALS_MUTATION = {
     "pkg/__init__.py": "pass\n",
     "pkg/a.py": (
@@ -386,8 +401,8 @@ def _inline_workers(monkeypatch):
     monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
 
 
-def _index_graph(root):
-    index = indexer.index_repository(str(root))
+def _index_graph(root, **kwargs):
+    index = indexer.index_repository(str(root), **kwargs)
     reexport_facts = materialize_reexport_facts_by_module(
         index.modules,
         index.reference_facts_by_module,
@@ -455,6 +470,288 @@ def _cache_data(root: Path, source: Path) -> dict:
     )["data"]
 
 
+def _assert_d2b5_hard_scc(index, graph, target):
+    guarded = next(
+        item for item in index.modules["pkg.a"].imports
+        if item.module == target and not item.is_from_import
+    )
+    assert guarded.type_only is False
+    assert target in graph.hard_edges["pkg.a"]
+    assert "pkg.a" in graph.hard_edges[target]
+    assert target not in graph.soft_edges["pkg.a"]
+    assert any(
+        set(members) == {"pkg.a", target}
+        for members in _scc_signature(index, graph)
+    )
+
+
+def test_p1d3_d2b5_excluded_child_keeps_hard_scc(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B5_EXCLUDED_CHILD)
+    source_local, error = indexer.read_imports(root / "pkg" / "a.py")
+    assert error is None
+    assert next(item for item in source_local if item.module == "pkg.c").type_only
+    index, graph = _index_graph(root, excludes=["pkg/hidden.py"])
+    assert "pkg.hidden" not in index.modules
+    assert {"pkg.a", "pkg.c", "pkg.launcher"} <= set(index.modules)
+    assert not index.skipped
+    _assert_d2b5_hard_scc(index, graph, "pkg.c")
+    assert indexer._project_typing_imports_closed(index.modules) is False
+    assert run_synthetic_import(root, "pkg.a").returncode == 0
+    assert run_synthetic_import(root, "pkg.c").returncode == 0
+    failed = run_synthetic_import(root, "pkg.launcher")
+    assert failed.returncode != 0
+    assert "partially initialized module" in failed.stderr
+    assert "pkg.a" in failed.stderr
+
+
+def test_p1d3_d2b5_excluded_local_typing_shadow(
+    tmp_path, isolated_dirs,
+):
+    fixture = {**D2B_NAME_SAFE, "typing.py": "TYPE_CHECKING = True\n"}
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    source_local, error = indexer.read_imports(root / "pkg" / "a.py")
+    assert error is None
+    assert next(item for item in source_local if item.module == "pkg.b").type_only
+    index, graph = _index_graph(root, excludes=["typing.py"])
+    assert "typing" not in index.modules
+    _assert_d2b5_hard_scc(index, graph, "pkg.b")
+    program = (
+        "import sys;"
+        "assert 'typing' not in sys.modules;"
+        "sys.path.insert(0, sys.argv[1]);"
+        "import pkg.a"
+    )
+    failed = subprocess.run(
+        [sys.executable, "-I", "-S", "-B", "-c", program, str(root.resolve())],
+        capture_output=True, text=True, timeout=8, check=False,
+    )
+    assert failed.returncode != 0
+    assert "partially initialized module" in failed.stderr
+
+
+@pytest.mark.parametrize(
+    "case,extra,kwargs",
+    [
+        ("X01", {"typing.py": "TYPE_CHECKING = True\n"}, {"excludes": ["typing.py"]}),
+        ("X02", {"pkg/hidden.py": "pass\n"}, {"excludes": ["pkg/hidden.py"]}),
+        ("X03", {"hidden/unrelated.py": "pass\n"}, {"extra_ignored_dirs": {"hidden"}}),
+        ("X04", {"build/unrelated.py": "pass\n"}, {}),
+        ("X05", {}, {"excludes": ["nonexistent.py"]}),
+    ],
+)
+def test_p1d3_d2b5_exclusion_matrix(
+    tmp_path, isolated_dirs, case, extra, kwargs,
+):
+    root = write_synthetic_repository(tmp_path / case, {**D2B_NAME_SAFE, **extra})
+    index, graph = _index_graph(root, **kwargs)
+    guarded = next(
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    )
+    assert guarded.type_only is (case == "X05")
+    assert ("pkg.b" in graph.hard_edges["pkg.a"]) is (case != "X05")
+    assert ("pkg.b" in graph.soft_edges["pkg.a"]) is (case == "X05")
+
+
+def test_p1d3_d2b5_package_prefix_exclude(
+    tmp_path, isolated_dirs,
+):
+    fixture = {
+        "app/__init__.py": "pass\n",
+        "app/a.py": (
+            "from typing import TYPE_CHECKING\n"
+            "if TYPE_CHECKING:\n"
+            "    import app.b\n"
+            "value = 1\n"
+        ),
+        "app/b.py": "from app.a import value\n",
+        "pkg/hidden.py": "pass\n",
+    }
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    index, graph = _index_graph(root, excludes=["pkg"])
+    assert "pkg.hidden" not in index.modules
+    assert next(
+        item for item in index.modules["app.a"].imports
+        if item.module == "app.b"
+    ).type_only is False
+    assert "app.b" in graph.hard_edges["app.a"]
+
+
+def test_p1d3_d2b5_source_visibility_toggle(
+    tmp_path, isolated_dirs,
+):
+    fixture = {**D2B_NAME_SAFE, "unrelated.py": "pass\n"}
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    original_a = (root / "pkg" / "a.py").read_bytes()
+    original_b = (root / "pkg" / "b.py").read_bytes()
+    states = []
+    for excludes in (None, ["unrelated.py"], None):
+        index, graph = _index_graph(root, excludes=excludes)
+        states.append((
+            next(
+                item for item in index.modules["pkg.a"].imports
+                if item.module == "pkg.b"
+            ).type_only,
+            "pkg.b" in graph.hard_edges["pkg.a"],
+            "pkg.b" in graph.soft_edges["pkg.a"],
+        ))
+        assert _cache_data(root, root / "pkg" / "a.py")[
+            "import_classification_semantics_version"
+        ] == 6
+    assert states == [(True, False, True), (False, True, False), (True, False, True)]
+    assert (root / "pkg" / "a.py").read_bytes() == original_a
+    assert (root / "pkg" / "b.py").read_bytes() == original_b
+
+
+D2B5_IMPORTFROM_NEGATIVES = [
+    ("F01", "from pkg import absent\n", {}, None),
+    ("F02", "from pkg import b, absent\n", {}, None),
+    ("F03", "from pkg import __path__\n", {}, None),
+    ("F04", "from pkg import child\n", {"pkg/child.py": "pass\n"}, ["pkg/child.py"]),
+    ("F05", "from pkg.sub import child\n", {"pkg/sub/__init__.py": "pass\n"}, None),
+    ("F06", "from typing import Any\n", {}, None),
+]
+
+
+@pytest.mark.parametrize("case,source,extra,excludes", D2B5_IMPORTFROM_NEGATIVES)
+def test_p1d3_d2b5_importfrom_negative_matrix(
+    tmp_path, isolated_dirs, case, source, extra, excludes,
+):
+    fixture = {**D2B_NAME_SAFE, "pkg/reader.py": source, **extra}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    index, graph = _index_graph(root, excludes=excludes)
+    assert indexer._project_typing_imports_closed(index.modules) is False
+    _assert_d2b5_hard_scc(index, graph, "pkg.b")
+    cold_imports = _import_signature(index)
+    cold_graph = _graph_signature(index, graph)
+    warm_index, warm_graph = _index_graph(root, excludes=excludes)
+    assert _import_signature(warm_index) == cold_imports
+    assert _graph_signature(warm_index, warm_graph) == cold_graph
+
+
+D2B5_IMPORTFROM_POSITIVES = [
+    ("P01", "from pkg.a import value\n", {}),
+    ("P02", "from pkg import b\n", {}),
+    ("P03", "from pkg import b as alias\n", {}),
+    ("P04", "from pkg import b, c\n", {"pkg/c.py": "pass\n"}),
+    (
+        "P05", "from pkg.sub import child\n",
+        {"pkg/sub/__init__.py": "pass\n", "pkg/sub/child.py": "pass\n"},
+    ),
+    ("P06", "from typing import TYPE_CHECKING\n", {}),
+]
+
+
+@pytest.mark.parametrize("case,source,extra", D2B5_IMPORTFROM_POSITIVES)
+def test_p1d3_d2b5_importfrom_positive_matrix(
+    tmp_path, isolated_dirs, case, source, extra,
+):
+    fixture = {**D2B_NAME_SAFE, "pkg/reader.py": source, **extra}
+    root = write_synthetic_repository(tmp_path / case, fixture)
+    index, graph = _index_graph(root)
+    assert indexer._project_typing_imports_closed(index.modules) is True
+    guarded = next(
+        item for item in index.modules["pkg.a"].imports
+        if item.module == "pkg.b"
+    )
+    assert guarded.type_only is True
+    assert "pkg.b" in graph.soft_edges["pkg.a"]
+    assert "pkg.b" not in graph.hard_edges["pkg.a"]
+    cold_imports = _import_signature(index)
+    cold_graph = _graph_signature(index, graph)
+    warm_index, warm_graph = _index_graph(root)
+    assert _import_signature(warm_index) == cold_imports
+    assert _graph_signature(warm_index, warm_graph) == cold_graph
+
+
+@pytest.mark.parametrize(
+    "case,fixture,kwargs",
+    [
+        ("safe", D2B_NAME_SAFE, {}),
+        ("excluded-child", D2B5_EXCLUDED_CHILD, {"excludes": ["pkg/hidden.py"]}),
+        (
+            "excluded-typing",
+            {**D2B_NAME_SAFE, "typing.py": "TYPE_CHECKING = True\n"},
+            {"excludes": ["typing.py"]},
+        ),
+        (
+            "ignored-unrelated",
+            {**D2B_NAME_SAFE, "build/unrelated.py": "pass\n"},
+            {},
+        ),
+        (
+            "indexed-child",
+            {**D2B_NAME_SAFE, "pkg/reader.py": "from pkg import b\n"},
+            {},
+        ),
+        (
+            "missing-child",
+            {**D2B_NAME_SAFE, "pkg/reader.py": "from pkg import absent\n"},
+            {},
+        ),
+    ],
+)
+def test_p1d3_d2b5_inline_process_pool_parity(
+    tmp_path, isolated_dirs, monkeypatch, case, fixture, kwargs,
+):
+    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    inline_index, inline_graph = _index_graph(inline_root, **kwargs)
+
+    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
+    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
+    pool_index, pool_graph = _index_graph(pool_root, **kwargs)
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
+@pytest.mark.parametrize(
+    "fixture,excludes",
+    [
+        (D2B5_EXCLUDED_CHILD, ["pkg/hidden.py"]),
+        ({**D2B_NAME_SAFE, "pkg/reader.py": "from pkg import absent\n"}, None),
+    ],
+    ids=["excluded-child", "incomplete-child"],
+)
+def test_p1d3_d2b5_original_worker_reindex_same_domain(
+    tmp_path, isolated_dirs, fixture, excludes,
+):
+    root = write_synthetic_repository(tmp_path / "repo", fixture)
+    original, graph = _index_graph(root, excludes=excludes)
+    plan = plan_original_worker_reindex(original, graph.hard_edges)
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    assert plan.selected_module_ids
+    captured, captured_graph = _index_graph(
+        root,
+        excludes=excludes,
+        source_capture_module_ids=plan.selected_module_ids,
+    )
+    assert captured.original_worker_capture_status == (
+        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
+    )
+    assert captured_graph.hard_edges == graph.hard_edges
+    assert captured_graph.soft_edges == graph.soft_edges
+    assert captured.source_fingerprints_by_module == (
+        original.source_fingerprints_by_module
+    )
+    assert plan.selected_module_ids.issubset(
+        captured.original_worker_source_snapshots
+    )
+    for module_id in plan.selected_module_ids:
+        assert captured.original_worker_source_snapshots[
+            module_id
+        ].source_fingerprint == captured.source_fingerprints_by_module[module_id]
+
+
 D2B4_MUTATIONS = [
     ("M01", "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n"),
     ("M02", 'import typing\nsetattr(typing, "TYPE_CHECKING", True)\nimport pkg.a\n'),
@@ -573,7 +870,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 5
+    assert cached["import_classification_semantics_version"] == 6
     assert cached["typing_guard_marker_mutation"] is True
     cached["import_classification_semantics_version"] = 3
     cached["typing_guard_marker_mutation"] = False
@@ -582,7 +879,7 @@ def test_p1d3_d2b4_forged_stale_launcher_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 5
+    assert rewritten["import_classification_semantics_version"] == 6
     assert rewritten["typing_guard_marker_mutation"] is True
 
 
@@ -770,7 +1067,7 @@ def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
     _index_graph(root)
     source = root / "pkg" / "launcher.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 5
+    assert cached["import_classification_semantics_version"] == 6
     assert cached["typing_guard_marker_mutation"] is False
     assert cached["typing_guard_opaque_effects"] is True
     cached["import_classification_semantics_version"] = 4
@@ -780,7 +1077,7 @@ def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
     index, graph = _index_graph(root)
     _assert_d2b4_launcher_graph(index, graph)
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 5
+    assert rewritten["import_classification_semantics_version"] == 6
     assert rewritten["typing_guard_opaque_effects"] is True
 
 
@@ -863,7 +1160,7 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
     cold_graph_signature = _graph_signature(cold_index, cold_graph)
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 5
+    assert cached["import_classification_semantics_version"] == 6
     assert next(
         item for item in cached["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -881,8 +1178,8 @@ def test_cold_and_warm_worker_cache_match_type_only_graph(
 
 
 @pytest.mark.parametrize(
-    "stored_version", [None, 0, 1, 2, 3, 4],
-    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4"],
+    "stored_version", [None, 0, 1, 2, 3, 4, 5],
+    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5"],
 )
 def test_stale_import_classification_cache_reparses_same_snapshot(
     tmp_path, isolated_dirs, stored_version, monkeypatch,
@@ -926,7 +1223,7 @@ def test_stale_import_classification_cache_reparses_same_snapshot(
         for item in result.modules["pkg.a"].imports
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 5
+    assert rewritten["import_classification_semantics_version"] == 6
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is True
@@ -1230,7 +1527,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
 
     source = root / "pkg" / "a.py"
     cached = _cache_data(root, source)
-    assert cached["import_classification_semantics_version"] == 5
+    assert cached["import_classification_semantics_version"] == 6
     forged_imports = [
         item for item in cached["imports"] if item["module"] == "pkg.b"
     ]
@@ -1252,7 +1549,7 @@ def test_d2b2_r1_forged_version_one_cache_is_reparsed(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, source)
-    assert rewritten["import_classification_semantics_version"] == 5
+    assert rewritten["import_classification_semantics_version"] == 6
     assert next(
         item for item in rewritten["imports"] if item["module"] == "pkg.b"
     )["type_only"] is False
@@ -1464,7 +1761,7 @@ def test_d2b2_r2_worker_success_returns_and_warm_cache(
     ]
     assert warm["source_fingerprint"] == cold["source_fingerprint"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 5
+    assert cached["import_classification_semantics_version"] == 6
     assert type(cached["typing_guard_initializer_passive"]) is bool
     assert cached["typing_guard_initializer_passive"] is expected_passive
     assert cached["typing_guard_marker_mutation"] is cold[
@@ -1483,7 +1780,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     parent = root / "pkg" / "__init__.py"
     original_fingerprint = original.source_fingerprints_by_module["pkg.__init__"]
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 5
+    assert cached["import_classification_semantics_version"] == 6
     assert cached["typing_guard_initializer_passive"] is False
     cached["typing_guard_initializer_passive"] = True
     cached["import_classification_semantics_version"] = 2
@@ -1501,7 +1798,7 @@ def test_d2b2_r2_forged_stale_parent_cache_rejected(
     assert graph.hard_edges["pkg.a"] == {"pkg.b"}
     assert graph.hard_edges["pkg.b"] == {"pkg.a"}
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 5
+    assert rewritten["import_classification_semantics_version"] == 6
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
@@ -1519,7 +1816,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
     _index_graph(root)
     parent = root / "pkg" / "__init__.py"
     cached = _cache_data(root, parent)
-    assert cached["import_classification_semantics_version"] == 5
+    assert cached["import_classification_semantics_version"] == 6
     if case == "missing":
         cached.pop("typing_guard_initializer_passive")
     else:
@@ -1557,7 +1854,7 @@ def test_d2b2_r2_malformed_current_parent_cache_rejected(
         for members in _scc_signature(replayed, graph)
     )
     rewritten = _cache_data(root, parent)
-    assert rewritten["import_classification_semantics_version"] == 5
+    assert rewritten["import_classification_semantics_version"] == 6
     assert type(rewritten["typing_guard_initializer_passive"]) is bool
     assert rewritten["typing_guard_initializer_passive"] is False
 
diff --git a/tests/test_p1d3_package_cycle_integration.py b/tests/test_p1d3_package_cycle_integration.py
index c1d6daa..ad1aa4b 100644
--- a/tests/test_p1d3_package_cycle_integration.py
+++ b/tests/test_p1d3_package_cycle_integration.py
@@ -270,6 +270,19 @@ D2B4_R1_ALIAS_LAUNCHER = {
     ),
 }
 
+D2B5_EXCLUDED_CHILD = {
+    "pkg/__init__.py": "pass\n",
+    "pkg/a.py": (
+        "from typing import TYPE_CHECKING\n"
+        "if TYPE_CHECKING:\n"
+        "    import pkg.c\n"
+        "value = 1\n"
+    ),
+    "pkg/c.py": "from pkg.a import value\n",
+    "pkg/hidden.py": "import typing\ntyping.TYPE_CHECKING = True\n",
+    "pkg/launcher.py": "from pkg import hidden\nimport pkg.a\n",
+}
+
 D2B3_SOURCE_BOUND_NEGATIVES = [
     (
         "N01-no-marker",
@@ -1052,8 +1065,8 @@ def test_p1d3_d1_official_isolated_full_receipt(
         assert calls == [root.resolve()]
 
 
-def _d2a_canonical_index_graph(root):
-    index = index_repository(str(root))
+def _d2a_canonical_index_graph(root, **kwargs):
+    index = index_repository(str(root), **kwargs)
 
     facts = materialize_reexport_facts_by_module(
         index.modules,
@@ -1228,6 +1241,49 @@ def test_p1d3_d2b4_launcher_source_checker_fails_closed(
     assert prepared.manifest is None
 
 
+def test_p1d3_d2b5_excluded_child_source_checker_fails_closed(
+    tmp_path, isolated_dirs,
+):
+    root = write_synthetic_repository(tmp_path / "repo", D2B5_EXCLUDED_CHILD)
+    excludes = ["pkg/hidden.py"]
+    index, graph = _d2a_canonical_index_graph(root, excludes=excludes)
+    assert "pkg.hidden" not in index.modules
+    assert graph.hard_edges["pkg.a"] == {"pkg.c"}
+    assert graph.hard_edges["pkg.c"] == {"pkg.a"}
+    plan = plan_original_worker_reindex(index, graph.hard_edges)
+    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
+    captured, captured_graph = _d2a_canonical_index_graph(
+        root, excludes=excludes,
+        source_capture_module_ids=plan.selected_module_ids,
+    )
+    assert captured_graph.hard_edges == graph.hard_edges
+    assert captured.source_fingerprints_by_module == (
+        index.source_fingerprints_by_module
+    )
+    parsed = {
+        module: parse_source_snapshot(snapshot, module)
+        for module, snapshot in captured.original_worker_source_snapshots.items()
+    }
+    closure = compute_cycle_model_source_closures(graph.hard_edges)
+    assert len(closure) == 1
+    assert "pkg.hidden" not in closure[0].evidence_source_modules
+    consistency = assess_package_graph_consistency(
+        graph.hard_edges,
+        {module_id: source.tree for module_id, source in parsed.items()},
+        closure[0].evidence_source_modules,
+    )
+    assert consistency.status == "INDETERMINATE"
+    assert consistency.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
+    evidence = build_source_bound_cycle_evidence(graph.hard_edges, parsed)
+    assert evidence.scenarios.components[0].classification != (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
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
DIRECT_EVIDENCE: None requiring implementation deviation. The existing matcher does not match `pkg/` as a directory prefix, so X06 used the explicitly authorized spelling `pkg`.

## 33. DESIGN_GAPS
DIRECT_EVIDENCE: None encountered for the literal D2B-5 patch.

## 34. UNKNOWN / UNSUPPORTED
UNKNOWN: Active LIVE loaded-code adoption, arbitrary Python runtime behavior outside the specified domain and global-suite result were not established.

## 35. FINAL IMPLEMENTER OBSERVATION
DIRECT_EVIDENCE: Literal D2B-5 implementation and focused validation complete; architectural acceptance remains with ChatGPT. STOP after D2B-5.
