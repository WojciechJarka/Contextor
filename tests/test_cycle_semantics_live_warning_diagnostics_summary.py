"""WARN-4F: installed warning eligibility controls MCP attention only."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from contextor.core.diagnostics_projection import (
    diagnostics_summary_for_state,
)
from contextor.core.live_state.runtime import (
    _repository_canonical_query_handler,
)
from contextor.core.cycle_semantics.live_warning_diagnostics_summary import (
    project_locked_warning_diagnostics_summary,
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


def _install_query_handler(server):
    server._canonical_query_handler = _repository_canonical_query_handler


def _summary(client):
    response = client.canonical_query(
        "diagnostics_summary",
        payload={},
    )
    assert response["status"] == "ok"
    return response["result"]


@pytest.mark.parametrize("sources,accepted,active", [
    (PASS_AND_UNKNOWN, 1, 1),
    (PASS_AND_HAZARD, 1, 1),
    (TWO_PASS, 2, 0),
])
def test_t01_t03_installed_partial_scc_controls_attention(
    tmp_path, isolated_dirs, sources, accepted, active,
):
    _, state, metadata = _fixture(tmp_path, sources)

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)

        original = diagnostics_summary_for_state(state)
        structural = copy.deepcopy(state.cycles)
        events = copy.deepcopy(server._events)

        summary = _summary(client)

        assert summary["cycles"]["count"] == 2
        assert summary["cycles"]["model_pass_count"] == accepted
        assert summary["cycles"]["active_warning_count"] == active
        assert summary["cycles"]["warning_availability"] == "fresh"
        assert summary["attention_required"] is (active > 0)

        assert original["cycles"]["count"] == 2
        assert "active_warning_count" not in original["cycles"]
        assert state.cycles == structural
        assert server._events == events


def test_t04_no_partial_receipt_preserves_all_warnings(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(
        tmp_path, TWO_PASS, partial=False,
    )

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)
        summary = _summary(client)

        assert summary["cycles"]["count"] == 2
        assert summary["cycles"]["model_pass_count"] == 0
        assert summary["cycles"]["active_warning_count"] == 2
        assert summary["attention_required"] is True


def test_t05_invalid_partial_receipt_cannot_suppress(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    receipt = state.cycle_partial_source_publication
    state.cycle_partial_source_publication = replace(
        receipt,
        claims_sha256="0" * 64,
    )

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)
        summary = _summary(client)

        assert summary["cycles"]["count"] == 2
        assert summary["cycles"]["model_pass_count"] == 0
        assert summary["cycles"]["active_warning_count"] == 2
        assert summary["attention_required"] is True


def test_t06_real_syntax_error_remains_attention(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)

    state.syntax_diagnostics_state = "fresh"
    state.syntax_diagnostics_by_path = {
        "broken.py": {
            "status": "checked_with_errors",
            "errors": [{"message": "invalid syntax"}],
        },
    }

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)
        summary = _summary(client)

        assert summary["cycles"]["count"] == 2
        assert summary["cycles"]["active_warning_count"] == 0
        assert summary["syntax_errors"]["count"] == 1
        assert summary["attention_required"] is True


def test_t07_collision_remains_attention(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)

    state.collisions_state = "fresh"
    state.collisions = [object()]

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)
        summary = _summary(client)

        assert summary["cycles"]["active_warning_count"] == 0
        assert summary["name_collisions"]["count"] == 1
        assert summary["attention_required"] is True


def test_t08_stale_structural_inventory_never_claims_zero(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    state.cycles_state = "stale"

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)
        summary = _summary(client)

        assert summary["cycles"]["count"] is None
        assert "active_warning_count" not in summary["cycles"]
        assert summary["cycles"]["availability"] == "stale"


def test_t09_resync_never_suppresses_or_certifies(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)
    state.resync_required = True

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)
        summary = _summary(client)

        assert summary["cycles"]["count"] is None
        assert "active_warning_count" not in summary["cycles"]
        assert summary["cycles"]["availability"] == "stale"


def test_t10_recovery_degraded_preserves_raw_summary(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)
        try:
            server._recovery_release_degraded = True
            summary = _summary(client)

            assert summary["cycles"]["count"] == 2
            assert "active_warning_count" not in summary["cycles"]
            assert summary["attention_required"] is True
        finally:
            server._recovery_release_degraded = False


def test_t11_incomplete_authority_preserves_raw_warnings(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)
        server._authority_identity["process_start_identity"] = None

        summary = _summary(client)

        assert summary["cycles"]["count"] == 2
        assert "active_warning_count" not in summary["cycles"]
        assert summary["attention_required"] is True


def test_t12_pure_projection_rejects_wrong_revision(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        with server._lock:
            raw = diagnostics_summary_for_state(state)
            report = server._owner_cycle_warning_report_locked()
            original = copy.deepcopy(raw)

            result = project_locked_warning_diagnostics_summary(
                raw,
                report,
                canonical_revision=server._revision + 1,
                activity_epoch=server._activity_epoch,
                authority_identity=server._authority_identity,
            )

        assert result is raw
        assert raw == original
        assert "active_warning_count" not in result["cycles"]


def test_t13_pure_projection_rejects_count_mismatch(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        with server._lock:
            raw = diagnostics_summary_for_state(state)
            report = server._owner_cycle_warning_report_locked()
            damaged = dict(report, structural_count=99)

            result = project_locked_warning_diagnostics_summary(
                raw,
                damaged,
                canonical_revision=server._revision,
                activity_epoch=server._activity_epoch,
                authority_identity=server._authority_identity,
            )

        assert result is raw
        assert raw["cycles"]["count"] == 2
        assert raw["attention_required"] is True


def test_t14_narrow_mcp_transport_uses_owner_summary(
    tmp_path, isolated_dirs, monkeypatch,
):
    from contextor.mcp.runtime import (
        query_live_diagnostics_summary_narrow,
    )

    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)

        monkeypatch.setattr(
            "contextor.core.live_state.connect",
            lambda _root: client,
        )

        result = query_live_diagnostics_summary_narrow(root)

        assert result.status == "ok"
        assert result.revision == metadata.revision
        assert result.summary["cycles"]["count"] == 2
        assert result.summary["cycles"]["model_pass_count"] == 2
        assert result.summary["cycles"]["active_warning_count"] == 0
        assert result.summary["attention_required"] is False


def test_t15_repeated_query_is_read_only(
    tmp_path, isolated_dirs,
):
    _, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _install_query_handler(server)

        before = copy.deepcopy((
            state.cycles,
            state.dependency_graph.hard_edges,
            server._events,
            server._activity_seq,
        ))

        first = _summary(client)
        second = _summary(client)

        assert first == second
        assert (
            state.cycles,
            state.dependency_graph.hard_edges,
            server._events,
            server._activity_seq,
        ) == before
