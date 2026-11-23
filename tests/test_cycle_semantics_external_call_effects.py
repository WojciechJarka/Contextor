import ast

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


FIELD_EFFECT = "PASSIVE_DEFAULTLESS_DATACLASS_FIELD"
PROPERTY_EFFECT = "PASSIVE_PROPERTY"
FACTORY_EFFECT = (
    "FROZEN_DATACLASS_DECORATOR_FACTORY"
)


def _run(source, effects=None):
    declared_effects = {
        ("dataclasses", "dataclass"): FACTORY_EFFECT,
    }

    if effects is not None:
        declared_effects.update(effects)

    return evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(source),
            "pkg.child": ast.parse(
                "from pkg import C\n"
            ),
        },
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
        _assumed_external_callable_effects=(
            declared_effects
        ),
    )


def _source(import_line, default="field()"):
    return (
        import_line
        + "@dataclass(frozen=True)\n"
        + "class C:\n"
        + "    x: int = "
        + default
        + "\n"
    )


def test_import_success_is_not_call_effect_proof():
    result = _run(
        _source(
            "from dataclasses import dataclass, field\n"
        )
    )

    assert result.outcome == "UNKNOWN"
    assert tuple(
        row.effect
        for row in result.assumed_external_call_effects
    ) == (FACTORY_EFFECT,)
    assert not any(
        event.operation
        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
        for event in result.events
    )


def test_declared_effect_preserves_field():
    result = _run(
        _source(
            "from dataclasses import dataclass, field\n",
            "field(hash=False, compare=False)",
        ),
        {("dataclasses", "field"): FIELD_EFFECT},
    )

    assert result.outcome == "MODEL_PASS"
    field_rows = tuple(
        row
        for row in result.assumed_external_call_effects
        if row.effect == FIELD_EFFECT
    )
    assert len(field_rows) == 1
    row = field_rows[0]
    assert (
        row.import_module,
        row.imported_symbol,
        row.effect,
    ) == (
        "dataclasses",
        "field",
        FIELD_EFFECT,
    )
    assert (
        "EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
        in result.evidence_scope
    )


def test_declared_effect_is_independent_of_import_name():
    result = _run(
        _source(
            "from dataclasses import dataclass\n"
            "from some_external_module import factory as field\n"
        ),
        {
            ("some_external_module", "factory"):
                FIELD_EFFECT,
        },
    )

    assert result.outcome == "MODEL_PASS"
    assert any(
        row.import_module == "some_external_module"
        and row.effect == FIELD_EFFECT
        for row in result.assumed_external_call_effects
    )


def test_rebinding_invalidates_callable_fact():
    result = _run(
        _source(
            "from dataclasses import dataclass, field\n"
            "field = None\n"
        ),
        {("dataclasses", "field"): FIELD_EFFECT},
    )

    assert result.outcome == "UNKNOWN"
    assert tuple(
        row.effect
        for row in result.assumed_external_call_effects
    ) == (FACTORY_EFFECT,)


def test_wrong_effect_does_not_authorize_call():
    result = _run(
        _source(
            "from dataclasses import dataclass, field\n"
        ),
        {("dataclasses", "field"): PROPERTY_EFFECT},
    )

    assert result.outcome == "UNKNOWN"


def test_invalid_effect_contract_is_unknown():
    result = _run(
        _source(
            "from dataclasses import dataclass, field\n"
        ),
        {("dataclasses", "field"): "UNKNOWN_EFFECT"},
    )

    assert result.outcome == "UNKNOWN"
    assert result.assumed_external_call_effects == ()


def test_imported_property_needs_own_effect_proof():
    source = (
        "from dataclasses import dataclass\n"
        "from builtins import property as prop\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
        "    @prop\n"
        "    def value(self):\n"
        "        return 1\n"
    )

    without = _run(source)
    with_contract = _run(
        source,
        {("builtins", "property"): PROPERTY_EFFECT},
    )

    assert without.outcome == "UNKNOWN"
    assert with_contract.outcome == "MODEL_PASS"
    assert any(
        row.effect == PROPERTY_EFFECT
        for row in with_contract.assumed_external_call_effects
    )


def test_conventional_builtin_property_remains():
    result = _run(
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
        "    @property\n"
        "    def value(self):\n"
        "        return 1\n"
    )

    assert result.outcome == "MODEL_PASS"
    assert tuple(
        row.effect
        for row in result.assumed_external_call_effects
    ) == (FACTORY_EFFECT,)


