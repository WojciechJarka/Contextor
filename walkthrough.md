# P5-M02 — BOUNDED INTEGER ARITHMETIC EXTRACTION

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `53f0b167ccaaae1744b3628aca15418d7f6423e1`; initial `git status --short` showed only `M walkthrough.md` (previous P5-M02 discovery report), disclosed before overwrite. Contextor pre-change canonical revision 1264, `package_model.py` canonical_state=fresh and workspace_sync=verified; cycle_semantics stale. Backend MCP PID 14072 executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.

DIRECT_EVIDENCE: Contextor `get_symbol_implementation` returned `_bounded_integer_arithmetic` at `package_model.py:640-714`, identical to requested complete function. Disk preflight: `execution/__init__.py` exists and length 0; `execution/steps.py` exists; `package_model.py:27` imports `_Step` from `.execution.steps`; `execution/expressions.py` absent. Existing `_pure_literal_expression` calls the helper through the `package_model` global name at pre-change line 753, and positive/negative arithmetic regressions already exist in `tests/test_cycle_semantics_package_model_literals.py:282-325`. No semantic broadening was authorized or performed.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/expressions.py` (new)
- `contextor/core/cycle_semantics/package_model.py` (exact import and original helper deletion)

`walkthrough.md` is the report only. No test edits.

## EXACT_IMPLEMENTATION

DIRECT_EVIDENCE: new `expressions.py` contains the exact supplied function and imports. `package_model.py` imports it immediately after the `_Step` import; the original definition and trailing separation were removed. `_pure_literal_expression`, `_safe_annassign`, `_pure_all_assignment`, `_compile`, callers and existing imports were not edited. The full file and source diff follow.

## COMPATIBILITY_RESULTS

DIRECT_EVIDENCE: all required backend-venv assertions passed. `package_model._bounded_integer_arithmetic is expressions._bounded_integer_arithmetic`; `_pure_literal_expression.__globals__["_bounded_integer_arithmetic"]` is that same object. `_pure_literal_expression`, `_safe_annassign` and `_compile` retain `__module__ == "contextor.core.cycle_semantics.package_model"`. New helper `__module__ == "contextor.core.cycle_semantics.execution.expressions"`.

CODE_PATH_PROVED: the helper's algorithm and caller lookup are unchanged in the checked source paths. UNKNOWN: arbitrary external introspection or pickle compatibility beyond the requested assertions is not certified.

## TARGETED_TEST_RESULTS

DIRECT_EVIDENCE: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_package_model_literals.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_passive_functions.py tests/test_cycle_semantics_passive_classes.py tests/test_cycle_semantics_decorator_definition_effects.py -rs` → **439 passed in 39.95s**. `git diff --check` exited 0 before report replacement; after report replacement it was rerun and remained clean except Git's line-ending advisory. No full suite.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: desktop_watcher UPDATED `execution/expressions.py` at canonical revision 1265 and `package_model.py` at 1266. At revision 1266, both changed files report workspace_sync=verified and canonical_state=fresh. LIVE syntax-error count 0; package_model outbound graph adds hard edge `contextor.core.cycle_semantics.package_model -> contextor.core.cycle_semantics.execution.expressions`, making its outbound total 6. Expressions module inbound edge is package_model; outbound total 0. Structural cycles remain 16 normalized DFS paths; active warnings 16, MODEL_PASS paths 0. `cycle_semantics=stale`; current cyclic SCC count and graph fingerprint were not available in queried projections (UNKNOWN). Static source freshness does not prove running MCP code adoption. No FULL, update_file, restart, commit or push.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/execution/expressions.py b/contextor/core/cycle_semantics/execution/expressions.py
new file mode 100644
--- /dev/null
+++ b/contextor/core/cycle_semantics/execution/expressions.py
@@ -0,0 +1,80 @@
+from __future__ import annotations
+
+import ast
+
+
+def _bounded_integer_arithmetic(
+    expression: ast.AST,
+    *,
+    depth: int,
+    node_budget: int,
+) -> tuple[bool, int]:
+    """Recognize bounded, exact built-in integer arithmetic only."""
+    used = 0
+
+    def calculate(
+        node: ast.AST,
+        node_depth: int,
+    ) -> int | None:
+        nonlocal used
+
+        if node_depth > 16 or used >= node_budget:
+            return None
+
+        used += 1
+
+        if type(node) is ast.Constant:
+            if type(node.value) is not int:
+                return None
+            value = node.value
+
+        elif type(node) is ast.UnaryOp:
+            if type(node.op) not in (ast.UAdd, ast.USub):
+                return None
+
+            operand = calculate(
+                node.operand,
+                node_depth + 1,
+            )
+            if operand is None:
+                return None
+
+            value = (
+                operand
+                if type(node.op) is ast.UAdd
+                else -operand
+            )
+
+        elif type(node) is ast.BinOp:
+            if type(node.op) not in (
+                ast.Add,
+                ast.Sub,
+                ast.Mult,
+            ):
+                return None
+
+            left = calculate(node.left, node_depth + 1)
+            if left is None:
+                return None
+
+            right = calculate(node.right, node_depth + 1)
+            if right is None:
+                return None
+
+            if type(node.op) is ast.Add:
+                value = left + right
+            elif type(node.op) is ast.Sub:
+                value = left - right
+            else:
+                value = left * right
+
+        else:
+            return None
+
+        if value.bit_length() > 64:
+            return None
+
+        return value
+
+    accepted = calculate(expression, depth) is not None
+    return accepted, used
```

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 0203d28..11d171c 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -25,6 +25,7 @@ from contextor.core.cycle_semantics.typing_guard import (
     recognize_typing_guard,
 )
 from .execution.steps import _Step
+from .execution.expressions import _bounded_integer_arithmetic


 @dataclass(frozen=True)
@@ -637,83 +638,6 @@ def _safe_passive_class_definition(
     return True


-def _bounded_integer_arithmetic(
-    expression: ast.AST,
-    *,
-    depth: int,
-    node_budget: int,
-) -> tuple[bool, int]:
-    """Recognize bounded, exact built-in integer arithmetic only."""
-    used = 0
-
-    def calculate(
-        node: ast.AST,
-        node_depth: int,
-    ) -> int | None:
-        nonlocal used
-
-        if node_depth > 16 or used >= node_budget:
-            return None
-
-        used += 1
-
-        if type(node) is ast.Constant:
-            if type(node.value) is not int:
-                return None
-            value = node.value
-
-        elif type(node) is ast.UnaryOp:
-            if type(node.op) not in (ast.UAdd, ast.USub):
-                return None
-
-            operand = calculate(
-                node.operand,
-                node_depth + 1,
-            )
-            if operand is None:
-                return None
-
-            value = (
-                operand
-                if type(node.op) is ast.UAdd
-                else -operand
-            )
-
-        elif type(node) is ast.BinOp:
-            if type(node.op) not in (
-                ast.Add,
-                ast.Sub,
-                ast.Mult,
-            ):
-                return None
-
-            left = calculate(node.left, node_depth + 1)
-            if left is None:
-                return None
-
-            right = calculate(node.right, node_depth + 1)
-            if right is None:
-                return None
-
-            if type(node.op) is ast.Add:
-                value = left + right
-            elif type(node.op) is ast.Sub:
-                value = left - right
-            else:
-                value = left * right
-
-        else:
-            return None
-
-        if value.bit_length() > 64:
-            return None
-
-        return value
-
-    accepted = calculate(expression, depth) is not None
-    return accepted, used
-
-
 def _pure_literal_expression(expr: ast.AST) -> bool:
     pending: list[tuple[ast.AST, int, bool]] = [
         (expr, 0, False)
```

## FINAL_VERDICT

TARGETED_SOURCE_AND_TEST_PASS. Exact extraction, compatibility assertions, focused regressions and watcher/source freshness at revision 1266 are verified. Cycle semantics remains stale, so no fresh semantic-classification or runtime-adoption claim is made.
