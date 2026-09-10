STATUS=BLOCKED

CONTEXTOR_EVIDENCE=Pre-edit Contextor edit-context was fresh/verified at revision 530; active and deferred Contextor pools were inspected. No post-edit architecture certification was run because the mandatory frozen-suite gate failed before completion.

STATE_OWNERSHIP=Partial implementation created LineageExtractionState as the single holder of mutable fields and moved the five private records. However, acceptance cannot be completed under the frozen-test/no-properties contradiction below.

EMISSION_OWNERSHIP=Partial implementation created lineage_extraction_emit.py and converted facade emission methods to forwarding adapters.

DISPATCH_INVARIANT=No dispatch code was moved or changed.

ORACLE=PASS before D2 edits: 2 passed in 0.79s. The D1 oracle file and EXPECTED_HASHES were not modified.

NO_DUPLICATES=Not certified because implementation is blocked before final textual/architecture verification.

FILES_CHANGED=contextor/core/analysis/lineage_extraction.py; contextor/core/analysis/lineage_extraction_state.py; contextor/core/analysis/lineage_extraction_emit.py; walkthrough.md.

TESTS_RUN=.venv\Scripts\python.exe -m pytest tests/analysis/test_lineage_extraction_equivalence.py tests/analysis/test_lineage_extraction.py -q; git diff --check -- contextor/core/analysis/lineage_extraction.py contextor/core/analysis/lineage_extraction_state.py contextor/core/analysis/lineage_extraction_emit.py

TEST_RESULTS=1 failed, 98 passed. The frozen existing test tests/analysis/test_lineage_extraction.py::test_stage_1c_occurrence_cache_reuses_same_ref directly asserts len(extractor._ids) == 1. D2 simultaneously requires extractor __dict__ contain only paths/source_key/module_name/state and expressly bans compatibility @property for old state fields. With _ids moved into state, the frozen test necessarily raises AttributeError. Adding a property violates NO_PROPERTIES and state ownership; changing the test violates FILES_FROZEN. Direction is required: authorize changing that private-test assertion to extractor.state._ids, or authorize the forbidden compatibility property.

FULL_DIFFS=
+diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 6227c9a..7b186d9 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -18,6 +18,8 @@ from contextor.core.analysis.lineage_extraction_contracts import (
     build_local_occurrence_id,
     parse_local_occurrence_id,
 )
+from contextor.core.analysis.lineage_extraction_emit import add_anchor, emit_flow, occurrence, parameter_symbolic, return_symbolic
+from contextor.core.analysis.lineage_extraction_state import _ActiveComprehension, _CallArgumentInfo, _CallableInfo, _ImportInfo, _ParameterInfo, LineageExtractionState
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
     ExtractedFlowFact,
@@ -33,112 +35,38 @@ from contextor.core.domain.lineage_facts import (
 )
 
 
-@dataclass(frozen=True)
-class _ParameterInfo:
-    local_id: str
-    name: str
-    kind: ParameterKind
-    ordinal: int
-
-
-@dataclass(frozen=True)
-class _CallableInfo:
-    name: str
-    anchor_id: str
-    parameters: tuple[_ParameterInfo, ...]
-
-
-@dataclass(frozen=True)
-class _ImportInfo:
-    module_name: str
-    symbol_name: str | None
-    binding_id: str
-
-
-@dataclass
-class _ActiveComprehension:
-    lookup_owner: str
-    lexical_enclosing_owner: str | None
-    effective_walrus_owner: str | None
-    walrus_entry_frame: dict[str, ExtractedOccurrenceRef]
-    touched_walrus_names: set[str]
-
-
-@dataclass(frozen=True)
-class _CallArgumentInfo:
-    occurrence: ExtractedOccurrenceRef
-    node: ast.AST
-    kind: str
-    keyword_name: str | None
-
-
 class _AnchorExtractor:
     def __init__(self, paths: dict[int, str], source_key: str) -> None:
         self.paths = paths
         self.source_key = source_key
         self.module_name = _module_name_from_source_key(source_key)
