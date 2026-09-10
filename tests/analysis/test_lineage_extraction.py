import ast
import codecs
import hashlib
import sys

import pytest

from contextor.core.analysis import lineage_extraction as lineage_extraction_module
from contextor.core.analysis.incremental.preparation import prepare_source_update
from contextor.core.analysis.lineage_extraction import (
    LineageExtractionLimits,
    build_local_occurrence_id,
    extract_lineage_source_facts,
    parse_local_occurrence_id,
)
from contextor.core.analysis.lineage_extraction_emit import occurrence
from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
from contextor.core.domain.lineage_facts import (
    ExtractedOccurrenceRef,
    ExtractedSymbolicRef,
    ExtractedSymbolicKind,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    ResolutionKind,
)
from contextor.core.source import parse_source_with_fingerprint
from contextor.core.symbol_engine import indexer as indexer_module

FINGERPRINT = "a" * 64


def _decoded_anchors(facts):
    return [(anchor, parse_local_occurrence_id(anchor.local_id)) for anchor in facts.anchors]


def test_local_occurrence_id_round_trip_and_multi_name_disambiguation():
    first = build_local_occurrence_id("global_declaration", "0.1", "x:y%z", ordinal=0)
    second = build_local_occurrence_id("global_declaration", "0.1", "other", ordinal=1)
    assert first != second
    assert parse_local_occurrence_id(first) == ("global_declaration", "0.1", 0, "x:y%z")
    assert parse_local_occurrence_id(second) == ("global_declaration", "0.1", 1, "other")


def test_stage_1c_occurrence_kinds_round_trip():
    for kind in (
        "name_load",
        "call_site",
        "call_argument",
        "call_result",
        "runtime_bound_local",
    ):
        local_id = build_local_occurrence_id(
            kind,
            "0.1",
            "value",
            ordinal=2,
        )
        assert parse_local_occurrence_id(local_id) == (
            kind,
            "0.1",
            2,
            "value",
        )


def test_stage_1c_occurrence_cache_reuses_same_ref():
    tree = ast.parse("value = 1\n")
    paths, reason = lineage_extraction_module._index_ast_paths(
        tree,
        lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS,
    )
    assert reason is None
    state = LineageExtractionState()
    node = tree.body[0].value
    first = occurrence(state, paths, "expression_result", node)
    second = occurrence(state, paths, "expression_result", node)
    assert first is second
    assert first.local_id == second.local_id
    assert len(state._ids) == 1


def test_stage_1c_merge_frames_keeps_only_identical_occurrences():
    state = LineageExtractionState()
    a = ExtractedOccurrenceRef("a")
    b1 = ExtractedOccurrenceRef("b1")
    b2 = ExtractedOccurrenceRef("b2")
    merged = state.merge_frames(
        (
            {"a": a, "b": b1},
            {"a": a, "b": b2},
        )
    )
    assert merged == {"a": a}
    assert state.merge_frames(
        (
            {"a": a},
            {"a": a},
            {"a": a},
        )
    ) == {"a": a}


def _stage_1c_facts(source: str):
    return extract_lineage_source_facts(ast.parse(source), source_key="pkg.py", source_fingerprint=FINGERPRINT)


def _stage_1c_facts_at(source: str, source_key: str):
    return extract_lineage_source_facts(ast.parse(source), source_key=source_key, source_fingerprint=FINGERPRINT)


def _stage_1c_named(facts, kind, name):
    return [item for item in facts.anchors if item.kind == kind and parse_local_occurrence_id(item.local_id)[3] == name]


def _stage_1c_runtime_assignment(facts, name):
    return next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.ASSIGNS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.source.local_id)[0] == "runtime_bound_local"
        and parse_local_occurrence_id(flow.source.local_id)[3] == name
        and parse_local_occurrence_id(flow.target.local_id)[3] == name
    )


def _stage_1c_lexical_bind_sources(facts, name, line):
    return [
        flow.source.local_id
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == name
        and flow.evidence.start_line == line
    ]


def _stage_1c_call_result_flows(facts):
    return [flow for flow in facts.flows if flow.relation is LineageRelation.CALL_RESULT]


def _stage_1c_argument_parameter_names(facts):
    return [parse_local_occurrence_id(flow.target.source_local_id)[3] for flow in facts.flows if flow.relation is LineageRelation.ARGUMENT_TO_PARAMETER and isinstance(flow.target, ExtractedSymbolicRef)]


def test_stage_1c5_local_function_call_links_return_and_argument_exactly():
    facts = _stage_1c_facts("def produce(value):\n return value\nresult = produce(1)\n")
    function = _stage_1c_named(facts, "function", "produce")[0]
    returns = [flow for flow in facts.flows if flow.relation is LineageRelation.RETURNS]
    assert len(returns) == 1 and isinstance(returns[0].target, ExtractedSymbolicRef)
    assert returns[0].target.kind is ExtractedSymbolicKind.RETURN and returns[0].target.source_local_id == function.local_id
    call = next(flow for flow in _stage_1c_call_result_flows(facts) if flow.resolution_kind is ResolutionKind.CALL_EXACT)
    assert isinstance(call.source, ExtractedSymbolicRef) and call.source == returns[0].target
    assert _stage_1c_argument_parameter_names(facts) == ["value"]


