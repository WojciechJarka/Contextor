# TASK
P15-R11

# PREFLIGHT
DIRECT_EVIDENCE: Contextor `get_module_context` returned `package_model.py` and `tests/test_cycle_semantics_package_model.py` at canonical revision 1150, `canonical_state=fresh`, `workspace_sync=verified`. All specified anchors A–G and the test insertion anchor matched. Source/test files had no pre-existing diff. Repository `.venv\Scripts\python.exe`: CPython 3.15.2.

# HEAD_BEFORE
`d36023c5c9dd81586e445b9e1d3ef2be92e3727d`; worktree clean before R11.

# FILES_CHANGED
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`

# EXACT_PATCH_VERIFICATION
CONTRACT_PROVED: supplied production patches A–G and exact test block were applied at their specified anchors. No unrelated production/test changes. The supplied patch is internally inconsistent with the existing later class validation loop; no unsupplied correction was made.

# TARGETED_TESTS
`& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_package_model.py`: **1 failed, 200 passed** (15.33 s). Failure: `test_r11_real_module_shape_crosses_class`, line 790, expected `MODEL_PASS`, actual `UNKNOWN`. `git diff --check`: PASS.

# MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: `get_live_events(after_revision=1150)` returned continuous desktop_watcher events at 1151 (`package_model.py` UPDATED), 1152 (same path UNCHANGED), 1153 (test file UPDATED), `resync_required=false`. Post-change `get_module_context` returned production canonical revision 1153, `canonical_state=fresh`, `workspace_sync=verified`. `cycle_semantics=stale`. No FULL analysis, `update_file`, restart, commit, or push.

# PASSIVE_CLASS_ANNOTATION_BINDING
CODE_PATH_PROVED: the supplied syntax validator accepts a nonbuiltin name and the supplied conditional decoration guard requires a previously modeled `\x00PASSIVE_CLASS:` binding. The failing positive case reaches `FROM pkg.imports ImportRef`, with ImportRef already conditionally decorated and bound. It stops before Module decoration.

# DATACLASS_FIELD_CALL_AUTHORITY
DIRECT_EVIDENCE: for the supplied positive fixture, `result.outcome=UNKNOWN`, `target_module=pkg.module`, `symbol=None`; the last event is `FROM pkg.imports ImportRef`. Direct function checks on its AST returned `_safe_passive_class_definition(..., allow_conditional_frozen_dataclass=True) == False` and `_safe_annassign(imports_field, "DEFERRED") == False`. CODE_PATH_PROVED: the new initial conditional validator admits `field(hash=False)`, but the preserved later loop calls `_safe_annassign`, which accepts only no value or `_pure_literal_expression(value)`. `field(hash=False)` is an `ast.Call`, so the later loop returns False before `_compile` emits `CHECK_DATACLASS_FIELD_FACTORY`. The instructions explicitly prohibit changing `_safe_annassign` and prescribe no exception in the later loop. This is the exact blocking contradiction.

# BUILTIN_PROPERTY_AUTHORITY
The supplied recognizer, validator option, ordered check step, and evaluator check are present. The positive fixture never reaches these steps because class validation fails earlier. No claim of successful property behavior is made.

# CLASS_BODY_EVALUATION_ORDER
CODE_PATH_PROVED from inserted code: `CHECK_DATACLASS_FIELD_FACTORY` would precede `CLASS_LOCAL_BIND`, and `CHECK_BUILTIN_PROPERTY` would occur at method-definition position before conditional decoration. The failing fixture does not reach those compiled steps.

# NEGATIVE_REGRESSIONS
The target file's other 200 cases passed, including the supplied negative R11 cases. This does not satisfy the failed positive contract.

# R7_R10_REGRESSION_STATUS
Existing tests in the target file passed within the 200 passing cases; the required R11 positive case failed. No full-suite or runtime certification claim.

# AUTHORITY_LIMITATIONS
No actual CPython import execution or runtime cycle safety was proven. Watcher source parity does not establish persistent MCP interpreter adoption. No conditional result was promoted or warning suppressed. Auditor correction is needed before implementation can pass the supplied contract.

# FULL_DIFFS
```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 1374295..4ba018e 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -101,6 +101,7 @@ def _safe_passive_function_definition(
     *,
     allow_dunder: bool = False,
     annotation_semantics: str | None = None,
+    allow_builtin_property: bool = False,
 ) -> bool:
     """A definition whose creation has no unknown evaluations.
 
@@ -113,7 +114,18 @@ def _safe_passive_function_definition(
             statement.name.startswith("__")
             and not allow_dunder
         )
-        or statement.decorator_list
+        or (
+            bool(statement.decorator_list)
+            and not (
+                allow_builtin_property
+                and type(statement) is ast.FunctionDef
+                and len(statement.decorator_list) == 1
+                and type(statement.decorator_list[0])
+                is ast.Name
+                and statement.decorator_list[0].id
+                == "property"
+            )
+        )
         or (statement.returns is not None and annotation_semantics not in {
             "DEFERRED", "STRINGIFIED",
         })
@@ -195,15 +207,31 @@ def _exact_frozen_dataclass_decorator(
     )
 
 
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
 def _restricted_dataclass_field_annotation(
     node: ast.AST,
 ) -> bool:
     if isinstance(node, ast.Name):
-        return node.id in {
-            "str", "int", "bool", "float",
-            "bytes", "dict", "list",
-            "set", "tuple",
-        }
+        return (
+            node.id.isidentifier()
+            and not node.id.startswith("__")
+            and node.id != "ast"
+        )
 
     if type(node) is ast.Attribute:
         return (
@@ -305,6 +333,48 @@ def _safe_passive_class_definition(
     if conditional_dataclass:
         seen_default_field = False
 
+        uses_field_call = any(
+            isinstance(item, ast.AnnAssign)
+            and item.value is not None
+            and _exact_restricted_dataclass_hash_field_call(
+                item.value
+            )
+            for item in statement.body
+        )
+
+        uses_property = any(
+            type(item) is ast.FunctionDef
+            and len(item.decorator_list) == 1
+            and type(item.decorator_list[0]) is ast.Name
+            and item.decorator_list[0].id == "property"
+            for item in statement.body
+        )
+
+        protected_names = set()
+
+        if uses_field_call:
+            protected_names.add("field")
+
+        if uses_property:
+            protected_names.add("property")
+
+        if any(
+            (
+                isinstance(item, ast.AnnAssign)
+                and isinstance(item.target, ast.Name)
+                and item.target.id in protected_names
+            )
+            or (
+                isinstance(
+                    item,
+                    (ast.FunctionDef, ast.AsyncFunctionDef),
+                )
+                and item.name in protected_names
+            )
+            for item in statement.body
+        ):
+            return False
+
         for body_statement in statement.body:
             if isinstance(
                 body_statement,
@@ -324,9 +394,9 @@ def _safe_passive_class_definition(
                     if seen_default_field:
                         return False
                 else:
-                    if (
-                        type(default_value) is not ast.Constant
-                        or type(default_value.value) not in {
+                    literal_default = (
+                        type(default_value) is ast.Constant
+                        and type(default_value.value) in {
                             type(None),
                             bool,
                             int,
@@ -335,6 +405,14 @@ def _safe_passive_class_definition(
                             str,
                             bytes,
                         }
+                    )
+
+                    if (
+                        not literal_default
+                        and not
+                        _exact_restricted_dataclass_hash_field_call(
+                            default_value
+                        )
                     ):
                         return False
 
@@ -397,6 +475,7 @@ def _safe_passive_class_definition(
                 body_statement,
                 allow_dunder=True,
                 annotation_semantics=annotation_semantics,
+                allow_builtin_property=conditional_dataclass,
             )
         ):
             continue
@@ -945,15 +1024,47 @@ def _compile(
                     )
                     continue
 
-                if not isinstance(body_statement, (ast.Import, ast.ImportFrom)):
+                if not isinstance(
+                    body_statement,
+                    (ast.Import, ast.ImportFrom),
+                ):
                     if (
                         isinstance(body_statement, ast.AnnAssign)
                         and body_statement.value is not None
                     ):
-                        steps.append(_Step(
-                            "BIND", binding=body_statement.target.id,
-                            class_local=True,
-                        ))
+                        if _exact_restricted_dataclass_hash_field_call(
+                            body_statement.value
+                        ):
+                            steps.append(
+                                _Step(
+                                    "CHECK_DATACLASS_FIELD_FACTORY",
+                                    target="field",
+                                )
+                            )
+
+                        steps.append(
+                            _Step(
+                                "BIND",
+                                binding=body_statement.target.id,
+                                class_local=True,
+                            )
+                        )
+
+                    if (
+                        type(body_statement) is ast.FunctionDef
+                        and len(body_statement.decorator_list) == 1
+                        and type(body_statement.decorator_list[0])
+                        is ast.Name
+                        and body_statement.decorator_list[0].id
+                        == "property"
+                    ):
+                        steps.append(
+                            _Step(
+                                "CHECK_BUILTIN_PROPERTY",
+                                target="property",
+                            )
+                        )
+
                     continue
 
                 fragment = ast.Module(
@@ -2003,6 +2114,29 @@ def evaluate_package_import_order(
                 )
             )
 
+        elif step.op == "CHECK_DATACLASS_FIELD_FACTORY":
+            if (
+                step.target != "field"
+                or namespaces[module].get("field")
+                != "\x00ASSUMED_EXTERNAL:dataclasses:field"
+            ):
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.target,
+                )
+
+        elif step.op == "CHECK_BUILTIN_PROPERTY":
+            if (
+                step.target != "property"
+                or "property" in namespaces[module]
+            ):
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.target,
+                )
+
         elif step.op == "DEFINE_CONDITIONAL_FROZEN_DATACLASS":
             if (
                 namespaces[module].get("dataclass")
@@ -2012,7 +2146,27 @@ def evaluate_package_import_order(
                         namespaces[module].get(name)
                         != "\x00ASSUMED_EXTERNAL:ast"
                         if name == "ast"
-                        else name in namespaces[module]
+                        else (
+                            name in namespaces[module]
+                            if name in {
+                                "str",
+                                "int",
+                                "bool",
+                                "float",
+                                "bytes",
+                                "dict",
+                                "list",
+                                "set",
+                                "tuple",
+                            }
+                            else not (
+                                type(namespaces[module].get(name))
+                                is str
+                                and namespaces[module][name].startswith(
+                                    "\x00PASSIVE_CLASS:"
+                                )
+                            )
+                        )
                     )
                     for name in step.annotation_builtin_names
                 )
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 55002f6..a50c607 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -717,6 +717,366 @@ def test_r10_requires_deferred_annotation_semantics(
     _r10_assert_rejected(result)
 
 
+def _r11_module_result(
+    module_source,
+    *,
+    import_type="from .imports import ImportRef\n",
+    import_dataclass="from dataclasses import dataclass, field\n",
+    prelude="",
+    annotation_semantics="DEFERRED",
+    assume=True,
+):
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.imports": (
+            "from dataclasses import dataclass\n"
+            "@dataclass(frozen=True)\n"
+            "class ImportRef:\n"
+            "    module: str | None\n"
+        ),
+        "pkg.module": (
+            import_dataclass
+            + import_type
+            + prelude
+            + module_source
+            + "\nfrom .child import token\n"
+        ),
+        "pkg.child": "token = 7\n",
+    }
+
+    return evaluate_package_import_order(
+        {
+            key: ast.parse(value)
+            for key, value in sources.items()
+        },
+        "pkg.module",
+        annotation_semantics=annotation_semantics,
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=assume,
+    )
+
+
+def _r11_class_source():
+    return (
+        "@dataclass(frozen=True)\n"
+        "class Module:\n"
+        "    module_id: str\n"
+        "    path: str\n"
+        "    absolute_path: str\n"
+        "    imports: list[ImportRef] = field(hash=False)\n"
+        "    @property\n"
+        "    def ast_tree(self):\n"
+        "        return None\n"
+    )
+
+
+def _r11_assert_module_rejected(result):
+    assert result.outcome == "UNKNOWN"
+    assert not any(
+        item.class_name == "Module"
+        for item in result.assumed_dataclass_decorations
+    )
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "Module"
+        for event in result.events
+    )
+
+
+def test_r11_real_module_shape_crosses_class():
+    result = _r11_module_result(_r11_class_source())
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert tuple(
+        item.class_name
+        for item in result.assumed_dataclass_decorations
+    ) == (
+        "ImportRef",
+        "Module",
+    )
+
+    events = list(result.events)
+
+    imported_type = next(
+        index for index, event in enumerate(events)
+        if event.operation == "FROM"
+        and event.target == "pkg.imports"
+        and event.symbol == "ImportRef"
+    )
+
+    bound_field = next(
+        index for index, event in enumerate(events)
+        if event.operation == "CLASS_LOCAL_BIND"
+        and event.symbol == "imports"
+    )
+
+    decorated = next(
+        index for index, event in enumerate(events)
+        if event.operation
+        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
+        and event.symbol == "Module"
+    )
+
+    bound_class = next(
+        index for index, event in enumerate(events)
+        if event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "Module"
+    )
+
+    imported_child = next(
+        index for index, event in enumerate(events)
+        if event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+    )
+
+    assert (
+        imported_type
+        < bound_field
+        < decorated
+        < bound_class
+        < imported_child
+    )
+
+    assert result.reached_unmodeled_import is None
+
+
+def test_r11_named_passive_class_annotation_not_hardcoded():
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class Module:\n"
+        "    reference: OtherType\n"
+    )
+
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.imports": (
+            "class OtherType:\n"
+            "    pass\n"
+        ),
+        "pkg.module": (
+            "from dataclasses import dataclass\n"
+            "from .imports import OtherType\n"
+            + source
+        ),
+    }
+
+    result = evaluate_package_import_order(
+        {
+            key: ast.parse(value)
+            for key, value in sources.items()
+        },
+        "pkg.module",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        item.class_name == "Module"
+        for item in result.assumed_dataclass_decorations
+    )
+
+
+@pytest.mark.parametrize(
+    "import_type,prelude",
+    [
+        ("", ""),
+        ("from pathlib import ImportRef\n", ""),
+        ("from .imports import ImportRef\n", "ImportRef = 7\n"),
+    ],
+)
+def test_r11_requires_proven_passive_type(
+    import_type,
+    prelude,
+):
+    result = _r11_module_result(
+        _r11_class_source(),
+        import_type=import_type,
+        prelude=prelude,
+    )
+
+    _r11_assert_module_rejected(result)
+
+
+@pytest.mark.parametrize(
+    "import_dataclass,prelude",
+    [
+        ("from dataclasses import dataclass\n", ""),
+        (
+            "from dataclasses import dataclass\n"
+            "from pathlib import Path as field\n",
+            "",
+        ),
+        (
+            "from dataclasses import dataclass, field\n",
+            "field = 42\n",
+        ),
+    ],
+)
+def test_r11_requires_exact_field_factory_binding(
+    import_dataclass,
+    prelude,
+):
+    result = _r11_module_result(
+        _r11_class_source(),
+        import_dataclass=import_dataclass,
+        prelude=prelude,
+    )
+
+    _r11_assert_module_rejected(result)
+
+    assert not any(
+        event.operation == "CLASS_LOCAL_BIND"
+        and event.symbol == "imports"
+        for event in result.events
+    )
+
+
+@pytest.mark.parametrize(
+    "default_expression",
+    [
+        "field()",
+        "field(default=1)",
+        "field(hash=True)",
+        "field(hash=0)",
+        "field(hash=False, compare=True)",
+        "other(hash=False)",
+        "field(hash=False) or None",
+    ],
+)
+def test_r11_rejects_other_default_calls(
+    default_expression,
+):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class Module:\n"
+        f"    imports: list[ImportRef] = {default_expression}\n"
+    )
+
+    result = _r11_module_result(source)
+
+    _r11_assert_module_rejected(result)
+
+
+@pytest.mark.parametrize(
+    "decorator",
+    [
+        "@property()",
+        "@unknown",
+        "@property\n    @unknown",
+    ],
+)
+def test_r11_rejects_other_method_decorators(decorator):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class Module:\n"
+        "    imports: list[ImportRef] = field(hash=False)\n"
+        f"    {decorator}\n"
+        "    def ast_tree(self):\n"
+        "        return None\n"
+    )
+
+    result = _r11_module_result(source)
+
+    _r11_assert_module_rejected(result)
+
+
+def test_r11_rejects_shadowed_builtin_property():
+    result = _r11_module_result(
+        _r11_class_source(),
+        prelude="property = 12\n",
+    )
+
+    _r11_assert_module_rejected(result)
+
+
+@pytest.mark.parametrize(
+    "shadow_source",
+    [
+        "    property: str = 'shadow'\n",
+        "    field: str = 'shadow'\n",
+    ],
+)
+def test_r11_rejects_class_local_callable_shadow(
+    shadow_source,
+):
+    source = _r11_class_source().replace(
+        "    imports: list[ImportRef] = field(hash=False)\n",
+        shadow_source
+        + "    imports: list[ImportRef] = field(hash=False)\n",
+    )
+
+    result = _r11_module_result(source)
+
+    _r11_assert_module_rejected(result)
+
+
+def test_r11_rejects_unmodeled_async_property():
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class Module:\n"
+        "    imports: list[ImportRef] = field(hash=False)\n"
+        "    @property\n"
+        "    async def ast_tree(self):\n"
+        "        return None\n"
+    )
+
+    result = _r11_module_result(source)
+
+    _r11_assert_module_rejected(result)
+
+
+def test_r11_plain_class_property_remains_unmodeled():
+    sources = {
+        "pkg.__init__": (
+            "class Plain:\n"
+            "    @property\n"
+            "    def value(self):\n"
+            "        return 1\n"
+        )
+    }
+
+    result = evaluate_package_import_order(
+        {
+            key: ast.parse(value)
+            for key, value in sources.items()
+        },
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+    )
+
+    assert result.outcome == "UNKNOWN"
+
+
+def test_r11_requires_explicit_conditional_assumption():
+    result = _r11_module_result(
+        _r11_class_source(),
+        assume=False,
+    )
+
+    _r11_assert_module_rejected(result)
+
+
+@pytest.mark.parametrize(
+    "annotation_semantics",
+    [None, "STRINGIFIED"],
+)
+def test_r11_requires_deferred_annotation_semantics(
+    annotation_semantics,
+):
+    result = _r11_module_result(
+        _r11_class_source(),
+        annotation_semantics=annotation_semantics,
+    )
+
+    _r11_assert_module_rejected(result)
+
+
 def test_external_assumption_normal_model_still_unknown():
     result = _model({"pkg.__init__": "import os\n"}, "pkg")
     assert result.outcome == "UNKNOWN"
```

# FINAL_VERDICT
FAIL. Exact supplied patch and tests do not satisfy the positive R11 contract because preserved `_safe_annassign` rejects the exact `field(hash=False)` call in the later validation loop. 200 tests pass, 1 fails. No unsupplied fix was made. Auditor correction is required before proceeding.
