from dataclasses import replace
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
from contextor.core.lineage_query.index import build_lineage_query_indexes
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

    sources = {
        "pkg/b.py": source_b,
        "pkg/a.py": source_a,
    }
    owner_source_index, source_owner_index, anchor_complete = (
        build_lineage_query_indexes(sources)
    )
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            revision=21,
            provenance="live",
            lineage_facts_state=family_state,
            lineage_facts_semantic_version="1",
            lineage_facts_by_source=sources,
            lineage_owner_source_index=owner_source_index,
            lineage_source_owner_index=source_owner_index,
            lineage_query_index_state="fresh",
            lineage_semantic_anchor_bindings_complete=anchor_complete,
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
    sources = {source_key: source}
    owner_source_index, source_owner_index, anchor_complete = (
        build_lineage_query_indexes(sources)
    )
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            lineage_facts_state="fresh",
            lineage_facts_semantic_version="1",
            lineage_facts_by_source=sources,
            lineage_owner_source_index=owner_source_index,
            lineage_source_owner_index=source_owner_index,
            lineage_query_index_state="fresh",
            lineage_semantic_anchor_bindings_complete=anchor_complete,
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
    backend._state.lineage_semantic_anchor_bindings_complete = False

    result = service.direct_facts(target)

    assert result.metadata.family_state == "fresh"
    assert result.metadata.semantic_anchor_bindings_complete is False
    assert result.complete is False


def test_direct_facts_never_enumerates_repo_wide_source_keys(monkeypatch):
    service, backend, target, _ = _direct_service()
    monkeypatch.setattr(
        backend,
        "source_keys",
        lambda: (_ for _ in ()).throw(AssertionError("repo scan")),
    )

    result = service.direct_facts(target)

    assert result.incoming
    assert result.outgoing
