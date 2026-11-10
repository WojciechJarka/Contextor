# P5-M08-T3 — Call frame and return semantics baseline

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. `_execute_restricted_call` resolves to `contextor/core/cycle_semantics/execution/calls.py:25-45`; canonical LIVE revision 1305, source fresh, `workspace_sync=verified`, cycle semantics stale. HEAD `2ff92eb2f0838c82a1872a43ed91302c7dac956a`; initial status ` M walkthrough.md` only. That pre-existing discovery report was inspected during this task and overwritten as required.
- DIRECT_EVIDENCE: Active backend venv `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` reports CPython 3.15.2. M08-D2 anchors remain: `_RestrictedFunction` has only module/body (`execution/calls.py:9-22`); call helper splices body steps (`:25-45`); `_ExecutionCursor.frames` stores module/index tuples (`execution/state.py:30-40`); `_Step` has no parameter or return fields (`execution/steps.py:6-23`); `_compile` excludes argument-bearing calls and decorated functions (`package_model.py:935-955,1031-1048`). Target test did not exist before editing.

## FILES_CHANGED

- Added `tests/test_cycle_semantics_call_frame_baseline.py` exactly as specified. Complete new-file diff below.
- Overwrote `walkthrough.md`; no production or existing test file changed.

## CPYTHON_CALL_FRAME_MATRIX

DIRECT_EVIDENCE: The isolated subprocess uses the active Python 3.15.2 interpreter; the test checks the full observed JSON per case (`tests/test_cycle_semantics_call_frame_baseline.py:15-190`). All seven cases passed.

| Case | CPython `error` | CPython `pkg.` import trace |
|---|---|---|
| positional-identity-return | null | none |
| parameter-and-local-binding | null | none |
| return-skips-later-import | null | none |
| pass-through-decorator-defers-body | null | none |
| pass-through-decorator-then-call | null | `pkg.child` |
| return-callable-and-invoke | null | `pkg.child` |
| missing-required-argument | `TypeError` | none |

## CURRENT_MODEL_BOUNDARY_MATRIX

DIRECT_EVIDENCE: Each corresponding AST input returns UNKNOWN. Exact event tuples were read from the evaluator on the same CASES; the new test asserts the outcome (`tests/test_cycle_semantics_call_frame_baseline.py:179-190`).

| Case | Model outcome | Model events |
|---|---|---|
| positional-identity-return | UNKNOWN | none |
| parameter-and-local-binding | UNKNOWN | none |
| return-skips-later-import | UNKNOWN | none |
| pass-through-decorator-defers-body | UNKNOWN | none |
| pass-through-decorator-then-call | UNKNOWN | none |
| return-callable-and-invoke | UNKNOWN | none |
| missing-required-argument | UNKNOWN | `START_IMPORT(pkg)`, `DEFINE_OPAQUE_FUNCTION(identity)` |

UNKNOWN does not establish CPython/model parity or passivity.

## RETURN_AND_IMPORT_EFFECTS

- DIRECT_EVIDENCE: CPython `return 1` prevents the following `import pkg.child` in the same function; the tested source asserts the return value. A pass-through decorator leaves the body deferred until `f()`; that call imports `pkg.child`. Returning a function object and invoking the alias also imports `pkg.child` (`tests/test_cycle_semantics_call_frame_baseline.py:15-93`).
- CODE_PATH_PROVED: Current compiler stores a parameterized or return-containing body as opaque or rejects later expressions, and the call helper has no return-value representation (`package_model.py:935-1056`; `execution/calls.py:9-45`; `execution/steps.py:6-23`). None of the six successful CPython cases is certified by a MODEL_PASS here.

## NEGATIVE_ARITY_CONTRACT

