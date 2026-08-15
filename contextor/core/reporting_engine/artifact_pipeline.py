"""Artifact, identity, compaction, and analytics stage of reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contextor.core.errors import checkpoint
from contextor.core.program_log import log_program_event

from contextor.core.reporting_layer.artifact_usage_report import (
    collect_qualified_artifact_identities,
    generate_artifact_usage_report,
)
from contextor.core.reporting_layer.artifact_usage_report_compact import (
    compact_artifact_report,
)

from .dictionary import IndexDictionary
from .graph_analytics import generate_graph_analytics_report
from .persistent_registry import PersistentIdentityRegistry
from .structure_generator import compact_structure_report


@dataclass(frozen=True)
class ArtifactPipelineResult:
    """Values produced together from one full artifact source of truth."""

    artifact_data: dict
    usage_sidecar: dict
    index_dict: IndexDictionary
    compact_artifact_data: dict
    compact_structure_data: dict
    graph_analytics_data: dict


def build_artifact_pipeline(
    *,
    modules: dict,
    root_path: str,
    runtime: dict,
    report_header: dict,
    structure_data: dict,
    hard_edges: dict,
    soft_edges: dict,
    progress_callback=None,
    log=None,
) -> ArtifactPipelineResult:
    """Build mutually consistent artifact and graph report representations."""
    log_program_event("REPORT", "artifact pipeline start", modules=len(modules))
    if log:
        log("Generating artifact usage report...")

    artifact_data = generate_artifact_usage_report(
        modules,
        root_path,
        runtime,
        progress_callback=progress_callback,
    )
    artifact_data["debug_info"] = {
        "module_count": len(modules),
        "root_path": root_path,
        "timestamp": datetime.now().isoformat(),
    }
    artifact_data["report_header"] = {
        **report_header,
        "data_source": "artifacts",
    }
    usage_sidecar = artifact_data.get("_usage_sidecar", {})

    checkpoint(progress_callback, "Compacting artifact and structure reports")

    if log:
        log("Generating compact version of artifacts report...")

    registry = PersistentIdentityRegistry(root_path)
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules),
            collect_qualified_artifact_identities(
                artifact_data.get("_module_artifacts", {})
            ),
        )
        registry.run_garbage_collector()
        index_dict = IndexDictionary(registry)
        compact_artifact_data = compact_artifact_report(
            artifact_data,
            index_dict,
        )
        compact_structure_data = compact_structure_report(
            structure_data,
            index_dict,
        )

    if log:
        log("Generating graph analytics report...")

    checkpoint(progress_callback, "Starting graph analytics")

    graph_analytics_data = generate_graph_analytics_report(
        artifact_data=artifact_data,
        hard_edges=hard_edges,
        soft_edges=soft_edges,
        modules=modules,
        index_dict=index_dict,
        scope="global",
        progress_callback=progress_callback,
    )
    log_program_event(
        "REPORT",
        "artifact pipeline complete",
        artifacts=len(artifact_data.get("artifacts", {})),
    )
    return ArtifactPipelineResult(
        artifact_data=artifact_data,
        usage_sidecar=usage_sidecar,
        index_dict=index_dict,
        compact_artifact_data=compact_artifact_data,
        compact_structure_data=compact_structure_data,
        graph_analytics_data=graph_analytics_data,
    )
