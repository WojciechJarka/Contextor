"""Restricted named class decorator execution and fail-closed boundaries."""

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
        "class C:\n    pass\n", None, (), "MODEL_PASS", (), (),
        id="A-undecorated-class",
    ),
    pytest.param(
        "def deco(cls):\n    return cls\n"
        "deco = None\n@deco\nclass C:\n    pass\n",
        "TypeError", (), "UNKNOWN", (), (),
        id="B-overwritten-decorator",
    ),
    pytest.param(
        "def deco(cls):\n    import pkg.effect\n    return\n"
        "@deco\nclass C:\n    pass\nC()\n",
        "TypeError", ("pkg.effect",), "UNKNOWN", ("deco",),
        ("pkg.effect",), id="C-final-none-called",
    ),
    pytest.param(
        "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n",
        None, (), "MODEL_PASS", ("C",), (),
        id="D-same-name",
    ),
    pytest.param(
        "def top_decorator(cls):\n"
        "    import pkg.top\n"
        "    return cls\n"
        "def bottom_decorator(cls):\n"
        "    import pkg.bottom\n"
        "    return cls\n"
        "@top_decorator\n"
        "@bottom_decorator\n"
        "class C:\n"
        "    pass\n",
        None, ("pkg.bottom", "pkg.top"), "MODEL_PASS",
        ("bottom_decorator", "top_decorator"),
        ("pkg.bottom", "pkg.top"),
        id="E-two-pass-through",
    ),
    pytest.param(
        "def deco(cls):\n    import pkg.effect\n    return cls\n"
        "@deco\nclass C:\n    import pkg.body\n",
        None, ("pkg.body", "pkg.effect"), "MODEL_PASS",
        ("deco",), ("pkg.body", "pkg.effect"),
        id="F-body-before-decorator",
    ),
    pytest.param(
        "@factory.decorate\nclass C:\n    pass\n",
        "NameError", (), "UNKNOWN", (), (),
        id="G-attribute-decorator",
    ),
    pytest.param(
        "def deco(cls):\n    return cls\n"
        "class Meta(type):\n    def __new__(mcls, name, bases, ns):\n"
        "        return super().__new__(mcls, name, bases, ns)\n"
        "@deco\nclass C(metaclass=Meta):\n    pass\n",
        None, (), "UNKNOWN", (), (),
        id="H-unsupported-metaclass",
    ),
    pytest.param(
        "def deco(cls):\n    return cls\n"
        "class X: pass\nclass Y: pass\n"
        "class A(X, Y): pass\nclass B(Y, X): pass\n"
        "@deco\nclass C(A, B): pass\n",
        "TypeError", (), "UNKNOWN", (), (),
        id="I-conflicting-mro",
    ),
    pytest.param(
        "def deco(cls):\n    return cls\n"
        "@deco\nclass child:\n    pass\n",
        None, (), "UNKNOWN", (), (),
        id="J-indexed-child-name-collision",
    ),
]


@pytest.mark.parametrize(
    "source,error,imports,outcome,calls,starts", CASES,
)
def test_named_class_decorator_execution(
    tmp_path, source, error, imports, outcome, calls, starts,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")
    child_names = ("effect", "body", "top", "bottom", "child")
    sources = {"pkg.__init__": ast.parse(source)}
    for name in child_names:
        (package / f"{name}.py").write_text("pass\n", encoding="utf-8")
        sources[f"pkg.{name}"] = ast.parse("pass\n")

    process = subprocess.run(
        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {
        "error": error, "imports": list(imports),
    }

    result = evaluate_package_import_order(sources, "pkg")
    assert result.outcome == outcome, [
        event.__dict__ for event in result.events
    ]
    assert tuple(
        event.symbol for event in result.events
        if event.operation == "CALL_FUNCTION"
    ) == calls
    assert tuple(
        event.target for event in result.events
        if event.operation == "START_IMPORT"
        and event.target is not None
        and event.target.startswith("pkg.")
    ) == starts
    if outcome == "MODEL_PASS":
        assert any(
            event.operation == "DEFINE_PASSIVE_CLASS"
            and event.symbol == "C"
            for event in result.events
        )
