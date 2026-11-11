import ast
import json
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)

from test_cycle_semantics_decorator_import_effect_baseline import (
    RUNNER,
)


CASES = [
    pytest.param(
        (
            "def deco(fn):\n"
            "    import pkg.child\n"
            "    return\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "pass\n",
        None,
        ("pkg.child",),
        "MODEL_PASS",
        id="import-then-bare-return",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    import pkg.child\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "pass\n",
        None,
        ("pkg.child",),
        "MODEL_PASS",
        id="import-then-implicit-none",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    import pkg.child\n"
            "    return fn\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "pass\n",
        None,
        ("pkg.child",),
        "UNKNOWN",
        id="import-then-parameter-return",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    import pkg.child\n"
            "    return\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "from pkg import f\n",
        "ImportError",
        ("pkg.child",),
        None,
        id="decorator-import-before-final-binding",
    ),
]


@pytest.mark.parametrize(
    "source,child_source,error,imports,model_outcome",
    CASES,
)
def test_decorator_import_return_gate(
    tmp_path,
    source,
    child_source,
    error,
    imports,
    model_outcome,
):
    package = tmp_path / "pkg"
    package.mkdir()

    (package / "__init__.py").write_text(
        source,
        encoding="utf-8",
    )
    (package / "child.py").write_text(
        child_source,
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
        "error": error,
        "imports": list(imports),
    }

    result = evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(source),
            "pkg.child": ast.parse(child_source),
        },
        "pkg",
    )

    if model_outcome is None:
        assert result.outcome != "MODEL_PASS"
    else:
        assert result.outcome == model_outcome

    child_starts = [
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target == "pkg.child"
    ]

    if model_outcome == "MODEL_PASS":
        assert child_starts == ["pkg.child"]

    if model_outcome == "UNKNOWN":
        assert not any(
            event.operation == "CALL_FUNCTION"
            for event in result.events
        )
