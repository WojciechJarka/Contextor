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
16. All 25 registered FastMCP tools coverage & registry synchronization
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


class _ReadOnlyRevisionState:
    @property
    def revision(self):
        return None

    @revision.setter
    def revision(self, value):
        raise AttributeError("read-only property")


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
            client.publish(SimpleNamespace(modules={}, revision=2 + i), origin="desktop_analysis")
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

    # 1. Publish canonical event (successor 2)
    state = SimpleNamespace(modules={"mod_a": 1}, revision=2)
    client.publish(state, origin="desktop_analysis")
    feed.poll_once()

    assert controller.last_live_state is not None
    assert controller.last_live_state["revision"] == 2
    saved_state = dict(controller.last_live_state)

    # 2. Non-mutating status / activity event
    client.status("Operational heartbeat", origin="desktop")
    client.record_activity("MCP_CALL", tool="search_artifacts", source="mcp")
    feed.poll_once()

    # last_live_state must remain identical
    assert controller.last_live_state == saved_state

    # 3. Canonical update_file (advances to rev 3)
    def updater(s, path):
        s.revision = 3
        return SimpleNamespace(status="UPDATED", file_path=path, affected_modules=[])

    server._updater = updater
    client.update_file("mod_a.py", origin="desktop_watcher")
    feed.poll_once()

    # last_live_state advances to rev 3
    assert controller.last_live_state["revision"] == 3


def test_feed_paginates_more_than_100_events_without_loss(live_server_instance):
    server, client = live_server_instance
    delivered_seqs = []

    def status_callback(msg, event=None):
        if event and "seq" in event:
            delivered_seqs.append(event["seq"])

    feed = DesktopLiveEventFeed(client, status_callback, initial_seq=0)

    # Create 250 MCP_CALL / LIVE_STATE events before polling
    for i in range(125):
        client.publish(SimpleNamespace(modules={}, revision=2 + i), origin="desktop_analysis")
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

    state = SimpleNamespace(modules={"mod_a": object()}, revision=2)
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
    assert "(rev 2)" in received_statuses[0]
    assert received_events[0]["canonical_revision"] == 2
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

    state = SimpleNamespace(modules={"pkg": object()}, revision=2)
    client.publish(state, origin="mcp_analysis")

    events = client.get_events(after_seq=0)["events"]
    assert len(events) == 2

    assert events[0]["category"] == "MCP_CALL"
    assert events[0]["tool"] == "analyze_project"
    assert events[0]["canonical_revision"] is None

    assert events[1]["category"] == "LIVE_STATE"
    assert events[1]["operation"] == "publish"
    assert events[1]["source"] == "mcp_analysis"
    assert events[1]["canonical_revision"] == 2


def test_all_25_registered_mcp_tools_telemetry_against_fastmcp_registry(monkeypatch):
    fastmcp_tool_names = set(mcp._tool_manager._tools.keys())
    assert set(REGISTERED_MCP_TOOL_NAMES) == fastmcp_tool_names
    assert len(REGISTERED_MCP_TOOL_NAMES) == 25

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
        client.publish(SimpleNamespace(modules={}, revision=2 + i), origin="desktop_analysis")
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

    assert controller.last_live_state["revision"] == 6
def test_desktop_vs_mcp_full_analysis_equivalence(live_server_instance):
    server, client = live_server_instance

    state_d = SimpleNamespace(modules={"a": 1}, revision=2)
    res_d = client.publish(state_d, origin="desktop_analysis")
    assert res_d["status"] == "ok"
    assert res_d["revision"] == 2

    state_m = SimpleNamespace(modules={"a": 1, "b": 2}, revision=3)
    res_m = client.publish(state_m, origin="mcp_analysis")
    assert res_m["status"] == "ok"
    assert res_m["revision"] == 3

    events = client.get_events(after_seq=0)["events"]
    assert len(events) == 2
    assert events[0]["category"] == "LIVE_STATE"
    assert events[0]["operation"] == "publish"
    assert events[0]["source"] == "desktop_analysis"
    assert events[0]["canonical_revision"] == 2
    assert events[0]["revision"] == 2

    assert events[1]["category"] == "LIVE_STATE"
    assert events[1]["operation"] == "publish"
    assert events[1]["source"] == "mcp_analysis"
    assert events[1]["canonical_revision"] == 3
    assert events[1]["revision"] == 3


