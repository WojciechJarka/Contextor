# P5-M08-I10-I3-R1/R2/R3 — indexed cross-module decorator stacks

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD aa393a25bdfd254491f65716d6aa61dc742af4eb, main aligned with origin/main. Working tree was clean before R3 edits.
- DIRECT_EVIDENCE: CPython 3.15.2.
- DIRECT_EVIDENCE: Contextor preflight LIVE revision 1390, provenance live; package_model.py and the three relevant test modules were workspace_sync=verified. Canonical state fresh; syntax errors 0; cycle-semantics family stale.
- DIRECT_EVIDENCE: I3-R1 implementation is present in HEAD. Commit 103de3e includes package_model.py plus R1's T3 baseline and continuation tests.
- DIRECT_EVIDENCE: I3-R2 test corrections are present in HEAD. Commit aa393a2 contains the baseline F local-import expectation and continuation bootstrap-start filter.
- DIRECT_EVIDENCE: the historical test source matched the reported fixture and old UNKNOWN/no-call assertions. R3 changed only that test and walkthrough.md.

## FILES_CHANGED

- tests/test_cycle_semantics_cross_module_single_decorator.py — R3 historical stacked-decorator contract.
- walkthrough.md — report only, excluded from source/test diff accounting.

Commit status:
- I3-R1 committed in 103de3e: package_model.py, tests/test_cycle_semantics_cross_module_stacked_baseline.py, tests/test_cycle_semantics_cross_module_stack_continuation.py.
- I3-R2 committed in aa393a2: corrections in the two I3 test modules above.
- I3-R3 is currently uncommitted: the single-decorator test file only, plus this walkthrough report.

## STALE_TEST_ROOT_CAUSE

The prior assertion treated an indexed imported restricted stack as UNKNOWN even though I3-R1 supports these named restricted decorators and CPython executes them bottom-to-top. R2's full regression reported MODEL_PASS for this fixture; CPython independently called lower, then upper, and left f callable. The failure was a stale historical expectation, not a production regression.

## EXACT_HISTORICAL_CONTRACT_CHANGE

Renamed test_imported_stacked_decorators_remain_unknown to test_imported_stacked_decorators_execute_bottom_to_top. Preserved its complete package fixture and model invocation. Replaced the UNKNOWN/no-call assertions with MODEL_PASS, exact CALL_FUNCTION records for pkg.app lower then upper, and FROM symbols lower then upper from pkg.decorators. No other test or fixture changed.

## FOREIGN_DECORATOR_EXECUTION

The R1 continuation suite verifies each decorator body runs in its defining module while CALL_FUNCTION remains attributed to pkg.app, the applying module:
- A: bottom body in pkg.decorators; upper body in pkg.app.
- B: bottom body in pkg.app; upper body in pkg.decorators.
- C: lower body in pkg.lower; upper body in pkg.upper.
- D: aliases retain the snapshotted objects from pkg.lower and pkg.upper.

## BOTTOM_UP_APPLICATION

R1 and R3 tests assert the lower decorator is called before the upper decorator. The newly updated historical test verifies:
~~~text
("pkg.app", "lower")
("pkg.app", "upper")
~~~

## DEFINING_MODULE_IMPORT_EFFECTS

The R1 tests verify decorator-local effects are emitted under each defining module. For example, the foreign bottom in case A imports pkg.bottom_effect under pkg.decorators, then the local upper imports pkg.upper_effect under pkg.app. Cases B-D similarly verify their module attribution and import order.

## APPLYING_MODULE_RESULT_BINDING

The committed R1 implementation carries binding_module as the result owner, attributes continuation CALL_FUNCTION events to it, and writes the final decorated name after the last decorator completes. R3 made no production changes.

## ALIAS_IDENTITY

R1's alias case verifies bottom_alias/top_alias calls while preserving FROM exports lower/upper. The isolated snapshot unit test confirms namespace alias rebinding does not replace objects already captured in the snapshot.

## INTERMEDIATE_NONE

R1 natural-completion and bare-return cases pass None to the next decorator. The definition-only model result is MODEL_PASS; the model-only f() call is UNKNOWN.

## NONCALLABLE_UPPER_BOUNDARY

R1 verifies a None upper decorator yields UNKNOWN after the lower effect and emits no upper CALL_FUNCTION.

## UNCHANGED_CLASS_DECORATOR_BOUNDARY

The targeted regression includes class decorator execution, class baseline, and class identity counterexample modules. They passed. R1/R2/R3 make no class decorator or class compiler changes.

## UNCHANGED_EXTERNAL_IMPORT_POLICY

