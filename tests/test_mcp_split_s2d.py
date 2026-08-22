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
    "lookup_artifact_by_symbol", "search_source", "get_source_range",
    "get_symbol_call_context", "get_mcp_documentation",
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
    "get_symbol_implementation": "(repo_path: str, symbol: str, file_paths: list[str] | None = None, mode: str = 'auto', include: list[str] | None = None, methods: list[str] | None = None, member_limit: int | None = 50, file_path: str | None = None) -> str",
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


def test_get_symbol_implementation_auto_small_returns_implementation(tmp_path):
    import json
    src = tmp_path / "small_mod.py"
    src.write_text("def helper():\n    return 42\n", encoding="utf-8")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="helper",
        file_paths=["small_mod.py"],
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "implementation" in res
    assert "def helper():" in res["implementation"]
    assert "auto_fetch" not in res


def test_get_symbol_implementation_auto_large_returns_preview_with_auto_fetch(tmp_path):
    import json
    # Create a function that exceeds 5120 bytes in serialized JSON
    large_body = "\n".join(f"    x_{i} = {i} * 1000" for i in range(300))
    src = tmp_path / "large_mod.py"
    src.write_text(f"def large_func():\n{large_body}\n    return True\n", encoding="utf-8")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="large_func",
        file_paths=["large_mod.py"],
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "preview"
    assert "implementation" not in res
    assert "auto_fetch" in res
    assert res["auto_fetch"]["threshold_bytes"] == 5120
    assert res["auto_fetch"]["candidate_response_bytes"] > 5120
    assert res["auto_fetch"]["decision"] == "preview"
    assert "mode='fetch'" in res["auto_fetch"]["message"]


def test_get_symbol_implementation_explicit_preview_small_returns_preview(tmp_path):
    import json
    src = tmp_path / "small_mod.py"
    src.write_text("def helper():\n    return 42\n", encoding="utf-8")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="helper",
        file_paths=["small_mod.py"],
        mode="preview",
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "preview"
    assert "implementation" not in res
    assert "auto_fetch" not in res


def test_get_symbol_implementation_explicit_fetch_large_returns_implementation(tmp_path):
    import json
    large_body = "\n".join(f"    x_{i} = {i} * 1000" for i in range(300))
    src = tmp_path / "large_mod.py"
    src.write_text(f"def large_func():\n{large_body}\n    return True\n", encoding="utf-8")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="large_func",
        file_paths=["large_mod.py"],
        mode="fetch",
        include=["implementation"],
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "implementation" in res
    assert "def large_func():" in res["implementation"]
    assert "auto_fetch" not in res


def test_get_symbol_implementation_explicit_fetch_without_include_returns_selection_required(tmp_path):
    import json
    src = tmp_path / "small_mod.py"
    src.write_text("def helper():\n    return 42\n", encoding="utf-8")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="helper",
        file_paths=["small_mod.py"],
        mode="fetch",
    )
    res = json.loads(res_raw)
    assert res["status"] == "selection_required"
    assert "Fetch requires an explicit include selection" in res["message"]


def test_get_symbol_implementation_invalid_mode(tmp_path):
    import json
    src = tmp_path / "small_mod.py"
    src.write_text("def helper():\n    return 42\n", encoding="utf-8")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="helper",
        file_paths=["small_mod.py"],
        mode="invalid_mode",
    )
    res = json.loads(res_raw)
    assert res["status"] == "error"
    assert "mode must be 'auto', 'preview', or 'fetch'." in res["error"]


def _generate_exact_candidate_source(target_bytes: int, tmp_path: Path, filename: str) -> Path:
    src = tmp_path / filename
    base_pad = 2000
    src.write_text(f"def exact_func():\n    # {'X' * base_pad}\n    return 42\n", encoding="utf-8")
    probe_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="exact_func",
        file_paths=[filename],
        mode="fetch",
        include=["implementation"],
    )
    diff = target_bytes - len(probe_raw.encode("utf-8"))
    final_pad = base_pad + diff
    src.write_text(f"def exact_func():\n    # {'X' * final_pad}\n    return 42\n", encoding="utf-8")
    verify_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="exact_func",
        file_paths=[filename],
        mode="fetch",
        include=["implementation"],
    )
    assert len(verify_raw.encode("utf-8")) == target_bytes
    return src


