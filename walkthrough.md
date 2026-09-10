# Contextor Stage 1E.1 final corrective pass — direct __all__ subscript mutation authority

STATUS=COMPLETE_WITH_LIVE_CERTIFICATION_BLOCKED

Added facade-dispatched _visit_Subscript. At module scope it invalidates exact __all__ authority only for Store/Del Subscript targets whose direct value is Name(__all__), then visits value and slice once in generic traversal order. Reads and alias-mediated mutation remain unaffected/out of scope. No AST walk, second visitor, reread, domain, materialization, MCP, schema, or version change.

## Regression evidence

* __all__[0] assignment, slice assignment, subscript AugAssign, and del __all__[0] each produce surfaces=().
* x=__all__[0] preserves confirmed exact literal EXPORT.
* Equivalence test passed unchanged, including legacy anchors+flows with surfaces stripped; no hash regeneration.

## Tests

* test_lineage_extraction.py: 194 passed.
* test_lineage_extraction_equivalence.py: 3 passed.
* required combined focused command: 208 passed.
* git diff --check: passed; only LF-to-CRLF advisories.

## LIVE / Contextor

Pre-edit revision=600, resync_required=false, diagnostics fresh, active MCP documentation inspected; no deferred discovery tool was injected. Post-edit get_live_events(after_revision=600) returned transient_connection_failure, so matching later watcher revision, continuous cursor, and verified changed-file freshness cannot be established. update_file was not called. LIVE_CERTIFICATION=BLOCKED.

One LineageExtractionState construction and facade dispatch owner remain; textual verification found no ast.walk. New helper has no facade back-edge. Pre-edit cycle/collision diagnostics were fresh; post-edit graph certification blocked by LIVE owner reachability.

FILES_CHANGED:
* contextor/core/analysis/lineage_extraction.py
* contextor/core/analysis/lineage_extraction_surfaces.py
* tests/analysis/test_lineage_extraction.py

## COMPLETE raw unified FULL_DIFF

~~~diff
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index d9215e7..0af88a9 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -1,17 +1,17 @@
-from __future__ import annotations
-
+from __future__ import annotations
+
 import ast
 
 from contextor.core.analysis.state_manager import canonical_python_source_path
-from contextor.core.analysis.lineage_extraction_contracts import (
-    DEFAULT_LINEAGE_EXTRACTION_LIMITS,
-    ExtractedLineageContribution,
-    ExtractedLineageProvider,
-    LineageExtractionLimits,
-    ParsedLineageSourceInput,
-    _FINGERPRINT_RE,
-    _index_ast_paths,
-    _module_name_from_source_key,
+from contextor.core.analysis.lineage_extraction_contracts import (
+    DEFAULT_LINEAGE_EXTRACTION_LIMITS,
+    ExtractedLineageContribution,
+    ExtractedLineageProvider,
+    LineageExtractionLimits,
+    ParsedLineageSourceInput,
+    _FINGERPRINT_RE,
+    _index_ast_paths,
+    _module_name_from_source_key,
     build_local_occurrence_id,
     parse_local_occurrence_id,
 )
@@ -57,7 +57,7 @@ from contextor.core.analysis.lineage_extraction_visitors import (
     visit_yield,
 )
 from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
-from contextor.core.analysis.lineage_extraction_surfaces import finalize_surfaces
+from contextor.core.analysis.lineage_extraction_surfaces import finalize_surfaces, observe_all_subscript_mutation
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
     ExtractedFlowFact,
@@ -66,22 +66,22 @@ from contextor.core.domain.lineage_facts import (
     ExtractedSurfaceFact,
     LineageFamilyStatus,
 )
-
-
-class _AnchorExtractor:
-    def __init__(self, paths: dict[int, str], source_key: str) -> None:
-        self.paths = paths
-        self.source_key = source_key
-        self.module_name = _module_name_from_source_key(source_key)
-        self.state = LineageExtractionState()
-
+
+
+class _AnchorExtractor:
+    def __init__(self, paths: dict[int, str], source_key: str) -> None:
+        self.paths = paths
+        self.source_key = source_key
+        self.module_name = _module_name_from_source_key(source_key)
+        self.state = LineageExtractionState()
+
     def extract(self, tree: ast.AST) -> tuple[tuple[ExtractedAnchorFact, ...], tuple[ExtractedFlowFact, ...], tuple[ExtractedSurfaceFact, ...]]:
         self._visit(tree, None, None)
         finalize_captures(self.state, self.paths)
         module_owner = next(anchor.local_id for anchor in self.state.anchors if anchor.kind == "module")
         finalize_surfaces(self.state, self.paths, self.module_name, module_owner)
         return tuple(sorted(self.state.anchors)), tuple(sorted(self.state.flows)), tuple(sorted(self.state.surfaces))
-
+
     def _publish_executed_walrus(
         self,
         name: str,
@@ -94,15 +94,15 @@ class _AnchorExtractor:
             binding,
             target_owner,
         )
-
+
     def _value(
-        self,
-        node: ast.AST,
-        owner: str | None,
-        walrus_owner: str | None,
-    ) -> ExtractedOccurrenceRef:
-        self._visit(node, owner, walrus_owner)
-        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
+        self,
+        node: ast.AST,
+        owner: str | None,
+        walrus_owner: str | None,
+    ) -> ExtractedOccurrenceRef:
+        self._visit(node, owner, walrus_owner)
+        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
             return occurrence(
                 self.state,
                 self.paths,
@@ -123,33 +123,33 @@ class _AnchorExtractor:
             "expression_result",
             node,
         )
