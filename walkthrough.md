# P0 L3B — Full-analysis lineage reuse

## STATUS

SUCCESS

Pełna analiza reużywa per-source materialized lineage facts fail-closed: dokładny obiekt przy równoważnym ResolutionContext, re-resolve przy zmianie globalnego resolution oraz materializacja przy niezgodnym źródle lub braku compact origin.

## CONTEXTOR_FINAL_VERIFICATION

Contextor potwierdził call path `ContextorFacade.analyze_project -> _materialize_full_analysis_lineage` (direct call, linia 693 w canonical revision 1048). Po edycji workspace jest `out_of_sync`, więc Contextor nie zwraca implementacji zmienionego helpera bez nowej analizy; zgodnie z polityką heavy execution nie odświeżano canonical state. Literalna weryfikacja bieżącego pliku potwierdza przekazanie `previous_canonical_state.state` oraz użycie L3A gate, re-resolve i fallback materialize.

## IMPLEMENTATION

- `facade._materialize_full_analysis_lineage(..., previous_state=None)` waliduje poprzedni canonical state i per-source manifest.
- Przy dopasowanym L3A gate zachowuje identyczny obiekt slice.
- Przy zmianie resolution wywołuje `reresolve_materialized_lineage_source_facts`.
- `LineageOriginUnavailableError` powoduje fail-closed fallback do materializacji.
- Trace rejestruje liczniki źródeł oraz czasy gate/re-resolve/materialize.

## FOCUSED_TESTS

` .\\.venv\\Scripts\\python.exe -m pytest -q tests\\test_full_analysis_lineage_materialization.py tests\\analysis\\test_lineage_materialization.py `

`45 passed in 4.11s`

Pokryto: exact object reuse, fingerprint change -> materialize, identity change -> reresolve bez materializacji, missing compact origin -> fallback materialize.

## FILES_CHANGED

- `contextor/core/api/facade.py`
- `tests/test_full_analysis_lineage_materialization.py`

## FULL_DIFFS

