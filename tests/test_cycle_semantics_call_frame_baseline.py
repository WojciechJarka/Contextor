import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


CASES = [
    pytest.param(
        (
            "def identity(value):\n"
            "    return value\n"
            "assert identity(7) == 7\n"
        ),
        None,
        (),
        "UNKNOWN",
        id="positional-identity-return",
    ),
    pytest.param(
        (
            "def calculate(value):\n"
            "    local = value\n"
            "    return local\n"
            "assert calculate(9) == 9\n"
            "assert 'local' not in globals()\n"
        ),
        None,
        (),
        "UNKNOWN",
        id="parameter-and-local-binding",
    ),
    pytest.param(
        (
            "def f():\n"
            "    return 1\n"
            "    import pkg.child\n"
            "assert f() == 1\n"
        ),
        None,
        (),
        "UNKNOWN",
        id="return-skips-later-import",
    ),
    pytest.param(
        (
            "def identity(fn):\n"
            "    return fn\n"
            "@identity\n"
            "def f():\n"
            "    import pkg.child\n"
        ),
        None,
        (),
        "MODEL_PASS",
        id="pass-through-decorator-defers-body",
    ),
    pytest.param(
        (
            "def identity(fn):\n"
            "    return fn\n"
            "@identity\n"
            "def f():\n"
            "    import pkg.child\n"
            "f()\n"
        ),
        None,
        ("pkg.child",),
        "MODEL_PASS",
        id="pass-through-decorator-then-call",
    ),
    pytest.param(
        (
            "def original():\n"
            "    import pkg.child\n"
            "def return_callable():\n"
            "    return original\n"
            "alias = return_callable()\n"
            "alias()\n"
        ),
        None,
        ("pkg.child",),
        "UNKNOWN",
        id="return-callable-and-invoke",
    ),
    pytest.param(
        (
            "def identity(value):\n"
            "    return value\n"
            "identity()\n"
        ),
        "TypeError",
        (),
        "UNKNOWN",
        id="missing-required-argument",
    ),
]


RUNNER = """
import builtins
import importlib
import json
import sys

sys.path.insert(0, sys.argv[1])

observed = []
original_import = builtins.__import__

def traced_import(name, *args, **kwargs):
    if name.startswith("pkg."):
        observed.append(name)
    return original_import(name, *args, **kwargs)

builtins.__import__ = traced_import

error = None

try:
    importlib.import_module("pkg")
except Exception as exc:
    error = type(exc).__name__

print(json.dumps({
    "error": error,
    "imports": observed,
}))
"""


@pytest.mark.parametrize(
    "source,expected_error,expected_imports,expected_model_outcome",
    CASES,
)
def test_call_frame_cpython_and_current_model(
    tmp_path: Path,
    source: str,
    expected_error: str | None,
    expected_imports: tuple[str, ...],
    expected_model_outcome: str,
):
    package = tmp_path / "pkg"
    package.mkdir()

    (package / "__init__.py").write_text(
        source,
        encoding="utf-8",
    )
    (package / "child.py").write_text(
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

    result = evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(source),
            "pkg.child": ast.parse("pass\n"),
        },
        "pkg",
    )

    assert result.outcome == expected_model_outcome

    # A conservative UNKNOWN must not be presented
    # as execution parity or as evidence of passivity.
