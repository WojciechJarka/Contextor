# Walkthrough

## TASK=BOTTLENECKS-0A CURRENT PERFORMANCE BOTTLENECK MAP

Discovery/audit only. No production code or tests were modified. No full
pytest, MCP restart, LIVE restart, or new full-repository analysis was run.

## CURRENT_FULL_ANALYSIS_PATH

Authoritative path confirmed through Contextor MCP and source spans:

```text
CLI/MCP/GUI entry
  -> run_full_analysis_exclusive (full_analysis_coordinator.py)
  -> ContextorFacade.analyze_project (core/api/facade.py:301)
  -> repository identity + reset_caches
  -> index_repository (symbol_engine/indexer.py:260)
  -> collision facts + trie/package-root
  -> get_cached_graph / serial build_graph (facade.py:354)
  -> validate
  -> graph metrics + cycles + debt
  -> execute_global_pipeline (reporting_engine/pipeline.py:32)
  -> build_artifact_pipeline (reporting_engine/artifact_pipeline.py:37)
  -> generate_artifact_usage_report
  -> compact/index registry + graph analytics
  -> report/layer persistence
  -> RepositoryAnalysisState construction
  -> dependency matrix + shared-usage clusters
  -> save_engine_state
  -> LIVE publish
```

Stage classification:

| Stage | Scope | Parallelizable | Current execution | Finding |
|---|---|---:|---|---|
| file discovery and import extraction | PER_FILE | yes | ProcessPool | one submitted task per Python file |
| collision fact extraction | PER_FILE | yes | serial parent loop | separate pass over current modules |
| trie/package-root construction | GLOBAL | no | serial | required before graph resolution |
| dependency graph resolution | PER_MODULE/GLOBAL result | per-module in principle | serial | `build_graph` sorts and visits every module |
| graph validation | GLOBAL | limited | serial | consumes complete graph |
| metrics, cycles, debt | GLOBAL | limited | serial | whole graph traversals/aggregations |
| artifact usage collection | PER_MODULE plus GLOBAL index | yes | ProcessPool | one task per module, then serial assembly |
| report compaction and analytics | GLOBAL | limited | serial | derived from full artifact report and graph |
| persistence and publication | GLOBAL | no | serial | exact snapshot, FileState payload, then LIVE publish |

## CURRENT_INCREMENTAL_PATH

`DesktopWatcher.poll_once` scans the repository (`live_state/watcher.py:246-249`),
selects changed paths, and calls LIVE `update_file`. The analytical path is:

```text
watcher.poll_once
  -> IncrementalAnalysisEngine.update_file
  -> prepare_source_update / prepare_deleted_module_update
  -> RefreshPlanner.plan_refresh
  -> execute_refresh_plan
  -> Copy-on-Write candidate state
  -> targeted patch/recompute/graph phases
  -> RAM commit + FileState acknowledgement
  -> persistence + canonical publication
```

Reused from canonical state: modules, artifact records, usage facts, graph,
trie/package root, metrics, topology analytics, cached analytics, cycles,
collision facts, and artifact-consumption data unless the refresh plan marks a
family for patch/recompute. Recomputed after a change when planned: the changed
file's syntax/import/symbol/usage/collision facts; affected consumer slices;
changed module graph edges (or the complete graph for add/delete); selected
macro/advanced metrics, cycles, cached analytics, collisions, and blast radius.
No source I/O occurs in `execute_refresh_plan` for planned consumer recomputes.

## CURRENT_PERFORMANCE_BASELINE

Primary evidence was existing runtime trace data, not historical timings.
Across the available trace set:

```ini
FS_CHANGE_DETECTED: n=1906, median scan_ms=1219, p90=1640, max=7484
UPDATER_END:       n=1559, median elapsed_ms=265,  p90=1594, max=171594
WATCH_UPDATE_END:  n=1037, median elapsed_ms=1922, p90=4453, max=59703
INCREMENTAL_END:   n=1052, median elapsed_ms=47,   p90=2094, max=171031
```

Representative trace `logs/contextor_runtime_20260828_214144_693_9688.jsonl`
shows `scan_ms=1313` before an update, an unchanged updater of about 344 ms,
and a complete watcher update of about 2516 ms; persistence in the same event
completed in about 285 ms. This is current evidence of material per-change fixed
cost, not evidence of a LIVE correctness regression.

