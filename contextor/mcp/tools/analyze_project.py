import json
from pathlib import Path

from contextor.mcp import analysis_jobs
from contextor.mcp.runtime import publish_live_status


async def analyze_project(
    repo_path: str, exclude_paths: list[str] | None = None
) -> str:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    publish_live_status(root, "MCP: analyzing full repository")
    return json.dumps(
        analysis_jobs._start_analysis_job(
            "project", root, exclude_paths=exclude_paths
        ),
        indent=2,
    )