-        self.anchors: list[ExtractedAnchorFact] = []
-        self.flows: list[ExtractedFlowFact] = []
-        self._ids: set[str] = set()
-        self._flow_ids: set[str] = set()
-        self._occurrences: dict[tuple[str, int, str | None, int], ExtractedOccurrenceRef] = {}
-        self._bindings: dict[str | None, dict[str, ExtractedOccurrenceRef]] = {}
-        self._callables: dict[str | None, dict[str, _CallableInfo]] = {}
-        self._callables_by_anchor: dict[str, _CallableInfo] = {}
-        self._callables_by_binding: dict[str, _CallableInfo] = {}
-        self._callable_values: dict[str, _CallableInfo] = {}
-        self._imports: dict[str | None, dict[str, _ImportInfo]] = {}
-        self._blocked: dict[str | None, set[str]] = {}
-        self._active_comprehensions: list[_ActiveComprehension] = []
+        self.state = LineageExtractionState()
 
     def extract(self, tree: ast.AST) -> tuple[tuple[ExtractedAnchorFact, ...], tuple[ExtractedFlowFact, ...]]:
         self._visit(tree, None, None)
-        return tuple(sorted(self.anchors)), tuple(sorted(self.flows))
+        return tuple(sorted(self.state.anchors)), tuple(sorted(self.state.flows))
 
     def _add(self, kind: str, node: ast.AST, name: str | None, owner_local_id: str | None, *, ordinal: int = 0, local_kind: str | None = None) -> str:
-        local_id = build_local_occurrence_id(local_kind or kind, self.paths[id(node)], name, ordinal=ordinal)
-        if local_id in self._ids:
-            raise ValueError(f"Duplicate lineage local id: {local_id}")
-        self._ids.add(local_id)
-        self.anchors.append(ExtractedAnchorFact(local_id=local_id, kind=kind, span=_source_span(node), owner_local_id=owner_local_id))
-        return local_id
+        return add_anchor(self.state, self.paths, kind, node, name, owner_local_id, ordinal=ordinal, local_kind=local_kind)
 
     def _occurrence(self, kind: str, node: ast.AST, name: str | None = None, *, ordinal: int = 0) -> ExtractedOccurrenceRef:
-        cache_key = (kind, id(node), name, ordinal)
-        cached = self._occurrences.get(cache_key)
-        if cached is not None:
-            return cached
-        local_id = build_local_occurrence_id(
-            kind,
-            self.paths[id(node)],
-            name,
-            ordinal=ordinal,
-        )
-        if local_id in self._ids:
-            raise ValueError(f"Duplicate lineage local id: {local_id}")
-        self._ids.add(local_id)
-        occurrence = ExtractedOccurrenceRef(local_id)
-        self._occurrences[cache_key] = occurrence
-        return occurrence
+        return occurrence(self.state, self.paths, kind, node, name, ordinal=ordinal)
 
     def _flow(self, *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0, dynamic_boundary: str | None = None) -> None:
-        local_id = f"flow:v1:{relation.value}:{self.paths[id(node)]}:i:{ordinal}"
-        if local_id in self._flow_ids: raise ValueError(f"Duplicate lineage flow id: {local_id}")
-        self._flow_ids.add(local_id)
-        self.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence, dynamic_boundary=dynamic_boundary))
+        emit_flow(self.state, self.paths, source=source, target=target, relation=relation, node=node, resolution_kind=resolution_kind, confidence=confidence, ordinal=ordinal, dynamic_boundary=dynamic_boundary)
 
     def _frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
-        return self._bindings.setdefault(owner, {})
+        return self.state.frame(owner)
 
     def _clone_frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
-        return dict(self._frame(owner))
+        return self.state.clone_frame(owner)
 
     def _replace_frame(
         self,
         owner: str | None,
         frame: dict[str, ExtractedOccurrenceRef],
     ) -> None:
