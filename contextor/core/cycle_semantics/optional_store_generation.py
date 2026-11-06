"""Compare optional preview with the current local snapshot.

The cache directory is caller-selected. A successful result means
consistency with the generation returned by the existing local
snapshot reader.

This does not authenticate repository ownership, original source
provenance, installed LIVE, atomic source capture or runtime safety.

No new receipt, publication or warning authority is created.
"""

from __future__ import annotations

import pickle

from dataclasses import dataclass
from pathlib import Path

from contextor.core.live_state.store import (
    LiveStateMetadata,
    load_snapshot,
    read_metadata,
)

from .optional_generation_anchor import (
    OPTIONAL_GENERATION_ANCHOR_AUTHORITY,
    OPTIONAL_GENERATION_ANCHOR_VERSION,
    OptionalPreparedGenerationAnchor,
    OptionalPreparedGenerationAssessment,
    assess_optional_prepared_generation,
)
from .original_worker_preparation import (
    OriginalWorkerManifestPreparation,
)


OPTIONAL_STORE_ASSESSMENT_AUTHORITY = (
    "CALLER_SELECTED_LOCAL_SNAPSHOT_READ_CONSISTENCY"
    "_NOT_ORIGIN_OR_LIVE_AUTHENTICATED"
    "_NOT_RUNTIME_SAFETY"
)


@dataclass(frozen=True)
class OptionalStoredGenerationAssessment:
    status: str
    reason: str | None
    revision: int | None
    state_id: str | None
    graph_sha256: str | None
    source_manifest_sha256: str | None
    authority: str = OPTIONAL_STORE_ASSESSMENT_AUTHORITY


def assess_optional_stored_generation(
    cache_dir: str | Path,
    anchor: object,
    preparation: object,
) -> OptionalStoredGenerationAssessment:
    """Assess v3 preview against the current local cache generation.

    The existing snapshot loader validates persisted metadata.
    A second metadata read detects an observed generation rollover.

    The operation does not hold a lock across all checks and does
    not establish atomicity or installed LIVE authority.
    """

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

    def unavailable(reason: str):
        return OptionalStoredGenerationAssessment(
            status="UNAVAILABLE",
            reason=reason,
            revision=revision,
            state_id=state_id,
            graph_sha256=None,
            source_manifest_sha256=None,
        )

    if (
        not isinstance(cache_dir, (str, Path))
        or not str(cache_dir)
        or type(anchor) is not OptionalPreparedGenerationAnchor
        or type(preparation) is not OriginalWorkerManifestPreparation
    ):
        return unavailable("INVALID_INPUT_CONTRACT")

    if (
        type(anchor.revision) is not int
        or anchor.revision < 1
        or type(anchor.state_id) is not str
        or not anchor.state_id
        or type(anchor.repo_id) is not str
        or not anchor.repo_id
        or type(anchor.root_path) is not str
        or not anchor.root_path
        or anchor.version != OPTIONAL_GENERATION_ANCHOR_VERSION
        or anchor.authority != OPTIONAL_GENERATION_ANCHOR_AUTHORITY
    ):
        return unavailable("INVALID_ANCHOR_IDENTITY")

    try:
        before = read_metadata(cache_dir)
    except (
        OSError,
        TypeError,
        ValueError,
        AttributeError,
    ):
        return unavailable("STORE_METADATA_UNAVAILABLE")

    if type(before) is not LiveStateMetadata:
        return unavailable("STORE_METADATA_UNAVAILABLE")

    if (
        before.revision,
        before.state_id,
        before.repo_id,
        before.root_path,
    ) != (
        anchor.revision,
        anchor.state_id,
        anchor.repo_id,
        anchor.root_path,
    ):
        return unavailable("STORE_GENERATION_NOT_CURRENT")

    try:
        loaded = load_snapshot(
            cache_dir,
            anchor.state_id,
            expected_repo_id=anchor.repo_id,
            expected_root_path=anchor.root_path,
        )
    except (
        OSError,
        EOFError,
        pickle.PickleError,
        TypeError,
        ValueError,
        AttributeError,
        KeyError,
        RecursionError,
        OverflowError,
    ):
        return unavailable("STORE_SNAPSHOT_UNAVAILABLE")

    if type(loaded) is not tuple or len(loaded) != 2:
        return unavailable("STORE_SNAPSHOT_UNAVAILABLE")

    state, metadata = loaded

    if (
        type(metadata) is not LiveStateMetadata
        or metadata != before
    ):
        return unavailable("LOADED_METADATA_MISMATCH")

    try:
        after = read_metadata(cache_dir)
    except (
        OSError,
        TypeError,
        ValueError,
        AttributeError,
    ):
        return unavailable("STORE_HEAD_CHANGED")

    if type(after) is not LiveStateMetadata or after != before:
        return unavailable("STORE_HEAD_CHANGED")

    try:
        assessment = assess_optional_prepared_generation(
            anchor,
            preparation,
            state,
            metadata,
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        KeyError,
        IndexError,
        RecursionError,
        OverflowError,
    ):
        return unavailable("GENERATION_ASSESSMENT_UNAVAILABLE")

    if (
        type(assessment) is not OptionalPreparedGenerationAssessment
        or assessment.status
        != "MATCHED_SUPPLIED_GENERATION_NON_ATOMIC"
        or assessment.reason is not None
    ):
        reason = (
            assessment.reason
            if type(assessment) is OptionalPreparedGenerationAssessment
            else None
        )

        return unavailable(
            "GENERATION_" + (reason or "UNAVAILABLE")
        )

    return OptionalStoredGenerationAssessment(
        status="MATCHED_CURRENT_LOCAL_SNAPSHOT_NON_ATOMIC",
        reason=None,
        revision=metadata.revision,
        state_id=metadata.state_id,
        graph_sha256=assessment.graph_sha256,
        source_manifest_sha256=assessment.source_manifest_sha256,
    )
