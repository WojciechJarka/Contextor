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
    # Iterowanie tylko po graph["hard_edges"].items() pomijało
    # takie moduły całkowicie - miały in-degree > 0 (są używane),
    # ale nie dostawały żadnego risk score, bo nigdy nie były
    # kluczem w słowniku.
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

        # Bez normalizacji "soft" był surową liczbą (np. 5 miękkich
        # zależności = +1.0), podczas gdy in_deg/out_deg są znormalizowane
        # do [0,1] przez max_in/max_out - hard dependency dawał maksymalnie
        # 0.5+0.3=0.8, więc soft mógł całkowicie zdominować wynik. Brak
        # osobnej metryki "max_soft" w `metrics`, więc normalizujemy przez
        # max_out (ta sama skala co out-degree - też liczba wychodzących
        # zależności modułu).
        soft_score = min(
            soft / max_out,
            1
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

def _compute_risk_summary(
    risk_map: dict,
    critical_score: float,
) -> dict:
    """
    Agregat mapy ryzyka dla LLM - surowa mapa module -> score jest
    dobra do szczegółowego wglądu, ale odpowiedź na pytanie "co jest
    najbardziej ryzykowne w tym repo" wymaga przejrzenia WSZYSTKICH
    wpisów. To robi to za LLM: lista modułów przekraczających próg
    krytyczny, oraz średnia/maksimum do szybkiej orientacji o skali.
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

    # Hotspot score mierzy TYLKO sprzężenie w grafie zależności
    # (in/out-degree, soft-deps) - nie uwzględnia np. tego, że
    # moduł ma mały hotspot score, ale ogromną liczbę faktycznych
    # użytkowników. risk_map (z _compute_module_risk) to dodatkowy,
    # częściowo niezależny sygnał - łączymy oba przy ustalaniu
    # priorytetu, zamiast patrzeć wyłącznie na hotspot score.
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

    hard_edges = project_graph.hard_edges or {}
    soft_edges = project_graph.soft_edges or {}

    # "or {}" - zabezpieczenie na wypadek pustego/None wyniku
    # (np. pusty projekt, zero plików .py) - bez tego kolejna
    # linia (metrics.get("nodes", 0)) i tak by nie wybuchła
    # dzięki .get(), ale wolimy nie polegać na tym, że
    # compute_graph_metrics zawsze zwraca dict.
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
        "hard_edges": {
            k: sorted(
                [
                    edge.target
                    for edge in hard_edges[k]
                ]
            )
            for k in sorted(hard_edges)
        },

        "soft_edges": {
            k: sorted(
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
    label: str = "",
    compact: bool = False,
) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if log and label:
        log(f"Serializowanie i zapisywanie: {label} ({path})...")

    # OPT_SORT_KEYS: klucze obiektów JSON zawsze w tej samej
    # kolejności (alfabetycznej), niezależnie od kolejności
    # wstawiania w Pythonie - ten sam raport zawsze wygląda
    # identycznie bajt w bajt. UWAGA: to sortuje tylko KLUCZE
    # obiektów, NIE kolejność elementów w listach/tablicach -
    # za to nadal odpowiada ręczne sortowanie w kodzie generującym
    # dane (patrz _build_undirected_graph, _connected_components,
    # generate_structure_report, slice_report_for_layer itd.).
    option = (
        orjson.OPT_NON_STR_KEYS
        |
        orjson.OPT_SORT_KEYS
    )
    if not compact:
        option |= orjson.OPT_INDENT_2

    serialized = orjson.dumps(
        report,
        option=option
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

    real_collisions = [
        c for c in collisions
        if not getattr(c, "is_identical", False)
    ]

    return {
        "generated_at": datetime.now().isoformat(),
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
        "hard_edges": {k: sorted(set(v)) for k, v in sorted(hard_edges.items())},
        "soft_edges": {k: sorted(set(v)) for k, v in sorted(soft_edges.items())}
    }


def generate_collisions_report(modules: dict, precomputed: list | None = None) -> dict:
    """
    Generuje dedykowany raport kolizji nazw dla artefaktów tego samego typu 
    (klasa z klasą, funkcja z funkcją itp.), które posiadają inny kod.
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
                "artifact_type": getattr(error, "artifact_type", "unknown"),
                "is_identical": getattr(error, "is_identical", False),
                "conflicting_code": getattr(error, "code_snippets", {}),
                "symbol_details": getattr(error, "symbol_details", []),
            }
        )

    # Rozbicie liczby kolizji na nieszkodliwe duplikaty (ten sam
    # kod pod tą samą nazwą, np. re-export) i realne konflikty
    # (różny kod pod tą samą nazwą - to one psują status/debt,
    # patrz generate_summary_report / compute_debt).
    identical_count = sum(
        1 for c in collisions_data if c["is_identical"]
    )
    conflicting_count = len(collisions_data) - identical_count

    return {
        "generated_at": datetime.now().isoformat(),
        "total_collisions": len(collisions_data),
        "collision_summary": {
            "total": len(collisions_data),
            "identical": identical_count,
            "conflicting": conflicting_count,
        },
        "collisions": collisions_data,
    }


