"""Compare worker second-pass bytes with committed SCC claims.

The state and metadata are supplied by the caller.
Only an already co-published prepared manifest can be used.

This module authenticates neither the caller nor the state origin.
It never promotes source equivalence to import-runtime safety.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
)
from contextor.core.live_state.store import LiveStateMetadata
from contextor.core.source import (
    SourceSnapshot,
    parse_source_snapshot,
)

from .publication_binding import (
    CanonicalCycleManifestReceipt,
    verify_co_published_cycle_manifest,
)
from .selective_worker_capture import (
    SCCWorkerCapture,
    WORKER_CAPTURE_AUTHORITY,
)


WORKER_CLAIM_BINDING_AUTHORITY = (
    "CALLER_SUPPLIED_STATE_COMMITTED_CLAIM_COMPARISON"
    "_NOT_SOURCE_OR_LIVE_ORIGIN_AUTHENTICATED"
    "_NOT_RUNTIME_SAFETY"
)

_CAPTURE_STATUS = (
    "WORKER_SECOND_PASS_BYTES_AND_IMPORTS_MATCH_INDEX_NON_ATOMIC"
)

_MATCH = "DECLARED_BYTES_MATCH_COMMITTED_PREPARED_CLAIMS"

_AST_MODES = frozenset({
    "PARSED_FROM_WORKER_READ",
    "CACHE_SHA256_EQUIVALENT",
})


@dataclass(frozen=True)
class WorkerCommittedClaimAssessment:
    members: tuple[str, ...]
    binding_state: str
    reason: str | None
    canonical_revision: int | None
    state_id: str | None
    graph_sha256: str | None
    authority: str = WORKER_CLAIM_BINDING_AUTHORITY


def assess_worker_capture_committed_claim(
    state: RepositoryAnalysisState,
    metadata: LiveStateMetadata,
    capture: SCCWorkerCapture,
    *,
    max_source_bytes: int = 2 * 1024 * 1024,
    max_closure_bytes: int = 32 * 1024 * 1024,
) -> WorkerCommittedClaimAssessment:
    """Verify one complete SCC capture against co-published claims.

    No filesystem access, IPC, state mutation, worker execution,
    LIVE freshness lookup or safety classification.

    Matching means declaration consistency only. The receipt
    is not proof of original source-byte provenance.
    """
    if (
        type(max_source_bytes) is not int
        or not 1 <= max_source_bytes <= 64 * 1024 * 1024
        or type(max_closure_bytes) is not int
        or not 1 <= max_closure_bytes <= 256 * 1024 * 1024
    ):
        raise ValueError("invalid worker claim byte budget")

    members = (
        capture.members
        if type(capture) is SCCWorkerCapture
        and type(capture.members) is tuple
        else ()
    )
    revision = (
        metadata.revision
        if type(metadata) is LiveStateMetadata
        and type(metadata.revision) is int
        else None
    )
    state_id = (
        metadata.state_id
        if type(metadata) is LiveStateMetadata
        and type(metadata.state_id) is str
        else None
    )

    def unavailable(
        reason: str,
        graph_hash: str | None = None,
    ) -> WorkerCommittedClaimAssessment:
        return WorkerCommittedClaimAssessment(
            members=members,
            binding_state="UNAVAILABLE",
            reason=reason,
            canonical_revision=revision,
            state_id=state_id,
            graph_sha256=graph_hash,
        )

    if (
        type(state) is not RepositoryAnalysisState
        or type(metadata) is not LiveStateMetadata
        or type(capture) is not SCCWorkerCapture
    ):
        return unavailable("INVALID_INPUT_CONTRACT")

    if (
        type(metadata.revision) is not int
        or metadata.revision < 1
        or type(metadata.state_id) is not str
        or not metadata.state_id
        or type(metadata.repo_id) is not str
        or not metadata.repo_id
        or type(metadata.root_path) is not str
        or not metadata.root_path
    ):
        return unavailable("COMMITTED_IDENTITY_UNAVAILABLE")

    if (
        getattr(state, "revision", None)
        != metadata.revision
        or getattr(state, "state_id", None)
        != metadata.state_id
    ):
        return unavailable("GENERATION_IDENTITY_MISMATCH")

    receipt = getattr(
        state, "cycle_source_publication", None
    )
    if type(receipt) is not CanonicalCycleManifestReceipt:
        return unavailable("CO_PUBLISHED_RECEIPT_UNAVAILABLE")

    try:
        valid = verify_co_published_cycle_manifest(
            state,
            revision=metadata.revision,
            state_id=metadata.state_id,
            repo_id=metadata.repo_id,
            root_path=metadata.root_path,
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        valid = False

    if not valid:
        return unavailable("CO_PUBLISHED_RECEIPT_INVALID")

    manifest = receipt.prepared_manifest
    graph_hash = manifest.graph_sha256

    if (
        capture.status != _CAPTURE_STATUS
        or capture.reason is not None
        or capture.authority != WORKER_CAPTURE_AUTHORITY
    ):
        return unavailable(
            "WORKER_CAPTURE_NOT_ACCEPTED", graph_hash
        )

    prepared = next(
        (
            item
            for item in manifest.components
            if item.members == members
        ),
        None,
    )
    if prepared is None:
        return unavailable(
            "SCC_NOT_IN_COMMITTED_MANIFEST", graph_hash
        )

    signatures = prepared.source_signatures
    expected_modules = tuple(
        name for name, _, _ in signatures
    )

    if (
        capture.reachable_modules != expected_modules
        or not isinstance(capture.source_snapshots, Mapping)
        or set(capture.source_snapshots)
        != set(expected_modules)
        or type(capture.ast_modes) is not tuple
        or tuple(name for name, _ in capture.ast_modes)
        != expected_modules
        or any(
            type(mode) is not str or mode not in _AST_MODES
            for _, mode in capture.ast_modes
        )
    ):
        return unavailable(
            "SCC_CLOSURE_INCOMPLETE_OR_MISMATCHED",
            graph_hash,
        )

    total = 0

    for module, expected_raw, expected_ast in signatures:
        supplied = capture.source_snapshots[module]

        if (
            type(supplied) is not SourceSnapshot
            or type(supplied.raw) is not bytes
            or type(supplied.source_fingerprint) is not str
        ):
            return unavailable(
                "WORKER_SOURCE_INVALID:" + module,
                graph_hash,
            )

        size = len(supplied.raw)
        if (
            size > max_source_bytes
            or total + size > max_closure_bytes
        ):
            return unavailable(
                "SOURCE_BYTE_BUDGET_EXCEEDED:" + module,
                graph_hash,
            )

        total += size

        actual_raw = hashlib.sha256(
            supplied.raw
        ).hexdigest()

        if (
            actual_raw != supplied.source_fingerprint
            or actual_raw != expected_raw
        ):
            return unavailable(
                "SOURCE_BYTES_CLAIM_MISMATCH:" + module,
                graph_hash,
            )

        try:
            parsed = parse_source_snapshot(
                supplied, module
            )
            actual_ast = hashlib.sha256(
                ast.dump(
                    parsed.tree,
                    include_attributes=True,
                ).encode("utf-8")
            ).hexdigest()
        except (
            ValueError,
            TypeError,
            SyntaxError,
            RecursionError,
            OverflowError,
        ):
            return unavailable(
                "SOURCE_AST_UNAVAILABLE:" + module,
                graph_hash,
            )

        if actual_ast != expected_ast:
            return unavailable(
                "SOURCE_AST_CLAIM_MISMATCH:" + module,
                graph_hash,
            )

    if (
        type(capture.retained_raw_bytes) is not int
        or capture.retained_raw_bytes != total
    ):
        return unavailable(
            "CAPTURE_BYTE_ACCOUNTING_MISMATCH",
            graph_hash,
        )

    return WorkerCommittedClaimAssessment(
        members=members,
        binding_state=_MATCH,
        reason=None,
        canonical_revision=metadata.revision,
        state_id=metadata.state_id,
        graph_sha256=graph_hash,
    )
