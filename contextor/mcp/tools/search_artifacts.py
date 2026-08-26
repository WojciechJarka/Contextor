import json
from pathlib import Path

from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers


def search_artifacts(
    repo_path: str,
    search_term: str | None = None,
    limit: int | None = 20,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
    query: str | None = None,
) -> str:
    if search_term is None and query is None:
        return json.dumps(
            {
                "status": "error",
                "error": "search_term or query is required.",
            },
            indent=2,
        )

    if (
        search_term is not None
        and query is not None
        and search_term != query
    ):
        return json.dumps(
            {
                "status": "error",
                "error": "search_term and query must match when both are provided.",
            },
            indent=2,
        )

    effective_term = search_term if search_term is not None else query

    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    engine = mcp_runtime.get_or_init_engine(root)
    if not engine:
        return "Error: No live canonical state found. Run analyze_project first."
        
    try:
        found_artifacts = []
        found_modules = []
        kind_by_category = {
            "functions": "function",
            "classes": "class",
            "methods": "method",
            "globals": "global",
        }
        module_paths = sorted(
            set(getattr(engine.state, "modules", {}))
            | set(engine.state.artifacts)
        )
        for mod_path in module_paths:
            unavailable = query_helpers.module_truth_unavailable(engine.state, mod_path)
            module_leaf = mod_path.rsplit(".", 1)[-1]
            if effective_term.casefold() in mod_path.casefold():
                if unavailable:
                    return json.dumps(unavailable, indent=2)
                graph = engine.state.dependency_graph
                inbound = []
                outbound = []
                if graph is not None:
                    hard_edges = getattr(graph, "hard_edges", {})
                    soft_edges = getattr(graph, "soft_edges", {})
                    outbound = sorted(
                        set(hard_edges.get(mod_path, set()))
                        | set(soft_edges.get(mod_path, set()))
                    )
                    inbound = sorted(
                        source
                        for source in set(hard_edges) | set(soft_edges)
                        if mod_path
                        in (
                            set(hard_edges.get(source, set()))
                            | set(soft_edges.get(source, set()))
                        )
                    )
                exact_module = effective_term.casefold() in {
                    mod_path.casefold(),
                    module_leaf.casefold(),
                }
                inbound_items, inbound_total, inbound_truncated = query_helpers.bounded_items(
                    inbound, evidence_limit
                )
                outbound_items, outbound_total, outbound_truncated = query_helpers.bounded_items(
                    outbound, evidence_limit
                )
                _compact_ev_limit = 3 if evidence_limit is None else min(3, evidence_limit)
                if compact:
                    inbound_ev = inbound_items[:_compact_ev_limit]
                    inbound_dep = {
                        "total": inbound_total,
                        "truncated": inbound_total > len(inbound_ev),
                        "evidence": inbound_ev,
                    }
                    if inbound_dep["truncated"]:
                        inbound_dep["expand"] = {"compact": False, "evidence_limit": None}
                    outbound_ev = outbound_items[:_compact_ev_limit]
                    outbound_dep = {
                        "total": outbound_total,
                        "truncated": outbound_total > len(outbound_ev),
                        "evidence": outbound_ev,
                    }
                    if outbound_dep["truncated"]:
                        outbound_dep["expand"] = {"compact": False, "evidence_limit": None}
                else:
                    inbound_dep = {
                        "total": inbound_total,
                        "truncated": inbound_truncated,
                        "items": inbound_items,
                    }
                    outbound_dep = {
                        "total": outbound_total,
                        "truncated": outbound_truncated,
                        "items": outbound_items,
                    }
                module_entry = {
                    "kind": "module",
                    "module_id": engine.registry.get_module_id(mod_path),
                    "dependencies_inbound": inbound_dep,
                    "dependencies_outbound": outbound_dep,
                }
                found_modules.append(
                    (
                        not exact_module,
                        mod_path.casefold(),
                        mod_path,
                        module_entry,
                    )
                )
        for mod_path, mod_arts in engine.state.artifacts.items():
            unavailable = query_helpers.module_truth_unavailable(engine.state, mod_path)
            symbols = mod_arts.get("symbols", {})
            for category, kind in kind_by_category.items():
                raw_names = symbols.get(category, [])
                names = raw_names.keys() if isinstance(raw_names, dict) else raw_names
                for raw_name in names:
                    name = str(raw_name)
                    if effective_term.lower() in name.lower():
                        if unavailable:
                            return json.dumps(unavailable, indent=2)
                        definer_mod = engine.registry.get_module_id(mod_path)
                        consumers_dict = mod_arts.get("consumers", {}).get(name, {})
                        if isinstance(consumers_dict, dict):
                            consumers = consumers_dict.get("consumers", [])
                        else:
                            consumers = consumers_dict if isinstance(consumers_dict, list) else []

                        consumer_paths = [
                            engine.registry.get_module_path(str(c)) or str(c)
                            for c in consumers
                        ]

                        consumer_items, consumer_total, consumer_truncated = query_helpers.bounded_items(
                            consumer_paths, evidence_limit
                        )
                        _compact_ev_limit = 3 if evidence_limit is None else min(3, evidence_limit)
                        if compact:
                            con_ev = consumer_items[:_compact_ev_limit]
                            consumers_view = {
                                "total": consumer_total,
                                "truncated": consumer_total > len(con_ev),
                                "evidence": con_ev,
                            }
                            if consumers_view["truncated"]:
                                consumers_view["expand"] = {"compact": False, "evidence_limit": None}
                        else:
                            consumers_view = {
                                "total": consumer_total,
                                "truncated": consumer_truncated,
                                "items": consumer_items,
                            }
                        artifact_entry = {
                            "kind": kind,
                            "definer_module_path": mod_path,
                            "definer_module_id": definer_mod,
                            "consumers": consumers_view,
                        }
                        found_artifacts.append((name.lower() != effective_term.lower(), name.lower(), f"{mod_path}::{name}", artifact_entry))

        if not found_artifacts and not found_modules:
            return f"No live modules or artifacts found matching '{effective_term}'."

        found_artifacts.sort()
        found_modules.sort()
        all_found = [
            (item[0], item[1], "artifact", item[2], item[3])
            for item in found_artifacts
        ] + [
            (item[0], item[1], "module", item[2], item[3])
            for item in found_modules
        ]
        all_found.sort()
        if not all_found[0][0]:
            all_found = [item for item in all_found if not item[0]]
        selected, total, truncated = query_helpers.bounded_items(all_found, limit)
        selected_artifacts = [item for item in selected if item[2] == "artifact"]
        selected_modules = [item for item in selected if item[2] == "module"]
        result = {
            "query": effective_term,
            "match_count": len(selected),
            "total_matches": total,
            "truncated": truncated,
            "data_source": "live_canonical_state",
            "state_freshness": query_helpers.build_state_freshness(root, engine.state, engine=engine),
            "modules": {item[3]: item[4] for item in selected_modules},
            "artifacts": {item[3]: item[4] for item in selected_artifacts},
        }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for search_artifacts",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting artifact context from live state: {e}"
