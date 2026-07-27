# -*- coding: utf-8 -*-

"""
repo_guardian/core/report_models.py

GRAPH REPORT CONTRACTS

Transportowe modele danych dla grafu zależności.

Nie zawiera:
- logiki
- walidacji
- scoringu
- analizy architektury

Źródło:
    graph builder

Cel:
    stabilny transport EdgeInfo
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeInfo:
    """
    Immutable dependency edge contract.
    """

    target: str

    edge_type: str

    confidence: float

    reason: str

    count: int = 1


__all__ = [
    "EdgeInfo",
]
