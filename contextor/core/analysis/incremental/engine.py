import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Set, Dict, Iterable, Tuple, Any

from contextor.core.domain.graph import ProjectGraph
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState, FileDelta
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

from contextor.core.analysis.incremental.graph_ops import (
    LocalDegreeDeltaResult,
    calculate_affected_set,
    calculate_degree_deltas,
)
from contextor.core.analysis.incremental.materialization import (
    ensure_module_usages,
    ensure_topology_analytics,
    ensure_cached_analytics,
    ensure_cycles,
    materialize_incremental_state,
)
from contextor.core.analysis.incremental.preparation import (
    extract_artifact_names,
    calculate_file_delta,
    prepare_source_update,
    prepare_deleted_module_update,
)
from contextor.core.analysis.incremental.plan_executor import (
    execute_refresh_plan,
)


@dataclass
class IncrementalUpdateResult:
    """Contract for what the incremental engine returns to MCP/IDE."""
    status: str
    file_path: str
    delta: Optional[FileDelta] = None
    graph_state: str = "stale"
    dependencies_state: str = "stale"
    blast_radius_state: str = "stale"
    local_metrics_state: str = "stale"
    global_metrics_state: str = "stale"
    topology_metrics_state: str = "stale"
    cached_analytics_state: str = "stale"
    cycles_state: str = "stale"
    artifact_consumption_state: str = "stale"

    error: str | None = None
    line_number: int | None = None
    column_number: int | None = None
    affected_modules: list[str] = field(default_factory=list)
    shadow_plan: Optional[Any] = field(default=None, repr=False)
    execution_trace: Optional[Dict[str, Any]] = field(default=None, repr=False)


