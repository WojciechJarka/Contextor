### Layer and single-file reporting performance

* Reworked layer analysis to consume validated authoritative canonical state directly instead of constructing and materializing a full incremental engine when layer reporting does not require update semantics.
* Preserved the existing LIVE-first/snapshot-validated repository-state selection, repository identity checks, collision freshness rules and fail-closed fallbacks while removing unnecessary repository-wide materialization from layer reports.
* Reduced large-layer analysis from full-engine-scale latency to a few seconds on the Contextor repository without reducing report content or architectural analysis.
* Added a fail-closed state-only fast path for single-file analysis when the target is already tracked, byte-current and backed by healthy canonical state.
* Healthy unchanged single-file analysis now reuses canonical modules, dependency graph, artifacts and existing report fallbacks directly, avoiding incremental-engine construction, repository-wide module-usage materialization and a redundant `update_file` call.
* Changed, new, deleted, stale or resync-required files continue through the existing full incremental-engine path, preserving refresh planning, recovery, persistence and LIVE publication semantics.
* Unified downstream single-file reporting around the selected canonical analysis state so deep context, artifact projection and graph analytics use the same report pipeline regardless of whether the state came from the lightweight or full-engine path.
* Preserved source-backed reference discovery when persisted canonical state intentionally lacks materialized module-usage facts; output parity was verified against the previous fully materialized path.
* Reduced healthy unchanged single-file analysis to roughly 0.5 seconds in warm measurements while retaining the existing report and MCP contracts.


## Patch — Full Repository Analysis Performance] - 2026-08-31

### Full repository analysis performance

* Reworked the full `analyze_project` execution path to eliminate repeated repository-wide work while preserving the complete analysis, reporting, cache, LIVE, persistence and fallback contracts.
* Fused collision analysis into the existing indexed AST/fact pipeline. Warm current-schema analyses now reuse cached collision facts instead of traversing every module AST again, while incomplete or invalid coverage still falls back to the authoritative repository-wide collision extractor.
* Fused test-context facts into the index worker/cache path. Test imports, referenced names and assertion presence are extracted from the already-live AST and reused by `TestContextIndex`, removing the previous second parse/visitor pass over test files.
* Reused the already-computed global shared-usage Jaccard clusters for canonical state publication. The handoff is accepted only with exact current-run provenance, domain and structural validation; invalid or incomplete handoffs retain the canonical recomputation fallback.
* Replaced repeated `TestContextIndex.find_test_files()` full scans with run-scoped reverse indexes for filename and dotted import-prefix lookup, preserving exact previous matching, deduplication and deterministic ordering semantics.
* Reused automatic test-directory discovery directly from the current `RepositoryIndex` result domain instead of rescanning indexed module paths during artifact reporting. Explicit caller-supplied `test_dirs`, including custom directories, remain authoritative and unchanged.
* Preserved serial and ProcessPool parity, current cache fingerprint/source validation, schema migration behavior, exclusions, test discovery rules, canonical/LIVE freshness, report contents, MCP/API contracts and persistent identities throughout the optimization series.
* Final warm-path attribution confirmed that current-schema indexed files perform zero source parses, zero symbol/reference/collision/test-fact extraction and zero cache rewrites. Remaining `index_repository` cost is dominated by required cache freshness validation, ProcessPool transport/coordination and construction of current-run repository representations rather than duplicated analysis work.
* Controlled post-optimization full-repository benchmarking reached a warm median of approximately **5.9 s** on the current Contextor repository workload. No further repository-wide optimization target with at least approximately 100 ms of demonstrated safely removable duplicate work remained, so the full-analysis performance series was closed rather than adding marginal complexity.


## Patch — MCP Ergonomics and Round-Trip Runtime Hardening] - 2026-08-26

### Public MCP ergonomics

- Completed an end-to-end ergonomics review of the full public MCP surface. All 24 public tools, their centralized documentation entries and runtime discovery descriptions were audited for parameter consistency, bounded output behavior, identity handling and LLM-oriented usage.
- Standardized common query ergonomics without breaking existing public contracts. Added or retained compatibility aliases where useful, preserved explicit ambiguity handling and removed unnecessary multi-call workflows where canonical state already contained enough information to answer safely.
- Hardened shared active-identity resolution across artifact-oriented tools. Persistent module and artifact registries remain identity stores only; canonical LIVE state remains authoritative for current architectural ownership and source location.
- Kept public FastMCP discovery descriptions centralized in `contextor/mcp/docs/index.json`. Registered tool descriptions remain index-backed, bounded in size and separate from implementation functions.

### Compact evidence without information-free responses

- Reworked compact responses so non-empty collections no longer collapse to counts with no supporting evidence.
- `compact=True` remains the default, but affected collections now return up to three representative evidence items together with the full `total` and an explicit `truncated` flag.
- Applied the bounded-evidence contract to artifact consumers, inbound/outbound dependencies, report-diff layers, isolation clusters and violations, edit-context API/import/consumer/test data, affected modules and semantic file-delta symbol collections.
- Preserved existing non-compact behavior and caller-provided item/evidence limits.
- Kept mutating `update_file` free from unsafe replay-style expansion semantics; complete evidence must be requested on the original call when required.

### Single-shot large-output handling

- Added deterministic semantic auto-bounding for MCP responses that can safely return a useful prefix instead of forcing an identical second request solely to approve a large payload.
- Added a shared `largest_fitting_prefix` helper using serialized UTF-8 size and the existing 15 KiB (`15360` byte) warning threshold.
- `search_source` now returns the largest deterministic match prefix that fits the context budget, together with exact full-output byte metadata and an `allow_large_output=true` retry path for the complete result.
- `lookup_index_entries` now performs equivalent deterministic prefix bounding while preserving requested ID order and reserved metadata safety.
- `get_analysis_status` now bounds only skipped-file evidence while preserving all scalar job state and exact durable-job contents.
- `get_symbol_call_context` now performs output bounding only after normal call-graph traversal and representation negotiation. The selected named/indexed representation is pinned during bounding; no second BFS, registry resolution or representation negotiation is performed.
- Existing representation rules remain unchanged: material indexed savings are required for automatic switching, and oversized named call-context payloads still use the established forced-indexed contract.
- `get_source_range` intentionally remains lossless. Oversized exact ranges still require explicit large-output approval rather than semantic truncation.

### Canonical projection single-call quickstart

- Removed the mandatory `describe_canonical_state` prerequisite for basic canonical projection queries.
- When both `schema_version` and `language_version` are omitted, `query_canonical_projection` now uses the stable `1.0/1.0` contract automatically.
- Partial version specification remains fail-closed: supplying exactly one version field returns `missing_required_field`.
- Explicit `1.0/1.0` and `1.1/1.1` behavior, cross-version rejection, field validation, request limits and query-language semantics remain unchanged.
- Basic requests can now directly specify `root`, `filters` and `select` for `modules`, `artifacts` or `dependencies`; empty filters match all records and an empty selection requests all selectable fields.
- `describe_canonical_state` remains available for complete versioned schemas, field/operator discovery, v1.1 capabilities, ordering, null semantics, limits and validation repair.

### Single-shot symbol implementation lookup

- Extended `get_symbol_implementation` so a globally unique plain symbol can be resolved without first calling `search_artifacts` or supplying a file path.
- Plain leaves without explicit file scope now use the shared active artifact resolver. A unique exact leaf resolves to its canonical artifact identity and canonical LIVE module ownership before entering the existing source/AST implementation pipeline.
- Ambiguous plain leaves fail closed with canonical candidates and artifact IDs; no implementation is guessed or fetched.
- Textual misses return bounded fuzzy suggestions only. Fuzzy matching remains active-registry-only and never promotes a suggestion into an implementation result.
- Explicit `file_path` / `file_paths` behavior remains AST-first and scope-constrained, preserving zero-registry-read exact and ambiguous scoped resolution.
- Artifact IDs, lowercase artifact IDs, canonical `module::symbol` identities, stale/resync protection and the existing `auto` / `preview` / `fetch` modes remain compatible.
- Canonical LIVE state remains the source of identity, ownership and source location; implementation text continues to be read from the current file on disk.
- The existing 5120-byte automatic implementation-fetch threshold is unchanged.

### Concurrent analysis-status disambiguation

- Hardened `get_analysis_status(job_id=None)` for durable stores containing multiple queued or running jobs.
- When more than one active durable job exists, the tool now returns `status="ambiguous_job"` instead of silently selecting one.
- Ambiguous responses include a deterministic, read-only list of up to five active candidates with job ID, operation, target, status and timestamps.
- Active candidates are ordered newest-first by durable file modification time with a stable job-ID tie-break.
- Explicit `job_id` remains authoritative and bypasses active-job enumeration entirely.
- Existing latest-job behavior is intentionally preserved when zero or one active job exists; a sole active job is not automatically preferred over a newer terminal job.
- Existing stale-owner interruption, job deduplication, public job shaping and large skipped-file output bounding remain unchanged.
- The ambiguity branch is strictly read-only and does not rewrite or normalize durable job files.

### Runtime certification

- Restarted the MCP server and independently certified the new behavior against the running FastMCP runtime rather than relying only on source-level tests.
- Verified fresh client-visible schemas and registered descriptions for canonical projection, symbol implementation and analysis-status tools.
- Exercised compact evidence against real Contextor repository data and confirmed that non-empty compact collections retain bounded evidence.
- Verified `search_source` auto-bounding against an oversized real response and confirmed byte-exact parity with the corresponding lossless `allow_large_output=true` response.
- Verified `get_source_range` retains the lossless confirmation-only exception.
- Verified `get_analysis_status` auto-bounds large skipped-file evidence while returning the complete durable job unchanged when explicitly approved.
- Exercised `get_symbol_call_context` against a temporary 600-edge canonical call graph: an 87,709-byte indexed response was automatically reduced to a 15,273-byte deterministic 98-edge prefix while retaining the same representation; the full 600-edge response remained byte-exact under `allow_large_output=true`.
- Verified canonical projection directly in one call without prior schema discovery, including implicit `1.0/1.0`, partial-version rejection, explicit v1.1 and cross-version rejection.
- Verified unique plain-symbol implementation retrieval without a preceding artifact lookup, controlled ambiguity, fuzzy suggestion-only behavior and explicit file-scoped resolution.
- Verified concurrent analysis ambiguity on isolated durable jobs, including the five-item bound, deterministic ordering, explicit-job override and preservation of legacy latest-job semantics.
- Confirmed the ambiguous analysis-status path is byte-for-byte read-only using SHA-256 checks of durable job files before and after the runtime call.

