# P5-M08-I10-T3 — cross-module decorator stack baseline

## PREFLIGHT

- **DIRECT_EVIDENCE:** Contextor MCP first returned canonical LIVE revision `1382`; `package_model.py` was `canonical_state=fresh`, `workspace_sync=verified`, provenance `live`, with no advisory warning.
- **DIRECT_EVIDENCE:** HEAD was `37545a8f85dfc609042eae38c74bf49585e5e7a2`; working tree was clean before this task.
- **DIRECT_EVIDENCE:** active `.venv\Scripts\python.exe` is CPython `3.15.2`.
- **DIRECT_EVIDENCE:** `tests/test_cycle_semantics_cross_module_stacked_baseline.py` did not exist at preflight.
- **CODE_PATH_PROVED:** I10-I2/R2 is present. The single imported decorator branch remains at `package_model.py:2227-2308`; the imported-object helper remains guarded at `execution/calls.py:86-101`.
- **CODE_PATH_PROVED:** `DEFINE_STACKED_FUNCTION` at `package_model.py:2156` snapshots named decorator objects and reverses the snapshot for bottom-up application, but calls each object helper with the applying module. The helper rejects a `_RestrictedFunction` whose `defining_module` differs.
- **CODE_PATH_PROVED:** the return continuation at `package_model.py:2687` advances to the next snapshot object using the current frame module. Natural completion at `package_model.py:1780-1850` similarly supplies `None` to the next object using that module.
- **CODE_PATH_PROVED:** `_FunctionFrame` carries `module`, decorator continuation fields, and `binding_module`; `_advance_frame` preserves them (`execution/state.py:32-78`).
- No production source or existing test was edited.

## FILES_CHANGED

- `tests/test_cycle_semantics_cross_module_stacked_baseline.py` (new).
- `walkthrough.md` (this report; excluded from source/test diff accounting).
- No production changes and no existing test changes.

## CPYTHON_STACK_MATRIX

| Case | CPython decorator calls, in order | CPython imports, in order | Error | Final `f` |
|---|---|---|---|---|
| A | `bottom@pkg.decorators`, `upper@pkg.app` | `pkg.decorators`, `pkg.bottom_effect`, `pkg.upper_effect` | none | callable function; same object as first decorator input |
| B | `bottom@pkg.app`, `upper@pkg.decorators` | `pkg.decorators`, `pkg.bottom_effect`, `pkg.upper_effect` | none | callable function; same object as first decorator input |
| C | `lower@pkg.lower`, `upper@pkg.upper` | `pkg.lower`, `pkg.upper`, `pkg.lower_effect`, `pkg.upper_effect` | none | callable function; same object as first decorator input |
| D | `lower@pkg.lower`, `upper@pkg.upper` through aliases | `pkg.lower`, `pkg.upper`, `pkg.lower_effect`, `pkg.upper_effect` | none | callable function; same object as first decorator input |
| E | `bottom@pkg.decorators`, then `upper@pkg.app` receives `None` | `pkg.decorators` | none | `None`, not callable |
| F | `bottom@pkg.app` | `pkg.decorators`, `pkg.bottom_effect` | `TypeError` applying `None` as upper decorator | no final binding; failed module import |

Every CPython reference subprocess used `-I -B` and reported version `[3, 15, 2]`. The import trace records actual import order; `loaded_effect_modules` is compared as a membership set, not used as an ordering channel.

## FOREIGN_BOTTOM_LOCAL_UPPER

- Case A CPython invokes the foreign bottom decorator first, imports `pkg.bottom_effect`, then invokes the local upper decorator and imports `pkg.upper_effect`. The final binding is the original callable function.
- Model result: `UNKNOWN`, evidence scope `RESTRICTED_REGULAR_PACKAGE_MODEL`, target `pkg.app`, symbol `bottom`. It records the imported bottom binding and local upper definition, but no decorator call or effect import.

```text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='bottom')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='upper')
```

## LOCAL_BOTTOM_FOREIGN_UPPER

