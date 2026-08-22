import json
from pathlib import Path

from contextor.core.analysis.state_manager import artifact_consumption_is_fresh
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers


def lookup_artifact_by_symbol(
    repo_path: str,
    symbol_name: str = "",
    limit: int | None = 20,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
    symbol: str | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    normalized_symbol_name = symbol_name.strip()
    normalized_symbol = symbol.strip() if symbol is not None else ""

    if normalized_symbol_name and normalized_symbol and normalized_symbol_name != normalized_symbol:
        return json.dumps(
            {
                "status": "error",
                "error": "symbol_name and symbol must match when both are provided.",
            },
            indent=2,
        )

    effective_symbol = normalized_symbol or normalized_symbol_name
    if not effective_symbol:
        return json.dumps(
            {
                "status": "error",
                "error": "symbol_name or symbol is required.",
            },
            indent=2,
        )

    try:
        _, _, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."

        state = engine.state
        term = effective_symbol.casefold()
        candidates = []
        for module_name, module_data in sorted((state.artifacts or {}).items()):
            unavailable = query_helpers.module_truth_unavailable(state, module_name)
            for s, kind in query_helpers.canonical_symbol_catalog(module_data).items():
                if term not in s.casefold():
                    continue
                if unavailable:
                    return json.dumps(unavailable, indent=2)
                full_name = f"{module_name}::{s}"
                artifact_id = art_path_to_id.get(full_name)
                key = artifact_id or full_name
                candidates.append(
                    (s.casefold() != term, s.casefold(), full_name, key, kind)
                )

        candidates.sort()
        if candidates and not candidates[0][0]:
            candidates = [item for item in candidates if not item[0]]
        if len(candidates) > 1 and not candidates[0][0]:
            return json.dumps(
                {
                    "error": "Ambiguous canonical symbol identity.",
                    "query": effective_symbol,
                    "candidates": [item[2] for item in candidates],
                    "data_source": "live_canonical_state",
                },
                indent=2,
            )

        if not candidates:
            identity_resolution = query_helpers.resolve_artifact_identity(
                effective_symbol,
                art_path_to_id,
                art_id_to_path,
            )
            if identity_resolution["status"] == "resolved":
                resolved_full_name = identity_resolution["artifact"]
                resolved_module, resolved_symbol = (
                    resolved_full_name.split("::", 1)
                    if "::" in resolved_full_name
                    else ("", resolved_full_name)
                )
                if (
                    resolved_module in (state.artifacts or {})
                    and resolved_symbol
                    in query_helpers.canonical_symbol_catalog(
                        state.artifacts[resolved_module]
                    )
                ):
                    unavailable = query_helpers.module_truth_unavailable(
                        state, resolved_module
                    )
                    if unavailable:
                        return json.dumps(unavailable, indent=2)

                    kind = query_helpers.canonical_symbol_catalog(
                        state.artifacts[resolved_module]
                    )[resolved_symbol]
                    artifact_id = art_path_to_id.get(resolved_full_name)
                    key = artifact_id or resolved_full_name
                    candidates = [
                        (False, resolved_symbol.casefold(), resolved_full_name, key, kind)
                    ]
            elif (
                identity_resolution["status"] == "not_found"
                and identity_resolution.get("similar_candidates")
            ):
                return json.dumps(
                    {
                        "status": "not_found",
                        "query": effective_symbol,
                        "similar_candidates": identity_resolution["similar_candidates"],
                        "data_source": "active_artifact_registry",
                    },
                    indent=2,
                )
            elif identity_resolution["status"] == "ambiguous":
                return json.dumps(
                    {
                        "error": "Ambiguous canonical symbol identity.",
                        "query": effective_symbol,
                        "candidates": [
                            c["artifact"]
                            for c in identity_resolution.get("candidates", [])
                        ],
                        "data_source": "active_artifact_registry",
                    },
                    indent=2,
                )

        if not candidates:
            return f"No current artifacts found matching '{effective_symbol}'."

        candidates, total_matches, matches_truncated = query_helpers.bounded_items(
            candidates, limit
        )

        results: dict = {}
        for _, _, full_name, key, kind in candidates:
            module_name, s = full_name.split("::", 1)
            entry = {
                "symbol": s,
                "full_name": full_name,
                "kind": kind,
                "definer_module": module_name,
            }
            if artifact_consumption_is_fresh(state):
                resolved_consumers = query_helpers.canonical_symbol_consumers(
                    state, module_name, s
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
                "query": effective_symbol,
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
