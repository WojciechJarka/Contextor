"""Native CPython 3.15 namespace-cycle execution contracts.

All runtime scenarios execute using the interpreter running pytest.
Older CPython installations are not required.

These tests do not certify LIVE runtime safety or warning suppression.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


_SAFE_NESTED = {
    "ctxpkg/__init__.py": "pass\n",
    "ctxpkg/ns/a.py": "value=1\nimport ctxpkg.ns.b\n",
    "ctxpkg/ns/b.py": "from ctxpkg.ns.a import value\nx=value\n",
}

_HAZARD_NESTED = {
    "ctxpkg/__init__.py": "pass\n",
    "ctxpkg/ns/a.py": "import ctxpkg.ns.b\nvalue=1\n",
    "ctxpkg/ns/b.py": "from ctxpkg.ns.a import value\nx=value\n",
}

_SAFE_TOP = {
    "ctxns/a.py": "value=1\nimport ctxns.b\n",
    "ctxns/b.py": "from ctxns.a import value\nx=value\n",
}

_HAZARD_ATTRIBUTE = {
    "ctxns/a.py": "import ctxns.b\nvalue=1\n",
    "ctxns/b.py": "import ctxns.a\nx=ctxns.a.value\n",
}

_CLASS_EAGER = {
    "ctxns/a.py": (
        "class C:\n"
        "    import ctxns.b\n"
        "value=1\n"
    ),
    "ctxns/b.py": "from ctxns.a import value\nx=value\n",
}

_FUNCTION_DEFERRED = {
    "ctxns/a.py": (
        "def load():\n"
        "    import ctxns.b\n"
        "value=1\n"
    ),
    "ctxns/b.py": "import ctxns.a\nx=ctxns.a.value\n",
}

_TWO_PORTIONS = (
    {"ctxns/a.py": "value=1\nimport ctxns.b\n"},
    {"ctxns/b.py": "from ctxns.a import value\nx=value\n"},
)

_SHADOWED = (
    _SAFE_TOP,
    {"ctxns/__init__.py": "value=99\n"},
)

CASES = (
    ("nested_safe_a", (_SAFE_NESTED,), "ctxpkg.ns.a", None),
    ("nested_safe_b", (_SAFE_NESTED,), "ctxpkg.ns.b", None),
    ("nested_hazard_a", (_HAZARD_NESTED,), "ctxpkg.ns.a", "ImportError"),
    ("nested_hazard_b", (_HAZARD_NESTED,), "ctxpkg.ns.b", None),
    ("top_safe_a", (_SAFE_TOP,), "ctxns.a", None),
    ("top_safe_b", (_SAFE_TOP,), "ctxns.b", None),
    ("two_portions_a", _TWO_PORTIONS, "ctxns.a", None),
    ("two_portions_b", _TWO_PORTIONS, "ctxns.b", None),
    (
        "parent_attribute_hazard_a",
        (_HAZARD_ATTRIBUTE,),
        "ctxns.a",
        "AttributeError",
    ),
    (
        "parent_attribute_hazard_b",
        (_HAZARD_ATTRIBUTE,),
        "ctxns.b",
        None,
    ),
    ("class_eager_a", (_CLASS_EAGER,), "ctxns.a", "ImportError"),
    ("class_eager_b", (_CLASS_EAGER,), "ctxns.b", None),
    ("function_deferred_a", (_FUNCTION_DEFERRED,), "ctxns.a", None),
    ("function_deferred_b", (_FUNCTION_DEFERRED,), "ctxns.b", None),
    (
        "regular_package_shadows_namespace",
        _SHADOWED,
        "ctxns.a",
        "ModuleNotFoundError",
    ),
)


def _require_cpython315() -> str:
    if (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 15)
    ):
        pytest.fail(
            "CONTEXTOR_TEST_RUNTIME_REQUIRES_CPYTHON_315"
        )

    return sys.executable


def _execute(
    tmp_path,
    portions,
    entry,
    *,
    script_extra="",
):
    interpreter = _require_cpython315()
    paths = []

    for number, files in enumerate(portions):
        root = tmp_path / ("portion_" + str(number))
        paths.append(str(root))

        for relative, body in files.items():
            target = root / relative
            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            target.write_text(
                body,
                encoding="utf-8",
            )

    script = (
        "import importlib, json, sys\n"
        "sys.path[:0] = json.loads(sys.argv[1])\n"
        "module = importlib.import_module(sys.argv[2])\n"
        + script_extra
    )

    return subprocess.run(
        (
            interpreter,
            "-I",
            "-B",
            "-X",
            "lazy_imports=normal",
            "-c",
            script,
            json.dumps(paths),
            entry,
        ),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize(
    "scenario,portions,entry,error",
    CASES,
    ids=[case[0] for case in CASES],
)
def test_namespace_cycle_entry_matrix(
    tmp_path,
    scenario,
    portions,
    entry,
    error,
):
    result = _execute(
        tmp_path,
        portions,
        entry,
    )

    if error is None:
        assert result.returncode == 0, (
            "CPython 3.15",
            scenario,
            result.stderr,
        )
    else:
        assert result.returncode != 0, (
            "CPython 3.15",
            scenario,
        )
        assert (
            result.stderr.strip()
            .splitlines()[-1]
            .startswith(error + ":")
        ), (
            "CPython 3.15",
            scenario,
            result.stderr,
        )


@pytest.mark.parametrize(
    "sources,entry",
    (
        (
            {
                "ctxns.a": _SAFE_TOP["ctxns/a.py"],
                "ctxns.b": _SAFE_TOP["ctxns/b.py"],
            },
            "ctxns.a",
        ),
        (
            {
                "ctxpkg.__init__": "pass",
                "ctxpkg.ns.a": _HAZARD_NESTED[
                    "ctxpkg/ns/a.py"
                ],
                "ctxpkg.ns.b": _HAZARD_NESTED[
                    "ctxpkg/ns/b.py"
                ],
            },
            "ctxpkg.ns.a",
        ),
    ),
)
def test_restricted_regular_model_remains_unknown(
    sources,
    entry,
):
    assessment = evaluate_package_import_order(
        {
            name: ast.parse(body)
            for name, body in sources.items()
        },
        entry,
    )

    assert assessment.outcome == "UNKNOWN"
    assert assessment.events == ()


def test_315_lazy_import_defers_cycle(tmp_path):
    portions = (
        {
            "ctxns/a.py": (
                "lazy import ctxns.b\n"
                "value=1\n"
            ),
            "ctxns/b.py": (
                "from ctxns.a import value\n"
                "x=value\n"
            ),
        },
    )

    result = _execute(
        tmp_path,
        portions,
        "ctxns.a",
        script_extra=(
            "assert 'ctxns.b' not in sys.modules\n"
            "assert module.ctxns.b.x == 1\n"
            "assert 'ctxns.b' in sys.modules\n"
        ),
    )

    assert result.returncode == 0, result.stderr


def test_315_eager_import_still_has_hazard(tmp_path):
    portions = (
        {
            "ctxns/a.py": (
                "import ctxns.b\n"
                "value=1\n"
            ),
            "ctxns/b.py": (
                "from ctxns.a import value\n"
                "x=value\n"
            ),
        },
    )

    result = _execute(
        tmp_path,
        portions,
        "ctxns.a",
    )

    assert result.returncode != 0
    assert result.stderr.strip().splitlines()[-1].startswith(
        "ImportError:"
    ), result.stderr


def test_required_cpython315_runtime_gate():
    assert sys.implementation.name == "cpython"
    assert sys.version_info[:2] == (3, 15)
    assert sys.executable
