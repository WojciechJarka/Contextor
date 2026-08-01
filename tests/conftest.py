"""
Shared test fixtures.

The 'contextor' package is importable from a source checkout as long as
the project root is on sys.path; no import machinery tricks required.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    """
    Redirects cache, state and output away from real user directories.
    """

    for variable, name in (
        ("CONTEXTOR_CACHE_DIR", "cache"),
        ("CONTEXTOR_STATE_DIR", "state"),
        ("CONTEXTOR_OUTPUT_DIR", "output"),
    ):
        monkeypatch.setenv(variable, str(tmp_path / name))

    return tmp_path


@pytest.fixture
def sample_repo(tmp_path):
    """
    Small repository exercising imports, a cycle and a name collision.
    """

    root = tmp_path / "repo"

    files = {
        "core/__init__.py": "",
        "core/alpha.py": (
            "from core.beta import helper\n"
            "\n"
            "MAX_ITEMS = 10\n"
            "\n"
            "\n"
            "class Engine:\n"
            "    def start(self):\n"
            "        return helper()\n"
        ),
        "core/beta.py": ("from core.alpha import Engine\n\n\ndef helper():\n    return 1\n"),
        "core/gamma.py": (
            "MAX_ITEMS = 99\n"
            "\n"
            "\n"
            "def helper():\n"
            "    return 'a completely different implementation'\n"
        ),
        "ui/__init__.py": "",
        "ui/app.py": (
            "from core.alpha import Engine\n\n\ndef run():\n    return Engine().start()\n"
        ),
    }

    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return root
