# P5-M08-I8-I2-R1 — regression STOP

## PREFLIGHT

Accepted prior preflight. At continuation: HEAD `48dbe14cb2b41c52e61aad81a4e3be41f644b584`, clean source tree, CPython 3.15.2. Exact source anchors unchanged.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/calls.py`
- `contextor/core/cycle_semantics/execution/steps.py`
- `contextor/core/cycle_semantics/execution/state.py`
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_stacked_decorator_execution.py`
- `tests/test_cycle_semantics_stacked_decorator_identity.py`
- `tests/test_cycle_semantics_decorator_import_effect_baseline.py`

## SNAPSHOT_APPLICATION_ORDER

CODE_PATH_PROVED: the new stacked branch snapshots decorator references before application, then reverses the captured pair order. It never rescans namespace names. Each next decorator receives the previous return object through a separate frame.

## FUNCTION_FRAME_CONTINUATION

CODE_PATH_PROVED: return and natural completion both continue through `remaining_decorators`; ordinary `result_binding` path is retained. The module caller is advanced once before the first decorator. The 10000-step budget is unchanged.

## INTERMEDIATE_VALUE_TRANSPORT

CODE_PATH_PROVED: `returned_value` is passed by object identity. Natural completion passes `None`.

## FINAL_BINDING_CONTRACT

CODE_PATH_PROVED: the stacked branch does not write `namespaces[module][step.binding]`; the last continuation writes final binding. This is code path evidence only; targeted regressions failed.

## CPYTHON_PARITY_MATRIX

The nine new cases A–I and six identity cases passed their assertions in the targeted run, including isolated CPython checks. No separate broad semantic parity claim follows. The two failures below occurred in pre-existing baselines. CPython observations for failing baseline cases were asserted successfully before model assertion:
- `multiple-decorators`: `{"error": null, "imports": []}`.
- `stacked-decorator-import-order`: `{"error": null, "imports": ["pkg.lower", "pkg.upper"]}`.

## NEGATIVE_ARITY_AND_REBINDING

New D/F/I tests passed in the targeted run. UNKNOWN is not CPython parity.

## UPDATED_BASELINES

`stacked_decorator_identity.py` updated for six outcomes; its six tests passed. `decorator_import_effect_baseline.py` changed the specified stacked expectation to MODEL_PASS; this failed because that unchanged fixture names decorator functions `upper` and `lower` and direct child modules `pkg.upper` and `pkg.lower`. The existing child-name guard returns UNKNOWN before any events. The R1 correction changed only G/H/I, so this old baseline conflict persists.

A second existing baseline `test_cycle_semantics_named_function_decorators.py::... [multiple-decorators]` expects UNKNOWN and zero calls. The new model returns MODEL_PASS with two identity calls. That test file is outside the authorized edit set. No assertion was weakened.

## TARGETED_TEST_RESULTS

Exact specified command: `2 failed, 310 passed, 2 warnings in 48.41s`.

Failure 1: `test_named_function_decorator_cpython_and_model[multiple-decorators]`, `tests/test_cycle_semantics_named_function_decorators.py:100`. Expected UNKNOWN, actual MODEL_PASS. Full model event sequence:
```json
[{"module":"\u0000ENTRY","operation":"START_IMPORT","target":"pkg","symbol":null},{"module":"pkg","operation":"DEFINE_FUNCTION","target":null,"symbol":"identity"},{"module":"pkg","operation":"DEFINE_FUNCTION","target":null,"symbol":"f"},{"module":"pkg","operation":"CALL_FUNCTION","target":null,"symbol":"identity"},{"module":"pkg","operation":"CALL_FUNCTION","target":null,"symbol":"identity"},{"module":"pkg","operation":"READY","target":null,"symbol":null}]
```

Failure 2: `test_minimal_decorator_import_effects[stacked-decorator-import-order]`, `tests/test_cycle_semantics_decorator_import_effect_baseline.py:186`. Expected MODEL_PASS, actual UNKNOWN. Full model event sequence: `[]`. Relevant source anchors: `package_model.py:1573-1584`, `:1674-1685` before the patch; both package child-name guards retained and extended for DEFINE_STACKED_FUNCTION.

Pytest tracebacks: both failures are AssertionError at the respective `assert result.outcome == expected...`; actual/expected values above. No production exception occurred.

`git diff --check`: exit 0. Git printed only LF/CRLF conversion warnings.

## MCP_POST_CHANGE_AUDIT

