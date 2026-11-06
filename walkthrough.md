# CONTEXTOR C16-B03-P1D3D-R1

## FILES_CHANGED

- tests/test_cycle_semantics_optional_child_full_preview.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2, `-B -m pytest -q -rs -p no:cacheprovider`, basetemp outside repository. Two specified drift tests: 2 passed in 3.46 s. Five specified modules: 62 passed in 35.58 s. `git diff --check` passed. No full suite.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP `get_module_context` for changed test: canonical_state=fresh, workspace_sync=verified, canonical_revision=1027, advisory_warning=null, syntax_errors=0. Structural DFS cycles=16, fresh. Cycle semantics family=stale. No FULL outside tests, update_file, backend restart, or commit.

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_optional_child_full_preview.py b/tests/test_cycle_semantics_optional_child_full_preview.py
index 0c86154..b4d5b11 100644
--- a/tests/test_cycle_semantics_optional_child_full_preview.py
+++ b/tests/test_cycle_semantics_optional_child_full_preview.py
@@ -214,7 +214,7 @@ def test_optional_source_drift_fails_closed(
     def drifted(*args, **kwargs):
         if kwargs.get("source_capture_module_ids") is not None:
             (root / "pkg" / "child.py").write_bytes(
-                b"changed = True\n"
+                b"import pkg.helper\n# source drift\n"
             )
         return original(*args, **kwargs)
 
@@ -240,6 +240,41 @@ def test_optional_source_drift_fails_closed(
     assert state.cycle_partial_source_publication is None
 
 
+def test_optional_import_graph_drift_fails_closed(
+    tmp_path, isolated_dirs, monkeypatch,
+):
+    root = _repo(tmp_path)
+    original = facade_module.index_repository
+
+    def drifted(*args, **kwargs):
+        if kwargs.get("source_capture_module_ids") is not None:
+            (root / "pkg" / "child.py").write_bytes(
+                b"changed = True\n"
+            )
+        return original(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module, "index_repository", drifted
+    )
+
+    result = _run(
+        root,
+        cycle_source_preparation_preview=True,
+        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
+    )
+
+    preview = result.cycle_source_preparation_preview
+
+    assert preview.status == "UNAVAILABLE"
+    assert preview.reason == "VERIFY_REINDEX_GRAPH_CHANGED"
+    assert preview.manifest is None
+    assert preview.source_selection == "OPTIONAL_NAMED_CHILDREN"
+
+    state, _ = _persisted(root)
+    assert state.cycle_source_publication is None
+    assert state.cycle_partial_source_publication is None
+
+
 def test_legacy_default_source_selection_unchanged(
     tmp_path, isolated_dirs,
 ):
```

## FINAL_VERDICT

PASS
