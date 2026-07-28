# -*- coding: utf-8 -*-

"""
repo_guardian/core/hotspots/classification.py

Klasyfikowanie węzłów i generowanie score na bazie ujednoliconych metryk.
"""

def compute_hotspot_score(
    impact_percentile: float,
    complexity_percentile: float,
    log_score: float,
    geometric_score: float,
) -> float:
    score = (impact_percentile + complexity_percentile + log_score + geometric_score) / 4
    return round(score, 4)

def classify_module(
    impact: float,
    complexity: float,
    score: float,
    thresholds: dict,
    in_degree: int = None,
    out_degree: int = None,
) -> str:
    if in_degree == 0 and out_degree == 0:
        return "ISOLATED"
    
    if impact >= thresholds["hub_percentile"] and complexity <= thresholds["low_complexity_percentile"]:
        return "HUB"
        
    if impact >= thresholds["hotspot_percentile"] and complexity >= thresholds["hotspot_percentile"]:
        return "HOTSPOT"
        
    if complexity >= thresholds["outbound_percentile"]:
        return "OUTBOUND_HOTSPOT"
        
    return "NORMAL"

def _dominant_factor(components: dict[str, float]) -> str:
    return max(components, key=components.get)

def _build_hotspot_explanation(
    kind: str,
    impact: float,
    complexity: float,
    log_score: float,
    geometric_score: float,
) -> dict:
    components = {
        "impact": impact,
        "complexity": complexity,
        "log_score": log_score,
        "geometric_score": geometric_score,
    }
    return {
        "classification": kind,
        "aggregation": "equal_average",
        "dominant_factor": _dominant_factor(components),
        "metrics": components,
    }