### Verification status

- Public MCP ergonomics review: 24/24 tools complete.
- Public MCP documentation and discovery parity: complete.
- Round-trip ergonomics fixes: 5/5 closed.
- Targeted regression and contract suites: passing.
- Large-output regression suite: 22/22 passing.
- Runtime MCP freshness: verified.
- Runtime round-trip ergonomics certification: 5/5 passing.
- Open code, contract and runtime findings: none.

### Canonical single-file reference projection
Replaced single-file repository-wide reference rescans with canonical in-memory reference projection backed by `artifact_consumption` and per-module `reference_evidence`, while preserving exact legacy reference, consumer, ambiguity, and detail semantics.

### Legacy reference-evidence hydration
Added fail-closed one-time materialization of legacy reference evidence during normal repository hydration, allowing existing snapshots to upgrade through the authoritative usage extraction path so subsequent hydrations and single-file queries avoid repository-wide source and AST rescans.

### Desktop LIVE startup hardening
Hardened Desktop LIVE startup against transient service initialization delays with bounded non-blocking GUI retries, duplicate-watcher prevention, and shutdown-safe retry cancellation, without changing canonical LIVE runtime behavior or MCP connection timeout semantics.

Added per-tool canonical freshness envelopes across LLM-facing MCP queries, exposing canonical revision, LIVE/snapshot provenance, workspace synchronization state, family-level freshness and explicit advisory warnings without requiring a separate get_analysis_status call.
Hardened interrupted-analysis handling so stale canonical answers are no longer silent: disk/canonical divergence is reported as out_of_sync or unverified, while later LIVE reconciliation correctly restores verified freshness instead of permanently inheriting an old interrupted-job state.
Added positive generation proof between canonical state and FileState using state_id, publication revision and file fingerprints; incomplete legacy evidence remains explicitly unverified, while confirmed generation mismatches fail closed for source-sensitive operations.
Made get_symbol_implementation refuse implementation extraction when canonical coordinates cannot be safely matched to the current workspace generation, preventing stale AST/source slices from being returned after repository changes.
Synchronized successful full repository analyses with an already-running LIVE daemon in place, keeping persisted snapshot, FileState, daemon state and subsequent MCP queries on the same canonical publication without daemon restart or manual MCP cache clearing.
Separated canonical publication revisions from LIVE transport/event journal revisions throughout runtime caching and reporting. Canonical engine caches now track only canonical state revisions, while live_publish_revision retains the daemon journal/event revision returned by publication.
Hardened LIVE publication failure semantics: missing daemons are reported as not_attempted, rejected/unknown responses fail closed, IPC failures and timeouts remain visible through live_publish_status / live_publish_warning, and valid persisted canonical state is preserved even when daemon publication fails.
Added strict LIVE publish response validation (status == "ok" with a revision) and regressions proving that a heavily advanced LIVE event journal can never contaminate canonical revision tracking.
Hardened LIVE cold startup by separating normal connection timing from a bounded 60-second canonical-initialization budget, detecting dead child processes immediately and avoiding termination of healthy daemons performing one-time canonical materialization.
Persisted startup materialization so expensive legacy/canonical backfill is paid once: the real Contextor repository completed an initial 299-module LIVE bootstrap in ~11.9 s and subsequent startup in ~0.95 s.
Added end-to-end regressions for daemon restart epochs, same-session cache reuse, cross-session journal reuse, full-analysis same-daemon publication, explicit generation mismatch, publication rejection/failure handling, journal-ahead revision separation and slow/dead/hung LIVE startup paths.
Completed post-restart runtime certification with all audited MCP tools resolving from the same verified LIVE canonical publication, canonical/event revision separation intact, Desktop watcher active and no runtime freshness warnings.


## [1.2.0-beta Patch — LIVE Hardening, MCP Modularization & Token Efficiency] - 2026-08-21

### Canonical LIVE truth and recovery semantics

- Hardened canonical LIVE state against syntax-invalid source updates. Modules with parse failures now retain last-known-good structural facts only as explicitly stale data instead of being exposed as current truth.
- Added persistent per-module parse freshness tracking and authoritative current-truth helpers shared by LIVE updates and MCP query paths.
- Added explicit recovery semantics: a successfully reparsed stale module now emits `RECOVERED`, even when its semantic payload matches the previous valid version.
- Preserved parse-freshness state across canonical persistence and hydration.
- Extended stale/fail-closed handling across architecture, module-context, file-edit, artifact search, symbol lookup and canonical projection paths.
- Hardened LIVE reconnect handling against transient IPC failures without starting competing owners.
- Strengthened owner identity validation with repository identity, root path, PID, endpoint, owner token and authentication identity checks.
- Preserved journal and revision continuity across transient reconnects and desktop/MCP restarts.

### LIVE incremental correctness and restart reconciliation

- Fixed incremental ADD handling when persisted file fingerprints were ahead of canonical state. An unchanged fingerprint can no longer suppress materialization of a module missing from canonical RAM.
- `UNCHANGED` is now valid only when the current file fingerprint matches and the module already exists in authoritative canonical state.
- Added canonical ADD/DELETE verification for modules, artifacts and dependency-graph nodes without requiring a Full Analysis.
- Added startup reconciliation for files added, modified or deleted while the desktop watcher was offline.
- Startup reconciliation compares current filesystem state, persisted file fingerprints and canonical module membership, then routes only proven differences through the normal incremental COW/update pipeline.
- Preserved exclusions as authoritative during startup reconciliation.
- Added restart-idempotence guarantees: restarting LIVE without repository changes no longer produces repeated no-op updates or revision churn.
- Semantic `UNCHANGED` updates now acknowledge the current file fingerprint so the same file is not redispatched on subsequent restarts.
- Added pre-dispatch revalidation of startup candidates to prevent stale reconciliation queues from producing unnecessary `update_file` journal events.
- Verified offline ADD, MODIFY and DELETE recovery, canonical cleanup/materialization and zero-change restart idempotence.

### MCP discovery and documentation token reduction

- Moved public MCP documentation out of Python tool docstrings into `contextor/mcp/docs`.
- Added a compact documentation index with per-tool short descriptions and one JSON document per public MCP tool.
- Added `get_mcp_documentation` for progressive documentation disclosure: index-only, selected tools and selected sections can be requested without loading the complete documentation corpus.
- FastMCP tool descriptions are now sourced from the compact documentation index.
- Reduced existing MCP tool-description payload from 24,544 bytes to 2,770 bytes and the complete 21-tool description payload to 2,925 bytes.
- Reduced the serialized FastMCP discovery catalog from 36,961 bytes to 15,517 bytes, a 58.02% reduction, while preserving public tool schemas and behavior.
- Removed public documentation docstrings from tool implementations to keep discovery payloads independent from full operational documentation.

### MCP server modularization

- Split the former monolithic `contextor/mcp_server.py` into one implementation module per public MCP tool under `contextor/mcp/tools`.
- All 21 public MCP tools now have dedicated implementation owners; `mcp_server.py` contains zero public tool implementation bodies.
- Preserved the complete public MCP surface, including exact tool names, order, signatures, defaults, annotations, short descriptions and `contextor.mcp_server.<tool>.fn` compatibility bindings.
- Centralized registration remains explicit and exactly-once; tool modules contain no FastMCP instances, decorators or registration side effects.
- Enforced dependency direction:
  `mcp_main -> mcp_server -> tools/* -> shared MCP modules -> core`.
- Removed tool-to-server and tool-to-tool imports, registration-time dependency injection, temporary resolver bindings and private compatibility bridges.
- Added dedicated shared MCP owners:
  - `contextor.mcp.runtime` for canonical engine/runtime state and LIVE status publication;
  - `contextor.mcp.analysis_jobs` for analysis-job lifecycle, locks, durable status, worker execution, hydration and LIVE publication orchestration;
  - `contextor.mcp.query_helpers` for shared canonical query projections, registry access, freshness handling and artifact catalog/consumer helpers;
  - `contextor.mcp.report_helpers` for shared historical/report resolution.
- Kept single-consumer helpers local to their tool owners instead of creating unnecessary shared abstractions.
- Migrated tests and monkeypatches to actual implementation owners and removed obsolete test dependencies on private `mcp_server` symbols.

### MCP analysis execution and Windows multiprocessing

- Removed the obsolete MCP-specific `CONTEXTOR_DISABLE_PROCESS_POOL=1` override that forced full repository analysis into sequential artifact processing.
- Restored the same internal ProcessPool execution policy used by desktop analysis while retaining an explicitly inherited sequential fallback when requested by the environment.
- Preserved analysis-job deduplication, status persistence, canonical hydration, LIVE publication, exclusions and shared facade semantics.
- Added lightweight `contextor.mcp_main` startup entrypoint so Windows multiprocessing children no longer bootstrap FastMCP, register all MCP tools or initialize unnecessary server dependencies.
- Kept `multiprocessing.freeze_support()` and heavy MCP imports behind the protected runtime startup path.
- Eliminated the previously observed MCP-specific ~2x full-analysis slowdown caused by forced sequential artifact analysis.
- Controlled desktop/MCP measurements now show equivalent global-pipeline execution, with only bounded MCP process/bootstrap overhead.

### Canonical MCP query ownership and SSOT cleanup

