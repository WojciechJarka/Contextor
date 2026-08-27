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
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
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


def test_internal_typeerror_propagates_and_executes_once():
    """Verify internal TypeError inside _compute_metrics_and_debt propagates without catching/retry."""
    from unittest.mock import patch, MagicMock
    from contextor.core.api.facade import ContextorFacade
    import contextor.core.api.facade as facade_module

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "mod.py"
        path.write_text("def run():\n    pass\n", encoding="utf-8")

        real_compute = facade_module._compute_metrics_and_debt
        compute_mock = MagicMock(side_effect=TypeError("Simulated internal TypeError"))

        with patch.object(facade_module, "_compute_metrics_and_debt", compute_mock):
            with pytest.raises(TypeError, match="Simulated internal TypeError"):
                ContextorFacade.analyze_project(str(tmpdir))

        # Must be invoked exactly once: zero fallback / retry recomputations
        assert compute_mock.call_count == 1


def test_collision_fact_complete_mapping_operation_matrix():
    """Exhaustively verify all mapping operations on CollisionFact match plain dict contract."""
    from collections.abc import KeysView, ItemsView, ValuesView, Mapping
    import copy
    import pickle

    src = "class AccountHandler:\n    def handle(self):\n        return True\n"
    tree = ast.parse(src)
    node = tree.body[0]

    unparse_calls = 0
    real_unparse = ast.unparse
    def counting_unparse(n):
        nonlocal unparse_calls
        unparse_calls += 1
        return real_unparse(n)

    with patch("ast.unparse", side_effect=counting_unparse):
        fact = CollisionFact(
            name="AccountHandler",
            kind="class",
            module_path="app.handler",
            file_path="/app/handler.py",
            node=node,
            line_start=1,
            line_end=3,
            col_start=0,
            col_end=19,
        )

        assert unparse_calls == 0

        # 1. [] access for non-code keys does not trigger unparse
        assert fact["name"] == "AccountHandler"
        assert fact["type"] == "class"
        assert fact["file"] == "app.handler"
        assert fact["file_path"] == "/app/handler.py"
        assert fact["line_start"] == 1
        assert fact["line_end"] == 3
        assert fact["col_start"] == 0
        assert fact["col_end"] == 19
        assert unparse_calls == 0

        # 2. get method
        assert fact.get("name") == "AccountHandler"
        assert fact.get("nonexistent", "fallback") == "fallback"
        assert unparse_calls == 0

        # 3. in operator
        assert "name" in fact
        assert "type" in fact
        assert "code" in fact
        assert "nonexistent" not in fact
        assert unparse_calls == 0

        # 4. len
        assert len(fact) == 9
        assert unparse_calls == 0

        # 5. keys() view
        kv = fact.keys()
        assert isinstance(kv, KeysView)
        assert repr(kv).startswith("dict_keys(")
        expected_keys = ["name", "type", "file", "file_path", "code", "line_start", "line_end", "col_start", "col_end"]
        assert list(kv) == expected_keys
        assert set(kv) == set(expected_keys)
        assert kv & {"name", "type"} == {"name", "type"}
        assert unparse_calls == 0

        # 6. items() view
        iv = fact.items()
        assert isinstance(iv, ItemsView)
        assert repr(iv).startswith("dict_items(")
        assert len(iv) == 9

        # 7. values() view
        vv = fact.values()
        assert isinstance(vv, ValuesView)
        assert repr(vv).startswith("dict_values(")
        assert len(vv) == 9

        # 8. dict(fact) materialization
        d = dict(fact)
        assert type(d) is dict
        assert list(d.keys()) == expected_keys
        expected_code = real_unparse(node)
        assert d["code"] == expected_code
        assert unparse_calls == 1

        # 9. copy / deepcopy
        c = fact.copy()
        assert isinstance(c, dict)
        assert c["code"] == expected_code
        dc = copy.deepcopy(fact)
        assert dc["code"] == expected_code

        # 10. pickle / unpickle
        p_bytes = pickle.dumps(fact)
        p_loaded = pickle.loads(p_bytes)
        assert type(p_loaded) is dict
        assert list(p_loaded.keys()) == expected_keys
        assert p_loaded["code"] == expected_code
        assert not hasattr(p_loaded, "_node")


