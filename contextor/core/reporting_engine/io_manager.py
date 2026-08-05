import os
import json
import glob
from datetime import datetime
from typing import Any
from pathlib import Path
from contextor.core.analysis.git_context import collect_git_context
from contextor.core.git.repo_state import is_git_repo, get_current_commit
from contextor.core.git.diff_engine import diff_reports, detect_regression
from contextor.core.reporting_layer.git_report import build_global_git_section
from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report
from contextor.core.reporting_layer.artifact_usage_report_compact import compact_artifact_report, save_compact_artifact_report
from contextor.core.hotspots import detect_hotspots
from contextor.core.validator.collisions import validate_name_collisions
from .formatting import save_json
from .generators import _sanity_check_reports, generate_summary_report, generate_structure_report, generate_collisions_report, slice_report_for_layer

def _build_report_header(root_path: str, data_source: str) -> dict:
    """
    Builds a stable report header present in every generated report.
    Provides commit SHA, branch, tool version, and data_source tag so
    a consumer (LLM or human) can unambiguously identify where a given
    report comes from and how to reconcile it with others.
    """
    try:
        import importlib.metadata
        tool_version = importlib.metadata.version("contextor")
    except Exception:
        tool_version = "unknown"

    # collect_git_context returns per-file data; we call it on root to get
    # repo-level commit / branch (uses git log on the directory itself).
    git_info = collect_git_context(root_path, root_path)

    # Try to read branch name separately (git_context only returns commit date).
    branch = None
    try:
        import subprocess
        from pathlib import Path
        p = Path(root_path)
        if (p / ".git").exists():
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(p), capture_output=True, text=True, check=True,
            )
            branch = result.stdout.strip() or None
            result2 = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(p), capture_output=True, text=True, check=True,
            )
            commit_sha = result2.stdout.strip()[:12] or None
        else:
            commit_sha = None
    except Exception:
        commit_sha = None

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "commit_sha": commit_sha,
        "branch": branch,
        "tool_version": tool_version,
        "data_source": data_source,
    }


def _save_usage_sidecar(usage_sidecar: dict, path: str, log=None) -> None:
    """
    Saves the usage sidecar (artifact_id -> usage dict with line numbers)
    extracted from the artifact report as a separate on-demand file.
    """
    save_json(usage_sidecar, path, log=log, label="artifacts usage sidecar")


def save_layer_reports(
    repo_name: str, layer_name: str, layer_reports: dict[str, dict[str, Any]], log=None, datestamp: str | None = None, layer_output_dir: str | None = None
) -> dict:
    """
    Saves all layer-specific report files and returns a status summary dict
    for aggregation into the global summary's ``layer_index``.
    """
    base_dir = f"output/{layer_output_dir}" if layer_output_dir else "output"
    import os
    os.makedirs(base_dir, exist_ok=True)
    suffix = f"_{datestamp}" if datestamp else ""
    prefix = f"{base_dir}/{repo_name}_{layer_name}"
    save_json(
        layer_reports["summary"],
        f"{prefix}_summary{suffix}.json",
        log=log,
        label=f"layer report [{layer_name}] - summary",
    )
    save_json(
        layer_reports["structure"],
        f"{prefix}_structure{suffix}.json",
        log=log,
        label=f"layer report [{layer_name}] - structure",
    )
    save_json(
        layer_reports["metrics"],
        f"{prefix}_metrics{suffix}.json",
        log=log,
        label=f"layer report [{layer_name}] - metrics",
    )
    save_json(
        layer_reports["artifacts"],
        f"{prefix}_artifacts{suffix}.json",
        log=log,
        label=f"layer report [{layer_name}] - artifacts",
    )
    save_json(
        layer_reports["artifacts_compact"],
        f"{prefix}_artifacts_compact{suffix}.json",
        log=log,
        label=f"layer report [{layer_name}] - artifacts (compact)",
    )

    summary = layer_reports["summary"]
    return {
        "layer": layer_name,
        "module_count": summary.get("layer_module_count", 0),
        "status": summary.get("status", "UNKNOWN"),
        "cycles_count": summary.get("layer_cycles_count", 0),
        "hotspot_count": len(summary.get("hotspots", [])),
        "computation_mode": summary.get("computation_mode", "filtered"),
    }