-
-    def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
-        method = getattr(self, f"_visit_{type(node).__name__}", None)
-        if method is not None:
-            method(node, owner_local_id, walrus_owner_local_id)
-            return
-        for child in ast.iter_child_nodes(node):
-            self._visit(child, owner_local_id, walrus_owner_local_id)
-
+
+    def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
+        method = getattr(self, f"_visit_{type(node).__name__}", None)
+        if method is not None:
+            method(node, owner_local_id, walrus_owner_local_id)
+            return
+        for child in ast.iter_child_nodes(node):
+            self._visit(child, owner_local_id, walrus_owner_local_id)
+
     def _visit_Module(self, node: ast.Module, _owner: str | None, _walrus_owner: str | None) -> None:
         return visit_module(self.state, self.paths, node, visit=self._visit)
-
+
     def _visit_ClassDef(self, node: ast.ClassDef, owner: str | None, walrus_owner: str | None) -> None:
         return visit_class_def(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
-
+
     def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
         return visit_function(self.state, self.paths, self.module_name, node, kind, owner, walrus_owner, visit=self._visit)
-
-    def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
-        self._visit_function(node, "function", owner, walrus_owner)
-
-    def _visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef, owner: str | None, walrus_owner: str | None) -> None:
-        self._visit_function(node, "async_function", owner, walrus_owner)
-
+
+    def _visit_FunctionDef(self, node: ast.FunctionDef, owner: str | None, walrus_owner: str | None) -> None:
+        self._visit_function(node, "function", owner, walrus_owner)
+
+    def _visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef, owner: str | None, walrus_owner: str | None) -> None:
+        self._visit_function(node, "async_function", owner, walrus_owner)
+
     def _visit_Lambda(self, node: ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
         return visit_lambda(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)
-
+
     def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
         return visit_return(self.state, self.paths, self.module_name, node, owner, walrus_owner, value=self._value)
 
@@ -158,17 +158,17 @@ class _AnchorExtractor:
 
     def _visit_YieldFrom(self, node: ast.YieldFrom, owner: str | None, walrus_owner: str | None) -> None:
         return visit_yield(self.state, node, owner, walrus_owner, visit=self._visit)
-
+
     def _visit_Call(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> None:
         return visit_call(self.state, self.paths, self.module_name, node, owner, walrus_owner, visit=self._visit, value=self._value)
-
+
     def _visit_comprehension_expression(
-        self,
-        node: ast.AST,
-        generators: list[ast.comprehension],
-        values: tuple[ast.AST, ...],
-        owner: str | None,
-        walrus_owner: str | None,
+        self,
+        node: ast.AST,
+        generators: list[ast.comprehension],
+        values: tuple[ast.AST, ...],
+        owner: str | None,
+        walrus_owner: str | None,
     ) -> None:
         return visit_comprehension_expression(
             self.state,
@@ -181,115 +181,120 @@ class _AnchorExtractor:
             visit=self._visit,
             runtime_bind_target=self._runtime_bind_target,
         )
-
-    def _visit_ListComp(self, node, owner, walrus_owner) -> None:
-        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)
-
-    def _visit_SetComp(self, node, owner, walrus_owner) -> None:
-        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)
-
-    def _visit_GeneratorExp(self, node, owner, walrus_owner) -> None:
-        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)
-
-    def _visit_DictComp(self, node, owner, walrus_owner) -> None:
-        self._visit_comprehension_expression(node, node.generators, (node.key, node.value), owner, walrus_owner)
-
+
+    def _visit_ListComp(self, node, owner, walrus_owner) -> None:
+        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)
+
+    def _visit_SetComp(self, node, owner, walrus_owner) -> None:
+        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)
+
+    def _visit_GeneratorExp(self, node, owner, walrus_owner) -> None:
+        self._visit_comprehension_expression(node, node.generators, (node.elt,), owner, walrus_owner)
+
+    def _visit_DictComp(self, node, owner, walrus_owner) -> None:
+        self._visit_comprehension_expression(node, node.generators, (node.key, node.value), owner, walrus_owner)
+
     def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
         visit_name(self.state, self.paths, node, owner)
 
