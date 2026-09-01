# 0F0B — current-path timing and field-level single-file consumer trace

## Scope and authority

Discovery used Contextor MCP source retrieval/search only. The MCP source envelope remained `canonical_state=fresh`, `workspace_sync=verified`, revision 138. No production or test file was modified; no `pytest` or `py_compile` command was run.

`MCP_AVAILABILITY=PASS` and `MCP_RUNTIME_FRESHNESS=PASS` carry forward from the verified public tool surface plus MCP-resolved implementations.

## Part A — actual single-file field consumers

`ContextorFacade.analyze_single_file` calls `hydrate_repository_engine`, `engine.update_file`, then reads `engine.state.modules`, `engine.state.dependency_graph`, passes `engine.state` to `collect_all_contexts`, and projects `engine.state.artifacts` for graph analytics. `collect_all_contexts` parses/reads the target file, builds `ContextPayload`, then executes the 15 builders in `default_registry`.

Only `SymbolContextBuilder` and `ArchitectureContextBuilder` directly read `payload.engine_state`; passing the payload to every builder is not treated as consumption.

| FIELD | MATERIALIZATION_OWNER | DIRECT_SINGLE_FILE_CONSUMER / CONSUMER_SYMBOL | READ_FOR_UNCHANGED_TARGET | READ_FOR_REPORT_OUTPUT | READ_ONLY_FOR_UPDATE_PATH | PERSISTED_BEFORE_ENGINE | FRESHNESS_GATE | ENGINE_CONSTRUCTOR_MATERIALIZATION_REQUIRED | EVIDENCE |
|---|---|---|---|---|---|---|---|---|---|
| modules | persisted state; materializer ensures module usages, not modules | facade; `SymbolContextBuilder` | YES | YES | YES | YES | module-current truth | NO | facade reads `engine.state.modules`; builder uses `engine_state.modules` for canonical reference universe |
| dependency_graph | persisted state | facade, `generate_report`, architecture builder | YES | YES | YES | YES | resolver rejects missing graph | NO | facade assigns graph before report/context |
| trie | resolver/layer-only fallback | none in single-file path | NO | NO | YES | YES | NONE | NO | no single-file attribute read found |
| package_root | resolver/layer-only fallback | none | NO | NO | YES | YES | NONE | NO | no single-file attribute read found |
| artifacts | persisted state | `SymbolContextBuilder`; canonical artifact projection | YES | YES | YES | YES | `_canonical_state_module_is_current` | NO | `engine_state.artifacts` read for target/catalog/ecosystem; facade passes artifacts to projection |
| artifact_consumption | `ensure_artifact_consumption` | `SymbolContextBuilder` | CONDITIONAL | YES | YES | PARTIAL | target module current AND `artifact_consumption_state == fresh` | CONDITIONAL | canonical usage/reference branch reads the map; otherwise source-backed fallback |
| module_usages | `ensure_module_usages` | `SymbolContextBuilder` | CONDITIONAL | YES | YES | PARTIAL | canonical current + artifact consumption fresh + dict type | CONDITIONAL | passed to `build_symbol_references_from_canonical`; otherwise fallback |
| reference evidence | derived by canonical reference builder / fallback | `SymbolContextBuilder` | CONDITIONAL | YES | YES | PARTIAL | same canonical-reference eligibility; exception falls back | CONDITIONAL | `CanonicalReferenceEvidenceUnavailable` selects fallback |
| symbol calls | no direct single-file `engine_state` read | none | NO | NO | YES | PARTIAL | NONE | NO | no direct attribute read found |
| topology analytics | `ensure_topology_analytics` | none | NO | NO | YES | PARTIAL | NONE | NO | architecture builder recomputes graph metrics |
| cached analytics | `ensure_cached_analytics` | none | NO | NO | YES | PARTIAL | NONE | NO | no direct attribute read found |
| cycles | `ensure_cycles` | `ArchitectureContextBuilder` | CONDITIONAL | YES | YES | PARTIAL | `cycles_state == fresh` | CONDITIONAL | otherwise `detect_cycles(hard_edges)` recomputes |
| collision facts/state | `ensure_collisions` | `ArchitectureContextBuilder` | CONDITIONAL | YES | YES | PARTIAL | `collisions_state == fresh` | CONDITIONAL | otherwise validates collisions from modules |
| dependency matrix | `ensure_dependency_matrix` | none | NO | NO | YES | PARTIAL | NONE | NO | no direct attribute read found |
| shared usage clusters | `ensure_shared_usage_clusters` | none | NO | NO | YES | PARTIAL | NONE | NO | no direct attribute read found |
| resync_required | update engine | `update_file` only | YES | indirect freshness outcome | NO | YES | if true, marks artifact consumption stale before no-op | CONDITIONAL | exact pre-no-op mutation in `update_file` |
| parse/recovery state | update engine | `update_file` only | CONDITIONAL | indirect | NO | PARTIAL | source prep/clear parse failure | CONDITIONAL | no-op may return `RECOVERED`; changed path owns it |
| registry | hydrated engine constructor | update path only | NO for pure output | NO | NO | persisted registry external to state | NONE | CONDITIONAL | required for changed/new/deleted update identity; not directly read by report builders |
| FileStateManager | hydrated engine constructor | `update_file` | YES | NO | NO | external `file_state.json` | `has_changed(target)` | YES for existing currentness authority | exact unchanged gate is `not has_changed and module in state.modules` |

