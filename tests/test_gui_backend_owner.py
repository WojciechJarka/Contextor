import threading
import time
from types import SimpleNamespace

import pytest

from contextor.mcp_backend_control import (
    BackendOwnerAlreadyClaimed,
    BackendOwnerInstanceRevoked,
)
from contextor.ui import gui


def _record(instance_id, pid=100, creation_time=1000):
    return SimpleNamespace(
        instance_id=instance_id,
        pid=pid,
        creation_time=creation_time,
    )


def _status(state, ready=False, record=None):
    return SimpleNamespace(
        state=state,
        ready=ready,
        record=record,
    )


def _controller():
    status_calls = []
    controller = SimpleNamespace(
        desktop_instance_id="desktop-instance",
        backend_owner_token="backend-owner-token",
        backend_owner_claim=None,
        _backend_owner_claim_error=None,
        _backend_owner_claim_thread=None,
        _backend_owner_claim_state="idle",
        _backend_owner_claim_attempt=0,
        _closing=False,
        _status_calls=status_calls,
        _set_live_status=lambda *args, **kwargs: status_calls.append(
            (args, kwargs)
        ),
    )
    controller._claim_current_backend_for_desktop = lambda: (
        gui.ContextorGUI._claim_current_backend_for_desktop(controller)
    )
    return controller


def _fast_retry_clock(monkeypatch, controller=None):
    clock = [0.0]
    sleeps = []

    def monotonic():
        return clock[0]

    def sleep(delay):
        sleeps.append(delay)
        if controller is not None:
            controller._closing = True
            clock[0] += 10.0
        else:
            clock[0] += delay

    monkeypatch.setattr(gui.time, "monotonic", monotonic)
    monkeypatch.setattr(gui.time, "sleep", sleep)
    return clock, sleeps


def _published_statuses(controller):
    return [
        (args[0], kwargs)
        for args, kwargs in controller._status_calls
    ]


class _FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def trace_add(self, *_args):
        return "trace-id"


class _FakeRoot:
    def title(self, *_args):
        pass

    def minsize(self, *_args):
        pass

    def geometry(self, *_args):
        pass

    def protocol(self, *_args):
        pass

    def after(self, *_args):
        pass


def test_init_creates_separate_live_and_backend_owner_identities(monkeypatch):
    monkeypatch.setattr(
        gui,
        "load_state",
        lambda: {
            "gui_pos": "",
            "theme": "light",
            "repository": "",
            "layer": "",
            "python_file": "",
        },
    )
    monkeypatch.setattr(gui.tk, "StringVar", _FakeVar)
    monkeypatch.setattr(gui, "apply_theme", lambda *_args: None)
    monkeypatch.setattr(gui.ContextorGUI, "_build_ui", lambda _self: None)

    controller = gui.ContextorGUI(_FakeRoot())

    assert controller.owner_token
    assert controller.backend_owner_token
    assert controller.desktop_instance_id
    assert len(
        {
            controller.owner_token,
            controller.backend_owner_token,
            controller.desktop_instance_id,
        }
    ) == 3
    assert controller.backend_owner_claim is None
    assert controller._backend_owner_claim_error is None
    assert controller._backend_owner_claim_thread is None
    assert controller._backend_owner_claim_state == "idle"
    assert controller._backend_owner_claim_attempt == 0


def test_claim_current_backend_uses_exact_desktop_owner_contract(monkeypatch):
    controller = _controller()
    claim = SimpleNamespace(backend_instance_id="instance-1")
    calls = []

    def claim_backend_owner(**kwargs):
        calls.append(kwargs)
        return claim

    monkeypatch.setattr(gui, "claim_backend_owner", claim_backend_owner)

    result = gui.ContextorGUI._claim_current_backend_for_desktop(controller)

    assert result is claim
    assert controller.backend_owner_claim is claim
    assert controller._backend_owner_claim_error is None
    assert calls == [
        {
            "host_owner_identity": "desktop-instance",
            "host_kind": "desktop",
            "owner_token": "backend-owner-token",
            "probe_timeout": 2.0,
            "lock_timeout": 5.0,
        }
    ]


