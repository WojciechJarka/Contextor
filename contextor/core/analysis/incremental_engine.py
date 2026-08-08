from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Set, Dict, Any

from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState, FileDelta
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.symbol_engine.indexer import read_imports


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
    artifact_consumption_state: str = "stale"


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

    def update_file(self, file_path: str) -> IncrementalUpdateResult:
        """
        Updates the canonical state incrementally for a single changed file.
        Returns the update status and the freshness of the architectural model.
        """
        if not self.state_manager.has_changed(file_path):
            return IncrementalUpdateResult(status="UNCHANGED", file_path=file_path)
            
        path = Path(file_path)
        rel_path = path.relative_to(self.root_path)
        module_path = ".".join(rel_path.with_suffix("").parts)
        
        # 1. Handle Deletion
        current_state = self.state_manager.get_current_file_state(file_path, compute_hash=False)
        if not current_state:
            delta = FileDelta(
                module_path=module_path,
                is_deleted=True
            )
            self._apply_delta_and_commit(file_path, delta, [], {})
            return IncrementalUpdateResult(
                status="DELETED", 
                file_path=file_path, 
                delta=delta,
                graph_state="fresh",
                dependencies_state="fresh",
                blast_radius_state="deferred",
                local_metrics_state="deferred",
                global_metrics_state="deferred",
                artifact_consumption_state="deferred"
            )

        # 2. Parse new file
        try:
            new_imports, error = read_imports(path)
            if error:
                # Syntax error = zero changes to the architectural model
                return IncrementalUpdateResult(status="SYNTAX_ERROR", file_path=file_path)
        except Exception:
            return IncrementalUpdateResult(status="ERROR", file_path=file_path)

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
                "consumers": old_consumers # Preserve previous snapshot
            }
        except Exception:
            old_artifacts = self.state.artifacts.get(module_path, {})
            old_consumers = old_artifacts.get("consumers", {})
            new_artifacts = {"symbols": {}, "own_symbols": set(), "consumers": old_consumers}
            raw_symbols = {}
        
        # 4. Calculate FileDelta (Purely structural, NO identity logic here)
        # We need to know if it's a new file by checking if it exists in the active registry.
        # But wait, registry ID check is fast. We can check if it has an ID to know if it's new.
        module_id = self.registry.get_module_id(module_path)
        is_new = module_id is None
        
        delta = self._calculate_delta(module_path, module_id, is_new, new_imports, new_artifacts)
        
        # 5. Apply and Commit
        self._apply_delta_and_commit(file_path, delta, new_imports, new_artifacts)
        
        # Determine graph state based on whether it was a full canonical rebuild or local update
        graph_state = "fresh" if (is_new or delta.is_deleted) else "fresh" # We always keep it fresh now because ADD/DELETE does full rebuild
        
        return IncrementalUpdateResult(
            status="UPDATED", 
            file_path=file_path, 
            delta=delta,
            graph_state=graph_state,
            dependencies_state="fresh",
            blast_radius_state="deferred",
            local_metrics_state="deferred",
            global_metrics_state="deferred",
            artifact_consumption_state="deferred"
        )
        
    def _calculate_delta(self, module_path: str, persistent_id: Optional[str], is_new: bool, new_imports: List, new_artifacts_dict: dict) -> FileDelta:
        delta = FileDelta(
            module_path=module_path,
            is_new=is_new
        )
        
        if is_new or persistent_id is None:
            delta.imports_added = new_imports or []
            symbols = new_artifacts_dict.get("symbols", {})
            delta.artifacts_added = list(symbols.get("functions", [])) + \
                                    list(symbols.get("classes", [])) + \
                                    list(symbols.get("methods", []))
            return delta
            
        # Get old state using the canonical dot-path!
        old_module = self.state.modules.get(module_path)
        old_imports = old_module.imports if old_module else []
        
        # Compute imports delta
        old_import_names = {imp.module for imp in old_imports if imp.module}
        new_import_names = {imp.module for imp in (new_imports or []) if imp.module}
        
        delta.imports_added = list(new_import_names - old_import_names)
        delta.imports_removed = list(old_import_names - new_import_names)
        
        # Compute artifacts delta
        symbols = new_artifacts_dict.get("symbols", {})
        new_artifact_names = set(symbols.get("functions", [])) | \
                             set(symbols.get("classes", [])) | \
                             set(symbols.get("methods", []))
                             
        old_artifacts = self.state.artifacts.get(module_path, {})
        # Note: self.state.artifacts contains the tuple (symbols, own_symbols, consumers)
        # So we just get the own_symbols from it to compute delta.
        old_symbols = old_artifacts.get("symbols", {})
        old_artifact_names = set(old_symbols.get("functions", [])) | \
                             set(old_symbols.get("classes", [])) | \
                             set(old_symbols.get("methods", []))
                             
        delta.artifacts_added = list(new_artifact_names - old_artifact_names)
        delta.artifacts_removed = list(old_artifact_names - new_artifact_names)
        
        return delta

    def _apply_delta_and_commit(self, file_path: str, delta: FileDelta, new_imports: list, mod_artifacts: dict):
        """
        Applies the delta to the graph/registry and commits atomically.
        """
        path = Path(file_path)
        
        # 0. Shallow copy state to guarantee transactional atomicity
        new_modules = dict(self.state.modules)
        new_artifacts = dict(self.state.artifacts)
        
        # 1. Update working dictionaries
        if delta.is_deleted:
            if delta.module_path in new_modules:
                del new_modules[delta.module_path]
            if delta.module_path in new_artifacts:
                del new_artifacts[delta.module_path]
        else:
            from contextor.core.domain.module import Module
            new_module = Module(
                module_id=delta.module_path,
                path=str(path.relative_to(self.root_path)),
                absolute_path=str(path.resolve()),
                imports=new_imports or []
            )
            new_modules[delta.module_path] = new_module
            new_artifacts[delta.module_path] = mod_artifacts

        # 2. Canonical Graph / Trie Rebuild
        if delta.is_deleted or delta.is_new:
            # Canonical Full Graph Rebuild for ADD/DELETE
            from contextor.core.graph.graph import build_trie, detect_package_root, build_graph
            new_trie = build_trie(new_modules.keys())
            new_package_root = detect_package_root(new_modules, new_trie)
            new_graph = build_graph(new_modules, trie=new_trie, package_root=new_package_root)
        else:
            # Incremental Graph Update for MODIFY
            new_trie = self.state.trie
            new_package_root = self.state.package_root
            new_graph = self.state.dependency_graph
            if new_graph:
                from contextor.core.graph.graph import resolve_module_edges
                hard, soft = resolve_module_edges(delta.module_path, new_modules[delta.module_path], new_trie, new_package_root)
                new_graph = new_graph.with_module_edges(delta.module_path, hard, soft)

        # 3. Canonical update for artifact_consumption (Deferred)
        # We preserve the previous snapshot entirely until a global rebuild occurs.
        new_artifact_consumption = self.state.artifact_consumption

        # 4. Fast set logic for orphans/re-allocations
        all_modules = set(new_modules.keys())
        all_artifacts_set = set()
        for mod_id, mod_artifacts_data in new_artifacts.items():
            symbols = mod_artifacts_data.get("symbols", {})
            all_artifacts_set.update(symbols.get("functions", []))
            all_artifacts_set.update(symbols.get("classes", []))
            all_artifacts_set.update(symbols.get("methods", []))
        
        # 5. Commit Boundary
        # Transaction context handles ONLY the write to the disk.
        # If any part of it fails (e.g. disk full), the with block will raise OSError.
        with self.registry.transaction():
            self.registry.sync_with_workspace(all_modules, all_artifacts_set)
            
        # ATOMIC RAM SWAP (Safe from exceptions because it runs only if transaction() exits cleanly)
        self.state.modules = new_modules
        self.state.artifacts = new_artifacts
        self.state.dependency_graph = new_graph
        self.state.artifact_consumption = new_artifact_consumption
        self.state.trie = new_trie
        self.state.package_root = new_package_root

        # Post-Transaction: Update FileState in RAM
        self.state_manager.update_state(file_path)

        
    def _calculate_affected_set(self, changed_module: str, delta: FileDelta) -> Set[str]:
        """
        Calculates the blast radius of the change.
        """
        affected = {changed_module}
        
        # Example propagation logic using blast radius
        if self.state.dependency_graph:
            # Add modules that depend on the changed artifacts
            pass
            
        return affected
        
    def _update_local_metrics(self, affected_set: Set[str]):
        """
        Updates strictly local metrics (fan-in, fan-out) for the affected set.
        Global metrics (PageRank) are skipped for now or deferred.
        """
        pass
