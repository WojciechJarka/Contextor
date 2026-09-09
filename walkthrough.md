STATUS=FINAL_PASS
CONTEXTOR_PRE_EDIT=Fresh Contextor edit context revision 506; base HEAD matched and targets were clean.
IMPLEMENTATION=Stage 1C.5 implemented.
DEFERRED=Imports, attribute calls, literal star/dstar expansion, CFG, await, and expression-control behavior.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; tests/analysis/test_lineage_extraction.py
TESTS_RUN=focused and combined specified suites; git diff --check.
TEST_RESULTS=43 passed; 54 passed; diff check passed.
FULL_DIFFS=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 791a61e..b6e2ac5 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -172,6 +172,14 @@ class _ImportInfo:
     binding_id: str
 
 
+@dataclass(frozen=True)
+class _CallArgumentInfo:
+    occurrence: ExtractedOccurrenceRef
+    node: ast.AST
+    kind: str
+    keyword_name: str | None
+
+
 class _AnchorExtractor:
     def __init__(self, paths: dict[int, str], source_key: str) -> None:
         self.paths = paths
@@ -185,6 +193,8 @@ class _AnchorExtractor:
         self._bindings: dict[str | None, dict[str, ExtractedOccurrenceRef]] = {}
         self._callables: dict[str | None, dict[str, _CallableInfo]] = {}
         self._callables_by_anchor: dict[str, _CallableInfo] = {}
+        self._callables_by_binding: dict[str, _CallableInfo] = {}
+        self._callable_values: dict[str, _CallableInfo] = {}
         self._imports: dict[str | None, dict[str, _ImportInfo]] = {}
         self._blocked: dict[str | None, set[str]] = {}
 
@@ -218,11 +228,11 @@ class _AnchorExtractor:
         self._occurrences[cache_key] = occurrence
         return occurrence
 
-    def _flow(self, *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0) -> None:
+    def _flow(self, *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0, dynamic_boundary: str | None = None) -> None:
         local_id = f"flow:v1:{relation.value}:{self.paths[id(node)]}:i:{ordinal}"
         if local_id in self._flow_ids: raise ValueError(f"Duplicate lineage flow id: {local_id}")
         self._flow_ids.add(local_id)
-        self.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence))
+        self.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence, dynamic_boundary=dynamic_boundary))
 
     def _frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
         return self._bindings.setdefault(owner, {})
@@ -290,6 +300,49 @@ class _AnchorExtractor:
     def _parameter_symbolic(self, callable_symbol_name: str, parameter: _ParameterInfo) -> ExtractedSymbolicRef:
         return ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, self.module_name, callable_symbol_name, parameter.local_id)
 
