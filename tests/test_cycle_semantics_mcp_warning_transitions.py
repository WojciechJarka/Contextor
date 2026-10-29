"""WARN-4I: MCP projects current commit warning transitions separately."""

from __future__ import annotations

import copy
import json

import pytest

from contextor.mcp.tools.get_live_events import get_live_events
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture, _owner,
)
from tests.test_cycle_semantics_live_warning_transition_checkpoint import (
    _installed_next,
)
from tests.test_original_worker_partial_scc_preparation import TWO_PASS
from tests.test_cycle_semantics_mcp_live_warning_view import _fake_reports


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _connect(monkeypatch, client):
    monkeypatch.setattr(
        "contextor.core.live_state.runtime.connect_existing_with_status",
        lambda _root: (client, "ok"),
    )


def _checkpoint():
    return {
        "status": "ok",
        "binding_state": "INSTALLED_WARNING_TRANSITION_CHECKPOINT",
        "from_revision": 11,
        "to_revision": 12,
        "activity_epoch": "epoch-1",
        "repo_id": "synthetic-repo",
        "root_path": "/synthetic",
        "service_instance_id": "synthetic-service",
        "process_start_identity": "synthetic-process",
        "transitions": (
            {
                "path": ("a", "b", "a"),
                "action": "MODEL_ACCEPTED",
                "previous_state": "ACTIVE",
                "current_state": "MODEL_PASS",
            },
            {
                "path": ("x", "y", "x"),
                "action": "STRUCTURAL_ADDED",
                "previous_state": None,
                "current_state": "ACTIVE",
            },
        ),
        "authority": (
            "LIVE_OWNER_COMMIT_SCOPED_WARNING_TRANSITIONS"
            "_NOT_STRUCTURAL_REMOVAL_FOR_MODEL_ACCEPTANCE"
            "_NOT_RUNTIME_SAFETY"
        ),
    }


class _Client:
    def __init__(self, events, projection, checkpoint):
        self.events = events
        self.projection = projection
        self.checkpoint = checkpoint
        self.checkpoint_calls = 0

    def get_events(self, **_kwargs):
        return self.events

    def get_installed_cycle_warning_projection(self):
        return self.projection

    def request(self, operation, **kwargs):
        assert operation == "get_installed_cycle_warning_transitions"
        assert kwargs == {"timeout": 2.0}
        self.checkpoint_calls += 1
        if isinstance(self.checkpoint, Exception):
            raise self.checkpoint
        return self.checkpoint


