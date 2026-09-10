# Contextor Stage 1E.1 corrective pass — surface authority holes

STATUS=COMPLETE_WITH_LIVE_CERTIFICATION_BLOCKED

## Exact corrective fixes

* P0.1: Surface-only deletion tombstones preserve 1A–1D lexical frames while preventing deleted bindings from authorizing default PUBLIC_SYMBOL, explicit local EXPORT, or REEXPORT. A later different binding supersedes its tombstone.
* P0.2: State-owned note_module_all_touch now invalidates explicit-all authority from module binding paths; direct supported Assign may then replace it with exact authority. Hooks cover assignment/runtime binding/store/delete/import/function/class/exception/match paths.
* P0.3: empty literal strings now invalidate literal __all__ rather than reaching the token-validating domain constructor.
* P1: surface names are percent-escaped in IDs, including colon/slash names.
* The equivalence oracle remains unchanged for anchor/flow hashes; no expected legacy hash regeneration occurred.

## Regression evidence

* Deleted local/import binding: no stale confirmed surface; later exact binding becomes confirmed local EXPORT.
* AnnAssign, walrus, import alias, for target, destructuring target for __all__ suppress fallback surfaces.
* Empty literal __all__ member is fail-closed without an exception.
* a:b/c emits deterministic escaped ID n:a%3Ab%2Fc.

## Tests

* tests/analysis/test_lineage_extraction.py -q: 189 passed.
* tests/analysis/test_lineage_extraction_equivalence.py -q: 3 passed.
* required combined focused command: 203 passed.
* git diff --check: passed; only LF-to-CRLF advisory warnings.

## Contextor / LIVE

Pre-edit revision=592, resync_required=false, and diagnostics fresh. Active MCP documentation, LIVE events, and canonical module contexts were checked; no deferred discovery tool was injected. Both changed-module contexts at revision 592 had fresh syntax diagnostics. Post-edit get_live_events(after_revision=592) returned transient_connection_failure (LIVE owner temporarily unreachable), so no matching later watcher revision/continuous post-edit cursor can be proved. Per task rule, update_file was not called. LIVE_CERTIFICATION=BLOCKED.

Static certification: one LineageExtractionState construction remains in lineage_extraction.py; no new visitor/traversal/source reread was introduced; helper has no facade import/back-edge. Pre-edit diagnostics reported cycles/collisions fresh. Post-edit MCP cycle/collision certification is blocked by the unreachable owner.

FILES_CHANGED:
* contextor/core/analysis/lineage_extraction.py
* contextor/core/analysis/lineage_extraction_bindings.py
* contextor/core/analysis/lineage_extraction_calls.py
* contextor/core/analysis/lineage_extraction_control.py
* contextor/core/analysis/lineage_extraction_emit.py
* contextor/core/analysis/lineage_extraction_state.py
* contextor/core/analysis/lineage_extraction_visitors.py
* tests/analysis/test_lineage_extraction.py
* tests/analysis/test_lineage_extraction_equivalence.py
* contextor/core/analysis/lineage_extraction_surfaces.py

## COMPLETE raw unified FULL_DIFF

~~~diff
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 63c985a..d9215e7 100644
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
@@ -57,27 +57,31 @@ from contextor.core.analysis.lineage_extraction_visitors import (
     visit_yield,
 )
 from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
+from contextor.core.analysis.lineage_extraction_surfaces import finalize_surfaces
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
     ExtractedFlowFact,
     ExtractedLineageSourceFacts,
     ExtractedOccurrenceRef,
+    ExtractedSurfaceFact,
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
-    def extract(self, tree: ast.AST) -> tuple[tuple[ExtractedAnchorFact, ...], tuple[ExtractedFlowFact, ...]]:
+
+
+class _AnchorExtractor:
+    def __init__(self, paths: dict[int, str], source_key: str) -> None:
+        self.paths = paths
+        self.source_key = source_key
+        self.module_name = _module_name_from_source_key(source_key)
+        self.state = LineageExtractionState()
+
+    def extract(self, tree: ast.AST) -> tuple[tuple[ExtractedAnchorFact, ...], tuple[ExtractedFlowFact, ...], tuple[ExtractedSurfaceFact, ...]]:
         self._visit(tree, None, None)
         finalize_captures(self.state, self.paths)