-    def _runtime_bind_target(
-        self,
-        target: ast.AST,
-        owner: str | None,
-        walrus_owner: str | None,
-    ) -> None:
+    def _visit_Subscript(self, node: ast.Subscript, owner: str | None, walrus_owner: str | None) -> None:
+        observe_all_subscript_mutation(self.state, node, owner)
+        self._visit(node.value, owner, walrus_owner)
+        self._visit(node.slice, owner, walrus_owner)
+
+    def _runtime_bind_target(
+        self,
+        target: ast.AST,
+        owner: str | None,
+        walrus_owner: str | None,
+    ) -> None:
         runtime_bind_target(self.state, self.paths, target, owner, walrus_owner, visit=self._visit)
-
-    def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
+
+    def _visit_Assign(self, node: ast.Assign, owner: str | None, walrus_owner: str | None) -> None:
         visit_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)
-
-    def _visit_AnnAssign(self, node: ast.AnnAssign, owner: str | None, walrus_owner: str | None) -> None:
+
+    def _visit_AnnAssign(self, node: ast.AnnAssign, owner: str | None, walrus_owner: str | None) -> None:
         visit_ann_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)
-
-    def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
+
+    def _visit_NamedExpr(self, node: ast.NamedExpr, owner: str | None, walrus_owner: str | None) -> None:
         visit_named_expr(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit, publish_walrus=self._publish_executed_walrus)
-
-    def _visit_AugAssign(self, node: ast.AugAssign, owner: str | None, walrus_owner: str | None) -> None:
+
+    def _visit_AugAssign(self, node: ast.AugAssign, owner: str | None, walrus_owner: str | None) -> None:
         visit_aug_assign(self.state, self.paths, node, owner, walrus_owner, value=self._value, visit=self._visit)
-
+
     def _visit_If(self, node: ast.If, owner: str | None, walrus_owner: str | None) -> None:
         return visit_if(self.state, node, owner, walrus_owner, visit=self._visit)
