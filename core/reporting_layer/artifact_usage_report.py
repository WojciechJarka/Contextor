# -*- coding: utf-8 -*-

"""
core/reporting_layer/artifact_usage_report.py

GLOBAL ARTIFACT USAGE REPORT

Layer:
    REPORT ASSEMBLY (auxiliary, invoked by reporting.py)

Responsibilities:
- Gathers symbols (functions / classes / methods / globals) defined in each module
- Determines which modules actually use the same artifacts
- Groups consumer modules into shared usage clusters
- Prepares a list of candidates for core logic extraction in a format tailored for LLM

Does not do:
- AST parsing (delegates to symbol_analysis / symbol_reference)
- Risk / graph metric calculations (handled by reporting.py)
- Architecture validation

Sources of truth:
    symbol_analysis.py      -> local module symbols
    symbol_reference.py     -> who uses a given symbol
    api_consumers.py        -> consumer normalization


Output contract for generate_artifact_usage_report():

{
    "runtime": {...},
    "module_count": int,
    "artifact_count": int,
    "shared_artifact_count": int,
    "artifacts": {
        "<moduł_definiujący>::<symbol>": {
            "artifact": str,
            "kind": "class"|"function"|"method"|"global",
            "definer_module": str,
            "consumers": [str],
            "consumer_count": int,
            "usage": {...}
        }
    },
    "shared_artifacts": [...tylko consumer_count >= 2...],
    "shared_usage_clusters": [
        {
            "modules": [...],
            "size": int,
            "shared_artifact_count": int,
            "shared_artifacts": [...]
        }
    ],
    "core_extraction_candidates": [
        {
            "consumer_modules": [...],
            "likely_core_modules": [...],
            "shared_artifact_count": int,
            "top_shared_artifacts": [...],
            "reason": str
        }
    ]
}
"""

import os
import json
from datetime import datetime
from collections import defaultdict, deque
from itertools import combinations

from repo_guardian.core.symbol_analysis import extract_file_symbols
from repo_guardian.core.symbol_reference import build_symbol_references
from repo_guardian.core.api.api_consumers import extract_api_consumers
from repo_guardian.core.analysis.test_context import build_test_context


# ==========================================================
# CONFIG
# ==========================================================

# Minimum number of distinct consumer modules required
# to consider an artifact "shared" (core candidate)
MIN_SHARED_CONSUMERS = 2

# Minimum cluster size required to propose
# it as a candidate for common core extraction
MIN_CLUSTER_SIZE = 2


# ==========================================================
# SYMBOL COLLECTION PER MODULE
# ==========================================================


def _module_own_symbols(symbols: dict) -> list[str]:
    return (
        symbols.get("classes", [])
        + symbols.get("functions", [])
        + symbols.get("methods", [])
        + symbols.get("globals", [])
    )


def _symbol_kind(symbol: str, symbols: dict) -> str:
    if symbol in symbols.get("classes", []):
        return "class"

    if symbol in symbols.get("functions", []):
        return "function"

    if symbol in symbols.get("methods", []):
        return "method"

    if symbol in symbols.get("globals", []):
        return "global"

    return "unknown"


def collect_module_artifacts(
    modules: dict,
    root_path: str,
) -> dict:
    """
    Builds the following for each module:

    - local symbols (facts from symbol_analysis)
    - consumers of these symbols (api_consumers, based
      on symbol_reference)

    Returns:

    {
        module_id: {
            "symbols": {...extract_file_symbols...},
            "own_symbols": [...],
            "consumers": {...extract_api_consumers...},
        }
    }
    """
    result = {}
    tree_cache = {}

    for module_id, module in modules.items():
        abs_path = getattr(module, "absolute_path", getattr(module, "path", module_id))

        symbols = extract_file_symbols(str(abs_path))
        own_symbols = _module_own_symbols(symbols)

        if not own_symbols:
            result[module_id] = {
                "symbols": symbols,
                "own_symbols": own_symbols,
                "consumers": {},
            }
            continue

        references = build_symbol_references(
            modules,
            own_symbols,
            root_path,
            definer_module=module_id,
            tree_cache=tree_cache,
        )

        signatures = symbols.get("signatures", {})

        consumers = extract_api_consumers(
            own_symbols,
            references,
            signatures=signatures
        )

        result[module_id] = {
            "symbols": symbols,
            "own_symbols": own_symbols,
            "consumers": consumers,
        }

    return result


