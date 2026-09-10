STATUS=FINAL_PASS

CONTEXTOR_EVIDENCE=
- ACTIVE and DEFERRED MCP inventories were checked. Required read capabilities were active; no deferred Contextor capability was advertised.
- Fresh Contextor edit context for tests/analysis/test_lineage_extraction.py: module 352/1, live revision 524, workspace_sync=verified, syntax=checked_and_none.
- Production file was frozen. Its current worktree modification predates this test-only turn and was not edited.

PRODUCTION_CHANGED=NO

TEST_MATRIX=
- Split prior combined outer-iterable/target test into independent enclosing-lookup, local-shadowing, and post-exit restoration cases.
- Split prior combined runtime-target test into independent element, filter, later-iterable, and later-target filter/value cases.
- Added explicit prior-binding versus NamedExpr zero/body conservative-merge regression.
- Preserved all existing Stage 1C.7 regressions and parameterized per-form/local-import cases.

FILES_CHANGED=
- tests/analysis/test_lineage_extraction.py
- walkthrough.md (this report only)

TESTS_RUN=
- .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q
- .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q
- git diff --check -- contextor/core/analysis/lineage_extraction.py tests/analysis/test_lineage_extraction.py

TEST_RESULTS=
- PASS: 97 passed in 2.65s.
- PASS: 108 passed in 3.82s.
- PASS: diff check; only LF-to-CRLF workspace warnings.

