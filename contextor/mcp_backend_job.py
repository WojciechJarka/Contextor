"""Windows process-tree ownership for the persistent MCP backend."""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from typing import Any


class BackendJobError(RuntimeError):
    """The backend process tree cannot be safely owned or verified."""


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _BASIC_LIMITS(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _EXTENDED_LIMITS(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BASIC_LIMITS),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryLimit", ctypes.c_size_t),
        ("PeakJobMemoryLimit", ctypes.c_size_t),
    ]


_KILL_ON_JOB_CLOSE = 0x00002000
_BREAKAWAY_OK = 0x00000800
_EXTENDED_LIMIT_INFORMATION = 9

_active_handle: Any = None
_active_pid: int | None = None


def _kernel32() -> Any:
    kernel = ctypes.WinDLL(
        "kernel32",
        use_last_error=True,
    )

    kernel.CreateJobObjectW.argtypes = [
        ctypes.c_void_p,
        wintypes.LPCWSTR,
    ]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE

    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL

    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE

    kernel.AssignProcessToJobObject.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
    ]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL

    kernel.IsProcessInJob.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.BOOL),
    ]
    kernel.IsProcessInJob.restype = wintypes.BOOL

    kernel.CloseHandle.argtypes = [
        wintypes.HANDLE,
    ]
    kernel.CloseHandle.restype = wintypes.BOOL

    return kernel


def protect_persistent_backend() -> None:
    """Own backend descendants until the backend process exits."""
    global _active_handle
    global _active_pid

    if sys.platform != "win32":
        return

    current_pid = os.getpid()

    if _active_handle is not None:
        if _active_pid != current_pid:
            raise BackendJobError(
                "backend Job Object belongs to a different process"
            )
        return

    kernel = _kernel32()

    handle = kernel.CreateJobObjectW(None, None)

    if not handle:
        raise BackendJobError(
            "CreateJobObjectW failed; "
            f"winerror={ctypes.get_last_error()}"
        )

    try:
        limits = _EXTENDED_LIMITS()

        limits.BasicLimitInformation.LimitFlags = (
            _KILL_ON_JOB_CLOSE | _BREAKAWAY_OK
        )

        if not kernel.SetInformationJobObject(
            handle,
            _EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            raise BackendJobError(
                "SetInformationJobObject failed; "
                f"winerror={ctypes.get_last_error()}"
            )

        if not kernel.AssignProcessToJobObject(
            handle,
            kernel.GetCurrentProcess(),
        ):
            raise BackendJobError(
                "AssignProcessToJobObject failed; "
                f"winerror={ctypes.get_last_error()}"
            )

    except BaseException:
        kernel.CloseHandle(handle)
        raise

    # Retain this non-inheritable Job Object handle for the
    # entire backend lifetime. Do not close it while running.
    #
    # The final OS handle close terminates processes that
    # remain assigned to this Job Object.
    _active_handle = handle
    _active_pid = current_pid

    # Environment variables can be inherited by unrelated children.
    # Ownership authority remains exclusively in this process.


def backend_job_active_for_current_process() -> bool:
    """Return true only for the process holding the backend Job."""
    if sys.platform != "win32":
        return False

    if _active_handle is None:
        if _active_pid is not None:
            raise BackendJobError(
                "backend Job Object ownership state is inconsistent"
            )
        return False

    if _active_pid != os.getpid():
        raise BackendJobError(
            "backend Job Object belongs to a different process"
        )

    return True


def require_live_outside_backend_job(
    process: Any,
) -> None:
    """Verify that an explicitly breaking-away LIVE process escaped."""
    if sys.platform != "win32":
        return

    if (
        _active_handle is None
        or _active_pid != os.getpid()
    ):
        raise BackendJobError(
            "backend Job Object is not installed"
        )

    process_handle = getattr(process, "_handle", None)

    try:
        child_handle = int(process_handle)
    except (TypeError, ValueError):
        raise BackendJobError(
            "LIVE process handle is unavailable"
        ) from None

    if child_handle <= 0:
        raise BackendJobError(
            "LIVE process handle is invalid"
        )

    kernel = _kernel32()
    belongs = wintypes.BOOL(0)

    if not kernel.IsProcessInJob(
        child_handle,
        _active_handle,
        ctypes.byref(belongs),
    ):
        raise BackendJobError(
            "LIVE Job Object membership could not be verified; "
            f"winerror={ctypes.get_last_error()}"
        )

    if belongs.value:
        raise BackendJobError(
            "LIVE did not break away from the backend Job Object"
        )


__all__ = [
    "BackendJobError",
    "backend_job_active_for_current_process",
    "protect_persistent_backend",
    "require_live_outside_backend_job",
]
