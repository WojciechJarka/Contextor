"""MCP get_live_events current warning view and structural event separation."""

from __future__ import annotations

import copy
import json

import pytest

from contextor.mcp.tools.get_live_events import get_live_events
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture, _owner,
)
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_HAZARD, PASS_AND_UNKNOWN, TWO_PASS,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _connect(monkeypatch, client):
    monkeypatch.setattr(
        "contextor.core.live_state.runtime.connect_existing_with_status",
        lambda _root: (client, "ok"),
    )


@pytest.mark.parametrize("sources,accepted,active", [
    (PASS_AND_UNKNOWN, 1, 1),
    (PASS_AND_HAZARD, 1, 1),
    (TWO_PASS, 2, 0),
])
def test_t01_t03_real_installed_partial_warning_view(
    tmp_path, isolated_dirs, monkeypatch, sources, accepted, active,
):
    root, state, metadata = _fixture(tmp_path, sources)
    with _owner(state, metadata) as (server, client):
        _connect(monkeypatch, client)
        before = copy.deepcopy((
            server._events,
            server._activity_seq,
            state.cycles,
        ))

        result = json.loads(get_live_events(str(root)))

        assert result["status"] == "ok"
        assert result["cycle_diagnostic_history_semantics"] == (
            "STRUCTURAL_CHANGES_NOT_CURRENT_ACTIVE_WARNING_STATE"
        )

        view = result["cycle_warning_view"]
        assert view["status"] == "fresh"
        assert view["revision"] == metadata.revision
        assert view["activity_epoch"] == server._activity_epoch
        assert view["structural_count"] == 2
        assert view["model_pass_count"] == accepted
        assert view["active_warning_count"] == active
        assert len(view["model_pass_paths"]) == accepted
        assert len(view["active_warning_paths"]) == active
        assert set(map(tuple, view["model_pass_paths"])).isdisjoint(
            set(map(tuple, view["active_warning_paths"]))
        )
        assert len(view["structural_paths"]) == 2

        assert (
            server._events,
            server._activity_seq,
            state.cycles,
        ) == before