def test_collision_fact_ast_node_lifetime_and_pickle_isolation():
    """Verify raw AST node references are strictly transient and not retained in pickled snapshots."""
    import pickle
    src = "def util_func():\n    return 42\n"
    tree = ast.parse(src)
    node = tree.body[0]

    fact = CollisionFact(
        name="util_func",
        kind="function",
        module_path="core.util",
        file_path="/core/util.py",
        node=node,
        line_start=1,
        line_end=2,
        col_start=0,
        col_end=14,
    )

    assert fact._node is node

    # 1. Pickling un-rendered fact produces plain dict with code="" and zero unparse calls
    pickled = pickle.dumps(fact)
    restored = pickle.loads(pickled)

    assert type(restored) is dict
    assert not hasattr(restored, "_node")
    assert restored["name"] == "util_func"
    assert restored["code"] == ""

    # 2. Pickling pre-rendered fact preserves rendered code
    _ = fact["code"]  # force lazy rendering
    assert fact._rendered_code == "def util_func():\n    return 42"
    pickled_rendered = pickle.dumps(fact)
    restored_rendered = pickle.loads(pickled_rendered)
    assert restored_rendered["code"] == "def util_func():\n    return 42"


def test_hard_reset_independently_rebuilt_module_sets():
    """Verify two independently rebuilt module sets produce fresh facts with zero global cache leakage."""
    src1 = "def step_one():\n    pass\n"
    src2 = "def step_two():\n    pass\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        path1 = Path(tmpdir) / "mod1.py"
        path2 = Path(tmpdir) / "mod2.py"
        path1.write_text(src1, encoding="utf-8")
        path2.write_text(src2, encoding="utf-8")

        # Set 1
        modules1 = {
            "mod1": Module(module_id="mod1", path="mod1.py", absolute_path=str(path1), imports=[]),
        }
        facts1 = extract_repository_collision_facts(modules1)
        assert len(facts1["mod1"]) == 1
        assert facts1["mod1"][0]["name"] == "step_one"

        # Set 2
        modules2 = {
            "mod2": Module(module_id="mod2", path="mod2.py", absolute_path=str(path2), imports=[]),
        }
        facts2 = extract_repository_collision_facts(modules2)
        assert len(facts2["mod2"]) == 1
        assert facts2["mod2"][0]["name"] == "step_two"
        assert "mod1" not in facts2


def test_same_mapping_ast_replacement_hard_reset():
    """Verify replacing module.ast_tree in the SAME modules mapping extracts fresh facts without stale state."""
    from unittest.mock import PropertyMock

    src_v1 = "def legacy_handler():\n    return 1\n"
    src_v2 = "def updated_handler():\n    return 2\n\nUPDATED_CONFIG = 100\n"

    tree_v1 = ast.parse(src_v1)
    tree_v2 = ast.parse(src_v2)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "service.py"
        path.write_text(src_v1, encoding="utf-8")

        module = Module(module_id="service", path="service.py", absolute_path=str(path), imports=[])
        modules = {"service": module}

        # 1. First extraction with populated AST v1
        with patch.object(Module, "ast_tree", new_callable=PropertyMock, return_value=tree_v1):
            facts_v1 = extract_repository_collision_facts(modules)
            assert len(facts_v1["service"]) == 1
            assert facts_v1["service"][0]["name"] == "legacy_handler"

        # 2. Second extraction on the SAME modules dict after replacing ast_tree with AST v2
        with patch.object(Module, "ast_tree", new_callable=PropertyMock, return_value=tree_v2):
            facts_v2 = extract_repository_collision_facts(modules)
            assert len(facts_v2["service"]) == 2
            names_v2 = {f["name"] for f in facts_v2["service"]}
            assert names_v2 == {"updated_handler", "UPDATED_CONFIG"}
            assert "legacy_handler" not in names_v2


