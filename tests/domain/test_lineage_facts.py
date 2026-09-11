from __future__ import annotations

import sys

import pytest

from contextor.core.domain.lineage_facts import (
    LINEAGE_FACTS_SEMANTIC_VERSION,
    ExtractedAnchorFact,
    ExtractedFlowFact,
    ExtractedLineageSourceFacts,
    ExtractedOccurrenceRef,
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    ExtractedSurfaceFact,
    ProviderRef,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    MaterializedFlowFact,
    MaterializedAnchorFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    MaterializedSymbolicRef,
    MaterializedSurfaceFact,
    ParameterKind,
    ResolutionKind,
    SemanticEndpoint,
    SourceLineageManifest,
    SourceSpan,
    SurfaceDeclarationEvidence,
    SurfaceKind,
    build_class_attr_slot,
    build_instance_attr_slot,
    build_keyword_binding_slot,
    build_module_global_slot,
    build_parameter_value_slot,
    build_positional_binding_slot,
    build_return_slot,
    claims_exact_semantic_target,
    parse_semantic_slot,
)


def test_extracted_facts_are_local_and_materialized_flows_require_semantic_endpoints():
    span = SourceSpan(1, 0, 1, 3)
    source = ExtractedOccurrenceRef("occ-1")
    target = ExtractedOccurrenceRef("occ-2")
    extracted = ExtractedFlowFact(
        "flow-1",
        source,
        target,
        LineageRelation.ASSIGNS,
        span,
        ResolutionKind.LEXICAL_EXACT,
        LineageConfidence.CONFIRMED,
    )
    facts = ExtractedLineageSourceFacts(
        "pkg/mod.py",
        "sha256:one",
        anchors=(ExtractedAnchorFact("occ-1", "binding", span), ExtractedAnchorFact("occ-2", "use", span)),
        flows=(extracted,),
    )
    assert facts.flows[0].source == source
    with pytest.raises(TypeError):
        MaterializedFlowFact(  # type: ignore[arg-type]
            "flow-2", source, target, LineageRelation.ASSIGNS, span,
            ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED,
        )


def test_materialized_occurrences_can_flow_through_semantic_slot_but_not_cross_source():
    span = SourceSpan(1, 0, 1, 3)
    left = MaterializedOccurrenceRef("a.py", "a", "call")
    right = MaterializedOccurrenceRef("a.py", "a", "result")
    endpoint = SemanticEndpoint("A1/1", build_return_slot("A1/1"))
    MaterializedFlowFact("to-slot", left, endpoint, LineageRelation.RETURNS, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED)
    MaterializedFlowFact("from-slot", endpoint, right, LineageRelation.CALL_RESULT, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED)
    with pytest.raises(ValueError, match="Cross-source"):
        MaterializedFlowFact("bad", left, MaterializedOccurrenceRef("b.py", "b", "use"), LineageRelation.ASSIGNS, span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED)
    with pytest.raises(TypeError):
        MaterializedFlowFact("bad-phase", ExtractedOccurrenceRef("x"), endpoint, LineageRelation.ASSIGNS, span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED)  # type: ignore[arg-type]


def test_extracted_symbolic_reference_has_no_persistent_identity():
    symbolic = ExtractedSymbolicRef(ExtractedSymbolicKind.CALLEE, "pkg.mod", "handler", "call")
    assert (symbolic.module_name, symbolic.symbol_name) == ("pkg.mod", "handler")
    assert symbolic.qualified_name == "pkg.mod::handler"
    assert not hasattr(symbolic, "owner_id")


def test_extracted_flow_accepts_all_phase_safe_endpoint_combinations():
    span = SourceSpan(1, 0, 1, 1)
    occ = ExtractedOccurrenceRef("occ")
    parameter = ExtractedSymbolicRef(ExtractedSymbolicKind.PARAMETER, "pkg.mod", "parameter")
    state = ExtractedSymbolicRef(ExtractedSymbolicKind.STATE, "pkg.mod", "state")
    returned = ExtractedSymbolicRef(ExtractedSymbolicKind.RETURN, "pkg.mod", "function")
    public = ExtractedSymbolicRef(ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "public")
    for source, target in ((occ, parameter), (occ, state), (returned, occ), (occ, public), (occ, occ)):
        ExtractedFlowFact("flow-" + str(source) + str(target), source, target, LineageRelation.ASSIGNS, span, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED)


