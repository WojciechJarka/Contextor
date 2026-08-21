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
import ast
import asyncio
import atexit
import hashlib
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any


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
from contextor.core.analysis.state_manager import (
    artifact_consumption_is_fresh,
    canonical_artifact_consumption_targets,
    module_current_truth,
)
from contextor.core.paths import output_dir as resolve_output_dir
from contextor.core.source import SourceError, read_source
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
from contextor.mcp.analysis_jobs import _bounded_items
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


def _canonical_symbol_consumers(state, module_name: str, symbol: str) -> list[str]:
    """Return deterministic consumer facts from canonical RAM only."""
    if not artifact_consumption_is_fresh(state):
        raise ValueError("Canonical artifact consumption is unavailable or stale.")
    target = f"{module_name}::{symbol}"
    consumption = getattr(state, "artifact_consumption", {}) or {}
    entry = consumption.get(target, {}) if isinstance(consumption, dict) else {}
    consumers = entry.get("consumers", []) if isinstance(entry, dict) else []
    return sorted({str(item) for item in consumers})


def _module_truth_unavailable(state, module_name: str) -> dict | None:
    """Shape the authoritative canonical parse-freshness contract for MCP."""
    truth = module_current_truth(state, module_name)
    if truth["available"]:
        return None
    return {
        "status": "stale",
        "available": False,
        "module": module_name,
        **{key: value for key, value in truth.items() if key != "available"},
    }


def _stale_module_truths(state) -> dict[str, dict]:
    """Return parse-stale canonical modules using the shared core contract."""
    module_names = set(getattr(state, "modules", {}) or {}) | set(
        getattr(state, "artifacts", {}) or {}
    )
    return {
        module_name: truth
        for module_name in sorted(module_names)
        if not (truth := module_current_truth(state, module_name))["available"]
    }


def _canonical_symbol_catalog(module_data: dict) -> dict[str, str]:
    """Project canonical symbol names to kinds without report enrichment."""
    targets = canonical_artifact_consumption_targets({"module": module_data})
    result = {target.split("::", 1)[1]: "unknown" for target in targets}
    symbols = module_data.get("symbols", {}) or {}
    for category, kind in (
        ("classes", "class"),
        ("functions", "function"),
        ("methods", "method"),
        ("globals", "global"),
    ):
        raw_names = symbols.get(category, []) or []
        names = raw_names.keys() if isinstance(raw_names, dict) else raw_names
        for name in names:
            if str(name) in result:
                result[str(name)] = kind
    return result


def _resolve_symbol_source_paths(root: Path, file_paths: list[str]) -> list[Path]:
    """Resolve explicit Python source paths while retaining repository scope."""
    resolved: list[Path] = []
    for raw_path in file_paths:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Source file '{candidate}' is outside the repository.") from exc
        if not candidate.is_file():
            raise ValueError(f"Source file '{candidate}' does not exist.")
        if candidate.suffix != ".py":
            raise ValueError(f"Source file '{candidate}' is not a Python file.")
        if candidate not in resolved:
            resolved.append(candidate)
    if not resolved:
        raise ValueError("At least one Python source file is required.")
    return resolved


def _symbol_signature(node: ast.AST) -> str:
    """Return a semantic signature without splitting a source implementation."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return f"class {node.name}" if isinstance(node, ast.ClassDef) else ""
    try:
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        arguments = ast.unparse(node.args)
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        return f"{prefix} {node.name}({arguments}){returns}"
    except Exception:
        return node.name


def _ast_symbol_candidates(path: Path, requested_symbol: str) -> list[dict]:
    """Find complete class/function/method AST nodes matching one symbol name."""
    source = read_source(path)
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines(keepends=True)
    normalized = requested_symbol.split("::", 1)[-1].strip()
    candidates: list[dict] = []

    def add_candidate(node: ast.AST, kind: str, class_stack: tuple[str, ...]) -> None:
        name = getattr(node, "name", "")
        qualified_name = ".".join((*class_stack, name)) if class_stack else name
        aliases = {qualified_name}
        if not class_stack:
            aliases.add(name)
        elif "." not in normalized:
            aliases.add(name)
        if normalized not in aliases:
            return
        start_line = min(
            [getattr(decorator, "lineno", node.lineno) for decorator in node.decorator_list]
            or [node.lineno]
        )
        end_line = getattr(node, "end_lineno", node.lineno)
        source_text = "".join(lines[start_line - 1 : end_line])
        docstring = ast.get_docstring(node, clean=False) or ""
        candidates.append(
            {
                "file_path": str(path),
                "symbol": qualified_name,
                "kind": kind,
                "node": node,
                "source": source_text,
                "source_lines": lines,
                "docstring": docstring,
                "start_line": start_line,
                "end_line": end_line,
            }
        )

    def visit_statements(statements: list[ast.stmt], class_stack: tuple[str, ...] = ()) -> None:
        for node in statements:
            if isinstance(node, ast.ClassDef):
                add_candidate(node, "class", class_stack)
                visit_statements(node.body, (*class_stack, node.name))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                add_candidate(node, "method" if class_stack else "function", class_stack)
                # Nested definitions are implementation details, not file symbols.

    visit_statements(tree.body)
    return candidates


def _module_path_for_source(root: Path, path: Path) -> str:
    """Map a repository-relative Python path to Contextor's dotted module path."""
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _symbol_static_context(root: Path, candidate: dict) -> dict:
    """Return compact current consumer evidence when a live engine is available."""
    engine = mcp_runtime.get_or_init_engine(root)
    module_path = _module_path_for_source(root, Path(candidate["file_path"]))
    context = {
        "module": module_path,
        "consumers": {"available": False, "total": 0, "truncated": False},
        "evidence_scope": "current live canonical state; static consumers only",
    }
    if not engine:
        return context
    unavailable = _module_truth_unavailable(engine.state, module_path)
    if unavailable:
        return unavailable
    module_artifacts = getattr(engine.state, "artifacts", {}).get(module_path, {})
    raw_consumers = module_artifacts.get("consumers", {}).get(candidate["symbol"], [])
    if isinstance(raw_consumers, dict):
        raw_consumers = raw_consumers.get("consumers", [])
    if not isinstance(raw_consumers, list):
        raw_consumers = []
    context["consumers"] = {
        "available": True,
        "total": len(raw_consumers),
        "truncated": False,
    }
    return context