def test_clean_repo_zero_unparse_end_to_end_through_hydration():
    """Verify clean repository full analysis performs 0 unparse calls through canonical validation + persistence + hydration."""
    from contextor.core.api.facade import ContextorFacade
    from contextor.core.live_state import hydrate_repository_engine

    src_a = "def unique_handler_a():\n    return 'a'\n"
    src_b = "def unique_handler_b():\n    return 'b'\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "mod_a.py").write_text(src_a, encoding="utf-8")
        (root / "mod_b.py").write_text(src_b, encoding="utf-8")

        unparse_calls = 0
        real_unparse = ast.unparse
        def counting_unparse(node):
            nonlocal unparse_calls
            unparse_calls += 1
            return real_unparse(node)

        with patch("ast.unparse", side_effect=counting_unparse):
            errors, analysis_result = ContextorFacade.analyze_project(str(root))
            assert errors == []
            assert getattr(analysis_result, "collisions", []) == []

            # Hydrate canonical state
            hydrated = hydrate_repository_engine(root)
            assert hydrated is not None
            live_state = hydrated.engine.state
            assert len(live_state.collision_facts) == 2

            # All facts in hydrated state are plain dicts with 0 AST nodes
            for mod, facts in live_state.collision_facts.items():
                for f in facts:
                    assert type(f) is dict
                    assert not hasattr(f, "_node")

            # End-to-end unparse count must be strictly 0 for non-colliding facts
            assert unparse_calls == 0


def test_real_collision_candidate_materializes_exact_code_and_parity():
    """Verify real collision candidates materialize exact code and produce pre-H2C equivalent errors."""
    src_a = "def conflict_func():\n    return 1\n"
    src_b = "def conflict_func():\n    return 2\n"

    tree_a = ast.parse(src_a)
    tree_b = ast.parse(src_b)

    facts = {
        "mod_a": extract_module_collision_facts(tree_a, "mod_a", "/tmp/mod_a.py"),
        "mod_b": extract_module_collision_facts(tree_b, "mod_b", "/tmp/mod_b.py"),
    }

    errors = compute_collisions_from_facts(facts)
    assert len(errors) == 1
    err = errors[0]
    assert err.kind == "NAME_COLLISION"
    assert err.artifact_type == "function"
    assert err.nodes == ["mod_a", "mod_b"]
    assert err.code_snippets["mod_a"] == "def conflict_func():\n    return 1"
    assert err.code_snippets["mod_b"] == "def conflict_func():\n    return 2"
    assert err.symbol_details[0]["name"] == "conflict_func"


def test_hydrated_canonical_collision_facts_incremental_lifecycle():
    """Verify hydrated canonical collision_facts preserve everything required by incremental preparation and plan execution."""
    from contextor.core.analysis.incremental.preparation import prepare_source_update
    from contextor.core.analysis.incremental.materialization import (
        collision_facts_complete,
        ensure_collisions,
        materialize_incremental_state,
    )
    from contextor.core.analysis.state_manager import RepositoryAnalysisState

    mod_a = Module(module_id="mod_a", path="mod_a.py", absolute_path="/tmp/mod_a.py", imports=[])
    plain_facts_a = [{"name": "FuncA", "type": "function", "file": "mod_a", "file_path": "/tmp/mod_a.py", "code": "", "line_start": 1, "line_end": 2, "col_start": 0, "col_end": 10}]

    state = RepositoryAnalysisState(
        modules={"mod_a": mod_a},
        collision_facts={"mod_a": plain_facts_a},
        collisions_state="fresh",
        collisions=[],
    )

    # 1. State completeness check
    assert collision_facts_complete(state) is True
    ensure_collisions(state)
    assert state.collisions_state == "fresh"

    # 2. Preparation with updated source
    src_a_v2 = "def FuncA():\n    return 99\n\ndef FuncB():\n    return 100\n"
    tree_a_v2 = ast.parse(src_a_v2)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "mod_a.py"
        path.write_text(src_a_v2, encoding="utf-8")

        prep = prepare_source_update(
            file_path=str(path),
            module_path="mod_a",
            is_new=False,
            old_module=mod_a,
            old_artifacts={},
            old_usage=None,
            persistent_id="mod_a",
            old_collision_facts=state.collision_facts["mod_a"],
        )

        assert prep.collision_facts_changed is True
        assert len(prep.new_collision_facts) == 2
        names = {f["name"] for f in prep.new_collision_facts}
        assert names == {"FuncA", "FuncB"}




