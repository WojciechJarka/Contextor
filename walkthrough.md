# L32H2D2A registry read-only patch and D2B direct-writer source handoff

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py
- C:\Temp\Contextor_Repo\tests\test_persistent_registry.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only; excluded from source/test diff).
Git status showed exactly those three production/test files and the report modified. Existing L32H2D1 production/test changes were not edited in this task.

## READ_TRANSACTION_SOURCE_CONTRACT

DIRECT_EVIDENCE from complete Contextor implementations at canonical revision 228, workspace_sync=verified: read_registries only reads four _state mappings and returns them. Before patch it used registry.transaction(). PersistentIdentityRegistry.__init__ (C:\Temp\Contextor_Repo\contextor\core\reporting_engine\persistent_registry.py:15–43) invokes _recover_transaction and _load_all. transaction (199–263) obtains registry lock, recovers and loads, then unconditionally writes all registry JSON via temporary files, a transaction marker and os.replace after yield. read_transaction (315–334) obtains the same registry lock, recovers and loads, then yields without a commit loop. _recover_transaction (172–197) may replace staged JSON and remove the marker when an interrupted transaction is present. _load_all (113–119) loads and performs in-memory repair. The exact one-line production substitution changes only the context manager in read_registries; constructor/recovery/write APIs and schema remain unchanged. Returned mappings are read from the same _state keys.

## RED_RESULT

Before production edit, four focused tests: 3 expected FAIL, 1 PASS. Healthy read changed st_mtime_ns of registry JSON; instrumentation caught entry into write transaction; injected read_transaction error was ignored because that API was never called. Interrupted-commit recovery passed. RED command exit 1, 3 failed/1 passed in 7.97s.

## GREEN_RESULT

After exact one-line patch: the four new regressions passed (4 passed, 0 failed). Selected existing + new targeted gate: complete C:\Temp\Contextor_Repo\tests\test_persistent_registry.py; complete C:\Temp\Contextor_Repo\tests\mcp\tools\test_minimal_registry_read_path.py; exact-ID module context, exact artifact and registry-reading symbol lookup nodes; new MCP read-error test: 24 passed, 0 failed in 7.93s. No full repository suite. Python py_compile for the production file and two modified test files: exit 0. git diff --check for those files: exit 0 (Git emitted LF/CRLF working-copy warning only).

## REGISTRY_BYTES_AND_MTIME_INVARIANCE

CONTRACT_PROVED by isolated initialized registry: two consecutive read_registries calls returned all four exact expected mappings and persistent IDs; every registry JSON retained identical bytes and st_mtime_ns; no transaction.tmp or *.json.tmp existed before or after healthy reads. Separate test made PersistentIdentityRegistry.transaction forbidden and the read still succeeded. An ordinary completed write remained visible to the next read.

## REGISTRY_RECOVERY_COMPATIBILITY

CODE_PATH_PROVED: __init__ and read_transaction still call _recover_transaction. A focused test staged a committing module_registry.json.tmp plus transaction.tmp in an isolated repository; read_registries observed the recovered mappings and both staged file and marker disappeared. This is deliberately not a zero-write assertion during recovery. Read errors propagate as RuntimeError rather than returning invented empty mappings. Existing checkpoint/restore and read/write transaction tests passed in the complete targeted persistent-registry file.

## MCP_CONSUMER_COMPATIBILITY

Contextor get_file_edit_context for query_helpers reported tests_covering=53 (nontruncated when max_items=100), including MCP tool owners. Exact read_registries blast radius after edit lists 10 production MCP tool modules and six direct test consumers, no truncation. Selected module-context and symbol-implementation lookup tests passed. No MCP public response schema was changed. This is targeted consumer compatibility, not every 53-file gate.

## DIRECT_LAYER_WRITER_CALLERS

CODE_PATH_PROVED by complete facade method and exact caller regions: ContextorFacade.analyze_layer at C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1302–1491 initializes repository identity and registry; its registry.transaction at 1428 builds compact artifacts/layer slices, then writes report files. It calls resolve_authoritative_repository_state; that helper calls connect(root) and may migrate a legacy snapshot. Direct production callers: C:\Temp\Contextor_Repo\contextor\cli.py:104, C:\Temp\Contextor_Repo\contextor\mcp_worker.py:42, C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:278, C:\Temp\Contextor_Repo\contextor\ui\gui.py:2025. Contextor blast radius independently confirmed these four modules, plus five test consumers.

## DIRECT_SINGLE_FILE_WRITER_CALLERS

CODE_PATH_PROVED: ContextorFacade.analyze_single_file at C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1492–1776 initializes identity, resolves LIVE/snapshot state, optionally hydrates IncrementalAnalysisEngine and calls update_file at 1586. That engine can commit registry.transaction when identity_sync_required (C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:826); it updates FileStateManager RAM at 642/1012 and candidate/canonical state in its own engine. The facade requests LIVE canonical RAM publication with hydrated.client.publish for UPDATED at 1599–1637. Its own report compaction uses registry.transaction at 1674 and writes report/analytics files. Direct production callers: C:\Temp\Contextor_Repo\contextor\cli.py:113, C:\Temp\Contextor_Repo\contextor\mcp_worker.py:46, C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:283, C:\Temp\Contextor_Repo\contextor\ui\gui.py:2088; Contextor blast radius confirms these modules plus five test consumers.

FileStateManager.update_state is RAM-only (C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:475–485). No explicit save_engine_state/save_snapshot in analyze_single_file itself. CONDITIONAL: resolve_authoritative_repository_state calls migrate_legacy_snapshot, which may write a legacy migration snapshot before analysis. Whether an attempted LIVE publish is accepted depends on IPC response and committed snapshot state; no acceptance is inferred from method source alone.

## DIRECT_PROJECT_WRITER_CALLERS

ContextorFacade.analyze_project at C:\Temp\Contextor_Repo\contextor\core\api\facade.py:558 onward invokes execute_global_pipeline (registry mutation via artifact_pipeline.py:88–104), save_engine_state at 1108 and connect(path)/client.publish at 1135 onward. Targeted production search and Contextor blast radius found only run_full_analysis_exclusive (C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py:662) as a direct production caller. CLI, MCP job/worker, profile runner and GUI invoke that wrapper for project analysis. No unwrapped direct production project-analysis call was confirmed in the inspected source; the facade method itself is callable directly and does not acquire the lease internally, so external/dynamic reachability is UNKNOWN.

