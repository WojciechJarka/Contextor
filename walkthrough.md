# TASK
P15-R8

# PREFLIGHT
DIRECT_EVIDENCE: HEAD 25542634930286b95d7be8e56988f3325dfab6a0; worktree before edit: only walkthrough.md modified. Production and test files clean. Interpreter .venv/Scripts/python.exe: Python 3.15.2. MCP module canonical revision 1144, canonical_state=fresh, workspace_sync=verified; cycle_semantics=stale. Exact production and test anchors matched. No pre-existing differences in task files.

# FILES_CHANGED
- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py

# IMPLEMENTATION
CONTRACT_PROVED: Replaced annotation validator with exact optional-union AST restriction. Replaced initial conditional dataclass field validation with exact literal-default allowlist and default ordering check. Preserved later validation loop. Inserted supplied test block verbatim before the named test anchor.

# TARGETED_TESTS
`& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_package_model.py`: 142 passed, 0 failed, 0 skipped, 24.17s. `git diff --check`: pass.

# MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: get_live_events(after_revision=1144) returned continuous desktop_watcher update_file for package_model.py, revision 1145, resync_required=false. Subsequent get_module_context: canonical_state=fresh, workspace_sync=verified, canonical_revision=1145, provenance=live; syntax_errors=0; cycle_semantics=stale. No FULL analysis or restart. The test file is outside module freshness evidence.

# REGRESSION_CONTRACTS
CONTRACT_PROVED by targeted tests: accepted restricted optional annotations and listed constant defaults; rejected dynamic defaults, arbitrary/nested unions, invalid field ordering, and disabled frozen-dataclass or deferred-annotation assumptions. Existing R7 tests retained.

# AUTHORITY_LIMITATIONS
CODE_PATH_PROVED by tests, not runtime import safety. Conditional MODEL_PASS is not promoted to runtime proof. Structural warnings remain active (16); no warning suppression. Changed source does not establish persistent MCP runtime adoption; reload requirement remains separate. No commit or push.

# FINAL_VERDICT
PASS for exact source/test implementation and targeted test contract. UNKNOWN for persistent MCP runtime adoption and runtime cycle safety.

