import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from contextor.core.canonical_state_query.runtime import validate_request, execute_projection
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.canonical_state_query.contract import (
    CANONICAL_QUERY_SCHEMA_VERSION,
    CANONICAL_QUERY_SCHEMA_VERSION_V1_1,
    LANGUAGE_VERSION,
    LANGUAGE_VERSION_V1_1,
)


def test_canonical_projection_single_call__both_versions_omitted_default_to_v1():
    req = {
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    normalized, error = validate_request(req)
    assert error is None
    assert normalized is not None
    assert normalized["schema_version"] == "1.0"
    assert normalized["language_version"] == "1.0"
    assert normalized["root"] == "modules"
    assert normalized["select"] == ["module_name"]


def test_canonical_projection_single_call__defaulting_does_not_mutate_input():
    req = {
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    req_before = copy.deepcopy(req)
    normalized, error = validate_request(req)
    assert error is None
    assert req == req_before
    assert "schema_version" not in req
    assert "language_version" not in req


def test_canonical_projection_single_call__missing_schema_with_explicit_language_fails_closed():
    req = {
        "language_version": "1.0",
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    normalized, error = validate_request(req)
    assert normalized is None
    assert error is not None
    assert error["status"] == "error"
    assert error["error"]["code"] == "missing_required_field"
    assert error["error"]["path"] == "schema_version"


def test_canonical_projection_single_call__missing_language_with_explicit_schema_fails_closed():
    req = {
        "schema_version": "1.0",
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    normalized, error = validate_request(req)
    assert normalized is None
    assert error is not None
    assert error["status"] == "error"
    assert error["error"]["code"] == "missing_required_field"
    assert error["error"]["path"] == "language_version"


def test_canonical_projection_single_call__explicit_v1_is_equivalent_to_implicit_v1():
    req_implicit = {
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    req_explicit = {
        "schema_version": "1.0",
        "language_version": "1.0",
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }

    norm_implicit, err_implicit = validate_request(req_implicit)
    norm_explicit, err_explicit = validate_request(req_explicit)

    assert err_implicit is None
    assert err_explicit is None
    assert norm_implicit == norm_explicit


def test_canonical_projection_single_call__explicit_v1_1_remains_v1_1():
    req_1_1 = {
        "schema_version": "1.1",
        "language_version": "1.1",
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
        "evidence_limit": 5,
    }
    normalized, error = validate_request(req_1_1)
    assert error is None
    assert normalized is not None
    assert normalized["schema_version"] == "1.1"
    assert normalized["language_version"] == "1.1"
    assert normalized["evidence_limit"] == 5


def test_canonical_projection_single_call__cross_version_pairs_still_fail():
    for schema_ver, lang_ver in [("1.0", "1.1"), ("1.1", "1.0")]:
        req = {
            "schema_version": schema_ver,
            "language_version": lang_ver,
            "root": "modules",
            "filters": [],
            "select": ["module_name"],
        }
        normalized, error = validate_request(req)
        assert normalized is None
        assert error is not None
        assert error["error"]["code"] == "unsupported_version_pair"


def test_canonical_projection_single_call__v1_rejects_evidence_limit():
    req = {
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
        "evidence_limit": 3,
    }
    normalized, error = validate_request(req)
    assert normalized is None
    assert error is not None
    assert error["error"]["code"] == "invalid_request"
    assert "evidence_limit" in error["error"]["details"]["unknown_fields"]


def test_canonical_projection_single_call__unknown_request_keys_still_fail():
    req = {
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
        "bogus_key": "unexpected",
    }
    normalized, error = validate_request(req)
    assert normalized is None
    assert error is not None
    assert error["error"]["code"] == "invalid_request"
    assert "bogus_key" in error["error"]["details"]["unknown_fields"]


@pytest.mark.parametrize("root_name", ["modules", "artifacts", "dependencies"])
def test_canonical_projection_single_call__all_three_roots_validate_without_describe(root_name):
    req = {
        "root": root_name,
        "filters": [],
        "select": [],
    }
    normalized, error = validate_request(req)
    assert error is None
    assert normalized is not None
    assert normalized["root"] == root_name
    assert normalized["schema_version"] == "1.0"
    assert normalized["language_version"] == "1.0"


def test_canonical_projection_single_call__filter_shape_works_without_version_fields():
    req = {
        "root": "modules",
        "filters": [
            {
                "field": "module_name",
                "operator": "eq",
                "value": "pkg.module",
            }
        ],
        "select": ["module_name"],
    }
    normalized, error = validate_request(req)
    assert error is None
    assert normalized is not None
    assert len(normalized["filters"]) == 1
    assert normalized["filters"][0]["field"] == "module_name"
    assert normalized["filters"][0]["operator"] == "eq"
    assert normalized["filters"][0]["value"] == "pkg.module"


def test_canonical_projection_single_call__execute_projection_reports_defaulted_versions():
    class DummyModule:
        path = "pkg/module.py"

    state = RepositoryAnalysisState(
        modules={"pkg.module": DummyModule()},
        artifacts={"pkg.module": {"own_symbols": ["pkg.module::func"]}},
        module_usages={},
    )
    req = {
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    res = execute_projection(state, req)
    assert res["status"] == "ok"
    assert res["schema_version"] == "1.0"
    assert res["language_version"] == "1.0"
    assert res["total_matches"] == 1
    assert res["results"] == [{"module_name": "pkg.module"}]



def test_canonical_projection_single_call__docs_are_self_sufficient_for_basic_v1():
    doc_path = Path(__file__).resolve().parents[3] / "contextor" / "mcp" / "docs" / "query_canonical_projection.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8"))

    doc_str = json.dumps(doc).lower()
    for keyword in (
        "modules",
        "artifacts",
        "dependencies",
        "filters",
        "field",
        "operator",
        "value",
        "select",
        "1.0",
    ):
        assert keyword in doc_str, f"keyword {keyword} missing from query_canonical_projection docs"


def test_canonical_projection_single_call__describe_is_optional_not_prerequisite():
    query_doc_path = Path(__file__).resolve().parents[3] / "contextor" / "mcp" / "docs" / "query_canonical_projection.json"
    describe_doc_path = Path(__file__).resolve().parents[3] / "contextor" / "mcp" / "docs" / "describe_canonical_state.json"

    query_doc = json.loads(query_doc_path.read_text(encoding="utf-8"))
    describe_doc = json.loads(describe_doc_path.read_text(encoding="utf-8"))

    query_notes = " ".join(query_doc.get("usage_notes", []))
    describe_notes = " ".join(describe_doc.get("usage_notes", []))

    # Must explicitly state basic projections don't require calling describe first
    assert "basic v1.0 projections can be executed directly without calling describe_canonical_state first" in query_notes
    assert "basic v1.0 queries can be composed directly in query_canonical_projection without calling this first" in describe_notes


def test_canonical_projection_single_call__runtime_query_description_is_index_backed_and_self_sufficient():
    from contextor import mcp_server
    from contextor.mcp import documentation

    tool = mcp_server.mcp._tool_manager._tools["query_canonical_projection"]
    index = documentation.load_documentation_index()
    entry = next(
        item for item in index["tools"]
        if item["tool"] == "query_canonical_projection"
    )

    assert tool.description == entry["short_description"]

    description = tool.description.lower()

    for term in (
        "modules",
        "artifacts",
        "dependencies",
        "filters",
        "field",
        "operator",
        "value",
        "select",
        "1.0/1.0",
    ):
        assert term in description

    assert "flat and" in description
    assert "describe_canonical_state only" in description
    assert tool.fn.__doc__ is None


def test_canonical_projection_single_call__runtime_describe_description_is_optional_discovery():
    from contextor import mcp_server
    from contextor.mcp import documentation

    tool = mcp_server.mcp._tool_manager._tools["describe_canonical_state"]
    index = documentation.load_documentation_index()
    entry = next(
        item for item in index["tools"]
        if item["tool"] == "describe_canonical_state"
    )

    assert tool.description == entry["short_description"]

    description = tool.description.lower()

    assert "optional" in description
    assert "basic v1.0" in description
    assert "operators" in description
    assert "limits" in description
    assert "v1.1" in description
    assert tool.fn.__doc__ is None



