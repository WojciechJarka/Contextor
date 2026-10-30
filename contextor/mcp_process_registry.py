"""Small on-disk registry for processes owned by the Contextor MCP server."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import errno
import json
import ntpath
import os
import signal
import time
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class ProcessIdentityProbe:
    state: Literal["alive", "dead", "unknown"]
    image: str | None
    creation_time: int | None


def registry_dir(root: Path) -> Path:
    return root / ".contextor" / "mcp_processes"


def _windows_process_identity(pid: int) -> tuple[str | None, int | None, bool]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, wintypes.LPDWORD]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        wintypes.PDWORD,
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    query_access = 0x1000
    handle = kernel32.OpenProcess(query_access, False, pid)
    if not handle:
        return None, None, False
    try:
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return None, None, False
        alive = exit_code.value == 259

        size = ctypes.c_ulong(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        image = None
        if kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            image = buffer.value

        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        created = None
        if kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            created = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        return image, created, alive
    finally:
        kernel32.CloseHandle(handle)


def _windows_process_identity_probe(pid: int) -> ProcessIdentityProbe:
    unknown = ProcessIdentityProbe("unknown", None, None)
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            wintypes.PDWORD,
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.GetProcessTimes.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        ]
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
    except (OSError, AttributeError, TypeError, ValueError):
        return unknown

    process_query_limited_information = 0x1000
    synchronize = 0x00100000
    try:
        handle = kernel32.OpenProcess(
            process_query_limited_information | synchronize,
            False,
            pid,
        )
    except OSError:
        return unknown

    if not handle:
        if ctypes.get_last_error() == 87:  # ERROR_INVALID_PARAMETER
            return ProcessIdentityProbe("dead", None, None)
        return unknown

    try:
        try:
            wait_result = kernel32.WaitForSingleObject(handle, 0)
        except OSError:
            return unknown

        if wait_result == 0:  # WAIT_OBJECT_0
            return ProcessIdentityProbe("dead", None, None)
        if wait_result != 258:  # WAIT_TIMEOUT
            return unknown

        image = None
        try:
            size = ctypes.c_ulong(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(
                handle,
                0,
                buffer,
                ctypes.byref(size),
            ):
                image = buffer.value
        except (OSError, TypeError, ValueError):
            pass

        created = None
        try:
            creation = wintypes.FILETIME()
            exit_time = wintypes.FILETIME()
            kernel = wintypes.FILETIME()
            user = wintypes.FILETIME()
            if kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel),
                ctypes.byref(user),
            ):
                created = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        except (OSError, TypeError, ValueError):
            pass

        return ProcessIdentityProbe("alive", image, created)
    finally:
        try:
            kernel32.CloseHandle(handle)
        except OSError:
            pass


def process_identity(pid: int) -> tuple[str | None, int | None, bool]:
    if sys_platform_is_windows():
        return _windows_process_identity(pid)
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return None, None, False
    image = None
    try:
        image = str(Path(f"/proc/{pid}/exe").resolve(strict=True))
    except OSError:
        pass
    return image, None, True


def probe_process_identity(pid: int) -> ProcessIdentityProbe:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return ProcessIdentityProbe("unknown", None, None)

    if sys_platform_is_windows():
        return _windows_process_identity_probe(pid)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return ProcessIdentityProbe("dead", None, None)
    except PermissionError:
        return ProcessIdentityProbe("alive", None, None)
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return ProcessIdentityProbe("dead", None, None)
        if exc.errno == errno.EPERM:
            return ProcessIdentityProbe("alive", None, None)
        return ProcessIdentityProbe("unknown", None, None)

    image = None
    try:
        image = str(Path(f"/proc/{pid}/exe").resolve(strict=True))
    except (OSError, RuntimeError):
        pass
    return ProcessIdentityProbe("alive", image, None)


def sys_platform_is_windows() -> bool:
    return os.name == "nt"


def register_process(
    directory: Path,
    *,
    pid: int,
    parent_pid: int,
    kind: str,
    executable: str,
) -> Path:
    image, creation_time, _ = process_identity(pid)
    _, parent_creation_time, _ = process_identity(parent_pid)
    record = {
        "pid": pid,
        "parent_pid": parent_pid,
        "kind": kind,
        "executable": image or executable,
        "creation_time": creation_time,
        "parent_creation_time": parent_creation_time,
        "registered_at": time.time(),
    }
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{kind}-{pid}.json"
    temporary = directory / f".{kind}-{pid}-{os.getpid()}.tmp"
    temporary.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    temporary.replace(target)
    return target


def remove_record(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def read_records(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    if not directory.is_dir():
        return records
    for path in directory.glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                records.append((path, value))
            else:
                remove_record(path)
        except (OSError, ValueError):
            remove_record(path)
    return records


def record_matches_process(record: dict[str, Any]) -> bool:
    try:
        pid = int(record["pid"])
    except (KeyError, TypeError, ValueError):
        return False
    image, creation_time, alive = process_identity(pid)
    if not alive:
        return False
    expected_image = str(record.get("executable") or "")
    if image and expected_image:
        if Path(image).name.casefold() != Path(expected_image).name.casefold():
            return False
    expected_creation = record.get("creation_time")
    if expected_creation is not None and creation_time is not None:
        if int(expected_creation) != creation_time:
            return False
    return True


def _terminate_windows_record_identity_bound(
    record: dict[str, Any],
) -> bool:
    """Terminate only the process identified by one verified Windows handle."""
    if not isinstance(record, dict):
        return False

    pid = record.get("pid")
    creation_time = record.get("creation_time")
    executable = record.get("executable")

    if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
        return False

    if (
        type(creation_time) is not int
        or not 0 < creation_time <= 0xFFFFFFFFFFFFFFFF
    ):
        return False

    if (
        not isinstance(executable, str)
        or not executable
        or not ntpath.isabs(executable)
        or not ntpath.splitdrive(executable)[0]
    ):
        return False

    expected_image = ntpath.normcase(
        ntpath.normpath(executable)
    )

    try:
        kernel32 = ctypes.WinDLL(
            "kernel32",
            use_last_error=True,
        )

        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE

        kernel32.WaitForSingleObject.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
        ]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD

        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

        kernel32.GetProcessTimes.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        ]
        kernel32.GetProcessTimes.restype = wintypes.BOOL

        kernel32.TerminateProcess.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
        ]
        kernel32.TerminateProcess.restype = wintypes.BOOL

        kernel32.CloseHandle.argtypes = [
            wintypes.HANDLE,
        ]
        kernel32.CloseHandle.restype = wintypes.BOOL

        # PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION
        # | SYNCHRONIZE
        handle = kernel32.OpenProcess(
            0x00101001,
            False,
            pid,
        )

        if not handle:
            return False

        try:
            # WAIT_TIMEOUT means the handle identifies a live process.
            if kernel32.WaitForSingleObject(handle, 0) != 258:
                return False

            length = wintypes.DWORD(32768)
            image_buffer = ctypes.create_unicode_buffer(
                length.value
            )

            if not kernel32.QueryFullProcessImageNameW(
                handle,
                0,
                image_buffer,
                ctypes.byref(length),
            ):
                return False

            actual_image = image_buffer.value

            if (
                not actual_image
                or not ntpath.isabs(actual_image)
                or not ntpath.splitdrive(actual_image)[0]
            ):
                return False

            if (
                ntpath.normcase(ntpath.normpath(actual_image))
                != expected_image
            ):
                return False

            creation = wintypes.FILETIME()
            exit_time = wintypes.FILETIME()
            kernel_time = wintypes.FILETIME()
            user_time = wintypes.FILETIME()

            if not kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel_time),
                ctypes.byref(user_time),
            ):
                return False

            actual_creation = (
                (creation.dwHighDateTime << 32)
                | creation.dwLowDateTime
            )

            if actual_creation != creation_time:
                return False

            # Verification and termination use the SAME handle.
            # No second PID lookup and no taskkill.
            if not kernel32.TerminateProcess(handle, 1):
                return False

            # TerminateProcess is asynchronous.
            # WAIT_OBJECT_0 confirms that this process exited.
            return kernel32.WaitForSingleObject(
                handle,
                2000,
            ) == 0

        finally:
            kernel32.CloseHandle(handle)

    except (OSError, AttributeError, TypeError, ValueError):
        return False


def terminate_registered_process(
    record: dict[str, Any],
) -> bool:
    if sys_platform_is_windows():
        return _terminate_windows_record_identity_bound(
            record
        )

    # Preserve the existing POSIX contract.
    if not record_matches_process(record):
        return False

    pid = int(record["pid"])

    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError:
        return False


def terminate_registered_record(
    path: Path | None,
) -> bool:
    if path is None:
        return False
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, TypeError):
        remove_record(path)
        return False
    if not isinstance(value, dict):
        remove_record(path)
        return False
    terminated = terminate_registered_process(value)

    if terminated:
        remove_record(path)

    return terminated
