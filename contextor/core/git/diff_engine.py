"""
contextor/core/git/diff_engine.py

Diff engine for JSON reports and quality regression detection.
"""

def diff_reports(old_summary: dict, new_summary: dict) -> dict:
    """
    Compares two Contextor summary reports and extracts metric deltas.
    """
    diff_stats = {
        "metrics": {},
        "debt": {},
        "layers": {},
        "is_empty": True
    }
    
    old_metrics = old_summary.get("metrics", {})
    new_metrics = new_summary.get("metrics", {})
    
    metric_keys = ["nodes", "edges_total", "edges_hard", "edges_soft", "in_degree_max", "out_degree_max"]
    for key in metric_keys:
        old_val = old_metrics.get(key, 0)
        new_val = new_metrics.get(key, 0)
        if old_val != new_val:
            diff_stats["metrics"][key] = {"old": old_val, "new": new_val, "delta": new_val - old_val}
            diff_stats["is_empty"] = False

    old_debt = old_summary.get("debt_summary", {})
    new_debt = new_summary.get("debt_summary", {})
    
    debt_keys = ["hotspot_count", "isolated_count", "total_score"]
    for key in debt_keys:
        old_val = old_debt.get(key, 0)
        new_val = new_debt.get(key, 0)
        if old_val != new_val:
            # handle floats for total_score
            delta = round(new_val - old_val, 4) if isinstance(new_val, float) else new_val - old_val
            diff_stats["debt"][key] = {"old": old_val, "new": new_val, "delta": delta}
            diff_stats["is_empty"] = False

    old_layers = {layer.get("layer"): layer for layer in old_summary.get("layer_index", [])}
    new_layers = {layer.get("layer"): layer for layer in new_summary.get("layer_index", [])}
    
    all_layer_names = set(old_layers.keys()).union(set(new_layers.keys()))
    for name in all_layer_names:
        old_l = old_layers.get(name, {})
        new_l = new_layers.get(name, {})
        
        l_diff = {}
        for key in ["module_count", "cycles_count", "hotspot_count"]:
            old_val = old_l.get(key, 0)
            new_val = new_l.get(key, 0)
            if old_val != new_val:
                l_diff[key] = {"old": old_val, "new": new_val, "delta": new_val - old_val}
        
        if l_diff:
            diff_stats["layers"][name] = l_diff
            diff_stats["is_empty"] = False
            
    return diff_stats


def detect_regression(diff_stats: dict) -> str:
    """
    Evaluates if technical debt or hotspots increased.
    Returns: "REGRESSION", "IMPROVED", or "UNCHANGED"
    """
    if diff_stats.get("is_empty"):
        return "UNCHANGED"
        
    debt_diff = diff_stats.get("debt", {})
    
    total_score_delta = debt_diff.get("total_score", {}).get("delta", 0)
    hotspot_delta = debt_diff.get("hotspot_count", {}).get("delta", 0)
    isolated_delta = debt_diff.get("isolated_count", {}).get("delta", 0)
    
    if total_score_delta > 0 or hotspot_delta > 0:
        return "REGRESSION"
    elif total_score_delta < 0 or hotspot_delta < 0 or isolated_delta < 0:
        return "IMPROVED"
        
    return "UNCHANGED"
