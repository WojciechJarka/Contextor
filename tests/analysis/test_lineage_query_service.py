from types import SimpleNamespace

import pytest

from contextor.core.domain.lineage_facts import (
    ExtractedSymbolicKind,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    MaterializedFlowFact,
    MaterializedLineageSourceFacts,
    MaterializedAnchorFact,
    MaterializedOccurrenceRef,
    MaterializedSurfaceFact,
    MaterializedSymbolicRef,
    ResolutionKind,
    SemanticAnchorBinding,
    SemanticEndpoint,
    SourceLineageManifest,
    SourceSpan,
    SurfaceDeclarationEvidence,
    SurfaceKind,
)
from contextor.core.lineage_query import (
    LineageQueryService,
    RepositoryStateLineageBackend,
    ResolvedLineageTarget,
)
from contextor.core.report_query import IndexCatalog


def _service(artifacts: dict[str, str]) -> LineageQueryService:
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            lineage_facts_state="fresh",
            lineage_facts_by_source={},
        )
    )
    return LineageQueryService(
        backend,
        IndexCatalog(
            modules={},
            artifacts=artifacts,
        ),
    )


def test_resolves_active_artifact_id_exactly():
    service = _service(
        {"A17/2": "pkg.mod::handler"}
    )

    result = service.resolve_target("a17/2")

    assert result.status == "resolved"
    assert result.target == ResolvedLineageTarget(
        artifact_id="A17/2",
        qualified_name="pkg.mod::handler",
        module_name="pkg.mod",
        symbol_name="handler",
        resolution="exact_id",
    )
    assert result.candidates == ()


def test_resolves_exact_qualified_identity_to_same_owner():
    service = _service(
        {"A17/2": "pkg.mod::handler"}
    )

    result = service.resolve_target("pkg.mod::handler")

    assert result.status == "resolved"
    assert result.target == ResolvedLineageTarget(
        artifact_id="A17/2",
        qualified_name="pkg.mod::handler",
        module_name="pkg.mod",
        symbol_name="handler",
        resolution="exact_identity",
    )


def test_missing_syntactic_artifact_id_never_falls_back():
    service = _service(
        {"A17/2": "pkg.mod::handler"}
    )

    result = service.resolve_target("A999/1")

    assert result.status == "not_found"
    assert result.target is None
    assert result.candidates == ()


@pytest.mark.parametrize(
    "query",
    [
        "",
        "handler",
        "pkg.mod",
        "pkg.mod::",
        "::handler",
        "pkg.mod::handler::extra",
    ],
)
def test_non_exact_target_shapes_are_rejected(query):
    service = _service(
        {"A17/2": "pkg.mod::handler"}
    )

    result = service.resolve_target(query)

    assert result.status == "invalid"
    assert result.target is None


def test_resolution_is_case_sensitive_for_qualified_identity():
    service = _service(
        {"A17/2": "pkg.mod::Handler"}
    )

    result = service.resolve_target("pkg.mod::handler")

    assert result.status == "not_found"


def test_duplicate_active_identity_fails_closed_as_ambiguous():
    service = _service(
        {
            "A18/1": "pkg.mod::handler",
            "A17/2": "pkg.mod::handler",
        }
    )

    result = service.resolve_target("pkg.mod::handler")

    assert result.status == "ambiguous"
    assert result.target is None
    assert tuple(item.artifact_id for item in result.candidates) == (
        "A17/2",
        "A18/1",
    )


def test_recovery_catalog_is_not_used_for_lineage_resolution():
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            lineage_facts_state="fresh",
            lineage_facts_by_source={},
        )
    )
    service = LineageQueryService(
        backend,
        IndexCatalog(
            modules={},
            artifacts={},
            recovered_artifacts={
                "A17/2": "pkg.mod::handler",
            },
        ),
    )

    by_id = service.resolve_target("A17/2")
    by_name = service.resolve_target("pkg.mod::handler")

    assert by_id.status == "not_found"
    assert by_name.status == "not_found"


