import inspect
import json
from pathlib import Path

from contextor import mcp_server
from contextor.mcp import documentation


def _load_doc(tool_name: str) -> dict:
    doc_path = documentation.DOCS_DIR / f"{tool_name}.json"
    return json.loads(doc_path.read_text(encoding="utf-8"))


def test_architecture_context_contracts__get_project_architecture_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_project_architecture"].fn))
    assert sig == "(repo_path: str, max_items: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str"


def test_architecture_context_contracts__get_file_edit_context_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_file_edit_context"].fn))
    assert sig == "(repo_path: str, file_path: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, mode: str | None = None, target: str | None = None) -> str"


def test_architecture_context_contracts__get_layer_isolation_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_layer_isolation"].fn))
    assert sig == "(repo_path: str, layer_name: str, max_clusters: int | None = 8, max_boundary_violations: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str"


def test_architecture_context_contracts__get_report_diff_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_report_diff"].fn))
    assert sig == "(repo_path: str, max_items: int | None = 20, compact: bool = True, fields: list[str] | None = None) -> str"


def test_architecture_context_contracts__get_source_range_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_source_range"].fn))
    assert sig == "(repo_path: str, file_path: str, start_line: int, end_line: int, allow_large_output: bool = False) -> str"


def test_architecture_context_contracts__get_project_architecture_docs_complete():
    doc = _load_doc("get_project_architecture")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "max_items (integer or null, default 10)" in params_text
    assert "compact (boolean, default true)" in params_text
    assert "fields (array of strings or null, default null)" in params_text


def test_architecture_context_contracts__get_file_edit_context_docs_complete():
    doc = _load_doc("get_file_edit_context")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert 'file_path (string, optional, default "")' in params_text
    assert "max_items (integer or null, default 30)" in params_text
    assert "compact (boolean, default true)" in params_text
    assert "fields (array of strings or null, default null)" in params_text
    assert "mode (string or null, default null)" in params_text
    assert "target (string or null, default null)" in params_text


def test_architecture_context_contracts__get_layer_isolation_docs_complete():
    doc = _load_doc("get_layer_isolation")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "layer_name (string, required)" in params_text
    assert "max_clusters (integer or null, default 8)" in params_text
    assert "max_boundary_violations (integer or null, default 10)" in params_text
    assert "compact (boolean, default true)" in params_text
    assert "fields (array of strings or null, default null)" in params_text


def test_architecture_context_contracts__get_report_diff_docs_complete():
    doc = _load_doc("get_report_diff")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "max_items (integer or null, default 20)" in params_text
    assert "compact (boolean, default true)" in params_text
    assert "fields (array of strings or null, default null)" in params_text


def test_architecture_context_contracts__get_source_range_docs_complete():
    doc = _load_doc("get_source_range")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "file_path (string, required)" in params_text
    assert "start_line (integer, required)" in params_text
    assert "end_line (integer, required)" in params_text
    assert "allow_large_output (boolean, default false)" in params_text


def test_architecture_context_contracts__report_diff_docs_do_not_equate_empty_diff_with_identical_source():
    doc = _load_doc("get_report_diff")
    combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", []))
    assert "not" in combined.lower() and "identical" in combined.lower()


def test_architecture_context_contracts__source_range_docs_pin_large_output_guard():
    doc = _load_doc("get_source_range")
    combined = "\n".join(doc.get("parameters", []) + doc.get("errors", []))
    assert "15360" in combined
    assert "allow_large_output" in combined


def test_architecture_context_contracts__file_edit_context_docs_describe_minimal_mode():
    doc = _load_doc("get_file_edit_context")
    combined = "\n".join(doc.get("parameters", []) + doc.get("behavior", []))
    assert "minimal" in combined
    assert "in-memory" in combined
