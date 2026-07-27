#~~~~~~[START PLIKU: reporting.py - CZĘŚĆ 1/2 ]~~~~~~#
# -*- coding: utf-8 -*-

"""
repo_guardian/core/reporting.py

REFACTOR SIGNAL ENGINE v3 + LAYER SLICING EXTENSION

Rozszerza klasyczny raport o:
- hotspot ranking
- module risk score
- dependency clusters
- refactor suggestions
- import profile
- architectural debt signals
- soft dependency explanations
- inspection targets
- name collisions report (with conflicting code snippets)
- layer/subpath slicing engine (generating 5 scoped sub-reports)
"""

import os
import orjson

from datetime import datetime
from collections import defaultdict, deque
from typing import Dict, Any

from repo_guardian.core.cycles import detect_cycles
from repo_guardian.core.metrics import compute_graph_metrics
from repo_guardian.core.debt import compute_debt
from repo_guardian.core.hotspots import detect_hotspots
from repo_guardian.core.thresholds import get_thresholds
from repo_guardian.core.artifact_usage_report import generate_artifact_usage_report
from repo_guardian.core.artifact_usage_report_compact import (
    compact_artifact_report,
    save_compact_artifact_report,
)
from repo_guardian.core.validator.collisions import validate_name_collisions

# ==========================================================
# GRAPH HELPERS
# ==========================================================


def _build_undirected_graph(
    hard_edges: dict
) -> dict:

    graph = defaultdict(set)

    for src, edges in sorted(hard_edges.items()):

        for edge in sorted(
            edges,
            key=lambda e: e.target if hasattr(e, "target") else e
        ):

            target = (
                edge.target
                if hasattr(edge, "target")
                else edge
            )

            graph[src].add(target)
            graph[target].add(src)

    return graph


def _connected_components(
    graph: dict
) -> list[list[str]]:

    visited = set()
    clusters = []

    for node in sorted(graph):

        if node in visited:
            continue

        queue = deque([node])
        component = []

        while queue:

            current = queue.popleft()

            if current in visited:
                continue

            visited.add(current)
            component.append(current)

            for neigh in sorted(graph[current]):

                if neigh not in visited:
                    queue.append(neigh)

        clusters.append(
            sorted(component)
        )

    return sorted(
        clusters,
        key=len,
        reverse=True
    )


# ==========================================================
# SIGNAL LAYERS
# ==========================================================


def _compute_soft_dependencies(
    graph: dict
) -> list[dict]:

    dependencies = []

    for source, targets in sorted(graph["soft_edges"].items()):

        for target in sorted(targets):

            dependencies.append(
                {
                    "from": source,
                    "to": target,
                    "reason": "resolver_fallback",
                }
            )

    return sorted(
        dependencies,
        key=lambda x: (
            x["from"],
            x["to"]
        )
    )


def _compute_module_risk(
    metrics: dict,
    graph: dict
) -> dict:

    max_in = max(
        metrics.get(
            "max_in_degree",
            1
        ),
        1
    )

    max_out = max(
        metrics.get(
            "max_out_degree",
            1
        ),
        1
    )

    # Zbieramy WSZYSTKIE węzły - także te, które występują
    # WYŁĄCZNIE jako cel krawędzi (in-degree > 0, out-degree 0).
    nodes = set(graph["hard_edges"])

    for targets in graph["hard_edges"].values():
        nodes.update(targets)

    risks = {}

    for node in sorted(nodes):

        deps = graph["hard_edges"].get(node, [])

        in_deg = sum(
            node in targets
            for targets in graph["hard_edges"].values()
        )

        out_deg = len(deps)

        soft = len(
            graph["soft_edges"].get(
                node,
                []
            )
        )

        soft_score = min(
            soft / max_out,
            1
        )

        score = (
            (in_deg / max_in) * 0.5
            +
            (out_deg / max_out) * 0.3
            +
            soft_score * 0.2
        )

        # konfiguracja jest centralna,
        # ale nie powinna być traktowana
        # jak ryzykowny moduł

        if (
            node.startswith("config.")
        ):
            score *= 0.25

        risks[node] = round(
            score,
            4
        )

    return risks


def _compute_risk_summary(
    risk_map: dict,
    critical_score: float,
) -> dict:
    """
    Agregat mapy ryzyka dla LLM.
    """

    if not risk_map:
        return {
            "critical": [],
            "average": 0,
            "max": 0,
        }

    values = list(risk_map.values())

    critical = sorted(
        module
        for module, score in risk_map.items()
        if score >= critical_score
    )

    return {
        "critical": critical,
        "average": round(sum(values) / len(values), 4),
        "max": round(max(values), 4),
    }


