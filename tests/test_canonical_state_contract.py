"""Focused tests for the versioned canonical-state projection contract."""

import json
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools import (
    query_canonical_projection as query_canonical_projection_tool,
)
from contextor.core.canonical_state_query import (
    LANGUAGE_VERSION,
    CANONICAL_QUERY_SCHEMA_VERSION,
    describe_contract,
    execute_projection,
    validate_request,
)
from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module

pytestmark = pytest.mark.live


def _request(root, *, filters=None, select=None, limit=None):
    request = {
        "schema_version": CANONICAL_QUERY_SCHEMA_VERSION,
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
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: engine,
    )

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


def test_expression_based_canonical_query_tools_are_not_exposed():
    tool_names = set(mcp_server.mcp._tool_manager._tools)

    assert "query_canonical_state" not in tool_names
    assert "query_canonical_state_bounded" not in tool_names
    assert {"describe_canonical_state", "query_canonical_projection"} <= tool_names


def test_mcp_projection_returns_structured_unavailable_state(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: None,
    )

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


from contextor.core.canonical_state_query.contract import (
    CANONICAL_QUERY_SCHEMA_VERSION_V1_1,
    LANGUAGE_VERSION_V1_1,
    SCHEMA_V1_1,
)


def _request_v1_1(root, *, filters=None, select=None, limit=None, evidence_limit="OMIT"):
    request = {
        "schema_version": CANONICAL_QUERY_SCHEMA_VERSION_V1_1,
        "language_version": LANGUAGE_VERSION_V1_1,
        "root": root,
        "filters": filters or [],
        "select": select or [],
    }
    if limit is not None:
        request["limit"] = limit
    if evidence_limit != "OMIT":
        request["evidence_limit"] = evidence_limit
    return request


def _state_with_high_fanout():
    many_imports = [ImportRef(f"ext.lib{i}", 0, [], False) for i in range(8)]
    modules = {
        "pkg.heavy": Module("pkg.heavy", "pkg/heavy.py", "C:/repo/pkg/heavy.py", many_imports),
        "pkg.empty": Module("pkg.empty", "pkg/empty.py", "C:/repo/pkg/empty.py", []),
    }
    artifacts = {
        "pkg.heavy": {
            "symbols": {
                "classes": ["ManyConsumers", "ZeroConsumers"],
                "functions": ["UnavailableSymbol"],
                "methods": [],
                "globals": [],
                "signatures": {"ManyConsumers": "class ManyConsumers", "ZeroConsumers": "class ZeroConsumers"},
            },
            "own_symbols": ["ManyConsumers", "ZeroConsumers", "UnavailableSymbol"],
            "consumers": {
                "ManyConsumers": {
                    "consumers": [f"consumer.mod{i}" for i in range(7)],
                    "consumer_count": {"total": 7},
                },
                "ZeroConsumers": {
                    "consumers": [],
                    "consumer_count": {"total": 0},
                },
            },
        }
    }
    graph = SimpleNamespace(
        hard_edges={"pkg.heavy": {"pkg.empty"}},
        soft_edges={},
    )
    return SimpleNamespace(modules=modules, artifacts=artifacts, dependency_graph=graph)


def test_version_1_0_rejects_evidence_limit():
    req = _request("modules", select=["module_name"])
    req["evidence_limit"] = 3
    _, err = validate_request(req)

    assert err is not None
    assert err["error"]["code"] == "invalid_request"


