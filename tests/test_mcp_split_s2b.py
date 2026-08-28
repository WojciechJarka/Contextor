import ast
import importlib
import inspect
import json
import subprocess
import sys
from pathlib import Path

from contextor import mcp_server
from contextor.mcp import analysis_jobs
from contextor.mcp.documentation import load_documentation_index
from contextor.mcp.tools.analyze_layer import analyze_layer
from contextor.mcp.tools.analyze_project import analyze_project
from contextor.mcp.tools.analyze_single_file import analyze_single_file
from contextor.mcp.tools.get_analysis_status import get_analysis_status
from contextor.mcp.tools.get_live_events import get_live_events


_EXPECTED_ORDER = [
    "analyze_project", "analyze_layer", "analyze_single_file",
    "get_analysis_status", "get_live_events", "update_file",
    "get_project_architecture", "get_module_context",
    "get_artifact_blast_radius", "search_artifacts",
    "get_symbol_implementation", "get_file_edit_context",
    "get_layer_isolation", "get_report_diff", "describe_canonical_state",
    "query_canonical_projection", "extract_indexed_report_context",
    "lookup_index_entries", "get_artifacts_for_module",
    "lookup_artifact_by_symbol", "search_source", "get_source_range",
    "get_symbol_call_context", "get_name_collisions", "get_mcp_documentation",
]

_IMPLEMENTATIONS = {
    "analyze_project": analyze_project,
    "analyze_layer": analyze_layer,
    "analyze_single_file": analyze_single_file,
    "get_analysis_status": get_analysis_status,
    "get_live_events": get_live_events,
}

_EXPECTED_SIGNATURES = {
    "analyze_project": "(repo_path: str, exclude_paths: list[str] | None = None) -> str",
    "analyze_layer": "(repo_path: str, layer_name: str, exclude_paths: list[str] | None = None) -> str",
    "analyze_single_file": "(repo_path: str, file_path: str, exclude_paths: list[str] | None = None) -> str",
    "get_analysis_status": "(repo_path: str, job_id: str | None = None, max_skipped_files: int | None = 10, allow_large_output: bool = False) -> str",
    "get_live_events": "(repo_path: str, after_revision: int | None = None, limit: int | None = 20) -> str",
}

JOB_STATE = {
    "_analysis_lock", "_analysis_job_lock",
    "_analysis_tasks", "_analysis_jobs_by_repo",
}


def test_s2b_registration_contract_and_implementation_owners():
    registered = mcp_server.mcp._tool_manager._tools
    descriptions = {
        entry["tool"]: entry["short_description"]
        for entry in load_documentation_index()["tools"]
    }

    assert list(registered) == _EXPECTED_ORDER
    for name in _IMPLEMENTATIONS:
        implementation = getattr(
            importlib.import_module(f"contextor.mcp.tools.{name}"), name
        )
        tool = registered[name]
        assert getattr(mcp_server, name) is tool
        assert tool.fn.__wrapped__ is implementation
        assert tool.fn.__module__ == f"contextor.mcp.tools.{name}"
        assert str(inspect.signature(tool.fn)) == _EXPECTED_SIGNATURES[name]
        assert tool.description == descriptions[name]


def test_s2b_import_graph_state_owner_and_remaining_tool_count():
    root = Path(__file__).parents[1]
    server_path = Path(mcp_server.__file__)
    server_tree = ast.parse(server_path.read_text(encoding="utf-8"))
    decorated = [
        node.name
        for node in server_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(ast.unparse(item).startswith("mcp.tool") for item in node.decorator_list)
    ]
    assert decorated == []
    assert JOB_STATE.isdisjoint(vars(mcp_server))
    assert JOB_STATE <= vars(analysis_jobs).keys()
    assert "_MCP_OWNER_TOKEN" not in vars(analysis_jobs)

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
        assert not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.decorator_list for node in tree.body
        )


def test_s2b_spawn_entrypoint_does_not_bootstrap_fastmcp_in_child_mode():
    code = (
        "import json,runpy,sys; "
        "runpy.run_module('contextor.mcp_main', run_name='__mp_main__'); "
        "print(json.dumps({'fastmcp': 'fastmcp' in sys.modules, "
        "'server': 'contextor.mcp_server' in sys.modules}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {"fastmcp": False, "server": False}


def test_s2b_has_no_registration_dependency_binding():
    tree = ast.parse(Path(mcp_server.__file__).read_text(encoding="utf-8"))
    forbidden = {"bind_engine_resolver", "set_analysis_engine"}
    assert not any(
        isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name) and node.func.id in forbidden
            or isinstance(node.func, ast.Attribute) and node.func.attr in forbidden
        )
        for node in ast.walk(tree)
    )
