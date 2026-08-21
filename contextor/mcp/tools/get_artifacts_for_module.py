import json
from pathlib import Path

from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers


def get_artifacts_for_module(
    repo_path: str,
    module_name: str,
    include_consumers: bool = True,
    symbol_filter: str = "",
    limit: int | None = 50,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    # Normalise file-path input to dotted module name.
    target_path = Path(module_name)
    if target_path.is_absolute() or module_name.endswith(".py") or "/" in module_name or "\\" in module_name:
        if target_path.is_absolute():
            try:
                rel_path = target_path.relative_to(root)
            except ValueError:
                rel_path = target_path
        else:
            rel_path = target_path

        parts = list(rel_path.parts)
        if parts and parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
            if parts[-1] == "__init__":
                parts.pop()

        module_name = ".".join(parts)

    try:
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."
        state = engine.state
        unavailable = query_helpers.module_truth_unavailable(state, module_name)
        if unavailable:
            return json.dumps(unavailable, indent=2)
        live_modules = getattr(state, "modules", {}) or {}
        live_artifact_catalog = getattr(state, "artifacts", {}) or {}
        live_artifacts = live_artifact_catalog.get(module_name, {})
        mod_compact_id = mod_path_to_id.get(module_name)
        live_module = live_modules.get(module_name)
        if not mod_compact_id and live_module is not None:
            mod_compact_id = getattr(live_module, "module_id", None)
            if mod_compact_id is None and isinstance(live_module, dict):
                mod_compact_id = live_module.get("module_id")
        if not mod_compact_id and live_module is None and not live_artifacts:
            return (
                f"Module '{module_name}' not found in registry or canonical LIVE state. "
                "Check the module name or run an analysis."
            )

        result_artifacts: dict = {}
        live_symbols = live_artifacts.get("symbols", {})
        signatures = live_symbols.get("signatures", {}) or {}
        for symbol, kind in query_helpers.canonical_symbol_catalog(live_artifacts).items():
            full_name = f"{module_name}::{symbol}"
            artifact_id = art_path_to_id.get(full_name)
            key = artifact_id or full_name
            entry = {
                "artifact_id": artifact_id,
                "symbol": symbol,
                "full_name": full_name,
                "kind": kind,
                "signature": signatures.get(symbol),
            }
            if include_consumers:
                consumers = query_helpers.canonical_symbol_consumers(state, module_name, symbol)
                consumer_items, consumer_total, consumer_truncated = query_helpers.bounded_items(
                    consumers, evidence_limit
                )
                entry["consumers"] = {
                    "total": consumer_total,
                    "truncated": consumer_truncated,
                }
                if not compact:
                    entry["consumers"]["items"] = consumer_items
            result_artifacts[key] = entry

        entries = sorted(
            result_artifacts.items(),
            key=lambda item: item[1].get("symbol", "").lower(),
        )
        if symbol_filter:
            term = symbol_filter.lower()
            entries = [
                item
                for item in entries
                if term in item[1].get("symbol", "").lower()
            ]
        selected, total_count, truncated = query_helpers.bounded_items(entries, limit)

        result = {
                "module": module_name,
                "module_id": mod_compact_id,
                "artifact_count": len(selected),
                "total_artifact_count": total_count,
                "truncated": truncated,
                "symbol_filter": symbol_filter or None,
                "data_sources": ["live_symbol_state"],
                "complete_symbol_catalog": True,
                "artifacts": dict(selected),
            }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for get_artifacts_for_module",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error reading artifacts for module: {e}"
