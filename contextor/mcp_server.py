"""
Contextor MCP Server
====================

Model Context Protocol server for Contextor architectural analysis tools.

IMPORTANT:
-----------
MCP stdio transport is extremely sensitive.
stdout MUST contain only JSON-RPC messages.

Do NOT use:
- print() to stdout
- startup banners
- debug logs on stdout
- third-party libraries that write startup messages to stdout

Use stderr for diagnostics only.


EMERGENCY RECOVERY PROCEDURE
============================

If Antigravity shows:

    context deadline exceeded

or MCP server does not expose tools:

1. Close Antigravity IDE completely.

2. Verify installed FastMCP version:

    python -m pip show fastmcp fastmcp-slim mcp


3. If FastMCP installation is corrupted or mixed:

    python -m pip uninstall fastmcp fastmcp-slim -y


4. Remove remaining package folders manually if they exist:

    <python>\Lib\site-packages\fastmcp
    <python>\Lib\site-packages\fastmcp-*.dist-info


5. Clean reinstall compatible version:

    python -m pip install fastmcp==2.12.4


6. Verify import:

    python -c "from fastmcp import FastMCP; print('FAST MCP OK')"


7. Verify MCP server starts:

    python -m contextor.mcp_server


8. Restart Antigravity IDE.

9. Open MCP configuration and check:

    contextor
    Enabled
    tools visible


TROUBLESHOOTING CHECKS
======================

Check active Python:

    python -c "import sys; print(sys.executable)"


Check MCP package:

    python -c "import mcp; print(mcp.__file__)"


Check FastMCP package:

    python -c "import fastmcp; print(fastmcp.__file__)"


Expected:
- mcp and fastmcp must come from the same Python environment.
- Do not mix FastMCP 3.x packages with FastMCP 2.x runtime.
- Do not install FastMCP globally when using an embedded Python distribution.


WINDOWS NOTE
============

For Windows stdio transport:

- keep "-u" in MCP command arguments
- use UTF-8 encoding
- redirect diagnostic output to stderr

Example:

    print("debug", file=sys.stderr, flush=True)


The MCP server must start silently and wait for JSON-RPC messages.
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
        ContextorFacade.analyze_single_file(str(target_file), str(root), log=_stderr_log)
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
            "module_count": summary.get("metrics", {}).get("nodes", 0)
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
def get_file_edit_context(repo_path: str, file_path: str) -> str:
    """
    [OPTIMIZED] Specialized single-shot context pill for LLMs prior to editing a file.
    Combines module metrics, API signature blast radius, and dependency trees into one response.
    Returns: file, module, public_api, imports, consumers, risk_score, tests_covering.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    # Deriving module name from file path
    target_path = Path(file_path)
    if target_path.is_absolute():
        try:
            rel_path = target_path.relative_to(root)
        except ValueError:
            rel_path = target_path
    else:
        rel_path = target_path

    parts = list(rel_path.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts.pop()
    
    module_name = ".".join(parts)
    
    ga_path = _find_latest_report(root, f"{repo_name}_graph_analytics_*.json")
    idx_path = _find_latest_report(root, f"{repo_name}_index_dictionary_*.json")
    art_path = _find_latest_report(root, f"{repo_name}_artifacts_compact_*.json")
    
    if not (ga_path and idx_path and art_path):
        return "Error: Missing required reports. Run analyze_project first."
        
    try:
        ga = json.loads(ga_path.read_text(encoding="utf-8"))
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        art_comp = json.loads(art_path.read_text(encoding="utf-8"))
        
        mod_info = ga.get("modules", {}).get(module_name, {})
        
        # Prefer real hotspot score from summary.json, fall back to centrality proxy
        risk_score = 0.0
        summary_path = _find_latest_report(root, f"{repo_name}_summary_*.json")
        if summary_path:
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                for h in summary.get("top_hotspots", []):
                    if h.get("module") == module_name:
                        risk_score = h.get("score", 0.0)
                        break
            except Exception:
                pass
        if risk_score == 0.0:
            risk_score = round(
                (mod_info.get("betweenness", 0) + mod_info.get("hub_score", 0)) / 2, 4
            )
        
        modules_rev = {str(v): str(k) for k, v in idx.get("modules", {}).items()}
        mod_id = modules_rev.get(module_name)
        
        imports = []
        consumers = []
        
        matrix = ga.get("module_dependency_matrix", {})
        if mod_id:
            if mod_id in matrix:
                for target_id in matrix[mod_id].keys():
                    target_name = idx.get("modules", {}).get(target_id, target_id)
                    imports.append(target_name)
            for src_id, targets in matrix.items():
                if mod_id in targets:
                    src_name = idx.get("modules", {}).get(src_id, src_id)
                    consumers.append(src_name)
        else:
            if module_name in matrix:
                imports = list(matrix[module_name].keys())
            for src_name, targets in matrix.items():
                if module_name in targets:
                    consumers.append(src_name)
                    
        public_api = []
        if mod_id:
            # O(1) lookup if index is present in artifacts_compact
            if "module_artifacts" in art_comp and str(mod_id) in art_comp["module_artifacts"]:
                public_api = art_comp["module_artifacts"][str(mod_id)]
            else:
                # O(n) fallback
                for art_id, art_data in art_comp.get("artifacts", {}).items():
                    if str(art_data.get("definer_module")) == mod_id:
                        art_name = idx.get("artifacts", {}).get(art_id, str(art_id))
                        if not art_name.split("::")[-1].startswith("_"):
                            public_api.append(art_name)
        
        # tests_covering: modules from 'tests.*' layer that depend on this module
        tests_covering = [c for c in consumers if c.startswith("tests.")]
        
        result = {
            "file": file_path,
            "file_exists": target_path.is_file(),
            "module": module_name,
            "layer": mod_info.get("layer", "unknown"),
            "entrypoint": mod_info.get("entrypoint", False),
            "public_api": public_api,
            "imports": imports,
            "consumers": consumers,
            "risk_score": risk_score,
            "tests_covering": {
                "available": len(tests_covering) > 0,
                "tests": tests_covering
            }
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting file edit context: {e}"


@mcp.tool()
def get_layer_isolation(repo_path: str, layer_name: str) -> str:
    """
    [OPTIMIZED] Extracts isolation metrics, clusters, and leaks for a specific architectural layer.
    Use this before refactoring a large component to understand its internal cohesion.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    # Normalize layer_name in case user passes a path like "contextor/core"
    normalized_layer_name = Path(layer_name).name
    
    # Try to find layer-specific report in high_risk_layers
    ga_path = _find_latest_report(root, f"*{repo_name}_{normalized_layer_name}_graph_analytics_*.json")
    
    if not ga_path:
        # Fallback to global summary if layer report doesn't exist
        summary_path = _find_latest_report(root, f"{repo_name}_summary_*.json")
        if not summary_path:
             return f"Error: No layer report found for '{normalized_layer_name}' and no global summary found."
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            for layer in summary.get("layer_index", []):
                if layer.get("layer") == normalized_layer_name:
                    return json.dumps(layer, indent=2)
            return f"Layer '{normalized_layer_name}' not found in global layer index."
        except Exception as e:
            return f"Error reading fallback layer info: {e}"
            
    try:
        ga = json.loads(ga_path.read_text(encoding="utf-8"))
        
        # Build id->name map for resolving matrix indices
        idx_path = _find_latest_report(root, f"{repo_name}_index_dictionary_*.json")
        id_to_name: dict[str, str] = {}
        if idx_path:
            idx = json.loads(idx_path.read_text(encoding="utf-8"))
            id_to_name = idx.get("modules", {})
        
        modules = ga.get("modules", {})
        matrix = ga.get("module_dependency_matrix", {})
        
        # Allowed layer dependency directions (src_layer -> set of allowed tgt_layers)
        # Higher layers may call lower layers but not vice versa.
        # Order: tests > ui/cli > contract > engine > runtime > adapter
        _LAYER_ORDER = ["tests", "ui", "cli", "contract", "engine", "runtime", "adapter"]
        _LAYER_RANK = {l: i for i, l in enumerate(_LAYER_ORDER)}
        
        def _is_violation(src_layer: str, tgt_layer: str) -> bool:
            """A violation occurs when a lower-ranked layer calls a higher-ranked one."""
            src_rank = _LAYER_RANK.get(src_layer, -1)
            tgt_rank = _LAYER_RANK.get(tgt_layer, -1)
            if src_rank < 0 or tgt_rank < 0:
                return False
            # ui/cli calling engine/runtime is a violation
            return src_rank > tgt_rank
        
        boundary_violations = []
        for src_id, targets in matrix.items():
            src_name = id_to_name.get(src_id, src_id)
            src_layer = modules.get(src_name, {}).get("layer", "")
            if not src_layer:
                continue
            for tgt_id in targets:
                tgt_name = id_to_name.get(tgt_id, tgt_id)
                if tgt_name == src_name:
                    continue
                tgt_layer = modules.get(tgt_name, {}).get("layer", "")
                if not tgt_layer:
                    continue
                if _is_violation(src_layer, tgt_layer):
                    boundary_violations.append({
                        "from": src_name,
                        "from_layer": src_layer,
                        "to": tgt_name,
                        "to_layer": tgt_layer,
                    })
        
        result = {
            "layer": normalized_layer_name,
            "module_count": ga.get("module_count", 0),
            "clusters": ga.get("shared_usage_clusters", []),
            "dependency_types": ga.get("dependency_type_breakdown", {}),
            "boundary_violations": boundary_violations,
            "boundary_violations_count": len(boundary_violations),
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting layer isolation: {e}"


@mcp.tool()
def get_report_diff(repo_path: str) -> str:
    """
    [OPTIMIZED] Returns architectural regression analysis between the last two analysis runs.
    Shows delta in hotspot count, debt score, cycle count, and lists new/resolved hotspots.
    Run analyze_project at least twice (on different code states) to populate this.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    diff_path = _find_latest_report(root, f"{repo_name}_report_diff_*.json")
    if not diff_path:
        return (
            f"No diff report found for '{repo_name}'. "
            "Run analyze_project at least twice (on different commits or code states) "
            "to generate a regression diff."
        )
    try:
        diff_data = json.loads(diff_path.read_text(encoding="utf-8"))
        report = diff_data.get("report_diff", diff_data)
        return json.dumps(report, indent=2)
    except Exception as e:
        return f"Error reading diff report: {e}"


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
        # Safe sandbox: only whitelisted builtins, no import/exec/open
        _safe_builtins = {
            "__builtins__": {},
            "data": data,
            "json": json,
            "sorted": sorted, "list": list, "dict": dict, "set": set,
            "len": len, "str": str, "int": int, "float": float, "bool": bool,
            "min": min, "max": max, "sum": sum,
            "enumerate": enumerate, "zip": zip, "range": range,
            "any": any, "all": all, "filter": filter, "map": map,
            "isinstance": isinstance, "round": round, "abs": abs,
            "True": True, "False": False, "None": None,
        }
        result = eval(python_filter_expression, _safe_builtins)
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