# CONTEXTOR P1D3-D2B-EXIT-GATE — read-only certification audit

## 1. EXECUTIVE OBSERVATION

DIRECT_EVIDENCE: Read-only D2B exit audit performed. Global suite was not run because safety of the complete test collection was not established. A reviewed, isolated 13-module subset passed 540 tests, with one platform skip. No architectural GO is declared.

## 2. INITIAL / FINAL HEAD

DIRECT_EVIDENCE: Initial and final HEAD `d4c1e56f2b935bcf0a1eaf45c4dab5212939f8e8`.

## 3. INITIAL / FINAL WORKTREE

DIRECT_EVIDENCE: Initial `git status --short` was clean. After tests, source/test worktree remained clean. Only this `walkthrough.md` report was rewritten.

## 4. D2B-7 BASELINE VERIFICATION

CODE_PATH_PROVED: `contextor/core/symbol_engine/indexer.py:81` has `IMPORT_CLASSIFICATION_SEMANTICS_VERSION = 9`; lines 20-24 import `SOURCE_SUFFIXES`; lines 88-94 derive `_ALTERNATIVE_SOURCE_SUFFIXES`; lines 2490-2527 use one `root_path.rglob("*")`, preserve the `.py` branch, and set `unindexed_import_artifacts_present` for real alternative-source/binary artifacts and directory symlinks. Lines 2606-2613 reuse the global `project_effects_closed` veto. No ordinary `__pycache__` exemption occurs in the discovery branch. `original_worker_capture_status` remains `ALL_SELECTED_CAPTURED_NON_ATOMIC` (`indexer.py:1642`); planner READY remains `READY_FOR_REINDEX_NON_ATOMIC` (`original_worker_reindex_planning.py:22`). `generation_manifest.py:26` defines `cycle-source-manifest/2`; `publication_binding.py:26` defines `cycle-prepared-co-publication/2` and retains explicit v1 legacy identifiers at lines 28-29.

## 5. TEST SAFETY PREFLIGHT

DIRECT_EVIDENCE: `pyproject.toml:32-40` discovers all `tests/test_*.py` and defines only `live` marker. `tests/conftest.py:16-30` redirects cache/state/output only when a test requests `isolated_dirs`; lines 33-46 redirect those roots for `live`-marked tests; lines 48-53 redirect only the central registry for other tests. The collection contains 261 Python files. Tests such as `tests/test_live_job_object.py:196-275` spawn and terminate separate LIVE processes; `tests/test_live_state_ipc.py:2788` exercises connect-or-start. These examples use temporary roots, but their presence and the conditional fixture do not prove isolation for every collected test. UNKNOWN: every global test's external side effects have not been exhaustively audited. The full suite therefore failed the safety preflight for indiscriminate execution. Clearly isolated selected modules use `tmp_path`, `isolated_dirs`, local CanonicalLiveServer fixtures, or monkeypatched runtime, as inspected before execution. No active Contextor FULL, LIVE publication, service restart, or elevated privilege request was performed.

## 6. GLOBAL REGRESSION RESULTS

UNKNOWN: The exact global command `.\.venv\Scripts\python.exe -m pytest -q -rs` was not executed because complete-suite isolation was unverified. Global passed/failed/skipped/error counts, duration, and global failure taxonomy are UNKNOWN. The 540-pass selected result is not labeled global.

## 7. DOWNSTREAM INTEGRATION RESULTS

DIRECT_EVIDENCE: Selected 13-module suite passed 540, skipped 1, failed 0, errors 0 in pytest 138.65 s (outer PowerShell stopwatch 140.9179735 s), exit 0. Executed modules: `tests/test_p1d3_d2b2_type_only.py`, `tests/test_p1d3_package_cycle_integration.py`, `tests/test_cycle_semantics_full_integration.py`, `tests/test_cycle_semantics_publication_live_integration.py`, `tests/test_original_worker_official_full_live_publication.py`, `tests/live_state/test_installed_cycle_generation_gate.py`, `tests/mcp/tools/test_get_project_architecture_full_reports.py`, `tests/test_cycle_semantics_invalidation.py`, `tests/test_cycle_semantics_registered_store_binding.py`, `tests/test_cycle_semantics_publication_binding.py`, `tests/test_original_worker_reindex_planning.py`, `tests/test_original_worker_manifest_preparation.py`, `tests/test_original_worker_full_to_live_receipt.py`. These cover the named FULL, incremental, LIVE, installed-generation, MCP, graph, source capture, cache, manifest, receipt and historical report pathways within isolated fixtures. Aggregate success does not establish arbitrary Python runtime safety.

## 8. P0/P1B INVARIANTS

CONTRACT_PROVED: The selected P1D3 integration and original-worker modules passed the existing P0/P1B fail-closed assertions, source SHA binding and original-worker non-atomic limitations. CODE_PATH_PROVED: Existing source capture and planner statuses explicitly retain `NON_ATOMIC`; no P0/P1B source or contract was edited.

