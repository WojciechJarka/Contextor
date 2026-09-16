import json
from pathlib import Path
from typing import Any

from contextor.core.analysis.state_manager import module_current_truth
from contextor.mcp import query_helpers
from contextor.mcp import report_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.diagnostics import diagnostics_summary
from contextor.mcp.output_guard import guard_large_output
from contextor.mcp.representation import serialized_json_bytes


PROJECT_ARCHITECTURE_DIRECT_BYTES = 50 * 1024

_REPORT_FILES: tuple[tuple[str, str], ...] = (
    ("summary", "summary.json"),
    ("structure", "structure.json"),
    ("name_collisions", "name_collisions.json"),
    ("artifacts_compact", "artifacts_compact.json"),
    ("graph_analytics", "graph_analytics.json"),
    ("report_diff", "report_diff.json"),
)


def _error(code: str, **details: Any) -> str:
    return json.dumps(
        {
            "status": "error",
            "error": code,
            **details,
        },
        indent=2,
        ensure_ascii=False,
    )


def _stale_module_truths(state: Any) -> dict[str, dict[str, Any]]:
    module_names = set(getattr(state, "modules", {}) or {}) | set(
        getattr(state, "artifacts", {}) or {}
    )
    return {
        module_name: truth
        for module_name in sorted(module_names)
        if not (truth := module_current_truth(state, module_name))["available"]
    }


