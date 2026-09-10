STATUS=BLOCKED
DEAD_PLUMBING_REMOVED=PASS: all 27 DELETE_METHODS_EXACT definitions and every self.<name> reference are absent; FINAL_IMPORTS_EXACT PASS; direct facade -> lineage_extraction_calls dependency removed.
PUBLIC_API_COMPATIBILITY=PASS: __all__ exactly matches the frozen 8-name list; every export exists; contract re-export identities are preserved; observed __module__ values remain contextor.core.analysis.lineage_extraction as established by D1.
ONE_DISPATCH_CERTIFICATION=PASS: exactly one dynamic getattr(self, f"_visit_{type(node).__name__}", None), at facade line 121; none in the eight helper modules; no NodeVisitor or ast.walk found in the nine-module family.
ONE_STATE_CERTIFICATION=PASS: exactly one LineageExtractionState() construction, in _AnchorExtractor.__init__.
ARCHITECTURE_MATRIX=PASS: all nine family modules report canonical_state=fresh, workspace_sync=verified, provenance=live, canonical_revision=555, syntax checked_and_none, collisions=0, cycles=0. Facade fan_out decreased 10 -> 9; its final outbound dependencies exclude lineage_extraction_calls. calls is consumed only by visitors. All helper outbound sets exclude facade, so no private-helper -> facade back-edge; zero fresh cycles certifies no helper cycle.
CONTEXTOR_EVIDENCE=PRE: facade revision 554, workspace_sync=verified, snapshot provenance; facade initially had direct hard edge to lineage_extraction_calls. POST: Desktop watcher revision 555; facade fresh/verified/live; syntax checked_and_none; collisions=0; cycles=0; final facade outbound total=9 with no calls edge. Family module contexts were queried for contracts,state,emit,calls,comprehensions,control,bindings,visitors at revision 555.
LIVE_EVIDENCE=Desktop watcher event after revision 554: revision=555, operation=update_file, origin=desktop_watcher, status=UPDATED, file_path=C:\Temp\Contextor_Repo\contextor\core\analysis\lineage_extraction.py, blast_radius_state=fresh, resync_required=false. No manual update_file was called.
FILES_CHANGED=contextor/core/analysis/lineage_extraction.py
TESTS_RUN=.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction_equivalence.py -q; .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py -q; .venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction.py tests/analysis/test_lineage_extraction_equivalence.py tests/test_no_double_parse.py tests/test_index_fusion.py -q; git diff --check 04a73557d0d9bb258db1b128c0ad4ce603c7e967 -- contextor/core/analysis/lineage_extraction.py
TEST_RESULTS=2 PASS; 95 PASS and 2 FAIL; 108 PASS and 2 FAIL; diff-check PASS. The two failures are test_stage_1c_occurrence_cache_reuses_same_ref and test_stage_1c_merge_frames_keeps_only_identical_occurrences in tests/analysis/test_lineage_extraction.py. Each directly invokes a facade method that D6 DELETE_METHODS_EXACT requires absent: respectively _occurrence and _merge_frames. Restoring either violates DEAD_PLUMBING_GATE; changing either test violates TEST_FREEZE. This is a real frozen-contract contradiction, so D6 cannot be FINAL_PASS without authorization to alter one of those gates.
FULL_DIFFS=
```diff
diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index b3a4f57..2249d7e 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -1,7 +1,6 @@
 from __future__ import annotations
 
 import ast
-from dataclasses import dataclass
 
 from contextor.core.analysis.state_manager import canonical_python_source_path
 from contextor.core.analysis.lineage_extraction_contracts import (
@@ -13,23 +12,17 @@ from contextor.core.analysis.lineage_extraction_contracts import (
     _FINGERPRINT_RE,
     _index_ast_paths,
     _module_name_from_source_key,
-    _resolve_import_module,
-    _source_span,
     build_local_occurrence_id,
     parse_local_occurrence_id,
 )
-from contextor.core.analysis.lineage_extraction_calls import bind_call_arguments, collect_call_arguments, current_import_info, default_flows, emit_argument_to_parameter, function_signature_evidence, parameter_anchors, register_import_binding, resolve_current_imported_callable, resolve_current_local_callable
-from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence, parameter_symbolic, return_symbolic
+from contextor.core.analysis.lineage_extraction_emit import occurrence
 from contextor.core.analysis.lineage_extraction_comprehensions import (
-    begin_comprehension,
-    finish_comprehension,
     publish_executed_walrus,
     visit_comprehension_expression,
 )
 from contextor.core.analysis.lineage_extraction_control import (
     visit_async_for,
     visit_async_with,
-    visit_block_from_frame,
     visit_except_handler,
     visit_for,
     visit_if,
@@ -42,7 +35,6 @@ from contextor.core.analysis.lineage_extraction_control import (
     visit_with,
 )
 from contextor.core.analysis.lineage_extraction_bindings import (
-    assign_target,
     runtime_bind_target,
     visit_ann_assign,
     visit_assign,
@@ -62,19 +54,13 @@ from contextor.core.analysis.lineage_extraction_visitors import (
     visit_module,
     visit_return,
 )
-from contextor.core.analysis.lineage_extraction_state import _ActiveComprehension, _CallArgumentInfo, _CallableInfo, _ImportInfo, _ParameterInfo, LineageExtractionState
+from contextor.core.analysis.lineage_extraction_state import LineageExtractionState
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
     ExtractedFlowFact,
     ExtractedLineageSourceFacts,
     ExtractedOccurrenceRef,
-    ExtractedSymbolicKind,
-    ExtractedSymbolicRef,
-    LineageConfidence,
     LineageFamilyStatus,
-    LineageRelation,
-    ParameterKind,
-    ResolutionKind,
 )
 
 
@@ -89,41 +75,6 @@ class _AnchorExtractor:
         self._visit(tree, None, None)
         return tuple(sorted(self.state.anchors)), tuple(sorted(self.state.flows))
 
-    def _add(self, kind: str, node: ast.AST, name: str | None, owner_local_id: str | None, *, ordinal: int = 0, local_kind: str | None = None) -> str:
-        return add_anchor(self.state, self.paths, kind, node, name, owner_local_id, ordinal=ordinal, local_kind=local_kind)
-
-    def _occurrence(self, kind: str, node: ast.AST, name: str | None = None, *, ordinal: int = 0) -> ExtractedOccurrenceRef:
-        return occurrence(self.state, self.paths, kind, node, name, ordinal=ordinal)
-
-    def _flow(self, *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0, dynamic_boundary: str | None = None) -> None:
-        emit_flow(self.state, self.paths, source=source, target=target, relation=relation, node=node, resolution_kind=resolution_kind, confidence=confidence, ordinal=ordinal, dynamic_boundary=dynamic_boundary)
-
-    def _frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
-        return self.state.frame(owner)
-
-    def _clone_frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
-        return self.state.clone_frame(owner)
-
-    def _replace_frame(
-        self,
-        owner: str | None,
-        frame: dict[str, ExtractedOccurrenceRef],
-    ) -> None:
-        self.state.replace_frame(owner, frame)
-
-    def _begin_comprehension(
-        self,
-        lookup_owner: str,
-        lexical_enclosing_owner: str | None,
-        effective_walrus_owner: str | None,
-    ) -> _ActiveComprehension:
-        return begin_comprehension(
-            self.state,
-            lookup_owner,
-            lexical_enclosing_owner,
-            effective_walrus_owner,
-        )
-
     def _publish_executed_walrus(
         self,
         name: str,
@@ -137,48 +88,6 @@ class _AnchorExtractor:
             target_owner,
         )
 
-    def _finish_comprehension(
-        self,
-        record: _ActiveComprehension,
-    ) -> None:
-        return finish_comprehension(
-            self.state,
-            record,
-        )
-
-    def _merge_frames(
-        self,
-        frames: tuple[dict[str, ExtractedOccurrenceRef], ...],
-    ) -> dict[str, ExtractedOccurrenceRef]:
-        return self.state.merge_frames(frames)
-
-    def _visit_block_from_frame(
-        self,
-        body: list[ast.stmt],
-        owner: str | None,
-        walrus_owner: str | None,
-        frame: dict[str, ExtractedOccurrenceRef],
-    ) -> dict[str, ExtractedOccurrenceRef]:
-        return visit_block_from_frame(
-            self.state,
-            body,
-            owner,
-            walrus_owner,
-            frame,
-            visit=self._visit,
-        )
-
-    def _blocked_names(self, owner: str | None) -> set[str]:
-        return self.state.blocked_names(owner)
-
-    def _callable_frame(self, owner: str | None) -> dict[str, _CallableInfo]:
-        return self.state.callable_frame(owner)
-
-    def _import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
-        return self.state.import_frame(owner)
-
-    def _register_import_binding(self, alias: ast.alias, owner: str | None, local_name: str, module_name: str | None, symbol_name: str | None) -> None:
-        return register_import_binding(self.state, self.paths, alias, owner, local_name, module_name, symbol_name)
     def _value(
         self,
         node: ast.AST,
@@ -187,29 +96,26 @@ class _AnchorExtractor:
     ) -> ExtractedOccurrenceRef:
         self._visit(node, owner, walrus_owner)
         if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
-            return self._occurrence("name_load", node, node.id)
+            return occurrence(
+                self.state,
+                self.paths,
+                "name_load",
+                node,
+                node.id,
+            )
         if isinstance(node, ast.Call):
-            return self._occurrence("call_result", node)
-        return self._occurrence("expression_result", node)
-
-    def _parameter_symbolic(self, callable_symbol_name: str, parameter: _ParameterInfo) -> ExtractedSymbolicRef:
-        return parameter_symbolic(self.module_name, callable_symbol_name, parameter)
-
-    def _return_symbolic(self, callable_info: _CallableInfo) -> ExtractedSymbolicRef:
-        return return_symbolic(self.module_name, callable_info)
-
-    def _resolve_current_local_callable(self, node: ast.Call, owner: str | None) -> _CallableInfo | None:
-        return resolve_current_local_callable(self.state, node, owner)
-    def _current_import_info(self, owner: str | None, local_name: str) -> _ImportInfo | None:
-        return current_import_info(self.state, owner, local_name)
-    def _resolve_current_imported_callable(self, node: ast.Call, owner: str | None) -> ExtractedSymbolicRef | None:
-        return resolve_current_imported_callable(self.state, node, owner)
-    def _collect_call_arguments(self, node: ast.Call, owner: str | None, walrus_owner: str | None) -> tuple[_CallArgumentInfo, ...]:
-        return collect_call_arguments(self.state, self.paths, node, owner, walrus_owner, value=self._value)
-    def _emit_argument_to_parameter(self, argument: _CallArgumentInfo, callable_info: _CallableInfo, parameter: _ParameterInfo) -> None:
-        return emit_argument_to_parameter(self.state, self.paths, self.module_name, argument, callable_info, parameter)
-    def _bind_call_arguments(self, arguments: tuple[_CallArgumentInfo, ...], callable_info: _CallableInfo) -> None:
-        return bind_call_arguments(self.state, self.paths, self.module_name, arguments, callable_info)
+            return occurrence(
+                self.state,
+                self.paths,
+                "call_result",
+                node,
+            )
+        return occurrence(
+            self.state,
+            self.paths,
+            "expression_result",
+            node,
+        )
 
     def _visit(self, node: ast.AST, owner_local_id: str | None, walrus_owner_local_id: str | None) -> None:
         method = getattr(self, f"_visit_{type(node).__name__}", None)
@@ -225,13 +131,6 @@ class _AnchorExtractor:
     def _visit_ClassDef(self, node: ast.ClassDef, owner: str | None, walrus_owner: str | None) -> None:
         return visit_class_def(self.state, self.paths, node, owner, walrus_owner, visit=self._visit)
 
-    def _function_signature_evidence(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, owner: str | None, walrus_owner: str | None) -> None:
-        return function_signature_evidence(node, owner, walrus_owner, visit=self._visit)
-    def _parameter_anchors(self, args: ast.arguments, owner: str, callable_symbol_name: str) -> tuple[_ParameterInfo, ...]:
-        return parameter_anchors(self.state, self.paths, self.module_name, args, owner, callable_symbol_name)
-    def _default_flows(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, callable_symbol_name: str, parameters: tuple[_ParameterInfo, ...]) -> None:
-        return default_flows(self.state, self.paths, self.module_name, node, callable_symbol_name, parameters)
-
     def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str, owner: str | None, walrus_owner: str | None) -> None:
         return visit_function(self.state, self.paths, self.module_name, node, kind, owner, walrus_owner, visit=self._visit)
 
@@ -285,15 +184,6 @@ class _AnchorExtractor:
     def _visit_Name(self, node: ast.Name, owner: str | None, _walrus_owner: str | None) -> None:
         visit_name(self.state, self.paths, node, owner)
 
-    def _assign_target(
-        self,
-        target: ast.AST,
-        source: ExtractedOccurrenceRef,
-        owner: str | None,
-        walrus_owner: str | None,
-    ) -> ExtractedOccurrenceRef | None:
-        return assign_target(self.state, self.paths, target, source, owner, walrus_owner, visit=self._visit)
-
     def _runtime_bind_target(
         self,
         target: ast.AST,
```
