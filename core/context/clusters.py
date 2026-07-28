# -*- coding: utf-8 -*-

"""
repo_guardian/core/context/clusters.py

Responsibility:
- local dependency cluster
"""

def find_cluster(module_id: str, hard_edges: dict) -> list[str]:
    """
    Returns local graph fragment:
    - own dependencies
    - module users
    """
    cluster = {module_id}
    cluster.update(hard_edges.get(module_id, []))

    for source, targets in hard_edges.items():
        if module_id in targets:
            cluster.add(source)

    return sorted(cluster)
