# P5-M06-I7 — Module frame completion extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `e8d5ad7f581886d62d9e8d7d3a34910ec4048f26`; initial worktree clean. No Git index/history mutation by this task.
- DIRECT_EVIDENCE: Contextor LIVE revision 1289 before change; `package_model.py` fresh, workspace_sync verified. Active backend executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: Exact completion block at `package_model.py:1577-1603` matched specification. `frames = execution_cursor.frames` at lines 1470-1472; per-invocation `states`/`namespaces` aliases at 1460-1462; per-invocation `events` at 1166. `execution/lifecycle.py` absent. No SOURCE_DRIFT.
- CODE_PATH_PROVED: The new helper preserves frame pop, READY state write, READY event, child binding and BIND_CHILD event order. Event callback is invoked synchronously during the helper call, without buffering.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/lifecycle.py` (new)
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (report only)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Created `execution/lifecycle.py` with exactly the supplied `_complete_module_frame` implementation.
- DIRECT_EVIDENCE: `package_model.py` imports the helper and replaces only the verified frame completion block with the specified synchronous event callback.

## LIFECYCLE_ORDER_CHECKS

- DIRECT_EVIDENCE: All specified backend-venv assertions passed. Child completion popped its frame before READY event, set READY before the event, bound the child only after READY event, then emitted BIND_CHILD. Parent completion emitted only READY. Bootstrap completion popped without state or event changes. Compiler/evaluator `__module__` unchanged.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Requested focused pytest subset: 410 passed, 2 third-party deprecation warnings, 41.23 s. No SCC02 or full suite.
- DIRECT_EVIDENCE: `git diff --check` exit 0 with no output.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1291. Both changed modules canonical fresh and workspace_sync verified; module, graph, topology, cycles and lineage fresh. Project-level workspace_sync unverified.
- DIRECT_EVIDENCE: New hard edge `package_model -> execution.lifecycle`; `execution.lifecycle` has zero outbound hard dependencies and no edge back to `package_model`.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16. `cycle_semantics` stale, so current cyclic SCC count unavailable. No FULL, update_file or restart.
- UNKNOWN: Running backend adoption not established by source freshness; direct checks used a new backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/lifecycle.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/lifecycle.py b/contextor/core/cycle_semantics/execution/lifecycle.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/execution/lifecycle.py
@@ -0,0 +1,33 @@
+from __future__ import annotations
+
+from typing import Callable
+
+
+def _complete_module_frame(
+    module: str,
+    *,
+    bootstrap: str,
+    frames: list[tuple[str, int]],
+    states: dict[str, str],
+    namespaces: dict[str, dict[str, object | None]],
+    emit_event: Callable[
+        [str, str, str | None, str | None],
+        None,
+    ],
+) -> None:
+    frames.pop()
+
+    if module != bootstrap:
+        states[module] = "READY"
+        emit_event(module, "READY", None, None)
+
+        if "." in module:
+            parent, child = module.rsplit(".", 1)
+            namespaces[parent][child] = module
+
+            emit_event(
+                parent,
+                "BIND_CHILD",
+                module,
+                child,
+            )
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 959db1c..b332b17 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -55,6 +55,7 @@ from .execution.imports import (
     _execute_from_binding,
     _classify_external_import,
 )
+from .execution.lifecycle import _complete_module_frame
 
 
 @dataclass(frozen=True)
@@ -1575,27 +1576,23 @@ def evaluate_package_import_order(
         )
 
         if index >= len(steps):
-            frames.pop()
-
-            if module != bootstrap:
-                states[module] = "READY"
-                events.append(
-                    PackageModelEvent(module, "READY")
-                )
-
-                if "." in module:
-                    parent, child = module.rsplit(".", 1)
-                    namespaces[parent][child] = module
-
+            _complete_module_frame(
+                module,
+                bootstrap=bootstrap,
+                frames=frames,
+                states=states,
+                namespaces=namespaces,
+                emit_event=lambda event_module, operation, target, symbol: (
                     events.append(
                         PackageModelEvent(
-                            parent,
-                            "BIND_CHILD",
-                            module,
-                            child,
+                            event_module,
+                            operation,
+                            target,
+                            symbol,
                         )
                     )
-
+                ),
+            )
             continue
 
         step = steps[index]
```

## FINAL_VERDICT

- CONTRACT_PROVED: Exact extraction, direct lifecycle checks, focused regressions and diff check passed. Changed-file LIVE evidence fresh. Cycle semantics and running-backend adoption remain unverified; no runtime semantic certification is claimed.
