# P5-M08-T1 — Definition-time effect order

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. `_compile` resolves to `contextor/core/cycle_semantics/package_model.py:476-1056`, canonical LIVE revision 1303, source fresh, `workspace_sync=verified`, cycle semantics stale. HEAD `c646ea353a88efc926e241354f9c2d13b0749be1`; initial `git status --short` clean.
- DIRECT_EVIDENCE: Active backend venv `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` reports CPython 3.15.2. M07-I2A `_RestrictedFunction` and factory are present at `execution/calls.py:9-22` and `package_model.py:1886`; M07-I2B counterexample test exists. The target test did not exist before this task.

## FILES_CHANGED

- Added `tests/test_cycle_semantics_definition_effect_order_cpython.py` exactly as specified; complete new-file diff below.
- Overwrote `walkthrough.md` for this task. No production or existing test file changed; final pre-report status showed only the new untracked test.

## CPYTHON_DEFINITION_ORDER_MATRIX

DIRECT_EVIDENCE: Each row is the complete JSON expected and asserted by the isolated CPython runner in `tests/test_cycle_semantics_definition_effect_order_cpython.py:9-240`; all eight cases passed.

| Case | Observed `trace` | `error` | `child_imported` |
|---|---|---|---:|
| function-decorator-application | `apply`, `after` | null | false |
| stacked-application-bottom-up | `apply-lower`, `apply-upper` | null | false |
| factory-evaluation-and-application | `evaluate-upper`, `evaluate-lower`, `apply-lower`, `apply-upper` | null | false |
| decorator-expression-before-default | `decorator-expression`, `default-expression`, `application` | null | false |
| class-body-before-decoration | `class-body`, `class-decoration` | null | false |
| decorator-replaces-function-binding | `replacement-called` | null | false |
| decorator-imports-during-definition | `decorator-import` | null | true |
| decorator-exception-stops-module | `before-error` | `RuntimeError` | false |

These tests establish CPython behavior only. They do not assert Contextor model parity or extend MODEL_PASS eligibility.

## DECORATOR_IMPORT_EFFECTS

- DIRECT_EVIDENCE: The `decorator-imports-during-definition` fixture imports `pkg.child` in `deco`, applies `@deco` to `f`, and asserts `child_imported=true` with `trace=["decorator-import"]` (`tests/test_cycle_semantics_definition_effect_order_cpython.py:136-150,191-240`). The definition-time import is observed through `sys.modules` in the isolated subprocess runner.

## NEGATIVE_EXCEPTION_CONTRACT

- DIRECT_EVIDENCE: The exception fixture appends `before-error`, raises `RuntimeError` during decorator application, and places an `unreachable` append afterwards. The isolated runner reports `trace=["before-error"]`, `error="RuntimeError"`, `child_imported=false` (`tests/test_cycle_semantics_definition_effect_order_cpython.py:151-166,191-240`). This proves the subsequent module statement was not reached in this CPython scenario.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Required command with the active venv interpreter over `tests/test_cycle_semantics_definition_effect_order_cpython.py` and `tests/test_cycle_semantics_decorator_definition_effects.py` returned `22 passed in 5.20s`.
- DIRECT_EVIDENCE: `git diff --check` exited 0. No full pytest, FULL, `update_file`, restart, Git add/commit/push, or index/history mutation.

## MCP_AUDIT

- DIRECT_EVIDENCE: Post-task Contextor query remained at canonical LIVE revision 1303, `package_model.py` source fresh and `workspace_sync=verified`, cycle semantics stale. Git status showed only the new test file before report rewrite, so no production file changed. No semantic analysis refresh or runtime adoption is claimed.

## FULL_DIFFS

