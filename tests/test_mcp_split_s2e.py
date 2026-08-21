import ast
import inspect
from pathlib import Path

from contextor import mcp_server
from contextor.mcp.documentation import load_documentation_index
from contextor.mcp.tools.extract_indexed_report_context import extract_indexed_report_context
from contextor.mcp.tools.get_layer_isolation import get_layer_isolation
from contextor.mcp.tools.get_report_diff import get_report_diff
from contextor.mcp.tools.update_file import update_file


_EXPECTED_ORDER = [
    "analyze_project", "analyze_layer", "analyze_single_file",
    "get_analysis_status", "get_live_events", "update_file",
    "get_project_architecture", "get_module_context",
    "get_artifact_blast_radius", "search_artifacts",
    "get_symbol_implementation", "get_file_edit_context",
    "get_layer_isolation", "get_report_diff", "describe_canonical_state",
    "query_canonical_projection", "extract_indexed_report_context",
    "lookup_index_entries", "get_artifacts_for_module",
    "lookup_artifact_by_symbol", "get_mcp_documentation",
]

_IMPLEMENTATIONS = {
    "update_file": update_file,
    "get_layer_isolation": get_layer_isolation,
    "get_report_diff": get_report_diff,
    "extract_indexed_report_context": extract_indexed_report_context,
}

_EXPECTED_SIGNATURES = {
    "update_file": "(repo_path: str, file_path: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_layer_isolation": "(repo_path: str, layer_name: str, max_clusters: int | None = 8, max_boundary_violations: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_report_diff": "(repo_path: str, max_items: int | None = 20, compact: bool = True, fields: list[str] | None = None) -> str",
    "extract_indexed_report_context": "(repo_path: str, query: str, report_path: str = '', resolve_indices: bool = True, public_api_only: bool = False, max_items: int | None = 20, fields: list[str] | None = None) -> str",
}


def test_s2e_registration_order_bindings_signatures_and_descriptions():
    registered = mcp_server.mcp._tool_manager._tools
    descriptions = {
        entry["tool"]: entry["short_description"]
        for entry in load_documentation_index()["tools"]
    }
    assert list(registered) == _EXPECTED_ORDER
    for name, implementation in _IMPLEMENTATIONS.items():
        tool = registered[name]
        assert getattr(mcp_server, name) is tool
        assert tool.fn is implementation
        assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
        assert str(inspect.signature(tool.fn)) == _EXPECTED_SIGNATURES[name]
        assert tool.description == descriptions[name]


def test_s2e_final_ownership_import_graph_and_thin_server():
    root = Path(__file__).parents[1]
    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
    server_tree = ast.parse(server_source)
    decorated = [
        node.name
        for node in server_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(ast.unparse(item).startswith("mcp.tool") for item in node.decorator_list)
    ]
    assert decorated == []
    assert "bind_" not in server_source

    for name in _IMPLEMENTATIONS:
        path = root / "contextor" / "mcp" / "tools" / f"{name}.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.module for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "contextor.mcp_server" not in imports
        assert not any(module.startswith("contextor.mcp.tools.") for module in imports)
        assert "FastMCP" not in source
        public_functions = [
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        ]
        assert [node.name for node in public_functions] == [name]
        assert not public_functions[0].decorator_list
        assert ast.get_docstring(public_functions[0]) is None


def test_s2e_helper_ownership_and_report_contract_sharing():
    root = Path(__file__).parents[1] / "contextor" / "mcp"
    helper_names = {
        "_persist_live_engine",
        "_semantic_artifact_diff",
        "_semantic_diff_view",
        "_resolve_cluster_ids",
        "get_canonical_report",
    }
    owners = {name: [] for name in helper_names}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in owners:
                    owners[node.name].append(path)
    assert {name: len(paths) for name, paths in owners.items()} == {
        name: 1 for name in helper_names
    }
    assert owners["get_canonical_report"][0].name == "report_helpers.py"
    assert owners["_resolve_cluster_ids"][0].name == "get_layer_isolation.py"
    for name in ("_persist_live_engine", "_semantic_artifact_diff", "_semantic_diff_view"):
        assert owners[name][0].name == "update_file.py"