-        return tuple(sorted(self.state.anchors)), tuple(sorted(self.state.flows))
-
+        module_owner = next(anchor.local_id for anchor in self.state.anchors if anchor.kind == "module")
+        finalize_surfaces(self.state, self.paths, self.module_name, module_owner)
+        return tuple(sorted(self.state.anchors)), tuple(sorted(self.state.flows)), tuple(sorted(self.state.surfaces))
+
     def _publish_executed_walrus(
         self,
         name: str,
@@ -90,15 +94,15 @@ class _AnchorExtractor:
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
@@ -119,33 +123,33 @@ class _AnchorExtractor:
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
 
@@ -154,17 +158,17 @@ class _AnchorExtractor:
 
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
@@ -177,115 +181,115 @@ class _AnchorExtractor:
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
-
-    def _runtime_bind_target(
-        self,
-        target: ast.AST,
-        owner: str | None,
-        walrus_owner: str | None,
-    ) -> None:
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
-    anchors, flows = _AnchorExtractor(paths, source_key).extract(tree)
-    return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, anchors=anchors, flows=flows, surfaces=(), status=LineageFamilyStatus.FRESH)
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
+    anchors, flows, surfaces = _AnchorExtractor(paths, source_key).extract(tree)
+    return ExtractedLineageSourceFacts(source_key=source_key, source_fingerprint=source_fingerprint, anchors=anchors, flows=flows, surfaces=surfaces, status=LineageFamilyStatus.FRESH)
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
diff --git a/contextor/core/analysis/lineage_extraction_bindings.py b/contextor/core/analysis/lineage_extraction_bindings.py
index 2868b56..f356ed5 100644
--- a/contextor/core/analysis/lineage_extraction_bindings.py
+++ b/contextor/core/analysis/lineage_extraction_bindings.py
@@ -5,6 +5,7 @@ from collections.abc import Callable
 
 from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence
 from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
