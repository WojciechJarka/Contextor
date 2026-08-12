from datetime import datetime
from contextor.core.git.repo_state import get_branch, get_current_commit, is_git_repo

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
        if is_git_repo(root_path):
            header["commit_sha"] = get_current_commit(root_path)
            header["branch"] = get_branch(root_path)
    except Exception:
        pass
    return header