def test_startup_claims_the_ready_backend_instance(monkeypatch):
    controller = _controller()
    status = _status("running", True, _record("instance-1"))
    claim = SimpleNamespace(backend_instance_id="instance-1")
    start_calls = []
    claim_calls = []

    monkeypatch.setattr(
        gui,
        "start_backend",
        lambda **kwargs: start_calls.append(kwargs) or status,
    )
    monkeypatch.setattr(
        gui,
        "claim_backend_owner",
        lambda **kwargs: claim_calls.append(kwargs) or claim,
    )

    result = gui.ContextorGUI._claim_backend_owner_on_startup(controller)

    assert result is claim
    assert controller.backend_owner_claim is claim
    assert start_calls == [{"timeout": 20.0, "probe_timeout": 2.0}]
    assert claim_calls == [
        {
            "host_owner_identity": "desktop-instance",
            "host_kind": "desktop",
            "owner_token": "backend-owner-token",
            "probe_timeout": 2.0,
            "lock_timeout": 5.0,
        }
    ]


def test_startup_rejects_claim_for_another_instance(monkeypatch):
    controller = _controller()
    status = _status("running", True, _record("active-instance"))
    claim = SimpleNamespace(backend_instance_id="different-instance")
    monkeypatch.setattr(gui, "start_backend", lambda **_kwargs: status)
    monkeypatch.setattr(gui, "claim_backend_owner", lambda **_kwargs: claim)

    with pytest.raises(RuntimeError, match="active backend instance"):
        gui.ContextorGUI._claim_backend_owner_on_startup(controller)