def test_canonical_revision_succession_and_noncanonical_invariance():
    """Prove deterministic revision succession:
    read-only MCP telemetry -> R (unchanged)
    ACTIVITY status         -> R (unchanged)
    update_file             -> R+1 everywhere
    MCP_CALL                -> R+1 (unchanged)
    publish                 -> R+2 everywhere
    """
    initial_state = SimpleNamespace(modules={"mod_a": object()}, revision=10)
    server = CanonicalLiveServer(state=initial_state, revision=10)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        # 1. Baseline: R = 10
        assert client.ping()["revision"] == 10
        assert server._state.revision == 10

        # 2. Read-only MCP telemetry -> R = 10
        client.record_activity("MCP_CALL", tool="search_artifacts", source="mcp", success=True)
        assert client.ping()["revision"] == 10
        assert server._state.revision == 10

        # 3. ACTIVITY status -> R = 10
        client.status("Operational heartbeat", origin="desktop")
        assert client.ping()["revision"] == 10
        assert server._state.revision == 10

        # 4. update_file -> R+1 = 11 everywhere
        def mock_updater(s, path):
            s.revision = 11
            return SimpleNamespace(status="UPDATED", file_path=path, affected_modules=[])

        server._updater = mock_updater
        res_upd = client.update_file("src/mod_a.py", origin="desktop_watcher")
        assert res_upd["status"] == "ok"
        assert res_upd["revision"] == 11
        assert client.ping()["revision"] == 11
        assert server._state.revision == 11

        # Check event
        events = client.get_events(after_seq=0)["events"]
        upd_evt = [e for e in events if e.get("operation") == "update_file"][0]
        assert upd_evt["canonical_revision"] == 11
        assert upd_evt["revision"] == 11

        # 5. MCP_CALL -> R+1 = 11
        client.record_activity("MCP_CALL", tool="get_module_context", source="mcp", success=True)
        assert client.ping()["revision"] == 11
        assert server._state.revision == 11

        # 6. publish -> R+2 = 12 everywhere
        new_state = SimpleNamespace(modules={"mod_a": object(), "mod_b": object()}, revision=12)
        res_pub = client.publish(new_state, origin="mcp_analysis")
        assert res_pub["status"] == "ok"
        assert res_pub["revision"] == 12
        assert client.ping()["revision"] == 12
        assert server._state.revision == 12

        pub_events = [e for e in client.get_events(after_seq=0)["events"] if e.get("operation") == "publish"]
        assert len(pub_events) == 1
        assert pub_events[0]["canonical_revision"] == 12
        assert pub_events[0]["revision"] == 12
    finally:
        server.close()
        thread.join(timeout=2)


def test_desktop_and_mcp_consecutive_publish_revision_parity():
    """Verify consecutive publishes from MCP and Desktop:
    before = R
    MCP publish     -> R+1 everywhere
    Desktop publish -> R+2 everywhere
    Only origin/source differs.
    """
    server = CanonicalLiveServer(state=None, revision=50)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        assert client.ping()["revision"] == 50

        # MCP publish -> 51
        state_mcp = SimpleNamespace(modules={"pkg": 1}, revision=51)
        res_mcp = client.publish(state_mcp, origin="mcp_analysis")
        assert res_mcp["status"] == "ok"
        assert res_mcp["revision"] == 51
        assert client.ping()["revision"] == 51
        assert server._state.revision == 51

        # Desktop publish -> 52
        state_dsk = SimpleNamespace(modules={"pkg": 1, "pkg.sub": 2}, revision=52)
        res_dsk = client.publish(state_dsk, origin="desktop_analysis")
        assert res_dsk["status"] == "ok"
        assert res_dsk["revision"] == 52
        assert client.ping()["revision"] == 52
        assert server._state.revision == 52

        events = client.get_events(after_seq=0)["events"]
        assert len(events) == 2
        assert events[0]["source"] == "mcp_analysis"
        assert events[0]["canonical_revision"] == 51
        assert events[0]["revision"] == 51

        assert events[1]["source"] == "desktop_analysis"
        assert events[1]["canonical_revision"] == 52
        assert events[1]["revision"] == 52
    finally:
        server.close()
        thread.join(timeout=2)


