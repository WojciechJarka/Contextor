# -*- coding: utf-8 -*-

"""
repo_guardian/core/context/signals.py

Responsibility:
- architectural signals
"""

from .dependencies import find_dependents, find_soft_dependents

def architecture_signals(
    module_id,
    hard_edges,
    soft_edges,
    hotspots,
    cycles,
    node_count=None
):
    """
    Returns actual architectural signals.
    Does not calculate score.
    """
    signals = set()

    # DEPENDENCY FACTS
    incoming = find_dependents(module_id, hard_edges)
    outgoing = hard_edges.get(module_id, set())

    if incoming:
        signals.add("has_dependents")
    if outgoing:
        signals.add("has_dependencies")

    # CYCLES
    cycle_nodes = {node for cycle in (cycles or []) for node in cycle}
    if module_id in cycle_nodes:
        signals.add("cycle_member")

    # SOFT DEPENDENCIES
    if soft_edges.get(module_id):
        signals.add("contains_soft_dependencies")
    if module_id in find_soft_dependents(module_id, soft_edges):
        signals.add("has_soft_dependents")

    # HOTSPOT FACTS
    for hotspot in (hotspots or []):
        if hotspot.get("module") != module_id:
            continue

        hotspot_type = hotspot.get("type")
        if hotspot_type in {"HOTSPOT", "OUTBOUND_HOTSPOT", "HUB", "CONFIG_HUB"}:
            signals.add("hotspot")
        if hotspot_type == "CONFIG_HUB":
            signals.add("config_hub")

    return sorted(signals)
