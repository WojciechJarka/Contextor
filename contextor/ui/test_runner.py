"""
contextor/ui/test_runner.py

Runs Contextor's own test suite from the GUI.

Tests execute in a separate interpreter rather than in the GUI process:
pytest mutates global interpreter state (import machinery, warning
filters, collected fixtures) and several tests spawn process pools, none
of which is safe to do inside a running Tk application.

Output is streamed line by line so the log box fills in as tests run,
and the run honours the Stop button like any other long operation.
"""

import importlib.util
import re
import subprocess
import sys

from contextor.core.errors import AnalysisCancelled
from contextor.core.paths import package_root

# Lines pytest emits per test in verbose mode, e.g.
#   tests/test_cycles.py::test_simple_cycle PASSED   [ 12%]
#
# Anchored on the node id so the trailing "short test summary info"
# block - whose lines start with the outcome instead - is not counted a
# second time.
_RESULT_RE = re.compile(
    r"^(?P<nodeid>.+::.+)\s+(?P<outcome>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b"
)

_COLLECTED_RE = re.compile(r"(\d+)\s+tests?\s+collected")

_SUMMARY_RE = re.compile(
    r"(?P<count>\d+)\s+(?P<outcome>passed|failed|errors?|skipped|xfailed|xpassed)\b",
    re.IGNORECASE,
)

_OUTCOME_ORDER = ("FAILED", "ERROR", "PASSED", "SKIPPED", "XFAIL", "XPASS")


class TestSuiteUnavailable(RuntimeError):
    """
    Raised when the suite cannot be run at all, with a reason to display.
    """


def tests_dir():
    return package_root() / "tests"


def _ensure_runnable() -> None:
    import importlib.metadata
    import importlib.util
    
    missing_deps = False
    if importlib.util.find_spec("pytest") is None:
        missing_deps = True

    try:
        if importlib.metadata.version("setuptools") != "69.5.1":
            missing_deps = True
    except importlib.metadata.PackageNotFoundError:
        missing_deps = True

    if missing_deps:
        raise TestSuiteUnavailable(
            "Libraries setuptools==69.5.1, pytest and editable install (pip install -e .) "
            "with dev dependencies are required for full test suite, "
            "please install them running GUI_test_suite_installer.bat file "
            "from root folder of this application."
        )

    if not tests_dir().is_dir():
        raise TestSuiteUnavailable(
            f"No test directory found at:\n{tests_dir()}\n\n"
            "Tests ship with the source checkout, not with an installed package."
        )


def _popen(arguments: list[str], *, show_console: bool = False) -> subprocess.Popen:
    """
    Starts pytest with its output merged into one stream.

    On Windows every runner-owned process is hidden by default. The GUI
    streams output into its own operation log instead of relying on a
    console window that may not exist in a desktop launch.
    """

    creation_flags = 0
    startup_info = None

    # The GUI normally runs with its console hidden; without this a
    # console window pops up for every child process on Windows.
    if sys.platform == "win32" and not show_console:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = subprocess.SW_HIDE

    return subprocess.Popen(
        [sys.executable, "-m", "pytest", "-p", "no:nbval", *arguments],
        cwd=str(package_root()),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creation_flags,
        startupinfo=startup_info,
    )


def _suite_arguments(*, live_only: bool) -> list[str]:
    """Pytest selection shared by collection and execution."""

    return ["-m", "live"] if live_only else []


def _count_tests(*, show_console: bool = False, live_only: bool = False) -> int:
    """
    Number of tests pytest will run, for the progress bar.

    Best effort: a failure here must not stop the actual run.
    """

    try:
        completed = _popen(
            [
                "--collect-only",
                "-q",
                *_suite_arguments(live_only=live_only),
                str(tests_dir()),
            ],
            show_console=show_console,
        )

        output = completed.stdout.read() if completed.stdout else ""
        completed.wait(timeout=120)

    except (OSError, subprocess.SubprocessError):
        return 0

    match = _COLLECTED_RE.search(output)

    return int(match.group(1)) if match else 0


