STATUS=FINAL_PASS
CONTEXTOR_EVIDENCE=Deferred Contextor MCP pool was available. Manual incremental publication was used because get_live_events reported no_live_service after transient unreachability. Both final edit contexts are canonical_state=fresh, workspace_sync=verified, syntax=checked_and_none, canonical_revision=554. Fresh diagnostics: collision count 0; cycle count 0. Dependency direction is lineage_extraction.py -> lineage_extraction_visitors.py only. update_file reported live_state_persisted=true for both files.
VISITOR_OWNERSHIP=Exactly the eight moved semantic implementations live in lineage_extraction_visitors.py: visit_module, visit_class_def, visit_function, visit_lambda, visit_return, visit_call, visit_import, visit_import_from. The facade retains dispatch targets and contains forwarding-only bodies for those eight methods.
SEMANTIC_INVARIANTS=The implementation follows the frozen D5C orchestration: ordered anchors/frames, decorator/signature/default processing, callable registration order, parameter binding, local/import/dynamic call resolution, return behavior, dotted import binding, and wildcard frame replacement. Immutable equivalence hashes passed unchanged.
DISPATCH_INVARIANT=Exactly one dynamic getattr(self, f"_visit_{type(node).__name__}", None) remains in facade _AnchorExtractor._visit. Visitors defines no _visit_* function.
NO_SECONDARY_TRAVERSAL=Visitors contains no NodeVisitor, ast.walk, or LineageExtractionState construction. All AST descent uses injected visit/value callbacks; the only state construction remains facade _AnchorExtractor.__init__.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; contextor/core/analysis/lineage_extraction_visitors.py
TESTS_RUN=.venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction_equivalence.py -q; .venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q; .venv\\Scripts\\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/analysis/test_lineage_extraction_equivalence.py tests/test_no_double_parse.py tests/test_index_fusion.py -q; git diff --check 1866512e60b45aa08978571c052732c5fc76d2a3 -- contextor/core/analysis/lineage_extraction.py contextor/core/analysis/lineage_extraction_visitors.py
TEST_RESULTS=2 passed in 0.78s; 97 passed in 1.90s; 110 passed in 4.59s; diff-check PASS.
FULL_DIFFS=
```diff
warning: in the working copy of 'contextor/core/analysis/lineage_extraction.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 1cbd85c..b3a4f57 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -52,6 +52,16 @@ from contextor.core.analysis.lineage_extraction_bindings import (
     visit_named_expr,
     visit_nonlocal,
 )
+from contextor.core.analysis.lineage_extraction_visitors import (
+    visit_call,
+    visit_class_def,
+    visit_function,
+    visit_import,
+    visit_import_from,
+    visit_lambda,
+    visit_module,
+    visit_return,
+)
 from contextor.core.analysis.lineage_extraction_state import _ActiveComprehension, _CallArgumentInfo, _CallableInfo, _ImportInfo, _ParameterInfo, LineageExtractionState
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
@@ -210,20 +220,10 @@ class _AnchorExtractor:
             self._visit(child, owner_local_id, walrus_owner_local_id)
 
     def _visit_Module(self, node: ast.Module, _owner: str | None, _walrus_owner: str | None) -> None:
-        module_id = self._add("module", node, None, None)
-        self._frame(module_id)
-        for child in node.body:
-            self._visit(child, module_id, None)
+        return visit_module(self.state, self.paths, node, visit=self._visit)
 
     def _visit_ClassDef(self, node: ast.ClassDef, owner: str | None, walrus_owner: str | None) -> None:
-        class_id = self._add("class", node, node.name, owner)
-        for child in (*node.decorator_list, *node.bases, *node.keywords):
-            self._visit(child, owner, walrus_owner)
-        self._frame(class_id)
-        for child in node.body:
-            self._visit(child, class_id, None)
-        if node.name not in self._blocked_names(owner):
-            self._frame(owner)[node.name] = ExtractedOccurrenceRef(class_id)
+        return visit_class_def(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
 
     def _function_signature_evidence(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
         return function_signature_evidence(node, owner, walrus_owner, visit=self._visit)
@@ -233,22 +233,7 @@ class _AnchorExtractor:
         return default_flows(self.state, self.paths, self.module_name, node, callable_symbol_name, parameters)
 
     def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
-        function_id = self._add(kind, node, node.name, owner)
-        for decorator in node.decorator_list:
-            self._visit(decorator, owner, walrus_owner)
-        self._function_signature_evidence(node, owner, walrus_owner)
-        parameters = self._parameter_anchors(node.args, function_id, node.name)
-        self._default_flows(node, node.name, parameters)
-        callable_info = _CallableInfo(node.name, function_id, parameters)
-        self._callable_frame(owner)[node.name] = callable_info
-        self.state._callables_by_anchor[function_id] = callable_info
-        function_frame = self._frame(function_id)
-        for parameter in parameters:
-            function_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
-        for child in node.body:
-            self._visit(child, function_id, None)
-        if node.name not in self._blocked_names(owner):
-            self._frame(owner)[node.name] = ExtractedOccurrenceRef(function_id)
+        return visit_function(self.state, self.paths, self.module_name, node, kind, owner, walrus_owner, visit=self._visit)
 
     def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
         self._visit_function(node, "function", owner, walrus_owner)
@@ -257,49 +242,13 @@ class _AnchorExtractor:
         self._visit_function(node, "async_function", owner, walrus_owner)
 
     def _visit_Lambda(self, node: ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
-        lambda_id = self._add("lambda", node, None, owner)
-        self._function_signature_evidence(node, owner, walrus_owner)
-        callable_symbol_name = f"lambda@{self.paths[id(node)]}"
-        parameters = self._parameter_anchors(node.args, lambda_id, callable_symbol_name)
-        self._default_flows(node, callable_symbol_name, parameters)
-        callable_info = _CallableInfo(callable_symbol_name, lambda_id, parameters)
-        self.state._callables_by_anchor[lambda_id] = callable_info
-        lambda_frame = self._frame(lambda_id)
-        for parameter in parameters:
-            lambda_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
-        body_source = self._value(node.body, lambda_id, None)
-        self._flow(source=body_source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node.body, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
-        lambda_value = self._occurrence("expression_result", node)
-        self.state._callable_values[lambda_value.local_id] = callable_info
+        return visit_lambda(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)
 
     def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
-        if node.value is None: return
-        source = self._value(node.value, owner, walrus_owner)
-        callable_info = self.state._callables_by_anchor.get(owner) if owner is not None else None
-        if callable_info is not None:
-            self._flow(source=source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+        return visit_return(self.state, self.paths, self.module_name, node, owner, walrus_owner, value=self._value)
 
     def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
-        self._visit(node.func, owner, walrus_owner)
-        callable_info = self._resolve_current_local_callable(node, owner)
-        imported_return = self._resolve_current_imported_callable(node, owner)
-        callee_ref = self._frame(owner).get(node.func.id) if isinstance(node.func, ast.Name) else None
-        call_site, call_result = self._occurrence("call_site", node), self._occurrence("call_result", node)
-        arguments = self._collect_call_arguments(node, owner, walrus_owner)
-        if callable_info is not None:
-            self._bind_call_arguments(arguments, callable_info)
-            self._flow(source=self._return_symbolic(callable_info), target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.CALL_EXACT, confidence=LineageConfidence.CONFIRMED)
-            return
-        if imported_return is not None:
-            self._flow(source=imported_return, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=ResolutionKind.IMPORT_EXACT, confidence=LineageConfidence.CONFIRMED)
-            return
-        if isinstance(node.func, ast.Name) and callee_ref is None:
-            resolution_kind, confidence = ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED
-            dynamic_boundary = None
-        else:
-            resolution_kind, confidence = ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC
-            dynamic_boundary = "dynamic_call"
-        self._flow(source=call_site, target=call_result, relation=LineageRelation.CALL_RESULT, node=node, resolution_kind=resolution_kind, confidence=confidence, dynamic_boundary=dynamic_boundary)
+        return visit_call(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)
 
     def _visit_comprehension_expression(
         self,
@@ -384,18 +333,10 @@ class _AnchorExtractor:
         return visit_async_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
 
     def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
-        for alias in node.names:
-            local_name = alias.asname or alias.name.split(".", 1)[0]
-            self._register_import_binding(alias, owner, local_name, alias.name if alias.asname is not None else alias.name.split(".", 1)[0], None)
+        return visit_import(self.state, self.paths, node, owner)
 
     def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
-        module_name = _resolve_import_module(self.source_key, node.module, node.level)
-        for alias in node.names:
-            if alias.name == "*":
-                self._replace_frame(owner, {})
-                continue
-            local_name = alias.asname or alias.name
-            self._register_import_binding(alias, owner, local_name, module_name, alias.name)
+        return visit_import_from(self.state, self.paths, self.source_key, node, owner)
 
     def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
         visit_global(self.state, self.paths, node, owner)
```
