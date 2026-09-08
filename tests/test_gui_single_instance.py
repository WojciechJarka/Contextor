from __future__ import annotations

import contextor.__main__ as entry
from contextor.ui import single_instance


def test_secondary_desktop_short_circuits_before_gui_startup(monkeypatch):
    calls = []

    class Guard:
        is_primary = False

        def signal_existing(self):
            calls.append("signal")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(
        single_instance.DesktopSingleInstance,
        "acquire",
        classmethod(lambda cls: Guard()),
    )
    assert entry._run_gui() == 0
    assert calls == ["signal", "close"]


def test_primary_activation_is_repeatable_and_polled_on_gui_thread(monkeypatch):
    calls, scheduled = [], []

    class Kernel:
        def __init__(self):
            self.results = [single_instance.WAIT_OBJECT_0, single_instance.WAIT_TIMEOUT, single_instance.WAIT_OBJECT_0]
        def WaitForSingleObject(self, _event, timeout):
            assert timeout == 0
            return self.results.pop(0)
        def CloseHandle(self, _handle):
            return True

    class Root:
        def after(self, delay, callback):
            scheduled.append((delay, callback))

    monkeypatch.setattr(single_instance.os, "name", "nt")
    guard = single_instance.DesktopSingleInstance(mutex=11, event=22, primary=True, kernel=Kernel())
    guard.register_activation(Root(), lambda: calls.append("activate"))
    assert scheduled[0][0] == 0
    for expected in (["activate"], ["activate"], ["activate", "activate"]):
        _, poll = scheduled.pop(0)
        poll()
        assert calls == expected
    guard.close()


def test_close_stops_future_activation_poll(monkeypatch):
    scheduled = []

    class Kernel:
        def WaitForSingleObject(self, _event, _timeout):
            raise AssertionError("poll must not reach kernel after close")
        def CloseHandle(self, _handle):
            return True

    class Root:
        def after(self, delay, callback):
            scheduled.append((delay, callback))

    monkeypatch.setattr(single_instance.os, "name", "nt")
    guard = single_instance.DesktopSingleInstance(mutex=11, event=22, primary=True, kernel=Kernel())
    guard.register_activation(Root(), lambda: None)
    _, poll = scheduled.pop(0)
    guard.close()
    poll()
    assert scheduled == []
