# PREFLIGHT

**DIRECT_EVIDENCE**

- HEAD: d884572ede58c1a35ec83cca87e1fc70aaaf1c45.
- Preflight git status was clean.
- Contextor MCP canonical LIVE revision: 1371. Canonical state was fresh and workspace_sync=verified for execution/state.py, package_model.py, and the specified existing tests. The cycle_semantics family was stale; advisory_warning was null.
- Active interpreter: C:\Temp\Contextor_Repo\.venv\Scripts\python.exe, CPython 3.15.2.
- Exact local anchors matched the task contract: _FunctionFrame, _advance_frame, _frame_position, natural function-frame completion, RETURN_FUNCTION, both function decorator branches, decorated passive class, and CALL_FUNCTION. There were six _FunctionFrame construction sites in package_model.py: two continuation sites and four initial sites. The requested field could be appended without changing any existing field or same-module call guard.

# FILES_CHANGED

- contextor/core/cycle_semantics/execution/state.py — appended binding_module and preserved it in _advance_frame.
- contextor/core/cycle_semantics/package_model.py — staged the result owner at natural completion and explicit return, used it only for final destination writes, and carried it across the two decorator-continuation frames.
- tests/test_cycle_semantics_function_frame_result_owner.py — new focused tests A-H.
- walkthrough.md — overwritten with this task report; excluded from the source/test FILES_CHANGED list.

# FRAME_EXECUTION_MODULE_CONTRACT

**DIRECT_EVIDENCE**

- execution/state.py:31-62: _FunctionFrame.module remains the field returned by _frame_module and _frame_position.
- package_model.py:1680-1700 reads module and index from the active frame, and evaluates that frame’s stored steps. No execution-module behavior was changed.

# FRAME_BINDING_MODULE_FIELD

**CODE_PATH_PROVED**

- execution/state.py:31-46 appends binding_module: str | None = None after remaining_decorators. Existing fields and their order are unchanged.
- None means the legacy destination module. Both natural completion and RETURN_FUNCTION resolve None to the current execution module.
- The four initial evaluator frame constructors remain unchanged and use the default None: stacked function, single decorated function, decorated passive class, and CALL_FUNCTION.
- _RestrictedFunction, callable provenance checks, import resolution, and module initialization are unchanged.

# FRAME_ADVANCEMENT_PRESERVATION

**DIRECT_EVIDENCE**

- execution/state.py:65-78: _advance_frame still increments index and preserves module, steps, local_bindings, result_binding, decorator_final_binding, and remaining_decorators. The final positional field is now frame.binding_module.
- New tests verify the default None, preserve a binding destination that differs from frame.module, and verify the pre-existing field values and required object identities after advancement.

# NATURAL_COMPLETION_RESULT_OWNER

**CODE_PATH_PROVED**

- package_model.py:1791-1854 derives binding_module at the start of natural _FunctionFrame completion.
- Implicit-None decorated-name writes and ordinary result_binding writes now target namespaces[binding_module].
- The next decorator is still invoked with module=module; event attribution and execution-module behavior are unchanged.

# EXPLICIT_RETURN_RESULT_OWNER

**CODE_PATH_PROVED**

- package_model.py:2649-2720 derives binding_module after validating that active_frame is a _FunctionFrame.
- Return-value lookup, frame pop, event order, and budget behavior remain in their previous order.
- Explicit returned decorated-name results and result_binding results now target namespaces[binding_module].

# DECORATOR_CONTINUATION_OWNER

**DIRECT_EVIDENCE**

- The natural-completion continuation frame at package_model.py:1828-1840 receives binding_module.
- The RETURN_FUNCTION continuation frame at package_model.py:2697-2709 receives binding_module.
- Both constructors retain module=module, so execution continues in the same execution module while the result destination is preserved separately.

# UNCHANGED_SAME_MODULE_BEHAVIOR

**DIRECT_EVIDENCE — new focused tests**

- D: local identity-decorated f is MODEL_PASS. CALL_FUNCTION remains (deco, f); DEFINE_FUNCTION remains (deco, f). Calling f after decoration proves the final function binding is available.
- E: local decorated class C and subclass Child are MODEL_PASS. DEFINE_PASSIVE_CLASS remains (C, Child), and CALL_FUNCTION remains (deco). Child(C) exercises the post-decoration class binding.
- F: stacked decorators remain MODEL_PASS and bottom-to-top: CALL_FUNCTION is (lower, upper, f), with each decorator called once.
- Existing event-order regression files also passed in the targeted subset.

# CROSS_MODULE_CALL_STILL_REJECTED

**DIRECT_EVIDENCE**

- G: imported identity reaches pkg.app’s FROM event, remains UNKNOWN, and has no CALL_FUNCTION for identity.
- H: functools.lru_cache remains an unmodeled FROM import with target_module=functools, UNKNOWN, and no CALL_FUNCTION for lru_cache.
- execution/calls.py was not changed. Its same-module defining_module checks remain in place. No foreign frame was fabricated in tests.

