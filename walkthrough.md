# PRE-SPLIT FULL SUITE - 4 FAILURE CLOSURE

## FAILURE_1_ROOT_CAUSE

Classification: TEST_DRIFT

The test expected UPDATED after:

    valid source -> syntax-invalid source -> valid source

The authoritative incremental contract records the parse-invalid module in canonical per-module freshness state. The first subsequent valid parse is an explicit recovery transition and returns RECOVERED even when normal semantic update work also occurs.

Correction:

- changed only the expected status from UPDATED to RECOVERED;
- retained assertions proving the recovered symbol facts are current;
- production RECOVERED behavior was not changed.

## FAILURE_2_ROOT_CAUSE

Classification: FIXTURE_DRIFT

The retry-success fixture mocked connect() but provided no persisted endpoint identity and its fake client exposed no endpoint. The hardened contract requires:

- owner_token;
- authkey;
- repo_id;
- root_path;
- stable endpoint identity before and after retry.

Correction:

- fixture now uses the existing full-identity endpoint helper;
- fake client exposes the same endpoint;
- _read_endpoint returns that endpoint;
- canonical repository identity matches repo_id/root_path;
- connect_or_start remains forbidden.

Journal revision 42 remains unchanged after retry.

## FAILURE_3_ROOT_CAUSE

Classification: FIXTURE_DRIFT

The transient-owner fixture supplied PID/token only. The production gate correctly returned endpoint_identity_unverified because repo_id and root_path were absent.

Correction:

- fixture now provides full endpoint and repository identity;
- same identity plus live service PID still yields transient_connection_failure;
- removing endpoint metadata still yields no_live_service;
- PID-only semantics were not restored.

## FAILURE_4_ROOT_CAUSE

Classification: FIXTURE_DRIFT

Exact returned payload before correction:

    {
      "status": "unavailable",
      "reason": "Canonical LIVE dependency graph is unavailable. Run analyze_project first."
    }

Path:

    get_file_edit_context(mode="minimal")
    -> usable engine
    -> module freshness gate passes
    -> dependency_graph is None
    -> fail-closed unavailable return

layer_guard did not disappear from a valid full response. The fixture stopped before layer_guard construction because dependency_graph=None represents missing canonical graph, not a fresh graph with zero edges.

The public current-truth contract requires no-graph minimal context to fail closed; returning layer_guard together with fabricated zero dependency/test evidence would regress that contract.

Correction:

- the layer_guard fixture now supplies one shared fresh empty graph with hard_edges={} and soft_edges={};
- cached layer analytics remain unchanged;
- all layer_guard cases now exercise their intended branch;
- production code and unavailable gate were not changed.

## FILES_CHANGED

- C:\Temp\Contextor_Repo\tests\test_incremental_equivalence.py
- C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py
- C:\Temp\Contextor_Repo\walkthrough.md

No production file changed in this closure.

## TARGETED_RESULT

Command:

    python -m pytest -q +      tests/test_incremental_equivalence.py::test_incremental_successful_modify_after_failed_modify +      tests/test_live_e2e_corrections.py::test_live_events_retries_same_owner_and_preserves_journal +      tests/test_live_e2e_corrections.py::test_live_events_distinguishes_transient_owner_from_absence +      tests/test_mcp_regressions.py::test_file_edit_context_layer_guard

Result:

- 4 passed
- 0 failed
- 1 third-party FastMCP/Authlib deprecation warning
- duration: 8.34s

The 748-test suite was not repeated.

## LIVE_VERIFICATION

- revision 858: test_incremental_equivalence.py UPDATED by desktop_watcher
- revision 859: test_live_e2e_corrections.py UPDATED by desktop_watcher
- revision 860: test_mcp_regressions.py UPDATED by desktop_watcher

## CONTEXTOR_POST_CHANGE_AUDIT

- recovery contract remains RECOVERED for parse-invalid -> valid;
- owner identity remains exact and repository-bound, never PID-only;
- no-graph file-edit context remains fail-closed;
- layer_guard remains available for usable graph plus fresh cached analytics;
- production implementations and consumers are unchanged;
- no scope leakage into structural split.

## FINAL_VERDICT

PRE_SPLIT_FAILURES_CLOSED
