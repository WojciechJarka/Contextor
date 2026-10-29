"""Pure contracts for store-owned partial SCC co-publication.

A standalone seal is not a durable commit, source certificate, or safety proof.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
from .generation_manifest import _digest
from .original_worker_preparation import OriginalWorkerManifestPreparation
from .partial_scc_claims import (
    PARTIAL_SCC_CLAIMS_AUTHORITY,
    PARTIAL_SCC_CLAIMS_VERSION,
    PreparedPartialSCCClaims,
    validate_partial_scc_claims,
)


PARTIAL_SCC_PUBLICATION_VERSION = "cycle-partial-scc-co-publication/1"
PARTIAL_SCC_PUBLICATION_AUTHORITY = (
    "COMMITTED_PARTIAL_SCC_DECLARATIONS_NOT_SOURCE_CERTIFIED"
)


@dataclass(frozen=True)
class CanonicalPartialSCCReceipt:
    preparation: OriginalWorkerManifestPreparation
    claims_sha256: str
    revision: int
    state_id: str
    repo_id: str
    root_path: str
    version: str = PARTIAL_SCC_PUBLICATION_VERSION
    authority: str = PARTIAL_SCC_PUBLICATION_AUTHORITY


def seal_partial_scc_preparation(
    state: Any,
    preparation: OriginalWorkerManifestPreparation,
    *,
    revision: int,
    state_id: str,
    repo_id: str,
    root_path: str,
) -> CanonicalPartialSCCReceipt:
    """Validate declarations and seal an exact supplied generation identity."""
    if type(preparation) is not OriginalWorkerManifestPreparation:
        raise TypeError("partial SCC preparation contract missing")
    snapshot = getattr(state, "cycle_semantics", None)
    graph = getattr(state, "dependency_graph", None)
    hard_edges = getattr(graph, "hard_edges", None)
    if (
        type(snapshot) is not CycleSemanticsSnapshot
        or getattr(state, "cycle_semantics_state", None) != "fresh"
        or getattr(state, "cycles_state", None) != "fresh"
        or getattr(state, "resync_required", False) is not False
        or type(hard_edges) is not dict
    ):
        raise ValueError("canonical partial SCC evidence unavailable")
    graph_sha256 = fingerprint_hard_edges(hard_edges)
    if graph_sha256 != snapshot.graph_sha256:
        raise ValueError("canonical partial SCC graph identity mismatch")
    if (
        type(revision) is not int or revision < 1
        or type(state_id) is not str or not state_id
        or type(repo_id) is not str
        or type(root_path) is not str
        or type(getattr(state, "revision", None)) is not int
        or state.revision != revision
        or type(getattr(state, "state_id", None)) is not str
        or state.state_id != state_id
    ):
        raise ValueError("partial SCC publication generation identity mismatch")
    claims = validate_partial_scc_claims(hard_edges, snapshot, preparation)
    if (
        type(claims) is not PreparedPartialSCCClaims
        or claims.version != PARTIAL_SCC_CLAIMS_VERSION
        or claims.authority != PARTIAL_SCC_CLAIMS_AUTHORITY
    ):
        raise ValueError("partial SCC declarations unavailable")
    claims_sha256 = _digest((
        PARTIAL_SCC_PUBLICATION_VERSION,
        graph_sha256,
        asdict(claims),
        asdict(preparation),
    ))
    return CanonicalPartialSCCReceipt(
        preparation=preparation,
        claims_sha256=claims_sha256,
        revision=revision,
        state_id=state_id,
        repo_id=repo_id,
        root_path=root_path,
    )


def verify_co_published_partial_scc_preparation(
    state: Any,
    *,
    revision: int,
    state_id: str,
    repo_id: str,
    root_path: str,
) -> bool:
    """Revalidate stored declarations against the current supplied state."""
    receipt = getattr(state, "cycle_partial_source_publication", None)
    if (
        type(receipt) is not CanonicalPartialSCCReceipt
        or receipt.version != PARTIAL_SCC_PUBLICATION_VERSION
        or receipt.authority != PARTIAL_SCC_PUBLICATION_AUTHORITY
    ):
        return False
    try:
        expected = seal_partial_scc_preparation(
            state,
            receipt.preparation,
            revision=revision,
            state_id=state_id,
            repo_id=repo_id,
            root_path=root_path,
        )
    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
        return False
    return receipt == expected
