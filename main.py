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
import os

project_root = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_root)
folder_name = os.path.basename(project_root)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

if folder_name != "repo_guardian":
    import importlib
    # Import the package using its real folder name
    real_mod = importlib.import_module(folder_name)
    # Alias it in sys.modules so any "import repo_guardian" redirects here
    sys.modules["repo_guardian"] = real_mod

def main():
    # GUI mode
    if "--gui" in sys.argv:
        from repo_guardian.ui.gui import run
        run()
        return

    # CLI mode (default)
    from repo_guardian.cli import main as cli_main
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(cli_main(path))


if __name__ == "__main__":
    main()
