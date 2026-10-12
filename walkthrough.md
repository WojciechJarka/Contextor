# CONTEXTOR_B0G2D6_DIRECT_ENGINE_FAILURE_ROLLBACK

## FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only, excluded from source/test changed files)
- No test edits. Existing B0G2D5 RED tests remained untouched.

## SOURCE_PRECHECK
DIRECT_EVIDENCE: Contextor MCP used first; current documentation and deferred tools checked. Complete current implementations fetched for _apply_delta_and_commit, _commit_syntax_candidate, _updated_module_usage_manifest, FileStateManager.update_state and PersistentIdentityRegistry.restore_checkpoint. update_file fetched in complete contiguous source ranges. Source contract matched auditor anchors. Contextor call-context confirmed update_file calls _apply_delta_and_commit at the deletion and normal-update branches. Static artifact blast radius returned zero direct symbol consumers, a narrower claim than runtime call reachability. FileStateManager.update_state installs a newly computed FileState entry or deletes an entry; it does not mutate a prior FileState instance in place. Initial Contextor workspace_sync=verified, revision 371, continuity=continuous, resync_required=false.
Current HEAD 8ca0c623ec7aa8c5a123f5e45cb51de88bd7d1d2. This is an externally performed auto-commit of the preceding B0G2D5 test and walkthrough, not a production engine change. Prepatch worktree was clean.

## EXACT_ROLLBACK_IMPLEMENTATION
Added the exact auditor-supplied _atomic_delta_commit decorator and _failed_commit_guard context manager, plus contextmanager and wraps imports. Full literal source appears in FULL_DIFFS below. Guard captures the current state object's attribute dictionary by shallow copy, the FileStateManager mapping by shallow copy, and an optional detached registry checkpoint. On an ordinary exception, it attempts registry restore where scoped, restores all original state attributes and the same tracked mapping, then propagates the original exception. No source reparse, FULL analysis or full graph deepcopy was added.

## NORMAL_COMMIT_GUARD
Applied @_atomic_delta_commit to _apply_delta_and_commit, with original body unchanged. Decorator extracts RefreshPlan from keyword or fourth positional argument and enables registry checkpoint only when patch_families includes identity_registry. This covers registry sync, lineage materialization, canonical RAM publication, FileState acknowledgement and manifest publication.

## SEMANTIC_NOOP_GUARD
Wrapped only _commit_syntax_candidate, state_manager.update_state and _updated_module_usage_manifest assignment in update_file's parsed semantic no-op branch. Their order and the return payload outside the context are unchanged. Syntax-error handling and early UNCHANGED handling were not edited.

## REGISTRY_CHECKPOINT_SCOPE
The guard requests create_checkpoint only for a plan declaring identity_registry. It calls restore_checkpoint on a guarded failure and does not swallow a rollback failure. The normal no-op branch uses no registry checkpoint.

## COW_AND_STATE_IDENTITY
DIRECT_EVIDENCE from unchanged B0G2D5 test: all A-D retain the identical RepositoryAnalysisState object and exact 36-field structural projection after injected failures, without timestamp normalization. Case D remains the prepublication COW control. These tests establish the tested paths, not arbitrary nested mutations in untested paths.

## FILESTATE_RESTORATION
Unchanged B0G2D5 A-D tests found no FileStateManager._state difference after exception. Case B and C each performed one real FileState acknowledgement before the later missing-hash exception, then returned to baseline mapping.

## MANIFEST_RESTORATION
Unchanged B0G2D5 A-D tests found no module_usages_manifest difference after exception. The guard restores the original field reference through the state attribute snapshot.

## RED_TO_GREEN_RESULTS
Command: .venv\Scripts\python.exe -m pytest -q -s tests/test_incremental_failed_commit_atomicity.py
PASS: 4 passed, 1 dependency warning in 17.48s; exit 0. A/B/C/D all printed canonical_state_object_same=True and first differences None for canonical state, FileState, manifest, registry and persisted generation metadata. The test file was not modified.

