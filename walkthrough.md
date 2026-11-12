# P5-M08-I10-T4-C — imported class decorator baseline

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was queried first. Pre-change canonical LIVE revision 1391, provenance live; `package_model.py`, `execution/calls.py`, and `execution/class_facts.py` were workspace_sync=verified.
- DIRECT_EVIDENCE: Pre-change HEAD was `a03bfa085e95d7790dea1fd712ff13bdef49e885` on `main`, aligned with `origin/main`. The only pre-existing worktree change was the incomplete T4 stage report in `walkthrough.md`; the required new test file did not exist.
- DIRECT_EVIDENCE: I10-I3 commits are present: R1 `103de3e`, R2 `aa393a2`, R3 `a03bfa0`.
- DIRECT_EVIDENCE: active interpreter and each isolated reference subprocess used CPython 3.15.2.
- DIRECT_EVIDENCE: final HEAD remained `a03bfa085e95d7790dea1fd712ff13bdef49e885`; final status before this report rewrite was:
```
a03bfa085e95d7790dea1fd712ff13bdef49e885
 M walkthrough.md
?? tests/test_cycle_semantics_cross_module_class_decorator_baseline.py
```
- No production source or existing test was edited.

## FILES_CHANGED

- `tests/test_cycle_semantics_cross_module_class_decorator_baseline.py` — added the 12-case CPython reference and model-boundary suite.
- `walkthrough.md` — report only; not counted as a source/test change.
- No Git index or history operation was performed. The new test remains untracked as authorized.

## CPYTHON_CLASS_DECORATOR_MATRIX

Each reference subprocess ran with `-I -B`, reported Python `(3, 15, 2)`, and captured import success/error type, decorator calls and defining modules, helper calls where applicable, marked synthetic effect modules, final `C` binding presence/type, identity with the first decorator input, and subclass behavior.

| Case | CPython result and calls (application order) | Effect modules | Final `C` and identity | Subclass |
|---|---|---|---|---|
| A | Import succeeds; `identity @ pkg.decorators` | none | present, `builtins.type`, class; same object as decorator input | n/a |
| B | Import succeeds; aliased function `identity @ pkg.decorators` | none | present, `builtins.type`, class; same object | n/a |
| C | Import succeeds; `decorate @ pkg.decorators` | `pkg.effect` | present, `builtins.type`, class; same object | n/a |
| D | Import succeeds; `replace @ pkg.decorators` returns None | none | present, `builtins.NoneType`, not a class; not same object | n/a |
| E | Import succeeds; decorator `decorate @ pkg.decorators`; nested helper `factory @ pkg.decorators` | none | present, `builtins.type`, class; same object | n/a |
| F | Import raises `TypeError`; imported `identity` was rebound to None and no decorator function call occurs | none | `C` absent from the partially initialized app module | n/a |
| G | Import succeeds; `bottom @ pkg.app`, then `upper @ pkg.upper` | none | present, `builtins.type`, class; same object | n/a |
| H | Import succeeds; `lower @ pkg.lower`, then `upper @ pkg.upper` | none | present, `builtins.type`, class; same object | n/a |
| I | Import succeeds; `identity @ pkg.decorators` | none | present, `builtins.type`, class; same object | `Child` present and a class; `issubclass(Child, C)` and `isinstance(Child(), C)` are true |
| J | Import succeeds; `decorate @ pkg.decorators` | `pkg.decorators.effect`; decoy `pkg.effect` is not imported | present, `builtins.type`, class; same object | n/a |
| K | Import succeeds; local `identity @ pkg.app` | none | present, `builtins.type`, class; same object | n/a |
| L | Import succeeds; external `dataclass @ dataclasses` | no marked synthetic effect modules; external `dataclasses` import/call is observed | present, `builtins.type`, class; same object | n/a |

The reference assertions are literal expected CPython observations, independent of the model outcome. All 12 passed under the subprocess runner.

## COMPILER_LOCAL_DEFINITION_GATE

DIRECT_EVIDENCE — `contextor/core/cycle_semantics/package_model.py:848-861`:

```python
if any(
    not any(
        earlier.op == "DEFINE_FUNCTION"
        and earlier.binding == decorator_name
        for earlier in steps
    )
    for decorator_name in decorator_names
):
    return None
```

