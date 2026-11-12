# P5-M08-I10-I3-R1/R2 — cross-module decorator stacks

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD 103de3e85fd0c45b2fb3f41314de6347daf9de40; branch main, aligned with origin/main.
- DIRECT_EVIDENCE: R2 preflight working tree was clean. Active interpreter was CPython 3.15.2.
- DIRECT_EVIDENCE: Contextor LIVE revision 1388, provenance live. package_model.py and both test modules were workspace_sync=verified, canonical state fresh, no advisory warning.
- DIRECT_EVIDENCE: Contextor syntax_errors=0 and structural DFS cycle count=16, semantics DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES. cycle_semantics family was stale; no semantic refresh was done.
- DIRECT_EVIDENCE: I3-R1 production and test changes are already committed in HEAD 103de3e. Commit 103de3e includes package_model.py, the T3 baseline test, the new continuation test, and walkthrough.md. The R1 production changes are not part of the current R2 diff.
- DIRECT_EVIDENCE: exact R2 anchors matched: baseline F local_imports still had the string-only tuple at _EXPECTED["F"]; _starts still filtered START_IMPORT by non-None pkg.* target without excluding the internal entry module.
- R2 changed only the two authorized test assertions/helper. No production source changed.

## FILES_CHANGED

- tests/test_cycle_semantics_cross_module_stacked_baseline.py — R2 F local-import expectation.
- tests/test_cycle_semantics_cross_module_stack_continuation.py — R2 bootstrap START_IMPORT filter.
- walkthrough.md — report only; excluded from source/test diff accounting.

R1 source/test files already committed at HEAD: contextor/core/cycle_semantics/package_model.py, tests/test_cycle_semantics_cross_module_stacked_baseline.py, and tests/test_cycle_semantics_cross_module_stack_continuation.py.

## F_LOCAL_IMPORT_EXPECTATION_CORRECTION

The F expectation now matches the existing pair assertion: (event.target, event.module) equals (("pkg.bottom_effect", "pkg.app"),). F's CPython fixture, UNKNOWN outcome, bottom-only call sequence, and effect import expectations were unchanged.

## BOOTSTRAP_START_FILTER_CORRECTION

The _starts helper preserves (event.module, event.target), START_IMPORT, non-None target and pkg. prefix conditions. It excludes only event.module == "\x00ENTRY". Real pkg.* module starts remain selected; no target-specific filtering was added.

## FOREIGN_DECORATOR_EXECUTION_MODULES

R1 targeted tests verified that CALL_FUNCTION is attributed to applying module pkg.app while decorator body effects execute in each decorator's defining module:
- A: bottom in pkg.decorators; upper in pkg.app.
- B: bottom in pkg.app; upper in pkg.decorators.
- C: lower in pkg.lower; upper in pkg.upper.
- D: aliases preserve the original lower/upper snapshot objects and execute in their defining modules.

## DECORATOR_CONTINUATION

The R1 test gate verified explicit return, natural completion, and bare-return continuation cases. Intermediate results travel to the next stored object; natural completion and bare return pass None. The R1 noncallable-upper case remains UNKNOWN after lower effects, with no upper call.

## APPLYING_MODULE_BINDING

The committed R1 implementation retains binding_module as the final result owner, emits continuation CALL_FUNCTION under that module, and writes the decorated name after the stack completes. R2 made no evaluator or frame changes.

## BOTTOM_UP_ORDER

R1 baseline and continuation tests verified bottom-to-top call order. The existing reversed snapshot order and exact captured objects remain unchanged by R2.

## INTERMEDIATE_NONE

R1 continuation tests for implicit natural completion and explicit bare return passed. Both definition-only cases were MODEL_PASS; the appended f() model-only checks were UNKNOWN, with no CALL_FUNCTION(f).

## NONCALLABLE_UPPER_BOUNDARY

The R1 test passed for an upper snapshot value of None: the lower effect remained visible, outcome was UNKNOWN, and no upper CALL_FUNCTION was fabricated.

## SNAPSHOT_IDENTITY

The R1 unit regression passed: after snapshot, rebinding a mutable namespace's upper alias did not alter the captured object identity or source-name order; reversing the stored pairs selected the original bottom and upper objects. This remains a unit-only snapshot identity check.

## CPYTHON_PARITY_MATRIX

All six unchanged T3 CPython reference fixtures passed in the first gate:
| Case | Calls | Outcome/final binding |
|---|---|---|
| A | bottom@pkg.decorators, upper@pkg.app | successful import; original function remains callable |
| B | bottom@pkg.app, upper@pkg.decorators | successful import; original function remains callable |
| C | lower@pkg.lower, upper@pkg.upper | successful import; original function remains callable |
| D | lower@pkg.lower, upper@pkg.upper via aliases | successful import; original function remains callable |
| E | bottom@pkg.decorators, upper@pkg.app receives None | successful import; f is None |
| F | bottom@pkg.app only | TypeError at upper=None; no final f binding |

Independent CPython evidence for the later targeted-subset failure used the same imported stacked-decorator shape: calls were ["lower", "upper"], f was callable, and f() returned None. The existing UNKNOWN expectation conflicts with ordinary Python decorator application and with the I3-R1 indexed-stack behavior.

