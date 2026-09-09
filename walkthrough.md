STATUS=REPORT_COMPLETED
FILES_CHANGED=NONE
TESTS_RUN=NONE
MISSING_FULL_DIFFS=

diff --git a/contextor/core/analysis/lineage_extraction.py b/contextor/core/analysis/lineage_extraction.py
index 6a8e051..6a4bb8a 100644
--- a/contextor/core/analysis/lineage_extraction.py
+++ b/contextor/core/analysis/lineage_extraction.py
@@ -25,7 +25,19 @@ from contextor.core.domain.lineage_facts import (
 
 _LOCAL_ID_VERSION: Final[str] = "v1"
 _ANCHOR_KINDS: Final[frozenset[str]] = frozenset({"module", "class", "function", "async_function", "lambda", "comprehension", "parameter", "binding", "import_binding", "global_declaration", "nonlocal_declaration"})
-_LOCAL_ID_KINDS: Final[frozenset[str]] = _ANCHOR_KINDS | frozenset({"parameter_posonly", "parameter_poskw", "parameter_kwonly", "parameter_vararg", "parameter_varkw", "expression_result"})
+_LOCAL_ID_KINDS: Final[frozenset[str]] = _ANCHOR_KINDS | frozenset({
+    "parameter_posonly",
+    "parameter_poskw",
+    "parameter_kwonly",
+    "parameter_vararg",
+    "parameter_varkw",
+    "expression_result",
+    "name_load",
+    "call_site",
+    "call_argument",
+    "call_result",
+    "runtime_bound_local",
+})
 _AST_PATH_RE: Final[re.Pattern[str]] = re.compile(r"^(?:root|(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*))*)$")
 _FINGERPRINT_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
 
@@ -146,14 +158,35 @@ class _ParameterInfo:
     ordinal: int
 
 
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
 class _AnchorExtractor:
     def __init__(self, paths: dict[int, str], source_key: str) -> None:
         self.paths = paths
+        self.source_key = source_key
         self.module_name = _module_name_from_source_key(source_key)
         self.anchors: list[ExtractedAnchorFact] = []
         self.flows: list[ExtractedFlowFact] = []
         self._ids: set[str] = set()
         self._flow_ids: set[str] = set()
+        self._occurrences: dict[tuple[str, int, str | None, int], ExtractedOccurrenceRef] = {}
+        self._bindings: dict[str | None, dict[str, ExtractedOccurrenceRef]] = {}
+        self._callables: dict[str | None, dict[str, _CallableInfo]] = {}
+        self._callables_by_anchor: dict[str, _CallableInfo] = {}
+        self._imports: dict[str | None, dict[str, _ImportInfo]] = {}
+        self._blocked: dict[str | None, set[str]] = {}
 
     def extract(self, tree: ast.AST) -> tuple[tuple[ExtractedAnchorFact, ...], tuple[ExtractedFlowFact, ...]]:
         self._visit(tree, None, None)
@@ -168,10 +201,22 @@ class _AnchorExtractor:
         return local_id
 
     def _occurrence(self, kind: str, node: ast.AST, name: str | None = None, *, ordinal: int = 0) -> ExtractedOccurrenceRef:
-        local_id = build_local_occurrence_id(kind, self.paths[id(node)], name, ordinal=ordinal)
-        if local_id in self._ids: raise ValueError(f"Duplicate lineage local id: {local_id}")
+        cache_key = (kind, id(node), name, ordinal)
+        cached = self._occurrences.get(cache_key)
+        if cached is not None:
+            return cached
+        local_id = build_local_occurrence_id(
+            kind,
+            self.paths[id(node)],
+            name,
+            ordinal=ordinal,
+        )
+        if local_id in self._ids:
+            raise ValueError(f"Duplicate lineage local id: {local_id}")
         self._ids.add(local_id)
-        return ExtractedOccurrenceRef(local_id)
+        occurrence = ExtractedOccurrenceRef(local_id)
+        self._occurrences[cache_key] = occurrence
+        return occurrence
 
     def _flow(self, *, source, target, relation: LineageRelation, node: ast.AST, resolution_kind: ResolutionKind, confidence: LineageConfidence, ordinal: int = 0) -> None:
         local_id = f"flow:v1:{relation.value}:{self.paths[id(node)]}:i:{ordinal}"
@@ -179,6 +224,57 @@ class _AnchorExtractor:
         self._flow_ids.add(local_id)
         self.flows.append(ExtractedFlowFact(local_id, source, target, relation, _source_span(node), resolution_kind, confidence))
 
+    def _frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
+        return self._bindings.setdefault(owner, {})
+
+    def _clone_frame(self, owner: str | None) -> dict[str, ExtractedOccurrenceRef]:
+        return dict(self._frame(owner))
+
+    def _replace_frame(
+        self,
+        owner: str | None,
+        frame: dict[str, ExtractedOccurrenceRef],
+    ) -> None:
+        self._bindings[owner] = dict(frame)
+
+    def _merge_frames(
+        self,
+        frames: tuple[dict[str, ExtractedOccurrenceRef], ...],
+    ) -> dict[str, ExtractedOccurrenceRef]:
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
+    def _blocked_names(self, owner: str | None) -> set[str]:
+        return self._blocked.setdefault(owner, set())
+
+    def _callable_frame(self, owner: str | None) -> dict[str, _CallableInfo]:
+        return self._callables.setdefault(owner, {})
+
+    def _import_frame(self, owner: str | None) -> dict[str, _ImportInfo]:
+        return self._imports.setdefault(owner, {})
+
+    def _value(
+        self,
+        node: ast.AST,
+        owner: str | None,
+        walrus_owner: str | None,
+    ) -> ExtractedOccurrenceRef:
+        self._visit(node, owner, walrus_owner)
+        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
+            return self._occurrence("name_load", node, node.id)
+        if isinstance(node, ast.Call):
+            return self._occurrence("call_result", node)
+        return self._occurrence("expression_result", node)
+
     def _parameter_symbolic(self, callable_symbol_name: str, parameter: _ParameterInfo) -> ExtractedSymbolicRef:
         return ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, self.module_name, callable_symbol_name, parameter.local_id)
 
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index a5c128e..104de5a 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -5,6 +5,7 @@ import sys
 
 import pytest
 
