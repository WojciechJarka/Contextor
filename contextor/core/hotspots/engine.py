"""
contextor/core/hotspots/engine.py

Główny silnik uruchamiający analizer hotspotów.
"""

from contextor.core.graph.thresholds import get_thresholds

from .classification import _build_hotspot_explanation, classify_module, compute_hotspot_score
from .degrees import compute_in_degree, compute_out_degree
from .normalization import _geometric_map, _log_normalize, _percentile_map


def detect_hotspots(hard_edges: dict[str, set[str]]) -> list[dict]:
    modules = set(hard_edges.keys())

    in_degree = compute_in_degree(hard_edges)
    out_degree = compute_out_degree(hard_edges)

    modules.update(in_degree.keys())
    modules.update(out_degree.keys())

    impact_map = _percentile_map(in_degree)
    complexity_map = _percentile_map(out_degree)

    log_map = _log_normalize(
        {module: in_degree.get(module, 0) + out_degree.get(module, 0) for module in modules}
    )

    geometric_map = _geometric_map(in_degree, out_degree)
    thresholds = get_thresholds(len(modules))

    results = []

    for module in modules:
        incoming = in_degree.get(module, 0)
        outgoing = out_degree.get(module, 0)
        impact = impact_map.get(module, 0.0)
        complexity = complexity_map.get(module, 0.0)

        score = compute_hotspot_score(
            impact, complexity, log_map.get(module, 0.0), geometric_map.get(module, 0.0)
        )

        kind = classify_module(impact, complexity, score, thresholds, incoming, outgoing)

        if kind == "HUB" and (module.endswith("settings") or module.endswith("config")):
            kind = "CONFIG_HUB"

        if kind != "NORMAL":
            if kind == "ISOLATED":
                score = 0.0
                impact = 0.0
                complexity = 0.0

            results.append(
                {
                    "module": module,
                    "type": kind,
                    "score": score,
                    "explanation": _build_hotspot_explanation(
                        kind,
                        impact,
                        complexity,
                        log_map.get(module, 0.0),
                        geometric_map.get(module, 0.0),
                    ),
                    "impact_percentile": impact,
                    "complexity_percentile": complexity,
                    "in_degree": incoming,
                    "out_degree": outgoing,
                }
            )

    return sorted(results, key=lambda item: (-item["score"], item["module"]))
