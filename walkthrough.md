# P5-M08-I5 — restricted return value transport

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP queried `package_model.py` first. Canonical LIVE revision 1319, source fresh and `workspace_sync=verified`; `cycle_semantics=stale`. Initial HEAD `8003547c6fce9047379b936fe7414d39322b8066`; initial `git status --short` clean. Backend `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` (CPython 3.15.2, established by prior M08-I4 and used in this task).
- DIRECT_EVIDENCE: Accepted anchors matched current source: `_Step` fields (`execution/steps.py:6-25`), `_FunctionFrame` and `_advance_frame` (`execution/state.py:31-72`), function/call compiler (`package_model.py:940-1149`), return and call evaluator (`package_model.py:2279-2348`). `replace` was already imported at `package_model.py:11`. Package child-name collision guards were present at `package_model.py:1543-1570,1636-1672`. All `_FunctionFrame` constructors and `_advance_frame` consumers were inventoried by targeted `rg`.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/steps.py`
- `contextor/core/cycle_semantics/execution/state.py`
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_return_value_transport.py` (new)
- `walkthrough.md` (this report)

## RETURN_VALUE_TRANSPORT

- CODE_PATH_PROVED: The compiler emits `RETURN_FUNCTION` with `step.symbol` only for a return of the sole positional parameter (`package_model.py:1008-1020`). It marks a restricted function opaque if that kind of return is combined with an import step (`package_model.py:1063-1076`). Bare return remains supported.
- CODE_PATH_PROVED: On return, the evaluator reads the current function frame's local binding, pops the function frame, and writes the result to the suspended module's result binding (`package_model.py:2279-2301`). Normal function-frame exhaustion binds abstract `None` (`package_model.py:1691-1699`). The caller was already advanced before the function frame was pushed (`package_model.py:2337-2348`).

## FUNCTION_OBJECT_IDENTITY

- CODE_PATH_PROVED: `_execute_restricted_call` returns the bound object from the current namespace and places that same object in the frame's `local_bindings` (`execution/calls.py:27-52`); `RETURN_FUNCTION` reads and rebinds it without copying (`package_model.py:2286-2301`). The positive CPython/model cases prove execution of the returned object's original body after aliasing and rebinding (`tests/test_cycle_semantics_return_value_transport.py:18-37,75-117`).

## ASSIGNED_CALL_CONTRACT

- CODE_PATH_PROVED: `_compile` accepts `result = simple_name(...)` only with zero or one literal or ordinary name argument, preserving the pre-existing assignment-target and dunder restrictions (`package_model.py:683-793`). Expression calls use the same argument boundary (`package_model.py:1112-1149`). Name arguments are looked up in the current module namespace immediately before admission; missing names yield `UNKNOWN` (`package_model.py:2303-2323`). A new frame carries `result_binding` (`execution/state.py:31-72; package_model.py:2339-2348`). Both package child-name collision guards now include assigned `CALL_FUNCTION` (`package_model.py:1557-1567,1657-1668`).

## CPYTHON_PARITY_MATRIX

| Case | CPython 3.15.2 | Model | Model CALL_FUNCTION |
|---|---|---|---|
| pass-through identity | success; `pkg.child` | MODEL_PASS; child | identity, alias |
| alias after original rebinding | success; `pkg.child` | MODEL_PASS; child | identity, alias |
| independent calls | success; first, second | MODEL_PASS; first, second | identity, identity, a, b |
| bare return assigned | success; no child | MODEL_PASS | f |
| natural completion assigned | success; no child | MODEL_PASS | f |
| unresolved argument name | NameError; no child | UNKNOWN | none |
| unsupported global return lookup | success; no child | UNKNOWN | none |
| returned noncallable | TypeError; no child | UNKNOWN | identity only |
| local import shadows parameter | success; `pkg.child` | UNKNOWN | none |

- DIRECT_EVIDENCE: The nine parameterized cases in `tests/test_cycle_semantics_return_value_transport.py:18-118` execute the same source under isolated CPython and as AST through the model. Exact error type, ordered child import trace, model outcome and call-event order are asserted. `UNKNOWN` is not claimed as parity.

## NEGATIVE_CONTRACTS

