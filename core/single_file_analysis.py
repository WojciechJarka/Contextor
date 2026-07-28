# -*- coding: utf-8 -*-

"""
core/single_file_analysis.py

Single module deep-dive orchestrator.
Builds the raw context dictionary by triggering all granular semantic,
state and architectural analyzers for a given file.
"""

import ast
from pathlib import Path

from repo_guardian.core.single_file.context_builders import (
    collect_symbol_context,
    collect_import_context,
    collect_export_context,
    collect_semantic_context,
    collect_architecture_context,
)
from repo_guardian.core.context.locator import find_module_id
from repo_guardian.core.module_intent import extract_module_intent
from repo_guardian.core.analysis.function_analysis import analyze_functions
from repo_guardian.core.api_surface.engine import extract_api_surface
from repo_guardian.core.api_surface.metadata import extract_api_metadata
from repo_guardian.core.api.public_api import extract_public_api
from repo_guardian.core.analysis.activity import classify_symbol_activity, summarize_activity
from repo_guardian.core.artifact_consumption import build_artifact_consumption
from repo_guardian.core.reference.engine import find_import_users
from repo_guardian.core.analysis.test_context import build_test_context
from repo_guardian.core.analysis.git_context import collect_git_context

def read_tree(file_path: str):
    path = Path(file_path)
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        return ast.parse(source), source
    except Exception:
        return None, source


def collect_all_contexts(file_path: str, modules: dict, project_graph, global_report: dict = None, root_path: str = None):
    """
    Acts as the master pipeline for a single file. Gathers INTENT, SYMBOL, STATE,
    and EXPORT contexts alongside the calculated technical debt and architectural linkages.
    Returns the fully populated raw diagnostic dictionary ready for JSON serialization.
    """
    module_id = find_module_id(file_path, modules)
    if not module_id:
        raise ValueError(f"Module not found: {file_path}")

    module = modules[module_id]
    tree, source = read_tree(file_path)

    module_intent = extract_module_intent(tree, source)

    symbol_context = collect_symbol_context(file_path, modules, module_id, root_path)
    import_context = collect_import_context(module, modules)
    export_context = collect_export_context(
        tree,
        symbol_context["all_symbols"],
        symbol_context["usage"],
        local_calls=symbol_context["symbols"].get("calls", []),
        references=symbol_context["references"]
    )
    semantic_context = collect_semantic_context(tree)
    function_context = analyze_functions(tree)
    
    from repo_guardian.core.analysis.state_analysis import analyze_module_states
    state_context = analyze_module_states(tree)
    
    architecture = collect_architecture_context(module_id, project_graph, global_report, modules=modules)

    api_surface = {
        "surface": extract_api_surface(module),
        "metadata": extract_api_metadata(module),
    }
    public_api = extract_public_api(symbol_context["symbols"])
    symbol_activity = classify_symbol_activity(
        symbol_context["all_symbols"],
        symbol_context["references"],
        public_symbols=public_api,
        local_calls=symbol_context["symbols"].get("calls", []),
        analyze_scope="all"
    )
    activity_summary = summarize_activity(symbol_activity)

    artifact_consumption = build_artifact_consumption(
        module_id,
        symbol_context["all_symbols"],
        symbol_context["consumers"],
        import_context["imports"],
        architecture["imported_by"],
        public_api,
        symbol_activity,
        activity_summary,
        modules,
        root_path,
        tree,
    )

    import_users = find_import_users(module_id, modules)

    test_context = build_test_context(
        module_id,
        root_path,
        public_api,
    )

    git_context = collect_git_context(file_path, root_path)

    return {
        "module_id": module_id,
        "file_path": file_path,
        "lines_of_code": len(source.splitlines()) if source else 0,
        "module_intent": module_intent,
        "symbol_context": symbol_context,
        "import_context": import_context,
        "export_context": export_context,
        "semantic_context": semantic_context,
        "function_context": function_context,
        "state_context": state_context,
        "architecture_context": architecture,
        "api_surface": api_surface,
        "public_api": public_api,
        "symbol_activity": symbol_activity,
        "activity_summary": activity_summary,
        "artifact_consumption": artifact_consumption,
        "import_users": import_users,
        "test_context": test_context,
        "git_context": git_context,
    }
