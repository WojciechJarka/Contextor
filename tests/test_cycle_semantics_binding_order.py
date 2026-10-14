import ast
import json
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.provenance import (
    extract_import_provenance,
)
from contextor.core.cycle_semantics.binding_order import (
    extract_cycle_module_binding_order,
)


def _binding_order_for(code):
    tree = ast.parse(code)
    facts = extract_import_provenance(
        tree,
        module_id="pkg.a",
        source_key="pkg/a.py",
        source_path="C:/fixture/pkg/a.py",
        source_fingerprint="fingerprint",
    )
    return extract_cycle_module_binding_order(tree, facts)


def test_binding_order_switch_same_import_graph():
    before = _binding_order_for(
        "value = 1\nimport b\n"
    )
    after = _binding_order_for(
        "import b\nvalue = 1\n"
    )

    assert (
        before.statements[0].binding_candidates[0].name
        == "value"
    )
    assert (
        before.statements[1].contained_import_ordinals
        == (0,)
    )

    assert (
        after.statements[0].contained_import_ordinals
        == (0,)
    )
    assert (
        after.statements[1].binding_candidates[0].name
        == "value"
    )

    assert before.initialization_reachability == "UNKNOWN"
    assert after.initialization_reachability == "UNKNOWN"


def test_same_line_separate_import_statements():
    result = _binding_order_for(
        "import a; import b\n"
    )

    assert [
        item.contained_import_ordinals
        for item in result.statements
    ] == [(0,), (1,)]


def test_function_and_class_imports_are_contained():
    result = _binding_order_for(
        "def f():\n"
        "    import a\n"
        "class K:\n"
        "    import b\n"
    )

    assert [
        item.contained_import_ordinals
        for item in result.statements
    ] == [(0,), (1,)]

    assert [
        item.binding_candidates[0].completion_point
        for item in result.statements
    ] == [
        "AFTER_FUNCTION_DEFINITION",
        "AFTER_CLASS_DEFINITION",
    ]


def test_conditional_imports_share_top_level_owner():
    result = _binding_order_for(
        "if flag:\n"
        "    import a\n"
        "else:\n"
        "    import b\n"
    )

    assert (
        result.statements[0].contained_import_ordinals
        == (0, 1)
    )
    assert result.statements[0].binding_candidates == ()


def test_import_alias_binding_candidates():
    result = _binding_order_for(
        "import os.path, sys as ss\n"
        "from . import child as c\n"
    )

    assert [
        candidate.name
        for candidate in result.statements[0].binding_candidates
    ] == ["os", "ss"]

    assert (
        result.statements[1].binding_candidates[0].name
        == "c"
    )


def test_delete_and_augmented_assignment():
    result = _binding_order_for(
        "x = 1\n"
        "x += 1\n"
        "del x\n"
    )

    assert [
        statement.binding_candidates[0].operation
        for statement in result.statements
    ] == ["BIND", "BIND", "DELETE"]


def test_annotation_without_value_not_binding_candidate():
    result = _binding_order_for(
        "x: int\n"
        "y: int = 1\n"
        "a, b = (1, 2)\n"
    )

    assert result.statements[0].binding_candidates == ()
    assert (
        result.statements[1].binding_candidates[0].name
        == "y"
    )
    assert result.statements[2].binding_candidates == ()


def test_star_import_not_guessed():
    result = _binding_order_for(
        "from pkg import *\n"
    )

    assert result.statements[0].binding_candidates == ()
    assert (
        result.statements[0].contained_import_ordinals
        == (0,)
    )


def test_no_imports_remains_valid():
    result = _binding_order_for("x = 1\n")

    assert result.statements[0].contained_import_ordinals == ()
    assert result.initialization_reachability == "UNKNOWN"


def test_ast_provenance_mismatch_rejected():
    tree = ast.parse("import a\n")
    facts = extract_import_provenance(
        tree,
        module_id="m",
        source_key="m.py",
        source_path="C:/m.py",
        source_fingerprint="fingerprint",
    )

    with pytest.raises(ValueError, match="differ"):
        extract_cycle_module_binding_order(
            ast.parse("import b\n"),
            facts,
        )


def test_wrong_input_types_rejected():
    tree = ast.parse("import a\n")
    facts = extract_import_provenance(
        tree,
        module_id="m",
        source_key="m.py",
        source_path="C:/m.py",
        source_fingerprint="fingerprint",
    )

    with pytest.raises(TypeError):
        extract_cycle_module_binding_order(None, facts)

    with pytest.raises(TypeError):
        extract_cycle_module_binding_order(tree, None)


def test_deterministic_json_compatible():
    first = _binding_order_for(
        "if True:\n    import a\n"
    )
    second = _binding_order_for(
        "if True:\n    import a\n"
    )

    assert first == second
    json.dumps(asdict(first))

    assert all(
        statement.execution_proven == "UNKNOWN"
        for statement in first.statements
    )
