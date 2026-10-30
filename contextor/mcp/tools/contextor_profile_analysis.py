import asyncio
import json
import os
import sys
from pathlib import Path

from contextor.core.profiling.registry import SCHEMA, build_catalog, get_scope, list_scopes, validate_scope_presets
from contextor.core.profiling.runner import validate_probe_request
from contextor.mcp.query_helpers import fuzzy_choice_candidates

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

    bounded_timeout = max(
        0.0,
        timeout,
    )

    try:
        await asyncio.wait_for(
            process.wait(),
            timeout=bounded_timeout,
        )
        return
    except asyncio.TimeoutError:
        pass

    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass

    if process.returncode is not None:
        return

    try:
        await asyncio.wait_for(
            process.wait(),
            timeout=bounded_timeout,
        )
    except (
        asyncio.TimeoutError,
        ProcessLookupError,
    ):
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
    probe_request: dict[str, object] | None = None,
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

    try:
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

        request_payload = (
            {
                "repo_path": str(root),
                "exclude_paths": exclude_paths,
            } if probe_request is None else {"repo_path": str(root), **probe_request}
        )
        request = json.dumps(
            request_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

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
        if process.returncode is not None:
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
    mode: str = "full",
    scope: str | None = None,
    presets: list[str] | None = None,
    samples: int = 1,
    warmup: int = 0,
    result_view: str = "summary",
) -> str:
    def invalid(parameter: str, value: object, reason: str, allowed: list[str] | None = None,
                owner: str | None = None) -> str:
        result: dict[str, object] = {
            "schema": SCHEMA, "status": "invalid_profile_request", "parameter": parameter,
            "invalid_value": value[:120] if isinstance(value, str) else value if isinstance(value, (int, float, bool, type(None))) else str(type(value).__name__),
            "reason": reason, "similar_candidates": fuzzy_choice_candidates(value, allowed or []) if isinstance(value, str) else [],
            "allowed_values": allowed or [], "retry_instruction": "Choose an exact supported value.",
            "documentation_hint": "get_mcp_documentation",
        }
        if owner is not None:
            result["owning_scope"] = owner
        return json.dumps(result, ensure_ascii=False)

    if not isinstance(mode, str) or mode not in ("full", "catalog", "probe"):
        return invalid("mode", mode, "Unsupported profiling mode.", ["full", "catalog", "probe"])
    if not isinstance(repo_path, str) or not repo_path.strip():
        return invalid("repo_path", repo_path, "Repository path must be a nonempty string.")
    if mode == "full":
        if scope is not None or presets is not None or samples != 1 or type(samples) is not int or warmup != 0 or type(warmup) is not int or result_view != "summary":
            return invalid("mode", mode, "FULL mode does not accept probe parameters.")
        if exclude_paths is not None and (not isinstance(exclude_paths, list) or
                                          any(not isinstance(item, str) or not item.strip() for item in exclude_paths)):
            return invalid("exclude_paths", exclude_paths, "Invalid exclusions.")
    else:
        if exclude_paths is not None:
            return invalid("exclude_paths", exclude_paths, "Exclusions are valid only for FULL mode.")
        if mode == "catalog":
            if scope is not None or presets is not None or samples != 1 or type(samples) is not int or warmup != 0 or type(warmup) is not int or result_view != "summary":
                return invalid("mode", mode, "Catalog does not accept probe parameters.")
            return json.dumps(build_catalog(), ensure_ascii=False)
        if scope is None:
            return invalid("scope", scope, "A scope is required.", [item.name for item in list_scopes()])
        if not isinstance(scope, str) or get_scope(scope) is None:
            return invalid("scope", scope, "Unsupported profiling scope.", [item.name for item in list_scopes()])
        if not isinstance(presets, list) or not presets:
            return invalid("presets", presets, "Explicit nonempty preset selection required.", list(get_scope(scope).presets))
        if any(not isinstance(item, str) for item in presets):
            return invalid("presets", presets, "Presets must be strings.", list(get_scope(scope).presets))
        if len(set(presets)) != len(presets):
            return invalid("presets", presets, "Duplicate preset.", list(get_scope(scope).presets))
        for preset in presets:
            if preset not in get_scope(scope).presets:
                owner = next((item.name for item in list_scopes() if preset in item.presets), None)
                return invalid("presets", preset, "Preset does not belong to selected scope.", list(get_scope(scope).presets), owner)
        if type(samples) is not int or not 1 <= samples <= 10:
            return invalid("samples", samples, "samples must be an integer from 1 to 10.")
        if type(warmup) is not int or not 0 <= warmup <= 3:
            return invalid("warmup", warmup, "warmup must be an integer from 0 to 3.")
        if not isinstance(result_view, str) or result_view not in ("summary", "spans"):
            return invalid("result_view", result_view, "Unsupported result view.", ["summary", "spans"])
        validated_presets = list(validate_probe_request(scope, presets, samples, warmup, result_view))
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return (
            f"Error: Repository path '{root}' "
            "does not exist."
        )

    profile = await _run_profile_subprocess(
        root,
        exclude_paths=exclude_paths,
        **({"probe_request": {
            "mode": "probe", "scope": scope, "presets": validated_presets,
            "samples": samples, "warmup": warmup, "result_view": result_view,
        }} if mode == "probe" else {}),
    )
    if mode == "probe":
        return json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(profile, indent=2)


__all__ = [
    "contextor_profile_analysis",
]
