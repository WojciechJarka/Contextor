# CONTEXTOR_P1D2M_FINAL_CYCLE_SEMANTICS_ACCEPTANCE

## PREFLIGHT_RESULT

DIRECT_EVIDENCE: HEAD `94f2588f9f4580ac2232329c30d7e675537a1f83`; initial worktree clean. This stage is read-only for source, tests, configuration, active repository analysis and active LIVE. Reviewed the P1D2L report in `HEAD:walkthrough.md`: 6/6 new tests and 255/255 focused regression tests passed. These are isolated focused results, not a repository-wide suite pass. This stage ran only two existing isolated package-fixture tests: `python -m pytest -q tests/test_original_worker_full_preparation_optin.py::test_p1d2f_t03_unsupported_package_full_fails_closed tests/test_original_worker_full_receipt_optin.py::test_p1d2i_t06_unsupported_package_not_published` -> 2 passed in 5.63s. No active-repository FULL or active LIVE connection occurred.

## P1D2_INTEGRATION_PATH_REVIEW

| Claim | Evidence and classification | Limit |
|---|---|---|
| A. Ordinary FULL requests no cycle receipt | CODE_PATH_PROVED: both flags default to `False` in `contextor/core/api/facade.py:558-568`; manifest forwarding is conditional at 1384-1420. CONTRACT_PROVED: `tests/test_original_worker_full_receipt_optin.py:93-113` (T01). | Ordinary FULL can still publish the canonical snapshot through the official queue. |
| B. Preview-only requests no receipt | CODE_PATH_PROVED: the second opt-in is required at `facade.py:596-609`, and the store kwarg is omitted at 1384-1420. CONTRACT_PROVED: P1D2I T02 (`tests/test_original_worker_full_receipt_optin.py:115-131`) and P1D2L T02 (`tests/test_original_worker_official_full_live_publication.py:257-306`). | Preview is non-atomic preparation only. |
| C. Both flags can prepare and co-publish | CODE_PATH_PROVED: `facade.py:874-983,1384-1432`; the manifest is forwarded only after status, freshness, graph and module-domain checks. CONTRACT_PROVED: P1D2I T03 and P1D2L T01. | Only supported, fully covered input can pass. |
| D. Store seals receipt | CODE_PATH_PROVED: `contextor/core/analysis/state_manager.py:525-576` forwards the optional manifest; `contextor/core/live_state/store.py:1507-1556,1743-1779,1909-1914` seals under its lock before metadata commit. `contextor/core/cycle_semantics/publication_binding.py:227-269` validates claims. CONTRACT_PROVED: P1D2H store tests (`tests/test_original_worker_store_handoff.py`). | `facade.py` never creates a receipt. |
| E. Receipt belongs to one generation | CODE_PATH_PROVED: receipt fields include revision/state_id/repo_id/root_path at `publication_binding.py:36-45`, verified at 272-306. CONTRACT_PROVED: P1D2I T03, P1D2J T01 and P1D2K T01. | Receipt authority is `COMMITTED_PREPARED_CLAIMS_NOT_SOURCE_CERTIFIED`, not source authentication. |
| F. FULL uses official queue after successful persistence | CODE_PATH_PROVED: `facade.py:1422-1490` imports `connect` after `meta` and calls `publish_committed_and_wait` with repo_id/state_id/revision/origin; `contextor/core/live_state/publication_receipt.py:98-190` submits, polls and checks authority. CONTRACT_PROVED: P1D2L T01/T03/T05/T06. | Isolated localhost server; active application adoption UNKNOWN. |
| G. LIVE installs durable committed generation | CODE_PATH_PROVED: `contextor/core/live_state/ipc.py:1357-1582,1960-1996` uses committed snapshot reader and mutation queue. CONTRACT_PROVED: P1D2J T01 (`tests/test_original_worker_full_to_live_receipt.py:111-156`), P1D2L T01 (`tests/test_original_worker_official_full_live_publication.py:185-255`). | Client-supplied source bytes are not an installation input. |
| H. LIVE verifies under owner lock | CODE_PATH_PROVED: `ipc.py:2337-2400` checks exact payload and calls `assess_live_installed_prepared_claims` inside `self._lock`; `contextor/core/cycle_semantics/live_installed_claims.py:35-209` checks owner, generation, graph and receipt. CONTRACT_PROVED: P1D2K T01/T03/T06. | The answer is lock-scoped at reply time, not a continuing lease or import-safety certificate. |
| I. Later generation drops old receipt | CODE_PATH_PROVED: `contextor/core/analysis/state_manager.py:147-165` clears on update and `store.py:1769-1779` clears inherited receipt without a new manifest. CONTRACT_PROVED: P1D2I T10, P1D2J T04/T05, P1D2K T04/T05, P1D2L T04. | No automatic carry-forward. |
| J. Invalid or stale receipt fails closed | CODE_PATH_PROVED: `store.py:2352-2372,2472-2491` validates on load; `live_installed_claims.py:150-192` rejects stale family, invalid receipt and graph mismatch. CONTRACT_PROVED: P1D2J T06, P1D2K T03/T04/T05/T06. | Does not authenticate source-byte owner. |

