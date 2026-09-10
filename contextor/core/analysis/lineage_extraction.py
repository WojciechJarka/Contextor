from __future__ import annotations

import ast
from dataclasses import dataclass

from contextor.core.analysis.state_manager import canonical_python_source_path
from contextor.core.analysis.lineage_extraction_contracts import (
    DEFAULT_LINEAGE_EXTRACTION_LIMITS,
    ExtractedLineageContribution,
    ExtractedLineageProvider,
    LineageExtractionLimits,
    ParsedLineageSourceInput,
    _FINGERPRINT_RE,
    _index_ast_paths,
    _module_name_from_source_key,
    _resolve_import_module,
    _source_span,
    build_local_occurrence_id,
    parse_local_occurrence_id,
)
from contextor.core.analysis.lineage_extraction_calls import bind_call_arguments, collect_call_arguments, current_import_info, default_flows, emit_argument_to_parameter, function_signature_evidence, parameter_anchors, register_import_binding, resolve_current_imported_callable, resolve_current_local_callable
from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence, parameter_symbolic, return_symbolic
from contextor.core.analysis.lineage_extraction_comprehensions import (
    begin_comprehension,
    finish_comprehension,
    publish_executed_walrus,
    visit_comprehension_expression,
)
from contextor.core.analysis.lineage_extraction_control import (
    visit_async_for,
    visit_async_with,
    visit_block_from_frame,
    visit_except_handler,
    visit_for,
    visit_if,
    visit_match,
    visit_match_as,
    visit_match_mapping,
    visit_match_star,
    visit_try,
    visit_while,
    visit_with,
)
from contextor.core.analysis.lineage_extraction_bindings import (
    assign_target,
    runtime_bind_target,
    visit_ann_assign,
    visit_assign,
    visit_aug_assign,
    visit_global,
    visit_name,
    visit_named_expr,
    visit_nonlocal,
)
from contextor.core.analysis.lineage_extraction_visitors import (
    visit_call,
    visit_class_def,
    visit_function,
    visit_import,
    visit_import_from,
    visit_lambda,
    visit_module,
    visit_return,
)
from contextor.core.analysis.lineage_extraction_state import _ActiveComprehension, _CallArgumentInfo, _CallableInfo, _ImportInfo, _ParameterInfo, LineageExtractionState
from contextor.core.domain.lineage_facts import (
    ExtractedAnchorFact,
    ExtractedFlowFact,
    ExtractedLineageSourceFacts,
    ExtractedOccurrenceRef,
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    ParameterKind,
    ResolutionKind,
)


