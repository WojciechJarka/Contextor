import json
from pathlib import Path

from contextor.core.report_query import catalog_from_registry
from contextor.mcp.output_guard import (
    LARGE_OUTPUT_WARNING_BYTES,
    guard_large_output,
    largest_fitting_prefix,
)


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
        result_items = list(result.items())
        serialized_output = json.dumps(result, indent=2)
        full_bytes = len(serialized_output.encode("utf-8"))

        if (
            full_bytes > LARGE_OUTPUT_WARNING_BYTES
            and not allow_large_output
            and len(result_items) > 0
            and "_output" not in result
        ):
            def _build(count: int) -> str:
                prefix_dict = dict(result_items[:count])
                prefix_dict["_output"] = {
                    "auto_bounded": True,
                    "full_output_bytes": full_bytes,
                    "warning_threshold_bytes": LARGE_OUTPUT_WARNING_BYTES,
                    "requested_count": len(ids),
                    "returned_count": count,
                    "retry": {"allow_large_output": True},
                }
                return json.dumps(prefix_dict, indent=2)

            bounded = largest_fitting_prefix(len(result_items), _build, min_count=1)
            if bounded is not None:
                return bounded[0]

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

