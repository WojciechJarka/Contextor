"""
core/reporting_engine/engine.py

Main analytical pipeline for generating JSON reports and extracting insights
(slicing, graph metrics, collisions, cycles, action items reporting).
"""

import os
from datetime import datetime
from typing import Any
from pathlib import Path

from contextor.core.analysis.git_context import collect_git_context
from contextor.core.graph.cycles import detect_cycles
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.graph.thresholds import get_thresholds
from contextor.core.hotspots import detect_hotspots
from contextor.core.reporting_engine.debt import compute_debt
from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report
from contextor.core.reporting_layer.artifact_usage_report_compact import (
    compact_artifact_report,
    save_compact_artifact_report,
)
from contextor.core.validator.collisions import validate_name_collisions

from .formatting import _collision_severity, _compute_status, save_json
from .graph_aggregators import _build_undirected_graph, _connected_components
from .refactor_planner import _compute_refactor_plan
from .risk_signals import (
    _compute_inspection_targets,
    _compute_module_risk,
    _compute_risk_summary,
    _compute_soft_dependencies,
)


# ==========================================================
# REPORT HEADER (P2)
# ==========================================================


def _build_report_header(root_path: str, data_source: str) -> dict:
    """
    Builds a stable report header present in every generated report.
    Provides commit SHA, branch, tool version, and data_source tag so
    a consumer (LLM or human) can unambiguously identify where a given
    report comes from and how to reconcile it with others.
    """
    try:
        import importlib.metadata
        tool_version = importlib.metadata.version("contextor")
    except Exception:
        tool_version = "unknown"

    # collect_git_context returns per-file data; we call it on root to get
    # repo-level commit / branch (uses git log on the directory itself).
    git_info = collect_git_context(root_path, root_path)

    # Try to read branch name separately (git_context only returns commit date).
    branch = None
    try:
        import subprocess
        from pathlib import Path
        p = Path(root_path)
        if (p / ".git").exists():
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(p), capture_output=True, text=True, check=True,
            )
            branch = result.stdout.strip() or None
            result2 = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(p), capture_output=True, text=True, check=True,
            )
            commit_sha = result2.stdout.strip()[:12] or None
        else:
            commit_sha = None
    except Exception:
        commit_sha = None

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "commit_sha": commit_sha,
        "branch": branch,
        "tool_version": tool_version,
        "data_source": data_source,
    }


# ==========================================================
# USAGE SIDECAR SAVE (P1b)
# ==========================================================


def _save_usage_sidecar(usage_sidecar: dict, path: str, log=None) -> None:
    """
    Saves the usage sidecar (artifact_id -> usage dict with line numbers)
    extracted from the artifact report as a separate on-demand file.
    """
    save_json(usage_sidecar, path, log=log, label="artifacts usage sidecar")


# ==========================================================
# SANITY CHECKS (P6c)
# ==========================================================


def _sanity_check_reports(
    summary: dict,
    artifacts: dict,
    compact: dict,
) -> list[str]:
    """
    Cross-validates key counts between summary, artifacts and compact reports.
    Returns a list of warning strings (empty = all consistent).
    """
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
        # Distinguish CLI / entry-point modules (expected to be isolated)
        # from genuinely dead code.
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

    # Stated explicitly so a partial analysis is visibly partial. These
    # files carry a '.py' name but are not analyzable Python.
    if skipped_files:
        report["skipped_files"] = [
            {"path": item.path, "reason": item.reason} for item in skipped_files
        ]
        report["skipped_file_count"] = len(skipped_files)

    return report



def generate_structure_report(hard_edges: dict, soft_edges: dict) -> dict:
    return {
        "hard_edges": {k: sorted(set(v)) for k, v in sorted(hard_edges.items())},
        "soft_edges": {k: sorted(set(v)) for k, v in sorted(soft_edges.items())},
    }


