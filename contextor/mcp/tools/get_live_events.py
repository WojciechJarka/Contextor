import json
from pathlib import Path


def _current_cycle_warning_view(client, events):
    """Read current warning state without reinterpreting historical events."""
    def unavailable(reason):
        return {"status": "unavailable", "reason": reason}

    try:
        report = client.get_installed_cycle_warning_projection()
    except (OSError, EOFError, RuntimeError, AttributeError, TypeError, ValueError):
        return unavailable("LIVE_WARNING_PROJECTION_QUERY_FAILED")

    if type(report) is not dict or report.get("status") != "ok":
        return unavailable("LIVE_WARNING_PROJECTION_UNAVAILABLE")

    if (
        report.get("binding_state") != "INSTALLED_CYCLE_WARNING_PROJECTION"
        or type(events.get("revision")) is not int
        or type(report.get("revision")) is not int
        or report["revision"] != events["revision"]
        or type(events.get("activity_epoch")) is not str
        or not events["activity_epoch"]
        or report.get("activity_epoch") != events["activity_epoch"]
    ):
        return unavailable("LIVE_WARNING_GENERATION_MISMATCH")

    structural = report.get("structural_paths")
    accepted = report.get("model_pass_paths")
    active = report.get("active_warning_paths")

    if any(type(paths) is not tuple for paths in (structural, accepted, active)):
        return unavailable("LIVE_WARNING_PARTITION_INVALID")

    for paths in (structural, accepted, active):
        if any(
            type(path) is not tuple
            or len(path) < 2
            or any(type(node) is not str or not node for node in path)
            or path[0] != path[-1]
            or len(set(path[:-1])) != len(path) - 1
            for path in paths
        ) or len(set(paths)) != len(paths):
            return unavailable("LIVE_WARNING_PARTITION_INVALID")

    structural_set = set(structural)
    accepted_set = set(accepted)
    active_set = set(active)

    if (
        not accepted_set.isdisjoint(active_set)
        or accepted_set | active_set != structural_set
        or accepted != tuple(p for p in structural if p in accepted_set)
        or active != tuple(p for p in structural if p in active_set)
        or any(
            type(report.get(count)) is not int
            or report[count] != len(paths)
            for count, paths in (
                ("structural_count", structural),
                ("model_pass_count", accepted),
                ("active_warning_count", active),
            )
        )
    ):
        return unavailable("LIVE_WARNING_PARTITION_INVALID")

    return {
        "status": "fresh",
        "scope": "CURRENT_INSTALLED_GENERATION_STATIC_MODEL_NOT_RUNTIME_SAFETY",
        "revision": report["revision"],
        "activity_epoch": report["activity_epoch"],
        "structural_count": report["structural_count"],
        "model_pass_count": report["model_pass_count"],
        "active_warning_count": report["active_warning_count"],
        "structural_paths": structural,
        "model_pass_paths": accepted,
        "active_warning_paths": active,
    }


