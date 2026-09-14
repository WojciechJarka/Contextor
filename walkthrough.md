# P0 L3A retry — lineage reuse gate

## STATUS

SUCCESS. Implemented the supplied fail-closed per-source resolution gate and corrected fixture. No full analysis, benchmark, full pytest, facade, persistence, LIVE, or MCP change.

## CONTEXTOR_DISCOVERY

Before the edit, Contextor confirmed `materialize_lineage_source_facts` as the existing single-slice materializer and its direct helpers `_semantic_anchor_bindings` and `_seed_defining_interface_descriptors`; `reresolve_materialized_lineage_source_facts` remains the existing resolution lifecycle.

After the edit, Contextor resolved the new predicate at `lineage_materialization.py:360-526`, but correctly returned `stale_source` because the working-tree change is not canonical LIVE state. Its call-context query also failed closed as stale. No incremental LIVE/MCP publication was performed because it is outside scope. Current source, compilation, and focused tests establish the implementation; Contextor stale state does not assert a parallel lifecycle.

## IMPLEMENTATION

Added `materialized_lineage_source_matches_resolution(materialized, resolution)` immediately before the materializer. It fails closed unless the manifest has current semantic version, fresh status, and all materialization capabilities. It reconstructs expected semantic anchors/descriptors under current active identity mappings, re-resolves symbolic/semantic endpoints using compact origins, and returns true only for exact equality.

Added the requested owned-flow fixture and four tests: unchanged resolution; changed owner identity; symbolic endpoint that becomes resolvable; and semantic endpoint without origin.

## VALIDATION

- `.\\.venv\\Scripts\\python.exe -m py_compile contextor\\core\\analysis\\lineage_materialization.py tests\\analysis\\test_lineage_materialization.py` — passed.
- `.\\.venv\\Scripts\\python.exe -m pytest -q tests\\analysis\\test_lineage_materialization.py` — **31 passed in 3.02s**.
- Source/test `git diff --check` passed before embedding the required raw unified
  diffs. The literal diff block below retains unified-diff context blank-space
  lines, so repository-wide `git diff --check` flags only those report lines.

## FILES_CHANGED

- `contextor/core/analysis/lineage_materialization.py`
- `tests/analysis/test_lineage_materialization.py`

## FULL_DIFFS

