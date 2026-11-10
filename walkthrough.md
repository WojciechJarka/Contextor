# P5-M06-I1 — Import chain resolution extraction

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD before and after: `68ec5c5e668440b4af47020a603d60e0c8282b9f`. Initial status: only ` M walkthrough.md` (pre-existing M06-D1 report). No Git index or history mutation was performed.
- DIRECT_EVIDENCE: Contextor LIVE pre-change revision 1277; `package_model.py` canonical state fresh, workspace_sync verified. Backend interpreter executable: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` (active backend PID 14072).
- DIRECT_EVIDENCE: `execution/imports.py` did not exist. `package_model.py:1466-1482` contained the exact specified nested definitions. The only calls were at old lines 1684, 1714, 1825. Repository search found no other `missing_piece` references in production or tests.
- CODE_PATH_PROVED: The extracted helper reads the same mutable `states` mapping at each of the same three call sites, in the same order, with the same comparisons and returns. It introduces no Contextor-specific branch or semantic assumption.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `contextor/core/cycle_semantics/execution/imports.py` (new)
- `walkthrough.md` (report only; overwritten as required)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Added `_chain` and `_missing_piece` to `execution/imports.py:1-26` exactly as specified.
- DIRECT_EVIDENCE: `package_model.py:50` imports `_missing_piece`; deleted only the nested `chain` and `missing_piece` definitions; updated the three calls to pass `states`.

## IMPORT_CHAIN_CHECKS

- DIRECT_EVIDENCE: Backend interpreter assertions passed: `package_model._missing_piece is execution.imports._missing_piece`; `_chain("a.b.c") == ("a", "a.b", "a.b.c")`; absent and NEW pieces return their first unresolved segment; INITIALIZING parent advances to child; fully READY chain returns `None`; `_compile` and `evaluate_package_import_order` retain `package_model` as `__module__`.
- CODE_PATH_PROVED: The helper does not mutate `states`; its only mapping operations are membership and lookup (`execution/imports.py:20-25`).

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Exact requested focused command using backend venv: 393 passed, 2 third-party deprecation warnings, 43.17 s. Files: `test_cycle_semantics_package_model.py`, `test_cycle_semantics_function_local_from.py`, `test_cycle_semantics_namespace_path_model.py`, `test_cycle_semantics_passive_classes.py`, `test_f1h_runtime_attestation.py`.
- DIRECT_EVIDENCE: `git diff --check` exit 0. Git emitted only an LF/CRLF advisory for `walkthrough.md`.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Canonical LIVE revision 1279. Both changed modules have canonical state fresh and workspace_sync verified; module, graph, topology, cycles and lineage fresh. Project-level workspace_sync is unverified, so file-level verification is the narrower evidence.
- DIRECT_EVIDENCE: `package_model -> execution.imports` is one hard dependency. `execution.imports` has zero outbound dependencies; specifically no reverse edge to `package_model`.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warning count 16; model pass count 0. Cyclic SCC count unavailable because `cycle_semantics` is stale. No FULL, update_file, or backend restart.
- UNKNOWN: Runtime process adoption of the changed source was not established by LIVE source freshness; importability was checked in a fresh backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/imports.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/imports.py b/contextor/core/cycle_semantics/execution/imports.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/execution/imports.py
@@ -0,0 +1,26 @@
+from __future__ import annotations
+
+from typing import Mapping
+
+
+def _chain(name: str) -> tuple[str, ...]:
+    parts = name.split(".")
+
+    return tuple(
+        ".".join(parts[:index])
+        for index in range(1, len(parts) + 1)
+    )
+
+
+def _missing_piece(
+    name: str,
+    states: Mapping[str, str],
+) -> str | None:
+    for piece in _chain(name):
+        if piece not in states:
+            return piece
+
+        if states[piece] == "NEW":
+            return piece
+
+    return None
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 00eb8df..6804430 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -47,6 +47,7 @@ from .execution.state import (
     _new_execution_cursor,
     _new_definition_state,
 )
+from .execution.imports import _missing_piece
 
 
 @dataclass(frozen=True)
@@ -1463,24 +1464,6 @@ def evaluate_package_import_order(
     execution_cursor = _new_execution_cursor(bootstrap)
     frames = execution_cursor.frames
 
-    def chain(name: str) -> tuple[str, ...]:
-        parts = name.split(".")
-
-        return tuple(
-            ".".join(parts[:index])
-            for index in range(1, len(parts) + 1)
-        )
-
-    def missing_piece(name: str) -> str | None:
-        for piece in chain(name):
-            if piece not in states:
-                return piece
-
-            if states[piece] == "NEW":
-                return piece
-
-        return None
-
     indexed_roots = frozenset(
         name.split(".", 1)[0]
         for name in programs
@@ -1681,7 +1664,7 @@ def evaluate_package_import_order(
                     reached_unmodeled_import=blocker,
                 )
 
-            next_piece = missing_piece(target)
+            next_piece = _missing_piece(target, states)
 
             if next_piece:
                 if next_piece not in programs:
@@ -1711,7 +1694,7 @@ def evaluate_package_import_order(
 
                     if child in programs:
                         if states[child] == "NEW":
-                            if missing_piece(child) != child:
+                            if _missing_piece(child, states) != child:
                                 return result("UNKNOWN", child, member)
 
                             states[child] = "INITIALIZING"
@@ -1822,7 +1805,7 @@ def evaluate_package_import_order(
                         if states[child] != "NEW":
                             return result("UNKNOWN", child, member)
 
-                        next_child = missing_piece(child)
+                        next_child = _missing_piece(child, states)
 
                         if next_child != child:
                             return result("UNKNOWN", child, member)
```

## FINAL_VERDICT

- CONTRACT_PROVED: Literal extraction completed; compatibility assertions, focused regressions, and diff check passed. Source-level LIVE audit is fresh for both changed modules. Cycle semantics remains stale and runtime adoption is UNKNOWN, so neither is claimed as certified.
