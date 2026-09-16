import asyncio
import json
import os
import sys
from pathlib import Path

from contextor.mcp_process_registry import (
    register_process,
    remove_record,
    terminate_registered_record,
)


_PROFILE_PROCESS_WAIT_SECONDS = 2.0


async def _wait_profile_process(
    process: asyncio.subprocess.Process,
    *,
    timeout: float = _PROFILE_PROCESS_WAIT_SECONDS,
) -> None:
    if process.returncode is not None:
        return
    try:
        await asyncio.wait_for(
            process.wait(),
            timeout=max(0.0, timeout),
        )
    except asyncio.TimeoutError:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        try:
            await process.wait()
        except ProcessLookupError:
            pass


async def _terminate_profile_subprocess(
    process: asyncio.subprocess.Process,
    record_path: Path | None,
) -> None:
    if process.returncode is not None:
        return

    if record_path is not None:
        try:
            await asyncio.shield(
                asyncio.to_thread(
                    terminate_registered_record,
                    record_path,
                )
            )
        except Exception:
            pass

    if process.returncode is None:
        try:
            process.terminate()
        except ProcessLookupError:
            pass

    await _wait_profile_process(process)


async def _run_profile_subprocess(
    root: Path,
    *,
    exclude_paths: list[str] | None,
) -> dict[str, object]:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        "-m",
        "contextor.core.analysis.profile_worker",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    record_path: Path | None = None
    registry_value = os.environ.get(
        "CONTEXTOR_MCP_PROCESS_REGISTRY"
    )

    if registry_value:
        record_path = register_process(
            Path(registry_value),
            pid=process.pid,
            parent_pid=os.getpid(),
            kind="profile-worker",
            executable=sys.executable,
        )

    request = json.dumps(
        {
            "repo_path": str(root),
            "exclude_paths": exclude_paths,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    try:
        stdout, stderr = await process.communicate(
            request
        )
    except BaseException:
        await _terminate_profile_subprocess(
            process,
            record_path,
        )
        raise
    finally:
        remove_record(record_path)

    if process.returncode != 0:
        error = stderr.decode(
            "utf-8",
            errors="replace",
        ).strip()
        if len(error) > 4000:
            error = error[-4000:]
        raise RuntimeError(
            "Contextor profile worker failed"
            + (
                f": {error}"
                if error
                else "."
            )
        )

    try:
        payload = json.loads(
            stdout.decode("utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            "Contextor profile worker returned invalid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            "Contextor profile worker returned a non-object payload."
        )

    return payload


async def contextor_profile_analysis(
    repo_path: str,
    exclude_paths: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return (
            f"Error: Repository path '{root}' "
            "does not exist."
        )

    profile = await _run_profile_subprocess(
        root,
        exclude_paths=exclude_paths,
    )
    return json.dumps(
        profile,
        indent=2,
    )


__all__ = [
    "contextor_profile_analysis",
]