def test_stage_1c5_lambda_rebind_and_branch_resolution_are_fail_closed():
    lambda_facts = _stage_1c_facts("fn = lambda value: value\nresult = fn(1)\n")
    assert next(flow for flow in _stage_1c_call_result_flows(lambda_facts) if flow.resolution_kind is ResolutionKind.CALL_EXACT)
    rebound = _stage_1c_facts("def run():\n return 1\nrun = other\nvalue = run()\n")
    assert _stage_1c_call_result_flows(rebound)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
    branch = _stage_1c_facts("def run():\n return 1\nif cond:\n run = other\nvalue = run()\n")
    assert _stage_1c_call_result_flows(branch)[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME


def test_stage_1c5_signature_stars_and_dynamic_calls_are_conservative():
    facts = _stage_1c_facts("def run(a, /, b, *rest, flag, **extra):\n return b\nresult = run(1, 2, 3, 4, flag=5, other=6)\n")
    assert _stage_1c_argument_parameter_names(facts) == ["a", "b", "rest", "rest", "flag", "extra"]
    stars = _stage_1c_facts("def run(a, *rest, **extra):\n return a\nresult = run(*items, **mapping)\n")
    assert _stage_1c_argument_parameter_names(stars) == []
    unresolved = _stage_1c_facts("result = missing(1)\n")
    dynamic = _stage_1c_facts("result = obj.method(1)\n")
    assert _stage_1c_call_result_flows(unresolved)[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
    assert _stage_1c_call_result_flows(dynamic)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY


def test_stage_1c5_callee_identity_is_captured_before_argument_rebind():
    facts = _stage_1c_facts("def run(value):\n return value\nresult = run((run := other))\nlater = run(1)\n")
    first = next(flow for flow in _stage_1c_call_result_flows(facts) if flow.evidence.start_line == 3)
    later = next(flow for flow in _stage_1c_call_result_flows(facts) if flow.evidence.start_line == 4)
    assert first.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(first.source, ExtractedSymbolicRef) and first.source.symbol_name == "run"
    assert later.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
    assert later.confidence is LineageConfidence.DYNAMIC and later.dynamic_boundary == "dynamic_call"


def test_stage_1c5_unresolved_callee_stays_unresolved_when_argument_binds_name():
    facts = _stage_1c_facts("result = missing((missing := other))\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.UNRESOLVED_NAME
    assert flow.confidence is LineageConfidence.UNRESOLVED and flow.dynamic_boundary is None


def test_stage_1c5_async_function_name_call_uses_exact_local_return_identity():
    facts = _stage_1c_facts("async def produce(value):\n return value\nresult = produce(1)\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT and flow.confidence is LineageConfidence.CONFIRMED
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.kind is ExtractedSymbolicKind.RETURN and flow.source.symbol_name == "produce"


def test_stage_1c5_lambda_assignment_keeps_binding_as_lexical_authority():
    facts = _stage_1c_facts("fn = lambda value: value\nresult = fn(1)\n")
    binding = _stage_1c_named(facts, "binding", "fn")[0]
    assert _stage_1c_lexical_bind_sources(facts, "fn", 2) == [binding.local_id]
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT and isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name.startswith("lambda@")
    assert _stage_1c_argument_parameter_names(facts) == ["value"]


def test_stage_1c5_rebound_function_name_is_dynamic_not_exact():
    facts = _stage_1c_facts("def run():\n return 1\nrun = other\nresult = run()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC and flow.dynamic_boundary == "dynamic_call"


def test_stage_1c5_branch_invalidated_callable_is_unresolved_not_exact():
    facts = _stage_1c_facts("def run():\n return 1\nif cond:\n run = other\nresult = run()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.UNRESOLVED_NAME and flow.confidence is LineageConfidence.UNRESOLVED and flow.dynamic_boundary is None


def test_stage_1c5_explicit_keywords_bind_poskw_and_kwonly_exactly():
    facts = _stage_1c_facts("def run(value, *, flag):\n return value\nresult = run(value=1, flag=2)\n")
    flows = [f for f in facts.flows if f.relation is LineageRelation.ARGUMENT_TO_PARAMETER]
    assert _stage_1c_argument_parameter_names(facts) == ["value", "flag"] and len(flows) == 2
    assert all(f.resolution_kind is ResolutionKind.CALL_EXACT and f.confidence is LineageConfidence.CONFIRMED for f in flows)


def test_stage_1c5_duplicate_fixed_parameter_does_not_get_second_exact_edge():
    facts = _stage_1c_facts("def run(value):\n return value\nresult = run(1, value=2)\n")
    flows = [f for f in facts.flows if f.relation is LineageRelation.ARGUMENT_TO_PARAMETER]
    assert len(flows) == 1 and _stage_1c_argument_parameter_names(facts) == ["value"]


def test_stage_1c5_bare_return_has_no_edge_and_multiple_returns_share_identity():
    bare = _stage_1c_facts("def stop():\n return\n")
    assert not any(f.relation is LineageRelation.RETURNS for f in bare.flows)
    multiple = _stage_1c_facts("def choose(flag):\n if flag:\n  return 1\n return 2\n")
    returns = [f.target for f in multiple.flows if f.relation is LineageRelation.RETURNS and isinstance(f.target, ExtractedSymbolicRef)]
    assert len(returns) == 2 and returns[0] == returns[1] and returns[0].kind is ExtractedSymbolicKind.RETURN


def test_stage_1c6_direct_from_import_call_is_import_exact():
    facts = _stage_1c_facts("from pkg.mod import f\nresult = f()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.kind is ExtractedSymbolicKind.RETURN
    assert flow.source.module_name == "pkg.mod" and flow.source.symbol_name == "f"


def test_stage_1c6_from_import_alias_keeps_original_semantic_symbol():
    facts = _stage_1c_facts("from pkg.mod import f as local\nresult = local()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.kind is ExtractedSymbolicKind.RETURN
    assert flow.source.module_name == "pkg.mod" and flow.source.symbol_name == "f"


def test_stage_1c6_direct_imported_symbol_rebind_is_not_import_exact():
    facts = _stage_1c_facts("from pkg.mod import f\nf = other\nresult = f()\n")
    flows = _stage_1c_call_result_flows(facts)
    assert flows[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)


def test_stage_1c6_branch_invalidated_imported_symbol_is_not_import_exact():
    facts = _stage_1c_facts("from pkg.mod import f\nif cond:\n f = other\nresult = f()\n")
    flows = _stage_1c_call_result_flows(facts)
    assert flows[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)


def test_stage_1c6_package_alias_attribute_call_is_import_exact():
    facts = _stage_1c_facts("import pkg as p\nresult = p.f()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.kind is ExtractedSymbolicKind.RETURN
    assert flow.source.module_name == "pkg" and flow.source.symbol_name == "f"


def test_stage_1c6_unaliased_dotted_import_root_attribute_is_import_exact():
    facts = _stage_1c_facts("import pkg.mod\nresult = pkg.f()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.module_name == "pkg" and flow.source.symbol_name == "f"


def test_stage_1c6_module_alias_rebind_is_not_import_exact():
    facts = _stage_1c_facts("import pkg.mod as m\nm = other\nresult = m.f()\n")
    flows = _stage_1c_call_result_flows(facts)
    assert flows[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)


def test_stage_1c6_unrelated_assignment_does_not_invalidate_import_exactness():
    facts = _stage_1c_facts("from pkg.mod import f\nunrelated = other\nresult = f()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.module_name == "pkg.mod" and flow.source.symbol_name == "f"


def test_stage_1c6_instance_attribute_call_remains_dynamic_runtime_boundary():
    facts = _stage_1c_facts("result = obj.f()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC
    assert flow.dynamic_boundary == "dynamic_call"


def test_stage_1c6_star_import_has_no_import_authority():
    facts = _stage_1c_facts("from pkg import *\nresult = f()\n")
    flows = _stage_1c_call_result_flows(facts)
    assert flows[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)


def test_stage_1c6_star_import_invalidates_prior_import_exact_authority():
    facts = _stage_1c_facts(
        "from old import f\n"
        "from new import *\n"
        "result = f()\n"
    )
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.UNRESOLVED_NAME
    assert flow.confidence is LineageConfidence.UNRESOLVED
    assert not any(
        item.resolution_kind is ResolutionKind.IMPORT_EXACT
        for item in _stage_1c_call_result_flows(facts)
    )


def test_stage_1c6_star_import_invalidates_prior_local_callable_authority():
    facts = _stage_1c_facts(
        "def f():\n"
        " return 1\n"
        "from new import *\n"
        "result = f()\n"
    )
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.UNRESOLVED_NAME
    assert flow.confidence is LineageConfidence.UNRESOLVED
    assert not any(
        item.resolution_kind is ResolutionKind.CALL_EXACT
        for item in _stage_1c_call_result_flows(facts)
    )


def test_stage_1c6_relative_child_import_resolves_from_source_key():
    facts = _stage_1c_facts_at("from .sub import f\nresult = f()\n", "pkg/mod.py")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.module_name == "pkg.sub" and flow.source.symbol_name == "f"


def test_stage_1c6_relative_parent_import_resolves_from_source_key():
    facts = _stage_1c_facts_at("from ..util import f\nresult = f()\n", "pkg/sub/mod.py")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.module_name == "pkg.util" and flow.source.symbol_name == "f"


def test_stage_1c6_package_init_relative_arithmetic():
    first = _stage_1c_facts_at("from .sub import f\nresult = f()\n", "pkg/__init__.py")
    second = _stage_1c_facts_at("from ..util import f\nresult = f()\n", "pkg/sub/__init__.py")
    first_flow, second_flow = _stage_1c_call_result_flows(first)[0], _stage_1c_call_result_flows(second)[0]
    assert first_flow.resolution_kind is ResolutionKind.IMPORT_EXACT and first_flow.source.module_name == "pkg.sub"
    assert second_flow.resolution_kind is ResolutionKind.IMPORT_EXACT and second_flow.source.module_name == "pkg.util"


def test_stage_1c6_relative_current_package_import_resolves_from_source_key():
    facts = _stage_1c_facts_at("from . import f\nresult = f()\n", "pkg/sub/mod.py")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.module_name == "pkg.sub" and flow.source.symbol_name == "f"


def test_stage_1c6_relative_escape_has_no_import_exact_metadata():
    facts = _stage_1c_facts_at("from ..outside import f\nresult = f()\n", "pkg/mod.py")
    flows = _stage_1c_call_result_flows(facts)
    assert flows[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
    assert all(flow.resolution_kind is not ResolutionKind.IMPORT_EXACT for flow in flows)


def test_stage_1c6_imported_callee_snapshot_precedes_argument_rebind():
    facts = _stage_1c_facts("from pkg import f\nresult = f((f := other))\nlater = f()\n")
    first, later = _stage_1c_call_result_flows(facts)
    assert first.resolution_kind is ResolutionKind.IMPORT_EXACT and isinstance(first.source, ExtractedSymbolicRef)
    assert first.source.module_name == "pkg" and first.source.symbol_name == "f"
    assert later.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY


def test_stage_1c6_imported_call_arguments_do_not_bind_parameters():
    facts = _stage_1c_facts("from pkg import f\nresult = f(1, flag=2)\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.IMPORT_EXACT and flow.confidence is LineageConfidence.CONFIRMED
    assert not any(flow.relation is LineageRelation.ARGUMENT_TO_PARAMETER for flow in facts.flows)


def test_stage_1c6_nested_dotted_import_attribute_call_remains_dynamic():
    facts = _stage_1c_facts("import pkg.mod\nresult = pkg.mod.f()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC
    assert flow.dynamic_boundary == "dynamic_call"
    assert not any(item.resolution_kind is ResolutionKind.IMPORT_EXACT for item in _stage_1c_call_result_flows(facts))


def test_stage_1c6_local_function_call_remains_call_exact_not_import_exact():
    facts = _stage_1c_facts("def f():\n return 1\nresult = f()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT and flow.confidence is LineageConfidence.CONFIRMED
    assert flow.resolution_kind is not ResolutionKind.IMPORT_EXACT and isinstance(flow.source, ExtractedSymbolicRef)


def test_stage_1c5_dynamic_attribute_call_carries_required_boundary_metadata():
    facts = _stage_1c_facts("result = obj.method(1)\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY and flow.confidence is LineageConfidence.DYNAMIC and flow.dynamic_boundary == "dynamic_call"


def test_stage_1c_if_branches_are_exact_inside_and_ambiguous_after_merge():
    facts = _stage_1c_facts(
        "def run(cond):\n"
        " stable = 1\n"
        " if cond:\n"
        "  value = 2\n"
        "  left = value\n"
        " else:\n"
        "  value = 3\n"
        "  right = value\n"
        " after_value = value\n"
        " after_stable = stable\n"
    )
    value_bindings = _stage_1c_named(facts, "binding", "value")
    stable = _stage_1c_named(facts, "binding", "stable")[0]
    assert len(value_bindings) == 2
    assert _stage_1c_lexical_bind_sources(facts, "value", 5) == [
        next(anchor.local_id for anchor in value_bindings if anchor.span.start_line == 4)
    ]
    assert _stage_1c_lexical_bind_sources(facts, "value", 8) == [
        next(anchor.local_id for anchor in value_bindings if anchor.span.start_line == 7)
    ]
    assert _stage_1c_lexical_bind_sources(facts, "value", 9) == []
    assert _stage_1c_lexical_bind_sources(facts, "stable", 10) == [
        stable.local_id
    ]


def test_stage_1c_if_without_else_invalidates_conditional_rebind():
    facts = _stage_1c_facts(
        "def run(cond):\n"
        " value = 1\n"
        " if cond:\n"
        "  value = 2\n"
        " after = value\n"
    )
    assert _stage_1c_lexical_bind_sources(
        facts,
        "value",
        5,
    ) == []


def test_stage_1c_for_body_touch_invalidates_non_target_binding_after_loop():
    facts = _stage_1c_facts(
        "def run(items):\n"
        " stable = 1\n"
        " changed = 2\n"
        " for item in items:\n"
        "  changed = item\n"
        " after_changed = changed\n"
        " after_stable = stable\n"
    )
    stable = _stage_1c_named(facts, "binding", "stable")[0]
    assert _stage_1c_lexical_bind_sources(
        facts,
        "changed",
        6,
    ) == []
    assert _stage_1c_lexical_bind_sources(
        facts,
        "stable",
        7,
    ) == [stable.local_id]


def test_stage_1c_while_body_and_else_only_bindings_are_not_exact_after_loop():
    facts = _stage_1c_facts(
        "def run(cond):\n"
        " value = 1\n"
        " while cond:\n"
        "  value = 2\n"
        " else:\n"
        "  else_only = 3\n"
        " after_value = value\n"
        " after_else = else_only\n"
    )
    assert _stage_1c_lexical_bind_sources(
        facts,
        "value",
        7,
    ) == []
    assert _stage_1c_lexical_bind_sources(
        facts,
        "else_only",
        8,
    ) == []


def test_stage_1c_try_handler_conflict_merges_to_unresolved_but_finally_is_exact():
    facts = _stage_1c_facts(
        "def run():\n"
        " try:\n"
        "  value = 1\n"
        "  try_seen = value\n"
        " except Error:\n"
        "  value = 2\n"
        "  except_seen = value\n"
        " finally:\n"
        "  stable = 3\n"
        " after_value = value\n"
        " after_stable = stable\n"
    )
    value_bindings = _stage_1c_named(facts, "binding", "value")
    try_value = next(anchor for anchor in value_bindings if anchor.span.start_line == 3)
    except_value = next(anchor for anchor in value_bindings if anchor.span.start_line == 6)
    stable = _stage_1c_named(facts, "binding", "stable")[0]
    assert _stage_1c_lexical_bind_sources(facts, "value", 4) == [try_value.local_id]
    assert _stage_1c_lexical_bind_sources(facts, "value", 7) == [except_value.local_id]
    assert _stage_1c_lexical_bind_sources(facts, "value", 10) == []
    assert _stage_1c_lexical_bind_sources(facts, "stable", 11) == [stable.local_id]


def test_stage_1c_try_merge_observes_handler_body_rebinding():
    facts = _stage_1c_facts(
        "def run():\n"
        " value = 0\n"
        " try:\n"
        "  pass\n"
        " except Error:\n"
        "  value = 1\n"
        " after = value\n"
    )
    assert _stage_1c_lexical_bind_sources(
        facts,
        "value",
        7,
    ) == []


def test_stage_1c_finally_does_not_restore_pre_handler_binding_after_handler_rebind():
    facts = _stage_1c_facts(
        "def run():\n"
        " value = 0\n"
        " try:\n"
        "  pass\n"
        " except Error:\n"
        "  value = 1\n"
        " finally:\n"
        "  seen = value\n"
    )
    assert _stage_1c_lexical_bind_sources(
        facts,
        "value",
        9,
    ) == []


def test_stage_1c_try_handler_starts_from_entry_not_partial_try_state():
    facts = _stage_1c_facts(
        "def run():\n"
        " before = 1\n"
        " try:\n"
        "  partial = before\n"
        "  explode()\n"
        " except Error:\n"
        "  seen_before = before\n"
        "  seen_partial = partial\n"
    )
    before = _stage_1c_named(facts, "binding", "before")[0]
    assert _stage_1c_lexical_bind_sources(facts, "before", 7) == [before.local_id]
    assert _stage_1c_lexical_bind_sources(facts, "partial", 8) == []


def test_stage_1c_match_cases_are_independent_and_no_match_path_is_preserved():
    facts = _stage_1c_facts(
        "def run(subject):\n"
        " value = 0\n"
        " match subject:\n"
        "  case 1:\n"
        "   value = 1\n"
        "   first = value\n"
        "  case 2:\n"
        "   value = 2\n"
        "   second = value\n"
        " after = value\n"
    )
    value_bindings = _stage_1c_named(facts, "binding", "value")
    first_case = next(anchor for anchor in value_bindings if anchor.span.start_line == 5)
    second_case = next(anchor for anchor in value_bindings if anchor.span.start_line == 8)
    assert _stage_1c_lexical_bind_sources(facts, "value", 6) == [first_case.local_id]
    assert _stage_1c_lexical_bind_sources(facts, "value", 9) == [second_case.local_id]
    assert _stage_1c_lexical_bind_sources(facts, "value", 10) == []


def test_stage_1c_for_target_is_runtime_bound_only_inside_loop_body():
    facts = _stage_1c_facts(
        "def run(items):\n"
        " for item in items:\n"
        "  inside = item\n"
        " after = item\n"
    )
    runtime = _stage_1c_runtime_assignment(facts, "item")
    item_binding = _stage_1c_named(facts, "binding", "item")[0]
    assert runtime.target.local_id == item_binding.local_id
    inside_load = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == item_binding.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
        and flow.evidence.start_line == 3
    )
    assert inside_load.source.local_id == item_binding.local_id
    assert not any(
        flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
        and flow.evidence.start_line == 4
        for flow in facts.flows
    )


def test_stage_1c_for_target_does_not_restore_prior_exact_binding_after_loop():
    facts = _stage_1c_facts(
        "def run(items):\n"
        " item = 1\n"
        " for item in items:\n"
        "  inside = item\n"
        " after = item\n"
    )
    prior = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "item")
        if anchor.span.start_line == 2
    )
    runtime_binding = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "item")
        if anchor.span.start_line == 3
    )
    inside = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == runtime_binding.local_id
        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
        and flow.evidence.start_line == 4
    )
    assert inside.source.local_id == runtime_binding.local_id
    assert not any(
        flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id in {prior.local_id, runtime_binding.local_id}
        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
        and flow.evidence.start_line == 5
        for flow in facts.flows
    )


def test_stage_1c_for_else_does_not_claim_prior_or_runtime_target_as_exact():
    facts = _stage_1c_facts(
        "def run(items):\n"
        " item = 1\n"
        " for item in items:\n"
        "  pass\n"
        " else:\n"
        "  probe = item\n"
    )
    item_bindings = {
        anchor.local_id
        for anchor in _stage_1c_named(facts, "binding", "item")
    }
    assert not any(
        flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id in item_bindings
        and parse_local_occurrence_id(flow.target.local_id)[3] == "item"
        and flow.evidence.start_line == 6
        for flow in facts.flows
    )


def test_stage_1c_for_destructuring_gets_independent_runtime_sources():
    facts = _stage_1c_facts(
        "def run(rows):\n"
        " for left, *rest in rows:\n"
        "  a = left\n"
        "  b = rest\n"
    )
    left_runtime = _stage_1c_runtime_assignment(facts, "left")
    rest_runtime = _stage_1c_runtime_assignment(facts, "rest")
    assert left_runtime.source.local_id != rest_runtime.source.local_id
    assert parse_local_occurrence_id(left_runtime.source.local_id)[0] == "runtime_bound_local"
    assert parse_local_occurrence_id(rest_runtime.source.local_id)[0] == "runtime_bound_local"
    assert not any(
        flow.relation is LineageRelation.ASSIGNS
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.target.local_id)[3] in {"left", "rest"}
        and parse_local_occurrence_id(flow.source.local_id)[0] != "runtime_bound_local"
        for flow in facts.flows
    )


def test_stage_1c_with_binding_is_runtime_bound_and_remains_available_after_body():
    facts = _stage_1c_facts(
        "def run(manager):\n"
        " with manager as resource:\n"
        "  inside = resource\n"
        " after = resource\n"
    )
    runtime = _stage_1c_runtime_assignment(facts, "resource")
    resource_binding = _stage_1c_named(facts, "binding", "resource")[0]
    assert runtime.target.local_id == resource_binding.local_id
    loads = [
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == resource_binding.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "resource"
    ]
    assert {flow.evidence.start_line for flow in loads} == {3, 4}


def test_stage_1c_with_items_bind_sequentially_without_context_producer_flow():
    facts = _stage_1c_facts(
        "def run(first):\n"
        " with first as x, x as y:\n"
        "  result = y\n"
    )
    x_runtime = _stage_1c_runtime_assignment(facts, "x")
    y_runtime = _stage_1c_runtime_assignment(facts, "y")
    x_binding = _stage_1c_named(facts, "binding", "x")[0]
    second_context_load = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == x_binding.local_id
        and parse_local_occurrence_id(flow.target.local_id)[3] == "x"
        and flow.evidence.start_line == 2
    )
    assert second_context_load.source.local_id == x_binding.local_id
    assert parse_local_occurrence_id(x_runtime.source.local_id)[0] == "runtime_bound_local"
    assert parse_local_occurrence_id(y_runtime.source.local_id)[0] == "runtime_bound_local"


def test_stage_1c_except_alias_is_runtime_bound_only_inside_handler():
    facts = _stage_1c_facts(
        "def run():\n"
        " try:\n"
        "  pass\n"
        " except Error as exc:\n"
        "  inside = exc\n"
        " after = exc\n"
    )
    runtime = _stage_1c_runtime_assignment(facts, "exc")
    exc_binding = _stage_1c_named(facts, "binding", "exc")[0]
    assert runtime.target.local_id == exc_binding.local_id
    inside_load = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == exc_binding.local_id
        and parse_local_occurrence_id(flow.target.local_id)[3] == "exc"
        and flow.evidence.start_line == 5
    )
    assert inside_load.source.local_id == exc_binding.local_id
    assert not any(
        flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.target.local_id)[3] == "exc"
        and flow.evidence.start_line == 6
        for flow in facts.flows
    )


def test_stage_1c_except_alias_does_not_restore_prior_exact_binding_after_handler():
    facts = _stage_1c_facts(
        "def run():\n"
        " exc = 1\n"
        " try:\n"
        "  pass\n"
        " except Error as exc:\n"
        "  inside = exc\n"
        " after = exc\n"
    )
    bindings = _stage_1c_named(facts, "binding", "exc")
    prior = next(anchor for anchor in bindings if anchor.span.start_line == 2)
    handler = next(anchor for anchor in bindings if anchor.span.start_line == 5)
    inside = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == handler.local_id
        and parse_local_occurrence_id(flow.target.local_id)[3] == "exc"
        and flow.evidence.start_line == 6
    )
    assert inside.source.local_id == handler.local_id
    assert not any(
        flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id in {prior.local_id, handler.local_id}
        and parse_local_occurrence_id(flow.target.local_id)[3] == "exc"
        and flow.evidence.start_line == 7
        for flow in facts.flows
    )


def test_stage_1c_async_for_and_async_with_use_runtime_bound_locals():
    facts = _stage_1c_facts(
        "async def run(items, manager):\n"
        " async for item in items:\n"
        "  seen = item\n"
        " async with manager as resource:\n"
        "  used = resource\n"
    )
    item_runtime = _stage_1c_runtime_assignment(facts, "item")
    resource_runtime = _stage_1c_runtime_assignment(facts, "resource")
    assert parse_local_occurrence_id(item_runtime.source.local_id)[0] == "runtime_bound_local"
    assert parse_local_occurrence_id(resource_runtime.source.local_id)[0] == "runtime_bound_local"
    assert item_runtime.resolution_kind is ResolutionKind.LEXICAL_EXACT
    assert resource_runtime.resolution_kind is ResolutionKind.LEXICAL_EXACT
    assert item_runtime.confidence is LineageConfidence.CONFIRMED
    assert resource_runtime.confidence is LineageConfidence.CONFIRMED


def test_stage_1c_direct_assignments_chain_through_current_frame():
    facts = _stage_1c_facts(
        "def run(arg):\n"
        " first = arg\n"
        " second = first\n"
        " return second\n"
    )
    arg_param = _stage_1c_named(facts, "parameter", "arg")[0]
    first = _stage_1c_named(facts, "binding", "first")[0]
    second = _stage_1c_named(facts, "binding", "second")[0]
    lexical_binds = [
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
    ]
    assigns = [
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.ASSIGNS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
    ]
    arg_bind = next(
        flow
        for flow in lexical_binds
        if flow.source.local_id == arg_param.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "arg"
    )
    first_assign = next(
        flow
        for flow in assigns
        if flow.source.local_id == arg_bind.target.local_id
        and flow.target.local_id == first.local_id
    )
    first_bind = next(
        flow
        for flow in lexical_binds
        if flow.source.local_id == first.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "first"
    )
    second_assign = next(
        flow
        for flow in assigns
        if flow.source.local_id == first_bind.target.local_id
        and flow.target.local_id == second.local_id
    )
    second_bind = next(
        flow
        for flow in lexical_binds
        if flow.source.local_id == second.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "second"
    )
    assert first_assign.target.local_id == first.local_id
    assert second_assign.target.local_id == second.local_id
    assert second_bind.source.local_id == second.local_id

def test_stage_1c_rebinding_uses_latest_prior_unconditional_binding():
    facts = _stage_1c_facts("x=1\nbefore=x\nx=2\nafter=x\n")
    xs = _stage_1c_named(facts, "binding", "x")
    loads = [f for f in facts.flows if f.relation is LineageRelation.BINDS and isinstance(f.target, ExtractedOccurrenceRef) and parse_local_occurrence_id(f.target.local_id)[0] == "name_load" and parse_local_occurrence_id(f.target.local_id)[3] == "x"]
    assert [f.source.local_id for f in loads] == [xs[0].local_id, xs[1].local_id]


def test_stage_1c_annotation_only_and_destructuring_do_not_claim_direct_value_flow():
    facts = _stage_1c_facts(
        "source=1\n"
        "a: int = source\n"
        "b: int\n"
        "probe = b\n"
        "left, right = source\n"
    )
    a = _stage_1c_named(facts, "binding", "a")[0]
    b = _stage_1c_named(facts, "binding", "b")[0]
    left = _stage_1c_named(facts, "binding", "left")[0]
    right = _stage_1c_named(facts, "binding", "right")[0]
    assert any(
        flow.relation is LineageRelation.ASSIGNS
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.target.local_id == a.local_id
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        for flow in facts.flows
    )
    assert not any(
        flow.relation is LineageRelation.ASSIGNS
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.target.local_id == b.local_id
        for flow in facts.flows
    )
    assert not any(
        flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "b"
        for flow in facts.flows
    )
    assert not any(
        flow.relation is LineageRelation.ASSIGNS
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.target.local_id in {left.local_id, right.local_id}
        for flow in facts.flows
    )

def test_stage_1c_walrus_updates_current_frame():
    facts = _stage_1c_facts("def run(source):\n result = (captured := source)\n return captured\n")
    captured = _stage_1c_named(facts, "binding", "captured")[0]
    result = _stage_1c_named(facts, "binding", "result")[0]
    assert any(f.target.local_id == captured.local_id and f.relation is LineageRelation.ASSIGNS for f in facts.flows)
    assert any(f.target.local_id == result.local_id and f.relation is LineageRelation.ASSIGNS for f in facts.flows)
    assert any(isinstance(f.source, ExtractedOccurrenceRef) and f.source.local_id == captured.local_id and f.relation is LineageRelation.BINDS for f in facts.flows)


def test_stage_1c_defs_and_import_bindings_are_local_lexical_sources_only():
    facts = _stage_1c_facts(
        "from pkg import item as imported\n"
        "def helper(): pass\n"
        "a=imported\n"
        "b=helper\n"
    )
    imported = _stage_1c_named(facts, "import_binding", "imported")[0]
    helper = _stage_1c_named(facts, "function", "helper")[0]
    imported_flow = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == imported.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "imported"
    )
    helper_flow = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == helper.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "helper"
    )
    assert imported_flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
    assert imported_flow.confidence is LineageConfidence.CONFIRMED
    assert helper_flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
    assert helper_flow.confidence is LineageConfidence.CONFIRMED
    assert not any(
        flow.resolution_kind is ResolutionKind.IMPORT_EXACT
        for flow in facts.flows
    )

def test_stage_1c_does_not_resolve_enclosing_global_or_nonlocal_names():
    facts = _stage_1c_facts("x=1\ndef outer():\n y=2\n def inner():\n  nonlocal y\n  return x+y\n return inner\n")
    assert not any(f.relation is LineageRelation.BINDS and f.resolution_kind is ResolutionKind.LEXICAL_EXACT and isinstance(f.target, ExtractedOccurrenceRef) and parse_local_occurrence_id(f.target.local_id)[3] in {"x", "y"} for f in facts.flows)


def test_stage_1c_augassign_requires_prior_local_and_has_no_single_source_assign_flow():
    facts = _stage_1c_facts(
        "known=1\n"
        "known += rhs\n"
        "return_known=known\n"
        "missing += rhs\n"
        "after=missing\n"
    )
    known_bindings = _stage_1c_named(facts, "binding", "known")
    initial_known = next(anchor for anchor in known_bindings if anchor.span.start_line == 1)
    aug_known = next(anchor for anchor in known_bindings if anchor.span.start_line == 2)
    aug_read = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == initial_known.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "known"
        and flow.evidence.start_line == 2
    )
    later_known = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.source.local_id == aug_known.local_id
        and parse_local_occurrence_id(flow.target.local_id)[0] == "name_load"
        and parse_local_occurrence_id(flow.target.local_id)[3] == "known"
        and flow.evidence.start_line == 3
    )
    assert aug_read.source.local_id == initial_known.local_id
    assert later_known.source.local_id == aug_known.local_id
    assert not any(
        flow.relation is LineageRelation.ASSIGNS
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and flow.target.local_id == aug_known.local_id
        for flow in facts.flows
    )
    assert not any(
        flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.target.local_id)[3] == "missing"
        for flow in facts.flows
    )

def test_stage_1c_augassign_snapshots_prior_before_rhs_rebinding():
    facts = _stage_1c_facts("x = 1\nx += (x := 2)\nafter = x\n")
    bindings = _stage_1c_named(facts, "binding", "x")
    initial = next(anchor for anchor in bindings if anchor.span.start_line == 1)
    aug_binding = next(anchor for anchor in bindings if anchor.span.start_line == 2 and anchor.span.start_column == 0)
    walrus_binding = next(anchor for anchor in bindings if anchor.span.start_line == 2 and anchor.span.start_column > 0)
    lexical = [flow for flow in facts.flows if flow.relation is LineageRelation.BINDS and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT and isinstance(flow.source, ExtractedOccurrenceRef) and isinstance(flow.target, ExtractedOccurrenceRef)]
    aug_read = next(flow for flow in lexical if parse_local_occurrence_id(flow.target.local_id)[3] == "x" and flow.evidence.start_line == 2 and flow.evidence.start_column == 0)
    after_read = next(flow for flow in lexical if parse_local_occurrence_id(flow.target.local_id)[3] == "x" and flow.evidence.start_line == 3)
    assert aug_read.source.local_id == initial.local_id
    assert aug_read.source.local_id != walrus_binding.local_id
    assert after_read.source.local_id == aug_binding.local_id
    assert not any(flow.relation is LineageRelation.ASSIGNS and isinstance(flow.target, ExtractedOccurrenceRef) and flow.target.local_id == aug_binding.local_id for flow in facts.flows)


def test_extraction_is_deterministic_source_local_and_has_parameter_lineage(monkeypatch):
    tree = ast.parse("import pkg.mod as pm\nvalue = 1\ndef run(arg):\n    local = arg\n    return local\n")
    monkeypatch.setattr("builtins.open", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("extractor performed filesystem I/O")))
    first = extract_lineage_source_facts(tree, source_key="pkg/mod.py", source_fingerprint=FINGERPRINT)
    second = extract_lineage_source_facts(tree, source_key="pkg/mod.py", source_fingerprint=FINGERPRINT)
    assert first == second
    assert first.status is LineageFamilyStatus.FRESH
    assert first.flows and first.surfaces == ()
    assert len({item.local_id for item in first.anchors}) == len(first.anchors)
    module = sys.modules["contextor.core.analysis.lineage_extraction"]
    assert "PersistentIdentityRegistry" not in vars(module)
    assert "RepositoryAnalysisState" not in vars(module)
    assert "SemanticEndpoint" not in vars(module)


