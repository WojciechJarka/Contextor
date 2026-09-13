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
from contextor.core.runtime_trace import trace_event


@dataclass(frozen=True, slots=True)
class FullAnalysisLease:
    repo_key: str
    token: str
    owner: str
    lock_path: str
    repo_id: str
    lock_fd: int
    owner_pid: int = 0
    owner_process_start_identity: int | None = None


class FullAnalysisBusyError(RuntimeError):
    """Raised when the full analysis lease cannot be acquired."""
    pass


# A dead process normally releases its OS lock immediately. This bound is only
# for the defensive case where a stale lock handle survives process death; it
# prevents an orphan diagnostic from turning into an unbounded wait.
ORPHAN_RECOVERY_TIMEOUT_SECONDS = 5.0


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


def _read_lease_metadata(fd: int) -> dict[str, Any] | None:
    """Read diagnostic owner metadata without treating it as lock authority."""
    try:
        original_offset = os.lseek(fd, 0, os.SEEK_CUR)
        os.lseek(fd, 0, os.SEEK_SET)
        payload = os.read(fd, 16 * 1024)
    except (OSError, UnicodeError):
        return None
    finally:
        try:
            os.lseek(fd, original_offset, os.SEEK_SET)
        except (OSError, UnboundLocalError):
            pass

    if not payload:
        return None
    try:
        metadata = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return metadata if isinstance(metadata, dict) else None


def _lease_metadata_path(lock_path: Path) -> Path:
    return lock_path.with_name("full_analysis.lease.json")


def _read_lease_metadata_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    if not payload:
        return None
    try:
        metadata = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return metadata if isinstance(metadata, dict) else None


def _write_lease_metadata_file(
    path: Path,
    metadata: dict[str, Any],
) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _process_identity(pid: int) -> tuple[str | None, int | None, bool]:
    """Use the existing process-ownership identity model for lease diagnostics."""
    from contextor.mcp_process_registry import process_identity

    return process_identity(pid)


def _lease_owner_state(
    metadata: dict[str, Any] | None,
) -> tuple[str, str]:
    """Return ``active``, ``orphaned`` or ``unknown`` for lease metadata."""
    if not metadata:
        return "unknown", "owner metadata unavailable"

    try:
        owner_pid = int(metadata["pid"])
    except (KeyError, TypeError, ValueError):
        return "orphaned", "invalid owner pid"

    image, process_start_identity, alive = _process_identity(owner_pid)
    owner = str(metadata.get("owner") or "unknown")
    description = f"owner={owner}, pid={owner_pid}"
    if not alive:
        return "orphaned", f"{description} is not alive"

    expected_image = str(metadata.get("executable") or "")
    if not expected_image:
        return "unknown", f"{description} identity metadata unavailable"
    if not image:
        return "unknown", f"{description} executable identity unavailable"
    if Path(image).name.casefold() != Path(expected_image).name.casefold():
        return "orphaned", f"{description} has a reused process identity"

    expected_start = metadata.get("process_start_identity")
    if expected_start is not None:
        if process_start_identity is None:
            return "unknown", f"{description} start identity unavailable"
        try:
            if int(expected_start) != int(process_start_identity):
                return "orphaned", f"{description} has a reused process identity"
        except (TypeError, ValueError):
            return "orphaned", f"{description} has invalid start identity"

    return "active", description


def _log_orphan_recovery(
    log: Callable[[str], None] | None,
    repo_id: str,
    reason: str,
) -> None:
    if log:
        log(
            f"Recovering orphaned full analysis lease on repository {repo_id} "
            f"({reason})."
        )


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
    logged_recovery = False
    orphan_recovery_deadline: float | None = None
    unknown_owner_deadline: float | None = None

    try:
        fd = _prepare_lock_fd(lock_file)

        while True:
            if is_cancelled and is_cancelled():
                raise AnalysisCancelled(
                    "Full analysis cancelled while waiting for repository lease."
                )

            previous_metadata = _read_lease_metadata(fd)
            if previous_metadata is None:
                previous_metadata = _read_lease_metadata_file(
                    _lease_metadata_path(lock_file)
                )
            if _try_lock_fd(fd):
                previous_owner_state, previous_owner_reason = _lease_owner_state(
                    previous_metadata
                )
                if previous_owner_state == "orphaned" and not logged_recovery:
                    _log_orphan_recovery(
                        log,
                        repo_id,
                        previous_owner_reason,
                    )
                    logged_recovery = True
                token = uuid.uuid4().hex

                owner_image, owner_process_start_identity, _ = _process_identity(
                    os.getpid()
                )

                metadata = {
                    "pid": os.getpid(),
                    "token": token,
                    "owner": str(owner),
                    "repo_id": str(repo_id),
                    "timestamp": time.time(),
                }
                if owner_image:
                    metadata["executable"] = owner_image
                if owner_process_start_identity is not None:
                    metadata["process_start_identity"] = owner_process_start_identity

                _write_lease_metadata_file(
                    _lease_metadata_path(lock_file),
                    metadata,
                )

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
                    owner_pid=os.getpid(),
                    owner_process_start_identity=owner_process_start_identity,
                )

            if not logged_waiting:
                if log:
                    log(
                        f"Waiting for full analysis lease on repository {repo_id}..."
                    )
                    owner_state, owner_reason = _lease_owner_state(previous_metadata)
                    if owner_state == "active":
                        log(
                            "Full analysis lease has a valid active owner "
                            f"({owner_reason})."
                        )
                    elif owner_state == "unknown":
                        log(
                            "Full analysis lease owner could not be verified; "
                            f"continuing to wait ({owner_reason})."
                        )
                logged_waiting = True

            owner_state, owner_reason = _lease_owner_state(previous_metadata)
            if owner_state == "orphaned":
                unknown_owner_deadline = None
                if orphan_recovery_deadline is None:
                    orphan_recovery_deadline = min(
                        deadline
                        if deadline is not None
                        else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS,
                        time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS,
                    )
                if not logged_recovery:
                    _log_orphan_recovery(log, repo_id, owner_reason)
                    logged_recovery = True
                if time.monotonic() >= orphan_recovery_deadline:
                    raise FullAnalysisBusyError(
                        f"Timed out recovering orphaned full analysis lease for "
                        f"{repo_id}"
                    )
            elif owner_state == "unknown":
                orphan_recovery_deadline = None
                if unknown_owner_deadline is None:
                    unknown_owner_deadline = min(
                        deadline
                        if deadline is not None
                        else time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS,
                        time.monotonic() + ORPHAN_RECOVERY_TIMEOUT_SECONDS,
                    )
                if time.monotonic() >= unknown_owner_deadline:
                    raise FullAnalysisBusyError(
                        f"Timed out waiting because full analysis lease owner "
                        f"could not be verified for {repo_id}"
                    )
            else:
                orphan_recovery_deadline = None
                unknown_owner_deadline = None

            if (
                deadline is not None
                and time.monotonic() >= deadline
            ):
                raise FullAnalysisBusyError(
                    f"Repository {repo_id} is currently locked for full analysis"
                )

            time.sleep(min(max(poll_interval, 0.01), 0.25))

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
    repo = str(Path(path).resolve())
    full_started = time.monotonic()
    lease_wait_started = full_started
    lease = acquire_full_analysis(
        path,
        owner=owner,
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
            result=f"total_ms={total_ms:.3f}",
        )
