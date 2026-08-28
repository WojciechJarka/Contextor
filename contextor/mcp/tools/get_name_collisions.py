"""Bounded projection of canonical name-collision diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextor.mcp import diagnostics
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import (
    LARGE_OUTPUT_WARNING_BYTES,
    guard_large_output,
    largest_fitting_prefix,
)


def _severity(error: Any) -> str:
    value = getattr(error, "severity", None)
    if value in {"critical", "warning", "info"}:
        return value
    from contextor.core.reporting_engine.formatting import _collision_severity

    return _collision_severity(
        getattr(error, "artifact_type", "unknown"),
        getattr(error, "symbol_details", []) or [],
        getattr(error, "code_snippets", {}) or {},
    )


def _sort_key(error: Any) -> tuple:
    return (
        str(getattr(error, "kind", "")),
        str(getattr(error, "artifact_type", "")),
        tuple(sorted(str(node) for node in (getattr(error, "nodes", []) or []))),
        str(getattr(error, "message", "")),
        bool(getattr(error, "is_identical", False)),
    )


def _detail(
    error: Any,
    representation: str,
    *,
    result_index: int | None = None,
    severity_value: str | None = None,
) -> dict[str, Any]:
    base = {
        "collision_type": getattr(error, "kind", "NAME_COLLISION"),
        "artifact_type": getattr(error, "artifact_type", "unknown"),
        "severity": severity_value if severity_value is not None else _severity(error),
        "is_identical": bool(getattr(error, "is_identical", False)),
        "modules": sorted(str(node) for node in (getattr(error, "nodes", []) or [])),
    }
    if representation != "summary":
        base["result_index"] = result_index
    if representation in {"indexed", "summary"}:
        return base
    base.update(
        {
            "message": getattr(error, "message", ""),
            "symbol_details": getattr(error, "symbol_details", []) or [],
            "conflicting_code": getattr(error, "code_snippets", {}) or {},
        }
    )
    return base


def _error_payload(message: str) -> str:
    return json.dumps({"error": message}, indent=2)


def get_name_collisions(
    repo_path: str,
    severity: str | None = None,
    artifact_type: str | None = None,
    collision_type: str | None = None,
    module: str | None = None,
    conflicting_only: bool = False,
    identical_only: bool = False,
    representation: str = "auto",
    offset: int = 0,
    limit: int | None = 20,
    allow_large_output: bool = False,
) -> str:
    if offset < 0:
        return _error_payload("offset must be >= 0")
    if limit is not None and limit <= 0:
        return _error_payload("limit must be > 0 or null")
    if severity is not None and severity not in {"critical", "warning", "info"}:
        return json.dumps({"error": "Unsupported severity", "allowed": ["critical", "warning", "info"]}, indent=2)
    if conflicting_only and identical_only:
        return _error_payload("conflicting_only and identical_only are mutually exclusive")
    if representation not in {"auto", "summary", "bounded", "indexed", "named"}:
        return json.dumps({"error": "Unsupported representation", "allowed": ["auto", "summary", "bounded", "indexed", "named"]}, indent=2)

    root = Path(repo_path).expanduser().resolve()
    engine = mcp_runtime.get_or_init_engine(root)
    state = getattr(engine, "state", None) if engine is not None else None
    availability = getattr(state, "collisions_state", "unavailable") if state is not None else "unavailable"
    if availability != "fresh":
        payload = {
            "total": None,
            "matched": None,
            "offset": offset,
            "returned": 0,
            "has_more": False,
            "next_offset": None,
            "severity_counts": {"critical": None, "warning": None, "info": None},
            "conflicting": None,
            "identical": None,
            "representation": representation,
            "truncated": offset > 0,
            "estimated_full_bytes": None,
            "context_budget_bytes": LARGE_OUTPUT_WARNING_BYTES,
            "attention_required": False,
            "availability": availability,
            "details": [],
            "guidance": "Collision diagnostics are not fresh; rerun analyze_project and retry.",
            "diagnostics_summary": diagnostics.diagnostics_summary(root, state),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    errors = list(getattr(state, "collisions", []) or [])
    selected: list[tuple[Any, str]] = []
    for error in errors:
        identical = bool(getattr(error, "is_identical", False))
        if artifact_type and str(getattr(error, "artifact_type", "")) != artifact_type:
            continue
        if collision_type and str(getattr(error, "kind", "")) != collision_type:
            continue
        if module and module not in {str(node) for node in (getattr(error, "nodes", []) or [])}:
            continue
        if conflicting_only and identical:
            continue
        if identical_only and not identical:
            continue
        item_severity = _severity(error)
        if severity and item_severity != severity:
            continue
        selected.append((error, item_severity))

    selected.sort(key=lambda item: _sort_key(item[0]))
    matched = len(selected)
    severity_counts = {name: sum(item[1] == name for item in selected) for name in ("critical", "warning", "info")}
    identical_count = sum(bool(getattr(error, "is_identical", False)) for error, _ in selected)
    if limit is None:
        page = selected[offset:]
    else:
        page = selected[offset : offset + limit]

    if representation == "auto":
        if matched == 0:
            effective = "named"
        elif limit is None:
            effective = "indexed"
        else:
            effective = "named"
    else:
        effective = representation

    def details_for(kind: str) -> list[dict[str, Any]]:
        return [
            _detail(
                error,
                kind,
                result_index=offset + index,
                severity_value=item_severity,
            )
            for index, (error, item_severity) in enumerate(page)
        ]

    visible_details = [] if effective == "summary" else details_for(effective)
    estimated_full_bytes = None

    def make_payload(details: list[dict[str, Any]], kind: str) -> dict[str, Any]:
        returned = len(details)
        if kind == "summary":
            has_more = False
            next_offset = None
            truncated = bool(matched)
        else:
            has_more = offset + returned < matched
            next_offset = offset + returned if has_more else None
            truncated = offset > 0 or has_more
        return {
            "total": len(errors),
            "matched": matched,
            "offset": offset,
            "returned": returned,
            "has_more": has_more,
            "next_offset": next_offset,
            "severity_counts": severity_counts,
            "conflicting": matched - identical_count,
            "identical": identical_count,
            "representation": kind,
            "truncated": truncated,
            "estimated_full_bytes": estimated_full_bytes,
            "context_budget_bytes": LARGE_OUTPUT_WARNING_BYTES,
            "attention_required": bool(matched),
            "availability": "fresh",
            "details": details,
            "diagnostics_summary": diagnostics.diagnostics_summary(root, state),
        }

    if representation == "auto" and effective == "named" and matched:
        candidate = json.dumps(make_payload(visible_details, effective), indent=2, ensure_ascii=False)
        if not allow_large_output and len(candidate.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES:
            effective = "indexed"
            visible_details = details_for(effective)

    if effective == "summary":
        visible_details = []

    def build(count: int) -> str:
        details = visible_details[:count]
        return json.dumps(make_payload(details, effective), indent=2, ensure_ascii=False)

    candidate = build(len(visible_details))
    if len(candidate.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES and not allow_large_output:
        bounded = largest_fitting_prefix(len(visible_details), build, min_count=0)
        if bounded is not None:
            bounded_text = bounded[0]
            bounded_payload = json.loads(bounded_text)
            returned = int(bounded_payload.get("returned", 0))
            has_more = bool(bounded_payload.get("has_more", False))
            next_offset = bounded_payload.get("next_offset")
            if not has_more:
                return bounded_text
            if returned > 0 and isinstance(next_offset, int) and next_offset > offset:
                return bounded_text
    return guard_large_output(
        candidate,
        allow_large_output=allow_large_output,
        requested_count=limit,
        retry_instruction="Repeat with representation='indexed' or a smaller limit, or set allow_large_output=true.",
    )
