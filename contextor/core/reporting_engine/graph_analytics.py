"""
contextor/core/reporting_engine/graph_analytics.py

GRAPH ANALYTICS REPORT

Generates an additional JSON report alongside existing reports for all three
report types (full project, layer, single file).

Provides what the existing reports lack:
  - provider_count / export_degree (fan-out on artifact level)
  - visibility classification (public / internal / private)
  - architectural layer classification
  - improved clustering (Jaccard-based, smaller tighter clusters)
  - connection strength (shared_ratio, jaccard_similarity)
  - graph centrality metrics (betweenness, pagerank, hub_score, bridge_score)
  - dependency type breakdown (call / inheritance / import)
  - Module Dependency Matrix: module -> module with weights
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
    public   -- has consumers outside its own layer
    internal -- has consumers only within its own layer
    private  -- no consumers (isolated)
    """
    if not consumer_modules:
        return "private"
    for consumer in consumer_modules:
        consumer_layer = _classify_layer(consumer)
        if consumer_layer != layer:
            return "public"
    return "internal"


# ==========================================================
# MODULE DEPENDENCY MATRIX
# ==========================================================

def build_module_dependency_matrix(
    artifact_data: dict,
    hard_edges: dict,
) -> dict[str, dict[str, dict]]:
    """
    Builds a weighted module-to-module dependency matrix from the artifact index.

    For each pair (consumer -> definer):
      weight    -- number of artifacts defined in definer that are consumed by consumer
      dep_types -- inferred dependency types (call / inheritance / import)
    """
    artifacts = artifact_data.get("artifacts", {})

    matrix: dict[str, dict[str, dict]] = defaultdict(
        lambda: defaultdict(lambda: {"weight": 0, "dep_types": set()})
    )

    for _key, artifact in artifacts.items():
        definer = artifact.get("definer_module")
        consumers = artifact.get("consumers", [])
        kind = artifact.get("kind", "unknown")

        if kind == "class":
            dep_type = "inheritance"
        elif kind in ("function", "method"):
            dep_type = "call"
        else:
            dep_type = "import"

        for consumer in consumers:
            if consumer == definer:
                continue
            matrix[consumer][definer]["weight"] += 1
            matrix[consumer][definer]["dep_types"].add(dep_type)

    # Enrich with hard_edges for import-level edges not covered by artifacts
    for src, targets in (hard_edges or {}).items():
        for tgt in targets:
            matrix[src][tgt]["dep_types"].add("import")

    # Serialize (convert sets to sorted lists)
    result: dict[str, dict[str, dict]] = {}
    for consumer, deps in matrix.items():
        result[consumer] = {
            definer: {
                "weight": data["weight"],
                "dep_types": sorted(data["dep_types"]),
            }
            for definer, data in deps.items()
        }
    return result


# ==========================================================
# JACCARD-BASED CLUSTERING
# ==========================================================

def _jaccard(set_a: frozenset, set_b: frozenset) -> float:
    if not set_a and not set_b:
        return 0.0
    union = len(set_a | set_b)
    return len(set_a & set_b) / union if union > 0 else 0.0


