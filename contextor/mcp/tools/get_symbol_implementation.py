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
    engine = mcp_runtime.get_or_init_engine(root)
    module_path = _module_path_for_source(root, Path(candidate["file_path"]))
    state_freshness = query_helpers.build_state_freshness(
        root, engine.state if engine else None, target_file=candidate["file_path"], target_module=module_path, engine=engine
    )
    base = {
        "status": "resolved",
        "resolution": resolution,
        "state_freshness": state_freshness,
    }

    # BLOCKER 4 — fail closed: if the source file on disk is out of sync with the
    # canonical state that produced the T0 line locations, returning source would
    # risk delivering a stale/misaligned fragment. Surface this as a first-class
    # stale status instead. metadata_match (no sha256) is treated conservatively.
    # Furthermore, explicit generation mismatch between canonical state and FileState
    # must fail closed to prevent serving misaligned AST slices.
    explicit_mismatch = query_helpers.is_explicit_generation_mismatch(
        root, engine.state if engine else None, engine=engine
    )
    source_unreliable = (
        state_freshness.get("workspace_sync") in {"out_of_sync", "metadata_match"}
        or explicit_mismatch
    )
    if source_unreliable:
        stale_reason = (
            "Source file on disk has diverged from canonical generation / state. "
            "Re-run analyze_project or update_file to refresh canonical state before fetching implementation."
            if explicit_mismatch
            else "Source file on disk has diverged from canonical T0 state. "
            "Re-run analyze_project or update_file to refresh canonical state before fetching implementation."
        )
        return {
            **base,
            "status": "stale_source",
            "mode": "preview",
            "stale_reason": stale_reason,
            "source_contract": {
                "implementation_is_complete": False,
                "implementation_includes_docstring": False,
                "no_partial_symbol_source": False,
            },
        }

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
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"auto", "preview", "fetch"}:
        return json.dumps(
            {"status": "error", "error": "mode must be 'auto', 'preview', or 'fetch'."},
            indent=2,
        )
    effective_file_paths = list(file_paths or [])
    if file_path and file_path not in effective_file_paths:
        effective_file_paths.append(file_path)

    from contextor.core.report_query import normalize_module_path_to_dotted

    raw_symbol = symbol.strip()
    is_id = query_helpers.is_artifact_id(raw_symbol)
    is_qualified = "::" in raw_symbol

    _registries: tuple[dict, dict, dict, dict] | None = None

    def _get_registries() -> tuple[dict, dict, dict, dict]:
        nonlocal _registries
        if _registries is None:
            _registries = query_helpers.read_registries(root)
        return _registries

    target_symbol = raw_symbol
    search_paths: list[Path] = []
    canonical_artifact: str | None = None

    if is_id:
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _get_registries()
        identity = query_helpers.resolve_artifact_identity(raw_symbol, art_path_to_id, art_id_to_path)
        if identity["status"] == "resolved" and identity.get("resolution") == "exact_id":
            canonical_artifact = identity["artifact"]
            definer_mod, target_symbol = canonical_artifact.split("::", 1)
            if effective_file_paths:
                try:
                    explicit_paths = _resolve_symbol_source_paths(root, effective_file_paths)
                except ValueError as exc:
                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
                explicit_modules = {
                    normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root))
                    for p in explicit_paths
                }
                if definer_mod not in explicit_modules:
                    return json.dumps(
                        {
                            "status": "not_found",
                            "symbol": symbol,
                            "searched_files": effective_file_paths,
                            "message": "Resolved artifact is outside the requested file constraints.",
                            "resolved_artifact": canonical_artifact,
                            "artifact_id": identity["artifact_id"],
                            "definer_module": definer_mod,
                        },
                        indent=2,
                    )
                search_paths = [
                    p for p in explicit_paths
                    if normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root)) == definer_mod
                ] or explicit_paths
            else:
                engine = mcp_runtime.get_or_init_engine(root)
                if not engine or getattr(engine.state, "resync_required", False):
                    return json.dumps({"status": "error", "error": "Error: No usable canonical LIVE state. Run analyze_project first."}, indent=2)
                state = engine.state
                unavailable = query_helpers.module_truth_unavailable(state, definer_mod)
                if unavailable:
                    return json.dumps(unavailable, indent=2)
                module_obj = getattr(state, "modules", {}).get(definer_mod)
                canonical_rel_path = getattr(module_obj, "path", None)
                if not canonical_rel_path:
                    return json.dumps({"status": "error", "error": f"Cannot determine canonical source path for module '{definer_mod}'."}, indent=2)
                try:
                    search_paths = _resolve_symbol_source_paths(root, [canonical_rel_path])
                except ValueError as exc:
                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
        elif identity["status"] == "not_found" and identity.get("query_kind") == "artifact_id":
            return json.dumps(
                {
                    "status": "not_found",
                    "symbol": symbol,
                    "message": f"Artifact '{symbol}' not found in the active registry.",
                },
                indent=2,
            )
        else:
            return json.dumps(
                {
                    "status": "not_found",
                    "symbol": symbol,
                    "message": f"Artifact '{symbol}' not found in the active registry.",
                },
                indent=2,
            )
    elif is_qualified:
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _get_registries()
        identity = query_helpers.resolve_artifact_identity(raw_symbol, art_path_to_id, art_id_to_path)
        if identity["status"] == "resolved" and identity.get("resolution") == "exact_identity":
            canonical_artifact = identity["artifact"]
            definer_mod, target_symbol = canonical_artifact.split("::", 1)
            if effective_file_paths:
                try:
                    explicit_paths = _resolve_symbol_source_paths(root, effective_file_paths)
                except ValueError as exc:
                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
                explicit_modules = {
                    normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root))
                    for p in explicit_paths
                }
                if definer_mod not in explicit_modules:
                    return json.dumps(
                        {
                            "status": "not_found",
                            "symbol": symbol,
                            "searched_files": effective_file_paths,
                            "message": "Resolved artifact is outside the requested file constraints.",
                            "resolved_artifact": canonical_artifact,
                            "artifact_id": identity["artifact_id"],
                            "definer_module": definer_mod,
                        },
                        indent=2,
                    )
                search_paths = [
                    p for p in explicit_paths
                    if normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root)) == definer_mod
                ] or explicit_paths
            else:
                engine = mcp_runtime.get_or_init_engine(root)
                if not engine or getattr(engine.state, "resync_required", False):
                    return json.dumps({"status": "error", "error": "Error: No usable canonical LIVE state. Run analyze_project first."}, indent=2)
                state = engine.state
                unavailable = query_helpers.module_truth_unavailable(state, definer_mod)
                if unavailable:
                    return json.dumps(unavailable, indent=2)
                module_obj = getattr(state, "modules", {}).get(definer_mod)
                canonical_rel_path = getattr(module_obj, "path", None)
                if not canonical_rel_path:
                    return json.dumps({"status": "error", "error": f"Cannot determine canonical source path for module '{definer_mod}'."}, indent=2)
                try:
                    search_paths = _resolve_symbol_source_paths(root, [canonical_rel_path])
                except ValueError as exc:
                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
        else:
            if effective_file_paths:
                try:
                    explicit_paths = _resolve_symbol_source_paths(root, effective_file_paths)
                except ValueError as exc:
                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
                explicit_modules = {
                    normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root))
                    for p in explicit_paths
                }
                scoped_art_path_to_id = {
                    k: v for k, v in art_path_to_id.items()
                    if k.split("::", 1)[0] in explicit_modules
                }
                scoped_art_id_to_path = {v: k for k, v in scoped_art_path_to_id.items()}
                fuzzy_identity = query_helpers.resolve_artifact_identity(
                    raw_symbol, scoped_art_path_to_id, scoped_art_id_to_path
                )
                if fuzzy_identity.get("similar_candidates"):
                    return json.dumps(
                        {
                            "status": "not_found",
                            "symbol": symbol,
                            "searched_files": effective_file_paths,
                            "similar_candidates": fuzzy_identity["similar_candidates"],
                            "data_source": "active_artifact_registry",
                        },
                        indent=2,
                    )
                return json.dumps(
                    {
                        "status": "not_found",
                        "symbol": symbol,
                        "searched_files": effective_file_paths,
                        "message": "No exact class, function, or method match was found.",
                    },
                    indent=2,
                )
            else:
                if identity.get("similar_candidates"):
                    return json.dumps(
                        {
                            "status": "not_found",
                            "symbol": symbol,
                            "similar_candidates": identity["similar_candidates"],
                            "data_source": "active_artifact_registry",
                        },
                        indent=2,
                    )
                return json.dumps(
                    {
                        "status": "not_found",
                        "symbol": symbol,
                        "message": "No exact class, function, or method match was found.",
                    },
                    indent=2,
                )
    else:
        if effective_file_paths:
            try:
                search_paths = _resolve_symbol_source_paths(root, effective_file_paths)
            except ValueError as exc:
                return json.dumps({"status": "error", "error": str(exc)}, indent=2)
        else:
            mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _get_registries()
            identity = query_helpers.resolve_artifact_identity(raw_symbol, art_path_to_id, art_id_to_path)
            if identity["status"] == "resolved" and identity.get("resolution") in ("exact_leaf", "exact_identity", "exact_id"):
                canonical_artifact = identity["artifact"]
                definer_mod, target_symbol = canonical_artifact.split("::", 1)
                engine = mcp_runtime.get_or_init_engine(root)
                if not engine or getattr(engine.state, "resync_required", False):
                    return json.dumps({"status": "error", "error": "Error: No usable canonical LIVE state. Run analyze_project first."}, indent=2)
                state = engine.state
                unavailable = query_helpers.module_truth_unavailable(state, definer_mod)
                if unavailable:
                    return json.dumps(unavailable, indent=2)
                module_obj = getattr(state, "modules", {}).get(definer_mod)
                canonical_rel_path = getattr(module_obj, "path", None)
                if not canonical_rel_path:
                    return json.dumps({"status": "error", "error": f"Cannot determine canonical source path for module '{definer_mod}'."}, indent=2)
                try:
                    search_paths = _resolve_symbol_source_paths(root, [canonical_rel_path])
                except ValueError as exc:
                    return json.dumps({"status": "error", "error": str(exc)}, indent=2)
            elif identity["status"] == "ambiguous":
                return json.dumps(
                    {
                        "status": "ambiguous",
                        "symbol": symbol,
                        "candidate_count": len(identity.get("candidates", [])),
                        "candidates": identity.get("candidates", []),
                        "message": "Symbol is ambiguous across multiple modules; specify file_path or use a qualified module::symbol.",
                    },
                    indent=2,
                )
            else:
                if identity.get("similar_candidates"):
                    return json.dumps(
                        {
                            "status": "not_found",
                            "symbol": symbol,
                            "similar_candidates": identity["similar_candidates"],
                            "data_source": "active_artifact_registry",
                        },
                        indent=2,
                    )
                return json.dumps(
                    {
                        "status": "not_found",
                        "symbol": symbol,
                        "message": "No exact class, function, or method match was found.",
                    },
                    indent=2,
                )


    try:
        candidates = []
        for path in search_paths:
            candidates.extend(_ast_symbol_candidates(path, target_symbol))
    except (OSError, SyntaxError, UnicodeDecodeError, SourceError, ValueError) as exc:
        return json.dumps({"status": "error", "error": str(exc)}, indent=2)

    if not candidates:
        if effective_file_paths:
            try:
                explicit_paths = _resolve_symbol_source_paths(root, effective_file_paths)
            except ValueError:
                explicit_paths = search_paths
            explicit_modules = {
                normalize_module_path_to_dotted(str(p.relative_to(root)), repo_root=str(root))
                for p in explicit_paths
            }
            _, _, art_path_to_id, _ = _get_registries()
            scoped_art_path_to_id = {
                k: v for k, v in art_path_to_id.items()
                if k.split("::", 1)[0] in explicit_modules
            }
            scoped_art_id_to_path = {v: k for k, v in scoped_art_path_to_id.items()}
            fuzzy_identity = query_helpers.resolve_artifact_identity(
                raw_symbol, scoped_art_path_to_id, scoped_art_id_to_path
            )
            if fuzzy_identity.get("similar_candidates"):
                return json.dumps(
                    {
                        "status": "not_found",
                        "symbol": symbol,
                        "searched_files": effective_file_paths,
                        "similar_candidates": fuzzy_identity["similar_candidates"],
                        "data_source": "active_artifact_registry",
                    },
                    indent=2,
                )
            return json.dumps(
                {
                    "status": "not_found",
                    "symbol": symbol,
                    "searched_files": effective_file_paths,
                    "message": "No exact class, function, or method match was found.",
                },
                indent=2,
            )
        else:
            return json.dumps(
                {
                    "status": "not_found",
                    "symbol": symbol,
                    "searched_files": [str(p.relative_to(root)) if p.is_relative_to(root) else str(p) for p in search_paths],
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

    if preview.get("status") == "stale_source":
        return json.dumps(
            {
                "status": "stale_source",
                "mode": normalized_mode,
                "resolution": preview["resolution"],
                "state_freshness": preview["state_freshness"],
                "stale_reason": preview.get("stale_reason"),
                "source_contract": preview["source_contract"],
            },
            indent=2,
        )

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
    state_freshness = preview["state_freshness"]

    result: dict[str, Any] = {
        "status": "resolved",
        "mode": "fetch",
        "resolution": resolution,
        "state_freshness": state_freshness,
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