- DIRECT_EVIDENCE: `identity()` without the required `value` parameter yields CPython `TypeError` and no `pkg.` import (`tests/test_cycle_semantics_call_frame_baseline.py:94-103,129-190`). The model records `DEFINE_OPAQUE_FUNCTION(identity)` then returns UNKNOWN, preserving a conservative boundary. This case must not be reported as MODEL_PASS on the observed source.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Required focused run across the four specified files returned `26 passed in 6.06s`.
- DIRECT_EVIDENCE: An initial `git diff --check` detected trailing whitespace in the pre-existing `walkthrough.md` discovery report at line 335. This report overwrite removes that line. The final `git diff --check` exited 0, with only an LF→CRLF advisory for `walkthrough.md`. No full pytest, SCC02, FULL, `update_file`, restart, Git add/commit/push, or index/history mutation.

## MCP_POST_TASK_AUDIT

- DIRECT_EVIDENCE: Post-task Contextor query remained at canonical LIVE revision 1305, production `execution/calls.py` source fresh, `workspace_sync=verified`, cycle semantics stale. No production file changed; status showed only the pre-existing modified report and the newly untracked test before report overwrite. No runtime adoption or semantic refresh is claimed.

## FULL_DIFFS

Complete actual new-file diff (`/dev/null` → `tests/test_cycle_semantics_call_frame_baseline.py`):

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_call_frame_baseline.py
@@ -0,0 +1,190 @@
+import ast
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
+            "def identity(value):\n"
+            "    return value\n"
+            "assert identity(7) == 7\n"
+        ),
+        None,
+        (),
+        id="positional-identity-return",
+    ),
+    pytest.param(
+        (
+            "def calculate(value):\n"
+            "    local = value\n"
+            "    return local\n"
+            "assert calculate(9) == 9\n"
+            "assert 'local' not in globals()\n"
+        ),
+        None,
+        (),
+        id="parameter-and-local-binding",
+    ),
+    pytest.param(
+        (
+            "def f():\n"
+            "    return 1\n"
+            "    import pkg.child\n"
+            "assert f() == 1\n"
+        ),
+        None,
+        (),
+        id="return-skips-later-import",
+    ),
+    pytest.param(
+        (
+            "def identity(fn):\n"
+            "    return fn\n"
+            "@identity\n"
+            "def f():\n"
+            "    import pkg.child\n"
+        ),
+        None,
+        (),
+        id="pass-through-decorator-defers-body",
+    ),
+    pytest.param(
+        (
+            "def identity(fn):\n"
+            "    return fn\n"
+            "@identity\n"
+            "def f():\n"
+            "    import pkg.child\n"
+            "f()\n"
+        ),
+        None,
+        ("pkg.child",),
+        id="pass-through-decorator-then-call",
+    ),
+    pytest.param(
+        (
+            "def original():\n"
+            "    import pkg.child\n"
+            "def return_callable():\n"
+            "    return original\n"
+            "alias = return_callable()\n"
+            "alias()\n"
+        ),
+        None,
+        ("pkg.child",),
+        id="return-callable-and-invoke",
+    ),
+    pytest.param(
+        (
+            "def identity(value):\n"
+            "    return value\n"
+            "identity()\n"
+        ),
+        "TypeError",
+        (),
+        id="missing-required-argument",
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
+@pytest.mark.parametrize(
+    "source,expected_error,expected_imports",
+    CASES,
+)
+def test_call_frame_cpython_and_current_model(
+    tmp_path: Path,
+    source: str,
+    expected_error: str | None,
+    expected_imports: tuple[str, ...],
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+
+    (package / "__init__.py").write_text(
+        source,
+        encoding="utf-8",
+    )
+    (package / "child.py").write_text(
+        "pass\n",
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
+        "error": expected_error,
+        "imports": list(expected_imports),
+    }
+
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
+            "pkg.child": ast.parse("pass\n"),
+        },
+        "pkg",
+    )
+
+    # Baseline of the current model, not the target
+    # outcome after call-frame implementation.
+    assert result.outcome == "UNKNOWN"
+
+    # A conservative UNKNOWN must not be presented
+    # as execution parity or as evidence of passivity.
```

## FINAL_VERDICT

- CONTRACT_PROVED: The exact seven-case CPython and current-model UNKNOWN baseline was added; all requested focused tests passed. The CPython outcomes and model uncertainty remain separate. Stop after this baseline.
