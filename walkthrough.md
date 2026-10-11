# L32H2J1_FIX_16_STALE_TEST_CONTRACTS_AND_D1_HANDOFF

## FILES_CHANGED_THIS_TASK
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_minimal_registry_read_path.py`
- `C:\Temp\Contextor_Repo\tests\test_h3a_workspace_canonical_freshness.py`
- `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`
- `C:\Temp\Contextor_Repo\tests\test_cached_facts_live_analytics.py`
- `C:\Temp\Contextor_Repo\tests\test_cycles_live_lifecycle.py`
- `C:\Temp\Contextor_Repo\tests\test_persistent_topology_provenance.py`
- `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py`
- `C:\Temp\Contextor_Repo\tests\test_pipeline.py`

Only these nine authorized test files changed. `C:\Temp\Contextor_Repo\walkthrough.md` was overwritten as the report. `C:\Temp\Contextor_Repo\tests\mcp\tools\test_compact_evidence_contract.py` was read only.

## SOURCE_PREFLIGHT
DIRECT_EVIDENCE: pre-edit HEAD `7ee8ab8377aa194a4f8ed635f97966f9c74176ee`; pre-edit worktree had only `M walkthrough.md`. Contextor MCP complete `get_or_init_engine` source at `C:\Temp\Contextor_Repo\contextor\mcp\runtime.py:442-481` showed keyword-only `_defer_migration: bool = False`, `canonical_state=fresh`, `workspace_sync=verified`, revision 313. Exact test anchors were inspected before editing. The first supplied attachment was truncated mid-sentence; the complete replacement attachment was read before B/C/D changes. The exact planned changes were written to this report before edits; this final report supersedes that preflight checkpoint.

## MOCK_SIGNATURE_FIXES
The nine named A/D3 failing nodes now accept `*, _defer_migration=False` in every local `get_or_init_engine` mock. Return expressions and assertions remain unchanged. All five sequential mocks inside `test_file_edit_context_layer_guard` were updated. Production migration behavior was untouched.

## REGISTRY_LOCK_FIXTURES
In each of the three specified tests, `PersistentIdentityRegistry` and `FileStateManager` are constructed before the existing `builtins.open` patch. `IncrementalAnalysisEngine` is still constructed inside the patch; the cycles test retains its `Path.read_text` patch. Analytics/cycles/topology assertions are unchanged. All three tests passed, so no forbidden disk read by engine construction was observed in these targeted executions.

## GUI_PUBLISH_MOCK_CONTRACT
Both specified `Client.publish` fakes accept `acknowledge_installed=False` and assert that the GUI passed `True`. Their original event recording and return values remain. Both tests passed; GUI production code was untouched.

## H3A_COW_ENGINE_IDENTITY
The specified final assertion now checks current cache identity, old engine immutability at `r0`, current revision parity with public freshness, and `_live_engine_revisions` parity. Earlier UPDATED/workspace-sync/revision assertions remain. The targeted test passed.

## LAYER_REPORT_AST_OWNER
The facade AST writer target is `_analyze_layer_uncoordinated`, while `execute_global_pipeline` remains its own target. A new AST assertion verifies a real `ContextorFacade._analyze_layer_uncoordinated(...)` call in the `analyze_layer` wrapper's `try` body, with `acquire_full_analysis` before and `release_full_analysis` in `finally`. The datestamp AST assertions remain. The targeted test passed.

## TARGETED_GREEN_MATRIX_16
Exact command used repository `.venv` Python with `pytest -q` and only these 16 node IDs. Every row reached its original assertions and passed:

| Node | Result |
|---|---|
| `C:\Temp\Contextor_Repo\tests\mcp\tools\test_minimal_registry_read_path.py::test_fresh_minimal_query_uses_one_read_transaction_and_no_discovery` | PASS |
| `C:\Temp\Contextor_Repo\tests\mcp\tools\test_minimal_registry_read_path.py::test_incomplete_canonical_paths_fallback_runs_after_first_read_lock` | PASS |
| `C:\Temp\Contextor_Repo\tests\mcp\tools\test_minimal_registry_read_path.py::test_canonical_relative_path_is_resolved_from_repo_root` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_h3a_workspace_canonical_freshness.py::test_h3a_case_aa_analysis_job_revision_mismatch_fails_closed` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py::test_affected_mcp_queries_fail_closed_on_parse_stale_state` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py::test_minimal_file_context_fails_closed_without_usable_live_graph` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py::test_file_edit_context_minimal_mode_and_target_resolution` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py::test_file_edit_context_layer_guard` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py::test_analysis_endpoint_returns_reusable_job_and_pollable_completion` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_cached_facts_live_analytics.py::test_snapshot_lifecycle_and_consumer_projection` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_cycles_live_lifecycle.py::test_legacy_snapshot_hydration_recomputes_cycles_in_ram` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_persistent_topology_provenance.py::test_legacy_snapshot_reconstruction_with_provenance` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py::test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py::test_switching_repositories_keeps_previous_watcher_active` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_h3a_workspace_canonical_freshness.py::test_h3a_case_j_local_incremental_mutation_revision_sync` | PASS |
| `C:\Temp\Contextor_Repo\tests\test_pipeline.py::test_layer_report_writers_receive_datestamp` | PASS |

