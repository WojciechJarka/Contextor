"""Tests for Desktop GUI LIVE startup retry hardening."""

from queue import Queue
from types import SimpleNamespace
from unittest.mock import MagicMock
import threading
import time

import pytest

from contextor.core.live_state import connect_or_start
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
        _start_backend_owner_claim=MagicMock(),
        _live_start_retry_attempt=0,
        _live_start_retry_after_id=None,
        _closing=False,
        _live_start_lock=threading.Lock(),
        _live_start_inflight=set(),
        _live_start_threads={},
        repo_id_var=_GuiFakeVar("Repo ID: unregistered"),
        repo_path_var=_GuiFakeVar(str(repo_path)),
        _selected_live_repo_path=str(repo_path),
        layer_path_var=_GuiFakeVar(""),
        file_path_var=_GuiFakeVar(""),
        theme_mode="light",
        _set_live_status=lambda msg: statuses.append(msg),
        _events=events,
        _statuses=statuses,
    )
    return controller


def test_selected_live_repository_predicate_does_not_read_tk_variable(tmp_path):
    selected = tmp_path / "selected"
    other = tmp_path / "other"
    selected.mkdir()
    other.mkdir()

    def forbidden_get():
        raise AssertionError("worker predicate must not read Tk/StringVar")

    controller = SimpleNamespace(
        _selected_live_repo_path=str(selected),
        repo_path_var=SimpleNamespace(get=forbidden_get),
    )

    assert ContextorGUI._is_selected_live_repository(controller, str(selected)) is True
    assert ContextorGUI._is_selected_live_repository(controller, str(other)) is False


