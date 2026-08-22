import ast
import json
from pathlib import Path
from typing import Any

from contextor.core.source import SourceError, read_source
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime

DEFAULT_AUTO_FETCH_THRESHOLD_BYTES = 5120


def _resolve_symbol_source_paths(root: Path, file_paths: list[str]) -> list[Path]:
    """Resolve explicit Python source paths while retaining repository scope."""
    resolved: list[Path] = []
    for raw_path in file_paths:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Source file '{candidate}' is outside the repository.") from exc
        if not candidate.is_file():
            raise ValueError(f"Source file '{candidate}' does not exist.")
        if candidate.suffix != ".py":
            raise ValueError(f"Source file '{candidate}' is not a Python file.")
        if candidate not in resolved:
            resolved.append(candidate)
    if not resolved:
        raise ValueError("At least one Python source file is required.")
    return resolved


def _symbol_signature(node: ast.AST) -> str:
    """Return a semantic signature without splitting a source implementation."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return f"class {node.name}" if isinstance(node, ast.ClassDef) else ""
    try:
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        arguments = ast.unparse(node.args)
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        return f"{prefix} {node.name}({arguments}){returns}"
    except Exception:
        return node.name


def _ast_symbol_candidates(path: Path, requested_symbol: str) -> list[dict]:
    """Find complete class/function/method AST nodes matching one symbol name."""
    source = read_source(path)
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines(keepends=True)
    normalized = requested_symbol.split("::", 1)[-1].strip()
    candidates: list[dict] = []

    def add_candidate(node: ast.AST, kind: str, class_stack: tuple[str, ...]) -> None:
        name = getattr(node, "name", "")
        qualified_name = ".".join((*class_stack, name)) if class_stack else name
        aliases = {qualified_name}
        if not class_stack:
            aliases.add(name)
        elif "." not in normalized:
            aliases.add(name)
        if normalized not in aliases:
            return
        start_line = min(
            [getattr(decorator, "lineno", node.lineno) for decorator in node.decorator_list]
            or [node.lineno]
        )
        end_line = getattr(node, "end_lineno", node.lineno)
        source_text = "".join(lines[start_line - 1 : end_line])
        docstring = ast.get_docstring(node, clean=False) or ""
        candidates.append(
            {
                "file_path": str(path),
                "symbol": qualified_name,
                "kind": kind,
                "node": node,
                "source": source_text,
                "source_lines": lines,
                "docstring": docstring,
                "start_line": start_line,
                "end_line": end_line,
            }
        )

    def visit_statements(statements: list[ast.stmt], class_stack: tuple[str, ...] = ()) -> None:
        for node in statements:
            if isinstance(node, ast.ClassDef):
                add_candidate(node, "class", class_stack)
                visit_statements(node.body, (*class_stack, node.name))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                add_candidate(node, "method" if class_stack else "function", class_stack)
                # Nested definitions are implementation details, not file symbols.

    visit_statements(tree.body)
    return candidates


def _module_path_for_source(root: Path, path: Path) -> str:
    """Map a repository-relative Python path to Contextor's dotted module path."""
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _symbol_static_context(root: Path, candidate: dict) -> dict:
    """Return compact current consumer evidence when a live engine is available."""
    engine = mcp_runtime.get_or_init_engine(root)
    module_path = _module_path_for_source(root, Path(candidate["file_path"]))
    context = {
        "module": module_path,
        "consumers": {"available": False, "total": 0, "truncated": False},
        "evidence_scope": "current live canonical state; static consumers only",
    }
    if not engine:
        return context
    unavailable = query_helpers.module_truth_unavailable(engine.state, module_path)
    if unavailable:
        return unavailable
    module_artifacts = getattr(engine.state, "artifacts", {}).get(module_path, {})
    raw_consumers = module_artifacts.get("consumers", {}).get(candidate["symbol"], [])
    if isinstance(raw_consumers, dict):
        raw_consumers = raw_consumers.get("consumers", [])
    if not isinstance(raw_consumers, list):
        raw_consumers = []
    context["consumers"] = {
        "available": True,
        "total": len(raw_consumers),
        "truncated": False,
    }
    return context


