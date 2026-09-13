from __future__ import annotations

import ast
from collections.abc import Callable

from contextor.core.analysis.lineage_extraction_calls import (
    bind_call_arguments,
    collect_call_arguments,
    default_flows,
    function_signature_evidence,
    parameter_anchors,
    register_import_binding,
    resolve_current_imported_callable,
    resolve_current_local_callable,
)
from contextor.core.analysis.lineage_extraction_contracts import _resolve_import_module
from contextor.core.analysis.lineage_extraction_emit import (
    add_anchor,
    emit_flow,
    occurrence,
    parameter_symbolic,
    return_symbolic,
)
from contextor.core.analysis.lineage_extraction_state import (
    _CallableInfo,
    LineageExtractionState,
)
from contextor.core.analysis.lineage_extraction_surfaces import observe_all_mutation, record_direct_public_candidates
from contextor.core.domain.lineage_facts import (
    ExtractedOccurrenceRef,
    LineageConfidence,
    LineageRelation,
    ParameterKind,
    ResolutionKind,
)

VisitFn = Callable[[ast.AST, str | None, str | None], None]
ValueFn = Callable[[ast.AST, str | None, str | None], ExtractedOccurrenceRef]


def visit_module(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.Module,
    *,
    visit: VisitFn,
) -> None:
    module_id = add_anchor(
        state,
        paths,
        "module",
        node,
        None,
        None,
    )
    state.register_owner(module_id, None, "module", node)
    state.frame(module_id)
    for child in node.body:
        state.begin_module_statement(child)
        try:
            visit(child, module_id, None)
            record_direct_public_candidates(state, child, module_id)
        finally:
            state.end_module_statement()


def visit_class_def(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.ClassDef,
    owner: str | None,
    walrus_owner: str | None,
    *,
    visit: VisitFn,
) -> None:
    class_id = add_anchor(
        state,
        paths,
        "class",
        node,
        node.name,
        owner,
    )
    state.declare_local(owner, node.name)
    state.register_owner(class_id, owner, "class", node)
    for child in (*node.decorator_list, *node.bases, *node.keywords):
        visit(child, owner, walrus_owner)
    state.frame(class_id)
    for child in node.body:
        visit(child, class_id, None)
    if node.name not in state.blocked_names(owner):
        state.frame(owner)[node.name] = ExtractedOccurrenceRef(class_id)
        state.note_module_all_touch(owner, node.name)


def visit_function(
    state: LineageExtractionState,
    paths: dict[int, str],
    module_name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    kind: str,
    owner: str | None,
    walrus_owner: str | None,
    *,
    visit: VisitFn,
) -> None:
    function_id = add_anchor(
        state,
        paths,
        kind,
        node,
        node.name,
        owner,
    )
    state.declare_local(owner, node.name)
    state.register_owner(function_id, owner, kind, node)
    for decorator in node.decorator_list:
        visit(decorator, owner, walrus_owner)
    function_signature_evidence(
        node,
        owner,
        walrus_owner,
        visit=visit,
    )
    parameters = parameter_anchors(
        state,
        paths,
        module_name,
        node.args,
        function_id,
        node.name,
    )
    default_flows(
        state,
        paths,
        module_name,
        node,
        node.name,
        parameters,
        owner_local_id=owner,
    )
    callable_info = _CallableInfo(
        node.name,
        function_id,
        parameters,
    )
    state.callable_frame(owner)[node.name] = callable_info
    state._callables_by_anchor[function_id] = callable_info
    function_frame = state.frame(function_id)
    for parameter in parameters:
        function_frame[parameter.name] = ExtractedOccurrenceRef(
            parameter.local_id
        )
    for child in node.body:
        visit(child, function_id, None)
    state.finalize_function_callable_return(function_id, node)
    if node.name not in state.blocked_names(owner):
        state.frame(owner)[node.name] = ExtractedOccurrenceRef(
            function_id
        )
        state.note_module_all_touch(owner, node.name)


