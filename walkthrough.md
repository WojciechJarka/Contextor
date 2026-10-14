TASK: CONTEXTOR_B0G4C17F_DIAGNOSTIC_TEST_NAME_COLLISIONS_FIX
HEAD_BEFORE: da56cd5233458b6839bfcdb18c1b6f7dd1ee6874
HEAD_AFTER: da56cd5233458b6839bfcdb18c1b6f7dd1ee6874
GIT_STATUS:
 M tests/test_cycle_semantics_diagnostic_view.py

LIVE_REVISION_BEFORE: 445
LIVE_REVISION_AFTER: 446
ACTIVITY_EPOCH: 1beab26da2ff4932852caa7db6ff4242
FILES_CHANGED: tests/test_cycle_semantics_diagnostic_view.py only (walkthrough.md is report artifact)
ORIGINAL_COLLISION_EVIDENCE: DIRECT_EVIDENCE get_name_collisions at revision 445 returned exactly four NAME_COLLISION warnings for variable D/F/G/I, each pairing tests.test_cycle_semantics_closure_witness with tests.test_cycle_semantics_diagnostic_view. Canonical collisions fresh, cycles 16/fresh, resync_required=false. Owner test module had zero direct/downstream consumers; state verified at revision 445.
EXACT_IDENTIFIER_RENAMES: Token-aware NAME-only replacement, 35 occurrences: D -> C17_DIRECT_SITE; F -> C17_FUNCTION_SITE; G -> C17_GUARDED_SITE; I -> C17_INDIRECT_SITE. Required tuple values unchanged. Literal grep found no obsolete D/F/G/I identifier in modified file. No strings/comments/attributes or other identifiers replaced.
TEST_SEMANTICS_PRESERVED: Every test function, parametrization, assertion, fixture, expected category and API usage retained; isolated and focused suites passed. git diff --check passed.
ISOLATED_TEST_RESULTS: .\.venv\Scripts\python.exe -B -m pytest -q tests/test_cycle_semantics_diagnostic_view.py => 17 passed in 1.18s.
FOCUSED_TEST_RESULTS: .\.venv\Scripts\python.exe -B -m pytest -q [the 17 task-specified cycle_semantics files] => 289 passed in 20.33s.
LIVE_EVENT_CONTINUITY: DIRECT_EVIDENCE get_live_events after revision 445 returned desktop_watcher UPDATED for modified test at revision 446; continuity=continuous, same epoch, resync_required=false. diagnostic_changes total 4 RESOLVED collision records, payload bounded/truncated to three details.
WORKSPACE_SYNC: DIRECT_EVIDENCE modified test get_file_edit_context workspace_sync=verified and canonical_state=fresh at revision 446.
CANONICAL_COLLISION_COUNT_BEFORE_AFTER: 4/fresh -> 0/fresh. Post-edit get_name_collisions total=0 and details=[].
SPECIFIC_COLLISION_PAIR_REMOVAL: DIRECT_EVIDENCE all four original D/F/G/I pairs absent from full canonical collision result (total 0); event reports four RESOLVED, though only first three are shown in bounded event detail.
STRUCTURAL_CYCLE_COUNT_BEFORE_AFTER: 16/fresh -> 16/fresh. Path identity not independently compared.
CANONICAL_FRESHNESS: Revision 446; syntax errors 0/fresh, graph/cycles/collisions fresh; all reported state families for modified test fresh.
NO_PRODUCTION_MODIFICATION: git diff for contextor/core/cycle_semantics/diagnostic_view.py empty; no production file edited.
NO_WARNING_SUPPRESSION: No collision engine, warning policy or diagnostic suppression modified.
FINAL_VERDICT: B0G4C17F_FINAL_PASS

FULL_DIFFS:
diff --git a/tests/test_cycle_semantics_diagnostic_view.py b/tests/test_cycle_semantics_diagnostic_view.py
index d922566..5f4ebbf 100644
--- a/tests/test_cycle_semantics_diagnostic_view.py
+++ b/tests/test_cycle_semantics_diagnostic_view.py
@@ -25,10 +25,10 @@ from contextor.core.cycle_semantics.diagnostic_view import (
 )
 
 
-D = ("MODULE_TOP_LEVEL", "FROM_BASE")
-F = ("FUNCTION_SCOPED", "FROM_BASE")
-G = ("GUARDED_TOP_LEVEL", "FROM_BASE")
-I = ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER")
+C17_DIRECT_SITE = ("MODULE_TOP_LEVEL", "FROM_BASE")
+C17_FUNCTION_SITE = ("FUNCTION_SCOPED", "FROM_BASE")
+C17_GUARDED_SITE = ("GUARDED_TOP_LEVEL", "FROM_BASE")
+C17_INDIRECT_SITE = ("MODULE_TOP_LEVEL", "PARENT_INITIALIZER")
 
 
 def _pipeline(graph, specs):
