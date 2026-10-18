import json
import os
from pathlib import Path

from contextor.mcp import analysis_jobs
from contextor.mcp.output_guard import (
    LARGE_OUTPUT_WARNING_BYTES,
    guard_large_output,
    largest_fitting_prefix,
)
from contextor.mcp.diagnostics import diagnostics_summary, diagnostics_summary_for_completed_job


def get_analysis_status(
    repo_path: str,
    job_id: str | None = None,
    max_skipped_files: int | None = 10,
    allow_large_output: bool = False,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return json.dumps(
            {"status": "missing_repository", "repo_path": str(root)}, indent=2
        )
    if job_id is None:
        active_jobs = analysis_jobs._active_analysis_jobs(root)

        if len(active_jobs) > 1:
            active_job_limit = 5
            selected_active_jobs = active_jobs[:active_job_limit]

            return json.dumps(
                {
                    "status": "ambiguous_job",
                    "job_id": None,
                    "repo_path": str(root),
                    "active_job_count": len(active_jobs),
                    "active_jobs": [
                        {
                            "job_id": job.get("job_id"),
                            "operation": job.get("operation"),
                            "target": job.get("target"),
                            "status": job.get("status"),
                            "created_at": job.get("created_at"),
                            "updated_at": job.get("updated_at"),
                        }
                        for job in selected_active_jobs
                    ],
                    "truncated": len(active_jobs) > active_job_limit,
                    "message": (
                        "Multiple queued/running analysis jobs exist. "
                        "Repeat get_analysis_status with one listed job_id."
                    ),
                },
                indent=2,
            )

        job = analysis_jobs._latest_analysis_job(root)

    else:
        job = analysis_jobs._read_analysis_job(root, job_id)

    if job is None:
        return json.dumps(
            {"status": "not_found", "job_id": job_id, "repo_path": str(root)},
            indent=2,
        )
    if job.get("status") in {"queued", "running"}:
        interruption_error = None
        interruption_message = None

        if job.get("owner_pid") != os.getpid():
            interruption_error = "owner_process_changed"
            interruption_message = (
                "The MCP server process that owned this job is no longer active."
            )
        elif not analysis_jobs._is_current_process_analysis_task_active(
            str(job.get("job_id") or "")
        ):
            interruption_error = "worker_not_active"
            interruption_message = (
                "The analysis worker for this job is no longer active."
            )

        if interruption_error is not None:
            job = {
                **job,
                "status": "interrupted",
                "completed_at": analysis_jobs._utc_now(),
                "message": interruption_message,
                "error": interruption_error,
            }
            try:
                analysis_jobs._write_analysis_job(root, job)
            except OSError as exc:
                job = {
                    **job,
                    "message": (
                        f"{interruption_message} "
                        "Durable reconciliation persistence failed: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
    if (
        job_id is not None
        and job.get("status") == "completed"
        and job.get("live_publish_status") == "pending_verification"
        and isinstance(job.get("live_publish_expected_state_id"), str)
        and type(job.get("live_publish_expected_revision")) is int
        and isinstance(job.get("live_publish_service_instance_id"), str)
        and isinstance(job.get("live_publish_process_start_identity"), str)
        and (
            isinstance(job.get("live_publish_job_id"), str)
            or isinstance(job.get("live_publish_idempotency_key"), str)
        )
    ):
        from contextor.core.live_state import connect
        from contextor.core.live_state.publication_receipt import classify_publication_receipt
        from contextor.core.live_state.publication_receipt import committed_publication_key

        try:
            client = connect(root, reconcile_missing_endpoint_binding=False)
        except (OSError, ValueError, RuntimeError):
            client = None
        expected_service = job.get("live_publish_service_instance_id")
        expected_process = job.get("live_publish_process_start_identity")
        if client is not None:
            endpoint_service = client.endpoint.service_instance_id
            endpoint_process = client.endpoint.process_start_identity
            endpoint_identity_available = (
                isinstance(endpoint_service, str) and bool(endpoint_service)
                and isinstance(endpoint_process, str) and bool(endpoint_process)
            )
            if endpoint_identity_available and (
                endpoint_service != expected_service
                or endpoint_process != expected_process
            ):
                job = {
                    **job,
                    "live_publish_status": "unverified_authority_changed",
                    "live_publish_revision": None,
                    "live_publish_warning": "LIVE authority identity changed before receipt verification.",
                }
                endpoint_identity_available = False
            if endpoint_identity_available:
                try:
                    authority = client.authority_status()
                except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
                    authority = None
            else:
                authority = None
        if client is not None and authority is not None:
            if not isinstance(authority, dict) or authority.get("status") != "ok":
                authority = None
            else:
                authority_service = authority.get("service_instance_id")
                authority_process = authority.get("process_start_identity")
                authority_identity_available = (
                    isinstance(authority_service, str) and bool(authority_service)
                    and isinstance(authority_process, str) and bool(authority_process)
                )
                if authority_identity_available and (
                    authority_service != expected_service
                    or authority_process != expected_process
                ):
                    job = {
                        **job,
                        "live_publish_status": "unverified_authority_changed",
                        "live_publish_revision": None,
                        "live_publish_warning": "LIVE authority identity changed before receipt verification.",
                    }
                    authority = None
                elif not authority_identity_available:
                    authority = None
        if client is not None and isinstance(authority, dict) and authority.get("status") == "ok":
            mutation_job_id = job.get("live_publish_job_id")
            if not isinstance(mutation_job_id, str):
                state_id = job["live_publish_expected_state_id"]
                revision = job["live_publish_expected_revision"]
                stored_key = job.get("live_publish_idempotency_key")
                repo_id = authority.get("repo_id")
                expected_key = None
                if isinstance(repo_id, str) and repo_id:
                    try:
                        expected_key = committed_publication_key(repo_id, state_id, revision)
                    except ValueError:
                        expected_key = None
                if isinstance(stored_key, str) and stored_key == expected_key:
                    try:
                        lookup = client.lookup_committed_publish(
                            idempotency_key=stored_key, state_id=state_id,
                            revision=revision,
                        )
                    except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
                        lookup = None
                    if (
                        isinstance(lookup, dict)
                        and lookup.get("status") == "ok"
                        and isinstance(lookup.get("job_id"), str)
                        and bool(lookup.get("job_id"))
                        and lookup.get("requested_state_id") == state_id
                        and type(lookup.get("requested_revision")) is int
                        and lookup.get("requested_revision") == revision
                    ):
                        mutation_job_id = lookup["job_id"]
                        job = {**job, "live_publish_job_id": mutation_job_id}
                        try:
                            analysis_jobs._write_analysis_job(root, job)
                        except OSError:
                            pass
            if isinstance(mutation_job_id, str) and mutation_job_id:
                try:
                    receipt = client.mutation_status(mutation_job_id)
                except (OSError, EOFError, ConnectionError, TimeoutError, RuntimeError):
                    receipt = None
                classified = classify_publication_receipt(
                    receipt,
                    job_id=mutation_job_id,
                    service_instance_id=expected_service,
                    process_start_identity=expected_process,
                    state_id=job["live_publish_expected_state_id"],
                    revision=job["live_publish_expected_revision"],
                    idempotency_key=job.get("live_publish_idempotency_key"),
                )
                if classified["live_publish_status"] in {"success", "failed", "recovery_required"}:
                    job = {**job, **classified}
                    analysis_jobs._write_analysis_job(root, job)
    public_job = analysis_jobs._public_job(job, max_skipped_files=max_skipped_files)
    if public_job.get("status") == "completed":
        diag = diagnostics_summary_for_completed_job(diagnostics_summary(root), job)
        public_job["diagnostics_summary"] = diag
        public_job["diagnostics_attention_required"] = diag["attention_required"]
    serialized = json.dumps(public_job, indent=2)
    full_bytes = len(serialized.encode("utf-8"))

    if full_bytes > LARGE_OUTPUT_WARNING_BYTES and not allow_large_output:
        curr_skipped_items = (
            (public_job.get("analysis_coverage", {}).get("skipped_python_files", {}) or {}).get(
                "items", []
            )
        )
        upper_bound = len(curr_skipped_items)

        def _build(count: int) -> str:
            cand = analysis_jobs._public_job(job, max_skipped_files=count)
            emitted = len(
                (cand.get("analysis_coverage", {}).get("skipped_python_files", {}) or {}).get(
                    "items", []
                )
            )
            cand["_output"] = {
                "auto_bounded": True,
                "full_output_bytes": full_bytes,
                "warning_threshold_bytes": LARGE_OUTPUT_WARNING_BYTES,
                "retry": {"allow_large_output": True},
                "bounded_collection": "skipped_files",
                "returned_count": emitted,
            }
            return json.dumps(cand, indent=2)

        bounded = largest_fitting_prefix(upper_bound, _build, min_count=0)
        if bounded is not None:
            return bounded[0]

    return guard_large_output(
        serialized,
        allow_large_output=allow_large_output,
        retry_instruction=(
            "Repeat the same get_analysis_status call with the same repo_path, job_id, and max_skipped_files and set allow_large_output=true."
        ),
    )
