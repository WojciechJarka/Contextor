# P5-M03 — EXPRESSION PREDICATES EXTRACTION

## PREFLIGHT

DIRECT_EVIDENCE: HEAD `d0e94e0398f31ad9aecc8d847ac25fc85e31e142`; initial `git status --short` clean. Canonical LIVE revision 1266 before edits; Contextor `get_symbol_implementation` returned `_pure_literal_expression` at `package_model.py:641-738` and `_safe_annassign` at 753-768, both workspace_sync=verified. `_bounded_integer_arithmetic` resolved in `execution/expressions.py:6-80`, workspace_sync=verified. Backend MCP PID 14072 executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`.

CODE_PATH_PROVED: source definitions match the preceding P5-M02 discovery content; their line numbers shifted after the bounded helper extraction. Dependency chain verified in current source: `_safe_annassign -> _pure_literal_expression -> _bounded_integer_arithmetic` (`package_model.py:767,677`). The existing `_bounded_integer_arithmetic` implementation was not edited. Before editing, `package_model.py:28` contained exactly `from .execution.expressions import _bounded_integer_arithmetic`. No unrelated worktree modification pre-existed. Positive/negative literal, arithmetic, annotation and class/function regressions were identified in the previous discovery; this is a structural move with no new acceptance path.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/expressions.py`
- `contextor/core/cycle_semantics/package_model.py`

`walkthrough.md` is the overwritten report only. No test or other source file changed.

## EXACT_IMPLEMENTATION

DIRECT_EVIDENCE: the complete two existing definitions were copied to `execution/expressions.py` after `_bounded_integer_arithmetic`, in the requested order and with two blank lines between module-level definitions. `package_model.py` now imports all three names in the requested parenthesized form and no longer defines the two relocated predicates. `_pure_all_assignment`, `_safe_passive_class_definition`, `_compile`, evaluator branches, result/event types and public evaluators were not edited. The full actual changed-source diffs are below.

## COMPATIBILITY_RESULTS

DIRECT_EVIDENCE: backend-venv assertions passed for all three `package_model` aliases being identical to `expressions` functions; `expressions._pure_literal_expression.__globals__["_bounded_integer_arithmetic"]` resolves to the exported helper; `expressions._safe_annassign.__globals__["_pure_literal_expression"]` resolves to the exported predicate. `package_model._compile.__module__` and `evaluate_package_import_order.__module__` remain `contextor.core.cycle_semantics.package_model`.

DIRECT_EVIDENCE: both relocated functions report `__module__ = contextor.core.cycle_semantics.execution.expressions` and `__globals__["__name__"] = contextor.core.cycle_semantics.execution.expressions`. No manual identity or metadata override was applied. UNKNOWN: compatibility of arbitrary external reflection/monkeypatching beyond these checks is not certified.

## TARGETED_TEST_RESULTS

DIRECT_EVIDENCE: `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_package_model_literals.py tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_passive_functions.py tests/test_cycle_semantics_passive_classes.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_cycle_semantics_namespace_path_model.py -rs` → **506 passed in 37.08s**. `git diff --check` exited 0; only a Git line-ending advisory appeared. No full pytest.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: desktop_watcher UPDATED `execution/expressions.py` at revision 1267 and `package_model.py` at revision 1268. Contextor `get_module_context` at canonical LIVE revision 1268 reports workspace_sync=verified for both changed files; canonical_state=fresh; syntax errors 0. The existing hard dependency `package_model -> execution.expressions` remains, with package_model outbound total 6 and expressions outbound total 0; no newly distinct module edge was observed. Structural diagnostic count remains 16 normalized DFS paths, active warnings 16, MODEL_PASS paths 0. `cycle_semantics=stale`. Cyclic SCC count was not available in the queried fresh projection. Static freshness does not prove running MCP code adoption. No FULL, update_file, restart, commit or push.

## FULL_DIFFS

