"""Regression coverage for function-frame result-owner provenance."""

import ast

from contextor.core.cycle_semantics.execution.state import (
    _FunctionFrame,
    _advance_frame,
)
from contextor.core.cycle_semantics.execution.steps import _Step
from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


def _evaluate_sources(sources, entry_module):
    return evaluate_package_import_order(
        {
            module: ast.parse(source)
            for module, source in sources.items()
        },
        entry_module,
    )


def test_function_frame_binding_module_defaults_to_none():
    frame = _FunctionFrame(
        module="pkg.app",
        index=0,
        steps=(),
    )

    assert frame.binding_module is None


def test_advance_frame_preserves_distinct_binding_module():
    frame = _FunctionFrame(
        module="pkg.execution",
        index=3,
        steps=(),
        binding_module="pkg.results",
    )

    advanced = _advance_frame(frame)

    assert isinstance(advanced, _FunctionFrame)
    assert advanced.module == "pkg.execution"
    assert advanced.index == 4
    assert advanced.binding_module == "pkg.results"


def test_advance_frame_preserves_existing_fields_and_identities():
    steps = (_Step("PASS"),)
    local_bindings = {"fn": object()}
    decorator = object()
    remaining_decorators = (("outer", decorator),)
    frame = _FunctionFrame(
        module="pkg.execution",
        index=5,
        steps=steps,
        local_bindings=local_bindings,
        result_binding="call_result",
        decorator_final_binding="decorated_name",
        remaining_decorators=remaining_decorators,
        binding_module="pkg.results",
    )

    advanced = _advance_frame(frame)

    assert isinstance(advanced, _FunctionFrame)
    assert advanced.module == frame.module
    assert advanced.index == frame.index + 1
    assert advanced.steps is steps
    assert advanced.local_bindings is local_bindings
    assert advanced.result_binding == "call_result"
    assert advanced.decorator_final_binding == "decorated_name"
    assert advanced.remaining_decorators is remaining_decorators
    assert advanced.binding_module == "pkg.results"


def test_local_decorated_function_keeps_call_sequence_and_binding():
    modeled = _evaluate_sources(
        {
            "pkg.__init__": (
                "def deco(fn):\n"
                "    return fn\n"
                "@deco\n"
                "def f():\n"
                "    pass\n"
                "f()\n"
            ),
        },
        "pkg",
    )

    assert modeled.outcome == "MODEL_PASS"
    assert tuple(
        event.symbol
        for event in modeled.events
        if event.operation == "CALL_FUNCTION"
    ) == ("deco", "f")
    assert tuple(
        event.symbol
        for event in modeled.events
        if event.operation == "DEFINE_FUNCTION"
    ) == ("deco", "f")


def test_local_decorated_class_keeps_definition_and_call_sequence():
    modeled = _evaluate_sources(
        {
            "pkg.__init__": (
                "def deco(cls):\n"
                "    return cls\n"
                "@deco\n"
                "class C:\n"
                "    pass\n"
                "class Child(C):\n"
                "    pass\n"
            ),
        },
        "pkg",
    )

    assert modeled.outcome == "MODEL_PASS"
    assert tuple(
        event.symbol
        for event in modeled.events
        if event.operation == "DEFINE_PASSIVE_CLASS"
    ) == ("C", "Child")
    assert tuple(
        event.symbol
        for event in modeled.events
        if event.operation == "CALL_FUNCTION"
    ) == ("deco",)


def test_stacked_decorators_remain_bottom_to_top_without_duplicates():
    modeled = _evaluate_sources(
        {
            "pkg.__init__": (
                "def upper(fn):\n"
                "    return fn\n"
                "def lower(fn):\n"
                "    return fn\n"
                "@upper\n"
                "@lower\n"
                "def f():\n"
                "    pass\n"
                "f()\n"
            ),
        },
        "pkg",
    )

    calls = tuple(
        event.symbol
        for event in modeled.events
        if event.operation == "CALL_FUNCTION"
    )
    assert modeled.outcome == "MODEL_PASS"
    assert calls == ("lower", "upper", "f")
    assert calls.count("lower") == 1
    assert calls.count("upper") == 1


def test_imported_decorator_executes_in_defining_module():
    modeled = _evaluate_sources(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": (
                "def identity(fn):\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\n"
                "def f():\n"
                "    pass\n"
            ),
        },
        "pkg.app",
    )

    assert modeled.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == "identity"
        for event in modeled.events
    )
    calls = tuple(
        event
        for event in modeled.events
        if event.operation == "CALL_FUNCTION"
        and event.symbol == "identity"
    )
    assert len(calls) == 1
    assert calls[0].module == "pkg.app"


def test_external_functools_decorator_remains_unmodeled():
    modeled = _evaluate_sources(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": "pass\n",
            "pkg.app": (
                "from functools import lru_cache\n"
                "@lru_cache\n"
                "def f():\n"
                "    pass\n"
            ),
        },
        "pkg.app",
    )

    assert modeled.outcome == "UNKNOWN"
    assert modeled.target_module == "functools"
    assert modeled.reached_unmodeled_import is not None
    assert (
        modeled.reached_unmodeled_import.operation,
        modeled.reached_unmodeled_import.target,
        modeled.reached_unmodeled_import.symbol,
    ) == ("FROM", "functools", "lru_cache")
    assert not any(
        event.operation == "CALL_FUNCTION"
        and event.symbol == "lru_cache"
        for event in modeled.events
    )
