STATUS=FINAL_PASS

CONTEXTOR_EVIDENCE=Not rerun in the final D3 substep; D2 Contextor evidence remains fresh at revision 535 for facade/state/emit with verified workspace sync, checked_and_none syntax and zero collision/cycle diagnostics.

CALL_HELPER_OWNERSHIP=All ten callable/call/import helpers now have their semantic implementation in lineage_extraction_calls.py; facade methods forward to it.

SIGNATURE_HELPER_OWNERSHIP=function_signature_evidence, parameter_anchors and default_flows are calls-module implementations with facade forwarding adapters.

IMPORT_AUTHORITY=current_import_info preserves the existing binding_id equality check; tests passed.

DISPATCH_INVARIANT=_visit remains the only dynamic dispatch owner in facade; calls has no visitor.

ORACLE=2 PASS unchanged.

NO_DUPLICATES=Facade helper bodies are forwarding-only.

FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; contextor/core/analysis/lineage_extraction_calls.py; walkthrough.md.

TESTS_RUN=oracle plus lineage: 99 passed in 1.57s; combined requested suite: 110 passed in 3.99s; diff-check passed.

TEST_RESULTS=PASS.

FULL_DIFFS=
warning: in the working copy of 'contextor/core/analysis/lineage_extraction.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 7b186d9..65b54ba 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -18,6 +18,7 @@ from contextor.core.analysis.lineage_extraction_contracts import (
     build_local_occurrence_id,
     parse_local_occurrence_id,
 )
+from contextor.core.analysis.lineage_extraction_calls import bind_call_arguments, collect_call_arguments, current_import_info, default_flows, emit_argument_to_parameter, function_signature_evidence, parameter_anchors, register_import_binding, resolve_current_imported_callable, resolve_current_local_callable
 from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence, parameter_symbolic, return_symbolic
 from contextor.core.analysis.lineage_extraction_state import _ActiveComprehension, _CallArgumentInfo, _CallableInfo, _ImportInfo, _ParameterInfo, LineageExtractionState
 from contextor.core.domain.lineage_facts import (
@@ -168,11 +169,7 @@ class _AnchorExtractor:
         return self.state.import_frame(owner)
 
     def _register_import_binding(self, alias: ast.alias, owner: str | None, local_name: str, module_name: str | None, symbol_name: str | None) -> None:
-        binding_id = self._add("import_binding", alias, local_name, owner)
-        if local_name in self._blocked_names(owner): return
-        self._frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
-        if module_name is not None: self._import_frame(owner)[local_name] = _ImportInfo(module_name, symbol_name, binding_id)
-
+        return register_import_binding(self.state, self.paths, alias, owner, local_name, module_name, symbol_name)
     def _value(
         self,
         node: ast.AST,
@@ -193,59 +190,17 @@ class _AnchorExtractor:
         return return_symbolic(self.module_name, callable_info)
 
     def _resolve_current_local_callable(self, node: ast.Call, owner: str | None) -> _CallableInfo | None:
-        if not isinstance(node.func, ast.Name): return None
-        current = self._frame(owner).get(node.func.id)
-        if current is None: return None
-        return self.state._callables_by_anchor.get(current.local_id) or self.state._callables_by_binding.get(current.local_id)
-
+        return resolve_current_local_callable(self.state, node, owner)
     def _current_import_info(self, owner: str | None, local_name: str) -> _ImportInfo | None:
-        current, info = self._frame(owner).get(local_name), self._import_frame(owner).get(local_name)
-        return info if current is not None and info is not None and current.local_id == info.binding_id else None
-
+        return current_import_info(self.state, owner, local_name)
     def _resolve_current_imported_callable(self, node: ast.Call, owner: str | None) -> ExtractedSymbolicRef | None:
-        if isinstance(node.func, ast.Name):
-            info = self._current_import_info(owner, node.func.id)
-            if info is None or info.symbol_name is None: return None
-            return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, info.module_name, info.symbol_name, info.binding_id)
-        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
-            info = self._current_import_info(owner, node.func.value.id)
-            if info is None or info.symbol_name is not None: return None
-            return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, info.module_name, node.func.attr, info.binding_id)
-        return None
-
+        return resolve_current_imported_callable(self.state, node, owner)
     def _collect_call_arguments(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> tuple[_CallArgumentInfo, ...]:
-        pending = [(arg, "starred" if isinstance(arg, ast.Starred) else "positional", None, index) for index, arg in enumerate(node.args)]
-        pending += [(keyword.value, "double_starred" if keyword.arg is None else "keyword", keyword.arg, len(node.args) + index) for index, keyword in enumerate(node.keywords)]
-        pending.sort(key=lambda item: (int(getattr(item[0], "lineno", 0) or 0), int(getattr(item[0], "col_offset", 0) or 0), item[3]))
-        result = []
-        for ordinal, (argument_node, kind, keyword_name, _source_ordinal) in enumerate(pending):
-            self._value(argument_node, owner, walrus_owner)
-            result.append(_CallArgumentInfo(self._occurrence("call_argument", argument_node, keyword_name if kind == "keyword" else None, ordinal=ordinal), argument_node, kind, keyword_name))
-        return tuple(result)
-
+        return collect_call_arguments(self.state, self.paths, node, owner, walrus_owner, value=self._value)
     def _emit_argument_to_parameter(self, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo) -> None:
-        self._flow(source=argument.occurrence, target=self._parameter_symbolic(callable_info.name, parameter), relation=LineageRelation.ARGUMENT_TO_PARAMETER, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
-
+        return emit_argument_to_parameter(self.state, self.paths, self.module_name, argument, callable_info, parameter)
     def _bind_call_arguments(self, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo) -> None:
-        fixed = tuple(p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
-        keywords = {p.name: p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_OR_KEYWORD, ParameterKind.KEYWORD_ONLY)}
-        vararg = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_POSITIONAL), None)
-        varkw = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_KEYWORD), None)
-        consumed, index, uncertain = set(), 0, False
-        for argument in arguments:
-            if argument.kind == "starred": uncertain = True; continue
-            if argument.kind == "double_starred": continue
-            if argument.kind == "positional":
-                if uncertain: continue
-                if index < len(fixed):
-                    parameter = fixed[index]; index += 1; consumed.add(parameter.local_id); self._emit_argument_to_parameter(argument, callable_info, parameter)
-                elif vararg is not None: self._emit_argument_to_parameter(argument, callable_info, vararg)
-                continue
-            if argument.kind == "keyword" and argument.keyword_name is not None:
-                parameter = keywords.get(argument.keyword_name)
-                if parameter is not None and parameter.local_id not in consumed:
-                    consumed.add(parameter.local_id); self._emit_argument_to_parameter(argument, callable_info, parameter)
-                elif parameter is None and varkw is not None: self._emit_argument_to_parameter(argument, callable_info, varkw)
+        return bind_call_arguments(self.state, self.paths, self.module_name, arguments, callable_info)
 
     def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
         method = getattr(self, f"_visit_{type(node).__name__}", None)
