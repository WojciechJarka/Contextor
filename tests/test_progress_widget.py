"""Terminal progress states must never leave stale determinate percentages."""

from contextor.ui import progress_widget
from contextor.core.errors import AnalysisCancelled
from contextor.core.reporting_engine.graph_analytics import (
    generate_graph_analytics_report,
)


class _Widget:
    def __init__(self):
        self.options = {}
        self.started = []
        self.stopped = 0

    def __getitem__(self, key):
        return self.options[key]

    def __setitem__(self, key, value):
        self.options[key] = value

    def config(self, **kwargs):
        self.options.update(kwargs)

    def start(self, value):
        self.started.append(value)

    def stop(self):
        self.stopped += 1


class _Root:
    def __init__(self):
        self.delayed = []

    def after(self, delay, callback, *args):
        if delay == 0:
            callback(*args)
        else:
            self.delayed.append((callback, args))


class _SynchronousThread:
    def __init__(self, *, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


def _progress_container():
    container = type("Progress", (), {})()
    container.indet = _Widget()
    container.det = _Widget()
    container.flicker_label = _Widget()
    container.time_label = _Widget()
    container.is_cancelled = False
    return container


def test_success_resets_last_determinate_percentage(monkeypatch):
    monkeypatch.setattr(progress_widget.threading, "Thread", _SynchronousThread)
    progress = _progress_container()

    def task(progress_callback):
        progress_callback(2, 3, "module.py")
        return "done"

    progress_widget.run_with_progress(_Root(), progress, task)

    assert progress.det["value"] == 0
    assert progress.flicker_label.options["text"] == ""
    assert progress.time_label.options["text"] == ""


def test_error_resets_last_determinate_percentage(monkeypatch):
    monkeypatch.setattr(progress_widget.threading, "Thread", _SynchronousThread)
    progress = _progress_container()

    def task(progress_callback):
        progress_callback(2, 3, "module.py")
        raise RuntimeError("boom")

    progress_widget.run_with_progress(_Root(), progress, task)

    assert progress.det["value"] == 0
    assert progress.flicker_label.options["text"] == ""
    assert progress.time_label.options["text"] == ""


def test_cancelled_operation_keeps_the_shared_reset_behavior(monkeypatch):
    monkeypatch.setattr(progress_widget.threading, "Thread", _SynchronousThread)
    progress = _progress_container()

    def task(progress_callback):
        progress_callback(2, 3, "module.py")
        raise AnalysisCancelled()

    progress_widget.run_with_progress(_Root(), progress, task)

    assert progress.det["value"] == 0


def test_eta_refresh_remains_active_during_a_long_stage(monkeypatch):
    monkeypatch.setattr(progress_widget.threading, "Thread", _SynchronousThread)
    progress = _progress_container()
    root = _Root()
    observed = []

    def task(progress_callback):
        progress_callback(7, 11, "Step 8/11: Writing JSON report snapshots")
        callback, args = root.delayed.pop(0)
        callback(*args)
        observed.append(progress.time_label.options["text"])
        return "done"

    progress_widget.run_with_progress(root, progress, task)

    assert observed and "ETA:" in observed[0]
    assert "[100.0%]" not in observed[0]
    assert progress.det["value"] == 0


def test_task_without_item_callback_shows_indeterminate_eta_while_running(monkeypatch):
    monkeypatch.setattr(progress_widget.threading, "Thread", _SynchronousThread)
    progress = _progress_container()
    observed = []

    def task():
        observed.append(progress.time_label.options["text"])
        return "done"

    progress_widget.run_with_progress(_Root(), progress, task)

    assert observed == ["[ -- ] ETA: estimating…"]
    assert progress.time_label.options["text"] == ""


def test_stop_interrupts_graph_analytics_internal_checkpoint(monkeypatch):
    monkeypatch.setattr(progress_widget.threading, "Thread", _SynchronousThread)
    progress = _progress_container()
    cancelled = []

    def task(progress_callback):
        progress.is_cancelled = True
        return generate_graph_analytics_report(
            artifact_data={"artifacts": {}},
            hard_edges={"pkg.consumer": ["pkg.model"], "pkg.model": []},
            progress_callback=progress_callback,
        )

    progress_widget.run_with_progress(
        _Root(), progress, task, on_cancel=lambda: cancelled.append(True)
    )

    assert cancelled == [True]
    assert progress.det["value"] == 0


def test_failed_test_result_is_not_logged_as_success(monkeypatch):
    monkeypatch.setattr(progress_widget.threading, "Thread", _SynchronousThread)
    emitted = []
    monkeypatch.setattr(progress_widget, "emit_program_log", emitted.append)

    progress_widget.run_with_progress(
        _Root(),
        _progress_container(),
        lambda: {"exit_code": 1, "failed": 1},
    )

    assert any(message.startswith("[FAILED]") for message in emitted)
    assert not any(message.startswith("[SUCCESS]") for message in emitted)