The ordinary decorated-class compiler path requires every decorator name to have an earlier local `DEFINE_FUNCTION`. An indexed `FROM` binding does not satisfy this check. At `package_model.py:1615-1616`, a failed module compilation returns `UNKNOWN` for that module before execution events are emitted. This was observed for A-J and L: target_module `pkg.app`, symbol `None`, and complete events `()`.

## INDEXED_FROM_STEP_ORDER

DIRECT_EVIDENCE — `package_model.py:881-910, 918-1034`:
- Earlier source statements retain their earlier compiled steps, so an indexed `FROM` can precede the class's `SNAPSHOT_CLASS_DECORATORS` in the step list.
- At the class statement, the compiler appends `SNAPSHOT_CLASS_DECORATORS` then `PREPARE_PASSIVE_CLASS`.
- Class-body imports are compiled and appended later, before `DEFINE_DECORATED_PASSIVE_CLASS`.
- For imported decorators in A-J, the local-definition gate returns None during compilation; the evaluator therefore emits no `FROM`, snapshot, or call event. The empty event tuple is a compile-rejection boundary, not evidence that CPython skipped the import or decorator call.

## CLASS_FACT_CREATION

DIRECT_EVIDENCE — `package_model.py:2498-2641`; `execution/class_facts.py:6-17`:
- `PREPARE_PASSIVE_CLASS` resolves and validates base `_ClassFact` values and the selected metaclass, including passive creation and MRO conditions.
- The definition branch constructs a frozen `_ClassFact` with `identity=definition_id`, its base identities, linear MRO, metaclass identity, and subclass flags.
- `class_facts_by_identity[identity] = class_fact` occurs at line 2641 before decorated-class application begins at line 2642.

## CLASS_IDENTITY_AND_NONE_BINDING

CODE_PATH_PROVED — `execution/calls.py:86-101`; `package_model.py:2624-2698, 2709-2790`:
- The restricted object-call helper passes the exact argument object into the one function parameter's local binding.
- For `return cls`, `RETURN_FUNCTION` reads that object from the function frame and transports it as the next decorator argument or final class binding.
- For bare return, `returned_value` remains None; the final class name is bound to None. CPython case D independently confirms `C is None`.
- The independent `class_facts_by_identity` map keeps the previously created fact keyed by its definition identity.
- Natural function-frame completion at `package_model.py:1788-1866` follows the same continuation and uses None as the result when no explicit return occurs.

## CLASS_DECORATOR_STACK_ORDER

DIRECT_EVIDENCE — `package_model.py:2469-2496, 2642-2698`; `execution/calls.py:21-44`:
- Snapshot captures the complete decorator name/value tuple from the namespace.
- The evaluator reverses the captured pairs before application. CPython G and H confirm bottom-to-top order.
- The local supported case K remains `MODEL_PASS` and preserves the event sequence: entry starts `pkg`, package is ready, entry starts `pkg.app`, `DEFINE_FUNCTION(identity)`, `DEFINE_PASSIVE_CLASS(C)`, `CALL_FUNCTION(identity)`, app is ready, then package binds child `pkg.app`.

## DEFINING_MODULE_IMPORT_CONTEXT

DIRECT_EVIDENCE — `execution/calls.py:8-12, 86-101`; `execution/state.py:32-46`; `package_model.py:2642-2698, 2709-2790`:
- `_RestrictedFunction` carries `defining_module`; the object-call helper checks that it equals the supplied module.
- `_FunctionFrame` carries execution `module`, `result_binding`, `decorator_final_binding`, `remaining_decorators`, and optional `binding_module`.
- The first class-decorator call is issued with the applying module; final class result writes use the frame's result-owner module (or current module when unset). In current cases the only modeled decorated class is local K, so both are `pkg.app`.
- CPython confirms defining modules in A-J/L as listed in the matrix. Model does not claim execution for those imported decorators.

## METACLASS_AND_BASE_PRECONDITIONS

DIRECT_EVIDENCE — `package_model.py:260-325, 820-1034, 2498-2623`:
- Passive classes admit no bases or simple `Name` bases; other base expression nodes are rejected.
- The admitted explicit metaclass form is one `metaclass=` keyword with an `ast.Name` value; other class keyword forms are rejected.
- Named decorators are syntactically restricted to simple non-dunder names when enabled.
- Class-body statements are independently constrained; direct imports compile only to the restricted import/member-preparation operations.
- The frozen dataclass exception is conditional on deferred annotation semantics and the exact single frozen-dataclass decorator; it emits a separate `DEFINE_CONDITIONAL_FROZEN_DATACLASS` step.
- All T4 class bodies remain passive; I uses an ordinary supported subclass body. These source conditions describe the model's admission boundary, not general Python validity.

