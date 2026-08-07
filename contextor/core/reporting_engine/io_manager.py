import os
import json
import glob
from pathlib import Path
from typing import Any

from .formatting import save_json

def _save_usage_sidecar(usage_sidecar: dict, path: str, log=None) -> None:
    save_json(usage_sidecar, path, log=log, label="artifacts usage sidecar")



def write_layer_reports(
    repo_name: str, layer_name: str, layer_reports: dict[str, Any], log=None, datestamp: str | None = None, layer_output_dir: str | None = None
):
    base_dir = f"output/{layer_output_dir}" if layer_output_dir else "output"
    os.makedirs(base_dir, exist_ok=True)
    suffix = f"_{datestamp}" if datestamp else ""
    prefix = f"{base_dir}/{repo_name}_{layer_name}"

    if "summary" in layer_reports:
        save_json(layer_reports["summary"], f"{prefix}_summary{suffix}.json", log=log, label=f"layer report [{layer_name}] - summary")
    if "structure" in layer_reports:
        save_json(layer_reports["structure"], f"{prefix}_structure{suffix}.json", log=log, label=f"layer report [{layer_name}] - structure")
    if "metrics" in layer_reports:
        save_json(layer_reports["metrics"], f"{prefix}_metrics{suffix}.json", log=log, label=f"layer report [{layer_name}] - metrics")
    if "artifacts_compact" in layer_reports:
        save_json(layer_reports["artifacts_compact"], f"{prefix}_artifacts_compact{suffix}.json", log=log, label=f"layer report [{layer_name}] - artifacts (compact)")
    if "graph_analytics" in layer_reports:
        save_json(layer_reports["graph_analytics"], f"{prefix}_graph_analytics{suffix}.json", log=log, label=f"layer report [{layer_name}] - graph analytics")
    


def write_global_reports(
    reports_data: dict[str, Any], repo_name: str, datestamp: str | None = None, log=None
):
    suffix = f"_{datestamp}" if datestamp else ""
    
    if "structure" in reports_data:
        save_json(reports_data["structure"], f"output/{repo_name}_structure{suffix}.json", log=log, label="graph structure report")
    
    if "collisions" in reports_data:
        save_json(reports_data["collisions"], f"output/{repo_name}_name_collisions{suffix}.json", log=log, label="name collisions report")
        
    if "artifacts_compact" in reports_data:
        from contextor.core.reporting_layer.artifact_usage_report_compact import save_compact_artifact_report
        save_compact_artifact_report(reports_data["artifacts_compact"], f"output/{repo_name}_artifacts_compact{suffix}.json")
        

        
    if "graph_analytics" in reports_data:
        save_json(reports_data["graph_analytics"], f"output/{repo_name}_graph_analytics{suffix}.json", log=log, label="graph analytics report")
        
    if "diff_report" in reports_data and reports_data["diff_report"] is not None:
        save_json(reports_data["diff_report"], f"output/{repo_name}_report_diff{suffix}.json", log=log, label="report diff")
        
    if "summary" in reports_data:
        save_json(reports_data["summary"], f"output/{repo_name}_summary{suffix}.json", log=log, label="summary report")
