"""
contextor/core/reporting_engine/graph_analytics.py

GRAPH ANALYTICS REPORT

Generates an additional JSON report alongside existing reports for all
report types (global project, layer, single file).

Responsibilities:

- provider_count / export_degree;
- artifact-level fan-in / fan-out;
- visibility classification;
- architectural layer classification;
- Jaccard-based consumer clustering;
- connection strength;
- graph centrality metrics;
- dependency type breakdown;
- module-to-module dependency matrix.

This module is a REPORT ASSEMBLY component.

It does not:

- parse AST;
- resolve references;
- classify references;
- mutate source reports;
- assign persistent identities.

Sources of truth:

    artifact_usage_report
        -> artifact definitions and confirmed consumers

    hard_edges
        -> module import graph

    IndexDictionary
        -> persistent compact identities

The artifact usage report currently stores cluster artifacts as:

    {
        "artifact_id": "...",
        "consumers": [...]
    }

Older upstream representations containing shared_artifact_keys are also
accepted for compatibility.

The implementation is deterministic and does not depend on networkx.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


# ==========================================================
# LAYER CLASSIFICATION
# ==========================================================

_LAYER_RULES: list[tuple[str, str]] = [
    ("tests.", "tests"),
    ("contextor.ui.", "ui"),
    ("contextor.cli", "cli"),
    ("contextor.core.domain.", "contract"),
    ("contextor.core.api.", "contract"),
    ("contextor.core.reporting_engine.", "engine"),
    ("contextor.core.reporting_layer.", "engine"),
    ("contextor.core.graph.", "runtime"),
    ("contextor.core.analysis.", "runtime"),
    ("contextor.core.symbol_engine.", "runtime"),
    ("contextor.core.hotspots.", "runtime"),
    ("contextor.core.facts.", "runtime"),
    ("contextor.core.reference.", "runtime"),
    ("contextor.core.single_file.", "runtime"),
    ("contextor.core.validator.", "runtime"),
    ("contextor.core.context.", "runtime"),
    ("contextor.core.git.", "adapter"),
    ("contextor.repo_generator.", "adapter"),
]


def _classify_layer(module_id: str) -> str:
    """Return the architectural layer for a module identifier."""
    if not module_id:
        return "adapter"

    for prefix, layer in _LAYER_RULES:
        if module_id.startswith(prefix):
            return layer

    return "adapter"


# ==========================================================
# VISIBILITY CLASSIFICATION
# ==========================================================


def _classify_visibility(
    module_id: str,
    consumer_modules: list[str],
    layer: str,
) -> str:
    """
    Classify module visibility from confirmed artifact consumers.

    public:
        consumed by at least one module outside its own layer.

    internal:
        consumed, but only by modules in the same layer.

    private:
        no confirmed consumers.

    The classification is intentionally structural. It does not claim
    that a Python module is literally part of a package's public API.
    """
    if not consumer_modules:
        return "private"

    for consumer in consumer_modules:
        if _classify_layer(consumer) != layer:
            return "public"

    return "internal"


# ==========================================================
# ARTIFACT / USAGE NORMALIZATION
# ==========================================================


def _artifact_usage_sidecar(artifact_data: dict) -> dict:
    """
    Return the optional raw usage sidecar.

    The current artifact report stores usage separately under
    ``_usage_sidecar``. Older reports may not contain it.
    """
    usage = artifact_data.get("_usage_sidecar", {})

    if not isinstance(usage, dict):
        return {}

    return usage


def _artifact_consumers(artifact: dict) -> list[str]:
    """Return deterministic confirmed consumers for one artifact."""
    consumers = artifact.get("consumers", [])

    if not isinstance(consumers, (list, tuple, set)):
        return []

    return sorted(
        {
            consumer
            for consumer in consumers
            if isinstance(consumer, str) and consumer
        }
    )


def _artifact_id(
    key: str,
    artifact: dict,
) -> str:
    """
    Resolve the canonical artifact identity.

    The current artifact report stores artifact_id explicitly, while the
    dictionary key remains ``<definer_module>::<symbol>``.
    """
    value = artifact.get("artifact_id")

    if isinstance(value, str) and value:
        return value

    return key


def _usage_dependency_types(usage: dict) -> set[str]:
    """
    Infer dependency types from usage categories.

    This is intentionally conservative. Categories are mapped to the
    three graph-level dependency types:

        call
        inheritance
        import

    Unknown categories do not create a dependency type.
    """
    result: set[str] = set()

    if not isinstance(usage, dict):
        return result

    for category, values in usage.items():
        if not values:
            continue

        category_lower = str(category).lower()

        if "inherit" in category_lower:
            result.add("inheritance")

        if (
            "call" in category_lower
            or "runtime" in category_lower
            or "callback" in category_lower
        ):
            result.add("call")

        if (
            "import" in category_lower
            or "api_import" in category_lower
        ):
            result.add("import")

    return result


def _fallback_dependency_type(artifact: dict) -> str:
    """
    Infer a dependency type from artifact kind.

    This is only a fallback when usage evidence is unavailable.
    """
    kind = artifact.get("kind", "unknown")

    if kind in ("function", "method"):
        return "call"

    return "import"


# ==========================================================
# MODULE DEPENDENCY MATRIX
# ==========================================================


def build_module_dependency_matrix(
    artifact_data: dict,
    hard_edges: dict,
) -> dict[str, dict[str, dict]]:
    """
    Build a weighted module-to-module dependency matrix.

    Matrix direction:

        consumer -> definer

    ``weight`` counts confirmed artifact relationships.

    ``dep_types`` contains one or more of:

        call
        inheritance
        import

    Import edges from ``hard_edges`` are included even when no artifact
    relationship exists.

    Import-only edges therefore have:

        weight = 0
        dep_types = ["import"]

    This is intentional: the edge exists structurally, but no consumed
    artifact was attributed to it.
    """
    artifacts = artifact_data.get("artifacts", {})

    if not isinstance(artifacts, dict):
        artifacts = {}

    usage_sidecar = _artifact_usage_sidecar(artifact_data)

    matrix: dict[
        str,
        dict[str, dict[str, Any]],
    ] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "weight": 0,
                "dep_types": set(),
            }
        )
    )

    for key, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            continue

        definer = artifact.get("definer_module")

        if not isinstance(definer, str) or not definer:
            continue

        consumers = _artifact_consumers(artifact)

        artifact_key = _artifact_id(key, artifact)

        usage = usage_sidecar.get(key)

        if usage is None:
            usage = usage_sidecar.get(artifact_key, {})

        dep_types = _usage_dependency_types(usage)

        if not dep_types:
            dep_types.add(
                _fallback_dependency_type(artifact)
            )

        for consumer in consumers:
            if consumer == definer:
                continue

            entry = matrix[consumer][definer]

            entry["weight"] += 1
            entry["dep_types"].update(dep_types)

    # Add import-level edges that are not represented by artifact usage.
    for source, targets in (hard_edges or {}).items():
        if not isinstance(source, str):
            continue

        if not isinstance(targets, (list, tuple, set)):
            continue

        for target in targets:
            if not isinstance(target, str) or not target:
                continue

            if source == target:
                continue

            entry = matrix[source][target]
            entry["dep_types"].add("import")

    result: dict[str, dict[str, dict]] = {}

    for consumer in sorted(matrix):
        deps = matrix[consumer]

        result[consumer] = {}

        for definer in sorted(deps):
            data = deps[definer]

            result[consumer][definer] = {
                "weight": int(data["weight"]),
                "dep_types": sorted(data["dep_types"]),
            }

    return result


# ==========================================================
# JACCARD-BASED CLUSTERING
# ==========================================================


def _jaccard(
    set_a: frozenset,
    set_b: frozenset,
) -> float:
    """Return Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0

    union = len(set_a | set_b)

    if union == 0:
        return 0.0

    return len(set_a & set_b) / union


