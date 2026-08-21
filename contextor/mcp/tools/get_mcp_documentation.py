import json

from contextor.mcp.documentation import query_documentation


def get_mcp_documentation(
    tool: str | None = None,
    tools: list[str] | None = None,
    sections: list[str] | None = None,
) -> str:
    return json.dumps(
        query_documentation(tool=tool, tools=tools, sections=sections),
        ensure_ascii=False,
        indent=2,
    )

