# -*- coding: utf-8 -*-
"""
repo_guardian/main.py

Entry point aplikacji Repo Guardian.

Odpowiada wyłącznie za routing uruchomienia:
- CLI (domyślnie)
- GUI (--gui)

Nie zawiera logiki analitycznej.
"""

import os
import sys


# ============================================================
# Configure Python path
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# Main
# ============================================================

def main() -> None:
    """
    Application entry point.
    """

    if "--gui" in sys.argv:
        from repo_guardian.ui.gui import run

        run()
        return

    from repo_guardian.cli import main as cli_main

    path = "."

    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            path = arg
            break

    sys.exit(cli_main(path))


# ============================================================
# Bootstrap
# ============================================================

if __name__ == "__main__":
    main()
