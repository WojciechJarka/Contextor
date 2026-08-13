"""
contextor/core/reporting_engine/pipeline.py

REPORT PIPELINE ORCHESTRATOR

Coordinates generation of:
- summary report
- structure report
- collisions report
- full artifact usage report
- compact artifact usage report
- graph analytics report
- layer reports
- git metadata
- incremental analysis state

This module orchestrates report generation.
It does not perform AST analysis or graph analysis itself.
"""

from __future__ import annotations

from pathlib import Path

# ==========================================================
# GLOBAL PIPELINE
# ==========================================================

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
    trie: dict | None = None,
    package_root: str = "",
):
    """
    Execute the complete global report pipeline.

    The full artifact report is the source of truth.

    The compact artifact report is derived from it.

    Graph analytics is also derived from the full artifact report
    and the graph structure. It never consumes the compact report
    as its analytical source.

    PersistentIdentityRegistry is the single authority for module
    and artifact identity.
    """
    if log:
        log(
            "Starting sequential report generation..."
        )

    # ------------------------------------------------------
    # IMPORTS
    # ------------------------------------------------------

    from contextor.core.analysis.state_manager import (
        AnalysisResult,
        FileStateManager,
    )
    from contextor.core.git.repo_state import (
        get_current_commit,
        is_git_repo,
    )
    from contextor.core.hotspots import detect_hotspots
    from contextor.core.paths import repo_cache_dir
    from contextor.core.reporting_layer.git_report import (
        build_global_git_section,
    )
    from contextor.core.validator.collisions import (
        validate_name_collisions,
    )

    from .generators import (
        _sanity_check_reports,
        generate_collisions_report,
        generate_structure_report,
        generate_summary_report,
        slice_report_for_layer,
    )
    from .artifact_pipeline import build_artifact_pipeline
    from .header import build_report_header
    from .io_manager import (
        write_global_reports,
        write_layer_reports,
    )
    from .layer_pipeline import execute_layer_pipeline

    # ------------------------------------------------------
    # BASIC GRAPH / VALIDATION DATA
    # ------------------------------------------------------

    all_collisions = (
        collisions
        if collisions is not None
        else validate_name_collisions(modules)
    )

    hotspots = detect_hotspots(
        graph.hard_edges
    )

    report_header = build_report_header(
        root_path,
        data_source="global",
    )

    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # STRUCTURE
    # ------------------------------------------------------

    structure_data = generate_structure_report(
        graph.hard_edges,
        graph.soft_edges,
    )

    # ------------------------------------------------------
    # COLLISIONS
    # ------------------------------------------------------

    if log:
        log(
            "Generating name collisions report..."
        )

    collisions_data = generate_collisions_report(
        modules,
        precomputed=all_collisions,
    )

    artifact_bundle = build_artifact_pipeline(
        modules=modules,
        root_path=root_path,
        runtime=runtime,
        report_header=report_header,
        structure_data=structure_data,
        hard_edges=graph.hard_edges,
        soft_edges=graph.soft_edges,
        progress_callback=progress_callback,
        log=log,
    )
    artifact_data = artifact_bundle.artifact_data
    usage_sidecar = artifact_bundle.usage_sidecar
    index_dict = artifact_bundle.index_dict
    compact_artifact_data = artifact_bundle.compact_artifact_data
    compact_structure_data = artifact_bundle.compact_structure_data
    graph_analytics_data = artifact_bundle.graph_analytics_data

    # ------------------------------------------------------
    # SANITY CHECK
    # ------------------------------------------------------

    sanity_warnings = _sanity_check_reports(
        summary_data,
        artifact_data,
        compact_artifact_data,
    )

    if sanity_warnings:
        summary_data["sanity_warnings"] = (
            sanity_warnings
        )

        if log:
            for warning in sanity_warnings:
                log(
                    f"[SANITY] {warning}"
                )

    # ------------------------------------------------------
    # LAYER REPORTS
    # ------------------------------------------------------

    layer_index_data: list[dict] = []
    layer_reports_payloads: list[
        tuple[str, dict, dict]
    ] = []

    if not layer_index:

        top_layers = sorted(
            {
                module_id.split(".")[0]
                for module_id in modules.keys()
            }
        )

        for layer in top_layers:
            layer_path = (
                Path(root_path) / layer
            )

            if not layer_path.is_dir():
                continue

            try:
                layer_sliced = (
                    slice_report_for_layer(
                        layer_path=str(
                            layer_path
                        ),
                        root_path=root_path,
                        global_metrics=metrics,
                        global_structure=structure_data,
                        global_summary=summary_data,
                        global_artifacts=artifact_data,
                        global_compact_artifacts=(
                            compact_artifact_data
                        ),
                        global_hotspots=hotspots,
                        global_cycles=cycles,
                        global_collisions=(
                            all_collisions
                        ),
                        global_skipped_files=(
                            skipped_files
                        ),
                        report_header=report_header,
                        index_dict=index_dict,
                    )
                )

                # Ensure the layer pipeline sees the same
                # persistent identity dictionary.
                layer_sliced["_index_dict"] = (
                    index_dict
                )

                # P0-3: Pass the full global artifact report so the
                # layer pipeline can compute visibility from the
                # project-wide consumer graph.
                layer_sliced["_global_artifact_data"] = (
                    artifact_data
                )

                # If slicing preserved the full artifact
                # report under "artifacts", it remains the
                # analytical source of truth.
                layer_status = (
                    execute_layer_pipeline(
                        repo_name,
                        layer,
                        layer_sliced,
                        log=log,
                        datestamp=datestamp,
                    )
                )

                layer_index_data.append(
                    layer_status
                )

                layer_reports_payloads.append(
                    (
                        layer,
                        layer_sliced,
                        layer_status,
                    )
                )

            except Exception as exc:
                if log:
                    log(
                        "[WARNING] Failed to generate "
                        f"layer reports for {layer}: "
                        f"{type(exc).__name__}: {exc}"
                    )

        if layer_index_data:
            summary_data["layer_index"] = sorted(
                layer_index_data,
                key=lambda item: item.get(
                    "layer",
                    "",
                ),
            )

    # ------------------------------------------------------
    # GIT STATE
    # ------------------------------------------------------

    repo_state_info = {
        "is_git_repo": is_git_repo(
            root_path
        )
    }

    if repo_state_info["is_git_repo"]:
        repo_state_info["commit_sha"] = (
            get_current_commit(root_path)
        )

    git_section = build_global_git_section(
        report_header,
        repo_state_info,
    )

    summary_data["git_changes"] = (
        git_section
    )

    # ------------------------------------------------------
    # WRITE HIGH-RISK LAYER REPORTS
    # ------------------------------------------------------

    for (
        layer,
        layer_sliced,
        layer_status,
    ) in layer_reports_payloads:

        if (
            layer_status.get(
                "computation_mode"
            )
            == "full"
        ):
            layer_dir = (
                f"{repo_name}_high_risk_layers"
            )

            write_layer_reports(
                repo_name,
                layer,
                layer_sliced,
                datestamp=datestamp,
                log=log,
                layer_output_dir=layer_dir,
            )

    # ------------------------------------------------------
    # GLOBAL REPORT PAYLOAD
    # ------------------------------------------------------

    # P0-1: Build the public artifact payload without the private
    # _usage_sidecar key.  We construct a shallow copy so that
    # artifact_data itself (with its sidecar) remains intact for any
    # downstream consumer that still needs it after this point.
    artifact_data_public = {
        k: v
        for k, v in artifact_data.items()
        if k != "_usage_sidecar"
    }

    reports_data = {
        "summary": summary_data,
        "structure": compact_structure_data,
        "collisions": collisions_data,
        "artifacts": artifact_data_public,
        "artifacts_compact": (
            compact_artifact_data
        ),
        "usage_sidecar": usage_sidecar,
        "graph_analytics": (
            graph_analytics_data
        ),
    }

    # ------------------------------------------------------
    # WRITE GLOBAL REPORTS
    # ------------------------------------------------------

    write_global_reports(
        reports_data,
        repo_name,
        datestamp=datestamp,
        log=log,
    )

    if log:
        log(
            "All reports have been successfully "
            "generated and saved."
        )

    # ------------------------------------------------------
    # INCREMENTAL CACHE
    # ------------------------------------------------------

    if log:
        log(
            "Initializing incremental cache..."
        )

    state_mgr = FileStateManager(
        str(
            repo_cache_dir(
                root_path
            )
        )
    )

    for module_id, module in modules.items():
        absolute_path = getattr(
            module,
            "absolute_path",
            None,
        )

        if absolute_path:
            state_mgr.update_state(
                absolute_path
            )

    # datestamp keeps engine_state and file_state
    # synchronized.
    state_mgr.save(
        datestamp or ""
    )

    # ------------------------------------------------------
    # RETURNED FILE PATHS
    # ------------------------------------------------------

    high_risk_layers = (
        [
            layer["layer"]
            for layer in layer_index_data
            if layer.get(
                "computation_mode"
            )
            == "full"
        ]
        if not layer_index
        else []
    )

    summary_path = (
        f"output/{repo_name}_summary.json"
    )

    structure_path = (
        f"output/{repo_name}_structure.json"
    )

    collisions_path = (
        f"output/{repo_name}_name_collisions.json"
    )

    artifacts_path = (
        f"output/{repo_name}_artifacts.json"
    )

    artifacts_compact_path = (
        f"output/{repo_name}_artifacts_compact.json"
    )

    artifacts_usage_path = (
        f"output/{repo_name}_artifacts_usage.json"
    )

    # ------------------------------------------------------
    # ANALYSIS RESULT
    # ------------------------------------------------------

    analysis_result = AnalysisResult(
        repo_name=repo_name,
        root_path=root_path,
        modules=modules,
        graph=graph,
        metrics=metrics,
        cycles=cycles,
        debt=debt,
        collisions=(
            all_collisions
            if all_collisions is not None
            else []
        ),
        hotspots=hotspots,
        layer_index=layer_index_data,
        artifacts=artifact_data.get(
            "_module_artifacts",
            {},
        ),
        compact_artifacts=(
            compact_artifact_data
        ),
        summary_data=summary_data,
        report_header=report_header,
        trie=trie,
        package_root=package_root,
    )

    # ------------------------------------------------------
    # RESULT
    # ------------------------------------------------------

    return {
        "saved": True,
        "repo": repo_name,
        "high_risk_layers": (
            high_risk_layers
        ),
        "files": [
            summary_path,
            structure_path,
            collisions_path,
            artifacts_path,
            artifacts_compact_path,
            artifacts_usage_path,
        ],
        "reports": [
            "summary",
            "structure",
            "collisions",
            "artifacts",
            "artifacts_compact",
            "artifacts_usage",
            "graph_analytics",
        ],
        "_report_header": report_header,
        "_hotspots": hotspots,
        "_cycles": cycles,
        "_collisions": all_collisions,
        "_summary_data": summary_data,
        "_artifact_data": artifact_data,
        "_compact_artifact_data": (
            compact_artifact_data
        ),
        "_graph_analytics_data": (
            graph_analytics_data
        ),
        "_analysis_result": analysis_result,
    }