class _AnchorExtractor:
    def __init__(self, paths: dict[int, str], source_key: str) -> None:
        self.paths = paths
        self.source_key = source_key
        self.module_name = _module_name_from_source_key(source_key)
        self.state = LineageExtractionState()

    def extract(self, tree: ast.AST) -> tuple[tuple[ExtractedAnchorFact, ...], tuple[ExtractedFlowFact, ...]]:
        self._visit(tree, None, None)
        return tuple(sorted(self.state.anchors)), tuple(sorted(self.state.flows))

    def _add(self, kind: str, node: ast.AST, name: str | None, owner_local_id: str | None, *, ordinal: int = 0, local_kind: str | None = None) -> str:
        return add_anchor(self.state, self.paths, kind, node, name, owner_local_id, ordinal=ordinal, local_kind=local_kind)

    def _occurrence(self, kind: str, node: ast.AST, name: str | None = None, *, ordinal: int = 0) -> ExtractedOccurrenceRef:
        return occurrence(self.state, self.paths, kind, node, name, ordinal=ordinal)

    def _flow(self, *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0, dynamic_boundary: str | None = None) -> None:
        emit_flow(self.state, self.paths, source=source, target=target, relation=relation, node=node, resolution_kind=resolution_kind, confidence=confidence, ordinal=ordinal, dynamic_boundary=dynamic_boundary)

    def _frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
        return self.state.frame(owner)

    def _clone_frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
        return self.state.clone_frame(owner)

    def _replace_frame(
        self,
        owner: str | None,
        frame: dict[str, ExtractedOccurrenceRef],
    ) -> None:
        self.state.replace_frame(owner, frame)

    def _begin_comprehension(
        self,
        lookup_owner: str,
        lexical_enclosing_owner: str | None,
        effective_walrus_owner: str | None,
    ) -> _ActiveComprehension:
        return begin_comprehension(
            self.state,
            lookup_owner,
            lexical_enclosing_owner,
            effective_walrus_owner,
        )

    def _publish_executed_walrus(
        self,
        name: str,
        binding: ExtractedOccurrenceRef,
        target_owner: str | None,
    ) -> None:
        return publish_executed_walrus(
            self.state,
            name,
            binding,
            target_owner,
        )

    def _finish_comprehension(
        self,
        record: _ActiveComprehension,
    ) -> None:
        return finish_comprehension(
            self.state,
            record,
        )

    def _merge_frames(
        self,
        frames: tuple[dict[str, ExtractedOccurrenceRef], ...],
    ) -> dict[str, ExtractedOccurrenceRef]:
        return self.state.merge_frames(frames)

    def _visit_block_from_frame(
        self,
        body: list[ast.stmt],
        owner: str | None,
        walrus_owner: str | None,
        frame: dict[str, ExtractedOccurrenceRef],
    ) -> dict[str, ExtractedOccurrenceRef]:
        return visit_block_from_frame(
            self.state,
            body,
            owner,
            walrus_owner,
            frame,
            visit=self._visit,
        )

    def _blocked_names(self, owner: str | None) -> set[str]:
        return self.state.blocked_names(owner)

    def _callable_frame(self, owner: str | None) -> dict[str, _CallableInfo]:
        return self.state.callable_frame(owner)

    def _import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
        return self.state.import_frame(owner)

    def _register_import_binding(self, alias: ast.alias, owner: str | None, local_name: str, module_name: str | None, symbol_name: str | None) -> None:
        return register_import_binding(self.state, self.paths, alias, owner, local_name, module_name, symbol_name)
    def _value(
        self,
        node: ast.AST,
        owner: str | None,
        walrus_owner: str | None,
    ) -> ExtractedOccurrenceRef:
        self._visit(node, owner, walrus_owner)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            return self._occurrence("name_load", node, node.id)
        if isinstance(node, ast.Call):
            return self._occurrence("call_result", node)
        return self._occurrence("expression_result", node)

    def _parameter_symbolic(self, callable_symbol_name: str, parameter: _ParameterInfo) -> ExtractedSymbolicRef:
        return parameter_symbolic(self.module_name, callable_symbol_name, parameter)

    def _return_symbolic(self, callable_info: _CallableInfo) -> ExtractedSymbolicRef:
        return return_symbolic(self.module_name, callable_info)

    def _resolve_current_local_callable(self, node: ast.Call, owner: str | None) -> _CallableInfo | None:
        return resolve_current_local_callable(self.state, node, owner)
    def _current_import_info(self, owner: str | None, local_name: str) -> _ImportInfo | None:
        return current_import_info(self.state, owner, local_name)
    def _resolve_current_imported_callable(self, node: ast.Call, owner: str | None) -> ExtractedSymbolicRef | None:
        return resolve_current_imported_callable(self.state, node, owner)
    def _collect_call_arguments(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> tuple[_CallArgumentInfo, ...]:
        return collect_call_arguments(self.state, self.paths, node, owner, walrus_owner, value=self._value)
    def _emit_argument_to_parameter(self, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo) -> None:
        return emit_argument_to_parameter(self.state, self.paths, self.module_name, argument, callable_info, parameter)
    def _bind_call_arguments(self, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo) -> None:
        return bind_call_arguments(self.state, self.paths, self.module_name, arguments, callable_info)

    def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
        method = getattr(self, f"_visit_{type(node).__name__}", None)
        if method is not None:
            method(node, owner_local_id, walrus_owner_local_id)
            return
        for child in ast.iter_child_nodes(node):
            self._visit(child, owner_local_id, walrus_owner_local_id)

    def _visit_Module(self, node: ast.Module, _owner: str | None, _walrus_owner: str | None) -> None:
        return visit_module(self.state, self.paths, node, visit=self._visit)

    def _visit_ClassDef(self, node: ast.ClassDef, owner: str | None, walrus_owner: str | None) -> None:
        return visit_class_def(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)

    def _function_signature_evidence(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
        return function_signature_evidence(node, owner, walrus_owner, visit=self._visit)
    def _parameter_anchors(self, args: ast.arguments, owner: str, callable_symbol_name: str) -> tuple[_ParameterInfo, ...]:
        return parameter_anchors(self.state, self.paths, self.module_name, args, owner, callable_symbol_name)
    def _default_flows(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...]) -> None:
        return default_flows(self.state, self.paths, self.module_name, node, callable_symbol_name, parameters)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
        return visit_function(self.state, self.paths, self.module_name, node, kind, owner, walrus_owner, visit=self._visit)

    def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "function", owner, walrus_owner)

    def _visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "async_function", owner, walrus_owner)

    def _visit_Lambda(self, node: ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
        return visit_lambda(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)

    def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
        return visit_return(self.state, self.paths, self.module_name, node, owner, walrus_owner, value=self._value)

    def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
        return visit_call(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)

    def _visit_comprehension_expression(
        self,
        node: ast.AST,
        generators: list[ast.comprehension],
        values: tuple[ast.AST, ...],
        owner: str | None,
        walrus_owner: str | None,
    ) -> None:
        return visit_comprehension_expression(
            self.state,
            self.paths,
            node,
            generators,
            values,
            owner,
            walrus_owner,
            visit=self._visit,
            runtime_bind_target=self._runtime_bind_target,
        )

    def _visit_ListComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_SetComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_GeneratorExp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_DictComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.key, node.value), owner, walrus_owner)

    def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
        visit_name(self.state, self.paths, node, owner)

    def _assign_target(
        self,
        target: ast.AST,
        source: ExtractedOccurrenceRef,
        owner: str | None,
        walrus_owner: str | None,
    ) -> ExtractedOccurrenceRef | None:
        return assign_target(self.state, self.paths, target, source, owner, walrus_owner, visit=self._visit)

    def _runtime_bind_target(
        self,
        target: ast.AST,
        owner: str | None,
        walrus_owner: str | None,
    ) -> None:
        runtime_bind_target(self.state, self.paths, target, owner, walrus_owner, visit=self._visit)

    def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
        visit_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

    def _visit_AnnAssign(self, node: ast.AnnAssign, owner: str | None, walrus_owner: str | None) -> None:
        visit_ann_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

    def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
        visit_named_expr(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit, publish_walrus=self._publish_executed_walrus)

    def _visit_AugAssign(self, node: ast.AugAssign, owner: str | None, walrus_owner: str | None) -> None:
        visit_aug_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)

    def _visit_If(self, node: ast.If, owner: str | None, walrus_owner: str | None) -> None:
        return visit_if(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
        return visit_for(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)

    def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
        return visit_async_for(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)

    def _visit_While(self, node: ast.While, owner: str | None, walrus_owner: str | None) -> None:
        return visit_while(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
        return visit_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)

    def _visit_AsyncWith(self, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None) -> None:
        return visit_async_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)

    def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
        return visit_import(self.state, self.paths, node, owner)

    def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
        return visit_import_from(self.state, self.paths, self.source_key, node, owner)

    def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
        visit_global(self.state, self.paths, node, owner)

    def _visit_Nonlocal(self, node: ast.Nonlocal, owner: str | None, _walrus_owner: str | None) -> None:
        visit_nonlocal(self.state, self.paths, node, owner)

    def _visit_Try(self, node: ast.Try, owner: str | None, walrus_owner: str | None) -> None:
        return visit_try(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
        return visit_except_handler(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)

    def _visit_Match(self, node: ast.Match, owner: str | None, walrus_owner: str | None) -> None:
        return visit_match(self.state, node, owner, walrus_owner, visit=self._visit)

    def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
        return visit_match_as(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)

    def _visit_MatchStar(self, node: ast.MatchStar, owner: str | None, _walrus_owner: str | None) -> None:
        return visit_match_star(self.state, self.paths, node, owner)

    def _visit_MatchMapping(self, node: ast.MatchMapping, owner: str | None, walrus_owner: str | None) -> None:
        return visit_match_mapping(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)


def extract_lineage_source_facts(tree: ast.AST, *, source_key: str, source_fingerprint: str, limits: LineageExtractionLimits = DEFAULT_LINEAGE_EXTRACTION_LIMITS) -> ExtractedLineageSourceFacts:
    if not isinstance(tree, ast.AST):
        raise TypeError("tree must be ast.AST.")
    canonical_key = canonical_python_source_path(source_key)
    if canonical_key is None or canonical_key != source_key:
        raise ValueError("source_key must be canonical repository-relative POSIX Python path.")
    if not isinstance(source_fingerprint, str) or _FINGERPRINT_RE.fullmatch(source_fingerprint) is None:
        raise ValueError("source_fingerprint must be lowercase raw-byte SHA-256.")
    if not isinstance(limits, LineageExtractionLimits):
        raise TypeError("limits must be LineageExtractionLimits.")
    paths, limit_reason = _index_ast_paths(tree, limits)
    if limit_reason is not None:
        return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, status=LineageFamilyStatus.RESOURCE_LIMIT, resource_limit_reason=limit_reason)
    anchors, flows = _AnchorExtractor(paths, source_key).extract(tree)
    return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, anchors=anchors, flows=flows, surfaces=(), status=LineageFamilyStatus.FRESH)


__all__ = [
    "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
    "ExtractedLineageContribution",
    "ExtractedLineageProvider",
    "LineageExtractionLimits",
    "ParsedLineageSourceInput",
    "build_local_occurrence_id",
    "extract_lineage_source_facts",
    "parse_local_occurrence_id",
]