- Completed migration of current architecture, module-context, file-edit, artifact-search and symbol-implementation queries to canonical `RepositoryAnalysisState` ownership.
- Preserved fail-closed parse freshness, exact canonical artifact domains, zero-consumer artifacts, ambiguity handling, freshness/provenance and bounded response semantics through the MCP split.
- Kept historical/report-oriented access only where it is part of the explicit contract, including report diff and indexed report context.
- `get_layer_isolation` remains intentionally report-backed pending its separate canonical R4/R5 cleanup.
- Preserved complete AST-scoped symbol implementation retrieval with signatures, source resolution, ambiguity refusal and static context after modularization.

### Validation and regression coverage

- Added structural regression coverage for all MCP split stages, including tool ownership, registration parity, dependency direction, shared-helper uniqueness and absence of monolithic tool bodies.
- Added Windows spawn regressions proving multiprocessing children do not bootstrap FastMCP or MCP registration.
- Added focused LIVE regressions for stale parse truth, recovery, new-module materialization, startup reconciliation and restart idempotence.
- Removed obsolete and inert test monkeypatches left behind by MCP ownership changes; tests now patch the actual runtime lookup sites.
- Verified incremental materialization of newly created MCP modules through desktop LIVE without using Full Analysis as a repair mechanism.
- Full-suite checkpoints during the refactor identified only expected test/fixture drift from deliberate ownership and contract changes; affected tests were migrated without restoring legacy compatibility paths.

### Performance characterization

- Controlled OLD-vs-CURRENT Full Analysis benchmarking found no performance regression from the MCP/LIVE refactors.
- Current code processed a larger repository snapshot faster than the older comparison revision under identical execution conditions.
- `collect_module_artifacts` showed healthy scaling: module count increased by ~14% while stage duration increased by ~8%, reducing average cost per module.
- Graph analytics helpers, including PageRank, HITS, betweenness, dependency matrices and Jaccard clustering, remain sub-second in aggregate at the current repository size.
- Large historical Full Analysis timing variance was classified as environmental/runtime variance rather than a deterministic code regression.
- Remaining Full Analysis cost is now treated as a scalability concern for larger repositories rather than a regression introduced by the current refactor.

Patch — MCP Pre-Edit Ergonomics & GUI Operation Timing] - 2026-08-19

### Lightweight pre-edit context for coding agents

- Extended `get_file_edit_context` with an opt-in `mode="minimal"` designed as a low-overhead pre-edit guard for coding agents.
- Preserved the existing `get_file_edit_context` contract as the default behavior; existing positional and named callers remain backward-compatible.
- Added flexible target resolution through the existing canonical index resolver. Minimal mode can resolve:
  - absolute Python file paths,
  - repository-relative paths,
  - dotted module names,
  - persistent module IDs,
  - symbols and artifact references.
- Reduced common pre-edit workflows from multiple MCP round-trips to a single query for dotted module names, module IDs and other canonical target forms.
- Added canonical equivalence handling for `file_path` and `target`; different textual representations of the same module are accepted, while genuinely conflicting targets return an explicit structured validation error.
- Added explicit validation for unsupported `mode` values instead of silently falling back to another response contract.
- Symbol/artifact inputs are resolved without being misclassified as modules and return their canonical identity, defining module and a `get_artifact_blast_radius` next-tool hint.
- Minimal responses remain bounded and expose only pre-edit facts required for rapid repository orientation:
  - canonical module identity,
  - file,
  - layer,
  - LIVE revision when available,
  - canonical module risk,
  - direct consumer count,
  - transitive consumer count,
  - bounded consumer sample,
  - statically reachable covering-test count,
  - bounded test sample,
  - truncation state and warnings.
- Reused the canonical reverse-reachability implementation in `analysis.incremental.graph_ops.calculate_affected_set`; no duplicate MCP-specific BFS implementation was introduced.
- Minimal mode performs no source-code reads, repository analysis, report generation, graph recomputation or LIVE mutation.
- Removed proposed heuristic `local / guarded / deep` scope classification rather than exposing uncalibrated safety judgments to coding agents.

### Canonical LIVE risk integration

- Fixed `get_file_edit_context(mode="minimal")` reading per-module risk from the wrong LIVE state field.
- `risk_score` now uses the canonical:
  `RepositoryAnalysisState.topology_analytics["module_risk"]`
  source used by LIVE topology analytics.
- Risk values are now guarded by `topology_metrics_state`:
  - `fresh` + available module risk → canonical risk value,
  - `deferred` → `null`,
  - `stale` → `null`,
  - `fresh` with a missing module entry → `null` with a diagnostic warning.
- Removed fallback estimation from unrelated hotspot, betweenness and HITS metrics so `risk_score` retains one stable semantic meaning.
- Direct LIVE MCP verification confirmed canonical risk propagation for representative modules, including:
  - `contextor.ui.gui`,
  - `contextor.core.api.facade`.

### GUI analysis duration reporting

- Added end-to-end operation timing for the three primary GUI analysis actions:
  - repository analysis,
  - layer analysis,
  - single-file analysis.
- Successful operations now emit messages such as:
  - `[SUCCESS] Repository analysis completed. (duration: 83 s)`
  - `[SUCCESS] Layer analysis completed. (duration: 12 s)`
  - `[SUCCESS] Single-file analysis completed. (duration: 3 s)`
- Timing is measured once in the shared `run_with_progress` lifecycle using a monotonic clock rather than duplicated across individual analysis handlers.
- Duration covers the user-visible analysis lifecycle from operation start until successful task completion/finalization.
- Existing consumers of `run_with_progress` that do not provide an operation name preserve the previous success-message contract exactly.
- Failure, cancellation, progress and ETA semantics remain unchanged.

LLM-friendly MCP target resolution

- Hardened `get_module_context` for natural LLM input by adding a backward-compatible `module` alias alongside the existing `module_name` parameter.
- Module inputs are now compared through canonical identity rather than raw text, allowing equivalent forms such as dotted module names and persistent module IDs to resolve safely to the same target.
- Conflicting `module_name` and `module` inputs now return a structured validation error instead of silently selecting one value.
- Passing an artifact or symbol to `get_module_context` now returns a structured diagnostic containing:
  - canonical artifact identity,
  - persistent artifact ID,
  - defining module,
  - `get_artifact_blast_radius` as the suggested next tool.
- Hardened `get_artifact_blast_radius` when a module name or module ID is supplied instead of an artifact.
- Module targets are now recognized through the existing canonical resolver and return:
  - canonical module identity,
  - persistent module ID,
  - `get_module_context` as the suggested next tool,
  - a bounded deterministic list of artifact candidates defined by the module,
  - total candidate count and truncation state.
- Existing valid artifact names, qualified symbols and persistent artifact IDs retain their previous behavior.
- No implicit semantic switching was introduced: module tools and artifact tools continue to perform their own responsibilities while providing useful routing diagnostics for mismatched target types.
- Full MCP regression coverage for these routing changes passed: `56/56`.

### Canonical LIVE layer provenance

- Fixed `get_file_edit_context(mode="minimal")` returning `layer: "unknown"` despite fresh cached LIVE analytics.
- Minimal pre-edit context now reads module layers exclusively from:
  `RepositoryAnalysisState.cached_analytics["module_layers"]`.
- Layer values are exposed only when `cached_analytics_state == "fresh"`.
- `deferred`, `stale`, or missing canonical entries remain unavailable rather than falling back to report files or package-name heuristics.
- Direct LIVE verification confirmed canonical layers for representative modules:
  - `contextor.ui.gui` → `ui`
  - `contextor.core.api.facade` → `contract`
  - `contextor.ui.exclude_check` → `ui`

### Persistent LIVE revision restoration

- Fixed `get_file_edit_context(mode="minimal")` returning `live_revision: null` after MCP hydration from persisted LIVE state.
- Canonical revision remains lifecycle metadata rather than becoming part of `RepositoryAnalysisState`.
- `_get_or_init_engine` now restores the persisted `LiveStateMetadata.revision` into the existing MCP revision cache after successful state validation and hydration.
- Minimal pre-edit context now reads revision from the same revision cache used by active IPC, snapshot refresh and LIVE publication.
- Invalid or rejected hydration explicitly clears stale engine and revision cache entries.
- Revision lifecycle was verified across:
  - persisted snapshot hydration,
  - active IPC `ping` / `snapshot`,
  - subsequent LIVE publication,
  - independent repository roots.
- Existing manual `update_file` revision invalidation using `remote_revision - 1` was audited and confirmed to intentionally force immediate snapshot refresh without producing a final off-by-one revision.
- Direct verification after MCP restart confirmed:
  - active LIVE revision: `374`
  - `get_file_edit_context(..., mode="minimal")` revision: `374`
  - persisted hydration correctly restored revision `373` without incrementing it.

### Verification

- Running MCP verification confirmed correct target routing for dotted module names, module IDs, artifacts and symbols.
- Canonical conflict detection was verified for equivalent and genuinely different target representations.
- Minimal pre-edit context now consistently exposes canonical:
  - `layer`,
  - `risk_score`,
  - `live_revision`,
  from their respective LIVE state sources.

### MCP artifact ranking and dependency semantics

- Improved module-to-artifact diagnostics in `get_artifact_blast_radius` with deterministic public-first candidate ranking.
- Artifact candidates now prioritize:
  - canonical exported/public API symbols,
  - syntactically public non-exported symbols,
  - dunder methods,
  - private methods,
  - private/internal symbols.
- Candidate ranking changes presentation only; the complete addressable artifact set is preserved without filtering private or internal symbols.
- Reused the existing canonical public API extraction logic rather than introducing a second definition of symbol visibility.
- Clarified MCP dependency semantics for coding agents:
  - `fan_in` represents direct inbound hard dependency/import edges only,
  - `direct consumer` represents unique direct consumers across hard and soft dependency edges,
  - `transitive consumer` represents reverse transitive reachability across hard and soft dependencies, excluding the target itself.
- Confirmed that differences between `fan_in` and pre-edit `direct_count` are intentional rather than inconsistent metrics; for example, soft test consumers may contribute to `direct_count` without contributing to hard-import `fan_in`.
- Updated MCP tool descriptions so agents receive these definitions directly instead of having to infer the meaning of the metrics.
- Targeted MCP regression verification passed: `9/9`.

