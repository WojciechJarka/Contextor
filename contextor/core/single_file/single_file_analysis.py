"""
core/single_file_analysis.py

Single module deep-dive orchestrator.
Builds the raw context dictionary by triggering all granular semantic,
state and architectural analyzers for a given file via a plugin registry.
"""

import ast

from contextor.core.context.locator import find_module_id
from contextor.core.source import SourceError, read_source
from contextor.core.single_file.builders import default_registry, ContextPayload


def read_tree(file_path: str):
    try:
        source = read_source(file_path)
    except SourceError:
        return None, ""

    try:
        return ast.parse(source), source
    except (SyntaxError, ValueError, RecursionError):
        return None, source


def collect_all_contexts(
    file_path: str, modules: dict, project_graph, global_report: dict = None, root_path: str = None
):
    """
    Acts as the master pipeline for a single file. Gathers INTENT, SYMBOL, STATE,
    and EXPORT contexts alongside the calculated technical debt and architectural linkages
    by executing a topological sequence of registered context builders.
    Returns the fully populated raw diagnostic dictionary ready for JSON serialization.
    """
    module_id = find_module_id(file_path, modules)
    if not module_id:
        raise ValueError(f"Module not found: {file_path}")

    module = modules[module_id]
    tree, source = read_tree(file_path)

    payload = ContextPayload(
        file_path=file_path,
        module_id=module_id,
        modules=modules,
        root_path=root_path,
        module=module,
        tree=tree,
        source=source,
        project_graph=project_graph,
        global_report=global_report,
    )

    results = default_registry.build_all(payload)
    
    # Inject base metadata
    results["module_id"] = module_id
    results["file_path"] = file_path
    results["lines_of_code"] = len(source.splitlines()) if source else 0

    return results