-        self._bindings[owner] = dict(frame)
+        self.state.replace_frame(owner, frame)
 
     def _begin_comprehension(
         self,
@@ -162,7 +90,7 @@ class _AnchorExtractor:
         imports.update(
             self._import_frame(lexical_enclosing_owner)
         )
-        self._active_comprehensions.append(record)
+        self.state._active_comprehensions.append(record)
         return record
 
     def _publish_executed_walrus(
@@ -171,7 +99,7 @@ class _AnchorExtractor:
         binding: ExtractedOccurrenceRef,
         target_owner: str | None,
     ) -> None:
-        for record in self._active_comprehensions:
+        for record in self.state._active_comprehensions:
             if record.effective_walrus_owner != target_owner:
                 continue
             record.touched_walrus_names.add(name)
@@ -182,8 +110,8 @@ class _AnchorExtractor:
         record: _ActiveComprehension,
     ) -> None:
         if (
-            not self._active_comprehensions
-            or self._active_comprehensions[-1] is not record
+            not self.state._active_comprehensions
+            or self.state._active_comprehensions[-1] is not record
         ):
             raise RuntimeError(
                 "Comprehension lineage stack mismatch"
@@ -198,8 +126,8 @@ class _AnchorExtractor:
             record.effective_walrus_owner,
             merged,
         )
-        self._active_comprehensions.pop()
-        for parent in self._active_comprehensions:
+        self.state._active_comprehensions.pop()
+        for parent in self.state._active_comprehensions:
             if (
                 parent.effective_walrus_owner
                 != record.effective_walrus_owner
@@ -216,17 +144,7 @@ class _AnchorExtractor:
         self,
         frames: tuple[dict[str, ExtractedOccurrenceRef], ...],
     ) -> dict[str, ExtractedOccurrenceRef]:
-        if not frames:
-            return {}
-        common_names = set(frames[0])
-        for frame in frames[1:]:
-            common_names.intersection_update(frame)
-        merged: dict[str, ExtractedOccurrenceRef] = {}
-        for name in common_names:
-            first = frames[0][name]
-            if all(frame[name] == first for frame in frames[1:]):
-                merged[name] = first
-        return merged
+        return self.state.merge_frames(frames)
 
     def _visit_block_from_frame(
         self,
@@ -241,13 +159,13 @@ class _AnchorExtractor:
         return self._clone_frame(owner)
 
     def _blocked_names(self, owner: str | None) -> set[str]:
-        return self._blocked.setdefault(owner, set())
+        return self.state.blocked_names(owner)
 
     def _callable_frame(self, owner: str | None) -> dict[str, _CallableInfo]:
-        return self._callables.setdefault(owner, {})
+        return self.state.callable_frame(owner)
 
     def _import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
-        return self._imports.setdefault(owner, {})
+        return self.state.import_frame(owner)
 
     def _register_import_binding(self, alias: ast.alias, owner: str | None, local_name: str, module_name: str | None, symbol_name: str | None) -> None:
         binding_id = self._add("import_binding", alias, local_name, owner)
@@ -269,16 +187,16 @@ class _AnchorExtractor:
         return self._occurrence("expression_result", node)
 
     def _parameter_symbolic(self, callable_symbol_name: str, parameter: _ParameterInfo) -> ExtractedSymbolicRef:
-        return ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, self.module_name, callable_symbol_name, parameter.local_id)
+        return parameter_symbolic(self.module_name, callable_symbol_name, parameter)
 
     def _return_symbolic(self, callable_info: _CallableInfo) -> ExtractedSymbolicRef:
-        return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, self.module_name, callable_info.name, callable_info.anchor_id)
+        return return_symbolic(self.module_name, callable_info)
 
     def _resolve_current_local_callable(self, node: ast.Call, owner: str | None) -> _CallableInfo | None:
         if not isinstance(node.func, ast.Name): return None
         current = self._frame(owner).get(node.func.id)
         if current is None: return None
-        return self._callables_by_anchor.get(current.local_id) or self._callables_by_binding.get(current.local_id)
+        return self.state._callables_by_anchor.get(current.local_id) or self.state._callables_by_binding.get(current.local_id)
 
     def _current_import_info(self, owner: str | None, local_name: str) -> _ImportInfo | None:
         current, info = self._frame(owner).get(local_name), self._import_frame(owner).get(local_name)
@@ -404,7 +322,7 @@ class _AnchorExtractor:
         self._default_flows(node, node.name, parameters)
         callable_info = _CallableInfo(node.name, function_id, parameters)
         self._callable_frame(owner)[node.name] = callable_info
-        self._callables_by_anchor[function_id] = callable_info
+        self.state._callables_by_anchor[function_id] = callable_info
         function_frame = self._frame(function_id)
         for parameter in parameters:
             function_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
