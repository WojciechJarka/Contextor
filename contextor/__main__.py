"""
contextor/__main__.py

Entry point of the Contextor application.

Responsible exclusively for startup routing:
- CLI (default)
- GUI (--gui)

Does not contain analytical logic.

Runnable as `python -m contextor`.
"""

import multiprocessing
import sys

# ============================================================
# GUI
# ============================================================


def _hide_console() -> None:
    """
    Hides the console window that launched a GUI session on Windows.
    """

    if sys.platform != "win32":
        return

    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()

        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)

    except (OSError, AttributeError):
        # Console control is cosmetic; never let it block startup.
        pass


def _run_gui() -> int:
    from contextor.ui.single_instance import DesktopSingleInstance

    guard = DesktopSingleInstance.acquire()
    if not guard.is_primary:
        guard.signal_existing()
        guard.close()
        return 0
    from contextor.core.program_log import configure_program_log
    from contextor.core.runtime_trace import (
        finish_desktop_trace_session,
        start_desktop_trace_session,
    )

    configure_program_log()
    start_desktop_trace_session()
    try:
        _hide_console()

        from contextor.ui.gui import run

        run(single_instance=guard)
    finally:
        finish_desktop_trace_session()
        guard.close()

    return 0


# ============================================================
# Main
# ============================================================


def main(argv: list[str] | None = None) -> int:
    """
    Application entry point.
    """

    argv = list(sys.argv[1:] if argv is None else argv)

    if "--gui" in argv:
        return _run_gui()

    # '--cli' is accepted for symmetry with '--gui' and documentation,
    # but CLI is the default mode.
    cli_argv = [
        arg
        for arg in argv
        if arg != "--cli"
    ]

    if (
        len(cli_argv) >= 2
        and cli_argv[0] == "backend"
        and cli_argv[1]
        in {
            "start",
            "status",
            "stop",
        }
    ):
        from contextor.mcp_backend_cli import (
            main as backend_cli_main,
        )

        return backend_cli_main(
            cli_argv[1:]
        )

    from contextor.cli import main as cli_main

    return cli_main(
        cli_argv
    )


# ============================================================
# Bootstrap
# ============================================================


if __name__ == "__main__":
    # Required before any ProcessPoolExecutor is created on Windows,
    # and harmless elsewhere.
    multiprocessing.freeze_support()

    sys.exit(main())
