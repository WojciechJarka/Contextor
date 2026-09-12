# Antigravity Walkthrough

STATUS

PASS_TARGETED. The active-owner lifecycle repair now uses a compact canonical semantic-origin sidecar; the duplicated lineage_extracted_facts_by_source state/candidate/snapshot payload is removed. No measurements were performed.

ROOT_CAUSE

A materialized SemanticEndpoint retains an opaque active owner_id and optional slot, but discards the symbolic fields required to reapply exact materialization when the active owner domain changes. The previous repair retained every ExtractedLineageSourceFacts slice to recover those fields, which duplicated the full lineage graph payload.

FINAL_ARCHITECTURE

Canonical state retains one MaterializedLineageSourceFacts representation per source. The slice now carries an immutable, sorted compact semantic_endpoint_origins tuple only for endpoint positions strengthened from symbolic references to SemanticEndpoint.

REMOVED_DUPLICATION

lineage_extracted_facts_by_source was removed from RepositoryAnalysisState, CandidateState, full-analysis state construction, incremental publication, and snapshot state normalization. Snapshot normalization strips the obsolete historical attribute when encountered so it is not retained after hydration.

COMPACT_ORIGIN_MODEL

Each SemanticEndpointOrigin stores the slice source key/fingerprint, stable fact local id, endpoint role (FLOW_SOURCE, FLOW_TARGET, or SURFACE_EXPOSED), and exact symbolic fields: kind, module name, symbol name, and source-local id. It contains no anchors, flows, surfaces, AST, or second extracted representation.

MaterializedLineageSourceFacts validates sorted/unique origins, one origin per locator, source key/fingerprint equality with its manifest, and that each locator resolves to an existing semantic endpoint at the declared fact role.

REMATERIALIZATION_CONTRACT

reresolve_materialized_lineage_source_facts is pure and deterministic. It keeps occurrence refs unchanged, re-resolves symbolic refs using the existing exact proof helper, and re-resolves semantic endpoints from compact origin using that same helper. A current active owner can yield a new-generation endpoint; an absent/invalid owner degrades to MaterializedSymbolicRef. No source scan, parse, or extraction is performed for untouched slices.

At identity_sync_required, finalized registry sync, changed-source materialization, and all-slice compact re-resolution stay within the existing COW/registry transaction. A SemanticEndpoint lacking origin raises the narrow legacy-origin condition; the candidate remains publishable but lineage is marked STALE rather than falsely FRESH.

LEGACY_SNAPSHOT_BEHAVIOR

Legacy slices without origins still hydrate. They are not rejected merely because an old SemanticEndpoint lacks the new sidecar. On a later identity-domain change, an untouched legacy semantic endpoint without origin fail-closes the family to STALE; no owner/name heuristic is attempted.

OWNER_DELETION_PROOF

The focused deletion parity case begins with an untouched consumer semantic endpoint. Provider deletion removes only the provider slice. Compact re-resolution converts the consumer endpoint to MaterializedSymbolicRef, and the resulting incremental slice equals fresh full materialization of the same final source domain.

OWNER_INTRODUCTION_PROOF

The consumer initially carries MaterializedSymbolicRef, so no origin is stored. When the provider becomes active, all existing materialized slices are re-resolved and the untouched consumer is promoted to the same SemanticEndpoint and compact origin emitted by fresh full materialization.

GENERATION_PROOF

The focused generation case moves provider::target from A:provider/1 to A:provider/2. Stored origin re-resolves against the final active registry and produces the A:provider/2 endpoint. The previous generation never remains current.

SNAPSHOT_PROOF

Snapshot roundtrip preserves compact origin metadata. A hydrated consumer slice can be re-resolved from semantic to symbolic after owner removal and back to a current-generation semantic endpoint after owner introduction, without source work.

CORRUPTION_PROOF

Snapshot normalization rejects duplicate locators, wrong source key, wrong fingerprint, missing fact locator, and role/fact mismatches. Revalidation reconstructs the frozen slice, which executes the canonical sidecar validator fail-closed.

ATOMICITY_PROOF

The focused re-resolution failure test injects an exception for the untouched consumer after registry sync. It verifies no canonical modules, artifacts, materialized lineage, registry mappings, or acknowledgement are published. The existing identity-sync rollback regression remains green.

INVARIANTS_PRESERVED

- interface_descriptors={}, D1/build-state freshness, MCP query tools, and output budgeting were untouched.
- The same exact resolution/confidence/slot/descriptor proof remains authoritative.
- Materialized occurrences remain slice-local; symbolic refs remain symbolic boundaries.
- No external lineage store was introduced.
- A FRESH lineage family cannot certify an unresolvable legacy semantic endpoint after an identity-domain change.

FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\lineage_materialization.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py
- C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py
- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py
- C:\Temp\Contextor_Repo\tests\analysis\test_lineage_materialization.py
- C:\Temp\Contextor_Repo\tests\test_full_analysis_lineage_materialization.py
- C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py

walkthrough.md is excluded from FILES_CHANGED and ACTUAL_DIFF. Current git diff includes the immediately preceding lifecycle repair in overlapping files; this report attributes only the compact-origin redesign, while ACTUAL_DIFF preserves the complete current unified diff as required.

TESTS_RUN

- .venv\Scripts\python.exe -m pytest tests/test_lineage_state_lifecycle.py tests/test_full_analysis_lineage_materialization.py tests/analysis/test_lineage_materialization.py -q -> 53 passed.
- .venv\Scripts\python.exe -m pytest tests/test_live_state_store.py -q -> 20 passed.
- .venv\Scripts\python.exe -m pytest tests/test_completeness_freshness_parity_proof.py -q -> 31 passed.
- .venv\Scripts\python.exe -m py_compile on all changed production and test Python files -> passed.
- git diff --check on the ten task files, excluding this raw-diff report -> passed.
- Full pytest was not run, per task.

REMAINING_RISKS

