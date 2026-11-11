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
            "    return fn\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "pass\n",
        None,
        ("pkg.child",),
        "MODEL_PASS",
        ("deco",),
        id="nonconflicting-import",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    import pkg.child as alias\n"
            "    return fn\n"
            "@deco\n"
            "def f():\n"
            "    import pkg.after\n"
            "f()\n"
        ),
        "pass\n",
        None,
        ("pkg.child", "pkg.after"),
        "MODEL_PASS",
        ("deco", "f"),
        id="nonconflicting-import-alias",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    from pkg.child import item as other\n"
            "    return fn\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "item = 7\n",
        None,
        ("pkg.child",),
        "MODEL_PASS",
        ("deco",),
        id="nonconflicting-from-binding",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    import pkg.child as fn\n"
            "    return fn\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "pass\n",
        None,
        ("pkg.child",),
        "UNKNOWN",
        (),
        id="import-alias-overwrites-parameter",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    from pkg.child import item as fn\n"
            "    return fn\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "item = 7\n",
        None,
        ("pkg.child",),
        "UNKNOWN",
        (),
        id="from-import-overwrites-parameter",
    ),
    pytest.param(
        (
            "def deco(pkg):\n"
            "    import pkg.child\n"
            "    return pkg\n"
            "@deco\n"
            "def f():\n"
            "    pass\n"
        ),
        "pass\n",
        None,
        ("pkg.child",),
        "UNKNOWN",
        (),
        id="root-import-overwrites-parameter",
    ),
    pytest.param(
        (
            "def deco(fn):\n"
            "    return fn\n"
            "    import pkg.child as fn\n"
            "@deco\n"
            "def f():\n"
            "    import pkg.after\n"
            "f()\n"
        ),
        "pass\n",
        None,
        ("pkg.after",),
        "MODEL_PASS",
        ("deco", "f"),
        id="unreachable-import-after-return",
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
        "from pkg import f\n",
        "ImportError",
        ("pkg.child",),
        None,
        None,
        id="reentrant-import-before-final-binding",
    ),
]


@pytest.mark.parametrize(
    "source,child_source,error,imports,outcome,calls",
    CASES,
)
def test_import_return_binding_conflict(
    tmp_path,
    source,
    child_source,
    error,
    imports,
    outcome,
    calls,
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
    (package / "after.py").write_text(
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

    actual = json.loads(process.stdout)

    assert actual == {
        "error": error,
        "imports": list(imports),
    }

    result = evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(source),
            "pkg.child": ast.parse(child_source),
            "pkg.after": ast.parse("pass\n"),
        },
        "pkg",
    )

    if outcome is None:
        assert result.outcome != "MODEL_PASS"
        return

    assert result.outcome == outcome

    if calls is not None:
        assert tuple(
            event.symbol
            for event in result.events
            if event.operation == "CALL_FUNCTION"
        ) == calls

    if outcome == "MODEL_PASS":
        assert tuple(
            event.target
            for event in result.events
            if event.operation == "START_IMPORT"
            and event.target in {
                "pkg.child",
                "pkg.after",
            }
        ) == imports
