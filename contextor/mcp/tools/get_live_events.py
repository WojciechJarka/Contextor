import json
from pathlib import Path


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
        return json.dumps(
            client.get_events(after_revision=after_revision, limit=limit), indent=2
        )
    except (OSError, EOFError, RuntimeError) as exc:
        return json.dumps({"status": "error", "error": str(exc)}, indent=2)
