from __future__ import annotations

import ast
from collections.abc import Callable

from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence
from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
from contextor.core.analysis.lineage_extraction_surfaces import observe_all_assignment, observe_all_augassign, observe_all_delete
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
        state.declare_local(owner, node.id)
        return
    if isinstance(node.ctx, ast.Del):
        state.declare_local(owner, node.id)
        if owner is not None and state._owner_kind.get(owner) == "module" and node.id == "__all__":
            observe_all_delete(state)
        return
    if isinstance(node.ctx, ast.Load):
        load = occurrence(state, paths, "name_load", node, node.id)
        if node.id in state.blocked_names(owner):
            return
        source = state.frame(owner).get(node.id)
        if source is None:
            if (
                owner is not None
                and state._owner_kind.get(owner)
                in {"function", "async_function", "lambda"}
            ):
                state.request_capture(load, node, owner, node.id)
            return
        callable_info = (
            state._callables_by_anchor.get(source.local_id)
            or state._callables_by_binding.get(source.local_id)
        )
        if callable_info is not None:
            state._callable_values[load.local_id] = callable_info
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
    state.declare_local(owner, target.id)
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
        state.declare_local(owner, target.id)
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
        binding = assign_target(
            state,
            paths,
            target,
            source,
            owner,
            walrus_owner,
            visit=visit,
        )
        if owner is not None and state._owner_kind.get(owner) == "module" and isinstance(target, ast.Name) and target.id == "__all__" and binding is not None:
            observe_all_assignment(state, node, binding)


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
    if owner is not None and state._owner_kind.get(owner) == "module" and isinstance(node.target, ast.Name) and node.target.id == "__all__":
        observe_all_augassign(state)
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
    state.declare_local(owner, node.target.id)
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
        state._declared_locals.get(owner, set()).discard(name)


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
        state._declared_locals.get(owner, set()).discard(name)


def ensure_lexical_cell(
    state: LineageExtractionState,
    paths: dict[int, str],
    owner: str,
    name: str,
) -> ExtractedOccurrenceRef:
    key = (owner, name)
    cached = state._lexical_cells.get(key)
    if cached is not None:
        return cached
    node = state._owner_nodes.get(owner)
    if node is None:
        raise ValueError(f"Missing lineage owner node: {owner}")
    cell = ExtractedOccurrenceRef(
        add_anchor(
            state,
            paths,
            "closure_cell",
            node,
            name,
            owner,
            local_kind="closure_cell",
        )
    )
    state._lexical_cells[key] = cell
    return cell


def finalize_captures(
    state: LineageExtractionState,
    paths: dict[int, str],
) -> None:
    for request in sorted(
        state._capture_requests.values(), key=lambda item: item.load.local_id
    ):
        owner = state.resolve_capture_owner(request.owner, request.name)
        if owner is None:
            continue
        emit_flow(
            state,
            paths,
            source=ensure_lexical_cell(state, paths, owner, request.name),
            target=request.load,
            relation=LineageRelation.CAPTURES,
            node=request.node,
            resolution_kind=ResolutionKind.LEXICAL_EXACT,
            confidence=LineageConfidence.CONFIRMED,
        )
