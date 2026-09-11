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
    _prepare_candidate_state,
    execute_refresh_plan,
)
from contextor.core.analysis.state_manager import (
    artifact_consumption_is_fresh,
    canonical_python_source_path,
    clear_module_parse_failure,
    mark_module_parse_failure,
    validate_canonical_artifact_consumption_coverage,
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
    collisions_state: str = "stale"
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

    def _ensure_collisions(self) -> None:
        """Compatibility wrapper delegating to materialization.ensure_collisions."""
        ensure_collisions(self.state)

    def _commit_syntax_candidate(
        self,
        *,
        source_path: str,
        syntax_fact: Dict[str, Any] | None = None,
        remove_syntax_fact: bool = False,
        mark_parse_error: tuple[str | None, int | None, int | None] | None = None,
        clear_parse_module: str | None = None,
        degrade_syntax_family: bool = False,
        extracted_lineage_facts: Any | None = None,
        invalidate_lineage: bool = False,
    ) -> None:
        """Commit syntax, parse-freshness, and lineage changes through one COW candidate."""
        candidate = _prepare_candidate_state(self.state)
        if invalidate_lineage:
            candidate.lineage_facts_by_source.pop(source_path, None)
            candidate.lineage_facts_state = "stale"
        elif extracted_lineage_facts is not None:
            with self.registry.read_transaction():
                self._update_candidate_lineage_slice(
                    candidate,
                    source_path=source_path,
                    extracted_lineage_facts=extracted_lineage_facts,
                )
        if remove_syntax_fact:
            candidate.syntax_diagnostics_by_path.pop(source_path, None)
        elif syntax_fact is not None:
            candidate.syntax_diagnostics_by_path[source_path] = syntax_fact
        if degrade_syntax_family and candidate.syntax_diagnostics_state == "fresh":
            candidate.syntax_diagnostics_state = "deferred"
        if mark_parse_error is not None:
            error, line_number, column_number = mark_parse_error
            mark_module_parse_failure(
                candidate,
                clear_parse_module or "",
                error=error,
                line_number=line_number,
                column_number=column_number,
            )
        elif clear_parse_module is not None:
            clear_module_parse_failure(candidate, clear_parse_module)
        self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
        self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
        self.state.module_parse_freshness = candidate.module_parse_freshness
        self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
        self.state.lineage_facts_state = candidate.lineage_facts_state
        self.state.lineage_facts_semantic_version = (
            candidate.lineage_facts_semantic_version
        )

    def _update_candidate_lineage_slice(
        self,
        candidate: Any,
        *,
        source_path: str,
        extracted_lineage_facts: Any | None = None,
        delete: bool = False,
    ) -> None:
        """Install or remove exactly one source-keyed lineage slice on a COW candidate."""
        from contextor.core.analysis.lineage_materialization import (
            LineageResolutionContext,
            materialize_lineage_source_facts,
        )
        from contextor.core.domain.lineage_facts import (
            LINEAGE_FACTS_SEMANTIC_VERSION,
            LineageFamilyStatus,
        )
        from contextor.core.reporting_layer.artifact_usage_report import (
            collect_qualified_artifact_identities,
        )

        eligible_source_keys = {
            Path(str(module.path)).as_posix()
            for module in candidate.modules.values()
        }
        lineage_by_source = candidate.lineage_facts_by_source

        if delete:
            lineage_by_source.pop(source_path, None)
            candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION
        else:
            if extracted_lineage_facts is None:
                raise ValueError("Successful incremental lineage update requires extracted facts.")
            if extracted_lineage_facts.source_key != source_path:
                raise ValueError("Extracted lineage source key does not match incremental source.")
            if source_path not in eligible_source_keys:
                raise ValueError("Incremental lineage source is outside the active candidate.")

            active_module_names = set(candidate.modules)
            active_artifact_names = collect_qualified_artifact_identities(
                candidate.artifacts
            )
            module_registry = self.registry._state["module_registry"]["path_to_id"]
            artifact_registry = self.registry._state["artifact_registry"]["path_to_id"]
            active_module_ids = {
                name: module_registry[name]
                for name in sorted(active_module_names)
                if name in module_registry
            }
            active_artifact_ids = {
                name: artifact_registry[name]
                for name in sorted(active_artifact_names)
                if name in artifact_registry
            }
            missing_module_ids = active_module_names - set(active_module_ids)
            missing_artifact_ids = active_artifact_names - set(active_artifact_ids)
            if missing_module_ids or missing_artifact_ids:
                raise ValueError(
                    "Finalized identity registry is missing active lineage owners: "
                    f"modules={sorted(missing_module_ids)!r}, "
                    f"artifacts={sorted(missing_artifact_ids)!r}"
                )

            resolution = LineageResolutionContext(
                active_module_ids=active_module_ids,
                active_artifact_ids=active_artifact_ids,
                active_owner_ids=frozenset(
                    (*active_module_ids.values(), *active_artifact_ids.values())
                ),
                interface_descriptors={},
            )
            materialized = materialize_lineage_source_facts(
                extracted_lineage_facts,
                resolution,
            )
            if (
                materialized.manifest.source_key != extracted_lineage_facts.source_key
                or materialized.manifest.source_fingerprint
                != extracted_lineage_facts.source_fingerprint
            ):
                raise ValueError(
                    "Materialized lineage manifest does not match extracted source."
                )
            lineage_by_source[source_path] = materialized
            candidate.lineage_facts_semantic_version = LINEAGE_FACTS_SEMANTIC_VERSION

        foreign_source_keys = set(lineage_by_source) - eligible_source_keys
        if foreign_source_keys:
            raise ValueError(
                "Materialized lineage contains sources outside the active candidate: "
                f"{sorted(foreign_source_keys)!r}"
            )
        missing_source_keys = eligible_source_keys - set(lineage_by_source)
        if getattr(self.state, "resync_required", False):
            candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
        elif missing_source_keys:
            candidate.lineage_facts_state = (
                LineageFamilyStatus.STALE.value
                if candidate.lineage_facts_state == LineageFamilyStatus.STALE.value
                else LineageFamilyStatus.DEFERRED.value
            )
        elif any(
            item.manifest.status is LineageFamilyStatus.STALE
            for item in lineage_by_source.values()
        ):
            candidate.lineage_facts_state = LineageFamilyStatus.STALE.value
        elif any(
            item.manifest.status is LineageFamilyStatus.DEFERRED
            for item in lineage_by_source.values()
        ):
            candidate.lineage_facts_state = LineageFamilyStatus.DEFERRED.value
        elif any(
            item.manifest.status is LineageFamilyStatus.RESOURCE_LIMIT
            for item in lineage_by_source.values()
        ):
            candidate.lineage_facts_state = LineageFamilyStatus.RESOURCE_LIMIT.value
        else:
            candidate.lineage_facts_state = LineageFamilyStatus.FRESH.value

    def update_file(self, file_path: str) -> IncrementalUpdateResult:
        """
        Updates the canonical state incrementally for a single changed file.
        Returns the update status and the freshness of the architectural model.
        """
        with self._lock:
            if getattr(self.state, "resync_required", False):
                # Every exit path, including a semantic no-op, must expose the
                # already-lost incremental continuity as fail-closed.
                self.state.artifact_consumption_state = "stale"
            path = Path(file_path)
            rel_path = path.relative_to(self.root_path)
            module_path = ".".join(rel_path.with_suffix("").parts)
            source_path = canonical_python_source_path(rel_path.as_posix())
            if source_path is None:
                raise ValueError(f"Incremental source path is not canonical Python: {file_path}")

            if (
                not self.state_manager.has_changed(file_path)
                and module_path in self.state.modules
            ):
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
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
                )

            # 1. Handle Deletion
            current_state = self.state_manager.get_current_file_state(file_path, compute_hash=False)
            if not current_state:
                old_module = self.state.modules.get(module_path)
                old_artifacts = self.state.artifacts.get(module_path, {})
                old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
                old_collision_facts = self.state.collision_facts.get(module_path) if hasattr(self.state, "collision_facts") and self.state.collision_facts else None
                delta, usage_delta, collision_facts_changed = prepare_deleted_module_update(
                    module_path,
                    old_module=old_module,
                    old_artifacts=old_artifacts,
                    old_usage=old_usage,
                    old_collision_facts=old_collision_facts,
                )

                from contextor.core.analysis.refresh_planner import RefreshPlanner
                plan = RefreshPlanner.plan_refresh(
                    delta,
                    usage_delta=usage_delta,
                    module_usages=self.state.module_usages,
                    collision_facts_changed=collision_facts_changed,
                )
                affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                    file_path, delta, usage_delta, plan, [], {}, ModuleUsageFacts(),
                    new_collision_facts=None,
                    syntax_source_path=source_path,
                    remove_syntax_fact=True,
                    clear_parse_module=module_path,
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
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
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
            old_collision_facts = self.state.collision_facts.get(module_path) if hasattr(self.state, "collision_facts") and self.state.collision_facts else None

            prep = prepare_source_update(
                file_path=file_path,
                module_path=module_path,
                is_new=is_new,
                old_module=old_module,
                old_artifacts=old_artifacts,
                old_usage=old_usage,
                persistent_id=module_id,
                old_collision_facts=old_collision_facts,
                source_key=source_path,
            )

            if prep.has_error:
                syntax_fact = (
                    {
                        "status": "checked_with_errors",
                        "errors": [{
                            "message": prep.error_message,
                            "line_number": prep.line_number,
                            "column_number": prep.column_number,
                        }],
                    }
                    if prep.error_status == "SYNTAX_ERROR"
                    else None
                )
                self._commit_syntax_candidate(
                    source_path=source_path,
                    syntax_fact=syntax_fact,
                    mark_parse_error=(
                        prep.error_message,
                        prep.line_number,
                        prep.column_number,
                    ),
                    clear_parse_module=module_path,
                    degrade_syntax_family=prep.error_status != "SYNTAX_ERROR",
                    invalidate_lineage=True,
                )
                return IncrementalUpdateResult(
                    status=prep.error_status,
                    file_path=file_path,
                    error=prep.error_message,
                    line_number=prep.line_number,
                    column_number=prep.column_number,
                )

            freshness = getattr(self.state, "module_parse_freshness", {}) or {}
            recovered_from_parse_failure = (
                isinstance(freshness.get(module_path), dict)
                and freshness[module_path].get("state") == "stale"
            )
            checked_and_none = {"status": "checked_and_none", "errors": []}

            delta = prep.delta
            usage_delta = prep.usage_delta
            new_imports = prep.new_imports
            new_artifacts = prep.new_artifacts
            new_usage = prep.new_usage
            new_collision_facts = prep.new_collision_facts

            from contextor.core.analysis.refresh_planner import RefreshPlanner
            plan = RefreshPlanner.plan_refresh(
                delta,
                usage_delta=usage_delta,
                module_usages=self.state.module_usages,
                collision_facts_changed=prep.collision_facts_changed,
            )

            # Check if true no-op
            if plan.is_empty and not is_new and not delta.is_deleted:
                # Parsing proved the tracked source is semantically unchanged.
                # Acknowledge its current fingerprint so restart reconciliation
                # does not repeatedly queue the same canonical module.
                self._commit_syntax_candidate(
                    source_path=source_path,
                    syntax_fact=checked_and_none,
                    clear_parse_module=module_path,
                    extracted_lineage_facts=prep.extracted_lineage_facts,
                )
                self.state_manager.update_state(file_path)
                return IncrementalUpdateResult(
                    status="RECOVERED" if recovered_from_parse_failure else "UNCHANGED",
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
                    collisions_state=getattr(self.state, "collisions_state", "deferred"),
                    artifact_consumption_state="fresh" if artifact_consumption_is_fresh(self.state) else "stale",
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
                file_path, delta, usage_delta, plan, new_imports, new_artifacts, new_usage,
                new_collision_facts=new_collision_facts,
                extracted_lineage_facts=prep.extracted_lineage_facts,
                syntax_source_path=source_path,
                syntax_fact=checked_and_none,
                clear_parse_module=module_path,
            )

            if plan.refresh_completeness == "requires_resync":
                graph_state = "stale"
                dependencies_state = "stale"
                blast_radius_state = "deferred"
                topology_metrics_state = "stale"
                cached_analytics_state = "stale"
                cycles_state = "stale"
                collisions_state = "stale"
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
                collisions_state = getattr(self.state, "collisions_state", "deferred")
                artifact_consumption_state = "fresh" if artifact_consumption_is_fresh(self.state) else "stale"

            affected_modules = sorted(affected_set) if blast_radius_complete else []

            return IncrementalUpdateResult(
                status="RECOVERED" if recovered_from_parse_failure else "UPDATED",
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
                collisions_state=collisions_state,
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
        new_collision_facts: Optional[List[Dict[str, Any]]] = None,
        extracted_lineage_facts: Any | None = None,
        syntax_source_path: str | None = None,
        syntax_fact: Dict[str, Any] | None = None,
        remove_syntax_fact: bool = False,
        clear_parse_module: str | None = None,
    ) -> tuple[Set[str], bool, dict]:
        """
        Executes planned RefreshPlan phases and performs atomic persistent & RAM commit.
        """
        resync_required = bool(getattr(self.state, "resync_required", False))
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
            new_collision_facts=new_collision_facts,
        )

        candidate = outcome.candidate_state

        # Persistent identity sync and lineage materialization share one registry view.
        if outcome.identity_sync_required:
            try:
                with self.registry.transaction():
                    self.registry.sync_with_workspace(
                        outcome.all_modules,
                        outcome.current_artifacts,
                    )
                    self._update_candidate_lineage_slice(
                        candidate,
                        source_path=syntax_source_path or "",
                        extracted_lineage_facts=extracted_lineage_facts,
                        delete=bool(getattr(delta, "is_deleted", False)),
                    )
            except Exception:
                # A failed write transaction leaves no persisted commit; reload its
                # in-memory view before exposing the registry again.
                with self.registry.read_transaction():
                    pass
                raise
        elif extracted_lineage_facts is not None or bool(
            getattr(delta, "is_deleted", False)
        ):
            with self.registry.read_transaction():
                self._update_candidate_lineage_slice(
                    candidate,
                    source_path=syntax_source_path or "",
                    extracted_lineage_facts=extracted_lineage_facts,
                    delete=bool(getattr(delta, "is_deleted", False)),
                )

        # Canonical State Publication
        if remove_syntax_fact and syntax_source_path is not None:
            candidate.syntax_diagnostics_by_path.pop(syntax_source_path, None)
        elif syntax_fact is not None and syntax_source_path is not None:
            candidate.syntax_diagnostics_by_path[syntax_source_path] = syntax_fact
        if clear_parse_module is not None:
            clear_module_parse_failure(candidate, clear_parse_module)
        self.state.modules = candidate.modules
        self.state.artifacts = candidate.artifacts
        self.state.module_parse_freshness = candidate.module_parse_freshness
        self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
        self.state.syntax_diagnostics_state = candidate.syntax_diagnostics_state
        self.state.dependency_graph = candidate.dependency_graph
        self.state.metrics = candidate.metrics
        self.state.topology_analytics = candidate.topology_analytics
        self.state.cached_analytics = candidate.cached_analytics
        self.state.dependency_matrix = candidate.dependency_matrix
        self.state.dependency_matrix_state = candidate.dependency_matrix_state
        self.state.shared_usage_clusters = candidate.shared_usage_clusters
        self.state.shared_usage_clusters_state = candidate.shared_usage_clusters_state
        self.state.topology_metrics_state = candidate.topology_metrics_state
        self.state.cached_analytics_state = candidate.cached_analytics_state
        self.state.cycles = candidate.cycles
        self.state.cycles_state = candidate.cycles_state
        self.state.collision_facts = candidate.collision_facts
        self.state.collisions = candidate.collisions
        self.state.collisions_state = candidate.collisions_state
        self.state.artifact_consumption = candidate.artifact_consumption
        if (
            candidate.artifact_consumption_state != "stale"
            and not resync_required
            and validate_canonical_artifact_consumption_coverage(candidate.artifact_consumption, candidate.artifacts)
        ):
            self.state.artifact_consumption_state = "fresh"
        else:
            self.state.artifact_consumption_state = "stale"
        if resync_required:
            # A lost incremental continuity is authoritative until a full
            # rebuild replaces this state; an incremental candidate cannot
            # certify it fresh again.
            self.state.resync_required = True
        self.state.module_usages = candidate.module_usages
        self.state.lineage_facts_by_source = candidate.lineage_facts_by_source
        self.state.lineage_facts_state = candidate.lineage_facts_state
        self.state.lineage_facts_semantic_version = (
            candidate.lineage_facts_semantic_version
        )
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
