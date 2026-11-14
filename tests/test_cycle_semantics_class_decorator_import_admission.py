"""Indexed class decorator admission and unchanged semantic boundaries."""

import ast

import pytest

from contextor.core.cycle_semantics.package_model import (
    _compile,
    evaluate_package_import_order,
)


def _compile_app(source):
    return _compile(ast.parse(source), "pkg.app", False)


def _model(sources, entry="pkg.app", **options):
    return evaluate_package_import_order(
        {name: ast.parse(source) for name, source in sources.items()},
        entry,
        **options,
    )


def _calls(result):
    return tuple(
        (event.module, event.symbol)
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    )


def test_a_matching_earlier_indexed_from_is_admitted():
    app = (
        "from pkg.decorators import decorate\n"
        "@decorate\nclass Product:\n    pass\n"
    )
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def decorate(cls):\n    return cls\n",
        "pkg.app": app,
    })

    assert _compile_app(app) is not None
    assert result.outcome == "MODEL_PASS"
    assert tuple(
        (event.module, event.target, event.symbol)
        for event in result.events
        if event.operation == "FROM"
    ) == (("pkg.app", "pkg.decorators", "decorate"),)
    assert _calls(result) == (("pkg.app", "decorate"),)


def test_b_imported_alias_uses_its_exact_binding_name():
    app = (
        "from pkg.decorators import decorate as alias\n"
        "@alias\nclass Product:\n    pass\n"
    )
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def decorate(cls):\n    return cls\n",
        "pkg.app": app,
    })

    assert _compile_app(app) is not None
    assert result.outcome == "MODEL_PASS"
    assert tuple(
        (event.target, event.symbol)
        for event in result.events
        if event.operation == "FROM"
    ) == (("pkg.decorators", "decorate"),)
    assert _calls(result) == (("pkg.app", "alias"),)


def test_c_from_after_class_does_not_admit_decorator():
    app = (
        "@decorate\nclass Product:\n    pass\n"
        "from pkg.decorators import decorate\n"
    )

    assert _compile_app(app) is None


def test_d_unrelated_earlier_from_does_not_admit_decorator():
    app = (
        "from pkg.other import token\n"
        "@decorate\nclass Product:\n    pass\n"
    )

    assert _compile_app(app) is None


def test_e_prior_binding_is_not_callable_proof():
    app = "decorate = None\n@decorate\nclass Product:\n    pass\n"

    assert _compile_app(app) is None


def test_f_prior_import_alone_does_not_admit_decorator():
    app = "import pkg.decorators\n@decorate\nclass Product:\n    pass\n"

    assert _compile_app(app) is None


def test_g_every_name_in_decorator_stack_needs_earlier_binding():
    app = (
        "from pkg.decorators import lower\n"
        "@upper\n@lower\nclass Product:\n    pass\n"
    )

    assert _compile_app(app) is None


def test_h_external_callable_is_not_executed():
    app = (
        "from dataclasses import dataclass\n"
        "@dataclass\nclass Product:\n    pass\n"
    )
    result = _model({"pkg.__init__": "pass\n", "pkg.app": app})

    assert _compile_app(app) is not None
    assert result.outcome == "UNKNOWN"
    assert result.target_module == "dataclasses"
    assert not _calls(result)


def test_i_none_class_decorator_result_does_not_admit_class_call():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def replace(cls):\n    return\n",
        "pkg.app": (
            "from pkg.decorators import replace\n"
            "@replace\nclass Product:\n    pass\n"
            "Product()\n"
        ),
    })

    assert result.outcome == "UNKNOWN"
    assert _calls(result) == (("pkg.app", "replace"),)
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "Product"
        for event in result.events
    )