def test_revoked_startup_waits_then_claims_replacement_without_stopping_old_backend(
    monkeypatch,
):
    controller = _controller()
    initial = _status("running", True, _record("old-instance"))
    replacement = _status("running", True, _record("new-instance", 200, 2000))
    stopped = _status("stopped", False, None)
    replacement_claim = SimpleNamespace(backend_instance_id="new-instance")
    starts = iter((initial, replacement))
    start_calls = []
    claim_calls = []
    status_calls = []
    stops = []

    def start_backend(**kwargs):
        start_calls.append(kwargs)
        return next(starts)

    def claim_backend_owner(**kwargs):
        claim_calls.append(kwargs)
        if len(claim_calls) == 1:
            raise BackendOwnerInstanceRevoked("old instance is revoked")
        return replacement_claim

    monkeypatch.setattr(gui, "start_backend", start_backend)
    monkeypatch.setattr(gui, "claim_backend_owner", claim_backend_owner)
    monkeypatch.setattr(
        gui,
        "get_backend_status",
        lambda **kwargs: status_calls.append(kwargs) or stopped,
    )
    monkeypatch.setattr(gui, "stop_backend", lambda **kwargs: stops.append(kwargs))
    monkeypatch.setattr(gui.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(gui.time, "sleep", lambda _seconds: None)

    result = gui.ContextorGUI._claim_backend_owner_on_startup(controller)

    assert result is replacement_claim
    assert controller.backend_owner_claim is replacement_claim
    assert start_calls == [
        {"timeout": 20.0, "probe_timeout": 2.0},
        {"timeout": 20.0, "probe_timeout": 2.0},
    ]
    assert status_calls == [{"probe_timeout": 0.5}]
    assert len(claim_calls) == 2
    assert all(
        call
        == {
            "host_owner_identity": "desktop-instance",
            "host_kind": "desktop",
            "owner_token": "backend-owner-token",
            "probe_timeout": 2.0,
            "lock_timeout": 5.0,
        }
        for call in claim_calls
    )
    assert stops == []


def test_revoked_startup_timeout_never_stops_backend(monkeypatch):
    controller = _controller()
    initial = _status("running", True, _record("old-instance"))
    active = _status("running", True, _record("old-instance"))
    clock = [0.0]
    status_calls = []
    stops = []

    def get_status(**kwargs):
        status_calls.append(kwargs)
        clock[0] += 1.0
        return active

    monkeypatch.setattr(gui, "start_backend", lambda **_kwargs: initial)
    monkeypatch.setattr(
        gui,
        "claim_backend_owner",
        lambda **_kwargs: (_ for _ in ()).throw(
            BackendOwnerInstanceRevoked("old instance is revoked")
        ),
    )
    monkeypatch.setattr(gui, "get_backend_status", get_status)
    monkeypatch.setattr(gui, "stop_backend", lambda **kwargs: stops.append(kwargs))
    monkeypatch.setattr(gui.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(gui.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds + 1.0))

    with pytest.raises(RuntimeError, match="did not self-terminate before timeout"):
        gui.ContextorGUI._claim_backend_owner_on_startup(controller)

    assert status_calls
    assert stops == []


def test_start_backend_owner_claim_runs_in_nonblocking_daemon_thread():
    controller = _controller()
    entered = threading.Event()
    release = threading.Event()

    def claim_on_startup():
        entered.set()
        release.wait(timeout=2.0)

    controller._claim_backend_owner_on_startup = claim_on_startup
    started = time.monotonic()

    gui.ContextorGUI._start_backend_owner_claim(controller)

    assert time.monotonic() - started < 0.25
    assert entered.wait(timeout=1.0)
    thread = controller._backend_owner_claim_thread
    assert thread.is_alive()
    assert thread.daemon is True
    assert thread.name == "contextor-backend-owner-claim"
    release.set()
    thread.join(timeout=1.0)
    assert not thread.is_alive()


def test_start_backend_owner_claim_stores_worker_exception(monkeypatch):
    controller = _controller()
    expected = RuntimeError("claim failed")
    monkeypatch.setattr(gui, "BACKEND_OWNER_CLAIM_MAX_ATTEMPTS", 1)
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *_args, **_kwargs: pytest.fail("worker must not show a messagebox"),
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showinfo",
        lambda *_args, **_kwargs: pytest.fail("worker must not show a messagebox"),
    )

    def fail_claim():
        raise expected

    controller._claim_backend_owner_on_startup = fail_claim

    gui.ContextorGUI._start_backend_owner_claim(controller)

    controller._backend_owner_claim_thread.join(timeout=1.0)
    assert controller._backend_owner_claim_thread.is_alive() is False
    assert controller._backend_owner_claim_error is expected
    assert controller._backend_owner_claim_state == "failed"
    assert controller._backend_owner_claim_attempt == 1
    assert controller._status_calls == [
        (("Backend ownership failed: claim failed",), {"category": "MCP_CALL"})
    ]


def test_owner_claim_first_attempt_success_has_no_retry_or_failure_status():
    controller = _controller()
    claim = SimpleNamespace(backend_instance_id="instance-1")
    calls = []
    controller._claim_backend_owner_on_startup = lambda: calls.append(1) or claim

    gui.ContextorGUI._start_backend_owner_claim(controller)

    thread = controller._backend_owner_claim_thread
    thread.join(timeout=1.0)

    assert not thread.is_alive()
    assert calls == [1]
    assert controller.backend_owner_claim is claim
    assert controller._backend_owner_claim_state == "claimed"
    assert controller._backend_owner_claim_attempt == 1
    assert controller._backend_owner_claim_error is None
    assert _published_statuses(controller) == []


