import ast
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics import extract_import_provenance
from contextor.core.cycle_semantics.execution_context import (
    project_execution_context,
)
from contextor.core.cycle_semantics.provenance import (
    ImportProvenance,
    ImportOccurrence,
    ScopeFrame,
)


def project(code):
    facts = extract_import_provenance(
        ast.parse(code),
        module_id="pkg.a",
        source_key="pkg/a.py",
        source_path="C:/fixture/pkg/a.py",
        source_fingerprint="fingerprint",
    )
    return project_execution_context(facts)


def test_module_and_class_import_candidates_not_certified_safe():
    p = project("import a\nclass K:\n    import b\n")
    assert [c.phase for c in p.contexts] == [
        "MODULE_OR_CLASS_CANDIDATE", "MODULE_OR_CLASS_CANDIDATE"
    ]
    assert p.contexts[1].activation_requirements == ("EXECUTE_CLASS_DEFINITION",)
    assert all(c.initialization_reachability == "UNKNOWN" for c in p.contexts)


def test_function_and_method_are_call_dependent_not_safe():
    p = project("def f():\n    import a\nclass K:\n    def g(self):\n        import b\n")
    assert [c.phase for c in p.contexts] == ["CALL_DEPENDENT"] * 2
    assert p.contexts[1].activation_requirements == (
        "EXECUTE_CLASS_DEFINITION", "CALL_FUNCTION_BODY"
    )


def test_nested_class_inside_function_requires_parent_call():
    p = project("def f():\n    class K:\n        import x\n")
    assert p.contexts[0].phase == "CALL_DEPENDENT"
    assert p.contexts[0].activation_requirements == (
        "CALL_FUNCTION_BODY", "EXECUTE_CLASS_DEFINITION"
    )


def test_async_body_requires_resume():
    p = project("async def f():\n    import a\n")
    assert p.contexts[0].activation_requirements == ("RESUME_COROUTINE_BODY",)
    assert p.contexts[0].phase == "CALL_DEPENDENT"


def test_controls_not_evaluated():
    p = project(
        "if False:\n    import a\n"
        "try:\n    import b\n"
        "except ImportError:\n    import c\n"
    )
    assert [c.control_kinds for c in p.contexts] == [
        ("IF",), ("TRY",), ("EXCEPT",)
    ]
    assert all(c.guard_evaluation == "UNEVALUATED" for c in p.contexts)
    assert all(c.initialization_reachability == "UNKNOWN" for c in p.contexts)


def test_control_in_function_preserves_both_dimensions():
    p = project("def f():\n    if ready:\n        import a\n")
    c = p.contexts[0]
    assert c.phase == "CALL_DEPENDENT"
    assert c.control_kinds == ("IF",)
    assert c.initialization_reachability == "UNKNOWN"


def test_no_imports_stable():
    p = project("x = 1\n")
    assert p.contexts == ()
    assert p.source_fingerprint == "fingerprint"


def test_repeated_occurrences_preserved_in_source_order():
    p = project("import a\nimport a\n")
    assert tuple(c.ordinal for c in p.contexts) == (0, 1)
    assert p.contexts[0].line != p.contexts[1].line


def test_projection_is_deterministic_and_json_compatible():
    p = project("class A:\n    import x\n")
    assert p == project("class A:\n    import x\n")
    import json
    json.dumps(asdict(p))


def test_unknown_scope_fail_closed():
    occurrence = ImportOccurrence(
        ordinal=0, line=1, column=0, end_line=1, end_column=8,
        form="IMPORT", module=None, level=0, aliases=(("a", None),),
        scopes=(ScopeFrame("FUTURE_SCOPE", "f", 1),), controls=()
    )
    facts = ImportProvenance("p", "p.py", "C:/p.py", "sha", (occurrence,))
    c = project_execution_context(facts).contexts[0]
    assert c.phase == "UNKNOWN"
    assert c.activation_requirements == ("UNKNOWN_SCOPE_ACTIVATION",)


def test_duplicate_ordinal_fails_closed():
    occurrence = ImportOccurrence(
        ordinal=0, line=1, column=0, end_line=1, end_column=8,
        form="IMPORT", module=None, level=0, aliases=(("a", None),),
        scopes=(), controls=()
    )
    facts = ImportProvenance("p", "p.py", "C:/p.py", "sha", (occurrence, occurrence))
    with pytest.raises(ValueError, match="duplicate"):
        project_execution_context(facts)


def test_wrong_input_type_rejected():
    with pytest.raises(TypeError):
        project_execution_context(None)
