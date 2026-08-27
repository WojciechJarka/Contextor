"""Tests for Desktop GUI LIVE startup retry hardening."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.ui import gui
from contextor.ui.gui import (
    LIVE_START_MAX_ATTEMPTS,
    LIVE_START_RETRY_DELAYS_MS,
    ContextorGUI,
)

pytestmark = pytest.mark.live


class _GuiFakeVar:
    def __init__(self, initial=""):
        self.value = initial

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class MockTkRoot:
    def __init__(self):
        self.scheduled = {}
        self.cancelled = []
        self._next_id = 1
        self.destroyed = False

    def after(self, delay_ms, callback):
        after_id = f"timer_{self._next_id}"
        self._next_id += 1
        self.scheduled[after_id] = (delay_ms, callback)
        return after_id

    def after_cancel(self, after_id):
        self.cancelled.append(after_id)
        self.scheduled.pop(after_id, None)

    def run_next_scheduled(self):
        if not self.scheduled:
            return False
        first_key = next(iter(self.scheduled))
        _, callback = self.scheduled.pop(first_key)
        callback()
        return True

    def run_all_scheduled(self):
        count = 0
        while self.run_next_scheduled():
            count += 1
        return count

    def geometry(self):
        return "800x600+50+50"

    def destroy(self):
        self.destroyed = True


def _make_controller(repo_path, root=None):
    root = root or MockTkRoot()
    events = []
    statuses = []
    controller = SimpleNamespace(
        root=root,
        live_watcher=None,
        live_event_feed=None,
        live_watchers={},
        live_event_feeds={},
        live_clients={},
        live_client=None,
        owner_token="test-owner-token",
        _live_start_retry_attempt=0,
        _live_start_retry_after_id=None,
        repo_id_var=_GuiFakeVar("Repo ID: unregistered"),
        repo_path_var=_GuiFakeVar(str(repo_path)),
        layer_path_var=_GuiFakeVar(""),
        file_path_var=_GuiFakeVar(""),
        theme_mode="light",
        _set_live_status=lambda msg: statuses.append(msg),
        _events=events,
        _statuses=statuses,
    )
    return controller


def test_initial_success(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    registry = PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _make_controller(repo, root)

    class Client:
        def publish(self, state, *, origin="unknown"):
            pass

    watcher_instances = []

    class Watcher:
        def __init__(self, root_path, client, **kwargs):
            self.root_path = root_path
            self.client = client
            self.started = False
            watcher_instances.append(self)

        def start(self):
            self.started = True

        def stop(self):
            self.started = False

    class EventFeed:
        def __init__(self, client, on_status):
            self.started = False

        def start(self):
            self.started = True

        def stop(self):
            self.started = False

    mock_connect = MagicMock(return_value=Client())
    monkeypatch.setattr(gui, "connect_or_start", mock_connect)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *args, **kwargs: SimpleNamespace(modules={}),
    )

    ContextorGUI._start_live_watcher(controller, str(repo))

    assert mock_connect.call_count == 1
    assert len(watcher_instances) == 1
    assert watcher_instances[0].started is True
    assert controller.live_watcher is watcher_instances[0]
    assert controller._live_start_retry_attempt == 0
    assert controller._live_start_retry_after_id is None
    assert len(root.scheduled) == 0


def test_timeout_then_success(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _make_controller(repo, root)

    class Client:
        def publish(self, state, *, origin="unknown"):
            pass

    watcher_instances = []

    class Watcher:
        def __init__(self, root_path, client, **kwargs):
            self.started = False
            watcher_instances.append(self)

        def start(self):
            self.started = True

        def stop(self):
            self.started = False

    class EventFeed:
        def __init__(self, client, on_status):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    attempts = 0

    def mock_connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError(f"Canonical LIVE service did not start for {repo}")
        return Client()

    monkeypatch.setattr(gui, "connect_or_start", mock_connect)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *args, **kwargs: SimpleNamespace(modules={}),
    )

    # First attempt: triggers TimeoutError and schedules retry
    ContextorGUI._start_live_watcher(controller, str(repo))

    assert attempts == 1
    assert len(watcher_instances) == 0
    assert controller._live_start_retry_attempt == 1
    assert controller._live_start_retry_after_id is not None
    assert any("retrying (2/4)" in s for s in controller._statuses)
    assert not any("LIVE connection error:" in s for s in controller._statuses)

    # Execute scheduled retry callback
    executed = root.run_next_scheduled()
    assert executed is True
    assert attempts == 2
    assert len(watcher_instances) == 1
    assert watcher_instances[0].started is True
    assert controller._live_start_retry_attempt == 0
    assert controller._live_start_retry_after_id is None
    assert not any("LIVE connection error:" in s for s in controller._statuses)


def test_late_service_connection(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _make_controller(repo, root)

    connect_calls = []

    class Client:
        def publish(self, state, *, origin="unknown"):
            pass

    def mock_connect_or_start(path, *, owner_pid=None, owner_token=None):
        connect_calls.append((path, owner_pid, owner_token))
        if len(connect_calls) == 1:
            raise TimeoutError("timeout")
        return Client()

    class Watcher:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    class EventFeed:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    monkeypatch.setattr(gui, "connect_or_start", mock_connect_or_start)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", EventFeed)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *args, **kwargs: SimpleNamespace(modules={}),
    )

    ContextorGUI._start_live_watcher(controller, str(repo))
    assert len(connect_calls) == 1
    assert controller._live_start_retry_after_id is not None

    root.run_next_scheduled()
    assert len(connect_calls) == 2
    assert connect_calls[1] == (str(repo), controller.owner_token and None or connect_calls[0][1], controller.owner_token)
    assert controller.live_client is not None
    assert controller._live_start_retry_after_id is None


def test_all_attempts_fail_cleanly(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _make_controller(repo, root)

    attempts = 0

    def always_timeout(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        raise TimeoutError(f"Canonical LIVE service did not start for {repo}")

    watcher_created = False

    class Watcher:
        def __init__(self, *args, **kwargs):
            nonlocal watcher_created
            watcher_created = True

        def start(self):
            pass

        def stop(self):
            pass

    monkeypatch.setattr(gui, "connect_or_start", always_timeout)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)

    # Initial call
    ContextorGUI._start_live_watcher(controller, str(repo))
    assert attempts == 1

    # Run all retries until exhaustion
    run_count = root.run_all_scheduled()
    assert attempts == LIVE_START_MAX_ATTEMPTS
    assert run_count == LIVE_START_MAX_ATTEMPTS - 1
    assert watcher_created is False
    assert controller.live_watcher is None
    assert controller._live_start_retry_after_id is None
    assert controller._live_start_retry_attempt == 0

    final_errors = [s for s in controller._statuses if "LIVE connection error:" in s]
    assert len(final_errors) == 1
    assert "Canonical LIVE service did not start" in final_errors[0]


def test_duplicate_watcher_prevented(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    registry = PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _make_controller(repo, root)

    connect_count = 0

    def mock_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        raise TimeoutError("timeout")

    monkeypatch.setattr(gui, "connect_or_start", mock_connect)

    # First attempt fails and schedules retry
    ContextorGUI._start_live_watcher(controller, str(repo))
    assert connect_count == 1
    assert controller._live_start_retry_after_id is not None
    pending_timer = controller._live_start_retry_after_id

    # Simulate that an active watcher was established by another operation
    existing_watcher = SimpleNamespace(start=lambda: None, stop=lambda: None)
    controller.live_watchers[registry.repo_id] = existing_watcher

    # Now execute the stale retry callback
    ContextorGUI._start_live_watcher(controller, str(repo))

    # connect_or_start must NOT be called again
    assert connect_count == 1
    assert controller.live_watcher is existing_watcher
    assert pending_timer in root.cancelled
    assert controller._live_start_retry_after_id is None
    assert controller._live_start_retry_attempt == 0


def test_shutdown_cancels_pending_retry(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _make_controller(repo, root)

    def mock_connect(*args, **kwargs):
        raise TimeoutError("timeout")

    monkeypatch.setattr(gui, "connect_or_start", mock_connect)
    monkeypatch.setattr(gui, "save_state", lambda **payload: None)

    # Initial call sets a pending retry timer
    ContextorGUI._start_live_watcher(controller, str(repo))
    assert controller._live_start_retry_after_id is not None
    scheduled_id = controller._live_start_retry_after_id

    # GUI close handler
    ContextorGUI.on_closing(controller)

    assert scheduled_id in root.cancelled
    assert controller._live_start_retry_after_id is None
    assert controller._live_start_retry_attempt == 0
    assert root.destroyed is True