Complete actual new-file diff (`/dev/null` → `tests/test_cycle_semantics_definition_effect_order_cpython.py`):

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_definition_effect_order_cpython.py
@@ -0,0 +1,240 @@
+import json
+import subprocess
+import sys
+from pathlib import Path
+
+import pytest
+
+
+CASES = [
+    pytest.param(
+        """
+def deco(fn):
+    trace.append("apply")
+    return fn
+
+@deco
+def f():
+    trace.append("body")
+
+trace.append("after")
+""",
+        ["apply", "after"],
+        None,
+        False,
+        id="function-decorator-application",
+    ),
+    pytest.param(
+        """
+def upper(fn):
+    trace.append("apply-upper")
+    return fn
+
+def lower(fn):
+    trace.append("apply-lower")
+    return fn
+
+@upper
+@lower
+def f():
+    pass
+""",
+        ["apply-lower", "apply-upper"],
+        None,
+        False,
+        id="stacked-application-bottom-up",
+    ),
+    pytest.param(
+        """
+def make(label):
+    trace.append("evaluate-" + label)
+
+    def deco(fn):
+        trace.append("apply-" + label)
+        return fn
+
+    return deco
+
+@make("upper")
+@make("lower")
+def f():
+    pass
+""",
+        [
+            "evaluate-upper",
+            "evaluate-lower",
+            "apply-lower",
+            "apply-upper",
+        ],
+        None,
+        False,
+        id="factory-evaluation-and-application",
+    ),
+    pytest.param(
+        """
+def make():
+    trace.append("decorator-expression")
+
+    def deco(fn):
+        trace.append("application")
+        return fn
+
+    return deco
+
+def default():
+    trace.append("default-expression")
+    return 7
+
+@make()
+def f(x=default()):
+    pass
+""",
+        [
+            "decorator-expression",
+            "default-expression",
+            "application",
+        ],
+        None,
+        False,
+        id="decorator-expression-before-default",
+    ),
+    pytest.param(
+        """
+def deco(cls):
+    trace.append("class-decoration")
+    return cls
+
+@deco
+class C:
+    trace.append("class-body")
+""",
+        ["class-body", "class-decoration"],
+        None,
+        False,
+        id="class-body-before-decoration",
+    ),
+    pytest.param(
+        """
+def deco(fn):
+    def replacement():
+        trace.append("replacement-called")
+    return replacement
+
+@deco
+def f():
+    trace.append("original-called")
+
+f()
+""",
+        ["replacement-called"],
+        None,
+        False,
+        id="decorator-replaces-function-binding",
+    ),
+    pytest.param(
+        """
+def deco(fn):
+    import pkg.child
+    trace.append("decorator-import")
+    return fn
+
+@deco
+def f():
+    pass
+""",
+        ["decorator-import"],
+        None,
+        True,
+        id="decorator-imports-during-definition",
+    ),
+    pytest.param(
+        """
+def deco(fn):
+    trace.append("before-error")
+    raise RuntimeError("decorator failed")
+
+@deco
+def f():
+    pass
+
+trace.append("unreachable")
+""",
+        ["before-error"],
+        "RuntimeError",
+        False,
+        id="decorator-exception-stops-module",
+    ),
+]
+
+
+RUNNER = """
+import json
+import sys
+
+sys.path.insert(0, sys.argv[1])
+
+trace = []
+error = None
+
+try:
+    exec(
+        compile(sys.argv[2], "<definition-effects>", "exec"),
+        {"trace": trace},
+    )
+except Exception as exc:
+    error = type(exc).__name__
+
+print(json.dumps({
+    "trace": trace,
+    "error": error,
+    "child_imported": "pkg.child" in sys.modules,
+}))
+"""
+
+
+@pytest.mark.parametrize(
+    "source,expected_trace,expected_error,child_imported",
+    CASES,
+)
+def test_definition_effect_order_cpython(
+    tmp_path: Path,
+    source: str,
+    expected_trace: list[str],
+    expected_error: str | None,
+    child_imported: bool,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+
+    (package / "__init__.py").write_text(
+        "pass\n", encoding="utf-8"
+    )
+    (package / "child.py").write_text(
+        "pass\n", encoding="utf-8"
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
+            source,
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
+        "trace": expected_trace,
+        "error": expected_error,
+        "child_imported": child_imported,
+    }
```

## FINAL_VERDICT

- CONTRACT_PROVED: The exact CPython-only baseline was added and all eight new cases passed within the requested focused test run. No Contextor model parity or runtime semantic certification is claimed. Stop after tests and audit.
