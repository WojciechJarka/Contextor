"""
contextor/core/git/repo_state.py

Minimal interface for Git repository state.
"""

import subprocess
import os
from pathlib import Path


def _find_git_dir(root_path: str) -> Path | None:
    """Resolve a repository's Git directory without spawning Git."""
    start = Path(root_path).resolve()
    for worktree in (start, *start.parents):
        marker = worktree / ".git"
        if marker.is_dir():
            return marker
        if marker.is_file():
            try:
                value = marker.read_text(encoding="utf-8").strip()
                if value.lower().startswith("gitdir:"):
                    git_dir = Path(value.split(":", 1)[1].strip())
                    if not git_dir.is_absolute():
                        git_dir = worktree / git_dir
                    return git_dir.resolve()
            except OSError:
                return None
    return None


def _common_git_dir(git_dir: Path) -> Path:
    """Return the shared Git directory for linked worktrees."""
    common_marker = git_dir / "commondir"
    try:
        value = common_marker.read_text(encoding="utf-8").strip()
    except OSError:
        return git_dir
    common = Path(value)
    if not common.is_absolute():
        common = git_dir / common
    return common.resolve()


def _read_ref(git_dir: Path, ref_name: str) -> str | None:
    common_dir = _common_git_dir(git_dir)
    for base in (git_dir, common_dir):
        try:
            value = (base / ref_name).read_text(encoding="ascii").strip()
            if value:
                return value
        except OSError:
            pass

    for base in dict.fromkeys((git_dir, common_dir)):
        try:
            lines = (base / "packed-refs").read_text(encoding="ascii").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line or line[0] in "#^":
                continue
            sha, _, packed_ref = line.partition(" ")
            if packed_ref == ref_name:
                return sha
    return None


def _read_head(root_path: str) -> tuple[str | None, str | None]:
    git_dir = _find_git_dir(root_path)
    if git_dir is None:
        return None, None
    try:
        head = (git_dir / "HEAD").read_text(encoding="ascii").strip()
    except OSError:
        return None, None
    if head.startswith("ref: "):
        ref_name = head[5:].strip()
        return _read_ref(git_dir, ref_name), ref_name
    return (head or None), None


def _run_git(args, cwd):
    try:
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
        }
        process_options = {}
        if os.name == "nt":
            process_options["creationflags"] = getattr(
                subprocess, "CREATE_NO_WINDOW", 0
            )
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = subprocess.SW_HIDE
            process_options["startupinfo"] = startup_info
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
            **process_options,
        )
        return result.stdout.strip()
    except Exception:
        return None


def is_git_repo(root_path: str) -> bool:
    """
    Checks if the given root_path is within a Git repository.
    """
    if not root_path:
        return False
    
    if _find_git_dir(root_path) is not None:
        return True
    
    # Fallback git check
    res = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=root_path)
    return res == "true"


def get_current_commit(root_path: str) -> str | None:
    """
    Returns the current HEAD commit SHA.
    """
    commit, _ = _read_head(root_path)
    return commit


def get_branch(root_path: str) -> str | None:
    """
    Returns the current branch name.
    """
    _, ref_name = _read_head(root_path)
    if ref_name is None:
        return "HEAD" if _find_git_dir(root_path) is not None else None
    prefix = "refs/heads/"
    return ref_name[len(prefix):] if ref_name.startswith(prefix) else ref_name
