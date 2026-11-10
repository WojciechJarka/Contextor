# P5-M06-I5 — FROM symbol binding extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `de99c8431af26cd1efd13c3660654c530f554226`; initial worktree clean. No Git index/history mutation by this task.
- DIRECT_EVIDENCE: Contextor LIVE revision 1285 before change; both target modules fresh with workspace_sync verified. Active backend venv executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M06-I4 `_resolve_from_child` present unchanged (`execution/imports.py:145-199`). Ordinary FROM tail matched the exact specified anchor (`package_model.py:1818-1857`). No SOURCE_DRIFT.
- CODE_PATH_PROVED: The extracted helper retains missing-export classification, class-local admissibility, namespace write and event selection. The caller retains event-before-result ordering for failure and the common program-counter tail for success.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/imports.py`
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (report only)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Added `Callable`, `RETURN_OUTCOME`, `outcome` and the exact `_execute_from_binding` function to `execution/imports.py`. Existing functions remain unchanged.
- DIRECT_EVIDENCE: `package_model.py` imports the helper and replaces only the verified ordinary FROM tail. It passes the existing `_safe_class_namespace_value` predicate by reference.

## FROM_BINDING_CONTROL_CHECKS

- DIRECT_EVIDENCE: All specified backend-venv assertions passed: EARLY_BINDING_HAZARD, MISSING_EXPORT, ordinary FROM binding, function-local and class-local event selection without module binding, class-local UNKNOWN for inadmissible value, object identity of ordinary binding, and unchanged compiler/evaluator `__module__`.
- CODE_PATH_PROVED: Failure controls carry the same target/member and event/outcome names as the former branch. The helper writes `namespaces[module][step.binding]` only for ordinary non-local success.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Requested focused pytest subset: 407 passed, 2 third-party deprecation warnings, 50.19 s. No SCC02 or full suite.
- DIRECT_EVIDENCE: `git diff --check` exit 0; only LF/CRLF advisory for `execution/imports.py`.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1287. Both changed modules canonical fresh, workspace_sync verified; module, graph, topology, cycles and lineage fresh. Project-level workspace_sync unverified.
- DIRECT_EVIDENCE: Hard edges remain `package_model -> execution.imports -> execution.steps`; no reverse `execution.imports -> package_model` edge.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16. `cycle_semantics` stale; current cyclic SCC count unavailable. No FULL, update_file or restart.
- UNKNOWN: Running backend adoption not proved by source freshness; direct checks used a new backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/imports.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/imports.py b/contextor/core/cycle_semantics/execution/imports.py
index 707edf5..fd469f3 100644
--- a/contextor/core/cycle_semantics/execution/imports.py
+++ b/contextor/core/cycle_semantics/execution/imports.py
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 from dataclasses import dataclass
+from typing import Callable
 from typing import Mapping
 from typing import Literal
 
@@ -37,10 +38,12 @@ class _ImportControl:
         "RETURN_UNKNOWN",
         "START_CHILD",
         "REENTRANT_CHILD",
+        "RETURN_OUTCOME",
     ]
     target: str | None = None
     symbol: str | None = None
     event_operation: str | None = None
+    outcome: str | None = None
 
 
 def _execute_ready_import(
@@ -197,3 +200,58 @@ def _resolve_from_child(
             )
 
     return _ImportControl("ADVANCE")
+
+
+def _execute_from_binding(
+    step: _Step,
+    *,
+    module: str,
+    states: Mapping[str, str],
+    namespaces: dict[str, dict[str, object | None]],
+    class_namespace_admissible: Callable[[object], bool],
+) -> _ImportControl:
+    target = step.target
+    member = step.symbol
+
+    if member not in namespaces[target]:
+        outcome = (
+            "EARLY_BINDING_HAZARD"
+            if states[target] == "INITIALIZING"
+            else "MISSING_EXPORT"
+        )
+
+        return _ImportControl(
+            "RETURN_OUTCOME",
+            target=target,
+            symbol=member,
+            event_operation=outcome,
+            outcome=outcome,
+        )
+
+    imported_value = namespaces[target][member]
+
+    if (
+        step.class_local
+        and not class_namespace_admissible(imported_value)
+    ):
+        return _ImportControl(
+            "RETURN_UNKNOWN",
+            target=target,
+            symbol=member,
+        )
+
+    if not step.function_local and not step.class_local:
+        namespaces[module][step.binding] = imported_value
+
+    return _ImportControl(
+        "ADVANCE",
+        target=target,
+        symbol=member,
+        event_operation=(
+            "FUNCTION_LOCAL_FROM"
+            if step.function_local
+            else "CLASS_LOCAL_FROM"
+            if step.class_local
+            else "FROM"
+        ),
+    )
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index ae332e6..fa2124b 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -52,6 +52,7 @@ from .execution.imports import (
     _execute_ready_import,
     _execute_prepare_from_member,
     _resolve_from_child,
+    _execute_from_binding,
 )
 
 
@@ -1815,44 +1816,43 @@ def evaluate_package_import_order(
                     frames.append((child, 0))
                     continue
 
-                if member not in namespaces[target]:
-                    outcome = (
-                        "EARLY_BINDING_HAZARD"
-                        if states[target] == "INITIALIZING"
-                        else "MISSING_EXPORT"
+                from_binding_control = _execute_from_binding(
+                    step,
+                    module=module,
+                    states=states,
+                    namespaces=namespaces,
+                    class_namespace_admissible=(
+                        _safe_class_namespace_value
+                    ),
+                )
+
+                if from_binding_control.action == "RETURN_UNKNOWN":
+                    return result(
+                        "UNKNOWN",
+                        from_binding_control.target,
+                        from_binding_control.symbol,
                     )
 
+                if from_binding_control.action == "RETURN_OUTCOME":
                     events.append(
                         PackageModelEvent(
                             module,
-                            outcome,
+                            from_binding_control.event_operation,
                             target,
                             member,
                         )
                     )
 
-                    return result(outcome, target, member)
-
-                imported_value = namespaces[target][member]
-                if (
-                    step.class_local
-                    and not _safe_class_namespace_value(imported_value)
-                ):
-                    return result("UNKNOWN", target, member)
-
-                if not step.function_local and not step.class_local:
-                    namespaces[module][step.binding] = imported_value
+                    return result(
+                        from_binding_control.outcome,
+                        from_binding_control.target,
+                        from_binding_control.symbol,
+                    )
 
                 events.append(
                     PackageModelEvent(
                         module,
-                        (
-                            "FUNCTION_LOCAL_FROM"
-                            if step.function_local
-                            else "CLASS_LOCAL_FROM"
-                            if step.class_local
-                            else "FROM"
-                        ),
+                        from_binding_control.event_operation,
                         target,
                         member,
                     )
```

## FINAL_VERDICT

- CONTRACT_PROVED: Exact extraction, direct checks, focused regressions and diff check passed. Changed-file LIVE evidence fresh. Cycle semantics and running-backend adoption remain unverified, so no runtime semantic certification is claimed.
