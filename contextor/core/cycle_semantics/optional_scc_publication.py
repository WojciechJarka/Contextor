"""Store-generation receipt for optional SCC declarations.

A receipt establishes co-publication of declarations with a supplied
canonical generation when created by the locked snapshot writer.

Standalone sealing is pure and does not prove a durable commit.
Neither sealing nor verification certifies source origin, atomicity,
installed LIVE, runtime import safety, or warning suppression.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .contracts import (
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from .generation_manifest import _digest
from .original_worker_preparation import (
    OriginalWorkerManifestPreparation,
)
from .partial_scc_claims import (
    OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY,
    OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION,
    PreparedOptionalPartialSCCClaims,
    validate_optional_partial_scc_claims,
)


OPTIONAL_SCC_PUBLICATION_VERSION = (
    "cycle-optional-scc-co-publication/1"
)

OPTIONAL_SCC_PUBLICATION_AUTHORITY = (
    "COMMITTED_OPTIONAL_SCC_DECLARATIONS"
    "_NOT_SOURCE_CERTIFIED_NOT_RUNTIME_SAFETY"
)


@dataclass(frozen=True)
class CanonicalOptionalSCCReceipt:
    preparation: OriginalWorkerManifestPreparation
    claims_sha256: str
    revision: int
    state_id: str
    repo_id: str
    root_path: str
    version: str = OPTIONAL_SCC_PUBLICATION_VERSION
    authority: str = OPTIONAL_SCC_PUBLICATION_AUTHORITY


def seal_optional_scc_preparation(
    state: Any,
    preparation: OriginalWorkerManifestPreparation,
    *,
    revision: int,
    state_id: str,
    repo_id: str,
    root_path: str,
) -> CanonicalOptionalSCCReceipt:
    """Seal declared optional SCC evidence for a supplied generation.

    Only invocation by the locked canonical writer establishes
    co-publication. This pure function does not persist anything.
    """

    if type(preparation) is not OriginalWorkerManifestPreparation:
        raise TypeError("optional SCC preparation contract missing")

    if (
        preparation.source_selection != "OPTIONAL_NAMED_CHILDREN"
        or preparation.status != "PREPARED_UNPUBLISHED_NON_ATOMIC"
        or preparation.reason is not None
        or preparation.manifest is None
    ):
        raise ValueError("optional SCC preparation unavailable")

    snapshot = getattr(state, "cycle_semantics", None)
    graph = getattr(state, "dependency_graph", None)
    hard_edges = getattr(graph, "hard_edges", None)
    modules = getattr(state, "modules", None)
    package_root = getattr(state, "package_root", None)

    if (
        type(snapshot) is not CycleSemanticsSnapshot
        or getattr(state, "cycle_semantics_state", None) != "fresh"
        or getattr(state, "cycles_state", None) != "fresh"
        or getattr(state, "resync_required", False) is not False
        or type(hard_edges) is not dict
        or type(modules) is not dict
        or set(hard_edges) != set(modules)
        or (
            package_root is not None
            and type(package_root) is not str
        )
    ):
        raise ValueError("canonical optional SCC evidence unavailable")

    graph_sha256 = fingerprint_hard_edges(hard_edges)

    if graph_sha256 != snapshot.graph_sha256:
        raise ValueError("canonical optional SCC graph mismatch")

    if (
        type(revision) is not int
        or revision < 1
        or type(state_id) is not str
        or not state_id
        or type(repo_id) is not str
        or not repo_id
        or type(root_path) is not str
        or not root_path
        or type(getattr(state, "revision", None)) is not int
        or state.revision != revision
        or type(getattr(state, "state_id", None)) is not str
        or state.state_id != state_id
    ):
        raise ValueError("optional SCC generation identity mismatch")

    indexed_imports = {
        module_id: module.imports
        for module_id, module in modules.items()
    }

    claims = validate_optional_partial_scc_claims(
        hard_edges,
        snapshot,
        preparation,
        indexed_imports,
        package_root=package_root or None,
    )

    if (
        type(claims) is not PreparedOptionalPartialSCCClaims
        or claims.version != OPTIONAL_PARTIAL_SCC_CLAIMS_VERSION
        or claims.authority != OPTIONAL_PARTIAL_SCC_CLAIMS_AUTHORITY
        or claims.declared_manifest_sha256 is None
        or claims.source_modules != preparation.source_modules
        or claims.components != preparation.component_preparations
    ):
        raise ValueError("optional SCC declarations unavailable")

    claims_sha256 = _digest((
        OPTIONAL_SCC_PUBLICATION_VERSION,
        graph_sha256,
        asdict(claims),
        asdict(preparation),
    ))

    return CanonicalOptionalSCCReceipt(
        preparation=preparation,
        claims_sha256=claims_sha256,
        revision=revision,
        state_id=state_id,
        repo_id=repo_id,
        root_path=root_path,
    )


def verify_co_published_optional_scc_preparation(
    state: Any,
    *,
    revision: int,
    state_id: str,
    repo_id: str,
    root_path: str,
) -> bool:
    """Revalidate an existing receipt against supplied generation data.

    This function cannot independently prove which writer created
    an in-memory receipt. Store ownership requires the store path.
    """

    receipt = getattr(
        state,
        "cycle_optional_source_publication",
        None,
    )

    if (
        type(receipt) is not CanonicalOptionalSCCReceipt
        or receipt.version != OPTIONAL_SCC_PUBLICATION_VERSION
        or receipt.authority != OPTIONAL_SCC_PUBLICATION_AUTHORITY
    ):
        return False

    try:
        expected = seal_optional_scc_preparation(
            state,
            receipt.preparation,
            revision=revision,
            state_id=state_id,
            repo_id=repo_id,
            root_path=root_path,
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
        return False

    return receipt == expected
