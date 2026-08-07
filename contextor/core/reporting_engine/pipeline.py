from typing import Any
import json
import os
import glob
from datetime import datetime
from pathlib import Path

def execute_layer_pipeline(
    repo_name: str, layer_name: str, layer_reports: dict[str, Any], log=None, datestamp: str | None = None
) -> dict:
    from .graph_analytics import generate_graph_analytics_report
    
    layer_artifact_data = layer_reports.get("artifacts") or layer_reports.get("artifacts_compact", {})
    layer_structure = layer_reports.get("structure", {})
    layer_hard_edges = layer_structure.get("hard_edges", {})
    layer_soft_edges = layer_structure.get("soft_edges", {})
    index_dict = layer_reports.get("_index_dict")
    
    if layer_artifact_data and isinstance(layer_artifact_data, dict) and "artifacts" in layer_artifact_data:
        graph_analytics_layer_data = generate_graph_analytics_report(
            artifact_data=layer_artifact_data,
            hard_edges=layer_hard_edges,
            soft_edges=layer_soft_edges,
            index_dict=index_dict,
            scope="layer",
        )
        layer_reports["graph_analytics"] = graph_analytics_layer_data

    summary = layer_reports["summary"]
    return {
        "layer": layer_name,
        "module_count": summary.get("layer_module_count", 0),
        "status": summary.get("status", "UNKNOWN"),
        "cycles_count": summary.get("layer_cycles_count", 0),
        "hotspot_count": len(summary.get("hotspots", [])),
        "computation_mode": summary.get("computation_mode", "filtered"),
    }