def test_materialized_slice_rejects_foreign_occurrences_but_allows_semantic_boundary():
    span = SourceSpan(1, 0, 1, 1)
    manifest = SourceLineageManifest("a.py", "a", "1", LineageFamilyStatus.FRESH, 1, 1, 1)
    local = MaterializedOccurrenceRef("a.py", "a", "local")
    foreign = MaterializedOccurrenceRef("b.py", "b", "foreign")
    endpoint = SemanticEndpoint("A1/1", build_return_slot("A1/1"))
    good = MaterializedLineageSourceFacts(manifest, (MaterializedAnchorFact("a", local, "binding", span),), (MaterializedFlowFact("f", local, endpoint, LineageRelation.RETURNS, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED),), (MaterializedSurfaceFact("s", SurfaceKind.EXPORT, endpoint, span, ResolutionKind.IMPORT_EXACT, LineageConfidence.CONFIRMED, "x"),))
    assert good.flows[0].target == endpoint
    anchor_manifest = SourceLineageManifest("a.py", "a", "1", LineageFamilyStatus.FRESH, 1, 0, 0)
    with pytest.raises(ValueError, match="foreign local reference"):
        MaterializedLineageSourceFacts(anchor_manifest, (MaterializedAnchorFact("a", foreign, "binding", span),), (), ())
    source_manifest = SourceLineageManifest("a.py", "a", "1", LineageFamilyStatus.FRESH, 0, 1, 0)
    with pytest.raises(ValueError, match="foreign local reference"):
        MaterializedLineageSourceFacts(source_manifest, (), (MaterializedFlowFact("f", foreign, endpoint, LineageRelation.RETURNS, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED),), ())
    with pytest.raises(ValueError, match="foreign local reference"):
        MaterializedLineageSourceFacts(source_manifest, (), (MaterializedFlowFact("f", endpoint, foreign, LineageRelation.CALL_RESULT, span, ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED),), ())
    surface_manifest = SourceLineageManifest("a.py", "a", "1", LineageFamilyStatus.FRESH, 0, 0, 1)
    with pytest.raises(ValueError, match="foreign local reference"):
        MaterializedLineageSourceFacts(surface_manifest, (), (), (MaterializedSurfaceFact("s", SurfaceKind.EXPORT, foreign, span, ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, "x"),))


def test_provider_pair_and_dynamic_surface_boundary_contract():
    span = SourceSpan(1, 0, 1, 1)
    with pytest.raises(ValueError, match="dynamic_boundary"):
        ExtractedSurfaceFact("s", SurfaceKind.REGISTRATION, ExtractedOccurrenceRef("x"), span, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "x")
    surface = ExtractedSurfaceFact("s", SurfaceKind.REGISTRATION, ExtractedOccurrenceRef("x"), span, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "x", dynamic_boundary="runtime", provider=ProviderRef("provider", "1"))
    assert surface.provider == ProviderRef("provider", "1")
    with pytest.raises(ValueError):
        ProviderRef("provider", "")
    with pytest.raises(TypeError, match="ProviderRef"):
        ExtractedSurfaceFact("s2", SurfaceKind.REGISTRATION, ExtractedOccurrenceRef("x"), span, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "x", dynamic_boundary="runtime", provider="provider" )  # type: ignore[arg-type]


def test_slot_builder_parser_round_trip_and_opaque_owner_escaping():
    owner = "A17/2:opaque owner"
    slot = build_return_slot(owner)
    parsed = parse_semantic_slot(slot)
    assert parsed.owner_id == owner
    assert parsed.raw == slot
    assert build_return_slot(parsed.owner_id) == slot