- Case B CPython invokes local bottom before foreign upper. Both effects occur and `f` remains the original callable function.
- Model result: `UNKNOWN`, evidence scope `RESTRICTED_REGULAR_PACKAGE_MODEL`, target `pkg.app`, symbol `upper`. The local bottom decorator runs once and imports `pkg.bottom_effect`; there is no upper `CALL_FUNCTION` or `pkg.upper_effect` import.

```text
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
```

## TWO_FOREIGN_DEFINING_MODULES

- Case C CPython invokes `lower` in `pkg.lower`, then `upper` in `pkg.upper`; each imports its own effect. The final binding remains the original function.
- Model result: `UNKNOWN`, evidence scope `RESTRICTED_REGULAR_PACKAGE_MODEL`, target `pkg.app`, symbol `lower`. Both FROM bindings are recorded, with no decorator calls or effect imports.

```text
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
```

## IMPORTED_ALIASES

- Case D CPython calls the original `lower` and `upper` function objects from their defining modules through `bottom_alias` and `top_alias`, bottom-up. The final binding is identical to the original function input.
- Model result: `UNKNOWN`, evidence scope `RESTRICTED_REGULAR_PACKAGE_MODEL`, target `pkg.app`, symbol `bottom_alias`. The model's FROM event symbols remain the original exports `lower`, `upper`; no decorator calls or effects are invented.

```text
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
```

## INTERMEDIATE_NONE

- Case E CPython calls foreign `bottom`, which returns `None`; local `upper` then receives `None` and returns it. Final `f` is `None`.
- Model result: `UNKNOWN`, evidence scope `RESTRICTED_REGULAR_PACKAGE_MODEL`, target `pkg.app`, symbol `bottom`. It records no decorator call because the foreign bottom object is rejected by the existing module-provenance check.

```text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='bottom')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='bottom')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='upper')
```

## NONCALLABLE_FOREIGN_UPPER

- Case F CPython applies local bottom and imports `pkg.bottom_effect`, then attempts to call the rebound `None` upper decorator and raises `TypeError`. The failed `pkg.app` module has no final `f` binding.
- Model result: `UNKNOWN`, evidence scope `RESTRICTED_REGULAR_PACKAGE_MODEL`, target `pkg.app`, symbol `upper`. It records bottom's call and import, but no fabricated upper call or upper effect.

```text
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
```

## CURRENT_FRAME_CONTINUATION_EVIDENCE

- `_FunctionFrame` carries decorator-final binding, remaining decorator object identities, and a separate `binding_module` (`execution/state.py:32-78`). `_advance_frame` preserves those fields.
- `DEFINE_STACKED_FUNCTION` snapshots namespace objects before application, reverses the decorator list, and attempts the bottom object first (`package_model.py:2156 onward`). It validates the first object using `_execute_restricted_object_call(..., module=applying_module)` before emitting its CALL_FUNCTION event.
- `RETURN_FUNCTION` and natural completion pass the next captured decorator object the intermediate value or `None`, but use the current frame module in the helper call (`package_model.py:2687 onward; 1780 onward`). Thus a local bottom may run and produce imports, while a foreign upper remains unexecuted and makes the outcome UNKNOWN.
- `_execute_restricted_object_call` rejects mismatched defining modules and any object that is not a one-parameter `_RestrictedFunction` (`execution/calls.py:86-101`).
- These are **CODE_PATH_PROVED** boundaries; CPython parity is directly evidenced by the subprocess matrix above. No stack support was added.

## SINGLE_DECORATOR_REGRESSION

- The requested regression command includes the existing I10-I2 single-decorator test `test_indexed_single_decorator_matches_cpython_and_binds_result` in `test_cycle_semantics_cross_module_single_decorator.py`; it passed.
- Same-module stack guards `test_stacked_decorator_execution` and `test_stacked_decorators_remain_bottom_to_top_without_duplicates` passed.
- External callable guards `test_external_lru_cache_remains_unknown` and `test_external_functools_decorator_remains_unmodeled` passed.