def test_canonical_revision_continuity_across_server_restart(tmp_path):
    """Verify revision unification survives daemon restart / reconnect:
    - publish canonical R;
    - reload / restart server;
    - server resumes / binds authoritative R;
    - next canonical mutation becomes correct successor.
    """
    state_v1 = SimpleNamespace(modules={"a": 1}, revision=105)
    server_1 = CanonicalLiveServer(state=state_v1)
    thread_1 = threading.Thread(target=server_1.serve_forever, daemon=True)
    thread_1.start()
    client_1 = LiveStateClient(server_1.endpoint)

    try:
        assert client_1.ping()["revision"] == 105
    finally:
        server_1.close()
        thread_1.join(timeout=2)

    # Server 2 initialized from resumed canonical state
    state_resumed = SimpleNamespace(modules={"a": 1}, revision=105)
    server_2 = CanonicalLiveServer(state=state_resumed)
    thread_2 = threading.Thread(target=server_2.serve_forever, daemon=True)
    thread_2.start()
    client_2 = LiveStateClient(server_2.endpoint)

    try:
        assert client_2.ping()["revision"] == 105

        # Next mutation is R+1 = 106
        state_v2 = SimpleNamespace(modules={"a": 1, "b": 2}, revision=106)
        res = client_2.publish(state_v2, origin="desktop_analysis")
        assert res["status"] == "ok"
        assert res["revision"] == 106
        assert client_2.ping()["revision"] == 106
    finally:
        server_2.close()
        thread_2.join(timeout=2)


def test_strict_canonical_only_after_revision_filtering():
    """Verify after_revision returns strictly canonical mutations, while after_seq returns mixed stream:
    - Baseline R=10
    - Canonical update -> R=11
    - Append MCP_CALL and ACTIVITY status while at R=11
    - get_events(after_revision=10) returns exactly the 1 canonical mutation at R=11 and 0 MCP_CALL / ACTIVITY
    - get_events(after_seq=0) returns all 3 events
    """
    initial_state = SimpleNamespace(modules={"pkg": 1}, revision=10)
    server = CanonicalLiveServer(state=initial_state, revision=10)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        assert client.ping()["revision"] == 10

        # 1. Canonical update -> R=11
        server._updater = lambda s, p: SimpleNamespace(status="UPDATED", file_path=p, revision=11)
        res_upd = client.update_file("pkg/mod.py", origin="desktop_watcher")
        assert res_upd["status"] == "ok"
        assert res_upd["revision"] == 11

        # 2. Append MCP_CALL and ACTIVITY at R=11
        client.record_activity("MCP_CALL", tool="get_module_context", source="mcp", success=True)
        client.status("Daemon heartbeat alive", origin="desktop")

        # Check total events in server
        res_mixed = client.get_events(after_seq=0)
        assert len(res_mixed["events"]) == 3
        categories = [e["category"] for e in res_mixed["events"]]
        assert categories == ["LIVE_STATE", "MCP_CALL", "ACTIVITY"]  # update_file, mcp_call, status

        # 3. Query with after_revision=10
        res_canonical = client.get_events(after_revision=10)
        assert res_canonical["continuity"] == "continuous"
        assert res_canonical["resync_required"] is False
        assert len(res_canonical["events"]) == 1
        assert res_canonical["total"] == 1
        assert res_canonical["events"][0]["operation"] == "update_file"
        assert res_canonical["events"][0]["revision"] == 11

        # Query with after_revision=11 (latest)
        res_latest = client.get_events(after_revision=11)
        assert res_latest["continuity"] == "continuous"
        assert res_latest["resync_required"] is False
        assert len(res_latest["events"]) == 0
        assert res_latest["total"] == 0
    finally:
        server.close()
        thread.join(timeout=2)


