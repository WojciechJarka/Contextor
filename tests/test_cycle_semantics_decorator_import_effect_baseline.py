import ast
import builtins
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
            "def deco(fn):\n"
            "    return fn\n"
            "@deco\n"
            "def f():\n"
            "    import pkg.child\n"
        ),
        (),
        "MODEL_PASS",
        id="decorated-function-body-deferred",
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
        ("pkg.child",),
        "UNKNOWN",
        id="decorator-import-during-definition",
    ),
    pytest.param(
        (
            "def upper(fn):\n"
            "    import pkg.upper\n"
            "    return fn\n"
            "def lower(fn):\n"
            "    import pkg.lower\n"
            "    return fn\n"
            "@upper\n"
            "@lower\n"
            "def f():\n"
            "    pass\n"
        ),
        ("pkg.lower", "pkg.upper"),
        "UNKNOWN",
        id="stacked-decorator-import-order",
    ),
    pytest.param(
        (
            "def deco(cls):\n"
            "    import pkg.decorate\n"
            "    return cls\n"
            "@deco\n"
            "class C:\n"
            "    import pkg.body\n"
        ),
        ("pkg.body", "pkg.decorate"),
        "UNKNOWN",
        id="class-body-before-decorator",
    ),
    pytest.param(
        (
            "def default():\n"
            "    import pkg.default\n"
            "    return 7\n"
            "def deco(fn):\n"
            "    import pkg.decorate\n"
            "    return fn\n"
            "@deco\n"
            "def f(x=default()):\n"
            "    pass\n"
        ),
        ("pkg.default", "pkg.decorate"),
        "UNKNOWN",
        id="default-before-decorator-application",
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


@pytest.mark.parametrize("source,expected_imports,expected_model_outcome", CASES)
def test_minimal_decorator_import_effects(
    tmp_path: Path,
    source: str,
    expected_imports: tuple[str, ...],
    expected_model_outcome: str,
):
    package = tmp_path / "pkg"
    package.mkdir()

    (package / "__init__.py").write_text(
        source,
        encoding="utf-8",
    )

    child_names = {
        "child",
        "upper",
        "lower",
        "body",
        "decorate",
        "default",
    }

    for name in child_names:
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

    assert observed["error"] is None
    assert observed["imports"] == list(expected_imports)

    sources = {
        "pkg.__init__": ast.parse(source),
    }

    for name in child_names:
        sources["pkg." + name] = ast.parse("pass\n")

    result = evaluate_package_import_order(
        sources,
        "pkg",
    )

    assert result.outcome == expected_model_outcome
