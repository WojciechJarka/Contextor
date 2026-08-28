import json
from pathlib import Path

from contextor.core.analysis.state_manager import module_current_truth
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.diagnostics import diagnostics_summary


def _stale_module_truths(state) -> dict[str, dict]:
    """Return parse-stale canonical modules using the shared core contract."""
    module_names = set(getattr(state, "modules", {}) or {}) | set(
        getattr(state, "artifacts", {}) or {}
    )
    return {
        module_name: truth
        for module_name in sorted(module_names)
        if not (truth := module_current_truth(state, module_name))["available"]
    }


def _layer_index_view(
    layer_items: list[dict],
    max_items: int | None,
    compact: bool,
) -> dict:
    selected, total, truncated = query_helpers.bounded_items(layer_items, max_items)
    if compact:
        result = {
            "available": True,
            "distribution": {
                str(item["layer"]): int(item["module_count"])
                for item in selected
            },
            "total": total,
            "truncated": truncated,
        }
    else:
        result = {
            "available": True,
            "items": selected,
            "total": total,
            "truncated": truncated,
        }
    if truncated:
        result["expand"] = {
            "compact": False,
            "max_items": None,
        }
    return result


def get_project_architecture(
    repo_path: str,
    max_items: int | None = 10,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."

        state = engine.state
        stale_modules = _stale_module_truths(state)
        if stale_modules:
            return json.dumps(
                {
                    "status": "stale",
                    "available": False,
                    "scope": "project",
                    "provenance": "last_known_good",
                    "affected_modules": stale_modules,
                },
                indent=2,
            )
        unavailable = {
            "available": False,
            "state": "deferred",
            "reason": "No fresh canonical LIVE producer is available for this analytics family.",
        }
        collections = {
            "action_items": dict(unavailable),
            "top_global_hotspots": dict(unavailable),
        }
        debt_summary = dict(unavailable)

        cached_analytics = getattr(state, "cached_analytics", {}) or {}
        cached_state = getattr(state, "cached_analytics_state", "deferred")
        canonical_modules = set(getattr(state, "modules", {}) or {})
        module_layers = None
        if (
            cached_state == "fresh"
            and isinstance(cached_analytics, dict)
            and "module_layers" in cached_analytics
            and isinstance(cached_analytics["module_layers"], dict)
        ):
            candidate_layers = cached_analytics["module_layers"]
            if set(candidate_layers) == canonical_modules:
                module_layers = candidate_layers
        if isinstance(module_layers, dict):
            layer_counts: dict[str, int] = {}
            for layer in module_layers.values():
                layer_name = str(layer)
                layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
            layer_items = [
                {"layer": layer, "module_count": count}
                for layer, count in sorted(layer_counts.items())
            ]
            layer_index = _layer_index_view(
                layer_items,
                max_items,
                compact,
            )
        else:
            layer_index = dict(unavailable)
        collections["layer_index"] = layer_index
        diag = diagnostics_summary(root, state)
        result = {
            **collections,
            "debt_summary": debt_summary,
            "module_count": len(getattr(state, "modules", {}) or {}),
            "data_source": "live_canonical_state",
            "diagnostics_summary": diag,
            "diagnostics_attention_required": diag["attention_required"],
        }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for get_project_architecture",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error reading project architecture: {e}"
