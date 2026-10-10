"""
High-level full-analysis runner and compatibility exports for the lease owner.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from contextor.core.runtime_trace import trace_event
from contextor.core.analysis.full_analysis_lease import (
    FullAnalysisLease,
    FullAnalysisBusyError,
    ORPHAN_RECOVERY_TIMEOUT_SECONDS,
    _PROCESS_LOCKS,
    _PROCESS_LOCKS_GUARD,
    _ADMISSION_LOCKS,
    _ADMISSION_LOCKS_GUARD,
    _ADMISSION_TRACE_FIELD_NAMES,
    _select_admission_trace_fields,
    _get_process_lock,
    _get_admission_lock,
    _acquire_process_lock_until,
    _canonical_writer_admission,
    _prepare_lock_fd,
    _try_lock_fd,
    _unlock_fd,
    _read_lease_metadata,
    _lease_metadata_path,
    _read_lease_metadata_file,
    _write_lease_metadata_file,
    _process_identity,
    _lease_owner_state,
    _log_orphan_recovery,
    _resolve_lock_path,
    acquire_full_analysis,
    release_full_analysis,
)

def run_full_analysis_exclusive(
    path: str | Path,
    *,
    owner: str = "desktop_analysis",
    analysis_fn: Callable[..., Any] | None = None,
    log: Callable[[str], None] | None = None,
    progress_callback: Any = None,
    additional_excludes: list[str] | None = None,
    timeout: float | None = None,
    is_cancelled: Callable[[], bool] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Execute full repository analysis while holding an exclusive repository lease.
    Guarantees single-writer execution across Desktop, MCP, and CLI.
    """
    repo = str(Path(path).resolve())
    full_started = time.monotonic()
    lease_wait_started = full_started
    lease = acquire_full_analysis(
        path,
        owner=owner,
        writer_kind="full_analysis",
        timeout=timeout,
        is_cancelled=is_cancelled,
        log=log,
    )
    try:
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_LEASE_ACQUIRED",
            owner=owner,
            repo=repo,
            wait_ms=(time.monotonic() - lease_wait_started) * 1000.0,
            timing_semantics="critical_path_lease_wait",
        )
        if analysis_fn is not None:
            analysis_started = time.monotonic()
            analysis_result = analysis_fn(
                str(path),
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
                owner=owner,
                **kwargs,
            )
        else:
            from contextor.core.api.facade import ContextorFacade

            analysis_started = time.monotonic()
            analysis_result = ContextorFacade.analyze_project(
                str(path),
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
                owner=owner,
                **kwargs,
            )
        analysis_ms = (time.monotonic() - analysis_started) * 1000.0
        total_before_release_ms = (time.monotonic() - full_started) * 1000.0
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_BODY_END",
            owner=owner,
            repo=repo,
            analysis_ms=analysis_ms,
            total_before_release_ms=total_before_release_ms,
            elapsed_ms=analysis_ms,
            timing_semantics="critical_path_analysis_body",
            result=(
                f"analysis_ms={analysis_ms:.3f};"
                f"total_before_release_ms={total_before_release_ms:.3f}"
            ),
        )
        return analysis_result
    finally:
        release_full_analysis(lease)
        total_ms = (time.monotonic() - full_started) * 1000.0
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_END",
            owner=owner,
            repo=repo,
            total_ms=total_ms,
            elapsed_ms=total_ms,
            timing_semantics="critical_path_total",
            result=f"total_ms={total_ms:.3f}",
        )
