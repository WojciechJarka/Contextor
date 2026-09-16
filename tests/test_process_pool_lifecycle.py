from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace
import threading
import time

import contextor.core.analysis.process_pool_lifecycle as lifecycle
import contextor.ui.gui as gui_module


def _sleep_worker(seconds):
    time.sleep(seconds)
    return seconds


class _FakeProcess:
    def __init__(self, *, survive_terminate=False):
        self.alive = True
        self.survive_terminate = survive_terminate
        self.terminate_calls = 0
        self.kill_calls = 0
        self.join_calls = 0

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminate_calls += 1
        if not self.survive_terminate:
            self.alive = False

    def kill(self):
        self.kill_calls += 1
        self.alive = False

    def join(self, timeout=None):
        self.join_calls += 1


class _FakeExecutor:
    def __init__(self, processes=None):
        self._processes = {
            index: process
            for index, process in enumerate(processes or ())
        }
        self.shutdown_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def shutdown(self, *, wait=True, cancel_futures=False):
        self.shutdown_calls.append(
            (wait, cancel_futures)
        )


def test_managed_process_pool_registry_is_process_local():
    assert lifecycle.active_process_pool_count() == 0

    with lifecycle.managed_process_pool(
        _FakeExecutor,
    ):
        assert lifecycle.active_process_pool_count() == 1

    assert lifecycle.active_process_pool_count() == 0


def test_force_shutdown_terminates_then_kills_survivors():
    normal = _FakeProcess()
    stubborn = _FakeProcess(survive_terminate=True)
    executor = _FakeExecutor([normal, stubborn])

    terminated = lifecycle.terminate_process_pool(
        executor,
        timeout=0.01,
    )

    assert terminated == 2
    assert executor.shutdown_calls == [
        (False, True)
    ]
    assert normal.terminate_calls == 1
    assert normal.kill_calls == 0
    assert stubborn.terminate_calls == 1
    assert stubborn.kill_calls == 1
    assert not normal.is_alive()
    assert not stubborn.is_alive()


def test_real_process_pool_workers_are_force_terminated():
    with lifecycle.managed_process_pool(
        ProcessPoolExecutor,
        max_workers=2,
    ) as executor:
        executor.submit(_sleep_worker, 60)
        executor.submit(_sleep_worker, 60)

        deadline = time.monotonic() + 5.0
        processes = ()
        while time.monotonic() < deadline:
            raw = getattr(executor, "_processes", None)
            if isinstance(raw, dict) and len(raw) == 2:
                processes = tuple(raw.values())
                if all(process.is_alive() for process in processes):
                    break
            time.sleep(0.02)

        assert len(processes) == 2
        assert all(
            process.is_alive()
            for process in processes
        )
        assert lifecycle.active_process_pool_count() == 1

        terminated = lifecycle.terminate_active_process_pools(
            timeout=2.0,
        )

        assert terminated == 2
        assert all(
            not process.is_alive()
            for process in processes
        )

    assert lifecycle.active_process_pool_count() == 0


def test_desktop_close_force_terminates_process_local_pools(
    monkeypatch,
):
    calls = []
    destroyed = []

    monkeypatch.setattr(
        gui_module,
        "close_cmd_log",
        lambda: None,
    )
    monkeypatch.setattr(
        gui_module,
        "save_state",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        gui_module,
        "terminate_active_process_pools",
        lambda *, timeout: calls.append(timeout) or 0,
    )
    monkeypatch.setattr(
        gui_module,
        "FULL_ANALYSIS_SHUTDOWN_WAIT_SECONDS",
        0.01,
    )

    class _Root:
        def geometry(self):
            return "800x600+10+10"

        def destroy(self):
            destroyed.append(True)

    class _Var:
        def get(self):
            return ""

    controller = object.__new__(
        gui_module.ContextorGUI
    )
    controller.root = _Root()
    controller.theme_mode = "light"
    controller.repo_path_var = _Var()
    controller.layer_path_var = _Var()
    controller.file_path_var = _Var()
    controller.live_watchers = {}
    controller.live_event_feeds = {}
    controller.live_clients = {}
    controller.live_client = None
    controller._live_start_retry_after_id = None
    controller._full_analysis_done = threading.Event()

    gui_module.ContextorGUI.on_closing(controller)

    assert calls == [0.01]
    assert destroyed == [True]
    assert controller._closing is True
