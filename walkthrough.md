# TASK
P15-R10

# PREFLIGHT
DIRECT_EVIDENCE: Contextor `get_module_context` and `get_symbol_implementation` returned `package_model.py` at canonical revision 1148, `canonical_state=fresh`, `workspace_sync=verified`. Both production anchors and the test insertion anchor matched exactly. Source/test files had no pre-existing diff. `.venv\Scripts\python.exe` is CPython 3.15.2.

# HEAD_BEFORE
`c7c069cb3e217f6b34928a637da42dc5eb563160`. Only `walkthrough.md` was modified before R10. Its prior report was overwritten as instructed; no unrelated source/test changes were overwritten.

# FILES_CHANGED
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`

# EXACT_PATCH_VERIFICATION
CONTRACT_PROVED: PATCH A adds exactly the `ast.AST` attribute shape to the restricted conditional dataclass annotation validator. PATCH B checks that an annotation reference named `ast` has the exact existing assumed external binding at decoration time; all other annotation name shadow checks retain their old branch. The supplied test block was inserted before the exact anchor. No other source/test changes.

# TARGETED_TESTS
`& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_package_model.py`: 175 passed, 0 failed, 0 skipped (15.23 s). `git diff --check`: PASS.

# MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: `get_live_events(after_revision=1148)` returned continuous `desktop_watcher` update_file for package_model.py at revision 1149, `resync_required=false`. `get_module_context` then returned `canonical_state=fresh`, `workspace_sync=verified`, revision 1149, syntax errors 0. `cycle_semantics=stale`; 16 structural warnings remain. No FULL analysis, `update_file`, restart, commit, or push.

# QUALIFIED_ANNOTATION_CONTRACT
CONTRACT_PROVED by focused tests: `ast.AST`, `ast.AST | None`, `None | ast.AST`, and `list[ast.AST]` pass only within the existing conditional frozen dataclass path. The existing R8 union/Tuple/Subscript logic is untouched.

# EXTERNAL_MODULE_BINDING_PROOF
CODE_PATH_PROVED: `_compile` already collects annotation `ast.Name` references; PATCH B checks `namespaces[module].get("ast") == "\x00ASSUMED_EXTERNAL:ast"` when the conditional dataclass step executes. Missing, reimported under another module, or rebound `ast` fails before decoration/binding. A later rebinding does not retroactively fail the class. No new public event or assumption type was added.

# NEGATIVE_REGRESSIONS
CONTRACT_PROVED by focused tests: unsupported attributes, calls, arbitrary/nested unions, absent or wrong `ast` binding, disabled dataclass assumption, and non-DEFERRED annotation semantics remain UNKNOWN without binding `ParsedSourceInput`.

# R7_R8_R9_REGRESSION_STATUS
Existing tests were preserved; all 175 tests in the target file pass.

# AUTHORITY_LIMITATIONS
Focused model tests and watcher indexing do not prove actual CPython runtime import safety or persistent MCP interpreter adoption of the changed implementation. Conditional MODEL_PASS is not runtime proof. Structural warnings were not suppressed.

# FULL_DIFFS
```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index c9600af..1374295 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -205,6 +205,13 @@ def _restricted_dataclass_field_annotation(
             "set", "tuple",
         }
 
+    if type(node) is ast.Attribute:
+        return (
+            type(node.value) is ast.Name
+            and node.value.id == "ast"
+            and node.attr == "AST"
+        )
+
     if isinstance(node, ast.Constant):
         return type(node.value) is str
 
@@ -2001,7 +2008,12 @@ def evaluate_package_import_order(
                 namespaces[module].get("dataclass")
                 != "\x00ASSUMED_EXTERNAL:dataclasses:dataclass"
                 or any(
-                    name in namespaces[module]
+                    (
+                        namespaces[module].get(name)
+                        != "\x00ASSUMED_EXTERNAL:ast"
+                        if name == "ast"
+                        else name in namespaces[module]
+                    )
                     for name in step.annotation_builtin_names
                 )
             ):
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index cf35e22..55002f6 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -458,6 +458,265 @@ def test_r9_existing_plain_class_unchanged():
     )
 
 