def build_jaccard_clusters(
    artifact_data: dict,
    min_jaccard: float = 0.30,
    max_cluster_size: int = 25,
    min_cluster_size: int = 2,
) -> list[dict]:
    """
    Jaccard-similarity based clustering of consumer modules.

    Instead of connected-components (which creates clusters of size 100+),
    groups modules that share at least `min_jaccard` of their artifact sets.

    min_jaccard=0.30 means two modules must share ≥30% of the artifacts
    they consume — this produces semantically tight clusters (size 6-15)
    instead of one giant cluster containing the entire repository.
    """
    artifacts = artifact_data.get("artifacts", {})

    # module -> frozenset of artifact keys they consume
    module_artifacts: dict[str, set] = defaultdict(set)
    for key, artifact in artifacts.items():
        for consumer in artifact.get("consumers", []):
            module_artifacts[consumer].add(key)

    frozen: dict[str, frozenset] = {m: frozenset(s) for m, s in module_artifacts.items()}
    modules = sorted(frozen.keys())

    if not modules:
        return []

    # Build Jaccard-threshold adjacency graph
    adjacency: dict[str, set] = defaultdict(set)
    for i, mod_a in enumerate(modules):
        for mod_b in modules[i + 1:]:
            if _jaccard(frozen[mod_a], frozen[mod_b]) >= min_jaccard:
                adjacency[mod_a].add(mod_b)
                adjacency[mod_b].add(mod_a)

    # Complete-linkage clustering: a module joins a cluster ONLY if its
    # Jaccard with EVERY current cluster member >= min_jaccard.
    # This eliminates BFS chain propagation (A-B-C merging even when A-C < threshold).
    clusters: list[dict] = []
    unassigned = list(modules)  # sorted for determinism

    while unassigned:
        seed = unassigned.pop(0)
        if seed not in adjacency:
            continue  # no edges at threshold -> skip singletons
        cluster = [seed]

        changed = True
        while changed:
            changed = False
            remaining = []
            for candidate in unassigned:
                # Complete linkage: must meet threshold with EVERY member
                if all(
                    _jaccard(frozen.get(candidate, frozenset()), frozen.get(m, frozenset())) >= min_jaccard
                    for m in cluster
                ):
                    cluster.append(candidate)
                    changed = True
                else:
                    remaining.append(candidate)
            unassigned = remaining

        if len(cluster) < min_cluster_size:
            continue
        if len(cluster) > max_cluster_size:
            cluster = sorted(
                cluster,
                key=lambda m: len(adjacency.get(m, set())),
                reverse=True,
            )[:max_cluster_size]

        component_set = frozenset(cluster)
        shared_keys = [
            key for key, art in artifacts.items()
            if component_set.intersection(art.get("consumers", []))
        ]
        pairs = [(a, b) for i, a in enumerate(cluster) for b in cluster[i + 1:]]
        avg_j = (
            sum(_jaccard(frozen.get(a, frozenset()), frozen.get(b, frozenset())) for a, b in pairs)
            / len(pairs)
            if pairs else 0.0
        )
        clusters.append({
            "modules": sorted(cluster),
            "size": len(cluster),
            "shared_artifact_count": len(shared_keys),
            "shared_artifact_keys": shared_keys[:20],
            "jaccard_similarity": round(avg_j, 4),
            "shared_ratio": round(avg_j, 4),
        })

    return sorted(clusters, key=lambda c: (-c["shared_artifact_count"], -c["size"]))


# ==========================================================
# CENTRALITY METRICS (pure-Python, no networkx)
# ==========================================================

def _all_nodes(hard_edges: dict) -> list[str]:
    nodes: set[str] = set(hard_edges.keys())
    for tgts in hard_edges.values():
        nodes.update(tgts)
    return sorted(nodes)


def _compute_pagerank(
    hard_edges: dict,
    damping: float = 0.85,
    iterations: int = 50,
) -> dict[str, float]:
    nodes = _all_nodes(hard_edges)
    n = len(nodes)
    if n == 0:
        return {}
    rank = {node: 1.0 / n for node in nodes}
    for _ in range(iterations):
        new_rank: dict[str, float] = {node: (1 - damping) / n for node in nodes}
        for src, targets in hard_edges.items():
            if not targets:
                continue
            share = rank.get(src, 0.0) / len(targets)
            for tgt in targets:
                new_rank[tgt] = new_rank.get(tgt, 0.0) + damping * share
        rank = new_rank
    max_val = max(rank.values()) if rank else 1.0
    return {node: round(v / max_val, 6) for node, v in rank.items()} if max_val > 0 else rank