def generate_collisions_report(modules: dict, precomputed: list | None = None) -> dict:
    all_collisions = precomputed if precomputed is not None else validate_name_collisions(modules)
    collisions_data = []

    for error in all_collisions:
        severity = getattr(error, "severity", None)
        if severity is None:
            severity = _collision_severity(
                artifact_type=getattr(error, "artifact_type", "unknown"),
                symbol_details=getattr(error, "symbol_details", []),
                code_snippets=getattr(error, "code_snippets", {}),
            )
        collisions_data.append(
            {
                "message": error.message,
                "nodes": error.nodes,
                "artifact_type": getattr(error, "artifact_type", "unknown"),
                "is_identical": getattr(error, "is_identical", False),
                "severity": severity,
                "conflicting_code": getattr(error, "code_snippets", {}),
                "symbol_details": getattr(error, "symbol_details", []),
            }
        )

    identical_count = sum(1 for c in collisions_data if c["is_identical"])
    conflicting_count = len(collisions_data) - identical_count

    severity_counts = {
        "critical": sum(1 for c in collisions_data if c.get("severity") == "critical"),
        "warning": sum(1 for c in collisions_data if c.get("severity") == "warning"),
        "info": sum(1 for c in collisions_data if c.get("severity") == "info"),
    }

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    collisions_data.sort(key=lambda c: severity_order.get(c.get("severity", "warning"), 1))

    return {
        "generated_at": datetime.now().isoformat(),
        "total_collisions": len(collisions_data),
        "collision_summary": {
            "total": len(collisions_data),
            "identical": identical_count,
            "conflicting": conflicting_count,
            "by_severity": severity_counts,
        },
        "collisions": collisions_data,
    }


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


def _compute_layer_health(
    layer_set: set,
    layer_modules: list,
    internal_hard: dict,
    internal_soft: dict,
    inbound_hard: list,
    outbound_hard: list,
    global_hotspots: list,
    global_cycles: list,
    global_collisions: list,
    global_skipped_files: list,
    global_summary: dict,
    report_header: dict | None = None,
) -> dict:
    """
    Computes layer-scoped health signals.

    Default mode: filter global results to modules in this layer.
    Full per-layer computation is triggered automatically when:
      - density_ratio > 3.0  (layer much denser than global)
      - any filtered hotspot has score > 0.85 and type == HUB
      - 0 cycles found by filtering but internal_edge_count > layer_module_count
        (conditions necessary for a cycle are satisfied)
    """
    # --- filtered mode ---
    layer_hotspots = [
        h for h in global_hotspots if h.get("module") in layer_set
    ]

    layer_cycles = [
        cycle for cycle in global_cycles
        if any(m in layer_set for m in cycle)
    ]

    layer_real_collisions = [
        c for c in global_collisions
        if not getattr(c, "is_identical", False)
        and all(n in layer_set for n in getattr(c, "nodes", []))
    ]

    layer_skipped = [
        item for item in global_skipped_files
        if any(item.path.replace("\\", "/").replace("/", ".") in m for m in layer_set)
    ] if global_skipped_files else []

    internal_edge_count = sum(len(v) for v in internal_hard.values())
    layer_module_count = len(layer_modules)

    # --- trigger check for full per-layer computation ---
    global_density = global_summary.get("metrics", {}).get("density_hard", 0)
    layer_density = (
        round(internal_edge_count / (layer_module_count * (layer_module_count - 1)), 4)
        if layer_module_count > 1 else 0
    )
    density_ratio = round(layer_density / global_density, 2) if global_density > 0 else 0

    trigger_reasons = []
    if density_ratio > 3.0:
        trigger_reasons.append(f"density_ratio={density_ratio} > 3.0")
    if any(h.get("score", 0) > 0.85 and h.get("type") == "HUB" for h in layer_hotspots):
        trigger_reasons.append("filtered hotspot score > 0.85 (type=HUB)")
    if not layer_cycles and internal_edge_count > layer_module_count:
        trigger_reasons.append(
            f"no cycles found but internal_edge_count({internal_edge_count}) "
            f"> module_count({layer_module_count}) — possible cycle"
        )

    computation_mode = "filtered"

    if trigger_reasons:
        # Full per-layer computation
        computation_mode = "full"
        layer_cycles = detect_cycles(internal_hard)
        layer_hotspots = detect_hotspots(internal_hard)

    # --- debt (always per-layer using internal edges) ---
    layer_metrics_raw = compute_graph_metrics(internal_hard, internal_soft)
    layer_debt = compute_debt(
        internal_hard,
        internal_soft,
        layer_cycles,
        layer_metrics_raw,
        hotspots=layer_hotspots,
        collisions=layer_real_collisions,
    )

    active_layer_hotspots = [h for h in layer_hotspots if h.get("type") not in ("ISOLATED", "NORMAL")]
    layer_status = _compute_status(layer_cycles, layer_real_collisions, active_layer_hotspots)

    layer_action_items = _compute_action_items(
        layer_cycles,
        layer_real_collisions,
        hotspots=active_layer_hotspots,
        isolated_modules=[
            h["module"] for h in layer_hotspots
            if h.get("type") == "ISOLATED" and not h["module"].endswith("__init__")
        ],
    )

    result = {
        "status": layer_status,
        "computation_mode": computation_mode,
        "cycles": layer_cycles,
        "layer_cycles_count": len(layer_cycles),
        "hotspots": active_layer_hotspots[:5],
        "debt_summary": {
            "total_score": layer_debt.get("score", 0),
            "normalized": layer_debt.get("normalized", 0),
            "label": layer_debt.get("interpretation", {}).get("label", "unknown"),
            "hotspot_count": len(active_layer_hotspots),
        },
        "action_items": layer_action_items,
        "name_collisions_count": len(layer_real_collisions),
        "global_context": {
            "status": global_summary.get("status", "UNKNOWN"),
            "cycles_total": global_summary.get("cycle_count", 0),
            "nodes_total": global_summary.get("metrics", {}).get("nodes", 0),
            "collision_count_total": global_summary.get("collision_count", 0),
        },
    }

    if trigger_reasons:
        result["full_computation_triggered_by"] = trigger_reasons

    if layer_skipped:
        result["skipped_files"] = [{"path": item.path, "reason": item.reason} for item in layer_skipped]

    if report_header:
        result["report_header"] = {**report_header, "data_source": "layer"}

    return result


