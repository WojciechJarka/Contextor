# P5-M08-I4 — single positional argument binding

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP used first. Initial canonical LIVE revision 1315, source fresh, `workspace_sync=verified`. Initial HEAD `d17534a8510d691a38196d50442423f46f280389`; initial status clean. Backend `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` is CPython 3.15.2. Source anchors matched at `execution/steps.py:6-23`, `execution/calls.py:8-38`, `execution/state.py:31-41`, `package_model.py:940-1064,1905-1917,2192-2212`. The external two-argument factory calls at `tests/test_cycle_semantics_function_identity_model.py:113-114` retain compatibility through the new default.

## FILES_CHANGED

`contextor/core/cycle_semantics/execution/steps.py`; `contextor/core/cycle_semantics/execution/calls.py`; `contextor/core/cycle_semantics/package_model.py`; `tests/test_cycle_semantics_single_positional_binding.py` (new). `walkthrough.md` is this report.

## ARGUMENT_BINDING_CONTRACT

CODE_PATH_PROVED: Compiler admits at most one ordinary required positional parameter and at most one literal call argument of type `None`, `bool`, `int`, or `str` (`package_model.py:946-956,1050-1073`). The supported function body remains pass/import/from-import/bare-return (`package_model.py:958-1012`). The call helper checks the current module namespace object, defining module and arity before binding (`execution/calls.py:27-52`).

## FUNCTION_SIGNATURE_REPRESENTATION

DIRECT_EVIDENCE: Two fields appended to frozen `_Step` (`execution/steps.py:24-25`); one field appended to `_RestrictedFunction` with an empty default (`execution/calls.py:12`). `_new_restricted_function` preserves two-argument calls (`execution/calls.py:16-27`).

## LOCAL_BINDING_ISOLATION

CODE_PATH_PROVED: A new dictionary is made for each call and stored in that call's frame (`package_model.py:2207-2239`); frame advancement retains the same dictionary (`execution/state.py:64-72`). Direct tests cover binding, two independent calls, aliasing, wrong arity, zero arguments and foreign calls (`tests/test_cycle_semantics_single_positional_binding.py:129-201`).

## CPYTHON_PARITY_MATRIX

| Case | CPython 3.15.2 | Model | Child START_IMPORT |
|---|---|---|---|
| required argument import | success; child | MODEL_PASS | child |
| alias signature | success; child | MODEL_PASS | child |
| argument and bare return | success; child only | MODEL_PASS | child |
| missing argument | TypeError; none | UNKNOWN | none |
| excess argument | TypeError; none | UNKNOWN | none |
| two arguments | TypeError; none | UNKNOWN | none |

DIRECT_EVIDENCE: `tests/test_cycle_semantics_single_positional_binding.py:20-128` asserts the six rows using the isolated CPython runner in `tests/test_cycle_semantics_decorator_import_effect_baseline.py:76-107`, then separately checks model outcome and events. This does not prove arbitrary call support.

## WRONG_ARITY_NEGATIVE_CONTRACTS

CODE_PATH_PROVED: Wrong arity returns `UNKNOWN` before `CALL_FUNCTION` or child import; two-argument syntax is rejected by compiler (`execution/calls.py:36-42`; `package_model.py:1050-1062,2207-2220`). Direct helper test proves no local write on failed arity (`tests/test_cycle_semantics_single_positional_binding.py:160-171`).

## UNCHANGED_UNKNOWN_BOUNDARIES

CODE_PATH_PROVED: Decorated definitions, computed/keyword call arguments, defaults for restricted calls and unsupported bodies remain outside this execution path (`package_model.py:142-225,946-1012,1050-1062`). Foreign functions return `None` from the helper (`execution/calls.py:36-42`). No parameter reads, valued returns or closures were introduced.

## TARGETED_TEST_RESULTS

DIRECT_EVIDENCE: The requested 11 focused test files completed with **289 passed, 2 third-party Authlib deprecation warnings**, exit 0, 41.20 s. `git diff --check` exit 0, with line-ending notices only.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Canonical LIVE revision **1319**, `workspace_sync=verified` for `package_model.py`, `execution/steps.py` and `execution/calls.py`; source/graph/topology/cycles fresh; `cycle_semantics=stale`. Syntax errors 0; DFS structural cycle count 16; active warning count 16. Hard edges remain `package_model -> execution.calls -> execution.steps`; steps has no outbound hard edge. Separate cyclic SCC count was not available from this query. Source freshness does not establish loaded-code adoption or current semantic classification.

## FULL_DIFFS

These are complete source/test diffs. Blank context lines omit only Git's trailing context space for Markdown whitespace hygiene.

### execution/steps.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/steps.py b/contextor/core/cycle_semantics/execution/steps.py
index 4c6245b..fd962a9 100644
--- a/contextor/core/cycle_semantics/execution/steps.py
+++ b/contextor/core/cycle_semantics/execution/steps.py
@@ -21,3 +21,5 @@ class _Step:
     base_names: tuple[str, ...] = ()
     explicit_metaclass_name: str | None = None
     passive_metaclass_body: bool = False
