# P5-M08-I2 — Bare return function semantics

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. `_compile` resolved to `contextor/core/cycle_semantics/package_model.py:479-1059`, canonical LIVE revision 1311, source fresh, `workspace_sync=verified`; cycle semantics stale. HEAD `fc6f86b7fcd0dcc81ab8145ea51f5aecbe4891bb`; initial `git status --short` clean. Active backend interpreter `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M08-I1 frame anchors matched `execution/state.py:31-78` and `package_model.py:1495-1496,1582-1616,2176-2196,2293-2298`. The exact restricted body loop at `package_model.py:960-968` and UNKNOWN fallback/shared advancement at `:2293-2298` matched. The target test did not exist.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- Added `tests/test_cycle_semantics_bare_return_frames.py`
- `walkthrough.md` (this report). No other source or test change.

## BARE_RETURN_COMPILER_CONTRACT

- DIRECT_EVIDENCE: `package_model.py:960-975` now emits `_Step("RETURN_FUNCTION")` for `ast.Return` with `value is None` inside a restricted zero-argument FunctionDef. The existing loop continues compiling later import steps but execution can stop before reaching them. All other body-statement handling is unchanged.
- DIRECT_EVIDENCE: Direct assertions showed `def f(): return; import pkg.child` compiles to `DEFINE_FUNCTION` with `function_body` ops `[RETURN_FUNCTION, IMPORT]`, and the import step retains `function_local=True`. `return 7` compiles to `DEFINE_OPAQUE_FUNCTION`; `_Step.__dataclass_fields__` remains the original 16 fields. `_compile.__module__` and evaluator `__module__` remain `contextor.core.cycle_semantics.package_model`.

## FUNCTION_FRAME_TERMINATION

- DIRECT_EVIDENCE: `package_model.py:2185-2191` accepts RETURN_FUNCTION only when `active_frame` is `_FunctionFrame`, pops that frame and continues. It does not advance the popped frame, change module state, emit READY/BIND_CHILD or refund the return step's budget charge. The caller was already advanced in CALL_FUNCTION (`package_model.py:2203-2205`), so its next module step resumes after return.
- CODE_PATH_PROVED: A RETURN_FUNCTION step outside a function frame returns UNKNOWN. Function-frame normal completion still follows M08-I1 at `package_model.py:1592-1614`; the new early return bypasses that completion path.

## CPYTHON_PARITY_MATRIX

DIRECT_EVIDENCE: The exact new tests run isolated CPython and compare `pkg.` import order with the model's START_IMPORT events for MODEL_PASS cases (`tests/test_cycle_semantics_bare_return_frames.py:11-169`).

| Case | CPython imports | Model outcome | Model child START_IMPORT | Status |
|---|---|---|---|---|
| return-skips-import | none | MODEL_PASS | none | observed parity |
| import-before-return-only | `pkg.first` | MODEL_PASS | `pkg.first` | observed parity |
| alias-return-resumes-module | `pkg.after` | MODEL_PASS | `pkg.after` | observed parity |
| valued-return-still-unknown | none | UNKNOWN | not asserted as parity | conservative boundary |

- DIRECT_EVIDENCE: An additional direct evaluator assertion for `import pkg.first; return; import pkg.child` followed by module-level `import pkg.after` observed `START_IMPORT(pkg.first)` before `START_IMPORT(pkg.after)`, no `pkg.child` import, exactly one module READY, and no extra BIND_CHILD for function completion. Its complete event operations were `START_IMPORT(pkg), DEFINE_FUNCTION(f), CALL_FUNCTION(f), START_IMPORT(pkg.first), READY(pkg.first), BIND_CHILD(pkg.first), FUNCTION_LOCAL_IMPORT(pkg.first), START_IMPORT(pkg.after), READY(pkg.after), BIND_CHILD(pkg.after), IMPORT(pkg.after), READY(pkg)`.

## NEGATIVE_VALUED_RETURN_CONTRACT

- DIRECT_EVIDENCE: `return 7` remains outside the bare-return condition (`package_model.py:963-971`), so the function is opaque and its call returns UNKNOWN before a CALL_FUNCTION event. The negative test asserts this (`tests/test_cycle_semantics_bare_return_frames.py:46-54,162-169`). CPython succeeds and imports neither child; UNKNOWN is not presented as parity.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Required focused command across nine test files returned `296 passed, 2 warnings in 31.48s`. The two warnings were third-party Authlib deprecations. Direct compiler/frame assertions returned `DIRECT_BARE_RETURN_CONTRACT_PASS`.
- DIRECT_EVIDENCE: `git diff --check` exited 0 before report rewrite. No full pytest, SCC02, FULL, update_file, restart, Git add/commit/push, or index/history mutation.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Post-change canonical LIVE revision 1313: changed production module fresh with `workspace_sync=verified`; syntax errors 0; DFS structural cycle count 16; active warnings 16; cycle semantics stale. Module-context dependency evidence was read at revision 1313 and showed package_model's existing hard dependency on `execution.calls`; no new source import was added by this patch. The response was bounded, so a complete edge inventory is not claimed. No current semantic classification or loaded-backend adoption is inferred from source freshness.

## FULL_DIFFS

Complete changed-source diff:

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 41cb31a..7b0384b 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -960,6 +960,15 @@ def _compile(
                     if isinstance(body_statement, ast.Pass):
                         continue

+                    if (
+                        isinstance(body_statement, ast.Return)
+                        and body_statement.value is None
+                    ):
+                        function_steps.append(
+                            _Step("RETURN_FUNCTION")
+                        )
+                        continue
+
                     if not isinstance(
                         body_statement,
                         (ast.Import, ast.ImportFrom),
@@ -2173,6 +2182,13 @@ def evaluate_package_import_order(
                 )
             )

+        elif step.op == "RETURN_FUNCTION":
+            if not isinstance(active_frame, _FunctionFrame):
+                return result("UNKNOWN", module)
+
+            frames.pop()
+            continue
+
         elif step.op == "CALL_FUNCTION":
             body = _execute_restricted_call(
                 step,
```