The compact sidecar deliberately covers only endpoints strengthened by this materializer. Legacy semantic endpoints without provenance cannot regain exact symbolic origin and therefore degrade the family to STALE on the next identity-domain change. Full pytest and LIVE F2L-READY certification remain intentionally pending.

CONTEXTOR_TOOL_USAGE

Contextor MCP was active immediately; deferred loading was not needed. Contextor-first discovery used get_mcp_documentation, get_artifacts_for_module, search_source, and get_symbol_implementation to inspect the materializer, semantic domain slice, incremental lifecycle, candidate state, full-analysis path, and snapshot normalizer. rg was used only afterward for textual verification of removal.

ACTUAL_DIFF

~~~diff
warning: in the working copy of 'contextor/core/analysis/incremental/engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/analysis/incremental/plan_executor.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/analysis/lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/analysis/state_manager.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/domain/lineage_facts.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/live_state/store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_full_analysis_lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_lineage_state_lifecycle.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 9dcf625..c0ed5b6 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -124,7 +124,6 @@ class IncrementalAnalysisEngine:
             )
 
             candidate.lineage_facts_by_source.pop(source_path, None)
-            candidate.lineage_extracted_facts_by_source.pop(source_path, None)
             if candidate.lineage_facts_state == LineageFamilyStatus.NOT_MATERIALIZED.value:
                 candidate.lineage_facts_state = LineageFamilyStatus.NOT_MATERIALIZED.value
                 candidate.lineage_facts_semantic_version = None
@@ -158,9 +157,6 @@ class IncrementalAnalysisEngine:
         self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
         self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
         self.state.module_parse_freshness = candidate.module_parse_freshness
-        self.state.lineage_extracted_facts_by_source = (
-            candidate.lineage_extracted_facts_by_source
-        )
         self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
         self.state.lineage_facts_state = candidate.lineage_facts_state
         self.state.lineage_facts_semantic_version = (
@@ -176,10 +172,12 @@ class IncrementalAnalysisEngine:
         delete: bool = False,
         rematerialize_all: bool = False,
     ) -> None:
-        """Install/remove lineage and optionally rebuild all retained slices."""
+        """Install/remove lineage and re-resolve canonical slices after identity sync."""
         from contextor.core.analysis.lineage_materialization import (
+            LineageOriginUnavailableError,
             LineageResolutionContext,
             materialize_lineage_source_facts,
+            reresolve_materialized_lineage_source_facts,
         )
         from contextor.core.domain.lineage_facts import (
             LINEAGE_FACTS_SEMANTIC_VERSION,
@@ -193,12 +191,10 @@ class IncrementalAnalysisEngine:
             Path(str(module.path)).as_posix()
             for module in candidate.modules.values()
         }
-        extracted_by_source = candidate.lineage_extracted_facts_by_source
         lineage_by_source = candidate.lineage_facts_by_source
 
         if delete:
             lineage_by_source.pop(source_path, None)
-            extracted_by_source.pop(source_path, None)
             candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
         else:
             if extracted_lineage_facts is None:
@@ -207,26 +203,10 @@ class IncrementalAnalysisEngine:
                 raise ValueError("Extracted lineage source key does not match incremental source.")
             if source_path not in eligible_source_keys:
                 raise ValueError("Incremental lineage source is outside the active candidate.")
-            extracted_by_source[source_path] = extracted_lineage_facts
-
-        foreign_extracted_keys = set(extracted_by_source) - eligible_source_keys
-        if foreign_extracted_keys:
-            raise ValueError(
-                "Extracted lineage contains sources outside the active candidate: "
-                f"{sorted(foreign_extracted_keys)!r}"
-            )
-        for source_key, extracted in extracted_by_source.items():
-            if extracted.source_key != source_key:
-                raise ValueError(
-                    "Extracted lineage mapping key does not match its source key."
-                )
 
-        source_keys_to_materialize = (
-            tuple(sorted(extracted_by_source))
-            if rematerialize_all
-            else (() if delete else (source_path,))
-        )
-        if source_keys_to_materialize:
+        needs_resolution = rematerialize_all or not delete
+        origin_unavailable = False
+        if needs_resolution:
             active_module_names = set(candidate.modules)
             active_artifact_names = collect_qualified_artifact_identities(
                 candidate.artifacts
@@ -260,8 +240,8 @@ class IncrementalAnalysisEngine:
                 ),
                 interface_descriptors={},
             )
