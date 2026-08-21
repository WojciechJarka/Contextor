import json
from pathlib import Path

from contextor.mcp import analysis_jobs
from contextor.mcp.runtime import publish_live_status


async def analyze_single_file(
    repo_path: str,
    file_path: str,
    exclude_paths: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    target_file = Path(file_path).expanduser()
    if not target_file.is_absolute():
        target_file = root / target_file
    target_file = target_file.resolve()
    if not target_file.is_file():
        return f"Error: Target file '{target_file}' does not exist."
    publish_live_status(root, f"MCP: analyzing file {target_file.name}")
    return json.dumps(
        analysis_jobs._start_analysis_job(
            "single_file", root, target_file, exclude_paths=exclude_paths
        ),
        indent=2,
    )
