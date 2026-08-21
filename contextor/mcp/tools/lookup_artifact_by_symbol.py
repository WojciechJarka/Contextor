import json
from pathlib import Path

from contextor.core.analysis.state_manager import artifact_consumption_is_fresh
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers


def lookup_artifact_by_symbol(
    repo_path: str,
    symbol_name: str,
    limit: int | None = 20,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        _, _, art_path_to_id, _ = query_helpers.read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."

        state = engine.state
        term = symbol_name.casefold()
        candidates = []
        for module_name, module_data in sorted((state.artifacts or {}).items()):
            unavailable = query_helpers.module_truth_unavailable(state, module_name)
            for symbol, kind in query_helpers.canonical_symbol_catalog(module_data).items():
                if term not in symbol.casefold():
                    continue
                if unavailable:
                    return json.dumps(unavailable, indent=2)
                full_name = f"{module_name}::{symbol}"
                artifact_id = art_path_to_id.get(full_name)
                key = artifact_id or full_name
                candidates.append(
                    (symbol.casefold() != term, symbol.casefold(), full_name, key, kind)
                )

        candidates.sort()
        if candidates and not candidates[0][0]:
            candidates = [item for item in candidates if not item[0]]
        if len(candidates) > 1 and not candidates[0][0]:
            return json.dumps(
                {
                    "error": "Ambiguous canonical symbol identity.",
                    "query": symbol_name,
                    "candidates": [item[2] for item in candidates],
                    "data_source": "live_canonical_state",
                },
                indent=2,
            )
        candidates, total_matches, matches_truncated = query_helpers.bounded_items(
            candidates, limit
        )

        if not candidates:
            return f"No current artifacts found matching '{symbol_name}'."

        results: dict = {}
        for _, _, full_name, key, kind in candidates:
            module_name, symbol = full_name.split("::", 1)
            entry = {
                "symbol": symbol,
                "full_name": full_name,
                "kind": kind,
                "definer_module": module_name,
            }
            if artifact_consumption_is_fresh(state):
                resolved_consumers = query_helpers.canonical_symbol_consumers(
                    state, module_name, symbol
                )
                consumer_items, consumer_total, consumer_truncated = query_helpers.bounded_items(
                    resolved_consumers, evidence_limit
                )
                entry["consumers"] = {
                    "total": consumer_total,
                    "truncated": consumer_truncated,
                }
                if not compact:
                    entry["consumers"]["items"] = consumer_items
            else:
                entry["consumers"] = {
                    "available": False,
                    "state": getattr(state, "artifact_consumption_state", "deferred"),
                    "reason": "Canonical artifact consumption is unavailable or stale.",
                }
            results[key] = entry

        result = {
                "query": symbol_name,
                "match_count": len(results),
                "total_matches": total_matches,
                "truncated": matches_truncated,
                "data_source": "live_canonical_state",
                "artifacts": results,
            }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for lookup_artifact_by_symbol",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error searching artifacts by symbol: {e}"