def test_posonly_and_poskw_value_and_positional_slots_ignore_renames():
    owner = "A1/1"
    assert build_parameter_value_slot(owner, ParameterKind.POSITIONAL_ONLY, ordinal=0) == build_parameter_value_slot(owner, ParameterKind.POSITIONAL_ONLY, ordinal=0)
    assert build_parameter_value_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=1) == build_parameter_value_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=1)
    assert build_positional_binding_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=1) == build_positional_binding_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, ordinal=1)


def test_poskw_keyword_binding_is_name_sensitive():
    owner = "A1/1"
    assert build_keyword_binding_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, name="value") != build_keyword_binding_slot(owner, ParameterKind.POSITIONAL_OR_KEYWORD, name="item")


def test_kwonly_value_is_name_based_and_reorder_independent():
    owner = "A1/1"
    a = build_parameter_value_slot(owner, ParameterKind.KEYWORD_ONLY, name="a")
    b = build_parameter_value_slot(owner, ParameterKind.KEYWORD_ONLY, name="b")
    assert a == build_parameter_value_slot(owner, ParameterKind.KEYWORD_ONLY, name="a")
    assert a != b
    assert build_keyword_binding_slot(owner, ParameterKind.KEYWORD_ONLY, name="a") != build_keyword_binding_slot(owner, ParameterKind.KEYWORD_ONLY, name="b")


def test_kwonly_rename_is_sensitive():
    owner = "A1/1"
    assert build_parameter_value_slot(owner, ParameterKind.KEYWORD_ONLY, name="a") != build_parameter_value_slot(owner, ParameterKind.KEYWORD_ONLY, name="c")


def test_vararg_and_varkw_collectors_have_no_position_or_key_parts():
    owner = "A1/1"
    vararg = parse_semantic_slot(build_parameter_value_slot(owner, ParameterKind.VAR_POSITIONAL))
    varkw = parse_semantic_slot(build_parameter_value_slot(owner, ParameterKind.VAR_KEYWORD))
    assert vararg.parts == (ParameterKind.VAR_POSITIONAL.value,)
    assert varkw.parts == (ParameterKind.VAR_KEYWORD.value,)
    assert parse_semantic_slot(build_positional_binding_slot(owner, ParameterKind.VAR_POSITIONAL)).parts == (ParameterKind.VAR_POSITIONAL.value,)
    assert parse_semantic_slot(build_keyword_binding_slot(owner, ParameterKind.VAR_KEYWORD)).parts == (ParameterKind.VAR_KEYWORD.value,)


@pytest.mark.parametrize("name", ["varkw", "vararg", "fixed", "kwonly", "a:b/c d%"])
def test_fixed_keyword_slots_are_unambiguous_and_round_trip_safe(name):
    owner = "A1/1"
    fixed = build_keyword_binding_slot(owner, ParameterKind.KEYWORD_ONLY, name=name)
    collector = build_keyword_binding_slot(owner, ParameterKind.VAR_KEYWORD)
    assert fixed != collector
    assert parse_semantic_slot(fixed).parts == ("fixed", name)
    assert parse_semantic_slot(collector).parts == ("varkw",)


def test_state_slots_do_not_conflate_namespaces():
    assert len({
        build_module_global_slot("11/1", "x"),
        build_class_attr_slot("A2/1", "x"),
        build_instance_attr_slot("A2/1", "x"),
    }) == 3


def test_surface_confidence_contract_rejects_confirmed_name_convention():
    span = SourceSpan(1, 0, 1, 1)
    with pytest.raises(ValueError, match="PYTHON_NAME_CONVENTION"):
        ExtractedFlowFact(
            "flow",
            ExtractedOccurrenceRef("a"),
            ExtractedOccurrenceRef("b"),
            LineageRelation.EXPOSES,
            span,
            ResolutionKind.PYTHON_NAME_CONVENTION,
            LineageConfidence.CONFIRMED,
        )
    assert SurfaceKind.EXPORT.value == "EXPORT"
    assert LineageConfidence.CONFIRMED.value == "CONFIRMED"