## EXISTING_LEASE_OWNERSHIP

CLI executes run_full_analysis_exclusive at cli.py:95 and then calls analyze_layer/analyze_single_file at 104/113 after wrapper return and lease release. MCP worker only wraps its project branch; layer/single branches call facade directly. MCP analysis_jobs only wraps project branch; layer/single calls directly under its in-process _analysis_lock, not the cross-process full_analysis.lock. GUI project task calls the wrapper (gui.py:1309); layer/single task closures call facade directly (2025/2088). Thus no inspected layer/single caller holds an existing full-analysis lease across its direct facade call. The methods themselves do not acquire full_analysis.lock.

## NESTED_LOCK_RISK

CONTRACT_PROVED: full_analysis.lock uses a nonreentrant per-repository threading.Lock; recursive acquisition would wait/timeout. No direct acquire_full_analysis/run_full_analysis_exclusive call exists inside the complete analyze_layer or analyze_single_file methods or the inspected resolver/hydration helper. Both scoped methods call resolve_authoritative_repository_state, which calls connect(root) and may migrate snapshot. This is a full_analysis → LIVE domain connection edge if an outer lease is held; it is not a nested full-analysis acquisition in the inspected path. Single-file's client.publish similarly does not visibly acquire the full-analysis coordinator in the facade body. Dynamic callbacks and unknown external service behavior remain UNKNOWN. This answers wrapper feasibility as an observed call-path property, without proposing a wrapper patch.

## EXACT_SOURCE_HANDOFF

Complete literal analyze_layer and analyze_single_file methods, the decision-making portions of analyze_project, caller regions and hydration helpers follow in SOURCE_APPENDIX. Project source is explicitly segmented and not represented as a complete 700+ line implementation. Contextor source ranges were exact and complete for each requested range, not preview output. No D2B implementation is made.

## MINIMUM_PATCH_OWNERS_FOR_D2B

Potential production boundaries identified by actual bypass calls, without selecting a patch: C:\Temp\Contextor_Repo\contextor\cli.py:95–113; C:\Temp\Contextor_Repo\contextor\mcp_worker.py:30–46; C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py:244–283; C:\Temp\Contextor_Repo\contextor\ui\gui.py:1309/2025/2088; canonical methods C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1302–1491 and 1492–1776; existing coordinator API C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py:410–699. This is a source handoff, not authorization to modify facade or callers.

## TARGETED_TEST_OWNERS

Registry patch: C:\Temp\Contextor_Repo\tests\test_persistent_registry.py; C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py; C:\Temp\Contextor_Repo\tests\mcp\tools\test_minimal_registry_read_path.py, test_get_module_context.py and test_get_symbol_implementation.py. D2B future scope: C:\Temp\Contextor_Repo\tests\test_facade_progress_staging.py, test_layer_state_only_hydration.py, test_live_single_file_reuse.py, test_full_analysis_coordination.py, test_repository_scope_guards.py, and MCP analysis-job/GUI integration owners. Contextor tests_covering was available through get_file_edit_context (53 query-helper module owners); targeted nodes were chosen from exact read/registry contracts. No further tests after entering D2B discovery.

## SOURCE_SYNC_VERIFICATION

Updated read_registries was fetched complete after edit with workspace_sync=verified and canonical revision 231. Contextor blast radius returned direct consumers without truncation. Textual git status/diff showed only the three authorized source/test files modified plus report. No Contextor update_file call.

## LIVE_REVISION_BEFORE_AFTER

Before 228; after 231. get_live_events(after_revision=228) returned continuous desktop_watcher UPDATED events: revision 229 for C:\Temp\Contextor_Repo\tests\test_persistent_registry.py, 230 for C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py, 231 for C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py. resync_required=false; same activity epoch 9e9a2a2edcb046bba00df0850244ad36.

## FULL_DIFFS_FOR_EVERY_CHANGED_SOURCE_TEST_FILE

Complete raw Git diff for the three task-modified production/test files:

```diff
diff --git a/contextor/mcp/query_helpers.py b/contextor/mcp/query_helpers.py
index 0d48511..e1db1b7 100644
--- a/contextor/mcp/query_helpers.py
+++ b/contextor/mcp/query_helpers.py
@@ -85,7 +85,7 @@ def read_registries(root: Path) -> tuple[dict, dict, dict, dict]:
     )
 
     registry = PersistentIdentityRegistry(str(root))
-    with registry.transaction():
+    with registry.read_transaction():
         mod_reg = registry._state.get("module_registry", {})
         art_reg = registry._state.get("artifact_registry", {})
     return (
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index e47921e..daf1bc6 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -77,6 +77,28 @@ def _patch_empty_registries(monkeypatch):
     monkeypatch.setattr(query_helpers, "read_registries", lambda _root: ({}, {}, {}, {}))
 
 
+def test_read_registries_observes_committed_write_and_propagates_read_error(
+    tmp_path, monkeypatch
+):
+    registry = PersistentIdentityRegistry(str(tmp_path))
+    with registry.transaction():
+        registry.sync_with_workspace({"first"}, {"first::run"})
+    assert query_helpers.read_registries(tmp_path)[0]["first"] == registry.get_module_id("first")
+
+    with registry.transaction():
+        registry.sync_with_workspace({"first", "second"}, {"first::run", "second::run"})
+    result = query_helpers.read_registries(tmp_path)
+    assert result[0]["second"] == registry.get_module_id("second")
+    assert result[2]["second::run"] == registry.get_artifact_id("second::run")
+
+    def fail_read(_self):
+        raise RuntimeError("registry read failed")
+
+    monkeypatch.setattr(PersistentIdentityRegistry, "read_transaction", fail_read)
+    with pytest.raises(RuntimeError, match="registry read failed"):
+        query_helpers.read_registries(tmp_path)
+
+
 class _ObservedRLock:
     def __init__(self, watched_thread_name: str):
         self._lock = threading.RLock()
diff --git a/tests/test_persistent_registry.py b/tests/test_persistent_registry.py
index 7d603e2..c985889 100644
--- a/tests/test_persistent_registry.py
+++ b/tests/test_persistent_registry.py
@@ -6,6 +6,7 @@ import pytest
 from pathlib import Path
 
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.mcp import query_helpers
 
 @pytest.fixture
 def temp_repo(tmp_path):
@@ -56,6 +57,72 @@ def test_checkpoint_restore_persists_exact_registry_state(temp_repo):
     assert reloaded._state["artifact_slots"] == checkpoint["artifact_slots"]
     assert reloaded._state["output_references"] == checkpoint["output_references"]
 
+
+def test_read_registries_healthy_read_keeps_bytes_mtime_and_ids(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.transaction():
+        registry.sync_with_workspace({"pkg.module"}, {"pkg.module::run"})
+    expected = (
+        copy.deepcopy(registry._state["module_registry"]["path_to_id"]),
+        copy.deepcopy(registry._state["module_registry"]["id_to_path"]),
+        copy.deepcopy(registry._state["artifact_registry"]["path_to_id"]),
+        copy.deepcopy(registry._state["artifact_registry"]["id_to_path"]),
+    )
+    files = tuple(registry.files.values())
+    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
+    marker = registry.transaction_file
+    temporary = tuple(path.with_suffix(".json.tmp") for path in files)
+    assert not marker.exists()
+    assert not any(path.exists() for path in temporary)
+
+    first = query_helpers.read_registries(Path(temp_repo))
+    second = query_helpers.read_registries(Path(temp_repo))
+
+    assert first == expected == second
+    assert {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in files} == before
+    assert not marker.exists()
+    assert not any(path.exists() for path in temporary)
+    reloaded = PersistentIdentityRegistry(temp_repo)
+    assert reloaded.get_module_id("pkg.module") == expected[0]["pkg.module"]
+    assert reloaded.get_artifact_id("pkg.module::run") == expected[2]["pkg.module::run"]
+
+
+def test_read_registries_does_not_enter_write_transaction(temp_repo, monkeypatch):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.transaction():
+        registry.sync_with_workspace({"pkg.module"}, {"pkg.module::run"})
+
+    def forbidden(_self):
+        pytest.fail("healthy read entered a write transaction")
+
+    monkeypatch.setattr(PersistentIdentityRegistry, "transaction", forbidden)
+    result = query_helpers.read_registries(Path(temp_repo))
+    assert result[0]["pkg.module"] == registry.get_module_id("pkg.module")
+    assert result[2]["pkg.module::run"] == registry.get_artifact_id("pkg.module::run")
+
+
+def test_read_registries_recovers_interrupted_commit(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    with registry.transaction():
+        registry.sync_with_workspace({"pkg.module"}, set())
+    path = registry.files["module_registry"]
+    next_state = json.loads(path.read_text(encoding="utf-8"))
+    next_state["path_to_id"]["pkg.recovered"] = "9/1"
+    next_state["id_to_path"]["9/1"] = "pkg.recovered"
+    staged = path.with_suffix(".json.tmp")
+    staged.write_text(json.dumps(next_state), encoding="utf-8")
+    registry.transaction_file.write_text(
+        json.dumps({"status": "committing", "files": ["module_registry"]}),
+        encoding="utf-8",
+    )
+
+    result = query_helpers.read_registries(Path(temp_repo))
+
+    assert result[0]["pkg.recovered"] == "9/1"
+    assert result[1]["9/1"] == "pkg.recovered"
+    assert not staged.exists()
+    assert not registry.transaction_file.exists()
+
 def test_identity_preservation(temp_repo):
     # nowy plik dostaje ID
     registry = PersistentIdentityRegistry(temp_repo)
```

## REMAINING_GLOBAL_WRITER_BYPASSES

After the read-only patch, healthy read_registries no longer unconditionally rewrites registry files; prior interrupted transaction recovery may still write as designed. Direct analyze_layer/analyze_single_file paths still write registry without full_analysis.lock in inspected production callers. No unwrapped production analyze_project caller was confirmed, but direct facade invocation remains possible. Conditional legacy snapshot migration and single-file LIVE publish require separate scope assessment. No global exclusion claim.

## RESTART_REQUIRED

YES for serving-process certification: MCP processes importing contextor.mcp.query_helpers need manual reload. Current source-index sync and fresh-process pytest do not prove imported-code reload. No MCP/LIVE/Desktop restart performed.

## FINAL_VERDICT

REGISTRY_READ_ONLY_TARGETED_PASS; D2B_LITERAL_SOURCE_HANDOFF_COMPLETE_WITH_UNKNOWN_DYNAMIC_REACHABILITY. Await auditor instruction and `proceduj`. No D2B production changes.

## SOURCE_APPENDIX

### C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py — read_registries, complete

```python
def read_registries(root: Path) -> tuple[dict, dict, dict, dict]:
    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    registry = PersistentIdentityRegistry(str(root))
    with registry.read_transaction():
        mod_reg = registry._state.get("module_registry", {})
        art_reg = registry._state.get("artifact_registry", {})
    return (
        mod_reg.get("path_to_id", {}),
        mod_reg.get("id_to_path", {}),
        art_reg.get("path_to_id", {}),
        art_reg.get("id_to_path", {}),
    )
```

### C:\Temp\Contextor_Repo\contextor\core\api\facade.py — ContextorFacade.analyze_layer, complete lines 1302–1491