- CODE_PATH_PROVED: Unsupported global return is opaque because zero-parameter `return original` does not match the parameter-return branch (`package_model.py:1008-1025`). Import followed by parameter return is opaque by the mixed-step guard (`package_model.py:1063-1076`). Missing name and noncallable target return `UNKNOWN` before a successful call event for that target (`package_model.py:2307-2331`). Foreign restricted function calls remain rejected by `execution/calls.py:35-42`.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: The exact requested 13-file focused pytest command completed with **314 passed, 2 third-party Authlib deprecation warnings**, exit code 0, 39.79 s. `git diff --check` exited 0; Git printed only line-ending notices. No full suite or SCC02 was run.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Canonical LIVE revision **1323**; `package_model.py`, `execution/state.py` and `execution/steps.py` source fresh with `workspace_sync=verified`; module/graph/topology/cycles fresh; `cycle_semantics=stale`. Syntax errors 0, DFS structural cycle count 16, active warnings 16. `execution/state.py` still depends on `execution.class_facts` and `execution.steps`; `execution.steps` has no outbound hard edge. Source freshness is not runtime adoption or fresh semantic classification.

## FULL_DIFFS

Complete source/test diffs follow. Git's trailing spaces on blank context lines are omitted in the Markdown rendering only.

### execution/steps.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/steps.py b/contextor/core/cycle_semantics/execution/steps.py
index fd962a9..2d92617 100644
--- a/contextor/core/cycle_semantics/execution/steps.py
+++ b/contextor/core/cycle_semantics/execution/steps.py
@@ -23,3 +23,4 @@ class _Step:
     passive_metaclass_body: bool = False
     parameters: tuple[str, ...] = ()
     call_argument_values: tuple[object, ...] = ()
+    call_argument_name: str | None = None
```

### execution/state.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index 17d54aa..7fd4221 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -38,6 +38,7 @@ class _FunctionFrame:
         compare=False,
         repr=False,
     )
+    result_binding: str | None = None


 def _frame_module(
@@ -65,6 +66,7 @@ def _advance_frame(
             frame.index + 1,
             frame.steps,
             frame.local_bindings,
+            frame.result_binding,
         )
     return (frame[0], frame[1] + 1)
```

### package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 10fdf8f..0500033 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -749,6 +749,42 @@ def _compile(
                         name,
                     )
                 )
+            elif (
+                isinstance(value, ast.Call)
+                and isinstance(value.func, ast.Name)
+                and not value.func.id.startswith("__")
+                and len(value.args) <= 1
+                and not value.keywords
+                and all(
+                    (
+                        type(argument) is ast.Constant
+                        and type(argument.value)
+                        in (type(None), bool, int, str)
+                    )
+                    or (
+                        type(argument) is ast.Name
+                        and not argument.id.startswith("__")
+                    )
+                    for argument in value.args
+                )
+            ):
+                steps.append(
+                    _Step(
+                        "CALL_FUNCTION",
+                        target=value.func.id,
+                        binding=name,
+                        call_argument_name=(
+                            value.args[0].id
+                            if value.args and type(value.args[0]) is ast.Name
+                            else None
+                        ),
+                        call_argument_values=tuple(
+                            argument.value
+                            for argument in value.args
+                            if type(argument) is ast.Constant
+                        ),
+                    )
+                )
             else:
                 return None

@@ -969,6 +1005,20 @@ def _compile(
                         )
                         continue

