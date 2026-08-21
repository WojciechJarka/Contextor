import asyncio
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from contextor.core.api.facade import ContextorFacade
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.query_helpers import bounded_items
from contextor.mcp_process_registry import registry_dir


_MCP_OWNER_TOKEN: str = uuid4().hex
_analysis_lock = threading.Lock()
_analysis_job_lock = threading.RLock()
_analysis_tasks: dict[str, threading.Thread] = {}
_analysis_jobs_by_repo: dict[str, str] = {}


def _mcp_cache_root(root: Path) -> Path:
    from contextor.core.paths import app_cache_dir

    return app_cache_dir()


def _analysis_job_dir(root: Path) -> Path:
    return root / ".contextor" / "analysis_jobs"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(root: Path, job_id: str) -> Path:
    if len(job_id) != 32 or any(char not in "0123456789abcdef" for char in job_id):
        raise ValueError("Invalid analysis job ID.")
    return _analysis_job_dir(root) / f"{job_id}.json"


def _write_analysis_job(root: Path, job: dict) -> None:
    directory = _analysis_job_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    target = _job_path(root, str(job["job_id"]))
    temporary = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
    payload = {**job, "updated_at": _utc_now()}
    with _analysis_job_lock:
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, target)


def _read_analysis_job(root: Path, job_id: str) -> dict | None:
    try:
        path = _job_path(root, job_id)
    except ValueError:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _latest_analysis_job(root: Path) -> dict | None:
    directory = _analysis_job_dir(root)
    if not directory.is_dir():
        return None
    candidates = sorted(
        directory.glob("*.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    for path in candidates:
        job = _read_analysis_job(root, path.stem)
        if job is not None:
            return job
    return None




def _public_job(
    job: dict,
    *,
    reused: bool = False,
    max_skipped_files: int | None = 10,
) -> dict:
    visible = {
        key: job.get(key)
        for key in (
            "job_id", "operation", "repo_path", "target", "status",
            "created_at", "started_at", "completed_at", "updated_at",
            "message", "error", "live_publish_status",
            "live_publish_revision", "live_publish_warning",
        )
    }
    if "skipped_python_files" in job:
        skipped_files = list(job["skipped_python_files"])
        selected, total, truncated = bounded_items(skipped_files, max_skipped_files)
        visible["analysis_coverage"] = {
            "skipped_python_files": {
                "total": total,
                "syntax_error_count": sum(
                    "not valid Python" in str(item.get("reason", ""))
                    for item in skipped_files
                ),
                "truncated": truncated,
                "items": selected,
            }
        }
    visible["reused"] = reused
    return visible


def _stderr_log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


async def _run_analysis_worker(
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
    log=None,
) -> dict:
    effective_log = log or _stderr_log

    def run() -> dict:
        with _analysis_lock:
            previous_cache = os.environ.get("CONTEXTOR_CACHE_DIR")
            previous_registry = os.environ.get("CONTEXTOR_MCP_PROCESS_REGISTRY")
            os.environ["CONTEXTOR_CACHE_DIR"] = str(_mcp_cache_root(root))
            os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] = str(registry_dir(root))
            try:
                if operation == "project":
                    _, result = ContextorFacade.analyze_project(
                        str(root), log=effective_log, additional_excludes=exclude_paths
                    )
                    if result is None:
                        raise RuntimeError("Analysis returned no canonical state.")
                    skipped_files = (getattr(result, "summary_data", {}) or {}).get(
                        "skipped_files", []
                    )
                    if not isinstance(skipped_files, list):
                        skipped_files = []
                    return {"skipped_python_files": skipped_files}
                if operation == "layer":
                    ContextorFacade.analyze_layer(
                        str(root), str(target), log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                elif operation == "single_file":
                    ContextorFacade.analyze_single_file(
                        str(target), str(root), log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                else:
                    raise ValueError(f"Unsupported analysis operation: {operation}")
                return {}
            finally:
                if previous_cache is None:
                    os.environ.pop("CONTEXTOR_CACHE_DIR", None)
                else:
                    os.environ["CONTEXTOR_CACHE_DIR"] = previous_cache
                if previous_registry is None:
                    os.environ.pop("CONTEXTOR_MCP_PROCESS_REGISTRY", None)
                else:
                    os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] = previous_registry

    return await asyncio.to_thread(run)


async def _execute_analysis_job(
    root: Path,
    job: dict,
    target: Path | None,
    exclude_paths: list[str] | None,
) -> None:
    job = {
        **job, "status": "running", "started_at": _utc_now(),
        "message": "Analysis started.",
    }
    _write_analysis_job(root, job)

    def job_log(message: str) -> None:
        nonlocal job
        _stderr_log(message)
        job = {**job, "message": str(message)}
        _write_analysis_job(root, job)

    try:
        analysis_outcome = await _run_analysis_worker(
            str(job["operation"]), root, target, exclude_paths, log=job_log
        )
        if job["operation"] == "project":
            mcp_runtime._live_engines.pop(str(root), None)
            engine = mcp_runtime.get_or_init_engine(root)
            if engine is None:
                raise RuntimeError(
                    "Analysis completed but canonical state could not be loaded."
                )
            engine_state = engine.state
            from contextor.core.live_state import connect_or_start
            try:
                live_client = connect_or_start(
                    root, owner_pid=os.getpid(), owner_token=_MCP_OWNER_TOKEN,
                    timeout=10.0,
                )
                published = live_client.publish(
                    engine_state, origin="mcp_analysis", timeout=10.0
                )
                revision = int(published["revision"])
                mcp_runtime._live_engine_revisions[str(root)] = revision
                job = {
                    **job, "live_publish_status": "success",
                    "live_publish_revision": revision,
                    "live_publish_warning": None,
                }
            except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError) as live_exc:
                publish_status = (
                    "timed_out" if isinstance(live_exc, TimeoutError) else "failed"
                )
                warning = f"{type(live_exc).__name__}: {live_exc}"
                _stderr_log(f"Warning: Live state publish {publish_status}: {warning}")
                job = {
                    **job, "live_publish_status": publish_status,
                    "live_publish_revision": None,
                    "live_publish_warning": warning,
                }
        publish_status = job.get("live_publish_status")
        completed_message = "Analysis completed successfully."
        if job["operation"] == "project" and publish_status != "success":
            completed_message = (
                "Analysis completed, but canonical LIVE publish "
                f"{publish_status or 'failed'}."
            )
        job = {
            **job, **(analysis_outcome or {}), "status": "completed",
            "completed_at": _utc_now(), "message": completed_message, "error": None,
        }
        _write_analysis_job(root, job)
    except Exception as exc:
        live_publish_status = job.get("live_publish_status")
        if job.get("operation") == "project" and live_publish_status == "pending":
            live_publish_status = "not_attempted"
        job = {
            **job, "status": "failed", "completed_at": _utc_now(),
            "message": "Analysis failed.",
            "error": f"{type(exc).__name__}: {exc}",
            "live_publish_status": live_publish_status,
        }
        _write_analysis_job(root, job)
    finally:
        with _analysis_job_lock:
            _analysis_tasks.pop(str(job["job_id"]), None)
            if _analysis_jobs_by_repo.get(str(root)) == job["job_id"]:
                _analysis_jobs_by_repo.pop(str(root), None)


def _start_analysis_job(
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
) -> dict:
    repo_key = str(root)
    with _analysis_job_lock:
        active_id = _analysis_jobs_by_repo.get(repo_key)
        active_task = _analysis_tasks.get(active_id) if active_id else None
        if active_id and active_task is not None and active_task.is_alive():
            existing = _read_analysis_job(root, active_id)
            if existing is not None:
                return _public_job(existing, reused=True)
        job_id = uuid4().hex
        job = {
            "job_id": job_id, "operation": operation, "repo_path": repo_key,
            "target": str(target) if target is not None else None,
            "exclude_paths": list(exclude_paths or []), "status": "queued",
            "created_at": _utc_now(), "started_at": None, "completed_at": None,
            "message": "Analysis accepted.", "error": None,
            "live_publish_status": (
                "pending" if operation == "project" else "not_applicable"
            ),
            "live_publish_revision": None, "live_publish_warning": None,
            "owner_pid": os.getpid(),
        }
        _write_analysis_job(root, job)
        def run_job() -> None:
            asyncio.run(_execute_analysis_job(root, job, target, exclude_paths))
        task = threading.Thread(
            target=run_job, name=f"contextor-analysis-{job_id}", daemon=True
        )
        _analysis_jobs_by_repo[repo_key] = job_id
        _analysis_tasks[job_id] = task
        task.start()
        return _public_job(job)