def _compute_inspection_targets(
    hotspots: list[dict]
) -> list[dict]:

    targets = []

    for priority, item in enumerate(
        hotspots[:10],
        start=1
    ):

        signals = []

        if item.get("type") == "CONFIG_HUB":

            signals.append(
                "shared_configuration_dependency"
            )

        if item.get("type") == "HOTSPOT":

            signals.append(
                "high_coupling"
            )

        if item.get("type") == "OUTBOUND_HOTSPOT":

            signals.append(
                "high_out_degree"
            )

        if item.get("type") == "HUB":

            signals.append(
                "high_dependency_centrality"
            )

        if item.get(
            "out_degree",
            0
        ) >= 10:

            signals.append(
                "high_out_degree"
            )

        if item.get(
            "in_degree",
            0
        ) >= 10:

            signals.append(
                "high_in_degree"
            )

        if item.get(
            "in_degree",
            0
        ) >= 20:

            signals.append(
                "many_dependents"
            )

        if signals:

            targets.append(
                {
                    "module": item["module"],
                    "priority": priority,
                    "signals": sorted(
                        set(signals)
                    ),
                }
            )

    return targets

# ==========================================================
# REFACTOR PLAN
# ==========================================================


def _compute_refactor_plan(
    hotspots: list,
    clusters: list,
    total_modules: int,
    thresholds: dict,
    risk_map: dict | None = None,
) -> list[dict]:

    risk_map = risk_map or {}

    plan = []

    for h in hotspots[:10]:

        hotspot_type = h.get(
            "type",
            ""
        )

        score = h.get(
            "score",
            0
        )

        module_risk = risk_map.get(
            h.get("module", ""),
            0
        )

        combined_score = score + module_risk

        if hotspot_type == "CONFIG_HUB":

            plan.append(
                {
                    "type":
                        "KEEP_AS_SHARED_CONFIG",

                    "target":
                        h["module"],

                    "priority":
                        "INFO",

                    "reason":
                        "central configuration module"
                }
            )

            continue

        if hotspot_type in (
            "HOTSPOT",
            "OUTBOUND_HOTSPOT",
            "HUB",
        ):

            plan.append(
                {
                    "type":
                        (
                            "EXTRACT_INTERFACE"
                            if hotspot_type == "HUB"
                            else "SPLIT_MODULE"
                        ),

                    "target":
                        h["module"],

                    "hotspot_score":
                        score,

                    "module_risk":
                        module_risk,

                    "priority":
                        (
                            "HIGH"
                            if combined_score >= thresholds.get("critical_score", 0.85)
                            else "MEDIUM"
                        ),

                    "reason":
                        {
                            "HOTSPOT":
                                "high coupling detected",

                            "HUB":
                                "high dependency centrality",

                            "OUTBOUND_HOTSPOT":
                                "too many outgoing dependencies",

                        }.get(
                            hotspot_type,
                            "architectural hotspot"
                        )
                }
            )

    for cluster in clusters:

        if (
            len(cluster) >= thresholds["refactor_cluster_size"]
            and
            len(cluster) < total_modules * 0.6
        ):

            plan.append(
                {
                    "type":
                        "SPLIT_PACKAGE",

                    "target_modules":
                        cluster,

                    "priority":
                        "MEDIUM",

                    "reason":
                        "large isolated dependency cluster detected"
                }
            )

    return plan


def _compute_import_profile(
    modules: dict
) -> dict:

    profile = {}

    for module_id, module in modules.items():

        total = len(
            module.imports
        )

        local = sum(
            1
            for imp in module.imports
            if imp.is_local
        )

        profile[module_id] = {
            "global_imports":
                total - local,

            "local_imports":
                local,
        }

    return profile

#~~~~~~[START PLIKU: reporting.py - CZĘŚĆ 2/2 ]~~~~~~#

# ==========================================================
# LAYER / SUBPATH SLICING ENGINE
# ==========================================================


