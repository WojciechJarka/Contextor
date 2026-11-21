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


@pytest.mark.parametrize(
    "source,children,expected_imports,expected_calls",
    [
        pytest.param(
            (
                "def deco(fn):\n"
                "    import pkg.decorate\n"
                "    return fn\n"
                "def g():\n"
                "    import pkg.default\n"
                "@deco\n"
                "def f(x=g()):\n"
                "    pass\n"
            ),
            {"pkg.decorate": "pass", "pkg.default": "pass"},
            ("pkg.default", "pkg.decorate"),
            ("g", "deco"),
            id="single-decorator-default",
        ),
        pytest.param(
            (
                "def upper_decorator(fn):\n"
                "    import pkg.upper\n"
                "    return fn\n"
                "def lower_decorator(fn):\n"
                "    import pkg.lower\n"
                "    return fn\n"
                "def g():\n"
                "    import pkg.default\n"
                "@upper_decorator\n"
                "@lower_decorator\n"
                "def f(x=g()):\n"
                "    pass\n"
            ),
            {
                "pkg.upper": "pass",
                "pkg.lower": "pass",
                "pkg.default": "pass",
            },
            ("pkg.default", "pkg.lower", "pkg.upper"),
            ("g", "lower_decorator", "upper_decorator"),
            id="stacked-decorators-default",
        ),
    ],
)
def test_p6_decorated_default_effect_order(
    source,
    children,
    expected_imports,
    expected_calls,
):
    result = _p6_boundary_model(source, children)

    assert result.outcome == "MODEL_PASS"

    imports = tuple(
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target in children
    )
    assert imports == expected_imports

    calls = tuple(
        event.symbol
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    )
    assert calls == expected_calls

    definitions = [
        event
        for event in result.events
        if event.operation == "DEFINE_OPAQUE_FUNCTION"
        and event.symbol == "f"
    ]
    assert len(definitions) == 1


def test_p6_missing_decorator_precedes_default():
    result = _p6_boundary_model(
        "def g():\n"
        "    import pkg.default\n"
        "@missing\n"
        "def f(x=g()):\n"
        "    pass\n",
        {"pkg.default": "pass"},
    )

    assert result.outcome == "UNKNOWN"
    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.default"
        for event in result.events
    )


def test_p6_noncallable_decorator_after_default():
    result = _p6_boundary_model(
        "deco = None\n"
        "def g():\n"
        "    import pkg.default\n"
        "@deco\n"
        "def f(x=g()):\n"
        "    pass\n",
        {"pkg.default": "pass"},
    )

    assert result.outcome == "UNKNOWN"
    assert any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.default"
        for event in result.events
    )
    assert not any(
        event.operation == "CALL_FUNCTION"
        and event.symbol == "deco"
        for event in result.events
    )


def test_p6_unmodeled_decorator_rebinding_unknown():
    result = _p6_boundary_model(
        "def deco(fn):\n"
        "    import pkg.original\n"
        "    return fn\n"
        "def g():\n"
        "    import pkg.child\n"
        "@deco\n"
        "def f(x=g()):\n"
        "    pass\n",
        {
            "pkg.child": "import pkg\npkg.deco = None\n",
            "pkg.original": "pass",
        },
    )

    assert result.outcome == "UNKNOWN"


def test_p6_decorated_opaque_later_call_unknown():
    result = _p6_boundary_model(
        "def deco(fn):\n"
        "    return fn\n"
        "def g():\n"
        "    import pkg.default\n"
        "@deco\n"
        "def f(x=g()):\n"
        "    pass\n"
        "f()\n",
        {"pkg.default": "pass"},
    )

    assert result.outcome == "UNKNOWN"
    assert any(
        event.operation == "DEFINE_OPAQUE_FUNCTION"
        and event.symbol == "f"
        for event in result.events
    )


def test_p6_decorated_default_early_binding_hazard():
    result = _p6_boundary_model(
        "def deco(fn):\n"
        "    return fn\n"
        "def g():\n"
        "    import pkg.child\n"
        "@deco\n"
        "def f(x=g()):\n"
        "    pass\n",
        {"pkg.child": "from pkg import f"},
    )

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "f"


