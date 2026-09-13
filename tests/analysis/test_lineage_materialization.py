from __future__ import annotations

import builtins

import pytest

from contextor.core.analysis.lineage_materialization import (
    LineageResolutionContext,
    materialize_lineage_source_facts,
    reresolve_materialized_lineage_source_facts,
)
from contextor.core.domain.lineage_facts import (
    ExtractedAnchorFact,
    ExtractedFlowFact,
    ExtractedLineageSourceFacts,
    ExtractedOccurrenceRef,
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    ExtractedSurfaceFact,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    LINEAGE_FACTS_SEMANTIC_VERSION,
    MaterializedAnchorFact,
    MaterializedFlowFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    MaterializedSymbolicRef,
    ParameterKind,
    ProviderRef,
    ResolutionKind,
    SemanticAnchorBinding,
    SemanticEndpoint,
    SemanticEndpointOrigin,
    SemanticEndpointRole,
    SemanticInterfaceDescriptor,
    SourceLineageManifest,
    SourceSpan,
    SurfaceDeclarationEvidence,
    SurfaceKind,
    build_parameter_value_slot,
    build_return_slot,
)


def _context(*, artifacts=None, modules=None, active=None, descriptors=None):
    artifacts = artifacts or {}
    modules = modules or {}
    if active is None:
        active = frozenset((*artifacts.values(), *modules.values()))
    return LineageResolutionContext(modules, artifacts, frozenset(active), descriptors or {})


def _facts(*, anchors=(), flows=(), surfaces=()):
    return ExtractedLineageSourceFacts(
        "pkg/mod.py", "sha256:test", anchors, flows, surfaces
    )


def test_materializer_is_deterministic_and_preserves_local_anchors_and_flows():
    span = SourceSpan(1, 0, 1, 1)
    facts = _facts(
        anchors=(ExtractedAnchorFact("anchor", "binding", span),),
        flows=(
            ExtractedFlowFact(
                "flow",
                ExtractedOccurrenceRef("anchor"),
                ExtractedOccurrenceRef("use"),
                LineageRelation.ASSIGNS,
                span,
                ResolutionKind.LEXICAL_EXACT,
                LineageConfidence.CONFIRMED,
                owner_local_id="anchor",
            ),
        ),
    )
    first = materialize_lineage_source_facts(facts, _context())
    assert first == materialize_lineage_source_facts(facts, _context())
    assert first.manifest.source_key == "pkg/mod.py"
    assert first.manifest.source_fingerprint == "sha256:test"
    assert first.anchors[0].reference == MaterializedOccurrenceRef(
        "pkg/mod.py", "sha256:test", "anchor"
    )
    assert first.flows[0].resolution_kind is ResolutionKind.LEXICAL_EXACT
    assert first.flows[0].owner_local_id == "anchor"
    assert first.manifest.flow_ownership_materialized is True


def test_materialized_slice_rejects_missing_or_cyclic_anchor_owner():
    span = SourceSpan(1, 0, 1, 1)
    source_key = "pkg.py"
    fingerprint = "f" * 64

    parent_ref = MaterializedOccurrenceRef(
        source_key,
        fingerprint,
        "parent",
    )
    child_ref = MaterializedOccurrenceRef(
        source_key,
        fingerprint,
        "child",
    )
    manifest = SourceLineageManifest(
        source_key,
        fingerprint,
        LINEAGE_FACTS_SEMANTIC_VERSION,
        LineageFamilyStatus.FRESH,
        1,
        0,
        0,
        semantic_anchor_bindings_materialized=True,
        anchor_ownership_materialized=True,
    )

    with pytest.raises(ValueError, match="owner must reference"):
        MaterializedLineageSourceFacts(
            manifest=manifest,
            anchors=(
                MaterializedAnchorFact(
                    "child",
                    child_ref,
                    "binding",
                    span,
                    owner_local_id="missing",
                ),
            ),
        )

    cycle_manifest = SourceLineageManifest(
        source_key,
        fingerprint,
        LINEAGE_FACTS_SEMANTIC_VERSION,
        LineageFamilyStatus.FRESH,
        2,
        0,
        0,
        semantic_anchor_bindings_materialized=True,
        anchor_ownership_materialized=True,
    )
    with pytest.raises(ValueError, match="ownership contains a cycle"):
        MaterializedLineageSourceFacts(
            manifest=cycle_manifest,
            anchors=tuple(
                sorted(
                    (
                        MaterializedAnchorFact(
                            "parent",
                            parent_ref,
                            "function",
                            span,
                            owner_local_id="child",
                        ),
                        MaterializedAnchorFact(
                            "child",
                            child_ref,
                            "binding",
                            span,
                            owner_local_id="parent",
                        ),
                    )
                )
            ),
        )


