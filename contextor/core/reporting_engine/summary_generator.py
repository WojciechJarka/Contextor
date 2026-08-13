from datetime import datetime

from contextor.core.graph.cycles import detect_cycles
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.graph.thresholds import get_thresholds
from contextor.core.hotspots import detect_hotspots
from contextor.core.reporting_engine.debt import compute_debt
from contextor.core.validator.collisions import validate_name_collisions
from .formatting import _compute_status
from .graph_aggregators import _build_undirected_graph, _connected_components
from .refactor_planner import _compute_refactor_plan
from .risk_signals import (
    _compute_inspection_targets, 
    _compute_module_risk, 
    _compute_risk_summary, 
    _compute_soft_dependencies
)
from .collisions_generator import generate_collisions_report


def _sanity_check_reports(
    summary: dict,
    artifacts: dict,
    compact: dict,
) -> list[str]:
    warnings = []

    summary_nodes = summary.get("metrics", {}).get("nodes", None)
    artifact_modules = artifacts.get("module_count", None)
    if summary_nodes is not None and artifact_modules is not None:
        if summary_nodes != artifact_modules:
            warnings.append(
                f"nodes mismatch: summary.metrics.nodes={summary_nodes} "
                f"!= artifacts.module_count={artifact_modules}"
            )

    full_count = artifacts.get("artifact_count", None)
    compact_count = compact.get("artifact_count", None)
    if full_count is not None and compact_count is not None:
        if full_count != compact_count:
            warnings.append(
                f"artifact_count mismatch: artifacts.json={full_count} "
                f"!= artifacts_compact.json={compact_count}"
            )

    return warnings


def _compute_import_profile(modules: dict) -> dict:
    profile = {}
    for module_id, module in modules.items():
        total = len(module.imports)
        local = sum(1 for imp in module.imports if imp.is_local)
        profile[module_id] = {
            "global_imports": total - local,
            "local_imports": local,
        }
    return profile


def _compute_action_items(
    cycles: list,
    real_collisions: list,
    hotspots: list | None = None,
    isolated_modules: list | None = None,
) -> list[str]:
    items = []

    if cycles:
        worst = cycles[0]
        items.append(
            f"CRITICAL: Eliminate import cycle {' -> '.join(worst)} ({len(worst)} modules)"
        )

    critical_collisions = [
        c for c in real_collisions if getattr(c, "severity", "warning") == "critical"
    ]
    if critical_collisions:
        c = critical_collisions[0]
        name = getattr(c, "message", "").split("'")[1] if "'" in getattr(c, "message", "") else "?"
        items.append(
            f"BROKEN: Fix structural collision '{name}' "
            f"({len(critical_collisions)} critical collision(s) total)"
        )
    elif real_collisions:
        total = len(real_collisions)
        items.append(
            f"BROKEN: Resolve {total} name collision(s) (duplicate public API across modules)"
        )

    if hotspots:
        outbound = [h for h in hotspots if h.get("type") == "OUTBOUND_HOTSPOT"]
        if outbound:
            top = outbound[0]
            items.append(
                f"WARNING: Refactor '{top['module']}' "
                f"(out_degree={top.get('out_degree', '?')}, "
                f"type=OUTBOUND_HOTSPOT)"
            )

    if isolated_modules:
        _ENTRYPOINT_PATTERNS = ("cli_", "__main__", "main", "scripts.", "entrypoint", "entry_")

        entrypoints = [
            m for m in isolated_modules
            if any(
                m == pat or m.endswith("." + pat) or m.startswith(pat)
                or ("."+pat) in m
                for pat in _ENTRYPOINT_PATTERNS
            )
        ]
        dead_code = [m for m in isolated_modules if m not in entrypoints]

        if entrypoints:
            items.append(
                f"INFO: {len(entrypoints)} isolated CLI/entry-point module(s) "
                f"(expected, no action needed): {', '.join(entrypoints[:3])}"
            )
        if dead_code:
            items.append(
                f"INFO: {len(dead_code)} isolated module(s) with no connections "
                f"— remove or integrate: {', '.join(dead_code[:3])}"
            )

    return items[:5]


