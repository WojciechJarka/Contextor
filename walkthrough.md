# Full-analysis regression discovery/profiling (read-only)

Date: 2026-09-03  
Repository: `C:\Temp\Contextor_Repo`  
Benchmark root: `C:\Temp\Contextor_Benchmarks\full_regression_20260903`

## Decision

`EXPECTED_CANONICAL_COST`

Representative healthy full run: `22,155.731 ms`, 326/326 modules, zero analysis errors, result present. The new canonical `ModuleUsageFacts` baseline cost `15,917.523 ms` inclusive. It alone explains the approximately `11 s` increase from the supplied historical approximately `12 s` level. No current-run fact-equivalent recomputation with exact identity/snapshot/domain equivalence and safely measurable removable end-to-end cost was proven, so there is no `REDUNDANCY_GO_CANDIDATE`.

Dominant decomposition:

- `_build_module_usage_baseline`: once, `15,917.523 ms` inclusive / `287.783 ms` self.
- `extract_module_usage_facts`: 326 calls, `13,347.658 ms` inclusive / `5,726.852 ms` self.
- Six full `ast.walk(tree)` traversals per module: `1,956 = 326 * 6`, `6,744.978 ms`.
- Nested `ast.walk(node.func)`: 56,090 calls, `875.828 ms`.
- Fresh-process `Module.ast_tree -> parse_source`: exactly 326 reads/parses, `2,282.081 ms`.

The compact index facts overlap with `ModuleUsageFacts`, but their contracts are not identical: compact facts contain aliases/calls/callbacks/events/inheritance/qualified refs/imports/reexports, while the canonical baseline guarantees materialized `symbol_calls` and `reference_evidence` with canonical identities and complete current-module coverage. No exact converter/parity proof exists. Therefore the measured extractor cost is not labeled removable.

## Health, seeds, and raw timings

Disposable source copy; isolated cache/state/output/registry; normal ProcessPool enabled; LIVE connection disabled only inside the external harness.

```text
{"seed": 0, "total_ms": 22155.730546000996, "health": {"errors": 0, "module_count": 326, "result_present": true, "live_publish_status": "not_attempted"}}
{"count": 1, "median_total_ms": 22155.730546000996, "min_total_ms": 22155.730546000996, "max_total_ms": 22155.730546000996}
```

Additional healthy seeds used only to identify warmup/outliers:

```text
seed=0 total_ms=36635.16634100233 errors=0 modules=326  # cold/warmup; separate
seed=1 total_ms=21563.904071008437 errors=0 modules=326
seed=2 total_ms=19615.975424007047 errors=0 modules=326
```

No degraded run occurred. The 36.635 s cold observation is not mixed with warm results.

Raw stage timings for the representative run:

```text
Step 1/8 Initializing repository identity        165.291 ms
Step 2/8 Indexing repository files             2509.530 ms
Step 3/8 Resolving dependency graph               48.218 ms
Step 4/8 Validating dependency graph               4.859 ms
Step 5/8 Computing metrics, cycles and debt         2.648 ms
Step 6/8 Generating architectural reports        2691.804 ms
Step 7/8 Persisting canonical LIVE snapshot     16707.896 ms
Step 8/8 Finalizing analysis                       25.466 ms
TOTAL                                           22155.731 ms
```

Artifacts:

```text
C:\Temp\Contextor_Benchmarks\full_regression_20260903\profile_full.py
C:\Temp\Contextor_Benchmarks\full_regression_20260903\observations.json
C:\Temp\Contextor_Benchmarks\full_regression_20260903\observations_detail.json
C:\Temp\Contextor_Benchmarks\full_regression_20260903\source
C:\Temp\Contextor_Benchmarks\full_regression_20260903\runtime
```

## Exact commands

Contextor MCP was used first:

```text
mcp__contextor__get_mcp_documentation(tools=[get_project_architecture,get_symbol_call_context,get_symbol_implementation,search_source,analyze_project,get_analysis_status], sections=[purpose,parameters,behavior,freshness,usage_notes,examples])
mcp__contextor__get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo", compact=true, max_items=20)
mcp__contextor__search_artifacts(... search_term="analyze_project"|"index_repository"|"execute_global_pipeline"|"ModuleUsageFacts")
mcp__contextor__get_symbol_implementation(... mode="fetch", include=["implementation","static_context"])
mcp__contextor__get_symbol_call_context(... direction="both", depth=2, max_items=100, representation="named", allow_large_output=true)
```

