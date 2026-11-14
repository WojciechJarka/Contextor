# P5-FINAL-R3 — SCC02 source contract reconciliation

## PREFLIGHT

- DIRECT_EVIDENCE — Contextor MCP was queried first. Pre-change canonical LIVE revision was 1401, canonical_state fresh, provenance live. Per-file contexts for tests/test_cycle_semantics_scc02_entry_order.py and contextor/ui/gui.py reported workspace_sync verified and zero syntax errors. contextor/core/cycle_semantics/package_model.py was also verified at revision 1401 with zero syntax errors.
- DIRECT_EVIDENCE — Git HEAD: b72f93d0a63308dc2fd54709d5e73a3015d2f747. Pre-change status contained only the existing walkthrough.md modification from P5-FINAL-R2. CPython: 3.15.2.
- DIRECT_EVIDENCE — Exact anchors were present: _real_tree at test line 25; _from at 33; _definition at 49; the two named tests at 151 and 196; ContextorGUI at gui.py:180; open_repo_builder at :480; method-local import and following call assignment at :485-486; module-level run at :2483. There was no top-level run_repo_generator import.
- DIRECT_EVIDENCE — Test changes were limited to tests/test_cycle_semantics_scc02_entry_order.py. Production source was not edited.

## HISTORICAL_SOURCE_CONTRACT

- DIRECT_EVIDENCE — Commit b6bcfb118c54c0f6d85cb9969c80dba381d49f86 introduced both historical assertions on 2026-10-14. _from searches tree.body only and requires a module-body ast.ImportFrom.
- DIRECT_EVIDENCE — Commit 56dd18d3495c08b3d46981ffdd36fed323e7f661 moved the import on 2026-11-08 from gui.py's module body into the else branch of ContextorGUI.open_repo_builder. The exact current code is gui.py:480-486.
- DIRECT_EVIDENCE — The M05-I1 task and implementation/report followed on 2026-11-10. The GUI import move therefore preceded M05. M05-I1/I2/I3 production diffs did not touch gui.py or this test module.
- DIRECT_EVIDENCE — Current test assertions inspected source AST placement only. They did not import or execute the real GUI. The tests’ synthetic SCC02 projections and semantic assertions are unchanged.

## ACCEPTED_LAZY_IMPORT_BEHAVIOR

- DIRECT_EVIDENCE — The 56dd18d walkthrough records the approved method-scoped import and regression test test_scc2_gui_generator_import_remains_method_scoped. That earlier task's focused CPython import-order and export checks passed; its targeted subset recorded 30 passed.
- DIRECT_EVIDENCE — Current gui.py has exactly one ImportFrom of contextor.repo_generator.run_repo_generator, located in open_repo_builder's else branch immediately before the assignment call. There is no matching module-level ImportFrom.
- CONTRACT_PROVED — R3 preserves this accepted production behavior and changes only source tests that incorrectly require the old module-level location.

## EXACT_AST_HELPER

Added _gui_builder_lazy_import immediately after _definition. It:

- resolves the top-level ContextorGUI class using the existing _definition helper;
- selects exactly one open_repo_builder method and one ast.If in that method;
- requires exactly one unaliased, level-zero ImportFrom for run_repo_generator in the if statement's else branch;
- requires exactly one direct assignment call to run_repo_generator in that branch and verifies import-before-call ordering;
- asserts that no matching ImportFrom exists in the GUI module body;
- returns the import and call AST nodes.

The existing _from and _definition helpers were not modified or broadened.

## FIRST_TEST_CORRECTION

In test_scc02_source_chain_still_exists, the four existing lexical import checks for repo_generator, main, filters, and ui remain unchanged. Only the final GUI module-body _from assertion was replaced with _gui_builder_lazy_import(gui).

## SECOND_TEST_CORRECTION

In test_scc02_reexport_bindings_follow_imports, both existing assertions for FilterWindow-before-run_repo_generator and theme-before-FilterWindow remain unchanged. Only the final GUI module-body ordering assertion was replaced with the returned method-local import and call ordering check.

## SYNTHETIC_SCC02_PROJECTION_UNCHANGED

- DIRECT_EVIDENCE — The synthetic _projection fixture and all import-order/model assertions below the two historical source tests were not changed.
- DIRECT_EVIDENCE — No production code, GUI source, package_model.py, SCC02 semantic expectation, or unrelated test was edited.

## TWO_NODE_RESULTS

- DIRECT_EVIDENCE — First required gate: .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_scc02_entry_order.py::test_scc02_source_chain_still_exists tests/test_cycle_semantics_scc02_entry_order.py::test_scc02_reexport_bindings_follow_imports -rs → 2 passed in 2.16s.
- DIRECT_EVIDENCE — Discovery located tests/test_cycle_semantics_scc2_import_order_regression.py::test_scc2_gui_generator_import_remains_method_scoped at line 98.
- DIRECT_EVIDENCE — Related regression node: .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_scc2_import_order_regression.py::test_scc2_gui_generator_import_remains_method_scoped -rs → 1 passed in 0.44s.
- DIRECT_EVIDENCE — git diff --check exited 0. Git printed only LF-to-CRLF working-copy notices for walkthrough.md and the changed test file; there were no whitespace errors.
- DIRECT_EVIDENCE — No broad SCC02 suite, full pytest, FULL, semantic refresh, update_file, or restart was run.

