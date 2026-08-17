import ast
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Set, Dict, Iterable, Tuple, Any



from contextor.core.domain.graph import ProjectGraph

from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState, FileDelta
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.symbol_engine.indexer import read_imports


@dataclass(frozen=True)
class LocalDegreeDeltaResult:
    """Represents exact local graph degree updates derived from an OLD->NEW hard-edge graph delta."""
    complete: bool
    fan_in_updates: Dict[str, int] = field(default_factory=dict)
    fan_out_updates: Dict[str, int] = field(default_factory=dict)
    added_modules: Set[str] = field(default_factory=set)
    removed_modules: Set[str] = field(default_factory=set)


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
        self._ensure_module_usages()
        self._ensure_topology_analytics()
        self._ensure_cached_analytics()

    def _ensure_topology_analytics(self):
        """Materializes state.topology_analytics from canonical graph if missing/empty and not stale."""
        if not hasattr(self.state, "topology_metrics_state") or self.state.topology_metrics_state is None:
            self.state.topology_metrics_state = "fresh" if bool(getattr(self.state, "topology_analytics", None)) else "deferred"

        if not hasattr(self.state, "topology_analytics") or self.state.topology_analytics is None:
            self.state.topology_analytics = {}

        if self.state.topology_metrics_state != "stale" and not self.state.topology_analytics and getattr(self.state, "dependency_graph", None) is not None:
            from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics
            self.state.topology_analytics = compute_topology_analytics(
                self.state.dependency_graph.hard_edges,
                self.state.dependency_graph.soft_edges,
                self.state.metrics,
            )
            self.state.topology_metrics_state = "fresh"

    def _ensure_cached_analytics(self):
        """Materializes state.cached_analytics from canonical facts if missing/empty and not stale."""
        if not hasattr(self.state, "cached_analytics_state") or self.state.cached_analytics_state is None:
            self.state.cached_analytics_state = "fresh" if bool(getattr(self.state, "cached_analytics", None)) else "deferred"

        if not hasattr(self.state, "cached_analytics") or self.state.cached_analytics is None:
            self.state.cached_analytics = {}

        if self.state.cached_analytics_state != "stale" and not self.state.cached_analytics and getattr(self.state, "modules", None):
            from contextor.core.reporting_engine.graph_analytics import compute_cached_analytics
            hard_edges = getattr(self.state.dependency_graph, "hard_edges", {}) if self.state.dependency_graph else {}
            self.state.cached_analytics = compute_cached_analytics(
                modules=self.state.modules,
                artifacts=getattr(self.state, "artifacts", {}),
                artifact_consumption=getattr(self.state, "artifact_consumption", {}),
                hard_edges=hard_edges,
            )
            self.state.cached_analytics_state = "fresh"


    def _ensure_module_usages(self):

        """Initializes state.module_usages for pre-existing state.modules if missing."""
        if not hasattr(self.state, "module_usages") or self.state.module_usages is None:
            self.state.module_usages = {}

        missing_modules = set(self.state.modules.keys()) - set(self.state.module_usages.keys())
        if missing_modules:
            from contextor.core.reference.engine import extract_module_usage_facts
            for mod_path in missing_modules:
                mod = self.state.modules[mod_path]
                mod_abs = getattr(mod, "absolute_path", None) or getattr(mod, "path", None)
                source_text = None
                if mod_abs and Path(mod_abs).exists():
                    try:
                        source_text = Path(mod_abs).read_text(encoding="utf-8")
                    except OSError:
                        source_text = None
                imports = getattr(mod, "imports", [])
                self.state.module_usages[mod_path] = extract_module_usage_facts(
                    mod_path,
                    source_text,
                    imports=imports,
                )


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
                    artifact_consumption_state="fresh" if self.state.artifact_consumption is not None else "stale",
                )




                
            path = Path(file_path)
            rel_path = path.relative_to(self.root_path)
            module_path = ".".join(rel_path.with_suffix("").parts)
            
            # 1. Handle Deletion
            current_state = self.state_manager.get_current_file_state(file_path, compute_hash=False)
            if not current_state:
                old_artifacts = self.state.artifacts.get(module_path, {})
                old_module = self.state.modules.get(module_path)
                delta = FileDelta(
                    module_path=module_path,
                    is_deleted=True,
                    imports_removed=sorted(
                        {
                            imp.module
                            for imp in (old_module.imports if old_module else [])
                            if imp.module
                        }
                    ),
                    artifacts_removed=sorted(self._artifact_names(old_artifacts)),
                )
                from contextor.core.domain.usage_facts import ModuleUsageFacts, diff_usage_facts
                old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
                usage_delta = diff_usage_facts(module_path, old_usage, ModuleUsageFacts())

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
                    artifact_consumption_state="fresh",
                    affected_modules=affected_modules,
                    shadow_plan=plan,
                    execution_trace=execution_trace,
                )



            # 2. Parse new file
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                return IncrementalUpdateResult(
                    status="SYNTAX_ERROR",
                    file_path=file_path,
                    error=exc.msg,
                    line_number=exc.lineno,
                    column_number=exc.offset,
                )
            except OSError as exc:
                return IncrementalUpdateResult(
                    status="ERROR", file_path=file_path, error=str(exc)
                )
            try:
                new_imports, error = read_imports(path)
                if error:
                    return IncrementalUpdateResult(
                        status="SYNTAX_ERROR", file_path=file_path, error=str(error)
                    )
            except Exception as exc:
                return IncrementalUpdateResult(
                    status="ERROR", file_path=file_path, error=str(exc)
                )

            # 3. Parse new artifacts
            from contextor.core.reporting_layer.artifact_usage_report import extract_file_symbols, _module_own_symbols
            try:
                raw_symbols = extract_file_symbols(str(path))
                own_symbols = _module_own_symbols(raw_symbols)
                old_artifacts = self.state.artifacts.get(module_path, {})
                old_consumers = old_artifacts.get("consumers", {})
                new_artifacts = {
                    "symbols": raw_symbols,
                    "own_symbols": own_symbols,
                    "consumers": old_consumers
                }
            except Exception:
                old_artifacts = self.state.artifacts.get(module_path, {})
                old_consumers = old_artifacts.get("consumers", {})
                new_artifacts = {"symbols": {}, "own_symbols": set(), "consumers": old_consumers}
                raw_symbols = {}
            
            # 4. Calculate FileDelta & UsageDelta
            module_id = self.registry.get_module_id(module_path)
            is_new = (module_id is None) or (module_path not in self.state.modules)
            delta = self._calculate_delta(module_path, module_id, is_new, new_imports, new_artifacts)


            source_text = None
            if path.exists():
                try:
                    source_text = path.read_text(encoding="utf-8")
                except OSError:
                    source_text = None
            from contextor.core.reference.engine import extract_module_usage_facts
            from contextor.core.domain.usage_facts import ModuleUsageFacts, diff_usage_facts
            new_usage = extract_module_usage_facts(
                module_path,
                source_text,
                imports=new_imports,
            )
            old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
            usage_delta = diff_usage_facts(module_path, old_usage, new_usage)
            
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




            # 5. Apply and Commit driven by RefreshPlan
            affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                file_path, delta, usage_delta, plan, new_imports, new_artifacts, new_usage
            )
            
            if plan.refresh_completeness == "requires_resync":
                graph_state = "stale"
                dependencies_state = "stale"
                blast_radius_state = "deferred"
                topology_metrics_state = "stale"
                cached_analytics_state = "stale"
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
                artifact_consumption_state=artifact_consumption_state,
                affected_modules=affected_modules,
                shadow_plan=plan,
                execution_trace=execution_trace,
            )



            
    @staticmethod
    def _artifact_names(artifacts: dict) -> set[str]:
        """Return definition artifacts represented in one module snapshot."""

        symbols = artifacts.get("symbols", {}) if artifacts else {}
        return {
            str(name)
            for category in ("functions", "classes", "methods")
            for name in symbols.get(category, [])
        }

    def _calculate_delta(self, module_path: str, persistent_id: Optional[str], is_new: bool, new_imports: List, new_artifacts_dict: dict) -> FileDelta:
        delta = FileDelta(
            module_path=module_path,
            is_new=is_new
        )
        
        if is_new or persistent_id is None or module_path not in self.state.modules:
            delta.is_new = True
            delta.imports_added = sorted(
                {imp.module for imp in (new_imports or []) if imp.module}
            )
            delta.artifacts_added = sorted(self._artifact_names(new_artifacts_dict))
            return delta

            
        old_module = self.state.modules.get(module_path)
        old_imports = old_module.imports if old_module else []
        
        old_import_names = {imp.module for imp in old_imports if imp.module}
        new_import_names = {imp.module for imp in (new_imports or []) if imp.module}
        
        delta.imports_added = sorted(new_import_names - old_import_names)
        delta.imports_removed = sorted(old_import_names - new_import_names)
        
        new_artifact_names = self._artifact_names(new_artifacts_dict)
        old_artifacts = self.state.artifacts.get(module_path, {})
        old_artifact_names = self._artifact_names(old_artifacts)
                             
        delta.artifacts_added = sorted(new_artifact_names - old_artifact_names)
        delta.artifacts_removed = sorted(old_artifact_names - new_artifact_names)
        
        return delta

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
        Executes explicit RefreshPlan phases:
        REPARSE -> RECOMPUTE -> PATCH -> GRAPH -> COMMIT
        """
        path = Path(file_path)
        executed_reparse = []
        executed_recompute = []
        executed_patch_families = []
        executed_graph_recomputations = []
        
        # A. PREPARE - shallow copy state for Copy-On-Write isolation
        new_modules = dict(self.state.modules)
        new_artifacts = dict(self.state.artifacts)
        new_module_usages = dict(getattr(self.state, "module_usages", {}))
        new_artifact_consumption = dict(self.state.artifact_consumption or {})
        old_graph = self.state.dependency_graph
        new_graph = self.state.dependency_graph
        new_trie = self.state.trie
        new_package_root = self.state.package_root
        new_metrics = self.state.metrics
        new_topology_analytics = dict(getattr(self.state, "topology_analytics", {}) or {})
        new_cached_analytics = dict(getattr(self.state, "cached_analytics", {}) or {})
        affected_set = set()
        blast_radius_complete = False


        
        mod_id = Path(delta.module_path).stem if delta.module_path.endswith(".py") else delta.module_path

        # B. REPARSE - parse only additional modules planned
        for reparse_mod in plan.reparse_modules:
            executed_reparse.append(reparse_mod)

        # C. RECOMPUTE - reevaluate planned cached modules in RAM without source I/O
        from contextor.core.reference.engine import _build_reexport_map
        from contextor.core.reference.resolution import _resolve_alias, _resolve_reexport

        def _get_copy_of_entry(raw_entry: dict) -> dict:
            consumers = list(raw_entry.get("consumers", []))
            channels = {
                k: list(v)
                for k, v in raw_entry.get("channels", {}).items()
            }
            return {"consumers": consumers, "channels": channels}

        def _is_valid_target(t: str) -> bool:
            if not t:
                return False
            mod_prefix = t.rsplit(".", 1)[0] if "." in t else t
            top_prefix = t.split(".")[0] if "." in t else t
            return mod_prefix in new_modules or top_prefix in new_modules or t in new_modules

        if plan.recompute_modules:
            old_reexports = _build_reexport_map(self.state.modules)
            new_reexports = _build_reexport_map(new_modules)
            for consumer_path in plan.recompute_modules:
                consumer_facts = new_module_usages.get(consumer_path)
                if consumer_facts:
                    c_aliases = dict(consumer_facts.aliases)
                    for call in (consumer_facts.direct_calls + consumer_facts.qualified_refs):
                        old_t = _resolve_reexport(_resolve_alias(call, c_aliases), old_reexports)
                        new_t = _resolve_reexport(_resolve_alias(call, c_aliases), new_reexports)
                        if old_t and old_t != new_t and old_t in new_artifact_consumption:
                            entry = _get_copy_of_entry(new_artifact_consumption[old_t])
                            if consumer_path in entry["consumers"]:
                                entry["consumers"].remove(consumer_path)
                            entry["channels"].pop(consumer_path, None)
                            entry["consumers"] = sorted(set(entry["consumers"]))
                            new_artifact_consumption[old_t] = entry
                        if new_t and _is_valid_target(new_t):
                            entry = _get_copy_of_entry(new_artifact_consumption.get(new_t, {}))
                            if consumer_path not in entry["consumers"]:
                                entry["consumers"].append(consumer_path)
                            entry["consumers"] = sorted(set(entry["consumers"]))
                            ch_list = set(entry["channels"].get(consumer_path, ["direct_calls"]))
                            entry["channels"][consumer_path] = sorted(ch_list)
                            new_artifact_consumption[new_t] = entry
                    executed_recompute.append(consumer_path)

        # D. PATCH - apply fact families listed in plan.patch_families
        for family in plan.patch_families:
            if family == "modules":
                if delta.is_deleted:
                    new_modules.pop(mod_id, None)
                    new_modules.pop(delta.module_path, None)
                else:
                    from contextor.core.domain.module import Module
                    new_module = Module(
                        module_id=delta.module_path,
                        path=str(path.relative_to(self.root_path)),
                        absolute_path=str(path.resolve()),
                        imports=new_imports or []
                    )
                    new_modules[delta.module_path] = new_module
                executed_patch_families.append("modules")

            elif family == "definitions":
                if delta.is_deleted:
                    new_artifacts.pop(mod_id, None)
                    new_artifacts.pop(delta.module_path, None)
                else:
                    new_artifacts[delta.module_path] = mod_artifacts
                executed_patch_families.append("definitions")

            elif family == "module_usages":
                if delta.is_deleted:
                    new_module_usages.pop(delta.module_path, None)
                else:
                    new_module_usages[delta.module_path] = new_usage
                executed_patch_families.append("module_usages")

            elif family == "dependency_graph":
                if delta.is_deleted or delta.is_new:
                    from contextor.core.graph.graph import build_trie, detect_package_root, build_graph
                    new_trie = build_trie(new_modules.keys())
                    new_package_root = detect_package_root(new_modules, new_trie)
                    new_graph = build_graph(new_modules, trie=new_trie, package_root=new_package_root)
                else:
                    new_trie = self.state.trie
                    new_package_root = self.state.package_root
                    new_graph = self.state.dependency_graph
                    if new_graph:
                        from contextor.core.graph.graph import resolve_module_edges
                        hard, soft = resolve_module_edges(delta.module_path, new_modules[delta.module_path], new_trie, new_package_root)
                        new_graph = new_graph.with_module_edges(delta.module_path, hard, soft)
                executed_patch_families.append("dependency_graph")

            elif family == "artifact_consumption":
                if delta.is_deleted:
                    for art_key in list(new_artifact_consumption.keys()):
                        if art_key == mod_id or art_key == delta.module_path or art_key.startswith(mod_id + ".") or art_key.startswith(delta.module_path + "."):
                            new_artifact_consumption.pop(art_key, None)

                reexports = _build_reexport_map(new_modules)
                # Unregister removed usages
                from contextor.core.domain.usage_facts import ModuleUsageFacts
                old_usage = getattr(self.state, "module_usages", {}).get(delta.module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
                old_aliases = dict(old_usage.aliases)
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
                    if target and target in new_artifact_consumption:
                        entry = _get_copy_of_entry(new_artifact_consumption[target])
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
                        new_artifact_consumption[target] = entry

                # Register current usages
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
                    if target and _is_valid_target(target):
                        entry = _get_copy_of_entry(new_artifact_consumption.get(target, {}))
                        if delta.module_path not in entry["consumers"]:
                            entry["consumers"].append(delta.module_path)
                        entry["consumers"] = sorted(set(entry["consumers"]))
                        ch_list = set(entry["channels"].get(delta.module_path, []))
                        ch_list.add(ch_name)
                        entry["channels"][delta.module_path] = sorted(ch_list)
                        new_artifact_consumption[target] = entry

                executed_patch_families.append("artifact_consumption")

            elif family == "identity_registry":
                executed_patch_families.append("identity_registry")

            elif family == "cached_analytics":
                from contextor.core.reporting_engine.graph_analytics import compute_cached_analytics
                hard_edges = getattr(new_graph, "hard_edges", {}) if new_graph else {}
                new_cached_analytics = compute_cached_analytics(
                    modules=new_modules,
                    artifacts=new_artifacts,
                    artifact_consumption=new_artifact_consumption,
                    hard_edges=hard_edges,
                )
                executed_patch_families.append("cached_analytics")

            else:
                raise ValueError(f"Unsupported patch family: {family}")


        # E. GRAPH - execute graph-only computations
        for graph_item in plan.graph_recomputations:
            if graph_item == "reverse_blast_radius":
                if delta.is_deleted:
                    blast_radius_complete = old_graph is not None
                elif delta.is_new:
                    blast_radius_complete = new_graph is not None
                else:
                    blast_radius_complete = old_graph is not None and new_graph is not None

                affected_set = (
                    self._calculate_affected_set(
                        delta.module_path,
                        old_graph=old_graph,
                        new_graph=new_graph,
                    )
                    if blast_radius_complete
                    else set()
                )
                executed_graph_recomputations.append("reverse_blast_radius")

            elif graph_item == "macro_metrics":
                if new_graph is not None:
                    from contextor.core.graph.metrics import compute_graph_metrics
                    new_metrics = compute_graph_metrics(new_graph.hard_edges, new_graph.soft_edges)
                executed_graph_recomputations.append("macro_metrics")

            elif graph_item == "advanced_graph_metrics":
                if new_graph is not None:
                    from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics
                    new_topology_analytics = compute_topology_analytics(
                        new_graph.hard_edges,
                        new_graph.soft_edges,
                        new_metrics,
                    )
                executed_graph_recomputations.append("advanced_graph_metrics")

            else:
                raise ValueError(f"Unsupported graph recomputation: {graph_item}")

        # F. COMMIT - commit boundary & atomic swap
        if "identity_registry" in executed_patch_families:
            all_modules = set(new_modules.keys())
            from contextor.core.reporting_layer.artifact_usage_report import (
                collect_qualified_artifact_identities,
            )
            current_artifacts = collect_qualified_artifact_identities(new_artifacts)
            with self.registry.transaction():
                self.registry.sync_with_workspace(all_modules, current_artifacts)

        # ATOMIC RAM SWAP
        self.state.modules = new_modules
        self.state.artifacts = new_artifacts
        self.state.dependency_graph = new_graph
        self.state.metrics = new_metrics
        self.state.topology_analytics = new_topology_analytics
        self.state.cached_analytics = new_cached_analytics
        if plan.refresh_completeness == "requires_resync":
            self.state.topology_metrics_state = "stale"
            self.state.cached_analytics_state = "stale"
        else:
            if "advanced_graph_metrics" in plan.graph_recomputations:
                self.state.topology_metrics_state = "fresh"
            if "cached_analytics" in plan.patch_families:
                self.state.cached_analytics_state = "fresh"
        self.state.artifact_consumption = new_artifact_consumption



        self.state.module_usages = new_module_usages
        self.state.trie = new_trie
        self.state.package_root = new_package_root

        self.state_manager.update_state(file_path)

        execution_trace = {
            "reparse_modules": tuple(executed_reparse),
            "recompute_modules": tuple(executed_recompute),
            "patch_families": tuple(executed_patch_families),
            "graph_recomputations": tuple(executed_graph_recomputations),
        }

        return affected_set, blast_radius_complete, execution_trace

        
    def _calculate_affected_set(
        self,
        changed_module: str,
        old_graph: Optional[ProjectGraph] = None,
        new_graph: Optional[ProjectGraph] = None,
    ) -> Set[str]:
        """
        Calculates the reverse transitive closure (blast radius) of the change.
        A module is affected if it directly or transitively depends on changed_module
        in either the old or candidate new dependency graph (hard and soft edges).
        """
        affected: Set[str] = {changed_module}

        graphs = [g for g in (old_graph, new_graph) if g is not None]
        if not graphs:
            return affected

        reverse_edges: dict[str, set[str]] = defaultdict(set)
        for g in graphs:
            for source, targets in g.hard_edges.items():
                for target in targets:
                    reverse_edges[target].add(source)
            for source, targets in g.soft_edges.items():
                for target in targets:
                    reverse_edges[target].add(source)

        queue = deque([changed_module])
        while queue:
            curr = queue.popleft()
            for consumer in reverse_edges.get(curr, set()):
                if consumer not in affected:
                    affected.add(consumer)
                    queue.append(consumer)

        return affected

    @staticmethod
    def _calculate_degree_deltas(
        old_graph: Optional[ProjectGraph] = None,
        new_graph: Optional[ProjectGraph] = None,
        old_modules: Optional[Iterable[str]] = None,
        new_modules: Optional[Iterable[str]] = None,
    ) -> LocalDegreeDeltaResult:
        """
        Calculates exact local graph degree changes (fan_in, fan_out) from hard-edge deltas
        between old_graph and new_graph.

        - fan_in / fan_out use hard_edges ONLY (soft_edges do not participate).
        - Values are recomputed from candidate new_graph.
        - Missing either old_graph or new_graph marks complete=False.
        - Newly added isolated modules receive fan_in=0, fan_out=0.
        - Deleted modules are reported in removed_modules and excluded from active degree updates.
        - Unrelated unchanged nodes are not included in update sets.
        """
        if old_graph is None or new_graph is None:
            return LocalDegreeDeltaResult(complete=False)

        old_mod_set = set(old_modules) if old_modules is not None else set(old_graph.hard_edges.keys())
        new_mod_set = set(new_modules) if new_modules is not None else set(new_graph.hard_edges.keys())

        added_modules = new_mod_set - old_mod_set
        removed_modules = old_mod_set - new_mod_set

        old_edges: Set[Tuple[str, str]] = {
            (source, target)
            for source, targets in old_graph.hard_edges.items()
            for target in targets
        }
        new_edges: Set[Tuple[str, str]] = {
            (source, target)
            for source, targets in new_graph.hard_edges.items()
            for target in targets
        }

        added_edges = new_edges - old_edges
        removed_edges = old_edges - new_edges

        fan_out_changed = {source for source, _ in (added_edges | removed_edges)} | added_modules
        fan_in_changed = {target for _, target in (added_edges | removed_edges)} | added_modules

        # Surviving / newly active modules to update
        surviving_fan_out = fan_out_changed - removed_modules
        surviving_fan_in = fan_in_changed - removed_modules

        fan_out_updates: Dict[str, int] = {}
        for m in sorted(surviving_fan_out):
            fan_out_updates[m] = len(new_graph.hard_edges.get(m, set()))

        fan_in_updates: Dict[str, int] = {}
        for m in sorted(surviving_fan_in):
            fan_in_updates[m] = sum(
                1 for _, targets in new_graph.hard_edges.items() if m in targets
            )

        return LocalDegreeDeltaResult(
            complete=True,
            fan_in_updates=fan_in_updates,
            fan_out_updates=fan_out_updates,
            added_modules=added_modules,
            removed_modules=removed_modules,
        )