Text verification:

```powershell
git status --short
rg -n "def analyze_project|def _process_single_file|def execute_global_pipeline|ModuleUsageFacts|ensure_module_usages|artifact_consumption|extract_test|graph_metrics|derived" contextor/core contextor/mcp/analysis_jobs.py
Get-Content -LiteralPath contextor/core/api/facade.py | Select-Object -Skip 320 -First 280
Get-Content -LiteralPath contextor/core/reporting_engine/pipeline.py | Select-Object -First 260
Get-Content -LiteralPath contextor/core/symbol_engine/indexer.py | Select-Object -Skip 280 -First 240
Get-Content -LiteralPath contextor/core/reporting_engine/artifact_pipeline.py | Select-Object -First 360
Get-Content -LiteralPath contextor/core/reference/engine.py | Select-Object -Skip 760 -First 140
rg -n "build_jaccard_clusters\(" contextor/core/reporting_engine contextor/core/analysis
rg -n "_build_module_usage_baseline\(" contextor/core
rg -n "extract_module_usage_facts\(" contextor/core/symbol_engine contextor/core/reference contextor/core/api
git diff -- contextor tests
git diff --numstat -- contextor tests
```

Benchmark:

```powershell
$dest='C:\Temp\Contextor_Benchmarks\full_regression_20260903\source'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
robocopy 'C:\Temp\Contextor_Repo' $dest /E /XD .git .venv output logs .pytest_cache __pycache__ /XF walkthrough.md *.pyc
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' -u 'C:\Temp\Contextor_Benchmarks\full_regression_20260903\profile_full.py'
```

Robocopy completion:

```text
Dirs : 160 total, 125 copied, 35 skipped, 0 failed
Files: 1062 total, 1061 copied, 1 skipped, 0 failed
Bytes: 5.39 m total, 5.37 m copied
```

## Contextor architectural evidence

At canonical revision 182 Contextor reported 326 modules, `data_source=live_canonical_state`, and fresh module/graph/topology/artifact-consumption/cycles/collisions families. Layer counts: adapter 76, cli 1, contract 12, engine 27, runtime 74, tests 126, ui 10.

- `contextor.core.api.facade::ContextorFacade.analyze_project` owns orchestration. Canonical intra-module call facts showed `_initialize_repository_identity`, `_analysis_filters`, `_compute_metrics_and_debt`, `_log_skipped`. Cross-module flow below was verified from exact source because MCP documents this query as intra-module only.
- `contextor.core.symbol_engine.indexer::index_repository` is `indexer.py:558-719`; Contextor showed 18 static consumers. Canonical callees included `_process_single_file`, fact validators, `read_imports`, `_extract_collision_facts`, and `_extract_test_facts`.
- `contextor.core.reporting_engine.pipeline::execute_global_pipeline` had 5 static consumers. Its canonical call query returned zero cross-module edges, consistent with the documented scope; exact source showed artifact/layer/report/file-state orchestration.
- Contextor showed exact edge `_build_module_usage_baseline -> extract_module_usage_facts` at `engine.py:772`.
- `ModuleUsageFacts` had 23 canonical static consumers (bounded response). The full-run producer is `_build_module_usage_baseline`; consumers include `RepositoryAnalysisState`, persistence, LIVE and incremental/query paths.
- `generate_artifact_usage_report` canonical callees included `collect_module_artifacts`, `build_artifact_index`, shared filtering/clusters and core candidates.
- Fetched implementations for `index_repository`, `extract_module_usage_facts`, `ensure_module_usages` were `workspace_sync=verified`, revision 182, provenance live.

## Complete `analyze_project` flow

1. `_initialize_repository_identity`, cache reset, filters.
2. `index_repository`: enumerate Python; `_process_single_file` via ProcessPool; on miss one AST feeds imports, symbol facts, compact references, collision facts, test facts; valid warm cache returns JSON-safe facts without parse.
3. `assemble_reference_index_or_fallback` and collision assembly, both complete-coverage/fail-closed.
4. Trie/package root; cached graph/build graph; validation.
5. Metrics, cycles, collisions, debt.
6. `execute_global_pipeline`: summary, structure, collisions.
7. `build_artifact_pipeline -> generate_artifact_usage_report`: definitions, references, test context, artifact index, shared filtering/clusters, core candidates.
8. Registry/compaction, graph analytics, layer slicing/analytics.
9. Report writes and `FileStateManager` snapshot.
10. Canonical state: `build_canonical_artifact_consumption`, `_build_module_usage_baseline`, topology, dependency matrix, shared-usage cluster handoff/recompute gate.
11. `save_engine_state`, then production LIVE publish. The harness stopped before connection by returning no client.

