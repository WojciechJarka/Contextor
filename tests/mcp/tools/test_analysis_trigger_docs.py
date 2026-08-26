import inspect
import json
from pathlib import Path

from contextor import mcp_server
from contextor.mcp import documentation


def _load_doc(tool_name: str) -> dict:
    doc_path = documentation.DOCS_DIR / f"{tool_name}.json"
    return json.loads(doc_path.read_text(encoding="utf-8"))


def test_analysis_trigger_docs__analyze_project_parameters_complete():
    doc = _load_doc("analyze_project")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "exclude_paths (array of strings or null, optional, default null)" in params_text


def test_analysis_trigger_docs__analyze_layer_parameters_complete():
    doc = _load_doc("analyze_layer")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "layer_name (string, required)" in params_text
    assert "exclude_paths (array of strings or null, optional, default null)" in params_text


def test_analysis_trigger_docs__analyze_single_file_parameters_complete():
    doc = _load_doc("analyze_single_file")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "file_path (string, required)" in params_text
    assert "exclude_paths (array of strings or null, optional, default null)" in params_text


def test_analysis_trigger_docs__runtime_signatures_unchanged():
    tools = mcp_server.mcp._tool_manager._tools

    assert str(inspect.signature(tools["analyze_project"].fn)) == (
        "(repo_path: str, exclude_paths: list[str] | None = None) -> str"
    )
    assert str(inspect.signature(tools["analyze_layer"].fn)) == (
        "(repo_path: str, layer_name: str, exclude_paths: list[str] | None = None) -> str"
    )
    assert str(inspect.signature(tools["analyze_single_file"].fn)) == (
        "(repo_path: str, file_path: str, exclude_paths: list[str] | None = None) -> str"
    )
