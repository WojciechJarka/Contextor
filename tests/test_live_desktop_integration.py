"""Desktop adapter tests for publishing and watching shared canonical LIVE state."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from contextor.core.live_state.watcher import DesktopLiveWatcher
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.repository_identity import read_repository_identity
from contextor.ui import gui

pytestmark = pytest.mark.live


class _LiveIntegrationFakeVar:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


def test_same_revision_startup_attaches_without_redundant_publish(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    state = SimpleNamespace(modules={}, revision=7, state_id="same-generation")
    events = []

    class Client:
        def ping(self):
            return {"revision": 7, "available": True}

        def snapshot(self):
            return {"state": state, "revision": 7}

        def publish(self, *_args, **_kwargs):
            events.append("publish")

    class Watcher:
        def __init__(self, *_args, **_kwargs): pass
        def start(self): pass

    class Feed:
        def __init__(self, *_args, **_kwargs): pass
        def start(self): pass

    statuses = []
    statuses = []
    controller = SimpleNamespace(
        live_watcher=None, live_event_feed=None, live_watchers={},
        live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
        _set_live_status=statuses.append,
    )
    monkeypatch.setattr(gui, "connect_or_start", lambda *_args, **_kwargs: Client())
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_args, **_kwargs: state,
    )

    gui.ContextorGUI._start_live_watcher(controller, str(repo))

    assert events == []
    assert "LIVE: shared state attached; watcher active" in statuses


def test_same_revision_different_state_id_does_not_attach_as_same_generation(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    loaded = SimpleNamespace(modules={}, revision=7, state_id="loaded-generation")
    remote = SimpleNamespace(modules={}, revision=7, state_id="remote-generation")
    events = []
    statuses = []

    class Client:
        def snapshot(self):
            return {"state": remote, "revision": 7}

        def publish(self, *_args, **_kwargs):
            events.append("publish")

    class Watcher:
        def __init__(self, *_args, **_kwargs): pass
        def start(self): pass

    class Feed:
        def __init__(self, *_args, **_kwargs): pass
        def start(self): pass

    controller = SimpleNamespace(
        live_watcher=None, live_event_feed=None, live_watchers={},
        live_event_feeds={}, repo_id_var=_LiveIntegrationFakeVar(),
        _set_live_status=statuses.append,
    )
    monkeypatch.setattr(gui, "connect_or_start", lambda *_args, **_kwargs: Client())
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_args, **_kwargs: loaded,
    )

    gui.ContextorGUI._start_live_watcher(controller, str(repo))

    assert events == []
    assert "LIVE: generation conflict; analysis required" in statuses


def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    registry = PersistentIdentityRegistry(str(repo))
    state = SimpleNamespace(modules={"current": object()})
    events = []

    class Client:
        def publish(self, published, *, origin="unknown"):
            events.append(("publish", published, origin))

    class Watcher:
        def __init__(self, root, client, *, on_status=None, **_kwargs):
            events.append(("watcher", root, client, on_status))

        def start(self):
            events.append(("start",))

        def stop(self):
            events.append(("stop-new",))

    class EventFeed:
        def __init__(self, _client, _on_status):
            events.append(("feed",))

        def start(self):
            events.append(("feed-start",))

        def stop(self):
            events.append(("feed-stop",))

    controller = SimpleNamespace(
        live_watcher=None,
        live_event_feed=None,
        live_watchers={},
        live_event_feeds={},
        repo_id_var=_LiveIntegrationFakeVar(),
        _set_live_status=lambda message: events.append(("status", message)),
    )
    monkeypatch.setattr(gui, "connect_or_start", lambda *args, **kwargs: Client())
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_args, **_kwargs: state,
    )

    gui.ContextorGUI._start_live_watcher(controller, str(repo))

    assert events[0] == ("publish", state, "desktop_analysis")
    assert events[-2:] == [("start",), ("feed-start",)]
    assert isinstance(controller.live_watcher, Watcher)
    assert controller.live_watchers == {registry.repo_id: controller.live_watcher}
    assert controller.repo_id_var.value == f"Repo ID: {registry.repo_id}"


def test_desktop_refuses_live_for_unregistered_repository(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    events = []

    class Watcher:
        def __init__(self, _root, _client, *, on_status=None, **_kwargs):
            pass

        def start(self):
            events.append("started")

    class EventFeed:
        def __init__(self, _client, _on_status):
            pass

        def start(self):
            events.append("feed-started")

        def stop(self):
            pass

    client = SimpleNamespace(publish=lambda _state: events.append("published"))
    controller = SimpleNamespace(
        live_watcher=None,
        live_event_feed=None,
        live_watchers={},
        live_event_feeds={},
        repo_id_var=_LiveIntegrationFakeVar(),
        _set_live_status=lambda message: events.append(("status", message)),
    )
    monkeypatch.setattr(gui, "connect_or_start", lambda _path: client)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_args, **_kwargs: None,
    )

    gui.ContextorGUI._start_live_watcher(controller, str(repo))

    assert events == [
        ("status", "LIVE: repository not registered; run an analysis"),
    ]
    assert controller.repo_id_var.value == "Repo ID: unregistered"


def test_browse_repository_switches_live_to_selected_registered_repo(
    tmp_path, monkeypatch
):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    PersistentIdentityRegistry(str(first))
    second_registry = PersistentIdentityRegistry(str(second))
    calls = []

    controller = SimpleNamespace(
        repo_path_var=_LiveIntegrationFakeVar(),
        layer_path_var=_LiveIntegrationFakeVar(),
        _start_live_watcher=lambda path: calls.append(path),
    )
    monkeypatch.setattr(gui.filedialog, "askdirectory", lambda: str(second))
    monkeypatch.setattr(gui, "save_state", lambda **payload: calls.append(payload))

    gui.ContextorGUI.browse_repository(controller)

    selected = str(second).replace("\\", "/")
    assert controller.repo_path_var.value == selected
    assert controller.layer_path_var.value == ""
    assert calls == [{"repository": selected}, selected]
    assert second_registry.repo_id != read_repository_identity(first).repo_id


def test_switching_repositories_keeps_previous_watcher_active(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_registry = PersistentIdentityRegistry(str(first))
    second_registry = PersistentIdentityRegistry(str(second))
    events = []

    class Client:
        def publish(self, _state, *, origin="unknown"):
            events.append(("publish", origin))

    class Watcher:
        def __init__(self, root, _client, *, on_status=None, **_kwargs):
            self.root = str(root)
            self.on_status = on_status

        def start(self):
            events.append(("start", self.root))

        def stop(self):
            events.append(("stop", self.root))

    class EventFeed:
        def __init__(self, _client, _on_status):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    controller = SimpleNamespace(
        live_watcher=None,
        live_event_feed=None,
        live_watchers={},
        live_event_feeds={},
        repo_id_var=_LiveIntegrationFakeVar(),
        _set_live_status=lambda message: events.append(("status", message)),
    )
    monkeypatch.setattr(gui, "connect_or_start", lambda *args, **kwargs: Client())
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_args, **_kwargs: SimpleNamespace(modules={}),
    )

    gui.ContextorGUI._start_live_watcher(controller, str(first))
    first_watcher = controller.live_watchers[first_registry.repo_id]
    gui.ContextorGUI._start_live_watcher(controller, str(second))

    assert controller.live_watchers == {
        first_registry.repo_id: first_watcher,
        second_registry.repo_id: controller.live_watcher,
    }
    assert not [event for event in events if event[0] == "stop"]
    assert len([event for event in events if event[0] == "start"]) == 2


def test_closing_gui_stops_every_repository_watcher_and_feed(monkeypatch):
    stopped = []

    def component(name):
        return SimpleNamespace(stop=lambda: stopped.append(name))

    root = SimpleNamespace(
        geometry=lambda: "900x700+10+20",
        destroy=lambda: stopped.append("root"),
    )
    controller = SimpleNamespace(
        root=root,
        live_watchers={"ctx_a": component("watcher-a"), "ctx_b": component("watcher-b")},
        live_event_feeds={"ctx_a": component("feed-a"), "ctx_b": component("feed-b")},
        theme_mode="dark",
        repo_path_var=SimpleNamespace(get=lambda: "A"),
        layer_path_var=SimpleNamespace(get=lambda: ""),
        file_path_var=SimpleNamespace(get=lambda: ""),
    )
    monkeypatch.setattr(gui, "save_state", lambda **_payload: None)

    gui.ContextorGUI.on_closing(controller)

    assert stopped == ["watcher-a", "watcher-b", "feed-a", "feed-b", "root"]


@pytest.mark.parametrize("operation", ["layer", "single"])
def test_scoped_analysis_success_refreshes_repository_live_identity(
    tmp_path, monkeypatch, operation
):
    repo = tmp_path / "repo"
    layer = repo / "pkg"
    repo.mkdir()
    layer.mkdir()
    target = layer / "module.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    started = []

    def run_immediately(_root, _progress, task, *, on_success, **_kwargs):
        on_success(task())

    monkeypatch.setattr(gui, "run_with_progress", run_immediately)
    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *_args: None)
    monkeypatch.setattr(
        gui.ContextorFacade,
        "analyze_layer",
        lambda *_args, **_kwargs: "layer-output",
    )
    monkeypatch.setattr(
        gui.ContextorFacade,
        "analyze_single_file",
        lambda *_args, **_kwargs: "single-output",
    )
    controller = SimpleNamespace(
        root=object(),
        progress_bar=SimpleNamespace(is_cancelled=False),
        log_box=object(),
        cpu_indicator=object(),
        stop_btn=object(),
        repo_path_var=SimpleNamespace(get=lambda: str(repo)),
        layer_path_var=SimpleNamespace(get=lambda: str(layer)),
        file_path_var=SimpleNamespace(get=lambda: str(target)),
        _busy_buttons=lambda: [],
        _start_live_watcher=lambda path: started.append(str(path)),
    )

    if operation == "layer":
        gui.ContextorGUI.analyze_layer(controller)
    else:
        gui.ContextorGUI.analyze_single(controller)

    assert started == [str(repo.resolve()) if operation == "layer" else str(repo)]


def test_closing_gui_shuts_down_owned_live_client(monkeypatch):
    events = []
    token = "test-gui-owner-token"
    client = SimpleNamespace(
        is_owner=True,
        owner_token=token,
        service_pid=12345,
        request=lambda op, **_kw: events.append(("request", op)),
    )
    root = SimpleNamespace(
        geometry=lambda: "900x700+10+20",
        destroy=lambda: events.append(("destroy",)),
    )
    controller = SimpleNamespace(
        root=root,
        owner_token=token,
        live_clients={"repo_1": client},
        live_client=client,
        live_watchers={},
        live_event_feeds={},
        theme_mode="dark",
        repo_path_var=SimpleNamespace(get=lambda: "A"),
        layer_path_var=SimpleNamespace(get=lambda: ""),
        file_path_var=SimpleNamespace(get=lambda: ""),
    )
    monkeypatch.setattr(gui, "save_state", lambda **_payload: None)
    monkeypatch.setattr("contextor.core.live_state.runtime._is_pid_alive", lambda _pid: False)

    gui.ContextorGUI.on_closing(controller)
    assert events == [("request", "shutdown"), ("destroy",)]


def test_closing_gui_does_not_shut_down_unowned_live_client(monkeypatch):
    events = []
    token = "test-gui-owner-token"
    client = SimpleNamespace(
        is_owner=False,
        owner_token=token,
        service_pid=12345,
        request=lambda op, **_kw: events.append(("request", op)),
    )
    root = SimpleNamespace(
        geometry=lambda: "900x700+10+20",
        destroy=lambda: events.append(("destroy",)),
    )
    controller = SimpleNamespace(
        root=root,
        owner_token=token,
        live_clients={"repo_1": client},
        live_client=client,
        live_watchers={},
        live_event_feeds={},
        theme_mode="dark",
        repo_path_var=SimpleNamespace(get=lambda: "A"),
        layer_path_var=SimpleNamespace(get=lambda: ""),
        file_path_var=SimpleNamespace(get=lambda: ""),
    )
    monkeypatch.setattr(gui, "save_state", lambda **_payload: None)

    gui.ContextorGUI.on_closing(controller)
    # Since is_owner is False, no shutdown request must be sent!
    assert events == [("destroy",)]


def test_closing_gui_with_missing_owner_token_does_not_shut_down_client(monkeypatch):
    events = []
    # Client has is_owner=True but owner_token=None
    client = SimpleNamespace(
        is_owner=True,
        owner_token=None,
        service_pid=12345,
        request=lambda op, **_kw: events.append(("request", op)),
    )
    root = SimpleNamespace(
        geometry=lambda: "900x700+10+20",
        destroy=lambda: events.append(("destroy",)),
    )
    controller = SimpleNamespace(
        root=root,
        owner_token="test-gui-owner-token",
        live_clients={"repo_1": client},
        live_client=client,
        live_watchers={},
        live_event_feeds={},
        theme_mode="dark",
        repo_path_var=SimpleNamespace(get=lambda: "A"),
        layer_path_var=SimpleNamespace(get=lambda: ""),
        file_path_var=SimpleNamespace(get=lambda: ""),
    )
    monkeypatch.setattr(gui, "save_state", lambda **_payload: None)

    gui.ContextorGUI.on_closing(controller)
    # Missing client owner_token must NOT trigger shutdown
    assert events == [("destroy",)]


def test_closing_gui_with_mismatched_owner_token_does_not_shut_down_client(monkeypatch):
    events = []
    # Client has is_owner=True but token does not match GUI's token
    client = SimpleNamespace(
        is_owner=True,
        owner_token="different-token",
        service_pid=12345,
        request=lambda op, **_kw: events.append(("request", op)),
    )
    root = SimpleNamespace(
        geometry=lambda: "900x700+10+20",
        destroy=lambda: events.append(("destroy",)),
    )
    controller = SimpleNamespace(
        root=root,
        owner_token="test-gui-owner-token",
        live_clients={"repo_1": client},
        live_client=client,
        live_watchers={},
        live_event_feeds={},
        theme_mode="dark",
        repo_path_var=SimpleNamespace(get=lambda: "A"),
        layer_path_var=SimpleNamespace(get=lambda: ""),
        file_path_var=SimpleNamespace(get=lambda: ""),
    )
    monkeypatch.setattr(gui, "save_state", lambda **_payload: None)

    gui.ContextorGUI.on_closing(controller)
    # Mismatched owner_token must NOT trigger shutdown
    assert events == [("destroy",)]


def test_desktop_watcher_recovers_after_live_service_death(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    py_file = repo / "sample.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    status_events = []
    reconnect_events = []

    # Mock client 1 that dies on ping
    dead_client = MagicMock()
    dead_client.ping.side_effect = ConnectionRefusedError("LIVE service connection lost")

    # Mock client 2 that succeeds
    recovered_client = MagicMock()
    recovered_client.ping.return_value = {"status": "ok", "available": True}
    recovered_client.snapshot.return_value = {"status": "ok"}
    recovered_client.update_file.return_value = {"status": "ok", "result": SimpleNamespace(status="UPDATED")}

    def on_reconnect(client):
        reconnect_events.append(client)

    watcher = DesktopLiveWatcher(
        repo,
        dead_client,
        owner_pid=111,
        owner_token="gui-token-xyz",
        on_status=lambda msg: status_events.append(msg),
        on_reconnect=on_reconnect,
    )

    recovery_called = []

    def mock_recover():
        recovery_called.append(True)
        watcher.client = recovered_client
        if watcher.on_reconnect:
            watcher.on_reconnect(recovered_client)
        return recovered_client

    watcher._recover_client = mock_recover
    watcher._trusted_file_state = lambda _snapshot: object()
    watcher._candidate_requires_update = lambda _path, _current: True

    # Modify file so that watcher detects a change
    py_file.write_text("x = 2000\n", encoding="utf-8")

    # poll_once should recover and succeed
    changed = watcher.poll_once()

    assert len(recovery_called) == 1
    assert len(reconnect_events) == 1
    assert reconnect_events[0] == recovered_client
    assert watcher.client == recovered_client
    assert str(py_file) in changed


def test_desktop_watcher_recovery_preserves_unowned_if_another_service_wins_race(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    dead_client = MagicMock()
    dead_client.ping.side_effect = ConnectionResetError("Connection reset")

    external_client = MagicMock()
    external_client.ping.return_value = {"status": "ok", "available": False}
    external_client.is_owner = False
    external_client.owner_token = "other-token-999"

    reconnected_clients = []

    watcher = DesktopLiveWatcher(
        repo,
        dead_client,
        owner_pid=111,
        owner_token="gui-token-xyz",
        on_reconnect=lambda c: reconnected_clients.append(c),
    )

    def mock_recover():
        watcher.client = external_client
        if watcher.on_reconnect:
            watcher.on_reconnect(external_client)
        return external_client

    watcher._recover_client = mock_recover

    res = watcher.poll_once()
    assert res == []
    assert len(reconnected_clients) == 1
    assert reconnected_clients[0].is_owner is False
    assert reconnected_clients[0].owner_token == "other-token-999"


def test_desktop_watcher_syntax_error_does_not_trigger_recovery(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    py_file = repo / "bad.py"
    py_file.write_text("def (\n", encoding="utf-8")

    live_client = MagicMock()
    live_client.ping.return_value = {"status": "ok", "available": True}
    live_client.update_file.return_value = {
        "status": "ok",
        "result": SimpleNamespace(
            status="SYNTAX_ERROR",
            line_number=1,
            column_number=5,
            error="invalid syntax",
        ),
    }

    recovery_called = []
    watcher = DesktopLiveWatcher(
        repo,
        live_client,
        owner_pid=111,
        owner_token="gui-token-xyz",
    )
    watcher._recover_client = lambda: recovery_called.append(True)
    watcher._candidate_requires_update = lambda *_args: True

    status_messages = []
    watcher.on_status = lambda msg: status_messages.append(msg)

    # Initial scan
    watcher._snapshot = {}
    changed = watcher.poll_once()

    assert str(py_file) in changed
    assert len(recovery_called) == 0
    assert any("syntax error" in msg.lower() for msg in status_messages)