# TARGETED_TEST_RESULTS

**DIRECT_EVIDENCE**

- Exact command: .venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_function_frame_result_owner.py tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_stacked_decorator_execution.py tests/test_cycle_semantics_class_decorator_execution.py tests/test_cycle_semantics_class_decorator_baseline.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_cycle_semantics_package_model.py -rs
- Result: 270 passed in 29.65s; exit code 0.
- git diff --check: exit code 0 with no whitespace errors. Git emitted only LF-to-CRLF working-copy advisories.
- No full pytest, SCC02, FULL, update_file, backend restart, semantic refresh, Git index/history mutation, commit, or push was performed.

# MCP_POST_CHANGE_AUDIT

**DIRECT_EVIDENCE**

- Canonical LIVE revision: 1374. Contextor reported canonical_state=fresh and workspace_sync=verified for both changed production modules and the new test module. cycle_semantics remained stale; advisory_warning was null.
- Source diagnostics: syntax_errors=0, fresh. Structural DFS cycle count=16, fresh; the count semantics are DFS back-edge paths deduplicated by rotation, not all simple cycles.
- Dependency directions, from the canonical LIVE graph:
  - execution/state.py: 2 outbound hard dependencies (execution/class_facts, execution/steps); 7 inbound hard dependencies, including package_model.py and the new test.
  - package_model.py: 12 outbound hard dependencies, including execution/state.py; 41 inbound dependencies, fetched untruncated, including the new test. The GUI and one listed test dependency are soft; the other listed inbound edges are hard.
  - the new test: 3 outbound hard dependencies (execution/state.py, execution/steps, package_model.py); 0 inbound dependencies.
- get_symbol_call_context reports only intra-module edges; _advance_frame has no intra-module edges in that channel. Literal source and constructor-site inspection remain the evidence for cross-module frame propagation. The _FunctionFrame lineage query has fresh LIVE lineage at revision 1374; its workspace_sync is unverified by design for that query path.

# FULL_DIFFS

Complete actual zero-context unified diffs follow. Unchanged context lines are omitted; every changed line is included.

