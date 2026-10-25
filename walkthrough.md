# CONTEXTOR_P1D1E_STRUCTURAL_CYCLE_REGRESSION_FIX

TASK: Exact implementation of the supplied two-file patch; no redesign.
HEAD_BEFORE: 63099e26ac0bb071450d918ed0242c8aceb4124e
HEAD_AFTER: 63099e26ac0bb071450d918ed0242c8aceb4124e
FILES_CHANGED:
- contextor/core/cycle_semantics/live_installed_claims.py
- tests/live_state/test_installed_cycle_generation_gate.py
The pre-existing walkthrough.md change was overwritten as the required report and is excluded from FILES_CHANGED.

STRUCTURAL_CYCLE_ROOT_CAUSE:
DIRECT_EVIDENCE: At canonical revision 668, Contextor showed the hard edge live_installed_claims -> analysis.state_manager. The retained revision-667 desktop_watcher event recorded ADDED for this exact cycle:
analysis.state_manager -> live_state.__init__ -> live_state.hydration -> live_state.runtime -> live_state.ipc -> cycle_semantics.live_installed_claims -> analysis.state_manager.
The current structural count before edit was 17 DFS back-edge paths.

EXACT_FIX:
Removed the direct RepositoryAnalysisState import. The LIVE helper retrieves the already-loaded nominal class via sys.modules and compares exact type identity. Missing or replaced class fails closed. Added only T17 and T18 from the supplied patch.

T01_T18_RESULTS: 18 passed, 0 failed in tests/live_state/test_installed_cycle_generation_gate.py.
NOMINAL_CLASS_IDENTITY_PROOF: CODE_PATH_PROVED: type(registered_state_type) is type and type(state) is registered_state_type. CONTRACT_PROVED: T17 rejects SimpleNamespace carrying copied state attributes with INSTALLED_STATE_UNAVAILABLE.
ABSENT_MODULE_FAIL_CLOSED_PROOF: CONTRACT_PROVED: T18 removes the module registry entry and receives INSTALLED_STATE_UNAVAILABLE. The helper contains no fallback import.
FOCUSED_NON_REGRESSION: 67 passed, 0 failed across the six specified focused files. Both changed files compiled with py_compile. Historical 4298-PASS baseline was not rerun.

CANONICAL_CYCLE_BEFORE_AFTER: Fresh structural cycle diagnostics: revision 668 = 17; revision 669 and 670 = 16. Count semantics are deduplicated DFS back-edge paths, not all simple cycles. Current cycle-semantic family remains stale and runtime execution status is UNKNOWN_NOT_EVALUATED.
CYCLE_RESOLUTION_EVENT: DIRECT_EVIDENCE: revision-669 desktop_watcher update_file for live_installed_claims.py contained diagnostic_changes action=RESOLVED, diagnostic_kind=cycle, with the exact seven-node cycle above.
HARD_EDGE_ABSENCE: DIRECT_EVIDENCE: revision-670 Contextor module context lists only publication_binding as an outbound hard dependency; canonical dependencies query for live_installed_claims -> analysis.state_manager returned zero matches.
LIVE_REVISION_BEFORE_AFTER: 668 -> 670; activity_epoch 714b1f0fcdf34953b33ba77281b7e94b throughout.
WATCHER_EVENTS: revision 669 UPDATED live_installed_claims.py; revision 670 UPDATED test_installed_cycle_generation_gate.py; origin desktop_watcher. Cursor continuity continuous; resync_required=false.
WORKSPACE_SYNC: Both changed files workspace_sync=verified and canonical_state=fresh at revision 670. Project-wide workspace_sync remains unverified; no repository-wide sync is claimed.
COLLISION_DIAGNOSTICS: Fresh canonical name collisions = 2 before and after; both warning/conflicting. No new count observed.
RUNTIME_ADOPTION_LIMITATION: UNKNOWN: Existing service process code-load adoption of the changed helper was not verified. Static tests and watcher indexing do not prove loaded runtime behavior.
RESTART_REQUIREMENTS: No restart was performed per task. A later runtime certification requires independently verified code-load adoption or manual reload, then freshness/schema/version check.
WHITESPACE_CHECK: git diff --check exit 0. Git emitted only LF-to-CRLF working-copy warnings.
FINAL_VERDICT: PASS for exact source patch, focused tests, and canonical structural cycle resolution. LIVE execution of newly loaded code remains UNKNOWN.

