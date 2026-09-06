import json
import os
from pathlib import Path

from contextor.core.source import SourceError
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import guard_large_output
from contextor.mcp.source_helpers import canonical_python_sources, read_range


def _select_exact_source(
    root: Path,
    state: object,
    normalized_file_path: str,
) -> tuple[str, str, Path] | None:
    """Select an exact, non-legacy canonical source without a full projection."""
    matches: list[tuple[str, str, Path]] = []
    for module_name, module in sorted((getattr(state, "modules", {}) or {}).items()):
        relative = str(getattr(module, "path", "") or "").replace("\\", "/")
        if not relative or relative != normalized_file_path:
            continue

        candidate = root / relative
        absolute_raw = str(getattr(module, "absolute_path", "") or "")
        if absolute_raw:
            declared_absolute = Path(absolute_raw).expanduser()
            if os.path.normcase(os.path.normpath(str(declared_absolute))) != os.path.normcase(
                os.path.normpath(str(candidate))
            ):
                return None

        try:
            candidate = candidate.resolve()
            candidate.relative_to(root)
        except (OSError, ValueError):
            continue
        if candidate.suffix == ".py":
            matches.append((relative, str(module_name), candidate))

    if not matches:
        return None
    return sorted(matches, key=lambda item: (item[0].casefold(), item[1].casefold()))[0]


def get_source_range(
    repo_path: str,
    file_path: str,
    start_line: int,
    end_line: int,
    allow_large_output: bool = False,
) -> str:
    if not isinstance(file_path, str) or not file_path:
        return json.dumps({"status": "error", "error": "invalid_file_path"}, indent=2)
    if (
        isinstance(start_line, bool)
        or not isinstance(start_line, int)
        or isinstance(end_line, bool)
        or not isinstance(end_line, int)
        or start_line < 1
        or end_line < start_line
    ):
        return json.dumps({"status": "error", "error": "invalid_line_range"}, indent=2)
    if not isinstance(allow_large_output, bool):
        return json.dumps({"status": "error", "error": "invalid_allow_large_output"}, indent=2)

    root = Path(repo_path).expanduser().resolve()
    engine = mcp_runtime.get_or_init_engine(root)
    if not engine or getattr(engine.state, "resync_required", False):
        return json.dumps({"status": "error", "error": "canonical_state_unavailable"}, indent=2)

    normalized = file_path.replace("\\", "/")
    selected = _select_exact_source(root, engine.state, normalized)
    if selected is None:
        sources = canonical_python_sources(root, engine.state)
        selected = next((item for item in sources if item[0] == normalized), None)
    if selected is None:
        return json.dumps({"status": "error", "error": "file_not_in_canonical_scope"}, indent=2)
    relative, module_name, absolute = selected
    unavailable = query_helpers.module_truth_unavailable(engine.state, module_name)
    if unavailable:
        return json.dumps(unavailable, indent=2)
    try:
        text, source_total_lines = read_range(absolute, start_line, end_line)
    except (SourceError, ValueError) as exc:
        return json.dumps({"status": "error", "error": "source_range_unavailable", "reason": str(exc)}, indent=2)

    result = {
        "status": "ok",
        "file_path": relative,
        "module": module_name,
        "start_line": start_line,
        "end_line": end_line,
        "total_lines": end_line - start_line + 1,
        "source_total_lines": source_total_lines,
        "text": text,
    }
    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    return guard_large_output(
        serialized,
        allow_large_output=allow_large_output,
        requested_count=end_line - start_line + 1,
        reason="Source range output exceeds the recommended context size.",
        retry_instruction=(
            "Repeat the same get_source_range call with the same repo_path, file_path, start_line, and end_line and set allow_large_output=true."
        ),
    )
