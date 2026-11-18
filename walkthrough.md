# SP-DIAG-M1 — Malformed Cycle Marker Fail-Closed

## PREFLIGHT

- DIRECT_EVIDENCE — HEAD before edit: 74a3b0a23e962033aeaaf3555031f0090be11997; branch main...origin/main. git status was clean.
- DIRECT_EVIDENCE — pre-change LIVE: canonical revision 1435, provenance live, canonical_state fresh, resync_required=false.
- DIRECT_EVIDENCE — target file context at revision 1435: workspace_sync=verified; syntax diagnostics were checked_and_none with errors=[].
- DIRECT_EVIDENCE — Contextor resolved _soft_dependent_cycle_diagnostic from the current LIVE source at lines 22-62. The exact requested anchor matched at lines 36-44; no source drift.
- DIRECT_EVIDENCE — actual pre-edit scope was one replacement inside _soft_dependent_cycle_diagnostic: guard set membership with the exact built-in str type check requested. No test file changes.
- DIRECT_EVIDENCE — repository virtual environment interpreter is CPython 3.15.2.

## ROOT_CAUSE

- CODE_PATH_PROVED — after rejecting cycles_state == "fresh", the prior code evaluated cycle_state membership in a set of string markers before returning the unavailable projection.
- DIRECT_EVIDENCE — the selected test's INVALID_MARKERS includes [] and {}; its parametrized cycle-family case carries a cycles payload and expects malformed markers to project as unavailable.
- INFERENCE — Python set membership hashes the candidate value. For list and dict markers, the membership expression raises TypeError before the intended unavailable return. The pre-change behavior was established from the source path and Python semantics; no pre-patch test run was performed.

## EXACT_PATCH

- DIRECT_EVIDENCE — replaced only the requested availability expression in contextor/core/diagnostics_projection.py.
- CODE_PATH_PROVED — set membership now runs only when type(cycle_state) is str; otherwise the availability falls back to unavailable.
- DIRECT_EVIDENCE — no tests or other source files were modified. The patch does not change the fresh-cycle projection or other diagnostic families.

## FAIL_CLOSED_BEHAVIOR

- CODE_PATH_PROVED — for non-fresh non-string markers, the short-circuit type condition avoids set membership and returns the existing unavailable mapping, including count=None, components=None, and runtime_execution_proven=False.
- DIRECT_EVIDENCE — the targeted parameterized tests include unhashable list and dict markers and passed for the cycle diagnostic family.
- DIRECT_EVIDENCE — exact string markers stale, deferred, and unavailable retain the existing availability mapping; fresh remains on the existing path.
- INFERENCE / REVIEW NOTE — the exact requested type(cycle_state) is str guard rejects str subclasses even when their value equals a recognized marker. Whether such subclasses are valid state markers is UNKNOWN; the requested patch explicitly requires exact type identity.
- UNKNOWN / SCOPE LIMIT — cycle_state != "fresh" is evaluated before the new type guard. The tested built-in unhashable markers compare safely, but this change does not establish behavior for custom objects whose equality operation raises or returns a non-boolean value. No evidence in this task shows such objects are produced as cycles_state.

## TARGETED_TESTS

- DIRECT_EVIDENCE — ran the exact requested selector from the repository virtual environment on CPython 3.15.2:
  python -m pytest -q tests/test_mcp_diagnostics.py -k "malformed_collision_or_cycle_marker_never_certifies_payload or malformed_syntax_marker_never_materializes_facts or name_collision_tool_normalizes_malformed_marker or missing_markers_with_payload_do_not_certify_diagnostics"
- DIRECT_EVIDENCE — result: 33 passed, 32 deselected, 2 dependency deprecation warnings, in 3.71s.
- DIRECT_EVIDENCE — no full pytest suite was run.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE — canonical LIVE revision 1436, provenance live, canonical_state fresh, resync_required=false.
- DIRECT_EVIDENCE — revision 1436 event: desktop_watcher update_file UPDATED for contextor/core/diagnostics_projection.py; event continuity from revision 1435 was continuous.
- DIRECT_EVIDENCE — target file workspace_sync=verified at revision 1436.
- DIRECT_EVIDENCE — target syntax diagnostics are checked_and_none, materialized=true, errors=[]; global syntax diagnostic count is 0 and fresh.
- DIRECT_EVIDENCE — graph and cycles remain fresh.
- UNKNOWN — workspace synchronization confirms disk-to-LIVE source freshness, not that a running process adopted this code. Runtime adoption was not inspected. No restart or MCP update_file was performed.

## FINAL_VERDICT

DIAG_M1_PASS

The requested exact guard is present, the focused malformed-marker selector passed, and the target file is synchronized and syntax-clean in LIVE. This verdict is limited to the specified projection guard and test selection; it is not evidence of runtime process adoption or behavior for arbitrary custom equality implementations.

## FILES_CHANGED

- contextor/core/diagnostics_projection.py

walkthrough.md was overwritten as the required report artifact and is not counted as an implementation file. No test file changed.

## FULL_DIFFS

The following is the complete changed-line diff from git diff --unified=0 for the sole implementation file.

### contextor/core/diagnostics_projection.py

~~~~diff
diff --git a/contextor/core/diagnostics_projection.py b/contextor/core/diagnostics_projection.py
index 4c2e34c..6c20280 100644
--- a/contextor/core/diagnostics_projection.py
+++ b/contextor/core/diagnostics_projection.py
@@ -39,3 +39,7 @@ def _soft_dependent_cycle_diagnostic(state: Any) -> dict[str, Any]:
-        availability = cycle_state if cycle_state in {
-            "stale", "deferred", "unavailable",
-        } else "unavailable"
+        availability = (
+            cycle_state
+            if type(cycle_state) is str and cycle_state in {
+                "stale", "deferred", "unavailable",
+            }
+            else "unavailable"
+        )
~~~~
