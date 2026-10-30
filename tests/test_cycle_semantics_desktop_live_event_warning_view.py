"""WARN-4J: Desktop LIVE feed suppresses only owner-proven cycle additions."""

from __future__ import annotations

import copy

import pytest

from contextor.core.live_state.watcher import DesktopLiveEventFeed
from tests.test_cycle_semantics_live_installed_partial_claims import (
    _fixture,
    _owner,
)
from tests.test_original_worker_partial_scc_preparation import (
    PASS_AND_UNKNOWN,
    TWO_PASS,
)


@pytest.fixture(autouse=True)
def _inline_worker(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _event(paths, revision, *, status="UPDATED", action="ADDED"):
    return {
        "seq": 1,
        "category": "LIVE_STATE",
        "operation": "update_file",
        "origin": "desktop_watcher",
        "status": status,
        "file_path": "a.py",
        "canonical_revision": revision,
        "diagnostic_changes": {
            "total": len(paths),
            "truncated": False,
            "items": [
                {
                    "action": action,
                    "diagnostic_kind": "cycle",
                    "cycle_nodes": list(path),
                }
                for path in paths
            ],
        },
    }


def _feed(client, server, event, *, report=None, report_error=None):
    response = {
        "status": "ok",
        "revision": server._revision,
        "activity_epoch": server._activity_epoch,
        "events": [event],
        "truncated": False,
    }

    received = []
    reads = []

    class Adapter:
        endpoint = client.endpoint

        def get_events(self, **_kwargs):
            return response

        def get_installed_cycle_warning_projection(self):
            reads.append(1)
            if report_error is not None:
                raise report_error
            if report is not None:
                return report
            return client.get_installed_cycle_warning_projection()

    feed = DesktopLiveEventFeed(
        Adapter(),
        lambda message, event=None: received.append(
            (message, event)
        ),
        initial_seq=0,
    )
    return feed, received, reads, response


def test_t01_mixed_real_owner_suppresses_only_model_pass(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(
        tmp_path, PASS_AND_UNKNOWN,
    )

    with _owner(state, metadata) as (server, client):
        event = _event(state.cycles, metadata.revision)
        original = copy.deepcopy(event)
        feed, received, reads, response = _feed(
            client, server, event,
        )

        feed.poll_once()

        assert len(reads) == 1
        assert len(received) == 1
        message, delivered_event = received[0]

        assert "cycle added: x -> y -> x" in message
        assert "cycle added: a -> b -> a" not in message
        assert delivered_event is event
        assert event == original
        assert len(state.cycles) == 2


def test_t02_two_model_pass_cycles_are_both_suppressed(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        event = _event(state.cycles, metadata.revision)
        feed, received, reads, response = _feed(
            client, server, event,
        )

        feed.poll_once()

        assert len(reads) == 1
        assert received == [
            (
                f"[LIVE] Watcher updated a.py (rev {metadata.revision})",
                event,
            ),
        ]


def test_t03_syntax_error_message_survives_suppression(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        event = _event(
            state.cycles,
            metadata.revision,
            status="SYNTAX_ERROR",
        )
        event.update({
            "error": "invalid syntax",
            "line_number": 2,
            "column_number": 3,
        })

        feed, received, reads, response = _feed(
            client, server, event,
        )

        feed.poll_once()

        assert len(reads) == 1
        assert received == [
            (
                "[LIVE] Syntax error in a.py line 2, "
                "column 3: invalid syntax",
                event,
            ),
        ]


@pytest.mark.parametrize("mutation", [
    {"revision": 999},
    {"activity_epoch": "wrong-epoch"},
    {"service_instance_id": "foreign-owner"},
    {"model_pass_count": 0},
    {"graph_sha256": "invalid"},
])
def test_t04_mismatched_generation_or_identity_preserves_warning(
    tmp_path, isolated_dirs, mutation,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        report = client.get_installed_cycle_warning_projection()
        report.update(mutation)
        event = _event(state.cycles[:1], metadata.revision)
        feed, received, reads, response = _feed(
            client, server, event, report=report,
        )

        feed.poll_once()

        assert len(reads) == 1
        assert len(received) == 1
        assert "cycle added: a -> b -> a" in received[0][0]


def test_t05_unavailable_owner_preserves_original_warning(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        event = _event(state.cycles[:1], metadata.revision)
        feed, received, reads, response = _feed(
            client, server, event,
            report_error=TimeoutError("synthetic timeout"),
        )

        feed.poll_once()

        assert len(reads) == 1
        assert "cycle added: a -> b -> a" in received[0][0]


def test_t06_older_event_never_uses_latest_projection(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        event = _event(
            state.cycles[:1], metadata.revision - 1,
        )
        feed, received, reads, response = _feed(
            client, server, event,
        )

        feed.poll_once()

        assert reads == []
        assert "cycle added: a -> b -> a" in received[0][0]


def test_t07_resolved_cycle_is_not_relabelled_as_model_acceptance(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        event = _event(
            state.cycles[:1],
            metadata.revision,
            action="RESOLVED",
        )
        feed, received, reads, response = _feed(
            client, server, event,
        )

        feed.poll_once()

        assert reads == []
        assert "cycle resolved: a -> b -> a" in received[0][0]


def test_t08_no_cycle_addition_does_not_query_projection(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        event = _event([], metadata.revision)
        feed, received, reads, response = _feed(
            client, server, event,
        )

        feed.poll_once()

        assert reads == []
        assert len(received) == 1
        assert received[0][1] is event


def test_t09_current_warning_projection_does_not_change_journal(
    tmp_path, isolated_dirs,
):
    root, state, metadata = _fixture(
        tmp_path, PASS_AND_UNKNOWN,
    )

    with _owner(state, metadata) as (server, client):
        event = _event(state.cycles, metadata.revision)
        before = copy.deepcopy((
            server._events,
            server._activity_seq,
            state.cycles,
            state.dependency_graph.hard_edges,
        ))

        feed, received, reads, response = _feed(
            client, server, event,
        )

        feed.poll_once()

        assert len(reads) == 1
        assert (
            server._events,
            server._activity_seq,
            state.cycles,
            state.dependency_graph.hard_edges,
        ) == before


@pytest.mark.parametrize("bad_nodes", [
    [["a"], "b", "a"],
    [{"module": "a"}, "b", "a"],
    ["a", ["b"], "a"],
])
def test_t10_malformed_cycle_nodes_do_not_crash_event_feed(
    tmp_path, isolated_dirs, bad_nodes,
):
    root, state, metadata = _fixture(tmp_path, TWO_PASS)

    with _owner(state, metadata) as (server, client):
        event = _event(state.cycles[:1], metadata.revision)
        event["diagnostic_changes"]["items"][0]["cycle_nodes"] = bad_nodes

        original = copy.deepcopy(event)

        feed, received, reads, response = _feed(
            client, server, event,
        )

        feed.poll_once()

        assert len(reads) == 1
        assert received == [
            (
                f"[LIVE] Watcher updated a.py (rev {metadata.revision})",
                event,
            ),
        ]
        assert feed._last_seq == 1
        assert event == original
