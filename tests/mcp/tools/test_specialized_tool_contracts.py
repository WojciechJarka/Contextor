import inspect
import json
from pathlib import Path
from typing import Any

from contextor import mcp_server
from contextor.mcp import documentation


def _load_doc(tool_name: str) -> dict:
    doc_path = documentation.DOCS_DIR / f"{tool_name}.json"
    return json.loads(doc_path.read_text(encoding="utf-8"))


def test_specialized_tool_contracts__describe_canonical_state_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["describe_canonical_state"].fn))
    assert sig == "(schema_version: str = '1.0', language_version: str = '1.0') -> str"


def test_specialized_tool_contracts__query_canonical_projection_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["query_canonical_projection"].fn))
    assert sig in (
        "(repo_path: str, request: dict[str, Any]) -> str",
        "(repo_path: str, request: dict[str, typing.Any]) -> str",
    )


def test_specialized_tool_contracts__extract_indexed_report_context_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["extract_indexed_report_context"].fn))
    assert sig == "(repo_path: str, query: str, report_path: str = '', resolve_indices: bool = True, public_api_only: bool = False, max_items: int | None = 20, fields: list[str] | None = None, evidence_limit: int | None = 3, representation: str | None = None) -> str"


def test_specialized_tool_contracts__lookup_index_entries_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["lookup_index_entries"].fn))
    assert sig == "(repo_path: str, ids: list[str], allow_large_output: bool = False) -> str"


def test_specialized_tool_contracts__get_mcp_documentation_signature():
    tools = mcp_server.mcp._tool_manager._tools
    sig = str(inspect.signature(tools["get_mcp_documentation"].fn))
    assert sig == "(tool: str | None = None, tools: list[str] | None = None, sections: list[str] | None = None) -> str"


def test_specialized_tool_contracts__describe_canonical_state_docs_complete():
    doc = _load_doc("describe_canonical_state")
    params_text = "\n".join(doc.get("parameters", []))
    assert "schema_version" in params_text
    assert "language_version" in params_text
    assert "1.0" in params_text


def test_specialized_tool_contracts__query_canonical_projection_docs_complete():
    doc = _load_doc("query_canonical_projection")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "request (object/dict, required)" in params_text


def test_specialized_tool_contracts__extract_indexed_report_context_docs_complete():
    doc = _load_doc("extract_indexed_report_context")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "query (string, required)" in params_text
    assert 'report_path (string, optional, default "")' in params_text
    assert "resolve_indices (boolean, default true)" in params_text
    assert "public_api_only (boolean, default false)" in params_text
    assert "max_items (integer or null, default 20)" in params_text
    assert "fields (array of strings or null, default null)" in params_text
    assert "evidence_limit (integer or null, default 3)" in params_text
    assert "representation (string or null, default null)" in params_text


def test_specialized_tool_contracts__lookup_index_entries_docs_complete():
    doc = _load_doc("lookup_index_entries")
    params_text = "\n".join(doc.get("parameters", []))
    assert "repo_path (string, required)" in params_text
    assert "ids (array of strings, required)" in params_text
    assert "allow_large_output (boolean, default false)" in params_text


def test_specialized_tool_contracts__get_mcp_documentation_docs_complete():
    doc = _load_doc("get_mcp_documentation")
    params_text = "\n".join(doc.get("parameters", []))
    assert "tool (string or null, optional, default null)" in params_text
    assert "tools (array of strings or null, optional, default null)" in params_text
    assert "sections (array of strings or null, optional, default null)" in params_text


def test_specialized_tool_contracts__documentation_default_is_index_only():
    doc = _load_doc("get_mcp_documentation")
    combined = "\n".join(doc.get("behavior", []) + doc.get("usage_notes", []))
    assert "index" in combined.lower()


def test_specialized_tool_contracts__documentation_single_and_multi_tool_filters_are_documented():
    doc = _load_doc("get_mcp_documentation")
    combined = "\n".join(doc.get("parameters", []) + doc.get("behavior", []))
    assert "tool" in combined
    assert "tools" in combined


def test_specialized_tool_contracts__documentation_conflicting_filters_are_documented():
    doc = _load_doc("get_mcp_documentation")
    combined = "\n".join(doc.get("behavior", []) + doc.get("errors", []))
    assert "conflicting" in combined.lower() or "invalid_documentation_query" in combined


def test_specialized_tool_contracts__canonical_projection_docs_require_versioned_safe_request():
    doc = _load_doc("query_canonical_projection")
    combined = "\n".join(doc.get("parameters", []) + doc.get("behavior", []))
    assert "schema_version" in combined
    assert "language_version" in combined
    assert "safe" in combined.lower()


def test_specialized_tool_contracts__indexed_report_docs_pin_all_exact_defaults():
    doc = _load_doc("extract_indexed_report_context")
    params_text = "\n".join(doc.get("parameters", []))
    assert "default 20" in params_text
    assert "default 3" in params_text
    assert "default true" in params_text
    assert "default false" in params_text


def test_specialized_tool_contracts__lookup_index_entries_docs_pin_large_output_guard():
    doc = _load_doc("lookup_index_entries")
    combined = "\n".join(doc.get("parameters", []) + doc.get("behavior", []))
    assert "15360" in combined
    assert "allow_large_output" in combined
