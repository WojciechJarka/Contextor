"""
contextor/core/analysis/full_analysis_coordinator.py

Single-writer cross-process coordinator for full repository analysis.
Guarantees that at most one full analysis execution runs per repository identity
across Desktop GUI, MCP server, and CLI processes.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from contextor.core.errors import AnalysisCancelled
from contextor.core.live_state.runtime import _is_pid_alive
from contextor.core.paths import repo_cache_dir, repo_key
from contextor.core.repository_identity import read_repository_identity


@dataclass(frozen=True, slots=True)
class FullAnalysisLease:
    repo_key: str
    token: str
    owner: str
    lock_path: str
    repo_id: str


class FullAnalysisBusyError(RuntimeError):
    """Raised when the full analysis lease cannot be acquired."""
    pass


_PROCESS_LOCKS: dict[str, threading.RLock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


def _get_process_lock(repo_key_str: str) -> threading.RLock:
    with _PROCESS_LOCKS_GUARD:
        if repo_key_str not in _PROCESS_LOCKS:
            _PROCESS_LOCKS[repo_key_str] = threading.RLock()
        return _PROCESS_LOCKS[repo_key_str]


def _resolve_lock_path(repo_path: str | Path) -> tuple[Path, str, str]:
    """Resolve lock file path, repo_key, and repo_id for a given repository."""
    resolved_root = Path(repo_path).expanduser().resolve()
    key = repo_key(resolved_root)
    identity = read_repository_identity(resolved_root)
    repo_id = identity.repo_id if identity is not None else key

    cache_dir = repo_cache_dir(resolved_root)
    runtime_dir = cache_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    lock_file = runtime_dir / "full_analysis.lock"
    return lock_file, key, repo_id


def acquire_full_analysis(
    repo_path: str | Path,
    *,
    owner: str = "desktop_analysis",
    timeout: float | None = None,
    poll_interval: float = 0.25,
    is_cancelled: Callable[[], bool] | None = None,
    log: Callable[[str], None] | None = None,
) -> FullAnalysisLease:
    """
    Acquire exclusive single-writer lease for full repository analysis.
    Blocks if another process or thread holds the lease until released,
    timed out, or cancelled.
    """
    lock_file, key, repo_id = _resolve_lock_path(repo_path)
    proc_lock = _get_process_lock(key)

    # In-process lock acquisition
    start_time = time.monotonic()
    deadline = (start_time + timeout) if timeout is not None else None

    # Wait for process-level lock
    while True:
        if is_cancelled and is_cancelled():
            raise AnalysisCancelled("Full analysis cancelled while waiting for local lock.")
        acquired_proc = proc_lock.acquire(blocking=False)
        if acquired_proc:
            break
        if deadline is not None and time.monotonic() >= deadline:
            raise FullAnalysisBusyError(
                f"Timed out waiting for in-process full analysis lock for {repo_id}"
            )
        time.sleep(min(poll_interval, 0.1))

    token = uuid.uuid4().hex
    fd = -1
    logged_waiting = False

    try:
        while True:
            if is_cancelled and is_cancelled():
                raise AnalysisCancelled("Full analysis cancelled while waiting for repository lease.")

            # Attempt atomic creation of lock file
            try:
                fd = os.open(
                    lock_file,
                    os.O_CREAT | os.O_EXCL | os.O_RDWR,
                )
                payload = {
                    "pid": os.getpid(),
                    "token": token,
                    "owner": str(owner),
                    "repo_id": str(repo_id),
                    "timestamp": time.time(),
                }
                data = json.dumps(payload).encode("utf-8")
                os.write(fd, data)
                os.close(fd)
                fd = -1
                return FullAnalysisLease(
                    repo_key=key,
                    token=token,
                    owner=str(owner),
                    lock_path=str(lock_file),
                    repo_id=str(repo_id),
                )
            except (FileExistsError, PermissionError):
                # Lock file exists or is locked by another process
                existing_pid = None
                existing_owner = "unknown"
                try:
                    raw = lock_file.read_text(encoding="utf-8")
                    if raw:
                        parsed = json.loads(raw)
                        existing_pid = parsed.get("pid")
                        existing_owner = parsed.get("owner", "unknown")
                except Exception:
                    pass

                # Check for dead process (stale lock recovery)
                if existing_pid is not None and not _is_pid_alive(existing_pid):
                    try:
                        lock_file.unlink(missing_ok=True)
                        if log:
                            log(f"Recovered stale full-analysis lock from terminated PID {existing_pid}")
                        continue
                    except Exception:
                        pass

                if not logged_waiting:
                    if log:
                        log(f"Waiting for full analysis lease on repository {repo_id} (owned by {existing_owner})...")
                    logged_waiting = True

                if deadline is not None and time.monotonic() >= deadline:
                    raise FullAnalysisBusyError(
                        f"Repository {repo_id} is currently locked for full analysis by owner '{existing_owner}' (PID {existing_pid})"
                    )

                time.sleep(poll_interval)
    except Exception:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        proc_lock.release()
        raise


def release_full_analysis(lease: FullAnalysisLease) -> None:
    """Release the full analysis lease."""
    if not isinstance(lease, FullAnalysisLease):
        return

    lock_file = Path(lease.lock_path)
    try:
        if lock_file.exists():
            try:
                raw = lock_file.read_text(encoding="utf-8")
                if raw:
                    parsed = json.loads(raw)
                    if parsed.get("token") == lease.token:
                        lock_file.unlink(missing_ok=True)
            except Exception:
                lock_file.unlink(missing_ok=True)
    finally:
        proc_lock = _get_process_lock(lease.repo_key)
        try:
            proc_lock.release()
        except RuntimeError:
            pass


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
    lease = acquire_full_analysis(
        path,
        owner=owner,
        timeout=timeout,
        is_cancelled=is_cancelled,
        log=log,
    )
    try:
        if analysis_fn is not None:
            return analysis_fn(
                str(path),
                log=log,
                progress_callback=progress_callback,
                additional_excludes=additional_excludes,
                owner=owner,
                **kwargs,
            )
        from contextor.core.api.facade import ContextorFacade
        return ContextorFacade.analyze_project(
            str(path),
            log=log,
            progress_callback=progress_callback,
            additional_excludes=additional_excludes,
            owner=owner,
            **kwargs,
        )
    finally:
        release_full_analysis(lease)
