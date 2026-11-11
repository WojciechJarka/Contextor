# P5-M08-I7 — import binding conflict before parameter return

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP first reported canonical LIVE revision 1328, `package_model.py` source fresh, `workspace_sync=verified`, structural cycles fresh and cycle semantics stale. HEAD `1075211bfacee3c3da07fe6c2ca0bdbb034b7f1b`; initial `git status --short` clean. Active backend `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, CPython 3.15.2.
- DIRECT_EVIDENCE: Existing blanket guard matched at `contextor/core/cycle_semantics/package_model.py:1071-1084`. `IMPORT.binding` derives from `asname` or root name at `:529-537`; `FROM.binding` derives from alias at `:619-650`; `PREPARE_FROM_MEMBER` has no binding at `:600-611`. Restricted function body accepts only pass, bare/parameter return and imports at `:1001-1070`. M08-I6 and I7-T1 files were present.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_decorator_import_binding_conflicts.py` (new)
- `tests/test_cycle_semantics_decorator_import_return_gate.py`
- `tests/test_cycle_semantics_named_function_decorators.py`
- `tests/test_cycle_semantics_decorator_import_effect_baseline.py`
- `walkthrough.md` (this report)

## REPLACED_BLANKET_RESTRICTION

- CODE_PATH_PROVED: The blanket mixed import/valued-return rejection was replaced by a positional scan of earlier `IMPORT`/`FROM` steps binding the returned parameter name (`package_model.py:1072-1095`). No other production branch was edited. This is a syntax-level conservative restriction; it does not execute or infer an imported value.

## LOCAL_BINDING_CONFLICT_POLICY

- CODE_PATH_PROVED: `import pkg.child` binds `pkg`, `import pkg.child as alias` binds `alias`, and `from pkg.child import item as other` binds `other`; only an earlier binding matching `RETURN_FUNCTION.symbol` makes the restricted function opaque (`package_model.py:529-537,619-650,1072-1095`). Imports after a return do not affect that return. Function-local import execution remains in the existing helper and does not write the module namespace (`execution/imports.py:78-85,244-253`).

## CPYTHON_PARITY_MATRIX

| Case | CPython expected in new test | Model expected in new test |
|---|---|---|
| nonconflicting import | success; child | MODEL_PASS; deco |
| nonconflicting import alias | success; child, after | MODEL_PASS; deco, f |
| nonconflicting from binding | success; child | MODEL_PASS; deco |
| import alias overwrites parameter | success; child | UNKNOWN |
| from import overwrites parameter | success; child | UNKNOWN |
| root import overwrites parameter | success; child | UNKNOWN |
| unreachable import after return | success; after | MODEL_PASS; deco, f |
| reentrant import before final binding | ImportError; child | not MODEL_PASS |

- DIRECT_EVIDENCE: The eight new parameterized comparisons are in `tests/test_cycle_semantics_decorator_import_binding_conflicts.py:15-235`. The focused pytest run reached two failures in a separate pre-existing D03/D05 test; it did not report failures in the new file. This is not a claim that the full requested regression command passed.

## NEGATIVE_SHADOWING_CONTRACTS

- CODE_PATH_PROVED: Imports binding `fn` or `pkg` before `return fn`/`return pkg` cause `DEFINE_OPAQUE_FUNCTION` (or decorated compilation UNKNOWN) by `package_model.py:1072-1099`. The new negative tests compare CPython import traces with conservative model UNKNOWN; they do not classify Python's successful execution as a model error.

## REENTRANT_EARLY_BINDING_CONTRACT

- DIRECT_EVIDENCE: New reentrant case expects CPython ImportError when `pkg.child` imports `f` before decorator completion and demands the model not return MODEL_PASS (`tests/test_cycle_semantics_decorator_import_binding_conflicts.py:145-163,215-235`). The existing D03/D05 test at `tests/test_cycle_semantics_decorator_definition_effects.py:153-175` also covers entry-order behavior but has an unconditional historical `UNKNOWN` assertion.

## UPDATED_BASELINES