def _wait_for_live_start(controller, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with controller._live_start_lock:
            threads = list(controller._live_start_threads.values())
        if not threads:
            return
        for thread in threads:
            thread.join(timeout=0.05)
    raise AssertionError("LIVE startup background thread did not finish")


def test_public_live_start_returns_before_blocking_connect_finishes(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    controller = _make_controller(repo)
    connect_entered, allow_connect = threading.Event(), threading.Event()

    class Client:
        def publish(self, *_args, **_kwargs): pass
    class Watcher:
        def __init__(self, *_args, **_kwargs): self.started = False
        def start(self): self.started = True
    class Feed:
        def __init__(self, *_args, **_kwargs): pass
        def start(self): pass
    def connect(*_args, **_kwargs):
        connect_entered.set()
        assert allow_connect.wait(timeout=5)
        return Client()
    monkeypatch.setattr(gui, "connect_or_start", connect)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
    monkeypatch.setattr("contextor.core.analysis.state_manager.load_engine_state", lambda *_a, **_k: None)
    started = time.monotonic()
    ContextorGUI._start_live_watcher(controller, str(repo))
    assert time.monotonic() - started < 0.25
    assert connect_entered.wait(timeout=2)
    assert controller.live_watcher is None
    allow_connect.set()
    _wait_for_live_start(controller)
    assert controller.live_watcher.started is True


def test_duplicate_public_start_while_inflight_creates_one_worker(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    controller = _make_controller(repo)
    entered, allow = threading.Event(), threading.Event()
    calls = 0
    def connect(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        entered.set()
        assert allow.wait(timeout=5)
        return SimpleNamespace()
    monkeypatch.setattr(gui, "connect_or_start", connect)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", lambda *_a, **_k: SimpleNamespace(start=lambda: None))
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", lambda *_a, **_k: SimpleNamespace(start=lambda: None))
    monkeypatch.setattr("contextor.core.analysis.state_manager.load_engine_state", lambda *_a, **_k: None)
    ContextorGUI._start_live_watcher(controller, str(repo))
    assert entered.wait(timeout=2)
    ContextorGUI._start_live_watcher(controller, str(repo))
    with controller._live_start_lock:
        assert len(controller._live_start_inflight) == len(controller._live_start_threads) == 1
    assert calls == 1
    allow.set()
    _wait_for_live_start(controller)
    assert calls == 1


def test_closing_prevents_new_background_live_start(tmp_path, monkeypatch):
    controller = _make_controller(tmp_path)
    controller._closing = True
    connect = MagicMock()
    monkeypatch.setattr(gui, "connect_or_start", connect)
    ContextorGUI._start_live_watcher(controller, str(tmp_path))
    connect.assert_not_called()
    assert controller._live_start_inflight == set()
    assert controller._live_start_threads == {}


def test_post_paint_tasks_do_not_wait_for_cache_cleanup(tmp_path, monkeypatch):
    controller = _make_controller("")
    entered, allow = threading.Event(), threading.Event()
    thread_ids = []
    def cleanup():
        thread_ids.append(threading.get_ident())
        entered.set()
        assert allow.wait(timeout=5)
        return {"cache": {"errors": []}}
    monkeypatch.setattr(gui, "prune_startup_caches", cleanup)
    controller._check_stale_excludes = MagicMock()
    controller._start_live_watcher = MagicMock()
    main_id = threading.get_ident()
    started = time.monotonic()
    ContextorGUI._start_post_paint_tasks(controller)
    assert time.monotonic() - started < 0.25
    controller._start_backend_owner_claim.assert_called_once_with()
    assert entered.wait(timeout=2)
    assert thread_ids[0] != main_id
    allow.set()


def test_initial_success(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    registry = PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _make_controller(repo, root)

    class Client:
        def publish(self, state, *, origin="unknown"):
            return {"status": "ok"}

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

    ContextorGUI._start_live_watcher_blocking(controller, str(repo))

    assert mock_connect.call_count == 1
    assert len(watcher_instances) == 1
    assert watcher_instances[0].started is True
    assert controller.live_watcher is watcher_instances[0]
    assert controller._live_start_retry_attempt == 0
    assert controller._live_start_retry_after_id is None
    assert len(root.scheduled) == 0


def test_second_desktop_is_rejected_before_gui_cache_touch(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
    desktop_a = connect_or_start(repo, client_kind="desktop", desktop_instance_id="desktop-a")
    controller = _make_controller(repo)
    controller.desktop_instance_id = "desktop-b"
    watcher_instances = []

    class Watcher:
        def __init__(self, *args, **kwargs):
            watcher_instances.append(self)

        def start(self):
            pass

    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(
        gui,
        "migrate_legacy_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("cache touched before admission")
        ),
    )
    try:
        ContextorGUI._start_live_watcher_blocking(controller, str(repo))
        assert watcher_instances == []
        assert controller.live_watcher is None
        assert any("already active" in status for status in controller._statuses)
    finally:
        try:
            desktop_a.request("shutdown", timeout=1.0)
        except Exception:
            pass


def test_timeout_then_success(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _make_controller(repo, root)

    class Client:
        def publish(self, state, *, origin="unknown"):
            return {"status": "ok"}

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
    ContextorGUI._start_live_watcher_blocking(controller, str(repo))

    assert attempts == 1
    assert len(watcher_instances) == 0
    assert controller._live_start_retry_attempt == 1
    assert controller._live_start_retry_after_id is not None
    assert any("retrying (2/4)" in s for s in controller._statuses)
    assert not any("LIVE connection error:" in s for s in controller._statuses)

    # Execute scheduled retry callback
    executed = root.run_next_scheduled()
    assert executed is True
    _wait_for_live_start(controller)
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
            return {"status": "ok"}

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

    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
    assert len(connect_calls) == 1
    assert controller._live_start_retry_after_id is not None

    root.run_next_scheduled()
    _wait_for_live_start(controller)
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
    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
    assert attempts == 1

    # Run all retries until exhaustion
    run_count = 0
    while root.run_next_scheduled():
        run_count += 1
        _wait_for_live_start(controller)
    assert attempts == LIVE_START_MAX_ATTEMPTS
    assert run_count >= LIVE_START_MAX_ATTEMPTS - 1
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
    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
    assert connect_count == 1
    assert controller._live_start_retry_after_id is not None
    pending_timer = controller._live_start_retry_after_id

    # Simulate that an active watcher was established by another operation
    existing_watcher = SimpleNamespace(start=lambda: None, stop=lambda: None)
    controller.live_watchers[registry.repo_id] = existing_watcher

    # Now execute the stale retry callback
    ContextorGUI._start_live_watcher_blocking(controller, str(repo))

    # connect_or_start must NOT be called again
    assert connect_count == 1
    assert controller.live_watcher is existing_watcher
    assert pending_timer in root.cancelled
    assert controller._live_start_retry_after_id is None
    assert controller._live_start_retry_attempt == 0


def test_reselecting_existing_watcher_restores_client_feed_and_status(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    registry = PersistentIdentityRegistry(str(repo))
    controller = _make_controller(repo)
    existing_watcher = SimpleNamespace()
    existing_client = SimpleNamespace(name="existing-client")
    existing_feed = SimpleNamespace(client=existing_client)
    controller.live_watchers[registry.repo_id] = existing_watcher
    controller.live_event_feeds[registry.repo_id] = existing_feed
    controller.live_clients[registry.repo_id] = existing_client
    controller.live_watcher = SimpleNamespace(name="stale-watcher")
    controller.live_event_feed = SimpleNamespace(name="stale-feed")
    controller.live_client = SimpleNamespace(name="stale-client")
    connect_calls = []
    monkeypatch.setattr(
        gui,
        "connect_or_start",
        lambda *args, **kwargs: connect_calls.append((args, kwargs)),
    )

    ContextorGUI._start_live_watcher_blocking(controller, str(repo))

    assert connect_calls == []
    assert controller.live_client is existing_client
    assert controller.live_watcher is existing_watcher
    assert controller.live_event_feed is existing_feed
    assert controller._statuses == [
        f"[{repo.name}] LIVE: shared state attached; watcher active"
    ]


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
    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
    assert controller._live_start_retry_after_id is not None
    scheduled_id = controller._live_start_retry_after_id

    # GUI close handler
    ContextorGUI.on_closing(controller)

    assert scheduled_id in root.cancelled
    assert controller._live_start_retry_after_id is None
    assert controller._live_start_retry_attempt == 0
    assert root.destroyed is True



def _bind_recovery_prompt(controller):
    controller.analyze = MagicMock()
    controller._live_recovery_queue = Queue()
    controller._live_recovery_prompt_pending = set()
    controller._live_recovery_lock = threading.Lock()
    controller._request_full_analysis_recovery = (
        lambda path, reason: ContextorGUI._request_full_analysis_recovery(
            controller, path, reason
        )
    )
    controller._drain_live_recovery_queue = (
        lambda: ContextorGUI._drain_live_recovery_queue(controller)
    )
    return controller


def test_generation_conflict_schedules_one_recovery_prompt(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    loaded = SimpleNamespace(revision=7, state_id="loaded-generation")
    remote = SimpleNamespace(revision=7, state_id="remote-generation")
    ask = MagicMock(return_value=False)

    class Client:
        def snapshot(self):
            return {"state": remote, "revision": 7}

        def publish(self, *_args, **_kwargs):
            raise AssertionError("generation conflict must not publish")

    monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
    monkeypatch.setattr(gui, "migrate_legacy_snapshot", lambda *_a: tmp_path / "cache")
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_a, **_k: loaded,
    )
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)

    ContextorGUI._start_live_watcher_blocking(controller, str(repo))
    ContextorGUI._start_live_watcher_blocking(controller, str(repo))

    assert controller._statuses.count(
        "LIVE: generation conflict; analysis required"
    ) == 2
    assert controller._live_recovery_queue.qsize() == 1
    assert root.scheduled == {}
    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
    ask.assert_not_called()
    controller.analyze.assert_not_called()


def test_recovery_prompt_decline_preserves_incident(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    ask = MagicMock(return_value=False)
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)

    ContextorGUI._request_full_analysis_recovery(
        controller, str(repo), "Canonical state identity mismatch."
    )
    assert controller._live_recovery_queue.qsize() == 1
    ContextorGUI._drain_live_recovery_queue(controller)

    ask.assert_called_once()
    assert ask.call_args.kwargs["parent"] is root
    assert "Canonical state identity mismatch." in ask.call_args.args[1]
    controller.analyze.assert_not_called()
    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}

    ContextorGUI._request_full_analysis_recovery(
        controller, str(repo), "Canonical state identity mismatch."
    )
    assert controller._live_recovery_queue.qsize() == 0
    assert next(iter(root.scheduled.values()))[0] == 100
    ask.assert_called_once()


def test_recovery_prompt_accept_runs_existing_analyze_once(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    ask = MagicMock(return_value=True)
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)

    ContextorGUI._request_full_analysis_recovery(
        controller, str(repo), "Canonical state identity mismatch."
    )
    assert controller._live_recovery_queue.qsize() == 1
    ContextorGUI._drain_live_recovery_queue(controller)

    ask.assert_called_once()
    controller.analyze.assert_called_once_with()
    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
    assert controller._live_recovery_queue.qsize() == 0
    assert next(iter(root.scheduled.values()))[0] == 100

    ContextorGUI._request_full_analysis_recovery(
        controller, str(repo), "Canonical state identity mismatch."
    )
    assert controller._live_recovery_queue.qsize() == 0
    controller.analyze.assert_called_once_with()


def test_recovery_prompt_failed_analysis_preserves_incident(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    controller.analyze.side_effect = RuntimeError("analysis failed")
    ask = MagicMock(return_value=True)
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)

    ContextorGUI._request_full_analysis_recovery(
        controller, str(repo), "Canonical state identity mismatch."
    )
    with pytest.raises(RuntimeError, match="analysis failed"):
        ContextorGUI._drain_live_recovery_queue(controller)

    ask.assert_called_once()
    controller.analyze.assert_called_once_with()
    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
    assert controller._live_recovery_queue.qsize() == 0


def test_recovery_prompt_suppressed_after_desktop_closes(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    ask = MagicMock()
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)

    ContextorGUI._request_full_analysis_recovery(
        controller, str(repo), "Canonical state identity mismatch."
    )
    controller._closing = True
    assert controller._live_recovery_queue.qsize() == 1
    ContextorGUI._drain_live_recovery_queue(controller)

    ask.assert_not_called()
    controller.analyze.assert_not_called()
    assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
    assert controller._live_recovery_queue.qsize() == 1
    assert root.scheduled == {}


def test_recovery_prompt_suppressed_after_repository_switch(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    repo.mkdir()
    other.mkdir()
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    ask = MagicMock()
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)

    ContextorGUI._request_full_analysis_recovery(
        controller, str(repo), "Canonical state identity mismatch."
    )
    controller._selected_live_repo_path = str(other)
    assert controller._live_recovery_queue.qsize() == 1
    ContextorGUI._drain_live_recovery_queue(controller)

    ask.assert_not_called()
    controller.analyze.assert_not_called()
    assert controller._live_recovery_prompt_pending == set()
    assert controller._live_recovery_queue.qsize() == 0
    assert next(iter(root.scheduled.values()))[0] == 100


def test_live_connection_retry_does_not_prompt_for_recovery(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    ask = MagicMock()
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
    monkeypatch.setattr(
        gui, "connect_or_start",
        lambda *_a, **_k: (_ for _ in ()).throw(TimeoutError("transient")),
    )

    ContextorGUI._start_live_watcher_blocking(controller, str(repo))

    assert controller._live_start_retry_attempt == 1
    assert len(root.scheduled) == 1
    assert next(iter(root.scheduled.values()))[0] == LIVE_START_RETRY_DELAYS_MS[0]
    assert controller._live_recovery_prompt_pending == set()
    assert controller._live_recovery_queue.qsize() == 0
    ask.assert_not_called()
    controller.analyze.assert_not_called()


def test_rejected_startup_publication_schedules_recovery_prompt(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    loaded = SimpleNamespace(revision=7, state_id="loaded-generation")
    remote = SimpleNamespace(revision=6, state_id="remote-generation")
    ask = MagicMock(return_value=False)
    released = []

    class Client:
        def snapshot(self):
            return {"state": remote, "revision": 6}

        def publish(self, *_args, **_kwargs):
            return {
                "status": "error",
                "error": "canonical_revision_discontinuity",
                "revision": 6,
                "expected_revision": 7,
            }

    class Watcher:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

    class Feed:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
    monkeypatch.setattr(gui, "migrate_legacy_snapshot", lambda *_a: tmp_path / "cache")
    monkeypatch.setattr(gui, "acquire_full_analysis", lambda *_a, **_k: object())
    monkeypatch.setattr(gui, "release_full_analysis", released.append)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_a, **_k: loaded,
    )

    ContextorGUI._start_live_watcher_blocking(controller, str(repo))

    assert released and len(released) == 1
    assert "LIVE: shared state attach failed; analysis required" in controller._statuses
    assert controller._live_recovery_queue.qsize() == 1
    assert root.scheduled == {}
    ContextorGUI._drain_live_recovery_queue(controller)
    assert ask.call_args.args[1].endswith(
        "Reason: Canonical LIVE consistency error: canonical_revision_discontinuity.\n\n"
        "Run a full repository analysis now?"
    )
    assert next(iter(root.scheduled.values()))[0] == 100
    controller.analyze.assert_not_called()



def test_recovery_request_from_worker_uses_queue_without_tk(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    main_thread = threading.get_ident()
    original_after = root.after
    after_threads = []
    dialog_threads = []

    def checked_after(delay_ms, callback):
        after_threads.append(threading.get_ident())
        assert threading.get_ident() == main_thread
        return original_after(delay_ms, callback)

    def checked_dialog(*_args, **_kwargs):
        dialog_threads.append(threading.get_ident())
        assert threading.get_ident() == main_thread
        return False

    root.after = checked_after
    monkeypatch.setattr(gui.messagebox, "askyesno", checked_dialog)
    worker = threading.Thread(
        target=ContextorGUI._request_full_analysis_recovery,
        args=(controller, str(repo), "Canonical state identity mismatch."),
    )
    worker.start()
    worker.join(5)

    assert not worker.is_alive()
    assert controller._live_recovery_queue.qsize() == 1
    assert root.scheduled == {}
    assert after_threads == []
    assert dialog_threads == []

    ContextorGUI._drain_live_recovery_queue(controller)
    assert dialog_threads == [main_thread]
    assert after_threads == [main_thread]
    assert next(iter(root.scheduled.values()))[0] == 100
    controller.analyze.assert_not_called()


@pytest.mark.parametrize(
    ("response", "expected_reason"),
    [
        (
            {"status": "error", "error": "non_monotonic_canonical_revision"},
            None,
        ),
        (
            {"status": "error", "error": "daemon_busy"},
            None,
        ),
        (
            {
                "status": "error",
                "error": "canonical_persistence_revision_conflict",
                "resync_required": True,
            },
            "Canonical LIVE consistency error: canonical_persistence_revision_conflict.",
        ),
    ],
)
def test_startup_publication_error_recovery_classification(
    tmp_path, monkeypatch, response, expected_reason
):
    repo = tmp_path / "repo"
    repo.mkdir()
    PersistentIdentityRegistry(str(repo))
    root = MockTkRoot()
    controller = _bind_recovery_prompt(_make_controller(repo, root))
    loaded = SimpleNamespace(revision=7, state_id="loaded-generation")
    remote = SimpleNamespace(revision=6, state_id="remote-generation")
    ask = MagicMock(return_value=False)
    released = []

    class Client:
        def snapshot(self):
            return {"state": remote, "revision": 6}

        def publish(self, *_args, **_kwargs):
            return response

    class Watcher:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

    class Feed:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(gui, "connect_or_start", lambda *_a, **_k: Client())
    monkeypatch.setattr(gui, "migrate_legacy_snapshot", lambda *_a: tmp_path / "cache")
    monkeypatch.setattr(gui, "acquire_full_analysis", lambda *_a, **_k: object())
    monkeypatch.setattr(gui, "release_full_analysis", released.append)
    monkeypatch.setattr(gui, "DesktopLiveWatcher", Watcher)
    monkeypatch.setattr(gui, "DesktopLiveEventFeed", Feed)
    monkeypatch.setattr(gui.messagebox, "askyesno", ask)
    monkeypatch.setattr(
        "contextor.core.analysis.state_manager.load_engine_state",
        lambda *_a, **_k: loaded,
    )

    ContextorGUI._start_live_watcher_blocking(controller, str(repo))

    assert len(released) == 1
    assert "LIVE: shared state attach failed; analysis required" in controller._statuses
    if expected_reason is None:
        assert controller._live_recovery_queue.qsize() == 0
        assert controller._live_recovery_prompt_pending == set()
        assert root.scheduled == {}
        ask.assert_not_called()
    else:
        assert controller._live_recovery_queue.qsize() == 1
        assert controller._live_recovery_prompt_pending == {str(repo.resolve())}
        assert root.scheduled == {}
        ContextorGUI._drain_live_recovery_queue(controller)
        assert expected_reason in ask.call_args.args[1]
        assert next(iter(root.scheduled.values()))[0] == 100
    controller.analyze.assert_not_called()
