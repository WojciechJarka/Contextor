"""Tests for _execute_canonical_query and related MCP canonical-state tools.

These tests verify:
- _execute_canonical_query evaluates expressions in a safe sandbox
- query_canonical_state and query_canonical_state_bounded call
  _execute_canonical_query directly (not via .fn proxy), so Contextor's
  static analysis can resolve the dependency.
- Bounded tool correctly applies _bounded_query_result.
"""

import ast
import json
import dataclasses
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.mcp_server import (
    _bounded_query_result,
    _execute_canonical_query,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(modules=None, artifacts=None, dependency_graph=None, registry=None):
    """Build a minimal fake engine accepted by _execute_canonical_query."""
    state = SimpleNamespace(
        modules=modules or {},
        artifacts=artifacts or {},
        dependency_graph=dependency_graph or {},
    )
    return SimpleNamespace(state=state, registry=registry or {})


# ---------------------------------------------------------------------------
# _execute_canonical_query — core sandbox tests
# ---------------------------------------------------------------------------

class TestExecuteCanonicalQuery:
    def test_simple_expression_returns_json(self):
        engine = _make_engine(modules={"a": SimpleNamespace(imports=[1, 2, 3])})
        result = _execute_canonical_query(engine, "list(modules.keys())")
        assert json.loads(result) == ["a"]

    def test_len_builtin_is_available(self):
        engine = _make_engine(modules={"x": None, "y": None})
        result = _execute_canonical_query(engine, "len(modules)")
        assert json.loads(result) == 2

    def test_filter_expression(self):
        engine = _make_engine(
            modules={
                "mod.a": SimpleNamespace(imports=list(range(25))),
                "mod.b": SimpleNamespace(imports=[]),
            }
        )
        expr = "[m for m, mod in modules.items() if len(mod.imports) > 20]"
        result = json.loads(_execute_canonical_query(engine, expr))
        assert result == ["mod.a"]

    def test_artifacts_variable_accessible(self):
        engine = _make_engine(artifacts={"A1": "Foo::bar", "A2": "Baz::qux"})
        result = _execute_canonical_query(engine, "list(artifacts.keys())")
        assert json.loads(result) == ["A1", "A2"]

    def test_registry_variable_accessible(self):
        engine = _make_engine(registry={"id_1": "module.path"})
        result = _execute_canonical_query(engine, "list(registry.keys())")
        assert json.loads(result) == ["id_1"]

    def test_syntax_error_returns_error_string(self):
        engine = _make_engine()
        result = _execute_canonical_query(engine, "this is not valid python !!!")
        assert result.startswith("Error executing query:")

    def test_forbidden_builtin_import_blocked(self):
        engine = _make_engine()
        result = _execute_canonical_query(engine, "__import__('os').getcwd()")
        assert result.startswith("Error executing query:")

    def test_set_serialized_as_list(self):
        engine = _make_engine()
        result = _execute_canonical_query(engine, "{1, 2, 3}")
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert sorted(parsed) == [1, 2, 3]

    def test_dataclass_serialized_via_asdict(self):
        @dataclasses.dataclass
        class Mod:
            name: str
            count: int

        engine = _make_engine(modules={"x": Mod(name="hello", count=5)})
        result = _execute_canonical_query(engine, "modules['x']")
        parsed = json.loads(result)
        assert parsed == {"name": "hello", "count": 5}

    def test_object_with_to_dict_serialized(self):
        class Obj:
            def to_dict(self):
                return {"key": "value"}

        engine = _make_engine(modules={"x": Obj()})
        result = _execute_canonical_query(engine, "modules['x']")
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_fallback_serialization_uses_str(self):
        class Unserializable:
            def __repr__(self):
                return "custom_repr"

        engine = _make_engine(modules={"x": Unserializable()})
        result = _execute_canonical_query(engine, "modules['x']")
        parsed = json.loads(result)
        assert isinstance(parsed, str)


# ---------------------------------------------------------------------------
# query_canonical_state — MCP tool integration
# ---------------------------------------------------------------------------

class TestQueryCanonicalStateTool:
    def test_returns_error_when_no_engine(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)
        result = mcp_server.query_canonical_state.fn(
            str(tmp_path), "list(modules.keys())"
        )
        assert "Error" in result
        assert "analyze_project" in result

    def test_evaluates_expression_via_execute_canonical_query(
        self, tmp_path, monkeypatch
    ):
        engine = _make_engine(modules={"mod.a": None})
        monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
        result = mcp_server.query_canonical_state.fn(
            str(tmp_path), "list(modules.keys())"
        )
        assert json.loads(result) == ["mod.a"]

    def test_does_not_use_fn_proxy_internally(self):
        """query_canonical_state_bounded must call _execute_canonical_query
        directly, not query_canonical_state.fn — otherwise Contextor cannot
        resolve the dependency via static AST analysis."""
        src = Path(mcp_server.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "query_canonical_state_bounded"
            ):
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute):
                        assert not (
                            isinstance(child.value, ast.Name)
                            and child.value.id == "query_canonical_state"
                            and child.attr == "fn"
                        ), (
                            "query_canonical_state_bounded must not call "
                            "query_canonical_state.fn — use _execute_canonical_query directly."
                        )


