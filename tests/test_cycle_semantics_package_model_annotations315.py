"""Explicit annotation semantics in the restricted package execution model."""

import ast

import pytest

from contextor.core.cycle_semantics.package_model import (
    _compile,
    evaluate_package_import_order,
)


def _sources(body: str, initializer: str = "pass"):
    return {
        "pkg.__init__": ast.parse(initializer),
        "pkg.child": ast.parse(body),
    }


def _assess(body: str, *, mode="DEFERRED", initializer="pass"):
    return evaluate_package_import_order(
        _sources(body, initializer), "pkg.child",
        annotation_semantics=mode,
    )


@pytest.mark.parametrize("body", [
    "def f(x: int) -> str:\n    pass",
    "def f(x: Later):\n    pass",
    "def f() -> Later:\n    pass",
    "def f(x: side_effect()) -> side_effect():\n    pass",
    "def f(x: Later = 1):\n    pass",
])
def test_deferred_function_annotations_and_literal_defaults(body):
    result = _assess(body)
    assert result.outcome == "MODEL_PASS"
    assert any(event.operation.startswith("DEFINE_") for event in result.events)
    assert not any(event.operation == "CALL_FUNCTION" for event in result.events)


def test_module_annassign_without_value_does_not_bind():
    result = _assess("x: Later")
    assert result.outcome == "MODEL_PASS"
    assert not any(event.operation == "BIND" for event in result.events)


def test_module_annassign_value_binds_in_statement_order():
    result = _assess("x: Later = 1\nfrom pkg import child")
    assert result.outcome == "MODEL_PASS"
    assert [(event.operation, event.symbol) for event in result.events
            if event.operation == "BIND"] == [("BIND", "x")]


def test_class_annotations_have_separate_binding_and_import_order():
    result = _assess(
        "class C:\n"
        "    x: Later\n"
        "    from pkg import child\n"
        "    y: Later = 1\n"
        "    def method(self, value: Later) -> Later:\n"
        "        pass\n"
    )
    assert result.outcome == "MODEL_PASS"
    operations = [event.operation for event in result.events]
    assert any(op.startswith("CLASS_LOCAL_FROM") for op in operations)
    assert "CLASS_LOCAL_BIND" in operations
    assert next(i for i, op in enumerate(operations)
                if op.startswith("CLASS_LOCAL_FROM")) < operations.index("CLASS_LOCAL_BIND")
    assert operations.index("CLASS_LOCAL_BIND") < operations.index("DEFINE_PASSIVE_CLASS")
    assert not any(event.operation == "BIND" and event.symbol == "y"
                   for event in result.events)


def test_future_annotation_directive_is_not_silently_elided():
    source = "from __future__ import annotations\ndef f(x: Later):\n    pass"
    assert _compile(ast.parse(source), "pkg.child", False,
                    annotation_semantics="STRINGIFIED") is not None
    assert _assess(source, mode=None).outcome == "UNKNOWN"


def test_deterministic_and_ast_unchanged():
    sources = _sources("x: Later = 1\ndef f(y: Later):\n    pass")
    before = {name: ast.dump(tree) for name, tree in sources.items()}
    one = evaluate_package_import_order(sources, "pkg.child",
                                        annotation_semantics="DEFERRED")
    two = evaluate_package_import_order(sources, "pkg.child",
                                        annotation_semantics="DEFERRED")
    assert one == two
    assert before == {name: ast.dump(tree) for name, tree in sources.items()}


@pytest.mark.parametrize("body", [
    "@side_effect()\ndef f(x: Later):\n    pass",
    "def f(x: Later = side_effect()):\n    pass",
    "class C(side_effect()):\n    pass",
    "@side_effect()\nclass C:\n    pass",
    "class C(metaclass=side_effect()):\n    pass",
    "class C:\n    side_effect()",
    "x: Later = side_effect()",
    "obj.x: Later = 1",
    "(x): Later = 1",
    "print(f.__annotations__)",
    "import missing_external",
])
def test_unknown_effects_remain_unknown(body):
    assert _assess(body).outcome == "UNKNOWN"


def test_eager_and_unknown_version_reject_annotated_function():
    body = "def f(x: side_effect()):\n    pass"
    assert _assess(body, mode="STOCK_EAGER").outcome == "UNKNOWN"
    assert _assess(body, mode=None).outcome == "UNKNOWN"


def test_eager_and_unknown_version_reject_annassign():
    for mode in ("STOCK_EAGER", None):
        assert _assess("x: side_effect() = 1", mode=mode).outcome == "UNKNOWN"


def test_stringified_mode_requires_future_directive_in_each_source():
    assert _assess("def f(x: Later):\n    pass", mode="STRINGIFIED").outcome == "UNKNOWN"


@pytest.mark.parametrize("body", [
    "x = 1\nfrom __future__ import annotations",
])
def test_invalid_future_directive_fails_closed(body):
    assert _assess(body).outcome == "UNKNOWN"


def test_unknown_future_feature_fails_during_ast_parse():
    with pytest.raises(SyntaxError):
        ast.parse("from __future__ import nonexistent_feature")
    malformed = ast.Module(
        body=[ast.ImportFrom(
            module="__future__", names=[ast.alias(name="nonexistent_feature")],
            level=0,
        )],
        type_ignores=[],
    )
    ast.fix_missing_locations(malformed)
    sources = _sources("pass")
    sources["pkg.child"] = malformed
    assert evaluate_package_import_order(
        sources, "pkg.child", annotation_semantics="DEFERRED",
    ).outcome == "UNKNOWN"


def test_namespace_layout_still_unknown():
    sources = {"pkg.child": ast.parse("x: Later = 1")}
    assert evaluate_package_import_order(
        sources, "pkg.child", annotation_semantics="DEFERRED",
    ).outcome == "UNKNOWN"


def test_early_binding_hazard_survives_annotations():
    sources = _sources(
        "from pkg import late\n"
        "def f(x: Later):\n    pass",
        initializer="from pkg.child import f\nlate = 1",
    )
    result = evaluate_package_import_order(
        sources, "pkg.child", annotation_semantics="DEFERRED",
    )
    assert result.outcome == "EARLY_BINDING_HAZARD"


def test_restricted_class_annotation_does_not_leak_module_binding():
    result = _assess("class C:\n    value: Later = 1\nfrom pkg.child import value")
    assert result.outcome != "MODEL_PASS"
