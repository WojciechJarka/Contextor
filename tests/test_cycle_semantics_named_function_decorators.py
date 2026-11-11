import ast
import json
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
from test_cycle_semantics_decorator_import_effect_baseline import RUNNER


CASES = [
    pytest.param(
        "def identity(fn):\n    return fn\n@identity\ndef f():\n    import pkg.child\nf()\n",
        None, ("pkg.child",), "MODEL_PASS", ("identity", "f"),
        id="pass-through-decorator",
    ),
    pytest.param(
        "def identity(fn):\n    return fn\n@identity\ndef f():\n    import pkg.child\n",
        None, (), "MODEL_PASS", ("identity",),
        id="deferred-decorated-function",
    ),
    pytest.param(
        "def identity(fn):\n    return fn\nalias = identity\n@alias\ndef f():\n    import pkg.child\nf()\n",
        None, ("pkg.child",), "MODEL_PASS", ("alias", "f"),
        id="decorator-alias",
    ),
    pytest.param(
        "def f(fn):\n    return fn\n@f\ndef f():\n    import pkg.child\nf()\n",
        None, ("pkg.child",), "MODEL_PASS", ("f", "f"),
        id="same-name-decorator",
    ),
    pytest.param(
        "def deco(fn):\n    return\n@deco\ndef f():\n    import pkg.child\n",
        None, (), "MODEL_PASS", ("deco",),
        id="decorator-returns-none",
    ),
    pytest.param(
        "def deco(fn):\n    return\n@deco\ndef f():\n    import pkg.child\nf()\n",
        "TypeError", (), "UNKNOWN", ("deco",),
        id="noncallable-decorated-result",
    ),
    pytest.param(
        "deco = None\n@deco\ndef f():\n    import pkg.child\n",
        "TypeError", (), "UNKNOWN", (),
        id="noncallable-decorator",
    ),
    pytest.param(
        "def deco():\n    return\n@deco\ndef f():\n    import pkg.child\n",
        "TypeError", (), "UNKNOWN", (),
        id="decorator-wrong-arity",
    ),
    pytest.param(
        "def identity(fn):\n    return fn\n@identity\ndef f(x=1):\n    import pkg.child\n",
        None, (), "UNKNOWN", (),
        id="decorated-unsupported-body",
    ),
    pytest.param(
        "def identity(fn):\n    return fn\n@identity\n@identity\ndef f():\n    import pkg.child\n",
        None, (), "UNKNOWN", (),
        id="multiple-decorators",
    ),
    pytest.param(
        "def deco(fn):\n    import pkg.child\n    return fn\n@deco\ndef f():\n    pass\n",
        None, ("pkg.child",), "MODEL_PASS", ("deco",),
        id="decorator-import-effect-unsupported",
    ),
]


@pytest.mark.parametrize(
    "source,expected_error,expected_imports,expected_outcome,expected_calls",
    CASES,
)
def test_named_function_decorator_cpython_and_model(
    tmp_path, source, expected_error, expected_imports,
    expected_outcome, expected_calls,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")
    (package / "child.py").write_text("pass\n", encoding="utf-8")
    process = subprocess.run(
        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {
        "error": expected_error,
        "imports": list(expected_imports),
    }

    result = evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(source),
            "pkg.child": ast.parse("pass\n"),
        },
        "pkg",
    )
    assert result.outcome == expected_outcome
    assert tuple(
        event.symbol for event in result.events
        if event.operation == "CALL_FUNCTION"
    ) == expected_calls
    if expected_outcome == "MODEL_PASS":
        assert tuple(
            event.target for event in result.events
            if event.operation == "START_IMPORT" and event.target == "pkg.child"
        ) == expected_imports
    else:
        assert not any(
            event.operation == "START_IMPORT" and event.target == "pkg.child"
            for event in result.events
        )