def test_owner_claim_transient_failure_then_success_retries_once(monkeypatch):
    controller = _controller()
    _, sleeps = _fast_retry_clock(monkeypatch)
    temporary = RuntimeError("temporary")
    claim = SimpleNamespace(backend_instance_id="instance-1")
    call_times = []

    def claim_on_startup():
        call_times.append(gui.time.monotonic())
        if len(call_times) == 1:
            raise temporary
        return claim

    controller._claim_backend_owner_on_startup = claim_on_startup
    gui.ContextorGUI._start_backend_owner_claim(controller)
    thread = controller._backend_owner_claim_thread
    thread.join(timeout=1.0)

    assert not thread.is_alive()
    assert len(call_times) == 2
    assert call_times[1] - call_times[0] == pytest.approx(0.5)
    assert controller.backend_owner_claim is claim
    assert controller._backend_owner_claim_state == "claimed"
    assert controller._backend_owner_claim_attempt == 2
    assert controller._backend_owner_claim_error is None
    assert _published_statuses(controller) == [
        (
            "Backend ownership unavailable; retrying (2/3)...",
            {"category": "MCP_CALL"},
        ),
        (
            "Backend ownership restored.",
            {"category": "MCP_CALL"},
        ),
    ]
    assert sum(sleeps) == pytest.approx(0.5)


def test_owner_claim_two_failures_then_success_traverses_both_delays(monkeypatch):
    controller = _controller()
    _, sleeps = _fast_retry_clock(monkeypatch)
    errors = [RuntimeError("temporary-1"), RuntimeError("temporary-2")]
    claim = SimpleNamespace(backend_instance_id="instance-1")
    call_times = []

    def claim_on_startup():
        call_times.append(gui.time.monotonic())
        if len(call_times) <= 2:
            raise errors[len(call_times) - 1]
        return claim

    controller._claim_backend_owner_on_startup = claim_on_startup
    gui.ContextorGUI._start_backend_owner_claim(controller)
    thread = controller._backend_owner_claim_thread
    thread.join(timeout=1.0)

    assert not thread.is_alive()
    assert len(call_times) == 3
    assert call_times[1] - call_times[0] == pytest.approx(0.5)
    assert call_times[2] - call_times[1] == pytest.approx(1.0)
    assert sum(sleeps) == pytest.approx(1.5)
    assert controller.backend_owner_claim is claim
    assert controller._backend_owner_claim_state == "claimed"
    assert controller._backend_owner_claim_attempt == 3
    assert controller._backend_owner_claim_error is None
    assert _published_statuses(controller) == [
        (
            "Backend ownership unavailable; retrying (2/3)...",
            {"category": "MCP_CALL"},
        ),
        (
            "Backend ownership unavailable; retrying (3/3)...",
            {"category": "MCP_CALL"},
        ),
        (
            "Backend ownership restored.",
            {"category": "MCP_CALL"},
        ),
    ]


def test_owner_claim_three_failures_emits_one_terminal_failure(monkeypatch):
    controller = _controller()
    _, sleeps = _fast_retry_clock(monkeypatch)
    errors = [
        RuntimeError("temporary-1"),
        RuntimeError("temporary-2"),
        RuntimeError("final"),
    ]
    calls = []

    def fail_claim():
        calls.append(1)
        raise errors[len(calls) - 1]

    controller._claim_backend_owner_on_startup = fail_claim
    gui.ContextorGUI._start_backend_owner_claim(controller)
    thread = controller._backend_owner_claim_thread
    thread.join(timeout=1.0)

    assert not thread.is_alive()
    assert calls == [1, 1, 1]
    assert controller._backend_owner_claim_state == "failed"
    assert controller._backend_owner_claim_attempt == 3
    assert controller._backend_owner_claim_error is errors[-1]
    assert _published_statuses(controller) == [
        (
            "Backend ownership unavailable; retrying (2/3)...",
            {"category": "MCP_CALL"},
        ),
        (
            "Backend ownership unavailable; retrying (3/3)...",
            {"category": "MCP_CALL"},
        ),
        (
            "Backend ownership failed: final",
            {"category": "MCP_CALL"},
        ),
    ]
    assert sum(sleeps) == pytest.approx(1.5)


