"""Pure transitions between two installed cycle-warning projections.

The caller captures each projection under its generation's LIVE owner lock.
This module validates projection shapes but cannot authenticate their origin.
MODEL_PASS is restricted static-model evidence, never runtime safety.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cycle_warning_projection import InstalledCycleWarningProjection


@dataclass(frozen=True)
class CycleWarningTransition:
    path: tuple[str, ...]
    action: str
    previous_state: str | None
    current_state: str | None


@dataclass(frozen=True)
class InstalledCycleWarningDelta:
    status: str
    reason: str | None
    from_revision: int | None
    to_revision: int | None
    transitions: tuple[CycleWarningTransition, ...] | None


def _validated_states(
    projection: InstalledCycleWarningProjection,
) -> dict[tuple[str, ...], str] | None:
    """Validate an entire partition, including ordering, before comparing."""
    if (
        type(projection) is not InstalledCycleWarningProjection
        or projection.status != "FRESH"
        or projection.reason is not None
        or type(projection.revision) is not int
        or projection.revision < 0
        or type(projection.structural_paths) is not tuple
        or type(projection.model_pass_paths) is not tuple
        or type(projection.active_warning_paths) is not tuple
    ):
        return None

    structural = projection.structural_paths
    accepted = projection.model_pass_paths
    active = projection.active_warning_paths

    for paths in (structural, accepted, active):
        identities: set[tuple[str, ...]] = set()
        for path in paths:
            if (
                type(path) is not tuple
                or len(path) < 2
                or any(type(node) is not str or not node for node in path)
                or path[0] != path[-1]
                or len(path[:-1]) != len(set(path[:-1]))
                or path in identities
            ):
                return None
            identities.add(path)

    structural_set = set(structural)
    accepted_set = set(accepted)
    active_set = set(active)
    if (
        not accepted_set.isdisjoint(active_set)
        or accepted_set | active_set != structural_set
        or len(accepted) + len(active) != len(structural)
        or accepted != tuple(path for path in structural if path in accepted_set)
        or active != tuple(path for path in structural if path in active_set)
    ):
        return None

    return {
        path: "MODEL_PASS" if path in accepted_set else "ACTIVE"
        for path in structural
    }


def diff_installed_cycle_warning_projections(
    previous: InstalledCycleWarningProjection,
    current: InstalledCycleWarningProjection,
) -> InstalledCycleWarningDelta:
    """Diff valid snapshots; do not confuse warning status with topology."""
    unavailable = InstalledCycleWarningDelta(
        status="UNAVAILABLE",
        reason="WARNING_PROJECTION_UNAVAILABLE",
        from_revision=None,
        to_revision=None,
        transitions=None,
    )
    try:
        before = _validated_states(previous)
        after = _validated_states(current)
        if before is None or after is None:
            return unavailable
        old_revision = previous.revision
        new_revision = current.revision
        if new_revision < old_revision:
            return unavailable
        if new_revision == old_revision and previous != current:
            return unavailable

        transitions: list[CycleWarningTransition] = []
        for path in previous.structural_paths:
            old_state = before[path]
            new_state = after.get(path)
            if new_state == old_state:
                continue
            if new_state is None:
                action = "STRUCTURAL_REMOVED"
            elif old_state == "ACTIVE":
                action = "MODEL_ACCEPTED"
            else:
                action = "WARNING_REACTIVATED"
            transitions.append(CycleWarningTransition(
                path=path,
                action=action,
                previous_state=old_state,
                current_state=new_state,
            ))

        for path in current.structural_paths:
            if path not in before:
                transitions.append(CycleWarningTransition(
                    path=path,
                    action="STRUCTURAL_ADDED",
                    previous_state=None,
                    current_state=after[path],
                ))

        return InstalledCycleWarningDelta(
            status="FRESH",
            reason=None,
            from_revision=old_revision,
            to_revision=new_revision,
            transitions=tuple(transitions),
        )
    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
        return unavailable
