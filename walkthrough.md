# P5-M08-I3 — Per-call local function environment

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. `evaluate_package_import_order` resolved to `contextor/core/cycle_semantics/package_model.py:1169-2314`; canonical LIVE revision 1313, source fresh, `workspace_sync=verified`, cycle semantics stale. HEAD `faec99f43420635a6ffd6fab8d0152ac49f95281`; initial `git status --short` clean. Active backend executable: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M08-I1 `_FunctionFrame(module,index,steps)` and `_advance_frame` matched `execution/state.py:31-63`; package_model creates `_FunctionFrame(module,0,body)` at `:2210-2211`; M08-I2 RETURN_FUNCTION pops the active function frame at `:2185-2190`. Repository-wide literal search found only these two production constructors, plus frame-field access in the evaluator. The new test file did not exist. No source drift or extra constructor was found.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/state.py`
- Added `tests/test_cycle_semantics_function_frame_locals.py`
- `walkthrough.md` (this report). No other source or test file changed.

## FRAME_LOCAL_ENVIRONMENT

- DIRECT_EVIDENCE: `execution/state.py:3,31-40` now gives each default-constructed `_FunctionFrame` a distinct `dict[str, object | None]` via `field(default_factory=dict, compare=False, repr=False)`. `_advance_frame` passes the same dictionary to the next immutable frame object (`:59-68`). Module frames remain `(module,index)` tuples; bootstrap and 10000-step budget are unchanged (`:71-82`).
- CODE_PATH_PROVED: The new dictionary is currently infrastructure only. `package_model.py:2210-2211` still constructs a function frame without passing a locals mapping. No compiler, `_Step`, namespace import, parameter, assignment, return-value, decorator or foreign-call branch was changed.

## ISOLATION_AND_ADVANCEMENT_CHECKS

- DIRECT_EVIDENCE: The five exact new tests passed: two fresh frames have distinct empty dictionaries; advancement preserves dictionary identity; nested frames have separate dictionaries; a module tuple does not acquire locals; frame equality ignores mutable locals (`tests/test_cycle_semantics_function_frame_locals.py:1-91`).
- DIRECT_EVIDENCE: Direct backend assertions additionally confirmed a fresh callee dictionary, stable identity after advancement and import suspension, and unchanged `_compile`/evaluator module ownership and `_Step` fields. The returned result was `DIRECT_LOCAL_ENVIRONMENT_PASS`.

## IMPORT_SUSPENSION_CONTRACT

- DIRECT_EVIDENCE: A direct lifecycle check suspended a function frame while `_start_module_frame` pushed `pkg.child`, then `_complete_module_frame` popped that module. The function-frame object and its `local_bindings` dictionary remained the same. Events were `START_IMPORT(pkg.child)`, `READY(pkg.child)`, `BIND_CHILD(pkg.child)`; `pkg` remained INITIALIZING until its own completion. Popping the function frame left the caller module tuple in place. The module namespace acquired only the normal child binding, not the function locals (`execution/lifecycle.py:6-49`; `execution/state.py:31-68`).
- CODE_PATH_PROVED: M08-I2 RETURN_FUNCTION still pops only the active function frame (`package_model.py:2185-2190`). The new locals mapping is not read by module namespace logic.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Required focused command across eight specified files returned `255 passed, 2 warnings in 32.39s`. Both warnings were third-party Authlib deprecations.
- DIRECT_EVIDENCE: `git diff --check` exited 0 before report rewrite, with only an LF→CRLF advisory for `execution/state.py`. No full pytest, SCC02, FULL, update_file, restart, Git add/commit/push, or index/history mutation.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Post-change canonical LIVE revision 1315: changed `execution.state` source fresh, `workspace_sync=verified`, syntax errors 0, DFS structural cycle count 16, active warnings 16, cycle semantics stale. The stale semantic family does not certify current classification or loaded-backend adoption.
- DIRECT_EVIDENCE: `execution.state` has hard inbound dependencies from `execution.imports`, `execution.lifecycle`, and `package_model`; hard outbound dependencies to `execution.class_facts` and `execution.steps` (Contextor module-context, revision 1315). No new hard dependency edge appeared. Cyclic SCC count was not available in the response.

## FULL_DIFFS

Complete changed-source diff (blank context lines are represented without trailing spaces in this Markdown report):

```diff
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index 4fbece6..17d54aa 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -1,6 +1,6 @@
 from __future__ import annotations

