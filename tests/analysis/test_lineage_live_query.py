from dataclasses import replace
from types import SimpleNamespace

import pytest

from contextor.core.domain.lineage_facts import (
    ExtractedSymbolicKind,
    LineageConfidence,
    LineageFamilyStatus,
    LineageRelation,
    MaterializedAnchorFact,
    MaterializedFlowFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    ResolutionKind,
    SemanticEndpoint,
    SemanticAnchorBinding,
    SemanticEndpointOrigin,
    SemanticEndpointRole,
    SourceLineageManifest,
    SourceSpan,
    build_module_global_slot,
)
from contextor.core.lineage_query.backend import (
    RepositoryStateLineageBackend,
)
from contextor.core.lineage_query.index import (
    build_lineage_query_indexes,
)
from contextor.core.lineage_query.live_query import (
    LiveSymbolLineageQueryResult,
    build_selected_lineage_owner_names,
    build_live_lineage_target_catalog,
    query_live_symbol_lineage,
)
from contextor.core.lineage_query.service import (
    LineageQueryService,
)


def _source(
    source_key,
    fingerprint,
    identities,
):
    span = SourceSpan(1, 0, 1, 10)
    anchors = []
    bindings = []

    for index, (owner_id, qualified_name) in enumerate(
        identities
    ):
        local_id = f"definition-{index}"
        reference = MaterializedOccurrenceRef(
            source_key,
            fingerprint,
            local_id,
        )
        anchors.append(
            MaterializedAnchorFact(
                local_id,
                reference,
                "function",
                span,
            )
        )
        bindings.append(
            SemanticAnchorBinding(
                owner_id,
                qualified_name,
                reference,
            )
        )

    return MaterializedLineageSourceFacts(
        manifest=SourceLineageManifest(
            source_key=source_key,
            source_fingerprint=fingerprint,
            semantic_version="1",
            status=LineageFamilyStatus.FRESH,
            anchor_count=len(anchors),
            flow_count=0,
            surface_count=0,
            semantic_anchor_bindings_materialized=True,
            anchor_ownership_materialized=True,
            flow_ownership_materialized=True,
        ),
        anchors=tuple(sorted(anchors)),
        flows=(),
        surfaces=(),
        semantic_anchors=tuple(sorted(bindings)),
    )


def _fixture():
    provider = _source(
        "pkg/mod.py",
        "a" * 64,
        (
            ("A17/2", "pkg.mod::handler"),
            ("A18/1", "pkg.mod::other"),
        ),
    )
    unrelated = _source(
        "pkg/other.py",
        "b" * 64,
        (
            ("A99/1", "pkg.other::thing"),
        ),
    )
    sources = {
        "pkg/mod.py": provider,
        "pkg/other.py": unrelated,
    }
    (
        owner_source_index,
        source_owner_index,
        anchor_complete,
    ) = build_lineage_query_indexes(sources)

    state = SimpleNamespace(
        revision=7,
        provenance="live",
        modules={
            "pkg.mod": SimpleNamespace(
                path="pkg/mod.py",
            ),
            "pkg.other": SimpleNamespace(
                path="pkg/other.py",
            ),
        },
        lineage_facts_state="fresh",
        lineage_facts_semantic_version="1",
        lineage_facts_by_source=sources,
        lineage_owner_source_index=(
            owner_source_index
        ),
        lineage_source_owner_index=(
            source_owner_index
        ),
        lineage_query_index_state="fresh",
        lineage_semantic_anchor_bindings_complete=(
            anchor_complete
        ),
    )
    return (
        state,
        RepositoryStateLineageBackend(state),
    )


def test_live_target_catalog_resolves_artifact_id_only_through_owner_index(
    monkeypatch,
):
    state, backend = _fixture()

    monkeypatch.setattr(
        backend,
        "source_keys",
        lambda: (_ for _ in ()).throw(
            AssertionError("repo-wide lineage scan")
        ),
    )

    original_iter = backend.iter_sources
    observed = {}

    def iter_sources(source_keys=None):
        observed["source_keys"] = source_keys
        return original_iter(source_keys)

    monkeypatch.setattr(
        backend,
        "iter_sources",
        iter_sources,
    )

    catalog = build_live_lineage_target_catalog(
        state,
        backend,
        "a17/2",
    )

    assert catalog.artifacts == {
        "A17/2": "pkg.mod::handler",
    }
    assert observed["source_keys"] == (
        "pkg/mod.py",
    )