-
+
     def _visit_For(self, node: ast.For, owner: str | None, walrus_owner: str | None) -> None:
         return visit_for(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
-
+
     def _visit_AsyncFor(self, node: ast.AsyncFor, owner: str | None, walrus_owner: str | None) -> None:
         return visit_async_for(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
-
+
     def _visit_While(self, node: ast.While, owner: str | None, walrus_owner: str | None) -> None:
         return visit_while(self.state, node, owner, walrus_owner, visit=self._visit)
-
+
     def _visit_With(self, node: ast.With, owner: str | None, walrus_owner: str | None) -> None:
         return visit_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
-
+
     def _visit_AsyncWith(self, node: ast.AsyncWith, owner: str | None, walrus_owner: str | None) -> None:
         return visit_async_with(self.state, node, owner, walrus_owner, visit=self._visit, runtime_bind_target=self._runtime_bind_target)
-
+
     def _visit_Import(self, node: ast.Import, owner: str | None, _walrus_owner: str | None) -> None:
         return visit_import(self.state, self.paths, node, owner)
-
+
     def _visit_ImportFrom(self, node: ast.ImportFrom, owner: str | None, _walrus_owner: str | None) -> None:
         return visit_import_from(self.state, self.paths, self.source_key, node, owner)
-
+
     def _visit_Global(self, node: ast.Global, owner: str | None, _walrus_owner: str | None) -> None:
         visit_global(self.state, self.paths, node, owner)
-
+
     def _visit_Nonlocal(self, node: ast.Nonlocal, owner: str | None, _walrus_owner: str | None) -> None:
         visit_nonlocal(self.state, self.paths, node, owner)
-
+
     def _visit_Try(self, node: ast.Try, owner: str | None, walrus_owner: str | None) -> None:
         return visit_try(self.state, node, owner, walrus_owner, visit=self._visit)
-
+
     def _visit_ExceptHandler(self, node: ast.ExceptHandler, owner: str | None, walrus_owner: str | None) -> None:
         return visit_except_handler(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
-
+
     def _visit_Match(self, node: ast.Match, owner: str | None, walrus_owner: str | None) -> None:
         return visit_match(self.state, node, owner, walrus_owner, visit=self._visit)
-
+
     def _visit_MatchAs(self, node: ast.MatchAs, owner: str | None, walrus_owner: str | None) -> None:
         return visit_match_as(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
-
+
     def _visit_MatchStar(self, node: ast.MatchStar, owner: str | None, _walrus_owner: str | None) -> None:
         return visit_match_star(self.state, self.paths, node, owner)
-
+
     def _visit_MatchMapping(self, node: ast.MatchMapping, owner: str | None, walrus_owner: str | None) -> None:
         return visit_match_mapping(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
-
-
-def extract_lineage_source_facts(tree: ast.AST, *, source_key: str, source_fingerprint: str, limits: LineageExtractionLimits = DEFAULT_LINEAGE_EXTRACTION_LIMITS) -> ExtractedLineageSourceFacts:
-    if not isinstance(tree, ast.AST):
-        raise TypeError("tree must be ast.AST.")
-    canonical_key = canonical_python_source_path(source_key)
-    if canonical_key is None or canonical_key != source_key:
-        raise ValueError("source_key must be canonical repository-relative POSIX Python path.")
-    if not isinstance(source_fingerprint, str) or _FINGERPRINT_RE.fullmatch(source_fingerprint) is None:
-        raise ValueError("source_fingerprint must be lowercase raw-byte SHA-256.")
-    if not isinstance(limits, LineageExtractionLimits):
-        raise TypeError("limits must be LineageExtractionLimits.")
-    paths, limit_reason = _index_ast_paths(tree, limits)
-    if limit_reason is not None:
-        return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, status=LineageFamilyStatus.RESOURCE_LIMIT, resource_limit_reason=limit_reason)
+
+
+def extract_lineage_source_facts(tree: ast.AST, *, source_key: str, source_fingerprint: str, limits: LineageExtractionLimits = DEFAULT_LINEAGE_EXTRACTION_LIMITS) -> ExtractedLineageSourceFacts:
+    if not isinstance(tree, ast.AST):
+        raise TypeError("tree must be ast.AST.")
+    canonical_key = canonical_python_source_path(source_key)
+    if canonical_key is None or canonical_key != source_key:
+        raise ValueError("source_key must be canonical repository-relative POSIX Python path.")
+    if not isinstance(source_fingerprint, str) or _FINGERPRINT_RE.fullmatch(source_fingerprint) is None:
+        raise ValueError("source_fingerprint must be lowercase raw-byte SHA-256.")
+    if not isinstance(limits, LineageExtractionLimits):
+        raise TypeError("limits must be LineageExtractionLimits.")
+    paths, limit_reason = _index_ast_paths(tree, limits)
+    if limit_reason is not None:
+        return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, status=LineageFamilyStatus.RESOURCE_LIMIT, resource_limit_reason=limit_reason)
     anchors, flows, surfaces = _AnchorExtractor(paths, source_key).extract(tree)
     return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, anchors=anchors, flows=flows, surfaces=surfaces, status=LineageFamilyStatus.FRESH)
-
-
-__all__ = [
-    "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
-    "ExtractedLineageContribution",
-    "ExtractedLineageProvider",
-    "LineageExtractionLimits",
-    "ParsedLineageSourceInput",
-    "build_local_occurrence_id",
-    "extract_lineage_source_facts",
-    "parse_local_occurrence_id",
-]
+
+
+__all__ = [
+    "DEFAULT_LINEAGE_EXTRACTION_LIMITS",
+    "ExtractedLineageContribution",
+    "ExtractedLineageProvider",
+    "LineageExtractionLimits",
+    "ParsedLineageSourceInput",
+    "build_local_occurrence_id",
+    "extract_lineage_source_facts",
+    "parse_local_occurrence_id",
+]
diff --git a/contextor/core/analysis/lineage_extraction_surfaces.py b/contextor/core/analysis/lineage_extraction_surfaces.py
index a5d71d4..32fbb20 100644
--- a/contextor/core/analysis/lineage_extraction_surfaces.py
+++ b/contextor/core/analysis/lineage_extraction_surfaces.py
@@ -49,6 +49,21 @@ def observe_all_mutation(state: LineageExtractionState, node: ast.Call) -> None:
         state.invalidate_all()
 
 
+def observe_all_subscript_mutation(
+    state: LineageExtractionState,
+    node: ast.Subscript,
+    owner: str | None,
+) -> None:
+    if (
+        owner is not None
+        and state._owner_kind.get(owner) == "module"
+        and isinstance(node.ctx, (ast.Store, ast.Del))
+        and isinstance(node.value, ast.Name)
+        and node.value.id == "__all__"
+    ):
+        state.invalidate_all()
+
+
 def record_direct_public_candidates(state: LineageExtractionState, node: ast.AST, owner: str) -> None:
     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
         names = (node.name,)
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index d46e3dc..ff346a8 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -2162,3 +2162,21 @@ def test_stage_1e1_surface_id_escapes_non_identifier_literal_name_deterministica
     surface = first.surfaces[0]
     assert surface.declared_name == "a:b/c"
     assert ":n:a%3Ab%2Fc" in surface.local_id
+
+
+@pytest.mark.parametrize("source", [
+    "__all__ = ['a']\n__all__[0] = 'x'\ndef a(): pass\n",
+    "__all__ = ['a']\n__all__[:] = ['x']\ndef a(): pass\n",
+    "__all__ = ['a']\n__all__[0] += 'x'\ndef a(): pass\n",
+    "__all__ = ['a']\ndel __all__[0]\ndef a(): pass\n",
+])
+def test_stage_1e1_direct_all_subscript_mutation_suppresses_exact_surfaces(source):
+    assert _stage_1c_facts(source).surfaces == ()
+
+
+def test_stage_1e1_reading_all_subscript_preserves_exact_literal_authority():
+    facts = _stage_1c_facts("__all__ = ['a']\nx = __all__[0]\ndef a(): pass\n")
+    surface = facts.surfaces[0]
+    assert surface.declared_name == "a"
+    assert surface.kind is SurfaceKind.EXPORT
+    assert surface.confidence is LineageConfidence.CONFIRMED
~~~
