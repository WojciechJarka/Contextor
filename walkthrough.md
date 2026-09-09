STATUS=FINAL_PASS
CONTEXTOR_PRE_EDIT=Fresh Contextor context revision 510; HEAD matched base and targets were clean.
IMPLEMENTATION=Captured callee classification before argument evaluation; retained required dynamic boundary metadata.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; tests/analysis/test_lineage_extraction.py
TESTS_RUN=focused pytest and git diff check.
TEST_RESULTS=45 passed in 1.21s; diff check passed.
FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index b6e2ac5..5d8578f 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -458,18 +458,21 @@ class _AnchorExtractor:
 
     def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
         self._visit(node.func, owner, walrus_owner)
+        callable_info = self._resolve_current_local_callable(node, owner)
+        callee_ref = self._frame(owner).get(node.func.id) if isinstance(node.func, ast.Name) else None
         call_site, call_result = self._occurrence("call_site", node), self._occurrence("call_result", node)
         arguments = self._collect_call_arguments(node, owner, walrus_owner)
-        callable_info = self._resolve_current_local_callable(node, owner)
         if callable_info is not None:
             self._bind_call_arguments(arguments, callable_info)
             self._flow(source=self._return_symbolic(callable_info), target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
             return
-        if isinstance(node.func, ast.Name) and self._frame(owner).get(node.func.id) is None:
+        if isinstance(node.func, ast.Name) and callee_ref is None:
             resolution_kind, confidence = ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED
+            dynamic_boundary = None
         else:
             resolution_kind, confidence = ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC
-        self._flow(source=call_site, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=resolution_kind, confidence=confidence, dynamic_boundary="dynamic_call" if confidence is LineageConfidence.DYNAMIC else None)
+            dynamic_boundary = "dynamic_call"
+        self._flow(source=call_site, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=resolution_kind, confidence=confidence, dynamic_boundary=dynamic_boundary)
 
     def _visit_comprehension_expression(self, node: ast.AST, generators: list[ast.comprehension], values: tuple[ast.AST, ...], owner: str | None, walrus_owner: str | None) -> None:
         comprehension_id = self._add("comprehension", node, None, owner)
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 659830b..9c21b53 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -182,6 +182,23 @@ def test_stage_1c5_signature_stars_and_dynamic_calls_are_conservative():
     assert _stage_1c_call_result_flows(dynamic)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
 
 
+def test_stage_1c5_callee_identity_is_captured_before_argument_rebind():
+    facts = _stage_1c_facts("def run(value):\n return value\nresult = run((run := other))\nlater = run(1)\n")
+    first = next(flow for flow in _stage_1c_call_result_flows(facts) if flow.evidence.start_line == 3)
+    later = next(flow for flow in _stage_1c_call_result_flows(facts) if flow.evidence.start_line == 4)
+    assert first.resolution_kind is ResolutionKind.CALL_EXACT
+    assert isinstance(first.source, ExtractedSymbolicRef) and first.source.symbol_name == "run"
+    assert later.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+    assert later.confidence is LineageConfidence.DYNAMIC and later.dynamic_boundary == "dynamic_call"
+
+
+def test_stage_1c5_unresolved_callee_stays_unresolved_when_argument_binds_name():
+    facts = _stage_1c_facts("result = missing((missing := other))\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert flow.confidence is LineageConfidence.UNRESOLVED and flow.dynamic_boundary is None
+
+
 def test_stage_1c_if_branches_are_exact_inside_and_ambiguous_after_merge():
     facts = _stage_1c_facts(
         "def run(cond):\n"

