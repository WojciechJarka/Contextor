"""
contextor/core/reporting_layer/artifact_usage_report.py

GLOBAL ARTIFACT USAGE REPORT

Layer:
    REPORT ASSEMBLY (auxiliary, invoked by reporting.py)

Responsibilities:
- Gathers symbols (functions / classes / methods / globals) defined in each module
- Determines which modules actually use the same artifacts
- Groups consumer modules into shared usage clusters
- Prepares candidates for core logic extraction in an LLM-friendly format

Does not do:
- AST parsing
- Reference classification
- Scoring
- Dead-code detection
- Architectural validation
- Refactoring planning

Sources of truth:
    symbol_engine
        -> local module symbols

    reference.engine
        -> symbol usage facts

    api_consumers
        -> normalized consumer classification


NOTE:
    shared_usage_clusters is limited to MAX_CLUSTERS.

    Cluster artifacts contain only artifact_id and the relevant
    consumer subset so the report does not duplicate full artifact
    records.
"""

import os
from collections import defaultdict, deque
from datetime import datetime
from itertools import combinations

from contextor.core.analysis.test_context import (
    build_test_context,
    build_test_context_index,
    discover_test_dirs,
)
from contextor.core.api.api_consumers import extract_api_consumers
from contextor.core.errors import AnalysisCancelled, checkpoint
from contextor.core.reference import (
    RepositoryReferenceIndex,
    build_repository_reference_index,
    build_symbol_references,
)
from contextor.core.symbol_engine import extract_file_symbols


# ==========================================================
# CONFIG
# ==========================================================

MIN_SHARED_CONSUMERS = 2
MIN_CLUSTER_SIZE = 2
MAX_CLUSTERS = 30


# ==========================================================
# SYMBOL COLLECTION PER MODULE
# ==========================================================


def _module_own_symbols(symbols: dict) -> list[str]:
    """
    Return all symbols defined by a module.

    The ordering follows the symbol-engine categories so the
    resulting artifact processing remains deterministic.
    """
    return (
        symbols.get("classes", [])
        + symbols.get("functions", [])
        + symbols.get("methods", [])
        + symbols.get("globals", [])
    )


def _symbol_kind(symbol: str, symbols: dict) -> str:
    """
    Resolve the artifact kind from the symbol-engine output.
    """
    if symbol in symbols.get("classes", []):
        return "class"

    if symbol in symbols.get("functions", []):
        return "function"

    if symbol in symbols.get("methods", []):
        return "method"

    if symbol in symbols.get("globals", []):
        return "global"

    return "unknown"


# ==========================================================
# PROCESS WORKER STATE
# ==========================================================

# The module index is identical for every task, so it is handed
# to each worker once at process start rather than pickled into
# every individual work item.

_WORKER_MODULES: dict = {}
_WORKER_ROOT: str = ""
_WORKER_REFERENCE_INDEX: RepositoryReferenceIndex | None = None
_WORKER_SYMBOL_FACTS: dict[str, dict] = {}


def _init_artifact_worker(
    modules: dict,
    root_path: str,
    reference_index: RepositoryReferenceIndex | None = None,
    symbol_facts_by_module: dict[str, dict] | None = None,
) -> None:
    """
    Initialize process-local worker state.
    """
    global _WORKER_MODULES, _WORKER_ROOT, _WORKER_REFERENCE_INDEX, _WORKER_SYMBOL_FACTS

    _WORKER_MODULES = modules
    _WORKER_ROOT = root_path
    _WORKER_REFERENCE_INDEX = reference_index
    _WORKER_SYMBOL_FACTS = symbol_facts_by_module or {}


def _process_single_artifact_module(module_id: str):
    """
    Build symbol/reference facts for one defining module.
    """
    module = _WORKER_MODULES[module_id]

    absolute_path = (
        getattr(module, "absolute_path", None)
        or module.path
    )

    fact_record = _WORKER_SYMBOL_FACTS.get(module_id)
    if fact_record and fact_record.get("status") == "available":
        symbols = fact_record["facts"]
    else:
        symbols = extract_file_symbols(str(absolute_path))
    own_symbols = _module_own_symbols(symbols)

    if not own_symbols:
        return module_id, {
            "symbols": symbols,
            "own_symbols": own_symbols,
            "consumers": {},
        }

    references = build_symbol_references(
        _WORKER_MODULES,
        own_symbols,
        _WORKER_ROOT,
        definer_module=module_id,
        reference_index=_WORKER_REFERENCE_INDEX,
    )

    signatures = symbols.get("signatures", {})

    consumers = extract_api_consumers(
        own_symbols,
        references,
        signatures=signatures,
    )

    return module_id, {
        "symbols": symbols,
        "own_symbols": own_symbols,
        "consumers": consumers,
    }


