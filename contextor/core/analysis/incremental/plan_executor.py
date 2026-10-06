"""
contextor/core/analysis/incremental/plan_executor.py

RefreshPlan execution pipeline for incremental updates:
- CandidateState Copy-on-Write container
- PlanExecutionOutcome immutable result contract
- Execution phases: REPARSE, RECOMPUTE, PATCH, GRAPH
- Fail-closed patch family and graph recomputation dispatch
- Complete isolation from disk I/O and threading locks
"""

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Set, Dict, Tuple, Any, Mapping

from contextor.core.analysis.incremental.graph_ops import calculate_affected_set
from contextor.core.analysis.state_manager import (
    FileDelta,
    RepositoryAnalysisState,
    canonical_artifact_consumption_targets,
    validate_canonical_artifact_consumption_coverage,
)
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.lineage_facts import MaterializedLineageSourceFacts
from contextor.core.domain.module import Module
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.graph.graph import build_trie, detect_package_root, build_graph, resolve_module_edges
from contextor.core.reference.shared import (
    _assemble_reexport_map,
    validate_reexport_facts_by_module,
)
from contextor.core.reference.resolution import _resolve_alias, _resolve_reexport
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_qualified_artifact_identities,
)


@dataclass
class CandidateState:
    """
    Mutable Copy-on-Write candidate container holding the in-flight
    architectural model during RefreshPlan execution before commit.
    """
    modules: Dict[str, Any]
    reexport_facts_by_module: Dict[str, Dict[str, Any]]
    artifacts: Dict[str, Any]
    module_parse_freshness: Dict[str, Dict[str, Any]]
    syntax_diagnostics_by_path: Dict[str, Dict[str, Any]]
    syntax_diagnostics_state: str
    module_usages: Dict[str, Any]
    lineage_facts_by_source: Dict[str, MaterializedLineageSourceFacts]
    lineage_facts_state: str
    lineage_facts_semantic_version: str | None
    lineage_owner_source_index: Dict[str, tuple[str, ...]]
    lineage_source_owner_index: Dict[str, tuple[str, ...]]
    lineage_query_index_state: str
    lineage_semantic_anchor_bindings_complete: bool
    artifact_consumption: Dict[str, Any]
    dependency_graph: Optional[ProjectGraph]
    trie: Any
    package_root: Any
    metrics: Any
    topology_analytics: Dict[str, Any]
    dependency_matrix: Dict[str, Any]
    dependency_matrix_state: str
    shared_usage_clusters: list
    shared_usage_clusters_state: str
    cached_analytics: Dict[str, Any]
    topology_metrics_state: str
    cached_analytics_state: str
    cycles: list
    cycles_state: str
    collision_facts: Dict[str, list]
    collisions: list
    collisions_state: str
    artifact_consumption_state: str = "deferred"


@dataclass(frozen=True)
class PlanExecutionOutcome:
    """
    Immutable result of RefreshPlan execution containing the computed candidate state,
    affected modules, execution trace, and identity registry sync requirements.
    """
    candidate_state: CandidateState
    affected_modules: Set[str]
    blast_radius_complete: bool
    execution_trace: Dict[str, Tuple[str, ...]]
    identity_sync_required: bool
    all_modules: Set[str]
    current_artifacts: Dict[str, Any]


def _get_copy_of_entry(raw_entry: dict) -> dict:
    """Deep-copies consumers and channels for one artifact_consumption entry."""
    consumers = list(raw_entry.get("consumers", []))
    channels = {
        k: list(v)
        for k, v in raw_entry.get("channels", {}).items()
    }
    return {"consumers": consumers, "channels": channels}


def _build_consumer_target_index(
    consumption: Mapping[str, Any],
) -> Dict[str, Set[str]]:
    """
    Builds one transient reverse lookup for the current plan execution.

    This is execution-local acceleration only. It is not canonical state
    and is never persisted.
    """
    index: Dict[str, Set[str]] = {}

    for target, raw_entry in consumption.items():
        if not isinstance(raw_entry, dict):
            continue

        consumers = raw_entry.get("consumers", ())
        if isinstance(
            consumers,
            (
                list,
                tuple,
                set,
            ),
        ):
            for consumer in consumers:
                if (
                    isinstance(consumer, str)
                    and consumer
                ):
                    index.setdefault(
                        consumer,
                        set(),
                    ).add(target)

        channels = raw_entry.get(
            "channels",
            {},
        )
        if isinstance(channels, dict):
            for consumer in channels:
                if (
                    isinstance(consumer, str)
                    and consumer
                ):
                    index.setdefault(
                        consumer,
                        set(),
                    ).add(target)

    return index