def test_typed_parameter_ids_bind_and_defaults_need_no_ast_reread():
    tree = ast.parse("def run(a, /, b=1, *items, flag=2, **extra):\n    return b\n")
    facts = extract_lineage_source_facts(tree, source_key="pkg.py", source_fingerprint=FINGERPRINT)
    parsed_parameters = {
        parse_local_occurrence_id(anchor.local_id)
        for anchor in facts.anchors
        if anchor.kind == "parameter"
    }
    assert {(kind, ordinal, name) for kind, _path, ordinal, name in parsed_parameters} == {
        ("parameter_posonly", 0, "a"),
        ("parameter_poskw", 0, "b"),
        ("parameter_vararg", 0, "items"),
        ("parameter_kwonly", 0, "flag"),
        ("parameter_varkw", 0, "extra"),
    }
    binds = [
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.SIGNATURE_EXACT
    ]
    assert len(binds) == 5
    assert all(
        flow.source.kind is ExtractedSymbolicKind.PARAMETER
        and flow.resolution_kind is ResolutionKind.SIGNATURE_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and flow.source.source_local_id is not None
        for flow in binds
    )
    for flow in binds:
        kind, _path, _ordinal, name = parse_local_occurrence_id(flow.source.source_local_id)
        assert kind.startswith("parameter_")
        assert name
    defaults = [flow for flow in facts.flows if flow.relation is LineageRelation.DEFAULTS_TO_PARAMETER]
    assert len(defaults) == 2
    assert all(
        isinstance(flow.source, ExtractedOccurrenceRef)
        and flow.target.kind is ExtractedSymbolicKind.PARAMETER
        and flow.resolution_kind is ResolutionKind.SIGNATURE_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        for flow in defaults
    )