## METHOD_SCOPED_REGRESSION_RESULT

- DIRECT_EVIDENCE — The exact existing regression passed after the two historical tests were corrected. This supports the current AST contract that the import stays method-scoped.
- LIMIT — The checks are bounded source/fixture regressions; this result is not a general runtime-safety certification for the GUI or arbitrary import orders.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE — The first post-change parallel query observed a revision transition: the SCC02 test context answered at revision 1401 with workspace_sync=out_of_sync while gui.py and package_model.py were already verified at revision 1402. The test-file query was repeated against canonical state rather than refreshing semantics.
- DIRECT_EVIDENCE — Final canonical LIVE revision: 1402, provenance live, canonical_state fresh. Project-wide workspace_sync remains unverified. Per-file workspace_sync is verified for tests/test_cycle_semantics_scc02_entry_order.py, contextor/ui/gui.py, and contextor/core/cycle_semantics/package_model.py, all at revision 1402.
- DIRECT_EVIDENCE — Syntax diagnostics: zero project syntax errors; each of the three target files reports checked_and_none at revision 1402.
- DIRECT_EVIDENCE — Structural cycle diagnostics remain fresh at 16 normalized DFS back-edge paths. This is not an SCC count. One hard-union-soft potential cycle remains separately reported.
- DIRECT_EVIDENCE — cycle_semantics remains stale at revision 1402. No semantic refresh was requested or performed.

## FULL_DIFFS

FILES_CHANGED:

- tests/test_cycle_semantics_scc02_entry_order.py
- walkthrough.md (report only)

Complete actual diff for the changed test file:

~~~diff
diff --git a/tests/test_cycle_semantics_scc02_entry_order.py b/tests/test_cycle_semantics_scc02_entry_order.py
index 5198f83..5befc5b 100644
--- a/tests/test_cycle_semantics_scc02_entry_order.py
+++ b/tests/test_cycle_semantics_scc02_entry_order.py
@@ -60,6 +60,62 @@ def _definition(tree, name):
     assert len(found) == 1
     return found[0]
 
 
+def _gui_builder_lazy_import(tree):
+    gui_class = _definition(tree, "ContextorGUI")
+    methods = [
+        stmt
+        for stmt in gui_class.body
+        if isinstance(stmt, ast.FunctionDef)
+        and stmt.name == "open_repo_builder"
+    ]
+    assert len(methods) == 1
+    method = methods[0]
+
+    branches = [
+        stmt
+        for stmt in method.body
+        if isinstance(stmt, ast.If)
+    ]
+    assert len(branches) == 1
+    branch = branches[0]
+
+    imports = [
+        stmt
+        for stmt in branch.orelse
+        if isinstance(stmt, ast.ImportFrom)
+        and stmt.module == "contextor.repo_generator"
+        and stmt.level == 0
+        and len(stmt.names) == 1
+        and stmt.names[0].name == "run_repo_generator"
+        and stmt.names[0].asname is None
+    ]
+    assert len(imports) == 1
+
+    calls = [
+        stmt
+        for stmt in branch.orelse
+        if isinstance(stmt, ast.Assign)
+        and isinstance(stmt.value, ast.Call)
+        and isinstance(stmt.value.func, ast.Name)
+        and stmt.value.func.id == "run_repo_generator"
+    ]
+    assert len(calls) == 1
+
+    assert imports[0].lineno < calls[0].lineno
+
+    assert not any(
+        isinstance(stmt, ast.ImportFrom)
+        and stmt.module == "contextor.repo_generator"
+        and any(
+            alias.name == "run_repo_generator"
+            for alias in stmt.names
+        )
+        for stmt in tree.body
+    )
+
+    return imports[0], calls[0]
+
+
 def _projection():
@@ -186,11 +242,7 @@ def test_scc02_source_chain_still_exists():
         "run",
         level=1,
     )
-    _from(
-        gui,
-        "contextor.repo_generator",
-        "run_repo_generator",
-    )
+    _gui_builder_lazy_import(gui)
 
 
 def test_scc02_reexport_bindings_follow_imports():
@@ -222,14 +274,8 @@ def test_scc02_reexport_bindings_follow_imports():
     ).lineno
 
-    assert _from(
-        gui,
-        "contextor.repo_generator",
-        "run_repo_generator",
-    ).lineno < _definition(
-        gui,
-        "run",
-    ).lineno
+    gui_import, gui_call = _gui_builder_lazy_import(gui)
+    assert gui_import.lineno < gui_call.lineno
~~~

ACTUAL_DIFF for walkthrough.md is excluded by the reporting convention. Production diff: NONE.

## FINAL_VERDICT

PASS for P5-FINAL-R3's exact test-only source-contract reconciliation. Both named SCC02 nodes and the accepted method-scoped-import regression passed; diff-check passed; Contextor reports the changed test synchronized at LIVE revision 1402 with zero syntax errors. GUI and package_model were not changed. cycle_semantics remains stale and was not refreshed.

No test changes beyond the specified helper and two assertions were made. No Git staging, commit, push, index/history mutation, broad SCC02 run, full pytest, FULL, restart, or update_file occurred.
