import json
from pathlib import Path

from contextor.mcp import analysis_jobs


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
    return json.dumps(
        analysis_jobs._start_analysis_job(
            "single_file", root, target_file, exclude_paths=exclude_paths
        ),
        indent=2,
    )
