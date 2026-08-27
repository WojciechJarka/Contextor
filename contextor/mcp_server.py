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

from typing import Any, Callable
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
from contextor.mcp.tools.get_symbol_call_context import (
    get_symbol_call_context as _get_symbol_call_context_impl,
)
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


def _resolve_telemetry_clients(root_path: Any = None) -> list[Any]:
    from pathlib import Path
    from contextor.core.live_state import connect
    from contextor.mcp import runtime as mcp_runtime

    clients = []
    seen_endpoints = set()

    def add_client(client):
        if client is not None:
            ep = getattr(client, "endpoint", None)
            ep_key = (ep.host, ep.port) if ep else id(client)
            if ep_key not in seen_endpoints:
                seen_endpoints.add(ep_key)
                clients.append(client)

    if root_path:
        try:
            p = Path(root_path).expanduser().resolve()
            add_client(connect(p))
        except Exception:
            pass

    if not clients:
        for root_str in sorted(mcp_runtime._live_engines.keys()):
            try:
                add_client(connect(Path(root_str)))
            except Exception:
                pass

        if not clients:
            try:
                add_client(connect(Path.cwd()))
            except Exception:
                pass

    return clients


def _emit_mcp_call_telemetry(
    tool_name: str,
    root_path: Any,
    success: bool,
    error: str | None = None,
) -> None:
    try:
        clients = _resolve_telemetry_clients(root_path)
        for client in clients:
            try:
                client.record_activity(
                    category="MCP_CALL",
                    tool=tool_name,
                    source="mcp",
                    success=success,
                    error=error,
                    message=f"{tool_name}" + (f" (failed: {error})" if not success else ""),
                )
            except Exception:
                pass
    except Exception:
        pass


def _instrument_mcp_tool(func: Any, tool_name: str) -> Any:
    import functools
    from inspect import iscoroutinefunction
    from pathlib import Path

    if iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            root_path = kwargs.get("repo_path") or kwargs.get("root_path") or (args[0] if args and isinstance(args[0], (str, Path)) else None)
            try:
                result = await func(*args, **kwargs)
                _emit_mcp_call_telemetry(tool_name, root_path, success=True)
                return result
            except Exception as exc:
                _emit_mcp_call_telemetry(tool_name, root_path, success=False, error=str(exc))
                raise
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            root_path = kwargs.get("repo_path") or kwargs.get("root_path") or (args[0] if args and isinstance(args[0], (str, Path)) else None)
            try:
                result = func(*args, **kwargs)
                _emit_mcp_call_telemetry(tool_name, root_path, success=True)
                return result
            except Exception as exc:
                _emit_mcp_call_telemetry(tool_name, root_path, success=False, error=str(exc))
                raise
        return sync_wrapper


def register_mcp_tool(
    func: Any,
    name: str | None = None,
    description: str | None = None,
) -> Any:
    tool_name = name or func.__name__
    desc = description or short_description(tool_name)
    wrapped = _instrument_mcp_tool(func, tool_name)
    return mcp.tool(name=tool_name, description=desc)(wrapped)


REGISTERED_MCP_TOOL_NAMES: tuple[str, ...] = (
    "analyze_project",
    "analyze_layer",
    "analyze_single_file",
    "get_analysis_status",
    "get_live_events",
    "update_file",
    "get_project_architecture",
    "get_module_context",
    "get_artifact_blast_radius",
    "search_artifacts",
    "get_symbol_implementation",
    "get_file_edit_context",
    "get_layer_isolation",
    "get_report_diff",
    "describe_canonical_state",
    "query_canonical_projection",
    "extract_indexed_report_context",
    "lookup_index_entries",
    "get_artifacts_for_module",
    "lookup_artifact_by_symbol",
    "search_source",
    "get_source_range",
    "get_symbol_call_context",
    "get_mcp_documentation",
)


# ==========================================================
# 1. ANALYSIS TRIGGER TOOLS
# ==========================================================

analyze_project = register_mcp_tool(_analyze_project_impl, name="analyze_project")
analyze_layer = register_mcp_tool(_analyze_layer_impl, name="analyze_layer")
analyze_single_file = register_mcp_tool(_analyze_single_file_impl, name="analyze_single_file")
get_analysis_status = register_mcp_tool(_get_analysis_status_impl, name="get_analysis_status")
get_live_events = register_mcp_tool(_get_live_events_impl, name="get_live_events")
update_file = register_mcp_tool(_update_file_impl, name="update_file")


# ==========================================================
# 2. QUERY LAYER (OPTIMIZED FOR LLM)
# ==========================================================

get_project_architecture = register_mcp_tool(_get_project_architecture_impl, name="get_project_architecture")
get_module_context = register_mcp_tool(_get_module_context_impl, name="get_module_context")
get_artifact_blast_radius = register_mcp_tool(_get_artifact_blast_radius_impl, name="get_artifact_blast_radius")
search_artifacts = register_mcp_tool(_search_artifacts_impl, name="search_artifacts")
get_symbol_implementation = register_mcp_tool(_get_symbol_implementation_impl, name="get_symbol_implementation")
get_file_edit_context = register_mcp_tool(_get_file_edit_context_impl, name="get_file_edit_context")
get_layer_isolation = register_mcp_tool(_get_layer_isolation_impl, name="get_layer_isolation")
get_report_diff = register_mcp_tool(_get_report_diff_impl, name="get_report_diff")
describe_canonical_state = register_mcp_tool(_describe_canonical_state_impl, name="describe_canonical_state")
query_canonical_projection = register_mcp_tool(_query_canonical_projection_impl, name="query_canonical_projection")


# ==========================================================
# 3. TARGETED INDEX / ARTIFACT QUERY TOOLS
# ==========================================================

extract_indexed_report_context = register_mcp_tool(_extract_indexed_report_context_impl, name="extract_indexed_report_context")
lookup_index_entries = register_mcp_tool(_lookup_index_entries_impl, name="lookup_index_entries")
get_artifacts_for_module = register_mcp_tool(_get_artifacts_for_module_impl, name="get_artifacts_for_module")
lookup_artifact_by_symbol = register_mcp_tool(_lookup_artifact_by_symbol_impl, name="lookup_artifact_by_symbol")
search_source = register_mcp_tool(_search_source_impl, name="search_source")
get_source_range = register_mcp_tool(_get_source_range_impl, name="get_source_range")
get_symbol_call_context = register_mcp_tool(_get_symbol_call_context_impl, name="get_symbol_call_context")
get_mcp_documentation = register_mcp_tool(_get_mcp_documentation_impl, name="get_mcp_documentation")


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
