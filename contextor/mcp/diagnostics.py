"""Small, fail-closed diagnostics projections for MCP responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextor.core.diagnostics_projection import (
    diagnostics_summary_for_state,
)
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES, guard_large_output
from contextor.core.analysis.state_manager import canonical_python_source_path


def syntax_diagnostics_for_path(
    state: Any,
    source_path: str,
    *,
    max_items: int | None = 30,
    compact: bool = True,
) -> dict[str, Any]:
    """Project one canonical syntax fact without reading or parsing source."""
    canonical_path = canonical_python_source_path(source_path)
    if canonical_path is None:
        return {
            "status": "unavailable",
            "availability": "unavailable",
            "materialized": False,
            "errors": None,
        }

    family_state = getattr(state, "syntax_diagnostics_state", None)
    facts = getattr(state, "syntax_diagnostics_by_path", None)
    if family_state != "fresh" or not isinstance(facts, dict):
        return {
            "status": "unavailable",
            "availability": family_state if family_state in {"not_materialized", "deferred", "stale", "unavailable"} else "unavailable",
            "materialized": False,
            "source_path": canonical_path,
            "errors": None,
        }

    fact = facts.get(canonical_path)
    if not isinstance(fact, dict) or fact.get("status") not in {"checked_and_none", "checked_with_errors"}:
        return {
            "status": "unavailable",
            "availability": "unavailable",
            "materialized": False,
            "source_path": canonical_path,
            "errors": None,
        }

    status = fact["status"]
    if status == "checked_and_none":
        return {
            "status": status,
            "availability": "fresh",
            "materialized": True,
            "source_path": canonical_path,
            "errors": [],
            "total": 0,
            "truncated": False,
        }

    errors = fact.get("errors")
    if not isinstance(errors, list):
        errors = []
    bound = 3 if compact else max_items
    if bound is None:
        bounded_errors = list(errors)
    else:
        bounded_errors = errors[:max(0, bound)]
    return {
        "status": status,
        "availability": "fresh",
        "materialized": True,
        "source_path": canonical_path,
        "errors": bounded_errors,
        "total": len(errors),
        "truncated": len(bounded_errors) < len(errors),
    }


def diagnostics_summary(
    root: Path,
    state: Any = None,
) -> dict[str, Any]:
    if state is not None:
        return diagnostics_summary_for_state(
            state
        )

    live = (
        mcp_runtime
        .query_live_diagnostics_summary_narrow(
            root
        )
    )

    if (
        live.status == "ok"
        and live.summary is not None
    ):
        return live.summary

    if live.status == "unavailable":
        engine = (
            mcp_runtime
            ._cached_engine(root)
        )
        cached_state = (
            getattr(
                engine,
                "state",
                None,
            )
            if engine is not None
            else None
        )

        return diagnostics_summary_for_state(
            cached_state
        )

    return diagnostics_summary_for_state(
        None
    )


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
    fields: Any = None,
) -> Any:
    """Add a small summary to JSON analytical responses without touching prose/errors."""
    if tool_name in {"get_mcp_documentation", "lookup_index_entries"} or not isinstance(result, str):
        return result
    try:
        payload = json.loads(result)
    except (TypeError, json.JSONDecodeError):
        return result
    if not isinstance(payload, dict):
        return result
    if payload.get("status") in {
        "error",
        "queued",
        "running",
        "accepted",
        "missing_repository",
    }:
        return result
    if isinstance(fields, (list, tuple)) and fields:
        return result
    if any(
        key in payload
        for key in (
            "diagnostics_summary",
            "diagnostics_attention_required",
            "representation",
            "representation_decision",
            "sizes",
            "_output",
        )
    ):
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
