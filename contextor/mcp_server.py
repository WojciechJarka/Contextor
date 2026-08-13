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
import asyncio
import ast
import hashlib
import json
import os
import subprocess
import sys
import glob
import warnings
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


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
        [str(interpreter), "-u", "-m", "contextor.mcp_server", *sys.argv[1:]],
    )
    raise RuntimeError("Contextor MCP virtual-environment re-exec returned unexpectedly.")


_ensure_virtual_environment()

# Suppress all warnings (like AuthlibDeprecationWarning) to prevent JSON-RPC stream corruption
warnings.filterwarnings("ignore")

from fastmcp import FastMCP
from contextor.core.api.facade import ContextorFacade
from contextor.core.canonical_state_query import (
    describe_contract as _describe_canonical_contract,
    execute_projection as _execute_canonical_projection,
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

# Initialize FastMCP Server
mcp = FastMCP("Contextor")

# Global state to maintain incremental engines across MCP sessions
_live_engines: dict[str, Any] = {}
_live_engine_revisions: dict[str, int] = {}
_analysis_lock = threading.Lock()
_analysis_job_lock = threading.RLock()
_analysis_tasks: dict[str, threading.Thread] = {}
_analysis_jobs_by_repo: dict[str, str] = {}


def _mcp_cache_root(root: Path) -> Path:
    """Shared application cache root used by desktop and MCP."""
    from contextor.core.paths import app_cache_dir

    return app_cache_dir()


def _publish_mcp_live_status(root: Path, message: str) -> None:
    """Best-effort status for the desktop LIVE bar; never fails a tool call."""
    try:
        from contextor.core.live_state import connect

        client = connect(root)
        if client is not None:
            client.status(message, origin="mcp")
    except (OSError, EOFError, RuntimeError):
        pass


def _analysis_job_dir(root: Path) -> Path:
    """Return the persistent MCP analysis-job directory for one repository."""

    return root / ".contextor" / "analysis_jobs"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(root: Path, job_id: str) -> Path:
    if len(job_id) != 32 or any(char not in "0123456789abcdef" for char in job_id):
        raise ValueError("Invalid analysis job ID.")
    return _analysis_job_dir(root) / f"{job_id}.json"


def _write_analysis_job(root: Path, job: dict) -> None:
    """Atomically persist one job so client disconnects cannot lose its status."""

    directory = _analysis_job_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    target = _job_path(root, str(job["job_id"]))
    # Job progress is written from worker threads and can also be observed by
    # another MCP process. A per-write sibling avoids collisions on Windows.
    temporary = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
    payload = {**job, "updated_at": _utc_now()}
    with _analysis_job_lock:
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, target)


