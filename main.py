# -*- coding: utf-8 -*-
"""
repo_guardian/main.py

Entry point aplikacji Repo Guardian.

Odpowiada wyłącznie za routing uruchomienia:
- CLI (domyślnie)
- GUI (--gui)

Nie zawiera logiki analitycznej.
"""

import sys


def main():
    # GUI mode
    if "--gui" in sys.argv:
        from repo_guardian.ui.gui import run
        run()
        return

    # CLI mode (default)
    from repo_guardian.cli import main as cli_main
    sys.exit(cli_main())


if __name__ == "__main__":
    main()
