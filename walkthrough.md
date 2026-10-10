# L32G_FINAL_COMBINED_REGRESSION_GATE

## COMBINED_TEST_RESULT

Command (repository .venv Python; exactly the 13 requested files):
    & .\.venv\Scripts\python.exe -m pytest -q tests/mcp/tools/test_lineage_freshness.py tests/mcp/tools/test_contextor_fact_lineage.py tests/mcp/tools/test_get_module_blast_radius.py tests/mcp/tools/test_get_project_architecture_full_reports.py tests/mcp/tools/test_get_source_range_direct_lookup.py tests/test_module_usage_reuse.py tests/test_canonical_state_contract.py tests/test_reporting_single_file.py tests/analysis/test_lineage_live_query.py tests/test_live_e2e_corrections.py tests/test_refresh_plan_execution.py tests/test_syntax_diagnostics_full_analysis.py tests/test_live_state_ipc.py

Result: 423 passed, 1 warning in 134.59s. Warning only: installed fastmcp dependency emits AuthlibDeprecationWarning for authlib.jose. No failed node or traceback.

## CONTRACT_MATRIX

Classifications: PROVED_SAFE means source plus targeted regression evidence; CODE_PATH_PROVED means source deterministically emits the described value but LIVE did not contain the malformed state; UNKNOWN means the requested interaction is not directly covered and available source evidence does not establish the complete contract.

| Contract | Evidence and result |
|---|---|
| 1. Malformed public derived-family markers are not emitted as fresh | PROVED_SAFE for topology, artifact_consumption, cycles, collisions, and lineage. build_state_freshness normalizes derived markers against their allowed sets; malformed values become unavailable. Tests cover None, unknown strings, bool, int, list and dict, plus legal states and missing-attribute defaults. See query_helpers.py:322-526 and tests/mcp/tools/test_lineage_freshness.py. Exception/gap: aggregate families.module below. |
| 2. Invalid module parse metadata is unavailable/untrusted | PROVED_SAFE when evaluated for a specific module. module_current_truth accepts only dict entries with exact str state fresh or stale; unknown/bad types and non-dict whole maps yield unavailable/untrusted. Missing map attribute and missing module entry retain the legacy current/fresh contract. Targeted projections and lineage checks use that truth. Aggregate envelopes without target_module have the false-fresh path below. |
| 3. Valid parse-stale modules retain LKG | PROVED_SAFE for intentional lineage selection. Exact stale entry returns available=false, state=stale, provenance=last_known_good and parse-failure details. query_live_symbol_lineage blocks unavailable, not stale, and returns selected facts with stale/LKG freshness. Tests cover stale direct modules and package __init__ alias. Other public consumers may return an explicit stale response rather than facts; LKG is consumer-specific. |
| 4. Untrusted requested module, resolved target, alias and package __init__ expose no selected lineage facts | PROVED_SAFE. query_live_symbol_lineage gates requested module, existing requested package __init__, and resolved target before selected facts. Its global resync branch returns unavailable before resolution. Tests include requested/resolved module, alias/origin, package init, nested package init, valid fresh/stale alias, unrelated malformed package, and resync cases. |
| 5. Malformed whole parse-freshness map cannot be coerced to empty during COW | PROVED_SAFE. _prepare_candidate_state checks the raw attribute is a dict before candidate creation and copies that dict directly; it no longer applies dict(raw_parse_freshness or {}). It raises before candidate publication. Tests cover falsey malformed maps, truthy non-dict maps, valid/missing legacy maps and preservation. |
| 6. Syntax failure cannot promote an invalid target marker to LKG | PROVED_SAFE. mark_module_parse_failure calls module_current_truth and raises for unavailable target truth before writing stale metadata. Syntax-failure and malformed-map regressions pass. |
| 7. Verified parse recovery is target-local | PROVED_SAFE within targeted coverage. Successful update records verified target recovery while preserving unrelated parse metadata; syntax-failure then valid-parse recovery and valid current/stale state are covered. |
| 8. Invalid candidate publication preserves prior canonical state, revision and snapshot | PROVED_SAFE by candidate-validation-before-publication and targeted atomicity/persistence regressions. The suite includes malformed hydrated state, rejected syntax mutation, prior-generation persistence, and canonical structural clone/persist-before-exposure checks. |
| 9. No unintended mutation of unrelated modules | PROVED_SAFE in tested COW/update cases. Candidate map is a detached top-level dict; entries are retained as entries, and tests assert unrelated malformed entry identity/content remains. Canonical top-level state is not mutated on rejected candidate. |
| 10. Global resync stays fail-closed | PROVED_SAFE for selected facts and diagnostic/collision paths: lineage exits unavailable before resolving; diagnostics projection marks unavailable/stale counts; public module/source projections reject resync. Targeted global-resync tests pass. Note: aggregate families.module may remain fresh, as detailed below, although enclosing canonical_state/result is stale or unavailable. |

