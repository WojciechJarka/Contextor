"""Registered-store boundary for P1D1C worker claim comparison.

The snapshot is selected via the central repository registry
and loaded under the canonical snapshot-store lock.

The resulting assessment identifies a durable generation.
It does not prove that this generation is still current
in the running LIVE service or authenticate capture origin.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from contextor.core.live_state.store import (
    LiveStateMetadata,
    locked_committed_snapshot,
)
from contextor.core.paths import repo_cache_dir
from contextor.core.repository_identity import (
    read_repository_identity,
)

from .selective_worker_capture import SCCWorkerCapture
from .worker_claim_binding import (
    assess_worker_capture_committed_claim,
)


_AUTHORITY = (
    "REGISTERED_REPOSITORY_COMMITTED_STORE_GENERATION"
    "_NOT_CURRENT_LIVE_OR_CAPTURE_ORIGIN_AUTHENTICATED"
    "_NOT_RUNTIME_SAFETY"
)

_MATCH = (
    "REGISTERED_COMMITTED_GENERATION_CLAIMS_MATCH_WORKER_BYTES"
)

_INNER_MATCH = (
    "DECLARED_BYTES_MATCH_COMMITTED_PREPARED_CLAIMS"
)


@dataclass(frozen=True)
class RegisteredStoreWorkerAssessment:
    members: tuple[str, ...]
    binding_state: str
    reason: str | None
    canonical_revision: int | None
    state_id: str | None
    repo_id: str | None
    root_path: str | None
    graph_sha256: str | None
    authority: str = _AUTHORITY


def assess_registered_committed_worker_capture(
    repository_root: str | Path,
    capture: SCCWorkerCapture,
    *,
    expected_revision: int,
    expected_state_id: str,
    max_source_bytes: int = 2 * 1024 * 1024,
    max_closure_bytes: int = 32 * 1024 * 1024,
) -> RegisteredStoreWorkerAssessment:
    """Compare capture with one selected committed generation.

    Repository identity comes from the existing central registry.
    Snapshot state and metadata come from the existing locked
    committed-store reader, never from a caller-supplied state.

    The store lock is released before P1D1C parsing.
    Thus no current-LIVE or post-return freshness is certified.
    """
    if (
        type(expected_revision) is not int
        or expected_revision < 1
        or type(expected_state_id) is not str
        or not expected_state_id
    ):
        raise ValueError("invalid expected generation identity")

    if (
        type(max_source_bytes) is not int
        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
        or type(max_closure_bytes) is not int
        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
    ):
        raise ValueError("invalid capture byte limits")

    members = (
        capture.members
        if type(capture) is SCCWorkerCapture
        and type(capture.members) is tuple
        else ()
    )

    repo_id: str | None = None
    root_path: str | None = None

    def unavailable(
        reason: str,
        *,
        revision: int | None = None,
        state_id: str | None = None,
        graph_hash: str | None = None,
    ) -> RegisteredStoreWorkerAssessment:
        return RegisteredStoreWorkerAssessment(
            members=members,
            binding_state="UNAVAILABLE",
            reason=reason,
            canonical_revision=revision,
            state_id=state_id,
            repo_id=repo_id,
            root_path=root_path,
            graph_sha256=graph_hash,
        )

    if type(capture) is not SCCWorkerCapture:
        return unavailable("INVALID_CAPTURE_CONTRACT")

    try:
        root = Path(repository_root).expanduser().resolve(
            strict=True
        )
        if not root.is_dir():
            return unavailable("REPOSITORY_ROOT_UNAVAILABLE")
    except (OSError, RuntimeError, TypeError, ValueError):
        return unavailable("REPOSITORY_ROOT_UNAVAILABLE")

    try:
        identity = read_repository_identity(root)
    except (OSError, RuntimeError, TypeError, ValueError):
        return unavailable("REPOSITORY_IDENTITY_INVALID")

    if identity is None:
        return unavailable("REPOSITORY_NOT_REGISTERED")

    if (
        type(identity.repo_id) is not str
        or not identity.repo_id.startswith("ctx_")
        or type(identity.root_path) is not str
        or identity.root_path != str(root)
    ):
        return unavailable("REPOSITORY_IDENTITY_INVALID")

    repo_id = identity.repo_id
    root_path = identity.root_path

    # Acquire canonical store lock for loading only.
    # Do NOT run worker tasks or AST parsing while holding it.
    try:
        with locked_committed_snapshot(
            repo_cache_dir(root),
            expected_repo_id=repo_id,
            expected_root_path=root_path,
        ) as loaded:
            if (
                type(loaded) is not tuple
                or len(loaded) != 2
            ):
                return unavailable(
                    "COMMITTED_GENERATION_UNAVAILABLE"
                )

            state, metadata = loaded

            if type(metadata) is not LiveStateMetadata:
                return unavailable(
                    "COMMITTED_METADATA_INVALID"
                )

            if (
                metadata.repo_id != repo_id
                or metadata.root_path != root_path
            ):
                return unavailable(
                    "COMMITTED_REPOSITORY_MISMATCH"
                )

            if (
                type(metadata.revision) is not int
                or metadata.revision != expected_revision
                or metadata.state_id != expected_state_id
            ):
                return unavailable(
                    "COMMITTED_EXPECTATION_MISMATCH",
                    revision=metadata.revision,
                    state_id=metadata.state_id,
                )

    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        EOFError,
    ):
        return unavailable("COMMITTED_SNAPSHOT_LOAD_FAILED")

    # The durable generation has been loaded and the lock
    # released. P1D1C compares this isolated loaded object.
    # No new assertion about current LIVE state is made.
    result = assess_worker_capture_committed_claim(
        state,
        metadata,
        capture,
        max_source_bytes=max_source_bytes,
        max_closure_bytes=max_closure_bytes,
    )

    if result.binding_state != _INNER_MATCH:
        return unavailable(
            result.reason or "COMMITTED_CLAIM_NOT_VERIFIED",
            revision=metadata.revision,
            state_id=metadata.state_id,
            graph_hash=result.graph_sha256,
        )

    return RegisteredStoreWorkerAssessment(
        members=result.members,
        binding_state=_MATCH,
        reason=None,
        canonical_revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=repo_id,
        root_path=root_path,
        graph_sha256=result.graph_sha256,
    )
