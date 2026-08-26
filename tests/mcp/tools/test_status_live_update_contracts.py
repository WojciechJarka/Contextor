import inspect
import json
from pathlib import Path

from contextor import mcp_server
from contextor.mcp import documentation


def _load_doc(tool_name: str) -> dict:
    doc_path = documentation.DOCS_DIR / f"{tool_name}.json"
    return json.loads(doc_path.read_text(encoding="utf-8"))


def test_status_live_update_contracts__get_analysis_status_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_analysis_status"].fn))
    assert sig == "(repo_path: str, job_id: str | None = None, max_skipped_files: int | None = 10, allow_large_output: bool = False) -> str"


def test_status_live_update_contracts__get_live_events_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_live_events"].fn))
    assert sig == "(repo_path: str, after_revision: int | None = None, limit: int | None = 20) -> str"


def test_status_live_update_contracts__update_file_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["update_file"].fn))
    assert sig == "(repo_path: str, file_path: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str"


def test_status_live_update_contracts__get_analysis_status_docs_complete():
    doc = _load_doc("get_analysis_status")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "job_id (string or null, optional, default null)" in params_text
    assert "max_skipped_files (integer or null, optional, default 10)" in params_text
    assert "allow_large_output (boolean, optional, default false)" in params_text


def test_status_live_update_contracts__get_live_events_docs_complete():
    doc = _load_doc("get_live_events")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "after_revision (integer or null, optional, default null)" in params_text
    assert "limit (integer or null, optional, default 20)" in params_text


def test_status_live_update_contracts__update_file_docs_complete():
    doc = _load_doc("update_file")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "file_path (string, required)" in params_text
    assert "max_items (integer or null, default 30)" in params_text
    assert "compact (boolean, default true)" in params_text
    assert "fields (array of strings or null, default null)" in params_text


def test_status_live_update_contracts__update_file_docs_describe_desktop_watcher_path():
    doc = _load_doc("update_file")
    combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", []))
    assert "desktop_watcher" in combined
    assert "get_live_events" in combined


def test_status_live_update_contracts__update_file_docs_describe_manual_incremental_path():
    doc = _load_doc("update_file")
    combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", []))
    assert "semantic_diff" in combined
    assert "bodies_changed" in combined


def test_status_live_update_contracts__update_file_docs_describe_runtime_restart_signal():
    doc = _load_doc("update_file")
    combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", [] + doc.get("errors", [])))
    assert "runtime_restart_required" in combined