+from contextor.core.analysis import lineage_extraction as lineage_extraction_module
 from contextor.core.analysis.incremental.preparation import prepare_source_update
 from contextor.core.analysis.lineage_extraction import (
     LineageExtractionLimits,
@@ -38,6 +39,64 @@ def test_local_occurrence_id_round_trip_and_multi_name_disambiguation():
     assert parse_local_occurrence_id(second) == ("global_declaration", "0.1", 1, "other")
 
 
+def test_stage_1c_occurrence_kinds_round_trip():
+    for kind in (
+        "name_load",
+        "call_site",
+        "call_argument",
+        "call_result",
+        "runtime_bound_local",
+    ):
+        local_id = build_local_occurrence_id(
+            kind,
+            "0.1",
+            "value",
+            ordinal=2,
+        )
+        assert parse_local_occurrence_id(local_id) == (
+            kind,
+            "0.1",
+            2,
+            "value",
+        )
+
+
+def test_stage_1c_occurrence_cache_reuses_same_ref():
+    tree = ast.parse("value = 1\n")
+    paths, reason = lineage_extraction_module._index_ast_paths(
+        tree,
+        lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS,
+    )
+    assert reason is None
+    extractor = lineage_extraction_module._AnchorExtractor(paths, "pkg.py")
+    node = tree.body[0].value
+    first = extractor._occurrence("expression_result", node)
+    second = extractor._occurrence("expression_result", node)
+    assert first is second
+    assert first.local_id == second.local_id
+    assert len(extractor._ids) == 1
+
+
+def test_stage_1c_merge_frames_keeps_only_identical_occurrences():
+    tree = ast.parse("a = 1\nb = 2\nc = 3\n")
+    paths, reason = lineage_extraction_module._index_ast_paths(
+        tree,
+        lineage_extraction_module.DEFAULT_LINEAGE_EXTRACTION_LIMITS,
+    )
+    assert reason is None
+    extractor = lineage_extraction_module._AnchorExtractor(paths, "pkg.py")
+    a = ExtractedOccurrenceRef("a")
+    b1 = ExtractedOccurrenceRef("b1")
+    b2 = ExtractedOccurrenceRef("b2")
+    merged = extractor._merge_frames(
+        (
+            {"a": a, "b": b1},
+            {"a": a, "b": b2},
+        )
+    )
+    assert merged == {"a": a}
+
+
 def test_extraction_is_deterministic_source_local_and_has_parameter_lineage(monkeypatch):
     tree = ast.parse("import pkg.mod as pm\nvalue = 1\ndef run(arg):\n    local = arg\n    return local\n")
     monkeypatch.setattr("builtins.open", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("extractor performed filesystem I/O")))

