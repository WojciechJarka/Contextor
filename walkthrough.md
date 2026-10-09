# L32C_CACHED_ANALYTICS_PREREQUISITE_TRUST_GATE

## CURRENT_HEAD

`8927890c31676c34d3187931cc46785a8ecb748e` (user-specified verified starting HEAD). Contextor MCP first: retrieved complete `ensure_cached_analytics`, `dependency_matrix_inputs_are_fresh`, and `materialize_incremental_state`; all source lookups reported `workspace_sync=verified`, canonical LIVE revision 133. Blast-radius lookup confirms runtime consumers in the incremental engine and hydration chain. Git confirmed the exact anchor before edits. No full analysis, actual-repository update_file, or service restart.

## FILES_CHANGED

- `contextor/core/analysis/incremental/materialization.py`
- `tests/test_cached_facts_live_analytics.py`

## PRE_FIX_RED_RESULTS

Added negative and isolated durable repro tests before production change. Exact new regression command:

```text
python -m pytest -q tests/test_cached_facts_live_analytics.py -k 'requires_trusted_artifact or untrusted_artifact_consumption_invalidates or isolated_snapshot_hydration_does_not_publish'
8 failed, 15 deselected, 1 external Authlib warning
```

All eight failures were expected: UNKNOWN, stale, None, list and dict artifact-consumption markers, pre-populated fresh cache invalidation, and both persisted/hydrated cases (UNKNOWN and stale) incorrectly ended with `cached_analytics_state='fresh'`.

## ARTIFACT_PREREQUISITE_MATRIX

| Prerequisite state | Cache before materialization | Result |
|---|---|---|
| Valid fresh artifact consumption + valid graph | Empty/deferred | Successful RAM compute may yield fresh |
| Valid fresh artifact consumption + valid graph | Fresh/populated | Preserved; no unnecessary recompute |
| artifact state UNKNOWN, stale, None, list or dict | Empty/deferred | stale; no computation |
| artifact state UNKNOWN/stale/invalid | Fresh/populated | stale; payload retained but untrusted |
| artifact state deferred | Fresh/populated | deferred; payload retained |
| artifact state deferred | Previously stale/populated | stale preserved |
| resync_required=True | Any cache | stale |
| Missing/invalid graph | Empty/deferred | stale; no computation |

Production guard calls existing `dependency_matrix_inputs_are_fresh`, which requires no resync, genuinely fresh/validated artifact-consumption coverage, and a graph with dict `hard_edges` (`state_manager.py:686-707`). The existing analytics algorithm is unchanged.

## OLD_FRESH_CACHE_INVALIDATION

New direct regression sets cache state fresh with a populated visibility payload and stale artifact consumption. Result: marker becomes stale and payload remains byte-for-byte/value-equal. Direct negative matrix also checks UNKNOWN, stale, None, list and dict with structurally valid canonical map and nonempty module domain; all become stale and leave empty cache empty.

## ISOLATED_SNAPSHOT_REPRODUCTION

Temporary repository contains real `contextor/core/analysis/mod.py` defining `foo` and `contextor/ui/consumer.py` defining `VALUE`. Real incremental updates establish modules/artifacts/graph and initially classify the definer visibility as private. A separate deep-copied state retains exact canonical target-key coverage, replaces only `mod::foo` consumer facts with the structurally valid obsolete `contextor.ui.consumer` / `api_imports` entry, and uses UNKNOWN or stale artifact marker, deferred cached marker, empty cache, resync false.

Real `save_snapshot` writes revision 1 with repository identity and matching FileState generation. Real `load_snapshot` preserves selected marker, entry and revision. Real `IncrementalAnalysisEngine` initialization now results in stale cached analytics, retains no computed cache, and isolated in-process `get_module_context` does not expose public visibility. Before patch both parameter cases failed because hydration produced fresh cache and the public path could consume the obsolete consumer-derived visibility. Only tmp_path state was mutated; actual LIVE state was untouched.

## POST_HYDRATION_RESULT

Both isolated roundtrips pass for artifact marker UNKNOWN and stale. The prerequisite guard invalidates freshness before recompute and preserves the empty cache. FileState state_id/revision are asserted equal to the committed snapshot metadata.