def build_jaccard_clusters(
    artifact_data: dict,
    min_jaccard: float = 0.30,
    max_cluster_size: int = 25,
    min_cluster_size: int = 2,
) -> list[dict]:
    """
    Build deterministic complete-linkage clusters of consumer modules.

    Each module is represented by the set of artifact IDs it consumes.

    Two modules are eligible to coexist in a cluster only when their
    Jaccard similarity is at least ``min_jaccard``.

    Complete linkage is deliberate: it prevents chain propagation such
    as A~B and B~C causing A/B/C to become one cluster when A~C is below
    the threshold.
    """
    if min_jaccard < 0.0 or min_jaccard > 1.0:
        raise ValueError(
            "min_jaccard must be between 0.0 and 1.0"
        )

    if min_cluster_size < 2:
        raise ValueError(
            "min_cluster_size must be at least 2"
        )

    if max_cluster_size < min_cluster_size:
        raise ValueError(
            "max_cluster_size must be >= min_cluster_size"
        )

    artifacts = artifact_data.get("artifacts", {})

    if not isinstance(artifacts, dict):
        return []

    module_artifacts: dict[str, set[str]] = defaultdict(set)

    for key, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            continue

        artifact_id = _artifact_id(key, artifact)

        for consumer in _artifact_consumers(artifact):
            module_artifacts[consumer].add(
                artifact_id
            )

    frozen: dict[str, frozenset[str]] = {
        module: frozenset(values)
        for module, values in module_artifacts.items()
    }

    modules = sorted(frozen)

    if not modules:
        return []

    adjacency: dict[str, set[str]] = defaultdict(set)

    for index, module_a in enumerate(modules):
        for module_b in modules[index + 1:]:
            similarity = _jaccard(
                frozen[module_a],
                frozen[module_b],
            )

            if similarity >= min_jaccard:
                adjacency[module_a].add(module_b)
                adjacency[module_b].add(module_a)

    clusters: list[dict] = []

    unassigned = list(modules)

    while unassigned:
        seed = unassigned.pop(0)

        if seed not in adjacency:
            continue

        cluster = [seed]

        changed = True

        while changed:
            changed = False
            remaining: list[str] = []

            for candidate in unassigned:
                if all(
                    _jaccard(
                        frozen[candidate],
                        frozen[current],
                    ) >= min_jaccard
                    for current in cluster
                ):
                    cluster.append(candidate)
                    changed = True
                else:
                    remaining.append(candidate)

            unassigned = remaining

        cluster = sorted(cluster)

        if len(cluster) < min_cluster_size:
            continue

        if len(cluster) > max_cluster_size:
            cluster = sorted(
                cluster,
                key=lambda module: (
                    -len(adjacency.get(module, set())),
                    module,
                ),
            )[:max_cluster_size]

            cluster = sorted(cluster)

        component_set = frozenset(cluster)

        shared_artifact_ids = sorted(
            {
                _artifact_id(key, artifact)
                for key, artifact in artifacts.items()
                if isinstance(artifact, dict)
                and component_set.issubset(
                    set(_artifact_consumers(artifact))
                )
            }
        )
        pairs = [
            (left, right)
            for index, left in enumerate(cluster)
            for right in cluster[index + 1:]
        ]

        average_jaccard = (
            sum(
                _jaccard(
                    frozen[left],
                    frozen[right],
                )
                for left, right in pairs
            )
            / len(pairs)
            if pairs
            else 0.0
        )

        clusters.append(
            {
                "modules": cluster,
                "size": len(cluster),
                "shared_artifact_count": len(
                    shared_artifact_ids
                ),
                "shared_artifact_keys": (
                    shared_artifact_ids[:20]
                ),
                "jaccard_similarity": round(
                    average_jaccard,
                    4,
                ),
                "shared_ratio": round(
                    (
                        len(shared_artifact_ids)
                        / len(
                            set().union(
                                *(
                                    frozen[module]
                                    for module in cluster
                                )
                            )
                        )
                        if cluster
                        else 0.0
                    ),
                    4,
                ),
            }
        )

    return sorted(
        clusters,
        key=lambda cluster: (
            -cluster["shared_artifact_count"],
            -cluster["size"],
            cluster["modules"],
        ),
    )


