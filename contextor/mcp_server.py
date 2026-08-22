r"""
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

    python -m contextor.mcp_main


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
import asyncio
import atexit
import os
import sys
import warnings
from pathlib import Path


def _is_virtual_environment() -> bool:
    """Return whether this interpreter is isolated by venv/virtualenv."""

    return bool(
        getattr(sys, "real_prefix", None)
        or sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    )


def _project_venv_python() -> Path:
    """Return the repository-local interpreter expected to host MCP."""

    venv_dir = Path(__file__).resolve().parents[1] / ".venv"
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _ensure_virtual_environment() -> None:
    """Re-exec MCP in the project venv before importing its dependencies.

    LLM/client use: MCP configuration may safely invoke any Python that can
    import this bootstrap module. Outside a virtual environment the process is
    atomically replaced by ``.venv`` Python, preserving the JSON-RPC stdio
    streams. A missing project venv is a startup error rather than permission to
    fall back to globally installed, potentially incompatible dependencies.
    """

    if _is_virtual_environment():
        return

    interpreter = _project_venv_python()
    if not interpreter.is_file():
        raise RuntimeError(
            "Contextor MCP must run in a virtual environment, but the "
            f"project interpreter was not found: {interpreter}"
        )

    os.execv(
        str(interpreter),
        [str(interpreter), "-u", "-m", "contextor.mcp_main", *sys.argv[1:]],
    )
    raise RuntimeError("Contextor MCP virtual-environment re-exec returned unexpectedly.")


_ensure_virtual_environment()

# Suppress all warnings (like AuthlibDeprecationWarning) to prevent JSON-RPC stream corruption
warnings.filterwarnings("ignore")

from fastmcp import FastMCP
from contextor.mcp_process_registry import (
    process_identity,
    read_records,
    record_matches_process,
    register_process,
    registry_dir,
    remove_record,
    terminate_registered_process,
)
from contextor.mcp.documentation import short_description
from contextor.mcp.tools.get_artifact_blast_radius import (
    get_artifact_blast_radius as _get_artifact_blast_radius_impl,
)
from contextor.mcp.tools.search_artifacts import search_artifacts as _search_artifacts_impl
from contextor.mcp.tools.search_source import search_source as _search_source_impl
from contextor.mcp.tools.get_source_range import get_source_range as _get_source_range_impl
from contextor.mcp.tools.get_artifacts_for_module import (
    get_artifacts_for_module as _get_artifacts_for_module_impl,
)
from contextor.mcp.tools.lookup_artifact_by_symbol import (
    lookup_artifact_by_symbol as _lookup_artifact_by_symbol_impl,
)
from contextor.mcp.tools.analyze_project import analyze_project as _analyze_project_impl
from contextor.mcp.tools.analyze_layer import analyze_layer as _analyze_layer_impl
from contextor.mcp.tools.analyze_single_file import (
    analyze_single_file as _analyze_single_file_impl,
)
from contextor.mcp.tools.get_analysis_status import (
    get_analysis_status as _get_analysis_status_impl,
)
from contextor.mcp.tools.get_live_events import get_live_events as _get_live_events_impl
from contextor.mcp.tools.describe_canonical_state import (
    describe_canonical_state as _describe_canonical_state_impl,
)
from contextor.mcp.tools.get_mcp_documentation import (
    get_mcp_documentation as _get_mcp_documentation_impl,
)
from contextor.mcp.tools.lookup_index_entries import (
    lookup_index_entries as _lookup_index_entries_impl,
)
from contextor.mcp.tools.query_canonical_projection import (
    query_canonical_projection as _query_canonical_projection_impl,
)
from contextor.mcp.tools.get_project_architecture import (
    get_project_architecture as _get_project_architecture_impl,
)
from contextor.mcp.tools.get_module_context import (
    get_module_context as _get_module_context_impl,
)
from contextor.mcp.tools.get_file_edit_context import (
    get_file_edit_context as _get_file_edit_context_impl,
)
from contextor.mcp.tools.get_symbol_implementation import (
    get_symbol_implementation as _get_symbol_implementation_impl,
)
from contextor.mcp.tools.update_file import update_file as _update_file_impl
from contextor.mcp.tools.get_layer_isolation import (
    get_layer_isolation as _get_layer_isolation_impl,
)
from contextor.mcp.tools.get_report_diff import get_report_diff as _get_report_diff_impl
from contextor.mcp.tools.extract_indexed_report_context import (
    extract_indexed_report_context as _extract_indexed_report_context_impl,
)

# Initialize FastMCP Server
mcp = FastMCP("Contextor")

def _cleanup_orphaned_processes(directory: Path) -> None:
    """Stop only registered MCP/Git processes whose recorded parent is gone."""
    # Two passes handle a stale server and one of its Git children regardless
    # of filesystem iteration order: pass one stops the server, pass two the child.
    for _ in range(2):
        stopped_process = False
        for record_path, record in read_records(directory):
            if not record_matches_process(record):
                remove_record(record_path)
                continue
            try:
                parent_pid = int(record["parent_pid"])
            except (KeyError, TypeError, ValueError):
                remove_record(record_path)
                continue
            _, parent_creation_time, parent_alive = process_identity(parent_pid)
            expected_parent_creation = record.get("parent_creation_time")
            if expected_parent_creation is not None and parent_creation_time is not None:
                parent_alive = int(expected_parent_creation) == parent_creation_time
            if not parent_alive:
                stopped_process = terminate_registered_process(record) or stopped_process
                remove_record(record_path)
        if not stopped_process:
            break


def _cleanup_owned_processes(directory: Path, owner_pid: int) -> None:
    """Stop registered child processes still owned by this server."""
    for record_path, record in read_records(directory):
        try:
            is_child = int(record.get("parent_pid")) == owner_pid
        except (TypeError, ValueError):
            is_child = False
        if is_child:
            terminate_registered_process(record)
            remove_record(record_path)


# ==========================================================
# 1. ANALYSIS TRIGGER TOOLS
# ==========================================================

analyze_project = mcp.tool(description=short_description("analyze_project"))(
    _analyze_project_impl
)
analyze_layer = mcp.tool(description=short_description("analyze_layer"))(
    _analyze_layer_impl
)
analyze_single_file = mcp.tool(description=short_description("analyze_single_file"))(
    _analyze_single_file_impl
)
get_analysis_status = mcp.tool(description=short_description("get_analysis_status"))(
    _get_analysis_status_impl
)
get_live_events = mcp.tool(description=short_description("get_live_events"))(
    _get_live_events_impl
)


update_file = mcp.tool(description=short_description("update_file"))(
    _update_file_impl
)


# ==========================================================
# 2. QUERY LAYER (OPTIMIZED FOR LLM)
# ==========================================================

get_project_architecture = mcp.tool(description=short_description("get_project_architecture"))(
    _get_project_architecture_impl
)

get_module_context = mcp.tool(description=short_description("get_module_context"))(
    _get_module_context_impl
)
get_artifact_blast_radius = mcp.tool(description=short_description("get_artifact_blast_radius"))(
    _get_artifact_blast_radius_impl
)


search_artifacts = mcp.tool(description=short_description("search_artifacts"))(
    _search_artifacts_impl
)


get_symbol_implementation = mcp.tool(description=short_description("get_symbol_implementation"))(
    _get_symbol_implementation_impl
)

get_file_edit_context = mcp.tool(description=short_description("get_file_edit_context"))(
    _get_file_edit_context_impl
)

get_layer_isolation = mcp.tool(description=short_description("get_layer_isolation"))(
    _get_layer_isolation_impl
)

get_report_diff = mcp.tool(description=short_description("get_report_diff"))(
    _get_report_diff_impl
)


describe_canonical_state = mcp.tool(
    description=short_description("describe_canonical_state")
)(_describe_canonical_state_impl)


query_canonical_projection = mcp.tool(
    description=short_description("query_canonical_projection")
)(_query_canonical_projection_impl)


# ==========================================================
# 3. TARGETED INDEX / ARTIFACT QUERY TOOLS
# ==========================================================

extract_indexed_report_context = mcp.tool(
    description=short_description("extract_indexed_report_context")
)(_extract_indexed_report_context_impl)


lookup_index_entries = mcp.tool(
    description=short_description("lookup_index_entries")
)(_lookup_index_entries_impl)


get_artifacts_for_module = mcp.tool(description=short_description("get_artifacts_for_module"))(
    _get_artifacts_for_module_impl
)


lookup_artifact_by_symbol = mcp.tool(description=short_description("lookup_artifact_by_symbol"))(
    _lookup_artifact_by_symbol_impl
)

search_source = mcp.tool(description=short_description("search_source"))(
    _search_source_impl
)
get_source_range = mcp.tool(description=short_description("get_source_range"))(
    _get_source_range_impl
)


get_mcp_documentation = mcp.tool(
    description=short_description("get_mcp_documentation")
)(_get_mcp_documentation_impl)


def main():
    """Entry point for the MCP server."""
    # Ensure Windows IO encoding is UTF-8 to prevent charmap errors in JSON-RPC
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    import asyncio

    process_directory = registry_dir(Path.cwd().resolve())
    _cleanup_orphaned_processes(process_directory)
    server_record = register_process(
        process_directory,
        pid=os.getpid(),
        parent_pid=os.getppid(),
        kind="mcp-server",
        executable=sys.executable,
    )

    def _shutdown_cleanup() -> None:
        _cleanup_owned_processes(process_directory, os.getpid())
        remove_record(server_record)

    atexit.register(_shutdown_cleanup)

    transport = os.environ.get("CONTEXTOR_MCP_TRANSPORT", "stdio").lower()

    async def _run():
        if transport in {"http", "streamable-http"}:
            host = os.environ.get("CONTEXTOR_MCP_HOST", "127.0.0.1")
            port = int(os.environ.get("CONTEXTOR_MCP_PORT", "8765"))
            await mcp.run_http_async(
                transport="streamable-http",
                host=host,
                port=port,
                show_banner=False,
            )
        else:
            await mcp.run_stdio_async()
        
    asyncio.run(_run())


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
