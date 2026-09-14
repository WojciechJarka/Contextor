import asyncio
import json
from pathlib import Path

from contextor.core.analysis.profile_runner import run_analysis_profile


async def contextor_profile_analysis(repo_path: str, exclude_paths: list[str] | None = None) -> str:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    profile = await asyncio.to_thread(run_analysis_profile, root, exclude_paths=exclude_paths)
    return json.dumps(profile, indent=2)