def test_live_target_catalog_resolves_qualified_name_from_one_module_slice_only(
    monkeypatch,
):
    state, backend = _fixture()

    monkeypatch.setattr(
        backend,
        "source_keys",
        lambda: (_ for _ in ()).throw(
            AssertionError("repo-wide lineage scan")
        ),
    )
    monkeypatch.setattr(
        backend,
        "iter_sources",
        lambda *_args, **_kwargs: (
            (_ for _ in ()).throw(
                AssertionError(
                    "qualified lookup iterated lineage"
                )
            )
        ),
    )

    original_get = backend.get_source
    observed = []

    def get_source(source_key):
        observed.append(source_key)
        return original_get(source_key)

    monkeypatch.setattr(
        backend,
        "get_source",
        get_source,
    )

    catalog = build_live_lineage_target_catalog(
        state,
        backend,
        "pkg.mod::handler",
    )

    assert catalog.artifacts == {
        "A17/2": "pkg.mod::handler",
    }
    assert observed == ["pkg/mod.py"]


def test_live_target_catalog_preserves_duplicate_exact_identity_for_service_ambiguity():
    state, backend = _fixture()
    source = _source(
        "pkg/mod.py",
        "c" * 64,
        (
            ("A17/2", "pkg.mod::handler"),
            ("A18/1", "pkg.mod::handler"),
        ),
    )
    state.lineage_facts_by_source[
        "pkg/mod.py"
    ] = source
    (
        owner_source_index,
        source_owner_index,
        anchor_complete,
    ) = build_lineage_query_indexes(
        state.lineage_facts_by_source
    )
    state.lineage_owner_source_index = (
        owner_source_index
    )
    state.lineage_source_owner_index = (
        source_owner_index
    )
    state.lineage_semantic_anchor_bindings_complete = (
        anchor_complete
    )

    catalog = build_live_lineage_target_catalog(
        state,
        backend,
        "pkg.mod::handler",
    )

    assert catalog.artifacts == {
        "A17/2": "pkg.mod::handler",
        "A18/1": "pkg.mod::handler",
    }


@pytest.mark.parametrize(
    "query",
    (
        "",
        "handler",
        "pkg.mod",
        "pkg.mod::",
        "::handler",
        "pkg.mod::handler::extra",
        "pkg.missing::handler",
    ),
)
def test_live_target_catalog_invalid_or_missing_exact_query_returns_empty_catalog(
    query,
):
    state, backend = _fixture()

    catalog = build_live_lineage_target_catalog(
        state,
        backend,
        query,
    )

    assert catalog.artifacts == {}


def test_live_target_catalog_fails_closed_when_identity_capability_is_not_fresh():
    state, backend = _fixture()
    state.lineage_query_index_state = "stale"

    with pytest.raises(
        ValueError,
        match=(
            "Canonical lineage target identity "
            "catalog is unavailable or stale."
        ),
    ):
        build_live_lineage_target_catalog(
            state,
            backend,
            "pkg.mod::handler",
        )


def test_live_target_catalog_rejects_inconsistent_owner_identity():
    state, backend = _fixture()

    conflicting = _source(
        "pkg/duplicate.py",
        "d" * 64,
        (
            ("A17/2", "pkg.other::handler"),
        ),
    )
    state.lineage_facts_by_source[
        "pkg/duplicate.py"
    ] = conflicting
    state.lineage_owner_source_index[
        "A17/2"
    ] = (
        "pkg/duplicate.py",
        "pkg/mod.py",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Canonical lineage owner identity "
            "is inconsistent."
        ),
    ):
        build_live_lineage_target_catalog(
            state,
            backend,
            "A17/2",
        )


def test_live_symbol_lineage_query_resolves_once_and_selects_canonical_sections(
    monkeypatch,
):
    state, _backend = _fixture()

    original_facts = (
        LineageQueryService.symbol_lineage_facts
    )
    original_select = (
        LineageQueryService.select_symbol_lineage_sections
    )
    calls = {
        "facts": 0,
        "select": 0,
    }

    def symbol_lineage_facts(
        service,
        target,
    ):
        calls["facts"] += 1
        return original_facts(
            service,
            target,
        )

    def select_symbol_lineage_sections(
        service,
        facts,
        sections,
    ):
        calls["select"] += 1
        return original_select(
            service,
            facts,
            sections,
        )

    monkeypatch.setattr(
        LineageQueryService,
        "symbol_lineage_facts",
        symbol_lineage_facts,
    )
    monkeypatch.setattr(
        LineageQueryService,
        "select_symbol_lineage_sections",
        select_symbol_lineage_sections,
    )
    monkeypatch.setattr(
        LineageQueryService,
        "traverse_lexical_scope",
        lambda *_args, **_kwargs: (
            (_ for _ in ()).throw(
                AssertionError(
                    "symbol lineage query must not traverse"
                )
            )
        ),
    )

    result = query_live_symbol_lineage(
        state,
        "a17/2",
        (
            "state",
            "connections",
            "interface",
        ),
    )

    assert isinstance(
        result,
        LiveSymbolLineageQueryResult,
    )
    assert result.resolution.status == "resolved"
    assert result.resolution.target is not None
    assert (
        result.resolution.target.artifact_id
        == "A17/2"
    )
    assert result.selected is not None
    assert result.selected.selected_sections == (
        "interface",
        "connections",
        "state",
    )
    assert result.selected.target == (
        result.resolution.target
    )
    assert calls == {
        "facts": 1,
        "select": 1,
    }