FULL_DIFFS=
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 91ca1cf..3e1e708 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -1257,3 +1257,323 @@ def test_incremental_preparation_carries_transient_lineage_and_errors_do_not(tmp
     assert broken.has_error and broken.error_status == "SYNTAX_ERROR" and broken.extracted_lineage_facts is None
     missing = prepare_source_update(file_path=tmp_path / "missing.py", module_path="missing", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="missing.py")
     assert missing.has_error and missing.error_status == "ERROR" and missing.extracted_lineage_facts is None
+
+
+def _stage_1c_exact_bind_flows(facts, name):
+    return [
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and isinstance(flow.target, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.target.local_id)[3] == name
+    ]
+
+
+def test_stage_1c7_outermost_iterable_uses_enclosing_binding():
+    facts = _stage_1c_facts(
+        "def run(items):\n"
+        " outer = items\n"
+        " result = [item for item in outer]\n"
+    )
+    outer = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "outer")
+        if anchor.span.start_line == 2
+    )
+    assert _stage_1c_lexical_bind_sources(facts, "outer", 3) == [
+        outer.local_id
+    ]
+
+
+def test_stage_1c7_target_is_comprehension_local_and_shadows_outer_inside():
+    facts = _stage_1c_facts(
+        "def run(items):\n"
+        " x = items\n"
+        " result = [x for x in items]\n"
+    )
+    outer = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "x")
+        if anchor.span.start_line == 2
+    )
+    target = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "x")
+        if anchor.span.start_line == 3
+    )
+    comprehension = next(
+        anchor for anchor in facts.anchors if anchor.kind == "comprehension"
+    )
+    assert target.owner_local_id == comprehension.local_id
+    assert target.owner_local_id != outer.owner_local_id
+    assert _stage_1c_lexical_bind_sources(facts, "x", 3) == [
+        target.local_id
+    ]
+
+
+def test_stage_1c7_target_does_not_leak_and_outer_binding_remains_exact():
+    facts = _stage_1c_facts(
+        "def run(items):\n"
+        " x = items\n"
+        " result = [x for x in items]\n"
+        " after = x\n"
+    )
+    outer = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "x")
+        if anchor.span.start_line == 2
+    )
+    target = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "x")
+        if anchor.span.start_line == 3
+    )
+    assert _stage_1c_lexical_bind_sources(facts, "x", 4) == [
+        outer.local_id
+    ]
+    assert target.local_id not in _stage_1c_lexical_bind_sources(facts, "x", 4)
+
+
+def test_stage_1c7_element_sees_first_runtime_target():
+    facts = _stage_1c_facts("result = [x for x in xs]\n")
+    runtime = _stage_1c_runtime_assignment(facts, "x")
+    binds = _stage_1c_exact_bind_flows(facts, "x")
+    assert len(binds) == 1
+    assert binds[0].source.local_id == runtime.target.local_id
+    assert binds[0].resolution_kind is ResolutionKind.LEXICAL_EXACT
+    assert binds[0].confidence is LineageConfidence.CONFIRMED
+
+
+def test_stage_1c7_filter_sees_first_runtime_target():
+    facts = _stage_1c_facts("result = [x for x in xs if x]\n")
+    runtime = _stage_1c_runtime_assignment(facts, "x")
+    binds = _stage_1c_exact_bind_flows(facts, "x")
+    assert len(binds) == 2
+    assert all(flow.source.local_id == runtime.target.local_id for flow in binds)
+    assert all(flow.relation is LineageRelation.BINDS for flow in binds)
+
+
+def test_stage_1c7_later_generator_iterable_sees_prior_runtime_target():
+    facts = _stage_1c_facts("result = [(x, y) for x in xs for y in x]\n")
+    runtime = _stage_1c_runtime_assignment(facts, "x")
+    binds = _stage_1c_exact_bind_flows(facts, "x")
+    assert len(binds) == 2
+    assert all(flow.source.local_id == runtime.target.local_id for flow in binds)
+    assert all(flow.confidence is LineageConfidence.CONFIRMED for flow in binds)
+
+
+def test_stage_1c7_later_target_sees_its_filter_and_final_value():
+    facts = _stage_1c_facts(
+        "result = [(x, y) for x in xs for y in ys if y]\n"
+    )
+    runtime = _stage_1c_runtime_assignment(facts, "y")
+    binds = _stage_1c_exact_bind_flows(facts, "y")
+    assert len(binds) == 2
+    assert all(flow.source.local_id == runtime.target.local_id for flow in binds)
+    assert all(flow.resolution_kind is ResolutionKind.LEXICAL_EXACT for flow in binds)
+
+
+def test_stage_1c7_nested_comprehensions_keep_targets_independent():
+    facts = _stage_1c_facts(
+        "def run(xs):\n"
+        " return [[y for y in x] for x in xs]\n"
+    )
+    comprehensions = [
+        anchor for anchor in facts.anchors if anchor.kind == "comprehension"
+    ]
+    x = _stage_1c_named(facts, "binding", "x")[0]
+    y = _stage_1c_named(facts, "binding", "y")[0]
+    assert len(comprehensions) == 2
+    assert x.owner_local_id != y.owner_local_id
+    assert any(
+        flow.source.local_id == x.local_id
+        for flow in _stage_1c_exact_bind_flows(facts, "x")
+    )
+
+
+def test_stage_1c7_walrus_is_visible_on_body_path_but_not_afterwards():
+    facts = _stage_1c_facts(
+        "def run(xs):\n"
+        " result = [(y := x, y) for x in xs]\n"
+        " after = y\n"
+    )
+    y = _stage_1c_named(facts, "binding", "y")[0]
+    y_binds = _stage_1c_exact_bind_flows(facts, "y")
+    assert any(
+        flow.source.local_id == y.local_id and flow.evidence.start_line == 2
+        for flow in y_binds
+    )
+    assert not any(flow.evidence.start_line == 3 for flow in y_binds)
+
+
+def test_stage_1c7_zero_body_walrus_rebind_invalidates_prior_authority():
+    facts = _stage_1c_facts(
+        "def run(xs, old):\n"
+        " y = old\n"
+        " result = [(y := x) for x in xs]\n"
+        " after = y\n"
+    )
+    prior = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "y")
+        if anchor.span.start_line == 2
+    )
+    walrus = next(
+        anchor
+        for anchor in _stage_1c_named(facts, "binding", "y")
+        if anchor.span.start_line == 3
+    )
+    post_sources = _stage_1c_lexical_bind_sources(facts, "y", 4)
+    assert prior.local_id != walrus.local_id
+    assert post_sources == []
+    assert prior.local_id not in post_sources
+    assert walrus.local_id not in post_sources
+
+
+def test_stage_1c7_filter_walrus_visibility_and_zero_iteration_merge():
+    facts = _stage_1c_facts(
+        "def run(xs):\n"
+        " result = [y for x in xs if (y := x)]\n"
+        " after = y\n"
+    )
+    y = _stage_1c_named(facts, "binding", "y")[0]
+    y_binds = _stage_1c_exact_bind_flows(facts, "y")
+    assert any(
+        flow.source.local_id == y.local_id and flow.evidence.start_line == 2
+        for flow in y_binds
+    )
+    assert not any(flow.evidence.start_line == 3 for flow in y_binds)
+
+
+def test_stage_1c7_nested_walrus_uses_containing_owner_and_merges_conservatively():
+    facts = _stage_1c_facts(
+        "def run(xs, ys):\n"
+        " result = [[((z := y), z) for y in ys] for x in xs]\n"
+        " after = z\n"
+    )
+    function = _stage_1c_named(facts, "function", "run")[0]
+    z = _stage_1c_named(facts, "binding", "z")[0]
+    z_binds = _stage_1c_exact_bind_flows(facts, "z")
+    assert z.owner_local_id == function.local_id
+    assert any(
+        flow.source.local_id == z.local_id and flow.evidence.start_line == 2
+        for flow in z_binds
+    )
+    assert not any(flow.evidence.start_line == 3 for flow in z_binds)
+
+
+@pytest.mark.parametrize(
+    "source",
+    (
+        "def run(xs):\n result = [x for x in xs]\n",
+        "def run(xs):\n result = {x for x in xs}\n",
+        "def run(xs):\n result = (x for x in xs)\n",
+        "def run(xs):\n result = {x: x for x in xs}\n",
+    ),
+)
+def test_stage_1c7_all_comprehension_forms_have_one_local_target(source):
+    facts = _stage_1c_facts(source)
+    comprehensions = [
+        anchor for anchor in facts.anchors if anchor.kind == "comprehension"
+    ]
+    target = _stage_1c_named(facts, "binding", "x")[0]
+    runtime = _stage_1c_runtime_assignment(facts, "x")
+    assert len(comprehensions) == 1
+    assert target.owner_local_id == comprehensions[0].local_id
+    assert runtime.target.local_id == target.local_id
+
+
+def test_stage_1c7_dict_key_walrus_precedes_value_and_does_not_leak():
+    facts = _stage_1c_facts(
+        "def run(xs):\n"
+        " result = {(y := x): y for x in xs}\n"
+        " after = y\n"
+    )
+    y = _stage_1c_named(facts, "binding", "y")[0]
+    y_binds = _stage_1c_exact_bind_flows(facts, "y")
+    body_bind = next(
+        flow
+        for flow in y_binds
+        if flow.source.local_id == y.local_id
+        and flow.evidence.start_line == 2
+    )
+    assert parse_local_occurrence_id(body_bind.target.local_id)[1] > parse_local_occurrence_id(
+        y.local_id
+    )[1]
+    assert not any(flow.evidence.start_line == 3 for flow in y_binds)
+
+
+@pytest.mark.parametrize(
+    "source",
+    (
+        "def run(xs):\n def target(): return 1\n [(target := other) for x in xs]\n return target()\n",
+        "def run(xs):\n from pkg import target\n [(target := other) for x in xs]\n return target()\n",
+    ),
+)
+def test_stage_1c7_walrus_callable_and_import_rebind_are_unresolved_after_merge(
+    source,
+):
+    facts = _stage_1c_facts(source)
+    later = next(
+        flow
+        for flow in _stage_1c_call_result_flows(facts)
+        if flow.evidence.start_line == 4
+    )
+    assert later.resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert later.confidence is LineageConfidence.UNRESOLVED
+    assert later.dynamic_boundary is None
+
+
+@pytest.mark.parametrize(
+    ("source", "resolution"),
+    (
+        (
+            "def run():\n"
+            " def produce(): return 1\n"
+            " result = [x for x in produce()]\n",
+            ResolutionKind.CALL_EXACT,
+        ),
+        (
+            "def run():\n"
+            " from pkg import produce\n"
+            " result = [x for x in produce()]\n",
+            ResolutionKind.IMPORT_EXACT,
+        ),
+    ),
+)
+def test_stage_1c7_outermost_iterable_call_uses_enclosing_authority(
+    source,
+    resolution,
+):
+    facts = _stage_1c_facts(source)
+    call = next(
+        flow
+        for flow in _stage_1c_call_result_flows(facts)
+        if flow.evidence.start_line == 3
+    )
+    assert call.resolution_kind is resolution
+    assert call.confidence is LineageConfidence.CONFIRMED
+
+
+def test_stage_1c7_iterable_walrus_is_rejected_before_extraction():
+    with pytest.raises(SyntaxError):
+        compile("[x for x in (y := xs)]", "pkg.py", "exec")
+
+
+def test_stage_1c7_runtime_target_has_one_assignment_and_unique_ids():
+    facts = _stage_1c_facts("result = [x for x in xs if x]\n")
+    assignments = [
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.ASSIGNS
+        and isinstance(flow.source, ExtractedOccurrenceRef)
+        and parse_local_occurrence_id(flow.source.local_id)[0]
+        == "runtime_bound_local"
+        and parse_local_occurrence_id(flow.source.local_id)[3] == "x"
+    ]
+    assert len(assignments) == 1
+    assert len({anchor.local_id for anchor in facts.anchors}) == len(facts.anchors)
+    assert len({flow.local_id for flow in facts.flows}) == len(facts.flows)\n
