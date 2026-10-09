# L32B_CACHED_ANALYTICS_FALSE_FRESH_FIX

## CURRENT_HEAD

`fe097fff93cb4b4b2149913dcd2560606f8144d3`. Contextor MCP first: complete `ensure_cached_analytics` implementation at `contextor/core/analysis/incremental/materialization.py:164-195`, `workspace_sync=verified`, LIVE revision 130; symbol lineage and blast radius found direct runtime consumers in incremental engine. Git confirmed the exact literal anchor. No active LIVE state, cache or snapshot was modified.

## PRE_FIX_RED_RESULTS

After adding the focused tests and before editing production, the exact new subset ran with `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cached_facts_live_analytics.py -k 'none_cached_marker or missing_cached_marker or explicit_none_cached_marker or cached_marker_positive_lifecycle' --tb=short`: **3 failed, 1 passed, 11 deselected, 1 external Authlib warning**. The three failures each showed `fresh` where `deferred` was required. The isolated snapshot case passed real save/load preconditions and failed at post-hydration false-fresh promotion. An earlier test-authoring run had one unrelated test-fixture constructor error; it was corrected before the recorded red gate.

## FILES_CHANGED

- `contextor/core/analysis/incremental/materialization.py`
- `tests/test_cached_facts_live_analytics.py`

## CACHED_ANALYTICS_MARKER_MATRIX

| Marker/payload | Result after fix |
|---|---|
| None + nonempty obsolete payload | deferred; payload retained, untrusted |
| genuinely missing legacy marker + nonempty payload | deferred; payload retained, untrusted |
| None/missing + empty payload + valid modules | normal RAM computation may produce fresh |
| fresh + populated payload | fresh preserved, no forced recomputation |
| stale + populated payload | stale preserved, no auto-promotion |
| deferred + empty payload + valid modules | computed fresh from canonical RAM inputs |

The production change is exactly the specified replacement: None/missing state becomes `deferred`; the existing compute branch and all other families remain unchanged.

## SNAPSHOT_LOAD_RESULT

The new isolated test builds canonical state by updating a Python file only inside `tmp_path`, then saves a valid first generation with repository ID/root and FileState payload at revision 1. It loads that generation and confirms the cache is fresh. It sets only the loaded test state's cached marker to None and injects `module_layers[contextor.core.analysis.mod]=obsolete_layer`, saves revision 2 with matching repository identity and FileState revision, and reloads it. Real `load_snapshot` retains explicit None and the obsolete sentinel; metadata and FileState revisions match 2.

## POST_HYDRATION_RESULT

Real `IncrementalAnalysisEngine` initialization with the loaded state and revision-matched `FileStateManager` now yields `cached_analytics_state=deferred`. The sentinel payload remains present but untrusted. Before the fix, this exact assertion failed because hydration set `fresh`.

## PUBLIC_PROJECTION_RESULT

An isolated in-process `get_module_context` projection bound to the hydrated test engine does not return `obsolete_layer` in `metrics.layer`. The pre-fix red test reached and failed the marker assertion before this projection; the after-fix test proves the public sentinel guard. The active MCP backend was not restarted or mutated, so its current runtime is not certified for this change.

## LEGACY_COMPATIBILITY_RESULT

Existing `test_snapshot_lifecycle_and_consumer_projection` remains passing: a genuinely missing legacy cache is reconstructed from canonical RAM inputs and becomes fresh. New separate missing-marker + populated-cache test proves such payload alone no longer certifies freshness. Positive tests confirm existing fresh/stale behavior, successful deferred recomputation, and unchanged topology/cycle markers.

## TARGETED_TEST_RESULTS

Post-fix exact new subset: **4 passed, 11 deselected, 1 external Authlib warning**. Required focused gate `tests/test_cached_facts_live_analytics.py tests/test_graph_only_live_analytics.py tests/test_freshness_preservation.py tests/test_mcp_incremental_hydration.py`: **31 passed, 1 external Authlib warning**. `git diff --check` found no whitespace errors. No full suite.

## REGRESSION_FAILURES

None in the required focused gate.

## RUNTIME_RESTART_REQUIREMENT

