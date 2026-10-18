"""Pure, bounded views over canonical cycle-semantic evidence."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from contextor.core.cycle_semantics.activation_view import (
    analyze_cycle_activation_view,
)
from contextor.core.cycle_semantics.closure_witness import (
    analyze_single_edge_cycle_closures,
)
from contextor.core.cycle_semantics.contracts import (
    CycleSemanticsSnapshot,
)
from contextor.core.cycle_semantics.diagnostic_view import (
    build_cycle_evidence_digest,
)


_COMPONENT_FIELDS = (
    "members",
    "structural_kind",
    "diagnostic_category",
    "structural_edge_count",
    "matched_edge_count",
    "unresolved_edge_count",
    "direct_candidate_edge_count",
    "non_direct_candidate_edge_count",
    "direct_cyclic_component_count",
    "single_non_direct_closure_count",
    "multiple_non_direct_closure_count",
    "runtime_execution_status",
)

_OVERVIEW_EVIDENCE_FIELDS = (
    "available",
    "freshness_at_report_generation",
    "coverage_status",
    "graph_sha256",
    "cyclic_module_count",
    "observed_source_count",
    "unobserved_source_count",
    "source_issues",
    "source_snapshot_binding",
    "runtime_execution_status",
)

_OVERVIEW_PROJECTION_FIELDS = (
    "schema_version",
    "evidence_scope",
    "source_snapshot_binding",
    "canonical_graph_revision",
    "canonical_graph_revision_status",
    "runtime_execution_status",
    "selection_coverage_status",
    "selection_scope",
    "unavailable_source_modules",
    "unresolved_lexical_edge_count",
    "examined_outgoing_count",
)


def project_historical_cycle_semantics(
    report: Any,
    *,
    view: str,
    component: str | None,
) -> tuple[Any, dict[str, Any] | None]:
    """Return a lossless or reduced historical report without mutation."""

    if view == "full":
        return report, None

    if not isinstance(report, dict) or report.get("available") is False:
        return deepcopy(report), None

    projection = report.get("projection")
    selected_component: dict[str, Any] | None = None
    selection_metadata: dict[str, Any] | None = None

    if component is not None:
        projection_summary = (
            projection.get("summary")
            if isinstance(projection, dict)
            else None
        )
        source_components = (
            projection.get("components")
            if isinstance(projection, dict)
            else None
        )
        components = (
            source_components
            if isinstance(source_components, list)
            else []
        )
        matching = [
            row
            for row in components
            if isinstance(row, dict)
            and isinstance(row.get("members"), list)
            and component in row["members"]
        ]
        projection_truncated = bool(
            isinstance(projection_summary, dict)
            and projection_summary.get("components_truncated") is True
        )
        if not matching:
            return report, {
                "status": "error",
                "error": "component_not_in_projection",
                "component": component,
                "projection_truncated": projection_truncated,
                "cyclic_scc_total": (
                    projection_summary.get("cyclic_scc_total")
                    if isinstance(projection_summary, dict)
                    else None
                ),
                "cyclic_scc_returned": len(components),
            }
        if len(matching) != 1:
            return report, {
                "status": "error",
                "error": "component_not_unique_in_projection",
                "component": component,
                "projection_truncated": projection_truncated,
                "cyclic_scc_total": (
                    projection_summary.get("cyclic_scc_total")
                    if isinstance(projection_summary, dict)
                    else None
                ),
                "cyclic_scc_returned": len(components),
            }
        selected_component = matching[0]
        total = (
            projection_summary.get("cyclic_scc_total")
            if isinstance(projection_summary, dict)
            else None
        )
        selection_metadata = {
            "component": component,
            "cyclic_scc_total": total,
            "components_returned": 1,
            "materialized_projection_components_returned": len(components),
            "materialized_projection_components_truncated": projection_truncated,
        }

    result = deepcopy(report)
    original_projection = result.get("projection")
    original_summary = (
        original_projection.get("summary")
        if isinstance(original_projection, dict)
        else None
    )
    original_components = (
        original_projection.get("components")
        if isinstance(original_projection, dict)
        else None
    )
    original_components = (
        original_components
        if isinstance(original_components, list)
        else []
    )
    original_truncated = bool(
        isinstance(original_summary, dict)
        and original_summary.get("components_truncated") is True
    )
    original_total = (
        original_summary.get("cyclic_scc_total")
        if isinstance(original_summary, dict)
        else None
    )

    if view == "diagnostic":
        evidence = result.get("semantic_evidence")
        fingerprints = (
            evidence.get("source_fingerprints")
            if isinstance(evidence, dict)
            else None
        )
        fingerprint_count = (
            len(fingerprints)
            if isinstance(fingerprints, list)
            else None
        )
        if isinstance(evidence, dict):
            evidence.pop("source_fingerprints", None)

        presentation = {
            "view": "diagnostic",
            "source_fingerprints_omitted": True,
            "source_fingerprint_count": fingerprint_count,
            "full_evidence_available": True,
        }
        if component is not None and selected_component is not None:
            result_projection = result.get("projection")
            if isinstance(result_projection, dict):
                result_projection["components"] = [
                    deepcopy(selected_component)
                ]
                summary = result_projection.get("summary")
                if isinstance(summary, dict):
                    summary["cyclic_scc_returned"] = 1
                    summary["components_truncated"] = (
                        original_truncated
                        or original_total != 1
                    )
            presentation["component_selection"] = selection_metadata
        result["presentation"] = presentation
        return result, None

    evidence = report.get("semantic_evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    projection = report.get("projection")
    projection = projection if isinstance(projection, dict) else None
    summary = (
        projection.get("summary")
        if projection is not None
        else None
    )
    summary = summary if isinstance(summary, dict) else {}

    visible_components = (
        projection.get("components", [])
        if projection is not None
        else []
    )
    visible_components = (
        visible_components
        if isinstance(visible_components, list)
        else []
    )
    if component is not None and selected_component is not None:
        visible_components = [selected_component]

    overview_components = [
        {
            field: deepcopy(row[field])
            for field in _COMPONENT_FIELDS
            if field in row
        }
        for row in visible_components
        if isinstance(row, dict)
    ]

    overview_projection = None
    if projection is not None:
        overview_projection = {
            field: projection[field]
            for field in _OVERVIEW_PROJECTION_FIELDS
            if field in projection
        }
        overview_projection["summary"] = {
            field: summary[field]
            for field in (
                "cyclic_scc_total",
                "cyclic_scc_returned",
                "components_truncated",
                "conditional_group_total",
                "conditional_witness_total",
            )
            if field in summary
        }
        if component is not None:
            overview_projection["summary"]["cyclic_scc_returned"] = 1
            overview_projection["summary"]["components_truncated"] = (
                original_truncated or original_total != 1
            )
        overview_projection["components"] = overview_components

    fingerprint_rows = evidence.get("source_fingerprints")
    presentation: dict[str, Any] = {
        "view": "overview",
        "source_fingerprints_omitted": True,
        "source_fingerprint_count": (
            len(fingerprint_rows)
            if isinstance(fingerprint_rows, list)
            else None
        ),
        "omitted_details": [
            "source_fingerprints",
            "lexical_source_site_details",
            "detailed_edges",
            "conditional_witness_chains",
        ],
        "full_evidence_available": True,
        "full_evidence_retrieval_path": (
            'get_project_architecture(fields=["cycle_semantics"], '
            'cycle_semantics_view="full")'
        ),
        "materialized_projection_components_truncated": original_truncated,
    }
    if component is not None:
        presentation["component_selection"] = selection_metadata

    result = {
        key: report[key]
        for key in (
            "schema_version",
            "status",
            "report_header",
            "publication_binding",
            "projection_error",
        )
        if key in report
    }
    result["semantic_evidence"] = {
        key: evidence[key]
        for key in _OVERVIEW_EVIDENCE_FIELDS
        if key in evidence
    }
    result["projection"] = overview_projection
    result["presentation"] = presentation
    return result, None


def live_cycle_semantic_diagnostics(
    state: Any,
    freshness: Any,
    *,
    engine: Any = None,
) -> dict[str, Any]:
    """Classify current canonical evidence behind its positive freshness gate."""

    canonical_revision = None
    if isinstance(freshness, dict):
        revision = freshness.get("canonical_revision")
        if type(revision) is int and revision >= 0:
            canonical_revision = revision

    runtime_status = "UNKNOWN_NOT_EVALUATED"

    def unavailable(status: str, reason: str, *, coverage: str | None = None):
        return {
            "status": status,
            "source": "live_canonical_state",
            "canonical_revision": canonical_revision,
            "cyclic_scc_count": None,
            "cyclic_module_count": None,
            "unguarded_direct_cyclic_scc_count": None,
            "non_direct_closure_scc_count": None,
            "unresolved_lexical_edge_count": None,
            "direct_candidate_attention_required": None,
            "coverage_status": coverage,
            "runtime_execution_status": runtime_status,
            "reason": reason,
        }

    if state is None:
        return unavailable("unavailable", "No canonical LIVE state is available.")

    if getattr(state, "resync_required", False):
        return unavailable("stale", "Canonical LIVE state requires resynchronization.")

    families = freshness.get("families") if isinstance(freshness, dict) else None
    family_status = (
        families.get("cycle_semantics")
        if isinstance(families, dict)
        else None
    )
    if family_status != "fresh":
        status = family_status if family_status in {
            "stale", "deferred", "unavailable",
        } else "unavailable"
        return unavailable(
            status,
            f"Current cycle-semantic family is {status}; positive freshness is required.",
        )

    canonical_state = freshness.get("canonical_state") if isinstance(freshness, dict) else None
    if canonical_state != "fresh":
        status = canonical_state if canonical_state in {
            "stale", "unavailable",
        } else "unavailable"
        return unavailable(
            status,
            f"Canonical state is {status}; semantic derivation requires a fresh canonical generation.",
        )

    if canonical_revision is None:
        return unavailable("unavailable", "Canonical revision is missing or invalid.")

    state_revision = getattr(state, "revision", None)
    engine_revision = getattr(engine, "revision", None) if engine is not None else None
    if (
        type(state_revision) is not int
        or state_revision != canonical_revision
        or (
            engine is not None
            and (
                type(engine_revision) is not int
                or engine_revision != canonical_revision
            )
        )
    ):
        return unavailable(
            "unavailable",
            "Canonical state, engine, and freshness revisions are incoherent.",
        )

    state_manager = getattr(engine, "state_manager", None) if engine is not None else None
    manager_revision = getattr(state_manager, "revision", None)
    if manager_revision is not None and (
        type(manager_revision) is not int
        or manager_revision != canonical_revision
    ):
        return unavailable(
            "unavailable",
            "Canonical state-manager generation does not match the LIVE revision.",
        )

    state_id = getattr(state, "state_id", None)
    manager_state_id = getattr(state_manager, "state_id", None)
    if (
        state_id is not None
        and manager_state_id is not None
        and state_id != manager_state_id
    ):
        return unavailable(
            "unavailable",
            "Canonical state and state-manager identities are incoherent.",
        )

    snapshot = getattr(state, "cycle_semantics", None)
    if type(snapshot) is not CycleSemanticsSnapshot:
        return unavailable(
            "unavailable",
            "Fresh cycle-semantic evidence is missing or has an invalid structure.",
        )

    if (
        snapshot.runtime_execution_status
        != "UNKNOWN_NOT_EVALUATED"
    ):
        return unavailable(
            "unavailable",
            "Cycle-semantic evidence has an unsupported runtime-execution status.",
            coverage=snapshot.coverage_status,
        )

    if snapshot.coverage_status not in {
        "FILESYSTEM_STABLE_NON_ATOMIC",
        "PARTIAL_SOURCE_EVIDENCE",
    }:
        return unavailable(
            "unavailable",
            "Cycle-semantic evidence has an unsupported coverage status.",
            coverage=snapshot.coverage_status,
        )

    activation = analyze_cycle_activation_view(snapshot.import_sites)
    closures = analyze_single_edge_cycle_closures(
        activation,
        snapshot.import_sites,
    )
    digest = build_cycle_evidence_digest(
        snapshot.import_sites,
        activation,
        closures,
    )

    components = digest.components
    structural_components = snapshot.import_sites.topology.cyclic_components
    if len(components) != len(structural_components):
        raise ValueError("Semantic component count does not match canonical topology")

    diagnosed_modules = tuple(sorted({
        member
        for component in components
        for member in component.members
    }))
    if diagnosed_modules != snapshot.cyclic_modules:
        raise ValueError("Semantic cyclic-module identities do not match the snapshot")

    direct_count = sum(
        component.category == "UNGUARDED_DIRECT_CYCLIC_SUBGRAPH"
        for component in components
    )
    non_direct_count = sum(
        component.category
        == "ACYCLIC_DIRECT_SUBGRAPH_WITH_SINGLE_EDGE_CLOSURES"
        for component in components
    )
    unresolved = snapshot.conditional_discovery.unresolved_lexical_edge_count
    if type(unresolved) is not int or unresolved < 0:
        raise ValueError("Unresolved lexical edge count is invalid")

    complete = snapshot.coverage_status == "FILESYSTEM_STABLE_NON_ATOMIC"
    status = "fresh" if complete else "partial"
    attention = (
        True
        if direct_count > 0
        else False
        if complete
        else None
    )
    reason = (
        None
        if complete
        else "Canonical semantic evidence has partial source coverage; absence of direct cycles is unproven."
    )

    return {
        "status": status,
        "source": "live_canonical_state",
        "canonical_revision": canonical_revision,
        "cyclic_scc_count": len(components),
        "cyclic_module_count": len(snapshot.cyclic_modules),
        "unguarded_direct_cyclic_scc_count": direct_count,
        "non_direct_closure_scc_count": non_direct_count,
        "unresolved_lexical_edge_count": unresolved,
        "direct_candidate_attention_required": attention,
        "coverage_status": snapshot.coverage_status,
        "runtime_execution_status": snapshot.runtime_execution_status,
        "reason": reason,
    }