# ==========================================================
# GRAPH NODE COLLECTION
# ==========================================================


def _all_nodes(
    hard_edges: dict,
) -> list[str]:
    """Return all nodes occurring in a directed graph."""
    nodes: set[str] = set()

    for source, targets in (hard_edges or {}).items():
        if isinstance(source, str):
            nodes.add(source)

        if isinstance(targets, (list, tuple, set)):
            nodes.update(
                target
                for target in targets
                if isinstance(target, str)
            )

    return sorted(nodes)


def _normalized_edges(
    hard_edges: dict,
) -> dict[str, tuple[str, ...]]:
    """
    Normalize the hard-edge graph.

    Duplicate edges are removed and target ordering is deterministic.
    """
    normalized: dict[str, tuple[str, ...]] = {}

    for source, targets in (hard_edges or {}).items():
        if not isinstance(source, str):
            continue

        if not isinstance(targets, (list, tuple, set)):
            normalized[source] = ()
            continue

        normalized[source] = tuple(
            sorted(
                {
                    target
                    for target in targets
                    if isinstance(target, str)
                    and target
                    and target != source
                }
            )
        )

    for target_list in normalized.values():
        # Targets are already included through the edge collection,
        # but this loop intentionally does nothing. It exists only to
        # keep normalization semantics explicit.
        _ = target_list

    return normalized