- DIRECT_EVIDENCE: Three requested baseline expectations changed: I7-T1 `import-then-parameter-return` to MODEL_PASS; named-function decorator `decorator-import-effect-unsupported` to MODEL_PASS and call `deco`; T2 `decorator-import-during-definition` to MODEL_PASS. Their CPython inputs and expected imports were unchanged. See full diffs below.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Requested 13-file pytest command exited **1: 2 failed, 310 passed, 2 third-party warnings, 44.19 s**. Both failures are `test_d03_d05_decorator_import_entry_dependency` for the `function_decorator` case in `tests/test_cycle_semantics_decorator_definition_effects.py:153-175`:
  - `pkg.a`, `should_succeed=False`: expected `UNKNOWN`, observed `EARLY_BINDING_HAZARD`.
  - `pkg.b`, `should_succeed=True`: expected `UNKNOWN`, observed `MODEL_PASS`.
- DIRECT_EVIDENCE: Traceback assertion: `assert modeled.outcome == "UNKNOWN"` at line 165. The test computes `_actual(...)` first, but its CPython result assertions at lines 169-173 were not reached in these failing instances. The output did not print complete model events or CPython trace; those observations remain UNKNOWN. Under the task's failure contract, no production or additional test adjustment was made and no further semantic run was performed.
- DIRECT_EVIDENCE: `git diff --check` exit 0; only line-ending notices. The source/test modifications remain in the worktree for audit; no Git index/history mutation was made.

## MCP_POST_CHANGE_AUDIT

- UNKNOWN: The task required post-change MCP audit only if all checks passed. Because the targeted command failed, no post-change MCP audit was requested. Pre-change canonical revision was 1328; post-change freshness, syntax and structural metrics are unverified in this stage.

## FULL_DIFFS

Complete actual task diffs follow. Blank context lines omit only Git's trailing context space in this Markdown representation.

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index c8c81a6..af766cc 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -1069,19 +1069,26 @@ def _compile(
                         for item in compiled
                     )

-            if restricted_callable and any(
-                item.op == "RETURN_FUNCTION"
-                and item.symbol is not None
-                for item in function_steps
-            ) and any(
-                item.op in {
-                    "IMPORT",
-                    "FROM",
-                    "PREPARE_FROM_MEMBER",
-                }
-                for item in function_steps
-            ):
-                restricted_callable = False
+            if restricted_callable:
+                parameter_returns = (
+                    (
+                        position,
+                        item.symbol,
+                    )
+                    for position, item in enumerate(function_steps)
+                    if (
+                        item.op == "RETURN_FUNCTION"
+                        and item.symbol is not None
+                    )
+                )
+
+                if any(
+                    earlier.op in {"IMPORT", "FROM"}
+                    and earlier.binding == returned_name
+                    for position, returned_name in parameter_returns
+                    for earlier in function_steps[:position]
+                ):
+                    restricted_callable = False

             if stmt.decorator_list and not restricted_callable:
                 return None
```

### tests/test_cycle_semantics_decorator_import_return_gate.py

```diff
diff --git a/tests/test_cycle_semantics_decorator_import_return_gate.py b/tests/test_cycle_semantics_decorator_import_return_gate.py
index b7611f8..31e8791 100644
--- a/tests/test_cycle_semantics_decorator_import_return_gate.py
+++ b/tests/test_cycle_semantics_decorator_import_return_gate.py
@@ -56,7 +56,7 @@ CASES = [
         "pass\n",
         None,
         ("pkg.child",),
-        "UNKNOWN",
+        "MODEL_PASS",
         id="import-then-parameter-return",
     ),
     pytest.param(
```

### tests/test_cycle_semantics_named_function_decorators.py

```diff
diff --git a/tests/test_cycle_semantics_named_function_decorators.py b/tests/test_cycle_semantics_named_function_decorators.py
index 806084b..3f66a8a 100644
--- a/tests/test_cycle_semantics_named_function_decorators.py
+++ b/tests/test_cycle_semantics_named_function_decorators.py
@@ -62,7 +62,7 @@ CASES = [
     ),
     pytest.param(
         "def deco(fn):\n    import pkg.child\n    return fn\n@deco\ndef f():\n    pass\n",
-        None, ("pkg.child",), "UNKNOWN", (),
+        None, ("pkg.child",), "MODEL_PASS", ("deco",),
         id="decorator-import-effect-unsupported",
     ),
 ]
```

### tests/test_cycle_semantics_decorator_import_effect_baseline.py

```diff
diff --git a/tests/test_cycle_semantics_decorator_import_effect_baseline.py b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
index 32d3067..4027548 100644
--- a/tests/test_cycle_semantics_decorator_import_effect_baseline.py
+++ b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
@@ -35,7 +35,7 @@ CASES = [
             "    pass\n"
         ),
         ("pkg.child",),