## contextor/core/cycle_semantics/execution/state.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index 96b9a44..d54a968 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -45,0 +46 @@ class _FunctionFrame:
+    binding_module: str | None = None
@@ -75,0 +77 @@ def _advance_frame(
+            frame.binding_module,
```

## contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 7c80b5b..b90315c 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -1792,0 +1793,6 @@ def evaluate_package_import_order(
+                binding_module = (
+                    active_frame.binding_module
+                    if active_frame.binding_module is not None
+                    else module
+                )
+
@@ -1832,0 +1839 @@ def evaluate_package_import_order(
+                                binding_module=binding_module,
@@ -1836 +1843 @@ def evaluate_package_import_order(
-                        namespaces[module][
+                        namespaces[binding_module][
@@ -1843 +1850,3 @@ def evaluate_package_import_order(
-                    namespaces[module][active_frame.result_binding] = None
+                    namespaces[binding_module][
+                        active_frame.result_binding
+                    ] = None
@@ -2643,0 +2653,6 @@ def evaluate_package_import_order(
+            binding_module = (
+                active_frame.binding_module
+                if active_frame.binding_module is not None
+                else module
+            )
+
@@ -2692,0 +2708 @@ def evaluate_package_import_order(
+                            binding_module=binding_module,
@@ -2696 +2712 @@ def evaluate_package_import_order(
-                    namespaces[module][
+                    namespaces[binding_module][
@@ -2703 +2719 @@ def evaluate_package_import_order(
-                namespaces[module][result_binding] = returned_value
+                namespaces[binding_module][result_binding] = returned_value
```

## tests/test_cycle_semantics_function_frame_result_owner.py

```diff
diff --git a/tests/test_cycle_semantics_function_frame_result_owner.py b/tests/test_cycle_semantics_function_frame_result_owner.py
new file mode 100644
index 0000000..7d255d0
--- /dev/null
+++ b/tests/test_cycle_semantics_function_frame_result_owner.py
@@ -0,0 +1,226 @@
+"""Regression coverage for function-frame result-owner provenance."""
+
+import ast
+
+from contextor.core.cycle_semantics.execution.state import (
+    _FunctionFrame,
+    _advance_frame,
+)
+from contextor.core.cycle_semantics.execution.steps import _Step
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+def _evaluate_sources(sources, entry_module):
+    return evaluate_package_import_order(
+        {
+            module: ast.parse(source)
+            for module, source in sources.items()
+        },
+        entry_module,
+    )
+
+
+def test_function_frame_binding_module_defaults_to_none():
+    frame = _FunctionFrame(
+        module="pkg.app",
+        index=0,
+        steps=(),
+    )
+
+    assert frame.binding_module is None
+
+
+def test_advance_frame_preserves_distinct_binding_module():
+    frame = _FunctionFrame(
+        module="pkg.execution",
+        index=3,
+        steps=(),
+        binding_module="pkg.results",
+    )
+
+    advanced = _advance_frame(frame)
+
+    assert isinstance(advanced, _FunctionFrame)
+    assert advanced.module == "pkg.execution"
+    assert advanced.index == 4
+    assert advanced.binding_module == "pkg.results"
+
+
+def test_advance_frame_preserves_existing_fields_and_identities():
+    steps = (_Step("PASS"),)
+    local_bindings = {"fn": object()}
+    decorator = object()
+    remaining_decorators = (("outer", decorator),)
+    frame = _FunctionFrame(
+        module="pkg.execution",
+        index=5,
+        steps=steps,
+        local_bindings=local_bindings,
+        result_binding="call_result",
+        decorator_final_binding="decorated_name",
+        remaining_decorators=remaining_decorators,
+        binding_module="pkg.results",
+    )
+
+    advanced = _advance_frame(frame)
+
+    assert isinstance(advanced, _FunctionFrame)
+    assert advanced.module == frame.module
+    assert advanced.index == frame.index + 1
+    assert advanced.steps is steps
+    assert advanced.local_bindings is local_bindings
+    assert advanced.result_binding == "call_result"
+    assert advanced.decorator_final_binding == "decorated_name"
+    assert advanced.remaining_decorators is remaining_decorators
+    assert advanced.binding_module == "pkg.results"
+
+
+def test_local_decorated_function_keeps_call_sequence_and_binding():
+    modeled = _evaluate_sources(
+        {
+            "pkg.__init__": (
+                "def deco(fn):\n"
+                "    return fn\n"
+                "@deco\n"
+                "def f():\n"
+                "    pass\n"
+                "f()\n"
+            ),
+        },
+        "pkg",
+    )
+
+    assert modeled.outcome == "MODEL_PASS"
+    assert tuple(
+        event.symbol
+        for event in modeled.events
+        if event.operation == "CALL_FUNCTION"
+    ) == ("deco", "f")
+    assert tuple(
+        event.symbol
+        for event in modeled.events
+        if event.operation == "DEFINE_FUNCTION"
+    ) == ("deco", "f")
+
+
+def test_local_decorated_class_keeps_definition_and_call_sequence():
+    modeled = _evaluate_sources(
+        {
+            "pkg.__init__": (
+                "def deco(cls):\n"
+                "    return cls\n"
+                "@deco\n"
+                "class C:\n"
+                "    pass\n"
+                "class Child(C):\n"
+                "    pass\n"
+            ),
+        },
+        "pkg",
+    )
+
+    assert modeled.outcome == "MODEL_PASS"
+    assert tuple(
+        event.symbol
+        for event in modeled.events
+        if event.operation == "DEFINE_PASSIVE_CLASS"
+    ) == ("C", "Child")
+    assert tuple(
+        event.symbol
+        for event in modeled.events
+        if event.operation == "CALL_FUNCTION"
+    ) == ("deco",)
+
+
+def test_stacked_decorators_remain_bottom_to_top_without_duplicates():
+    modeled = _evaluate_sources(
+        {
+            "pkg.__init__": (
+                "def upper(fn):\n"
+                "    return fn\n"
+                "def lower(fn):\n"
+                "    return fn\n"
+                "@upper\n"
+                "@lower\n"
+                "def f():\n"
+                "    pass\n"
+                "f()\n"
+            ),
+        },
+        "pkg",
+    )
+
+    calls = tuple(
+        event.symbol
+        for event in modeled.events
+        if event.operation == "CALL_FUNCTION"
+    )
+    assert modeled.outcome == "MODEL_PASS"
+    assert calls == ("lower", "upper", "f")
+    assert calls.count("lower") == 1
+    assert calls.count("upper") == 1
+
+
+def test_imported_decorator_remains_unknown_after_from():
+    modeled = _evaluate_sources(
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
+        },
+        "pkg.app",
+    )
+
+    assert modeled.outcome == "UNKNOWN"
+    assert any(
+        event.operation == "FROM"
+        and event.module == "pkg.app"
+        and event.target == "pkg.decorators"
+        and event.symbol == "identity"
+        for event in modeled.events
+    )
+    assert not any(
+        event.operation == "CALL_FUNCTION"
+        and event.symbol == "identity"
+        for event in modeled.events
+    )
+
+
+def test_external_functools_decorator_remains_unmodeled():
+    modeled = _evaluate_sources(
+        {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": "pass\n",
+            "pkg.app": (
+                "from functools import lru_cache\n"
+                "@lru_cache\n"
+                "def f():\n"
+                "    pass\n"
+            ),
+        },
+        "pkg.app",
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
+        event.operation == "CALL_FUNCTION"
+        and event.symbol == "lru_cache"
+        for event in modeled.events
+    )
```

# FINAL_VERDICT

PASS — the explicit binding destination is staged and propagated while same-module execution, supported model outcomes, decorator event order, and cross-module rejection remain unchanged in the exact targeted regression set.
