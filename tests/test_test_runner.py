"""
Parsing of pytest output for the GUI test-suite button.

The result pattern must match the per-test verbose lines and nothing
else. Matching anywhere in the line also caught pytest's trailing
"short test summary info" block, which counted every failure twice and
put the literal word FAILED into the list of failing tests.
"""

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.live

from contextor.ui import gui
from contextor.ui import test_runner
from contextor.ui.test_runner import (
    _RESULT_RE,
    TestSuiteUnavailable as SuiteUnavailable,
    _summary_counts,
    format_summary,
)


def _parse(line):
    match = _RESULT_RE.match(line)

    return (match.group("nodeid"), match.group("outcome")) if match else None


def test_matches_a_verbose_result_line():
    line = "tests/test_cycles.py::test_simple_cycle PASSED                    [ 12%]"

    assert _parse(line) == ("tests/test_cycles.py::test_simple_cycle", "PASSED")


def test_matches_a_parametrized_test():
    line = "tests/test_cancellation.py::test_validate[0] FAILED               [ 50%]"

    assert _parse(line) == ("tests/test_cancellation.py::test_validate[0]", "FAILED")


def test_ignores_the_short_summary_block():
    """
    These lines start with the outcome and would otherwise be counted a
    second time.
    """

    assert _parse("FAILED tests/test_x.py::test_y - AssertionError: nope") is None
    assert _parse("ERROR tests/test_x.py - ImportError") is None


def test_ignores_ordinary_output():
    assert _parse("collected 64 items") is None
    assert _parse("=== 64 passed in 19.53s ===") is None
    assert _parse("") is None


def test_summary_lists_failing_tests():
    summary = format_summary(
        {
            "passed": 3,
            "failed": 1,
            "skipped": 0,
            "exit_code": 1,
            "failures": ["tests/test_x.py::test_y"],
        }
    )

    assert "Failed:  1" in summary
    assert "tests/test_x.py::test_y" in summary


def test_summary_explains_a_failure_with_no_failing_test():
    summary = format_summary(
        {"passed": 0, "failed": 0, "skipped": 0, "exit_code": 2, "failures": []}
    )

    assert "collection or import error" in summary


def test_summary_of_a_clean_run_lists_no_failures():
    summary = format_summary(
        {"passed": 5, "failed": 0, "skipped": 1, "exit_code": 0, "failures": []}
    )

    assert "Failing tests:" not in summary
    assert "Passed:  5" in summary


def test_terminal_summary_fallback_counts_outcomes():
    counts = _summary_counts("=== 1 failed, 7 passed, 2 skipped, 1 xfailed ===")

    assert counts["FAILED"] == 1
    assert counts["PASSED"] == 7
    assert counts["SKIPPED"] == 2
    assert counts["XFAIL"] == 1


class _FakeProcess:
    def __init__(self, output, exit_code=0):
        self.stdout = io.StringIO(output)
        self._exit_code = exit_code

    def wait(self, timeout=None):
        return self._exit_code

    def poll(self):
        return self._exit_code

    def kill(self):
        pass

    def terminate(self):
        pass


def test_success_without_any_reported_test_is_unavailable(monkeypatch):
    monkeypatch.setattr(test_runner, "_ensure_runnable", lambda: None)
    monkeypatch.setattr(test_runner, "_count_tests", lambda **_kwargs: 0)
    monkeypatch.setattr(
        test_runner,
        "_popen",
        lambda _args, **_kwargs: _FakeProcess("", 0),
    )

    with pytest.raises(SuiteUnavailable, match="no test results"):
        test_runner.run_test_suite()


@pytest.mark.parametrize(
    ("live_only", "expected_selector"),
    [(False, []), (True, ["-m", "live"])],
)
def test_runner_uses_the_same_suite_selector_for_collection_and_execution(
    monkeypatch, live_only, expected_selector
):
    calls = []

    monkeypatch.setattr(test_runner, "_ensure_runnable", lambda: None)

    def fake_popen(arguments, **_kwargs):
        calls.append(arguments)
        if "--collect-only" in arguments:
            return _FakeProcess("1 test collected\n", 0)
        return _FakeProcess("tests/test_x.py::test_y PASSED [100%]\n", 0)

    monkeypatch.setattr(test_runner, "_popen", fake_popen)

    result = test_runner.run_test_suite(live_only=live_only)

    assert result["passed"] == 1
    assert calls[0][2:2 + len(expected_selector)] == expected_selector
    run_selector_start = calls[1].index("no:cacheprovider") + 1
    assert calls[1][run_selector_start:run_selector_start + len(expected_selector)] == expected_selector
    if not expected_selector:
        assert "-m" not in calls[0]
        assert "-m" not in calls[1]


