"""
contextor/core/reporting_engine/refactor_planner.py

Generates refactoring proposals for the architecture based on
input signals and hotspots.
"""


def _compute_refactor_plan(
    hotspots: list,
    clusters: list,
    total_modules: int,
    thresholds: dict,
    risk_map: dict | None = None,
) -> list[dict]:

    risk_map = risk_map or {}
    plan = []

    for h in hotspots[:10]:
        hotspot_type = h.get("type", "")
        score = h.get("score", 0)
        module_risk = risk_map.get(h.get("module", ""), 0)
        combined_score = score + module_risk

        if hotspot_type == "CONFIG_HUB":
            plan.append(
                {
                    "type": "KEEP_AS_SHARED_CONFIG",
                    "target": h["module"],
                    "priority": "INFO",
                    "reason": "central configuration module",
                }
            )
            continue

        if hotspot_type in ("HOTSPOT", "OUTBOUND_HOTSPOT", "HUB"):
            plan.append(
                {
                    "type": "EXTRACT_INTERFACE" if hotspot_type == "HUB" else "SPLIT_MODULE",
                    "target": h["module"],
                    "hotspot_score": score,
                    "module_risk": module_risk,
                    "priority": "HIGH"
                    if combined_score >= thresholds.get("critical_score", 0.85)
                    else "MEDIUM",
                    "reason": {
                        "HOTSPOT": "high coupling detected",
                        "HUB": "high dependency centrality",
                        "OUTBOUND_HOTSPOT": "too many outgoing dependencies",
                    }.get(hotspot_type, "architectural hotspot"),
                }
            )

    for cluster in clusters:
        if (
            len(cluster) >= thresholds["refactor_cluster_size"]
            and len(cluster) < total_modules * 0.6
        ):
            plan.append(
                {
                    "type": "SPLIT_PACKAGE",
                    "target_modules": cluster,
                    "priority": "MEDIUM",
                    "reason": "large isolated dependency cluster detected",
                }
            )

    return plan
