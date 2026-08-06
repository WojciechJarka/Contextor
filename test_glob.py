import glob, os, sys
from pathlib import Path

def _find_latest_report(repo_path: Path, pattern: str) -> Path | None:
    out_dir = repo_path / "output"
    if not out_dir.is_dir():
        return None
    search_pattern = str(out_dir / "**" / pattern)
    print(f"Searching: {search_pattern}")
    matches = sorted(glob.glob(search_pattern, recursive=True), reverse=True)
    print(f"Matches: {matches}")
    for match in matches:
        if "_outdated" not in match:
            return Path(match)
    return None

repo = Path(r"c:\Temp\Contextor_Repo")
print(f"Result for 'Contextor_Repo_summary_*.json': {_find_latest_report(repo, 'Contextor_Repo_summary_*.json')}")
print(f"Result for '*Contextor_Repo_contextor_graph_analytics_*.json': {_find_latest_report(repo, '*Contextor_Repo_contextor_graph_analytics_*.json')}")
