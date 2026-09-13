from __future__ import annotations

import json
from pathlib import Path

from contextor.core.lineage_query.service import (
    LineageTargetResolution,
    ResolvedLineageTarget,
)
from contextor.mcp import representation as mcp_rep
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.lineage_response import (
    plan_symbol_lineage_response,
    render_symbol_lineage_response,
)


def _error(code: str, **details) -> str:
    return json.dumps(
        {"status": "error", "error": code, **details},
        indent=2,
        ensure_ascii=False,
    )


def _target_payload(target: ResolvedLineageTarget) -> dict:
    return {
        "artifact_id": target.artifact_id,
        "qualified_name": target.qualified_name,
        "module": target.module_name,
        "symbol": target.symbol_name,
        "resolution": target.resolution,
    }


def _resolution_response(
    resolution: LineageTargetResolution,
    *,
    state_freshness: dict[str, object],
    unavailable_reason: str | None = None,
) -> str:
    if resolution.status == "unavailable":
        return json.dumps(
            {
                "status": "unavailable",
                "symbol": resolution.query,
                "reason": unavailable_reason,
                "state_freshness": state_freshness,
            },
            indent=2,
            ensure_ascii=False,
        )
    if resolution.status == "invalid":
        return json.dumps(
            {
                "status": "invalid",
                "error": "exact_symbol_required",
                "symbol": resolution.query,
                "expected": "active artifact ID or exact module::symbol identity",
                "state_freshness": state_freshness,
            },
            indent=2,
            ensure_ascii=False,
        )
    if resolution.status == "not_found":
        return json.dumps(
            {"status": "not_found", "symbol": resolution.query, "state_freshness": state_freshness},
            indent=2,
            ensure_ascii=False,
        )
    if resolution.status == "ambiguous":
        return json.dumps(
            {
                "status": "ambiguous",
                "symbol": resolution.query,
                "candidates": [_target_payload(candidate) for candidate in resolution.candidates],
                "state_freshness": state_freshness,
            },
            indent=2,
            ensure_ascii=False,
        )
    return _error(
        "canonical_lineage_resolution_invalid",
        resolution_status=resolution.status,
    )


def get_symbol_lineage(
    repo_path: str,
    symbol: str,
    mode: str = "auto",
    sections: list[str] | None = None,
    representation: str = "auto",
    allow_large_output: bool = False,
) -> str:
    if not isinstance(repo_path, str):
        return _error("invalid_repo_path", expected="string")
    if not isinstance(symbol, str):
        return _error(
            "invalid_symbol",
            expected="active artifact ID or exact module::symbol identity",
        )
    if sections is not None and not isinstance(sections, list):
        return _error("invalid_sections", expected="list of section names or null")
    if not isinstance(representation, str):
        return _error(
            "invalid_representation",
            allowed=sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
        )
    normalized_representation = representation.strip().lower()
    if not mcp_rep.is_supported_representation(normalized_representation):
        return _error(
            "invalid_representation",
            allowed=sorted(mcp_rep.ALLOWED_REPRESENTATIONS),
        )
    if not isinstance(allow_large_output, bool):
        return _error("invalid_allow_large_output")

    requested_sections = None if sections is None else tuple(sections)
    try:
        plan = plan_symbol_lineage_response(mode=mode, sections=requested_sections)
    except (TypeError, ValueError) as exc:
        return _error("invalid_request", message=str(exc))

    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return _error("repository_not_found", repo_path=str(root))

    transport = mcp_runtime.query_live_symbol_lineage_narrow(
        root,
        query=symbol,
        sections=plan.candidate_sections,
    )
    if transport.status != "ok":
        details = {}
        if transport.detail is not None:
            details["detail"] = transport.detail
        if transport.revision is not None:
            details["canonical_revision"] = transport.revision
        return _error(transport.error or "canonical_live_query_failed", **details)

    result = transport.result
    if result is None:
        return _error("canonical_query_response_invalid")
    resolution = result.resolution
    if resolution.status != "resolved" or resolution.target is None:
        return _resolution_response(
            resolution,
            state_freshness=result.state_freshness,
            unavailable_reason=result.unavailable_reason,
        )
    if result.selected is None:
        return _error(
            "canonical_query_response_invalid",
            message="Resolved lineage target returned no selected facts.",
        )
    try:
        return render_symbol_lineage_response(
            result.selected,
            mode=plan.mode,
            sections=requested_sections,
            representation=normalized_representation,
            owner_names=result.owner_names,
            state_freshness=result.state_freshness,
            allow_large_output=allow_large_output,
        )
    except (TypeError, ValueError) as exc:
        return _error("lineage_response_failed", message=str(exc))
