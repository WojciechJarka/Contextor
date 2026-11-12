# P5-M08-I10-I3-R1 — cross-module decorator stacks

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD 08ec8a8f5b412d226e57b289fd18e3e22e4eac31.
- DIRECT_EVIDENCE: before implementation, git status contained only the previous walkthrough.md report modification; no production/test source was premodified. This report replaces that previous report per repository instructions.
- DIRECT_EVIDENCE: Contextor LIVE revision 1384, provenance live; package_model.py and the T3 baseline test were workspace_sync=verified, no advisory warning.
- DIRECT_EVIDENCE: active interpreter CPython 3.15.2.
- DIRECT_EVIDENCE: I10-I1 _FunctionFrame still has result_binding, decorator_final_binding, remaining_decorators, binding_module; _advance_frame carries the fields.
- DIRECT_EVIDENCE: I10-I2 single foreign decorator branch remains around package_model.py:2227-2308 and executes a one-parameter restricted function in its defining module.
- DIRECT_EVIDENCE: all six unchanged T3 CPython fixture checks passed in the first gate before model assertions.
- DIRECT_EVIDENCE: Contextor reported cycle_semantics stale; no semantic refresh was performed.

## FILES_CHANGED

- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_cross_module_stacked_baseline.py
- tests/test_cycle_semantics_cross_module_stack_continuation.py (new)
- walkthrough.md (report artifact; excluded from source/test diff accounting)

## PREVIOUS_STOP_RESOLUTION

R1 replaced the unrepresentable runtime global-rebinding requirement with an isolated _snapshot_named_decorators identity regression. No grammar was extended. The snapshot identity test passed in the first gate.

## OBJECT_IDENTITY_ADMISSION

The production patch applies the specified admission checks to the exact snapshot object at the first and continuation call sites: _RestrictedFunction, one parameter, defining module present in logical_sources and programs. It calls _execute_restricted_object_call with that object's defining module. The helper itself and its guards were not changed.

## FIRST_DECORATOR_EXECUTION

DEFINE_STACKED_FUNCTION now executes the bottom captured object in first_object.defining_module while attributing its CALL_FUNCTION event to the applying module. The frame owns the defining module and carries binding_module=applying module.

## RETURN_CONTINUATION

RETURN_FUNCTION now transports returned_value to the next captured object, executes it in next_object.defining_module, attributes CALL_FUNCTION to binding_module, and preserves deferred final namespace binding.

## NATURAL_CONTINUATION

Natural frame completion now transports None and executes the next captured object in its defining module. CALL_FUNCTION is attributed to binding_module. Existing frame pop order, step-budget compensation, continuation state and final None binding remain.

## APPLYING_MODULE_BINDING

The final binding still writes to namespaces[binding_module] only after the last decorator. No intermediate namespace write was added.

## BOTTOM_UP_ORDER

The existing reversed snapshot name/object order is preserved. In the tested passing model outcomes, CALL_FUNCTION symbols were bottom-to-top and attributed to pkg.app.

## T3_CPYTHON_PARITY_MATRIX

- DIRECT_EVIDENCE: all six unchanged CPython fixture comparisons passed during the first gate, including exact calls/imports and final binding observations.
- A-E passed their complete baseline tests, including updated model expectations and separate f() checks.
- F's CPython comparison passed; its model remained UNKNOWN, called only bottom, and recorded bottom_effect. It failed on a local_imports expected-value shape.
- No CPython fixture source or reference expectation was changed.

## INTERMEDIATE_NONE

The new natural-completion and bare-return tests both passed: definition-only MODEL_PASS and appended f() UNKNOWN, with no CALL_FUNCTION(f).

## SNAPSHOT_IDENTITY_UNIT_REGRESSION

The new unit test passed. After snapshot, the mutable namespace's upper alias was changed to a third restricted function; snapshot names and exact original upper/bottom object identities remained unchanged. This is the unit-only identity contract, not full evaluator parity for runtime global rebinding.

## NEGATIVE_BOUNDARIES

- The noncallable-upper test reached UNKNOWN after the bottom call and bottom_effect import, with no fabricated upper call; its starts assertion failed before later assertions.
- Same-module stacked execution, single imported decorator, imported class decorator, and external functools.lru_cache tests passed.
- No class, compiler, helper, external callable, or import policy changes were made.

## FIRST_GATE_RESULTS

Command:
.\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_stacked_baseline.py tests/test_cycle_semantics_cross_module_stack_continuation.py -rs

DIRECT_EVIDENCE: 5 failed, 12 passed in 4.63s. Per R1, STOP was required at this gate. No independent fixes were made.

### Exact failures and traceback anchors

