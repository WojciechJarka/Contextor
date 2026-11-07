import ast

import pytest

from contextor.core.cycle_semantics.package_model import (
    _compile,
    _pure_literal_expression,
    evaluate_package_import_order,
)


def _model(
    body: str,
    *,
    initializer: str = "pass",
    mode=None,
    entry: str = "pkg.child",
):
    return evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(initializer),
            "pkg.child": ast.parse(body),
        },
        entry,
        annotation_semantics=mode,
    )


@pytest.mark.parametrize(
    "source",
    [
        "x = [1, 2, 3]",
        "x = ('a', 'b')",
        "x = {'a', 'b'}",
        "x = {'a': 1, 'b': 2}",
        "x = [1, ('a', {'b': [2, 3]})]",
        "x = -3",
        "x = +2.5",
        "x = -2j",
        "x = []",
        "x = ()",
        "x = {}",
        "x = {(1, 2): 'ok'}",
        "x = {(1, 2), (3, 4)}",
        "__all__ = ['a', 'b']",
        "__all__ = ('a', 'b')",
    ],
)
def test_pure_literal_assignments_pass(source):
    result = _model(source)
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "BIND"
        for event in result.events
    )


@pytest.mark.parametrize(
    "source",
    [
        "x = side_effect()",
        "x = [side_effect()]",
        "x = [v for v in values]",
        "x = {'a': side_effect()}",
        "x = {[]: 1}",
        "x = {[1, 2]}",
        "x = {(1, []): 1}",
        "x = {'a': 1, **other}",
        'x = f"{side_effect()}"',
        "x = other.attribute",
        "x = other[0]",
        "x = 1 / 0",
        "x = [1] * 1000000000",
        "x = y = [1]",
        "obj.x = [1]",
        "__path__ = ['other']",
        "__getattr__ = something",
        "__annotations__ = {}",
        "__all__ = side_effect()",
        "__all__ = [side_effect()]",
        "__all__ = ['a', 7]",
        "__all__ = {'a', 'b'}",
        "x = set()",
        "x = -True",
        "x = --3",
    ],
)
def test_unsupported_assignment_remains_unknown(source):
    assert _model(source).outcome == "UNKNOWN"


def test_pure_literal_depth_budget():
    expression = "[" * 17 + "0" + "]" * 17
    assert _model("x = " + expression).outcome == "UNKNOWN"


def test_pure_literal_node_budget():
    source = "x = [" + ",".join(
        "1" for _ in range(257)
    ) + "]"
    assert _model(source).outcome == "UNKNOWN"


def test_pure_literal_classifier_rejects_calls():
    tree = ast.parse("x = f()")
    expression = tree.body[0].value
    assert _pure_literal_expression(expression) is False


def test_valid_dict_hashability():
    assert _model(
        "x = {(1, (2, 3)): {'a': [4]}}"
    ).outcome == "MODEL_PASS"


@pytest.mark.parametrize(
    "source",
    [
        "class C:\n    x = [1, 2]",
        "class C:\n    x = {'a': 1}",
        "class C:\n    x = (1, 2)\n    y = [3]",
    ],
)
def test_class_local_literal_bindings(source):
    result = _model(source)
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "CLASS_LOCAL_BIND"
        for event in result.events
    )
    assert not any(
        event.operation == "BIND"
        for event in result.events
    )


def test_class_local_order():
    result = _model(
        "class C:\n"
        "    from pkg import child\n"
        "    x = [1, 2]\n"
    )
    assert result.outcome == "MODEL_PASS"
    operations = [
        event.operation for event in result.events
    ]
    import_index = next(
        index for index, operation in enumerate(operations)
        if operation.startswith("CLASS_LOCAL_FROM")
    )
    bind_index = operations.index("CLASS_LOCAL_BIND")
    class_index = operations.index("DEFINE_PASSIVE_CLASS")
    assert import_index < bind_index < class_index


def test_class_binding_does_not_export_module_name():
    result = _model(
        "class C:\n"
        "    value = [1, 2]\n"
        "from pkg.child import value\n"
    )
    assert result.outcome != "MODEL_PASS"


def test_literal_annassign_in_deferred_mode():
    result = _model(
        "x: Later = [1, {'a': 2}]",
        mode="DEFERRED",
    )
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "BIND"
        and event.symbol == "x"
        for event in result.events
    )


def test_class_literal_annassign():
    result = _model(
        "class C:\n"
        "    x: Later = [1, 2]\n",
        mode="DEFERRED",
    )
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "CLASS_LOCAL_BIND"
        and event.symbol == "x"
        for event in result.events
    )


def test_eager_annassign_stays_unknown():
    assert _model(
        "x: side_effect() = [1, 2]",
        mode="STOCK_EAGER",
    ).outcome == "UNKNOWN"


def test_early_binding_hazard_not_hidden():
    result = _model(
        "from pkg import value",
        initializer=(
            "import pkg.child\n"
            "value = [1, 2]\n"
        ),
        entry="pkg",
    )
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "value"


def test_safe_binding_before_import():
    result = _model(
        "from pkg import value",
        initializer=(
            "value = [1, 2]\n"
            "import pkg.child\n"
        ),
        entry="pkg",
    )
    assert result.outcome == "MODEL_PASS"


def test_star_import_remains_unknown():
    assert _model(
        "from pkg import *",
        initializer="__all__ = ['child']",
    ).outcome == "UNKNOWN"