def test_lexical_owners_parameters_comprehensions_and_declarations():
    tree = ast.parse("seed = 1\ndef outer(x=(y := seed)):\n    global g, h\n    def inner(arg):\n        nonlocal x\n        return arg\n    values = [item for item in range(3)]\n    return inner\n")
    facts = extract_lineage_source_facts(tree, source_key="pkg.py", source_fingerprint=FINGERPRINT)
    decoded = _decoded_anchors(facts)
    by_name = {}
    for anchor, (kind, _path, ordinal, name) in decoded:
        if name is not None:
            by_name.setdefault((kind, name), []).append((anchor, ordinal))
    module_anchor = next(anchor for anchor, (kind, *_rest) in decoded if kind == "module")
    outer = by_name[("function", "outer")][0][0]
    inner = by_name[("function", "inner")][0][0]
    assert outer.owner_local_id == module_anchor.local_id
    assert inner.owner_local_id == outer.local_id
    assert by_name[("parameter_poskw", "x")][0][0].owner_local_id == outer.local_id
    assert by_name[("parameter_poskw", "arg")][0][0].owner_local_id == inner.local_id
    assert by_name[("binding", "y")][0][0].owner_local_id == module_anchor.local_id
    comprehension = next(anchor for anchor, (kind, *_rest) in decoded if kind == "comprehension")
    assert by_name[("binding", "item")][0][0].owner_local_id == comprehension.local_id
    assert {name: ordinal for _anchor, (kind, _path, ordinal, name) in decoded if kind == "global_declaration"} == {"g": 0, "h": 1}
    assert by_name[("nonlocal_declaration", "x")][0][0].owner_local_id == inner.local_id