+def _r10_qualified_ast_result(
+    class_source,
+    *,
+    prelude="import ast\n",
+    after_class="",
+    assume=True,
+    annotation_semantics="DEFERRED",
+):
+    source = (
+        prelude
+        + "from dataclasses import dataclass\n"
+        + class_source
+        + "\n"
+        + after_class
+        + "from .child import token\n"
+    )
+
+    return evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
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
+def _r10_assert_rejected(result):
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_dataclass_decorations == ()
+
+    assert not any(
+        event.operation in {
+            "ASSUMED_FROZEN_DATACLASS_DECORATION",
+            "DEFINE_PASSIVE_CLASS",
+        }
+        and event.symbol == "ParsedSourceInput"
+        for event in result.events
+    )
+
+
+def test_r10_parsed_source_input_crosses_class():
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ParsedSourceInput:\n"
+        "    tree: ast.AST\n"
+        "    source_fingerprint: str\n"
+    )
+
+    result = _r10_qualified_ast_result(source)
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
+
+    assert decoration.class_name == "ParsedSourceInput"
+    assert decoration.decorator == (
+        "dataclasses.dataclass(frozen=True)"
+    )
+
+    events = list(result.events)
+
+    decorated = next(
+        index for index, event in enumerate(events)
+        if event.operation
+        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
+        and event.symbol == "ParsedSourceInput"
+    )
+
+    bound = next(
+        index for index, event in enumerate(events)
+        if event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "ParsedSourceInput"
+    )
+
+    imported = next(
+        index for index, event in enumerate(events)
+        if event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+    )
+
+    assert decorated < bound < imported
+    assert result.reached_unmodeled_import is None
+
+
+def test_r10_both_source_dataclasses_cross():
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ParsedSourceInput:\n"
+        "    tree: ast.AST\n"
+        "    source_fingerprint: str\n"
+        "\n"
+        "@dataclass(frozen=True)\n"
+        "class SourceSnapshot:\n"
+        "    raw: bytes\n"
+        "    source_fingerprint: str\n"
+    )
+
+    result = _r10_qualified_ast_result(source)
+
+    assert result.outcome == "MODEL_PASS"
+
+    assert tuple(
+        record.class_name
+        for record in result.assumed_dataclass_decorations
+    ) == (
+        "ParsedSourceInput",
+        "SourceSnapshot",
+    )
+
+
+@pytest.mark.parametrize(
+    "annotation",
+    [
+        "ast.AST",
+        "ast.AST | None",
+        "None | ast.AST",
+        "list[ast.AST]",
+    ],
+)
+def test_r10_restricted_qualified_annotations(annotation):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ParsedSourceInput:\n"
+        f"    tree: {annotation}\n"
+    )
+
+    result = _r10_qualified_ast_result(source)
+
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_dataclass_decorations) == 1
+
+
+@pytest.mark.parametrize(
+    "annotation",
+    [
+        "ast.Unknown",
+        "ast.AST.child",
+        "ast.AST()",
+        "os.AST",
+        "unknown.AST",
+        "ast.AST | str",
+        "ast.AST | None | None",
+    ],
+)
+def test_r10_rejects_unsupported_qualified_annotations(
+    annotation,
+):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ParsedSourceInput:\n"
+        f"    tree: {annotation}\n"
+    )
+
+    result = _r10_qualified_ast_result(source)
+
+    _r10_assert_rejected(result)
+
+
+@pytest.mark.parametrize(
+    "prelude",
+    [
+        "",
+        "import os as ast\n",
+        "import ast\nast = 42\n",
+    ],
+)
+def test_r10_rejects_unproven_ast_binding(prelude):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ParsedSourceInput:\n"
+        "    tree: ast.AST\n"
+    )
+
+    result = _r10_qualified_ast_result(
+        source,
+        prelude=prelude,
+    )
+
+    _r10_assert_rejected(result)
+
+
+def test_r10_later_ast_rebinding_does_not_retroactively_fail():
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ParsedSourceInput:\n"
+        "    tree: ast.AST\n"
+    )
+
+    result = _r10_qualified_ast_result(
+        source,
+        after_class="ast = 42\n",
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_dataclass_decorations) == 1
+
+    events = list(result.events)
+
+    bound = next(
+        index for index, event in enumerate(events)
+        if event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "ParsedSourceInput"
+    )
+
+    rebound = next(
+        index for index, event in enumerate(events)
+        if event.operation == "BIND"
+        and event.symbol == "ast"
+    )
+
+    assert bound < rebound
+
+
+def test_r10_requires_explicit_dataclass_assumption():
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ParsedSourceInput:\n"
+        "    tree: ast.AST\n"
+    )
+
+    result = _r10_qualified_ast_result(
+        source,
+        assume=False,
+    )
+
+    _r10_assert_rejected(result)
+
+
+@pytest.mark.parametrize(
+    "annotation_semantics",
+    [None, "STRINGIFIED"],
+)
+def test_r10_requires_deferred_annotation_semantics(
+    annotation_semantics,
+):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class ParsedSourceInput:\n"
+        "    tree: ast.AST\n"
+    )
+
+    result = _r10_qualified_ast_result(
+        source,
+        annotation_semantics=annotation_semantics,
+    )
+
+    _r10_assert_rejected(result)
+
+
 def test_external_assumption_normal_model_still_unknown():
     result = _model({"pkg.__init__": "import os\n"}, "pkg")
     assert result.outcome == "UNKNOWN"
```

# FINAL_VERDICT
PASS for the exact supplied R10 patch, focused tests, and post-change MCP source parity. Runtime import safety and persistent MCP interpreter adoption remain UNKNOWN.
