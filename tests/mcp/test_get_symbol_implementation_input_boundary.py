import asyncio
import json

import mcp.types as mcp_types
import pytest
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import MiddlewareContext
from fastmcp.tools.tool import ToolResult
from pydantic_core import ValidationError as PydanticCoreValidationError

from contextor import mcp_server


def _call_get_symbol_implementation(arguments):
    result = asyncio.run(
        mcp_server.mcp._mcp_call_tool(
            "get_symbol_implementation",
            arguments,
        )
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], mcp_types.TextContent)

    return json.loads(result[0].text)


def _assert_documentation_boundary_response(
    result,
    *,
    parameter,
):
    assert result["tool"] == "get_symbol_implementation"
    assert result["version"] == "1.0.0"
    assert "parameters" in result
    assert "behavior" in result
    assert "usage_notes" in result
    assert (
        result["parameter_contract_error"]["parameter"]
        == parameter
    )
    assert (
        "Do not repeat the same invalid call."
        in result[
            "parameter_contract_error"
        ]["retry_instruction"]
    )


def test_unknown_argument_name_returns_full_documentation_before_fastmcp_validation():
    result = _call_get_symbol_implementation(
        {
            "repo_path": "unused",
            "symbol": "anything",
            "output": "full",
        }
    )

    _assert_documentation_boundary_response(
        result,
        parameter="unknown_argument",
    )

    assert (
        result["parameter_contract_error"][
            "invalid_value"
        ]
        == ["output"]
    )


def test_unknown_argument_typo_returns_bounded_parameter_name_candidate():
    result = _call_get_symbol_implementation(
        {
            "repo_path": "unused",
            "symbol": "anything",
            "file_paht": "pkg/a.py",
        }
    )

    _assert_documentation_boundary_response(
        result,
        parameter="unknown_argument",
    )

    candidates = result[
        "parameter_contract_error"
    ]["similar_candidates"]["file_paht"]

    assert 1 <= len(candidates) <= 5
    assert candidates[0]["value"] == "file_path"
    assert candidates[0]["score"] >= 0.75


def test_missing_required_argument_returns_full_documentation_before_fastmcp_validation():
    result = _call_get_symbol_implementation(
        {
            "repo_path": "unused",
        }
    )

    _assert_documentation_boundary_response(
        result,
        parameter="missing_required_argument",
    )

    assert (
        result["parameter_contract_error"][
            "invalid_value"
        ]
        == ["symbol"]
    )


def test_fastmcp_type_validation_failure_returns_full_documentation():
    result = _call_get_symbol_implementation(
        {
            "repo_path": ".",
            "symbol": "anything",
            "member_limit": {
                "not": "an integer",
            },
        }
    )

    _assert_documentation_boundary_response(
        result,
        parameter="member_limit",
    )


def test_boundary_middleware_does_not_intercept_other_tools():
    middleware = (
        mcp_server
        ._GetSymbolImplementationInputBoundaryMiddleware()
    )
    calls = []

    async def call_next(context):
        calls.append(context)
        return ToolResult(content="PASSTHROUGH")

    context = MiddlewareContext(
        message=mcp_types.CallToolRequestParams(
            name="other_tool",
            arguments={
                "invented": "value",
            },
        ),
        source="client",
        type="request",
        method="tools/call",
    )

    result = asyncio.run(
        middleware.on_call_tool(
            context,
            call_next,
        )
    )

    assert calls == [context]
    assert result.content[0].text == "PASSTHROUGH"


def test_boundary_reraises_tool_error_without_pydantic_cause():
    middleware = (
        mcp_server
        ._GetSymbolImplementationInputBoundaryMiddleware()
    )

    async def call_next(context):
        raise ToolError("internal failure")

    context = MiddlewareContext(
        message=mcp_types.CallToolRequestParams(
            name="get_symbol_implementation",
            arguments={
                "repo_path": ".",
                "symbol": "anything",
            },
        ),
        source="client",
        type="request",
        method="tools/call",
    )

    with pytest.raises(
        ToolError,
        match="internal failure",
    ):
        asyncio.run(
            middleware.on_call_tool(
                context,
                call_next,
            )
        )


def test_validation_parameter_helper_rejects_non_public_location():
    class FakeValidationError:
        def errors(self):
            return [
                {
                    "loc": (
                        "internal_field",
                    )
                }
            ]

    assert (
        mcp_server
        ._get_symbol_implementation_validation_parameters(
            FakeValidationError()
        )
        is None
    )
