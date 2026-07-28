# -*- coding: utf-8 -*-

"""
repo_guardian/core/reporting_engine/risk_signals.py

Calculating risk level, evaluating dependency centralization and
hotspots for reporting purposes.
"""

def _compute_soft_dependencies(graph: dict) -> list[dict]:
    dependencies = []
    for source, targets in sorted(graph["soft_edges"].items()):
        for target in sorted(targets):
            dependencies.append({
                "from": source,
                "to": target,
                "reason": "resolver_fallback",
            })
    return sorted(dependencies, key=lambda x: (x["from"], x["to"]))

def _compute_module_risk(metrics: dict, graph: dict) -> dict:
    max_in = max(metrics.get("max_in_degree", 1), 1)
    max_out = max(metrics.get("max_out_degree", 1), 1)
    max_soft = max(metrics.get("max_soft_out_degree", 1), 1)

    nodes = set(graph["hard_edges"])
    for targets in graph["hard_edges"].values():
        nodes.update(targets)

    risks = {}
    for node in sorted(nodes):
        deps = graph["hard_edges"].get(node, [])
        in_deg = sum(
            node in targets
            for targets in graph["hard_edges"].values()
        )
        out_deg = len(deps)
        soft = len(graph["soft_edges"].get(node, []))
        soft_score = min(soft / max_soft, 1)

        score = (in_deg / max_in) * 0.5 + (out_deg / max_out) * 0.3 + soft_score * 0.2
        if node.startswith("config."):
            score *= 0.25

        risks[node] = round(score, 4)

    return risks

def _compute_risk_summary(risk_map: dict, critical_score: float) -> dict:
    if not risk_map:
        return {"critical": [], "average": 0, "max": 0}

    values = list(risk_map.values())
    critical = sorted(
        module
        for module, score in risk_map.items()
        if score >= critical_score
    )

    return {
        "critical": critical,
        "average": round(sum(values) / len(values), 4),
        "max": round(max(values), 4),
    }

def _compute_inspection_targets(hotspots: list[dict]) -> list[dict]:
    targets = []
    for priority, item in enumerate(hotspots[:10], start=1):
        signals = []
        if item.get("type") == "CONFIG_HUB":
            signals.append("shared_configuration_dependency")
        if item.get("type") == "HOTSPOT":
            signals.append("high_coupling")
        if item.get("type") == "OUTBOUND_HOTSPOT":
            signals.append("high_out_degree")
        if item.get("type") == "HUB":
            signals.append("high_dependency_centrality")
        
        if item.get("out_degree", 0) >= 10:
            signals.append("high_out_degree")
        if item.get("in_degree", 0) >= 10:
            signals.append("high_in_degree")
        if item.get("in_degree", 0) >= 20:
            signals.append("many_dependents")

        if signals:
            targets.append({
                "module": item["module"],
                "priority": priority,
                "signals": sorted(set(signals)),
            })
    return targets