def test_attribute_and_subscript_store_are_not_1b_binding_anchors():
    facts = extract_lineage_source_facts(ast.parse("obj.attr = value\nitems[index] = value\nplain = value\n"), source_key="pkg.py", source_fingerprint=FINGERPRINT)
    names = {name for _anchor, (kind, _path, _ordinal, name) in _decoded_anchors(facts) if kind == "binding"}
    assert "plain" in names and "attr" not in names and "items" not in names


def test_resource_limits_fail_closed_without_partial_fresh_slice():
    node_limited = extract_lineage_source_facts(ast.parse("x = 1\ny = 2\n"), source_key="pkg.py", source_fingerprint=FINGERPRINT, limits=LineageExtractionLimits(max_nodes=1, max_ast_depth=100))
    assert node_limited.status is LineageFamilyStatus.RESOURCE_LIMIT
    assert node_limited.resource_limit_reason == "node_limit"
    assert node_limited.anchors == () and node_limited.flows == () and node_limited.surfaces == ()
    depth_limited = extract_lineage_source_facts(ast.parse("def f():\n    if True:\n        x = 1\n"), source_key="pkg.py", source_fingerprint=FINGERPRINT, limits=LineageExtractionLimits(max_nodes=100, max_ast_depth=1))
    assert depth_limited.status is LineageFamilyStatus.RESOURCE_LIMIT
    assert depth_limited.resource_limit_reason == "ast_depth_limit"


@pytest.mark.parametrize("use_bom", [False, True])
def test_parsed_source_fingerprint_is_exact_raw_sha256_and_encoding_safe(tmp_path, use_bom):
    path = tmp_path / "encoded.py"
    raw = codecs.BOM_UTF8 + "value = 'ą'\n".encode("utf-8") if use_bom else b"# -*- coding: cp1250 -*-\n" + "value = 'ą'\n".encode("cp1250")
    path.write_bytes(raw)
    parsed = parse_source_with_fingerprint(path)
    assert isinstance(parsed.tree, ast.AST)
    assert parsed.source_fingerprint == hashlib.sha256(raw).hexdigest()


def test_full_index_transports_transient_lineage_on_cache_miss_and_hit(tmp_path, monkeypatch):
    source = tmp_path / "pkg.py"
    source.write_text("value = 1\n", encoding="utf-8")
    class FakeCache:
        def __init__(self): self.data = None
        def get(self, _path): return self.data
        def set(self, _path, data): self.data = data
    cache = FakeCache()
    monkeypatch.setattr(indexer_module, "_cache_manager", lambda _root: cache)
    first = indexer_module._process_single_file(str(source), str(tmp_path))
    second = indexer_module._process_single_file(str(source), str(tmp_path))
    assert second["lineage_facts"] == first["lineage_facts"]
    assert first["lineage_facts"].source_key == "pkg.py"
    assert first["lineage_facts"].source_fingerprint == hashlib.sha256(source.read_bytes()).hexdigest()


def test_repository_index_collects_source_keyed_transient_lineage(tmp_path, monkeypatch):
    (tmp_path / "pkg.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    class FakeCache:
        def get(self, _path): return None
        def set(self, _path, _data): return None
    monkeypatch.setattr(indexer_module, "_cache_manager", lambda _root: FakeCache())
    result = indexer_module.index_repository(str(tmp_path))
    assert set(result.lineage_facts_by_source) == {"pkg.py"}


def test_incremental_preparation_carries_transient_lineage_and_errors_do_not(tmp_path):
    path = tmp_path / "pkg.py"
    path.write_text("value = 1\n", encoding="utf-8")
    prepared = prepare_source_update(file_path=path, module_path="pkg", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="pkg.py")
    assert not prepared.has_error and prepared.extracted_lineage_facts is not None
    assert prepared.extracted_lineage_facts.surfaces == ()
    path.write_text("def broken(:\n", encoding="utf-8")
    broken = prepare_source_update(file_path=path, module_path="pkg", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="pkg.py")
    assert broken.has_error and broken.error_status == "SYNTAX_ERROR" and broken.extracted_lineage_facts is None
    missing = prepare_source_update(file_path=tmp_path / "missing.py", module_path="missing", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="missing.py")
    assert missing.has_error and missing.error_status == "ERROR" and missing.extracted_lineage_facts is None


def _stage_1c_exact_bind_flows(facts, name):
    return [
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.BINDS
        and flow.resolution_kind is ResolutionKind.LEXICAL_EXACT
        and flow.confidence is LineageConfidence.CONFIRMED
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and isinstance(flow.target, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.target.local_id)[3] == name
    ]


def test_stage_1c7_outermost_iterable_uses_enclosing_binding():
    facts = _stage_1c_facts(
        "def run(items):\n"
        " outer = items\n"
        " result = [item for item in outer]\n"
    )
    outer = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "outer")
        if anchor.span.start_line == 2
    )
    assert _stage_1c_lexical_bind_sources(facts, "outer", 3) == [
        outer.local_id
    ]