def test_t01_latest_installed_commit_reports_real_reactivations(
    tmp_path, isolated_dirs, monkeypatch,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        _connect(monkeypatch, client)

        before = json.loads(get_live_events(str(root)))

        assert before["status"] == "ok"
        assert before["cycle_warning_view"]["status"] == "fresh"
        assert before["cycle_warning_transitions"]["status"] == "unavailable"

        _installed_next(root, server, partial=False)

        journal_before = copy.deepcopy(
            (server._events, server._activity_seq)
        )

        result = json.loads(get_live_events(str(root)))

        view = result["cycle_warning_view"]
        delta = result["cycle_warning_transitions"]

        assert result["status"] == "ok"
        assert view["status"] == "fresh"
        assert view["structural_count"] == 2
        assert view["model_pass_count"] == 0
        assert view["active_warning_count"] == 2

        assert delta["status"] == "fresh"
        assert delta["scope"] == (
            "LATEST_INSTALLED_COMMIT_ONLY_NOT_RETAINED_EVENT_HISTORY"
        )
        assert delta["from_revision"] == metadata.revision
        assert delta["to_revision"] == result["revision"]
        assert delta["activity_epoch"] == result["activity_epoch"]
        assert delta["transition_count"] == 2
        assert [item["action"] for item in delta["transitions"]] == [
            "WARNING_REACTIVATED", "WARNING_REACTIVATED",
        ]

        assert (
            server._events, server._activity_seq
        ) == journal_before


def test_t02_model_acceptance_is_not_structural_removal(
    tmp_path, monkeypatch,
):
    events, projection = _fake_reports()
    checkpoint = _checkpoint()
    client = _Client(events, projection, checkpoint)
    _connect(monkeypatch, client)

    result = json.loads(get_live_events(str(tmp_path)))

    delta = result["cycle_warning_transitions"]

    assert delta["status"] == "fresh"
    assert delta["transition_count"] == 2
    assert [item["action"] for item in delta["transitions"]] == [
        "MODEL_ACCEPTED", "STRUCTURAL_ADDED",
    ]
    assert result["cycle_warning_view"]["structural_count"] == 2
    assert client.checkpoint_calls == 1


@pytest.mark.parametrize("change", [
    {"to_revision": 13},
    {"activity_epoch": "wrong-epoch"},
    {"from_revision": 12},
    {"binding_state": "FORGED"},
    {"authority": "FORGED"},
    {"service_instance_id": ""},
])
def test_t03_checkpoint_identity_and_generation_mismatch_fails_closed(
    tmp_path, monkeypatch, change,
):
    events, projection = _fake_reports()
    checkpoint = {**_checkpoint(), **change}
    _connect(monkeypatch, _Client(events, projection, checkpoint))

    response = json.loads(get_live_events(str(tmp_path)))
    delta = response["cycle_warning_transitions"]

    assert delta["status"] == "unavailable"
    assert "transition_count" not in delta
    assert response["cycle_warning_view"]["status"] == "fresh"


@pytest.mark.parametrize("item", [
    {
        "path": ("a", "b", "a"),
        "action": "STRUCTURAL_REMOVED",
        "previous_state": "ACTIVE",
        "current_state": None,
    },
    {
        "path": ("a", "b", "a"),
        "action": "WARNING_REACTIVATED",
        "previous_state": "MODEL_PASS",
        "current_state": "ACTIVE",
    },
    {
        "path": ("a", "b", "a"),
        "action": "MODEL_ACCEPTED",
        "previous_state": "ACTIVE",
        "current_state": "ACTIVE",
    },
    {
        "path": ("a", "b", "a"),
        "action": "UNKNOWN",
        "previous_state": "ACTIVE",
        "current_state": "MODEL_PASS",
    },
    {
        "path": ("a", "b", "x"),
        "action": "MODEL_ACCEPTED",
        "previous_state": "ACTIVE",
        "current_state": "MODEL_PASS",
    },
])
def test_t04_invalid_transition_never_becomes_fresh(
    tmp_path, monkeypatch, item,
):
    events, projection = _fake_reports()
    checkpoint = _checkpoint()
    checkpoint["transitions"] = (item,)
    _connect(monkeypatch, _Client(events, projection, checkpoint))

    delta = json.loads(get_live_events(str(tmp_path)))[
        "cycle_warning_transitions"
    ]

    assert delta["status"] == "unavailable"
    assert "transitions" not in delta


def test_t05_missing_checkpoint_does_not_claim_zero(
    tmp_path, monkeypatch,
):
    events, projection = _fake_reports()
    client = _Client(
        events,
        projection,
        {
            "status": "unavailable",
            "reason": "NO_COMMITTED_WARNING_TRANSITION",
        },
    )
    _connect(monkeypatch, client)

    result = json.loads(get_live_events(str(tmp_path)))

    assert result["cycle_warning_transitions"]["status"] == "unavailable"
    assert "transition_count" not in result["cycle_warning_transitions"]


def test_t06_unavailable_current_view_skips_transition_query(
    tmp_path, monkeypatch,
):
    events, projection = _fake_reports()
    projection["revision"] = 13
    client = _Client(events, projection, _checkpoint())
    _connect(monkeypatch, client)

    result = json.loads(get_live_events(str(tmp_path)))

    assert result["cycle_warning_view"]["status"] == "unavailable"
    assert result["cycle_warning_transitions"]["status"] == "unavailable"
    assert client.checkpoint_calls == 0


def test_t07_transport_failure_does_not_remove_history(
    tmp_path, monkeypatch,
):
    events, projection = _fake_reports()
    events["events"] = [{
        "canonical_revision": 12,
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

    client = _Client(
        events, projection, TimeoutError("synthetic timeout"),
    )
    _connect(monkeypatch, client)

    result = json.loads(get_live_events(str(tmp_path)))

    assert result["status"] == "ok"
    assert result["events"] == original["events"]
    assert result["cycle_warning_transitions"]["status"] == "unavailable"
    assert "transition_count" not in result["cycle_warning_transitions"]
    assert events == original


def test_t08_documentation_describes_current_warning_semantics():
    from pathlib import Path

    docs = (
        Path(__file__).resolve().parents[1]
        / "contextor" / "mcp" / "docs" / "get_live_events.json"
    )

    data = json.loads(docs.read_text(encoding="utf-8"))

    assert data["version"] == "1.0.0"
    assert data["tool"] == "get_live_events"

    behavior = " ".join(data["behavior"])

    for term in (
        "cycle_warning_view",
        "cycle_warning_transitions",
        "MODEL_ACCEPTED",
        "WARNING_REACTIVATED",
        "STRUCTURAL_ADDED",
        "STRUCTURAL_REMOVED",
        "historical structural changes",
        "unavailable",
    ):
        assert term in behavior