@@ -272,46 +227,11 @@ class _AnchorExtractor:
             self._frame(owner)[node.name] = ExtractedOccurrenceRef(class_id)
 
     def _function_signature_evidence(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
-        args = node.args
-        for default in args.defaults:
-            self._visit(default, owner, walrus_owner)
-        for default in args.kw_defaults:
-            if default is not None:
-                self._visit(default, owner, walrus_owner)
-        all_args = list(getattr(args, "posonlyargs", ())) + list(args.args) + list(args.kwonlyargs)
-        if args.vararg is not None:
-            all_args.append(args.vararg)
-        if args.kwarg is not None:
-            all_args.append(args.kwarg)
-        for arg in all_args:
-            if arg.annotation is not None:
-                self._visit(arg.annotation, owner, walrus_owner)
-        returns = getattr(node, "returns", None)
-        if returns is not None:
-            self._visit(returns, owner, walrus_owner)
-
+        return function_signature_evidence(node, owner, walrus_owner, visit=self._visit)
     def _parameter_anchors(self, args: ast.arguments, owner: str, callable_symbol_name: str) -> tuple[_ParameterInfo, ...]:
-        result = []
-        groups = ((getattr(args, "posonlyargs", ()), ParameterKind.POSITIONAL_ONLY, "parameter_posonly"), (args.args, ParameterKind.POSITIONAL_OR_KEYWORD, "parameter_poskw"), ((args.vararg,) if args.vararg else (), ParameterKind.VAR_POSITIONAL, "parameter_vararg"), (args.kwonlyargs, ParameterKind.KEYWORD_ONLY, "parameter_kwonly"), ((args.kwarg,) if args.kwarg else (), ParameterKind.VAR_KEYWORD, "parameter_varkw"))
-        for group, kind, local_kind in groups:
-            for ordinal, parameter in enumerate(group):
-                local_id = self._add("parameter", parameter, parameter.arg, owner, ordinal=ordinal if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD) else 0, local_kind=local_kind)
-                info = _ParameterInfo(local_id, parameter.arg, kind, ordinal if kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD) else 0)
-                result.append((info, parameter))
-        for ordinal, (info, parameter) in enumerate(result):
-            self._flow(source=self._parameter_symbolic(callable_symbol_name, info), target=ExtractedOccurrenceRef(info.local_id), relation=LineageRelation.BINDS, node=parameter, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
-        return tuple(info for info, _parameter in result)
-
+        return parameter_anchors(self.state, self.paths, self.module_name, args, owner, callable_symbol_name)
     def _default_flows(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...]) -> None:
-        positional_parameters = tuple(parameter for parameter in parameters if parameter.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
-        positional_defaults = tuple(node.args.defaults)
-        if positional_defaults:
-            for ordinal, (default, parameter) in enumerate(zip(positional_defaults, positional_parameters[-len(positional_defaults) :])):
-                self._flow(source=self._occurrence("expression_result", default), target=self._parameter_symbolic(callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
-        kwonly_parameters = tuple(parameter for parameter in parameters if parameter.kind is ParameterKind.KEYWORD_ONLY)
-        for ordinal, (default, parameter) in enumerate(zip(node.args.kw_defaults, kwonly_parameters)):
-            if default is not None:
-                self._flow(source=self._occurrence("expression_result", default), target=self._parameter_symbolic(callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
+        return default_flows(self.state, self.paths, self.module_name, node, callable_symbol_name, parameters)
 
     def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
         function_id = self._add(kind, node, node.name, owner)