-from dataclasses import dataclass
+from dataclasses import dataclass, field
 from typing import Mapping

 from .class_facts import _ClassFact, _BUILTIN_CLASS_FACTS
@@ -33,6 +33,11 @@ class _FunctionFrame:
     module: str
     index: int
     steps: tuple[_Step, ...]
+    local_bindings: dict[str, object | None] = field(
+        default_factory=dict,
+        compare=False,
+        repr=False,
+    )


 def _frame_module(
@@ -59,6 +64,7 @@ def _advance_frame(
             frame.module,
             frame.index + 1,
             frame.steps,
+            frame.local_bindings,
         )
     return (frame[0], frame[1] + 1)

```

Complete new-test diff (`/dev/null` → `tests/test_cycle_semantics_function_frame_locals.py`):

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_function_frame_locals.py
@@ -0,0 +1,91 @@
+from contextor.core.cycle_semantics.execution.state import (
+    _FunctionFrame,
+    _advance_frame,
+    _frame_module,
+    _frame_position,
+)
+from contextor.core.cycle_semantics.execution.steps import (
+    _Step,
+)
+
+
+def test_each_call_has_independent_local_environment():
+    body = (_Step("PASS"),)
+
+    first = _FunctionFrame("pkg", 0, body)
+    second = _FunctionFrame("pkg", 0, body)
+
+    assert first is not second
+    assert first.local_bindings is not second.local_bindings
+    assert first.local_bindings == {}
+    assert second.local_bindings == {}
+
+    first.local_bindings["value"] = 7
+
+    assert first.local_bindings == {"value": 7}
+    assert second.local_bindings == {}
+
+
+def test_advancement_preserves_same_local_environment():
+    body = (_Step("PASS"),)
+
+    initial = _FunctionFrame("pkg", 0, body)
+    initial.local_bindings["argument"] = "item"
+
+    advanced = _advance_frame(initial)
+
+    assert isinstance(advanced, _FunctionFrame)
+    assert advanced is not initial
+    assert advanced.index == 1
+    assert advanced.steps is body
+    assert (
+        advanced.local_bindings
+        is initial.local_bindings
+    )
+
+    advanced.local_bindings["local"] = 12
+
+    assert initial.local_bindings["local"] == 12
+    assert _frame_module(advanced) == "pkg"
+    assert _frame_position(advanced) == ("pkg", 1)
+
+
+def test_nested_calls_do_not_share_local_environment():
+    body = (_Step("PASS"),)
+
+    outer = _FunctionFrame("pkg", 0, body)
+    inner = _FunctionFrame("pkg", 0, body)
+
+    outer.local_bindings["x"] = 1
+    inner.local_bindings["x"] = 2
+
+    assert outer.local_bindings["x"] == 1
+    assert inner.local_bindings["x"] == 2
+
+    resumed = _advance_frame(outer)
+
+    assert resumed.local_bindings is outer.local_bindings
+    assert resumed.local_bindings is not inner.local_bindings
+
+
+def test_module_frame_does_not_acquire_function_locals():
+    module_frame = ("pkg", 4)
+
+    advanced = _advance_frame(module_frame)
+
+    assert advanced == ("pkg", 5)
+    assert type(advanced) is tuple
+
+
+def test_frame_equality_does_not_depend_on_mutable_locals():
+    body = (_Step("PASS"),)
+
+    first = _FunctionFrame("pkg", 0, body)
+    second = _FunctionFrame("pkg", 0, body)
+
+    assert first == second
+
+    first.local_bindings["x"] = 3
+
+    assert first == second
+    assert first.local_bindings is not second.local_bindings
```

## FINAL_VERDICT

- CONTRACT_PROVED for this bounded infrastructure change: each call frame has an independent local dictionary and advancement preserves it. Focused regressions and direct lifecycle assertions passed; no new model semantics were admitted. Canonical source is fresh, while cycle semantics and backend loaded-code adoption remain unverified. Stop after implementation and audit.
