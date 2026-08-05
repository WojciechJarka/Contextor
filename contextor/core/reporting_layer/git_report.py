"""
contextor/core/reporting_layer/git_report.py

Builds Git and diff sections for global and single-file reports.
"""

from contextor.core.analysis.git_context import collect_git_context


def build_global_git_section(
    current_header: dict,
    previous_header: dict | None,
    diff_stats: dict | None,
    repo_state: dict,
    regression_status: str,
) -> dict:
    """
    Builds the 'git_changes' block for the global summary report.
    """
    if not repo_state.get("is_git_repo", False):
        return {"status": "non_git_repo"}

    current_commit = current_header.get("commit_sha")
    previous_commit = previous_header.get("commit_sha") if previous_header else None
    
    # Fallback to unchanged
    if current_commit == previous_commit and diff_stats and diff_stats.get("is_empty"):
        return {
            "status": "no_changes",
            "current_commit": current_commit,
            "previous_commit": previous_commit
        }
        
    git_section = {
        "status": regression_status,
        "current": {
            "branch": current_header.get("branch"),
            "commit_sha": current_commit,
            "generated_at": current_header.get("generated_at"),
        }
    }
    
    if previous_header:
        git_section["previous"] = {
            "branch": previous_header.get("branch"),
            "commit_sha": previous_commit,
            "generated_at": previous_header.get("generated_at"),
        }
        
    if diff_stats:
        delta = {}
        if "debt" in diff_stats:
            for k, v in diff_stats["debt"].items():
                delta[k] = v.get("delta")
        if delta:
            git_section["delta"] = delta
            
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