def test_materialized_flow_ownership_rejects_missing_or_foreign_owner():
    span = SourceSpan(1, 0, 1, 1)
    source_key = "pkg.py"
    fingerprint = "f" * 64
    owner = MaterializedOccurrenceRef(source_key, fingerprint, "owner")
    value = MaterializedOccurrenceRef(source_key, fingerprint, "value")
    manifest = SourceLineageManifest(
        source_key,
        fingerprint,
        LINEAGE_FACTS_SEMANTIC_VERSION,
        LineageFamilyStatus.FRESH,
        1,
        1,
        0,
        semantic_anchor_bindings_materialized=True,
        anchor_ownership_materialized=True,
        flow_ownership_materialized=True,
    )
    anchors = (MaterializedAnchorFact("owner", owner, "function", span),)
    with pytest.raises(ValueError, match="ownership is incomplete"):
        MaterializedLineageSourceFacts(
            manifest=manifest,
            anchors=anchors,
            flows=(
                MaterializedFlowFact(
                    "flow",
                    owner,
                    value,
                    LineageRelation.ASSIGNS,
                    span,
                    ResolutionKind.LEXICAL_EXACT,
                    LineageConfidence.CONFIRMED,
                ),
            ),
        )
    with pytest.raises(ValueError, match="owner must reference"):
        MaterializedLineageSourceFacts(
            manifest=manifest,
            anchors=anchors,
            flows=(
                MaterializedFlowFact(
                    "flow",
                    owner,
                    value,
                    LineageRelation.ASSIGNS,
                    span,
                    ResolutionKind.LEXICAL_EXACT,
                    LineageConfidence.CONFIRMED,
                    owner_local_id="missing",
                ),
            ),
        )


def test_reresolution_preserves_materialized_flow_ownership():
    span = SourceSpan(1, 0, 1, 1)
    facts = _facts(
        anchors=(ExtractedAnchorFact("owner", "function", span),),
        flows=(
            ExtractedFlowFact(
                "flow",
                ExtractedOccurrenceRef("owner"),
                ExtractedSymbolicRef(
                    ExtractedSymbolicKind.DEFINITION,
                    "pkg.mod",
                    "target",
                ),
                LineageRelation.BINDS,
                span,
                ResolutionKind.LEXICAL_EXACT,
                LineageConfidence.CONFIRMED,
                owner_local_id="owner",
            ),
        ),
    )
    initial = materialize_lineage_source_facts(
        facts,
        _context(artifacts={"pkg.mod::target": "A1/1"}),
    )
    rerun = reresolve_materialized_lineage_source_facts(
        initial,
        _context(artifacts={"pkg.mod::target": "A1/2"}),
    )
    assert initial.manifest.flow_ownership_materialized is True
    assert rerun.manifest.flow_ownership_materialized is True
    assert rerun.flows[0].owner_local_id == "owner"

