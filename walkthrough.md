STATUS=PASS
TASK=Stage 1F.2 final end-to-end certification
HEAD=de0cd98 Auto-commit: Cleanup and update
MCP_DISCOVERY=ACTIVE: contextor_fact_lineage available; contextor_lineage absent from active and exposed deferred pools. contextor_fact_lineage family=lineage_facts returned invalid_family (only artifact_consumption, syntax_diagnostics, symbol_calls), so it supplied no lineage-family projection.

MINOR_CLEANUP=
- contextor/core/domain/lineage_facts.py: exact confirmed materialized surfaces reject only bare MaterializedOccurrenceRef; diagnostic now accurately permits SemanticEndpoint or exact symbolic boundary.
- tests/test_full_analysis_lineage_materialization.py: ends with LF.

FOCUSED_VALIDATION=
- .\.venv\Scripts\python.exe -m pytest -q tests/domain/test_lineage_facts.py
- result: 65 passed in 1.19s
- .\.venv\Scripts\python.exe -m py_compile contextor/core/api/facade.py contextor/core/analysis/lineage_extraction_surfaces.py contextor/core/domain/lineage_facts.py
- result: exit 0
- git diff --check -- . ':(exclude)walkthrough.md'
- result: exit 0

REAL_FULL_ANALYSIS_COMMAND=
CONTEXTOR_DISABLE_PROCESS_POOL=1 .\.venv\Scripts\python.exe -u -c "ContextorFacade.analyze_project(r'C:\Temp\Contextor_Repo', log=print, owner='cli_analysis'); hydrate_repository_engine(...); assert canonical lineage invariants"
REAL_FULL_ANALYSIS_EXIT_RESULT=exit 0; errors=[]; result_type=AnalysisResult; REAL_FULL_ANALYSIS_CERTIFICATION_PASS
PROGRESS_TAIL=
[PROGRESS] Step 1/8: Initializing repository identity
[PROGRESS] Step 2/8: Indexing repository files
[PROGRESS] Step 3/8: Resolving dependency graph
[PROGRESS] Step 4/8: Validating dependency graph
[PROGRESS] Step 5/8: Computing metrics, cycles and debt
[PROGRESS] Step 6/8: Generating architectural reports
[PROGRESS] Step 7/8: Persisting canonical LIVE snapshot
[PROGRESS] Step 8/8: Finalizing analysis
REAL_FULL_ANALYSIS_RETURN errors=[] result_type=AnalysisResult
REAL_FULL_ANALYSIS_CERTIFICATION_PASS
STEP7_RESULT=PASS: canonical LIVE snapshot persistence completed and analysis continued to Step 8; no confirmed-exact-SemanticEndpoint error occurred.

REAL_CANONICAL_LINEAGE_SUMMARY=
- lineage_facts_by_source: 365 non-empty source slices
- lineage_facts_state: fresh
- lineage_facts_semantic_version: 1 (matches LINEAGE_FACTS_SEMANTIC_VERSION=1)
- manifest/source-key mismatches: 0
- surfaces: 2,893 (SemanticEndpoint=322; MaterializedSymbolicRef=11; MaterializedOccurrenceRef=2,560)
- confirmed exact local occurrence surfaces: 0
- duplicate/stale source keys: none observed; every mapping key equals manifest.source_key

REPRESENTATIVE_REAL_SURFACES=
- exact local EXPORT: contextor/core/analysis/activity.py, classify_symbol_activity, LITERAL_CONTAINER_EXACT/CONFIRMED -> SemanticEndpoint(A1477/1)
- internal exact REEXPORT: contextor/core/__init__.py, build_index, IMPORT_EXACT/CONFIRMED -> SemanticEndpoint(A1561/1)
- exact symbolic boundary: contextor/core/__init__.py, validate, IMPORT_EXACT/CONFIRMED -> MaterializedSymbolicRef(contextor.core.validator::validate); no allocation/failure
- inferred PUBLIC_SYMBOL: contextor/__main__.py, main, PYTHON_NAME_CONVENTION/INFERRED -> MaterializedOccurrenceRef; not strengthened

PERSISTENCE_FAILURE=NONE
FILES_CHANGED=
- contextor/core/analysis/lineage_extraction_surfaces.py
- contextor/core/domain/lineage_facts.py
- tests/analysis/test_lineage_extraction.py
- tests/test_full_analysis_lineage_materialization.py
- walkthrough.md