class IncrementalAnalysisEngine:
    """
    Core engine for handling real-time delta updates to the canonical repository state.
    """
    
    def __init__(
        self, 
        state: RepositoryAnalysisState,
        registry: PersistentIdentityRegistry,
        state_manager: FileStateManager,
        root_path: str
    ):
        self.state = state
        self.registry = registry
        self.state_manager = state_manager
        self.root_path = Path(root_path)
        self._lock = threading.Lock()
        materialize_incremental_state(self.state)

    def _ensure_topology_analytics(self) -> None:
        """Compatibility wrapper delegating to materialization.ensure_topology_analytics."""
        ensure_topology_analytics(self.state)

    def _ensure_cached_analytics(self) -> None:
        """Compatibility wrapper delegating to materialization.ensure_cached_analytics."""
        ensure_cached_analytics(self.state)

    def _ensure_module_usages(self) -> None:
        """Compatibility wrapper delegating to materialization.ensure_module_usages."""
        ensure_module_usages(self.state)

    def _ensure_cycles(self) -> None:
        """Compatibility wrapper delegating to materialization.ensure_cycles."""
        ensure_cycles(self.state)

    def update_file(self, file_path: str) -> IncrementalUpdateResult:
        """
        Updates the canonical state incrementally for a single changed file.
        Returns the update status and the freshness of the architectural model.
        """
        with self._lock:
            if not self.state_manager.has_changed(file_path):
                return IncrementalUpdateResult(
                    status="UNCHANGED",
                    file_path=file_path,
                    graph_state="fresh" if self.state.dependency_graph is not None else "stale",
                    dependencies_state="fresh",
                    blast_radius_state="deferred",
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state=getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred"),
                    cached_analytics_state=getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred"),
                    cycles_state=getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred"),
                    artifact_consumption_state="fresh" if self.state.artifact_consumption is not None else "stale",
                )

            path = Path(file_path)
            rel_path = path.relative_to(self.root_path)
            module_path = ".".join(rel_path.with_suffix("").parts)

            # 1. Handle Deletion
            current_state = self.state_manager.get_current_file_state(file_path, compute_hash=False)
            if not current_state:
                old_module = self.state.modules.get(module_path)
                old_artifacts = self.state.artifacts.get(module_path, {})
                old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
                delta, usage_delta = prepare_deleted_module_update(
                    module_path,
                    old_module=old_module,
                    old_artifacts=old_artifacts,
                    old_usage=old_usage,
                )

                from contextor.core.analysis.refresh_planner import RefreshPlanner
                plan = RefreshPlanner.plan_refresh(delta, usage_delta=usage_delta, module_usages=self.state.module_usages)
                affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                    file_path, delta, usage_delta, plan, [], {}, ModuleUsageFacts()
                )
                blast_radius_state = "fresh" if blast_radius_complete else "deferred"
                affected_modules = sorted(affected_set) if blast_radius_complete else []
                return IncrementalUpdateResult(
                    status="DELETED",
                    file_path=file_path,
                    delta=delta,
                    graph_state="fresh",
                    dependencies_state="fresh",
                    blast_radius_state=blast_radius_state,
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state="fresh",
                    cached_analytics_state="fresh",
                    cycles_state="fresh",
                    artifact_consumption_state="fresh",
                    affected_modules=affected_modules,
                    shadow_plan=plan,
                    execution_trace=execution_trace,
                )

            # 2. Prepare Source Update
            module_id = self.registry.get_module_id(module_path)
            is_new = (module_id is None) or (module_path not in self.state.modules)
            old_module = self.state.modules.get(module_path)
            old_artifacts = self.state.artifacts.get(module_path, {})
            old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()

            prep = prepare_source_update(
                file_path=file_path,
                module_path=module_path,
                is_new=is_new,
                old_module=old_module,
                old_artifacts=old_artifacts,
                old_usage=old_usage,
                persistent_id=module_id,
            )

            if prep.has_error:
                return IncrementalUpdateResult(
                    status=prep.error_status,
                    file_path=file_path,
                    error=prep.error_message,
                    line_number=prep.line_number,
                    column_number=prep.column_number,
                )

            delta = prep.delta
            usage_delta = prep.usage_delta
            new_imports = prep.new_imports
            new_artifacts = prep.new_artifacts
            new_usage = prep.new_usage

            from contextor.core.analysis.refresh_planner import RefreshPlanner
            plan = RefreshPlanner.plan_refresh(delta, usage_delta=usage_delta, module_usages=self.state.module_usages)

            # Check if true no-op
            if plan.is_empty and not is_new and not delta.is_deleted:
                return IncrementalUpdateResult(
                    status="UNCHANGED",
                    file_path=file_path,
                    delta=delta,
                    graph_state="fresh",
                    dependencies_state="fresh",
                    blast_radius_state="deferred",
                    local_metrics_state="deferred",
                    global_metrics_state="deferred",
                    topology_metrics_state=getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred"),
                    cached_analytics_state=getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred"),
                    cycles_state=getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred"),
                    artifact_consumption_state="fresh",
                    affected_modules=[],
                    shadow_plan=plan,
                    execution_trace={
                        "reparse_modules": (),
                        "recompute_modules": (),
                        "patch_families": (),
                        "graph_recomputations": (),
                    },
                )

            # 3. Apply and Commit driven by RefreshPlan
            affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                file_path, delta, usage_delta, plan, new_imports, new_artifacts, new_usage
            )

            if plan.refresh_completeness == "requires_resync":
                graph_state = "stale"
                dependencies_state = "stale"
                blast_radius_state = "deferred"
                topology_metrics_state = "stale"
                cached_analytics_state = "stale"
                cycles_state = "stale"
                artifact_consumption_state = "stale"
            else:
                graph_state = "fresh" if ("dependency_graph" in plan.patch_families or self.state.dependency_graph is not None) else "stale"
                dependencies_state = "fresh"
                blast_radius_state = "fresh" if blast_radius_complete else "deferred"
                if "advanced_graph_metrics" in plan.graph_recomputations:
                    topology_metrics_state = "fresh"
                else:
                    topology_metrics_state = getattr(self.state, "topology_metrics_state", "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred")
                if "cached_analytics" in plan.patch_families:
                    cached_analytics_state = "fresh"
                else:
                    cached_analytics_state = getattr(self.state, "cached_analytics_state", "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred")
                if "cycles" in plan.graph_recomputations:
                    cycles_state = "fresh"
                else:
                    cycles_state = getattr(self.state, "cycles_state", "fresh" if hasattr(self.state, "cycles") else "deferred")
                artifact_consumption_state = "fresh" if ("artifact_consumption" in plan.patch_families or self.state.artifact_consumption is not None) else "stale"

            affected_modules = sorted(affected_set) if blast_radius_complete else []

            return IncrementalUpdateResult(
                status="UPDATED",
                file_path=file_path,
                delta=delta,
                graph_state=graph_state,
                dependencies_state=dependencies_state,
                blast_radius_state=blast_radius_state,
                local_metrics_state="deferred",
                global_metrics_state="deferred",
                topology_metrics_state=topology_metrics_state,
                cached_analytics_state=cached_analytics_state,
                cycles_state=cycles_state,
                artifact_consumption_state=artifact_consumption_state,
                affected_modules=affected_modules,
                shadow_plan=plan,
                execution_trace=execution_trace,
            )

    @staticmethod
    def _artifact_names(artifacts: dict) -> set[str]:
        """Compatibility wrapper delegating to preparation.extract_artifact_names."""
        return extract_artifact_names(artifacts)

    def _calculate_delta(
        self,
        module_path: str,
        persistent_id: Optional[str],
        is_new: bool,
        new_imports: List,
        new_artifacts_dict: dict,
    ) -> FileDelta:
        """Compatibility wrapper delegating to preparation.calculate_file_delta."""
        return calculate_file_delta(
            module_path=module_path,
            persistent_id=persistent_id,
            is_new=is_new,
            old_module=self.state.modules.get(module_path),
            old_artifacts=self.state.artifacts.get(module_path, {}),
            new_imports=new_imports,
            new_artifacts_dict=new_artifacts_dict,
        )

    def _apply_delta_and_commit(
        self,
        file_path: str,
        delta: FileDelta,
        usage_delta: Any,
        plan: Any,
        new_imports: list,
        mod_artifacts: dict,
        new_usage: Any,
    ) -> tuple[Set[str], bool, dict]:
        """
        Executes planned RefreshPlan phases and performs atomic persistent & RAM commit.
        """
        outcome = execute_refresh_plan(
            state=self.state,
            delta=delta,
            usage_delta=usage_delta,
            plan=plan,
            new_imports=new_imports,
            new_artifacts=mod_artifacts,
            new_usage=new_usage,
            root_path=self.root_path,
            file_path=file_path,
        )

        # Persistent Identity Registry Commit
        if outcome.identity_sync_required:
            with self.registry.transaction():
                self.registry.sync_with_workspace(outcome.all_modules, outcome.current_artifacts)

        # Canonical State Publication
        candidate = outcome.candidate_state
        self.state.modules = candidate.modules
        self.state.artifacts = candidate.artifacts
        self.state.dependency_graph = candidate.dependency_graph
        self.state.metrics = candidate.metrics
        self.state.topology_analytics = candidate.topology_analytics
        self.state.cached_analytics = candidate.cached_analytics
        self.state.topology_metrics_state = candidate.topology_metrics_state
        self.state.cached_analytics_state = candidate.cached_analytics_state
        self.state.cycles = candidate.cycles
        self.state.cycles_state = candidate.cycles_state
        self.state.artifact_consumption = candidate.artifact_consumption
        self.state.module_usages = candidate.module_usages
        self.state.trie = candidate.trie
        self.state.package_root = candidate.package_root

        # FileStateManager acknowledgement
        self.state_manager.update_state(file_path)

        return outcome.affected_modules, outcome.blast_radius_complete, outcome.execution_trace

    @staticmethod
    def _calculate_affected_set(
        changed_module: str,
        old_graph: Optional[ProjectGraph] = None,
        new_graph: Optional[ProjectGraph] = None,
    ) -> Set[str]:
        """Compatibility wrapper delegating to graph_ops.calculate_affected_set."""
        return calculate_affected_set(
            changed_module,
            old_graph=old_graph,
            new_graph=new_graph,
        )

    @staticmethod
    def _calculate_degree_deltas(
        old_graph: Optional[ProjectGraph] = None,
        new_graph: Optional[ProjectGraph] = None,
        old_modules: Optional[Iterable[str]] = None,
        new_modules: Optional[Iterable[str]] = None,
    ) -> LocalDegreeDeltaResult:
        """Compatibility wrapper delegating to graph_ops.calculate_degree_deltas."""
        return calculate_degree_deltas(
            old_graph=old_graph,
            new_graph=new_graph,
            old_modules=old_modules,
            new_modules=new_modules,
        )