```python
    def analyze_layer(
        root_dir: str,
        layer_dir: str,
        log=None,
        progress_callback=None,
        additional_excludes: list[str] | None = None,
    ) -> str:
        """Analyzes a specific layer. Returns output pattern."""
        progress = _StagedProgress(progress_callback, total_stages=10, log=log)
        progress.begin("Validating repository and layer scope")
        root_resolved, layer_resolved = _resolve_repository_target(
            root_dir, layer_dir, target_kind="layer"
        )
        repo_name = root_resolved.name
        layer_name = layer_resolved.name

        progress.begin("Initializing repository identity")
        registry = _initialize_repository_identity(root_resolved)
        reset_caches()

        if log:
            log(f"Processing layer '{layer_name}' in project '{repo_name}'...")
        excludes, extra_dirs = _analysis_filters(
            str(root_resolved), additional_excludes
        )
        from contextor.core.graph.resolver import build_trie, detect_package_root

        collision_facts = None
        authoritative_state = resolve_authoritative_repository_state(root_resolved)
        if authoritative_state is not None:
            progress.begin("Loading canonical LIVE context")
            state = authoritative_state.state
            modules = state.modules
            trie = state.trie or build_trie(modules.keys())
            package_root = (
                state.package_root
                or detect_package_root(modules, trie)
            )
            progress.begin("Reusing canonical dependency graph")
            graph = state.dependency_graph
            cache_hit = True
            skipped_files = []
            reference_index = None
            collision_facts = _assemble_layer_collision_facts(
                modules, state=state
            )
            if log:
                log(
                    "Reused canonical context "
                    f"from {authoritative_state.source}; skipped repository re-indexing."
                )
        else:
            index_progress = progress.begin("Indexing repository files")
            index = index_repository(
                str(root_resolved),
                excludes=excludes,
                extra_ignored_dirs=extra_dirs,
                progress_callback=index_progress,
            )
            modules = index.modules
            trie = build_trie(modules.keys())
            package_root = detect_package_root(modules, trie)
            progress.begin("Resolving dependency graph")
            graph_progress = progress.items
            graph, cache_hit = get_cached_graph(
                modules,
                lambda m: build_graph(
                    m,
                    trie=trie,
                    package_root=package_root,
                    progress_callback=graph_progress,
                ),
            )
            skipped_files = getattr(index, "skipped", [])
            reference_index = assemble_reference_index_or_fallback(
                modules,
                str(root_resolved),
                index.reference_facts_by_module,
            )
            collision_facts = _assemble_layer_collision_facts(
                modules, indexed_facts=index.collision_facts_by_module
            )

        if log:
            log("Calculating metrics and collisions for the full project...")
        metrics_progress = progress.begin("Computing metrics, cycles and debt")
        metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(
            modules,
            graph,
            progress_callback=metrics_progress,
            collision_facts=collision_facts,
        )

        runtime = {"cache_hit": cache_hit}

        if log:
            log("Preparing data structures for slicing...")
        progress.begin("Preparing report data structures")
        hotspots = detect_hotspots(graph.hard_edges)
        global_summary = generate_summary_report(
            metrics,
            cycles,
            debt,
            collisions=all_collisions,
            hotspots=hotspots,
        )
        global_structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
        artifacts_progress = progress.begin("Preparing artifact usage")
        if authoritative_state is not None:
            checkpoint(artifacts_progress, "Projecting canonical artifacts", 0, 1)
            global_artifacts = canonical_artifact_report(
                authoritative_state.state.artifacts
            )
        else:
            global_artifacts = generate_artifact_usage_report(
                modules,
                str(root_resolved),
                runtime,
                progress_callback=artifacts_progress,
                symbol_facts_by_module=getattr(index, "symbol_facts_by_module", None),
                reference_index=reference_index,
            )
        
        from contextor.core.reporting_engine.dictionary import IndexDictionary
        
        progress.begin("Compacting and slicing layer reports")
        with registry.transaction():
            index_dict = IndexDictionary(registry)
            global_compact_artifacts = compact_artifact_report(global_artifacts, index_dict)

            if log:
                log(f"Slicing reports for layer: {layer_name}...")

            # Build report_header once — same header for global summary and layer reports.
            report_header = build_report_header(str(root_resolved), "global")
            
            layer_sliced_reports = slice_report_for_layer(
            layer_path=str(layer_resolved),
            root_path=str(root_resolved),
            global_metrics=metrics,
            global_structure=global_structure,
            global_summary=global_summary,
            global_artifacts=global_artifacts,
            global_compact_artifacts=global_compact_artifacts,
            global_hotspots=hotspots,
            global_cycles=cycles,
            global_collisions=all_collisions,
            global_skipped_files=skipped_files,
            report_header=report_header,
            index_dict=index_dict,
        )

        if log:
            log(f"Saving 5 layer reports for '{layer_name}'...")
            
        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        from contextor.core.reporting_engine.layer_pipeline import (
            execute_layer_pipeline,
        )
        from contextor.core.reporting_engine.io_manager import write_layer_reports
        
        progress.begin("Writing layer report bundle")
        execute_layer_pipeline(
            repo_name,
            layer_name,
            layer_sliced_reports,
            log=log,
            datestamp=datestamp,
            progress_callback=progress.items,
        )
        write_layer_reports(
            repo_name=repo_name,
            layer_name=layer_name,
            layer_reports=layer_sliced_reports,
            datestamp=datestamp,
            log=log,
        )

        # Absolute, so what the GUI shows the user is a path that exists.
        pattern = str(output_dir() / f"{repo_name}_{layer_name}_*.json")

        progress.begin("Finalizing layer analysis")
        progress.finish()
        if log:
            log(f"Finished! Saved reports package: {pattern}")
        return pattern

    @staticmethod
```

### C:\Temp\Contextor_Repo\contextor\core\api\facade.py — ContextorFacade.analyze_single_file, complete lines 1492–1776