def test_foreign_owner_is_terminal_without_retry_or_messagebox(monkeypatch):
    controller = _controller()
    error = BackendOwnerAlreadyClaimed("foreign owner")
    calls = []

    def fail_claim():
        calls.append(1)
        raise error

    def fail_messagebox(*_args, **_kwargs):
        pytest.fail("owner worker must not show a messagebox")

    controller._claim_backend_owner_on_startup = fail_claim
    monkeypatch.setattr(gui.messagebox, "showerror", fail_messagebox)
    monkeypatch.setattr(gui.messagebox, "showinfo", fail_messagebox)
    monkeypatch.setattr(
        gui.time,
        "sleep",
        lambda _delay: pytest.fail("foreign owner must not be retried"),
    )

    gui.ContextorGUI._start_backend_owner_claim(controller)
    thread = controller._backend_owner_claim_thread
    thread.join(timeout=1.0)

    assert not thread.is_alive()
    assert calls == [1]
    assert controller._backend_owner_claim_state == "failed"
    assert controller._backend_owner_claim_attempt == 1
    assert controller._backend_owner_claim_error is error
    assert _published_statuses(controller) == [
        (
            "Backend ownership failed: foreign owner",
            {"category": "MCP_CALL"},
        )
    ]


def test_closing_during_retry_delay_aborts_without_final_failure(monkeypatch):
    controller = _controller()
    _, sleeps = _fast_retry_clock(monkeypatch, controller=controller)
    temporary = RuntimeError("temporary")
    calls = []

    def fail_claim():
        calls.append(1)
        raise temporary

    controller._claim_backend_owner_on_startup = fail_claim
    gui.ContextorGUI._start_backend_owner_claim(controller)
    thread = controller._backend_owner_claim_thread
    thread.join(timeout=1.0)

    assert not thread.is_alive()
    assert calls == [1]
    assert sleeps
    assert controller._backend_owner_claim_state == "aborted"
    assert controller._backend_owner_claim_attempt == 1
    assert controller._backend_owner_claim_error is temporary
    assert _published_statuses(controller) == [
        (
            "Backend ownership unavailable; retrying (2/3)...",
            {"category": "MCP_CALL"},
        )
    ]


def test_duplicate_owner_worker_is_suppressed_while_first_is_alive():
    controller = _controller()
    entered = threading.Event()
    release = threading.Event()
    calls = []
    claim = SimpleNamespace(backend_instance_id="instance-1")

    def claim_on_startup():
        calls.append(1)
        entered.set()
        release.wait(timeout=2.0)
        return claim

    controller._claim_backend_owner_on_startup = claim_on_startup
    gui.ContextorGUI._start_backend_owner_claim(controller)
    first_thread = controller._backend_owner_claim_thread

    assert entered.wait(timeout=1.0)
    gui.ContextorGUI._start_backend_owner_claim(controller)

    assert controller._backend_owner_claim_thread is first_thread
    assert first_thread.is_alive()
    assert calls == [1]
    release.set()
    first_thread.join(timeout=1.0)

    assert not first_thread.is_alive()
    assert calls == [1]
    assert controller.backend_owner_claim is claim
    assert controller._backend_owner_claim_state == "claimed"


def test_post_paint_starts_backend_claim_before_cleanup_and_live(monkeypatch, tmp_path):
    events = []
    cleanup_done = threading.Event()
    controller = SimpleNamespace(
        _closing=False,
        _start_backend_owner_claim=lambda: events.append("owner"),
        _set_live_status=lambda _message: None,
        _check_stale_excludes=lambda: events.append("stale-excludes"),
        repo_path_var=SimpleNamespace(get=lambda: str(tmp_path)),
        _start_live_watcher=lambda _path: events.append("live"),
    )

    def cleanup():
        events.append("cache-cleanup")
        cleanup_done.set()
        return {"cache": {"errors": []}}

    monkeypatch.setattr(gui, "prune_startup_caches", cleanup)

    gui.ContextorGUI._start_post_paint_tasks(controller)

    assert cleanup_done.wait(timeout=1.0)
    assert events.index("owner") < events.index("cache-cleanup")
    assert events.index("owner") < events.index("live")