def filter_report_by_subpath(
    report: Dict[str, Any],
    subpath: str
) -> Dict[str, Any]:
    """
    Generuje wycinek (slice) pełnego raportu zarezerwowany dla modułów,
    których nazwa zaczyna się od `subpath`.
    """
    prefix = subpath if subpath.endswith(".") else f"{subpath}."

    def is_match(mod_name: str) -> bool:
        return mod_name == subpath or mod_name.startswith(prefix)

    sliced_hard = {
        k: [target for target in v if is_match(target)]
        for k, v in report.get("graph", {}).get("hard_edges", {}).items()
        if is_match(k)
    }

    sliced_soft = {
        k: [target for target in v if is_match(target)]
        for k, v in report.get("graph", {}).get("soft_edges", {}).items()
        if is_match(k)
    }

    sliced_cycles = [
        cycle for cycle in report.get("cycles", [])
        if any(is_match(node) for node in cycle)
    ]

    sliced_collisions = [
        col for col in report.get("collisions", [])
        if any(is_match(m) for m in col.get("modules", []))
    ]

    llm = report.get("llm_signals", {})

    sliced_risk = {
        k: v for k, v in llm.get("module_risk", {}).items()
        if is_match(k)
    }

    sliced_hotspots = [
        h for h in llm.get("hotspots", [])
        if is_match(h.get("module", ""))
    ]

    sliced_targets = [
        t for t in llm.get("inspection_targets", [])
        if is_match(t.get("module", ""))
    ]

    sliced_clusters = [
        [mod for mod in cluster if is_match(mod)]
        for cluster in llm.get("dependency_clusters", [])
    ]
    sliced_clusters = [c for c in sliced_clusters if len(c) > 1]

    sliced_plan = []
    for plan_item in llm.get("refactor_plan", []):
        target = plan_item.get("target")
        target_mods = plan_item.get("target_modules")
        if target and is_match(target):
            sliced_plan.append(plan_item)
        elif target_mods and any(is_match(m) for m in target_mods):
            sliced_plan.append(plan_item)

    sliced_soft_deps = [
        sd for sd in llm.get("soft_dependencies", [])
        if is_match(sd.get("from", "")) or is_match(sd.get("to", ""))
    ]

    sliced_import_profile = {
        k: v for k, v in llm.get("module_import_profile", {}).items()
        if is_match(k)
    }

    nodes_count = len(sliced_hard)
    total_edges = sum(len(v) for v in sliced_hard.values())

    return {
        "subpath": subpath,
        "runtime": report.get("runtime", {}),
        "metrics": {
            "nodes": nodes_count,
            "edges": total_edges,
        },
        "cycles": sliced_cycles,
        "collisions": sliced_collisions,
        "debt": compute_debt(
            {k: [type("Edge", (), {"target": t})() for t in v] for k, v in sliced_hard.items()},
            {k: [type("Edge", (), {"target": t})() for t in v] for k, v in sliced_soft.items()},
            sliced_cycles,
            {"nodes": nodes_count, "edges": total_edges},
            clusters=sliced_clusters,
            hotspots=sliced_hotspots,
            collisions=sliced_collisions,
        ),
        "graph": {
            "hard_edges": sliced_hard,
            "soft_edges": sliced_soft,
        },
        "llm_signals": {
            "module_risk": sliced_risk,
            "risk_summary": _compute_risk_summary(sliced_risk, 0.85),
            "hotspots": sliced_hotspots,
            "inspection_targets": sliced_targets,
            "dependency_clusters": sliced_clusters,
            "refactor_plan": sliced_plan,
            "soft_dependencies": sliced_soft_deps,
            "module_import_profile": sliced_import_profile,
        },
    }


def generate_sliced_reports(
    report: Dict[str, Any],
    out_dir: str
) -> Dict[str, str]:
    """
    Tworzy 5 pod-raportów wycinkowych (core, web, services, utils, adapters)
    i zapisuje je na dysku w podkatalogu `sliced/`.
    """
    sliced_dir = os.path.join(out_dir, "sliced")
    os.makedirs(sliced_dir, exist_ok=True)

    target_layers = ["core", "web", "services", "utils", "adapters"]
    paths_map = {}

    for layer in target_layers:
        sliced_data = filter_report_by_subpath(report, layer)
        file_path = os.path.join(sliced_dir, f"report_{layer}.json")
        with open(file_path, "wb") as f:
            f.write(orjson.dumps(sliced_data, option=orjson.OPT_INDENT_2))
        paths_map[layer] = file_path

    return paths_map


# ==========================================================
# MAIN REPORT
# ==========================================================