## LKG_AND_UNTRUSTED_SEPARATION

Literal module truth contract from C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:227-269:

    if freshness is missing:
        freshness = {}

    entry = freshness.get(module_name, missing) if isinstance(freshness, dict) else None

    if entry is missing:
        return {"available": True, "state": "fresh", "provenance": "current"}

    if (
        not isinstance(entry, dict)
        or type(entry.get("state")) is not str
        or entry["state"] not in {"fresh", "stale"}
    ):
        return {
            "available": False,
            "state": "unavailable",
            "provenance": "untrusted",
            "reason": "Canonical module parse freshness metadata is invalid or untrusted.",
        }

    if entry["state"] == "fresh":
        return {"available": True, "state": "fresh", "provenance": "current"}

    return {
        "available": False,
        "state": "stale",
        "provenance": "last_known_good",
        "reason": "Current source could not be parsed; canonical facts are last-known-good.",
        "parse_failure": {
            key: entry.get(key)
            for key in ("error", "line_number", "column_number")
            if entry.get(key) is not None
        },
    }

Missing map attribute and missing per-module entry are intentionally legacy-fresh. A present non-dict map produces entry=None and therefore unavailable/untrusted. Individual None, non-dict, missing state, non-string state, and unknown state are unavailable/untrusted.

## COW_FALSE_FRESH_GATE

C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:681-765 validates raw module_parse_freshness before copying. The current guard raises ValueError with “Canonical module_parse_freshness is invalid; fresh full analysis is required.” The candidate copy is based on dict(raw_parse_freshness), not dict(raw_parse_freshness or {}). C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:272-296 similarly refuses to mark a malformed target stale. Exact tests include:

- tests/test_refresh_plan_execution.py::test_prepare_candidate_state_rejects_malformed_parse_freshness_maps
- tests/test_refresh_plan_execution.py::test_prepare_candidate_state_preserves_legacy_and_valid_parse_freshness_cow
- tests/test_live_e2e_corrections.py::test_syntax_failure_rejects_malformed_whole_parse_freshness_map
- tests/test_live_e2e_corrections.py::test_syntax_failure_does_not_promote_untrusted_target_entry_to_lkg
- tests/test_live_e2e_corrections.py::test_semantic_noop_rejects_malformed_parse_freshness_map
- tests/test_live_e2e_corrections.py::test_updated_and_deleted_candidates_reject_malformed_parse_freshness
- tests/test_live_e2e_corrections.py::test_successful_update_preserves_unrelated_malformed_parse_entry
- tests/test_live_e2e_corrections.py::test_early_unchanged_keeps_untrusted_target_marker_without_parsing
- tests/test_live_e2e_corrections.py::test_malformed_snapshot_map_rejects_hydrated_syntax_update
- tests/test_syntax_diagnostics_full_analysis.py::test_live_mutation_job_failure_preserves_malformed_parse_freshness_atomically

## LIVE_ATOMICITY_GATE

Contextor LIVE summary observed canonical_state=fresh, provenance=live, canonical_revision=184, resync_required=false, parse_stale_modules empty. get_live_events(after_revision=184) reported revision/latest_revision=184, continuity=continuous, resync_required=false, and zero events. This is a healthy-state observation; it does not demonstrate malformed-state runtime reachability or prove a serving-process reload.

Candidate failure paths are source-proved to raise before candidate publication. Targeted persistence/IPC tests passed, including tests/test_live_state_ipc.py::test_persister_runs_after_validation_before_canonical_exposure, test_persistence_conflict_fails_closed_without_live_event, and the real adapter/persister predecessor-generation tests. The malformed-snapshot and syntax-mutation atomicity cases also passed. No runtime state was deliberately corrupted.