def test_live_symbol_lineage_query_resolves_exact_qualified_identity():
    state, _backend = _fixture()

    result = query_live_symbol_lineage(
        state,
        "pkg.mod::handler",
        ("connections",),
    )

    assert result.resolution.status == "resolved"
    assert result.resolution.target is not None
    assert (
        result.resolution.target.resolution
        == "exact_identity"
    )
    assert result.selected is not None
    assert result.selected.selected_sections == (
        "connections",
    )


@pytest.mark.parametrize(
    ("query", "expected_status"),
    (
        ("", "invalid"),
        ("handler", "invalid"),
        ("A404/1", "not_found"),
        ("pkg.missing::handler", "not_found"),
    ),
)
def test_live_symbol_lineage_query_unresolved_targets_never_build_facts(
    monkeypatch,
    query,
    expected_status,
):
    state, _backend = _fixture()

    monkeypatch.setattr(
        LineageQueryService,
        "symbol_lineage_facts",
        lambda *_args, **_kwargs: (
            (_ for _ in ()).throw(
                AssertionError(
                    "unresolved target built facts"
                )
            )
        ),
    )

    result = query_live_symbol_lineage(
        state,
        query,
        ("interface",),
    )

    assert (
        result.resolution.status
        == expected_status
    )
    assert result.selected is None


def test_live_symbol_lineage_query_preserves_ambiguity_without_selection(
    monkeypatch,
):
    state, _backend = _fixture()
    source = _source(
        "pkg/mod.py",
        "c" * 64,
        (
            ("A17/2", "pkg.mod::handler"),
            ("A18/1", "pkg.mod::handler"),
        ),
    )
    state.lineage_facts_by_source[
        "pkg/mod.py"
    ] = source
    (
        owner_source_index,
        source_owner_index,
        anchor_complete,
    ) = build_lineage_query_indexes(
        state.lineage_facts_by_source
    )
    state.lineage_owner_source_index = (
        owner_source_index
    )
    state.lineage_source_owner_index = (
        source_owner_index
    )
    state.lineage_semantic_anchor_bindings_complete = (
        anchor_complete
    )

    monkeypatch.setattr(
        LineageQueryService,
        "symbol_lineage_facts",
        lambda *_args, **_kwargs: (
            (_ for _ in ()).throw(
                AssertionError(
                    "ambiguous target built facts"
                )
            )
        ),
    )

    result = query_live_symbol_lineage(
        state,
        "pkg.mod::handler",
        ("interface",),
    )

    assert result.resolution.status == "ambiguous"
    assert result.selected is None
    assert tuple(
        candidate.artifact_id
        for candidate
        in result.resolution.candidates
    ) == (
        "A17/2",
        "A18/1",
    )


def test_live_symbol_lineage_query_reports_stale_capability_as_unavailable():
    state, _backend = _fixture()
    state.lineage_query_index_state = "stale"

    result = query_live_symbol_lineage(
        state,
        "pkg.mod::handler",
        ("interface",),
    )

    assert result.resolution.status == (
        "unavailable"
    )
    assert result.resolution.target is None
    assert result.selected is None
    assert result.unavailable_reason == (
        "Canonical lineage target identity "
        "catalog is unavailable or stale."
    )


def test_live_symbol_lineage_query_does_not_hide_canonical_identity_corruption():
    state, _backend = _fixture()

    conflicting = _source(
        "pkg/duplicate.py",
        "d" * 64,
        (
            ("A17/2", "pkg.other::handler"),
        ),
    )
    state.lineage_facts_by_source[
        "pkg/duplicate.py"
    ] = conflicting
    state.lineage_owner_source_index[
        "A17/2"
    ] = (
        "pkg/duplicate.py",
        "pkg/mod.py",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Canonical lineage owner identity "
            "is inconsistent."
        ),
    ):
        query_live_symbol_lineage(
            state,
            "A17/2",
            ("interface",),
        )


