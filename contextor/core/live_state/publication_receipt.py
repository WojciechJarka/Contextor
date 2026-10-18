"""Bounded confirmation of one exact committed LIVE publication job."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any


CONFIRMATION_SECONDS = 90.0
POLL_SECONDS = 0.1


def committed_publication_key(repo_id: str, state_id: str, revision: int) -> str:
    if (
        not isinstance(repo_id, str) or not repo_id
        or not isinstance(state_id, str) or not state_id
        or type(revision) is not int or revision < 1
    ):
        raise ValueError("Invalid committed publication identity.")
    encoded = json.dumps(
        [repo_id, state_id, revision],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return "cp-" + hashlib.sha256(encoded).hexdigest()


def _result(
    status: str, *, job_id: str | None, service_instance_id: str | None,
    process_start_identity: str | None, state_id: str, revision: int,
    idempotency_key: str | None = None,
    published_revision: int | None = None, warning: str | None = None,
) -> dict[str, object]:
    return {
        "live_publish_status": status,
        "live_publish_revision": published_revision,
        "live_publish_warning": warning,
        "live_publish_job_id": job_id,
        "live_publish_service_instance_id": service_instance_id,
        "live_publish_process_start_identity": process_start_identity,
        "live_publish_expected_state_id": state_id,
        "live_publish_expected_revision": revision,
        "live_publish_idempotency_key": idempotency_key,
    }


def classify_publication_receipt(
    receipt: object, *,
    job_id: str,
    service_instance_id: str,
    process_start_identity: str,
    state_id: str,
    revision: int,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    common = dict(
        job_id=job_id, service_instance_id=service_instance_id,
        process_start_identity=process_start_identity,
        state_id=state_id, revision=revision,
        idempotency_key=idempotency_key,
    )
    if not isinstance(receipt, dict) or receipt.get("job_id") != job_id:
        return _result("pending_verification", **common, warning="Exact mutation job status unavailable.")
    if (
        receipt.get("requested_state_id") != state_id
        or type(receipt.get("requested_revision")) is not int
        or receipt["requested_revision"] != revision
    ):
        return _result("pending_verification", **common, warning="Mutation generation identity mismatch.")
    if receipt.get("status") != "ok":
        return _result("pending_verification", **common, warning="Mutation status unavailable.")
    state = receipt.get("state")
    if state == "queued" or state == "running":
        return _result("pending_verification", **common)
    if state != "completed" and state != "failed" and state != "cancelled":
        return _result("pending_verification", **common, warning="Mutation completion state unavailable.")
    response = receipt.get("response")
    if state != "completed":
        return _result("failed", **common, warning="Committed publication job failed.")
    if not isinstance(response, dict):
        return _result("pending_verification", **common, warning="Terminal publication response unavailable.")
    if response.get("status") != "ok":
        return _result("failed", **common, warning="Committed publication was rejected.")
    if type(response.get("revision")) is not int or response["revision"] != revision:
        return _result("pending_verification", **common, warning="Installed revision did not match request.")
    if response.get("resync_required") is True:
        return _result("recovery_required", **common, published_revision=revision,
                       warning="LIVE recovery verification required.")
    warning = (
        "LIVE generation was already installed; event origin is not verified."
        if response.get("already_installed") is True else None
    )
    return _result("success", **common, published_revision=revision, warning=warning)


def publish_committed_and_wait(
    client,
    *,
    repo_id,
    state_id,
    revision,
    origin,
) -> dict[str, object]:
    key = committed_publication_key(repo_id, state_id, revision)
    endpoint = client.endpoint
    service_id = getattr(endpoint, "service_instance_id", None)
    process_identity = getattr(endpoint, "process_start_identity", None)
    common = dict(
        job_id=None, service_instance_id=service_id,
        process_start_identity=process_identity,
        state_id=state_id, revision=revision, idempotency_key=key,
    )
    if not isinstance(service_id, str) or not service_id or not isinstance(process_identity, str) or not process_identity:
        return _result("unverified_authority_changed", **common,
                       warning="Verified LIVE service identity unavailable.")
    deadline = time.monotonic() + CONFIRMATION_SECONDS
    accepted: dict[str, Any] | None = None
    for _ in range(2):
        try:
            submitted = client.submit_committed_publish(
                state_id=state_id, revision=revision, origin=origin,
                idempotency_key=key,
            )
        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
            continue
        if isinstance(submitted, dict):
            accepted = submitted
        break
    if accepted is None:
        try:
            accepted = client.lookup_committed_publish(
                idempotency_key=key, state_id=state_id, revision=revision,
            )
        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
            accepted = None
        if not isinstance(accepted, dict) or accepted.get("status") != "ok":
            return _result("pending_verification", **common,
                           warning="Publication admission and read-only job lookup unavailable.")
    if accepted.get("status") == "ok" and isinstance(accepted.get("job_id"), str):
        job_id = accepted["job_id"]
    elif accepted.get("status") == "accepted" and accepted.get("accepted") is True:
        job_id = accepted.get("job_id")
    else:
        return _result("failed", **common, warning="Publication admission rejected.")
    if not isinstance(job_id, str) or not job_id:
        try:
            recovered = client.lookup_committed_publish(
                idempotency_key=key, state_id=state_id, revision=revision,
            )
        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
            recovered = None
        if isinstance(recovered, dict) and recovered.get("status") == "ok":
            accepted = recovered
            job_id = recovered.get("job_id")
        else:
            return _result("pending_verification", **common,
                           warning="Publication job identity unavailable; read-only recovery found no job.")
    if not isinstance(job_id, str) or not job_id:
        return _result("pending_verification", **common,
                       warning="Publication job identity unavailable.")
    common["job_id"] = job_id
    while True:
        try:
            status = client.mutation_status(job_id)
        except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
            return _result("pending_verification", **common,
                           warning="Publication status unavailable.")
        classified = classify_publication_receipt(
            status, job_id=job_id, service_instance_id=service_id,
            process_start_identity=process_identity,
            state_id=state_id, revision=revision, idempotency_key=key,
        )
        if classified["live_publish_status"] != "pending_verification":
            try:
                authority = client.authority_status()
            except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
                authority = None
            if not isinstance(authority, dict) or authority.get("status") != "ok":
                return _result("pending_verification", **common,
                               warning="LIVE authority identity unavailable for receipt verification.")
            if (authority.get("service_instance_id") != service_id
                    or authority.get("process_start_identity") != process_identity):
                return _result("unverified_authority_changed", **common,
                               warning="LIVE authority identity changed before receipt verification.")
            return classified
        if time.monotonic() >= deadline:
            return classified
        time.sleep(min(POLL_SECONDS, max(0.0, deadline - time.monotonic())))
