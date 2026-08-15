"""
contextor/core/analysis/git_context.py

Module fetching context from Git (last modification, author, recent churn).
Requires `git` in system PATH.
"""

import subprocess
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from contextor.core.git.repo_state import is_git_repo
from contextor.mcp_process_registry import register_process, remove_record


def _run_git(args, cwd):
    record_path = None
    try:
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
        }
        executable = shutil.which("git") or "git"
        process_options = {}
        if os.name == "nt":
            process_options["creationflags"] = getattr(
                subprocess, "CREATE_NO_WINDOW", 0
            )
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = subprocess.SW_HIDE
            process_options["startupinfo"] = startup_info
        process = subprocess.Popen(
            [executable] + args,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **process_options,
        )
        registry = os.environ.get("CONTEXTOR_MCP_PROCESS_REGISTRY")
        if registry:
            record_path = register_process(
                Path(registry),
                pid=process.pid,
                parent_pid=os.getpid(),
                kind="git",
                executable=executable,
            )
        stdout, _ = process.communicate()
        if process.returncode != 0:
            return None
        return stdout.strip()
    except Exception:
        return None
    finally:
        remove_record(record_path)


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

    commands = {
        "log_info": ["log", "-1", "--format=%H|%cI|%an", "--", rel_path],
        "recent_commits": ["log", "--since=30.days", "--oneline", "--", rel_path],
        "diff_stats": ["diff", "HEAD~1", "HEAD", "--numstat", "--", rel_path],
        "patch": ["diff", "HEAD~1", "HEAD", "--", rel_path],
    }
    with ThreadPoolExecutor(max_workers=len(commands)) as executor:
        futures = {
            name: executor.submit(_run_git, args, str(p_root))
            for name, args in commands.items()
        }
        git_results = {name: future.result() for name, future in futures.items()}

    log_info = git_results["log_info"]
    if log_info and "|" in log_info:
        parts = log_info.split("|", 2)
        if len(parts) == 3:
            default_ctx["last_commit"] = parts[0]
            default_ctx["last_modified"] = parts[1]
            default_ctx["last_author"] = parts[2]

    recent_commits = git_results["recent_commits"]
    if recent_commits:
        lines = len(recent_commits.splitlines())
        default_ctx["commits_last_30d"] = lines
        default_ctx["churn_score"] = min(1.0, lines / 10.0)

    diff_stats = git_results["diff_stats"]
    if diff_stats:
        parts = diff_stats.split()
        if len(parts) >= 2:
            try:
                default_ctx["recent_changes"]["lines_added"] = int(parts[0])
                default_ctx["recent_changes"]["lines_removed"] = int(parts[1])
            except ValueError:
                pass
                
    patch = git_results["patch"]
    if patch:
        # opcjonalnie przycięte
        default_ctx["patch"] = patch[:2000]

    return default_ctx


__all__ = ["collect_git_context"]
