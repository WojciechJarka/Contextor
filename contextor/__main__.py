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
    _hide_console()

    from contextor.ui.gui import run

    run()

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

    from contextor.cli import main as cli_main

    # '--cli' is accepted for symmetry with '--gui' and documentation,
    # but CLI is the default mode.
    return cli_main([arg for arg in argv if arg != "--cli"])


# ============================================================
# Bootstrap
# ============================================================


if __name__ == "__main__":
    # Required before any ProcessPoolExecutor is created on Windows,
    # and harmless elsewhere.
    multiprocessing.freeze_support()

    sys.exit(main())