def test_materializer_builds_and_reresolves_exact_semantic_anchor_bindings():
    span = SourceSpan(1, 0, 1, 1)
    module_anchor = "occ:v1:module:root:i:0:n:pkg"
    class_anchor = "occ:v1:class:0:i:0:n:Thing"
    method_anchor = "occ:v1:function:0.0:i:0:n:run"
    facts = _facts(
        anchors=tuple(
            sorted(
                (
                    ExtractedAnchorFact(module_anchor, "module", span),
                    ExtractedAnchorFact(
                        class_anchor,
                        "class",
                        span,
                        module_anchor,
                    ),
                    ExtractedAnchorFact(
                        method_anchor,
                        "function",
                        span,
                        class_anchor,
                    ),
                )
            )
        ),
    )
    initial = materialize_lineage_source_facts(
        facts,
        _context(
            artifacts={
                "pkg.mod::Thing": "A1/1",
                "pkg.mod::Thing.run": "A2/1",
            }
        ),
    )

    assert initial.manifest.semantic_anchor_bindings_materialized is True
    assert initial.semantic_anchors == (
        SemanticAnchorBinding(
            "A1/1",
            "pkg.mod::Thing",
            MaterializedOccurrenceRef("pkg/mod.py", "sha256:test", class_anchor),
        ),
        SemanticAnchorBinding(
            "A2/1",
            "pkg.mod::Thing.run",
            MaterializedOccurrenceRef("pkg/mod.py", "sha256:test", method_anchor),
        ),
    )
    anchors_by_id = {
        anchor.local_id: anchor
        for anchor in initial.anchors
    }
    assert initial.manifest.anchor_ownership_materialized is True
    assert anchors_by_id[module_anchor].owner_local_id is None
    assert anchors_by_id[class_anchor].owner_local_id == module_anchor
    assert anchors_by_id[method_anchor].owner_local_id == class_anchor

    reresolved = reresolve_materialized_lineage_source_facts(
        initial,
        _context(
            artifacts={
                "pkg.mod::Thing": "A1/1",
                "pkg.mod::Thing.run": "A2/2",
            }
        ),
    )
    assert tuple(binding.owner_id for binding in reresolved.semantic_anchors) == (
        "A1/1",
        "A2/2",
    )
    assert reresolved.anchors == initial.anchors
    assert reresolved.manifest.anchor_ownership_materialized is True

    removed = reresolve_materialized_lineage_source_facts(
        reresolved,
        _context(artifacts={"pkg.mod::Thing": "A1/1"}),
    )
    assert tuple(binding.qualified_name for binding in removed.semantic_anchors) == (
        "pkg.mod::Thing",
    )


def test_exact_active_return_parameter_and_descriptor_slots_are_materialized():
    span = SourceSpan(1, 0, 1, 1)
    owner = "A1/1"
    parameter_id = "occ:v1:parameter_poskw:0:i:0:n:value"
    parameter = ExtractedSymbolicRef(
        ExtractedSymbolicKind.PARAMETER, "pkg.mod", "run", parameter_id
    )
    returned = ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, "pkg.mod", "run")
    slots = tuple(sorted((
        build_parameter_value_slot(
            owner, ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=0
        ),
        build_return_slot(owner),
    )))
    descriptor = SemanticInterfaceDescriptor(owner, slots, "digest")
    facts = _facts(flows=(
        ExtractedFlowFact(
            "a", ExtractedOccurrenceRef("x"), parameter,
            LineageRelation.ARGUMENT_TO_PARAMETER, span,
            ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED,
        ),
        ExtractedFlowFact(
            "b", returned, ExtractedOccurrenceRef("x"), LineageRelation.RETURNS,
            span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED,
        ),
    ))
    result = materialize_lineage_source_facts(
        facts, _context(artifacts={"pkg.mod::run": owner}, descriptors={owner: descriptor})
    )
    assert isinstance(result.flows[0].target, SemanticEndpoint)
    assert result.interface_descriptors == (descriptor,)