COMBINED_RESULT: 16 passed, 1 unrelated Authlib deprecation warning, 24.38 s. D1 was not included.

## NAMED_RELEVANT_REGRESSIONS
Exact named subset: 
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py::test_project_analysis_cold_migration_exits_outer_cache_transaction`
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py::test_direct_live_update_cold_refresh_exits_outer_cache_and_checks_revision`
- `C:\Temp\Contextor_Repo\tests\test_persistent_registry.py::test_constructor_waits_for_registry_lock_held_by_another_process`
- `C:\Temp\Contextor_Repo\tests\test_persistent_registry.py::test_constructor_holds_registry_os_lock_during_recovery_and_load`
- `C:\Temp\Contextor_Repo\tests\test_persistent_registry.py::test_constructor_releases_registry_lock_after_recovery_or_load_failure`
- `C:\Temp\Contextor_Repo\tests\test_persistent_registry.py::test_independent_registry_instances_share_the_same_os_lock_path`
- `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py::test_desktop_startup_publish_uses_startup_publish_writer_kind`
- `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py::test_desktop_skips_cache_publish_when_canonical_writer_is_busy_but_starts_watcher`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_candidate_cow_keeps_original_nested_facts_and_tracked_files`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_candidate_updated_installs_only_after_exact_persistence`
- `C:\Temp\Contextor_Repo\tests\test_pipeline.py::test_global_pipeline_forwards_datestamp_to_report_writer`

RESULT: 13 pytest cases passed (some named nodes are parametrized), 1 unrelated Authlib deprecation warning, 14.85 s. Coverage: deferred migration lock ordering; registry constructor recovery/locking; G2D desktop publish caller; local COW candidate publication; pipeline datestamp forwarding. No full suite run.

## D1_COMPACT_EVIDENCE_DISCOVERY
DIRECT_EVIDENCE: the current D1 fake is not cache-owned and lacks `state.clone_for_update`, tracked `FileStateManager._state`, and registry checkpoint/restore. Local `update_file` checks cache ownership before candidate update, so its fake `update_file` call count stays zero. The public `update_file` builds `affected_modules` with `query_helpers.bounded_items`, caps compact `evidence` at three, reports `total` and `truncated`, and omits `expand`. `_semantic_artifact_diff` computes symbol sets; `_semantic_diff_view` serializes `symbols_added`, `symbols_removed`, `signatures_changed`, `bodies_changed`, and `affected_symbols` with the same compact cap. The existing D1 file already tests `_semantic_diff_view` directly (source below). No D1 test edit, production edit, formatter redesign, or bypass occurred.

## D1_EXACT_TEST_SEAM
CONTRACT_PROVED: `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py:53-97` owns `_build_local_fallback_engine` and `_local_update`. The fixture creates a real repository/index/artifacts, `PersistentIdentityRegistry` with synced identities, `FileStateManager` with tracked provider, real `IncrementalAnalysisEngine`, and cache registration under the resolved root; it patches only LIVE connection absence for the local route. `test_local_candidate_updated_installs_only_after_exact_persistence` at :993-1027 proves this seam reaches real candidate update, exact persistence, and cache publication. It is the smallest inspected existing valid local candidate regression. Independently, `C:\Temp\Contextor_Repo\tests\mcp\tools\test_compact_evidence_contract.py:476-570` is the existing pure semantic formatter seam. UNKNOWN: the one-provider local fixture does not itself create four affected reverse modules, so it cannot alone establish D1's four-item `affected_modules` expectation. The auditor must specify the literal replacement; no alternate mutation path is proposed.

