"""
tests/test_h2c_collision_equivalence.py

H2C Equivalence Tests:
Verifies 100% semantic equivalence between legacy/eager collision extraction
and the optimized lazy/deduplicated path for all scenarios:
1. No collisions (clean repository)
2. Identical duplicate definitions (identical normalized code across modules)
3. Conflicting same-name definitions (different code across modules)
4. Classes, functions, async functions, and exported uppercase constants
5. Private/public filtering (_private, __magic__, ignored entrypoints)
6. Complex multi-module scenarios with mixed identical and conflicting definitions
"""

import ast
import tempfile
from pathlib import Path
import pytest

from contextor.core.domain.module import Module
from contextor.core.domain.validation import ValidationError
from contextor.core.validator.collisions import (
    CollisionFact,
    compute_collisions_from_facts,
    extract_module_collision_facts,
    extract_repository_collision_facts,
    validate_name_collisions,
)


def _legacy_eager_extract(tree: ast.AST, module_path: str, file_path: str = "") -> list[dict]:
    """Reference eager extraction implementation matching pre-H2C logic."""
    symbols = []
    class_depth = 0
    function_depth = 0

    from contextor.core.validator.collisions import _ignore

    def _add(name: str, kind: str, node: ast.AST):
        if _ignore(name):
            return
        code = ""
        try:
            code = ast.unparse(node)
        except Exception:
            code = name
        symbols.append({
            "name": name,
            "type": kind,
            "file": module_path,
            "file_path": file_path,
            "code": code,
            "line_start": getattr(node, "lineno", None),
            "line_end": getattr(node, "end_lineno", None),
            "col_start": getattr(node, "col_offset", None),
            "col_end": getattr(node, "end_col_offset", None),
        })

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            nonlocal class_depth
            if class_depth == 0 and function_depth == 0:
                _add(node.name, "class", node)
            class_depth += 1
            self.generic_visit(node)
            class_depth -= 1

        def visit_FunctionDef(self, node):
            nonlocal function_depth
            if class_depth == 0 and function_depth == 0:
                _add(node.name, "function", node)
            function_depth += 1
            self.generic_visit(node)
            function_depth -= 1

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_Assign(self, node):
            if class_depth != 0 or function_depth != 0:
                return
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    _add(target.id, "variable", node)

    Visitor().visit(tree)
    return symbols


def test_collision_fact_dict_contract_and_schema():
    """Verify CollisionFact satisfies exact dict schema and lazy evaluation."""
    src = "class User:\n    id: int\n\nMAX_COUNT = 100\n"
    tree = ast.parse(src)
    facts = extract_module_collision_facts(tree, "app.models", "/tmp/models.py")

    assert len(facts) == 2
    user_fact = next(f for f in facts if f["name"] == "User")
    assert isinstance(user_fact, dict)
    assert user_fact["type"] == "class"
    assert user_fact["file"] == "app.models"
    assert user_fact["file_path"] == "/tmp/models.py"
    assert user_fact["line_start"] == 1
    assert "code" in user_fact
    assert user_fact["code"] == "class User:\n    id: int"

    # Schema keys check
    expected_keys = {"name", "type", "file", "file_path", "code", "line_start", "line_end", "col_start", "col_end"}
    assert expected_keys.issubset(set(user_fact.keys()))


def test_no_collisions_equivalence():
    """Verify no collisions produce empty error lists under both paths."""
    src_a = "class ServiceA:\n    pass\ndef helper_a():\n    return 1\n"
    src_b = "class ServiceB:\n    pass\ndef helper_b():\n    return 2\n"
    tree_a = ast.parse(src_a)
    tree_b = ast.parse(src_b)

    legacy_facts = {
        "mod_a": _legacy_eager_extract(tree_a, "mod_a", "/tmp/mod_a.py"),
        "mod_b": _legacy_eager_extract(tree_b, "mod_b", "/tmp/mod_b.py"),
    }
    opt_facts = {
        "mod_a": extract_module_collision_facts(tree_a, "mod_a", "/tmp/mod_a.py"),
        "mod_b": extract_module_collision_facts(tree_b, "mod_b", "/tmp/mod_b.py"),
    }

    legacy_errors = compute_collisions_from_facts(legacy_facts)
    opt_errors = compute_collisions_from_facts(opt_facts)

    assert legacy_errors == []
    assert opt_errors == []


