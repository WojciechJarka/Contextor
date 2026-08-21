import ast
import inspect
from pathlib import Path

from contextor import mcp_server
from contextor.mcp.documentation import load_documentation_index
from contextor.mcp.tools.get_artifact_blast_radius import get_artifact_blast_radius
from contextor.mcp.tools.get_artifacts_for_module import get_artifacts_for_module
from contextor.mcp.tools.lookup_artifact_by_symbol import lookup_artifact_by_symbol
from contextor.mcp.tools.search_artifacts import search_artifacts


EXPECTED_ORDER = [
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

IMPLEMENTATIONS = {
    "get_artifact_blast_radius": get_artifact_blast_radius,
    "search_artifacts": search_artifacts,
    "get_artifacts_for_module": get_artifacts_for_module,
    "lookup_artifact_by_symbol": lookup_artifact_by_symbol,
}

EXPECTED_SIGNATURES = {
    "get_artifact_blast_radius": "(repo_path: str, artifact_name: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str",
    "search_artifacts": "(repo_path: str, search_term: str, limit: int | None = 20, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_artifacts_for_module": "(repo_path: str, module_name: str, include_consumers: bool = True, symbol_filter: str = '', limit: int | None = 50, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None) -> str",
    "lookup_artifact_by_symbol": "(repo_path: str, symbol_name: str, limit: int | None = 20, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None) -> str",
}


def test_s2c_registration_order_bindings_signatures_and_descriptions():
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
        assert tool.description == descriptions[name]


def test_s2c_ownership_import_graph_and_shared_helper_uniqueness():
    root = Path(__file__).parents[1]
    server_path = Path(mcp_server.__file__)
    server_tree = ast.parse(server_path.read_text(encoding="utf-8"))
    decorated = [
        node.name
        for node in server_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(ast.unparse(item).startswith("mcp.tool") for item in node.decorator_list)
    ]
    assert len(decorated) == 8
    assert set(IMPLEMENTATIONS).isdisjoint(decorated)

    for name in IMPLEMENTATIONS:
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

    helper_names = {
        "bounded_items", "read_registries", "canonical_symbol_consumers",
        "module_truth_unavailable", "canonical_symbol_catalog",
    }
    owners = {}
    for path in (root / "contextor" / "mcp").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in helper_names:
                    owners.setdefault(node.name, []).append(path)
    assert {name: len(paths) for name, paths in owners.items()} == {
        name: 1 for name in helper_names
    }


def test_s2c_has_no_registration_dependency_binding_or_report_io():
    root = Path(__file__).parents[1]
    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
    assert "bind_" not in server_source
    for name in IMPLEMENTATIONS:
        source = (
            root / "contextor" / "mcp" / "tools" / f"{name}.py"
        ).read_text(encoding="utf-8")
        assert "resolve_output_dir" not in source
        assert "_get_canonical_report" not in source
        assert "json.load" not in source
