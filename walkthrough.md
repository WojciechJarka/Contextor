STATUS=PASS
CONTEXTOR_PRE_EDIT=LIVE revision 482; fresh checked_and_none syntax diagnostics; direct consumers=3.
IMPLEMENTATION=Stage 1C.2 current-frame lexical binding, direct assignments, valued annotations, walrus, conservative augassign, definitions/imports, and global/nonlocal blocking.
DEFERRED=1C.3 runtime-bound locals; 1C.4 control-flow; 1C.5 returns/calls; 1C.6 import resolution; 1C.7 comprehension/walrus edge cases; attribute/subscript lineage.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; tests/analysis/test_lineage_extraction.py; walkthrough.md report only.
TESTS_RUN=tests/analysis/test_lineage_extraction.py -q; tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q; git diff --check target files.
TEST_RESULTS=14 passed in 0.72s; 25 passed in 2.97s; diff check PASS.
FULL_DIFFS=

diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 6a4bb8a..7a6bdca 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -288,6 +288,7 @@ class _AnchorExtractor:
 
     def _visit_Module(self, node: ast.Module, _owner: str | None, _walrus_owner: str | None) -> None:
         module_id = self._add("module", node, None, None)
+        self._frame(module_id)
         for child in node.body:
             self._visit(child, module_id, None)
 
@@ -295,8 +296,11 @@ class _AnchorExtractor:
         class_id = self._add("class", node, node.name, owner)
         for child in (*node.decorator_list, *node.bases, *node.keywords):
             self._visit(child, owner, walrus_owner)
+        self._frame(class_id)
         for child in node.body:
             self._visit(child, class_id, None)
