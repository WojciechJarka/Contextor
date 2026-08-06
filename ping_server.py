from fastmcp import FastMCP

mcp = FastMCP("PingServer")


@mcp.tool()
def ping() -> str:
    return "pong"


if __name__ == "__main__":
    mcp.run(transport="stdio")