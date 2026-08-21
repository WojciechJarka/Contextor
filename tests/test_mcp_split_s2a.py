import ast
import inspect
from pathlib import Path

from contextor import mcp_server
from contextor.mcp.documentation import load_documentation_index
from contextor.mcp.tools.describe_canonical_state import (
    describe_canonical_state as describe_canonical_state_impl,
)
from contextor.mcp.tools.get_mcp_documentation import (
    get_mcp_documentation as get_mcp_documentation_impl,
)
from contextor.mcp.tools.lookup_index_entries import (
    lookup_index_entries as lookup_index_entries_impl,
)
from contextor.mcp.tools.query_canonical_projection import (
    query_canonical_projection as query_canonical_projection_impl,
)


EXPECTED_ORDER = [
    "analyze_project",
    "analyze_layer",
    "analyze_single_file",
    "get_analysis_status",
    "get_live_events",
    "update_file",
    "get_project_architecture",
    "get_module_context",
    "get_artifact_blast_radius",
    "search_artifacts",
    "get_symbol_implementation",
    "get_file_edit_context",
    "get_layer_isolation",
    "get_report_diff",
    "describe_canonical_state",
    "query_canonical_projection",
    "extract_indexed_report_context",
    "lookup_index_entries",
    "get_artifacts_for_module",
    "lookup_artifact_by_symbol",
    "get_mcp_documentation",
]

IMPLEMENTATIONS = {
    "get_mcp_documentation": get_mcp_documentation_impl,
    "describe_canonical_state": describe_canonical_state_impl,
    "lookup_index_entries": lookup_index_entries_impl,
    "query_canonical_projection": query_canonical_projection_impl,
}

EXPECTED_SIGNATURES = {
    "get_mcp_documentation": "(tool: str | None = None, tools: list[str] | None = None, sections: list[str] | None = None) -> str",
    "describe_canonical_state": "() -> str",
    "lookup_index_entries": "(repo_path: str, ids: list[str]) -> str",
    "query_canonical_projection": "(repo_path: str, request: dict[str, typing.Any]) -> str",
}

EXPECTED_PARAMETERS = {
    "get_mcp_documentation": {
        "properties": {
            "tool": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
            "tools": {
                "anyOf": [
                    {"items": {"type": "string"}, "type": "array"},
                    {"type": "null"},
                ],
                "default": None,
            },
            "sections": {
                "anyOf": [
                    {"items": {"type": "string"}, "type": "array"},
                    {"type": "null"},
                ],
                "default": None,
            },
        },
        "type": "object",
    },
    "describe_canonical_state": {"properties": {}, "type": "object"},
    "lookup_index_entries": {
        "properties": {
            "repo_path": {"type": "string"},
            "ids": {"items": {"type": "string"}, "type": "array"},
        },
        "required": ["repo_path", "ids"],
        "type": "object",
    },
    "query_canonical_projection": {
        "properties": {
            "repo_path": {"type": "string"},
            "request": {"additionalProperties": True, "type": "object"},
        },
        "required": ["repo_path", "request"],
        "type": "object",
    },
}


def test_s2a_registration_order_owners_signatures_schemas_and_descriptions():
    registered = mcp_server.mcp._tool_manager._tools
    descriptions = {
        entry["tool"]: entry["short_description"]
        for entry in load_documentation_index()["tools"]
    }

    assert list(registered) == EXPECTED_ORDER
    for name, implementation in IMPLEMENTATIONS.items():
        tool = registered[name]
        assert getattr(mcp_server, name) is tool
        assert tool.fn is implementation
        assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
        assert str(inspect.signature(tool.fn)) == EXPECTED_SIGNATURES[name]
        assert tool.parameters == EXPECTED_PARAMETERS[name]
        assert tool.description == descriptions[name]


def test_s2a_tool_modules_have_no_registration_or_forbidden_import_edges():
    tools_dir = Path(__file__).parents[1] / "contextor" / "mcp" / "tools"
    before = list(mcp_server.mcp._tool_manager._tools)

    for name in IMPLEMENTATIONS:
        path = tools_dir / f"{name}.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "contextor.mcp_server" not in imported_modules
        assert not any(module.startswith("contextor.mcp.tools.") for module in imported_modules)
        assert not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.decorator_list
            for node in tree.body
        )
        assert "FastMCP" not in path.read_text(encoding="utf-8")

    assert list(mcp_server.mcp._tool_manager._tools) == before


def test_s2a_implementations_remain_moved_after_later_slices():
    server_path = Path(mcp_server.__file__)
    tree = ast.parse(server_path.read_text(encoding="utf-8"))
    decorated = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(ast.unparse(item).startswith("mcp.tool") for item in node.decorator_list)
    ]

    assert len(decorated) == 12
    assert set(IMPLEMENTATIONS).isdisjoint(decorated)


def test_s2a_query_projection_uses_single_shared_runtime_owner():
    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
    tool_source = inspect.getsource(
        __import__(
            "contextor.mcp.tools.query_canonical_projection",
            fromlist=["query_canonical_projection"],
        )
    )

    assert "bind_engine_resolver" not in server_source
    assert "bind_engine_resolver" not in tool_source
    assert "_get_or_init_engine" not in server_source
    assert "from contextor.mcp import runtime as mcp_runtime" in tool_source
    assert "mcp_runtime.get_or_init_engine(root)" in tool_source
