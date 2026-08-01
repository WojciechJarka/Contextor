"""
contextor/core/context/dependencies.py

Responsibility:
- incoming/outgoing and transitive BFS dependencies
"""

from collections import deque


def find_dependents(module_id: str, hard_edges: dict) -> list[str]:
    result = {source for source, targets in hard_edges.items() if module_id in targets}
    return sorted(result)


def find_soft_dependents(module_id: str, soft_edges: dict) -> list[str]:
    result = {source for source, targets in soft_edges.items() if module_id in targets}
    return sorted(result)


def find_transitive_dependents(module_id: str, hard_edges: dict, max_depth: int = 6) -> list:
    """
    BFS on inverted dependency graph.
    Returns all consumers (direct and indirect).
    """
    visited = {}  # module -> depth
    queue = deque([(module_id, 0)])

    # Precalculated inverse graph for ultra-fast BFS (without iterating over all hard_edges)
    reverse_edges = {}
    for src, targets in hard_edges.items():
        for tgt in targets:
            reverse_edges.setdefault(tgt, set()).add(src)

    while queue:
        current, depth = queue.popleft()

        if depth >= max_depth:
            continue

        for src in reverse_edges.get(current, set()):
            if src not in visited and src != module_id:
                visited[src] = depth + 1
                queue.append((src, depth + 1))

    return [{"module": m, "depth": d} for m, d in sorted(visited.items(), key=lambda x: x[1])]