+    parameters: tuple[str, ...] = ()
+    call_argument_values: tuple[object, ...] = ()
```

### execution/calls.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index 32965a1..e9c5728 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -9,15 +9,18 @@ from .steps import _Step
 class _RestrictedFunction:
     defining_module: str
     body: tuple[_Step, ...]
+    parameters: tuple[str, ...] = ()


 def _new_restricted_function(
     defining_module: str,
     body: tuple[_Step, ...],
+    parameters: tuple[str, ...] = (),
 ) -> _RestrictedFunction:
     return _RestrictedFunction(
         defining_module=defining_module,
         body=body,
+        parameters=parameters,
     )


@@ -26,13 +29,23 @@ def _execute_restricted_call(
     *,
     module: str,
     namespaces: dict[str, dict[str, object | None]],
+    local_bindings: dict[str, object | None],
 ) -> tuple[_Step, ...] | None:
     value = namespaces[module].get(step.target)

     if (
         not isinstance(value, _RestrictedFunction)
         or value.defining_module != module
+        or len(value.parameters)
+        != len(step.call_argument_values)
     ):
         return None

+    local_bindings.update(
+        zip(
+            value.parameters,
+            step.call_argument_values,
+        )
+    )
+
     return value.body
```

### package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 7b0384b..10fdf8f 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -943,14 +943,14 @@ def _compile(

             args = stmt.args

-            restricted_callable = not (
-                args.posonlyargs
-                or args.args
-                or args.vararg is not None
-                or args.kwonlyargs
-                or args.kwarg is not None
-                or args.defaults
-                or args.kw_defaults
+            restricted_callable = (
+                not args.posonlyargs
+                and len(args.args) <= 1
+                and args.vararg is None
+                and not args.kwonlyargs
+                and args.kwarg is None
+                and not args.defaults
+                and not args.kw_defaults
             )

             function_steps: list[_Step] = []
@@ -1016,6 +1016,10 @@ def _compile(
                         "DEFINE_FUNCTION",
                         binding=stmt.name,
                         function_body=tuple(function_steps),
+                        parameters=tuple(
+                            parameter.arg
+                            for parameter in args.args
+                        ),
                     )
                 )
             else:
@@ -1047,8 +1051,14 @@ def _compile(
                 not isinstance(expression, ast.Call)
                 or not isinstance(expression.func, ast.Name)
                 or expression.func.id.startswith("__")
-                or expression.args
+                or len(expression.args) > 1
                 or expression.keywords
+                or any(
+                    not isinstance(argument, ast.Constant)
+                    or type(argument.value)
+                    not in (type(None), bool, int, str)
+                    for argument in expression.args
                 )
             ):
                 return None

@@ -1056,6 +1066,10 @@ def _compile(
                 _Step(
                     "CALL_FUNCTION",
                     target=expression.func.id,
+                    call_argument_values=tuple(
+                        argument.value
+                        for argument in expression.args
+                    ),
                 )
             )

@@ -1907,6 +1921,7 @@ def evaluate_package_import_order(
                 _new_restricted_function(
                     module,
                     step.function_body,
+                    step.parameters,
                 )
             )

