# P5-M06-I4 — FROM child resolution extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `840fdb8d042e98b9e7300d6b87138523bcb7c015`; initial worktree clean. No Git index/history mutation by this task.
- DIRECT_EVIDENCE: Contextor LIVE revision 1283 before change; `package_model.py` and `execution/imports.py` fresh with workspace_sync verified. Active backend executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` (PID 14072).
- DIRECT_EVIDENCE: M06-I3 `_execute_prepare_from_member` was present and unchanged (`execution/imports.py:88-141`). FROM child block matched the specified P5-M06-D1 sequence (`package_model.py:1756-1830`), including namespace precedence, active reentrant fallback, UNKNOWN conditions, NEW child start, and unchanged ordinary FROM tail.
- CODE_PATH_PROVED: The extracted helper makes the same read-only decisions; the evaluator still performs binding, event emission, frame advance or child start in the original order. No new semantic exception was introduced.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/imports.py`
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (report only)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Added `REENTRANT_CHILD` to `_ImportControl.action` and appended exactly `_resolve_from_child` in `execution/imports.py`. Existing functions remain unchanged.
- DIRECT_EVIDENCE: `package_model.py` imports the helper and replaces only FROM indexed-child resolution. The missing-export/early-binding, class-local safety, ordinary binding/event and common program-counter logic remain unchanged.

## FROM_CHILD_CONTROL_CHECKS

- DIRECT_EVIDENCE: All specified backend-venv assertions passed: NEW child START_CHILD with no mutation; inactive INITIALIZING UNKNOWN; active INITIALIZING REENTRANT_CHILD; READY UNKNOWN; existing namespace binding ADVANCE; NEW parent guard UNKNOWN; unchanged evaluator/compiler `__module__`.
- CODE_PATH_PROVED: `_resolve_from_child` only reads mappings and frames. The caller applies reentrant binding and event before frame advance, or INITIALIZING state and START_IMPORT event before child frame push.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Requested focused pytest subset: 407 passed, 2 third-party deprecation warnings, 43.68 s. No SCC02 or full suite.
- DIRECT_EVIDENCE: `git diff --check` exit 0; only LF/CRLF advisory for `execution/imports.py`.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1285. Both changed modules canonical fresh with workspace_sync verified; module, graph, topology, cycles and lineage fresh. Project-level workspace_sync unverified.
- DIRECT_EVIDENCE: Hard dependency edges remain `package_model -> execution.imports -> execution.steps`; `execution.imports` has no edge back to `package_model`.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16. `cycle_semantics` stale, so current cyclic SCC count unavailable. No FULL, update_file or restart.
- UNKNOWN: Running backend adoption not established by source freshness; direct checks used a new backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/imports.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/imports.py b/contextor/core/cycle_semantics/execution/imports.py
index aa92857..707edf5 100644
--- a/contextor/core/cycle_semantics/execution/imports.py
+++ b/contextor/core/cycle_semantics/execution/imports.py
@@ -36,6 +36,7 @@ class _ImportControl:
         "ADVANCE",
         "RETURN_UNKNOWN",
         "START_CHILD",
+        "REENTRANT_CHILD",
     ]
     target: str | None = None
     symbol: str | None = None
@@ -139,3 +140,60 @@ def _execute_prepare_from_member(
         "ADVANCE",
         event_operation="PREPARE_FROM_MEMBER",
     )
+
+
+def _resolve_from_child(
+    step: _Step,
+    *,
+    packages: set[str],
+    programs: Mapping[str, object],
+    states: Mapping[str, str],
+    namespaces: Mapping[str, dict[str, object | None]],
+    frames: list[tuple[str, int]],
+) -> _ImportControl:
+    target = step.target
+    member = step.symbol
+
+    if target in packages and member not in namespaces[target]:
+        child = target + "." + member
+
+        if child in programs:
+            if states[child] == "INITIALIZING":
+                if not any(
+                    active == child
+                    for active, _ in frames
+                ):
+                    return _ImportControl(
+                        "RETURN_UNKNOWN",
+                        target=child,
+                        symbol=member,
+                    )
+
+                return _ImportControl(
+                    "REENTRANT_CHILD",
+                    target=child,
+                    symbol=member,
+                )
+
+            if states[child] != "NEW":
+                return _ImportControl(
+                    "RETURN_UNKNOWN",
+                    target=child,
+                    symbol=member,
+                )
+
+            next_child = _missing_piece(child, states)
+
+            if next_child != child:
+                return _ImportControl(
+                    "RETURN_UNKNOWN",
+                    target=child,
+                    symbol=member,
+                )
+
+            return _ImportControl(
+                "START_CHILD",
+                target=child,
+            )
+
+    return _ImportControl("ADVANCE")
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 6b1de38..ae332e6 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -51,6 +51,7 @@ from .execution.imports import (
     _missing_piece,
     _execute_ready_import,
     _execute_prepare_from_member,
+    _resolve_from_child,
 )
 
 
