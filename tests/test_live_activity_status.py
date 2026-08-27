"""Comprehensive test suite for Desktop LIVE status and MCP activity event architecture.

Covers all 10 concrete correctness and evidence requirements:
1. Authoritative Desktop full analysis event & first-run cursor handoff
2. Event timestamp authoritativeness & invariance to drain delay
3. Single-event watcher & MCP update semantics
4. Canonical continuity isolation from >100 MCP telemetry events
5. Central MCP wrapper read-only success
6. Central MCP wrapper failure re-raise & logging
7. MCP analyze_project wrapper & canonical publication separation
8. All 24 registered FastMCP tools coverage & registry synchronization
9. Real server-to-GUI burst ordering, zero dropped events & zero duplicates
10. Desktop vs MCP full analysis publication equivalence
"""

import inspect
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from contextor.core.live_state import (
    CanonicalLiveServer,
    DesktopLiveEventFeed,
    DesktopLiveWatcher,
    LiveStateClient,
)
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.mcp_server import (
    REGISTERED_MCP_TOOL_NAMES,
    _emit_mcp_call_telemetry,
    _instrument_mcp_tool,
    _resolve_telemetry_clients,
    mcp,
    register_mcp_tool,
)
from contextor.ui import gui

pytestmark = pytest.mark.live


class _FakeVar:
    def __init__(self, value=""):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


@pytest.fixture
def live_server_instance():
    server = CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=1)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)
    yield server, client
    server.close()
    thread.join(timeout=2)


def test_desktop_full_analysis_authoritative_event_and_first_run_cursor_handoff(live_server_instance):
    server, client = live_server_instance

    # 1. Cursor handoff: capture pre_seq before analysis starts
    pre_seq = client.get_events(limit=1).get("latest_seq", 0)
    assert pre_seq == 0

    # 2. Analysis completes and publishes canonical state to server
    state = SimpleNamespace(modules={"mod_a": object()}, revision=10)
    pub_res = client.publish(state, origin="desktop_analysis")
    assert pub_res["status"] == "ok"
    assert pub_res["seq"] == 1

    # 3. Create feed using cursor handoff (initial_seq=pre_seq)
    received_statuses = []
    received_events = []

    def status_callback(msg, event=None):
        received_statuses.append(msg)
        if event is not None:
            received_events.append(event)

    feed = DesktopLiveEventFeed(client, status_callback, initial_seq=pre_seq)
    feed.poll_once()

    # Authoritative LIVE_STATE publication is consumed exactly once from journal
    assert len(received_statuses) == 1
    assert len(received_events) == 1
    assert "[LIVE]" in received_statuses[0]
    assert "(rev 10)" in received_statuses[0]
    assert received_events[0]["canonical_revision"] == 10
    assert received_events[0]["source"] == "desktop_analysis"


def test_event_timestamp_is_authoritative_and_invariant_to_drain_delay():
    queue_instance = queue.Queue()
    controller = SimpleNamespace(
        live_status_var=_FakeVar(),
        _live_status_queue=queue_instance,
        _live_status_draining=False,
        last_live_state=None,
    )

    # Event with explicit UTC timestamp
    fixed_ts = "2026-08-27T12:34:56.789000+00:00"
    event_payload = {
        "seq": 42,
        "timestamp": fixed_ts,
        "category": "LIVE_STATE",
        "canonical_revision": 7,
        "status": "PUBLISHED",
        "source": "desktop_analysis",
    }

    # Queue event
    gui.ContextorGUI._set_live_status(
        controller,
        "[LIVE] Analysis published",
        category="LIVE_STATE",
        event=event_payload,
    )

    # Simulate rotation/drain delay
    time.sleep(0.1)

    # Drain queue
    gui.ContextorGUI._drain_live_status_queue(controller)

    # Convert fixed_ts to local time string
    expected_local_dt = datetime.fromisoformat(fixed_ts).astimezone()
    expected_time_str = expected_local_dt.strftime("%H:%M:%S")

    display = controller.live_status_var.get()
    assert expected_time_str in display
    assert controller.last_live_state["timestamp"] == fixed_ts
    assert controller.last_live_state["revision"] == 7