def _lexical_scope_service(
    *,
    family_state="fresh",
    anchor_ownership=True,
    flow_ownership=True,
):
    owner = "A17/2"
    other_owner = "A99/1"
    source_key = "pkg/target.py"
    reference_key = "pkg/reference.py"
    fp = "d" * 64
    ref_fp = "e" * 64
    span = SourceSpan(1, 0, 1, 8)

    module_ref = MaterializedOccurrenceRef(
        source_key,
        fp,
        "module",
    )
    outer_ref = MaterializedOccurrenceRef(
        source_key,
        fp,
        "outer",
    )
    inner_ref = MaterializedOccurrenceRef(
        source_key,
        fp,
        "inner",
    )
    comprehension_ref = MaterializedOccurrenceRef(
        source_key,
        fp,
        "comprehension",
    )
    local_ref = MaterializedOccurrenceRef(
        source_key,
        fp,
        "local",
    )

    module_anchor = MaterializedAnchorFact(
        "module",
        module_ref,
        "module",
        span,
    )
    outer_anchor = MaterializedAnchorFact(
        "outer",
        outer_ref,
        "function",
        span,
        owner_local_id="module",
    )
    inner_anchor = MaterializedAnchorFact(
        "inner",
        inner_ref,
        "function",
        span,
        owner_local_id="outer",
    )
    comprehension_anchor = MaterializedAnchorFact(
        "comprehension",
        comprehension_ref,
        "comprehension",
        span,
        owner_local_id="outer",
    )
    local_anchor = MaterializedAnchorFact(
        "local",
        local_ref,
        "binding",
        span,
        owner_local_id="outer",
    )
    semantic_binding = SemanticAnchorBinding(
        owner,
        "pkg.target::outer",
        outer_ref,
    )

    source = MaterializedLineageSourceFacts(
        manifest=SourceLineageManifest(
            source_key=source_key,
            source_fingerprint=fp,
            semantic_version="1",
            status=LineageFamilyStatus.FRESH,
            anchor_count=5,
            flow_count=5,
            surface_count=0,
            semantic_anchor_bindings_materialized=True,
            anchor_ownership_materialized=anchor_ownership,
            flow_ownership_materialized=flow_ownership,
        ),
        anchors=tuple(
            sorted(
                (
                    module_anchor,
                    outer_anchor,
                    inner_anchor,
                    comprehension_anchor,
                    local_anchor,
                )
            )
        ),
        flows=tuple(
            sorted(
                (
                    MaterializedFlowFact(
                        "a_outer_bind",
                        outer_ref,
                        local_ref,
                        LineageRelation.BINDS,
                        span,
                        ResolutionKind.LEXICAL_EXACT,
                        LineageConfidence.CONFIRMED,
                        owner_local_id="outer",
                    ),
                    MaterializedFlowFact(
                        "b_outer_call",
                        local_ref,
                        MaterializedOccurrenceRef(
                            source_key,
                            fp,
                            "outer-result",
                        ),
                        LineageRelation.CALL_RESULT,
                        span,
                        ResolutionKind.CALL_EXACT,
                        LineageConfidence.CONFIRMED,
                        owner_local_id="outer",
                    ),
                    MaterializedFlowFact(
                        "c_inner_return",
                        inner_ref,
                        MaterializedOccurrenceRef(
                            source_key,
                            fp,
                            "inner-result",
                        ),
                        LineageRelation.RETURNS,
                        span,
                        ResolutionKind.LEXICAL_EXACT,
                        LineageConfidence.CONFIRMED,
                        owner_local_id="inner",
                    ),
                    MaterializedFlowFact(
                        "d_comprehension_assign",
                        comprehension_ref,
                        MaterializedOccurrenceRef(
                            source_key,
                            fp,
                            "comprehension-result",
                        ),
                        LineageRelation.ASSIGNS,
                        span,
                        ResolutionKind.LEXICAL_EXACT,
                        LineageConfidence.CONFIRMED,
                        owner_local_id="comprehension",
                    ),
                    MaterializedFlowFact(
                        "e_definition_default",
                        module_ref,
                        outer_ref,
                        LineageRelation.DEFAULTS_TO_PARAMETER,
                        span,
                        ResolutionKind.SIGNATURE_EXACT,
                        LineageConfidence.CONFIRMED,
                        owner_local_id="module",
                    ),
                )
            )
        ),
        semantic_anchors=(semantic_binding,),
    )

    reference_owner_ref = MaterializedOccurrenceRef(
        reference_key,
        ref_fp,
        "reference-owner",
    )
    reference = MaterializedLineageSourceFacts(
        manifest=SourceLineageManifest(
            source_key=reference_key,
            source_fingerprint=ref_fp,
            semantic_version="1",
            status=LineageFamilyStatus.FRESH,
            anchor_count=1,
            flow_count=1,
            surface_count=0,
            semantic_anchor_bindings_materialized=True,
            anchor_ownership_materialized=True,
            flow_ownership_materialized=True,
        ),
        anchors=(
            MaterializedAnchorFact(
                "reference-owner",
                reference_owner_ref,
                "function",
                span,
            ),
        ),
        flows=(
            MaterializedFlowFact(
                "reference-to-target",
                SemanticEndpoint(owner),
                reference_owner_ref,
                LineageRelation.CALL_RESULT,
                span,
                ResolutionKind.CALL_EXACT,
                LineageConfidence.CONFIRMED,
                owner_local_id="reference-owner",
            ),
        ),
    )

    sources = {
        source_key: source,
        reference_key: reference,
    }
    owner_source_index, source_owner_index, anchor_complete = (
        build_lineage_query_indexes(sources)
    )
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            revision=31,
            provenance="live",
            lineage_facts_state=family_state,
            lineage_facts_semantic_version="1",
            lineage_facts_by_source=sources,
            lineage_owner_source_index=owner_source_index,
            lineage_source_owner_index=source_owner_index,
            lineage_query_index_state="fresh",
            lineage_semantic_anchor_bindings_complete=(
                anchor_complete
            ),
        )
    )
    service = LineageQueryService(
        backend,
        IndexCatalog(
            modules={},
            artifacts={
                owner: "pkg.target::outer",
                other_owner: "pkg.other::thing",
            },
        ),
    )
    resolved = service.resolve_target(owner)
    assert resolved.status == "resolved"
    assert resolved.target is not None
    return service, backend, resolved.target