```diff
warning: in the working copy of 'contextor/core/cycle_semantics/execution/expressions.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/cycle_semantics/execution/expressions.py b/contextor/core/cycle_semantics/execution/expressions.py
index 5357893..57daf1f 100644
--- a/contextor/core/cycle_semantics/execution/expressions.py
+++ b/contextor/core/cycle_semantics/execution/expressions.py
@@ -78,3 +78,121 @@ def _bounded_integer_arithmetic(

     accepted = calculate(expression, depth) is not None
     return accepted, used
+
+
+def _pure_literal_expression(expr: ast.AST) -> bool:
+    pending: list[tuple[ast.AST, int, bool]] = [
+        (expr, 0, False)
+    ]
+    visited = 0
+
+    while pending:
+        node, depth, hashable_required = pending.pop()
+        visited += 1
+
+        if visited > 256 or depth > 16:
+            return False
+
+        if type(node) is ast.Constant:
+            if type(node.value) not in {
+                type(None), bool, int, float,
+                complex, str, bytes,
+            }:
+                return False
+            continue
+
+        if type(node) is ast.UnaryOp:
+            if (
+                type(node.op) not in (ast.UAdd, ast.USub)
+                or type(node.operand) is not ast.Constant
+                or type(node.operand.value)
+                not in (int, float, complex)
+            ):
+                return False
+
+            pending.append(
+                (node.operand, depth + 1, hashable_required)
+            )
+            continue
+
+        if type(node) is ast.BinOp:
+            accepted, counted = _bounded_integer_arithmetic(
+                node,
+                depth=depth,
+                node_budget=257 - visited,
+            )
+
+            visited += counted - 1
+
+            if not accepted or visited > 256:
+                return False
+
+            continue
+
+        if type(node) is ast.Tuple:
+            pending.extend(
+                (item, depth + 1, hashable_required)
+                for item in reversed(node.elts)
+            )
+            continue
+
+        if type(node) is ast.List:
+            if hashable_required:
+                return False
+
+            pending.extend(
+                (item, depth + 1, False)
+                for item in reversed(node.elts)
+            )
+            continue
+
+        if type(node) is ast.Set:
+            if hashable_required:
+                return False
+
+            pending.extend(
+                (item, depth + 1, True)
+                for item in reversed(node.elts)
+            )
+            continue
+
+        if type(node) is ast.Dict:
+            if (
+                hashable_required
+                or len(node.keys) != len(node.values)
+                or any(key is None for key in node.keys)
+            ):
+                return False
+
+            for key, value in reversed(
+                list(zip(node.keys, node.values))
+            ):
+                pending.append(
+                    (value, depth + 1, False)
+                )
+                pending.append(
+                    (key, depth + 1, True)
+                )
+            continue
+
+        return False
+
+    return True
+
+
+def _safe_annassign(
+    statement: ast.AnnAssign,
+    annotation_semantics: str | None,
+) -> bool:
+    if (
+        annotation_semantics not in {"DEFERRED", "STRINGIFIED"}
+        or not isinstance(statement.target, ast.Name)
+        or statement.simple != 1
+        or not statement.target.id.isidentifier()
+        or statement.target.id.startswith("__")
+    ):
+        return False
+    return (
+        statement.value is None
+        or _pure_literal_expression(statement.value)
+    )
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 11d171c..4ab403a 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -25,7 +25,11 @@ from contextor.core.cycle_semantics.typing_guard import (
     recognize_typing_guard,
 )
 from .execution.steps import _Step
-from .execution.expressions import _bounded_integer_arithmetic
+from .execution.expressions import (
+    _bounded_integer_arithmetic,
+    _pure_literal_expression,
+    _safe_annassign,
+)


 @dataclass(frozen=True)
@@ -638,106 +642,6 @@ def _safe_passive_class_definition(
     return True


-def _pure_literal_expression(expr: ast.AST) -> bool:
-    pending: list[tuple[ast.AST, int, bool]] = [
-        (expr, 0, False)
-    ]
-    visited = 0
-
-    while pending:
-        node, depth, hashable_required = pending.pop()
-        visited += 1
-
-        if visited > 256 or depth > 16:
-            return False
-
-        if type(node) is ast.Constant:
-            if type(node.value) not in {
-                type(None), bool, int, float,
-                complex, str, bytes,
-            }:
-                return False
-            continue
-
-        if type(node) is ast.UnaryOp:
-            if (
-                type(node.op) not in (ast.UAdd, ast.USub)
-                or type(node.operand) is not ast.Constant
-                or type(node.operand.value)
-                not in (int, float, complex)
-            ):
-                return False
-
-            pending.append(
-                (node.operand, depth + 1, hashable_required)
-            )
-            continue
-
-        if type(node) is ast.BinOp:
-            accepted, counted = _bounded_integer_arithmetic(
-                node,
-                depth=depth,
-                node_budget=257 - visited,
-            )
-
-            visited += counted - 1
-
-            if not accepted or visited > 256:
-                return False
-
-            continue
-
-        if type(node) is ast.Tuple:
-            pending.extend(
-                (item, depth + 1, hashable_required)
-                for item in reversed(node.elts)
-            )
-            continue
-
-        if type(node) is ast.List:
-            if hashable_required:
-                return False
-
-            pending.extend(
-                (item, depth + 1, False)
-                for item in reversed(node.elts)
-            )
-            continue
-
-        if type(node) is ast.Set:
-            if hashable_required:
-                return False
-
-            pending.extend(
-                (item, depth + 1, True)
-                for item in reversed(node.elts)
-            )
-            continue
-
-        if type(node) is ast.Dict:
-            if (
-                hashable_required
-                or len(node.keys) != len(node.values)
-                or any(key is None for key in node.keys)
-            ):
-                return False
-
-            for key, value in reversed(
-                list(zip(node.keys, node.values))
-            ):
-                pending.append(
-                    (value, depth + 1, False)
-                )
-                pending.append(
-                    (key, depth + 1, True)
-                )
-            continue
-
-        return False
-
-    return True
-
-
 def _pure_all_assignment(value: ast.AST) -> bool:
     return (
         type(value) in (ast.List, ast.Tuple)
@@ -750,24 +654,6 @@ def _pure_all_assignment(value: ast.AST) -> bool:
     )


-def _safe_annassign(
-    statement: ast.AnnAssign,
-    annotation_semantics: str | None,
-) -> bool:
-    if (
-        annotation_semantics not in {"DEFERRED", "STRINGIFIED"}
-        or not isinstance(statement.target, ast.Name)
-        or statement.simple != 1
-        or not statement.target.id.isidentifier()
-        or statement.target.id.startswith("__")
-    ):
-        return False
-    return (
-        statement.value is None
-        or _pure_literal_expression(statement.value)
-    )
-
-
 def _compile(
     tree: ast.Module,
     logical: str,
```

## FINAL_VERDICT

TARGETED_SOURCE_AND_TEST_PASS. Requested extraction and compatibility checks pass at source/test level; LIVE watcher and file freshness are verified at revision 1268. Fresh cycle semantics and runtime adoption remain unproved, so no broader FINAL PASS claim is made.
