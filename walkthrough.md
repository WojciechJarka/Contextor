# P5-M07-I1 — Restricted call execution extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `59caae34dc8edd0f817e1ef0b25daf23aed3fae3`; initial `git status --short` showed only ` M walkthrough.md` (pre-existing M07-D1 report, overwritten as requested). No Git index/history mutation by this task.
- DIRECT_EVIDENCE: Contextor LIVE revision 1293 before change; `package_model.py` canonical fresh and workspace_sync verified. Active backend executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`. `execution/calls.py` did not exist.
- DIRECT_EVIDENCE: The CALL_FUNCTION branch at `package_model.py:2162-2196` matched the specified marker check, UNKNOWN result, tuple body lookup, list splice, and event ordering. `programs[name] = list(program)` at 1422 and 1572; function body tuple stored at 1881-1884; shared frame advance at 2295. `_Step` imported from `execution.steps`. No SOURCE_DRIFT.
- CODE_PATH_PROVED: The helper preserves exact marker matching and splice location. It does not emit events; the evaluator still emits CALL_FUNCTION after successful insertion and before shared frame increment. No alias, argument or decorator behavior is added.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/calls.py` (new)
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (report only)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Created `execution/calls.py` with the exact supplied `_execute_restricted_call` implementation.
- DIRECT_EVIDENCE: `package_model.py` imports that helper and replaces only the CALL_FUNCTION branch's marker check and program splice. Event emission and common frame increment remain in the evaluator.

## CALL_EXECUTION_CHECKS

- DIRECT_EVIDENCE: All specified backend-venv assertions passed: successful splice after call step, stored tuple identity preserved, repeated insertion without tuple mutation, aliased call UNKNOWN without program change, rebound original UNKNOWN without program change, and unchanged compiler/evaluator `__module__`.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Requested focused pytest subset: 285 passed, 2 third-party deprecation warnings, 27.22 s. No SCC02 or full suite.
- DIRECT_EVIDENCE: `git diff --check` exit 0; only an LF/CRLF advisory for `walkthrough.md`.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1295. Both changed modules canonical fresh and workspace_sync verified; module, graph, topology, cycles and lineage fresh. Project-level workspace_sync unverified.
- DIRECT_EVIDENCE: New hard edge `package_model -> execution.calls`; calls has one outbound edge to `execution.steps` and none back to `package_model`.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16. `cycle_semantics` stale, so current cyclic SCC count unavailable. No FULL, update_file or restart.
- UNKNOWN: Running backend adoption not established by source freshness; direct checks used a new backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/calls.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -0,0 +1,35 @@
+from __future__ import annotations
+
+from typing import Literal
+
+from .steps import _Step
+
+
+def _execute_restricted_call(
+    step: _Step,
+    *,
+    module: str,
+    index: int,
+    namespaces: dict[str, dict[str, object | None]],
+    function_definitions: dict[
+        str,
+        dict[str, tuple[_Step, ...]],
+    ],
+    programs: dict[str, list[_Step]],
+) -> Literal["ADVANCE", "RETURN_UNKNOWN"]:
+    expected_binding = (
+        "\x00FUNCTION:" + module + ":" + step.target
+    )
+
+    if (
+        namespaces[module].get(step.target)
+        != expected_binding
+        or step.target not in function_definitions[module]
+    ):
+        return "RETURN_UNKNOWN"
+
+    body_steps = function_definitions[module][step.target]
+
+    programs[module][index + 1:index + 1] = list(body_steps)
+
+    return "ADVANCE"
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index b8be4f1..d8249f5 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -59,6 +59,7 @@ from .execution.lifecycle import (
     _complete_module_frame,
     _start_module_frame,
 )
+from .execution.calls import _execute_restricted_call
 
 
 @dataclass(frozen=True)
@@ -2160,31 +2161,17 @@ def evaluate_package_import_order(
             )
 
         elif step.op == "CALL_FUNCTION":
-            expected_binding = (
-                "\x00FUNCTION:" + module + ":" + step.target
+            call_control = _execute_restricted_call(
+                step,
+                module=module,
+                index=index,
+                namespaces=namespaces,
+                function_definitions=function_definitions,
+                programs=programs,
             )
 
-            if (
-                namespaces[module].get(step.target)
-                != expected_binding
-                or step.target
-                not in function_definitions[module]
-            ):
-                return result(
-                    "UNKNOWN",
-                    module,
-                    step.target,
-                )
-
-            # Expand the function's restricted import-only body
-            # at its actual call site. This changes only the
-            # in-memory compiled execution sequence, never
-            # caller AST or source bytes.
-            body_steps = function_definitions[module][step.target]
-
-            programs[module][
-                index + 1:index + 1
-            ] = list(body_steps)
+            if call_control == "RETURN_UNKNOWN":
+                return result("UNKNOWN", module, step.target)
 
             events.append(
                 PackageModelEvent(
```

## FINAL_VERDICT

- CONTRACT_PROVED: Exact extraction, direct controls, focused regressions and diff check passed. Changed-file LIVE evidence fresh. Cycle semantics and running-backend adoption remain unverified; no runtime semantic certification is claimed.