The current canonical state observed through Contextor MCP is fresh at revision
5488, with 316 modules, 972 hard edges, 170 soft edges, zero cycles, and zero
name collisions. The current report output at
`output/Contextor_Repo_20260829_182043/Contextor_Repo_summary.json` identifies
`contextor.core.api.facade` as the top hotspot and
`contextor.core.reporting_engine.pipeline` as an outbound hotspot.

No trace event records a complete full-analysis wall-clock breakdown. Full-run
cost claims below are therefore architectural evidence or inference, not
measured timings. Existing historical full-analysis timings were deliberately
not treated as current truth.

## CONTEXTOR MCP ARCHITECTURAL EVIDENCE

Contextor MCP revision 5488 reported these bounded topology/consumer facts:

| Module | Direct consumers | Transitive consumers | Other signal |
|---|---:|---:|---|
| `core/symbol_engine/indexer.py` | 20 | 129 | runtime, risk 0.226 |
| `core/reporting_layer/artifact_usage_report.py` | 16 | 128 | engine |
| `core/analysis/incremental/plan_executor.py` | 6 | 106 | runtime, risk 0.2044 |
| `core/analysis/incremental/engine.py` | 3 | 106 | single-file graph analytics: betweenness=1.0, hub=1.0, bridge=0.847222 |
| `core/analysis/full_analysis_coordinator.py` | 7 | 74 | runtime |

The full report's graph analytics also ranked `core.api.facade` with
in-degree 27/out-degree 28, `mcp_server` with 5/29,
`incremental.plan_executor` with 6/15, and `reporting_engine.pipeline` with
4/12. These are ownership/bridge signals, not proof that every call is slow.

## P0_BOTTLENECKS

### P0-1 — watcher scan cost on every poll with a candidate change

```ini
RANK=P0-1
OWNER_SYMBOL=DesktopWatcher._scan / DesktopWatcher.poll_once
FILE=contextor/core/live_state/watcher.py:107,246-249
EXECUTION_STAGE=incremental/LIVE change detection
EVIDENCE=MEASURED; 1906 trace samples, median scan_ms 1219, p90 1640
APPROX_COST=~1.22 s median before analytical update; ~1.92 s median full watcher update
ROOT_CAUSE=full recursive *.py snapshot scan is repeated for polling cycles
OPTIMIZATION_CLASS=change-detection scheduling/snapshot reuse
ARCH_RISK=high; watcher ownership and startup/reconciliation semantics are protected
CONFIDENCE=high for cost, medium for dominant user-visible share
```

This is recorded but is not selected as the first implementation target because
the task explicitly excludes reopening watcher/LIVE lifecycle stabilization
without a demonstrated correctness regression, and the trace demonstrates
cost rather than a correctness regression.

### P0-2 — full artifact report uses one ProcessPool task per module and reparses

```ini
RANK=P0-2
OWNER_SYMBOL=collect_module_artifacts / _process_single_artifact_module
FILE=contextor/core/reporting_layer/artifact_usage_report.py:145-225
EXECUTION_STAGE=full analysis, artifact/reference extraction
EVIDENCE=ARCHITECTURAL_EVIDENCE; 316-module current state, one task per module,
initializer receives modules/root/reference_index, worker calls extract_file_symbols
APPROX_COST=unmeasured current wall time; 316 task submissions plus worker startup,
payload transfer, result transfer, and one source parse per worker module
ROOT_CAUSE=per-module granularity and worker-side symbol extraction are separate
from parent collision/reference passes
OPTIMIZATION_CLASS=parallel batching/work-unit and parse reuse
ARCH_RISK=high; artifact parity, worker isolation, and canonical report invariants
CONFIDENCE=medium; material by structure, no current full-run timing
```

### P0-3 — affected-consumer recompute copies/scans the complete consumption map

