STATUS=PASS
FILES_CHANGED=tests/analysis/test_lineage_extraction.py; walkthrough.md report only.
TESTS_RUN=focused: 22 passed; regression: 33 passed.
FULL_DIFFS=

diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 7be9473..f415dbc 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -106,14 +106,69 @@ def _stage_1c_named(facts, kind, name):
 
 
 def test_stage_1c_direct_assignments_chain_through_current_frame():
-    facts = _stage_1c_facts("def run(arg):\n first = arg\n second = first\n return second\n")
+    facts = _stage_1c_facts(
+        "def run(arg):\n"
+        " first = arg\n"
+        " second = first\n"
+        " return second\n"
+    )
     arg_param = _stage_1c_named(facts, "parameter", "arg")[0]
-    first, second = _stage_1c_named(facts, "binding", "first")[0], _stage_1c_named(facts, "binding", "second")[0]
-    flows = facts.flows
-    assert any(isinstance(f.source, ExtractedOccurrenceRef) and f.source.local_id == arg_param.local_id and f.relation is LineageRelation.BINDS and f.resolution_kind is ResolutionKind.LEXICAL_EXACT and f.confidence is LineageConfidence.CONFIRMED for f in flows)
-    assert any(f.target.local_id == first.local_id and f.relation is LineageRelation.ASSIGNS for f in flows)
-    assert any(f.target.local_id == second.local_id and f.relation is LineageRelation.ASSIGNS for f in flows)
-
+    first = _stage_1c_named(facts, "binding", "first")[0]
+    second = _stage_1c_named(facts, "binding", "second")[0]
+    lexical_binds = [
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+    ]
+    assigns = [
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.ASSIGNS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+    ]
+    arg_bind = next(
+        flow
+        for flow in lexical_binds
+        if flow.source.local_id == arg_param.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "arg"
+    )
+    first_assign = next(
+        flow
+        for flow in assigns
+        if flow.source.local_id == arg_bind.target.local_id
+        and flow.target.local_id == first.local_id
+    )
+    first_bind = next(
+        flow
+        for flow in lexical_binds
+        if flow.source.local_id == first.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "first"
+    )
+    second_assign = next(
+        flow
+        for flow in assigns
+        if flow.source.local_id == first_bind.target.local_id
+        and flow.target.local_id == second.local_id
+    )
+    second_bind = next(
+        flow
+        for flow in lexical_binds
+        if flow.source.local_id == second.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "second"
+    )
+    assert first_assign.target.local_id == first.local_id
+    assert second_assign.target.local_id == second.local_id
+    assert second_bind.source.local_id == second.local_id
 
 def test_stage_1c_rebinding_uses_latest_prior_unconditional_binding():
     facts = _stage_1c_facts("x=1\nbefore=x\nx=2\nafter=x\n")
@@ -123,11 +178,45 @@ def test_stage_1c_rebinding_uses_latest_prior_unconditional_binding():
 
 
 def test_stage_1c_annotation_only_and_destructuring_do_not_claim_direct_value_flow():
-    facts = _stage_1c_facts("source=1\na: int = source\nb: int\nleft, right = source\n")
+    facts = _stage_1c_facts(
+        "source=1\n"
+        "a: int = source\n"
+        "b: int\n"
+        "probe = b\n"
+        "left, right = source\n"
+    )
     a = _stage_1c_named(facts, "binding", "a")[0]
-    assert any(f.target.local_id == a.local_id and f.relation is LineageRelation.ASSIGNS for f in facts.flows)
-    assert not any(f.relation is LineageRelation.ASSIGNS and parse_local_occurrence_id(f.target.local_id)[3] in {"left", "right"} for f in facts.flows)
-
+    b = _stage_1c_named(facts, "binding", "b")[0]
+    left = _stage_1c_named(facts, "binding", "left")[0]
+    right = _stage_1c_named(facts, "binding", "right")[0]
+    assert any(
+        flow.relation is LineageRelation.ASSIGNS
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.target.local_id == a.local_id
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        for flow in facts.flows
+    )
+    assert not any(
+        flow.relation is LineageRelation.ASSIGNS
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.target.local_id == b.local_id
+        for flow in facts.flows
+    )
+    assert not any(
+        flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "b"
+        for flow in facts.flows
+    )
+    assert not any(
+        flow.relation is LineageRelation.ASSIGNS
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.target.local_id in {left.local_id, right.local_id}
+        for flow in facts.flows
+    )
 
 def test_stage_1c_walrus_updates_current_frame():
     facts = _stage_1c_facts("def run(source):\n result = (captured := source)\n return captured\n")
@@ -139,13 +228,42 @@ def test_stage_1c_walrus_updates_current_frame():
 
 
 def test_stage_1c_defs_and_import_bindings_are_local_lexical_sources_only():