def test_missing_or_ambiguous_slot_stays_explicit_and_dynamic_surface_is_preserved(monkeypatch):
    span = SourceSpan(1, 0, 1, 1)
    missing = ExtractedSymbolicRef(
        ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "missing"
    )
    facts = _facts(
        flows=(
            ExtractedFlowFact(
                "flow", ExtractedOccurrenceRef("x"), missing, LineageRelation.EXPOSES,
                span, ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED,
            ),
        ),
        surfaces=(
            ExtractedSurfaceFact(
                "surface", SurfaceKind.REGISTRATION, missing, span,
                ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC,
                "missing", "runtime", ProviderRef("fixture", "1"),
                SurfaceDeclarationEvidence.STATIC_DECLARATION,
            ),
        ),
    )
    monkeypatch.setattr(
        builtins, "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("I/O")),
    )
    result = materialize_lineage_source_facts(facts, _context())
    assert isinstance(result.flows[0].target, MaterializedSymbolicRef)
    assert result.flows[0].target.kind is ExtractedSymbolicKind.PUBLIC_TARGET
    assert result.surfaces[0].dynamic_boundary == "runtime"
    assert result.surfaces[0].provider == ProviderRef("fixture", "1")


def test_active_mapping_cannot_contain_recovery_and_bad_parameter_is_rejected():
    with pytest.raises(ValueError, match="active owner"):
        _context(artifacts={"pkg.mod::run": "A1/1"}, active=())
    span = SourceSpan(1, 0, 1, 1)
    bad = ExtractedSymbolicRef(
        ExtractedSymbolicKind.PARAMETER, "pkg.mod", "run",
        "binding:v1:p:i:0:n:value",
    )
    facts = _facts(flows=(
        ExtractedFlowFact(
            "flow", ExtractedOccurrenceRef("x"), bad, LineageRelation.BINDS,
            span, ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED,
        ),
    ))
    with pytest.raises(ValueError, match="Invalid local occurrence id"):
        materialize_lineage_source_facts(
            facts, _context(artifacts={"pkg.mod::run": "A1/1"})
        )


def test_materializer_does_not_mutate_input_mappings():
    artifacts = {"pkg.mod::run": "A1/1"}
    context = _context(artifacts=artifacts)
    materialize_lineage_source_facts(_facts(), context)
    assert artifacts == {"pkg.mod::run": "A1/1"}


def test_compact_origins_preserve_only_strengthened_endpoint_provenance():
    span = SourceSpan(1, 0, 1, 1)
    reference = ExtractedSymbolicRef(
        ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "target"
    )
    facts = _facts(flows=(
        ExtractedFlowFact(
            "flow", ExtractedOccurrenceRef("local"), reference,
            LineageRelation.EXPOSES, span, ResolutionKind.IMPORT_EXACT,
            LineageConfidence.CONFIRMED,
        ),
    ))
    materialized = materialize_lineage_source_facts(
        facts, _context(artifacts={"pkg.mod::target": "A1/1"})
    )
    assert materialized.flows[0].target == SemanticEndpoint("A1/1")
    assert materialized.semantic_endpoint_origins == (
        SemanticEndpointOrigin(
            "pkg/mod.py", "sha256:test", "flow",
            SemanticEndpointRole.FLOW_TARGET,
            ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "target",
        ),
    )

    removed = reresolve_materialized_lineage_source_facts(
        materialized, _context()
    )
    assert isinstance(removed.flows[0].target, MaterializedSymbolicRef)
    assert removed.semantic_endpoint_origins == ()

    restored = reresolve_materialized_lineage_source_facts(
        removed, _context(artifacts={"pkg.mod::target": "A1/2"})
    )
    assert restored.flows[0].target == SemanticEndpoint("A1/2")
    assert len(restored.semantic_endpoint_origins) == 1