### Pre-Edit Layer Guard

- Extended `get_file_edit_context(..., mode="minimal")` with a lightweight `layer_guard` so coding agents can see layer-rule context before editing without invoking the full `get_layer_isolation` workflow.
- `layer_guard` is built entirely from canonical in-memory state and existing validator rules; it performs no source reads, report reads, repository analysis, graph recomputation or LIVE mutation.
- Added canonical layer-rule visibility:
  - `outbound_rules_defined`
  - `forbidden_outbound_layers`
  - `forbidden_outbound_prefixes`
- Added current layer-violation visibility with separate:
  - `outbound_violation_count`
  - `inbound_violation_count`
  - bounded violation details with explicit direction.
- `outbound_rules_defined` refers only to rules governing dependencies originating from the target module's layer and does not imply that the module cannot participate as the target of an inbound violation.
- Layer-rule facts respect `cached_analytics_state` freshness:
  - `fresh` exposes canonical rule and violation data,
  - `stale` or `deferred` returns the guard as unavailable rather than serving outdated results.
- Added `get_layer_isolation` guidance when the module has outbound restrictions or participates in an inbound/outbound layer violation.
- Preserved the legacy `get_file_edit_context` contract unchanged.
- LIVE verification confirmed correct behavior for both restricted and unrestricted layers, including canonical `layer`, `risk_score`, `live_revision` and layer-rule state.
- Targeted MCP regression verification passed: `14/14`.

### Cross-Layer Artifact Blast Radius

- Extended `get_artifact_blast_radius` with an architectural projection for direct symbol consumers.
- Added canonical classification of consumers into:
  - same-module consumers,
  - same-layer consumers,
  - production cross-layer consumers,
  - test consumers,
  - unknown-layer consumers.
- Added `definer_layer`, unique `consumer_layers`, `cross_layer_consumer_count`, `cross_layer_consumers`, `test_consumer_count`, and a bounded production-only `cross_layer_sample`.
- Test consumers are tracked separately from production cross-layer dependencies so test impact does not inflate architectural blast radius.
- Architecture counts are derived from the exact same unique direct consumer set as the existing artifact blast radius and preserve a tested count invariant.
- Layer classification uses fresh canonical LIVE `module_layers` only; stale, deferred, or report-only states return the architecture projection as unavailable rather than guessing.
- The projection performs no source reads, report generation, graph recomputation or LIVE mutation.
- MCP tool descriptions were updated to expose the exact semantics directly to coding agents.
- LIVE verification confirmed correct same-layer, cross-layer and test-impact classification for real Contextor artifacts.

### Symbol-Seeded Downstream Module Reachability

- Extended `get_artifact_blast_radius` with conservative downstream module reachability seeded by confirmed direct symbol consumers.
- Reused the canonical `calculate_affected_set` implementation over the LIVE hard + soft dependency graph; no duplicate traversal algorithm was introduced.
- Kept direct symbol consumers and downstream modules strictly separate:
  - direct consumers remain confirmed symbol-level references,
  - downstream modules represent additional module-level dependents reachable behind those direct consumers.
- Explicitly avoided false symbol-level precision: downstream modules are not presented as transitive consumers of the original symbol.
- Added separate downstream counts for:
  - production modules,
  - test modules,
  - modules with unknown canonical layer.
- Added bounded production and test downstream samples while preserving deterministic output.
- Downstream reachability remains available whenever the canonical LIVE dependency graph is available; layer classification is exposed only when cached layer analytics are fresh.
- Enforced invariants:
  - direct consumers and downstream modules are disjoint,
  - the defining module is excluded from downstream results,
  - production + test + unknown downstream counts equal the total downstream count.
- Existing direct-consumer `architecture` classification remains unchanged and continues to describe only confirmed direct symbol consumers.
- The MCP tool description now explicitly defines the feature as conservative module-level downstream reachability rather than transitive symbol-to-symbol consumption.
- LIVE verification confirmed real downstream expansion for facade and incremental-analysis symbols, including production/test separation and zero-result behavior for locally unused symbols.
- Targeted MCP regression verification passed: `16/16`.

### Canonical LIVE Topology Metrics & Lifecycle Hardening

- Hardened `get_module_context` so advanced graph metrics now prefer canonical LIVE `topology_analytics` whenever the LIVE engine is available.
- `pagerank`, `betweenness`, HITS hub/authority scores, bridge score and module risk are now sourced from their dedicated canonical LIVE maps instead of saved graph-analysis snapshots.
- Preserved `fan_in` and `fan_out` as direct LIVE measurements from the current hard dependency graph.
- Removed silent fallback to stale `_graph_analytics.json` values when canonical topology state is `stale` or `deferred`.
- Missing topology entries are treated as unavailable rather than replaced with misleading `0.0` defaults, with each topology metric resolved independently.
- Report-only operation remains backward-compatible and explicitly identifies `saved_graph_analytics` as its provenance.
- Completed the canonical LIVE lifecycle for topology analytics across bootstrap, persistence, hydration and incremental updates.
- Full repository analysis now explicitly marks successfully computed `topology_analytics` as `fresh` instead of persisting valid metrics with the default `deferred` state.
- Legacy persisted `deferred` topology states are safely rematerialized in RAM from the canonical dependency graph during hydration, without a full repository source scan.
- `stale` topology state remains protected from automatic healing because it represents `requires_resync` / an untrusted dependency graph.
- Topology recomputation is atomic: newly computed analytics are committed only after successful completion, preserving previous state on failure.
- Fresh topology state survives persistence and restart without being downgraded to `deferred`.
- Body-only edits preserve fresh topology metrics without unnecessary recomputation, while graph-changing edits continue to trigger the existing `advanced_graph_metrics` in-memory refresh path.
- `cached_analytics` and its independent freshness lifecycle remain unchanged.
- LIVE verification confirmed `get_module_context` serving PageRank, betweenness, HITS, bridge and risk metrics from `live_canonical_topology`.
- Targeted topology lifecycle tests passed `7/7`, with the related MCP regression set passing `17/17`.

Canonical Artifact Consumption Channels & Reference Semantics
Extended canonical artifact-consumption tracking with explicit qualified_refs, runtime_calls, callback_calls and event_bindings channels while preserving exact <module>::<qualified_symbol> identities.
Added non-call qualified attribute reference detection and prevented callee attribute subtrees from being double-classified as both calls and qualified references.
Hardened callback and event semantics with a disjoint contract: callback arguments remain callback_calls, while bind, subscribe and on registrations are classified exclusively as event_bindings.
Preserved unresolved dynamic reflection as runtime_calls facts without inventing arbitrary canonical target bindings.
Added full-vs-incremental parity coverage for qualified references, nested qualified calls, callbacks, event bindings and dynamic runtime usage.
Hardened dependent-consumer selection across all canonical usage families, including imports, aliases, inheritance, callbacks, events, runtime calls and qualified references.
Verified re-export retargeting so incremental state moves consumers between canonical providers without retaining stale bindings.
Replaced fuzzy graph dependency classification with an exact canonical channel mapping: call channels map to call, import/qualified-reference channels to import, and inheritance to inheritance.
Canonical LIVE Artifact Consumption Lifecycle & Ambiguity Hardening
Added natural dotted-identity ambiguity handling for cases where distinct canonical targets collapse to the same dotted reference, such as pkg.a::B.foo and pkg.a.B::foo.
Incremental late-provider updates now discover affected consumers from persisted in-memory usage facts and recompute their artifact-consumption slices without rereading unchanged consumer source files.
Canonical target resolution now fails closed on multiple valid matches instead of selecting an arbitrary provider.
Added copy-on-write consumer-slice sanitization: when resolution becomes ambiguous, the affected consumer is removed from all candidate target bindings while unrelated artifact-consumption entries remain unchanged.
Ambiguous incremental updates explicitly transition artifact_consumption_state to stale, preventing uncertain relations from being exposed as trusted LIVE state.
Preserved the previous canonical artifact-consumption container without in-place mutation during failed or ambiguous recomputation.
Added lifecycle proofs for late-provider ambiguity, consumer-added-after-providers ambiguity, unchanged-source no-reread behavior and unaffected-slice preservation.
Verified that both full reporting and RAM/LIVE dependency-matrix paths use the same authoritative exact channel mapper, preserving parity between canonical repository analysis and incremental materialization.

### Regression and contract verification

- Added deterministic GUI progress-widget regression coverage for named-operation durations and legacy success-message compatibility.
- Added MCP regression coverage for:
  - legacy `get_file_edit_context` compatibility,
  - absolute and repository-relative path resolution,
  - dotted module resolution,
  - persistent module-ID resolution,
  - artifact/symbol resolution,
  - equivalent `file_path` / `target` representations,
  - canonical conflict detection,
  - invalid mode handling,
  - bounded consumer/test samples,
  - topology freshness behavior for canonical module risk.
- Targeted GUI regression suite passed:
  `13 passed`.
- Targeted MCP `get_file_edit_context` regression suite passed:
  `4 passed`.
- Direct verification against the running MCP server confirmed the new minimal pre-edit paths, canonical target resolution, artifact guidance and LIVE risk wiring.

## [1.2.0-beta Patch — Incremental module-level blast radius in LIVE] - 2026-08-17

- Added incremental module-level reverse blast radius propagation to the
  canonical LIVE engine (`IncrementalAnalysisEngine`). Updates now calculate the
  transitive reverse dependency reachability (`_calculate_affected_set`) over
  the union of hard and soft graph edges with cycle termination.
- Implemented operation-specific freshness contracts for blast radius:
  - `ADD`: marked as `"fresh"` when candidate `NEW` graph evidence is available,
    allowing newly resolved dependencies and newly active consumers to be included.
  - `DELETE`: marked as `"fresh"` only when `OLD` graph evidence is present,
    preventing post-deletion rebuilt graphs from silently omitting lost consumers.
  - `MODIFY`: marked as `"fresh"` when both `OLD` and candidate `NEW` graph
    evidence are present to guarantee complete closure.
  - Missing graph evidence marks `blast_radius_state` as `"deferred"` with an
    empty `affected_modules = []`, avoiding false claims of completeness.