def test_resolution_does_not_read_or_iterate_lineage_slices():
    class ResolutionOnlyBackend:
        def metadata(self):
            raise AssertionError("resolution must not read lineage metadata")

        def source_keys(self):
            raise AssertionError("resolution must not enumerate lineage")

        def get_source(self, source_key):
            raise AssertionError("resolution must not read lineage")

        def get_manifest(self, source_key):
            raise AssertionError("resolution must not read lineage")

        def source_keys_for_owner(self, owner_id):
            raise AssertionError("resolution must not index lineage")

        def iter_sources(self, source_keys=None):
            raise AssertionError("resolution must not iterate lineage")

    service = LineageQueryService(
        ResolutionOnlyBackend(),
        IndexCatalog(
            modules={},
            artifacts={"A17/2": "pkg.mod::handler"},
        ),
    )

    result = service.resolve_target("pkg.mod::handler")

    assert result.status == "resolved"
    assert result.target is not None
    assert result.target.artifact_id == "A17/2"


def _direct_slice(
    source_key: str,
    fingerprint: str,
    *,
    anchors=(),
    flows=(),
    surfaces=(),
    semantic_anchors=(),
):
    ordered_anchors = tuple(sorted(anchors))
    ordered_flows = tuple(sorted(flows))
    ordered_surfaces = tuple(sorted(surfaces))
    return MaterializedLineageSourceFacts(
        manifest=SourceLineageManifest(
            source_key=source_key,
            source_fingerprint=fingerprint,
            semantic_version="1",
            status=LineageFamilyStatus.FRESH,
            anchor_count=len(ordered_anchors),
            flow_count=len(ordered_flows),
            surface_count=len(ordered_surfaces),
            semantic_anchor_bindings_materialized=True,
        ),
        anchors=ordered_anchors,
        flows=ordered_flows,
        surfaces=ordered_surfaces,
        semantic_anchors=tuple(sorted(semantic_anchors)),
    )


def _direct_service(*, family_state="fresh"):
    owner = "A17/2"
    other_owner = "A99/1"
    fp_a = "a" * 64
    fp_b = "b" * 64
    span = SourceSpan(4, 1, 4, 8)

    symbolic_boundary = MaterializedSymbolicRef(
        source_key="pkg/a.py",
        source_fingerprint=fp_a,
        kind=ExtractedSymbolicKind.PUBLIC_TARGET,
        module_name="external.pkg",
        symbol_name="unknown",
    )

    source_a = _direct_slice(
        "pkg/a.py",
        fp_a,
        flows=(
            MaterializedFlowFact(
                "a_incoming",
                symbolic_boundary,
                SemanticEndpoint(owner),
                LineageRelation.ALIASES,
                span,
                ResolutionKind.IMPORT_EXACT,
                LineageConfidence.CONFIRMED,
            ),
            MaterializedFlowFact(
                "b_unrelated",
                MaterializedOccurrenceRef("pkg/a.py", fp_a, "local"),
                SemanticEndpoint(other_owner),
                LineageRelation.ASSIGNS,
                span,
                ResolutionKind.LEXICAL_EXACT,
                LineageConfidence.CONFIRMED,
            ),
        ),
    )

    source_b = _direct_slice(
        "pkg/b.py",
        fp_b,
        flows=(
            MaterializedFlowFact(
                "a_outgoing",
                SemanticEndpoint(owner),
                MaterializedOccurrenceRef("pkg/b.py", fp_b, "consumer"),
                LineageRelation.CALL_RESULT,
                span,
                ResolutionKind.CALL_EXACT,
                LineageConfidence.CONFIRMED,
            ),
        ),
        surfaces=(
            MaterializedSurfaceFact(
                "surface_target",
                SurfaceKind.PUBLIC_SYMBOL,
                SemanticEndpoint(owner),
                span,
                ResolutionKind.LEXICAL_EXACT,
                LineageConfidence.CONFIRMED,
                "handler",
                declaration_evidence=SurfaceDeclarationEvidence.STATIC_DECLARATION,
            ),
        ),
    )

    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            revision=21,
            provenance="live",
            lineage_facts_state=family_state,
            lineage_facts_semantic_version="1",
            lineage_facts_by_source={
                "pkg/b.py": source_b,
                "pkg/a.py": source_a,
            },
        )
    )
    service = LineageQueryService(
        backend,
        IndexCatalog(
            modules={},
            artifacts={
                owner: "pkg.target::handler",
                other_owner: "pkg.other::thing",
            },
        ),
    )
    resolved = service.resolve_target(owner)
    assert resolved.status == "resolved"
    assert resolved.target is not None
    return service, backend, resolved.target, symbolic_boundary


