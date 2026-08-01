"""
contextor/core/domain/graph.py

Dependency graph model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectGraph:
    """
    Gotowy graf zależności.
    """

    hard_edges: dict[str, set[str]]

    soft_edges: dict[str, set[str]]
