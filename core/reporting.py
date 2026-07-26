# -*- coding: utf-8 -*-

"""
repo_guardian/core/reporting.py

REFACTOR SIGNAL ENGINE v3

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
"""

import os
import orjson

from datetime import datetime
from collections import defaultdict, deque

from repo_guardian.core.cycles import detect_cycles
from repo_guardian.core.metrics import compute_graph_metrics
from repo_guardian.core.debt import compute_debt
from repo_guardian.core.hotspots import detect_hotspots
from repo_guardian.core.thresholds import get_thresholds
from repo_guardian.core.artifact_usage_report import generate_artifact_usage_report
from repo_guardian.core.validator.collisions import validate_name_collisions

# ==========================================================
# GRAPH HELPERS
# ==========================================================


def _build_undirected_graph(
    hard_edges: dict
) -> dict:

    graph = defaultdict(set)

    for src, targets in hard_edges.items():

        for tgt in targets:

            graph[src].add(tgt)
            graph[tgt].add(src)

    return graph



def _connected_components(
    graph: dict
) -> list[list[str]]:

    visited = set()
    clusters = []

    for node in graph:

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

            for neigh in graph[current]:

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

    for source, targets in graph["soft_edges"].items():

        for target in targets:

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


    risks = {}


    for node, deps in graph["hard_edges"].items():

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


        score = (
            (in_deg / max_in) * 0.5
            +
            (out_deg / max_out) * 0.3
            +
            soft * 0.2
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
) -> list[dict]:

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

                    "priority":
                        (
                            "HIGH"
                            if score >= thresholds.get("critical_score", 0.85)
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


    #
    # Connected component całego projektu
    # nie jest kandydatem do splitu.
    #

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



# ==========================================================
# MAIN REPORT
# ==========================================================


def generate_report(
    project_graph,
    modules: dict | None = None,
    root_path: str = ".",
    runtime: dict | None = None
) -> dict:


    hard_edges = project_graph.hard_edges
    soft_edges = project_graph.soft_edges


    metrics = compute_graph_metrics(
        hard_edges,
        soft_edges
    )
    
    thresholds = get_thresholds(
        metrics["nodes"]
    )

    cycles = detect_cycles(
        hard_edges
    )


    graph_dict = {

        "hard_edges":
            {
                k:
                    sorted(list(set(v)))
                for k, v in hard_edges.items()
            },


        "soft_edges":
            {
                k:
                    sorted(list(set(v)))
                for k, v in soft_edges.items()
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


    collisions_list = []
    if modules is not None:
        collisions_list = validate_name_collisions(modules)
        llm_signals["module_import_profile"] = _compute_import_profile(modules)
        llm_signals["name_collisions"] = generate_collisions_report(
            modules, precomputed=collisions_list
        )

    real_collisions = [
        c for c in collisions_list
        if not getattr(c, "is_identical", False)
    ]

    return {
        "status": (
            "HEALTHY"
            if not cycles and not real_collisions
            else "BROKEN"
        ),

        "runtime": runtime_info,

        "metrics": metrics,

        "cycles": cycles,

        "cycle_count": len(cycles),

        "debt": debt,

        "graph": graph_dict,

        "llm_signals": llm_signals,
    }

def save_json(
    report: dict,
    path: str,
    log=None,
    label: str = ""
) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if log and label:
        log(f"Serializowanie i zapisywanie: {label} ({path})...")

    serialized = orjson.dumps(
        report,
        option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
    )
    with open(path, "wb") as f:
        f.write(serialized)

    if log and label:
        log(f"Zapisano pomyślnie: {label}")

# ==========================================================
# EXPORT HELPERS FOR SPLIT REPORTS
# ==========================================================

def generate_summary_report(
    metrics: dict,
    cycles: list,
    debt: dict,
    collisions: list | None = None,
) -> dict:
    """Generuje skondensowany raport stanu projektu."""
    collisions = collisions or []

    # is_identical=True to nieszkodliwy duplikat (np. re-export) —
    # nie psuje statusu. Liczy się tylko realny konflikt API:
    # ta sama nazwa, różny kod.
    real_collisions = [
        c for c in collisions
        if not getattr(c, "is_identical", False)
    ]

    return {
        "status": "HEALTHY" if not cycles and not real_collisions else "BROKEN",
        "metrics": metrics,
        "cycle_count": len(cycles),
        "collision_count": len(real_collisions),
        "debt_summary": {
            "total_score": debt.get("score", 0),
            "hotspot_count": len(debt.get("hotspots", [])),
        }
    }

def generate_structure_report(hard_edges: dict, soft_edges: dict) -> dict:
    """Generuje czysty graf zależności z deduplikacją krawędzi."""
    return {
        "hard_edges": {k: sorted(list(set(v))) for k, v in hard_edges.items()},
        "soft_edges": {k: sorted(list(set(v))) for k, v in soft_edges.items()}
    }

def generate_collisions_report(modules: dict, precomputed: list | None = None) -> dict:
    """
    Generuje dedykowany raport kolizji nazw dla artefaktów tego samego typu 
    (klasa z klasą, funkcja z funkcją itp.), które posiadają inny kod,
    zawierający również szczegóły kodu skoligaconych elementów.
    """
    all_collisions = (
        precomputed
        if precomputed is not None
        else validate_name_collisions(modules)
    )
    collisions_data = []

    for error in all_collisions:

        collisions_data.append(
            {
                "message": error.message,

                "nodes": error.nodes,

                "artifact_type":
                    getattr(
                        error,
                        "artifact_type",
                        "unknown"
                    ),

                "is_identical":
                    getattr(
                        error,
                        "is_identical",
                        False
                    ),

                #
                # pełny kod konfliktujących artefaktów
                #
                "conflicting_code":
                    getattr(
                        error,
                        "code_snippets",
                        {}
                    ),

                #
                # rozszerzone dane AST
                #
                "symbol_details":
                    getattr(
                        error,
                        "symbol_details",
                        []
                    ),
            }
        )

    return {
        "generated_at": datetime.now().isoformat(),
        "total_collisions": len(collisions_data),
        "collisions": collisions_data,
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
    log=None
):
    """Fasada: zapisuje oddzielne pliki w katalogu output sekwencyjnie z orjson."""
    
    if log:
        log("Rozpoczynanie sekwencyjnego zapisu raportów...")

    # 1. Raport podsumowujący
    summary_data = generate_summary_report(metrics, cycles, debt)
    save_json(
        summary_data,
        f"output/{repo_name}_summary.json",
        log=log,
        label="raport podsumowujący"
    )
    
    # 2. Raport struktury grafu
    structure_data = generate_structure_report(graph.hard_edges, graph.soft_edges)
    save_json(
        structure_data,
        f"output/{repo_name}_structure.json",
        log=log,
        label="raport struktury grafu"
    )
    
    # 3. Raport kolizji nazw (duplikatów)
    if log:
        log("Generowanie raportu kolizji nazw...")
    collisions_data = generate_collisions_report(modules)
    save_json(
        collisions_data,
        f"output/{repo_name}_name_collisions.json",
        log=log,
        label="raport kolizji nazw"
    )

    # 4. Raport użycia artefaktów
    if log:
        log("Generowanie raportu użycia artefaktów...")
    artifact_data = generate_artifact_usage_report(modules, root_path, runtime)
    
    artifact_data["debug_info"] = {
        "module_count": len(modules),
        "root_path": root_path,
        "timestamp": datetime.now().isoformat()
    }
    
    save_json(
        artifact_data,
        f"output/{repo_name}_artifacts.json",
        log=log,
        label="raport artefaktów"
    )

    if log:
        log("Wszystkie raporty zostały pomyślnie zapisane.")
