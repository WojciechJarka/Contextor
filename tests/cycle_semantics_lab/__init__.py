"""Small isolated source fixtures for cycle-semantics tests."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath


def write_synthetic_repository(
    root: Path,
    sources: Mapping[str, str],
) -> Path:
    """Write exact UTF-8 Python fixture sources below one test root."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    planned: dict[Path, str] = {}
    for name, source in sources.items():
        if not isinstance(name, str) or "\\" in name or not isinstance(source, str):
            raise ValueError("invalid synthetic source")
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or relative.suffix != ".py"
        ):
            raise ValueError("invalid synthetic path")
        target = root.joinpath(*relative.parts).resolve()
        if target == root or root not in target.parents or target in planned:
            raise ValueError("duplicate or escaping synthetic path")
        planned[target] = source
    for target, source in planned.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.encode("utf-8"))
    return root


def run_synthetic_import(
    root: Path,
    module: str,
    *,
    timeout: float = 8,
) -> subprocess.CompletedProcess[str]:
    """Run only an authored temporary fixture in a fresh isolated CPython."""
    if not isinstance(module, str) or not all(
        part.isidentifier() for part in module.split(".")
    ):
        raise ValueError("invalid synthetic entry module")
    return subprocess.run(
        [
            sys.executable, "-I", "-B", "-c",
            "import importlib,sys;sys.path.insert(0,sys.argv[1]);"
            "importlib.import_module(sys.argv[2])",
            str(Path(root).resolve()), module,
        ],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
