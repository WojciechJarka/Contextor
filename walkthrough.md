STATUS=PASS
IMPLEMENTATION=Focused Stage 1C.2 tests added; production unchanged in this completion pass.
FILES_CHANGED=tests/analysis/test_lineage_extraction.py; walkthrough.md report only.
TESTS_RUN=focused and regression commands requested.
TEST_RESULTS=21 passed in 0.84s; 32 passed in 2.96s; git diff --check PASS.
FULL_DIFFS=

diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index e2442d6..7be9473 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -97,6 +97,69 @@ def test_stage_1c_merge_frames_keeps_only_identical_occurrences():
     assert merged == {"a": a}
 
 
+def _stage_1c_facts(source: str):
+    return extract_lineage_source_facts(ast.parse(source), source_key="pkg.py", source_fingerprint=FINGERPRINT)
+
+
+def _stage_1c_named(facts, kind, name):
+    return [item for item in facts.anchors if item.kind == kind and parse_local_occurrence_id(item.local_id)[3] == name]
+
+
+def test_stage_1c_direct_assignments_chain_through_current_frame():
+    facts = _stage_1c_facts("def run(arg):\n first = arg\n second = first\n return second\n")
+    arg_param = _stage_1c_named(facts, "parameter", "arg")[0]
+    first, second = _stage_1c_named(facts, "binding", "first")[0], _stage_1c_named(facts, "binding", "second")[0]
+    flows = facts.flows
+    assert any(isinstance(f.source, ExtractedOccurrenceRef) and f.source.local_id == arg_param.local_id and f.relation is LineageRelation.BINDS and f.resolution_kind is ResolutionKind.LEXICAL_EXACT and f.confidence is LineageConfidence.CONFIRMED for f in flows)
+    assert any(f.target.local_id == first.local_id and f.relation is LineageRelation.ASSIGNS for f in flows)
+    assert any(f.target.local_id == second.local_id and f.relation is LineageRelation.ASSIGNS for f in flows)
+
+
+def test_stage_1c_rebinding_uses_latest_prior_unconditional_binding():
+    facts = _stage_1c_facts("x=1\nbefore=x\nx=2\nafter=x\n")
+    xs = _stage_1c_named(facts, "binding", "x")
+    loads = [f for f in facts.flows if f.relation is LineageRelation.BINDS and isinstance(f.target, ExtractedOccurrenceRef) and parse_local_occurrence_id(f.target.local_id)[0] == "name_load" and parse_local_occurrence_id(f.target.local_id)[3] == "x"]
+    assert [f.source.local_id for f in loads] == [xs[0].local_id, xs[1].local_id]
+
+
+def test_stage_1c_annotation_only_and_destructuring_do_not_claim_direct_value_flow():
+    facts = _stage_1c_facts("source=1\na: int = source\nb: int\nleft, right = source\n")
+    a = _stage_1c_named(facts, "binding", "a")[0]
+    assert any(f.target.local_id == a.local_id and f.relation is LineageRelation.ASSIGNS for f in facts.flows)
+    assert not any(f.relation is LineageRelation.ASSIGNS and parse_local_occurrence_id(f.target.local_id)[3] in {"left", "right"} for f in facts.flows)
+
+
+def test_stage_1c_walrus_updates_current_frame():
+    facts = _stage_1c_facts("def run(source):\n result = (captured := source)\n return captured\n")
+    captured = _stage_1c_named(facts, "binding", "captured")[0]
+    result = _stage_1c_named(facts, "binding", "result")[0]
+    assert any(f.target.local_id == captured.local_id and f.relation is LineageRelation.ASSIGNS for f in facts.flows)
+    assert any(f.target.local_id == result.local_id and f.relation is LineageRelation.ASSIGNS for f in facts.flows)
+    assert any(isinstance(f.source, ExtractedOccurrenceRef) and f.source.local_id == captured.local_id and f.relation is LineageRelation.BINDS for f in facts.flows)
+
+
+def test_stage_1c_defs_and_import_bindings_are_local_lexical_sources_only():
+    facts = _stage_1c_facts("from pkg import item as imported\ndef helper(): pass\na=imported\nb=helper\n")
+    imports = _stage_1c_named(facts, "import_binding", "imported")[0]
+    helper = _stage_1c_named(facts, "function", "helper")[0]
+    lexical = [f for f in facts.flows if f.relation is LineageRelation.BINDS and f.resolution_kind is ResolutionKind.LEXICAL_EXACT]
+    assert {imports.local_id, helper.local_id} <= {f.source.local_id for f in lexical}
+    assert all(f.resolution_kind is not ResolutionKind.IMPORT_EXACT for f in facts.flows)
+
+
+def test_stage_1c_does_not_resolve_enclosing_global_or_nonlocal_names():
+    facts = _stage_1c_facts("x=1\ndef outer():\n y=2\n def inner():\n  nonlocal y\n  return x+y\n return inner\n")
+    assert not any(f.relation is LineageRelation.BINDS and f.resolution_kind is ResolutionKind.LEXICAL_EXACT and isinstance(f.target, ExtractedOccurrenceRef) and parse_local_occurrence_id(f.target.local_id)[3] in {"x", "y"} for f in facts.flows)
+
+
+def test_stage_1c_augassign_requires_prior_local_and_has_no_single_source_assign_flow():
+    facts = _stage_1c_facts("known=1\nknown += rhs\nreturn_known=known\nmissing += rhs\nafter=missing\n")
+    known = _stage_1c_named(facts, "binding", "known")
+    assert any(f.source.local_id == known[0].local_id and f.relation is LineageRelation.BINDS for f in facts.flows)
+    assert not any(f.target.local_id == known[1].local_id and f.relation is LineageRelation.ASSIGNS for f in facts.flows)
+    assert not any(f.relation is LineageRelation.BINDS and isinstance(f.target, ExtractedOccurrenceRef) and parse_local_occurrence_id(f.target.local_id)[3] == "missing" for f in facts.flows)
+
+
 def test_extraction_is_deterministic_source_local_and_has_parameter_lineage(monkeypatch):
     tree = ast.parse("import pkg.mod as pm\nvalue = 1\ndef run(arg):\n    local = arg\n    return local\n")
     monkeypatch.setattr("builtins.open", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("extractor performed filesystem I/O")))

