# P5-M06-I2 — Ready import operation extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `e3bd0648a511b8cbce6141189d11a1c8142d812f`; initial worktree clean. No Git index or history mutation by this task.
- DIRECT_EVIDENCE: Contextor canonical LIVE revision 1279; `package_model.py` fresh, workspace_sync verified. Active backend executable: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` (PID 14072).
- DIRECT_EVIDENCE: `execution/imports.py:1-26` retained the accepted M06-I1 implementation. `package_model.py:1732-1763` matched the specified IMPORT branch verbatim. No source drift.
- CODE_PATH_PROVED: The extracted operation preserves the same check for dotted explicit aliases, namespace assignment condition, event kind, and UNKNOWN result arguments. The common evaluator target resolution and frame-index advancement remain outside this branch. This extraction adds no semantic rule or Contextor-specific exception.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/imports.py`
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (report only; overwritten)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Added `_ImportControl` and `_execute_ready_import` to `execution/imports.py:31-81`; existing `_chain` and `_missing_piece` remain unchanged.
- DIRECT_EVIDENCE: `package_model.py:50-53` imports the new helper; the ready IMPORT branch delegates to it, returns UNKNOWN on `RETURN_UNKNOWN`, and appends the same `PackageModelEvent` on advance.

## IMPORT_CONTROL_CHECKS

- DIRECT_EVIDENCE: All specified backend-venv assertions passed: explicit dotted alias binding, missing parent binding UNKNOWN with no consumer mutation, bootstrap advance with no event, function-local and class-local events without module binding, and unchanged `__module__` for `_compile` and `evaluate_package_import_order`.
- CODE_PATH_PROVED: `execution/imports.py:49-81` reads the same `step` fields and namespace entries as the old branch; the evaluator appends the event only after the helper returns advance.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Exact requested focused pytest subset passed: 410 passed, 2 third-party deprecation warnings, 43.97 s. No SCC02 or full suite run.
- DIRECT_EVIDENCE: `git diff --check` exit 0; only an LF/CRLF advisory for `execution/imports.py`.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1281. Both changed modules have canonical state fresh and workspace_sync verified. Module, graph, topology, cycles and lineage fresh. Project-level workspace_sync remains unverified.
- DIRECT_EVIDENCE: Hard dependency edges: `package_model -> execution.imports -> execution.steps`. `execution.imports` has no outbound hard edge to `package_model`.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16. `cycle_semantics` is stale; current cyclic SCC count is unavailable. No FULL, update_file or restart.
- UNKNOWN: LIVE source freshness does not attest adoption by the already-running backend; importability and behavior were checked in a new backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/imports.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/imports.py b/contextor/core/cycle_semantics/execution/imports.py
index c422b8c..b41a624 100644
--- a/contextor/core/cycle_semantics/execution/imports.py
+++ b/contextor/core/cycle_semantics/execution/imports.py
@@ -1,6 +1,10 @@
 from __future__ import annotations
 
+from dataclasses import dataclass
 from typing import Mapping
+from typing import Literal
+
+from .steps import _Step
 
 
 def _chain(name: str) -> tuple[str, ...]:
@@ -24,3 +28,54 @@ def _missing_piece(
             return piece
 
     return None
+
+
+@dataclass(frozen=True)
+class _ImportControl:
+    action: Literal["ADVANCE", "RETURN_UNKNOWN"]
+    target: str | None = None
+    symbol: str | None = None
+    event_operation: str | None = None
+
+
+def _execute_ready_import(
+    step: _Step,
+    *,
+    module: str,
+    bootstrap: str,
+    namespaces: dict[str, dict[str, object | None]],
+) -> _ImportControl:
+    target = step.target
+
+    if module == bootstrap:
+        return _ImportControl("ADVANCE")
+
+    if step.explicit_alias and "." in target:
+        parent, child = target.rsplit(".", 1)
+
+        if namespaces[parent].get(child) != target:
+            return _ImportControl(
+                "RETURN_UNKNOWN",
+                target=target,
+                symbol=child,
+            )
+
+    binding_target = (
+        target
+        if step.explicit_alias
+        else target.split(".")[0]
+    )
+
+    if not step.function_local and not step.class_local:
+        namespaces[module][step.binding] = binding_target
+
+    return _ImportControl(
+        "ADVANCE",
+        event_operation=(
+            "FUNCTION_LOCAL_IMPORT"
+            if step.function_local
+            else "CLASS_LOCAL_IMPORT"
+            if step.class_local
+            else "IMPORT"
+        ),
+    )
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 6804430..b98dad9 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -47,7 +47,10 @@ from .execution.state import (
     _new_execution_cursor,
     _new_definition_state,
 )
-from .execution.imports import _missing_piece
+from .execution.imports import (
+    _missing_piece,
+    _execute_ready_import,
+)
 
 
 @dataclass(frozen=True)
@@ -1730,32 +1733,25 @@ def evaluate_package_import_order(
                 )
 
             elif step.op == "IMPORT":
-                if module != bootstrap:
-                    if step.explicit_alias and "." in target:
-                        parent, child = target.rsplit(".", 1)
-
-                        if namespaces[parent].get(child) != target:
-                            return result("UNKNOWN", target, child)
+                import_control = _execute_ready_import(
+                    step,
+                    module=module,
+                    bootstrap=bootstrap,
+                    namespaces=namespaces,
+                )
 
-                    binding_target = (
-                        target
-                        if step.explicit_alias
-                        else target.split(".")[0]
+                if import_control.action == "RETURN_UNKNOWN":
+                    return result(
+                        "UNKNOWN",
+                        import_control.target,
+                        import_control.symbol,
                     )
 
-                    if not step.function_local and not step.class_local:
-                        namespaces[module][step.binding] = binding_target
-
+                if import_control.event_operation is not None:
                     events.append(
                         PackageModelEvent(
                             module,
-                            (
-                                "FUNCTION_LOCAL_IMPORT"
-                                if step.function_local
-                                else "CLASS_LOCAL_IMPORT"
-                                if step.class_local
-                                else "IMPORT"
-                            ),
+                            import_control.event_operation,
                             target,
                             step.binding,
                         )
```

## FINAL_VERDICT

- CONTRACT_PROVED: Exact extraction completed; direct compatibility checks, targeted tests and diff check passed. Source-level LIVE audit is fresh for both changed modules. Current cycle semantics and running-backend adoption remain unverified, so no runtime semantic certification is claimed.