```python
    def analyze_single_file(
        file_path: str,
        repo_root: str,
        log=None,
        progress_callback=None,
        additional_excludes: list[str] | None = None,
        publication_result: dict[str, Any] | None = None,
    ) -> str:
        """Analyzes a single file within the context of a project. Returns report output path."""
        if publication_result is not None:
            publication_result.update(status="not_attempted", revision=None, warning=None)
        progress = _StagedProgress(progress_callback, total_stages=11, log=log)
        progress.begin("Validating repository and file scope")
        root_resolved, file = _resolve_repository_target(
            repo_root, file_path, target_kind="file"
        )
        if file.suffix.lower() != ".py":
            raise ValueError(f"Selected file is not a Python file: {file}")
        progress.begin("Initializing repository identity")
        registry = _initialize_repository_identity(root_resolved)
        repo_root = str(registry.repo_path.resolve())
        reset_caches()
        if log:
            log(f"Single file analysis: {file.name}")

        if log:
            log("Preparing project context...")
        excludes, extra_dirs = _analysis_filters(repo_root, additional_excludes)
        hydrated = None
        analysis_state = None
        state_only = False

        resolved = resolve_authoritative_repository_state(repo_root)

        if resolved is not None:
            state = resolved.state

            try:
                rel_path = file.resolve().relative_to(Path(repo_root).resolve())
                module_path = ".".join(rel_path.with_suffix("").parts)
            except ValueError:
                module_path = ""

            state_only_candidate = (
                not getattr(state, "resync_required", False)
                and getattr(state, "artifact_consumption_state", None) == "fresh"
                and getattr(state, "cycles_state", None) == "fresh"
                and getattr(state, "collisions_state", None) == "fresh"
                and isinstance(getattr(state, "module_usages", None), dict)
                and getattr(state, "artifacts", None) is not None
                and bool(module_path)
                and module_path in state.modules
            )

            if state_only_candidate:
                from contextor.core.analysis.state_manager import FileStateManager

                state_manager = FileStateManager(str(resolved.cache_dir))

                if not state_manager.has_changed(str(file)):
                    progress.begin("Loading canonical LIVE context")
                    verify_progress = progress.begin(
                        "Verifying selected file in canonical context"
                    )
                    checkpoint(
                        verify_progress,
                        f"Verifying {file.name}",
                        0,
                        1,
                    )

                    modules = state.modules
                    graph = state.dependency_graph
                    analysis_state = state
                    cache_hit = True
                    state_only = True

                    if log:
                        log(
                            "Reused unchanged canonical context "
                            f"from {resolved.source}; skipped incremental-engine materialization."
                        )

        if not state_only:
            hydrated = hydrate_repository_engine(repo_root)

        if state_only:
            pass
        elif hydrated is not None:
            progress.begin("Loading canonical LIVE context")
            update_progress = progress.begin(
                "Refreshing selected file in LIVE context"
            )
            checkpoint(update_progress, f"Refreshing {file.name}", 0, 1)
            update_result = hydrated.engine.update_file(str(file))
            if update_result.status in {"SYNTAX_ERROR", "ERROR"}:
                location = ""
                if getattr(update_result, "line_number", None):
                    location = f" at line {update_result.line_number}"
                raise ValueError(
                    f"Cannot analyze {file.name}{location}: {update_result.error}"
                )
            analysis_state = hydrated.engine.state
            modules = analysis_state.modules
            graph = analysis_state.dependency_graph
            cache_hit = True
            if update_result.status == "UPDATED" and hydrated.client is not None:
                try:
                    published = hydrated.client.publish(
                        analysis_state,
                        origin="scoped_analysis",
                        timeout=5.0,
                    )
                    if isinstance(published, dict) and published.get("status") == "ok":
                        if published.get("resync_required") is True:
                            status = "recovery_required"
                            warning = published.get("warning") or "LIVE recovery verification required."
                        else:
                            status = "success"
                            warning = None
                        revision = int(published["revision"]) if published.get("revision") is not None else None
                    else:
                        status = "failed"
                        revision = None
                        warning = (
                            published.get("error") if isinstance(published, dict) else None
                        ) or "Canonical LIVE service rejected publication."
                    if publication_result is not None:
                        publication_result.update(status=status, revision=revision, warning=warning)
                    if status in {"failed", "recovery_required"} and log:
                        log(f"[WARNING] Single-file LIVE publication: {warning}")
                except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError) as exc:
                    if publication_result is not None:
                        publication_result.update(status="failed", revision=None, warning=f"{type(exc).__name__}: {exc}")
                    if log:
                        log("[WARNING] Updated single-file state could not be published to LIVE.")
            if log:
                log(
                    "Reused canonical context "
                    f"from {hydrated.source}; skipped repository re-indexing."
                )
        else:
            index_progress = progress.begin("Indexing repository files")
            modules = build_index(
                repo_root,
                excludes=excludes,
                extra_ignored_dirs=extra_dirs,
                progress_callback=index_progress,
            )
            graph_progress = progress.begin("Resolving dependency graph")
            graph, cache_hit = get_cached_graph(
                modules,
                lambda m: build_graph(m, progress_callback=graph_progress),
            )

        if log:
            log("Generating global report (hotspots)...")
        progress.begin("Generating global context")
        global_report = generate_report(graph, modules=modules, runtime={"cache_hit": cache_hit})

        if log:
            log("Fetching deep context for file...")
        progress.begin("Collecting deep file context")
        ctx = collect_all_contexts(
            file_path,
            modules,
            graph,
            global_report=global_report,
            root_path=repo_root,
            progress_callback=progress.items,
            engine_state=analysis_state,
        )

        if log:
            log("Creating report for file...")

        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        from contextor.core.reporting_engine.dictionary import IndexDictionary

        progress.begin("Building and compacting file report")
        with registry.transaction():
            index_dict = IndexDictionary(registry)
            report = generate_single_file_report(ctx, len(modules), index_dict=index_dict)

        # Named after the module path, not the bare stem: two files called
        # 'engine.py' in different packages used to overwrite each other.
        try:
            relative = file.resolve().relative_to(Path(repo_root).resolve())
            slug = ".".join(relative.with_suffix("").parts)
        except ValueError:
            slug = file.stem

        output = str(output_dir() / f"single_{slug}.json")
        from contextor.core.reporting_engine.dictionary import compact_recursively
        progress.begin("Writing JSON report snapshots")
        compact_report = compact_recursively(
            report,
            index_dict,
            set(modules.keys()),
            progress_callback=progress.items,
        )
        compact_report["module_name"] = report["module_name"]
        save_single_file_report(compact_report, output)
        snapshot_dir = output_dir() / f"{Path(repo_root).resolve().name}_{datestamp}"
        snapshot_json = snapshot_dir / f"single_{slug}.json"
        save_single_file_report(compact_report, str(snapshot_json))



        # Graph analytics for the single analyzed module
        progress.begin("Generating graph analytics")
        from contextor.core.reporting_engine.graph_analytics import generate_graph_analytics_report
        from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report as _gen_art
        try:
            if analysis_state is not None:
                sf_artifact_data = canonical_artifact_report(
                    analysis_state.artifacts
                )
            else:
                sf_artifact_data = _gen_art(
                    modules,
                    repo_root,
                    runtime={"cache_hit": cache_hit},
                    progress_callback=progress.items,
                )
            target_module_id = None
            # Find module_id matching the analyzed file
            file_resolved = file.resolve()
            for mid, mod in modules.items():
                mod_path = Path(getattr(mod, "absolute_path", None) or getattr(mod, "path", ""))
                if mod_path.resolve() == file_resolved:
                    target_module_id = mid
                    break

            scope_mods = {target_module_id} if target_module_id else None
            # Include direct neighbors for useful matrix
            if scope_mods and target_module_id:
                from contextor.core.graph.graph import build_graph as _bg
                hard_e = graph.hard_edges
                neighbors = set(hard_e.get(target_module_id, []))
                for src, tgts in hard_e.items():
                    if target_module_id in tgts:
                        neighbors.add(src)
                scope_mods = {target_module_id} | neighbors

            ga_data = generate_graph_analytics_report(
                artifact_data=sf_artifact_data,
                hard_edges=graph.hard_edges,
                soft_edges=graph.soft_edges,
                modules=modules,
                index_dict=index_dict,
                scope="single_file",
                scope_modules=scope_mods,
                progress_callback=progress.items,
            )
            ga_output = str(output_dir() / f"single_{slug}_graph_analytics.json")
            import json as _json
            with open(ga_output, "w", encoding="utf-8") as f_ga:
                _json.dump(ga_data, f_ga, indent=2, ensure_ascii=False)
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            with open(
                snapshot_dir / f"single_{slug}_graph_analytics.json",
                "w",
                encoding="utf-8",
            ) as f_ga:
                _json.dump(ga_data, f_ga, indent=2, ensure_ascii=False)
        except Exception as _ga_err:
            if log:
                log(f"[WARNING] graph_analytics skipped for single file: {_ga_err}")

        progress.begin("Writing Markdown context")
        md_output = str(output_dir() / f"single_{slug}_llm_context.md")
        generate_llm_markdown(report, md_output)
        generate_llm_markdown(
            report,
            str(snapshot_dir / f"single_{slug}_llm_context.md"),
        )

        progress.begin("Finalizing single-file analysis")
        progress.finish()
        if log:
            log("Single file report and MD bundle saved successfully.")
        return output
```