def test_get_symbol_implementation_auto_exact_threshold_5120_bytes_returns_implementation(tmp_path):
    import json
    _generate_exact_candidate_source(5120, tmp_path, "mod_5120.py")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="exact_func",
        file_paths=["mod_5120.py"],
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "implementation" in res
    assert len(res_raw.encode("utf-8")) == 5120
    assert "auto_fetch" not in res


def test_get_symbol_implementation_auto_exact_threshold_5121_bytes_returns_preview(tmp_path):
    import json
    _generate_exact_candidate_source(5121, tmp_path, "mod_5121.py")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="exact_func",
        file_paths=["mod_5121.py"],
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "preview"
    assert "implementation" not in res
    assert "auto_fetch" in res
    assert res["auto_fetch"]["threshold_bytes"] == 5120
    assert res["auto_fetch"]["candidate_response_bytes"] == 5121
    assert res["auto_fetch"]["decision"] == "preview"


def test_get_symbol_implementation_file_paths_list_works(tmp_path):
    import json
    src = tmp_path / "mod_list.py"
    src.write_text("def fn_list():\n    return 1\n", encoding="utf-8")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="fn_list",
        file_paths=["mod_list.py"],
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "def fn_list():" in res["implementation"]


def test_get_symbol_implementation_file_path_singular_works(tmp_path):
    import json
    src = tmp_path / "mod_single.py"
    src.write_text("def fn_single():\n    return 2\n", encoding="utf-8")
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="fn_single",
        file_path="mod_single.py",
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "def fn_single():" in res["implementation"]


def test_get_symbol_implementation_file_paths_and_file_path_deduplication(tmp_path):
    import json
    src = tmp_path / "mod_dedup.py"
    src.write_text("def fn_dedup():\n    return 3\n", encoding="utf-8")
    # Same file path passed in both file_paths and file_path
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="fn_dedup",
        file_paths=["mod_dedup.py"],
        file_path="mod_dedup.py",
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "def fn_dedup():" in res["implementation"]

    # Not found search diagnostic should show deduplicated list of 1 file
    not_found_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="non_existent",
        file_paths=["mod_dedup.py"],
        file_path="mod_dedup.py",
    )
    not_found = json.loads(not_found_raw)
    assert not_found["status"] == "not_found"
    assert not_found["searched_files"] == ["mod_dedup.py"]


def test_get_symbol_implementation_file_paths_and_file_path_merging(tmp_path):
    import json
    src_a = tmp_path / "mod_a.py"
    src_a.write_text("def fn_a():\n    return 'a'\n", encoding="utf-8")
    src_b = tmp_path / "mod_b.py"
    src_b.write_text("def fn_b():\n    return 'b'\n", encoding="utf-8")

    # Symbol in file_path (b) while file_paths contains (a)
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="fn_b",
        file_paths=["mod_a.py"],
        file_path="mod_b.py",
    )
    res = json.loads(res_raw)
    assert res["status"] == "resolved"
    assert "def fn_b():" in res["implementation"]

    # Not found search diagnostic should show both merged files
    not_found_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="non_existent",
        file_paths=["mod_a.py"],
        file_path="mod_b.py",
    )
    not_found = json.loads(not_found_raw)
    assert not_found["status"] == "not_found"
    assert not_found["searched_files"] == ["mod_a.py", "mod_b.py"]


def test_get_symbol_implementation_no_file_paths_or_file_path_returns_error(tmp_path):
    import json
    res_raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="any_symbol",
    )
    res = json.loads(res_raw)
    assert res["status"] == "error"
    assert res["error"] == "At least one Python source file is required."