```diff
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_full_analysis_lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 12d5a26..89006bd 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -261,17 +261,27 @@ def _initialize_repository_identity(repo_root: str | Path) -> PersistentIdentity
     return registry
 
 
-def _materialize_full_analysis_lineage(index, registry, modules, artifacts):
+def _materialize_full_analysis_lineage(
+    index,
+    registry,
+    modules,
+    artifacts,
+    previous_state=None,
+):
     """Materialize current index lineage from finalized active identities."""
     lineage_materialization_started = time.monotonic()
     from contextor.core.analysis.lineage_materialization import (
+        LineageOriginUnavailableError,
         LineageResolutionContext,
         build_extracted_callable_interface_descriptors,
+        materialized_lineage_source_matches_resolution,
         materialize_lineage_source_facts,
+        reresolve_materialized_lineage_source_facts,
     )
     from contextor.core.domain.lineage_facts import (
         LINEAGE_FACTS_SEMANTIC_VERSION,
         LineageFamilyStatus,
+        MaterializedLineageSourceFacts,
     )
     from contextor.core.reporting_layer.artifact_usage_report import (
         collect_qualified_artifact_identities,
@@ -327,7 +337,34 @@ def _materialize_full_analysis_lineage(index, registry, modules, artifacts):
         ),
         interface_descriptors=interface_descriptors,
     )
+    previous_lineage_by_source = {}
+    previous_state_reusable = (
+        previous_state is not None
+        and not getattr(previous_state, "resync_required", False)
+        and getattr(previous_state, "lineage_facts_state", None) == "fresh"
+        and getattr(previous_state, "lineage_query_index_state", None) == "fresh"
+        and getattr(previous_state, "lineage_facts_semantic_version", None)
+        == LINEAGE_FACTS_SEMANTIC_VERSION
+        and getattr(
+            previous_state,
+            "lineage_semantic_anchor_bindings_complete",
+            None,
+        )
+        is True
+        and isinstance(
+            getattr(previous_state, "lineage_facts_by_source", None),
+            dict,
+        )
+    )
+    if previous_state_reusable:
+        previous_lineage_by_source = previous_state.lineage_facts_by_source
     materialized_by_source = {}
+    reuse_sources = 0
+    reresolve_sources = 0
+    materialize_sources = 0
+    reresolve_fallback_sources = 0
+    reuse_gate_ms = 0.0
+    reresolve_calls_ms = 0.0
     materialize_calls_ms = 0.0
     anchor_count = 0
     flow_count = 0
@@ -337,9 +374,46 @@ def _materialize_full_analysis_lineage(index, registry, modules, artifacts):
         extracted = extracted_by_source[source_key]
         if extracted.source_key != source_key:
             raise ValueError("Extracted lineage mapping key does not match its source key.")
-        materialize_started = time.monotonic()
-        materialized = materialize_lineage_source_facts(extracted, resolution)
-        materialize_calls_ms += (time.monotonic() - materialize_started) * 1000.0
+        materialized = None
+        previous_materialized = previous_lineage_by_source.get(source_key)
+        previous_source_reusable = (
+            isinstance(previous_materialized, MaterializedLineageSourceFacts)
+            and previous_materialized.manifest.source_key == source_key
+            and previous_materialized.manifest.source_fingerprint == extracted.source_fingerprint
+            and previous_materialized.manifest.semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
+            and previous_materialized.manifest.status is LineageFamilyStatus.FRESH
+            and previous_materialized.manifest.semantic_anchor_bindings_materialized is True
+            and previous_materialized.manifest.anchor_ownership_materialized is True
+            and previous_materialized.manifest.flow_ownership_materialized is True
+            and previous_materialized.manifest.interface_descriptors_materialized is True
+        )
+        if previous_source_reusable:
+            reuse_gate_started = time.monotonic()
+            matches_resolution = materialized_lineage_source_matches_resolution(
+                previous_materialized, resolution
+            )
+            reuse_gate_ms += (time.monotonic() - reuse_gate_started) * 1000.0
+            if matches_resolution:
+                materialized = previous_materialized
+                reuse_sources += 1
+            else:
+                reresolve_started = time.monotonic()
+                try:
+                    materialized = reresolve_materialized_lineage_source_facts(
+                        previous_materialized, resolution
+                    )
+                except LineageOriginUnavailableError:
+                    materialized = None
+                    reresolve_fallback_sources += 1
+                else:
+                    reresolve_sources += 1
+                finally:
+                    reresolve_calls_ms += (time.monotonic() - reresolve_started) * 1000.0
+        if materialized is None:
+            materialize_started = time.monotonic()
+            materialized = materialize_lineage_source_facts(extracted, resolution)
+            materialize_calls_ms += (time.monotonic() - materialize_started) * 1000.0
+            materialize_sources += 1
         if (
             materialized.manifest.source_key != extracted.source_key
             or materialized.manifest.source_fingerprint != extracted.source_fingerprint
@@ -371,6 +445,12 @@ def _materialize_full_analysis_lineage(index, registry, modules, artifacts):
         elapsed_ms=lineage_materialization_ms,
         operation="lineage_materialization",
         result=(
+            f"reuse_sources={reuse_sources};"
+            f"reresolve_sources={reresolve_sources};"
+            f"materialize_sources={materialize_sources};"
+            f"reresolve_fallback_sources={reresolve_fallback_sources};"
+            f"reuse_gate_ms={reuse_gate_ms:.3f};"
+            f"reresolve_calls_ms={reresolve_calls_ms:.3f};"
             f"materialize_calls_ms={materialize_calls_ms:.3f};"
             f"sources={len(materialized_by_source)};anchors={anchor_count};"
             f"flows={flow_count};surfaces={surface_count};"
@@ -695,6 +775,11 @@ class ContextorFacade:
                 registry,
                 mods,
                 raw_artifacts,
+                previous_state=(
+                    previous_canonical_state.state
+                    if previous_canonical_state
+                    else None
+                ),
             )
             from contextor.core.lineage_query.index import (
                 build_lineage_query_indexes,
diff --git a/tests/test_full_analysis_lineage_materialization.py b/tests/test_full_analysis_lineage_materialization.py
index 9cf7c10..e62492a 100644
--- a/tests/test_full_analysis_lineage_materialization.py
+++ b/tests/test_full_analysis_lineage_materialization.py
@@ -1,8 +1,10 @@
-import pytest
 import ast
 from contextlib import contextmanager
+from dataclasses import replace
 from types import SimpleNamespace
 
+import pytest
+
 from contextor.core.api.facade import (
     ContextorFacade,
     _materialize_full_analysis_lineage,
@@ -94,6 +96,41 @@ def _fresh_slice(status=LineageFamilyStatus.FRESH):
     )
 
 
+def _owned_fresh_slice(*, fingerprint="fingerprint"):
+    span = SourceSpan(1, 0, 1, 1)
+    module_anchor = "occ:v1:module:root:i:0:n:pkg"
+    return ExtractedLineageSourceFacts(
+        source_key="pkg.py",
+        source_fingerprint=fingerprint,
+        anchors=(ExtractedAnchorFact(module_anchor, "module", span),),
+        flows=(
+            ExtractedFlowFact(
+                "flow",
+                ExtractedOccurrenceRef(module_anchor),
+                ExtractedSymbolicRef(
+                    ExtractedSymbolicKind.DEFINITION, "pkg", "target"
+                ),
+                LineageRelation.CALL_RESULT,
+                span,
+                ResolutionKind.CALL_EXACT,
+                LineageConfidence.CONFIRMED,
+                owner_local_id=module_anchor,
+            ),
+        ),
+    )
+
+
+def _previous_lineage_state(lineage_facts_by_source):
+    return SimpleNamespace(
+        resync_required=False,
+        lineage_facts_state="fresh",
+        lineage_query_index_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+        lineage_semantic_anchor_bindings_complete=True,
+        lineage_facts_by_source=lineage_facts_by_source,
+    )
+
+
 def _index(*, facts=None, skipped=()):
     return SimpleNamespace(
         modules={"pkg": SimpleNamespace(path="pkg.py")},
@@ -336,3 +373,120 @@ def test_domain_rejects_exact_surface_with_bare_local_occurrence():
             "target",
             declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION,
         )
+
+
+def test_full_analysis_reuses_exact_previous_lineage_slice_object():
+    facts = _owned_fresh_slice()
+    index = _index(facts={"pkg.py": facts})
+    artifacts = {"pkg": {"own_symbols": ["target"]}}
+    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
+
+    first_mapping, _, _ = _materialize_full_analysis_lineage(
+        index, registry, index.modules, artifacts
+    )
+    previous = first_mapping["pkg.py"]
+
+    second_mapping, family_state, version = _materialize_full_analysis_lineage(
+        index,
+        registry,
+        index.modules,
+        artifacts,
+        previous_state=_previous_lineage_state(first_mapping),
+    )
+
+    assert family_state == "fresh"
+    assert version == LINEAGE_FACTS_SEMANTIC_VERSION
+    assert second_mapping["pkg.py"] is previous
+
+
+def test_full_analysis_materializes_changed_source_fingerprint():
+    artifacts = {"pkg": {"own_symbols": ["target"]}}
+    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
+    first_index = _index(facts={"pkg.py": _owned_fresh_slice(fingerprint="old")})
+    first_mapping, _, _ = _materialize_full_analysis_lineage(
+        first_index, registry, first_index.modules, artifacts
+    )
+    second_index = _index(facts={"pkg.py": _owned_fresh_slice(fingerprint="new")})
+
+    second_mapping, _, _ = _materialize_full_analysis_lineage(
+        second_index,
+        registry,
+        second_index.modules,
+        artifacts,
+        previous_state=_previous_lineage_state(first_mapping),
+    )
+
+    assert second_mapping["pkg.py"] is not first_mapping["pkg.py"]
+    assert second_mapping["pkg.py"].manifest.source_fingerprint == "new"
+
+
+def test_full_analysis_reresolves_changed_global_identity_without_materializing(
+    monkeypatch,
+):
+    from contextor.core.analysis import lineage_materialization
+
+    facts = _owned_fresh_slice()
+    index = _index(facts={"pkg.py": facts})
+    artifacts = {"pkg": {"own_symbols": ["target"]}}
+    first_registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
+    first_mapping, _, _ = _materialize_full_analysis_lineage(
+        index, first_registry, index.modules, artifacts
+    )
+
+    def fail_materialize(*_args, **_kwargs):
+        raise AssertionError("global identity change must reresolve, not materialize")
+
+    monkeypatch.setattr(
+        lineage_materialization,
+        "materialize_lineage_source_facts",
+        fail_materialize,
+    )
+    second_registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/2"})
+    second_mapping, _, _ = _materialize_full_analysis_lineage(
+        index,
+        second_registry,
+        index.modules,
+        artifacts,
+        previous_state=_previous_lineage_state(first_mapping),
+    )
+
+    assert second_mapping["pkg.py"] is not first_mapping["pkg.py"]
+    assert second_mapping["pkg.py"].flows[0].target == SemanticEndpoint("A1/2")
+
+
+def test_full_analysis_falls_back_to_materialization_for_missing_origin(monkeypatch):
+    from contextor.core.analysis import lineage_materialization
+
+    facts = _owned_fresh_slice()
+    index = _index(facts={"pkg.py": facts})
+    artifacts = {"pkg": {"own_symbols": ["target"]}}
+    registry = _ReadOnlyRegistry({"pkg": "1/1"}, {"pkg::target": "A1/1"})
+    first_mapping, _, _ = _materialize_full_analysis_lineage(
+        index, registry, index.modules, artifacts
+    )
+    previous = first_mapping["pkg.py"]
+    legacy_previous = replace(previous, semantic_endpoint_origins=())
+    calls = []
+    original_materialize = lineage_materialization.materialize_lineage_source_facts
+
+    def counted_materialize(*args, **kwargs):
+        calls.append(1)
+        return original_materialize(*args, **kwargs)
+
+    monkeypatch.setattr(
+        lineage_materialization,
+        "materialize_lineage_source_facts",
+        counted_materialize,
+    )
+    second_mapping, _, _ = _materialize_full_analysis_lineage(
+        index,
+        registry,
+        index.modules,
+        artifacts,
+        previous_state=_previous_lineage_state({"pkg.py": legacy_previous}),
+    )
+
+    assert calls == [1]
+    assert second_mapping["pkg.py"] is not legacy_previous
+    assert second_mapping["pkg.py"].flows[0].target == SemanticEndpoint("A1/1")
+    assert second_mapping["pkg.py"].semantic_endpoint_origins

```

