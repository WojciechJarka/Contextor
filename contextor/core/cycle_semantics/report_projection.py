"""Historical FULL report projection for cycle semantics.

This module consumes canonical immutable evidence.
It performs no source reads, AST parsing, graph
construction, LIVE access or persistence.

A completed report is not an atomic certificate
of the subsequently published LIVE revision.
"""

from __future__ import annotations

from contextor.core.errors import AnalysisCancelled

from .contracts import CycleSemanticsSnapshot
from .public_projection import project_cycle_semantics


CYCLE_SEMANTICS_REPORT_SCHEMA_VERSION = "1.0.0"

REPORT_LIVE_BINDING_STATUS = (
    "UNVERIFIED_REPORT_VS_CANONICAL_LIVE"
)


def build_cycle_semantics_report(
    snapshot: CycleSemanticsSnapshot | None,
    freshness: str,
    invalidation_reason: str | None,
    *,
    report_header: dict,
) -> dict:
    """Project one FULL semantic result as historical evidence."""

    if type(report_header) is not dict:
        raise TypeError(
            "report_header must be a dictionary"
        )

    if freshness not in (
        "fresh",
        "stale",
        "deferred",
    ):
        raise ValueError(
            "Unsupported semantic freshness state"
        )

    if snapshot is not None and type(snapshot) is not (
        CycleSemanticsSnapshot
    ):
        raise TypeError(
            "Expected CycleSemanticsSnapshot"
        )

    if snapshot is None and (
        freshness != "deferred"
        or invalidation_reason is not None
    ):
        raise ValueError(
            "Missing semantic evidence cannot be certified"
        )

    if (
        freshness == "fresh"
        and invalidation_reason is not None
    ):
        raise ValueError(
            "Fresh semantic evidence cannot have an invalidation reason"
        )

    evidence = {
        "available": snapshot is not None,
        "freshness_at_report_generation": freshness,
        "invalidation_reason": invalidation_reason,
        "snapshot_schema_version": (
            snapshot.schema_version
            if snapshot is not None
            else None
        ),
        "graph_sha256": (
            snapshot.graph_sha256
            if snapshot is not None
            else None
        ),
        "cyclic_module_count": (
            snapshot.cyclic_module_count
            if snapshot is not None
            else None
        ),
        "observed_source_count": (
            snapshot.observed_source_count
            if snapshot is not None
            else None
        ),
        "unobserved_source_count": (
            snapshot.unobserved_source_count
            if snapshot is not None
            else None
        ),
        "coverage_status": (
            snapshot.coverage_status
            if snapshot is not None
            else None
        ),
        "source_snapshot_binding": (
            snapshot.source_snapshot_binding
            if snapshot is not None
            else None
        ),
        "runtime_execution_status": (
            snapshot.runtime_execution_status
            if snapshot is not None
            else None
        ),
        "source_fingerprints": (
            [
                {
                    "module_id": module,
                    "sha256": digest,
                }
                for module, digest in (
                    snapshot.observed_source_fingerprints
                )
            ]
            if snapshot is not None
            else []
        ),
        "source_issues": (
            [
                {
                    "module_id": module,
                    "reason": reason,
                }
                for module, reason in snapshot.source_issues
            ]
            if snapshot is not None
            else []
        ),
    }

    result = {
        "schema_version": (
            CYCLE_SEMANTICS_REPORT_SCHEMA_VERSION
        ),
        "report_header": dict(report_header),
        "publication_binding": {
            "status": REPORT_LIVE_BINDING_STATUS,
            "canonical_revision": None,
            "live_revision": None,
        },
        "status": (
            "unavailable"
            if snapshot is None
            else "stale"
            if freshness == "stale"
            else "deferred"
            if freshness == "deferred"
            else "partial"
            if snapshot.coverage_status
            == "PARTIAL_SOURCE_EVIDENCE"
            else "ok"
        ),
        "semantic_evidence": evidence,
        "projection": None,
        "projection_error": None,
    }

    if snapshot is None:
        return result

    try:
        result["projection"] = project_cycle_semantics(
            snapshot.import_sites,
            snapshot.conditional_discovery,
        )
    except AnalysisCancelled:
        raise
    except Exception as exc:
        result["status"] = "projection_unavailable"
        result["projection_error"] = (
            type(exc).__name__
        )

    return result
