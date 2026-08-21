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
import hashlib
import json
import os
import sys
import warnings
from pathlib import Path


_MCP_SERVER_SOURCE_FINGERPRINT = hashlib.sha256(
    Path(__file__).read_bytes()
).hexdigest()


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
from contextor.core.paths import output_dir as resolve_output_dir
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
from contextor.mcp.documentation import short_description
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers
from contextor.mcp.tools.get_artifact_blast_radius import (
    get_artifact_blast_radius as _get_artifact_blast_radius_impl,
)
from contextor.mcp.tools.search_artifacts import search_artifacts as _search_artifacts_impl
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


def _get_canonical_report(repo_path: Path, filename: str) -> Path | None:
    """Return a report from the shared GUI/CLI/MCP output directory."""
    del repo_path  # Reports are installation-scoped, never repository-local.
    out_dir = resolve_output_dir()
    if not out_dir.is_dir():
        return None
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

def _persist_live_engine(root: Path, engine) -> bool:
    """Persist incremental canonical state so the next MCP process can hydrate it."""

    from contextor.core.analysis.state_manager import save_engine_state
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    identity = require_repository_identity(root)
    cache_dir = repo_cache_dir(root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return bool(
        save_engine_state(
            engine.state,
            str(cache_dir),
            getattr(engine.state_manager, "state_id", ""),
            writer="mcp",
            repo_id=identity.repo_id,
            root_path=identity.root_path,
        )
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
























def _semantic_diff_view(diff: dict, max_items: int | None, compact: bool) -> dict:
    """Shape semantic diff collections for a bounded LLM response."""
    result = {
        "changed_symbol_count": diff.get("changed_symbol_count", 0),
        "body_change_count": diff.get("body_change_count", 0),
        "body_only_changes_tracked": diff.get("body_only_changes_tracked", False),
    }
    for key in (
        "symbols_added",
        "symbols_removed",
        "signatures_changed",
        "bodies_changed",
        "affected_symbols",
    ):
        value = diff.get(key, {}) if key == "signatures_changed" else diff.get(key, [])
        entries = sorted(value.items()) if isinstance(value, dict) else list(value)
        selected, total, truncated = query_helpers.bounded_items(entries, max_items)
        collection = {"total": total, "truncated": truncated}
        if not compact:
            collection["items"] = dict(selected) if isinstance(value, dict) else selected
        result[key] = collection
    return result




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


@mcp.tool(description=short_description('update_file'))
def update_file(
    repo_path: str,
    file_path: str,
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    target_file = Path(file_path).expanduser()
    if not target_file.is_absolute():
        target_file = root / target_file
    target_file = target_file.resolve()
    
    engine = mcp_runtime.get_or_init_engine(root)
            
    if not engine:
        return json.dumps({"status": "NO_SESSION", "file_path": str(target_file), "error": "Run analyze_project first to initialize the session."}, indent=2)
        
    try:
        rel_path = target_file.relative_to(root)
        module_path = ".".join(rel_path.with_suffix("").parts)
        old_artifacts = engine.state.artifacts.get(module_path, {})
        from contextor.core.live_state import connect

        live_client = connect(root)
        if live_client:
            remote = live_client.update_file(str(target_file), origin="mcp")
            if remote.get("status") != "ok":
                raise RuntimeError(remote.get("error", "Shared LIVE update failed."))
            res = remote["result"]
            mcp_runtime._live_engine_revisions[str(root)] = int(remote["revision"]) - 1
            engine = mcp_runtime.get_or_init_engine(root)
            live_state_persisted = True
        else:
            res = engine.update_file(str(target_file))
            live_state_persisted = (
                _persist_live_engine(root, engine)
                if res.status in {"UPDATED", "DELETED"}
                else True
            )
        new_artifacts = engine.state.artifacts.get(module_path, {})
        semantic_diff = _semantic_artifact_diff(old_artifacts, new_artifacts)
        affected_items, affected_total, affected_truncated = query_helpers.bounded_items(
            getattr(res, "affected_modules", []) or [], max_items
        )
        affected_view = {"total": affected_total, "truncated": affected_truncated}
        if not compact:
            affected_view["items"] = affected_items
        result = {
            "status": res.status,
            "file_path": res.file_path,
            "graph_state": res.graph_state,
            "dependencies_state": res.dependencies_state,
            "blast_radius_state": res.blast_radius_state,
            "local_metrics_state": res.local_metrics_state,
            "global_metrics_state": res.global_metrics_state,
            "artifact_consumption_state": res.artifact_consumption_state,
            "affected_modules": affected_view,
            "live_state_persisted": live_state_persisted,
            "semantic_diff": _semantic_diff_view(semantic_diff, max_items, compact),
        }
        runtime_restart_required = (
            target_file == Path(__file__).resolve()
            and hashlib.sha256(target_file.read_bytes()).hexdigest()
            != _MCP_SERVER_SOURCE_FINGERPRINT
        )
        result["runtime_restart_required"] = runtime_restart_required
        if runtime_restart_required:
            result["runtime_state"] = "stale_until_mcp_server_restart"
            result["runtime_warning"] = (
                "Canonical state now describes the MCP server code on disk, but "
                "the running MCP process still executes the previously loaded code. "
                "Restart the MCP server and verify the changed tool live."
            )
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
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps(
                    {
                        "error": "Unsupported fields for update_file",
                        "unknown_fields": unknown_fields,
                        "allowed_fields": sorted(allowed_fields),
                    },
                    indent=2,
                )
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "file_path": str(target_file), "error": str(e)}, indent=2)


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

@mcp.tool(description=short_description('get_layer_isolation'))
def get_layer_isolation(
    repo_path: str,
    layer_name: str,
    max_clusters: int | None = 8,
    max_boundary_violations: int | None = 10,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    raw_layer = str(layer_name).strip().replace("\\", "/").strip("/")
    candidate = Path(raw_layer).expanduser()
    if candidate.is_absolute():
        try:
            raw_layer = candidate.resolve().relative_to(root).as_posix()
        except ValueError:
            return f"Error: Layer path '{candidate}' is outside the repository."
    requested_layer = raw_layer.replace("/", ".")
    normalized_layer_name = requested_layer.rsplit(".", 1)[-1]
    
    # Try to find layer-specific report in high_risk_layers
    ga_path = _get_canonical_report(root, f"{repo_name}_{normalized_layer_name}_graph_analytics.json")
    if not ga_path:
        engine = mcp_runtime.get_or_init_engine(root)
        if engine and engine.state.dependency_graph:
            graph = engine.state.dependency_graph
            layer_modules = {
                name
                for name in engine.state.modules
                if name == requested_layer or name.startswith(requested_layer + ".")
            }
            if layer_modules:
                boundary_edges = []
                dependency_types = {"hard": 0, "soft": 0}
                for edge_type, edge_map in (
                    ("hard", graph.hard_edges),
                    ("soft", graph.soft_edges),
                ):
                    for source, targets in edge_map.items():
                        for target in targets:
                            source_inside = source in layer_modules
                            target_inside = target in layer_modules
                            if source_inside:
                                dependency_types[edge_type] += 1
                            if source_inside != target_inside:
                                boundary_edges.append(
                                    {
                                        "from": source,
                                        "to": target,
                                        "edge_type": edge_type,
                                        "direction": "outbound" if source_inside else "inbound",
                                    }
                                )
                items, total, truncated = query_helpers.bounded_items(
                    sorted(
                        boundary_edges,
                        key=lambda item: (
                            item["from"], item["to"], item["edge_type"]
                        ),
                    ),
                    max_boundary_violations,
                )
                result = {
                    "layer": requested_layer,
                    "report_layer": normalized_layer_name,
                    "data_source": "live_canonical_graph",
                    "module_count": len(layer_modules),
                    "clusters": {
                        "total": 0,
                        "truncated": False,
                        "available": False,
                    },
                    "dependency_types": dependency_types,
                    "boundary_violations": {
                        "total": total,
                        "truncated": truncated,
                        "evidence_scope": "cross_boundary_edges_not_policy_violations",
                    },
                }
                if not compact:
                    result["clusters"]["items"] = []
                    result["boundary_violations"]["items"] = items
                if fields is not None:
                    unknown_fields = sorted(set(fields) - set(result))
                    if unknown_fields:
                        return json.dumps(
                            {
                                "error": "Unsupported fields for get_layer_isolation",
                                "unknown_fields": unknown_fields,
                                "allowed_fields": sorted(result),
                            },
                            indent=2,
                        )
                    result = {field: result[field] for field in fields}
                return json.dumps(result, indent=2)
        # Fallback to global summary if layer report doesn't exist
        summary_path = _get_canonical_report(root, f"{repo_name}_summary.json")
        if not summary_path:
             return f"Error: No layer report found for '{normalized_layer_name}' and no global summary found."
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            for layer in summary.get("layer_index", []):
                if layer.get("layer") == normalized_layer_name:
                    return json.dumps(layer, indent=2)
            return (
                f"Layer '{requested_layer}' has no dedicated report and is not "
                "present in the global top-level layer index. Run analyze_layer "
                "for this nested layer first."
            )
        except Exception as e:
            return f"Error reading fallback layer info: {e}"
            
    try:
        ga = json.loads(ga_path.read_text(encoding="utf-8"))
        
        # Resolve only the IDs exposed by this bounded response.
        _, id_to_name, _, artifact_id_to_name = query_helpers.read_registries(root)
        
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
        
        clusters, cluster_count, clusters_truncated = query_helpers.bounded_items(
            ga.get("shared_usage_clusters", []), max_clusters
        )
        clusters = [
            _resolve_cluster_ids(cluster, id_to_name, artifact_id_to_name)
            for cluster in clusters
        ]
        violations, violation_count, violations_truncated = query_helpers.bounded_items(
            boundary_violations, max_boundary_violations
        )
        cluster_collection = {
            "total": cluster_count,
            "truncated": clusters_truncated,
        }
        violation_collection = {
            "total": violation_count,
            "truncated": violations_truncated,
        }
        if not compact:
            cluster_collection["items"] = clusters
            violation_collection["items"] = violations
        result = {
            "layer": requested_layer,
            "report_layer": normalized_layer_name,
            "data_source": str(ga_path),
            "module_count": ga.get("module_count", 0),
            "clusters": cluster_collection,
            "dependency_types": ga.get("dependency_type_breakdown", {}),
            "boundary_violations": violation_collection,
        }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for get_layer_isolation",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting layer isolation: {e}"


@mcp.tool(description=short_description('get_report_diff'))
def get_report_diff(
    repo_path: str,
    max_items: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
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
        report_diff = diff_data.get("report_diff", {})
        layers = report_diff.get("layers", {})
        layer_items, layer_total, layer_truncated = query_helpers.bounded_items(
            sorted(layers.items()), max_items
        )
        layer_collection = {"total": layer_total, "truncated": layer_truncated}
        if not compact:
            layer_collection["items"] = dict(layer_items)
        diff_data["report_diff"] = {**report_diff, "layers": layer_collection}
        if fields is not None:
            allowed_fields = set(diff_data)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for get_report_diff",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            diff_data = {field: diff_data[field] for field in fields}
        return json.dumps(diff_data, indent=2)
    except Exception as e:
        return f"Error reading diff report: {e}"


describe_canonical_state = mcp.tool(
    description=short_description("describe_canonical_state")
)(_describe_canonical_state_impl)


query_canonical_projection = mcp.tool(
    description=short_description("query_canonical_projection")
)(_query_canonical_projection_impl)


# ==========================================================
# 3. TARGETED INDEX / ARTIFACT QUERY TOOLS
# ==========================================================

@mcp.tool(description=short_description('extract_indexed_report_context'))
def extract_indexed_report_context(
    repo_path: str,
    query: str,
    report_path: str = "",
    resolve_indices: bool = True,
    public_api_only: bool = False,
    max_items: int | None = 20,
    fields: list[str] | None = None,
) -> str:
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
        engine = mcp_runtime.get_or_init_engine(root)
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
        artifact_entries = sorted(result.get("artifacts", {}).items())
        selected_entries, total_artifacts, artifacts_truncated = query_helpers.bounded_items(
            artifact_entries, max_items
        )
        result["artifacts"] = dict(selected_entries)
        result["artifact_count"] = len(selected_entries)
        result["total_artifact_count"] = total_artifacts
        result["truncated"] = artifacts_truncated
        result["data_source"] = str(selected_path)
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for extract_indexed_report_context",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error extracting indexed report context: {e}"


lookup_index_entries = mcp.tool(
    description=short_description("lookup_index_entries")
)(_lookup_index_entries_impl)


get_artifacts_for_module = mcp.tool(description=short_description("get_artifacts_for_module"))(
    _get_artifacts_for_module_impl
)


lookup_artifact_by_symbol = mcp.tool(description=short_description("lookup_artifact_by_symbol"))(
    _lookup_artifact_by_symbol_impl
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
