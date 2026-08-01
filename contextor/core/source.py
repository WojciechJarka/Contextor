"""
contextor/core/source.py

Reading and parsing Python source files.

Single entry point for turning a path into text or an AST, because the
encoding rules are not obvious and were previously reimplemented per
call site with `read_text(encoding="utf-8")`. That rejected two kinds of
perfectly valid Python:

- files beginning with a UTF-8 BOM, which CPython accepts;
- files declaring another encoding via a PEP 263 header
  (`# -*- coding: cp1250 -*-`), which CPython honours.

`tokenize.open()` applies exactly CPython's own rules, so what Contextor
considers readable Python matches what Python considers readable Python.
"""

import ast
import tokenize
from pathlib import Path

__all__ = [
    "SourceError",
    "parse_source",
    "read_source",
]


class SourceError(ValueError):
    """
    A path is not readable or parsable Python, with a printable reason.
    """


def read_source(path: str | Path) -> str:
    """
    Reads a Python source file using the encoding Python itself would.

    Raises:
        SourceError: the file cannot be read or decoded.
    """

    try:
        with tokenize.open(str(path)) as handle:
            return handle.read()

    except UnicodeDecodeError:
        raise SourceError("not valid text in its declared encoding") from None

    except SyntaxError:
        # tokenize.open raises this when the bytes cannot be decoded and
        # carry no usable PEP 263 header - in practice, binary content.
        # Its message embeds the absolute path, which the caller already
        # reports separately.
        raise SourceError("is not text in any declared encoding") from None

    except OSError as exc:
        raise SourceError(f"could not be read ({exc.strerror or exc})") from None


def parse_source(path: str | Path) -> ast.AST:
    """
    Reads and parses a Python source file.

    Raises:
        SourceError: the file cannot be read, decoded or parsed.
    """

    source = read_source(path)

    try:
        return ast.parse(source)

    except SyntaxError as exc:
        raise SourceError(f"is not valid Python (line {exc.lineno}: {exc.msg})") from None

    except ValueError as exc:
        # ast.parse rejects sources containing null bytes.
        raise SourceError(f"is not valid Python ({exc})") from None

    except RecursionError:
        raise SourceError("is too deeply nested to parse") from None
