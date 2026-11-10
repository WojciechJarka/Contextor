import ast
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


CASES = [
    pytest.param(
        (
            "def f():\n"
            "    return\n"
            "    import pkg.child\n"
            "f()\n"
        ),
        (),
        "MODEL_PASS",
        id="return-skips-import",
    ),
    pytest.param(
        (
            "def f():\n"
            "    import pkg.first\n"
            "    return\n"
            "    import pkg.child\n"
            "f()\n"
        ),
        ("pkg.first",),
        "MODEL_PASS",
        id="import-before-return-only",
    ),
    pytest.param(
        (
            "def f():\n"
            "    return\n"
            "    import pkg.child\n"
            "g = f\n"
            "g()\n"
            "import pkg.after\n"
        ),
        ("pkg.after",),
        "MODEL_PASS",
        id="alias-return-resumes-module",
    ),
    pytest.param(
        (
            "def f():\n"
            "    return 7\n"
            "    import pkg.child\n"
            "f()\n"
        ),
        (),
        "UNKNOWN",
        id="valued-return-still-unknown",
    ),
]


@pytest.mark.parametrize(
    "source,expected_imports,expected_outcome",
    CASES,
)
def test_bare_return_frame_and_cpython(
    tmp_path,
    source,
    expected_imports,
    expected_outcome,
):
    package = tmp_path / "pkg"
    package.mkdir()

    (package / "__init__.py").write_text(
        source, encoding="utf-8"
    )

    for name in ("child", "first", "after"):
        (package / (name + ".py")).write_text(
            "pass\n", encoding="utf-8"
        )

    runner = """
import builtins
import importlib
import json
import sys

sys.path.insert(0, sys.argv[1])
original = builtins.__import__
observed = []

def traced(name, *args, **kwargs):
    if name.startswith("pkg."):
        observed.append(name)
    return original(name, *args, **kwargs)

builtins.__import__ = traced

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

    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            runner,
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert process.returncode == 0, process.stderr

    import json
    observed = json.loads(process.stdout)

    assert observed["error"] is None
    assert observed["imports"] == list(expected_imports)

    sources = {
        "pkg.__init__": ast.parse(source),
    }

    for name in ("child", "first", "after"):
        sources["pkg." + name] = ast.parse("pass\n")

    result = evaluate_package_import_order(
        sources,
        "pkg",
    )

    assert result.outcome == expected_outcome

    if expected_outcome == "MODEL_PASS":
        imported = [
            event.target
            for event in result.events
            if event.operation == "START_IMPORT"
            and event.target in {
                "pkg.child",
                "pkg.first",
                "pkg.after",
            }
        ]

        assert imported == list(expected_imports)

    if expected_outcome == "UNKNOWN":
        assert not any(
            event.operation == "CALL_FUNCTION"
            for event in result.events
        )