def slice_report_for_layer(
    layer_path: str,
    root_path: str,
    global_metrics: dict[str, Any],
    global_structure: dict[str, Any],
    global_summary: dict[str, Any],
    global_artifacts: dict[str, Any],
    global_compact_artifacts: dict[str, Any],
    global_hotspots: list | None = None,
    global_cycles: list | None = None,
    global_collisions: list | None = None,
    global_skipped_files: list | None = None,
    report_header: dict | None = None,
) -> dict[str, dict[str, Any]]:
    abs_layer = os.path.abspath(layer_path)
    abs_root = os.path.abspath(root_path)

    try:
        rel_path = os.path.relpath(abs_layer, abs_root)
    except ValueError:
        rel_path = os.path.basename(abs_layer)

    if rel_path == ".":
        layer_prefix = ""
    else:
        layer_prefix = rel_path.replace("\\", "/").strip("/").replace("/", ".")

    def is_in_layer(mod_id: str) -> bool:
        if not mod_id:
            return False
        norm_mod = mod_id.replace("\\", "/").strip("/").replace("/", ".")
        if not layer_prefix:
            return True
        return norm_mod == layer_prefix or norm_mod.startswith(layer_prefix + ".")

    structure_map = global_structure.get("hard_edges", {})
    all_known_modules = set(structure_map.keys())
    for targets in structure_map.values():
        all_known_modules.update(targets)
    all_known_modules.update(global_compact_artifacts.get("modules", []))

    layer_modules = sorted(m for m in all_known_modules if is_in_layer(m))
    layer_set = set(layer_modules)

    hard_edges = global_structure.get("hard_edges", {})
    soft_edges = global_structure.get("soft_edges", {})

    internal_hard = {}
    internal_soft = {}
    inbound_hard = []
    outbound_hard = []

    for src, targets in sorted(hard_edges.items()):
        src_in = is_in_layer(src)
        for tgt in sorted(targets):
            tgt_in = is_in_layer(tgt)
            if src_in and tgt_in:
                internal_hard.setdefault(src, []).append(tgt)
            elif src_in and not tgt_in:
                outbound_hard.append({"source": src, "target": tgt})
            elif not src_in and tgt_in:
                inbound_hard.append({"source": src, "target": tgt})

    for src, targets in sorted(soft_edges.items()):
        src_in = is_in_layer(src)
        for tgt in sorted(targets):
            tgt_in = is_in_layer(tgt)
            if src_in and tgt_in:
                internal_soft.setdefault(src, []).append(tgt)

    internal_hard = {src: sorted(set(targets)) for src, targets in sorted(internal_hard.items())}
    internal_soft = {src: sorted(set(targets)) for src, targets in sorted(internal_soft.items())}
    inbound_hard = sorted(inbound_hard, key=lambda e: (e["source"], e["target"]))
    outbound_hard = sorted(outbound_hard, key=lambda e: (e["source"], e["target"]))

    # --- Layer health (P3) ---
    layer_health = _compute_layer_health(
        layer_set=layer_set,
        layer_modules=layer_modules,
        internal_hard=internal_hard,
        internal_soft=internal_soft,
        inbound_hard=inbound_hard,
        outbound_hard=outbound_hard,
        global_hotspots=global_hotspots or [],
        global_cycles=global_cycles or [],
        global_collisions=global_collisions or [],
        global_skipped_files=global_skipped_files or [],
        global_summary=global_summary,
        report_header=report_header,
    )

    layer_summary_report = {
        "layer": {"path": layer_path, "root": os.path.abspath(root_path)},
        "layer_modules": layer_modules,
        "layer_module_count": len(layer_modules),
        "total_module_count": len(all_known_modules),
        "internal_edges": {"hard": internal_hard, "soft": internal_soft},
        "boundary": {
            "inbound_hard": inbound_hard,
            "outbound_hard": outbound_hard,
            "depended_on_by": sorted({e["source"] for e in inbound_hard}),
            "depends_on": sorted({e["target"] for e in outbound_hard}),
        },
        "summary": {
            "internal_edge_count": sum(len(v) for v in internal_hard.values()),
            "inbound_edge_count": len(inbound_hard),
            "outbound_edge_count": len(outbound_hard),
            "external_dependents_count": len({e["source"] for e in inbound_hard}),
            "external_dependencies_count": len({e["target"] for e in outbound_hard}),
        },
        "generated_at": global_summary.get("generated_at", datetime.now().isoformat()),
        # Health signals injected from layer_health (P3)
        "status": layer_health["status"],
        "computation_mode": layer_health["computation_mode"],
        "cycles": layer_health["cycles"],
        "layer_cycles_count": layer_health["layer_cycles_count"],
        "hotspots": layer_health["hotspots"],
        "debt_summary": layer_health["debt_summary"],
        "action_items": layer_health["action_items"],
        "name_collisions_count": layer_health["name_collisions_count"],
        "global_context": layer_health["global_context"],
    }

    if "full_computation_triggered_by" in layer_health:
        layer_summary_report["full_computation_triggered_by"] = layer_health["full_computation_triggered_by"]
    if "skipped_files" in layer_health:
        layer_summary_report["skipped_files"] = layer_health["skipped_files"]
    if report_header:
        layer_summary_report["report_header"] = {**report_header, "data_source": "layer"}

    layer_structure_report = {"hard_edges": internal_hard, "soft_edges": internal_soft}

    layer_node_count = len(layer_modules)
    layer_edge_count = sum(len(v) for v in internal_hard.values())
    layer_soft_edge_count = sum(len(v) for v in internal_soft.values())

    if layer_node_count > 1:
        layer_density = round(layer_edge_count / (layer_node_count * (layer_node_count - 1)), 4)
    else:
        layer_density = 0

    global_density = global_metrics.get("density_hard", global_metrics.get("density", 0))
    density_ratio = round(layer_density / global_density, 2) if global_density > 0 else 0

    # P4: per-module in/out degree within layer
    per_module_degrees = {}
    for mod in layer_modules:
        out_deg = len(internal_hard.get(mod, []))
        in_deg = sum(1 for targets in internal_hard.values() if mod in targets)
        # Also add inbound/outbound boundary connections
        boundary_in = sum(1 for e in inbound_hard if e["target"] == mod)
        boundary_out = sum(1 for e in outbound_hard if e["source"] == mod)
        per_module_degrees[mod] = {
            "in_degree": in_deg + boundary_in,
            "out_degree": out_deg + boundary_out,
            "internal_in": in_deg,
            "internal_out": out_deg,
        }

    layer_metrics_report = {
        "nodes": layer_node_count,
        "edges": layer_edge_count,
        "edges_soft": layer_soft_edge_count,
        "density": layer_density,
        "global_density": global_density,
        "density_ratio": density_ratio,
        "inbound_edge_count": len(inbound_hard),
        "outbound_edge_count": len(outbound_hard),
        "layer_scope": layer_path,
        "per_module": per_module_degrees,
    }

    layer_artifacts = {
        k: v
        for k, v in global_artifacts.get("artifacts", {}).items()
        if is_in_layer(v.get("definer_module", ""))
    }

    layer_artifacts_report = {
        "runtime": global_artifacts.get("runtime", {}),
        "module_count": len(layer_modules),
        "artifact_count": len(layer_artifacts),
        "artifacts": layer_artifacts,
        # shared_artifact_keys filtered to this layer's artifacts
        "shared_artifact_keys": [
            k for k in global_artifacts.get("shared_artifact_keys", [])
            if k in layer_artifacts
        ],
    }

    compact_modules = global_compact_artifacts.get("modules", [])
    layer_global_indices = {idx for idx, mod in enumerate(compact_modules) if is_in_layer(mod)}

    def _resolve(idx):
        return compact_modules[idx] if idx is not None and 0 <= idx < len(compact_modules) else None

    raw_layer_artifacts = {
        k: v
        for k, v in global_compact_artifacts.get("artifacts", {}).items()
        if v.get("definer_module") in layer_global_indices
    }

    referenced_modules = set()

    for artifact in raw_layer_artifacts.values():
        definer = _resolve(artifact.get("definer_module"))
        if definer:
            referenced_modules.add(definer)
        for c in artifact.get("consumers", []) or []:
            mod = _resolve(c)
            if mod:
                referenced_modules.add(mod)
        for values in (artifact.get("usage", {}) or {}).values():
            for v in values or []:
                if isinstance(v, dict):
                    mod = _resolve(v.get("module"))
                else:
                    mod = _resolve(v)
                if mod:
                    referenced_modules.add(mod)

    layer_compact_modules = sorted(referenced_modules)
    new_index_of = {mod: i for i, mod in enumerate(layer_compact_modules)}

    def _remap(idx):
        mod = _resolve(idx)
        return new_index_of.get(mod) if mod else None

    layer_compact_artifacts = {}
    for key, artifact in sorted(raw_layer_artifacts.items()):
        remapped = {
            "artifact": artifact.get("artifact"),
            "kind": artifact.get("kind"),
            "signature": artifact.get("signature"),
            "definer_module": _remap(artifact.get("definer_module")),
            "consumers": sorted(
                v for v in (_remap(c) for c in artifact.get("consumers", []) or []) if v is not None
            ),
        }
        usage = artifact.get("usage")
        if usage:
            remapped_usage = {}
            for category, values in sorted(usage.items()):
                if category == "ambiguous_calls" or category.endswith("_detail"):
                    new_vals = []
                    for v in values:
                        if isinstance(v, dict):
                            new_mod = _remap(v.get("module"))
                            if new_mod is not None:
                                new_val = dict(v)
                                new_val["module"] = new_mod
                                new_vals.append(new_val)
                        else:
                            new_mod = _remap(v)
                            if new_mod is not None:
                                new_vals.append(new_mod)
                    if new_vals:
                        if all(isinstance(x, dict) for x in new_vals):
                            remapped_usage[category] = sorted(
                                new_vals, key=lambda x: x.get("module", 0)
                            )
                        else:
                            remapped_usage[category] = new_vals  # skip sorting if mixed
                else:
                    # Flat arrays of indices
                    new_vals = sorted(m for m in (_remap(x) for x in values) if m is not None)
                    if new_vals:
                        remapped_usage[category] = new_vals

            if remapped_usage:
                remapped["usage"] = remapped_usage
        layer_compact_artifacts[key] = remapped

    layer_compact_artifacts_report = {
        "_format_note": global_compact_artifacts.get("_format_note", ""),
        "runtime": global_compact_artifacts.get("runtime", {}),
        "layer_module_count": len(layer_modules),
        "compact_module_count": len(layer_compact_modules),
        "modules": layer_compact_modules,
        "artifacts": layer_compact_artifacts,
    }

    return {
        "summary": layer_summary_report,
        "structure": layer_structure_report,
        "metrics": layer_metrics_report,
        "artifacts": layer_artifacts_report,
        "artifacts_compact": layer_compact_artifacts_report,
    }