## PUBLIC_VISIBILITY_RESULT

For both persisted failure cases, the isolated module-context response contains no `visibility='public'` certification from the obsolete consumer entry. The sentinel is not computed into cached analytics. This is test-based local MCP projection evidence, not a live malformed-state request.

## LEGACY_MIGRATION_RESULT

Changed only `_CachedAnalyticsLegacySnapshotState.artifact_consumption` from empty dict to recognized `{"_report": {}}`. The existing `test_snapshot_lifecycle_and_consumer_projection` now asserts migrated `artifact_consumption_state='fresh'` before accepting cached analytics fresh; its source-free reconstruction and public projection assertions still pass. No legacy exemption was added to the production trust gate.

## VALID_INPUT_PARITY

Positive control asserts deferred empty-cache computation with fresh artifact map and graph equals the `compute_cached_analytics` RAM oracle. Existing fresh populated data remains preserved; stale data remains stale. New controls verify resync and missing graph fail closed, deferred prerequisites downgrade fresh to deferred and preserve stale, and unrelated topology/cycle markers remain unchanged.

## TARGETED_TEST_RESULTS

After production patch and fixture correction, exact relevant subset: **13 passed, 10 deselected, 1 external Authlib warning**. Entire `tests/test_cached_facts_live_analytics.py`: **27 passed, 1 external Authlib warning**. Required five-file gate:

```text
tests/test_cached_facts_live_analytics.py
tests/test_matrix_clusters_state_lifecycle.py
tests/test_graph_only_live_analytics.py
tests/test_mcp_incremental_hydration.py
tests/test_freshness_preservation.py
97 passed, 1 external Authlib warning, 48.17 seconds
```

`git diff --check` passed. No full repository suite.

## REMAINING_GAPS

No remaining gap in the requested trust-gate contract was identified in the focused paths. The gate intentionally relies on the existing dependency-matrix prerequisite predicate; unsupported malformed structures outside that predicate's documented graph/artifact coverage are not certified by this test scope.

## MCP_RESTART_REQUIRED

**YES.** The changed core runtime module requires a manual MCP backend restart before runtime certification. No restart was performed.

## FINAL_VERDICT

**FOCUSED_IMPLEMENTATION_PASS.** Exact auditor-designed prerequisite gate, isolated durable repro, legacy migration contract, positive oracle and required targeted regressions pass.

## FULL_DIFFS

