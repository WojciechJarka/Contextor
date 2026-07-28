# -*- coding: utf-8 -*-

"""
repo_guardian/core/reporting_engine/graph_aggregators.py

Tools supporting graph operations for reporting purposes.
"""

from collections import defaultdict, deque

def _build_undirected_graph(hard_edges: dict) -> dict:
    graph = defaultdict(set)
    for src, targets in sorted(hard_edges.items()):
        for tgt in sorted(targets):
            graph[src].add(tgt)
            graph[tgt].add(src)
    return graph

def _connected_components(graph: dict) -> list[list[str]]:
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
        clusters.append(sorted(component))

    return sorted(clusters, key=len, reverse=True)
