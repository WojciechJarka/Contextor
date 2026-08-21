import hashlib
import json
from pathlib import Path

from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime


_MCP_SERVER_SOURCE_PATH = Path(__file__).resolve().parents[2] / "mcp_server.py"
_MCP_SERVER_SOURCE_FINGERPRINT = hashlib.sha256(
    _MCP_SERVER_SOURCE_PATH.read_bytes()
).hexdigest()


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
            target_file == _MCP_SERVER_SOURCE_PATH
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
                "artifacts_removed": res.delta.artifacts_removed,
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
