# -*- coding: utf-8 -*-

"""
repo_guardian/core/module/graph.py

Graph contracts
"""


from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectGraph:

    hard_edges: dict[str, set[str]]

    soft_edges: dict[str, set[str]]
