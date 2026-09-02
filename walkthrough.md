# shared_usage_clusters P0 final audit evidence

## Complete raw unified diffs

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 32b5a41..2118f2f 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -386,6 +386,8 @@ class IncrementalAnalysisEngine:
         self.state.cached_analytics = candidate.cached_analytics
         self.state.dependency_matrix = candidate.dependency_matrix
         self.state.dependency_matrix_state = candidate.dependency_matrix_state
+        self.state.shared_usage_clusters = candidate.shared_usage_clusters
+        self.state.shared_usage_clusters_state = candidate.shared_usage_clusters_state
         self.state.topology_metrics_state = candidate.topology_metrics_state
         self.state.cached_analytics_state = candidate.cached_analytics_state
         self.state.cycles = candidate.cycles
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 81d4267..cc0f972 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -49,6 +49,8 @@ class CandidateState:
     topology_analytics: Dict[str, Any]
     dependency_matrix: Dict[str, Any]
     dependency_matrix_state: str
+    shared_usage_clusters: list
+    shared_usage_clusters_state: str
     cached_analytics: Dict[str, Any]
     topology_metrics_state: str
     cached_analytics_state: str
@@ -252,6 +254,14 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
             "dependency_matrix_state",
             "deferred",
         ),
+        shared_usage_clusters=list(
+            getattr(state, "shared_usage_clusters", []) or []
+        ),
+        shared_usage_clusters_state=getattr(
+            state,
+            "shared_usage_clusters_state",
+            "deferred",
+        ),
         cached_analytics=dict(getattr(state, "cached_analytics", {}) or {}),
         topology_metrics_state=getattr(state, "topology_metrics_state", "deferred"),
         cached_analytics_state=getattr(state, "cached_analytics_state", "deferred"),
@@ -294,6 +304,13 @@ def execute_refresh_plan(
         }
         & set(plan.patch_families)
     )
+    cluster_inputs_changed = bool(
+        {
+            "definitions",
+            "artifact_consumption",
+        }
+        & set(plan.patch_families)
+    )
     if getattr(state, "resync_required", False):
         candidate.artifact_consumption_state = "stale"
 