## FIRST_GATE_RESULTS

Exact command:
.\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_stacked_baseline.py tests/test_cycle_semantics_cross_module_stack_continuation.py -rs

DIRECT_EVIDENCE: 17 passed in 3.41s.

## TARGETED_REGRESSION_RESULTS

Exact R2 targeted regression subset ran and returned 317 passed, 1 failed in 28.06s.

Failure:
tests/test_cycle_semantics_cross_module_single_decorator.py::test_imported_stacked_decorators_remain_unknown
Source anchor: tests/test_cycle_semantics_cross_module_single_decorator.py:546-566; failing assertion at line 566.

Original expected outcome: UNKNOWN.
Actual model outcome: MODEL_PASS.
Assertion traceback:
~~~text
_______________ test_imported_stacked_decorators_remain_unknown _______________
>       assert modeled.outcome == "UNKNOWN"
E       AssertionError: assert 'MODEL_PASS' == 'UNKNOWN'
E       AssertionError: tests\test_cycle_semantics_cross_module_single_decorator.py:566
1 failed, 317 passed in 28.06s
~~~

Complete model events (outcome MODEL_PASS; target_module=None; symbol=None):
~~~text
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg', symbol=None)
PackageModelEvent(module='pkg', operation='READY', target=None, symbol=None)
PackageModelEvent(module='\x00ENTRY', operation='START_IMPORT', target='pkg.app', symbol=None)
PackageModelEvent(module='pkg.app', operation='START_IMPORT', target='pkg.decorators', symbol=None)
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='lower')
PackageModelEvent(module='pkg.decorators', operation='DEFINE_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.decorators', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.decorators', symbol='decorators')
PackageModelEvent(module='pkg.app', operation='PREPARE_FROM_MEMBER', target='pkg.decorators', symbol='lower')
PackageModelEvent(module='pkg.app', operation='PREPARE_FROM_MEMBER', target='pkg.decorators', symbol='upper')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='lower')
PackageModelEvent(module='pkg.app', operation='FROM', target='pkg.decorators', symbol='upper')
PackageModelEvent(module='pkg.app', operation='DEFINE_FUNCTION', target=None, symbol='f')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='lower')
PackageModelEvent(module='pkg.app', operation='CALL_FUNCTION', target=None, symbol='upper')
PackageModelEvent(module='pkg.app', operation='READY', target=None, symbol=None)
PackageModelEvent(module='pkg', operation='BIND_CHILD', target='pkg.app', symbol='app')
~~~

Failure classification:
- DIRECT_EVIDENCE: this is the sole failing test in the targeted regression command.
- DIRECT_EVIDENCE: the CPython fixture with the same import/decorator ordering calls lower then upper successfully and leaves f callable.
- CONTRACT_PROVED: I3-R1 adds execution for named restricted stacks across indexed modules. The old UNKNOWN expectation is incompatible with this implemented contract.
- No further test edit was authorized in R2, so work stops here. The remaining assertion forbidding CALL_FUNCTION(lower/upper) was not reached because the outcome assertion failed first.

git diff --check exited 0. Git printed only line-ending normalization warnings for the two modified tests.

## MCP_POST_CHANGE_AUDIT

NOT RUN. R2 requires the audit only after both gates pass; the targeted regression command had one failure. Preflight Contextor revision 1388 and sync evidence above are not post-change audit evidence.

## FULL_DIFFS

The following are the complete R2 diffs from HEAD 103de3e. R1 implementation and test changes are committed in that HEAD. walkthrough.md is the report artifact.

~~~diff
diff --git a/tests/test_cycle_semantics_cross_module_stack_continuation.py b/tests/test_cycle_semantics_cross_module_stack_continuation.py
index 823901e..6679107 100644
--- a/tests/test_cycle_semantics_cross_module_stack_continuation.py
+++ b/tests/test_cycle_semantics_cross_module_stack_continuation.py
@@ -35,7 +35,11 @@ def _starts(model):
     return tuple(
         (event.module, event.target)
         for event in _events(model, "START_IMPORT")
-        if event.target is not None and event.target.startswith("pkg.")
+        if (
+            event.target is not None
+            and event.target.startswith("pkg.")
+            and event.module != "\x00ENTRY"
+        )
     )
 
 
diff --git a/tests/test_cycle_semantics_cross_module_stacked_baseline.py b/tests/test_cycle_semantics_cross_module_stacked_baseline.py
index 61791b2..e480c52 100644
--- a/tests/test_cycle_semantics_cross_module_stacked_baseline.py
+++ b/tests/test_cycle_semantics_cross_module_stacked_baseline.py
@@ -282,7 +282,9 @@ _EXPECTED = {
         "model_calls": ("bottom",),
         "from_symbols": ("upper",),
         "model_starts": ("pkg.decorators", "pkg.bottom_effect"),
-        "local_imports": ("pkg.bottom_effect",),
+        "local_imports": (
+            ("pkg.bottom_effect", "pkg.app"),
+        ),
     },
 }
~~~

## FINAL_VERDICT

STOP after the targeted regression failure. First gate PASS (17 passed); targeted subset is not clean (317 passed, 1 failed). No additional test expectation was changed, no production code was modified in R2, and no post-change MCP audit was performed.