NOT RUN: original section 15 authorizes it only after PASS. No FULL, update_file, semantic refresh or restart. LIVE source adoption and revision after edits remain UNKNOWN.

## FULL_DIFFS

```diff
warning: in the working copy of 'contextor/core/cycle_semantics/execution/calls.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/cycle_semantics/execution/state.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/cycle_semantics/execution/steps.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_cycle_semantics_decorator_import_effect_baseline.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_cycle_semantics_stacked_decorator_identity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index 840c919..8f7db99 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -81,3 +81,21 @@ def _execute_restricted_call(
     )
 
     return value.body
+
+
+def _execute_restricted_object_call(
+    value: object,
+    argument: object,
+    *,
+    module: str,
+    local_bindings: dict[str, object | None],
+) -> tuple[_Step, ...] | None:
+    if (
+        not isinstance(value, _RestrictedFunction)
+        or value.defining_module != module
+        or len(value.parameters) != 1
+    ):
+        return None
+
+    local_bindings[value.parameters[0]] = argument
+    return value.body
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index 7fd4221..9b52250 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -39,6 +39,10 @@ class _FunctionFrame:
         repr=False,
     )
     result_binding: str | None = None
+    decorator_final_binding: str | None = None
+    remaining_decorators: tuple[
+        tuple[str, object], ...
+    ] = ()
 
 
 def _frame_module(
@@ -67,6 +71,8 @@ def _advance_frame(
             frame.steps,
             frame.local_bindings,
             frame.result_binding,
+            frame.decorator_final_binding,
+            frame.remaining_decorators,
         )
     return (frame[0], frame[1] + 1)
 
diff --git a/contextor/core/cycle_semantics/execution/steps.py b/contextor/core/cycle_semantics/execution/steps.py
index 2d92617..1288c81 100644
--- a/contextor/core/cycle_semantics/execution/steps.py
+++ b/contextor/core/cycle_semantics/execution/steps.py
@@ -24,3 +24,4 @@ class _Step:
     parameters: tuple[str, ...] = ()
     call_argument_values: tuple[object, ...] = ()
     call_argument_name: str | None = None
+    decorator_names: tuple[str, ...] = ()
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index af766cc..f914265 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -64,7 +64,9 @@ from .execution.lifecycle import (
 )
 from .execution.calls import (
     _execute_restricted_call,
+    _execute_restricted_object_call,
     _new_restricted_function,
+    _snapshot_named_decorators,
 )
 
 
@@ -171,9 +173,12 @@ def _safe_passive_function_definition(
             )
             and not (
                 allow_restricted_decorator
-                and len(statement.decorator_list) == 1
-                and type(statement.decorator_list[0]) is ast.Name
-                and not statement.decorator_list[0].id.startswith("__")
+                and bool(statement.decorator_list)
+                and all(
+                    type(decorator) is ast.Name
+                    and not decorator.id.startswith("__")
+                    for decorator in statement.decorator_list
+                )
             )
         )
         or (statement.returns is not None and annotation_semantics not in {
@@ -1097,9 +1102,13 @@ def _compile(
                 steps.append(
                     _Step(
                         (
-                            "DEFINE_DECORATED_FUNCTION"
-                            if stmt.decorator_list
-                            else "DEFINE_FUNCTION"
+                            "DEFINE_STACKED_FUNCTION"
+                            if len(stmt.decorator_list) > 1
+                            else (
+                                "DEFINE_DECORATED_FUNCTION"
+                                if stmt.decorator_list
+                                else "DEFINE_FUNCTION"
+                            )
                         ),
                         target=(
                             stmt.decorator_list[0].id
@@ -1112,6 +1121,10 @@ def _compile(
                             parameter.arg
                             for parameter in args.args
                         ),
+                        decorator_names=tuple(
+                            decorator.id
+                            for decorator in stmt.decorator_list
+                        ) if len(stmt.decorator_list) > 1 else (),
                     )
                 )
             else:
@@ -1574,6 +1587,7 @@ def evaluate_package_import_order(
             step.op in {
                 "DEFINE_FUNCTION",
                 "DEFINE_DECORATED_FUNCTION",
+                "DEFINE_STACKED_FUNCTION",
                 "DEFINE_OPAQUE_FUNCTION",
                 "DEFINE_PASSIVE_CLASS",
                 "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
@@ -1675,6 +1689,7 @@ def evaluate_package_import_order(
                     step.op in {
                         "DEFINE_FUNCTION",
                         "DEFINE_DECORATED_FUNCTION",
+                        "DEFINE_STACKED_FUNCTION",
                         "DEFINE_OPAQUE_FUNCTION",
                         "DEFINE_PASSIVE_CLASS",
                         "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
@@ -1721,6 +1736,55 @@ def evaluate_package_import_order(
 
         if index >= len(steps):
             if isinstance(active_frame, _FunctionFrame):
+                if active_frame.decorator_final_binding is not None:
+                    frames.pop()
+                    execution_cursor.step_budget += 1
+
+                    if active_frame.remaining_decorators:
+                        next_name, next_object = (
+                            active_frame.remaining_decorators[0]
+                        )
+                        next_locals: dict[str, object | None] = {}
+
+                        next_body = _execute_restricted_object_call(
+                            next_object,
+                            None,
+                            module=module,
+                            local_bindings=next_locals,
+                        )
+
+                        if next_body is None:
+                            return result("UNKNOWN", module, next_name)
+
+                        events.append(
+                            PackageModelEvent(
+                                module,
+                                "CALL_FUNCTION",
+                                symbol=next_name,
+                            )
+                        )
+
+                        frames.append(
+                            _FunctionFrame(
+                                module=module,
+                                index=0,
+                                steps=next_body,
+                                local_bindings=next_locals,
+                                decorator_final_binding=(
+                                    active_frame.decorator_final_binding
+                                ),
+                                remaining_decorators=(
+                                    active_frame.remaining_decorators[1:]
+                                ),
+                            )
+                        )
+                    else:
+                        namespaces[module][
+                            active_frame.decorator_final_binding
+                        ] = None
+
+                    continue
+
                 if active_frame.result_binding is not None:
                     namespaces[module][active_frame.result_binding] = None
                 frames.pop()
@@ -2025,6 +2089,77 @@ def evaluate_package_import_order(
                     )
                 )
 
+        elif step.op == "DEFINE_STACKED_FUNCTION":
+            if (
+                not step.binding
+                or len(step.decorator_names) < 2
+            ):
+                return result("UNKNOWN", module)
+
+            snapshot = _snapshot_named_decorators(
+                step.decorator_names,
+                namespaces[module],
+            )
+
+            if snapshot is None:
+                return result("UNKNOWN", module)
+
+            decorated_function = _new_restricted_function(
+                module,
+                step.function_body,
+                step.parameters,
+            )
+
+            application_order = tuple(
+                reversed(
+                    tuple(
+                        zip(snapshot.names, snapshot.values)
+                    )
+                )
+            )
+
+            first_name, first_object = application_order[0]
+            local_bindings: dict[str, object | None] = {}
+
+            body = _execute_restricted_object_call(
+                first_object,
+                decorated_function,
+                module=module,
+                local_bindings=local_bindings,
+            )
+
+            if body is None:
+                return result("UNKNOWN", module, first_name)
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "DEFINE_FUNCTION",
+                    symbol=step.binding,
+                )
+            )
+
+            events.append(
+                PackageModelEvent(
+                    module,
+                    "CALL_FUNCTION",
+                    symbol=first_name,
+                )
+            )
+
+            frames[-1] = _advance_frame(frames[-1])
+            frames.append(
+                _FunctionFrame(
+                    module=module,
+                    index=0,
+                    steps=body,
+                    local_bindings=local_bindings,
+                    decorator_final_binding=step.binding,
+                    remaining_decorators=application_order[1:],
+                )
+            )
+            continue
+
         elif step.op == "DEFINE_DECORATED_FUNCTION":
             if (
                 not step.target
@@ -2377,6 +2512,52 @@ def evaluate_package_import_order(
 
             frames.pop()
 
+            if active_frame.decorator_final_binding is not None:
+                if active_frame.remaining_decorators:
+                    next_name, next_object = (
+                        active_frame.remaining_decorators[0]
+                    )
+                    next_locals: dict[str, object | None] = {}
+
+                    next_body = _execute_restricted_object_call(
+                        next_object,
+                        returned_value,
+                        module=module,
+                        local_bindings=next_locals,
+                    )
+
+                    if next_body is None:
+                        return result("UNKNOWN", module, next_name)
+
+                    events.append(
+                        PackageModelEvent(
+                            module,
+                            "CALL_FUNCTION",
+                            symbol=next_name,
+                        )
+                    )
+
+                    frames.append(
+                        _FunctionFrame(
+                            module=module,
+                            index=0,
+                            steps=next_body,
+                            local_bindings=next_locals,
+                            decorator_final_binding=(
+                                active_frame.decorator_final_binding
+                            ),
+                            remaining_decorators=(
+                                active_frame.remaining_decorators[1:]
+                            ),
+                        )
+                    )
+                else:
+                    namespaces[module][
+                        active_frame.decorator_final_binding
+                    ] = returned_value
+
+                continue
+
             if result_binding is not None:
                 namespaces[module][result_binding] = returned_value
 
diff --git a/tests/test_cycle_semantics_decorator_import_effect_baseline.py b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
index 4027548..9942d25 100644
--- a/tests/test_cycle_semantics_decorator_import_effect_baseline.py
+++ b/tests/test_cycle_semantics_decorator_import_effect_baseline.py
@@ -52,7 +52,7 @@ CASES = [
             "    pass\n"
         ),
         ("pkg.lower", "pkg.upper"),
-        "UNKNOWN",
+        "MODEL_PASS",
         id="stacked-decorator-import-order",
     ),
     pytest.param(
diff --git a/tests/test_cycle_semantics_stacked_decorator_identity.py b/tests/test_cycle_semantics_stacked_decorator_identity.py
index 85c71d3..55010cb 100644
--- a/tests/test_cycle_semantics_stacked_decorator_identity.py
+++ b/tests/test_cycle_semantics_stacked_decorator_identity.py
@@ -28,6 +28,7 @@ CASES = [
         ),
         None,
         ("pkg.bottom", "pkg.top"),
+        "MODEL_PASS",
         id="bottom-up-application",
     ),
     pytest.param(
@@ -42,6 +43,7 @@ CASES = [
         ),
         None,
         ("pkg.child", "pkg.child"),
+        "MODEL_PASS",
         id="same-decorator-called-twice",
     ),
     pytest.param(
@@ -61,6 +63,7 @@ CASES = [
         ),
         None,
         ("pkg.bottom", "pkg.top"),
+        "UNKNOWN",
         id="upper-binding-replaced-after-evaluation",
     ),
     pytest.param(
@@ -77,6 +80,7 @@ CASES = [
         ),
         None,
         ("pkg.top",),
+        "MODEL_PASS",
         id="none-intermediate-value",
     ),
     pytest.param(
@@ -94,6 +98,7 @@ CASES = [
         ),
         "TypeError",
         ("pkg.bottom",),
+        "UNKNOWN",
         id="upper-wrong-arity-after-lower-effect",
     ),
     pytest.param(
@@ -112,13 +117,14 @@ CASES = [
         ),
         None,
         ("pkg.bottom", "pkg.top", "pkg.child"),
+        "MODEL_PASS",
         id="decorated-body-executed-last",
     ),
 ]
 
 
 @pytest.mark.parametrize(
-    "source,expected_error,expected_imports",
+    "source,expected_error,expected_imports,expected_model_outcome",
     CASES,
 )
 def test_stacked_decorator_cpython_and_current_boundary(
@@ -126,6 +132,7 @@ def test_stacked_decorator_cpython_and_current_boundary(
     source,
     expected_error,
     expected_imports,
+    expected_model_outcome,
 ):
     package = tmp_path / "pkg"
     package.mkdir()
@@ -177,10 +184,13 @@ def test_stacked_decorator_cpython_and_current_boundary(
         "pkg",
     )
 
-    assert result.outcome == "UNKNOWN"
+    assert result.outcome == expected_model_outcome
 
-    assert not any(
-        event.operation == "CALL_FUNCTION"
-        and event.symbol in {"upper", "lower", "deco"}
-        for event in result.events
-    )
+    if expected_model_outcome == "MODEL_PASS":
+        actual_starts = tuple(
+            event.target for event in result.events
+            if event.operation == "START_IMPORT"
+            and event.target is not None
+            and event.target.startswith("pkg.")
+        )
+        assert actual_starts == tuple(dict.fromkeys(expected_imports))
diff --git a/tests/test_cycle_semantics_stacked_decorator_execution.py b/tests/test_cycle_semantics_stacked_decorator_execution.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_stacked_decorator_execution.py
@@ -0,0 +1,107 @@
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
+from test_cycle_semantics_stacked_decorator_identity import CASES
+
+
+THREE_PASS = (
+    "def top_decorator(fn):\n"
+    "    import pkg.a\n"
+    "    return fn\n"
+    "def middle_decorator(fn):\n"
+    "    import pkg.b\n"
+    "    return fn\n"
+    "def bottom_decorator(fn):\n"
+    "    import pkg.c\n"
+    "    return fn\n"
+    "@top_decorator\n"
+    "@middle_decorator\n"
+    "@bottom_decorator\n"
+    "def f():\n"
+    "    pass\n"
+)
+
+MIDDLE_NONE = (
+    "def top_decorator(fn):\n"
+    "    import pkg.a\n"
+    "    return fn\n"
+    "def middle_decorator(fn):\n"
+    "    return\n"
+    "def bottom_decorator(fn):\n"
+    "    import pkg.c\n"
+    "    return fn\n"
+    "@top_decorator\n"
+    "@middle_decorator\n"
+    "@bottom_decorator\n"
+    "def f():\n"
+    "    pass\n"
+)
+
+
+@pytest.mark.parametrize(
+    "source,error,imports,outcome,calls,starts",
+    [
+        pytest.param(CASES[0].values[0], None, ("pkg.bottom", "pkg.top"), "MODEL_PASS", ("lower", "upper"), ("pkg.bottom", "pkg.top"), id="A-bottom-up"),
+        pytest.param(CASES[1].values[0], None, ("pkg.child", "pkg.child"), "MODEL_PASS", ("deco", "deco"), ("pkg.child",), id="B-repeated"),
+        pytest.param(CASES[3].values[0], None, ("pkg.top",), "MODEL_PASS", ("lower", "upper"), ("pkg.top",), id="C-intermediate-none"),
+        pytest.param(CASES[4].values[0], "TypeError", ("pkg.bottom",), "UNKNOWN", ("lower",), ("pkg.bottom",), id="D-wrong-arity"),
+        pytest.param(CASES[5].values[0], None, ("pkg.bottom", "pkg.top", "pkg.child"), "MODEL_PASS", ("lower", "upper", "f"), ("pkg.bottom", "pkg.top", "pkg.child"), id="E-deferred-body"),
+        pytest.param(CASES[2].values[0], None, ("pkg.bottom", "pkg.top"), "UNKNOWN", (), (), id="F-global-rebinding"),
+        pytest.param(THREE_PASS, None, ("pkg.c", "pkg.b", "pkg.a"), "MODEL_PASS", ("bottom_decorator", "middle_decorator", "top_decorator"), ("pkg.c", "pkg.b", "pkg.a"), id="G-three-pass-through"),
+        pytest.param(MIDDLE_NONE, None, ("pkg.c", "pkg.a"), "MODEL_PASS", ("bottom_decorator", "middle_decorator", "top_decorator"), ("pkg.c", "pkg.a"), id="H-middle-none"),
+        pytest.param(MIDDLE_NONE + "f()\n", "TypeError", ("pkg.c", "pkg.a"), "UNKNOWN", ("bottom_decorator", "middle_decorator", "top_decorator"), ("pkg.c", "pkg.a"), id="I-final-none-called"),
+    ],
+)
+def test_stacked_decorator_execution(
+    tmp_path, source, error, imports, outcome, calls, starts,
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    (package / "__init__.py").write_text(source, encoding="utf-8")
+
+    child_names = ("top", "bottom", "child", "a", "b", "c")
+    sources = {"pkg.__init__": ast.parse(source)}
+    for name in child_names:
+        (package / f"{name}.py").write_text("pass\n", encoding="utf-8")
+        sources[f"pkg.{name}"] = ast.parse("pass\n")
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
+    assert observed == {"error": error, "imports": list(imports)}
+
+    result = evaluate_package_import_order(sources, "pkg")
+    assert result.outcome == outcome
+    actual_calls = tuple(
+        event.symbol for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    )
+    assert actual_calls == calls
+    actual_starts = tuple(
+        event.target for event in result.events
+        if event.operation == "START_IMPORT"
+        and event.target is not None
+        and event.target.startswith("pkg.")
+    )
+    assert actual_starts == starts
+
+    if source == CASES[1].values[0]:
+        assert sum(
+            event.operation == "FUNCTION_LOCAL_IMPORT"
+            and event.target == "pkg.child"
+            for event in result.events
+        ) == 2
```

## FINAL_VERDICT

REGRESSION_FAILURE / BLOCKED_SEMANTIC_INTEGRITY. FINAL PASS denied. Per failure contract, no independent repair or further tests. Corrective specification must resolve both existing baseline conflicts while preserving the child-name guards and authorization boundary.
