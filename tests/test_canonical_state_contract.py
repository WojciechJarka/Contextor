"""Focused tests for the versioned canonical-state projection contract."""

import json
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.core.canonical_state_query import (
    LANGUAGE_VERSION,
    SCHEMA_VERSION,
    describe_contract,
    execute_projection,
    validate_request,
)
from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module

pytestmark = pytest.mark.live


def _request(root, *, filters=None, select=None, limit=None):
    request = {
        "schema_version": SCHEMA_VERSION,
        "language_version": LANGUAGE_VERSION,
        "root": root,
        "filters": filters or [],
        "select": select or [],
    }
    if limit is not None:
        request["limit"] = limit
    return request


def _state():
    modules = {
        "pkg.empty": Module("pkg.empty", "pkg/empty.py", "C:/repo/pkg/empty.py", []),
        "pkg.used": Module(
            "pkg.used",
            "pkg/used.py",
            "C:/repo/pkg/used.py",
            [ImportRef("os", 0, [], False)],
        ),
    }
    artifacts = {
        "pkg.used": {
            "symbols": {
                "classes": [],
                "functions": ["known", "unknown"],
                "methods": [],
                "globals": ["collision"],
                "signatures": {"known": "def known()", "unknown": "", "collision": ""},
            },
            "own_symbols": ["unknown", "known", "collision"],
            "consumers": {
                "known": {
                    "consumers": [],
                    "consumer_count": {"total": 0},
                },
                "collision": {
                    "consumers": ["pkg.empty"],
                    "consumer_count": {"total": 1},
                },
            },
        }
    }
    graph = SimpleNamespace(
        hard_edges={"pkg.used": {"pkg.empty"}},
        soft_edges={"pkg.used": {"pkg.empty", "pkg.symbol.call"}},
    )
    return SimpleNamespace(modules=modules, artifacts=artifacts, dependency_graph=graph)


def test_describe_contract_is_the_single_versioned_source_of_truth():
    result = describe_contract()

    assert result["schema_version"] == "1.0"
    assert result["language_version"] == "1.0"
    assert set(result["schema"]["roots"]) == {"modules", "artifacts", "dependencies"}
    consumers = result["schema"]["roots"]["artifacts"]["fields"]["consumers"]
    assert consumers["nullable"] is True
    assert "is_null" in consumers["allowed_operators"]


def test_modules_projection_is_canonical_bounded_and_excludes_absolute_path():
    result = execute_projection(
        _state(),
        _request("modules", filters=[], select=["module_name", "import_count"], limit=1),
    )

    assert result["status"] == "ok"
    assert result["total_matches"] == 2
    assert result["returned"] == 1
    assert result["truncated"] is True
    assert result["results"] == [{"module_name": "pkg.empty", "import_count": 0}]
    assert "absolute_path" not in result["results"][0]


def test_artifact_projection_preserves_unknown_consumer_state_and_null_rules():
    unknown = execute_projection(
        _state(),
        _request(
            "artifacts",
            filters=[{"field": "consumer_count", "operator": "is_null"}],
            select=["artifact_name", "consumer_data_available", "consumer_count", "consumers", "signature"],
        ),
    )
    zero = execute_projection(
        _state(),
        _request(
            "artifacts",
            filters=[{"field": "consumer_count", "operator": "eq", "value": 0}],
            select=["artifact_name", "consumer_count"],
        ),
    )
    empty_consumers = execute_projection(
        _state(),
        _request(
            "artifacts",
            filters=[{"field": "consumers", "operator": "is_empty"}],
            select=["artifact_name"],
        ),
    )

    assert unknown["results"] == [{
        "artifact_name": "unknown",
        "consumer_data_available": False,
        "consumer_count": None,
        "consumers": None,
        "signature": None,
    }]
    assert zero["results"] == [{"artifact_name": "known", "consumer_count": 0}]
    assert empty_consumers["results"] == [{"artifact_name": "known"}]


def test_dependencies_keep_hard_and_soft_records_for_the_same_pair():
    result = execute_projection(
        _state(),
        _request(
            "dependencies",
            filters=[{"field": "target", "operator": "eq", "value": "pkg.empty"}],
            select=["source", "target", "edge_type"],
        ),
    )

    assert result["results"] == [
        {"source": "pkg.used", "target": "pkg.empty", "edge_type": "hard"},
        {"source": "pkg.used", "target": "pkg.empty", "edge_type": "soft"},
    ]


