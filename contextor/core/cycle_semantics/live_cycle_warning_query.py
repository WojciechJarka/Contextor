"""Lock-scoped, read-only projection of canonical LIVE cycle warnings.

The owner obtains and reports its own generation identity. No caller
supplies a state, receipt, graph, or source capture. MODEL_PASS is a
restricted static-model claim, not a runtime safety certificate.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from typing import Any

from .contracts import fingerprint_hard_edges
from .cycle_warning_projection import project_installed_cycle_warnings
from .partial_scc_publication import CanonicalPartialSCCReceipt


_AUTHORITY = (
    "LIVE_OWNER_LOCK_SCOPED_CYCLE_WARNING_PROJECTION"
    "_NOT_STABLE_AFTER_REPLY_NOT_RUNTIME_SAFETY"
)
_BINDING = "INSTALLED_CYCLE_WARNING_PROJECTION"
_NO_RECEIPT_SHA256 = "0" * 64


def read_locked_installed_cycle_warnings(
    state: Any,
    *,
    canonical_revision: int,
    authority_identity: Mapping[str, Any],
    activity_epoch: str,
) -> dict[str, Any]:
    """Project installed warnings; the caller MUST hold the LIVE owner lock."""
    def unavailable(reason: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": reason,
            "revision": canonical_revision,
            "activity_epoch": activity_epoch,
            "authority": _AUTHORITY,
        }

    if (
        type(canonical_revision) is not int
        or canonical_revision < 1
        or type(activity_epoch) is not str
        or not activity_epoch
        or not isinstance(authority_identity, Mapping)
    ):
        return unavailable("INSTALLED_GENERATION_UNAVAILABLE")

    owner_values = tuple(
        authority_identity.get(name)
        for name in (
            "repo_id", "root_path", "service_instance_id",
            "process_start_identity",
        )
    )
    if any(type(value) is not str or not value for value in owner_values):
        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")
    repo_id, root_path, service_instance_id, process_start_identity = owner_values

    registered = getattr(
        sys.modules.get("contextor.core.analysis.state_manager"),
        "RepositoryAnalysisState", None,
    )
    if type(registered) is not type or type(state) is not registered:
        return unavailable("INSTALLED_STATE_UNAVAILABLE")

    revision = getattr(state, "revision", None)
    state_id = getattr(state, "state_id", None)
    if (
        type(revision) is not int
        or revision != canonical_revision
        or type(state_id) is not str
        or not state_id
    ):
        return unavailable("INSTALLED_GENERATION_MISMATCH")

    try:
        graph_sha256 = fingerprint_hard_edges(state.dependency_graph.hard_edges)
        receipt = getattr(state, "cycle_partial_source_publication", None)
        claims_sha256 = (
            receipt.claims_sha256
            if type(receipt) is CanonicalPartialSCCReceipt
            and type(receipt.claims_sha256) is str
            else _NO_RECEIPT_SHA256
        )
        projection = project_installed_cycle_warnings(
            state,
            canonical_revision=canonical_revision,
            authority_identity=authority_identity,
            activity_epoch=activity_epoch,
            expected_revision=canonical_revision,
            expected_state_id=state_id,
            expected_repo_id=repo_id,
            expected_root_path=root_path,
            expected_graph_sha256=graph_sha256,
            expected_claims_sha256=claims_sha256,
            expected_service_instance_id=service_instance_id,
            expected_process_start_identity=process_start_identity,
        )
    except (AttributeError, KeyError, TypeError, ValueError, IndexError,
            RecursionError, OverflowError):
        return unavailable("CYCLE_WARNING_PROJECTION_UNAVAILABLE")

    if projection.status != "FRESH":
        return unavailable(projection.reason or "CYCLE_WARNING_PROJECTION_UNAVAILABLE")

    structural = projection.structural_paths
    accepted = projection.model_pass_paths
    active = projection.active_warning_paths
    if any(type(value) is not tuple for value in (structural, accepted, active)):
        return unavailable("CYCLE_WARNING_PROJECTION_UNAVAILABLE")

    return {
        "status": "ok",
        "binding_state": _BINDING,
        "revision": canonical_revision,
        "state_id": state_id,
        "repo_id": repo_id,
        "root_path": root_path,
        "service_instance_id": service_instance_id,
        "process_start_identity": process_start_identity,
        "activity_epoch": activity_epoch,
        "graph_sha256": graph_sha256,
        "structural_paths": structural,
        "model_pass_paths": accepted,
        "active_warning_paths": active,
        "structural_count": len(structural),
        "model_pass_count": len(accepted),
        "active_warning_count": len(active),
        "authority": _AUTHORITY,
    }