-    facts = _stage_1c_facts("from pkg import item as imported\ndef helper(): pass\na=imported\nb=helper\n")
-    imports = _stage_1c_named(facts, "import_binding", "imported")[0]
+    facts = _stage_1c_facts(
+        "from pkg import item as imported\n"
+        "def helper(): pass\n"
+        "a=imported\n"
+        "b=helper\n"
+    )
+    imported = _stage_1c_named(facts, "import_binding", "imported")[0]
     helper = _stage_1c_named(facts, "function", "helper")[0]
-    lexical = [f for f in facts.flows if f.relation is LineageRelation.BINDS and f.resolution_kind is ResolutionKind.LEXICAL_EXACT]
-    assert {imports.local_id, helper.local_id} <= {f.source.local_id for f in lexical}
-    assert all(f.resolution_kind is not ResolutionKind.IMPORT_EXACT for f in facts.flows)
-
+    imported_flow = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == imported.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "imported"
+    )
+    helper_flow = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == helper.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "helper"
+    )
+    assert imported_flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+    assert imported_flow.confidence is LineageConfidence.CONFIRMED
+    assert helper_flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+    assert helper_flow.confidence is LineageConfidence.CONFIRMED
+    assert not any(
+        flow.resolution_kind is ResolutionKind.IMPORT_EXACT
+        for flow in facts.flows
+    )
 
 def test_stage_1c_does_not_resolve_enclosing_global_or_nonlocal_names():
     facts = _stage_1c_facts("x=1\ndef outer():\n y=2\n def inner():\n  nonlocal y\n  return x+y\n return inner\n")
@@ -153,11 +271,71 @@ def test_stage_1c_does_not_resolve_enclosing_global_or_nonlocal_names():
 
 
 def test_stage_1c_augassign_requires_prior_local_and_has_no_single_source_assign_flow():
-    facts = _stage_1c_facts("known=1\nknown += rhs\nreturn_known=known\nmissing += rhs\nafter=missing\n")
-    known = _stage_1c_named(facts, "binding", "known")
-    assert any(f.source.local_id == known[0].local_id and f.relation is LineageRelation.BINDS for f in facts.flows)
-    assert not any(f.target.local_id == known[1].local_id and f.relation is LineageRelation.ASSIGNS for f in facts.flows)
-    assert not any(f.relation is LineageRelation.BINDS and isinstance(f.target, ExtractedOccurrenceRef) and parse_local_occurrence_id(f.target.local_id)[3] == "missing" for f in facts.flows)
+    facts = _stage_1c_facts(
+        "known=1\n"
+        "known += rhs\n"
+        "return_known=known\n"
+        "missing += rhs\n"
+        "after=missing\n"
+    )
+    known_bindings = _stage_1c_named(facts, "binding", "known")
+    initial_known = next(anchor for anchor in known_bindings if anchor.span.start_line == 1)
+    aug_known = next(anchor for anchor in known_bindings if anchor.span.start_line == 2)
+    aug_read = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == initial_known.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "known"
+        and flow.evidence.start_line == 2
+    )
+    later_known = next(
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.source.local_id == aug_known.local_id
+        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "known"
+        and flow.evidence.start_line == 3
+    )
+    assert aug_read.source.local_id == initial_known.local_id
+    assert later_known.source.local_id == aug_known.local_id
+    assert not any(
+        flow.relation is LineageRelation.ASSIGNS
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and flow.target.local_id == aug_known.local_id
+        for flow in facts.flows
+    )
+    assert not any(
+        flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.target.local_id)[3] == "missing"
+        for flow in facts.flows
+    )
+
+def test_stage_1c_augassign_snapshots_prior_before_rhs_rebinding():
+    facts = _stage_1c_facts("x = 1\nx += (x := 2)\nafter = x\n")
+    bindings = _stage_1c_named(facts, "binding", "x")
+    initial = next(anchor for anchor in bindings if anchor.span.start_line == 1)
+    aug_binding = next(anchor for anchor in bindings if anchor.span.start_line == 2 and anchor.span.start_column == 0)
+    walrus_binding = next(anchor for anchor in bindings if anchor.span.start_line == 2 and anchor.span.start_column > 0)
+    lexical = [flow for flow in facts.flows if flow.relation is LineageRelation.BINDS and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT and isinstance(flow.source, ExtractedOccurrenceRef) and isinstance(flow.target, ExtractedOccurrenceRef)]
+    aug_read = next(flow for flow in lexical if parse_local_occurrence_id(flow.target.local_id)[3] == "x" and flow.evidence.start_line == 2 and flow.evidence.start_column == 0)
+    after_read = next(flow for flow in lexical if parse_local_occurrence_id(flow.target.local_id)[3] == "x" and flow.evidence.start_line == 3)
+    assert aug_read.source.local_id == initial.local_id
+    assert aug_read.source.local_id != walrus_binding.local_id
+    assert after_read.source.local_id == aug_binding.local_id
+    assert not any(flow.relation is LineageRelation.ASSIGNS and isinstance(flow.target, ExtractedOccurrenceRef) and flow.target.local_id == aug_binding.local_id for flow in facts.flows)
 
 
 def test_extraction_is_deterministic_source_local_and_has_parameter_lineage(monkeypatch):

