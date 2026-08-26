from typing import Any
from .registry import ContextBuilder, ContextPayload, BuildState

class ModuleIntentBuilder:
    name = "ModuleIntentBuilder"
    requires = set()
    provides = {"module_intent"}
    
    def build(self, payload: ContextPayload, state: BuildState) -> dict[str, Any]:
        from contextor.core.analysis.module_intent import extract_module_intent
        return {"module_intent": extract_module_intent(payload.tree, payload.source)}

def _canonical_state_module_is_current(state: Any, module_id: str) -> bool:
    if state is None:
        return False

    artifacts = getattr(state, "artifacts", None)
    if not isinstance(artifacts, dict) or module_id not in artifacts:
        return False

    from contextor.core.analysis.state_manager import module_current_truth

    truth = module_current_truth(state, module_id)
    return bool(
        truth.get("available")
        and truth.get("state") == "fresh"
        and truth.get("provenance") == "current"
    )


def _canonical_module_is_current(payload: ContextPayload) -> bool:
    return _canonical_state_module_is_current(
        payload.engine_state,
        payload.module_id,
    )


def _collision_applies_to_module(
    nodes: Any,
    module_id: str,
) -> bool:
    if not isinstance(module_id, str) or not module_id:
        return False

    path_form = module_id.replace(".", "/")

    if isinstance(nodes, str):
        candidates = (nodes,)
    else:
        candidates = nodes or ()

    return any(
        isinstance(node, str)
        and (
            module_id in node
            or node.endswith(path_form)
        )
        for node in candidates
    )

