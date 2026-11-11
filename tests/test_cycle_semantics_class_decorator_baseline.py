"""CPython class-decorator timing versus the current conservative model."""

import ast
import json
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)
from test_cycle_semantics_decorator_import_effect_baseline import RUNNER


CASES = [
    pytest.param(
        "def identity(cls):\n    return cls\n@identity\nclass C:\n    pass\n",
        None, (), "MODEL_PASS", ("identity",), (), id="A-pass-through",
    ),
    pytest.param(
        "def apply_decorator(cls):\n    import pkg.decorate\n    return cls\n"
        "@apply_decorator\nclass C:\n    pass\n",
        None, ("pkg.decorate",), "MODEL_PASS",
        ("apply_decorator",), ("pkg.decorate",), id="B-decorator-import",
    ),
    pytest.param(
        "def apply_decorator(cls):\n    import pkg.decorate\n    return cls\n"
        "@apply_decorator\nclass C:\n    import pkg.body\n",
        None, ("pkg.body", "pkg.decorate"), "MODEL_PASS",
        ("apply_decorator",), ("pkg.body", "pkg.decorate"),
        id="C-body-before-decorator",
    ),
    pytest.param(
        "def top_decorator(cls):\n    import pkg.top\n    return cls\n"
        "def bottom_decorator(cls):\n    import pkg.bottom\n    return cls\n"
        "@top_decorator\n@bottom_decorator\nclass C:\n"
        "    import pkg.body\n",
        None, ("pkg.body", "pkg.bottom", "pkg.top"), "MODEL_PASS",
        ("bottom_decorator", "top_decorator"),
        ("pkg.body", "pkg.bottom", "pkg.top"),
        id="D-stacked-class-decorators",
    ),
    pytest.param(
        "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n",
        None, (), "MODEL_PASS", ("C",), (), id="E-same-name-decorator",
    ),
    pytest.param(
        "def apply_decorator(cls):\n    return\n@apply_decorator\nclass C:\n"
        "    import pkg.body\n",
        None, ("pkg.body",), "MODEL_PASS",
        ("apply_decorator",), ("pkg.body",),
        id="F-decorator-returns-none",
    ),
    pytest.param(
        "def apply_decorator(cls):\n    import pkg.child\n    return cls\n"
        "@apply_decorator\nclass C:\n    pass\n",
        "ImportError", ("pkg.child",), "EARLY_BINDING_HAZARD",
        ("apply_decorator",), ("pkg.child",),
        id="G-early-class-binding-hazard",
    ),
]


@pytest.mark.parametrize(
    "source,expected_error,expected_imports,expected_model_outcome,expected_calls,expected_starts",
    CASES,
)
def test_class_decorator_definition_time_baseline(
    tmp_path, source, expected_error, expected_imports,
    expected_model_outcome, expected_calls, expected_starts,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")

    sources = {"pkg.__init__": ast.parse(source)}
    for child in ("body", "decorate", "top", "bottom", "child"):
        child_source = (
            "from pkg import C\n"
            if child == "child" and expected_error == "ImportError"
            else "pass\n"
        )
        (package / f"{child}.py").write_text(child_source, encoding="utf-8")
        sources[f"pkg.{child}"] = ast.parse(child_source)

    process = subprocess.run(
        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    observed = json.loads(process.stdout)
    assert observed == {
        "error": expected_error,
        "imports": list(expected_imports),
    }

    result = evaluate_package_import_order(sources, "pkg")
    assert result.outcome == expected_model_outcome, (
        result.outcome,
        [event.__dict__ for event in result.events],
    )
    actual_calls = tuple(
        event.symbol for event in result.events
        if event.operation == "CALL_FUNCTION"
    )
    assert actual_calls == expected_calls
    actual_starts = tuple(
        event.target for event in result.events
        if event.operation == "START_IMPORT"
        and event.target is not None
        and event.target.startswith("pkg.")
    )
    assert actual_starts == expected_starts
    if expected_model_outcome == "EARLY_BINDING_HAZARD":
        assert any(
            event.operation == "EARLY_BINDING_HAZARD"
            and event.symbol == "C"
            for event in result.events
        )
        assert not any(
            event.operation == "BIND"
            and event.module == "pkg"
            and event.symbol == "C"
            for event in result.events
        )