def _json_size(value: dict) -> dict:
    """Return the exact UTF-8 JSON payload size and a readable decimal KB value."""
    byte_count = len(json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8"))
    return {"bytes": byte_count, "kb": round(byte_count / 1000, 1)}


def _symbol_preview(root: Path, candidate: dict, member_limit: int | None) -> dict:
    """Build non-overlapping fetch plans and member costs for one AST symbol."""
    node = candidate["node"]
    resolution = {
        "symbol": candidate["symbol"],
        "file_path": candidate["file_path"],
        "kind": candidate["kind"],
        "lines": {"start": candidate["start_line"], "end": candidate["end_line"]},
    }
    signature = _symbol_signature(node)
    static_context = _symbol_static_context(root, candidate)
    base = {"status": "resolved", "resolution": resolution}
    signature_section = {**base, "signature": signature, "docstring": candidate["docstring"]}
    implementation_section = {**base, "implementation": candidate["source"]}
    full_section = {**implementation_section, "static_context": static_context}
    preview = {
        **base,
        "mode": "preview",
        "available_sections": ["signature", "docstring", "implementation", "static_context"],
        "section_sizes": {
            "signature": _json_size({"signature": signature}),
            "docstring": _json_size({"docstring": candidate["docstring"]}),
            "implementation": _json_size({"implementation": candidate["source"]}),
            "static_context": _json_size({"static_context": static_context}),
        },
        "fetch_plans": {
            "signature_and_docstring": _json_size(signature_section),
            "implementation": _json_size(implementation_section),
            "implementation_with_static_context": _json_size(full_section),
        },
        "source_contract": {
            "implementation_is_complete": True,
            "implementation_includes_docstring": bool(candidate["docstring"]),
            "no_partial_symbol_source": True,
        },
    }
    if isinstance(node, ast.ClassDef):
        members = []
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            start_line = min(
                [getattr(decorator, "lineno", child.lineno) for decorator in child.decorator_list]
                or [child.lineno]
            )
            end_line = getattr(child, "end_lineno", child.lineno)
            member_source = "".join(candidate["source_lines"][start_line - 1 : end_line])
            members.append(
                {
                    "name": child.name,
                    "kind": "method",
                    "lines": {"start": start_line, "end": end_line},
                    "implementation": _json_size({"implementation": member_source}),
                    "docstring": _json_size({"docstring": ast.get_docstring(child, clean=False) or ""}),
                }
            )
        selected, total, truncated = _bounded_items(members, member_limit)
        preview["available_sections"].append("methods")
        preview["methods"] = {"total": total, "truncated": truncated, "items": selected}
        preview["method_selection_contract"] = (
            "Fetch a named method only through include=['methods'] and methods=[...]. "
            "Every requested method is returned as one complete AST symbol."
        )
    return preview


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
        selected, total, truncated = _bounded_items(entries, max_items)
        collection = {"total": total, "truncated": truncated}
        if not compact:
            collection["items"] = dict(selected) if isinstance(value, dict) else selected
        result[key] = collection
    return result


def _static_test_reachability(
    target: str,
    hard_edges: dict,
    soft_edges: dict,
    test_modules: set[str],
    module_to_id: dict[str, str],
    max_depth: int = 6,
) -> list[dict]:
    """Return shortest static dependency paths from tests to one module."""
    reverse: dict[str, set[str]] = {}
    for edge_map in (hard_edges, soft_edges):
        for source, targets in edge_map.items():
            for destination in targets:
                reverse.setdefault(str(destination), set()).add(str(source))

    paths = {target: [target]}
    queue = [target]
    while queue:
        current = queue.pop(0)
        current_path = paths[current]
        if len(current_path) - 1 >= max_depth:
            continue
        for predecessor in sorted(reverse.get(current, set())):
            if predecessor in paths:
                continue
            paths[predecessor] = [predecessor, *current_path]
            queue.append(predecessor)

    return [
        {
            "module_id": module_to_id.get(module),
            "module": module,
            "distance": len(paths[module]) - 1,
            "evidence_path": paths[module],
            "evidence_scope": "static_dependency_reachability",
        }
        for module in sorted(test_modules)
        if module in paths and module != target
    ]


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
        affected_items, affected_total, affected_truncated = _bounded_items(
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

@mcp.tool(description=short_description('get_project_architecture'))
def get_project_architecture(
    repo_path: str,
    max_items: int | None = 10,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."

        state = engine.state
        stale_modules = _stale_module_truths(state)
        if stale_modules:
            return json.dumps(
                {
                    "status": "stale",
                    "available": False,
                    "scope": "project",
                    "provenance": "last_known_good",
                    "affected_modules": stale_modules,
                },
                indent=2,
            )
        unavailable = {
            "available": False,
            "state": "deferred",
            "reason": "No fresh canonical LIVE producer is available for this analytics family.",
        }
        collections = {
            "action_items": dict(unavailable),
            "top_global_hotspots": dict(unavailable),
        }
        debt_summary = dict(unavailable)

        cached_analytics = getattr(state, "cached_analytics", {}) or {}
        cached_state = getattr(state, "cached_analytics_state", "deferred")
        canonical_modules = set(getattr(state, "modules", {}) or {})
        module_layers = None
        if (
            cached_state == "fresh"
            and isinstance(cached_analytics, dict)
            and "module_layers" in cached_analytics
            and isinstance(cached_analytics["module_layers"], dict)
        ):
            candidate_layers = cached_analytics["module_layers"]
            if set(candidate_layers) == canonical_modules:
                module_layers = candidate_layers
        if isinstance(module_layers, dict):
            layer_counts: dict[str, int] = {}
            for layer in module_layers.values():
                layer_name = str(layer)
                layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1
            layer_items = [
                {"layer": layer, "module_count": count}
                for layer, count in sorted(layer_counts.items())
            ]
            items, total, truncated = _bounded_items(layer_items, max_items)
            layer_index = {"available": True, "total": total, "truncated": truncated}
            if not compact:
                layer_index["items"] = items
        else:
            layer_index = dict(unavailable)
        collections["layer_index"] = layer_index
        result = {
            **collections,
            "debt_summary": debt_summary,
            "module_count": len(getattr(state, "modules", {}) or {}),
            "data_source": "live_canonical_state",
        }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for get_project_architecture",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error reading project architecture: {e}"


@mcp.tool(description=short_description('get_module_context'))
def get_module_context(
    repo_path: str,
    module_name: str = "",
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
    module: str | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    from contextor.core.report_query import IndexCatalog, catalog_from_registry, resolve_index_query

    mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)
    catalog = catalog_from_registry(str(root))
    if not catalog.modules and mod_id_to_path:
        catalog = IndexCatalog(
            modules=mod_id_to_path,
            artifacts=art_id_to_path,
            module_paths={name: name.replace(".", "/") + ".py" for name in mod_path_to_id},
            recovered_modules={},
            recovered_artifacts={},
        )

    effective_name = (module_name or "").strip()
    effective_alias = (module or "").strip()

    if effective_name and effective_alias:
        res_name = resolve_index_query(effective_name, catalog, repo_root=str(root))
        res_alias = resolve_index_query(effective_alias, catalog, repo_root=str(root))
        matches_name = res_name.get("matches", [])
        matches_alias = res_alias.get("matches", [])
        if matches_name and matches_alias:
            m_n = matches_name[0]
            m_a = matches_alias[0]
            if (
                (m_n.get("id") != m_a.get("id"))
                or (m_n.get("name") != m_a.get("name"))
                or (m_n.get("kind") != m_a.get("kind"))
            ):
                return json.dumps(
                    {
                        "error": "Conflicting 'module_name' and 'module' arguments provided. Resolved to different canonical targets.",
                        "module_name": effective_name,
                        "module_name_resolved": {"id": m_n.get("id"), "name": m_n.get("name"), "kind": m_n.get("kind")},
                        "module": effective_alias,
                        "module_resolved": {"id": m_a.get("id"), "name": m_a.get("name"), "kind": m_a.get("kind")},
                    },
                    indent=2,
                )

    input_query = effective_alias or effective_name
    if not input_query:
        return json.dumps({"error": "Either 'module_name' or 'module' must be provided."}, indent=2)

    resolution = resolve_index_query(input_query, catalog, repo_root=str(root))
    if resolution.get("matches"):
        top = resolution["matches"][0]
        if top.get("kind") == "artifact":
            art_name = top["name"]
            art_id = top["id"]
            definer_mod = art_name.split("::", 1)[0]
            return json.dumps(
                {
                    "target": input_query,
                    "resolved_as": "artifact",
                    "artifact": art_name,
                    "artifact_id": art_id,
                    "definer_module": definer_mod,
                    "suggested_next_tool": "get_artifact_blast_radius",
                    "warnings": [
                        "Target resolved to an artifact/symbol rather than a module. "
                        "Use get_artifact_blast_radius for symbol-level consumption."
                    ],
                },
                indent=2,
            )
        elif top.get("kind") == "module":
            module_name = top["name"]
    else:
        module_name = input_query

    engine = mcp_runtime.get_or_init_engine(root)
    if not engine or getattr(engine.state, "resync_required", False):
        return "Error: No usable canonical LIVE state. Run analyze_project first."
    state = engine.state
    unavailable = _module_truth_unavailable(state, module_name)
    if unavailable:
        return json.dumps(unavailable, indent=2)
    live_modules = set(getattr(state, "modules", {})) | set(
        getattr(state, "artifacts", {})
    )
    if module_name not in live_modules:
        return f"Module '{module_name}' not found in the project graph."

    inbound = {}
    outbound = {}
    dependency_source = "live_canonical_graph"
    graph = getattr(state, "dependency_graph", None)
    if graph is None:
        return "Error: Canonical LIVE dependency graph is unavailable. Run analyze_project first."
    hard_edges = getattr(graph, "hard_edges", {}) if graph else {}
    soft_edges = getattr(graph, "soft_edges", {}) if graph else {}

    def relationship(source: str, target: str) -> dict:
        classes = []
        if target in set(hard_edges.get(source, set())):
            classes.append("hard_dependency")
        if target in set(soft_edges.get(source, set())):
            classes.append("soft_dependency")
        return {
            "dep_types": classes,
            "weight": 1,
            "data_source": "live_canonical_graph",
        }

    targets = set(hard_edges.get(module_name, set())) | set(
        soft_edges.get(module_name, set())
    )
    outbound = {
        target: relationship(module_name, target)
        for target in sorted(targets)
    }
    sources = set(hard_edges) | set(soft_edges)
    inbound = {
        source: relationship(source, module_name)
        for source in sorted(sources)
        if module_name
        in (
            set(hard_edges.get(source, set()))
            | set(soft_edges.get(source, set()))
        )
    }

    if graph is not None:
        hard_edges = getattr(graph, "hard_edges", {}) or {}
        live_fan_out = len(hard_edges.get(module_name, set()))
        live_fan_in = sum(
            1 for _, targets in hard_edges.items() if module_name in targets
        )
        topo = getattr(state, "topology_analytics", {}) or {}
        topo_freshness = getattr(state, "topology_metrics_state", "deferred")

        metrics = {
            "fan_in": live_fan_in,
            "fan_out": live_fan_out,
        }
        degree_metrics_source = "live_canonical_graph"

        if topo_freshness == "fresh" and isinstance(topo, dict):
            has_any_topo = False
            for topo_key, metric_field in [
                ("pagerank", "pagerank"),
                ("betweenness", "betweenness"),
                ("hub_scores", "hub_score"),
                ("authority_scores", "authority_score"),
                ("bridge_scores", "bridge_score"),
            ]:
                val_map = topo.get(topo_key, {})
                if isinstance(val_map, dict) and module_name in val_map:
                    metrics[metric_field] = val_map[module_name]
                    has_any_topo = True

            if "module_risk" in topo and isinstance(topo["module_risk"], dict) and module_name in topo["module_risk"]:
                metrics["risk_score"] = topo["module_risk"][module_name]
                has_any_topo = True

            metrics_source = "live_canonical_topology" if has_any_topo else "live_canonical_graph"
        elif topo_freshness == "stale":
            metrics_source = "stale_topology_analytics"
        else:
            metrics_source = "deferred_topology_analytics"

        if mod_path_to_id.get(module_name):
            metrics["module_idx"] = mod_path_to_id[module_name]

        cached_analytics = getattr(state, "cached_analytics", {}) or {}
        cached_freshness = getattr(state, "cached_analytics_state", "deferred")
        if cached_freshness == "fresh" and isinstance(cached_analytics, dict):
            if "module_layers" in cached_analytics and module_name in cached_analytics["module_layers"]:
                metrics["layer"] = cached_analytics["module_layers"][module_name]
            if "visibility" in cached_analytics and module_name in cached_analytics["visibility"]:
                metrics["visibility"] = cached_analytics["visibility"][module_name]
            if "export_degree" in cached_analytics and module_name in cached_analytics["export_degree"]:
                metrics["export_degree"] = cached_analytics["export_degree"][module_name]

    else:
        metrics = {"fan_in": len(inbound), "fan_out": len(outbound)}
        canonical_metrics = getattr(state, "metrics", {}) or {}
        if isinstance(canonical_metrics.get(module_name), dict):
            metrics.update(canonical_metrics[module_name])
        metrics_source = "deferred_topology_analytics"
        degree_metrics_source = "canonical_module_metrics"

    inbound_items, inbound_total, inbound_truncated = _bounded_items(
        sorted(inbound.items()), max_items
    )
    outbound_items, outbound_total, outbound_truncated = _bounded_items(
        sorted(outbound.items()), max_items
    )
    common_result = {
        "module": module_name,
        "metrics": metrics,
        "metrics_source": metrics_source,
        "degree_metrics_source": degree_metrics_source,
        "dependency_data_source": dependency_source,
    }
    full_result = {
        **common_result,
        "dependencies_inbound_who_calls_me": {
            "items": dict(inbound_items),
            "total": inbound_total,
            "truncated": inbound_truncated,
        },
        "dependencies_outbound_who_i_call": {
            "items": dict(outbound_items),
            "total": outbound_total,
            "truncated": outbound_truncated,
        },
    }
    compact_result = {
        **common_result,
        "dependencies_inbound_who_calls_me": {
            "total": inbound_total,
            "truncated": inbound_truncated,
        },
        "dependencies_outbound_who_i_call": {
            "total": outbound_total,
            "truncated": outbound_truncated,
        },
    }
    result = compact_result if compact else full_result

    if fields is not None:
        allowed_fields = set(result)
        unknown_fields = sorted(set(fields) - allowed_fields)
        if unknown_fields:
            return json.dumps(
                {
                    "error": "Unsupported fields for get_module_context",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                },
                indent=2,
            )
        result = {field: result[field] for field in fields}

    return json.dumps(result, indent=2)

@mcp.tool(description=short_description('get_artifact_blast_radius'))
def get_artifact_blast_radius(
    repo_path: str,
    artifact_name: str,
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."
        target_art = art_id_to_path.get(artifact_name, artifact_name)
        if engine:
            live_matches = []
            for module_name, artifact_state in engine.state.artifacts.items():
                for local_name, kind in _canonical_symbol_catalog(artifact_state).items():
                    full_name = f"{module_name}::{local_name}"
                    art_id = str(art_path_to_id.get(full_name, ""))
                    if (
                        full_name != artifact_name
                        and local_name != artifact_name
                        and art_id != artifact_name
                        and full_name != target_art
                    ):
                        continue
                    unavailable = _module_truth_unavailable(
                        engine.state, module_name
                    )
                    if unavailable:
                        return json.dumps(unavailable, indent=2)
                    live_matches.append(
                        {
                            "artifact": full_name,
                            "artifact_id": art_path_to_id.get(full_name),
                            "kind": kind,
                            "definer": module_name,
                            "consumer_items": _canonical_symbol_consumers(
                                engine.state, module_name, str(local_name)
                            ),
                        }
                    )
            if live_matches:
                ordered_matches = sorted(live_matches, key=lambda item: item["artifact"])
                if len(ordered_matches) > 1:
                    return json.dumps(
                        {
                            "error": "Ambiguous canonical artifact identity.",
                            "query": artifact_name,
                            "candidates": [item["artifact"] for item in ordered_matches],
                            "data_source": "live_canonical_state",
                        },
                        indent=2,
                    )
                selected = ordered_matches[0]
                raw_consumer_items = list(selected.pop("consumer_items"))
                unique_direct_consumers = sorted(set(raw_consumer_items))
                consumer_items, consumer_total, consumer_truncated = _bounded_items(
                    unique_direct_consumers, max_items
                )

                architecture = {"available": False}
                cached_analytics = getattr(engine.state, "cached_analytics", {}) or {}
                cached_state = getattr(engine.state, "cached_analytics_state", "deferred")
                if cached_state == "fresh" and isinstance(cached_analytics, dict):
                    module_layers = cached_analytics.get("module_layers", {}) or {}
                    definer_module = selected.get("definer", "")
                    definer_layer = module_layers.get(definer_module)

                    same_module_consumers = []
                    same_layer_consumers = []
                    cross_layer_consumers_list = []
                    test_consumers = []
                    unknown_layer_consumers = []
                    known_consumer_layers_set = set()

                    for c_mod in unique_direct_consumers:
                        if c_mod == definer_module:
                            same_module_consumers.append(c_mod)
                            continue

                        c_layer = module_layers.get(c_mod)
                        if c_layer is not None:
                            known_consumer_layers_set.add(c_layer)

                        if c_layer == "tests":
                            test_consumers.append(c_mod)
                        elif definer_layer is None:
                            unknown_layer_consumers.append(c_mod)
                        elif c_layer is None:
                            unknown_layer_consumers.append(c_mod)
                        elif c_layer == definer_layer:
                            same_layer_consumers.append(c_mod)
                        else:
                            cross_layer_consumers_list.append({"module": c_mod, "layer": c_layer})

                    same_mod_count = len(same_module_consumers)
                    same_layer_count = len(same_layer_consumers)
                    cross_layer_count = len(cross_layer_consumers_list)
                    test_count = len(test_consumers)
                    unknown_count = len(unknown_layer_consumers)

                    architecture = {
                        "available": True,
                        "definer_layer": definer_layer,
                        "consumer_layers": sorted(known_consumer_layers_set),
                        "same_module_consumer_count": same_mod_count,
                        "same_layer_consumer_count": same_layer_count,
                        "cross_layer_consumer_count": cross_layer_count,
                        "test_consumer_count": test_count,
                        "cross_layer_consumers": cross_layer_count > 0,
                    }
                    if unknown_count > 0:
                        architecture["unknown_layer_consumer_count"] = unknown_count
                    if cross_layer_count > 0:
                        cross_sample, cross_total, cross_trunc = _bounded_items(
                            cross_layer_consumers_list, 5
                        )
                        architecture["cross_layer_sample"] = {
                            "total": cross_total,
                            "items": cross_sample,
                            "truncated": cross_trunc,
                        }
                else:
                    architecture = {
                        "available": False,
                        "reason": f"Cached analytics state is '{cached_state}'.",
                    }

                # 2. Downstream module reachability (Model B)
                from contextor.core.analysis.incremental.graph_ops import calculate_affected_set

                dep_graph = getattr(engine.state, "dependency_graph", None) if engine else None
                definer_module = selected.get("definer", "")

                if dep_graph is not None:
                    all_reachable: set[str] = set()
                    for seed_mod in unique_direct_consumers:
                        all_reachable.update(calculate_affected_set(seed_mod, old_graph=dep_graph))

                    downstream_set = all_reachable - set(unique_direct_consumers) - {definer_module}
                    sorted_downstream = sorted(downstream_set)
                    total_downstream = len(sorted_downstream)

                    downstream_reachability = {
                        "available": True,
                        "total_downstream_count": total_downstream,
                    }

                    if cached_state == "fresh" and isinstance(cached_analytics, dict):
                        module_layers = cached_analytics.get("module_layers", {}) or {}
                        prod_downstream = []
                        test_downstream = []
                        unknown_downstream = []

                        for d_mod in sorted_downstream:
                            d_layer = module_layers.get(d_mod)
                            if d_layer == "tests":
                                test_downstream.append(d_mod)
                            elif d_layer is not None:
                                prod_downstream.append(d_mod)
                            else:
                                unknown_downstream.append(d_mod)

                        prod_sample, prod_total, prod_trunc = _bounded_items(prod_downstream, 5)
                        test_sample, test_total, test_trunc = _bounded_items(test_downstream, 5)

                        downstream_reachability.update(
                            {
                                "layer_classification_available": True,
                                "production_downstream_count": len(prod_downstream),
                                "test_downstream_count": len(test_downstream),
                                "unknown_layer_downstream_count": len(unknown_downstream),
                                "production_downstream_sample": {
                                    "total": prod_total,
                                    "items": prod_sample,
                                    "truncated": prod_trunc,
                                },
                                "test_downstream_sample": {
                                    "total": test_total,
                                    "items": test_sample,
                                    "truncated": test_trunc,
                                },
                            }
                        )
                    else:
                        downstream_reachability.update(
                            {
                                "layer_classification_available": False,
                                "reason": f"Cached analytics state is '{cached_state}'.",
                            }
                        )
                else:
                    downstream_reachability = {
                        "available": False,
                        "reason": "Live dependency graph is not available.",
                    }

                result = {
                    **selected,
                    "architecture": architecture,
                    "downstream_module_reachability": downstream_reachability,
                    "consumers": {
                        "total": consumer_total,
                        "truncated": consumer_truncated,
                    },
                    "evidence_scope": "direct_static_artifact_consumption",
                    "data_source": "live_canonical_state",
                }
                if not compact:
                    result["consumers"]["items"] = consumer_items
                if fields is not None:
                    unknown_fields = sorted(set(fields) - set(result))
                    if unknown_fields:
                        return json.dumps(
                            {
                                "error": "Unsupported fields for get_artifact_blast_radius",
                                "unknown_fields": unknown_fields,
                                "allowed_fields": sorted(result),
                            },
                            indent=2,
                        )
                    result = {field: result[field] for field in fields}
                return json.dumps(result, indent=2)

        candidates = [
            (art_id, full_name)
            for art_id, full_name in art_id_to_path.items()
            if full_name == artifact_name
            or full_name.endswith("::" + artifact_name)
        ]
        if not candidates:
            from contextor.core.report_query import IndexCatalog, catalog_from_registry, resolve_index_query

            catalog = catalog_from_registry(str(root))
            if not catalog.modules and mod_id_to_path:
                catalog = IndexCatalog(
                    modules=mod_id_to_path,
                    artifacts=art_id_to_path,
                    module_paths={name: name.replace(".", "/") + ".py" for name in mod_path_to_id},
                    recovered_modules={},
                    recovered_artifacts={},
                )
            resolution = resolve_index_query(artifact_name, catalog, repo_root=str(root))
            if resolution.get("matches"):
                top = resolution["matches"][0]
                if top.get("kind") == "module":
                    target_module = top["name"]
                    target_module_id = top["id"]
                    prefix = target_module + "::"
                    art_state = (getattr(engine.state, "artifacts", {}) or {}).get(target_module, {}) if engine else {}
                    symbols = art_state.get("symbols", {}) or {}
                    kind_map = {}
                    for category, kind_label in [
                        ("classes", "class"),
                        ("functions", "function"),
                        ("methods", "method"),
                        ("globals", "global"),
                    ]:
                        for s in symbols.get(category, []) or []:
                            kind_map[str(s)] = kind_label

                    candidates_list = []
                    seen_artifacts = set()
                    for full_name, art_id in sorted(art_path_to_id.items()):
                        if full_name.startswith(prefix):
                            local_name = full_name.split("::", 1)[-1]
                            seen_artifacts.add(local_name)
                            candidates_list.append(
                                {
                                    "artifact_id": str(art_id),
                                    "artifact": full_name,
                                    "kind": kind_map.get(local_name, "symbol"),
                                }
                            )
                    for local_name in sorted(art_state.get("own_symbols", []) or []):
                        if local_name not in seen_artifacts:
                            full_name = f"{target_module}::{local_name}"
                            candidates_list.append(
                                {
                                    "artifact_id": str(art_path_to_id.get(full_name, "")),
                                    "artifact": full_name,
                                    "kind": kind_map.get(str(local_name), "symbol"),
                                }
                            )
                            seen_artifacts.add(local_name)

                    from contextor.core.api.public_api import extract_public_api

                    canonical_public_api = set(extract_public_api(symbols)) if symbols else set()

                    def _candidate_rank_key(item: dict) -> tuple:
                        full_name = item.get("artifact", "")
                        kind = item.get("kind", "symbol")
                        local = str(full_name).split("::", 1)[-1].split("(", 1)[0]
                        parts = local.split(".")
                        leaf = parts[-1]
                        is_dunder = leaf.startswith("__") and leaf.endswith("__")
                        is_private_leaf = leaf.startswith("_") and not is_dunder
                        has_priv_parent = any(
                            p.startswith("_") and not (p.startswith("__") and p.endswith("__"))
                            for p in parts[:-1]
                        )
                        is_canonical_public = local in canonical_public_api

                        if is_canonical_public:
                            kind_order = {"class": 0, "function": 1, "method": 2, "global": 3}.get(kind, 4)
                            tier = (0, kind_order)
                        elif not has_priv_parent and not is_private_leaf and not is_dunder:
                            kind_order = {"class": 0, "function": 1, "method": 2, "global": 3}.get(kind, 4)
                            tier = (1, kind_order)
                        elif not has_priv_parent and is_dunder:
                            tier = (2, 0)
                        elif not has_priv_parent and is_private_leaf:
                            tier = (3, 0)
                        else:
                            tier = (4, 0)
                        return (tier, local)

                    candidates_list.sort(key=_candidate_rank_key)
                    items, total, truncated = _bounded_items(candidates_list, max_items)
                    return json.dumps(
                        {
                            "target": artifact_name,
                            "resolved_as": "module",
                            "module": target_module,
                            "module_id": target_module_id,
                            "suggested_next_tool": "get_module_context",
                            "artifact_candidates": {
                                "total": total,
                                "items": items,
                                "truncated": truncated,
                            },
                            "warnings": [
                                "Target resolved to a module rather than an artifact. "
                                "Use get_module_context for module-level context or choose one of the artifact candidates."
                            ],
                        },
                        indent=2,
                    )
            return f"Artifact '{artifact_name}' not found in the registry."

        return f"Artifact '{artifact_name}' not found in canonical LIVE state."
    except Exception as e:
        return f"Error calculating artifact blast radius: {e}"


@mcp.tool(description=short_description('search_artifacts'))
def search_artifacts(
    repo_path: str,
    search_term: str,
    limit: int | None = 20,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    engine = mcp_runtime.get_or_init_engine(root)
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
            unavailable = _module_truth_unavailable(engine.state, mod_path)
            module_leaf = mod_path.rsplit(".", 1)[-1]
            if search_term.casefold() in mod_path.casefold():
                if unavailable:
                    return json.dumps(unavailable, indent=2)
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
                inbound_items, inbound_total, inbound_truncated = _bounded_items(
                    inbound, evidence_limit
                )
                outbound_items, outbound_total, outbound_truncated = _bounded_items(
                    outbound, evidence_limit
                )
                module_entry = {
                    "kind": "module",
                    "module_id": engine.registry.get_module_id(mod_path),
                    "dependencies_inbound": {
                        "total": inbound_total,
                        "truncated": inbound_truncated,
                    },
                    "dependencies_outbound": {
                        "total": outbound_total,
                        "truncated": outbound_truncated,
                    },
                }
                if not compact:
                    module_entry["dependencies_inbound"]["items"] = inbound_items
                    module_entry["dependencies_outbound"]["items"] = outbound_items
                found_modules.append(
                    (
                        not exact_module,
                        mod_path.casefold(),
                        mod_path,
                        module_entry,
                    )
                )
        for mod_path, mod_arts in engine.state.artifacts.items():
            unavailable = _module_truth_unavailable(engine.state, mod_path)
            symbols = mod_arts.get("symbols", {})
            for category, kind in kind_by_category.items():
                raw_names = symbols.get(category, [])
                names = raw_names.keys() if isinstance(raw_names, dict) else raw_names
                for raw_name in names:
                    name = str(raw_name)
                    if search_term.lower() in name.lower():
                        if unavailable:
                            return json.dumps(unavailable, indent=2)
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

                        consumer_items, consumer_total, consumer_truncated = _bounded_items(
                            consumer_paths, evidence_limit
                        )
                        artifact_entry = {
                            "kind": kind,
                            "definer_module_path": mod_path,
                            "definer_module_id": definer_mod,
                            "consumers": {
                                "total": consumer_total,
                                "truncated": consumer_truncated,
                            },
                        }
                        if not compact:
                            artifact_entry["consumers"]["items"] = consumer_items
                        found_artifacts.append((name.lower() != search_term.lower(), name.lower(), f"{mod_path}::{name}", artifact_entry))

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
        result = {
            "query": search_term,
            "match_count": len(selected),
            "total_matches": total,
            "truncated": truncated,
            "modules": {item[3]: item[4] for item in selected_modules},
            "artifacts": {item[3]: item[4] for item in selected_artifacts},
        }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for search_artifacts",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting artifact context from live state: {e}"


@mcp.tool(description=short_description('get_symbol_implementation'))
def get_symbol_implementation(
    repo_path: str,
    symbol: str,
    file_paths: list[str],
    mode: str = "preview",
    include: list[str] | None = None,
    methods: list[str] | None = None,
    member_limit: int | None = 50,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return json.dumps({"status": "error", "error": f"Repository path '{root}' does not exist."}, indent=2)
    mcp_runtime.publish_live_status(root, f"MCP: reading symbol {symbol}")
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"preview", "fetch"}:
        return json.dumps(
            {"status": "error", "error": "mode must be 'preview' or 'fetch'."},
            indent=2,
        )
    try:
        candidates = []
        for path in _resolve_symbol_source_paths(root, file_paths):
            candidates.extend(_ast_symbol_candidates(path, symbol))
    except (OSError, SyntaxError, UnicodeDecodeError, SourceError, ValueError) as exc:
        return json.dumps({"status": "error", "error": str(exc)}, indent=2)

    if not candidates:
        return json.dumps(
            {
                "status": "not_found",
                "symbol": symbol,
                "searched_files": file_paths,
                "message": "No exact class, function, or method match was found.",
            },
            indent=2,
        )
    if len(candidates) != 1:
        return json.dumps(
            {
                "status": "ambiguous",
                "symbol": symbol,
                "candidate_count": len(candidates),
                "candidates": [
                    {
                        "symbol": item["symbol"],
                        "file_path": item["file_path"],
                        "kind": item["kind"],
                        "lines": {"start": item["start_line"], "end": item["end_line"]},
                    }
                    for item in candidates
                ],
                "message": "Narrow file_paths or use a qualified symbol; no implementation was selected.",
            },
            indent=2,
        )

    candidate = candidates[0]
    preview = _symbol_preview(root, candidate, member_limit)
    if normalized_mode == "preview":
        return json.dumps(preview, indent=2, ensure_ascii=False)

    allowed_sections = set(preview["available_sections"])
    selected_sections = list(include or [])
    if not selected_sections:
        return json.dumps(
            {
                "status": "selection_required",
                "message": "Fetch requires an explicit include selection. Run preview to compare costs.",
                "allowed_sections": sorted(allowed_sections),
            },
            indent=2,
        )
    unknown_sections = sorted(set(selected_sections) - allowed_sections)
    if unknown_sections:
        return json.dumps(
            {
                "status": "error",
                "error": "Unsupported include sections.",
                "unknown_sections": unknown_sections,
                "allowed_sections": sorted(allowed_sections),
            },
            indent=2,
        )
    if "implementation" in selected_sections and "methods" in selected_sections:
        return json.dumps(
            {
                "status": "error",
                "error": "implementation and methods are mutually exclusive.",
            },
            indent=2,
        )
    if "methods" in selected_sections and not methods:
        return json.dumps(
            {
                "status": "selection_required",
                "message": "Fetching methods requires explicit method names from preview.methods.items.",
            },
            indent=2,
        )

    resolution = preview["resolution"]
    result: dict[str, Any] = {
        "status": "resolved",
        "mode": "fetch",
        "resolution": resolution,
        "source_contract": preview["source_contract"],
    }
    node = candidate["node"]
    if "signature" in selected_sections:
        result["signature"] = _symbol_signature(node)
    if "docstring" in selected_sections:
        result["docstring"] = candidate["docstring"]
    if "implementation" in selected_sections:
        result["implementation"] = candidate["source"]
    if "static_context" in selected_sections:
        result["static_context"] = _symbol_static_context(root, candidate)
    if "methods" in selected_sections:
        source_lines = read_source(Path(candidate["file_path"])).splitlines(keepends=True)
        available_methods = {
            child.name: child
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        unknown_methods = sorted(set(methods or []) - set(available_methods))
        if unknown_methods:
            return json.dumps(
                {
                    "status": "error",
                    "error": "Unknown class methods.",
                    "unknown_methods": unknown_methods,
                    "available_methods": sorted(available_methods),
                },
                indent=2,
            )
        complete_methods = []
        for name in methods or []:
            child = available_methods[name]
            start_line = min(
                [getattr(decorator, "lineno", child.lineno) for decorator in child.decorator_list]
                or [child.lineno]
            )
            end_line = getattr(child, "end_lineno", child.lineno)
            complete_methods.append(
                {
                    "name": name,
                    "kind": "method",
                    "lines": {"start": start_line, "end": end_line},
                    "implementation": "".join(source_lines[start_line - 1 : end_line]),
                }
            )
        result["methods"] = complete_methods
    result["actual_response_size"] = _json_size(result)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool(description=short_description('get_file_edit_context'))
def get_file_edit_context(
    repo_path: str,
    file_path: str = "",
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
    mode: str | None = None,
    target: str | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    # Validate mode explicitly
    if mode is not None and mode != "minimal":
        return json.dumps(
            {
                "error": f"Unsupported mode '{mode}'. Allowed modes are: None (legacy), 'minimal'.",
                "allowed_modes": [None, "minimal"],
            },
            indent=2,
        )

    # Read registries & catalog for canonical resolution
    from contextor.core.report_query import IndexCatalog, catalog_from_registry, resolve_index_query

    mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)
    catalog = catalog_from_registry(str(root))
    if not catalog.modules and mod_id_to_path:
        catalog = IndexCatalog(
            modules=mod_id_to_path,
            artifacts=art_id_to_path,
            module_paths={name: name.replace(".", "/") + ".py" for name in mod_path_to_id},
            recovered_modules={},
            recovered_artifacts={},
        )

    # Handle input target resolution and canonical conflict detection
    effective_file = (file_path or "").strip()
    effective_target = (target or "").strip()

    if effective_file and effective_target:
        res_file = resolve_index_query(effective_file, catalog, repo_root=str(root))
        res_target = resolve_index_query(effective_target, catalog, repo_root=str(root))
        matches_file = res_file.get("matches", [])
        matches_target = res_target.get("matches", [])
        if matches_file and matches_target:
            m_f = matches_file[0]
            m_t = matches_target[0]
            if (
                (m_f.get("id") != m_t.get("id"))
                or (m_f.get("name") != m_t.get("name"))
                or (m_f.get("kind") != m_t.get("kind"))
            ):
                return json.dumps(
                    {
                        "error": "Conflicting 'file_path' and 'target' arguments provided. Resolved to different canonical targets.",
                        "file_path": effective_file,
                        "file_path_resolved": {"id": m_f.get("id"), "name": m_f.get("name"), "kind": m_f.get("kind")},
                        "target": effective_target,
                        "target_resolved": {"id": m_t.get("id"), "name": m_t.get("name"), "kind": m_t.get("kind")},
                    },
                    indent=2,
                )
        elif effective_file != effective_target:
            # Fallback string comparison when unindexed
            try:
                norm_file = Path(effective_file).resolve().relative_to(root).as_posix()
            except ValueError:
                norm_file = effective_file.replace("\\", "/").lstrip("./")
            try:
                norm_target = Path(effective_target).resolve().relative_to(root).as_posix()
            except ValueError:
                norm_target = effective_target.replace("\\", "/").lstrip("./")
            if norm_file != norm_target and norm_file.replace("/", ".").rstrip(".py") != norm_target:
                return json.dumps(
                    {
                        "error": "Conflicting 'file_path' and 'target' arguments provided. Provide only one.",
                        "file_path": file_path,
                        "target": target,
                    },
                    indent=2,
                )

    query_input = effective_target or effective_file
    if not query_input:
        return json.dumps({"error": "Either 'target' or 'file_path' must be provided."}, indent=2)

    # -------------------------------------------------------------------------
    # MINIMAL PRE-EDIT PROJECTION (mode == "minimal")
    # -------------------------------------------------------------------------
    if mode == "minimal":
        try:
            from contextor.core.analysis.incremental.graph_ops import calculate_affected_set

            resolution = resolve_index_query(query_input, catalog, repo_root=str(root))

            if not resolution.get("matches"):
                return json.dumps(
                    {
                        "status": "not_found",
                        "target": query_input,
                        "reason": resolution.get("reason", "no_matching_entry"),
                        "suggestions": resolution.get("suggestions", []),
                    },
                    indent=2,
                )

            top = resolution["matches"][0]
            kind = top.get("kind")

            # Handling artifact / symbol input
            if kind == "artifact":
                art_name = top["name"]
                art_id = top["id"]
                definer_mod = art_name.split("::", 1)[0]
                definer_file = (catalog.module_paths or {}).get(definer_mod) or definer_mod.replace(".", "/") + ".py"
                return json.dumps(
                    {
                        "target": query_input,
                        "resolved_as": "artifact",
                        "artifact": art_name,
                        "artifact_id": art_id,
                        "definer_module": definer_mod,
                        "definer_file": definer_file,
                        "suggested_next_tool": "get_artifact_blast_radius",
                        "warnings": [
                            "Target resolved to an artifact/symbol rather than a module. "
                            "Use get_artifact_blast_radius for symbol-level consumption."
                        ],
                    },
                    indent=2,
                )

            module_name = top["name"]
            module_id = top["id"]
            file_path_resolved = (catalog.module_paths or {}).get(module_name) or module_name.replace(".", "/") + ".py"

            engine = mcp_runtime.get_or_init_engine(root)
            if not engine or getattr(engine.state, "resync_required", False):
                return json.dumps(
                    {
                        "status": "unavailable",
                        "reason": "No usable canonical LIVE state. Run analyze_project first.",
                    },
                    indent=2,
                )
            unavailable = _module_truth_unavailable(engine.state, module_name)
            if unavailable:
                return json.dumps(unavailable, indent=2)
            live_graph = getattr(engine.state, "dependency_graph", None)
            if live_graph is None:
                return json.dumps(
                    {
                        "status": "unavailable",
                        "reason": "Canonical LIVE dependency graph is unavailable. Run analyze_project first.",
                    },
                    indent=2,
                )

            direct_consumers = []
            transitive_count = 0

            if live_graph:
                consumer_modules = {
                    src
                    for edge_map in (live_graph.hard_edges, live_graph.soft_edges)
                    for src, targets in edge_map.items()
                    if module_name in targets
                }
                direct_consumers = sorted(consumer_modules)
                affected = calculate_affected_set(module_name, new_graph=live_graph)
                transitive_count = len(affected - {module_name})

            reachability_hard = getattr(live_graph, "hard_edges", {}) if live_graph else {}
            reachability_soft = getattr(live_graph, "soft_edges", {}) if live_graph else {}
            graph_modules = set(reachability_hard) | set(reachability_soft)
            for edge_map in (reachability_hard, reachability_soft):
                for tgts in edge_map.values():
                    graph_modules.update(tgts)

            test_modules = {
                name
                for name in graph_modules
                if name.startswith("tests.") or name == "tests" or name.rsplit(".", 1)[-1].startswith("test_")
            }
            if engine and getattr(engine.state, "cached_analytics_state", "deferred") == "fresh":
                cached = getattr(engine.state, "cached_analytics", {}) or {}
                canonical_layers = cached.get("module_layers", {}) if isinstance(cached, dict) else {}
                test_modules.update(
                    name for name, layer in canonical_layers.items() if layer == "tests"
                )

            mod_path_to_id = {name: mid for mid, name in catalog.modules.items()}
            tests_covering = _static_test_reachability(
                module_name,
                reachability_hard,
                reachability_soft,
                test_modules,
                mod_path_to_id,
            )

            sample_limit = 5 if max_items is None or max_items == 30 else max_items
            sample_consumers = direct_consumers[:sample_limit]
            test_names = [t["module"] for t in tests_covering]
            sample_tests = test_names[:sample_limit]

            warnings = []
            layer = "unknown"
            if engine:
                cached_analytics = getattr(engine.state, "cached_analytics", {}) or {}
                cached_state = getattr(engine.state, "cached_analytics_state", "deferred")
                if cached_state == "fresh":
                    module_layers = cached_analytics.get("module_layers", {}) if isinstance(cached_analytics, dict) else {}
                    if module_name in module_layers:
                        layer = module_layers[module_name]
                    else:
                        warnings.append(f"Canonical module_layers entry not found for '{module_name}'.")

            risk_score = None
            if engine:
                topo = getattr(engine.state, "topology_analytics", {}) or {}
                topo_state = getattr(engine.state, "topology_metrics_state", "deferred")
                if topo_state == "fresh":
                    module_risk_map = topo.get("module_risk", {}) if isinstance(topo, dict) else {}
                    if module_name in module_risk_map:
                        risk_score = module_risk_map[module_name]
                    else:
                        warnings.append(f"Canonical module_risk not computed for '{module_name}'.")

            layer_guard = {"available": False}
            if engine:
                if cached_state == "fresh":
                    from contextor.core.validator.rules import FORBIDDEN_LAYER_RULES, FORBIDDEN_PREFIX_RULES

                    forbidden_outbound_layers = [r[1] for r in FORBIDDEN_LAYER_RULES if r[0] == layer]
                    forbidden_outbound_prefixes = [r[1] for r in FORBIDDEN_PREFIX_RULES if r[0] == layer]
                    outbound_rules_defined = bool(forbidden_outbound_layers or forbidden_outbound_prefixes)

                    raw_violations = cached_analytics.get("layer_violations", []) if isinstance(cached_analytics, dict) else []
                    outbound_violations = [
                        v for v in raw_violations
                        if len(v.get("nodes", [])) >= 2 and v["nodes"][0] == module_name
                    ]
                    inbound_violations = [
                        v for v in raw_violations
                        if len(v.get("nodes", [])) >= 2 and v["nodes"][1] == module_name
                    ]

                    all_module_violations = []
                    for v in outbound_violations:
                        all_module_violations.append(
                            {
                                "direction": "outbound",
                                "kind": v.get("kind", "LAYER"),
                                "source_module": v["nodes"][0],
                                "target_module": v["nodes"][1],
                                "message": v.get("message", ""),
                            }
                        )
                    for v in inbound_violations:
                        all_module_violations.append(
                            {
                                "direction": "inbound",
                                "kind": v.get("kind", "LAYER"),
                                "source_module": v["nodes"][0],
                                "target_module": v["nodes"][1],
                                "message": v.get("message", ""),
                            }
                        )

                    sample_violations, total_v, truncated_v = _bounded_items(
                        all_module_violations, 5
                    )

                    layer_guard = {
                        "available": True,
                        "outbound_rules_defined": outbound_rules_defined,
                        "outbound_violation_count": len(outbound_violations),
                        "inbound_violation_count": len(inbound_violations),
                        "violations": {
                            "total": total_v,
                            "items": sample_violations,
                            "truncated": truncated_v,
                        },
                    }
                    if forbidden_outbound_layers:
                        layer_guard["forbidden_outbound_layers"] = forbidden_outbound_layers
                    if forbidden_outbound_prefixes:
                        layer_guard["forbidden_outbound_prefixes"] = forbidden_outbound_prefixes
                    if outbound_rules_defined or len(outbound_violations) > 0 or len(inbound_violations) > 0:
                        layer_guard["suggested_next_tool"] = "get_layer_isolation"
                else:
                    layer_guard = {
                        "available": False,
                        "reason": f"Cached analytics state is '{cached_state}'.",
                    }

            live_revision = mcp_runtime._live_engine_revisions.get(str(root)) if engine else None

            return json.dumps(
                {
                    "target": query_input,
                    "resolved_as": "module",
                    "module": module_name,
                    "module_id": module_id,
                    "file": file_path_resolved,
                    "live_revision": live_revision,
                    "layer": layer,
                    "risk_score": risk_score,
                    "layer_guard": layer_guard,
                    "consumers": {
                        "direct_count": len(direct_consumers),
                        "transitive_count": transitive_count,
                        "sample": sample_consumers,
                        "truncated": len(direct_consumers) > len(sample_consumers),
                    },
                    "tests_covering": {
                        "count": len(test_names),
                        "sample": sample_tests,
                        "truncated": len(test_names) > len(sample_tests),
                    },
                    "warnings": warnings,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": f"Error in minimal pre-edit context: {e}"}, indent=2)

    # -------------------------------------------------------------------------
    # LEGACY GET_FILE_EDIT_CONTEXT PATH (mode is None or unsupported mode)
    # -------------------------------------------------------------------------
    # Deriving module name from file path
    target_path = Path(query_input).expanduser()
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
    
    engine = mcp_runtime.get_or_init_engine(root)
    if not engine or getattr(engine.state, "resync_required", False):
        return "Error: No usable canonical LIVE state. Run analyze_project first."
        
    try:
        state = engine.state
        unavailable = _module_truth_unavailable(state, module_name)
        if unavailable:
            return json.dumps(unavailable, indent=2)
        state_metrics = getattr(state, "metrics", {}) or {}
        candidate_metrics = state_metrics.get(module_name, {}) if isinstance(state_metrics, dict) else {}
        mod_info = candidate_metrics if isinstance(candidate_metrics, dict) else {}
        cached_analytics = getattr(state, "cached_analytics", {}) or {}
        if getattr(state, "cached_analytics_state", "deferred") == "fresh":
            module_layers = cached_analytics.get("module_layers", {}) or {}
            if module_name in module_layers:
                mod_info = {**mod_info, "layer": module_layers[module_name]}
        
        risk_score = None
        topology = getattr(state, "topology_analytics", {}) or {}
        if getattr(state, "topology_metrics_state", "deferred") == "fresh":
            risk_score = (topology.get("module_risk", {}) or {}).get(module_name)
        
        # We must read registries OUTSIDE the transaction block to avoid Resource Deadlock
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)
        module_to_id = {
            **{path: module_id for module_id, path in mod_id_to_path.items()},
            **mod_path_to_id,
        }
        artifact_name_to_id = {
            **{name: artifact_id for artifact_id, name in art_id_to_path.items()},
            **art_path_to_id,
        }
        live_module = state.modules.get(module_name)
        mod_id = mod_path_to_id.get(module_name) or getattr(live_module, "module_id", None)
        if not mod_id:
            if live_module is None:
                return f"Error: Module '{module_name}' is not present in canonical LIVE state."
            mod_id = module_name
            
        imports = []
        consumers = []
        dependency_data_source = "live_canonical_graph"
        artifact_data_source = "live_registry_and_symbol_state"
        live_graph = state.dependency_graph
        reachability_hard = {}
        reachability_soft = {}
        if module_name in state.modules and live_graph:
            reachability_hard = live_graph.hard_edges
            reachability_soft = live_graph.soft_edges
            target_modules = set(live_graph.hard_edges.get(module_name, set()))
            target_modules.update(live_graph.soft_edges.get(module_name, set()))
            imports = [module_to_id.get(target, target) for target in sorted(target_modules)]
            consumer_modules = {
                source
                for edge_map in (live_graph.hard_edges, live_graph.soft_edges)
                for source, targets in edge_map.items()
                if module_name in targets
            }
            consumers = [module_to_id.get(source, source) for source in sorted(consumer_modules)]
            dependency_data_source = "live_canonical_graph"
                        
        # Resolve public API artifact IDs to human-readable names so an
        # LLM does not need a separate lookup_index_entries call.
        public_api = {}
        unresolved_public_api_ids = []
        if module_name in state.artifacts:
            prefix = module_name + "::"
            module_artifacts = state.artifacts[module_name]
            symbols = module_artifacts.get("symbols", {}) or {}
            for local_name in sorted(_canonical_symbol_catalog(module_artifacts)):
                leaf = local_name.rsplit(".", 1)[-1]
                if leaf.startswith("_") and not (
                    leaf.startswith("__") and leaf.endswith("__")
                ):
                    continue
                full_name = prefix + local_name
                artifact_key = str(artifact_name_to_id.get(full_name, full_name))
                public_api[artifact_key] = full_name
        
        graph_modules = set(reachability_hard) | set(reachability_soft)
        graph_modules.update(
            target
            for edge_map in (reachability_hard, reachability_soft)
            for targets in edge_map.values()
            for target in targets
        )
        test_modules = {
            name
            for name in graph_modules
            if name.startswith("tests.")
            or name == "tests"
            or name.rsplit(".", 1)[-1].startswith("test_")
        }
        if getattr(state, "cached_analytics_state", "deferred") == "fresh":
            canonical_layers = cached_analytics.get("module_layers", {}) if isinstance(cached_analytics, dict) else {}
            test_modules.update(
                name for name, layer in canonical_layers.items() if layer == "tests"
            )
        tests_covering = _static_test_reachability(
            module_name,
            reachability_hard,
            reachability_soft,
            test_modules,
            {
                **{path: module_id for module_id, path in mod_id_to_path.items()},
                **mod_path_to_id,
            },
        )

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
        
        common_result = {
            "file": file_path,
            "file_exists": target_path.is_file(),
            "module": module_name,
            "module_id": mod_id,
            "layer": mod_info.get("layer", "unknown"),
            "entrypoint": mod_info.get("entrypoint", False),
            "risk_score": risk_score,
            "dependency_data_source": dependency_data_source,
            "artifact_data_source": artifact_data_source,
        }
        full_result = {
            **common_result,
            "public_api": {
                "items": dict(public_api_items),
                "total": public_api_total,
                "truncated": public_api_truncated,
                "unresolved_ids": sorted(set(unresolved_public_api_ids)),
                "unresolved_total": len(set(unresolved_public_api_ids)),
            },
            "imports": {
                "items": [
                    {
                        "module_id": mod_path_to_id.get(item, item),
                        "module": mod_id_to_path.get(item, item),
                    }
                    for item in import_items
                ],
                "total": imports_total,
                "truncated": imports_truncated,
            },
            "consumers": {
                "items": [
                    {
                        "module_id": mod_path_to_id.get(item, item),
                        "module": mod_id_to_path.get(item, item),
                    }
                    for item in consumer_items
                ],
                "total": consumers_total,
                "truncated": consumers_truncated,
            },
            "tests_covering": {
                "available": tests_total > 0,
                "total": tests_total,
                "truncated": tests_truncated,
                "evidence_scope": "static_dependency_reachability",
                "max_depth": 6,
                "tests": test_items,
            }
        }

        compact_result = {
            **common_result,
            "public_api": {
                key: full_result["public_api"][key]
                for key in ("total", "truncated", "unresolved_total")
            },
            "imports": {
                key: full_result["imports"][key]
                for key in ("total", "truncated")
            },
            "consumers": {
                key: full_result["consumers"][key]
                for key in ("total", "truncated")
            },
            "tests_covering": {
                key: full_result["tests_covering"][key]
                for key in ("available", "total", "truncated", "evidence_scope", "max_depth")
            },
        }

        result = compact_result if compact else full_result

        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps(
                    {
                        "error": "Unsupported fields for get_file_edit_context",
                        "unknown_fields": unknown_fields,
                        "allowed_fields": sorted(allowed_fields),
                    },
                    indent=2,
                )
            result = {field: result[field] for field in fields}

        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error extracting file edit context: {e}"


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
                items, total, truncated = _bounded_items(
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
        layer_items, layer_total, layer_truncated = _bounded_items(
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
        selected_entries, total_artifacts, artifacts_truncated = _bounded_items(
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


@mcp.tool(description=short_description('get_artifacts_for_module'))
def get_artifacts_for_module(
    repo_path: str,
    module_name: str,
    include_consumers: bool = True,
    symbol_filter: str = "",
    limit: int | None = 50,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
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

    try:
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."
        state = engine.state
        unavailable = _module_truth_unavailable(state, module_name)
        if unavailable:
            return json.dumps(unavailable, indent=2)
        live_modules = getattr(state, "modules", {}) or {}
        live_artifact_catalog = getattr(state, "artifacts", {}) or {}
        live_artifacts = live_artifact_catalog.get(module_name, {})
        mod_compact_id = mod_path_to_id.get(module_name)
        live_module = live_modules.get(module_name)
        if not mod_compact_id and live_module is not None:
            mod_compact_id = getattr(live_module, "module_id", None)
            if mod_compact_id is None and isinstance(live_module, dict):
                mod_compact_id = live_module.get("module_id")
        if not mod_compact_id and live_module is None and not live_artifacts:
            return (
                f"Module '{module_name}' not found in registry or canonical LIVE state. "
                "Check the module name or run an analysis."
            )

        result_artifacts: dict = {}
        live_symbols = live_artifacts.get("symbols", {})
        signatures = live_symbols.get("signatures", {}) or {}
        for symbol, kind in _canonical_symbol_catalog(live_artifacts).items():
            full_name = f"{module_name}::{symbol}"
            artifact_id = art_path_to_id.get(full_name)
            key = artifact_id or full_name
            entry = {
                "artifact_id": artifact_id,
                "symbol": symbol,
                "full_name": full_name,
                "kind": kind,
                "signature": signatures.get(symbol),
            }
            if include_consumers:
                consumers = _canonical_symbol_consumers(state, module_name, symbol)
                consumer_items, consumer_total, consumer_truncated = _bounded_items(
                    consumers, evidence_limit
                )
                entry["consumers"] = {
                    "total": consumer_total,
                    "truncated": consumer_truncated,
                }
                if not compact:
                    entry["consumers"]["items"] = consumer_items
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

        result = {
                "module": module_name,
                "module_id": mod_compact_id,
                "artifact_count": len(selected),
                "total_artifact_count": total_count,
                "truncated": truncated,
                "symbol_filter": symbol_filter or None,
                "data_sources": ["live_symbol_state"],
                "complete_symbol_catalog": True,
                "artifacts": dict(selected),
            }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for get_artifacts_for_module",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error reading artifacts for module: {e}"


@mcp.tool(description=short_description('lookup_artifact_by_symbol'))
def lookup_artifact_by_symbol(
    repo_path: str,
    symbol_name: str,
    limit: int | None = 20,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    root = Path(repo_path).expanduser().resolve()
    try:
        _, _, art_path_to_id, _ = _read_registries(root)
        engine = mcp_runtime.get_or_init_engine(root)
        if not engine or getattr(engine.state, "resync_required", False):
            return "Error: No usable canonical LIVE state. Run analyze_project first."

        state = engine.state
        term = symbol_name.casefold()
        candidates = []
        for module_name, module_data in sorted((state.artifacts or {}).items()):
            unavailable = _module_truth_unavailable(state, module_name)
            for symbol, kind in _canonical_symbol_catalog(module_data).items():
                if term not in symbol.casefold():
                    continue
                if unavailable:
                    return json.dumps(unavailable, indent=2)
                full_name = f"{module_name}::{symbol}"
                artifact_id = art_path_to_id.get(full_name)
                key = artifact_id or full_name
                candidates.append(
                    (symbol.casefold() != term, symbol.casefold(), full_name, key, kind)
                )

        candidates.sort()
        if candidates and not candidates[0][0]:
            candidates = [item for item in candidates if not item[0]]
        if len(candidates) > 1 and not candidates[0][0]:
            return json.dumps(
                {
                    "error": "Ambiguous canonical symbol identity.",
                    "query": symbol_name,
                    "candidates": [item[2] for item in candidates],
                    "data_source": "live_canonical_state",
                },
                indent=2,
            )
        candidates, total_matches, matches_truncated = _bounded_items(
            candidates, limit
        )

        if not candidates:
            return f"No current artifacts found matching '{symbol_name}'."

        results: dict = {}
        for _, _, full_name, key, kind in candidates:
            module_name, symbol = full_name.split("::", 1)
            entry = {
                "symbol": symbol,
                "full_name": full_name,
                "kind": kind,
                "definer_module": module_name,
            }
            if artifact_consumption_is_fresh(state):
                resolved_consumers = _canonical_symbol_consumers(
                    state, module_name, symbol
                )
                consumer_items, consumer_total, consumer_truncated = _bounded_items(
                    resolved_consumers, evidence_limit
                )
                entry["consumers"] = {
                    "total": consumer_total,
                    "truncated": consumer_truncated,
                }
                if not compact:
                    entry["consumers"]["items"] = consumer_items
            else:
                entry["consumers"] = {
                    "available": False,
                    "state": getattr(state, "artifact_consumption_state", "deferred"),
                    "reason": "Canonical artifact consumption is unavailable or stale.",
                }
            results[key] = entry

        result = {
                "query": symbol_name,
                "match_count": len(results),
                "total_matches": total_matches,
                "truncated": matches_truncated,
                "data_source": "live_canonical_state",
                "artifacts": results,
            }
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps({
                    "error": "Unsupported fields for lookup_artifact_by_symbol",
                    "unknown_fields": unknown_fields,
                    "allowed_fields": sorted(allowed_fields),
                }, indent=2)
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error searching artifacts by symbol: {e}"


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
