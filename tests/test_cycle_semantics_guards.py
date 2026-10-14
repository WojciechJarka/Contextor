import ast
import json
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.provenance import extract_import_provenance
from contextor.core.cycle_semantics.guards import project_import_guards


def project(code):
    tree = ast.parse(code)
    p = extract_import_provenance(
        tree, module_id="p.a", source_key="p/a.py",
        source_path="C:/fixture/p/a.py", source_fingerprint="fingerprint",
    )
    return project_import_guards(tree, p)


def test_literal_false_body_and_else():
    result = project("if False:\n    import a\nelse:\n    import b\n")
    assert [a.gate for a in result.assessments] == [
        "BLOCKED_BY_LITERAL", "NO_KNOWN_GUARD_BLOCKER"]
    assert [f.branch_gate for a in result.assessments for f in a.frames] == [
        "BLOCKED", "POSSIBLE"
    ]


def test_literal_true_else_blocked():
    result = project("if True:\n    import a\nelse:\n    import b\n")
    assert [a.gate for a in result.assessments] == [
        "NO_KNOWN_GUARD_BLOCKER", "BLOCKED_BY_LITERAL"]


def test_nested_condition_false_overrides_dynamic_unknown():
    result = project("if condition:\n    if False:\n        import a\n")
    assert result.assessments[0].gate == "BLOCKED_BY_LITERAL"
    assert [f.branch_gate for f in result.assessments[0].frames] == [
        "UNKNOWN", "BLOCKED"
    ]


def test_boolean_literals_not_and():
    result = project(
        "if not False and True:\n    import a\n"
        "if True and False:\n    import b\n"
    )
    assert [a.gate for a in result.assessments] == [
        "NO_KNOWN_GUARD_BLOCKER", "BLOCKED_BY_LITERAL"]


def test_dynamic_predicate_stays_unknown():
    result = project("if arbitrary_function():\n    import a\n")
    assert result.assessments[0].gate == "GUARDED_UNKNOWN"
    assert result.assessments[0].frames[0].predicate_kind == "UNKNOWN_EXPRESSION"


def test_type_checking_direct_alias_candidate_not_proof():
    result = project(
        "from typing import TYPE_CHECKING as TC\n"
        "if TC:\n    import a\n"
    )
    assert result.assessments[1].frames[0].predicate_kind == (
        "TYPE_CHECKING_CANDIDATE"
    )
    assert result.assessments[1].gate == "GUARDED_UNKNOWN"


def test_typing_module_alias_candidate():
    result = project("import typing as t\nif t.TYPE_CHECKING:\n    import a\n")
    assert result.assessments[1].frames[0].predicate_kind == (
        "TYPE_CHECKING_CANDIDATE"
    )
    assert result.assessments[1].gate == "GUARDED_UNKNOWN"


def test_unbound_and_shadowed_typechecking_unresolved():
    p = project("if TC:\n    import a\n")
    assert p.assessments[0].frames[0].predicate_kind == "UNKNOWN_EXPRESSION"
    p = project(
        "from typing import TYPE_CHECKING as TC\n"
        "TC = True\nif TC:\n    import a\n"
    )
    assert p.assessments[1].frames[0].predicate_kind == "UNKNOWN_EXPRESSION"


def test_future_alias_import_does_not_count():
    p = project(
        "if TC:\n    import a\n"
        "from typing import TYPE_CHECKING as TC\n"
    )
    assert p.assessments[0].frames[0].predicate_kind == "UNKNOWN_EXPRESSION"


def test_main_guard_candidate_is_not_runtime_proof():
    p = project('if __name__ == "__main__":\n    import a\n')
    assert p.assessments[0].frames[0].predicate_kind == "MAIN_GUARD_CANDIDATE"
    assert p.assessments[0].gate == "GUARDED_UNKNOWN"


def test_try_and_for_controls_unknown():
    p = project(
        "try:\n    import a\n"
        "except ImportError:\n    import b\n"
        "for x in seq:\n    import c\n"
    )
    assert [a.gate for a in p.assessments] == ["GUARDED_UNKNOWN"] * 3
    assert all(
        a.frames[0].predicate_kind == "NON_IF_CONTROL"
        for a in p.assessments
    )


def test_absence_of_guard_is_not_reachability_proof():
    p = project("def later():\n    import a\n")
    a = p.assessments[0]
    assert a.gate == "NO_KNOWN_GUARD_BLOCKER"
    assert a.initialization_reachability == "UNKNOWN"


def test_nested_if_in_function_preserves_lexical_blocker():
    p = project("def later():\n    if False:\n        import a\n")
    assert p.assessments[0].gate == "BLOCKED_BY_LITERAL"
    assert p.assessments[0].initialization_reachability == "UNKNOWN"


def test_ast_mismatch_rejected():
    tree = ast.parse("import a")
    p = extract_import_provenance(
        tree, module_id="m", source_key="m.py", source_path="C:/m.py",
        source_fingerprint="fingerprint"
    )
    with pytest.raises(ValueError, match="differ"):
        project_import_guards(ast.parse("import b"), p)


def test_invalid_inputs_rejected():
    tree = ast.parse("import a")
    p = extract_import_provenance(
        tree, module_id="m", source_key="m.py", source_path="C:/m.py",
        source_fingerprint="fingerprint"
    )
    with pytest.raises(TypeError):
        project_import_guards(None, p)
    with pytest.raises(TypeError):
        project_import_guards(tree, None)


def test_deterministic_json_compatible_and_nonmutating():
    code = "if False:\n    import a\n"
    tree = ast.parse(code)
    p = extract_import_provenance(
        tree, module_id="m", source_key="m.py", source_path="C:/m.py",
        source_fingerprint="fingerprint"
    )
    before = ast.dump(tree, include_attributes=True)
    first = project_import_guards(tree, p)
    assert first == project_import_guards(tree, p)
    json.dumps(asdict(first))
    assert ast.dump(tree, include_attributes=True) == before