def _json_size(value: dict) -> dict:
    """Return the exact UTF-8 JSON payload size and a readable decimal KB value."""
    byte_count = len(json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8"))
    return {"bytes": byte_count, "kb": round(byte_count / 1000, 1)}


def _symbol_preview(root: Path, candidate: dict, member_limit: int | None) -> dict:
    """Build non-overlapping fetch plans and member costs for one AST symbol."""
    node = candidate["node"]
    resolution = {
        "symbol": candidate["symbol"],
        "file_path": candidate["file_path"],
        "kind": candidate["kind"],
        "lines": {"start": candidate["start_line"], "end": candidate["end_line"]},
    }
    signature = _symbol_signature(node)
    static_context = _symbol_static_context(root, candidate)
    base = {"status": "resolved", "resolution": resolution}
    signature_section = {**base, "signature": signature, "docstring": candidate["docstring"]}
    implementation_section = {**base, "implementation": candidate["source"]}
    full_section = {**implementation_section, "static_context": static_context}
    preview = {
        **base,
        "mode": "preview",
        "available_sections": ["signature", "docstring", "implementation", "static_context"],
        "section_sizes": {
            "signature": _json_size({"signature": signature}),
            "docstring": _json_size({"docstring": candidate["docstring"]}),
            "implementation": _json_size({"implementation": candidate["source"]}),
            "static_context": _json_size({"static_context": static_context}),
        },
        "fetch_plans": {
            "signature_and_docstring": _json_size(signature_section),
            "implementation": _json_size(implementation_section),
            "implementation_with_static_context": _json_size(full_section),
        },
        "source_contract": {
            "implementation_is_complete": True,
            "implementation_includes_docstring": bool(candidate["docstring"]),
            "no_partial_symbol_source": True,
        },
    }
    if isinstance(node, ast.ClassDef):
        members = []
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            start_line = min(
                [getattr(decorator, "lineno", child.lineno) for decorator in child.decorator_list]
                or [child.lineno]
            )
            end_line = getattr(child, "end_lineno", child.lineno)
            member_source = "".join(candidate["source_lines"][start_line - 1 : end_line])
            members.append(
                {
                    "name": child.name,
                    "kind": "method",
                    "lines": {"start": start_line, "end": end_line},
                    "implementation": _json_size({"implementation": member_source}),
                    "docstring": _json_size({"docstring": ast.get_docstring(child, clean=False) or ""}),
                }
            )
        selected, total, truncated = query_helpers.bounded_items(members, member_limit)
        preview["available_sections"].append("methods")
        preview["methods"] = {"total": total, "truncated": truncated, "items": selected}
        preview["method_selection_contract"] = (
            "Fetch a named method only through include=['methods'] and methods=[...]. "
            "Every requested method is returned as one complete AST symbol."
        )
    return preview


def get_symbol_implementation(
    repo_path: str,
    symbol: str,
    file_paths: list[str] | None = None,
    mode: str = "auto",
    include: list[str] | None = None,
    methods: list[str] | None = None,
    member_limit: int | None = 50,
    file_path: str | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return json.dumps({"status": "error", "error": f"Repository path '{root}' does not exist."}, indent=2)
    mcp_runtime.publish_live_status(root, f"MCP: reading symbol {symbol}")
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"auto", "preview", "fetch"}:
        return json.dumps(
            {"status": "error", "error": "mode must be 'auto', 'preview', or 'fetch'."},
            indent=2,
        )
    effective_file_paths = list(file_paths or [])
    if file_path and file_path not in effective_file_paths:
        effective_file_paths.append(file_path)

    try:
        candidates = []
        for path in _resolve_symbol_source_paths(root, effective_file_paths):
            candidates.extend(_ast_symbol_candidates(path, symbol))
    except (OSError, SyntaxError, UnicodeDecodeError, SourceError, ValueError) as exc:
        return json.dumps({"status": "error", "error": str(exc)}, indent=2)

    if not candidates:
        return json.dumps(
            {
                "status": "not_found",
                "symbol": symbol,
                "searched_files": effective_file_paths,
                "message": "No exact class, function, or method match was found.",
            },
            indent=2,
        )
    if len(candidates) != 1:
        return json.dumps(
            {
                "status": "ambiguous",
                "symbol": symbol,
                "candidate_count": len(candidates),
                "candidates": [
                    {
                        "symbol": item["symbol"],
                        "file_path": item["file_path"],
                        "kind": item["kind"],
                        "lines": {"start": item["start_line"], "end": item["end_line"]},
                    }
                    for item in candidates
                ],
                "message": "Narrow file_paths or use a qualified symbol; no implementation was selected.",
            },
            indent=2,
        )

    candidate = candidates[0]
    preview = _symbol_preview(root, candidate, member_limit)
    if normalized_mode == "preview":
        return json.dumps(preview, indent=2, ensure_ascii=False)

    allowed_sections = set(preview["available_sections"])
    selected_sections = (
        ["implementation"] if normalized_mode == "auto" else list(include or [])
    )
    if not selected_sections:
        return json.dumps(
            {
                "status": "selection_required",
                "message": "Fetch requires an explicit include selection. Run preview to compare costs.",
                "allowed_sections": sorted(allowed_sections),
            },
            indent=2,
        )
    unknown_sections = sorted(set(selected_sections) - allowed_sections)
    if unknown_sections:
        return json.dumps(
            {
                "status": "error",
                "error": "Unsupported include sections.",
                "unknown_sections": unknown_sections,
                "allowed_sections": sorted(allowed_sections),
            },
            indent=2,
        )
    if "implementation" in selected_sections and "methods" in selected_sections:
        return json.dumps(
            {
                "status": "error",
                "error": "implementation and methods are mutually exclusive.",
            },
            indent=2,
        )
    if "methods" in selected_sections and not methods:
        return json.dumps(
            {
                "status": "selection_required",
                "message": "Fetching methods requires explicit method names from preview.methods.items.",
            },
            indent=2,
        )

    resolution = preview["resolution"]
    result: dict[str, Any] = {
        "status": "resolved",
        "mode": "fetch",
        "resolution": resolution,
        "source_contract": preview["source_contract"],
    }
    node = candidate["node"]
    if "signature" in selected_sections:
        result["signature"] = _symbol_signature(node)
    if "docstring" in selected_sections:
        result["docstring"] = candidate["docstring"]
    if "implementation" in selected_sections:
        result["implementation"] = candidate["source"]
    if "static_context" in selected_sections:
        result["static_context"] = _symbol_static_context(root, candidate)
    if "methods" in selected_sections:
        source_lines = read_source(Path(candidate["file_path"])).splitlines(keepends=True)
        available_methods = {
            child.name: child
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        unknown_methods = sorted(set(methods or []) - set(available_methods))
        if unknown_methods:
            return json.dumps(
                {
                    "status": "error",
                    "error": "Unknown class methods.",
                    "unknown_methods": unknown_methods,
                    "available_methods": sorted(available_methods),
                },
                indent=2,
            )
        complete_methods = []
        for name in methods or []:
            child = available_methods[name]
            start_line = min(
                [getattr(decorator, "lineno", child.lineno) for decorator in child.decorator_list]
                or [child.lineno]
            )
            end_line = getattr(child, "end_lineno", child.lineno)
            complete_methods.append(
                {
                    "name": name,
                    "kind": "method",
                    "lines": {"start": start_line, "end": end_line},
                    "implementation": "".join(source_lines[start_line - 1 : end_line]),
                }
            )
        result["methods"] = complete_methods
    result["actual_response_size"] = _json_size(result)
    serialized_result = json.dumps(result, indent=2, ensure_ascii=False)

    if normalized_mode == "auto":
        response_bytes = len(serialized_result.encode("utf-8"))
        if response_bytes > DEFAULT_AUTO_FETCH_THRESHOLD_BYTES:
            preview["auto_fetch"] = {
                "threshold_bytes": DEFAULT_AUTO_FETCH_THRESHOLD_BYTES,
                "candidate_response_bytes": response_bytes,
                "decision": "preview",
                "message": (
                    "Automatic implementation fetch was not returned because the "
                    "candidate response exceeds the 5120-byte default threshold. "
                    "Use mode='fetch' with an explicit include selection to fetch it."
                ),
            }
            return json.dumps(preview, indent=2, ensure_ascii=False)

    return serialized_result
