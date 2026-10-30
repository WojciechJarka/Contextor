"""CPython 3.10 import-resolution contracts for namespace packages.

These tests do not authorize LIVE MODEL_PASS or warning suppression.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _run(roots: tuple[Path, ...], script: str):
    prefix = (
        "import sys, json\n"
        "roots=json.loads(sys.argv[1])\n"
        "sys.path[:0]=roots\n"
    )
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            prefix + script,
            json.dumps([str(root) for root in roots]),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _restricted(sources: dict[str, str], entry: str):
    return evaluate_package_import_order(
        {
            name: ast.parse(source)
            for name, source in sources.items()
        },
        entry,
    )


def test_t01_namespace_under_regular_package(tmp_path):
    root = tmp_path / "root"
    _write(root, "regular/__init__.py", "value = 1\n")
    _write(root, "regular/ns/child.py", "value = 7\n")

    result = _run(
        (root,),
        (
            "import regular.ns.child\n"
            "assert regular.ns.child.value == 7\n"
            "assert regular.ns.__spec__.origin is None\n"
            "assert regular.ns.__spec__.submodule_search_locations\n"
        ),
    )
    assert result.returncode == 0, result.stderr

    model = _restricted(
        {
            "regular.__init__": "value = 1",
            "regular.ns.child": "value = 7",
        },
        "regular.ns.child",
    )
    assert model.outcome == "UNKNOWN"


def test_t02_top_level_namespace(tmp_path):
    root = tmp_path / "root"
    _write(root, "nsp/child.py", "value = 11\n")

    result = _run(
        (root,),
        (
            "import nsp.child\n"
            "assert nsp.child.value == 11\n"
            "assert nsp.__spec__.origin is None\n"
            "assert nsp.__spec__.submodule_search_locations\n"
        ),
    )
    assert result.returncode == 0, result.stderr

    assert _restricted(
        {"nsp.child": "value = 11"},
        "nsp.child",
    ).outcome == "UNKNOWN"


def test_t03_namespace_with_two_portions(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    _write(first, "nsp/left.py", "value = 1\n")
    _write(second, "nsp/right.py", "value = 2\n")

    result = _run(
        (first, second),
        (
            "import nsp.left, nsp.right\n"
            "assert nsp.left.value == 1\n"
            "assert nsp.right.value == 2\n"
            "assert len(list(nsp.__path__)) == 2\n"
        ),
    )
    assert result.returncode == 0, result.stderr


def test_t04_later_regular_package_shadows_namespace(
    tmp_path,
):
    first = tmp_path / "first"
    second = tmp_path / "second"

    _write(first, "nsp/namespace_child.py", "value = 1\n")
    _write(second, "nsp/__init__.py", "value = 99\n")

    result = _run(
        (first, second),
        (
            "import nsp\n"
            "assert nsp.value == 99\n"
            "assert nsp.__file__ is not None\n"
            "assert nsp.__spec__.origin.endswith('__init__.py')\n"
        ),
    )
    assert result.returncode == 0, result.stderr


def test_t05_namespace_path_changes_dynamically(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    _write(first, "nsp/left.py", "value = 1\n")
    _write(second, "nsp/right.py", "value = 2\n")

    result = _run(
        (first,),
        (
            "import nsp.left\n"
            f"sys.path.insert(0, {str(second)!r})\n"
            "import nsp.right\n"
            "assert nsp.right.value == 2\n"
            "assert len(list(nsp.__path__)) == 2\n"
        ),
    )
    assert result.returncode == 0, result.stderr


def test_t06_meta_path_finder_can_override_resolution(
    tmp_path,
):
    root = tmp_path / "root"
    _write(root, "nsp/child.py", "value = 7\n")

    result = _run(
        (root,),
        (
            "import nsp\n"
            "class Blocker:\n"
            "    def find_spec(self, fullname, path=None, target=None):\n"
            "        if fullname == 'nsp.child':\n"
            "            raise ModuleNotFoundError('blocked by finder')\n"
            "sys.meta_path.insert(0, Blocker())\n"
            "try:\n"
            "    import nsp.child\n"
            "except ModuleNotFoundError as exc:\n"
            "    assert str(exc) == 'blocked by finder'\n"
            "else:\n"
            "    raise AssertionError('custom finder was ignored')\n"
        ),
    )
    assert result.returncode == 0, result.stderr
