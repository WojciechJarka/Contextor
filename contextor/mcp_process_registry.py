"""Small on-disk registry for processes owned by the Contextor MCP server."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
import signal
import time
from pathlib import Path
from typing import Any


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


def terminate_registered_process(record: dict[str, Any]) -> bool:
    if not record_matches_process(record):
        return False
    pid = int(record["pid"])
    if sys_platform_is_windows():
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x0001, False, pid)
        if not handle:
            return False
        try:
            terminated = bool(kernel32.TerminateProcess(handle, 1))
            if terminated:
                kernel32.WaitForSingleObject(handle, 2000)
            return terminated
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError:
        return False