## D1_COMPLETE_SOURCE_FRAGMENTS
Every symbol below was retrieved from Contextor MCP with `mode=fetch`, `include=["implementation"]`, `implementation_is_complete=true`, and `workspace_sync=verified`; the final existing formatter tests are a contiguous complete source range from `get_source_range`. No preview or truncated source is treated as complete.

### `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:491-621` — `update_file`

```python
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
            cold_migration = False
            with mcp_runtime._engine_cache_transaction(root) as root_key:
                mcp_runtime._live_engine_revisions[root_key] = int(remote["revision"]) - 1
                engine = mcp_runtime.get_or_init_engine(
                    root, _defer_migration=True
                )
                cold_migration = engine is mcp_runtime._MIGRATION_NEEDED
                if cold_migration:
                    mcp_runtime._live_engine_revisions.pop(root_key, None)
            if cold_migration:
                mcp_runtime.get_or_init_engine(root)
                with mcp_runtime._engine_cache_transaction(root) as root_key:
                    engine = mcp_runtime._live_engines.get(root_key)
                    refreshed_revision = mcp_runtime._live_engine_revisions.get(root_key)
                    if (
                        engine is None
                        or refreshed_revision != int(remote["revision"])
                        or getattr(engine.state, "revision", None) != refreshed_revision
                    ):
                        raise RuntimeError(
                            "Canonical LIVE state could not be hydrated at the committed revision."
                        )
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
```

### `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:410-452` — `_semantic_artifact_diff`

```python
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
```

### `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:455-488` — `_semantic_diff_view`

```python
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
```

### `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:251-273` — `_execute_local_candidate_update`

```python
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
```

### `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:276-317` — `_execute_local_candidate_update_with_domain_fence`

```python
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
```

### `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py:320-407` — `_execute_local_candidate_update_unfenced`

```python
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
```

### `C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py:73-79` — `bounded_items`

```python
def bounded_items(items: list, limit: int | None) -> tuple[list, int, bool]:
    total = len(items)
    if limit is None:
        return items, total, False
    safe_limit = max(0, int(limit))
    selected = items[:safe_limit]
    return selected, total, total > len(selected)
```

### `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py:53-91` — `_build_local_fallback_engine`

```python
def _build_local_fallback_engine(tmp_path, monkeypatch, source):
    repo = tmp_path / "repo"
    repo.mkdir()
    provider = repo / "provider.py"
    provider.write_text(source, encoding="utf-8")
    index = index_repository(str(repo))
    modules = index.modules
    reexport_facts_by_module = materialize_reexport_facts_by_module(
        modules,
        index.reference_facts_by_module,
    )
    artifacts, failures = collect_module_artifacts(modules, str(repo))
    assert not failures
    trie = build_trie(modules)
    package_root = detect_package_root(modules, trie)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        reexport_facts_by_module=reexport_facts_by_module,
        artifacts=artifacts,
        dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
        trie=trie,
        package_root=package_root,
        artifact_consumption={},
    )
    registry = PersistentIdentityRegistry(str(repo))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules), collect_qualified_artifact_identities(artifacts)
        )
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    cache_dir = repo_cache_dir(repo)
    state_manager = FileStateManager(str(cache_dir))
    state_manager.update_state(str(provider))
    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(repo))
    monkeypatch.setattr(mcp_runtime, "_live_engines", {str(repo.resolve()): engine})
    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
    return repo, provider, engine
```

### `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py:94-97` — `_local_update`

```python
def _local_update(repo, provider):
    return json.loads(
        mcp_server.update_file.fn(repo_path=str(repo), file_path=str(provider))
    )
```

### `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py:993-1027` — `test_local_candidate_updated_installs_only_after_exact_persistence`

