"""Post-save identity label for an optional preparation preview.

This caller-visible label does not authenticate the store, original
source bytes, atomicity, installed LIVE, or Python runtime safety.
It is not a receipt and must never authorize warning suppression.
"""

from __future__ import annotations

from dataclasses import dataclass

from .generation_manifest import (
    OPTIONAL_MANIFEST_VERSION,
    PreparedCycleSourceManifest,
    verify_prepared_optional_manifest_digest,
)
from .original_worker_preparation import (
    OriginalWorkerManifestPreparation,
)


OPTIONAL_GENERATION_ANCHOR_VERSION = (
    "cycle-optional-generation-anchor/1"
)
OPTIONAL_GENERATION_ANCHOR_AUTHORITY = (
    "CALLER_SUPPLIED_POST_SAVE_METADATA"
    "_NOT_SOURCE_OR_LIVE_AUTHENTICATED"
    "_NOT_RUNTIME_SAFETY"
)


@dataclass(frozen=True)
class OptionalPreparedGenerationAnchor:
    revision: int
    state_id: str
    repo_id: str
    root_path: str
    graph_sha256: str
    source_manifest_sha256: str
    version: str = OPTIONAL_GENERATION_ANCHOR_VERSION
    authority: str = OPTIONAL_GENERATION_ANCHOR_AUTHORITY


def make_optional_prepared_generation_anchor(
    preparation: object,
    metadata: object,
) -> OptionalPreparedGenerationAnchor | None:
    """Label a prepared v3 manifest with supplied post-save metadata.

    Pure consistency check. Caller origin is not authenticated.
    Does not read files, access LIVE, modify state or seal receipts.
    """
    from contextor.core.live_state.store import LiveStateMetadata

    if (
        type(preparation) is not OriginalWorkerManifestPreparation
        or type(metadata) is not LiveStateMetadata
        or preparation.source_selection != "OPTIONAL_NAMED_CHILDREN"
        or preparation.status != "PREPARED_UNPUBLISHED_NON_ATOMIC"
        or preparation.reason is not None
        or type(preparation.manifest) is not PreparedCycleSourceManifest
        or type(metadata.revision) is not int
        or metadata.revision < 1
        or type(metadata.state_id) is not str
        or not metadata.state_id
        or type(metadata.repo_id) is not str
        or not metadata.repo_id
        or type(metadata.root_path) is not str
        or not metadata.root_path
    ):
        return None

    manifest = preparation.manifest

    if (
        manifest.version != OPTIONAL_MANIFEST_VERSION
        or manifest.source_selection != "OPTIONAL_NAMED_CHILDREN"
        or not verify_prepared_optional_manifest_digest(manifest)
        or preparation.component_preparations != manifest.components
        or type(preparation.source_modules) is not tuple
    ):
        return None

    expected_sources = tuple(sorted({
        module
        for component in manifest.components
        for module, _, _ in component.source_signatures
    }))

    if preparation.source_modules != expected_sources:
        return None

    return OptionalPreparedGenerationAnchor(
        revision=metadata.revision,
        state_id=metadata.state_id,
        repo_id=metadata.repo_id,
        root_path=metadata.root_path,
        graph_sha256=manifest.graph_sha256,
        source_manifest_sha256=manifest.source_manifest_sha256,
    )


OPTIONAL_GENERATION_ASSESSMENT_AUTHORITY = (
    "CALLER_SUPPLIED_GENERATION_CONSISTENCY"
    "_NOT_STORE_OR_SOURCE_OR_LIVE_AUTHENTICATED"
    "_NOT_RUNTIME_SAFETY"
)


@dataclass(frozen=True)
class OptionalPreparedGenerationAssessment:
    status: str
    reason: str | None
    revision: int | None
    state_id: str | None
    graph_sha256: str | None
    source_manifest_sha256: str | None
    authority: str = OPTIONAL_GENERATION_ASSESSMENT_AUTHORITY


