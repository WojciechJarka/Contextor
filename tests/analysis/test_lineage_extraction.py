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
from contextor.core.domain.lineage_facts import (
    ExtractedOccurrenceRef,
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
    extractor = lineage_extraction_module._AnchorExtractor(paths, "pkg.py")
    node = tree.body[0].value
    first = extractor._occurrence("expression_result", node)
    second = extractor._occurrence("expression_result", node)
    assert first is second
    assert first.local_id == second.local_id
    assert len(extractor._ids) == 1


def test_stage_1c_merge_frames_keeps_only_identical_occurrences():
    tree = ast.parse("a = 1\nb = 2\nc = 3\n")
    paths, reason = lineage_extraction_module._index_ast_paths(
        tree,
        lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS,
    )
    assert reason is None
    extractor = lineage_extraction_module._AnchorExtractor(paths, "pkg.py")
    a = ExtractedOccurrenceRef("a")
    b1 = ExtractedOccurrenceRef("b1")
    b2 = ExtractedOccurrenceRef("b2")
    merged = extractor._merge_frames(
        (
            {"a": a, "b": b1},
            {"a": a, "b": b2},
        )
    )
    assert merged == {"a": a}


def _stage_1c_facts(source: str):
    return extract_lineage_source_facts(ast.parse(source), source_key="pkg.py", source_fingerprint=FINGERPRINT)


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
