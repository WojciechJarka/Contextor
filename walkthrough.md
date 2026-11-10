# P5-M07-I2A — Stable function identity semantic fix

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP first resolved `_execute_restricted_call` at `contextor/core/cycle_semantics/execution/calls.py:8-35`; canonical LIVE revision 1297, source fresh, `workspace_sync=verified`, cycle semantics stale. HEAD `4be79c53bd1ab3183e7052da01e3e7d1a89701a3`; initial `git status --short` clean. Active backend venv executable: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: Old marker/body map anchors matched `execution/calls.py:8-35`, `execution/state.py:46-70`, `package_model.py:1470-1473,1882-1889,2163-2171`; ALIAS copies values at `package_model.py:2196-2210`; BIND writes `None` at `:2184-2186`. `_compile` and frozen `_Step` were not changed.
- DIRECT_EVIDENCE: T1 CPython and T2 model baseline files existed; pre-edit focused run returned `14 passed in 3.13s`. Independent T1 CPython evidence is in `tests/test_cycle_semantics_function_identity_cpython.py`; observable T2 baseline was in `tests/test_cycle_semantics_function_identity_model.py`. Existing alias UNKNOWN regression was at `tests/test_cycle_semantics_package_model_async_alias.py:235-242`.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/calls.py`
- `contextor/core/cycle_semantics/execution/state.py`
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_function_identity_model.py`
- `tests/test_cycle_semantics_package_model_async_alias.py`
- `walkthrough.md` (this report)

## FUNCTION_IDENTITY_IMPLEMENTATION

- DIRECT_EVIDENCE: `execution/calls.py:8-23` now defines a frozen, identity-equality `_RestrictedFunction` and factory. `:25-45` reads the current namespace value, accepts only a same-module `_RestrictedFunction`, and inserts its captured body steps into the mutable program. This is a per-definition object: `package_model.py:1883-1891` calls the factory for every executed DEFINE_FUNCTION step; neither `_Step` nor `_PackageSourceSession` stores the object (`execution/steps.py:6-24`; `package_model.py:124-133`).
- CODE_PATH_PROVED: ALIAS copies the object reference (`package_model.py:2196-2210`), while BIND and later DEFINE_FUNCTION overwrite only the named namespace slot (`:2184-2186`, `:1883-1891`). Thus an alias retains its earlier object and body. The call helper rejects non-objects and foreign-module objects before splicing steps (`execution/calls.py:35-43`).
- DIRECT_EVIDENCE: The model baseline now checks expected outcomes, imported child targets, and exactly one local `CALL_FUNCTION` event for CPython-successful same-module calls (`tests/test_cycle_semantics_function_identity_model.py:65-108`). The old alias regression now expects one `CALL_FUNCTION(other)` and MODEL_PASS (`tests/test_cycle_semantics_package_model_async_alias.py:235-250`).

## REMOVED_DUPLICATE_STATE

- DIRECT_EVIDENCE: Removed `function_definitions` from `_DefinitionState` and its factory, removed the unused `_Step` import and factory argument (`execution/state.py:1-65`); removed evaluator alias, writes, and call argument (`package_model.py:1470-1475,1883-1891,2163-2172`). The factory now has no arguments.
- DIRECT_EVIDENCE: `rg -n 'function_definitions|\\x00FUNCTION:' contextor` returned no matches (exit code 1). The `\x00OPAQUE_FUNCTION:` marker remains in `package_model.py:1899-1905` as instructed. No second restricted-function body registry remains in production source.

## CPYTHON_PARITY_MATRIX

The independent CPython T1 cases passed before and after the change; the updated model T2 assertions passed. `old/new` denotes observed `START_IMPORT` effect for the child module, not the bootstrap package.

| Case | CPython T1 | Model after change | Child import effect | Call event | Status |
|---|---|---|---|---|---|
| direct-call | success, old | MODEL_PASS | old | `f` | observed parity |
| alias-call | success, old | MODEL_PASS | old | `g` | observed parity |
| alias-survives-rebinding | success, old | MODEL_PASS | old | `g` | observed parity |
| old-alias-survives-redefinition | success, old | MODEL_PASS | old | `g` | observed parity |
| new-definition-call | success, new | MODEL_PASS | new | `f` | observed parity |
| noncallable-rebinding | TypeError, neither | UNKNOWN | no invented effect | none | conservative boundary |
| foreign-function-cpython-control | success, old | UNKNOWN | no invented effect | none | intentional foreign-call boundary |

The CPython case and expected-effect definitions are at `tests/test_cycle_semantics_function_identity_cpython.py:22-70`; model assertions are at `tests/test_cycle_semantics_function_identity_model.py:14-108`. UNKNOWN is not claimed as CPython parity.

## NEGATIVE_CONTRACTS

