from __future__ import annotations

import ast
from collections.abc import Callable

from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence
from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
from contextor.core.domain.lineage_facts import (
    ExtractedOccurrenceRef,
    LineageConfidence,
    LineageRelation,
    ResolutionKind,
)

VisitFn = Callable[[ast.AST, str | None, str | None], None]
RuntimeBindTargetFn = Callable[[ast.AST, str | None, str | None], None]


def visit_block_from_frame(state: LineageExtractionState, body: list[ast.stmt], owner: str | None, walrus_owner: str | None, frame: dict[str, ExtractedOccurrenceRef], *, visit: VisitFn) -> dict[str, ExtractedOccurrenceRef]:
    state.replace_frame(owner, frame)
    for child in body:
        visit(child, owner, walrus_owner)
    return state.clone_frame(owner)


def visit_if(state: LineageExtractionState, node: ast.If, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
    visit(node.test, owner, walrus_owner)
    entry_frame = state.clone_frame(owner)
    body_frame = visit_block_from_frame(state, node.body, owner, walrus_owner, entry_frame, visit=visit)
    if node.orelse:
        else_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, entry_frame, visit=visit)
    else:
        else_frame = dict(entry_frame)
    state.replace_frame(owner, state.merge_frames((body_frame, else_frame)))


def visit_for(state: LineageExtractionState, node: ast.For, owner: str | None, walrus_owner: str | None, *, visit: VisitFn, runtime_bind_target: RuntimeBindTargetFn) -> None:
    visit(node.iter, owner, walrus_owner)
    entry_frame = state.clone_frame(owner)
    state.replace_frame(owner, entry_frame)
    runtime_bind_target(node.target, owner, walrus_owner)
    for child in node.body:
        visit(child, owner, walrus_owner)
    body_frame = state.clone_frame(owner)
    loop_exit_frame = state.merge_frames((entry_frame, body_frame))
    state.replace_frame(owner, loop_exit_frame)
    if not node.orelse:
        return
    else_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, loop_exit_frame, visit=visit)
    state.replace_frame(owner, state.merge_frames((loop_exit_frame, else_frame)))


def visit_async_for(state: LineageExtractionState, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None, *, visit: VisitFn, runtime_bind_target: RuntimeBindTargetFn) -> None:
    visit(node.iter, owner, walrus_owner)
    entry_frame = state.clone_frame(owner)
    state.replace_frame(owner, entry_frame)
    runtime_bind_target(node.target, owner, walrus_owner)
    for child in node.body:
        visit(child, owner, walrus_owner)
    body_frame = state.clone_frame(owner)
    loop_exit_frame = state.merge_frames((entry_frame, body_frame))
    state.replace_frame(owner, loop_exit_frame)
    if not node.orelse:
        return
    else_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, loop_exit_frame, visit=visit)
    state.replace_frame(owner, state.merge_frames((loop_exit_frame, else_frame)))


def visit_while(state: LineageExtractionState, node: ast.While, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
    visit(node.test, owner, walrus_owner)
    entry_frame = state.clone_frame(owner)
    body_frame = visit_block_from_frame(state, node.body, owner, walrus_owner, entry_frame, visit=visit)
    loop_exit_frame = state.merge_frames((entry_frame, body_frame))
    state.replace_frame(owner, loop_exit_frame)
    if not node.orelse:
        return
    else_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, loop_exit_frame, visit=visit)
    state.replace_frame(owner, state.merge_frames((loop_exit_frame, else_frame)))


def visit_with(state: LineageExtractionState, node: ast.With, owner: str | None, walrus_owner: str | None, *, visit: VisitFn, runtime_bind_target: RuntimeBindTargetFn) -> None:
    for item in node.items:
        visit(item.context_expr, owner, walrus_owner)
        if item.optional_vars is not None:
            runtime_bind_target(item.optional_vars, owner, walrus_owner)
    for child in node.body:
        visit(child, owner, walrus_owner)


