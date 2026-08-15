"""Process-wide logging for desktop Contextor sessions.

The GUI may be launched without a Windows console.  This module preserves a
single durable stdout/stderr stream and can expose it deliberately in a CMD
window without letting helper processes flash their own consoles.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import TextIO

from contextor.core.paths import state_dir


_LOCK = threading.RLock()
_HANDLE: TextIO | None = None
_PATH: Path | None = None
_CMD_PROCESS: subprocess.Popen | None = None


class _TeeStream:
    """Write to the original stream and the program log without breaking I/O."""

    def __init__(self, original, log_handle: TextIO):
        self._original = original
        self._log_handle = log_handle

    def write(self, text):
        if not isinstance(text, str):
            text = str(text)
        with _LOCK:
            if self._original is not None:
                self._original.write(text)
            self._log_handle.write(text)
            self._log_handle.flush()
        return len(text)

    def flush(self):
        with _LOCK:
            if self._original is not None:
                self._original.flush()
            self._log_handle.flush()

    def isatty(self):
        return bool(self._original and self._original.isatty())

    def __getattr__(self, name):
        if self._original is None:
            raise AttributeError(name)
        return getattr(self._original, name)


def program_log_path() -> Path:
    """Return the per-user desktop program log path."""

    return state_dir() / "logs" / "contextor-program.log"


def configure_program_log() -> Path:
    """Start process-wide stdout/stderr mirroring once and return its file."""

    global _HANDLE, _PATH
    with _LOCK:
        if _PATH is not None:
            return _PATH
        path = program_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _HANDLE = path.open("a", encoding="utf-8", buffering=1)
        _PATH = path
        sys.stdout = _TeeStream(sys.stdout, _HANDLE)
        sys.stderr = _TeeStream(sys.stderr, _HANDLE)
        emit_program_log("[START] Contextor desktop log initialized.")
        return path


def emit_program_log(message: str) -> None:
    """Append an explicit application event even when stdout is unavailable."""

    with _LOCK:
        if _HANDLE is None:
            return
        _HANDLE.write(f"{message}\n")
        _HANDLE.flush()


def log_program_event(component: str, event: str, **details) -> None:
    """Write one low-volume technical event to the process-wide log."""

    rendered = " ".join(
        f"{key}={value!r}" for key, value in details.items() if value is not None
    )
    suffix = f" {rendered}" if rendered else ""
    timestamp = datetime.now().strftime("%H:%M:%S")
    emit_program_log(f"[{timestamp}] [{component}] {event}{suffix}")


def open_cmd_log() -> bool:
    """Open one visible CMD window tailing the complete program log."""

    global _CMD_PROCESS
    path = configure_program_log()
    if sys.platform != "win32":
        return False
    with _LOCK:
        if _CMD_PROCESS is not None and _CMD_PROCESS.poll() is None:
            return True
        executable = str(Path(sys.executable).resolve())
        command = (
            "title Contextor program log && "
            f'"{executable}" -u -m contextor.core.program_log_tail '
            f'"{path}"'
        )
        _CMD_PROCESS = subprocess.Popen(
            ["cmd.exe", "/d", "/k", command],
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        log_program_event("GUI", "CMD program log opened")
        return True


def close_cmd_log() -> None:
    """Close only the CMD log window spawned by this Contextor process."""

    global _CMD_PROCESS
    with _LOCK:
        process = _CMD_PROCESS
        _CMD_PROCESS = None
    if process is not None and process.poll() is None:
        process.terminate()


__all__ = [
    "close_cmd_log",
    "configure_program_log",
    "emit_program_log",
    "log_program_event",
    "open_cmd_log",
    "program_log_path",
]
