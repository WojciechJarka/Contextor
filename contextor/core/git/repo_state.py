"""
contextor/core/git/repo_state.py

Minimal interface for Git repository state.
"""

import subprocess
from pathlib import Path


def _run_git(args, cwd):
    try:
        result = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, check=True
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
    
    # Fast check
    p_root = Path(root_path)
    if (p_root / ".git").exists():
        return True
    
    # Fallback git check
    res = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=root_path)
    return res == "true"


def get_current_commit(root_path: str) -> str | None:
    """
    Returns the current HEAD commit SHA.
    """
    return _run_git(["rev-parse", "HEAD"], cwd=root_path)


def get_branch(root_path: str) -> str | None:
    """
    Returns the current branch name.
    """
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root_path)
