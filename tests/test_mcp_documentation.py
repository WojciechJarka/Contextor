import inspect
import json
from pathlib import Path

from contextor import mcp_server
from contextor.mcp import documentation


LEGACY_SIGNATURES = {
    "analyze_project": "(repo_path: str, exclude_paths: list[str] | None = None) -> str",
    "analyze_layer": "(repo_path: str, layer_name: str, exclude_paths: list[str] | None = None) -> str",
    "analyze_single_file": "(repo_path: str, file_path: str, exclude_paths: list[str] | None = None) -> str",
    "get_analysis_status": "(repo_path: str, job_id: str | None = None, max_skipped_files: int | None = 10, allow_large_output: bool = False) -> str",
    "get_live_events": "(repo_path: str, after_revision: int | None = None, limit: int | None = 20) -> str",
    "update_file": "(repo_path: str, file_path: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_project_architecture": "(repo_path: str, max_items: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_module_context": "(repo_path: str, module_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, module: str | None = None) -> str",
    "get_artifact_blast_radius": "(repo_path: str, artifact_name: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, representation: str = 'named', artifact: str | None = None) -> str",
    "search_artifacts": "(repo_path: str, search_term: str | None = None, limit: int | None = 20, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None, query: str | None = None) -> str",
    "get_symbol_implementation": "(repo_path: str, symbol: str, file_paths: list[str] | None = None, mode: str = 'auto', include: list[str] | None = None, methods: list[str] | None = None, member_limit: int | None = 50, file_path: str | None = None) -> str",
    "get_file_edit_context": "(repo_path: str, file_path: str = '', max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None, mode: str | None = None, target: str | None = None) -> str",
    "get_layer_isolation": "(repo_path: str, layer_name: str, max_clusters: int | None = 8, max_boundary_violations: int | None = 10, compact: bool = True, fields: list[str] | None = None) -> str",
    "get_report_diff": "(repo_path: str, max_items: int | None = 20, compact: bool = True, fields: list[str] | None = None) -> str",
    "describe_canonical_state": "(schema_version: str = '1.0', language_version: str = '1.0') -> str",
    "query_canonical_projection": "(repo_path: str, request: dict[str, typing.Any]) -> str",
    "extract_indexed_report_context": "(repo_path: str, query: str, report_path: str = '', resolve_indices: bool = True, public_api_only: bool = False, max_items: int | None = 20, fields: list[str] | None = None, evidence_limit: int | None = 3, representation: str | None = None) -> str",
    "lookup_index_entries": "(repo_path: str, ids: list[str], allow_large_output: bool = False) -> str",
    "get_artifacts_for_module": "(repo_path: str, module_name: str = '', include_consumers: bool = True, symbol_filter: str = '', limit: int | None = 50, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None, representation: str = 'named', module: str | None = None) -> str",
    "lookup_artifact_by_symbol": "(repo_path: str, symbol_name: str = '', limit: int | None = 20, evidence_limit: int | None = 20, compact: bool = True, fields: list[str] | None = None, symbol: str | None = None) -> str",
}


def test_documentation_has_exact_public_tool_file_coverage():
    index = documentation.validate_documentation_catalog()
    indexed = [entry["tool"] for entry in index["tools"]]
    public = list(mcp_server.mcp._tool_manager._tools)
    doc_files = sorted(
        path.stem
        for path in documentation.DOCS_DIR.glob("*.json")
        if path.name != "index.json"
    )

    assert indexed[:20] == list(LEGACY_SIGNATURES)
    assert indexed[-1] == "get_mcp_documentation"
    assert set(public) == set(indexed) == set(doc_files)


def test_discovery_descriptions_are_short_and_index_backed():
    index = documentation.load_documentation_index()
    descriptions = {
        entry["tool"]: entry["short_description"] for entry in index["tools"]
    }

    assert all(len(value.encode("utf-8")) <= 300 for value in descriptions.values())
    assert all("\n\n" not in value for value in descriptions.values())
    for name, tool in mcp_server.mcp._tool_manager._tools.items():
        assert tool.description == descriptions[name]
        assert tool.fn.__doc__ is None




def test_documentation_default_returns_only_index(monkeypatch):
    loaded = []
    original = documentation._read_json

    def tracked(path):
        loaded.append(path)
        return original(path)

    monkeypatch.setattr(documentation, "_read_json", tracked)
    result = json.loads(mcp_server.get_mcp_documentation.fn())

    assert result["version"]
    assert len(result["tools"]) == 29
    assert result["documentation_hint"] == (
        "For full documentation of a tool, call "
        "get_mcp_documentation with tool=<tool_name>."
    )
    assert loaded == [documentation.INDEX_PATH]


def test_get_symbol_implementation_description_prevents_undocumented_modes():
    index = documentation.load_documentation_index()
    entry = next(
        item
        for item in index["tools"]
        if item["tool"] == "get_symbol_implementation"
    )
    description = entry["short_description"]
    assert "auto|preview|fetch" in description
    assert "include=['implementation']" in description
    assert "Use only documented argument names" in description
    assert len(description.encode("utf-8")) <= 300
    document = documentation.load_tool_document("get_symbol_implementation")
    serialized = json.dumps(document)
    assert "only to missing fetch include selection" not in serialized
    assert "parameter_contract_error" in serialized
    assert "Symbol-name and selected method-name lookup misses" in serialized
    assert (
        "Unknown argument names are rejected by the MCP/FastMCP input boundary"
        not in serialized
    )
    assert (
        "dedicated MCP input-boundary middleware"
        in serialized
    )
    assert (
        "Missing required arguments receive the same"
        in serialized
    )
    assert (
        "ToolError cause chain"
        in serialized
    )
    assert (
        "Unrelated ToolError or validation failures are re-raised"
        in serialized
    )


