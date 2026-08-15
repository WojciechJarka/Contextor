"""Desktop adapter tests for publishing and watching shared canonical LIVE state."""

from types import SimpleNamespace

import pytest

from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.repository_identity import read_repository_identity
from contextor.ui import gui

pytestmark = pytest.mark.live


class FakeVar:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


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
        def __init__(self, root, client, *, on_status=None):
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
        repo_id_var=FakeVar(),
        _set_live_status=lambda message: events.append(("status", message)),
    )
    monkeypatch.setattr(gui, "connect_or_start", lambda _path: Client())
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
        def __init__(self, _root, _client, *, on_status=None):
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
        repo_id_var=FakeVar(),
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
        repo_path_var=FakeVar(),
        layer_path_var=FakeVar(),
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
        def __init__(self, root, _client, *, on_status=None):
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
        repo_id_var=FakeVar(),
        _set_live_status=lambda message: events.append(("status", message)),
    )
    monkeypatch.setattr(gui, "connect_or_start", lambda _path: Client())
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
