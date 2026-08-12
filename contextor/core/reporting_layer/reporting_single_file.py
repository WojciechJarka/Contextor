"""
core/reporting_layer/reporting_single_file.py

SINGLE MODULE REPORT FORMATTER

Layer: REPORT ASSEMBLY

Responsibilities:
- Formats context data into the final JSON matrix
- Injects LOC and semantic metrics into LLM summary
- Acts solely as a compiler (no domain AST knowledge)
"""

from datetime import datetime

import orjson

from contextor.core.paths import atomic_write, resolve_report_path
from contextor.core.reporting_engine.dictionary import IndexDictionary


def _qualified_artifact_name(module_name: str, symbol: str) -> str:
    """Return the repository-wide identity used by the global artifact report."""
    if "::" in symbol:
        return symbol
    return f"{module_name}::{symbol}"


def _artifact_id(index_dict: IndexDictionary, module_name: str, symbol: str) -> str:
    return index_dict.get_artifact_id(_qualified_artifact_name(module_name, symbol))


def _symbol_kinds(symbols: dict) -> dict[str, str]:
    kinds = {}
    if not isinstance(symbols, dict):
        return kinds
    for category, kind in (
        ("classes", "class"),
        ("functions", "function"),
        ("methods", "method"),
        ("globals", "global"),
    ):
        for symbol in symbols.get(category, []):
            kinds[symbol] = kind
    return kinds


def _flatten_api_surface(surface: dict) -> dict:
    """Normalize grouped and already-flat API surface schemas."""
    if not isinstance(surface, dict):
        return {}
    grouped = {"classes", "functions", "methods", "globals"}
    flattened = {}
    for name, data in surface.items():
        if name in grouped and isinstance(data, dict):
            flattened.update(data)
        else:
            flattened[name] = data
    return flattened


def _compact_module_evidence(data: dict, index_dict: IndexDictionary) -> dict:
    compacted = {}
    for category, value in data.items():
        if isinstance(value, dict) and isinstance(value.get("modules"), list):
            compacted[category] = {
                **value,
                "modules": [index_dict.get_module_id(module) for module in value["modules"]],
            }
        else:
            compacted[category] = value
    return compacted


def save_single_file_report(report, path):
    """
    JSON report save using orjson.
    """

    atomic_write(
        resolve_report_path(path),
        orjson.dumps(report, option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS),
    )


