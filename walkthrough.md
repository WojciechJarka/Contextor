STATUS=FINAL_PASS
VISITORS_VERIFY=Approved D5C implementation confirmed: exactly visit_module, visit_class_def, visit_function, visit_lambda, visit_return, visit_call, visit_import, visit_import_from. No def _visit_*, NodeVisitor, ast.walk, or LineageExtractionState() construction exists. Reused evidence: canonical revision 554 fresh/verified; syntax checked_and_none; collision=0; cycles=0; dependency direction PASS; 2 PASS; 97 PASS; 110 PASS; diff-check PASS.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; contextor/core/analysis/lineage_extraction_visitors.py
FULL_DIFFS=
```diff
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
warning: in the working copy of 'contextor/core/analysis/lineage_extraction_visitors.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/lineage_extraction_visitors.py b/contextor/core/analysis/lineage_extraction_visitors.py
new file mode 100644
index 0000000..9cc1511
--- /dev/null
+++ b/contextor/core/analysis/lineage_extraction_visitors.py
@@ -0,0 +1,398 @@
+from __future__ import annotations
+
+import ast
+from collections.abc import Callable
+
+from contextor.core.analysis.lineage_extraction_calls import (
+    bind_call_arguments,
+    collect_call_arguments,
+    default_flows,
+    function_signature_evidence,
+    parameter_anchors,
+    register_import_binding,
+    resolve_current_imported_callable,
+    resolve_current_local_callable,
+)
+from contextor.core.analysis.lineage_extraction_contracts import _resolve_import_module
+from contextor.core.analysis.lineage_extraction_emit import (
+    add_anchor,
+    emit_flow,
+    occurrence,
+    return_symbolic,
+)
+from contextor.core.analysis.lineage_extraction_state import (
+    _CallableInfo,
+    LineageExtractionState,
+)
+from contextor.core.domain.lineage_facts import (
+    ExtractedOccurrenceRef,
+    LineageConfidence,
+    LineageRelation,
+    ResolutionKind,
+)
+
+VisitFn = Callable[[ast.AST, str | None, str | None], None]
+ValueFn = Callable[[ast.AST, str | None, str | None], ExtractedOccurrenceRef]
+
+
+def visit_module(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.Module,
+    *,
+    visit: VisitFn,
+) -> None:
+    module_id = add_anchor(
+        state,
+        paths,
+        "module",
+        node,
+        None,
+        None,
+    )
+    state.frame(module_id)
+    for child in node.body:
+        visit(child, module_id, None)
+
+
+def visit_class_def(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.ClassDef,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    visit: VisitFn,
+) -> None:
+    class_id = add_anchor(
+        state,
+        paths,
+        "class",
+        node,
+        node.name,
+        owner,
+    )
+    for child in (*node.decorator_list, *node.bases, *node.keywords):
+        visit(child, owner, walrus_owner)
+    state.frame(class_id)
+    for child in node.body:
+        visit(child, class_id, None)
+    if node.name not in state.blocked_names(owner):
+        state.frame(owner)[node.name] = ExtractedOccurrenceRef(class_id)
+
+
+def visit_function(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    module_name: str,
+    node: ast.FunctionDef | ast.AsyncFunctionDef,
+    kind: str,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    visit: VisitFn,
+) -> None:
+    function_id = add_anchor(
+        state,
+        paths,
+        kind,
+        node,
+        node.name,
+        owner,
+    )
+    for decorator in node.decorator_list:
+        visit(decorator, owner, walrus_owner)
+    function_signature_evidence(
+        node,
+        owner,
+        walrus_owner,
+        visit=visit,
+    )
+    parameters = parameter_anchors(
+        state,
+        paths,
+        module_name,
+        node.args,
+        function_id,
+        node.name,
+    )
+    default_flows(
+        state,
+        paths,
+        module_name,
+        node,
+        node.name,
+        parameters,
+    )
+    callable_info = _CallableInfo(
+        node.name,
+        function_id,
+        parameters,
+    )
+    state.callable_frame(owner)[node.name] = callable_info
+    state._callables_by_anchor[function_id] = callable_info
+    function_frame = state.frame(function_id)
+    for parameter in parameters:
+        function_frame[parameter.name] = ExtractedOccurrenceRef(
+            parameter.local_id
+        )
+    for child in node.body:
+        visit(child, function_id, None)
+    if node.name not in state.blocked_names(owner):
+        state.frame(owner)[node.name] = ExtractedOccurrenceRef(
+            function_id
+        )
+
+
+def visit_lambda(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    module_name: str,
+    node: ast.Lambda,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    visit: VisitFn,
+    value: ValueFn,
+) -> None:
+    lambda_id = add_anchor(
+        state,
+        paths,
+        "lambda",
+        node,
+        None,
+        owner,
+    )
+    function_signature_evidence(
+        node,
+        owner,
+        walrus_owner,
+        visit=visit,
+    )
+    callable_symbol_name = f"lambda@{paths[id(node)]}"
+    parameters = parameter_anchors(
+        state,
+        paths,
+        module_name,
+        node.args,
+        lambda_id,
+        callable_symbol_name,
+    )
+    default_flows(
+        state,
+        paths,
+        module_name,
+        node,
+        callable_symbol_name,
+        parameters,
+    )
+    callable_info = _CallableInfo(
+        callable_symbol_name,
+        lambda_id,
+        parameters,
+    )
+    state._callables_by_anchor[lambda_id] = callable_info
+    lambda_frame = state.frame(lambda_id)
+    for parameter in parameters:
+        lambda_frame[parameter.name] = ExtractedOccurrenceRef(
+            parameter.local_id
+        )
+    body_source = value(node.body, lambda_id, None)
+    emit_flow(
+        state,
+        paths,
+        source=body_source,
+        target=return_symbolic(module_name, callable_info),
+        relation=LineageRelation.RETURNS,
+        node=node.body,
+        resolution_kind=ResolutionKind.LEXICAL_EXACT,
+        confidence=LineageConfidence.CONFIRMED,
+    )
+    lambda_value = occurrence(
+        state,
+        paths,
+        "expression_result",
+        node,
+    )
+    state._callable_values[lambda_value.local_id] = callable_info
+
+
+def visit_return(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    module_name: str,
+    node: ast.Return,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    value: ValueFn,
+) -> None:
+    if node.value is None:
+        return
+    source = value(node.value, owner, walrus_owner)
+    callable_info = (
+        state._callables_by_anchor.get(owner)
+        if owner is not None
+        else None
+    )
+    if callable_info is not None:
+        emit_flow(
+            state,
+            paths,
+            source=source,
+            target=return_symbolic(module_name, callable_info),
+            relation=LineageRelation.RETURNS,
+            node=node,
+            resolution_kind=ResolutionKind.LEXICAL_EXACT,
+            confidence=LineageConfidence.CONFIRMED,
+        )
+
+
+def visit_call(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    module_name: str,
+    node: ast.Call,
+    owner: str | None,
+    walrus_owner: str | None,
+    *,
+    visit: VisitFn,
+    value: ValueFn,
+) -> None:
+    visit(node.func, owner, walrus_owner)
+    callable_info = resolve_current_local_callable(
+        state,
+        node,
+        owner,
+    )
+    imported_return = resolve_current_imported_callable(
+        state,
+        node,
+        owner,
+    )
+    callee_ref = (
+        state.frame(owner).get(node.func.id)
+        if isinstance(node.func, ast.Name)
+        else None
+    )
+    call_site = occurrence(
+        state,
+        paths,
+        "call_site",
+        node,
+    )
+    call_result = occurrence(
+        state,
+        paths,
+        "call_result",
+        node,
+    )
+    arguments = collect_call_arguments(
+        state,
+        paths,
+        node,
+        owner,
+        walrus_owner,
+        value=value,
+    )
+    if callable_info is not None:
+        bind_call_arguments(
+            state,
+            paths,
+            module_name,
+            arguments,
+            callable_info,
+        )
+        emit_flow(
+            state,
+            paths,
+            source=return_symbolic(module_name, callable_info),
+            target=call_result,
+            relation=LineageRelation.CALL_RESULT,
+            node=node,
+            resolution_kind=ResolutionKind.CALL_EXACT,
+            confidence=LineageConfidence.CONFIRMED,
+        )
+        return
+    if imported_return is not None:
+        emit_flow(
+            state,
+            paths,
+            source=imported_return,
+            target=call_result,
+            relation=LineageRelation.CALL_RESULT,
+            node=node,
+            resolution_kind=ResolutionKind.IMPORT_EXACT,
+            confidence=LineageConfidence.CONFIRMED,
+        )
+        return
+    if isinstance(node.func, ast.Name) and callee_ref is None:
+        resolution_kind = ResolutionKind.UNRESOLVED_NAME
+        confidence = LineageConfidence.UNRESOLVED
+        dynamic_boundary = None
+    else:
+        resolution_kind = ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
+        confidence = LineageConfidence.DYNAMIC
+        dynamic_boundary = "dynamic_call"
+    emit_flow(
+        state,
+        paths,
+        source=call_site,
+        target=call_result,
+        relation=LineageRelation.CALL_RESULT,
+        node=node,
+        resolution_kind=resolution_kind,
+        confidence=confidence,
+        dynamic_boundary=dynamic_boundary,
+    )
+
+
+def visit_import(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    node: ast.Import,
+    owner: str | None,
+) -> None:
+    for alias in node.names:
+        local_name = alias.asname or alias.name.split(".", 1)[0]
+        register_import_binding(
+            state,
+            paths,
+            alias,
+            owner,
+            local_name,
+            (
+                alias.name
+                if alias.asname is not None
+                else alias.name.split(".", 1)[0]
+            ),
+            None,
+        )
+
+
+def visit_import_from(
+    state: LineageExtractionState,
+    paths: dict[int, str],
+    source_key: str,
+    node: ast.ImportFrom,
+    owner: str | None,
+) -> None:
+    module_name = _resolve_import_module(
+        source_key,
+        node.module,
+        node.level,
+    )
+    for alias in node.names:
+        if alias.name == "*":
+            state.replace_frame(owner, {})
+            continue
+        local_name = alias.asname or alias.name
+        register_import_binding(
+            state,
+            paths,
+            alias,
+            owner,
+            local_name,
+            module_name,
+            alias.name,
+        )
```