## CURRENT_MODEL_BOUNDARIES

All records use `evidence_scope="RESTRICTED_REGULAR_PACKAGE_MODEL"`.

- A-J and L: `outcome="UNKNOWN"`, `target_module="pkg.app"`, `symbol=None`, complete `events=()`. The compiler returns None at the local `DEFINE_FUNCTION` gate before execution/import simulation.
- K: `outcome="MODEL_PASS"`, `target_module=None`, `symbol=None`; full events are listed under CLASS_DECORATOR_STACK_ORDER and asserted in the new test.
- No imported class decorator was given a new MODEL_PASS admission. External L remains UNKNOWN despite CPython's successful dataclass decoration.

## TARGETED_TEST_RESULTS

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_class_decorator_baseline.py tests/test_cycle_semantics_class_decorator_baseline.py tests/test_cycle_semantics_class_decorator_execution.py tests/test_cycle_semantics_class_decorator_identity_counterexamples.py tests/test_cycle_semantics_cross_module_stack_continuation.py tests/test_cycle_semantics_package_model.py -rs
```

Result: **253 passed in 22.87s**.

- `git diff --check`: exit 0; only Git's LF-to-CRLF working-copy notice.
- The new test was untracked, so an additional `git diff --no-index --check /dev/null <new test>` was run. It emitted no whitespace diagnostics; its exit 1 indicates the expected non-empty no-index diff.

## MCP_POST_TASK_AUDIT

- Canonical LIVE revision 1393, provenance live.
- New test: `workspace_sync=verified`; syntax `checked_and_none`, 0 errors.
- Production sources `package_model.py`, `execution/calls.py`, `execution/class_facts.py`, and `execution/state.py`: each `workspace_sync=verified`; syntax `checked_and_none`, 0 errors.
- Structural cycles: 16, fresh, count semantics `DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES`.
- `cycle_semantics` freshness: stale, recorded separately. No semantic refresh was requested or performed.
- No FULL, SCC02, backend restart, or `update_file`.

## FULL_DIFFS

Complete added-file diff:

~~~diff
diff --git a/tests/test_cycle_semantics_cross_module_class_decorator_baseline.py b/tests/test_cycle_semantics_cross_module_class_decorator_baseline.py
new file mode 100644
index 0000000..9463636
--- /dev/null
+++ b/tests/test_cycle_semantics_cross_module_class_decorator_baseline.py
@@ -0,0 +1,533 @@
+"""CPython references for imported class decorators and model boundaries."""
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
+import importlib
+import json
+import sys
+
+sys.path.insert(0, sys.argv[1])
+specs = {
+    (item["module"], item["name"]): item
+    for item in json.loads(sys.argv[2])
+}
+calls = []
+active_calls = {}
+first_decorator_input = {"seen": False, "value": None}
+
+def type_name(value):
+    value_type = type(value)
+    return value_type.__module__ + "." + value_type.__qualname__
+
+def trace_calls(frame, event, arg):
+    key = (frame.f_globals.get("__name__"), frame.f_code.co_name)
+    spec = specs.get(key)
+    if spec is None:
+        return trace_calls
+
+    if event == "call":
+        value = frame.f_locals.get(spec["parameter"])
+        record = {
+            "name": spec["name"],
+            "module": spec["module"],
+            "role": spec["role"],
+            "input_type": type_name(value),
+            "return_type": None,
+            "returned_input": None,
+            "_input": value,
+        }
+        calls.append(record)
+        active_calls[id(frame)] = record
+        if spec["role"] == "decorator" and not first_decorator_input["seen"]:
+            first_decorator_input["seen"] = True
+            first_decorator_input["value"] = value
+    elif event == "return":
+        record = active_calls.pop(id(frame), None)
+        if record is not None:
+            record["return_type"] = type_name(arg)
+            record["returned_input"] = arg is record["_input"]
+            del record["_input"]
+    return trace_calls
+
+error_type = None
+app = None
+sys.settrace(trace_calls)
+try:
+    app = importlib.import_module("pkg.app")
+except BaseException as exc:
+    error_type = type(exc).__name__
+    app = sys.modules.get("pkg.app")
+finally:
+    sys.settrace(None)
+
+binding_present = app is not None and "C" in app.__dict__
+value = app.__dict__.get("C") if binding_present else None
+subclass = None
+if app is not None and "Child" in app.__dict__:
+    child = app.__dict__["Child"]
+    if binding_present and isinstance(value, type) and isinstance(child, type):
+        instance = child()
+        subclass = {
+            "present": True,
+            "is_class": True,
+            "issubclass": issubclass(child, value),
+            "instantiable_as_base": isinstance(instance, value),
+        }
+    else:
+        subclass = {
+            "present": True,
+            "is_class": isinstance(child, type),
+            "issubclass": False,
+            "instantiable_as_base": False,
+        }
+
+decorator_calls = [item for item in calls if item["role"] == "decorator"]
+helper_calls = [item for item in calls if item["role"] == "helper"]
+for item in calls:
+    item.pop("role", None)
+effect_modules = [
+    name
+    for name, module in sys.modules.items()
+    if name.startswith("pkg.")
+    and getattr(module, "__contextor_effect__", False)
+]
+print(json.dumps({
+    "python": list(sys.version_info[:3]),
+    "import_succeeded": error_type is None,
+    "error_type": error_type,
+    "decorator_calls": decorator_calls,
+    "helper_calls": helper_calls,
+    "effect_modules": effect_modules,
+    "binding_present": binding_present,
+    "binding_type": type_name(value) if binding_present else None,
+    "is_class": binding_present and isinstance(value, type),
+    "final_same_as_first_decorator_input": (
+        value is first_decorator_input["value"]
+        if binding_present and first_decorator_input["seen"]
+        else None
+    ),
+    "subclass": subclass,
+}))
+"""
+
+
+def _spec(name, module, role="decorator"):
+    return {
+        "name": name,
+        "module": module,
+        "parameter": "cls",
+        "role": role,
+    }
+
+
+def _call(name, module, *, input_type="builtins.type", return_type="builtins.type", returned_input=True):
+    return (name, module, input_type, return_type, returned_input)
+
+
+def _reference(
+    *,
+    error_type=None,
+    decorator_calls=(),
+    helper_calls=(),
+    effect_modules=(),
+    binding_present=True,
+    binding_type="builtins.type",
+    is_class=True,
+    same_as_input=True,
+    subclass=None,
+):
+    return {
+        "import_succeeded": error_type is None,
+        "error_type": error_type,
+        "decorator_calls": decorator_calls,
+        "helper_calls": helper_calls,
+        "effect_modules": effect_modules,
+        "binding_present": binding_present,
+        "binding_type": binding_type,
+        "is_class": is_class,
+        "same_as_input": same_as_input,
+        "subclass": subclass,
+    }
+
+
+_UNKNOWN_COMPILE_REJECTION = {
+    "outcome": "UNKNOWN",
+    "target_module": "pkg.app",
+    "symbol": None,
+    "evidence_scope": "RESTRICTED_REGULAR_PACKAGE_MODEL",
+    "events": (),
+}
+
+_LOCAL_IDENTITY_EVENTS = (
+    ("\x00ENTRY", "START_IMPORT", "pkg", None),
+    ("pkg", "READY", None, None),
+    ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+    ("pkg.app", "DEFINE_FUNCTION", None, "identity"),
+    ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+    ("pkg.app", "CALL_FUNCTION", None, "identity"),
+    ("pkg.app", "READY", None, None),
+    ("pkg", "BIND_CHILD", "pkg.app", "app"),
+)
+
+
+CASES = [
+    {
+        "id": "A-imported-identity",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": "def identity(cls):\n    return cls\n",
+            "pkg.app": (
+                "from pkg.decorators import identity\n"
+                "@identity\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [_spec("identity", "pkg.decorators")],
+        "reference": _reference(
+            decorator_calls=(_call("identity", "pkg.decorators"),),
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "B-imported-identity-alias",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": "def identity(cls):\n    return cls\n",
+            "pkg.app": (
+                "from pkg.decorators import identity as alias\n"
+                "@alias\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [_spec("identity", "pkg.decorators")],
+        "reference": _reference(
+            decorator_calls=(_call("identity", "pkg.decorators"),),
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "C-imported-decorator-effect",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": (
+                "def decorate(cls):\n"
+                "    import pkg.effect\n"
+                "    return cls\n"
+            ),
+            "pkg.effect": "__contextor_effect__ = True\n",
+            "pkg.app": (
+                "from pkg.decorators import decorate\n"
+                "@decorate\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [_spec("decorate", "pkg.decorators")],
+        "reference": _reference(
+            decorator_calls=(_call("decorate", "pkg.decorators"),),
+            effect_modules=("pkg.effect",),
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "D-imported-decorator-returns-none",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": "def replace(cls):\n    return\n",
+            "pkg.app": (
+                "from pkg.decorators import replace\n"
+                "@replace\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [_spec("replace", "pkg.decorators")],
+        "reference": _reference(
+            decorator_calls=(
+                _call(
+                    "replace",
+                    "pkg.decorators",
+                    return_type="builtins.NoneType",
+                    returned_input=False,
+                ),
+            ),
+            binding_type="builtins.NoneType",
+            is_class=False,
+            same_as_input=False,
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "E-imported-decorator-nested-call",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": (
+                "def factory(cls):\n"
+                "    return cls\n"
+                "def decorate(cls):\n"
+                "    return factory(cls)\n"
+            ),
+            "pkg.app": (
+                "from pkg.decorators import decorate\n"
+                "@decorate\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [
+            _spec("decorate", "pkg.decorators"),
+            _spec("factory", "pkg.decorators", role="helper"),
+        ],
+        "reference": _reference(
+            decorator_calls=(_call("decorate", "pkg.decorators"),),
+            helper_calls=(_call("factory", "pkg.decorators"),),
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "F-imported-decorator-rebound-to-none",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": "def identity(cls):\n    return cls\n",
+            "pkg.app": (
+                "from pkg.decorators import identity\n"
+                "identity = None\n"
+                "@identity\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [_spec("identity", "pkg.decorators")],
+        "reference": _reference(
+            error_type="TypeError",
+            decorator_calls=(),
+            binding_present=False,
+            binding_type=None,
+            is_class=False,
+            same_as_input=None,
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "G-local-bottom-imported-upper",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.upper": "def upper(cls):\n    return cls\n",
+            "pkg.app": (
+                "def bottom(cls):\n    return cls\n"
+                "from pkg.upper import upper\n"
+                "@upper\n@bottom\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [
+            _spec("bottom", "pkg.app"),
+            _spec("upper", "pkg.upper"),
+        ],
+        "reference": _reference(
+            decorator_calls=(
+                _call("bottom", "pkg.app"),
+                _call("upper", "pkg.upper"),
+            ),
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "H-imported-decorators-distinct-modules",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.lower": "def lower(cls):\n    return cls\n",
+            "pkg.upper": "def upper(cls):\n    return cls\n",
+            "pkg.app": (
+                "from pkg.lower import lower\n"
+                "from pkg.upper import upper\n"
+                "@upper\n@lower\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [
+            _spec("lower", "pkg.lower"),
+            _spec("upper", "pkg.upper"),
+        ],
+        "reference": _reference(
+            decorator_calls=(
+                _call("lower", "pkg.lower"),
+                _call("upper", "pkg.upper"),
+            ),
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "I-imported-identity-then-subclass",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators": "def identity(cls):\n    return cls\n",
+            "pkg.app": (
+                "from pkg.decorators import identity\n"
+                "@identity\nclass C:\n    pass\n"
+                "class Child(C):\n    pass\n"
+            ),
+        },
+        "specs": [_spec("identity", "pkg.decorators")],
+        "reference": _reference(
+            decorator_calls=(_call("identity", "pkg.decorators"),),
+            subclass={
+                "present": True,
+                "is_class": True,
+                "issubclass": True,
+                "instantiable_as_base": True,
+            },
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "J-relative-import-in-defining-package",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.decorators.__init__": (
+                "def decorate(cls):\n"
+                "    from . import effect\n"
+                "    return cls\n"
+            ),
+            "pkg.decorators.effect": "__contextor_effect__ = True\n",
+            "pkg.effect": "__contextor_effect__ = True\n",
+            "pkg.app": (
+                "from pkg.decorators import decorate\n"
+                "@decorate\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [_spec("decorate", "pkg.decorators")],
+        "reference": _reference(
+            decorator_calls=(_call("decorate", "pkg.decorators"),),
+            effect_modules=("pkg.decorators.effect",),
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+    {
+        "id": "K-local-identity",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.app": (
+                "def identity(cls):\n    return cls\n"
+                "@identity\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [_spec("identity", "pkg.app")],
+        "reference": _reference(
+            decorator_calls=(_call("identity", "pkg.app"),),
+        ),
+        "model": {
+            "outcome": "MODEL_PASS",
+            "target_module": None,
+            "symbol": None,
+            "evidence_scope": "RESTRICTED_REGULAR_PACKAGE_MODEL",
+            "events": _LOCAL_IDENTITY_EVENTS,
+        },
+    },
+    {
+        "id": "L-external-dataclass-decorator",
+        "sources": {
+            "pkg.__init__": "pass\n",
+            "pkg.app": (
+                "from dataclasses import dataclass\n"
+                "@dataclass\nclass C:\n    pass\n"
+            ),
+        },
+        "specs": [_spec("dataclass", "dataclasses")],
+        "reference": _reference(
+            decorator_calls=(_call("dataclass", "dataclasses"),),
+        ),
+        "model": _UNKNOWN_COMPILE_REJECTION,
+    },
+]
+
+
+def _write_sources(root: Path, sources: dict[str, str]) -> None:
+    for module, source in sources.items():
+        parts = module.split(".")
+        directory = root.joinpath(*parts[:-1])
+        filename = "__init__.py" if parts[-1] == "__init__" else parts[-1] + ".py"
+        directory.mkdir(parents=True, exist_ok=True)
+        directory.joinpath(filename).write_text(source, encoding="utf-8")
+
+
+def _cpython_reference(tmp_path: Path, case: dict) -> dict:
+    _write_sources(tmp_path, case["sources"])
+    completed = subprocess.run(
+        [
+            sys.executable,
+            "-I",
+            "-B",
+            "-c",
+            _REFERENCE_RUNNER,
+            str(tmp_path),
+            json.dumps(case["specs"]),
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
+def _model_record(case: dict) -> dict:
+    modeled = evaluate_package_import_order(
+        {
+            module: ast.parse(source)
+            for module, source in case["sources"].items()
+        },
+        "pkg.app",
+    )
+    return {
+        "outcome": modeled.outcome,
+        "target_module": modeled.target_module,
+        "symbol": modeled.symbol,
+        "evidence_scope": modeled.evidence_scope,
+        "events": tuple(
+            (event.module, event.operation, event.target, event.symbol)
+            for event in modeled.events
+        ),
+    }
+
+
+def _call_shape(call: dict) -> tuple:
+    return (
+        call["name"],
+        call["module"],
+        call["input_type"],
+        call["return_type"],
+        call["returned_input"],
+    )
+
+
+@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
+def test_cross_module_class_decorator_baseline(tmp_path: Path, case: dict):
+    observed = _cpython_reference(tmp_path, case)
+    assert tuple(observed["python"]) == tuple(sys.version_info[:3])
+    assert tuple(observed["python"]) == (3, 15, 2)
+
+    actual_reference = {
+        "import_succeeded": observed["import_succeeded"],
+        "error_type": observed["error_type"],
+        "decorator_calls": tuple(
+            _call_shape(call) for call in observed["decorator_calls"]
+        ),
+        "helper_calls": tuple(
+            _call_shape(call) for call in observed["helper_calls"]
+        ),
+        "effect_modules": tuple(observed["effect_modules"]),
+        "binding_present": observed["binding_present"],
+        "binding_type": observed["binding_type"],
+        "is_class": observed["is_class"],
+        "same_as_input": observed["final_same_as_first_decorator_input"],
+        "subclass": observed["subclass"],
+    }
+    assert actual_reference == case["reference"], (
+        case["id"],
+        actual_reference,
+    )
+
+    actual_model = _model_record(case)
+    assert actual_model == case["model"], (case["id"], actual_model)
~~~

## FINAL_VERDICT

FINAL PASS for P5-M08-I10-T4-C: all twelve CPython references matched their explicit contracts, all model boundary records matched, the requested targeted subset passed (253 tests), whitespace checks reported no findings, and the post-task Contextor audit verified the new test and production source state. No production file or existing test was changed.

