from types import SimpleNamespace

import pytest

from contextor.core.domain.lineage_facts import (
    LINEAGE_FACTS_SEMANTIC_VERSION,
    LineageFamilyStatus,
    MaterializedLineageSourceFacts,
    SourceLineageManifest,
)
from contextor.core.lineage_query import (
    CanonicalLineageBackend,
    LineageBackendMetadata,
    RepositoryStateLineageBackend,
)


def _slice(source_key: str) -> MaterializedLineageSourceFacts:
    return MaterializedLineageSourceFacts(
        manifest=SourceLineageManifest(
            source_key=source_key,
            source_fingerprint="f" * 64,
            semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
            status=LineageFamilyStatus.FRESH,
            anchor_count=0,
            flow_count=0,
            surface_count=0,
        )
    )


def _state():
    source_a = _slice("pkg/a.py")
    source_b = _slice("pkg/b.py")
    return (
        SimpleNamespace(
            revision=11,
            provenance="live",
            lineage_facts_state="fresh",
            lineage_facts_semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
            lineage_facts_by_source={
                "pkg/b.py": source_b,
                "pkg/a.py": source_a,
            },
        ),
        source_a,
        source_b,
    )


def test_repository_state_backend_exposes_canonical_metadata():
    state, _, _ = _state()
    backend = RepositoryStateLineageBackend(state)

    assert isinstance(backend, CanonicalLineageBackend)
    assert backend.metadata() == LineageBackendMetadata(
        revision=11,
        provenance="live",
        family_state="fresh",
        semantic_version=LINEAGE_FACTS_SEMANTIC_VERSION,
        source_count=2,
    )


def test_repository_state_backend_preserves_slice_identity_and_order():
    state, source_a, source_b = _state()
    backend = RepositoryStateLineageBackend(state)

    assert backend.source_keys() == ("pkg/a.py", "pkg/b.py")
    assert backend.get_source("pkg/a.py") is source_a
    assert backend.get_manifest("pkg/a.py") is source_a.manifest
    assert backend.get_source("pkg/missing.py") is None
    assert backend.get_manifest("pkg/missing.py") is None

    assert backend.iter_sources(
        ["pkg/b.py", "pkg/a.py", "pkg/a.py", "pkg/missing.py"]
    ) == (source_a, source_b)


def test_repository_state_backend_defaults_to_not_materialized():
    backend = RepositoryStateLineageBackend(SimpleNamespace())

    assert backend.metadata() == LineageBackendMetadata(
        revision=None,
        provenance="snapshot",
        family_state="not_materialized",
        semantic_version=None,
        source_count=0,
    )
    assert backend.source_keys() == ()
    assert backend.iter_sources() == ()


def test_repository_state_backend_rejects_invalid_storage_shape():
    with pytest.raises(TypeError, match="must be a mapping"):
        RepositoryStateLineageBackend(
            SimpleNamespace(lineage_facts_by_source=[])
        )

    with pytest.raises(TypeError, match="non-empty strings"):
        RepositoryStateLineageBackend(
            SimpleNamespace(lineage_facts_by_source={1: _slice("pkg/a.py")})
        )


def test_repository_state_backend_fails_closed_on_invalid_slice():
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            lineage_facts_by_source={"pkg/a.py": object()}
        )
    )

    with pytest.raises(TypeError, match="invalid type"):
        backend.get_source("pkg/a.py")


def test_repository_state_backend_rejects_invalid_family_state():
    backend = RepositoryStateLineageBackend(
        SimpleNamespace(
            lineage_facts_state="pretend_fresh",
            lineage_facts_by_source={},
        )
    )

    with pytest.raises(ValueError, match="family state is invalid"):
        backend.metadata()


def test_repository_state_backend_rejects_string_as_source_collection():
    state, _, _ = _state()
    backend = RepositoryStateLineageBackend(state)

    with pytest.raises(TypeError, match="iterable of source-key strings"):
        backend.iter_sources("pkg/a.py")
