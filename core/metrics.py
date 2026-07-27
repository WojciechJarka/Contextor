# -*- coding: utf-8 -*-

"""
repo_guardian/core/metrics.py

GRAPH METRICS ENGINE

Odpowiedzialność:

- podstawowe statystyki grafu zależności
- liczby węzłów
- liczby krawędzi
- stopnie wejścia/wyjścia

Nie ocenia:
- jakości architektury
- ryzyka
- długu
- refaktoryzacji


Źródło prawdy:

    ProjectGraph
"""


from typing import (
    Dict,
    Set,
)



# ==========================================================
# BASIC COUNTERS
# ==========================================================


def count_nodes(
    hard_edges: Dict[str, Set[str]],
    soft_edges: Dict[str, Set[str]] | None = None,
) -> int:
    """
    Liczy wszystkie moduły
    obecne w grafie.
    """


    nodes = set(
        hard_edges.keys()
    )


    for targets in hard_edges.values():

        nodes.update(
            targets
        )



    for targets in (
        soft_edges or {}
    ).values():

        nodes.update(
            targets
        )



    return len(
        nodes
    )



def count_edges(
    edges: Dict[str, Set[str]]
) -> int:
    """
    Liczy krawędzie skierowane.
    """


    return sum(

        len(targets)

        for targets in edges.values()

    )



# ==========================================================
# DEGREE METRICS
# ==========================================================


def compute_degrees(
    edges: Dict[str, Set[str]]
) -> dict:
    """
    Zwraca:

    - in_degree
    - out_degree
    """


    in_degree = {

        node: 0

        for node in edges

    }


    out_degree = {

        node:
            len(targets)

        for node, targets
        in edges.items()

    }



    for targets in edges.values():

        for target in targets:

            in_degree.setdefault(
                target,
                0
            )

            in_degree[target] += 1



    return {

        "in_degree":
            in_degree,

        "out_degree":
            out_degree,

    }



# ==========================================================
# PUBLIC API
# ==========================================================


def compute_graph_metrics(
    hard_edges: Dict[str, Set[str]],
    soft_edges: Dict[str, Set[str]] | None = None,
) -> dict:
    """
    Kompletny zestaw metryk grafu.

    Przykład:

    {
        "nodes": 42,
        "hard_edges": 85,
        "soft_edges": 12,
        "edges": 97,
        "average_degree": 2.3
    }

    """


    hard_count = count_edges(
        hard_edges
    )


    soft_count = count_edges(
        soft_edges or {}
    )


    nodes = count_nodes(
        hard_edges,
        soft_edges,
    )



    total_edges = (
        hard_count
        +
        soft_count
    )



    average_degree = 0.0


    if nodes:

        average_degree = round(

            total_edges / nodes,

            4

        )



       # in_degree/out_degree muszą liczyć się z tej samej bazy co
    # "edges" i "average_degree" wyżej (hard + soft)

    combined_edges = {

        node: {

            (
                edge.target
                if hasattr(edge, "target")
                else edge
            )

            for edge in (
                set(hard_edges.get(node, []))
                |
                set((soft_edges or {}).get(node, []))
            )

        }

        for node in (
            set(hard_edges)
            |
            set(soft_edges or {})
        )

    }


    degrees = compute_degrees(
        combined_edges
    )



    return {

        "nodes":
            nodes,


        "hard_edges":
            hard_count,


        "soft_edges":
            soft_count,


        "edges":
            total_edges,


        "average_degree":
            average_degree,


        "in_degree":
            degrees["in_degree"],


        "out_degree":
            degrees["out_degree"],


        "model":
        {
            "type":
                "directed_dependency_graph",

            "includes":
                [
                    "hard_edges",
                    "soft_edges",
                ],
        },

    }