Additional materialization-owned families are the eight ordered children: artifact consumption, module usages, topology analytics, cached analytics, cycles, collisions, dependency matrix, and shared usage clusters. The constructor invokes `materialize_incremental_state` before update/report consumption.

`UNCHANGED_REPORT_MATERIALIZED_FIELDS_ACTUALLY_REQUIRED=artifact_consumption (conditional), module_usages (conditional), reference evidence (conditional), cycles (conditional), collisions (conditional)`

`UNCHANGED_REPORT_MATERIALIZED_FIELDS_UNUSED=trie, package_root, symbol_calls, topology analytics, cached analytics, dependency matrix, shared usage clusters`

`UNCHANGED_REPORT_FIELDS_ALREADY_PERSISTED_AND_FRESH=modules, dependency_graph, artifacts; other required families are PARTIAL and must pass their own state gates`

## Part B — resync/degraded semantics

B1 healthy/current: `PARTIAL`. The consumer trace disproves the earlier blanket rejection: not every constructor materialization family is consumed by an unchanged single-file report. A healthy state-only branch remains semantically possible only if it first uses the existing `FileStateManager.has_changed` authority, target module membership, `resync_required=False`, and all conditional report gates above are satisfied from persisted state.

B2 degraded/resync: `YES`, full engine is required. Current `update_file` deliberately changes `artifact_consumption_state` to stale before an otherwise unchanged return when `resync_required` is true. A fast path must fail closed rather than silently expose canonical reference data.

B3 changed/new/deleted: `YES`, full engine/update is required. It owns deletion deltas, parse failures/recovery, refresh planning, state acknowledgement, commit, and optional LIVE publication.

`HEALTHY_CURRENT_FAST_PATH_SEMANTICALLY_POSSIBLE=PARTIAL`

`DEGRADED_STATE_REQUIRES_FULL_ENGINE=YES`

`CHANGED_TARGET_REQUIRES_FULL_ENGINE=YES`

## Part C–F — external harness and validity result

Harness location: `C:\Temp\Contextor_Benchmarks\0F0B_20260901\harness.py`.

It used a disposable source copy, isolated runtime cache/output, one complete-project seed, target `contextor/core/api/facade.py` unchanged after the seed, explicit wrappers only around named hydration/materialization/update/currentness owners, immediate JSONL persistence, one diagnostic observation, and six sequential retained warm observations.

The protocol’s mandatory health gate failed: all diagnostic/warm observations reported `TARGET_BYTE_CURRENT=YES`, `HYDRATION_SOURCE=snapshot`, `ERROR=NONE`, but `RESYNC_REQUIRED_AT_START=YES`. Consequently **zero** warm observations satisfy the required `RESYNC_REQUIRED_AT_START=NO` condition. They are retained as invalid/degraded observations, not used as accepted warm baseline data.

Persisted raw observations: `C:\Temp\Contextor_Benchmarks\0F0B_20260901\observations.jsonl`.