def generate_report(
    project_graph,
    modules: dict | None = None,
    root_path: str = ".",
    runtime: dict | None = None
) -> dict:

    hard_edges = project_graph.hard_edges or {}
    soft_edges = project_graph.soft_edges or {}

    metrics = compute_graph_metrics(
        hard_edges,
        soft_edges
    ) or {}

    thresholds = get_thresholds(
        metrics.get("nodes", 0)
    )

    cycles = detect_cycles(
        hard_edges
    )

    collisions_list = []
    if modules is not None:
        collisions_list = validate_name_collisions(modules)

    graph_dict = {
        "hard_edges":
            {
                k:
                    sorted(
                        [
                            edge.target
                            for edge in hard_edges[k]
                        ]
                    )
                for k in sorted(hard_edges)
            },

        "soft_edges":
            {
                k:
                    sorted(
                        [
                            edge.target
                            for edge in soft_edges[k]
                        ]
                    )
                for k in sorted(soft_edges)
            },
    }

    risk_map = _compute_module_risk(
        metrics,
        graph_dict
    )

    hotspots = detect_hotspots(
        graph_dict["hard_edges"]
    )

    inspection_targets = _compute_inspection_targets(
        hotspots
    )

    undirected = _build_undirected_graph(
        graph_dict["hard_edges"]
    )

    clusters = _connected_components(
        undirected
    )

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

    risk_summary = _compute_risk_summary(
        risk_map,
        thresholds.get("critical_score", 0.85),
    )

    runtime_info = (
        runtime.copy()
        if runtime
        else {}
    )

    runtime_info["generated_at"] = (
        datetime.now().isoformat()
    )

    llm_signals = {
        "module_risk":
            risk_map,

        "risk_summary":
            risk_summary,

        "hotspots":
            hotspots,

        "inspection_targets":
            inspection_targets,

        "dependency_clusters":
            clusters,

        "refactor_plan":
            refactor_plan,

        "soft_dependencies":
            _compute_soft_dependencies(
                graph_dict
            ),
    }

    if modules is not None:
        llm_signals["module_import_profile"] = _compute_import_profile(modules)

    main_report = {
        "runtime": runtime_info,
        "metrics": metrics,
        "cycles": cycles,
        "collisions": collisions_list,
        "debt": debt,
        "graph": graph_dict,
        "llm_signals": llm_signals,
    }

    # Generowanie dedykowanego raportu użycia artefaktów
    if modules is not None:
        try:
            artifact_report = generate_artifact_usage_report(modules, project_graph)
            main_report["artifact_usage"] = artifact_report

            compact = compact_artifact_report(artifact_report)
            main_report["artifact_usage_compact"] = compact

            output_dir = runtime_info.get("output_dir", root_path)
            if output_dir:
                save_compact_artifact_report(compact, output_dir)
        except Exception as e:
            main_report["artifact_usage_error"] = str(e)

    # Generowanie 5 pod-raportów wycinkowych (sliced reports)
    output_dir = runtime_info.get("output_dir", root_path)
    if output_dir:
        try:
            sliced_paths = generate_sliced_reports(main_report, output_dir)
            main_report["sliced_reports"] = sliced_paths
        except Exception as e:
            main_report["sliced_reports_error"] = str(e)

    return main_report

def save_all_reports(
    report: Dict[str, Any],
    output_dir: str,
    filename: str = "report.json"
) -> Dict[str, Any]:
    """
    Zapisuje główny raport w katalogu output_dir oraz wyzwala
    generowanie i zapis pod-raportów (sliced) oraz raportu artefaktów.
    """
    os.makedirs(output_dir, exist_ok=True)
    main_report_path = os.path.join(output_dir, filename)

    # Uaktualnienie output_dir w runtime
    if "runtime" not in report:
        report["runtime"] = {}
    report["runtime"]["output_dir"] = output_dir

    # Wygenerowanie i dodanie ścieżek pod-raportów (sliced)
    try:
        sliced_paths = generate_sliced_reports(report, output_dir)
        report["sliced_reports"] = sliced_paths
    except Exception as e:
        report["sliced_reports_error"] = str(e)

    # Zapis głównego pliku JSON
    with open(main_report_path, "wb") as f:
        f.write(orjson.dumps(report, option=orjson.OPT_INDENT_2))

    return {
        "main_report": main_report_path,
        "sliced_reports": report.get("sliced_reports", {}),
    }
    
# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [
    "generate_report",
    "filter_report_by_subpath",
    "generate_sliced_reports",
    "save_all_reports",
]
