# F1H — unproved `TYPE_CHECKING` value

## PREFLIGHT

- Applicable `AGENTS.md` instructions were followed. Contextor MCP was queried before literal source inspection. Both target files were available and source-synchronized at canonical revision 1197, with fresh zero-error syntax diagnostics; `cycle_semantics` was stale.
- Initial HEAD: `d43867eb53e018e27641d1fb683da45d910f1adb`. The only pre-existing worktree change was the F1G report in `walkthrough.md`; both requested source/test files were clean.
- Exact anchor in `_compile` was `selected = stmt.orelse` at `package_model.py:873`. The existing `UNMODELED_STATEMENT` step and its UNKNOWN execution handler were already present. No other accepting branch for this recognized typing-guard condition was found on the checked `_compile` path.

## EXACT_IMPLEMENTATION

- Replaced only the recognized typing-guard `ast.If` branch's `selected = stmt.orelse` with `steps.append(_Step("UNMODELED_STATEMENT")); return tuple(steps)` (two source lines). Constant-bool and `__name__` conditions are unchanged.
- The earlier import step remains in the returned prefix. In ordinary mode, reaching the unmodeled external `typing` import returns UNKNOWN with `reached_unmodeled_import.target == "typing"`. In conditional mode, the explicit passive-external policy records the assumed import, then the preserved `UNMODELED_STATEMENT` prevents `CONDITIONAL_MODEL_PASS`.
- No typing recognizer, indexer, hard/soft graph, SCC, receipt, Desktop, or MCP server code was edited.

## REGRESSION_TESTS

- Added one parameterized test with NAME (`from typing import TYPE_CHECKING`) and ATTRIBUTE (`import typing`) forms. Both use the specified `pkg/__init__.py`, `pkg/ns/a.py`, and `pkg/ns/b.py` source bytes in an AST/`SearchPortion` inventory.
- The ordinary evaluator requires a package initializer before it can reach `pkg.ns.a`. Its test input therefore includes a **model-only** empty `pkg.ns.__init__` AST; this is not a repository source file. The conditional evaluator receives the unaugmented namespace source inventory and its existing `SearchPortion` contract. Initial execution without that model-only initializer stopped at `pkg.ns` with UNKNOWN and no reached-import provenance; the targeted fixture correction made the import-effect assertion meaningful.
- For each form the test asserts ordinary UNKNOWN, reached target `typing`, conditional UNKNOWN, nested model UNKNOWN, recorded assumed external target `typing`, and absence of ordinary/conditional MODEL_PASS.
- Existing positive controls remain unchanged: `opaque_dependency` without a typing guard still yields `CONDITIONAL_MODEL_PASS` under the explicit passive-import policy; an uncalled function-local external import still yields ordinary `MODEL_PASS`. UNKNOWN is not classified as a confirmed import hazard.

## TARGETED_TEST_RESULTS

- `tests/test_cycle_semantics_external_import_authority.py`: **6 passed** (including both new variants and both controls). The first run had two fixture failures because ordinary evaluation stopped before the external import at an unsupported namespace parent; the model-only initializer resolved this test setup issue. Final run passed.
- `tests/test_cycle_semantics_package_model.py` selected external-assumption, reached-unmodeled-import, and existing guard-control cases: **11 passed, 195 deselected**. The `-k` filter also deselected two explicitly named integration nodes in that invocation; they were run separately.
- Direct integration guard controls `test_p1d3_d2b_name_guard_inactive` and `test_p1d3_d2b_attribute_guard_inactive`: **2 passed**.
- `git diff --check` for both changed source/test files passed. No full pytest suite was run; no existing expectations were changed.

## POST_CHANGE_MCP_AUDIT

- Contextor Desktop watcher recorded `package_model.py` at revision 1198 (`UPDATED`) and the test file at 1199 (`UPDATED`) and 1200 (`UNCHANGED`), with continuous event history and no resync requirement.
- At canonical revision 1200 both target files have `workspace_sync=verified`, materialized `checked_and_none` syntax diagnostics, zero errors, and no Contextor warnings. Project-wide workspace sync remains `unverified`; that is not relabeled as a verified global source claim.
- Graph, topology and structural-cycle families remain fresh; structural DFS path count remains 16, current active warning count 16, MODEL_PASS warning count 0. Current potential diagnostic remains count 1, fresh, restricted hard-union-soft potential scope, `runtime_execution_proven=false`. `cycle_semantics` remains stale and is reported as stale.
- No graph construction source was changed. No MCP server/runtime code was changed; no restart was requested or performed.

