# -*- coding: utf-8 -*-

"""
repo_guardian/core/domain/graph.py

Dependency graph model.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class EdgeInfo:
    target: str
    edge_type: str
    confidence: float
    reason: str
    count: int = 1

@dataclass(frozen=True)
class ProjectGraph:
    """
    Gotowy graf zależności.
    """

    hard_edges: dict[str, set[str]]

    soft_edges: dict[str, set[str]]

