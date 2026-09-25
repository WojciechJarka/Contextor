"""Pure diagnostic projections from canonical repository state."""

from __future__ import annotations

from typing import Any


def _availability(
    state: Any,
    family: str,
    values: Any,
) -> str:
    status = getattr(
        state,
        f"{family}_state",
        None,
    )

    if values is None and status == "fresh":
        return "unavailable"

    if status in {
        "fresh",
        "stale",
        "deferred",
        "unavailable",
    }:
        return status

    if values is None:
        return "unavailable"

    return "fresh"


def diagnostics_summary_for_state(
    state: Any,
) -> dict[str, Any]:
    """Return canonical diagnostic counts plus freshness."""

    if state is None:
        unavailable = {
            "count": None,
            "availability": "unavailable",
        }

        return {
            "syntax_errors": dict(unavailable),
            "name_collisions": {
                "count": None,
                "critical": None,
                "warning": None,
                "info": None,
                "availability": "unavailable",
            },
            "cycles": dict(unavailable),
            "attention_required": False,
            "availability": {
                "syntax_errors": "unavailable",
                "name_collisions": "unavailable",
                "cycles": "unavailable",
            },
        }

    syntax_state = getattr(
        state,
        "syntax_diagnostics_state",
        None,
    )
    syntax_facts = getattr(
        state,
        "syntax_diagnostics_by_path",
        None,
    )

    if (
        syntax_state == "fresh"
        and isinstance(syntax_facts, dict)
    ):
        syntax_values = sum(
            isinstance(fact, dict)
            and fact.get("status")
            == "checked_with_errors"
            for fact in syntax_facts.values()
        )
        syntax_availability = "fresh"

    elif syntax_state in {
        "not_materialized",
        "deferred",
        "stale",
        "unavailable",
    }:
        syntax_values = None
        syntax_availability = syntax_state

    else:
        syntax_values = None
        syntax_availability = "unavailable"

    collisions = getattr(
        state,
        "collisions",
        None,
    )
    cycles = getattr(
        state,
        "cycles",
        None,
    )

    collision_availability = _availability(
        state,
        "collisions",
        collisions,
    )
    cycle_availability = _availability(
        state,
        "cycles",
        cycles,
    )

    if collision_availability != "fresh":
        collision_count = None
        critical = None
        warning = None
        info = None
    else:
        collision_count = len(
            collisions or []
        )
        critical = None
        warning = None
        info = None

    cycle_count = (
        len(cycles)
        if cycle_availability == "fresh"
        else None
    )

    syntax_issue = (
        syntax_values
        if syntax_availability == "fresh"
        else None
    )

    attention = any(
        value is not None and value > 0
        for value in (
            syntax_issue,
            collision_count,
            cycle_count,
        )
    )

    return {
        "syntax_errors": {
            "count": syntax_values,
            "availability": syntax_availability,
        },
        "name_collisions": {
            "count": collision_count,
            "critical": critical,
            "warning": warning,
            "info": info,
            "availability": collision_availability,
        },
        "cycles": {
            "count": cycle_count,
            "availability": cycle_availability,
        },
        "attention_required": bool(attention),
        "availability": {
            "syntax_errors": syntax_availability,
            "name_collisions": collision_availability,
            "cycles": cycle_availability,
        },
    }


__all__ = [
    "diagnostics_summary_for_state",
]
