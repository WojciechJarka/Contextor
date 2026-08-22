"""Shared source-scope and logical-span helpers for MCP retrieval tools."""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path
from typing import Any

from contextor.core.source import SourceError, read_source


FULL_SPAN_LINE_LIMIT = 20
LINE_PREVIEW_CHAR_LIMIT = 60
LINE_PREVIEW_TOKEN_LIMIT = 4


def canonical_python_sources(root: Path, state: Any) -> list[tuple[str, str, Path]]:
    """Return deterministic, repository-scoped Python files from canonical state."""
    result: list[tuple[str, str, Path]] = []
    for module_name, module in sorted((getattr(state, "modules", {}) or {}).items()):
        relative = str(getattr(module, "path", "") or "").replace("\\", "/")
        absolute_raw = str(getattr(module, "absolute_path", "") or "")
        candidate = Path(absolute_raw).expanduser() if absolute_raw else root / relative
        try:
            candidate = candidate.resolve()
            candidate.relative_to(root)
        except (OSError, ValueError):
            continue
        if candidate.suffix == ".py":
            if not relative:
                relative = candidate.relative_to(root).as_posix()
            result.append((relative, str(module_name), candidate))
    return sorted(result, key=lambda item: (item[0].casefold(), item[1].casefold()))


def read_range(path: Path, start_line: int, end_line: int) -> tuple[str, int]:
    source = read_source(path)
    lines = source.splitlines()
    total_lines = len(lines)
    if start_line < 1 or end_line < start_line or end_line > total_lines:
        raise ValueError(
            f"Requested line range {start_line}-{end_line} is outside 1-{total_lines}."
        )
    return "\n".join(lines[start_line - 1 : end_line]), total_lines


def _docstring_nodes(tree: ast.AST) -> set[ast.AST]:
    result: set[ast.AST] = set()
    for owner in ast.walk(tree):
        if not isinstance(
            owner,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue
        body = getattr(owner, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            result.add(first.value)
    return result


def _contains(node: ast.AST, line_no: int, column: int) -> bool:
    start_line = getattr(node, "lineno", None)
    end_line = getattr(node, "end_lineno", start_line)
    if start_line is None or end_line is None or not start_line <= line_no <= end_line:
        return False
    if line_no == start_line and column < getattr(node, "col_offset", 0):
        return False
    if line_no == end_line and column >= getattr(node, "end_col_offset", column + 1):
        return False
    return True


class SourceSpanResolver:
    """Resolve occurrence-aware logical spans using one tokenize/AST pass per file."""

    def __init__(self, source: str):
        self.source = source
        self.lines = source.splitlines()
        self.comment_tokens: list[tuple[int, int, int, int, int, str]] = []
        tokens: list[tokenize.TokenInfo] = []
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        except (IndentationError, tokenize.TokenError):
            pass

        comments = [token for token in tokens if token.type == tokenize.COMMENT]
        full_line = {
            token.start[0]: token
            for token in comments
            if self.lines[token.start[0] - 1].lstrip().startswith("#")
        }
        block_for_line: dict[int, tuple[int, int]] = {}
        for line_no in sorted(full_line):
            if line_no in block_for_line:
                continue
            end = line_no
            while end + 1 in full_line:
                end += 1
            for member in range(line_no, end + 1):
                block_for_line[member] = (line_no, end)

        for token in comments:
            line_no = token.start[0]
            start, end = block_for_line.get(line_no, (line_no, line_no))
            self.comment_tokens.append(
                (line_no, token.start[1], token.end[1], start, end, token.string)
            )

        try:
            self.tree: ast.AST | None = ast.parse(source)
        except (SyntaxError, ValueError, RecursionError):
            self.tree = None
        self.docstrings = _docstring_nodes(self.tree) if self.tree is not None else set()
        nodes = list(ast.walk(self.tree)) if self.tree is not None else []
        self.strings = [
            node for node in nodes
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        self.statements = [node for node in nodes if isinstance(node, ast.stmt)]

    def resolve(self, line_no: int, column: int) -> tuple[int, int, str, str]:
        for token_line, start_col, end_col, start, end, token_text in self.comment_tokens:
            if token_line == line_no and start_col <= column < end_col:
                text = (
                    "\n".join(self.lines[start - 1 : end])
                    if start != end or self.lines[line_no - 1].lstrip().startswith("#")
                    else token_text
                )
                return start, end, "comment", text

        if self.tree is None:
            return line_no, line_no, "line", self.lines[line_no - 1]

        strings = [node for node in self.strings if _contains(node, line_no, column)]
        if strings:
            node = min(
                strings,
                key=lambda item: (item.end_lineno - item.lineno, item.col_offset),
            )
            if node in self.docstrings or node.end_lineno > node.lineno:
                kind = "docstring" if node in self.docstrings else "multiline_string"
                return (
                    node.lineno,
                    node.end_lineno,
                    kind,
                    "\n".join(self.lines[node.lineno - 1 : node.end_lineno]),
                )

        statements = [node for node in self.statements if _contains(node, line_no, column)]
        if statements:
            node = min(
                statements,
                key=lambda item: (item.end_lineno - item.lineno, item.col_offset),
            )
            return (
                node.lineno,
                node.end_lineno,
                "statement",
                "\n".join(self.lines[node.lineno - 1 : node.end_lineno]),
            )
        return line_no, line_no, "line", self.lines[line_no - 1]


def matched_line_numbers(
    lines: list[str], term: str, start: int, end: int, *, case_sensitive: bool
) -> list[int]:
    needle = term if case_sensitive else term.casefold()
    result = []
    for line_no in range(start, end + 1):
        value = lines[line_no - 1]
        haystack = value if case_sensitive else value.casefold()
        if needle in haystack:
            result.append(line_no)
    return result


def line_preview(line: str) -> str:
    indent = line[: len(line) - len(line.lstrip())][:8]
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|[^\w\s]", line.lstrip())
    preview = indent + " ".join(tokens[:LINE_PREVIEW_TOKEN_LIMIT])
    return preview[:LINE_PREVIEW_CHAR_LIMIT]


def shape_span(
    source: str,
    *,
    start: int,
    end: int,
    text: str,
    match_kind: str,
    matched_lines: list[int],
    file_path: str,
) -> dict[str, Any]:
    total_lines = end - start + 1
    base: dict[str, Any] = {
        "span_start": start,
        "span_end": end,
        "total_lines": total_lines,
        "match_kind": match_kind,
        "matched_lines": matched_lines,
    }
    if total_lines <= FULL_SPAN_LINE_LIMIT:
        return {**base, "content_mode": "full", "text": text}

    source_lines = source.splitlines()
    line_map = []
    matched = set(matched_lines)
    for line_no in range(start, end + 1):
        full_line = source_lines[line_no - 1]
        if line_no in matched:
            line_map.append({"line": line_no, "text": full_line, "matched": True})
        else:
            line_map.append({"line": line_no, "preview": line_preview(full_line), "matched": False})
    return {
        **base,
        "content_mode": "line_map",
        "lines": line_map,
        "collapsed": True,
        "expand": {
            "tool": "get_source_range",
            "file_path": file_path,
            "start_line": start,
            "end_line": end,
        },
    }


__all__ = [
    "SourceError",
    "canonical_python_sources",
    "SourceSpanResolver",
    "matched_line_numbers",
    "read_range",
    "shape_span",
]