def _consumer_slice_signature(
    consumer: str,
    consumption: Mapping[str, Any],
    consumer_target_index: Mapping[str, Set[str]],
) -> Tuple[Tuple[str, bool, Tuple[str, ...]], ...]:
    """
    Return a deterministic execution-local signature of one consumer's
    canonical artifact_consumption slice.

    This observes only canonical RAM state. It performs no source I/O.
    """
    rows: List[Tuple[str, bool, Tuple[str, ...]]] = []

    for target in sorted(
        consumer_target_index.get(
            consumer,
            set(),
        )
    ):
        entry = consumption.get(
            target,
            {},
        )
        if not isinstance(entry, dict):
            continue

        consumers = entry.get(
            "consumers",
            (),
        )
        channels = entry.get(
            "channels",
            {},
        )

        is_consumer = (
            consumer in consumers
            if isinstance(
                consumers,
                (
                    list,
                    tuple,
                    set,
                ),
            )
            else False
        )

        consumer_channels: Tuple[str, ...] = ()
        if isinstance(channels, dict):
            raw_channels = channels.get(
                consumer,
                (),
            )
            if isinstance(
                raw_channels,
                (
                    list,
                    tuple,
                    set,
                ),
            ):
                consumer_channels = tuple(
                    sorted(
                        str(channel)
                        for channel in raw_channels
                    )
                )

        if is_consumer or consumer_channels:
            rows.append(
                (
                    target,
                    is_consumer,
                    consumer_channels,
                )
            )

    return tuple(rows)


def _build_dotted_target_index(
    expected_targets: Set[str],
) -> Dict[str, Tuple[str, ...]]:
    """
    Builds one transient lookup from dotted target spelling to all
    canonical targets that share that spelling.

    All canonical identities with the same exact dotted spelling are
    preserved so incremental consumer rebuilding matches the full-analysis
    reference projection.
    """
    grouped: Dict[str, List[str]] = {}

    for canonical in expected_targets:
        definer, sep, symbol = canonical.partition("::")
        if not sep:
            continue

        dotted = f"{definer}.{symbol}"
        grouped.setdefault(
            dotted,
            [],
        ).append(
            canonical
        )

    return {
        dotted: tuple(
            sorted(
                targets
            )
        )
        for dotted, targets in grouped.items()
    }


def _resolve_canonical_target_keys(
    target: Optional[str],
    candidate_consumption: Mapping[str, Any],
    candidate_artifacts: Mapping[str, Any],
    expected_targets: Optional[Set[str]] = None,
    dotted_target_index: Optional[
        Mapping[str, Tuple[str, ...]]
    ] = None,
) -> Tuple[Tuple[str, ...], str]:
    """
    Resolve one reference spelling to every exact canonical target
    represented by that spelling.

    A complete dotted spelling may map to more than one canonical
    identity, for example:

        pkg.a::B.foo
        pkg.a.B::foo

    both serialize to:

        pkg.a.B.foo

    Full analysis projects confirmed evidence to every such exact
    canonical identity. Incremental rebuilding must preserve the same
    semantics.

    This helper performs no short-name fallback.
    """
    if not target:
        return (), "unresolved"

    if expected_targets is None:
        expected_targets = canonical_artifact_consumption_targets(
            candidate_artifacts
        )

    if "::" in target:
        if target in expected_targets:
            return (target,), "resolved"
        return (), "unresolved"

    if dotted_target_index is not None:
        matches = tuple(
            dotted_target_index.get(
                target,
                (),
            )
        )
    else:
        matches = tuple(
            sorted(
                canonical
                for canonical in expected_targets
                if (
                    "::" in canonical
                    and ".".join(
                        canonical.split("::", 1)
                    ) == target
                )
            )
        )

    matches = tuple(
        sorted(
            set(matches)
        )
    )

    if matches:
        return matches, "resolved"

    return (), "unresolved"


