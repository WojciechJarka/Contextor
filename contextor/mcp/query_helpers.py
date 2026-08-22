import difflib
from pathlib import Path

from contextor.core.analysis.state_manager import (
    artifact_consumption_is_fresh,
    canonical_artifact_consumption_targets,
    module_current_truth,
)

FUZZY_MIN_SCORE: float = 0.75
FUZZY_MAX_CANDIDATES: int = 5


def bounded_items(items: list, limit: int | None) -> tuple[list, int, bool]:
    total = len(items)
    if limit is None:
        return items, total, False
    safe_limit = max(0, int(limit))
    selected = items[:safe_limit]
    return selected, total, total > len(selected)


def read_registries(root: Path) -> tuple[dict, dict, dict, dict]:
    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    registry = PersistentIdentityRegistry(str(root))
    with registry.transaction():
        mod_reg = registry._state.get("module_registry", {})
        art_reg = registry._state.get("artifact_registry", {})
    return (
        mod_reg.get("path_to_id", {}),
        mod_reg.get("id_to_path", {}),
        art_reg.get("path_to_id", {}),
        art_reg.get("id_to_path", {}),
    )


def canonical_symbol_consumers(
    state, module_name: str, symbol: str
) -> list[str]:
    if not artifact_consumption_is_fresh(state):
        raise ValueError("Canonical artifact consumption is unavailable or stale.")
    target = f"{module_name}::{symbol}"
    consumption = getattr(state, "artifact_consumption", {}) or {}
    entry = consumption.get(target, {}) if isinstance(consumption, dict) else {}
    consumers = entry.get("consumers", []) if isinstance(entry, dict) else []
    return sorted({str(item) for item in consumers})


def module_truth_unavailable(state, module_name: str) -> dict | None:
    truth = module_current_truth(state, module_name)
    if truth["available"]:
        return None
    return {
        "status": "stale",
        "available": False,
        "module": module_name,
        **{key: value for key, value in truth.items() if key != "available"},
    }


def canonical_symbol_catalog(module_data: dict) -> dict[str, str]:
    targets = canonical_artifact_consumption_targets({"module": module_data})
    result = {target.split("::", 1)[1]: "unknown" for target in targets}
    symbols = module_data.get("symbols", {}) or {}
    for category, kind in (
        ("classes", "class"),
        ("functions", "function"),
        ("methods", "method"),
        ("globals", "global"),
    ):
        raw_names = symbols.get(category, []) or []
        names = raw_names.keys() if isinstance(raw_names, dict) else raw_names
        for name in names:
            if str(name) in result:
                result[str(name)] = kind
    return result


def is_module_id(query: str) -> bool:
    raw = query.strip()
    parts = raw.split("/")
    return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()


def _is_artifact_id(query: str) -> bool:
    if not (query.startswith(("A", "a")) and "/" in query):
        return False
    parts = query[1:].split("/")
    return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()


def resolve_module_identity(
    query: str,
    mod_path_to_id: dict[str, str],
    mod_id_to_path: dict[str, str],
) -> dict:
    raw = query.strip()
    if not raw:
        return {
            "status": "not_found",
            "query": raw,
            "similar_candidates": [],
        }

    # 1. Module ID lookup
    if is_module_id(raw):
        exact_name = mod_id_to_path.get(raw)
        if exact_name:
            return {
                "status": "resolved",
                "resolution": "exact_id",
                "module": exact_name,
                "module_id": raw,
                "similar_candidates": [],
            }
        return {
            "status": "not_found",
            "query": raw,
            "query_kind": "module_id",
            "similar_candidates": [],
        }

    # 2. Exact canonical module name
    if raw in mod_path_to_id:
        return {
            "status": "resolved",
            "resolution": "exact_name",
            "module": raw,
            "module_id": mod_path_to_id[raw],
            "similar_candidates": [],
        }

    # 3. Fuzzy textual module suggestions
    q_cf = raw.casefold()
    scored = []
    for name in mod_path_to_id:
        raw_score = difflib.SequenceMatcher(None, q_cf, name.casefold()).ratio()
        if raw_score >= FUZZY_MIN_SCORE:
            scored.append((-raw_score, name, mod_path_to_id[name], raw_score))

    scored.sort()
    candidates = [
        {
            "module": name,
            "module_id": active_id,
            "score": round(score, 4),
        }
        for _, name, active_id, score in scored[:FUZZY_MAX_CANDIDATES]
    ]

    return {
        "status": "not_found",
        "query": raw,
        "similar_candidates": candidates,
    }


def resolve_artifact_identity(
    query: str,
    art_path_to_id: dict[str, str],
    art_id_to_path: dict[str, str],
) -> dict:
    raw = query.strip()
    if not raw:
        return {
            "status": "not_found",
            "query": raw,
            "similar_candidates": [],
        }

    # 1. Artifact ID lookup
    if _is_artifact_id(raw):
        normalized_id = raw[0].upper() + raw[1:]
        exact_identity = art_id_to_path.get(normalized_id)
        if exact_identity:
            return {
                "status": "resolved",
                "resolution": "exact_id",
                "artifact": exact_identity,
                "artifact_id": normalized_id,
                "similar_candidates": [],
            }
        return {
            "status": "not_found",
            "query": raw,
            "query_kind": "artifact_id",
            "similar_candidates": [],
        }

    # 2. Exact canonical artifact identity
    if raw in art_path_to_id:
        return {
            "status": "resolved",
            "resolution": "exact_identity",
            "artifact": raw,
            "artifact_id": art_path_to_id[raw],
            "similar_candidates": [],
        }

    # 3. Exact leaf match
    exact_leaf_matches = []
    for full_name, art_id in art_path_to_id.items():
        leaf = full_name.split("::", 1)[-1] if "::" in full_name else full_name
        if leaf == raw:
            exact_leaf_matches.append((full_name, art_id))

    if len(exact_leaf_matches) == 1:
        full_name, art_id = exact_leaf_matches[0]
        return {
            "status": "resolved",
            "resolution": "exact_leaf",
            "artifact": full_name,
            "artifact_id": art_id,
            "similar_candidates": [],
        }
    elif len(exact_leaf_matches) > 1:
        exact_leaf_matches.sort(key=lambda item: item[0])
        return {
            "status": "ambiguous",
            "resolution": "exact_leaf",
            "query": raw,
            "candidates": [
                {
                    "artifact": full_name,
                    "artifact_id": art_id,
                }
                for full_name, art_id in exact_leaf_matches
            ],
        }

    # 4. Fuzzy suggestions
    q_cf = raw.casefold()
    scored = []
    for full_name, art_id in art_path_to_id.items():
        leaf = full_name.split("::", 1)[-1] if "::" in full_name else full_name
        full_score = difflib.SequenceMatcher(None, q_cf, full_name.casefold()).ratio()
        leaf_score = difflib.SequenceMatcher(None, q_cf, leaf.casefold()).ratio()
        raw_score = max(full_score, leaf_score)
        if raw_score >= FUZZY_MIN_SCORE:
            scored.append((-raw_score, full_name, art_id, raw_score))

    scored.sort()
    candidates = [
        {
            "artifact": full_name,
            "artifact_id": art_id,
            "score": round(score, 4),
        }
        for _, full_name, art_id, score in scored[:FUZZY_MAX_CANDIDATES]
    ]

    return {
        "status": "not_found",
        "query": raw,
        "similar_candidates": candidates,
    }
