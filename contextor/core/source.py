"""Reading and parsing Python source files with CPython-compatible encodings."""

import ast
import hashlib
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ParsedSourceInput",
    "SourceError",
    "parse_source",
    "parse_source_with_fingerprint",
    "read_source",
]


class SourceError(ValueError):
    """A path is not readable or parsable Python, with structured failure data."""

    def __init__(self, message: str, *, error_status: str = "ERROR", line_number: int | None = None, column_number: int | None = None, detail_message: str | None = None) -> None:
        super().__init__(message)
        self.error_status = error_status
        self.line_number = line_number
        self.column_number = column_number
        self.detail_message = detail_message if detail_message is not None else message


@dataclass(frozen=True)
class ParsedSourceInput:
    tree: ast.AST
    source_fingerprint: str


def read_source(path: str | Path) -> str:
    """Read Python source using the encoding rules used by CPython."""
    try:
        with tokenize.open(str(path)) as handle:
            return handle.read()
    except UnicodeDecodeError:
        raise SourceError("not valid text in its declared encoding") from None
    except SyntaxError:
        raise SourceError("is not text in any declared encoding") from None
    except OSError as exc:
        raise SourceError(f"could not be read ({exc.strerror or exc})") from None


def _read_source_snapshot(path: str | Path) -> tuple[bytes, str]:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise SourceError(f"could not be read ({exc.strerror or exc})") from None
    return raw, hashlib.sha256(raw).hexdigest()


def _decode_source_snapshot(raw: bytes) -> str:
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
    except SyntaxError:
        raise SourceError("is not text in any declared encoding") from None
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        raise SourceError("not valid text in its declared encoding") from None


def parse_source_with_fingerprint(path: str | Path) -> ParsedSourceInput:
    """Parse and SHA-256 fingerprint one exact byte snapshot of a Python file."""
    raw, fingerprint = _read_source_snapshot(path)
    source = _decode_source_snapshot(raw)
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        location = f"line {exc.lineno}"
        if exc.offset is not None:
            location += f", column {exc.offset}"
        raise SourceError(f"is not valid Python ({location}: {exc.msg})", error_status="SYNTAX_ERROR", line_number=exc.lineno, column_number=exc.offset, detail_message=exc.msg) from None
    except ValueError as exc:
        raise SourceError(f"is not valid Python ({exc})", error_status="SYNTAX_ERROR", detail_message=str(exc)) from None
    except RecursionError:
        raise SourceError("is too deeply nested to parse", error_status="SYNTAX_ERROR", detail_message="is too deeply nested to parse") from None
    return ParsedSourceInput(tree=tree, source_fingerprint=fingerprint)


def parse_source(path: str | Path) -> ast.AST:
    """Backward-compatible AST-only wrapper."""
    return parse_source_with_fingerprint(path).tree
