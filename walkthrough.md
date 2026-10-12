# CONTEXTOR_B0G2D1_FIX_FIXTURE_NAME_COLLISION

## FILES_CHANGED

- C:\Temp\Contextor_Repo\tests\test_desktop_mcp_live_incremental_parity.py
- C:\Temp\Contextor_Repo\walkthrough.md (current report only)

No production file or other test changed.

## EXACT_FIXTURE_CORRECTION

Exactly two approved bytes literals changed: consumer.py now declares CONSUMED_VALUE = child.VALUE; unrelated.py now declares UNRELATED_VALUE = 2. The import from pkg, qualified child.VALUE reference, pkg/__init__.py, pkg/child.py and _CHANGED_INIT remain untouched. No validator, comparator, assertion or production code changed. Pre-edit Contextor get_source_range confirmed both exact old anchors. HEAD=1f2684f4d2a7ffc4cc43091eaff47fb09b01c71b and worktree was clean before the edit.

## COLLISION_VALIDATION_RESULT

The corrected first FULL baseline passed the existing assert not errors. Read-only inspection of the preserved initial snapshot found zero collisions; collisions_state=fresh. This removes the accidental fixture NAME_COLLISION without suppressing collision detection.

## REAL_FULL_BASELINE

Production run_full_analysis_exclusive plus ContextorFacade completed on the isolated four-file fixture. Preserved initial_full.pickle: writer=desktop, revision=1, state_id=20261012_130208, repo_id=ctx_aa7ae0e9, resync_required=false. Its graph has consumer hard_edges={'pkg.__init__'} and soft_edges={'pkg.child'}. FileState payload _meta matches revision 1 and state_id. No Contextor_Repo FULL analysis ran.

## DESKTOP_WATCHER_TRANSPORT

The test advanced through real DesktopLiveWatcher._enqueue_path and poll_once, real IPC LiveStateClient.submit_update_file, asynchronous coordinator job completion and mutation_status. All transport assertions before the failing canonical comparison passed: exactly one job, stored request operation=submit_update_file, origin=desktop_watcher, completed state, result status UPDATED, consumer in affected_modules and unrelated absent, graph_state=fresh, one event with desktop_watcher origin, no resync. No synchronous MCP route was substituted for this phase.

## MCP_PUBLIC_UPDATE_TRANSPORT

NOT REACHED. The explicit fail gate stops after the Desktop incremental state diverges from fresh FULL oracle A. No MCP public update was invoked in this run.

## LIVE_REVISION_AND_PERSISTENCE

Isolated fixture generations from preserved evidence: initial FULL revision 1 writer desktop; watcher incremental revision 2 writer live-service, state_id 20261012_130208; fresh FULL oracle A revision 3 writer desktop, state_id 20261012_130209. Each captured FileState _meta matches its own revision/state_id, has four tracked source files, and each source hash was checked by _capture_snapshot. Both modified-source captures have the expected 12-byte pkg/__init__.py and unchanged other source bytes. All three captured states report resync_required=false. The isolated LIVE server closed before oracle A, and the test preserved state evidence at:
C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-555\test_real_desktop_watcher_and_0\b0g2d_canonical_mismatch_evidence\initial_full.pickle
C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-555\test_real_desktop_watcher_and_0\b0g2d_canonical_mismatch_evidence\desktop_incremental.pickle
C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-555\test_real_desktop_watcher_and_0\b0g2d_canonical_mismatch_evidence\fresh_full_a.pickle

## FOUR_WAY_CANONICAL_PARITY

NOT ESTABLISHED. The strict B0G2C3 comparator stopped at the first Desktop incremental versus FULL oracle A difference, before restoring the second baseline or entering the MCP phase. The differing canonical family is artifacts/consumers. Graph hard/soft edges agree in the two modified-source captures, but graph equality does not erase the artifact difference.

## FIRST_FAILURE_IF_ANY

Exact first failure from the sole test run:

    F
    ================================== FAILURES ===================================
    ____ test_real_desktop_watcher_and_public_mcp_incremental_match_fresh_full ____
    Desktop incremental vs fresh FULL A canonical mismatch: first_field=state.artifacts[{'kind': 'primitive', 'type': 'builtins.str', 'value': 'pkg.__init__'}][{'kind': 'primitive', 'type': 'builtins.str', 'value': 'consumers'}].<key-count>; left=0; right=1; evidence=C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-555\test_real_desktop_watcher_and_0\b0g2d_canonical_mismatch_evidence
    FAILED tests/test_desktop_mcp_live_incremental_parity.py::test_real_desktop_watcher_and_public_mcp_incremental_match_fresh_full
    1 failed, 1 warning in 7.58s

