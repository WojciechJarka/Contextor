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
        None, (), id="A-pass-through",
    ),
    pytest.param(
        "def decorate(cls):\n    import pkg.decorate\n    return cls\n"
        "@decorate\nclass C:\n    pass\n",
        None, ("pkg.decorate",), id="B-decorator-import",
    ),
    pytest.param(
        "def decorate(cls):\n    import pkg.decorate\n    return cls\n"
        "@decorate\nclass C:\n    import pkg.body\n",
        None, ("pkg.body", "pkg.decorate"), id="C-body-before-decorator",
    ),
    pytest.param(
        "def top_decorator(cls):\n    import pkg.top\n    return cls\n"
        "def bottom_decorator(cls):\n    import pkg.bottom\n    return cls\n"
        "@top_decorator\n@bottom_decorator\nclass C:\n"
        "    import pkg.body\n",
        None, ("pkg.body", "pkg.bottom", "pkg.top"),
        id="D-stacked-class-decorators",
    ),
    pytest.param(
        "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n",
        None, (), id="E-same-name-decorator",
    ),
    pytest.param(
        "def decorate(cls):\n    return\n@decorate\nclass C:\n"
        "    import pkg.body\n",
        None, ("pkg.body",), id="F-decorator-returns-none",
    ),
    pytest.param(
        "def decorate(cls):\n    import pkg.child\n    return cls\n"
        "@decorate\nclass C:\n    pass\n",
        "ImportError", ("pkg.child",), id="G-early-class-binding-hazard",
    ),
]


@pytest.mark.parametrize("source,expected_error,expected_imports", CASES)
def test_class_decorator_definition_time_baseline(
    tmp_path, source, expected_error, expected_imports,
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
    assert result.outcome == "UNKNOWN", (
        result.outcome,
        [event.__dict__ for event in result.events],
    )