@pytest.mark.parametrize(
    ("kind", "confidence"),
    [
        (ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.CONFIRMED),
        (ResolutionKind.UNRESOLVED_NAME, LineageConfidence.INFERRED),
        (ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.UNRESOLVED),
        (ResolutionKind.LEXICAL_EXACT, LineageConfidence.DYNAMIC),
    ],
)
def test_invalid_resolution_confidence_combinations_are_rejected(kind, confidence):
    with pytest.raises(ValueError):
        ExtractedFlowFact("flow", ExtractedOccurrenceRef("a"), ExtractedOccurrenceRef("b"), LineageRelation.ASSIGNS, SourceSpan(1, 0, 1, 1), kind, confidence)


def test_closed_relation_additions_are_available():
    assert LineageRelation.DEFAULTS_TO_PARAMETER.value == "DEFAULTS_TO_PARAMETER"
    assert LineageRelation.DECLARES_PUBLIC_NAMES.value == "DECLARES_PUBLIC_NAMES"


def test_frozen_hashable_ordered_facts_and_fresh_manifest_count_contract():
    span = SourceSpan(1, 0, 1, 1)
    anchors = (
        ExtractedAnchorFact("a", "binding", span),
        ExtractedAnchorFact("b", "use", span),
    )
    assert tuple(sorted(anchors)) == anchors
    assert len({anchors[0], anchors[1]}) == 2
    with pytest.raises(ValueError, match="sorted and unique"):
        ExtractedLineageSourceFacts("x.py", "hash", anchors=tuple(reversed(anchors)))
    manifest = SourceLineageManifest("x.py", "hash", "1", LineageFamilyStatus.FRESH, 0, 0, 0)
    assert manifest.status == LineageFamilyStatus.FRESH


def test_domain_module_does_not_import_or_construct_persistent_registry():
    module = sys.modules["contextor.core.domain.lineage_facts"]
    assert "PersistentIdentityRegistry" not in vars(module)
    assert not any(name.endswith("persistent_registry") for name in sys.modules if name.startswith("contextor.core.domain.lineage_facts"))


@pytest.mark.parametrize(
    ("declaration_evidence", "resolution_kind", "confidence", "dynamic_boundary"),
    [
        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED, None),
        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, None),
        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED, None),
        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "runtime"),
        (SurfaceDeclarationEvidence.STATIC_DECLARATION, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, None),
        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.LITERAL_CONTAINER_EXACT, LineageConfidence.CONFIRMED, None),
        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, None),
        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED, None),
        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "runtime"),
        (SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, None),
        (None, ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, None),
    ],
)
def test_surface_declaration_evidence_and_target_resolution_are_orthogonal(
    declaration_evidence,
    resolution_kind,
    confidence,
    dynamic_boundary,
):
    kind = (
        SurfaceKind.EXPORT
        if declaration_evidence is SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION
        else SurfaceKind.PUBLIC_SYMBOL
    )
    surface = ExtractedSurfaceFact(
        "surface",
        kind,
        ExtractedOccurrenceRef("occurrence"),
        SourceSpan(1, 0, 1, 1),
        resolution_kind,
        confidence,
        "name",
        dynamic_boundary=dynamic_boundary,
        declaration_evidence=declaration_evidence,
    )
    assert surface.declaration_evidence is declaration_evidence


def test_literal_all_declaration_requires_export_surface_kind():
    span = SourceSpan(1, 0, 1, 1)
    ExtractedSurfaceFact(
        "export",
        SurfaceKind.EXPORT,
        ExtractedOccurrenceRef("occurrence"),
        span,
        ResolutionKind.LITERAL_CONTAINER_EXACT,
        LineageConfidence.CONFIRMED,
        "name",
        declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION,
    )
    for kind in (
        SurfaceKind.PUBLIC_SYMBOL,
        SurfaceKind.REEXPORT,
        SurfaceKind.ENTRYPOINT,
        SurfaceKind.REGISTRATION,
    ):
        with pytest.raises(ValueError, match="LITERAL_ALL_DECLARATION"):
            ExtractedSurfaceFact(
                "not-export",
                kind,
                ExtractedOccurrenceRef("occurrence"),
                span,
                ResolutionKind.UNRESOLVED_NAME,
                LineageConfidence.UNRESOLVED,
                "name",
                declaration_evidence=SurfaceDeclarationEvidence.LITERAL_ALL_DECLARATION,
            )