@@ -2190,10 +2205,13 @@ def evaluate_package_import_order(
             continue

         elif step.op == "CALL_FUNCTION":
+            local_bindings: dict[str, object | None] = {}
+
             body = _execute_restricted_call(
                 step,
                 module=module,
                 namespaces=namespaces,
+                local_bindings=local_bindings,
             )

             if body is None:
@@ -2208,7 +2226,14 @@ def evaluate_package_import_order(
             )

             frames[-1] = _advance_frame(frames[-1])
-            frames.append(_FunctionFrame(module, 0, body))
+            frames.append(
+                _FunctionFrame(
+                    module,
+                    0,
+                    body,
+                    local_bindings,
+                )
             continue

         elif step.op == "BIND":
```

### tests/test_cycle_semantics_single_positional_binding.py

```diff
diff --git a/tests/test_cycle_semantics_single_positional_binding.py b/tests/test_cycle_semantics_single_positional_binding.py
new file mode 100644
index 0000000..d3fee70
--- /dev/null
+++ b/tests/test_cycle_semantics_single_positional_binding.py
@@ -0,0 +1,201 @@
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
+from contextor.core.cycle_semantics.execution.state import _FunctionFrame
+from contextor.core.cycle_semantics.execution.steps import _Step
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+from test_cycle_semantics_decorator_import_effect_baseline import RUNNER
+
+
+CASES = [
+    pytest.param(
+        "def f(x):\n    import pkg.child\nf(7)\n",
+        None,
+        ("pkg.child",),
+        "MODEL_PASS",
+        id="required-argument-import",
+    ),
+    pytest.param(
+        "def f(x):\n    import pkg.child\ng = f\ng(7)\n",
+        None,
+        ("pkg.child",),
+        "MODEL_PASS",
+        id="alias-preserves-parameter-signature",
+    ),
+    pytest.param(
+        "def f(x):\n    import pkg.child\n    return\n    import pkg.after\nf(7)\n",
+        None,
+        ("pkg.child",),
+        "MODEL_PASS",
+        id="argument-with-bare-return",
+    ),
+    pytest.param(
+        "def f(x):\n    import pkg.child\nf()\n",
+        "TypeError",
+        (),
+        "UNKNOWN",
+        id="missing-argument",
+    ),
+    pytest.param(
+        "def f():\n    import pkg.child\nf(7)\n",
+        "TypeError",
+        (),
+        "UNKNOWN",
+        id="excess-argument",
+    ),
+    pytest.param(
+        "def f(x):\n    import pkg.child\nf(7, 8)\n",
+        "TypeError",
+        (),
+        "UNKNOWN",
+        id="two-arguments-unsupported",
+    ),
+]
+
+
+@pytest.mark.parametrize(
+    "source,expected_error,expected_imports,expected_outcome",
+    CASES,
+)
+def test_single_positional_binding_matches_cpython(
+    tmp_path,
+    source,
+    expected_error,
+    expected_imports,
+    expected_outcome,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+    for child in ("child", "after"):
+        (package / f"{child}.py").write_text("pass\n", encoding="utf-8")
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
+    result = evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
+            "pkg.child": ast.parse("pass\n"),
+            "pkg.after": ast.parse("pass\n"),
+        },
+        "pkg",
+    )
+    assert result.outcome == expected_outcome
+    imported = [
+        event.target
+        for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target in {"pkg.child", "pkg.after"}
+    ]
+    if expected_outcome == "MODEL_PASS":
+        assert imported == list(expected_imports)
+    else:
+        assert imported == []
+        assert not any(
+            event.operation == "CALL_FUNCTION"
+            for event in result.events
+        )
+
+
+def test_argument_is_bound_in_new_frame():
+    body = (_Step("RETURN_FUNCTION"),)
+    function = _new_restricted_function("pkg", body, ("x",))
+    namespaces = {"pkg": {"f": function}}
+    local_bindings = {}
+    returned = _execute_restricted_call(
+        _Step("CALL_FUNCTION", target="f", call_argument_values=(7,)),
+        module="pkg",
+        namespaces=namespaces,
+        local_bindings=local_bindings,
+    )
+    frame = _FunctionFrame("pkg", 0, returned, local_bindings)
+    assert returned is body
+    assert frame.local_bindings == {"x": 7}
+    assert frame.local_bindings is local_bindings
+
+
+def test_two_calls_have_independent_local_bindings():
+    function = _new_restricted_function("pkg", (), ("x",))
+    namespaces = {"pkg": {"f": function}}
+    first = {}
+    second = {}
+    for value, bindings in ((7, first), (8, second)):
+        assert _execute_restricted_call(
+            _Step("CALL_FUNCTION", target="f", call_argument_values=(value,)),
+            module="pkg",
+            namespaces=namespaces,
+            local_bindings=bindings,
+        ) == ()
+    assert first == {"x": 7}
+    assert second == {"x": 8}
+    assert first is not second
+
+
+def test_wrong_arity_does_not_bind():
+    function = _new_restricted_function("pkg", (), ("x",))
+    bindings = {}
+    assert _execute_restricted_call(
+        _Step("CALL_FUNCTION", target="f"),
+        module="pkg",
+        namespaces={"pkg": {"f": function}},
+        local_bindings=bindings,
+    ) is None
+    assert bindings == {}
+
+
+def test_alias_preserves_signature():
+    function = _new_restricted_function("pkg", (), ("x",))
+    bindings = {}
+    assert _execute_restricted_call(
+        _Step("CALL_FUNCTION", target="g", call_argument_values=(7,)),
+        module="pkg",
+        namespaces={"pkg": {"f": function, "g": function}},
+        local_bindings=bindings,
+    ) == ()
+    assert bindings == {"x": 7}
+
+
+def test_no_argument_function_still_works():
+    function = _new_restricted_function("pkg", ())
+    bindings = {}
+    assert _execute_restricted_call(
+        _Step("CALL_FUNCTION", target="f"),
+        module="pkg",
+        namespaces={"pkg": {"f": function}},
+        local_bindings=bindings,
+    ) == ()
+    assert bindings == {}
+
+
+def test_foreign_function_is_not_executed():
+    function = _new_restricted_function("other", (), ("x",))
+    bindings = {}
+    assert _execute_restricted_call(
+        _Step("CALL_FUNCTION", target="f", call_argument_values=(7,)),
+        module="pkg",
+        namespaces={"pkg": {"f": function}},
+        local_bindings=bindings,
+    ) is None
+    assert bindings == {}
```

## FINAL_VERDICT

CONTRACT_PROVED for the six stated CPython import-effect cases and the focused helper contracts. The bounded extension passed all requested focused tests. Canonical LIVE source is fresh; `cycle_semantics` remains stale, so no fresh warning or runtime-safety classification is claimed. STOP after this stage.