-        "UNKNOWN",
+        "MODEL_PASS",
         id="decorator-import-during-definition",
     ),
     pytest.param(
```

### tests/test_cycle_semantics_decorator_import_binding_conflicts.py

```diff
diff --git a/tests/test_cycle_semantics_decorator_import_binding_conflicts.py b/tests/test_cycle_semantics_decorator_import_binding_conflicts.py
new file mode 100644
index 0000000..589d5d7
--- /dev/null
+++ b/tests/test_cycle_semantics_decorator_import_binding_conflicts.py
@@ -0,0 +1,235 @@
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
+            "    return fn\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "pass\n",
+        None,
+        ("pkg.child",),
+        "MODEL_PASS",
+        ("deco",),
+        id="nonconflicting-import",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    import pkg.child as alias\n"
+            "    return fn\n"
+            "@deco\n"
+            "def f():\n"
+            "    import pkg.after\n"
+            "f()\n"
+        ),
+        "pass\n",
+        None,
+        ("pkg.child", "pkg.after"),
+        "MODEL_PASS",
+        ("deco", "f"),
+        id="nonconflicting-import-alias",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    from pkg.child import item as other\n"
+            "    return fn\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "item = 7\n",
+        None,
+        ("pkg.child",),
+        "MODEL_PASS",
+        ("deco",),
+        id="nonconflicting-from-binding",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    import pkg.child as fn\n"
+            "    return fn\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "pass\n",
+        None,
+        ("pkg.child",),
+        "UNKNOWN",
+        (),
+        id="import-alias-overwrites-parameter",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    from pkg.child import item as fn\n"
+            "    return fn\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "item = 7\n",
+        None,
+        ("pkg.child",),
+        "UNKNOWN",
+        (),
+        id="from-import-overwrites-parameter",
+    ),
+    pytest.param(
+        (
+            "def deco(pkg):\n"
+            "    import pkg.child\n"
+            "    return pkg\n"
+            "@deco\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+        "pass\n",
+        None,
+        ("pkg.child",),
+        "UNKNOWN",
+        (),
+        id="root-import-overwrites-parameter",
+    ),
+    pytest.param(
+        (
+            "def deco(fn):\n"
+            "    return fn\n"
+            "    import pkg.child as fn\n"
+            "@deco\n"
+            "def f():\n"
+            "    import pkg.after\n"
+            "f()\n"
+        ),
+        "pass\n",
+        None,
+        ("pkg.after",),
+        "MODEL_PASS",
+        ("deco", "f"),
+        id="unreachable-import-after-return",
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
+        "from pkg import f\n",
+        "ImportError",
+        ("pkg.child",),
+        None,
+        None,
+        id="reentrant-import-before-final-binding",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,child_source,error,imports,outcome,calls",
+    CASES,
+)
+def test_import_return_binding_conflict(
+    tmp_path,
+    source,
+    child_source,
+    error,
+    imports,
+    outcome,
+    calls,
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
+    (package / "after.py").write_text(
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
+    actual = json.loads(process.stdout)
+
+    assert actual == {
+        "error": error,
+        "imports": list(imports),
+    }
+
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
+            "pkg.child": ast.parse(child_source),
+            "pkg.after": ast.parse("pass\n"),
+        },
+        "pkg",
+    )
+
+    if outcome is None:
+        assert result.outcome != "MODEL_PASS"
+        return
+
+    assert result.outcome == outcome
+
+    if calls is not None:
+        assert tuple(
+            event.symbol
+            for event in result.events
+            if event.operation == "CALL_FUNCTION"
+        ) == calls
+
+    if outcome == "MODEL_PASS":
+        assert tuple(
+            event.target
+            for event in result.events
+            if event.operation == "START_IMPORT"
+            and event.target in {
+                "pkg.child",
+                "pkg.after",
+            }
+        ) == imports
```

## FINAL_VERDICT

**FAILED_REGRESSION / STOP.** The requested source and test edits remain uncommitted. Two historical D03/D05 assertions require UNKNOWN where the changed model now reports `EARLY_BINDING_HAZARD` and `MODEL_PASS`; CPython result assertions for those instances were not reached. Under the supplied failure contract, no independent repair or baseline weakening was performed. Full targeted pass, post-change MCP audit and FINAL PASS are not claimed.