def save_layer_reports(
    repo_name: str, layer_name: str, layer_reports: dict[str, dict[str, Any]], log=None
) -> dict:
    """
    Saves all layer-specific report files and returns a status summary dict
    for aggregation into the global summary's ``layer_index``.
    """
    prefix = f"output/{repo_name}_{layer_name}"
    save_json(
        layer_reports["summary"],
        f"{prefix}_summary.json",
        log=log,
        label=f"layer report [{layer_name}] - summary",
    )
    save_json(
        layer_reports["structure"],
        f"{prefix}_structure.json",
        log=log,
        label=f"layer report [{layer_name}] - structure",
    )
    save_json(
        layer_reports["metrics"],
        f"{prefix}_metrics.json",
        log=log,
        label=f"layer report [{layer_name}] - metrics",
    )
    save_json(
        layer_reports["artifacts"],
        f"{prefix}_artifacts.json",
        log=log,
        label=f"layer report [{layer_name}] - artifacts",
    )
    save_json(
        layer_reports["artifacts_compact"],
        f"{prefix}_artifacts_compact.json",
        log=log,
        label=f"layer report [{layer_name}] - artifacts (compact)",
    )

    summary = layer_reports["summary"]
    return {
        "layer": layer_name,
        "module_count": summary.get("layer_module_count", 0),
        "status": summary.get("status", "UNKNOWN"),
        "cycles_count": summary.get("layer_cycles_count", 0),
        "hotspot_count": len(summary.get("hotspots", [])),
        "computation_mode": summary.get("computation_mode", "filtered"),
    }


