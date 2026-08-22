import json
from pathlib import Path

from contextor.core.report_query import catalog_from_registry
from contextor.mcp.output_guard import guard_large_output


def lookup_index_entries(
    repo_path: str, ids: list[str], allow_large_output: bool = False
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        catalog = catalog_from_registry(str(root))
        result = {}
        for id_ in ids:
            normalized_id = str(id_)
            if normalized_id.upper().startswith("A"):
                normalized_id = normalized_id.upper()
                active = catalog.artifacts
                recovery = catalog.recovered_artifacts or {}
            else:
                active = catalog.modules
                recovery = catalog.recovered_modules or {}
            if normalized_id in active:
                entry = {"name": active[normalized_id], "status": "active"}
            elif normalized_id in recovery:
                entry = {"name": recovery[normalized_id], "status": "recovery"}
            else:
                entry = {"name": None, "status": "missing"}
            result[str(id_)] = entry
        serialized_output = json.dumps(result, indent=2)
        return guard_large_output(
            serialized_output,
            allow_large_output=allow_large_output,
            requested_count=len(ids),
            reason="Estimated lookup output exceeds the recommended context size.",
            retry_instruction=(
                "Repeat the same lookup_index_entries call with the same repo_path and ids and set allow_large_output=true."
            ),
        )
    except Exception as e:
        return f"Error resolving index entries: {e}"

