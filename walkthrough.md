# P5-M08-I7-T1 — decorator import and early-binding gate

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP first reported canonical LIVE revision 1327, `package_model.py` fresh with `workspace_sync=verified`. Initial HEAD `999f74cc0e1b6db5f3fc75fb991b2be361e26bfb`; initial `git status --short` clean. Active backend `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2. The new target test did not exist.
- DIRECT_EVIDENCE: M08-I6 branches remain at `package_model.py:142-180,980-1105,2021-2075,2357-2410`. Existing tests were inspected at `tests/test_cycle_semantics_named_function_decorators.py:1-114`, `tests/test_cycle_semantics_decorator_import_effect_baseline.py:1-186`, and `tests/test_cycle_semantics_decorator_definition_effects.py:61-286`. Production and prior tests were unchanged in this task.

## FILES_CHANGED

- `tests/test_cycle_semantics_decorator_import_return_gate.py` (new)
- `walkthrough.md` (this report)

## DECORATOR_IMPORT_MATRIX

| Case | CPython 3.15.2 | Model assertion | Import evidence |
|---|---|---|---|
| import then bare return | success | MODEL_PASS | `pkg.child` in both |
| import then implicit None | success | MODEL_PASS | `pkg.child` in both |
| import then parameter return | success | UNKNOWN | CPython imports `pkg.child`; no model CALL_FUNCTION |
| import before final binding | ImportError | not MODEL_PASS | CPython imports `pkg.child` first |

DIRECT_EVIDENCE: `tests/test_cycle_semantics_decorator_import_return_gate.py:15-155` executes each case in isolated CPython through the existing runner and separately evaluates the same AST through the model. The test asserts exact CPython error/import JSON, model outcome boundary and positive child START_IMPORT evidence. UNKNOWN is not treated as parity.

## BARE_VS_VALUED_RETURN_BOUNDARY

- CODE_PATH_PROVED: `return` is compiled to `RETURN_FUNCTION` and can follow import steps (`package_model.py:1008-1016`). A return of the bound parameter after an import is made opaque by the mixed import/valued-return guard (`package_model.py:1072-1083`); a decorated opaque body is rejected during compilation (`package_model.py:1086-1090`). The new tests distinguish these paths without broadening production behavior.

## EARLY_BINDING_CASE

- DIRECT_EVIDENCE: In the fourth CPython case, `pkg.child` executes `from pkg import f` while `@deco` is still executing. CPython records `pkg.child` and then raises ImportError (`tests/test_cycle_semantics_decorator_import_return_gate.py:56-69,111-124`). The model test demands only that this case cannot be `MODEL_PASS` (`:136-139`); it does not assert an unproved exact failure classification. The decorated name is bound only after the function frame returns in current source (`package_model.py:2021-2075,2357-2380`).

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: The requested five focused test files completed: **45 passed**, exit 0, 13.47 s. `git diff --check` exited 0. No production or existing test file changed; no full suite or SCC02 was run.

## MCP_POST_TASK_AUDIT

- DIRECT_EVIDENCE: Contextor MCP indexed the new test at canonical LIVE revision **1328**, source fresh with `workspace_sync=verified`; syntax errors 0, structural DFS back-edge cycle count 16. `cycle_semantics=stale`; source freshness does not prove runtime adoption or a fresh semantic classification.

## FULL_DIFFS

### tests/test_cycle_semantics_decorator_import_return_gate.py

```diff
diff --git a/tests/test_cycle_semantics_decorator_import_return_gate.py b/tests/test_cycle_semantics_decorator_import_return_gate.py
new file mode 100644
index 0000000..b7611f8
--- /dev/null
+++ b/tests/test_cycle_semantics_decorator_import_return_gate.py
@@ -0,0 +1,155 @@
+import ast
+import json
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+from test_cycle_semantics_decorator_import_effect_baseline import (
+    RUNNER,
+)
+
+
+CASES = [
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    import pkg.child\n"
+            "    return\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "pass\n",
+        None,
+        ("pkg.child",),
+        "MODEL_PASS",
+        id="import-then-bare-return",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    import pkg.child\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "pass\n",
+        None,
+        ("pkg.child",),
+        "MODEL_PASS",
+        id="import-then-implicit-none",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    import pkg.child\n"
+            "    return fn\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "pass\n",
+        None,
+        ("pkg.child",),
+        "UNKNOWN",
+        id="import-then-parameter-return",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    import pkg.child\n"
+            "    return\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "from pkg import f\n",
+        "ImportError",
+        ("pkg.child",),
+        None,
+        id="decorator-import-before-final-binding",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,child_source,error,imports,model_outcome",
+    CASES,
+)
+def test_decorator_import_return_gate(
+    tmp_path,
+    source,
+    child_source,
+    error,
+    imports,
+    model_outcome,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+
+    (package / "__init__.py").write_text(
+        source,
+        encoding="utf-8",
+    )
+    (package / "child.py").write_text(
+        child_source,
+        encoding="utf-8",
+    )
+
+    process = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            RUNNER,
+            str(tmp_path),
+        ],
+        capture_output=True,
+        text=True,
+        timeout=20,
+        check=False,
+    )
+
+    assert process.returncode == 0, process.stderr
+
+    observed = json.loads(process.stdout)
+
+    assert observed == {
+        "error": error,
+        "imports": list(imports),
+    }
+
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
+            "pkg.child": ast.parse(child_source),
+        },
+        "pkg",
+    )
+
+    if model_outcome is None:
+        assert result.outcome != "MODEL_PASS"
+    else:
+        assert result.outcome == model_outcome
+
+    child_starts = [
+        event.target
+        for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+    ]
+
+    if model_outcome == "MODEL_PASS":
+        assert child_starts == ["pkg.child"]
+
+    if model_outcome == "UNKNOWN":
+        assert not any(
+            event.operation == "CALL_FUNCTION"
+            for event in result.events
+        )
```

## FINAL_VERDICT

CONTRACT_PROVED for the four CPython observations and the asserted model gate. The test-only stage passed. The valued parameter-return path remains UNKNOWN; the early-binding case is not MODEL_PASS. STOP after this stage.
