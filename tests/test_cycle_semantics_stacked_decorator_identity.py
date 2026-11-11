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
        (
            "def upper(fn):\n"
            "    import pkg.top\n"
            "    return fn\n"
            "def lower(fn):\n"
            "    import pkg.bottom\n"
            "    return fn\n"
            "@upper\n"
            "@lower\n"
            "def f():\n"
            "    pass\n"
        ),
        None,
        ("pkg.bottom", "pkg.top"),
        "MODEL_PASS",
        id="bottom-up-application",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    import pkg.child\n"
            "    return fn\n"
            "@deco\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        None,
        ("pkg.child", "pkg.child"),
        "MODEL_PASS",
        id="same-decorator-called-twice",
    ),
    pytest.param(
        (
            "def upper(fn):\n"
            "    import pkg.top\n"
            "    return fn\n"
            "def lower(fn):\n"
            "    global upper\n"
            "    upper = None\n"
            "    import pkg.bottom\n"
            "    return fn\n"
            "@upper\n"
            "@lower\n"
            "def f():\n"
            "    pass\n"
        ),
        None,
        ("pkg.bottom", "pkg.top"),
        "UNKNOWN",
        id="upper-binding-replaced-after-evaluation",
    ),
    pytest.param(
        (
            "def upper(fn):\n"
            "    import pkg.top\n"
            "    return fn\n"
            "def lower(fn):\n"
            "    return\n"
            "@upper\n"
            "@lower\n"
            "def f():\n"
            "    pass\n"
        ),
        None,
        ("pkg.top",),
        "MODEL_PASS",
        id="none-intermediate-value",
    ),
    pytest.param(
        (
            "def upper():\n"
            "    import pkg.top\n"
            "    return\n"
            "def lower(fn):\n"
            "    import pkg.bottom\n"
            "    return fn\n"
            "@upper\n"
            "@lower\n"
            "def f():\n"
            "    pass\n"
        ),
        "TypeError",
        ("pkg.bottom",),
        "UNKNOWN",
        id="upper-wrong-arity-after-lower-effect",
    ),
    pytest.param(
        (
            "def upper(fn):\n"
            "    import pkg.top\n"
            "    return fn\n"
            "def lower(fn):\n"
            "    import pkg.bottom\n"
            "    return fn\n"
            "@upper\n"
            "@lower\n"
            "def f():\n"
            "    import pkg.child\n"
            "f()\n"
        ),
        None,
        ("pkg.bottom", "pkg.top", "pkg.child"),
        "MODEL_PASS",
        id="decorated-body-executed-last",
    ),
]


@pytest.mark.parametrize(
    "source,expected_error,expected_imports,expected_model_outcome",
    CASES,
)
def test_stacked_decorator_cpython_and_current_boundary(
    tmp_path,
    source,
    expected_error,
    expected_imports,
    expected_model_outcome,
):
    package = tmp_path / "pkg"
    package.mkdir()

    (package / "__init__.py").write_text(
        source,
        encoding="utf-8",
    )

    for name in ("top", "bottom", "child"):
        (package / (name + ".py")).write_text(
            "pass\n",
            encoding="utf-8",
        )

    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            RUNNER,
            str(tmp_path),
        ],
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

    sources = {
        "pkg.__init__": ast.parse(source),
    }

    for name in ("top", "bottom", "child"):
        sources["pkg." + name] = ast.parse("pass\n")

    result = evaluate_package_import_order(
        sources,
        "pkg",
    )

    assert result.outcome == expected_model_outcome

    if expected_model_outcome == "MODEL_PASS":
        actual_starts = tuple(
            event.target for event in result.events
            if event.operation == "START_IMPORT"
            and event.target is not None
            and event.target.startswith("pkg.")
        )
        assert actual_starts == tuple(dict.fromkeys(expected_imports))
