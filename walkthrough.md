# P5-M04-I1 — Definition predicates extraction

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `0d12c2d6748a0e76c0b262ac990579a247a3b9d5`; initial `git status --short` showed only ` M walkthrough.md` from the previous report. That report was intentionally replaced. No pre-existing source/test changes were overwritten.
- DIRECT_EVIDENCE: Contextor MCP returned canonical LIVE revision 1268, `canonical_state=fresh`, `workspace_sync=verified` for all three source predicates, and `cycle_semantics=stale`. Backend executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` (PID 14072).
- DIRECT_EVIDENCE: Current source definitions at `contextor/core/cycle_semantics/package_model.py:310-328,331-344,347-407` matched the supplied bodies exactly. `contextor/core/cycle_semantics/execution/definition_checks.py` did not exist before editing. Direct callers and transitive dependencies were established in the preceding P5-M04-D2 report and rechecked against current source.
- CODE_PATH_PROVED: Independent semantic-integrity review for this structural move: the three function bodies are copied unchanged; all call sites in `package_model.py` still resolve the same names through its module globals; the recursive annotation predicate now resolves itself within its new module. Supported and rejected AST shapes are unchanged. Existing focused tests include positive, negative and CPython-backed class/decorator cases (`tests/test_cycle_semantics_package_model.py`, `tests/test_cycle_semantics_passive_classes.py`, `tests/test_cycle_semantics_decorator_definition_effects.py`). This establishes refactor compatibility, not general semantic proof of the restricted model.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/definition_checks.py` — new file.
- `contextor/core/cycle_semantics/package_model.py` — import of moved predicates; old definitions removed.
- `walkthrough.md` — this report, exempt from production/test diff accounting under AGENTS.md §10.

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: New module contains only `from __future__ import annotations`, `import ast`, and the three specified predicate bodies, in specified order. `package_model.py` imports those names immediately after its existing `execution.expressions` block. The three old definitions were removed; `_safe_passive_function_definition`, `_safe_passive_class_definition`, `_safe_class_namespace_value`, `_ClassFact`, `_compile`, `_compile_reachable_prefix`, evaluator branches, event/result types and existing imports were left unchanged. Full diffs appear below.

## COMPATIBILITY_RESULTS

- CONTRACT_PROVED: With the actual backend venv interpreter, all three `package_model` attributes were identical by `is` to their `definition_checks` counterparts.
- CONTRACT_PROVED: `_restricted_dataclass_field_annotation.__globals__["_restricted_dataclass_field_annotation"]` is the relocated function; the three names in `_safe_passive_class_definition.__globals__` are the relocated functions.
- CONTRACT_PROVED: `package_model._compile.__module__ == "contextor.core.cycle_semantics.package_model"` and its `__code__.co_filename.endswith("package_model.py")`.
- DIRECT_EVIDENCE: All three relocated `__module__` values are `contextor.core.cycle_semantics.execution.definition_checks`. Compatibility command exited 0.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Backend venv `python.exe -m pytest -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_package_model_literals.py tests/test_cycle_semantics_package_model_annotations315.py tests/test_cycle_semantics_passive_functions.py tests/test_cycle_semantics_passive_classes.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_f1h_runtime_attestation.py -rs`: **472 passed, 2 third-party deprecation warnings, 45.14 s**. No full suite was run.
- DIRECT_EVIDENCE: `git diff --check` produced no whitespace-error output. The combined inspection command returned exit 1 because `git diff --no-index -- NUL <new file>` reports differences with exit 1; this is expected and is not a `git diff --check` failure.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Contextor canonical LIVE revision advanced 1268 → 1270. `get_module_context` reported `canonical_state=fresh`, `workspace_sync=verified` for both `package_model` and new `execution.definition_checks`; graph/topology/module families fresh, `cycle_semantics=stale`.
- DIRECT_EVIDENCE: LIVE syntax-error count 0. Hard structural DFS cycle count 16. Active warning count 16, with model-pass count 0 in module diagnostics. The new hard edge is `contextor.core.cycle_semantics.package_model → contextor.core.cycle_semantics.execution.definition_checks`; new module has one inbound and zero outbound hard dependencies.
- UNKNOWN: Current cyclic SCC count and graph fingerprint were not exposed in the selected current LIVE audit. `cycle_semantics` classification remains stale; historical report data were not used to replace it. Running-backend reload/adoption was not certified, and no restart was performed.

## FULL_DIFFS

### `contextor/core/cycle_semantics/package_model.py`

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 4ab403a..a6acd8b 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -30,6 +30,11 @@ from .execution.expressions import (
     _pure_literal_expression,
     _safe_annassign,
 )
+from .execution.definition_checks import (
+    _exact_frozen_dataclass_decorator,
+    _exact_restricted_dataclass_hash_field_call,
+    _restricted_dataclass_field_annotation,
+)
 
 
 @dataclass(frozen=True)