def _report_generated_at(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    generated_at = payload.get("generated_at")
    if isinstance(generated_at, str) and generated_at:
        return generated_at

    report_header = payload.get("report_header")
    if isinstance(report_header, dict):
        generated_at = report_header.get("generated_at")
        if isinstance(generated_at, str) and generated_at:
            return generated_at

    current = payload.get("current")
    if isinstance(current, dict):
        generated_at = current.get("generated_at")
        if isinstance(generated_at, str) and generated_at:
            return generated_at

    runtime = payload.get("runtime")
    if isinstance(runtime, dict):
        generated_at = runtime.get("generated_at")
        if isinstance(generated_at, str) and generated_at:
            return generated_at

    return None


def _load_report(
    root: Path,
    field: str,
    suffix: str,
) -> tuple[Any, dict[str, Any]]:
    filename = f"{root.name}_{suffix}"
    try:
        path = report_helpers.get_canonical_report(root, filename)
    except Exception as exc:
        unavailable = {
            "available": False,
            "state": "unavailable",
            "reason": f"Report lookup failed: {exc}",
        }
        return unavailable, {
            "available": False,
            "field": field,
            "filename": filename,
            "state": "unavailable",
            "reason": unavailable["reason"],
            "serialized_bytes": None,
            "serialized_kib": None,
        }

    if path is None:
        unavailable = {
            "available": False,
            "state": "unavailable",
            "reason": f"Completed project report not found: {filename}",
        }
        return unavailable, {
            "available": False,
            "field": field,
            "filename": filename,
            "state": "unavailable",
            "reason": unavailable["reason"],
            "serialized_bytes": None,
            "serialized_kib": None,
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        unavailable = {
            "available": False,
            "state": "invalid",
            "reason": f"Completed project report could not be read: {exc}",
        }
        return unavailable, {
            "available": False,
            "field": field,
            "filename": filename,
            "report_path": str(path),
            "state": "invalid",
            "reason": unavailable["reason"],
            "serialized_bytes": None,
            "serialized_kib": None,
        }

    payload_bytes = serialized_json_bytes(payload)
    return payload, {
        "available": True,
        "field": field,
        "filename": filename,
        "report_path": str(path),
        "source": "completed_analysis_report",
        "generated_at": _report_generated_at(payload),
        "serialized_bytes": payload_bytes,
        "serialized_kib": payload_bytes / 1024,
    }


def _load_report_bundle(
    root: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    reports: dict[str, Any] = {}
    catalog: dict[str, dict[str, Any]] = {}
    for field, suffix in _REPORT_FILES:
        payload, metadata = _load_report(root, field, suffix)
        reports[field] = payload
        catalog[field] = metadata
    return reports, catalog


def _live_state_overlay(root: Path) -> dict[str, Any]:
    try:
        engine = mcp_runtime.get_or_init_engine(root)
    except Exception as exc:
        return {
            "available": False,
            "state": "unavailable",
            "reason": f"Canonical LIVE state lookup failed: {exc}",
        }

    state = getattr(engine, "state", None) if engine is not None else None
    if state is None:
        return {
            "available": False,
            "state": "unavailable",
            "reason": "No usable canonical LIVE state is available.",
        }

    try:
        diag = diagnostics_summary(root, state)
    except Exception as exc:
        diag = {
            "available": False,
            "state": "unavailable",
            "reason": f"Diagnostics summary failed: {exc}",
        }

    try:
        freshness = query_helpers.build_state_freshness(
            root,
            state,
            engine=engine,
        )
    except Exception as exc:
        freshness = {
            "canonical_state": (
                "stale"
                if getattr(state, "resync_required", False)
                else "unknown"
            ),
            "workspace_sync": "unverified",
            "canonical_revision": getattr(engine, "revision", None),
            "provenance": getattr(engine, "provenance", None),
            "families": {},
            "advisory_warning": f"Freshness envelope failed: {exc}",
        }

    stale_modules = _stale_module_truths(state)
    if stale_modules:
        freshness = dict(freshness)
        freshness["canonical_state"] = "stale"
        existing_warning = freshness.get("advisory_warning")
        stale_warning = (
            "One or more modules are parse-stale; canonical facts for those "
            "modules are last-known-good."
        )
        freshness["advisory_warning"] = (
            f"{existing_warning} {stale_warning}"
            if existing_warning
            else stale_warning
        )

    return {
        "available": True,
        "data_source": "live_canonical_state",
        "module_count": len(getattr(state, "modules", {}) or {}),
        "resync_required": bool(getattr(state, "resync_required", False)),
        "parse_stale_modules": stale_modules,
        "state_freshness": freshness,
        "diagnostics_summary": diag,
        "diagnostics_attention_required": (
            bool(diag.get("attention_required", False))
            if isinstance(diag, dict)
            else False
        ),
    }


def _bundle_state(catalog: dict[str, dict[str, Any]]) -> str:
    available = sum(
        1
        for metadata in catalog.values()
        if metadata.get("available") is True
    )
    if available == len(catalog):
        return "complete"
    if available:
        return "partial"
    return "unavailable"


def _build_payload(
    *,
    selected_fields: list[str],
    reports: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    live_state: dict[str, Any],
) -> dict[str, Any]:
    bundle_state = _bundle_state(catalog)
    return {
        "status": "ok" if bundle_state == "complete" else "partial",
        "scope": "project",
        "data_source": "completed_analysis_report_bundle",
        "report_bundle_state": bundle_state,
        "available_fields": [field for field, _ in _REPORT_FILES],
        "selected_fields": selected_fields,
        "reports": {
            field: reports[field]
            for field in selected_fields
        },
        "report_catalog": catalog,
        "live_state": live_state,
    }


def get_project_architecture(
    repo_path: str,
    fields: list[str] | None = None,
    allow_large_output: bool = False,
) -> str:
    if fields is not None and (
        not isinstance(fields, list)
        or any(not isinstance(field, str) for field in fields)
    ):
        return _error(
            "invalid_fields",
            expected="array of project report field names or null",
        )
    if not isinstance(allow_large_output, bool):
        return _error(
            "invalid_allow_large_output",
            expected="boolean",
        )

    root = Path(repo_path).expanduser().resolve()
    allowed_fields = [field for field, _ in _REPORT_FILES]

    if fields is None:
        selected_fields = list(allowed_fields)
    else:
        selected_fields = list(dict.fromkeys(fields))
        unknown_fields = sorted(set(selected_fields) - set(allowed_fields))
        if unknown_fields:
            return _error(
                "unsupported_fields",
                unknown_fields=unknown_fields,
                allowed_fields=allowed_fields,
            )

    try:
        reports, catalog = _load_report_bundle(root)
        live_state = _live_state_overlay(root)
        result = _build_payload(
            selected_fields=selected_fields,
            reports=reports,
            catalog=catalog,
            live_state=live_state,
        )
        serialized = json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )

        guarded = guard_large_output(
            serialized,
            allow_large_output=allow_large_output,
            requested_count=len(selected_fields),
            reason=(
                "Selected project architecture reports exceed the "
                "50 KiB direct-response threshold."
            ),
            retry_instruction=(
                "Inspect report_catalog serialized_bytes/serialized_kib, "
                "retry with fields limited to the report sections you need, "
                "or repeat the identical selection with "
                "allow_large_output=true."
            ),
            warning_threshold_bytes=PROJECT_ARCHITECTURE_DIRECT_BYTES,
        )
        if guarded == serialized:
            return serialized

        warning = json.loads(guarded)
        warning.update(
            {
                "scope": "project",
                "report_bundle_state": result["report_bundle_state"],
                "available_fields": allowed_fields,
                "selected_fields": selected_fields,
                "report_catalog": catalog,
                "live_state": live_state,
                "retry": {
                    "fields": selected_fields,
                    "allow_large_output": True,
                },
            }
        )
        return json.dumps(
            warning,
            indent=2,
            ensure_ascii=False,
        )
    except Exception as exc:
        return _error(
            "project_architecture_failed",
            detail=str(exc),
        )
