import json
from typing import Any

LARGE_OUTPUT_WARNING_BYTES = 15 * 1024


def guard_large_output(
    serialized_output: str,
    *,
    allow_large_output: bool,
    retry_instruction: str,
    requested_count: int | None = None,
    reason: str = "Estimated output exceeds the recommended context size.",
) -> str:
    estimated_output_bytes = len(serialized_output.encode("utf-8"))
    if estimated_output_bytes <= LARGE_OUTPUT_WARNING_BYTES or allow_large_output:
        return serialized_output

    warning_response: dict[str, Any] = {
        "status": "confirmation_required",
        "reason": reason,
    }
    if requested_count is not None:
        warning_response["requested_count"] = requested_count

    warning_response.update(
        {
            "estimated_output_bytes": estimated_output_bytes,
            "estimated_output_kib": estimated_output_bytes / 1024,
            "warning_threshold_bytes": LARGE_OUTPUT_WARNING_BYTES,
            "warning_threshold_kib": 15.0,
            "retry": {
                "allow_large_output": True,
            },
            "retry_instruction": retry_instruction,
        }
    )
    return json.dumps(warning_response, indent=2)