def test_fail_closed_against_non_monotonic_and_stale_publish():
    """Verify CanonicalLiveServer enforces exact successor policy (expected = R+1):
    - Current R=11
    - publish 12 -> PASS
    - publish 12 again -> FAIL non_monotonic_canonical_revision
    - publish 11 -> FAIL non_monotonic_canonical_revision
    - publish 14 -> FAIL canonical_revision_discontinuity
    - Prove for all rejected publishes: state, revision, activity_seq unchanged, zero LIVE_STATE event emitted
    """
    initial_state = SimpleNamespace(modules={"pkg": 1}, revision=11, tag="v11")
    server = CanonicalLiveServer(state=initial_state, revision=11)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        assert client.ping()["revision"] == 11

        # 1. Exact successor publish 12 -> PASS
        state_12 = SimpleNamespace(modules={"pkg": 1, "pkg.a": 2}, revision=12, tag="v12")
        res_12 = client.publish(state_12, origin="desktop_analysis")
        assert res_12["status"] == "ok"
        assert res_12["revision"] == 12
        assert client.ping()["revision"] == 12
        assert server._state.tag == "v12"
        assert server._state.revision == 12

        events_before = client.get_events(after_seq=0)["events"]
        assert len(events_before) == 1
        seq_before = events_before[0]["seq"]

        # 2. Equal publish 12 -> FAIL
        state_12_dup = SimpleNamespace(modules={"pkg": 99}, revision=12, tag="v12_dup")
        res_dup = client.publish(state_12_dup, origin="desktop_analysis")
        assert res_dup["status"] == "error"
        assert res_dup["error"] == "non_monotonic_canonical_revision"
        assert res_dup["revision"] == 12
        assert res_dup["candidate_revision"] == 12
        assert res_dup["expected_revision"] == 13

        # State and revision must NOT have changed
        assert server._state.tag == "v12"
        assert server._state.revision == 12
        assert client.ping()["revision"] == 12

        # 3. Stale publish 11 -> FAIL
        state_stale = SimpleNamespace(modules={"pkg": 0}, revision=11, tag="v11_stale")
        res_stale = client.publish(state_stale, origin="mcp_analysis")
        assert res_stale["status"] == "error"
        assert res_stale["error"] == "non_monotonic_canonical_revision"
        assert res_stale["revision"] == 12
        assert res_stale["candidate_revision"] == 11
        assert res_stale["expected_revision"] == 13

        # State and revision must NOT have changed
        assert server._state.tag == "v12"
        assert server._state.revision == 12
        assert client.ping()["revision"] == 12

        # 4. Discontinuous forward publish 14 -> FAIL canonical_revision_discontinuity
        state_gap = SimpleNamespace(modules={"pkg": 100}, revision=14, tag="v14_gap")
        res_gap = client.publish(state_gap, origin="desktop_analysis")
        assert res_gap["status"] == "error"
        assert res_gap["error"] == "canonical_revision_discontinuity"
        assert res_gap["revision"] == 12
        assert res_gap["candidate_revision"] == 14
        assert res_gap["expected_revision"] == 13

        # State and revision must NOT have changed
        assert server._state.tag == "v12"
        assert server._state.revision == 12
        assert client.ping()["revision"] == 12

        # 5. Prove no failed publish emitted any event and activity_seq is unchanged
        events_after = client.get_events(after_seq=0)["events"]
        assert len(events_after) == 1
        assert events_after[0]["seq"] == seq_before
    finally:
        server.close()
        thread.join(timeout=2)


def test_fail_closed_when_state_revision_cannot_be_bound():
    """Verify CanonicalLiveServer fails closed when revision cannot be bound into state:
    - Immutable / frozen state with read-only revision raises on publish without valid revision
    - Constructor raises ValueError on unbindable state
    - Explicit bool revision rejected
    """
    # 1. Constructor fails closed on unbindable state with explicit revision
    with pytest.raises(ValueError, match="Failed to bind explicit canonical revision=5 into state"):
        CanonicalLiveServer(state=_ReadOnlyRevisionState(), revision=5)

    # 2. Constructor fails closed on unbindable state with default revision=0
    with pytest.raises(ValueError, match="Failed to bind default canonical revision=0 into state"):
        CanonicalLiveServer(state=_ReadOnlyRevisionState())

    # 3. Constructor rejects bool revision
    with pytest.raises(ValueError, match="Invalid canonical revision: True"):
        CanonicalLiveServer(state=SimpleNamespace(modules={}, revision=1), revision=True)

    # 4. Publish fails closed when attempting to allocate revision on unbindable state
    server = CanonicalLiveServer(state=None, revision=10)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        res = client.publish(_ReadOnlyRevisionState(), origin="desktop_analysis")
        assert res["status"] == "error"
        assert res["error"] == "canonical_revision_binding_failed"
        assert res["revision"] == 10
        assert res["candidate_revision"] is None

        # Server state remains None, revision remains 10, zero events recorded
        assert client.ping()["revision"] == 10
        assert client.get_events(after_seq=0)["events"] == []
    finally:
        server.close()
        thread.join(timeout=2)


def test_constructor_canonical_revision_parity_and_mismatch_rejection():
    """Verify constructor enforces strict canonical revision parity:
    - State with revision=10 and explicit revision=10 -> matches
    - State with revision=10 and mismatching revision=12 -> raises ValueError
    - State without revision and explicit revision=7 -> sets server=7 and state.revision=7
    - State without revision and no explicit revision -> sets server=0 and state.revision=0
    """
    # 1. Matching state and explicit revision
    state_a = SimpleNamespace(modules={}, revision=10)
    server_a = CanonicalLiveServer(state=state_a, revision=10)
    assert server_a._revision == 10
    assert state_a.revision == 10
    server_a.close()

    # 2. Mismatching explicit revision raises ValueError
    state_b = SimpleNamespace(modules={}, revision=10)
    with pytest.raises(ValueError, match="Constructor canonical revision mismatch: explicit revision=12 != state.revision=10"):
        CanonicalLiveServer(state=state_b, revision=12)

    # 3. State without revision adopts explicit revision
    state_c = SimpleNamespace(modules={})
    server_c = CanonicalLiveServer(state=state_c, revision=7)
    assert server_c._revision == 7
    assert state_c.revision == 7
    server_c.close()

    # 4. State without revision and no explicit revision defaults to 0
    state_d = SimpleNamespace(modules={})
    server_d = CanonicalLiveServer(state=state_d)
    assert server_d._revision == 0
    assert state_d.revision == 0
    server_d.close()


