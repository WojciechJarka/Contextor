# P5-M06-I8 — Module frame start extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `e1744d912458bb207e817941ca92afd34a7e68e0`; initial worktree clean. No Git index/history mutation by this task.
- DIRECT_EVIDENCE: Contextor LIVE revision 1291 before change; `package_model.py` and `execution/lifecycle.py` fresh with workspace_sync verified. Active backend venv executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M06-I7 `_complete_module_frame` matched accepted code (`execution/lifecycle.py:6-33`). Exactly three START_IMPORT state/event/frame sequences were found at `package_model.py:1678-1693, 1710-1727, 1805-1822`, each matching the specified anchors. No SOURCE_DRIFT.
- CODE_PATH_PROVED: All existing guards remain before each helper call. Each helper call writes INITIALIZING, invokes the event callback synchronously, then appends the child frame. Caller program counter remains unchanged on these retry paths.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/lifecycle.py`
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (report only)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Appended exactly `_start_module_frame` to `execution/lifecycle.py`; `_complete_module_frame` unchanged.
- DIRECT_EVIDENCE: `package_model.py` imports the helper and replaces only the three verified start sequences with the specified synchronous event callbacks.

## MODULE_START_ORDER_CHECKS

- DIRECT_EVIDENCE: All specified backend-venv assertions passed. START_IMPORT callback observed target INITIALIZING before child frame push, for regular and bootstrap importers. Existing completion helper still popped the child and emitted READY. Compiler/evaluator `__module__` unchanged.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Requested focused pytest subset: 424 passed, 2 third-party deprecation warnings, 46.16 s. No SCC02 or full suite.
- DIRECT_EVIDENCE: `git diff --check` exit 0; only LF/CRLF advisory for `execution/lifecycle.py`.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1293. Both changed modules canonical fresh with workspace_sync verified; module, graph, topology, cycles and lineage fresh. Project-level workspace_sync unverified.
- DIRECT_EVIDENCE: Hard edge `package_model -> execution.lifecycle`; lifecycle has zero outbound hard edges and no reverse dependency.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16. `cycle_semantics` stale, so current cyclic SCC count unavailable. No FULL, update_file or restart.
- UNKNOWN: Running backend adoption not established by source freshness; direct checks used a new backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/lifecycle.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/lifecycle.py b/contextor/core/cycle_semantics/execution/lifecycle.py
index c0d2e53..bf2ca0f 100644
--- a/contextor/core/cycle_semantics/execution/lifecycle.py
+++ b/contextor/core/cycle_semantics/execution/lifecycle.py
@@ -31,3 +31,19 @@ def _complete_module_frame(
                 module,
                 child,
             )
+
+
+def _start_module_frame(
+    target: str,
+    *,
+    importer: str,
+    frames: list[tuple[str, int]],
+    states: dict[str, str],
+    emit_event: Callable[
+        [str, str, str | None, str | None],
+        None,
+    ],
+) -> None:
+    states[target] = "INITIALIZING"
+    emit_event(importer, "START_IMPORT", target, None)
+    frames.append((target, 0))
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index b332b17..b8be4f1 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -55,7 +55,10 @@ from .execution.imports import (
     _execute_from_binding,
     _classify_external_import,
 )
-from .execution.lifecycle import _complete_module_frame
+from .execution.lifecycle import (
+    _complete_module_frame,
+    _start_module_frame,
+)
 
 
 @dataclass(frozen=True)
@@ -1678,17 +1681,22 @@ def evaluate_package_import_order(
                 if next_piece not in programs:
                     return result("UNKNOWN", next_piece)
 
-                states[next_piece] = "INITIALIZING"
-
-                events.append(
-                    PackageModelEvent(
-                        module,
-                        "START_IMPORT",
-                        next_piece,
-                    )
+                _start_module_frame(
+                    next_piece,
+                    importer=module,
+                    frames=frames,
+                    states=states,
+                    emit_event=lambda event_module, operation, target, symbol: (
+                        events.append(
+                            PackageModelEvent(
+                                event_module,
+                                operation,
+                                target,
+                                symbol,
+                            )
+                        )
+                    ),
                 )
-
-                frames.append((next_piece, 0))
                 continue
 
             if step.op == "PREPARE_FROM_MEMBER":
@@ -1710,17 +1718,22 @@ def evaluate_package_import_order(
 
                 if prepare_control.action == "START_CHILD":
                     child = prepare_control.target
-                    states[child] = "INITIALIZING"
-
-                    events.append(
-                        PackageModelEvent(
-                            module,
-                            "START_IMPORT",
-                            child,
-                        )
+                    _start_module_frame(
+                        child,
+                        importer=module,
+                        frames=frames,
+                        states=states,
+                        emit_event=lambda event_module, operation, target, symbol: (
+                            events.append(
+                                PackageModelEvent(
+                                    event_module,
+                                    operation,
+                                    target,
+                                    symbol,
+                                )
+                            )
+                        ),
                     )
-
-                    frames.append((child, 0))
                     continue
 
                 events.append(
@@ -1805,17 +1818,22 @@ def evaluate_package_import_order(
 
                 if from_child_control.action == "START_CHILD":
                     child = from_child_control.target
-                    states[child] = "INITIALIZING"
-
-                    events.append(
-                        PackageModelEvent(
-                            module,
-                            "START_IMPORT",
-                            child,
-                        )
+                    _start_module_frame(
+                        child,
+                        importer=module,
+                        frames=frames,
+                        states=states,
+                        emit_event=lambda event_module, operation, target, symbol: (
+                            events.append(
+                                PackageModelEvent(
+                                    event_module,
+                                    operation,
+                                    target,
+                                    symbol,
+                                )
+                            )
+                        ),
                     )
-
-                    frames.append((child, 0))
                     continue
 
                 from_binding_control = _execute_from_binding(
```

## FINAL_VERDICT

- CONTRACT_PROVED: Exact extraction, direct order checks, focused regressions and diff check passed. Changed-file LIVE evidence fresh. Cycle semantics and running-backend adoption remain unverified; no runtime semantic certification is claimed.