@@ -307,106 +312,6 @@ def _safe_passive_function_definition(
     return True
 
 
-def _exact_frozen_dataclass_decorator(
-    decorator: ast.AST,
-) -> bool:
-    return (
-        isinstance(decorator, ast.Call)
-        and isinstance(decorator.func, ast.Name)
-        and decorator.func.id == "dataclass"
-        and not decorator.args
-        and len(decorator.keywords) == 1
-        and decorator.keywords[0].arg == "frozen"
-        and isinstance(
-            decorator.keywords[0].value,
-            ast.Constant,
-        )
-        and decorator.keywords[0].value.value is True
-        and type(
-            decorator.keywords[0].value.value
-        ) is bool
-    )
-
-
-def _exact_restricted_dataclass_hash_field_call(
-    node: ast.AST,
-) -> bool:
-    return (
-        type(node) is ast.Call
-        and type(node.func) is ast.Name
-        and node.func.id == "field"
-        and not node.args
-        and len(node.keywords) == 1
-        and node.keywords[0].arg == "hash"
-        and type(node.keywords[0].value) is ast.Constant
-        and type(node.keywords[0].value.value) is bool
-        and node.keywords[0].value.value is False
-    )
-
-
-def _restricted_dataclass_field_annotation(
-    node: ast.AST,
-) -> bool:
-    if isinstance(node, ast.Name):
-        return (
-            node.id.isidentifier()
-            and not node.id.startswith("__")
-            and node.id != "ast"
-        )
-
-    if type(node) is ast.Attribute:
-        return (
-            type(node.value) is ast.Name
-            and node.value.id == "ast"
-            and node.attr == "AST"
-        )
-
-    if isinstance(node, ast.Constant):
-        return type(node.value) is str
-
-    if isinstance(node, ast.BinOp):
-        if not isinstance(node.op, ast.BitOr):
-            return False
-
-        if (
-            isinstance(node.left, ast.Constant)
-            and type(node.left.value) is type(None)
-            and not isinstance(node.right, ast.BinOp)
-        ):
-            return _restricted_dataclass_field_annotation(
-                node.right
-            )
-
-        if (
-            isinstance(node.right, ast.Constant)
-            and type(node.right.value) is type(None)
-            and not isinstance(node.left, ast.BinOp)
-        ):
-            return _restricted_dataclass_field_annotation(
-                node.left
-            )
-
-        return False
-
-    if isinstance(node, ast.Tuple):
-        return all(
-            _restricted_dataclass_field_annotation(item)
-            for item in node.elts
-        )
-
-    if isinstance(node, ast.Subscript):
-        return (
-            _restricted_dataclass_field_annotation(
-                node.value
-            )
-            and _restricted_dataclass_field_annotation(
-                node.slice
-            )
-        )
-
-    return False
-
-
 def _safe_passive_class_definition(
     statement: ast.ClassDef,
     *,
```

### `contextor/core/cycle_semantics/execution/definition_checks.py`

```diff
diff --git a/contextor/core/cycle_semantics/execution/definition_checks.py b/contextor/core/cycle_semantics/execution/definition_checks.py
new file mode 100644
index 0000000..1d470b3
--- /dev/null
+++ b/contextor/core/cycle_semantics/execution/definition_checks.py
@@ -0,0 +1,103 @@
+from __future__ import annotations
+
+import ast
+
+
+def _exact_frozen_dataclass_decorator(
+    decorator: ast.AST,
+) -> bool:
+    return (
+        isinstance(decorator, ast.Call)
+        and isinstance(decorator.func, ast.Name)
+        and decorator.func.id == "dataclass"
+        and not decorator.args
+        and len(decorator.keywords) == 1
+        and decorator.keywords[0].arg == "frozen"
+        and isinstance(
+            decorator.keywords[0].value,
+            ast.Constant,
+        )
+        and decorator.keywords[0].value.value is True
+        and type(
+            decorator.keywords[0].value.value
+        ) is bool
+    )
+
+
+def _exact_restricted_dataclass_hash_field_call(
+    node: ast.AST,
+) -> bool:
+    return (
+        type(node) is ast.Call
+        and type(node.func) is ast.Name
+        and node.func.id == "field"
+        and not node.args
+        and len(node.keywords) == 1
+        and node.keywords[0].arg == "hash"
+        and type(node.keywords[0].value) is ast.Constant
+        and type(node.keywords[0].value.value) is bool
+        and node.keywords[0].value.value is False
+    )
+
+
+def _restricted_dataclass_field_annotation(
+    node: ast.AST,
+) -> bool:
+    if isinstance(node, ast.Name):
+        return (
+            node.id.isidentifier()
+            and not node.id.startswith("__")
+            and node.id != "ast"
+        )
+
+    if type(node) is ast.Attribute:
+        return (
+            type(node.value) is ast.Name
+            and node.value.id == "ast"
+            and node.attr == "AST"
+        )
+
+    if isinstance(node, ast.Constant):
+        return type(node.value) is str
+
+    if isinstance(node, ast.BinOp):
+        if not isinstance(node.op, ast.BitOr):
+            return False
+
+        if (
+            isinstance(node.left, ast.Constant)
+            and type(node.left.value) is type(None)
+            and not isinstance(node.right, ast.BinOp)
+        ):
+            return _restricted_dataclass_field_annotation(
+                node.right
+            )
+
+        if (
+            isinstance(node.right, ast.Constant)
+            and type(node.right.value) is type(None)
+            and not isinstance(node.left, ast.BinOp)
+        ):
+            return _restricted_dataclass_field_annotation(
+                node.left
+            )
+
+        return False
+
+    if isinstance(node, ast.Tuple):
+        return all(
+            _restricted_dataclass_field_annotation(item)
+            for item in node.elts
+        )
+
+    if isinstance(node, ast.Subscript):
+        return (
+            _restricted_dataclass_field_annotation(
+                node.value
+            )
+            and _restricted_dataclass_field_annotation(
+                node.slice
+            )
+        )
+
+    return False
```

## FINAL_VERDICT

- CONTRACT_PROVED: The exact structural extraction, compatibility checks and requested focused regression set passed. Contextor confirmed fresh source/graph state at revision 1270. `cycle_semantics` remains stale, so no fresh semantic classification or runtime-adoption claim is made. STOP after implementation and audit.
