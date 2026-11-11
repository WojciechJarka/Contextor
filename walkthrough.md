# P5-M08-I8-T1 — stacked function decorator order and identity

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. Initial canonical LIVE revision 1334, `package_model.py` source fresh with `workspace_sync=verified`; cycle semantics stale. Initial HEAD `eb2786f45ca66d023ee363d7b659a77ce6030c4b`. Active backend `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2.
- DIRECT_EVIDENCE: Initial worktree already contained `M tests/test_cycle_semantics_decorator_definition_effects.py` and `M walkthrough.md` from R1. Both were preserved; the former was not edited in this task. The new target test did not exist. I7's `parameter_returns` guard and single-name decorator path remain at `package_model.py:1072-1105,2028-2083`; multi-decorator rejection remains at `_safe_passive_function_definition`, `package_model.py:160-180`. R1's entry-specific assertions remain at `tests/test_cycle_semantics_decorator_definition_effects.py:98-184`.

## FILES_CHANGED

- `tests/test_cycle_semantics_stacked_decorator_identity.py` (new)
- `walkthrough.md` (this report)

## CPYTHON_STACKED_DECORATOR_MATRIX

| Case | CPython 3.15.2 error | Ordered `pkg.*` imports | Current model |
|---|---|---|---|
| bottom-up application | none | bottom, top | UNKNOWN |
| same decorator twice | none | child, child | UNKNOWN |
| upper binding replaced after evaluation | none | bottom, top | UNKNOWN |
| None intermediate value | none | top | UNKNOWN |
| upper wrong arity after lower effect | TypeError | bottom | UNKNOWN |
| decorated body executed last | none | bottom, top, child | UNKNOWN |

- DIRECT_EVIDENCE: `tests/test_cycle_semantics_stacked_decorator_identity.py:13-186` runs each source in isolated CPython with the existing runner and then evaluates the same AST through `evaluate_package_import_order`. Exact error type and ordered import trace are asserted; the model's UNKNOWN and absence of a successful decorator CALL_FUNCTION are asserted separately. UNKNOWN is not presented as CPython parity.

## EVALUATION_SNAPSHOT_CONTRACT

- DIRECT_EVIDENCE: The `upper-binding-replaced-after-evaluation` CPython case changes global `upper` during the lower decorator's call yet still imports bottom then top (`tests/test_cycle_semantics_stacked_decorator_identity.py:45-66`). This demonstrates the previously evaluated upper decorator object is used. The model remains UNKNOWN.

## BOTTOM_UP_APPLICATION_CONTRACT

- DIRECT_EVIDENCE: The bottom-up case imports `pkg.bottom` before `pkg.top`; the repeated-decorator case imports `pkg.child` twice; the decorated-body case imports bottom, top, then child (`tests/test_cycle_semantics_stacked_decorator_identity.py:15-44,96-120`). These are CPython observations from the passing focused test, not modeled effects.

## NEGATIVE_ARITY_CONTRACT

- DIRECT_EVIDENCE: In the `upper-wrong-arity-after-lower-effect` case, CPython records `pkg.bottom` and then raises `TypeError` before `pkg.top` (`tests/test_cycle_semantics_stacked_decorator_identity.py:78-95`). The model remains UNKNOWN without a decorator CALL_FUNCTION event.

## CURRENT_UNKNOWN_BOUNDARIES

- CODE_PATH_PROVED: `_safe_passive_function_definition` admits at most one ordinary named decorator when the restricted flag is set (`package_model.py:169-177`). All six stacked cases therefore remain outside the current model. The new test asserts UNKNOWN and no `CALL_FUNCTION` for `upper`, `lower` or `deco` (`tests/test_cycle_semantics_stacked_decorator_identity.py:178-186`). No production source or existing tests were changed.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: The requested five focused test files completed **47 passed**, exit 0, 16.09 s. `git diff --check` exited 0. No full pytest or SCC02 was run.

## MCP_POST_TASK_AUDIT

- DIRECT_EVIDENCE: New test indexed at canonical LIVE revision **1335**, source fresh and `workspace_sync=verified`; syntax errors 0; structural DFS back-edge cycle count 16. Its only hard dependency target is `package_model`. `cycle_semantics=stale`, so no fresh semantic or runtime-safety claim is made.

## FULL_DIFFS

The full new-file diff follows. The pre-existing R1 test modification is preserved and is not an I8-T1 change.

```diff
diff --git a/tests/test_cycle_semantics_stacked_decorator_identity.py b/tests/test_cycle_semantics_stacked_decorator_identity.py
new file mode 100644
index 0000000..85c71d3
--- /dev/null
+++ b/tests/test_cycle_semantics_stacked_decorator_identity.py
@@ -0,0 +1,186 @@
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
+from test_cycle_semantics_decorator_import_effect_baseline import RUNNER
+
+
+CASES = [
+    pytest.param(
+        (
+            "def upper(fn):\n"
+            "    import pkg.top\n"
+            "    return fn\n"
+            "def lower(fn):\n"
+            "    import pkg.bottom\n"
+            "    return fn\n"
+            "@upper\n"
+            "@lower\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        None,
+        ("pkg.bottom", "pkg.top"),
+        id="bottom-up-application",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    import pkg.child\n"
+            "    return fn\n"
+            "@deco\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        None,
+        ("pkg.child", "pkg.child"),
+        id="same-decorator-called-twice",
+    ),
+    pytest.param(
+        (
+            "def upper(fn):\n"
+            "    import pkg.top\n"
+            "    return fn\n"
+            "def lower(fn):\n"
+            "    global upper\n"
+            "    upper = None\n"
+            "    import pkg.bottom\n"
+            "    return fn\n"
+            "@upper\n"
+            "@lower\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        None,
+        ("pkg.bottom", "pkg.top"),
+        id="upper-binding-replaced-after-evaluation",
+    ),
+    pytest.param(
+        (
+            "def upper(fn):\n"
+            "    import pkg.top\n"
+            "    return fn\n"
+            "def lower(fn):\n"
+            "    return\n"
+            "@upper\n"
+            "@lower\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        None,
+        ("pkg.top",),
+        id="none-intermediate-value",
+    ),
+    pytest.param(
+        (
+            "def upper():\n"
+            "    import pkg.top\n"
+            "    return\n"
+            "def lower(fn):\n"
+            "    import pkg.bottom\n"
+            "    return fn\n"
+            "@upper\n"
+            "@lower\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "TypeError",
+        ("pkg.bottom",),
+        id="upper-wrong-arity-after-lower-effect",
+    ),
+    pytest.param(
+        (
+            "def upper(fn):\n"
+            "    import pkg.top\n"
+            "    return fn\n"
+            "def lower(fn):\n"
+            "    import pkg.bottom\n"
+            "    return fn\n"
+            "@upper\n"
+            "@lower\n"
+            "def f():\n"
+            "    import pkg.child\n"
+            "f()\n"
+        ),
+        None,
+        ("pkg.bottom", "pkg.top", "pkg.child"),
+        id="decorated-body-executed-last",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,expected_error,expected_imports",
+    CASES,
+)
+def test_stacked_decorator_cpython_and_current_boundary(
+    tmp_path,
+    source,
+    expected_error,
+    expected_imports,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+
+    (package / "__init__.py").write_text(
+        source,
+        encoding="utf-8",
+    )
+
+    for name in ("top", "bottom", "child"):
+        (package / (name + ".py")).write_text(
+            "pass\n",
+            encoding="utf-8",
+        )
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
+        "error": expected_error,
+        "imports": list(expected_imports),
+    }
+
+    sources = {
+        "pkg.__init__": ast.parse(source),
+    }
+
+    for name in ("top", "bottom", "child"):
+        sources["pkg." + name] = ast.parse("pass\n")
+
+    result = evaluate_package_import_order(
+        sources,
+        "pkg",
+    )
+
+    assert result.outcome == "UNKNOWN"
+
+    assert not any(
+        event.operation == "CALL_FUNCTION"
+        and event.symbol in {"upper", "lower", "deco"}
+        for event in result.events
+    )
```

## FINAL_VERDICT

CONTRACT_PROVED for six bounded CPython observations and the current conservative UNKNOWN boundary. The focused regression subset passed; no production or existing test edits were made. STOP after this stage.
