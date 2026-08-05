"""
contextor/mcp_server.py

Model Context Protocol (MCP) Server for Contextor.
Allows LLMs (like Claude Desktop) to invoke Contextor analysis directly.
"""

import json
from pathlib import Path
import sys

# We lazily import mcp to avoid blowing up if the user hasn't installed it yet,
# though the entrypoint implies it is available.
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("[ERROR] 'mcp' package is not installed. Please run MCP_installer.bat.")
    sys.exit(1)

from contextor.core.api.facade import ContextorFacade
from contextor.ui.gui_parser import parse_and_filter_json

# Initialize FastMCP Server
mcp = FastMCP("Contextor")


@mcp.tool()
def analyze_project(repo_path: str) -> str:
    """
    Triggers a global architectural analysis on the specified repository.
    Generates summary, structure, and artifact reports in the 'output' directory.
    Returns a summary of the execution.
    """
    root = Path(repo_path).expanduser().resolve()
    
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist or is not a directory."
        
    try:
        ContextorFacade.analyze_project(str(root))
        return f"Analysis complete for {root.name}. Reports have been saved to the 'output' directory inside the repository."
    except Exception as e:
        return f"Error during analysis: {str(e)}"


@mcp.tool()
def analyze_layer(repo_path: str, layer_name: str) -> str:
    """
    Triggers an architectural analysis on a specific layer (directory) within the repository.
    Generates layer-specific summary and artifacts.
    """
    root = Path(repo_path).expanduser().resolve()
    layer = root / layer_name
    
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    if not layer.is_dir():
        return f"Error: Layer path '{layer}' does not exist inside the repository."
        
    try:
        ContextorFacade.analyze_layer(str(root), str(layer))
        return f"Layer analysis complete for '{layer_name}'. Reports have been saved to the 'output' directory."
    except Exception as e:
        return f"Error during layer analysis: {str(e)}"


@mcp.tool()
def analyze_single_file(repo_path: str, file_path: str) -> str:
    """
    Triggers an architectural analysis on a single Python file within the context of the repository.
    Returns a summary of the execution.
    """
    root = Path(repo_path).expanduser().resolve()
    target_file = Path(file_path).expanduser().resolve()
    
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    if not target_file.is_file():
        return f"Error: Target file '{target_file}' does not exist."
        
    try:
        ContextorFacade.analyze_single_file(str(root), str(target_file))
        return f"Single-file analysis complete for {target_file.name}. Report has been saved to the 'output' directory."
    except Exception as e:
        return f"Error during single-file analysis: {str(e)}"


@mcp.tool()
def filter_artifacts(json_path: str, search_term: str) -> str:
    """
    Filters a generated artifacts JSON report (e.g., Contextor_Repo_artifacts.json) 
    by a specific symbol, module, or file path. Uses strict string matching.
    Returns the filtered artifact chunks.
    """
    target = Path(json_path).expanduser().resolve()
    if not target.is_file():
        return f"Error: Artifacts file '{target}' does not exist."
        
    try:
        filtered_chunks = parse_and_filter_json(str(target), search_term)
        if not filtered_chunks:
            return f"No artifacts found matching '{search_term}'."
            
        return f"Found {len(filtered_chunks)} artifacts:\n\n" + "\n---\n".join(filtered_chunks)
    except Exception as e:
        return f"Error filtering artifacts: {str(e)}"


@mcp.tool()
def read_json_report(report_path: str) -> str:
    """
    Reads and returns the contents of a generated Contextor JSON report from disk.
    Use this to read summary, structure, or collision reports.
    """
    target = Path(report_path).expanduser().resolve()
    if not target.is_file():
        return f"Error: Report file '{target}' does not exist."
        
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading report: {str(e)}"


def main():
    """
    Entry point for the MCP server.
    """
    mcp.run()


if __name__ == "__main__":
    main()