def test_desktop_watcher_and_mcp_update_file_single_event_semantics(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    py_file = repo / "module.py"
    py_file.write_text("x = 1\n", encoding="utf-8")
    PersistentIdentityRegistry(str(repo))

    initial_state = SimpleNamespace(modules={"module": object()}, revision=1)

    def updater(state, path):
        state.revision += 1
        return SimpleNamespace(status="UPDATED", file_path=path, affected_modules=["module"])

    server = CanonicalLiveServer(state=initial_state, revision=1, updater=updater)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    gui_statuses = []

    def gui_status_callback(message, event=None):
        if event is None and (message.startswith("LIVE update successful:") or message.startswith("Updating LIVE:")):
            return
        gui_statuses.append((message, event))

    watcher = DesktopLiveWatcher(
        repo,
        client,
        on_status=lambda msg: gui_status_callback(msg, event=None),
    )
    feed = DesktopLiveEventFeed(
        client,
        lambda msg, event=None: gui_status_callback(msg, event=event),
        initial_seq=0,
    )

    try:
        time.sleep(0.05)
        py_file.write_text("x = 2\n", encoding="utf-8")

        # 1. Watcher polls and calls client.update_file
        changed = watcher.poll_once()
        assert str(py_file) in changed

        # 2. Event feed polls journal
        feed.poll_once()

        # Exactly 1 displayed update message from authoritative journal event
        assert len(gui_statuses) == 1
        msg, evt = gui_statuses[0]
        assert "[LIVE] Watcher updated module.py (rev 2)" in msg
        assert evt is not None
        assert evt["canonical_revision"] == 2
        assert evt["source"] == "desktop_watcher"
    finally:
        server.close()
        thread.join(timeout=2)


def test_canonical_continuity_after_100_mcp_events_regression(live_server_instance):
    server, client = live_server_instance

    # Set canonical revision R = 10
    state = SimpleNamespace(modules={"pkg": object()}, revision=10)
    client.publish(state, origin="desktop_analysis")
    assert client.ping()["revision"] == 2  # initial server had revision=1, publish made it 2
    r_rev = client.ping()["revision"]

    # Append 120 MCP_CALL events to evict all previous entries from the 100-event buffer
    for i in range(120):
        client.record_activity("MCP_CALL", tool=f"tool_{i}", source="mcp")

    # 1. Canonical revision remains strictly R
    assert client.ping()["revision"] == r_rev

    # 2. MCP events cannot satisfy after_revision=r_rev or manufacture canonical continuity
    res_latest = client.get_events(after_revision=r_rev)
    assert res_latest["continuity"] == "continuous"
    assert res_latest["resync_required"] is False
    assert res_latest["events"] == []
    assert res_latest["total"] == 0

    # 3. Requesting after_revision < r_rev indicates gap since all canonical events were evicted
    res_gap = client.get_events(after_revision=r_rev - 1)
    assert res_gap["continuity"] == "gap"
    assert res_gap["resync_required"] is True
    assert res_gap["resync_reason"] == "event_retention_gap"

    # 4. New canonical publication works and returns new canonical event
    state_new = SimpleNamespace(modules={"pkg": object()}, revision=r_rev + 1)
    client.publish(state_new, origin="desktop_analysis")
    new_rev = client.ping()["revision"]
    assert new_rev == r_rev + 1

    res_after = client.get_events(after_revision=r_rev)
    assert res_after["continuity"] == "continuous"
    assert res_after["resync_required"] is False
    assert len(res_after["events"]) == 1
    assert res_after["events"][0]["revision"] == new_rev


def test_central_mcp_wrapper_read_only_success(live_server_instance, monkeypatch):
    server, client = live_server_instance
    initial_rev = client.ping()["revision"]

    # Point telemetry resolution to test client
    monkeypatch.setattr("contextor.mcp_server._resolve_telemetry_clients", lambda *args, **kwargs: [client])

    def mock_search_artifacts(repo_path: str, query: str):
        return {"results": ["item_1", "item_2"]}

    wrapped = _instrument_mcp_tool(mock_search_artifacts, "search_artifacts")

    # Invoke tool through wrapper
    res = wrapped(repo_path=".", query="test")
    assert res == {"results": ["item_1", "item_2"]}

    # Exactly 1 MCP_CALL event produced
    events = client.get_events(after_seq=0, category="MCP_CALL")["events"]
    assert len(events) == 1
    assert events[0]["tool"] == "search_artifacts"
    assert events[0]["success"] is True
    assert events[0]["canonical_revision"] is None

    # Canonical revision completely unchanged
    assert client.ping()["revision"] == initial_rev


def test_central_mcp_wrapper_failure_reraises_and_logs(live_server_instance, monkeypatch):
    server, client = live_server_instance
    initial_rev = client.ping()["revision"]

    monkeypatch.setattr("contextor.mcp_server._resolve_telemetry_clients", lambda *args, **kwargs: [client])

    def failing_tool(repo_path: str):
        raise ValueError("Simulated tool crash")

    wrapped = _instrument_mcp_tool(failing_tool, "get_module_context")

    with pytest.raises(ValueError, match="Simulated tool crash"):
        wrapped(repo_path=".")

    events = client.get_events(after_seq=0, category="MCP_CALL")["events"]
    assert len(events) == 1
    assert events[0]["tool"] == "get_module_context"
    assert events[0]["success"] is False
    assert events[0]["error"] == "Simulated tool crash"

    assert client.ping()["revision"] == initial_rev


def test_mcp_analyze_project_wrapper_and_canonical_publish_equivalence(live_server_instance, monkeypatch):
    server, client = live_server_instance

    monkeypatch.setattr("contextor.mcp_server._resolve_telemetry_clients", lambda *args, **kwargs: [client])

    # 1. MCP tool wrapper invocation entry
    def dummy_analyze(repo_path: str):
        return {"status": "job_started"}

    wrapped = _instrument_mcp_tool(dummy_analyze, "analyze_project")
    wrapped(repo_path=".")

    # 2. Canonical publication upon completion
    state = SimpleNamespace(modules={"pkg": object()}, revision=5)
    client.publish(state, origin="mcp_analysis")

    # Assert exactly 1 MCP_CALL and 1 distinct LIVE_STATE publish event
    events = client.get_events(after_seq=0)["events"]
    assert len(events) == 2

    assert events[0]["category"] == "MCP_CALL"
    assert events[0]["tool"] == "analyze_project"
    assert events[0]["canonical_revision"] is None

    assert events[1]["category"] == "LIVE_STATE"
    assert events[1]["operation"] == "publish"
    assert events[1]["source"] == "mcp_analysis"
    assert events[1]["canonical_revision"] == 5


def test_all_24_registered_mcp_tools_telemetry_against_fastmcp_registry(monkeypatch):
    # Verify FastMCP registry synchronization
    fastmcp_tool_names = set(mcp._tool_manager._tools.keys())
    assert set(REGISTERED_MCP_TOOL_NAMES) == fastmcp_tool_names
    assert len(REGISTERED_MCP_TOOL_NAMES) == 24

    calls_emitted = []

    def mock_emit(tool_name, root_path, success, error=None):
        calls_emitted.append((tool_name, success, error))

    monkeypatch.setattr("contextor.mcp_server._emit_mcp_call_telemetry", mock_emit)

    for tool_name in REGISTERED_MCP_TOOL_NAMES:
        calls_emitted.clear()

        def dummy_fn(**kwargs):
            return {"status": "ok"}

        wrapped = _instrument_mcp_tool(dummy_fn, tool_name)
        res = wrapped(repo_path=".")
        assert res == {"status": "ok"}
        assert len(calls_emitted) == 1
        assert calls_emitted[0] == (tool_name, True, None)


def test_real_server_to_gui_burst_ordering_and_zero_dropped_events(live_server_instance):
    server, client = live_server_instance

    queue_instance = queue.Queue()
    controller = SimpleNamespace(
        live_status_var=_FakeVar(),
        _live_status_queue=queue_instance,
        _live_status_draining=False,
        last_live_state=None,
    )

    def gui_callback(msg, event=None):
        cat = event.get("category", "LIVE_STATE") if event else "LIVE_STATE"
        gui.ContextorGUI._set_live_status(controller, msg, category=cat, event=event)

    feed = DesktopLiveEventFeed(client, gui_callback, initial_seq=0)

    # 1. Create interleaved sequence of 10 events (5 LIVE_STATE, 5 MCP_CALL) on server
    for i in range(5):
        client.publish(SimpleNamespace(modules={}, revision=10 + i), origin="desktop_analysis")
        client.record_activity("MCP_CALL", tool=f"mcp_tool_{i}", source="mcp")

    assert server._activity_seq == 10

    # 2. Poll in one single batch
    feed.poll_once()

    # 3. Assert queue has exactly 10 events in server sequence order
    assert queue_instance.qsize() == 10

    processed_events = []
    while not queue_instance.empty():
        item = queue_instance.get_nowait()
        processed_events.append(item)
        # Update last_live_state as GUI would
        if item.get("category") == "LIVE_STATE" and item.get("event"):
            controller.last_live_state = {
                "revision": item["event"].get("canonical_revision"),
                "status": item["event"].get("status"),
                "timestamp": item["event"].get("timestamp"),
                "source": item["event"].get("source"),
            }

    assert len(processed_events) == 10

    # Assert sequence ordering 1..10 and category alternating
    for idx, item in enumerate(processed_events):
        evt = item["event"]
        assert evt["seq"] == idx + 1
        expected_cat = "LIVE_STATE" if idx % 2 == 0 else "MCP_CALL"
        assert item["category"] == expected_cat

        # Timestamps match event timestamp in local time
        expected_time = datetime.fromisoformat(evt["timestamp"]).astimezone().strftime("%H:%M:%S")
        assert expected_time in item["formatted"]

    # Final last_live_state has canonical revision 14 (from event 9, 10 was MCP_CALL)
    assert controller.last_live_state["revision"] == 14


def test_desktop_vs_mcp_full_analysis_equivalence(live_server_instance):
    server, client = live_server_instance

    # Desktop publish
    state_d = SimpleNamespace(modules={"a": 1}, revision=100)
    res_d = client.publish(state_d, origin="desktop_analysis")
    assert res_d["status"] == "ok"
    assert res_d["revision"] == 2

    # MCP publish
    state_m = SimpleNamespace(modules={"a": 1, "b": 2}, revision=101)
    res_m = client.publish(state_m, origin="mcp_analysis")
    assert res_m["status"] == "ok"
    assert res_m["revision"] == 3

    events = client.get_events(after_seq=0)["events"]
    assert len(events) == 2

    # Both increment canonical revision and share identical LIVE_STATE event schema
    assert events[0]["category"] == "LIVE_STATE"
    assert events[0]["operation"] == "publish"
    assert events[0]["source"] == "desktop_analysis"
    assert events[0]["canonical_revision"] == 100

    assert events[1]["category"] == "LIVE_STATE"
    assert events[1]["operation"] == "publish"
    assert events[1]["source"] == "mcp_analysis"
    assert events[1]["canonical_revision"] == 101
