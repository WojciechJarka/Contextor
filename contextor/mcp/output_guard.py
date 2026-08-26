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


def largest_fitting_prefix(
    max_count: int,
    build_serialized,
    *,
    min_count: int = 1,
) -> tuple[str, int] | None:
    """
    Return the largest deterministic prefix whose serialized UTF-8 payload
    fits within LARGE_OUTPUT_WARNING_BYTES.

    `build_serialized(count)` must build deterministic prefixes whose
    serialized byte size is monotonically non-decreasing as `count` grows.
    This helper has no JSON or domain semantics; it only measures serialized
    UTF-8 payload size and performs a binary search under that precondition.
    """
    if max_count < min_count:
        return None

    max_candidate = build_serialized(max_count)
    if len(max_candidate.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES:
        return max_candidate, max_count

    min_candidate = build_serialized(min_count)
    if len(min_candidate.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES:
        return None

    low = min_count
    high = max_count - 1
    best_candidate = min_candidate
    best_count = min_count

    while low <= high:
        mid = (low + high) // 2
        candidate = build_serialized(mid)

        if len(candidate.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES:
            best_candidate = candidate
            best_count = mid
            low = mid + 1
        else:
            high = mid - 1

    return best_candidate, best_count