class SymbolContextBuilder:
    name = "SymbolContextBuilder"
    requires = set()
    provides = {"symbol_context"}

    def build(
        self,
        payload: ContextPayload,
        state: BuildState,
    ) -> dict[str, Any]:
        from contextor.core.api.api_consumers import (
            extract_api_consumers,
            summarize_api_consumers,
        )

        canonical_current = _canonical_module_is_current(payload)

        # --------------------------------------------------
        # LOCAL SYMBOL CATALOG
        # --------------------------------------------------

        if canonical_current:
            canonical_artifact = payload.engine_state.artifacts[payload.module_id]

            raw_symbols = canonical_artifact.get("symbols", {})

            symbols = {
                key: list(value) if isinstance(value, (list, tuple, set)) else value
                for key, value in raw_symbols.items()
            }

            all_symbols = list(
                canonical_artifact.get("own_symbols", ())
            )
        else:
            from contextor.core.symbol_engine import extract_file_symbols

            symbols = extract_file_symbols(payload.file_path)

            all_symbols = (
                symbols.get("classes", [])
                + symbols.get("functions", [])
                + symbols.get("methods", [])
                + symbols.get("globals", [])
            )

        # --------------------------------------------------
        # CANONICAL USAGE
        # --------------------------------------------------

        consumption_fresh = bool(
            canonical_current
            and getattr(
                payload.engine_state,
                "artifact_consumption_state",
                "deferred",
            )
            == "fresh"
        )

        if consumption_fresh:
            canonical_consumption = (
                payload.engine_state.artifact_consumption or {}
            )

            usage = {}

            for symbol in all_symbols:
                record = canonical_consumption.get(
                    f"{payload.module_id}::{symbol}",
                    {},
                )

                consumers = sorted(
                    set(record.get("consumers", ()))
                )

                if consumers:
                    usage[symbol] = consumers
        else:
            from contextor.core.symbol_engine import find_symbol_usage

            usage = find_symbol_usage(
                payload.modules,
                payload.module_id,
                all_symbols,
                payload.root_path,
            )

        # --------------------------------------------------
        # CANONICAL SYMBOL ECOSYSTEM
        # --------------------------------------------------

        if canonical_current:
            target_symbols = set(all_symbols)
            ecosystem: dict[str, list[str]] = {}

            for module_id, module_artifacts in (
                payload.engine_state.artifacts or {}
            ).items():
                if not _canonical_state_module_is_current(
                    payload.engine_state,
                    module_id,
                ):
                    continue

                if not isinstance(module_artifacts, dict):
                    continue

                for qualified_symbol in module_artifacts.get(
                    "own_symbols",
                    (),
                ):
                    leaf = qualified_symbol.split(".")[-1]

                    if (
                        qualified_symbol in target_symbols
                        or leaf in target_symbols
                    ):
                        ecosystem.setdefault(
                            qualified_symbol,
                            [],
                        ).append(module_id)

            ecosystem = {
                symbol: sorted(set(module_ids))
                for symbol, module_ids in ecosystem.items()
            }
        else:
            from contextor.core.symbol_engine import build_symbol_index

            raw_ecosystem = build_symbol_index(
                payload.modules,
                payload.root_path,
            )

            ecosystem = {
                symbol: users
                for symbol, users in raw_ecosystem.items()
                if (
                    symbol in all_symbols
                    or symbol.split(".")[-1] in all_symbols
                )
            }

        # --------------------------------------------------
        # REFERENCES & CANONICAL PROJECTION
        # --------------------------------------------------

        from contextor.core.reference.engine import (
            CanonicalReferenceEvidenceUnavailable,
            build_symbol_references,
            build_symbol_references_from_canonical,
        )

        canonical_reference_eligible = bool(
            canonical_current
            and getattr(payload.engine_state, "artifact_consumption_state", "deferred") == "fresh"
            and isinstance(getattr(payload.engine_state, "module_usages", None), dict)
        )

        references = None
        if canonical_reference_eligible:
            current_consumer_modules = {
                mod_id
                for mod_id in payload.engine_state.module_usages
                if _canonical_state_module_is_current(payload.engine_state, mod_id)
            }
            try:
                references = build_symbol_references_from_canonical(
                    definer_module=payload.module_id,
                    symbols=all_symbols,
                    artifact_consumption=payload.engine_state.artifact_consumption or {},
                    module_usages=payload.engine_state.module_usages,
                    current_modules=current_consumer_modules,
                )
            except CanonicalReferenceEvidenceUnavailable:
                references = None

        if references is None:
            references = build_symbol_references(
                payload.modules,
                all_symbols,
                payload.root_path,
                definer_module=payload.module_id,
            )

        consumers = extract_api_consumers(
            all_symbols,
            references,
            signatures=symbols.get("signatures", {}),
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

        engine_state = payload.engine_state

        # Cycles
        if (
            engine_state is not None
            and getattr(
                engine_state,
                "cycles_state",
                "deferred",
            ) == "fresh"
        ):
            cycles = list(engine_state.cycles)
        else:
            cycles = detect_cycles(hard_edges)

        # Metrics (canonicalization deferred to avoid uncontracted assumptions)
        metrics = compute_graph_metrics(hard_edges, soft_edges)
        thresholds = get_thresholds(metrics.get("nodes", 0)) if isinstance(metrics, dict) and "nodes" in metrics else {}

        # Collisions
        name_collisions = []
        if (
            engine_state is not None
            and getattr(
                engine_state,
                "collisions_state",
                "deferred",
            ) == "fresh"
        ):
            for error in engine_state.collisions:
                if isinstance(error, str):
                    if _collision_applies_to_module(
                        error,
                        payload.module_id,
                    ):
                        name_collisions.append(error)
                    continue

                if _collision_applies_to_module(
                    getattr(error, "nodes", ()),
                    payload.module_id,
                ):
                    name_collisions.append(
                        getattr(error, "message", str(error))
                    )
        elif payload.modules:
            all_collisions = validate_name_collisions(payload.modules)
            for error in all_collisions:
                if _collision_applies_to_module(
                    getattr(error, "nodes", ()),
                    payload.module_id,
                ):
                    name_collisions.append(error.message)

        # Hotspots (canonicalization deferred)
        hotspots = []
        if payload.global_report:
            hotspots = (
                payload.global_report
                .get("llm_signals", {})
                .get("hotspots", [])
            )

        return {
            "architecture_context": {
                "hard_dependencies": sorted(hard_edges.get(payload.module_id, [])),
                "soft_dependencies": sorted(soft_edges.get(payload.module_id, [])),
                "imported_by": find_dependents(payload.module_id, hard_edges),
                "soft_imported_by": find_soft_dependents(payload.module_id, soft_edges),
                "cluster": find_cluster(payload.module_id, hard_edges),
                "signals": architecture_signals(
                    payload.module_id, hard_edges, soft_edges, hotspots, cycles, metrics.get("nodes", 0) if isinstance(metrics, dict) else 0
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
