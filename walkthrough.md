# P5-M08-I9-T1 — class decorator definition-time baseline

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `6d978b31534f9ab773d44d8f455642d8f7b54fdb`; clean worktree at start; active `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2. Contextor package_model revision 1352, workspace_sync verified, structural DFS cycles 16, cycle_semantics stale. I8-I2 snapshot/object-call/stacked continuation and both child-name guards are present. New target test file did not exist.

CODE_PATH_PROVED: `package_model.py:245-307` rejects ordinary decorated ClassDef in passive class validation. `:809-984` otherwise prepares passive class, compiles class-body imports before `DEFINE_PASSIVE_CLASS`; `:2429-2497` binds the passive class. Child-name guards are at `:1578-1598` and `:1680-1700`. Existing decorator and stacked tests were inspected. Contextor identifies `evaluate_package_import_order` as canonical owner, with `evaluate_conditional_namespace_import_order` as a direct intra-module caller; static call context is not a complete dynamic call graph.

## FILES_CHANGED

- `tests/test_cycle_semantics_class_decorator_baseline.py`

`walkthrough.md` is the task report, excluded from source/test/docs diff count. No production or existing test file changed.

## CPYTHON_CLASS_DECORATOR_MATRIX

| Case | Isolated CPython JSON | Model | Complete model events |
|---|---|---|---|
| A pass-through | `{"error":null,"imports":[]}` | UNKNOWN | `[]` |
| B decorator import | `{"error":null,"imports":["pkg.decorate"]}` | UNKNOWN | `[]` |
| C body first | `{"error":null,"imports":["pkg.body","pkg.decorate"]}` | UNKNOWN | `[]` |
| D stacked | `{"error":null,"imports":["pkg.body","pkg.bottom","pkg.top"]}` | UNKNOWN | `[]` |
| E same name | `{"error":null,"imports":[]}` | UNKNOWN | `[]` |
| F replacement None | `{"error":null,"imports":["pkg.body"]}` | UNKNOWN | `[]` |
| G reentrant import | `{"error":"ImportError","imports":["pkg.child"]}` | UNKNOWN | `[]` |

The exact JSON expectations passed in isolated subprocess tests. UNKNOWN is no claim of model parity.

## CLASS_BODY_EXECUTION_ORDER

DIRECT_EVIDENCE: C and D show class-body import before decorator imports. Class-body evaluation therefore precedes decorator application in these fixtures.

## DECORATOR_APPLICATION_ORDER

DIRECT_EVIDENCE: D import trace `pkg.body`, `pkg.bottom`, `pkg.top` establishes bottom-to-top application after body execution for that stack.

## CLASS_OBJECT_AND_FINAL_BINDING

DIRECT_EVIDENCE: F completes with a None replacement; G raises ImportError when child import requests `C` during decoration. Together they support class object creation and decorator application before final binding of `C`. This is fixture evidence, not a complete general CPython proof. No model staging claim is made.

## SAME_NAME_DECORATOR_CONTRACT

DIRECT_EVIDENCE: E succeeds when `@C` refers to the prior function binding while the new class has the same name.

## REENTRANT_EARLY_BINDING_CONTRACT

DIRECT_EVIDENCE: G observes `pkg.child` first and raises ImportError when `from pkg import C` executes before the decorated class is finally bound.

## CURRENT_MODEL_BOUNDARIES

CODE_PATH_PROVED: ordinary class decorators fail passive-class validation and `evaluate_package_import_order` returns UNKNOWN before events. All seven fixtures returned UNKNOWN with complete event sequences `[]`. The test does not assert model import order under UNKNOWN. No new MODEL_PASS admission.

## TARGETED_TEST_RESULTS

Specified focused command: `55 passed in 13.80s`. `git diff --check`: exit 0. No full pytest or SCC02.

## MCP_POST_TASK_AUDIT

Contextor canonical revision advanced from 1352 to 1353. New test module `workspace_sync=verified`; syntax errors 0, structural DFS cycle count 16. Source freshness does not attest loaded backend code. The event endpoint returned `confirmation_required` for the broad payload, so no exact watcher event is claimed. No FULL, update_file, restart, or semantic refresh.

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_class_decorator_baseline.py b/tests/test_cycle_semantics_class_decorator_baseline.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_class_decorator_baseline.py
@@ -0,0 +1,92 @@
+"""CPython class-decorator timing versus the current conservative model."""
+
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
+from test_cycle_semantics_decorator_import_effect_baseline import RUNNER
+
+
+CASES = [
+    pytest.param(
+        "def identity(cls):\n    return cls\n@identity\nclass C:\n    pass\n",
+        None, (), id="A-pass-through",
+    ),
+    pytest.param(
+        "def decorate(cls):\n    import pkg.decorate\n    return cls\n"
+        "@decorate\nclass C:\n    pass\n",
+        None, ("pkg.decorate",), id="B-decorator-import",
+    ),
+    pytest.param(
+        "def decorate(cls):\n    import pkg.decorate\n    return cls\n"
+        "@decorate\nclass C:\n    import pkg.body\n",
+        None, ("pkg.body", "pkg.decorate"), id="C-body-before-decorator",
+    ),
+    pytest.param(
+        "def top_decorator(cls):\n    import pkg.top\n    return cls\n"
+        "def bottom_decorator(cls):\n    import pkg.bottom\n    return cls\n"
+        "@top_decorator\n@bottom_decorator\nclass C:\n"
+        "    import pkg.body\n",
+        None, ("pkg.body", "pkg.bottom", "pkg.top"),
+        id="D-stacked-class-decorators",
+    ),
+    pytest.param(
+        "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n",
+        None, (), id="E-same-name-decorator",
+    ),
+    pytest.param(
+        "def decorate(cls):\n    return\n@decorate\nclass C:\n"
+        "    import pkg.body\n",
+        None, ("pkg.body",), id="F-decorator-returns-none",
+    ),
+    pytest.param(
+        "def decorate(cls):\n    import pkg.child\n    return cls\n"
+        "@decorate\nclass C:\n    pass\n",
+        "ImportError", ("pkg.child",), id="G-early-class-binding-hazard",
+    ),
+]
+
+
+@pytest.mark.parametrize("source,expected_error,expected_imports", CASES)
+def test_class_decorator_definition_time_baseline(
+    tmp_path, source, expected_error, expected_imports,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+
+    sources = {"pkg.__init__": ast.parse(source)}
+    for child in ("body", "decorate", "top", "bottom", "child"):
+        child_source = (
+            "from pkg import C\n"
+            if child == "child" and expected_error == "ImportError"
+            else "pass\n"
+        )
+        (package / f"{child}.py").write_text(child_source, encoding="utf-8")
+        sources[f"pkg.{child}"] = ast.parse(child_source)
+
+    process = subprocess.run(
+        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
+        capture_output=True,
+        text=True,
+        timeout=20,
+        check=False,
+    )
+    assert process.returncode == 0, process.stderr
+    observed = json.loads(process.stdout)
+    assert observed == {
+        "error": expected_error,
+        "imports": list(expected_imports),
+    }
+
+    result = evaluate_package_import_order(sources, "pkg")
+    assert result.outcome == "UNKNOWN", (
+        result.outcome,
+        [event.__dict__ for event in result.events],
+    )
```

## FINAL_VERDICT

PASS for I9-T1 baseline scope: seven isolated CPython cases and current UNKNOWN boundaries verified; targeted tests and source freshness passed. No class-decorator execution admitted.