# ==========================================================
# GLOBAL ARTIFACT INDEX
# ==========================================================


def build_artifact_index(module_artifacts: dict) -> dict:
    """
    Flattens per-module data into a global artifact index.

    Artifact key:

        "<definer_module>::<qualified_symbol>"

    The module prefix is necessary because different modules can
    have symbols with identical local names
    (e.g., two "Config" classes in different files).
    """
    artifacts = {}

    for module_id, data in module_artifacts.items():
        symbols = data["symbols"]
        consumers = data["consumers"]

        for symbol in data["own_symbols"]:
            consumer_data = consumers.get(symbol, {})

            consumer_modules = sorted(
                {
                    c
                    for c in consumer_data.get("consumers", [])
                    if c != module_id
                }
            )

            key = f"{module_id}::{symbol}"

            # Significance Threshold filter
            # Ignore constants (global) and private variables and methods (_)
            # that are not used by anyone (noise in reports)
            is_private = symbol.startswith("_") or "." + "_" in symbol
            is_visitor_method = "Visitor.visit_" in symbol or symbol.startswith("visit_")
            kind = _symbol_kind(symbol, symbols)
            
            if len(consumer_modules) == 0 and (kind == "global" or is_private or is_visitor_method):
                continue
            
            # Additional heuristic: if it is a module_level function or method but has 'build_shared' we can ignore zero consumption
            if len(consumer_modules) == 0 and (symbol.startswith("build_") or symbol.startswith("filter_")):
                pass # Still include it to be aware, but mark it internal? It doesn't break if we keep it, but we can silence the warnings in risk scoring later.
                
            artifacts[key] = {
                "artifact": symbol,
                "kind": kind,
                "signature": consumer_data.get("signature", ""),
                "definer_module": module_id,
                "consumers": consumer_modules,
                "consumer_count": len(consumer_modules),
                "usage": consumer_data.get("usage", {}),
            }

    return dict(sorted(artifacts.items()))


def filter_shared_artifacts(
    artifacts: dict,
    min_consumers: int = MIN_SHARED_CONSUMERS,
) -> list[dict]:
    """
    Returns artifacts shared by multiple consumers,
    sorted descending by consumer count.
    """
    shared = [
        {"key": key, **data}
        for key, data in artifacts.items()
        if data["consumer_count"] >= min_consumers
    ]

    return sorted(
        shared,
        key=lambda item: (
            -item["consumer_count"],
            item["definer_module"],
            item["artifact"],
        ),
    )


# ==========================================================
# CONSUMER CLUSTERING
# ==========================================================


def _build_consumer_graph(shared_artifacts: list[dict]) -> dict:
    graph = defaultdict(set)

    for artifact in shared_artifacts:
        consumers = artifact["consumers"]

        for a, b in combinations(consumers, 2):
            graph[a].add(b)
            graph[b].add(a)

    return graph


def _connected_components(graph: dict) -> list[list[str]]:
    visited = set()
    clusters = []

    for node in graph:
        if node in visited:
            continue

        queue = deque([node])
        component = []

        while queue:
            current = queue.popleft()

            if current in visited:
                continue

            visited.add(current)
            component.append(current)

            for neigh in graph[current]:
                if neigh not in visited:
                    queue.append(neigh)

        clusters.append(sorted(component))

    return sorted(clusters, key=len, reverse=True)


def build_shared_usage_clusters(
    shared_artifacts: list[dict],
    min_cluster_size: int = MIN_CLUSTER_SIZE,
) -> list[dict]:
    """
    Groups consumer modules that use the same artifacts
    into clusters.

    Cluster = candidate for review for common core extraction.
    """
    graph = _build_consumer_graph(shared_artifacts)
    components = _connected_components(graph)
    clusters = []

    for component in components:
        if len(component) < min_cluster_size:
            continue

        component_set = set(component)

        cluster_artifacts = [
            {
                "artifact": a["artifact"],
                "definer_module": a["definer_module"],
                "kind": a["kind"],
                "consumers": [
                    c
                    for c in a["consumers"]
                    if c in component_set
                ],
            }
            for a in shared_artifacts
            if component_set.intersection(a["consumers"])
        ]

        clusters.append(
            {
                "modules": component,
                "size": len(component),
                "shared_artifact_count": len(cluster_artifacts),
                "shared_artifacts": cluster_artifacts,
            }
        )

    return sorted(
        clusters,
        key=lambda c: (
            -c["shared_artifact_count"],
            -c["size"],
        ),
    )


