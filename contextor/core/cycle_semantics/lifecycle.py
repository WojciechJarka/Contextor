"""Canonical freshness lifecycle for cycle-semantic evidence.

This module does not analyze cycles, read source,
open LIVE IPC, persist snapshots, or publish state.

Invalidation preserves immutable historical
evidence while marking it unavailable as fresh.

The caller owns COW, transaction and publication
boundaries.
"""

from __future__ import annotations

from .contracts import CycleSemanticsSnapshot


FULL_SOURCE_DRIFT_ISSUES = frozenset({
    "CANONICAL_FINGERPRINT_MISMATCH",
    "SOURCE_CHANGED_DURING_READ",
})

FULL_SOURCE_AUTHORITY_UNAVAILABLE_ISSUES = frozenset({
    "MISSING_OR_INVALID_CANONICAL_PATH",
    "SOURCE_UNREADABLE",
    "INVALID_CANONICAL_FINGERPRINT",
})

FULL_SOURCE_BOUNDED_EVALUATION_ISSUES = frozenset({
    "SOURCE_FILE_LIMIT",
    "SOURCE_COHORT_BYTE_LIMIT",
    "SOURCE_NOT_COMPILABLE",
})


def classify_full_cycle_semantics(
    snapshot: CycleSemanticsSnapshot,
) -> tuple[str, str | None]:
    """Classify FULL evidence freshness, not completeness.

    A source mismatch cannot be marked fresh.

    Missing source authority cannot certify freshness.

    Bounded or otherwise explicitly incomplete
    evaluation may still be a current diagnostic.

    The snapshot itself always preserves its
    explicit source coverage and issue details.
    """

    if type(snapshot) is not CycleSemanticsSnapshot:
        raise TypeError(
            "Expected CycleSemanticsSnapshot"
        )

    reasons = {
        reason
        for _, reason in snapshot.source_issues
    }

    if reasons & FULL_SOURCE_DRIFT_ISSUES:
        return "stale", "SOURCE_CHANGED"

    if reasons & FULL_SOURCE_AUTHORITY_UNAVAILABLE_ISSUES:
        return "deferred", None

    classified_reasons = (
        FULL_SOURCE_DRIFT_ISSUES
        | FULL_SOURCE_AUTHORITY_UNAVAILABLE_ISSUES
        | FULL_SOURCE_BOUNDED_EVALUATION_ISSUES
    )

    if reasons - classified_reasons:
        return "deferred", None

    if (
        snapshot.coverage_status
        == "PARTIAL_SOURCE_EVIDENCE"
        and not reasons
    ):
        return "deferred", None

    return "fresh", None


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

    # Even retained historical semantic evidence cannot carry
    # its old publication receipt into a new generation.
    state.cycle_source_publication = None
    state.cycle_partial_source_publication = None

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