def test_lexical_scope_facts_return_only_exact_root_owned_flows():
    service, _, target = _lexical_scope_service()

    result = service.lexical_scope_facts(target)

    assert result.target is target
    assert result.metadata.revision == 31
    assert result.scope_available is True
    assert result.root_ambiguous is False
    assert result.materialization_complete is True
    assert result.complete is True

    assert len(result.roots) == 1
    assert result.roots[0].source_key == "pkg/target.py"
    assert result.roots[0].binding.owner_id == "A17/2"
    assert result.roots[0].anchor.local_id == "outer"
    assert result.roots[0].anchor.kind == "function"

    assert tuple(
        item.flow.local_id
        for item in result.flows
    ) == (
        "a_outer_bind",
        "b_outer_call",
    )

    assert tuple(
        item.anchor.local_id
        for item in result.nested_scopes
    ) == (
        "comprehension",
        "inner",
    )

    assert all(
        item.source_key == "pkg/target.py"
        for item in (
            *result.roots,
            *result.flows,
            *result.nested_scopes,
        )
    )


def test_lexical_scope_facts_do_not_cross_into_nested_scopes():
    service, _, target = _lexical_scope_service()

    result = service.lexical_scope_facts(target)

    returned = {
        item.flow.local_id
        for item in result.flows
    }
    assert "c_inner_return" not in returned
    assert "d_comprehension_assign" not in returned
    assert "e_definition_default" not in returned


def test_lexical_scope_facts_ignore_candidate_slice_without_semantic_root():
    service, backend, target = _lexical_scope_service()

    assert backend.source_keys_for_owner(
        target.artifact_id
    ) == (
        "pkg/reference.py",
        "pkg/target.py",
    )

    result = service.lexical_scope_facts(target)

    assert all(
        item.source_key != "pkg/reference.py"
        for item in (
            *result.roots,
            *result.flows,
            *result.nested_scopes,
        )
    )


def test_lexical_scope_facts_are_incomplete_without_flow_ownership():
    service, _, target = _lexical_scope_service(
        flow_ownership=False,
    )

    result = service.lexical_scope_facts(target)

    assert result.scope_available is True
    assert result.materialization_complete is False
    assert result.complete is False
    assert tuple(
        item.flow.local_id
        for item in result.flows
    ) == (
        "a_outer_bind",
        "b_outer_call",
    )


def test_lexical_scope_facts_are_incomplete_without_anchor_ownership():
    service, _, target = _lexical_scope_service(
        anchor_ownership=False,
    )

    result = service.lexical_scope_facts(target)

    assert result.scope_available is True
    assert result.materialization_complete is False
    assert result.complete is False


def test_lexical_scope_facts_expose_stale_family_fail_closed():
    service, _, target = _lexical_scope_service(
        family_state="stale",
    )

    result = service.lexical_scope_facts(target)

    assert result.scope_available is True
    assert result.metadata.family_state == "stale"
    assert result.complete is False
    assert result.flows


def test_lexical_scope_facts_never_enumerate_repo_wide_source_keys(
    monkeypatch,
):
    service, backend, target = _lexical_scope_service()
    monkeypatch.setattr(
        backend,
        "source_keys",
        lambda: (_ for _ in ()).throw(
            AssertionError("repo scan")
        ),
    )

    result = service.lexical_scope_facts(target)

    assert result.complete is True
    assert result.flows


