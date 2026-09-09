BASELINE_LIVE=
HEALTHY.

Contextor MCP \`get_live_events\` before the first pytest batch:
- LIVE reachable: YES (\`status=ok\`)
- canonical/live revision: 446
- activity/runtime epoch: \`4b987d9a613a4b628eee87c848e05298\`
- service/runtime identity: not exposed by the public MCP response; not inferred
- resync_required: false; resync_reason: null
- activity_resync_required: false
- latest_seq: 57

BATCHES_TESTED=
1. \`tests/live_state/\`
   - pytest: 43 passed in 42.19s.
   - The runner printed all tests before a short delayed process exit; it then exited 0. This was not treated as a LIVE failure.
   - LIVE after: reachable YES; revision 446; epoch unchanged; resync_required=false; latest_seq 59.

2. \`tests/test_runtime_trace.py tests/test_runtime_authority_events.py\`
   - pytest: 46 passed in 33.09s.
   - LIVE after: reachable YES; revision 446; epoch unchanged; resync_required=false; latest_seq 60.

3. \`tests/test_live_state_ipc.py\`
   - pytest: 53 passed, 1 permitted external FastMCP/Authlib deprecation warning, 76.07s.
   - LIVE after: reachable YES; revision 446; epoch unchanged; resync_required=false; latest_seq 61.

4. \`tests/test_live_authority_bootstrap.py tests/test_live_e2e_corrections.py tests/test_live_job_object.py\`
   - pytest: 33 passed, 1 failed, 1 permitted external FastMCP/Authlib deprecation warning, 89.00s.
   - Ordinary test failure: \`test_real_windows_job_object_breakaway_integration\` received no \`HELPER_DONE\` line from its helper. This was not classified as a LIVE failure.
   - LIVE after: reachable YES; revision 446; epoch unchanged; resync_required=false; latest_seq 62.

5. \`tests/test_live_activity_status.py tests/test_live_desktop_integration.py tests/test_live_watcher_startup_reconciliation.py tests/test_gui_live_startup.py tests/test_gui_single_instance.py\`
   - pytest: 96 passed, 1 permitted external FastMCP/Authlib deprecation warning, 54.79s.
   - LIVE after: reachable YES; revision 446; epoch unchanged; resync_required=false; latest_seq 63.

6. Contextor-selected MCP/process-cleanup batch:
   \`tests/test_mcp_split_s2b.py tests/mcp/tools/test_analysis_status_concurrency.py tests/test_mcp_regressions.py tests/test_mcp_incremental_hydration.py tests/test_full_analysis_coordination.py tests/test_live_state_store.py\`
   - Selection basis: Contextor identifies \`get_live_events -> runtime\`, while \`analysis_jobs\` owns full-analysis/process coordination.
   - pytest: 125 passed, 6 failed, 2 warnings, 55.45s.
   - All six ordinary failures are in \`tests/test_full_analysis_coordination.py\`: its non-LIVE-marked lease tests attempted their test repository locks under the real per-user cache and got WinError 5 while creating unrelated \`...Contextor/cache/repo_*/runtime\` roots. One resulting thread warning came from the same failed isolated lease setup.
   - LIVE after: reachable YES; revision 446; epoch unchanged; resync_required=false; latest_seq 67.

BAD_BATCH=
NONE. Every completed batch left the MCP-oracle reachable with unchanged revision 446, unchanged activity/runtime epoch, and no resync requirement.

BISECTION_HISTORY=
NOT_STARTED: no BAD_BATCH exists. Per contract, no halves or order-dependent reduction were run.

MINIMAL_REPRO=
NONE FOUND in the permitted runtime/LIVE/GUI/MCP-process batches.

ORDER_DEPENDENT=
NOT ESTABLISHED. No selected batch caused the observed production LIVE violation, so there is no failing prefix to minimize.

LIVE_BEFORE=
reachable=YES; revision=446; activity_epoch=4b987d9a613a4b628eee87c848e05298; resync_required=false; service identity=not exposed by public MCP.

LIVE_AFTER=
reachable=YES; revision=446; activity_epoch=4b987d9a613a4b628eee87c848e05298; resync_required=false; service identity=not exposed by public MCP.

AUTHORITY_EVENTS=
The public mixed-event response remained available but its limited returned event list is ordered from the retained beginning, not a terminal authority-event tail. The authority lifecycle entries exposed in every oracle response were unchanged historical records from 2026-09-08:
- \`RUNTIME_AUTHORITY_START\`
- \`RUNTIME_LEASE_ACQUIRE\`
- \`RUNTIME_LEASE_TAKEOVER_REJECT\` (UNKNOWN; refused connection)
- \`RUNTIME_AUTHORITY_BOOTSTRAP_FAIL\`
- \`RUNTIME_AUTHORITY_START\`

No new authority lifecycle event, runtime-identity change, revision discontinuity, or resync signal was exposed after any batch. \`latest_seq\` incremented from 57 to 67, consistent with MCP activity; this alone is not an authority mutation.

CLASSIFICATION=
NO_BAD_BATCH_REPRODUCED_IN_RUNTIME_LIVE_GUI_MCP_PROCESS_SLICE.

FILES_CHANGED=NONE
DIFFS=NONE

