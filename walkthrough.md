# P5-M08-I10-I2 + I10-I2-R1 — single indexed cross-module decorator

## PREFLIGHT

- **DIRECT_EVIDENCE:** Contextor MCP first returned canonical LIVE revision `1380`, provenance `live`, `canonical_state=fresh`, and `workspace_sync=verified` for `contextor.core.cycle_semantics.package_model`. The `cycle_semantics` family was `stale`; advisory warning was null.
- **DIRECT_EVIDENCE:** HEAD was `35eda44f79b17de17a9a667611cbee0e81df8d1c`; the working tree was clean before the R1 change.
- **DIRECT_EVIDENCE:** `.venv\Scripts\python.exe` is CPython `3.15.2`.
- **CONTRACT_PROVED:** `execution/calls.py:12-16` defines `_RestrictedFunction`; `package_model.py` referenced it in the I10-I2 `DEFINE_DECORATED_FUNCTION` branch but the calls import block at lines 60-69 did not import it.
- **DIRECT_EVIDENCE:** The I10-I2 branch and existing test changes are present in HEAD. The exact one-line R1 insertion is the only current production diff.
- No source-contract drift was found during preflight.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py` — the single authorized import line.
- `walkthrough.md` — this combined report; it is excluded from source/test diff accounting.
- No test file changed in R1. I10-I2 test changes already exist in HEAD.

## MISSING_IMPORT_ROOT_CAUSE

- **DIRECT_EVIDENCE:** The preceding I10-I2 gate raised `NameError: name '_RestrictedFunction' is not defined` at `package_model.py:2250`, with `17 failed, 18 passed`. The evaluator returned no assessment for those exceptions.
- **CODE_PATH_PROVED:** `_RestrictedFunction` is defined in `execution/calls.py`; it was absent from `package_model.py`'s `.execution.calls` import list.
- R1 added only the missing import. The new first gate no longer reports that NameError.

## EXACT_ONE_LINE_CORRECTION

- Added `_RestrictedFunction,` immediately before `_execute_restricted_call,` in the existing import list.
- No other production line was changed by R1.

## CROSS_MODULE_CALL_ADMISSION

- The existing I10-I2 branch remains in `DEFINE_DECORATED_FUNCTION` (`package_model.py:2227-2308`). It retains the same-module `_execute_restricted_call` path and admits only an exact `_RestrictedFunction` from a different indexed module, present in `logical_sources` and `programs`, with one parameter.
- The foreign branch passes the captured imported object to `_execute_restricted_object_call`; helper provenance and arity checks remain unchanged (`execution/calls.py:80-101`).
- No broader call path or callable type was added.

## DEFINING_MODULE_EXECUTION

- The existing foreign frame stores the decorator's defining module. Its body execution is therefore attributed to that frame module.
- **DIRECT_EVIDENCE:** G's returned event sequence below shows the relative target `pkg.decorators.effect` starting from event module `pkg.decorators`.

## APPLYING_MODULE_BINDING

- The existing foreign frame keeps `binding_module` set to `pkg.app`; unchanged I10-I1 return/natural-completion code handles the final destination (`RETURN_FUNCTION` begins at `package_model.py:2687`).
- A, B, and D model assertions passed in the first gate. C also returned `MODEL_PASS` and called the decorated function; its test failed only because the assertion searched for event symbol `identity` while the decorator expression uses alias `alias`.

## RELATIVE_IMPORT_CONTEXT

- G's model outcome was `MODEL_PASS`. The indexed import started as `pkg.decorators.effect` with event module `pkg.decorators`, and the local from-import event was `FUNCTION_LOCAL_FROM`, also under `pkg.decorators`.
- The fixture's contrasting `pkg.effect` module was not imported.
- The test failed because its assertion expected `FUNCTION_LOCAL_IMPORT` for a `from .effect import ORIGIN` statement. No test change is authorized in R1.

## INDEXED_IMPORT_EFFECTS

- B's test passed: `pkg.effect` was initialized during decorator execution, with `FUNCTION_LOCAL_IMPORT` attributed to `pkg.decorators`; the decorator call event was attributed to `pkg.app`.
- The baseline A2-C2 contract and the effectful imported-decorator regression passed after the import correction.

## SAME_MODULE_REGRESSION

- The same-module single-decorator order test passed. Existing same-module `_execute_restricted_call` behavior remains unchanged.

## NEGATIVE_BOUNDARIES

- The negative tests for rebinding an imported decorator to `None`, unsupported global access, nested unsupported calls, imported stacked decorators, and external `functools.lru_cache` passed.
- The imported class-decorator test returned `UNKNOWN` as required, but its added assertion expecting a `FROM` event failed: the model result had target `pkg.app` and an empty event tuple. The existing compiler returns `None` for a class whose named decorator was not previously defined as a local `DEFINE_FUNCTION` (`package_model.py:848-861`), so evaluation rejects this source before import events. This R1 task authorizes no test edits.

## CPYTHON_PARITY_MATRIX

| Case | CPython 3.15.2 | Model result |
|---|---|---|
| A imported identity | Passed reference assertions: successful import, callable `f`, same object passed through, one decorator call. | `MODEL_PASS`; gate passed. |
| B indexed effect | Passed reference assertions: ordered imports include `pkg.decorators`, then `pkg.effect`; `f` remains callable and identical. | `MODEL_PASS`; effect import event attributed to `pkg.decorators`; gate passed. |
| C imported alias | CPython reference assertions passed; alias applies the imported function and preserves the function object. | `MODEL_PASS`; events call `alias`, then `f`. Gate assertion failed because it expected symbol `identity`. |
| D bare return | CPython reference assertions passed: import succeeds, `f` is `None`, later invocation raises `TypeError`. | Definition is `MODEL_PASS`; later `f()` is `UNKNOWN`; gate passed. |
| G relative import | CPython reference assertions passed; relative effect module is loaded from `pkg.decorators`. | `MODEL_PASS`; defining-package event attribution is correct. Gate assertion failed on expected event operation name. |

## FIRST_GATE_RESULTS

- Exact command: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_function_frame_result_owner.py -rs`
- **DIRECT_EVIDENCE:** `3 failed, 32 passed in 6.74s`; exit code `1`.

