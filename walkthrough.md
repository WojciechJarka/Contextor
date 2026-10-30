# CONTEXTOR P1D3-WARN-5G — exact module docstring semantics

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `422c4e603e4ec0f27990904e1b56b0fdc1484df7`; initially only `walkthrough.md` was modified. Both Python targets were clean.
- DIRECT_EVIDENCE: Contextor MCP `get_file_edit_context` resolved production and test modules at revision 892, workspace_sync verified, graph/cycles/cycle_semantics fresh, structural DFS cycle count 16. Production had 11 direct consumers and `scenarios` among them.
- DIRECT_EVIDENCE: The supplied production SEARCH occurred exactly once after CRLF normalization; test SEARCH occurred exactly once. No source drift or anchor conflict.

## SEARCH_REPLACE_RESULT

- DIRECT_EVIDENCE: Applied the architect's two literal SEARCH→REPLACE blocks to exactly the authorized Python files. No independent refactor or contract change.

## DOCSTRING_SEMANTICS

- CODE_PATH_PROVED: `_compile` now skips only a leading `ast.Expr(ast.Constant(str))` at `_depth == 0`. The condition does not mutate the AST. Existing import-order steps remain in their original sequence after the skipped docstring.
- CONTRACT_PROVED: New positive test shows `MODEL_PASS` and actual CPython import success for the safe ordering. New hazard test shows `EARLY_BINDING_HAZARD`, target `pkg`, symbol `value`, and actual CPython import failure.

## NEGATIVE_CASES

- CONTRACT_PROVED: New tests retain `UNKNOWN` for a nonleading string expression, a string expression nested under `if True`, and a leading docstring followed by unsupported `raise`.
- CODE_PATH_PROVED: The existing `NAMESPACE_CANDIDATE` gate in `evaluate_package_import_order` precedes `_compile`; the change does not promote namespace candidates to MODEL_PASS.

## TARGETED_TESTS

- DIRECT_EVIDENCE: `python -m py_compile` on both changed files passed.
- DIRECT_EVIDENCE: `python -m pytest -q -rs tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_passive_functions.py` → `119 passed in 18.82s`.
- DIRECT_EVIDENCE: `git diff --check --` both changed Python files passed.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: MCP `get_module_context` for both modified files returned workspace_sync `verified`, canonical revision 894, canonical/graph/cycles fresh, structural DFS cycle count 16. `cycle_semantics` is `stale` at revision 894; no active FULL was run. The existing warning projection still reports 16 active warnings, 0 MODEL_PASS for the installed generation.
- UNKNOWN: Active Desktop/LIVE/MCP loaded-code adoption of the new local Python implementation was not established. Source synchronization is not loaded-code proof.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`

`walkthrough.md` was overwritten as the report and is excluded from source/test FILES_CHANGED.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 5d9a8c6..cbe6822 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -192,7 +192,19 @@ def _compile(
     if _depth >= 32:
         return None
 
-    for stmt in tree.body:
+    for statement_index, stmt in enumerate(tree.body):
+        if (
+            _depth == 0
+            and statement_index == 0
+            and isinstance(stmt, ast.Expr)
+            and isinstance(stmt.value, ast.Constant)
+            and type(stmt.value.value) is str
+        ):
+            # A module docstring literal has no import-time side effects.
+            # The restricted model cannot observe __doc__ through its
+            # supported attribute/import operations.
+            continue
+
         if (
             _depth == 0
             and typing_guard is not None
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index c5d2fa6..eff81d0 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -90,6 +90,83 @@ def test_parent_initializer_precedes_submodule(tmp_path):
     assert _actual(tmp_path, source, "pkg.sub")
 
 
+def test_warn_5g_module_docstrings_preserve_safe_order(tmp_path):
+    source = {
+        "pkg.__init__": (
+            '"""Package documentation."""\n'
+            "value=2\n"
+            "import pkg.sub"
+        ),
+        "pkg.sub": (
+            '"""Submodule documentation."""\n'
+            "import pkg\n"
+            "x=pkg.value"
+        ),
+    }
+
+    result = _model(source, "pkg")
+
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg")
+
+
+def test_warn_5g_docstrings_do_not_hide_early_binding_hazard(
+    tmp_path,
+):
+    source = {
+        "pkg.__init__": (
+            '"""Package documentation."""\n'
+            "import pkg.sub\n"
+            "value=2"
+        ),
+        "pkg.sub": (
+            '"""Submodule documentation."""\n'
+            "import pkg\n"
+            "x=pkg.value"
+        ),
+    }
+
+    result = _model(source, "pkg")
+
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.target_module == "pkg"
+    assert result.symbol == "value"
+    assert not _actual(tmp_path, source, "pkg")
+
+
+def test_warn_5g_nonleading_string_expression_remains_unknown():
+    source = {
+        "pkg.__init__": (
+            "pass\n"
+            "'not a module docstring'"
+        ),
+    }
+
+    assert _model(source, "pkg").outcome == "UNKNOWN"
+
+
+def test_warn_5g_nested_string_expression_remains_unknown():
+    source = {
+        "pkg.__init__": (
+            "if True:\n"
+            "    'not a module docstring'"
+        ),
+    }
+
+    assert _model(source, "pkg").outcome == "UNKNOWN"
+
+
+def test_warn_5g_docstring_does_not_hide_unsupported_effect():
+    source = {
+        "pkg.__init__": (
+            '"""Package documentation."""\n'
+            'raise RuntimeError("unsupported")'
+        ),
+    }
+
+    assert _model(source, "pkg").outcome == "UNKNOWN"
+
+
 def test_package_early_attribute_failure(tmp_path):
     source = {
         "pkg.__init__": "import pkg.sub\nvalue=2",
```

## REMAINING_UNKNOWN

- Active loaded-code adoption and fresh semantic re-evaluation of this repository remain unknown/stale respectively. No claim of current repository MODEL_PASS or runtime safety follows from the focused synthetic tests.

## FINAL_IMPLEMENTER_OBSERVATION

The literal change and focused regressions passed. Structural DFS cycles remain 16; canonical cycle_semantics is stale after source edits. STOP after WARN-5G.