# ==========================================================
# PAGERANK
# ==========================================================


def _compute_pagerank(
    hard_edges: dict,
    damping: float = 0.85,
    iterations: int = 50,
) -> dict[str, float]:
    """
    Compute deterministic PageRank using pure Python.

    Dangling nodes redistribute their rank uniformly, matching the
    standard PageRank treatment.
    """
    if not 0.0 < damping < 1.0:
        raise ValueError(
            "damping must be between 0.0 and 1.0"
        )

    if iterations <= 0:
        raise ValueError(
            "iterations must be positive"
        )

    edges = _normalized_edges(hard_edges)
    nodes = _all_nodes(hard_edges)

    n = len(nodes)

    if n == 0:
        return {}

    rank = {
        node: 1.0 / n
        for node in nodes
    }

    for _ in range(iterations):
        new_rank = {
            node: (1.0 - damping) / n
            for node in nodes
        }

        dangling_mass = sum(
            rank[node]
            for node in nodes
            if not edges.get(node)
        )

        if dangling_mass:
            redistributed = (
                damping * dangling_mass / n
            )

            for node in nodes:
                new_rank[node] += redistributed

        for source, targets in edges.items():
            if not targets:
                continue

            share = (
                damping
                * rank.get(source, 0.0)
                / len(targets)
            )

            for target in targets:
                new_rank[target] += share

        rank = new_rank

    max_value = max(rank.values()) if rank else 0.0

    if max_value <= 0.0:
        return {
            node: 0.0
            for node in nodes
        }

    return {
        node: round(
            value / max_value,
            6,
        )
        for node, value in rank.items()
    }


# ==========================================================
# BETWEENNESS
# ==========================================================


def _compute_betweenness(
    hard_edges: dict,
    sample_limit: int = 80,
) -> dict[str, float]:
    """
    Approximate directed betweenness centrality via Brandes-style BFS.

    For repositories larger than ``sample_limit`` only the first
    deterministic subset of source nodes is used.
    """
    if sample_limit <= 0:
        raise ValueError(
            "sample_limit must be positive"
        )

    edges = _normalized_edges(hard_edges)
    nodes = _all_nodes(hard_edges)

    if not nodes:
        return {}

    betweenness: dict[str, float] = {
        node: 0.0
        for node in nodes
    }

    sources = nodes[:sample_limit]

    for source in sources:
        distance: dict[str, int] = {
            source: 0
        }

        predecessors: dict[
            str,
            list[str],
        ] = defaultdict(list)

        sigma: dict[str, float] = {
            source: 1.0
        }

        queue: deque[str] = deque([source])
        order: list[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)

            for target in edges.get(
                current,
                (),
            ):
                if target not in distance:
                    distance[target] = (
                        distance[current] + 1
                    )
                    queue.append(target)

                if distance.get(target) == (
                    distance[current] + 1
                ):
                    sigma[target] = (
                        sigma.get(target, 0.0)
                        + sigma.get(current, 0.0)
                    )
                    predecessors[target].append(
                        current
                    )

        dependency: dict[str, float] = {
            node: 0.0
            for node in nodes
        }

        for current in reversed(order):
            sigma_current = sigma.get(
                current,
                1.0,
            )

            if sigma_current == 0.0:
                continue

            for predecessor in predecessors.get(
                current,
                [],
            ):
                dependency[predecessor] += (
                    sigma.get(
                        predecessor,
                        0.0,
                    )
                    / sigma_current
                ) * (
                    1.0
                    + dependency[current]
                )

            if current != source:
                betweenness[current] += (
                    dependency[current]
                )

    max_value = (
        max(betweenness.values())
        if betweenness
        else 0.0
    )

    if max_value <= 0.0:
        return {
            node: 0.0
            for node in betweenness
        }

    return {
        node: round(
            value / max_value,
            6,
        )
        for node, value in betweenness.items()
    }


# ==========================================================
# HITS
# ==========================================================


