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

    # 1. Blast Radius
    blast_radius = len(direct_dependents) + len(transitive_dependents)

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
    if blast_radius > 15:
        guidance.append(
            f"WARNING: Blast radius is {blast_radius} modules. Do not change the public API without thorough testing (or maintain backward compatibility)."
        )
    if not guidance:
        guidance.append(
            "Module is stable (no elevated architectural risk). You can modify its API normally."
        )

    # 3. Deep Surface (API callable by LLM)
    api_surface_deep = ctx.get("api_surface", {}).get("surface", {})
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
        "blast_radius": blast_radius,
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


def generate_single_file_report(ctx: dict, module_count: int, report_header: dict | None = None):
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

    report = {
        # --------------------------------------------------
        # IDENTITY
        # --------------------------------------------------
        "module": ctx["module_id"],
        # Explicit link to the global dependency graph node — allows a
        # consumer holding only this single-file report to look up the
        # module in artifacts.json / structure.json by key without
        # reconstructing the id from the file path. (P5)
        "global_node_id": ctx["module_id"],
        "file": str(ctx["file_path"]),
        "generated_at": datetime.now().isoformat(),
        # --------------------------------------------------
        # MODULE INTENT  (nowe - F2)
        # --------------------------------------------------
        "module_intent": ctx.get("module_intent", {}),
        # --------------------------------------------------
        # SYMBOL DOMAIN
        # --------------------------------------------------
        "symbols": symbol_context["symbols"],
        "symbol_usage": symbol_context["usage"],
        "symbol_ecosystem": symbol_context["ecosystem"],
        "symbol_references": symbol_context["references"],
        "api_consumers": symbol_context["consumers"],
        "api_consumer_summary": symbol_context["consumer_summary"],
        # --------------------------------------------------
        # API DOMAIN
        # --------------------------------------------------
        "public_api": ctx["public_api"],
        "exports": export_context["exports"],
        "export_summary": export_context["export_summary"],
        # --------------------------------------------------
        # SYMBOL ACTIVITY
        # --------------------------------------------------
        "symbol_activity": ctx["symbol_activity"],
        "activity_summary": ctx["activity_summary"],
        "unused_public_api": sorted(
            [
                symbol
                for symbol, data in ctx["symbol_activity"].items()
                if data["status"] == "UNUSED_PUBLIC"
            ]
        ),
        "unused_candidates_old": export_context["unused_candidates"],
        # --------------------------------------------------
        # ARTIFACT CONSUMPTION
        # --------------------------------------------------
        "artifact_consumption": ctx["artifact_consumption"],
        "api_surface": ctx["api_surface"],
        # --------------------------------------------------
        # CODE SEMANTICS & STATE
        # --------------------------------------------------
        "module_semantics": module_semantics,
        "semantic_analysis": {
            "mutability": [
                {
                    "symbol": k,
                    "mutated_args": v.get("mutated_args", []),
                    "globals_mutated": v.get("globals_mutated", []),
                }
                for k, v in ctx.get("state_context", {}).items()
                if not v.get("is_pure", True)
            ],
            "side_effects": [
                {
                    "symbol": k,
                    "nonlocals": v.get("nonlocals_used", []),
                    "self_mutations": v.get("self_mutations", []),
                    "captured": v.get("captured_in_closures", []),
                }
                for k, v in ctx.get("state_context", {}).items()
                if not v.get("is_pure", True)
            ],
            "risks": [
                {
                    "symbol": k,
                    "complexity": v.get("metrics", {}).get("complexity", 1),
                    "raises": v.get("metrics", {}).get("raises", []),
                }
                for k, v in ctx.get("function_context", {}).items()
                if v.get("metrics", {}).get("complexity", 1) > 5
            ],
        },
        "functions": ctx.get("function_context", {}),
        # --------------------------------------------------
        # IMPORTS
        # --------------------------------------------------
        "imports": ctx["import_context"]["imports"],
        "import_users": ctx["import_users"],
        # --------------------------------------------------
        # ARCHITECTURE
        # --------------------------------------------------
        "architecture": architecture,
        "lines_of_code": ctx.get("lines_of_code", 0),
        # --------------------------------------------------
        # TEST CONTEXT  (nowe - F5)
        # --------------------------------------------------
        "test_context": ctx.get("test_context", {}),
        # --------------------------------------------------
        # GIT CONTEXT
        # --------------------------------------------------
        "git_context": ctx.get("git_context", {}),
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
    }

    # Inject report_header if provided (P2e) — same schema as other report types.
    if report_header:
        report["report_header"] = {**report_header, "data_source": "single_file"}

    return report
