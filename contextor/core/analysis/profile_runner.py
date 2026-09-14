from __future__ import annotations
from pathlib import Path
from contextor.core.analysis.full_analysis_coordinator import (
    FullAnalysisBusyError,
    run_full_analysis_exclusive,
)
from contextor.core.analysis.profile_analysis import (
    PROFILE_SCHEMA,
    build_analysis_profile,
)
from contextor.core.runtime_trace import (
    capture_trace_events,
    new_trace_operation,
    trace_operation,
)
def run_analysis_profile(
    repo_path: str | Path,
    *,
    exclude_paths: list[str] | None = None,
) -> dict[str, object]:
    root = Path(repo_path).expanduser().resolve()
    operation_id = new_trace_operation("profile")
    with trace_operation(operation_id), capture_trace_events() as events:
        try:
            run_full_analysis_exclusive(
                root,
                owner="mcp_analysis",
                timeout=0.0,
                additional_excludes=exclude_paths,
            )
        except FullAnalysisBusyError:
            return {
                "schema": PROFILE_SCHEMA,
                "status": "busy",
                "operation_id": operation_id,
                "reason_code": "full_analysis_busy",
            }
    return build_analysis_profile(
        events,
        operation_id=operation_id,
    )
__all__ = ["run_analysis_profile"]