-            for source_key in source_keys_to_materialize:
-                extracted = extracted_by_source[source_key]
+            if not delete:
+                extracted = extracted_lineage_facts
                 materialized = materialize_lineage_source_facts(
                     extracted,
                     resolution,
@@ -274,15 +254,20 @@ class IncrementalAnalysisEngine:
                     raise ValueError(
                         "Materialized lineage manifest does not match extracted source."
                     )
-                lineage_by_source[source_key] = materialized
+                lineage_by_source[source_path] = materialized
+            if rematerialize_all:
+                for source_key in sorted(lineage_by_source):
+                    try:
+                        lineage_by_source[source_key] = (
+                            reresolve_materialized_lineage_source_facts(
+                                lineage_by_source[source_key],
+                                resolution,
+                            )
+                        )
+                    except LineageOriginUnavailableError:
+                        origin_unavailable = True
             candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
 
-        unrebuildable_source_keys = (
-            set(lineage_by_source) - set(extracted_by_source)
-            if rematerialize_all
-            else set()
-        )
-
         foreign_source_keys = set(lineage_by_source) - eligible_source_keys
         if foreign_source_keys:
             raise ValueError(
@@ -292,7 +277,7 @@ class IncrementalAnalysisEngine:
         missing_source_keys = eligible_source_keys - set(lineage_by_source)
         if getattr(self.state, "resync_required", False):
             candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
-        elif unrebuildable_source_keys:
+        elif origin_unavailable:
             candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
         elif missing_source_keys:
             candidate.lineage_facts_state = (
@@ -707,9 +692,6 @@ class IncrementalAnalysisEngine:
             # certify it fresh again.
             self.state.resync_required = True
         self.state.module_usages = candidate.module_usages
-        self.state.lineage_extracted_facts_by_source = (
-            candidate.lineage_extracted_facts_by_source
-        )
         self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
         self.state.lineage_facts_state = candidate.lineage_facts_state
         self.state.lineage_facts_semantic_version = (
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 2a10648..86948a6 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -21,10 +21,7 @@ from contextor.core.analysis.state_manager import (
     validate_canonical_artifact_consumption_coverage,
 )
 from contextor.core.domain.graph import ProjectGraph
-from contextor.core.domain.lineage_facts import (
-    ExtractedLineageSourceFacts,
-    MaterializedLineageSourceFacts,
-)
+from contextor.core.domain.lineage_facts import MaterializedLineageSourceFacts
 from contextor.core.domain.module import Module
 from contextor.core.domain.refresh_plan import RefreshPlan
 from contextor.core.domain.usage_facts import ModuleUsageFacts
@@ -48,7 +45,6 @@ class CandidateState:
     syntax_diagnostics_by_path: Dict[str, Dict[str, Any]]
     syntax_diagnostics_state: str
     module_usages: Dict[str, Any]
-    lineage_extracted_facts_by_source: Dict[str, ExtractedLineageSourceFacts]
     lineage_facts_by_source: Dict[str, MaterializedLineageSourceFacts]
     lineage_facts_state: str
     lineage_facts_semantic_version: str | None
@@ -254,9 +250,6 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
         syntax_diagnostics_by_path=dict(getattr(state, "syntax_diagnostics_by_path", {}) or {}),
         syntax_diagnostics_state=getattr(state, "syntax_diagnostics_state", "not_materialized"),
         module_usages=dict(getattr(state, "module_usages", {}) or {}),
-        lineage_extracted_facts_by_source=dict(
-            getattr(state, "lineage_extracted_facts_by_source", {}) or {}
-        ),
         lineage_facts_by_source=dict(
             getattr(state, "lineage_facts_by_source", {}) or {}
         ),
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index 63a24b7..db4978c 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -25,6 +25,8 @@ from contextor.core.domain.lineage_facts import (
     ParameterKind,
     ResolutionKind,
     SemanticEndpoint,
+    SemanticEndpointOrigin,
+    SemanticEndpointRole,
     SemanticInterfaceDescriptor,
     SourceLineageManifest,
     build_module_global_slot,
@@ -70,6 +72,10 @@ class LineageResolutionContext:
                 )
 
 
+class LineageOriginUnavailableError(ValueError):
+    """A legacy semantic endpoint cannot be safely re-resolved."""
+
+
 def materialize_lineage_source_facts(
     extracted: ExtractedLineageSourceFacts,
     resolution: LineageResolutionContext,
@@ -87,17 +93,37 @@ def materialize_lineage_source_facts(
         )
 
     descriptors: dict[str, SemanticInterfaceDescriptor] = {}
+    origins: list[SemanticEndpointOrigin] = []
 
     def endpoint(
         reference: ExtractedOccurrenceRef | ExtractedSymbolicRef,
         kind: ResolutionKind,
         confidence: LineageConfidence,
+        fact_local_id: str,
+        endpoint_role: SemanticEndpointRole,
     ) -> MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint:
         if isinstance(reference, ExtractedOccurrenceRef):
             return occurrence(reference.local_id)
-        return _symbolic_endpoint(
-            reference, resolution, descriptors, kind, confidence, extracted
+        resolved = _symbolic_endpoint(
+            reference,
+            resolution,
+            descriptors,
+            kind,
+            confidence,
+            extracted.source_key,
+            extracted.source_fingerprint,
         )
+        if isinstance(resolved, SemanticEndpoint):
+            origins.append(
+                _semantic_origin(
+                    reference,
+                    extracted.source_key,
+                    extracted.source_fingerprint,
+                    fact_local_id,
+                    endpoint_role,
+                )
+            )
+        return resolved
     anchors = tuple(
         sorted(
             MaterializedAnchorFact(
@@ -106,39 +132,53 @@ def materialize_lineage_source_facts(
             for anchor in extracted.anchors
         )
     )
-    flows = tuple(
-        sorted(
-            MaterializedFlowFact(
+    flows = tuple(sorted(
+        MaterializedFlowFact(
+            flow.local_id,
+            endpoint(
+                flow.source,
+                flow.resolution_kind,
+                flow.confidence,
                 flow.local_id,
-                endpoint(flow.source, flow.resolution_kind, flow.confidence),
-                endpoint(flow.target, flow.resolution_kind, flow.confidence),
-                flow.relation,
-                flow.evidence,
+                SemanticEndpointRole.FLOW_SOURCE,
+            ),
+            endpoint(
+                flow.target,
                 flow.resolution_kind,
                 flow.confidence,
-                flow.dynamic_boundary,
-                flow.provider,
-            )
-            for flow in extracted.flows
+                flow.local_id,
+                SemanticEndpointRole.FLOW_TARGET,
+            ),
+            flow.relation,
+            flow.evidence,
+            flow.resolution_kind,
+            flow.confidence,
+            flow.dynamic_boundary,
+            flow.provider,
         )
-    )
-    surfaces = tuple(
-        sorted(
-            MaterializedSurfaceFact(
-                surface.local_id,
-                surface.kind,
-                endpoint(surface.exposed, surface.resolution_kind, surface.confidence),
-                surface.evidence,
+        for flow in extracted.flows
+    ))
+    surfaces = tuple(sorted(
+        MaterializedSurfaceFact(
+            surface.local_id,
+            surface.kind,
+            endpoint(
+                surface.exposed,
                 surface.resolution_kind,
                 surface.confidence,
-                surface.declared_name,
-                surface.dynamic_boundary,
-                surface.provider,
-                surface.declaration_evidence,
-            )
-            for surface in extracted.surfaces
+                surface.local_id,
+                SemanticEndpointRole.SURFACE_EXPOSED,
+            ),
+            surface.evidence,
+            surface.resolution_kind,
+            surface.confidence,
+            surface.declared_name,
+            surface.dynamic_boundary,
+            surface.provider,
+            surface.declaration_evidence,
         )
-    )
+        for surface in extracted.surfaces
+    ))
     manifest = SourceLineageManifest(
         extracted.source_key,
         extracted.source_fingerprint,
@@ -150,7 +190,159 @@ def materialize_lineage_source_facts(
         extracted.resource_limit_reason,
     )
     return MaterializedLineageSourceFacts(
-        manifest, anchors, flows, surfaces, tuple(sorted(descriptors.values()))
+        manifest,
+        anchors,
+        flows,
+        surfaces,
+        tuple(sorted(descriptors.values())),
+        tuple(sorted(origins)),
+    )
+
+
+def reresolve_materialized_lineage_source_facts(
+    materialized: MaterializedLineageSourceFacts,
+    resolution: LineageResolutionContext,
+) -> MaterializedLineageSourceFacts:
+    """Re-resolve one canonical slice without source, AST, or extracted facts."""
+
+    if not isinstance(materialized, MaterializedLineageSourceFacts):
+        raise TypeError("materialized must be MaterializedLineageSourceFacts.")
+    if not isinstance(resolution, LineageResolutionContext):
+        raise TypeError("resolution must be LineageResolutionContext.")
+
+    origins = {
+        (origin.fact_local_id, origin.endpoint_role): origin
+        for origin in materialized.semantic_endpoint_origins
+    }
+    descriptors: dict[str, SemanticInterfaceDescriptor] = {}
+    resolved_origins: list[SemanticEndpointOrigin] = []
+
+    def endpoint(
+        current: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint,
+        resolution_kind: ResolutionKind,
+        confidence: LineageConfidence,
+        fact_local_id: str,
+        endpoint_role: SemanticEndpointRole,
+    ) -> MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint:
+        if isinstance(current, MaterializedOccurrenceRef):
+            return current
+        if isinstance(current, MaterializedSymbolicRef):
+            reference = ExtractedSymbolicRef(
+                current.kind,
+                current.module_name,
+                current.symbol_name,
+                current.source_local_id,
+            )
+            source_key = current.source_key
+            source_fingerprint = current.source_fingerprint
+        else:
+            origin = origins.get((fact_local_id, endpoint_role))
+            if origin is None:
+                raise LineageOriginUnavailableError(
+                    "Semantic endpoint is missing compact symbolic origin."
+                )
+            reference = ExtractedSymbolicRef(
+                origin.kind,
+                origin.module_name,
+                origin.symbol_name,
+                origin.source_local_id,
+            )
+            source_key = origin.source_key
+            source_fingerprint = origin.source_fingerprint
+        resolved = _symbolic_endpoint(
+            reference,
+            resolution,
+            descriptors,
+            resolution_kind,
+            confidence,
+            source_key,
+            source_fingerprint,
+        )
+        if isinstance(resolved, SemanticEndpoint):
+            resolved_origins.append(
+                _semantic_origin(
+                    reference,
+                    source_key,
+                    source_fingerprint,
+                    fact_local_id,
+                    endpoint_role,
+                )
+            )
+        return resolved
+
+    flows = tuple(sorted(
+        MaterializedFlowFact(
+            flow.local_id,
+            endpoint(
+                flow.source,
+                flow.resolution_kind,
+                flow.confidence,
+                flow.local_id,
+                SemanticEndpointRole.FLOW_SOURCE,
+            ),
+            endpoint(
+                flow.target,
+                flow.resolution_kind,
+                flow.confidence,
+                flow.local_id,
+                SemanticEndpointRole.FLOW_TARGET,
+            ),
+            flow.relation,
+            flow.evidence,
+            flow.resolution_kind,
+            flow.confidence,
+            flow.dynamic_boundary,
+            flow.provider,
+        )
+        for flow in materialized.flows
+    ))
+    surfaces = tuple(sorted(
+        MaterializedSurfaceFact(
+            surface.local_id,
+            surface.kind,
+            endpoint(
+                surface.exposed,
+                surface.resolution_kind,
+                surface.confidence,
+                surface.local_id,
+                SemanticEndpointRole.SURFACE_EXPOSED,
+            ),
+            surface.evidence,
+            surface.resolution_kind,
+            surface.confidence,
+            surface.declared_name,
+            surface.dynamic_boundary,
+            surface.provider,
+            surface.declaration_evidence,
+        )
+        for surface in materialized.surfaces
+    ))
+    return MaterializedLineageSourceFacts(
+        materialized.manifest,
+        materialized.anchors,
+        flows,
+        surfaces,
+        tuple(sorted(descriptors.values())),
+        tuple(sorted(resolved_origins)),
+    )
+
+
+def _semantic_origin(
+    reference: ExtractedSymbolicRef,
+    source_key: str,
+    source_fingerprint: str,
+    fact_local_id: str,
+    endpoint_role: SemanticEndpointRole,
+) -> SemanticEndpointOrigin:
+    return SemanticEndpointOrigin(
+        source_key,
+        source_fingerprint,
+        fact_local_id,
+        endpoint_role,
+        reference.kind,
+        reference.module_name,
+        reference.symbol_name,
+        reference.source_local_id,
     )
 
 
@@ -160,10 +352,11 @@ def _symbolic_endpoint(
     descriptors: dict[str, SemanticInterfaceDescriptor],
     resolution_kind: ResolutionKind,
     confidence: LineageConfidence,
-    extracted: ExtractedLineageSourceFacts,
+    source_key: str,
+    source_fingerprint: str,
 ) -> MaterializedSymbolicRef | SemanticEndpoint:
     symbolic = MaterializedSymbolicRef(
-        extracted.source_key, extracted.source_fingerprint, reference.kind,
+        source_key, source_fingerprint, reference.kind,
         reference.module_name, reference.symbol_name, reference.source_local_id,
     )
     if not claims_exact_semantic_target(resolution_kind, confidence):
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index fb9648d..a1fcfcd 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -4,10 +4,7 @@ from dataclasses import dataclass, field
 from typing import Dict, Any, Optional
 from pathlib import Path
 
-from contextor.core.domain.lineage_facts import (
-    ExtractedLineageSourceFacts,
-    MaterializedLineageSourceFacts,
-)
+from contextor.core.domain.lineage_facts import MaterializedLineageSourceFacts
 
 
 @dataclass
@@ -98,9 +95,6 @@ class RepositoryAnalysisState:
     syntax_diagnostics_state: str = "not_materialized"
     module_usages: Dict[str, Any] = field(default_factory=dict)
     module_usages_manifest: Dict[str, Dict[str, str]] = field(default_factory=dict)
-    lineage_extracted_facts_by_source: Dict[str, ExtractedLineageSourceFacts] = field(
-        default_factory=dict
-    )
     lineage_facts_by_source: Dict[str, MaterializedLineageSourceFacts] = field(default_factory=dict)
     lineage_facts_state: str = "not_materialized"
     lineage_facts_semantic_version: str | None = None
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index f607248..279fd3b 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -703,9 +703,6 @@ class ContextorFacade:
                 syntax_diagnostics_state=syntax_diagnostics_state,
                 module_usages=module_usages,
                 module_usages_manifest=module_usages_manifest,
-                lineage_extracted_facts_by_source=dict(
-                    getattr(index, "lineage_facts_by_source", {}) or {}
-                ),
                 lineage_facts_by_source=lineage_facts_by_source,
                 lineage_facts_state=lineage_facts_state,
                 lineage_facts_semantic_version=lineage_facts_semantic_version,
diff --git a/contextor/core/domain/lineage_facts.py b/contextor/core/domain/lineage_facts.py
index 69e5ea1..6b2a284 100644
--- a/contextor/core/domain/lineage_facts.py
+++ b/contextor/core/domain/lineage_facts.py
@@ -110,6 +110,12 @@ class ExtractedSymbolicKind(str, Enum):
     PUBLIC_TARGET = "public_target"
 
 
+class SemanticEndpointRole(str, Enum):
+    FLOW_SOURCE = "flow_source"
+    FLOW_TARGET = "flow_target"
+    SURFACE_EXPOSED = "surface_exposed"
+
+
 @dataclass(frozen=True, order=True)
 class SourceSpan:
     """Exact source evidence; it is never semantic identity."""
@@ -217,6 +223,33 @@ class MaterializedSymbolicRef:
             _require_token(self.source_local_id, "source_local_id")
 
 
+@dataclass(frozen=True, order=True)
+class SemanticEndpointOrigin:
+    """Compact symbolic provenance for one strengthened semantic endpoint."""
+
+    source_key: str
+    source_fingerprint: str
+    fact_local_id: str
+    endpoint_role: SemanticEndpointRole
+    kind: ExtractedSymbolicKind
+    module_name: str
+    symbol_name: str
+    source_local_id: str | None = None
+
+    def __post_init__(self) -> None:
+        _require_token(self.source_key, "source_key")
+        _require_token(self.source_fingerprint, "source_fingerprint")
+        _require_token(self.fact_local_id, "fact_local_id")
+        if not isinstance(self.endpoint_role, SemanticEndpointRole):
+            raise TypeError("endpoint_role must be SemanticEndpointRole.")
+        if not isinstance(self.kind, ExtractedSymbolicKind):
+            raise TypeError("kind must be ExtractedSymbolicKind.")
+        _require_token(self.module_name, "module_name")
+        _require_token(self.symbol_name, "symbol_name")
+        if self.source_local_id is not None:
+            _require_token(self.source_local_id, "source_local_id")
+
+
 @dataclass(frozen=True, order=True)
 class ExtractedAnchorFact:
     local_id: str
@@ -412,12 +445,14 @@ class MaterializedLineageSourceFacts:
     flows: tuple[MaterializedFlowFact, ...] = ()
     surfaces: tuple[MaterializedSurfaceFact, ...] = ()
     interface_descriptors: tuple[SemanticInterfaceDescriptor, ...] = ()
+    semantic_endpoint_origins: tuple[SemanticEndpointOrigin, ...] = ()
 
     def __post_init__(self) -> None:
         _require_sorted_unique(self.anchors, "anchors")
         _require_sorted_unique(self.flows, "flows")
         _require_sorted_unique(self.surfaces, "surfaces")
         _require_sorted_unique(self.interface_descriptors, "interface_descriptors")
+        _require_sorted_unique(self.semantic_endpoint_origins, "semantic_endpoint_origins")
         if self.manifest.status == LineageFamilyStatus.FRESH:
             expected = (len(self.anchors), len(self.flows), len(self.surfaces))
             actual = (
@@ -434,6 +469,32 @@ class MaterializedLineageSourceFacts:
             _require_slice_occurrence(flow.target, self.manifest)
         for surface in self.surfaces:
             _require_slice_occurrence(surface.exposed, self.manifest)
+        self._validate_semantic_endpoint_origins()
+
+    def _validate_semantic_endpoint_origins(self) -> None:
+        flow_by_id = {flow.local_id: flow for flow in self.flows}
+        surface_by_id = {surface.local_id: surface for surface in self.surfaces}
+        locators: set[tuple[str, SemanticEndpointRole]] = set()
+        for origin in self.semantic_endpoint_origins:
+            if (
+                origin.source_key != self.manifest.source_key
+                or origin.source_fingerprint != self.manifest.source_fingerprint
+            ):
+                raise ValueError("Semantic endpoint origin must belong to its slice.")
+            locator = (origin.fact_local_id, origin.endpoint_role)
+            if locator in locators:
+                raise ValueError("Semantic endpoint origins must have unique locators.")
+            locators.add(locator)
+            if origin.endpoint_role is SemanticEndpointRole.FLOW_SOURCE:
+                endpoint = getattr(flow_by_id.get(origin.fact_local_id), "source", None)
+            elif origin.endpoint_role is SemanticEndpointRole.FLOW_TARGET:
+                endpoint = getattr(flow_by_id.get(origin.fact_local_id), "target", None)
+            else:
+                endpoint = getattr(surface_by_id.get(origin.fact_local_id), "exposed", None)
+            if not isinstance(endpoint, SemanticEndpoint):
+                raise ValueError(
+                    "Semantic endpoint origin must locate a semantic endpoint."
+                )
 
 
 @dataclass(frozen=True, order=True)
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index fa7d9b4..4ff7f4f 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -14,7 +14,6 @@ from typing import Any
 
 from contextor.core.domain.lineage_facts import (
     LINEAGE_FACTS_SEMANTIC_VERSION,
-    ExtractedLineageSourceFacts,
     LineageConfidence,
     LineageFamilyStatus,
     LineageRelation,
@@ -27,6 +26,8 @@ from contextor.core.domain.lineage_facts import (
     ProviderRef,
     ResolutionKind,
     SemanticEndpoint,
+    SemanticEndpointOrigin,
+    SemanticEndpointRole,
     SemanticInterfaceDescriptor,
     SourceLineageManifest,
     SourceSpan,
@@ -202,6 +203,14 @@ def _revalidate_lineage_descriptor(
     return replace(descriptor)
 
 
+def _revalidate_lineage_origin(origin: Any) -> SemanticEndpointOrigin:
+    if not isinstance(origin, SemanticEndpointOrigin):
+        raise pickle.UnpicklingError("Invalid lineage semantic endpoint origin.")
+    if not isinstance(origin.endpoint_role, SemanticEndpointRole):
+        raise pickle.UnpicklingError("Invalid lineage semantic endpoint origin role.")
+    return replace(origin)
+
+
 def _revalidate_lineage_slice(
     source_slice: Any,
 ) -> MaterializedLineageSourceFacts:
@@ -228,6 +237,10 @@ def _revalidate_lineage_slice(
             _revalidate_lineage_descriptor(item)
             for item in source_slice.interface_descriptors
         ),
+        semantic_endpoint_origins=tuple(
+            _revalidate_lineage_origin(item)
+            for item in getattr(source_slice, "semantic_endpoint_origins", ())
+        ),
     )
 
 
@@ -240,15 +253,14 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
     try:
         if not hasattr(state, "lineage_facts_by_source"):
             state.lineage_facts_by_source = {}
-        if not hasattr(state, "lineage_extracted_facts_by_source"):
-            state.lineage_extracted_facts_by_source = {}
+        if hasattr(state, "lineage_extracted_facts_by_source"):
+            delattr(state, "lineage_extracted_facts_by_source")
         if not hasattr(state, "lineage_facts_state"):
             state.lineage_facts_state = "not_materialized"
         if not hasattr(state, "lineage_facts_semantic_version"):
             state.lineage_facts_semantic_version = None
 
         raw_mapping = state.lineage_facts_by_source
-        raw_extracted_mapping = state.lineage_extracted_facts_by_source
         raw_family_state = state.lineage_facts_state
         raw_version = state.lineage_facts_semantic_version
 
@@ -256,10 +268,6 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
             raise pickle.UnpicklingError(
                 "Lineage source mapping must be a dict."
             )
-        if not isinstance(raw_extracted_mapping, dict):
-            raise pickle.UnpicklingError(
-                "Extracted lineage source mapping must be a dict."
-            )
         if not isinstance(raw_family_state, str):
             raise pickle.UnpicklingError(
                 "Lineage family state must be a string."
@@ -286,10 +294,6 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
                 raise pickle.UnpicklingError(
                     "Not-materialized lineage cannot have a semantic version."
                 )
-            if raw_extracted_mapping:
-                raise pickle.UnpicklingError(
-                    "Not-materialized lineage cannot retain extracted source facts."
-                )
         elif raw_version != LINEAGE_FACTS_SEMANTIC_VERSION:
             raise pickle.UnpicklingError(
                 "Materialized lineage requires the current semantic version."
@@ -308,24 +312,7 @@ def _normalize_lineage_facts_state(state: Any) -> Any:
                 )
             normalized[source_key] = rebuilt
 
-        extracted_normalized: dict[str, ExtractedLineageSourceFacts] = {}
-        for source_key, extracted in raw_extracted_mapping.items():
-            if not isinstance(source_key, str) or not source_key:
-                raise pickle.UnpicklingError(
-                    "Extracted lineage source key must be a non-empty string."
-                )
-            if not isinstance(extracted, ExtractedLineageSourceFacts):
-                raise pickle.UnpicklingError(
-                    "Invalid extracted lineage source facts."
-                )
-            if extracted.source_key != source_key:
-                raise pickle.UnpicklingError(
-                    "Extracted lineage mapping key does not match source_key."
-                )
-            extracted_normalized[source_key] = extracted
-
         state.lineage_facts_by_source = normalized
-        state.lineage_extracted_facts_by_source = extracted_normalized
         state.lineage_facts_state = family_status.value
         state.lineage_facts_semantic_version = raw_version
         return state
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index 6a47961..c97d171 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -7,6 +7,7 @@ import pytest
 from contextor.core.analysis.lineage_materialization import (
     LineageResolutionContext,
     materialize_lineage_source_facts,
+    reresolve_materialized_lineage_source_facts,
 )
 from contextor.core.domain.lineage_facts import (
     ExtractedAnchorFact,
@@ -24,6 +25,8 @@ from contextor.core.domain.lineage_facts import (
     ProviderRef,
     ResolutionKind,
     SemanticEndpoint,
+    SemanticEndpointOrigin,
+    SemanticEndpointRole,
     SemanticInterfaceDescriptor,
     SourceSpan,
     SurfaceDeclarationEvidence,
@@ -161,6 +164,43 @@ def test_materializer_does_not_mutate_input_mappings():
     assert artifacts == {"pkg.mod::run": "A1/1"}
 
 
+def test_compact_origins_preserve_only_strengthened_endpoint_provenance():
+    span = SourceSpan(1, 0, 1, 1)
+    reference = ExtractedSymbolicRef(
+        ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "target"
+    )
+    facts = _facts(flows=(
+        ExtractedFlowFact(
+            "flow", ExtractedOccurrenceRef("local"), reference,
+            LineageRelation.EXPOSES, span, ResolutionKind.IMPORT_EXACT,
+            LineageConfidence.CONFIRMED,
+        ),
+    ))
+    materialized = materialize_lineage_source_facts(
+        facts, _context(artifacts={"pkg.mod::target": "A1/1"})
+    )
+    assert materialized.flows[0].target == SemanticEndpoint("A1/1")
+    assert materialized.semantic_endpoint_origins == (
+        SemanticEndpointOrigin(
+            "pkg/mod.py", "sha256:test", "flow",
+            SemanticEndpointRole.FLOW_TARGET,
+            ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "target",
+        ),
+    )
+
+    removed = reresolve_materialized_lineage_source_facts(
+        materialized, _context()
+    )
+    assert isinstance(removed.flows[0].target, MaterializedSymbolicRef)
+    assert removed.semantic_endpoint_origins == ()
+
+    restored = reresolve_materialized_lineage_source_facts(
+        removed, _context(artifacts={"pkg.mod::target": "A1/2"})
+    )
+    assert restored.flows[0].target == SemanticEndpoint("A1/2")
+    assert len(restored.semantic_endpoint_origins) == 1
+
+
 
 def test_active_symbol_and_state_resolve_only_with_exact_existing_slot():
     span = SourceSpan(1, 0, 1, 1)
@@ -254,4 +294,4 @@ def test_exact_surface_requires_endpoint_but_unresolved_surface_keeps_symbolic_b
     result = materialize_lineage_source_facts(
         unresolved, _context(artifacts={"pkg.mod::target": "A9/1"})
     )
-    assert isinstance(result.surfaces[0].exposed, MaterializedSymbolicRef)
\ No newline at end of file
+    assert isinstance(result.surfaces[0].exposed, MaterializedSymbolicRef)
diff --git a/tests/test_full_analysis_lineage_materialization.py b/tests/test_full_analysis_lineage_materialization.py
index e3d8985..5d84ec3 100644
--- a/tests/test_full_analysis_lineage_materialization.py
+++ b/tests/test_full_analysis_lineage_materialization.py
@@ -183,7 +183,6 @@ def test_real_full_analysis_installs_current_lineage_without_second_extraction(t
     state = captured_states[0]
     assert state.lineage_facts_state == "fresh"
     assert state.lineage_facts_semantic_version == LINEAGE_FACTS_SEMANTIC_VERSION
-    assert set(state.lineage_extracted_facts_by_source) == {"consumer.py", "provider.py"}
     assert set(state.lineage_facts_by_source) == {"consumer.py", "provider.py"}
     assert all(
         source_key == source_slice.manifest.source_key
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index b804803..1c1e37e 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -19,6 +19,7 @@ from contextor.core.analysis.lineage_extraction import extract_lineage_source_fa
 from contextor.core.analysis.lineage_materialization import (
     LineageResolutionContext,
     materialize_lineage_source_facts,
+    reresolve_materialized_lineage_source_facts,
 )
 from contextor.core.analysis.state_manager import RepositoryAnalysisState
 from contextor.core.domain.graph import ProjectGraph
@@ -37,6 +38,7 @@ from contextor.core.domain.lineage_facts import (
     ProviderRef,
     ResolutionKind,
     SemanticEndpoint,
+    SemanticEndpointRole,
     SemanticInterfaceDescriptor,
     SourceLineageManifest,
     SourceSpan,
@@ -505,7 +507,6 @@ def _lineage_state_for_facts(facts, registry, modules, artifacts):
     return RepositoryAnalysisState(
         modules=modules,
         artifacts=artifacts,
-        lineage_extracted_facts_by_source=dict(facts),
         lineage_facts_by_source=materialized,
         lineage_facts_state=family_state,
         lineage_facts_semantic_version=semantic_version,
@@ -546,6 +547,101 @@ def _slice_for(source_key: str) -> MaterializedLineageSourceFacts:
     )
 
 
+def test_identity_sync_legacy_semantic_without_origin_fails_closed_to_stale(tmp_path):
+    legacy = _lineage_slice()
+    other = _slice_for("other.py")
+    state = RepositoryAnalysisState(
+        modules={"pkg": _module("pkg"), "other": _module("other")},
+        artifacts={"pkg": {"own_symbols": set()}, "other": {"own_symbols": set()}},
+        lineage_facts_by_source={"pkg.py": legacy, "other.py": other},
+        lineage_facts_state="fresh",
+        lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
+    )
+    engine, _ = _lineage_engine(
+        state,
+        _LineageRegistry({"pkg": "M:pkg", "other": "M:other"}),
+        tmp_path,
+    )
+    candidate = _prepare_candidate_state(state)
+
+    with engine.registry.read_transaction():
+        engine._update_candidate_lineage_slice(
+            candidate,
+            source_path="other.py",
+            extracted_lineage_facts=_extracted("other.py"),
+            rematerialize_all=True,
+        )
+
+    assert candidate.lineage_facts_state == LineageFamilyStatus.STALE.value
+    assert candidate.lineage_facts_by_source["pkg.py"] is legacy
+
+
+def test_snapshot_round_trip_compact_origin_reresolves_without_source_work(tmp_path):
+    facts = _cross_source_facts()
+    modules = {name: _module(name) for name in ("provider", "consumer")}
+    artifacts = {
+        "provider": {"own_symbols": {"target"}},
+        "consumer": {"own_symbols": set()},
+    }
+    registry = _LifecycleRegistry(
+        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
+        {"provider::target": "A:provider/1"},
+    )
+    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    save_snapshot(state, tmp_path, "compact-origin")
+    loaded, _ = load_snapshot(tmp_path, expected_state_id="compact-origin")
+    consumer = loaded.lineage_facts_by_source["consumer.py"]
+    assert consumer.semantic_endpoint_origins
+
+    removed = reresolve_materialized_lineage_source_facts(
+        consumer,
+        LineageResolutionContext(
+            {"consumer": "M:consumer/1"}, {}, frozenset({"M:consumer/1"}), {}
+        ),
+    )
+    assert isinstance(removed.surfaces[0].exposed, MaterializedSymbolicRef)
+    restored = reresolve_materialized_lineage_source_facts(
+        removed,
+        LineageResolutionContext(
+            {"consumer": "M:consumer/1"},
+            {"provider::target": "A:provider/2"},
+            frozenset({"M:consumer/1", "A:provider/2"}),
+            {},
+        ),
+    )
+    assert restored.surfaces[0].exposed == SemanticEndpoint("A:provider/2")
+
+
+@pytest.mark.parametrize(
+    "origins",
+    [
+        lambda origin: (origin, replace(origin, symbol_name="different")),
+        lambda origin: (replace(origin, source_key="other.py"),),
+        lambda origin: (replace(origin, source_fingerprint="other"),),
+        lambda origin: (replace(origin, fact_local_id="missing"),),
+        lambda origin: (replace(origin, endpoint_role=SemanticEndpointRole.FLOW_SOURCE),),
+    ],
+)
+def test_snapshot_rejects_corrupt_compact_origin(tmp_path, origins):
+    facts = _cross_source_facts()
+    modules = {name: _module(name) for name in ("provider", "consumer")}
+    artifacts = {
+        "provider": {"own_symbols": {"target"}},
+        "consumer": {"own_symbols": set()},
+    }
+    registry = _LifecycleRegistry(
+        {"provider": "M:provider/1", "consumer": "M:consumer/1"},
+        {"provider::target": "A:provider/1"},
+    )
+    state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    source_slice = state.lineage_facts_by_source["consumer.py"]
+    origin = source_slice.semantic_endpoint_origins[0]
+    object.__setattr__(source_slice, "semantic_endpoint_origins", origins(origin))
+    save_snapshot(state, tmp_path, "corrupt-origin")
+
+    assert load_snapshot(tmp_path, expected_state_id="corrupt-origin") is None
+
+
 def test_incremental_lineage_modify_replaces_only_changed_candidate_slice(tmp_path):
     old_pkg = _slice_for("pkg.py")
     other = _slice_for("other.py")
@@ -847,7 +943,6 @@ def test_identity_sync_owner_deletion_matches_fresh_full_materialization_without
         {"provider::target": "A:provider/1"},
     )
     state = _lineage_state_for_facts(facts, registry, modules, artifacts)
-    old_consumer_facts = state.lineage_extracted_facts_by_source["consumer.py"]
     candidate = _prepare_candidate_state(state)
     candidate.modules = {"consumer": modules["consumer"]}
     candidate.artifacts = {"consumer": artifacts["consumer"]}
@@ -902,9 +997,6 @@ def test_identity_sync_owner_deletion_matches_fresh_full_materialization_without
     assert state.lineage_facts_semantic_version == expected_version
     assert set(state.lineage_facts_by_source) == {"consumer.py"}
     assert state.lineage_facts_by_source == expected
-    assert state.lineage_extracted_facts_by_source == {
-        "consumer.py": old_consumer_facts
-    }
     exposed = state.lineage_facts_by_source["consumer.py"].surfaces[0].exposed
     assert isinstance(exposed, MaterializedSymbolicRef)
     assert exposed.module_name == "provider"
@@ -1067,7 +1159,6 @@ def test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_st
     original_modules = dict(state.modules)
     original_artifacts = dict(state.artifacts)
     original_lineage = dict(state.lineage_facts_by_source)
-    original_extracted = dict(state.lineage_extracted_facts_by_source)
     candidate = _prepare_candidate_state(state)
     candidate.modules = {"consumer": modules["consumer"]}
     candidate.artifacts = {"consumer": artifacts["consumer"]}
@@ -1085,13 +1176,13 @@ def test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_st
         lambda **_kwargs: outcome,
     )
 
-    def fail_on_untouched_consumer(extracted, _resolution):
-        if extracted.source_key == "consumer.py":
+    def fail_on_untouched_consumer(source_slice, _resolution):
+        if source_slice.manifest.source_key == "consumer.py":
             raise ValueError("consumer rematerialization failed")
         raise AssertionError("deleted provider should not be rematerialized")
 
     monkeypatch.setattr(
-        "contextor.core.analysis.lineage_materialization.materialize_lineage_source_facts",
+        "contextor.core.analysis.lineage_materialization.reresolve_materialized_lineage_source_facts",
         fail_on_untouched_consumer,
     )
     engine, acknowledged = _lineage_engine(state, registry, tmp_path)
@@ -1111,7 +1202,6 @@ def test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_st
     assert state.modules == original_modules
     assert state.artifacts == original_artifacts
     assert state.lineage_facts_by_source == original_lineage
-    assert state.lineage_extracted_facts_by_source == original_extracted
     assert registry._state["module_registry"]["path_to_id"]["provider"] == "M:provider/1"
     assert registry._state["artifact_registry"]["path_to_id"]["provider::target"] == "A:provider/1"
     assert acknowledged == []

~~~
