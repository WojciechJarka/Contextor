import json
from typing import Any

ALLOWED_REPRESENTATIONS = {"auto", "indexed", "named"}
AUTO_NEGOTIATION_MIN_BYTES_SAVED: int = 512


def is_supported_representation(rep: str) -> bool:
    """Return whether the representation format is supported."""
    return rep in ALLOWED_REPRESENTATIONS


def serialized_json_bytes(payload: Any) -> int:
    """Calculate deterministic byte length of UTF-8 encoded formatted JSON."""
    return len(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))


def representation_size_stats(
    named_candidate: Any,
    indexed_candidate: Any,
) -> dict[str, int | float]:
    """Calculate exact JSON size comparison between named and indexed candidates."""
    named_bytes = serialized_json_bytes(named_candidate)
    indexed_bytes = serialized_json_bytes(indexed_candidate)
    bytes_saved = named_bytes - indexed_bytes
    percent_saved = (
        round((bytes_saved / named_bytes) * 100, 1) if named_bytes > 0 else 0.0
    )
    return {
        "named_bytes": named_bytes,
        "indexed_bytes": indexed_bytes,
        "bytes_saved": bytes_saved,
        "percent_saved": percent_saved,
    }
