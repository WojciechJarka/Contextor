# -*- coding: utf-8 -*-

"""
repo_guardian/core/hotspots.py

GRAPH HOTSPOT ANALYZER

Analizuje ryzyko modułów
na podstawie grafu zależności.

Nie ocenia kodu.
Nie zna AST.
Nie zna LLM.

Źródło prawdy:
    ProjectGraph.hard_edges

Model:
- degree extraction
- relative ranking
- normalized scoring
- threshold classification

Kategorie:

HUB:
    wysoki wpływ względny,
    niski koszt zależności.

HOTSPOT:
    wysoki wpływ + wysoka aktywność.

OUTBOUND_HOTSPOT:
    moduł silnie zależny od innych.

CONFIG_HUB:
    hub konfiguracji traktowany specjalnie.
"""


from typing import Dict, Set, List
import math

from repo_guardian.core.thresholds import get_thresholds


# ==========================================================
# DEGREE CALCULATION
# ==========================================================


def compute_in_degree(
    edges: Dict[str, Set[str]]
) -> dict[str, int]:

    result = {
        node: 0
        for node in edges
    }


    for _, targets in edges.items():

        for target in targets:

            result.setdefault(
                target,
                0
            )

            result[target] += 1


    return result



def compute_out_degree(
    edges: Dict[str, Set[str]]
) -> dict[str, int]:

    return {
        node: len(targets)
        for node, targets in edges.items()
    }



# ==========================================================
# NORMALIZATION
# ==========================================================


def _percentile_map(
    values: dict[str, int]
) -> dict[str, float]:
    """
    Relative ranking 0-1.

    Nie zależy od wielkości repo.
    """

    if not values:
        return {}


    ordered = sorted(
        values.items(),
        key=lambda item: item[1]
    )


    total = len(ordered)

    result = {}


    for index, (key, _) in enumerate(ordered):

        if total == 1:
            result[key] = 1.0

        else:
            result[key] = round(
                index / (total - 1),
                4
            )


    return result



def _log_normalize(
    values: dict[str, int]
) -> dict[str, float]:

    if not values:
        return {}


    max_value = max(
        values.values()
    )


    if max_value == 0:
        return {
            key: 0.0
            for key in values
        }


    denominator = math.log(
        1 + max_value
    )


    return {

        key:
            round(
                math.log(
                    1 + value
                )
                /
                denominator,
                4
            )

        for key, value in values.items()
    }



def _geometric_map(
    incoming: dict[str, int],
    outgoing: dict[str, int]
) -> dict[str, float]:

    values = {}


    maximum = 0


    for node in set(incoming) | set(outgoing):

        value = math.sqrt(
            incoming.get(node, 0)
            *
            outgoing.get(node, 0)
        )

        values[node] = value

        maximum = max(
            maximum,
            value
        )


    if maximum == 0:

        return {
            node: 0.0
            for node in values
        }


    return {

        node:
            round(
                value / maximum,
                4
            )

        for node, value in values.items()

    }



# ==========================================================
# SCORE
# ==========================================================


def compute_hotspot_score(
    impact_percentile: float,
    complexity_percentile: float,
    log_score: float,
    geometric_score: float,
) -> float:
    """
    Łączy kilka metod normalizacji.

    Każda metoda wnosi 1/3 wpływu.
    """

    score = (

        impact_percentile

        +

        complexity_percentile

        +

        log_score

        +

        geometric_score

    ) / 4


    return round(
        score,
        4
    )



# ==========================================================
# CLASSIFICATION
# ==========================================================