+        if node.name not in self._blocked_names(owner):
+            self._frame(owner)[node.name] = ExtractedOccurrenceRef(class_id)
 
     def _function_signature_evidence(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
         args = node.args
@@ -347,8 +351,16 @@ class _AnchorExtractor:
         self._function_signature_evidence(node, owner, walrus_owner)
         parameters = self._parameter_anchors(node.args, function_id, node.name)
         self._default_flows(node, node.name, parameters)
+        callable_info = _CallableInfo(node.name, function_id, parameters)
+        self._callable_frame(owner)[node.name] = callable_info
+        self._callables_by_anchor[function_id] = callable_info
+        function_frame = self._frame(function_id)
+        for parameter in parameters:
+            function_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
         for child in node.body:
             self._visit(child, function_id, None)
+        if node.name not in self._blocked_names(owner):
+            self._frame(owner)[node.name] = ExtractedOccurrenceRef(function_id)
 
     def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
         self._visit_function(node, "function", owner, walrus_owner)
@@ -362,6 +374,10 @@ class _AnchorExtractor:
         callable_symbol_name = f"lambda@{self.paths[id(node)]}"
         parameters = self._parameter_anchors(node.args, lambda_id, callable_symbol_name)
         self._default_flows(node, callable_symbol_name, parameters)
+        self._callables_by_anchor[lambda_id] = _CallableInfo(callable_symbol_name, lambda_id, parameters)
+        lambda_frame = self._frame(lambda_id)
+        for parameter in parameters:
+            lambda_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
         self._visit(node.body, lambda_id, None)
 
     def _visit_comprehension_expression(self, node: ast.AST, generators: list[ast.comprehension], values: tuple[ast.AST, ...], owner: str | None, walrus_owner: str | None) -> None:
@@ -399,32 +415,86 @@ class _AnchorExtractor:
     def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
         if isinstance(node.ctx, ast.Store):
             self._add("binding", node, node.id, owner)
+            return
+        if isinstance(node.ctx, ast.Load):
+            load = self._occurrence("name_load", node, node.id)
+            if node.id in self._blocked_names(owner):
+                return
+            source = self._frame(owner).get(node.id)
+            if source is None:
+                return
+            self._flow(source=source, target=load, relation=LineageRelation.BINDS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+
+    def _assign_target(self, target: ast.AST, source: ExtractedOccurrenceRef, owner: str | None, walrus_owner: str | None) -> None:
+        if not isinstance(target, ast.Name):
+            self._visit(target, owner, walrus_owner)
+            return
+        binding = ExtractedOccurrenceRef(self._add("binding", target, target.id, owner))
+        if target.id in self._blocked_names(owner):
+            return
+        self._frame(owner)[target.id] = binding
+        self._flow(source=source, target=binding, relation=LineageRelation.ASSIGNS, node=target, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+
+    def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
+        source = self._value(node.value, owner, walrus_owner)
+        for target in node.targets:
+            self._assign_target(target, source, owner, walrus_owner)
+
+    def _visit_AnnAssign(self, node: ast.AnnAssign, owner: str | None, walrus_owner: str | None) -> None:
+        if node.value is None:
+            self._visit(node.target, owner, walrus_owner)
+            self._visit(node.annotation, owner, walrus_owner)
+            return
+        source = self._value(node.value, owner, walrus_owner)
+        self._assign_target(node.target, source, owner, walrus_owner)
+        self._visit(node.annotation, owner, walrus_owner)
 
     def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
         target_owner = walrus_owner or owner
-        if isinstance(node.target, ast.Name):
-            self._add("binding", node.target, node.target.id, target_owner)
-        else:
-            self._visit(node.target, target_owner, walrus_owner)
-        self._visit(node.value, owner, walrus_owner)
+        source = self._value(node.value, owner, walrus_owner)
+        self._assign_target(node.target, source, target_owner, walrus_owner)
+
+    def _visit_AugAssign(self, node: ast.AugAssign, owner: str | None, walrus_owner: str | None) -> None:
+        self._value(node.value, owner, walrus_owner)
+        if not isinstance(node.target, ast.Name):
+            self._visit(node.target, owner, walrus_owner)
+            return
+        binding = ExtractedOccurrenceRef(self._add("binding", node.target, node.target.id, owner))
+        if node.target.id in self._blocked_names(owner):
+            return
+        prior = self._frame(owner).get(node.target.id)
+        if prior is None:
+            return
+        prior_load = self._occurrence("name_load", node.target, node.target.id)
+        self._flow(source=prior, target=prior_load, relation=LineageRelation.BINDS, node=node.target, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
+        self._frame(owner)[node.target.id] = binding
 
     def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
         for alias in node.names:
             local_name = alias.asname or alias.name.split(".", 1)[0]
-            self._add("import_binding", alias, local_name, owner)
+            binding_id = self._add("import_binding", alias, local_name, owner)
+            if local_name not in self._blocked_names(owner):
+                self._frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
 
     def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
         for alias in node.names:
             if alias.name != "*":
-                self._add("import_binding", alias, alias.asname or alias.name, owner)
+                local_name = alias.asname or alias.name
+                binding_id = self._add("import_binding", alias, local_name, owner)
+                if local_name not in self._blocked_names(owner):
+                    self._frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
 
     def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
         for ordinal, name in enumerate(node.names):
             self._add("global_declaration", node, name, owner, ordinal=ordinal)
+            self._blocked_names(owner).add(name)
+            self._frame(owner).pop(name, None)
 
     def _visit_Nonlocal(self, node: ast.Nonlocal, owner: str | None, _walrus_owner: str | None) -> None:
         for ordinal, name in enwarning: in the working copy of 'tests/analysis/test_lineage_extraction.py', LF will be replaced by CRLF the next time Git touches it
umerate(node.names):
             self._add("nonlocal_declaration", node, name, owner, ordinal=ordinal)
+            self._blocked_names(owner).add(name)
+            self._frame(owner).pop(name, None)
 
     def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
         if node.type is not None:
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index 104de5a..e2442d6 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -127,7 +127,12 @@ def test_typed_parameter_ids_bind_and_defaults_need_no_ast_reread():
         ("parameter_kwonly", 0, "flag"),
         ("parameter_varkw", 0, "extra"),
     }
-    binds = [flow for flow in facts.flows if flow.relation is LineageRelation.BINDS]
+    binds = [
+        flow
+        for flow in facts.flows
+        if flow.relation is LineageRelation.BINDS
+        and flow.resolution_kind is ResolutionKind.SIGNATURE_EXACT
+    ]
     assert len(binds) == 5
     assert all(
         flow.source.kind is ExtractedSymbolicKind.PARAMETER