def test_gui_launchers_target_project_virtual_environment():
    root = Path(__file__).resolve().parents[1]
    launcher = (root / "run_gui.bat").read_text(encoding="utf-8").lower()
    installer = (root / "GUI_test_suite_installer.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert ".venv\\scripts\\pythonw.exe" in launcher
    assert ".venv\\scripts\\python.exe" in installer
    assert "start \"\" /d \"%~dp0\" \"c:\\spiralprophet" not in launcher


def test_pytest_console_is_hidden_unless_explicitly_requested(monkeypatch):
    calls = []

    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))
        return object()

    monkeypatch.setattr(test_runner.subprocess, "Popen", fake_popen)

    test_runner._popen(["--collect-only"], show_console=False)
    hidden_kwargs = calls[-1][1]

    assert hidden_kwargs["creationflags"] & test_runner.subprocess.CREATE_NO_WINDOW
    assert hidden_kwargs["startupinfo"].dwFlags & test_runner.subprocess.STARTF_USESHOWWINDOW
    assert hidden_kwargs["startupinfo"].wShowWindow == test_runner.subprocess.SW_HIDE

    test_runner._popen(["--collect-only"], show_console=True)
    visible_kwargs = calls[-1][1]

    assert visible_kwargs["creationflags"] == 0
    assert visible_kwargs["startupinfo"] is None


@pytest.mark.parametrize("checkbox_value", [False, True])
def test_gui_cmd_checkbox_controls_test_runner_console(monkeypatch, checkbox_value):
    captured = {}

    def fake_run_with_progress(_root, _bar, task, **_kwargs):
        captured["task"] = task

    def fake_run_test_suite(**kwargs):
        captured["runner_kwargs"] = kwargs
        return {"exit_code": 0, "total": 1, "passed": 1}

    monkeypatch.setattr(gui, "run_with_progress", fake_run_with_progress)
    monkeypatch.setattr(gui, "run_test_suite", fake_run_test_suite)

    controller = SimpleNamespace(
        root=object(),
        progress_bar=SimpleNamespace(is_cancelled=True),
        cmd_var=SimpleNamespace(get=lambda: checkbox_value),
        log_box=object(),
        cpu_indicator=object(),
        stop_btn=object(),
        _busy_buttons=lambda: [],
    )

    controller._run_test_suite = lambda **kwargs: gui.ContextorGUI._run_test_suite(
        controller, **kwargs
    )
    gui.ContextorGUI.run_test_suite(controller)
    captured["task"](log="log", progress_callback="progress")

    assert captured["runner_kwargs"] == {
        "log": "log",
        "progress_callback": "progress",
        "show_console": checkbox_value,
        "live_only": False,
    }


def test_gui_live_suite_selects_only_live_tests(monkeypatch):
    captured = {}

    def fake_run_with_progress(_root, _bar, task, **_kwargs):
        captured["task"] = task

    def fake_run_test_suite(**kwargs):
        captured["runner_kwargs"] = kwargs
        return {"exit_code": 0, "total": 1, "passed": 1, "failed": 0, "skipped": 0, "failures": []}

    monkeypatch.setattr(gui, "run_with_progress", fake_run_with_progress)
    monkeypatch.setattr(gui, "run_test_suite", fake_run_test_suite)

    controller = SimpleNamespace(
        root=object(),
        progress_bar=SimpleNamespace(is_cancelled=True),
        cmd_var=SimpleNamespace(get=lambda: False),
        log_box=object(),
        cpu_indicator=object(),
        stop_btn=object(),
        _busy_buttons=lambda: [],
    )
    controller._run_test_suite = lambda **kwargs: gui.ContextorGUI._run_test_suite(
        controller, **kwargs
    )

    gui.ContextorGUI.run_live_suite(controller)
    captured["task"](log="log", progress_callback="progress")

    assert captured["runner_kwargs"]["live_only"] is True
