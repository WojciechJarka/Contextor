"""Layer-specific report pipeline.

This module transforms a sliced layer payload into graph analytics and the
compact status consumed by the global report orchestrator.
"""

from __future__ import annotations

from typing import Any

from contextor.core.program_log import log_program_event

from .graph_analytics import generate_graph_analytics_report


def execute_layer_pipeline(
    repo_name: str,
    layer_name: str,
    layer_reports: dict[str, Any],
    log=None,
    datestamp: str | None = None,
    progress_callback=None,
) -> dict:
    """Complete report-specific processing for one architectural layer."""
    log_program_event("REPORT", "layer pipeline start", layer=layer_name)
    del repo_name, log, datestamp  # Reserved by the stable public interface.

    artifact_data = layer_reports.get("artifacts")
    if not _is_full_artifact_report(artifact_data):
        candidate = layer_reports.get("artifacts_full")
        if _is_full_artifact_report(candidate):
            artifact_data = candidate

    structure = (
        layer_reports.get("structure_raw")
        or layer_reports.get("structure")
        or {}
    )
    if not isinstance(structure, dict):
        structure = {}

    if _is_full_artifact_report(artifact_data):
        summary = layer_reports.get("summary", {})
        module_names = (
            summary.get("layer_modules", [])
            if isinstance(summary, dict)
            else []
        )
        scope_modules = {
            name for name in module_names if isinstance(name, str)
        }
        layer_reports["graph_analytics"] = generate_graph_analytics_report(
            artifact_data=artifact_data,
            hard_edges=structure.get("hard_edges", {}) or {},
            soft_edges=structure.get("soft_edges", {}) or {},
            index_dict=layer_reports.get("_index_dict"),
            scope="layer",
            scope_modules=scope_modules,
            global_artifact_data=layer_reports.get("_global_artifact_data"),
            progress_callback=progress_callback,
        )

    status = _layer_status(layer_name, layer_reports.get("summary", {}))
    log_program_event(
        "REPORT",
        "layer pipeline complete",
        layer=layer_name,
        mode=status.get("computation_mode"),
    )
    return status


def _is_full_artifact_report(value: object) -> bool:
    """Return whether *value* contains the full artifact mapping."""
    return isinstance(value, dict) and isinstance(value.get("artifacts"), dict)


def _layer_status(layer_name: str, summary: object) -> dict:
    """Build the small layer-index record used by global summaries."""
    if not isinstance(summary, dict):
        summary = {}
    return {
        "layer": layer_name,
        "module_count": summary.get("layer_module_count", 0),
        "status": summary.get("status", "UNKNOWN"),
        "cycles_count": summary.get("layer_cycles_count", 0),
        "hotspot_count": len(summary.get("hotspots", []) or []),
        "computation_mode": summary.get("computation_mode", "filtered"),
    }
