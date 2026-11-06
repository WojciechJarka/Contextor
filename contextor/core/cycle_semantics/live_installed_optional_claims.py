"""Lock-scoped assessment of installed optional SCC declarations.

The caller must hold the canonical LIVE owner state lock.

This verifies one installed generation and its co-published
optional SCC receipt. It does not certify original source
provenance, atomicity, runtime safety or warning eligibility.
"""

from __future__ import annotations

import sys

from collections.abc import Mapping
from typing import Any

from .contracts import fingerprint_hard_edges
from .optional_scc_publication import (
    CanonicalOptionalSCCReceipt,
    verify_co_published_optional_scc_preparation,
)


OPTIONAL_LIVE_AUTHORITY = (
    "LIVE_OWNER_LOCK_SCOPED_INSTALLED_OPTIONAL_SCC_DECLARATIONS"
    "_NOT_STABLE_AFTER_REPLY"
    "_NOT_SOURCE_CERTIFIED"
    "_NOT_RUNTIME_SAFETY"
)

OPTIONAL_LIVE_MATCH = (
    "INSTALLED_OPTIONAL_SCC_CLAIMS_MATCH_EXPECTED_GENERATION"
)


def assess_live_installed_optional_claims(
    state: Any,
    *,
    canonical_revision: int,
    authority_identity: Mapping[str, Any],
    activity_epoch: str,
    expected_revision: Any,
    expected_state_id: Any,
    expected_repo_id: Any,
    expected_root_path: Any,
    expected_graph_sha256: Any,
    expected_source_manifest_sha256: Any,
    expected_claims_sha256: Any,
    expected_service_instance_id: Any,
    expected_process_start_identity: Any,
) -> dict[str, Any]:
    """Compare expectations with the installed LIVE-owned state.

    Caller must hold CanonicalLiveServer._lock throughout
    evaluation and response construction.
    """

    def unavailable(reason: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": reason,
            "revision": canonical_revision,
            "activity_epoch": activity_epoch,
            "authority": OPTIONAL_LIVE_AUTHORITY,
        }

    expected_strings = (
        expected_state_id,
        expected_repo_id,
        expected_root_path,
        expected_service_instance_id,
        expected_process_start_identity,
    )

    expected_hashes = (
        expected_graph_sha256,
        expected_source_manifest_sha256,
        expected_claims_sha256,
    )

    if (
        type(expected_revision) is not int
        or expected_revision < 1
        or any(
            type(value) is not str
            or not value
            or len(value) > 4096
            for value in expected_strings
        )
        or any(
            type(value) is not str
            or len(value) != 64
            or any(
                character not in "0123456789abcdef"
                for character in value
            )
            for value in expected_hashes
        )
    ):
        return unavailable("INVALID_EXPECTED_GENERATION")

    if (
        not isinstance(authority_identity, Mapping)
        or type(activity_epoch) is not str
        or not activity_epoch
    ):
        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")

    owner_repo = authority_identity.get("repo_id")
    owner_root = authority_identity.get("root_path")
    owner_instance = authority_identity.get(
        "service_instance_id"
    )
    owner_process = authority_identity.get(
        "process_start_identity"
    )

    if any(
        type(value) is not str or not value
        for value in (
            owner_repo,
            owner_root,
            owner_instance,
            owner_process,
        )
    ):
        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")

    if owner_instance != expected_service_instance_id:
        return unavailable("LIVE_INSTANCE_MISMATCH")

    if owner_process != expected_process_start_identity:
        return unavailable("LIVE_PROCESS_START_MISMATCH")

    if (
        owner_repo != expected_repo_id
        or owner_root != expected_root_path
    ):
        return unavailable("LIVE_REPOSITORY_MISMATCH")

    # Resolve existing loaded class without importing
    # analysis.state_manager from LIVE query code.
    registered_state_type = getattr(
        sys.modules.get(
            "contextor.core.analysis.state_manager"
        ),
        "RepositoryAnalysisState",
        None,
    )

    if (
        type(registered_state_type) is not type
        or type(state) is not registered_state_type
    ):
        return unavailable("INSTALLED_STATE_UNAVAILABLE")

    if (
        type(canonical_revision) is not int
        or canonical_revision != expected_revision
        or type(getattr(state, "revision", None)) is not int
        or state.revision != canonical_revision
        or getattr(state, "state_id", None)
        != expected_state_id
    ):
        return unavailable("INSTALLED_GENERATION_MISMATCH")

    if getattr(state, "resync_required", False) is not False:
        return unavailable("CANONICAL_RESYNC_REQUIRED")

    if (
        getattr(state, "cycle_semantics_state", None)
        != "fresh"
        or getattr(state, "cycles_state", None)
        != "fresh"
    ):
        return unavailable("REQUIRED_CYCLE_FAMILY_NOT_FRESH")

    receipt = getattr(
        state,
        "cycle_optional_source_publication",
        None,
    )

    if type(receipt) is not CanonicalOptionalSCCReceipt:
        return unavailable("CO_PUBLISHED_OPTIONAL_RECEIPT_UNAVAILABLE")

    try:
        valid = verify_co_published_optional_scc_preparation(
            state,
            revision=canonical_revision,
            state_id=expected_state_id,
            repo_id=owner_repo,
            root_path=owner_root,
        )
    except (
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        IndexError,
        RecursionError,
        OverflowError,
    ):
        valid = False

    if not valid:
        return unavailable("CO_PUBLISHED_OPTIONAL_RECEIPT_INVALID")

    manifest = receipt.preparation.manifest

    if (
        manifest is None
        or receipt.claims_sha256 != expected_claims_sha256
    ):
        return unavailable("INSTALLED_CLAIMS_IDENTITY_MISMATCH")

    if (
        manifest.source_manifest_sha256
        != expected_source_manifest_sha256
    ):
        return unavailable("INSTALLED_MANIFEST_IDENTITY_MISMATCH")

    try:
        current_graph_sha256 = fingerprint_hard_edges(
            state.dependency_graph.hard_edges
        )
        snapshot_graph_sha256 = (
            state.cycle_semantics.graph_sha256
        )
    except (
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        IndexError,
        RecursionError,
        OverflowError,
    ):
        return unavailable("INSTALLED_GRAPH_IDENTITY_MISMATCH")

    if (
        manifest.graph_sha256 != expected_graph_sha256
        or snapshot_graph_sha256 != expected_graph_sha256
        or current_graph_sha256 != expected_graph_sha256
    ):
        return unavailable("INSTALLED_GRAPH_IDENTITY_MISMATCH")

    return {
        "status": "ok",
        "binding_state": OPTIONAL_LIVE_MATCH,
        "revision": canonical_revision,
        "state_id": expected_state_id,
        "repo_id": owner_repo,
        "root_path": owner_root,
        "service_instance_id": owner_instance,
        "process_start_identity": owner_process,
        "activity_epoch": activity_epoch,
        "graph_sha256": expected_graph_sha256,
        "source_manifest_sha256": expected_source_manifest_sha256,
        "claims_sha256": expected_claims_sha256,
        "authority": OPTIONAL_LIVE_AUTHORITY,
    }