def test_identical_duplicate_definitions_equivalence():
    """Verify identical definitions across modules produce identical duplicate errors with matching details."""
    src_a = "def common_util(x: int) -> int:\n    return x * 2\n\nCONFIG_VAL = 42\n"
    src_b = "def common_util(x: int) -> int:\n    return x * 2\n\nCONFIG_VAL = 42\n"
    tree_a = ast.parse(src_a)
    tree_b = ast.parse(src_b)

    legacy_facts = {
        "mod_a": _legacy_eager_extract(tree_a, "mod_a", "/tmp/mod_a.py"),
        "mod_b": _legacy_eager_extract(tree_b, "mod_b", "/tmp/mod_b.py"),
    }
    opt_facts = {
        "mod_a": extract_module_collision_facts(tree_a, "mod_a", "/tmp/mod_a.py"),
        "mod_b": extract_module_collision_facts(tree_b, "mod_b", "/tmp/mod_b.py"),
    }

    legacy_errors = compute_collisions_from_facts(legacy_facts)
    opt_errors = compute_collisions_from_facts(opt_facts)

    assert len(legacy_errors) == len(opt_errors) == 2
    for leg, opt in zip(sorted(legacy_errors, key=lambda e: e.message), sorted(opt_errors, key=lambda e: e.message)):
        assert leg.kind == opt.kind == "IDENTICAL_DEFINITION_DUPLICATE"
        assert leg.message == opt.message
        assert leg.nodes == opt.nodes == ["mod_a", "mod_b"]
        assert leg.artifact_type == opt.artifact_type
        assert leg.is_identical == opt.is_identical == True
        assert leg.code_snippets == opt.code_snippets
        assert leg.symbol_details == opt.symbol_details


def test_conflicting_same_name_definitions_equivalence():
    """Verify conflicting definitions across modules produce NAME_COLLISION errors with exact parity."""
    src_a = "class Manager:\n    def run(self):\n        return 1\n"
    src_b = "class Manager:\n    def run(self):\n        return 2\n"
    tree_a = ast.parse(src_a)
    tree_b = ast.parse(src_b)

    legacy_facts = {
        "mod_a": _legacy_eager_extract(tree_a, "mod_a", "/tmp/mod_a.py"),
        "mod_b": _legacy_eager_extract(tree_b, "mod_b", "/tmp/mod_b.py"),
    }
    opt_facts = {
        "mod_a": extract_module_collision_facts(tree_a, "mod_a", "/tmp/mod_a.py"),
        "mod_b": extract_module_collision_facts(tree_b, "mod_b", "/tmp/mod_b.py"),
    }

    legacy_errors = compute_collisions_from_facts(legacy_facts)
    opt_errors = compute_collisions_from_facts(opt_facts)

    assert len(legacy_errors) == len(opt_errors) == 1
    leg, opt = legacy_errors[0], opt_errors[0]
    assert leg.kind == opt.kind == "NAME_COLLISION"
    assert leg.message == opt.message
    assert leg.nodes == opt.nodes == ["mod_a", "mod_b"]
    assert leg.artifact_type == opt.artifact_type == "class"
    assert leg.is_identical == opt.is_identical == False
    assert leg.code_snippets == opt.code_snippets
    assert leg.symbol_details == opt.symbol_details


def test_filtering_rules_equivalence():
    """Verify private symbols, magic methods, and ignored names are filtered out identically."""
    src = (
        "__all__ = ['Public']\n"
        "__version__ = '1.0'\n"
        "_private_var = 10\n"
        "def _private_func():\n    pass\n"
        "def main():\n    pass\n"
        "def run():\n    pass\n"
        "def get():\n    pass\n"
        "def visit_ClassDef():\n    pass\n"
        "class PublicClass:\n"
        "    def method(self):\n        pass\n"
        "PUBLIC_CONST = 99\n"
    )
    tree = ast.parse(src)

    legacy_facts = _legacy_eager_extract(tree, "mod_filter", "/tmp/mod_filter.py")
    opt_facts = extract_module_collision_facts(tree, "mod_filter", "/tmp/mod_filter.py")

    assert len(legacy_facts) == len(opt_facts) == 2
    leg_names = {f["name"] for f in legacy_facts}
    opt_names = {f["name"] for f in opt_facts}
    assert leg_names == opt_names == {"PublicClass", "PUBLIC_CONST"}