## REAL_FOUR_WAY_PARITY_REGRESSION
tests/test_desktop_mcp_live_incremental_parity.py was included in the subsequent targeted run. Its test was not among the two failing nodes. The complete targeted command returned 24 passed, 2 failed, so the combined gate is not PASS. No Contextor_Repo FULL analysis was run; the test uses isolated temporary repositories.

## OTHER_TARGETED_REGRESSIONS
Command included exactly the three required files test_incremental_consumer_manifest_parity.py, test_incremental_layer_report_parity.py, test_desktop_mcp_live_incremental_parity.py, plus selected nodes for module add/delete, semantic no-op, registry identity, phase trace, COW and LIVE persistence conflicts.
Result: 24 passed, 2 failed, 1 dependency warning in 48.49s, exit 1.
First failure: tests/test_incremental_phase_trace.py::test_identity_sync_success_emits_order_and_no_missing_owners. Trace: _run -> decorated _apply_delta_and_commit -> _failed_commit_guard at engine.py:179 -> AttributeError: 'FakeStateManager' object has no attribute '_state'. The synthetic FakeStateManager lacks the real FileStateManager mapping required by the exact guard.
Second failure: tests/test_incremental_phase_trace.py::test_identity_sync_lineage_failure_propagates_without_file_state, same AttributeError at engine.py:179, before its intended ValueError owner-failure.
No subsequent tests were run. No independent implementation adaptation or test change was made.

## ROLLBACK_FAILURE_POLICY
CODE_PATH_PROVED from exact helper: after a guarded ordinary exception, failed registry restore is retained as rollback_error while state attributes and FileState mapping are restored in finally; then a fatal RuntimeError("Incremental commit failed and persistent registry rollback also failed") is raised from the rollback error. Otherwise the original exception propagates. This policy was not separately failure-injection tested in this task.

## RESIDUAL_ATOMICITY_LIMITATIONS
The guard covers ordinary Python exceptions in the two specified commit scopes only. It does not establish power-loss durability, process-termination safety, protection from unsupported concurrent external registry writers, or atomicity of unrelated unguarded paths. The two targeted fake-manager failures block full regression acceptance. Serving-process code reload has not been certified.

## PY_COMPILE
.venv\Scripts\python.exe -m py_compile contextor\core\analysis\incremental\engine.py: PASS, exit 0.

## GIT_DIFF_CHECK
git diff --check: exit 0, no whitespace error. Git printed only its LF-to-CRLF working-copy warning.

## LIVE_REVISION_BEFORE_AFTER
Before 371. After 372. One continuous desktop_watcher update_file UPDATED event for C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py; no manual MCP update_file, no restart. resync_required=false.

## WORKSPACE_SYNC_POSTCHECK
Contextor get_symbol_implementation on new _failed_commit_guard returned complete source with workspace_sync=verified at canonical revision 372. This proves source indexing sync, not imported-code reload.

## RESYNC_REQUIRED
false, per post-edit get_live_events; continuity=continuous.

## RESTART_REQUIRED
Manual serving-process reload will be needed before operational runtime certification because production engine.py changed. No MCP, Desktop or LIVE process was restarted in this task.

## FINAL_VERDICT
B0G2D6_OTHER_REGRESSION_BLOCKED. Literal implementation passed all four strong failure-atomicity tests, but two directly relevant existing phase-trace tests fail at guard entry because FakeStateManager has no _state. Per task instruction, stopped without redesign or test modification. Await proceduj.

## FULL_DIFFS
Complete actual diff for the only changed source file:

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index c95f756..13e137c 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -1,6 +1,8 @@
 import threading
 import time
+from contextlib import contextmanager
 from dataclasses import dataclass, field
+from functools import wraps
 from pathlib import Path
 from typing import Optional, List, Set, Dict, Iterable, Tuple, Any
 
@@ -116,6 +118,35 @@ class IncrementalUpdateResult:
     execution_trace: Optional[Dict[str, Any]] = field(default=None, repr=False)
 
 