- Extended `IncrementalUpdateResult` with an event-specific field
  `affected_modules: list[str] = field(default_factory=list)` containing the
  sorted reverse blast radius when `blast_radius_state == "fresh"`. The field
  is purely event-specific and is not persisted in `RepositoryAnalysisState`.
- Added bounded `affected_modules` payloads (`{"total": N, "truncated": bool, "items": [...]}`)
  and `blast_radius_state` to the IPC event journal (`CanonicalLiveServer._record_event`)
  with a hard limit of 20 items per event in the 100-event RAM ring buffer.
- Updated MCP `update_file` to expose the same contract: `compact=True` omits
  `items`, `compact=False` provides bounded items up to `max_items`, and dynamic
  `fields` projection seamlessly includes `affected_modules`. Updated docstrings
  in `update_file` and `get_live_events` to document the new payloads.
- Added targeted unit and regression tests covering MODIFY provider with upstream
  consumer, DELETE provider with OLD consumer preservation, ADD resolving
  previously unresolved imports, DELETE with missing OLD graph, missing graph
  evidence fallback (`deferred`), syntax errors (`stale`), IPC event bounding,
  and MCP compact/full/fields shaping.
- Verified end-to-end live runtime behavior with the active `desktop_watcher`
  after canonical LIVE owner restart, confirming real-time emission of `UPDATED`
  and `DELETED` events containing `blast_radius_state: "fresh"` and valid
  `affected_modules` payloads.
- Note: Local/global graph metrics, artifact-level consumption refresh, test-impact
  propagation, and artifact-level blast radius remain deferred in this stage.
  
  - Hardened canonical LIVE runtime ownership so GUI and MCP clients can safely share one service without stealing or falsely claiming ownership.
- Added durable per-process `owner_token` identities alongside service and owner PIDs. PID values are now used only for process/liveness tracking, while ownership requires an explicit token match.
- Added serialized per-repository LIVE startup and post-spawn process verification to prevent concurrent GUI/MCP startups from leaving competing or orphaned runtime processes.
- Added Windows-safe owner monitoring using a retained process handle, preventing PID reuse from keeping orphaned LIVE runtimes alive after their owner exits.
- GUI shutdown now terminates only the LIVE runtime it can prove it owns. Connected external or MCP-owned runtimes are left untouched.
- Added graceful IPC shutdown with exact-PID process-tree termination as a fallback and race-safe endpoint cleanup.
- Fixed normal listener shutdown on Windows so closing the LIVE server no longer produces `WinError 10038` / `PytestUnhandledThreadExceptionWarning`.
- Preserved backward compatibility with legacy LIVE endpoint files lacking ownership metadata; such services remain connectable but are never implicitly treated as owned.
- Verified the lifecycle end-to-end on Windows: GUI-created LIVE remained shared with MCP, disappeared cleanly when the GUI closed, removed its endpoint, and restarted with a new service PID, owner PID, port, authentication key and owner token.
- Updated the GUI launcher regression to target the canonical `run_contextor.bat` launcher and its repository-local `.venv`.

 — Incremental LIVE graph metrics

- Synchronized canonical `RepositoryAnalysisState.metrics` directly from the current in-memory dependency graph after incremental ADD, MODIFY and DELETE operations, without a full repository source rescan.
- Preserved `state.metrics` as a macro-only graph summary containing `nodes`, hard/soft/total edge counts, hard-edge density and maximum in/out degree; no per-module metric records are stored there.
- Kept per-module `fan_in` and `fan_out` live by deriving them directly from the current canonical hard-edge graph in `get_module_context`.
- Added `degree_metrics_source = "live_canonical_graph"` so LLM-facing context can distinguish immediately fresh degree metrics from wider deferred analytical families.
- Retained broader local/global analytical freshness as deferred where PageRank, HITS, betweenness, bridge and other non-local metric families are not yet incrementally refreshed.
- Verified the full LIVE update cycle end-to-end: baseline → isolated ADD → connected ADD → edge-removing MODIFY → DELETE consumer → DELETE target.
- Confirmed at every checkpoint that canonical `state.metrics` exactly matched an independently recomputed `compute_graph_metrics(...)` oracle.
- Verified full cleanup and reversibility: after deleting probe modules, LIVE graph metrics returned exactly to the original baseline state.

— Dependency-driven LIVE semantic refresh

- Reworked incremental repository updates around a deterministic `RefreshPlanner` and explicit `REPARSE → RECOMPUTE → PATCH → GRAPH → COMMIT` execution model.
- LIVE updates now parse changed source only once, reuse cached canonical facts for unchanged modules, and avoid repository-wide source rescans during normal ADD, MODIFY and DELETE operations.
- Added canonical per-module `ModuleUsageFacts` for imports, direct calls, qualified references, runtime calls, callbacks, event bindings, inheritance and aliases.
- Added incremental, channel-aware artifact-consumption maintenance with alias and re-export resolution, including re-export retargeting without reparsing unchanged consumers.
- Added semantic `FileDelta` / `UsageDelta` driven invalidation and bounded RAM reevaluation of only affected modules.
- Dependency graph updates, reverse blast radius and macro graph metrics are now executed directly from the refresh plan and kept synchronized with the current canonical state.
- Added transactional Copy-On-Write refresh execution so published LIVE state is never partially mutated before commit.
- Integrated persistent module and artifact identity updates into planned incremental transactions while preserving generation and recovery semantics.
- Separated static refresh completeness from runtime semantic certainty, allowing statically complete LIVE updates to explicitly retain unresolved dynamic Python relations.
- Corrected freshness semantics so unchanged canonical families remain `fresh` when an update does not invalidate them, instead of being marked stale merely because no recomputation was required.
- Added explicit `requires_resync`, `runtime_unresolved`, deferred advanced-metrics and per-update blast-radius states without inflating normal MCP/LIVE payloads.
- Verified incremental canonical parity against fresh static rebuilds for module state, definitions, dependency edges, macro metrics, usage facts, artifact-consumption channels, identities and affected-module sets.
- Hardened RefreshPlan execution with fail-closed dispatch, no-double-parse guarantees, no unchanged-source rereads and exact `plan == executed work` invariants.

- Added persistent LIVE topology analytics derived entirely from the canonical dependency graph, including PageRank, Betweenness, HITS hub/authority scores, Bridge Score, Hotspots, Module Risk and Inspection Targets.
- Advanced graph analytics now refresh only when dependency topology changes and remain current across body-only edits and no-op updates without unnecessary recomputation.
- Added persistent `topology_metrics_state` provenance so fresh, stale and deferred topology analytics remain correctly distinguishable across snapshots and process restarts.
- Legacy snapshots without topology analytics are reconstructed directly from the canonical graph in RAM with zero source rereads.
- Updated LIVE consumers such as module context to prefer canonical topology analytics over stale saved graph-analysis snapshots when fresh state is available.
- Preserved compact MCP/LIVE payloads while making topology metrics available through existing context and report projections.
- Verified topology analytics parity against fresh production computation across import changes, module ADD/DELETE, restart, snapshot recovery and body-only updates.

## [1.2.0-beta Patch — LIVE Analytics & Incremental Engine Refactor] - 2026-08-18

### Persistent LIVE topology and cached analytics

- Added persistent canonical LIVE topology analytics, including PageRank,
  betweenness, HITS hub/authority scores, bridge scores, hotspots,
  module risk and inspection targets.
- Added persistent cached architectural analytics for module layers,
  visibility, export degree and layer violations.
- Added explicit freshness tracking for topology and cached analytics with
  `fresh`, `stale` and `deferred` states preserved across LIVE snapshots
  and MCP restarts.
- Added RAM-only reconstruction of missing legacy analytics from canonical
  dependency, module, artifact and artifact-consumption state without
  unnecessary source reads.
- Added stale-state guards so non-empty stale analytics are never silently
  reconstructed or promoted to fresh after restart.
- Extended LIVE module-context responses with canonical topology and cached
  analytics while preserving existing fan-in and fan-out information.
- Refined RefreshPlanner invalidation so statically complete
  `runtime_unresolved` updates may remain fresh.
- Added true no-op handling for implementation-body-only changes when no
  modeled imports, definitions or usage facts change.
- Reduced call-retarget refresh scope to the canonical usage,
  artifact-consumption and cached-analytics families actually affected.
- Reduced unnecessary persistent identity-registry synchronization for
  updates that do not add or remove symbol identities.

### Incremental artifact consumption and refresh execution

- Maintained canonical incremental `ModuleUsageFacts` and reverse
  artifact-consumption state across LIVE ADD, MODIFY and DELETE updates.
- Preserved typed usage channels for API imports, direct calls,
  qualified references, runtime calls, callback calls, event bindings
  and inheritance.
- Added RefreshPlan-driven incremental execution with explicit
  `REPARSE`, `RECOMPUTE`, `PATCH`, `GRAPH` and commit boundaries.
- Preserved fail-closed execution for unsupported refresh tokens and exact
  plan-versus-execution tracing.
- Preserved Copy-on-Write isolation so failed recomputation, analytics or
  registry operations do not publish partially updated canonical state.
- Preserved correct re-export resolution ordering by ensuring recomputation
  observes candidate module state before resolving new re-export targets.
- Kept persistent identity-registry transactions outside candidate-state
  computation so persistent commit remains owned by the incremental engine.
- Preserved semantic separation between refresh completeness and static
  certainty, allowing `complete + runtime_unresolved` states without
  incorrectly marking canonical static data stale.

### Incremental engine decomposition

- Refactored the incremental analysis engine from a monolithic implementation
  into cohesive incremental-analysis components while preserving its public
  behavior and compatibility.
- Extracted pure reverse blast-radius and local degree calculations into
  `analysis/incremental/graph_ops.py`.
- Extracted LIVE bootstrap and canonical-state materialization into
  `analysis/incremental/materialization.py`.
