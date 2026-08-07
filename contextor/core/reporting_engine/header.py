from datetime import datetime
from contextor.core.git.repo_state import is_git_repo, get_current_commit

def build_report_header(root_path: str, data_source: str) -> dict:
    """
    Builds the common header for all generated reports.
    """
    header = {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "data_source": data_source,
        "commit_sha": None,
        "branch": None,
    }
    try:
        from contextor.core.analysis.git_context import collect_git_context
        git_ctx = collect_git_context(root_path)
        if git_ctx and getattr(git_ctx, "commit_hash", None):
            header["commit_sha"] = git_ctx.commit_hash
        elif is_git_repo(root_path):
            header["commit_sha"] = get_current_commit(root_path)
    except Exception:
        pass
    return header
