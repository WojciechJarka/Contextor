import json
from pathlib import Path

from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime

_COMPACT_EVIDENCE_LIMIT = 3
_QUERY_INDEX_CACHE: dict[str, tuple[int, tuple, object]] = {}


def _dependency_collection_view(
    items: list[tuple[str, dict]],
    max_items: int | None,
    compact: bool,
) -> dict:
    total = len(items)
    if compact:
        if max_items is None:
            evidence_limit = _COMPACT_EVIDENCE_LIMIT
        else:
            evidence_limit = min(
                _COMPACT_EVIDENCE_LIMIT,
                max(0, int(max_items)),
            )
        selected = items[:evidence_limit]
        result = {
            "evidence": {
                module_name: list(details.get("dep_types", []))
                for module_name, details in selected
            },
            "total": total,
            "truncated": total > len(selected),
        }
    else:
        selected, _, truncated = query_helpers.bounded_items(items, max_items)
        result = {
            "items": dict(selected),
            "total": total,
            "truncated": truncated,
        }
    if result["truncated"]:
        result["expand"] = {
            "compact": False,
            "max_items": None,
        }
    return result


def get_module_context(
    repo_path: str,
    module_name: str = "",
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
    module: str | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    from contextor.core.report_query import (
        IndexCatalog,
        catalog_from_registry,
        normalize_module_path_to_dotted,
        resolve_index_query,
    )

    engine = mcp_runtime.get_or_init_engine(root)
    state = getattr(engine, "state", None) if engine is not None else None
    canonical_module_paths = {
        str(name): str(getattr(module_obj, "path"))
        for name, module_obj in (getattr(state, "modules", {}) or {}).items()
        if getattr(module_obj, "path", None)
    }
    cache_key = str(root)
    revision = getattr(state, "revision", None)
    effective_name = (module_name or "").strip()
    effective_alias = (module or "").strip()
    direct_query = effective_alias or effective_name
    direct_module = (
        direct_query
        if effective_name == effective_alias or not (effective_name and effective_alias)
        else ""
    )
    direct_module_obj = (getattr(state, "modules", {}) or {}).get(direct_module)
    direct_fast_path = bool(
        direct_module_obj is not None
        and direct_module
        and not query_helpers.is_module_id(direct_module)
    )
    if direct_fast_path:
        direct_id = str(getattr(direct_module_obj, "module_id", direct_module))
        registries = (
            {direct_module: direct_id},
            {direct_id: direct_module},
            {},
            {},
        )
        catalog = IndexCatalog(
            modules={direct_id: direct_module},
            artifacts={},
            module_paths=canonical_module_paths,
            recovered_modules={},
            recovered_artifacts={},
        )
        cached = None
    else:
        cached = _QUERY_INDEX_CACHE.get(cache_key)
        if cached is not None and cached[0] == revision:
            registries = cached[1]
            catalog = cached[2]
        else:
            registries = query_helpers.read_registries(root)
            catalog = catalog_from_registry(
                str(root),
                module_paths=canonical_module_paths or None,
            )
            if revision is not None:
                _QUERY_INDEX_CACHE[cache_key] = (revision, registries, catalog)
    mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = registries
    if not catalog.modules and mod_id_to_path:
        catalog = IndexCatalog(
            modules=mod_id_to_path,
            artifacts=art_id_to_path,
            module_paths={name: name.replace(".", "/") + ".py" for name in mod_path_to_id},
            recovered_modules={},
            recovered_artifacts={},
        )

    if effective_name and effective_alias:
        res_name = resolve_index_query(effective_name, catalog, repo_root=str(root))
        res_alias = resolve_index_query(effective_alias, catalog, repo_root=str(root))
        matches_name = res_name.get("matches", [])
        matches_alias = res_alias.get("matches", [])
        if matches_name and matches_alias:
            m_n = matches_name[0]
            m_a = matches_alias[0]
            if (
                (m_n.get("id") != m_a.get("id"))
                or (m_n.get("name") != m_a.get("name"))
                or (m_n.get("kind") != m_a.get("kind"))
            ):
                return json.dumps(
                    {
                        "error": "Conflicting 'module_name' and 'module' arguments provided. Resolved to different canonical targets.",
                        "module_name": effective_name,
                        "module_name_resolved": {"id": m_n.get("id"), "name": m_n.get("name"), "kind": m_n.get("kind")},
                        "module": effective_alias,
                        "module_resolved": {"id": m_a.get("id"), "name": m_a.get("name"), "kind": m_a.get("kind")},
                    },
                    indent=2,
                )

    input_query = effective_alias or effective_name
    if not input_query:
        return json.dumps({"error": "Either 'module_name' or 'module' must be provided."}, indent=2)

    is_id = query_helpers.is_module_id(input_query)

    if not is_id:
        resolution = resolve_index_query(input_query, catalog, repo_root=str(root))
        if resolution.get("matches"):
            top = resolution["matches"][0]
            if top.get("kind") == "artifact":
                art_name = top["name"]
                art_id = top["id"]
                definer_mod = art_name.split("::", 1)[0]
                return json.dumps(
                    {
                        "target": input_query,
                        "resolved_as": "artifact",
                        "artifact": art_name,
                        "artifact_id": art_id,
                        "definer_module": definer_mod,
                        "suggested_next_tool": "get_artifact_blast_radius",
                        "warnings": [
                            "Target resolved to an artifact/symbol rather than a module. "
                            "Use get_artifact_blast_radius for symbol-level consumption."
                        ],
                    },
                    indent=2,
                )
            elif top.get("kind") == "module":
                module_name = top["name"]
        else:
            module_name = input_query

    if not engine or getattr(engine.state, "resync_required", False):
        return "Error: No usable canonical LIVE state. Run analyze_project first."

    state = engine.state
    live_modules = set(getattr(state, "modules", {})) | set(
        getattr(state, "artifacts", {})
    )

    if is_id:
        identity = query_helpers.resolve_module_identity(
            input_query,
            mod_path_to_id,
            mod_id_to_path,
        )
        if identity["status"] == "resolved" and identity.get("resolution") == "exact_id":
            module_name = identity["module"]
        elif identity["status"] == "not_found" and identity.get("query_kind") == "module_id":
            return f"Module '{input_query}' not found in the project graph."
        else:
            module_name = input_query

    unavailable = query_helpers.module_truth_unavailable(state, module_name)
    if unavailable:
        return json.dumps(unavailable, indent=2)

    if module_name not in live_modules:
        # Textual Not-Found: shared fuzzy suggestions fallback
        normalized_for_resolver = normalize_module_path_to_dotted(input_query, repo_root=str(root))

        identity_resolution = query_helpers.resolve_module_identity(
            normalized_for_resolver,
            mod_path_to_id,
            mod_id_to_path,
        )
        if identity_resolution["status"] == "resolved":
            resolved_module = identity_resolution["module"]
            unavailable = query_helpers.module_truth_unavailable(state, resolved_module)
            if unavailable:
                return json.dumps(unavailable, indent=2)
            if resolved_module in live_modules:
                module_name = resolved_module
            else:
                return f"Module '{input_query}' not found in the project graph."
        elif (
            identity_resolution["status"] == "not_found"
            and identity_resolution.get("similar_candidates")
        ):
            return json.dumps(
                {
                    "status": "not_found",
                    "query": input_query,
                    "similar_candidates": identity_resolution["similar_candidates"],
                    "data_source": "active_module_registry",
                },
                indent=2,
            )
        else:
            return f"Module '{input_query}' not found in the project graph."

    inbound = {}
    outbound = {}
    dependency_source = "live_canonical_graph"
    graph = getattr(state, "dependency_graph", None)
    if graph is None:
        return "Error: Canonical LIVE dependency graph is unavailable. Run analyze_project first."
    hard_edges = getattr(graph, "hard_edges", {}) if graph else {}
    soft_edges = getattr(graph, "soft_edges", {}) if graph else {}

    def relationship(source: str, target: str) -> dict:
        classes = []
        if target in set(hard_edges.get(source, set())):
            classes.append("hard_dependency")
        if target in set(soft_edges.get(source, set())):
            classes.append("soft_dependency")
        return {
            "dep_types": classes,
            "weight": 1,
            "data_source": "live_canonical_graph",
        }

    targets = set(hard_edges.get(module_name, set())) | set(
        soft_edges.get(module_name, set())
    )
    outbound = {
        target: relationship(module_name, target)
        for target in sorted(targets)
    }
    sources = set(hard_edges) | set(soft_edges)
    inbound = {
        source: relationship(source, module_name)
        for source in sorted(sources)
        if module_name
        in (
            set(hard_edges.get(source, set()))
            | set(soft_edges.get(source, set()))
        )
    }

    if graph is not None:
        hard_edges = getattr(graph, "hard_edges", {}) or {}
        live_fan_out = len(hard_edges.get(module_name, set()))
        live_fan_in = sum(
            1 for _, targets in hard_edges.items() if module_name in targets
        )
        topo = getattr(state, "topology_analytics", {}) or {}
        topo_freshness = getattr(state, "topology_metrics_state", "deferred")

        metrics = {
            "fan_in": live_fan_in,
            "fan_out": live_fan_out,
        }
        degree_metrics_source = "live_canonical_graph"

        if topo_freshness == "fresh" and isinstance(topo, dict):
            has_any_topo = False
            for topo_key, metric_field in [
                ("pagerank", "pagerank"),
                ("betweenness", "betweenness"),
                ("hub_scores", "hub_score"),
                ("authority_scores", "authority_score"),
                ("bridge_scores", "bridge_score"),
            ]:
                val_map = topo.get(topo_key, {})
                if isinstance(val_map, dict) and module_name in val_map:
                    metrics[metric_field] = val_map[module_name]
                    has_any_topo = True

            if "module_risk" in topo and isinstance(topo["module_risk"], dict) and module_name in topo["module_risk"]:
                metrics["risk_score"] = topo["module_risk"][module_name]
                has_any_topo = True

            metrics_source = "live_canonical_topology" if has_any_topo else "live_canonical_graph"
        elif topo_freshness == "stale":
            metrics_source = "stale_topology_analytics"
        else:
            metrics_source = "deferred_topology_analytics"

        if mod_path_to_id.get(module_name):
            metrics["module_idx"] = mod_path_to_id[module_name]

        cached_analytics = getattr(state, "cached_analytics", {}) or {}
        cached_freshness = getattr(state, "cached_analytics_state", "deferred")
        if cached_freshness == "fresh" and isinstance(cached_analytics, dict):
            if "module_layers" in cached_analytics and module_name in cached_analytics["module_layers"]:
                metrics["layer"] = cached_analytics["module_layers"][module_name]
            if "visibility" in cached_analytics and module_name in cached_analytics["visibility"]:
                metrics["visibility"] = cached_analytics["visibility"][module_name]
            if "export_degree" in cached_analytics and module_name in cached_analytics["export_degree"]:
                metrics["export_degree"] = cached_analytics["export_degree"][module_name]

    else:
        metrics = {"fan_in": len(inbound), "fan_out": len(outbound)}
        canonical_metrics = getattr(state, "metrics", {}) or {}
        if isinstance(canonical_metrics.get(module_name), dict):
            metrics.update(canonical_metrics[module_name])
        metrics_source = "deferred_topology_analytics"
        degree_metrics_source = "canonical_module_metrics"

    common_result = {
        "module": module_name,
        "metrics": metrics,
        "metrics_source": metrics_source,
        "degree_metrics_source": degree_metrics_source,
        "dependency_data_source": dependency_source,
        "state_freshness": query_helpers.build_state_freshness(
            root, state, target_module=module_name, engine=engine
        ),
    }
    result = {
        **common_result,
        "dependencies_inbound_who_calls_me": _dependency_collection_view(
            sorted(inbound.items()),
            max_items,
            compact,
        ),
        "dependencies_outbound_who_i_call": _dependency_collection_view(
            sorted(outbound.items()),
            max_items,
            compact,
        ),
    }

    if fields is not None:
        allowed_fields = set(result)
        unknown_fields = sorted(set(fields) - allowed_fields)
        if unknown_fields:
            return json.dumps(
                {
                    "error": "Unsupported fields for get_module_context",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                },
                indent=2,
            )
        result = {field: result[field] for field in fields}

    return json.dumps(result, indent=2)
