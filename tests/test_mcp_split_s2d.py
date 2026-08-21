import ast
import inspect
from pathlib import Path

from contextor import mcp_server
from contextor.mcp.documentation import load_documentation_index
from contextor.mcp.tools.get_file_edit_context import get_file_edit_context
from contextor.mcp.tools.get_module_context import get_module_context
from contextor.mcp.tools.get_project_architecture import get_project_architecture
from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation


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
    "get_project_architecture": get_project_architecture,
    "get_module_context": get_module_context,
    "get_symbol_implementation": get_symbol_implementation,
    "get_file_edit_context": get_file_edit_context,
}

_EXPECTED_SIGNATURES = {
    "get_project_architecture": "(repo_path: str, max_items: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_module_context": "(repo_path: str, module_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, module: str | None = None) -> str",
    "get_symbol_implementation": "(repo_path: str, symbol: str, file_paths: list[str], mode: str = 'preview', include: list[str] | None = None, methods: list[str] | None = None, member_limit: int | None = 50) -> str",
    "get_file_edit_context": "(repo_path: str, file_path: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, mode: str | None = None, target: str | None = None) -> str",
}


def test_s2d_registration_order_bindings_signatures_and_descriptions():
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


def test_s2d_ownership_and_import_graph():
    root = Path(__file__).parents[1]
    server_tree = ast.parse(Path(mcp_server.__file__).read_text(encoding="utf-8"))
    decorated = [
        node.name
        for node in server_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(ast.unparse(item).startswith("mcp.tool") for item in node.decorator_list)
    ]
    assert decorated == []
    assert set(_IMPLEMENTATIONS).isdisjoint(decorated)
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


def test_s2d_has_no_dependency_binding_or_report_ssot():
    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "bind_" not in server_source
    for implementation in _IMPLEMENTATIONS.values():
        source = Path(implementation.__code__.co_filename).read_text(encoding="utf-8")
        assert "resolve_output_dir" not in source
        assert "_get_canonical_report" not in source
        assert "json.load" not in source
