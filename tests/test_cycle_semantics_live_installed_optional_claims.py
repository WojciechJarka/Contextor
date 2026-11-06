"""P1D3G3: installed optional SCC receipt identity under LIVE lock."""

import copy

from dataclasses import replace

import pytest

from contextor.core.api.facade import ContextorFacade
from contextor.core.cycle_semantics.warning_eligibility import (
    _verified_model_pass_cycle_paths,
)
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _owner,
)
from tests.test_cycle_semantics_optional_child_full_preview import (
    _repo,
)
from tests.test_original_worker_full_receipt_optin import (
    _persisted,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _full(root, *, publication=True):
    errors, result = ContextorFacade.analyze_project(
        str(root),
        cycle_source_preparation_preview=True,
        cycle_source_selection="OPTIONAL_NAMED_CHILDREN",
        cycle_optional_source_publication_opt_in=publication,
    )
    assert isinstance(errors, list)
    assert result is not None
    return result


def _fixture(tmp_path, *, publication=True):
    root = _repo(tmp_path)
    _full(root, publication=publication)
    state, metadata = _persisted(root)
    return root, state, metadata


def _expected(state, metadata):
    receipt = state.cycle_optional_source_publication
    manifest = receipt.preparation.manifest

    return {
        "expected_revision": metadata.revision,
        "expected_state_id": metadata.state_id,
        "expected_repo_id": metadata.repo_id,
        "expected_root_path": metadata.root_path,
        "expected_graph_sha256": manifest.graph_sha256,
        "expected_source_manifest_sha256": (
            manifest.source_manifest_sha256
        ),
        "expected_claims_sha256": receipt.claims_sha256,
    }


def _check(client, expected, **overrides):
    return client.verify_installed_optional_scc_generation(
        **{**expected, **overrides},
    )


def test_t01_installed_optional_receipt_matches(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    with _owner(state, metadata) as (server, client):
        response = _check(client, expected)

        assert response["status"] == "ok"
        assert response["binding_state"] == (
            "INSTALLED_OPTIONAL_SCC_CLAIMS_MATCH_EXPECTED_GENERATION"
        )
        assert response["revision"] == metadata.revision
        assert response["state_id"] == metadata.state_id
        assert response["graph_sha256"] == (
            expected["expected_graph_sha256"]
        )
        assert response["source_manifest_sha256"] == (
            expected["expected_source_manifest_sha256"]
        )
        assert response["claims_sha256"] == (
            expected["expected_claims_sha256"]
        )
        assert response["activity_epoch"] == (
            server._activity_epoch
        )
        assert response["service_instance_id"] == (
            server.endpoint.service_instance_id
        )
        assert response["process_start_identity"] == (
            server.endpoint.process_start_identity
        )

        assert set(response) == {
            "status",
            "binding_state",
            "revision",
            "state_id",
            "repo_id",
            "root_path",
            "service_instance_id",
            "process_start_identity",
            "activity_epoch",
            "graph_sha256",
            "source_manifest_sha256",
            "claims_sha256",
            "authority",
        }

        assert response == _check(client, expected)

    assert _verified_model_pass_cycle_paths(
        state,
        expected_revision=metadata.revision,
        expected_state_id=metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=metadata.root_path,
    ) == frozenset()


def test_t02_committed_receipt_without_installation_fails(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    with _owner(None, metadata) as (_, client):
        response = _check(client, expected)
        assert response["status"] == "unavailable"


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_revision", 999999),
        ("expected_state_id", "foreign-state"),
        ("expected_repo_id", "foreign-repo"),
        ("expected_root_path", "foreign-root"),
        ("expected_graph_sha256", "0" * 64),
        ("expected_source_manifest_sha256", "0" * 64),
        ("expected_claims_sha256", "0" * 64),
    ],
)
def test_t03_expected_identity_mismatch_fails(
    tmp_path, isolated_dirs, field, value,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    with _owner(state, metadata) as (_, client):
        response = _check(
            client,
            expected,
            **{field: value},
        )
        assert response["status"] == "unavailable"


@pytest.mark.parametrize(
    "field",
    [
        "expected_service_instance_id",
        "expected_process_start_identity",
    ],
)
def test_t04_foreign_owner_identity_fails(
    tmp_path, isolated_dirs, field,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    with _owner(state, metadata) as (server, _):
        request = {
            "operation": "verify_installed_optional_scc_generation",
            **expected,
            "expected_service_instance_id": (
                server.endpoint.service_instance_id
            ),
            "expected_process_start_identity": (
                server.endpoint.process_start_identity
            ),
        }
        request[field] = "foreign"

        response = server._dispatch(request)
        assert response["status"] == "unavailable"


@pytest.mark.parametrize(
    "mutation",
    ["missing", "claims", "manifest", "classification", "version"],
)
def test_t05_invalid_installed_receipt_fails(
    tmp_path, isolated_dirs, mutation,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    receipt = state.cycle_optional_source_publication

    if mutation == "missing":
        state.cycle_optional_source_publication = None

    elif mutation == "claims":
        state.cycle_optional_source_publication = replace(
            receipt,
            claims_sha256="0" * 64,
        )

    elif mutation == "manifest":
        invalid_manifest = replace(
            receipt.preparation.manifest,
            source_manifest_sha256="0" * 64,
        )
        state.cycle_optional_source_publication = replace(
            receipt,
            preparation=replace(
                receipt.preparation,
                manifest=invalid_manifest,
            ),
        )

    elif mutation == "classification":
        components = list(
            receipt.preparation.component_preparations
        )
        components[0] = replace(
            components[0],
            model_classification="FORGED",
        )
        state.cycle_optional_source_publication = replace(
            receipt,
            preparation=replace(
                receipt.preparation,
                component_preparations=tuple(components),
            ),
        )

    else:
        state.cycle_optional_source_publication = replace(
            receipt,
            version="unsupported",
        )

    with _owner(state, metadata) as (_, client):
        response = _check(client, expected)
        assert response["status"] == "unavailable"


@pytest.mark.parametrize(
    "mutation",
    ["semantics", "cycles", "resync"],
)
def test_t06_stale_or_resync_fails(
    tmp_path, isolated_dirs, mutation,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    if mutation == "semantics":
        state.cycle_semantics_state = "stale"
    elif mutation == "cycles":
        state.cycles_state = "stale"
    else:
        state.resync_required = True

    with _owner(state, metadata) as (_, client):
        response = _check(client, expected)
        assert response["status"] == "unavailable"


@pytest.mark.parametrize(
    "extra",
    ["state", "receipt", "source_bytes", "preparation"],
)
def test_t07_extra_payload_rejected(
    tmp_path, isolated_dirs, extra,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    with _owner(state, metadata) as (server, client):
        request = {
            **expected,
            "expected_service_instance_id": (
                server.endpoint.service_instance_id
            ),
            "expected_process_start_identity": (
                server.endpoint.process_start_identity
            ),
            extra: "not accepted",
        }

        response = client.request(
            "verify_installed_optional_scc_generation",
            **request,
        )
        assert response["status"] == "unavailable"
        assert response["reason"] == (
            "INVALID_GENERATION_CHECK_PAYLOAD"
        )


def test_t08_recovery_not_ready_rejected(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    with _owner(state, metadata) as (server, client):
        server._pending_recovery_certificate = {
            "certificate_id": "isolated",
        }

        try:
            response = _check(client, expected)
            assert response["status"] == "unavailable"
            assert response["reason"] == "LIVE_OWNER_NOT_READY"
        finally:
            server._pending_recovery_certificate = None


def test_t09_newer_installation_invalidates_old_check(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path)
    old_expected = _expected(state, metadata)

    with _owner(state, metadata) as (server, client):
        assert _check(client, old_expected)["status"] == "ok"

        _full(root, publication=True)
        newer, newer_metadata = _persisted(root)

        assert newer_metadata.revision > metadata.revision

        published = server._execute_publish({
            "state": newer,
            "origin": "isolated_test",
        })
        assert published["status"] == "ok"

        assert _check(client, old_expected)["status"] == "unavailable"
        assert _check(
            client,
            _expected(newer, newer_metadata),
        )["status"] == "ok"


def test_t10_read_only_and_no_diagnostic_mutation(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path)
    expected = _expected(state, metadata)

    original_edges = copy.deepcopy(
        state.dependency_graph.hard_edges
    )
    original_cycles = copy.deepcopy(state.cycles)
    original_scc = copy.deepcopy(
        state.cycle_semantics.import_sites.topology.cyclic_components
    )

    with _owner(state, metadata) as (server, client):
        original_events = copy.deepcopy(server._events)

        assert _check(client, expected)["status"] == "ok"
        assert _check(client, expected)["status"] == "ok"

        assert server._events == original_events

    assert state.dependency_graph.hard_edges == original_edges
    assert state.cycles == original_cycles
    assert (
        state.cycle_semantics.import_sites.topology.cyclic_components
        == original_scc
    )