Complete new-test diff (`/dev/null` → `tests/test_cycle_semantics_bare_return_frames.py`):

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_bare_return_frames.py
@@ -0,0 +1,169 @@
+import ast
+import subprocess
+import sys
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
+            "def f():\n"
+            "    return\n"
+            "    import pkg.child\n"
+            "f()\n"
+        ),
+        (),
+        "MODEL_PASS",
+        id="return-skips-import",
+    ),
+    pytest.param(
+        (
+            "def f():\n"
+            "    import pkg.first\n"
+            "    return\n"
+            "    import pkg.child\n"
+            "f()\n"
+        ),
+        ("pkg.first",),
+        "MODEL_PASS",
+        id="import-before-return-only",
+    ),
+    pytest.param(
+        (
+            "def f():\n"
+            "    return\n"
+            "    import pkg.child\n"
+            "g = f\n"
+            "g()\n"
+            "import pkg.after\n"
+        ),
+        ("pkg.after",),
+        "MODEL_PASS",
+        id="alias-return-resumes-module",
+    ),
+    pytest.param(
+        (
+            "def f():\n"
+            "    return 7\n"
+            "    import pkg.child\n"
+            "f()\n"
+        ),
+        (),
+        "UNKNOWN",
+        id="valued-return-still-unknown",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,expected_imports,expected_outcome",
+    CASES,
+)
+def test_bare_return_frame_and_cpython(
+    tmp_path,
+    source,
+    expected_imports,
+    expected_outcome,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+
+    (package / "__init__.py").write_text(
+        source, encoding="utf-8"
+    )
+
+    for name in ("child", "first", "after"):
+        (package / (name + ".py")).write_text(
+            "pass\n", encoding="utf-8"
+        )
+
+    runner = """
+import builtins
+import importlib
+import json
+import sys
+
+sys.path.insert(0, sys.argv[1])
+original = builtins.__import__
+observed = []
+
+def traced(name, *args, **kwargs):
+    if name.startswith("pkg."):
+        observed.append(name)
+    return original(name, *args, **kwargs)
+
+builtins.__import__ = traced
+
+error = None
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
+    process = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            runner,
+            str(tmp_path),
+        ],
+        text=True,
+        capture_output=True,
+        timeout=20,
+        check=False,
+    )
+
+    assert process.returncode == 0, process.stderr
+
+    import json
+    observed = json.loads(process.stdout)
+
+    assert observed["error"] is None
+    assert observed["imports"] == list(expected_imports)
+
+    sources = {
+        "pkg.__init__": ast.parse(source),
+    }
+
+    for name in ("child", "first", "after"):
+        sources["pkg." + name] = ast.parse("pass\n")
+
+    result = evaluate_package_import_order(
+        sources,
+        "pkg",
+    )
+
+    assert result.outcome == expected_outcome
+
+    if expected_outcome == "MODEL_PASS":
+        imported = [
+            event.target
+            for event in result.events
+            if event.operation == "START_IMPORT"
+            and event.target in {
+                "pkg.child",
+                "pkg.first",
+                "pkg.after",
+            }
+        ]
+
+        assert imported == list(expected_imports)
+
+    if expected_outcome == "UNKNOWN":
+        assert not any(
+            event.operation == "CALL_FUNCTION"
+            for event in result.events
+        )
```

## FINAL_VERDICT

- CONTRACT_PROVED for this bounded change: bare return now ends only its restricted function frame, preserving earlier imports and skipping later body steps. Four CPython-backed cases, the focused regression set and direct compiler/frame checks passed. Cycle semantics and backend loaded-code adoption remain unverified. Stop after implementation and audit.
