"""Historical summary-report read probe."""

import json
from pathlib import Path

from contextor.core.paths import output_dir

PRESETS = ("resolve_path", "read_bytes", "json_decode")


def run_scope(root: Path, recorder) -> dict[str, object]:
    with recorder.span("resolve_path"):
        base = output_dir().resolve()
        path = base / f"{root.name}_summary.json"
        if path.name != f"{root.name}_summary.json" or path.resolve().parent != base or not path.is_file():
            return {"status": "unavailable", "reason": "summary_report_unavailable"}
    try:
        with recorder.span("read_bytes"):
            content = path.read_bytes()
    except OSError:
        return {"status": "unavailable", "reason": "summary_report_unavailable"}
    try:
        with recorder.span("json_decode"):
            parsed = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return {"status": "invalid_data", "reason": "invalid_summary_json"}
    return {
        "status": "ok",
        "bytes_read": len(content),
        "json_root_type": type(parsed).__name__,
        "data_source": "historical_report",
        "live_binding_verified": False,
    }
