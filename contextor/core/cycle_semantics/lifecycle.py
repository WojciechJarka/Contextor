"""Canonical freshness lifecycle for cycle-semantic evidence.

This module does not analyze cycles, read source,
open LIVE IPC, persist snapshots, or publish state.

Invalidation preserves immutable historical
evidence while marking it unavailable as fresh.

The caller owns COW, transaction and publication
boundaries.
"""

from __future__ import annotations


CYCLE_SEMANTICS_INVALIDATION_REASONS = frozenset({
    "SOURCE_CHANGED",
    "SOURCE_DELETED",
    "SOURCE_PARSE_FAILED",
    "CANONICAL_RESYNC_REQUIRED",
})


def invalidate_cycle_semantics(
    state: object,
    reason: str,
) -> None:
    """Invalidate semantic evidence without destroying it.

    An absent snapshot remains deferred.

    An existing snapshot becomes stale.

    Preserve the first invalidation reason unless
    a canonical resync overrides it.
    """

    if reason not in (
        CYCLE_SEMANTICS_INVALIDATION_REASONS
    ):
        raise ValueError(
            "Unsupported cycle semantics invalidation reason"
        )

    evidence = getattr(
        state,
        "cycle_semantics",
        None,
    )

    if evidence is None:
        state.cycle_semantics_state = "deferred"
        state.cycle_semantics_invalidation_reason = None
        return

    previous_state = getattr(
        state,
        "cycle_semantics_state",
        "deferred",
    )

    previous_reason = getattr(
        state,
        "cycle_semantics_invalidation_reason",
        None,
    )

    state.cycle_semantics_state = "stale"

    if (
        reason == "CANONICAL_RESYNC_REQUIRED"
        or previous_state != "stale"
        or previous_reason not in (
            CYCLE_SEMANTICS_INVALIDATION_REASONS
        )
    ):
        state.cycle_semantics_invalidation_reason = (
            reason
        )