def _resolve_canonical_target_key(
    target: Optional[str],
    candidate_consumption: Mapping[str, Any],
    candidate_artifacts: Mapping[str, Any],
    expected_targets: Optional[Set[str]] = None,
    dotted_target_index: Optional[
        Mapping[str, Tuple[str, ...]]
    ] = None,
) -> Tuple[Optional[str], str]:
    """
    Singular compatibility resolver.

    Returns one canonical key only when the exact spelling identifies
    exactly one canonical identity. Multiple exact canonical identities
    retain the existing singular 'ambiguous' result.
    """
    matches, status = _resolve_canonical_target_keys(
        target,
        candidate_consumption,
        candidate_artifacts,
        expected_targets=expected_targets,
        dotted_target_index=dotted_target_index,
    )

    if status != "resolved":
        return None, status

    if len(matches) == 1:
        return matches[0], "resolved"

    return None, "ambiguous"


def _to_canonical_target_key(
    target: Optional[str],
    candidate_consumption: Mapping[str, Any],
    candidate_artifacts: Mapping[str, Any],
) -> Optional[str]:
    key, _status = _resolve_canonical_target_key(target, candidate_consumption, candidate_artifacts)
    return key


def _rebuild_consumer_slice(
    consumer: str,
    consumer_facts: ModuleUsageFacts,
    candidate_consumption: Dict[str, Any],
    candidate_artifacts: Mapping[str, Any],
    reexports: Mapping[str, str],
    expected_targets: Optional[Set[str]] = None,
    dotted_target_index: Optional[
        Mapping[str, Tuple[str, ...]]
    ] = None,
    consumer_target_index: Optional[Dict[str, Set[str]]] = None,
) -> Dict[str, Any]:
    """
    Rebuilds the entire artifact_consumption slice for a single consumer.

    When an execution-local reverse index is supplied, the candidate
    top-level mapping is already Copy-On-Write and only entries known to
    contain the consumer are inspected. Nested entries are still copied
    before mutation.

    Without the execution-local index, the legacy full-map fallback is
    preserved.

    Returns the updated consumption dictionary. A complete dotted
    spelling that maps to multiple exact canonical identities is projected
    to each identity, matching the full-analysis reference projection.
    """
    c_aliases = dict(consumer_facts.aliases)
    c_tagged = (
        [
            (sym, "direct_calls")
            for sym in consumer_facts.direct_calls
        ]
        + [
            (sym, "runtime_calls")
            for sym in consumer_facts.runtime_calls
        ]
        + [
            (sym, "qualified_refs")
            for sym in consumer_facts.qualified_refs
        ]
        + [
            (sym, "callback_calls")
            for sym in consumer_facts.callback_calls
        ]
        + [
            (sym, "event_bindings")
            for sym in consumer_facts.event_bindings
        ]
        + [
            (sym, "api_imports")
            for sym in consumer_facts.imports
        ]
        + [
            (item[1], "inheritance")
            for item in consumer_facts.inheritance_refs
            if len(item) >= 2 and item[1]
        ]
    )

    rebuilt_targets: Dict[str, Set[str]] = {}
    for sym, ch_name in c_tagged:
        raw_t = _resolve_reexport(
            _resolve_alias(
                sym,
                c_aliases,
            ),
            reexports,
        )
        if (
            ch_name == "api_imports"
            and raw_t in candidate_artifacts
        ):
            continue

        targets, status = _resolve_canonical_target_keys(
            raw_t,
            candidate_consumption,
            candidate_artifacts,
            expected_targets=expected_targets,
            dotted_target_index=dotted_target_index,
        )

        if status == "resolved":
            for target in targets:
                if target not in rebuilt_targets:
                    rebuilt_targets[target] = set()

                rebuilt_targets[target].add(
                    ch_name
                )

    if consumer_target_index is None:
        new_consumption = dict(
            candidate_consumption
        )
        previous_targets = tuple(
            new_consumption.keys()
        )
    else:
        new_consumption = candidate_consumption
        previous_targets = tuple(
            consumer_target_index.get(
                consumer,
                (),
            )
        )

    # Remove the consumer only from entries known to contain its old slice.
    for t_key in previous_targets:
        entry = new_consumption.get(
            t_key
        )
        if not isinstance(entry, dict):
            continue

        if (
            consumer in entry.get(
                "consumers",
                [],
            )
            or consumer
            in entry.get(
                "channels",
                {},
            )
        ):
            copied_entry = _get_copy_of_entry(
                entry
            )

            if consumer in copied_entry[
                "consumers"
            ]:
                copied_entry[
                    "consumers"
                ].remove(
                    consumer
                )

            copied_entry[
                "channels"
            ].pop(
                consumer,
                None,
            )

            new_consumption[
                t_key
            ] = copied_entry

    # Install rebuilt exact slice.
    for target, channels in rebuilt_targets.items():
        entry = _get_copy_of_entry(
            new_consumption.get(
                target,
                {
                    "consumers": [],
                    "channels": {},
                },
            )
        )

        if consumer not in entry[
            "consumers"
        ]:
            entry[
                "consumers"
            ].append(
                consumer
            )

        entry[
            "consumers"
        ] = sorted(
            set(
                entry[
                    "consumers"
                ]
            )
        )

        entry[
            "channels"
        ][
            consumer
        ] = sorted(
            channels
        )

        new_consumption[
            target
        ] = entry

    if consumer_target_index is not None:
        if rebuilt_targets:
            consumer_target_index[
                consumer
            ] = set(
                rebuilt_targets
            )
        else:
            consumer_target_index.pop(
                consumer,
                None,
            )

    return new_consumption


