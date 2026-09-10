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
ValueFn = Callable[[ast.AST, str | None, str | None], ExtractedOccurrenceRef]
PublishWalrusFn = Callable[[str, ExtractedOccurrenceRef, str | None], None]


def visit_name(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.Name,
    owner: str | None,
) -> None:
    if isinstance(node.ctx, ast.Store):
        add_anchor(state, paths, "binding", node, node.id, owner)
        return
    if isinstance(node.ctx, ast.Load):
        load = occurrence(state, paths, "name_load", node, node.id)
        if node.id in state.blocked_names(owner):
            return
        source = state.frame(owner).get(node.id)
        if source is None:
            return
        emit_flow(
            state,
            paths,
            source=source,
            target=load,
            relation=LineageRelation.BINDS,
            node=node,
            resolution_kind=ResolutionKind.LEXICAL_EXACT,
            confidence=LineageConfidence.CONFIRMED,
        )


def assign_target(
    state: LineageExtractionState,
    paths: dict[int, str],
    target: ast.AST,
    source: ExtractedOccurrenceRef,
    owner: str | None,
    walrus_owner: str | None,
    *,
    visit: VisitFn,
) -> ExtractedOccurrenceRef | None:
    if not isinstance(target, ast.Name):
        visit(target, owner, walrus_owner)
        return None
    binding = ExtractedOccurrenceRef(
        add_anchor(state, paths, "binding", target, target.id, owner)
    )
    if target.id in state.blocked_names(owner):
        return None
    state.frame(owner)[target.id] = binding
    callable_info = state._callable_values.get(source.local_id)
    if callable_info is not None:
        state._callables_by_binding[binding.local_id] = callable_info
    emit_flow(
        state,
        paths,
        source=source,
        target=binding,
        relation=LineageRelation.ASSIGNS,
        node=target,
        resolution_kind=ResolutionKind.LEXICAL_EXACT,
        confidence=LineageConfidence.CONFIRMED,
    )
    return binding


def runtime_bind_target(
    state: LineageExtractionState,
    paths: dict[int, str],
    target: ast.AST,
    owner: str | None,
    walrus_owner: str | None,
    *,
    visit: VisitFn,
) -> None:
    if isinstance(target, ast.Name):
        binding = ExtractedOccurrenceRef(
            add_anchor(state, paths, "binding", target, target.id, owner)
        )
        if target.id in state.blocked_names(owner):
            return
        source = occurrence(
            state,
            paths,
            "runtime_bound_local",
            target,
            target.id,
        )
        state.frame(owner)[target.id] = binding
        emit_flow(
            state,
            paths,
            source=source,
            target=binding,
            relation=LineageRelation.ASSIGNS,
            node=target,
            resolution_kind=ResolutionKind.LEXICAL_EXACT,
            confidence=LineageConfidence.CONFIRMED,
        )
        return
    if isinstance(target, (ast.Tuple, ast.List)):
        for item in target.elts:
            runtime_bind_target(
                state,
                paths,
                item,
                owner,
                walrus_owner,
                visit=visit,
            )
        return
    if isinstance(target, ast.Starred):
        runtime_bind_target(
            state,
            paths,
            target.value,
            owner,
            walrus_owner,
            visit=visit,
        )
        return
    visit(target, owner, walrus_owner)


def visit_assign(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.Assign,
    owner: str | None,
    walrus_owner: str | None,
    *,
    value: ValueFn,
    visit: VisitFn,
) -> None:
    source = value(node.value, owner, walrus_owner)
    for target in node.targets:
        assign_target(
            state,
            paths,
            target,
            source,
            owner,
            walrus_owner,
            visit=visit,
        )


def visit_ann_assign(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.AnnAssign,
    owner: str | None,
    walrus_owner: str | None,
    *,
    value: ValueFn,
    visit: VisitFn,
) -> None:
    if node.value is None:
        visit(node.target, owner, walrus_owner)
        visit(node.annotation, owner, walrus_owner)
        return
    source = value(node.value, owner, walrus_owner)
    assign_target(
        state,
        paths,
        node.target,
        source,
        owner,
        walrus_owner,
        visit=visit,
    )
    visit(node.annotation, owner, walrus_owner)


def visit_named_expr(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.NamedExpr,
    owner: str | None,
    walrus_owner: str | None,
    *,
    value: ValueFn,
    visit: VisitFn,
    publish_walrus: PublishWalrusFn,
) -> None:
    target_owner = walrus_owner or owner
    source = value(node.value, owner, walrus_owner)
    binding = assign_target(
        state,
        paths,
        node.target,
        source,
        target_owner,
        walrus_owner,
        visit=visit,
    )
    if binding is not None and isinstance(node.target, ast.Name):
        publish_walrus(
            node.target.id,
            binding,
            target_owner,
        )


def visit_aug_assign(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.AugAssign,
    owner: str | None,
    walrus_owner: str | None,
    *,
    value: ValueFn,
    visit: VisitFn,
) -> None:
    if not isinstance(node.target, ast.Name):
        visit(node.target, owner, walrus_owner)
        value(node.value, owner, walrus_owner)
        return
    blocked = node.target.id in state.blocked_names(owner)
    prior = None if blocked else state.frame(owner).get(node.target.id)
    if prior is not None:
        prior_load = occurrence(
            state,
            paths,
            "name_load",
            node.target,
            node.target.id,
        )
        emit_flow(
            state,
            paths,
            source=prior,
            target=prior_load,
            relation=LineageRelation.BINDS,
            node=node.target,
            resolution_kind=ResolutionKind.LEXICAL_EXACT,
            confidence=LineageConfidence.CONFIRMED,
        )
    value(node.value, owner, walrus_owner)
    binding = ExtractedOccurrenceRef(
        add_anchor(
            state,
            paths,
            "binding",
            node.target,
            node.target.id,
            owner,
        )
    )
    if blocked or prior is None:
        return
    state.frame(owner)[node.target.id] = binding


def visit_global(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.Global,
    owner: str | None,
) -> None:
    for ordinal, name in enumerate(node.names):
        add_anchor(
            state,
            paths,
            "global_declaration",
            node,
            name,
            owner,
            ordinal=ordinal,
        )
        state.blocked_names(owner).add(name)
        state.frame(owner).pop(name, None)


def visit_nonlocal(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.Nonlocal,
    owner: str | None,
) -> None:
    for ordinal, name in enumerate(node.names):
        add_anchor(
            state,
            paths,
            "nonlocal_declaration",
            node,
            name,
            owner,
            ordinal=ordinal,
        )
        state.blocked_names(owner).add(name)
        state.frame(owner).pop(name, None)
