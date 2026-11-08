# TASK
P15-R11-F1

# PREFLIGHT
DIRECT_EVIDENCE: Contextor module contexts for `package_model.py` and `test_cycle_semantics_package_model.py` returned canonical revision 1153, `canonical_state=fresh`, `workspace_sync=verified`. The exact later-loop production anchor and exact test insertion anchor matched. Repository `.venv\Scripts\python.exe`: CPython 3.15.2.

# HEAD_BEFORE
`3ac1cee472c019d76d13ea7fcc887a7ba5a0bedf`; worktree clean before F1.

# PREEXISTING_R11_CHANGES
The R11 implementation and tests were already in current HEAD. They were preserved; no A–G patch or earlier R11 test block was reapplied.

# ROOT_CAUSE
CODE_PATH_PROVED in R11: the initial conditional dataclass validation accepted `field(hash=False)`, but the preserved later class-body loop called `_safe_annassign`, which rejected its `ast.Call` value. The R11 positive test therefore returned UNKNOWN before Module decoration.

# EXACT_CORRECTION
The one specified later-loop AnnAssign block was replaced verbatim. It retains `_safe_annassign` and adds only the exact conditional dataclass exception for a simple valid name target and `_exact_restricted_dataclass_hash_field_call(value)`. The supplied three regression cases were inserted verbatim. No other production behavior was edited.

# FILES_CHANGED
- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`

# TARGETED_TESTS
`& .\.venv\Scripts\python.exe -m pytest -q -rs tests/test_cycle_semantics_package_model.py`: **204 passed, 0 failed, 0 skipped** (18.15 s). `git diff --check`: PASS.

# MCP_POST_CHANGE_AUDIT
DIRECT_EVIDENCE: desktop_watcher UPDATED production file at revision 1154 and test file at revision 1155. `get_live_events` continuity continuous, `resync_required=false`. Both target module contexts at revision 1155: `canonical_state=fresh`, `workspace_sync=verified`; syntax errors 0; `cycle_semantics=stale`. An intermediate test-file read at revision 1154 was out_of_sync before its watcher event; final revision 1155 resolves that parity gap. No FULL analysis, `update_file`, restart, commit, or push.

# POSITIVE_R11_REGRESSION
CONTRACT_PROVED by the passing targeted file: the previously failing `test_r11_real_module_shape_crosses_class` now reaches MODEL_PASS with the expected ImportRef and Module conditional decoration records and ordered class events.

# NEGATIVE_F1_REGRESSIONS
CONTRACT_PROVED: a plain class with `field(hash=False)` stays UNKNOWN; non-simple attribute/subscript field targets remain rejected. The F1 addition contains one plain-class case and two parametrized target cases.

# R7_R10_REGRESSION_STATUS
All existing tests in the target file pass within the 204 passing cases. No full-suite or runtime certification claim.

# AUTHORITY_LIMITATIONS
Focused model tests and watcher indexing do not prove actual CPython runtime cycle safety or persistent MCP interpreter adoption of the changed code. Conditional MODEL_PASS is not runtime proof. No warning suppression.

# FULL_DIFFS
```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 4ba018e..d01ac09 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -434,10 +434,25 @@ def _safe_passive_class_definition(
         if isinstance(body_statement, (ast.Import, ast.ImportFrom)):
             continue
 
-        if isinstance(body_statement, ast.AnnAssign) and _safe_annassign(
-            body_statement, annotation_semantics,
-        ):
-            continue
+        if isinstance(body_statement, ast.AnnAssign):
+            if _safe_annassign(
+                body_statement, annotation_semantics,
+            ):
+                continue
+
+            if (
+                conditional_dataclass
+                and type(body_statement.target) is ast.Name
+                and body_statement.simple == 1
+                and body_statement.target.id.isidentifier()
+                and not body_statement.target.id.startswith("__")
+                and _exact_restricted_dataclass_hash_field_call(
+                    body_statement.value
+                )
+            ):
+                continue
+
+            return False
 
         if isinstance(body_statement, ast.Assign):
             if (
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index a50c607..bf0bce6 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -1077,6 +1077,41 @@ def test_r11_requires_deferred_annotation_semantics(
     _r11_assert_module_rejected(result)
 
 
+def test_r11_f1_plain_class_field_call_remains_unknown():
+    result = _r11_module_result(
+        "class Plain:\n"
+        "    imports: list[ImportRef] = field(hash=False)\n"
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "Plain"
+        for event in result.events
+    )
+
+
+@pytest.mark.parametrize(
+    "field_target",
+    [
+        "holder.imports",
+        "holder['imports']",
+    ],
+)
+def test_r11_f1_field_call_requires_simple_name_target(
+    field_target,
+):
+    source = (
+        "@dataclass(frozen=True)\n"
+        "class Module:\n"
+        f"    {field_target}: list[ImportRef] = field(hash=False)\n"
+    )
+
+    result = _r11_module_result(source)
+
+    _r11_assert_module_rejected(result)
+
+
 def test_external_assumption_normal_model_still_unknown():
     result = _model({"pkg.__init__": "import os\n"}, "pkg")
     assert result.outcome == "UNKNOWN"
```

# FINAL_VERDICT
PASS for the exact F1 correction, all 204 targeted tests, and verified post-change Contextor parity. Runtime cycle safety remains UNKNOWN.
