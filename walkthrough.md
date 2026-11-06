# CONTEXTOR C16-B03-P1D3F1-R1

## FILES_CHANGED

- tests/test_cycle_semantics_optional_generation_anchor.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2; `-B -m pytest -q -rs -p no:cacheprovider`; basetemp outside repository. Filtered test: 1 passed, 7 deselected. Six specified modules: 78 passed in 44.06 s. No full suite.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP changed-test module context: canonical_revision=1038, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Structural DFS cycles=16, fresh; cycle_semantics family=stale. No production FULL, update_file, or backend restart.

Git HEAD advanced during this task from supplied base `5a26774ef9e367ad47ca81db8a42827f6092a15a` to external `b5f5968c6b5d7fd06db87df8a01f44a7e84b7e1e` (`Auto-commit: Cleanup and update`). Agent did not create a commit. Full diff below is base to current HEAD for the changed file.

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_optional_generation_anchor.py b/tests/test_cycle_semantics_optional_generation_anchor.py
index 7c19f23..bb7270a 100644
--- a/tests/test_cycle_semantics_optional_generation_anchor.py
+++ b/tests/test_cycle_semantics_optional_generation_anchor.py
@@ -88,15 +88,40 @@ def test_identical_sources_distinct_full_generations(
     first_manifest = (
         first.cycle_source_preparation_preview.manifest
     )
+    _, first_metadata = _persisted(root)
 
     second = _optional(root)
     second_anchor = second.cycle_source_preparation_generation_anchor
     second_manifest = (
         second.cycle_source_preparation_preview.manifest
     )
+    _, second_metadata = _persisted(root)
+
+    assert (
+        first_anchor.revision,
+        first_anchor.state_id,
+        first_anchor.repo_id,
+        first_anchor.root_path,
+    ) == (
+        first_metadata.revision,
+        first_metadata.state_id,
+        first_metadata.repo_id,
+        first_metadata.root_path,
+    )
+
+    assert (
+        second_anchor.revision,
+        second_anchor.state_id,
+        second_anchor.repo_id,
+        second_anchor.root_path,
+    ) == (
+        second_metadata.revision,
+        second_metadata.state_id,
+        second_metadata.repo_id,
+        second_metadata.root_path,
+    )
 
     assert second_anchor.revision > first_anchor.revision
-    assert second_anchor.state_id == first_anchor.state_id
     assert second_anchor.repo_id == first_anchor.repo_id
     assert second_anchor.root_path == first_anchor.root_path
 
@@ -108,6 +133,7 @@ def test_identical_sources_distinct_full_generations(
         first_anchor.source_manifest_sha256
         == second_anchor.source_manifest_sha256
     )
+
     assert first_anchor != second_anchor
```

## FINAL_VERDICT

PASS
