"""Bounded projection of canonical name-collision diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextor.mcp import diagnostics
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import LARGE_OUTPUT_WARNING_BYTES, guard_large_output, largest_fitting_prefix


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


def _detail(error: Any, representation: str) -> dict[str, Any]:
    severity = _severity(error)
    base = {
        "collision_type": getattr(error, "kind", "NAME_COLLISION"),
        "artifact_type": getattr(error, "artifact_type", "unknown"),
        "severity": severity,
        "is_identical": bool(getattr(error, "is_identical", False)),
        "modules": sorted(str(node) for node in (getattr(error, "nodes", []) or [])),
    }
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


def get_name_collisions(
    repo_path: str,
    severity: str | None = None,
    artifact_type: str | None = None,
    collision_type: str | None = None,
    module: str | None = None,
    conflicting_only: bool = False,
    identical_only: bool = False,
    representation: str = "auto",
    limit: int | None = 20,
    allow_large_output: bool = False,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    engine = mcp_runtime.get_or_init_engine(root)
    state = getattr(engine, "state", None) if engine is not None else None
    availability = getattr(state, "collisions_state", "unavailable") if state is not None else "unavailable"
    if availability != "fresh":
        payload = {
            "total": None,
            "matched": None,
            "returned": 0,
            "severity_counts": {"critical": None, "warning": None, "info": None},
            "conflicting": None,
            "identical": None,
            "representation": representation,
            "truncated": False,
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
    if severity is not None and severity not in {"critical", "warning", "info"}:
        return json.dumps({"error": "Unsupported severity", "allowed": ["critical", "warning", "info"]}, indent=2)
    if conflicting_only and identical_only:
        return json.dumps({"error": "conflicting_only and identical_only are mutually exclusive"}, indent=2)
    if representation not in {"auto", "summary", "bounded", "indexed", "named"}:
        return json.dumps({"error": "Unsupported representation", "allowed": ["auto", "summary", "bounded", "indexed", "named"]}, indent=2)
    selected = []
    for error in errors:
        item_severity = _severity(error)
        identical = bool(getattr(error, "is_identical", False))
        if severity and item_severity != severity:
            continue
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
        selected.append(error)

    severity_counts = {name: sum(_severity(error) == name for error in selected) for name in ("critical", "warning", "info")}
    identical_count = sum(bool(getattr(error, "is_identical", False)) for error in selected)
    full_details = [_detail(error, "named") for error in selected]
    estimated_full_bytes = len(json.dumps(full_details, indent=2, ensure_ascii=False).encode("utf-8"))
    effective = "indexed" if representation == "auto" and estimated_full_bytes > LARGE_OUTPUT_WARNING_BYTES else ("named" if representation == "auto" else representation)
    if effective == "summary":
        visible_details = []
    else:
        visible_details = [_detail(error, effective) for error in selected]
    if limit is not None:
        visible_details = visible_details[: max(0, int(limit))]
    truncated = len(visible_details) < len(selected)
    summary = {
        "total": len(errors),
        "matched": len(selected),
        "returned": len(visible_details),
        "severity_counts": severity_counts,
        "conflicting": len(selected) - identical_count,
        "identical": identical_count,
        "representation": effective,
        "truncated": truncated,
        "estimated_full_bytes": estimated_full_bytes,
        "context_budget_bytes": LARGE_OUTPUT_WARNING_BYTES,
        "attention_required": bool(selected),
        "availability": "fresh",
    }

    def build(count: int) -> str:
        body = {**summary, "returned": count, "truncated": count < len(selected), "details": visible_details[:count], "diagnostics_summary": diagnostics.diagnostics_summary(root, state)}
        if count < len(selected):
            body["guidance"] = "Narrow by severity, module, artifact_type, or use representation='indexed'."
        return json.dumps(body, indent=2, ensure_ascii=False)

    candidate = build(len(visible_details))
    if len(candidate.encode("utf-8")) > LARGE_OUTPUT_WARNING_BYTES and not allow_large_output:
        bounded = largest_fitting_prefix(len(visible_details), build, min_count=0)
        if bounded is not None:
            return bounded[0]
    return guard_large_output(
        candidate,
        allow_large_output=allow_large_output,
        requested_count=limit,
        retry_instruction="Repeat with representation='indexed' or a smaller limit, or set allow_large_output=true.",
    )
