# -*- coding: utf-8 -*-

"""
repo_guardian/core/thresholds.py

Central heuristics configuration.

Contains:
- relative hotspot ranking thresholds
- repo-size dependent cluster thresholds
"""


def get_thresholds(nodes: int) -> dict:
    """
    Returns adaptive thresholds.

    Ranking:
    - independent of repo size
    - operates on 0-1 percentiles

    Structure:
        0.90 = top 10%
        0.85 = top 15%
        0.75 = top 25%
    """


    thresholds = {


        # ===============================
        # HOTSPOT RANKING
        # ===============================


        "hub_percentile":
            0.90,


        "hotspot_percentile":
            0.85,


        "outbound_percentile":
            0.90,


        "low_complexity_percentile":
            0.35,



        # ===============================
        # LEGACY SCORE COMPATIBILITY
        # ===============================

        # used by older modules

        "inspection_score":
            0.50,


        "hotspot_score":
            0.70,


        "critical_score":
            0.85,

    }



    # ===============================
    # CLUSTER SCALING
    # ===============================


    if nodes <= 30:

        thresholds.update({

            "cluster_size":
                8,


            "refactor_cluster_size":
                10,

        })


    elif nodes <= 80:

        thresholds.update({

            "cluster_size":
                15,


            "refactor_cluster_size":
                18,

        })


    elif nodes <= 200:

        thresholds.update({

            "cluster_size":
                25,


            "refactor_cluster_size":
                30,

        })


    else:

        thresholds.update({

            "cluster_size":
                40,


            "refactor_cluster_size":
                50,

        })


    return thresholds