def _summary_counts(line: str) -> dict[str, int]:
    """Parse pytest's terminal summary when plugins suppress per-test lines."""

    result = dict.fromkeys(_OUTCOME_ORDER, 0)
    outcome_map = {
        "passed": "PASSED",
        "xpassed": "XPASS",
        "failed": "FAILED",
        "error": "ERROR",
        "errors": "ERROR",
        "skipped": "SKIPPED",
        "xfailed": "XFAIL",
    }
    for match in _SUMMARY_RE.finditer(line):
        result[outcome_map[match.group("outcome").lower()]] += int(
            match.group("count")
        )
    return result


def run_test_suite(
    log=None,
    progress_callback=None,
    *,
    show_console: bool = False,
    live_only: bool = False,
) -> dict:
    """
    Runs the full suite, or only tests marked ``live``, and returns a summary.

    Returns:
        {
            "passed": int, "failed": int, "skipped": int, "other": int,
            "total": int, "exit_code": int, "failures": [str, ...]
        }
    """

    _ensure_runnable()

    suite_label = "LIVE suite" if live_only else "test suite"

    if log:
        log(f"Running {suite_label} from {tests_dir()}")

    total = _count_tests(show_console=show_console, live_only=live_only)

    if log and total:
        log(f"Collected {total} tests.")

    counts = dict.fromkeys(_OUTCOME_ORDER, 0)
    failures: list[str] = []
    completed = 0
    fallback_counts = dict.fromkeys(_OUTCOME_ORDER, 0)

    process = _popen(
        [
            "-v",
            "--tb=short",
            "-p",
            "no:cacheprovider",
            *_suite_arguments(live_only=live_only),
            str(tests_dir()),
        ],
        show_console=show_console,
    )

    try:
        for raw_line in process.stdout:
            line = raw_line.rstrip()

            if not line:
                continue

            if log:
                log(line)

            line_summary = _summary_counts(line)
            if sum(line_summary.values()):
                fallback_counts = line_summary

            match = _RESULT_RE.match(line)

            if not match:
                continue

            outcome = match.group("outcome")
            nodeid = match.group("nodeid")

            counts[outcome] += 1
            completed += 1

            if outcome in ("FAILED", "ERROR"):
                failures.append(nodeid)

            if progress_callback and not progress_callback(completed, total, nodeid):
                process.terminate()
                raise AnalysisCancelled()

        exit_code = process.wait()

    finally:
        if process.poll() is None:
            process.kill()

        if process.stdout:
            process.stdout.close()

    if completed == 0 and sum(fallback_counts.values()):
        counts = fallback_counts
        completed = sum(counts.values())

    if completed == 0 and exit_code == 0:
        raise TestSuiteUnavailable(
            "pytest exited successfully but reported no test results. "
            f"Interpreter: {sys.executable}. Restart the GUI through run_gui.bat "
            "so it uses the project .venv, then try again."
        )

    return {
        "passed": counts["PASSED"] + counts["XPASS"],
        "failed": counts["FAILED"] + counts["ERROR"],
        "skipped": counts["SKIPPED"] + counts["XFAIL"],
        "total": completed,
        "exit_code": exit_code,
        "failures": failures,
    }


def format_summary(result: dict) -> str:
    """
    Human-readable one-block summary of a run.
    """

    lines = [
        f"Passed:  {result['passed']}",
        f"Failed:  {result['failed']}",
        f"Skipped: {result['skipped']}",
    ]

    # pytest failed without any individual test failing - typically a
    # collection or import error. Say so rather than showing all zeros.
    if result["exit_code"] != 0 and not result["failed"]:
        lines.append("")
        lines.append(
            f"pytest exited with code {result['exit_code']} without a failing test.\n"
            "This usually means a collection or import error - see the log."
        )

    if result["failures"]:
        shown = result["failures"][:10]
        lines.append("")
        lines.append("Failing tests:")
        lines.extend(f"  • {name}" for name in shown)

        remaining = len(result["failures"]) - len(shown)
        if remaining > 0:
            lines.append(f"  … and {remaining} more")

    return "\n".join(lines)


__all__ = [
    "TestSuiteUnavailable",
    "format_summary",
    "run_test_suite",
    "tests_dir",
]
