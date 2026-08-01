"""
contextor/core/analysis/call_chain.py

Finds entry chains for a given module (shortest paths from known entry points).
"""

from collections import deque

ENTRY_POINT_HEURISTICS = {"main", "cli", "run", "app", "__main__"}


def _is_entry_point(module_id: str) -> bool:
    name = module_id.split(".")[-1]
    return name in ENTRY_POINT_HEURISTICS


def build_entry_chains(target_module_id: str, hard_edges: dict) -> list[str]:
    """
    Reverse BFS to find paths from entry points to the target module.
    """
    # Reverse graph: node -> who imports node
    reverse_graph = {}
    for src, targets in hard_edges.items():
        for tgt in targets:
            reverse_graph.setdefault(tgt, set()).add(src)

    if target_module_id not in reverse_graph:
        return []

    visited = {target_module_id}
    queue = deque([[target_module_id]])
    paths = []

    # Limit search depth to prevent infinite loops / long execution
    max_depth = 5

    while queue:
        path = queue.popleft()
        current = path[-1]

        if len(path) > max_depth:
            continue

        if _is_entry_point(current) and current != target_module_id:
            # Revert path so it looks like: entry_point -> ... -> target
            reversed_path = path[::-1]
            paths.append(" -> ".join(reversed_path))
            continue

        for neighbor in reverse_graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return sorted(paths)


__all__ = ["build_entry_chains"]