def test_live_symbol_lineage_query_validates_section_contract_before_resolution():
    state, _backend = _fixture()

    with pytest.raises(
        TypeError,
        match=(
            "sections must be a tuple "
            "of section names."
        ),
    ):
        query_live_symbol_lineage(
            state,
            "A404/1",
            ["interface"],
        )

    with pytest.raises(
        ValueError,
        match=(
            "sections must not contain duplicates."
        ),
    ):
        query_live_symbol_lineage(
            state,
            "A404/1",
            ("state", "state"),
        )

    with pytest.raises(
        ValueError,
        match=(
            "Unknown symbol lineage sections: mystery"
        ),
    ):
        query_live_symbol_lineage(
            state,
            "A404/1",
            ("mystery",),
        )


def test_live_symbol_lineage_query_allows_empty_core_selection():
    state, _backend = _fixture()

    result = query_live_symbol_lineage(
        state,
        "A17/2",
        (),
    )

    assert result.resolution.status == "resolved"
    assert result.selected is not None
    assert result.selected.selected_sections == ()
    assert result.selected.complete is True


def _owner_name_projection_fixture():
    source_key = "pkg/mod.py"
    fingerprint = "e" * 64
    span = SourceSpan(1, 0, 1, 10)
    target_ref = MaterializedOccurrenceRef(
        source_key, fingerprint, "definition-0"
    )
    local_ref = MaterializedOccurrenceRef(
        source_key, fingerprint, "local"
    )
    target_anchor = MaterializedAnchorFact(
        "definition-0", target_ref, "function", span
    )
    target_binding = SemanticAnchorBinding(
        "A17/2", "pkg.mod::handler", target_ref
    )
    state_flow = MaterializedFlowFact(
        "state-read",
        SemanticEndpoint(
            "17/2", build_module_global_slot("17/2", "CACHE")
        ),
        local_ref,
        LineageRelation.READS_STATE,
        span,
        ResolutionKind.LEXICAL_EXACT,
        LineageConfidence.CONFIRMED,
        owner_local_id="definition-0",
    )
    call_flow = MaterializedFlowFact(
        "call-other",
        local_ref,
        SemanticEndpoint("A18/1"),
        LineageRelation.CALL_RESULT,
        span,
        ResolutionKind.CALL_EXACT,
        LineageConfidence.CONFIRMED,
        owner_local_id="definition-0",
    )
    unselected_flow = MaterializedFlowFact(
        "callback-hidden",
        local_ref,
        SemanticEndpoint("A99/1"),
        LineageRelation.CALLBACK_INVOKES,
        span,
        ResolutionKind.CALL_EXACT,
        LineageConfidence.CONFIRMED,
        owner_local_id="definition-0",
    )
    origins = (
        SemanticEndpointOrigin(
            source_key,
            fingerprint,
            "state-read",
            SemanticEndpointRole.FLOW_SOURCE,
            ExtractedSymbolicKind.STATE,
            "pkg.mod",
            "CACHE",
        ),
        SemanticEndpointOrigin(
            source_key,
            fingerprint,
            "call-other",
            SemanticEndpointRole.FLOW_TARGET,
            ExtractedSymbolicKind.CALLEE,
            "pkg.mod",
            "other",
        ),
        SemanticEndpointOrigin(
            source_key,
            fingerprint,
            "callback-hidden",
            SemanticEndpointRole.FLOW_TARGET,
            ExtractedSymbolicKind.CALLEE,
            "pkg.callbacks",
            "hidden",
        ),
    )
    source = MaterializedLineageSourceFacts(
        manifest=SourceLineageManifest(
            source_key=source_key,
            source_fingerprint=fingerprint,
            semantic_version="1",
            status=LineageFamilyStatus.FRESH,
            anchor_count=1,
            flow_count=3,
            surface_count=0,
            semantic_anchor_bindings_materialized=True,
            anchor_ownership_materialized=True,
            flow_ownership_materialized=True,
        ),
        anchors=(target_anchor,),
        flows=tuple(sorted((
            state_flow, call_flow, unselected_flow,
        ))),
        surfaces=(),
        semantic_endpoint_origins=tuple(sorted(origins)),
        semantic_anchors=(target_binding,),
    )
    sources = {source_key: source}
    (
        owner_source_index,
        source_owner_index,
        anchor_complete,
    ) = build_lineage_query_indexes(sources)
    state = SimpleNamespace(
        revision=11,
        provenance="live",
        modules={"pkg.mod": SimpleNamespace(path=source_key)},
        lineage_facts_state="fresh",
        lineage_facts_semantic_version="1",
        lineage_facts_by_source=sources,
        lineage_owner_source_index=owner_source_index,
        lineage_source_owner_index=source_owner_index,
        lineage_query_index_state="fresh",
        lineage_semantic_anchor_bindings_complete=anchor_complete,
    )
    backend = RepositoryStateLineageBackend(state)
    result = query_live_symbol_lineage(
        state, "A17/2", ("calls_interfaces", "state")
    )
    assert result.resolution.status == "resolved"
    assert result.selected is not None
    return state, backend, result.selected


