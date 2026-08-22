import json
from pathlib import Path

from contextor.core.report_query import catalog_from_registry


LARGE_OUTPUT_WARNING_BYTES = 15 * 1024


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
        estimated_output_bytes = len(serialized_output.encode("utf-8"))

        if estimated_output_bytes > LARGE_OUTPUT_WARNING_BYTES and not allow_large_output:
            warning_response = {
                "status": "confirmation_required",
                "reason": "Estimated lookup output exceeds the recommended context size.",
                "requested_count": len(ids),
                "estimated_output_bytes": estimated_output_bytes,
                "estimated_output_kib": estimated_output_bytes / 1024,
                "warning_threshold_bytes": LARGE_OUTPUT_WARNING_BYTES,
                "warning_threshold_kib": 15.0,
                "retry": {
                    "allow_large_output": True,
                },
                "retry_instruction": (
                    "Repeat the same lookup_index_entries call with the same repo_path and ids and set allow_large_output=true."
                ),
            }
            return json.dumps(warning_response, indent=2)

        return serialized_output
    except Exception as e:
        return f"Error resolving index entries: {e}"