```diff
diff --git a/contextor/core/analysis/incremental/materialization.py b/contextor/core/analysis/incremental/materialization.py
index 07eeaaa..a3c8a01 100644
--- a/contextor/core/analysis/incremental/materialization.py
+++ b/contextor/core/analysis/incremental/materialization.py
@@ -172,6 +172,21 @@ def ensure_cached_analytics(state: RepositoryAnalysisState) -> None:
     if not hasattr(state, "cached_analytics") or state.cached_analytics is None:
         state.cached_analytics = {}
 
+    from contextor.core.analysis.state_manager import (
+        dependency_matrix_inputs_are_fresh,
+    )
+
+    if not dependency_matrix_inputs_are_fresh(state):
+        if (
+            not getattr(state, "resync_required", False)
+            and getattr(state, "artifact_consumption_state", None) == "deferred"
+        ):
+            if state.cached_analytics_state != "stale":
+                state.cached_analytics_state = "deferred"
+        else:
+            state.cached_analytics_state = "stale"
+        return
+
     if (
         state.cached_analytics_state != "stale"
         and not state.cached_analytics
diff --git a/tests/test_cached_facts_live_analytics.py b/tests/test_cached_facts_live_analytics.py
index e54ee94..938b93b 100644
--- a/tests/test_cached_facts_live_analytics.py
+++ b/tests/test_cached_facts_live_analytics.py
@@ -9,6 +9,7 @@ and zero-call execution minimality for pure implementation-body changes.
 """
 
 from pathlib import Path
+from copy import deepcopy
 from unittest.mock import patch, MagicMock
 import json
 import time
@@ -22,6 +23,9 @@ from contextor.core.analysis.incremental.materialization import ensure_cached_an
 from contextor.core.analysis.state_manager import (
     RepositoryAnalysisState,
     FileStateManager,
+    canonical_artifact_consumption_targets,
+    validate_canonical_artifact_consumption,
+    validate_canonical_artifact_consumption_coverage,
 )
 from contextor.core.domain.graph import ProjectGraph
 from contextor.core.domain.module import Module
@@ -38,6 +42,7 @@ from contextor.core.reporting_engine.graph_analytics import (
 )
 from contextor.core.validator.layers import validate_layer_rules
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.repository_identity import ensure_repository_identity
 from contextor.mcp_server import get_module_context
 from contextor.mcp.runtime import _live_engines
 
@@ -298,7 +303,7 @@ class _CachedAnalyticsLegacySnapshotState:
         self.dependency_graph = graph
         self.metrics = metrics
         self.artifacts = {"contextor.core.analysis.mod": {"own_symbols": ["foo"]}}
-        self.artifact_consumption = {}
+        self.artifact_consumption = {"_report": {}}
 
 
 def test_snapshot_lifecycle_and_consumer_projection(tmp_path):
@@ -331,6 +336,7 @@ def test_snapshot_lifecycle_and_consumer_projection(tmp_path):
         )
 
     # Reconstructed to fresh with zero disk reads
+    assert engine.state.artifact_consumption_state == "fresh"
     assert engine.state.cached_analytics_state == "fresh"
     assert "contextor.core.analysis.mod" in engine.state.cached_analytics["module_layers"]
     assert engine.state.cached_analytics["export_degree"]["contextor.core.analysis.mod"] == 1
@@ -378,8 +384,17 @@ def test_none_cached_marker_preserves_obsolete_payload_without_certifying_it():
 
 
 def test_missing_cached_marker_with_populated_legacy_cache_is_not_fresh():
-    state = _CachedAnalyticsLegacySnapshotState({}, ProjectGraph({}, {}), {})
+    module_name = "contextor.core.analysis.mod"
+    state = _CachedAnalyticsLegacySnapshotState(
+        {module_name: Module(module_name, "mod.py", "/tmp/mod.py", [])},
+        ProjectGraph({module_name: set()}, {module_name: set()}),
+        {},
+    )
     state.cached_analytics = {"module_layers": {"legacy.mod": "obsolete_layer"}}
+    state.artifact_consumption = {
+        f"{module_name}::foo": {"consumers": [], "channels": {}}
+    }
+    state.artifact_consumption_state = "fresh"
     assert not hasattr(state, "cached_analytics_state")
 
     ensure_cached_analytics(state)
@@ -477,6 +492,11 @@ def test_cached_marker_positive_lifecycle_preserves_other_families():
     for marker in ("fresh", "stale"):
         state = RepositoryAnalysisState(
             modules={module_name: module},
+            artifacts={module_name: {"own_symbols": ["foo"]}},
+            artifact_consumption={
+                f"{module_name}::foo": {"consumers": [], "channels": {}}
+            },
+            artifact_consumption_state="fresh",
             dependency_graph=graph,
             cached_analytics_state=marker,
             cached_analytics=sentinel.copy(),
@@ -491,6 +511,11 @@ def test_cached_marker_positive_lifecycle_preserves_other_families():
 
     deferred = RepositoryAnalysisState(
         modules={module_name: module},
+        artifacts={module_name: {"own_symbols": ["foo"]}},
+        artifact_consumption={
+            f"{module_name}::foo": {"consumers": [], "channels": {}}
+        },
+        artifact_consumption_state="fresh",
         dependency_graph=graph,
         cached_analytics_state="deferred",
         cached_analytics={},
@@ -498,12 +523,205 @@ def test_cached_marker_positive_lifecycle_preserves_other_families():
         cycles_state="stale",
     )
     ensure_cached_analytics(deferred)
+    oracle = compute_cached_analytics(
+        modules=deferred.modules,
+        artifacts=deferred.artifacts,
+        artifact_consumption=deferred.artifact_consumption,
+        hard_edges=deferred.dependency_graph.hard_edges,
+    )
     assert deferred.cached_analytics_state == "fresh"
-    assert deferred.cached_analytics["module_layers"][module_name] == "runtime"
+    assert deferred.cached_analytics == oracle
     assert deferred.topology_metrics_state == "stale"
     assert deferred.cycles_state == "stale"
 
 
+@pytest.mark.parametrize("missing_graph", [False, True], ids=["resync", "missing_graph"])
+def test_cached_analytics_requires_valid_graph_and_no_resync(missing_graph):
+    module_name = "contextor.core.analysis.mod"
+    graph = None if missing_graph else ProjectGraph({module_name: set()}, {module_name: set()})
+    state = RepositoryAnalysisState(
+        modules={module_name: Module(module_name, "mod.py", "/tmp/mod.py", [])},
+        artifacts={module_name: {"own_symbols": ["foo"]}},
+        artifact_consumption={
+            f"{module_name}::foo": {"consumers": [], "channels": {}}
+        },
+        artifact_consumption_state="fresh",
+        dependency_graph=graph,
+        cached_analytics_state="deferred",
+        cached_analytics={},
+    )
+    state.resync_required = not missing_graph
+
+    ensure_cached_analytics(state)
+
+    assert state.cached_analytics_state == "stale"
+    assert state.cached_analytics == {}
+
+
+@pytest.mark.parametrize(
+    ("cached_state", "expected_state"),
+    [("fresh", "deferred"), ("stale", "stale")],
+)
+def test_deferred_artifact_prerequisite_degrades_only_fresh_cache(cached_state, expected_state):
+    module_name = "contextor.core.analysis.mod"
+    payload = {"visibility": {module_name: "public"}}
+    state = RepositoryAnalysisState(
+        modules={module_name: Module(module_name, "mod.py", "/tmp/mod.py", [])},
+        artifacts={module_name: {"own_symbols": ["foo"]}},
+        artifact_consumption={
+            f"{module_name}::foo": {"consumers": [], "channels": {}}
+        },
+        artifact_consumption_state="deferred",
+        dependency_graph=ProjectGraph({module_name: set()}, {module_name: set()}),
+        cached_analytics_state=cached_state,
+        cached_analytics=deepcopy(payload),
+    )
+
+    ensure_cached_analytics(state)
+
+    assert state.cached_analytics_state == expected_state
+    assert state.cached_analytics == payload
+
+
+@pytest.mark.parametrize("artifact_state", ["UNKNOWN", "stale", None, [], {}], ids=repr)
+def test_cached_analytics_requires_trusted_artifact_consumption(artifact_state):
+    module_name = "contextor.core.analysis.mod"
+    target = f"{module_name}::foo"
+    state = RepositoryAnalysisState(
+        modules={
+            module_name: Module(
+                module_name,
+                "contextor/core/analysis/mod.py",
+                "/tmp/mod.py",
+                [],
+            )
+        },
+        artifacts={module_name: {"own_symbols": ["foo"]}},
+        artifact_consumption={target: {"consumers": [], "channels": {}}},
+        artifact_consumption_state=artifact_state,
+        dependency_graph=ProjectGraph({module_name: set()}, {module_name: set()}),
+        cached_analytics_state="deferred",
+        cached_analytics={},
+    )
+    assert validate_canonical_artifact_consumption(state.artifact_consumption)
+    assert validate_canonical_artifact_consumption_coverage(
+        state.artifact_consumption,
+        state.artifacts,
+    )
+    assert set(state.artifact_consumption) == canonical_artifact_consumption_targets(
+        state.artifacts
+    )
+
+    ensure_cached_analytics(state)
+
+    assert state.cached_analytics_state == "stale"
+    assert state.cached_analytics == {}
+
+
+def test_untrusted_artifact_consumption_invalidates_existing_fresh_cached_payload():
+    module_name = "contextor.core.analysis.mod"
+    cached = {"visibility": {module_name: "public"}, "sentinel": "retain"}
+    state = RepositoryAnalysisState(
+        modules={module_name: Module(module_name, "mod.py", "/tmp/mod.py", [])},
+        artifact_consumption_state="stale",
+        dependency_graph=ProjectGraph({module_name: set()}, {module_name: set()}),
+        cached_analytics_state="fresh",
+        cached_analytics=deepcopy(cached),
+    )
+
+    ensure_cached_analytics(state)
+
+    assert state.cached_analytics_state == "stale"
+    assert state.cached_analytics == cached
+
+
+@pytest.mark.parametrize("artifact_state", ["UNKNOWN", "stale"])
+def test_isolated_snapshot_hydration_does_not_publish_visibility_from_untrusted_consumers(
+    tmp_path,
+    artifact_state,
+):
+    repo = tmp_path / "repo"
+    mod_file = repo / "contextor" / "core" / "analysis" / "mod.py"
+    consumer_file = repo / "contextor" / "ui" / "consumer.py"
+    mod_file.parent.mkdir(parents=True)
+    consumer_file.parent.mkdir(parents=True)
+    mod_file.write_text("def foo():\n    return 1\n", encoding="utf-8")
+    consumer_file.write_text("VALUE = 2\n", encoding="utf-8")
+
+    identity = ensure_repository_identity(repo)[0]
+    cache_dir = tmp_path / "cache"
+    state_manager = FileStateManager(str(cache_dir))
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(modules={}),
+        PersistentIdentityRegistry(str(repo)),
+        state_manager,
+        str(repo),
+    )
+    assert engine.update_file(str(mod_file)).status == "UPDATED"
+    assert engine.update_file(str(consumer_file)).status == "UPDATED"
+    definer = "contextor.core.analysis.mod"
+    consumer = "contextor.ui.consumer"
+    target = f"{definer}::foo"
+    assert engine.state.cached_analytics["visibility"][definer] == "private"
+
+    candidate = deepcopy(engine.state)
+    assert set(candidate.artifact_consumption) == canonical_artifact_consumption_targets(
+        candidate.artifacts
+    )
+    candidate.artifact_consumption[target] = {
+        "consumers": [consumer],
+        "channels": {consumer: ["api_imports"]},
+    }
+    candidate.artifact_consumption_state = artifact_state
+    candidate.cached_analytics_state = "deferred"
+    candidate.cached_analytics = {}
+    candidate.resync_required = False
+    assert validate_canonical_artifact_consumption(candidate.artifact_consumption)
+    assert validate_canonical_artifact_consumption_coverage(
+        candidate.artifact_consumption,
+        candidate.artifacts,
+    )
+    assert target in candidate.artifact_consumption
+    assert candidate.artifact_consumption[target]["channels"][consumer] == ["api_imports"]
+
+    state_id = "l32c-prerequisite-trust"
+    metadata = save_snapshot(
+        candidate,
+        cache_dir,
+        state_id,
+        repo_id=identity.repo_id,
+        root_path=identity.root_path,
+        exact_revision=1,
+        file_state_payload=state_manager.build_payload(state_id, 1),
+    )
+    loaded = load_snapshot(
+        cache_dir,
+        expected_state_id=state_id,
+        expected_repo_id=identity.repo_id,
+        expected_root_path=identity.root_path,
+    )
+    assert loaded is not None
+    loaded_state, loaded_metadata = loaded
+    assert loaded_metadata.revision == metadata.revision == 1
+    assert loaded_state.artifact_consumption_state == artifact_state
+    hydrated_files = FileStateManager(str(cache_dir))
+    assert hydrated_files.revision == loaded_metadata.revision
+    assert hydrated_files.state_id == loaded_metadata.state_id
+    hydrated = IncrementalAnalysisEngine(
+        loaded_state,
+        PersistentIdentityRegistry(str(repo)),
+        hydrated_files,
+        str(repo),
+    )
+
+    assert hydrated.state.cached_analytics_state == "stale"
+    assert hydrated.state.cached_analytics == {}
+    fn = getattr(get_module_context, "fn", get_module_context)
+    with patch.dict(_live_engines, {str(repo.resolve()): hydrated}):
+        projected = json.loads(fn(str(repo), definer, compact=True))
+    assert projected["metrics"].get("visibility") != "public"
+
+
 def test_atomicity_and_isolation_on_failure(tmp_path):
     """6. Failure during cached analytics computation does not corrupt published state."""
     models_py, service_py, _, _ = _setup_multi_layer_repo(tmp_path)
```
