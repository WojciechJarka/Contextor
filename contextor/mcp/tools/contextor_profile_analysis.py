import asyncio
import json
import sys
from pathlib import Path


async def _run_profile_subprocess(root: Path, *, exclude_paths: list[str] | None) -> dict[str, object]:
    process = await asyncio.create_subprocess_exec(sys.executable, "-u", "-m", "contextor.core.analysis.profile_worker", stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    request = json.dumps({"repo_path": str(root), "exclude_paths": exclude_paths}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    stdout, stderr = await process.communicate(request)
    if process.returncode != 0:
        error = stderr.decode("utf-8", errors="replace").strip()
        if len(error) > 4000: error = error[-4000:]
        raise RuntimeError("Contextor profile worker failed" + (f": {error}" if error else "."))
    try: payload = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise RuntimeError("Contextor profile worker returned invalid JSON.") from exc
    if not isinstance(payload, dict): raise RuntimeError("Contextor profile worker returned a non-object payload.")
    return payload
async def contextor_profile_analysis(repo_path: str, exclude_paths: list[str] | None = None) -> str:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    profile = await _run_profile_subprocess(root, exclude_paths=exclude_paths)
    return json.dumps(profile, indent=2)

__all__ = ["contextor_profile_analysis"]