## TARGETED_TEST_RESULTS

- Exact command: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_stacked_baseline.py tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_stacked_decorator_execution.py tests/test_cycle_semantics_stacked_decorator_identity.py tests/test_cycle_semantics_function_frame_result_owner.py -rs`.
- The first attempt reached a helper assertion before model evaluation for C/D because the test compared loaded-module membership in the filter-list order. The CPython import-order assertion is separate and remained exact; the membership comparison was corrected to sets.
- Final **DIRECT_EVIDENCE:** `41 passed in 7.43s`.
- `git diff --check` exited `0`.
- No full pytest or SCC02 was run.

## MCP_POST_TASK_AUDIT

- **DIRECT_EVIDENCE:** canonical LIVE revision `1384`, provenance `live`.
- New test source: `canonical_state=fresh`, `workspace_sync=verified`, no advisory warning.
- `package_model.py`: `canonical_state=fresh`, `workspace_sync=verified`, no advisory warning; production source was not changed.
- Syntax error count: `0`.
- Structural DFS cycle count: `16`, with semantics `DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES` (not all simple cycles).
- `cycle_semantics` family remains marked stale; no semantic refresh was requested or performed.
- No FULL, `update_file`, backend restart, Git staging, commit, push, index mutation, or history mutation was performed.

## FULL_DIFFS

Complete diff for the new test file. No existing tests or production files changed. `walkthrough.md` is this report and is excluded from source/test diff accounting.

```diff
diff --git a/tests/test_cycle_semantics_cross_module_stacked_baseline.py b/tests/test_cycle_semantics_cross_module_stacked_baseline.py
new file mode 100644
index 0000000..fadf7fe
--- /dev/null
+++ b/tests/test_cycle_semantics_cross_module_stacked_baseline.py
@@ -0,0 +1,468 @@
+"""CPython and model baselines for cross-module decorator stacks."""
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
+decorator_specs = json.loads(sys.argv[2])
+tracked_imports = set(json.loads(sys.argv[3]))
+tracked_effects = json.loads(sys.argv[4])
+imports = []
+decorator_calls = []
+decorator_inputs = []
+original_import = builtins.__import__
+
+def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
+    if name in tracked_imports:
+        imports.append(name)
+    return original_import(name, globals, locals, fromlist, level)
+
+builtins.__import__ = traced_import
+
+def trace_decorators(frame, event, arg):
+    if event == "call":
+        module_name = frame.f_globals.get("__name__")
+        function_name = frame.f_code.co_name
+        for expected_name, expected_module, parameter in decorator_specs:
+            if function_name == expected_name and module_name == expected_module:
+                value = frame.f_locals.get(parameter)
+                decorator_calls.append(
+                    [
+                        function_name,
+                        module_name,
+                        type(value).__module__ + "." + type(value).__qualname__,
+                    ]
+                )
+                decorator_inputs.append(value)
+                break
+    return trace_decorators
+
+sys.settrace(trace_decorators)
+error_type = None
+try:
+    app = importlib.import_module("pkg.app")
+except BaseException as exc:
+    app = sys.modules.get("pkg.app")
+    error_type = type(exc).__name__
+finally:
+    sys.settrace(None)
+    builtins.__import__ = original_import
+
+binding_present = app is not None and "f" in app.__dict__
+value = app.__dict__.get("f") if binding_present else None
+print(json.dumps({
+    "python": list(sys.version_info[:3]),
+    "error_type": error_type,
+    "decorator_calls": decorator_calls,
+    "imports": imports,
+    "loaded_effect_modules": [
+        name for name in tracked_effects if name in sys.modules
+    ],
+    "binding_present": binding_present,
+    "binding_type": (
+        type(value).__module__ + "." + type(value).__qualname__
+        if binding_present else None
+    ),
+    "binding_callable": callable(value) if binding_present else False,
+    "binding_is_first_decorator_input": (
+        binding_present
+        and bool(decorator_inputs)
+        and value is decorator_inputs[0]
+    ),
+}, sort_keys=True))
+"""
+
+
+_TRACKED_IMPORTS = (
+    "pkg.decorators",
+    "pkg.lower",
+    "pkg.upper",
+    "pkg.bottom_effect",
+    "pkg.upper_effect",
+    "pkg.lower_effect",
+)
+_TRACKED_EFFECTS = (
+    "pkg.bottom_effect",
+    "pkg.upper_effect",
+    "pkg.lower_effect",
+)
+
+_DECORATOR_SPECS = {
+    "A": (
+        ("bottom", "pkg.decorators", "fn"),
+        ("upper", "pkg.app", "fn"),
+    ),
+    "B": (
+        ("bottom", "pkg.app", "fn"),
+        ("upper", "pkg.decorators", "fn"),
+    ),
+    "C": (
+        ("lower", "pkg.lower", "fn"),
+        ("upper", "pkg.upper", "fn"),
+    ),
+    "D": (
+        ("lower", "pkg.lower", "fn"),
+        ("upper", "pkg.upper", "fn"),
+    ),
+    "E": (
+        ("bottom", "pkg.decorators", "fn"),
+        ("upper", "pkg.app", "value"),
+    ),
+    "F": (
+        ("bottom", "pkg.app", "fn"),
+        ("upper", "pkg.decorators", "fn"),
+    ),
+}
+
+_EXPECTED = {
+    "A": {
+        "error_type": None,
+        "calls": (
+            ("bottom", "pkg.decorators", "builtins.function"),
+            ("upper", "pkg.app", "builtins.function"),
+        ),
+        "imports": (
+            "pkg.decorators",
+            "pkg.bottom_effect",
+            "pkg.upper_effect",
+        ),
+        "loaded_effects": ("pkg.bottom_effect", "pkg.upper_effect"),
+        "binding_present": True,
+        "binding_type": "builtins.function",
+        "binding_callable": True,
+        "binding_is_first_input": True,
+        "model_calls": (),
+        "from_symbols": ("bottom",),
+        "model_starts": ("pkg.decorators",),
+        "local_imports": (),
+    },
+    "B": {
+        "error_type": None,
+        "calls": (
+            ("bottom", "pkg.app", "builtins.function"),
+            ("upper", "pkg.decorators", "builtins.function"),
+        ),
+        "imports": (
+            "pkg.decorators",
+            "pkg.bottom_effect",
+            "pkg.upper_effect",
+        ),
+        "loaded_effects": ("pkg.bottom_effect", "pkg.upper_effect"),
+        "binding_present": True,
+        "binding_type": "builtins.function",
+        "binding_callable": True,
+        "binding_is_first_input": True,
+        "model_calls": ("bottom",),
+        "from_symbols": ("upper",),
+        "model_starts": ("pkg.decorators", "pkg.bottom_effect"),
+        "local_imports": ("pkg.bottom_effect",),
+    },
+    "C": {
+        "error_type": None,
+        "calls": (
+            ("lower", "pkg.lower", "builtins.function"),
+            ("upper", "pkg.upper", "builtins.function"),
+        ),
+        "imports": (
+            "pkg.lower",
+            "pkg.upper",
+            "pkg.lower_effect",
+            "pkg.upper_effect",
+        ),
+        "loaded_effects": ("pkg.lower_effect", "pkg.upper_effect"),
+        "binding_present": True,
+        "binding_type": "builtins.function",
+        "binding_callable": True,
+        "binding_is_first_input": True,
+        "model_calls": (),
+        "from_symbols": ("lower", "upper"),
+        "model_starts": ("pkg.lower", "pkg.upper"),
+        "local_imports": (),
+    },
+    "D": {
+        "error_type": None,
+        "calls": (
+            ("lower", "pkg.lower", "builtins.function"),
+            ("upper", "pkg.upper", "builtins.function"),
+        ),
+        "imports": (
+            "pkg.lower",
+            "pkg.upper",
+            "pkg.lower_effect",
+            "pkg.upper_effect",
+        ),
+        "loaded_effects": ("pkg.lower_effect", "pkg.upper_effect"),
+        "binding_present": True,
+        "binding_type": "builtins.function",
+        "binding_callable": True,
+        "binding_is_first_input": True,
+        "model_calls": (),
+        "from_symbols": ("lower", "upper"),
+        "model_starts": ("pkg.lower", "pkg.upper"),
+        "local_imports": (),
+    },
+    "E": {
+        "error_type": None,
+        "calls": (
+            ("bottom", "pkg.decorators", "builtins.function"),
+            ("upper", "pkg.app", "builtins.NoneType"),
+        ),
+        "imports": ("pkg.decorators",),
+        "loaded_effects": (),
+        "binding_present": True,
+        "binding_type": "builtins.NoneType",
+        "binding_callable": False,
+        "binding_is_first_input": False,
+        "model_calls": (),
+        "from_symbols": ("bottom",),
+        "model_starts": ("pkg.decorators",),
+        "local_imports": (),
+    },
+    "F": {
+        "error_type": "TypeError",
+        "calls": (("bottom", "pkg.app", "builtins.function"),),
+        "imports": ("pkg.decorators", "pkg.bottom_effect"),
+        "loaded_effects": ("pkg.bottom_effect",),
+        "binding_present": False,
+        "binding_type": None,
+        "binding_callable": False,
+        "binding_is_first_input": False,
+        "model_calls": ("bottom",),
+        "from_symbols": ("upper",),
+        "model_starts": ("pkg.decorators", "pkg.bottom_effect"),
+        "local_imports": ("pkg.bottom_effect",),
+    },
+}
+
+
+def _sources(case):
+    sources = {"pkg.__init__": "pass\n"}
+    if case == "A":
+        sources.update(
+            {
+                "pkg.decorators": (
+                    "def bottom(fn):\n"
+                    "    import pkg.bottom_effect\n"
+                    "    return fn\n"
+                ),
+                "pkg.bottom_effect": "pass\n",
+                "pkg.upper_effect": "pass\n",
+                "pkg.app": (
+                    "from pkg.decorators import bottom\n"
+                    "def upper(fn):\n"
+                    "    import pkg.upper_effect\n"
+                    "    return fn\n"
+                    "@upper\n"
+                    "@bottom\n"
+                    "def f():\n"
+                    "    pass\n"
+                ),
+            }
+        )
+    elif case == "B":
+        sources.update(
+            {
+                "pkg.decorators": (
+                    "def upper(fn):\n"
+                    "    import pkg.upper_effect\n"
+                    "    return fn\n"
+                ),
+                "pkg.upper_effect": "pass\n",
+                "pkg.bottom_effect": "pass\n",
+                "pkg.app": (
+                    "from pkg.decorators import upper\n"
+                    "def bottom(fn):\n"
+                    "    import pkg.bottom_effect\n"
+                    "    return fn\n"
+                    "@upper\n"
+                    "@bottom\n"
+                    "def f():\n"
+                    "    pass\n"
+                ),
+            }
+        )
+    elif case in {"C", "D"}:
+        sources.update(
+            {
+                "pkg.lower": (
+                    "def lower(fn):\n"
+                    "    import pkg.lower_effect\n"
+                    "    return fn\n"
+                ),
+                "pkg.upper": (
+                    "def upper(fn):\n"
+                    "    import pkg.upper_effect\n"
+                    "    return fn\n"
+                ),
+                "pkg.lower_effect": "pass\n",
+                "pkg.upper_effect": "pass\n",
+                "pkg.app": (
+                    (
+                        "from pkg.lower import lower as bottom_alias\n"
+                        "from pkg.upper import upper as top_alias\n"
+                        "@top_alias\n"
+                        "@bottom_alias\n"
+                    )
+                    if case == "D"
+                    else (
+                        "from pkg.lower import lower\n"
+                        "from pkg.upper import upper\n"
+                        "@upper\n"
+                        "@lower\n"
+                    )
+                )
+                + "def f():\n    pass\n",
+            }
+        )
+    elif case == "E":
+        sources.update(
+            {
+                "pkg.decorators": "def bottom(fn):\n    return\n",
+                "pkg.app": (
+                    "from pkg.decorators import bottom\n"
+                    "def upper(value):\n"
+                    "    return value\n"
+                    "@upper\n"
+                    "@bottom\n"
+                    "def f():\n"
+                    "    pass\n"
+                ),
+            }
+        )
+    elif case == "F":
+        sources.update(
+            {
+                "pkg.decorators": (
+                    "def upper(fn):\n"
+                    "    import pkg.upper_effect\n"
+                    "    return fn\n"
+                ),
+                "pkg.upper_effect": "pass\n",
+                "pkg.bottom_effect": "pass\n",
+                "pkg.app": (
+                    "from pkg.decorators import upper\n"
+                    "upper = None\n"
+                    "def bottom(fn):\n"
+                    "    import pkg.bottom_effect\n"
+                    "    return fn\n"
+                    "@upper\n"
+                    "@bottom\n"
+                    "def f():\n"
+                    "    pass\n"
+                ),
+            }
+        )
+    else:
+        raise AssertionError(f"unknown case: {case}")
+    return sources
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
+def _cpython_reference(tmp_path, case, sources):
+    _write_sources(tmp_path, sources)
+    completed = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            _REFERENCE_RUNNER,
+            str(tmp_path),
+            json.dumps(_DECORATOR_SPECS[case]),
+            json.dumps(_TRACKED_IMPORTS),
+            json.dumps(_TRACKED_EFFECTS),
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
+@pytest.mark.parametrize("case", ("A", "B", "C", "D", "E", "F"))
+def test_cross_module_decorator_stack_cpython_and_model_baseline(tmp_path, case):
+    expected = _EXPECTED[case]
+    sources = _sources(case)
+    observed = _cpython_reference(tmp_path, case, sources)
+
+    assert observed["python"] == [3, 15, 2]
+    assert observed["error_type"] == expected["error_type"]
+    assert tuple(tuple(call) for call in observed["decorator_calls"]) == expected["calls"]
+    assert tuple(observed["imports"]) == expected["imports"]
+    assert set(observed["loaded_effect_modules"]) == set(expected["loaded_effects"])
+    assert observed["binding_present"] is expected["binding_present"]
+    assert observed["binding_type"] == expected["binding_type"]
+    assert observed["binding_callable"] is expected["binding_callable"]
+    assert (
+        observed["binding_is_first_decorator_input"]
+        is expected["binding_is_first_input"]
+    )
+
+    modeled = _model(sources)
+    assert modeled.outcome == "UNKNOWN"
+    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert tuple(event.symbol for event in _events(modeled, "CALL_FUNCTION")) == expected[
+        "model_calls"
+    ]
+    assert tuple(event.symbol for event in _events(modeled, "FROM")) == expected[
+        "from_symbols"
+    ]
+    assert tuple(
+        event.target
+        for event in _events(modeled, "START_IMPORT")
+        if event.target in _TRACKED_IMPORTS
+    ) == expected["model_starts"]
+    local_imports = tuple(
+        event
+        for event in modeled.events
+        if event.operation == "FUNCTION_LOCAL_IMPORT"
+        and event.target in _TRACKED_EFFECTS
+    )
+    assert tuple(event.target for event in local_imports) == expected["local_imports"]
+    assert all(event.module == "pkg.app" for event in local_imports)
+    if expected["model_calls"]:
+        assert all(
+            event.module == "pkg.app"
+            for event in _events(modeled, "CALL_FUNCTION")
+        )
```

## FINAL_VERDICT

**PASS for P5-M08-I10-T3 baseline scope.** All six cross-module stack cases match the specified CPython references and remain `UNKNOWN` in the model with the recorded event boundaries. The focused I10-I2, same-module stack, and external-decorator guards pass; `git diff --check` and the Contextor post-task audit pass.
