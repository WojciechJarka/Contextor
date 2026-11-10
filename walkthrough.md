# P5-M06-I6 — External import policy extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `f5980a8dd781e0b8d84e8fa7e1e59a5e349d29cd`; initial worktree clean. No Git index/history mutation by this task.
- DIRECT_EVIDENCE: Contextor LIVE revision 1287 before change; both target modules fresh with workspace_sync verified. Active backend venv executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.
- DIRECT_EVIDENCE: M06-I5 `_execute_from_binding` present unchanged (`execution/imports.py:205-257`). Common external-target branch matched the specified condition and subsequent evidence/binding/blocker flow (`package_model.py:1602-1668`). No SOURCE_DRIFT.
- CODE_PATH_PROVED: The extracted helper retains the same conjunctive admission condition and class-local rejection. It does not alter the pre-existing optional passive-external assumption; admission remains conditional, with unmodeled targets returning UNKNOWN under the original caller path.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/imports.py`
- `contextor/core/cycle_semantics/package_model.py`
- `walkthrough.md` (report only)

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: Appended exactly `_classify_external_import` in `execution/imports.py`; all existing functions and `_ImportControl` remain unchanged.
- DIRECT_EVIDENCE: `package_model.py` imports the helper and replaces only the admission conditional. The original assumption recording, event, namespace marker, frame advance, blocker construction and UNKNOWN result remain in place.

## EXTERNAL_POLICY_CHECKS

- DIRECT_EVIDENCE: All specified backend-venv assertions passed: external ASSUME only when enabled and outside bootstrap/indexed roots; class-local UNKNOWN_CLASS_LOCAL; function-local ASSUME; internal and unknown indexed-root UNKNOWN_UNMODELED; empty target UNKNOWN_UNMODELED; external FROM and PREPARE ASSUME; unchanged compiler/evaluator `__module__`.
- CODE_PATH_PROVED: `_classify_external_import` reads only its inputs and returns a three-way decision. It neither records an assumption nor mutates namespace, frames or events.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Requested focused pytest subset: 407 passed, 2 third-party deprecation warnings, 36.90 s. No SCC02 or full suite.
- DIRECT_EVIDENCE: `git diff --check` exit 0; only LF/CRLF advisory for `execution/imports.py`.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: LIVE revision 1289. Both changed modules canonical fresh with workspace_sync verified; module, graph, topology, cycles and lineage fresh. Project-level workspace_sync unverified.
- DIRECT_EVIDENCE: Hard edges remain `package_model -> execution.imports -> execution.steps`; no reverse `execution.imports -> package_model` edge.
- DIRECT_EVIDENCE: Syntax errors 0; structural DFS back-edge cycle count 16; active warnings 16. `cycle_semantics` stale, so current cyclic SCC count unavailable. No FULL, update_file or restart.
- UNKNOWN: Running backend adoption not proved by source freshness; direct checks used a new backend-venv interpreter.

## FULL_DIFFS

### contextor/core/cycle_semantics/execution/imports.py

```diff
diff --git a/contextor/core/cycle_semantics/execution/imports.py b/contextor/core/cycle_semantics/execution/imports.py
index fd469f3..89f2a27 100644
--- a/contextor/core/cycle_semantics/execution/imports.py
+++ b/contextor/core/cycle_semantics/execution/imports.py
@@ -255,3 +255,33 @@ def _execute_from_binding(
             else "FROM"
         ),
     )
+
+
+def _classify_external_import(
+    step: _Step,
+    *,
+    module: str,
+    bootstrap: str,
+    programs: Mapping[str, object],
+    indexed_roots: frozenset[str],
+    assume_passive_external_imports: bool,
+) -> Literal[
+    "ASSUME",
+    "UNKNOWN_CLASS_LOCAL",
+    "UNKNOWN_UNMODELED",
+]:
+    target = step.target
+
+    if (
+        assume_passive_external_imports
+        and target
+        and target not in programs
+        and module != bootstrap
+        and target.split(".", 1)[0] not in indexed_roots
+    ):
+        if step.class_local:
+            return "UNKNOWN_CLASS_LOCAL"
+
+        return "ASSUME"
+
+    return "UNKNOWN_UNMODELED"
```

### contextor/core/cycle_semantics/package_model.py

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index fa2124b..959db1c 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -53,6 +53,7 @@ from .execution.imports import (
     _execute_prepare_from_member,
     _resolve_from_child,
     _execute_from_binding,
+    _classify_external_import,
 )
 
 
@@ -1607,17 +1608,21 @@ def evaluate_package_import_order(
             target = step.target
 
             if not target or target not in programs:
-                if (
-                    _assume_passive_external_imports
-                    and target
-                    and target not in programs
-                    and module != bootstrap
-                    and target.split(".", 1)[0]
-                    not in indexed_roots
-                ):
-                    if step.class_local:
-                        return result("UNKNOWN", module, target)
+                external_decision = _classify_external_import(
+                    step,
+                    module=module,
+                    bootstrap=bootstrap,
+                    programs=programs,
+                    indexed_roots=indexed_roots,
+                    assume_passive_external_imports=(
+                        _assume_passive_external_imports
+                    ),
+                )
+
+                if external_decision == "UNKNOWN_CLASS_LOCAL":
+                    return result("UNKNOWN", module, target)
 
+                if external_decision == "ASSUME":
                     assumed_external_imports.append(
                         ReachedUnmodeledImport(
                             importer=module,
```

## FINAL_VERDICT

- CONTRACT_PROVED: Literal extraction, direct controls, focused regressions and diff check passed. Changed-file LIVE evidence fresh. Cycle semantics and running-backend adoption remain unverified; no runtime semantic certification is claimed.
