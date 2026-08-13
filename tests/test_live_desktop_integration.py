"""Desktop adapter tests for publishing and watching shared canonical LIVE state."""

from types import SimpleNamespace

import pytest

from contextor.ui import gui

pytestmark = pytest.mark.live


def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    state = SimpleNamespace(modules={"current": object()})
    events = []

    class Client:
        def publish(self, published, *, origin="unknown"):
            events.append(("publish", published, origin))

    class Watcher:
        def __init__(self, root, client):
            events.append(("watcher", root, client))

        def start(self):
            events.append(("start",))

        def stop(self):
            events.append(("stop-new",))

    old_watcher = SimpleNamespace(stop=lambda: events.append(("stop-old",)))
    controller = SimpleNamespace(live_watcher=old_watcher)
    monkeypatch.setattr(gui, "connect_or_start", lambda _path: Client())
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_args: state,
    )

    gui.ContextorGUI._start_live_watcher(controller, str(repo))

    assert events[0] == ("stop-old",)
    assert events[1] == ("publish", state, "desktop_analysis")
    assert events[-1] == ("start",)
    assert isinstance(controller.live_watcher, Watcher)


def test_desktop_starts_uninitialized_watcher_without_publishing(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    events = []

    class Watcher:
        def __init__(self, _root, _client):
            pass

        def start(self):
            events.append("started")

    client = SimpleNamespace(publish=lambda _state: events.append("published"))
    controller = SimpleNamespace(live_watcher=None)
    monkeypatch.setattr(gui, "connect_or_start", lambda _path: client)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_args: None,
    )

    gui.ContextorGUI._start_live_watcher(controller, str(repo))

    assert events == ["started"]
