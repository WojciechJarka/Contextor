import os
from datetime import datetime
from typing import Any

from contextor.core.graph.cycles import detect_cycles
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.hotspots import detect_hotspots
from contextor.core.reporting_engine.debt import compute_debt
from contextor.core.reporting_engine.dictionary import IndexDictionary
from contextor.core.reporting_engine.structure_generator import compact_structure_report
from contextor.core.reporting_layer.artifact_usage_report_compact import compact_artifact_report

from .formatting import _compute_status
from .summary_generator import _compute_action_items

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
        # P0-5: A cycle belongs to a layer only when ALL of its modules
        # are inside the layer.  Using any() would count cross-layer
        # cycles as layer cycles, inflating layer cycle count and
        # mis-attributing responsibility.
        if all(m in layer_set for m in cycle)
    ]

    layer_real_collisions = [
        c for c in global_collisions
        if not getattr(c, "is_identical", False)
        and all(n in layer_set for n in getattr(c, "nodes", []))
    ]

    # P1-6: Match skipped files to the layer using module-prefix lookup.
    # The previous approach converted the file path to a dotted string and
    # searched for it as a substring inside module IDs, which could produce
    # false positives for short or ambiguous path segments.
    # We now check whether any module in layer_set starts with the dotted
    # path prefix derived from the skipped file, which is the same
    # convention used to derive module identifiers from file paths.
    def _file_matches_layer(item) -> bool:
        raw_path = getattr(item, "path", "") or ""
        # Normalise separators and strip leading/trailing slashes.
        dotted = raw_path.replace("\\", "/").strip("/").replace("/", ".")
        # Remove common file extensions so `contextor/core/api/foo.py`
        # becomes `contextor.core.api.foo` for prefix matching.
        for ext in (".py", ".pyi"):
            if dotted.endswith(ext):
                dotted = dotted[: -len(ext)]
                break
        # Strip .__init__ suffix so that `contextor/core/api/__init__.py`
        # is treated as `contextor.core.api` and correctly matched against
        # the layer_set entry for the package itself.
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        if not dotted:
            return False
        # A file belongs to the layer if its derived module ID is exactly
        # a layer module or is a prefix of one (handles sub-packages).
        return dotted in layer_set or any(
            m == dotted or m.startswith(dotted + ".")
            for m in layer_set
        )

    layer_skipped = [
        item for item in global_skipped_files
        if _file_matches_layer(item)
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
    index_dict: IndexDictionary | None = None,
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
    if index_dict:
        all_known_modules.update(index_dict.registry.list_modules())

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

    per_module_degrees = {}
    for mod in layer_modules:
        out_deg = len(internal_hard.get(mod, []))
        in_deg = sum(1 for targets in internal_hard.values() if mod in targets)
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
        "shared_artifact_keys": [
            k for k in global_artifacts.get("shared_artifact_keys", [])
            if k in layer_artifacts
        ],
        "_usage_sidecar": {
            k: v
            for k, v in global_artifacts.get("_usage_sidecar", {}).items()
            if k in layer_artifacts
        },
    }
    layer_artifacts_report["shared_artifact_count"] = len(
        layer_artifacts_report["shared_artifact_keys"]
    )

    if index_dict is None:
        raise ValueError("index_dict must be provided to slice_report_for_layer")
    layer_compact_artifacts_report = compact_artifact_report(layer_artifacts_report, index_dict)

    layer_structure_report = {"hard_edges": internal_hard, "soft_edges": internal_soft}
    layer_compact_structure_report = compact_structure_report(layer_structure_report, index_dict)

    return {
        "summary": layer_summary_report,
        "structure": layer_compact_structure_report,
        # structure_raw exposes the non-compact edge graph with full module names.
        # execute_layer_pipeline must use this (not "structure") when passing
        # hard_edges to generate_graph_analytics_report, otherwise compact IDs
        # leak into graph metrics and produce ghost entries in the modules dict.
        "structure_raw": layer_structure_report,
        "metrics": layer_metrics_report,
        "artifacts": layer_artifacts_report,
        "artifacts_compact": layer_compact_artifacts_report,
        "_index_dict": index_dict,
    }
