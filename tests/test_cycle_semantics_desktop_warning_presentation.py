"""WARN-4G: Desktop only hides exactly installed MODEL_PASS cycle errors."""

from __future__ import annotations

from types import SimpleNamespace
from dataclasses import replace

import pytest

from contextor.core.domain.validation import ValidationError
from contextor.ui.cycle_warning_presentation import (
    _accepted_paths,
    filter_installed_desktop_cycle_errors,
)
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture,
    _owner,
)
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_UNKNOWN,
    PASS_AND_HAZARD,
    TWO_PASS,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _analysis_result(metadata, server):
    return SimpleNamespace(
        live_publish_status="success",
        live_publish_revision=metadata.revision,
        live_publish_expected_revision=metadata.revision,
        live_publish_expected_state_id=metadata.state_id,
        live_publish_service_instance_id=(
            server.endpoint.service_instance_id
        ),
        live_publish_process_start_identity=(
            server.endpoint.process_start_identity
        ),
    )


def _cycle(path):
    return ValidationError(
        kind="ArchitectureCycle",
        message=(
            "Cyclic dependency detected in architecture: "
            + " -> ".join(path)
        ),
        nodes=list(path),
    )


def _other():
    return ValidationError(
        kind="ForbiddenDependency",
        message="Unrelated architecture error",
        nodes=["a", "b"],
    )


def _connect(monkeypatch, client):
    monkeypatch.setattr(
        "contextor.core.live_state.connect",
        lambda _root: client,
    )


@pytest.mark.parametrize("sources,expected_remaining", [
    (TWO_PASS, 0),
    (PASS_AND_UNKNOWN, 1),
    (PASS_AND_HAZARD, 1),
])
def test_t01_t03_real_owner_acceptance_filters_only_pass(
    tmp_path, isolated_dirs, monkeypatch,
    sources, expected_remaining,
):
    root, state, metadata = _fixture(tmp_path, sources)

    with _owner(state, metadata) as (server, client):
        _connect(monkeypatch, client)
        errors = [_cycle(path) for path in state.cycles]
        other = _other()
        errors.append(other)

        result = filter_installed_desktop_cycle_errors(
            errors,
            _analysis_result(metadata, server),
            str(root),
        )

        remaining_cycles = [
            item for item in result
            if item.kind == "ArchitectureCycle"
        ]

        assert len(remaining_cycles) == expected_remaining
        assert result[-1] is other
        assert len(errors) == 3
        assert len(state.cycles) == 2


def test_t04_noncanonical_message_is_not_removed(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _connect(monkeypatch, client)
        invalid = _cycle(state.cycles[0])
        invalid.message = "Unrelated warning with same nodes"

        result = filter_installed_desktop_cycle_errors(
            [invalid],
            _analysis_result(metadata, server),
            str(root),
        )

        assert result == [invalid]


def test_t05_unpublished_full_preserves_all_errors(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _connect(monkeypatch, client)
        errors = [_cycle(path) for path in state.cycles]
        publication = _analysis_result(metadata, server)
        publication.live_publish_status = "pending_verification"

        assert filter_installed_desktop_cycle_errors(
            errors, publication, str(root)
        ) is errors


def test_t06_wrong_revision_preserves_all_errors(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _connect(monkeypatch, client)
        errors = [_cycle(path) for path in state.cycles]
        publication = _analysis_result(metadata, server)
        publication.live_publish_revision += 1

        assert filter_installed_desktop_cycle_errors(
            errors, publication, str(root)
        ) is errors


def test_t07_wrong_service_preserves_all_errors(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _connect(monkeypatch, client)
        errors = [_cycle(path) for path in state.cycles]
        publication = _analysis_result(metadata, server)
        publication.live_publish_service_instance_id = "foreign"

        assert filter_installed_desktop_cycle_errors(
            errors, publication, str(root)
        ) is errors


def test_t08_invalid_partition_never_suppresses(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        report = client.get_installed_cycle_warning_projection()
        report["active_warning_paths"] = report["model_pass_paths"]

        assert _accepted_paths(
            _analysis_result(metadata, server),
            str(root),
            report,
        ) is None


def test_t09_wrong_repository_never_suppresses(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        report = client.get_installed_cycle_warning_projection()
        report["repo_id"] = "foreign-repository"

        assert _accepted_paths(
            _analysis_result(metadata, server),
            str(root),
            report,
        ) is None


def test_t10_missing_owner_preserves_all_errors(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    monkeypatch.setattr(
        "contextor.core.live_state.connect",
        lambda _root: None,
    )

    errors = [_cycle(path) for path in state.cycles]

    assert filter_installed_desktop_cycle_errors(
        errors,
        SimpleNamespace(live_publish_status="success"),
        str(root),
    ) is errors


def test_t11_query_failure_preserves_all_errors(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    class FailingClient:
        def request(self, *_args, **_kwargs):
            raise RuntimeError("unavailable")

    _connect(monkeypatch, FailingClient())
    errors = [_cycle(path) for path in state.cycles]

    with _owner(state, metadata) as (server, client):
        assert filter_installed_desktop_cycle_errors(
            errors,
            _analysis_result(metadata, server),
            str(root),
        ) is errors


def test_t12_no_cycles_does_not_query_live(
    tmp_path, monkeypatch,
):
    def forbidden(_root):
        raise AssertionError("LIVE must not be queried")

    monkeypatch.setattr(
        "contextor.core.live_state.connect",
        forbidden,
    )

    errors = [_other()]

    assert filter_installed_desktop_cycle_errors(
        errors,
        SimpleNamespace(live_publish_status="success"),
        str(tmp_path),
    ) is errors


def test_t13_presenter_is_connected_to_desktop_full_scan():
    import inspect
    from contextor.ui.gui import ContextorGUI

    source = inspect.getsource(ContextorGUI.analyze)

    assert "filter_installed_desktop_cycle_errors(" in source
    assert "return errors, analysis_result" in source