- Extracted source preparation, syntax validation, import and symbol
  extraction, and semantic `FileDelta` / `UsageDelta` calculation into
  `analysis/incremental/preparation.py`.
- Reduced duplicate source handling in the preparation path and reused the
  prepared source data across downstream incremental analysis.
- Extracted RefreshPlan candidate-state execution into
  `analysis/incremental/plan_executor.py`, including recomputation,
  patch-family dispatch, graph recomputations and execution tracing.
- Kept lock ownership, update lifecycle, registry transaction handling,
  canonical-state publication and file-state acknowledgement in the
  incremental engine orchestration boundary.
- Reduced `incremental_engine.py` from approximately 802 to 374 lines before
  final subsystem consolidation, removing more than half of the original
  monolithic implementation.
- Preserved existing incremental engine import contracts throughout the
  refactor while preparing the implementation for final consolidation under
  the dedicated `analysis.incremental` subsystem.

### Regression and contract alignment

- Updated historical Stage 2 tests to the current LIVE artifact-consumption
  freshness contract.
- Updated module-context tests to validate required fan-in and fan-out
  behavior without rejecting the newer topology and cached-analytics fields.
- Updated failure-injection tests to target the extracted RefreshPlan
  execution boundary while preserving Copy-on-Write rollback guarantees.
- Updated registry failure fixtures so they exercise updates that genuinely
  require persistent identity synchronization.
- Updated reverse-blast-radius fixtures so they exercise modeled dependency
  changes instead of implementation-body-only no-ops.
- Verified the Stage 3 critical regression ratchet with 139 passing tests.
- Consolidated the incremental analysis subsystem under
  `analysis/incremental`, moving the canonical engine implementation to
  `analysis/incremental/engine.py`.
- Replaced the former top-level `analysis/incremental_engine.py`
  implementation with a lightweight backward-compatible facade, preserving
  all existing engine, result and degree-delta import paths.
- Added package-level incremental-engine exports while preserving reference
  identity between legacy, canonical and package-level imports.
- Completed the incremental-engine decomposition with clear boundaries for
  orchestration, source preparation, RefreshPlan execution, state
  materialization and pure graph operations.
- Reduced the historical `incremental_engine.py` from approximately 802 lines
  to an 18-line compatibility facade, with the canonical orchestrator now
  isolated in `analysis/incremental/engine.py`.

## [1.2.0-beta Patch — Scoped analysis guards] - 2026-08-15

- Removed the deprecated expression-based ``query_canonical_state`` and
  ``query_canonical_state_bounded`` MCP endpoints together with their private
  ``eval`` runtime and transport limiter. Canonical ad-hoc queries now use only
  the versioned, bounded ``query_canonical_projection`` contract.
- Blocked layer and single-file analysis when the selected target resolves
  outside the chosen repository root. GUI users receive an immediate warning;
  facade/MCP callers receive a `ValueError` before an identity or analysis job
  can be created.
- Reset the determinate GUI progress bar on success and error as well as
  cancellation, preventing a completed operation from leaving a stale percent.
- Split project, layer and single-file analysis into explicit end-to-end
  progress stages. Long report generation, JSON/Markdown serialization,
  snapshot persistence and finalization now retain a sub-100% progress range;
  the GUI refreshes its global ETA once per second even when an individual
  stage has no item-level callback.
- Repaired ``Open CMD log`` as a separate tail of the process-wide Contextor
  stdout/stderr log, including analysis stages, test output and uncaught
  tracebacks. The lower GUI operation log remains permanently visible and
  independent. Removed the separate GUI ``LIVE suite`` button; Test suite
  remains the full run, including LIVE tests.
- Added cooperative STOP checkpoints throughout dependency graph resolution,
  global/layer report orchestration and graph analytics (matrix construction,
  PageRank, betweenness, HITS, Jaccard clusters and module assembly). Windows
  Git probes and pytest subprocesses now run without flashing helper consoles;
  only the explicitly requested CMD program log creates a visible console.
- Corrected the CMD tail launcher so its visible console inherits stdout and
  remains open while following the process log. Test-suite failures are now
  logged as ``[FAILED]`` rather than receiving the runner's generic success
  message. MCP project jobs validate hydrated canonical state before starting
  LIVE IPC, avoiding a slow orphan service path after invalid hydration.
- Made ``get_artifacts_for_module`` genuinely LIVE-first: canonical symbol
  state now works without an ``artifacts_compact`` report, while an available
  report remains an optional source of saved consumer evidence. The response
  reports only the data sources that were actually used.
- Repaired the optional program-log console: the checkbox again has its own
  tooltip and launches a persistent Python tail inside a real CMD window,
  without PowerShell quoting or prompt fall-through. The log now records
  low-volume technical builder, report-pipeline and graph-analytics events;
  GUI progress stages remain confined to the lower operation log.
- Made desktop and MCP single-file reports reuse canonical LIVE/snapshot
  modules, dependency graph and artifact-consumption evidence. The selected
  file is refreshed incrementally, while repository indexing, graph rebuild
  and global artifact reparsing are now fallback-only operations when no
  complete canonical state exists. LIVE IPC request/publish timeouts are
  configurable per call and covered by regression tests.
- Added the same canonical warm path to layer reports and documented cold-start
  behavior: the first scoped run builds the repository baseline, while later
  layer/file iterations reuse LIVE state. Broke the real ``paths`` ↔
  ``repository_identity`` cycle through a dependency-neutral storage-root
  module and replaced colliding module-level ``SCHEMA_VERSION`` names with
  domain-specific canonical-query and LIVE-state constants.
- Made global MCP analysis publication status durable and independent from the
  report result. ``get_analysis_status`` now preserves
  ``live_publish_status``, the published revision and any timeout/failure
  warning across later polling and server restarts; failed publication no
  longer disappears behind a generic successful-analysis message.

## [1.2.0-beta Patch — Central repository identities] - 2026-08-14

- Moved creation and lookup of persistent identity dictionaries to Contextor's
  central `.contextor/repositories/` directory. Analyzed repositories are no
  longer modified to hold registries or `.gitignore` entries.
- Namespaced every registry directory as `<repo_name>__<repo_id>` and resolved
  identities by the canonical `root_path` stored in `repo.meta.json`.
- Bound AppData LIVE snapshots to durable repository IDs and added GUI-startup
  cleanup for orphaned `ctx_*` cache directories whose IDs no longer exist in
  the central registry. Startup cleanup also removes pytest cache directories
  and legacy path-keyed caches only after the same registered root has a
  complete snapshot under its current repository ID.
- Added per-repository desktop LIVE watchers so changing the GUI root preserves
  updates for repositories already watched in the current desktop session.
- Full, layer and single-file analysis now initialize the same central identity;
  scoped analysis success refreshes the permanent Repo ID shown by the GUI.

## [1.2.0-beta Patch — Parts II–IV] - 2026-08-13

### Part II — Reliable reporting and persistent identities

- Repaired global, layer and single-file report consistency, including real
  module/symbol identities, correct Markdown context, Git headers and
  timestamped physical snapshots alongside stable canonical filenames.
- Unified GUI and MCP indexed report parsing. Exact module paths, dotted module
  names, qualified symbols, active/recovery registries and public-API filtering
  now share one resolution path with explicit ambiguity diagnostics.
- Corrected artifact consumption, dependency classification, test discovery,
  layer module accounting and false name-collision handling for local symbols.
- Preserved per-repository identity isolation, generation-based IDs, recovery
  dictionaries and reusable slot bookkeeping across incremental updates.

### Part III — LIVE model and LLM-oriented MCP tools

- Added one authenticated localhost Canonical LIVE owner in RAM, shared by the
  desktop watcher and MCP through revisioned IPC. Atomic disk snapshots are now
  recovery state rather than the primary cross-process communication path.
- Desktop startup reconnects to existing LIVE state and file create/edit/delete
  events update it automatically after the initial full analysis. MCP refreshes
  its local adapter whenever the shared revision advances; manual `update_file`
  remains a fallback and routes through the shared owner when available.
- Added the GUI `LIVE suite` button and pytest `live` marker. The complete Test
  suite still includes LIVE, while the focused button runs only LIVE unit,
  socket/process integration, watcher, restart, persistence and MCP regressions.
  LIVE tests isolate output/cache/state paths from production directories.
- Made project architecture, artifact blast radius, file-edit context and layer
  isolation LIVE-first. Missing JSON reports no longer disable structural
  answers; reports are optional metric/cluster enrichment and historical output.
- Added persistent canonical LIVE state that survives MCP restarts and supports
  incremental file addition, modification and deletion without a global rebuild.
- Added versioned ``describe_canonical_state`` and
  ``query_canonical_projection`` endpoints. The v1 JSON query contract exposes
  normalized modules, artifacts and dependencies with per-field operator
  allowlists, deterministic ordering, strict null semantics, structural errors
  and hard request/result limits; it never evaluates expressions or exposes
  raw Python objects. Expression-based canonical queries are now legacy.
- Added semantic file deltas for symbols, signatures, normalized AST body
  fingerprints, imports and removed artifacts. These complement—rather than
  replace—the normal source and Git diff.
- Added bounded, documented MCP context tools for indexed report extraction,
  module APIs, blast radius, file-edit context, registry lookup and safe
  canonical-state projection.
- Added `get_symbol_implementation`: an AST-backed two-phase MCP reader.
  Its preview reports the cost of complete response variants before source is
  fetched; fetch returns only whole classes, functions or explicitly selected
  methods, never arbitrary line fragments.
- Made project, layer and single-file analysis non-blocking. Analysis calls now
  return durable job IDs with progress and terminal status, eliminating client
  timeouts during long report generation.
- Completed global analysis jobs now expose bounded parser/read coverage gaps
  through ``analysis_coverage.skipped_python_files``, including syntax-error
  counts, structured first parser ``line_number`` and ``column_number`` when
  available, and the original indexer reason for each skipped Python file.
