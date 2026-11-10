from contextor.core.cycle_semantics.execution.state import (
    _FunctionFrame,
    _advance_frame,
    _frame_module,
    _frame_position,
)
from contextor.core.cycle_semantics.execution.steps import (
    _Step,
)


def test_each_call_has_independent_local_environment():
    body = (_Step("PASS"),)

    first = _FunctionFrame("pkg", 0, body)
    second = _FunctionFrame("pkg", 0, body)

    assert first is not second
    assert first.local_bindings is not second.local_bindings
    assert first.local_bindings == {}
    assert second.local_bindings == {}

    first.local_bindings["value"] = 7

    assert first.local_bindings == {"value": 7}
    assert second.local_bindings == {}


def test_advancement_preserves_same_local_environment():
    body = (_Step("PASS"),)

    initial = _FunctionFrame("pkg", 0, body)
    initial.local_bindings["argument"] = "item"

    advanced = _advance_frame(initial)

    assert isinstance(advanced, _FunctionFrame)
    assert advanced is not initial
    assert advanced.index == 1
    assert advanced.steps is body
    assert (
        advanced.local_bindings
        is initial.local_bindings
    )

    advanced.local_bindings["local"] = 12

    assert initial.local_bindings["local"] == 12
    assert _frame_module(advanced) == "pkg"
    assert _frame_position(advanced) == ("pkg", 1)


def test_nested_calls_do_not_share_local_environment():
    body = (_Step("PASS"),)

    outer = _FunctionFrame("pkg", 0, body)
    inner = _FunctionFrame("pkg", 0, body)

    outer.local_bindings["x"] = 1
    inner.local_bindings["x"] = 2

    assert outer.local_bindings["x"] == 1
    assert inner.local_bindings["x"] == 2

    resumed = _advance_frame(outer)

    assert resumed.local_bindings is outer.local_bindings
    assert resumed.local_bindings is not inner.local_bindings


def test_module_frame_does_not_acquire_function_locals():
    module_frame = ("pkg", 4)

    advanced = _advance_frame(module_frame)

    assert advanced == ("pkg", 5)
    assert type(advanced) is tuple


def test_frame_equality_does_not_depend_on_mutable_locals():
    body = (_Step("PASS"),)

    first = _FunctionFrame("pkg", 0, body)
    second = _FunctionFrame("pkg", 0, body)

    assert first == second

    first.local_bindings["x"] = 3

    assert first == second
    assert first.local_bindings is not second.local_bindings