def save_all_reports(
    repo_name: str,
    modules: dict,
    graph: object,
    metrics: dict,
    cycles: list,
    debt: dict,
    runtime: dict,
    root_path: str,
    log=None,
    collisions: list | None = None,
    progress_callback=None,
    skipped_files: list | None = None,
    layer_index: list[dict] | None = None,
):
    """
    Generate and save all reports for the repository.
    """
    if log:
        log("Starting sequential report saving...")

    all_collisions = collisions if collisions is not None else validate_name_collisions(modules)
    hotspots = detect_hotspots(graph.hard_edges)

    # Build report_header once; passed to all sub-reports for consistency (P2)
    report_header = _build_report_header(root_path, data_source="global")

    summary_path = f"output/{repo_name}_summary.json"
    structure_path = f"output/{repo_name}_structure.json"
    collisions_path = f"output/{repo_name}_name_collisions.json"
    artifacts_path = f"output/{repo_name}_artifacts.json"
    artifacts_compact_path = f"output/{repo_name}_artifacts_compact.json"
    artifacts_usage_path = f"output/{repo_name}_artifacts_usage.json"

    summary_data = generate_summary_report(
        metrics,
        cycles,
        debt,
        collisions=all_collisions,
        hotspots=hotspots,
        skipped_files=skipped_files,
        report_header=report_header,
        layer_index=layer_index,
    )
    # summary_data is saved AFTER sanity checks below

    structure_data = generate_structure_report(graph.hard_edges, graph.soft_edges)
    save_json(structure_data, structure_path, log=log, label="graph structure report")

    if log:
        log("Generating name collisions report...")
    collisions_data = generate_collisions_report(modules, precomputed=all_collisions)
    save_json(collisions_data, collisions_path, log=log, label="name collisions report")

    if log:
        log("Generating artifact usage report...")
    artifact_data = generate_artifact_usage_report(
        modules, root_path, runtime, progress_callback=progress_callback
    )
    artifact_data["debug_info"] = {
        "module_count": len(modules),
        "root_path": root_path,
        "timestamp": datetime.now().isoformat(),
    }
    artifact_data["report_header"] = {**report_header, "data_source": "artifacts"}

    # Extract and save usage sidecar BEFORE stripping _usage_sidecar from the report (P1b)
    usage_sidecar = artifact_data.pop("_usage_sidecar", {})
    _save_usage_sidecar(usage_sidecar, artifacts_usage_path, log=log)

    save_json(artifact_data, artifacts_path, log=log, label="artifacts report")

    if log:
        log("Generating compact version of artifacts report...")
    compact_artifact_data = compact_artifact_report(artifact_data)
    save_compact_artifact_report(compact_artifact_data, artifacts_compact_path)

    sanity_warnings = _sanity_check_reports(summary_data, artifact_data, compact_artifact_data)
    if sanity_warnings:
        summary_data["sanity_warnings"] = sanity_warnings
        if log:
            for w in sanity_warnings:
                log(f"[SANITY] {w}")

    # Generate layer reports (P3d)
    if not layer_index:
        layer_index_data = []
        top_layers = set(m.split('.')[0] for m in modules.keys())
        for layer in top_layers:
            layer_path = Path(root_path) / layer
            if not layer_path.is_dir():
                continue
            try:
                layer_sliced = slice_report_for_layer(
                    layer_path=str(layer_path),
                    root_path=root_path,
                    global_metrics=metrics,
                    global_structure=structure_data,
                    global_summary=summary_data,
                    global_artifacts=artifact_data,
                    global_compact_artifacts=compact_artifact_data,
                    global_hotspots=hotspots,
                    global_cycles=cycles,
                    global_collisions=all_collisions,
                    global_skipped_files=skipped_files,
                    report_header=report_header,
                )
                summary = layer_sliced["summary"]
                layer_status = {
                    "layer": layer,
                    "module_count": summary.get("layer_module_count", 0),
                    "status": summary.get("status", "UNKNOWN"),
                    "cycles_count": summary.get("layer_cycles_count", 0),
                    "hotspot_count": len(summary.get("hotspots", [])),
                    "computation_mode": summary.get("computation_mode", "filtered"),
                }
                if layer_status["computation_mode"] == "full":
                    # Only save files if layer triggered deep computation
                    save_layer_reports(
                        repo_name=repo_name,
                        layer_name=layer,
                        layer_reports=layer_sliced,
                        log=log,
                    )
                layer_index_data.append(layer_status)
            except Exception as e:
                if log:
                    log(f"[WARNING] Failed to generate layer reports for {layer}: {e}")

        if layer_index_data:
            summary_data["layer_index"] = sorted(layer_index_data, key=lambda x: x.get("layer", ""))

    save_json(summary_data, summary_path, log=log, label="summary report")

    if log:
        log("All reports have been successfully saved.")

    return {
        "saved": True,
        "repo": repo_name,
        "files": [
            summary_path,
            structure_path,
            collisions_path,
            artifacts_path,
            artifacts_compact_path,
            artifacts_usage_path,
        ],
        "reports": ["summary", "structure", "collisions", "artifacts", "artifacts_compact", "artifacts_usage"],
        # Expose for callers that aggregate layer reports
        "_report_header": report_header,
        "_hotspots": hotspots,
        "_cycles": cycles,
        "_collisions": all_collisions,
        "_summary_data": summary_data,
        "_artifact_data": artifact_data,
        "_compact_artifact_data": compact_artifact_data,
    }
