# CONTEXTOR P1D3-WARN-2C — CONTRACT_CONFLICT

## 1. PREFLIGHT

DIRECT_EVIDENCE: Initial HEAD `72753947474f612fbe90609f6b355205802a6e47`, clean worktree. Contextor MCP inspected `facade.py` and `state_manager.py` first; structural cycle count was 16. Local source showed the official preview originates from the second original-worker index pass and `save_snapshot` already accepts `prepared_partial_scc_preparation`. Existing v2 opt-in remains separate.

## 2. HEAD / WORKTREE

DIRECT_EVIDENCE: Final HEAD unchanged. Implementation attempt was fully removed after the contract conflict. Final worktree changes only this report.

## 3. NEW OPT-IN API

UNKNOWN: Not retained because the specified publication gate conflicts with the current state contract.

## 4. PARAMETER VALIDATION

CONTRACT_PROVED: During the bounded attempt, non-bool opt-ins and missing-preview opt-in were rejected before analysis. This code was removed with the attempt.

## 5. ORIGINAL-WORKER PREVIEW REUSE

CODE_PATH_PROVED: Current `ContextorFacade.analyze_project` performs one original index, plans a reindex, performs a second original-worker capture, verifies it and calls `prepare_original_worker_cycle_manifest`. The attempted implementation did not add a third index pass.

## 6. PRE-PERSISTENCE PARTIAL AUTHORITY GATE

CONTRACT_CONFLICT: The literal gate requires `state.resync_required is False`. `RepositoryAnalysisState` does not initialize that attribute. `facade.py:1265-1266` assigns it only when `analysis_result.resync_required` is true. Existing v2 gate at `facade.py:1399` uses `getattr(state, "resync_required", False) is False`. For normal FULL states, direct access raised `AttributeError` at the new gate before persistence. Substituting `getattr` or changing the state model would be an architectural decision outside the literal instruction.

## 7. SAVE_ENGINE_STATE FORWARDING

UNKNOWN: Attempted optional forwarding was removed with the conflicting facade change. Existing v2 forwarding remains.

## 8. REAL FULL PASS / INDETERMINATE

DIRECT_EVIDENCE: The attempted focused integration test failed at direct `state.resync_required` access before a partial receipt could be committed.

## 9. REAL FULL PASS / HAZARD

DIRECT_EVIDENCE: Same failure boundary as above.

## 10. COEXISTENCE WITH COMPLETE V2

UNKNOWN: Could not be tested past the failing partial gate. Existing v2 code was not changed.

## 11. DEFAULT AND PREVIEW-ONLY COMPATIBILITY

DIRECT_EVIDENCE: Initial focused run produced 8 passes before the 12 failing partial-opt-in scenarios. No final implementation remains.

## 12. FAILURE / DRIFT FAIL-CLOSED

UNKNOWN: Cannot evaluate the requested new path until the contradictory resync gate is resolved by the architect.

## 13. GENERATION IDENTITY

CODE_PATH_PROVED: Existing store owns metadata identity and sealing. The attempt would have forwarded preparation through `save_engine_state`; no retained change exists.

## 14. STRUCTURAL GRAPH IMMUTABILITY

DIRECT_EVIDENCE: Final source is unchanged. No new imports or hard edges remain. Preflight structural count was 16; no post-change count is meaningful because all source edits were removed.

## 15. FOCUSED TEST RESULTS

DIRECT_EVIDENCE: `py_compile` on the attempted three files exited 0. Initial new test module run: 8 passed, 12 failed, exit 1, 18.95 s. Failure root: `AttributeError: 'RepositoryAnalysisState' object has no attribute 'resync_required'` at attempted `facade.py:1445`. Required regressions were not run after the STOP boundary. After removing the attempted implementation, `git diff --check` passed with no source/test changes.

## 16. POST-CHANGE MCP AUDIT

UNKNOWN: No modified source/test file remains for a post-change audit. Preflight Contextor revision 836 reported 16 fresh structural DFS back-edge cycles. No loaded-code adoption claim is made.

## 17. FILES_CHANGED

NONE (source/test/docs). Only `walkthrough.md` was overwritten for this report.

## 18. FULL_DIFFS

ACTUAL_DIFF=DIFFS=NONE for source/test/docs.

## 19. CONTRACT_CONFLICTS

CONTRACT_CONFLICT — `ContextorFacade.analyze_project`, `contextor/core/api/facade.py`: requested literal `state.resync_required is False` assumes an attribute that normal `RepositoryAnalysisState` instances lack. Existing state contract uses optional dynamic attribute; existing caller accesses it via `getattr(..., False)`. The missing decision is how the new gate should interpret an absent resync flag. Without that decision, literal implementation breaks ordinary partial-opt-in FULL.

## 20. REMAINING UNKNOWN

UNKNOWN: Correct architect-approved absent-resync handling; genuine FULL partial receipt publication; coexistence and failure cases; active runtime adoption. No active user FULL/LIVE, restart, commit or push occurred.

## 21. FINAL IMPLEMENTER OBSERVATION

STOP — CONTRACT_CONFLICT. No source/test implementation remains. Await exact architect instruction.
