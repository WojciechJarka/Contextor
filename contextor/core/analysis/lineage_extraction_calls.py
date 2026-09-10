from __future__ import annotations

import ast
from collections.abc import Callable

from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence, parameter_symbolic
from contextor.core.analysis.lineage_extraction_state import _CallArgumentInfo, _CallableInfo, _ImportInfo, _ParameterInfo, LineageExtractionState
from contextor.core.domain.lineage_facts import ExtractedOccurrenceRef, ExtractedSymbolicKind, ExtractedSymbolicRef, LineageConfidence, LineageRelation, ParameterKind, ResolutionKind

VisitFn = Callable[[ast.AST, str | None, str | None], None]
ValueFn = Callable[[ast.AST, str | None, str | None], ExtractedOccurrenceRef]

def register_import_binding(state: LineageExtractionState, paths: dict[int, str], alias: ast.alias, owner: str | None, local_name: str, module_name: str | None, symbol_name: str | None) -> None:
    binding_id = add_anchor(state, paths,"import_binding", alias, local_name, owner)
    state.declare_local(owner, local_name)
    if local_name in state.blocked_names(owner): return
    state.frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
    if module_name is not None: state.import_frame(owner)[local_name] = _ImportInfo(module_name, symbol_name, binding_id)


def resolve_current_local_callable(state: LineageExtractionState, node: ast.Call, owner: str | None) -> _CallableInfo | None:
    if not isinstance(node.func, ast.Name): return None
    current = state.frame(owner).get(node.func.id)
    if current is None: return None
    return state._callables_by_anchor.get(current.local_id) or state._callables_by_binding.get(current.local_id)


def current_import_info(state: LineageExtractionState, owner: str | None, local_name: str) -> _ImportInfo | None:
    current, info = state.frame(owner).get(local_name), state.import_frame(owner).get(local_name)
    return info if current is not None and info is not None and current.local_id == info.binding_id else None


def resolve_current_imported_callable(state: LineageExtractionState, node: ast.Call, owner: str | None) -> ExtractedSymbolicRef | None:
    if isinstance(node.func, ast.Name):
        info = current_import_info(state,owner, node.func.id)
        if info is None or info.symbol_name is None: return None
        return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, info.module_name, info.symbol_name, info.binding_id)
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        info = current_import_info(state,owner, node.func.value.id)
        if info is None or info.symbol_name is not None: return None
        return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, info.module_name, node.func.attr, info.binding_id)
    return None


def collect_call_arguments(state: LineageExtractionState, paths: dict[int, str], node: ast.Call, owner: str | None, walrus_owner: str | None, *, value: ValueFn) -> tuple[_CallArgumentInfo, ...]:
    pending = [(arg, "starred" if isinstance(arg, ast.Starred) else "positional", None, index) for index, arg in enumerate(node.args)]
    pending += [(keyword.value, "double_starred" if keyword.arg is None else "keyword", keyword.arg, len(node.args) + index) for index, keyword in enumerate(node.keywords)]
    pending.sort(key=lambda item: (int(getattr(item[0], "lineno", 0) or 0), int(getattr(item[0], "col_offset", 0) or 0), item[3]))
    result = []
    for ordinal, (argument_node, kind, keyword_name, _source_ordinal) in enumerate(pending):
        source = value(argument_node, owner, walrus_owner)
        result.append(_CallArgumentInfo(occurrence(state, paths,"call_argument", argument_node, keyword_name if kind == "keyword" else None, ordinal=ordinal), source, argument_node, kind, keyword_name))
    return tuple(result)


