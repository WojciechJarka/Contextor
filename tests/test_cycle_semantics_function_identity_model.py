import ast

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)

from test_cycle_semantics_function_identity_cpython import (
    CASES,
)


@pytest.mark.parametrize(
    "package_source,consumer_source,expected",
    CASES,
)
def test_current_model_identity_boundary(
    package_source,
    consumer_source,
    expected,
):
    sources = {
        "pkg.__init__": ast.parse(package_source),
        "pkg.old": ast.parse("pass\n"),
        "pkg.new": ast.parse("pass\n"),
    }

    entry = "pkg"

    if consumer_source is not None:
        sources["consumer"] = ast.parse(consumer_source)
        entry = "consumer"

    result = evaluate_package_import_order(
        sources,
        entry,
    )

    operations = [
        event.operation
        for event in result.events
    ]

    imported_targets = [
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
    ]

    assert result.outcome in {
        "MODEL_PASS",
        "UNKNOWN",
    }

    if expected["ok"] is False:
        assert result.outcome == "UNKNOWN"

    if expected["ok"] is True:
        assert result.outcome in {
            "MODEL_PASS",
            "UNKNOWN",
        }

    if result.outcome == "MODEL_PASS":
        assert ("pkg.old" in imported_targets) == (
            expected["old"]
        )
        assert ("pkg.new" in imported_targets) == (
            expected["new"]
        )

    assert not (
        "pkg.old" in imported_targets
        and "pkg.new" in imported_targets
        and expected["old"] != expected["new"]
    )

    expected_outcome = (
        "UNKNOWN"
        if consumer_source is not None or not expected["ok"]
        else "MODEL_PASS"
    )

    assert result.outcome == expected_outcome

    call_events = [
        event
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    ]

    if expected_outcome == "MODEL_PASS":
        assert len(call_events) == 1
        assert call_events[0].module == "pkg"
        assert call_events[0].symbol == (
            "g" if "g()" in package_source else "f"
        )
    else:
        assert call_events == []


def test_restricted_function_objects_have_distinct_identity():
    from contextor.core.cycle_semantics.execution.calls import (
        _new_restricted_function,
    )
    from contextor.core.cycle_semantics.execution.steps import (
        _Step,
    )

    body = (_Step("PASS"),)

    first = _new_restricted_function("pkg", body)
    second = _new_restricted_function("pkg", body)

    assert first is not second
    assert first != second
    assert first.body is body
    assert second.body is body

    bindings = {"f": first}
    bindings["g"] = bindings["f"]
    bindings["f"] = second

    assert bindings["g"] is first
    assert bindings["f"] is second


def test_foreign_function_identity_remains_unknown():
    sources = {
        "pkg.__init__": ast.parse(
            "def f():\n"
            "    import pkg.old\n"
        ),
        "pkg.old": ast.parse("pass\n"),
        "consumer": ast.parse(
            "from pkg import f\n"
            "f()\n"
        ),
    }

    result = evaluate_package_import_order(
        sources,
        "consumer",
    )

    assert result.outcome == "UNKNOWN"
    assert not any(
        event.operation == "CALL_FUNCTION"
        for event in result.events
    )
    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.old"
        for event in result.events
    )
