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
import re
import shutil
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


def repository_registry_root() -> Path:
    """Central identity registry owned by Contextor, never an analyzed repo."""

    return _env_dir("CONTEXTOR_REGISTRY_DIR") or package_root() / ".contextor" / "repositories"


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
    Cache directory dedicated to one analyzed repository identity.

    Registered repositories use their durable ``repo_id``. Before the first
    registration, callers retain the legacy path-derived cache location.
    """

    from contextor.core.repository_identity import read_repository_identity

    identity = read_repository_identity(root_path)
    if identity is not None:
        return app_cache_dir() / "repositories" / identity.repo_id
    return legacy_repo_cache_dir(root_path)


def legacy_repo_cache_dir(root_path: str | Path) -> Path:
    """Pre-identity cache location retained only for safe migration."""

    return app_cache_dir() / repo_key(root_path)


def prune_orphaned_repository_caches() -> dict[str, list[str]]:
    """Remove repo-ID caches that no longer have a central identity record."""

    from contextor.core.repository_identity import registered_repository_ids

    cache_root = app_cache_dir() / "repositories"
    result = {"removed": [], "errors": []}
    if not cache_root.is_dir():
        return result
    registered = registered_repository_ids()
    resolved_root = cache_root.resolve()
    for candidate in cache_root.iterdir():
        if not candidate.is_dir() or not candidate.name.startswith("ctx_"):
            continue
        if candidate.name in registered:
            continue
        resolved_candidate = candidate.resolve()
        if resolved_candidate.parent != resolved_root:
            result["errors"].append(f"unsafe cache path: {resolved_candidate}")
            continue
        try:
            shutil.rmtree(resolved_candidate)
            result["removed"].append(candidate.name)
        except OSError as exc:
            result["errors"].append(f"{candidate.name}: {exc}")
    return result


_TEST_CACHE_DIRECTORY = re.compile(
    r"^(?:test_.+|test_repo|repo|RealMcpLiveTest|TestRepoLive)-[0-9a-f]{16}$",
    re.IGNORECASE,
)


def prune_test_cache_entries() -> dict[str, list[str]]:
    """Remove legacy cache directories created by pytest temporary repositories."""

    cache_root = app_cache_dir()
    result = {"removed": [], "errors": []}
    if not cache_root.is_dir():
        return result
    resolved_root = cache_root.resolve()
    for candidate in cache_root.iterdir():
        if not candidate.is_dir() or not _TEST_CACHE_DIRECTORY.fullmatch(candidate.name):
            continue
        resolved_candidate = candidate.resolve()
        if resolved_candidate.parent != resolved_root:
            result["errors"].append(f"unsafe cache path: {resolved_candidate}")
            continue
        try:
            shutil.rmtree(resolved_candidate)
            result["removed"].append(candidate.name)
        except OSError as exc:
            result["errors"].append(f"{candidate.name}: {exc}")
    return result


def prune_superseded_legacy_repo_caches() -> dict[str, list[str]]:
    """Remove path-keyed caches only after the same registered root has a snapshot by ID."""

    from contextor.core.repository_identity import registered_repository_identities

    cache_root = app_cache_dir()
    result = {"removed": [], "errors": []}
    if not cache_root.is_dir():
        return result
    resolved_root = cache_root.resolve()
    for identity in registered_repository_identities():
        legacy = legacy_repo_cache_dir(identity.root_path)
        current = cache_root / "repositories" / identity.repo_id
        if not legacy.is_dir() or legacy == current:
            continue
        # A modern cache directory alone is not proof of a completed handoff.
        # Keep the legacy parse cache until a complete revisioned snapshot exists.
        if not (current / "engine_state.meta.json").is_file():
            continue
        resolved_legacy = legacy.resolve()
        if resolved_legacy.parent != resolved_root:
            result["errors"].append(f"unsafe cache path: {resolved_legacy}")
            continue
        try:
            shutil.rmtree(resolved_legacy)
            result["removed"].append(legacy.name)
        except OSError as exc:
            result["errors"].append(f"{legacy.name}: {exc}")
    return result


def prune_startup_caches() -> dict[str, dict[str, list[str]]]:
    """Run the safe cache cleanup policy used when desktop Contextor starts."""

    return {
        "orphaned_repository_caches": prune_orphaned_repository_caches(),
        "superseded_legacy_repo_caches": prune_superseded_legacy_repo_caches(),
        "test_cache_entries": prune_test_cache_entries(),
    }


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