### C:\Temp\Contextor_Repo\contextor\core\api\facade.py — analyze_project decision regions: signature, global report/registry boundary, snapshot/LIVE publication

```python
    def analyze_project(
        path: str,
        log=None,
        progress_callback=None,
        additional_excludes: list[str] | None = None,
        owner: str = "desktop_analysis",
    ) -> list:
        """
        Analyzes full project hierarchy, builds dependency graph, evaluates
        technical debt, detects cycles and saves all generated artifacts.

        Args:
            path: Absolute string path to the project root directory.
            log: Optional callback function for streaming stdout progress.
            progress_callback: Optional callback for progress percentage (completed, total, filename).
            additional_excludes: Optional list of additional directory paths to exclude.
            owner: Analysis caller identity (desktop_analysis, mcp_analysis, cli_analysis).

        Returns:
            list: List of architectural validation errors, if any.
        """
        facade_started = time.monotonic()

        def emit_stage_end(stage: str, started: float) -> None:
            elapsed_ms = (time.monotonic() - started) * 1000.0
            trace_event(
                "ANALYSIS",
                "FULL_ANALYSIS_STAGE_END",
                stage=stage,
                operation=stage,
                elapsed_ms=elapsed_ms,
                timing_semantics="critical_path_stage",
                result=f"stage={stage};elapsed_ms={elapsed_ms:.3f}",
            )

        def emit_stage_component(
            stage: str,
            component: str,
            elapsed_ms: float,
            *,
            status: str | None = None,
        ) -> None:
            trace_event(
                "ANALYSIS",
                "FULL_ANALYSIS_STAGE_COMPONENT_END",
                stage=stage,
                component=component,
                operation=f"{stage}:{component}",
                elapsed_ms=elapsed_ms,
                timing_semantics="critical_path_stage_component",
                status=status,
                result=(
                    f"stage={stage};component={component};"
                    f"elapsed_ms={elapsed_ms:.3f}"
                ),
            )

        def emit_stage_component_end(
            stage: str,
            component: str,
            started: float,
            *,
            status: str | None = None,
        ) -> float:
            elapsed_ms = (time.monotonic() - started) * 1000.0
            emit_stage_component(
                stage,
                component,
                elapsed_ms,
                status=status,
            )
            return elapsed_ms

        identity_and_setup_started = facade_started

        component_started = time.monotonic()
        progress = _StagedProgress(progress_callback, total_stages=8, log=log)
        progress.begin("Initializing repository identity")
        emit_stage_component_end(
            "identity_and_setup",
            "progress_setup",
            component_started,
        )
# ... unchanged intervening analysis/setup ...

        repo_name = Path(path).name

        metrics_progress = progress.begin("Computing metrics, cycles and debt")

        metrics_started = time.monotonic()
        metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(
            modules,
            graph,
            progress_callback=metrics_progress,
            collisions=all_collisions,
            collision_facts=collision_facts,
        )

        emit_stage_end("metrics", metrics_started)

        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report_progress = progress.begin("Generating architectural reports")

        reports_started = time.monotonic()
        report_result = execute_global_pipeline(
            repo_name=repo_name,
            modules=modules,
            graph=graph,
            metrics=metrics,
            cycles=cycles,
            debt=debt,
            runtime={"cache_hit": cache_hit},
            root_path=path,
            log=log,
            collisions=all_collisions,
            collision_facts=collision_facts,
            progress_callback=report_progress,
            skipped_files=index.skipped,
            datestamp=datestamp,
            trie=trie,
            package_root=package_root,
            symbol_facts_by_module=index.symbol_facts_by_module,
            reference_index=reference_index,
            test_facts_by_path=index.test_facts_by_path,
            automatic_test_dirs=index.automatic_test_dirs,
        )

        emit_stage_end("reports", reports_started)

        if log and report_result.get("high_risk_layers"):
            high_risk_layers = ", ".join(report_result["high_risk_layers"])
            log(f"Generated additional reports for high risk layers: {high_risk_layers}")

        canonical_materialization_started = time.monotonic()
        canonical_setup_started = canonical_materialization_started
        analysis_result = report_result.get("_analysis_result")

        progress.begin("Persisting canonical LIVE snapshot")
        if analysis_result:
            from contextor.core.analysis.state_manager import (
                FileStateManager,
                RepositoryAnalysisState,
                artifact_consumption_is_fresh,
                build_syntax_diagnostics_from_index,
                build_canonical_artifact_consumption,
                dependency_matrix_inputs_are_fresh,
                save_engine_state,
                validate_canonical_artifact_consumption_coverage,
            )
            from contextor.core.paths import repo_cache_dir
            from contextor.core.live_state.store import read_metadata
            from contextor.core.reporting_engine.graph_analytics import (
                compute_dependency_matrix_from_state,
                compute_shared_usage_clusters_from_state,
                compute_topology_analytics,
                is_valid_shared_usage_clusters_handoff,
            )

            emit_stage_component_end(
                "canonical_materialization",
                "setup_and_imports",
                canonical_setup_started,
            )

            component_started = time.monotonic()
            graph = getattr(analysis_result, "graph", None)
            hard_edges = getattr(graph, "hard_edges", {}) if graph else {}
            soft_edges = getattr(graph, "soft_edges", {}) if graph else {}
            metrics = getattr(analysis_result, "metrics", {})
            topology_analytics = compute_topology_analytics(hard_edges, soft_edges, metrics) if hard_edges else {}
            emit_stage_component_end(
                "canonical_materialization",
                "topology_analytics",
# ... unchanged intervening canonical materialization ...
            current_metadata = read_metadata(cache_dir)
            target_revision = (
                current_metadata.revision
                if current_metadata
                else 0
            ) + 1
            emit_stage_component_end(
                "persistence",
                "metadata_and_revision",
                component_started,
            )

            component_started = time.monotonic()
            file_state_payload = (
                file_state_manager.build_payload(
                    datestamp or "",
                    target_revision,
                )
                if file_state_manager is not None
                else None
            )
            emit_stage_component_end(
                "persistence",
                "file_state_payload",
                component_started,
            )

            component_started = time.monotonic()
            meta = save_engine_state(
                state,
                cache_dir,
                datestamp,
                writer=writer,
                repo_id=registry.repo_id,
                root_path=path,
                exact_revision=target_revision,
                file_state_payload=file_state_payload,
            )
            emit_stage_component_end(
                "persistence",
                "snapshot_save",
                component_started,
                status=(
                    "success"
                    if meta is not None
                    else "failed"
                ),
            )

            emit_stage_end("persistence", persistence_started)

            live_publish_started = time.monotonic()
            connect_ms = 0.0
            publish_ms = 0.0
            status_handling_ms = 0.0
            if meta is not None:
                from contextor.core.live_state import connect

                client = None
                try:
                    component_started = time.monotonic()
                    try:
                        client = connect(path)
                    finally:
                        connect_ms = (time.monotonic() - component_started) * 1000.0
                    if client is not None:
                        component_started = time.monotonic()
                        try:
                            published = client.publish(state, origin=origin)
                        finally:
                            publish_ms = (time.monotonic() - component_started) * 1000.0
                        component_started = time.monotonic()
                        if (
                            isinstance(published, dict)
                            and published.get("status") == "ok"
                            and published.get("revision") is not None
                        ):
                            live_publish_revision = int(published["revision"])
                            if published.get("resync_required") is True:
                                live_publish_status = "recovery_required"
                                live_publish_warning = (
                                    published.get("warning")
                                    or "LIVE recovery verification required."
                                )
                            else:
                                live_publish_status = "success"
```

