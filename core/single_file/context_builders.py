# -*- coding: utf-8 -*-
"""
repo_guardian/core/single_file/context_builders.py

Auxiliary module offloading the main single analysis file.
Contains builders for individual report contexts (symbols, imports, architecture).
"""

from repo_guardian.core.symbol_analysis import (
    extract_file_symbols,
    classify_imports,
    find_symbol_usage,
    build_symbol_index,
)
from repo_guardian.core.symbol_reference import build_symbol_references
from repo_guardian.core.analysis.export_analysis import extract_exports, find_unused_public_api, summarize_exports
from repo_guardian.core.api.api_consumers import extract_api_consumers, summarize_api_consumers
from repo_guardian.core.analysis.import_analysis import extract_import_usage
from repo_guardian.core.analysis.semantic_analysis import analyze_module_semantics
from repo_guardian.core.analysis.risk_analysis import analyze_effects
from repo_guardian.core.graph.cycles import detect_cycles
from repo_guardian.core.graph.metrics import compute_graph_metrics
from repo_guardian.core.graph.thresholds import get_thresholds
from repo_guardian.core.architecture_context import (
    find_dependents,
    find_soft_dependents,
    find_cluster,
    architecture_signals,
    find_transitive_dependents,
)
from repo_guardian.core.validator.collisions import validate_name_collisions
from repo_guardian.core.analysis.call_chain import build_entry_chains


def collect_symbol_context(file_path, modules, module_id, root_path):
    symbols = extract_file_symbols(file_path)
    all_symbols = (
        symbols.get("classes", [])
        + symbols.get("functions", [])
        + symbols.get("methods", [])
        + symbols.get("globals", [])
    )

    usage = find_symbol_usage(modules, module_id, all_symbols, root_path)
    ecosystem = build_symbol_index(modules, root_path)

    ecosystem = {
        symbol: users
        for symbol, users in ecosystem.items()
        if (symbol in all_symbols or symbol.split(".")[-1] in all_symbols)
    }

    references = build_symbol_references(
        modules, all_symbols, root_path, definer_module=module_id
    )

    consumers = extract_api_consumers(all_symbols, references)

    return {
        "symbols": symbols,
        "all_symbols": all_symbols,
        "usage": usage,
        "ecosystem": ecosystem,
        "references": references,
        "consumers": consumers,
        "consumer_summary": summarize_api_consumers(consumers),
    }

def collect_import_context(module, modules):
    known_modules = set(modules.keys()) | {
        key.replace("core.", "repo_guardian.core.")
        for key in modules.keys()
        if key.startswith("core.")
    }
    imports = classify_imports(module, known_modules)
    return {"imports": imports}

def collect_export_context(tree, symbols, usage, local_calls=None, references=None):
    exports = extract_exports(tree)
    unused_candidates = find_unused_public_api(
        symbols, usage, exports, local_calls, references=references
    )
    return {
        "exports": exports,
        "export_summary": summarize_exports(exports),
        "unused_candidates": unused_candidates,
    }

def collect_semantic_context(tree):
    semantic = analyze_module_semantics(tree)
    effects = analyze_effects(tree)
    imports = extract_import_usage(tree)
    return {
        "semantic_analysis": {
            **semantic,
            **effects,
            "import_usage": imports,
        }
    }

def collect_architecture_context(module_id, project_graph, global_report=None, modules=None):
    hard_edges = project_graph.hard_edges
    soft_edges = project_graph.soft_edges
    cycles = detect_cycles(hard_edges)
    metrics = compute_graph_metrics(hard_edges, soft_edges)
    thresholds = get_thresholds(metrics["nodes"])

    name_collisions = []
    if modules:
        all_collisions = validate_name_collisions(modules)
        for error in all_collisions:
            if any(module_id in node or node.endswith(module_id.replace(".", "/")) for node in error.nodes):
                name_collisions.append(error.message)

    hotspots = []
    if global_report:
        hotspots = global_report.get("llm_signals", {}).get("hotspots", [])

    return {
        "hard_dependencies": sorted(hard_edges.get(module_id, [])),
        "soft_dependencies": sorted(soft_edges.get(module_id, [])),
        "imported_by": find_dependents(module_id, hard_edges),
        "soft_imported_by": find_soft_dependents(module_id, soft_edges),
        "cluster": find_cluster(module_id, hard_edges),
        "signals": architecture_signals(module_id, hard_edges, soft_edges, hotspots, cycles, metrics["nodes"]),
        "thresholds": thresholds,
        "cycles": [cycle for cycle in cycles if module_id in cycle],
        "name_collisions": name_collisions,
        "graph_metrics": metrics,
        "impact_radius": find_transitive_dependents(module_id, hard_edges),
        "entry_chains": build_entry_chains(module_id, hard_edges),
    }
