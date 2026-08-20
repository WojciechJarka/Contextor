"""Validated, lazy access to MCP tool documentation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DOCS_DIR = Path(__file__).with_name("docs")
INDEX_PATH = DOCS_DIR / "index.json"
DOCUMENTATION_TOOL_NAME = "get_mcp_documentation"
DOCUMENTATION_SECTIONS = (
    "purpose",
    "parameters",
    "behavior",
    "freshness",
    "errors",
    "usage_notes",
    "examples",
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate documentation key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"Documentation JSON must contain an object: {path.name}")
    return payload


def load_documentation_index() -> dict[str, Any]:
    """Load only the small discovery index."""
    payload = _read_json(INDEX_PATH)
    version = payload.get("version")
    entries = payload.get("tools")
    if not isinstance(version, str) or not version:
        raise ValueError("Documentation version must be a non-empty string.")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Documentation index must contain tools.")

    names: set[str] = set()
    filenames: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "tool",
            "filename",
            "short_description",
        }:
            raise ValueError("Invalid documentation index entry.")
        name = entry["tool"]
        filename = entry["filename"]
        description = entry["short_description"]
        if not all(isinstance(item, str) and item for item in (name, filename, description)):
            raise ValueError("Documentation index values must be non-empty strings.")
        if name in names or filename in filenames:
            raise ValueError("Duplicate tool or filename in documentation index.")
        if filename != f"{name}.json" or Path(filename).name != filename:
            raise ValueError(f"Invalid documentation filename for tool: {name}")
        names.add(name)
        filenames.add(filename)
    return payload


def _index_entries() -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    index = load_documentation_index()
    entries = {entry["tool"]: entry for entry in index["tools"]}
    return index, entries


def short_description(tool_name: str) -> str:
    """Return one discovery description without loading a full tool document."""
    _, entries = _index_entries()
    try:
        return entries[tool_name]["short_description"]
    except KeyError as exc:
        raise ValueError(f"Unknown documented MCP tool: {tool_name}") from exc


def load_tool_document(tool_name: str) -> dict[str, Any]:
    """Load and validate exactly one requested tool document."""
    index, entries = _index_entries()
    entry = entries.get(tool_name)
    if entry is None:
        raise ValueError(f"Unknown documented MCP tool: {tool_name}")
    payload = _read_json(DOCS_DIR / entry["filename"])
    expected = {"version", "tool", *DOCUMENTATION_SECTIONS}
    if set(payload) != expected:
        raise ValueError(f"Invalid documentation sections for tool: {tool_name}")
    if payload["version"] != index["version"] or payload["tool"] != tool_name:
        raise ValueError(f"Documentation identity mismatch for tool: {tool_name}")
    for section in DOCUMENTATION_SECTIONS:
        value = payload[section]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"Documentation section must be a list: {tool_name}.{section}")
    return payload


def validate_documentation_catalog() -> dict[str, Any]:
    """Validate exact index/file coverage; intended for startup tests and audits."""
    index, entries = _index_entries()
    expected_files = {entry["filename"] for entry in entries.values()}
    actual_files = {
        path.name for path in DOCS_DIR.glob("*.json") if path.name != INDEX_PATH.name
    }
    if actual_files != expected_files:
        raise ValueError("Documentation index and per-tool files do not have exact coverage.")
    for name in entries:
        load_tool_document(name)
    return index


def query_documentation(
    tool: str | None = None,
    tools: list[str] | None = None,
    sections: list[str] | None = None,
) -> dict[str, Any]:
    """Return the index or lazily load only explicitly selected documents."""
    index, entries = _index_entries()
    ordered_names = [entry["tool"] for entry in index["tools"]]
    if tool is not None and tools is not None:
        return {
            "status": "invalid_documentation_query",
            "reason": "Use either tool or tools, not both.",
        }

    selected = [tool] if tool is not None else tools
    if selected is None:
        if sections is not None:
            return {
                "status": "tool_selection_required",
                "reason": "Sections require an explicit tool or tools selection.",
            }
        return {
            "version": index["version"],
            "tools": [
                {
                    "tool": entry["tool"],
                    "short_description": entry["short_description"],
                }
                for entry in index["tools"]
            ],
        }

    unknown_tools = sorted(set(selected) - set(entries))
    unknown_sections = sorted(set(sections or ()) - set(DOCUMENTATION_SECTIONS))
    if unknown_tools or unknown_sections:
        return {
            "status": "invalid_documentation_query",
            "unknown_tools": unknown_tools,
            "unknown_sections": unknown_sections,
            "available_tools": ordered_names,
            "available_sections": list(DOCUMENTATION_SECTIONS),
        }

    selected_names = [name for name in ordered_names if name in set(selected)]
    selected_sections = list(DOCUMENTATION_SECTIONS) if sections is None else [
        section for section in DOCUMENTATION_SECTIONS if section in set(sections)
    ]
    documents: dict[str, Any] = {}
    for name in selected_names:
        document = load_tool_document(name)
        documents[name] = {
            section: document[section] for section in selected_sections
        }
    return {"version": index["version"], "tools": documents}
