import json
from pathlib import Path

from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers


def get_artifact_blast_radius(
    repo_path: str,
    artifact_name: str,
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."
        target_art = art_id_to_path.get(artifact_name, artifact_name)
        if engine:
            live_matches = []
            for module_name, artifact_state in engine.state.artifacts.items():
                for local_name, kind in query_helpers.canonical_symbol_catalog(artifact_state).items():
                    full_name = f"{module_name}::{local_name}"
                    art_id = str(art_path_to_id.get(full_name, ""))
                    if (
                        full_name != artifact_name
                        and local_name != artifact_name
                        and art_id != artifact_name
                        and full_name != target_art
                    ):
                        continue
                    unavailable = query_helpers.module_truth_unavailable(
                        engine.state, module_name
                    )
                    if unavailable:
                        return json.dumps(unavailable, indent=2)
                    live_matches.append(
                        {
                            "artifact": full_name,
                            "artifact_id": art_path_to_id.get(full_name),
                            "kind": kind,
                            "definer": module_name,
                            "consumer_items": query_helpers.canonical_symbol_consumers(
                                engine.state, module_name, str(local_name)
                            ),
                        }
                    )
            if live_matches:
                ordered_matches = sorted(live_matches, key=lambda item: item["artifact"])
                if len(ordered_matches) > 1:
                    return json.dumps(
                        {
                            "error": "Ambiguous canonical artifact identity.",
                            "query": artifact_name,
                            "candidates": [item["artifact"] for item in ordered_matches],
                            "data_source": "live_canonical_state",
                        },
                        indent=2,
                    )
                selected = ordered_matches[0]
                raw_consumer_items = list(selected.pop("consumer_items"))
                unique_direct_consumers = sorted(set(raw_consumer_items))
                consumer_items, consumer_total, consumer_truncated = query_helpers.bounded_items(
                    unique_direct_consumers, max_items
                )

                architecture = {"available": False}
                cached_analytics = getattr(engine.state, "cached_analytics", {}) or {}
                cached_state = getattr(engine.state, "cached_analytics_state", "deferred")
                if cached_state == "fresh" and isinstance(cached_analytics, dict):
                    module_layers = cached_analytics.get("module_layers", {}) or {}
                    definer_module = selected.get("definer", "")
                    definer_layer = module_layers.get(definer_module)

                    same_module_consumers = []
                    same_layer_consumers = []
                    cross_layer_consumers_list = []
                    test_consumers = []
                    unknown_layer_consumers = []
                    known_consumer_layers_set = set()

                    for c_mod in unique_direct_consumers:
                        if c_mod == definer_module:
                            same_module_consumers.append(c_mod)
                            continue

                        c_layer = module_layers.get(c_mod)
                        if c_layer is not None:
                            known_consumer_layers_set.add(c_layer)

                        if c_layer == "tests":
                            test_consumers.append(c_mod)
                        elif definer_layer is None:
                            unknown_layer_consumers.append(c_mod)
                        elif c_layer is None:
                            unknown_layer_consumers.append(c_mod)
                        elif c_layer == definer_layer:
                            same_layer_consumers.append(c_mod)
                        else:
                            cross_layer_consumers_list.append({"module": c_mod, "layer": c_layer})

                    same_mod_count = len(same_module_consumers)
                    same_layer_count = len(same_layer_consumers)
                    cross_layer_count = len(cross_layer_consumers_list)
                    test_count = len(test_consumers)
                    unknown_count = len(unknown_layer_consumers)

                    architecture = {
                        "available": True,
                        "definer_layer": definer_layer,
                        "consumer_layers": sorted(known_consumer_layers_set),
                        "same_module_consumer_count": same_mod_count,
                        "same_layer_consumer_count": same_layer_count,
                        "cross_layer_consumer_count": cross_layer_count,
                        "test_consumer_count": test_count,
                        "cross_layer_consumers": cross_layer_count > 0,
                    }
                    if unknown_count > 0:
                        architecture["unknown_layer_consumer_count"] = unknown_count
                    if cross_layer_count > 0:
                        cross_sample, cross_total, cross_trunc = query_helpers.bounded_items(
                            cross_layer_consumers_list, 5
                        )
                        architecture["cross_layer_sample"] = {
                            "total": cross_total,
                            "items": cross_sample,
                            "truncated": cross_trunc,
                        }
                else:
                    architecture = {
                        "available": False,
                        "reason": f"Cached analytics state is '{cached_state}'.",
                    }

                # 2. Downstream module reachability (Model B)
                from contextor.core.analysis.incremental.graph_ops import calculate_affected_set

                dep_graph = getattr(engine.state, "dependency_graph", None) if engine else None
                definer_module = selected.get("definer", "")

                if dep_graph is not None:
                    all_reachable: set[str] = set()
                    for seed_mod in unique_direct_consumers:
                        all_reachable.update(calculate_affected_set(seed_mod, old_graph=dep_graph))

                    downstream_set = all_reachable - set(unique_direct_consumers) - {definer_module}
                    sorted_downstream = sorted(downstream_set)
                    total_downstream = len(sorted_downstream)

                    downstream_reachability = {
                        "available": True,
                        "total_downstream_count": total_downstream,
                    }

                    if cached_state == "fresh" and isinstance(cached_analytics, dict):
                        module_layers = cached_analytics.get("module_layers", {}) or {}
                        prod_downstream = []
                        test_downstream = []
                        unknown_downstream = []

                        for d_mod in sorted_downstream:
                            d_layer = module_layers.get(d_mod)
                            if d_layer == "tests":
                                test_downstream.append(d_mod)
                            elif d_layer is not None:
                                prod_downstream.append(d_mod)
                            else:
                                unknown_downstream.append(d_mod)

                        prod_sample, prod_total, prod_trunc = query_helpers.bounded_items(prod_downstream, 5)
                        test_sample, test_total, test_trunc = query_helpers.bounded_items(test_downstream, 5)

                        downstream_reachability.update(
                            {
                                "layer_classification_available": True,
                                "production_downstream_count": len(prod_downstream),
                                "test_downstream_count": len(test_downstream),
                                "unknown_layer_downstream_count": len(unknown_downstream),
                                "production_downstream_sample": {
                                    "total": prod_total,
                                    "items": prod_sample,
                                    "truncated": prod_trunc,
                                },
                                "test_downstream_sample": {
                                    "total": test_total,
                                    "items": test_sample,
                                    "truncated": test_trunc,
                                },
                            }
                        )
                    else:
                        downstream_reachability.update(
                            {
                                "layer_classification_available": False,
                                "reason": f"Cached analytics state is '{cached_state}'.",
                            }
                        )
                else:
                    downstream_reachability = {
                        "available": False,
                        "reason": "Live dependency graph is not available.",
                    }

                result = {
                    **selected,
                    "architecture": architecture,
                    "downstream_module_reachability": downstream_reachability,
                    "consumers": {
                        "total": consumer_total,
                        "truncated": consumer_truncated,
                    },
                    "evidence_scope": "direct_static_artifact_consumption",
                    "data_source": "live_canonical_state",
                }
                if not compact:
                    result["consumers"]["items"] = consumer_items
                if fields is not None:
                    unknown_fields = sorted(set(fields) - set(result))
                    if unknown_fields:
                        return json.dumps(
                            {
                                "error": "Unsupported fields for get_artifact_blast_radius",
                                "unknown_fields": unknown_fields,
                                "allowed_fields": sorted(result),
                            },
                            indent=2,
                        )
                    result = {field: result[field] for field in fields}
                return json.dumps(result, indent=2)

        candidates = [
            (art_id, full_name)
            for art_id, full_name in art_id_to_path.items()
            if full_name == artifact_name
            or full_name.endswith("::" + artifact_name)
        ]
        if not candidates:
            from contextor.core.report_query import IndexCatalog, catalog_from_registry, resolve_index_query

            catalog = catalog_from_registry(str(root))
            if not catalog.modules and mod_id_to_path:
                catalog = IndexCatalog(
                    modules=mod_id_to_path,
                    artifacts=art_id_to_path,
                    module_paths={name: name.replace(".", "/") + ".py" for name in mod_path_to_id},
                    recovered_modules={},
                    recovered_artifacts={},
                )
            resolution = resolve_index_query(artifact_name, catalog, repo_root=str(root))
            if resolution.get("matches"):
                top = resolution["matches"][0]
                if top.get("kind") == "module":
                    target_module = top["name"]
                    target_module_id = top["id"]
                    prefix = target_module + "::"
                    art_state = (getattr(engine.state, "artifacts", {}) or {}).get(target_module, {}) if engine else {}
                    symbols = art_state.get("symbols", {}) or {}
                    kind_map = {}
                    for category, kind_label in [
                        ("classes", "class"),
                        ("functions", "function"),
                        ("methods", "method"),
                        ("globals", "global"),
                    ]:
                        for s in symbols.get(category, []) or []:
                            kind_map[str(s)] = kind_label

                    candidates_list = []
                    seen_artifacts = set()
                    for full_name, art_id in sorted(art_path_to_id.items()):
                        if full_name.startswith(prefix):
                            local_name = full_name.split("::", 1)[-1]
                            seen_artifacts.add(local_name)
                            candidates_list.append(
                                {
                                    "artifact_id": str(art_id),
                                    "artifact": full_name,
                                    "kind": kind_map.get(local_name, "symbol"),
                                }
                            )
                    for local_name in sorted(art_state.get("own_symbols", []) or []):
                        if local_name not in seen_artifacts:
                            full_name = f"{target_module}::{local_name}"
                            candidates_list.append(
                                {
                                    "artifact_id": str(art_path_to_id.get(full_name, "")),
                                    "artifact": full_name,
                                    "kind": kind_map.get(str(local_name), "symbol"),
                                }
                            )
                            seen_artifacts.add(local_name)

                    from contextor.core.api.public_api import extract_public_api

                    canonical_public_api = set(extract_public_api(symbols)) if symbols else set()

                    def _candidate_rank_key(item: dict) -> tuple:
                        full_name = item.get("artifact", "")
                        kind = item.get("kind", "symbol")
                        local = str(full_name).split("::", 1)[-1].split("(", 1)[0]
                        parts = local.split(".")
                        leaf = parts[-1]
                        is_dunder = leaf.startswith("__") and leaf.endswith("__")
                        is_private_leaf = leaf.startswith("_") and not is_dunder
                        has_priv_parent = any(
                            p.startswith("_") and not (p.startswith("__") and p.endswith("__"))
                            for p in parts[:-1]
                        )
                        is_canonical_public = local in canonical_public_api

                        if is_canonical_public:
                            kind_order = {"class": 0, "function": 1, "method": 2, "global": 3}.get(kind, 4)
                            tier = (0, kind_order)
                        elif not has_priv_parent and not is_private_leaf and not is_dunder:
                            kind_order = {"class": 0, "function": 1, "method": 2, "global": 3}.get(kind, 4)
                            tier = (1, kind_order)
                        elif not has_priv_parent and is_dunder:
                            tier = (2, 0)
                        elif not has_priv_parent and is_private_leaf:
                            tier = (3, 0)
                        else:
                            tier = (4, 0)
                        return (tier, local)

                    candidates_list.sort(key=_candidate_rank_key)
                    items, total, truncated = query_helpers.bounded_items(candidates_list, max_items)
                    return json.dumps(
                        {
                            "target": artifact_name,
                            "resolved_as": "module",
                            "module": target_module,
                            "module_id": target_module_id,
                            "suggested_next_tool": "get_module_context",
                            "artifact_candidates": {
                                "total": total,
                                "items": items,
                                "truncated": truncated,
                            },
                            "warnings": [
                                "Target resolved to a module rather than an artifact. "
                                "Use get_module_context for module-level context or choose one of the artifact candidates."
                            ],
                        },
                        indent=2,
                    )
            return f"Artifact '{artifact_name}' not found in the registry."

        return f"Artifact '{artifact_name}' not found in canonical LIVE state."
    except Exception as e:
        return f"Error calculating artifact blast radius: {e}"
