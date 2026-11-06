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