```python
def test_local_candidate_updated_installs_only_after_exact_persistence(
    tmp_path, monkeypatch
):
    repo, provider, engine = _build_local_fallback_engine(
        tmp_path, monkeypatch, "def run():\n    return 1\n"
    )
    assert update_file_module._persist_live_engine(repo, engine) is True
    key = str(repo.resolve())
    original_artifacts = deepcopy(engine.state.artifacts)
    provider.write_text(
        "def run():\n    return 1\n\ndef added():\n    return 2\n", encoding="utf-8"
    )
    real_persist = update_file_module._persist_live_engine
    seen = []

    def assert_before_publish(root, candidate):
        seen.append((mcp_runtime._live_engines[key] is engine, candidate is not engine))
        persisted = real_persist(root, candidate)
        seen.append((mcp_runtime._live_engines[key] is engine, candidate is not engine))
        return persisted

    monkeypatch.setattr(update_file_module, "_persist_live_engine", assert_before_publish)
    response = _local_update(repo, provider)
    published = mcp_runtime._live_engines[key]

    assert response["status"] == "UPDATED"
    assert response["live_state_persisted"] is True
    assert seen == [(True, True), (True, True)]
    assert published is not engine
    assert published.state is not engine.state
    assert published.state_manager._state is not engine.state_manager._state
    assert engine.state.artifacts == original_artifacts
    assert published.state.artifacts != original_artifacts
    assert read_metadata(repo_cache_dir(repo)).revision == 2
    assert published.revision == mcp_runtime._live_engine_revisions[key] == 2
```

### `C:\Temp\Contextor_Repo\tests\mcp\tools\test_compact_evidence_contract.py:415-473` — `test_compact_evidence_contract__update_file_collections_include_evidence`

```python
def test_compact_evidence_contract__update_file_collections_include_evidence(tmp_path, monkeypatch):
    update_calls = []

    class UpdateRes:
        status = "UPDATED"
        file_path = str(tmp_path / "pkg" / "a.py")
        graph_state = "fresh"
        dependencies_state = "fresh"
        blast_radius_state = "fresh"
        local_metrics_state = "fresh"
        global_metrics_state = "fresh"
        artifact_consumption_state = "fresh"
        affected_modules = ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"]
        delta = None

    class Engine:
        state = type("State", (), {"artifacts": {}})()
        def update_file(self, path):
            update_calls.append(path)
            return UpdateRes()

    engine = Engine()
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)
    monkeypatch.setattr("contextor.core.live_state.connect", lambda root: None)
    monkeypatch.setattr("contextor.mcp.tools.update_file._persist_live_engine", lambda root, eng: True)
    monkeypatch.setattr("contextor.mcp.tools.update_file._semantic_artifact_diff", lambda old, new: {
        "changed_symbol_count": 4,
        "body_change_count": 0,
        "body_only_changes_tracked": False,
        "symbols_added": ["s1", "s2", "s3", "s4"],
        "symbols_removed": [],
        "signatures_changed": {},
        "bodies_changed": [],
        "affected_symbols": ["s1", "s2", "s3", "s4"],
    })

    file_path = tmp_path / "pkg" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("x = 1\n", encoding="utf-8")

    raw = update_file(str(tmp_path), file_path="pkg/a.py", compact=True)
    res = json.loads(raw)

    assert len(update_calls) == 1, "update_file MUST NOT perform extra analysis/update calls"

    aff = res["affected_modules"]
    assert "evidence" in aff
    assert aff["total"] == 4
    assert len(aff["evidence"]) == 3
    assert aff["truncated"] is True
    assert "expand" not in aff

    diff = res["semantic_diff"]
    sym_added = diff["symbols_added"]
    assert "evidence" in sym_added
    assert sym_added["total"] == 4
    assert len(sym_added["evidence"]) == 3
    assert sym_added["truncated"] is True
    assert "expand" not in sym_added
```

### `C:\Temp\Contextor_Repo\tests\mcp\tools\test_compact_evidence_contract.py:476-570` — `existing_semantic_diff_formatter_regressions`

