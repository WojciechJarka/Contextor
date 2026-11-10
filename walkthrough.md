# P5-M08-I1 — Separate restricted function frames

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was used first. `_execute_restricted_call` resolved to `contextor/core/cycle_semantics/execution/calls.py:25-45`, canonical LIVE revision 1306, source fresh, `workspace_sync=verified`, cycle semantics stale. HEAD `32b20545a4ae687efb4960d6e53255959ec8eddc`; initial `git status --short` clean. Active backend executable: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M07-I2A identity object, M07-I2B counterexample tests and M08-T3 baseline were present. Required old mechanics matched `execution/state.py:30-41`, `execution/calls.py:25-45`, `package_model.py:1492,1578-1604,1661,1819,2164-2182,2282`, `execution/imports.py:92-177`, and `execution/lifecycle.py:6-49`.
- DIRECT_EVIDENCE: Repository-wide literal search found all package-import simulator frame readers/writers in those five modules. `initialization_model.py` and `guards.py` have independent frame structures and were not consumers of `_ExecutionCursor.frames`. No source drift in the requested anchors.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/state.py`
- `contextor/core/cycle_semantics/execution/calls.py`
- `contextor/core/cycle_semantics/execution/imports.py`
- `contextor/core/cycle_semantics/execution/lifecycle.py`
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (this report). No test file changed.

## FRAME_REPRESENTATION

- DIRECT_EVIDENCE: `execution/state.py:31-65` now defines frozen `_FunctionFrame(module,index,steps)` and `_frame_module`, `_frame_position`, `_advance_frame`. `_ExecutionCursor.frames` accepts module tuples or function frames; bootstrap remains `(bootstrap,0)` and budget remains 10000 (`:66-77`).
- DIRECT_EVIDENCE: Direct assertions passed for both frame kinds: module and position lookup, advancement preserving kind, body tuple identity, empty-body `()` as a valid call result, and foreign `_RestrictedFunction` returning `None`.

## CALL_EXECUTION_CHANGE

- DIRECT_EVIDENCE: `execution/calls.py:24-38` retains same-module `_RestrictedFunction` admission but returns its body tuple or `None`; there is no `programs` argument or mutation. `package_model.py:2176-2197` emits the same CALL_FUNCTION event, advances the suspended caller, pushes `_FunctionFrame(module,0,body)` and continues. A function frame reads its own immutable steps (`package_model.py:1582-1594`).
- CODE_PATH_PROVED: `body is None` alone causes UNKNOWN, so an empty tuple runs as an empty body. `_compile`, `_compile_reachable_prefix`, `_Step`, namespace binding, result shape and source session were not edited.

## IMPORT_SUSPENSION_AND_RESUMPTION

- DIRECT_EVIDENCE: `execution/imports.py:92-177` scans active module names through `_frame_module` for either frame kind. `execution/lifecycle.py:6-51` retains module-frame push/pop and READY/BIND_CHILD order, with only widened frame annotations. A direct evaluator assertion for `def f(): import pkg.child; f(); value=1` returned MODEL_PASS and observed `CALL_FUNCTION`, `START_IMPORT(pkg.child)`, child READY, BIND_CHILD, FUNCTION_LOCAL_IMPORT, then module BIND and module READY. The function completion itself emitted neither READY nor BIND_CHILD.
- CODE_PATH_PROVED: After an imported module frame pops, the suspended `_FunctionFrame` remains and resumes from its index. Function completion pops only that frame (`package_model.py:1596-1617`). The required focused import and cycle regressions passed.

## BUDGET_PARITY

- CODE_PATH_PROVED: The loop still decrements the 10000-step budget on each iteration (`package_model.py:1489-1493`). Completing a new function frame creates one bookkeeping iteration and refunds exactly one unit (`:1596-1600`). The old body-splice path had no such completion iteration; each body step remains charged. This is code-path parity for the bounded restricted bodies, not a claim about general Python calls.

## UNKNOWN_BOUNDARIES

- DIRECT_EVIDENCE: The helper still requires `_RestrictedFunction` with `defining_module == module`; other targets return `None` and evaluator returns UNKNOWN before a CALL_FUNCTION event (`execution/calls.py:29-38`; `package_model.py:2176-2186`). No parameters, return values, closures, decorators, foreign calls or new compiler steps were introduced.
- DIRECT_EVIDENCE: The separate M08-T3 baseline remained `7 passed`; all seven previously unsupported scenarios still assert UNKNOWN. The nine-file focused regression run passed and includes function identity, aliases, local imports, namespace prefix, passive definitions and GUI attestation.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Required nine-file regression command using the active backend venv: `366 passed, 2 warnings in 45.65s`. Both warnings were third-party Authlib deprecations. Separate M08-T3 command: `7 passed in 2.20s`.
- DIRECT_EVIDENCE: Direct frame integrity assertions A–K passed; output was `DIRECT_FRAME_INTEGRITY_PASS` with the observed event order above. `_compile.__module__` and evaluator `__module__` remain `contextor.core.cycle_semantics.package_model`.
- DIRECT_EVIDENCE: `git diff --check` exited 0; only LF→CRLF advisories were printed. No full pytest, SCC02, FULL, update_file, restart, Git add/commit/push, or index/history mutation.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Post-change canonical LIVE revision 1311: changed modules fresh with `workspace_sync=verified`; syntax errors 0; DFS structural cycle count 16; active warnings 16; cycle semantics stale. Cyclic SCC count was not provided. The stale semantic family cannot certify current warning classification or MODEL_PASS counts.
- DIRECT_EVIDENCE: Hard edges: `package_model → execution.calls`, `package_model → execution.state`, `package_model → execution.imports`, `package_model → execution.lifecycle`; `execution.calls → execution.steps`; `execution.imports → execution.state, execution.steps`; `execution.lifecycle → execution.state`; `execution.state → execution.class_facts, execution.steps`. No execution-module hard edge to `package_model` appeared in Contextor module-context responses. Source freshness does not prove loaded backend adoption.

## FULL_DIFFS

Complete actual changed-source diffs:

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index 80c23be..32965a1 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -1,7 +1,6 @@
 from __future__ import annotations

 from dataclasses import dataclass
-from typing import Literal

 from .steps import _Step

@@ -26,20 +25,14 @@ def _execute_restricted_call(
     step: _Step,
     *,
     module: str,
-    index: int,
     namespaces: dict[str, dict[str, object | None]],
-    programs: dict[str, list[_Step]],
-) -> Literal["ADVANCE", "RETURN_UNKNOWN"]:
+) -> tuple[_Step, ...] | None:
     value = namespaces[module].get(step.target)

     if (
         not isinstance(value, _RestrictedFunction)
         or value.defining_module != module
     ):
-        return "RETURN_UNKNOWN"
+        return None

-    programs[module][index + 1:index + 1] = list(
-        value.body
-    )
-
-    return "ADVANCE"
+    return value.body
diff --git a/contextor/core/cycle_semantics/execution/imports.py b/contextor/core/cycle_semantics/execution/imports.py
index 89f2a27..1b507ce 100644
--- a/contextor/core/cycle_semantics/execution/imports.py
+++ b/contextor/core/cycle_semantics/execution/imports.py
@@ -6,6 +6,7 @@ from typing import Mapping
 from typing import Literal

 from .steps import _Step
+from .state import _FunctionFrame, _frame_module


 def _chain(name: str) -> tuple[str, ...]:
@@ -96,7 +97,7 @@ def _execute_prepare_from_member(
     programs: Mapping[str, object],
     states: Mapping[str, str],
     namespaces: Mapping[str, dict[str, object | None]],
-    frames: list[tuple[str, int]],
+    frames: list[tuple[str, int] | _FunctionFrame],
 ) -> _ImportControl:
     target = step.target
     member = step.symbol
@@ -123,8 +124,8 @@ def _execute_prepare_from_member(

             if states[child] == "INITIALIZING":
                 if not any(
-                    active == child
-                    for active, _ in frames
+                    _frame_module(frame) == child
+                    for frame in frames
                 ):
                     return _ImportControl(
                         "RETURN_UNKNOWN",
@@ -152,7 +153,7 @@ def _resolve_from_child(
     programs: Mapping[str, object],
     states: Mapping[str, str],
     namespaces: Mapping[str, dict[str, object | None]],
-    frames: list[tuple[str, int]],
+    frames: list[tuple[str, int] | _FunctionFrame],
 ) -> _ImportControl:
     target = step.target
     member = step.symbol
@@ -163,8 +164,8 @@ def _resolve_from_child(
         if child in programs:
             if states[child] == "INITIALIZING":
                 if not any(
-                    active == child
-                    for active, _ in frames
+                    _frame_module(frame) == child
+                    for frame in frames
                 ):
                     return _ImportControl(
diff --git a/contextor/core/cycle_semantics/execution/lifecycle.py b/contextor/core/cycle_semantics/execution/lifecycle.py
index bf2ca0f..70a6d21 100644
--- a/contextor/core/cycle_semantics/execution/lifecycle.py
+++ b/contextor/core/cycle_semantics/execution/lifecycle.py
@@ -2,12 +2,14 @@ from __future__ import annotations

 from typing import Callable

+from .state import _FunctionFrame
+

 def _complete_module_frame(
     module: str,
     *,
     bootstrap: str,
-    frames: list[tuple[str, int]],
+    frames: list[tuple[str, int] | _FunctionFrame],
     states: dict[str, str],
     namespaces: dict[str, dict[str, object | None]],
     emit_event: Callable[
@@ -37,7 +39,7 @@ def _start_module_frame(
     target: str,
     *,
     importer: str,
-    frames: list[tuple[str, int]],
+    frames: list[tuple[str, int] | _FunctionFrame],
     states: dict[str, str],
     emit_event: Callable[
         [str, str, str | None, str | None],
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index a8c9bd7..4fbece6 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -4,6 +4,7 @@ from dataclasses import dataclass
 from typing import Mapping

 from .class_facts import _ClassFact, _BUILTIN_CLASS_FACTS
+from .steps import _Step


 @dataclass
@@ -27,9 +28,44 @@ def _new_module_initialization_state(
     )


+@dataclass(frozen=True)
+class _FunctionFrame:
+    module: str
+    index: int
+    steps: tuple[_Step, ...]
+
+
+def _frame_module(
+    frame: tuple[str, int] | _FunctionFrame,
+) -> str:
+    if isinstance(frame, _FunctionFrame):
+        return frame.module
+    return frame[0]
+
+
+def _frame_position(
+    frame: tuple[str, int] | _FunctionFrame,
+) -> tuple[str, int]:
+    if isinstance(frame, _FunctionFrame):
+        return frame.module, frame.index
+    return frame
+
+
+def _advance_frame(
+    frame: tuple[str, int] | _FunctionFrame,
+) -> tuple[str, int] | _FunctionFrame:
+    if isinstance(frame, _FunctionFrame):
+        return _FunctionFrame(
+            frame.module,
+            frame.index + 1,
+            frame.steps,
+        )
+    return (frame[0], frame[1] + 1)
+
+
 @dataclass
 class _ExecutionCursor:
-    frames: list[tuple[str, int]]
+    frames: list[tuple[str, int] | _FunctionFrame]
     step_budget: int


diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 19fe6df..41cb31a 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -46,6 +46,9 @@ from .execution.state import (
     _new_module_initialization_state,
     _new_execution_cursor,
     _new_definition_state,
+    _FunctionFrame,
+    _frame_position,
+    _advance_frame,
 )
 from .execution.imports import (
     _missing_piece,
@@ -1489,7 +1492,8 @@ def evaluate_package_import_order(
         if execution_cursor.step_budget < 0:
             return result("UNKNOWN")

-        module, index = frames[-1]
+        active_frame = frames[-1]
+        module, index = _frame_position(active_frame)

         if module in pending_programs:
             tree = logical_sources[module]
@@ -1576,29 +1580,37 @@ def evaluate_package_import_order(
             pending_programs.remove(module)

         steps = (
-            (_Step("IMPORT", entry_module, binding=None),)
-            if module == bootstrap
-            else programs[module]
+            active_frame.steps
+            if isinstance(active_frame, _FunctionFrame)
+            else (
+                (_Step("IMPORT", entry_module, binding=None),)
+                if module == bootstrap
+                else programs[module]
+            )
         )

         if index >= len(steps):
-            _complete_module_frame(
-                module,
-                bootstrap=bootstrap,
-                frames=frames,
-                states=states,
-                namespaces=namespaces,
-                emit_event=lambda event_module, operation, target, symbol: (
-                    events.append(
-                        PackageModelEvent(
-                            event_module,
-                            operation,
-                            target,
-                            symbol,
+            if isinstance(active_frame, _FunctionFrame):
+                frames.pop()
+                execution_cursor.step_budget += 1
+            else:
+                _complete_module_frame(
+                    module,
+                    bootstrap=bootstrap,
+                    frames=frames,
+                    states=states,
+                    namespaces=namespaces,
+                    emit_event=lambda event_module, operation, target, symbol: (
+                        events.append(
+                            PackageModelEvent(
+                                event_module,
+                                operation,
+                                target,
+                                symbol,
+                            )
                         )
-                    )
-                ),
-            )
+                    ),
+                )
             continue

         step = steps[index]
@@ -1658,7 +1670,7 @@ def evaluate_package_import_order(
                                 else ""
                             )
                         )
-                    frames[-1] = (module, index + 1)
+                    frames[-1] = _advance_frame(frames[-1])
                     continue
                 blocker = (
                     ReachedUnmodeledImport(
@@ -1816,7 +1828,7 @@ def evaluate_package_import_order(
                         )
                     )

-                    frames[-1] = (module, index + 1)
+                    frames[-1] = _advance_frame(frames[-1])
                     continue

                 if from_child_control.action == "START_CHILD":
@@ -2162,15 +2174,13 @@ def evaluate_package_import_order(
             )

         elif step.op == "CALL_FUNCTION":
-            call_control = _execute_restricted_call(
+            body = _execute_restricted_call(
                 step,
                 module=module,
-                index=index,
                 namespaces=namespaces,
-                programs=programs,
             )

-            if call_control == "RETURN_UNKNOWN":
+            if body is None:
                 return result("UNKNOWN", module, step.target)

             events.append(
@@ -2181,6 +2191,10 @@ def evaluate_package_import_order(
                 )
             )

+            frames[-1] = _advance_frame(frames[-1])
+            frames.append(_FunctionFrame(module, 0, body))
+            continue
+
         elif step.op == "BIND":
             if not step.class_local:
                 namespaces[module][step.binding] = None
@@ -2279,7 +2293,7 @@ def evaluate_package_import_order(
         else:
             return result("UNKNOWN")

-        frames[-1] = (module, index + 1)
+        frames[-1] = _advance_frame(frames[-1])

     return result("MODEL_PASS")

```

## FINAL_VERDICT

- CONTRACT_PROVED for this bounded structural change: restricted bodies now run in separate frames without program splicing; same-module admission, event order, import behavior and UNKNOWN boundaries passed focused regressions. Canonical source/graph evidence is fresh, while cycle semantics and loaded backend adoption remain unverified. Stop after implementation and audit.