def visit_lambda(
    state: LineageExtractionState,
    paths: dict[int, str],
    module_name: str,
    node: ast.Lambda,
    owner: str | None,
    walrus_owner: str | None,
    *,
    visit: VisitFn,
    value: ValueFn,
) -> None:
    lambda_id = add_anchor(
        state,
        paths,
        "lambda",
        node,
        None,
        owner,
    )
    state.register_owner(lambda_id, owner, "lambda", node)
    function_signature_evidence(
        node,
        owner,
        walrus_owner,
        visit=visit,
    )
    callable_symbol_name = f"lambda@{paths[id(node)]}"
    parameters = parameter_anchors(
        state,
        paths,
        module_name,
        node.args,
        lambda_id,
        callable_symbol_name,
    )
    default_flows(
        state,
        paths,
        module_name,
        node,
        callable_symbol_name,
        parameters,
        owner_local_id=owner,
    )
    callable_info = _CallableInfo(
        callable_symbol_name,
        lambda_id,
        parameters,
    )
    state._callables_by_anchor[lambda_id] = callable_info
    lambda_frame = state.frame(lambda_id)
    for parameter in parameters:
        lambda_frame[parameter.name] = ExtractedOccurrenceRef(
            parameter.local_id
        )
    body_source = value(node.body, lambda_id, None)
    emit_flow(
        state,
        paths,
        source=body_source,
        target=return_symbolic(module_name, callable_info),
        relation=LineageRelation.RETURNS,
        node=node.body,
        resolution_kind=ResolutionKind.LEXICAL_EXACT,
        confidence=LineageConfidence.CONFIRMED,
        owner_local_id=lambda_id,
    )
    state.publish_lambda_callable_return(lambda_id, body_source)
    lambda_value = occurrence(
        state,
        paths,
        "expression_result",
        node,
    )
    state._callable_values[lambda_value.local_id] = callable_info


def visit_return(
    state: LineageExtractionState,
    paths: dict[int, str],
    module_name: str,
    node: ast.Return,
    owner: str | None,
    walrus_owner: str | None,
    *,
    value: ValueFn,
) -> None:
    source = value(node.value, owner, walrus_owner) if node.value is not None else None
    returned_callable = (
        state._callable_values.get(source.local_id)
        if source is not None
        else None
    )
    callable_info = (
        state._callables_by_anchor.get(owner)
        if owner is not None
        else None
    )
    if callable_info is not None and source is not None:
        emit_flow(
            state,
            paths,
            source=source,
            target=return_symbolic(module_name, callable_info),
            relation=LineageRelation.RETURNS,
            node=node,
            resolution_kind=ResolutionKind.LEXICAL_EXACT,
            confidence=LineageConfidence.CONFIRMED,
            owner_local_id=owner,
        )
    state.record_callable_return(owner, node, returned_callable)


def visit_yield(
    state: LineageExtractionState,
    node: ast.Yield | ast.YieldFrom,
    owner: str | None,
    walrus_owner: str | None,
    *,
    visit: VisitFn,
) -> None:
    state.mark_generator(owner)
    if node.value is not None:
        visit(node.value, owner, walrus_owner)


