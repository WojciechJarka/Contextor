"""
Parsing of pytest output for the GUI test-suite button.

The result pattern must match the per-test verbose lines and nothing
else. Matching anywhere in the line also caught pytest's trailing
"short test summary info" block, which counted every failure twice and
put the literal word FAILED into the list of failing tests.
"""

from contextor.ui.test_runner import _RESULT_RE, format_summary


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
