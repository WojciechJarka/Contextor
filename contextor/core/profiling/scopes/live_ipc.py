"""Existing-authority read-only ping probe."""

from pathlib import Path

from contextor.core.live_state import connect

PRESETS = ("connect", "ping")


def run_scope(root: Path, recorder) -> dict[str, object]:
    with recorder.span("connect"):
        client = connect(root, reconcile_missing_endpoint_binding=False)
    if client is None:
        return {"status": "unavailable", "reason": "live_authority_unavailable"}
    with recorder.span("ping"):
        response = client.ping()
    if not isinstance(response, dict) or response.get("status") != "ok":
        return {"status": "invalid_data", "reason": "invalid_ping_response"}
    revision = response.get("revision")
    if type(revision) is not int or revision < 0:
        return {"status": "invalid_data", "reason": "invalid_ping_revision"}
    return {
        "status": "ok",
        "observed_revision": revision,
        "operation": "ping",
        "data_source": "live_authority",
    }