# ---------------------------------------------------------------------------
# query_canonical_state_bounded — MCP tool integration
# ---------------------------------------------------------------------------

class TestQueryCanonicalStateBounded:
    def test_returns_error_when_no_engine(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)
        result = mcp_server.query_canonical_state_bounded.fn(
            str(tmp_path), "list(modules.keys())"
        )
        assert "Error" in result
        assert "analyze_project" in result

    def test_bounds_list_result(self, tmp_path, monkeypatch):
        modules = {f"mod.{i}": None for i in range(50)}
        engine = _make_engine(modules=modules)
        monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
        result = mcp_server.query_canonical_state_bounded.fn(
            str(tmp_path), "list(modules.keys())", limit=10
        )
        parsed = json.loads(result)
        assert parsed["total_items"] == 50
        assert parsed["truncated"] is True
        assert len(parsed["result"]) == 10

    def test_no_truncation_when_within_limit(self, tmp_path, monkeypatch):
        modules = {"mod.a": None, "mod.b": None}
        engine = _make_engine(modules=modules)
        monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
        result = mcp_server.query_canonical_state_bounded.fn(
            str(tmp_path), "list(modules.keys())", limit=100
        )
        parsed = json.loads(result)
        assert parsed["truncated"] is False
        assert parsed["total_items"] == 2

    def test_propagates_query_error_directly(self, tmp_path, monkeypatch):
        engine = _make_engine()
        monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
        result = mcp_server.query_canonical_state_bounded.fn(
            str(tmp_path), "this is !!! invalid"
        )
        assert "Error executing query" in result


# ---------------------------------------------------------------------------
# Architectural: _execute_canonical_query is statically reachable from both tools
# ---------------------------------------------------------------------------

def test_execute_canonical_query_called_directly_from_both_tools():
    """Verify via AST that both MCP tools reference _execute_canonical_query
    as a plain Name call — not through an attribute proxy — so that Contextor
    can detect the hard dependency in static analysis."""
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)

    tool_names = {"query_canonical_state", "query_canonical_state_bounded"}
    found_calls: dict[str, bool] = {name: False for name in tool_names}

    for node in tree.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name in tool_names
        ):
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == "_execute_canonical_query"
                ):
                    found_calls[node.name] = True

    assert found_calls["query_canonical_state"], (
        "query_canonical_state must call _execute_canonical_query directly"
    )
    assert found_calls["query_canonical_state_bounded"], (
        "query_canonical_state_bounded must call _execute_canonical_query directly"
    )