```ini
RANK=P0-3
OWNER_SYMBOL=_rebuild_consumer_slice via execute_refresh_plan
FILE=contextor/core/analysis/incremental/plan_executor.py:137-200,257-575
EXECUTION_STAGE=incremental RECOMPUTE/artifact-consumption patch
EVIDENCE=ARCHITECTURAL_EVIDENCE plus current trace; plan executor has 106
transitive consumers and the slice rebuild scans every target to remove one consumer
APPROX_COST=O(number of canonical artifact targets) per recomputed consumer,
then copies changed entries; exact current share unmeasured
ROOT_CAUSE=Copy-on-Write safety is implemented as a full target-map scan for each
consumer slice
OPTIMIZATION_CLASS=bounded reverse-index/targeted copy-on-write redesign
ARCH_RISK=high; exact-successor, ambiguity, freshness, and invalidation contracts
CONFIDENCE=medium
```

## P1_BOTTLENECKS

### P1-1 — duplicate parsing in incremental preparation

```ini
RANK=P1-1
OWNER_SYMBOL=prepare_source_update
FILE=contextor/core/analysis/incremental/preparation.py:139-249
EXECUTION_STAGE=incremental PREPARE
EVIDENCE=ARCHITECTURAL_EVIDENCE; source is read/ast.parse at 150-151, then
read_imports calls parse_source, and extract_file_symbols calls parse_source again
APPROX_COST=up to three source/AST passes for one changed file; updater median 265 ms
in trace, but parse-only share is not separately measured
ROOT_CAUSE=three consumers accept file paths instead of sharing the already parsed AST
OPTIMIZATION_CLASS=single-parse fact extraction
ARCH_RISK=medium; syntax/error parity and extractor API compatibility
CONFIDENCE=high for duplication, medium for materiality
```

### P1-2 — serial full graph resolution

```ini
RANK=P1-2
OWNER_SYMBOL=build_graph
FILE=contextor/core/graph/graph.py:111-155
EXECUTION_STAGE=full analysis dependency graph
EVIDENCE=ARCHITECTURAL_EVIDENCE; deterministic loop over all sorted modules and
get_cached_graph invokes one builder call
APPROX_COST=one serial pass over 316 current modules; no current stage timing
ROOT_CAUSE=per-module edge resolution is structurally separable but executed serially
OPTIMIZATION_CLASS=parallel graph edge resolution with deterministic reduction
ARCH_RISK=medium/high; ordering, cancellation, cache, and graph parity
CONFIDENCE=medium
```

### P1-3 — full-run source parsing is repeated across independent passes

```ini
RANK=P1-3
OWNER_SYMBOL=analyze_project plus collision/reference/artifact owners
FILE=contextor/core/api/facade.py:332-342; reporting_layer/artifact_usage_report.py:145-164
EXECUTION_STAGE=full analysis indexing -> collision facts -> reference index -> artifacts
EVIDENCE=ARCHITECTURAL_EVIDENCE; indexer parses imports, collision extraction consumes
module.ast_tree, reference index consumes module.ast_tree, and artifact workers call
extract_file_symbols on paths
APPROX_COST=multiple AST/source passes per repository file; exact count/timing depends
on cache/process boundaries and is not claimed as measured
ROOT_CAUSE=AST ownership is not shared across process boundaries and report workers
reconstruct symbol facts from paths
OPTIMIZATION_CLASS=run-scoped parse/fact ownership
ARCH_RISK=high; persistence of ASTs is explicitly out of scope and process isolation matters
CONFIDENCE=high for structural duplication, medium for current dominance
```

## PROCESSPOOL_FINDINGS

### Import/index pool

Owner: `index_repository` in `contextor/core/symbol_engine/indexer.py`. Work unit:
one path (`_process_single_file(path_str, root_str)`). No custom initializer;
worker-local `_CACHE_MANAGERS` is keyed by root. Input is two strings; output is
a dictionary containing module id/path/absolute path/imports/error/filename.
The worker checks cache, otherwise reads/parses the file through `read_imports`,
and returns imports. One future is submitted per file. Results are reconstructed
into `Module` objects in the parent. Current execution is ProcessPool unless
`CONTEXTOR_DISABLE_PROCESS_POOL=1`; the serial branch is an explicit diagnostic
fallback. Four logical CPUs are not enough evidence by themselves to change it.

### Artifact pool

