"""Index-first selection of complete artifact blocks from compact reports."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


MODULE_ID_RE = re.compile(r"^\d+/\d+$")
ARTIFACT_ID_RE = re.compile(r"^A\d+/\d+$", re.IGNORECASE)
QUERY_PREFIXES = {"id", "file", "module", "symbol", "artifact"}


def is_public_artifact_name(full_name: str) -> bool:
    """Apply Python naming visibility without inferring it from consumer counts."""

    local_name = str(full_name).split("::", 1)[-1].split("(", 1)[0]
    leaf = local_name.rsplit(".", 1)[-1]
    return not leaf.startswith("_") or (leaf.startswith("__") and leaf.endswith("__"))


def filter_public_artifact_report(
    report: Mapping[str, Any], catalog: "IndexCatalog"
) -> dict:
    """Return a shallow report view containing only naming-public artifact blocks."""

    artifacts = report.get("artifacts", {})
    if not isinstance(artifacts, Mapping):
        raise ValueError("Indexed report must contain an 'artifacts' object.")
    filtered = {
        str(artifact_id): block
        for artifact_id, block in artifacts.items()
        if is_public_artifact_name(
            catalog.artifacts.get(str(artifact_id))
            or (catalog.recovered_artifacts or {}).get(str(artifact_id))
            or "_unresolved"
        )
    }
    return {**report, "artifacts": filtered}


@dataclass(frozen=True)
class IndexCatalog:
    """Active/recovery identities plus optional authoritative module paths."""

    modules: Mapping[str, str]
    artifacts: Mapping[str, str]
    module_paths: Mapping[str, str] | None = None
    recovered_modules: Mapping[str, str] | None = None
    recovered_artifacts: Mapping[str, str] | None = None


def catalog_from_registry(
    repo_path: str,
    module_paths: Mapping[str, str] | None = None,
) -> IndexCatalog:
    """Snapshot the repository-keyed persistent registry for GUI or MCP use."""

    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    registry = PersistentIdentityRegistry(repo_path)
    with registry.transaction():
        state = registry._state
        modules = dict(state.get("module_registry", {}).get("id_to_path", {}))
        artifacts = dict(state.get("artifact_registry", {}).get("id_to_path", {}))
        recovered_modules = {
            str(obj_id): entry.get("path")
            for obj_id, entry in state.get("module_recovery", {}).items()
            if isinstance(entry, dict) and entry.get("path")
        }
        recovered_artifacts = {
            str(obj_id): entry.get("name")
            for obj_id, entry in state.get("artifact_recovery", {}).items()
            if isinstance(entry, dict) and entry.get("name")
        }
    active_modules = {str(key): value for key, value in modules.items() if value}
    resolved_module_paths = (
        dict(module_paths)
        if module_paths is not None
        else discover_module_paths(repo_path, active_modules.values())
    )
    return IndexCatalog(
        modules=active_modules,
        artifacts={str(key): value for key, value in artifacts.items() if value},
        module_paths=resolved_module_paths,
        recovered_modules=recovered_modules,
        recovered_artifacts=recovered_artifacts,
    )


def discover_module_paths(repo_path: str, module_names: Any) -> dict[str, str]:
    """Map indexed dotted modules to real Python paths without parsing source files."""

    root = Path(repo_path).expanduser().resolve()
    ignored_parts = {".git", ".contextor", ".venv", "venv", "output", "__pycache__"}
    python_paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if not ignored_parts.intersection(path.relative_to(root).parts)
    )
    result: dict[str, str] = {}
    for raw_name in module_names:
        module_name = str(raw_name)
        dotted_parts = module_name.split(".")
        if dotted_parts[-1:] == ["__init__"]:
            direct_targets = ["/".join(dotted_parts) + ".py"]
        else:
            stem = "/".join(dotted_parts)
            direct_targets = [stem + ".py", stem + "/__init__.py"]
        ranked: list[tuple[int, str]] = []
        for path in python_paths:
            for target_index, target in enumerate(direct_targets):
                if path == target:
                    ranked.append((100 - target_index, path))
                elif path.endswith("/" + target):
                    ranked.append((90 - target_index, path))
        if not ranked:
            continue
        best_score = max(score for score, _ in ranked)
        best_paths = sorted({path for score, path in ranked if score == best_score})
        if len(best_paths) == 1:
            result[module_name] = best_paths[0]
    return result


def _split_explicit_prefix(query: str) -> tuple[str | None, str]:
    prefix, separator, value = query.partition(":")
    if separator and prefix.lower() in QUERY_PREFIXES:
        return prefix.lower(), value.strip()
    return None, query


def _classify_query(query: str) -> tuple[str, str]:
    explicit, value = _split_explicit_prefix(query.strip())
    if explicit == "id":
        if ARTIFACT_ID_RE.fullmatch(value):
            return "artifact_id", value.upper()
        if MODULE_ID_RE.fullmatch(value):
            return "module_id", value
        return "invalid_id", value
    if explicit == "file":
        return "file", value
    if explicit == "module":
        return "module", value
    if explicit == "symbol":
        return "symbol", value
    if explicit == "artifact":
        return "artifact", value
    if ARTIFACT_ID_RE.fullmatch(value):
        return "artifact_id", value.upper()
    if MODULE_ID_RE.fullmatch(value):
        return "module_id", value
    if "::" in value:
        return "artifact", value
    if value.lower().endswith(".py"):
        return "file", value
    return "symbol", value


def _derived_module_path(module_name: str) -> str:
    return module_name.replace(".", "/") + ".py"


def _normalize_relative_path(value: str, repo_root: str | None) -> tuple[str | None, str | None]:
    raw = value.strip().replace("\\", "/")
    if not raw:
        return None, "empty_query"
    path = Path(raw).expanduser()
    if path.is_absolute():
        if not repo_root:
            return None, "absolute_path_requires_repo_root"
        root = Path(repo_root).expanduser().resolve()
        try:
            raw = path.resolve().relative_to(root).as_posix()
        except ValueError:
            return None, "path_outside_repository"
    else:
        while raw.startswith("./"):
            raw = raw[2:]
    normalized = str(PurePosixPath(raw))
    if normalized == "." or ".." in PurePosixPath(normalized).parts:
        return None, "path_outside_repository"
    return normalized, None


def _candidate(
    obj_id: str,
    name: str,
    kind: str,
    match_kind: str,
    score: int,
    report_ids: set[str] | None,
    **extra: Any,
) -> dict:
    result = {
        "id": str(obj_id),
        "name": name,
        "kind": kind,
        "match_kind": match_kind,
        "score": score,
        "in_report": None if report_ids is None else str(obj_id) in report_ids,
    }
    result.update(extra)
    return result


def _best_tier(candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []
    best = max(item["score"] for item in candidates)
    return sorted(
        (item for item in candidates if item["score"] == best),
        key=lambda item: (item["name"].casefold(), item["id"]),
    )


def _suggestion_match(value: str, target: str) -> tuple[str, int] | None:
    """Suggest only segment prefixes; never match the middle of an unrelated word."""

    folded_value = value.casefold()
    if not folded_value:
        return None
    segments = [
        segment
        for segment in re.split(r"::|[._/\\]+", target.casefold())
        if segment
    ]
    if any(segment.startswith(folded_value) for segment in segments):
        return "segment_prefix_suggestion", 60
    return None


def resolve_index_query(
    query: str,
    catalog: IndexCatalog,
    report_artifact_ids: set[str] | None = None,
    report_module_ids: set[str] | None = None,
    repo_root: str | None = None,
) -> dict:
    """Resolve a user query to active index IDs without silent fuzzy selection."""

    artifact_report_ids = (
        None
        if report_artifact_ids is None
        else {str(value) for value in report_artifact_ids}
    )
    module_report_ids = (
        None if report_module_ids is None else {str(value) for value in report_module_ids}
    )
    if not isinstance(query, str) or not query.strip():
        return {
            "status": "invalid",
            "query": query,
            "query_kind": None,
            "reason": "empty_query",
            "matches": [],
            "suggestions": [],
        }

    query_kind, value = _classify_query(query)
    if query_kind == "invalid_id":
        return {
            "status": "invalid",
            "query": query,
            "query_kind": query_kind,
            "reason": "invalid_id",
            "matches": [],
            "suggestions": [],
        }

    recovered_modules = dict(catalog.recovered_modules or {})
    recovered_artifacts = dict(catalog.recovered_artifacts or {})

    if query_kind in {"module_id", "artifact_id"}:
        active = catalog.modules if query_kind == "module_id" else catalog.artifacts
        recovered = recovered_modules if query_kind == "module_id" else recovered_artifacts
        kind = "module" if query_kind == "module_id" else "artifact"
        if value in active:
            report_ids = module_report_ids if kind == "module" else artifact_report_ids
            match = _candidate(value, active[value], kind, "exact_id", 100, report_ids, index_source="active")
            return _resolution(query, query_kind, [match], [])
        if value in recovered:
            report_ids = module_report_ids if kind == "module" else artifact_report_ids
            stale = _candidate(value, recovered[value], kind, "recovery_id", 100, report_ids, index_source="recovery")
            if stale["in_report"]:
                return _resolution(query, query_kind, [stale], [])
            return {**_resolution(query, query_kind, [], []), "status": "stale_recovery_entry", "recovery_matches": [stale]}
        return _resolution(query, query_kind, [], [])

    candidates: list[dict] = []
    suggestions: list[dict] = []

    if query_kind in {"file", "module"}:
        if query_kind == "file":
            normalized, error = _normalize_relative_path(value, repo_root)
            if error:
                return {
                    "status": "invalid",
                    "query": query,
                    "query_kind": query_kind,
                    "reason": error,
                    "matches": [],
                    "suggestions": [],
                }
        else:
            normalized = value.strip()

        indexed_modules = [
            (module_id, module_name, "active")
            for module_id, module_name in catalog.modules.items()
        ] + [
            (module_id, module_name, "recovery")
            for module_id, module_name in recovered_modules.items()
            if module_id not in catalog.modules
        ]
        for module_id, module_name, index_source in indexed_modules:
            module_path = (catalog.module_paths or {}).get(module_name) or _derived_module_path(module_name)
            module_path = module_path.replace("\\", "/")
            if query_kind == "module":
                if module_name == normalized:
                    score, match_kind = 100, "exact_module"
                elif module_name.casefold() == normalized.casefold():
                    score, match_kind = 95, "case_insensitive_module"
                else:
                    continue
            else:
                assert normalized is not None
                if module_path == normalized:
                    score, match_kind = 100, "exact_path"
                elif module_path.casefold() == normalized.casefold():
                    score, match_kind = 95, "case_insensitive_path"
                elif "/" in normalized and module_path.casefold().endswith("/" + normalized.casefold()):
                    score, match_kind = 85, "path_suffix"
                elif "/" not in normalized and PurePosixPath(module_path).name.casefold() == normalized.casefold():
                    score, match_kind = 80, "basename"
                else:
                    continue
            candidates.append(
                _candidate(
                    module_id,
                    module_name,
                    "module",
                    match_kind,
                    score,
                    module_report_ids,
                    path=module_path,
                    path_source=(
                        "index" if module_name in (catalog.module_paths or {}) else "derived"
                    ),
                    index_source=index_source,
                )
            )
    else:
        indexed_artifacts = [
            (artifact_id, full_name, "active")
            for artifact_id, full_name in catalog.artifacts.items()
        ] + [
            (artifact_id, full_name, "recovery")
            for artifact_id, full_name in recovered_artifacts.items()
            if artifact_id not in catalog.artifacts
        ]
        for artifact_id, full_name, index_source in indexed_artifacts:
            local_name = full_name.split("::", 1)[-1]
            if query_kind == "artifact":
                if full_name == value:
                    score, match_kind = 100, "exact_artifact"
                elif full_name.casefold() == value.casefold():
                    score, match_kind = 95, "case_insensitive_artifact"
                else:
                    suggestion = _suggestion_match(value, full_name)
                    if suggestion:
                        suggestion_kind, suggestion_score = suggestion
                        suggestions.append(
                            _candidate(
                                artifact_id,
                                full_name,
                                "artifact",
                                suggestion_kind,
                                suggestion_score,
                                artifact_report_ids,
                                local_name=local_name,
                                index_source=index_source,
                            )
                        )
                    continue
            else:
                if local_name == value:
                    score, match_kind = 100, "exact_symbol"
                elif local_name.casefold() == value.casefold():
                    score, match_kind = 95, "case_insensitive_symbol"
                elif "." not in value and local_name.casefold().endswith("." + value.casefold()):
                    score, match_kind = 85, "qualified_symbol_suffix"
                else:
                    suggestion = _suggestion_match(value, local_name)
                    if not suggestion:
                        continue
                    suggestion_kind, suggestion_score = suggestion
                    suggestions.append(
                        _candidate(
                            artifact_id,
                            full_name,
                            "artifact",
                            suggestion_kind,
                            suggestion_score,
                            artifact_report_ids,
                            local_name=local_name,
                            index_source=index_source,
                        )
                    )
                    continue
            candidates.append(
                _candidate(
                    artifact_id,
                    full_name,
                    "artifact",
                    match_kind,
                    score,
                    artifact_report_ids,
                    local_name=local_name,
                    index_source=index_source,
                )
            )

    return _resolution(
        query,
        query_kind,
        _best_candidates(candidates),
        _best_tier(suggestions),
    )


def _resolution(query: str, query_kind: str, matches: list[dict], suggestions: list[dict]) -> dict:
    if matches:
        suggestions = []
    if len(matches) == 1:
        status = (
            "resolved_but_not_in_report"
            if matches[0]["in_report"] is False
            else "matched"
        )
    elif len(matches) > 1:
        status = "ambiguous"
    else:
        status = "not_found"
    return {
        "status": status,
        "query": query,
        "query_kind": query_kind,
        "match_count": len(matches),
        "ambiguous": len(matches) > 1,
        "matches": matches,
        "suggestions": suggestions,
    }


def _best_candidates(candidates: list[dict]) -> list[dict]:
    """Prefer identities present in the parsed report, then active identities."""

    if any(item.get("in_report") is True for item in candidates):
        candidates = [item for item in candidates if item.get("in_report") is True]
    best = _best_tier(candidates)
    if any(item.get("index_source") == "active" for item in best):
        best = [item for item in best if item.get("index_source") == "active"]
    return best


def select_complete_artifact_blocks(
    report: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> dict:
    """Copy complete top-level artifact blocks selected by resolved IDs."""

    artifacts = report.get("artifacts", {})
    if not isinstance(artifacts, Mapping):
        raise ValueError("Indexed report must contain an 'artifacts' object.")
    matches = resolution.get("matches", [])
    query_kind = resolution.get("query_kind")

    if query_kind in {"file", "module", "module_id"}:
        module_ids = {str(item["id"]) for item in matches}
        selected = {
            str(artifact_id): copy.deepcopy(block)
            for artifact_id, block in artifacts.items()
            if isinstance(block, Mapping)
            and (
                str(block.get("definer_module")) in module_ids
                or module_ids.intersection(
                    str(value) for value in block.get("consumer_module_indices", [])
                )
            )
        }
    else:
        artifact_ids = {str(item["id"]) for item in matches}
        selected = {
            str(artifact_id): copy.deepcopy(block)
            for artifact_id, block in artifacts.items()
            if str(artifact_id) in artifact_ids
        }

    return dict(sorted(selected.items()))


def describe_block_matches(
    blocks: Mapping[str, Any],
    resolution: Mapping[str, Any],
    catalog: IndexCatalog,
) -> list[dict]:
    """Explain why each complete block was selected without altering its payload."""

    query_kind = resolution.get("query_kind")
    module_ids = {str(item["id"]) for item in resolution.get("matches", [])}
    descriptions = []
    for artifact_id, block in blocks.items():
        roles = []
        if query_kind in {"file", "module", "module_id"} and isinstance(block, Mapping):
            if str(block.get("definer_module")) in module_ids:
                roles.append("defined_here")
            if module_ids.intersection(
                str(value) for value in block.get("consumer_module_indices", [])
            ):
                roles.append("consumed_here")
        else:
            roles.append("matched_artifact")
        descriptions.append(
            {
                "artifact_id": str(artifact_id),
                "artifact": (
                    catalog.artifacts.get(str(artifact_id))
                    or (catalog.recovered_artifacts or {}).get(str(artifact_id))
                ),
                "roles": roles,
            }
        )
    return descriptions


def rewrite_selected_indices(
    blocks: Mapping[str, Any],
    catalog: IndexCatalog,
    resolve_names: bool = True,
) -> tuple[dict, dict]:
    """Validate through active/recovery indexes and optionally replace IDs with names."""

    def module_name(value: Any) -> tuple[str | None, str | None]:
        key = str(value)
        if key in catalog.modules:
            return catalog.modules[key], "active"
        if key in (catalog.recovered_modules or {}):
            return (catalog.recovered_modules or {})[key], "recovery"
        return None, None

    def artifact_name(value: Any) -> tuple[str | None, str | None]:
        key = str(value)
        if key in catalog.artifacts:
            return catalog.artifacts[key], "active"
        if key in (catalog.recovered_artifacts or {}):
            return (catalog.recovered_artifacts or {})[key], "recovery"
        return None, None

    rewritten = {}
    diagnostics = {
        "omitted_blocks": [],
        "dropped_references": [],
        "resolved_from_recovery": [],
    }
    unresolved = object()

    def rewrite_nested_module_ids(value: Any, artifact_id: str, field: str) -> Any:
        if isinstance(value, str) and MODULE_ID_RE.fullmatch(value):
            resolved, source = module_name(value)
            if resolved is None:
                diagnostics["dropped_references"].append(
                    {"artifact_id": artifact_id, "field": field, "module_id": value}
                )
                return unresolved
            if source == "recovery":
                diagnostics["resolved_from_recovery"].append(
                    {"kind": "module", "id": value, "name": resolved}
                )
            return resolved if resolve_names else value
        if isinstance(value, list):
            rewritten_values = []
            for index, item in enumerate(value):
                rewritten_item = rewrite_nested_module_ids(
                    item, artifact_id, f"{field}[{index}]"
                )
                if rewritten_item is not unresolved:
                    rewritten_values.append(rewritten_item)
            return rewritten_values
        if isinstance(value, dict):
            rewritten_dict = {}
            for key, item in value.items():
                rewritten_item = rewrite_nested_module_ids(
                    item, artifact_id, f"{field}.{key}"
                )
                if rewritten_item is unresolved:
                    if key == "module":
                        return unresolved
                    continue
                rewritten_dict[key] = rewritten_item
            return rewritten_dict
        return value
    for artifact_id, original in blocks.items():
        resolved_artifact, artifact_source = artifact_name(artifact_id)
        if resolved_artifact is None:
            diagnostics["omitted_blocks"].append(
                {"artifact_id": str(artifact_id), "reason": "unknown_artifact_id"}
            )
            continue
        block = copy.deepcopy(original)
        if not isinstance(block, dict) or "definer_module" not in block:
            diagnostics["omitted_blocks"].append(
                {"artifact_id": str(artifact_id), "reason": "missing_definer_module"}
            )
            continue
        definer_id = str(block["definer_module"])
        resolved_definer, definer_source = module_name(definer_id)
        if resolved_definer is None:
            diagnostics["omitted_blocks"].append(
                {
                    "artifact_id": str(artifact_id),
                    "reason": "unknown_definer_module_id",
                    "module_id": definer_id,
                }
            )
            continue
        if resolve_names:
            block["definer_module"] = resolved_definer
        if artifact_source == "recovery":
            diagnostics["resolved_from_recovery"].append(
                {"kind": "artifact", "id": str(artifact_id), "name": resolved_artifact}
            )
        if definer_source == "recovery":
            diagnostics["resolved_from_recovery"].append(
                {"kind": "module", "id": definer_id, "name": resolved_definer}
            )
        if "consumer_module_indices" in block:
            consumers = []
            consumer_ids = []
            for value in block["consumer_module_indices"]:
                consumer_id = str(value)
                resolved_consumer, consumer_source = module_name(consumer_id)
                if resolved_consumer is None:
                    diagnostics["dropped_references"].append(
                        {
                            "artifact_id": str(artifact_id),
                            "field": "consumer_module_indices",
                            "module_id": consumer_id,
                        }
                    )
                    continue
                consumers.append(resolved_consumer)
                consumer_ids.append(consumer_id)
                if consumer_source == "recovery":
                    diagnostics["resolved_from_recovery"].append(
                        {"kind": "module", "id": consumer_id, "name": resolved_consumer}
                    )
            if resolve_names:
                block.pop("consumer_module_indices")
                block["consumer_modules"] = consumers
            else:
                block["consumer_module_indices"] = consumer_ids
        if block.get("usage") is not None:
            rewritten_usage = rewrite_nested_module_ids(
                block["usage"], str(artifact_id), "usage"
            )
            block["usage"] = None if rewritten_usage is unresolved else rewritten_usage
        output_key = resolved_artifact if resolve_names else str(artifact_id)
        if output_key in rewritten:
            output_key = f"{resolved_artifact} [{artifact_id}]"
        rewritten[output_key] = block
    return rewritten, diagnostics


def query_indexed_report(
    report: Mapping[str, Any],
    query: str,
    catalog: IndexCatalog,
    repo_root: str | None = None,
    resolve_indices: bool = True,
) -> dict:
    """Resolve, select whole blocks, then optionally rewrite IDs for presentation."""

    report_artifacts = report.get("artifacts", {})
    if not isinstance(report_artifacts, Mapping):
        raise ValueError("Indexed report must contain an 'artifacts' object.")
    resolution = resolve_index_query(
        query,
        catalog,
        report_artifact_ids={str(key) for key in report_artifacts},
        report_module_ids={
            str(module_id)
            for block in report_artifacts.values()
            if isinstance(block, Mapping)
            for module_id in (
                [block.get("definer_module")]
                + list(block.get("consumer_module_indices", []))
            )
            if module_id is not None
        },
        repo_root=repo_root,
    )
    blocks = select_complete_artifact_blocks(report, resolution)
    selection = describe_block_matches(blocks, resolution, catalog)
    diagnostics = {"omitted_blocks": [], "dropped_references": [], "resolved_from_recovery": []}
    blocks, diagnostics = rewrite_selected_indices(
        blocks,
        catalog,
        resolve_names=resolve_indices,
    )
    return {
        "resolution": resolution,
        "artifact_count": len(blocks),
        "artifacts": blocks,
        "selection": selection,
        "diagnostics": diagnostics,
    }