### C:\Temp\Contextor_Repo\contextor\cli.py — actual operation calls lines 85–120

```python

    if not root.is_dir():
        print(f"[ERROR] Not a directory: {root}", file=sys.stderr)
        return 2

    root = str(root.resolve())

    log = None if args.quiet else (lambda message: print(f"[INFO] {message}"))

    try:
        errors, _ = run_full_analysis_exclusive(root, owner="cli_analysis", log=log)

        if args.layer:
            layer = Path(args.layer).expanduser().resolve()

            if not layer.is_dir():
                print(f"[ERROR] Not a directory: {layer}", file=sys.stderr)
                return 2

            ContextorFacade.analyze_layer(root, str(layer), log=log)

        if args.file:
            target = Path(args.file).expanduser().resolve()

            if not target.is_file():
                print(f"[ERROR] Not a file: {target}", file=sys.stderr)
                return 2

            ContextorFacade.analyze_single_file(str(target), root, log=log)

    except AnalysisCancelled:
        print("[INFO] Analysis cancelled.")
        return 130

    if not args.quiet:
        print(f"[INFO] Reports written to: {output_dir()}")
```

### C:\Temp\Contextor_Repo\contextor\mcp_worker.py — actual operation calls lines 20–55

```python
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("project", "layer", "single_file"))
    parser.add_argument("repo_path")
    parser.add_argument("target", nargs="?")
    args = parser.parse_args(argv)

    root = Path(args.repo_path).resolve()
    try:
        from contextor.core.analysis.full_analysis_coordinator import run_full_analysis_exclusive
        from contextor.core.api.facade import ContextorFacade

        if args.operation == "project":
            _, analysis_result = run_full_analysis_exclusive(
                str(root),
                owner="mcp_analysis",
                log=_log,
            )
            if analysis_result is None:
                raise RuntimeError("Analysis returned no canonical state.")
        elif args.operation == "layer":
            if not args.target:
                raise ValueError("Layer analysis requires a target directory.")
            ContextorFacade.analyze_layer(str(root), args.target, log=_log)
        else:
            if not args.target:
                raise ValueError("Single-file analysis requires a target file.")
            ContextorFacade.analyze_single_file(args.target, str(root), log=_log)
        return 0
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
```

### C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py — actual operation calls lines 225–295

```python
    operation: str,
    root: Path,
    target: Path | None = None,
    exclude_paths: list[str] | None = None,
    log=None,
) -> dict:
    effective_log = log or _stderr_log

    def run() -> dict:
        with _analysis_lock:
            previous_cache = os.environ.get("CONTEXTOR_CACHE_DIR")
            previous_registry = os.environ.get("CONTEXTOR_MCP_PROCESS_REGISTRY")
            os.environ["CONTEXTOR_CACHE_DIR"] = str(_mcp_cache_root(root))
            if previous_registry is None:
                os.environ[
                    "CONTEXTOR_MCP_PROCESS_REGISTRY"
                ] = str(registry_dir(root))
            try:
                if operation == "project":
                    _, result = run_full_analysis_exclusive(
                        str(root),
                        owner="mcp_analysis",
                        log=effective_log,
                        progress_callback=_analysis_progress_callback,
                        additional_excludes=exclude_paths,
                        is_cancelled=_analysis_shutdown_requested,
                    )
                    if result is None:
                        raise RuntimeError("Analysis returned no canonical state.")
                    skipped_files = (getattr(result, "summary_data", {}) or {}).get(
                        "skipped_files", []
                    )
                    if not isinstance(skipped_files, list):
                        skipped_files = []
                    return {
                        "skipped_python_files": skipped_files,
                        "live_publish_status": getattr(
                            result,
                            "live_publish_status",
                            "not_attempted",
                        ),
                        "live_publish_revision": getattr(
                            result,
                            "live_publish_revision",
                            None,
                        ),
                        "live_publish_warning": getattr(
                            result,
                            "live_publish_warning",
                            None,
                        ),
                    }
                if operation == "layer":
                    ContextorFacade.analyze_layer(
                        str(root), str(target), log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                elif operation == "single_file":
                    ContextorFacade.analyze_single_file(
                        str(target), str(root), log=effective_log,
                        additional_excludes=exclude_paths,
                    )
                else:
                    raise ValueError(f"Unsupported analysis operation: {operation}")
                return {}
            finally:
                if previous_cache is None:
                    os.environ.pop("CONTEXTOR_CACHE_DIR", None)
                else:
                    os.environ["CONTEXTOR_CACHE_DIR"] = previous_cache
                if previous_registry is None:
```

