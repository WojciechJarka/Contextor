"""Windows-user-session Desktop admission and activation signalling."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Callable

MUTEX_NAME = "Local\\Contextor.Desktop.Singleton.v1"
ACTIVATE_EVENT_NAME = "Local\\Contextor.Desktop.Activate.v1"
ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
_ACTIVATION_POLL_MS = 100

def _kernel32():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateEventW.restype = wintypes.HANDLE
    kernel.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.SetEvent.argtypes = [wintypes.HANDLE]
    kernel.SetEvent.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel

class DesktopSingleInstance:
    def __init__(self, mutex=None, event=None, *, primary: bool = True, kernel=None) -> None:
        self._mutex, self._event, self._kernel = mutex, event, kernel
        self._closed = False
        self.is_primary = primary

    @classmethod
    def acquire(cls) -> "DesktopSingleInstance":
        if os.name != "nt":
            return cls()
        kernel = _kernel32()
        event = kernel.CreateEventW(None, False, False, ACTIVATE_EVENT_NAME)
        if not event:
            return cls(kernel=kernel)
        ctypes.set_last_error(0)
        mutex = kernel.CreateMutexW(None, False, MUTEX_NAME)
        mutex_error = ctypes.get_last_error()
        if not mutex:
            kernel.CloseHandle(event)
            return cls(kernel=kernel)
        return cls(mutex, event, primary=mutex_error != ERROR_ALREADY_EXISTS, kernel=kernel)

    def signal_existing(self) -> None:
        if os.name == "nt" and not self._closed and self._kernel is not None and self._event:
            self._kernel.SetEvent(self._event)

    def register_activation(self, root, callback: Callable[[], None]) -> None:
        if not self.is_primary or os.name != "nt" or self._closed or self._kernel is None or not self._event:
            return
        def poll_activation() -> None:
            if self._closed or not self._event:
                return
            result = self._kernel.WaitForSingleObject(self._event, 0)
            if result == WAIT_OBJECT_0:
                callback()
            elif result != WAIT_TIMEOUT:
                return
            if not self._closed:
                try:
                    root.after(_ACTIVATION_POLL_MS, poll_activation)
                except Exception:
                    pass
        root.after(0, poll_activation)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if os.name == "nt" and self._kernel is not None:
            for handle in (self._event, self._mutex):
                if handle:
                    self._kernel.CloseHandle(handle)
        self._event = self._mutex = None