COMPLETE_RAW_UNIFIED_FULL_DIFF (walkthrough.md itself intentionally excluded)=
diff --git a/contextor/core/analysis/lineage_extraction_surfaces.py b/contextor/core/analysis/lineage_extraction_surfaces.py
index 32fbb20..7965fd9 100644
--- a/contextor/core/analysis/lineage_extraction_surfaces.py
+++ b/contextor/core/analysis/lineage_extraction_surfaces.py
@@ -89,9 +89,9 @@ def finalize_surfaces(state: LineageExtractionState, paths: dict[int, str], modu
             candidate = state._module_public_candidates.get(name)
             imported = state.import_frame(module_owner).get(name)
             if candidate is not None and candidate[0] == current:
-                emit_surface(state, paths, kind=SurfaceKind.EXPORT, exposed=current, node=item, declared_name=name, resolution_kind=ResolutionKind.LITERAL_CONTAINER_EXACT, confidence=LineageConfidence.CONFIRMED, declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ordinal=ordinal)
+                emit_surface(state, paths, kind=SurfaceKind.EXPORT, exposed=ExtractedSymbolicRef(ExtractedSymbolicKind.PUBLIC_TARGET, module_name, name, current.local_id), node=item, declared_name=name, resolution_kind=ResolutionKind.LITERAL_CONTAINER_EXACT, confidence=LineageConfidence.CONFIRMED, declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ordinal=ordinal)
             elif current is not None and imported is not None and imported.symbol_name is not None and imported.binding_id == current.local_id:
-                emit_surface(state, paths, kind=SurfaceKind.REEXPORT, exposed=current, node=item, declared_name=name, resolution_kind=ResolutionKind.IMPORT_EXACT, confidence=LineageConfidence.CONFIRMED, declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION, ordinal=ordinal)
+                emit_surface(state, paths, kind=SurfaceKind.REEXPORT, exposed=ExtractedSymbolicRef(ExtractedSymbolicKind.PUBLIC_TARGET, imported.module_name, imported.symbol_name, current.local_id), node=item, declared_name=name, resolution_kind=ResolutionKind.IMPORT_EXACT, confidence=LineageConfidence.CONFIRMED, declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION, ordinal=ordinal)
             else:
                 emit_surface(state, paths, kind=SurfaceKind.EXPORT, exposed=ExtractedSymbolicRef(ExtractedSymbolicKind.PUBLIC_TARGET, module_name, name), node=item, declared_name=name, resolution_kind=ResolutionKind.UNRESOLVED_NAME, confidence=LineageConfidence.UNRESOLVED, declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ordinal=ordinal)
         return
diff --git a/contextor/core/domain/lineage_facts.py b/contextor/core/domain/lineage_facts.py
index eb93b30..69e5ea1 100644
--- a/contextor/core/domain/lineage_facts.py
+++ b/contextor/core/domain/lineage_facts.py
@@ -673,11 +673,12 @@ def _validate_materialized_surface_target(
     resolution_kind: ResolutionKind,
     confidence: LineageConfidence,
 ) -> None:
-    if claims_exact_semantic_target(resolution_kind, confidence) and not isinstance(
-        exposed, SemanticEndpoint
+    if claims_exact_semantic_target(resolution_kind, confidence) and isinstance(
+        exposed, MaterializedOccurrenceRef
     ):
         raise ValueError(
-            "confirmed exact semantic surface target requires SemanticEndpoint"
+            "confirmed exact semantic surface target cannot remain a bare local "
+            "occurrence; requires SemanticEndpoint or exact symbolic boundary"
         )
 
 
diff --git a/tests/analysis/test_lineage_extraction.py b/tests/analysis/test_lineage_extraction.py
index ff346a8..de2207e 100644
--- a/tests/analysis/test_lineage_extraction.py
+++ b/tests/analysis/test_lineage_extraction.py
@@ -2047,7 +2047,9 @@ def test_stage_1e1_later_literal_all_overrides_defaults_and_reuses_local_anchor(
     assert [surface.declared_name for surface in facts.surfaces] == ["a"]
     surface = facts.surfaces[0]
     assert surface.kind is SurfaceKind.EXPORT
-    assert surface.exposed == ExtractedOccurrenceRef(_stage_1c_named(facts, "function", "a")[0].local_id)
+    assert isinstance(surface.exposed, ExtractedSymbolicRef)
+    assert (surface.exposed.kind, surface.exposed.module_name, surface.exposed.symbol_name) == (ExtractedSymbolicKind.PUBLIC_TARGET, "pkg", "a")
+    assert surface.exposed.source_local_id == _stage_1c_named(facts, "function", "a")[0].local_id
     assert surface.resolution_kind is ResolutionKind.LITERAL_CONTAINER_EXACT
     assert surface.confidence is LineageConfidence.CONFIRMED
     assert surface.declaration_evidence is SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION
@@ -2078,7 +2080,11 @@ def test_stage_1e1_explicit_from_import_reexport_uses_current_binding(source_key
     assert surface.resolution_kind is ResolutionKind.IMPORT_EXACT
     assert surface.confidence is LineageConfidence.CONFIRMED
     assert surface.declaration_evidence is SurfaceDeclarationEvidence.STATIC_DECLARATION
-    assert surface.exposed == ExtractedOccurrenceRef(_stage_1c_named(facts, "import_binding", "public")[0].local_id)
+    assert isinstance(surface.exposed, ExtractedSymbolicRef)
+    assert surface.exposed.kind is ExtractedSymbolicKind.PUBLIC_TARGET
+    assert surface.exposed.module_name == ("provider" if source_key == "pkg.py" else "pkg.provider")
+    assert surface.exposed.symbol_name == "f"
+    assert surface.exposed.source_local_id == _stage_1c_named(facts, "import_binding", "public")[0].local_id
 
 
 def test_stage_1e1_rebound_import_is_local_export_not_reexport():
@@ -2086,7 +2092,9 @@ def test_stage_1e1_rebound_import_is_local_export_not_reexport():
     surface = facts.surfaces[0]
     assert surface.kind is SurfaceKind.EXPORT
     assert surface.resolution_kind is ResolutionKind.LITERAL_CONTAINER_EXACT
-    assert surface.exposed == ExtractedOccurrenceRef(_stage_1c_named(facts, "binding", "public")[-1].local_id)
+    assert isinstance(surface.exposed, ExtractedSymbolicRef)
+    assert (surface.exposed.kind, surface.exposed.module_name, surface.exposed.symbol_name) == (ExtractedSymbolicKind.PUBLIC_TARGET, "pkg", "public")
+    assert surface.exposed.source_local_id == _stage_1c_named(facts, "binding", "public")[-1].local_id
 
 
 @pytest.mark.parametrize("source", [
@@ -2137,7 +2145,9 @@ def test_stage_1e1_later_binding_supersedes_surface_delete_tombstone():
     surface = facts.surfaces[0]
     assert surface.kind is SurfaceKind.EXPORT
     assert surface.confidence is LineageConfidence.CONFIRMED
-    assert surface.exposed == ExtractedOccurrenceRef(_stage_1c_named(facts, "binding", "x")[-1].local_id)
+    assert isinstance(surface.exposed, ExtractedSymbolicRef)
+    assert (surface.exposed.kind, surface.exposed.module_name, surface.exposed.symbol_name) == (ExtractedSymbolicKind.PUBLIC_TARGET, "pkg", "x")
+    assert surface.exposed.source_local_id == _stage_1c_named(facts, "binding", "x")[-1].local_id
 
 
 @pytest.mark.parametrize("source", [
diff --git a/tests/test_full_analysis_lineage_materialization.py b/tests/test_full_analysis_lineage_materialization.py
index 9fa35a5..5d84ec3 100644
--- a/tests/test_full_analysis_lineage_materialization.py
+++ b/tests/test_full_analysis_lineage_materialization.py
@@ -1,3 +1,5 @@
+import pytest
+import ast
 from contextlib import contextmanager
 from types import SimpleNamespace
 
@@ -16,12 +18,17 @@ from contextor.core.domain.lineage_facts import (
     LineageConfidence,
     LineageFamilyStatus,
     LineageRelation,
+    MaterializedOccurrenceRef,
+    MaterializedSurfaceFact,
     MaterializedSymbolicRef,
     ResolutionKind,
     SemanticEndpoint,
     SourceSpan,
+    SurfaceDeclarationEvidence,
+    SurfaceKind,
 )
 from contextor.core.analysis import state_manager
+from contextor.core.analysis.lineage_extraction import extract_lineage_source_facts
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.symbol_engine import indexer
 
@@ -142,9 +149,9 @@ def test_real_full_analysis_installs_current_lineage_without_second_extraction(t
     monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
     monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
     monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
-    (repo / "provider.py").write_text("def target():\n    return 1\n", encoding="utf-8")
+    (repo / "provider.py").write_text("def target():\n    return 1\n__all__ = [\"target\"]\n", encoding="utf-8")
     (repo / "consumer.py").write_text(
-        "from provider import target\nvalue = target()\n", encoding="utf-8"
+        "from provider import target as exported\n__all__ = [\"exported\"]\nvalue = exported()\n", encoding="utf-8"
     )
 
     original_extract = indexer.extract_lineage_source_facts
@@ -181,3 +188,88 @@ def test_real_full_analysis_installs_current_lineage_without_second_extraction(t
         source_key == source_slice.manifest.source_key
         for source_key, source_slice in state.lineage_facts_by_source.items()
     )
+    registry = PersistentIdentityRegistry(str(repo))
+    with registry.read_transaction():
+        provider_target_id = registry._state["artifact_registry"]["path_to_id"]["provider::target"]
+    assert state.lineage_facts_by_source["provider.py"].surfaces[0].exposed == SemanticEndpoint(provider_target_id)
+    assert state.lineage_facts_by_source["consumer.py"].surfaces[0].exposed == SemanticEndpoint(provider_target_id)
+
+
+def test_exact_surface_materialization_uses_symbolic_targets_and_preserves_external_boundary():
+    local_facts = extract_lineage_source_facts(
+        ast.parse("def target():\n    return 1\n__all__ = ['target']\n"),
+        source_key="pkg.py",
+        source_fingerprint="a" * 64,
+    )
+    local_surface = local_facts.surfaces[0]
+    assert isinstance(local_surface.exposed, ExtractedSymbolicRef)
+    assert local_surface.exposed.kind is ExtractedSymbolicKind.PUBLIC_TARGET
+    assert local_surface.exposed.module_name == "pkg"
+    assert local_surface.exposed.symbol_name == "target"
+    assert local_surface.exposed.source_local_id is not None
+
+    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
+    local_index = _index(facts={"pkg.py": local_facts})
+    local_mapping, local_state, _ = _materialize_full_analysis_lineage(
+        local_index, registry, local_index.modules, {"pkg": {"own_symbols": ["target"]}}
+    )
+    assert local_state == "fresh"
+    assert local_mapping["pkg.py"].surfaces[0].exposed == SemanticEndpoint("A1/1")
+
+    external_facts = extract_lineage_source_facts(
+        ast.parse("from external import target as alias\n__all__ = ['alias']\n"),
+        source_key="pkg.py",
+        source_fingerprint="b" * 64,
+    )
+    external_surface = external_facts.surfaces[0]
+    assert external_surface.kind is SurfaceKind.REEXPORT
+    assert isinstance(external_surface.exposed, ExtractedSymbolicRef)
+    assert (
+        external_surface.exposed.module_name,
+        external_surface.exposed.symbol_name,
+    ) == ("external", "target")
+    assert external_surface.exposed.source_local_id is not None
+
+    external_registry = _ReadOnlyRegistry({"pkg": "1/1"}, {})
+    external_index = _index(facts={"pkg.py": external_facts})
+    external_mapping, external_state, _ = _materialize_full_analysis_lineage(
+        external_index, external_registry, external_index.modules, {"pkg": {"own_symbols": []}}
+    )
+    assert external_state == "fresh"
+    materialized_external = external_mapping["pkg.py"].surfaces[0].exposed
+    assert isinstance(materialized_external, MaterializedSymbolicRef)
+    assert (
+        materialized_external.module_name,
+        materialized_external.symbol_name,
+    ) == ("external", "target")
+
+
+def test_inferred_public_symbol_is_not_strengthened_by_matching_active_artifact():
+    facts = extract_lineage_source_facts(
+        ast.parse("def target():\n    return 1\n"),
+        source_key="pkg.py",
+        source_fingerprint="c" * 64,
+    )
+    index = _index(facts={"pkg.py": facts})
+    mapping, state, _ = _materialize_full_analysis_lineage(
+        index,
+        _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"}),
+        index.modules,
+        {"pkg": {"own_symbols": ["target"]}},
+    )
+    assert state == "fresh"
+    assert isinstance(mapping["pkg.py"].surfaces[0].exposed, MaterializedOccurrenceRef)
+
+
+def test_domain_rejects_exact_surface_with_bare_local_occurrence():
+    with pytest.raises(ValueError, match="requires SemanticEndpoint or exact symbolic boundary"):
+        MaterializedSurfaceFact(
+            "surface",
+            SurfaceKind.EXPORT,
+            MaterializedOccurrenceRef("pkg.py", "fingerprint", "local"),
+            SourceSpan(1, 0, 1, 1),
+            ResolutionKind.LITERAL_CONTAINER_EXACT,
+            LineageConfidence.CONFIRMED,
+            "target",
+            declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION,
+        )