def test_selected_owner_names_use_canonical_origins_for_module_and_artifact_owners_only(
    monkeypatch,
):
    _state, backend, selected = _owner_name_projection_fixture()
    monkeypatch.setattr(
        backend,
        "source_keys",
        lambda: (_ for _ in ()).throw(
            AssertionError("owner-name projection scanned lineage")
        ),
    )
    monkeypatch.setattr(
        backend,
        "iter_sources",
        lambda *_args, **_kwargs: (
            (_ for _ in ()).throw(
                AssertionError("owner-name projection iterated lineage")
            )
        ),
    )
    original_get = backend.get_source
    observed = []

    def get_source(source_key):
        observed.append(source_key)
        return original_get(source_key)

    monkeypatch.setattr(backend, "get_source", get_source)
    owner_names = build_selected_lineage_owner_names(backend, selected)

    assert owner_names == {
        "17/2": "pkg.mod",
        "A18/1": "pkg.mod::other",
    }
    assert "A99/1" not in owner_names
    assert observed == ["pkg/mod.py"]


def test_selected_owner_names_fail_closed_when_selected_semantic_origin_is_missing():
    state, _backend, selected = _owner_name_projection_fixture()
    source = state.lineage_facts_by_source["pkg/mod.py"]
    state.lineage_facts_by_source["pkg/mod.py"] = replace(
        source,
        semantic_endpoint_origins=tuple(
            origin
            for origin in source.semantic_endpoint_origins
            if origin.fact_local_id != "state-read"
        ),
    )
    backend = RepositoryStateLineageBackend(state)

    with pytest.raises(
        ValueError,
        match="Canonical semantic owner name origin is unavailable.",
    ):
        build_selected_lineage_owner_names(backend, selected)


def test_selected_owner_names_reject_conflicting_canonical_name_for_same_owner():
    state, _backend, _selected = _owner_name_projection_fixture()
    source = state.lineage_facts_by_source["pkg/mod.py"]
    span = SourceSpan(2, 0, 2, 10)
    local_ref = MaterializedOccurrenceRef(
        "pkg/mod.py", "e" * 64, "local-conflict"
    )
    conflict_flow = MaterializedFlowFact(
        "call-conflict",
        local_ref,
        SemanticEndpoint("A18/1"),
        LineageRelation.CALL_RESULT,
        span,
        ResolutionKind.CALL_EXACT,
        LineageConfidence.CONFIRMED,
        owner_local_id="definition-0",
    )
    conflict_origin = SemanticEndpointOrigin(
        "pkg/mod.py",
        "e" * 64,
        "call-conflict",
        SemanticEndpointRole.FLOW_TARGET,
        ExtractedSymbolicKind.CALLEE,
        "pkg.other",
        "other",
    )
    state.lineage_facts_by_source["pkg/mod.py"] = replace(
        source,
        manifest=replace(source.manifest, flow_count=4),
        flows=tuple(sorted((*source.flows, conflict_flow))),
        semantic_endpoint_origins=tuple(
            sorted((*source.semantic_endpoint_origins, conflict_origin))
        ),
    )
    (
        owner_source_index,
        source_owner_index,
        anchor_complete,
    ) = build_lineage_query_indexes(state.lineage_facts_by_source)
    state.lineage_owner_source_index = owner_source_index
    state.lineage_source_owner_index = source_owner_index
    state.lineage_semantic_anchor_bindings_complete = anchor_complete
    result = query_live_symbol_lineage(
        state, "A17/2", ("calls_interfaces",)
    )
    assert result.selected is not None
    backend = RepositoryStateLineageBackend(state)

    with pytest.raises(
        ValueError,
        match="Canonical semantic owner identity is inconsistent.",
    ):
        build_selected_lineage_owner_names(backend, result.selected)
