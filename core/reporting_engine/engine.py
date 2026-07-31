# -*- coding: utf-8 -*-

"""
core/reporting_engine/engine.py

Main analytical pipeline for generating JSON reports and extracting insights
(slicing, graph metrics, collisions, cycles, action items reporting).
"""

import os
from datetime import datetime
from typing import Dict, Any

from repo_guardian.core.graph.cycles import detect_cycles
from repo_guardian.core.graph.metrics import compute_graph_metrics
from repo_guardian.core.reporting_engine.debt import compute_debt
from repo_guardian.core.hotspots import detect_hotspots
from repo_guardian.core.graph.thresholds import get_thresholds
from repo_guardian.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report
from repo_guardian.core.reporting_layer.artifact_usage_report_compact import (
    compact_artifact_report,
    save_compact_artifact_report,
)
from repo_guardian.core.validator.collisions import validate_name_collisions

from .graph_aggregators import _build_undirected_graph, _connected_components
from .risk_signals import (
    _compute_soft_dependencies, 
    _compute_module_risk, 
    _compute_risk_summary, 
    _compute_inspection_targets
)
from .refactor_planner import _compute_refactor_plan
from .formatting import _collision_severity, _compute_status, save_json


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
            f"CRITICAL: Eliminate import cycle "
            f"{' -> '.join(worst)} ({len(worst)} modules)"
        )

    critical_collisions = [
        c for c in real_collisions
        if getattr(c, "severity", "warning") == "critical"
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
            f"BROKEN: Resolve {total} name collision(s) "
            f"(duplicate public API across modules)"
        )

    if hotspots:
        outbound = [
            h for h in hotspots
            if h.get("type") == "OUTBOUND_HOTSPOT"
        ]
        if outbound:
            top = outbound[0]
            items.append(
                f"WARNING: Refactor '{top['module']}' "
                f"(out_degree={top.get('out_degree', '?')}, "
                f"type=OUTBOUND_HOTSPOT)"
            )

    if isolated_modules:
        items.append(
            f"INFO: {len(isolated_modules)} isolated module(s) with no connections "
            f"— remove or integrate: {', '.join(isolated_modules[:3])}"
        )

    return items[:5]