## INVARIANT_STATUS

**PROVED within the checked restricted model branch:** syntactic recognition of a `TYPE_CHECKING` guard no longer selects its `else` suite as an established runtime value. The compiler preserves prior import steps and emits `UNMODELED_STATEMENT`; the ordinary evaluator stops at the reached unmodeled `typing` import, while the conditional passive-import evaluator records that assumption and then returns UNKNOWN at the unresolved guard. The two syntactic forms and the positive controls exercise distinct sides of this branch. This is model-relative proof, not a claim of CPython runtime safety or global environment identity.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_external_import_authority.py`
- `walkthrough.md` is the required report artifact and is excluded from this list under the applicable workflow instructions.

## FULL_DIFFS

Complete actual current-task production and test diffs:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 16fb3f9..6881435 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -870,7 +870,8 @@ def _compile(
                     typing_guard.form,
                 )
             ):
-                selected = stmt.orelse
+                steps.append(_Step("UNMODELED_STATEMENT"))
+                return tuple(steps)
             else:
                 if (
                     not isinstance(condition, ast.Compare)
diff --git a/tests/test_cycle_semantics_external_import_authority.py b/tests/test_cycle_semantics_external_import_authority.py
index d177e9e..a9a3247 100644
--- a/tests/test_cycle_semantics_external_import_authority.py
+++ b/tests/test_cycle_semantics_external_import_authority.py
@@ -4,6 +4,8 @@ import ast
 import subprocess
 import sys
 
+import pytest
+
 from contextor.core.cycle_semantics.namespace_path_model import SearchPortion
 from contextor.core.cycle_semantics.package_graph_consistency import (
     assess_package_graph_consistency,
@@ -121,3 +123,49 @@ def test_conditional_external_assumption_stays_conditional():
     assert result.model_assessment.assumed_external_imports[0].target == (
         "opaque_dependency"
     )
+
+
+@pytest.mark.parametrize(
+    "marker, guard",
+    [
+        ("from typing import TYPE_CHECKING", "TYPE_CHECKING"),
+        ("import typing", "typing.TYPE_CHECKING"),
+    ],
+    ids=("name", "attribute"),
+)
+def test_unproved_typing_guard_stops_ordinary_and_conditional_models(
+    marker, guard,
+):
+    trees = {
+        "pkg.__init__": ast.parse("pass\n"),
+        "pkg.ns.a": ast.parse(
+            f"{marker}\nif {guard}:\n    import pkg.ns.b\nvalue = 1\n"
+        ),
+        "pkg.ns.b": ast.parse("from pkg.ns.a import value\n"),
+    }
+    roots = (SearchPortion(
+        "root", frozenset({
+            "pkg/__init__.py", "pkg/ns/a.py", "pkg/ns/b.py",
+        }),
+    ),)
+
+    ordinary_trees = dict(trees)
+    ordinary_trees["pkg.ns.__init__"] = ast.parse("pass\n")
+    ordinary = evaluate_package_import_order(ordinary_trees, "pkg.ns.a")
+    conditional = evaluate_conditional_namespace_import_order(
+        trees, "pkg.ns.a", roots,
+        target_python_version=(3, 15),
+        assume_passive_external_imports=True,
+    )
+
+    assert ordinary.outcome == "UNKNOWN"
+    assert ordinary.reached_unmodeled_import is not None
+    assert ordinary.reached_unmodeled_import.target == "typing"
+    assert conditional.outcome == "UNKNOWN"
+    assert conditional.model_assessment is not None
+    assert conditional.model_assessment.outcome == "UNKNOWN"
+    assert "typing" in {
+        item.target for item in conditional.model_assessment.assumed_external_imports
+    }
+    assert conditional.outcome != "CONDITIONAL_MODEL_PASS"
+    assert ordinary.outcome != "MODEL_PASS"
```

## FINAL_VERDICT

**PROVED for the exact F1H contract in the checked ordinary and conditional model paths.** Both requested source and test edits are synchronized in current Contextor LIVE state, focused regressions pass, and all changed production/test files have complete diffs above. No claim is made about actual CPython runtime import safety.