# FULL_DIFFS
```diffdiff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index a690976..acfa5bd 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -208,6 +208,30 @@ def _restricted_dataclass_field_annotation(
     if isinstance(node, ast.Constant):
         return type(node.value) is str
 
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
     if isinstance(node, ast.Tuple):
         return all(
             _restricted_dataclass_field_annotation(item)
@@ -264,6 +288,8 @@ def _safe_passive_class_definition(
         return False
 
     if conditional_dataclass:
+        seen_default_field = False
+
         for body_statement in statement.body:
             if isinstance(
                 body_statement,
@@ -272,14 +298,33 @@ def _safe_passive_class_definition(
                 return False
 
             if isinstance(body_statement, ast.AnnAssign):
-                if (
-                    body_statement.value is not None
-                    or not _restricted_dataclass_field_annotation(
-                        body_statement.annotation
-                    )
+                if not _restricted_dataclass_field_annotation(
+                    body_statement.annotation
                 ):
                     return False
 
+                default_value = body_statement.value
+
+                if default_value is None:
+                    if seen_default_field:
+                        return False
+                else:
+                    if (
+                        type(default_value) is not ast.Constant
+                        or type(default_value.value) not in {
+                            type(None),
+                            bool,
+                            int,
+                            float,
+                            complex,
+                            str,
+                            bytes,
+                        }
+                    ):
+                        return False
+
+                    seen_default_field = True
+
             if isinstance(
                 body_statement,
                 (ast.FunctionDef, ast.AsyncFunctionDef),
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index a8cc90d..76b8312 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -88,6 +88,218 @@ def test_frozen_dataclass_rebound_name_does_not_bind_class():
     )
 
 
+def _r8_frozen_dataclass_result(
+    class_source,
+    *,
+    assume=True,
+    annotation_semantics="DEFERRED",
+):
+    return evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(
+                "from dataclasses import dataclass\n"
+                + class_source
+                + "\nfrom .child import token\n"
+            ),
+            "pkg.child": ast.parse("token = 7\n"),
+        },
+        "pkg",
+        annotation_semantics=annotation_semantics,
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=assume,
+    )
+
+
+def _r8_assert_rejected(result, class_name="ImportRef"):
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+    assert not any(
+        event.operation in {
+            "ASSUMED_FROZEN_DATACLASS_DECORATION",
+            "DEFINE_PASSIVE_CLASS",
+        }
+        and event.symbol == class_name
+        for event in result.events
+    )
+
+
+def test_r8_importref_shape_crosses_class_definition():
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ImportRef:\n"
+        '    """Raw AST import representation."""\n'
+        "    module: str | None\n"
+        "    level: int\n"
+        "    names: list[str]\n"
+        "    is_from_import: bool\n"
+        "    is_local: bool = False\n"
+        "    type_only: bool = False\n"
+        "    is_lazy: bool = False\n"
+    )
+
+    result = _r8_frozen_dataclass_result(source)
+
+    assert result.outcome == "MODEL_PASS"
+    assert result.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+
+    assert len(result.assumed_dataclass_decorations) == 1
+
+    decoration = result.assumed_dataclass_decorations[0]
+    assert decoration.class_name == "ImportRef"
+    assert decoration.decorator == (
+        "dataclasses.dataclass(frozen=True)"
+    )
+    assert (decoration.line, decoration.column) == (2, 1)
+
+    events = list(result.events)
+
+    decorated_at = next(
+        index for index, event in enumerate(events)
+        if event.operation
+        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
+        and event.symbol == "ImportRef"
+    )
+
+    defined_at = next(
+        index for index, event in enumerate(events)
+        if event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "ImportRef"
+    )
+
+    child_import_at = next(
+        index for index, event in enumerate(events)
+        if event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+    )
+
+    assert decorated_at < defined_at < child_import_at
+    assert result.reached_unmodeled_import is None
+
+
+@pytest.mark.parametrize(
+    "annotation",
+    [
+        "str | None",
+        "None | str",
+        "int | None",
+        "None | int",
+        "list[str] | None",
+        "None | list[str]",
+    ],
+)
+def test_r8_restricted_optional_annotation(annotation):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ImportRef:\n"
+        f"    value: {annotation}\n"
+    )
+
+    result = _r8_frozen_dataclass_result(source)
+
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_dataclass_decorations) == 1
+
+
+@pytest.mark.parametrize(
+    "literal",
+    [
+        "False",
+        "True",
+        "None",
+        "0",
+        "1.5",
+        "2j",
+        "'text'",
+        "b'bytes'",
+    ],
+)
+def test_r8_constant_field_defaults(literal):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ImportRef:\n"
+        "    required: str\n"
+        f"    optional: str = {literal}\n"
+    )
+
+    result = _r8_frozen_dataclass_result(source)
+
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_dataclass_decorations) == 1
+
+
+@pytest.mark.parametrize(
+    "field_source",
+    [
+        "value: bool = factory()",
+        "value: list[str] = []",
+        "value: bool = SOME_NAME",
+        "value: bool = 1 + 2",
+        "value: bool = (1, 2)",
+        "value: bool = {}",
+        "value: str | int",
+        "value: str | UnknownName",
+        "value: str | None | None",
+        "value: str + None",
+        "value: str | None = factory()",
+        "first: bool = False\n    later: int",
+    ],
+)
+def test_r8_rejects_unsupported_dataclass_fields(
+    field_source,
+):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ImportRef:\n"
+        f"    {field_source}\n"
+    )
+
+    result = _r8_frozen_dataclass_result(source)
+
+    _r8_assert_rejected(result)
+
+
+def test_r8_optional_class_requires_explicit_assumption():
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ImportRef:\n"
+        "    module: str | None\n"
+        "    is_local: bool = False\n"
+    )
+
+    result = _r8_frozen_dataclass_result(
+        source,
+        assume=False,
+    )
+
+    _r8_assert_rejected(result)
+
+
+@pytest.mark.parametrize(
+    "annotation_semantics",
+    [None, "STRINGIFIED"],
+)
+def test_r8_optional_class_requires_deferred_annotations(
+    annotation_semantics,
+):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ImportRef:\n"
+        "    module: str | None\n"
+        "    is_local: bool = False\n"
+    )
+
+    result = _r8_frozen_dataclass_result(
+        source,
+        annotation_semantics=annotation_semantics,
+    )
+
+    _r8_assert_rejected(result)
+
+
 def test_external_assumption_normal_model_still_unknown():
     result = _model({"pkg.__init__": "import os\n"}, "pkg")
     assert result.outcome == "UNKNOWN"
```
