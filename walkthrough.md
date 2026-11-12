# P5-M08-I10-I2 — SINGLE INDEXED CROSS-MODULE FUNCTION DECORATOR

## PREFLIGHT

- **DIRECT_EVIDENCE:** HEAD `ae8bef1ee1717cd8d6105be5d4e3f92ee9719b33`; `git status --short` was empty before changes.
- **DIRECT_EVIDENCE:** Contextor canonical LIVE revision `1374`, provenance `live`, `canonical_state=fresh`, target `workspace_sync=verified`; `cycle_semantics` family was `stale`, advisory warning `null`.
- **DIRECT_EVIDENCE:** active interpreter `.venv\Scripts\python.exe` is CPython `3.15.2`.
- **CODE_PATH_PROVED:** I10-I1 is present: `_FunctionFrame.binding_module` at `execution/state.py:46`; `_advance_frame` propagation at `execution/state.py:65-78`; decorator continuation and return destination writes at `package_model.py:2649-2720`.
- **CODE_PATH_PROVED:** source before the change showed the authorized `DEFINE_DECORATED_FUNCTION` branch at `package_model.py:2226-2305`; `_execute_restricted_call` and `_execute_restricted_object_call` remain guarded in `execution/calls.py:60-101`.
- **CODE_PATH_PROVED:** current evaluation builds `logical_sources` and `programs` for valid indexed modules in `package_model.py:1528-1622`.
- **INFERENCE:** the `binding_module` mechanism can preserve caller-side final binding while a frame carries the defining module, subject to the failed first gate below.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_cross_module_single_decorator.py` (new)
- `tests/test_cycle_semantics_cross_module_decorator_baseline.py`
- `tests/test_cycle_semantics_function_frame_result_owner.py`
- `walkthrough.md` (this report; excluded from source/test diff accounting)

## SINGLE_DECORATOR_ADMISSION

- The only production edit is inside `DEFINE_DECORATED_FUNCTION`.
- The attempted branch snapshots `namespaces[module][step.target]`, preserves the same-module `_execute_restricted_call` path, and restricts the foreign path to an indexed `_RestrictedFunction` with one parameter.
- **DIRECT_EVIDENCE / BLOCKER:** execution raised `NameError: name '_RestrictedFunction' is not defined` at `package_model.py:2250`. The branch did not produce a `PackageImportAssessment`; do not infer `UNKNOWN` or `MODEL_PASS` from this exception.
- No correction was made after the failure, per the task's first-gate STOP contract.

## EXACT_IMPORTED_OBJECT_IDENTITY

- The foreign path passes the captured namespace object directly to `_execute_restricted_object_call`; it does not perform a second name lookup.
- **UNKNOWN:** the intended identity-preserving behavior did not reach an evaluator result because the gate raised the `NameError` before the foreign path could be exercised.

## DEFINING_MODULE_EXECUTION

- The attempted frame uses `decorator_value.defining_module`; the object-call helper's unchanged contract requires exact `_RestrictedFunction` type, matching defining module, and one parameter (`execution/calls.py:80-101`).
- **UNKNOWN:** function-body event attribution and body execution were not established by the failed gate.

## APPLYING_MODULE_RESULT_BINDING

- The attempted foreign frame sets `binding_module` to the applying module and leaves namespace assignment to the existing return/natural-completion paths (`package_model.py:2653-2720`).
- **UNKNOWN:** no model result was returned, so final binding destination and absence of early binding are not claimed as tested.

## INDEXED_IMPORT_EFFECT_ATTRIBUTION

- New positive fixtures assert imported decorator calls are attributed to `pkg.app` and function-local import events to `pkg.decorators`.
- **UNKNOWN:** no event tuple was produced for the failing evaluator calls; attribution has not passed verification.

## IMPORTED_ALIAS

- The test fixture covers `from pkg.decorators import identity as alias`, CPython identity, one decorator call, and a subsequent call of `f`.
- **DIRECT_EVIDENCE:** the captured CPython 3.15.2 A fixture completed import, loaded `pkg.decorators`, retained a callable function identical to the decorator input, and observed exactly one decorator call.
- **UNKNOWN:** model parity for alias C did not complete because of the same evaluator `NameError`.

## RETURN_NONE

- The test fixture distinguishes bare `return` from the existing explicit `return None` unsupported baseline, checks definition-only success, and checks a later `f()` remains UNKNOWN.
- **UNKNOWN:** its evaluator assertions did not pass the first gate; no binding claim is made.

## RELATIVE_IMPORT_CONTEXT

- The new package-shaped G fixture uses `pkg.decorators.__init__`, a relative import of `pkg.decorators.effect`, and a distinct `pkg.effect` distractor.
- The isolated CPython A trace passed. No per-case G CPython output was retained in the truncated pytest response, so no G observation is asserted here.
- **UNKNOWN:** model import target and defining-package attribution were not validated.

## UNSUPPORTED_GLOBALS

- Negative fixtures cover an imported decorator with a global-variable expression and a nested unsupported call. The intended assertions preserve UNKNOWN and reject generic nested-call execution.
- **UNKNOWN:** these negative evaluator results are not certified by the failed gate.

## UNCHANGED_STACK_AND_CLASS_BOUNDARIES

- The source edit does not touch `DEFINE_STACKED_FUNCTION` or `DEFINE_DECORATED_PASSIVE_CLASS`; tests retain UNKNOWN expectations for cross-module stacks and class decorators.
- **DIRECT_EVIDENCE:** source diff is confined to `DEFINE_DECORATED_FUNCTION`; full exact diff follows.

## UNCHANGED_EXTERNAL_IMPORT_POLICY

- No external import classification or `lru_cache` handling was changed. The new L fixture retains the existing UNKNOWN boundary.

## CPYTHON_PARITY_MATRIX

| Case | CPython evidence captured | Model evidence |
|---|---|---|
| A imported identity | CPython 3.15.2 assertions passed before model evaluation: import succeeded; `pkg.decorators` import; callable binding identical to decorator input; one decorator call; no effect module. | No result; `NameError` at `package_model.py:2250`. |
| B indexed effect | Not independently transcribed from captured output. | No result; same exception. |
| C imported alias | Not independently transcribed from captured output. | No result; same exception. |
| D bare return | Not independently transcribed from captured output. | No result; same exception. |
| G relative import | Not independently transcribed from captured output. | No result; same exception. |

## TARGETED_TEST_RESULTS

- First required gate command:
  `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_function_frame_result_owner.py -rs`
- **DIRECT_EVIDENCE:** `17 failed, 18 passed in 16.21s` (pytest exit code `1`).
- Representative traceback: `test_indexed_single_decorator_matches_cpython_and_binds_result[A-imported-identity]` reached `_model(sources)` after its CPython assertions, then raised `NameError: name '_RestrictedFunction' is not defined` at `contextor/core/cycle_semantics/package_model.py:2250`.
- **UNKNOWN:** the unhandled exception prevented a `PackageImportAssessment`; complete model event lists are unavailable for these failures.
- The regression subset was not run because the first gate failed.
- `git diff --check` passed before the final gate, before the last small test-assertion amendment. It was not rerun after the gate because the task requires STOP at this failure.

## MCP_POST_CHANGE_AUDIT

- Not run. The task permits this audit only after the first gate and regression subset pass; the first gate failed.
- No FULL, SCC02, full pytest, `update_file`, backend restart, semantic refresh, Git index mutation, or history mutation was performed.

## FULL_DIFFS

Complete working-tree diff for all changed source/test files relative to HEAD. `walkthrough.md` is this report and is excluded from diff accounting.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index b90315c..efc02c9 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -2241,13 +2241,38 @@ def evaluate_package_import_order(
                 target=step.target,
                 call_argument_values=(decorated_function,),
             )
+            decorator_value = namespaces[module][step.target]
             local_bindings: dict[str, object | None] = {}
-            body = _execute_restricted_call(
-                decorator_call,
-                module=module,
-                namespaces=namespaces,
-                local_bindings=local_bindings,
-            )
+            function_module = module
+            binding_module = None
+
+            if (
+                isinstance(decorator_value, _RestrictedFunction)
+                and decorator_value.defining_module == module
+            ):
+                body = _execute_restricted_call(
+                    decorator_call,
+                    module=module,
+                    namespaces=namespaces,
+                    local_bindings=local_bindings,
+                )
+            elif (
+                isinstance(decorator_value, _RestrictedFunction)
+                and decorator_value.defining_module != module
+                and decorator_value.defining_module in logical_sources
+                and decorator_value.defining_module in programs
+                and len(decorator_value.parameters) == 1
+            ):
+                function_module = decorator_value.defining_module
+                binding_module = module
+                body = _execute_restricted_object_call(
+                    decorator_value,
+                    decorated_function,
+                    module=function_module,
+                    local_bindings=local_bindings,
+                )
+            else:
+                return result("UNKNOWN", module, step.target)
 
             if body is None:
                 return result("UNKNOWN", module, step.target)
@@ -2267,15 +2292,27 @@ def evaluate_package_import_order(
                 )
             )
             frames[-1] = _advance_frame(frames[-1])
-            frames.append(
-                _FunctionFrame(
-                    module,
-                    0,
-                    body,
-                    local_bindings,
-                    step.binding,
+            if binding_module is None:
+                frames.append(
+                    _FunctionFrame(
+                        module,
+                        0,
+                        body,
+                        local_bindings,
+                        step.binding,
+                    )
+                )
+            else:
+                frames.append(
+                    _FunctionFrame(
+                        function_module,
+                        0,
+                        body,
+                        local_bindings,
+                        step.binding,
+                        binding_module=binding_module,
+                    )
                 )
-            )
             continue
 
         elif step.op == "DEFINE_FUNCTION":
diff --git a/tests/test_cycle_semantics_cross_module_decorator_baseline.py b/tests/test_cycle_semantics_cross_module_decorator_baseline.py
index e0ba3ff..f42ee97 100644
--- a/tests/test_cycle_semantics_cross_module_decorator_baseline.py
+++ b/tests/test_cycle_semantics_cross_module_decorator_baseline.py
@@ -431,7 +431,7 @@ def test_indexed_cross_module_decorator_reference_and_model_boundary(
         ),
     ],
 )
-def test_supported_body_imported_decorators_remain_unknown(
+def test_supported_body_imported_decorators_execute_when_supported(
     tmp_path,
     case,
     export_name,
@@ -468,7 +468,7 @@ def test_supported_body_imported_decorators_remain_unknown(
         {name: ast.parse(source) for name, source in sources.items()},
         "pkg.app",
     )
-    assert modeled.outcome == "UNKNOWN"
+    assert modeled.outcome == ("UNKNOWN" if case == "D2" else "MODEL_PASS")
     assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
     assert any(
         event.operation == "FROM"
@@ -477,14 +477,41 @@ def test_supported_body_imported_decorators_remain_unknown(
         and event.symbol == imported_symbol
         for event in modeled.events
     )
-    assert not any(
-        event.operation == "CALL_FUNCTION"
-        for event in modeled.events
-    )
-    assert not any(
-        event.target == "pkg.effect"
+    decorator_calls = tuple(
+        event
         for event in modeled.events
+        if event.operation == "CALL_FUNCTION"
+        and event.symbol == decorator_binding_name
     )
+    if case == "D2":
+        assert decorator_calls == ()
+        assert not any(
+            event.target == "pkg.effect"
+            for event in modeled.events
+        )
+    else:
+        assert len(decorator_calls) == 1
+        assert decorator_calls[0].module == "pkg.app"
+
+        if case == "B2":
+            effect_imports = tuple(
+                event
+                for event in modeled.events
+                if event.operation == "FUNCTION_LOCAL_IMPORT"
+                and event.target == "pkg.effect"
+            )
+            assert len(effect_imports) == 1
+            assert effect_imports[0].module == "pkg.decorators"
+            assert sum(
+                event.operation == "START_IMPORT"
+                and event.target == "pkg.effect"
+                for event in modeled.events
+            ) == 1
+        else:
+            assert not any(
+                event.target == "pkg.effect"
+                for event in modeled.events
+            )
 
 
 def test_cpython_relative_decorator_import_uses_defining_package_context(
@@ -603,7 +630,7 @@ def test_imported_decorator_body_effect_is_not_reported_as_model_execution():
     }
     modeled = evaluate_package_import_order(sources, "pkg.app")
 
-    assert modeled.outcome == "UNKNOWN"
+    assert modeled.outcome == "MODEL_PASS"
     assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
     assert any(
         event.operation == "FROM"
@@ -612,21 +639,30 @@ def test_imported_decorator_body_effect_is_not_reported_as_model_execution():
         and event.symbol == "apply_decorator"
         for event in modeled.events
     )
-    assert not any(
-        event.operation == "CALL_FUNCTION"
-        and event.symbol == "apply_decorator"
+    calls = tuple(
+        event
         for event in modeled.events
+        if event.operation == "CALL_FUNCTION"
+        and event.symbol == "apply_decorator"
     )
-    assert not any(
-        event.operation == "START_IMPORT"
-        and event.target == "pkg.effect"
+    assert len(calls) == 1
+    assert calls[0].module == "pkg.app"
+    starts = tuple(
+        event
         for event in modeled.events
-    )
-    assert not any(
-        event.operation == "FUNCTION_LOCAL_IMPORT"
+        if event.operation == "START_IMPORT"
         and event.target == "pkg.effect"
+    )
+    assert len(starts) == 1
+    local_imports = tuple(
+        event
         for event in modeled.events
+        if event.operation == "FUNCTION_LOCAL_IMPORT"
+        and event.target == "pkg.effect"
     )
+    assert len(local_imports) == 1
+    assert local_imports[0].module == "pkg.decorators"
+    assert modeled.events.index(calls[0]) < modeled.events.index(local_imports[0])
 
 
 def test_external_functools_decorator_remains_unmodeled_without_assumptions():
diff --git a/tests/test_cycle_semantics_function_frame_result_owner.py b/tests/test_cycle_semantics_function_frame_result_owner.py
index 7d255d0..fc6a5b1 100644
--- a/tests/test_cycle_semantics_function_frame_result_owner.py
+++ b/tests/test_cycle_semantics_function_frame_result_owner.py
@@ -163,7 +163,7 @@ def test_stacked_decorators_remain_bottom_to_top_without_duplicates():
     assert calls.count("upper") == 1
 
 
-def test_imported_decorator_remains_unknown_after_from():
+def test_imported_decorator_executes_in_defining_module():
     modeled = _evaluate_sources(
         {
             "pkg.__init__": "pass\n",
@@ -181,7 +181,7 @@ def test_imported_decorator_remains_unknown_after_from():
         "pkg.app",
     )
 
-    assert modeled.outcome == "UNKNOWN"
+    assert modeled.outcome == "MODEL_PASS"
     assert any(
         event.operation == "FROM"
         and event.module == "pkg.app"
@@ -189,11 +189,14 @@ def test_imported_decorator_remains_unknown_after_from():
         and event.symbol == "identity"
         for event in modeled.events
     )
-    assert not any(
-        event.operation == "CALL_FUNCTION"
-        and event.symbol == "identity"
+    calls = tuple(
+        event
         for event in modeled.events
+        if event.operation == "CALL_FUNCTION"
+        and event.symbol == "identity"
     )
+    assert len(calls) == 1
+    assert calls[0].module == "pkg.app"
 
 
 def test_external_functools_decorator_remains_unmodeled():

diff --git a/tests/test_cycle_semantics_cross_module_single_decorator.py b/tests/test_cycle_semantics_cross_module_single_decorator.py
new file mode 100644
index 0000000..e130e2b
--- /dev/null
+++ b/tests/test_cycle_semantics_cross_module_single_decorator.py
@@ -0,0 +1,598 @@
+"""CPython-backed contract for one indexed cross-module decorator."""
+
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
+_REFERENCE_RUNNER = r"""
+import builtins
+import importlib
+import json
+import sys
+
+sys.path.insert(0, sys.argv[1])
+decorator_name = sys.argv[2]
+invoke_after_import = sys.argv[3] == "true"
+imports = []
+decorator_inputs = []
+original_import = builtins.__import__
+
+def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
+    if name in {"pkg.decorators", "pkg.effect"}:
+        imports.append(name)
+    elif (
+        level == 1
+        and globals is not None
+        and globals.get("__package__") == "pkg.decorators"
+        and (name == "effect" or "effect" in fromlist)
+    ):
+        imports.append("pkg.decorators.effect")
+    return original_import(name, globals, locals, fromlist, level)
+
+builtins.__import__ = traced_import
+
+def trace_decorator(frame, event, arg):
+    if (
+        event == "call"
+        and frame.f_globals.get("__name__") == "pkg.decorators"
+        and frame.f_code.co_name == decorator_name
+    ):
+        decorator_inputs.append(frame.f_locals.get("fn"))
+    return trace_decorator
+
+sys.settrace(trace_decorator)
+error = None
+try:
+    app = importlib.import_module("pkg.app")
+except BaseException as exc:
+    app = sys.modules.get("pkg.app")
+    error = {"type": type(exc).__name__, "message": str(exc)}
+finally:
+    sys.settrace(None)
+
+binding_present = app is not None and "f" in app.__dict__
+value = app.__dict__.get("f") if binding_present else None
+call_error = None
+if error is None and invoke_after_import:
+    try:
+        value()
+    except BaseException as exc:
+        call_error = {"type": type(exc).__name__, "message": str(exc)}
+
+seen = decorator_inputs[0] if decorator_inputs else None
+print(json.dumps({
+    "python": list(sys.version_info[:3]),
+    "error": error,
+    "call_error": call_error,
+    "imports": imports,
+    "binding_present": binding_present,
+    "binding_type": (
+        type(value).__module__ + "." + type(value).__qualname__
+        if binding_present else None
+    ),
+    "binding_callable": callable(value) if binding_present else False,
+    "binding_is_decorator_input": binding_present and value is seen,
+    "decorator_calls": len(decorator_inputs),
+    "loaded_effect_modules": [
+        name
+        for name in ("pkg.effect", "pkg.decorators.effect")
+        if name in sys.modules
+    ],
+}, sort_keys=True))
+"""
+
+
+def _write_sources(root: Path, sources):
+    for module, source in sources.items():
+        parts = module.split(".")
+        directory = root.joinpath(*parts[:-1])
+        filename = "__init__.py" if parts[-1] == "__init__" else parts[-1] + ".py"
+        directory.mkdir(parents=True, exist_ok=True)
+        directory.joinpath(filename).write_text(source, encoding="utf-8")
+
+
+def _cpython_reference(tmp_path, sources, decorator_name, *, invoke=False):
+    _write_sources(tmp_path, sources)
+    completed = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            _REFERENCE_RUNNER,
+            str(tmp_path),
+            decorator_name,
+            "true" if invoke else "false",
+        ],
+        capture_output=True,
+        text=True,
+        timeout=20,
+        check=False,
+    )
+    assert completed.returncode == 0, completed.stderr
+    return json.loads(completed.stdout)
+
+
+def _model(sources):
+    return evaluate_package_import_order(
+        {name: ast.parse(source) for name, source in sources.items()},
+        "pkg.app",
+    )
+
+
+def _events(model, operation):
+    return tuple(
+        event
+        for event in model.events
+        if event.operation == operation
+    )
+
+
+def _single_imported_decorator_contract(model, imported_symbol, decorator_name):
+    assert model.outcome == "MODEL_PASS"
+    assert model.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert any(
+        event.operation == "FROM"
+        and event.module == "pkg.app"
+        and event.target == "pkg.decorators"
+        and event.symbol == imported_symbol
+        for event in model.events
+    )
+    decorator_calls = tuple(
+        event
+        for event in _events(model, "CALL_FUNCTION")
+        if event.symbol == decorator_name
+    )
+    assert len(decorator_calls) == 1
+    assert decorator_calls[0].module == "pkg.app"
+    function_calls = tuple(
+        event
+        for event in _events(model, "CALL_FUNCTION")
+        if event.symbol == "f"
+    )
+    assert len(function_calls) == 1
+    assert function_calls[0].module == "pkg.app"
+    return decorator_calls[0]
+
+
+def _relevant_start_imports(model):
+    relevant = {"pkg.decorators", "pkg.effect", "pkg.decorators.effect"}
+    return tuple(
+        event.target
+        for event in _events(model, "START_IMPORT")
+        if event.target in relevant
+    )
+
+
+@pytest.mark.parametrize(
+    "case,decorator_name,imported_symbol,expected_imports,expected_loaded_effects",
+    [
+        ("A", "identity", "identity", ("pkg.decorators",), ()),
+        (
+            "B",
+            "apply_decorator",
+            "apply_decorator",
+            ("pkg.decorators", "pkg.effect"),
+            ("pkg.effect",),
+        ),
+        ("C", "identity", "identity", ("pkg.decorators",), ()),
+        (
+            "G",
+            "relative_decorator",
+            "relative_decorator",
+            ("pkg.decorators", "pkg.decorators.effect"),
+            ("pkg.decorators.effect",),
+        ),
+    ],
+    ids=["A-imported-identity", "B-indexed-effect", "C-imported-alias", "G-relative-import"],
+)
+def test_indexed_single_decorator_matches_cpython_and_binds_result(
+    tmp_path,
+    case,
+    decorator_name,
+    imported_symbol,
+    expected_imports,
+    expected_loaded_effects,
+):
+    sources = _positive_sources(case)
+    observed = _cpython_reference(tmp_path, sources, decorator_name)
+
+    assert observed["python"] == [3, 15, 2]
+    assert observed["error"] is None
+    assert tuple(observed["imports"]) == expected_imports
+    assert observed["binding_present"] is True
+    assert observed["binding_type"] == "builtins.function"
+    assert observed["binding_callable"] is True
+    assert observed["binding_is_decorator_input"] is True
+    assert observed["decorator_calls"] == 1
+    assert tuple(observed["loaded_effect_modules"]) == expected_loaded_effects
+
+    modeled = _model(sources)
+    decorator_call = _single_imported_decorator_contract(
+        modeled,
+        imported_symbol,
+        decorator_name,
+    )
+    assert _relevant_start_imports(modeled) == expected_imports
+
+    local_imports = _events(modeled, "FUNCTION_LOCAL_IMPORT")
+    if case == "B":
+        effect_import = tuple(
+            event
+            for event in local_imports
+            if event.target == "pkg.effect"
+        )
+        assert len(effect_import) == 1
+        assert effect_import[0].module == "pkg.decorators"
+        starts = _events(modeled, "START_IMPORT")
+        effect_start = next(
+            index
+            for index, event in enumerate(starts)
+            if event.target == "pkg.effect"
+        )
+        assert starts[effect_start].module == "pkg.decorators"
+        assert modeled.events.index(decorator_call) < modeled.events.index(
+            effect_import[0]
+        )
+        assert modeled.events.index(decorator_call) < modeled.events.index(
+            starts[effect_start]
+        )
+    elif case == "G":
+        relative_import = tuple(
+            event
+            for event in local_imports
+            if event.target == "pkg.decorators.effect"
+        )
+        assert len(relative_import) == 1
+        assert relative_import[0].module == "pkg.decorators"
+        assert not any(
+            event.target == "pkg.effect"
+            for event in modeled.events
+            if event.operation in {"START_IMPORT", "FUNCTION_LOCAL_IMPORT"}
+        )
+        assert modeled.events.index(decorator_call) < modeled.events.index(
+            relative_import[0]
+        )
+        relative_start = next(
+            event
+            for event in _events(modeled, "START_IMPORT")
+            if event.target == "pkg.decorators.effect"
+        )
+        assert modeled.events.index(decorator_call) < modeled.events.index(
+            relative_start
+        )
+    else:
+        assert local_imports == ()
+
+    starts = tuple(event.target for event in _events(modeled, "START_IMPORT"))
+    assert len(starts) == len(set(starts))
+    assert set(starts).issubset(
+        {"pkg", "pkg.app", "pkg.decorators", *expected_loaded_effects}
+    )
+
+
+def _positive_sources(case):
+    sources = {"pkg.__init__": "pass\n"}
+    if case == "A":
+        sources.update(
+            {
+                "pkg.decorators": "def identity(fn):\n    return fn\n",
+                "pkg.app": (
+                    "from pkg.decorators import identity\n"
+                    "@identity\n"
+                    "def f():\n"
+                    "    pass\n"
+                    "f()\n"
+                ),
+            }
+        )
+    elif case == "B":
+        sources.update(
+            {
+                "pkg.decorators": (
+                    "def apply_decorator(fn):\n"
+                    "    import pkg.effect\n"
+                    "    return fn\n"
+                ),
+                "pkg.app": (
+                    "from pkg.decorators import apply_decorator\n"
+                    "@apply_decorator\n"
+                    "def f():\n"
+                    "    pass\n"
+                    "f()\n"
+                ),
+                "pkg.effect": "pass\n",
+            }
+        )
+    elif case == "C":
+        sources.update(
+            {
+                "pkg.decorators": "def identity(fn):\n    return fn\n",
+                "pkg.app": (
+                    "from pkg.decorators import identity as alias\n"
+                    "@alias\n"
+                    "def f():\n"
+                    "    pass\n"
+                    "f()\n"
+                ),
+            }
+        )
+    elif case == "G":
+        sources.update(
+            {
+                "pkg.decorators.__init__": (
+                    "def relative_decorator(fn):\n"
+                    "    from .effect import ORIGIN\n"
+                    "    return fn\n"
+                ),
+                "pkg.decorators.effect": "ORIGIN = 'defining-package'\n",
+                "pkg.effect": "ORIGIN = 'caller-package'\n",
+                "pkg.app": (
+                    "from pkg.decorators import relative_decorator\n"
+                    "@relative_decorator\n"
+                    "def f():\n"
+                    "    pass\n"
+                    "f()\n"
+                ),
+            }
+        )
+    else:
+        raise AssertionError(f"unknown positive case: {case}")
+    return sources
+
+
+def test_imported_decorator_return_none_binds_none_then_call_is_unknown(tmp_path):
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.decorators": "def replace(fn):\n    return\n",
+        "pkg.app": (
+            "from pkg.decorators import replace\n"
+            "@replace\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+    }
+    observed = _cpython_reference(tmp_path, sources, "replace", invoke=True)
+
+    assert observed["python"] == [3, 15, 2]
+    assert observed["error"] is None
+    assert observed["call_error"]["type"] == "TypeError"
+    assert tuple(observed["imports"]) == ("pkg.decorators",)
+    assert observed["binding_present"] is True
+    assert observed["binding_type"] == "builtins.NoneType"
+    assert observed["binding_callable"] is False
+    assert observed["decorator_calls"] == 1
+    assert tuple(observed["loaded_effect_modules"]) == ()
+
+    definition = _model(sources)
+    assert definition.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "FROM"
+        and event.module == "pkg.app"
+        and event.target == "pkg.decorators"
+        and event.symbol == "replace"
+        for event in definition.events
+    )
+    decorator_calls = _events(definition, "CALL_FUNCTION")
+    assert tuple(
+        event.symbol
+        for event in decorator_calls
+    ) == ("replace",)
+    assert decorator_calls[0].module == "pkg.app"
+    assert _relevant_start_imports(definition) == ("pkg.decorators",)
+
+    called = _model(
+        {
+            **sources,
+            "pkg.app": sources["pkg.app"] + "f()\n",
+        }
+    )
+    assert called.outcome == "UNKNOWN"
+    assert tuple(
+        event.symbol
+        for event in _events(called, "CALL_FUNCTION")
+    ) == ("replace",)
+
+
+def test_rebound_imported_decorator_is_not_called_or_replaced():
+    modeled = _model(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": (
+                "def apply_decorator(fn):\n"
+                "    import pkg.effect\n"
+                "    return fn\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import apply_decorator\n"
+                "apply_decorator = None\n"
+                "@apply_decorator\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+            "pkg.effect": "pass\n",
+        }
+    )
+
+    assert modeled.outcome == "UNKNOWN"
+    assert any(
+        event.operation == "FROM"
+        and event.module == "pkg.app"
+        and event.target == "pkg.decorators"
+        and event.symbol == "apply_decorator"
+        for event in modeled.events
+    )
+    assert not _events(modeled, "CALL_FUNCTION")
+    assert not any(event.target == "pkg.effect" for event in modeled.events)
+
+
+def test_imported_decorator_global_expression_remains_unknown():
+    modeled = _model(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": (
+                "marker = 'decorators-global'\n"
+                "def read_marker(fn):\n"
+                "    return marker\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import read_marker\n"
+                "@read_marker\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        }
+    )
+
+    assert modeled.outcome == "UNKNOWN"
+    assert any(
+        event.operation == "FROM"
+        and event.module == "pkg.app"
+        and event.target == "pkg.decorators"
+        and event.symbol == "read_marker"
+        for event in modeled.events
+    )
+    assert not any(
+        event.operation == "CALL_FUNCTION" and event.symbol == "read_marker"
+        for event in modeled.events
+    )
+
+
+def test_nested_unsupported_decorator_call_remains_unknown():
+    modeled = _model(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": (
+                "def nested(fn):\n"
+                "    return helper(fn)\n"
+                "def helper(fn):\n"
+                "    return fn\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import nested\n"
+                "@nested\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        }
+    )
+
+    assert modeled.outcome == "UNKNOWN"
+    assert any(
+        event.operation == "FROM"
+        and event.module == "pkg.app"
+        and event.target == "pkg.decorators"
+        and event.symbol == "nested"
+        for event in modeled.events
+    )
+    assert not any(
+        event.operation == "CALL_FUNCTION"
+        and event.symbol in {"nested", "helper"}
+        for event in modeled.events
+    )
+
+
+def test_same_module_single_decorator_keeps_call_order():
+    modeled = _model(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.app": (
+                "def identity(fn):\n"
+                "    return fn\n"
+                "@identity\n"
+                "def f():\n"
+                "    pass\n"
+                "f()\n"
+            ),
+        }
+    )
+
+    assert modeled.outcome == "MODEL_PASS"
+    assert tuple(
+        event.symbol
+        for event in _events(modeled, "CALL_FUNCTION")
+    ) == ("identity", "f")
+    assert not any(event.operation == "FROM" for event in modeled.events)
+
+
+def test_imported_class_decorator_remains_unknown():
+    modeled = _model(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": "def identity(cls):\n    return cls\n",
+            "pkg.app": (
+                "from pkg.decorators import identity\n"
+                "@identity\n"
+                "class C:\n"
+                "    pass\n"
+            ),
+        }
+    )
+
+    assert modeled.outcome == "UNKNOWN"
+    assert any(event.operation == "FROM" for event in modeled.events)
+    assert not _events(modeled, "CALL_FUNCTION")
+
+
+def test_imported_stacked_decorators_remain_unknown():
+    modeled = _model(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": (
+                "def lower(fn):\n"
+                "    return fn\n"
+                "def upper(fn):\n"
+                "    return fn\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import lower, upper\n"
+                "@upper\n"
+                "@lower\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        }
+    )
+
+    assert modeled.outcome == "UNKNOWN"
+    assert not any(
+        event.operation == "CALL_FUNCTION"
+        and event.symbol in {"lower", "upper"}
+        for event in modeled.events
+    )
+
+
+def test_external_lru_cache_remains_unknown():
+    modeled = _model(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.app": (
+                "from functools import lru_cache\n"
+                "@lru_cache\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        }
+    )
+
+    assert modeled.outcome == "UNKNOWN"
+    assert modeled.target_module == "functools"
+    assert modeled.reached_unmodeled_import is not None
+    assert (
+        modeled.reached_unmodeled_import.operation,
+        modeled.reached_unmodeled_import.target,
+        modeled.reached_unmodeled_import.symbol,
+    ) == ("FROM", "functools", "lru_cache")
+    assert not any(
+        event.operation == "CALL_FUNCTION" and event.symbol == "lru_cache"
+        for event in modeled.events
+    )
```

## FINAL_VERDICT

**BLOCKED / FAIL — no FINAL PASS.** The first targeted gate failed on an unresolved `_RestrictedFunction` name in the authorized production branch. STOP was honored; no further fixes, test runs, or post-change audit were performed. The exact source/test changes at the stopping point are recorded above.