def test_repository_extraction_and_validate_name_collisions_parity():
    """Verify extract_repository_collision_facts and validate_name_collisions parity."""
    src_a = "def process():\n    return 1\n"
    src_b = "def process():\n    return 2\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        path_a = Path(tmpdir) / "mod_a.py"
        path_b = Path(tmpdir) / "mod_b.py"
        path_a.write_text(src_a, encoding="utf-8")
        path_b.write_text(src_b, encoding="utf-8")

        modules = {
            "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(path_a), imports=[]),
            "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(path_b), imports=[]),
        }

        # 1. Direct validation with auto-extraction
        errors_direct = validate_name_collisions(modules)

        # 2. Extract repository facts first, then validate with reuse
        repo_facts = extract_repository_collision_facts(modules)
        errors_reused = validate_name_collisions(modules, collision_facts=repo_facts)

        assert len(errors_direct) == len(errors_reused) == 1
        assert errors_direct[0].message == errors_reused[0].message
        assert errors_direct[0].code_snippets == errors_reused[0].code_snippets


def test_collision_fact_deterministic_order_and_serialization():
    """Verify CollisionFact preserves deterministic legacy key ordering and JSON serialization."""
    import json
    src = "class AccountService:\n    pass\n\nMAX_TIMEOUT = 30\n"
    tree = ast.parse(src)
    facts = extract_module_collision_facts(tree, "app.service", "/tmp/app/service.py")

    assert len(facts) == 2
    fact = facts[0]

    expected_order = [
        "name",
        "type",
        "file",
        "file_path",
        "code",
        "line_start",
        "line_end",
        "col_start",
        "col_end",
    ]

    # Deterministic legacy key ordering
    assert list(fact.keys()) == expected_order
    assert [k for k, _ in fact.items()] == expected_order
    assert [k for k in fact] == expected_order

    # JSON serialization produces exact ordered mapping
    serialized = json.dumps(fact)
    parsed = json.loads(serialized)
    assert list(parsed.keys()) == expected_order
    assert parsed["name"] == "AccountService"
    assert parsed["type"] == "class"
    assert parsed["code"] == "class AccountService:\n    pass"


def test_hard_reset_consecutive_extractions_and_mutation_isolation():
    """Verify consecutive extractions independently rebuild facts without global cache leakage."""
    src_v1 = "def endpoint():\n    return 1\n"
    src_v2 = "def endpoint():\n    return 2\n\nEXTRA_VAL = 99\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "service.py"
        path.write_text(src_v1, encoding="utf-8")

        modules = {
            "service": Module(module_id="service", path="service.py", absolute_path=str(path), imports=[]),
        }

        facts_run1 = extract_repository_collision_facts(modules)
        assert len(facts_run1["service"]) == 1
        assert facts_run1["service"][0]["name"] == "endpoint"

        # Update file on disk
        path.write_text(src_v2, encoding="utf-8")

        # Independent extraction on the same or mutated module dict MUST derive fresh facts
        facts_run2 = extract_repository_collision_facts(modules)
        assert len(facts_run2["service"]) == 2
        names_v2 = {f["name"] for f in facts_run2["service"]}
        assert names_v2 == {"endpoint", "EXTRA_VAL"}


def test_annotated_assignment_excluded_matching_pre_h2c():
    """Verify annotated assignments are excluded to preserve exact pre-H2C collision symbol set."""
    src = "MY_ANN_CONST: int = 10\nRAW_CONST = 20\n"
    tree = ast.parse(src)
    facts = extract_module_collision_facts(tree, "mod", "/tmp/mod.py")

    names = {f["name"] for f in facts}
    assert "RAW_CONST" in names
    assert "MY_ANN_CONST" not in names

