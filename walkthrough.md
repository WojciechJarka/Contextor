# CONTEXTOR C16-B03-P1D3F2-R1

## FILES_CHANGED

- tests/test_cycle_semantics_optional_generation_verification.py

## TARGETED_TESTS

DIRECT_EVIDENCE: CPython 3.15.2; `-B -m pytest -q -rs -p no:cacheprovider`; basetemp outside repository. Filtered test: 1 passed, 13 deselected. Full target module: 14 passed. Six specified modules: 90 passed in 31.98 s. `git diff --check` passed. No full suite.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP changed-test module context: canonical_revision=1041, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, syntax_errors=0. Structural DFS cycles=16, fresh; cycle_semantics family=stale. No production FULL, update_file, backend restart, or commit.

## FULL_DIFFS

```diff
diff --git a/tests/test_cycle_semantics_optional_generation_verification.py b/tests/test_cycle_semantics_optional_generation_verification.py
index 3a9dfc2..b6df329 100644
--- a/tests/test_cycle_semantics_optional_generation_verification.py
+++ b/tests/test_cycle_semantics_optional_generation_verification.py
@@ -175,19 +175,27 @@ def test_modified_canonical_graph_rejected(
 ):
     case = list(_case(tmp_path))
     changed = copy(case[2])
-    changed_graph = copy(changed.dependency_graph)
-    changed_graph.hard_edges = {
+
+    original_graph = changed.dependency_graph
+
+    changed_edges = {
         name: set(targets)
-        for name, targets in changed_graph.hard_edges.items()
+        for name, targets in original_graph.hard_edges.items()
     }
-    changed_graph.hard_edges["pkg.a"].add("pkg.helper")
-    changed.dependency_graph = changed_graph
+    changed_edges["pkg.a"].add("pkg.helper")
+
+    changed.dependency_graph = replace(
+        original_graph,
+        hard_edges=changed_edges,
+    )
     case[2] = changed
 
     result = _assess(case)
 
     assert result.status == "UNAVAILABLE"
-    assert result.reason == "OPTIONAL_DECLARATIONS_GENERATION_MISMATCH"
+    assert result.reason == (
+        "OPTIONAL_DECLARATIONS_GENERATION_MISMATCH"
+    )
 
 
 def test_changed_canonical_import_facts_rejected(
```

## FINAL_VERDICT

PASS