def assess_optional_prepared_generation(
    anchor: object,
    preparation: object,
    state: object,
    metadata: object,
) -> OptionalPreparedGenerationAssessment:
    """Compare v3 preview against a supplied canonical generation.

    No filesystem access, store lookup, LIVE IPC, mutation, receipt,
    source-origin certification or runtime safety determination.
    The caller supplies state and metadata; their origin is not proven.
    """
    from contextor.core.analysis.state_manager import (
        RepositoryAnalysisState,
    )
    from contextor.core.live_state.store import LiveStateMetadata
    from .contracts import CycleSemanticsSnapshot
    from .partial_scc_claims import (
        PreparedOptionalPartialSCCClaims,
        validate_optional_partial_scc_claims,
    )

    revision = (
        anchor.revision
        if type(anchor) is OptionalPreparedGenerationAnchor
        and type(anchor.revision) is int
        else None
    )
    state_id = (
        anchor.state_id
        if type(anchor) is OptionalPreparedGenerationAnchor
        and type(anchor.state_id) is str
        else None
    )

    def unavailable(reason):
        return OptionalPreparedGenerationAssessment(
            status="UNAVAILABLE",
            reason=reason,
            revision=revision,
            state_id=state_id,
            graph_sha256=None,
            source_manifest_sha256=None,
        )

    if (
        type(anchor) is not OptionalPreparedGenerationAnchor
        or type(preparation) is not OriginalWorkerManifestPreparation
        or type(state) is not RepositoryAnalysisState
        or type(metadata) is not LiveStateMetadata
    ):
        return unavailable("INVALID_INPUT_CONTRACT")

    try:
        expected_anchor = make_optional_prepared_generation_anchor(
            preparation, metadata,
        )
    except (
        AttributeError, KeyError, TypeError, ValueError,
        RecursionError, OverflowError,
    ):
        return unavailable("PREPARATION_CONTRACT_INVALID")

    if expected_anchor is None or anchor != expected_anchor:
        return unavailable("ANCHOR_METADATA_MISMATCH")

    if (
        type(getattr(state, "revision", None)) is not int
        or state.revision != metadata.revision
        or type(getattr(state, "state_id", None)) is not str
        or state.state_id != metadata.state_id
    ):
        return unavailable("CANONICAL_GENERATION_IDENTITY_MISMATCH")

    snapshot = getattr(state, "cycle_semantics", None)

    if (
        getattr(state, "cycle_semantics_state", None) != "fresh"
        or getattr(state, "cycles_state", None) != "fresh"
        or getattr(state, "resync_required", False) is not False
        or type(snapshot) is not CycleSemanticsSnapshot
        or snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
        or snapshot.source_issues
    ):
        return unavailable("CANONICAL_CYCLE_EVIDENCE_NOT_FRESH")

    graph = getattr(state, "dependency_graph", None)
    hard_edges = getattr(graph, "hard_edges", None)
    modules = getattr(state, "modules", None)
    package_root = getattr(state, "package_root", None)

    if (
        type(hard_edges) is not dict
        or type(modules) is not dict
        or set(hard_edges) != set(modules)
        or package_root is not None
        and type(package_root) is not str
    ):
        return unavailable("CANONICAL_INDEX_GRAPH_DOMAIN_INVALID")

    indexed_imports = {}

    try:
        indexed_imports = {
            name: module.imports
            for name, module in modules.items()
        }

        claims = validate_optional_partial_scc_claims(
            hard_edges,
            snapshot,
            preparation,
            indexed_imports,
            package_root=package_root or None,
        )
    except (
        AttributeError, KeyError, TypeError, ValueError,
        IndexError, RecursionError, OverflowError,
    ):
        return unavailable("OPTIONAL_CLAIM_VALIDATION_UNAVAILABLE")

    if (
        type(claims) is not PreparedOptionalPartialSCCClaims
        or claims.graph_sha256 != anchor.graph_sha256
        or claims.declared_manifest_sha256
        != anchor.source_manifest_sha256
        or claims.source_modules != preparation.source_modules
        or claims.components != preparation.component_preparations
    ):
        return unavailable("OPTIONAL_DECLARATIONS_GENERATION_MISMATCH")

    return OptionalPreparedGenerationAssessment(
        status="MATCHED_SUPPLIED_GENERATION_NON_ATOMIC",
        reason=None,
        revision=metadata.revision,
        state_id=metadata.state_id,
        graph_sha256=anchor.graph_sha256,
        source_manifest_sha256=anchor.source_manifest_sha256,
    )
