import ast

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


def _model(
    child: str,
    *,
    initializer: str = "pass",
    entry: str = "pkg.child",
    annotation_semantics=None,
):
    return evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(initializer),
            "pkg.child": ast.parse(child),
        },
        entry,
        annotation_semantics=annotation_semantics,
    )


def _operations(result):
    return [event.operation for event in result.events]


def test_plain_async_definition_passes():
    result = _model(
        "async def worker():\n"
        "    pass\n"
    )
    assert result.outcome == "MODEL_PASS"
    assert "DEFINE_OPAQUE_FUNCTION" in _operations(result)


def test_async_body_is_not_executed():
    result = _model(
        "async def worker():\n"
        "    import missing_external_xyz\n"
    )
    assert result.outcome == "MODEL_PASS"
    assert "DEFINE_OPAQUE_FUNCTION" in _operations(result)
    assert not any(
        event.target == "missing_external_xyz"
        for event in result.events
    )


def test_annotated_async_definition_deferred():
    result = _model(
        "async def worker(x: Missing) -> Missing:\n"
        "    pass\n",
        annotation_semantics="DEFERRED",
    )
    assert result.outcome == "MODEL_PASS"


def test_annotated_async_unknown_version():
    result = _model(
        "async def worker(x: Missing):\n"
        "    pass\n"
    )
    assert result.outcome == "UNKNOWN"


def test_annotated_async_eager():
    result = _model(
        "async def worker(x: side_effect()):\n"
        "    pass\n",
        annotation_semantics="STOCK_EAGER",
    )
    assert result.outcome == "UNKNOWN"


@pytest.mark.parametrize(
    "source",
    [
        "@decorator\nasync def worker():\n    pass",
        "async def worker(x=side_effect()):\n    pass",
        "@side_effect()\nasync def worker():\n    pass",
    ],
)
def test_async_eager_definition_effects_unknown(source):
    assert _model(source).outcome == "UNKNOWN"


def test_async_invocation_unknown():
    result = _model(
        "async def worker():\n"
        "    pass\n"
        "worker()\n"
    )
    assert result.outcome == "UNKNOWN"


def test_passive_async_class_method():
    result = _model(
        "class C:\n"
        "    async def method(self):\n"
        "        import missing_external_xyz\n"
    )
    assert result.outcome == "MODEL_PASS"
    assert "DEFINE_PASSIVE_CLASS" in _operations(result)


def test_decorated_async_class_method_unknown():
    result = _model(
        "class C:\n"
        "    @staticmethod\n"
        "    async def method():\n"
        "        pass\n"
    )
    assert result.outcome == "UNKNOWN"


def test_simple_module_alias():
    result = _model(
        "original = [1, 2]\n"
        "copied = original\n"
    )
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "ALIAS"
        and event.target == "original"
        and event.symbol == "copied"
        for event in result.events
    )


def test_chained_alias():
    result = _model(
        "a = 1\n"
        "b = a\n"
        "c = b\n"
    )
    assert result.outcome == "MODEL_PASS"
    assert _operations(result).count("ALIAS") == 2


def test_bound_self_alias():
    result = _model(
        "a = 1\n"
        "a = a\n"
    )
    assert result.outcome == "MODEL_PASS"


def test_unbound_self_alias_unknown():
    assert _model("a = a").outcome == "UNKNOWN"


def test_unbound_source_unknown():
    assert _model("copied = missing").outcome == "UNKNOWN"


def test_builtin_not_assumed_bound():
    assert _model("copied = len").outcome == "UNKNOWN"


def test_special_source_not_assumed():
    assert _model("copied = __name__").outcome == "UNKNOWN"


def test_alias_from_imported_name():
    result = _model(
        "from pkg import value\n"
        "copied = value\n",
        initializer="value = 7",
    )
    assert result.outcome == "MODEL_PASS"
    assert "FROM" in _operations(result)
    assert "ALIAS" in _operations(result)


def test_alias_export_from_child():
    result = _model(
        "original = 7\n"
        "copied = original\n",
        initializer="from pkg.child import copied",
        entry="pkg",
    )
    assert result.outcome == "MODEL_PASS"


def test_alias_before_binding_unknown():
    result = _model(
        "copied = original\n"
        "original = 1\n"
    )
    assert result.outcome == "UNKNOWN"


def test_alias_preserves_early_binding_hazard():
    result = _model(
        "from pkg import late\n"
        "copied = late\n",
        initializer=(
            "import pkg.child\n"
            "late = 1\n"
        ),
        entry="pkg",
    )
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "late"


def test_package_child_alias_shadowing_unknown():
    result = _model(
        "pass",
        initializer=(
            "value = 1\n"
            "child = value\n"
            "import pkg.child\n"
        ),
        entry="pkg",
    )
    assert result.outcome == "UNKNOWN"


def test_alias_of_function_is_bound():
    result = _model(
        "def f():\n"
        "    pass\n"
        "other = f\n"
    )
    assert result.outcome == "MODEL_PASS"
    assert "ALIAS" in _operations(result)


def test_aliased_restricted_function_call_executes():
    result = _model(
        "def f():\n"
        "    pass\n"
        "other = f\n"
        "other()\n"
    )
    assert result.outcome == "MODEL_PASS"
    assert sum(
        event.operation == "CALL_FUNCTION"
        and event.symbol == "other"
        for event in result.events
    ) == 1


def test_class_body_name_alias_still_unknown():
    result = _model(
        "x = 1\n"
        "class C:\n"
        "    copied = x\n"
    )
    assert result.outcome == "UNKNOWN"


def test_external_import_still_unknown():
    result = _model(
        "import missing_external_xyz\n"
        "copy = missing_external_xyz\n"
    )
    assert result.outcome == "UNKNOWN"


def test_namespace_layout_still_unknown():
    result = evaluate_package_import_order(
        {
            "pkg.child": ast.parse(
                "value = 1\n"
                "copy = value\n"
            )
        },
        "pkg.child",
    )
    assert result.outcome == "UNKNOWN"


def test_determinism_and_ast_immutability():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.child": ast.parse(
            "async def worker():\n"
            "    pass\n"
            "value = [1, 2]\n"
            "copied = value\n"
        ),
    }

    before = {
        name: ast.dump(tree)
        for name, tree in sources.items()
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
        name: ast.dump(tree)
        for name, tree in sources.items()
    }