## MODEL_CAPABILITY_BOUNDARIES

CODE_PATH_PROVED: `contextor/core/cycle_semantics/initialization_model.py:44-95` compiles only top-level `ast.Import` with simple identifiers, absolute `ast.ImportFrom` with simple module/name and no star, single-name assignments of supported constants or simple `alias.attribute`, and `ast.Pass`. Dotted names such as `pkg.a`, relative imports, `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, calls, control flow and other statements return unsupported/UNKNOWN. `_declared_import_targets` at `contextor/core/cycle_semantics/scenarios.py:38-53` rejects relative, star and dotted targets. This is a deliberately limited abstract model; it never executes analyzed Python (`initialization_model.py:98-106`).

CODE_PATH_PROVED: `initialization_model.py:133-197` tracks each module as NEW/INITIALIZING/READY, binding sets, import aliases, and an iterative stack of statement positions. A read or from-import of a name absent from an INITIALIZING target yields `EARLY_BINDING_HAZARD`; absent after READY yields `MISSING_EXPORT`/`MISSING_ATTRIBUTE`. Missing module/source or unsupported syntax yields UNKNOWN.

CODE_PATH_PROVED: `scenarios.py:56-66,87-194` normalizes cyclic SCCs, adds all hard-edge reachable modules, requires their ASTs and exact graph/source import-target equality, checks 64 entry, 4096 top-level statement and 16384 AST-node bounds, then evaluates every SCC member as an entry. `MODEL_INTERNAL_EARLY_BINDING_HAZARD` requires an observed early-binding event internal to the SCC (164-173). `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` requires every member-entry evaluation to yield `MODEL_PASS` (174-175). Other outcomes become `INDETERMINATE`, with complete or partial entry coverage and reason (176-192). Existing model tests in `tests/test_cycle_semantics_initialization_model.py:34-152` and `tests/test_cycle_semantics_scenarios.py:18-179` cover the supported cases, hazards, unsupported syntax, closure, graph/source discrepancy and budgets.

CODE_PATH_PROVED: `contextor/core/cycle_semantics/evidence.py:74-308`, `source_proof.py:42-220` and `generation_manifest.py:57-173` require coherent index/graph/model evidence, recomputed source-byte SHA-256, parsed AST signatures and complete supported per-SCC classifications before a global manifest digest exists. `original_worker_preparation.py:37-161` turns incomplete inputs into `UNAVAILABLE` and a successful result into `PREPARED_UNPUBLISHED_NON_ATOMIC`. This establishes bounded consistency, not atomic source origin or Python execution safety.

DIRECT_EVIDENCE: `_flat_repo` in `tests/test_original_worker_full_preparation_optin.py:21-36` uses simple `a`/`b` imports and assignments and has positive P1D2F/P1D2I/P1D2L coverage. `_package_repo` at lines 39-54 uses `import pkg.b`, `import pkg.a` and module-level `FunctionDef`. Existing tests at lines 167-185 and `tests/test_original_worker_full_receipt_optin.py:220-240` assert `P1C0_SOURCE_EVIDENCE_UNAVAILABLE`, no manifest and no receipt. Both were rerun in P1D2M and passed. Thus ordinary package cycles of that shape are currently unsupported. Arbitrary module execution is not modeled, and a passing model scenario is not an import-execution safety proof.

## STRUCTURAL_PATHS_VS_CYCLIC_SCCS

CODE_PATH_PROVED: `contextor/core/graph/cycles.py:121-149,157-273` records DFS back-edge paths, deduplicates rotations and returns paths; it does not enumerate every simple cycle. `contextor/core/cycle_semantics/scc.py:28-131` normalizes the entire hard graph with an iterative SCC pass; a multi-node SCC or self-loop is one cyclic SCC. Many DFS paths can belong to one SCC. Model classification attaches to an SCC via `scenarios.py:105-194`, not to each DFS path. Therefore the 16 reported structural paths are not 16 independently classified semantic components.

## CONTEXTOR_OWN_CYCLE_EVIDENCE

DIRECT_EVIDENCE: Read-only `get_project_architecture(fields=[])` at canonical revision 693 reported `cycles.count=16`, cycles family `fresh`, cycle_semantics family `stale`, `resync_required=false`, global `workspace_sync=unverified`, and current `cycle_semantic_diagnostics.status=stale` with `cyclic_scc_count=null`. These are current canonical facts, but current per-SCC semantic classifications are unavailable.

DIRECT_EVIDENCE: `get_project_architecture(fields=["cycle_semantics"], cycle_semantics_view="overview")` returned a completed-analysis **historical** report generated 2026-10-26 12:46:38 for commit `5f8ebbfa1bbb919078932852abbc740f4f5662e5`, with `projection.summary.cyclic_scc_total=2` and 36 cyclic modules. One historical SCC contains 27 `contextor.core.*` modules and is labeled `ACYCLIC_DIRECT_SUBGRAPH_WITH_SINGLE_EDGE_CLOSURES`; another contains 9 `contextor.repo_generator.*`/`contextor.ui.*` modules and is labeled `UNGUARDED_DIRECT_CYCLIC_SUBGRAPH`. Both report `runtime_execution_status=UNKNOWN_NOT_EVALUATED`. The report's `publication_binding.status=UNVERIFIED_REPORT_VS_CANONICAL_LIVE`, with null revisions. These are structural/lexical diagnostic categories, **not** `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` or `MODEL_INTERNAL_EARLY_BINDING_HAZARD`. Current HEAD is different and current canonical cycle_semantics is stale. CURRENT distinct cyclic SCC count: UNKNOWN; current per-SCC model results: UNKNOWN; current missing-source/unsupported-syntax reasons per SCC: UNKNOWN. No FULL was run to change that.

## USER_VISIBLE_SEMANTIC_RESULT_PATH

The table tracks source-bound model claims, separately from the existing structural/lexical cycle report. `contextor/core/cycle_semantics/contracts.py:190-225` defines a snapshot of structural/lexical evidence, not scenario results. `contextor/core/cycle_semantics/public_projection.py:238-332` exports diagnostic categories. `contextor/core/cycle_semantics/report_projection.py:26-185` creates a historical report with null publication binding. `contextor/core/reporting_engine/pipeline.py:200-229,548-549` and `io_manager.py:153-167` write it. `contextor/mcp/tools/get_project_architecture.py:462-597` and `contextor/mcp/cycle_semantics_views.py:67-319,322-539` expose historical per-SCC projection plus a separate freshness-gated LIVE aggregate. No matching cycle-semantic presentation path was found in `contextor/ui/gui.py`.

| Requested field | MODEL | FULL RESULT | CANONICAL STATE | LIVE | DESKTOP / API / REPORT | Status |
|---|---|---|---|---|---|---|
| SCC membership | `scenarios.py:76-84`; manifest component `generation_manifest.py:40-53` | Preview attribute `facade.py:1053-1060` when opted in | Receipt contains manifest `publication_binding.py:36-45` | Installed verification returns digests, not members `live_installed_claims.py:194-209` | Historical report per-SCC `public_projection.py:238-287`; MCP overview/component selection `cycle_semantics_views.py:67-150` | AVAILABLE_AND_PROVED for historical structural SCC; current semantic SCC UNKNOWN |
| Model classification | `scenarios.py:164-192` | Opt-in preview manifest components | Persisted only inside optional receipt | Verification returns `model_claims_sha256`, not classification | Historical report exposes a different `diagnostic_category`, not model classification | AVAILABLE_BUT_NOT_END_TO_END_PROVED |
| Classification reason | Scenario `reason` at `scenarios.py:69-84,184-192` | Global preview `reason` in `original_worker_preparation.py:30-34`; prepared component reason is None | Receipt retains prepared component reason, not detailed model trace | No reason in positive verification | Historical diagnostic category/edges may explain structural/lexical result, not model reason | NOT_EXPOSED for source-bound model reason |
| Evidence coverage | Scenario `coverage` and source signatures | Preview manifest and source modules | `CycleSemanticsSnapshot.coverage_status`, receipt signatures | Verification returns source-manifest digest only | Historical report `semantic_evidence` and projection coverage; LIVE aggregate only if fresh | AVAILABLE_BUT_NOT_END_TO_END_PROVED for model coverage |
| Fresh/stale/deferred | Model result is not a LIVE freshness field | FULL local status | `state_manager.py:133-145` stores family state | LIVE aggregate freshness gate `cycle_semantics_views.py:354-455` | MCP report and independent LIVE overlay; current stale | AVAILABLE_AND_PROVED for family freshness, not per-SCC model freshness |
| Canonical generation identity | Not an AST/model property | FULL publication metadata `facade.py:1451-1480` | Receipt revision/state_id/repo/root `publication_binding.py:36-45` | Installed check returns revision/state_id and owner identity `live_installed_claims.py:194-209` | Historical report binding explicitly unverified `report_projection.py:142-151` | AVAILABLE_AND_PROVED through isolated LIVE verification; historical report unbound |
| Authority limitations | Model docs `initialization_model.py:102-106` | Prepared authority in manifest `generation_manifest.py:25-26` | Receipt authority `publication_binding.py:27-45` | Lock-scoped authority string `live_installed_claims.py:194-209` | Historical report indicates no runtime status and unverified binding `report_projection.py:142-164` | AVAILABLE_BUT_NOT_END_TO_END_PROVED as a unified user explanation |

No dataclass field alone is counted as end-user delivery. An API caller can retrieve a historical structural/lexical SCC projection, but a normal Desktop user is not shown a proven current source-bound model classification, reason and generation-bound explanation per SCC.

## FAIL_CLOSED_AND_RESOURCE_BOUNDS

| CONDITION | EXPECTED BEHAVIOR | IMPLEMENTATION EVIDENCE | TEST EVIDENCE | ACTUAL CONFIDENCE |
|---|---|---|---|---|
| More than 16 selected SCC-closure source files | UNAVAILABLE / `CLOSURE_MODULE_LIMIT` | `original_worker_binding.py:23-25,104-119`; `original_worker_reindex_planning.py:20,109-120`; `indexer.py:1067-1085` | `tests/test_original_worker_cycle_closure_binding.py:103-116`; `test_original_worker_reindex_planning.py:154-172` | CONTRACT_PROVED |
| Source file over 2 MiB | Capture/binding unavailable | `original_worker_binding.py:24,130-138`; `selective_worker_capture.py:33-34,138-157`; `indexer.py:1091` | Focused worker/binding tests exist; exact threshold case not re-run here | CODE_PATH_PROVED |
| Selected closure over 32 MiB | Capture/binding unavailable | `original_worker_binding.py:25,127-138`; `selective_worker_capture.py:34` | No new test in this stage | CODE_PATH_PROVED |
| SCC entry/statement/AST limits | INDETERMINATE | `scenarios.py:15-17,105-144` | `tests/test_cycle_semantics_scenarios.py:115-129,171-179` | CONTRACT_PROVED from existing tests |
| Missing/partial source, parse or digest mismatch | UNAVAILABLE or INDETERMINATE; no complete manifest | `original_worker_preparation.py:67-139`; `source_proof.py:125-208`; `generation_manifest.py:85-171` | P1D2C T03-T06, P1D2F T03, P1D2I T06 | CONTRACT_PROVED |
| Source changed between index passes | Reject reindex and manifest | `original_worker_reindex_planning.py:193-281` | `test_original_worker_reindex_planning.py:173-213`; P1D2I T08 | CONTRACT_PROVED |
| Unsupported AST, dotted/relative/star imports | UNKNOWN/INDETERMINATE, then no complete manifest | `initialization_model.py:44-95,122-131`; `scenarios.py:38-53,146-177` | `test_cycle_semantics_initialization_model.py:88-116`; package tests rerun here | CONTRACT_PROVED |
| Canonical revision/state mismatch | Reject receipt or installed verification | `publication_binding.py:227-306`; `live_installed_claims.py:140-148` | P1D2K T03/T04 | CONTRACT_PROVED |
| LIVE service/repository identity mismatch | UNAVAILABLE | `live_installed_claims.py:95-118`; `publication_receipt.py:108-118,175-188` | P1D2K T03; P1D2L T05 | CONTRACT_PROVED |
| Invalid manifest/store failure | No metadata commit and no next publication job | `store.py:1743-1779,1909-1914`; `facade.py:1450-1490` | P1D2I T09; P1D2L T03 | CONTRACT_PROVED |
| Later default FULL | New receipt-free generation | `store.py:1769-1779` | P1D2I T10; P1D2L T04 | CONTRACT_PROVED |
| Incremental update | Clear receipt before updater/persister | `state_manager.py:147-165`; `ipc.py:2027-2290` | P1D2J T05; P1D2K T05 | CONTRACT_PROVED |
| Stale or tampered durable receipt | Discard on load; do not resurrect in LIVE | `store.py:2352-2372,2472-2491`; `live_installed_claims.py:161-192` | P1D2J T06 | CONTRACT_PROVED |

## ACCEPTANCE_MATRIX

| Dimension | STATUS | EVIDENCE | LIMITATION |
|---|---|---|---|
| A. Structural cycle detection | PROVED | DIRECT_EVIDENCE: current canonical 16 fresh DFS paths; `graph/cycles.py:157-273`. | Paths are not all simple cycles or SCC count. |
| B. SCC normalization and identity | PROVED | CODE_PATH_PROVED: `cycle_semantics/scc.py:28-131`; `tests/test_cycle_semantics_scc.py`. | Current repository SCC count UNKNOWN because current semantic family is stale and no coherent full graph projection was obtained. |
| C. Supported semantic scenario evaluation | PROVED | CONTRACT_PROVED within narrow model: `initialization_model.py:44-197`, `scenarios.py:87-194`; model tests. | Only supported flat syntax, not arbitrary Python. |
| D. Source-byte / AST consistency | PROVED | CONTRACT_PROVED in isolated tests; `source_proof.py:42-220`, P1D2C manifest tests. | Consistency is non-atomic and caller-supplied. |
| E. Reindex graph/source coherence | PROVED | `original_worker_reindex_planning.py:158-287`; `tests/test_original_worker_reindex_planning.py`. | Does not prove repository-wide atomicity. |
| F. FULL opt-in manifest preparation | PROVED | P1D2F/P1D2I flat tests; `facade.py:874-983`. | Unsupported packages and >16 closure files fail closed. |
| G. Canonical generation co-publication | PROVED | P1D2H/P1D2I/P1D2J; `store.py:1743-1779`. | No original source-owner authentication. |
| H. Automatic LIVE publication through official queue | PROVED | P1D2L T01-T06; `facade.py:1451-1490`, `publication_receipt.py:98-190`. | Proved with isolated localhost service. |
| I. Installed LIVE generation verification | PROVED | P1D2K T01-T06; `ipc.py:2337-2400`, `live_installed_claims.py:35-209`. | Lock-scoped response only. |
| J. Incremental receipt invalidation | PROVED | P1D2J T05, P1D2K T05; `state_manager.py:147-165`. | No receipt inheritance. |
| K. Coverage of realistic Python package-import cycles | UNAVAILABLE | DIRECT_EVIDENCE: two package tests passed today with `P1C0_SOURCE_EVIDENCE_UNAVAILABLE`; fixture `tests/test_original_worker_full_preparation_optin.py:39-54`. | Dotted imports and FunctionDef unsupported. |
| L. Classification of Contextor's own structural cycles | UNKNOWN | DIRECT_EVIDENCE: current cycle_semantics stale, current count/classifications null; historical 2 SCC diagnostic categories only. | No fresh, generation-bound per-SCC model results. |
| M. User-visible semantic explanation per SCC | PARTIAL | Historical MCP report and LIVE aggregate at `get_project_architecture.py:462-597`, `cycle_semantics_views.py:67-319,322-539`. | Historical diagnostic category is not source-bound model classification; no proven Desktop per-SCC model explanation. |
| N. Active application adoption | UNKNOWN | Watcher/source reads and isolated tests only. | No loaded-code identity proof for active application. |
| O. Runtime import execution safety | UNAVAILABLE | `initialization_model.py:102-106`, `public_projection.py:289-305` explicitly limit authority. | No arbitrary Python execution or safety certification. |

## INTEGRATION_GO_NO_GO

`P1D2_INTEGRATION_PATH=GO` **for the opt-in mechanism under isolated tests**. CONTRACT_PROVED by P1D2I/J/K/L focused suites: preparation, store sealing, official queued publication, installation and lock-scoped verification work for supported flat fixtures. This verdict does not claim active application adoption or broad semantic coverage.

## GENERAL_SEMANTICS_GO_NO_GO

`GENERAL_SEMANTIC_CLASSIFICATION=NO_GO` for arbitrary real-world package import cycles. DIRECT_EVIDENCE: `_package_repo` with `pkg.a`/`pkg.b` and functions still returns `P1C0_SOURCE_EVIDENCE_UNAVAILABLE` in the two rerun tests. CODE_PATH_PROVED: dotted module names and FunctionDef are unsupported by `initialization_model.py:40-95` and `scenarios.py:38-53`.

## CONTEXTOR_OWN_CYCLES_GO_NO_GO

`CONTEXTOR_OWN_CYCLES=NO_GO` as an acceptance claim that every current distinct cyclic SCC has a semantic model result. DIRECT_EVIDENCE: 16 current structural DFS paths, current `cycle_semantics=stale`, current SCC count and per-SCC classifications null. The historical report's two SCC diagnostic categories are not current generation-bound model classifications. Actual current classifications remain UNKNOWN.

## KNOWN_LIMITATIONS

CODE_PATH_PROVED: 16-file selected closure, 2 MiB/file and 32 MiB/closure bounds; flat limited AST; non-atomic source capture; second-pass equality does not authenticate source origin; report projection is structural/lexical with historical publication binding; LIVE verification is one lock-scoped observation. The publication authority is `COMMITTED_PREPARED_CLAIMS_NOT_SOURCE_CERTIFIED` (`publication_binding.py:27-45`). Neither a prepared manifest nor a receipt certifies Python import safety.

## UNVERIFIED_ASSUMPTIONS

UNKNOWN: active application loaded-code adoption; current distinct cyclic SCC inventory; current model classification, reasons and source-coverage details for Contextor's own SCCs; a user-facing Desktop explanation path for per-SCC source-bound model results; repository-wide cross-file atomicity; authenticated original worker byte ownership. The global `workspace_sync=unverified` overlay is not a source-closure hash proof. Contextor `get_symbol_lineage` preview for `ContextorFacade.analyze_project` resolved at revision 693, but its large sections were not fetched; `contextor_fact_lineage` documents only artifact_consumption, syntax_diagnostics and symbol_calls families, so it cannot certify cycle-semantics lifecycle.

## FILES_CHANGED

Source/test/docs/config: NONE. Only `walkthrough.md` was overwritten with this acceptance report.

## ACTUAL_DIFF

DIFFS=NONE for source/test/docs/config. `walkthrough.md` is excluded as the report itself.

## FINAL_VERDICT

DIRECT_EVIDENCE and CONTRACT_PROVED support an isolated P1D2 opt-in integration GO. GENERAL_SEMANTIC_CLASSIFICATION is NO_GO; CONTEXTOR_OWN_CYCLES acceptance is NO_GO because required current per-SCC model evidence is absent. No active repository or LIVE mutation was performed. STOP after P1D2M and await the architect's assessment and explicit `proceduj`.
