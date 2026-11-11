# P5-M08-I9-I2 + R2 — historical regression STOP

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `6966951bdf4d438ae82fbb7ac8df2ca1b8a268f5`; clean worktree at R2 start. Active `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2. Contextor LIVE revision 1362, `package_model.py` workspace_sync verified, structural DFS cycle count 16, cycle_semantics stale. HEAD includes I9-I2 production, baseline and first staging correction. _ClassFact construction, snapshot, continuation, and both child-name guards are present. The previous 31-pass/2-fail sources matched the current tests before R2 edits.

## FILES_CHANGED

New R2 edits:
- `tests/test_cycle_semantics_class_decorator_execution.py`
- `tests/test_cycle_semantics_class_decorator_staging.py`

Prior I9-I2 changes are committed in HEAD `6966951bdf4d438ae82fbb7ac8df2ca1b8a268f5`: `contextor/core/cycle_semantics/package_model.py`, `tests/test_cycle_semantics_class_decorator_baseline.py`, `tests/test_cycle_semantics_class_decorator_execution.py`, `tests/test_cycle_semantics_class_decorator_staging.py`. `walkthrough.md` is this report.

## CLASS_FACT_CREATION_REUSE

CODE_PATH_PROVED: committed I9-I2 production shares prepared-class validation and _ClassFact construction between ordinary and decorated classes, then stores the class fact by identity before decorator application. No R2 production edits.

## SNAPSHOT_OBJECT_IDENTITY

CODE_PATH_PROVED: named class decorators are snapshotted before PREPARE and class-body steps. The committed execution branch uses captured object pairs in reverse order; no name-based re-resolution. R2 did not change this path.

## CLASS_BODY_EXECUTION_ORDER

The first gate passed C/F class-body import cases. Their isolated CPython and model assertions establish body import before decorator import for these fixtures.

## BOTTOM_UP_DECORATOR_APPLICATION

Corrected E now uses `top_decorator` and `bottom_decorator` while keeping `pkg.top` and `pkg.bottom`. First gate passed the CPython import order and model call/import order. The child-name guards were not weakened.

## INTERMEDIATE_RETURN_VALUES

Committed continuation passes returned object to next decorator, including None. First gate passed its focused cases; no R2 continuation edit.

## FINAL_CLASS_NAME_BINDING

Committed decorated branch defers namespace assignment until decorator completion. Corrected same-name staging test passed with MODEL_PASS, one CALL_FUNCTION(C) and DEFINE_PASSIVE_CLASS(C). No direct runtime namespace inspection claimed.

## EARLY_BINDING_HAZARD

Baseline G passed first gate with EARLY_BINDING_HAZARD. In the full subset, an older D03/D05 class-decorator fixture produced the same hazard for entry `pkg.a`, as CPython's ImportError check expected.

## CORRECTED_E_FIXTURE

Exact source and call expectation changed per R2. First gate passed.

## CORRECTED_HISTORICAL_STAGING_TEST

Only `test_same_name_local_decorator_proof_gate` was renamed and its final model assertion updated with explicit call/class events. First gate passed.

## METACLASS_AND_MRO_PRESERVATION

No R2 production edit; passive-class metaclass and MRO tests in the full subset passed. The full subset nevertheless failed two old D03/D05 outcome expectations.

## CONDITIONAL_DATACLASS_PRESERVATION

No R2 production edit; the focused conditional dataclass regressions in the full subset passed.

## NEGATIVE_CONTRACTS

Unsupported expressions, metaclass/MRO and indexed child collisions in the first gate passed. The old D03/D05 fixture was previously UNKNOWN because class decoration was unsupported; its now modeled outcomes agree with CPython behavior on the tested entries. The existing test file is outside R2 authorization, so its assertions were not changed.

## CPYTHON_PARITY_MATRIX

- Corrected E: isolated runner success, `{"error":null,"imports":["pkg.bottom","pkg.top"]}`; model MODEL_PASS with bottom_decorator then top_decorator.
- D03/D05 class decorator, entry `pkg.a`: CPython subprocess had nonzero exit with ImportError in stderr; model EARLY_BINDING_HAZARD. Complete model events:
```json
[{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg","symbol":null},{"module":"pkg","operation":"READY","target":null,"symbol":null},{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg.a","symbol":null},{"module":"pkg.a","operation":"DEFINE_FUNCTION","target":null,"symbol":"deco"},{"module":"pkg.a","operation":"DEFINE_PASSIVE_CLASS","target":null,"symbol":"C"},{"module":"pkg.a","operation":"CALL_FUNCTION","target":null,"symbol":"deco"},{"module":"pkg.a","operation":"START_IMPORT","target":"pkg.b","symbol":null},{"module":"pkg.b","operation":"EARLY_BINDING_HAZARD","target":"pkg.a","symbol":"C"}]
```
- D03/D05 class decorator, entry `pkg.b`: CPython subprocess exited successfully; model MODEL_PASS. Complete model events:
```json
[{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg","symbol":null},{"module":"pkg","operation":"READY","target":null,"symbol":null},{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg.b","symbol":null},{"module":"pkg.b","operation":"START_IMPORT","target":"pkg.a","symbol":null},{"module":"pkg.a","operation":"DEFINE_FUNCTION","target":null,"symbol":"deco"},{"module":"pkg.a","operation":"DEFINE_PASSIVE_CLASS","target":null,"symbol":"C"},{"module":"pkg.a","operation":"CALL_FUNCTION","target":null,"symbol":"deco"},{"module":"pkg.a","operation":"FUNCTION_LOCAL_IMPORT","target":"pkg.b","symbol":"pkg"},{"module":"pkg.a","operation":"READY","target":null,"symbol":null},{"module":"pkg","operation":"BIND_CHILD","target":"pkg.a","symbol":"a"},{"module":"pkg.b","operation":"FROM","target":"pkg.a","symbol":"C"},{"module":"pkg.b","operation":"READY","target":null,"symbol":null},{"module":"pkg","operation":"BIND_CHILD","target":"pkg.b","symbol":"b"}]
```

## TARGETED_TEST_RESULTS

First gate: `33 passed in 5.64s`.

Full specified I9-I2 subset: `2 failed, 390 passed, 2 warnings in 52.95s`. Both failures are parameterizations of `tests/test_cycle_semantics_decorator_definition_effects.py::test_d03_d05_decorator_import_entry_dependency` at line 179, IDs `[pkg.a-False-class_decorator]` and `[pkg.b-True-class_decorator]`. Original expected outcomes `("UNKNOWN","UNKNOWN")`; actual `("EARLY_BINDING_HAZARD","MODEL_PASS")`. Pytest traceback is an AssertionError at `assert modeled.outcome == expected` for each. The CPython success/failure assertions passed before model comparison. Relevant source anchors: committed decorated class branch `package_model.py:2512-2626`; return continuation `:2650-2700`; historical fixture `test_cycle_semantics_decorator_definition_effects.py:118-179`.

`git diff --check`: exit 0; LF/CRLF notices only.

## MCP_POST_CHANGE_AUDIT

NOT RUN because the R2 specification authorizes it only after all tests pass. No FULL, update_file, restart or semantic refresh. Post-edit LIVE freshness is UNKNOWN.

## FULL_DIFFS

Complete current uncommitted source/test diff:

```diff
warning: in the working copy of 'tests/test_cycle_semantics_class_decorator_execution.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_cycle_semantics_class_decorator_staging.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/test_cycle_semantics_class_decorator_execution.py b/tests/test_cycle_semantics_class_decorator_execution.py
index 779d29c..fb34e66 100644
--- a/tests/test_cycle_semantics_class_decorator_execution.py
+++ b/tests/test_cycle_semantics_class_decorator_execution.py
@@ -36,11 +36,19 @@ CASES = [
         id="D-same-name",
     ),
     pytest.param(
-        "def top(cls):\n    import pkg.top\n    return cls\n"
-        "def bottom(cls):\n    import pkg.bottom\n    return cls\n"
-        "@top\n@bottom\nclass C:\n    pass\n",
+        "def top_decorator(cls):\n"
+        "    import pkg.top\n"
+        "    return cls\n"
+        "def bottom_decorator(cls):\n"
+        "    import pkg.bottom\n"
+        "    return cls\n"
+        "@top_decorator\n"
+        "@bottom_decorator\n"
+        "class C:\n"
+        "    pass\n",
         None, ("pkg.bottom", "pkg.top"), "MODEL_PASS",
-        ("bottom", "top"), ("pkg.bottom", "pkg.top"),
+        ("bottom_decorator", "top_decorator"),
+        ("pkg.bottom", "pkg.top"),
         id="E-two-pass-through",
     ),
     pytest.param(
diff --git a/tests/test_cycle_semantics_class_decorator_staging.py b/tests/test_cycle_semantics_class_decorator_staging.py
index be9578e..9bede4b 100644
--- a/tests/test_cycle_semantics_class_decorator_staging.py
+++ b/tests/test_cycle_semantics_class_decorator_staging.py
@@ -197,7 +197,7 @@ def test_forward_decorator_reference_rejects_compile():
     ) is None
 
 
-def test_same_name_local_decorator_proof_gate():
+def test_same_name_local_decorator_proof_and_execution():
     source = "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n"
     steps = _steps(source)
     assert steps is not None
@@ -206,9 +206,20 @@ def test_same_name_local_decorator_proof_gate():
         if step.op == "SNAPSHOT_CLASS_DECORATORS"
     )
     assert snapshot.decorator_names == ("C",)
-    assert evaluate_package_import_order(
+    result = evaluate_package_import_order(
         {"pkg.__init__": ast.parse(source)}, "pkg",
-    ).outcome == "UNKNOWN"
+    )
+    assert result.outcome == "MODEL_PASS"
+    assert tuple(
+        event.symbol
+        for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    ) == ("C",)
+    assert any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "C"
+        for event in result.events
+    )
 
 
 def test_exact_p10_eager_and_lazy_fixture():
```

Prior I9-I2 production/test changes are in HEAD `6966951bdf4d438ae82fbb7ac8df2ca1b8a268f5`; no uncommitted diff exists for them.

## FINAL_VERDICT

REGRESSION_FAILURE / BLOCKED_SEMANTIC_INTEGRITY. FINAL PASS denied pending corrected historical D03/D05 test contract and authorization. No further tests or edits after failure.
