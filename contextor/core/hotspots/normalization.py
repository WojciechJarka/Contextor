"""
contextor/core/hotspots/normalization.py

Normalizacja i ujednolicanie współczynników: percentyle, logarytmy, średnie geometryczne.
"""

import math


def _percentile_map(values: dict[str, int]) -> dict[str, float]:
    if not values:
        return {}

    ordered = sorted(values.items(), key=lambda item: item[1])
    total = len(ordered)

    if total == 1:
        return {ordered[0][0]: 1.0}

    return {key: round(index / (total - 1), 4) for index, (key, _) in enumerate(ordered)}


def _log_normalize(values: dict[str, int]) -> dict[str, float]:
    if not values:
        return {}

    max_value = max(values.values())
    if max_value == 0:
        return {key: 0.0 for key in values}

    denominator = math.log(1 + max_value)
    return {key: round(math.log(1 + value) / denominator, 4) for key, value in values.items()}


def _geometric_map(incoming: dict[str, int], outgoing: dict[str, int]) -> dict[str, float]:
    nodes = incoming.keys() | outgoing.keys()
    if not nodes:
        return {}

    values = {node: math.sqrt(incoming.get(node, 0) * outgoing.get(node, 0)) for node in nodes}

    maximum = max(values.values())
    if maximum == 0:
        return {node: 0.0 for node in nodes}

    return {node: round(val / maximum, 4) for node, val in values.items()}