+    def _return_symbolic(self, callable_info: _CallableInfo) -> ExtractedSymbolicRef:
+        return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, self.module_name, callable_info.name, callable_info.anchor_id)
+
+    def _resolve_current_local_callable(self, node: ast.Call, owner: str | None) -> _CallableInfo | None:
+        if not isinstance(node.func, ast.Name): return None
+        current = self._frame(owner).get(node.func.id)
+        if current is None: return None
+        return self._callables_by_anchor.get(current.local_id) or self._callables_by_binding.get(current.local_id)
+
+    def _collect_call_arguments(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> tuple[_CallArgumentInfo, ...]:
+        pending = [(arg, "starred" if isinstance(arg, ast.Starred) else "positional", None, index) for index, arg in enumerate(node.args)]
+        pending += [(keyword.value, "double_starred" if keyword.arg is None else "keyword", keyword.arg, len(node.args) + index) for index, keyword in enumerate(node.keywords)]
+        pending.sort(key=lambda item: (int(getattr(item[0], "lineno", 0) or 0), int(getattr(item[0], "col_offset", 0) or 0), item[3]))
+        result = []
+        for ordinal, (argument_node, kind, keyword_name, _source_ordinal) in enumerate(pending):
+            self._value(argument_node, owner, walrus_owner)
+            result.append(_CallArgumentInfo(self._occurrence("call_argument", argument_node, keyword_name if kind == "keyword" else None, ordinal=ordinal), argument_node, kind, keyword_name))
+        return tuple(result)
+
+    def _emit_argument_to_parameter(self, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo) -> None:
+        self._flow(source=argument.occurrence, target=self._parameter_symbolic(callable_info.name, parameter), relation=LineageRelation.ARGUMENT_TO_PARAMETER, node=argument.node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
+
+    def _bind_call_arguments(self, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo) -> None:
+        fixed = tuple(p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
+        keywords = {p.name: p for p in callable_info.parameters if p.kind in (ParameterKind.POSITIONAL_OR_KEYWORD, ParameterKind.KEYWORD_ONLY)}
+        vararg = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_POSITIONAL), None)
+        varkw = next((p for p in callable_info.parameters if p.kind is ParameterKind.VAR_KEYWORD), None)
+        consumed, index, uncertain = set(), 0, False
+        for argument in arguments:
+            if argument.kind == "starred": uncertain = True; continue
+            if argument.kind == "double_starred": continue
+            if argument.kind == "positional":
+                if uncertain: continue
+                if index < len(fixed):
+                    parameter = fixed[index]; index += 1; consumed.add(parameter.local_id); self._emit_argument_to_parameter(argument, callable_info, parameter)
+                elif vararg is not None: self._emit_argument_to_parameter(argument, callable_info, vararg)
+                continue
+            if argument.kind == "keyword" and argument.keyword_name is not None:
+                parameter = keywords.get(argument.keyword_name)
+                if parameter is not None and parameter.local_id not in consumed:
+                    consumed.add(parameter.local_id); self._emit_argument_to_parameter(argument, callable_info, parameter)
+                elif parameter is None and varkw is not None: self._emit_argument_to_parameter(argument, callable_info, varkw)
+
     def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
         method = getattr(self, f"_visit_{type(node).__name__}", None)
         if method is not None:
@@ -386,11 +439,37 @@ class _AnchorExtractor:
         callable_symbol_name = f"lambda@{self.paths[id(node)]}"
         parameters = self._parameter_anchors(node.args, lambda_id, callable_symbol_name)
         self._default_flows(node, callable_symbol_name, parameters)
-        self._callables_by_anchor[lambda_id] = _CallableInfo(callable_symbol_name, lambda_id, parameters)
+        callable_info = _CallableInfo(callable_symbol_name, lambda_id, parameters)
+        self._callables_by_anchor[lambda_id] = callable_info
         lambda_frame = self._frame(lambda_id)
         for parameter in parameters:
             lambda_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
-        self._visit(node.body, lambda_id, None)
+        body_source = self._value(node.body, lambda_id, None)
+        self._flow(source=body_source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node.body, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+        lambda_value = self._occurrence("expression_result", node)
+        self._callable_values[lambda_value.local_id] = callable_info
+
+    def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
+        if node.value is None: return
+        source = self._value(node.value, owner, walrus_owner)
+        callable_info = self._callables_by_anchor.get(owner) if owner is not None else None
+        if callable_info is not None:
+            self._flow(source=source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+
+    def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
+        self._visit(node.func, owner, walrus_owner)
+        call_site, call_result = self._occurrence("call_site", node), self._occurrence("call_result", node)
+        arguments = self._collect_call_arguments(node, owner, walrus_owner)
+        callable_info = self._resolve_current_local_callable(node, owner)
+        if callable_info is not None:
+            self._bind_call_arguments(arguments, callable_info)
+            self._flow(source=self._return_symbolic(callable_info), target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
+            return
+        if isinstance(node.func, ast.Name) and self._frame(owner).get(node.func.id) is None:
+            resolution_kind, confidence = ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED
+        else:
+            resolution_kind, confidence = ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC
+        self._flow(source=call_site, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=resolution_kind, confidence=confidence, dynamic_boundary="dynamic_call" if confidence is LineageConfidence.DYNAMIC else None)
 
     def _visit_comprehension_expression(self, node: ast.AST, generators: list[ast.comprehension], values: tuple[ast.AST, ...], owner: str | None, walrus_owner: str | None) -> None:
         comprehension_id = self._add("comprehension", node, None, owner)
@@ -445,6 +524,9 @@ class _AnchorExtractor:
         if target.id in self._blocked_names(owner):
             return
         self._frame(owner)[target.id] = binding
+        callable_info = self._callable_values.get(source.local_id)
+        if callable_info is not None:
+            self._callables_by_binding[binding.local_id] = callable_info
         self._flow(source=source, target=binding, relation=LineageRelation.ASSIGNS, node=target, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
 
     def _runtime_bind_target(
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 4c3901c..659830b 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -15,6 +15,7 @@ from contextor.core.analysis.lineage_extraction import (
 )
 from contextor.core.domain.lineage_facts import (
     ExtractedOccurrenceRef,
+    ExtractedSymbolicRef,
     ExtractedSymbolicKind,
     LineageConfidence,
     LineageFamilyStatus,
@@ -142,6 +143,45 @@ def _stage_1c_lexical_bind_sources(facts, name, line):
     ]
 
 
+def _stage_1c_call_result_flows(facts):
+    return [flow for flow in facts.flows if flow.relation is LineageRelation.CALL_RESULT]
+
+
+def _stage_1c_argument_parameter_names(facts):
+    return [parse_local_occurrence_id(flow.target.source_local_id)[3] for flow in facts.flows if flow.relation is LineageRelation.ARGUMENT_TO_PARAMETER and isinstance(flow.target, ExtractedSymbolicRef)]
+
+
+def test_stage_1c5_local_function_call_links_return_and_argument_exactly():
+    facts = _stage_1c_facts("def produce(value):\n return value\nresult = produce(1)\n")
+    function = _stage_1c_named(facts, "function", "produce")[0]
+    returns = [flow for flow in facts.flows if flow.relation is LineageRelation.RETURNS]
+    assert len(returns) == 1 and isinstance(returns[0].target, ExtractedSymbolicRef)
+    assert returns[0].target.kind is ExtractedSymbolicKind.RETURN and returns[0].target.source_local_id == function.local_id
+    call = next(flow for flow in _stage_1c_call_result_flows(facts) if flow.resolution_kind is ResolutionKind.CALL_EXACT)
+    assert isinstance(call.source, ExtractedSymbolicRef) and call.source == returns[0].target
+    assert _stage_1c_argument_parameter_names(facts) == ["value"]
+
+
+def test_stage_1c5_lambda_rebind_and_branch_resolution_are_fail_closed():
+    lambda_facts = _stage_1c_facts("fn = lambda value: value\nresult = fn(1)\n")
+    assert next(flow for flow in _stage_1c_call_result_flows(lambda_facts) if flow.resolution_kind is ResolutionKind.CALL_EXACT)
+    rebound = _stage_1c_facts("def run():\n return 1\nrun = other\nvalue = run()\n")
+    assert _stage_1c_call_result_flows(rebound)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+    branch = _stage_1c_facts("def run():\n return 1\nif cond:\n run = other\nvalue = run()\n")
+    assert _stage_1c_call_result_flows(branch)[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
+
+
+def test_stage_1c5_signature_stars_and_dynamic_calls_are_conservative():
+    facts = _stage_1c_facts("def run(a, /, b, *rest, flag, **extra):\n return b\nresult = run(1, 2, 3, 4, flag=5, other=6)\n")
+    assert _stage_1c_argument_parameter_names(facts) == ["a", "b", "rest", "rest", "flag", "extra"]
+    stars = _stage_1c_facts("def run(a, *rest, **extra):\n return a\nresult = run(*items, **mapping)\n")
+    assert _stage_1c_argument_parameter_names(stars) == []
+    unresolved = _stage_1c_facts("result = missing(1)\n")
+    dynamic = _stage_1c_facts("result = obj.method(1)\n")
+    assert _stage_1c_call_result_flows(unresolved)[0].resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert _stage_1c_call_result_flows(dynamic)[0].resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+
+
 def test_stage_1c_if_branches_are_exact_inside_and_ambiguous_after_merge():
     facts = _stage_1c_facts(
         "def run(cond):\n"

