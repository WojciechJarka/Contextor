# CONTEXTOR C16-B03-P1D3E-R1

## FILES_CHANGED

- contextor/core/cycle_semantics/generation_manifest.py
- tests/test_cycle_semantics_optional_child_manifest_digest.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2; `-B -m pytest -q -rs -p no:cacheprovider`; basetemp outside repository. Filtered new test: 2 passed, 15 deselected. Five specified modules: 77 passed in 14.59 s. `git diff --check` passed. No full suite.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Final Contextor MCP module contexts for both changed modules: canonical_revision=1034 for test and 1033 for production module; canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. An intermediate test module read at revision 1033 was out_of_sync; final revision 1034 verified. Cycle semantics family remains stale. No production FULL, update_file, backend restart, or commit.

## FULL_DIFFS

```diff
diff --git a/contextor/core/cycle_semantics/generation_manifest.py b/contextor/core/cycle_semantics/generation_manifest.py
index 066f43e..7805f93 100644
--- a/contextor/core/cycle_semantics/generation_manifest.py
+++ b/contextor/core/cycle_semantics/generation_manifest.py
@@ -340,10 +340,12 @@ def verify_prepared_optional_manifest_digest(
             or component.members != tuple(sorted(set(component.members)))
             or component.preparation_state != "PREPARED_UNPUBLISHED"
             or component.reason is not None
+            or type(component.model_classification) is not str
             or component.model_classification not in {
                 "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
                 "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
             }
+            or type(component.model_kind) is not str
             or component.model_kind not in {
                 "FLAT_MODULE",
                 "REGULAR_PACKAGE",
diff --git a/tests/test_cycle_semantics_optional_child_manifest_digest.py b/tests/test_cycle_semantics_optional_child_manifest_digest.py
index a4e6787..125c39a 100644
--- a/tests/test_cycle_semantics_optional_child_manifest_digest.py
+++ b/tests/test_cycle_semantics_optional_child_manifest_digest.py
@@ -177,6 +177,32 @@ def test_modified_component_source_signature_rejected(tmp_path):
     assert not verify_prepared_optional_manifest_digest(changed)
 
 
+@pytest.mark.parametrize(
+    "field,value",
+    [
+        ("model_classification", []),
+        ("model_kind", {}),
+    ],
+)
+def test_unhashable_component_model_fields_fail_closed(
+    tmp_path, field, value,
+):
+    manifest = _prepare(_fixture(tmp_path))
+    component = manifest.components[0]
+
+    malformed = replace(
+        manifest,
+        components=(
+            replace(component, **{field: value}),
+        ),
+    )
+
+    assert (
+        verify_prepared_optional_manifest_digest(malformed)
+        is False
+    )
+
+
 def test_missing_optional_child_blocks_complete_digest(tmp_path):
     case = list(_fixture(tmp_path))
     case[4] = dict(case[4])
```

## FINAL_VERDICT

PASS
