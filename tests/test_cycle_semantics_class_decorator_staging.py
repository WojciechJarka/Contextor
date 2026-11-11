"""Compilation staging for named class decorators; execution remains unknown."""

import ast

from contextor.core.cycle_semantics.execution.calls import (
    _snapshot_named_decorators,
)
from contextor.core.cycle_semantics.execution.class_facts import (
    _BUILTIN_CLASS_FACTS,
)
from contextor.core.cycle_semantics.package_model import (
    _compile,
    evaluate_package_import_order,
)


def _steps(source, **options):
    return _compile(ast.parse(source), "pkg", True, **options)


def test_single_named_class_decorator_staging():
    steps = _steps(
        "def identity(cls):\n    return cls\n"
        "@identity\nclass C:\n    pass\n"
    )
    assert steps is not None
    class_steps = steps[1:]
    assert tuple(step.op for step in class_steps) == (
        "SNAPSHOT_CLASS_DECORATORS",
        "PREPARE_PASSIVE_CLASS",
        "DEFINE_DECORATED_PASSIVE_CLASS",
    )
    assert class_steps[0].decorator_names == ("identity",)
    assert len({step.definition_id for step in class_steps}) == 1
    assert class_steps[0].definition_id is not None


def test_decorated_class_body_import_staging():
    steps = _steps(
        "def identity(cls):\n    return cls\n"
        "@identity\nclass C:\n    import pkg.body\n"
    )
    assert steps is not None
    class_steps = steps[1:]
    assert tuple(step.op for step in class_steps) == (
        "SNAPSHOT_CLASS_DECORATORS",
        "PREPARE_PASSIVE_CLASS",
        "IMPORT",
        "DEFINE_DECORATED_PASSIVE_CLASS",
    )
    assert class_steps[2].target == "pkg.body"
    assert class_steps[2].class_local is True
    assert class_steps[0].definition_id == class_steps[-1].definition_id


def test_multiple_named_class_decorators_keep_source_order():
    steps = _steps(
        "def top(cls):\n"
        "    return cls\n"
        "def bottom(cls):\n"
        "    return cls\n"
        "@top\n"
        "@bottom\n"
        "class C:\n"
        "    pass\n"
    )
    assert steps is not None
    snapshot = next(
        step for step in steps
        if step.op == "SNAPSHOT_CLASS_DECORATORS"
    )
    assert snapshot.decorator_names == ("top", "bottom")


def test_same_name_decorator_stages_and_executes():
    source = "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n"
    steps = _steps(source)
    assert steps is not None
    assert steps[1].op == "SNAPSHOT_CLASS_DECORATORS"
    assert steps[1].decorator_names == ("C",)
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)}, "pkg",
    )
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "CALL_FUNCTION"
        and event.symbol == "C"
        for event in result.events
    )


def test_attribute_class_decorator_stays_unknown():
    source = "@factory.decorate\nclass C:\n    pass\n"
    assert _steps(source) is None
    assert evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)}, "pkg",
    ).outcome == "UNKNOWN"


def test_call_class_decorator_stays_unknown():
    source = "@factory()\nclass C:\n    pass\n"
    assert _steps(source) is None
    assert evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)}, "pkg",
    ).outcome == "UNKNOWN"


def test_qualified_conditional_frozen_dataclass_unchanged():
    # Same qualified fixture and options as test_frozen_dataclass_direct_conditional_record.
    source = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\nclass Graph:\n    value: int\n"
    )
    steps = _steps(
        source,
        annotation_semantics="DEFERRED",
        assume_frozen_dataclass=True,
    )
    assert steps is not None
    assert any(
        step.op == "DEFINE_CONDITIONAL_FROZEN_DATACLASS"
        for step in steps
    )
    assert not any(
        step.op == "SNAPSHOT_CLASS_DECORATORS" for step in steps
    )
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)},
        "pkg",
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
    assert result.assumed_dataclass_decorations[0].class_name == "Graph"


def test_ordinary_undecorated_class_unchanged():
    steps = _steps("class C:\n    pass\n")
    assert steps is not None
    assert tuple(step.op for step in steps) == (
        "PREPARE_PASSIVE_CLASS",
        "DEFINE_PASSIVE_CLASS",
    )


def test_snapshot_preserves_class_fact_reference_without_execution():
    class_fact = _BUILTIN_CLASS_FACTS["object"]
    namespace = {"decorator": class_fact}
    before = namespace.copy()
    snapshot = _snapshot_named_decorators(
        ("decorator",), namespace,
    )
    assert snapshot is not None
    assert snapshot.values[0] is class_fact
    assert namespace == before


def test_unresolved_decorator_rejects_whole_module_compile():
    assert _steps(
        "value = 1\n@unknown_decorator\nclass Bad:\n    pass\n"
    ) is None


def test_preceding_local_restricted_decorator_stages_in_order():
    steps = _steps(
        "def identity(cls):\n    return cls\n"
        "@identity\nclass C:\n    pass\n"
    )
    assert steps is not None
    assert tuple(step.op for step in steps) == (
        "DEFINE_FUNCTION",
        "SNAPSHOT_CLASS_DECORATORS",
        "PREPARE_PASSIVE_CLASS",
        "DEFINE_DECORATED_PASSIVE_CLASS",
    )
    assert steps[0].binding == "identity"


def test_unbound_decorator_in_stack_rejects_compile():
    assert _steps(
        "def known(cls):\n    return cls\n"
        "@unknown\n@known\nclass C:\n    pass\n"
    ) is None


def test_forward_decorator_reference_rejects_compile():
    assert _steps(
        "@later\nclass C:\n    pass\n"
        "def later(cls):\n    return cls\n"
    ) is None


def test_same_name_local_decorator_proof_gate():
    source = "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n"
    steps = _steps(source)
    assert steps is not None
    snapshot = next(
        step for step in steps
        if step.op == "SNAPSHOT_CLASS_DECORATORS"
    )
    assert snapshot.decorator_names == ("C",)
    assert evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)}, "pkg",
    ).outcome == "UNKNOWN"


def test_exact_p10_eager_and_lazy_fixture():
    source = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse(
            "def later():\n"
            "    import pkg.bad\n"
            "value = 1\n"
        ),
        "pkg.bad": ast.parse(
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }
    eager = evaluate_package_import_order(
        source, "pkg.a", annotation_semantics="DEFERRED",
    )
    lazy = evaluate_package_import_order(
        source, "pkg.a", annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
    )
    assert eager.outcome == "UNKNOWN"
    assert eager.target_module == "pkg.bad"
    assert eager.events == ()
    assert lazy.outcome == "MODEL_PASS"
    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.bad"
        for event in lazy.events
    )


def test_exact_p11_strict_and_opt_in_fixture():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse(
            "value = 1\n"
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }
    strict = evaluate_package_import_order(
        sources, "pkg.a", annotation_semantics="DEFERRED",
    )
    opt_in = evaluate_package_import_order(
        sources, "pkg.a", annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
    )
    assert strict.outcome == "UNKNOWN"
    assert strict.target_module == "pkg.a"
    assert strict.events == ()
    assert opt_in.outcome == "UNKNOWN"
    assert opt_in.target_module == "pkg.a"
    assert any(
        event.operation == "BIND"
        and event.module == "pkg.a"
        and event.symbol == "value"
        for event in opt_in.events
    )