def test_active_symbol_and_state_resolve_only_with_exact_existing_slot():
    span = SourceSpan(1, 0, 1, 1)
    artifact_owner, module_owner = "A2/1", "2/1"
    state_slot = __import__(
        "contextor.core.domain.lineage_facts", fromlist=["build_module_global_slot"]
    ).build_module_global_slot(module_owner, "setting")
    state_descriptor = SemanticInterfaceDescriptor(module_owner, (state_slot,), "state")
    definition = ExtractedSymbolicRef(
        ExtractedSymbolicKind.DEFINITION, "pkg.mod", "thing"
    )
    state = ExtractedSymbolicRef(ExtractedSymbolicKind.STATE, "pkg.mod", "setting")
    facts = _facts(flows=(
        ExtractedFlowFact(
            "a", ExtractedOccurrenceRef("x"), definition, LineageRelation.EXPOSES,
            span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED,
        ),
        ExtractedFlowFact(
            "b", ExtractedOccurrenceRef("x"), state, LineageRelation.READS_STATE,
            span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED,
        ),
    ))
    result = materialize_lineage_source_facts(
        facts,
        _context(
            artifacts={"pkg.mod::thing": artifact_owner},
            modules={"pkg.mod": module_owner},
            descriptors={module_owner: state_descriptor},
        ),
    )
    assert result.flows[0].target == SemanticEndpoint(artifact_owner)
    assert result.flows[1].target == SemanticEndpoint(module_owner, state_slot)
    assert result.interface_descriptors == (state_descriptor,)


def test_missing_exact_slot_is_an_explicit_source_local_placeholder():
    span = SourceSpan(1, 0, 1, 1)
    state = ExtractedSymbolicRef(ExtractedSymbolicKind.STATE, "pkg.mod", "setting")
    facts = _facts(flows=(
        ExtractedFlowFact(
            "flow", ExtractedOccurrenceRef("x"), state, LineageRelation.READS_STATE,
            span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED,
        ),
    ))
    result = materialize_lineage_source_facts(
        facts, _context(modules={"pkg.mod": "2/1"})
    )
    assert isinstance(result.flows[0].target, MaterializedSymbolicRef)
    assert result.flows[0].target.kind is ExtractedSymbolicKind.STATE


@pytest.mark.parametrize(
    ("kind", "resolution_kind", "confidence"),
    [
        (ExtractedSymbolicKind.PUBLIC_TARGET, ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED),
        (ExtractedSymbolicKind.PUBLIC_TARGET, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC),
        (ExtractedSymbolicKind.PUBLIC_TARGET, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED),
        (ExtractedSymbolicKind.PUBLIC_TARGET, ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED),
    ],
)
def test_non_exact_evidence_never_strengthens_from_same_named_active_identity(
    kind, resolution_kind, confidence,
):
    span = SourceSpan(1, 0, 1, 1)
    reference = ExtractedSymbolicRef(kind, "pkg.mod", "target")
    kwargs = {"dynamic_boundary": "runtime"} if resolution_kind is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY else {}
    facts = _facts(flows=(
        ExtractedFlowFact(
            "flow", ExtractedOccurrenceRef("x"), reference, LineageRelation.EXPOSES,
            span, resolution_kind, confidence, **kwargs,
        ),
    ))
    result = materialize_lineage_source_facts(
        facts, _context(artifacts={"pkg.mod::target": "A9/1"})
    )
    target = result.flows[0].target
    assert isinstance(target, MaterializedSymbolicRef)
    assert (target.source_key, target.source_fingerprint) == ("pkg/mod.py", "sha256:test")
    assert target.symbol_name == "target"


def test_exact_surface_requires_endpoint_but_unresolved_surface_keeps_symbolic_boundary():
    span = SourceSpan(1, 0, 1, 1)
    reference = ExtractedSymbolicRef(ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "target")
    unresolved = _facts(surfaces=(
        ExtractedSurfaceFact(
            "surface", SurfaceKind.EXPORT, reference, span, ResolutionKind.UNRESOLVED_NAME,
            LineageConfidence.UNRESOLVED, "target",
        ),
    ))
    result = materialize_lineage_source_facts(
        unresolved, _context(artifacts={"pkg.mod::target": "A9/1"})
    )
    assert isinstance(result.surfaces[0].exposed, MaterializedSymbolicRef)