### C:\Temp\Contextor_Repo\contextor\ui\gui.py — layer/single-file task closures lines 1991–2112

```python
    def analyze_layer(self):
        root_dir = self.repo_path_var.get()
        layer_dir = self.layer_path_var.get()

        if not root_dir:
            messagebox.showwarning(
                "Missing repository", "Please select ROOT directory of scanned project"
            )
            return
        if not layer_dir:
            messagebox.showwarning(
                "Missing layer", "Please select a layer (subdirectory) to analyze."
            )
            return

        try:
            root_resolved = Path(root_dir).resolve()
            layer_resolved = Path(layer_dir).resolve()
        except Exception:
            messagebox.showerror("Invalid path", "Could not resolve selected paths.")
            return

        if (
            not root_resolved.is_dir()
            or not layer_resolved.is_dir()
            or layer_resolved == root_resolved
            or root_resolved not in layer_resolved.parents
        ):
            messagebox.showwarning(
                "Invalid layer", "Layer must be a subdirectory of the selected repository root."
            )
            return

        def task(log=None, progress_callback=None):
            return ContextorFacade.analyze_layer(
                str(root_resolved),
                str(layer_resolved),
                log=log,
                progress_callback=progress_callback,
            )

        def on_success(output_pattern):
            self._start_live_watcher(str(root_resolved))
            messagebox.showinfo("Done", f"Generated 5 layer reports:\n{output_pattern}")

        def on_error(exc):
            messagebox.showerror("Error", str(exc))

        self.progress_bar.is_cancelled = False

        run_with_progress(
            self.root,
            self.progress_bar,
            task,
            on_success=on_success,
            on_error=on_error,
            buttons=self._busy_buttons(),
# ... method boundary ...
            stop_button=self.stop_btn,
            operation_name="Layer analysis",
        )

    def analyze_single(self):
        file_path = self.file_path_var.get()
        if not file_path.endswith(".py"):
            messagebox.showwarning("Invalid file", "Select Python file first.")
            return

        repo_root = self.repo_path_var.get()
        if not repo_root:
            messagebox.showwarning(
                "Missing repository root", "Please select ROOT directory of scanned project"
            )
            return

        try:
            root_resolved = Path(repo_root).resolve()
            file_resolved = Path(file_path).resolve()
        except (OSError, RuntimeError):
            messagebox.showerror("Invalid path", "Could not resolve selected paths.")
            return
        if (
            not root_resolved.is_dir()
            or not file_resolved.is_file()
            or root_resolved not in file_resolved.parents
        ):
            messagebox.showwarning(
                "Invalid file",
                "Selected Python file must be inside the selected repository root.\n"
                f"Repository root:\n{root_resolved}",
            )
            return

        publication_result = {}

        def task(log=None, progress_callback=None):
            return ContextorFacade.analyze_single_file(
                str(file_resolved), str(root_resolved), log=log,
                progress_callback=progress_callback,
                publication_result=publication_result,
            )

        def on_success(output):
            if publication_result.get("status") == "recovery_required":
                self._request_full_analysis_recovery(
                    str(root_resolved),
                    "Canonical LIVE publish requires recovery verification.",
                )
                self._set_live_status(
                    "LIVE: recovery required after accepted publish "
                    f"(revision {publication_result.get('revision')})"
                )
            elif publication_result.get("status") != "failed":
                self._start_live_watcher(str(root_resolved))
            messagebox.showinfo("Done", f"Single file report created:\n{output}")

        def on_error(exc):
            messagebox.showerror("Error", str(exc))

        self.progress_bar.is_cancelled = False
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py — complete resolver and engine hydration

```python
def resolve_authoritative_repository_state(
    repo_path: str | Path,
) -> AuthoritativeRepositoryState | None:
    """Resolve the same LIVE-first, validated canonical state used by hydration."""

    from contextor.core.analysis.state_manager import load_engine_state
    from contextor.core.live_state.runtime import connect
    from contextor.core.live_state.store import migrate_legacy_snapshot, read_metadata
    from contextor.core.repository_identity import read_repository_identity

    root = Path(repo_path).resolve()
    identity = read_repository_identity(root)
    if identity is None:
        return None

    cache_dir = migrate_legacy_snapshot(root)
    client = connect(root)
    state = None
    revision = 0
    source = ""
    if client is not None:
        try:
            ping = client.ping()
            snapshot = client.snapshot()
            state = snapshot.get("state")
            revision = int(snapshot.get("revision", ping.get("revision", 0)))
            source = "live_service"
        except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError):
            client = None

    if state is None:
        metadata = read_metadata(cache_dir)
        state = load_engine_state(
            str(cache_dir),
            metadata.state_id if metadata else "",
            expected_repo_id=identity.repo_id,
            expected_root_path=identity.root_path,
        )
        source = "snapshot" if state is not None else ""

    if (
        state is None
        or not getattr(state, "modules", None)
        or getattr(state, "dependency_graph", None) is None
    ):
        return None

    return AuthoritativeRepositoryState(
        state=state,
        client=client,
        revision=revision,
        source=source,
        cache_dir=cache_dir,
    )


def hydrate_repository_engine(
    repo_path: str | Path,
) -> HydratedRepositoryEngine | None:
    """Load a complete engine without triggering a repository analysis."""

    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
    from contextor.core.analysis.state_manager import FileStateManager
    from contextor.core.reporting_engine.persistent_registry import (
        PersistentIdentityRegistry,
    )

    root = Path(repo_path).resolve()
    resolved = resolve_authoritative_repository_state(root)
    if resolved is None:
        return None

    engine = IncrementalAnalysisEngine(
        resolved.state,
        PersistentIdentityRegistry(str(root)),
        FileStateManager(str(resolved.cache_dir)),
        str(root),
    )
    return HydratedRepositoryEngine(
        engine=engine,
        client=resolved.client,
        revision=resolved.revision,
        source=resolved.source,
    )
```


