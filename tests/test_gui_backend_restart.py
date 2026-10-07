from types import SimpleNamespace

import pytest

from contextor.ui import gui


def _record(instance_id, pid, creation_time):
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
        endpoint="http://127.0.0.1:8765/mcp",
    )


def _controller():
    busy_buttons = [object(), object(), object()]
    controller = SimpleNamespace(
        root=object(),
        progress_bar=SimpleNamespace(is_cancelled=True),
        log_box=object(),
        cpu_indicator=object(),
        stop_btn=object(),
        _busy_buttons=lambda: busy_buttons,
    )
    return controller, busy_buttons


def _capture_progress(monkeypatch):
    captured = {}

    def capture(root, progress_bar, task, **kwargs):
        captured.update(
            root=root,
            progress_bar=progress_bar,
            task=task,
            **kwargs,
        )

    monkeypatch.setattr(gui, "run_with_progress", capture)
    return captured


def test_restart_runs_lifecycle_in_progress_task_and_confirms_new_identity(
    monkeypatch,
):
    before = _status(
        "ready",
        ready=True,
        record=_record("old-instance", 123, 1000),
    )
    stopped = _status("stopped")
    after = _status(
        "ready",
        ready=True,
        record=_record("new-instance", 123, 2000),
    )
    events = []
    statuses = iter((before, stopped))

    def get_status(*, probe_timeout):
        events.append(("status", probe_timeout))
        return next(statuses)

    def stop_backend(*, timeout):
        events.append(("stop", timeout))

    def start_backend(*, timeout, probe_timeout):
        events.append(("start", timeout, probe_timeout))
        return after

    monkeypatch.setattr(gui, "get_backend_status", get_status)
    monkeypatch.setattr(gui, "stop_backend", stop_backend)
    monkeypatch.setattr(gui, "start_backend", start_backend)
    captured = _capture_progress(monkeypatch)
    controller, busy_buttons = _controller()
    messages = []
    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *args: messages.append(args))

    gui.ContextorGUI._restart_backend(controller)

    assert events == []
    assert controller.progress_bar.is_cancelled is False
    assert captured["root"] is controller.root
    assert captured["progress_bar"] is controller.progress_bar
    assert captured["buttons"] is busy_buttons
    assert captured["log_box"] is controller.log_box
    assert captured["cpu_indicator"] is controller.cpu_indicator
    assert captured["stop_button"] is controller.stop_btn

    result = captured["task"]()

    assert result == (before, after)
    assert events == [
        ("status", 2.0),
        ("stop", 5.0),
        ("status", 0.5),
        ("start", 20.0, 2.0),
    ]

    captured["on_success"](result)
    assert len(messages) == 1
    assert "Old PID: 123" in messages[0][1]
    assert "New instance: new-instance" in messages[0][1]
    assert "http://127.0.0.1:8765/mcp" in messages[0][1]


def test_restart_rejects_reused_complete_backend_identity(monkeypatch):
    old_record = _record("same-instance", 123, 1000)
    before = _status("ready", ready=True, record=old_record)
    after = _status(
        "ready",
        ready=True,
        record=_record("same-instance", 123, 1000),
    )
    statuses = iter((before, _status("stopped")))
    monkeypatch.setattr(gui, "get_backend_status", lambda **_: next(statuses))
    monkeypatch.setattr(gui, "stop_backend", lambda **_: None)
    monkeypatch.setattr(gui, "start_backend", lambda **_: after)
    captured = _capture_progress(monkeypatch)
    controller, _ = _controller()

    gui.ContextorGUI._restart_backend(controller)

    with pytest.raises(RuntimeError, match="previous backend process identity"):
        captured["task"]()


def test_restart_requires_independently_confirmed_stopped_state(monkeypatch):
    before = _status("ready", ready=True, record=_record("old", 123, 1000))
    not_stopped = _status("unready", record=None)
    statuses = iter((before, not_stopped))
    events = []
    monkeypatch.setattr(gui, "get_backend_status", lambda **_: next(statuses))
    monkeypatch.setattr(gui, "stop_backend", lambda **_: events.append("stop"))
    monkeypatch.setattr(gui, "start_backend", lambda **_: events.append("start"))
    captured = _capture_progress(monkeypatch)
    controller, _ = _controller()

    gui.ContextorGUI._restart_backend(controller)

    with pytest.raises(RuntimeError, match="confirmed stopped state"):
        captured["task"]()
    assert events == ["stop"]


def test_restart_requires_new_backend_to_be_authenticated_and_ready(monkeypatch):
    before = _status("ready", ready=True, record=_record("old", 123, 1000))
    stopped = _status("stopped")
    unready = _status(
        "unready",
        ready=False,
        record=_record("new", 456, 2000),
    )
    statuses = iter((before, stopped))
    monkeypatch.setattr(gui, "get_backend_status", lambda **_: next(statuses))
    monkeypatch.setattr(gui, "stop_backend", lambda **_: None)
    monkeypatch.setattr(gui, "start_backend", lambda **_: unready)
    captured = _capture_progress(monkeypatch)
    controller, _ = _controller()
    errors = []
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: errors.append(args))

    gui.ContextorGUI._restart_backend(controller)

    with pytest.raises(RuntimeError, match="authenticated and ready") as exc_info:
        captured["task"]()
    captured["on_error"](exc_info.value)
    assert errors and "authenticated and ready" in errors[0][1]


def test_restart_starts_backend_when_initial_status_has_no_record(monkeypatch):
    before = _status("stopped", record=None)
    stopped = _status("stopped", record=None)
    after = _status(
        "ready",
        ready=True,
        record=_record("fresh-instance", 456, 2000),
    )
    statuses = iter((before, stopped))
    events = []

    def get_status(*, probe_timeout):
        events.append(("status", probe_timeout))
        return next(statuses)

    monkeypatch.setattr(gui, "get_backend_status", get_status)
    monkeypatch.setattr(gui, "stop_backend", lambda **_: events.append(("stop",)))
    monkeypatch.setattr(gui, "start_backend", lambda **_: after)
    captured = _capture_progress(monkeypatch)
    controller, _ = _controller()

    gui.ContextorGUI._restart_backend(controller)
    result = captured["task"]()

    assert result == (before, after)
    assert events == [("status", 2.0), ("stop",), ("status", 0.5)]


def test_restart_backend_button_is_in_shared_busy_buttons():
    controller = SimpleNamespace(
        analyze_btn=object(),
        analyze_layer_btn=object(),
        analyze_single_btn=object(),
        test_suite_btn=object(),
        restart_backend_btn=object(),
    )

    assert gui.ContextorGUI._busy_buttons(controller) == [
        controller.analyze_btn,
        controller.analyze_layer_btn,
        controller.analyze_single_btn,
        controller.test_suite_btn,
        controller.restart_backend_btn,
    ]
