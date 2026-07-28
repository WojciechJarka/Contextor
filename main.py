# -*- coding: utf-8 -*-
"""
repo_guardian/main.py

Entry point of the Repo Guardian application.

Responsible exclusively for startup routing:
- CLI (default)
- GUI (--gui)

Does not contain analytical logic.
"""

import os
import sys


# ============================================================
# Configure Python path
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# HACK/FIX: Map the virtual 'repo_guardian' package directly to the repository root,
# which allows running the code smoothly even when the repository folder has a different name
# (e.g. Repo_Guardian_Repo) and it was not installed via pip install -e .
import importlib.machinery
import importlib.abc

class RepoGuardianAliaser(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "repo_guardian":
            spec = importlib.machinery.ModuleSpec("repo_guardian", None, is_package=True)
            spec.submodule_search_locations = [PROJECT_ROOT]
            return spec
        return None

if not any(isinstance(f, RepoGuardianAliaser) for f in sys.meta_path):
    sys.meta_path.insert(0, RepoGuardianAliaser())


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
