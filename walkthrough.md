# CONTEXTOR P1D3-WARN-5H — package layout fail-fast

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `23ad36f1eeebbd0a1f69986d340e48a3ffaf7fde`; initial worktree clean. Contextor MCP resolved both target modules. SEARCH 1, SEARCH 2 (the original lower block), and the test SEARCH each occurred exactly once in current source. WARN-5G docstring tests were present.

## SEARCH_REPLACE_RESULT

- DIRECT_EVIDENCE: Applied exactly the three architect-authored substitutions in the two authorized Python files. The lower layout block was removed after inserting the preflight above CPython compile validation. No other source/test file changed.

## NAMESPACE_FAIL_FAST

- CODE_PATH_PROVED: `evaluate_package_import_order` now builds layout and rejects the first unsupported node before compiling the entire source mapping. The added test monkeypatches the module's `compile` boundary, obtains `UNKNOWN` targeting `pkg`, and confirms zero compile calls and zero model events.
- CONTRACT_PROVED: Namespace candidates remain UNKNOWN; this test does not claim general runtime import safety.

## COMPILATION_PARITY

- CONTRACT_PROVED: A regular package with a compile-time invalid nested `break` remains UNKNOWN at `pkg.a` with no events. A regular safe import remains MODEL_PASS and succeeds under actual CPython import. Existing focused hazard/parity tests pass.
- CODE_PATH_PROVED: The change only reorders layout rejection before CPython compile validation for unsupported layouts. No source AST mutation was added.

## TARGETED_REGRESSIONS

- DIRECT_EVIDENCE: `python -m py_compile` on both changed Python files passed.
- DIRECT_EVIDENCE: `python -m pytest -q -rs tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_scenarios.py tests/test_cycle_semantics_passive_functions.py tests/test_cycle_semantics_package_layout.py` → `134 passed in 19.60s`.
- DIRECT_EVIDENCE: `git diff --check --` both changed Python files passed.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: MCP at canonical revision 895 reports `package_model.py` workspace_sync verified, test file workspace_sync out_of_sync. A Desktop watcher event at revision 895 updated production; no corresponding test-file event was observed by the final bounded read. Canonical graph/cycles fresh, cycle_semantics stale. Structural DFS cycles remain 16. `get_live_events` returned activity_epoch `d08a5a93184d473f8bc124596f4a44c9`, resync_required false.
- UNKNOWN: Test-file canonical sync may occur later; it was not verified at this stage. Active loaded-code adoption is also unproved. No FULL, update_file or restart was performed.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`

`walkthrough.md` is the report and is excluded from source/test FILES_CHANGED.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index cbe6822..6323ba5 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -630,6 +630,29 @@ def evaluate_package_import_order(
     ):
         return result("UNKNOWN")
 
+    # An unsupported package layout cannot establish MODEL_PASS,
+    # regardless of the AST contents. Reject before repeatedly
+    # compiling an entire large SCC source closure.
+    try:
+        layout = build_package_layout(indexed_sources)
+    except (TypeError, ValueError):
+        return result("UNKNOWN")
+
+    nodes = {node.name: node for node in layout.nodes}
+    unsupported_layout = next(
+        (
+            node.name
+            for node in layout.nodes
+            if node.kind not in {
+                "REGULAR_PACKAGE",
+                "MODULE_FILE",
+            }
+        ),
+        None,
+    )
+    if unsupported_layout is not None:
+        return result("UNKNOWN", unsupported_layout)
+
     # AST parsing alone does not enforce every CPython
     # compilation rule. Even an uncalled function body
     # may contain a compile-time SyntaxError.
@@ -654,13 +677,6 @@ def evaluate_package_import_order(
         ):
             return result("UNKNOWN", indexed_id)
 
-    try:
-        layout = build_package_layout(indexed_sources)
-    except (TypeError, ValueError):
-        return result("UNKNOWN")
-
-    nodes = {node.name: node for node in layout.nodes}
-
     logical_sources: dict[str, ast.Module] = {}
     packages: set[str] = set()
 
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index eff81d0..a80736d 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -279,6 +279,62 @@ def test_from_package_child_loads_indexed_child(tmp_path):
     assert _actual(tmp_path, source, "entry")
 
 
+def test_warn_5h_namespace_rejected_before_ast_compilation(
+    monkeypatch,
+):
+    from contextor.core.cycle_semantics import package_model
+
+    calls = []
+
+    def forbidden_compile(*args, **kwargs):
+        calls.append((args, kwargs))
+        raise AssertionError(
+            "unsupported layout must reject before compilation"
+        )
+
+    monkeypatch.setattr(
+        package_model,
+        "compile",
+        forbidden_compile,
+        raising=False,
+    )
+
+    result = _model(
+        {"pkg.sub": "value=7"},
+        "pkg.sub",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.target_module == "pkg"
+    assert result.events == ()
+    assert calls == []
+
+
+def test_warn_5h_regular_layout_still_checks_compile_time_errors():
+    source = {
+        "pkg.__init__": "pass",
+        "pkg.a": "def f():\n    break",
+    }
+
+    result = _model(source, "pkg.a")
+
+    assert result.outcome == "UNKNOWN"
+    assert result.target_module == "pkg.a"
+    assert result.events == ()
+
+
+def test_warn_5h_regular_layout_still_proves_safe_import(tmp_path):
+    source = {
+        "pkg.__init__": "value=1\nimport pkg.a",
+        "pkg.a": "import pkg\nx=pkg.value",
+    }
+
+    result = _model(source, "pkg")
+
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, source, "pkg")
+
 def test_namespace_ambiguous_external_unknown():
     assert _model(
         {"pkg.sub": "value=7"},
```

## REMAINING_UNKNOWN

- Test-file workspace synchronization is out_of_sync at revision 895. Cycle semantics is stale after edits, and loaded-code adoption is unverified. Focused synthetic tests do not certify current repository SCCs or runtime safety.

## FINAL_IMPLEMENTER_OBSERVATION

Exact substitutions and focused regressions passed; namespace fail-fast is covered. Structural cycle count remains 16. STOP after WARN-5H.