@@ -1759,61 +1760,60 @@ def evaluate_package_import_order(
                 # CPython checks a package attribute before attempting
                 # to load a same-named child module. An existing binding
                 # takes precedence over the indexed child candidate.
-                if target in packages and member not in namespaces[target]:
-                    child = target + "." + member
-
-                    if child in programs:
-                        # CPython 3.10 IMPORT_FROM can fall back to sys.modules
-                        # for a child that has not yet been attached to its
-                        # parent package. Model only the active same-thread case.
-                        if states[child] == "INITIALIZING":
-                            if not any(
-                                active == child
-                                for active, _ in frames
-                            ):
-                                return result("UNKNOWN", child, member)
-
-                            if not step.function_local and not step.class_local:
-                                namespaces[module][step.binding] = child
-
-                            events.append(
-                                PackageModelEvent(
-                                    module,
-                                    (
-                                        "FUNCTION_LOCAL_FROM_REENTRANT_CHILD"
-                                        if step.function_local
-                                        else "CLASS_LOCAL_FROM_REENTRANT_CHILD"
-                                        if step.class_local
-                                        else "FROM_REENTRANT_CHILD"
-                                    ),
-                                    child,
-                                    member,
-                                )
-                            )
+                from_child_control = _resolve_from_child(
+                    step,
+                    packages=packages,
+                    programs=programs,
+                    states=states,
+                    namespaces=namespaces,
+                    frames=frames,
+                )
 
-                            frames[-1] = (module, index + 1)
-                            continue
+                if from_child_control.action == "RETURN_UNKNOWN":
+                    return result(
+                        "UNKNOWN",
+                        from_child_control.target,
+                        from_child_control.symbol,
+                    )
 
-                        if states[child] != "NEW":
-                            return result("UNKNOWN", child, member)
+                if from_child_control.action == "REENTRANT_CHILD":
+                    child = from_child_control.target
 
-                        next_child = _missing_piece(child, states)
+                    if not step.function_local and not step.class_local:
+                        namespaces[module][step.binding] = child
 
-                        if next_child != child:
-                            return result("UNKNOWN", child, member)
+                    events.append(
+                        PackageModelEvent(
+                            module,
+                            (
+                                "FUNCTION_LOCAL_FROM_REENTRANT_CHILD"
+                                if step.function_local
+                                else "CLASS_LOCAL_FROM_REENTRANT_CHILD"
+                                if step.class_local
+                                else "FROM_REENTRANT_CHILD"
+                            ),
+                            child,
+                            member,
+                        )
+                    )
+
+                    frames[-1] = (module, index + 1)
+                    continue
 
-                        states[child] = "INITIALIZING"
+                if from_child_control.action == "START_CHILD":
+                    child = from_child_control.target
+                    states[child] = "INITIALIZING"
 
-                        events.append(
-                            PackageModelEvent(
-                                module,
-                                "START_IMPORT",
-                                child,
-                            )
+                    events.append(
+                        PackageModelEvent(
+                            module,
+                            "START_IMPORT",
+                            child,
                         )
+                    )
 
-                        frames.append((child, 0))
-                        continue
+                    frames.append((child, 0))
+                    continue
 
                 if member not in namespaces[target]:
                     outcome = (
```

## FINAL_VERDICT

- CONTRACT_PROVED: Literal extraction, direct compatibility checks, focused regressions and diff check passed. Changed-file LIVE evidence fresh. Cycle semantics and running-backend adoption remain unverified and are not claimed as certified.
