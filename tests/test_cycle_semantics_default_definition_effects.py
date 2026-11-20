import ast

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


CASES = [
    pytest.param(
        (
            "def g():\n"
            "    import pkg.child\n"
            "def f(x=g()):\n"
            "    pass\n"
        ),
        {"pkg.child": "pass"},
        "MODEL_PASS",
        ("pkg.child",),
        id="single-default-import",
    ),
    pytest.param(
        (
            "def g():\n"
            "    import pkg.a\n"
            "def h():\n"
            "    import pkg.b\n"
            "def f(x=g(), y=h()):\n"
            "    pass\n"
        ),
        {"pkg.a": "pass", "pkg.b": "pass"},
        "MODEL_PASS",
        ("pkg.a", "pkg.b"),
        id="sequential-default-imports",
    ),
    pytest.param(
        (
            "def g():\n"
            "    import pkg.child\n"
            "def f(x=g()):\n"
            "    pass\n"
            "g = None\n"
        ),
        {"pkg.child": "pass"},
        "MODEL_PASS",
        ("pkg.child",),
        id="rebind-after-default",
    ),
    pytest.param(
        (
            "def g():\n"
            "    import pkg.child\n"
            "g = None\n"
            "def f(x=g()):\n"
            "    pass\n"
        ),
        {"pkg.child": "pass"},
        "UNKNOWN",
        (),
        id="rebind-before-default",
    ),
    pytest.param(
        (
            "def g():\n"
            "    import pkg.child\n"
            "    return 10\n"
            "def f(x=g()):\n"
            "    pass\n"
        ),
        {"pkg.child": "pass"},
        "UNKNOWN",
        (),
        id="unsupported-return",
    ),
]


@pytest.mark.parametrize(
    "source,children,expected_outcome,expected_imports",
    CASES,
)
def test_default_definition_effects(
    source,
    children,
    expected_outcome,
    expected_imports,
):
    sources = {
        "pkg.__init__": ast.parse(source),
        **{
            name: ast.parse(child_source)
            for name, child_source in children.items()
        },
    }

    result = evaluate_package_import_order(
        sources,
        "pkg",
    )

    assert result.outcome == expected_outcome

    if expected_outcome == "UNKNOWN":
        return

    events = list(result.events)

    definition_positions = [
        index
        for index, event in enumerate(events)
        if (
            event.operation == "DEFINE_OPAQUE_FUNCTION"
            and event.symbol == "f"
        )
    ]

    assert len(definition_positions) == 1
    definition_position = definition_positions[0]

    observed_positions = []

    for target in expected_imports:
        positions = [
            index
            for index, event in enumerate(events)
            if (
                event.operation == "START_IMPORT"
                and event.target == target
            )
        ]

        assert len(positions) == 1
        observed_positions.append(positions[0])

    assert observed_positions == sorted(observed_positions)
    assert all(
        position < definition_position
        for position in observed_positions
    )


def _p6_boundary_model(source, children):
    sources = {
        "pkg.__init__": ast.parse(source),
        **{
            name: ast.parse(code)
            for name, code in children.items()
        },
    }
    return evaluate_package_import_order(sources, "pkg")


def test_p6_keyword_only_default_order():
    result = _p6_boundary_model(
        "def g():\n"
        "    import pkg.a\n"
        "def h():\n"
        "    import pkg.b\n"
        "def f(*, x=g(), y=h()):\n"
        "    pass\n",
        {"pkg.a": "pass", "pkg.b": "pass"},
    )
    assert result.outcome == "MODEL_PASS"
    imports = [
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target in {"pkg.a", "pkg.b"}
    ]
    assert imports == ["pkg.a", "pkg.b"]


def test_p6_repeated_default_call():
    result = _p6_boundary_model(
        "def g():\n"
        "    import pkg.child\n"
        "def f(x=g(), y=g()):\n"
        "    pass\n",
        {"pkg.child": "pass"},
    )
    assert result.outcome == "MODEL_PASS"
    calls = [
        event.symbol
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    ]
    assert calls == ["g", "g"]
    imports = [
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target == "pkg.child"
    ]
    assert imports == ["pkg.child"]


def test_p6_alias_rebinding_before_default():
    result = _p6_boundary_model(
        "def g():\n"
        "    import pkg.a\n"
        "def h():\n"
        "    import pkg.b\n"
        "g = h\n"
        "def f(x=g()):\n"
        "    pass\n",
        {"pkg.a": "pass", "pkg.b": "pass"},
    )
    assert result.outcome == "MODEL_PASS"
    imports = [
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target in {"pkg.a", "pkg.b"}
    ]
    assert imports == ["pkg.b"]


def test_p6_later_opaque_call_remains_unknown():
    result = _p6_boundary_model(
        "def g():\n"
        "    import pkg.child\n"
        "def f(x=g()):\n"
        "    pass\n"
        "f()\n",
        {"pkg.child": "pass"},
    )
    assert result.outcome == "UNKNOWN"
    assert any(
        event.operation == "DEFINE_OPAQUE_FUNCTION"
        and event.symbol == "f"
        for event in result.events
    )


def test_p6_import_before_function_binding():
    result = _p6_boundary_model(
        "def g():\n"
        "    import pkg.child\n"
        "def f(x=g()):\n"
        "    pass\n",
        {"pkg.child": "from pkg import f"},
    )
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "f"
    assert any(
        event.operation == "EARLY_BINDING_HAZARD"
        and event.target == "pkg"
        and event.symbol == "f"
        for event in result.events
    )
