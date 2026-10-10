import hashlib
import json
import copy
from pathlib import Path

from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime


_MCP_PACKAGE_SOURCE_ROOT = Path(__file__).resolve().parents[1]
_CONTEXTOR_PACKAGE_ROOT = _MCP_PACKAGE_SOURCE_ROOT.parent

_TOP_LEVEL_MCP_SOURCES: tuple[Path, ...] = (
    _CONTEXTOR_PACKAGE_ROOT / "mcp_server.py",
    _CONTEXTOR_PACKAGE_ROOT / "mcp_main.py",
    _CONTEXTOR_PACKAGE_ROOT / "mcp_process_registry.py",
)


def _mcp_runtime_source_paths() -> tuple[Path, ...]:
    """Return all Python source paths that define this running MCP server."""
    sources: set[Path] = set(_TOP_LEVEL_MCP_SOURCES)
    if _MCP_PACKAGE_SOURCE_ROOT.is_dir():
        sources.update(_MCP_PACKAGE_SOURCE_ROOT.rglob("*.py"))
    return tuple(sorted(p.resolve() for p in sources if p.is_file()))


def _source_fingerprint(path: Path) -> str | None:
    """Compute sha256 fingerprint of a source file if accessible."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


_MCP_RUNTIME_SOURCE_FINGERPRINTS: dict[Path, str | None] = {
    path: _source_fingerprint(path)
    for path in _mcp_runtime_source_paths()
}


def _is_mcp_runtime_source_path(path: Path) -> bool:
    """Determine whether a path is within the running MCP process source domain."""
    resolved = path.resolve()
    if resolved in {p.resolve() for p in _TOP_LEVEL_MCP_SOURCES}:
        return True
    if resolved.suffix == ".py":
        try:
            resolved.relative_to(_MCP_PACKAGE_SOURCE_ROOT)
            return True
        except ValueError:
            return False
    return False


def _mcp_runtime_restart_required(target_file: Path) -> bool:
    """Check if target_file is an MCP runtime source whose content/presence changed since MCP startup."""
    resolved = target_file.resolve()
    if not _is_mcp_runtime_source_path(resolved):
        return False
    if resolved in _MCP_RUNTIME_SOURCE_FINGERPRINTS:
        baseline = _MCP_RUNTIME_SOURCE_FINGERPRINTS[resolved]
        if baseline is None:
            return True
        if not resolved.is_file():
            return True
        current = _source_fingerprint(resolved)
        if current is None:
            return True
        return current != baseline
    return resolved.is_file()


def _persist_live_engine(root: Path, engine) -> bool:
    """Persist local state and FileState in one exact snapshot generation."""
    from contextor.core.analysis.state_manager import save_engine_state
    from contextor.core.live_state import read_metadata
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    identity = require_repository_identity(root)
    cache_dir = repo_cache_dir(root)
    cache_dir.mkdir(parents=True, exist_ok=True)

    manager = getattr(engine, "state_manager", None)
    if manager is None or not callable(getattr(manager, "build_payload", None)):
        raise RuntimeError(
            "Local persistence requires a FileStateManager with build_payload."
        )

    with mcp_runtime._engine_cache_transaction(root) as root_key:
        current = read_metadata(cache_dir)
        metadata_path = cache_dir / "engine_state.meta.json"

        if current is None and metadata_path.exists():
            raise RuntimeError(
                "Existing canonical snapshot metadata is invalid; "
                "local persistence cannot bootstrap over it."
            )

        expected_previous_revision = (
            int(current.revision) if current is not None else None
        )

        for revision_name, value in (
            ("engine", getattr(engine, "revision", None)),
            ("state", getattr(engine.state, "revision", None)),
            ("cache", mcp_runtime._live_engine_revisions.get(root_key)),
        ):
            if value is None:
                continue
            if isinstance(value, bool) or type(value) is not int:
                raise RuntimeError(
                    f"Local {revision_name} revision is invalid."
                )
            if expected_previous_revision is None:
                if value != 0:
                    raise RuntimeError(
                        f"Local {revision_name} revision has no committed baseline."
                    )
            elif value != expected_previous_revision:
                raise RuntimeError(
                    f"Local {revision_name} revision differs from "
                    "committed snapshot revision."
                )

        state_id = str(
            (current.state_id if current is not None else "")
            or getattr(engine.state, "state_id", "")
            or getattr(manager, "state_id", "")
            or identity.repo_id
        )

        if current is not None and current.state_id:
            for existing_id in (
                getattr(engine.state, "state_id", None),
                getattr(manager, "state_id", None),
            ):
                if existing_id and str(existing_id) != current.state_id:
                    raise RuntimeError(
                        "Local state identity differs from committed snapshot."
                    )

        next_revision = (
            expected_previous_revision + 1
            if expected_previous_revision is not None
            else 1
        )

        candidate = engine.state.clone_for_update()
        payload = manager.build_payload(state_id, next_revision)

        meta = save_engine_state(
            candidate,
            str(cache_dir),
            state_id,
            writer="mcp",
            repo_id=identity.repo_id,
            root_path=identity.root_path,
            exact_revision=next_revision,
            file_state_payload=payload,
        )

        if meta is None:
            return False

        if meta.revision != next_revision or meta.state_id != state_id:
            raise RuntimeError(
                "Exact local snapshot returned mismatching commit identity."
            )

        engine.revision = next_revision
        engine.state.revision = next_revision
        engine.state.state_id = state_id
        manager.state_id = state_id
        manager.revision = next_revision
        mcp_runtime._live_engine_revisions[root_key] = next_revision

        return True


class _LocalCandidatePersistenceRejected(RuntimeError):
    """The local candidate was discarded because its snapshot was not committed."""


def _assert_local_committed_baseline(root: Path, engine, root_key: str) -> None:
    """Reject stale local RAM before registry or candidate mutation."""
    from contextor.core.live_state import read_metadata
    from contextor.core.paths import repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    identity = require_repository_identity(root)
    cache_dir = repo_cache_dir(root)
    metadata_path = cache_dir / "engine_state.meta.json"
    current = read_metadata(cache_dir)

    if current is None and metadata_path.exists():
        raise RuntimeError(
            "Local writer denied: committed snapshot metadata is invalid."
        )

    if current is not None:
        if current.repo_id and current.repo_id != identity.repo_id:
            raise RuntimeError(
                "Local writer denied: snapshot repository identity mismatch."
            )
        if (
            current.root_path
            and Path(current.root_path).expanduser().resolve()
            != Path(identity.root_path).expanduser().resolve()
        ):
            raise RuntimeError(
                "Local writer denied: snapshot repository root mismatch."
            )

    expected = int(current.revision) if current is not None else None

    for owner, value in (
        ("engine", getattr(engine, "revision", None)),
        ("state", getattr(engine.state, "revision", None)),
        ("cache", mcp_runtime._live_engine_revisions.get(root_key)),
    ):
        if value is None:
            continue
        if type(value) is not int:
            raise RuntimeError(
                f"Local writer denied: invalid {owner} revision."
            )
        if expected is None:
            if value != 0:
                raise RuntimeError(
                    f"Local writer denied: {owner} has no committed baseline."
                )
        elif value != expected:
            raise RuntimeError(
                f"Local writer denied: stale {owner} revision."
            )

    if current is not None and current.state_id:
        manager = getattr(engine, "state_manager", None)
        for owner, value in (
            ("state", getattr(engine.state, "state_id", None)),
            ("FileStateManager", getattr(manager, "state_id", None)),
        ):
            if value and str(value) != current.state_id:
                raise RuntimeError(
                    f"Local writer denied: {owner} identity mismatch."
                )


def _execute_local_candidate_update(
    root: Path, target_file: Path, engine
):
    """Coordinate local updates with repository canonical writers."""
    from contextor.core.analysis.full_analysis_coordinator import (
        acquire_full_analysis,
        release_full_analysis,
    )

    lease = acquire_full_analysis(
        root,
        owner="mcp_local_incremental",
        writer_kind="local_incremental",
        timeout=10.0,
    )
    try:
        return _execute_local_candidate_update_with_domain_fence(
            root,
            target_file,
            engine,
        )
    finally:
        release_full_analysis(lease)


def _execute_local_candidate_update_with_domain_fence(
    root: Path, target_file: Path, engine
):
    """Fence LIVE authority before executing a local candidate transaction."""
    from contextor.core.live_state.runtime import _production_domain
    from contextor.core.live_state.runtime_lease import RuntimeLeaseManager
    from contextor.core.repository_identity import require_repository_identity

    with mcp_runtime._engine_cache_transaction(root) as root_key:
        if mcp_runtime._live_engines.get(root_key) is not engine:
            raise RuntimeError(
                "Local cached engine ownership changed."
            )

        identity = require_repository_identity(root)
        domain = _production_domain(identity)
        lease_manager = RuntimeLeaseManager(domain)

        with lease_manager._lock():
            generation = lease_manager._read_generation()
            live_lease = lease_manager._read_live_lease()

            if (
                live_lease is not None
                or generation.status not in {"never_acquired", "released"}
            ):
                raise RuntimeError(
                    "Local writer denied: LIVE authority is present "
                    "or its ownership is unresolved."
                )

            _assert_local_committed_baseline(
                root,
                engine,
                root_key,
            )

            return _execute_local_candidate_update_unfenced(
                root,
                target_file,
                engine,
            )


def _execute_local_candidate_update_unfenced(
    root: Path, target_file: Path, engine
):
    """Commit a local update candidate before replacing the cached engine."""
    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
    from contextor.core.live_state import read_metadata
    from contextor.core.paths import repo_cache_dir

    with mcp_runtime._engine_cache_transaction(root) as root_key:
        if mcp_runtime._live_engines.get(root_key) is not engine:
            raise RuntimeError("Local cached engine ownership changed.")

        rel_path = target_file.relative_to(root)
        module_path = ".".join(rel_path.with_suffix("").parts)
        old_artifacts = engine.state.artifacts.get(module_path, {})

        state = getattr(engine, "state", None)
        if not callable(getattr(state, "clone_for_update", None)):
            raise RuntimeError("Local canonical state cannot be cloned for update.")
        manager = getattr(engine, "state_manager", None)
        if manager is None or not isinstance(getattr(manager, "_state", None), dict):
            raise RuntimeError("Local FileStateManager has no tracked-file mapping.")
        registry = getattr(engine, "registry", None)
        if (
            registry is None
            or not callable(getattr(registry, "create_checkpoint", None))
            or not callable(getattr(registry, "restore_checkpoint", None))
        ):
            raise RuntimeError("Local identity registry has no checkpoint capability.")

        cache_dir = repo_cache_dir(root)
        metadata_path = cache_dir / "engine_state.meta.json"
        previous_metadata = read_metadata(cache_dir)
        previous_metadata_exists = metadata_path.exists()

        candidate_state = state.clone_for_update()
        if candidate_state is state:
            raise RuntimeError("Local update candidate shares the canonical state holder.")
        candidate_manager = copy.copy(manager)
        candidate_manager._state = dict(manager._state)
        checkpoint = registry.create_checkpoint()

        try:
            candidate_engine = IncrementalAnalysisEngine(
                candidate_state,
                registry,
                candidate_manager,
                str(root),
            )
            for name in ("revision", "provenance"):
                if hasattr(engine, name):
                    setattr(candidate_engine, name, getattr(engine, name))

            res = candidate_engine.update_file(str(target_file))
            persisted = _persist_live_engine(root, candidate_engine)
            if not persisted:
                raise _LocalCandidatePersistenceRejected(
                    "Local candidate snapshot persistence failed."
                )
        except Exception as failure:
            current_metadata = read_metadata(cache_dir)
            if (
                current_metadata != previous_metadata
                or metadata_path.exists() != previous_metadata_exists
            ):
                mcp_runtime._live_engines.pop(root_key, None)
                mcp_runtime._live_engine_revisions.pop(root_key, None)
                mcp_runtime._live_engine_provenance.pop(root_key, None)
                raise RuntimeError(
                    "Local snapshot metadata changed during a rejected candidate; "
                    "possible disk/cache divergence."
                ) from failure
            try:
                registry.restore_checkpoint(checkpoint)
            except Exception as rollback_failure:
                mcp_runtime._live_engines.pop(root_key, None)
                mcp_runtime._live_engine_revisions.pop(root_key, None)
                mcp_runtime._live_engine_provenance.pop(root_key, None)
                raise RuntimeError(
                    "Local registry rollback failed after a rejected candidate."
                ) from rollback_failure
            raise

        mcp_runtime._live_engines[root_key] = candidate_engine
        candidate_engine.provenance = "snapshot"
        candidate_engine.state.provenance = "snapshot"
        mcp_runtime._live_engine_provenance[root_key] = "snapshot"
        return res, candidate_engine, old_artifacts, True


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
    _ev_limit = 3 if max_items is None else min(3, max_items)
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
        if compact:
            ev_items = selected[:_ev_limit]
            evidence = dict(ev_items) if isinstance(value, dict) else ev_items
            collection = {
                "total": total,
                "truncated": total > len(evidence),
                "evidence": evidence,
            }
        else:
            collection = {
                "total": total,
                "truncated": truncated,
                "items": dict(selected) if isinstance(value, dict) else selected,
            }
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
            with mcp_runtime._engine_cache_transaction(root) as root_key:
                mcp_runtime._live_engine_revisions[root_key] = int(remote["revision"]) - 1
                engine = mcp_runtime.get_or_init_engine(root)
            live_state_persisted = True
        else:
            res, engine, old_artifacts, live_state_persisted = (
                _execute_local_candidate_update(
                    root,
                    target_file,
                    engine,
                )
            )
        new_artifacts = engine.state.artifacts.get(module_path, {})
        semantic_diff = _semantic_artifact_diff(old_artifacts, new_artifacts)
        affected_items, affected_total, affected_truncated = query_helpers.bounded_items(
            getattr(res, "affected_modules", []) or [], max_items
        )
        _ev_limit = 3 if max_items is None else min(3, max_items)
        if compact:
            affected_ev = affected_items[:_ev_limit]
            affected_view = {
                "total": affected_total,
                "truncated": affected_total > len(affected_ev),
                "evidence": affected_ev,
            }
        else:
            affected_view = {
                "total": affected_total,
                "truncated": affected_truncated,
                "items": affected_items,
            }
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
        runtime_restart_required = _mcp_runtime_restart_required(target_file)
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
        error_result = {"status": "ERROR", "file_path": str(target_file), "error": str(e)}
        if isinstance(e, _LocalCandidatePersistenceRejected):
            error_result["live_state_persisted"] = False
        return json.dumps(error_result, indent=2)
