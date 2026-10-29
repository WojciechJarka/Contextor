"""Warning-aware diagnostics summary for one installed LIVE generation.

Canonical structural cycle counts are preserved. Only a validated,
owner-captured static-model acceptance partition can reduce active
cycle warnings. This does not establish runtime execution safety.

This pure function does not authenticate the caller or hold a lock.
The LIVE owner must invoke it while holding its canonical state lock.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .cycle_warning_projection import InstalledCycleWarningProjection
from .cycle_warning_transitions import _validated_states
from .live_cycle_warning_query import (
    _AUTHORITY as _PROJECTION_AUTHORITY,
    _BINDING as _PROJECTION_BINDING,
)


_IDENTITY_KEYS = (
    "repo_id",
    "root_path",
    "service_instance_id",
    "process_start_identity",
)

_PROJECTION_FIELDS = frozenset({
    "status",
    "binding_state",
    "revision",
    "state_id",
    "repo_id",
    "root_path",
    "service_instance_id",
    "process_start_identity",
    "activity_epoch",
    "graph_sha256",
    "structural_paths",
    "model_pass_paths",
    "active_warning_paths",
    "structural_count",
    "model_pass_count",
    "active_warning_count",
    "authority",
})

_WARNING_SEMANTICS = (
    "INSTALLED_STATIC_MODEL_ACCEPTANCE_NOT_RUNTIME_SAFETY"
)


def _nonnegative_count(value: Any) -> bool:
    return value is None or (
        type(value) is int and value >= 0
    )


def project_locked_warning_diagnostics_summary(
    summary: Any,
    warning_report: Any,
    *,
    canonical_revision: int,
    activity_epoch: str,
    authority_identity: Mapping[str, Any],
) -> Any:
    """Return an additive warning-aware summary, or unchanged original.

    Invalid evidence never suppresses a structural cycle warning.
    Structural evidence and source summary objects are never mutated.
    """
    if type(summary) is not dict:
        return summary

    try:
        if (
            type(canonical_revision) is not int
            or canonical_revision < 1
            or type(activity_epoch) is not str
            or not activity_epoch
            or not isinstance(authority_identity, Mapping)
            or type(warning_report) is not dict
            or set(warning_report) != _PROJECTION_FIELDS
        ):
            return summary

        if (
            warning_report["status"] != "ok"
            or warning_report["binding_state"] != _PROJECTION_BINDING
            or warning_report["authority"] != _PROJECTION_AUTHORITY
            or type(warning_report["revision"]) is not int
            or warning_report["revision"] != canonical_revision
            or warning_report["activity_epoch"] != activity_epoch
        ):
            return summary

        if any(
            type(authority_identity.get(key)) is not str
            or not authority_identity[key]
            or warning_report[key] != authority_identity[key]
            for key in _IDENTITY_KEYS
        ):
            return summary

        if (
            type(warning_report["state_id"]) is not str
            or not warning_report["state_id"]
            or type(warning_report["graph_sha256"]) is not str
            or len(warning_report["graph_sha256"]) != 64
            or any(
                char not in "0123456789abcdef"
                for char in warning_report["graph_sha256"]
            )
        ):
            return summary

        cycles = summary.get("cycles")
        syntax = summary.get("syntax_errors")
        collisions = summary.get("name_collisions")

        if (
            type(cycles) is not dict
            or type(syntax) is not dict
            or type(collisions) is not dict
            or cycles.get("availability") != "fresh"
            or type(cycles.get("count")) is not int
            or cycles["count"] < 0
            or type(summary.get("attention_required")) is not bool
            or not _nonnegative_count(syntax.get("count"))
            or not _nonnegative_count(collisions.get("count"))
        ):
            return summary

        structural = warning_report["structural_paths"]
        accepted = warning_report["model_pass_paths"]
        active = warning_report["active_warning_paths"]

        for field, paths in (
            ("structural_count", structural),
            ("model_pass_count", accepted),
            ("active_warning_count", active),
        ):
            if (
                type(paths) is not tuple
                or type(warning_report[field]) is not int
                or warning_report[field] < 0
                or warning_report[field] != len(paths)
            ):
                return summary

        if warning_report["structural_count"] != cycles["count"]:
            return summary

        projection = InstalledCycleWarningProjection(
            status="FRESH",
            reason=None,
            revision=canonical_revision,
            structural_paths=structural,
            model_pass_paths=accepted,
            active_warning_paths=active,
        )

        if _validated_states(projection) is None:
            return summary

        active_count = warning_report["active_warning_count"]

        result = dict(summary)
        result["cycles"] = {
            **cycles,
            "active_warning_count": active_count,
            "model_pass_count": warning_report["model_pass_count"],
            "warning_availability": "fresh",
            "warning_semantics": _WARNING_SEMANTICS,
        }
        result["attention_required"] = any(
            type(value) is int and value > 0
            for value in (
                syntax["count"],
                collisions["count"],
                active_count,
            )
        )
        return result

    except (
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        IndexError,
        RecursionError,
        OverflowError,
    ):
        return summary
