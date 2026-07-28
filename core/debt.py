# -*- coding: utf-8 -*-

"""
repo_guardian/core/debt.py

Obliczanie heurystycznego długu architektonicznego.

Model:
- cykle → presja zależności
- soft_edges → niepewność resolvera
- duże klastry → potencjalne granice refaktoryzacji
- hotspoty → centralne przeciążenie grafu

To nie jest formalny pomiar jakości kodu.

To warstwa sygnałów dla dalszej analizy.
"""



from typing import (
    Dict,
    Set,
    List,
    Optional,
)


from repo_guardian.core.thresholds import (
    get_thresholds
)



# ==========================================================
# PUBLIC API
# ==========================================================


def compute_debt(
    hard_edges: Dict[str, Set[str]],
    soft_edges: Dict[str, Set[str]],
    cycles: List[List[str]],
    metrics: Dict,
    clusters: Optional[List[List[str]]] = None,
    hotspots: Optional[List[Dict]] = None,
    collisions: Optional[List] = None,
) -> Dict:
    """
    Oblicza heurystyczną presję architektoniczną.

    Składowe:

    cycle_penalty:
        liczba elementów w cyklach

    soft_edge_penalty:
        niepewne zależności

    cluster_penalty:
        duże klastry

    hotspot_penalty:
        moduły przekraczające próg krytyczny

    collision_penalty:
        realne (nie identyczne) kolizje nazw API między modułami -
        dwie różne definicje pod tą samą nazwą to duże ryzyko
        pomyłki dla kogokolwiek (człowieka albo LLM-a) edytującego
        repo bez świadomości duplikatu.
    """



    # ======================================================
    # CYCLES
    # ======================================================


    cycle_penalty = sum(
        len(cycle)
        for cycle in cycles
    )



    # ======================================================
    # SOFT EDGES
    # ======================================================


    soft_edges_count = sum(

        len(targets)

        for targets in soft_edges.values()

    )


    soft_edge_penalty = round(
        soft_edges_count * 0.5,
        4
    )



    # ======================================================
    # ADAPTIVE THRESHOLDS
    # ======================================================


    thresholds = get_thresholds(
        metrics.get(
            "nodes",
            0
        )
    )



    # ======================================================
    # CLUSTERS
    # ======================================================


    config_modules = {

        hotspot.get("module")

        for hotspot in (hotspots or [])

        if hotspot.get("type")
        ==
        "CONFIG_HUB"

    }



    cluster_penalty = 0


    for cluster in clusters or []:


        if len(cluster) < thresholds["cluster_size"]:

            continue



        # config hubs są oczekiwanym
        # elementem architektury,
        # nie automatycznym długiem

        if any(
            module in config_modules
            for module in cluster
        ):

            continue



        cluster_penalty += 1



    # ======================================================
    # HOTSPOTS
    # ======================================================


    hotspot_penalty = 0


    critical_score = thresholds[
        "critical_score"
    ]



    for hotspot in hotspots or []:


        score = hotspot.get(
            "score",
            0
        )


        if score >= critical_score:

            hotspot_penalty += 1



    # ======================================================
    # NAME COLLISIONS
    # ======================================================


    real_collisions = [
        c for c in (collisions or [])
        if not getattr(c, "is_identical", False)
    ]


    collision_penalty = round(
        len(real_collisions) * 1.5,
        4
    )


    # ======================================================
    # FINAL SCORE
    # ======================================================


    score = (

        cycle_penalty * 2

        +

        soft_edge_penalty

        +

        cluster_penalty

        +

        hotspot_penalty

        +

        collision_penalty

    )


    edge_count = metrics.get(
        "edges",
        1
    )


    if edge_count <= 0:

        edge_count = 1



    normalized_score = round(score / edge_count, 4)

    if normalized_score < 0.05:
        label = "low"
    elif normalized_score < 0.15:
        label = "moderate"
    elif normalized_score < 0.30:
        label = "high"
    else:
        label = "critical"

    interpretation = {
        "label": label,
        "breakdown": {
            "collisions": f"{len(real_collisions)} real collisions (+{collision_penalty})" if real_collisions else "none",
            "soft_edges": f"{soft_edges_count} soft edges (+{soft_edge_penalty})" if soft_edges_count else "none",
            "cycles": f"{cycle_penalty} nodes in cycles (+{cycle_penalty * 2})" if cycle_penalty else "none",
            "hotspots": f"{hotspot_penalty} above critical threshold (+{hotspot_penalty})" if hotspot_penalty else "none above critical threshold"
        }
    }

    return {

        "score":
            round(
                score,
                4
            ),


        "cycle_penalty":
            cycle_penalty,


        "soft_edge_penalty":
            soft_edge_penalty,


        "soft_edges_count":
            soft_edges_count,


        "cluster_penalty":
            cluster_penalty,


        "hotspot_penalty":
            hotspot_penalty,


        "collision_penalty":
            collision_penalty,


        "collision_count":
            len(real_collisions),


        "normalized":
            normalized_score,


        "interpretation":
            interpretation,


        "model":
        {
            "type":
                "heuristic_architecture_pressure",

            "scale":
                "unbounded",

        },

    }