def test_single_tool_and_section_filters_load_only_selected_document(monkeypatch):
    loaded = []
    original = documentation._read_json

    def tracked(path):
        loaded.append(path)
        return original(path)

    monkeypatch.setattr(documentation, "_read_json", tracked)
    result = json.loads(
        mcp_server.get_mcp_documentation.fn(
            tool="get_file_edit_context",
            sections=["parameters", "freshness", "errors"],
        )
    )

    assert list(result["tools"]) == ["get_file_edit_context"]
    assert list(result["tools"]["get_file_edit_context"]) == [
        "parameters",
        "freshness",
        "errors",
    ]
    assert loaded == [
        documentation.INDEX_PATH,
        documentation.INDEX_PATH,
        documentation.DOCS_DIR / "get_file_edit_context.json",
    ]


def test_explicit_multi_tool_filter_is_deterministic():
    first = mcp_server.get_mcp_documentation.fn(
        tools=["get_module_context", "analyze_project"],
        sections=["purpose"],
    )
    second = mcp_server.get_mcp_documentation.fn(
        tools=["analyze_project", "get_module_context"],
        sections=["purpose"],
    )

    assert first == second
    assert list(json.loads(first)["tools"]) == [
        "analyze_project",
        "get_module_context",
    ]


def test_unknown_tool_section_and_unscoped_sections_are_diagnostic():
    unknown = documentation.query_documentation(
        tool="missing",
        sections=["missing_section"],
    )
    unscoped = documentation.query_documentation(sections=["purpose"])
    conflicting = documentation.query_documentation(
        tool="analyze_project",
        tools=["analyze_layer"],
    )

    assert unknown["status"] == "invalid_documentation_query"
    assert unknown["unknown_tools"] == ["missing"]
    assert unknown["unknown_sections"] == ["missing_section"]
    assert unscoped["status"] == "tool_selection_required"
    assert conflicting["status"] == "invalid_documentation_query"


def test_legacy_tool_names_signatures_and_defaults_are_unchanged():
    tools = mcp_server.mcp._tool_manager._tools

    assert list(tools)[:20] == list(LEGACY_SIGNATURES)
    assert {
        name: str(inspect.signature(tools[name].fn))
        for name in LEGACY_SIGNATURES
    } == LEGACY_SIGNATURES


def test_documentation_reader_paths_are_package_local(monkeypatch):
    read_paths = []
    original = Path.read_text

    def tracked(path, *args, **kwargs):
        read_paths.append(path.resolve())
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked)
    documentation.query_documentation(tool="get_module_context")

    docs_root = documentation.DOCS_DIR.resolve()
    assert read_paths
    assert all(path.parent == docs_root for path in read_paths)


def test_contextor_profile_analysis_is_registered_and_documented():
    tool = mcp_server.mcp._tool_manager._tools[
        "contextor_profile_analysis"
    ]
    index = documentation.load_documentation_index()
    entry = next(
        item
        for item in index["tools"]
        if item["tool"] == "contextor_profile_analysis"
    )

    assert tool.description == entry["short_description"]
    assert str(inspect.signature(tool.fn, eval_str=True)) == (
        "(repo_path: str, exclude_paths: list[str] | None = None) -> str"
    )
    assert index["tools"][-1]["tool"] == "get_mcp_documentation"


def test_get_symbol_lineage_is_registered_with_documented_public_signature():
    tool = mcp_server.mcp._tool_manager._tools[
        "get_symbol_lineage"
    ]
    index = documentation.load_documentation_index()
    entry = next(
        item
        for item in index["tools"]
        if item["tool"] == "get_symbol_lineage"
    )

    assert (
        tool.description
        == entry["short_description"]
        == (
            "Read canonical static value/data lineage for one "
            "exact symbol from LIVE state with bounded "
            "progressive disclosure."
        )
    )
    assert str(inspect.signature(tool.fn, eval_str=True)) == (
        "(repo_path: str, symbol: str, mode: str = 'auto', "
        "sections: list[str] | None = None, "
        "representation: str = 'auto', "
        "allow_large_output: bool = False) -> str"
    )


def test_get_symbol_lineage_documentation_is_lazy_and_complete(
    monkeypatch,
):
    loaded = []
    original = documentation._read_json

    def tracked(path):
        loaded.append(path)
        return original(path)

    monkeypatch.setattr(
        documentation,
        "_read_json",
        tracked,
    )
    result = documentation.query_documentation(
        tool="get_symbol_lineage",
    )

    assert list(result["tools"]) == [
        "get_symbol_lineage"
    ]
    document = result["tools"][
        "get_symbol_lineage"
    ]
    assert list(document) == list(
        documentation.DOCUMENTATION_SECTIONS
    )
    assert loaded == [
        documentation.INDEX_PATH,
        documentation.INDEX_PATH,
        (
            documentation.DOCS_DIR
            / "get_symbol_lineage.json"
        ),
    ]