def generate_summary_report(
    metrics: dict,
    cycles: list,
    debt: dict,
    collisions: list | None = None,
    hotspots: list | None = None,
    skipped_files: list | None = None,
    report_header: dict | None = None,
    layer_index: list[dict] | None = None,
) -> dict:
    collisions = collisions or []
    hotspots = hotspots or []
    skipped_files = skipped_files or []

    real_collisions = [c for c in collisions if not getattr(c, "is_identical", False)]
    active_hotspots = [h for h in hotspots if h.get("type") not in ("ISOLATED", "NORMAL")]
    isolated_modules = [
        h["module"]
        for h in hotspots
        if h.get("type") == "ISOLATED" and not h["module"].endswith("__init__")
    ]

    top_hotspots = [
        {
            "module": h["module"],
            "type": h["type"],
            "out_degree": h.get("out_degree", 0),
            "in_degree": h.get("in_degree", 0),
            "score": h.get("score", 0.0),
        }
        for h in active_hotspots[:5]
    ]

    status = _compute_status(cycles, real_collisions, active_hotspots)
    action_items = _compute_action_items(
        cycles,
        real_collisions,
        hotspots=active_hotspots,
        isolated_modules=isolated_modules,
    )

    report = {
        "generated_at": datetime.now().isoformat(),
        "status": status,
        "metrics": metrics,
        "cycle_count": len(cycles),
        "collision_count": len(real_collisions),
        "debt_summary": {
            "total_score": debt.get("score", 0),
            "hotspot_count": len(active_hotspots),
            "isolated_count": len(isolated_modules),
        },
        "top_hotspots": top_hotspots,
        "action_items": action_items,
    }

    if report_header:
        report["report_header"] = report_header

    if layer_index:
        report["layer_index"] = layer_index

    if skipped_files:
        report["skipped_files"] = [
            {
                "path": item.path,
                "reason": item.reason,
                "line_number": getattr(item, "line_number", None),
                "column_number": getattr(item, "column_number", None),
            }
            for item in skipped_files
        ]
        report["skipped_file_count"] = len(skipped_files)

    return report


def generate_report(
    project_graph, modules: dict | None = None, root_path: str = ".", runtime: dict | None = None
) -> dict:

    hard_edges = project_graph.hard_edges or {}
    soft_edges = project_graph.soft_edges or {}

    metrics = compute_graph_metrics(hard_edges, soft_edges) or {}
    thresholds = get_thresholds(metrics.get("nodes", 0))
    cycles = detect_cycles(hard_edges)

    collisions_list = []
    if modules is not None:
        collisions_list = validate_name_collisions(modules)

    graph_dict = {
        "hard_edges": {k: sorted(set(hard_edges[k])) for k in sorted(hard_edges)},
        "soft_edges": {k: sorted(set(soft_edges[k])) for k in sorted(soft_edges)},
    }

    risk_map = _compute_module_risk(metrics, graph_dict)
    hotspots = detect_hotspots(graph_dict["hard_edges"])
    inspection_targets = _compute_inspection_targets(hotspots)
    undirected = _build_undirected_graph(graph_dict["hard_edges"])
    clusters = _connected_components(undirected)

    debt = compute_debt(
        hard_edges,
        soft_edges,
        cycles,
        metrics,
        clusters=clusters,
        hotspots=hotspots,
        collisions=collisions_list,
    )

    refactor_plan = _compute_refactor_plan(
        hotspots,
        clusters,
        len(graph_dict["hard_edges"]),
        thresholds,
        risk_map=risk_map,
    )

    risk_summary = _compute_risk_summary(risk_map, thresholds.get("critical_score", 0.85))
    runtime_info = runtime.copy() if runtime else {}
    runtime_info["generated_at"] = datetime.now().isoformat()

    llm_signals = {
        "module_risk": risk_map,
        "risk_summary": risk_summary,
        "hotspots": hotspots,
        "inspection_targets": inspection_targets,
        "dependency_clusters": clusters,
        "refactor_plan": refactor_plan,
        "soft_dependencies": _compute_soft_dependencies(graph_dict),
    }

    if modules is not None:
        llm_signals["module_import_profile"] = _compute_import_profile(modules)
        llm_signals["name_collisions"] = generate_collisions_report(
            modules, precomputed=collisions_list
        )

    real_collisions = [c for c in collisions_list if not getattr(c, "is_identical", False)]

    return {
        "status": "HEALTHY" if not cycles and not real_collisions else "BROKEN",
        "runtime": runtime_info,
        "metrics": metrics,
        "cycles": cycles,
        "cycle_count": len(cycles),
        "debt": debt,
        "graph": graph_dict,
        "llm_signals": llm_signals,
    }
