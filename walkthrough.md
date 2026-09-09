FILES_CHANGED=
contextor/core/analysis/lineage_extraction.py
tests/analysis/test_lineage_extraction.py

TESTS_RUN=
.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q
.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/test_no_double_parse.py tests/test_index_fusion.py -q

TEST_RESULTS=
11 passed in 0.76s
22 passed in 2.69s

ACTUAL_DIFF=
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -138,6 +138,13 @@ def _module_name_from_source_key(source_key: str) -> str:
     return module_name[: -len(".__init__")] if module_name.endswith(".__init__") else module_name
 
 
+@dataclass(frozen=True)
+class _ParameterInfo:
+    local_id: str
+    name: str
+    kind: ParameterKind
+    ordinal: int
+
+
 class _AnchorExtractor:
@@ -225,13 +232,29 @@ class _AnchorExtractor:
             self._flow(source=self._parameter_symbolic(callable_symbol_name, info), target=ExtractedOccurrenceRef(info.local_id), relation=LineageRelation.BINDS, node=parameter, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
         return tuple(info for info, _parameter in result)
 
+    def _default_flows(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...]) -> None:
+        positional_parameters = tuple(parameter for parameter in parameters if parameter.kind in (ParameterKind.POSITIONAL_ONLY, ParameterKind.POSITIONAL_OR_KEYWORD))
+        positional_defaults = tuple(node.args.defaults)
+        if positional_defaults:
+            for ordinal, (default, parameter) in enumerate(zip(positional_defaults, positional_parameters[-len(positional_defaults) :])):
+                self._flow(source=self._occurrence("expression_result", default), target=self._parameter_symbolic(callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
+        kwonly_parameters = tuple(parameter for parameter in parameters if parameter.kind is ParameterKind.KEYWORD_ONLY)
+        for ordinal, (default, parameter) in enumerate(zip(node.args.kw_defaults, kwonly_parameters)):
+            if default is not None:
+                self._flow(source=self._occurrence("expression_result", default), target=self._parameter_symbolic(callable_symbol_name, parameter), relation=LineageRelation.DEFAULTS_TO_PARAMETER, node=default, resolution_kind=ResolutionKind.SIGNATURE_EXACT, confidence=LineageConfidence.CONFIRMED, ordinal=ordinal)
+
     def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
         function_id = self._add(kind, node, node.name, owner)
         for decorator in node.decorator_list:
             self._visit(decorator, owner, walrus_owner)
         self._function_signature_evidence(node, owner, walrus_owner)
-        self._parameter_anchors(node.args, function_id, node.name)
+        parameters = self._parameter_anchors(node.args, function_id, node.name)
+        self._default_flows(node, node.name, parameters)
         for child in node.body:
             self._visit(child, function_id, None)
@@ -243,7 +266,9 @@ class _AnchorExtractor:
     def _visit_Lambda(self, node: ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
         lambda_id = self._add("lambda", node, None, owner)
         self._function_signature_evidence(node, owner, walrus_owner)
-        self._parameter_anchors(node.args, lambda_id, f"lambda@{self.paths[id(node)]}")
+        callable_symbol_name = f"lambda@{self.paths[id(node)]}"
+        parameters = self._parameter_anchors(node.args, lambda_id, callable_symbol_name)
+        self._default_flows(node, callable_symbol_name, parameters)
         self._visit(node.body, lambda_id, None)
@@ -363,10 +388,3 @@ __all__ = [
     "extract_lineage_source_facts",
     "parse_local_occurrence_id",
 ]
-
-@dataclass(frozen=True)
-class _ParameterInfo:
-    local_id: str
-    name: str
-    kind: ParameterKind
-    ordinal: int
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -12,7 +12,14 @@ from contextor.core.analysis.lineage_extraction import (
     extract_lineage_source_facts,
     parse_local_occurrence_id,
 )
-from contextor.core.domain.lineage_facts import LineageFamilyStatus
+from contextor.core.domain.lineage_facts import (
+    ExtractedOccurrenceRef,
+    ExtractedSymbolicKind,
+    LineageConfidence,
+    LineageFamilyStatus,
+    LineageRelation,
+    ResolutionKind,
+)
 from contextor.core.source import parse_source_with_fingerprint
 from contextor.core.symbol_engine import indexer as indexer_module
@@ -50,6 +57,43 @@ def test_extraction_is_deterministic_source_local_and_has_parameter_lineage(mon
     assert "SemanticEndpoint" not in vars(module)
 
 
+def test_typed_parameter_ids_bind_and_defaults_need_no_ast_reread():
+    tree = ast.parse("def run(a, /, b=1, *items, flag=2, **extra):\n    return b\n")
+    facts = extract_lineage_source_facts(tree, source_key="pkg.py", source_fingerprint=FINGERPRINT)
+    parsed_parameters = {
+        parse_local_occurrence_id(anchor.local_id)
+        for anchor in facts.anchors
+        if anchor.kind == "parameter"
+    }
+    assert {(kind, ordinal, name) for kind, _path, ordinal, name in parsed_parameters} == {
+        ("parameter_posonly", 0, "a"),
+        ("parameter_poskw", 0, "b"),
+        ("parameter_vararg", 0, "items"),
+        ("parameter_kwonly", 0, "flag"),
+        ("parameter_varkw", 0, "extra"),
+    }
+    binds = [flow for flow in facts.flows if flow.relation is LineageRelation.BINDS]
+    assert len(binds) == 5
+    assert all(
+        flow.source.kind is ExtractedSymbolicKind.PARAMETER
+        and flow.resolution_kind is ResolutionKind.SIGNATURE_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        and flow.source.source_local_id is not None
+        for flow in binds
+    )
+    for flow in binds:
+        kind, _path, _ordinal, name = parse_local_occurrence_id(flow.source.source_local_id)
+        assert kind.startswith("parameter_")
+        assert name
+    defaults = [flow for flow in facts.flows if flow.relation is LineageRelation.DEFAULTS_TO_PARAMETER]
+    assert len(defaults) == 2
+    assert all(
+        isinstance(flow.source, ExtractedOccurrenceRef)
+        and flow.target.kind is ExtractedSymbolicKind.PARAMETER
+        and flow.resolution_kind is ResolutionKind.SIGNATURE_EXACT
+        and flow.confidence is LineageConfidence.CONFIRMED
+        for flow in defaults
+    )
+
+
 def test_lexical_owners_parameters_comprehensions_and_declarations():