def test_cross_version_pairs_fail_unsupported_version_pair():
    pair1 = {
        "schema_version": "1.0",
        "language_version": "1.1",
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    pair2 = {
        "schema_version": "1.1",
        "language_version": "1.0",
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    _, err1 = validate_request(pair1)
    _, err2 = validate_request(pair2)

    assert err1["error"]["code"] == "unsupported_version_pair"
    assert err1["error"]["path"] == "$request"
    assert err2["error"]["code"] == "unsupported_version_pair"
    assert err2["error"]["path"] == "$request"


def test_unsupported_schema_and_language_version_error_classes():
    # 1. Unsupported schema with supported or unsupported language
    for schema_ver, lang_ver in [("9.9", "1.0"), ("9.9", "1.1"), ("9.9", "9.9")]:
        _, err = validate_request({
            "schema_version": schema_ver,
            "language_version": lang_ver,
            "root": "modules",
            "filters": [],
            "select": ["module_name"],
        })
        assert err is not None
        assert err["error"]["code"] == "unsupported_schema_version", f"Failed for {schema_ver}, {lang_ver}"
        assert err["error"]["path"] == "schema_version"
        assert set(err["error"]["details"]["supported_versions"]) == {"1.0", "1.1"}

    # 2. Supported schema with unsupported language
    for schema_ver, lang_ver in [("1.0", "9.9"), ("1.1", "9.9")]:
        _, err = validate_request({
            "schema_version": schema_ver,
            "language_version": lang_ver,
            "root": "modules",
            "filters": [],
            "select": ["module_name"],
        })
        assert err is not None
        assert err["error"]["code"] == "unsupported_language_version", f"Failed for {schema_ver}, {lang_ver}"
        assert err["error"]["path"] == "language_version"
        assert set(err["error"]["details"]["supported_versions"]) == {"1.0", "1.1"}


def test_version_1_1_defaults_to_cap3_evidence_and_emits_expand():
    state = _state_with_high_fanout()
    result = execute_projection(
        state,
        _request_v1_1("modules", filters=[{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}], select=["module_name", "import_count", "imports"]),
    )

    assert result["status"] == "ok"
    assert result["schema_version"] == "1.1"
    assert result["language_version"] == "1.1"
    row = result["results"][0]
    assert row["import_count"] == 8
    assert len(row["imports"]) == 3
    assert row["imports_truncated"] is True
    assert "expand" in result
    assert result["expand"]["available"] is True
    assert result["expand"]["retry_with_full_evidence"]["evidence_limit"] is None
    assert result["expand"]["retry_with_full_evidence"]["schema_version"] == "1.1"
    assert result["expand"]["retry_with_full_evidence"]["language_version"] == "1.1"


def test_version_1_1_evidence_limit_explicit_none_gives_lossless():
    state = _state_with_high_fanout()
    result = execute_projection(
        state,
        _request_v1_1(
            "modules",
            filters=[{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}],
            select=["module_name", "import_count", "imports"],
            evidence_limit=None,
        ),
    )

    assert result["status"] == "ok"
    row = result["results"][0]
    assert row["import_count"] == 8
    assert len(row["imports"]) == 8
    assert row["imports_truncated"] is False
    assert "expand" not in result


def test_version_1_1_evidence_limit_zero_gives_empty_nested_list():
    state = _state_with_high_fanout()
    result = execute_projection(
        state,
        _request_v1_1(
            "modules",
            filters=[{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}],
            select=["module_name", "import_count", "imports"],
            evidence_limit=0,
        ),
    )

    assert result["status"] == "ok"
    row = result["results"][0]
    assert row["import_count"] == 8
    assert row["imports"] == []
    assert row["imports_truncated"] is True
    assert "expand" in result


def test_version_1_1_evidence_limit_positive_n():
    state = _state_with_high_fanout()
    result = execute_projection(
        state,
        _request_v1_1(
            "modules",
            filters=[{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}],
            select=["module_name", "import_count", "imports"],
            evidence_limit=5,
        ),
    )

    assert result["status"] == "ok"
    row = result["results"][0]
    assert row["import_count"] == 8
    assert len(row["imports"]) == 5
    assert row["imports_truncated"] is True


def test_version_1_1_invalid_evidence_limit_fails_closed():
    for bad_val in (-1, -10, True, False, 3.5, "three", [3]):
        _, err = validate_request(_request_v1_1("modules", select=["module_name"], evidence_limit=bad_val))
        assert err is not None, f"Expected error for {bad_val}"
        assert err["error"]["code"] == "invalid_evidence_limit"


def test_version_1_1_artifact_consumers_null_zero_and_cap_semantics():
    state = _state_with_high_fanout()

    # 1. Unavailable symbol
    res_unavail = execute_projection(
        state,
        _request_v1_1(
            "artifacts",
            filters=[{"field": "artifact_name", "operator": "eq", "value": "UnavailableSymbol"}],
            select=["artifact_name", "consumer_data_available", "consumer_count", "consumers"],
        ),
    )
    row_unavail = res_unavail["results"][0]
    assert row_unavail["consumer_data_available"] is False
    assert row_unavail["consumer_count"] is None
    assert row_unavail["consumers"] is None
    assert row_unavail["consumers_truncated"] is None
    assert "expand" not in res_unavail

    # 2. Zero consumers
    res_zero = execute_projection(
        state,
        _request_v1_1(
            "artifacts",
            filters=[{"field": "artifact_name", "operator": "eq", "value": "ZeroConsumers"}],
            select=["artifact_name", "consumer_data_available", "consumer_count", "consumers"],
        ),
    )
    row_zero = res_zero["results"][0]
    assert row_zero["consumer_data_available"] is True
    assert row_zero["consumer_count"] == 0
    assert row_zero["consumers"] == []
    assert row_zero["consumers_truncated"] is False
    assert "expand" not in res_zero

    # 3. High fanout (7 consumers, default cap3)
    res_cap = execute_projection(
        state,
        _request_v1_1(
            "artifacts",
            filters=[{"field": "artifact_name", "operator": "eq", "value": "ManyConsumers"}],
            select=["artifact_name", "consumer_data_available", "consumer_count", "consumers"],
        ),
    )
    row_cap = res_cap["results"][0]
    assert row_cap["consumer_data_available"] is True
    assert row_cap["consumer_count"] == 7
    assert len(row_cap["consumers"]) == 3
    assert row_cap["consumers_truncated"] is True
    assert "expand" in res_cap


def test_version_1_1_narrow_select_emits_no_companion_metadata():
    state = _state_with_high_fanout()
    res_mod = execute_projection(
        state,
        _request_v1_1("modules", filters=[{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}], select=["module_name", "import_count"]),
    )
    row_mod = res_mod["results"][0]
    assert set(row_mod.keys()) == {"module_name", "import_count"}
    assert "imports_truncated" not in row_mod
    assert "expand" not in res_mod

    res_art = execute_projection(
        state,
        _request_v1_1("artifacts", filters=[{"field": "artifact_name", "operator": "eq", "value": "ManyConsumers"}], select=["artifact_name", "consumer_count"]),
    )
    row_art = res_art["results"][0]
    assert set(row_art.keys()) == {"artifact_name", "consumer_count"}
    assert "consumers_truncated" not in row_art
    assert "expand" not in res_art


def test_version_1_1_companion_fields_are_not_independently_selectable():
    _, err_mod = validate_request(_request_v1_1("modules", select=["module_name", "imports_truncated"]))
    assert err_mod["error"]["code"] == "field_not_selectable"

    _, err_art = validate_request(_request_v1_1("artifacts", select=["artifact_name", "consumers_truncated"]))
    assert err_art["error"]["code"] == "field_not_selectable"


def test_version_1_1_expand_descriptor_execution_returns_lossless_scope():
    state = _state_with_high_fanout()
    initial = execute_projection(
        state,
        _request_v1_1("modules", filters=[{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}], select=["module_name", "imports"]),
    )
    assert "expand" in initial

    retry_request = initial["expand"]["retry_with_full_evidence"]
    retried = execute_projection(state, retry_request)

    assert retried["status"] == "ok"
    assert retried["results"][0]["imports_truncated"] is False
    assert len(retried["results"][0]["imports"]) == 8
    assert "expand" not in retried


def test_version_1_1_dependencies_domain_records_unaffected():
    state = _state_with_high_fanout()
    res = execute_projection(
        state,
        _request_v1_1("dependencies", select=["source", "target", "edge_type"]),
    )

    assert res["status"] == "ok"
    assert res["schema_version"] == "1.1"
    assert res["language_version"] == "1.1"
    assert res["results"] == [{"source": "pkg.heavy", "target": "pkg.empty", "edge_type": "hard"}]
    assert "expand" not in res


def test_describe_contract_version_1_1_formal_declarations():
    res_default = describe_contract()
    assert res_default["schema_version"] == "1.0"
    assert res_default["language_version"] == "1.0"

    res_1_1 = describe_contract("1.1", "1.1")
    assert res_1_1["schema_version"] == "1.1"
    assert res_1_1["language_version"] == "1.1"
    assert res_1_1["schema"]["roots"]["modules"]["fields"]["imports_truncated"]["selectable"] is False
    assert res_1_1["schema"]["roots"]["artifacts"]["fields"]["consumers_truncated"]["selectable"] is False


def test_legacy_validation_precedence_rejects_unsupported_field_before_missing_required():
    malformed = {
        "unsupported_field": 123,
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
    }
    _, err = validate_request(malformed)

    assert err is not None
    assert err["error"]["code"] == "invalid_request"
    assert err["error"]["path"] == "unsupported_field"
    assert err["error"]["details"]["unknown_fields"] == ["unsupported_field"]


def test_legacy_evidence_limit_precedence_before_other_defects():
    malformed = {
        "schema_version": "1.0",
        "language_version": "1.0",
        "root": "modules",
        "filters": [{"field": "module_name", "operator": "bad_op", "value": "x"}],
        "select": ["module_name"],
        "evidence_limit": 3,
    }
    _, err = validate_request(malformed)

    assert err is not None
    assert err["error"]["code"] == "invalid_request"
    assert err["error"]["path"] == "evidence_limit"
    assert err["error"]["details"]["unknown_fields"] == ["evidence_limit"]


def test_legacy_evidence_limit_precedence_with_missing_schema_version():
    malformed = {
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
        "evidence_limit": 3,
    }
    _, err = validate_request(malformed)

    assert err is not None
    assert err["error"]["code"] == "invalid_request"
    assert err["error"]["path"] == "evidence_limit"
    assert err["error"]["details"]["unknown_fields"] == ["evidence_limit"]


def test_public_describe_canonical_state_version_discovery():
    from contextor.mcp.tools.describe_canonical_state import describe_canonical_state

    # 1. Default call returns 1.0 contract
    raw_default = describe_canonical_state()
    parsed_default = json.loads(raw_default)
    assert parsed_default["schema_version"] == "1.0"
    assert parsed_default["language_version"] == "1.0"
    assert "imports_truncated" not in parsed_default["schema"]["roots"]["modules"]["fields"]

    # 2. Explicit 1.1 call returns 1.1 contract
    raw_1_1 = describe_canonical_state(schema_version="1.1", language_version="1.1")
    parsed_1_1 = json.loads(raw_1_1)
    assert parsed_1_1["schema_version"] == "1.1"
    assert parsed_1_1["language_version"] == "1.1"
    assert "imports_truncated" in parsed_1_1["schema"]["roots"]["modules"]["fields"]
    assert "consumers_truncated" in parsed_1_1["schema"]["roots"]["artifacts"]["fields"]
    assert parsed_1_1["schema"]["roots"]["modules"]["fields"]["imports_truncated"]["selectable"] is False

    # 3. Cross pair returns structured error
    raw_cross = describe_canonical_state(schema_version="1.0", language_version="1.1")
    parsed_cross = json.loads(raw_cross)
    assert parsed_cross["status"] == "error"
    assert parsed_cross["error"]["code"] == "unsupported_version_pair"

    # 4. Unsupported version returns structured error
    raw_unsupported = describe_canonical_state(schema_version="2.0", language_version="2.0")
    parsed_unsupported = json.loads(raw_unsupported)
    assert parsed_unsupported["status"] == "error"
    assert parsed_unsupported["error"]["code"] == "unsupported_version_pair"


def test_version_1_1_expand_exact_request_preservation():
    state = _state_with_high_fanout()

    # Case A: Omitted limit and omitted evidence_limit
    orig_req_a = {
        "schema_version": "1.1",
        "language_version": "1.1",
        "root": "modules",
        "filters": [{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}],
        "select": ["module_name", "imports"],
    }
    copy_a = dict(orig_req_a)
    res_a = execute_projection(state, orig_req_a)
    assert "expand" in res_a
    retry_a = res_a["expand"]["retry_with_full_evidence"]
    assert "limit" not in retry_a
    assert retry_a == {
        "schema_version": "1.1",
        "language_version": "1.1",
        "root": "modules",
        "filters": [{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}],
        "select": ["module_name", "imports"],
        "evidence_limit": None,
    }
    assert orig_req_a == copy_a, "Original request dict must not be mutated"

    # Case B: Explicit limit and explicit evidence_limit
    orig_req_b = {
        "schema_version": "1.1",
        "language_version": "1.1",
        "root": "modules",
        "filters": [{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}],
        "select": ["module_name", "imports"],
        "limit": 5,
        "evidence_limit": 2,
    }
    copy_b = dict(orig_req_b)
    res_b = execute_projection(state, orig_req_b)
    assert "expand" in res_b
    retry_b = res_b["expand"]["retry_with_full_evidence"]
    assert retry_b == {
        "schema_version": "1.1",
        "language_version": "1.1",
        "root": "modules",
        "filters": [{"field": "module_name", "operator": "eq", "value": "pkg.heavy"}],
        "select": ["module_name", "imports"],
        "limit": 5,
        "evidence_limit": None,
    }
    assert orig_req_b == copy_b, "Original request dict must not be mutated"


def test_v1_1_evidence_limit_requires_explicit_supported_version_pair_before_envelope_expansion():
    missing_schema = {
        "language_version": "1.1",
        "root": "modules",
        "filters": [],
        "select": [],
        "evidence_limit": 3,
    }
    _, err_missing_schema = validate_request(missing_schema)
    assert err_missing_schema is not None
    assert err_missing_schema["error"]["code"] == "invalid_request"
    assert err_missing_schema["error"]["path"] == "evidence_limit"
    assert err_missing_schema["error"]["details"]["unknown_fields"] == [
        "evidence_limit"
    ]
    missing_language = {
        "schema_version": "1.1",
        "root": "modules",
        "filters": [],
        "select": [],
        "evidence_limit": 3,
    }
    _, err_missing_language = validate_request(missing_language)
    assert err_missing_language is not None
    assert err_missing_language["error"]["code"] == "invalid_request"
    assert err_missing_language["error"]["path"] == "evidence_limit"
    assert err_missing_language["error"]["details"]["unknown_fields"] == [
        "evidence_limit"
    ]
    valid_v1_1 = {
        "schema_version": "1.1",
        "language_version": "1.1",
        "root": "modules",
        "filters": [],
        "select": ["module_name"],
        "evidence_limit": 3,
    }
    normalized, valid_error = validate_request(valid_v1_1)
    assert valid_error is None
    assert normalized is not None
    assert normalized["evidence_limit"] == 3
    unknown_v1_1 = {
        **valid_v1_1,
        "unsupported_field": True,
    }
    _, unknown_error = validate_request(unknown_v1_1)
    assert unknown_error is not None
    assert unknown_error["error"]["code"] == "invalid_request"
    assert unknown_error["error"]["path"] == "unsupported_field"