1. tests/test_cycle_semantics_cross_module_stacked_baseline.py::test_cross_module_decorator_stack_cpython_and_model_baseline[F], line 500: AssertionError. Actual local-import tuple: (("pkg.bottom_effect", "pkg.app"),). Expected: ("pkg.bottom_effect",). Earlier assertions passed: CPython comparison, UNKNOWN outcome, CALL_FUNCTION(bottom), FROM events, starts and uniqueness.

2. tests/test_cycle_semantics_cross_module_stack_continuation.py::test_foreign_bottom_then_local_upper_uses_each_defining_module, line 88: AssertionError in _starts. Actual tuple:
   (("\x00ENTRY", "pkg.app"), ("pkg.app", "pkg.decorators"), ("pkg.decorators", "pkg.bottom_effect"), ("pkg.app", "pkg.upper_effect"))
   Expected tuple:
   (("pkg.app", "pkg.decorators"), ("pkg.decorators", "pkg.bottom_effect"), ("pkg.app", "pkg.upper_effect"))

3. tests/test_cycle_semantics_cross_module_stack_continuation.py::test_local_bottom_then_foreign_upper_preserves_effect_order, line 140: AssertionError in _starts. Actual tuple:
   (("\x00ENTRY", "pkg.app"), ("pkg.app", "pkg.decorators"), ("pkg.app", "pkg.bottom_effect"), ("pkg.decorators", "pkg.upper_effect"))
   Expected tuple:
   (("pkg.app", "pkg.decorators"), ("pkg.app", "pkg.bottom_effect"), ("pkg.decorators", "pkg.upper_effect"))

4. tests/test_cycle_semantics_cross_module_stack_continuation.py::test_two_foreign_decorators_execute_in_distinct_modules, line 210: AssertionError in _starts. Actual tuple:
   (("\x00ENTRY", "pkg.app"), ("pkg.app", "pkg.lower"), ("pkg.app", "pkg.upper"), ("pkg.lower", "pkg.lower_effect"), ("pkg.upper", "pkg.upper_effect"))
   Expected tuple:
   (("pkg.app", "pkg.lower"), ("pkg.app", "pkg.upper"), ("pkg.lower", "pkg.lower_effect"), ("pkg.upper", "pkg.upper_effect"))

5. tests/test_cycle_semantics_cross_module_stack_continuation.py::test_noncallable_upper_stops_after_lower_effect_without_binding_f, line 366: AssertionError in _starts. Actual tuple:
   (("\x00ENTRY", "pkg.app"), ("pkg.app", "pkg.decorators"), ("pkg.app", "pkg.bottom_effect"))
   Expected tuple:
   (("pkg.app", "pkg.decorators"), ("pkg.app", "pkg.bottom_effect"))

The \x00ENTRY token above denotes the exact module string \x00ENTRY, as in the event representations below. These are assertion failures; no evaluator exception or production traceback occurred.

### Complete events — baseline case F

Outcome UNKNOWN; target_module=pkg.app; symbol=upper.

~~~text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='upper')
PackageModelEvent(module='pkg.app', operation='BIND', target=None, symbol='upper')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.bottom_effect', symbol=None)
PackageModelEvent(module='pkg.bottom_effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.bottom_effect', symbol='bottom_effect')
PackageModelEvent(module='pkg.app', operation='FUNCTION_LOCAL_IMPORT', target='pkg.bottom_effect', symbol='pkg')
~~~

### Complete events — continuation case A

Outcome MODEL_PASS; target_module=None; symbol=None.