## SOURCE_SYNC_STATUS

Contextor complete symbol retrievals for the audited owners returned workspace_sync=verified at LIVE revision 184 and no preview/truncation for fetched implementations. Owners fetched completely included state_manager.py, plan_executor.py, query_helpers.py, live_query.py, diagnostics.py, diagnostics_projection.py, get_project_architecture.py, contextor_fact_lineage.py, get_module_blast_radius.py, and get_source_range.py.

The unscoped get_project_architecture LIVE envelope reports workspace_sync=unverified; its documentation describes that envelope as current global state rather than target-file hash verification. This is distinct from Contextor per-source retrieval synchronization. No source/retrieval mismatch was reported for the fetched owners.

## RUNTIME_CERTIFICATION_STATUS

NOT CERTIFIED. LIVE authority was fresh at revision 184 and the event cursor was continuous, but this does not prove the existing MCP or Desktop processes reloaded current working-tree Python modules. No restart or update_file was performed.

## MANUAL_RESTART_BOUNDARIES

If runtime certification is later required, the Python process serving MCP/LIVE imports is one boundary. The Desktop watcher/application process is a separate boundary if it retains its own imported code. No process was restarted in this task.

## REMAINING_BLOCKERS

1. CODE_PATH_PROVED — aggregate module family can be falsely presented as fresh when parse truth is malformed:
   - C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py:465-468 sets families.module to module_current_truth only when target_module is supplied; otherwise it writes literal fresh.
   - C:\Temp\Contextor_Repo\contextor\mcp\tools\get_project_architecture.py:189-194 calls build_state_freshness without target_module. At lines 209-239 it detects untrusted per-module truth and changes canonical_state to unavailable, but does not change families.module. The existing regression checks parse_stale_modules and canonical_state but not families.module. The public live_state envelope can therefore combine canonical_state=unavailable with families.module=fresh for a malformed module entry. Existing parse-stale entries likewise do not alter that aggregate marker.
   - C:\Temp\Contextor_Repo\contextor\mcp\tools\contextor_fact_lineage.py:655-707 also calls build_state_freshness without target_module. _coverage counts malformed module truth as stale_module_count and _family_gate returns partial for symbol_calls, while _freshness adds the queried family/module_usages marker without downgrading canonical_state or families.module. The existing test asserts partial and stale_module_count but not freshness.canonical_state or freshness.families.module. This is a public status/freshness contradiction in the deterministic code path, not an observed malformed LIVE runtime.
   - Classification is CODE_PATH_PROVED; current LIVE itself contained no malformed entry.

2. UNKNOWN — syntax_diagnostics_for_path in C:\Temp\Contextor_Repo\contextor\mcp\diagnostics.py:17-92 gates on resync_required and syntax_diagnostics_state/facts, not module_current_truth. Public get_file_edit_context call sites at lines 242, 406, 461 and 600 are preceded by per-module module_truth_unavailable checks in the inspected paths. No requested targeted regression combines malformed module_parse_freshness with a fresh syntax family fact and inspects the final public syntax diagnostic response. Whether the family-scoped syntax fact is independently authoritative in that combination is not proved here.

3. Runtime certification remains unavailable without the prohibited MCP/LIVE/Desktop reload. Targeted pytest results certify fresh test processes only.

No failing tests. The contract gap above prevents an all-contract PASS verdict.

## FILES_CHANGED

- C:\Temp\Contextor_Repo\walkthrough.md — this report only.
- No production, test, or documentation files changed by this task.
- Before writing this report, post-test git status and source/test diffs were empty. Final status contains only walkthrough.md. git diff --check reported no whitespace errors; Git emitted only its LF-to-CRLF normalization warning for walkthrough.md.

## ACTUAL_DIFF

FULL_DIFFS=NONE for production/test files. No source or test file changed in this task. The report file is excluded from its own diff.

## FINAL_VERDICT

BLOCKED_CONTRACT_AUDIT — all 13 requested targeted files pass (423 passed), compile-in-memory succeeded for 10 audited Python owners, and no source/test changes occurred. A deterministic public false-fresh code path remains in unscoped families.module projections for get_project_architecture and contextor_fact_lineage. No implementation or patch design was performed.


