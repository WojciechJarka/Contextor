import ast
import json
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.execution.calls import (
    _execute_restricted_call,
    _new_restricted_function,
)
from contextor.core.cycle_semantics.execution.state import (
    _FunctionFrame,
    _advance_frame,
)
from contextor.core.cycle_semantics.execution.steps import _Step
from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
from test_cycle_semantics_decorator_import_effect_baseline import RUNNER


CASES = [
    pytest.param(
        "def original():\n    import pkg.child\ndef identity(fn):\n    return fn\nalias = identity(original)\nalias()\n",
        None, ("pkg.child",), "MODEL_PASS", ("identity", "alias"),
        id="pass-through-identity",
    ),
    pytest.param(
        "def original():\n    import pkg.child\nsaved = original\ndef identity(fn):\n    return fn\noriginal = None\nalias = identity(saved)\nalias()\n",
        None, ("pkg.child",), "MODEL_PASS", ("identity", "alias"),
        id="alias-after-rebinding",
    ),
    pytest.param(
        "def one():\n    import pkg.first\ndef two():\n    import pkg.second\ndef identity(fn):\n    return fn\na = identity(one)\nb = identity(two)\na()\nb()\n",
        None, ("pkg.first", "pkg.second"), "MODEL_PASS",
        ("identity", "identity", "a", "b"),
        id="independent-calls",
    ),
    pytest.param(
        "def f():\n    return\nresult = f()\n",
        None, (), "MODEL_PASS", ("f",), id="bare-return-assigned",
    ),
    pytest.param(
        "def f():\n    pass\nresult = f()\n",
        None, (), "MODEL_PASS", ("f",), id="natural-completion-assigned",
    ),
    pytest.param(
        "def identity(fn):\n    return fn\nalias = identity(missing)\n",
        "NameError", (), "UNKNOWN", (), id="unresolved-argument-name",
    ),
    pytest.param(
        "def original():\n    pass\ndef f():\n    return original\nalias = f()\n",
        None, (), "UNKNOWN", (), id="unsupported-global-return-lookup",
    ),
    pytest.param(
        "def identity(fn):\n    return fn\nalias = identity(7)\nalias()\n",
        "TypeError", (), "UNKNOWN", ("identity",),
        id="returned-noncallable",
    ),
    pytest.param(
        "def f(x):\n    import pkg.child as x\n    return x\nresult = f(7)\n",
        None, ("pkg.child",), "UNKNOWN", (),
        id="local-import-shadows-parameter",
    ),
]


@pytest.mark.parametrize(
    "source,expected_error,expected_imports,expected_outcome,expected_calls",
    CASES,
)
def test_return_value_transport_matches_cpython(
    tmp_path, source, expected_error, expected_imports,
    expected_outcome, expected_calls,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")
    for child in ("child", "first", "second"):
        (package / f"{child}.py").write_text("pass\n", encoding="utf-8")

    process = subprocess.run(
        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {
        "error": expected_error,
        "imports": list(expected_imports),
    }

    sources = {"pkg.__init__": ast.parse(source)}
    for child in ("child", "first", "second"):
        sources[f"pkg.{child}"] = ast.parse("pass\n")
    result = evaluate_package_import_order(sources, "pkg")
    assert result.outcome == expected_outcome
    assert tuple(
        event.symbol for event in result.events
        if event.operation == "CALL_FUNCTION"
    ) == expected_calls
    if expected_outcome == "MODEL_PASS":
        assert tuple(
            event.target for event in result.events
            if event.operation == "START_IMPORT"
            and event.target in {"pkg.child", "pkg.first", "pkg.second"}
        ) == expected_imports
    else:
        assert not any(
            event.operation == "START_IMPORT"
            and event.target in {"pkg.child", "pkg.first", "pkg.second"}
            for event in result.events
        )


def test_returned_function_retains_object_identity():
    body = (_Step("RETURN_FUNCTION"),)
    function = _new_restricted_function("pkg", body)
    local_bindings = {"fn": function}
    frame = _FunctionFrame("pkg", 0, body, local_bindings, "alias")
    advanced = _advance_frame(frame)
    assert advanced.result_binding == "alias"
    assert advanced.local_bindings is local_bindings
    assert local_bindings["fn"] is function
    assert _execute_restricted_call(
        _Step("CALL_FUNCTION", target="alias"), module="pkg",
        namespaces={"pkg": {"alias": function}}, local_bindings={},
    ) is body


def test_foreign_function_remains_rejected():
    foreign = _new_restricted_function("other", ())
    assert _execute_restricted_call(
        _Step("CALL_FUNCTION", target="alias"), module="pkg",
        namespaces={"pkg": {"alias": foreign}}, local_bindings={},
    ) is None