~~~text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='bottom')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.decorators', operation='START_IMPORT', target='pkg.bottom_effect', symbol=None)
PackageModelEvent(module='pkg.bottom_effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.bottom_effect', symbol='bottom_effect')
PackageModelEvent(module='pkg.decorators', operation='FUNCTION_LOCAL_IMPORT', target='pkg.bottom_effect', symbol='pkg')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.upper_effect', symbol=None)
PackageModelEvent(module='pkg.upper_effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.upper_effect', symbol='upper_effect')
PackageModelEvent(module='pkg.app', operation='FUNCTION_LOCAL_IMPORT', target='pkg.upper_effect', symbol='pkg')
PackageModelEvent(module='pkg.app', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.app', symbol='app')
~~~

### Complete events — continuation case B

Outcome MODEL_PASS; target_module=None; symbol=None.

~~~text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='upper')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.bottom_effect', symbol=None)
PackageModelEvent(module='pkg.bottom_effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.bottom_effect', symbol='bottom_effect')
PackageModelEvent(module='pkg.app', operation='FUNCTION_LOCAL_IMPORT', target='pkg.bottom_effect', symbol='pkg')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.decorators', operation='START_IMPORT', target='pkg.upper_effect', symbol=None)
PackageModelEvent(module='pkg.upper_effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.upper_effect', symbol='upper_effect')
PackageModelEvent(module='pkg.decorators', operation='FUNCTION_LOCAL_IMPORT', target='pkg.upper_effect', symbol='pkg')
PackageModelEvent(module='pkg.app', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.app', symbol='app')
~~~

### Complete events — continuation case C

Outcome MODEL_PASS; target_module=None; symbol=None.

~~~text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.lower', symbol=None)
PackageModelEvent(module='pkg.lower', operation='DEFINE_FUNCTION', target=None, symbol='lower')
PackageModelEvent(module='pkg.lower', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.lower', symbol='lower')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.lower', symbol='lower')
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.upper', symbol=None)
PackageModelEvent(module='pkg.upper', operation='DEFINE_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.upper', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.upper', symbol='upper')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.upper', symbol='upper')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='lower')
PackageModelEvent(module='pkg.lower', operation='START_IMPORT', target='pkg.lower_effect', symbol=None)
PackageModelEvent(module='pkg.lower_effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.lower_effect', symbol='lower_effect')
PackageModelEvent(module='pkg.lower', operation='FUNCTION_LOCAL_IMPORT', target='pkg.lower_effect', symbol='pkg')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.upper', operation='START_IMPORT', target='pkg.upper_effect', symbol=None)
PackageModelEvent(module='pkg.upper_effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.upper_effect', symbol='upper_effect')
PackageModelEvent(module='pkg.upper', operation='FUNCTION_LOCAL_IMPORT', target='pkg.upper_effect', symbol='pkg')
PackageModelEvent(module='pkg.app', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.app', symbol='app')
~~~

### Complete events — continuation case G

Outcome UNKNOWN; target_module=pkg.app; symbol=upper.

~~~text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='upper')
PackageModelEvent(module='pkg.app', operation='BIND', target=None, symbol='upper')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.bottom_effect', symbol=None)
PackageModelEvent(module='pkg.bottom_effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.bottom_effect', symbol='bottom_effect')
PackageModelEvent(module='pkg.app', operation='FUNCTION_LOCAL_IMPORT', target='pkg.bottom_effect', symbol='pkg')
~~~

## TARGETED_REGRESSION_RESULTS

NOT RUN. The first gate failed. The targeted regression command was not run. No full pytest or SCC02 was run.

## MCP_POST_CHANGE_AUDIT

NOT RUN because R1 requires stopping after a first-gate failure. Preflight LIVE was revision 1384. No post-change source freshness or revision is claimed.

## FULL_DIFFS

Complete task diffs for all changed source/test files are included below. walkthrough.md is the report artifact.

~~~diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 1e7e9df..e6e477c 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -1807,10 +1807,23 @@ def evaluate_package_import_order(
                         )
                         next_locals: dict[str, object | None] = {}
 
+                        if (
+                            not isinstance(
+                                next_object,
+                                _RestrictedFunction,
+                            )
+                            or len(next_object.parameters) != 1
+                            or next_object.defining_module
+                            not in logical_sources
+                            or next_object.defining_module
+                            not in programs
+                        ):
+                            return result("UNKNOWN", module, next_name)
+
                         next_body = _execute_restricted_object_call(
                             next_object,
                             None,
-                            module=module,
+                            module=next_object.defining_module,
                             local_bindings=next_locals,
                         )
 
