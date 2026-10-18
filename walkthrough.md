# CONTEXTOR_REGRESSION_26 — REFRESH_PLAN_LINEAGE_10_FIX

## TASK

Controlled test-only replacement of incomplete RefreshPlan doubles with the canonical domain contract in two approved files. No production changes.

## HEAD_BEFORE

07abca0fac403788af5a89a17a9f2a7453a8b63d

## HEAD_AFTER

07abca0fac403788af5a89a17a9f2a7453a8b63d (no commit)

## FILES_CHANGED

- tests/test_incremental_phase_trace.py
- tests/test_lineage_state_lifecycle.py

walkthrough.md is this report and excluded from source/test diffs. Working tree had no other source/test changes at start.

## EXACT_IMPLEMENTATION

Both files import contextor.core.domain.refresh_plan.RefreshPlan. In test_incremental_phase_trace.py, the plan passed by _run is RefreshPlan(patch_families=patch_families), retaining the identity_registry tuple or empty tuple. In test_lineage_state_lifecycle.py, seven SimpleNamespace() values used as the positional plan argument of _apply_delta_and_commit are now RefreshPlan(). No other SimpleNamespace double or assertion changed.

Contextor identified RefreshPlan in the contract layer; runtime consumers include refresh_planner and incremental.plan_executor. The canonical class defaults refresh_completeness to "complete" and semantic_certainty to "statically_resolved". No requires_resync was introduced.

## TEN_REGRESSION_RESULTS

Command: .venv/Scripts/python.exe -m pytest -q --tb=short with the ten exact test node IDs specified in the task.
Result: 7 passed, 3 failed in 3.90 s.

1. test_identity_sync_success_emits_order_and_no_missing_owners: FAIL
2. test_identity_sync_lineage_failure_propagates_without_file_state: PASS
3. test_non_identity_path_emits_skip_and_default_lineage_scope: FAIL
4. test_registry_diagnostic_gap_is_observed_without_repair_or_raise: FAIL
5. test_incremental_commit_publishes_lineage_candidate_fields: PASS
6. test_identity_sync_materializes_against_new_ids_and_rolls_back_on_failure: PASS
7. test_identity_sync_owner_deletion_matches_fresh_full_materialization_without_reextracting_untouched_consumer: PASS
8. test_identity_sync_owner_introduction_promotes_retained_untouched_consumer_to_full_parity: PASS
9. test_identity_sync_generation_change_rematerializes_against_current_owner_id: PASS
10. test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_state: PASS

Exact failing traceback chain (same for tests 1, 3, 4; separately repeated with --tb=long, 3 failed in 1.20 s):

```text
tests/test_incremental_phase_trace.py:175 (or :234 or :261): _run(...)
tests/test_incremental_phase_trace.py:140: return engine._apply_delta_and_commit(...)
contextor/core/analysis/incremental/engine.py:148: return method(self, *args, **kwargs)
contextor/core/analysis/incremental/engine.py:1147:
    self.state.cycle_semantics = (candidate.cycle_semantics)
AttributeError: 'types.SimpleNamespace' object has no attribute 'cycle_semantics'. Did you mean: 'cycle_semantics_state'?
```

CLASSIFICATION: The approved RefreshPlan replacement removes the prior missing plan.refresh_completeness boundary. These three tests now reach a separate incomplete _candidate() SimpleNamespace in the phase-trace fixture. This is a test-double contract gap beyond the explicitly approved plan substitutions. The instruction forbids changing other SimpleNamespace doubles, so no candidate edit was made. The exact long traceback showed RefreshPlan(..., refresh_completeness='complete', semantic_certainty='statically_resolved').

## FOCUSED_NON_REGRESSION_RESULTS

Command: pytest -q --tb=short on only the two approved files with the ten named cases deselected via -k.
Result: 34 passed, 10 deselected in 6.56 s.

## CONTRACT_PRESERVATION

RefreshPlan canonical defaults are intact. Existing patch_families, identity/non-identity paths, phase-order assertions, rollback and lineage logic, registry, delta, candidate, outcome, and engine doubles remain unchanged. Production engine, refresh_plan, refresh_planner, and plan_executor were not edited. git diff --check passed for both files.

## LIVE_REVISION_BEFORE_AFTER

Before: revision 614, continuity=continuous, resync_required=false.
After: revision 616, continuity=continuous, resync_required=false, same activity epoch 5d758bf9339c4ac5a5816ab056e7f84b. Contextor get_symbol_implementation at revision 616 reported canonical_state=fresh and workspace_sync=verified for both edited files. get_file_edit_context reported syntax_diagnostics status=checked_and_none, zero errors in both files.