def test_stage_1c7_target_is_comprehension_local_and_shadows_outer_inside():
    facts = _stage_1c_facts(
        "def run(items):\n"
        " x = items\n"
        " result = [x for x in items]\n"
    )
    outer = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "x")
        if anchor.span.start_line == 2
    )
    target = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "x")
        if anchor.span.start_line == 3
    )
    comprehension = next(
        anchor for anchor in facts.anchors if anchor.kind == "comprehension"
    )
    assert target.owner_local_id == comprehension.local_id
    assert target.owner_local_id != outer.owner_local_id
    assert _stage_1c_lexical_bind_sources(facts, "x", 3) == [
        target.local_id
    ]


def test_stage_1c7_target_does_not_leak_and_outer_binding_remains_exact():
    facts = _stage_1c_facts(
        "def run(items):\n"
        " x = items\n"
        " result = [x for x in items]\n"
        " after = x\n"
    )
    outer = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "x")
        if anchor.span.start_line == 2
    )
    target = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "x")
        if anchor.span.start_line == 3
    )
    assert _stage_1c_lexical_bind_sources(facts, "x", 4) == [
        outer.local_id
    ]
    assert target.local_id not in _stage_1c_lexical_bind_sources(facts, "x", 4)


def test_stage_1c7_element_sees_first_runtime_target():
    facts = _stage_1c_facts("result = [x for x in xs]\n")
    runtime = _stage_1c_runtime_assignment(facts, "x")
    binds = _stage_1c_exact_bind_flows(facts, "x")
    assert len(binds) == 1
    assert binds[0].source.local_id == runtime.target.local_id
    assert binds[0].resolution_kind is ResolutionKind.LEXICAL_EXACT
    assert binds[0].confidence is LineageConfidence.CONFIRMED


def test_stage_1c7_filter_sees_first_runtime_target():
    facts = _stage_1c_facts("result = [x for x in xs if x]\n")
    runtime = _stage_1c_runtime_assignment(facts, "x")
    binds = _stage_1c_exact_bind_flows(facts, "x")
    assert len(binds) == 2
    assert all(flow.source.local_id == runtime.target.local_id for flow in binds)
    assert all(flow.relation is LineageRelation.BINDS for flow in binds)


def test_stage_1c7_later_generator_iterable_sees_prior_runtime_target():
    facts = _stage_1c_facts("result = [(x, y) for x in xs for y in x]\n")
    runtime = _stage_1c_runtime_assignment(facts, "x")
    binds = _stage_1c_exact_bind_flows(facts, "x")
    assert len(binds) == 2
    assert all(flow.source.local_id == runtime.target.local_id for flow in binds)
    assert all(flow.confidence is LineageConfidence.CONFIRMED for flow in binds)


def test_stage_1c7_later_target_sees_its_filter_and_final_value():
    facts = _stage_1c_facts(
        "result = [(x, y) for x in xs for y in ys if y]\n"
    )
    runtime = _stage_1c_runtime_assignment(facts, "y")
    binds = _stage_1c_exact_bind_flows(facts, "y")
    assert len(binds) == 2
    assert all(flow.source.local_id == runtime.target.local_id for flow in binds)
    assert all(flow.resolution_kind is ResolutionKind.LEXICAL_EXACT for flow in binds)


def test_stage_1c7_nested_comprehensions_keep_targets_independent():
    facts = _stage_1c_facts(
        "def run(xs):\n"
        " return [[y for y in x] for x in xs]\n"
    )
    comprehensions = [
        anchor for anchor in facts.anchors if anchor.kind == "comprehension"
    ]
    x = _stage_1c_named(facts, "binding", "x")[0]
    y = _stage_1c_named(facts, "binding", "y")[0]
    assert len(comprehensions) == 2
    assert x.owner_local_id != y.owner_local_id
    assert any(
        flow.source.local_id == x.local_id
        for flow in _stage_1c_exact_bind_flows(facts, "x")
    )


def test_stage_1c7_walrus_is_visible_on_body_path_but_not_afterwards():
    facts = _stage_1c_facts(
        "def run(xs):\n"
        " result = [(y := x, y) for x in xs]\n"
        " after = y\n"
    )
    y = _stage_1c_named(facts, "binding", "y")[0]
    y_binds = _stage_1c_exact_bind_flows(facts, "y")
    assert any(
        flow.source.local_id == y.local_id and flow.evidence.start_line == 2
        for flow in y_binds
    )
    assert not any(flow.evidence.start_line == 3 for flow in y_binds)


def test_stage_1c7_zero_body_walrus_rebind_invalidates_prior_authority():
    facts = _stage_1c_facts(
        "def run(xs, old):\n"
        " y = old\n"
        " result = [(y := x) for x in xs]\n"
        " after = y\n"
    )
    prior = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "y")
        if anchor.span.start_line == 2
    )
    walrus = next(
        anchor
        for anchor in _stage_1c_named(facts, "binding", "y")
        if anchor.span.start_line == 3
    )
    post_sources = _stage_1c_lexical_bind_sources(facts, "y", 4)
    assert prior.local_id != walrus.local_id
    assert post_sources == []
    assert prior.local_id not in post_sources
    assert walrus.local_id not in post_sources


def test_stage_1c7_filter_walrus_visibility_and_zero_iteration_merge():
    facts = _stage_1c_facts(
        "def run(xs):\n"
        " result = [y for x in xs if (y := x)]\n"
        " after = y\n"
    )
    y = _stage_1c_named(facts, "binding", "y")[0]
    y_binds = _stage_1c_exact_bind_flows(facts, "y")
    assert any(
        flow.source.local_id == y.local_id and flow.evidence.start_line == 2
        for flow in y_binds
    )
    assert not any(flow.evidence.start_line == 3 for flow in y_binds)


def test_stage_1c7_nested_walrus_uses_containing_owner_and_merges_conservatively():
    facts = _stage_1c_facts(
        "def run(xs, ys):\n"
        " result = [[((z := y), z) for y in ys] for x in xs]\n"
        " after = z\n"
    )
    function = _stage_1c_named(facts, "function", "run")[0]
    z = _stage_1c_named(facts, "binding", "z")[0]
    z_binds = _stage_1c_exact_bind_flows(facts, "z")
    assert z.owner_local_id == function.local_id
    assert any(
        flow.source.local_id == z.local_id and flow.evidence.start_line == 2
        for flow in z_binds
    )
    assert not any(flow.evidence.start_line == 3 for flow in z_binds)


@pytest.mark.parametrize(
    "source",
    (
        "def run(xs):\n result = [x for x in xs]\n",
        "def run(xs):\n result = {x for x in xs}\n",
        "def run(xs):\n result = (x for x in xs)\n",
        "def run(xs):\n result = {x: x for x in xs}\n",
    ),
)
def test_stage_1c7_all_comprehension_forms_have_one_local_target(source):
    facts = _stage_1c_facts(source)
    comprehensions = [
        anchor for anchor in facts.anchors if anchor.kind == "comprehension"
    ]
    target = _stage_1c_named(facts, "binding", "x")[0]
    runtime = _stage_1c_runtime_assignment(facts, "x")
    assert len(comprehensions) == 1
    assert target.owner_local_id == comprehensions[0].local_id
    assert runtime.target.local_id == target.local_id


def test_stage_1c7_dict_key_walrus_precedes_value_and_does_not_leak():
    facts = _stage_1c_facts(
        "def run(xs):\n"
        " result = {(y := x): y for x in xs}\n"
        " after = y\n"
    )
    y = _stage_1c_named(facts, "binding", "y")[0]
    y_binds = _stage_1c_exact_bind_flows(facts, "y")
    body_bind = next(
        flow
        for flow in y_binds
        if flow.source.local_id == y.local_id
        and flow.evidence.start_line == 2
    )
    assert parse_local_occurrence_id(body_bind.target.local_id)[1] > parse_local_occurrence_id(
        y.local_id
    )[1]
    assert not any(flow.evidence.start_line == 3 for flow in y_binds)


@pytest.mark.parametrize(
    "source",
    (
        "def run(xs):\n def target(): return 1\n [(target := other) for x in xs]\n return target()\n",
        "def run(xs):\n from pkg import target\n [(target := other) for x in xs]\n return target()\n",
    ),
)
def test_stage_1c7_walrus_callable_and_import_rebind_are_unresolved_after_merge(
    source,
):
    facts = _stage_1c_facts(source)
    later = next(
        flow
        for flow in _stage_1c_call_result_flows(facts)
        if flow.evidence.start_line == 4
    )
    assert later.resolution_kind is ResolutionKind.UNRESOLVED_NAME
    assert later.confidence is LineageConfidence.UNRESOLVED
    assert later.dynamic_boundary is None


@pytest.mark.parametrize(
    ("source", "resolution"),
    (
        (
            "def run():\n"
            " def produce(): return 1\n"
            " result = [x for x in produce()]\n",
            ResolutionKind.CALL_EXACT,
        ),
        (
            "def run():\n"
            " from pkg import produce\n"
            " result = [x for x in produce()]\n",
            ResolutionKind.IMPORT_EXACT,
        ),
    ),
)
def test_stage_1c7_outermost_iterable_call_uses_enclosing_authority(
    source,
    resolution,
):
    facts = _stage_1c_facts(source)
    call = next(
        flow
        for flow in _stage_1c_call_result_flows(facts)
        if flow.evidence.start_line == 3
    )
    assert call.resolution_kind is resolution
    assert call.confidence is LineageConfidence.CONFIRMED


