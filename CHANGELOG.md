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
