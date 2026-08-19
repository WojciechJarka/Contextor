"""
contextor/core/analysis/incremental/plan_executor.py

RefreshPlan execution pipeline for incremental updates:
- CandidateState Copy-on-Write container
- PlanExecutionOutcome immutable result contract
- Execution phases: REPARSE, RECOMPUTE, PATCH, GRAPH
- Fail-closed patch family and graph recomputation dispatch
- Complete isolation from disk I/O and threading locks
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Set, Dict, Tuple, Any, Mapping

from contextor.core.analysis.incremental.graph_ops import calculate_affected_set
from contextor.core.analysis.state_manager import FileDelta, RepositoryAnalysisState
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.graph.graph import build_trie, detect_package_root, build_graph, resolve_module_edges
from contextor.core.reference.engine import _build_reexport_map
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
    artifacts: Dict[str, Any]
    module_usages: Dict[str, Any]
    artifact_consumption: Dict[str, Any]
    dependency_graph: Optional[ProjectGraph]
    trie: Any
    package_root: Any
    metrics: Any
    topology_analytics: Dict[str, Any]
    cached_analytics: Dict[str, Any]
    topology_metrics_state: str
    cached_analytics_state: str
    cycles: list
    cycles_state: str
    collision_facts: Dict[str, list]
    collisions: list
    collisions_state: str


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


def _is_valid_target(t: str, candidate_modules: Mapping[str, Any]) -> bool:
    """Validates whether a target symbol/module belongs to known candidate modules."""
    if not t:
        return False
    mod_prefix = t.rsplit(".", 1)[0] if "." in t else t
    top_prefix = t.split(".")[0] if "." in t else t
    return mod_prefix in candidate_modules or top_prefix in candidate_modules or t in candidate_modules


def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
    """Initializes Copy-on-Write candidate state from current canonical state."""
    return CandidateState(
        modules=dict(state.modules),
        artifacts=dict(state.artifacts),
        module_usages=dict(getattr(state, "module_usages", {}) or {}),
        artifact_consumption=dict(state.artifact_consumption or {}),
        dependency_graph=state.dependency_graph,
        trie=state.trie,
        package_root=state.package_root,
        metrics=state.metrics,
        topology_analytics=dict(getattr(state, "topology_analytics", {}) or {}),
        cached_analytics=dict(getattr(state, "cached_analytics", {}) or {}),
        topology_metrics_state=getattr(state, "topology_metrics_state", "deferred"),
        cached_analytics_state=getattr(state, "cached_analytics_state", "deferred"),
        cycles=list(getattr(state, "cycles", []) or []),
        cycles_state=getattr(state, "cycles_state", "deferred"),
        collision_facts=dict(getattr(state, "collision_facts", {}) or {}),
        collisions=list(getattr(state, "collisions", []) or []),
        collisions_state=getattr(state, "collisions_state", "deferred"),
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
) -> PlanExecutionOutcome:
    """
    Executes the phases of a RefreshPlan (REPARSE, RECOMPUTE, PATCH, GRAPH)
    on an isolated Copy-on-Write candidate state without performing disk I/O or state mutation.
    """
    path = Path(file_path)
    mod_id = Path(delta.module_path).stem if delta.module_path.endswith(".py") else delta.module_path
    old_graph = state.dependency_graph

    # 1. PREPARE candidate state
    candidate = _prepare_candidate_state(state)

    # Pre-populate candidate module in candidate.modules so RECOMPUTE re-export resolution
    # observes the updated module structure before PATCH
    if delta.is_deleted:
        candidate.modules.pop(mod_id, None)
        candidate.modules.pop(delta.module_path, None)
    elif "modules" in plan.patch_families:
        candidate.modules[delta.module_path] = Module(
            module_id=delta.module_path,
            path=str(path.relative_to(root_path)),
            absolute_path=str(path.resolve()),
            imports=new_imports or [],
        )

    # 2. REPARSE - record planned reparse modules (trace-only, no secondary source I/O)
    executed_reparse: List[str] = []
    for reparse_mod in plan.reparse_modules:
        executed_reparse.append(reparse_mod)

    # 3. RECOMPUTE - re-evaluate planned cached modules in RAM without source I/O
    executed_recompute: List[str] = []
    if plan.recompute_modules:
        old_reexports = _build_reexport_map(state.modules)
        new_reexports = _build_reexport_map(candidate.modules)
        for consumer_path in plan.recompute_modules:
            consumer_facts = candidate.module_usages.get(consumer_path)
            if consumer_facts:
                c_aliases = dict(consumer_facts.aliases)
                for call in (consumer_facts.direct_calls + consumer_facts.qualified_refs):
                    old_t = _resolve_reexport(_resolve_alias(call, c_aliases), old_reexports)
                    new_t = _resolve_reexport(_resolve_alias(call, c_aliases), new_reexports)
                    if old_t and old_t != new_t and old_t in candidate.artifact_consumption:
                        entry = _get_copy_of_entry(candidate.artifact_consumption[old_t])
                        if consumer_path in entry["consumers"]:
                            entry["consumers"].remove(consumer_path)
                        entry["channels"].pop(consumer_path, None)
                        entry["consumers"] = sorted(set(entry["consumers"]))
                        candidate.artifact_consumption[old_t] = entry
                    if new_t and _is_valid_target(new_t, candidate.modules):
                        entry = _get_copy_of_entry(candidate.artifact_consumption.get(new_t, {}))
                        if consumer_path not in entry["consumers"]:
                            entry["consumers"].append(consumer_path)
                        entry["consumers"] = sorted(set(entry["consumers"]))
                        ch_list = set(entry["channels"].get(consumer_path, ["direct_calls"]))
                        entry["channels"][consumer_path] = sorted(ch_list)
                        candidate.artifact_consumption[new_t] = entry
                executed_recompute.append(consumer_path)

    # 4. PATCH - apply fact families listed in plan.patch_families
    executed_patch_families: List[str] = []
    identity_sync_required = False

    for family in plan.patch_families:
        if family == "modules":
            if delta.is_deleted:
                candidate.modules.pop(mod_id, None)
                candidate.modules.pop(delta.module_path, None)
            else:
                candidate.modules[delta.module_path] = Module(
                    module_id=delta.module_path,
                    path=str(path.relative_to(root_path)),
                    absolute_path=str(path.resolve()),
                    imports=new_imports or [],
                )
            executed_patch_families.append("modules")

        elif family == "definitions":
            if delta.is_deleted:
                candidate.artifacts.pop(mod_id, None)
                candidate.artifacts.pop(delta.module_path, None)
            else:
                candidate.artifacts[delta.module_path] = new_artifacts or {}
            executed_patch_families.append("definitions")

        elif family == "module_usages":
            if delta.is_deleted:
                candidate.module_usages.pop(delta.module_path, None)
            else:
                candidate.module_usages[delta.module_path] = new_usage or ModuleUsageFacts()
            executed_patch_families.append("module_usages")

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
                for art_key in list(candidate.artifact_consumption.keys()):
                    if (
                        art_key == mod_id
                        or art_key == delta.module_path
                        or art_key.startswith(mod_id + ".")
                        or art_key.startswith(delta.module_path + ".")
                    ):
                        candidate.artifact_consumption.pop(art_key, None)

            reexports = _build_reexport_map(candidate.modules)

            # Unregister removed usages
            old_mod_usage = getattr(state, "module_usages", {}).get(delta.module_path, ModuleUsageFacts()) if hasattr(state, "module_usages") and state.module_usages else ModuleUsageFacts()
            old_aliases = dict(old_mod_usage.aliases)
            rem_tagged = (
                [(sym, "direct_calls") for sym in usage_delta.removed_direct_calls] +
                [(sym, "runtime_calls") for sym in usage_delta.removed_runtime_calls] +
                [(sym, "qualified_refs") for sym in usage_delta.removed_qualified_refs] +
                [(sym, "callback_calls") for sym in usage_delta.removed_callback_calls] +
                [(sym, "event_bindings") for sym in usage_delta.removed_event_bindings] +
                [(sym, "api_imports") for sym in usage_delta.removed_imports] +
                [(item[1], "inheritance") for item in usage_delta.removed_inheritance_refs if len(item) >= 2 and item[1]]
            )
            for rem_symbol, ch_name in rem_tagged:
                target = _resolve_reexport(_resolve_alias(rem_symbol, old_aliases), reexports)
                if target and target in candidate.artifact_consumption:
                    entry = _get_copy_of_entry(candidate.artifact_consumption[target])
                    ch_list = entry["channels"].get(delta.module_path, [])
                    if ch_name in ch_list:
                        ch_list.remove(ch_name)
                    if ch_list:
                        entry["channels"][delta.module_path] = sorted(set(ch_list))
                    else:
                        entry["channels"].pop(delta.module_path, None)
                        if delta.module_path in entry["consumers"]:
                            entry["consumers"].remove(delta.module_path)
                    entry["consumers"] = sorted(set(entry["consumers"]))
                    candidate.artifact_consumption[target] = entry

            # Register current usages
            if new_usage:
                new_aliases = dict(new_usage.aliases)
                cur_tagged = (
                    [(sym, "direct_calls") for sym in new_usage.direct_calls] +
                    [(sym, "runtime_calls") for sym in new_usage.runtime_calls] +
                    [(sym, "qualified_refs") for sym in new_usage.qualified_refs] +
                    [(sym, "callback_calls") for sym in new_usage.callback_calls] +
                    [(sym, "event_bindings") for sym in new_usage.event_bindings] +
                    [(sym, "api_imports") for sym in new_usage.imports] +
                    [(item[1], "inheritance") for item in new_usage.inheritance_refs if len(item) >= 2 and item[1]]
                )
                for add_symbol, ch_name in cur_tagged:
                    target = _resolve_reexport(_resolve_alias(add_symbol, new_aliases), reexports)
                    if target and _is_valid_target(target, candidate.modules):
                        entry = _get_copy_of_entry(candidate.artifact_consumption.get(target, {}))
                        if delta.module_path not in entry["consumers"]:
                            entry["consumers"].append(delta.module_path)
                        entry["consumers"] = sorted(set(entry["consumers"]))
                        ch_list = set(entry["channels"].get(delta.module_path, []))
                        ch_list.add(ch_name)
                        entry["channels"][delta.module_path] = sorted(ch_list)
                        candidate.artifact_consumption[target] = entry

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
            from contextor.core.validator.collisions import compute_collisions_from_facts

            if candidate.collisions_state == "stale":
                pass
            elif _validate_collision_facts_dict(candidate.collision_facts, candidate.modules):
                try:
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
    if plan.refresh_completeness == "requires_resync":
        candidate.topology_metrics_state = "stale"
        candidate.cached_analytics_state = "stale"
        candidate.cycles_state = "stale"
        candidate.collisions_state = "stale"
    else:
        if "advanced_graph_metrics" in plan.graph_recomputations:
            candidate.topology_metrics_state = "fresh"
        if "cached_analytics" in plan.patch_families:
            candidate.cached_analytics_state = "fresh"
        if "cycles" in plan.graph_recomputations:
            candidate.cycles_state = "fresh"

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
