import os
import json
import glob
from pathlib import Path
from typing import Any

from .formatting import save_json
from contextor.core.paths import atomic_write, resolve_report_path


def _summary_markdown(title: str, summary: dict) -> str:
    lines = [f"# {title}", ""]
    for label, key in (("Status", "status"), ("Generated", "generated_at"), ("Modules", "layer_module_count")):
        value = summary.get(key)
        if value is not None:
            lines.append(f"- **{label}:** {value}")
    metrics = summary.get("metrics", {})
    if isinstance(metrics, dict):
        for key in ("nodes", "edges_hard", "edges_soft", "density_hard"):
            if key in metrics:
                lines.append(f"- **{key}:** {metrics[key]}")
    action_items = summary.get("action_items", [])
    if action_items:
        lines.extend(["", "## Action items", ""])
        lines.extend(f"- {item}" for item in action_items)
    return "\n".join(lines) + "\n"


def _save_markdown(content: str, path: str) -> None:
    atomic_write(resolve_report_path(path), content)

def _save_usage_sidecar(usage_sidecar: dict, path: str, log=None) -> None:
    save_json(usage_sidecar, path, log=log, label="artifacts usage sidecar")



def write_layer_reports(
    repo_name: str,
    layer_name: str,
    layer_reports: dict[str, Any],
    log=None,
    layer_output_dir: str | None = None,
    datestamp: str | None = None,
):
    """Write layer-specific report files.

    ``datestamp`` is accepted for API consistency with write_global_reports but
    is deliberately not appended to filenames — layer report names are stable
    and do not include a date suffix.
    """
    base_dir = f"output/{layer_output_dir}" if layer_output_dir else "output"
    os.makedirs(base_dir, exist_ok=True)
    prefix = f"{base_dir}/{repo_name}_{layer_name}"
    if datestamp and layer_output_dir:
        snapshot_prefix = f"{base_dir}/{datestamp}/{repo_name}_{layer_name}"
    elif datestamp:
        snapshot_prefix = f"output/{repo_name}_{datestamp}/{repo_name}_{layer_name}"
    else:
        snapshot_prefix = None

    if "summary" in layer_reports:
        save_json(layer_reports["summary"], f"{prefix}_summary.json", log=log, label=f"layer report [{layer_name}] - summary")
        _save_markdown(_summary_markdown(f"Layer report: {layer_name}", layer_reports["summary"]), f"{prefix}_summary.md")
        if snapshot_prefix:
            save_json(layer_reports["summary"], f"{snapshot_prefix}_summary.json", log=log, label=f"layer snapshot [{layer_name}] - summary")
            _save_markdown(_summary_markdown(f"Layer report: {layer_name}", layer_reports["summary"]), f"{snapshot_prefix}_summary.md")
    if "structure" in layer_reports:
        save_json(layer_reports["structure"], f"{prefix}_structure.json", log=log, label=f"layer report [{layer_name}] - structure")
        if snapshot_prefix:
            save_json(layer_reports["structure"], f"{snapshot_prefix}_structure.json", log=log, label=f"layer snapshot [{layer_name}] - structure")
    if "metrics" in layer_reports:
        save_json(layer_reports["metrics"], f"{prefix}_metrics.json", log=log, label=f"layer report [{layer_name}] - metrics")
        if snapshot_prefix:
            save_json(layer_reports["metrics"], f"{snapshot_prefix}_metrics.json", log=log, label=f"layer snapshot [{layer_name}] - metrics")
    if "artifacts_compact" in layer_reports:
        save_json(layer_reports["artifacts_compact"], f"{prefix}_artifacts_compact.json", log=log, label=f"layer report [{layer_name}] - artifacts (compact)")
        if snapshot_prefix:
            save_json(layer_reports["artifacts_compact"], f"{snapshot_prefix}_artifacts_compact.json", log=log, label=f"layer snapshot [{layer_name}] - artifacts")
    if "graph_analytics" in layer_reports:
        save_json(layer_reports["graph_analytics"], f"{prefix}_graph_analytics.json", log=log, label=f"layer report [{layer_name}] - graph analytics")
        if snapshot_prefix:
            save_json(layer_reports["graph_analytics"], f"{snapshot_prefix}_graph_analytics.json", log=log, label=f"layer snapshot [{layer_name}] - graph analytics")
    


def write_global_reports(
    reports_data: dict[str, Any], repo_name: str, datestamp: str | None = None, log=None
):
    snapshot_prefix = f"output/{repo_name}_{datestamp}/{repo_name}" if datestamp else None

    if "structure" in reports_data:
        save_json(reports_data["structure"], f"output/{repo_name}_structure.json", log=log, label="graph structure report")
        if snapshot_prefix:
            save_json(reports_data["structure"], f"{snapshot_prefix}_structure.json", log=log, label="graph structure snapshot")
    
    if "collisions" in reports_data:
        save_json(reports_data["collisions"], f"output/{repo_name}_name_collisions.json", log=log, label="name collisions report")
        if snapshot_prefix:
            save_json(reports_data["collisions"], f"{snapshot_prefix}_name_collisions.json", log=log, label="name collisions snapshot")
        
    if "artifacts_compact" in reports_data:
        from contextor.core.reporting_layer.artifact_usage_report_compact import save_compact_artifact_report
        save_compact_artifact_report(reports_data["artifacts_compact"], f"output/{repo_name}_artifacts_compact.json")
        if snapshot_prefix:
            save_json(reports_data["artifacts_compact"], f"{snapshot_prefix}_artifacts_compact.json", log=log, label="artifact snapshot")
        

        
    if "graph_analytics" in reports_data:
        save_json(reports_data["graph_analytics"], f"output/{repo_name}_graph_analytics.json", log=log, label="graph analytics report")
        if snapshot_prefix:
            save_json(reports_data["graph_analytics"], f"{snapshot_prefix}_graph_analytics.json", log=log, label="graph analytics snapshot")
        
    if "diff_report" in reports_data and reports_data["diff_report"] is not None:
        save_json(reports_data["diff_report"], f"output/{repo_name}_report_diff.json", log=log, label="report diff")
        if snapshot_prefix:
            save_json(reports_data["diff_report"], f"{snapshot_prefix}_report_diff.json", log=log, label="report diff snapshot")
        
    if "summary" in reports_data:
        save_json(reports_data["summary"], f"output/{repo_name}_summary.json", log=log, label="summary report")
        _save_markdown(_summary_markdown(f"Project report: {repo_name}", reports_data["summary"]), f"output/{repo_name}_summary.md")
        if snapshot_prefix:
            save_json(reports_data["summary"], f"{snapshot_prefix}_summary.json", log=log, label="summary snapshot")
            _save_markdown(_summary_markdown(f"Project report: {repo_name}", reports_data["summary"]), f"{snapshot_prefix}_summary.md")