Invalid degraded warm medians (six retained outliers; diagnostic excluded):

| Phase | Median ms | Valid for candidate? |
|---|---:|---|
| total facade | 21218.33 | NO — degraded state |
| authoritative resolver | 89.87 | NO — degraded state |
| engine construction | 13675.65 | NO — degraded state |
| materialize incremental state | 13675.65 | NO — degraded state |
| ensure module usages | 13414.75 | NO — degraded state |
| ensure artifact consumption | 38.24 | NO — below 50 ms |
| cached analytics | 166.30 | NO — degraded state |
| collisions | 16.91 | NO — below 50 ms |
| dependency matrix | 21.46 | NO — below 50 ms |
| shared clusters | 21.14 | NO — below 50 ms |
| FileStateManager construction | 3.14 | NO — degraded state |
| `has_changed(target)` | 0.69 | NO — degraded state |
| unchanged update | 22.45 | NO — degraded state |

The narrow wrappers did not cover the facade-import-bound hydration call nor report/build/write owners, so no valid values exist for full hydration, global report, `collect_all_contexts`, builders, artifact compaction, graph analytics, serialization, writes, or facade residual. Source/AST counters were likewise not collected by a valid narrow source-I/O owner wrapper. These are recorded as `UNAVAILABLE`, not zero. The protocol must be re-seeded to a healthy canonical state before rerunning the phase-accounting harness.

The observed 13.4-second `ensure_module_usages` time strongly indicates it is the dominant degraded materialization cost, but it is **not** proof that the 199 production modules are reread/reparsed, because the required source/AST accounting did not run and the starting state failed the health gate.

`EXISTING_CURRENTNESS_CHECK_TOTAL_MEDIAN_MS=3.83 (invalid/degraded observations; FileStateManager construction + has_changed; membership check was not separately wrapped)`

## Part E — materialization necessity matrix

| OWNER | MEDIAN_MS | OUTPUT_STATE_FAMILY | ACTUALLY_CONSUMED | ALREADY_VALID_PERSISTED_EQUIVALENT | REQUIRED_ONLY_FOR_FUTURE_UPDATE_CAPABILITY | POTENTIALLY_REMOVABLE_HEALTHY_CURRENT_READ_PATH_MS |
|---|---:|---|---|---|---|---|
| ensure_artifact_consumption | 38.24 invalid | artifact consumption | CONDITIONAL | PARTIAL | NO | requires healthy evidence |
| ensure_module_usages | 13414.75 invalid | module usages | CONDITIONAL | PARTIAL | NO | requires healthy evidence |
| ensure_topology_analytics | <0.01 invalid | topology | NO | PARTIAL | YES | requires healthy evidence |
| ensure_cached_analytics | 166.30 invalid | cached analytics | NO | PARTIAL | YES | requires healthy evidence |
| ensure_cycles | <0.01 invalid | cycles | CONDITIONAL | PARTIAL | NO | requires healthy evidence |
| ensure_collisions | 16.91 invalid | collisions | CONDITIONAL | PARTIAL | NO | requires healthy evidence |
| ensure_dependency_matrix | 21.46 invalid | dependency matrix | NO | PARTIAL | YES | requires healthy evidence |
| ensure_shared_usage_clusters | 21.14 invalid | shared clusters | NO | PARTIAL | YES | requires healthy evidence |

## Part G — decision

Candidate 0F1 is **not yet admitted**. The source-level consumer conditions are now bounded enough to keep it open, but its mandatory healthy-state timing and field-completeness proof are absent. The external run certified only the degraded branch, which must retain the full engine path.