def execute_global_pipeline(
    repo_name: str,
    modules: dict,
    graph: object,
    metrics: dict,
    cycles: list,
    debt: dict,
    runtime: dict,
    root_path: str,
    log=None,
    collisions: list | None = None,
    progress_callback=None,
    skipped_files: list | None = None,
    layer_index: list[dict] | None = None,
    datestamp: str | None = None,
):
    if log:
        log("Starting sequential report generation...")

    from contextor.core.validator.collisions import validate_name_collisions
    from contextor.core.hotspots import detect_hotspots
    from .header import build_report_header
    from .generators import _sanity_check_reports, generate_summary_report, generate_structure_report, generate_collisions_report, slice_report_for_layer
    from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report
    from contextor.core.reporting_layer.artifact_usage_report_compact import compact_artifact_report
    from contextor.core.reporting_engine.dictionary import IndexDictionary
    from .graph_analytics import generate_graph_analytics_report
    from contextor.core.git.repo_state import is_git_repo, get_current_commit
    from contextor.core.git.diff_engine import diff_reports, detect_regression
    from contextor.core.reporting_layer.git_report import build_global_git_section

    all_collisions = collisions if collisions is not None else validate_name_collisions(modules)
    hotspots = detect_hotspots(graph.hard_edges)

    report_header = build_report_header(root_path, data_source="global")

    summary_data = generate_summary_report(
        metrics,
        cycles,
        debt,
        collisions=all_collisions,
        hotspots=hotspots,
        skipped_files=skipped_files,
        report_header=report_header,
        layer_index=layer_index,
    )

    structure_data = generate_structure_report(graph.hard_edges, graph.soft_edges)

    if log:
        log("Generating name collisions report...")
    collisions_data = generate_collisions_report(modules, precomputed=all_collisions)

    if log:
        log("Generating artifact usage report...")
    artifact_data = generate_artifact_usage_report(
        modules, root_path, runtime, progress_callback=progress_callback
    )
    artifact_data["debug_info"] = {
        "module_count": len(modules),
        "root_path": root_path,
        "timestamp": datetime.now().isoformat(),
    }
    artifact_data["report_header"] = {**report_header, "data_source": "artifacts"}

    usage_sidecar = artifact_data.pop("_usage_sidecar", {})

    if log:
        log("Generating compact version of artifacts report...")
    
    from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
    registry = PersistentIdentityRegistry(root_path)
    
    with registry.transaction():
        # Sync with workspace to handle deletions/orphans
        current_modules = set(modules.keys())
        current_artifacts = set(artifact_data.get("artifacts", {}).keys())
        registry.sync_with_workspace(current_modules, current_artifacts)
        registry.run_garbage_collector()
        
        index_dict = IndexDictionary(registry)
        compact_artifact_data = compact_artifact_report(artifact_data, index_dict)

    if log:
        log("Generating graph analytics report...")
    graph_analytics_data = generate_graph_analytics_report(
        artifact_data=artifact_data,
        hard_edges=graph.hard_edges,
        soft_edges=graph.soft_edges,
        modules=modules,
        index_dict=index_dict,
        scope="global",
    )

    sanity_warnings = _sanity_check_reports(summary_data, artifact_data, compact_artifact_data)
    if sanity_warnings:
        summary_data["sanity_warnings"] = sanity_warnings
        if log:
            for w in sanity_warnings:
                log(f"[SANITY] {w}")

    layer_index_data = []
    layer_reports_payloads = []
    if not layer_index:
        top_layers = set(m.split('.')[0] for m in modules.keys())
        for layer in top_layers:
            layer_path = Path(root_path) / layer
            if not layer_path.is_dir():
                continue
            try:
                layer_sliced = slice_report_for_layer(
                    layer_path=str(layer_path),
                    root_path=root_path,
                    global_metrics=metrics,
                    global_structure=structure_data,
                    global_summary=summary_data,
                    global_artifacts=artifact_data,
                    global_compact_artifacts=compact_artifact_data,
                    global_hotspots=hotspots,
                    global_cycles=cycles,
                    global_collisions=all_collisions,
                    global_skipped_files=skipped_files,
                    report_header=report_header,
                    index_dict=index_dict,
                )
                
                layer_status = execute_layer_pipeline(repo_name, layer, layer_sliced, log=log, datestamp=datestamp)
                layer_index_data.append(layer_status)
                layer_reports_payloads.append((layer, layer_sliced, layer_status))
            except Exception as e:
                if log:
                    log(f"[WARNING] Failed to generate layer reports for {layer}: {e}")

        if layer_index_data:
            summary_data["layer_index"] = sorted(layer_index_data, key=lambda x: x.get("layer", ""))

    repo_state_info = {"is_git_repo": is_git_repo(root_path)}
    if repo_state_info["is_git_repo"]:
        repo_state_info["commit_sha"] = get_current_commit(root_path)

    suffix = f"_{datestamp}" if datestamp else ""
    summary_pattern = os.path.join("output", f"{repo_name}_summary*.json")
    existing_summaries = glob.glob(summary_pattern)
    previous_header = None
    diff_stats = None
    regression = "UNCHANGED"
    diff_report = None

    existing_summaries.sort(reverse=True)
    if existing_summaries:
        try:
            with open(existing_summaries[0], "r", encoding="utf-8") as f:
                old_summary = json.load(f)
            previous_header = old_summary.get("report_header")
            diff_stats = diff_reports(old_summary, summary_data)
            regression = detect_regression(diff_stats)
            
            diff_report = {
                "report_diff": {
                    "previous_report": os.path.basename(existing_summaries[0]),
                    "current_report": f"{repo_name}_summary{suffix}.json",
                    "changes": diff_stats,
                    "status": regression
                }
            }
        except Exception as e:
            if log:
                log(f"[WARNING] Failed to load or diff previous summary: {e}")

    git_section = build_global_git_section(
        report_header, previous_header, diff_stats, repo_state_info, regression
    )
    summary_data["git_changes"] = git_section
    
    from .io_manager import write_global_reports, write_layer_reports
    
    for layer, layer_sliced, layer_status in layer_reports_payloads:
        if layer_status["computation_mode"] == "full":
            layer_dir = f"{repo_name}_high_risk_layers_{datestamp}" if datestamp else f"{repo_name}_high_risk_layers"
            write_layer_reports(repo_name, layer, layer_sliced, log=log, datestamp=datestamp, layer_output_dir=layer_dir)
            
    reports_data = {
        "summary": summary_data,
        "structure": structure_data,
        "collisions": collisions_data,
        "artifacts": artifact_data,
        "artifacts_compact": compact_artifact_data,
        "usage_sidecar": usage_sidecar,
        "graph_analytics": graph_analytics_data,
        "diff_report": diff_report
    }
    
    write_global_reports(reports_data, repo_name, datestamp=datestamp, log=log)
    
    if log:
        log("All reports have been successfully generated and saved.")

    high_risk_layers = [layer["layer"] for layer in layer_index_data if layer.get("computation_mode") == "full"] if not layer_index else []

    summary_path = f"output/{repo_name}_summary{suffix}.json"
    structure_path = f"output/{repo_name}_structure{suffix}.json"
    collisions_path = f"output/{repo_name}_name_collisions{suffix}.json"
    artifacts_path = f"output/{repo_name}_artifacts{suffix}.json"
    artifacts_compact_path = f"output/{repo_name}_artifacts_compact{suffix}.json"
    artifacts_usage_path = f"output/{repo_name}_artifacts_usage{suffix}.json"

    return {
        "saved": True,
        "repo": repo_name,
        "high_risk_layers": high_risk_layers,
        "files": [
            summary_path,
            structure_path,
            collisions_path,
            artifacts_path,
            artifacts_compact_path,
            artifacts_usage_path,
        ],
        "reports": ["summary", "structure", "collisions", "artifacts", "artifacts_compact", "artifacts_usage"],
        "_report_header": report_header,
        "_hotspots": hotspots,
        "_cycles": cycles,
        "_collisions": all_collisions,
        "_summary_data": summary_data,
        "_artifact_data": artifact_data,
        "_compact_artifact_data": compact_artifact_data,
    }