def test_j_indexed_identity_class_fact_remains_a_supported_subclass_base():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def identity(cls):\n    return cls\n",
        "pkg.app": (
            "from pkg.decorators import identity\n"
            "@identity\nclass Product:\n    pass\n"
            "class Child(Product):\n    pass\n"
        ),
    })

    assert result.outcome == "MODEL_PASS"
    assert _calls(result) == (("pkg.app", "identity"),)
    assert tuple(
        event.symbol for event in result.events
        if event.operation == "DEFINE_PASSIVE_CLASS"
    ) == ("Product", "Child")


def test_k_same_module_class_decorator_event_contract_is_unchanged():
    result = _model({
        "pkg.__init__": (
            "def identity(cls):\n    return cls\n"
            "@identity\nclass Product:\n    pass\n"
        ),
    }, entry="pkg")

    assert result.outcome == "MODEL_PASS"
    assert tuple(
        (event.module, event.operation, event.target, event.symbol)
        for event in result.events
    ) == (
        ("\x00ENTRY", "START_IMPORT", "pkg", None),
        ("pkg", "DEFINE_FUNCTION", None, "identity"),
        ("pkg", "DEFINE_PASSIVE_CLASS", None, "Product"),
        ("pkg", "CALL_FUNCTION", None, "identity"),
        ("pkg", "READY", None, None),
    )


def test_l_imported_decorated_function_contract_is_unchanged():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def identity(fn):\n    return fn\n",
        "pkg.app": (
            "from pkg.decorators import identity\n"
            "@identity\ndef work():\n    pass\n"
        ),
    })

    assert result.outcome == "MODEL_PASS"
    assert _calls(result) == (("pkg.app", "identity"),)
    assert any(
        event.operation == "DEFINE_FUNCTION"
        and event.symbol == "work"
        for event in result.events
    )


def test_m_indexed_function_decorator_stack_contract_is_unchanged():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.lower": "def lower(fn):\n    return fn\n",
        "pkg.upper": "def upper(fn):\n    return fn\n",
        "pkg.app": (
            "from pkg.lower import lower\n"
            "from pkg.upper import upper\n"
            "@upper\n@lower\ndef work():\n    pass\n"
        ),
    })

    assert result.outcome == "MODEL_PASS"
    assert _calls(result) == (
        ("pkg.app", "lower"),
        ("pkg.app", "upper"),
    )


def test_n_conditional_frozen_dataclass_path_is_unchanged():
    result = _model(
        {
            "pkg.__init__": (
                "from dataclasses import dataclass\n"
                "@dataclass(frozen=True)\n"
                "class Record:\n    value: int\n"
            ),
        },
        entry="pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )

    assert result.outcome == "MODEL_PASS"
    assert result.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )
    assert len(result.assumed_dataclass_decorations) == 1
    assert result.assumed_dataclass_decorations[0].class_name == "Record"
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "dataclass"
        for event in result.events
    )


@pytest.mark.parametrize(
    "class_statement",
    (
        "@identity\nclass Product(MissingBase):\n    pass\n",
        "@identity\nclass Product(metaclass=MissingMeta):\n    pass\n",
    ),
    ids=("unsupported-base", "unsupported-metaclass"),
)
def test_o_unsupported_base_or_metaclass_stays_unknown(class_statement):
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def identity(cls):\n    return cls\n",
        "pkg.app": "from pkg.decorators import identity\n" + class_statement,
    })

    assert result.outcome == "UNKNOWN"
    assert not _calls(result)


def test_p_unsupported_imported_decorator_body_has_no_fabricated_calls():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": (
            "def helper(cls):\n    return cls\n"
            "def decorate(cls):\n    return helper(cls)\n"
        ),
        "pkg.app": (
            "from pkg.decorators import decorate\n"
            "@decorate\nclass Product:\n    pass\n"
        ),
    })

    assert result.outcome == "UNKNOWN"
    assert result.target_module == "pkg.app"
    assert result.symbol == "decorate"
    assert not _calls(result)
    assert not any(
        event.operation in {"FUNCTION_LOCAL_IMPORT", "FUNCTION_LOCAL_FROM"}
        for event in result.events
    )