## WATCHER_EVENTS

- Revision 615: desktop_watcher update_file UPDATED tests/test_incremental_phase_trace.py.
- Revision 616: desktop_watcher update_file UPDATED tests/test_lineage_state_lifecycle.py.

No manual update_file call.

## RESTART_REQUIREMENTS

MCP_BACKEND_RESTART_REQUIRED=NO; LIVE_SERVICE_RESTART_REQUIRED=NO. Changes are test-only and no process was restarted.

## FULL_DIFFS

Full actual unified diffs of both task-changed test files follow.
```diff
diff --git a/tests/test_incremental_phase_trace.py b/tests/test_incremental_phase_trace.py
index 4f28715..6fb219f 100644
--- a/tests/test_incremental_phase_trace.py
+++ b/tests/test_incremental_phase_trace.py
@@ -12,6 +12,7 @@ from contextor.core.analysis.state_manager import (
     FileState,
     RepositoryAnalysisState,
 )
+from contextor.core.domain.refresh_plan import RefreshPlan
 
 
 engine_module = import_module("contextor.core.analysis.incremental.engine")
@@ -140,7 +141,7 @@ def _run(
         "target.py",
         delta,
         None,
-        SimpleNamespace(
+        RefreshPlan(
             patch_families=patch_families,
         ),
         [],
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index b1391e7..0594937 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -51,6 +51,7 @@ from contextor.core.domain.lineage_facts import (
     build_return_slot,
 )
 from contextor.core.domain.module import Module
+from contextor.core.domain.refresh_plan import RefreshPlan
 from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.live_state.hydration import hydrate_repository_engine
 from contextor.core.live_state.store import load_snapshot, save_snapshot
@@ -548,7 +549,7 @@ def test_incremental_commit_publishes_lineage_candidate_fields(
         str(tmp_path / "pkg.py"),
         SimpleNamespace(module_path="pkg", is_deleted=False),
         None,
-        SimpleNamespace(),
+        RefreshPlan(),
         [],
         {},
         None,
@@ -1060,7 +1061,7 @@ def test_identity_sync_materializes_against_new_ids_and_rolls_back_on_failure(
         str(tmp_path / "pkg.py"),
         SimpleNamespace(module_path="pkg", is_deleted=False),
         None,
-        SimpleNamespace(),
+        RefreshPlan(),
         [],
         {},
         None,
@@ -1106,7 +1107,7 @@ def test_identity_sync_materializes_against_new_ids_and_rolls_back_on_failure(
             str(tmp_path / "pkg.py"),
             SimpleNamespace(module_path="pkg", is_deleted=False),
             None,
-            SimpleNamespace(),
+            RefreshPlan(),
             [],
             {},
             None,
@@ -1161,7 +1162,7 @@ def test_identity_sync_owner_deletion_matches_fresh_full_materialization_without
         str(tmp_path / "provider.py"),
         SimpleNamespace(module_path="provider", is_deleted=True),
         None,
-        SimpleNamespace(),
+        RefreshPlan(),
         [],
         {},
         None,
@@ -1249,7 +1250,7 @@ def test_identity_sync_owner_introduction_promotes_retained_untouched_consumer_t
         str(tmp_path / "provider.py"),
         SimpleNamespace(module_path="provider", is_deleted=False),
         None,
-        SimpleNamespace(),
+        RefreshPlan(),
         [],
         {},
         None,
@@ -1317,7 +1318,7 @@ def test_identity_sync_generation_change_rematerializes_against_current_owner_id
         str(tmp_path / "provider.py"),
         SimpleNamespace(module_path="provider", is_deleted=False),
         None,
-        SimpleNamespace(),
+        RefreshPlan(),
         [],
         {},
         None,
@@ -1384,7 +1385,7 @@ def test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_st
             str(tmp_path / "provider.py"),
             SimpleNamespace(module_path="provider", is_deleted=True),
             None,
-            SimpleNamespace(),
+            RefreshPlan(),
             [],
             {},
             None,
```
## FINAL_VERDICT

PARTIAL. The approved RefreshPlan substitutions are complete and all six lineage-state regressions pass. Three phase-trace regressions remain blocked by an independently incomplete candidate double. Their exact failure boundary is documented above; no unapproved changes were made. All 34 other tests in the two files passed.

STOP. Await `proceduj`.
