STATUS=FINAL_PASS
FILES_CHANGED=tests/analysis/test_lineage_extraction.py; walkthrough.md
TEST_RESULTS=97 PASS; 2 PASS; 110 PASS; diff-check PASS. Reused evidence: production diff=NONE; D6 invariants PASS; canonical revision 555 fresh/verified; collisions=0; cycles=0.
FULL_DIFFS=
```diff
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 7a314d1..faf1160 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -13,6 +13,8 @@ from contextor.core.analysis.lineage_extraction import (
     extract_lineage_source_facts,
     parse_local_occurrence_id,
 )
+from contextor.core.analysis.lineage_extraction_emit import occurrence
+from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
 from contextor.core.domain.lineage_facts import (
     ExtractedOccurrenceRef,
     ExtractedSymbolicRef,
@@ -69,34 +71,28 @@ def test_stage_1c_occurrence_cache_reuses_same_ref():
         lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS,
     )
     assert reason is None
-    extractor = lineage_extraction_module._AnchorExtractor(paths, "pkg.py")
+    state = LineageExtractionState()
     node = tree.body[0].value
-    first = extractor._occurrence("expression_result", node)
-    second = extractor._occurrence("expression_result", node)
+    first = occurrence(state, paths, "expression_result", node)
+    second = occurrence(state, paths, "expression_result", node)
     assert first is second
     assert first.local_id == second.local_id
-    assert len(extractor.state._ids) == 1
+    assert len(state._ids) == 1
 
 
 def test_stage_1c_merge_frames_keeps_only_identical_occurrences():
-    tree = ast.parse("a = 1\nb = 2\nc = 3\n")
-    paths, reason = lineage_extraction_module._index_ast_paths(
-        tree,
-        lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS,
-    )
-    assert reason is None
-    extractor = lineage_extraction_module._AnchorExtractor(paths, "pkg.py")
+    state = LineageExtractionState()
     a = ExtractedOccurrenceRef("a")
     b1 = ExtractedOccurrenceRef("b1")
     b2 = ExtractedOccurrenceRef("b2")
-    merged = extractor._merge_frames(
+    merged = state.merge_frames(
         (
             {"a": a, "b": b1},
             {"a": a, "b": b2},
         )
     )
     assert merged == {"a": a}
-    assert extractor._merge_frames(
+    assert state.merge_frames(
         (
             {"a": a},
             {"a": a},
```
