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
import atexit
import json
import os
import subprocess
import sys
import glob
import warnings
import threading
from pathlib import Path
from typing import Any


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
        [str(interpreter), "-u", "-m", "contextor.mcp_server", *sys.argv[1:]],
    )
    raise RuntimeError("Contextor MCP virtual-environment re-exec returned unexpectedly.")


_ensure_virtual_environment()

# Suppress all warnings (like AuthlibDeprecationWarning) to prevent JSON-RPC stream corruption
warnings.filterwarnings("ignore")

from fastmcp import FastMCP
from contextor.core.api.facade import ContextorFacade
from contextor.core.report_query import (
    catalog_from_registry,
    filter_public_artifact_report,
    query_indexed_report as _query_indexed_report,
)
from contextor.mcp_process_registry import (
    process_identity,
    read_records,
    record_matches_process,
    register_process,
    registry_dir,
    remove_record,
    terminate_registered_process,
)

# Initialize FastMCP Server
mcp = FastMCP("Contextor")

# Global state to maintain incremental engines across MCP sessions
_live_engines: dict[str, Any] = {}
_analysis_lock = threading.Lock()


def _mcp_cache_root(root: Path) -> Path:
    """Writable cache root dedicated to MCP analysis of this repository."""
    return root / ".contextor" / "cache"



def _stderr_log(msg: str) -> None:
    """Redirects progress logs to stderr to protect JSON-RPC on stdout."""
    print(msg, file=sys.stderr, flush=True)


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


async def _run_analysis_worker(
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
) -> None:
    """Run analysis in-process without blocking the FastMCP event loop.

    Codex Desktop can start the child interpreter but leaves it stalled before
    Python reaches ``contextor.mcp_worker.main``.  The MCP-only sequential mode
    avoids both that child interpreter and nested process pools.
    """
    import asyncio

    def run() -> None:
        with _analysis_lock:
            previous_pool_setting = os.environ.get("CONTEXTOR_DISABLE_PROCESS_POOL")
            previous_cache = os.environ.get("CONTEXTOR_CACHE_DIR")
            previous_registry = os.environ.get("CONTEXTOR_MCP_PROCESS_REGISTRY")
            os.environ["CONTEXTOR_DISABLE_PROCESS_POOL"] = "1"
            os.environ["CONTEXTOR_CACHE_DIR"] = str(_mcp_cache_root(root))
            os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] = str(registry_dir(root))
            try:
                if operation == "project":
                    _, result = ContextorFacade.analyze_project(
                        str(root),
                        log=_stderr_log,
                        additional_excludes=exclude_paths,
                    )
                    if result is None:
                        raise RuntimeError("Analysis returned no canonical state.")
                elif operation == "layer":
                    ContextorFacade.analyze_layer(
                        str(root),
                        str(target),
                        log=_stderr_log,
                        additional_excludes=exclude_paths,
                    )
                elif operation == "single_file":
                    ContextorFacade.analyze_single_file(
                        str(target),
                        str(root),
                        log=_stderr_log,
                        additional_excludes=exclude_paths,
                    )
                else:
                    raise ValueError(f"Unsupported analysis operation: {operation}")
            finally:
                if previous_pool_setting is None:
                    os.environ.pop("CONTEXTOR_DISABLE_PROCESS_POOL", None)
                else:
                    os.environ["CONTEXTOR_DISABLE_PROCESS_POOL"] = previous_pool_setting
                if previous_cache is None:
                    os.environ.pop("CONTEXTOR_CACHE_DIR", None)
                else:
                    os.environ["CONTEXTOR_CACHE_DIR"] = previous_cache
                if previous_registry is None:
                    os.environ.pop("CONTEXTOR_MCP_PROCESS_REGISTRY", None)
                else:
                    os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] = previous_registry

    await asyncio.to_thread(run)


def _get_canonical_report(repo_path: Path, filename: str) -> Path | None:
    """Returns the canonical report path without globbing."""
    out_dir = repo_path / "output"
    target = out_dir / filename
    if target.is_file():
        return target
    # Check for layer-specific subdirectories if not found in root output
    for sub in out_dir.iterdir():
        if sub.is_dir():
            sub_target = sub / filename
            if sub_target.is_file():
                return sub_target
    return None

def _get_or_init_engine(root: Path):
    """
    Returns the live engine from RAM. If absent, HYDRATES from the .contextor cache.
    Does NOT silently trigger analyze_project.
    """
    engine = _live_engines.get(str(root))
    if not engine:
        from contextor.core.analysis.state_manager import load_engine_state, FileStateManager
        from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
        from contextor.core.paths import repo_key
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
        
        cache_dir = str(_mcp_cache_root(root) / repo_key(root))
        state_mgr = FileStateManager(cache_dir)
        state = load_engine_state(cache_dir, getattr(state_mgr, "state_id", ""))
        if state:
            registry = PersistentIdentityRegistry(str(root))
            engine = IncrementalAnalysisEngine(state, registry, state_mgr, str(root))
            _live_engines[str(root)] = engine
    return engine


