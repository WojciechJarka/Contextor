import json
from pathlib import Path
from typing import Any

from contextor.core.canonical_state_query import execute_projection
from contextor.mcp import runtime as mcp_runtime


def query_canonical_projection(repo_path: str, request: dict[str, Any]) -> str:
    root = Path(repo_path).expanduser().resolve()


    engine = mcp_runtime.get_or_init_engine(root)
    if not engine:
        return json.dumps(
            {
                "status": "error",
                "error": {
                    "code": "canonical_state_unavailable",
                    "message": "No live canonical state is available. Run analyze_project first.",
                    "path": "repo_path",
                    "details": {"repo_path": str(root)},
                },
            },
            indent=2,
        )
    return json.dumps(
        execute_projection(engine.state, request),
        indent=2,
        ensure_ascii=False,
    )