def test_field_contract_includes_result_and_lifecycle():
    result = _run(
        _source(
            "from dataclasses import dataclass, field\n",
            "field(hash=False, compare=False)",
        ),
        {("dataclasses", "field"): FIELD_EFFECT},
    )

    assert result.outcome == "MODEL_PASS"
    field_rows = tuple(
        row
        for row in result.assumed_external_call_effects
        if row.effect == FIELD_EFFECT
    )
    assert len(field_rows) == 1
    row = field_rows[0]

    assert row.invocation_semantics == (
        "NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS"
    )
    assert row.result_semantics == (
        "EXACT_STDLIB_FIELD_NO_DEFAULT_OR_FACTORY_"
        "PRESERVE_LITERAL_HASH_COMPARE"
    )
    assert row.result_lifecycle_semantics == (
        "NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING"
    )


def test_property_contract_includes_result_and_lifecycle():
    source = (
        "from dataclasses import dataclass\n"
        "from builtins import property as prop\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
        "    @prop\n"
        "    def value(self):\n"
        "        return 7\n"
    )

    result = _run(
        source,
        {("builtins", "property"): PROPERTY_EFFECT},
    )

    assert result.outcome == "MODEL_PASS"
    property_rows = tuple(
        row
        for row in result.assumed_external_call_effects
        if row.effect == PROPERTY_EFFECT
    )
    assert len(property_rows) == 1
    row = property_rows[0]

    assert row.invocation_semantics == (
        "NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS"
    )
    assert row.result_semantics == (
        "EXACT_BUILTINS_PROPERTY_OF_DECORATED_FUNCTION"
    )
    assert row.result_lifecycle_semantics == (
        "NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING"
    )


def test_frozen_class_decorator_outcome_is_explicit():
    source = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
        "@dataclass(frozen=True)\n"
        "class D:\n"
        "    y: C | None\n"
        "import pkg.child\n"
    )

    result = evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(source),
            "pkg.child": ast.parse(
                "from pkg import D\n"
            ),
        },
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
        _assumed_external_callable_effects={
            ("dataclasses", "dataclass"): FACTORY_EFFECT,
        },
    )

    assert result.outcome == "MODEL_PASS"
    assert tuple(
        row.class_name
        for row in result.assumed_dataclass_decorations
    ) == ("C", "D")

    for row in result.assumed_dataclass_decorations:
        assert row.factory_invocation_semantics == (
            "NO_UNMODELED_FACTORY_EFFECTS_OR_EXCEPTIONS"
        )
        assert row.factory_result_semantics == (
            "EXACT_STANDARD_FROZEN_DATACLASS_DECORATOR"
        )
        assert row.application_invocation_semantics == (
            "NO_UNMODELED_DECORATION_EFFECTS_OR_EXCEPTIONS"
        )
        assert row.application_result_semantics == (
            "EXACT_STANDARD_FROZEN_DATACLASS_TRANSFORMATION"
        )
        assert row.application_lifecycle_semantics == (
            "NO_UNKNOWN_EFFECTS_BEFORE_CLASS_BINDING"
        )
        assert row.returned_class_identity == "INPUT_CLASS"

    assert result.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
        "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
    )


def test_rebound_class_decorator_has_no_outcome_fact():
    result = _run(
        "from dataclasses import dataclass\n"
        "dataclass = None\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
    )

    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "C"
        for event in result.events
    )


def test_factory_name_is_not_authority():
    source = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
    )

    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)},
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )

    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert result.assumed_external_call_effects == ()


def test_factory_semantics_independent_of_import_name():
    source = (
        "from external_provider import make as decorate\n"
        "@decorate(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
    )

    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)},
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
        _assumed_external_callable_effects={
            ("external_provider", "make"):
                FACTORY_EFFECT,
        },
    )

    assert result.outcome == "MODEL_PASS"
    assert len(result.assumed_dataclass_decorations) == 1
    assert (
        result.assumed_dataclass_decorations[0].decorator
        == "external_provider.make(frozen=True)"
    )
    assert (
        result.assumed_external_call_effects[0].effect
        == FACTORY_EFFECT
    )


def test_factory_alias_preserves_declared_semantics():
    source = (
        "from external_provider import make\n"
        "alias = make\n"
        "@alias(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
    )

    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)},
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
        _assumed_external_callable_effects={
            ("external_provider", "make"):
                FACTORY_EFFECT,
        },
    )

    assert result.outcome == "MODEL_PASS"
    assert (
        result.assumed_dataclass_decorations[0].decorator
        == "external_provider.make(frozen=True)"
    )


def test_factory_rebinding_removes_declared_semantics():
    source = (
        "from external_provider import make\n"
        "make = None\n"
        "@make(frozen=True)\n"
        "class C:\n"
        "    x: int\n"
    )

    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)},
        "pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
        _assumed_external_callable_effects={
            ("external_provider", "make"):
                FACTORY_EFFECT,
        },
    )

    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert result.assumed_external_call_effects == ()