def test_backend_returns_only_candidate_sources_for_semantic_owner():
    _, backend, target, _ = _direct_service()

    assert backend.source_keys_for_owner(target.artifact_id) == (
        "pkg/a.py",
        "pkg/b.py",
    )
    assert backend.source_keys_for_owner("A404/1") == ()


def test_direct_facts_return_exact_incoming_outgoing_and_surface_matches():
    service, _, target, symbolic_boundary = _direct_service()

    result = service.direct_facts(target)

    assert result.target is target
    assert result.metadata.revision == 21
    assert result.complete is True

    assert tuple(item.source_key for item in result.incoming) == (
        "pkg/a.py",
    )
    assert tuple(item.flow.local_id for item in result.incoming) == (
        "a_incoming",
    )
    assert result.incoming[0].flow.source == symbolic_boundary

    assert tuple(item.source_key for item in result.outgoing) == (
        "pkg/b.py",
    )
    assert tuple(item.flow.local_id for item in result.outgoing) == (
        "a_outgoing",
    )

    assert tuple(item.source_key for item in result.surfaces) == (
        "pkg/b.py",
    )
    assert tuple(item.surface.local_id for item in result.surfaces) == (
        "surface_target",
    )


def test_direct_facts_do_not_match_unrelated_semantic_owner():
    service, _, _, _ = _direct_service()
    resolved = service.resolve_target("A99/1")
    assert resolved.status == "resolved"
    assert resolved.target is not None

    result = service.direct_facts(resolved.target)

    assert tuple(item.flow.local_id for item in result.incoming) == (
        "b_unrelated",
    )
    assert result.outgoing == ()
    assert result.surfaces == ()


def test_direct_facts_expose_nonfresh_family_fail_closed():
    service, _, target, _ = _direct_service(family_state="stale")

    result = service.direct_facts(target)

    assert result.metadata.family_state == "stale"
    assert result.complete is False
    assert result.incoming
    assert result.outgoing


def test_direct_facts_seed_ordinary_symbol_from_semantic_anchor_binding():
    owner = "A17/2"
    source_key = "pkg/target.py"
    fingerprint = "c" * 64
    span = SourceSpan(4, 1, 4, 8)
    occurrence = MaterializedOccurrenceRef(source_key, fingerprint, "handler")
    anchor = MaterializedAnchorFact("handler", occurrence, "function", span)
    binding = SemanticAnchorBinding(owner, "pkg.target::handler", occurrence)
    surface = MaterializedSurfaceFact(
        "public-handler",
        SurfaceKind.PUBLIC_SYMBOL,
        occurrence,
        span,
        ResolutionKind.UNRESOLVED_NAME,
        LineageConfidence.UNRESOLVED,
        "handler",
    )
    source = _direct_slice(
        source_key,
        fingerprint,
        anchors=(anchor,),
        surfaces=(surface,),
        semantic_anchors=(binding,),
    )
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            lineage_facts_state="fresh",
            lineage_facts_semantic_version="1",
            lineage_facts_by_source={source_key: source},
        )
    )
    service = LineageQueryService(
        backend,
        IndexCatalog(modules={}, artifacts={owner: "pkg.target::handler"}),
    )
    resolved = service.resolve_target(owner)
    assert resolved.target is not None

    result = service.direct_facts(resolved.target)

    assert result.complete is True
    assert tuple(item.binding for item in result.anchors) == (binding,)
    assert tuple(item.surface.local_id for item in result.surfaces) == (
        "public-handler",
    )
    assert result.incoming == ()
    assert result.outgoing == ()


def test_direct_facts_are_incomplete_when_fresh_slice_lacks_anchor_materialization():
    service, backend, target, _ = _direct_service()
    source = backend.get_source("pkg/a.py")
    assert source is not None
    object.__setattr__(
        source.manifest,
        "semantic_anchor_bindings_materialized",
        False,
    )

    result = service.direct_facts(target)

    assert result.metadata.family_state == "fresh"
    assert result.metadata.semantic_anchor_bindings_complete is False
    assert result.complete is False
