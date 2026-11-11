import ast
import json
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.execution.calls import (
    _execute_restricted_call,
    _new_restricted_function,
)
from contextor.core.cycle_semantics.execution.state import _FunctionFrame
from contextor.core.cycle_semantics.execution.steps import _Step
from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)
from test_cycle_semantics_decorator_import_effect_baseline import RUNNER


CASES = [
    pytest.param(
        "def f(x):\n    import pkg.child\nf(7)\n",
        None,
        ("pkg.child",),
        "MODEL_PASS",
        id="required-argument-import",
    ),
    pytest.param(
        "def f(x):\n    import pkg.child\ng = f\ng(7)\n",
        None,
        ("pkg.child",),
        "MODEL_PASS",
        id="alias-preserves-parameter-signature",
    ),
    pytest.param(
        "def f(x):\n    import pkg.child\n    return\n    import pkg.after\nf(7)\n",
        None,
        ("pkg.child",),
        "MODEL_PASS",
        id="argument-with-bare-return",
    ),
    pytest.param(
        "def f(x):\n    import pkg.child\nf()\n",
        "TypeError",
        (),
        "UNKNOWN",
        id="missing-argument",
    ),
    pytest.param(
        "def f():\n    import pkg.child\nf(7)\n",
        "TypeError",
        (),
        "UNKNOWN",
        id="excess-argument",
    ),
    pytest.param(
        "def f(x):\n    import pkg.child\nf(7, 8)\n",
        "TypeError",
        (),
        "UNKNOWN",
        id="two-arguments-unsupported",
    ),
]


@pytest.mark.parametrize(
    "source,expected_error,expected_imports,expected_outcome",
    CASES,
)
def test_single_positional_binding_matches_cpython(
    tmp_path,
    source,
    expected_error,
    expected_imports,
    expected_outcome,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")
    for child in ("child", "after"):
        (package / f"{child}.py").write_text("pass\n", encoding="utf-8")

    process = subprocess.run(
        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
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
            "pkg.after": ast.parse("pass\n"),
        },
        "pkg",
    )
    assert result.outcome == expected_outcome
    imported = [
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target in {"pkg.child", "pkg.after"}
    ]
    if expected_outcome == "MODEL_PASS":
        assert imported == list(expected_imports)
    else:
        assert imported == []
        assert not any(
            event.operation == "CALL_FUNCTION"
            for event in result.events
        )


def test_argument_is_bound_in_new_frame():
    body = (_Step("RETURN_FUNCTION"),)
    function = _new_restricted_function("pkg", body, ("x",))
    namespaces = {"pkg": {"f": function}}
    local_bindings = {}
    returned = _execute_restricted_call(
        _Step("CALL_FUNCTION", target="f", call_argument_values=(7,)),
        module="pkg",
        namespaces=namespaces,
        local_bindings=local_bindings,
    )
    frame = _FunctionFrame("pkg", 0, returned, local_bindings)
    assert returned is body
    assert frame.local_bindings == {"x": 7}
    assert frame.local_bindings is local_bindings


def test_two_calls_have_independent_local_bindings():
    function = _new_restricted_function("pkg", (), ("x",))
    namespaces = {"pkg": {"f": function}}
    first = {}
    second = {}
    for value, bindings in ((7, first), (8, second)):
        assert _execute_restricted_call(
            _Step("CALL_FUNCTION", target="f", call_argument_values=(value,)),
            module="pkg",
            namespaces=namespaces,
            local_bindings=bindings,
        ) == ()
    assert first == {"x": 7}
    assert second == {"x": 8}
    assert first is not second


def test_wrong_arity_does_not_bind():
    function = _new_restricted_function("pkg", (), ("x",))
    bindings = {}
    assert _execute_restricted_call(
        _Step("CALL_FUNCTION", target="f"),
        module="pkg",
        namespaces={"pkg": {"f": function}},
        local_bindings=bindings,
    ) is None
    assert bindings == {}


def test_alias_preserves_signature():
    function = _new_restricted_function("pkg", (), ("x",))
    bindings = {}
    assert _execute_restricted_call(
        _Step("CALL_FUNCTION", target="g", call_argument_values=(7,)),
        module="pkg",
        namespaces={"pkg": {"f": function, "g": function}},
        local_bindings=bindings,
    ) == ()
    assert bindings == {"x": 7}


def test_no_argument_function_still_works():
    function = _new_restricted_function("pkg", ())
    bindings = {}
    assert _execute_restricted_call(
        _Step("CALL_FUNCTION", target="f"),
        module="pkg",
        namespaces={"pkg": {"f": function}},
        local_bindings=bindings,
    ) == ()
    assert bindings == {}


def test_foreign_function_is_not_executed():
    function = _new_restricted_function("other", (), ("x",))
    bindings = {}
    assert _execute_restricted_call(
        _Step("CALL_FUNCTION", target="f", call_argument_values=(7,)),
        module="pkg",
        namespaces={"pkg": {"f": function}},
        local_bindings=bindings,
    ) is None
    assert bindings == {}
