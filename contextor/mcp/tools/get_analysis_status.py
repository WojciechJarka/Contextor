import json
import os
from pathlib import Path

from contextor.mcp import analysis_jobs
from contextor.mcp.output_guard import (
    LARGE_OUTPUT_WARNING_BYTES,
    guard_large_output,
    largest_fitting_prefix,
)


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
    job = (
        analysis_jobs._read_analysis_job(root, job_id)
        if job_id is not None
        else analysis_jobs._latest_analysis_job(root)
    )
    if job is None:
        return json.dumps(
            {"status": "not_found", "job_id": job_id, "repo_path": str(root)},
            indent=2,
        )
    if (
        job.get("status") in {"queued", "running"}
        and job.get("owner_pid") != os.getpid()
    ):
        job = {
            **job,
            "status": "interrupted",
            "completed_at": analysis_jobs._utc_now(),
            "message": "The MCP server process that owned this job is no longer active.",
            "error": "owner_process_changed",
        }
        analysis_jobs._write_analysis_job(root, job)
    public_job = analysis_jobs._public_job(job, max_skipped_files=max_skipped_files)
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