Owner: `collect_module_artifacts`. Work unit: one `module_id` passed to
`_process_single_artifact_module`. Initializer receives the complete `modules`
mapping, `root_path`, and the run-scoped `RepositoryReferenceIndex` once per
worker. Each worker stores them globally, calls `extract_file_symbols` on the
module path, derives own symbols, uses the supplied reference index, and returns
`(module_id, {symbols, own_symbols, consumers})`. The parent collects one future
per module with `as_completed`; failures are retained by module id.

The reference index itself is built before worker processing and visits each
module AST in one pass. The artifact worker then reconstructs symbols by parsing
each module path again. There is no batching: granularity is one task per module.
This is a real serialization/process-boundary cost candidate, but current full-run
wall-clock and payload-size measurements are absent, so no numeric speedup is claimed.

## DUPLICATED_WORK_FINDINGS

| Work | Exact evidence | Classification |
|---|---|---|
| watcher recursive snapshot | `DesktopWatcher._scan` uses `root.rglob("*.py")` each poll | MEASURED + architectural |
| incremental parse/import/symbol facts | `prepare_source_update` parses, calls `read_imports`, calls `extract_file_symbols` | ARCHITECTURAL_EVIDENCE |
| full repository AST passes | indexer, collision facts, reference index, artifact worker each own a parse boundary | ARCHITECTURAL_EVIDENCE |
| artifact consumer removal | `_rebuild_consumer_slice` scans all target entries for every consumer | ARCHITECTURAL_EVIDENCE |
| graph analytics | full path computes graph metrics/cycles/debt, then report pipeline computes graph analytics and facade persistence computes topology/matrix/clusters | ARCHITECTURAL_EVIDENCE; some inputs are intentionally distinct canonical products, so duplication is not assumed without further timing |
| persistence/publication | trace shows persistence and canonical publication; no evidence that exact-successor persistence is redundant | NOT A TARGET |

No cache, AST persistence, worker-count change, public MCP contract change,
canonical revision change, FileState change, or activity-epoch change is proposed.

## FIRST_IMPLEMENTATION_TARGET

```ini
TARGET_FILE=contextor/core/analysis/incremental/preparation.py
TARGET_SYMBOL=prepare_source_update
CURRENT_OWNER=IncrementalAnalysisEngine.update_file
ROOT_CAUSE=the changed file is independently read/parsed for syntax validation,
imports, and symbols even though the first parse already produced parsed_tree
EXPECTED_CHANGE_SHAPE=make the preparation fact-extraction path share one parsed
source/AST result with import and symbol extraction, preserving the existing
PreparedSourceUpdate and FileDelta contracts; keep collision facts equivalent
EXPECTED_PERFORMANCE_EFFECT=remove redundant source/AST work from every changed
file, reducing the measured updater path (median 265 ms) by the parse portion;
exact gain must be measured before/after and is not estimated here
ARCH_RISK=medium and bounded to PREPARE; no watcher lifecycle, LIVE ownership,
canonical revision, FileState, or public MCP contract change
```

Required invariants:

```text
- identical syntax-error status/message/line/column behavior
- identical imports, symbols, own_symbols, usage delta, collision facts, and FileDelta
- unchanged RefreshPlanner decisions and execute_refresh_plan execution traces
- unchanged no-op, add, delete, recovery, ambiguity, and resync/freshness semantics
- no secondary source read/parse for the same changed file in the preparation path
- no mutation of canonical state before the existing commit boundary
```

Required focused tests: the dedicated incremental preparation/equivalence tests,
`tests/test_no_double_parse.py`, `tests/test_incremental_equivalence.py`,
`tests/test_incremental_local_metrics.py`, `tests/test_refresh_plan_execution.py`,
and the relevant syntax-error/recovery cases. Run only the focused subset after
implementation; do not run the full suite.

Required benchmark: one quiescent, read-only changed-file benchmark on the same
checkout, tagged `COLD` and `WARM` as applicable, recording total
`prepare_source_update` wall time and parse/read call counts. Compare semantic
output against the pre-change result and report the before/after parse count and
elapsed time; do not repeat runs solely to improve a number.

## FINAL_REPORT

```ini
VERDICT=BOTTLENECK_MAP_READY
FILES_CHANGED=NONE (production and tests)
DIFFS=NONE (production and tests)
WALKTHROUGH_CHANGED=YES (required report artifact only)
```

The audit is complete and awaits `proceduj` before any implementation work.
