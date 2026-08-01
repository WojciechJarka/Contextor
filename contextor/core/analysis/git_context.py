"""
contextor/core/analysis/git_context.py

Module fetching context from Git (last modification, author, recent churn).
Requires `git` in system PATH.
"""

import subprocess
from pathlib import Path


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
        "last_modified": None,
        "last_author": None,
        "commits_last_30d": 0,
        "churn_score": 0.0,
        "recent_changes": {"lines_added": 0, "lines_removed": 0},
    }

    if not root_path:
        return default_ctx

    p_root = Path(root_path)
    if not (p_root / ".git").exists():
        return default_ctx

    p_file = Path(file_path)
    try:
        rel_path = p_file.relative_to(p_root).as_posix()
    except ValueError:
        return default_ctx

    log_info = _run_git(["log", "-1", "--format=%cI|%an", "--", rel_path], cwd=str(p_root))
    if log_info and "|" in log_info:
        date_str, author = log_info.split("|", 1)
        default_ctx["last_modified"] = date_str
        default_ctx["last_author"] = author

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

    return default_ctx


__all__ = ["collect_git_context"]
