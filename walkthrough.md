# P5-M08-T2 — Minimal decorator import-effect baseline

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. `evaluate_package_import_order` resolves to `contextor/core/cycle_semantics/package_model.py:1157-2284`; canonical LIVE revision 1304, source fresh, `workspace_sync=verified`, cycle semantics stale. HEAD `6612d5ebef61148c5899dd62055b60efd004a426`; initial `git status --short` clean. Active backend executable: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M08-T1 `tests/test_cycle_semantics_definition_effect_order_cpython.py` and M07-I2B `tests/test_cycle_semantics_function_identity_counterexamples.py` exist. The new target file did not exist. No production source change was present or made.

## FILES_CHANGED

- Added `tests/test_cycle_semantics_decorator_import_effect_baseline.py` exactly as specified. Full new-file diff below.
- Overwrote `walkthrough.md` for this task. No production or existing test file changed.

## CPYTHON_IMPORT_ORDER_MATRIX

DIRECT_EVIDENCE: The isolated CPython runner records calls to `builtins.__import__` whose names begin with `pkg.`; all five exact expected lists passed (`tests/test_cycle_semantics_decorator_import_effect_baseline.py:15-182`). These are observed import attempts in the tested sources, not a general model proof.

| Case | CPython import order | Error |
|---|---|---|
| decorated-function-body-deferred | none | none |
| decorator-import-during-definition | `pkg.child` | none |
| stacked-decorator-import-order | `pkg.lower`, `pkg.upper` | none |
| class-body-before-decorator | `pkg.body`, `pkg.decorate` | none |
| default-before-decorator-application | `pkg.default`, `pkg.decorate` | none |

## CURRENT_MODEL_OUTCOME_MATRIX

DIRECT_EVIDENCE: Each corresponding AST input returned `UNKNOWN` with an empty `events` tuple. The new test asserts the outcome (`tests/test_cycle_semantics_decorator_import_effect_baseline.py:170-182`); the event tuples were read separately from the evaluator on the exact CASES.

| Case | Current model | Events |
|---|---|---|
| decorated-function-body-deferred | UNKNOWN | none |
| decorator-import-during-definition | UNKNOWN | none |
| stacked-decorator-import-order | UNKNOWN | none |
| class-body-before-decorator | UNKNOWN | none |
| default-before-decorator-application | UNKNOWN | none |

UNKNOWN does not establish parity or imply absence of CPython effects.

## DEFERRED_VS_DEFINITION_EFFECTS

- DIRECT_EVIDENCE: The first CPython fixture defines a decorated function whose body imports `pkg.child` but does not call the function; the import trace is empty. The second fixture puts that import in the decorator and records `pkg.child` during definition (`tests/test_cycle_semantics_decorator_import_effect_baseline.py:16-37,89-116`).
- DIRECT_EVIDENCE: The stacked, class-body, and default cases record the specific ordering listed above. Current model UNKNOWN in each case leaves definition-time effects unresolved; no MODEL_PASS is claimed.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Required focused command using the active backend venv across the new file, M08-T1 CPython file, and existing decorator regressions returned `27 passed in 8.75s`.
- DIRECT_EVIDENCE: `git diff --check` exited 0. No full pytest, FULL, `update_file`, restart, Git add/commit/push, or index/history mutation.

## MCP_POST_TASK_AUDIT

- DIRECT_EVIDENCE: Post-task Contextor query still reported canonical LIVE revision 1304, `package_model.py` source fresh with `workspace_sync=verified`, cycle semantics stale. Git status before report rewrite showed only the new untracked test, confirming no production file changed. No runtime adoption or semantic refresh is claimed.

## FULL_DIFFS

Complete actual new-file diff (`/dev/null` → `tests/test_cycle_semantics_decorator_import_effect_baseline.py`):

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
@@ -0,0 +1,182 @@
+import ast
+import builtins
+import json
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+CASES = [
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    return fn\n"
+            "@deco\n"
+            "def f():\n"
+            "    import pkg.child\n"
+        ),
+        (),
+        id="decorated-function-body-deferred",
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
+        ("pkg.child",),
+        id="decorator-import-during-definition",
+    ),
+    pytest.param(
+        (
+            "def upper(fn):\n"
+            "    import pkg.upper\n"
+            "    return fn\n"
+            "def lower(fn):\n"
+            "    import pkg.lower\n"
+            "    return fn\n"
+            "@upper\n"
+            "@lower\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        ("pkg.lower", "pkg.upper"),
+        id="stacked-decorator-import-order",
+    ),
+    pytest.param(
+        (
+            "def deco(cls):\n"
+            "    import pkg.decorate\n"
+            "    return cls\n"
+            "@deco\n"
+            "class C:\n"
+            "    import pkg.body\n"
+        ),
+        ("pkg.body", "pkg.decorate"),
+        id="class-body-before-decorator",
+    ),
+    pytest.param(
+        (
+            "def default():\n"
+            "    import pkg.default\n"
+            "    return 7\n"
+            "def deco(fn):\n"
+            "    import pkg.decorate\n"
+            "    return fn\n"
+            "@deco\n"
+            "def f(x=default()):\n"
+            "    pass\n"
+        ),
+        ("pkg.default", "pkg.decorate"),
+        id="default-before-decorator-application",
+    ),
+]
+
+
+RUNNER = """
+import builtins
+import importlib
+import json
+import sys
+
+sys.path.insert(0, sys.argv[1])
+
+observed = []
+original_import = builtins.__import__
+
+def traced_import(name, *args, **kwargs):
+    if name.startswith("pkg."):
+        observed.append(name)
+    return original_import(name, *args, **kwargs)
+
+builtins.__import__ = traced_import
+
+error = None
+
+try:
+    importlib.import_module("pkg")
+except Exception as exc:
+    error = type(exc).__name__
+
+print(json.dumps({
+    "error": error,
+    "imports": observed,
+}))
+"""
+
+
+@pytest.mark.parametrize("source,expected_imports", CASES)
+def test_minimal_decorator_import_effects(
+    tmp_path: Path,
+    source: str,
+    expected_imports: tuple[str, ...],
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+
+    (package / "__init__.py").write_text(
+        source,
+        encoding="utf-8",
+    )
+
+    child_names = {
+        "child",
+        "upper",
+        "lower",
+        "body",
+        "decorate",
+        "default",
+    }
+
+    for name in child_names:
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
+    assert observed["error"] is None
+    assert observed["imports"] == list(expected_imports)
+
+    sources = {
+        "pkg.__init__": ast.parse(source),
+    }
+
+    for name in child_names:
+        sources["pkg." + name] = ast.parse("pass\n")
+
+    result = evaluate_package_import_order(
+        sources,
+        "pkg",
+    )
+
+    # Current conservative model boundary.
+    # Not the target behavior after implementation.
+    assert result.outcome == "UNKNOWN"
```

## FINAL_VERDICT

- CONTRACT_PROVED: The exact five-case CPython import-order and current-model UNKNOWN baseline was added and passed. CPython ordering and model uncertainty are explicitly separate. Stop after tests and audit.
