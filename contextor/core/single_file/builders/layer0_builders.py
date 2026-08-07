from typing import Any
from .registry import ContextBuilder, ContextPayload, BuildState

class ModuleIntentBuilder:
    name = "ModuleIntentBuilder"
    requires = set()
    provides = {"module_intent"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.module_intent import extract_module_intent
        return {"module_intent": extract_module_intent(payload.tree, payload.source)}

class SymbolContextBuilder:
    name = "SymbolContextBuilder"
    requires = set()
    provides = {"symbol_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.symbol_engine import extract_file_symbols, build_symbol_index, find_symbol_usage
        from contextor.core.reference.engine import build_symbol_references
        from contextor.core.api.api_consumers import extract_api_consumers, summarize_api_consumers
        
        symbols = extract_file_symbols(payload.file_path)
        all_symbols = (
            symbols.get("classes", [])
            + symbols.get("functions", [])
            + symbols.get("methods", [])
            + symbols.get("globals", [])
        )
        usage = find_symbol_usage(payload.modules, payload.module_id, all_symbols, payload.root_path)
        ecosystem = build_symbol_index(payload.modules, payload.root_path)
        ecosystem = {
            symbol: users
            for symbol, users in ecosystem.items()
            if (symbol in all_symbols or symbol.split(".")[-1] in all_symbols)
        }
        references = build_symbol_references(
            payload.modules, all_symbols, payload.root_path, definer_module=payload.module_id
        )
        consumers = extract_api_consumers(
            all_symbols, references, signatures=symbols.get("signatures", {})
        )
        
        return {
            "symbol_context": {
                "symbols": symbols,
                "all_symbols": all_symbols,
                "usage": usage,
                "ecosystem": ecosystem,
                "references": references,
                "consumers": consumers,
                "consumer_summary": summarize_api_consumers(consumers),
            }
        }

class ImportContextBuilder:
    name = "ImportContextBuilder"
    requires = set()
    provides = {"import_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.symbol_engine import classify_imports
        known_modules = set(payload.modules.keys()) | {
            key.replace("core.", "contextor.core.") for key in payload.modules.keys() if key.startswith("core.")
        }
        imports = classify_imports(payload.module, known_modules)
        return {"import_context": {"imports": imports}}

class SemanticContextBuilder:
    name = "SemanticContextBuilder"
    requires = set()
    provides = {"semantic_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.semantic_analysis import analyze_module_semantics
        from contextor.core.analysis.risk_analysis import analyze_effects
        from contextor.core.analysis.import_analysis import extract_import_usage
        
        semantic = analyze_module_semantics(payload.tree)
        effects = analyze_effects(payload.tree)
        imports = extract_import_usage(payload.tree)
        return {
            "semantic_context": {
                "semantic_analysis": {
                    **semantic,
                    **effects,
                    "import_usage": imports,
                }
            }
        }

class FunctionContextBuilder:
    name = "FunctionContextBuilder"
    requires = set()
    provides = {"function_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.function_analysis import analyze_functions
        return {"function_context": analyze_functions(payload.tree)}

class StateContextBuilder:
    name = "StateContextBuilder"
    requires = set()
    provides = {"state_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.state_analysis import analyze_module_states
        return {"state_context": analyze_module_states(payload.tree)}

class ArchitectureContextBuilder:
    name = "ArchitectureContextBuilder"
    requires = set()
    provides = {"architecture_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.graph.cycles import detect_cycles
        from contextor.core.graph.metrics import compute_graph_metrics
        from contextor.core.graph.thresholds import get_thresholds
        from contextor.core.validator.collisions import validate_name_collisions
        from contextor.core.context import (
            find_dependents, find_soft_dependents, find_cluster, 
            architecture_signals, find_transitive_dependents
        )
        from contextor.core.analysis.call_chain import build_entry_chains
        
        hard_edges = payload.project_graph.hard_edges
        soft_edges = payload.project_graph.soft_edges
        cycles = detect_cycles(hard_edges)
        metrics = compute_graph_metrics(hard_edges, soft_edges)
        thresholds = get_thresholds(metrics["nodes"])
        
        name_collisions = []
        if payload.modules:
            all_collisions = validate_name_collisions(payload.modules)
            for error in all_collisions:
                if any(
                    payload.module_id in node or node.endswith(payload.module_id.replace(".", "/"))
                    for node in error.nodes
                ):
                    name_collisions.append(error.message)
                    
        hotspots = []
        if payload.global_report:
            hotspots = payload.global_report.get("llm_signals", {}).get("hotspots", [])
            
        return {
            "architecture_context": {
                "hard_dependencies": sorted(hard_edges.get(payload.module_id, [])),
                "soft_dependencies": sorted(soft_edges.get(payload.module_id, [])),
                "imported_by": find_dependents(payload.module_id, hard_edges),
                "soft_imported_by": find_soft_dependents(payload.module_id, soft_edges),
                "cluster": find_cluster(payload.module_id, hard_edges),
                "signals": architecture_signals(
                    payload.module_id, hard_edges, soft_edges, hotspots, cycles, metrics["nodes"]
                ),
                "thresholds": thresholds,
                "cycles": [cycle for cycle in cycles if payload.module_id in cycle],
                "name_collisions": name_collisions,
                "graph_metrics": metrics,
                "impact_radius": find_transitive_dependents(payload.module_id, hard_edges),
                "entry_chains": build_entry_chains(payload.module_id, hard_edges),
            }
        }

class ApiSurfaceBuilder:
    name = "ApiSurfaceBuilder"
    requires = set()
    provides = {"api_surface"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.api_surface.engine import extract_api_surface
        from contextor.core.api_surface.metadata import extract_api_metadata
        return {
            "api_surface": {
                "surface": extract_api_surface(payload.module),
                "metadata": extract_api_metadata(payload.module),
            }
        }

class ImportUsersBuilder:
    name = "ImportUsersBuilder"
    requires = set()
    provides = {"import_users"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.reference.engine import find_import_users
        return {"import_users": find_import_users(payload.module_id, payload.modules)}

class GitContextBuilder:
    name = "GitContextBuilder"
    requires = set()
    provides = {"git_context"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.git_context import collect_git_context
        return {"git_context": collect_git_context(payload.file_path, payload.root_path)}