@@ -426,19 +344,19 @@ class _AnchorExtractor:
         parameters = self._parameter_anchors(node.args, lambda_id, callable_symbol_name)
         self._default_flows(node, callable_symbol_name, parameters)
         callable_info = _CallableInfo(callable_symbol_name, lambda_id, parameters)
-        self._callables_by_anchor[lambda_id] = callable_info
+        self.state._callables_by_anchor[lambda_id] = callable_info
         lambda_frame = self._frame(lambda_id)
         for parameter in parameters:
             lambda_frame[parameter.name] = ExtractedOccurrenceRef(parameter.local_id)
         body_source = self._value(node.body, lambda_id, None)
         self._flow(source=body_source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node.body, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
         lambda_value = self._occurrence("expression_result", node)
-        self._callable_values[lambda_value.local_id] = callable_info
+        self.state._callable_values[lambda_value.local_id] = callable_info
 
     def _visit_Return(self, node: ast.Return, owner: str | None, walrus_owner: str | None) -> None:
         if node.value is None: return
         source = self._value(node.value, owner, walrus_owner)
-        callable_info = self._callables_by_anchor.get(owner) if owner is not None else None
+        callable_info = self.state._callables_by_anchor.get(owner) if owner is not None else None
         if callable_info is not None:
             self._flow(source=source, target=self._return_symbolic(callable_info), relation=LineageRelation.RETURNS, node=node, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
 
@@ -571,9 +489,9 @@ class _AnchorExtractor:
         if target.id in self._blocked_names(owner):
             return None
         self._frame(owner)[target.id] = binding
-        callable_info = self._callable_values.get(source.local_id)
+        callable_info = self.state._callable_values.get(source.local_id)
         if callable_info is not None:
-            self._callables_by_binding[binding.local_id] = callable_info
+            self.state._callables_by_binding[binding.local_id] = callable_info
         self._flow(source=source, target=binding, relation=LineageRelation.ASSIGNS, node=target, resolution_kind=ResolutionKind.LEXICAL_EXACT, confidence=LineageConfidence.CONFIRMED)
         return binding

diff --git a/contextor/core/analysis/lineage_extraction_state.py b/contextor/core/analysis/lineage_extraction_state.py
new file mode 100644
index 0000000..d407abc
--- /dev/null
+++ b/contextor/core/analysis/lineage_extraction_state.py
@@ -0,0 +1,93 @@
+from __future__ import annotations
+
+import ast
+from dataclasses import dataclass, field
+
+from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ParameterKind
+
+
+@dataclass(frozen=True)
+class _ParameterInfo:
+    local_id: str
+    name: str
+    kind: ParameterKind
+    ordinal: int
+
+
+@dataclass(frozen=True)
+class _CallableInfo:
+    name: str
+    anchor_id: str
+    parameters: tuple[_ParameterInfo, ...]
+
+
+@dataclass(frozen=True)
+class _ImportInfo:
+    module_name: str
+    symbol_name: str | None
+    binding_id: str
+
+
+@dataclass
+class _ActiveComprehension:
+    lookup_owner: str
+    lexical_enclosing_owner: str | None
+    effective_walrus_owner: str | None
+    walrus_entry_frame: dict[str, ExtractedOccurrenceRef]
+    touched_walrus_names: set[str]
+
+
+@dataclass(frozen=True)
+class _CallArgumentInfo:
+    occurrence: ExtractedOccurrenceRef
+    node: ast.AST
+    kind: str
+    keyword_name: str | None
+
+
+@dataclass
+class LineageExtractionState:
+    anchors: list[ExtractedAnchorFact] = field(default_factory=list)
+    flows: list[ExtractedFlowFact] = field(default_factory=list)
+    _ids: set[str] = field(default_factory=set)
+    _flow_ids: set[str] = field(default_factory=set)
+    _occurrences: dict[tuple[str, int, str | None, int], ExtractedOccurrenceRef] = field(default_factory=dict)
+    _bindings: dict[str | None, dict[str, ExtractedOccurrenceRef]] = field(default_factory=dict)
+    _callables: dict[str | None, dict[str, _CallableInfo]] = field(default_factory=dict)
+    _callables_by_anchor: dict[str, _CallableInfo] = field(default_factory=dict)
+    _callables_by_binding: dict[str, _CallableInfo] = field(default_factory=dict)
+    _callable_values: dict[str, _CallableInfo] = field(default_factory=dict)
+    _imports: dict[str | None, dict[str, _ImportInfo]] = field(default_factory=dict)
+    _blocked: dict[str | None, set[str]] = field(default_factory=dict)
+    _active_comprehensions: list[_ActiveComprehension] = field(default_factory=list)
+
+    def frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
+        return self._bindings.setdefault(owner, {})
+
+    def clone_frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
+        return dict(self.frame(owner))
+
+    def replace_frame(self, owner: str | None, frame: dict[str, ExtractedOccurrenceRef]) -> None:
+        self._bindings[owner] = dict(frame)
+
+    def merge_frames(self, frames: tuple[dict[str, ExtractedOccurrenceRef], ...]) -> dict[str, ExtractedOccurrenceRef]:
+        if not frames:
+            return {}
+        common_names = set(frames[0])
+        for frame in frames[1:]:
+            common_names.intersection_update(frame)
+        merged: dict[str, ExtractedOccurrenceRef] = {}
+        for name in common_names:
+            first = frames[0][name]
+            if all(frame[name] == first for frame in frames[1:]):
+                merged[name] = first
+        return merged
+
+    def blocked_names(self, owner: str | None) -> set[str]:
+        return self._blocked.setdefault(owner, set())
+
+    def callable_frame(self, owner: str | None) -> dict[str, _CallableInfo]:
+        return self._callables.setdefault(owner, {})
+
+    def import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
+        return self._imports.setdefault(owner, {})

diff --git a/contextor/core/analysis/lineage_extraction_emit.py b/contextor/core/analysis/lineage_extraction_emit.py
new file mode 100644
index 0000000..9b304b4
--- /dev/null
+++ b/contextor/core/analysis/lineage_extraction_emit.py
@@ -0,0 +1,45 @@
+from __future__ import annotations
+
+import ast
+
+from contextor.core.analysis.lineage_extraction_contracts import _source_span, build_local_occurrence_id
+from contextor.core.analysis.lineage_extraction_state import _CallableInfo, _ParameterInfo, LineageExtractionState
+from contextor.core.domain.lineage_facts import ExtractedAnchorFact, ExtractedFlowFact, ExtractedOccurrenceRef, ExtractedSymbolicKind, ExtractedSymbolicRef, LineageConfidence, LineageRelation, ResolutionKind
+
+
+def add_anchor(state, paths, kind, node, name, owner_local_id, *, ordinal=0, local_kind=None):
+    local_id = build_local_occurrence_id(local_kind or kind, paths[id(node)], name, ordinal=ordinal)
+    if local_id in state._ids:
+        raise ValueError(f"Duplicate lineage local id: {local_id}")
+    state._ids.add(local_id)
+    state.anchors.append(ExtractedAnchorFact(local_id=local_id, kind=kind, span=_source_span(node), owner_local_id=owner_local_id))
+    return local_id
+
+
+def occurrence(state, paths, kind, node, name=None, *, ordinal=0):
+    cache_key = (kind, id(node), name, ordinal)
+    cached = state._occurrences.get(cache_key)
+    if cached is not None:
+        return cached
+    local_id = build_local_occurrence_id(kind, paths[id(node)], name, ordinal=ordinal)
+    if local_id in state._ids:
+        raise ValueError(f"Duplicate lineage local id: {local_id}")
+    state._ids.add(local_id)
+    result = ExtractedOccurrenceRef(local_id)
+    state._occurrences[cache_key] = result
+    return result
+
+
+def emit_flow(state, paths, *, source, target, relation, node, resolution_kind, confidence, ordinal=0, dynamic_boundary=None):
+    local_id = f"flow:v1:{relation.value}:{paths[id(node)]}:i:{ordinal}"
+    if local_id in state._flow_ids: raise ValueError(f"Duplicate lineage flow id: {local_id}")
+    state._flow_ids.add(local_id)
+    state.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence, dynamic_boundary=dynamic_boundary))
+
+
+def parameter_symbolic(module_name, callable_symbol_name, parameter):
+    return ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, module_name, callable_symbol_name, parameter.local_id)
+
+
+def return_symbolic(module_name, callable_info):
+    return ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, module_name, callable_info.name, callable_info.anchor_id)