@@ -112,7 +112,7 @@ def _digest(graph, specs):
 def test_direct_cycle_is_still_structural():
     result = _digest(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [D]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_DIRECT_SITE]},
     )
     component = result.components[0]
 
@@ -129,7 +129,7 @@ def test_direct_cycle_is_still_structural():
 def test_function_local_edge_retains_closure_and_sites():
     result = _digest(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [F]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
     )
     component = result.components[0]
 
@@ -159,9 +159,9 @@ def test_multiple_nondirect_edges_without_one_edge_return():
     component = _digest(
         {"a": {"b"}, "b": {"c"}, "c": {"a"}},
         {
-            ("a", "b"): [D],
-            ("b", "c"): [F],
-            ("c", "a"): [F],
+            ("a", "b"): [C17_DIRECT_SITE],
+            ("b", "c"): [C17_FUNCTION_SITE],
+            ("c", "a"): [C17_FUNCTION_SITE],
         },
     ).components[0]
 
@@ -179,7 +179,7 @@ def test_multiple_nondirect_edges_without_one_edge_return():
 def test_guarded_candidate_keeps_uncertainty():
     component = _digest(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [G]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_GUARDED_SITE]},
     ).components[0]
 
     witness = component.single_edge_closures[0]
@@ -194,7 +194,7 @@ def test_guarded_candidate_keeps_uncertainty():
 def test_indirect_package_candidate_keeps_uncertainty():
     component = _digest(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [I]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_INDIRECT_SITE]},
     ).components[0]
 
     assert component.single_edge_closures[0].classification == (
@@ -206,7 +206,7 @@ def test_indirect_package_candidate_keeps_uncertainty():
 def test_missing_lexical_evidence_is_not_dropped():
     component = _digest(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D]},
+        {("a", "b"): [C17_DIRECT_SITE]},
     ).components[0]
 
     assert component.structural_edge_count == 2
@@ -227,7 +227,7 @@ def test_missing_lexical_evidence_is_not_dropped():
 def test_unmatched_lexical_site_preserved():
     component = _digest(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): []},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): []},
     ).components[0]
 
     assert any(
@@ -244,8 +244,8 @@ def test_two_independent_sccs_remain_distinct():
             "x": {"y"}, "y": {"x"},
         },
         {
-            ("a", "b"): [D], ("b", "a"): [F],
-            ("x", "y"): [D], ("y", "x"): [D],
+            ("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE],
+            ("x", "y"): [C17_DIRECT_SITE], ("y", "x"): [C17_DIRECT_SITE],
         },
     ).components
 
@@ -257,7 +257,7 @@ def test_two_independent_sccs_remain_distinct():
 
 @pytest.mark.parametrize(
     "site",
-    [D, F],
+    [C17_DIRECT_SITE, C17_FUNCTION_SITE],
 )
 def test_self_loop_preserved(site):
     component = _digest(
@@ -273,7 +273,7 @@ def test_self_loop_preserved(site):
 def test_mismatched_activation_rejected():
     sites, activation, closures = _pipeline(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [F]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
     )
 
     view = activation.components[0]
@@ -299,7 +299,7 @@ def test_mismatched_activation_rejected():
 def test_mismatched_closure_rejected():
     sites, activation, closures = _pipeline(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [F]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
     )
 
     component = closures.components[0]
@@ -326,7 +326,7 @@ def test_mismatched_closure_rejected():
 def test_mismatched_site_topology_rejected():
     sites, activation, closures = _pipeline(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [F]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
     )
 
     wrong_component = replace(
@@ -349,7 +349,7 @@ def test_mismatched_site_topology_rejected():
 def test_mismatched_site_counts_rejected():
     sites, activation, closures = _pipeline(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [F]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
     )
     wrong = replace(
         sites.components[0],
@@ -369,7 +369,7 @@ def test_mismatched_site_counts_rejected():
 def test_determinism_immutability_and_json():
     inputs = _pipeline(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [F]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
     )
     before = tuple(repr(item) for item in inputs)
 
@@ -403,7 +403,7 @@ def test_bad_argument_types():
 
     sites, activation, closures = _pipeline(
         {"a": {"b"}, "b": {"a"}},
-        {("a", "b"): [D], ("b", "a"): [F]},
+        {("a", "b"): [C17_DIRECT_SITE], ("b", "a"): [C17_FUNCTION_SITE]},
     )
 
     with pytest.raises(TypeError):
