"""Current-user Windows autostart for the persistent Contextor MCP backend."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from contextor.core.paths import package_root
from contextor.mcp_backend_control import (
    BackendControlError,
    start_backend,
)


AUTOSTART_VALUE_NAME = "ContextorMcpBackend"
AUTOSTART_RUN_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Run"
)

AUTOSTART_START_TIMEOUT = 120.0
AUTOSTART_PROBE_TIMEOUT = 2.0


class BackendAutostartError(RuntimeError):
    """Persistent backend autostart configuration failed."""


@dataclass(
    frozen=True,
    slots=True,
)
class BackendAutostartStatus:
    installed: bool
    command_matches: bool
    expected_command: str
    configured_command: str | None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "installed": self.installed,
            "command_matches": self.command_matches,
            "expected_command": self.expected_command,
            "configured_command": self.configured_command,
        }


def _require_windows() -> None:
    if sys.platform != "win32":
        raise BackendAutostartError(
            "persistent backend autostart is supported only on Windows"
        )


def _pythonw_path() -> Path:
    _require_windows()

    path = (
        package_root()
        / ".venv"
        / "Scripts"
        / "pythonw.exe"
    ).resolve()

    if not path.is_file():
        raise BackendAutostartError(
            "Contextor autostart interpreter was not found: "
            f"{path}"
        )

    return path


def backend_autostart_command() -> str:
    return subprocess.list2cmdline(
        [
            str(_pythonw_path()),
            "-u",
            "-X",
            "utf8",
            "-m",
            "contextor.mcp_backend_autostart",
            "launch",
        ]
    )


def _read_run_value() -> str | None:
    _require_windows()

    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_RUN_KEY,
            0,
            winreg.KEY_QUERY_VALUE,
        ) as key:
            try:
                value, value_type = (
                    winreg.QueryValueEx(
                        key,
                        AUTOSTART_VALUE_NAME,
                    )
                )
            except FileNotFoundError:
                return None

    except FileNotFoundError:
        return None

    if (
        value_type != winreg.REG_SZ
        or not isinstance(value, str)
        or not value
    ):
        raise BackendAutostartError(
            "existing Contextor autostart value is malformed"
        )

    return value


def _write_run_value(
    command: str,
) -> None:
    _require_windows()

    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        AUTOSTART_RUN_KEY,
        0,
        winreg.KEY_SET_VALUE
        | winreg.KEY_QUERY_VALUE,
    ) as key:
        winreg.SetValueEx(
            key,
            AUTOSTART_VALUE_NAME,
            0,
            winreg.REG_SZ,
            command,
        )


def _delete_run_value() -> bool:
    _require_windows()

    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            try:
                winreg.DeleteValue(
                    key,
                    AUTOSTART_VALUE_NAME,
                )
            except FileNotFoundError:
                return False

    except FileNotFoundError:
        return False

    return True


def get_backend_autostart_status(
) -> BackendAutostartStatus:
    expected = (
        backend_autostart_command()
    )
    configured = (
        _read_run_value()
    )

    return BackendAutostartStatus(
        installed=(
            configured is not None
        ),
        command_matches=(
            configured == expected
        ),
        expected_command=expected,
        configured_command=configured,
    )


def install_backend_autostart(
) -> BackendAutostartStatus:
    command = (
        backend_autostart_command()
    )

    _write_run_value(
        command
    )

    status = (
        get_backend_autostart_status()
    )

    if (
        not status.installed
        or not status.command_matches
    ):
        raise BackendAutostartError(
            "Contextor backend autostart registration was not verified"
        )

    return status


def remove_backend_autostart(
) -> BackendAutostartStatus:
    _delete_run_value()

    status = (
        get_backend_autostart_status()
    )

    if status.installed:
        raise BackendAutostartError(
            "Contextor backend autostart removal was not verified"
        )

    return status


def launch_backend_autostart() -> bool:
    try:
        status = start_backend(
            timeout=AUTOSTART_START_TIMEOUT,
            probe_timeout=AUTOSTART_PROBE_TIMEOUT,
        )
    except BackendControlError:
        return False

    return bool(
        status.ready
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "python -m "
            "contextor.mcp_backend_autostart"
        )
    )

    parser.add_argument(
        "command",
        choices=(
            "install",
            "status",
            "remove",
            "launch",
        ),
    )

    return parser


def _emit_status(
    status: BackendAutostartStatus,
) -> None:
    print(
        json.dumps(
            status.to_dict(),
            sort_keys=True,
        )
    )


def main(
    argv: list[str] | None = None,
) -> int:
    args = (
        _build_parser()
        .parse_args(argv)
    )

    if args.command == "launch":
        return (
            0
            if launch_backend_autostart()
            else 1
        )

    try:
        if args.command == "install":
            status = (
                install_backend_autostart()
            )
        elif args.command == "remove":
            status = (
                remove_backend_autostart()
            )
        else:
            status = (
                get_backend_autostart_status()
            )

    except BackendAutostartError as exc:
        print(
            f"[ERROR] {exc}",
            file=sys.stderr,
        )
        return 1

    _emit_status(
        status
    )

    if args.command == "status":
        return (
            0
            if (
                status.installed
                and status.command_matches
            )
            else 1
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "AUTOSTART_PROBE_TIMEOUT",
    "AUTOSTART_RUN_KEY",
    "AUTOSTART_START_TIMEOUT",
    "AUTOSTART_VALUE_NAME",
    "BackendAutostartError",
    "BackendAutostartStatus",
    "backend_autostart_command",
    "get_backend_autostart_status",
    "install_backend_autostart",
    "launch_backend_autostart",
    "main",
    "remove_backend_autostart",
]