## Complete cost table: every instrumented operation >=100 ms

Inclusive rows overlap. Percent uses total 22,155.731 ms. Self excludes explicitly instrumented children.

| Qualified owner | Count | Input domain | Inclusive ms | Self ms | % | Classification |
|---|---:|---|---:|---:|---:|---|
| `contextor.core.reference.engine._build_module_usage_baseline` | 1 | 326 current modules/AST/imports | 15917.523 | 287.783 | 71.84 | required new canonical usage baseline |
| `contextor.core.reference.engine.extract_module_usage_facts` | 326 | one AST/module | 13347.658 | 5726.852 | 60.24 | canonical usage/call/evidence producer |
| `ast.walk` aggregate inside extractor | 58046 | 326 ASTs | 7620.806 | 7620.806 | 34.40 | required current implementation work; not automatically duplicate |
| `ast.walk.full_tree` | 1956 | six per AST | 6744.978 | 6744.978 | 30.44 | distinct semantic channels/filters |
| `contextor.core.api.facade.execute_global_pipeline` | 1 | full report domain | 2691.761 | 799.322 | 12.15 | reports/artifacts/analytics/persistence preparation |
| `contextor.core.domain.module.parse_source` | 326 | 326 source files | 2282.081 | 2282.081 | 10.30 | AST materialization for baseline |
| `contextor.core.api.facade.index_repository` | 1 | 326 Python files | 2138.177 | 2138.177 | 9.65 | indexing/freshness/fact assembly |
| `contextor.core.reporting_engine.artifact_pipeline.generate_artifact_usage_report` | 1 | 326 modules + reference/test facts | 1176.779 | 265.654 | 5.31 | artifact semantics |
| `contextor.core.reporting_layer.artifact_usage_report.collect_module_artifacts` | 1 | 326 modules | 889.644 | 889.644 | 4.02 | definitions/references/test context |
| `ast.walk.nested` | 56090 | call-function subtrees | 875.828 | 875.828 | 3.95 | qualified-reference exclusion logic |
| `contextor.core.reporting_engine.artifact_pipeline.generate_graph_analytics_report` | 1 | artifact report + graph | 409.601 | 31.407 | 1.85 | required analytics |
| `contextor.core.analysis.state_manager.save_engine_state` | 1 | canonical state + file payload | 402.929 | 402.929 | 1.82 | persistence contract |
| `contextor.core.reporting_engine.graph_analytics.build_jaccard_clusters` | 3 | global/eligible-layer domains | 382.156 | 382.156 | 1.72 | different scopes/domains |
| `contextor.core.api.facade.assemble_reference_index_or_fallback` | 1 | 326 compact-fact envelopes | 346.636 | 346.636 | 1.56 | fail-closed reference resolution |
| `contextor.core.api.facade._initialize_repository_identity` | 1 | repository root | 161.226 | 161.226 | 0.73 | identity ownership |
| `contextor.core.analysis.state_manager.build_canonical_artifact_consumption` | 1 | complete raw artifacts | 141.931 | 141.931 | 0.64 | canonical inbound-consumption SSOT |
| `contextor.core.analysis.state_manager.FileStateManager.update_state` | 326 | one source/module | 133.525 | 133.525 | 0.60 | file-state snapshot |

## Per-module/source/AST counts

| Operation | Calls | Exact behavior | Wall |
|---|---:|---|---:|
| `_process_single_file` results | 326 | warm-cache source hash/read/decode/fact validation; no worker parse on accepted hits | in indexing 2138.177 ms |
| `Module.ast_tree -> parse_source -> read_text + ast.parse` | 326 | exactly once per source in fresh parent process | 2282.081 ms |
| `extract_module_usage_facts` | 326 | exactly once per AST | 13347.658 ms |
| `SymbolReferenceVisitor.visit(tree)` | 326 | one recursive visitor traversal per AST | included in extractor self |
| full `ast.walk(tree)` | 1956 | exactly six per AST | 6744.978 ms |
| nested `ast.walk(node.func)` | 56090 | variable by call count; total walks/module min 6, median 90, max 3456 | 875.828 ms |
| compact reference extractor | 0 current-run warm traversals | cached envelopes reused | assembly 346.636 ms |
| test-fact extractor | 0 current-run warm traversals | cached `test_facts_by_path` reused | included in artifact path |
| collision extractor | 0 current-run warm traversals | complete cached facts reused | included in indexing |