# ==========================================================
# CORE EXTRACTION CANDIDATES
# ==========================================================


def _dominant_definers(cluster: dict) -> list[str]:
    """
    Modules that most frequently define artifacts
    shared in a given cluster - the most likely
    candidates for "core" or the place to extract
    common logic to.
    """
    counts = defaultdict(int)

    for artifact in cluster["shared_artifacts"]:
        counts[artifact["definer_module"]] += 1

    return sorted(
        counts.keys(),
        key=lambda m: (-counts[m], m),
    )


def build_core_extraction_candidates(
    clusters: list[dict],
) -> list[dict]:
    """
    Format optimized for LLM refactoring decisions:
    "these modules share X artifacts - consider
    extracting a common core".
    """
    candidates = []

    for cluster in clusters:
        definers = _dominant_definers(cluster)

        top_artifacts = sorted(
            cluster["shared_artifacts"],
            key=lambda a: -len(a["consumers"]),
        )[:10]

        candidates.append(
            {
                "consumer_modules": cluster["modules"],
                "likely_core_modules": definers,
                "shared_artifact_count": cluster[
                    "shared_artifact_count"
                ],
                "top_shared_artifacts": [
                    {
                        "artifact": a["artifact"],
                        "defined_in": a["definer_module"],
                        "kind": a["kind"],
                        "used_by": a["consumers"],
                    }
                    for a in top_artifacts
                ],
                "reason": (
                    "modules share the usage of the same "
                    "artifacts (functions/classes/methods/fields) - "
                    "potential common core to extract"
                ),
            }
        )

    return candidates


# ==========================================================
# MAIN ENTRY POINT
# ==========================================================


def generate_artifact_usage_report(
    modules: dict,
    root_path: str,
    runtime: dict | None = None,
) -> dict:
    """
    Generates a global artifact usage report (functions,
    classes, methods, fields/globals) between repository files.

    Supplements generate_report() from reporting.py:

    - reporting.py describes project structure and module
      dependency graph
    - this report describes who actually uses whose code
      on a symbol level, and where candidates for core
      extraction are visible.
    """
    module_artifacts = collect_module_artifacts(
        modules,
        root_path,
    )

    artifact_index = build_artifact_index(
        module_artifacts
    )

    shared_artifacts = filter_shared_artifacts(
        artifact_index
    )

    clusters = build_shared_usage_clusters(
        shared_artifacts
    )

    core_candidates = build_core_extraction_candidates(
        clusters
    )

    runtime_info = (
        runtime.copy() if runtime else {}
    )

    runtime_info["generated_at"] = (
        datetime.now().isoformat()
    )

    # TEST TRACEABILITY MAPPING
    test_coverage_mapping = {}
    for module_id in modules:
        try:
            pub_sym = [s["artifact"] for s in artifact_index.values() if s["definer_module"] == module_id]
            test_ctx = build_test_context(module_id, root_path, pub_sym)
            test_coverage_mapping[module_id] = test_ctx
        except Exception:
            pass

    return {
        "runtime": runtime_info,
        "module_count": len(modules),
        "artifact_count": len(artifact_index),
        "shared_artifact_count": len(shared_artifacts),
        "artifacts": artifact_index,
        "shared_artifacts": shared_artifacts,
        "shared_usage_clusters": clusters,
        "core_extraction_candidates": core_candidates,
        "test_traceability": test_coverage_mapping,
    }


def save_artifact_usage_report(
    report: dict,
    path: str,
) -> None:
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )


# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [
    "collect_module_artifacts",
    "build_artifact_index",
    "filter_shared_artifacts",
    "build_shared_usage_clusters",
    "build_core_extraction_candidates",
    "generate_artifact_usage_report",
    "save_artifact_usage_report",
]