def _compute_hub_authority(
    hard_edges: dict,
    iterations: int = 20,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Compute HITS hub and authority scores.

    Scores are normalized independently by their maximum value.
    """
    if iterations <= 0:
        raise ValueError(
            "iterations must be positive"
        )

    edges = _normalized_edges(hard_edges)
    nodes = _all_nodes(hard_edges)

    if not nodes:
        return {}, {}

    hub = {
        node: 1.0
        for node in nodes
    }

    authority = {
        node: 1.0
        for node in nodes
    }

    for _ in range(iterations):
        new_authority = {
            node: 0.0
            for node in nodes
        }

        for source, targets in edges.items():
            source_score = hub.get(
                source,
                0.0,
            )

            for target in targets:
                new_authority[target] += (
                    source_score
                )

        new_hub = {
            node: 0.0
            for node in nodes
        }

        for source, targets in edges.items():
            new_hub[source] = sum(
                new_authority.get(
                    target,
                    0.0,
                )
                for target in targets
            )

        max_authority = (
            max(new_authority.values())
            if new_authority
            else 0.0
        )

        max_hub = (
            max(new_hub.values())
            if new_hub
            else 0.0
        )

        if max_authority > 0.0:
            authority = {
                node: value / max_authority
                for node, value
                in new_authority.items()
            }
        else:
            authority = {
                node: 0.0
                for node in nodes
            }

        if max_hub > 0.0:
            hub = {
                node: value / max_hub
                for node, value
                in new_hub.items()
            }
        else:
            hub = {
                node: 0.0
                for node in nodes
            }

    return (
        {
            node: round(
                value,
                6,
            )
            for node, value in hub.items()
        },
        {
            node: round(
                value,
                6,
            )
            for node, value
            in authority.items()
        },
    )


# ==========================================================
# BRIDGE SCORE
# ==========================================================


def _compute_bridge_score(
    hard_edges: dict,
    betweenness: dict[str, float],
) -> dict[str, float]:
    """
    Compute a directed approximation of bridge score.

    Formula:

        bridge_score =
            betweenness * (1 - local_clustering_coefficient)

    The local coefficient is computed over outgoing neighbors.

    This is a heuristic ranking metric, not a formal graph-theory
    bridge classification.
    """
    edges = _normalized_edges(hard_edges)

    scores: dict[str, float] = {}

    for node, betweenness_value in betweenness.items():
        neighbors = set(
            edges.get(
                node,
                (),
            )
        )

        if len(neighbors) < 2:
            clustering = 0.0
        else:
            possible = (
                len(neighbors)
                * (len(neighbors) - 1)
            )

            actual = 0

            for left in neighbors:
                for right in edges.get(
                    left,
                    (),
                ):
                    if (
                        right in neighbors
                        and right != left
                    ):
                        actual += 1

            clustering = (
                actual / possible
                if possible > 0
                else 0.0
            )

        scores[node] = round(
            betweenness_value
            * (1.0 - clustering),
            6,
        )

    return scores


# ==========================================================
# EXPORT DEGREE
# ==========================================================


def _compute_export_degrees(
    artifact_data: dict,
) -> dict[str, int]:
    """
    Count artifacts defined by every module.

    This is artifact-level export degree, not Python ``__all__``.
    """
    degrees: dict[str, int] = defaultdict(int)

    artifacts = artifact_data.get(
        "artifacts",
        {},
    )

    if not isinstance(artifacts, dict):
        return {}

    for artifact in artifacts.values():
        if not isinstance(artifact, dict):
            continue

        definer = artifact.get(
            "definer_module"
        )

        if isinstance(definer, str) and definer:
            degrees[definer] += 1

    return dict(degrees)


# ==========================================================
# DEPENDENCY TYPE BREAKDOWN
# ==========================================================


def _compute_dep_type_breakdown(
    matrix: dict,
) -> dict[str, int]:
    """
    Count module-pair relationships by dependency type.

    A dependency pair containing both call and import contributes once
    to each type. This is a relationship-type count, not an artifact
    count.
    """
    breakdown: dict[str, int] = defaultdict(int)

    for deps in matrix.values():
        for dependency in deps.values():
            for dependency_type in dependency.get(
                "dep_types",
                [],
            ):
                breakdown[dependency_type] += 1

    return dict(
        sorted(
            breakdown.items()
        )
    )


# ==========================================================
# SCOPE FILTERING
# ==========================================================


def _filter_scope(
    artifact_data: dict,
    hard_edges: dict,
    scope_modules: set[str] | None,
) -> tuple[dict, dict]:
    """
    Return scope-filtered artifact data and hard edges.

    Only relationships whose consumer and definer both belong to the
    scope are retained.

    This prevents a layer/single-file report from accidentally exposing
    cross-scope consumers through the global artifact index.
    """
    if not scope_modules:
        return (
            artifact_data,
            hard_edges,
        )

    scope = {
        module
        for module in scope_modules
        if isinstance(module, str)
    }

    filtered_edges: dict[str, list[str]] = {}

    for source, targets in (
        hard_edges or {}
    ).items():
        if source not in scope:
            continue

        filtered_edges[source] = [
            target
            for target in targets
            if target in scope
        ]

    source_artifacts = artifact_data.get(
        "artifacts",
        {},
    )

    filtered_artifacts: dict[str, dict] = {}

    if isinstance(source_artifacts, dict):
        for key, artifact in source_artifacts.items():
            if not isinstance(artifact, dict):
                continue

            definer = artifact.get(
                "definer_module"
            )

            if definer not in scope:
                continue

            # P0-4: Retain artifacts even when no consumers fall inside the
            # scope. Dropping them would undercount export_degree, which
            # is defined as "how many artifacts does a module define" —
            # independent of whether those artifacts are consumed locally.
            consumers = [
                consumer
                for consumer in _artifact_consumers(
                    artifact
                )
                if consumer in scope
            ]

            copied = dict(artifact)
            copied["consumers"] = consumers
            copied["consumer_count"] = len(
                consumers
            )

            filtered_artifacts[key] = copied

    scoped: dict[str, Any] = dict(
        artifact_data
    )

    scoped["artifacts"] = filtered_artifacts

    usage_sidecar = artifact_data.get(
        "_usage_sidecar"
    )

    if isinstance(usage_sidecar, dict):
        scoped["_usage_sidecar"] = {
            key: value
            for key, value in usage_sidecar.items()
            if key in filtered_artifacts
        }

    return (
        scoped,
        filtered_edges,
    )


# ==========================================================
# INDEX COMPACTION
# ==========================================================


def _compact_module_id(
    index_dict: Any,
    module_id: str,
) -> str:
    """
    Convert a module identifier through IndexDictionary.

    PersistentIdentityRegistry currently exposes string IDs, so the
    return type is deliberately string-based.
    """
    if index_dict is None:
        return module_id

    return str(
        index_dict.get_module_id(
            module_id
        )
    )


def _compact_artifact_id(
    index_dict: Any,
    artifact_id: str,
) -> str:
    """Convert an artifact identifier through IndexDictionary."""
    if index_dict is None:
        return artifact_id

    return str(
        index_dict.get_artifact_id(
            artifact_id
        )
    )


def _compact_matrix(
    matrix: dict,
    index_dict: Any,
) -> dict:
    """Compact module IDs in the dependency matrix."""
    if index_dict is None:
        return matrix

    compact: dict[str, dict] = {}

    for consumer, dependencies in matrix.items():
        compact_consumer = _compact_module_id(
            index_dict,
            consumer,
        )

        compact[compact_consumer] = {}

        for definer, data in dependencies.items():
            compact_definer = _compact_module_id(
                index_dict,
                definer,
            )

            compact[compact_consumer][
                compact_definer
            ] = data

    return compact


def _compact_clusters(
    clusters: list[dict],
    index_dict: Any,
) -> list[dict]:
    """Compact module and artifact IDs inside cluster records."""
    if index_dict is None:
        return clusters

    result: list[dict] = []

    for cluster in clusters:
        compact_cluster = dict(
            cluster
        )

        compact_cluster["modules"] = [
            _compact_module_id(
                index_dict,
                module_id,
            )
            for module_id
            in cluster.get(
                "modules",
                [],
            )
        ]

        compact_cluster[
            "shared_artifact_keys"
        ] = [
            _compact_artifact_id(
                index_dict,
                artifact_id,
            )
            for artifact_id
            in cluster.get(
                "shared_artifact_keys",
                [],
            )
        ]

        result.append(
            compact_cluster
        )

    return result


# ==========================================================
# MAIN ENTRY POINT
# ==========================================================


def generate_graph_analytics_report(
    artifact_data: dict,
    hard_edges: dict,
    soft_edges: dict | None = None,
    modules: dict | None = None,
    index_dict=None,
    scope: str = "global",
    scope_modules: set[str] | None = None,
    global_artifact_data: dict | None = None,
) -> dict:
    """
    Generate the graph analytics report.

    Args:
        artifact_data:
            Result of generate_artifact_usage_report(). For a layer or
            single-file scope this should be the **full** global artifact
            report so that ``_filter_scope`` can apply the correct scope
            boundaries.

        hard_edges:
            Dict[module_id, list[module_id]] representing the hard
            import graph.

        soft_edges:
            Optional soft dependency graph. Currently retained as
            context for API compatibility and intentionally not merged
            into hard graph metrics.

        modules:
            Optional full module index. Retained for API compatibility.

        index_dict:
            Optional IndexDictionary backed by PersistentIdentityRegistry.

        scope:
            One of ``global``, ``layer`` or ``single_file``.

        scope_modules:
            Optional set of module IDs limiting the analysis.

        global_artifact_data:
            When provided, visibility classification uses this data
            instead of the (possibly scope-filtered) ``artifact_data``.

            This implements the dual-perspective contract:

                scoped  → fan_in / fan_out / export_degree / matrix
                global  → visibility

            Pass the full project artifact report here whenever
            ``scope`` is ``"layer"`` or ``"single_file"``.

    Returns:
        Deterministic graph analytics report.
    """
    if not isinstance(
        artifact_data,
        dict,
    ):
        raise TypeError(
            "artifact_data must be a dict"
        )

    if not isinstance(
        hard_edges,
        dict,
    ):
        raise TypeError(
            "hard_edges must be a dict"
        )

    scoped_artifact_data, scoped_edges = (
        _filter_scope(
            artifact_data,
            hard_edges,
            scope_modules,
        )
    )

    dependency_matrix = build_module_dependency_matrix(
        scoped_artifact_data,
        scoped_edges,
    )

    # P0-3: Resolve the artifact source used for visibility.
    # Visibility must reflect whether a module is consumed *anywhere* in
    # the project, not only within the current scope.  When the caller
    # supplies global_artifact_data we use it exclusively for the
    # fan_in_global map that feeds _classify_visibility.  All other
    # metrics (fan_in, fan_out, export_degree, matrix) use the
    # scope-filtered data so that per-layer numbers stay local.
    _visibility_source = (
        global_artifact_data
        if isinstance(global_artifact_data, dict)
        else artifact_data
    )

    # ------------------------------------------------------
    # Artifact-level fan-in / fan-out  (scoped — local metrics)
    # ------------------------------------------------------

    fan_in: dict[str, set[str]] = defaultdict(set)
    fan_out: dict[str, set[str]] = defaultdict(set)

    artifacts = scoped_artifact_data.get(
        "artifacts",
        {},
    )

    if isinstance(artifacts, dict):
        for artifact in artifacts.values():
            if not isinstance(artifact, dict):
                continue

            definer = artifact.get(
                "definer_module"
            )

            if not isinstance(definer, str):
                continue

            for consumer in _artifact_consumers(
                artifact
            ):
                if consumer == definer:
                    continue

                fan_in[definer].add(
                    consumer
                )

                fan_out[consumer].add(
                    definer
                )

    # ------------------------------------------------------
    # Global fan-in for visibility classification
    # ------------------------------------------------------
    # Built from _visibility_source (global data when available).  This
    # gives _classify_visibility the full picture of who consumes each
    # module across the entire project, not just within the scope.

    fan_in_global: dict[str, set[str]] = defaultdict(set)

    _global_artifacts = _visibility_source.get(
        "artifacts",
        {},
    )

    if isinstance(_global_artifacts, dict):
        for _artifact in _global_artifacts.values():
            if not isinstance(_artifact, dict):
                continue

            _definer = _artifact.get(
                "definer_module"
            )

            if not isinstance(_definer, str):
                continue

            for _consumer in _artifact_consumers(
                _artifact
            ):
                if _consumer == _definer:
                    continue

                fan_in_global[_definer].add(
                    _consumer
                )

    export_degrees = (
        _compute_export_degrees(
            scoped_artifact_data
        )
    )

    # ------------------------------------------------------
    # Graph metrics
    # ------------------------------------------------------

    pagerank = _compute_pagerank(
        scoped_edges
    )

    betweenness = _compute_betweenness(
        scoped_edges
    )

    hub_scores, authority_scores = (
        _compute_hub_authority(
            scoped_edges
        )
    )

    bridge_scores = (
        _compute_bridge_score(
            scoped_edges,
            betweenness,
        )
    )

    # ------------------------------------------------------
    # Module universe
    # ------------------------------------------------------

    all_module_ids: set[str] = set()

    all_module_ids.update(
        source
        for source in scoped_edges
        if isinstance(source, str)
    )

    for targets in scoped_edges.values():
        if isinstance(
            targets,
            (list, tuple, set),
        ):
            all_module_ids.update(
                target
                for target in targets
                if isinstance(
                    target,
                    str,
                )
            )

    all_module_ids.update(
        fan_in.keys()
    )

    all_module_ids.update(
        fan_out.keys()
    )

    if scope_modules:
        all_module_ids.update(scope_modules)

    matrix_fan_out = {
        module_id: set(dependencies)
        for module_id, dependencies in dependency_matrix.items()
    }
    matrix_fan_in: dict[str, set[str]] = defaultdict(set)
    for consumer, dependencies in dependency_matrix.items():
        for definer in dependencies:
            matrix_fan_in[definer].add(consumer)

    all_module_ids.update(matrix_fan_out)
    all_module_ids.update(matrix_fan_in)

    # ------------------------------------------------------
    # Per-module metrics
    # ------------------------------------------------------

    modules_report: dict[
        str,
        dict[str, Any],
    ] = {}

    for module_id in sorted(
        all_module_ids
    ):
        layer = _classify_layer(
            module_id
        )

        # P0-3: Visibility uses global consumers so that a module
        # consumed outside this layer is still marked "public" even
        # when the layer-scoped fan_in contains no cross-layer entries.
        global_consumers = sorted(
            fan_in_global.get(
                module_id,
                set(),
            )
        )

        visibility = (
            _classify_visibility(
                module_id,
                global_consumers,
                layer,
            )
        )

        entry: dict[str, Any] = {
            "fan_in": len(
                matrix_fan_in.get(
                    module_id,
                    set(),
                )
            ),
            "fan_out": len(
                matrix_fan_out.get(
                    module_id,
                    set(),
                )
            ),
            "export_degree": (
                export_degrees.get(
                    module_id,
                    0,
                )
            ),
            "visibility": visibility,
            "layer": layer,
            "betweenness": (
                betweenness.get(
                    module_id,
                    0.0,
                )
            ),
            "pagerank": (
                pagerank.get(
                    module_id,
                    0.0,
                )
            ),
            "hub_score": (
                hub_scores.get(
                    module_id,
                    0.0,
                )
            ),
            "authority_score": (
                authority_scores.get(
                    module_id,
                    0.0,
                )
            ),
            "bridge_score": (
                bridge_scores.get(
                    module_id,
                    0.0,
                )
            ),
        }

        if index_dict is not None:
            entry["module_idx"] = (
                _compact_module_id(
                    index_dict,
                    module_id,
                )
            )

        modules_report[
            module_id
        ] = entry

    # ------------------------------------------------------
    # Module dependency matrix
    # ------------------------------------------------------

    compact_matrix = _compact_matrix(
        dependency_matrix,
        index_dict,
    )

    # ------------------------------------------------------
    # Jaccard clusters
    # ------------------------------------------------------

    clusters = build_jaccard_clusters(
        scoped_artifact_data
    )

    clusters = _compact_clusters(
        clusters,
        index_dict,
    )

    # ------------------------------------------------------
    # Dependency breakdown
    # ------------------------------------------------------

    dependency_breakdown = (
        _compute_dep_type_breakdown(
            dependency_matrix
        )
    )

    # ------------------------------------------------------
    # Report
    # ------------------------------------------------------

    # P1-7/8/9: Document metric semantics without renaming per-module keys
    # (renaming would break existing consumers and tests).
    metric_notes = {
        "pagerank": (
            "Max-normalized PageRank (d=0.85, 50 iter). "
            "Values do NOT sum to 1.0. "
            "Scores are divided by the maximum observed value so the "
            "top-ranked node always equals 1.0."
        ),
        "betweenness": (
            "Sampled betweenness centrality approximation. "
            f"Only the first {80} source nodes (sorted deterministically) "
            "are used for large graphs (sample_limit=80). "
            "Max-normalized to [0, 1]."
        ),
        "bridge_score": (
            "Bridge heuristic score — NOT a formal bridge/articulation-point "
            "metric from graph theory. "
            "Formula: sampled_betweenness × (1 − outgoing_local_clustering). "
            "Higher values suggest structural broker role."
        ),
    }

    report = {
        "schema_version": "1.0",
        "report_type": "graph_analytics",
        "scope": scope,
        "module_count": len(
            modules_report
        ),
        "metric_notes": metric_notes,
        "modules": modules_report,
        "module_dependency_matrix": (
            compact_matrix
        ),
        "shared_usage_clusters": clusters,
        "dependency_type_breakdown": (
            dependency_breakdown
        ),
    }

    return report


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [
    "generate_graph_analytics_report",
    "build_module_dependency_matrix",
    "build_jaccard_clusters",
    "_classify_layer",
    "_classify_visibility",
]