### Failure 1 — imported alias C

- Test: `test_indexed_single_decorator_matches_cpython_and_binds_result[C-imported-alias]`.
- Model outcome: `MODEL_PASS`; target and symbol are `None`.
- Failed assertion: helper `_single_imported_decorator_contract` expected exactly one `CALL_FUNCTION` with symbol `identity` (`tests/test_cycle_semantics_cross_module_single_decorator.py:155`). Actual decorator expression is `@alias`; complete model events follow.
- **DIRECT_EVIDENCE — complete events:**

```text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='identity')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='identity')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='alias')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.app', symbol='app')
```

### Failure 2 — relative import G

- Test: `test_indexed_single_decorator_matches_cpython_and_binds_result[G-relative-import]`.
- Model outcome: `MODEL_PASS`; target and symbol are `None`.
- Failed assertion: expected one `FUNCTION_LOCAL_IMPORT` with target `pkg.decorators.effect` (`tests/test_cycle_semantics_cross_module_single_decorator.py:255`). Actual operation is `FUNCTION_LOCAL_FROM` because the fixture uses `from .effect import ORIGIN`.
- **DIRECT_EVIDENCE — complete events:**

```text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='relative_decorator')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='relative_decorator')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='relative_decorator')
PackageModelEvent(module='pkg.decorators', operation='START_IMPORT', target='pkg.decorators.effect', symbol=None)
PackageModelEvent(module='pkg.decorators.effect', operation='BIND', target=None, symbol='ORIGIN')
PackageModelEvent(module='pkg.decorators.effect', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg.decorators', operation='BIND_CHILD', target='pkg.decorators.effect', symbol='effect')
PackageModelEvent(module='pkg.decorators', operation='FUNCTION_LOCAL_FROM', target='pkg.decorators.effect', symbol='ORIGIN')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.app', symbol='app')
```

### Failure 3 — imported class decorator J

- Test: `test_imported_class_decorator_remains_unknown`.
- Model outcome: `UNKNOWN`, target `pkg.app`, symbol `None`.
- Failed assertion: expected any `FROM` event (`tests/test_cycle_semantics_cross_module_single_decorator.py:542`).
- **DIRECT_EVIDENCE — complete events:** empty tuple `()`.
- **CODE_PATH_PROVED:** `package_model.py:848-861` requires each ordinary named class decorator to have an earlier local `DEFINE_FUNCTION`; otherwise `_compile` returns `None` before import-order evaluation. The observed empty event tuple is consistent with this compiler gate.

- The preceding I10-I2 gate's NameError is resolved by R1. No further repair was made after these three failures.
- The full I10-I2 regression command was not run because the first gate failed.
- `git diff --check` was not run: R1 requires it only after both targeted gates pass.

## FULL_TARGETED_RESULTS

- Not run; the first targeted gate failed.

## MCP_POST_CHANGE_AUDIT

- Not run; post-change audit is allowed only after both targeted gates pass.
- Preflight-only diagnostic baseline at LIVE revision 1380 reported zero syntax errors and 16 DFS back-edge-path cycle records. These are not post-change audit evidence.
- No FULL, SCC02, full pytest, `update_file`, backend restart, semantic refresh, Git staging, commit, push, index mutation, or history mutation was performed.

## FULL_DIFFS

All current uncommitted source/test changes relative to HEAD are included below. I10-I2's production and test changes are already present in HEAD; R1 changed only the import line. The walkthrough itself is the report artifact and is excluded from this diff.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index efc02c9..1e7e9df 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -63,6 +63,7 @@ from .execution.lifecycle import (
     _start_module_frame,
 )
 from .execution.calls import (
+    _RestrictedFunction,
     _execute_restricted_call,
     _execute_restricted_object_call,
     _new_restricted_function,
```

## FINAL_VERDICT

**BLOCKED / FAIL — no FINAL PASS.** The one-line R1 correction removed the NameError, but the required first gate still has three test assertion failures (C alias event symbol, G `FUNCTION_LOCAL_FROM` operation, J no import event before compiler rejection). The task's no-test-edit rule applies, so STOP was honored: no assertion changes, further tests, diff check, or post-change audit were performed.
