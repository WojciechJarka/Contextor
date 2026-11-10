# P5-M06-I3 — PREPARE_FROM_MEMBER execution extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `48d3187a62896e13a45e90ed100e14aeb5fa479e`; initial worktree clean. No Git index/history commands were used.
- DIRECT_EVIDENCE: Contextor LIVE revision 1281 before change; `package_model.py` and `execution/imports.py` fresh with workspace_sync verified. Active backend venv executable: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: The existing M06-I2 `_execute_ready_import` and `_ImportControl` matched the accepted source (`execution/imports.py:31-81`). The `PREPARE_FROM_MEMBER` branch matched the specified text (`package_model.py:1689-1733`). No SOURCE_DRIFT.
- CODE_PATH_PROVED: The decision helper reads package, program, state, namespace and frame data without mutating them. The evaluator retains the ordered `INITIALIZING` state write, `START_IMPORT` event, child frame append and `continue`. The UNKNOWN and ADVANCE paths preserve their earlier result/event arguments.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/imports.py`
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (this report only)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Extended `_ImportControl.action` with `START_CHILD` and appended the specified `_execute_prepare_from_member` function. Existing functions were left intact.
- DIRECT_EVIDENCE: Added its import in `package_model.py` and replaced only the verified PREPARE_FROM_MEMBER branch. IMPORT, FROM and common import resolution were not edited.

## PREPARE_CONTROL_CHECKS

- DIRECT_EVIDENCE: All specified backend-venv assertions passed: NEW child returns START_CHILD without mutation; existing package binding advances; inactive INITIALIZING child returns UNKNOWN; active INITIALIZING child advances; READY child returns UNKNOWN. `_compile` and evaluator retain `package_model` as `__module__`.
- CODE_PATH_PROVED: The helper's `START_CHILD` is a decision only; it neither changes `states` nor `frames`. The evaluator performs these writes in their original order.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Exact requested focused pytest subset: 407 passed, 2 third-party deprecation warnings, 42.51 s. No SCC02 or full suite.
- DIRECT_EVIDENCE: `git diff --check` exit 0; only an LF/CRLF advisory for `execution/imports.py`.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Canonical LIVE revision 1283. Both changed modules fresh with workspace_sync verified; module, graph, topology, cycles and lineage fresh. Project-level workspace_sync unverified.
- DIRECT_EVIDENCE: `package_model -> execution.imports -> execution.steps` are the relevant hard edges; `execution.imports` has no reverse dependency on `package_model`.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16. `cycle_semantics` stale, so current cyclic SCC count unavailable. No FULL, update_file or restart.
- UNKNOWN: Running backend adoption is not established by source freshness. The behavior checks used a new backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/imports.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/imports.py b/contextor/core/cycle_semantics/execution/imports.py
index b41a624..aa92857 100644
--- a/contextor/core/cycle_semantics/execution/imports.py
+++ b/contextor/core/cycle_semantics/execution/imports.py
@@ -32,7 +32,11 @@ def _missing_piece(
 
 @dataclass(frozen=True)
 class _ImportControl:
-    action: Literal["ADVANCE", "RETURN_UNKNOWN"]
+    action: Literal[
+        "ADVANCE",
+        "RETURN_UNKNOWN",
+        "START_CHILD",
+    ]
     target: str | None = None
     symbol: str | None = None
     event_operation: str | None = None
@@ -79,3 +83,59 @@ def _execute_ready_import(
             else "IMPORT"
         ),
     )
+
+
+def _execute_prepare_from_member(
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
+    if (
+        target in packages
+        and member not in namespaces[target]
+    ):
+        child = target + "." + member
+
+        if child in programs:
+            if states[child] == "NEW":
+                if _missing_piece(child, states) != child:
+                    return _ImportControl(
+                        "RETURN_UNKNOWN",
+                        target=child,
+                        symbol=member,
+                    )
+
+                return _ImportControl(
+                    "START_CHILD",
+                    target=child,
+                )
+
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
+            elif states[child] == "READY":
+                return _ImportControl(
+                    "RETURN_UNKNOWN",
+                    target=child,
+                    symbol=member,
+                )
+
+    return _ImportControl(
+        "ADVANCE",
+        event_operation="PREPARE_FROM_MEMBER",
+    )
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index b98dad9..6b1de38 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -50,6 +50,7 @@ from .execution.state import (
 from .execution.imports import (
     _missing_piece,
     _execute_ready_import,
+    _execute_prepare_from_member,
 )
 
 
@@ -1687,48 +1688,43 @@ def evaluate_package_import_order(
                 continue
 
             if step.op == "PREPARE_FROM_MEMBER":
-                member = step.symbol
-
-                if (
-                    target in packages
-                    and member not in namespaces[target]
-                ):
-                    child = target + "." + member
-
-                    if child in programs:
-                        if states[child] == "NEW":
-                            if _missing_piece(child, states) != child:
-                                return result("UNKNOWN", child, member)
-
-                            states[child] = "INITIALIZING"
+                prepare_control = _execute_prepare_from_member(
+                    step,
+                    packages=packages,
+                    programs=programs,
+                    states=states,
+                    namespaces=namespaces,
+                    frames=frames,
+                )
 
-                            events.append(
-                                PackageModelEvent(
-                                    module,
-                                    "START_IMPORT",
-                                    child,
-                                )
-                            )
+                if prepare_control.action == "RETURN_UNKNOWN":
+                    return result(
+                        "UNKNOWN",
+                        prepare_control.target,
+                        prepare_control.symbol,
+                    )
 
-                            frames.append((child, 0))
-                            continue
+                if prepare_control.action == "START_CHILD":
+                    child = prepare_control.target
+                    states[child] = "INITIALIZING"
 
-                        if states[child] == "INITIALIZING":
-                            if not any(
-                                active == child
-                                for active, _ in frames
-                            ):
-                                return result("UNKNOWN", child, member)
+                    events.append(
+                        PackageModelEvent(
+                            module,
+                            "START_IMPORT",
+                            child,
+                        )
+                    )
 
-                        elif states[child] == "READY":
-                            return result("UNKNOWN", child, member)
+                    frames.append((child, 0))
+                    continue
 
                 events.append(
                     PackageModelEvent(
                         module,
                         "PREPARE_FROM_MEMBER",
                         target,
-                        member,
+                        step.symbol,
                     )
                 )
 
```

## FINAL_VERDICT

- CONTRACT_PROVED: Exact extraction, direct compatibility checks, focused regressions and diff check passed. Changed-file LIVE evidence is fresh. Cycle semantics and running-backend adoption remain unverified and are not claimed as certified.