- DIRECT_EVIDENCE: `tests/test_cycle_semantics_function_identity_model.py` adds distinct-object identity checks and a foreign-function UNKNOWN/no-import-effect test. The existing shadowed noncallable regression remains at `tests/test_cycle_semantics_package_model.py:2542-2552`; CPython T1 confirms TypeError for the noncallable case.
- DIRECT_EVIDENCE: The requested direct semantic integrity assertions passed: same-body objects remain distinct; old/new alias calls insert the right body; noncallable and foreign targets return UNKNOWN without program mutation; the object is frozen; state has no `function_definitions`; `_compile` and evaluator remain in `package_model`.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Required focused command across nine test files: `402 passed, 2 warnings in 59.77s`. Both warnings were third-party Authlib deprecations. No SCC02 or full suite.
- DIRECT_EVIDENCE: `git diff --check` exited 0; only LF→CRLF advisories were emitted. No Git index/history mutation, FULL, `update_file`, or restart.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Post-change Contextor LIVE revision 1302 reported fresh canonical state, `workspace_sync=verified`, fresh module/graph/topology/lineage and stale cycle semantics. Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16; MODEL_PASS count 0 in the stale installed semantic family. These diagnostics do not certify runtime adoption or current semantic classification.
- DIRECT_EVIDENCE: `execution.calls` has one hard inbound edge from `package_model` and one hard outbound edge to `execution.steps`, with no reverse edge to `package_model`. `execution.state` has one hard inbound edge from `package_model` and one hard outbound edge to `execution.class_facts` (Contextor module-context response, revision 1301). No new hard dependency edge was reported. Cyclic SCC count was not available in these responses.

## FULL_DIFFS

Complete actual diffs for every changed source/test file follow.

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index ebcf1df..80c23be 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -1,35 +1,45 @@
 from __future__ import annotations
 
+from dataclasses import dataclass
 from typing import Literal
 
 from .steps import _Step
 
 
+@dataclass(frozen=True, eq=False)
+class _RestrictedFunction:
+    defining_module: str
+    body: tuple[_Step, ...]
+
+
+def _new_restricted_function(
+    defining_module: str,
+    body: tuple[_Step, ...],
+) -> _RestrictedFunction:
+    return _RestrictedFunction(
+        defining_module=defining_module,
+        body=body,
+    )
+
+
 def _execute_restricted_call(
     step: _Step,
     *,
     module: str,
     index: int,
     namespaces: dict[str, dict[str, object | None]],
-    function_definitions: dict[
-        str,
-        dict[str, tuple[_Step, ...]],
-    ],
     programs: dict[str, list[_Step]],
 ) -> Literal["ADVANCE", "RETURN_UNKNOWN"]:
-    expected_binding = (
-        "\x00FUNCTION:" + module + ":" + step.target
-    )
+    value = namespaces[module].get(step.target)
 
     if (
-        namespaces[module].get(step.target)
-        != expected_binding
-        or step.target not in function_definitions[module]
+        not isinstance(value, _RestrictedFunction)
+        or value.defining_module != module
     ):
         return "RETURN_UNKNOWN"
 
-    body_steps = function_definitions[module][step.target]
-
-    programs[module][index + 1:index + 1] = list(body_steps)
+    programs[module][index + 1:index + 1] = list(
+        value.body
    )
 
     return "ADVANCE"
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index 2e261ce..a8c9bd7 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -4,7 +4,6 @@ from dataclasses import dataclass
 from typing import Mapping
 
 from .class_facts import _ClassFact, _BUILTIN_CLASS_FACTS
-from .steps import _Step
 
 
 @dataclass
@@ -49,23 +48,13 @@ class _DefinitionState:
         str, tuple[tuple[_ClassFact, ...], _ClassFact]
     ]
     class_facts_by_identity: dict[str, _ClassFact]
-    function_definitions: dict[
-        str,
-        dict[str, tuple[_Step, ...]],
-    ]
 
 
-def _new_definition_state(
-    programs: Mapping[str, object],
-) -> _DefinitionState:
+def _new_definition_state() -> _DefinitionState:
     return _DefinitionState(
         prepared_class_bases={},
         class_facts_by_identity={
             fact.identity: fact
             for fact in _BUILTIN_CLASS_FACTS.values()
         },
-        function_definitions={
-            name: {}
-            for name in programs
-        },
     )
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index d8249f5..19fe6df 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -59,7 +59,10 @@ from .execution.lifecycle import (
     _complete_module_frame,
     _start_module_frame,
 )
-from .execution.calls import _execute_restricted_call
+from .execution.calls import (
+    _execute_restricted_call,
+    _new_restricted_function,
+)
 
 
 @dataclass(frozen=True)
@@ -1467,10 +1470,9 @@ def evaluate_package_import_order(
     )
     states = module_initialization_state.states
     namespaces = module_initialization_state.namespaces
