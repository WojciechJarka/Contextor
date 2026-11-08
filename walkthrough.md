# TASK
P15-R9

# PREFLIGHT
DIRECT_EVIDENCE: Contextor get_module_context and get_symbol_implementation resolved package_model.py at canonical revision 1146, canonical_state=fresh, workspace_sync=verified. All three production anchors and the test insertion anchor matched. Existing source/test diff was empty. Interpreter: repository `.venv\Scripts\python.exe`, CPython 3.15.2.

# HEAD_BEFORE
6e2eff77fe1041ee6f072caebbe230a90f1a3160. Worktree clean before R9. This differs from the historical D9 handoff HEAD; no reset was performed.

# FILES_CHANGED
- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py

# EXACT_PATCH_VERIFICATION
CONTRACT_PROVED: the three supplied production changes were applied verbatim: single `ValueError` base allowance; `CHECK_BUILTIN_CLASS_BASE` before class-body steps; evaluator shadow check before `DEFINE_PASSIVE_CLASS`. The exact supplied test block was inserted before the named anchor. No other production/test changes.

# TARGETED_TESTS
`& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_package_model.py`: 155 passed, 0 failed, 0 skipped (16.68s). `git diff --check`: PASS.

# MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: `get_live_events(after_revision=1146)` returned continuous `desktop_watcher` update_file for package_model.py at revision 1147, resync_required=false. A later get_module_context returned canonical_state=fresh, workspace_sync=verified, revision 1148, syntax errors=0. `cycle_semantics=stale`; 16 structural warnings remain. The first immediate post-event module read was unverified; the later verified read is the final parity evidence. No FULL analysis, update_file, or restart.

# BUILTIN_BASE_EVALUATION_ORDER
CODE_PATH_PROVED: the new check step is compiled before existing class-body steps and evaluated before class binding. Successful check emits no public event. The test verifies SourceError definition before child import.

# SHADOWING_NEGATIVE_REGRESSIONS
CONTRACT_PROVED by tests: prior literal or imported module binding for `ValueError` yields UNKNOWN without defining CustomError; literal shadowing prevents its class-body import event. Unsupported bases and executable class body remain UNKNOWN.

# R7_R8_REGRESSION_STATUS
CONTRACT_PROVED by the targeted file: all 155 tests pass; existing R7/R8 tests were preserved.

# AUTHORITY_LIMITATIONS
Focused model tests and Contextor indexing do not prove actual CPython import execution or persistent MCP interpreter adoption of the changed code. Conditional model acceptance is not runtime safety. The 16 structural warnings were not suppressed.

