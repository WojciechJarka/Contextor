"""Durable ownership state for one shared persistent Contextor MCP backend."""

from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
import uuid
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from contextor.core.paths import state_dir
from contextor.mcp_process_registry import process_identity


BACKEND_RECORD_SCHEMA_VERSION = 1
BACKEND_SERVER_ROLE = "persistent-backend"
BACKEND_TRANSPORT = "streamable-http"

_RECORD_FIELDS = {
    "schema_version",
    "instance_id",
    "server_role",
    "transport",
    "host",
    "port",
    "pid",
    "executable",
    "creation_time",
    "process_registry",
    "started_at",
}


class BackendStateError(RuntimeError):
    """Base error for persistent MCP backend ownership state."""


class BackendAlreadyRunning(BackendStateError):
    """Another process owns the persistent backend lifetime lock."""


class BackendRecordError(BackendStateError):
    """The durable backend record is malformed or violates its schema."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise BackendRecordError(
            f"{field} must be non-empty without surrounding whitespace"
        )
    return value


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BackendRecordError(
            f"{field} must be a positive integer"
        )
    return value


def _canonical_path(value: Any, field: str) -> str:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise BackendRecordError(
            f"{field} must be a non-empty path"
        )

    try:
        resolved = Path(value).expanduser().resolve(
            strict=False
        )
    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        raise BackendRecordError(
            f"{field} cannot be canonicalized"
        ) from exc

    if not resolved.is_absolute():
        raise BackendRecordError(
            f"{field} must be absolute"
        )

    return os.path.normcase(
        str(resolved)
    )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistentBackendRecord:
    schema_version: int
    instance_id: str
    server_role: str
    transport: str
    host: str
    port: int
    pid: int
    executable: str
    creation_time: int | None
    process_registry: str
    started_at: float

    def __post_init__(self) -> None:
        if (
            self.schema_version
            != BACKEND_RECORD_SCHEMA_VERSION
        ):
            raise BackendRecordError(
                "unsupported backend record schema_version"
            )

        object.__setattr__(
            self,
            "instance_id",
            _text(
                self.instance_id,
                "instance_id",
            ),
        )

        if self.server_role != BACKEND_SERVER_ROLE:
            raise BackendRecordError(
                "backend record server_role is invalid"
            )

        if self.transport != BACKEND_TRANSPORT:
            raise BackendRecordError(
                "backend record transport is invalid"
            )

        object.__setattr__(
            self,
            "host",
            _text(
                self.host,
                "host",
            ),
        )

        port = _positive_int(
            self.port,
            "port",
        )

        if port > 65535:
            raise BackendRecordError(
                "port must be at most 65535"
            )

        object.__setattr__(
            self,
            "pid",
            _positive_int(
                self.pid,
                "pid",
            ),
        )

        object.__setattr__(
            self,
            "executable",
            _text(
                self.executable,
                "executable",
            ),
        )

        if self.creation_time is not None:
            object.__setattr__(
                self,
                "creation_time",
                _positive_int(
                    self.creation_time,
                    "creation_time",
                ),
            )

        object.__setattr__(
            self,
            "process_registry",
            _canonical_path(
                self.process_registry,
                "process_registry",
            ),
        )

        if (
            isinstance(
                self.started_at,
                bool,
            )
            or not isinstance(
                self.started_at,
                (int, float),
            )
        ):
            raise BackendRecordError(
                "started_at must be a timestamp"
            )

        started_at = float(
            self.started_at
        )

        if (
            not math.isfinite(
                started_at
            )
            or started_at < 0
        ):
            raise BackendRecordError(
                "started_at must be a finite non-negative timestamp"
            )

        object.__setattr__(
            self,
            "started_at",
            started_at,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "instance_id": self.instance_id,
            "server_role": self.server_role,
            "transport": self.transport,
            "host": self.host,
            "port": self.port,
            "pid": self.pid,
            "executable": self.executable,
            "creation_time": self.creation_time,
            "process_registry": self.process_registry,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "PersistentBackendRecord":
        if (
            not isinstance(
                payload,
                Mapping,
            )
            or set(payload)
            != _RECORD_FIELDS
        ):
            raise BackendRecordError(
                "backend record fields do not match schema"
            )

        return cls(
            **dict(payload)
        )


def backend_state_dir() -> Path:
    return (
        state_dir()
        / "mcp_backend"
    )


def backend_record_path() -> Path:
    return (
        backend_state_dir()
        / "backend.json"
    )


def backend_lock_path() -> Path:
    return (
        backend_state_dir()
        / "backend.lock"
    )


def _write_record(
    record: PersistentBackendRecord,
) -> None:
    target = backend_record_path()

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = target.with_name(
        f".{target.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        with temporary.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            json.dump(
                record.to_dict(),
                stream,
                sort_keys=True,
                separators=(",", ":"),
            )

            stream.flush()

            os.fsync(
                stream.fileno()
            )

        os.replace(
            temporary,
            target,
        )

    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def read_backend_record(
) -> PersistentBackendRecord | None:
    try:
        payload = json.loads(
            backend_record_path().read_text(
                encoding="utf-8"
            )
        )

    except FileNotFoundError:
        return None

    except (
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise BackendRecordError(
            "persistent backend record is malformed"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise BackendRecordError(
            "persistent backend record must be an object"
        )

    return (
        PersistentBackendRecord
        .from_dict(
            payload
        )
    )


def remove_backend_record_if_exact(
    expected: PersistentBackendRecord,
) -> bool:
    try:
        current = (
            read_backend_record()
        )
    except BackendRecordError:
        return False

    if current != expected:
        return False

    try:
        backend_record_path().unlink()
    except FileNotFoundError:
        return False

    return True


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


class _BackendLifetimeLock(
    AbstractContextManager[
        "_BackendLifetimeLock"
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
    ) -> "_BackendLifetimeLock":
        if not self._thread_lock.acquire(
            timeout=self.timeout
        ):
            raise BackendAlreadyRunning(
                "persistent backend lifetime lock is already held"
            )

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._file = (
                self.path.open(
                    "a+b"
                )
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
                        raise BackendAlreadyRunning(
                            "persistent backend lifetime lock is already held"
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


class PersistentBackendLease:
    def __init__(
        self,
        record: PersistentBackendRecord,
        lifetime_lock: _BackendLifetimeLock,
    ) -> None:
        self.record = record
        self._lifetime_lock = (
            lifetime_lock
        )
        self._released = False

    @classmethod
    def acquire(
        cls,
        *,
        host: str,
        port: int,
        transport: str,
        process_registry: str | Path,
        timeout: float = 0.0,
    ) -> "PersistentBackendLease":
        lifetime_lock = (
            _BackendLifetimeLock(
                backend_lock_path(),
                timeout=timeout,
            )
        )

        lifetime_lock.__enter__()

        try:
            (
                image,
                creation_time,
                alive,
            ) = process_identity(
                os.getpid()
            )

            if not alive:
                raise BackendStateError(
                    "current persistent backend process identity is unavailable"
                )

            record = PersistentBackendRecord(
                schema_version=(
                    BACKEND_RECORD_SCHEMA_VERSION
                ),
                instance_id=(
                    uuid.uuid4().hex
                ),
                server_role=(
                    BACKEND_SERVER_ROLE
                ),
                transport=transport,
                host=host,
                port=port,
                pid=os.getpid(),
                executable=(
                    image
                    or sys.executable
                ),
                creation_time=(
                    int(creation_time)
                    if creation_time
                    is not None
                    else None
                ),
                process_registry=str(
                    Path(
                        process_registry
                    )
                    .expanduser()
                    .resolve(
                        strict=False
                    )
                ),
                started_at=time.time(),
            )

            _write_record(
                record
            )

            return cls(
                record,
                lifetime_lock,
            )

        except BaseException:
            lifetime_lock.__exit__(
                None,
                None,
                None,
            )
            raise

    def release(
        self,
    ) -> None:
        if self._released:
            return

        self._released = True

        try:
            remove_backend_record_if_exact(
                self.record
            )
        finally:
            self._lifetime_lock.__exit__(
                None,
                None,
                None,
            )


__all__ = [
    "BACKEND_RECORD_SCHEMA_VERSION",
    "BACKEND_SERVER_ROLE",
    "BACKEND_TRANSPORT",
    "BackendAlreadyRunning",
    "BackendRecordError",
    "BackendStateError",
    "PersistentBackendLease",
    "PersistentBackendRecord",
    "backend_lock_path",
    "backend_record_path",
    "backend_state_dir",
    "read_backend_record",
    "remove_backend_record_if_exact",
]
