import json
from pathlib import Path

from contextor.mcp import analysis_jobs
from contextor.mcp.runtime import publish_live_status


async def analyze_layer(
    repo_path: str,
    layer_name: str,
    exclude_paths: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    layer = root / layer_name
    if not layer.is_dir():
        return f"Error: Layer path '{layer}' does not exist."
    publish_live_status(root, f"MCP: analyzing layer {layer_name}")
    return json.dumps(
        analysis_jobs._start_analysis_job(
            "layer", root, layer, exclude_paths=exclude_paths
        ),
        indent=2,
    )