def visit_async_with(state: LineageExtractionState, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None, *, visit: VisitFn, runtime_bind_target: RuntimeBindTargetFn) -> None:
    for item in node.items:
        visit(item.context_expr, owner, walrus_owner)
        if item.optional_vars is not None:
            runtime_bind_target(item.optional_vars, owner, walrus_owner)
    for child in node.body:
        visit(child, owner, walrus_owner)


def visit_try(state: LineageExtractionState, node: ast.Try, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
    entry_frame = state.clone_frame(owner)
    normal_frame = visit_block_from_frame(state, node.body, owner, walrus_owner, entry_frame, visit=visit)
    if node.orelse:
        normal_frame = visit_block_from_frame(state, node.orelse, owner, walrus_owner, normal_frame, visit=visit)
    reachable_frames = [normal_frame]
    for handler in node.handlers:
        state.replace_frame(owner, entry_frame)
        visit(handler, owner, walrus_owner)
        reachable_frames.append(state.clone_frame(owner))
    state.replace_frame(owner, state.merge_frames(tuple(reachable_frames)))
    for child in node.finalbody:
        visit(child, owner, walrus_owner)


def visit_except_handler(state: LineageExtractionState, paths: dict[int, str], node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
    if node.type is not None:
        visit(node.type, owner, walrus_owner)
    alias_name = node.name if isinstance(node.name, str) else None
    if alias_name is not None:
        binding = ExtractedOccurrenceRef(add_anchor(state, paths, "binding", node, alias_name, owner))
        state.declare_local(owner, alias_name)
        if alias_name not in state.blocked_names(owner):
            source = occurrence(state, paths, "runtime_bound_local", node, alias_name)
            state.frame(owner)[alias_name] = binding
            state.note_module_all_touch(owner, alias_name)
            emit_flow(
                state,
                paths,
                source=source,
                target=binding,
                relation=LineageRelation.ASSIGNS,
                node=node,
                resolution_kind=ResolutionKind.LEXICAL_EXACT,
                confidence=LineageConfidence.CONFIRMED,
                owner_local_id=owner,
            )
    for child in node.body:
        visit(child, owner, walrus_owner)
    exit_frame = state.clone_frame(owner)
    if alias_name is not None:
        exit_frame.pop(alias_name, None)
    state.replace_frame(owner, exit_frame)


def visit_match(state: LineageExtractionState, node: ast.Match, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
    visit(node.subject, owner, walrus_owner)
    entry_frame = state.clone_frame(owner)
    reachable_frames = [dict(entry_frame)]
    for case in node.cases:
        state.replace_frame(owner, entry_frame)
        visit(case.pattern, owner, walrus_owner)
        if case.guard is not None:
            visit(case.guard, owner, walrus_owner)
        for child in case.body:
            visit(child, owner, walrus_owner)
        reachable_frames.append(state.clone_frame(owner))
    state.replace_frame(owner, state.merge_frames(tuple(reachable_frames)))


def visit_match_as(state: LineageExtractionState, paths: dict[int, str], node: ast.MatchAs, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
    if node.pattern is not None:
        visit(node.pattern, owner, walrus_owner)
    if node.name is not None:
        add_anchor(state, paths, "binding", node, node.name, owner)
        state.declare_local(owner, node.name)
        state.note_module_all_touch(owner, node.name)


def visit_match_star(state: LineageExtractionState, paths: dict[int, str], node: ast.MatchStar, owner: str | None) -> None:
    if node.name is not None:
        add_anchor(state, paths, "binding", node, node.name, owner)
        state.declare_local(owner, node.name)
        state.note_module_all_touch(owner, node.name)


def visit_match_mapping(state: LineageExtractionState, paths: dict[int, str], node: ast.MatchMapping, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
    for key in node.keys:
        visit(key, owner, walrus_owner)
    for pattern in node.patterns:
        visit(pattern, owner, walrus_owner)
    if node.rest is not None:
        add_anchor(state, paths, "binding", node, node.rest, owner)
        state.declare_local(owner, node.rest)
        state.note_module_all_touch(owner, node.rest)