The unabridged field path and evidence directory above are the test's first-failure output. A compact rendering follows:

    Desktop incremental vs fresh FULL A canonical mismatch:
    first_field=state.artifacts[{'kind': 'primitive', 'type': 'builtins.str',
    'value': 'pkg.__init__'}][{'kind': 'primitive', 'type': 'builtins.str',
    'value': 'consumers'}].<key-count>; left=0; right=1

DIRECT_EVIDENCE from preserved snapshots: incremental state.artifacts['pkg.__init__']['consumers'] is {}; fresh FULL A has a 'child' consumer entry with empty usage collections and zero counts. Both states have consumer hard edge {'pkg.__init__'}, no consumer soft edge, fresh artifact_consumption_state, fresh lineage_facts_state, fresh topology/cycles/collisions markers, and zero collisions. The exact mismatch is in canonical symbol/consumer materialization, not in the fixture collision or graph edge assertions.

## FAILURE_CLASSIFICATION

CANONICAL_SEMANTIC_MISMATCH (CODE_PATH_PROVED by the passing transport/persistence checks and DIRECT_EVIDENCE from the two preserved states). Root cause within incremental materialization is UNKNOWN; no production fix or additional normalization was attempted. It is not a transport failure, persistence failure or runtime blocker on the observed Desktop phase.

## TARGETED_TEST_RESULTS

Only the instructed new module ran:
C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q -s tests/test_desktop_mcp_live_incremental_parity.py
Result: 1 failed at the canonical comparison, 1 unrelated Authlib deprecation warning, 7.58 s. No other targeted regressions or full repository suite were run after the fail gate.

## PY_COMPILE

PASS: C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m py_compile C:\Temp\Contextor_Repo\tests\test_desktop_mcp_live_incremental_parity.py.

## GIT_DIFF_CHECK

PASS: git diff --check -- tests/test_desktop_mcp_live_incremental_parity.py (exit 0; only Git LF/CRLF warning). The full actual source diff appears below.

## LIVE_REVISION_BEFORE_AFTER

Real Contextor_Repo LIVE revision 359 before, 360 after. Contextor get_live_events(after_revision=359) reported one desktop_watcher UNCHANGED event at revision 360 for the approved test file; continuity=continuous and resync_required=false. The unchanged event is consistent with editing only Python fixture string values, but it is not used as proof of semantic parity. No manual update_file call was made.

## WORKSPACE_SYNC_POSTCHECK

Contextor get_source_range showed the exact two new fixture literals. get_symbol_implementation for _source_bytes returned workspace_sync=verified, complete source, canonical revision 360. This verifies indexed source identity, not separately serving process import reload.

## RESYNC_REQUIRED

false for real Contextor_Repo LIVE. false in all three preserved isolated captures.

## RESTART_REQUIRED

No restart required for this test-only fixture edit. No restart performed.

## FINAL_VERDICT

B0G2D1_NEXT_FAILURE_DISCOVERED. The collision fixture defect is fixed and real watcher transport reaches a committed revision, but Desktop incremental artifacts differ from fresh FULL at the exact consumer path above. Per instruction, stopped before MCP phase and made no further code or test changes. This is not Contextor FINAL PASS. Await "proceduj".

## FULL_DIFFS

Complete actual diff of C:\Temp\Contextor_Repo\tests\test_desktop_mcp_live_incremental_parity.py:

```diff
diff --git a/tests/test_desktop_mcp_live_incremental_parity.py b/tests/test_desktop_mcp_live_incremental_parity.py
index 81a8731..6458a1d 100644
--- a/tests/test_desktop_mcp_live_incremental_parity.py
+++ b/tests/test_desktop_mcp_live_incremental_parity.py
@@ -33,8 +33,8 @@ from contextor.mcp import runtime as mcp_runtime
 _INITIAL = {
     "pkg/__init__.py": b"",
     "pkg/child.py": b"VALUE = 1\n",
-    "consumer.py": b"from pkg import child\nVALUE = child.VALUE\n",
-    "unrelated.py": b"VALUE = 2\n",
+    "consumer.py": b"from pkg import child\nCONSUMED_VALUE = child.VALUE\n",
+    "unrelated.py": b"UNRELATED_VALUE = 2\n",
 }
 _CHANGED_INIT = b"child = 123\n"
 
```