@pytest.mark.parametrize(
    "resolution_kind",
    [
        ResolutionKind.LEXICAL_EXACT,
        ResolutionKind.IMPORT_EXACT,
        ResolutionKind.CALL_EXACT,
        ResolutionKind.SIGNATURE_EXACT,
        ResolutionKind.STATIC_MRO_EXACT,
        ResolutionKind.LITERAL_CONTAINER_EXACT,
    ],
)
def test_materialized_confirmed_exact_surface_targets_require_semantic_endpoint(
    resolution_kind,
):
    span = SourceSpan(1, 0, 1, 1)
    occurrence = MaterializedOccurrenceRef("a.py", "fingerprint", "occurrence")
    with pytest.raises(ValueError, match="confirmed exact semantic surface target"):
        MaterializedSurfaceFact(
            "surface",
            SurfaceKind.EXPORT,
            occurrence,
            span,
            resolution_kind,
            LineageConfidence.CONFIRMED,
            "name",
        )
    surface = MaterializedSurfaceFact(
        "surface",
        SurfaceKind.EXPORT,
        SemanticEndpoint("artifact/1"),
        span,
        resolution_kind,
        LineageConfidence.CONFIRMED,
        "name",
    )
    assert isinstance(surface.exposed, SemanticEndpoint)


def test_materialized_confirmed_receptor_target_requires_semantic_endpoint():
    span = SourceSpan(1, 0, 1, 1)
    occurrence = MaterializedOccurrenceRef("a.py", "fingerprint", "occurrence")
    with pytest.raises(ValueError, match="confirmed exact semantic surface target"):
        MaterializedSurfaceFact(
            "surface",
            SurfaceKind.REGISTRATION,
            occurrence,
            span,
            ResolutionKind.RECEPTOR_PROVIDED,
            LineageConfidence.CONFIRMED,
            "name",
        )
    surface = MaterializedSurfaceFact(
        "surface",
        SurfaceKind.REGISTRATION,
        SemanticEndpoint("artifact/1"),
        span,
        ResolutionKind.RECEPTOR_PROVIDED,
        LineageConfidence.CONFIRMED,
        "name",
    )
    assert isinstance(surface.exposed, SemanticEndpoint)


def test_exact_reexport_uses_static_declaration_and_semantic_endpoint():
    surface = MaterializedSurfaceFact(
        "reexport",
        SurfaceKind.REEXPORT,
        SemanticEndpoint("artifact/1"),
        SourceSpan(1, 0, 1, 1),
        ResolutionKind.IMPORT_EXACT,
        LineageConfidence.CONFIRMED,
        "name",
        declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION,
    )
    assert surface.declaration_evidence is SurfaceDeclarationEvidence.STATIC_DECLARATION


@pytest.mark.parametrize(
    ("resolution_kind", "confidence", "dynamic_boundary"),
    [
        (ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, None),
        (ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED, None),
        (ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, "runtime"),
    ],
)
def test_nonexact_materialized_surface_targets_can_remain_local_occurrences(
    resolution_kind,
    confidence,
    dynamic_boundary,
):
    occurrence = MaterializedOccurrenceRef("a.py", "fingerprint", "occurrence")
    surface = MaterializedSurfaceFact(
        "surface",
        SurfaceKind.EXPORT,
        occurrence,
        SourceSpan(1, 0, 1, 1),
        resolution_kind,
        confidence,
        "name",
        dynamic_boundary=dynamic_boundary,
    )
    assert surface.exposed is occurrence


def test_surface_declaration_evidence_rejects_invalid_type_and_preserves_convention_guard():
    span = SourceSpan(1, 0, 1, 1)
    with pytest.raises(TypeError, match="declaration_evidence"):
        ExtractedSurfaceFact(
            "surface",
            SurfaceKind.EXPORT,
            ExtractedOccurrenceRef("occurrence"),
            span,
            ResolutionKind.UNRESOLVED_NAME,
            LineageConfidence.UNRESOLVED,
            "name",
            declaration_evidence="STATIC_DECLARATION",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="PYTHON_NAME_CONVENTION"):
        ExtractedSurfaceFact(
            "surface",
            SurfaceKind.PUBLIC_SYMBOL,
            ExtractedOccurrenceRef("occurrence"),
            span,
            ResolutionKind.PYTHON_NAME_CONVENTION,
            LineageConfidence.CONFIRMED,
            "name",
            declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION,
        )