def collect_module_artifacts(
    modules: dict,
    root_path: str,
    progress_callback=None,
    reference_index: RepositoryReferenceIndex | None = None,
    symbol_facts_by_module: dict[str, dict] | None = None,
) -> tuple[dict, dict]:
    """
    Collect artifact/reference information for all modules.

    A failure in one module is surfaced in the returned failures
    mapping instead of aborting the entire report.
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed

    result = {}
    failures = {}

    total = len(modules)
    completed = 0

    if reference_index is None:
        reference_index = build_repository_reference_index(modules, root_path)

    symbol_facts_by_module = symbol_facts_by_module or {}
    for module_id, facts in symbol_facts_by_module.items():
        if facts.get("status") == "failure":
            failures[module_id] = (
                f"{facts.get('exception_type', 'Exception')}: "
                f"{facts.get('message', '')}"
            )

    eligible_module_ids = [
        module_id
        for module_id in modules
        if module_id not in failures
    ]

    if os.environ.get("CONTEXTOR_DISABLE_PROCESS_POOL") == "1":
        _init_artifact_worker(
            modules, root_path, reference_index, symbol_facts_by_module
        )
        for module_id in eligible_module_ids:
            try:
                returned_module_id, data = _process_single_artifact_module(module_id)
                result[returned_module_id] = data
            except Exception as exc:
                failures[module_id] = f"{type(exc).__name__}: {exc}"
            completed += 1
            checkpoint(progress_callback, f"JSON: {module_id}", completed, total)
        return result, failures

    with ProcessPoolExecutor(
        initializer=_init_artifact_worker,
        initargs=(
            modules,
            root_path,
            reference_index,
            symbol_facts_by_module,
        ),
    ) as executor:
        futures = {
            executor.submit(
                _process_single_artifact_module,
                module_id,
            ): module_id
            for module_id in eligible_module_ids
        }

        for future in as_completed(futures):
            module_id = futures[future]

            try:
                returned_module_id, data = future.result()
                result[returned_module_id] = data

            except Exception as exc:
                failures[module_id] = (
                    f"{type(exc).__name__}: {exc}"
                )

            completed += 1

            try:
                checkpoint(
                    progress_callback,
                    f"JSON: {module_id}",
                    completed,
                    total,
                )
            except AnalysisCancelled:
                executor.shutdown(
                    wait=False,
                    cancel_futures=True,
                )
                raise

    return result, failures


# ==========================================================
# GLOBAL ARTIFACT INDEX
# ==========================================================


def build_artifact_index(
    module_artifacts: dict,
) -> tuple[dict, dict]:
    """
    Flatten per-module artifact data into the global artifact index.

    Artifact identity:

        <definer_module>::<symbol>

    Returns:

        artifacts
            Lean artifact index intended for the main report.

        usage_sidecar
            Raw usage data intended for artifacts_usage.json.

    Artifacts with no confirmed consumers are omitted. Ambiguous
    reference evidence is preserved only inside the usage sidecar
    and does not create consumers.
    """
    artifacts = {}
    usage_sidecar = {}

    for module_id, data in module_artifacts.items():
        symbols = data["symbols"]
        consumers = data["consumers"]

        for symbol in data["own_symbols"]:
            consumer_data = consumers.get(symbol, {})

            consumer_modules = sorted(
                {
                    consumer
                    for consumer in consumer_data.get(
                        "consumers",
                        [],
                    )
                    if consumer != module_id
                }
            )

            # No confirmed consumers means there is no artifact
            # relationship to expose in this report.
            if not consumer_modules:
                continue

            key = f"{module_id}::{symbol}"

            kind = _symbol_kind(
                symbol,
                symbols,
            )

            usage = consumer_data.get(
                "usage",
                {},
            )

            artifacts[key] = {
                "artifact_id": key,
                "artifact": symbol,
                "kind": kind,
                "signature": consumer_data.get(
                    "signature",
                    "",
                ),
                "definer_module": module_id,
                "consumers": consumer_modules,
                "consumer_count": len(consumer_modules),
            }

            if usage:
                usage_sidecar[key] = usage

    return (
        dict(sorted(artifacts.items())),
        usage_sidecar,
    )


def collect_qualified_artifact_identities(module_artifacts: dict) -> set[str]:
    """Return stable identities for every symbol defined by the repository."""
    return {
        f"{module_id}::{symbol}"
        for module_id, data in module_artifacts.items()
        for symbol in data.get("own_symbols", set())
        if isinstance(symbol, str) and symbol
    }


# ==========================================================
# SHARED ARTIFACTS
# ==========================================================


def get_shared_artifact_keys(
    artifacts: dict,
    min_consumers: int = MIN_SHARED_CONSUMERS,
) -> list[str]:
    """
    Return artifact IDs used by at least min_consumers modules.

    Results are ordered deterministically:

        1. descending consumer count
        2. defining module
        3. artifact name
    """
    shared = [
        (key, data["consumer_count"])
        for key, data in artifacts.items()
        if data["consumer_count"] >= min_consumers
    ]

    return [
        key
        for key, _ in sorted(
            shared,
            key=lambda item: (
                -item[1],
                artifacts[item[0]]["definer_module"],
                artifacts[item[0]]["artifact"],
            ),
        )
    ]


def filter_shared_artifacts(
    artifacts: dict,
    min_consumers: int = MIN_SHARED_CONSUMERS,
) -> list[dict]:
    """
    Compatibility helper returning full artifact records.

    New code should prefer get_shared_artifact_keys().
    """
    shared = [
        {
            "key": key,
            **data,
        }
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


def _build_consumer_graph(
    shared_artifacts: list[dict],
) -> dict:
    """
    Build an undirected graph where two consumer modules are
    connected when they consume the same artifact.
    """
    graph = defaultdict(set)

    for artifact in shared_artifacts:
        consumers = artifact["consumers"]

        for left, right in combinations(
            consumers,
            2,
        ):
            graph[left].add(right)
            graph[right].add(left)

    return graph


def _connected_components(
    graph: dict,
) -> list[list[str]]:
    """
    Return connected components in deterministic order.
    """
    visited = set()
    clusters = []

    for node in sorted(graph):
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

            for neighbour in sorted(graph[current]):
                if neighbour not in visited:
                    queue.append(neighbour)

        clusters.append(
            sorted(component)
        )

    return sorted(
        clusters,
        key=lambda component: (
            -len(component),
            component,
        ),
    )


def build_shared_usage_clusters(
    shared_artifacts: list[dict],
    min_cluster_size: int = MIN_CLUSTER_SIZE,
) -> list[dict]:
    """
    Group consumer modules that share confirmed artifact usage.

    A cluster is only a structural candidate for further review.
    It is not itself an architectural/refactoring decision.
    """
    graph = _build_consumer_graph(
        shared_artifacts
    )

    components = _connected_components(
        graph
    )

    clusters = []

    for component in components:
        if len(component) < min_cluster_size:
            continue

        component_set = set(component)

        cluster_artifacts = []

        for artifact in shared_artifacts:
            relevant_consumers = [
                consumer
                for consumer in artifact["consumers"]
                if consumer in component_set
            ]

            if not relevant_consumers:
                continue

            cluster_artifacts.append(
                {
                    "artifact_id": artifact.get(
                        "artifact_id",
                        artifact.get("key"),
                    ),
                    "consumers": sorted(
                        relevant_consumers
                    ),
                }
            )

        clusters.append(
            {
                "modules": component,
                "size": len(component),
                "shared_artifact_count": len(
                    cluster_artifacts
                ),
                "shared_artifacts": cluster_artifacts,
            }
        )

    clusters.sort(
        key=lambda cluster: (
            -cluster["shared_artifact_count"],
            -cluster["size"],
            cluster["modules"],
        )
    )

    return clusters[:MAX_CLUSTERS]


# ==========================================================
# CORE EXTRACTION CANDIDATES
# ==========================================================


def _dominant_definers(
    cluster: dict,
    artifacts: dict,
) -> list[str]:
    """
    Return modules that define the largest number of artifacts
    shared inside the cluster.
    """
    counts = defaultdict(int)

    for cluster_artifact in cluster["shared_artifacts"]:
        artifact = artifacts.get(
            cluster_artifact["artifact_id"]
        )

        if artifact:
            counts[
                artifact["definer_module"]
            ] += 1

    return sorted(
        counts,
        key=lambda module: (
            -counts[module],
            module,
        ),
    )


def build_core_extraction_candidates(
    clusters: list[dict],
    artifacts: dict,
) -> list[dict]:
    """
    Produce structural candidates for LLM review.

    This function does not decide that extraction is correct.
    It only exposes strong shared-usage relationships.
    """
    candidates = []

    for cluster in clusters:
        definers = _dominant_definers(
            cluster,
            artifacts,
        )

        top_artifacts = sorted(
            cluster["shared_artifacts"],
            key=lambda artifact: (
                -len(artifact["consumers"]),
                artifact["artifact_id"],
            ),
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
                        "artifact_id": artifact[
                            "artifact_id"
                        ],
                        "used_by": artifact[
                            "consumers"
                        ],
                    }
                    for artifact in top_artifacts
                ],
                "reason": (
                    "modules share the usage of the same "
                    "artifacts (functions/classes/methods/globals) - "
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
    progress_callback=None,
    symbol_facts_by_module: dict[str, dict] | None = None,
) -> dict:
    """
    Generate the global artifact usage report.

    The report contains:

        artifacts
            Lean artifact index.

        _usage_sidecar
            Raw usage data for artifacts_usage.json.

        _module_artifacts
            Intermediate per-module data retained for the
            report engine.

    Consumer classification is performed upstream by
    api_consumers.py. This layer only assembles the results.
    """
    module_artifacts, failures = (
        collect_module_artifacts(
            modules,
            root_path,
            progress_callback=progress_callback,
            symbol_facts_by_module=symbol_facts_by_module,
        )
    )

    artifact_index, usage_sidecar = (
        build_artifact_index(
            module_artifacts
        )
    )

    shared_artifact_keys = (
        get_shared_artifact_keys(
            artifact_index
        )
    )

    # Clustering requires consumer lists, so temporarily recover
    # the full shared artifact records from the lean index.
    shared_artifacts_full = (
        filter_shared_artifacts(
            artifact_index
        )
    )

    clusters = build_shared_usage_clusters(
        shared_artifacts_full
    )

    core_candidates = (
        build_core_extraction_candidates(
            clusters,
            artifact_index,
        )
    )

    runtime_info = (
        runtime.copy()
        if runtime
        else {}
    )

    runtime_info["generated_at"] = (
        datetime.now().isoformat()
    )

    # ======================================================
    # TEST TRACEABILITY
    # ======================================================

    test_coverage_mapping = {}

    total_test = len(modules)
    completed_test = 0

    # Invert artifact ownership once instead of scanning the
    # entire artifact index for every module.
    symbols_by_definer = defaultdict(list)

    for entry in artifact_index.values():
        symbols_by_definer[
            entry["definer_module"]
        ].append(
            entry["artifact"]
        )

    for symbols in symbols_by_definer.values():
        symbols.sort()

    # Test directories and AST facts are repository-level information and
    # therefore discovered and indexed once.
    test_dirs = discover_test_dirs(
        root_path,
        allowed_python_paths=[module.path for module in modules.values()],
    )

    test_index = build_test_context_index(
        root_path,
        test_dirs=test_dirs,
        modules=modules,
        allowed_python_paths=[module.path for module in modules.values()],
    )

    for module_id in modules:
        checkpoint(
            progress_callback,
            f"TESTS: {module_id}",
            completed_test,
            total_test,
        )

        test_coverage_mapping[module_id] = (
            build_test_context(
                module_id,
                root_path,
                symbols_by_definer.get(
                    module_id,
                    [],
                ),
                test_dirs=test_dirs,
                test_index=test_index,
            )
        )

        completed_test += 1

    # ======================================================
    # REPORT
    # ======================================================

    report = {
        "runtime": runtime_info,
        "module_count": len(modules),
        "artifact_count": len(
            artifact_index
        ),
        "shared_artifact_count": len(
            shared_artifact_keys
        ),
        "shared_artifact_keys": (
            shared_artifact_keys
        ),
        "artifacts": artifact_index,
        "shared_usage_clusters": clusters,
        "core_extraction_candidates": (
            core_candidates
        ),
        "test_traceability": (
            test_coverage_mapping
        ),
    }

    # A partial report must remain visibly partial.
    if failures:
        report["skipped_modules"] = dict(
            sorted(failures.items())
        )
        report["skipped_module_count"] = len(
            failures
        )

    # Private engine-side payloads.
    report["_usage_sidecar"] = (
        usage_sidecar
    )
    report["_module_artifacts"] = (
        module_artifacts
    )

    return report


# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [
    "collect_module_artifacts",
    "build_artifact_index",
    "get_shared_artifact_keys",
    "filter_shared_artifacts",
    "build_shared_usage_clusters",
    "build_core_extraction_candidates",
    "generate_artifact_usage_report",
]