- `get_module_context` now combines current LIVE dependencies with clearly
  labelled saved or deferred metrics, including newly created modules before a
  full report refresh.

### Part IV — Refactor guidance and final MCP completeness

- Used Contextor's own hotspot and blast-radius data to split the reporting
  orchestrator into dedicated `artifact_pipeline` and `layer_pipeline` modules.
  The reporting pipeline's outbound degree fell from 15 to 10 while preserving
  the package-level public API.
- `get_report_diff` now compares consecutive canonical runs even when both
  working-tree states share the same commit SHA, and records comparison headers
  plus regression classification.
- `get_layer_isolation` now accepts nested layer paths and dotted layer names
  while retaining the full requested layer identity.
- `tests_covering` now reports bounded static reachability through aliases,
  re-exports and facades, including distance and an evidence path. It is
  explicitly structural evidence, not runtime line coverage.
- Fixed public collision collection so classes nested inside functions are not
  misreported as module-level APIs.
- Validated the final paths with focused unit/regression suites and temporary
  repository modules; removed probes were correctly transferred to recovery.

---

## [1.2.0-beta] - 2026-08-06

### Added

#### Model Context Protocol (MCP)

- Introduced a native FastMCP server, transforming Contextor into an LLM-oriented query engine.
- Added `MCP_installer.bat` for automated MCP environment setup.
- Added Level-3 `get_file_edit_context` providing a complete single-shot editing context.
- Added `get_report_diff` for architectural regression analysis between runs.
- Added architectural boundary validation in `get_layer_isolation`.
- Added secure sandbox execution for `query_json_data`.

#### Graph Analytics

- Added `graph_analytics.json` report.
- Added fan-in, fan-out and export-degree metrics.
- Added PageRank, Betweenness, Hub, Authority and Bridge centrality scores.
- Added module visibility classification (`public`, `internal`, `private`).
- Added weighted dependency matrix with dependency type classification.
- Added Jaccard complete-linkage clustering.
- Added dependency type breakdown statistics.

#### Reporting

- Added strict separation between global, layer and single-file reports.
- Added dedicated layer index dictionaries.
- Added Git-aware report diff engine.
- Added Git metadata to single-file reports.
- Added independent metrics and hotspots for the `tests` layer.
- Added automatic timestamp-based report versioning.

---

### Changed

#### Reporting Engine

- Replaced raw JSON reading with synthesized MCP query endpoints.
- Replaced GUI parser string search with indexed lookup.
- Replaced connected-component clustering with complete-linkage clustering.
- Optimized report routing and index dictionary management.
- Optimized LLM context generation using compact indexed structures.

#### Architecture

- Split `engine.py` into `generators.py` and `io_manager.py`.
- Split `generators.py` into dedicated generator modules.
- Retained backward-compatible facades after refactoring.
- Eliminated oversized architectural hotspots.

#### Performance

- Removed generation of `artifacts.json` and `artifacts_usage.json`.
- Standardized on compact indexed artifact reports.
- Added extraction limits for clusters and usage details.
- Reduced disk I/O and report size significantly.

---

### Fixed

#### MCP

- Fixed Windows multiprocessing initialization (`freeze_support()`).
- Fixed stdout corruption breaking JSON-RPC communication.
- Fixed argument ordering in `analyze_single_file`.
- Fixed layer normalization in `get_layer_isolation`.
- Fixed incorrect `module_count` returned by `get_project_architecture`.
- Fixed incorrect `risk_score` calculation in `get_file_edit_context`.
- Fixed Windows Codex MCP analysis hangs by isolating Git from the JSON-RPC stdin stream, using non-interactive Git subprocesses and native HEAD/ref resolution; verified all 17 MCP tools end to end.
- Added identity-verified MCP process cleanup for normal shutdown and orphan recovery on the next server start.

#### Reporting

- Fixed missing layer index dictionaries.
- Fixed global index overwrite detection.
- Fixed Rewrite Index fallback logic.
- Removed thread-unsafe Rewrite button from the JSON Parser window.

---

### Security

- Replaced unrestricted `eval()` in `query_json_data` with a sandboxed execution environment.

---

### Developer Experience

- Improved MCP support for LLM workflows.
- Added architectural context pills for AI-assisted refactoring.
- Improved report discoverability and automatic report resolution.

---

### Validation

- Verified all MCP tools in a full end-to-end test.
- Cross-validated generated reports against the analyzed source code.
- Confirmed correct isolation of global, layer and single-file report scopes.
- Verified zero cross-scope index overwrites.
### Known limitations

- The graph cache in `core/graph/incremental.py` remains in-memory only,
  so it never hits in a single CLI run.
- Comments and docstrings mix English and Polish.

## [Patch] - 2026-08-05

### Added & Improved

- **Global & Layered Reporting Separation**: Global reports are now robust and logically separated into distinct layers (e.g., `contextor` vs `tests`). Each layer receives its own specific metrics, structure, artifacts, and summary without mixing contexts.
- **Comprehensive Metrics**: Added complete global metrics (e.g., `density_hard`, `edges_hard`) and detailed per-layer `per_module` metrics (`in/out degree`, `internal_in/out`) to accurately evaluate hotspots and isolated code.
- **Hotspots, Technical Debt & Action Items**: Outbound hotspots and structural bottlenecks are now directly linked with actionable items (e.g., `WARNING: Refactor '...' (out_degree=X, type=OUTBOUND_HOTSPOT)`). Technical debt is synthesized in a normalized `debt_summary`.
- **Zero-Collision Validations**: Namespace collisions and dependency cycles are properly monitored. Stable analysis explicitly validates and reports `total_collisions: 0` and `cycle_count: 0`, guaranteeing analysis fidelity.
- **Tests Layer Observability**: `tests` is now treated as an independent architectural boundary with its own structural filtered metrics and hotspots, enabling analysis of test impact on the production architecture without noise.
- **Robust Strict String-Based GUI Parser**: Replaced the deep-search algorithm with a highly performant, short-circuiting strict string parser to definitively prevent false-positive matches of modules vs symbols.
- **Automated Output Routing & Timestamps**: All generated reports are now safely tagged with a `datestamp` to track history. High-risk layer reports are safely isolated into `[repo]_high_risk_layers_[datestamp]` subfolders.
- **Test Suite Enhancements**: Expanded the test suite coverage to accurately test the updated parsing mechanisms and architectural isolation logic.

- **Git & Diff Engine Integration**: Contextor now deeply integrates with Git context. Added a dedicated 
epo_state module and diff_engine to automatically identify previously generated reports, compute deltas across runs (hotspots, cycles, layers, and debt score), and accurately evaluate technical regression or improvements across the repository.
- **Granular Git Impact Reports**: Single-file reports now feature a dedicated git section containing recent commits, authors, and truncated file patches, allowing the LLM to understand immediate local file changes alongside architectural implications.

- **Model Context Protocol (MCP) Server**: Introduced a native FastMCP server allowing LLMs (like Claude) to directly invoke Contextor. The server exposes tools for global analysis (analyze_project), layered analysis (analyze_layer), single-file insights (analyze_single_file), artifact filtering (filter_artifacts), and reading raw JSON reports.
- **MCP Environment Installer**: Added MCP_installer.bat to safely handle environment detection and installation of MCP dependencies alongside Contextor.

- **Engine Refactoring**: Split the oversized `contextor.core.reporting_engine.engine` module (SRP violation) into `generators.py` (business logic) and `io_manager.py` (I/O operations). This decoupling significantly improves maintainability and testability. Updated `facade.py` imports and completely refactored the test suite to include robust integration tests. The old engine module has been safely backed up to `legacy/engine.py`.
- **I/O Optimization & Bloatware Removal**: Completely eliminated the generation and disk-writing of massive `artifacts.json` (70 MB) and `artifacts_usage.json` (140+ MB) reports. Contextor now generates and relies exclusively on a highly optimized, index-based `artifacts_compact.json`, reducing disk I/O latency and saving hundreds of megabytes per run.
- **Strict Indexed Extraction Engine**: Rewrote the core search/filtering engine in `gui_parser.py`. Replaced the slow, raw string-matching algorithm (based on `json.dumps` serialization) with a blazing-fast index-based traversal, resolving definitions and consumers against the compact modules array.
- **LLM Token Efficiency Maximization**: The output "single LLM context" subsets generated by the GUI parser now natively retain the `compact` integer-indexed format. This drastically minimizes the input token cost while supplying LLMs with a perfect structural "blast-radius" map.
- **Cluster & Detail Saturation Limiting**: Introduced strict safeguards (`MAX_CLUSTERS = 30` and `MAX_USAGE_DETAILS = 15`) in `artifact_usage_report.py` to truncate long-tail extraction candidates and AST detail bloat, preventing infinite context scaling on massive codebases.

## [Patch] - 2026-08-06

### Added

- **Graph Analytics Report** (`graph_analytics.py`): A new dedicated report generated alongside existing reports for all three reporting levels — full repository, per-layer, and single-file. Addresses the following gaps missing from previous reports:
  - `fan_in` (consumer count), `fan_out` (provider count), `export_degree` (number of artifacts exported by a module)
  - `visibility` classification per module: `public` (consumers outside its own layer), `internal` (consumers only within the same layer), `private` (no consumers)
  - Architectural `layer` classification: `runtime`, `contract`, `engine`, `ui`, `cli`, `adapter`, `tests`
  - Graph-centrality scores: `betweenness`, `pagerank`, `hub_score`, `authority_score`, `bridge_score` — all computed in pure Python without external dependencies
  - **Module Dependency Matrix**: weighted, indexed module-to-module dependency map with `weight` (shared artifact count) and `dep_types` (`call`, `inheritance`, `import`) for each directed edge
  - **Jaccard-similarity clusters** using complete-linkage algorithm (threshold ≥ 0.30): replaces the previous connected-components approach that produced a single cluster containing the entire repository (`size=102`); new clusters are semantically tight (`size=2–15`)
  - `dependency_type_breakdown`: global aggregation of edge types across the entire dependency matrix
  - Report is fully indexed (compact integer IDs via `IndexDictionary`) consistent with all other Contextor reports; human-readable form available via the GUI "Rewrite Index" button

