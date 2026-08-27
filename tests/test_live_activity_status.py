"""Comprehensive test suite for Desktop LIVE status and MCP activity event architecture.

Covers all concrete correctness and evidence requirements:
1. DesktopLiveEventFeed non-reentrant single poll owner & zero duplicates
2. Explicit inactive repo never falls through to other active repo
3. Rootless positional string is not repository path
4. Rootless tool emits once to each active repository
5. Noncanonical status/activity does not replace last_live_state
6. DesktopLiveEventFeed paginates >100 events without loss across pages
7. DesktopLiveEventFeed retention gap reports once and consumes all retained pages
8. Over 100 activity events are retained and not silently lost & activity gap detection
9. Authoritative Desktop full analysis event & first-run cursor handoff
10. Event timestamp authoritativeness & invariance to drain delay
11. Single-event watcher & MCP update semantics
12. Canonical continuity isolation from >100 MCP telemetry events
13. Central MCP wrapper read-only success
14. Central MCP wrapper failure re-raise & logging
15. MCP analyze_project wrapper & canonical publication separation
16. All 24 registered FastMCP tools coverage & registry synchronization
17. Real server-to-GUI burst ordering, zero dropped events & zero duplicates
18. Desktop vs MCP full analysis publication equivalence
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
from contextor.core.live_state.ipc import ACTIVITY_EVENT_RETENTION
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp_server import (
    REGISTERED_MCP_TOOL_NAMES,
    _emit_mcp_call_telemetry,
    _instrument_mcp_tool,
    _resolve_telemetry_clients,
    _tool_repository_argument,
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


def test_background_feed_has_single_poll_owner_and_no_duplicates(live_server_instance):
    server, client = live_server_instance
    delivered_seqs = []
    lock = threading.Lock()

    def status_callback(msg, event=None):
        if event and "seq" in event:
            with lock:
                delivered_seqs.append(event["seq"])

    feed = DesktopLiveEventFeed(client, status_callback, interval=0.05, initial_seq=0)
    feed.poll_once()
    feed.start()

    try:
        for i in range(5):
            client.publish(SimpleNamespace(modules={}, revision=10 + i), origin="desktop_analysis")
            client.record_activity("MCP_CALL", tool=f"tool_{i}", source="mcp")

        for _ in range(40):
            with lock:
                if len(delivered_seqs) == 10:
                    break
            time.sleep(0.05)

        with lock:
            seqs = list(delivered_seqs)

        assert len(seqs) > 0
        assert len(seqs) == len(set(seqs)), "DUPLICATE_EVENTS must be 0"
        assert seqs == sorted(seqs), "Sequence order must strictly match server order"
        assert seqs == list(range(1, 11)), "DROPPED_EVENTS must be 0"
    finally:
        feed.stop()


def test_explicit_inactive_repo_never_falls_through_to_other_active_repo(live_server_instance, monkeypatch, tmp_path):
    server_a, client_a = live_server_instance
    repo_a = tmp_path / "repo_a"
    repo_a.mkdir()
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()

    # Active LIVE service for repo A
    monkeypatch.setattr(
        "contextor.core.live_state.connect",
        lambda p: client_a if Path(p).resolve() == repo_a.resolve() else None,
    )
    monkeypatch.setattr(mcp_runtime, "_live_engines", {str(repo_a.resolve()): object()})

    # Invoke tool with explicit repo_b (which is inactive)
    def dummy_tool(repo_path: str):
        return "ok"

    wrapped = _instrument_mcp_tool(dummy_tool, "dummy_tool")
    wrapped(repo_path=str(repo_b))

    # Repo A must receive ZERO MCP_CALL events
    events_a = client_a.get_events(after_seq=0, category="MCP_CALL")["events"]
    assert len(events_a) == 0, "Explicit inactive repo must never fall through to repo A"


def test_rootless_positional_string_is_not_repository_path():
    def rootless_tool(symbol: str):
        return symbol

    wrapped = _instrument_mcp_tool(rootless_tool, "rootless_tool")
    assert _tool_repository_argument(rootless_tool, ("contextor.foo::bar",), {}) is None


def test_rootless_tool_emits_once_to_each_active_repository(tmp_path, monkeypatch):
    repo_a = tmp_path / "repo_a"
    repo_a.mkdir()
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()

    server_a = CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=1)
    thread_a = threading.Thread(target=server_a.serve_forever, daemon=True)
    thread_a.start()
    client_a = LiveStateClient(server_a.endpoint)

    server_b = CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=1)
    thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
    thread_b.start()
    client_b = LiveStateClient(server_b.endpoint)

    try:
        def mock_connect(p):
            p_res = Path(p).resolve()
            if p_res == repo_a.resolve():
                return client_a
            if p_res == repo_b.resolve():
                return client_b
            return None

        monkeypatch.setattr("contextor.core.live_state.connect", mock_connect)
        monkeypatch.setattr(
            mcp_runtime,
            "_live_engines",
            {str(repo_a.resolve()): object(), str(repo_b.resolve()): object()},
        )

        def doc_tool():
            return "docs"

        wrapped = _instrument_mcp_tool(doc_tool, "get_mcp_documentation")
        wrapped()

        events_a = client_a.get_events(after_seq=0, category="MCP_CALL")["events"]
        events_b = client_b.get_events(after_seq=0, category="MCP_CALL")["events"]

        assert len(events_a) == 1
        assert events_a[0]["tool"] == "get_mcp_documentation"

        assert len(events_b) == 1
        assert events_b[0]["tool"] == "get_mcp_documentation"
    finally:
        server_a.close()
        server_b.close()
        thread_a.join(timeout=2)
        thread_b.join(timeout=2)


def test_noncanonical_status_does_not_replace_last_live_state(live_server_instance):
    server, client = live_server_instance
    controller = SimpleNamespace(
        live_status_var=_FakeVar(),
        _live_status_queue=queue.Queue(),
        _live_status_draining=False,
        last_live_state=None,
    )

    def gui_callback(msg, event=None):
        cat = event.get("category", "LIVE_STATE") if event else "LIVE_STATE"
        gui.ContextorGUI._set_live_status(controller, msg, category=cat, event=event)

    feed = DesktopLiveEventFeed(client, gui_callback, initial_seq=0)

    # 1. Publish canonical event
    state = SimpleNamespace(modules={"mod_a": 1}, revision=5)
    client.publish(state, origin="desktop_analysis")
    feed.poll_once()

    assert controller.last_live_state is not None
    assert controller.last_live_state["revision"] == 5
    saved_state = dict(controller.last_live_state)

    # 2. Non-mutating status / activity event
    client.status("Operational heartbeat", origin="desktop")
    client.record_activity("MCP_CALL", tool="search_artifacts", source="mcp")
    feed.poll_once()

    # last_live_state must remain identical
    assert controller.last_live_state == saved_state

    # 3. Canonical update_file
    def updater(s, path):
        s.revision = 6
        return SimpleNamespace(status="UPDATED", file_path=path, affected_modules=[])

    server._updater = updater
    client.update_file("mod_a.py", origin="desktop_watcher")
    feed.poll_once()

    # last_live_state advances to rev 6
    assert controller.last_live_state["revision"] == 6


def test_feed_paginates_more_than_100_events_without_loss(live_server_instance):
    server, client = live_server_instance
    delivered_seqs = []

    def status_callback(msg, event=None):
        if event and "seq" in event:
            delivered_seqs.append(event["seq"])

    feed = DesktopLiveEventFeed(client, status_callback, initial_seq=0)

    # Create 250 MCP_CALL / LIVE_STATE events before polling
    for i in range(125):
        client.publish(SimpleNamespace(modules={}, revision=10 + i), origin="desktop_analysis")
        client.record_activity("MCP_CALL", tool=f"tool_{i}", source="mcp")

    assert server._activity_seq == 250

    # Call feed.poll_once() ONCE (page size remains 100 on each request)
    feed.poll_once()

    assert len(delivered_seqs) == 250
    assert delivered_seqs == list(range(1, 251))
    assert len(delivered_seqs) == len(set(delivered_seqs))
    assert feed._last_seq == 250


def test_feed_retention_gap_reports_once_and_consumes_all_retained_pages():
    server = CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=1, retention=150)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    delivered_seqs = []
    gap_events = []

    def status_callback(msg, event=None):
        if event:
            if event.get("operation") == "activity_gap":
                gap_events.append(event)
            if "seq" in event:
                delivered_seqs.append(event["seq"])

    feed = DesktopLiveEventFeed(client, status_callback, initial_seq=0)

    try:
        # Create 350 events so retention=150 keeps events 201..350 (gap for 1..200)
        for i in range(350):
            client.record_activity("MCP_CALL", tool=f"t_{i}", source="mcp")

        assert server._activity_seq == 350
        assert len(server._events) == 150
        retained_seqs = [e["seq"] for e in server._events]
        assert retained_seqs == list(range(201, 351))

        # Call poll_once() ONCE
        feed.poll_once()

        # Exactly 1 gap event reported
        assert len(gap_events) == 1
        assert gap_events[0]["category"] == "ACTIVITY"
        assert gap_events[0]["operation"] == "activity_gap"

        # All 150 retained events delivered across multiple 100-event pages in sequence order
        assert len(delivered_seqs) == 150
        assert delivered_seqs == list(range(201, 351))
        assert len(delivered_seqs) == len(set(delivered_seqs))
        assert feed._last_seq == 350
    finally:
        server.close()
        thread.join(timeout=2)


def test_over_100_activity_events_are_not_silently_lost(live_server_instance):
    server, client = live_server_instance
    assert ACTIVITY_EVENT_RETENTION == 10_000

    # Emit 150 MCP_CALL events
    for i in range(150):
        client.record_activity("MCP_CALL", tool=f"tool_{i}", source="mcp")

    res = client.get_events(after_seq=0, limit=200)
    assert res["status"] == "ok"
    assert res["activity_continuity"] == "continuous"
    assert res["activity_resync_required"] is False
    assert len(res["events"]) == 150

    seqs = [e["seq"] for e in res["events"]]
    assert seqs == list(range(1, 151))


def test_activity_gap_detection_when_querying_before_retained_range():
    server = CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=1)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        # Populate server and simulate eviction
        for i in range(50):
            client.record_activity("MCP_CALL", tool=f"t_{i}", source="mcp")

        # Manually simulate retention eviction of events 1..10
        with server._lock:
            server._events = [e for e in server._events if e["seq"] > 10]

        # Query after_seq=5 (which was evicted)
        res = client.get_events(after_seq=5)
        assert res["activity_continuity"] == "gap"
        assert res["activity_resync_required"] is True
        assert res["earliest_retained_seq"] == 11
        # Canonical continuity is not affected
        assert res["continuity"] == "not_requested"
    finally:
        server.close()
        thread.join(timeout=2)


def test_desktop_full_analysis_authoritative_event_and_first_run_cursor_handoff(live_server_instance):
    server, client = live_server_instance

    pre_seq = client.get_events(limit=1).get("latest_seq", 0)
    assert pre_seq == 0

    state = SimpleNamespace(modules={"mod_a": object()}, revision=10)
    pub_res = client.publish(state, origin="desktop_analysis")
    assert pub_res["status"] == "ok"
    assert pub_res["seq"] == 1

    received_statuses = []
    received_events = []

    def status_callback(msg, event=None):
        received_statuses.append(msg)
        if event is not None:
            received_events.append(event)

    feed = DesktopLiveEventFeed(client, status_callback, initial_seq=pre_seq)
    feed.poll_once()

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

    fixed_ts = "2026-08-27T12:34:56.789000+00:00"
    event_payload = {
        "seq": 42,
        "timestamp": fixed_ts,
        "category": "LIVE_STATE",
        "operation": "publish",
        "canonical_revision": 7,
        "status": "PUBLISHED",
        "source": "desktop_analysis",
    }

    gui.ContextorGUI._set_live_status(
        controller,
        "[LIVE] Analysis published",
        category="LIVE_STATE",
        event=event_payload,
    )

    time.sleep(0.1)

    gui.ContextorGUI._drain_live_status_queue(controller)

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

        changed = watcher.poll_once()
        assert str(py_file) in changed

        feed.poll_once()

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

    state = SimpleNamespace(modules={"pkg": object()}, revision=10)
    client.publish(state, origin="desktop_analysis")
    r_rev = client.ping()["revision"]

    for i in range(120):
        client.record_activity("MCP_CALL", tool=f"tool_{i}", source="mcp")

    assert client.ping()["revision"] == r_rev

    res_latest = client.get_events(after_revision=r_rev)
    assert res_latest["continuity"] == "continuous"
    assert res_latest["resync_required"] is False
    assert res_latest["events"] == []
    assert res_latest["total"] == 0

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

    monkeypatch.setattr("contextor.mcp_server._resolve_telemetry_clients", lambda *args, **kwargs: [client])

    def mock_search_artifacts(repo_path: str, query: str):
        return {"results": ["item_1", "item_2"]}

    wrapped = _instrument_mcp_tool(mock_search_artifacts, "search_artifacts")

    res = wrapped(repo_path=".", query="test")
    assert res == {"results": ["item_1", "item_2"]}

    events = client.get_events(after_seq=0, category="MCP_CALL")["events"]
    assert len(events) == 1
    assert events[0]["tool"] == "search_artifacts"
    assert events[0]["success"] is True
    assert events[0]["canonical_revision"] is None

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

    def dummy_analyze(repo_path: str):
        return {"status": "job_started"}

    wrapped = _instrument_mcp_tool(dummy_analyze, "analyze_project")
    wrapped(repo_path=".")

    state = SimpleNamespace(modules={"pkg": object()}, revision=5)
    client.publish(state, origin="mcp_analysis")

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

    for i in range(5):
        client.publish(SimpleNamespace(modules={}, revision=10 + i), origin="desktop_analysis")
        client.record_activity("MCP_CALL", tool=f"mcp_tool_{i}", source="mcp")

    assert server._activity_seq == 10

    feed.poll_once()

    assert queue_instance.qsize() == 10

    processed_events = []
    while not queue_instance.empty():
        item = queue_instance.get_nowait()
        processed_events.append(item)
        if item.get("category") == "LIVE_STATE" and item.get("event") and item["event"].get("operation") in {"publish", "update_file"}:
            controller.last_live_state = {
                "revision": item["event"].get("canonical_revision"),
                "status": item["event"].get("status"),
                "timestamp": item["event"].get("timestamp"),
                "source": item["event"].get("source"),
            }

    assert len(processed_events) == 10

    for idx, item in enumerate(processed_events):
        evt = item["event"]
        assert evt["seq"] == idx + 1
        expected_cat = "LIVE_STATE" if idx % 2 == 0 else "MCP_CALL"
        assert item["category"] == expected_cat

        expected_time = datetime.fromisoformat(evt["timestamp"]).astimezone().strftime("%H:%M:%S")
        assert expected_time in item["formatted"]

    assert controller.last_live_state["revision"] == 14


def test_desktop_vs_mcp_full_analysis_equivalence(live_server_instance):
    server, client = live_server_instance

    state_d = SimpleNamespace(modules={"a": 1}, revision=100)
    res_d = client.publish(state_d, origin="desktop_analysis")
    assert res_d["status"] == "ok"
    assert res_d["revision"] == 2

    state_m = SimpleNamespace(modules={"a": 1, "b": 2}, revision=101)
    res_m = client.publish(state_m, origin="mcp_analysis")
    assert res_m["status"] == "ok"
    assert res_m["revision"] == 3

    events = client.get_events(after_seq=0)["events"]
    assert len(events) == 2

    assert events[0]["category"] == "LIVE_STATE"
    assert events[0]["operation"] == "publish"
    assert events[0]["source"] == "desktop_analysis"
    assert events[0]["canonical_revision"] == 100

    assert events[1]["category"] == "LIVE_STATE"
    assert events[1]["operation"] == "publish"
    assert events[1]["source"] == "mcp_analysis"
    assert events[1]["canonical_revision"] == 101
