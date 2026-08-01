"""
main.py

Convenience launcher for running Contextor straight from a source
checkout, without installing it first:

    python main.py /path/to/project
    python main.py --gui

Equivalent to `python -m contextor` (or the `contextor` command once
installed with `pip install -e .`). Kept because the Windows launcher
and existing documentation refer to it.
"""

import multiprocessing
import os
import sys

# Allow importing the 'contextor' package from a source checkout.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextor.__main__ import main  # noqa: E402

if __name__ == "__main__":
    multiprocessing.freeze_support()

    sys.exit(main())