def _build_llm_summary(ctx: dict) -> dict:
    """
    Builds an LLM-friendly context aggregate (Context - Part 2).

    Merges into one structure:
    - module intent
    - deep API signatures (Surface)
    - blast radius (impact radius on dependencies)
    - AI guidance (architecture-based tips)
    """

    arch = ctx.get("architecture_context", {})
    activity = ctx.get("activity_summary", {})
    intent = ctx.get("module_intent", {})
    tests = ctx.get("test_context", {})
    git_ctx = ctx.get("git_context", {})
    impact = arch.get("impact_radius", [])
    signals = arch.get("signals", [])
    entry_chains = arch.get("entry_chains", [])

    direct_dependents = arch.get("imported_by", [])
    transitive_dependents = [e["module"] for e in impact if e.get("depth", 0) > 1]
    impact_depth = max((e.get("depth", 0) for e in impact), default=0)

    # Module-level reverse dependency closure. This is deliberately not
    # presented as an exact symbol-level refactoring blast radius.
    module_dependency_radius = len(direct_dependents) + len(transitive_dependents)

    # 2. AI Guidance (Hints Vector based on Debt/Hotspots)
    guidance = []
    if "cycle_member" in signals:
        guidance.append(
            "CRITICAL: File creates an import cycle. If modifying it, try using Dependency Inversion or extracting a common interface."
        )
    if "hotspot" in signals:
        guidance.append(
            "WARNING: File is marked as a HOTSPOT. It has a high change coefficient and many dependencies. Regression risk is elevated."
        )
    if "config_hub" in signals:
        guidance.append(
            "INFO: Module appears to be a configuration hub. High level of outgoing dependencies is natural here. Focus on data consistency."
        )
    if module_dependency_radius > 15:
        guidance.append(
            f"WARNING: Module dependency radius is {module_dependency_radius} modules. "
            "Public API changes require regression testing or backward compatibility."
        )
    if not guidance:
        guidance.append(
            "Module is stable (no elevated architectural risk). You can modify its API normally."
        )

    # 3. Deep Surface (API callable by LLM)
    api_surface_deep = _flatten_api_surface(
        ctx.get("api_surface", {}).get("surface", {})
    )
    functions = ctx.get("function_context", {})

    enriched_surface = {}
    for name, surface_data in api_surface_deep.items():
        enriched = dict(surface_data)
        if name in functions:
            fctx = functions[name]
            enriched["detailed_signature"] = fctx.get("signature")
            if not enriched.get("docstring"):
                enriched["docstring"] = fctx.get("docstring")
            enriched["arg_annotations"] = fctx.get("arg_annotations", [])
            enriched["return_annotation"] = fctx.get("return_annotation")
            enriched["complexity_metrics"] = fctx.get("metrics", {})
        enriched_surface[name] = enriched

    return {
        "purpose": intent.get("docstring") or "",
        "section_map": intent.get("section_headers", []),
        "api_surface": enriched_surface,
        "public_api_count": len(ctx.get("public_api", [])),
        "live_symbols": activity.get("live", 0),
        "unused_public_api_count": activity.get("unused_public_api", 0),
        "module_dependency_radius": module_dependency_radius,
        "module_dependency_radius_kind": "reverse_hard_dependency_closure",
        "direct_dependents": direct_dependents,
        "transitive_dependents": transitive_dependents,
        "impact_depth": impact_depth,
        "all_impact_radius": impact,
        "test_files": tests.get("test_files", []),
        "tested_symbols": tests.get("tested_symbols", []),
        "untested_public_symbols": tests.get("untested_public_symbols", []),
        "ai_guidance": guidance,
        "collision_warnings": arch.get("name_collisions", []),
        "architecture_signals": signals,
        "cycles": arch.get("cycles", []),
        "entry_chains": entry_chains,
        "git_context": git_ctx,
        "model": {
            "name": "facts_first",
            "architecture": "layered_context_extraction",
            "version": "2.2-llm-enriched",
        },
    }


