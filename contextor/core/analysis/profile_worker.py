from __future__ import annotations
import json
import multiprocessing
import sys
from pathlib import Path
from typing import Any
from contextor.core.analysis.profile_runner import run_analysis_profile
def execute_profile_request(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict): raise ValueError("profile worker request must be a JSON object")
    repo_path = payload.get("repo_path")
    if not isinstance(repo_path, str) or not repo_path.strip(): raise ValueError("repo_path must be a non-empty string")
    exclude_paths = payload.get("exclude_paths")
    if exclude_paths is not None and (not isinstance(exclude_paths, list) or not all(isinstance(item, str) and item.strip() for item in exclude_paths)): raise ValueError("exclude_paths must be null or an array of non-empty strings")
    return run_analysis_profile(Path(repo_path), exclude_paths=exclude_paths)
def main() -> int:
    payload: Any = json.loads(sys.stdin.buffer.read().decode("utf-8")); result = execute_profile_request(payload)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":"))); sys.stdout.flush(); return 0
if __name__ == "__main__":
    multiprocessing.freeze_support(); raise SystemExit(main())
__all__ = ["execute_profile_request", "main"]
