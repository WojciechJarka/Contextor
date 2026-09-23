"""Secure persistent bearer-token storage for the shared Contextor MCP backend."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
import math
import os
import secrets
import stat
import threading
import time
import uuid
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from contextor.mcp_backend_state import backend_state_dir


TOKEN_RECORD_SCHEMA_VERSION = 1
MIN_BACKEND_TOKEN_LENGTH = 32
BACKEND_TOKEN_RANDOM_BYTES = 48

_WINDOWS_PROTECTION = "windows-dpapi-current-user"
_POSIX_PROTECTION = "posix-user-file-0600"

_TOKEN_FIELDS = {
    "schema_version",
    "protection",
    "protected_data",
    "created_at",
}


class BackendSecretError(RuntimeError):
    """Base error for persistent backend bearer-token storage."""


class BackendSecretRecordError(BackendSecretError):
    """The durable secret record is malformed or violates its contract."""


@dataclass(
    frozen=True,
    slots=True,
)
class BackendSecretRecord:
    schema_version: int
    protection: str
    protected_data: str
    created_at: float

    def __post_init__(self) -> None:
        if self.schema_version != TOKEN_RECORD_SCHEMA_VERSION:
            raise BackendSecretRecordError(
                "unsupported backend token schema_version"
            )

        if self.protection not in {
            _WINDOWS_PROTECTION,
            _POSIX_PROTECTION,
        }:
            raise BackendSecretRecordError(
                "unsupported backend token protection"
            )

        if (
            not isinstance(self.protected_data, str)
            or not self.protected_data
            or self.protected_data != self.protected_data.strip()
        ):
            raise BackendSecretRecordError(
                "protected_data must be non-empty base64 text"
            )

        try:
            base64.b64decode(
                self.protected_data.encode("ascii"),
                validate=True,
            )
        except (
            UnicodeEncodeError,
            ValueError,
        ) as exc:
            raise BackendSecretRecordError(
                "protected_data is not valid base64"
            ) from exc

        if (
            isinstance(self.created_at, bool)
            or not isinstance(
                self.created_at,
                (int, float),
            )
        ):
            raise BackendSecretRecordError(
                "created_at must be a timestamp"
            )

        created_at = float(self.created_at)

        if (
            not math.isfinite(created_at)
            or created_at < 0
        ):
            raise BackendSecretRecordError(
                "created_at must be a finite non-negative timestamp"
            )

        object.__setattr__(
            self,
            "created_at",
            created_at,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "protection": self.protection,
            "protected_data": self.protected_data,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "BackendSecretRecord":
        if (
            not isinstance(payload, Mapping)
            or set(payload) != _TOKEN_FIELDS
        ):
            raise BackendSecretRecordError(
                "backend token fields do not match schema"
            )

        return cls(
            **dict(payload)
        )


def backend_token_path() -> Path:
    return (
        backend_state_dir()
        / "token.json"
    )


def backend_token_lock_path() -> Path:
    return (
        backend_state_dir()
        / "token.lock"
    )


def _validate_token(
    token: Any,
) -> str:
    if (
        not isinstance(token, str)
        or len(token) < MIN_BACKEND_TOKEN_LENGTH
        or token != token.strip()
    ):
        raise BackendSecretError(
            "backend bearer token does not satisfy the minimum contract"
        )

    return token


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        (
            "cbData",
            wintypes.DWORD,
        ),
        (
            "pbData",
            ctypes.POINTER(
                ctypes.c_ubyte
            ),
        ),
    ]


def _input_blob(
    data: bytes,
) -> tuple[_DATA_BLOB, Any]:
    buffer = (
        ctypes.c_ubyte
        * len(data)
    ).from_buffer_copy(
        data
    )

    blob = _DATA_BLOB(
        len(data),
        ctypes.cast(
            buffer,
            ctypes.POINTER(
                ctypes.c_ubyte
            ),
        ),
    )

    return blob, buffer


def _windows_crypto_libraries():
    crypt32 = ctypes.WinDLL(
        "crypt32",
        use_last_error=True,
    )
    kernel32 = ctypes.WinDLL(
        "kernel32",
        use_last_error=True,
    )

    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DATA_BLOB),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DATA_BLOB),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL

    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DATA_BLOB),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DATA_BLOB),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL

    kernel32.LocalFree.argtypes = [
        ctypes.c_void_p,
    ]
    kernel32.LocalFree.restype = ctypes.c_void_p

    return crypt32, kernel32


def _protect_windows(
    payload: bytes,
) -> bytes:
    if os.name != "nt":
        raise BackendSecretError(
            "Windows DPAPI is unavailable on this platform"
        )

    crypt32, kernel32 = (
        _windows_crypto_libraries()
    )

    input_blob, input_buffer = (
        _input_blob(
            payload
        )
    )

    output_blob = _DATA_BLOB()

    CRYPTPROTECT_UI_FORBIDDEN = 0x1

    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "Contextor MCP backend bearer token",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        error = ctypes.get_last_error()
        raise BackendSecretError(
            f"CryptProtectData failed with WinError {error}"
        )

    try:
        return ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(
                ctypes.cast(
                    output_blob.pbData,
                    ctypes.c_void_p,
                )
            )


def _unprotect_windows(
    payload: bytes,
) -> bytes:
    if os.name != "nt":
        raise BackendSecretError(
            "Windows DPAPI is unavailable on this platform"
        )

    crypt32, kernel32 = (
        _windows_crypto_libraries()
    )

    input_blob, input_buffer = (
        _input_blob(
            payload
        )
    )

    output_blob = _DATA_BLOB()
    description = wintypes.LPWSTR()

    CRYPTPROTECT_UI_FORBIDDEN = 0x1

    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        ctypes.byref(description),
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        error = ctypes.get_last_error()
        raise BackendSecretError(
            f"CryptUnprotectData failed with WinError {error}"
        )

    try:
        return ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )
    finally:
        if description:
            kernel32.LocalFree(
                ctypes.cast(
                    description,
                    ctypes.c_void_p,
                )
            )

        if output_blob.pbData:
            kernel32.LocalFree(
                ctypes.cast(
                    output_blob.pbData,
                    ctypes.c_void_p,
                )
            )


def _ensure_secret_directory() -> Path:
    directory = backend_state_dir()

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    if os.name != "nt":
        os.chmod(
            directory,
            0o700,
        )

    return directory


def _assert_posix_secret_permissions(
    path: Path,
) -> None:
    if os.name == "nt":
        return

    mode = stat.S_IMODE(
        path.stat().st_mode
    )

    if mode & 0o077:
        raise BackendSecretError(
            "backend token file permissions are broader than 0600"
        )


def _encode_secret_record(
    token: str,
) -> BackendSecretRecord:
    token = _validate_token(
        token
    )

    raw = token.encode(
        "utf-8"
    )

    if os.name == "nt":
        protection = (
            _WINDOWS_PROTECTION
        )
        protected = (
            _protect_windows(
                raw
            )
        )
    else:
        protection = (
            _POSIX_PROTECTION
        )
        protected = raw

    return BackendSecretRecord(
        schema_version=(
            TOKEN_RECORD_SCHEMA_VERSION
        ),
        protection=protection,
        protected_data=base64.b64encode(
            protected
        ).decode("ascii"),
        created_at=time.time(),
    )


def _decode_secret_record(
    record: BackendSecretRecord,
) -> str:
    protected = base64.b64decode(
        record.protected_data.encode(
            "ascii"
        ),
        validate=True,
    )

    if os.name == "nt":
        if (
            record.protection
            != _WINDOWS_PROTECTION
        ):
            raise BackendSecretError(
                "backend token protection does not match Windows"
            )

        raw = _unprotect_windows(
            protected
        )

    else:
        if (
            record.protection
            != _POSIX_PROTECTION
        ):
            raise BackendSecretError(
                "backend token protection does not match POSIX"
            )

        raw = protected

    try:
        token = raw.decode(
            "utf-8"
        )
    except UnicodeDecodeError as exc:
        raise BackendSecretError(
            "backend token payload is not UTF-8"
        ) from exc

    return _validate_token(
        token
    )


def _write_secret_record(
    record: BackendSecretRecord,
) -> None:
    directory = (
        _ensure_secret_directory()
    )

    target = backend_token_path()
    temporary = target.with_name(
        f".{target.name}.{uuid.uuid4().hex}.tmp"
    )

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
    )

    fd = None

    try:
        fd = os.open(
            temporary,
            flags,
            0o600,
        )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            fd = None

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

        if os.name != "nt":
            os.chmod(
                target,
                0o600,
            )

            directory_fd = None

            try:
                directory_fd = os.open(
                    directory,
                    os.O_RDONLY,
                )

                os.fsync(
                    directory_fd
                )

            except OSError:
                pass

            finally:
                if (
                    directory_fd
                    is not None
                ):
                    os.close(
                        directory_fd
                    )

    finally:
        if fd is not None:
            os.close(
                fd
            )

        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_secret_record(
) -> BackendSecretRecord | None:
    path = backend_token_path()

    try:
        _assert_posix_secret_permissions(
            path
        )

        payload = json.loads(
            path.read_text(
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
        raise BackendSecretRecordError(
            "persistent backend token record is malformed"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise BackendSecretRecordError(
            "persistent backend token record must be an object"
        )

    return (
        BackendSecretRecord
        .from_dict(
            payload
        )
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


class _BackendSecretLock(
    AbstractContextManager[
        "_BackendSecretLock"
    ]
):
    def __init__(
        self,
        path: Path,
        *,
        timeout: float = 10.0,
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
    ) -> "_BackendSecretLock":
        if not self._thread_lock.acquire(
            timeout=self.timeout
        ):
            raise BackendSecretError(
                "timed out waiting for backend token lock"
            )

        try:
            _ensure_secret_directory()

            deadline = (
                time.monotonic()
                + self.timeout
            )

            while True:
                try:
                    self._file = (
                        self.path.open(
                            "a+b"
                        )
                    )
                    break

                except PermissionError as exc:
                    if (
                        time.monotonic()
                        >= deadline
                    ):
                        raise BackendSecretError(
                            "timed out opening backend token lock"
                        ) from exc

                    time.sleep(
                        0.01
                    )

            if (
                self.path.stat().st_size
                == 0
            ):
                self._file.write(
                    b"0"
                )
                self._file.flush()

            self._file.seek(0)

            while True:
                try:
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
                        raise BackendSecretError(
                            "timed out waiting for backend token lock"
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


def _new_backend_token() -> str:
    token = secrets.token_urlsafe(
        BACKEND_TOKEN_RANDOM_BYTES
    )

    return _validate_token(
        token
    )


def read_backend_token(
) -> str | None:
    record = (
        _read_secret_record()
    )

    if record is None:
        return None

    return _decode_secret_record(
        record
    )


def get_or_create_backend_token(
) -> str:
    with _BackendSecretLock(
        backend_token_lock_path()
    ):
        existing = (
            read_backend_token()
        )

        if existing is not None:
            return existing

        token = (
            _new_backend_token()
        )

        _write_secret_record(
            _encode_secret_record(
                token
            )
        )

        return token


def rotate_backend_token(
) -> str:
    with _BackendSecretLock(
        backend_token_lock_path()
    ):
        token = (
            _new_backend_token()
        )

        _write_secret_record(
            _encode_secret_record(
                token
            )
        )

        return token


def delete_backend_token() -> bool:
    with _BackendSecretLock(
        backend_token_lock_path()
    ):
        try:
            backend_token_path().unlink()
        except FileNotFoundError:
            return False

        return True


__all__ = [
    "BACKEND_TOKEN_RANDOM_BYTES",
    "MIN_BACKEND_TOKEN_LENGTH",
    "TOKEN_RECORD_SCHEMA_VERSION",
    "BackendSecretError",
    "BackendSecretRecord",
    "BackendSecretRecordError",
    "backend_token_lock_path",
    "backend_token_path",
    "delete_backend_token",
    "get_or_create_backend_token",
    "read_backend_token",
    "rotate_backend_token",
]