def _compute_betweenness(hard_edges: dict, sample_limit: int = 80) -> dict[str, float]:
    """Approximate betweenness centrality via BFS from sampled source nodes."""
    nodes = _all_nodes(hard_edges)
    if not nodes:
        return {}

    betweenness: dict[str, float] = {n: 0.0 for n in nodes}
    sources = nodes[:sample_limit]

    for source in sources:
        dist: dict[str, int] = {source: 0}
        pred: dict[str, list] = {source: []}
        sigma: dict[str, float] = {source: 1.0}
        queue: deque = deque([source])
        order: list[str] = []

        while queue:
            v = queue.popleft()
            order.append(v)
            for w in hard_edges.get(v, []):
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist.get(w) == dist[v] + 1:
                    sigma[w] = sigma.get(w, 0.0) + sigma.get(v, 0.0)
                    pred.setdefault(w, []).append(v)

        delta: dict[str, float] = {n: 0.0 for n in nodes}
        for w in reversed(order):
            for v in pred.get(w, []):
                delta[v] += (sigma.get(v, 0.0) / sigma.get(w, 1.0)) * (1.0 + delta[w])
            if w != source:
                betweenness[w] = betweenness.get(w, 0.0) + delta[w]

    max_b = max(betweenness.values()) if betweenness else 1.0
    return {
        node: round(v / max_b, 6) if max_b > 0 else 0.0
        for node, v in betweenness.items()
    }


def _compute_hub_authority(hard_edges: dict, iterations: int = 20) -> tuple[dict, dict]:
    """HITS algorithm -- hub and authority scores."""
    nodes = _all_nodes(hard_edges)
    if not nodes:
        return {}, {}

    hub = {n: 1.0 for n in nodes}
    auth = {n: 1.0 for n in nodes}

    for _ in range(iterations):
        new_auth: dict[str, float] = {n: 0.0 for n in nodes}
        new_hub: dict[str, float] = {n: 0.0 for n in nodes}
        for src, targets in hard_edges.items():
            for tgt in targets:
                new_auth[tgt] = new_auth.get(tgt, 0.0) + hub.get(src, 0.0)
        for src, targets in hard_edges.items():
            for tgt in targets:
                new_hub[src] = new_hub.get(src, 0.0) + new_auth.get(tgt, 0.0)
        max_a = max(new_auth.values()) or 1.0
        max_h = max(new_hub.values()) or 1.0
        auth = {n: v / max_a for n, v in new_auth.items()}
        hub = {n: v / max_h for n, v in new_hub.items()}

    return (
        {n: round(v, 6) for n, v in hub.items()},
        {n: round(v, 6) for n, v in auth.items()},
    )


def _compute_bridge_score(hard_edges: dict, betweenness: dict) -> dict[str, float]:
    """bridge_score = betweenness * (1 - local_clustering_coefficient)."""
    scores: dict[str, float] = {}
    for node, b in betweenness.items():
        neighbors = set(hard_edges.get(node, []))
        if len(neighbors) < 2:
            lcc = 0.0
        else:
            possible = len(neighbors) * (len(neighbors) - 1)
            actual = sum(
                1 for n in neighbors
                for m in hard_edges.get(n, [])
                if m in neighbors
            )
            lcc = actual / possible if possible > 0 else 0.0
        scores[node] = round(b * (1.0 - lcc), 6)
    return scores


# ==========================================================
# EXPORT DEGREE PER MODULE
# ==========================================================

def _compute_export_degrees(artifact_data: dict) -> dict[str, int]:
    """Count how many artifacts each module defines (export_degree)."""
    degrees: dict[str, int] = defaultdict(int)
    for artifact in artifact_data.get("artifacts", {}).values():
        definer = artifact.get("definer_module")
        if definer:
            degrees[definer] += 1
    return dict(degrees)


# ==========================================================
# DEPENDENCY TYPE BREAKDOWN
# ==========================================================