def test_namespace_remains_unknown():
    result = evaluate_package_import_order(
        {
            "pkg.child": ast.parse(
                "x = [1, 2]"
            )
        },
        "pkg.child",
    )
    assert result.outcome == "UNKNOWN"


def test_external_import_remains_unknown():
    assert _model(
        "import nonexistent_external_xyz\n"
        "x = [1, 2]"
    ).outcome == "UNKNOWN"


def test_determinism_and_ast_immutability():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.child": ast.parse(
            "x = [1, {'a': (2, 3)}]"
        ),
    }
    before = {
        key: ast.dump(tree)
        for key, tree in sources.items()
    }
    first = evaluate_package_import_order(
        sources, "pkg.child",
    )
    second = evaluate_package_import_order(
        sources, "pkg.child",
    )
    assert first == second
    assert before == {
        key: ast.dump(tree)
        for key, tree in sources.items()
    }


def test_compile_accepts_all_literal_assignment():
    tree = ast.parse(
        "__all__ = ['alpha', 'beta']"
    )
    assert _compile(tree, "pkg.child", False) is not None


@pytest.mark.parametrize(
    "source",
    [
        "x = 16 * 1024",
        "x = 1 + 2 * 3",
        "x = (5 + 3) * (9 - 2)",
        "x = -4 * 3 + 2",
        "x = 3 * (1 - 2)",
        "x = [1 + 2, 4 * 8]",
        "x = {'size': 4 * 8}",
        "x = {1 + 2: 'value'}",
        "x = 0 * 100",
        "x = 9223372036854775808 - 1",
    ],
)
def test_g18_p1_bounded_integer_arithmetic_pass(source):
    result = _model(source)
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "BIND"
        for event in result.events
    )


@pytest.mark.parametrize(
    "source",
    [
        "x = True + 1",
        "x = 1 + True",
        "x = 1.0 + 2",
        "x = 'a' + 'b'",
        "x = 1 + missing",
        "x = 1 + side_effect()",
        "x = 1 / 0",
        "x = 2 ** 8",
        "x = 1 << 2",
        "x = 2 // 1",
        "x = 1 & 2",
        "x = 1 * [1]",
        "x = 18446744073709551615 + 1",
        "x = 9223372036854775808 * 2",
    ],
)
def test_g18_p1_unsupported_arithmetic_unknown(source):
    assert _model(source).outcome == "UNKNOWN"


def test_g18_p1_arithmetic_class_local_binding():
    result = _model(
        "class C:\n"
        "    x = 16 * 1024\n"
    )
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "CLASS_LOCAL_BIND"
        and event.symbol == "x"
        for event in result.events
    )


def test_g18_p1_arithmetic_deferred_annassign():
    result = _model(
        "x: Later = 16 * 1024",
        mode="DEFERRED",
    )
    assert result.outcome == "MODEL_PASS"


def test_g18_p1_version_literal_binding():
    result = _model(
        "__version__ = '1.0.4'"
    )
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "BIND"
        and event.symbol == "__version__"
        for event in result.events
    )


@pytest.mark.parametrize(
    "source",
    [
        "__version__ = 1",
        "__version__ = build_version()",
        "__version__ = '1' + '.0'",
        "__version__ = other",
        "__path__ = ['other']",
        "__getattr__ = something",
        "__annotations__ = {}",
        "class C:\n    __version__ = '1.0'",
    ],
)
def test_g18_p1_reserved_binding_restrictions(source):
    assert _model(source).outcome == "UNKNOWN"


def test_g18_p1_version_binding_preserves_order():
    result = _model(
        "__version__ = '1.0.4'\n"
        "from pkg import value\n",
        initializer="value = 7",
    )
    assert result.outcome == "MODEL_PASS"

    operations = [
        event.operation
        for event in result.events
        if event.module == "pkg.child"
    ]
    assert operations.index("BIND") < operations.index("FROM")


def test_g18_p1_arithmetic_early_binding_hazard():
    result = _model(
        "from pkg import late",
        initializer=(
            "import pkg.child\n"
            "late = 16 * 1024\n"
        ),
        entry="pkg",
    )
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "late"


def test_g18_p1_arithmetic_binding_before_import():
    result = _model(
        "from pkg import late",
        initializer=(
            "late = 16 * 1024\n"
            "import pkg.child\n"
        ),
        entry="pkg",
    )
    assert result.outcome == "MODEL_PASS"


def test_g18_p1_external_import_still_unknown():
    assert _model(
        "x = 16 * 1024\n"
        "import missing_external_xyz"
    ).outcome == "UNKNOWN"


def test_g18_p1_namespace_layout_still_unknown():
    result = evaluate_package_import_order(
        {
            "pkg.child": ast.parse(
                "x = 16 * 1024"
            )
        },
        "pkg.child",
    )
    assert result.outcome == "UNKNOWN"


def test_g18_p1_arithmetic_ast_immutability():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.child": ast.parse(
            "x = (5 + 3) * (9 - 2)"
        ),
    }

    before = {
        key: ast.dump(tree)
        for key, tree in sources.items()
    }

    first = evaluate_package_import_order(
        sources, "pkg.child"
    )
    second = evaluate_package_import_order(
        sources, "pkg.child"
    )

    assert first == second
    assert first.outcome == "MODEL_PASS"
    assert before == {
        key: ast.dump(tree)
        for key, tree in sources.items()
    }
