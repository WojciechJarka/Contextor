"""
contextor/mcp_server.py

Model Context Protocol (MCP) Server for Contextor.
Provides advanced Query APIs for LLMs to safely and efficiently extract 
architectural context without reading massive JSON dumps.
"""

import json
import sys
import glob
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from contextor.core.api.facade import ContextorFacade

# Initialize FastMCP Server
mcp = FastMCP("Contextor")


def _stderr_log(msg: str) -> None:
    """Redirects progress logs to stderr to protect JSON-RPC on stdout."""
    print(msg, file=sys.stderr, flush=True)


def _find_latest_report(repo_path: Path, pattern: str) -> Path | None:
    """Finds the most recently generated report matching the pattern."""
    out_dir = repo_path / "output"
    if not out_dir.is_dir():
        return None
    matches = sorted(glob.glob(str(out_dir / pattern)), reverse=True)
    for match in matches:
        if "_outdated" not in match:
            return Path(match)
    return None


# ==========================================================
# 1. ANALYSIS TRIGGER TOOLS
# ==========================================================

@mcp.tool()
def analyze_project(repo_path: str) -> str:
    """
    Triggers a global architectural analysis on the specified repository.
    Generates all reports in the 'output' directory.
    """
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    try:
        ContextorFacade.analyze_project(str(root), log=_stderr_log)
        return f"Analysis complete for {root.name}."
    except Exception as e:
        return f"Error during analysis: {str(e)}"

@mcp.tool()
def analyze_layer(repo_path: str, layer_name: str) -> str:
    """
    Triggers architectural analysis isolated to a specific layer (directory).
    """
    root = Path(repo_path).expanduser().resolve()
    layer = root / layer_name
    if not layer.is_dir():
        return f"Error: Layer path '{layer}' does not exist."
    try:
        ContextorFacade.analyze_layer(str(root), str(layer), log=_stderr_log)
        return f"Layer analysis complete for '{layer_name}'."
    except Exception as e:
        return f"Error during layer analysis: {str(e)}"

@mcp.tool()
def analyze_single_file(repo_path: str, file_path: str) -> str:
    """
    Triggers deep architectural analysis on a single Python file.
    """
    root = Path(repo_path).expanduser().resolve()
    target_file = Path(file_path).expanduser().resolve()
    if not target_file.is_file():
        return f"Error: Target file '{target_file}' does not exist."
    try:
        ContextorFacade.analyze_single_file(str(root), str(target_file), log=_stderr_log)
        return f"Single-file analysis complete for {target_file.name}."
    except Exception as e:
        return f"Error during single-file analysis: {str(e)}"


# ==========================================================
# 2. QUERY LAYER (OPTIMIZED FOR LLM)
# ==========================================================

