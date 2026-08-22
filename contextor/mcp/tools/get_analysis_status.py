import json
import os
from pathlib import Path

from contextor.mcp import analysis_jobs
from contextor.mcp.output_guard import guard_large_output


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
    serialized = json.dumps(
        analysis_jobs._public_job(job, max_skipped_files=max_skipped_files),
        indent=2,
    )
    return guard_large_output(
        serialized,
        allow_large_output=allow_large_output,
        retry_instruction=(
            "Repeat the same get_analysis_status call with the same repo_path, job_id, and max_skipped_files and set allow_large_output=true."
        ),
    )
