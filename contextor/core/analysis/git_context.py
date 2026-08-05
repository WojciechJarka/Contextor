"""
contextor/core/analysis/git_context.py

Module fetching context from Git (last modification, author, recent churn).
Requires `git` in system PATH.
"""

import subprocess
from pathlib import Path
from contextor.core.git.repo_state import is_git_repo


def _run_git(args, cwd):
    try:
        result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return None


def collect_git_context(file_path: str, root_path: str) -> dict:
    """
    Extracts Git facts for a given file.
    """
    default_ctx = {
        "status": "ok",
        "last_commit": None,
        "last_modified": None,
        "last_author": None,
        "commits_last_30d": 0,
        "churn_score": 0.0,
        "recent_changes": {"lines_added": 0, "lines_removed": 0},
        "patch": None
    }

    if not is_git_repo(root_path):
        return {"status": "non_git_repo"}

    p_root = Path(root_path)
    p_file = Path(file_path)
    try:
        rel_path = p_file.relative_to(p_root).as_posix()
    except ValueError:
        return {"status": "non_git_repo"}

    log_info = _run_git(["log", "-1", "--format=%H|%cI|%an", "--", rel_path], cwd=str(p_root))
    if log_info and "|" in log_info:
        parts = log_info.split("|", 2)
        if len(parts) == 3:
            default_ctx["last_commit"] = parts[0]
            default_ctx["last_modified"] = parts[1]
            default_ctx["last_author"] = parts[2]

    recent_commits = _run_git(
        ["log", "--since=30.days", "--oneline", "--", rel_path], cwd=str(p_root)
    )
    if recent_commits:
        lines = len(recent_commits.splitlines())
        default_ctx["commits_last_30d"] = lines
        default_ctx["churn_score"] = min(1.0, lines / 10.0)

    diff_stats = _run_git(["diff", "HEAD~1", "HEAD", "--numstat", "--", rel_path], cwd=str(p_root))
    if diff_stats:
        parts = diff_stats.split()
        if len(parts) >= 2:
            try:
                default_ctx["recent_changes"]["lines_added"] = int(parts[0])
                default_ctx["recent_changes"]["lines_removed"] = int(parts[1])
            except ValueError:
                pass
                
    patch = _run_git(["diff", "HEAD~1", "HEAD", "--", rel_path], cwd=str(p_root))
    if patch:
        # opcjonalnie przycięte
        default_ctx["patch"] = patch[:2000]

    return default_ctx


__all__ = ["collect_git_context"]