def generate_single_file_report(ctx: dict, module_count: int, report_header: dict | None = None, index_dict: IndexDictionary | None = None):
    """
    Generates a single file report using pre-calculated context structures.
    """

    symbol_context = ctx["symbol_context"]
    export_context = ctx["export_context"]
    architecture = ctx["architecture_context"]

    # Module semantics, effects and import usage are produced by
    # collect_semantic_context() but were never emitted: the report's
    # "semantic_analysis" key is built from state/function context and
    # shadowed them. Surfaced under their own key so the analysis that
    # already runs is not thrown away.
    module_semantics = ctx["semantic_context"].get("semantic_analysis", {})

    if index_dict is None:
        raise ValueError("index_dict must be provided to generate_single_file_report")
        
    module_name = ctx["module_id"]
    my_mod_idx = index_dict.get_module_id(module_name)
    artifact_id = lambda symbol: _artifact_id(index_dict, module_name, symbol)
    symbol_kinds = _symbol_kinds(symbol_context["symbols"])
    
    # Compact artifact_consumption
    original_ac = ctx.get("artifact_consumption", {})
    compact_symbols = {}
    
    for k, v in original_ac.get("symbols", {}).items():
        a_id = artifact_id(k)
        compact_usage = _compact_module_evidence(v, index_dict)
        consumers = sorted({
            module
            for value in v.values()
            if isinstance(value, dict)
            for module in value.get("modules", [])
            if module
        })
        compact_symbols[a_id] = {
            "artifact_id": a_id,
            "kind": symbol_kinds.get(k),
            "definer_module": my_mod_idx,
            "consumer_module_indices": [index_dict.get_module_id(c) for c in consumers],
            "consumer_count": len(consumers),
            "usage": compact_usage,
            "risk_score": v.get("risk_score", 0)
        }
        
    compact_module_consumers = {}
    for cat, data in original_ac.get("consumers", {}).items():
        compact_module_consumers[cat] = {
            "modules": [index_dict.get_module_id(m) for m in data.get("modules", [])],
            "evidence_type": data.get("evidence_type")
        }

    compact_consumption = {
        "module": my_mod_idx,
        "consumers": compact_module_consumers,
        "coupling": original_ac.get("coupling", {}),
        "risk_score": original_ac.get("risk_score", 0),
        "symbols": compact_symbols
    }
        
    # Compact architecture
    arch = ctx["architecture_context"]
    compact_arch = {
        "hard_dependencies": [index_dict.get_module_id(m) for m in arch.get("hard_dependencies", [])],
        "hard_dependents": [index_dict.get_module_id(m) for m in arch.get("imported_by", [])],
        "soft_dependencies": [index_dict.get_module_id(m) for m in arch.get("soft_dependencies", [])],
        "soft_dependents": [index_dict.get_module_id(m) for m in arch.get("soft_imported_by", [])],
        "graph_metrics": arch.get("graph_metrics", {}),
        "cycles": [
            [index_dict.get_module_id(m) for m in cycle] for cycle in arch.get("cycles", [])
        ] if "cycles" in arch else []
    }

    report = {
        # --------------------------------------------------
        # IDENTITY
        # --------------------------------------------------
        "module_id": my_mod_idx,
        "module_name": module_name,
        "global_node_id": my_mod_idx,
        "file": str(ctx["file_path"]),
        "generated_at": datetime.now().isoformat(),
        # --------------------------------------------------
        # MODULE INTENT  (nowe - F2)
        # --------------------------------------------------
        "module_intent": ctx.get("module_intent", {}),
        # --------------------------------------------------
        # SYMBOL DOMAIN
        # --------------------------------------------------
        "symbols": [artifact_id(s) for s in symbol_context["all_symbols"]],
        "symbol_usage": {artifact_id(k): [index_dict.get_module_id(v) for v in vals] for k, vals in symbol_context["usage"].items()},
        "symbol_ecosystem": {artifact_id(k): [index_dict.get_module_id(v) for v in vals] for k, vals in symbol_context["ecosystem"].items()},
        "symbol_references": symbol_context["references"],
        "api_consumers": {artifact_id(k): _compact_module_evidence(v, index_dict) for k, v in symbol_context["consumers"].items()},
        "api_consumer_summary": symbol_context["consumer_summary"],
        # --------------------------------------------------
        # API DOMAIN
        # --------------------------------------------------
        "public_api": [artifact_id(s) for s in ctx["public_api"]],
        "exports": [
            artifact_id(s)
            for s in (
                export_context["exports"].get("symbols", [])
                if isinstance(export_context["exports"], dict)
                else export_context["exports"]
            )
        ],
        "export_summary": export_context["export_summary"],
        # --------------------------------------------------
        # SYMBOL ACTIVITY
        # --------------------------------------------------
        "symbol_activity": {artifact_id(k): v for k, v in ctx["symbol_activity"].items()},
        "activity_summary": ctx["activity_summary"],
        "unused_public_api": sorted(
            [
                artifact_id(symbol)
                for symbol, data in ctx["symbol_activity"].items()
                if data["status"] == "UNUSED_PUBLIC"
            ]
        ),
        "unused_candidates_old": [artifact_id(s) for s in export_context["unused_candidates"]],
        # --------------------------------------------------
        # ARTIFACT CONSUMPTION
        # --------------------------------------------------
        "artifact_consumption": compact_consumption,
        "api_surface": {
            artifact_id(name): data
            for name, data in _flatten_api_surface(
                ctx.get("api_surface", {}).get("surface", {})
            ).items()
        },
        # --------------------------------------------------
        # CODE SEMANTICS & STATE
        # --------------------------------------------------
        "module_semantics": module_semantics,
        "semantic_analysis": {
            "mutability": [
                {
                    "symbol": artifact_id(k),
                    "mutated_args": v.get("mutated_args", []),
                    "globals_mutated": [artifact_id(g) for g in v.get("globals_mutated", [])],
                }
                for k, v in ctx.get("state_context", {}).items()
                if not v.get("is_pure", True)
            ],
            "side_effects": [
                {
                    "symbol": artifact_id(k),
                    "nonlocals": v.get("nonlocals_used", []),
                    "self_mutations": v.get("self_mutations", []),
                    "captured": v.get("captured_in_closures", []),
                }
                for k, v in ctx.get("state_context", {}).items()
                if not v.get("is_pure", True)
            ],
            "risks": [
                {
                    "symbol": artifact_id(k),
                    "complexity": v.get("metrics", {}).get("complexity", 1),
                    "raises": v.get("metrics", {}).get("raises", []),
                }
                for k, v in ctx.get("function_context", {}).items()
                if v.get("metrics", {}).get("complexity", 1) > 5
            ],
        },
        "functions": {artifact_id(k): v for k, v in ctx.get("function_context", {}).items()},
        # --------------------------------------------------
        # IMPORTS
        # --------------------------------------------------
        "imports": {
            category: [
                index_dict.get_module_id(module) if category in {"internal", "local"} else module
                for module in modules
            ]
            for category, modules in ctx["import_context"]["imports"].items()
        } if isinstance(ctx["import_context"]["imports"], dict) else [],
        "import_users": [index_dict.get_module_id(u) for u in ctx["import_users"]],
        # --------------------------------------------------
        # ARCHITECTURE
        # --------------------------------------------------
        "architecture": compact_arch,
        "lines_of_code": ctx.get("lines_of_code", 0),
        # --------------------------------------------------
        # TEST CONTEXT  (nowe - F5)
        # --------------------------------------------------
        "test_context": {
            "test_files": ctx.get("test_context", {}).get("test_files", []),
            "tested_symbols": [artifact_id(s) for s in ctx.get("test_context", {}).get("tested_symbols", [])],
            "untested_public_symbols": [artifact_id(s) for s in ctx.get("test_context", {}).get("untested_public_symbols", [])]
        } if ctx.get("test_context") else {},
        # --------------------------------------------------
        # GIT
        # --------------------------------------------------
        "git": ctx.get("git_context", {}),
        # --------------------------------------------------
        # REPOSITORY CONTEXT
        # --------------------------------------------------
        "repository_context": {
            "module_count": module_count,
            "graph_metrics": architecture["graph_metrics"],
            "cycles": architecture["cycles"],
            # Number of artifacts from this module present in the global
            # artifact index (only those with >=1 consumer). A low count
            # relative to symbol count suggests many unused exports. (P5b)
            "artifact_count_in_module": len([
                sym for sym in symbol_context.get("consumers", {}).values()
                if (sym.get("consumer_count", {}).get("total", 0) if isinstance(sym.get("consumer_count"), dict) else sym.get("consumer_count", 0)) > 0
            ]),
        },
        # --------------------------------------------------
        # LLM SUMMARY  (nowe - F6)
        # --------------------------------------------------
        "llm_summary": _build_llm_summary(ctx),
        "_format_version": "3",
        "_format_note": "Indexed Compact Single File Report"
    }

    # Inject report_header if provided (P2e) — same schema as other report types.
    if report_header:
        report["report_header"] = {**report_header, "data_source": "single_file"}

    return report