def test_p6_decorated_opaque_child_collision_unknown():
    result = _p6_boundary_model(
        "def deco(fn):\n"
        "    return fn\n"
        "def g():\n"
        "    return\n"
        "@deco\n"
        "def child(x=g()):\n"
        "    pass\n",
        {"pkg.child": "pass"},
    )

    assert result.outcome == "UNKNOWN"


def test_p6_stacked_decorator_child_name_collision_unknown():
    result = _p6_boundary_model(
        "def upper(fn):\n"
        "    import pkg.upper\n"
        "    return fn\n"
        "def lower(fn):\n"
        "    import pkg.lower\n"
        "    return fn\n"
        "def g():\n"
        "    import pkg.default\n"
        "@upper\n"
        "@lower\n"
        "def f(x=g()):\n"
        "    pass\n",
        {
            "pkg.upper": "pass",
            "pkg.lower": "pass",
            "pkg.default": "pass",
        },
    )

    assert result.outcome == "UNKNOWN"
    assert result.target_module == "pkg"
    assert result.symbol is None
    assert result.events == ()


def test_p6_decorator_import_before_final_binding():
    result = _p6_boundary_model(
        "def deco(fn):\n"
        "    import pkg.child\n"
        "    return fn\n"
        "def g():\n"
        "    return\n"
        "@deco\n"
        "def f(x=g()):\n"
        "    pass\n",
        {"pkg.child": "from pkg import f"},
    )

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "f"
    assert tuple(
        event.symbol
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    ) == ("g", "deco")


def test_p6_decorator_same_name_as_defined_function():
    result = _p6_boundary_model(
        "def f(fn):\n"
        "    return fn\n"
        "def g():\n"
        "    import pkg.default\n"
        "@f\n"
        "def f(x=g()):\n"
        "    pass\n",
        {"pkg.default": "pass"},
    )

    assert result.outcome == "MODEL_PASS"
    assert tuple(
        event.symbol
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    ) == ("g", "f")
    assert sum(
        event.operation == "DEFINE_OPAQUE_FUNCTION"
        and event.symbol == "f"
        for event in result.events
    ) == 1


def test_p6_keyword_only_defaults_before_decorator():
    result = _p6_boundary_model(
        "def deco(fn):\n"
        "    import pkg.decorate\n"
        "    return fn\n"
        "def g():\n"
        "    import pkg.a\n"
        "def h():\n"
        "    import pkg.b\n"
        "@deco\n"
        "def f(x=1, *, y=g(), z=h()):\n"
        "    pass\n",
        {
            "pkg.a": "pass",
            "pkg.b": "pass",
            "pkg.decorate": "pass",
        },
    )

    assert result.outcome == "MODEL_PASS"
    assert tuple(
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target in {
            "pkg.a", "pkg.b", "pkg.decorate"
        }
    ) == ("pkg.a", "pkg.b", "pkg.decorate")
    assert tuple(
        event.symbol
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    ) == ("g", "h", "deco")


def test_p6_cross_module_decorator_with_default():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.decorators": ast.parse(
            "def deco(fn):\n"
            "    import pkg.decorate\n"
            "    return fn\n"
        ),
        "pkg.app": ast.parse(
            "from pkg.decorators import deco\n"
            "def g():\n"
            "    import pkg.default\n"
            "@deco\n"
            "def f(x=g()):\n"
            "    pass\n"
        ),
        "pkg.default": ast.parse("pass"),
        "pkg.decorate": ast.parse("pass"),
    }

    result = evaluate_package_import_order(
        sources, "pkg.app"
    )

    assert result.outcome == "MODEL_PASS"
    assert tuple(
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target in {
            "pkg.default", "pkg.decorate"
        }
    ) == ("pkg.default", "pkg.decorate")
    assert tuple(
        event.symbol
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    ) == ("g", "deco")
    assert sum(
        event.operation == "DEFINE_OPAQUE_FUNCTION"
        and event.symbol == "f"
        and event.module == "pkg.app"
        for event in result.events
    ) == 1