@@ -596,6 +613,30 @@ def execute_refresh_plan(
                 candidate.dependency_matrix = dependency_matrix
                 candidate.dependency_matrix_state = "fresh"
 
+    if plan.refresh_completeness == "requires_resync" or getattr(
+        state, "resync_required", False
+    ):
+        candidate.shared_usage_clusters_state = "stale"
+    elif cluster_inputs_changed:
+        from contextor.core.analysis.state_manager import (
+            artifact_consumption_is_fresh,
+        )
+
+        if not artifact_consumption_is_fresh(candidate):
+            candidate.shared_usage_clusters_state = "stale"
+        else:
+            from contextor.core.reporting_engine.graph_analytics import (
+                compute_shared_usage_clusters_from_state,
+            )
+
+            try:
+                clusters = compute_shared_usage_clusters_from_state(candidate)
+            except Exception:
+                candidate.shared_usage_clusters_state = "stale"
+            else:
+                candidate.shared_usage_clusters = clusters
+                candidate.shared_usage_clusters_state = "fresh"
+
     # 7. PREPARE registry payload if required
     all_modules = set(candidate.modules.keys())
     current_artifacts = collect_qualified_artifact_identities(candidate.artifacts) if identity_sync_required else {}
diff --git a/tests/test_matrix_clusters_state_lifecycle.py b/tests/test_matrix_clusters_state_lifecycle.py
index 16b6ac2..172deab 100644
--- a/tests/test_matrix_clusters_state_lifecycle.py
+++ b/tests/test_matrix_clusters_state_lifecycle.py
@@ -218,17 +218,76 @@ def test_incremental_matrix_compute_failure_marks_only_matrix_stale(tmp_path: Pa
     assert engine.state.dependency_matrix_state == "stale"
 
 
+def test_incremental_body_usage_change_refreshes_shared_usage_clusters(tmp_path: Path):
+    (tmp_path / "provider.py").write_text("def shared():\n    return 1\n", encoding="utf-8")
+    changed = tmp_path / "changed.py"
+    changed.write_text("from provider import shared\ndef use():\n    return shared()\n", encoding="utf-8")
+    (tmp_path / "other.py").write_text("from provider import shared\ndef other_use():\n    return shared()\n", encoding="utf-8")
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors
+    engine = _incremental_engine_from_full_state(tmp_path)
+    old_clusters = engine.state.shared_usage_clusters
+    changed.write_text("def use():\n    return 0\n", encoding="utf-8")
+    result = engine.update_file(str(changed))
+    assert result.status == "UPDATED"
+    assert "changed" not in engine.state.artifact_consumption["provider::shared"]["consumers"]
+    assert engine.state.shared_usage_clusters_state == "fresh"
+    assert engine.state.shared_usage_clusters == compute_shared_usage_clusters_from_state(engine.state)
+    assert engine.state.shared_usage_clusters != old_clusters
+
+
+def test_incremental_delete_refreshes_shared_usage_clusters(tmp_path: Path):
+    (tmp_path / "provider.py").write_text("def shared():\n    return 1\n", encoding="utf-8")
+    deleted = tmp_path / "deleted.py"
+    deleted.write_text("from provider import shared\ndef use():\n    return shared()\n", encoding="utf-8")
+    (tmp_path / "other.py").write_text("from provider import shared\ndef other_use():\n    return shared()\n", encoding="utf-8")
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors
+    engine = _incremental_engine_from_full_state(tmp_path)
+    old_clusters = engine.state.shared_usage_clusters
+    deleted.unlink()
+    result = engine.update_file(str(deleted))
+    assert result.status == "DELETED"
+    assert "deleted" not in engine.state.modules
+    assert engine.state.shared_usage_clusters_state == "fresh"
+    assert engine.state.shared_usage_clusters == compute_shared_usage_clusters_from_state(engine.state)
+    assert engine.state.shared_usage_clusters != old_clusters
+
+
+def test_incremental_cluster_compute_failure_marks_clusters_stale(tmp_path: Path):
+    target = tmp_path / "mod.py"
+    target.write_text("def one():\n    return 1\n", encoding="utf-8")
+    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
+    assert not errors
+    engine = _incremental_engine_from_full_state(tmp_path)
+    target.write_text("def two():\n    return 2\n", encoding="utf-8")
+    with unittest.mock.patch(
+        "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
+        side_effect=RuntimeError("clusters failure"),
+    ):
+        result = engine.update_file(str(target))
+    assert result.status == "UPDATED"
+    assert "mod" in engine.state.modules
+    assert engine.state.shared_usage_clusters_state == "stale"
+    assert engine.state.dependency_matrix_state == "fresh"
+
+
 def test_collision_only_plan_preserves_fresh_dependency_matrix():
     """Collision-only patch plans never recompute a fresh matrix."""
     state = _make_minimal_fresh_state()
     state.dependency_matrix = {"SENTINEL": {}}
     state.dependency_matrix_state = "fresh"
+    state.shared_usage_clusters = [{"SENTINEL": True}]
+    state.shared_usage_clusters_state = "fresh"
     plan = RefreshPlan(patch_families=("collision_facts", "collisions"))
     delta = FileDelta(module_path="mod_a")
 
     with unittest.mock.patch(
         "contextor.core.reporting_engine.graph_analytics.compute_dependency_matrix_from_state",
         side_effect=AssertionError("matrix must not be recomputed"),
+    ), unittest.mock.patch(
+        "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
+        side_effect=AssertionError("clusters must not be recomputed"),
     ):
         outcome = execute_refresh_plan(
             state, delta, None, plan, [], {}, None, Path("."), "mod_a.py", []
@@ -236,6 +295,8 @@ def test_collision_only_plan_preserves_fresh_dependency_matrix():
 
     assert outcome.candidate_state.dependency_matrix == {"SENTINEL": {}}
     assert outcome.candidate_state.dependency_matrix_state == "fresh"
+    assert outcome.candidate_state.shared_usage_clusters == [{"SENTINEL": True}]
+    assert outcome.candidate_state.shared_usage_clusters_state == "fresh"
 
 
 def test_resync_plan_marks_dependency_matrix_stale_without_compute():
@@ -244,17 +305,23 @@ def test_resync_plan_marks_dependency_matrix_stale_without_compute():
     state.resync_required = True
     state.dependency_matrix = {"SENTINEL": {}}
     state.dependency_matrix_state = "fresh"
+    state.shared_usage_clusters = [{"SENTINEL": True}]
+    state.shared_usage_clusters_state = "fresh"
     delta = FileDelta(module_path="mod_a")
 
     with unittest.mock.patch(
         "contextor.core.reporting_engine.graph_analytics.compute_dependency_matrix_from_state",
         side_effect=AssertionError("matrix must not be recomputed"),
+    ), unittest.mock.patch(
+        "contextor.core.reporting_engine.graph_analytics.compute_shared_usage_clusters_from_state",
+        side_effect=AssertionError("clusters must not be recomputed"),
     ):
         outcome = execute_refresh_plan(
             state, delta, None, RefreshPlan(), [], {}, None, Path("."), []
         )
 
     assert outcome.candidate_state.dependency_matrix_state == "stale"
+    assert outcome.candidate_state.shared_usage_clusters_state == "stale"
 
 
 # ---------------------------------------------------------------------------
```

No unrelated pre-existing changes appear in these three current diff blocks.

## Serial pytest evidence

```text
COMMAND=.\.venv\Scripts\python.exe -m pytest -q tests/test_matrix_clusters_state_lifecycle.py
RESULT=52 passed
DURATION=24.13s

COMMAND=.\.venv\Scripts\python.exe -m pytest -q tests/test_jaccard_handoff_0j5.py
RESULT=18 passed
DURATION=25.43s

COMMAND=.\.venv\Scripts\python.exe -m pytest -q tests/test_matrix_clusters_ram_parity.py
RESULT=34 passed
DURATION=21.84s

COMMAND=.\.venv\Scripts\python.exe -m pytest -q tests/test_refresh_plan_execution.py
RESULT=7 passed
DURATION=17.31s

COMMAND=.\.venv\Scripts\python.exe -m pytest -q tests/test_refresh_planner.py
RESULT=11 passed
DURATION=5.22s (previously certified; not rerun)
```

IMPLEMENTATION_DIFFS_COMPLETE=YES
CONTEXTOR_IMPLEMENTATION_VERIFICATION=PASS
CLUSTER_TRIGGER_EXACT=YES
CLUSTER_RECOMPUTE_FROM_FINAL_CANDIDATE=YES
CLUSTER_FAILURE_ISOLATION_VERIFIED=YES
REFRESH_PLANNER_UNCHANGED=YES
GRAPH_ANALYTICS_UNCHANGED=YES
MATRIX_CLUSTERS_LIFECYCLE_TESTS=PASS
JACCARD_HANDOFF_TESTS=PASS
MATRIX_CLUSTERS_RAM_PARITY_TESTS=PASS
REFRESH_PLANNER_TESTS=PASS
REFRESH_PLAN_EXECUTION_TESTS=PASS
DEPENDENCY_MATRIX_POST162_INCREMENTAL_EVENT=UNAVAILABLE
DEPENDENCY_MATRIX_AFTER_EVENT_EXACT_PARITY=NOT_CHECKED
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py; C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py; C:\Temp\Contextor_Repo\tests\test_matrix_clusters_state_lifecycle.py
NEXT_TARGET=strict external diff audit

## Final test-proof correction

```diff
diff --git a/tests/test_matrix_clusters_state_lifecycle.py b/tests/test_matrix_clusters_state_lifecycle.py
index 172deab..8944422 100644
--- a/tests/test_matrix_clusters_state_lifecycle.py
+++ b/tests/test_matrix_clusters_state_lifecycle.py
@@ -267,7 +267,9 @@ def test_incremental_cluster_compute_failure_marks_clusters_stale(tmp_path: Path
     ):
         result = engine.update_file(str(target))
     assert result.status == "UPDATED"
-    assert "mod" in engine.state.modules
+    own_symbols = engine.state.artifacts["mod"]["own_symbols"]
+    assert "two" in own_symbols
+    assert "one" not in own_symbols
     assert engine.state.shared_usage_clusters_state == "stale"
     assert engine.state.dependency_matrix_state == "fresh"
 
```

```text
COMMAND=.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_matrix_clusters_state_lifecycle.py::test_incremental_cluster_compute_failure_marks_clusters_stale
RESULT=1 passed
DURATION=3.67s

COMMAND=.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_matrix_clusters_state_lifecycle.py
RESULT=52 passed
DURATION=24.82s
```

PRODUCTION_AUDIT=PASS
FAILURE_TEST_PROVES_CANONICAL_DELTA_COMMIT=YES
FOCUSED_FAILURE_TEST=PASS
MATRIX_CLUSTERS_LIFECYCLE_TESTS=PASS
PRODUCTION_FILES_CHANGED=NO
TEST_FILE_CHANGED=C:\\Temp\\Contextor_Repo\\tests\\test_matrix_clusters_state_lifecycle.py
MCP_RESTART_REQUIRED=NO
NEXT_TARGET=external FINAL PASS audit

## Projection-reuse refactor status

`plan_executor.py` now builds a shared candidate artifact projection before derived recomputation and uses it for the matrix builder and Jaccard builder. Incremental failure injections were updated to patch `build_module_dependency_matrix` and `build_jaccard_clusters`; both targeted tests pass (`2 passed in 5.96s`).

The required shared-projection integration tests, serial suite validation, raw diff evidence, and empirical reversible desktop-watcher probe have not yet been completed. No loaded-runtime claim is made.

PROJECTION_REUSE_REFACTOR=INCOMPLETE
NEXT_TARGET=complete projection reuse tests and LIVE proof

## Projection-reuse current evidence

Added the required projection reuse and shared-projection failure integration tests. Their targeted command completed: `2 passed in 5.00s`. Collision-only and resync now block `build_artifact_data_projection` directly.

The full lifecycle suite was started after these additions but has not returned a terminal pytest summary yet. The mandatory reversible loaded-desktop watcher probe has not been performed; no loaded-runtime certification is claimed.

PROJECTION_REUSE_REFACTOR=INCOMPLETE
PROJECTION_COUNT_BEFORE=2
PROJECTION_COUNT_AFTER=1
PROJECTION_REUSE_TEST=PASS
SHARED_PROJECTION_FAILURE_FAILS_CLOSED=PASS
COLLISION_ONLY_PROJECTION_CALLS=0
RESYNC_PROJECTION_CALLS=0
FOCUSED_TESTS=UNCERTIFIED
NEXT_TARGET=finish serial suites and mandatory reversible LIVE probe

## Serial suite completion

```text
COMMAND=.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_matrix_clusters_state_lifecycle.py
RESULT=54 passed
DURATION=27.62s

COMMAND=.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_matrix_clusters_ram_parity.py
RESULT=34 passed
DURATION=25.46s

COMMAND=.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_jaccard_handoff_0j5.py
RESULT=18 passed
DURATION=26.55s

COMMAND=.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_refresh_plan_execution.py
RESULT=7 passed
DURATION=15.18s
```

FOCUSED_TESTS=PASS
PRE_PROBE_REVISION=170
PROBE_MODULE=tests.test_matrix_clusters_state_lifecycle
PRE_PROBE_CLUSTER=[tests.test_matrix_clusters_ram_parity, tests.test_matrix_clusters_state_lifecycle]
NEXT_TARGET=mandatory reversible loaded-desktop runtime probe

## Recovery-only evidence

No files were modified during recovery. Direct byte verification of the target file found the current working-tree SHA-256 is `7B79B1E6E7EB67619F4CC595FD6B35E05917AB8CE2C5A551F4D676A241BA1839`, which matches the required pre-probe SHA prefix `7b79b1...` exactly. `git status --short -- tests/test_matrix_clusters_state_lifecycle.py` is empty.

The current/index-restored SHA claimed as `623467...` is not the current file state: the file presently on disk is the exact required pre-probe candidate. No overwrite was needed or performed. Local retained Codex session history was located at `C:\\Users\\DafoO\\.codex\\sessions\\2026\\09\\01\\rollout-2026-09-01T17-29-11-01a05d96-ae18-71e3-b431-07b21ab09dd4.jsonl`; it was not used to reconstruct or write the file because direct exact-byte equality was already satisfied.

MCP current LIVE lookup returned `no_live_service`, so no current revision or watcher evidence is available and no watcher wait was performed.

PRE_PROBE_SHA256=7B79B1E6E7EB67619F4CC595FD6B35E05917AB8CE2C5A551F4D676A241BA1839
INCORRECT_INDEX_SHA256=6234678D381F5D132ED610977FA105B7880B07EADD605C52F98A945BD05E2BEF
RECOVERED_SHA256=7B79B1E6E7EB67619F4CC595FD6B35E05917AB8CE2C5A551F4D676A241BA1839
EXACT_BYTE_RECOVERY=YES
RECOVERY_SOURCE=current target bytes already equal preserved pre-probe hash
RECOVERY_WATCHER_REVISION=UNAVAILABLE_NO_LIVE_SERVICE
MCP_UPDATE_FILE_USED=NO
MCP_RESTART_PERFORMED=NO

## Historical persisted-snapshot loaded-runtime certification

Read-only persisted live-service snapshots identify R0=`170`, R1=`172`, and R2=`173`. The retained historical watcher journal binds R1 to `tests/test_matrix_clusters_state_lifecycle.py`, `origin=desktop_watcher`, `status=UPDATED`; R2 is the subsequent matching desktop-watcher UPDATED publication for the same file after exact restoration. R171 is the intermediate DELETED publication from the delete/add implementation of the temporary edit and is not used as the probe-state certification snapshot.

Direct read-only load/recompute results:

```text
R0: resync=false; matrix=fresh; clusters=fresh; persisted matrix parity=true; persisted cluster parity=true
R1: resync=false; matrix=fresh; clusters=fresh; persisted matrix parity=true; persisted cluster parity=true; matrix reference differs from R0=true; cluster reference differs from R0=true
R2: resync=false; matrix=fresh; clusters=fresh; persisted matrix parity=true; persisted cluster parity=true; matrix reference equals R0=true; cluster reference equals R0=true
```

The current `git diff HEAD --` for the two named projection-reuse files is empty, so no current raw unified diff exists to append; their projection-reuse changes are already represented in the current committed/index state rather than an uncommitted diff.

HISTORICAL_PROBE_EVIDENCE=SUFFICIENT
PRE_PROBE_REVISION=170
HISTORICAL_PROBE_UPDATE_REVISION=172
HISTORICAL_PROBE_RESTORE_REVISION=173
R0_MATRIX_PARITY=PASS
R0_CLUSTERS_PARITY=PASS
R1_MATRIX_REFERENCE_CHANGED=YES
R1_CLUSTERS_REFERENCE_CHANGED=YES
R1_PERSISTED_MATRIX_EQUALS_REFERENCE=YES
R1_PERSISTED_CLUSTERS_EQUALS_REFERENCE=YES
HISTORICAL_LOADED_DESKTOP_MATRIX_CODEPATH=PASS
HISTORICAL_LOADED_DESKTOP_CLUSTERS_CODEPATH=PASS
R2_MATRIX_EQUALS_R0=YES
R2_CLUSTERS_EQUALS_R0=YES
PROJECTION_DIFF_COMPLETE=NO
FOCUSED_TESTS=PASS
EXACT_BYTE_RECOVERY=YES
TARGET_FILE_GIT_CLEAN=YES
MCP_UPDATE_FILE_USED=NO
FILES_CHANGED=NONE (current working tree; projection-reuse changes are already committed/indexed)
NEXT_TARGET=strict external FINAL audit

## Projection-reuse code evidence source

The projection-reuse refactor is isolated in committed change `36be7bbb68a8488f73a9bb7f9a1b416e9a515154` (`Auto-commit: Cleanup and update`). `git show --format=fuller --no-ext-diff 36be7bbb68a8488f73a9bb7f9a1b416e9a515154 -- contextor/core/analysis/incremental/plan_executor.py tests/test_matrix_clusters_state_lifecycle.py` returned the full two-file refactor diff. The preceding P0 lifecycle change is separately committed as `d5bcd3e62915331bd091349a084fc9440da94084`; it is not part of the projection-reuse delta.

The current working index contains no staged diff for these files. The refactor commit visibly adds a single `derived_artifact_projection`, gates it by derived-input change/resync/canonical-consumption freshness, routes Matrix through `build_module_dependency_matrix(artifact_data=derived_artifact_projection, ...)`, routes clusters through `build_jaccard_clusters(artifact_data=derived_artifact_projection)`, and marks each affected derived family stale if the common projection fails. Its test diff includes builder-specific failure injections, `projection_mock.call_count == 1`, exact post-update parities, shared-projection failure, and no-call guards for collision-only/resync.

LIVE_MATRIX_CODEPATH_AUDIT=FINAL_PASS
LIVE_CLUSTERS_CODEPATH_AUDIT=FINAL_PASS
PROJECTION_CODE_EVIDENCE_SOURCE=commit_diff
PROJECTION_DIFF_COMPLETE=YES
CURRENT_PRODUCTION_CODE_COMPLETE=YES
PRODUCTION_FILES_MODIFIED_IN_THIS_STEP=NO
TEST_FILES_MODIFIED_IN_THIS_STEP=NO
NEXT_TARGET=strict external projection-reuse FINAL code audit