def emit_argument_to_parameter(state: LineageExtractionState, paths: dict[int, str], module_name: str, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo) -> None:
    emit_flow(state, paths,source=argument.occurrence, target=parameter_symbolic(module_name,callable_info.name, parameter), relation=LineageRelation.ARGUMENT_TO_PARAMETER, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
    actual_callable = state._callable_values.get(argument.source.local_id)
    if parameter.local_id in state._callback_parameters and actual_callable is not None:
        emit_flow(state, paths,source=ExtractedOccurrenceRef(actual_callable.anchor_id), target=parameter_symbolic(module_name,callable_info.name, parameter), relation=LineageRelation.CALLBACK_REGISTERS, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)


def bind_call_arguments(state: LineageExtractionState, paths: dict[int, str], module_name: str, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo) -> None:
    fixed = tuple(p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
    keywords = {p.name: p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_OR_KEYWORD, ParameterKind.KEYWORD_ONLY)}
    vararg = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_POSITIONAL), None)
    varkw = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_KEYWORD), None)
    consumed, index, uncertain = set(), 0, False
    for argument in arguments:
        if argument.kind == "starred": uncertain = True; continue
        if argument.kind == "double_starred": continue
        if argument.kind == "positional":
            if uncertain: continue
            if index < len(fixed):
                parameter = fixed[index]; index += 1; consumed.add(parameter.local_id); emit_argument_to_parameter(state, paths, module_name,argument, callable_info, parameter)
            elif vararg is not None: emit_argument_to_parameter(state, paths, module_name,argument, callable_info, vararg)
            continue
        if argument.kind == "keyword" and argument.keyword_name is not None:
            parameter = keywords.get(argument.keyword_name)
            if parameter is not None and parameter.local_id not in consumed:
                consumed.add(parameter.local_id); emit_argument_to_parameter(state, paths, module_name,argument, callable_info, parameter)
            elif parameter is None and varkw is not None: emit_argument_to_parameter(state, paths, module_name,argument, callable_info, varkw)

def function_signature_evidence(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
    args = node.args
    for default in args.defaults:
        visit(default, owner, walrus_owner)
    for default in args.kw_defaults:
        if default is not None:
            visit(default, owner, walrus_owner)
    all_args = list(getattr(args, "posonlyargs", ())) + list(args.args) + list(args.kwonlyargs)
    if args.vararg is not None:
        all_args.append(args.vararg)
    if args.kwarg is not None:
        all_args.append(args.kwarg)
    for arg in all_args:
        if arg.annotation is not None:
            visit(arg.annotation, owner, walrus_owner)
    returns = getattr(node, "returns", None)
    if returns is not None:
        visit(returns, owner, walrus_owner)


def parameter_anchors(state: LineageExtractionState, paths: dict[int, str], module_name: str, args: ast.arguments, owner: str, callable_symbol_name: str) -> tuple[_ParameterInfo, ...]:
    result = []
    groups = ((getattr(args, "posonlyargs", ()), ParameterKind.POSITIONAL_ONLY, "parameter_posonly"), (args.args, ParameterKind.POSITIONAL_OR_KEYWORD, "parameter_poskw"), ((args.vararg,) if args.vararg else (), ParameterKind.VAR_POSITIONAL, "parameter_vararg"), (args.kwonlyargs, ParameterKind.KEYWORD_ONLY, "parameter_kwonly"), ((args.kwarg,) if args.kwarg else (), ParameterKind.VAR_KEYWORD, "parameter_varkw"))
    for group, kind, local_kind in groups:
        for ordinal, parameter in enumerate(group):
            local_id = add_anchor(state, paths,"parameter", parameter, parameter.arg, owner, ordinal=ordinal if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD) else 0, local_kind=local_kind)
            state.declare_local(owner, parameter.arg)
            info = _ParameterInfo(local_id, parameter.arg, kind, ordinal if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD) else 0)
            state.register_parameter(owner, info)
            result.append((info, parameter))
    for ordinal, (info, parameter) in enumerate(result):
        emit_flow(state, paths,source=parameter_symbolic(module_name,callable_symbol_name, info), target=ExtractedOccurrenceRef(info.local_id), relation=LineageRelation.BINDS, node=parameter, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
    return tuple(info for info, _parameter in result)


def default_flows(state: LineageExtractionState, paths: dict[int, str], module_name: str, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...]) -> None:
    positional_parameters = tuple(parameter for parameter in parameters if parameter.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
    positional_defaults = tuple(node.args.defaults)
    if positional_defaults:
        for ordinal, (default, parameter) in enumerate(zip(positional_defaults, positional_parameters[-len(positional_defaults) :])):
            emit_flow(state, paths,source=occurrence(state, paths,"expression_result", default), target=parameter_symbolic(module_name,callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
    kwonly_parameters = tuple(parameter for parameter in parameters if parameter.kind is ParameterKind.KEYWORD_ONLY)
    for ordinal, (default, parameter) in enumerate(zip(node.args.kw_defaults, kwonly_parameters)):
        if default is not None:
            emit_flow(state, paths,source=occurrence(state, paths,"expression_result", default), target=parameter_symbolic(module_name,callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
