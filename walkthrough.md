STATUS=FINAL_PASS
CONTEXTOR_PRE_EDIT=Production target clean; test-only change.
FILES_CHANGED=tests/analysis/test_lineage_extraction.py
TESTS_RUN=focused and combined matrices; git diff --check.
TEST_RESULTS=54 passed in 1.39s; 65 passed in 3.76s; diff check passed.
FULL_DIFFS=
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 9c21b53..b23b7f5 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -199,6 +199,68 @@ def test_stage_1c5_unresolved_callee_stays_unresolved_when_argument_binds_name()
     assert flow.confidence is LineageConfidence.UNRESOLVED and flow.dynamic_boundary is None
 
 
+def test_stage_1c5_async_function_name_call_uses_exact_local_return_identity():
+    facts = _stage_1c_facts("async def produce(value):\n return value\nresult = produce(1)\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT and flow.confidence is LineageConfidence.CONFIRMED
+    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.kind is ExtractedSymbolicKind.RETURN and flow.source.symbol_name == "produce"
+
+
+def test_stage_1c5_lambda_assignment_keeps_binding_as_lexical_authority():
+    facts = _stage_1c_facts("fn = lambda value: value\nresult = fn(1)\n")
+    binding = _stage_1c_named(facts, "binding", "fn")[0]
+    assert _stage_1c_lexical_bind_sources(facts, "fn", 2) == [binding.local_id]
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.CALL_EXACT and isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name.startswith("lambda@")
+    assert _stage_1c_argument_parameter_names(facts) == ["value"]
+
+
+def test_stage_1c5_rebound_function_name_is_dynamic_not_exact():
+    facts = _stage_1c_facts("def run():\n return 1\nrun = other\nresult = run()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC and flow.dynamic_boundary == "dynamic_call"
+
+
+def test_stage_1c5_branch_invalidated_callable_is_unresolved_not_exact():
+    facts = _stage_1c_facts("def run():\n return 1\nif cond:\n run = other\nresult = run()\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.UNRESOLVED_NAME and flow.confidence is LineageConfidence.UNRESOLVED and flow.dynamic_boundary is None
+
+
+def test_stage_1c5_explicit_keywords_bind_poskw_and_kwonly_exactly():
+    facts = _stage_1c_facts("def run(value, *, flag):\n return value\nresult = run(value=1, flag=2)\n")
+    flows = [f for f in facts.flows if f.relation is LineageRelation.ARGUMENT_TO_PARAMETER]
+    assert _stage_1c_argument_parameter_names(facts) == ["value", "flag"] and len(flows) == 2
+    assert all(f.resolution_kind is ResolutionKind.CALL_EXACT and f.confidence is LineageConfidence.CONFIRMED for f in flows)
+
+
+def test_stage_1c5_duplicate_fixed_parameter_does_not_get_second_exact_edge():
+    facts = _stage_1c_facts("def run(value):\n return value\nresult = run(1, value=2)\n")
+    flows = [f for f in facts.flows if f.relation is LineageRelation.ARGUMENT_TO_PARAMETER]
+    assert len(flows) == 1 and _stage_1c_argument_parameter_names(facts) == ["value"]
+
+
+def test_stage_1c5_bare_return_has_no_edge_and_multiple_returns_share_identity():
+    bare = _stage_1c_facts("def stop():\n return\n")
+    assert not any(f.relation is LineageRelation.RETURNS for f in bare.flows)
+    multiple = _stage_1c_facts("def choose(flag):\n if flag:\n  return 1\n return 2\n")
+    returns = [f.target for f in multiple.flows if f.relation is LineageRelation.RETURNS and isinstance(f.target, ExtractedSymbolicRef)]
+    assert len(returns) == 2 and returns[0] == returns[1] and returns[0].kind is ExtractedSymbolicKind.RETURN
+
+
+def test_stage_1c5_imported_callable_does_not_become_local_call_exact():
+    facts = _stage_1c_facts("from pkg import run\nresult = run(1)\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert not any(f.resolution_kind is ResolutionKind.IMPORT_EXACT for f in facts.flows)
+    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC and flow.dynamic_boundary == "dynamic_call"
+
+
+def test_stage_1c5_dynamic_attribute_call_carries_required_boundary_metadata():
+    facts = _stage_1c_facts("result = obj.method(1)\n")
+    flow = _stage_1c_call_result_flows(facts)[0]
+    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC and flow.dynamic_boundary == "dynamic_call"
+
+
 def test_stage_1c_if_branches_are_exact_inside_and_ambiguous_after_merge():
     facts = _stage_1c_facts(
         "def run(cond):\n"