def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
    """Initializes Copy-on-Write candidate state from current canonical state."""
    return CandidateState(
        modules=dict(state.modules),
        reexport_facts_by_module=dict(
            getattr(
                state,
                "reexport_facts_by_module",
                {},
            )
            or {}
        ),
        artifacts=dict(state.artifacts),
        module_parse_freshness=dict(getattr(state, "module_parse_freshness", {}) or {}),
        syntax_diagnostics_by_path=dict(getattr(state, "syntax_diagnostics_by_path", {}) or {}),
        syntax_diagnostics_state=getattr(state, "syntax_diagnostics_state", "not_materialized"),
        module_usages=dict(getattr(state, "module_usages", {}) or {}),
        lineage_facts_by_source=dict(
            getattr(state, "lineage_facts_by_source", {}) or {}
        ),
        lineage_facts_state=(
            getattr(state, "lineage_facts_state", "not_materialized")
            or "not_materialized"
        ),
        lineage_facts_semantic_version=getattr(
            state,
            "lineage_facts_semantic_version",
            None,
        ),
        lineage_owner_source_index=dict(
            getattr(state, "lineage_owner_source_index", {}) or {}
        ),
        lineage_source_owner_index=dict(
            getattr(state, "lineage_source_owner_index", {}) or {}
        ),
        lineage_query_index_state=getattr(
            state,
            "lineage_query_index_state",
            "not_materialized",
        ),
        lineage_semantic_anchor_bindings_complete=bool(
            getattr(state, "lineage_semantic_anchor_bindings_complete", False)
        ),
        artifact_consumption=dict(state.artifact_consumption or {}),
        dependency_graph=state.dependency_graph,
        trie=state.trie,
        package_root=state.package_root,
        metrics=state.metrics,
        topology_analytics=dict(getattr(state, "topology_analytics", {}) or {}),
        dependency_matrix=dict(
            getattr(state, "dependency_matrix", {}) or {}
        ),
        dependency_matrix_state=getattr(
            state,
            "dependency_matrix_state",
            "deferred",
        ),
        shared_usage_clusters=list(
            getattr(state, "shared_usage_clusters", []) or []
        ),
        shared_usage_clusters_state=getattr(
            state,
            "shared_usage_clusters_state",
            "deferred",
        ),
        cached_analytics=dict(getattr(state, "cached_analytics", {}) or {}),
        topology_metrics_state=getattr(state, "topology_metrics_state", "deferred"),
        cached_analytics_state=getattr(state, "cached_analytics_state", "deferred"),
        cycles=list(getattr(state, "cycles", []) or []),
        cycles_state=getattr(state, "cycles_state", "deferred"),
        collision_facts=dict(getattr(state, "collision_facts", {}) or {}),
        collisions=list(getattr(state, "collisions", []) or []),
        collisions_state=getattr(state, "collisions_state", "deferred"),
        artifact_consumption_state=getattr(state, "artifact_consumption_state", "deferred"),
    )


