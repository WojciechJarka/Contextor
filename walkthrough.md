# Stage 1F.1 deterministic lineage materializer

STATUS=PASS
BASE=9dc96eadccc334f6284b700b7f88dadeb3ba3ed6
HEAD=9dc96eadccc334f6284b700b7f88dadeb3ba3ed6

MCP_POOL_DISCOVERY
ACTIVE: contextor_fact_lineage, get_file_edit_context, search_source, lookup_index_entries and get_live_events are callable.
DEFERRED: complete exposed deferred/callable inventory inspected; contextor_lineage unavailable.
LINEAGE_TOOL_USED=contextor_fact_lineage, substitution for unavailable contextor_lineage. Its documented contract confirms active IDs only, no allocation and recovery IDs never active. New module has one covering test; watcher revision 648 is continuous with resync_required=false.

MATERIALIZER_API
contextor.core.analysis.lineage_materialization.materialize_lineage_source_facts(extracted, resolution)
LineageResolutionContext(active_module_ids, active_artifact_ids, active_owner_ids, interface_descriptors)
Internal-only; no public API/export/state installation added.

RESOLUTION_MATRIX
Occurrence -> MaterializedOccurrenceRef(source key/fingerprint/local id).
DEFINITION/CALLEE/IMPORT/PUBLIC_TARGET -> exact active artifact endpoint, otherwise deterministic unresolved source-local placeholder.
PARAMETER -> active callable plus descriptor-proven parameter-value slot; malformed ID errors; absent/ambiguous slot placeholder.
RETURN -> active callable plus descriptor-proven return slot; absent slot placeholder.
STATE -> active module plus descriptor-proven module-global slot; absent slot placeholder.
Original resolution kind/confidence/boundary/provider/declaration evidence are preserved. No target is guessed. Context rejects non-active mapping values, preventing recovery/orphan endpoint use.

NO_SIDE_EFFECT_PROOF
No AST/source/filesystem/registry/state/graph/snapshot/MCP imports or mutation/allocation. Context mappings are copied to MappingProxyType. Test uses hostile builtins.open and checks input mapping unchanged.

TESTS
py_compile: PASS
pytest -q tests/analysis/test_lineage_materialization.py tests/domain/test_lineage_facts.py: 58 passed in 1.22s
git diff --check: PASS
FIX_REQUIRED=NO

FILES_CHANGED
- contextor/core/analysis/lineage_materialization.py
- tests/analysis/test_lineage_materialization.py

FULL_DIFF
diff --git a/contextor/core/analysis/lineage_materialization.py b/contextor/core/analysis/lineage_materialization.py
new file mode 100644
index 0000000..8cf06c6
--- /dev/null
+++ b/contextor/core/analysis/lineage_materialization.py
@@ -0,0 +1,208 @@
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
+    MaterializedAnchorFact,
+    MaterializedFlowFact,
+    MaterializedLineageSourceFacts,
+    MaterializedOccurrenceRef,
+    MaterializedSurfaceFact,
+    ParameterKind,
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
+    ) -> MaterializedOccurrenceRef | SemanticEndpoint:
+        if isinstance(reference, ExtractedOccurrenceRef):
+            return occurrence(reference.local_id)
+        return _symbolic_endpoint(reference, resolution, occurrence, descriptors)
+
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
+                endpoint(flow.source),
+                endpoint(flow.target),
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
+                endpoint(surface.exposed),
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
+    occurrence,
+    descriptors: dict[str, SemanticInterfaceDescriptor],
+) -> MaterializedOccurrenceRef | SemanticEndpoint:
+    owner_id = (
+        resolution.active_module_ids.get(reference.module_name)
+        if reference.kind is ExtractedSymbolicKind.STATE
+        else resolution.active_artifact_ids.get(reference.qualified_name)
+    )
+    if owner_id is None:
+        return occurrence(_unresolved_local_id(reference))
+
+    slot = _slot_for(reference, owner_id)
+    if slot is not None:
+        descriptor = resolution.interface_descriptors.get(owner_id)
+        if descriptor is None or slot not in descriptor.slots:
+            return occurrence(_unresolved_local_id(reference))
+        descriptors[owner_id] = descriptor
+    return SemanticEndpoint(owner_id, slot)
+
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
+
+
+def _unresolved_local_id(reference: ExtractedSymbolicRef) -> str:
+    return "unresolved:v1:{kind}:m:{module}:s:{symbol}:l:{local}".format(
+        kind=reference.kind.value,
+        module=quote(reference.module_name, safe=""),
+        symbol=quote(reference.symbol_name, safe=""),
+        local=quote(reference.source_local_id or "", safe=""),
+    )
diff --git a/tests/analysis/test_lineage_materialization.py b/tests/analysis/test_lineage_materialization.py
new file mode 100644
index 0000000..69d65ce
--- /dev/null
+++ b/tests/analysis/test_lineage_materialization.py
@@ -0,0 +1,211 @@
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
+    assert isinstance(result.flows[0].target, MaterializedOccurrenceRef)
+    assert result.flows[0].target.local_id.startswith("unresolved:v1:public_target")
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
+    assert isinstance(result.flows[0].target, MaterializedOccurrenceRef)
+    assert result.flows[0].target.local_id.startswith("unresolved:v1:state")
