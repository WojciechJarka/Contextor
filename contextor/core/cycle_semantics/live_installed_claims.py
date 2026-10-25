"""Lock-scoped comparison of installed LIVE cycle claims.

The caller must invoke this helper while holding the canonical
LIVE owner's state lock. This helper does not acquire that lock.

It verifies the current installed generation and the existing
co-published prepared-manifest receipt.

No source provenance, durable-store read, or runtime import
safety is certified by this operation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
)

from .publication_binding import (
    CanonicalCycleManifestReceipt,
    verify_co_published_cycle_manifest,
)


_AUTHORITY = (
    "LIVE_OWNER_LOCK_SCOPED_INSTALLED_PREPARED_CLAIMS"
    "_NOT_STABLE_AFTER_REPLY"
    "_NOT_WORKER_SOURCE_CERTIFIED"
    "_NOT_RUNTIME_SAFETY"
)

_MATCH = "INSTALLED_PREPARED_CLAIMS_MATCH_EXPECTED_GENERATION"


def assess_live_installed_prepared_claims(
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
    expected_service_instance_id: Any,
) -> dict[str, Any]:
    """Compare expected identity with the installed LIVE state.

    IMPORTANT: The CanonicalLiveServer caller owns self._lock
    for the entire evaluation and response construction.
    """

    def unavailable(reason: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": reason,
            "revision": canonical_revision,
            "activity_epoch": activity_epoch,
            "authority": _AUTHORITY,
        }

    expected_strings = (
        expected_state_id,
        expected_repo_id,
        expected_root_path,
        expected_service_instance_id,
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
        or type(expected_graph_sha256) is not str
        or len(expected_graph_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in expected_graph_sha256
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

    if any(
        type(value) is not str or not value
        for value in (
            owner_repo,
            owner_root,
            owner_instance,
        )
    ):
        return unavailable("LIVE_AUTHORITY_UNAVAILABLE")

    if owner_instance != expected_service_instance_id:
        return unavailable("LIVE_INSTANCE_MISMATCH")

    if (
        owner_repo != expected_repo_id
        or owner_root != expected_root_path
    ):
        return unavailable("LIVE_REPOSITORY_MISMATCH")

    if type(state) is not RepositoryAnalysisState:
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
        "cycle_source_publication",
        None,
    )

    if type(receipt) is not CanonicalCycleManifestReceipt:
        return unavailable("CO_PUBLISHED_RECEIPT_UNAVAILABLE")

    try:
        valid = verify_co_published_cycle_manifest(
            state,
            revision=canonical_revision,
            state_id=expected_state_id,
            repo_id=owner_repo,
            root_path=owner_root,
        )
    except (
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
    ):
        valid = False

    if not valid:
        return unavailable("CO_PUBLISHED_RECEIPT_INVALID")

    manifest = receipt.prepared_manifest

    if manifest.graph_sha256 != expected_graph_sha256:
        return unavailable("INSTALLED_GRAPH_IDENTITY_MISMATCH")

    return {
        "status": "ok",
        "binding_state": _MATCH,
        "revision": canonical_revision,
        "state_id": expected_state_id,
        "repo_id": owner_repo,
        "root_path": owner_root,
        "service_instance_id": owner_instance,
        "activity_epoch": activity_epoch,
        "graph_sha256": manifest.graph_sha256,
        "source_manifest_sha256": (
            manifest.source_manifest_sha256
        ),
        "model_claims_sha256": receipt.model_claims_sha256,
        "authority": _AUTHORITY,
    }
