"""
contextor/core/analysis/full_analysis_coordinator.py

Single-writer cross-process coordinator for full repository analysis.
Guarantees that at most one full analysis execution runs per repository identity
across Desktop GUI, MCP server, and CLI processes using native OS file locking.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from contextor.core.errors import AnalysisCancelled
from contextor.core.paths import repo_cache_dir, repo_key
from contextor.core.repository_identity import read_repository_identity


@dataclass(frozen=True, slots=True)
class FullAnalysisLease:
    repo_key: str
    token: str
    owner: str
    lock_path: str
    repo_id: str
    lock_fd: int


class FullAnalysisBusyError(RuntimeError):
    """Raised when the full analysis lease cannot be acquired."""
    pass


_PROCESS_LOCKS: dict[str, threading.Lock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


def _get_process_lock(
    repo_key_str: str,
) -> threading.Lock:
    with _PROCESS_LOCKS_GUARD:
        lock = _PROCESS_LOCKS.get(repo_key_str)
        if lock is None:
            lock = threading.Lock()
            _PROCESS_LOCKS[repo_key_str] = lock
        return lock


def _prepare_lock_fd(lock_path: Path) -> int:
    lock_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT,
        0o600,
    )

    if os.fstat(fd).st_size == 0:
        os.write(fd, b"\0")
        os.fsync(fd)

    os.lseek(fd, 0, os.SEEK_SET)
    return fd


def _try_lock_fd(fd: int) -> bool:
    os.lseek(fd, 0, os.SEEK_SET)

    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(
                fd,
                msvcrt.LK_NBLCK,
                1,
            )
            return True
        except OSError:
            return False

    import fcntl

    try:
        fcntl.flock(
            fd,
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
        return True
    except BlockingIOError:
        return False


def _unlock_fd(fd: int) -> None:
    try:
        os.lseek(fd, 0, os.SEEK_SET)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(
                fd,
                msvcrt.LK_UNLCK,
                1,
            )
        else:
            import fcntl

            fcntl.flock(
                fd,
                fcntl.LOCK_UN,
            )
    finally:
        os.close(fd)


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

    start_time = time.monotonic()
    deadline = (
        start_time + timeout
        if timeout is not None
        else None
    )

    while True:
        if is_cancelled and is_cancelled():
            raise AnalysisCancelled(
                "Full analysis cancelled while waiting for local lock."
            )

        if proc_lock.acquire(blocking=False):
            break

        if (
            deadline is not None
            and time.monotonic() >= deadline
        ):
            raise FullAnalysisBusyError(
                "Timed out waiting for in-process full analysis lock for "
                f"{repo_id}"
            )

        time.sleep(
            min(max(poll_interval, 0.01), 0.25)
        )

    fd = -1
    logged_waiting = False

    try:
        fd = _prepare_lock_fd(lock_file)

        while True:
            if is_cancelled and is_cancelled():
                raise AnalysisCancelled(
                    "Full analysis cancelled while waiting for repository lease."
                )

            if _try_lock_fd(fd):
                token = uuid.uuid4().hex

                metadata = {
                    "pid": os.getpid(),
                    "token": token,
                    "owner": str(owner),
                    "repo_id": str(repo_id),
                    "timestamp": time.time(),
                }

                # Metadata is diagnostic only.
                # OS lock ownership is authoritative.
                os.ftruncate(fd, 0)
                os.lseek(fd, 0, os.SEEK_SET)
                os.write(
                    fd,
                    json.dumps(metadata).encode("utf-8"),
                )
                os.fsync(fd)

                # Ensure byte 0 remains inside the locked file after metadata write.
                os.lseek(fd, 0, os.SEEK_SET)

                return FullAnalysisLease(
                    repo_key=key,
                    token=token,
                    owner=str(owner),
                    lock_path=str(lock_file),
                    repo_id=str(repo_id),
                    lock_fd=fd,
                )

            if not logged_waiting:
                if log:
                    log(
                        f"Waiting for full analysis lease on repository {repo_id}..."
                    )
                logged_waiting = True

            if (
                deadline is not None
                and time.monotonic() >= deadline
            ):
                raise FullAnalysisBusyError(
                    f"Repository {repo_id} is currently locked for full analysis"
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


def release_full_analysis(
    lease: FullAnalysisLease,
) -> None:
    """Release the full analysis lease."""
    if not isinstance(
        lease,
        FullAnalysisLease,
    ):
        return

    try:
        _unlock_fd(lease.lock_fd)
    finally:
        proc_lock = _get_process_lock(
            lease.repo_key
        )
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
