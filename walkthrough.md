# CONTEXTOR C16-B03-P1D3B-R1

## FILES_CHANGED

- tests/test_cycle_semantics_optional_child_worker_manifest.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2; `-B -m pytest -q -rs -p no:cacheprovider`; basetemp `C:\Temp\Contextor_C16_P1D3B_R1_pytest_tmp` outside repository.

- Two specified tests: 2 passed.
- Five specified modules: 62 passed.
- No full suite run. `git diff --check` passed.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP `get_module_context` for `tests.test_cycle_semantics_optional_child_worker_manifest`: canonical_revision=1021, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Cycle semantics family remains stale; structural cycle count=16. No FULL, update_file, backend restart, or commit.

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_optional_child_worker_manifest.py b/tests/test_cycle_semantics_optional_child_worker_manifest.py
index 1082056..1782fe7 100644
--- a/tests/test_cycle_semantics_optional_child_worker_manifest.py
+++ b/tests/test_cycle_semantics_optional_child_worker_manifest.py
@@ -128,12 +128,17 @@ def test_default_mode_never_promotes_optional_evidence(tmp_path):
 def test_missing_optional_worker_capture_blocks_preparation(tmp_path):
     case = list(_pipeline(tmp_path))
     index = case[0]
+
     snapshots = dict(index.original_worker_source_snapshots)
+    modes = dict(index.original_worker_ast_modes)
+
     snapshots.pop("pkg.child")
+    modes.pop("pkg.child")
 
     case[0] = replace(
         index,
         original_worker_source_snapshots=snapshots,
+        original_worker_ast_modes=modes,
     )
 
     result = _prepare(case)
@@ -147,6 +152,30 @@ def test_missing_optional_worker_capture_blocks_preparation(tmp_path):
     assert result.source_selection == "OPTIONAL_NAMED_CHILDREN"
 
 
+def test_optional_worker_capture_ast_mode_domain_mismatch(tmp_path):
+    case = list(_pipeline(tmp_path))
+    index = case[0]
+
+    snapshots = dict(index.original_worker_source_snapshots)
+    snapshots.pop("pkg.child")
+
+    case[0] = replace(
+        index,
+        original_worker_source_snapshots=snapshots,
+    )
+
+    result = _prepare(case)
+
+    assert result.status == "UNAVAILABLE"
+    assert result.reason == (
+        "BINDING_INDEX_CAPTURE_SHAPE_INVALID"
+    )
+    assert result.manifest is None
+    assert result.component_preparations == ()
+    assert result.source_modules == ()
+    assert result.source_selection == "OPTIONAL_NAMED_CHILDREN"
+
+
 def test_changed_worker_bytes_block_preparation(tmp_path):
     case = list(_pipeline(tmp_path))
     index = case[0]
```

## FINAL_VERDICT

PASS
