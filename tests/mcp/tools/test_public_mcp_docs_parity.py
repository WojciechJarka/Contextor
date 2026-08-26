import inspect
import json
import re
from pathlib import Path

from contextor import mcp_server
from contextor.mcp import documentation


def _get_registered_tools() -> dict:
    return mcp_server.mcp._tool_manager._tools


def _load_doc(tool_name: str) -> dict:
    doc_path = documentation.DOCS_DIR / f"{tool_name}.json"
    assert doc_path.exists(), f"Documentation file missing: {doc_path}"
    return json.loads(doc_path.read_text(encoding="utf-8"))


def _parameter_doc_line(parameters: list[str], parameter_name: str) -> str | None:
    for entry in parameters:
        normalized = entry.lstrip().replace("``", "").replace("`", "")
        if not normalized.startswith(parameter_name):
            continue
        suffix = normalized[len(parameter_name):]
        if suffix.startswith((" ", "(", ":")):
            return entry
    return None


def _normalized_parameter_doc(entry: str) -> str:
    return entry.lower().replace("``", "").replace("`", "")


def _parameter_declaration(entry: str) -> str:
    normalized = _normalized_parameter_doc(entry)
    return normalized.split(":", 1)[0].strip()


def _declares_exact_default(entry: str, default: object) -> bool:
    declaration = _parameter_declaration(entry)

    if default is None:
        return bool(
            re.search(
                r"\bdefault\s+(?:null|none)(?=\s*[),]|$)",
                declaration,
            )
        )

    if default is True:
        return bool(
            re.search(
                r"\bdefault\s+true(?=\s*[),]|$)",
                declaration,
            )
        )

    if default is False:
        return bool(
            re.search(
                r"\bdefault\s+false(?=\s*[),]|$)",
                declaration,
            )
        )

    if isinstance(default, int):
        return bool(
            re.search(
                rf"\bdefault\s+{re.escape(str(default))}(?=\s*[),]|$)",
                declaration,
            )
        )

    if isinstance(default, str):
        if default == "":
            return bool(
                re.search(
                    r"""(?:\bdefault\s+(?:""|'')(?=\s*[),]|$)|\bdefault\s+empty\s+string(?=\s*[),]|$))""",
                    declaration,
                )
            )

        expected = re.escape(default.lower())
        return bool(
            re.search(
                rf"""(?:\bdefault\s+"{expected}"(?=\s*[),]|$)|\bdefault\s+'{expected}'(?=\s*[),]|$)|\bdefault\s+{expected}(?=\s*[),]|$))""",
                declaration,
            )
        )

    return True


def test_public_mcp_docs_parity__docs_files_exactly_match_registered_tools():
    registered_names = set(_get_registered_tools().keys())
    doc_files = {p.stem for p in documentation.DOCS_DIR.glob("*.json") if p.stem != "index"}
    assert doc_files == registered_names, f"Doc files mismatch: {doc_files.symmetric_difference(registered_names)}"


def test_public_mcp_docs_parity__documentation_index_exactly_matches_registered_tools():
    registered_names = set(_get_registered_tools().keys())
    doc_index = documentation.query_documentation()
    assert "tools" in doc_index
    if isinstance(doc_index["tools"], list):
        indexed_names = {entry["tool"] for entry in doc_index["tools"]}
    else:
        indexed_names = set(doc_index["tools"].keys())
    assert indexed_names == registered_names, f"Indexed tools mismatch: {indexed_names.symmetric_difference(registered_names)}"


def test_public_mcp_docs_parity__every_runtime_parameter_and_default_is_documented():
    tools = _get_registered_tools()
    findings = []

    for tool_name, tool in tools.items():
        doc = _load_doc(tool_name)
        params_list = doc.get("parameters", [])
        sig = inspect.signature(tool.fn)

        for param_name, param in sig.parameters.items():
            entry = _parameter_doc_line(params_list, param_name)

            if entry is None:
                findings.append(
                    f"[{tool_name}] Parameter '{param_name}' has no dedicated docs entry."
                )
                continue

            normalized = _normalized_parameter_doc(entry)

            if param.default is inspect._empty:
                if "required" not in normalized:
                    findings.append(
                        f"[{tool_name}] Parameter '{param_name}' is required "
                        "in runtime but docs do not mark it required."
                    )
                continue

            if not _declares_exact_default(entry, param.default):
                findings.append(
                    f"[{tool_name}] Parameter '{param_name}' has runtime "
                    f"default {param.default!r} but docs do not declare that exact default: {entry}"
                )

    assert not findings, (
        "Global documentation parity findings:\n" + "\n".join(findings)
    )


def test_public_mcp_docs_parity__exact_default_matcher_rejects_prefix_collisions():
    assert _declares_exact_default(
        "evidence_limit (integer or null, default 3): evidence.",
        3,
    )
    assert not _declares_exact_default(
        "evidence_limit (integer or null, default 30): evidence.",
        3,
    )

    assert _declares_exact_default(
        'mode (string, default "auto"): mode.',
        "auto",
    )
    assert not _declares_exact_default(
        'mode (string, default "automatic"): mode.',
        "auto",
    )

    assert _declares_exact_default(
        "compact (boolean, default true): shaping.",
        True,
    )
    assert not _declares_exact_default(
        "compact (boolean, default trueish): shaping.",
        True,
    )

    assert _declares_exact_default(
        "fields (array or null, default null): projection.",
        None,
    )
    assert not _declares_exact_default(
        "fields (array or null, default nullable): projection.",
        None,
    )
