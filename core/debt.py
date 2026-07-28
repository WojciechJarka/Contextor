# -*- coding: utf-8 -*-

"""
core/debt.py

Calculates heuristic architectural debt score.
Evaluates cyclical dependencies, collision overlaps and soft edges
to determine pressure on maintainability.
"""

from typing import Dict, Set, List, Optional
from repo_guardian.core.graph.thresholds import get_thresholds

def _compute_cycle_penalty(cycles: List[List[str]]) -> int:
    """Calculates penalty by summing the number of nodes trapped within circular dependencies."""
    return sum(len(cycle) for cycle in cycles)

def _compute_soft_edge_penalty(soft_edges: Dict[str, Set[str]]) -> tuple[int, float]:
    count = sum(len(targets) for targets in soft_edges.values())
    return count, round(count * 0.5, 4)

def _compute_cluster_penalty(clusters: List[List[str]], hotspots: List[Dict], thresholds: dict) -> int:
    config_modules = {
        hotspot.get("module") for hotspot in (hotspots or [])
        if hotspot.get("type") == "CONFIG_HUB"
    }

    penalty = 0
    for cluster in clusters or []:
        if len(cluster) < thresholds["cluster_size"]:
            continue
        if not config_modules.isdisjoint(cluster):
            continue
        penalty += 1
    return penalty

def _compute_hotspot_penalty(hotspots: List[Dict], critical_score: float) -> int:
    return sum(1 for hotspot in (hotspots or []) if hotspot.get("score", 0) >= critical_score)

def _compute_collision_penalty(collisions: List) -> tuple[int, float]:
    real_collisions = [c for c in (collisions or []) if not getattr(c, "is_identical", False)]
    return len(real_collisions), round(len(real_collisions) * 1.5, 4)

def compute_debt(
    hard_edges: Dict[str, Set[str]],
    soft_edges: Dict[str, Set[str]],
    cycles: List[List[str]],
    metrics: Dict,
    clusters: Optional[List[List[str]]] = None,
    hotspots: Optional[List[Dict]] = None,
    collisions: Optional[List] = None,
) -> Dict:
    """
    Computes an overarching metric representing technical debt accumulation.
    
    Factors included: Circular dependencies, unverified 'soft' calls,
    high-risk hotspots, clusters containing config hubs, and namespace collisions.
    Returns normalized score alongside human-readable interpretations.
    """
    thresholds = get_thresholds(metrics.get("nodes", 0))

    cycle_penalty = _compute_cycle_penalty(cycles)
    soft_edges_count, soft_edge_penalty = _compute_soft_edge_penalty(soft_edges)
    cluster_penalty = _compute_cluster_penalty(clusters, hotspots, thresholds)
    hotspot_penalty = _compute_hotspot_penalty(hotspots, thresholds["critical_score"])
    collision_count, collision_penalty = _compute_collision_penalty(collisions)

    score = (cycle_penalty * 2) + soft_edge_penalty + cluster_penalty + hotspot_penalty + collision_penalty
    edge_count = max(metrics.get("edges", 1), 1)
    normalized_score = round(score / edge_count, 4)

    if normalized_score < 0.05:
        label = "low"
    elif normalized_score < 0.15:
        label = "moderate"
    elif normalized_score < 0.30:
        label = "high"
    else:
        label = "critical"

    interpretation = {
        "label": label,
        "breakdown": {
            "collisions": f"{collision_count} real collisions (+{collision_penalty})" if collision_count else "none",
            "soft_edges": f"{soft_edges_count} soft edges (+{soft_edge_penalty})" if soft_edges_count else "none",
            "cycles": f"{cycle_penalty} nodes in cycles (+{cycle_penalty * 2})" if cycle_penalty else "none",
            "hotspots": f"{hotspot_penalty} above critical threshold (+{hotspot_penalty})" if hotspot_penalty else "none above critical threshold"
        }
    }

    return {
        "score": round(score, 4),
        "cycle_penalty": cycle_penalty,
        "soft_edge_penalty": soft_edge_penalty,
        "soft_edges_count": soft_edges_count,
        "cluster_penalty": cluster_penalty,
        "hotspot_penalty": hotspot_penalty,
        "collision_penalty": collision_penalty,
        "collision_count": collision_count,
        "normalized": normalized_score,
        "interpretation": interpretation,
        "model": {
            "type": "heuristic_architecture_pressure",
            "scale": "unbounded",
        },
    }
