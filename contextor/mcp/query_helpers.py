from pathlib import Path

from contextor.core.analysis.state_manager import (
    artifact_consumption_is_fresh,
    canonical_artifact_consumption_targets,
    module_current_truth,
)


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