-    definition_state = _new_definition_state(programs)
+    definition_state = _new_definition_state()
     prepared_class_bases = definition_state.prepared_class_bases
     class_facts_by_identity = definition_state.class_facts_by_identity
-    function_definitions = definition_state.function_definitions
 
     bootstrap = "\x00ENTRY"
     execution_cursor = _new_execution_cursor(bootstrap)
@@ -1880,12 +1882,11 @@ def evaluate_package_import_order(
                 )
 
         elif step.op == "DEFINE_FUNCTION":
-            function_definitions[module][step.binding] = (
-                step.function_body
-            )
-
             namespaces[module][step.binding] = (
-                "\x00FUNCTION:" + module + ":" + step.binding
+                _new_restricted_function(
+                    module,
+                    step.function_body,
+                )
             )
 
             events.append(
@@ -2166,7 +2167,6 @@ def evaluate_package_import_order(
                 module=module,
                 index=index,
                 namespaces=namespaces,
-                function_definitions=function_definitions,
                 programs=programs,
             )
 
diff --git a/tests/test_cycle_semantics_function_identity_model.py b/tests/test_cycle_semantics_function_identity_model.py
index 53ee886..86298f3 100644
--- a/tests/test_cycle_semantics_function_identity_model.py
+++ b/tests/test_cycle_semantics_function_identity_model.py
@@ -76,12 +76,81 @@ def test_current_model_identity_boundary(
         and expected["old"] != expected["new"]
     )
 
-    assert result.outcome == (
+    expected_outcome = (
         "UNKNOWN"
-        if consumer_source is not None
-        else (
-            "UNKNOWN"
-            if "g()" in package_source
-            else "MODEL_PASS"
+        if consumer_source is not None or not expected["ok"]
+        else "MODEL_PASS"
+    )
+
+    assert result.outcome == expected_outcome
+
+    call_events = [
+        event
+        for event in result.events
+        if event.operation == "CALL_FUNCTION"
+    ]
+
+    if expected_outcome == "MODEL_PASS":
+        assert len(call_events) == 1
+        assert call_events[0].module == "pkg"
+        assert call_events[0].symbol == (
+            "g" if "g()" in package_source else "f"
         )
+    else:
+        assert call_events == []
+
+
+def test_restricted_function_objects_have_distinct_identity():
+    from contextor.core.cycle_semantics.execution.calls import (
+        _new_restricted_function,
+    )
+    from contextor.core.cycle_semantics.execution.steps import (
+        _Step,
+    )
+
+    body = (_Step("PASS"),)
+
+    first = _new_restricted_function("pkg", body)
+    second = _new_restricted_function("pkg", body)
+
+    assert first is not second
+    assert first != second
+    assert first.body is body
+    assert second.body is body
+
+    bindings = {"f": first}
+    bindings["g"] = bindings["f"]
+    bindings["f"] = second
+
+    assert bindings["g"] is first
+    assert bindings["f"] is second
+
+
+def test_foreign_function_identity_remains_unknown():
+    sources = {
+        "pkg.__init__": ast.parse(
+            "def f():\n"
+            "    import pkg.old\n"
+        ),
+        "pkg.old": ast.parse("pass\n"),
+        "consumer": ast.parse(
+            "from pkg import f\n"
+            "f()\n"
+        ),
+    }
+
+    result = evaluate_package_import_order(
+        sources,
+        "consumer",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert not any(
+        event.operation == "CALL_FUNCTION"
+        for event in result.events
+    )
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.old"
+        for event in result.events
     )
diff --git a/tests/test_cycle_semantics_package_model_async_alias.py b/tests/test_cycle_semantics_package_model_async_alias.py
index 5897cb8..3417779 100644
--- a/tests/test_cycle_semantics_package_model_async_alias.py
+++ b/tests/test_cycle_semantics_package_model_async_alias.py
@@ -232,14 +232,19 @@ def test_alias_of_function_is_bound():
     assert "ALIAS" in _operations(result)
 
 
-def test_aliased_function_call_not_invented():
+def test_aliased_restricted_function_call_executes():
     result = _model(
         "def f():\n"
         "    pass\n"
         "other = f\n"
         "other()\n"
     )
-    assert result.outcome == "UNKNOWN"
+    assert result.outcome == "MODEL_PASS"
+    assert sum(
+        event.operation == "CALL_FUNCTION"
+        and event.symbol == "other"
+        for event in result.events
+    ) == 1
 
 
 def test_class_body_name_alias_still_unknown():
```

## FINAL_VERDICT

- CONTRACT_PROVED for this bounded change: the old name-marker/body map was removed, same-module alias calls now preserve function object identity and import effects on the seven CPython-backed cases, all requested regressions and direct checks passed, and current canonical source/graph evidence is fresh. Cycle-semantic LIVE classification and in-process backend code adoption remain unverified; this report does not claim either. Stop after implementation and audit.
