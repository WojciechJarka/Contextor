import json
from pathlib import Path

from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime


def _static_test_reachability(
    target: str,
    hard_edges: dict,
    soft_edges: dict,
    test_modules: set[str],
    module_to_id: dict[str, str],
    max_depth: int = 6,
) -> list[dict]:
    """Return shortest static dependency paths from tests to one module."""
    reverse: dict[str, set[str]] = {}
    for edge_map in (hard_edges, soft_edges):
        for source, targets in edge_map.items():
            for destination in targets:
                reverse.setdefault(str(destination), set()).add(str(source))

    paths = {target: [target]}
    queue = [target]
    while queue:
        current = queue.pop(0)
        current_path = paths[current]
        if len(current_path) - 1 >= max_depth:
            continue
        for predecessor in sorted(reverse.get(current, set())):
            if predecessor in paths:
                continue
            paths[predecessor] = [predecessor, *current_path]
            queue.append(predecessor)

    return [
        {
            "module_id": module_to_id.get(module),
            "module": module,
            "distance": len(paths[module]) - 1,
            "evidence_path": paths[module],
            "evidence_scope": "static_dependency_reachability",
        }
        for module in sorted(test_modules)
        if module in paths and module != target
    ]


def get_file_edit_context(
    repo_path: str,
    file_path: str = "",
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
    mode: str | None = None,
    target: str | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    # Validate mode explicitly
    if mode is not None and mode != "minimal":
        return json.dumps(
            {
                "error": f"Unsupported mode '{mode}'. Allowed modes are: None (legacy), 'minimal'.",
                "allowed_modes": [None, "minimal"],
            },
            indent=2,
        )

    # Read registries & catalog for canonical resolution
    from contextor.core.report_query import IndexCatalog, catalog_from_registry, resolve_index_query

    mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
    catalog = catalog_from_registry(str(root))
    if not catalog.modules and mod_id_to_path:
        catalog = IndexCatalog(
            modules=mod_id_to_path,
            artifacts=art_id_to_path,
            module_paths={name: name.replace(".", "/") + ".py" for name in mod_path_to_id},
            recovered_modules={},
            recovered_artifacts={},
        )

    # Handle input target resolution and canonical conflict detection
    effective_file = (file_path or "").strip()
    effective_target = (target or "").strip()

    if effective_file and effective_target:
        res_file = resolve_index_query(effective_file, catalog, repo_root=str(root))
        res_target = resolve_index_query(effective_target, catalog, repo_root=str(root))
        matches_file = res_file.get("matches", [])
        matches_target = res_target.get("matches", [])
        if matches_file and matches_target:
            m_f = matches_file[0]
            m_t = matches_target[0]
            if (
                (m_f.get("id") != m_t.get("id"))
                or (m_f.get("name") != m_t.get("name"))
                or (m_f.get("kind") != m_t.get("kind"))
            ):
                return json.dumps(
                    {
                        "error": "Conflicting 'file_path' and 'target' arguments provided. Resolved to different canonical targets.",
                        "file_path": effective_file,
                        "file_path_resolved": {"id": m_f.get("id"), "name": m_f.get("name"), "kind": m_f.get("kind")},
                        "target": effective_target,
                        "target_resolved": {"id": m_t.get("id"), "name": m_t.get("name"), "kind": m_t.get("kind")},
                    },
                    indent=2,
                )
        elif effective_file != effective_target:
            # Fallback string comparison when unindexed
            try:
                norm_file = Path(effective_file).resolve().relative_to(root).as_posix()
            except ValueError:
                norm_file = effective_file.replace("\\", "/").lstrip("./")
            try:
                norm_target = Path(effective_target).resolve().relative_to(root).as_posix()
            except ValueError:
                norm_target = effective_target.replace("\\", "/").lstrip("./")
            if norm_file != norm_target and norm_file.replace("/", ".").rstrip(".py") != norm_target:
                return json.dumps(
                    {
                        "error": "Conflicting 'file_path' and 'target' arguments provided. Provide only one.",
                        "file_path": file_path,
                        "target": target,
                    },
                    indent=2,
                )

    query_input = effective_target or effective_file
    if not query_input:
        return json.dumps({"error": "Either 'target' or 'file_path' must be provided."}, indent=2)

    # -------------------------------------------------------------------------
    # MINIMAL PRE-EDIT PROJECTION (mode == "minimal")
    # -------------------------------------------------------------------------
    if mode == "minimal":
        try:
            from contextor.core.analysis.incremental.graph_ops import calculate_affected_set

            resolution = resolve_index_query(query_input, catalog, repo_root=str(root))

            if not resolution.get("matches"):
                return json.dumps(
                    {
                        "status": "not_found",
                        "target": query_input,
                        "reason": resolution.get("reason", "no_matching_entry"),
                        "suggestions": resolution.get("suggestions", []),
                    },
                    indent=2,
                )

            top = resolution["matches"][0]
            kind = top.get("kind")

            # Handling artifact / symbol input
            if kind == "artifact":
                art_name = top["name"]
                art_id = top["id"]
                definer_mod = art_name.split("::", 1)[0]
                definer_file = (catalog.module_paths or {}).get(definer_mod) or definer_mod.replace(".", "/") + ".py"
                return json.dumps(
                    {
                        "target": query_input,
                        "resolved_as": "artifact",
                        "artifact": art_name,
                        "artifact_id": art_id,
                        "definer_module": definer_mod,
                        "definer_file": definer_file,
                        "suggested_next_tool": "get_artifact_blast_radius",
                        "warnings": [
                            "Target resolved to an artifact/symbol rather than a module. "
                            "Use get_artifact_blast_radius for symbol-level consumption."
                        ],
                    },
                    indent=2,
                )

            module_name = top["name"]
            module_id = top["id"]
            file_path_resolved = (catalog.module_paths or {}).get(module_name) or module_name.replace(".", "/") + ".py"

            engine = mcp_runtime.get_or_init_engine(root)
            if not engine or getattr(engine.state, "resync_required", False):
                return json.dumps(
                    {
                        "status": "unavailable",
                        "reason": "No usable canonical LIVE state. Run analyze_project first.",
                    },
                    indent=2,
                )
            unavailable = query_helpers.module_truth_unavailable(engine.state, module_name)
            if unavailable:
                return json.dumps(unavailable, indent=2)
            live_graph = getattr(engine.state, "dependency_graph", None)
            if live_graph is None:
                return json.dumps(
                    {
                        "status": "unavailable",
                        "reason": "Canonical LIVE dependency graph is unavailable. Run analyze_project first.",
                    },
                    indent=2,
                )

            direct_consumers = []
            transitive_count = 0

            if live_graph:
                consumer_modules = {
                    src
                    for edge_map in (live_graph.hard_edges, live_graph.soft_edges)
                    for src, targets in edge_map.items()
                    if module_name in targets
                }
                direct_consumers = sorted(consumer_modules)
                affected = calculate_affected_set(module_name, new_graph=live_graph)
                transitive_count = len(affected - {module_name})

            reachability_hard = getattr(live_graph, "hard_edges", {}) if live_graph else {}
            reachability_soft = getattr(live_graph, "soft_edges", {}) if live_graph else {}
            graph_modules = set(reachability_hard) | set(reachability_soft)
            for edge_map in (reachability_hard, reachability_soft):
                for tgts in edge_map.values():
                    graph_modules.update(tgts)

            test_modules = {
                name
                for name in graph_modules
                if name.startswith("tests.") or name == "tests" or name.rsplit(".", 1)[-1].startswith("test_")
            }
            if engine and getattr(engine.state, "cached_analytics_state", "deferred") == "fresh":
                cached = getattr(engine.state, "cached_analytics", {}) or {}
                canonical_layers = cached.get("module_layers", {}) if isinstance(cached, dict) else {}
                test_modules.update(
                    name for name, layer in canonical_layers.items() if layer == "tests"
                )

            mod_path_to_id = {name: mid for mid, name in catalog.modules.items()}
            tests_covering = _static_test_reachability(
                module_name,
                reachability_hard,
                reachability_soft,
                test_modules,
                mod_path_to_id,
            )

            sample_limit = 5 if max_items is None or max_items == 30 else max_items
            sample_consumers = direct_consumers[:sample_limit]
            test_names = [t["module"] for t in tests_covering]
            sample_tests = test_names[:sample_limit]

            warnings = []
            layer = "unknown"
            if engine:
                cached_analytics = getattr(engine.state, "cached_analytics", {}) or {}
                cached_state = getattr(engine.state, "cached_analytics_state", "deferred")
                if cached_state == "fresh":
                    module_layers = cached_analytics.get("module_layers", {}) if isinstance(cached_analytics, dict) else {}
                    if module_name in module_layers:
                        layer = module_layers[module_name]
                    else:
                        warnings.append(f"Canonical module_layers entry not found for '{module_name}'.")

            risk_score = None
            if engine:
                topo = getattr(engine.state, "topology_analytics", {}) or {}
                topo_state = getattr(engine.state, "topology_metrics_state", "deferred")
                if topo_state == "fresh":
                    module_risk_map = topo.get("module_risk", {}) if isinstance(topo, dict) else {}
                    if module_name in module_risk_map:
                        risk_score = module_risk_map[module_name]
                    else:
                        warnings.append(f"Canonical module_risk not computed for '{module_name}'.")

            layer_guard = {"available": False}
            if engine:
                if cached_state == "fresh":
                    from contextor.core.validator.rules import FORBIDDEN_LAYER_RULES, FORBIDDEN_PREFIX_RULES

                    forbidden_outbound_layers = [r[1] for r in FORBIDDEN_LAYER_RULES if r[0] == layer]
                    forbidden_outbound_prefixes = [r[1] for r in FORBIDDEN_PREFIX_RULES if r[0] == layer]
                    outbound_rules_defined = bool(forbidden_outbound_layers or forbidden_outbound_prefixes)

                    raw_violations = cached_analytics.get("layer_violations", []) if isinstance(cached_analytics, dict) else []
                    outbound_violations = [
                        v for v in raw_violations
                        if len(v.get("nodes", [])) >= 2 and v["nodes"][0] == module_name
                    ]
                    inbound_violations = [
                        v for v in raw_violations
                        if len(v.get("nodes", [])) >= 2 and v["nodes"][1] == module_name
                    ]

                    all_module_violations = []
                    for v in outbound_violations:
                        all_module_violations.append(
                            {
                                "direction": "outbound",
                                "kind": v.get("kind", "LAYER"),
                                "source_module": v["nodes"][0],
                                "target_module": v["nodes"][1],
                                "message": v.get("message", ""),
                            }
                        )
                    for v in inbound_violations:
                        all_module_violations.append(
                            {
                                "direction": "inbound",
                                "kind": v.get("kind", "LAYER"),
                                "source_module": v["nodes"][0],
                                "target_module": v["nodes"][1],
                                "message": v.get("message", ""),
                            }
                        )

                    sample_violations, total_v, truncated_v = query_helpers.bounded_items(
                        all_module_violations, 5
                    )

                    layer_guard = {
                        "available": True,
                        "outbound_rules_defined": outbound_rules_defined,
                        "outbound_violation_count": len(outbound_violations),
                        "inbound_violation_count": len(inbound_violations),
                        "violations": {
                            "total": total_v,
                            "items": sample_violations,
                            "truncated": truncated_v,
                        },
                    }
                    if forbidden_outbound_layers:
                        layer_guard["forbidden_outbound_layers"] = forbidden_outbound_layers
                    if forbidden_outbound_prefixes:
                        layer_guard["forbidden_outbound_prefixes"] = forbidden_outbound_prefixes
                    if outbound_rules_defined or len(outbound_violations) > 0 or len(inbound_violations) > 0:
                        layer_guard["suggested_next_tool"] = "get_layer_isolation"
                else:
                    layer_guard = {
                        "available": False,
                        "reason": f"Cached analytics state is '{cached_state}'.",
                    }

            live_revision = mcp_runtime._live_engine_revisions.get(str(root)) if engine else None

            return json.dumps(
                {
                    "target": query_input,
                    "resolved_as": "module",
                    "module": module_name,
                    "module_id": module_id,
                    "file": file_path_resolved,
                    "live_revision": live_revision,
                    "layer": layer,
                    "risk_score": risk_score,
                    "layer_guard": layer_guard,
                    "consumers": {
                        "direct_count": len(direct_consumers),
                        "transitive_count": transitive_count,
                        "sample": sample_consumers,
                        "truncated": len(direct_consumers) > len(sample_consumers),
                    },
                    "tests_covering": {
                        "count": len(test_names),
                        "sample": sample_tests,
                        "truncated": len(test_names) > len(sample_tests),
                    },
                    "warnings": warnings,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": f"Error in minimal pre-edit context: {e}"}, indent=2)

    # -------------------------------------------------------------------------
    # LEGACY GET_FILE_EDIT_CONTEXT PATH (mode is None or unsupported mode)
    # -------------------------------------------------------------------------
    # Deriving module name from file path
    target_path = Path(query_input).expanduser()
    if target_path.is_absolute():
        try:
            rel_path = target_path.relative_to(root)
        except ValueError:
            rel_path = target_path
    else:
        rel_path = target_path
        target_path = root / target_path

    parts = list(rel_path.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts.pop()

    module_name = ".".join(parts)
    
    engine = mcp_runtime.get_or_init_engine(root)
    if not engine or getattr(engine.state, "resync_required", False):
        return "Error: No usable canonical LIVE state. Run analyze_project first."
        
    try:
        state = engine.state
        unavailable = query_helpers.module_truth_unavailable(state, module_name)
        if unavailable:
            return json.dumps(unavailable, indent=2)
        state_metrics = getattr(state, "metrics", {}) or {}
        candidate_metrics = state_metrics.get(module_name, {}) if isinstance(state_metrics, dict) else {}
        mod_info = candidate_metrics if isinstance(candidate_metrics, dict) else {}
        cached_analytics = getattr(state, "cached_analytics", {}) or {}
        if getattr(state, "cached_analytics_state", "deferred") == "fresh":
            module_layers = cached_analytics.get("module_layers", {}) or {}
            if module_name in module_layers:
                mod_info = {**mod_info, "layer": module_layers[module_name]}
        
        risk_score = None
        topology = getattr(state, "topology_analytics", {}) or {}
        if getattr(state, "topology_metrics_state", "deferred") == "fresh":
            risk_score = (topology.get("module_risk", {}) or {}).get(module_name)
        
        # We must read registries OUTSIDE the transaction block to avoid Resource Deadlock
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
        module_to_id = {
            **{path: module_id for module_id, path in mod_id_to_path.items()},
            **mod_path_to_id,
        }
        artifact_name_to_id = {
            **{name: artifact_id for artifact_id, name in art_id_to_path.items()},
            **art_path_to_id,
        }
        live_module = state.modules.get(module_name)
        mod_id = mod_path_to_id.get(module_name) or getattr(live_module, "module_id", None)
        if not mod_id:
            if live_module is None:
                return f"Error: Module '{module_name}' is not present in canonical LIVE state."
            mod_id = module_name
            
        imports = []
        consumers = []
        dependency_data_source = "live_canonical_graph"
        artifact_data_source = "live_registry_and_symbol_state"
        live_graph = state.dependency_graph
        reachability_hard = {}
        reachability_soft = {}
        if module_name in state.modules and live_graph:
            reachability_hard = live_graph.hard_edges
            reachability_soft = live_graph.soft_edges
            target_modules = set(live_graph.hard_edges.get(module_name, set()))
            target_modules.update(live_graph.soft_edges.get(module_name, set()))
            imports = [module_to_id.get(target, target) for target in sorted(target_modules)]
            consumer_modules = {
                source
                for edge_map in (live_graph.hard_edges, live_graph.soft_edges)
                for source, targets in edge_map.items()
                if module_name in targets
            }
            consumers = [module_to_id.get(source, source) for source in sorted(consumer_modules)]
            dependency_data_source = "live_canonical_graph"
                        
        # Resolve public API artifact IDs to human-readable names so an
        # LLM does not need a separate lookup_index_entries call.
        public_api = {}
        unresolved_public_api_ids = []
        if module_name in state.artifacts:
            prefix = module_name + "::"
            module_artifacts = state.artifacts[module_name]
            symbols = module_artifacts.get("symbols", {}) or {}
            for local_name in sorted(query_helpers.canonical_symbol_catalog(module_artifacts)):
                leaf = local_name.rsplit(".", 1)[-1]
                if leaf.startswith("_") and not (
                    leaf.startswith("__") and leaf.endswith("__")
                ):
                    continue
                full_name = prefix + local_name
                artifact_key = str(artifact_name_to_id.get(full_name, full_name))
                public_api[artifact_key] = full_name
        
        graph_modules = set(reachability_hard) | set(reachability_soft)
        graph_modules.update(
            target
            for edge_map in (reachability_hard, reachability_soft)
            for targets in edge_map.values()
            for target in targets
        )
        test_modules = {
            name
            for name in graph_modules
            if name.startswith("tests.")
            or name == "tests"
            or name.rsplit(".", 1)[-1].startswith("test_")
        }
        if getattr(state, "cached_analytics_state", "deferred") == "fresh":
            canonical_layers = cached_analytics.get("module_layers", {}) if isinstance(cached_analytics, dict) else {}
            test_modules.update(
                name for name, layer in canonical_layers.items() if layer == "tests"
            )
        tests_covering = _static_test_reachability(
            module_name,
            reachability_hard,
            reachability_soft,
            test_modules,
            {
                **{path: module_id for module_id, path in mod_id_to_path.items()},
                **mod_path_to_id,
            },
        )

        public_api_items, public_api_total, public_api_truncated = query_helpers.bounded_items(
            sorted(public_api.items()), max_items
        )
        import_items, imports_total, imports_truncated = query_helpers.bounded_items(
            sorted(imports), max_items
        )
        consumer_items, consumers_total, consumers_truncated = query_helpers.bounded_items(
            sorted(consumers), max_items
        )
        test_items, tests_total, tests_truncated = query_helpers.bounded_items(
            tests_covering, max_items
        )
        
        common_result = {
            "file": file_path,
            "file_exists": target_path.is_file(),
            "module": module_name,
            "module_id": mod_id,
            "layer": mod_info.get("layer", "unknown"),
            "entrypoint": mod_info.get("entrypoint", False),
            "risk_score": risk_score,
            "dependency_data_source": dependency_data_source,
            "artifact_data_source": artifact_data_source,
        }
        full_result = {
            **common_result,
            "public_api": {
                "items": dict(public_api_items),
                "total": public_api_total,
                "truncated": public_api_truncated,
                "unresolved_ids": sorted(set(unresolved_public_api_ids)),
                "unresolved_total": len(set(unresolved_public_api_ids)),
            },
            "imports": {
                "items": [
                    {
                        "module_id": mod_path_to_id.get(item, item),
                        "module": mod_id_to_path.get(item, item),
                    }
                    for item in import_items
                ],
                "total": imports_total,
                "truncated": imports_truncated,
            },
            "consumers": {
                "items": [
                    {
                        "module_id": mod_path_to_id.get(item, item),
                        "module": mod_id_to_path.get(item, item),
                    }
                    for item in consumer_items
                ],
                "total": consumers_total,
                "truncated": consumers_truncated,
            },
            "tests_covering": {
                "available": tests_total > 0,
                "total": tests_total,
                "truncated": tests_truncated,
                "evidence_scope": "static_dependency_reachability",
                "max_depth": 6,
                "tests": test_items,
            }
        }

        compact_result = {
            **common_result,
            "public_api": {
                key: full_result["public_api"][key]
                for key in ("total", "truncated", "unresolved_total")
            },
            "imports": {
                key: full_result["imports"][key]
                for key in ("total", "truncated")
            },
            "consumers": {
                key: full_result["consumers"][key]
                for key in ("total", "truncated")
            },
            "tests_covering": {
                key: full_result["tests_covering"][key]
                for key in ("available", "total", "truncated", "evidence_scope", "max_depth")
            },
        }

        result = compact_result if compact else full_result

        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps(
                    {
                        "error": "Unsupported fields for get_file_edit_context",
                        "unknown_fields": unknown_fields,
                        "allowed_fields": sorted(allowed_fields),
                    },
                    indent=2,
                )
            result = {field: result[field] for field in fields}

        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting file edit context: {e}"