- **Index Dictionary Deduplication**: When saving a new `index_dictionary.json`, the engine now checks for an existing dictionary with the same base name:
  - Identical content → old file is silently removed and replaced by the new one
  - Different content → old file is renamed with an `_outdated` suffix before writing the new one
  - Applies to all three reporting paths: full project (`save_all_reports`), layer, and single-file (`analyze_single_file`)

- **Contextor Query Layer (MCP Server)**: Completely refactored `mcp_server.py` to serve as a specialized query layer optimized for Large Language Models.
  - Replaced raw JSON file-reading tools with dynamic endpoints: `get_project_architecture`, `get_module_context`, `get_artifact_blast_radius`, and `get_layer_isolation`.
  - Added automatic path resolution (`_find_latest_report`) so LLMs no longer need to know the exact timestamped filenames of reports.
  - LLMs now receive perfectly sized, synthesized insights (including reverse-mapped string dependencies) instead of massive arrays of integer indices.

### Fixed

- **MCP Server on Windows** (`mcp_server.py`): Added `multiprocessing.freeze_support()` call in the `__main__` block. Without it, `ProcessPoolExecutor` inside `ContextorFacade.analyze_project()` caused a `RuntimeError` during subprocess bootstrapping on Windows, making every MCP `analyze_*` tool call fail silently.
- **MCP Stream Corruption**: Forced all internal Contextor progress logs to be routed to `sys.stderr`, preventing stdout pollution from breaking the JSON-RPC communication stream used by MCP.
- **MCP Tool `analyze_single_file`**: Fixed an argument ordering bug where `repo_root` and `file_path` were swapped when calling the facade.
- **MCP Tool `get_layer_isolation`**: Fixed a bug where passing a full path (e.g., `contextor/core`) would fail to match the layer index; it now normalizes the input automatically.

### Architecture Refactoring
- **Generators Hotspot Elimination**: Split the massive `contextor.core.reporting_engine.generators` module (674 lines) into four domain-specific components: `summary_generator.py`, `structure_generator.py`, `collisions_generator.py`, and `layer_slicer.py`. The original `generators.py` was retained as a backward-compatible re-exporting facade. This refactoring completely eliminated the module from the top 5 global architectural hotspots (score dropped from 0.84 to unlisted), drastically reducing project technical debt.
- **MCP Context Pill**: Added a new Level-3 MCP tool `get_file_edit_context`. It provides LLMs with a specialized, single-shot context pill prior to editing a file, combining module metrics, API signature blast radius, and dependency trees into one response.

### Bug Fixes & UI Enhancements
- **Layer Report Index Dictionary Omission**: Fixed a bug where isolated layer reports failed to save their own `index_dictionary.json` file. `layer_slicer.py` now correctly surfaces the layer-specific index, and `io_manager.py` saves it with the correct layer prefix (e.g., `Contextor_Repo_core_index_dictionary_[datestamp].json`).
- **Global Index Overwrite Prevention**: Fixed an aggressive wildcard glob in `_save_index_dictionary_with_dedup` that was incorrectly flagging layer-specific index dictionaries as "outdated" versions of the global repository index and renaming them. The pattern matcher now strictly verifies segment length.
- **Smart Rewrite Fallback**: Upgraded the GUI "Rewrite Index -> Txt" tool to reliably locate the global repository index. It now searches for an exact datestamp match (even if outdated), explicitly ignores layer-specific or single-file dictionaries (by preferring the shortest filename), and surfaces a robust UI `MessageBox` fallback confirmation if it needs to use the latest available global index.
- **Parser GUI Cleanup**: Removed the redundant, thread-unsafe "Rewrite Index" button from the JSON Parser window, consolidating this capability exclusively to the main application window which properly supports native file dialogs and prompts.
- **MCP `get_project_architecture` — wrong `module_count` field**: Fixed a wrong key lookup (`metrics.global_module_count` → `metrics.nodes`). The tool was returning `module_count: 0` on every call despite the summary report containing the correct value.
- **MCP `get_file_edit_context` — `risk_score` always zero**: Fixed by replacing the non-existent `hotspot_score` key lookup (which lives in `summary.json`, not in `graph_analytics.json`) with a computed proxy based on `(betweenness + hub_score) / 2`, sourced correctly from `graph_analytics.json`.

### Production Test — 2026-08-06
Full end-to-end production test covering all 10 MCP tools and all three report types (full project, layer, single-file). All tools passed. Report data cross-validated against actual source code — data found to accurately reflect the real state of the codebase. Index dictionary separation between global, layer, and single-file scopes confirmed working with no cross-scope overwrites.

### MCP Refinements & Security Updates
- **Secure Sandbox for `query_json_data`**: Replaced the unrestricted `eval()` call with a strictly sandboxed execution environment (whitelisted built-ins only) to prevent arbitrary code execution vulnerabilities.
- **Accurate `risk_score` for Edit Context**: Fixed `get_file_edit_context` to correctly extract the true `hotspot_score` from `summary.json`, using the centrality metrics from `graph_analytics.json` only as a secondary fallback.
- **Test Coverage Context**: Enhanced `get_file_edit_context` to expose `tests_covering` by identifying modules from the `tests.*` layer that depend on the target module, giving LLMs immediate visibility into available test coverage.
- **Layer Boundary Violations**: Upgraded `get_layer_isolation` to detect and report architectural boundary violations (e.g., when a lower-tier layer like `ui` directly imports a higher-tier layer like `runtime`), enforcing strict layer hierarchy (`tests > ui/cli > contract > engine > runtime > adapter`).
- **Regression Analysis Tool (`get_report_diff`)**: Added a new MCP tool to expose the `report_diff` functionality. It computes the delta between the last two analysis runs, surfacing newly introduced hotspots, resolved debt, and cycle changes directly to the LLM.

## [Patch] - 2026-08-07

### Refactored & Improved

- **Single File Analysis Builders (Zombie Modules Cleanup)**: Refactored the oversized `single_file_analysis.py` module and its associated `context_builders.py`. Extracted the logic into a new structured pipeline with dedicated layer builders (`layer0_builders.py`, `layer1_builders.py`, `layer2_builders.py`, `layer3_builders.py`) managed by a new `registry.py` under `contextor/core/single_file/builders/`. The old "zombie" monolithic files were safely archived to the `legacy/` directory.
- **Reporting Engine Pipeline Extraction**: Refactored the massively overgrown `io_manager.py` (which previously handled both I/O and pipeline orchestration). Extracted the high-level analysis flow, dependency resolution, and layer slicing logic into a dedicated `pipeline.py` module, strictly enforcing the Single Responsibility Principle and reducing `io_manager.py` complexity by over 400 lines.
- **Persistent Identity Registry**: Completely refactored the core identity management of the system. Removed all local integer-based ID generation (`IndexDictionary`) from individual reports. All modules and artifacts are now tracked by a central `PersistentIdentityRegistry` located in `.contextor/repositories/<repo_id>`. IDs are now globally stable string identifiers (format `{gen}/{slot}`, e.g., `"17/4"`).
- **Atomic Operations & Locking**: The registry enforces strict atomicity using system-level file locks (`.lock`) and atomic renames (`fsync` + `rename`) to guarantee identity consistency even during parallel runs or abrupt crashes.
- **Reporting Engine Updates**: Removed the deprecated `_save_index_dictionary_with_dedup` from the engine (`io_manager.py`, `pipeline.py`, `facade.py`). Reports no longer output or rely on `*_index_dictionary.json` files in the output directory. They now operate strictly by querying the active `PersistentIdentityRegistry` context.
- **MCP Server Modernization**: Updated the FastMCP server (`mcp_server.py`) to directly query the `PersistentIdentityRegistry` instead of loading the removed index dictionary files from disk. 
- **New MCP Tool (`get_project_index`)**: Added a new MCP tool `get_project_index(repo_path: str)` to expose the active mapping of internal registry IDs to their actual module and artifact paths, allowing external LLM agents to accurately translate compact identifiers found in reports.
- **GUI Parser String ID Support**: Updated `gui_parser.py` (specifically `parse_and_filter_json` and `rewrite_index_to_text`) to correctly parse and process the new string-based generation/slot IDs, removing legacy integer coercion bugs.
- **Test Suite Updates**: Removed obsolete index-saving assertions and passed the mock `PersistentIdentityRegistry` instances into unit tests for `artifact_usage_report`, `generators`, and `reporting_single_file`.

## [Patch] - 2026-08-07 (Session 2)

### Fixed & Improved

- **Pipeline Artifact Bug Fix**: Fixed a critical bug in `pipeline.py` where a typo (`symbols` instead of `artifacts`) incorrectly marked all artifacts as orphaned, causing massive ID generation bloat (e.g., `A.../2`, `A.../3`).
- **Layer Slicer Index Passing**: Fixed `analyze_layer` (`layer_slicer.py`) crashing with `index_dict must be provided to build_module_index` by correctly spanning the registry transaction in `facade.py` to include artifact report compaction.
- **Flattened Local Registry**: Removed redundant `repositories/<repo_name>` subdirectories from `PersistentIdentityRegistry`. The registry now stores its files directly in the root `.contextor/` folder.
- **Indexed Structural Reports**: Updated `generate_structure_report` and `layer_slicer.py` to correctly map all string-based `hard_edges` and `soft_edges` to their compact registry IDs, drastically reducing report size and unifying the ID schema across all reports.
- **Test Artifact Cleanup**: Fixed `tests/test_reporting_single_file.py` to use Pytest's `tmp_path` fixture instead of a hardcoded `"dummy_path"`, and removed the leaked `dummy_path` folder from the project root.
- **End-to-End Validation**: Performed a full E2E test via the Model Context Protocol (MCP) server on the refactored architecture. All MCP query endpoints (`analyze_project`, `analyze_layer`, `get_project_architecture`, `get_project_index`, `get_module_context`) successfully passed and correctly interface with the centralized `.contextor/` registry.