```python
def test_compact_evidence_contract__update_file_compact_does_not_advertise_mutating_expand():
    diff = {
        "symbols_added": ["s1", "s2", "s3", "s4"],
        "symbols_removed": ["r1", "r2", "r3", "r4"],
        "signatures_changed": {
            "k1": {"before": "b1", "after": "a1"},
            "k2": {"before": "b2", "after": "a2"},
            "k3": {"before": "b3", "after": "a3"},
            "k4": {"before": "b4", "after": "a4"},
        },
        "bodies_changed": ["b1", "b2", "b3", "b4"],
        "affected_symbols": ["a1", "a2", "a3", "a4"],
    }
    view = _semantic_diff_view(diff, max_items=10, compact=True)

    for key in ("symbols_added", "symbols_removed", "signatures_changed", "bodies_changed", "affected_symbols"):
        col = view[key]
        assert col["total"] == 4
        assert col["truncated"] is True
        assert len(col["evidence"]) == 3
        assert "expand" not in col


def test_compact_evidence_contract__zero_items_returns_empty_evidence_not_truncated():
    view = _semantic_diff_view({"symbols_added": []}, max_items=10, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 0
    assert col["truncated"] is False
    assert col["evidence"] == []
    assert "expand" not in col


def test_compact_evidence_contract__one_item_returns_one_evidence_not_truncated():
    view = _semantic_diff_view({"symbols_added": ["sym1"]}, max_items=10, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 1
    assert col["truncated"] is False
    assert col["evidence"] == ["sym1"]
    assert "expand" not in col


def test_compact_evidence_contract__three_items_returns_three_not_truncated():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3"]}, max_items=10, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 3
    assert col["truncated"] is False
    assert col["evidence"] == ["s1", "s2", "s3"]
    assert "expand" not in col


def test_compact_evidence_contract__four_items_returns_three_and_truncated():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=10, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 4
    assert col["truncated"] is True
    assert col["evidence"] == ["s1", "s2", "s3"]
    assert "expand" not in col


def test_compact_evidence_contract__explicit_limit_one_caps_evidence_at_one():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=1, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 4
    assert col["truncated"] is True
    assert col["evidence"] == ["s1"]
    assert len(col["evidence"]) == 1


def test_compact_evidence_contract__null_limit_still_caps_compact_evidence_at_three():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4", "s5"]}, max_items=None, compact=True)
    col = view["symbols_added"]
    assert col["total"] == 5
    assert col["truncated"] is True
    assert len(col["evidence"]) == 3
    assert col["evidence"] == ["s1", "s2", "s3"]


def test_compact_evidence_contract__compact_false_preserves_existing_full_items_contract():
    view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=10, compact=False)
    col = view["symbols_added"]
    assert col["total"] == 4
    assert col["truncated"] is False
    assert "items" in col
    assert col["items"] == ["s1", "s2", "s3", "s4"]
    assert "evidence" not in col


def test_compact_evidence_contract__evidence_is_exact_prefix_of_full_collection():
    full_view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=10, compact=False)
    compact_view = _semantic_diff_view({"symbols_added": ["s1", "s2", "s3", "s4"]}, max_items=10, compact=True)
    assert compact_view["symbols_added"]["evidence"] == full_view["symbols_added"]["items"][:3]


def test_compact_evidence_contract__update_file_docs_require_noncompact_and_unbounded_for_complete_evidence():
    from contextor.mcp import documentation
```

## SOURCE_SYNC
Post-edit Contextor complete symbol retrieval for one changed test symbol in each of the nine files returned `canonical_state=fresh`, `workspace_sync=verified`, canonical revision 324. Complete production D1 symbols returned the same. Local `py_compile` succeeded for all nine changed tests; `git diff --check` succeeded. No source retrieval was accepted from a preview/truncated response.

## LIVE_REVISION_BEFORE_AFTER
Before: 313. After: 324, same activity epoch `31d588befe2843208dc2230a6de2fcb0`. `get_live_events(after_revision=313)` returned continuous revisions 314-324, eleven `desktop_watcher` UPDATED events for the nine edited tests (two repeat edits), `resync_required=false`, zero syntax errors, zero cycles. No manual `update_file`, analysis, or restart occurred.

## PRODUCTION_FILES_UNCHANGED
`git status --short` after edits listed exactly the nine authorized test files plus `walkthrough.md`; no production file and no D1 test was modified.

## RESTART_REQUIRED
NO for this test-only change. Serving production code was not edited. Contextor source indexing of tests is verified; no imported-code reload claim is made.

## REMAINING_GLOBAL_FAILURES
One original global failure remains intentionally unresolved: `C:\Temp\Contextor_Repo\tests\mcp\tools\test_compact_evidence_contract.py::test_compact_evidence_contract__update_file_collections_include_evidence` (D1). It was excluded from the green gate and not modified. A new full global run was not authorized; this is a classification of the original 17, not a new suite certification.

## FULL_DIFFS_FOR_ALL_CHANGED_FILES
The following is the full exact Git diff for every changed test file; `walkthrough.md` is the report and excluded from source/test diff accounting.

