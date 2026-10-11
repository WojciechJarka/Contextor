# L32H2J2_COMPACT_EVIDENCE_VALID_COW_FIXTURE

## FILES_CHANGED_THIS_TASK
- `C:\Temp\Contextor_Repo\tests\mcp\tools\test_compact_evidence_contract.py`

Only this authorized test file changed. `C:\Temp\Contextor_Repo\walkthrough.md` was overwritten as this report. All production files and `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py` stayed read-only.

## SOURCE_PREFLIGHT
DIRECT_EVIDENCE: pre-edit HEAD `92d5133f37a1db9ab3dc4a05bcc5ac5de181d785`, clean worktree. Contextor MCP complete implementations of public `update_file` (:491-621), `_execute_local_candidate_update` (:251-273), `_execute_local_candidate_update_unfenced` (:320-407), `_semantic_artifact_diff` (:410-452), `_semantic_diff_view` (:455-488), reference fixture `_build_local_fallback_engine` (:53-91), and original D1 test (:415-473) all returned `canonical_state=fresh`, `workspace_sync=verified`, revision 324. `IncrementalAnalysisEngine.update_file` was too large for one symbol fetch; its entire method was retrieved as the exact contiguous source range `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:453-734`, with no preview accepted as complete. Contextor `get_file_edit_context` returned tests_covering for the production update owner (35 covering modules, including the compact contract module); exact safety node IDs were checked in the corresponding test source. The exact planned test-only diff was written to walkthrough.md before editing.

## REAL_LOCAL_ENGINE_FIXTURE
`_build_compact_local_engine` copies the verified fixture construction: real indexing, reexport materialization, artifact extraction, trie/graph, `RepositoryAnalysisState`, synchronized `PersistentIdentityRegistry`, isolated cache root, tracked `FileStateManager`, real `IncrementalAnalysisEngine`, resolved-root cache registration, and absent LIVE connection. It imports no helper from another test module.

## SINGLE_REAL_UPDATE_EXECUTION
The test persists the real baseline, writes `original` plus four real new functions, captures the original `IncrementalAnalysisEngine.update_file`, and installs only the auditor-specified class-method result adapter. The adapter records `(candidate,path)`, invokes the original implementation, asserts `UPDATED`, then substitutes only the four `affected_modules` result entries for response shaping. The public `update_file` is called once; `len(update_calls)==1`, and its engine is the distinct current cached candidate. `_semantic_artifact_diff` remains real and unpatched.

## CANONICAL_OWNERSHIP_AND_DOMAIN_FENCE
CODE_PATH_PROVED: the public call enters `_execute_local_candidate_update`; the existing code acquires the canonical local writer lease, cache transaction, RuntimeLeaseManager domain lock, and checks cache ownership before candidate construction. The test does not patch the lease, fence, ownership check, candidate helper, or LIVE client success. The test's genuine cache registration satisfies ownership; `status=UPDATED` and `live_state_persisted=True` show the public local path completed. The related local safety tests below passed. An exact pre-existing node specifically named for `Local cached engine ownership changed` was not found; this gap is reported rather than inventing coverage.

## COW_CANDIDATE_AND_PERSISTENCE
The real `_persist_live_engine(repo,original_engine)` returned True before source mutation. The public operation returned `UPDATED` with `live_state_persisted=True`. The cached current engine is the observed candidate and differs from the original. Current engine, canonical state, FileStateManager, and cache revision match committed `read_metadata(repo_cache_dir(repo))` revision/state_id. No snapshot persister or registry checkpoint/rollback was mocked.

## COMPACT_AFFECTED_MODULES_EVIDENCE
`affected_modules.total==4`, `evidence==["pkg.m1","pkg.m2","pkg.m3"]`, `truncated is True`, and `expand` is absent. These four names are inserted only into the returned update result *after* the real incremental operation; they do not alter canonical graph, registry, FileState, or snapshot.

