# Stage 1F.1 corrective

STATUS=PASS
MCP_POOL_DISCOVERY: ACTIVE contextor_fact_lineage used; DEFERRED inventory inspected, contextor_lineage unavailable.
LINEAGE_TOOL_USED=contextor_fact_lineage
CORRECTED_REFERENCE_UNION=MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint.
EXACTNESS_GATE=SemanticEndpoint requires confirmed exact extraction kind (LEXICAL_EXACT, IMPORT_EXACT, CALL_EXACT, SIGNATURE_EXACT, STATIC_MRO_EXACT, LITERAL_CONTAINER_EXACT, RECEPTOR_PROVIDED) plus exact active identity and, where needed, descriptor-proven slot. All non-exact evidence remains MaterializedSymbolicRef despite same-named active identity.
NO_SYNTHETIC_UNRESOLVED_OCCURRENCE=PASS; _unresolved_local_id and urllib.quote removed.
TESTS=py_compile PASS; pytest focused 64 passed in 1.20s; git diff --check PASS.
FILES_CHANGED=contextor/core/domain/lineage_facts.py; contextor/core/analysis/lineage_materialization.py; tests/domain/test_lineage_facts.py; tests/analysis/test_lineage_materialization.py
FULL_DIFF
\ndiff --git a/contextor/core/domain/lineage_facts.py b/contextor/core/domain/lineage_facts.py
index 629b284..e69256a 100644
--- a/contextor/core/domain/lineage_facts.py
+++ b/contextor/core/domain/lineage_facts.py
@@ -197,6 +197,26 @@ class MaterializedOccurrenceRef:
         _require_token(self.local_id, "local_id")
 
 
+@dataclass(frozen=True, order=True)
+class MaterializedSymbolicRef:
+    """Canonical-slice symbolic boundary, never an occurrence or owner."""
+
+    source_key: str
+    source_fingerprint: str
+    kind: ExtractedSymbolicKind
+    module_name: str
+    symbol_name: str
+    source_local_id: str | None = None
+
+    def __post_init__(self) -> None:
+        _require_token(self.source_key, "source_key")
+        _require_token(self.source_fingerprint, "source_fingerprint")
+        _require_token(self.module_name, "module_name")
+        _require_token(self.symbol_name, "symbol_name")
+        if self.source_local_id is not None:
+            _require_token(self.source_local_id, "source_local_id")
+
+
 @dataclass(frozen=True, order=True)
 class ExtractedAnchorFact:
     local_id: str
@@ -280,7 +300,7 @@ class ExtractedLineageSourceFacts:
 @dataclass(frozen=True, order=True)
 class MaterializedAnchorFact:
     local_id: str
-    reference: MaterializedOccurrenceRef | SemanticEndpoint
+    reference: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint
     kind: str
     span: SourceSpan
 
@@ -293,8 +313,8 @@ class MaterializedAnchorFact:
 @dataclass(frozen=True, order=True)
 class MaterializedFlowFact:
     local_id: str
-    source: MaterializedOccurrenceRef | SemanticEndpoint
-    target: MaterializedOccurrenceRef | SemanticEndpoint
+    source: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint
+    target: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint
     relation: LineageRelation
     evidence: SourceSpan
     resolution_kind: ResolutionKind
@@ -318,7 +338,7 @@ class MaterializedFlowFact:
 class MaterializedSurfaceFact:
     local_id: str
     kind: SurfaceKind
-    exposed: MaterializedOccurrenceRef | SemanticEndpoint
+    exposed: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint
     evidence: SourceSpan
     resolution_kind: ResolutionKind
     confidence: LineageConfidence
