from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from contextor.core.runtime_trace import trace_event


_PUBLISH_FIELDS = (
    "live_publish_status",
    "live_publish_revision",
    "live_publish_warning",
    "live_publish_idempotency_key",
    "live_publish_job_id",
    "live_publish_service_instance_id",
    "live_publish_process_start_identity",
    "live_publish_expected_state_id",
    "live_publish_expected_revision",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_desktop_full_record(
    repo_path: str | Path,
    *,
    started_at: str,
    outcome: object,
    failure: BaseException | None,
) -> None:
    root = Path(repo_path).resolve()
    result = (
        outcome[1]
        if isinstance(outcome, tuple)
        and len(outcome) == 2
        else None
    )
    failed = failure is not None or result is None
    completed_at = _utc_now()
    job_id = uuid4().hex

    record = {
        "job_id": job_id,
        "source": "desktop",
        "operation": "project",
        "repo_path": str(root),
        "target": None,
        "status": "failed" if failed else "completed",
        "created_at": started_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "updated_at": completed_at,
        "message": (
            "Desktop FULL failed."
            if failed else "Desktop FULL completed."
        ),
        "error": (
            f"{type(failure).__name__}: {failure}"
            if failure is not None
            else "Analysis returned no result."
            if result is None
            else None
        ),
    }

    record.update({
        key: getattr(result, key, None)
        if not failed else None
        for key in _PUBLISH_FIELDS
    })

    summary = getattr(result, "summary_data", None)
    if (
        not failed
        and isinstance(summary, dict)
        and isinstance(summary.get("skipped_files"), list)
    ):
        record["skipped_python_files"] = list(
            summary["skipped_files"]
        )

    directory = root / ".contextor" / "analysis_jobs"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{job_id}.json"
    temporary = directory / (
        f"{job_id}.json.{uuid4().hex}.tmp"
    )

    try:
        temporary.write_text(
            json.dumps(
                record, indent=2, ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _record_best_effort(
    repo_path: str | Path,
    *,
    started_at: str,
    outcome: object,
    failure: BaseException | None,
) -> None:
    try:
        _write_desktop_full_record(
            repo_path,
            started_at=started_at,
            outcome=outcome,
            failure=failure,
        )
    except Exception as exc:
        trace_event(
            "ANALYSIS",
            "DESKTOP_FULL_HISTORY_PERSIST_FAILED",
            repo=str(repo_path),
            result=f"{type(exc).__name__}: {exc}",
        )


def run_desktop_full_with_history(
    repo_path: str | Path,
    *,
    runner: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    started_at = _utc_now()
    try:
        outcome = runner(
            repo_path,
            owner="desktop_analysis",
            **kwargs,
        )
    except BaseException as failure:
        _record_best_effort(
            repo_path,
            started_at=started_at,
            outcome=None,
            failure=failure,
        )
        raise

    _record_best_effort(
        repo_path,
        started_at=started_at,
        outcome=outcome,
        failure=None,
    )
    return outcome
