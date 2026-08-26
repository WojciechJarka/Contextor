import json
from pathlib import Path

from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import report_helpers


def _resolve_cluster_ids(
    cluster: dict,
    module_names: dict,
    artifact_names: dict,
) -> dict:
    """Make one analytics cluster directly readable by an LLM."""
    resolved = dict(cluster)
    resolved["modules"] = [
        module_names.get(str(item), str(item))
        for item in cluster.get("modules", [])
    ]
    resolved["shared_artifact_keys"] = [
        artifact_names.get(str(item), str(item))
        for item in cluster.get("shared_artifact_keys", [])
    ]
    resolved["ids_resolved"] = True
    return resolved


def get_layer_isolation(
    repo_path: str,
    layer_name: str,
    max_clusters: int | None = 8,
    max_boundary_violations: int | None = 10,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    raw_layer = str(layer_name).strip().replace("\\", "/").strip("/")
    candidate = Path(raw_layer).expanduser()
    if candidate.is_absolute():
        try:
            raw_layer = candidate.resolve().relative_to(root).as_posix()
        except ValueError:
            return f"Error: Layer path '{candidate}' is outside the repository."
    requested_layer = raw_layer.replace("/", ".")
    normalized_layer_name = requested_layer.rsplit(".", 1)[-1]

    ga_path = report_helpers.get_canonical_report(root, f"{repo_name}_{normalized_layer_name}_graph_analytics.json")
    if not ga_path:
        engine = mcp_runtime.get_or_init_engine(root)
        if engine and engine.state.dependency_graph:
            graph = engine.state.dependency_graph
            layer_modules = {
                name
                for name in engine.state.modules
                if name == requested_layer or name.startswith(requested_layer + ".")
            }
            if layer_modules:
                boundary_edges = []
                dependency_types = {"hard": 0, "soft": 0}
                for edge_type, edge_map in (
                    ("hard", graph.hard_edges),
                    ("soft", graph.soft_edges),
                ):
                    for source, targets in edge_map.items():
                        for target in targets:
                            source_inside = source in layer_modules
                            target_inside = target in layer_modules
                            if source_inside:
                                dependency_types[edge_type] += 1
                            if source_inside != target_inside:
                                boundary_edges.append(
                                    {
                                        "from": source,
                                        "to": target,
                                        "edge_type": edge_type,
                                        "direction": "outbound" if source_inside else "inbound",
                                    }
                                )
                items, total, truncated = query_helpers.bounded_items(
                    sorted(
                        boundary_edges,
                        key=lambda item: (
                            item["from"], item["to"], item["edge_type"]
                        ),
                    ),
                    max_boundary_violations,
                )
                _bv_ev_limit = 3 if max_boundary_violations is None else min(3, max_boundary_violations)
                bv_ev = items[:_bv_ev_limit]
                if compact:
                    cluster_view = {
                        "total": 0,
                        "truncated": False,
                        "available": False,
                        "evidence": [],
                    }
                    bv_view = {
                        "total": total,
                        "truncated": total > len(bv_ev),
                        "evidence_scope": "cross_boundary_edges_not_policy_violations",
                        "evidence": bv_ev,
                    }
                    if bv_view["truncated"]:
                        bv_view["expand"] = {"compact": False, "max_boundary_violations": None}
                else:
                    cluster_view = {
                        "total": 0,
                        "truncated": False,
                        "available": False,
                        "items": [],
                    }
                    bv_view = {
                        "total": total,
                        "truncated": truncated,
                        "evidence_scope": "cross_boundary_edges_not_policy_violations",
                        "items": items,
                    }
                result = {
                    "layer": requested_layer,
                    "report_layer": normalized_layer_name,
                    "data_source": "live_canonical_graph",
                    "module_count": len(layer_modules),
                    "clusters": cluster_view,
                    "dependency_types": dependency_types,
                    "boundary_violations": bv_view,
                }
                if fields is not None:
                    unknown_fields = sorted(set(fields) - set(result))
                    if unknown_fields:
                        return json.dumps(
                            {
                                "error": "Unsupported fields for get_layer_isolation",
                                "unknown_fields": unknown_fields,
                                "allowed_fields": sorted(result),
                            },
                            indent=2,
                        )
                    result = {field: result[field] for field in fields}
                return json.dumps(result, indent=2)
        summary_path = report_helpers.get_canonical_report(root, f"{repo_name}_summary.json")
        if not summary_path:
            return f"Error: No layer report found for '{normalized_layer_name}' and no global summary found."
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            for layer in summary.get("layer_index", []):
                if layer.get("layer") == normalized_layer_name:
                    return json.dumps(layer, indent=2)
            return (
                f"Layer '{requested_layer}' has no dedicated report and is not "
                "present in the global top-level layer index. Run analyze_layer "
                "for this nested layer first."
            )
        except Exception as e:
            return f"Error reading fallback layer info: {e}"

    try:
        ga = json.loads(ga_path.read_text(encoding="utf-8"))
        _, id_to_name, _, artifact_id_to_name = query_helpers.read_registries(root)
        modules = ga.get("modules", {})
        matrix = ga.get("module_dependency_matrix", {})
        _LAYER_ORDER = ["tests", "ui", "cli", "contract", "engine", "runtime", "adapter"]
        _LAYER_RANK = {l: i for i, l in enumerate(_LAYER_ORDER)}

        def _is_violation(src_layer: str, tgt_layer: str) -> bool:
            """A violation occurs when a lower-ranked layer calls a higher-ranked one."""
            src_rank = _LAYER_RANK.get(src_layer, -1)
            tgt_rank = _LAYER_RANK.get(tgt_layer, -1)
            if src_rank < 0 or tgt_rank < 0:
                return False
            return src_rank > tgt_rank

        boundary_violations = []
        for src_id, targets in matrix.items():
            src_name = id_to_name.get(src_id, src_id)
            src_layer = modules.get(src_name, {}).get("layer", "")
            if not src_layer:
                continue
            for tgt_id in targets:
                tgt_name = id_to_name.get(tgt_id, tgt_id)
                if tgt_name == src_name:
                    continue
                tgt_layer = modules.get(tgt_name, {}).get("layer", "")
                if not tgt_layer:
                    continue
                if _is_violation(src_layer, tgt_layer):
                    boundary_violations.append({
                        "from": src_name,
                        "from_layer": src_layer,
                        "to": tgt_name,
                        "to_layer": tgt_layer,
                    })

        clusters, cluster_count, clusters_truncated = query_helpers.bounded_items(
            ga.get("shared_usage_clusters", []), max_clusters
        )
        clusters = [
            _resolve_cluster_ids(cluster, id_to_name, artifact_id_to_name)
            for cluster in clusters
        ]
        violations, violation_count, violations_truncated = query_helpers.bounded_items(
            boundary_violations, max_boundary_violations
        )
        _cl_ev_limit = 3 if max_clusters is None else min(3, max_clusters)
        _bv_ev_limit = 3 if max_boundary_violations is None else min(3, max_boundary_violations)
        if compact:
            cl_ev = clusters[:_cl_ev_limit]
            cluster_collection = {
                "total": cluster_count,
                "truncated": cluster_count > len(cl_ev),
                "evidence": cl_ev,
            }
            if cluster_collection["truncated"]:
                cluster_collection["expand"] = {"compact": False, "max_clusters": None}
            bv_ev = violations[:_bv_ev_limit]
            violation_collection = {
                "total": violation_count,
                "truncated": violation_count > len(bv_ev),
                "evidence": bv_ev,
            }
            if violation_collection["truncated"]:
                violation_collection["expand"] = {"compact": False, "max_boundary_violations": None}
        else:
            cluster_collection = {
                "total": cluster_count,
                "truncated": clusters_truncated,
                "items": clusters,
            }
            violation_collection = {
                "total": violation_count,
                "truncated": violations_truncated,
                "items": violations,
            }
        result = {
            "layer": requested_layer,
            "report_layer": normalized_layer_name,
            "data_source": str(ga_path),
            "module_count": ga.get("module_count", 0),
            "clusters": cluster_collection,
            "dependency_types": ga.get("dependency_type_breakdown", {}),
            "boundary_violations": violation_collection,
        }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for get_layer_isolation",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting layer isolation: {e}"