def generate_summary_report(
    metrics: dict,
    cycles: list,
    debt: dict,
    collisions: list | None = None,
    hotspots: list | None = None,
) -> dict:
    collisions = collisions or []
    hotspots = hotspots or []

    real_collisions = [
        c for c in collisions
        if not getattr(c, "is_identical", False)
    ]
    active_hotspots = [
        h for h in hotspots
        if h.get("type") not in ("ISOLATED", "NORMAL")
    ]
    isolated_modules = [
        h["module"] for h in hotspots
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

    return {
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


def generate_structure_report(hard_edges: dict, soft_edges: dict) -> dict:
    return {
        "hard_edges": {k: sorted(set(v)) for k, v in sorted(hard_edges.items())},
        "soft_edges": {k: sorted(set(v)) for k, v in sorted(soft_edges.items())}
    }


def generate_collisions_report(modules: dict, precomputed: list | None = None) -> dict:
    all_collisions = (
        precomputed
        if precomputed is not None
        else validate_name_collisions(modules)
    )
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
    collisions_data.sort(
        key=lambda c: severity_order.get(c.get("severity", "warning"), 1)
    )

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
    project_graph,
    modules: dict | None = None,
    root_path: str = ".",
    runtime: dict | None = None
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


def slice_report_for_layer(
    layer_path: str,
    root_path: str,
    global_metrics: Dict[str, Any],
    global_structure: Dict[str, Any],
    global_summary: Dict[str, Any],
    global_artifacts: Dict[str, Any],
    global_compact_artifacts: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
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
            "depends_on": sorted({e["target"] for e in outbound_hard})
        },
        "summary": {
            "internal_edge_count": sum(len(v) for v in internal_hard.values()),
            "inbound_edge_count": len(inbound_hard),
            "outbound_edge_count": len(outbound_hard),
            "external_dependents_count": len({e["source"] for e in inbound_hard}),
            "external_dependencies_count": len({e["target"] for e in outbound_hard})
        },
        "generated_at": global_summary.get("generated_at", datetime.now().isoformat())
    }

    layer_structure_report = {
        "hard_edges": internal_hard,
        "soft_edges": internal_soft
    }

    layer_node_count = len(layer_modules)
    layer_edge_count = sum(len(v) for v in internal_hard.values())

    if layer_node_count > 1:
        layer_density = round(layer_edge_count / (layer_node_count * (layer_node_count - 1)), 4)
    else:
        layer_density = 0

    layer_metrics_report = {
        "nodes": layer_node_count,
        "edges": layer_edge_count,
        "density": layer_density,
        "global_density": global_metrics.get("density", 0),
        "layer_scope": layer_path
    }

    layer_artifacts = {
        k: v for k, v in global_artifacts.get("artifacts", {}).items()
        if is_in_layer(v.get("definer_module", ""))
    }

    layer_artifacts_report = {
        "runtime": global_artifacts.get("runtime", {}),
        "module_count": len(layer_modules),
        "artifact_count": len(layer_artifacts),
        "artifacts": layer_artifacts,
        "shared_artifacts": [
            a for a in global_artifacts.get("shared_artifacts", [])
            if is_in_layer(a.get("definer_module", ""))
        ]
    }

    compact_modules = global_compact_artifacts.get("modules", [])
    layer_global_indices = {idx for idx, mod in enumerate(compact_modules) if is_in_layer(mod)}

    def _resolve(idx):
        return compact_modules[idx] if idx is not None and 0 <= idx < len(compact_modules) else None

    raw_layer_artifacts = {
        k: v for k, v in global_compact_artifacts.get("artifacts", {}).items()
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
        for category, values in (artifact.get("usage", {}) or {}).items():
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
                            remapped_usage[category] = sorted(new_vals, key=lambda x: x.get("module", 0))
                        else:
                            remapped_usage[category] = new_vals # skip sorting if mixed
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
        "artifacts_compact": layer_compact_artifacts_report
    }

def save_layer_reports(repo_name: str, layer_name: str, layer_reports: Dict[str, Dict[str, Any]], log=None) -> None:
    prefix = f"output/{repo_name}_{layer_name}"
    save_json(layer_reports["summary"], f"{prefix}_summary.json", log=log, label=f"layer report [{layer_name}] - summary")
    save_json(layer_reports["structure"], f"{prefix}_structure.json", log=log, label=f"layer report [{layer_name}] - structure")
    save_json(layer_reports["metrics"], f"{prefix}_metrics.json", log=log, label=f"layer report [{layer_name}] - metrics")
    save_json(layer_reports["artifacts"], f"{prefix}_artifacts.json", log=log, label=f"layer report [{layer_name}] - artifacts")
    save_json(layer_reports["artifacts_compact"], f"{prefix}_artifacts_compact.json", log=log, label=f"layer report [{layer_name}] - artifacts (compact)")

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
    progress_callback=None
):
    if log:
        log("Starting sequential report saving...")

    all_collisions = collisions if collisions is not None else validate_name_collisions(modules)
    hotspots = detect_hotspots(graph.hard_edges)

    summary_path = f"output/{repo_name}_summary.json"
    structure_path = f"output/{repo_name}_structure.json"
    collisions_path = f"output/{repo_name}_name_collisions.json"
    artifacts_path = f"output/{repo_name}_artifacts.json"
    artifacts_compact_path = f"output/{repo_name}_artifacts_compact.json"

    summary_data = generate_summary_report(metrics, cycles, debt, collisions=all_collisions, hotspots=hotspots)
    save_json(summary_data, summary_path, log=log, label="summary report")
    
    structure_data = generate_structure_report(graph.hard_edges, graph.soft_edges)
    save_json(structure_data, structure_path, log=log, label="graph structure report")
    
    if log: log("Generating name collisions report...")
    collisions_data = generate_collisions_report(modules, precomputed=all_collisions)
    save_json(collisions_data, collisions_path, log=log, label="name collisions report")

    if log: log("Generating artifact usage report...")
    artifact_data = generate_artifact_usage_report(modules, root_path, runtime, progress_callback=progress_callback)
    artifact_data["debug_info"] = {
        "module_count": len(modules),
        "root_path": root_path,
        "timestamp": datetime.now().isoformat()
    }
    save_json(artifact_data, artifacts_path, log=log, label="artifacts report")

    if log: log("Generating compact version of artifacts report...")
    compact_artifact_data = compact_artifact_report(artifact_data)
    save_compact_artifact_report(compact_artifact_data, artifacts_compact_path)

    if log: log("All reports have been successfully saved.")

    return {
        "saved": True,
        "repo": repo_name,
        "files": [summary_path, structure_path, collisions_path, artifacts_path, artifacts_compact_path],
        "reports": ["summary", "structure", "collisions", "artifacts", "artifacts_compact"],
    }