+                    if (
+                        isinstance(body_statement, ast.Return)
+                        and isinstance(body_statement.value, ast.Name)
+                        and len(args.args) == 1
+                        and body_statement.value.id == args.args[0].arg
+                    ):
+                        function_steps.append(
+                            _Step(
+                                "RETURN_FUNCTION",
+                                symbol=body_statement.value.id,
+                            )
+                        )
+                        continue
+
                     if not isinstance(
                         body_statement,
                         (ast.Import, ast.ImportFrom),
@@ -1010,6 +1060,20 @@ def _compile(
                         for item in compiled
                     )

+            if restricted_callable and any(
+                item.op == "RETURN_FUNCTION"
+                and item.symbol is not None
+                for item in function_steps
+            ) and any(
+                item.op in {
+                    "IMPORT",
+                    "FROM",
+                    "PREPARE_FROM_MEMBER",
+                }
+                for item in function_steps
+            ):
+                restricted_callable = False
+
             if restricted_callable:
                 steps.append(
                     _Step(
@@ -1054,9 +1118,15 @@ def _compile(
                 or len(expression.args) > 1
                 or expression.keywords
                 or any(
-                    not isinstance(argument, ast.Constant)
-                    or type(argument.value)
-                    not in (type(None), bool, int, str)
+                    not (
+                        type(argument) is ast.Constant
+                        and type(argument.value)
+                        in (type(None), bool, int, str)
+                    )
+                    and not (
+                        type(argument) is ast.Name
+                        and not argument.id.startswith("__")
+                    )
                     for argument in expression.args
                 )
             ):
@@ -1066,9 +1136,16 @@ def _compile(
                 _Step(
                     "CALL_FUNCTION",
                     target=expression.func.id,
+                    call_argument_name=(
+                        expression.args[0].id
+                        if expression.args
+                        and type(expression.args[0]) is ast.Name
+                        else None
+                    ),
                     call_argument_values=tuple(
                         argument.value
                         for argument in expression.args
+                        if type(argument) is ast.Constant
                     ),
                 )
             )
@@ -1480,7 +1557,7 @@ def evaluate_package_import_order(
         writes_child = any(
             step.binding in children
             and (
-                step.op in {"BIND", "ALIAS"}
+                step.op in {"BIND", "ALIAS", "CALL_FUNCTION"}
                 or (step.op == "FROM" and step.target != package)
             )
             for step in programs[package]
@@ -1580,7 +1657,7 @@ def evaluate_package_import_order(
                 writes_child = any(
                     step.binding in children
                     and (
-                        step.op in {"BIND", "ALIAS"}
+                        step.op in {"BIND", "ALIAS", "CALL_FUNCTION"}
                         or (
                             step.op == "FROM"
                             and step.target != module
@@ -1614,6 +1691,8 @@ def evaluate_package_import_order(

         if index >= len(steps):
             if isinstance(active_frame, _FunctionFrame):
+                if active_frame.result_binding is not None:
+                    namespaces[module][active_frame.result_binding] = None
                 frames.pop()
                 execution_cursor.step_budget += 1
             else:
@@ -2201,14 +2280,46 @@ def evaluate_package_import_order(
             if not isinstance(active_frame, _FunctionFrame):
                 return result("UNKNOWN", module)

+            returned_value = None
+
+            if step.symbol is not None:
+                if step.symbol not in active_frame.local_bindings:
+                    return result("UNKNOWN", module, step.symbol)
+
+                returned_value = active_frame.local_bindings[step.symbol]
+
+            result_binding = active_frame.result_binding
+
             frames.pop()
+
+            if result_binding is not None:
+                namespaces[module][result_binding] = returned_value
+
             continue

         elif step.op == "CALL_FUNCTION":
+            call_step = step
+
+            if step.call_argument_name is not None:
+                if step.call_argument_name not in namespaces[module]:
+                    return result(
+                        "UNKNOWN",
+                        module,
+                        step.call_argument_name,
+                    )
+
+                call_step = replace(
+                    step,
+                    call_argument_values=(
+                        namespaces[module][step.call_argument_name],
+                    ),
+                    call_argument_name=None,
+                )
+
             local_bindings: dict[str, object | None] = {}

             body = _execute_restricted_call(
-                step,
+                call_step,
                 module=module,
                 namespaces=namespaces,
                 local_bindings=local_bindings,
@@ -2232,6 +2343,7 @@ def evaluate_package_import_order(
                     0,
                     body,
                     local_bindings,
+                    step.binding,
                 )
             )
             continue
```

### tests/test_cycle_semantics_return_value_transport.py

```diff
diff --git a/tests/test_cycle_semantics_return_value_transport.py b/tests/test_cycle_semantics_return_value_transport.py
new file mode 100644
index 0000000..d927962
--- /dev/null
+++ b/tests/test_cycle_semantics_return_value_transport.py
@@ -0,0 +1,134 @@
+import ast
+import json
+import subprocess
+import sys
+
+import pytest
+
+from contextor.core.cycle_semantics.execution.calls import (
+    _execute_restricted_call,
+    _new_restricted_function,
+)
+from contextor.core.cycle_semantics.execution.state import (
+    _FunctionFrame,
+    _advance_frame,
+)
+from contextor.core.cycle_semantics.execution.steps import _Step
+from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
+from test_cycle_semantics_decorator_import_effect_baseline import RUNNER
+
+
+CASES = [
+    pytest.param(
+        "def original():\n    import pkg.child\ndef identity(fn):\n    return fn\nalias = identity(original)\nalias()\n",
+        None, ("pkg.child",), "MODEL_PASS", ("identity", "alias"),
+        id="pass-through-identity",
+    ),
+    pytest.param(
+        "def original():\n    import pkg.child\nsaved = original\ndef identity(fn):\n    return fn\noriginal = None\nalias = identity(saved)\nalias()\n",
+        None, ("pkg.child",), "MODEL_PASS", ("identity", "alias"),
+        id="alias-after-rebinding",
+    ),
+    pytest.param(
+        "def one():\n    import pkg.first\ndef two():\n    import pkg.second\ndef identity(fn):\n    return fn\na = identity(one)\nb = identity(two)\na()\nb()\n",
+        None, ("pkg.first", "pkg.second"), "MODEL_PASS",
+        ("identity", "identity", "a", "b"),
+        id="independent-calls",
+    ),
+    pytest.param(
+        "def f():\n    return\nresult = f()\n",
+        None, (), "MODEL_PASS", ("f",), id="bare-return-assigned",
+    ),
+    pytest.param(
+        "def f():\n    pass\nresult = f()\n",
+        None, (), "MODEL_PASS", ("f",), id="natural-completion-assigned",
+    ),
+    pytest.param(
+        "def identity(fn):\n    return fn\nalias = identity(missing)\n",
+        "NameError", (), "UNKNOWN", (), id="unresolved-argument-name",
+    ),
+    pytest.param(
+        "def original():\n    pass\ndef f():\n    return original\nalias = f()\n",
+        None, (), "UNKNOWN", (), id="unsupported-global-return-lookup",
+    ),
+    pytest.param(
+        "def identity(fn):\n    return fn\nalias = identity(7)\nalias()\n",
+        "TypeError", (), "UNKNOWN", ("identity",),
+        id="returned-noncallable",
+    ),
+    pytest.param(
+        "def f(x):\n    import pkg.child as x\n    return x\nresult = f(7)\n",
+        None, ("pkg.child",), "UNKNOWN", (),
+        id="local-import-shadows-parameter",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,expected_error,expected_imports,expected_outcome,expected_calls",
+    CASES,
+)
+def test_return_value_transport_matches_cpython(
+    tmp_path, source, expected_error, expected_imports,
+    expected_outcome, expected_calls,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+    for child in ("child", "first", "second"):
+        (package / f"{child}.py").write_text("pass\n", encoding="utf-8")
+
+    process = subprocess.run(
+        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
+        capture_output=True, text=True, timeout=20, check=False,
+    )
+    assert process.returncode == 0, process.stderr
+    assert json.loads(process.stdout) == {
+        "error": expected_error,
+        "imports": list(expected_imports),
+    }
+
+    sources = {"pkg.__init__": ast.parse(source)}
+    for child in ("child", "first", "second"):
+        sources[f"pkg.{child}"] = ast.parse("pass\n")
+    result = evaluate_package_import_order(sources, "pkg")
+    assert result.outcome == expected_outcome
+    assert tuple(
+        event.symbol for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    ) == expected_calls
+    if expected_outcome == "MODEL_PASS":
+        assert tuple(
+            event.target for event in result.events
+            if event.operation == "START_IMPORT"
+            and event.target in {"pkg.child", "pkg.first", "pkg.second"}
+        ) == expected_imports
+    else:
+        assert not any(
+            event.operation == "START_IMPORT"
+            and event.target in {"pkg.child", "pkg.first", "pkg.second"}
+            for event in result.events
+        )
+
+
+def test_returned_function_retains_object_identity():
+    body = (_Step("RETURN_FUNCTION"),)
+    function = _new_restricted_function("pkg", body)
+    local_bindings = {"fn": function}
+    frame = _FunctionFrame("pkg", 0, body, local_bindings, "alias")
+    advanced = _advance_frame(frame)
+    assert advanced.result_binding == "alias"
+    assert advanced.local_bindings is local_bindings
+    assert local_bindings["fn"] is function
+    assert _execute_restricted_call(
+        _Step("CALL_FUNCTION", target="alias"), module="pkg",
+        namespaces={"pkg": {"alias": function}}, local_bindings={},
+    ) is body
+
+
+def test_foreign_function_remains_rejected():
+    foreign = _new_restricted_function("other", ())
+    assert _execute_restricted_call(
+        _Step("CALL_FUNCTION", target="alias"), module="pkg",
+        namespaces={"pkg": {"alias": foreign}}, local_bindings={},
+    ) is None
```

## FINAL_VERDICT

CONTRACT_PROVED for the nine listed CPython cases and bounded return transport. Focused tests passed. Canonical source and graph are fresh, while cycle semantics remain stale; no fresh warning-suppression or runtime-safety claim is made. STOP after this stage.