def _compute_dep_type_breakdown(matrix: dict) -> dict[str, int]:
    breakdown: dict[str, int] = defaultdict(int)
    for deps in matrix.values():
        for dep in deps.values():
            for dt in dep.get("dep_types", []):
                breakdown[dt] += 1
    return dict(breakdown)


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
    scope_modules: set | None = None,
) -> dict:
    """
    Generates the graph_analytics report.

    Args:
        artifact_data:  Result of generate_artifact_usage_report() (full dict).
        hard_edges:     Dict[module_id, list[module_id]] -- hard import graph.
        soft_edges:     Dict[module_id, list[module_id]] -- soft dependencies (unused here).
        modules:        Full module index (optional).
        index_dict:     IndexDictionary instance (optional, for compact module IDs in matrix).
        scope:          "global", "layer", or "single_file".
        scope_modules:  Set of module IDs to limit output to (layer/single_file).

    Returns:
        dict -- the full graph_analytics report.
    """
    # Scope filtering
    if scope_modules:
        hard_edges = {
            src: [t for t in tgts if t in scope_modules]
            for src, tgts in hard_edges.items()
            if src in scope_modules
        }
        filtered_arts = {
            key: art for key, art in artifact_data.get("artifacts", {}).items()
            if art.get("definer_module") in scope_modules
        }
        scoped_artifact_data: dict = {**artifact_data, "artifacts": filtered_arts}
    else:
        scoped_artifact_data = artifact_data

    # Fan-in / fan-out from artifact perspective
    fan_in: dict[str, set] = defaultdict(set)
    fan_out: dict[str, set] = defaultdict(set)

    for _key, art in scoped_artifact_data.get("artifacts", {}).items():
        definer = art.get("definer_module")
        for consumer in art.get("consumers", []):
            if definer and consumer != definer:
                fan_in[definer].add(consumer)
                fan_out[consumer].add(definer)

    export_degrees = _compute_export_degrees(scoped_artifact_data)

    # Graph centrality
    pagerank = _compute_pagerank(hard_edges)
    betweenness = _compute_betweenness(hard_edges)
    hub_scores, authority_scores = _compute_hub_authority(hard_edges)
    bridge_scores = _compute_bridge_score(hard_edges, betweenness)

    # Collect all relevant module IDs
    all_module_ids: set[str] = set()
    all_module_ids.update(hard_edges.keys())
    for tgts in hard_edges.values():
        all_module_ids.update(tgts)
    all_module_ids.update(fan_in.keys())
    all_module_ids.update(fan_out.keys())
    if scope_modules:
        all_module_ids &= scope_modules

    # Per-module metrics
    modules_report: dict[str, Any] = {}
    for mod_id in sorted(all_module_ids):
        layer = _classify_layer(mod_id)
        consumers_list = sorted(fan_in.get(mod_id, set()))
        visibility = _classify_visibility(mod_id, consumers_list, layer)

        entry: dict[str, Any] = {
            "fan_in": len(fan_in.get(mod_id, set())),
            "fan_out": len(fan_out.get(mod_id, set())),
            "export_degree": export_degrees.get(mod_id, 0),
            "visibility": visibility,
            "layer": layer,
            "betweenness": betweenness.get(mod_id, 0.0),
            "pagerank": pagerank.get(mod_id, 0.0),
            "hub_score": hub_scores.get(mod_id, 0.0),
            "authority_score": authority_scores.get(mod_id, 0.0),
            "bridge_score": bridge_scores.get(mod_id, 0.0),
        }

        if index_dict is not None:
            entry["module_idx"] = index_dict.get_module_id(mod_id)

        modules_report[mod_id] = entry

    # Module dependency matrix
    dep_matrix = build_module_dependency_matrix(scoped_artifact_data, hard_edges)

    # Always use compact index IDs when index_dict is provided (all scopes).
    # Human-readable conversion is handled by the GUI's 'rewrite index' button.
    if index_dict is not None:
        compact_matrix: dict = {}
        for consumer, deps in dep_matrix.items():
            c_idx = str(index_dict.get_module_id(consumer))
            compact_matrix[c_idx] = {
                str(index_dict.get_module_id(definer)): dep_data
                for definer, dep_data in deps.items()
            }
    else:
        compact_matrix = dep_matrix

    # Jaccard-based clusters
    clusters = build_jaccard_clusters(scoped_artifact_data)

    # Dependency type breakdown
    dep_breakdown = _compute_dep_type_breakdown(dep_matrix)

    return {
        "schema_version": "1.0",
        "report_type": "graph_analytics",
        "scope": scope,
        "module_count": len(modules_report),
        "modules": modules_report,
        "module_dependency_matrix": compact_matrix,
        "shared_usage_clusters": clusters,
        "dependency_type_breakdown": dep_breakdown,
    }


__all__ = [
    "generate_graph_analytics_report",
    "build_module_dependency_matrix",
    "build_jaccard_clusters",
    "_classify_layer",
    "_classify_visibility",
]