## REAL_SEMANTIC_SYMBOL_DIFF
The four functions `s1` through `s4` are present in real candidate artifacts but absent from the original engine artifacts. The unpatched `_semantic_artifact_diff` generated `symbols_added.total==4`, compact `evidence==["s1","s2","s3"]`, `truncated is True`, and no `expand`. The test makes no second mutating public update to inspect the full list.

## D1_GREEN_RESULT
Final D1 targeted node: PASS (part of final 17-node gate). Initial focused D1 run after replacing the fake also passed: 1 passed in 2.91 s.

## COMPACT_CONTRACT_GREEN_RESULTS
Entire `C:\Temp\Contextor_Repo\tests\mcp\tools\test_compact_evidence_contract.py`: 18 passed in 3.04 s. This run preceded the final added metadata state_id assertions; the D1 node was rerun and passed with those assertions in the final 17-node gate.

## LOCAL_WRITER_REGRESSIONS
Named safety gate A: 10 passed, 1 unrelated Authlib deprecation warning, 12.38 s:
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_incremental_lease_precedes_cache_domain_and_spans_commit`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_writer_rejects_stale_revision_before_checkpoint_or_update`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_domain_fence_blocks_live_acquire_until_persistence_finishes`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_registry_rollback_completes_before_domain_fence_release`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_candidate_cow_keeps_original_nested_facts_and_tracked_files`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_candidate_rejected_persistence_preserves_cache_state_manager_and_registry`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_candidate_persister_exception_before_commit_restores_registry`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_candidate_updated_installs_only_after_exact_persistence`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_candidate_serializes_update_through_persistence`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_cold_fallback_rechecks_cache_after_writer_admission`

Named safety gate B: `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py::test_local_writer_rejects_untrusted_authority_before_mutation` and `::test_two_mcp_processes_cannot_enter_local_candidate_concurrently`: 11 parametrized cases passed, 1 unrelated Authlib warning, 22.09 s. These cover authority rejection and cross-process domain admission. The D1 test itself asserts one real incremental execution.

## ORIGINAL_17_REGRESSION_MATRIX
Final exact 17-node gate after the last assertion edit: 17 passed, 1 unrelated Authlib deprecation warning, 20.15 s. Each row is an original global failure:

| Node | Result |
|---|---|
| `C:\Temp\Contextor_Repo\tests\mcp\tools\test_compact_evidence_contract.py::test_compact_evidence_contract__update_file_collections_include_evidence` | PASS |
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

This is not a full repository-suite result.

## SOURCE_SYNC
Post-edit Contextor MCP complete fetch of the changed D1 test: `canonical_state=fresh`, `workspace_sync=verified`, canonical revision 327. Diagnostics cycles.count=0. Repository `.venv` `py_compile` on the changed test passed, and `git diff --check` passed.

## LIVE_REVISION_BEFORE_AFTER
Before edit: 324. After edit: 327, same LIVE continuity, `resync_required=false`. `get_live_events(after_revision=324)` returned desktop_watcher revisions 325 UPDATED, 326 UNCHANGED, 327 UPDATED for the authorized test file; no manual `update_file`, analysis, or restart occurred.

## PRODUCTION_FILES_UNCHANGED
Post-edit `git status --short`: exactly `M tests/mcp/tools/test_compact_evidence_contract.py` and `M walkthrough.md`. No production or reference-test file changed.

## RESTART_REQUIRED
NO. Only a test file changed; no serving production code was edited. Contextor source indexing is verified; no imported-code reload claim is made.

## FULL_DIFFS_FOR_ALL_CHANGED_FILES
Full exact Git diff for the sole changed test file:

