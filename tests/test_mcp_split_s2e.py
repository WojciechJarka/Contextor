import ast
import importlib
import inspect
from pathlib import Path

from contextor import mcp_server
from contextor.mcp.documentation import load_documentation_index
from contextor.mcp.tools.extract_indexed_report_context import extract_indexed_report_context
from contextor.mcp.tools.get_layer_isolation import get_layer_isolation
from contextor.mcp.tools.get_report_diff import get_report_diff
from contextor.mcp.tools.get_symbol_call_context import get_symbol_call_context
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
    "lookup_artifact_by_symbol", "search_source", "get_source_range",
    "get_symbol_call_context", "get_name_collisions", "get_mcp_documentation",
]

_IMPLEMENTATIONS = {
    "update_file": update_file,
    "get_layer_isolation": get_layer_isolation,
    "get_report_diff": get_report_diff,
    "extract_indexed_report_context": extract_indexed_report_context,
    "get_symbol_call_context": get_symbol_call_context,
}

_EXPECTED_SIGNATURES = {
    "update_file": "(repo_path: str, file_path: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_layer_isolation": "(repo_path: str, layer_name: str, max_clusters: int | None = 8, max_boundary_violations: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_report_diff": "(repo_path: str, max_items: int | None = 20, compact: bool = True, fields: list[str] | None = None) -> str",
    "extract_indexed_report_context": "(repo_path: str, query: str, report_path: str = '', resolve_indices: bool = True, public_api_only: bool = False, max_items: int | None = 20, fields: list[str] | None = None, evidence_limit: int | None = 3, representation: str | None = None) -> str",
    "get_symbol_call_context": "(repo_path: str, symbol: str, direction: str = 'both', depth: int = 1, max_items: int | None = 20, representation: str = 'auto', allow_large_output: bool = False) -> str",
}


def test_s2e_registration_order_bindings_signatures_and_descriptions():
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


def test_s2e_final_ownership_import_graph_and_thin_server():
    root = Path(__file__).parents[1]
    server_tree = ast.parse(Path(mcp_server.__file__).read_text(encoding="utf-8"))
    decorated = [
        node.name
        for node in server_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(ast.unparse(item).startswith("mcp.tool") for item in node.decorator_list)
    ]
    assert decorated == []
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
        and (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
        in {"bind_engine_resolver", "set_analysis_engine"}
        for node in ast.walk(server_tree)
    )

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
        "_mcp_runtime_source_paths",
        "_source_fingerprint",
        "_is_mcp_runtime_source_path",
        "_mcp_runtime_restart_required",
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
    for name in (
        "_persist_live_engine",
        "_semantic_artifact_diff",
        "_semantic_diff_view",
        "_mcp_runtime_source_paths",
        "_source_fingerprint",
        "_is_mcp_runtime_source_path",
        "_mcp_runtime_restart_required",
    ):
        assert owners[name][0].name == "update_file.py"


