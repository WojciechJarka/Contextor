"""Small, fail-closed diagnostics projections for MCP responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES, guard_large_output


def _availability(state: Any, family: str, values: Any) -> str:
    status = getattr(state, f"{family}_state", None)
    if values is None and status == "fresh":
        return "unavailable"
    if status in {"fresh", "stale", "deferred", "unavailable"}:
        return status
    if values is None:
        return "unavailable"
    return "fresh"


def diagnostics_summary_for_state(state: Any) -> dict[str, Any]:
    """Return counts plus freshness, never converting unavailable to zero."""
    if state is None:
        unavailable = {"count": None, "availability": "unavailable"}
        return {
            "syntax_errors": dict(unavailable),
            "name_collisions": {
                "count": None, "critical": None, "warning": None, "info": None,
                "availability": "unavailable",
            },
            "cycles": dict(unavailable),
            "attention_required": False,
            "availability": {
                "syntax_errors": "unavailable",
                "name_collisions": "unavailable",
                "cycles": "unavailable",
            },
        }

    syntax_values = None
    syntax_availability = "unavailable"
    collisions = getattr(state, "collisions", None)
    cycles = getattr(state, "cycles", None)
    collision_availability = _availability(state, "collisions", collisions)
    cycle_availability = _availability(state, "cycles", cycles)
    if collision_availability != "fresh":
        collision_count = critical = warning = info = None
    else:
        collision_count = len(collisions or [])
        critical = warning = info = None
    cycle_count = len(cycles) if cycle_availability == "fresh" else None
    syntax_issue = syntax_values if syntax_availability == "fresh" else None
    attention = any(
        value is not None and value > 0
        for value in (syntax_issue, collision_count, cycle_count)
    )
    return {
        "syntax_errors": {"count": syntax_values, "availability": syntax_availability},
        "name_collisions": {
            "count": collision_count,
            "critical": critical,
            "warning": warning,
            "info": info,
            "availability": collision_availability,
        },
        "cycles": {"count": cycle_count, "availability": cycle_availability},
        "attention_required": bool(attention),
        "availability": {
            "syntax_errors": syntax_availability,
            "name_collisions": collision_availability,
            "cycles": cycle_availability,
        },
    }


def diagnostics_summary(root: Path, state: Any = None) -> dict[str, Any]:
    if state is None:
        engine = mcp_runtime._live_engines.get(str(root))
        state = getattr(engine, "state", None) if engine is not None else None
    summary = diagnostics_summary_for_state(state)
    return summary


def diagnostics_summary_for_completed_job(summary: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    """Enrich one exact completed project-job response, never a global query."""
    if job.get("status") != "completed" or job.get("operation") != "project":
        return summary
    skipped = job.get("skipped_python_files")
    if not isinstance(skipped, list):
        return summary
    syntax_count = sum("not valid Python" in str(item.get("reason", "")) for item in skipped)
    result = dict(summary)
    result["syntax_errors"] = {"count": syntax_count, "availability": "fresh"}
    result["availability"] = dict(summary["availability"], syntax_errors="fresh")
    result["attention_required"] = bool(summary["attention_required"] or syntax_count > 0)
    return result


def inject_diagnostics_summary(
    result: Any,
    root_path: Any,
    tool_name: str,
    *,
    allow_large_output: bool = False,
    supports_allow_large_output: bool = False,
) -> Any:
    """Add a small summary to JSON analytical responses without touching prose/errors."""
    if tool_name == "get_mcp_documentation" or not isinstance(result, str):
        return result
    try:
        payload = json.loads(result)
    except (TypeError, json.JSONDecodeError):
        return result
    if not isinstance(payload, dict):
        return result
    if payload.get("status") in {"queued", "running", "accepted", "missing_repository"}:
        return result
    root = Path(root_path).expanduser().resolve() if root_path else None
    if root is None:
        return result
    summary = diagnostics_summary(root)
    payload.setdefault("diagnostics_summary", summary)
    payload.setdefault("diagnostics_attention_required", summary["attention_required"])
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    if allow_large_output or len(serialized.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES:
        return serialized
    guarded = guard_large_output(
        serialized,
        allow_large_output=False,
        retry_instruction=(
            "Repeat the same call with a narrower projection or allow_large_output=true."
            if supports_allow_large_output
            else "Repeat the same call with a narrower projection or semantic filter."
        ),
    )
    try:
        warning = json.loads(guarded)
    except json.JSONDecodeError:
        return guarded
    if not supports_allow_large_output:
        retry = warning.get("retry")
        if isinstance(retry, dict):
            retry.pop("allow_large_output", None)
            if not retry:
                warning.pop("retry", None)
    warning["diagnostics_summary"] = summary
    warning["diagnostics_attention_required"] = summary["attention_required"]
    final_guarded = json.dumps(warning, indent=2, ensure_ascii=False)
    if len(final_guarded.encode("utf-8")) <= LARGE_OUTPUT_WARNING_BYTES:
        return final_guarded
    compact_warning = {
        key: warning[key]
        for key in (
            "status",
            "warning",
            "message",
            "full_bytes",
            "estimated_bytes",
            "threshold_bytes",
            "context_budget_bytes",
            "retry_instruction",
        )
        if key in warning
    }
    compact_warning["status"] = compact_warning.get("status", "confirmation_required")
    compact_warning["diagnostics_summary"] = summary
    compact_warning["diagnostics_attention_required"] = summary["attention_required"]
    final_guarded = json.dumps(compact_warning, indent=2, ensure_ascii=False)
    final_bytes = len(final_guarded.encode("utf-8"))
    if final_bytes > LARGE_OUTPUT_WARNING_BYTES:
        raise RuntimeError("Diagnostics confirmation envelope exceeds MCP response budget")
    return final_guarded