def test_lineage_facts_semantic_version_remains_initial_version():
    assert LINEAGE_FACTS_SEMANTIC_VERSION == "1"


def test_materialized_symbolic_ref_is_slice_bound_and_never_an_occurrence():
    span = SourceSpan(1, 0, 1, 1)
    manifest = SourceLineageManifest(
        "a.py", "fingerprint", "1", LineageFamilyStatus.FRESH, 0, 1, 0
    )
    symbolic = MaterializedSymbolicRef(
        "a.py", "fingerprint", ExtractedSymbolicKind.PUBLIC_TARGET,
        "pkg.mod", "missing",
    )
    slice_ = MaterializedLineageSourceFacts(
        manifest, (), (
            MaterializedFlowFact(
                "flow", MaterializedOccurrenceRef("a.py", "fingerprint", "x"),
                symbolic, LineageRelation.EXPOSES, span,
                ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED,
            ),
        ), (),
    )
    assert slice_.flows[0].target == symbolic
    foreign = MaterializedSymbolicRef(
        "b.py", "other", ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "missing"
    )
    with pytest.raises(ValueError, match="foreign local reference"):
        MaterializedLineageSourceFacts(
            manifest, (), (
                MaterializedFlowFact(
                    "bad", MaterializedOccurrenceRef("a.py", "fingerprint", "x"),
                    foreign, LineageRelation.EXPOSES, span,
                    ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED,
                ),
            ), (),
        )

def test_materialized_anchor_requires_actual_occurrence_at_runtime():
    span = SourceSpan(1, 0, 1, 1)
    occurrence = MaterializedOccurrenceRef("a.py", "fingerprint", "local")
    assert MaterializedAnchorFact("anchor", occurrence, "binding", span).reference == occurrence
    symbolic = MaterializedSymbolicRef(
        "a.py", "fingerprint", ExtractedSymbolicKind.PUBLIC_TARGET, "pkg.mod", "target"
    )
    with pytest.raises(TypeError, match="canonical occurrence"):
        MaterializedAnchorFact("symbolic", symbolic, "binding", span)
    with pytest.raises(TypeError, match="canonical occurrence"):
        MaterializedAnchorFact("endpoint", SemanticEndpoint("A1/1"), "binding", span)


@pytest.mark.parametrize(
    ("kind", "confidence", "expected"),
    [
        (ResolutionKind.LEXICAL_EXACT, LineageConfidence.CONFIRMED, True),
        (ResolutionKind.IMPORT_EXACT, LineageConfidence.CONFIRMED, True),
        (ResolutionKind.CALL_EXACT, LineageConfidence.CONFIRMED, True),
        (ResolutionKind.SIGNATURE_EXACT, LineageConfidence.CONFIRMED, True),
        (ResolutionKind.STATIC_MRO_EXACT, LineageConfidence.CONFIRMED, True),
        (ResolutionKind.LITERAL_CONTAINER_EXACT, LineageConfidence.CONFIRMED, True),
        (ResolutionKind.RECEPTOR_PROVIDED, LineageConfidence.CONFIRMED, True),
        (ResolutionKind.UNRESOLVED_NAME, LineageConfidence.UNRESOLVED, False),
        (ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY, LineageConfidence.DYNAMIC, False),
        (ResolutionKind.PYTHON_NAME_CONVENTION, LineageConfidence.INFERRED, False),
        (ResolutionKind.BOUNDED_STATIC_SET, LineageConfidence.INFERRED, False),
        (ResolutionKind.CALL_EXACT, LineageConfidence.INFERRED, False),
    ],
)
def test_claims_exact_semantic_target_matrix(kind, confidence, expected):
    assert claims_exact_semantic_target(kind, confidence) is expected