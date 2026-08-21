from pathlib import Path

from contextor.core.paths import output_dir as resolve_output_dir


def get_canonical_report(repo_path: Path, filename: str) -> Path | None:
    """Return a report from the shared GUI/CLI/MCP output directory."""
    del repo_path
    out_dir = resolve_output_dir()
    if not out_dir.is_dir():
        return None
    target = out_dir / filename
    if target.is_file():
        return target
    for sub in out_dir.iterdir():
        if sub.is_dir():
            sub_target = sub / filename
            if sub_target.is_file():
                return sub_target
    return None
