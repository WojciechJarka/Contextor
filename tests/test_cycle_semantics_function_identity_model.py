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

    assert result.outcome == (
        "UNKNOWN"
        if consumer_source is not None
        else (
            "UNKNOWN"
            if "g()" in package_source
            else "MODEL_PASS"
        )
    )