```diff
warning: in the working copy of 'contextor/core/analysis/lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/analysis/test_lineage_materialization.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
index 96ce8c3..57bfa19 100644
--- a/contextor/core/analysis/lineage_materialization.py
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -357,6 +357,174 @@ def _seed_defining_interface_descriptors(
             descriptors[binding.owner_id] = descriptor
 
 
+def materialized_lineage_source_matches_resolution(
+    materialized: MaterializedLineageSourceFacts,
+    resolution: LineageResolutionContext,
+) -> bool:
+    """Return True only when one canonical slice still matches current resolution."""
+    if not isinstance(materialized, MaterializedLineageSourceFacts):
+        raise TypeError("materialized must be MaterializedLineageSourceFacts.")
+    if not isinstance(resolution, LineageResolutionContext):
+        raise TypeError("resolution must be LineageResolutionContext.")
+
+    manifest = materialized.manifest
+    if (
+        manifest.semantic_version != LINEAGE_FACTS_SEMANTIC_VERSION
+        or manifest.status is not LineageFamilyStatus.FRESH
+        or not manifest.semantic_anchor_bindings_materialized
+        or not manifest.anchor_ownership_materialized
+        or not manifest.flow_ownership_materialized
+        or not manifest.interface_descriptors_materialized
+    ):
+        return False
+
+    extracted_anchors = tuple(
+        ExtractedAnchorFact(
+            anchor.local_id,
+            anchor.kind,
+            anchor.span,
+            anchor.owner_local_id,
+        )
+        for anchor in materialized.anchors
+    )
+    anchors_by_id = {
+        anchor.local_id: anchor
+        for anchor in extracted_anchors
+    }
+    references_by_id = {
+        anchor.local_id: anchor.reference
+        for anchor in materialized.anchors
+    }
+    module_name = _module_name_from_source_key(manifest.source_key)
+
+    expected_semantic_anchors: list[SemanticAnchorBinding] = []
+    for anchor in extracted_anchors:
+        if anchor.kind not in {
+            "class",
+            "function",
+            "async_function",
+            "binding",
+            "import_binding",
+        }:
+            continue
+
+        symbol_path = _anchor_symbol_path(anchor, anchors_by_id)
+        if symbol_path is None:
+            continue
+
+        qualified_name = f"{module_name}::{symbol_path}"
+        owner_id = resolution.active_artifact_ids.get(qualified_name)
+        if owner_id is None:
+            continue
+
+        reference = references_by_id.get(anchor.local_id)
+        if reference is None:
+            return False
+
+        expected_semantic_anchors.append(
+            SemanticAnchorBinding(
+                owner_id,
+                qualified_name,
+                reference,
+            )
+        )
+
+    expected_semantic_anchors_tuple = tuple(sorted(expected_semantic_anchors))
+    if expected_semantic_anchors_tuple != materialized.semantic_anchors:
+        return False
+
+    expected_descriptors: dict[str, SemanticInterfaceDescriptor] = {}
+    _seed_defining_interface_descriptors(
+        expected_descriptors,
+        expected_semantic_anchors_tuple,
+        resolution,
+    )
+
+    origins = {
+        (origin.fact_local_id, origin.endpoint_role): origin
+        for origin in materialized.semantic_endpoint_origins
+    }
+
+    def endpoint_matches(
+        current: MaterializedOccurrenceRef
+        | MaterializedSymbolicRef
+        | SemanticEndpoint,
+        resolution_kind: ResolutionKind,
+        confidence: LineageConfidence,
+        fact_local_id: str,
+        endpoint_role: SemanticEndpointRole,
+    ) -> bool:
+        if isinstance(current, MaterializedOccurrenceRef):
+            return True
+
+        if isinstance(current, MaterializedSymbolicRef):
+            reference = ExtractedSymbolicRef(
+                current.kind,
+                current.module_name,
+                current.symbol_name,
+                current.source_local_id,
+            )
+            source_key = current.source_key
+            source_fingerprint = current.source_fingerprint
+        elif isinstance(current, SemanticEndpoint):
+            origin = origins.get((fact_local_id, endpoint_role))
+            if origin is None:
+                return False
+            reference = ExtractedSymbolicRef(
+                origin.kind,
+                origin.module_name,
+                origin.symbol_name,
+                origin.source_local_id,
+            )
+            source_key = origin.source_key
+            source_fingerprint = origin.source_fingerprint
+        else:
+            return False
+
+        expected = _symbolic_endpoint(
+            reference,
+            resolution,
+            expected_descriptors,
+            resolution_kind,
+            confidence,
+            source_key,
+            source_fingerprint,
+        )
+        return expected == current
+
+    for flow in materialized.flows:
+        if not endpoint_matches(
+            flow.source,
+            flow.resolution_kind,
+            flow.confidence,
+            flow.local_id,
+            SemanticEndpointRole.FLOW_SOURCE,
+        ):
+            return False
+        if not endpoint_matches(
+            flow.target,
+            flow.resolution_kind,
+            flow.confidence,
+            flow.local_id,
+            SemanticEndpointRole.FLOW_TARGET,
+        ):
+            return False
+
+    for surface in materialized.surfaces:
+        if not endpoint_matches(
+            surface.exposed,
+            surface.resolution_kind,
+            surface.confidence,
+            surface.local_id,
+            SemanticEndpointRole.SURFACE_EXPOSED,
+        ):
+            return False
+
+    return (
+        tuple(sorted(expected_descriptors.values()))
+        == materialized.interface_descriptors
+    )
+
 def materialize_lineage_source_facts(
     extracted: ExtractedLineageSourceFacts,
     resolution: LineageResolutionContext,
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
index e1e67ba..1553677 100644
--- a/tests/analysis/test_lineage_materialization.py
+++ b/tests/analysis/test_lineage_materialization.py
@@ -13,6 +13,7 @@ from contextor.core.analysis.lineage_materialization import (
     LineageResolutionContext,
     build_extracted_callable_interface_descriptors,
     build_materialized_callable_interface_descriptors,
+    materialized_lineage_source_matches_resolution,
     materialize_lineage_source_facts,
     reresolve_materialized_lineage_source_facts,
 )
@@ -804,3 +805,108 @@ def test_interface_descriptor_capability_requires_anchor_capabilities():
         replace(manifest, interface_descriptors_materialized=True)
     with pytest.raises(TypeError, match="interface_descriptors_materialized must be boolean"):
         replace(manifest, interface_descriptors_materialized="yes")
+
+def _owned_exact_target_facts():
+    span = SourceSpan(1, 0, 1, 1)
+    return _facts(
+        anchors=(
+            ExtractedAnchorFact(
+                "owner",
+                "binding",
+                span,
+            ),
+        ),
+        flows=(
+            ExtractedFlowFact(
+                "flow",
+                ExtractedOccurrenceRef("owner"),
+                ExtractedSymbolicRef(
+                    ExtractedSymbolicKind.PUBLIC_TARGET,
+                    "pkg.mod",
+                    "target",
+                ),
+                LineageRelation.EXPOSES,
+                span,
+                ResolutionKind.IMPORT_EXACT,
+                LineageConfidence.CONFIRMED,
+                owner_local_id="owner",
+            ),
+        ),
+    )
+
+
+def test_materialized_lineage_source_matches_unchanged_resolution():
+    facts = _owned_exact_target_facts()
+    context = _context(
+        artifacts={"pkg.mod::target": "A1/1"},
+    )
+    materialized = materialize_lineage_source_facts(
+        facts,
+        context,
+    )
+
+    assert materialized.manifest.flow_ownership_materialized is True
+    assert materialized_lineage_source_matches_resolution(
+        materialized,
+        context,
+    ) is True
+
+
+def test_materialized_lineage_source_rejects_changed_resolution():
+    facts = _owned_exact_target_facts()
+    materialized = materialize_lineage_source_facts(
+        facts,
+        _context(
+            artifacts={"pkg.mod::target": "A1/1"},
+        ),
+    )
+
+    assert materialized.manifest.flow_ownership_materialized is True
+    assert materialized_lineage_source_matches_resolution(
+        materialized,
+        _context(
+            artifacts={"pkg.mod::target": "A1/2"},
+        ),
+    ) is False
+
+
+def test_materialized_lineage_source_rejects_symbolic_endpoint_that_now_resolves():
+    facts = _owned_exact_target_facts()
+    materialized = materialize_lineage_source_facts(
+        facts,
+        _context(),
+    )
+
+    assert materialized.manifest.flow_ownership_materialized is True
+    assert isinstance(
+        materialized.flows[0].target,
+        MaterializedSymbolicRef,
+    )
+    assert materialized_lineage_source_matches_resolution(
+        materialized,
+        _context(
+            artifacts={"pkg.mod::target": "A1/1"},
+        ),
+    ) is False
+
+
+def test_materialized_lineage_source_rejects_semantic_endpoint_without_origin():
+    facts = _owned_exact_target_facts()
+    context = _context(
+        artifacts={"pkg.mod::target": "A1/1"},
+    )
+    materialized = materialize_lineage_source_facts(
+        facts,
+        context,
+    )
+    assert materialized.manifest.flow_ownership_materialized is True
+
+    legacy_like = replace(
+        materialized,
+        semantic_endpoint_origins=(),
+    )
+
+    assert materialized_lineage_source_matches_resolution(
+        legacy_like,
+        context,
+    ) is False
```
