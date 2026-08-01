"""
contextor/core/metrics.py

GRAPH METRICS ENGINE
Responsibilities: basic statistics of the dependency graph (nodes, edges, degrees).
"""


def compute_graph_metrics(
    hard_edges: dict[str, set[str]], soft_edges: dict[str, set[str]] | None = None
) -> dict:
    """Complete set of metrics optimized for large graphs (with dead branches removed)."""

    # Inline count_edges
    hard_count = sum(len(targets) for targets in hard_edges.values())
    soft_count = sum(len(targets) for targets in (soft_edges or {}).values())

    # Inline count_nodes
    nodes_set = set(hard_edges.keys())
    for targets in hard_edges.values():
        nodes_set.update(targets)
    for targets in (soft_edges or {}).values():
        nodes_set.update(targets)
    nodes = len(nodes_set)

    # Inline compute_degrees (only for hard_edges per original specification)
    in_degree = {node: 0 for node in hard_edges}
    out_degree = {node: len(targets) for node, targets in hard_edges.items()}

    for targets in hard_edges.values():
        for target in targets:
            in_degree[target] = in_degree.get(target, 0) + 1

    return {
        "nodes": nodes,
        "edges_hard": hard_count,
        "edges_soft": soft_count,
        "edges_total": hard_count + soft_count,
        "density_hard": round(hard_count / (nodes * max(nodes - 1, 1)), 4) if nodes > 1 else 0,
        "in_degree_max": max(in_degree.values(), default=0),
        "out_degree_max": max(out_degree.values(), default=0),
    }