def test_s2e_update_file_mcp_restart_domain_detection(tmp_path, monkeypatch):
    from contextor.mcp.tools import update_file as update_file_module

    contextor_pkg = tmp_path / "contextor"
    mcp_pkg = contextor_pkg / "mcp"
    tools_pkg = mcp_pkg / "tools"
    tools_pkg.mkdir(parents=True)

    server_py = contextor_pkg / "mcp_server.py"
    main_py = contextor_pkg / "mcp_main.py"
    reg_py = contextor_pkg / "mcp_process_registry.py"
    worker_py = contextor_pkg / "mcp_worker.py"
    runtime_py = mcp_pkg / "runtime.py"
    tool_py = tools_pkg / "get_module_context.py"
    repo_file = tmp_path / "user_repo" / "app.py"
    repo_file.parent.mkdir(parents=True)

    server_py.write_text("server_v1", encoding="utf-8")
    main_py.write_text("main_v1", encoding="utf-8")
    reg_py.write_text("reg_v1", encoding="utf-8")
    worker_py.write_text("worker_v1", encoding="utf-8")
    runtime_py.write_text("runtime_v1", encoding="utf-8")
    tool_py.write_text("tool_v1", encoding="utf-8")
    repo_file.write_text("repo_v1", encoding="utf-8")

    top_levels = (server_py, main_py, reg_py)
    monkeypatch.setattr(update_file_module, "_CONTEXTOR_PACKAGE_ROOT", contextor_pkg)
    monkeypatch.setattr(update_file_module, "_MCP_PACKAGE_SOURCE_ROOT", mcp_pkg)
    monkeypatch.setattr(update_file_module, "_TOP_LEVEL_MCP_SOURCES", top_levels)

    startup_fingerprints = {
        server_py.resolve(): update_file_module._source_fingerprint(server_py),
        main_py.resolve(): update_file_module._source_fingerprint(main_py),
        reg_py.resolve(): update_file_module._source_fingerprint(reg_py),
        runtime_py.resolve(): update_file_module._source_fingerprint(runtime_py),
        tool_py.resolve(): update_file_module._source_fingerprint(tool_py),
    }
    monkeypatch.setattr(
        update_file_module, "_MCP_RUNTIME_SOURCE_FINGERPRINTS", startup_fingerprints
    )

    # 1. Unchanged startup-known MCP source -> False
    assert not update_file_module._mcp_runtime_restart_required(server_py)
    assert not update_file_module._mcp_runtime_restart_required(tool_py)

    # 2. Ordinary repo file outside MCP domain -> False
    assert not update_file_module._mcp_runtime_restart_required(repo_file)

    # 3. mcp_worker.py (explicitly excluded) -> False
    assert not update_file_module._mcp_runtime_restart_required(worker_py)

    # 4. Modified startup-known mcp_server.py -> True
    server_py.write_text("server_v2", encoding="utf-8")
    assert update_file_module._mcp_runtime_restart_required(server_py)

    # 5. Modified startup-known mcp_main.py -> True
    main_py.write_text("main_v2", encoding="utf-8")
    assert update_file_module._mcp_runtime_restart_required(main_py)

    # 6. Modified startup-known mcp_process_registry.py -> True
    reg_py.write_text("reg_v2", encoding="utf-8")
    assert update_file_module._mcp_runtime_restart_required(reg_py)

    # 7. Modified startup-known mcp/tools/*.py -> True
    tool_py.write_text("tool_v2", encoding="utf-8")
    assert update_file_module._mcp_runtime_restart_required(tool_py)

    # 8. Modified startup-known mcp/runtime.py -> True
    runtime_py.write_text("runtime_v2", encoding="utf-8")
    assert update_file_module._mcp_runtime_restart_required(runtime_py)

    # 9. Deleted startup-known MCP source -> True
    deleted_py = mcp_pkg / "deleted_helper.py"
    deleted_py.write_text("del_v1", encoding="utf-8")
    startup_fingerprints[deleted_py.resolve()] = update_file_module._source_fingerprint(deleted_py)
    deleted_py.unlink()
    assert update_file_module._mcp_runtime_restart_required(deleted_py)

    # 10. New .py created under contextor/mcp/ -> True
    new_tool = tools_pkg / "new_tool.py"
    new_tool.write_text("new_tool_v1", encoding="utf-8")
    assert update_file_module._mcp_runtime_restart_required(new_tool)

    # 11. Baseline fingerprint None -> True
    none_baseline_py = mcp_pkg / "none_baseline.py"
    none_baseline_py.write_text("content", encoding="utf-8")
    startup_fingerprints[none_baseline_py.resolve()] = None
    assert update_file_module._mcp_runtime_restart_required(none_baseline_py)

    # 12. Current fingerprint read failure -> True
    monkeypatch.setattr(update_file_module, "_source_fingerprint", lambda _p: None)
    assert update_file_module._mcp_runtime_restart_required(reg_py)
