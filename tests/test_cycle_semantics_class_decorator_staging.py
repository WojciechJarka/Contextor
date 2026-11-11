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
    steps = _steps("@top\n@bottom\nclass C:\n    pass\n")
    assert steps is not None
    assert steps[0].op == "SNAPSHOT_CLASS_DECORATORS"
    assert steps[0].decorator_names == ("top", "bottom")


def test_same_name_decorator_stages_but_remains_unknown():
    source = "def C(cls):\n    return cls\n@C\nclass C:\n    pass\n"
    steps = _steps(source)
    assert steps is not None
    assert steps[1].op == "SNAPSHOT_CLASS_DECORATORS"
    assert steps[1].decorator_names == ("C",)
    result = evaluate_package_import_order(
        {"pkg.__init__": ast.parse(source)}, "pkg",
    )
    assert result.outcome == "UNKNOWN"


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