# ==========================================================
# LAYER / SUBPATH SLICING ENGINE
# ==========================================================

def slice_report_for_layer(
    layer_path: str,
    root_path: str,
    global_metrics: Dict[str, Any],
    global_structure: Dict[str, Any],
    global_summary: Dict[str, Any],
    global_artifacts: Dict[str, Any],
    global_compact_artifacts: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """
    Redukuje globalne raporty do dedykowanych raportów dla wybranej warstwy/katalogu.

    Prawidłowo obsługuje dopasowanie prefiksów ścieżek modułów oraz krawędzie
    wewnętrzne (internal) i brzegowe (inbound / outbound).

    Deterministyczne: wszystkie iteracje po strukturach opartych na dict/set
    są sortowane przed użyciem, żeby ten sam graf wejściowy zawsze dawał
    identyczny wynik JSON, niezależnie od kolejności wstawiania kluczy.
    """
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

    # Deduplikacja i sortowanie list docelowych w wewnętrznych
    # krawędziach - setdefault().append() mogło dodać duplikat,
    # gdyby ta sama krawędź wystąpiła dwukrotnie w źródle, i nie
    # gwarantowało deterministycznej kolejności.
    internal_hard = {
        src: sorted(set(targets))
        for src, targets in sorted(internal_hard.items())
    }
    internal_soft = {
        src: sorted(set(targets))
        for src, targets in sorted(internal_soft.items())
    }

    inbound_hard = sorted(inbound_hard, key=lambda e: (e["source"], e["target"]))
    outbound_hard = sorted(outbound_hard, key=lambda e: (e["source"], e["target"]))

    # 1. Layer Summary Report
    layer_summary_report = {
        "layer": {
            "path": layer_path,
            "root": os.path.abspath(root_path)
        },
        "layer_modules": layer_modules,
        "layer_module_count": len(layer_modules),
        "total_module_count": len(all_known_modules),
        "internal_edges": {
            "hard": internal_hard,
            "soft": internal_soft
        },
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

    # 2. Layer Structure Report
    layer_structure_report = {
        "hard_edges": internal_hard,
        "soft_edges": internal_soft
    }

    # 3. Layer Metrics Report
    #
    # Gęstość liczona LOKALNIE dla warstwy (nie globalnie -
    # global_metrics.get("density") to gęstość CAŁEGO repo i
    # pokazywanie jej pod kluczem "density" tutaj było mylące,
    # sugerowało że to właściwość warstwy). Przy 0 lub 1 module
    # w warstwie gęstość nie jest zdefiniowana (dzielenie przez
    # zero) - zwracamy 0. Globalna wartość zostaje dostępna
    # osobno, pod jawną nazwą, dla porównania.
    layer_node_count = len(layer_modules)
    layer_edge_count = sum(len(v) for v in internal_hard.values())

    if layer_node_count > 1:
        layer_density = round(
            layer_edge_count / (layer_node_count * (layer_node_count - 1)),
            4,
        )
    else:
        layer_density = 0

    layer_metrics_report = {
        "nodes": layer_node_count,
        "edges": layer_edge_count,
        "density": layer_density,
        "global_density": global_metrics.get("density", 0),
        "layer_scope": layer_path
    }

    # 4. Layer Artifacts Usage Report (pełny, nie-skompaktowany -
    # tu nie ma indeksów, więc samo filtrowanie jest bezpieczne,
    # nic nie trzeba przemapowywać).
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

    # 5. Layer Compact Artifacts Report
    #
    # compact_artifacts używa LICZB (indeksów do "modules")
    # zamiast nazw modułów w definer_module/consumers/usage.
    # Samo przefiltrowanie listy "modules" do modułów warstwy
    # BEZ przeliczenia indeksów przesunęłoby wszystkie indeksy
    # i wskazywałoby na ZŁE moduły (albo wyleciałoby poza zakres
    # listy) - to byłby gorszy błąd niż trzymanie pełnej,
    # niepotrzebnie dużej listy z poprawnymi indeksami.
    #
    # Poprawne podejście: zbudować NOWĄ, lokalną tabelę indeksów
    # obejmującą moduły z warstwy ORAZ każdy moduł spoza niej,
    # który faktycznie występuje jako definer/consumer/usage w
    # przefiltrowanych artefaktach (domknięcie, nie tylko
    # fizyczna zawartość katalogu), i przemapować każdy indeks
    # na nowy - dopiero wtedy da się bezpiecznie skrócić listę.
    compact_modules = global_compact_artifacts.get("modules", [])

    layer_global_indices = {
        idx for idx, mod in enumerate(compact_modules) if is_in_layer(mod)
    }

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

        for values in (artifact.get("usage", {}) or {}).values():
            for v in values or []:
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
            "definer_module": _remap(artifact.get("definer_module")),
            "consumers": sorted(
                v for v in (
                    _remap(c) for c in artifact.get("consumers", []) or []
                )
                if v is not None
            ),
        }

        usage = artifact.get("usage")
        if usage:
            remapped["usage"] = {
                category: sorted(
                    v for v in (_remap(x) for x in values) if v is not None
                )
                for category, values in sorted(usage.items())
            }

        layer_compact_artifacts[key] = remapped

    layer_compact_artifacts_report = {
        "_format_note": global_compact_artifacts.get("_format_note", ""),
        "runtime": global_compact_artifacts.get("runtime", {}),

        # Rozdzielone celowo - to DWIE różne liczby. layer_module_count
        # to fizyczna zawartość katalogu warstwy (== len(layer_modules)
        # wszędzie indziej w tym raporcie). compact_module_count to
        # rozmiar tabeli "modules" niżej, która jest DOMKNIĘCIEM: zawiera
        # też moduły spoza warstwy, jeśli są konsumentami/zależnościami
        # artefaktów zdefiniowanych w warstwie. Jeden klucz "module_count"
        # dla obu byłby niejednoznaczny - który z nich by opisywał?
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


def save_layer_reports(
    repo_name: str,
    layer_name: str,
    layer_reports: Dict[str, Dict[str, Any]],
    log=None
) -> None:
    """Zapisuje wygenerowane raporty warstwy do katalogu output/."""
    prefix = f"output/{repo_name}_{layer_name}"

    save_json(layer_reports["summary"], f"{prefix}_summary.json", log=log, label=f"raport warstwy [{layer_name}] - podsumowanie")
    save_json(layer_reports["structure"], f"{prefix}_structure.json", log=log, label=f"raport warstwy [{layer_name}] - struktura")
    save_json(layer_reports["metrics"], f"{prefix}_metrics.json", log=log, label=f"raport warstwy [{layer_name}] - metryki")
    save_json(layer_reports["artifacts"], f"{prefix}_artifacts.json", log=log, label=f"raport warstwy [{layer_name}] - artefakty")
    save_json(layer_reports["artifacts_compact"], f"{prefix}_artifacts_compact.json", log=log, label=f"raport warstwy [{layer_name}] - artefakty (compact)")


# ==========================================================
# SAVE ALL GLOBAL REPORTS
# ==========================================================

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
):
    """Fasada: zapisuje oddzielne pliki w katalogu output sekwencyjnie z orjson."""
    
    if log:
        log("Rozpoczynanie sekwencyjnego zapisu raportów...")

    all_collisions = (
        collisions
        if collisions is not None
        else validate_name_collisions(modules)
    )

    # Ścieżki zbierane w trakcie zapisu - zwracane na końcu, żeby
    # wywołujący (np. GUI) mógł od razu pokazać konkretne pliki,
    # zamiast na nowo je sobie odtwarzać ze wzorca nazw.
    summary_path = f"output/{repo_name}_summary.json"
    structure_path = f"output/{repo_name}_structure.json"
    collisions_path = f"output/{repo_name}_name_collisions.json"
    artifacts_path = f"output/{repo_name}_artifacts.json"
    artifacts_compact_path = f"output/{repo_name}_artifacts_compact.json"

    # 1. Raport podsumowujący (generate_summary_report ustawia
    # "generated_at" samodzielnie - jest teraz samowystarczalna,
    # więc bezpośrednie wywołanie tej funkcji gdziekolwiek indziej
    # da dokładnie taki sam kształt jak zapisany raport)
    summary_data = generate_summary_report(metrics, cycles, debt, collisions=all_collisions)
    save_json(
        summary_data,
        summary_path,
        log=log,
        label="raport podsumowujący"
    )
    
    # 2. Raport struktury grafu
    structure_data = generate_structure_report(graph.hard_edges, graph.soft_edges)
    save_json(
        structure_data,
        structure_path,
        log=log,
        label="raport struktury grafu"
    )
    
    # 3. Raport kolizji nazw (duplikatów)
    if log:
        log("Generowanie raportu kolizji nazw...")
    collisions_data = generate_collisions_report(modules, precomputed=all_collisions)
    save_json(
        collisions_data,
        collisions_path,
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
        artifacts_path,
        log=log,
        label="raport artefaktów",
    )

    # 5. Zwarta wersja raportu artefaktów
    if log:
        log("Generowanie zwartej wersji raportu artefaktów...")

    compact_artifact_data = compact_artifact_report(artifact_data)

    save_compact_artifact_report(
        compact_artifact_data,
        artifacts_compact_path,
    )

    if log:
        log("Wszystkie raporty zostały pomyślnie zapisane.")

    return {
        "saved": True,
        "repo": repo_name,
        "files": [
            summary_path,
            structure_path,
            collisions_path,
            artifacts_path,
            artifacts_compact_path,
        ],
        "reports": [
            "summary",
            "structure",
            "collisions",
            "artifacts",
            "artifacts_compact",
        ],
    }