+from contextor.core.analysis.lineage_extraction_surfaces import observe_all_assignment, observe_all_augassign
 from contextor.core.domain.lineage_facts import (
     ExtractedOccurrenceRef,
     LineageConfidence,
@@ -27,9 +28,11 @@ def visit_name(
     if isinstance(node.ctx, ast.Store):
         add_anchor(state, paths, "binding", node, node.id, owner)
         state.declare_local(owner, node.id)
+        state.note_module_all_touch(owner, node.id)
         return
     if isinstance(node.ctx, ast.Del):
         state.declare_local(owner, node.id)
+        state.record_module_surface_delete(owner, node.id)
         return
     if isinstance(node.ctx, ast.Load):
         load = occurrence(state, paths, "name_load", node, node.id)
@@ -82,6 +85,7 @@ def assign_target(
     if target.id in state.blocked_names(owner):
         return None
     state.frame(owner)[target.id] = binding
+    state.note_module_all_touch(owner, target.id)
     callable_info = state._callable_values.get(source.local_id)
     if callable_info is not None:
         state._callables_by_binding[binding.local_id] = callable_info
@@ -122,6 +126,7 @@ def runtime_bind_target(
             target.id,
         )
         state.frame(owner)[target.id] = binding
+        state.note_module_all_touch(owner, target.id)
         emit_flow(
             state,
             paths,
@@ -169,7 +174,7 @@ def visit_assign(
 ) -> None:
     source = value(node.value, owner, walrus_owner)
     for target in node.targets:
-        assign_target(
+        binding = assign_target(
             state,
             paths,
             target,
@@ -178,6 +183,8 @@ def visit_assign(
             walrus_owner,
             visit=visit,
         )
+        if owner is not None and state._owner_kind.get(owner) == "module" and isinstance(target, ast.Name) and target.id == "__all__" and binding is not None:
+            observe_all_assignment(state, node, binding)
 
 
 def visit_ann_assign(
@@ -247,6 +254,10 @@ def visit_aug_assign(
     value: ValueFn,
     visit: VisitFn,
 ) -> None:
+    if isinstance(node.target, ast.Name):
+        state.note_module_all_touch(owner, node.target.id)
+    if owner is not None and state._owner_kind.get(owner) == "module" and isinstance(node.target, ast.Name) and node.target.id == "__all__":
+        observe_all_augassign(state)
     if not isinstance(node.target, ast.Name):
         visit(node.target, owner, walrus_owner)
         value(node.value, owner, walrus_owner)
diff --git a/contextor/core/analysis/lineage_extraction_calls.py b/contextor/core/analysis/lineage_extraction_calls.py
index 2eaaf36..0e7c5bb 100644
--- a/contextor/core/analysis/lineage_extraction_calls.py
+++ b/contextor/core/analysis/lineage_extraction_calls.py
@@ -15,6 +15,7 @@ def register_import_binding(state: LineageExtractionState, paths: dict[int, str]
     state.declare_local(owner, local_name)
     if local_name in state.blocked_names(owner): return
     state.frame(owner)[local_name] = ExtractedOccurrenceRef(binding_id)
+    state.note_module_all_touch(owner, local_name)
     if module_name is not None: state.import_frame(owner)[local_name] = _ImportInfo(module_name, symbol_name, binding_id)
 
 
diff --git a/contextor/core/analysis/lineage_extraction_control.py b/contextor/core/analysis/lineage_extraction_control.py
index c1e16f7..61ba673 100644
--- a/contextor/core/analysis/lineage_extraction_control.py
+++ b/contextor/core/analysis/lineage_extraction_control.py
@@ -121,6 +121,7 @@ def visit_except_handler(state: LineageExtractionState, paths: dict[int, str], n
         if alias_name not in state.blocked_names(owner):
             source = occurrence(state, paths, "runtime_bound_local", node, alias_name)
             state.frame(owner)[alias_name] = binding
+            state.note_module_all_touch(owner, alias_name)
             emit_flow(state, paths, source=source, target=binding, relation=LineageRelation.ASSIGNS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
     for child in node.body:
         visit(child, owner, walrus_owner)
@@ -151,12 +152,14 @@ def visit_match_as(state: LineageExtractionState, paths: dict[int, str], node: a
     if node.name is not None:
         add_anchor(state, paths, "binding", node, node.name, owner)
         state.declare_local(owner, node.name)
+        state.note_module_all_touch(owner, node.name)
 
 
 def visit_match_star(state: LineageExtractionState, paths: dict[int, str], node: ast.MatchStar, owner: str | None) -> None:
     if node.name is not None:
         add_anchor(state, paths, "binding", node, node.name, owner)
         state.declare_local(owner, node.name)
+        state.note_module_all_touch(owner, node.name)
 
 
 def visit_match_mapping(state: LineageExtractionState, paths: dict[int, str], node: ast.MatchMapping, owner: str | None, walrus_owner: str | None, *, visit: VisitFn) -> None:
@@ -167,3 +170,4 @@ def visit_match_mapping(state: LineageExtractionState, paths: dict[int, str], no
     if node.rest is not None:
         add_anchor(state, paths, "binding", node, node.rest, owner)
         state.declare_local(owner, node.rest)
+        state.note_module_all_touch(owner, node.rest)
diff --git a/contextor/core/analysis/lineage_extraction_emit.py b/contextor/core/analysis/lineage_extraction_emit.py
index 5e13328..13a5433 100644
--- a/contextor/core/analysis/lineage_extraction_emit.py
+++ b/contextor/core/analysis/lineage_extraction_emit.py
@@ -1,10 +1,11 @@
 from __future__ import annotations
 
 import ast
+from urllib.parse import quote
 
 from contextor.core.analysis.lineage_extraction_contracts import _source_span, build_local_occurrence_id
 from contextor.core.analysis.lineage_extraction_state import _CallableInfo, _ParameterInfo, LineageExtractionState
-from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ExtractedSymbolicKind, ExtractedSymbolicRef, LineageConfidence, LineageRelation, ResolutionKind
+from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ExtractedSurfaceFact, ExtractedSymbolicKind, ExtractedSymbolicRef, LineageConfidence, LineageRelation, ResolutionKind, SurfaceDeclarationEvidence, SurfaceKind
 
 
 def add_anchor(state: LineageExtractionState, paths: dict[int, str], kind: str, node: ast.AST, name: str | None, owner_local_id: str | None, *, ordinal: int = 0, local_kind: str | None = None) -> str:
@@ -37,6 +38,14 @@ def emit_flow(state: LineageExtractionState, paths: dict[int, str], *, source, t
     state.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence, dynamic_boundary=dynamic_boundary))
 
 
+def emit_surface(state: LineageExtractionState, paths: dict[int, str], *, kind: SurfaceKind, exposed, node: ast.AST, declared_name: str, resolution_kind: ResolutionKind, confidence: LineageConfidence, declaration_evidence: SurfaceDeclarationEvidence, ordinal: int = 0) -> None:
+    local_id = f"surface:v1:{kind.value}:{paths[id(node)]}:i:{ordinal}:n:{quote(declared_name, safe='')}"
+    if local_id in state._surface_ids:
+        raise ValueError(f"Duplicate lineage surface id: {local_id}")
+    state._surface_ids.add(local_id)
+    state.surfaces.append(ExtractedSurfaceFact(local_id, kind, exposed, _source_span(node), resolution_kind, confidence, declared_name, declaration_evidence=declaration_evidence))
+
+
 def parameter_symbolic(module_name: str, callable_symbol_name: str, parameter: _ParameterInfo) -> ExtractedSymbolicRef:
     return ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, module_name, callable_symbol_name, parameter.local_id)
 
diff --git a/contextor/core/analysis/lineage_extraction_state.py b/contextor/core/analysis/lineage_extraction_state.py
index 3727043..103a1e9 100644
--- a/contextor/core/analysis/lineage_extraction_state.py
+++ b/contextor/core/analysis/lineage_extraction_state.py
@@ -3,7 +3,7 @@ from __future__ import annotations
 import ast
 from dataclasses import dataclass, field
 
-from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ParameterKind
+from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ExtractedSurfaceFact, ParameterKind
 
 
 @dataclass(frozen=True)
@@ -64,8 +64,10 @@ class _CaptureRequest:
 class LineageExtractionState:
     anchors: list[ExtractedAnchorFact] = field(default_factory=list)
     flows: list[ExtractedFlowFact] = field(default_factory=list)
+    surfaces: list[ExtractedSurfaceFact] = field(default_factory=list)
     _ids: set[str] = field(default_factory=set)
     _flow_ids: set[str] = field(default_factory=set)
+    _surface_ids: set[str] = field(default_factory=set)
     _occurrences: dict[tuple[str, int, str | None, int], ExtractedOccurrenceRef] = field(default_factory=dict)
     _bindings: dict[str | None, dict[str, ExtractedOccurrenceRef]] = field(default_factory=dict)
     _callables: dict[str | None, dict[str, _CallableInfo]] = field(default_factory=dict)
@@ -86,6 +88,50 @@ class LineageExtractionState:
     _declared_locals: dict[str, set[str]] = field(default_factory=dict)
     _capture_requests: dict[str, _CaptureRequest] = field(default_factory=dict)
     _lexical_cells: dict[tuple[str, str], ExtractedOccurrenceRef] = field(default_factory=dict)
+    _module_direct_statement: ast.AST | None = None
+    _module_public_candidates: dict[str, tuple[ExtractedOccurrenceRef, ast.AST]] = field(default_factory=dict)
+    _all_status: str = "absent"
+    _all_binding: ExtractedOccurrenceRef | None = None
+    _all_items: tuple[tuple[str, ast.Constant], ...] = ()
+    _module_surface_deleted_bindings: dict[str, str | None] = field(default_factory=dict)
+
+    def begin_module_statement(self, node: ast.AST) -> None:
+        self._module_direct_statement = node
+
+    def end_module_statement(self) -> None:
+        self._module_direct_statement = None
+
+    def is_direct_module_statement(self, node: ast.AST) -> bool:
+        return self._module_direct_statement is node
+
+    def record_module_public_candidate(self, name: str, binding: ExtractedOccurrenceRef, node: ast.AST) -> None:
+        self._module_public_candidates[name] = (binding, node)
+
+    def record_all_exact(self, binding: ExtractedOccurrenceRef, items: tuple[tuple[str, ast.Constant], ...]) -> None:
+        self._all_status = "exact"
+        self._all_binding = binding
+        self._all_items = items
+
+    def invalidate_all(self) -> None:
+        self._all_status = "dynamic_or_ambiguous"
+        self._all_binding = None
+        self._all_items = ()
+
+    def note_module_all_touch(self, owner: str | None, name: str) -> None:
+        if owner is not None and self._owner_kind.get(owner) == "module" and name == "__all__":
+            self.invalidate_all()
+
+    def record_module_surface_delete(self, owner: str | None, name: str) -> None:
+        if owner is not None and self._owner_kind.get(owner) == "module":
+            current = self.frame(owner).get(name)
+            self._module_surface_deleted_bindings[name] = None if current is None else current.local_id
+            self.note_module_all_touch(owner, name)
+
+    def current_module_surface_binding(self, owner: str, name: str) -> ExtractedOccurrenceRef | None:
+        current = self.frame(owner).get(name)
+        if current is not None and current.local_id == self._module_surface_deleted_bindings.get(name):
+            return None
+        return current
 
     def frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
         return self._bindings.setdefault(owner, {})
diff --git a/contextor/core/analysis/lineage_extraction_visitors.py b/contextor/core/analysis/lineage_extraction_visitors.py
index 5d1b18f..8a26c16 100644
--- a/contextor/core/analysis/lineage_extraction_visitors.py
+++ b/contextor/core/analysis/lineage_extraction_visitors.py
@@ -25,6 +25,7 @@ from contextor.core.analysis.lineage_extraction_state import (
     _CallableInfo,
     LineageExtractionState,
 )
+from contextor.core.analysis.lineage_extraction_surfaces import observe_all_mutation, record_direct_public_candidates
 from contextor.core.domain.lineage_facts import (
     ExtractedOccurrenceRef,
     LineageConfidence,
@@ -55,7 +56,12 @@ def visit_module(
     state.register_owner(module_id, None, "module", node)
     state.frame(module_id)
     for child in node.body:
-        visit(child, module_id, None)
+        state.begin_module_statement(child)
+        try:
+            visit(child, module_id, None)
+            record_direct_public_candidates(state, child, module_id)
+        finally:
+            state.end_module_statement()
 
 
 def visit_class_def(
@@ -84,6 +90,7 @@ def visit_class_def(
         visit(child, class_id, None)
     if node.name not in state.blocked_names(owner):
         state.frame(owner)[node.name] = ExtractedOccurrenceRef(class_id)
+        state.note_module_all_touch(owner, node.name)
 
 
 def visit_function(
@@ -150,6 +157,7 @@ def visit_function(
         state.frame(owner)[node.name] = ExtractedOccurrenceRef(
             function_id
         )
+        state.note_module_all_touch(owner, node.name)
 
 
 def visit_lambda(
@@ -286,6 +294,8 @@ def visit_call(
     visit: VisitFn,
     value: ValueFn,
 ) -> None:
+    if owner is not None and state._owner_kind.get(owner) == "module":
+        observe_all_mutation(state, node)
     visit(node.func, owner, walrus_owner)
     callable_info = resolve_current_local_callable(
         state,
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index bcfe909..d46e3dc 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -23,6 +23,8 @@ from contextor.core.domain.lineage_facts import (
     LineageFamilyStatus,
     LineageRelation,
     ResolutionKind,
+    SurfaceDeclarationEvidence,
+    SurfaceKind,
 )
 from contextor.core.source import parse_source_with_fingerprint
 from contextor.core.symbol_engine import indexer as indexer_module
@@ -113,6 +115,10 @@ def _stage_1c_named(facts, kind, name):
     return [item for item in facts.anchors if item.kind == kind and parse_local_occurrence_id(item.local_id)[3] == name]
 
 
+def _surfaces_by_name(facts):
+    return {surface.declared_name: surface for surface in facts.surfaces}
+
+
 def _stage_1c_runtime_assignment(facts, name):
     return next(
         flow
@@ -1115,7 +1121,8 @@ def test_extraction_is_deterministic_source_local_and_has_parameter_lineage(monk
     second = extract_lineage_source_facts(tree, source_key="pkg/mod.py", source_fingerprint=FINGERPRINT)
     assert first == second
     assert first.status is LineageFamilyStatus.FRESH
-    assert first.flows and first.surfaces == ()
+    assert first.flows
+    assert {surface.declared_name for surface in first.surfaces} == {"value", "run"}
     assert len({item.local_id for item in first.anchors}) == len(first.anchors)
     module = sys.modules["contextor.core.analysis.lineage_extraction"]
     assert "PersistentIdentityRegistry" not in vars(module)
@@ -1247,7 +1254,7 @@ def test_incremental_preparation_carries_transient_lineage_and_errors_do_not(tmp
     path.write_text("value = 1\n", encoding="utf-8")
     prepared = prepare_source_update(file_path=path, module_path="pkg", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="pkg.py")
     assert not prepared.has_error and prepared.extracted_lineage_facts is not None
-    assert prepared.extracted_lineage_facts.surfaces == ()
+    assert [surface.declared_name for surface in prepared.extracted_lineage_facts.surfaces] == ["value"]
     path.write_text("def broken(:\n", encoding="utf-8")
     broken = prepare_source_update(file_path=path, module_path="pkg", is_new=True, old_module=None, old_artifacts=None, old_usage=None, source_key="pkg.py")
     assert broken.has_error and broken.error_status == "SYNTAX_ERROR" and broken.extracted_lineage_facts is None
@@ -2023,3 +2030,135 @@ def test_stage_1d4_o_existing_callable_facts_remain_and_callback_relations_are_a
     facts = _stage_1c_facts("def apply(callback): callback()\ndef f(): return 1\ng=f\napply(g)\nresult=g()\n")
     assert len(_stage_1d4_flows(facts, LineageRelation.CALLBACK_REGISTERS)) == 1
     assert _stage_1c_call_result_flows(facts)[-1].resolution_kind is ResolutionKind.CALL_EXACT
+
+
+def test_stage_1e1_default_module_surfaces_cover_supported_public_families_only():
+    facts = _stage_1c_facts("def f(): pass\nasync def af(): pass\nclass C: pass\nCONST = 1\n_private = 2\ndef outer():\n def nested(): pass\n local = 1\n")
+    surfaces = _surfaces_by_name(facts)
+    assert set(surfaces) == {"f", "af", "C", "CONST", "outer"}
+    assert all(surface.kind is SurfaceKind.PUBLIC_SYMBOL for surface in surfaces.values())
+    assert all(surface.resolution_kind is ResolutionKind.PYTHON_NAME_CONVENTION for surface in surfaces.values())
+    assert all(surface.confidence is LineageConfidence.INFERRED for surface in surfaces.values())
+    assert all(surface.declaration_evidence is SurfaceDeclarationEvidence.STATIC_DECLARATION for surface in surfaces.values())
+
+
+def test_stage_1e1_later_literal_all_overrides_defaults_and_reuses_local_anchor():
+    facts = _stage_1c_facts("def a(): pass\ndef b(): pass\n__all__ = ['a', 'a']\n")
+    assert [surface.declared_name for surface in facts.surfaces] == ["a"]
+    surface = facts.surfaces[0]
+    assert surface.kind is SurfaceKind.EXPORT
+    assert surface.exposed == ExtractedOccurrenceRef(_stage_1c_named(facts, "function", "a")[0].local_id)
+    assert surface.resolution_kind is ResolutionKind.LITERAL_CONTAINER_EXACT
+    assert surface.confidence is LineageConfidence.CONFIRMED
+    assert surface.declaration_evidence is SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION
+
+
+def test_stage_1e1_literal_all_allows_private_and_unresolved_symbolic_name():
+    facts = _stage_1c_facts("def _private(): pass\n__all__ = ['_private', 'missing']\n")
+    surfaces = _surfaces_by_name(facts)
+    assert surfaces["_private"].kind is SurfaceKind.EXPORT
+    missing = surfaces["missing"]
+    assert missing.kind is SurfaceKind.EXPORT
+    assert isinstance(missing.exposed, ExtractedSymbolicRef)
+    assert missing.exposed.kind is ExtractedSymbolicKind.PUBLIC_TARGET
+    assert missing.exposed.module_name == "pkg" and missing.exposed.symbol_name == "missing"
+    assert missing.resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert missing.confidence is LineageConfidence.UNRESOLVED
+    assert not [flow for flow in facts.flows if flow.relation in {LineageRelation.EXPOSES, LineageRelation.DECLARES_PUBLIC_NAMES}]
+
+
+@pytest.mark.parametrize("source_key, source", [
+    ("pkg.py", "from provider import f as public\n__all__ = ['public']\n"),
+    ("pkg/sub/mod.py", "from ..provider import f as public\n__all__ = ['public']\n"),
+])
+def test_stage_1e1_explicit_from_import_reexport_uses_current_binding(source_key, source):
+    facts = _stage_1c_facts_at(source, source_key)
+    surface = facts.surfaces[0]
+    assert surface.kind is SurfaceKind.REEXPORT
+    assert surface.resolution_kind is ResolutionKind.IMPORT_EXACT
+    assert surface.confidence is LineageConfidence.CONFIRMED
+    assert surface.declaration_evidence is SurfaceDeclarationEvidence.STATIC_DECLARATION
+    assert surface.exposed == ExtractedOccurrenceRef(_stage_1c_named(facts, "import_binding", "public")[0].local_id)
+
+
+def test_stage_1e1_rebound_import_is_local_export_not_reexport():
+    facts = _stage_1c_facts("from provider import f as public\npublic = 1\n__all__ = ['public']\n")
+    surface = facts.surfaces[0]
+    assert surface.kind is SurfaceKind.EXPORT
+    assert surface.resolution_kind is ResolutionKind.LITERAL_CONTAINER_EXACT
+    assert surface.exposed == ExtractedOccurrenceRef(_stage_1c_named(facts, "binding", "public")[-1].local_id)
+
+
+@pytest.mark.parametrize("source", [
+    "__all__ = ['a']\n__all__ += ['b']\ndef a(): pass\n",
+    "__all__ = ['a'] + ['b']\ndef a(): pass\n",
+    "__all__ = [*names]\ndef a(): pass\n",
+    "__all__ = [name for name in names]\ndef a(): pass\n",
+    "__all__ = build_exports()\ndef a(): pass\n",
+    "__all__ = ['a']\n__all__.append('b')\ndef a(): pass\n",
+    "__all__ = ['a']\ndel __all__\ndef a(): pass\n",
+    "if cond:\n __all__ = ['a']\ndef a(): pass\n",
+])
+def test_stage_1e1_dynamic_or_ambiguous_all_suppresses_all_surfaces(source):
+    assert _stage_1c_facts(source).surfaces == ()
+
+
+def test_stage_1e1_multiple_literal_all_uses_only_last_authoritative_binding():
+    facts = _stage_1c_facts("def a(): pass\ndef b(): pass\n__all__ = ['a']\n__all__ = ['b']\n")
+    assert [surface.declared_name for surface in facts.surfaces] == ["b"]
+
+
+def test_stage_1e1_plain_import_is_not_confirmed_reexport():
+    facts = _stage_1c_facts("import provider as public\n__all__ = ['public']\n")
+    surface = facts.surfaces[0]
+    assert surface.kind is SurfaceKind.EXPORT
+    assert surface.resolution_kind is ResolutionKind.UNRESOLVED_NAME
+    assert isinstance(surface.exposed, ExtractedSymbolicRef)
+
+
+def test_stage_1e1_entrypoint_and_callback_registration_do_not_create_surface_kinds():
+    facts = _stage_1c_facts("if __name__ == '__main__':\n main()\ndef apply(callback): callback()\ndef f(): pass\napply(f)\n")
+    assert not [surface for surface in facts.surfaces if surface.kind in {SurfaceKind.ENTRYPOINT, SurfaceKind.REGISTRATION}]
+
+
+@pytest.mark.parametrize("source", [
+    "x = 1\ndel x\n",
+    "x = 1\ndel x\n__all__ = ['x']\n",
+    "from provider import x\ndel x\n__all__ = ['x']\n",
+])
+def test_stage_1e1_deleted_module_binding_never_retains_surface_authority(source):
+    facts = _stage_1c_facts(source)
+    assert not [surface for surface in facts.surfaces if surface.confidence is LineageConfidence.CONFIRMED]
+    assert not [surface for surface in facts.surfaces if surface.kind is SurfaceKind.PUBLIC_SYMBOL]
+
+
+def test_stage_1e1_later_binding_supersedes_surface_delete_tombstone():
+    facts = _stage_1c_facts("x = 1\ndel x\nx = 2\n__all__ = ['x']\n")
+    surface = facts.surfaces[0]
+    assert surface.kind is SurfaceKind.EXPORT
+    assert surface.confidence is LineageConfidence.CONFIRMED
+    assert surface.exposed == ExtractedOccurrenceRef(_stage_1c_named(facts, "binding", "x")[-1].local_id)
+
+
+@pytest.mark.parametrize("source", [
+    "__all__: list[str] = ['a']\ndef a(): pass\n",
+    "(__all__ := ['a'])\ndef a(): pass\n",
+    "import provider as __all__\ndef a(): pass\n",
+    "for __all__ in values: pass\ndef a(): pass\n",
+    "[__all__] = [['a']]\ndef a(): pass\n",
+])
+def test_stage_1e1_non_assign_all_touches_suppress_default_fallback(source):
+    assert _stage_1c_facts(source).surfaces == ()
+
+
+def test_stage_1e1_empty_literal_all_member_fails_closed_without_domain_error():
+    assert _stage_1c_facts("__all__ = ['']\ndef a(): pass\n").surfaces == ()
+
+
+def test_stage_1e1_surface_id_escapes_non_identifier_literal_name_deterministically():
+    first = _stage_1c_facts("__all__ = ['a:b/c']\n")
+    second = _stage_1c_facts("__all__ = ['a:b/c']\n")
+    assert first == second
+    surface = first.surfaces[0]
+    assert surface.declared_name == "a:b/c"
+    assert ":n:a%3Ab%2Fc" in surface.local_id
diff --git a/tests/analysis/test_lineage_extraction_equivalence.py b/tests/analysis/test_lineage_extraction_equivalence.py
index 6605ac7..541a7ba 100644
--- a/tests/analysis/test_lineage_extraction_equivalence.py
+++ b/tests/analysis/test_lineage_extraction_equivalence.py
@@ -28,7 +28,17 @@ def _canonical(value):
     raise TypeError(f"Unsupported lineage equivalence value: {type(value)!r}")
 
 
-def _hash_result(source: str, source_key: str, limits=None) -> str:
+def _hash_value(value) -> str:
+    oracle_bytes = json.dumps(
+        _canonical(value),
+        ensure_ascii=False,
+        sort_keys=True,
+        separators=(",", ":"),
+    ).encode("utf-8")
+    return hashlib.sha256(oracle_bytes).hexdigest()
+
+
+def _result(source: str, source_key: str, limits=None):
     source_fingerprint = hashlib.sha256(source.encode("utf-8")).hexdigest()
     result = lineage_extraction.extract_lineage_source_facts(
         ast.parse(source),
@@ -36,13 +46,11 @@ def _hash_result(source: str, source_key: str, limits=None) -> str:
         source_fingerprint=source_fingerprint,
         **({} if limits is None else {"limits": limits}),
     )
-    oracle_bytes = json.dumps(
-        _canonical(result),
-        ensure_ascii=False,
-        sort_keys=True,
-        separators=(",", ":"),
-    ).encode("utf-8")
-    return hashlib.sha256(oracle_bytes).hexdigest()
+    return result
+
+
+def _hash_result(source: str, source_key: str, limits=None) -> str:
+    return _hash_value(_result(source, source_key, limits))
 
 
 _CORPUS = {
@@ -120,17 +128,24 @@ _CORPUS = {
 
 
 EXPECTED_HASHES = {
-    "async_yield": "110cd0c1d520261bffe673d6e0f1df573b68ed4653be674bcb762faacdf27bf9",
+    "async_yield": "57fe7c8ab6b6468031df1a70efa1d66320485207edf99912959977059166dab7",
     "comprehension_runtime_walrus": "35f7e091b7361051933afa6ae125eabb35b0e46776960955d1d45b0826d531e9",
     "if_for_frame_merge": "f27318c046fcadc2946c58e2e56f324b8a01fb563bd627ec7f85319c2b435b7a",
     "imports_alias_wildcard": "7fbd16baf177be5d965c212678763b9a123978e62ba711950602fab6bf9ccec8",
     "relative_import": "44e82ef594399306de449f12a46d3c8bf463d47050f454537f5c2630f976ca95",
     "resource_limit": "40c592a9bfb86c5f6d4fe747fa2714a92794dafbc204e601ea4b475c07e06adb",
-    "signature_defaults_local_call": "4d6984e8211918d2e84e976d5fda32f59aed9247d52821cafc688242c6f6533b",
+    "signature_defaults_local_call": "97a3964dd7208f83b8200c12e7732e685ffde29f79ca7a1c001c69b2989a0122",
     "try_except_finally_match": "ce25c00652779c30e47b06499408efe78515eda802cdd88aa2650fda6757c60f",
 }
 
 
+LEGACY_ANCHOR_FLOW_HASHES = {
+    **EXPECTED_HASHES,
+    "async_yield": "110cd0c1d520261bffe673d6e0f1df573b68ed4653be674bcb762faacdf27bf9",
+    "signature_defaults_local_call": "4d6984e8211918d2e84e976d5fda32f59aed9247d52821cafc688242c6f6533b",
+}
+
+
 def test_lineage_extraction_equivalence_oracle() -> None:
     assert {
         name: _hash_result(source, source_key, limits)
@@ -138,6 +153,13 @@ def test_lineage_extraction_equivalence_oracle() -> None:
     } == EXPECTED_HASHES
 
 
+def test_lineage_extraction_surface_delta_preserves_legacy_anchors_and_flows() -> None:
+    assert {
+        name: _hash_value(dataclasses.replace(_result(source, source_key, limits), surfaces=()))
+        for name, (source, source_key, limits) in _CORPUS.items()
+    } == LEGACY_ANCHOR_FLOW_HASHES
+
+
 def test_lineage_extraction_public_compatibility() -> None:
     assert lineage_extraction.__all__ == [
         "DEFAULT_LINEAGE_EXTRACTION_LIMITS",

diff --git a/contextor/core/analysis/lineage_extraction_surfaces.py b/contextor/core/analysis/lineage_extraction_surfaces.py
new file mode 100644
index 0000000..a5d71d4
--- /dev/null
+++ b/contextor/core/analysis/lineage_extraction_surfaces.py
@@ -0,0 +1,87 @@
+from __future__ import annotations
+
+import ast
+
+from contextor.core.analysis.lineage_extraction_emit import emit_surface
+from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
+from contextor.core.domain.lineage_facts import (
+    ExtractedSymbolicKind,
+    ExtractedSymbolicRef,
+    LineageConfidence,
+    ResolutionKind,
+    SurfaceDeclarationEvidence,
+    SurfaceKind,
+)
+
+
+def _literal_all_items(node: ast.Assign) -> tuple[tuple[str, ast.Constant], ...] | None:
+    if not isinstance(node.value, (ast.List, ast.Tuple)):
+        return None
+    items: list[tuple[str, ast.Constant]] = []
+    for item in node.value.elts:
+        if not isinstance(item, ast.Constant) or not isinstance(item.value, str) or not item.value:
+            return None
+        items.append((item.value, item))
+    return tuple(items)
+
+
+def observe_all_assignment(state: LineageExtractionState, node: ast.Assign, binding) -> None:
+    if not state.is_direct_module_statement(node):
+        state.invalidate_all()
+        return
+    items = _literal_all_items(node)
+    if items is None:
+        state.invalidate_all()
+        return
+    state.record_all_exact(binding, items)
+
+
+def observe_all_augassign(state: LineageExtractionState) -> None:
+    state.invalidate_all()
+
+
+def observe_all_delete(state: LineageExtractionState) -> None:
+    state.invalidate_all()
+
+
+def observe_all_mutation(state: LineageExtractionState, node: ast.Call) -> None:
+    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "__all__":
+        state.invalidate_all()
+
+
+def record_direct_public_candidates(state: LineageExtractionState, node: ast.AST, owner: str) -> None:
+    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
+        names = (node.name,)
+    elif isinstance(node, ast.Assign):
+        names = tuple(target.id for target in node.targets if isinstance(target, ast.Name) and target.id != "__all__")
+    else:
+        return
+    frame = state.frame(owner)
+    for name in names:
+        binding = frame.get(name)
+        if binding is not None:
+            state.record_module_public_candidate(name, binding, node)
+
+
+def finalize_surfaces(state: LineageExtractionState, paths: dict[int, str], module_name: str, module_owner: str) -> None:
+    if state._all_status == "exact" and state._all_binding == state.current_module_surface_binding(module_owner, "__all__"):
+        seen: set[str] = set()
+        for ordinal, (name, item) in enumerate(state._all_items):
+            if name in seen:
+                continue
+            seen.add(name)
+            current = state.current_module_surface_binding(module_owner, name)
+            candidate = state._module_public_candidates.get(name)
+            imported = state.import_frame(module_owner).get(name)
+            if candidate is not None and candidate[0] == current:
+                emit_surface(state, paths, kind=SurfaceKind.EXPORT, exposed=current, node=item, declared_name=name, resolution_kind=ResolutionKind.LITERAL_CONTAINER_EXACT, confidence=LineageConfidence.CONFIRMED, declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ordinal=ordinal)
+            elif current is not None and imported is not None and imported.symbol_name is not None and imported.binding_id == current.local_id:
+                emit_surface(state, paths, kind=SurfaceKind.REEXPORT, exposed=current, node=item, declared_name=name, resolution_kind=ResolutionKind.IMPORT_EXACT, confidence=LineageConfidence.CONFIRMED, declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION, ordinal=ordinal)
+            else:
+                emit_surface(state, paths, kind=SurfaceKind.EXPORT, exposed=ExtractedSymbolicRef(ExtractedSymbolicKind.PUBLIC_TARGET, module_name, name), node=item, declared_name=name, resolution_kind=ResolutionKind.UNRESOLVED_NAME, confidence=LineageConfidence.UNRESOLVED, declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ordinal=ordinal)
+        return
+    if state._all_status != "absent":
+        return
+    for ordinal, (name, (binding, node)) in enumerate(sorted(state._module_public_candidates.items())):
+        if name and not name.startswith("_") and state.current_module_surface_binding(module_owner, name) == binding:
+            emit_surface(state, paths, kind=SurfaceKind.PUBLIC_SYMBOL, exposed=binding, node=node, declared_name=name, resolution_kind=ResolutionKind.PYTHON_NAME_CONVENTION, confidence=LineageConfidence.INFERRED, declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION, ordinal=ordinal)
~~~
