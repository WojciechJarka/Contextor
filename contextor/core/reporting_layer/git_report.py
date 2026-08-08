"""
contextor/core/reporting_layer/git_report.py

Builds Git and diff sections for global and single-file reports.
"""

from contextor.core.analysis.git_context import collect_git_context


def build_global_git_section(
    current_header: dict,
    repo_state: dict,
) -> dict:
    """
    Builds the 'git_changes' block for the global summary report.
    """
    if not repo_state.get("is_git_repo", False):
        return {"status": "non_git_repo"}

    current_commit = current_header.get("commit_sha")
        
    git_section = {
        "status": "LIVE_CANONICAL_STATE",
        "current": {
            "branch": current_header.get("branch"),
            "commit_sha": current_commit,
            "generated_at": current_header.get("generated_at"),
        }
    }
    
    return git_section


def build_single_file_git_section(file_path: str, root_path: str) -> dict:
    """
    Builds the 'git' block for a single-file architectural report.
    """
    ctx = collect_git_context(file_path, root_path)
    
    if ctx.get("status") == "non_git_repo":
        return {"status": "non_git_repo"}
        
    return {
        "status": "ok",
        "last_commit": ctx.get("last_commit"),
        "last_modified": ctx.get("last_modified"),
        "last_author": ctx.get("last_author"),
        "patch": ctx.get("patch")
    }