def test_lexical_scope_facts_do_not_treat_plain_binding_as_scope():
    owner = "A17/2"
    source_key = "pkg/value.py"
    fingerprint = "f" * 64
    span = SourceSpan(1, 0, 1, 5)
    binding_ref = MaterializedOccurrenceRef(
        source_key,
        fingerprint,
        "value-binding",
    )
    module_ref = MaterializedOccurrenceRef(
        source_key,
        fingerprint,
        "module",
    )
    source = MaterializedLineageSourceFacts(
        manifest=SourceLineageManifest(
            source_key=source_key,
            source_fingerprint=fingerprint,
            semantic_version="1",
            status=LineageFamilyStatus.FRESH,
            anchor_count=2,
            flow_count=1,
            surface_count=0,
            semantic_anchor_bindings_materialized=True,
            anchor_ownership_materialized=True,
            flow_ownership_materialized=True,
        ),
        anchors=tuple(
            sorted(
                (
                    MaterializedAnchorFact(
                        "module",
                        module_ref,
                        "module",
                        span,
                    ),
                    MaterializedAnchorFact(
                        "value-binding",
                        binding_ref,
                        "binding",
                        span,
                        owner_local_id="module",
                    ),
                )
            )
        ),
        flows=(
            MaterializedFlowFact(
                "module-assignment",
                module_ref,
                binding_ref,
                LineageRelation.ASSIGNS,
                span,
                ResolutionKind.LEXICAL_EXACT,
                LineageConfidence.CONFIRMED,
                owner_local_id="module",
            ),
        ),
        semantic_anchors=(
            SemanticAnchorBinding(
                owner,
                "pkg.value::value",
                binding_ref,
            ),
        ),
    )
    sources = {source_key: source}
    owner_source_index, source_owner_index, anchor_complete = (
        build_lineage_query_indexes(sources)
    )
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            lineage_facts_state="fresh",
            lineage_facts_semantic_version="1",
            lineage_facts_by_source=sources,
            lineage_owner_source_index=owner_source_index,
            lineage_source_owner_index=source_owner_index,
            lineage_query_index_state="fresh",
            lineage_semantic_anchor_bindings_complete=(
                anchor_complete
            ),
        )
    )
    service = LineageQueryService(
        backend,
        IndexCatalog(
            modules={},
            artifacts={
                owner: "pkg.value::value",
            },
        ),
    )
    resolved = service.resolve_target(owner)
    assert resolved.target is not None

    result = service.lexical_scope_facts(
        resolved.target
    )

    assert result.roots == ()
    assert result.flows == ()
    assert result.nested_scopes == ()
    assert result.scope_available is False
    assert result.complete is False
def test_lexical_scope_facts_fail_closed_for_multiple_exact_roots():
    service, backend, target = _lexical_scope_service()
    source = backend.get_source("pkg/target.py")
    assert source is not None

    duplicate_ref = MaterializedOccurrenceRef(
        "pkg/target.py",
        "d" * 64,
        "outer-redefined",
    )
    duplicate_anchor = MaterializedAnchorFact(
        "outer-redefined",
        duplicate_ref,
        "function",
        SourceSpan(20, 0, 22, 1),
        owner_local_id="module",
    )
    duplicate_flow = MaterializedFlowFact(
        "z_redefined_return",
        duplicate_ref,
        MaterializedOccurrenceRef(
            "pkg/target.py",
            "d" * 64,
            "redefined-result",
        ),
        LineageRelation.RETURNS,
        SourceSpan(21, 1, 21, 10),
        ResolutionKind.LEXICAL_EXACT,
        LineageConfidence.CONFIRMED,
        owner_local_id="outer-redefined",
    )
    duplicate_binding = SemanticAnchorBinding(
        target.artifact_id,
        target.qualified_name,
        duplicate_ref,
    )

    replacement = replace(
        source,
        manifest=replace(
            source.manifest,
            anchor_count=source.manifest.anchor_count + 1,
            flow_count=source.manifest.flow_count + 1,
        ),
        anchors=tuple(
            sorted(
                (
                    *source.anchors,
                    duplicate_anchor,
                )
            )
        ),
        flows=tuple(
            sorted(
                (
                    *source.flows,
                    duplicate_flow,
                )
            )
        ),
        semantic_anchors=tuple(
            sorted(
                (
                    *source.semantic_anchors,
                    duplicate_binding,
                )
            )
        ),
    )
    backend._sources["pkg/target.py"] = replacement

    result = service.lexical_scope_facts(target)

    assert tuple(
        item.anchor.local_id
        for item in result.roots
    ) == (
        "outer",
        "outer-redefined",
    )
    assert result.scope_available is False
    assert result.root_ambiguous is True
    assert result.complete is False
    assert result.flows == ()
    assert result.nested_scopes == ()