def execute_refresh_plan(
    state: RepositoryAnalysisState,
    delta: FileDelta,
    usage_delta: Any,
    plan: RefreshPlan,
    new_imports: Optional[List[Any]],
    new_artifacts: Optional[Dict[str, Any]],
    new_usage: Optional[ModuleUsageFacts],
    root_path: Path,
    file_path: str,
    new_collision_facts: Optional[List[Dict[str, Any]]] = None,
    new_reexport_facts: Optional[Dict[str, Any]] = None,
) -> PlanExecutionOutcome:
    """
    Executes the phases of a RefreshPlan (REPARSE, RECOMPUTE, PATCH, GRAPH)
    on an isolated Copy-on-Write candidate state without performing disk I/O or state mutation.
    """
    path = Path(file_path)
    mod_id = Path(delta.module_path).stem if delta.module_path.endswith(".py") else delta.module_path
    old_graph = state.dependency_graph

    if not validate_reexport_facts_by_module(
        state.reexport_facts_by_module,
        state.modules,
    ):
        raise RuntimeError(
            "Canonical re-export facts baseline is incomplete; "
            "fresh full analysis is required."
        )

    # 1. PREPARE candidate state
    candidate = _prepare_candidate_state(state)
    matrix_inputs_changed = bool(
        {
            "definitions",
            "artifact_consumption",
            "dependency_graph",
        }
        & set(plan.patch_families)
    )
    cluster_inputs_changed = bool(
        {
            "definitions",
            "artifact_consumption",
        }
        & set(plan.patch_families)
    )
    if getattr(state, "resync_required", False):
        candidate.artifact_consumption_state = "stale"

    # Pre-populate candidate modules, artifacts, and usages before RECOMPUTE
    if delta.is_deleted:
        candidate.modules.pop(mod_id, None)
        candidate.modules.pop(delta.module_path, None)
        candidate.reexport_facts_by_module.pop(
            mod_id,
            None,
        )
        candidate.reexport_facts_by_module.pop(
            delta.module_path,
            None,
        )
        candidate.artifacts.pop(mod_id, None)
        candidate.artifacts.pop(delta.module_path, None)
        candidate.module_usages.pop(delta.module_path, None)
        # Purge deleted targets
        for art_key in list(candidate.artifact_consumption.keys()):
            if (
                art_key == mod_id
                or art_key == delta.module_path
                or art_key.startswith(mod_id + ".")
                or art_key.startswith(delta.module_path + ".")
                or art_key.startswith(mod_id + "::")
                or art_key.startswith(delta.module_path + "::")
            ):
                candidate.artifact_consumption.pop(art_key, None)
    else:
        if "modules" in plan.patch_families:
            candidate.modules[delta.module_path] = Module(
                module_id=delta.module_path,
                path=str(path.relative_to(root_path)),
                absolute_path=str(path.resolve()),
                imports=new_imports or [],
            )
        if "definitions" in plan.patch_families and new_artifacts is not None:
            candidate.artifacts[delta.module_path] = new_artifacts
        if "module_usages" in plan.patch_families and new_usage is not None:
            candidate.module_usages[delta.module_path] = new_usage

        # Ensure canonical targets for delta.module_path exist in candidate.artifact_consumption
        mod_art = candidate.artifacts.get(delta.module_path, {})
        if isinstance(mod_art, dict):
            current_targets = canonical_artifact_consumption_targets({delta.module_path: mod_art})
            for t_key in current_targets:
                if t_key not in candidate.artifact_consumption:
                    candidate.artifact_consumption[t_key] = {"consumers": [], "channels": {}}
            for art_key in list(candidate.artifact_consumption.keys()):
                if (
                    art_key.startswith(f"{delta.module_path}::")
                    or art_key.startswith(f"{mod_id}::")
                ) and art_key not in current_targets:
                    candidate.artifact_consumption.pop(art_key, None)

    if not delta.is_deleted and "reexport_facts" in plan.patch_families:
        if new_reexport_facts is None:
            raise ValueError(
                f"Planned reexport_facts patch for '{delta.module_path}' "
                "requires non-None new_reexport_facts."
            )
        candidate.reexport_facts_by_module[
            delta.module_path
        ] = new_reexport_facts

    if not validate_reexport_facts_by_module(
        candidate.reexport_facts_by_module,
        candidate.modules,
    ):
        raise RuntimeError(
            "Candidate re-export facts do not cover the candidate module domain."
        )

    expected_targets = canonical_artifact_consumption_targets(
        candidate.artifacts
    )
    dotted_target_index = _build_dotted_target_index(
        expected_targets
    )
    consumer_target_index = _build_consumer_target_index(
        candidate.artifact_consumption
    )

    # 2. REPARSE - record planned reparse modules (trace-only, no secondary source I/O)
    executed_reparse: List[str] = []
    for reparse_mod in plan.reparse_modules:
        executed_reparse.append(reparse_mod)

    reexports = None
    if (
        plan.recompute_modules
        or "artifact_consumption" in plan.patch_families
    ):
        reexports = _assemble_reexport_map(
            candidate.reexport_facts_by_module
        )

    # 3. RECOMPUTE - re-evaluate planned cached modules in RAM without source I/O
    executed_recompute: List[str] = []
    if plan.recompute_modules:
        from contextor.core.analysis.refresh_planner import (
            _find_dependent_consumers,
        )

        recompute_queue = deque(plan.recompute_modules)
        scheduled_recompute = set(plan.recompute_modules)
        processed_recompute: Set[str] = set()

        while recompute_queue:
            consumer_path = recompute_queue.popleft()

            if consumer_path in processed_recompute:
                continue

            processed_recompute.add(consumer_path)

            consumer_facts = candidate.module_usages.get(
                consumer_path
            )
            if not consumer_facts:
                continue

            previous_slice = _consumer_slice_signature(
                consumer_path,
                candidate.artifact_consumption,
                consumer_target_index,
            )

            candidate.artifact_consumption = _rebuild_consumer_slice(
                consumer=consumer_path,
                consumer_facts=consumer_facts,
                candidate_consumption=candidate.artifact_consumption,
                candidate_artifacts=candidate.artifacts,
                reexports=reexports,
                expected_targets=expected_targets,
                dotted_target_index=dotted_target_index,
                consumer_target_index=consumer_target_index,
            )

            executed_recompute.append(
                consumer_path
            )

            current_slice = _consumer_slice_signature(
                consumer_path,
                candidate.artifact_consumption,
                consumer_target_index,
            )

            if current_slice == previous_slice:
                continue

            downstream_consumers = _find_dependent_consumers(
                consumer_path,
                candidate.module_usages,
            )

            for downstream_consumer in sorted(
                downstream_consumers
            ):
                if downstream_consumer == delta.module_path:
                    continue

                if downstream_consumer in processed_recompute:
                    continue

                if downstream_consumer in scheduled_recompute:
                    continue

                scheduled_recompute.add(
                    downstream_consumer
                )
                recompute_queue.append(
                    downstream_consumer
                )

    # 4. PATCH - apply fact families listed in plan.patch_families
    executed_patch_families: List[str] = []
    identity_sync_required = False

    for family in plan.patch_families:
        if family == "modules":
            executed_patch_families.append("modules")

        elif family == "definitions":
            executed_patch_families.append("definitions")

        elif family == "module_usages":
            executed_patch_families.append("module_usages")

        elif family == "reexport_facts":
            executed_patch_families.append("reexport_facts")

        elif family == "dependency_graph":
            if delta.is_deleted or delta.is_new:
                new_trie = build_trie(candidate.modules.keys())
                new_package_root = detect_package_root(candidate.modules, new_trie)
                new_graph = build_graph(candidate.modules, trie=new_trie, package_root=new_package_root)
                candidate.trie = new_trie
                candidate.package_root = new_package_root
                candidate.dependency_graph = new_graph
            else:
                new_trie = candidate.trie
                new_package_root = candidate.package_root
                curr_graph = candidate.dependency_graph
                if curr_graph:
                    hard, soft = resolve_module_edges(delta.module_path, candidate.modules[delta.module_path], new_trie, new_package_root)
                    candidate.dependency_graph = curr_graph.with_module_edges(delta.module_path, hard, soft)
            executed_patch_families.append("dependency_graph")

        elif family == "artifact_consumption":
            if delta.is_deleted:
                # Remove delta.module_path from all remaining targets
                for t_key, entry in list(candidate.artifact_consumption.items()):
                    if delta.module_path in entry.get("consumers", []) or delta.module_path in entry.get("channels", {}):
                        copied_entry = _get_copy_of_entry(entry)
                        if delta.module_path in copied_entry["consumers"]:
                            copied_entry["consumers"].remove(delta.module_path)
                        copied_entry["channels"].pop(delta.module_path, None)
                        candidate.artifact_consumption[t_key] = copied_entry
            elif new_usage:
                candidate.artifact_consumption = _rebuild_consumer_slice(
                    consumer=delta.module_path,
                    consumer_facts=new_usage,
                    candidate_consumption=candidate.artifact_consumption,
                    candidate_artifacts=candidate.artifacts,
                    reexports=reexports,
                    expected_targets=expected_targets,
                    dotted_target_index=dotted_target_index,
                    consumer_target_index=consumer_target_index,
                )
            if (
                getattr(state, "resync_required", False)
                or plan.refresh_completeness == "requires_resync"
            ):
                candidate.artifact_consumption_state = "stale"
            elif validate_canonical_artifact_consumption_coverage(candidate.artifact_consumption, candidate.artifacts):
                candidate.artifact_consumption_state = "fresh"
            else:
                candidate.artifact_consumption_state = "stale"

            executed_patch_families.append("artifact_consumption")

        elif family == "identity_registry":
            identity_sync_required = True
            executed_patch_families.append("identity_registry")

        elif family == "cached_analytics":
            from contextor.core.reporting_engine.graph_analytics import compute_cached_analytics
            hard_edges = getattr(candidate.dependency_graph, "hard_edges", {}) if candidate.dependency_graph else {}
            candidate.cached_analytics = compute_cached_analytics(
                modules=candidate.modules,
                artifacts=candidate.artifacts,
                artifact_consumption=candidate.artifact_consumption,
                hard_edges=hard_edges,
            )
            executed_patch_families.append("cached_analytics")

        elif family == "collision_facts":
            if delta.is_deleted:
                candidate.collision_facts.pop(delta.module_path, None)
            else:
                if new_collision_facts is None:
                    raise ValueError(
                        f"Planned collision_facts patch for '{delta.module_path}' requires non-None new_collision_facts."
                    )
                candidate.collision_facts[delta.module_path] = new_collision_facts
            executed_patch_families.append("collision_facts")

        elif family == "collisions":
            from contextor.core.analysis.incremental.materialization import _validate_collision_facts_dict
            from contextor.core.validator.collisions import (
                compute_collisions_from_facts,
                resolve_collision_candidate_codes,
            )

            if candidate.collisions_state == "stale":
                pass
            elif _validate_collision_facts_dict(candidate.collision_facts, candidate.modules):
                try:
                    resolved_facts = resolve_collision_candidate_codes(
                        candidate.collision_facts,
                        candidate.modules,
                    )
                    candidate.collision_facts = resolved_facts
                    computed = compute_collisions_from_facts(candidate.collision_facts)
                    candidate.collisions = computed
                    candidate.collisions_state = "fresh"
                except Exception:
                    candidate.collisions_state = "deferred"
            else:
                candidate.collisions_state = "deferred"
            executed_patch_families.append("collisions")

        else:
            raise ValueError(f"Unsupported patch family: {family}")

    # 5. GRAPH - execute graph-only computations
    executed_graph_recomputations: List[str] = []
    affected_set: Set[str] = set()
    blast_radius_complete = False

    for graph_item in plan.graph_recomputations:
        if graph_item == "reverse_blast_radius":
            if delta.is_deleted:
                blast_radius_complete = old_graph is not None
            elif delta.is_new:
                blast_radius_complete = candidate.dependency_graph is not None
            else:
                blast_radius_complete = old_graph is not None and candidate.dependency_graph is not None

            affected_set = (
                calculate_affected_set(
                    delta.module_path,
                    old_graph=old_graph,
                    new_graph=candidate.dependency_graph,
                )
                if blast_radius_complete
                else set()
            )
            executed_graph_recomputations.append("reverse_blast_radius")

        elif graph_item == "macro_metrics":
            if candidate.dependency_graph is not None:
                from contextor.core.graph.metrics import compute_graph_metrics
                candidate.metrics = compute_graph_metrics(
                    candidate.dependency_graph.hard_edges,
                    candidate.dependency_graph.soft_edges,
                )
            executed_graph_recomputations.append("macro_metrics")

        elif graph_item == "advanced_graph_metrics":
            if candidate.dependency_graph is not None:
                from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics
                candidate.topology_analytics = compute_topology_analytics(
                    candidate.dependency_graph.hard_edges,
                    candidate.dependency_graph.soft_edges,
                    candidate.metrics,
                )
            executed_graph_recomputations.append("advanced_graph_metrics")

        elif graph_item == "cycles":
            if candidate.dependency_graph is not None:
                from contextor.core.graph.cycles import detect_cycles
                hard_edges = getattr(candidate.dependency_graph, "hard_edges", {}) or {}
                candidate.cycles = detect_cycles(hard_edges)
            executed_graph_recomputations.append("cycles")

        else:
            raise ValueError(f"Unsupported graph recomputation: {graph_item}")

    # 6. FRESHNESS ASSIGNMENT
    if plan.refresh_completeness == "requires_resync" or getattr(state, "resync_required", False):
        candidate.topology_metrics_state = "stale"
        candidate.cached_analytics_state = "stale"
        candidate.cycles_state = "stale"
        candidate.collisions_state = "stale"
        candidate.artifact_consumption_state = "stale"
    else:
        if "advanced_graph_metrics" in plan.graph_recomputations:
            candidate.topology_metrics_state = "fresh"
        if "cached_analytics" in plan.patch_families:
            candidate.cached_analytics_state = "fresh"
        if "cycles" in plan.graph_recomputations:
            candidate.cycles_state = "fresh"

    derived_artifact_projection = None
    derived_artifact_projection_failed = False
    if (
        (matrix_inputs_changed or cluster_inputs_changed)
        and plan.refresh_completeness != "requires_resync"
        and not getattr(state, "resync_required", False)
    ):
        from contextor.core.analysis.state_manager import artifact_consumption_is_fresh
        if artifact_consumption_is_fresh(candidate):
            from contextor.core.reporting_engine.graph_analytics import build_artifact_data_projection
            try:
                derived_artifact_projection = build_artifact_data_projection(
                    artifacts=candidate.artifacts,
                    artifact_consumption=candidate.artifact_consumption,
                )
            except Exception:
                derived_artifact_projection_failed = True

    if plan.refresh_completeness == "requires_resync" or getattr(
        state, "resync_required", False
    ):
        candidate.dependency_matrix_state = "stale"
    elif matrix_inputs_changed:
        from contextor.core.analysis.state_manager import (
            dependency_matrix_inputs_are_fresh,
        )

        if not dependency_matrix_inputs_are_fresh(candidate) or derived_artifact_projection_failed:
            candidate.dependency_matrix_state = "stale"
        else:
            from contextor.core.reporting_engine.graph_analytics import (
                build_module_dependency_matrix,
            )

            try:
                hard_edges = (
                    getattr(candidate.dependency_graph, "hard_edges", {}) or {}
                    if candidate.dependency_graph is not None
                    else {}
                )
                dependency_matrix = build_module_dependency_matrix(
                    artifact_data=derived_artifact_projection,
                    hard_edges=hard_edges,
                )
            except Exception:
                candidate.dependency_matrix_state = "stale"
            else:
                candidate.dependency_matrix = dependency_matrix
                candidate.dependency_matrix_state = "fresh"

    if plan.refresh_completeness == "requires_resync" or getattr(
        state, "resync_required", False
    ):
        candidate.shared_usage_clusters_state = "stale"
    elif cluster_inputs_changed:
        from contextor.core.analysis.state_manager import (
            artifact_consumption_is_fresh,
        )

        if not artifact_consumption_is_fresh(candidate) or derived_artifact_projection_failed:
            candidate.shared_usage_clusters_state = "stale"
        else:
            from contextor.core.reporting_engine.graph_analytics import (
                build_jaccard_clusters,
            )

            try:
                clusters = build_jaccard_clusters(artifact_data=derived_artifact_projection)
            except Exception:
                candidate.shared_usage_clusters_state = "stale"
            else:
                candidate.shared_usage_clusters = clusters
                candidate.shared_usage_clusters_state = "fresh"

    # 7. PREPARE registry payload if required
    all_modules = set(candidate.modules.keys())
    current_artifacts = collect_qualified_artifact_identities(candidate.artifacts) if identity_sync_required else {}

    execution_trace = {
        "reparse_modules": tuple(executed_reparse),
        "recompute_modules": tuple(executed_recompute),
        "patch_families": tuple(executed_patch_families),
        "graph_recomputations": tuple(executed_graph_recomputations),
    }

    return PlanExecutionOutcome(
        candidate_state=candidate,
        affected_modules=affected_set,
        blast_radius_complete=blast_radius_complete,
        execution_trace=execution_trace,
        identity_sync_required=identity_sync_required,
        all_modules=all_modules,
        current_artifacts=current_artifacts,
    )