def _persist_live_engine(root: Path, engine) -> bool:
    """Persist incremental canonical state so the next MCP process can hydrate it."""

    from contextor.core.analysis.state_manager import save_engine_state
    from contextor.core.paths import repo_key

    cache_dir = _mcp_cache_root(root) / repo_key(root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return bool(
        save_engine_state(
            engine.state,
            str(cache_dir),
            getattr(engine.state_manager, "state_id", ""),
        )
    )


def _read_registries(
    root: Path,
) -> tuple[dict, dict, dict, dict]:
    """
    Reads module and artifact registries from the persistent identity store.

    Returns:
        (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path)
    """
    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    registry = PersistentIdentityRegistry(str(root))
    with registry.transaction():
        mod_reg = registry._state.get("module_registry", {})
        art_reg = registry._state.get("artifact_registry", {})
    return (
        mod_reg.get("path_to_id", {}),
        mod_reg.get("id_to_path", {}),
        art_reg.get("path_to_id", {}),
        art_reg.get("id_to_path", {}),
    )


def _semantic_artifact_diff(old_artifacts: dict, new_artifacts: dict) -> dict:
    """Return a compact, JSON-safe semantic delta from cached symbol facts."""
    old_symbols = old_artifacts.get("symbols", {}) if old_artifacts else {}
    new_symbols = new_artifacts.get("symbols", {}) if new_artifacts else {}

    def names(symbols: dict) -> set[str]:
        return {
            str(name)
            for category in ("classes", "functions", "methods", "globals")
            for name in symbols.get(category, [])
        }

    old_names = names(old_symbols)
    new_names = names(new_symbols)
    old_signatures = old_symbols.get("signatures", {}) or {}
    new_signatures = new_symbols.get("signatures", {}) or {}
    old_bodies = old_symbols.get("body_fingerprints", {}) or {}
    new_bodies = new_symbols.get("body_fingerprints", {}) or {}
    changed_signatures = {
        name: {"before": old_signatures[name], "after": new_signatures[name]}
        for name in sorted(old_names & new_names)
        if old_signatures.get(name) != new_signatures.get(name)
    }
    changed_bodies = sorted(
        name
        for name in old_names & new_names & old_bodies.keys() & new_bodies.keys()
        if old_bodies[name] != new_bodies[name]
    )

    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    affected = sorted(
        set(added) | set(removed) | set(changed_signatures) | set(changed_bodies)
    )
    return {
        "symbols_added": added,
        "symbols_removed": removed,
        "signatures_changed": changed_signatures,
        "bodies_changed": changed_bodies,
        "body_change_count": len(changed_bodies),
        "affected_symbols": affected,
        "changed_symbol_count": len(affected),
        "body_only_changes_tracked": True,
    }


def _bounded_items(items: list, limit: int) -> tuple[list, int, bool]:
    """Bound an MCP collection while preserving its total cardinality."""
    total = len(items)
    safe_limit = max(0, min(int(limit), 500))
    selected = items[:safe_limit]
    return selected, total, total > len(selected)


def _bounded_query_result(value, limit: int) -> dict:
    """Wrap and bound a top-level canonical-state query result."""
    if isinstance(value, dict):
        selected, total, truncated = _bounded_items(list(value.items()), limit)
        result = dict(selected)
        result_type = "dict"
    elif isinstance(value, (list, tuple, set)):
        selected, total, truncated = _bounded_items(list(value), limit)
        result = selected
        result_type = type(value).__name__
    else:
        result = value
        total = 1
        truncated = False
        result_type = type(value).__name__
    return {
        "result": result,
        "result_type": result_type,
        "total_items": total,
        "truncated": truncated,
    }


def _resolve_cluster_ids(
    cluster: dict,
    module_names: dict,
    artifact_names: dict,
) -> dict:
    """Make one analytics cluster directly readable by an LLM."""
    resolved = dict(cluster)
    resolved["modules"] = [
        module_names.get(str(item), str(item))
        for item in cluster.get("modules", [])
    ]
    resolved["shared_artifact_keys"] = [
        artifact_names.get(str(item), str(item))
        for item in cluster.get("shared_artifact_keys", [])
    ]
    resolved["ids_resolved"] = True
    return resolved


# ==========================================================
# 1. ANALYSIS TRIGGER TOOLS
# ==========================================================

@mcp.tool()
async def analyze_project(
    repo_path: str, exclude_paths: list[str] | None = None
) -> str:
    """
    Triggers a global architectural analysis on the specified repository.
    Generates all reports in the 'output' directory.

    ``exclude_paths`` lets an LLM narrow this run without changing the saved
    GUI exclude configuration. Use repository-relative Python files or
    directory prefixes, for example ``["tests", "legacy/adapter.py"]``.
    Contextor already ignores non-Python files. Per-run and GUI excludes are
    combined before AST indexing.

    LLM use: choose this for a repository-wide baseline. Exclude ``tests``
    when production architecture is the only concern; keep it when later
    queries need test coverage or ``tests_covering`` evidence.
    """
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    try:
        await _run_analysis_worker("project", root, exclude_paths=exclude_paths)
        _live_engines.pop(str(root), None)
        if _get_or_init_engine(root) is None:
            raise RuntimeError("Analysis completed but canonical state could not be loaded.")
        
        return f"Analysis complete for {root.name}."
    except Exception as e:
        return f"Error during analysis: {str(e)}"

@mcp.tool()
async def analyze_layer(
    repo_path: str,
    layer_name: str,
    exclude_paths: list[str] | None = None,
) -> str:
    """
    Triggers architectural analysis isolated to a specific layer (directory).

    ``exclude_paths`` contains repository-relative Python files or directory
    prefixes to omit from this run. It is merged with, but never persisted to,
    the GUI exclude list. Non-Python files are ignored automatically.

    LLM use: prefer this over a global run when the decision is confined to one
    package. Exclude unrelated Python trees to reduce report size, but retain
    tests when boundary or coverage evidence matters.
    """
    root = Path(repo_path).expanduser().resolve()
    layer = root / layer_name
    if not layer.is_dir():
        return f"Error: Layer path '{layer}' does not exist."
    try:
        await _run_analysis_worker(
            "layer", root, layer, exclude_paths=exclude_paths
        )
        return f"Layer analysis complete for '{layer_name}'."
    except Exception as e:
        return f"Error during layer analysis: {str(e)}"

@mcp.tool()
async def analyze_single_file(
    repo_path: str,
    file_path: str,
    exclude_paths: list[str] | None = None,
) -> str:
    """
    Triggers deep architectural analysis on a single Python file.

    ``exclude_paths`` narrows the surrounding project context for this run.
    Entries are repository-relative Python files or directory prefixes and are
    combined with the saved GUI excludes without modifying them. Do not exclude
    the target file itself.

    LLM use: choose this for a focused symbol/API decision. Exclude unrelated
    packages to save tokens; retain relevant tests when test discovery is part
    of the question.
    """
    root = Path(repo_path).expanduser().resolve()
    target_file = Path(file_path).expanduser()
    if not target_file.is_absolute():
        target_file = root / target_file
    target_file = target_file.resolve()
    if not target_file.is_file():
        return f"Error: Target file '{target_file}' does not exist."
    try:
        await _run_analysis_worker(
            "single_file", root, target_file, exclude_paths=exclude_paths
        )
        return f"Single-file analysis complete for {target_file.name}."
    except Exception as e:
        return f"Error during single-file analysis: {str(e)}"


@mcp.tool()
def update_file(repo_path: str, file_path: str) -> str:
    """
    [OPTIMIZED] Incremental architectural update for a modified file.
    Updates the canonical state and graph structure in real-time.
    Requires `analyze_project` to have been run at least once during this session.

    LLM use: call this after each edit instead of rebuilding every report. Read
    ``semantic_diff`` for added/removed symbols and signature changes, then use
    normal code diff for line-level meaning. ``bodies_changed`` uses normalized
    AST fingerprints to flag body-only edits without sending body text; it does
    not explain their meaning. Consumption/global metrics may be deferred.
    """
    root = Path(repo_path).expanduser().resolve()
    target_file = Path(file_path).expanduser()
    if not target_file.is_absolute():
        target_file = root / target_file
    target_file = target_file.resolve()
    
    engine = _get_or_init_engine(root)
            
    if not engine:
        return json.dumps({"status": "NO_SESSION", "file_path": str(target_file), "error": "Run analyze_project first to initialize the session."}, indent=2)
        
    try:
        rel_path = target_file.relative_to(root)
        module_path = ".".join(rel_path.with_suffix("").parts)
        old_artifacts = engine.state.artifacts.get(module_path, {})
        res = engine.update_file(str(target_file))
        live_state_persisted = (
            _persist_live_engine(root, engine)
            if res.status in {"UPDATED", "DELETED"}
            else True
        )
        new_artifacts = engine.state.artifacts.get(module_path, {})
        result = {
            "status": res.status,
            "file_path": res.file_path,
            "graph_state": res.graph_state,
            "dependencies_state": res.dependencies_state,
            "blast_radius_state": res.blast_radius_state,
            "local_metrics_state": res.local_metrics_state,
            "global_metrics_state": res.global_metrics_state,
            "artifact_consumption_state": res.artifact_consumption_state,
            "live_state_persisted": live_state_persisted,
            "semantic_diff": _semantic_artifact_diff(old_artifacts, new_artifacts),
        }
        if res.delta:
            result["delta"] = {
                "module_path": res.delta.module_path,
                "is_new": res.delta.is_new,
                "is_deleted": res.delta.is_deleted,
                "imports_added": res.delta.imports_added,
                "imports_removed": res.delta.imports_removed,
                "artifacts_added": res.delta.artifacts_added,
                "artifacts_removed": res.delta.artifacts_removed
            }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "file_path": str(target_file), "error": str(e)}, indent=2)


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
    
    summary_path = _get_canonical_report(root, f"{repo_name}_summary.json")
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
def get_project_index(repo_path: str) -> str:
    """
    [OPTIMIZED] Returns the mapping of internal repository IDs to their actual paths.
    Use this to translate IDs (e.g., '17/4') found in reports back to file paths or artifact names.
    """
    root = Path(repo_path).expanduser().resolve()
    try:
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
        registry = PersistentIdentityRegistry(str(root))
        with registry.transaction():
            modules = registry._state.get("module_registry", {}).get("id_to_path", {})
            artifacts = registry._state.get("artifact_registry", {}).get("id_to_path", {})
            
        result = {
            "modules": modules,
            "artifacts": artifacts
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error reading project index: {e}"


@mcp.tool()
def get_module_context(repo_path: str, module_name: str) -> str:
    """
    [OPTIMIZED] Retrieves a compressed context pill for a single module.
    Returns its layer, visibility, metrics (fan_in/out, pagerank), and its direct inbound/outbound dependencies.
    Use this right before editing a file to understand its blast radius and requirements.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    ga_path = _get_canonical_report(root, f"{repo_name}_graph_analytics.json")
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
        
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
        registry = PersistentIdentityRegistry(str(root))
        with registry.transaction():
            mod_id = registry.get_module_id(module_name)
            
            if mod_id and str(mod_id) in matrix:
                for target_id, dep_data in matrix[str(mod_id)].items():
                    target_name = registry.get_module_path(target_id) or target_id
                    outbound[target_name] = dep_data
                    
            for src_id, targets in matrix.items():
                if str(mod_id) in targets:
                    src_name = registry.get_module_path(src_id) or src_id
                    inbound[src_name] = targets[str(mod_id)]
        
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
    [OPTIMIZED] Resolves direct, evidence-backed consumers of an artifact.
    Uses the current compact artifact report and reports its evidence scope;
    it does not claim that dynamic Python usage can be proven exact.

    LLM use: call before changing or removing a public symbol. Treat consumers
    as confirmed static evidence, not proof that dynamic Python has no callers.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    try:
        _, mod_id_to_path, _, art_id_to_path = _read_registries(root)
        candidates = [
            (art_id, full_name)
            for art_id, full_name in art_id_to_path.items()
            if full_name == artifact_name
            or full_name.endswith("::" + artifact_name)
        ]
        if not candidates:
            return f"Artifact '{artifact_name}' not found in the registry."

        art_path = _get_canonical_report(root, f"{repo_name}_artifacts_compact.json")
        if not art_path:
            return "Error: No current artifacts_compact report. Run analyze_project first."
        artifacts = json.loads(art_path.read_text(encoding="utf-8")).get("artifacts", {})
        current = [item for item in candidates if item[0] in artifacts]
        if not current:
            return f"Artifact '{artifact_name}' is not present in the current artifact report."
        art_id, full_name = sorted(current, key=lambda item: item[1])[0]
        art_data = artifacts[art_id]
        definer_id = str(art_data.get("definer_module", ""))
        consumer_ids = art_data.get("consumer_module_indices", [])

        result = {
            "artifact": full_name,
            "artifact_id": art_id,
            "kind": art_data.get("kind"),
            "definer": mod_id_to_path.get(definer_id, definer_id),
            "consumer_count": len(consumer_ids),
            "consumers": [mod_id_to_path.get(item, item) for item in consumer_ids],
            "evidence_scope": "direct_static_artifact_consumption",
            "data_source": "current_artifacts_compact",
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error calculating artifact blast radius: {e}"


@mcp.tool()
def search_artifacts(
    repo_path: str,
    search_term: str,
    limit: int = 20,
) -> str:
    """
    [OPTIMIZED] Searches the canonical live state for an artifact, module, or symbol matching 'search_term'.
    Returns its properties and all its dependencies and consumers (blast radius).
    Use this to extract arbitrary context about any symbol from the current architectural state.
    Exact symbol matches are preferred. ``limit``, ``total_matches`` and
    ``truncated`` bound broad searches without hiding their cardinality.

    LLM use: start here when only a partial symbol/module name is known. Keep
    the default limit, inspect ``truncated``, and narrow the term before raising
    the limit to avoid loading irrelevant canonical state.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    engine = _get_or_init_engine(root)
    if not engine:
        return "Error: No live canonical state found. Run analyze_project first."
        
    try:
        found_artifacts = []
        found_modules = []
        kind_by_category = {
            "functions": "function",
            "classes": "class",
            "methods": "method",
            "globals": "global",
        }
        module_paths = sorted(
            set(getattr(engine.state, "modules", {}))
            | set(engine.state.artifacts)
        )
        for mod_path in module_paths:
            module_leaf = mod_path.rsplit(".", 1)[-1]
            if search_term.casefold() in mod_path.casefold():
                graph = engine.state.dependency_graph
                inbound = []
                outbound = []
                if graph is not None:
                    hard_edges = getattr(graph, "hard_edges", {})
                    soft_edges = getattr(graph, "soft_edges", {})
                    outbound = sorted(
                        set(hard_edges.get(mod_path, set()))
                        | set(soft_edges.get(mod_path, set()))
                    )
                    inbound = sorted(
                        source
                        for source in set(hard_edges) | set(soft_edges)
                        if mod_path
                        in (
                            set(hard_edges.get(source, set()))
                            | set(soft_edges.get(source, set()))
                        )
                    )
                exact_module = search_term.casefold() in {
                    mod_path.casefold(),
                    module_leaf.casefold(),
                }
                found_modules.append(
                    (
                        not exact_module,
                        mod_path.casefold(),
                        mod_path,
                        {
                            "kind": "module",
                            "module_id": engine.registry.get_module_id(mod_path),
                            "dependencies_inbound": inbound,
                            "dependencies_outbound": outbound,
                        },
                    )
                )
        for mod_path, mod_arts in engine.state.artifacts.items():
            symbols = mod_arts.get("symbols", {})
            for category, kind in kind_by_category.items():
                raw_names = symbols.get(category, [])
                names = raw_names.keys() if isinstance(raw_names, dict) else raw_names
                for raw_name in names:
                    name = str(raw_name)
                    if search_term.lower() in name.lower():
                        definer_mod = engine.registry.get_module_id(mod_path)
                        consumers_dict = mod_arts.get("consumers", {}).get(name, {})
                        if isinstance(consumers_dict, dict):
                            consumers = consumers_dict.get("consumers", [])
                        else:
                            consumers = consumers_dict if isinstance(consumers_dict, list) else []

                        consumer_paths = [
                            engine.registry.get_module_path(str(c)) or str(c)
                            for c in consumers
                        ]

                        found_artifacts.append((name.lower() != search_term.lower(), name.lower(), f"{mod_path}::{name}", {
                            "kind": kind,
                            "definer_module_path": mod_path,
                            "definer_module_id": definer_mod,
                            "consumer_count": len(consumers),
                            "consumers": consumer_paths,
                        }))

        if not found_artifacts and not found_modules:
            return f"No live modules or artifacts found matching '{search_term}'."

        found_artifacts.sort()
        found_modules.sort()
        all_found = [
            (item[0], item[1], "artifact", item[2], item[3])
            for item in found_artifacts
        ] + [
            (item[0], item[1], "module", item[2], item[3])
            for item in found_modules
        ]
        all_found.sort()
        if not all_found[0][0]:
            all_found = [item for item in all_found if not item[0]]
        selected, total, truncated = _bounded_items(all_found, limit)
        selected_artifacts = [item for item in selected if item[2] == "artifact"]
        selected_modules = [item for item in selected if item[2] == "module"]
        return json.dumps({
            "query": search_term,
            "match_count": len(selected),
            "total_matches": total,
            "truncated": truncated,
            "modules": {item[3]: item[4] for item in selected_modules},
            "artifacts": {item[3]: item[4] for item in selected_artifacts},
        }, indent=2)
    except Exception as e:
        return f"Error extracting artifact context from live state: {e}"

@mcp.tool()
def get_file_edit_context(
    repo_path: str,
    file_path: str,
    max_items: int = 30,
) -> str:
    """
    [OPTIMIZED] Specialized single-shot context pill for LLMs prior to editing a file.
    Combines module metrics, API signature blast radius, and dependency trees into one response.
    Returns: file, module, public_api, imports, consumers, risk_score, tests_covering.

    Collections are bounded by ``max_items`` (default 30) to protect the LLM
    context window. Every bounded collection includes ``*_total`` and
    ``*_truncated`` metadata. Increase ``max_items`` only when the totals show
    that the omitted tail is relevant to the current decision.

    LLM use: this is the preferred one-call briefing immediately before editing
    a file. It complements, but does not replace, the source and code diff.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    # Deriving module name from file path
    target_path = Path(file_path).expanduser()
    if target_path.is_absolute():
        try:
            rel_path = target_path.relative_to(root)
        except ValueError:
            rel_path = target_path
    else:
        rel_path = target_path
        target_path = root / target_path

    parts = list(rel_path.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts.pop()
    
    module_name = ".".join(parts)
    
    ga_path = _get_canonical_report(root, f"{repo_name}_graph_analytics.json")
    art_path = _get_canonical_report(root, f"{repo_name}_artifacts_compact.json")
    
    if not (ga_path and art_path):
        return "Error: Missing required reports. Run analyze_project first."
        
    try:
        ga = json.loads(ga_path.read_text(encoding="utf-8"))
        art_comp = json.loads(art_path.read_text(encoding="utf-8"))
        
        mod_info = ga.get("modules", {}).get(module_name, {})
        
        # Prefer real hotspot score from summary.json, fall back to centrality proxy
        risk_score = 0.0
        summary_path = _get_canonical_report(root, f"{repo_name}_summary.json")
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
        
        # We must read registries OUTSIDE the transaction block to avoid Resource Deadlock
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)
        mod_id = mod_path_to_id.get(module_name)
        if not mod_id:
            return f"Error: Module '{module_name}' is not present in the current registry."
            
        imports = []
        consumers = []
        dependency_data_source = "saved_graph_analytics"
        artifact_data_source = "saved_artifacts_compact"
        matrix = ga.get("module_dependency_matrix", {})
        engine = _get_or_init_engine(root)
        live_graph = engine.state.dependency_graph if engine else None
        if engine and module_name in engine.state.modules and live_graph:
            target_modules = set(live_graph.hard_edges.get(module_name, set()))
            target_modules.update(live_graph.soft_edges.get(module_name, set()))
            imports = [
                mod_path_to_id[target]
                for target in sorted(target_modules)
                if target in mod_path_to_id
            ]
            consumer_modules = {
                source
                for edge_map in (live_graph.hard_edges, live_graph.soft_edges)
                for source, targets in edge_map.items()
                if module_name in targets
            }
            consumers = [
                mod_path_to_id[source]
                for source in sorted(consumer_modules)
                if source in mod_path_to_id
            ]
            dependency_data_source = "live_canonical_graph"
        else:
            if mod_id in matrix:
                imports.extend(matrix[mod_id].keys())
            for src_id, targets in matrix.items():
                if mod_id in targets:
                    consumers.append(src_id)
                        
        # Resolve public API artifact IDs to human-readable names so an
        # LLM does not need a separate lookup_index_entries call.
        public_api = {}
        unresolved_public_api_ids = []
        if engine and module_name in engine.state.artifacts:
            prefix = module_name + "::"
            for full_name, art_id in sorted(art_path_to_id.items()):
                if not full_name.startswith(prefix):
                    continue
                local_name = full_name.split("::", 1)[-1]
                leaf = local_name.rsplit(".", 1)[-1]
                if leaf.startswith("_") and not (
                    leaf.startswith("__") and leaf.endswith("__")
                ):
                    continue
                public_api[str(art_id)] = full_name
            artifact_data_source = "live_registry_and_symbol_state"
        elif "module_artifacts" in art_comp and mod_id in art_comp["module_artifacts"]:
            for art_id in art_comp["module_artifacts"][mod_id]:
                resolved = art_id_to_path.get(str(art_id))
                if resolved:
                    public_api[str(art_id)] = resolved
                else:
                    unresolved_public_api_ids.append(str(art_id))
        else:
            for art_id, art_data in art_comp.get("artifacts", {}).items():
                if str(art_data.get("definer_module")) == mod_id:
                    resolved = art_id_to_path.get(str(art_id))
                    if resolved:
                        public_api[str(art_id)] = resolved
                    else:
                        unresolved_public_api_ids.append(str(art_id))
        
        # tests_covering: test modules depend on this one, we can check prefix from paths if needed, 
        # but since we only have IDs, we look up the path for the prefix check but keep the ID.
        tests_covering = []
        for c in consumers:
            c_path = mod_id_to_path.get(c, "")
            if c_path.startswith("tests."):
                tests_covering.append({"module_id": c, "module": c_path})

        public_api_items, public_api_total, public_api_truncated = _bounded_items(
            sorted(public_api.items()), max_items
        )
        import_items, imports_total, imports_truncated = _bounded_items(
            sorted(imports), max_items
        )
        consumer_items, consumers_total, consumers_truncated = _bounded_items(
            sorted(consumers), max_items
        )
        test_items, tests_total, tests_truncated = _bounded_items(
            tests_covering, max_items
        )
        
        result = {
            "file": file_path,
            "file_exists": target_path.is_file(),
            "module": module_name,
            "module_id": mod_id,
            "layer": mod_info.get("layer", "unknown"),
            "entrypoint": mod_info.get("entrypoint", False),
            "public_api": dict(public_api_items),
            "public_api_total": public_api_total,
            "public_api_truncated": public_api_truncated,
            "unresolved_public_api_ids": sorted(set(unresolved_public_api_ids)),
            "imports": [
                {"module_id": item, "module": mod_id_to_path.get(item)}
                for item in import_items
            ],
            "imports_total": imports_total,
            "imports_truncated": imports_truncated,
            "consumers": [
                {"module_id": item, "module": mod_id_to_path.get(item)}
                for item in consumer_items
            ],
            "consumers_total": consumers_total,
            "consumers_truncated": consumers_truncated,
            "risk_score": risk_score,
            "dependency_data_source": dependency_data_source,
            "artifact_data_source": artifact_data_source,
            "tests_covering": {
                "available": tests_total > 0,
                "total": tests_total,
                "truncated": tests_truncated,
                "tests": test_items,
            }
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting file edit context: {e}"


@mcp.tool()
def get_layer_isolation(
    repo_path: str,
    layer_name: str,
    max_clusters: int = 8,
    max_boundary_violations: int = 10,
) -> str:
    """
    [OPTIMIZED] Extracts isolation metrics, clusters, and leaks for a specific architectural layer.
    Use this before refactoring a large component to understand its internal cohesion.

    ``max_clusters`` and ``max_boundary_violations`` bound verbose evidence.
    The response always retains full counts and explicit ``*_truncated`` flags,
    so an LLM can request a larger limit without loading everything by default.

    LLM use: call before moving modules or changing layer boundaries. Resolve a
    truncated tail only when the planned edit touches that omitted evidence.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    # Normalize layer_name in case user passes a path like "contextor/core"
    normalized_layer_name = Path(layer_name).name
    
    # Try to find layer-specific report in high_risk_layers
    ga_path = _get_canonical_report(root, f"{repo_name}_{normalized_layer_name}_graph_analytics.json")
    if not ga_path:
        # Fallback to global summary if layer report doesn't exist
        summary_path = _get_canonical_report(root, f"{repo_name}_summary.json")
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
        
        # Resolve only the IDs exposed by this bounded response.
        _, id_to_name, _, artifact_id_to_name = _read_registries(root)
        
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
        
        clusters, cluster_count, clusters_truncated = _bounded_items(
            ga.get("shared_usage_clusters", []), max_clusters
        )
        clusters = [
            _resolve_cluster_ids(cluster, id_to_name, artifact_id_to_name)
            for cluster in clusters
        ]
        violations, violation_count, violations_truncated = _bounded_items(
            boundary_violations, max_boundary_violations
        )
        result = {
            "layer": normalized_layer_name,
            "module_count": ga.get("module_count", 0),
            "clusters": clusters,
            "cluster_count": cluster_count,
            "clusters_truncated": clusters_truncated,
            "dependency_types": ga.get("dependency_type_breakdown", {}),
            "boundary_violations": violations,
            "boundary_violations_count": violation_count,
            "boundary_violations_truncated": violations_truncated,
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

    diff_path = _get_canonical_report(root, f"{repo_name}_report_diff.json")
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
def query_canonical_state(repo_path: str, python_filter_expression: str) -> str:
    """
    [ADVANCED] Allows you to run a safe Python list-comprehension or filter on the LIVE canonical state!
    The live objects are loaded into variables: 'modules', 'artifacts', 'dependency_graph', 'registry'.
    Example expression: "[m_path for m_path, mod in modules.items() if len(mod.imports) > 20]"
    """
    root = Path(repo_path).expanduser().resolve()
    engine = _get_or_init_engine(root)
    
    if not engine:
        return f"Error: No live canonical state found for {root}. Run analyze_project first."
        
    try:
        # Safe sandbox: only whitelisted builtins, no import/exec/open
        _safe_builtins = {
            "__builtins__": {},
            "modules": engine.state.modules,
            "artifacts": engine.state.artifacts,
            "dependency_graph": engine.state.dependency_graph,
            "registry": engine.registry,
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
        
        # Serialize result safely, handling dataclasses if needed
        import dataclasses
        class SafeEncoder(json.JSONEncoder):
             def default(self, o):
                 if dataclasses.is_dataclass(o):
                     return dataclasses.asdict(o)
                 if hasattr(o, "to_dict"):
                     return o.to_dict()
                 if isinstance(o, set):
                     return list(o)
                 return str(o)
                 
        return json.dumps(result, indent=2, cls=SafeEncoder)
    except Exception as e:
        return f"Error executing query: {str(e)}"


@mcp.tool()
def query_canonical_state_bounded(
    repo_path: str,
    python_filter_expression: str,
    limit: int = 100,
) -> str:
    """
    [OPTIMIZED] Runs the same restricted expression as
    ``query_canonical_state`` but bounds top-level list/dict results.

    Prefer this tool for exploration. The response includes ``total_items``
    and ``truncated`` so an LLM can refine the expression or raise ``limit``
    only when omitted items matter. Select narrow scalar fields in the
    expression when individual nested values may themselves be large.

    LLM use: use this as an escape hatch for questions not covered by a
    dedicated tool. Prefer projected scalar fields and a small limit; it is a
    structural query, not a substitute for reading the affected source.
    """
    raw = query_canonical_state.fn(
        repo_path=repo_path,
        python_filter_expression=python_filter_expression,
    )
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw
    return json.dumps(_bounded_query_result(value, limit), indent=2)


# ==========================================================
# 3. TARGETED INDEX / ARTIFACT QUERY TOOLS
# ==========================================================

@mcp.tool()
def extract_indexed_report_context(
    repo_path: str,
    query: str,
    report_path: str = "",
    resolve_indices: bool = True,
    public_api_only: bool = False,
) -> str:
    """
    [OPTIMIZED] Extracts complete matching blocks from an indexed artifact report.

    Resolution is index-first and shared with the GUI parser. Queries may use an
    artifact/module ID, a ``.py`` path, a full ``module::symbol`` key, or explicit
    ``file:``, ``module:``, ``symbol:`` and ``artifact:`` prefixes. Exact matches
    are never replaced by fuzzy guesses; ambiguous and missing queries remain
    explicit. Active dictionaries fall back to both recovery dictionaries, while
    blocks with unresolved artifact or definer IDs are omitted with diagnostics.

    Omit ``report_path`` to read the current compact artifact report. Every matched
    block is returned in full, including nested objects; results are never silently
    sampled or truncated.

    Set ``public_api_only=True`` to mirror the GUI checkbox: private names are
    excluded, but zero detected consumers do not make an artifact private.

    LLM use: prefer this over reading a whole compact JSON when one file, symbol, or
    ID is relevant. Inspect resolution/diagnostics and narrow an ambiguous query;
    do not treat suggestions as confirmed matches.
    """
    root = Path(repo_path).expanduser().resolve()
    try:
        if report_path:
            selected_path = Path(report_path).expanduser()
            if not selected_path.is_absolute():
                selected_path = root / selected_path
            selected_path = selected_path.resolve()
        else:
            selected_path = _get_canonical_report(
                root, f"{root.name}_artifacts_compact.json"
            )
        if not selected_path or not selected_path.is_file():
            return "Error: No indexed artifact report found. Run analysis or pass report_path."

        report = json.loads(selected_path.read_text(encoding="utf-8"))
        engine = _get_or_init_engine(root)
        module_paths = None
        if engine:
            module_paths = {
                str(module_name): str(module.path)
                for module_name, module in engine.state.modules.items()
                if getattr(module, "path", None)
            }
        catalog = catalog_from_registry(str(root), module_paths=module_paths)
        if public_api_only:
            report = filter_public_artifact_report(report, catalog)
        result = _query_indexed_report(
            report,
            query,
            catalog,
            repo_root=str(root),
            resolve_indices=resolve_indices,
        )
        result["total_artifact_count"] = result["artifact_count"]
        result["truncated"] = False
        result["data_source"] = str(selected_path)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error extracting indexed report context: {e}"


@mcp.tool()
def lookup_index_entries(repo_path: str, ids: list[str]) -> str:
    """
    [OPTIMIZED] Resolves a specific list of compact IDs to their full names.

    Use this instead of get_project_index when you only need to decode a
    handful of IDs found in a report (e.g. from module_dependency_matrix or
    shared_usage_clusters).  Much cheaper than loading the entire registry.

    Accepts both module IDs (e.g. '124/1') and artifact IDs (e.g. 'A35/1').
    Each ID resolves to ``{"name": ..., "status": "active|recovery|missing"}``
    so stale identities are distinguishable from malformed or unknown IDs.

    LLM use: pass only IDs visible in the current result instead of loading the
    full project dictionary. Recovery means a known historical identity and
    must not be presented as an active symbol; missing means no known identity.
    """
    root = Path(repo_path).expanduser().resolve()
    try:
        catalog = catalog_from_registry(str(root))
        result = {}
        for id_ in ids:
            normalized_id = str(id_)
            if normalized_id.upper().startswith("A"):
                normalized_id = normalized_id.upper()
                active = catalog.artifacts
                recovery = catalog.recovered_artifacts or {}
            else:
                active = catalog.modules
                recovery = catalog.recovered_modules or {}
            if normalized_id in active:
                entry = {"name": active[normalized_id], "status": "active"}
            elif normalized_id in recovery:
                entry = {"name": recovery[normalized_id], "status": "recovery"}
            else:
                entry = {"name": None, "status": "missing"}
            result[str(id_)] = entry
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error resolving index entries: {e}"


@mcp.tool()
def get_artifacts_for_module(
    repo_path: str,
    module_name: str,
    include_consumers: bool = True,
    symbol_filter: str = "",
    limit: int = 50,
) -> str:
    """
    [OPTIMIZED] Returns all artifacts exported by a module with consumer info.

    Equivalent to the GUI parser window — shows what a module defines and
    who uses each artifact across the project.

    ``module_name`` can be:
    - A full dotted module name: 'contextor.ui.gui_parser'
    - A file path relative to the repo root: 'contextor/ui/gui_parser.py'

    Set ``include_consumers=False`` for a compact signatures-only view.

    Use ``symbol_filter`` to select a name substring and ``limit`` to bound the
    result. ``total_artifact_count`` reports matches before limiting and
    ``truncated`` tells the LLM whether a narrower follow-up query is useful.
    Live state supplements the compact report with zero-consumer symbols.

    LLM use: call before changing one module's API. Disable consumers for the
    cheapest signature inventory; enable them only for impact analysis.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    # Normalise file-path input to dotted module name.
    target_path = Path(module_name)
    if target_path.is_absolute() or module_name.endswith(".py") or "/" in module_name or "\\" in module_name:
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

    art_path = _get_canonical_report(root, f"{repo_name}_artifacts_compact.json")
    if not art_path:
        return "Error: No artifacts_compact report found. Run analyze_project first."

    try:
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)

        mod_compact_id = mod_path_to_id.get(module_name)
        if not mod_compact_id:
            return (
                f"Module '{module_name}' not found in registry. "
                "Check the module name or run analyze_project."
            )

        art_comp = json.loads(art_path.read_text(encoding="utf-8"))
        artifacts_raw = art_comp.get("artifacts", {})

        result_artifacts: dict = {}
        for art_id, art_data in artifacts_raw.items():
            if str(art_data.get("definer_module")) != str(mod_compact_id):
                continue

            full_name = art_id_to_path.get(art_id, art_id)
            # Strip the module prefix from the name for readability.
            symbol = full_name.split("::", 1)[-1] if "::" in full_name else full_name

            entry: dict = {
                "artifact_id": art_id,
                "symbol": symbol,
                "full_name": full_name,
                "kind": art_data.get("kind"),
                "consumer_count": art_data.get("consumer_count", 0),
            }

            if include_consumers:
                consumer_ids = art_data.get("consumer_module_indices", [])
                entry["consumers"] = [
                    mod_id_to_path.get(c, c) for c in consumer_ids
                ]

            result_artifacts[art_id] = entry

        engine = _get_or_init_engine(root)
        live_artifacts = (
            engine.state.artifacts.get(module_name, {}) if engine else {}
        )
        live_symbols = live_artifacts.get("symbols", {})
        signatures = live_symbols.get("signatures", {}) or {}
        kind_by_category = {
            "classes": "class",
            "functions": "function",
            "methods": "method",
            "globals": "global",
        }
        for category, kind in kind_by_category.items():
            for raw_symbol in live_symbols.get(category, []):
                symbol = str(raw_symbol)
                full_name = f"{module_name}::{symbol}"
                artifact_id = art_path_to_id.get(full_name)
                key = artifact_id or full_name
                existing = result_artifacts.get(artifact_id, {}) if artifact_id else {}
                entry = {
                    "artifact_id": artifact_id,
                    "symbol": symbol,
                    "full_name": full_name,
                    "kind": existing.get("kind", kind),
                    "signature": signatures.get(symbol),
                    "consumer_count": existing.get("consumer_count", 0),
                }
                if include_consumers:
                    entry["consumers"] = existing.get("consumers", [])
                result_artifacts[key] = entry

        entries = sorted(
            result_artifacts.items(),
            key=lambda item: item[1].get("symbol", "").lower(),
        )
        if symbol_filter:
            term = symbol_filter.lower()
            entries = [
                item
                for item in entries
                if term in item[1].get("symbol", "").lower()
            ]
        selected, total_count, truncated = _bounded_items(entries, limit)

        return json.dumps(
            {
                "module": module_name,
                "module_id": mod_compact_id,
                "artifact_count": len(selected),
                "total_artifact_count": total_count,
                "truncated": truncated,
                "symbol_filter": symbol_filter or None,
                "data_sources": ["live_symbol_state", "artifacts_compact"],
                "complete_symbol_catalog": bool(engine),
                "artifacts": dict(selected),
            },
            indent=2,
        )
    except Exception as e:
        return f"Error reading artifacts for module: {e}"


@mcp.tool()
def lookup_artifact_by_symbol(
    repo_path: str,
    symbol_name: str,
    limit: int = 20,
) -> str:
    """
    [OPTIMIZED] Finds artifacts matching a symbol name and returns their details.

    Searches by partial, case-insensitive match against the symbol part of
    the artifact's full name (the part after '::', e.g. 'generate_graph'
    matches 'generate_graph_analytics_report').

    Works on the saved compact report — no active analysis session required.
    Returns defining module, kind, consumer count, and consumer module list.
    Exact matches are preferred over partial matches. ``limit`` bounds the
    response while ``total_matches`` and ``truncated`` describe omitted data.

    LLM use: choose this when no live session is available and a saved report is
    sufficient. Narrow ambiguous names before increasing ``limit``.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    art_path = _get_canonical_report(root, f"{repo_name}_artifacts_compact.json")
    if not art_path:
        return "Error: No artifacts_compact report found. Run analyze_project first."

    try:
        _, mod_id_to_path, _, art_id_to_path = _read_registries(root)

        term = symbol_name.lower()

        # Search artifact registry: keys are "module::symbol" strings.
        art_comp = json.loads(art_path.read_text(encoding="utf-8"))
        artifacts_raw = art_comp.get("artifacts", {})

        candidates = []
        for art_id in artifacts_raw:
            full_name = art_id_to_path.get(str(art_id))
            if not full_name or "::" not in full_name:
                continue
            symbol_part = full_name.split("::", 1)[1]
            if term in symbol_part.lower():
                candidates.append(
                    (symbol_part.lower() != term, symbol_part.lower(), art_id, full_name)
                )

        candidates.sort()
        if candidates and not candidates[0][0]:
            candidates = [item for item in candidates if not item[0]]
        total_matches = len(candidates)
        candidates = candidates[: max(1, min(int(limit), 100))]

        if not candidates:
            return f"No current artifacts found matching '{symbol_name}'."

        results: dict = {}
        for _, _, art_id, full_name in candidates:
            art_data = artifacts_raw[art_id]
            definer_id = str(art_data.get("definer_module", ""))
            consumer_ids = art_data.get("consumer_module_indices", [])

            results[art_id] = {
                "symbol": full_name.split("::", 1)[-1] if "::" in full_name else full_name,
                "full_name": full_name,
                "kind": art_data.get("kind", "unknown"),
                "definer_module": mod_id_to_path.get(definer_id, definer_id),
                "consumer_count": art_data.get("consumer_count", 0),
                "consumers": [mod_id_to_path.get(c, c) for c in consumer_ids],
            }

        return json.dumps(
            {
                "query": symbol_name,
                "match_count": len(results),
                "total_matches": total_matches,
                "truncated": total_matches > len(results),
                "data_source": "current_artifacts_compact",
                "artifacts": results,
            },
            indent=2,
        )
    except Exception as e:
        return f"Error searching artifacts by symbol: {e}"


# ==========================================================
# 4. FALLBACK TOOLS
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
