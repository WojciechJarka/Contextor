import os
import json
import glob
from pathlib import Path
from typing import Any

from .formatting import save_json

def _save_usage_sidecar(usage_sidecar: dict, path: str, log=None) -> None:
    save_json(usage_sidecar, path, log=log, label="artifacts usage sidecar")

def _save_index_dictionary_with_dedup(
    new_dict: dict,
    path: str,
    log=None,
    label: str = "index dictionary",
) -> None:
    target = Path(path)
    parent = target.parent
    stem_base = target.stem
    parts = stem_base.rsplit("_", 2)
    if len(parts) >= 3:
        base_prefix = "_".join(parts[:-2])
    else:
        base_prefix = stem_base

    pattern = str(parent / f"{base_prefix}_*_*.json")
    existing = sorted(
        [f for f in glob.glob(pattern) if "_outdated" not in f and len(Path(f).stem.split("_")) == len(parts) + 2],
        reverse=True,
    )

    new_content = json.dumps(new_dict, sort_keys=True)

    if existing:
        latest = existing[0]
        try:
            old_content = json.dumps(
                json.loads(Path(latest).read_text(encoding="utf-8")),
                sort_keys=True,
            )
        except Exception:
            old_content = None

        if old_content is not None and old_content == new_content:
            try:
                os.remove(latest)
                if log:
                    log(f"[DICT] Identical dictionary found — replaced: {Path(latest).name}")
            except OSError:
                pass
        else:
            outdated_path = Path(latest).with_stem(Path(latest).stem + "_outdated")
            try:
                os.rename(latest, outdated_path)
                if log:
                    log(f"[DICT] Dictionary changed — old marked as outdated: {outdated_path.name}")
            except OSError:
                pass

    save_json(new_dict, path, log=log, label=label)

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
    
    if "_index_dict" in layer_reports:
        index_dict = layer_reports["_index_dict"]
        index_dict_path = f"{prefix}_index_dictionary{suffix}.json"
        _save_index_dictionary_with_dedup(
            index_dict.to_json_dict(), 
            index_dict_path, 
            log=log, 
            label=f"layer report [{layer_name}] - index dictionary"
        )

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
        
    if "index_dict" in reports_data:
        _save_index_dictionary_with_dedup(reports_data["index_dict"], f"output/{repo_name}_index_dictionary{suffix}.json", log=log)
        
    if "graph_analytics" in reports_data:
        save_json(reports_data["graph_analytics"], f"output/{repo_name}_graph_analytics{suffix}.json", log=log, label="graph analytics report")
        
    if "diff_report" in reports_data and reports_data["diff_report"] is not None:
        save_json(reports_data["diff_report"], f"output/{repo_name}_report_diff{suffix}.json", log=log, label="report diff")
        
    if "summary" in reports_data:
        save_json(reports_data["summary"], f"output/{repo_name}_summary{suffix}.json", log=log, label="summary report")