Top walk-call modules:

```text
tests.test_mcp_regressions 3456
tests.test_live_state_ipc 1368
tests.test_h3a_workspace_canonical_freshness 1328
tests.test_live_watcher_startup_reconciliation 1306
tests.test_live_activity_status 1224
tests.test_completeness_freshness_parity_proof 1200
contextor.core.reporting_engine.graph_analytics 992
contextor.ui.gui 926
```

Complete 326-entry `parse_by_path` and `ast_walk_by_module` maps are in `observations_detail.json`.

## Duplicate/reuse map

| First producer | Later consumer/recompute | Identity/snapshot/domain evidence | Verdict |
|---|---|---|---|
| index cache/worker facts | reference/collision/artifact/test consumers | same indexed source identity; complete coverage gates | reused; no warm re-extraction |
| assembled reference index | artifact reference collection | same run-scoped instance, 326-module domain | reused |
| global report shared-cluster handoff | canonical shared clusters | artifact-data identity, keys, raw keys, scope, thresholds validated | reused when valid |
| report `_module_artifacts` | canonical artifact consumption | same analysis result/domain, different inbound SSOT contract | required derivation, 141.931 ms |
| compact reference facts | canonical module usage baseline | same module/source domain, but no exact parity for materialized symbol calls/reference evidence | overlap only; no GO |
| worker AST on cold miss | parent `Module.ast_tree` | cold unchanged-source path parses in both processes; accepted warm run had no worker parse | cold lead only; no safe measured removable warm cost |
| six full walks | one another | same AST but different channels/filters | not duplicate by AST identity alone |
| three Jaccard calls | global/layer outputs | scopes/domains differ | required scoped computations |

## Exact reread/reparse path

After warm indexing, every module was read/parsed in the fresh parent process:

```text
ContextorFacade.analyze_project
 -> _build_module_usage_baseline(mods)          facade.py:504
 -> module.ast_tree                             engine.py:774
 -> _get_cached_ast(absolute_path)              domain/module.py:60
 -> _parse(path,(mtime_ns,size))                domain/module.py:39
 -> parse_source -> Path.read_text + ast.parse  domain/module.py:22
```

Measured: 326/326 sources, one parse each, `2,282.081 ms`. Canonical facts are built from `modules[*].ast_tree`; the property reconstructs the AST from source on a process-local cache miss. Later accesses reuse the same process-local AST. On warm index cache hits this is not a same-run duplicate parse because indexing does not parse. On cold/migration paths worker and parent structurally parse unchanged source across the process boundary, but this did not cause the warm approximately 23 s regression and lacks an end-to-end removable-cost/parity proof.

## Uncertainties / non-claims

1. Parent instrumentation cannot see ProcessPool child subcomponents; worker time is included in `index_repository` wall. Accepted warm behavior follows the current cache-hit branch.
2. Timing uses deterministic wrappers, not sampling. `ast.walk` was materialized to time full iterator consumption; emitted nodes/semantics are unchanged, but allocation adds small overhead. Detailed totals 21.705 s and 22.156 s remain in the observed approximately 23 s class.
3. Exact compact-reference-to-`ModuleUsageFacts` parity is unproven; no removable saving is claimed.
4. Historical approximately 12 s came from the task and was not replayed on an older checkout.
5. Closed earlier optimizations (reference fusion, cached test/collision facts, run-scoped reference reuse, shared-cluster handoff) were not reopened because current evidence shows reuse, not regression.

## Mutation audit

`git diff -- contextor tests` returned no output.  
`git diff --numstat -- contextor tests` returned no output.  
Pre-existing/unrelated untracked runtime logs were untouched.

`FILES_CHANGED=NONE`  
`DIFFS=NONE`  
`FULL_SUITE_RUN_BY_AGENT=NO`

Only the required root `walkthrough.md` report was overwritten. No production/test file changed; therefore no production/test unified diff is required.