def save_all_reports(
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
    """
    Generate and save all reports for the repository.
    """
    if log:
        log("Starting sequential report saving...")

    all_collisions = collisions if collisions is not None else validate_name_collisions(modules)
    hotspots = detect_hotspots(graph.hard_edges)

    # Build report_header once; passed to all sub-reports for consistency (P2)
    report_header = _build_report_header(root_path, data_source="global")

    suffix = f"_{datestamp}" if datestamp else ""
    summary_path = f"output/{repo_name}_summary{suffix}.json"
    structure_path = f"output/{repo_name}_structure{suffix}.json"
    collisions_path = f"output/{repo_name}_name_collisions{suffix}.json"
    artifacts_path = f"output/{repo_name}_artifacts{suffix}.json"
    artifacts_compact_path = f"output/{repo_name}_artifacts_compact{suffix}.json"
    artifacts_usage_path = f"output/{repo_name}_artifacts_usage{suffix}.json"

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

    # summary_data is saved AFTER sanity checks below

    structure_data = generate_structure_report(graph.hard_edges, graph.soft_edges)
    save_json(structure_data, structure_path, log=log, label="graph structure report")

    if log:
        log("Generating name collisions report...")
    collisions_data = generate_collisions_report(modules, precomputed=all_collisions)
    save_json(collisions_data, collisions_path, log=log, label="name collisions report")

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

    # Extract and save usage sidecar BEFORE stripping _usage_sidecar from the report (P1b)
    usage_sidecar = artifact_data.pop("_usage_sidecar", {})
    _save_usage_sidecar(usage_sidecar, artifacts_usage_path, log=log)

    save_json(artifact_data, artifacts_path, log=log, label="artifacts report")

    if log:
        log("Generating compact version of artifacts report...")
    compact_artifact_data = compact_artifact_report(artifact_data)
    save_compact_artifact_report(compact_artifact_data, artifacts_compact_path)

    sanity_warnings = _sanity_check_reports(summary_data, artifact_data, compact_artifact_data)
    if sanity_warnings:
        summary_data["sanity_warnings"] = sanity_warnings
        if log:
            for w in sanity_warnings:
                log(f"[SANITY] {w}")

    # Generate layer reports (P3d)
    if not layer_index:
        layer_index_data = []
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
                )
                summary = layer_sliced["summary"]
                layer_status = {
                    "layer": layer,
                    "module_count": summary.get("layer_module_count", 0),
                    "status": summary.get("status", "UNKNOWN"),
                    "cycles_count": summary.get("layer_cycles_count", 0),
                    "hotspot_count": len(summary.get("hotspots", [])),
                    "computation_mode": summary.get("computation_mode", "filtered"),
                }
                if layer_status["computation_mode"] == "full":
                    # Only save files if layer triggered deep computation
                    layer_dir = f"{repo_name}_high_risk_layers_{datestamp}" if datestamp else f"{repo_name}_high_risk_layers"
                    save_layer_reports(
                        repo_name=repo_name,
                        layer_name=layer,
                        layer_reports=layer_sliced,
                        log=log,
                        datestamp=datestamp,
                        layer_output_dir=layer_dir,
                    )
                layer_index_data.append(layer_status)
            except Exception as e:
                if log:
                    log(f"[WARNING] Failed to generate layer reports for {layer}: {e}")

        if layer_index_data:
            summary_data["layer_index"] = sorted(layer_index_data, key=lambda x: x.get("layer", ""))

    # Git & Diff Integration (Needs to be here so summary_data has layer_index)
    repo_state_info = {"is_git_repo": is_git_repo(root_path)}
    if repo_state_info["is_git_repo"]:
        repo_state_info["commit_sha"] = get_current_commit(root_path)

    # Find previous summary report
    import os
    summary_pattern = os.path.join("output", f"{repo_name}_summary*.json")
    existing_summaries = glob.glob(summary_pattern)
    previous_summary = None
    previous_header = None
    diff_stats = None
    regression = "UNCHANGED"

    # Sort files to find the latest (excluding the one we are about to save)
    # The suffix contains datestamp, so alphabetical sort works well.
    existing_summaries.sort(reverse=True)
    if existing_summaries:
        # Assuming the newest existing one is the previous report
        try:
            with open(existing_summaries[0], "r", encoding="utf-8") as f:
                old_summary = json.load(f)
            previous_header = old_summary.get("report_header")
            diff_stats = diff_reports(old_summary, summary_data)
            regression = detect_regression(diff_stats)
            
            # Save diff report
            diff_report_path = f"output/{repo_name}_report_diff{suffix}.json"
            save_json({
                "report_diff": {
                    "previous_report": os.path.basename(existing_summaries[0]),
                    "current_report": os.path.basename(summary_path),
                    "changes": diff_stats,
                    "status": regression
                }
            }, diff_report_path, log=log, label="report diff")
            
        except Exception as e:
            if log:
                log(f"[WARNING] Failed to load or diff previous summary: {e}")

    git_section = build_global_git_section(
        report_header, previous_header, diff_stats, repo_state_info, regression
    )
    summary_data["git_changes"] = git_section

    save_json(summary_data, summary_path, log=log, label="summary report")

    if log:
        log("All reports have been successfully saved.")

    high_risk_layers = [layer["layer"] for layer in layer_index_data if layer.get("computation_mode") == "full"] if not layer_index else []

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
        # Expose for callers that aggregate layer reports
        "_report_header": report_header,
        "_hotspots": hotspots,
        "_cycles": cycles,
        "_collisions": all_collisions,
        "_summary_data": summary_data,
        "_artifact_data": artifact_data,
        "_compact_artifact_data": compact_artifact_data,
    }