def test_get_events_limit_contract_zero_negative_and_none():
    """Verify CanonicalLiveServer.get_events limit handling:
    - limit=None returns all matching events
    - limit=0 returns empty list with total count preserved and truncated=True
    - limit=-5 returns empty list with total count preserved and truncated=True
    - limit=1 returns first event with truncated=True
    """
    server = CanonicalLiveServer(state=None, revision=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        for i in range(5):
            client.record_activity("MCP_CALL", tool=f"tool_{i}", source="mcp")

        # limit=None -> all 5
        res_none = client.get_events(after_seq=0, limit=None)
        assert len(res_none["events"]) == 5
        assert res_none["total"] == 5
        assert res_none["truncated"] is False

        # limit=0 -> 0 events, total=5, truncated=True
        res_zero = client.get_events(after_seq=0, limit=0)
        assert len(res_zero["events"]) == 0
        assert res_zero["total"] == 5
        assert res_zero["truncated"] is True

        # limit=-5 -> 0 events, total=5, truncated=True
        res_neg = client.get_events(after_seq=0, limit=-5)
        assert len(res_neg["events"]) == 0
        assert res_neg["total"] == 5
        assert res_neg["truncated"] is True

        # limit=2 -> 2 events, total=5, truncated=True
        res_two = client.get_events(after_seq=0, limit=2)
        assert len(res_two["events"]) == 2
        assert res_two["total"] == 5
        assert res_two["truncated"] is True
    finally:
        server.close()
        thread.join(timeout=2)


def test_update_file_exact_successor_and_fail_closed_regressions():
    """Verify update_file exact successor and fail-closed binding behavior:
    A. Current R=10, updater leaves state.revision=10: succeeds, binds state revision 11, server 11, event rev 11.
    B. Current R=10, updater sets state.revision=11: succeeds, parity everywhere 11.
    C. Current R=10, updater sets state.revision=15: fails canonical_revision_discontinuity, server remains 10, zero event.
    D. Unbindable/read-only current state where updater leaves revision unchanged: fails canonical_revision_binding_failed, server unchanged, zero event.
    """
    # A. Current R=10, updater leaves revision=10 unchanged -> server binds R=11
    state_a = SimpleNamespace(modules={"a": 1}, revision=10)
    server_a = CanonicalLiveServer(state=state_a, revision=10, updater=lambda s, p: SimpleNamespace(status="UPDATED", file_path=p))
    thread_a = threading.Thread(target=server_a.serve_forever, daemon=True)
    thread_a.start()
    client_a = LiveStateClient(server_a.endpoint)

    try:
        res_a = client_a.update_file("src/a.py", origin="desktop_watcher")
        assert res_a["status"] == "ok"
        assert res_a["revision"] == 11
        assert server_a._revision == 11
        assert server_a._state.revision == 11
        assert state_a.revision == 10
        assert client_a.ping()["revision"] == 11

        events_a = client_a.get_events(after_seq=0)["events"]
        assert len(events_a) == 1
        assert events_a[0]["canonical_revision"] == 11
        assert events_a[0]["revision"] == 11
    finally:
        server_a.close()
        thread_a.join(timeout=2)

    # B. Current R=10, updater sets state.revision=11 -> succeeds with parity 11
    state_b = SimpleNamespace(modules={"b": 1}, revision=10)
    def updater_b(s, p):
        s.revision = 11
        return SimpleNamespace(status="UPDATED", file_path=p)

    server_b = CanonicalLiveServer(state=state_b, revision=10, updater=updater_b)
    thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
    thread_b.start()
    client_b = LiveStateClient(server_b.endpoint)

    try:
        res_b = client_b.update_file("src/b.py", origin="mcp")
        assert res_b["status"] == "ok"
        assert res_b["revision"] == 11
        assert server_b._revision == 11
        assert server_b._state.revision == 11
        assert state_b.revision == 10

        events_b = client_b.get_events(after_seq=0)["events"]
        assert len(events_b) == 1
        assert events_b[0]["canonical_revision"] == 11
    finally:
        server_b.close()
        thread_b.join(timeout=2)

    # C. Current R=10, updater sets state.revision=15 (discontinuous jump) -> fails canonical_revision_discontinuity
    state_c = SimpleNamespace(modules={"c": 1}, revision=10, tag="v10")
    def updater_c(s, p):
        s.revision = 15
        return SimpleNamespace(status="UPDATED", file_path=p)

    server_c = CanonicalLiveServer(state=state_c, revision=10, updater=updater_c)
    thread_c = threading.Thread(target=server_c.serve_forever, daemon=True)
    thread_c.start()
    client_c = LiveStateClient(server_c.endpoint)

    try:
        res_c = client_c.update_file("src/c.py", origin="desktop_watcher")
        assert res_c["status"] == "error"
        assert res_c["error"] == "canonical_revision_discontinuity"
        assert res_c["revision"] == 10
        assert res_c["candidate_revision"] == 15
        assert res_c["expected_revision"] == 11

        # Server revision remains 10, zero LIVE_STATE events emitted
        assert server_c._revision == 10
        assert client_c.ping()["revision"] == 10
        assert client_c.get_events(after_seq=0)["events"] == []
    finally:
        server_c.close()
        thread_c.join(timeout=2)

    # D. Unbindable/read-only current state where updater leaves revision unchanged -> fails canonical_revision_binding_failed
    class _CustomReadOnlyState:
        def __init__(self):
            self._rev = 10
        @property
        def revision(self):
            return self._rev
        @revision.setter
        def revision(self, val):
            raise AttributeError("read-only revision")

    state_d = _CustomReadOnlyState()
    # Constructor succeeds since state.revision == 10 matches explicit revision 10
    server_d = CanonicalLiveServer(state=state_d, revision=10, updater=lambda s, p: SimpleNamespace(status="UPDATED", file_path=p))
    thread_d = threading.Thread(target=server_d.serve_forever, daemon=True)
    thread_d.start()
    client_d = LiveStateClient(server_d.endpoint)

    try:
        res_d = client_d.update_file("src/d.py", origin="desktop_watcher")
        assert res_d["status"] == "error"
        assert res_d["error"] == "canonical_revision_binding_failed"
        assert res_d["revision"] == 10
        assert res_d["candidate_revision"] == 10
        assert res_d["expected_revision"] == 11

        # Server revision remains unchanged (10), zero LIVE_STATE events emitted
        assert server_d._revision == 10
        assert client_d.ping()["revision"] == 10
        assert client_d.get_events(after_seq=0)["events"] == []
    finally:
        server_d.close()
        thread_d.join(timeout=2)


def test_invalid_explicit_and_state_revision_rejection():
    """Verify constructor and publish reject invalid explicit or state revision types (bool, negative, string):
    - Constructor rejects revision=True, revision=-1, state.revision=True, state.revision="5"
    - Publish rejects candidates with revision=True, revision=-1, revision="11"
    - For every case: server revision unchanged, active state unchanged, zero canonical event emitted
    """
    # 1. Constructor invalid explicit revision rejection
    with pytest.raises(ValueError, match="Invalid canonical revision: True"):
        CanonicalLiveServer(SimpleNamespace(), revision=True)

    with pytest.raises(ValueError, match="Invalid canonical revision: False"):
        CanonicalLiveServer(SimpleNamespace(), revision=False)

    with pytest.raises(ValueError, match="Invalid canonical revision: -1"):
        CanonicalLiveServer(SimpleNamespace(), revision=-1)

    with pytest.raises(ValueError, match="Invalid canonical revision: '5'"):
        CanonicalLiveServer(SimpleNamespace(), revision="5")

    with pytest.raises(ValueError, match="Invalid canonical revision: 1.5"):
        CanonicalLiveServer(SimpleNamespace(), revision=1.5)

    # 2. Constructor invalid state revision rejection
    with pytest.raises(ValueError, match="Invalid canonical state revision: True"):
        CanonicalLiveServer(SimpleNamespace(revision=True))

    with pytest.raises(ValueError, match="Invalid canonical state revision: False"):
        CanonicalLiveServer(SimpleNamespace(revision=False))

    with pytest.raises(ValueError, match="Invalid canonical state revision: '5'"):
        CanonicalLiveServer(SimpleNamespace(revision="5"))

    with pytest.raises(ValueError, match="Invalid canonical state revision: -1"):
        CanonicalLiveServer(SimpleNamespace(revision=-1))

    # 3. Publish invalid candidate revision rejection against server R=10
    initial_state = SimpleNamespace(modules={"mod": 1}, revision=10, tag="v10")
    server = CanonicalLiveServer(state=initial_state, revision=10)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        assert client.ping()["revision"] == 10

        # Case A: candidate with revision=True
        res_true = client.publish(SimpleNamespace(revision=True), origin="desktop_analysis")
        assert res_true["status"] == "error"
        assert res_true["error"] == "invalid_canonical_revision"
        assert res_true["revision"] == 10
        assert res_true["candidate_revision"] is True
        assert server._state.tag == "v10"
        assert server._revision == 10
        assert client.ping()["revision"] == 10
        assert client.get_events(after_seq=0)["events"] == []

        # Case B: candidate with revision=-1
        res_neg = client.publish(SimpleNamespace(revision=-1), origin="desktop_analysis")
        assert res_neg["status"] == "error"
        assert res_neg["error"] == "invalid_canonical_revision"
        assert res_neg["revision"] == 10
        assert res_neg["candidate_revision"] == -1
        assert server._state.tag == "v10"
        assert server._revision == 10
        assert client.ping()["revision"] == 10
        assert client.get_events(after_seq=0)["events"] == []

        # Case C: candidate with revision="11"
        res_str = client.publish(SimpleNamespace(revision="11"), origin="desktop_analysis")
        assert res_str["status"] == "error"
        assert res_str["error"] == "invalid_canonical_revision"
        assert res_str["revision"] == 10
        assert res_str["candidate_revision"] == "11"
        assert server._state.tag == "v10"
        assert server._revision == 10
        assert client.ping()["revision"] == 10
        assert client.get_events(after_seq=0)["events"] == []
    finally:
        server.close()
        thread.join(timeout=2)


def test_update_file_forward_gap_rolls_back_entire_candidate_state():
    state = SimpleNamespace(
        revision=10,
        modules={"original": 1},
        marker="original",
    )

    def updater(candidate, path):
        candidate.modules["bad"] = 2
        candidate.marker = "mutated"
        candidate.revision = 15
        return SimpleNamespace(
            status="UPDATED",
            file_path=path,
        )

    server = CanonicalLiveServer(
        state=state,
        revision=10,
        updater=updater,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        pre_seq = server._activity_seq

        res = client.update_file(
            "src/a.py",
            origin="desktop_watcher",
        )

        assert res["status"] == "error"
        assert res["error"] == "canonical_revision_discontinuity"
        assert res["revision"] == 10
        assert res["candidate_revision"] == 15
        assert res["expected_revision"] == 11

        assert server._state is state
        assert server._revision == 10
        assert server._state.revision == 10
        assert server._state.modules == {"original": 1}
        assert server._state.marker == "original"

        assert state.revision == 10
        assert state.modules == {"original": 1}
        assert state.marker == "original"

        assert server._activity_seq == pre_seq
        assert client.get_events(after_seq=0)["events"] == []
    finally:
        server.close()
        thread.join(timeout=2)


def test_update_file_invalid_revision_rolls_back_entire_candidate_state():
    state = SimpleNamespace(
        revision=10,
        modules={"original": 1},
        marker="original",
    )

    def updater(candidate, path):
        candidate.modules["bad"] = 2
        candidate.marker = "mutated"
        candidate.revision = True
        return SimpleNamespace(
            status="UPDATED",
            file_path=path,
        )

    server = CanonicalLiveServer(
        state=state,
        revision=10,
        updater=updater,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        pre_seq = server._activity_seq

        res = client.update_file(
            "src/a.py",
            origin="desktop_watcher",
        )

        assert res["status"] == "error"
        assert res["error"] == "invalid_canonical_revision"
        assert res["revision"] == 10

        assert server._state is state
        assert server._revision == 10
        assert state.revision == 10
        assert state.modules == {"original": 1}
        assert state.marker == "original"

        assert server._activity_seq == pre_seq
        assert client.get_events(after_seq=0)["events"] == []
    finally:
        server.close()
        thread.join(timeout=2)


def test_update_file_updater_exception_cannot_mutate_active_state():
    state = SimpleNamespace(
        revision=10,
        modules={"original": 1},
        marker="original",
    )

    def updater(candidate, path):
        candidate.modules["bad"] = 2
        candidate.marker = "mutated"
        candidate.revision = 11
        raise RuntimeError("synthetic updater failure")

    server = CanonicalLiveServer(
        state=state,
        revision=10,
        updater=updater,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        pre_seq = server._activity_seq

        try:
            client.update_file(
                "src/a.py",
                origin="desktop_watcher",
            )
        except Exception:
            pass

        assert server._state is state
        assert server._revision == 10
        assert state.revision == 10
        assert state.modules == {"original": 1}
        assert state.marker == "original"
        assert server._activity_seq == pre_seq
        assert client.get_events(after_seq=0)["events"] == []
    finally:
        server.close()
        thread.join(timeout=2)


def test_update_file_success_commits_candidate_atomically():
    state = SimpleNamespace(
        revision=10,
        modules={"original": 1},
        marker="original",
    )

    def updater(candidate, path):
        candidate.modules["new"] = 2
        candidate.marker = "updated"
        candidate.revision = 11
        return SimpleNamespace(
            status="UPDATED",
            file_path=path,
        )

    server = CanonicalLiveServer(
        state=state,
        revision=10,
        updater=updater,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        res = client.update_file(
            "src/a.py",
            origin="desktop_watcher",
        )

        assert res["status"] == "ok"
        assert res["revision"] == 11

        # Active canonical ownership changed to detached committed candidate.
        assert server._state is not state
        assert server._revision == 11
        assert server._state.revision == 11
        assert server._state.modules == {
            "original": 1,
            "new": 2,
        }
        assert server._state.marker == "updated"

        # Previous active state was never mutated.
        assert state.revision == 10
        assert state.modules == {"original": 1}
        assert state.marker == "original"

        events = client.get_events(after_seq=0)["events"]
        assert len(events) == 1
        assert events[0]["operation"] == "update_file"
        assert events[0]["canonical_revision"] == 11
        assert events[0]["revision"] == 11
    finally:
        server.close()
        thread.join(timeout=2)


def test_update_file_server_binds_successor_on_candidate_then_commits():
    state = SimpleNamespace(
        revision=10,
        modules={"original": 1},
    )

    def updater(candidate, path):
        candidate.modules["new"] = 2
        # Intentionally leave candidate.revision == 10.
        return SimpleNamespace(
            status="UPDATED",
            file_path=path,
        )

    server = CanonicalLiveServer(
        state=state,
        revision=10,
        updater=updater,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        res = client.update_file(
            "src/a.py",
            origin="desktop_watcher",
        )

        assert res["status"] == "ok"
        assert res["revision"] == 11
        assert server._state is not state
        assert server._state.revision == 11
        assert server._state.modules == {
            "original": 1,
            "new": 2,
        }

        assert state.revision == 10
        assert state.modules == {"original": 1}

        events = client.get_events(after_seq=0)["events"]
        assert len(events) == 1
        assert events[0]["canonical_revision"] == 11
        assert events[0]["revision"] == 11
    finally:
        server.close()
        thread.join(timeout=2)


def test_publish_explicit_zero_revision_is_not_treated_as_missing():
    # 1. Server R=10, explicit candidate revision=0
    active = SimpleNamespace(
        revision=10,
        marker="active",
    )

    server = CanonicalLiveServer(
        state=active,
        revision=10,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    client = LiveStateClient(server.endpoint)

    try:
        candidate = SimpleNamespace(
            revision=0,
            marker="candidate",
        )

        res = client.publish(
            candidate,
            origin="desktop_analysis",
        )

        assert res["status"] == "error"
        assert res["error"] == "non_monotonic_canonical_revision"
        assert res["revision"] == 10
        assert res["candidate_revision"] == 0
        assert res["expected_revision"] == 11

        assert server._state is active
        assert server._revision == 10
        assert active.revision == 10
        assert active.marker == "active"
        assert candidate.revision == 0

        assert client.get_events(after_seq=0)["events"] == []
    finally:
        server.close()
        thread.join(timeout=2)

    # 2. Server R=0, explicit candidate revision=0
    active_zero = SimpleNamespace(
        revision=0,
        marker="active_zero",
    )
    server_zero = CanonicalLiveServer(
        state=active_zero,
        revision=0,
    )
    thread_zero = threading.Thread(
        target=server_zero.serve_forever,
        daemon=True,
    )
    thread_zero.start()
    client_zero = LiveStateClient(server_zero.endpoint)

    try:
        candidate_zero = SimpleNamespace(
            revision=0,
            marker="candidate_zero",
        )

        res = client_zero.publish(
            candidate_zero,
            origin="desktop_analysis",
        )

        assert res["status"] == "error"
        assert res["error"] == "non_monotonic_canonical_revision"
        assert res["revision"] == 0
        assert res["candidate_revision"] == 0
        assert res["expected_revision"] == 1

        assert server_zero._state is active_zero
        assert server_zero._revision == 0
        assert active_zero.revision == 0
        assert active_zero.marker == "active_zero"
        assert candidate_zero.revision == 0

        assert client_zero.get_events(after_seq=0)["events"] == []
    finally:
        server_zero.close()
        thread_zero.join(timeout=2)



