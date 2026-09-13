from types import SimpleNamespace

import pytest

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