def visit_call(
    state: LineageExtractionState,
    paths: dict[int, str],
    module_name: str,
    node: ast.Call,
    owner: str | None,
    walrus_owner: str | None,
    *,
    visit: VisitFn,
    value: ValueFn,
) -> None:
    if owner is not None and state._owner_kind.get(owner) == "module":
        observe_all_mutation(state, node)
    visit(node.func, owner, walrus_owner)
    callable_info = resolve_current_local_callable(
        state,
        node,
        owner,
    )
    imported_return = resolve_current_imported_callable(
        state,
        node,
        owner,
    )
    if callable_info is None and isinstance(node.func, ast.Call):
        inner_call_result = occurrence(
            state,
            paths,
            "call_result",
            node.func,
        )
        callable_info = state._callable_values.get(inner_call_result.local_id)
    callee_ref = (
        state.frame(owner).get(node.func.id)
        if isinstance(node.func, ast.Name)
        else None
    )
    call_site = occurrence(
        state,
        paths,
        "call_site",
        node,
    )
    call_result = occurrence(
        state,
        paths,
        "call_result",
        node,
    )
    parameter = state.current_parameter(owner, callee_ref)
    enclosing_callable = state._callables_by_anchor.get(owner) if owner is not None else None
    if (
        isinstance(node.func, ast.Name)
        and parameter is not None
        and enclosing_callable is not None
        and parameter.kind not in (ParameterKind.VAR_POSITIONAL, ParameterKind.VAR_KEYWORD)
    ):
        state.mark_callback_parameter(parameter)
        emit_flow(
            state,
            paths,
            source=parameter_symbolic(module_name, enclosing_callable.name, parameter),
            target=call_site,
            relation=LineageRelation.CALLBACK_INVOKES,
            node=node,
            resolution_kind=ResolutionKind.LEXICAL_EXACT,
            confidence=LineageConfidence.CONFIRMED,
            owner_local_id=owner,
        )
    arguments = collect_call_arguments(
        state,
        paths,
        node,
        owner,
        walrus_owner,
        value=value,
    )
    if callable_info is not None:
        bind_call_arguments(
            state,
            paths,
            module_name,
            arguments,
            callable_info,
            owner_local_id=owner,
        )
        emit_flow(
            state,
            paths,
            source=return_symbolic(module_name, callable_info),
            target=call_result,
            relation=LineageRelation.CALL_RESULT,
            node=node,
            resolution_kind=ResolutionKind.CALL_EXACT,
            confidence=LineageConfidence.CONFIRMED,
            owner_local_id=owner,
        )
        returned_callable = state._callable_returns.get(callable_info.anchor_id)
        if returned_callable is not None:
            state._callable_values[call_result.local_id] = returned_callable
        return
    if imported_return is not None:
        emit_flow(
            state,
            paths,
            source=imported_return,
            target=call_result,
            relation=LineageRelation.CALL_RESULT,
            node=node,
            resolution_kind=ResolutionKind.IMPORT_EXACT,
            confidence=LineageConfidence.CONFIRMED,
            owner_local_id=owner,
        )
        return
    if isinstance(node.func, ast.Name) and callee_ref is None:
        resolution_kind = ResolutionKind.UNRESOLVED_NAME
        confidence = LineageConfidence.UNRESOLVED
        dynamic_boundary = None
    else:
        resolution_kind = ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
        confidence = LineageConfidence.DYNAMIC
        dynamic_boundary = "dynamic_call"
    emit_flow(
        state,
        paths,
        source=call_site,
        target=call_result,
        relation=LineageRelation.CALL_RESULT,
        node=node,
        resolution_kind=resolution_kind,
        confidence=confidence,
        dynamic_boundary=dynamic_boundary,
        owner_local_id=owner,
    )


def visit_import(
    state: LineageExtractionState,
    paths: dict[int, str],
    node: ast.Import,
    owner: str | None,
) -> None:
    for alias in node.names:
        local_name = alias.asname or alias.name.split(".", 1)[0]
        register_import_binding(
            state,
            paths,
            alias,
            owner,
            local_name,
            (
                alias.name
                if alias.asname is not None
                else alias.name.split(".", 1)[0]
            ),
            None,
        )


def visit_import_from(
    state: LineageExtractionState,
    paths: dict[int, str],
    source_key: str,
    node: ast.ImportFrom,
    owner: str | None,
) -> None:
    module_name = _resolve_import_module(
        source_key,
        node.module,
        node.level,
    )
    for alias in node.names:
        if alias.name == "*":
            state.replace_frame(owner, {})
            continue
        local_name = alias.asname or alias.name
        register_import_binding(
            state,
            paths,
            alias,
            owner,
            local_name,
            module_name,
            alias.name,
        )