def classify_module(
    impact: float,
    complexity: float,
    score: float,
    thresholds: dict,
    in_degree: int = None,
    out_degree: int = None,
) -> str:
    """
    Klasyfikacja względna.

    ISOLATED liczone na surowych stopniach,
    nie na percentylach (percentyle przy
    remisach nie dają czystego zera).
    """

    if (
        in_degree == 0
        and
        out_degree == 0
    ):
        return "ISOLATED"



    if (
        impact >= thresholds["hub_percentile"]
        and
        complexity <= thresholds["low_complexity_percentile"]
    ):
        return "HUB"



    if (
        impact >= thresholds["hotspot_percentile"]
        and
        complexity >= thresholds["hotspot_percentile"]
    ):
        return "HOTSPOT"



    if (
        complexity >= thresholds["outbound_percentile"]
    ):
        return "OUTBOUND_HOTSPOT"



    return "NORMAL"



def _dominant_factor(
    components: dict[str, float]
) -> str:
    """
    Zwraca dominujący składnik
    wpływający na wynik hotspotu.

    Wszystkie komponenty są już
    znormalizowane do zakresu 0-1.
    """

    return max(
        components,
        key=components.get
    )



def _build_hotspot_explanation(
    kind: str,
    impact: float,
    complexity: float,
    log_score: float,
    geometric_score: float,
) -> dict:
    """
    Wyjaśnienie klasyfikacji.

    Nie jest to przyczyna biznesowa,
    tylko dominujący sygnał modelu.
    """

    components = {
        "impact": impact,
        "complexity": complexity,
        "log_score": log_score,
        "geometric_score": geometric_score,
    }


    return {
        "classification": kind,

        "aggregation":
            "equal_average",

        "dominant_factor":
            _dominant_factor(
                components
            ),

        "metrics":
            components,
    }
    
def detect_hotspots(
    hard_edges: Dict[str, Set[str]]
) -> List[dict]:
    """
    Analizuje graf zależności.

    Returns:

    [
        {
            "module": "core.types",
            "type": "HUB",
            "score": 0.91,
            "in_degree": 5,
            "out_degree": 1
        }
    ]
    """


    modules = set(
        hard_edges.keys()
    )


    in_degree = compute_in_degree(
        hard_edges
    )

    out_degree = compute_out_degree(
        hard_edges
    )


    modules.update(
        in_degree.keys()
    )

    modules.update(
        out_degree.keys()
    )


    impact_map = _percentile_map(
        in_degree
    )


    complexity_map = _percentile_map(
        out_degree
    )


    log_map = _log_normalize(
        {
            module:
                in_degree.get(module, 0)
                +
                out_degree.get(module, 0)

            for module in modules
        }
    )


    geometric_map = _geometric_map(
        in_degree,
        out_degree
    )


    thresholds = get_thresholds(
        len(modules)
    )


    results = []


    for module in modules:

        incoming = in_degree.get(
            module,
            0
        )

        outgoing = out_degree.get(
            module,
            0
        )


        impact = impact_map.get(
            module,
            0.0
        )

        complexity = complexity_map.get(
            module,
            0.0
        )


        score = compute_hotspot_score(
            impact,
            complexity,
            log_map.get(
                module,
                0.0
            ),
            geometric_map.get(
                module,
                0.0
            )
        )


        kind = classify_module(
            impact,
            complexity,
            score,
            thresholds,
            incoming,
            outgoing,
        )


        if kind == "HUB":

            if (
                module.endswith("settings")
                or
                module.endswith("config")
            ):
                kind = "CONFIG_HUB"



        if kind != "NORMAL":

            if kind == "ISOLATED":
                score = 0.0
                impact = 0.0
                complexity = 0.0


            results.append(
                {
                    "module": module,

                    "type": kind,

                    "score": score,

                    "explanation":
                        _build_hotspot_explanation(
                            kind,

                            impact,

                            complexity,

                            log_map.get(
                                module,
                                0.0
                            ),

                            geometric_map.get(
                                module,
                                0.0
                            ),
                        ),

                    "impact_percentile":
                        impact,

                    "complexity_percentile":
                        complexity,

                    "in_degree":
                        incoming,

                    "out_degree":
                        outgoing,
                }
            )


    return sorted(
        results,
        key=lambda item: (
            -item["score"],
            item["module"]
        )
    )