## 9. MANIFEST V2

CODE_PATH_PROVED: `MANIFEST_VERSION = "cycle-source-manifest/2"` in `generation_manifest.py:26`. CONTRACT_PROVED: Selected original-worker manifest preparation and publication-binding tests passed. This is declaration/consistency evidence, not general source-byte or runtime-safety certification.

## 10. RECEIPT V2

CODE_PATH_PROVED: `PUBLICATION_BINDING_VERSION = "cycle-prepared-co-publication/2"` in `publication_binding.py:26`; receipt dataclass is at lines 40-49; `verify_co_published_cycle_manifest` is at line 301. CONTRACT_PROVED: Selected binding, FULL-to-LIVE receipt, and official isolated publication tests passed. The source states that the receipt attests co-publication of claims, not source-byte provenance or runtime safety.

## 11. FULL / INCREMENTAL / LIVE CONTRACTS

CONTRACT_PROVED: Selected isolated FULL materialization, incremental invalidation, local CanonicalLiveServer publication, official isolated FULL-to-LIVE, and installed-generation gate modules passed. `test_cycle_semantics_full_integration.py` uses a `tmp_path` repository plus `isolated_dirs`; publication integration uses a local server/store; official FULL test uses isolated repository identity, local server endpoint and monkeypatched connect. UNKNOWN: active Desktop/MCP service and installed loaded code were not inspected or exercised; isolated publication is not active LIVE adoption.

## 12. MCP PROJECTION CONTRACTS

CONTRACT_PROVED: Selected `tests/mcp/tools/test_get_project_architecture_full_reports.py` passed; its fixtures install temporary JSON reports and monkeypatch runtime. Existing tests explicitly assert historical-only report metadata, stale/resync separation, unsupported-schema failure, and newer-LIVE versus historical-report distinction. No active MCP report was mutated.

## 13. FAILURES AND ROOT CAUSES

DIRECT_EVIDENCE: Selected suite had zero failed tests and zero collection/runtime errors. UNKNOWN: no conclusion about failures in the unrun global suite. One non-failing AuthlibDeprecationWarning came from `.venv/lib/site-packages/fastmcp/server/auth/providers/jwt.py:10` and mentions deprecated `authlib.jose`; no root-cause classification beyond the warning text is asserted.

## 14. SKIPS AND PLATFORM LIMITATIONS

DIRECT_EVIDENCE: One skip at `tests/test_p1d3_d2b2_type_only.py:973`: `directory symlink unavailable: [WinError 1314] A required privilege is not held by the client`, while linking the temporary `symlink-target` to temporary `repo/linked`. The symlink contract remains unverified in this run. No privileges or Windows developer settings were changed.

## 15. EXACT COMMANDS / EXIT CODES

DIRECT_EVIDENCE: Read-only preflight included `git rev-parse HEAD`, `git status --short`, Contextor `get_mcp_documentation` and `get_file_edit_context`, `rg`, and `Get-Content`; all returned successfully. Executed test command (exit 0):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs tests/test_p1d3_d2b2_type_only.py tests/test_p1d3_package_cycle_integration.py tests/test_cycle_semantics_full_integration.py tests/test_cycle_semantics_publication_live_integration.py tests/test_original_worker_official_full_live_publication.py tests/live_state/test_installed_cycle_generation_gate.py tests/mcp/tools/test_get_project_architecture_full_reports.py tests/test_cycle_semantics_invalidation.py tests/test_cycle_semantics_registered_store_binding.py tests/test_cycle_semantics_publication_binding.py tests/test_original_worker_reindex_planning.py tests/test_original_worker_manifest_preparation.py tests/test_original_worker_full_to_live_receipt.py
```

DIRECT_EVIDENCE: `540 passed, 1 skipped, 1 warning in 138.65s`; outer duration 140.9179735 s. The global `pytest -q -rs` command was not run.

## 16. FILES_CHANGED

FILES_CHANGED=NONE for production/test/docs. Only permitted report `walkthrough.md` was rewritten.

## 17. ACTUAL_DIFF

ACTUAL_DIFF=NONE for production/test/docs, per report convention. `walkthrough.md` is excluded from changed-file inventory.

## 18. CONTRACT_CONFLICTS

DIRECT_EVIDENCE: No contract conflict observed in the selected suite. UNKNOWN: unrun global suite may expose additional conflicts.

## 19. REMAINING UNKNOWN

UNKNOWN: Global suite coverage and outcomes; skipped directory-symlink behavior on this Windows account; active installed-code adoption; cross-file atomicity beyond the stated non-atomic contracts; arbitrary import hooks and dynamic imports; runtime state outside the restricted model; resource and scale limits. No item is promoted to proven by the selected suite.

## 20. FINAL IMPLEMENTER OBSERVATION

DIRECT_EVIDENCE: D2B-7 source baseline present, selected downstream tests passed, global safety preflight did not justify running all tests. Read-only audit stops here. Architectural acceptance remains with ChatGPT.