@@ -1819,7 +1832,7 @@ def evaluate_package_import_order(
 
                         events.append(
                             PackageModelEvent(
-                                module,
+                                binding_module,
                                 "CALL_FUNCTION",
                                 symbol=next_name,
                             )
@@ -1827,7 +1840,7 @@ def evaluate_package_import_order(
 
                         frames.append(
                             _FunctionFrame(
-                                module=module,
+                                module=next_object.defining_module,
                                 index=0,
                                 steps=next_body,
                                 local_bindings=next_locals,
@@ -2185,10 +2198,18 @@ def evaluate_package_import_order(
             first_name, first_object = application_order[0]
             local_bindings: dict[str, object | None] = {}
 
+            if (
+                not isinstance(first_object, _RestrictedFunction)
+                or len(first_object.parameters) != 1
+                or first_object.defining_module not in logical_sources
+                or first_object.defining_module not in programs
+            ):
+                return result("UNKNOWN", module, first_name)
+
             body = _execute_restricted_object_call(
                 first_object,
                 decorated_function,
-                module=module,
+                module=first_object.defining_module,
                 local_bindings=local_bindings,
             )
 
@@ -2214,12 +2235,13 @@ def evaluate_package_import_order(
             frames[-1] = _advance_frame(frames[-1])
             frames.append(
                 _FunctionFrame(
-                    module=module,
+                    module=first_object.defining_module,
                     index=0,
                     steps=body,
                     local_bindings=local_bindings,
                     decorator_final_binding=step.binding,
                     remaining_decorators=application_order[1:],
+                    binding_module=module,
                 )
             )
             continue
@@ -2713,10 +2735,23 @@ def evaluate_package_import_order(
                     )
                     next_locals: dict[str, object | None] = {}
 
+                    if (
+                        not isinstance(
+                            next_object,
+                            _RestrictedFunction,
+                        )
+                        or len(next_object.parameters) != 1
+                        or next_object.defining_module
+                        not in logical_sources
+                        or next_object.defining_module
+                        not in programs
+                    ):
+                        return result("UNKNOWN", module, next_name)
+
                     next_body = _execute_restricted_object_call(
                         next_object,
                         returned_value,
-                        module=module,
+                        module=next_object.defining_module,
                         local_bindings=next_locals,
                     )
 
@@ -2725,7 +2760,7 @@ def evaluate_package_import_order(
 
                     events.append(
                         PackageModelEvent(
-                            module,
+                            binding_module,
                             "CALL_FUNCTION",
                             symbol=next_name,
                         )
@@ -2733,7 +2768,7 @@ def evaluate_package_import_order(
 
                     frames.append(
                         _FunctionFrame(
-                            module=module,
+                            module=next_object.defining_module,
                             index=0,
                             steps=next_body,
                             local_bindings=next_locals,
diff --git a/tests/test_cycle_semantics_cross_module_stacked_baseline.py b/tests/test_cycle_semantics_cross_module_stacked_baseline.py
index fadf7fe..61791b2 100644
--- a/tests/test_cycle_semantics_cross_module_stacked_baseline.py
+++ b/tests/test_cycle_semantics_cross_module_stacked_baseline.py
@@ -147,10 +147,18 @@ _EXPECTED = {
         "binding_type": "builtins.function",
         "binding_callable": True,
         "binding_is_first_input": True,
-        "model_calls": (),
+        "model_outcome": "MODEL_PASS",
+        "model_calls": ("bottom", "upper"),
         "from_symbols": ("bottom",),
-        "model_starts": ("pkg.decorators",),
-        "local_imports": (),
+        "model_starts": (
+            "pkg.decorators",
+            "pkg.bottom_effect",
+            "pkg.upper_effect",
+        ),
+        "local_imports": (
+            ("pkg.bottom_effect", "pkg.decorators"),
+            ("pkg.upper_effect", "pkg.app"),
+        ),
     },
     "B": {
         "error_type": None,
@@ -168,10 +176,18 @@ _EXPECTED = {
         "binding_type": "builtins.function",
         "binding_callable": True,
         "binding_is_first_input": True,
-        "model_calls": ("bottom",),
+        "model_outcome": "MODEL_PASS",
+        "model_calls": ("bottom", "upper"),
         "from_symbols": ("upper",),
-        "model_starts": ("pkg.decorators", "pkg.bottom_effect"),
-        "local_imports": ("pkg.bottom_effect",),
+        "model_starts": (
+            "pkg.decorators",
+            "pkg.bottom_effect",
+            "pkg.upper_effect",
+        ),
+        "local_imports": (
+            ("pkg.bottom_effect", "pkg.app"),
+            ("pkg.upper_effect", "pkg.decorators"),
+        ),
     },
     "C": {
         "error_type": None,
@@ -190,10 +206,19 @@ _EXPECTED = {
         "binding_type": "builtins.function",
         "binding_callable": True,
         "binding_is_first_input": True,
-        "model_calls": (),
+        "model_outcome": "MODEL_PASS",
+        "model_calls": ("lower", "upper"),
         "from_symbols": ("lower", "upper"),
-        "model_starts": ("pkg.lower", "pkg.upper"),
-        "local_imports": (),
+        "model_starts": (
+            "pkg.lower",
+            "pkg.upper",
+            "pkg.lower_effect",
+            "pkg.upper_effect",
+        ),
+        "local_imports": (
+            ("pkg.lower_effect", "pkg.lower"),
+            ("pkg.upper_effect", "pkg.upper"),
+        ),
     },
     "D": {
         "error_type": None,
@@ -212,10 +237,19 @@ _EXPECTED = {
         "binding_type": "builtins.function",
         "binding_callable": True,
         "binding_is_first_input": True,
-        "model_calls": (),
+        "model_outcome": "MODEL_PASS",
+        "model_calls": ("bottom_alias", "top_alias"),
         "from_symbols": ("lower", "upper"),
-        "model_starts": ("pkg.lower", "pkg.upper"),
-        "local_imports": (),
+        "model_starts": (
+            "pkg.lower",
+            "pkg.upper",
+            "pkg.lower_effect",
+            "pkg.upper_effect",
+        ),
+        "local_imports": (
+            ("pkg.lower_effect", "pkg.lower"),
+            ("pkg.upper_effect", "pkg.upper"),
+        ),
     },
     "E": {
         "error_type": None,
@@ -229,7 +263,8 @@ _EXPECTED = {
         "binding_type": "builtins.NoneType",
         "binding_callable": False,
         "binding_is_first_input": False,
-        "model_calls": (),
+        "model_outcome": "MODEL_PASS",
+        "model_calls": ("bottom", "upper"),
         "from_symbols": ("bottom",),
         "model_starts": ("pkg.decorators",),
         "local_imports": (),
@@ -243,6 +278,7 @@ _EXPECTED = {
         "binding_type": None,
         "binding_callable": False,
         "binding_is_first_input": False,
+        "model_outcome": "UNKNOWN",
         "model_calls": ("bottom",),
         "from_symbols": ("upper",),
         "model_starts": ("pkg.decorators", "pkg.bottom_effect"),
@@ -440,29 +476,59 @@ def test_cross_module_decorator_stack_cpython_and_model_baseline(tmp_path, case)
     )
 
     modeled = _model(sources)
-    assert modeled.outcome == "UNKNOWN"
+    assert modeled.outcome == expected["model_outcome"]
     assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
-    assert tuple(event.symbol for event in _events(modeled, "CALL_FUNCTION")) == expected[
-        "model_calls"
-    ]
+    calls = _events(modeled, "CALL_FUNCTION")
+    assert tuple(event.symbol for event in calls) == expected["model_calls"]
+    assert tuple(event.module for event in calls) == ("pkg.app",) * len(calls)
     assert tuple(event.symbol for event in _events(modeled, "FROM")) == expected[
         "from_symbols"
     ]
-    assert tuple(
+    model_starts = tuple(
         event.target
         for event in _events(modeled, "START_IMPORT")
         if event.target in _TRACKED_IMPORTS
-    ) == expected["model_starts"]
+    )
+    assert model_starts == expected["model_starts"]
+    assert len(model_starts) == len(set(model_starts))
     local_imports = tuple(
         event
         for event in modeled.events
         if event.operation == "FUNCTION_LOCAL_IMPORT"
         and event.target in _TRACKED_EFFECTS
     )
-    assert tuple(event.target for event in local_imports) == expected["local_imports"]
-    assert all(event.module == "pkg.app" for event in local_imports)
-    if expected["model_calls"]:
-        assert all(
-            event.module == "pkg.app"
-            for event in _events(modeled, "CALL_FUNCTION")
+    assert tuple(
+        (event.target, event.module)
+        for event in local_imports
+    ) == expected["local_imports"]
+    assert not any(
+        event.operation == "BIND" and event.symbol == "f"
+        for event in modeled.events
+    )
+
+    if case in {"A", "B", "C", "D"}:
+        model_only_sources = dict(sources)
+        model_only_sources["pkg.app"] += "f()\n"
+        called = _model(model_only_sources)
+        assert called.outcome == "MODEL_PASS"
+        called_events = _events(called, "CALL_FUNCTION")
+        assert tuple(event.symbol for event in called_events) == (
+            *expected["model_calls"],
+            "f",
+        )
+        assert tuple(event.module for event in called_events) == (
+            "pkg.app",
+        ) * len(called_events)
+
+    elif case == "E":
+        model_only_sources = dict(sources)
+        model_only_sources["pkg.app"] += "f()\n"
+        called = _model(model_only_sources)
+        assert called.outcome == "UNKNOWN"
+        assert tuple(
+            event.symbol for event in _events(called, "CALL_FUNCTION")
+        ) == expected["model_calls"]
+        assert not any(
+            event.operation == "CALL_FUNCTION" and event.symbol == "f"
+            for event in called.events
         )
~~~

~~~diff
diff --git a/tests/test_cycle_semantics_cross_module_stack_continuation.py b/tests/test_cycle_semantics_cross_module_stack_continuation.py
new file mode 100644
index 0000000..823901e
--- /dev/null
+++ b/tests/test_cycle_semantics_cross_module_stack_continuation.py
@@ -0,0 +1,507 @@
+import ast
+
+from contextor.core.cycle_semantics.execution.calls import (
+    _RestrictedFunction,
+    _snapshot_named_decorators,
+)
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
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
+def _calls(model):
+    return tuple(
+        (event.module, event.symbol)
+        for event in _events(model, "CALL_FUNCTION")
+    )
+
+
+def _starts(model):
+    return tuple(
+        (event.module, event.target)
+        for event in _events(model, "START_IMPORT")
+        if event.target is not None and event.target.startswith("pkg.")
+    )
+
+
+def _local_imports(model):
+    return tuple(
+        (event.module, event.target, event.symbol)
+        for event in _events(model, "FUNCTION_LOCAL_IMPORT")
+    )
+
+
+def _assert_unique_module_starts(model):
+    targets = tuple(target for _module, target in _starts(model))
+    assert len(targets) == len(set(targets))
+
+
+def _with_f_call(sources):
+    model_sources = dict(sources)
+    model_sources["pkg.app"] += "f()\n"
+    return _model(model_sources)
+
+
+def test_foreign_bottom_then_local_upper_uses_each_defining_module():
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.decorators": (
+            "def bottom(fn):\n"
+            "    import pkg.bottom_effect\n"
+            "    return fn\n"
+        ),
+        "pkg.bottom_effect": "pass\n",
+        "pkg.upper_effect": "pass\n",
+        "pkg.app": (
+            "from pkg.decorators import bottom\n"
+            "def upper(fn):\n"
+            "    import pkg.upper_effect\n"
+            "    return fn\n"
+            "@upper\n"
+            "@bottom\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+    }
+
+    modeled = _model(sources)
+    assert modeled.outcome == "MODEL_PASS"
+    assert _calls(modeled) == (
+        ("pkg.app", "bottom"),
+        ("pkg.app", "upper"),
+    )
+    assert _starts(modeled) == (
+        ("pkg.app", "pkg.decorators"),
+        ("pkg.decorators", "pkg.bottom_effect"),
+        ("pkg.app", "pkg.upper_effect"),
+    )
+    assert _local_imports(modeled) == (
+        ("pkg.decorators", "pkg.bottom_effect", "pkg"),
+        ("pkg.app", "pkg.upper_effect", "pkg"),
+    )
+    assert not any(
+        event.operation == "BIND" and event.symbol == "f"
+        for event in modeled.events
+    )
+    _assert_unique_module_starts(modeled)
+
+    called = _with_f_call(sources)
+    assert called.outcome == "MODEL_PASS"
+    assert _calls(called) == (
+        ("pkg.app", "bottom"),
+        ("pkg.app", "upper"),
+        ("pkg.app", "f"),
+    )
+
+
+def test_local_bottom_then_foreign_upper_preserves_effect_order():
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.decorators": (
+            "def upper(fn):\n"
+            "    import pkg.upper_effect\n"
+            "    return fn\n"
+        ),
+        "pkg.upper_effect": "pass\n",
+        "pkg.bottom_effect": "pass\n",
+        "pkg.app": (
+            "from pkg.decorators import upper\n"
+            "def bottom(fn):\n"
+            "    import pkg.bottom_effect\n"
+            "    return fn\n"
+            "@upper\n"
+            "@bottom\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+    }
+
+    modeled = _model(sources)
+    assert modeled.outcome == "MODEL_PASS"
+    assert _calls(modeled) == (
+        ("pkg.app", "bottom"),
+        ("pkg.app", "upper"),
+    )
+    assert _starts(modeled) == (
+        ("pkg.app", "pkg.decorators"),
+        ("pkg.app", "pkg.bottom_effect"),
+        ("pkg.decorators", "pkg.upper_effect"),
+    )
+    assert _local_imports(modeled) == (
+        ("pkg.app", "pkg.bottom_effect", "pkg"),
+        ("pkg.decorators", "pkg.upper_effect", "pkg"),
+    )
+    bottom_call = next(
+        index
+        for index, event in enumerate(modeled.events)
+        if event.operation == "CALL_FUNCTION" and event.symbol == "bottom"
+    )
+    bottom_effect = next(
+        index
+        for index, event in enumerate(modeled.events)
+        if event.operation == "FUNCTION_LOCAL_IMPORT"
+        and event.target == "pkg.bottom_effect"
+    )
+    upper_call = next(
+        index
+        for index, event in enumerate(modeled.events)
+        if event.operation == "CALL_FUNCTION" and event.symbol == "upper"
+    )
+    upper_effect = next(
+        index
+        for index, event in enumerate(modeled.events)
+        if event.operation == "FUNCTION_LOCAL_IMPORT"
+        and event.target == "pkg.upper_effect"
+    )
+    assert bottom_call < bottom_effect < upper_call < upper_effect
+    _assert_unique_module_starts(modeled)
+
+    called = _with_f_call(sources)
+    assert called.outcome == "MODEL_PASS"
+    assert _calls(called)[-1] == ("pkg.app", "f")
+
+
+def test_two_foreign_decorators_execute_in_distinct_modules():
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.lower": (
+            "def lower(fn):\n"
+            "    import pkg.lower_effect\n"
+            "    return fn\n"
+        ),
+        "pkg.upper": (
+            "def upper(fn):\n"
+            "    import pkg.upper_effect\n"
+            "    return fn\n"
+        ),
+        "pkg.lower_effect": "pass\n",
+        "pkg.upper_effect": "pass\n",
+        "pkg.app": (
+            "from pkg.lower import lower\n"
+            "from pkg.upper import upper\n"
+            "@upper\n"
+            "@lower\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+    }
+
+    modeled = _model(sources)
+    assert modeled.outcome == "MODEL_PASS"
+    assert _calls(modeled) == (
+        ("pkg.app", "lower"),
+        ("pkg.app", "upper"),
+    )
+    assert _starts(modeled) == (
+        ("pkg.app", "pkg.lower"),
+        ("pkg.app", "pkg.upper"),
+        ("pkg.lower", "pkg.lower_effect"),
+        ("pkg.upper", "pkg.upper_effect"),
+    )
+    assert _local_imports(modeled) == (
+        ("pkg.lower", "pkg.lower_effect", "pkg"),
+        ("pkg.upper", "pkg.upper_effect", "pkg"),
+    )
+    assert tuple(
+        event.symbol for event in _events(modeled, "FROM")
+    ) == ("lower", "upper")
+    _assert_unique_module_starts(modeled)
+
+    called = _with_f_call(sources)
+    assert called.outcome == "MODEL_PASS"
+    assert _calls(called)[-1] == ("pkg.app", "f")
+
+
+def test_foreign_bottom_natural_completion_passes_none_to_upper():
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.decorators": "def bottom(fn):\n    pass\n",
+        "pkg.app": (
+            "from pkg.decorators import bottom\n"
+            "def upper(value):\n"
+            "    return value\n"
+            "@upper\n"
+            "@bottom\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+    }
+
+    modeled = _model(sources)
+    assert modeled.outcome == "MODEL_PASS"
+    assert _calls(modeled) == (
+        ("pkg.app", "bottom"),
+        ("pkg.app", "upper"),
+    )
+    _assert_unique_module_starts(modeled)
+
+    called = _with_f_call(sources)
+    assert called.outcome == "UNKNOWN"
+    assert _calls(called) == (
+        ("pkg.app", "bottom"),
+        ("pkg.app", "upper"),
+    )
+    assert not any(
+        event.operation == "CALL_FUNCTION" and event.symbol == "f"
+        for event in called.events
+    )
+
+
+def test_foreign_bottom_bare_return_passes_none_to_upper():
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.decorators": "def bottom(fn):\n    return\n",
+        "pkg.app": (
+            "from pkg.decorators import bottom\n"
+            "def upper(value):\n"
+            "    return value\n"
+            "@upper\n"
+            "@bottom\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+    }
+
+    modeled = _model(sources)
+    assert modeled.outcome == "MODEL_PASS"
+    assert _calls(modeled) == (
+        ("pkg.app", "bottom"),
+        ("pkg.app", "upper"),
+    )
+    _assert_unique_module_starts(modeled)
+
+    called = _with_f_call(sources)
+    assert called.outcome == "UNKNOWN"
+    assert _calls(called) == (
+        ("pkg.app", "bottom"),
+        ("pkg.app", "upper"),
+    )
+    assert not any(
+        event.operation == "CALL_FUNCTION" and event.symbol == "f"
+        for event in called.events
+    )
+
+
+def test_snapshot_identity_survives_namespace_rebinding():
+    bottom = _RestrictedFunction(
+        defining_module="pkg.lower",
+        body=(),
+        parameters=("fn",),
+    )
+    upper = _RestrictedFunction(
+        defining_module="pkg.upper",
+        body=(),
+        parameters=("fn",),
+    )
+    replacement = _RestrictedFunction(
+        defining_module="pkg.replacement",
+        body=(),
+        parameters=("fn",),
+    )
+    namespace = {
+        "top_alias": upper,
+        "bottom_alias": bottom,
+    }
+
+    snapshot = _snapshot_named_decorators(
+        ("top_alias", "bottom_alias"),
+        namespace,
+    )
+    assert snapshot is not None
+
+    namespace["top_alias"] = replacement
+
+    assert snapshot.names == ("top_alias", "bottom_alias")
+    assert snapshot.values[0] is upper
+    assert snapshot.values[1] is bottom
+    assert namespace["top_alias"] is replacement
+
+    application_order = tuple(
+        reversed(tuple(zip(snapshot.names, snapshot.values)))
+    )
+    assert tuple(name for name, _value in application_order) == (
+        "bottom_alias",
+        "top_alias",
+    )
+    assert application_order[0][1] is bottom
+    assert application_order[1][1] is upper
+
+
+def test_noncallable_upper_stops_after_lower_effect_without_binding_f():
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.decorators": "def upper(fn):\n    return fn\n",
+        "pkg.bottom_effect": "pass\n",
+        "pkg.app": (
+            "from pkg.decorators import upper\n"
+            "upper = None\n"
+            "def bottom(fn):\n"
+            "    import pkg.bottom_effect\n"
+            "    return fn\n"
+            "@upper\n"
+            "@bottom\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+    }
+
+    modeled = _model(sources)
+    assert modeled.outcome == "UNKNOWN"
+    assert _calls(modeled) == (("pkg.app", "bottom"),)
+    assert _starts(modeled) == (
+        ("pkg.app", "pkg.decorators"),
+        ("pkg.app", "pkg.bottom_effect"),
+    )
+    assert _local_imports(modeled) == (
+        ("pkg.app", "pkg.bottom_effect", "pkg"),
+    )
+    assert not any(
+        event.operation == "CALL_FUNCTION" and event.symbol == "upper"
+        for event in modeled.events
+    )
+    assert not any(
+        event.operation == "BIND" and event.symbol == "f"
+        for event in modeled.events
+    )
+    _assert_unique_module_starts(modeled)
+
+
+def test_same_module_stack_keeps_bottom_up_event_sequence():
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.a": "pass\n",
+        "pkg.b": "pass\n",
+        "pkg.c": "pass\n",
+        "pkg.app": (
+            "def top_decorator(fn):\n"
+            "    import pkg.a\n"
+            "    return fn\n"
+            "def middle_decorator(fn):\n"
+            "    import pkg.b\n"
+            "    return fn\n"
+            "def bottom_decorator(fn):\n"
+            "    import pkg.c\n"
+            "    return fn\n"
+            "@top_decorator\n"
+            "@middle_decorator\n"
+            "@bottom_decorator\n"
+            "def f():\n"
+            "    pass\n"
+        ),
+    }
+
+    modeled = _model(sources)
+    assert modeled.outcome == "MODEL_PASS"
+    relevant = tuple(
+        (event.operation, event.module, event.target, event.symbol)
+        for event in modeled.events
+        if (
+            event.operation == "CALL_FUNCTION"
+            or (
+                event.operation == "START_IMPORT"
+                and event.target in {"pkg.a", "pkg.b", "pkg.c"}
+            )
+            or (
+                event.operation == "FUNCTION_LOCAL_IMPORT"
+                and event.target in {"pkg.a", "pkg.b", "pkg.c"}
+            )
+        )
+    )
+    assert relevant == (
+        ("CALL_FUNCTION", "pkg.app", None, "bottom_decorator"),
+        ("START_IMPORT", "pkg.app", "pkg.c", None),
+        ("FUNCTION_LOCAL_IMPORT", "pkg.app", "pkg.c", "pkg"),
+        ("CALL_FUNCTION", "pkg.app", None, "middle_decorator"),
+        ("START_IMPORT", "pkg.app", "pkg.b", None),
+        ("FUNCTION_LOCAL_IMPORT", "pkg.app", "pkg.b", "pkg"),
+        ("CALL_FUNCTION", "pkg.app", None, "top_decorator"),
+        ("START_IMPORT", "pkg.app", "pkg.a", None),
+        ("FUNCTION_LOCAL_IMPORT", "pkg.app", "pkg.a", "pkg"),
+    )
+    _assert_unique_module_starts(modeled)
+
+    called = _with_f_call(sources)
+    assert called.outcome == "MODEL_PASS"
+    assert _calls(called)[-1] == ("pkg.app", "f")
+
+
+def test_single_imported_decorator_remains_model_pass():
+    modeled = _model(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": (
+                "def identity(fn):\n"
+                "    return fn\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import identity\n"
+                "@identity\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        }
+    )
+
+    assert modeled.outcome == "MODEL_PASS"
+    assert _calls(modeled) == (("pkg.app", "identity"),)
+    _assert_unique_module_starts(modeled)
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
+    assert modeled.events == ()
+
+
+def test_external_functools_lru_cache_remains_unknown():
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
~~~

## FINAL_VERDICT

STOP after the required first test gate. Actual result: 5 failed, 12 passed. No independent fixes, second regression command, git diff --check, or post-change MCP audit were performed.

