"""Pure owner-captured cycle warning transition checkpoint.

Both reports must have been obtained from the same LIVE owner, each while
its corresponding generation was installed under the owner's lock.
This module never authenticates caller-provided data on its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .cycle_warning_projection import InstalledCycleWarningProjection
from .cycle_warning_transitions import diff_installed_cycle_warning_projections
from .live_cycle_warning_query import _AUTHORITY as _PROJECTION_AUTHORITY
from .live_cycle_warning_query import _BINDING as _PROJECTION_BINDING

_CHECKPOINT_AUTHORITY = (
    "LIVE_OWNER_COMMIT_SCOPED_WARNING_TRANSITIONS"
    "_NOT_STRUCTURAL_REMOVAL_FOR_MODEL_ACCEPTANCE"
    "_NOT_RUNTIME_SAFETY"
)


def build_locked_warning_transition_checkpoint(
    before: Any,
    after: Any,
    *,
    authority_identity: Mapping[str, Any],
    activity_epoch: str,
) -> dict[str, Any]:
    """Diff two owner-captured reports; return no transitions on uncertainty."""
    def unavailable(reason: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": reason,
            "authority": _CHECKPOINT_AUTHORITY,
        }

    try:
        if type(activity_epoch) is not str or not activity_epoch:
            return unavailable("WARNING_TRANSITION_AUTHORITY_UNAVAILABLE")
        if not isinstance(authority_identity, Mapping):
            return unavailable("WARNING_TRANSITION_AUTHORITY_UNAVAILABLE")
        names = ("repo_id", "root_path", "service_instance_id", "process_start_identity")
        identity = {name: authority_identity.get(name) for name in names}
        if any(type(value) is not str or not value for value in identity.values()):
            return unavailable("WARNING_TRANSITION_AUTHORITY_UNAVAILABLE")
        fields = {
            "status", "binding_state", "revision", "state_id", "repo_id",
            "root_path", "service_instance_id", "process_start_identity",
            "activity_epoch", "graph_sha256", "structural_paths",
            "model_pass_paths", "active_warning_paths", "structural_count",
            "model_pass_count", "active_warning_count", "authority",
        }
        for report in (before, after):
            if type(report) is not dict or set(report) != fields:
                return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
            if (report["status"] != "ok"
                    or report["binding_state"] != _PROJECTION_BINDING
                    or report["authority"] != _PROJECTION_AUTHORITY
                    or report["activity_epoch"] != activity_epoch):
                return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
            if any(report[name] != identity[name] for name in names):
                return unavailable("WARNING_TRANSITION_IDENTITY_MISMATCH")
            if (type(report["revision"]) is not int or report["revision"] < 1
                    or type(report["state_id"]) is not str or not report["state_id"]
                    or type(report["graph_sha256"]) is not str
                    or len(report["graph_sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in report["graph_sha256"])):
                return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
            for count, paths in (
                ("structural_count", "structural_paths"),
                ("model_pass_count", "model_pass_paths"),
                ("active_warning_count", "active_warning_paths"),
            ):
                if (type(report[count]) is not int or report[count] < 0
                        or type(report[paths]) is not tuple
                        or report[count] != len(report[paths])):
                    return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")

        old_revision, new_revision = before["revision"], after["revision"]
        if new_revision <= old_revision:
            return unavailable("WARNING_TRANSITION_REVISION_MISMATCH")
        before_projection = InstalledCycleWarningProjection(
            "FRESH", None, old_revision,
            before["structural_paths"], before["model_pass_paths"],
            before["active_warning_paths"],
        )
        after_projection = InstalledCycleWarningProjection(
            "FRESH", None, new_revision,
            after["structural_paths"], after["model_pass_paths"],
            after["active_warning_paths"],
        )
        delta = diff_installed_cycle_warning_projections(
            before_projection, after_projection,
        )
        if (delta.status != "FRESH" or delta.transitions is None
                or delta.from_revision != old_revision
                or delta.to_revision != new_revision):
            return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
        return {
            "status": "ok",
            "binding_state": "INSTALLED_WARNING_TRANSITION_CHECKPOINT",
            "from_revision": old_revision,
            "to_revision": new_revision,
            "activity_epoch": activity_epoch,
            **identity,
            "transitions": tuple({
                "path": transition.path,
                "action": transition.action,
                "previous_state": transition.previous_state,
                "current_state": transition.current_state,
            } for transition in delta.transitions),
            "authority": _CHECKPOINT_AUTHORITY,
        }
    except (AttributeError, KeyError, TypeError, ValueError, IndexError,
            RecursionError, OverflowError):
        return unavailable("WARNING_TRANSITION_PROJECTION_UNAVAILABLE")
