"""
contextor/core/paths.py

CENTRAL PATH RESOLUTION

Single source of truth for every location Contextor reads from or writes to.

Rules enforced here:

- Contextor NEVER writes into the analyzed repository (read-only contract).
- No path is ever resolved against the current working directory.
- Cache is namespaced per analyzed repository by absolute-path hash,
  so two repositories with the same folder name never share state.
"""

import hashlib
import os
from pathlib import Path

# ==========================================================
# INSTALLATION ROOT
# ==========================================================


def package_root() -> Path:
    """
    Directory containing the Contextor installation.

    contextor/core/paths.py -> contextor/ -> installation root.
    """

    return Path(__file__).resolve().parents[2]


# ==========================================================
# RESOLUTION HELPERS
# ==========================================================


def _env_dir(variable: str) -> Path | None:
    """
    Directory named by an environment variable, if it is set.
    """

    value = os.environ.get(variable)

    return Path(value).expanduser().resolve() if value else None


def _platform_dir(windows_var: str, windows_sub: str, xdg_var: str, home_sub: Path) -> Path:
    """
    Per-user directory following the host platform's convention.
    """

    windows_base = os.environ.get(windows_var)

    if windows_base:
        return Path(windows_base) / windows_sub

    xdg_base = os.environ.get(xdg_var)

    if xdg_base:
        return Path(xdg_base) / "contextor"

    return Path.home() / home_sub


# ==========================================================
# OUTPUT
# ==========================================================


def output_dir() -> Path:
    """
    Directory receiving generated reports.

    Anchored to the installation, never to the process CWD, so that
    CLI and GUI always agree on where reports live.

    Override with the CONTEXTOR_OUTPUT_DIR environment variable.
    """

    return _env_dir("CONTEXTOR_OUTPUT_DIR") or package_root() / "output"


def resolve_report_path(path: str | Path) -> Path:
    """
    Anchors a report path to the output directory.

    A relative path used to be resolved against the process working
    directory, so reports landed wherever the user happened to launch
    from and the GUI looked for them somewhere else entirely.

    Lives here rather than in the reporting package because that
    package's __init__ pulls in the whole reporting engine; writers that
    only need a path would otherwise have to import it lazily to dodge a
    cycle.
    """

    candidate = Path(path)

    if candidate.is_absolute():
        return candidate

    parts = candidate.parts

    # Callers historically prefixed paths with "output/"; that prefix is
    # now expressed by the output directory itself.
    if parts and parts[0] == "output":
        candidate = Path(*parts[1:]) if len(parts) > 1 else Path()

    return output_dir() / candidate


def atomic_write(path: str | Path, data: bytes | str, encoding: str = "utf-8") -> Path:
    """
    Writes a file via a temporary sibling and an atomic replace.

    An interrupted run must never leave a truncated report or cache entry
    that the next run would fail to read.
    """

    target = Path(path)

    ensure_dir(target.parent)

    payload = data.encode(encoding) if isinstance(data, str) else data

    temp_target = target.with_name(target.name + ".tmp")

    with open(temp_target, "wb") as handle:
        handle.write(payload)

    os.replace(temp_target, target)

    return target


# ==========================================================
# CACHE
# ==========================================================


def app_cache_dir() -> Path:
    """
    User-level cache root for Contextor.

    Deliberately outside every analyzed repository: Contextor advertises
    read-only analysis and must not create files in inspected projects.

    Override with the CONTEXTOR_CACHE_DIR environment variable.
    """

    return _env_dir("CONTEXTOR_CACHE_DIR") or _platform_dir(
        "LOCALAPPDATA",
        "Contextor/cache",
        "XDG_CACHE_HOME",
        Path(".cache") / "contextor",
    )


def repo_key(root_path: str | Path) -> str:
    """
    Stable identifier for an analyzed repository.

    Derived from the absolute path, so repositories sharing a folder
    name ('/work/api' and '/private/api') stay isolated.
    """

    resolved = str(Path(root_path).expanduser().resolve())

    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]

    return f"{Path(resolved).name}-{digest}"


def repo_cache_dir(root_path: str | Path) -> Path:
    """
    Cache directory dedicated to one analyzed repository.
    """

    return app_cache_dir() / repo_key(root_path)


# ==========================================================
# STATE
# ==========================================================


def state_dir() -> Path:
    """
    Directory holding user-level UI state and exclude configuration.

    Kept out of the installation directory, which may be read-only.

    Override with the CONTEXTOR_STATE_DIR environment variable.
    """

    return _env_dir("CONTEXTOR_STATE_DIR") or _platform_dir(
        "APPDATA",
        "Contextor",
        "XDG_CONFIG_HOME",
        Path(".config") / "contextor",
    )


# ==========================================================
# HELPERS
# ==========================================================


# Directories never worth indexing, in any analyzed repository.
#
# Single source of truth: the indexer and the exclude configuration used
# to carry overlapping but unequal copies, so which directories were
# skipped depended on which entry point the user came through.
DEFAULT_IGNORED_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "venv",
        ".venv",
        "python",
        "Python",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode",
        "scratch",
    }
)


def ensure_dir(path: str | Path) -> Path:
    """
    Creates a directory (with parents) and returns it.
    """

    resolved = Path(path)

    resolved.mkdir(parents=True, exist_ok=True)

    return resolved
