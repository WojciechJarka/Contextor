"""Lifecycle control for the persistent shared Contextor MCP backend."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from fastmcp import Client

from contextor.core.paths import package_root
from contextor.mcp_backend_secret import (
    get_or_create_backend_token,
    read_backend_token,
)
from contextor.mcp_backend_state import (
    BACKEND_TRANSPORT as _BACKEND_TRANSPORT,
    PersistentBackendRecord,
    backend_state_dir,
    read_backend_record,
    remove_backend_record_if_exact,
)
from contextor.mcp_process_registry import (
    process_identity,
    read_records,
    record_matches_process,
    remove_record,
    terminate_registered_process,
)


BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8765
BACKEND_MCP_PATH = "/mcp"
BACKEND_SERVER_NAME = "Contextor"
_CREATE_BREAKAWAY_FROM_JOB = 0x01000000

BackendState = Literal[
    "stopped",
    "stale",
    "unready",
    "running",
]


class BackendControlError(RuntimeError):
    """Persistent backend lifecycle control failed."""


@dataclass(
    frozen=True,
    slots=True,
)
class BackendStatus:
    state: BackendState
    ready: bool
    detail: str
    record: PersistentBackendRecord | None

    @property
    def endpoint(
        self,
    ) -> str | None:
        if self.record is None:
            return None

        return (
            f"http://{self.record.host}:"
            f"{self.record.port}"
            f"{BACKEND_MCP_PATH}"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "state": self.state,
            "ready": self.ready,
            "detail": self.detail,
            "endpoint": self.endpoint,
            "pid": (
                None
                if self.record is None
                else self.record.pid
            ),
            "instance_id": (
                None
                if self.record is None
                else self.record.instance_id
            ),
        }


def backend_process_registry_dir() -> Path:
    return (
        backend_state_dir()
        / "processes"
    )


def backend_control_lock_path() -> Path:
    return (
        backend_state_dir()
        / "control.lock"
    )


def _backend_endpoint(
    record: PersistentBackendRecord,
) -> str:
    return (
        f"http://{record.host}:"
        f"{record.port}"
        f"{BACKEND_MCP_PATH}"
    )


def _record_process_matches(
    record: PersistentBackendRecord,
) -> bool:
    return record_matches_process(
        record.to_dict()
    )


async def _probe_backend_async(
    record: PersistentBackendRecord,
    token: str,
    *,
    timeout: float,
) -> bool:
    try:
        async with Client(
            _backend_endpoint(record),
            auth=token,
            timeout=timeout,
            init_timeout=timeout,
        ) as client:
            initialized = (
                client.initialize_result
            )

            if initialized is None:
                return False

            if (
                initialized.serverInfo.name
                != BACKEND_SERVER_NAME
            ):
                return False

            return bool(
                await client.ping()
            )

    except Exception:
        return False


def _probe_backend(
    record: PersistentBackendRecord,
    token: str,
    *,
    timeout: float,
) -> bool:
    return asyncio.run(
        _probe_backend_async(
            record,
            token,
            timeout=timeout,
        )
    )


def get_backend_status(
    *,
    probe_timeout: float = 2.0,
) -> BackendStatus:
    record = read_backend_record()

    if record is None:
        return BackendStatus(
            state="stopped",
            ready=False,
            detail="no persistent backend record",
            record=None,
        )

    if not _record_process_matches(
        record
    ):
        return BackendStatus(
            state="stale",
            ready=False,
            detail=(
                "persistent backend record does not "
                "match a live process identity"
            ),
            record=record,
        )

    token = read_backend_token()

    if token is None:
        return BackendStatus(
            state="unready",
            ready=False,
            detail=(
                "backend owner is live but bearer "
                "token is unavailable"
            ),
            record=record,
        )

    if not _probe_backend(
        record,
        token,
        timeout=probe_timeout,
    ):
        return BackendStatus(
            state="unready",
            ready=False,
            detail=(
                "backend owner is live but authenticated "
                "MCP readiness was not confirmed"
            ),
            record=record,
        )

    return BackendStatus(
        state="running",
        ready=True,
        detail=(
            "authenticated Contextor MCP backend is ready"
        ),
        record=record,
    )


_THREAD_LOCKS: dict[
    str,
    threading.Lock,
] = {}

_THREAD_LOCKS_GUARD = (
    threading.Lock()
)


def _thread_lock_for(
    path: Path,
) -> threading.Lock:
    key = os.path.normcase(
        str(path)
    )

    with _THREAD_LOCKS_GUARD:
        return (
            _THREAD_LOCKS
            .setdefault(
                key,
                threading.Lock(),
            )
        )


class _BackendControlLock(
    AbstractContextManager[
        "_BackendControlLock"
    ]
):
    def __init__(
        self,
        path: Path,
        *,
        timeout: float,
    ) -> None:
        self.path = path
        self.timeout = max(
            0.0,
            float(timeout),
        )
        self._thread_lock = (
            _thread_lock_for(
                path
            )
        )
        self._file: Any = None

    def __enter__(
        self,
    ) -> "_BackendControlLock":
        if not self._thread_lock.acquire(
            timeout=self.timeout
        ):
            raise BackendControlError(
                "persistent backend control lock is busy"
            )

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._file = self.path.open(
                "a+b"
            )

            if (
                self.path.stat().st_size
                == 0
            ):
                self._file.write(
                    b"0"
                )
                self._file.flush()

            deadline = (
                time.monotonic()
                + self.timeout
            )

            while True:
                try:
                    self._file.seek(0)

                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(
                            self._file.fileno(),
                            msvcrt.LK_NBLCK,
                            1,
                        )

                    else:
                        import fcntl

                        fcntl.flock(
                            self._file.fileno(),
                            fcntl.LOCK_EX
                            | fcntl.LOCK_NB,
                        )

                    return self

                except (
                    OSError,
                    BlockingIOError,
                ) as exc:
                    if (
                        time.monotonic()
                        >= deadline
                    ):
                        raise BackendControlError(
                            "persistent backend control lock is busy"
                        ) from exc

                    time.sleep(
                        0.01
                    )

        except Exception:
            self._close()
            self._thread_lock.release()
            raise

    def _close(
        self,
    ) -> None:
        if self._file is None:
            return

        try:
            self._file.seek(0)

            if os.name == "nt":
                import msvcrt

                msvcrt.locking(
                    self._file.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )

            else:
                import fcntl

                fcntl.flock(
                    self._file.fileno(),
                    fcntl.LOCK_UN,
                )

        except OSError:
            pass

        try:
            self._file.close()
        finally:
            self._file = None

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        tb: Any,
    ) -> None:
        try:
            self._close()
        finally:
            self._thread_lock.release()


def _backend_python() -> Path:
    installation = package_root()

    if sys.platform == "win32":
        interpreter = (
            installation
            / ".venv"
            / "Scripts"
            / "python.exe"
        )

    else:
        interpreter = (
            installation
            / ".venv"
            / "bin"
            / "python"
        )

    if not interpreter.is_file():
        raise BackendControlError(
            "Contextor backend interpreter was not found: "
            f"{interpreter}"
        )

    return interpreter


def _backend_environment(
    token: str,
) -> dict[str, str]:
    env = dict(
        os.environ
    )

    env[
        "CONTEXTOR_MCP_TRANSPORT"
    ] = _BACKEND_TRANSPORT

    env[
        "CONTEXTOR_MCP_SERVER_ROLE"
    ] = "persistent-backend"

    env[
        "CONTEXTOR_MCP_HOST"
    ] = BACKEND_HOST

    env[
        "CONTEXTOR_MCP_PORT"
    ] = str(
        BACKEND_PORT
    )

    env[
        "CONTEXTOR_MCP_PROCESS_REGISTRY"
    ] = str(
        backend_process_registry_dir()
        .expanduser()
        .resolve()
    )

    env[
        "CONTEXTOR_MCP_TOKEN"
    ] = token

    return env


def _spawn_backend_process(
    token: str,
) -> subprocess.Popen:
    interpreter = (
        _backend_python()
    )

    cmd = [
        str(interpreter),
        "-u",
        "-m",
        "contextor.mcp_main",
    ]

    kwargs = {
        "cwd": str(
            package_root()
        ),
        "env": (
            _backend_environment(
                token
            )
        ),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if sys.platform != "win32":
        return subprocess.Popen(
            cmd,
            creationflags=0,
            **kwargs,
        )

    base_flags = getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0,
    )

    primary_flags = (
        base_flags
        | _CREATE_BREAKAWAY_FROM_JOB
    )

    try:
        return subprocess.Popen(
            cmd,
            creationflags=primary_flags,
            **kwargs,
        )

    except OSError as exc:
        if (
            getattr(
                exc,
                "winerror",
                None,
            )
            != 5
        ):
            raise

        try:
            return subprocess.Popen(
                cmd,
                creationflags=base_flags,
                **kwargs,
            )

        except Exception as fallback_exc:
            raise fallback_exc from exc


def _spawn_identity_record(
    process: subprocess.Popen,
) -> dict[str, Any] | None:
    (
        image,
        creation_time,
        alive,
    ) = process_identity(
        process.pid
    )

    if not alive:
        return None

    return {
        "pid": process.pid,
        "executable": (
            image
            or str(
                _backend_python()
            )
        ),
        "creation_time": creation_time,
    }


def _cleanup_spawned_process(
    identity_record: dict[str, Any] | None,
) -> None:
    if identity_record is None:
        return

    terminate_registered_process(
        identity_record
    )


def _cleanup_stale_backend_record(
    status: BackendStatus,
) -> None:
    if (
        status.state == "stale"
        and status.record is not None
    ):
        remove_backend_record_if_exact(
            status.record
        )


def _wait_for_ready_backend(
    process: subprocess.Popen,
    *,
    timeout: float,
    probe_timeout: float,
) -> BackendStatus:
    deadline = (
        time.monotonic()
        + max(
            0.0,
            float(timeout),
        )
    )

    last_status = BackendStatus(
        state="stopped",
        ready=False,
        detail="backend startup has not published state yet",
        record=None,
    )

    while (
        time.monotonic()
        < deadline
    ):
        last_status = (
            get_backend_status(
                probe_timeout=probe_timeout,
            )
        )

        if last_status.ready:
            return last_status

        if (
            process.poll()
            is not None
        ):
            final_status = (
                get_backend_status(
                    probe_timeout=probe_timeout,
                )
            )

            if final_status.ready:
                return final_status

            raise BackendControlError(
                "persistent backend process exited "
                "before authenticated readiness"
            )

        time.sleep(
            0.05
        )

    raise BackendControlError(
        "persistent backend did not become "
        "authenticated and ready before timeout"
    )


def start_backend(
    *,
    timeout: float = 20.0,
    probe_timeout: float = 2.0,
) -> BackendStatus:
    with _BackendControlLock(
        backend_control_lock_path(),
        timeout=timeout,
    ):
        token = (
            get_or_create_backend_token()
        )

        current = (
            get_backend_status(
                probe_timeout=probe_timeout,
            )
        )

        if current.ready:
            return current

        if (
            current.state == "unready"
            and current.record is not None
        ):
            deadline = (
                time.monotonic()
                + max(
                    0.0,
                    float(timeout),
                )
            )

            while (
                time.monotonic()
                < deadline
            ):
                current = (
                    get_backend_status(
                        probe_timeout=probe_timeout,
                    )
                )

                if current.ready:
                    return current

                if (
                    current.state
                    != "unready"
                ):
                    break

                time.sleep(
                    0.05
                )

            if (
                current.state
                == "unready"
            ):
                raise BackendControlError(
                    "an existing persistent backend owner "
                    "is alive but did not become ready"
                )

        _cleanup_stale_backend_record(
            current
        )

        process = (
            _spawn_backend_process(
                token
            )
        )

        identity_record = (
            _spawn_identity_record(
                process
            )
        )

        try:
            return (
                _wait_for_ready_backend(
                    process,
                    timeout=timeout,
                    probe_timeout=probe_timeout,
                )
            )

        except BaseException:
            _cleanup_spawned_process(
                identity_record
            )
            raise


def _backend_owner_identity_matches(
    record: PersistentBackendRecord,
) -> bool:
    (
        image,
        creation_time,
        alive,
    ) = process_identity(
        record.pid
    )

    if not alive:
        return False

    if (
        record.creation_time is not None
        and creation_time is not None
        and int(
            record.creation_time
        )
        != int(
            creation_time
        )
    ):
        return False

    if (
        image
        and record.executable
        and Path(image).name.casefold()
        != Path(
            record.executable
        ).name.casefold()
    ):
        return False

    return True


def _cleanup_owned_registry_children(
    record: PersistentBackendRecord,
) -> None:
    directory = Path(
        record.process_registry
    )

    for (
        record_path,
        child,
    ) in read_records(
        directory
    ):
        try:
            parent_pid = int(
                child.get(
                    "parent_pid"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if parent_pid != record.pid:
            continue

        if (
            record.creation_time
            is not None
        ):
            expected_parent_creation = (
                child.get(
                    "parent_creation_time"
                )
            )

            if (
                expected_parent_creation
                is None
            ):
                continue

            try:
                if int(
                    expected_parent_creation
                ) != int(
                    record.creation_time
                ):
                    continue

            except (
                TypeError,
                ValueError,
            ):
                continue

        terminate_registered_process(
            child
        )

        remove_record(
            record_path
        )


def _wait_for_owner_exit(
    record: PersistentBackendRecord,
    *,
    timeout: float,
) -> bool:
    deadline = (
        time.monotonic()
        + max(
            0.0,
            float(timeout),
        )
    )

    while (
        time.monotonic()
        < deadline
    ):
        if not (
            _backend_owner_identity_matches(
                record
            )
        ):
            return True

        time.sleep(
            0.05
        )

    return not (
        _backend_owner_identity_matches(
            record
        )
    )


def stop_backend(
    *,
    timeout: float = 5.0,
) -> BackendStatus:
    with _BackendControlLock(
        backend_control_lock_path(),
        timeout=timeout,
    ):
        record = (
            read_backend_record()
        )

        if record is None:
            return BackendStatus(
                state="stopped",
                ready=False,
                detail="no persistent backend record",
                record=None,
            )

        if not (
            _backend_owner_identity_matches(
                record
            )
        ):
            remove_backend_record_if_exact(
                record
            )

            return BackendStatus(
                state="stopped",
                ready=False,
                detail=(
                    "stale persistent backend record "
                    "was removed without terminating "
                    "any process"
                ),
                record=None,
            )

        if (
            sys.platform == "win32"
            and record.creation_time is None
        ):
            raise BackendControlError(
                "refusing to terminate backend without "
                "Windows process creation identity"
            )

        terminated = (
            terminate_registered_process(
                record.to_dict()
            )
        )

        if not terminated:
            raise BackendControlError(
                "identity-checked backend termination "
                "was not accepted"
            )

        if not _wait_for_owner_exit(
            record,
            timeout=timeout,
        ):
            raise BackendControlError(
                "persistent backend process remained "
                "alive after identity-checked termination"
            )

        _cleanup_owned_registry_children(
            record
        )

        remove_backend_record_if_exact(
            record
        )

        return BackendStatus(
            state="stopped",
            ready=False,
            detail="persistent backend stopped",
            record=None,
        )


__all__ = [
    "BACKEND_HOST",
    "BACKEND_MCP_PATH",
    "BACKEND_PORT",
    "BACKEND_SERVER_NAME",
    "BackendControlError",
    "BackendStatus",
    "backend_control_lock_path",
    "backend_process_registry_dir",
    "get_backend_status",
    "start_backend",
    "stop_backend",
]
