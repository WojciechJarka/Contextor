from types import SimpleNamespace

import pytest

from contextor.core.domain.lineage_facts import (
    LineageFamilyStatus,
    MaterializedAnchorFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    SemanticAnchorBinding,
    SourceLineageManifest,
    SourceSpan,
)
from contextor.core.lineage_query.backend import (
    RepositoryStateLineageBackend,
)
from contextor.core.lineage_query.index import (
    build_lineage_query_indexes,
)
from contextor.core.lineage_query.live_query import (
    build_live_lineage_target_catalog,
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