def _current_cycle_warning_transitions(client, events, view):
    """Expose only the latest owner-verified warning transition checkpoint."""

    def unavailable(reason):
        return {"status": "unavailable", "reason": reason}

    if type(view) is not dict or view.get("status") != "fresh":
        return unavailable("CURRENT_WARNING_VIEW_UNAVAILABLE")

    try:
        checkpoint = client.request(
            "get_installed_cycle_warning_transitions",
            timeout=2.0,
        )
    except (
        OSError, EOFError, ConnectionError, TimeoutError,
        RuntimeError, AttributeError, TypeError, ValueError,
    ):
        return unavailable("WARNING_TRANSITION_QUERY_FAILED")

    if type(checkpoint) is not dict or checkpoint.get("status") != "ok":
        return unavailable("WARNING_TRANSITION_CHECKPOINT_UNAVAILABLE")

    required = {
        "status",
        "binding_state",
        "from_revision",
        "to_revision",
        "activity_epoch",
        "repo_id",
        "root_path",
        "service_instance_id",
        "process_start_identity",
        "transitions",
        "authority",
    }

    if set(checkpoint) != required:
        return unavailable("WARNING_TRANSITION_CHECKPOINT_INVALID")

    if (
        checkpoint["binding_state"]
        != "INSTALLED_WARNING_TRANSITION_CHECKPOINT"
        or checkpoint["authority"] != (
            "LIVE_OWNER_COMMIT_SCOPED_WARNING_TRANSITIONS"
            "_NOT_STRUCTURAL_REMOVAL_FOR_MODEL_ACCEPTANCE"
            "_NOT_RUNTIME_SAFETY"
        )
        or type(checkpoint["from_revision"]) is not int
        or type(checkpoint["to_revision"]) is not int
        or checkpoint["from_revision"] < 1
        or checkpoint["to_revision"] <= checkpoint["from_revision"]
        or checkpoint["to_revision"] != events.get("revision")
        or checkpoint["to_revision"] != view.get("revision")
        or checkpoint["activity_epoch"] != events.get("activity_epoch")
        or checkpoint["activity_epoch"] != view.get("activity_epoch")
        or type(checkpoint["activity_epoch"]) is not str
        or not checkpoint["activity_epoch"]
    ):
        return unavailable("WARNING_TRANSITION_GENERATION_MISMATCH")

    for key in (
        "repo_id",
        "root_path",
        "service_instance_id",
        "process_start_identity",
    ):
        if type(checkpoint[key]) is not str or not checkpoint[key]:
            return unavailable("WARNING_TRANSITION_IDENTITY_INVALID")

    transitions = checkpoint["transitions"]

    if type(transitions) is not tuple:
        return unavailable("WARNING_TRANSITION_CONTENT_INVALID")

    accepted = set(view["model_pass_paths"])
    active = set(view["active_warning_paths"])
    structural = set(view["structural_paths"])
    seen = set()

    for transition in transitions:
        if (
            type(transition) is not dict
            or set(transition) != {
                "path", "action", "previous_state", "current_state",
            }
        ):
            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")

        path = transition["path"]
        action = transition["action"]
        before = transition["previous_state"]
        after = transition["current_state"]

        if (
            type(path) is not tuple
            or len(path) < 2
            or any(type(node) is not str or not node for node in path)
            or path[0] != path[-1]
            or len(set(path[:-1])) != len(path) - 1
            or path in seen
        ):
            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")

        seen.add(path)

        if action == "STRUCTURAL_ADDED":
            valid = (
                before is None
                and after in {"MODEL_PASS", "ACTIVE"}
                and path in structural
            )
        elif action == "STRUCTURAL_REMOVED":
            valid = (
                before in {"MODEL_PASS", "ACTIVE"}
                and after is None
                and path not in structural
            )
        elif action == "MODEL_ACCEPTED":
            valid = (
                before == "ACTIVE"
                and after == "MODEL_PASS"
                and path in accepted
            )
        elif action == "WARNING_REACTIVATED":
            valid = (
                before == "MODEL_PASS"
                and after == "ACTIVE"
                and path in active
            )
        else:
            valid = False

        if not valid:
            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")

        if after == "MODEL_PASS" and path not in accepted:
            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")

        if after == "ACTIVE" and path not in active:
            return unavailable("WARNING_TRANSITION_CONTENT_INVALID")

    return {
        "status": "fresh",
        "scope": "LATEST_INSTALLED_COMMIT_ONLY_NOT_RETAINED_EVENT_HISTORY",
        "from_revision": checkpoint["from_revision"],
        "to_revision": checkpoint["to_revision"],
        "activity_epoch": checkpoint["activity_epoch"],
        "transition_count": len(transitions),
        "transitions": transitions,
    }


def get_live_events(
    repo_path: str,
    after_revision: int | None = None,
    limit: int | None = 20,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    if after_revision is not None and (
        isinstance(after_revision, bool)
        or not isinstance(after_revision, int)
    ):
        return json.dumps(
            {"status": "error", "error": "invalid_after_revision"}, indent=2
        )
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
    ):
        return json.dumps({"status": "error", "error": "invalid_limit"}, indent=2)
    from contextor.core.live_state.runtime import connect_existing_with_status

    client, connection_status = connect_existing_with_status(root)
    if client is None:
        if connection_status == "transient_connection_failure":
            return json.dumps(
                {
                    "status": "transient_connection_failure",
                    "repo_path": str(root),
                    "reason": "Existing LIVE owner is temporarily unreachable.",
                    "events": [], "total": 0, "truncated": False,
                },
                indent=2,
            )
        if connection_status in {
            "owner_identity_changed", "endpoint_identity_unverified",
        }:
            return json.dumps(
                {
                    "status": connection_status,
                    "repo_path": str(root),
                    "reason": "LIVE endpoint identity no longer proves the same repository owner instance.",
                    "events": [], "total": 0, "truncated": False,
                },
                indent=2,
            )
        return json.dumps(
            {
                "status": "no_live_service", "repo_path": str(root),
                "events": [], "total": 0, "truncated": False,
            },
            indent=2,
        )
    try:
        events = client.get_events(
            after_revision=after_revision,
            limit=limit,
        )

        if type(events) is not dict or events.get("status") != "ok":
            return json.dumps(events, indent=2)

        response = dict(events)
        response["cycle_diagnostic_history_semantics"] = (
            "STRUCTURAL_CHANGES_NOT_CURRENT_ACTIVE_WARNING_STATE"
        )
        response["cycle_warning_view"] = _current_cycle_warning_view(
            client, events,
        )
        response["cycle_warning_transitions"] = (
            _current_cycle_warning_transitions(
                client,
                events,
                response["cycle_warning_view"],
            )
        )
        return json.dumps(response, indent=2)

    except (OSError, EOFError, RuntimeError) as exc:
        return json.dumps({"status": "error", "error": str(exc)}, indent=2)