```diff
diff --git a/tests/mcp/tools/test_compact_evidence_contract.py b/tests/mcp/tools/test_compact_evidence_contract.py
index a26ce20..3c47862 100644
--- a/tests/mcp/tools/test_compact_evidence_contract.py
+++ b/tests/mcp/tools/test_compact_evidence_contract.py
@@ -1,7 +1,21 @@
+import importlib
 import json
 from pathlib import Path
+from types import SimpleNamespace
 import pytest
 
+from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
+from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
+from contextor.core.live_state import read_metadata
+from contextor.core.paths import repo_cache_dir
+from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.reporting_layer.artifact_usage_report import (
+    collect_module_artifacts,
+    collect_qualified_artifact_identities,
+)
+from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.mcp import query_helpers
 from contextor.mcp import runtime as mcp_runtime
 from contextor.mcp.tools.search_artifacts import search_artifacts
@@ -12,6 +26,47 @@ from contextor.mcp.tools.get_file_edit_context import get_file_edit_context
 from contextor.mcp.tools.update_file import update_file, _semantic_diff_view
 
 
+def _build_compact_local_engine(tmp_path, monkeypatch, source):
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    provider = repo / "provider.py"
+    provider.write_text(source, encoding="utf-8")
+    index = index_repository(str(repo))
+    modules = index.modules
+    reexport_facts_by_module = materialize_reexport_facts_by_module(
+        modules,
+        index.reference_facts_by_module,
+    )
+    artifacts, failures = collect_module_artifacts(modules, str(repo))
+    assert not failures
+    trie = build_trie(modules)
+    package_root = detect_package_root(modules, trie)
+    state = RepositoryAnalysisState(
+        modules=dict(modules),
+        reexport_facts_by_module=reexport_facts_by_module,
+        artifacts=artifacts,
+        dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
+        trie=trie,
+        package_root=package_root,
+        artifact_consumption={},
+    )
+    registry = PersistentIdentityRegistry(str(repo))
+    with registry.transaction():
+        registry.sync_with_workspace(
+            set(modules), collect_qualified_artifact_identities(artifacts)
+        )
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    cache_dir = repo_cache_dir(repo)
+    state_manager = FileStateManager(str(cache_dir))
+    state_manager.update_state(str(provider))
+    engine = IncrementalAnalysisEngine(state, registry, state_manager, str(repo))
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {str(repo.resolve()): engine})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
+    return repo, provider, engine
+
+
 def _setup_mock_search_and_lookup_engine(monkeypatch):
     class Registry:
         def get_module_id(self, module):
@@ -413,64 +468,106 @@ def test_compact_evidence_contract__file_edit_context_collections_include_eviden
 
 
 def test_compact_evidence_contract__update_file_collections_include_evidence(tmp_path, monkeypatch):
-    update_calls = []
-
-    class UpdateRes:
-        status = "UPDATED"
-        file_path = str(tmp_path / "pkg" / "a.py")
-        graph_state = "fresh"
-        dependencies_state = "fresh"
-        blast_radius_state = "fresh"
-        local_metrics_state = "fresh"
-        global_metrics_state = "fresh"
-        artifact_consumption_state = "fresh"
-        affected_modules = ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"]
-        delta = None
+    repo, provider, original_engine = _build_compact_local_engine(
+        tmp_path,
+        monkeypatch,
+        "def original():\n    return 1\n",
+    )
+    update_file_module = importlib.import_module("contextor.mcp.tools.update_file")
+    assert update_file_module._persist_live_engine(repo, original_engine) is True
+
+    provider.write_text(
+        "def original():\n"
+        "    return 1\n"
+        "\n"
+        "def s1():\n"
+        "    return 1\n"
+        "\n"
+        "def s2():\n"
+        "    return 2\n"
+        "\n"
+        "def s3():\n"
+        "    return 3\n"
+        "\n"
+        "def s4():\n"
+        "    return 4\n",
+        encoding="utf-8",
+    )
 
-    class Engine:
-        state = type("State", (), {"artifacts": {}})()
-        def update_file(self, path):
-            update_calls.append(path)
-            return UpdateRes()
+    real_update_file = IncrementalAnalysisEngine.update_file
+    update_calls = []
 
-    engine = Engine()
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda root: engine)
-    monkeypatch.setattr("contextor.core.live_state.connect", lambda root: None)
-    monkeypatch.setattr("contextor.mcp.tools.update_file._persist_live_engine", lambda root, eng: True)
-    monkeypatch.setattr("contextor.mcp.tools.update_file._semantic_artifact_diff", lambda old, new: {
-        "changed_symbol_count": 4,
-        "body_change_count": 0,
-        "body_only_changes_tracked": False,
-        "symbols_added": ["s1", "s2", "s3", "s4"],
-        "symbols_removed": [],
-        "signatures_changed": {},
-        "bodies_changed": [],
-        "affected_symbols": ["s1", "s2", "s3", "s4"],
-    })
+    def observed_real_update(self, path):
+        update_calls.append((self, path))
+
+        result = real_update_file(self, path)
+        assert result.status == "UPDATED"
+
+        return SimpleNamespace(
+            status=result.status,
+            file_path=result.file_path,
+            graph_state=result.graph_state,
+            dependencies_state=result.dependencies_state,
+            blast_radius_state=result.blast_radius_state,
+            local_metrics_state=result.local_metrics_state,
+            global_metrics_state=result.global_metrics_state,
+            artifact_consumption_state=result.artifact_consumption_state,
+            affected_modules=[
+                "pkg.m1",
+                "pkg.m2",
+                "pkg.m3",
+                "pkg.m4",
+            ],
+            delta=result.delta,
+        )
 
-    file_path = tmp_path / "pkg" / "a.py"
-    file_path.parent.mkdir(parents=True, exist_ok=True)
-    file_path.write_text("x = 1\n", encoding="utf-8")
+    monkeypatch.setattr(
+        IncrementalAnalysisEngine,
+        "update_file",
+        observed_real_update,
+    )
 
-    raw = update_file(str(tmp_path), file_path="pkg/a.py", compact=True)
+    raw = update_file_module.update_file(
+        str(repo),
+        file_path=str(provider),
+        compact=True,
+    )
     res = json.loads(raw)
 
-    assert len(update_calls) == 1, "update_file MUST NOT perform extra analysis/update calls"
+    assert res["status"] == "UPDATED"
+    assert res["live_state_persisted"] is True
+    assert len(update_calls) == 1
+    assert update_calls[0][0] is not original_engine
+    current_engine = mcp_runtime._live_engines[str(repo.resolve())]
+    assert current_engine is not original_engine
+    assert current_engine is update_calls[0][0]
+    metadata = read_metadata(repo_cache_dir(repo))
+    assert metadata is not None
+    assert current_engine.revision == metadata.revision
+    assert current_engine.state.revision == metadata.revision
+    assert current_engine.state.state_id == metadata.state_id
+    assert current_engine.state_manager.revision == metadata.revision
+    assert current_engine.state_manager.state_id == metadata.state_id
+    assert mcp_runtime._live_engine_revisions[str(repo.resolve())] == metadata.revision
 
     aff = res["affected_modules"]
-    assert "evidence" in aff
     assert aff["total"] == 4
-    assert len(aff["evidence"]) == 3
+    assert aff["evidence"] == ["pkg.m1", "pkg.m2", "pkg.m3"]
     assert aff["truncated"] is True
     assert "expand" not in aff
 
-    diff = res["semantic_diff"]
-    sym_added = diff["symbols_added"]
-    assert "evidence" in sym_added
+    sym_added = res["semantic_diff"]["symbols_added"]
     assert sym_added["total"] == 4
-    assert len(sym_added["evidence"]) == 3
+    assert sym_added["evidence"] == ["s1", "s2", "s3"]
     assert sym_added["truncated"] is True
     assert "expand" not in sym_added
+    original_functions = set(
+        original_engine.state.artifacts["provider"]["symbols"]["functions"]
+    )
+    current_functions = set(
+        current_engine.state.artifacts["provider"]["symbols"]["functions"]
+    )
+    assert current_functions - original_functions == {"s1", "s2", "s3", "s4"}
 
 
 def test_compact_evidence_contract__update_file_compact_does_not_advertise_mutating_expand():
```

## FINAL_VERDICT
L32H2J2_17_ORIGINAL_REGRESSIONS_PASS