@mcp.tool()
def get_project_architecture(repo_path: str) -> str:
    """
    [OPTIMIZED] The highest-level architectural summary of the project.
    Returns global action items, debt summary, layer index, and top 5 global hotspots.
    Use this first when exploring a new repository.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    summary_path = _find_latest_report(root, f"{repo_name}_summary_*.json")
    if not summary_path:
        return f"Error: No summary report found for {repo_name}. Run analyze_project first."
        
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        
        result = {
            "action_items": summary.get("action_items", []),
            "debt_summary": summary.get("debt_summary", {}),
            "layer_index": summary.get("layer_index", []),
            "top_global_hotspots": summary.get("top_hotspots", [])[:5],
            "module_count": summary.get("metrics", {}).get("global_module_count", 0)
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error reading project architecture: {e}"


@mcp.tool()
def get_module_context(repo_path: str, module_name: str) -> str:
    """
    [OPTIMIZED] Retrieves a compressed context pill for a single module.
    Returns its layer, visibility, metrics (fan_in/out, pagerank), and its direct inbound/outbound dependencies.
    Use this right before editing a file to understand its blast radius and requirements.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    ga_path = _find_latest_report(root, f"{repo_name}_graph_analytics_*.json")
    if not ga_path:
        return f"Error: No graph_analytics report found. Run analyze_project first."
        
    try:
        ga = json.loads(ga_path.read_text(encoding="utf-8"))
        modules = ga.get("modules", {})
        
        if module_name not in modules:
            return f"Module '{module_name}' not found in the project graph."
            
        mod_info = modules[module_name]
        
        # Resolve compact dependencies using index_dictionary if possible
        matrix = ga.get("module_dependency_matrix", {})
        
        inbound = {}
        outbound = {}
        
        # Note: In global scope, matrix keys are index IDs. We need the index dictionary.
        idx_path = _find_latest_report(root, f"{repo_name}_index_dictionary_*.json")
        if idx_path:
            idx = json.loads(idx_path.read_text(encoding="utf-8"))
            modules_rev = {str(v): str(k) for k, v in idx.get("modules", {}).items()}
            # Find the ID for our module
            mod_id = modules_rev.get(module_name)
            
            if mod_id and mod_id in matrix:
                for target_id, dep_data in matrix[mod_id].items():
                    target_name = idx.get("modules", {}).get(target_id, target_id)
                    outbound[target_name] = dep_data
                    
            for src_id, targets in matrix.items():
                if mod_id in targets:
                    src_name = idx.get("modules", {}).get(src_id, src_id)
                    inbound[src_name] = targets[mod_id]
        else:
            # Fallback if no index dictionary (e.g., matrix uses raw names)
            if module_name in matrix:
                outbound = matrix[module_name]
            for src_name, targets in matrix.items():
                if module_name in targets:
                    inbound[src_name] = targets[module_name]
        
        result = {
            "module": module_name,
            "metrics": mod_info,
            "dependencies_inbound_who_calls_me": inbound,
            "dependencies_outbound_who_i_call": outbound
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting module context: {e}"


@mcp.tool()
def get_artifact_blast_radius(repo_path: str, artifact_name: str) -> str:
    """
    [OPTIMIZED] Resolves the blast radius of a specific function, class, or variable.
    Returns the defining module and the exact list of modules that consume it.
    Use this to see what breaks if you change an artifact's signature.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    idx_path = _find_latest_report(root, f"{repo_name}_index_dictionary_*.json")
    art_path = _find_latest_report(root, f"{repo_name}_artifacts_compact_*.json")
    
    if not idx_path or not art_path:
        return "Error: Missing index dictionary or artifacts_compact report. Run analyze_project."
        
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        art_comp = json.loads(art_path.read_text(encoding="utf-8"))
        
        # Find the artifact ID
        art_id = None
        full_name = None
        for key, val in idx.get("artifacts", {}).items():
            # If the user passed just the name (e.g. 'IndexDictionary') or the full FQN (e.g. 'module::IndexDictionary')
            if val == artifact_name or val.endswith("::" + artifact_name) or val.endswith("." + artifact_name):
                art_id = key
                full_name = val
                break
                
        if not art_id:
            return f"Artifact '{artifact_name}' not found in the index dictionary."
            
        artifact_data = art_comp.get("artifacts", {}).get(art_id)
        if not artifact_data:
            return f"Artifact '{full_name}' found in index, but has no usage data (never consumed)."
            
        # Resolve module names
        id_to_name = idx.get("modules", {})
        definer = id_to_name.get(str(artifact_data.get("definer_module")), "Unknown")
        consumers = [id_to_name.get(str(c), str(c)) for c in artifact_data.get("consumer_module_indices", [])]
        
        result = {
            "artifact": full_name,
            "definer": definer,
            "consumer_count": len(consumers),
            "consumers": consumers
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting blast radius: {e}"


@mcp.tool()
def get_layer_isolation(repo_path: str, layer_name: str) -> str:
    """
    [OPTIMIZED] Extracts isolation metrics, clusters, and leaks for a specific architectural layer.
    Use this before refactoring a large component to understand its internal cohesion.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    # Try to find layer-specific report in high_risk_layers
    ga_path = _find_latest_report(root, f"*{repo_name}_{layer_name}_graph_analytics_*.json")
    
    if not ga_path:
        # Fallback to global summary if layer report doesn't exist
        summary_path = _find_latest_report(root, f"{repo_name}_summary_*.json")
        if not summary_path:
             return f"Error: No layer report found for '{layer_name}' and no global summary found."
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            for layer in summary.get("layer_index", []):
                if layer.get("layer") == layer_name:
                    return json.dumps(layer, indent=2)
            return f"Layer '{layer_name}' not found in global layer index."
        except Exception as e:
            return f"Error reading fallback layer info: {e}"
            
    try:
        ga = json.loads(ga_path.read_text(encoding="utf-8"))
        result = {
            "layer": layer_name,
            "module_count": ga.get("module_count", 0),
            "clusters": ga.get("shared_usage_clusters", []),
            "dependency_types": ga.get("dependency_type_breakdown", {})
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting layer isolation: {e}"


@mcp.tool()
def query_json_data(json_path: str, python_filter_expression: str) -> str:
    """
    [ADVANCED] Allows you to run a safe Python list-comprehension or filter on a large JSON file.
    The JSON payload is loaded into a variable named 'data'.
    Example expression: "[k for k, v in data.get('modules', {}).items() if v.get('fan_in', 0) > 20]"
    """
    target = Path(json_path).expanduser().resolve()
    if not target.is_file():
        return f"Error: File '{target}' does not exist."
        
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        # Execute the comprehension safely
        result = eval(python_filter_expression, {"data": data, "json": json})
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error executing query: {str(e)}\nMake sure 'data' is treated as a dict/list."


# ==========================================================
# 3. FALLBACK TOOLS
# ==========================================================

@mcp.tool()
def read_json_report(report_path: str) -> str:
    """
    [DEPRECATED] Reads a raw JSON report from disk.
    WARNING: Prefer using the targeted query tools (get_project_architecture, get_module_context) 
    to save context tokens. Use this only for small files like 'name_collisions'.
    """
    target = Path(report_path).expanduser().resolve()
    if not target.is_file():
        return f"Error: Report file '{target}' does not exist."
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading report: {str(e)}"


def main():
    """Entry point for the MCP server."""
    # Ensure Windows IO encoding is UTF-8 to prevent charmap errors in JSON-RPC
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    import asyncio
    async def _run():
        await mcp.run_stdio_async()
        
    asyncio.run(_run())


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