@@ -649,7 +669,7 @@ def _claims_exact_semantic_target(
 
 
 def _validate_materialized_surface_target(
-    exposed: MaterializedOccurrenceRef | SemanticEndpoint,
+    exposed: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint,
     resolution_kind: ResolutionKind,
     confidence: LineageConfidence,
 ) -> None:
@@ -674,18 +694,18 @@ def _require_sorted_unique(values: tuple[object, ...], label: str) -> None:
 
 
 def _require_materialized_reference(
-    value: MaterializedOccurrenceRef | SemanticEndpoint,
+    value: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint,
     label: str,
 ) -> None:
-    if not isinstance(value, (MaterializedOccurrenceRef, SemanticEndpoint)):
+    if not isinstance(value, (MaterializedOccurrenceRef, MaterializedSymbolicRef, SemanticEndpoint)):
         raise TypeError(f"{label} require canonical occurrence or semantic endpoint references.")
 
 
 def _require_slice_occurrence(
-    value: MaterializedOccurrenceRef | SemanticEndpoint,
+    value: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint,
     manifest: SourceLineageManifest,
 ) -> None:
-    if isinstance(value, MaterializedOccurrenceRef) and (
+    if isinstance(value, (MaterializedOccurrenceRef, MaterializedSymbolicRef)) and (
         value.source_key != manifest.source_key
         or value.source_fingerprint != manifest.source_fingerprint
     ):
@@ -711,6 +731,7 @@ __all__ = [
     "MaterializedFlowFact",
     "MaterializedLineageSourceFacts",
     "MaterializedOccurrenceRef",
+    "MaterializedSymbolicRef",
     "MaterializedSurfaceFact",
     "ParameterKind",
     "ResolutionKind",
diff --git a/tests/domain/test_lineage_facts.py b/tests/domain/test_lineage_facts.py
index 72d6536..cc368e5 100644
--- a/tests/domain/test_lineage_facts.py
+++ b/tests/domain/test_lineage_facts.py
@@ -21,6 +21,7 @@ from contextor.core.domain.lineage_facts import (
     MaterializedAnchorFact,
     MaterializedLineageSourceFacts,
     MaterializedOccurrenceRef,
+    MaterializedSymbolicRef,
     MaterializedSurfaceFact,
     ParameterKind,
     ResolutionKind,
@@ -453,3 +454,37 @@ def test_surface_declaration_evidence_rejects_invalid_type_and_preserves_convent
 
 def test_lineage_facts_semantic_version_remains_initial_version():
     assert LINEAGE_FACTS_SEMANTIC_VERSION == "1"
+
+
+def test_materialized_symbolic_ref_is_slice_bound_and_never_an_occurrence():
+    span = SourceSpan(1, 0, 1, 1)
+    manifest = SourceLineageManifest(
+        "a.py", "fingerprint", "1", LineageFamilyStatus.FRESH, 0, 1, 0
+    )
+    symbolic = MaterializedSymbolicRef(
+        "a.py", "fingerprint", ExtractedSymbolicKind.PUBLIC_TARGET,
+        "pkg.mod", "missing",
+    )
+    slice_ = MaterializedLineageSourceFacts(
+        manifest, (), (
+            MaterializedFlowFact(
+                "flow", MaterializedOccurrenceRef("a.py", "fingerprint", "x"),
+                symbolic, LineageRelation.EXPOSES, span,
+                ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED,
+            ),
+        ), (),
+    )
+    assert slice_.flows[0].target == symbolic
+    foreign = MaterializedSymbolicRef(
+        "b.py", "other", ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "missing"
+    )
+    with pytest.raises(ValueError, match="foreign occurrence"):
+        MaterializedLineageSourceFacts(
+            manifest, (), (
+                MaterializedFlowFact(
+                    "bad", MaterializedOccurrenceRef("a.py", "fingerprint", "x"),
+                    foreign, LineageRelation.EXPOSES, span,
+                    ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED,
+                ),
+            ), (),
+        )
\ No newline at end of file
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
new file mode 100644
index 0000000..62ce81f
--- /dev/null
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -0,0 +1,222 @@
+"""Pure deterministic materialization of one lineage source slice."""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from types import MappingProxyType
+from typing import Mapping
+from urllib.parse import quote
+
+from contextor.core.analysis.lineage_extraction_contracts import (
+    parse_local_occurrence_id,
+)
+from contextor.core.domain.lineage_facts import (
+    LINEAGE_FACTS_SEMANTIC_VERSION,
+    ExtractedLineageSourceFacts,
+    ExtractedOccurrenceRef,
+    ExtractedSymbolicKind,
+    ExtractedSymbolicRef,
+    LineageConfidence,
+    MaterializedAnchorFact,
+    MaterializedFlowFact,
+    MaterializedLineageSourceFacts,
+    MaterializedOccurrenceRef,
+    MaterializedSymbolicRef,
+    MaterializedSurfaceFact,
+    ParameterKind,
+    ResolutionKind,
+    SemanticEndpoint,
+    SemanticInterfaceDescriptor,
+    SourceLineageManifest,
+    build_module_global_slot,
+    build_parameter_value_slot,
+    build_return_slot,
+)
+
+
+@dataclass(frozen=True)
+class LineageResolutionContext:
+    """Narrow read-only evidence of currently active canonical identities."""
+
+    active_module_ids: Mapping[str, str]
+    active_artifact_ids: Mapping[str, str]
+    active_owner_ids: frozenset[str]
+    interface_descriptors: Mapping[str, SemanticInterfaceDescriptor]
+
+    def __post_init__(self) -> None:
+        object.__setattr__(
+            self, "active_module_ids", MappingProxyType(dict(self.active_module_ids))
+        )
+        object.__setattr__(
+            self, "active_artifact_ids", MappingProxyType(dict(self.active_artifact_ids))
+        )
+        object.__setattr__(
+            self,
+            "interface_descriptors",
+            MappingProxyType(dict(self.interface_descriptors)),
+        )
+        for owner_id in (
+            *self.active_module_ids.values(),
+            *self.active_artifact_ids.values(),
+        ):
+            if owner_id not in self.active_owner_ids:
+                raise ValueError(
+                    "Resolution mappings must contain only active owner ids."
+                )
+        for owner_id, descriptor in self.interface_descriptors.items():
+            if owner_id != descriptor.owner_id or owner_id not in self.active_owner_ids:
+                raise ValueError(
+                    "Interface descriptors must belong to active owners."
+                )
+
+
+def materialize_lineage_source_facts(
+    extracted: ExtractedLineageSourceFacts,
+    resolution: LineageResolutionContext,
+) -> MaterializedLineageSourceFacts:
+    """Convert one extracted slice without I/O, allocation, or mutation."""
+
+    if not isinstance(extracted, ExtractedLineageSourceFacts):
+        raise TypeError("extracted must be ExtractedLineageSourceFacts.")
+    if not isinstance(resolution, LineageResolutionContext):
+        raise TypeError("resolution must be LineageResolutionContext.")
+
+    def occurrence(local_id: str) -> MaterializedOccurrenceRef:
+        return MaterializedOccurrenceRef(
+            extracted.source_key, extracted.source_fingerprint, local_id
+        )
+
+    descriptors: dict[str, SemanticInterfaceDescriptor] = {}
+
+    def endpoint(
+        reference: ExtractedOccurrenceRef | ExtractedSymbolicRef,
+        kind: ResolutionKind,
+        confidence: LineageConfidence,
+    ) -> MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint:
+        if isinstance(reference, ExtractedOccurrenceRef):
+            return occurrence(reference.local_id)
+        return _symbolic_endpoint(
+            reference, resolution, descriptors, kind, confidence, extracted
+        )
+    anchors = tuple(
+        sorted(
+            MaterializedAnchorFact(
+                anchor.local_id, occurrence(anchor.local_id), anchor.kind, anchor.span
+            )
+            for anchor in extracted.anchors
+        )
+    )
+    flows = tuple(
+        sorted(
+            MaterializedFlowFact(
+                flow.local_id,
+                endpoint(flow.source, flow.resolution_kind, flow.confidence),
+                endpoint(flow.target, flow.resolution_kind, flow.confidence),
+                flow.relation,
+                flow.evidence,
+                flow.resolution_kind,
+                flow.confidence,
+                flow.dynamic_boundary,
+                flow.provider,
+            )
+            for flow in extracted.flows
+        )
+    )
+    surfaces = tuple(
+        sorted(
+            MaterializedSurfaceFact(
+                surface.local_id,
+                surface.kind,
+                endpoint(surface.exposed, surface.resolution_kind, surface.confidence),
+                surface.evidence,
+                surface.resolution_kind,
+                surface.confidence,
+                surface.declared_name,
+                surface.dynamic_boundary,
+                surface.provider,
+                surface.declaration_evidence,
+            )
+            for surface in extracted.surfaces
+        )
+    )
+    manifest = SourceLineageManifest(
+        extracted.source_key,
+        extracted.source_fingerprint,
+        LINEAGE_FACTS_SEMANTIC_VERSION,
+        extracted.status,
+        len(anchors),
+        len(flows),
+        len(surfaces),
+        extracted.resource_limit_reason,
+    )
+    return MaterializedLineageSourceFacts(
+        manifest, anchors, flows, surfaces, tuple(sorted(descriptors.values()))
+    )
+
+
+def _symbolic_endpoint(
+    reference: ExtractedSymbolicRef,
+    resolution: LineageResolutionContext,
+    descriptors: dict[str, SemanticInterfaceDescriptor],
+    resolution_kind: ResolutionKind,
+    confidence: LineageConfidence,
+    extracted: ExtractedLineageSourceFacts,
+) -> MaterializedSymbolicRef | SemanticEndpoint:
+    symbolic = MaterializedSymbolicRef(
+        extracted.source_key, extracted.source_fingerprint, reference.kind,
+        reference.module_name, reference.symbol_name, reference.source_local_id,
+    )
+    if not _claims_exact_semantic_target(resolution_kind, confidence):
+        return symbolic
+    owner_id = (
+        resolution.active_module_ids.get(reference.module_name)
+        if reference.kind is ExtractedSymbolicKind.STATE
+        else resolution.active_artifact_ids.get(reference.qualified_name)
+    )
+    if owner_id is None:
+        return symbolic
+    slot = _slot_for(reference, owner_id)
+    if slot is not None:
+        descriptor = resolution.interface_descriptors.get(owner_id)
+        if descriptor is None or slot not in descriptor.slots:
+            return symbolic
+        descriptors[owner_id] = descriptor
+    return SemanticEndpoint(owner_id, slot)
+
+
+def _claims_exact_semantic_target(
+    resolution_kind: ResolutionKind, confidence: LineageConfidence,
+) -> bool:
+    return confidence is LineageConfidence.CONFIRMED and resolution_kind in {
+        ResolutionKind.LEXICAL_EXACT, ResolutionKind.IMPORT_EXACT,
+        ResolutionKind.CALL_EXACT, ResolutionKind.SIGNATURE_EXACT,
+        ResolutionKind.STATIC_MRO_EXACT, ResolutionKind.LITERAL_CONTAINER_EXACT,
+        ResolutionKind.RECEPTOR_PROVIDED,
+    }
+
+def _slot_for(reference: ExtractedSymbolicRef, owner_id: str) -> str | None:
+    if reference.kind is ExtractedSymbolicKind.RETURN:
+        return build_return_slot(owner_id)
+    if reference.kind is ExtractedSymbolicKind.STATE:
+        return build_module_global_slot(owner_id, reference.symbol_name)
+    if reference.kind is not ExtractedSymbolicKind.PARAMETER:
+        return None
+    if reference.source_local_id is None:
+        raise ValueError("Parameter symbolic reference requires source_local_id.")
+    local_kind, _path, ordinal, name = parse_local_occurrence_id(
+        reference.source_local_id
+    )
+    parameter_kinds = {
+        "parameter_posonly": ParameterKind.POSITIONAL_ONLY,
+        "parameter_poskw": ParameterKind.POSITIONAL_OR_KEYWORD,
+        "parameter_vararg": ParameterKind.VAR_POSITIONAL,
+        "parameter_kwonly": ParameterKind.KEYWORD_ONLY,
+        "parameter_varkw": ParameterKind.VAR_KEYWORD,
+    }
+    try:
+        kind = parameter_kinds[local_kind]
+    except KeyError as exc:
+        raise ValueError(
+            "Parameter symbolic reference must point at a parameter local id."
+        ) from exc
+    return build_parameter_value_slot(owner_id, kind, ordinal=ordinal, name=name)
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
new file mode 100644
index 0000000..6a47961
--- /dev/null
+++ b/tests/analysis/test_lineage_materialization.py
@@ -0,0 +1,257 @@
+from __future__ import annotations
+
+import builtins
+
+import pytest
+
+from contextor.core.analysis.lineage_materialization import (
+    LineageResolutionContext,
+    materialize_lineage_source_facts,
+)
+from contextor.core.domain.lineage_facts import (
+    ExtractedAnchorFact,
+    ExtractedFlowFact,
+    ExtractedLineageSourceFacts,
+    ExtractedOccurrenceRef,
+    ExtractedSymbolicKind,
+    ExtractedSymbolicRef,
+    ExtractedSurfaceFact,
+    LineageConfidence,
+    LineageRelation,
+    MaterializedOccurrenceRef,
+    MaterializedSymbolicRef,
+    ParameterKind,
+    ProviderRef,
+    ResolutionKind,
+    SemanticEndpoint,
+    SemanticInterfaceDescriptor,
+    SourceSpan,
+    SurfaceDeclarationEvidence,
+    SurfaceKind,
+    build_parameter_value_slot,
+    build_return_slot,
+)
+
+
+def _context(*, artifacts=None, modules=None, active=None, descriptors=None):
+    artifacts = artifacts or {}
+    modules = modules or {}
+    if active is None:
+        active = frozenset((*artifacts.values(), *modules.values()))
+    return LineageResolutionContext(modules, artifacts, frozenset(active), descriptors or {})
+
+
+def _facts(*, anchors=(), flows=(), surfaces=()):
+    return ExtractedLineageSourceFacts(
+        "pkg/mod.py", "sha256:test", anchors, flows, surfaces
+    )
+
+
+def test_materializer_is_deterministic_and_preserves_local_anchors_and_flows():
+    span = SourceSpan(1, 0, 1, 1)
+    facts = _facts(
+        anchors=(ExtractedAnchorFact("anchor", "binding", span),),
+        flows=(
+            ExtractedFlowFact(
+                "flow", ExtractedOccurrenceRef("anchor"), ExtractedOccurrenceRef("use"),
+                LineageRelation.ASSIGNS, span, ResolutionKind.LEXICAL_EXACT,
+                LineageConfidence.CONFIRMED,
+            ),
+        ),
+    )
+    first = materialize_lineage_source_facts(facts, _context())
+    assert first == materialize_lineage_source_facts(facts, _context())
+    assert first.manifest.source_key == "pkg/mod.py"
+    assert first.manifest.source_fingerprint == "sha256:test"
+    assert first.anchors[0].reference == MaterializedOccurrenceRef(
+        "pkg/mod.py", "sha256:test", "anchor"
+    )
+    assert first.flows[0].resolution_kind is ResolutionKind.LEXICAL_EXACT
+
+
+def test_exact_active_return_parameter_and_descriptor_slots_are_materialized():
+    span = SourceSpan(1, 0, 1, 1)
+    owner = "A1/1"
+    parameter_id = "occ:v1:parameter_poskw:0:i:0:n:value"
+    parameter = ExtractedSymbolicRef(
+        ExtractedSymbolicKind.PARAMETER, "pkg.mod", "run", parameter_id
+    )
+    returned = ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, "pkg.mod", "run")
+    slots = tuple(sorted((
+        build_parameter_value_slot(
+            owner, ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=0
+        ),
+        build_return_slot(owner),
+    )))
+    descriptor = SemanticInterfaceDescriptor(owner, slots, "digest")
+    facts = _facts(flows=(
+        ExtractedFlowFact(
+            "a", ExtractedOccurrenceRef("x"), parameter,
+            LineageRelation.ARGUMENT_TO_PARAMETER, span,
+            ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED,
+        ),
+        ExtractedFlowFact(
+            "b", returned, ExtractedOccurrenceRef("x"), LineageRelation.RETURNS,
+            span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED,
+        ),
+    ))
+    result = materialize_lineage_source_facts(
+        facts, _context(artifacts={"pkg.mod::run": owner}, descriptors={owner: descriptor})
+    )
+    assert isinstance(result.flows[0].target, SemanticEndpoint)
+    assert result.interface_descriptors == (descriptor,)
+
+
+def test_missing_or_ambiguous_slot_stays_explicit_and_dynamic_surface_is_preserved(monkeypatch):
+    span = SourceSpan(1, 0, 1, 1)
+    missing = ExtractedSymbolicRef(
+        ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "missing"
+    )
+    facts = _facts(
+        flows=(
+            ExtractedFlowFact(
+                "flow", ExtractedOccurrenceRef("x"), missing, LineageRelation.EXPOSES,
+                span, ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED,
+            ),
+        ),
+        surfaces=(
+            ExtractedSurfaceFact(
+                "surface", SurfaceKind.REGISTRATION, missing, span,
+                ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC,
+                "missing", "runtime", ProviderRef("fixture", "1"),
+                SurfaceDeclarationEvidence.STATIC_DECLARATION,
+            ),
+        ),
+    )
+    monkeypatch.setattr(
+        builtins, "open",
+        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("I/O")),
+    )
+    result = materialize_lineage_source_facts(facts, _context())
+    assert isinstance(result.flows[0].target, MaterializedSymbolicRef)
+    assert result.flows[0].target.kind is ExtractedSymbolicKind.PUBLIC_TARGET
+    assert result.surfaces[0].dynamic_boundary == "runtime"
+    assert result.surfaces[0].provider == ProviderRef("fixture", "1")
+
+
+def test_active_mapping_cannot_contain_recovery_and_bad_parameter_is_rejected():
+    with pytest.raises(ValueError, match="active owner"):
+        _context(artifacts={"pkg.mod::run": "A1/1"}, active=())
+    span = SourceSpan(1, 0, 1, 1)
+    bad = ExtractedSymbolicRef(
+        ExtractedSymbolicKind.PARAMETER, "pkg.mod", "run",
+        "binding:v1:p:i:0:n:value",
+    )
+    facts = _facts(flows=(
+        ExtractedFlowFact(
+            "flow", ExtractedOccurrenceRef("x"), bad, LineageRelation.BINDS,
+            span, ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED,
+        ),
+    ))
+    with pytest.raises(ValueError, match="Invalid local occurrence id"):
+        materialize_lineage_source_facts(
+            facts, _context(artifacts={"pkg.mod::run": "A1/1"})
+        )
+
+
+def test_materializer_does_not_mutate_input_mappings():
+    artifacts = {"pkg.mod::run": "A1/1"}
+    context = _context(artifacts=artifacts)
+    materialize_lineage_source_facts(_facts(), context)
+    assert artifacts == {"pkg.mod::run": "A1/1"}
+
+
+
+def test_active_symbol_and_state_resolve_only_with_exact_existing_slot():
+    span = SourceSpan(1, 0, 1, 1)
+    artifact_owner, module_owner = "A2/1", "2/1"
+    state_slot = __import__(
+        "contextor.core.domain.lineage_facts", fromlist=["build_module_global_slot"]
+    ).build_module_global_slot(module_owner, "setting")
+    state_descriptor = SemanticInterfaceDescriptor(module_owner, (state_slot,), "state")
+    definition = ExtractedSymbolicRef(
+        ExtractedSymbolicKind.DEFINITION, "pkg.mod", "thing"
+    )
+    state = ExtractedSymbolicRef(ExtractedSymbolicKind.STATE, "pkg.mod", "setting")
+    facts = _facts(flows=(
+        ExtractedFlowFact(
+            "a", ExtractedOccurrenceRef("x"), definition, LineageRelation.EXPOSES,
+            span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED,
+        ),
+        ExtractedFlowFact(
+            "b", ExtractedOccurrenceRef("x"), state, LineageRelation.READS_STATE,
+            span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED,
+        ),
+    ))
+    result = materialize_lineage_source_facts(
+        facts,
+        _context(
+            artifacts={"pkg.mod::thing": artifact_owner},
+            modules={"pkg.mod": module_owner},
+            descriptors={module_owner: state_descriptor},
+        ),
+    )
+    assert result.flows[0].target == SemanticEndpoint(artifact_owner)
+    assert result.flows[1].target == SemanticEndpoint(module_owner, state_slot)
+    assert result.interface_descriptors == (state_descriptor,)
+
+
+def test_missing_exact_slot_is_an_explicit_source_local_placeholder():
+    span = SourceSpan(1, 0, 1, 1)
+    state = ExtractedSymbolicRef(ExtractedSymbolicKind.STATE, "pkg.mod", "setting")
+    facts = _facts(flows=(
+        ExtractedFlowFact(
+            "flow", ExtractedOccurrenceRef("x"), state, LineageRelation.READS_STATE,
+            span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED,
+        ),
+    ))
+    result = materialize_lineage_source_facts(
+        facts, _context(modules={"pkg.mod": "2/1"})
+    )
+    assert isinstance(result.flows[0].target, MaterializedSymbolicRef)
+    assert result.flows[0].target.kind is ExtractedSymbolicKind.STATE
+
+
+@pytest.mark.parametrize(
+    ("kind", "resolution_kind", "confidence"),
+    [
+        (ExtractedSymbolicKind.PUBLIC_TARGET, ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED),
+        (ExtractedSymbolicKind.PUBLIC_TARGET, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC),
+        (ExtractedSymbolicKind.PUBLIC_TARGET, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED),
+        (ExtractedSymbolicKind.PUBLIC_TARGET, ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED),
+    ],
+)
+def test_non_exact_evidence_never_strengthens_from_same_named_active_identity(
+    kind, resolution_kind, confidence,
+):
+    span = SourceSpan(1, 0, 1, 1)
+    reference = ExtractedSymbolicRef(kind, "pkg.mod", "target")
+    kwargs = {"dynamic_boundary": "runtime"} if resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY else {}
+    facts = _facts(flows=(
+        ExtractedFlowFact(
+            "flow", ExtractedOccurrenceRef("x"), reference, LineageRelation.EXPOSES,
+            span, resolution_kind, confidence, **kwargs,
+        ),
+    ))
+    result = materialize_lineage_source_facts(
+        facts, _context(artifacts={"pkg.mod::target": "A9/1"})
+    )
+    target = result.flows[0].target
+    assert isinstance(target, MaterializedSymbolicRef)
+    assert (target.source_key, target.source_fingerprint) == ("pkg/mod.py", "sha256:test")
+    assert target.symbol_name == "target"
+
+
+def test_exact_surface_requires_endpoint_but_unresolved_surface_keeps_symbolic_boundary():
+    span = SourceSpan(1, 0, 1, 1)
+    reference = ExtractedSymbolicRef(ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "target")
+    unresolved = _facts(surfaces=(
+        ExtractedSurfaceFact(
+            "surface", SurfaceKind.EXPORT, reference, span, ResolutionKind.UNRESOLVED_NAME,
+            LineageConfidence.UNRESOLVED, "target",
+        ),
+    ))
+    result = materialize_lineage_source_facts(
+        unresolved, _context(artifacts={"pkg.mod::target": "A9/1"})
+    )
+    assert isinstance(result.surfaces[0].exposed, MaterializedSymbolicRef)
\ No newline at end of file