# FULL_DIFFS
```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index acfa5bd..c9600af 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -277,7 +277,15 @@ def _safe_passive_class_definition(
     if (
         not statement.name.isidentifier()
         or statement.name.startswith("__")
-        or statement.bases
+        or (
+            bool(statement.bases)
+            and (
+                conditional_dataclass
+                or len(statement.bases) != 1
+                or type(statement.bases[0]) is not ast.Name
+                or statement.bases[0].id != "ValueError"
+            )
+        )
         or statement.keywords
         or (
             bool(statement.decorator_list)
@@ -911,6 +919,14 @@ def _compile(
             ):
                 return None
 
+            if stmt.bases:
+                steps.append(
+                    _Step(
+                        "CHECK_BUILTIN_CLASS_BASE",
+                        target="ValueError",
+                    )
+                )
+
             for body_statement in stmt.body:
                 if isinstance(body_statement, ast.Assign):
                     steps.append(
@@ -2021,6 +2037,17 @@ def evaluate_package_import_order(
                 )
             )
 
+        elif step.op == "CHECK_BUILTIN_CLASS_BASE":
+            if (
+                step.target != "ValueError"
+                or "ValueError" in namespaces[module]
+            ):
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.target,
+                )
+
         elif step.op == "DEFINE_PASSIVE_CLASS":
             namespaces[module][step.binding] = (
                 "\x00PASSIVE_CLASS:"
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 76b8312..cf35e22 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -300,6 +300,164 @@ def test_r8_optional_class_requires_deferred_annotations(
     _r8_assert_rejected(result)
 
 
+def _r9_builtin_base_result(source):
+    return evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(
+                source + "\nfrom .child import token\n"
+            ),
+            "pkg.child": ast.parse("token = 7\n"),
+            "pkg.side": ast.parse("ValueError = 123\n"),
+        },
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+    )
+
+
+def test_r9_sourceerror_shape_crosses_builtin_base():
+    source = (
+        "class SourceError(ValueError):\n"
+        '    """Structured source error."""\n'
+        "    def __init__(self, message: str, *, "
+        'error_status: str = "ERROR", '
+        "line_number: int | None = None, "
+        "column_number: int | None = None, "
+        "detail_message: str | None = None) -> None:\n"
+        "        super().__init__(message)\n"
+        "        self.error_status = error_status\n"
+    )
+
+    result = _r9_builtin_base_result(source)
+
+    assert result.outcome == "MODEL_PASS"
+    assert result.assumed_dataclass_decorations == ()
+
+    events = list(result.events)
+
+    defined = next(
+        i for i, event in enumerate(events)
+        if event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "SourceError"
+    )
+
+    imported = next(
+        i for i, event in enumerate(events)
+        if event.operation == "START_IMPORT"
+        and event.target == "pkg.child"
+    )
+
+    assert defined < imported
+    assert result.reached_unmodeled_import is None
+
+
+def test_r9_simple_builtin_exception_subclass():
+    result = _r9_builtin_base_result(
+        "class CustomError(ValueError):\n"
+        "    pass\n"
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "CustomError"
+        for event in result.events
+    )
+
+
+@pytest.mark.parametrize(
+    "declaration",
+    [
+        "class CustomError(Exception):",
+        "class CustomError(BaseException):",
+        "class CustomError(UnknownBase):",
+        "class CustomError(pkg.ValueError):",
+        "class CustomError(ValueError, Exception):",
+        "class CustomError(ValueError, metaclass=Meta):",
+        "@decorator\nclass CustomError(ValueError):",
+    ],
+)
+def test_r9_rejects_unmodeled_bases(declaration):
+    result = _r9_builtin_base_result(
+        declaration + "\n    pass\n"
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "CustomError"
+        for event in result.events
+    )
+
+
+def test_r9_rejects_shadowed_builtin_before_class_body():
+    result = _r9_builtin_base_result(
+        "ValueError = 123\n"
+        "class CustomError(ValueError):\n"
+        "    import pkg.side\n"
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.symbol == "ValueError"
+
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "CustomError"
+        for event in result.events
+    )
+
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.side"
+        for event in result.events
+    )
+
+
+def test_r9_rejects_imported_base_shadowing():
+    result = _r9_builtin_base_result(
+        "from .side import ValueError\n"
+        "class CustomError(ValueError):\n"
+        "    pass\n"
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.symbol == "ValueError"
+
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "CustomError"
+        for event in result.events
+    )
+
+
+def test_r9_rejects_executable_class_body():
+    result = _r9_builtin_base_result(
+        "class CustomError(ValueError):\n"
+        "    execute_unknown_code()\n"
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "CustomError"
+        for event in result.events
+    )
+
+
+def test_r9_existing_plain_class_unchanged():
+    result = _r9_builtin_base_result(
+        "class PlainClass:\n"
+        "    pass\n"
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "PlainClass"
+        for event in result.events
+    )
+
+
 def test_external_assumption_normal_model_still_unknown():
     result = _model({"pkg.__init__": "import os\n"}, "pkg")
     assert result.outcome == "UNKNOWN"
```

# FINAL_VERDICT
PASS for the exact R9 patch, focused tests, and post-change Contextor source parity. Runtime cycle safety and persistent MCP interpreter adoption remain UNKNOWN.