`MCP_RUNTIME_FRESHNESS=PASS`
`PRIMARY_FILE=contextor/core/api/facade.py`
`TARGET_BYTE_CURRENT=YES (all retained observations)`
`RESYNC_REQUIRED_AT_START=YES (all retained observations; healthy gate failed)`
`SUCCESSFUL_WARM_RUN_COUNT=0`
`CURRENT_SINGLE_FILE_WARM_MEDIAN_MS=UNAVAILABLE (six retained observations are invalid/degraded)`
`AUTHORITATIVE_STATE_RESOLUTION_MEDIAN_MS=UNAVAILABLE (healthy); 89.87 invalid/degraded`
`FULL_ENGINE_HYDRATION_MEDIAN_MS=UNAVAILABLE`
`ENGINE_CONSTRUCTION_MEDIAN_MS=UNAVAILABLE (healthy); 13675.65 invalid/degraded`
`MATERIALIZE_INCREMENTAL_STATE_MEDIAN_MS=UNAVAILABLE (healthy); 13675.65 invalid/degraded`
`ENSURE_MODULE_USAGES_MEDIAN_MS=UNAVAILABLE (healthy); 13414.75 invalid/degraded`
`UPDATE_FILE_UNCHANGED_MEDIAN_MS=UNAVAILABLE (healthy); 22.45 invalid/degraded`
`COLLECT_ALL_CONTEXTS_MEDIAN_MS=UNAVAILABLE`
`GRAPH_ANALYTICS_MEDIAN_MS=UNAVAILABLE`
`HYDRATION_SOURCE_READ_COUNT=UNAVAILABLE`
`HYDRATION_AST_PARSE_COUNT=UNAVAILABLE`
`UPDATE_FILE_SOURCE_READ_COUNT=UNAVAILABLE`
`UPDATE_FILE_AST_PARSE_COUNT=UNAVAILABLE`
`TARGET_FILE_AST_PARSE_COUNT=UNAVAILABLE`
`UNCHANGED_REPORT_MATERIALIZED_FIELDS_ACTUALLY_REQUIRED=artifact_consumption,module_usages,reference_evidence,cycles,collisions (all conditional)`
`UNCHANGED_REPORT_MATERIALIZED_FIELDS_UNUSED=trie,package_root,symbol_calls,topology_analytics,cached_analytics,dependency_matrix,shared_usage_clusters`
`HEALTHY_CURRENT_FAST_PATH_SEMANTICALLY_POSSIBLE=PARTIAL`
`DEGRADED_STATE_REQUIRES_FULL_ENGINE=YES`
`CHANGED_TARGET_REQUIRES_FULL_ENGINE=YES`
`EXISTING_CURRENTNESS_CHECK_TOTAL_MEDIAN_MS=UNAVAILABLE (healthy); 3.83 invalid/degraded`
`TOP_SINGLE_FILE_CANDIDATE=NONE`
`TOP_SINGLE_FILE_EXPECTED_SAVING_MS=NONE`
`SECOND_SINGLE_FILE_CANDIDATE=NONE`
`THIRD_SINGLE_FILE_CANDIDATE=NONE`
`NEXT_TARGET=establish a healthy isolated seed with resync_required=False, then rerun the same bounded wrappers with complete report/source-AST accounting`
`FILES_CHANGED=NONE`
`DIFFS=NONE`
`WHY=The consumer trace permits a fail-closed healthy state-only hypothesis, but all timed observations started degraded, so no valid performance or semantic admission evidence exists for 0F1.`

Waiting for `proceduj`.

## Continuation after `proceduj`

The previous invalidation was corrected: the old harness labelled `RESYNC_REQUIRED_AT_START` after the facade had already returned. A read-only isolated snapshot inspection immediately after a fresh project seed reports `resync_required=False`, `artifact_consumption_state=fresh`, `modules=325`, and `module_usages_len=0`.

A second disposable direct probe established the existing unchanged-target gate independently of the facade wrapper:

```
BEFORE: resync_required=False; FileStateManager.has_changed(target)=False
UPDATE: status=UNCHANGED; resync_required=False; artifact_consumption_state=fresh
```

Thus the target itself does not force resync and the existing `update_file` unchanged branch preserves a healthy state.

The corrected batch harness failed to persist its post-seed records, and an isolated facade-only probe terminated without post-call output despite no Python exception or nonzero shell status. This is an external-harness execution anomaly, not evidence of a production semantic transition. The production source contains no `os._exit` call. No new accepted warm timing was produced.

`CONTINUATION_HEALTHY_SEED=PASS`
`CONTINUATION_DIRECT_UNCHANGED_UPDATE=PASS`
`CONTINUATION_VALID_WARM_RUN_COUNT=0`
`CONTINUATION_STATUS=No further performance conclusion; repair the external harness execution boundary before another timed batch.`
