import json
from pathlib import Path

from contextor.core.source import SourceError, read_source
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.output_guard import guard_large_output
from contextor.mcp.source_helpers import (
    canonical_python_sources,
    SourceSpanResolver,
    matched_line_numbers,
    shape_span,
)


def search_source(
    repo_path: str,
    search_term: str | None = None,
    limit: int | None = 20,
    case_sensitive: bool = False,
    allow_large_output: bool = False,
    query: str | None = None,
) -> str:
    if search_term is None and query is None:
        return json.dumps(
            {
                "status": "error",
                "error": "search_term or query is required.",
            },
            indent=2,
        )

    if (
        search_term is not None
        and query is not None
        and search_term != query
    ):
        return json.dumps(
            {
                "status": "error",
                "error": "search_term and query must match when both are provided.",
            },
            indent=2,
        )

    effective_term = search_term if search_term is not None else query

    if (
        not isinstance(effective_term, str)
        or not effective_term
        or "\n" in effective_term
        or "\r" in effective_term
    ):
        return json.dumps({"status": "error", "error": "invalid_search_term"}, indent=2)
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
    ):
        return json.dumps({"status": "error", "error": "invalid_limit"}, indent=2)
    if not isinstance(case_sensitive, bool):
        return json.dumps({"status": "error", "error": "invalid_case_sensitive"}, indent=2)
    if not isinstance(allow_large_output, bool):
        return json.dumps({"status": "error", "error": "invalid_allow_large_output"}, indent=2)

    root = Path(repo_path).expanduser().resolve()
    engine = mcp_runtime.get_or_init_engine(root)
    if not engine or getattr(engine.state, "resync_required", False):
        return json.dumps({"status": "error", "error": "canonical_state_unavailable"}, indent=2)

    matches = []
    needle = effective_term if case_sensitive else effective_term.casefold()
    for file_path, module_name, absolute_path in canonical_python_sources(root, engine.state):
        unavailable = query_helpers.module_truth_unavailable(engine.state, module_name)
        if unavailable:
            return json.dumps(unavailable, indent=2)
        try:
            source = read_source(absolute_path)
        except SourceError as exc:
            return json.dumps(
                {"status": "error", "error": "source_unavailable", "file_path": file_path, "reason": str(exc)},
                indent=2,
            )
        lines = source.splitlines()
        resolver = SourceSpanResolver(source)
        occurrences = []
        for line_no, line in enumerate(lines, 1):
            haystack = line if case_sensitive else line.casefold()
            column = haystack.find(needle)
            while column >= 0:
                occurrences.append((line_no, column))
                column = haystack.find(needle, column + max(1, len(needle)))

        seen_spans: set[tuple[int, int, str]] = set()
        for line_no, column in occurrences:
            start, end, kind, text = resolver.resolve(line_no, column)
            identity = (start, end, kind)
            if identity in seen_spans:
                continue
            seen_spans.add(identity)
            matched = matched_line_numbers(
                lines, effective_term, start, end, case_sensitive=case_sensitive
            )
            matches.append(
                {
                    "file_path": file_path,
                    "module": module_name,
                    **shape_span(
                        source,
                        start=start,
                        end=end,
                        text=text,
                        match_kind=kind,
                        matched_lines=matched,
                        file_path=file_path,
                    ),
                }
            )

    matches.sort(key=lambda item: (item["file_path"].casefold(), item["span_start"], item["span_end"], item["match_kind"]))
    total = len(matches)
    selected = matches if limit is None else matches[:limit]
    result = {
        "status": "ok",
        "search_term": effective_term,
        "case_sensitive": case_sensitive,
        "total_matches": total,
        "matches": selected,
        "truncated": len(selected) < total,
    }
    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    return guard_large_output(
        serialized,
        allow_large_output=allow_large_output,
        requested_count=total,
        reason="Source search output exceeds the recommended context size.",
        retry_instruction=(
            "Repeat the same search_source call with the same repo_path, search_term, limit, and case_sensitive and set allow_large_output=true."
        ),
    )
