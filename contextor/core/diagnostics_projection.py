"""Pure diagnostic projections from canonical repository state."""

from __future__ import annotations

from typing import Any

from collections.abc import Mapping

from contextor.core.cycle_semantics.scc import (
    analyze_soft_dependent_potential_cycles,
)


_CYCLE_COUNT_SEMANTICS = (
    "DFS_BACK_EDGE_PATHS_DEDUP_ROTATION_NOT_ALL_SIMPLE_CYCLES"
)
_POTENTIAL_CYCLE_SCOPE = (
    "RESTRICTED_HARD_UNION_SOFT_IMPORT_GRAPH_POTENTIAL_ONLY"
)


def _soft_dependent_cycle_diagnostic(state: Any) -> dict[str, Any]:
    unavailable = {
        "count": None,
        "components": None,
        "availability": "unavailable",
        "evidence_scope": _POTENTIAL_CYCLE_SCOPE,
        "runtime_execution_proven": False,
    }
    if state is None:
        return unavailable
    resync_required = getattr(state, "resync_required", False)
    if resync_required is True:
        return {**unavailable, "availability": "stale"}
    if resync_required is not False:
        return unavailable
    cycle_state = getattr(state, "cycles_state", None)
    if cycle_state != "fresh":
        availability = cycle_state if cycle_state in {
            "stale", "deferred", "unavailable",
        } else "unavailable"
        return {**unavailable, "availability": availability}
    graph = getattr(state, "dependency_graph", None)
    hard = getattr(graph, "hard_edges", None)
    soft = getattr(graph, "soft_edges", None)
    if not isinstance(hard, Mapping) or not isinstance(soft, Mapping):
        return unavailable
    try:
        result = analyze_soft_dependent_potential_cycles(hard, soft)
    except (TypeError, ValueError):
        return unavailable
    return {
        "count": result.component_count,
        "components": tuple({
            "kind": component.kind,
            "members": component.members,
            "soft_only_internal_edges": component.soft_only_internal_edges,
        } for component in result.components),
        "availability": "fresh",
        "evidence_scope": result.evidence_scope,
        "runtime_execution_proven": False,
    }


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

    if isinstance(status, str) and status in {
        "fresh",
        "stale",
        "deferred",
        "unavailable",
    }:
        if status == "fresh" and values is None:
            return "unavailable"
        return status

    return "unavailable"


def diagnostics_summary_for_state(
    state: Any,
) -> dict[str, Any]:
    """Return canonical diagnostic counts plus freshness."""

    if state is None:
        potential = _soft_dependent_cycle_diagnostic(None)
        unavailable = {
            "count": None,
            "availability": "unavailable",
        }
        unavailable_cycles = {
            **unavailable,
            "count_semantics": _CYCLE_COUNT_SEMANTICS,
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
            "cycles": unavailable_cycles,
            "soft_dependent_potential_cycles": potential,
            "attention_required": False,
            "availability": {
                "syntax_errors": "unavailable",
                "name_collisions": "unavailable",
                "cycles": "unavailable",
                "soft_dependent_potential_cycles": potential["availability"],
            },
        }

    if getattr(state, "resync_required", False):
        potential = _soft_dependent_cycle_diagnostic(state)
        unavailable = {
            "count": None,
            "availability": "stale",
        }
        unavailable_cycles = {
            **unavailable,
            "count_semantics": _CYCLE_COUNT_SEMANTICS,
        }
        return {
            "syntax_errors": dict(unavailable),
            "name_collisions": {
                "count": None,
                "critical": None,
                "warning": None,
                "info": None,
                "availability": "stale",
            },
            "cycles": unavailable_cycles,
            "soft_dependent_potential_cycles": potential,
            "attention_required": False,
            "availability": {
                "syntax_errors": "stale",
                "name_collisions": "stale",
                "cycles": "stale",
                "soft_dependent_potential_cycles": potential["availability"],
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

    elif isinstance(syntax_state, str) and syntax_state in {
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
    potential = _soft_dependent_cycle_diagnostic(state)

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
            potential["count"],
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
            "count_semantics": _CYCLE_COUNT_SEMANTICS,
        },
        "soft_dependent_potential_cycles": potential,
        "attention_required": bool(attention),
        "availability": {
            "syntax_errors": syntax_availability,
            "name_collisions": collision_availability,
            "cycles": cycle_availability,
            "soft_dependent_potential_cycles": potential["availability"],
        },
    }


__all__ = [
    "diagnostics_summary_for_state",
]