```diff
diff --git a/tests/mcp/tools/test_minimal_registry_read_path.py b/tests/mcp/tools/test_minimal_registry_read_path.py
index a68cd70..504ec32 100644
--- a/tests/mcp/tools/test_minimal_registry_read_path.py
+++ b/tests/mcp/tools/test_minimal_registry_read_path.py
@@ -36,7 +36,7 @@ def test_fresh_minimal_query_uses_one_read_transaction_and_no_discovery(tmp_path
     state.cached_analytics_state = "deferred"
     state.topology_metrics_state = "deferred"
     engine = SimpleNamespace(state=state)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine)
 
     counts = {"read": 0, "write": 0, "discover": 0}
     original_read = PersistentIdentityRegistry.read_transaction
@@ -61,7 +61,7 @@ def test_incomplete_canonical_paths_fallback_runs_after_first_read_lock(tmp_path
     state = RepositoryAnalysisState(modules={"pkg.module": object()})
     state.resync_required = False
     engine = SimpleNamespace(state=state)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine)
 
     active_reads = {"value": 0, "nested": False, "discover": 0}
     original_read = PersistentIdentityRegistry.read_transaction
@@ -107,7 +107,7 @@ def test_canonical_relative_path_is_resolved_from_repo_root(tmp_path, monkeypatc
     state.dependency_graph = SimpleNamespace(hard_edges={}, soft_edges={})
     state.cached_analytics_state = "deferred"
     state.topology_metrics_state = "deferred"
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: SimpleNamespace(state=state))
 
     result = json.loads(get_file_edit_context(str(tmp_path), target="pkg.module", mode="minimal"))
 
diff --git a/tests/test_cached_facts_live_analytics.py b/tests/test_cached_facts_live_analytics.py
index 938b93b..bfa2382 100644
--- a/tests/test_cached_facts_live_analytics.py
+++ b/tests/test_cached_facts_live_analytics.py
@@ -327,11 +327,13 @@ def test_snapshot_lifecycle_and_consumer_projection(tmp_path):
     loaded_leg, _ = load_snapshot(cache_dir, expected_state_id="legacy_snap")
     assert loaded_leg.cached_analytics_state == "deferred"
 
+    registry = PersistentIdentityRegistry(str(tmp_path))
+    file_state_manager = FileStateManager(str(cache_dir))
     with patch("builtins.open", side_effect=OSError("Disk read blocked")):
         engine = IncrementalAnalysisEngine(
             loaded_leg,
-            PersistentIdentityRegistry(str(tmp_path)),
-            FileStateManager(str(cache_dir)),
+            registry,
+            file_state_manager,
             str(tmp_path),
         )
 
diff --git a/tests/test_cycles_live_lifecycle.py b/tests/test_cycles_live_lifecycle.py
index d1b6f08..c8673b7 100644
--- a/tests/test_cycles_live_lifecycle.py
+++ b/tests/test_cycles_live_lifecycle.py
@@ -194,12 +194,14 @@ def test_legacy_snapshot_hydration_recomputes_cycles_in_ram(tmp_path):
     assert hasattr(loaded_state, "cycles_state")
     assert loaded_state.cycles_state == "deferred"
 
+    registry = PersistentIdentityRegistry(str(tmp_path))
+    file_state_manager = FileStateManager(str(cache_dir))
     with patch("builtins.open", side_effect=OSError("Disk read blocked")), \
          patch("pathlib.Path.read_text", side_effect=OSError("Disk read blocked")):
         engine = IncrementalAnalysisEngine(
             loaded_state,
-            PersistentIdentityRegistry(str(tmp_path)),
-            FileStateManager(str(cache_dir)),
+            registry,
+            file_state_manager,
             str(tmp_path),
         )
 
diff --git a/tests/test_h3a_workspace_canonical_freshness.py b/tests/test_h3a_workspace_canonical_freshness.py
index b083483..8a14781 100644
--- a/tests/test_h3a_workspace_canonical_freshness.py
+++ b/tests/test_h3a_workspace_canonical_freshness.py
@@ -405,7 +405,15 @@ def test_h3a_case_j_local_incremental_mutation_revision_sync(tmp_path):
 
     assert freshness["workspace_sync"] == "verified"
     assert freshness["canonical_revision"] > r0
-    assert engine0.state.revision == freshness["canonical_revision"]
+    current_engine = mcp_runtime.get_or_init_engine(repo)
+    assert current_engine is not engine0
+    assert current_engine is mcp_runtime._live_engines[str(repo)]
+    assert engine0.state.revision == r0
+    assert current_engine.state.revision == freshness["canonical_revision"]
+    assert (
+        mcp_runtime._live_engine_revisions[str(repo)]
+        == freshness["canonical_revision"]
+    )
 
 
 def test_h3a_case_k_real_remote_live_lifecycle_and_journal_separation(tmp_path):
@@ -1403,7 +1411,7 @@ def test_h3a_case_aa_analysis_job_revision_mismatch_fails_closed(tmp_path, monke
         }
 
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine)
     analysis_jobs._analysis_tasks.clear()
     analysis_jobs._analysis_jobs_by_repo.clear()
 
diff --git a/tests/test_live_desktop_integration.py b/tests/test_live_desktop_integration.py
index 5b5c340..39c2079 100644
--- a/tests/test_live_desktop_integration.py
+++ b/tests/test_live_desktop_integration.py
@@ -334,7 +334,14 @@ def test_desktop_publishes_latest_snapshot_and_replaces_existing_watcher(
     events = []
 
     class Client:
-        def publish(self, published, *, origin="unknown"):
+        def publish(
+            self,
+            published,
+            *,
+            origin="unknown",
+            acknowledge_installed=False,
+        ):
+            assert acknowledge_installed is True
             events.append(("publish", published, origin))
             return {"status": "ok"}
 
@@ -551,7 +558,14 @@ def test_switching_repositories_keeps_previous_watcher_active(tmp_path, monkeypa
     events = []
 
     class Client:
-        def publish(self, _state, *, origin="unknown"):
+        def publish(
+            self,
+            _state,
+            *,
+            origin="unknown",
+            acknowledge_installed=False,
+        ):
+            assert acknowledge_installed is True
             events.append(("publish", origin))
             return {"status": "ok"}
 
diff --git a/tests/test_live_e2e_corrections.py b/tests/test_live_e2e_corrections.py
index d55f4d0..95e7d4f 100644
--- a/tests/test_live_e2e_corrections.py
+++ b/tests/test_live_e2e_corrections.py
@@ -259,7 +259,7 @@ def test_affected_mcp_queries_fail_closed_on_parse_stale_state(
 ):
     state = _stale_mcp_state(tmp_path)
     engine = SimpleNamespace(state=state)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine)
     monkeypatch.setattr(query_helpers, "read_registries",
         lambda _root: (
             {"provider": "1/1"},
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index c56c937..c120742 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -725,7 +725,7 @@ def test_minimal_file_context_fails_closed_without_usable_live_graph(
             recovered_artifacts={},
         ),
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: None)
     missing = json.loads(
         mcp_server.get_file_edit_context.fn(
             repo_path=str(tmp_path), target="1/1", mode="minimal"
@@ -734,7 +734,7 @@ def test_minimal_file_context_fails_closed_without_usable_live_graph(
 
     state = RepositoryAnalysisState(modules={"provider": object()})
     monkeypatch.setattr(
-        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
+        mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: SimpleNamespace(state=state)
     )
     missing_graph = json.loads(
         mcp_server.get_file_edit_context.fn(
@@ -959,7 +959,7 @@ def test_analysis_endpoint_returns_reusable_job_and_pollable_completion(
     engine_state = SimpleNamespace(fresh=True, revision=1)
     engine = SimpleNamespace(state=engine_state)
     monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine)
     analysis_jobs._analysis_tasks.clear()
     analysis_jobs._analysis_jobs_by_repo.clear()
 
@@ -4633,7 +4633,7 @@ def test_file_edit_context_minimal_mode_and_target_resolution(tmp_path, monkeypa
         )
     )
     mcp_runtime._live_engine_revisions[str(root)] = 42
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine)
     monkeypatch.setattr(query_helpers, "read_registries",
         lambda _root: (
             {"pkg.module": "10/1", "consumer.mod": "20/1", "tests.test_pkg": "30/1"},
@@ -5228,7 +5228,7 @@ def test_file_edit_context_layer_guard(monkeypatch, tmp_path):
             dependency_graph=empty_graph,
         )
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_fresh_clean)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine_fresh_clean)
 
     res_clean_ui = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
     assert res_clean_ui["layer_guard"]["available"] is True
@@ -5270,7 +5270,7 @@ def test_file_edit_context_layer_guard(monkeypatch, tmp_path):
             dependency_graph=empty_graph,
         )
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_with_v)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine_with_v)
 
     # For pkg.ui_mod (source of 2 violations -> 2 outbound)
     res_ui_v = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
@@ -5308,7 +5308,7 @@ def test_file_edit_context_layer_guard(monkeypatch, tmp_path):
             dependency_graph=empty_graph,
         )
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_inbound_core)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine_inbound_core)
     res_inbound_core = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.core_mod", mode="minimal"))
     assert res_inbound_core["layer_guard"]["outbound_rules_defined"] is False
     assert res_inbound_core["layer_guard"]["outbound_violation_count"] == 0
@@ -5326,7 +5326,7 @@ def test_file_edit_context_layer_guard(monkeypatch, tmp_path):
             dependency_graph=empty_graph,
         )
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_deferred)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine_deferred)
     res_deferred = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
     assert res_deferred["layer_guard"]["available"] is False
     assert "deferred" in res_deferred["layer_guard"]["reason"]
@@ -5342,7 +5342,7 @@ def test_file_edit_context_layer_guard(monkeypatch, tmp_path):
             dependency_graph=empty_graph,
         )
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_stale)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root, *, _defer_migration=False: engine_stale)
     res_stale = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
     assert res_stale["layer_guard"]["available"] is False
     assert "stale" in res_stale["layer_guard"]["reason"]
diff --git a/tests/test_persistent_topology_provenance.py b/tests/test_persistent_topology_provenance.py
index 34092bf..550bda3 100644
--- a/tests/test_persistent_topology_provenance.py
+++ b/tests/test_persistent_topology_provenance.py
@@ -177,11 +177,13 @@ def test_legacy_snapshot_reconstruction_with_provenance(tmp_path):
     assert hasattr(loaded_state, "topology_metrics_state")
     assert loaded_state.topology_metrics_state == "deferred"
 
+    registry = PersistentIdentityRegistry(str(tmp_path))
+    file_state_manager = FileStateManager(str(cache_dir))
     with patch("builtins.open", side_effect=OSError("Disk read blocked")):
         engine = IncrementalAnalysisEngine(
             loaded_state,
-            PersistentIdentityRegistry(str(tmp_path)),
-            FileStateManager(str(cache_dir)),
+            registry,
+            file_state_manager,
             str(tmp_path),
         )
 
diff --git a/tests/test_pipeline.py b/tests/test_pipeline.py
index 4a8184a..d348b9b 100644
--- a/tests/test_pipeline.py
+++ b/tests/test_pipeline.py
@@ -179,7 +179,7 @@ def test_per_analysis_excludes_reject_paths_outside_repository(
 def test_layer_report_writers_receive_datestamp():
     root = Path(__file__).parents[1]
     targets = {
-        root / "contextor" / "core" / "api" / "facade.py": "analyze_layer",
+        root / "contextor" / "core" / "api" / "facade.py": "_analyze_layer_uncoordinated",
         root / "contextor" / "core" / "reporting_engine" / "pipeline.py": (
             "execute_global_pipeline"
         ),
@@ -206,6 +206,39 @@ def test_layer_report_writers_receive_datestamp():
             assert isinstance(forwarded["datestamp"], ast.Name)
             assert forwarded["datestamp"].id == "datestamp"
 
+    facade_tree = ast.parse(
+        (root / "contextor" / "core" / "api" / "facade.py").read_text(encoding="utf-8")
+    )
+    wrapper = next(
+        node for node in ast.walk(facade_tree)
+        if isinstance(node, ast.FunctionDef) and node.name == "analyze_layer"
+    )
+    coordinated_try = next(node for node in wrapper.body if isinstance(node, ast.Try))
+    assert any(
+        isinstance(node, ast.Call)
+        and isinstance(node.func, ast.Name)
+        and node.func.id == "acquire_full_analysis"
+        for statement in wrapper.body
+        for node in ast.walk(statement)
+        if statement is not coordinated_try
+    )
+    assert any(
+        isinstance(node, ast.Call)
+        and isinstance(node.func, ast.Attribute)
+        and isinstance(node.func.value, ast.Name)
+        and node.func.value.id == "ContextorFacade"
+        and node.func.attr == "_analyze_layer_uncoordinated"
+        for statement in coordinated_try.body
+        for node in ast.walk(statement)
+    )
+    assert any(
+        isinstance(node, ast.Call)
+        and isinstance(node.func, ast.Name)
+        and node.func.id == "release_full_analysis"
+        for statement in coordinated_try.finalbody
+        for node in ast.walk(statement)
+    )
+
 
 def test_extracted_layer_pipeline_builds_analytics_and_status(monkeypatch):
     captured = {}
```

## FINAL_VERDICT
L32H2J1_16_TESTS_PASS_D1_PENDING