def test_validation_returns_first_deterministic_structural_error():
    _, missing = validate_request({})
    _, bad_null = validate_request(
        _request(
            "modules",
            filters=[{"field": "path", "operator": "is_null"}],
            select=["path"],
        )
    )
    _, bad_limit = validate_request(_request("modules", limit=True))

    assert missing["error"]["code"] == "missing_required_field"
    assert missing["error"]["path"] == "schema_version"
    assert bad_null["error"]["code"] == "is_null_on_non_nullable"
    assert bad_limit["error"]["code"] == "invalid_limit"


def test_validation_rejects_duplicate_and_wrong_typed_in_values():
    _, duplicate = validate_request(
        _request(
            "modules",
            filters=[{"field": "import_count", "operator": "in", "value": [1, 1]}],
            select=["module_name"],
        )
    )
    _, boolean = validate_request(
        _request(
            "modules",
            filters=[{"field": "import_count", "operator": "eq", "value": True}],
            select=["module_name"],
        )
    )

    assert duplicate["error"]["code"] == "invalid_filter"
    assert boolean["error"]["code"] == "operator_value_mismatch"


def test_mcp_describe_and_query_tools_share_the_contract(tmp_path, monkeypatch):
    engine = SimpleNamespace(state=_state())
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)

    described = json.loads(mcp_server.describe_canonical_state.fn())
    queried = json.loads(
        mcp_server.query_canonical_projection.fn(
            str(tmp_path),
            _request(
                "modules",
                filters=[{"field": "import_count", "operator": "gt", "value": 0}],
                select=["module_name", "import_count"],
            ),
        )
    )

    assert described["schema_version"] == queried["schema_version"] == "1.0"
    assert described["language_version"] == queried["language_version"] == "1.0"
    assert queried["results"] == [{"module_name": "pkg.used", "import_count": 1}]


def test_mcp_projection_returns_structured_unavailable_state(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)

    result = json.loads(
        mcp_server.query_canonical_projection.fn(
            str(tmp_path), _request("modules")
        )
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "canonical_state_unavailable"


def test_projection_rejects_traversal_and_expression_shaped_input():
    traversal = _request("modules.__class__", select=["module_name"])
    expression = _request(
        "modules",
        filters=[{
            "field": "__class__",
            "operator": "eq",
            "value": "__import__('os').getcwd()",
        }],
        select=["module_name"],
    )

    traversal_result = execute_projection(_state(), traversal)
    expression_result = execute_projection(_state(), expression)

    assert traversal_result["error"]["code"] == "unknown_root"
    assert expression_result["error"]["code"] == "unknown_field"


def test_projection_rejects_malformed_nested_values_without_python_exception():
    malformed_select = _request("modules", select=[{"field": "module_name"}])
    malformed_operator = _request(
        "modules",
        filters=[{"field": "path", "operator": ["eq"], "value": "x"}],
        select=["path"],
    )

    select_result = execute_projection(_state(), malformed_select)
    operator_result = execute_projection(_state(), malformed_operator)

    assert select_result["status"] == "error"
    assert select_result["error"]["path"] == "select[0]"
    assert operator_result["status"] == "error"
    assert operator_result["error"]["code"] == "invalid_operator_for_type"


def test_projection_enforces_hard_request_and_result_limits():
    too_large = _request(
        "modules",
        filters=[{"field": "path", "operator": "contains", "value": "x" * 17000}],
        select=["path"],
    )
    over_limit = _request("modules", select=["path"])
    over_limit["limit"] = 201

    large_result = execute_projection(_state(), too_large)
    limit_result = execute_projection(_state(), over_limit)

    assert large_result["error"]["code"] == "request_too_complex"
    assert limit_result["error"]["code"] == "invalid_limit"


def test_empty_select_returns_all_public_fields_but_never_absolute_path():
    result = execute_projection(_state(), _request("modules", select=[], limit=1))

    assert set(result["results"][0]) == {
        "module_name",
        "module_id",
        "path",
        "import_count",
        "imports",
    }