FULL_DIFFS / ACTUAL_DIFF:
```diff
diff --git a/contextor/core/cycle_semantics/live_installed_claims.py b/contextor/core/cycle_semantics/live_installed_claims.py
index 814c8cc..e923428 100644
--- a/contextor/core/cycle_semantics/live_installed_claims.py
+++ b/contextor/core/cycle_semantics/live_installed_claims.py
@@ -12,13 +12,10 @@ safety is certified by this operation.
 
 from __future__ import annotations
 
+import sys
 from collections.abc import Mapping
 from typing import Any
 
-from contextor.core.analysis.state_manager import (
-    RepositoryAnalysisState,
-)
-
 from .publication_binding import (
     CanonicalCycleManifestReceipt,
     verify_co_published_cycle_manifest,
@@ -120,7 +117,24 @@ def assess_live_installed_prepared_claims(
     ):
         return unavailable("LIVE_REPOSITORY_MISMATCH")
 
-    if type(state) is not RepositoryAnalysisState:
+    # The LIVE owner already holds an instance of the canonical
+    # state class. Resolve its exact loaded class identity without
+    # importing analysis.state_manager from the LIVE query layer.
+    #
+    # Do not dynamically import an absent module: that would
+    # reintroduce initialization coupling and weaken fail-closed
+    # behavior during partial or inconsistent runtime adoption.
+    registered_state_type = getattr(
+        sys.modules.get(
+            "contextor.core.analysis.state_manager"
+        ),
+        "RepositoryAnalysisState",
+        None,
+    )
+    if (
+        type(registered_state_type) is not type
+        or type(state) is not registered_state_type
+    ):
         return unavailable("INSTALLED_STATE_UNAVAILABLE")
 
     if (
diff --git a/tests/live_state/test_installed_cycle_generation_gate.py b/tests/live_state/test_installed_cycle_generation_gate.py
index c9d78f7..a72f2a8 100644
--- a/tests/live_state/test_installed_cycle_generation_gate.py
+++ b/tests/live_state/test_installed_cycle_generation_gate.py
@@ -342,3 +342,47 @@ def test_p1d1e_t16_owner_without_authority_fails_closed(
     assert answer["reason"] == (
         "LIVE_AUTHORITY_UNAVAILABLE"
     )
+
+
+def test_p1d1e_t17_structural_impostor_state_rejected(owner):
+    from types import SimpleNamespace
+
+    server, request = owner
+    original = server._state
+
+    # Copy the canonical state's attributes into a different
+    # class. Matching attributes do not imply class identity.
+    server._state = SimpleNamespace(**vars(original))
+    try:
+        answer = _check(server, request)
+    finally:
+        server._state = original
+
+    assert answer["status"] == "unavailable"
+    assert answer["reason"] == (
+        "INSTALLED_STATE_UNAVAILABLE"
+    )
+
+
+def test_p1d1e_t18_absent_loaded_class_fails_closed(
+    owner, monkeypatch,
+):
+    import sys
+
+    server, request = owner
+
+    # The helper must not try a dynamic import when the
+    # nominal canonical class cannot be obtained from the
+    # currently loaded module registry.
+    with monkeypatch.context() as scoped:
+        scoped.delitem(
+            sys.modules,
+            "contextor.core.analysis.state_manager",
+            raising=True,
+        )
+        answer = _check(server, request)
+
+    assert answer["status"] == "unavailable"
+    assert answer["reason"] == (
+        "INSTALLED_STATE_UNAVAILABLE"
+    )
```
