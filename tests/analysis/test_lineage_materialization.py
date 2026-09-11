from __future__ import annotations

import builtins

import pytest

from contextor.core.analysis.lineage_materialization import (
    LineageResolutionContext,
    materialize_lineage_source_facts,
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
    LineageRelation,
    MaterializedOccurrenceRef,
    ParameterKind,
    ProviderRef,
    ResolutionKind,
    SemanticEndpoint,
    SemanticInterfaceDescriptor,
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
                "flow", ExtractedOccurrenceRef("anchor"), ExtractedOccurrenceRef("use"),
                LineageRelation.ASSIGNS, span, ResolutionKind.LEXICAL_EXACT,
                LineageConfidence.CONFIRMED,
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
    assert isinstance(result.flows[0].target, MaterializedOccurrenceRef)
    assert result.flows[0].target.local_id.startswith("unresolved:v1:public_target")
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
    assert isinstance(result.flows[0].target, MaterializedOccurrenceRef)
    assert result.flows[0].target.local_id.startswith("unresolved:v1:state")
