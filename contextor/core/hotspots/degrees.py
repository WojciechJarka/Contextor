"""
contextor/core/hotspots/degrees.py

Calculating in-degrees and out-degrees.
Uses Counter for performance.
"""

from collections import Counter


def compute_in_degree(edges: dict[str, set[str]]) -> dict[str, int]:
    # Ensure each node exists
    result = Counter()
    for _, targets in edges.items():
        result.update(targets)

    # Add empty entries for nodes without incoming dependencies
    return {node: result[node] for node in edges.keys() | result.keys()}


def compute_out_degree(edges: dict[str, set[str]]) -> dict[str, int]:
    return {node: len(targets) for node, targets in edges.items()}