def test_stage_1c7_iterable_walrus_is_rejected_before_extraction():
    with pytest.raises(SyntaxError):
        compile("[x for x in (y := xs)]", "pkg.py", "exec")


def test_stage_1c7_runtime_target_has_one_assignment_and_unique_ids():
    facts = _stage_1c_facts("result = [x for x in xs if x]\n")
    assignments = [
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.ASSIGNS
        and isinstance(flow.source, ExtractedOccurrenceRef)
        and parse_local_occurrence_id(flow.source.local_id)[0]
        == "runtime_bound_local"
        and parse_local_occurrence_id(flow.source.local_id)[3] == "x"
    ]
    assert len(assignments) == 1
    assert len({anchor.local_id for anchor in facts.anchors}) == len(facts.anchors)
    assert len({flow.local_id for flow in facts.flows}) == len(facts.flows)


def _stage_1d_capture_flows(facts):
    return [flow for flow in facts.flows if flow.relation is LineageRelation.CAPTURES]


def _stage_1d_closure_cells(facts, name):
    return [
        anchor
        for anchor in facts.anchors
        if anchor.kind == "closure_cell"
        and parse_local_occurrence_id(anchor.local_id)[3] == name
    ]


@pytest.mark.parametrize(
    "source",
    (
        "def outer():\n x=1\n def inner(): return x\n x=2\n return inner\n",
        "def outer(flag):\n x=1\n def inner(): return x\n if flag: x=2\n return inner\n",
        "def outer():\n def inner(): return x\n x=1\n return inner\n",
    ),
)
def test_stage_1d1_capture_cell_is_stable_across_late_and_conditional_writes(source):
    facts = _stage_1c_facts(source)
    outer = _stage_1c_named(facts, "function", "outer")[0]
    cells = _stage_1d_closure_cells(facts, "x")
    captures = _stage_1d_capture_flows(facts)
    assert len(cells) == len(captures) == 1
    assert cells[0].owner_local_id == outer.local_id
    capture = captures[0]
    assert capture.source == ExtractedOccurrenceRef(cells[0].local_id)
    assert capture.resolution_kind is ResolutionKind.LEXICAL_EXACT
    assert capture.confidence is LineageConfidence.CONFIRMED
    assert isinstance(capture.target, ExtractedOccurrenceRef)
    assert parse_local_occurrence_id(capture.target.local_id)[:1] == ("name_load",)
    assignment_ids = {
        flow.target.local_id
        for flow in facts.flows
        if flow.relation is LineageRelation.ASSIGNS
        and isinstance(flow.target, ExtractedOccurrenceRef)
    }
    assert capture.source.local_id not in assignment_ids


def test_stage_1d1_class_is_transparent_and_outer_parameter_is_a_cell():
    facts = _stage_1c_facts(
        "def outer(x):\n class C:\n  x=2\n  def method(self): return x\n return C\n"
    )
    outer = _stage_1c_named(facts, "function", "outer")[0]
    cell = _stage_1d_closure_cells(facts, "x")[0]
    capture = _stage_1d_capture_flows(facts)[0]
    assert cell.owner_local_id == outer.local_id
    assert capture.source == ExtractedOccurrenceRef(cell.local_id)


@pytest.mark.parametrize(
    "source",
    (
        "def outer():\n x=1\n def inner():\n  y=x\n  x=2\n  return y\n return inner\n",
        "x=1\ndef outer():\n def inner(): return x\n return inner\n",
        "def outer():\n x=1\n def inner():\n  use(x)\n  del x\n return inner\n",
        "def outer(xs):\n x=1\n return [lambda: x for x in xs]\n",
    ),
)
def test_stage_1d1_local_global_del_and_comprehension_barriers_do_not_capture(source):
    facts = _stage_1c_facts(source)
    assert not _stage_1d_capture_flows(facts)
    assert not [anchor for anchor in facts.anchors if anchor.kind == "closure_cell"]


def test_stage_1d1_lambda_can_skip_comprehension_without_same_name_target():
    facts = _stage_1c_facts(
        "def outer(xs):\n y=1\n return [lambda: y for x in xs]\n"
    )
    outer = _stage_1c_named(facts, "function", "outer")[0]
    cell = _stage_1d_closure_cells(facts, "y")[0]
    capture = _stage_1d_capture_flows(facts)[0]
    assert cell.owner_local_id == outer.local_id
    assert capture.source == ExtractedOccurrenceRef(cell.local_id)


@pytest.mark.parametrize(
    "statement",
    (
        "x: int",
        "x += 1",
        "from pkg import x",
        "for x in (): pass",
        "with make_context() as x: pass",
        "try:\n pass\nexcept Exception as x:\n pass",
        "match 1:\n case x:\n  pass",
    ),
)
def test_stage_1d1_declaration_producers_block_outer_capture(statement):
    facts = _stage_1c_facts(
        "def outer(xs, ctx, value):\n x=1\n def inner():\n  use(x)\n  "
        + statement.replace("\n", "\n  ")
        + "\n return inner\n"
    )
    assert not _stage_1d_capture_flows(facts)


