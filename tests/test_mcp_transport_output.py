import asyncio
import json

from fastmcp.tools.tool import ToolResult

from contextor.mcp_server import mcp, register_mcp_tool


def test_registered_string_tool_emits_content_without_structured_content():
    name = "synthetic_transport_output"

    def synthetic_transport_output() -> str:
        return json.dumps({"status": "synthetic_ok"})

    registered = register_mcp_tool(
        synthetic_transport_output,
        name=name,
        description="Synthetic transport-output regression tool.",
    )
    try:
        assert registered.output_schema is None

        result = asyncio.run(registered.run({}))

        assert isinstance(result, ToolResult)
        assert result.structured_content is None
        assert len(result.content) == 1
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "synthetic_ok"
    finally:
        mcp.remove_tool(name)