def _read_analysis_job(root: Path, job_id: str) -> dict | None:
    try:
        path = _job_path(root, job_id)
    except ValueError:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _latest_analysis_job(root: Path) -> dict | None:
    directory = _analysis_job_dir(root)
    if not directory.is_dir():
        return None
    candidates = sorted(
        directory.glob("*.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    for path in candidates:
        job = _read_analysis_job(root, path.stem)
        if job is not None:
            return job
    return None


def _public_job(
    job: dict,
    *,
    reused: bool = False,
    max_skipped_files: int | None = 10,
) -> dict:
    """Return a stable, JSON-safe job view intended for an MCP client."""

    visible = {
        key: job.get(key)
        for key in (
            "job_id",
            "operation",
            "repo_path",
            "target",
            "status",
            "created_at",
            "started_at",
            "completed_at",
            "updated_at",
            "message",
            "error",
        )
    }
    if "skipped_python_files" in job:
        skipped_files = list(job["skipped_python_files"])
        selected, total, truncated = _bounded_items(skipped_files, max_skipped_files)
        visible["analysis_coverage"] = {
            "skipped_python_files": {
                "total": total,
                "syntax_error_count": sum(
                    "not valid Python" in str(item.get("reason", ""))
                    for item in skipped_files
                ),
                "truncated": truncated,
                "items": selected,
            }
        }
    visible["reused"] = reused
    return visible



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
    log=None,
) -> dict:
    """Run analysis in-process without blocking the FastMCP event loop.

    Codex Desktop can start the child interpreter but leaves it stalled before
    Python reaches ``contextor.mcp_worker.main``.  The MCP-only sequential mode
    avoids both that child interpreter and nested process pools.
    """
    import asyncio
    effective_log = log or _stderr_log

    def run() -> dict:
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
                        log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                    if result is None:
                        raise RuntimeError("Analysis returned no canonical state.")
                    summary_data = getattr(result, "summary_data", {}) or {}
                    skipped_files = summary_data.get("skipped_files", [])
                    if not isinstance(skipped_files, list):
                        skipped_files = []
                    return {"skipped_python_files": skipped_files}
                elif operation == "layer":
                    ContextorFacade.analyze_layer(
                        str(root),
                        str(target),
                        log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                elif operation == "single_file":
                    ContextorFacade.analyze_single_file(
                        str(target),
                        str(root),
                        log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                else:
                    raise ValueError(f"Unsupported analysis operation: {operation}")
                return {}
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

    return await asyncio.to_thread(run)


async def _execute_analysis_job(
    root: Path,
    job: dict,
    target: Path | None,
    exclude_paths: list[str] | None,
) -> None:
    """Execute one accepted analysis and leave a durable terminal status."""

    job = {
        **job,
        "status": "running",
        "started_at": _utc_now(),
        "message": "Analysis started.",
    }
    _write_analysis_job(root, job)

    def job_log(message: str) -> None:
        nonlocal job
        _stderr_log(message)
        job = {**job, "message": str(message)}
        _write_analysis_job(root, job)

    try:
        analysis_outcome = await _run_analysis_worker(
            str(job["operation"]),
            root,
            target,
            exclude_paths,
            log=job_log,
        )
        if job["operation"] == "project":
            _live_engines.pop(str(root), None)
            engine = _get_or_init_engine(root)
            if engine is None:
                raise RuntimeError(
                    "Analysis completed but canonical state could not be loaded."
                )
            from contextor.core.live_state import connect_or_start

            live_client = connect_or_start(root)
            published = live_client.publish(engine.state, origin="mcp_analysis")
            _live_engine_revisions[str(root)] = int(published["revision"])
        job = {
            **job,
            **(analysis_outcome or {}),
            "status": "completed",
            "completed_at": _utc_now(),
            "message": "Analysis completed successfully.",
            "error": None,
        }
        _write_analysis_job(root, job)
    except Exception as exc:
        job = {
            **job,
            "status": "failed",
            "completed_at": _utc_now(),
            "message": "Analysis failed.",
            "error": f"{type(exc).__name__}: {exc}",
        }
        _write_analysis_job(root, job)
    finally:
        with _analysis_job_lock:
            _analysis_tasks.pop(str(job["job_id"]), None)
            if _analysis_jobs_by_repo.get(str(root)) == job["job_id"]:
                _analysis_jobs_by_repo.pop(str(root), None)


def _start_analysis_job(
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
) -> dict:
    """Accept a non-blocking analysis, deduplicating an active job per repo."""

    repo_key = str(root)
    with _analysis_job_lock:
        active_id = _analysis_jobs_by_repo.get(repo_key)
        active_task = _analysis_tasks.get(active_id) if active_id else None
        if active_id and active_task is not None and active_task.is_alive():
            existing = _read_analysis_job(root, active_id)
            if existing is not None:
                return _public_job(existing, reused=True)

        job_id = uuid4().hex
        job = {
            "job_id": job_id,
            "operation": operation,
            "repo_path": repo_key,
            "target": str(target) if target is not None else None,
            "exclude_paths": list(exclude_paths or []),
            "status": "queued",
            "created_at": _utc_now(),
            "started_at": None,
            "completed_at": None,
            "message": "Analysis accepted.",
            "error": None,
            "owner_pid": os.getpid(),
        }
        _write_analysis_job(root, job)
        def run_job() -> None:
            """Own a dedicated loop; FastMCP may close a tool-call loop early."""
            asyncio.run(_execute_analysis_job(root, job, target, exclude_paths))

        task = threading.Thread(
            target=run_job,
            name=f"contextor-analysis-{job_id}",
            daemon=True,
        )
        _analysis_jobs_by_repo[repo_key] = job_id
        _analysis_tasks[job_id] = task
        task.start()
        return _public_job(job)


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

def _get_or_init_engine(root: Path):
    """
    Returns the live engine from RAM. If absent, HYDRATES from the .contextor cache.
    Does NOT silently trigger analyze_project.
    """
    from contextor.core.live_state import connect

    engine = _live_engines.get(str(root))
    client = connect(root)
    if client:
        remote = client.ping()
        remote_revision = int(remote.get("revision", 0))
        if remote_revision > _live_engine_revisions.get(str(root), -1):
            snapshot = client.snapshot()
            state = snapshot.get("state")
            if state is not None:
                from contextor.core.analysis.state_manager import FileStateManager
                from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
                from contextor.core.paths import repo_cache_dir
                from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

                manager = FileStateManager(str(repo_cache_dir(root)))
                engine = IncrementalAnalysisEngine(
                    state,
                    PersistentIdentityRegistry(str(root)),
                    manager,
                    str(root),
                )
                _live_engines[str(root)] = engine
                _live_engine_revisions[str(root)] = remote_revision
    if not engine:
        from contextor.core.analysis.state_manager import load_engine_state, FileStateManager
        from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
        from contextor.core.live_state import read_metadata
        from contextor.core.paths import repo_key
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
        
        cache_dir = str(_mcp_cache_root(root) / repo_key(root))
        metadata = read_metadata(cache_dir)
        state = load_engine_state(cache_dir, metadata.state_id if metadata else "")
        if state:
            state_mgr = FileStateManager(cache_dir)
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
            writer="mcp",
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


def _bounded_items(items: list, limit: int | None) -> tuple[list, int, bool]:
    """Optionally bound an MCP collection while preserving its cardinality."""
    total = len(items)
    if limit is None:
        return items, total, False
    safe_limit = max(0, int(limit))
    selected = items[:safe_limit]
    return selected, total, total > len(selected)


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
    engine = _get_or_init_engine(root)
    module_path = _module_path_for_source(root, Path(candidate["file_path"]))
    context = {
        "module": module_path,
        "consumers": {"available": False, "total": 0, "truncated": False},
        "evidence_scope": "current live canonical state; static consumers only",
    }
    if not engine:
        return context
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


# Keep well below the host tool-transport context threshold.  This is a
# transport guard, not a limit on canonical-state data held in memory.
_LEGACY_QUERY_MAX_RESPONSE_BYTES = 12 * 1024


def _legacy_query_value_summary(value) -> dict:
    """Describe a legacy query value without returning its nested payload."""
    if isinstance(value, dict):
        keys = [str(key) for key in value]
        preview = keys[:20]
        return {
            "type": "dict",
            "total_keys": len(keys),
            "keys": preview,
            "keys_truncated": len(preview) < len(keys),
        }
    if isinstance(value, (list, tuple, set)):
        return {"type": type(value).__name__, "total_items": len(value)}
    if isinstance(value, str):
        return {"type": "string", "characters": len(value)}
    return {"type": type(value).__name__}


def _bounded_query_result(value, limit: int | None) -> dict:
    """Wrap a legacy query result and prevent one nested record overfilling MCP."""
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
    bounded = {
        "result": result,
        "result_type": result_type,
        "total_items": total,
        "truncated": truncated,
    }
    encoded = json.dumps(bounded, indent=2).encode("utf-8")
    if len(encoded) <= _LEGACY_QUERY_MAX_RESPONSE_BYTES:
        return bounded

    return {
        "result": {
            "status": "payload_too_large",
            "preview": _legacy_query_value_summary(result),
        },
        "result_type": result_type,
        "total_items": total,
        "truncated": truncated,
        "payload_truncated": True,
        "original_response_bytes": len(encoded),
        "max_response_bytes": _LEGACY_QUERY_MAX_RESPONSE_BYTES,
        "recommendation": (
            "Project scalar fields in the legacy expression, or use "
            "describe_canonical_state followed by query_canonical_projection."
        ),
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
    Starts a non-blocking global architectural analysis and returns a job ID.
    Poll ``get_analysis_status`` until it reports ``completed`` or ``failed``.

    ``exclude_paths`` lets an LLM narrow this run without changing the saved
    GUI exclude configuration. Use repository-relative Python files or
    directory prefixes, for example ``["tests", "legacy/adapter.py"]``.
    Contextor already ignores non-Python files. Per-run and GUI excludes are
    combined before AST indexing.

    LLM use: choose this for a repository-wide baseline, then poll the returned
    job instead of repeating the call. Exclude ``tests`` when production
    architecture is the only concern; keep it when later queries need test
    coverage or ``tests_covering`` evidence. After a completed global job,
    inspect ``get_analysis_status(...).analysis_coverage`` before assuming the
    graph covers every Python file; it reports files skipped for syntax or read
    errors.
    """
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return f"Error: Repository path '{root}' does not exist."
    _publish_mcp_live_status(root, "MCP: analyzing full repository")
    return json.dumps(
        _start_analysis_job("project", root, exclude_paths=exclude_paths),
        indent=2,
    )

@mcp.tool()
async def analyze_layer(
    repo_path: str,
    layer_name: str,
    exclude_paths: list[str] | None = None,
) -> str:
    """
    Starts non-blocking analysis isolated to a specific layer (directory).
    Poll ``get_analysis_status`` with the returned job ID.

    ``exclude_paths`` contains repository-relative Python files or directory
    prefixes to omit from this run. It is merged with, but never persisted to,
    the GUI exclude list. Non-Python files are ignored automatically.

    LLM use: prefer this over a global run when the decision is confined to one
    package, then poll its job instead of repeating the call. Exclude unrelated
    Python trees to reduce report size, but retain tests when boundary or
    coverage evidence matters.
    """
    root = Path(repo_path).expanduser().resolve()
    layer = root / layer_name
    if not layer.is_dir():
        return f"Error: Layer path '{layer}' does not exist."
    _publish_mcp_live_status(root, f"MCP: analyzing layer {layer_name}")
    return json.dumps(
        _start_analysis_job(
            "layer", root, layer, exclude_paths=exclude_paths
        ),
        indent=2,
    )

@mcp.tool()
async def analyze_single_file(
    repo_path: str,
    file_path: str,
    exclude_paths: list[str] | None = None,
) -> str:
    """
    Starts non-blocking deep analysis on a single Python file.
    Poll ``get_analysis_status`` with the returned job ID.

    ``exclude_paths`` narrows the surrounding project context for this run.
    Entries are repository-relative Python files or directory prefixes and are
    combined with the saved GUI excludes without modifying them. Do not exclude
    the target file itself.

    LLM use: choose this for a focused symbol/API decision, then poll its job
    instead of repeating the call. Exclude unrelated packages to save tokens;
    retain relevant tests when test discovery is part of the question.
    """
    root = Path(repo_path).expanduser().resolve()
    target_file = Path(file_path).expanduser()
    if not target_file.is_absolute():
        target_file = root / target_file
    target_file = target_file.resolve()
    if not target_file.is_file():
        return f"Error: Target file '{target_file}' does not exist."
    _publish_mcp_live_status(root, f"MCP: analyzing file {target_file.name}")
    return json.dumps(
        _start_analysis_job(
            "single_file", root, target_file, exclude_paths=exclude_paths
        ),
        indent=2,
    )


@mcp.tool()
def get_analysis_status(
    repo_path: str,
    job_id: str | None = None,
    max_skipped_files: int | None = 10,
) -> str:
    """Return durable status for a non-blocking MCP analysis job.

    Omit ``job_id`` to inspect the repository's most recently updated job.
    Terminal states are ``completed``, ``failed`` and ``interrupted``. A job
    left running by a previous MCP server process is marked ``interrupted``
    rather than remaining permanently ambiguous.

    A completed global project job includes ``analysis_coverage`` when its
    indexer finished: ``skipped_python_files`` reports files that could not be
    statically analyzed, their parser/read reason, structured ``line_number``
    and ``column_number`` when parser coordinates exist, and
    ``syntax_error_count``.
    ``max_skipped_files`` bounds returned entries (default 10); pass ``None``
    for every skipped file. ``total`` and ``truncated`` make the coverage gap
    explicit. Layer and single-file jobs do not claim global coverage.

    LLM use: poll this after an analyze tool returns. Do not start another
    analysis while status is ``queued`` or ``running``; repeated analyze calls
    already return the same active job ID. Before assuming a completed global
    graph covers the whole repository, inspect ``analysis_coverage``.
    """

    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return json.dumps(
            {"status": "missing_repository", "repo_path": str(root)}, indent=2
        )
    job = (
        _read_analysis_job(root, job_id)
        if job_id is not None
        else _latest_analysis_job(root)
    )
    if job is None:
        return json.dumps(
            {"status": "not_found", "job_id": job_id, "repo_path": str(root)},
            indent=2,
        )
    if job.get("status") in {"queued", "running"} and job.get("owner_pid") != os.getpid():
        job = {
            **job,
            "status": "interrupted",
            "completed_at": _utc_now(),
            "message": "The MCP server process that owned this job is no longer active.",
            "error": "owner_process_changed",
        }
        _write_analysis_job(root, job)
    return json.dumps(
        _public_job(job, max_skipped_files=max_skipped_files), indent=2
    )


@mcp.tool()
def get_live_events(
    repo_path: str,
    after_revision: int | None = None,
    limit: int | None = 20,
) -> str:
    """Return revisioned desktop/MCP LIVE events since a known revision.

    Events are retained in RAM by the shared LIVE owner (most recent 100).
    Each event identifies its ``origin`` (``desktop_watcher``,
    ``mcp_analysis`` or ``mcp``), operation, status and file path. Syntax
    failures additionally expose ``error``, ``line_number`` and
    ``column_number``. The response always includes the current ``revision``,
    ``total`` and ``truncated``; ``limit`` defaults to 20 and may be ``None``
    for all retained events.

    LLM workflow after every file edit:
    - If the desktop app is running, do *not* call ``update_file``. Its watcher
      owns the update. Poll this tool with the last observed revision until the
      desktop event arrives, then react to its status before further edits.
    - If the desktop app is not running, call ``update_file`` after every edit,
      then call this tool to confirm the revision and diagnostics.

    MCP cannot push unsolicited messages into an idle model; this bounded,
    revisioned feed is the reliable pull mechanism for continuous LIVE state.
    """
    root = Path(repo_path).expanduser().resolve()
    if after_revision is not None and (
        isinstance(after_revision, bool) or after_revision < 0
    ):
        return json.dumps({"status": "error", "error": "invalid_after_revision"}, indent=2)
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
    ):
        return json.dumps({"status": "error", "error": "invalid_limit"}, indent=2)
    from contextor.core.live_state import connect

    client = connect(root)
    if client is None:
        return json.dumps(
            {"status": "no_live_service", "repo_path": str(root), "events": [], "total": 0, "truncated": False},
            indent=2,
        )
    try:
        return json.dumps(client.get_events(after_revision=after_revision, limit=limit), indent=2)
    except (OSError, EOFError, RuntimeError) as exc:
        return json.dumps({"status": "error", "error": str(exc)}, indent=2)


@mcp.tool()
def update_file(
    repo_path: str,
    file_path: str,
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Incremental architectural update for a modified file.
    Updates the canonical state and graph structure in real-time. When the
    shared LIVE service is available, the update executes in its owner process
    so desktop and MCP observe the same revision; otherwise the hydrated local
    engine remains a fallback. Requires a completed project analysis.

    Semantic-diff collections always expose ``total`` and ``truncated``. The
    default compact response omits ``items``; set ``compact=False`` for bounded
    symbol/signature evidence. ``max_items`` is the per-collection limit;
    pass ``None`` to return all requested evidence without truncation.
    ``fields`` projects top-level response keys after compact shaping. Stable
    fields include ``status``, ``file_path``, graph/metrics state fields,
    ``live_state_persisted``, ``semantic_diff`` and
    ``runtime_restart_required``; ``delta`` and runtime warning fields are
    conditional. Invalid projections return the current allowlist.

    LLM use after every file edit: if the desktop app is running, its watcher
    owns the update. Do not call this tool; poll ``get_live_events`` from the
    last revision until the ``desktop_watcher`` event reports the result. If
    desktop is not running, call this tool after every edit, then poll
    ``get_live_events`` to confirm the shared revision and any syntax
    diagnostic. Read ``semantic_diff`` for added/removed symbols and signature
    changes, then use normal code diff for line-level meaning. ``bodies_changed``
    uses normalized AST fingerprints to flag body-only edits without sending
    body text; it does not explain their meaning. Consumption/global metrics
    may be deferred.
    Editing this MCP server file updates disk and canonical state, but not the
    code already loaded by the running MCP process; restart the server whenever
    ``runtime_restart_required`` is true, then verify the tool live.
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
        from contextor.core.live_state import connect

        live_client = connect(root)
        if live_client:
            remote = live_client.update_file(str(target_file), origin="mcp")
            if remote.get("status") != "ok":
                raise RuntimeError(remote.get("error", "Shared LIVE update failed."))
            res = remote["result"]
            _live_engine_revisions[str(root)] = int(remote["revision"]) - 1
            engine = _get_or_init_engine(root)
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

@mcp.tool()
def get_project_architecture(
    repo_path: str,
    max_items: int | None = 10,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] The highest-level architectural summary of the project.
    Returns global action items, debt summary, layer index, and hotspots.
    Collections always expose ``total`` and ``truncated``. The compact default
    omits ``items``; set ``compact=False`` for evidence. ``max_items`` applies
    independently to every collection; pass ``None`` for all items. ``fields``
    projects top-level keys after compact shaping. Allowed values are
    ``action_items``, ``debt_summary``, ``layer_index``,
    ``top_global_hotspots``, ``module_count``, and ``data_source``.

    LLM use: start compact with the default limit. Increase it only when a
    relevant collection is truncated, or pass ``None`` after explicitly
    deciding that the complete collection is worth the token cost.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    try:
        summary_path = _get_canonical_report(root, f"{repo_name}_summary.json")
        engine = _get_or_init_engine(root)
        if summary_path:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            data_source = "current_summary_report"
        elif engine:
            layer_info = engine.state.layer_information or {}
            summary = dict(layer_info.get("summary_data", {}) or {})
            summary.setdefault("layer_index", layer_info.get("layer_index", []))
            summary.setdefault("top_hotspots", layer_info.get("hotspots", []))
            summary.setdefault("debt_summary", layer_info.get("debt", {}))
            summary.setdefault("metrics", {"nodes": len(engine.state.modules)})
            data_source = "live_canonical_state"
        else:
            return f"Error: No LIVE state or summary report found for {repo_name}. Run analyze_project first."
        
        collections = {}
        for key, source_key in (
            ("action_items", "action_items"),
            ("layer_index", "layer_index"),
            ("top_global_hotspots", "top_hotspots"),
        ):
            items, total, truncated = _bounded_items(
                summary.get(source_key, []), max_items
            )
            collection = {"total": total, "truncated": truncated}
            if not compact:
                collection["items"] = items
            collections[key] = collection
        result = {
            **collections,
            "debt_summary": summary.get("debt_summary", {}),
            "module_count": summary.get("metrics", {}).get("nodes", 0),
            "data_source": data_source,
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


@mcp.tool()
def get_module_context(
    repo_path: str,
    module_name: str,
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Retrieve a compressed context pill for one module.

    Full-report metrics are combined with the canonical LIVE dependency graph.
    A file added through update_file is therefore immediately queryable, even
    before another global report refreshes expensive metrics. Deferred metrics
    are labelled explicitly instead of hiding the module.

    Dependency collections always expose ``total`` and ``truncated``. The
    default compact response omits edge ``items``; set ``compact=False`` for
    bounded evidence. ``max_items`` applies independently to inbound and
    outbound edges; pass ``None`` to return every edge. ``compact`` shapes the
    response before ``fields`` projects it. Allowed values are ``module``, ``metrics``,
    ``metrics_source``, ``dependency_data_source``,
    ``dependencies_inbound_who_calls_me``, and
    ``dependencies_outbound_who_i_call``. Invalid projections return a
    structured error with the current allowlist.

    LLM use: call immediately before editing a known module. Trust LIVE
    inbound/outbound edges for current structure; treat metrics marked
    deferred as unavailable until the next full analysis.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name

    ga = {}
    ga_path = _get_canonical_report(root, f"{repo_name}_graph_analytics.json")
    if ga_path:
        try:
            ga = json.loads(ga_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            ga = {}

    saved_modules = ga.get("modules", {})
    engine = _get_or_init_engine(root)
    live_modules = set()
    if engine:
        live_modules = set(getattr(engine.state, "modules", {})) | set(
            getattr(engine.state, "artifacts", {})
        )

    if module_name not in saved_modules and module_name not in live_modules:
        if not ga_path and not engine:
            return "Error: No graph state found. Run analyze_project first."
        return f"Module '{module_name}' not found in the project graph."

    inbound = {}
    outbound = {}
    dependency_source = "saved_graph_analytics"

    if module_name in live_modules:
        graph = getattr(engine.state, "dependency_graph", None)
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
        dependency_source = "live_canonical_graph"
    else:
        matrix = ga.get("module_dependency_matrix", {})
        from contextor.core.reporting_engine.persistent_registry import (
            PersistentIdentityRegistry,
        )

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

    metrics = saved_modules.get(module_name)
    metrics_source = "saved_graph_analytics"
    if metrics is None:
        metrics_source = "deferred_until_full_analysis"
        metrics = {
            "module_idx": engine.registry.get_module_id(module_name),
            "fan_in": len(inbound),
            "fan_out": len(outbound),
            "visibility": "unknown",
            "metrics_state": "deferred",
        }

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

@mcp.tool()
def get_artifact_blast_radius(
    repo_path: str,
    artifact_name: str,
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Resolves direct, evidence-backed consumers of an artifact.
    Uses canonical LIVE symbol consumption first and falls back to the current
    compact artifact report. It does not claim that dynamic Python usage can
    be proven exact.

    ``consumers`` always contains ``total`` and ``truncated``. The default
    compact response omits ``items``; set ``compact=False`` for bounded static
    evidence. ``max_items`` controls returned consumers; pass ``None`` for all
    consumers without truncation. ``fields`` projects top-level
    keys after compact shaping. Allowed values are ``artifact``, ``artifact_id``,
    ``kind``, ``definer``, ``consumers``, ``evidence_scope``, and ``data_source``.

    LLM use: call before changing or removing a public symbol. Treat consumers
    as confirmed static evidence, not proof that dynamic Python has no callers.
    """
    root = Path(repo_path).expanduser().resolve()
    repo_name = root.name
    
    try:
        _, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)
        engine = _get_or_init_engine(root)
        if engine:
            live_matches = []
            for module_name, artifact_state in engine.state.artifacts.items():
                for local_name in artifact_state.get("own_symbols", []) or []:
                    full_name = f"{module_name}::{local_name}"
                    if full_name != artifact_name and local_name != artifact_name:
                        continue
                    symbols = artifact_state.get("symbols", {}) or {}
                    kinds = [
                        kind
                        for category, kind in (
                            ("classes", "class"),
                            ("functions", "function"),
                            ("methods", "method"),
                            ("globals", "global"),
                        )
                        if local_name in (symbols.get(category, []) or [])
                    ]
                    consumer_state = (artifact_state.get("consumers", {}) or {}).get(
                        local_name, {}
                    )
                    live_matches.append(
                        {
                            "artifact": full_name,
                            "artifact_id": art_path_to_id.get(full_name),
                            "kind": kinds[0] if len(kinds) == 1 else "ambiguous",
                            "definer": module_name,
                            "consumer_items": sorted(
                                consumer_state.get("consumers", []) or []
                            ),
                        }
                    )
            if live_matches:
                selected = sorted(live_matches, key=lambda item: item["artifact"])[0]
                consumer_items, consumer_total, consumer_truncated = _bounded_items(
                    selected.pop("consumer_items"), max_items
                )
                result = {
                    **selected,
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

        resolved_consumers = [mod_id_to_path.get(item, item) for item in consumer_ids]
        consumer_items, consumer_total, consumer_truncated = _bounded_items(
            resolved_consumers, max_items
        )
        common_result = {
            "artifact": full_name,
            "artifact_id": art_id,
            "kind": art_data.get("kind"),
            "definer": mod_id_to_path.get(definer_id, definer_id),
            "evidence_scope": "direct_static_artifact_consumption",
            "data_source": "current_artifacts_compact",
        }
        full_result = {
            **common_result,
            "consumers": {
                "items": consumer_items,
                "total": consumer_total,
                "truncated": consumer_truncated,
            },
        }
        compact_result = {
            **common_result,
            "consumers": {
                "total": consumer_total,
                "truncated": consumer_truncated,
            },
        }
        result = compact_result if compact else full_result
        if fields is not None:
            allowed_fields = set(result)
            unknown_fields = sorted(set(fields) - allowed_fields)
            if unknown_fields:
                return json.dumps(
                    {
                        "error": "Unsupported fields for get_artifact_blast_radius",
                        "unknown_fields": unknown_fields,
                        "allowed_fields": sorted(allowed_fields),
                    },
                    indent=2,
                )
            result = {field: result[field] for field in fields}
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error calculating artifact blast radius: {e}"


@mcp.tool()
def search_artifacts(
    repo_path: str,
    search_term: str,
    limit: int | None = 20,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Searches the canonical live state for an artifact, module, or symbol matching 'search_term'.
    Returns its properties and all its dependencies and consumers (blast radius).
    Use this to extract arbitrary context about any symbol from the current architectural state.
    Exact symbol matches are preferred. ``limit``, ``total_matches`` and
    ``truncated`` bound broad searches without hiding their cardinality.
    Nested module dependencies and artifact consumers are independently bounded
    by ``evidence_limit``. They always expose ``total`` and ``truncated``;
    set ``compact=False`` to include ``items``. Pass ``None`` for either limit
    to return every match or every nested evidence item. ``fields``
    projects ``query``, ``match_count``, ``total_matches``, ``truncated``,
    ``modules`` or ``artifacts`` after compact shaping.

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


@mcp.tool()
def get_symbol_implementation(
    repo_path: str,
    symbol: str,
    file_paths: list[str],
    mode: str = "preview",
    include: list[str] | None = None,
    methods: list[str] | None = None,
    member_limit: int | None = 50,
) -> str:
    """
    [OPTIMIZED] Resolves one class, function, or method from explicit source
    files and returns its exact AST-bounded implementation on demand.

    This is a two-phase, LLM-first tool. ``mode='preview'`` is the default and
    returns no source code: it resolves the symbol, reports its exact line
    range, and estimates UTF-8 JSON response sizes in bytes and decimal KB for
    complete fetch plans. For classes it also lists selectable methods with
    their individual complete-source costs. ``member_limit`` bounds that method
    catalogue only; pass ``None`` to see every method. ``total`` and
    ``truncated`` make omitted methods explicit.

    Use ``mode='fetch'`` only after preview. ``include`` is required and may
    contain ``signature``, ``docstring``, ``implementation``,
    ``static_context``, or (for a class) ``methods``. ``implementation``
    returns the entire resolved AST symbol, including decorators and its
    docstring when present; it is never split into line chunks. To fetch class
    methods instead of the whole class, choose ``include=['methods']`` and pass
    their names in ``methods``. Each selected method is returned whole, never
    partially. ``implementation`` and ``methods`` are mutually exclusive so a
    caller cannot accidentally duplicate a whole class and its methods.

    Symbol matching is exact and Python case-sensitive. Supply one or more
    repository-relative or absolute ``file_paths``; ambiguous matches return
    candidate metadata only, and no implementation is guessed. Source is read
    from disk at request time and is not stored in canonical state. The compact
    ``static_context`` contains the current static consumer total when live
    state is available; use the blast-radius tool for consumer evidence.

    LLM use: preview first, compare the planned payload sizes, then fetch the
    smallest complete combination that answers the implementation question.
    This complements source-file reading; it does not infer historical intent.
    """
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return json.dumps({"status": "error", "error": f"Repository path '{root}' does not exist."}, indent=2)
    _publish_mcp_live_status(root, f"MCP: reading symbol {symbol}")
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


@mcp.tool()
def get_file_edit_context(
    repo_path: str,
    file_path: str,
    max_items: int | None = 30,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Specialized single-shot context pill for LLMs prior to editing a file.
    Combines LIVE module/API/dependency state in one response. Saved reports
    enrich risk and layer metrics when available but are never required when
    canonical LIVE state exists.
    By default returns a compact decision summary: identity, risk, data sources,
    and collection metadata. Set ``compact=False`` to include bounded ``items``
    (or ``tests`` for ``tests_covering``) in the same nested collection objects.

    ``fields`` is a projection that returns only explicitly requested fields.
    Allowed values are: ``file``, ``file_exists``, ``module``, ``module_id``,
    ``layer``, ``entrypoint``, ``risk_score``, ``public_api``, ``imports``,
    ``consumers``, ``tests_covering``, ``dependency_data_source``, and
    ``artifact_data_source``. Collection fields are nested objects that always
    contain ``total`` and ``truncated``; full mode additionally includes
    ``items`` (or ``tests``). ``compact`` shapes the response first; ``fields``
    then selects top-level keys without changing their schema.

    ``tests_covering`` reports bounded static dependency paths from test
    modules, including paths through aliases, re-exports and facades. It is
    structural evidence, not runtime line or branch coverage.

    Collections use ``max_items`` (default 30) to protect the LLM context
    window. Increase it when omitted evidence matters, or pass ``None`` to
    return every item without truncation.

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
    engine = _get_or_init_engine(root)

    if not (ga_path and art_path) and not engine:
        return "Error: No canonical LIVE state or required reports. Run analyze_project first."
        
    try:
        ga = json.loads(ga_path.read_text(encoding="utf-8")) if ga_path else {}
        art_comp = json.loads(art_path.read_text(encoding="utf-8")) if art_path else {}
        
        mod_info = ga.get("modules", {}).get(module_name, {})
        if not mod_info and engine:
            state_metrics = getattr(engine.state, "metrics", {}) or {}
            candidate_metrics = state_metrics.get(module_name, {}) if isinstance(state_metrics, dict) else {}
            mod_info = candidate_metrics if isinstance(candidate_metrics, dict) else {}
        
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
        if risk_score == 0.0 and engine:
            for hotspot in (getattr(engine.state, "layer_information", {}) or {}).get("hotspots", []) or []:
                if hotspot.get("module") == module_name:
                    risk_score = hotspot.get("score", 0.0)
                    break
        
        # We must read registries OUTSIDE the transaction block to avoid Resource Deadlock
        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = _read_registries(root)
        live_module = engine.state.modules.get(module_name) if engine else None
        mod_id = mod_path_to_id.get(module_name) or getattr(live_module, "module_id", None)
        if not mod_id:
            if live_module is None:
                if ga_path or art_path:
                    return f"Error: Module '{module_name}' is not present in the current registry."
                return f"Error: Module '{module_name}' is not present in canonical LIVE state."
            mod_id = module_name
            
        imports = []
        consumers = []
        dependency_data_source = "saved_graph_analytics"
        artifact_data_source = "saved_artifacts_compact"
        matrix = ga.get("module_dependency_matrix", {})
        live_graph = engine.state.dependency_graph if engine else None
        reachability_hard = {}
        reachability_soft = {}
        if engine and module_name in engine.state.modules and live_graph:
            reachability_hard = live_graph.hard_edges
            reachability_soft = live_graph.soft_edges
            target_modules = set(live_graph.hard_edges.get(module_name, set()))
            target_modules.update(live_graph.soft_edges.get(module_name, set()))
            imports = [mod_path_to_id.get(target, target) for target in sorted(target_modules)]
            consumer_modules = {
                source
                for edge_map in (live_graph.hard_edges, live_graph.soft_edges)
                for source, targets in edge_map.items()
                if module_name in targets
            }
            consumers = [mod_path_to_id.get(source, source) for source in sorted(consumer_modules)]
            dependency_data_source = "live_canonical_graph"
        else:
            if mod_id in matrix:
                imports.extend(matrix[mod_id].keys())
            for src_id, targets in matrix.items():
                if mod_id in targets:
                    consumers.append(src_id)
            reachability_hard = {
                mod_id_to_path.get(src_id, src_id): {
                    mod_id_to_path.get(target_id, target_id)
                    for target_id in targets
                }
                for src_id, targets in matrix.items()
            }
                        
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
            live_symbols = engine.state.artifacts[module_name].get("own_symbols", []) or []
            for local_name in sorted(live_symbols):
                leaf = str(local_name).rsplit(".", 1)[-1]
                if leaf.startswith("_") and not (
                    leaf.startswith("__") and leaf.endswith("__")
                ):
                    continue
                full_name = prefix + str(local_name)
                artifact_key = str(art_path_to_id.get(full_name, full_name))
                public_api.setdefault(artifact_key, full_name)
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
            or ga.get("modules", {}).get(name, {}).get("layer") == "tests"
        }
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


@mcp.tool()
def get_layer_isolation(
    repo_path: str,
    layer_name: str,
    max_clusters: int | None = 8,
    max_boundary_violations: int | None = 10,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Extracts isolation metrics, clusters, and leaks for a specific architectural layer.
    Use this before refactoring a large component to understand its internal cohesion.

    Uses a dedicated layer report when present and otherwise derives bounded
    boundary evidence from canonical LIVE state. Reports enrich clusters and
    metrics but are not required for structural isolation.

    ``max_clusters`` and ``max_boundary_violations`` bound verbose evidence.
    Collections always expose ``total`` and ``truncated``. The compact default
    omits ``items``; set ``compact=False`` for evidence. Increase either limit
    or pass ``None`` for the complete corresponding collection. ``fields``
    projects top-level keys after compact shaping. Allowed values are ``layer``,
    ``report_layer``, ``data_source``, ``module_count``, ``clusters``,
    ``dependency_types``, and ``boundary_violations``.

    LLM use: call before moving modules or changing layer boundaries. Resolve a
    truncated tail only when the planned edit touches that omitted evidence.
    """
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
        engine = _get_or_init_engine(root)
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


@mcp.tool()
def get_report_diff(
    repo_path: str,
    max_items: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Returns architectural regression analysis between the last two analysis runs.
    Shows delta in hotspot count, debt score, cycle count, and lists new/resolved hotspots.
    Consecutive runs are compared before the canonical summary is overwritten,
    including different working-tree states on the same commit.
    Layer changes are returned as a collection with ``total`` and ``truncated``;
    set ``compact=False`` for bounded ``items``. ``max_items=None`` returns all
    changed layers. ``fields`` projects top-level keys after compact shaping;
    current reports expose ``classification``, ``report_diff``, ``baseline``,
    ``current``, and ``comparison_basis``.

    LLM use: run analysis once before and once after a change, then inspect the
    classification and metric deltas here. An empty diff means no tracked
    architectural metric changed; it does not mean source text was identical.
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


def _execute_canonical_query(engine: object, python_filter_expression: str) -> str:
    """Execute a restricted Python expression against a live canonical engine state.

    Provides a safe sandbox with whitelisted builtins only — no import, exec or
    open. The engine's ``modules``, ``artifacts``, ``dependency_graph`` and
    ``registry`` objects are injected as top-level variables.

    Returns a JSON-serialised string on success, or an ``"Error: ..."`` string
    on failure so callers can propagate the message directly to the LLM.
    """
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
def query_canonical_state(repo_path: str, python_filter_expression: str) -> str:
    """
    [DEPRECATED] Executes a restricted Python expression against LIVE state.
    Kept temporarily for migration compatibility. It receives no new features;
    prefer ``describe_canonical_state`` followed by
    ``query_canonical_projection`` for versioned, normalized, bounded queries.
    The live objects are loaded into variables: 'modules', 'artifacts', 'dependency_graph', 'registry'.
    Example expression: "[m_path for m_path, mod in modules.items() if len(mod.imports) > 20]"

    LLM use: prefer ``query_canonical_state_bounded`` for exploration; use this
    tool only when you need unbounded results or when the expression already
    projects to a small scalar value.
    """
    root = Path(repo_path).expanduser().resolve()
    engine = _get_or_init_engine(root)
    
    if not engine:
        return f"Error: No live canonical state found for {root}. Run analyze_project first."
        
    return _execute_canonical_query(engine, python_filter_expression)


@mcp.tool()
def query_canonical_state_bounded(
    repo_path: str,
    python_filter_expression: str,
    limit: int | None = 100,
) -> str:
    """
    [DEPRECATED] Runs the same restricted expression as
    ``query_canonical_state`` but bounds top-level list/dict results.

    Kept temporarily for migration compatibility. Prefer
    ``describe_canonical_state`` and ``query_canonical_projection``; the new
    path does not expose Python objects or evaluate expressions.

    Prefer this tool for exploration. The response includes ``total_items``
    and ``truncated`` so an LLM can refine the expression or raise ``limit``
    only when omitted items matter. Select narrow scalar fields in the
    expression when individual nested values may themselves be large.
    Pass ``limit=None`` only after explicitly choosing an unbounded top-level
    result. A legacy response with a nested value larger than 12 KiB is
    replaced by a structured ``payload_too_large`` preview; it reports the
    original size and directs the caller to a scalar expression or the
    projection API. This transport safety fallback is independent of the
    top-level ``limit``.

    LLM use: use this as an escape hatch for questions not covered by a
    dedicated tool. Prefer projected scalar fields and a small limit; it is a
    structural query, not a substitute for reading the affected source.
    """
    root = Path(repo_path).expanduser().resolve()
    engine = _get_or_init_engine(root)

    if not engine:
        return f"Error: No live canonical state found for {root}. Run analyze_project first."

    raw = _execute_canonical_query(engine, python_filter_expression)
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw
    return json.dumps(_bounded_query_result(value, limit), indent=2)


@mcp.tool()
def describe_canonical_state() -> str:
    """Return the complete versioned contract for safe canonical LIVE queries.

    This endpoint is passive discovery only: it returns ``SCHEMA_V1`` and
    ``LANGUAGE_V1`` from the same constants used by query validation. It does
    not read repository data, execute expressions, reflect over Python objects,
    or fetch records. The response documents the three roots (``modules``,
    ``artifacts``, ``dependencies``), every selectable field, per-field
    operators, null semantics, canonical ordering and hard request limits.

    LLM use: call this before composing a projection request or when a
    structural validation error reports an unfamiliar field/operator. Cache by
    ``schema_version`` and ``language_version``; do not treat it as repository
    data or use it in place of ``query_canonical_projection``.
    """
    return json.dumps(_describe_canonical_contract(), indent=2, ensure_ascii=False)


@mcp.tool()
def query_canonical_projection(repo_path: str, request: dict[str, Any]) -> str:
    """Execute a safe, bounded JSON query over normalized canonical LIVE data.

    ``request`` must explicitly include ``schema_version``,
    ``language_version``, ``root``, ``filters`` and ``select``. It may include
    ``limit`` (default 20, maximum 200). Filters are a flat AND and use only the
    operators declared for each field by ``describe_canonical_state``. Empty
    ``filters`` matches all records; empty ``select`` returns every selectable
    field. Results always report ``total_matches``, ``returned``, ``limit`` and
    ``truncated``.

    The executor first converts LIVE state to read-only JSON-safe records. It
    never uses ``eval``, accepts no Python expressions, exposes no arbitrary
    attributes and omits local absolute paths. Artifacts preserve the
    distinction between confirmed zero consumers and unavailable consumption
    data via ``consumer_data_available`` plus nullable consumer fields.
    Structural errors return one deterministic error with ``code``, ``path``
    and repair details.

    LLM use: discover the contract first, request the smallest useful field
    selection, and narrow filters when ``truncated`` is true. Use legacy
    ``query_canonical_state*`` only for temporary migration gaps.
    """
    root = Path(repo_path).expanduser().resolve()
    engine = _get_or_init_engine(root)
    if not engine:
        return json.dumps(
            {
                "status": "error",
                "error": {
                    "code": "canonical_state_unavailable",
                    "message": "No live canonical state is available. Run analyze_project first.",
                    "path": "repo_path",
                    "details": {"repo_path": str(root)},
                },
            },
            indent=2,
        )
    return json.dumps(
        _execute_canonical_projection(engine.state, request),
        indent=2,
        ensure_ascii=False,
    )


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
    max_items: int | None = 20,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Extracts complete matching blocks from an indexed artifact report.

    Resolution is index-first and shared with the GUI parser. Queries may use an
    artifact/module ID, a ``.py`` path, a full ``module::symbol`` key, or explicit
    ``file:``, ``module:``, ``symbol:`` and ``artifact:`` prefixes. Exact matches
    are never replaced by fuzzy guesses; ambiguous and missing queries remain
    explicit. Active dictionaries fall back to both recovery dictionaries, while
    blocks with unresolved artifact or definer IDs are omitted with diagnostics.

    Omit ``report_path`` to read the current compact artifact report. Every
    selected block is returned complete, including nested objects. ``max_items``
    controls the number of complete artifact blocks (default 20); pass ``None``
    for every match. ``total_artifact_count`` and ``truncated`` expose omitted
    matches. ``fields`` projects top-level keys after bounding; accepted names
    are the keys returned by the shared indexed-query resolver plus
    ``total_artifact_count``, ``truncated``, and ``data_source``. Invalid
    projections return the exact current allowlist.

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
    Output size is controlled directly by the number of IDs supplied; split a
    large set when one response would not fit the context window.
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
    limit: int | None = 50,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
) -> str:
    """
    [OPTIMIZED] Returns all artifacts exported by a module with consumer info.

    Equivalent to the GUI parser window — shows what a module defines and
    who uses each artifact across the project.

    ``module_name`` can be:
    - A full dotted module name: 'contextor.ui.gui_parser'
    - A file path relative to the repo root: 'contextor/ui/gui_parser.py'

    Set ``include_consumers=False`` for a signatures-only view. When included,
    each ``consumers`` object always exposes ``total`` and ``truncated``;
    ``compact=False`` adds ``items``. ``limit`` controls artifact matches and
    ``evidence_limit`` controls consumers per artifact; pass ``None`` for all
    matches or all nested evidence. ``fields`` projects top-level keys after
    compact shaping. Allowed values are ``module``, ``module_id``,
    ``artifact_count``, ``total_artifact_count``, ``truncated``,
    ``symbol_filter``, ``data_sources``, ``complete_symbol_catalog``, and
    ``artifacts``.

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
            }

            if include_consumers:
                consumer_ids = art_data.get("consumer_module_indices", [])
                resolved_consumers = [
                    mod_id_to_path.get(c, c) for c in consumer_ids
                ]
                consumer_items, consumer_total, consumer_truncated = _bounded_items(
                    resolved_consumers, evidence_limit
                )
                entry["consumers"] = {
                    "total": consumer_total,
                    "truncated": consumer_truncated,
                }
                if not compact:
                    entry["consumers"]["items"] = consumer_items

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
                }
                if include_consumers:
                    entry["consumers"] = existing.get(
                        "consumers", {"total": 0, "truncated": False}
                    )
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
                "data_sources": ["live_symbol_state", "artifacts_compact"],
                "complete_symbol_catalog": bool(engine),
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


@mcp.tool()
def lookup_artifact_by_symbol(
    repo_path: str,
    symbol_name: str,
    limit: int | None = 20,
    evidence_limit: int | None = 20,
    compact: bool = True,
    fields: list[str] | None = None,
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
    Consumers within every match are bounded independently by
    ``evidence_limit``, always expose ``total`` and ``truncated``, and include
    ``items`` only when ``compact=False``. Pass ``None`` for all matches or all
    consumers. ``fields`` projects top-level keys after compact shaping.
    Allowed values are ``query``, ``match_count``, ``total_matches``,
    ``truncated``, ``data_source``, and ``artifacts``.

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
        candidates, total_matches, matches_truncated = _bounded_items(
            candidates, limit
        )

        if not candidates:
            return f"No current artifacts found matching '{symbol_name}'."

        results: dict = {}
        for _, _, art_id, full_name in candidates:
            art_data = artifacts_raw[art_id]
            definer_id = str(art_data.get("definer_module", ""))
            consumer_ids = art_data.get("consumer_module_indices", [])

            resolved_consumers = [mod_id_to_path.get(c, c) for c in consumer_ids]
            consumer_items, consumer_total, consumer_truncated = _bounded_items(
                resolved_consumers, evidence_limit
            )
            entry = {
                "symbol": full_name.split("::", 1)[-1] if "::" in full_name else full_name,
                "full_name": full_name,
                "kind": art_data.get("kind", "unknown"),
                "definer_module": mod_id_to_path.get(definer_id, definer_id),
                "consumers": {
                    "total": consumer_total,
                    "truncated": consumer_truncated,
                },
            }
            if not compact:
                entry["consumers"]["items"] = consumer_items
            results[art_id] = entry

        result = {
                "query": symbol_name,
                "match_count": len(results),
                "total_matches": total_matches,
                "truncated": matches_truncated,
                "data_source": "current_artifacts_compact",
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