External functools.lru_cache remains UNKNOWN in the continuation test and targeted regression. No external callable execution or import-policy change was introduced.

## CPYTHON_PARITY_MATRIX

All six unchanged T3 subprocess references passed:
| Case | CPython decorator call order | CPython result |
|---|---|---|
| A | bottom@pkg.decorators, upper@pkg.app | import succeeds; f remains the original callable |
| B | bottom@pkg.app, upper@pkg.decorators | import succeeds; f remains the original callable |
| C | lower@pkg.lower, upper@pkg.upper | import succeeds; f remains the original callable |
| D | lower@pkg.lower, upper@pkg.upper via aliases | import succeeds; f remains the original callable |
| E | bottom@pkg.decorators, upper@pkg.app receives None | import succeeds; f is None |
| F | bottom@pkg.app only | TypeError at upper=None; no final f binding |

The exact historical imported-stack fixture also has direct CPython evidence: calls are lower then upper, f is callable, and f() returns None.

## FIRST_GATE_RESULTS

Command:
.\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_cross_module_stacked_baseline.py tests/test_cycle_semantics_cross_module_stack_continuation.py -rs

DIRECT_EVIDENCE: 29 passed in 5.04s.

## FULL_TARGETED_RESULTS

Exact R3 targeted command completed with 318 passed in 29.83s.

git diff --check exited 0. Git emitted only line-ending normalization warnings for modified walkthrough/test files.

No full pytest or SCC02 ran.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: post-change canonical LIVE revision 1391, provenance live.
- Changed test module tests/test_cycle_semantics_cross_module_single_decorator.py: workspace_sync=verified, canonical state fresh, syntax_diagnostics checked_and_none.
- Both I3 modules tests/test_cycle_semantics_cross_module_stacked_baseline.py and tests/test_cycle_semantics_cross_module_stack_continuation.py: workspace_sync=verified at revision 1391, syntax_diagnostics checked_and_none.
- package_model.py: workspace_sync=verified at revision 1391, syntax_diagnostics checked_and_none. R3 made no production change.
- Dependency direction: changed and I3 regression test modules import package_model; continuation also imports execution.calls for the snapshot unit contract. package_model's canonical context reports its existing execution/import dependencies and consumers; no production dependency direction was changed by R3.
- Syntax errors: 0.
- Structural DFS cycle count: 16, semantics DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES.
- cycle_semantics freshness is separate and remains stale. No semantic refresh, FULL, update_file, or backend restart was requested or performed.

## FULL_DIFFS

Complete current uncommitted R3 diff follows. R1 and R2 diffs are committed in 103de3e and aa393a2 respectively.

~~~diff
diff --git a/tests/test_cycle_semantics_cross_module_single_decorator.py b/tests/test_cycle_semantics_cross_module_single_decorator.py
index 69647b4..cae7c9f 100644
--- a/tests/test_cycle_semantics_cross_module_single_decorator.py
+++ b/tests/test_cycle_semantics_cross_module_single_decorator.py
@@ -543,7 +543,7 @@ def test_imported_class_decorator_remains_unknown():
     assert not _events(modeled, "CALL_FUNCTION")


-def test_imported_stacked_decorators_remain_unknown():
+def test_imported_stacked_decorators_execute_bottom_to_top():
     modeled = _model(
         {
             "pkg.__init__": "pass\n",
@@ -563,12 +563,23 @@ def test_imported_stacked_decorators_remain_unknown():
         }
     )

-    assert modeled.outcome == "UNKNOWN"
-    assert not any(
-        event.operation == "CALL_FUNCTION"
-        and event.symbol in {"lower", "upper"}
+    assert modeled.outcome == "MODEL_PASS"
+    calls = tuple(
+        (event.module, event.symbol)
         for event in modeled.events
+        if event.operation == "CALL_FUNCTION"
+    )
+    assert calls == (
+        ("pkg.app", "lower"),
+        ("pkg.app", "upper"),
+    )
+    from_symbols = tuple(
+        event.symbol
+        for event in modeled.events
+        if event.operation == "FROM"
+        and event.target == "pkg.decorators"
     )
+    assert from_symbols == ("lower", "upper")
 
 
 def test_external_lru_cache_remains_unknown():
~~~

## FINAL_VERDICT

FINAL PASS for the P5-M08-I10-I3-R1/R2/R3 targeted scope: the exact historical contract correction is in place, both requested gates pass, git diff --check passes, and the Contextor post-change audit is fresh for the changed source files. No other tests were changed and no production file changed in R3.

