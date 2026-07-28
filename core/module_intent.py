# -*- coding: utf-8 -*-

"""
core/module_intent.py

MODULE INTENT EXTRACTOR

Layer: FACT EXTRACTION
Extracts module intent strictly from AST and source code:
- module-level docstring
- section headers (# ==== comments)
Does not judge quality, only semantic facts.
"""

import ast
import re
from pathlib import Path


# ==========================================================
# SECTION HEADER DETECTION
# ==========================================================

_SECTION_RE = re.compile(
    r"^\s*#\s*={3,}.*?={0,}\s*$"
)


def _extract_section_comments(source: str) -> list:
    """
    Extracts section labels from comments in the style of:
        # ==========================
        # LABEL
        # ==========================

    Returns a list of unique labels in order of appearance.
    """

    labels = []
    lines = source.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        if _SECTION_RE.match(line):
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                m = re.match(r"^\s*#\s+(.*?)\s*$", next_line)
                if m:
                    label = m.group(1).strip()
                    if label and not _SECTION_RE.match(next_line):
                        labels.append(label)

        i += 1

    seen = set()
    result = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            result.append(label)

    return result


# ==========================================================
# PUBLIC API
# ==========================================================


def extract_module_intent(tree: ast.AST, source: str = "") -> dict:
    """
    Extracts module intent from AST and optionally source.

    Returns:
        {
            "docstring": str | None,
            "section_headers": list[str]
        }

    Purpose: LLM context - module map without reading code.
    """

    docstring = ast.get_docstring(tree)

    section_headers = []
    if source:
        section_headers = _extract_section_comments(source)

    return {
        "docstring": docstring,
        "section_headers": section_headers,
    }


def extract_module_intent_from_file(file_path: str) -> dict:
    """
    Convenience wrapper - reads the file and extracts intent.
    Used when we have a path, but not a parsed AST yet.
    """

    path = Path(file_path)

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return {
            "docstring": None,
            "section_headers": [],
        }

    return extract_module_intent(tree, source)