def test_t04_missing_partial_receipt_does_not_hide_warnings(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(
        tmp_path, TWO_PASS, partial=False,
    )
    with _owner(state, metadata) as (_, client):
        _connect(monkeypatch, client)
        view = json.loads(
            get_live_events(str(root))
        )["cycle_warning_view"]

        assert view["status"] == "fresh"
        assert view["structural_count"] == 2
        assert view["model_pass_count"] == 0
        assert view["active_warning_count"] == 2


def test_t05_stale_cycles_never_become_false_zero_warnings(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)
    state.cycles_state = "stale"

    with _owner(state, metadata) as (_, client):
        _connect(monkeypatch, client)
        view = json.loads(
            get_live_events(str(root))
        )["cycle_warning_view"]

        assert view["status"] == "unavailable"
        assert "active_warning_count" not in view
        assert "active_warning_paths" not in view


class _FakeClient:
    def __init__(self, events, projection):
        self.events = events
        self.projection = projection

    def get_events(self, **_kwargs):
        return self.events

    def get_installed_cycle_warning_projection(self):
        if isinstance(self.projection, Exception):
            raise self.projection
        return self.projection


def _fake_reports():
    a = ("a", "b", "a")
    b = ("x", "y", "x")

    events = {
        "status": "ok",
        "revision": 12,
        "activity_epoch": "epoch-1",
        "events": [],
        "total": 0,
        "truncated": False,
    }

    projection = {
        "status": "ok",
        "binding_state": "INSTALLED_CYCLE_WARNING_PROJECTION",
        "revision": 12,
        "activity_epoch": "epoch-1",
        "structural_paths": (a, b),
        "model_pass_paths": (a,),
        "active_warning_paths": (b,),
        "structural_count": 2,
        "model_pass_count": 1,
        "active_warning_count": 1,
    }

    return events, projection


@pytest.mark.parametrize("mutation", [
    {"revision": 13},
    {"activity_epoch": "epoch-2"},
    {"revision": True},
    {"binding_state": "FORGED"},
])
def test_t06_generation_or_binding_mismatch_fails_closed(
    tmp_path, monkeypatch, mutation,
):
    events, report = _fake_reports()
    report.update(mutation)
    _connect(monkeypatch, _FakeClient(events, report))

    view = json.loads(
        get_live_events(str(tmp_path))
    )["cycle_warning_view"]

    assert view["status"] == "unavailable"
    assert "active_warning_count" not in view


@pytest.mark.parametrize("mutation", [
    {"active_warning_paths": ()},
    {"model_pass_paths": (("a", "b", "a"), ("x", "y", "x"))},
    {"structural_count": 0},
    {"model_pass_paths": [["a", "b", "a"]]},
])
def test_t07_invalid_partition_fails_closed(
    tmp_path, monkeypatch, mutation,
):
    events, report = _fake_reports()
    report.update(mutation)
    _connect(monkeypatch, _FakeClient(events, report))

    view = json.loads(
        get_live_events(str(tmp_path))
    )["cycle_warning_view"]

    assert view["status"] == "unavailable"
    assert "active_warning_paths" not in view


def test_t08_query_failure_fails_closed_without_dropping_event_history(
    tmp_path, monkeypatch,
):
    events, _ = _fake_reports()
    events["events"] = [{
        "revision": 12,
        "diagnostic_changes": {
            "total": 1,
            "truncated": False,
            "items": [{
                "diagnostic_kind": "cycle",
                "action": "ADDED",
                "cycle_nodes": ["a", "b", "a"],
            }],
        },
    }]
    original = copy.deepcopy(events)

    _connect(monkeypatch, _FakeClient(events, RuntimeError("connection failed")))

    result = json.loads(get_live_events(str(tmp_path)))

    assert result["status"] == "ok"
    assert result["events"] == original["events"]
    assert result["cycle_warning_view"]["status"] == "unavailable"
    assert "active_warning_paths" not in result["cycle_warning_view"]
    assert events == original


def test_t09_raw_cycle_events_are_history_not_current_warning_list(
    tmp_path, monkeypatch,
):
    events, report = _fake_reports()
    events["events"] = [{
        "revision": 12,
        "diagnostic_changes": {
            "total": 1,
            "truncated": False,
            "items": [{
                "diagnostic_kind": "cycle",
                "action": "ADDED",
                "cycle_nodes": ["a", "b", "a"],
            }],
        },
    }]

    original = copy.deepcopy(events)
    _connect(monkeypatch, _FakeClient(events, report))

    result = json.loads(get_live_events(str(tmp_path)))

    assert result["events"] == original["events"]
    assert result["cycle_warning_view"]["model_pass_paths"] == [
        ["a", "b", "a"],
    ]
    assert result["cycle_warning_view"]["active_warning_paths"] == [
        ["x", "y", "x"],
    ]
    assert result["cycle_diagnostic_history_semantics"] == (
        "STRUCTURAL_CHANGES_NOT_CURRENT_ACTIVE_WARNING_STATE"
    )


def test_t10_no_live_owner_keeps_existing_response(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(
        "contextor.core.live_state.runtime.connect_existing_with_status",
        lambda _root: (None, "no_live_service"),
    )

    result = json.loads(get_live_events(str(tmp_path)))

    assert result["status"] == "no_live_service"
    assert "cycle_warning_view" not in result


def test_t11_non_ok_event_response_remains_unchanged(
    tmp_path, monkeypatch,
):
    events, report = _fake_reports()
    events = {
        "status": "error",
        "error": "event_history_unavailable",
    }
    _connect(monkeypatch, _FakeClient(events, report))

    result = json.loads(get_live_events(str(tmp_path)))

    assert result == events