**Manual MCP backend restart required** before runtime certification of changed core module. No automatic restart occurred.

## FINAL_VERDICT

**FOCUSED_FIX_PASS**: exact production patch, red/green proof, valid isolated snapshot and FileState contract, public projection guard, legacy and positive lifecycle, and focused regression gate completed. Active MCP runtime certification remains pending manual restart.

## FULL_DIFFS

```diff
diff --git a/contextor/core/analysis/incremental/materialization.py b/contextor/core/analysis/incremental/materialization.py
index 5a72dff..07eeaaa 100644
--- a/contextor/core/analysis/incremental/materialization.py
+++ b/contextor/core/analysis/incremental/materialization.py
@@ -167,9 +167,7 @@ def ensure_cached_analytics(state: RepositoryAnalysisState) -> None:
     RAM ONLY — ZERO source I/O.
     """
     if not hasattr(state, "cached_analytics_state") or state.cached_analytics_state is None:
-        state.cached_analytics_state = (
-            "fresh" if bool(getattr(state, "cached_analytics", None)) else "deferred"
-        )
+        state.cached_analytics_state = "deferred"
 
     if not hasattr(state, "cached_analytics") or state.cached_analytics is None:
         state.cached_analytics = {}
diff --git a/tests/test_cached_facts_live_analytics.py b/tests/test_cached_facts_live_analytics.py
index b4d1226..e54ee94 100644
--- a/tests/test_cached_facts_live_analytics.py
+++ b/tests/test_cached_facts_live_analytics.py
@@ -18,6 +18,7 @@ from contextor.core.analysis.incremental_engine import (
     IncrementalAnalysisEngine,
     IncrementalUpdateResult,
 )
+from contextor.core.analysis.incremental.materialization import ensure_cached_analytics
 from contextor.core.analysis.state_manager import (
     RepositoryAnalysisState,
     FileStateManager,
@@ -361,6 +362,148 @@ def test_snapshot_lifecycle_and_consumer_projection(tmp_path):
     assert engine_stale.state.cached_analytics_state == "stale"
 
 
+def test_none_cached_marker_preserves_obsolete_payload_without_certifying_it():
+    obsolete = {"module_layers": {"contextor.core.analysis.mod": "obsolete_layer"}}
+    state = RepositoryAnalysisState(
+        modules={},
+        cached_analytics_state=None,
+        cached_analytics=obsolete,
+    )
+
+    ensure_cached_analytics(state)
+
+    assert state.cached_analytics_state == "deferred"
+    assert state.cached_analytics is obsolete
+    assert state.cached_analytics["module_layers"]["contextor.core.analysis.mod"] == "obsolete_layer"
+
+
+def test_missing_cached_marker_with_populated_legacy_cache_is_not_fresh():
+    state = _CachedAnalyticsLegacySnapshotState({}, ProjectGraph({}, {}), {})
+    state.cached_analytics = {"module_layers": {"legacy.mod": "obsolete_layer"}}
+    assert not hasattr(state, "cached_analytics_state")
+
+    ensure_cached_analytics(state)
+
+    assert state.cached_analytics_state == "deferred"
+    assert state.cached_analytics["module_layers"]["legacy.mod"] == "obsolete_layer"
+
+
+def test_explicit_none_cached_marker_snapshot_hydration_and_public_projection(tmp_path):
+    repo = tmp_path / "repo"
+    module_file = repo / "contextor" / "core" / "analysis" / "mod.py"
+    module_file.parent.mkdir(parents=True)
+    module_file.write_text("def foo():\n    return 1\n", encoding="utf-8")
+    cache_dir = tmp_path / "cache"
+    state_manager = FileStateManager(str(cache_dir))
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(modules={}),
+        PersistentIdentityRegistry(str(repo)),
+        state_manager,
+        str(repo),
+    )
+    assert engine.update_file(str(module_file)).status == "UPDATED"
+    module_name = "contextor.core.analysis.mod"
+    assert engine.state.cached_analytics_state == "fresh"
+    assert module_name in engine.state.cached_analytics["module_layers"]
+
+    base = save_snapshot(
+        engine.state,
+        cache_dir,
+        "cached-analytics-test",
+        repo_id="isolated-cached-analytics",
+        root_path=str(repo),
+        exact_revision=1,
+        file_state_payload=state_manager.build_payload("cached-analytics-test", 1),
+    )
+    assert base.revision == 1
+    committed = load_snapshot(
+        cache_dir,
+        expected_state_id="cached-analytics-test",
+        expected_repo_id="isolated-cached-analytics",
+        expected_root_path=str(repo),
+    )
+    assert committed is not None
+    isolated_state, metadata = committed
+    assert metadata.revision == 1
+    assert isolated_state.cached_analytics_state == "fresh"
+
+    isolated_state.cached_analytics_state = None
+    isolated_state.cached_analytics["module_layers"][module_name] = "obsolete_layer"
+    next_revision = metadata.revision + 1
+    saved = save_snapshot(
+        isolated_state,
+        cache_dir,
+        metadata.state_id,
+        repo_id=metadata.repo_id,
+        root_path=metadata.root_path,
+        exact_revision=next_revision,
+        file_state_payload=state_manager.build_payload(metadata.state_id, next_revision),
+    )
+    assert saved.revision == next_revision
+    loaded = load_snapshot(
+        cache_dir,
+        expected_state_id=metadata.state_id,
+        expected_repo_id=metadata.repo_id,
+        expected_root_path=metadata.root_path,
+    )
+    assert loaded is not None
+    loaded_state, loaded_metadata = loaded
+    assert loaded_metadata.revision == next_revision
+    assert loaded_state.cached_analytics_state is None
+    assert loaded_state.cached_analytics["module_layers"][module_name] == "obsolete_layer"
+
+    hydrated_file_state = FileStateManager(str(cache_dir))
+    assert hydrated_file_state.revision == loaded_metadata.revision
+    assert hydrated_file_state.state_id == loaded_metadata.state_id
+    hydrated = IncrementalAnalysisEngine(
+        loaded_state,
+        PersistentIdentityRegistry(str(repo)),
+        hydrated_file_state,
+        str(repo),
+    )
+    assert hydrated.state.cached_analytics_state == "deferred"
+    assert hydrated.state.cached_analytics["module_layers"][module_name] == "obsolete_layer"
+    fn = getattr(get_module_context, "fn", get_module_context)
+    with patch.dict(_live_engines, {str(repo.resolve()): hydrated}):
+        projected = json.loads(fn(str(repo), module_name, compact=True))
+    assert projected["metrics"].get("layer") != "obsolete_layer"
+
+
+def test_cached_marker_positive_lifecycle_preserves_other_families():
+    module_name = "contextor.core.analysis.mod"
+    module = Module(module_name, "contextor/core/analysis/mod.py", "/tmp/mod.py", [])
+    graph = ProjectGraph({module_name: set()}, {module_name: set()})
+    sentinel = {"module_layers": {module_name: "runtime"}}
+    for marker in ("fresh", "stale"):
+        state = RepositoryAnalysisState(
+            modules={module_name: module},
+            dependency_graph=graph,
+            cached_analytics_state=marker,
+            cached_analytics=sentinel.copy(),
+            topology_metrics_state="stale",
+            cycles_state="stale",
+        )
+        ensure_cached_analytics(state)
+        assert state.cached_analytics_state == marker
+        assert state.cached_analytics == sentinel
+        assert state.topology_metrics_state == "stale"
+        assert state.cycles_state == "stale"
+
+    deferred = RepositoryAnalysisState(
+        modules={module_name: module},
+        dependency_graph=graph,
+        cached_analytics_state="deferred",
+        cached_analytics={},
+        topology_metrics_state="stale",
+        cycles_state="stale",
+    )
+    ensure_cached_analytics(deferred)
+    assert deferred.cached_analytics_state == "fresh"
+    assert deferred.cached_analytics["module_layers"][module_name] == "runtime"
+    assert deferred.topology_metrics_state == "stale"
+    assert deferred.cycles_state == "stale"
+
+
 def test_atomicity_and_isolation_on_failure(tmp_path):
     """6. Failure during cached analytics computation does not corrupt published state."""
     models_py, service_py, _, _ = _setup_multi_layer_repo(tmp_path)
```
