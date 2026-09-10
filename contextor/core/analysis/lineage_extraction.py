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
        record = _ActiveComprehension(
            lookup_owner,
            lexical_enclosing_owner,
            effective_walrus_owner,
            self._clone_frame(effective_walrus_owner),
            set(),
        )
        self._replace_frame(
            lookup_owner,
            self._clone_frame(lexical_enclosing_owner),
        )
        imports = self._import_frame(lookup_owner)
        imports.clear()
        imports.update(
            self._import_frame(lexical_enclosing_owner)
        )
        self.state._active_comprehensions.append(record)
        return record

    def _publish_executed_walrus(
        self,
        name: str,
        binding: ExtractedOccurrenceRef,
        target_owner: str | None,
    ) -> None:
        for record in self.state._active_comprehensions:
            if record.effective_walrus_owner != target_owner:
                continue
            record.touched_walrus_names.add(name)
            self._frame(record.lookup_owner)[name] = binding

    def _finish_comprehension(
        self,
        record: _ActiveComprehension,
    ) -> None:
        if (
            not self.state._active_comprehensions
            or self.state._active_comprehensions[-1] is not record
        ):
            raise RuntimeError(
                "Comprehension lineage stack mismatch"
            )
        body_frame = self._clone_frame(
            record.effective_walrus_owner
        )
        merged = self._merge_frames(
            (record.walrus_entry_frame, body_frame)
        )
        self._replace_frame(
            record.effective_walrus_owner,
            merged,
        )
        self.state._active_comprehensions.pop()
        for parent in self.state._active_comprehensions:
            if (
                parent.effective_walrus_owner
                != record.effective_walrus_owner
            ):
                continue
            for name in record.touched_walrus_names:
                parent.touched_walrus_names.add(name)
                if name in merged:
                    self._frame(parent.lookup_owner)[name] = merged[name]
                else:
                    self._frame(parent.lookup_owner).pop(name, None)

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
        self._replace_frame(owner, frame)
        for child in body:
            self._visit(child, owner, walrus_owner)
        return self._clone_frame(owner)

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
        module_id = self._add("module", node, None, None)
        self._frame(module_id)
        for child in node.body:
            self._visit(child, module_id, None)

    def _visit_ClassDef(self, node: ast.ClassDef, owner: str | None, walrus_owner: str | None) -> None:
        class_id = self._add("class", node, node.name, owner)
        for child in (*node.decorator_list, *node.bases, *node.keywords):
            self._visit(child, owner, walrus_owner)
        self._frame(class_id)
        for child in node.body:
            self._visit(child, class_id, None)
        if node.name not in self._blocked_names(owner):
            self._frame(owner)[node.name] = ExtractedOccurrenceRef(class_id)

    def _function_signature_evidence(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
        return function_signature_evidence(node, owner, walrus_owner, visit=self._visit)
    def _parameter_anchors(self, args: ast.arguments, owner: str, callable_symbol_name: str) -> tuple[_ParameterInfo, ...]:
        return parameter_anchors(self.state, self.paths, self.module_name, args, owner, callable_symbol_name)
    def _default_flows(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...]) -> None:
        return default_flows(self.state, self.paths, self.module_name, node, callable_symbol_name, parameters)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
        function_id = self._add(kind, node, node.name, owner)
        for decorator in node.decorator_list:
            self._visit(decorator, owner, walrus_owner)
        self._function_signature_evidence(node, owner, walrus_owner)
        parameters = self._parameter_anchors(node.args, function_id, node.name)
        self._default_flows(node, node.name, parameters)
        callable_info = _CallableInfo(node.name, function_id, parameters)
        self._callable_frame(owner)[node.name] = callable_info
        self.state._callables_by_anchor[function_id] = callable_info
        function_frame = self._frame(function_id)
        for parameter in parameters:
            function_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
        for child in node.body:
            self._visit(child, function_id, None)
        if node.name not in self._blocked_names(owner):
            self._frame(owner)[node.name] = ExtractedOccurrenceRef(function_id)

    def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "function", owner, walrus_owner)

    def _visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef, owner: str | None, walrus_owner: str | None) -> None:
        self._visit_function(node, "async_function", owner, walrus_owner)

    def _visit_Lambda(self, node: ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
        lambda_id = self._add("lambda", node, None, owner)
        self._function_signature_evidence(node, owner, walrus_owner)
        callable_symbol_name = f"lambda@{self.paths[id(node)]}"
        parameters = self._parameter_anchors(node.args, lambda_id, callable_symbol_name)
        self._default_flows(node, callable_symbol_name, parameters)
        callable_info = _CallableInfo(callable_symbol_name, lambda_id, parameters)
        self.state._callables_by_anchor[lambda_id] = callable_info
        lambda_frame = self._frame(lambda_id)
        for parameter in parameters:
            lambda_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
        body_source = self._value(node.body, lambda_id, None)
        self._flow(source=body_source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node.body, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
        lambda_value = self._occurrence("expression_result", node)
        self.state._callable_values[lambda_value.local_id] = callable_info

    def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
        if node.value is None: return
        source = self._value(node.value, owner, walrus_owner)
        callable_info = self.state._callables_by_anchor.get(owner) if owner is not None else None
        if callable_info is not None:
            self._flow(source=source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)

    def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.func, owner, walrus_owner)
        callable_info = self._resolve_current_local_callable(node, owner)
        imported_return = self._resolve_current_imported_callable(node, owner)
        callee_ref = self._frame(owner).get(node.func.id) if isinstance(node.func, ast.Name) else None
        call_site, call_result = self._occurrence("call_site", node), self._occurrence("call_result", node)
        arguments = self._collect_call_arguments(node, owner, walrus_owner)
        if callable_info is not None:
            self._bind_call_arguments(arguments, callable_info)
            self._flow(source=self._return_symbolic(callable_info), target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
            return
        if imported_return is not None:
            self._flow(source=imported_return, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.IMPORT_EXACT, confidence=LineageConfidence.CONFIRMED)
            return
        if isinstance(node.func, ast.Name) and callee_ref is None:
            resolution_kind, confidence = ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED
            dynamic_boundary = None
        else:
            resolution_kind, confidence = ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC
            dynamic_boundary = "dynamic_call"
        self._flow(source=call_site, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=resolution_kind, confidence=confidence, dynamic_boundary=dynamic_boundary)

    def _visit_comprehension_expression(
        self,
        node: ast.AST,
        generators: list[ast.comprehension],
        values: tuple[ast.AST, ...],
        owner: str | None,
        walrus_owner: str | None,
    ) -> None:
        comprehension_id = self._add(
            "comprehension",
            node,
            None,
            owner,
        )
        if not generators:
            raise ValueError(
                "Parsed comprehension without generators"
            )
        first = generators[0]
        self._visit(
            first.iter,
            owner,
            walrus_owner,
        )
        effective_walrus_owner = walrus_owner or owner
        record = self._begin_comprehension(
            comprehension_id,
            owner,
            effective_walrus_owner,
        )
        try:
            self._runtime_bind_target(
                first.target,
                comprehension_id,
                effective_walrus_owner,
            )
            for condition in first.ifs:
                self._visit(
                    condition,
                    comprehension_id,
                    effective_walrus_owner,
                )
            for generator in generators[1:]:
                self._visit(
                    generator.iter,
                    comprehension_id,
                    effective_walrus_owner,
                )
                self._runtime_bind_target(
                    generator.target,
                    comprehension_id,
                    effective_walrus_owner,
                )
                for condition in generator.ifs:
                    self._visit(
                        condition,
                        comprehension_id,
                        effective_walrus_owner,
                    )
            for value in values:
                self._visit(
                    value,
                    comprehension_id,
                    effective_walrus_owner,
                )
        finally:
            self._finish_comprehension(record)

    def _visit_ListComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_SetComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_GeneratorExp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)

    def _visit_DictComp(self, node, owner, walrus_owner) -> None:
        self._visit_comprehension_expression(node, node.generators, (node.key, node.value), owner, walrus_owner)

    def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
        if isinstance(node.ctx, ast.Store):
            self._add("binding", node, node.id, owner)
            return
        if isinstance(node.ctx, ast.Load):
            load = self._occurrence("name_load", node, node.id)
            if node.id in self._blocked_names(owner):
                return
            source = self._frame(owner).get(node.id)
            if source is None:
                return
            self._flow(source=source, target=load, relation=LineageRelation.BINDS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)

    def _assign_target(
        self,
        target: ast.AST,
        source: ExtractedOccurrenceRef,
        owner: str | None,
        walrus_owner: str | None,
    ) -> ExtractedOccurrenceRef | None:
        if not isinstance(target, ast.Name):
            self._visit(target, owner, walrus_owner)
            return None
        binding = ExtractedOccurrenceRef(self._add("binding", target, target.id, owner))
        if target.id in self._blocked_names(owner):
            return None
        self._frame(owner)[target.id] = binding
        callable_info = self.state._callable_values.get(source.local_id)
        if callable_info is not None:
            self.state._callables_by_binding[binding.local_id] = callable_info
        self._flow(source=source, target=binding, relation=LineageRelation.ASSIGNS, node=target, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
        return binding

    def _runtime_bind_target(
        self,
        target: ast.AST,
        owner: str | None,
        walrus_owner: str | None,
    ) -> None:
        if isinstance(target, ast.Name):
            binding = ExtractedOccurrenceRef(
                self._add("binding", target, target.id, owner)
            )
            if target.id in self._blocked_names(owner):
                return
            source = self._occurrence(
                "runtime_bound_local",
                target,
                target.id,
            )
            self._frame(owner)[target.id] = binding
            self._flow(
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
                self._runtime_bind_target(
                    item,
                    owner,
                    walrus_owner,
                )
            return
        if isinstance(target, ast.Starred):
            self._runtime_bind_target(
                target.value,
                owner,
                walrus_owner,
            )
            return
        self._visit(target, owner, walrus_owner)

    def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
        source = self._value(node.value, owner, walrus_owner)
        for target in node.targets:
            self._assign_target(target, source, owner, walrus_owner)

    def _visit_AnnAssign(self, node: ast.AnnAssign, owner: str | None, walrus_owner: str | None) -> None:
        if node.value is None:
            self._visit(node.target, owner, walrus_owner)
            self._visit(node.annotation, owner, walrus_owner)
            return
        source = self._value(node.value, owner, walrus_owner)
        self._assign_target(node.target, source, owner, walrus_owner)
        self._visit(node.annotation, owner, walrus_owner)

    def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
        target_owner = walrus_owner or owner
        source = self._value(node.value, owner, walrus_owner)
        binding = self._assign_target(
            node.target,
            source,
            target_owner,
            walrus_owner,
        )
        if (
            binding is not None
            and isinstance(node.target, ast.Name)
        ):
            self._publish_executed_walrus(
                node.target.id,
                binding,
                target_owner,
            )

    def _visit_AugAssign(self, node: ast.AugAssign, owner: str | None, walrus_owner: str | None) -> None:
        if not isinstance(node.target, ast.Name):
            self._visit(node.target, owner, walrus_owner)
            self._value(node.value, owner, walrus_owner)
            return
        blocked = node.target.id in self._blocked_names(owner)
        prior = None if blocked else self._frame(owner).get(node.target.id)
        if prior is not None:
            prior_load = self._occurrence("name_load", node.target, node.target.id)
            self._flow(
                source=prior,
                target=prior_load,
                relation=LineageRelation.BINDS,
                node=node.target,
                resolution_kind=ResolutionKind.LEXICAL_EXACT,
                confidence=LineageConfidence.CONFIRMED,
            )
        self._value(node.value, owner, walrus_owner)
        binding = ExtractedOccurrenceRef(
            self._add("binding", node.target, node.target.id, owner)
        )
        if blocked or prior is None:
            return
        self._frame(owner)[node.target.id] = binding

    def _visit_If(self, node: ast.If, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.test, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        body_frame = self._visit_block_from_frame(
            node.body,
            owner,
            walrus_owner,
            entry_frame,
        )
        if node.orelse:
            else_frame = self._visit_block_from_frame(
                node.orelse,
                owner,
                walrus_owner,
                entry_frame,
            )
        else:
            else_frame = dict(entry_frame)
        self._replace_frame(
            owner,
            self._merge_frames((body_frame, else_frame)),
        )

    def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.iter, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        self._replace_frame(owner, entry_frame)
        self._runtime_bind_target(
            node.target,
            owner,
            walrus_owner,
        )
        for child in node.body:
            self._visit(child, owner, walrus_owner)
        body_frame = self._clone_frame(owner)
        loop_exit_frame = self._merge_frames(
            (entry_frame, body_frame)
        )
        self._replace_frame(owner, loop_exit_frame)
        if not node.orelse:
            return
        else_frame = self._visit_block_from_frame(
            node.orelse,
            owner,
            walrus_owner,
            loop_exit_frame,
        )
        self._replace_frame(
            owner,
            self._merge_frames((loop_exit_frame, else_frame)),
        )

    def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.iter, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        self._replace_frame(owner, entry_frame)
        self._runtime_bind_target(
            node.target,
            owner,
            walrus_owner,
        )
        for child in node.body:
            self._visit(child, owner, walrus_owner)
        body_frame = self._clone_frame(owner)
        loop_exit_frame = self._merge_frames(
            (entry_frame, body_frame)
        )
        self._replace_frame(owner, loop_exit_frame)
        if not node.orelse:
            return
        else_frame = self._visit_block_from_frame(
            node.orelse,
            owner,
            walrus_owner,
            loop_exit_frame,
        )
        self._replace_frame(
            owner,
            self._merge_frames((loop_exit_frame, else_frame)),
        )

    def _visit_While(self, node: ast.While, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.test, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        body_frame = self._visit_block_from_frame(
            node.body,
            owner,
            walrus_owner,
            entry_frame,
        )
        loop_exit_frame = self._merge_frames(
            (entry_frame, body_frame)
        )
        self._replace_frame(owner, loop_exit_frame)
        if not node.orelse:
            return
        else_frame = self._visit_block_from_frame(
            node.orelse,
            owner,
            walrus_owner,
            loop_exit_frame,
        )
        self._replace_frame(
            owner,
            self._merge_frames((loop_exit_frame, else_frame)),
        )

    def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
        for item in node.items:
            self._visit(
                item.context_expr,
                owner,
                walrus_owner,
            )
            if item.optional_vars is not None:
                self._runtime_bind_target(
                    item.optional_vars,
                    owner,
                    walrus_owner,
                )
        for child in node.body:
            self._visit(child, owner, walrus_owner)

    def _visit_AsyncWith(self, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None) -> None:
        for item in node.items:
            self._visit(
                item.context_expr,
                owner,
                walrus_owner,
            )
            if item.optional_vars is not None:
                self._runtime_bind_target(
                    item.optional_vars,
                    owner,
                    walrus_owner,
                )
        for child in node.body:
            self._visit(child, owner, walrus_owner)

    def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            self._register_import_binding(alias, owner, local_name, alias.name if alias.asname is not None else alias.name.split(".", 1)[0], None)

    def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
        module_name = _resolve_import_module(self.source_key, node.module, node.level)
        for alias in node.names:
            if alias.name == "*":
                self._replace_frame(owner, {})
                continue
            local_name = alias.asname or alias.name
            self._register_import_binding(alias, owner, local_name, module_name, alias.name)

    def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
        for ordinal, name in enumerate(node.names):
            self._add("global_declaration", node, name, owner, ordinal=ordinal)
            self._blocked_names(owner).add(name)
            self._frame(owner).pop(name, None)

    def _visit_Nonlocal(self, node: ast.Nonlocal, owner: str | None, _walrus_owner: str | None) -> None:
        for ordinal, name in enumerate(node.names):
            self._add("nonlocal_declaration", node, name, owner, ordinal=ordinal)
            self._blocked_names(owner).add(name)
            self._frame(owner).pop(name, None)

    def _visit_Try(self, node: ast.Try, owner: str | None, walrus_owner: str | None) -> None:
        entry_frame = self._clone_frame(owner)
        normal_frame = self._visit_block_from_frame(
            node.body,
            owner,
            walrus_owner,
            entry_frame,
        )
        if node.orelse:
            normal_frame = self._visit_block_from_frame(
                node.orelse,
                owner,
                walrus_owner,
                normal_frame,
            )
        reachable_frames = [normal_frame]
        for handler in node.handlers:
            self._replace_frame(owner, entry_frame)
            self._visit(handler, owner, walrus_owner)
            reachable_frames.append(
                self._clone_frame(owner)
            )
        merged_frame = self._merge_frames(
            tuple(reachable_frames)
        )
        self._replace_frame(owner, merged_frame)
        for child in node.finalbody:
            self._visit(child, owner, walrus_owner)

    def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
        if node.type is not None:
            self._visit(node.type, owner, walrus_owner)
        alias_name = node.name if isinstance(node.name, str) else None
        if alias_name is not None:
            binding = ExtractedOccurrenceRef(
                self._add("binding", node, alias_name, owner)
            )
            if alias_name not in self._blocked_names(owner):
                source = self._occurrence(
                    "runtime_bound_local",
                    node,
                    alias_name,
                )
                self._frame(owner)[alias_name] = binding
                self._flow(
                    source=source,
                    target=binding,
                    relation=LineageRelation.ASSIGNS,
                    node=node,
                    resolution_kind=ResolutionKind.LEXICAL_EXACT,
                    confidence=LineageConfidence.CONFIRMED,
                )
        for child in node.body:
            self._visit(child, owner, walrus_owner)
        exit_frame = self._clone_frame(owner)
        if alias_name is not None:
            exit_frame.pop(alias_name, None)
        self._replace_frame(owner, exit_frame)

    def _visit_Match(self, node: ast.Match, owner: str | None, walrus_owner: str | None) -> None:
        self._visit(node.subject, owner, walrus_owner)
        entry_frame = self._clone_frame(owner)
        reachable_frames = [dict(entry_frame)]
        for case in node.cases:
            self._replace_frame(owner, entry_frame)
            self._visit(case.pattern, owner, walrus_owner)
            if case.guard is not None:
                self._visit(case.guard, owner, walrus_owner)
            for child in case.body:
                self._visit(child, owner, walrus_owner)
            reachable_frames.append(
                self._clone_frame(owner)
            )
        self._replace_frame(
            owner,
            self._merge_frames(tuple(reachable_frames)),
        )

    def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
        if node.pattern is not None:
            self._visit(node.pattern, owner, walrus_owner)
        if node.name is not None:
            self._add("binding", node, node.name, owner)

    def _visit_MatchStar(self, node: ast.MatchStar, owner: str | None, _walrus_owner: str | None) -> None:
        if node.name is not None:
            self._add("binding", node, node.name, owner)

    def _visit_MatchMapping(self, node: ast.MatchMapping, owner: str | None, walrus_owner: str | None) -> None:
        for key in node.keys:
            self._visit(key, owner, walrus_owner)
        for pattern in node.patterns:
            self._visit(pattern, owner, walrus_owner)
        if node.rest is not None:
            self._add("binding", node, node.rest, owner)


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