def test_stage_1d2_local_function_assignment_alias_resolves_call_exactly():
    facts = _stage_1c_facts("def f():\n return 1\ng=f\nresult=g()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.symbol_name == "f"


def test_stage_1d2_async_function_assignment_alias_resolves_call_exactly():
    facts = _stage_1c_facts("async def f():\n return 1\ng=f\nresult=g()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.symbol_name == "f"


def test_stage_1d2_nested_function_assignment_alias_resolves_call_exactly():
    facts = _stage_1c_facts(
        "def outer():\n def f(): return 1\n g=f\n return g()\n"
    )
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.symbol_name == "f"


def test_stage_1d2_chained_local_function_alias_resolves_call_exactly():
    facts = _stage_1c_facts("def f():\n return 1\ng=f\nh=g\nresult=h()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.symbol_name == "f"


def test_stage_1d2_lambda_assignment_alias_remains_call_exact():
    facts = _stage_1c_facts("f=lambda:1\ng=f\nresult=g()\n")
    flow = _stage_1c_call_result_flows(facts)[0]
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.symbol_name.startswith("lambda@")


def test_stage_1d2_rebound_alias_loses_local_callable_authority():
    facts = _stage_1c_facts("def f():\n return 1\ng=f\ng=42\nresult=g()\n")
    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d2_divergent_alias_bindings_fail_closed():
    facts = _stage_1c_facts(
        "def f():\n return 1\nif flag:\n g=f\nelse:\n g=lambda:2\nresult=g()\n"
    )
    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d2_branch_ambiguity_does_not_restore_prior_alias():
    facts = _stage_1c_facts(
        "def f():\n return 1\ng=f\nif flag:\n g=42\nresult=g()\n"
    )
    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d2_imported_callable_alias_is_not_newly_resolved():
    facts = _stage_1c_facts("from pkg import f\ng=f\nresult=g()\n")
    assert _stage_1c_call_result_flows(facts)[0].resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d2_factory_return_alias_is_not_newly_resolved():
    facts = _stage_1c_facts(
        "def f():\n return 1\ndef factory():\n return f\ng=factory()\nresult=g()\n"
    )
    flows = _stage_1c_call_result_flows(facts)
    assert flows[-1].resolution_kind is not ResolutionKind.CALL_EXACT


def _stage_1d3_final_call(facts):
    return _stage_1c_call_result_flows(facts)[-1]


def test_stage_1d3_a_factory_returned_local_callable_assigns_exactly():
    facts = _stage_1c_facts(
        "def factory():\n def f(): return 1\n return f\ng=factory()\nresult=g()\n"
    )
    flow = _stage_1d3_final_call(facts)
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"


def test_stage_1d3_b_factory_returned_local_alias_assigns_exactly():
    facts = _stage_1c_facts(
        "def factory():\n def f(): return 1\n g=f\n return g\nh=factory()\nresult=h()\n"
    )
    flow = _stage_1d3_final_call(facts)
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"


def test_stage_1d3_c_factory_returned_lambda_assigns_exactly():
    facts = _stage_1c_facts("def factory():\n return lambda: 1\ng=factory()\nresult=g()\n")
    flow = _stage_1d3_final_call(facts)
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name.startswith("lambda@")


def test_stage_1d3_d_direct_factory_result_invocation_is_exact():
    source = "def factory():\n def f(): return 1\n return f\nresult=factory()()\n"
    tree = ast.parse(source)
    outer_call = tree.body[-1].value
    assert isinstance(outer_call, ast.Call) and isinstance(outer_call.func, ast.Call)
    paths, reason = lineage_extraction_module._index_ast_paths(
        tree,
        lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS,
    )
    assert reason is None
    facts = _stage_1c_facts(source)
    outer_target = ExtractedOccurrenceRef(
        build_local_occurrence_id("call_result", paths[id(outer_call)])
    )
    inner_target = ExtractedOccurrenceRef(
        build_local_occurrence_id("call_result", paths[id(outer_call.func)])
    )
    outer_flow = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.CALL_RESULT and flow.target == outer_target
    )
    inner_flow = next(
        flow
        for flow in facts.flows
        if flow.relation is LineageRelation.CALL_RESULT and flow.target == inner_target
    )
    nested_f = _stage_1c_named(facts, "function", "f")[0]
    assert outer_flow is not inner_flow
    assert outer_flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert outer_flow.confidence is LineageConfidence.CONFIRMED
    assert isinstance(outer_flow.source, ExtractedSymbolicRef)
    assert outer_flow.source.symbol_name == "f"
    assert outer_flow.source.source_local_id == nested_f.local_id


def test_stage_1d3_e_terminal_return_of_proven_call_result_propagates():
    facts = _stage_1c_facts(
        "def factory2():\n def factory1():\n  def f(): return 1\n  return f\n return factory1()\ng=factory2()\nresult=g()\n"
    )
    flow = _stage_1d3_final_call(facts)
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"


def test_stage_1d3_f_terminal_return_after_other_statements_is_exact():
    facts = _stage_1c_facts(
        "def factory():\n marker=1\n def f(): return 1\n return f\ng=factory()\nresult=g()\n"
    )
    assert _stage_1d3_final_call(facts).resolution_kind is ResolutionKind.CALL_EXACT


def test_stage_1d3_g_multiple_explicit_returns_fail_closed():
    facts = _stage_1c_facts(
        "def factory(flag):\n def f(): return 1\n if flag: return f\n return f\ng=factory(True)\nresult=g()\n"
    )
    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d3_h_conditional_only_return_fails_closed():
    facts = _stage_1c_facts(
        "def factory(flag):\n def f(): return 1\n if flag: return f\ng=factory(True)\nresult=g()\n"
    )
    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d3_i_mixed_callable_and_non_callable_returns_fail_closed():
    facts = _stage_1c_facts(
        "def factory(flag):\n def f(): return 1\n if flag: return f\n return 1\ng=factory(True)\nresult=g()\n"
    )
    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d3_j_async_factory_return_does_not_become_callable_value():
    facts = _stage_1c_facts(
        "async def factory():\n def f(): return 1\n return f\ng=factory()\nresult=g()\n"
    )
    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d3_k_generator_factory_return_does_not_become_callable_value():
    facts = _stage_1c_facts(
        "def factory():\n def f(): return 1\n yield 1\n return f\ng=factory()\nresult=g()\n"
    )
    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT


@pytest.mark.parametrize(
    "source",
    (
        "from pkg import factory\ng=factory()\nresult=g()\n",
        "g=obj.factory()\nresult=g()\n",
        "g=[factory][0]()\nresult=g()\n",
        "g=getattr(obj, 'factory')()\nresult=g()\n",
    ),
)
def test_stage_1d3_l_imported_attribute_container_and_reflection_fail_closed(source):
    assert _stage_1d3_final_call(_stage_1c_facts(source)).resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d3_m_module_global_return_lookup_remains_unresolved():
    facts = _stage_1c_facts(
        "def f(): return 1\ndef factory(): return f\ng=factory()\nresult=g()\n"
    )
    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d3_n_closure_cell_callable_value_remains_unresolved():
    facts = _stage_1c_facts(
        "def outer():\n def f(): return 1\n def factory(): return f\n g=factory()\n return g()\n"
    )
    assert _stage_1d3_final_call(facts).resolution_kind is not ResolutionKind.CALL_EXACT


def test_stage_1d3_o_existing_local_callable_alias_remains_exact():
    facts = _stage_1c_facts("def f(): return 1\ng=f\nresult=g()\n")
    assert _stage_1d3_final_call(facts).resolution_kind is ResolutionKind.CALL_EXACT


def test_stage_1d3_lambda_callable_return_summary_propagates_inner_lambda():
    facts = _stage_1c_facts("maker=lambda:(lambda:1)\ng=maker()\nresult=g()\n")
    flow = _stage_1d3_final_call(facts)
    lambdas = _stage_1c_named(facts, "lambda", None)
    inner = max(lambdas, key=lambda item: item.span.start_column)
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef)
    assert flow.source.source_local_id == inner.local_id


def test_stage_1d3_yield_from_marks_only_nested_callable_owner():
    facts = _stage_1c_facts(
        "def factory():\n def f():\n  yield from ()\n return f\ng=factory()\nresult=g()\n"
    )
    flow = _stage_1d3_final_call(facts)
    assert flow.resolution_kind is ResolutionKind.CALL_EXACT
    assert isinstance(flow.source, ExtractedSymbolicRef) and flow.source.symbol_name == "f"


def _stage_1d4_flows(facts, relation):
    return [flow for flow in facts.flows if flow.relation is relation]


def test_stage_1d4_a_callback_path_is_composable_and_call_result_stays_dynamic():
    source = "def apply(callback):\n return callback()\ndef f(): return 1\napply(f)\n"
    tree = ast.parse(source)
    callback_call = tree.body[0].body[0].value
    paths, reason = lineage_extraction_module._index_ast_paths(tree, lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS)
    assert reason is None and isinstance(callback_call, ast.Call)
    facts = _stage_1c_facts(source)
    callback = _stage_1c_named(facts, "parameter", "callback")[0]
    function = _stage_1c_named(facts, "function", "f")[0]
    registers = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
    invokes = _stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)
    assert len(registers) == len(invokes) == 1
    assert registers[0].source == ExtractedOccurrenceRef(function.local_id)
    assert isinstance(registers[0].target, ExtractedSymbolicRef) and registers[0].target.source_local_id == callback.local_id
    assert isinstance(invokes[0].source, ExtractedSymbolicRef) and invokes[0].source.source_local_id == callback.local_id
    assert invokes[0].target == ExtractedOccurrenceRef(build_local_occurrence_id("call_site", paths[id(callback_call)]))
    callback_result = next(flow for flow in _stage_1c_call_result_flows(facts) if flow.evidence.start_line == 2)
    assert callback_result.resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY


def test_stage_1d4_b_keyword_callback_registers_exactly():
    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): pass\napply(callback=f)\n")
    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1


def test_stage_1d4_c_lambda_callback_registers_lambda_anchor():
    facts = _stage_1c_facts("def apply(callback): callback()\napply(lambda: 1)\n")
    flow = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)[0]
    assert flow.source == ExtractedOccurrenceRef(_stage_1c_named(facts, "lambda", None)[0].local_id)


def test_stage_1d4_d_callable_alias_registers_original_anchor():
    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): pass\ng=f\napply(g)\n")
    flow = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)[0]
    assert flow.source == ExtractedOccurrenceRef(_stage_1c_named(facts, "function", "f")[0].local_id)


def test_stage_1d4_e_returned_callable_registers_original_anchor():
    facts = _stage_1c_facts("def apply(callback): callback()\ndef factory():\n def f(): pass\n return f\napply(factory())\n")
    flow = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)[0]
    assert flow.source == ExtractedOccurrenceRef(_stage_1c_named(facts, "function", "f")[0].local_id)


def test_stage_1d4_f_multiple_callers_register_independently_to_one_invocation():
    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): pass\ndef g(): pass\napply(f)\napply(g)\n")
    registers = _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
    assert {flow.source.local_id for flow in registers} == {item.local_id for item in _stage_1c_named(facts, "function", "f") + _stage_1c_named(facts, "function", "g")}
    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)) == 1
    assert next(flow for flow in _stage_1c_call_result_flows(facts) if flow.evidence.start_line == 1).resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY


def test_stage_1d4_g_non_callable_argument_has_only_lexical_invocation():
    facts = _stage_1c_facts("def apply(callback): callback()\napply(42)\n")
    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)
    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)) == 1


@pytest.mark.parametrize("source", ("from pkg import f\ndef apply(callback): callback()\napply(f)\n", "def apply(callback): callback()\napply(obj.f)\n", "def apply(callback): callback()\napply([f][0])\n", "def apply(callback): callback()\napply(getattr(obj, 'f'))\n"))
def test_stage_1d4_h_imported_attribute_reflection_and_container_callbacks_do_not_register(source):
    assert not _stage_1d4_flows(_stage_1c_facts(source), LineageRelation.CALLBACK_REGISTERS)


def test_stage_1d4_i_rebound_parameter_is_not_callback_invocation_or_registration():
    facts = _stage_1c_facts("def apply(callback):\n callback=other\n callback()\ndef f(): pass\napply(f)\n")
    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)
    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)


def test_stage_1d4_j_uninvoked_parameter_does_not_register_callback():
    facts = _stage_1c_facts("def store(callback): return 1\ndef f(): pass\nstore(f)\n")
    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)
    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)


def test_stage_1d4_k_starred_and_double_starred_arguments_do_not_register():
    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): pass\napply(*[f])\napply(**{'callback': f})\n")
    assert not _stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)


def test_stage_1d4_l_async_callback_owner_composes_without_coroutine_specialization():
    facts = _stage_1c_facts("async def apply(callback): callback()\ndef f(): pass\napply(f)\n")
    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1
    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)) == 1


def test_stage_1d4_m_lambda_callback_owner_composes():
    facts = _stage_1c_facts("apply=lambda callback: callback()\ndef f(): pass\napply(f)\n")
    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1
    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)) == 1


def test_stage_1d4_n_callback_arguments_are_not_bound_to_actual_callable_signature():
    facts = _stage_1c_facts("def apply(callback): callback(1)\ndef f(value): pass\napply(f)\n")
    invokes = _stage_1d4_flows(facts, LineageRelation.CALLBACK_INVOKES)
    assert len(invokes) == 1
    assert not [flow for flow in _stage_1d4_flows(facts, LineageRelation.ARGUMENT_TO_PARAMETER) if flow.evidence.start_line == 1]


def test_stage_1d4_o_existing_callable_facts_remain_and_callback_relations_are_additive():
    facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): return 1\ng=f\napply(g)\nresult=g()\n")
    assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1
    assert _stage_1c_call_result_flows(facts)[-1].resolution_kind is ResolutionKind.CALL_EXACT