+def _atomic_delta_commit(method):
+    """Guard the direct engine's ordinary-exception commit boundary."""
+
+    @wraps(method)
+    def guarded(self, *args, **kwargs):
+        plan = kwargs.get("plan")
+
+        if plan is None and len(args) > 3:
+            plan = args[3]
+
+        if plan is None:
+            raise TypeError(
+                "Atomic incremental commit requires RefreshPlan"
+            )
+
+        patch_families = tuple(
+            getattr(plan, "patch_families", ()) or ()
+        )
+
+        with self._failed_commit_guard(
+            may_write_registry=(
+                "identity_registry" in patch_families
+            ),
+        ):
+            return method(self, *args, **kwargs)
+
+    return guarded
+
+
 class IncrementalAnalysisEngine:
     """
     Core engine for handling real-time delta updates to the canonical repository state.
@@ -135,6 +166,54 @@ class IncrementalAnalysisEngine:
         self._lock = threading.Lock()
         materialize_incremental_state(self.state)
 
+    @contextmanager
+    def _failed_commit_guard(
+        self,
+        *,
+        may_write_registry: bool = False,
+    ):
+        """Restore direct-engine ownership after a failed commit."""
+        state_object = self.state
+        state_before = vars(state_object).copy()
+
+        tracked_mapping = self.state_manager._state
+        tracked_before = tracked_mapping.copy()
+
+        registry_checkpoint = (
+            self.registry.create_checkpoint()
+            if may_write_registry
+            else None
+        )
+
+        try:
+            yield
+        except Exception:
+            rollback_error = None
+
+            try:
+                if registry_checkpoint is not None:
+                    self.registry.restore_checkpoint(
+                        registry_checkpoint
+                    )
+            except Exception as exc:
+                rollback_error = exc
+            finally:
+                current_attributes = vars(state_object)
+                current_attributes.clear()
+                current_attributes.update(state_before)
+
+                tracked_mapping.clear()
+                tracked_mapping.update(tracked_before)
+                self.state_manager._state = tracked_mapping
+
+            if rollback_error is not None:
+                raise RuntimeError(
+                    "Incremental commit failed and persistent "
+                    "registry rollback also failed"
+                ) from rollback_error
+
+            raise
+
     def _ensure_topology_analytics(self) -> None:
         """Compatibility wrapper delegating to materialization.ensure_topology_analytics."""
         ensure_topology_analytics(self.state)
@@ -665,20 +744,21 @@ class IncrementalAnalysisEngine:
                 # Parsing proved the tracked source is semantically unchanged.
                 # Acknowledge its current fingerprint so restart reconciliation
                 # does not repeatedly queue the same canonical module.
-                self._commit_syntax_candidate(
-                    source_path=source_path,
-                    syntax_fact=checked_and_none,
-                    clear_parse_module=module_path,
-                    extracted_lineage_facts=prep.extracted_lineage_facts,
-                )
-                self.state_manager.update_state(file_path)
-                self.state.module_usages_manifest = _updated_module_usage_manifest(
-                    self.state.module_usages_manifest,
-                    module_path,
-                    file_path,
-                    is_deleted=False,
-                    tracked_sha256=self.state_manager.get_tracked_sha256(file_path),
-                )
+                with self._failed_commit_guard():
+                    self._commit_syntax_candidate(
+                        source_path=source_path,
+                        syntax_fact=checked_and_none,
+                        clear_parse_module=module_path,
+                        extracted_lineage_facts=prep.extracted_lineage_facts,
+                    )
+                    self.state_manager.update_state(file_path)
+                    self.state.module_usages_manifest = _updated_module_usage_manifest(
+                        self.state.module_usages_manifest,
+                        module_path,
+                        file_path,
+                        is_deleted=False,
+                        tracked_sha256=self.state_manager.get_tracked_sha256(file_path),
+                    )
                 return IncrementalUpdateResult(
                     status="RECOVERED" if recovered_from_parse_failure else "UNCHANGED",
                     file_path=file_path,
@@ -796,6 +876,7 @@ class IncrementalAnalysisEngine:
             new_artifacts_dict=new_artifacts_dict,
         )
 
+    @_atomic_delta_commit
     def _apply_delta_and_commit(
         self,
         file_path: str,
```
