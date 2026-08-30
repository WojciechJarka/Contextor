# Post-0J2 warm cost remap — discovery only

## Scope and outcome

This was a measurement and architectural-discovery task only. No production or test file was modified. All benchmark harnesses, source copies, runtime state, profiles, and results were kept outside the repository under `C:\Temp\Contextor_Benchmarks`.

The fresh clean warm median for the complete `ContextorFacade.analyze_project()` path was **8496.943 ms** over six warm runs. The values were 8491.222, 8623.114, 8749.251, 8456.018, 8502.663, and 8410.229 ms; range **8410.229–8749.251 ms**. The spread is approximately 4.0% peak-to-peak and does not establish a regression against the previously recorded post-0J2 median of 8429.232 ms.

The largest removable-looking work is not the current warm index cache validation. It is repeated AST traversal for collision facts and test-file facts. A third, smaller candidate is the canonical-state Shared Usage Clusters recomputation after the report pipeline already computed Jaccard clusters from equivalent RAM facts.

## Benchmark protocol

- Repository under measurement: `C:\Temp\Contextor_Repo`.
- Disposable source copy: `C:\Temp\Contextor_Benchmarks\post0J2_clean_20260830_1\source`.
- Runtime cache, state, output, and registry were isolated under the same external benchmark directory.
- The source copy excluded `.git`, `.venv`, `.contextor`, bytecode, test caches, logs, output, and temporary directories.
- The measured project contained **318 modules**.
- One cold run followed by six warm runs.
- The normal ProcessPool path remained enabled.
- LIVE publication was disabled by an external harness patch to `live_state.connect`; this avoids daemon/network publication noise while retaining canonical snapshot persistence.
- No pytest command was run.
- A separate detailed external harness wrapped production symbols in memory only to record nested inclusive/exclusive timings. A cProfile run was used only for attribution; its absolute timings were not used as benchmark timings because profiler overhead is material.

Commands and results:

```powershell
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' 'C:\Temp\Contextor_Benchmarks\post0J2_clean_remap.py'
```

Result: `C:\Temp\Contextor_Benchmarks\post0J2_clean_20260830_1\results.json`, warm median `8496.942523983307` ms.

```powershell
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' 'C:\Temp\Contextor_Benchmarks\post0J2_cost_remap.py'
```

Result: `C:\Temp\Contextor_Benchmarks\post0J2_20260830_1\results.json`, detailed warm median `8325.15770199825` ms. This run had in-memory wrappers for nested attribution; it is not the authoritative wall-time baseline.

```powershell
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' 'C:\Temp\Contextor_Benchmarks\post0J2_profile.py'
```

Result: `C:\Temp\Contextor_Benchmarks\post0J2_profile_20260830_1\analyze_project.pstats`. The profiled warm call took 55.145 s and was used only to identify function ownership and repeated traversal; it is explicitly excluded from wall-time comparison.

## Accounting model

Inclusive time is the elapsed time of a symbol including wrapped descendants. Exclusive time is the elapsed time after subtracting wrapped descendant intervals. For the two requested unexplained buckets, the clean boundary harness intentionally wrapped only the named parent and `collect_module_artifacts`, so the bucket exclusive value is the per-run parent-minus-child value. The detailed harness then split the bucket into child stages.

This prevents adding a parent inclusive value to its child inclusive value. Where a parent has concurrent or separately imported descendants, aggregate leaf CPU work is reported separately and is not added to the parent wall-time total.

## Fresh top-level bucket remap

| Stage / bucket | OWNER_FILE | OWNER_SYMBOL | CALL_PATH | INCLUSIVE_MEDIAN_MS | EXCLUSIVE_MEDIAN_MS | RUN_VARIANCE | SOURCE_OR_AST_DEPENDENT | RECOMPUTES_ALREADY_AVAILABLE_STATE | DUPLICATED_WITH_OTHER_STAGE | CAN_REUSE_CURRENT_INDEX_CACHE_CANONICAL_FACTS | SEMANTIC_RISK | LIKELY_REMOVABLE_MS |
|---|---|---|---|---:|---:|---|---|---|---|---|---|---|
| Indexing repository | `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py` | `index_repository` | `ContextorFacade.analyze_project -> index_repository` | 1625.410 | 1625.410 | 1482.1–1650.9 ms | YES; warm cache validation still depends on current source metadata | NO | NO | YES | LOW; current index/cache owner and required freshness validation | 0–100 ms; no safe elimination shown |
| Reference index assembly | `C:\Temp\Contextor_Repo\contextor\core\reference\index.py` | `RepositoryReferenceIndex.from_compact_facts` via `assemble_reference_index_or_fallback` | `analyze_project -> assemble_reference_index_or_fallback` | 330.020 | 330.020 | 286.8–419.1 ms | NO on the measured available-facts warm path | NO | NO | YES | LOW; compact facts are already the intended fused input | 0 ms |
| Collision-facts extraction | `C:\Temp\Contextor_Repo\contextor\core\validator\collisions.py` | `extract_module_collision_facts` | `analyze_project -> extract_repository_collision_facts -> extract_module_collision_facts` | 1036.366 | 1036.366 | 1026.6–1110.3 ms | YES; one AST visitor per module, reusing the module AST where available | YES; indexing already traverses the same current-run ASTs | YES; duplicate AST traversal with indexing visitors | NO as an existing cache payload; an indexer extension would be required | MEDIUM-HIGH; collision snippets, locations, identical-definition classification, and failure behavior must remain exact | 0.80–1.05 s |
| Test-file AST fact extraction | `C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py` | `_extract_test_file_facts` | `analyze_project -> execute_global_pipeline -> build_artifact_pipeline -> generate_artifact_usage_report -> build_test_context_index -> TestContextIndex.build -> _extract_test_file_facts` | 900.273 | 900.273 | 866.3–920.1 ms | YES; 101 test files are AST-visited | YES; the module index already owns parsed ASTs for these files | YES; duplicate AST traversal with indexing visitors | NO as an existing cache payload; the current in-memory AST is reusable, but the derived facts are not present in the current canonical cache record | MEDIUM; names, imported modules, and assertion presence must remain exact | 0.70–0.95 s |
| Test-context index construction remainder | `C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py` | `TestContextIndex.build` | `generate_artifact_usage_report -> build_test_context_index -> TestContextIndex.build` | 1129.318 | 232.757 | 222.2–243.5 ms exclusive; 1106.5–1163.7 ms inclusive | YES; operates over test files and module paths, with AST facts extracted below it | PARTLY; current module objects and ASTs are supplied, but test index metadata is rebuilt each analysis | PARTLY; the per-file facts are new, while the path/module mapping is rebuilt | PARTLY; existing ASTs can be reused, but the derived test index is not cached | MEDIUM; filtering and excluded-file alignment are contractual | 0.70–0.95 s when paired with the child fact fusion; only 0.20–0.24 s for the construction remainder |
| Per-module test-file lookup | `C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py` | `TestContextIndex.find_test_files` | `generate_artifact_usage_report -> build_test_context -> TestContextIndex.build_test_context -> find_test_files` | 183.738 | 183.738 | 179.6–191.5 ms, one contaminated-looking run at 624.0 ms | NO; measured work scans in-memory `test_dirs` and `files_info` | YES; the same `files_info` index is scanned once per analyzed module | YES within the stage; repeated full `files_info` scan for 318 modules | YES; the existing `TestContextIndex` can own a reverse import-to-module map | LOW-MEDIUM; preserve filename conventions and import-prefix matching | 0.15–0.19 s |
| Test-directory discovery | `C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py` | `discover_test_dirs` | `generate_artifact_usage_report -> discover_test_dirs` | 168.520 | 168.520 | 163.9–196.2 ms | YES; filesystem walk or filtered path projection | NO; it derives repository-level test layout from the current filtered module paths | NO with another measured stage | YES only as an in-memory result passed to the test index; it is not in the current index cache | LOW; existing exclusion and allowed-path semantics are sensitive | 0.05–0.15 s |
| Artifact worker collection | `C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py` | `collect_module_artifacts` | `generate_artifact_usage_report -> collect_module_artifacts` | 1199.710 | 1199.710 | 728.1–1393.6 ms | YES in fallback-capable code; measured warm normal path used available facts and no fallback count | NO on the normal available-facts path | NO after 0J2 fusion; this remains the artifact worker computation | YES; receives current symbol/reference facts and reference index | MEDIUM; ProcessPool/fallback and cancellation contracts must remain intact | 0–0.20 s; variance dominates any safe conclusion |
| Shared-cluster computation from canonical state | `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py` | `compute_shared_usage_clusters_from_state` | `analyze_project -> canonical state construction -> compute_shared_usage_clusters_from_state -> compute_shared_usage_clusters -> build_jaccard_clusters` | 297.084 | 297.084 as a leaf boundary | 287.8–337.7 ms | NO; documented pure-RAM canonical facts path | YES; equivalent artifact/consumption facts and Jaccard computation already exist in report generation | YES; same Jaccard-family work is performed by graph analytics during artifact pipeline | YES; canonical RAM facts and the report-side graph-analytics input are already available | MEDIUM-HIGH; report compacting and canonical state shape differ, so exact parity must be proven before reuse | 0.25–0.33 s |
| Artifact pipeline remainder after usage report | `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py` | `build_artifact_pipeline` | `execute_global_pipeline -> build_artifact_pipeline` | 3583.112 | 339.869 after wrapped usage, compaction, registry, and analytics children | 310.9–464.5 ms exclusive; 3028.6–3749.0 ms inclusive | NO AST; consumes artifact/report RAM structures and persists registry/report forms | NO; compaction and report representations are required outputs | NO as a complete stage, although graph analytics has reused source facts | PARTLY; shares input facts but output dictionaries and compact IDs are distinct | MEDIUM; identities, compact representations, and graph analytics report contract all matter | 0.10–0.35 s; no single safe elimination isolated |
| Jaccard-cluster leaf work across global/layer/state consumers | `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py` | `build_jaccard_clusters` | `build_artifact_pipeline -> generate_graph_analytics_report -> build_jaccard_clusters`, layer analytics, and canonical-state cluster path | 720.510 aggregate | 720.510 aggregate leaf time; not added to parent wall time | 673.2–786.9 ms aggregate over four calls | NO; pure-RAM artifact projection and Jaccard work | YES for the state-side call and report-side equivalent facts | YES across global report, layer reports, and canonical-state materialization | YES; projection and cluster result can potentially be carried once, but exact compact/canonical shape must be preserved | MEDIUM-HIGH; multiple scopes and compact-ID output need parity | 0.25–0.45 s whole-analysis wall time, subject to scope overlap |
| Canonical snapshot save | `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py` | `save_engine_state` | `analyze_project -> save_engine_state -> live_state.save_snapshot` | 260.730 | 260.730 | 241.7–341.6 ms | NO AST; serialization and atomic snapshot persistence | NO; required publication/persistence work | NO; this is the canonical save boundary | NO; index facts are inputs, not a replacement for the snapshot | LOW-MEDIUM; persistence ordering and atomicity are correctness boundaries | 0–0.05 s |
| Incremental file-state updates | `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py` | `FileStateManager.update_state` | `execute_global_pipeline -> FileStateManager.update_state` for 318 modules | 123.390 aggregate | 123.390 aggregate | 109.7–127.2 ms | YES for source metadata/stat validation, not AST analysis | NO; required incremental state bookkeeping | NO across another stage | NO; it records file state rather than canonical semantic facts | LOW; persistence coverage must remain exact | 0–0.05 s |
| Global pipeline remainder excluding usage-report child | `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py` | `execute_global_pipeline` | `analyze_project -> execute_global_pipeline`, excluding its complete `generate_artifact_usage_report` child boundary | 3916.750 | 1492.616 clean boundary remainder | 1440.5–1566.4 ms | NO AST for the remainder; orchestration, report forms, layers, writes, and incremental state | NO as a whole; it contains required report/persistence outputs | NO as a whole; its children are the work accounted below | PARTLY; it passes already-built report facts to downstream forms | MEDIUM; orchestration and output contracts make broad removal unsafe | 0.15–0.35 s outside the separately ranked child candidates |
| Repository identity initialization | `C:\Temp\Contextor_Repo\contextor\core\api\facade.py` | `_initialize_repository_identity` | `ContextorFacade.analyze_project -> _initialize_repository_identity` | 114.340 | 113.630 | 105.7–126.1 ms | NO AST; identity/registry setup | NO; required repository collision-safe identity setup | NO | NO; it is the identity authority | LOW; identity collisions and path normalization are correctness boundaries | 0–0.03 s |
| Report-header preparation | `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\header.py` | `build_report_header` | `execute_global_pipeline -> build_report_header` | 105.920 | 105.920 | 95.3–119.0 ms | YES for repository metadata/filesystem context | NO; header is required report metadata | NO | PARTLY; consumes repository identity and path metadata but not index semantic facts | LOW-MEDIUM; public header compatibility matters | 0–0.03 s |

The detailed trace also measured `write_global_reports` at 88.8 ms median, `topology_analytics` at 87.0 ms inclusive / 23.8 ms exclusive, `_compute_pagerank` at 72.7 ms aggregate, `_compute_hub_authority` at 67.5 ms aggregate, `compute_dependency_matrix` at 39.3 ms inclusive, `build_module_dependency_matrix` at 43.5 ms, and `build_core_extraction_candidates` at below 1 ms. These are below the approximately 100 ms exclusive material-stage threshold and are not ranked as targets.

## Requested bucket decomposition

### `generate_artifact_usage_report` excluding `collect_module_artifacts`

Clean boundary values:

- `generate_artifact_usage_report` inclusive median: **2412.040 ms**.
- `collect_module_artifacts` inclusive median: **832.010 ms**.
- Per-run parent-minus-child exclusive remainder: **1581.835 ms**.
- Remainder values: **1583.6, 1566.0, 1610.2, 1594.1, 1580.1, 1551.9 ms**.

The detailed child trace partitions that remainder into approximately:

- `_extract_test_file_facts`: **900.273 ms** exclusive median.
- `TestContextIndex.build` own remainder after its fact-extraction child: **232.757 ms**.
- `TestContextIndex.find_test_files`: **183.738 ms**.
- `discover_test_dirs`: **168.520 ms**.
- remaining report assembly, per-module mapping, artifact-index flattening, filtering, clusters, and candidate construction: approximately **100–150 ms**, with no single safe target above the threshold after the measured children are removed.

The bucket is therefore primarily test-context discovery/indexing/fact extraction, not artifact-index construction or shared-artifact filtering.

### `GLOBAL_PIPELINE` excluding the complete artifact-usage stage

Clean boundary values:

- `execute_global_pipeline` inclusive median: **3916.750 ms**.
- Complete `generate_artifact_usage_report` child inclusive median: **2412.040 ms**.
- Per-run parent-minus-child exclusive remainder: **1492.616 ms**.
- Remainder values: **1532.3, 1566.4, 1516.4, 1467.0, 1468.9, 1440.5 ms**.

The detailed trace shows that this remainder contains the artifact-pipeline forms after usage extraction, graph analytics and layer report work, report writes, incremental file-state updates, and canonical result preparation. Its own residual after subtracting all instrumented children was only approximately **122.290 ms** median, so the 1492.616 ms bucket must not be interpreted as one monolithic removable function. The measurable candidates inside it are the separately listed Jaccard/graph analytics and persistence stages; the rest is required output orchestration and serialization.

## Contextor MCP architectural evidence

The current canonical state reported by Contextor was fresh at revision **35**, with verified workspace synchronization and fresh module, graph, topology, artifact-consumption, cycles, and collisions families.

The following Contextor calls were used surgically for ownership, call path, and reuse decisions:

- `get_symbol_implementation` resolved `ContextorFacade.analyze_project` to `C:\Temp\Contextor_Repo\contextor\core\api\facade.py`, lines 301–594; it confirmed the exact sequence: index, reference assembly, collision-fact extraction, graph/validation/metrics, global pipeline, then canonical persistence.
- `get_symbol_implementation` resolved `execute_global_pipeline` to `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py`, lines 32–634.
- `get_symbol_implementation` resolved `build_artifact_pipeline` to `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py`, lines 37–125.
- `get_symbol_implementation` resolved `generate_artifact_usage_report` to `C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py`, lines 701–881. Its implementation directly calls `collect_module_artifacts`, `build_artifact_index`, shared-artifact key/filter helpers, connected-component clusters, core candidates, `discover_test_dirs`, `build_test_context_index`, and per-module `build_test_context`.
- `get_symbol_implementation` resolved `extract_repository_collision_facts` to `C:\Temp\Contextor_Repo\contextor\core\validator\collisions.py`, lines 356–382. It loops over all modules and calls `extract_module_collision_facts` on each current module AST.
- `get_symbol_implementation` resolved `extract_module_collision_facts` to the same file, lines 340–353. It constructs `PublicSymbolCollector` and visits the complete AST.
- `get_symbol_implementation` resolved `_process_single_file` to `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py`, lines 198–320. It confirmed that the current index worker already parses once on cold/migration paths and produces imports, symbol facts, and reference facts from that AST; collision facts and test-file facts are not current fields in that payload.
- `get_symbol_implementation` resolved `TestContextIndex.build` to `C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py`, lines 223–289. It confirmed per-test-file `_extract_test_file_facts(tree)` and reuse of known module ASTs when available.
- `get_symbol_implementation` resolved `discover_test_dirs` to the same file, lines 50–109. Its contract explicitly states that discovery is repository-level and should be done once, using already-filtered paths.
- `get_symbol_implementation` resolved `compute_shared_usage_clusters_from_state` to `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py`, lines 2251–2271. It confirmed that the state path projects canonical RAM artifact/consumption facts and calls the same `build_jaccard_clusters` family used by report analytics.
- `get_symbol_implementation` resolved `build_artifact_data_projection` to the same graph-analytics file, lines 2080–2181. Its explicit invariants state zero filesystem reads, zero report reads, zero AST parsing, and single-source use of canonical RAM facts.
- `get_symbol_implementation` resolved `save_engine_state` to `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py`, lines 343–369; it is a save-snapshot boundary, not an analysis recomputation.
- `get_symbol_call_context` confirmed the direct intra-module edges from `generate_artifact_usage_report` to `collect_module_artifacts`, `build_artifact_index`, shared-artifact helpers, clusters, and core candidates; and from `TestContextIndex.build` to `_extract_test_file_facts` and `discover_test_dirs`.
- `get_symbol_call_context` confirmed `extract_repository_collision_facts -> extract_module_collision_facts` and the legacy collision caller relationship. The tool correctly reports intra-module edges only; dynamic/local imports in the facade and pipeline were verified with exact source ranges rather than guessed from missing call-graph edges.

## Candidate ranking

Ranking is by expected reduction in complete `analyze_project` wall time, not by local percentage speedup.

### 1. Fuse collision-fact extraction into the existing index worker

CURRENT_EVIDENCE: `extract_module_collision_facts` is a stable **1036.366 ms exclusive median** across 318 calls and is an AST visitor over ASTs already traversed by the indexer. The current index worker already has the AST and emits per-module fact payloads.

OWNER: `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py::_process_single_file`, with consumer/semantic owner `C:\Temp\Contextor_Repo\contextor\core\validator\collisions.py::extract_module_collision_facts`.

REMOVABLE_WORK: the second `PublicSymbolCollector` traversal across the current module ASTs, plus the parent aggregation loop if the complete collision-fact side table is returned with the index.

SAFE_OPTIMIZATION_SHAPE: extend the existing index-worker fact extraction and `RepositoryIndex` transfer path with collision facts, preserving the current collision-facts schema and fail-closed behavior. `compute_collisions_from_facts` must remain the sole aggregation/classification authority. Do not persist AST or source and do not create a second cache.

EXPECTED_WHOLE_ANALYSIS_SAVING_MS: **800–1050 ms**.

SEMANTIC_RISK: **MEDIUM-HIGH** because collision facts carry public symbol type/name, code snippets, line/column locations, identical-definition classification, and error behavior.

REQUIRED_INVARIANTS: exact `extract_repository_collision_facts` parity; exact `compute_collisions_from_facts` output; complete module coverage gate; no partial facts accepted as complete; source-change invalidation; transient extraction failures not persisted negatively; current `collision_facts` remains the input to validation, report, canonical state, and persistence.

### 2. Fuse test-file facts into the existing indexed AST/fact pass

CURRENT_EVIDENCE: `_extract_test_file_facts` is **900.273 ms exclusive median** over 101 test files, and `TestContextIndex.build` adds **232.757 ms** of own index construction. The Contextor source contract confirms that known module ASTs are already reused, but the test-context visitor runs again to derive names, imported modules, and assertion presence.

OWNER: `C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py::TestContextIndex.build`, with the upstream fusion point at `C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py::_process_single_file`.

REMOVABLE_WORK: the second AST fact extraction pass over test files and part of the per-analysis test-index construction.

SAFE_OPTIMIZATION_SHAPE: derive the exact test-file facts during the existing index AST pass and pass them through the existing index result into `TestContextIndex`; preserve `discover_test_dirs` filtering and all fallback behavior for callers outside the full facade path.

EXPECTED_WHOLE_ANALYSIS_SAVING_MS: **700–950 ms**.

SEMANTIC_RISK: **MEDIUM** because assertion detection, imported-module matching, excluded paths, and tested/untested symbol classification must remain exact.

REQUIRED_INVARIANTS: exact `TestContextIndex` parity; one fact extraction per test file; no reparse on warm current facts; correct allowed-path/exclude semantics; standalone callers retain fallback; no AST/source persistence; `find_test_files` and `extract_tested_symbols` consume the same facts.

### 3. Reuse the report-side Jaccard result for canonical Shared Usage Clusters

CURRENT_EVIDENCE: `compute_shared_usage_clusters_from_state` costs **297.084 ms inclusive median** and calls `build_artifact_data_projection` plus `build_jaccard_clusters`. The artifact pipeline already invokes graph analytics over equivalent artifact/usage RAM facts, while the detailed trace recorded **720.510 ms aggregate** across four Jaccard calls spanning global, layers, and state.

OWNER: `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py::compute_shared_usage_clusters_from_state`, with producer `build_artifact_pipeline`.

REMOVABLE_WORK: repeated canonical projection and Jaccard clustering after the report-side result has already been computed.

SAFE_OPTIMIZATION_SHAPE: carry an uncompact, canonical-shape Jaccard result or a proven conversion payload through the private analysis-result path and let canonical persistence consume it. Keep layer-scoped and compact-ID report outputs separate from the canonical state payload.

EXPECTED_WHOLE_ANALYSIS_SAVING_MS: **250–330 ms**.

SEMANTIC_RISK: **MEDIUM-HIGH** because the report-side graph analytics result is compacted and scoped, while canonical state has its own freshness/trust gate and shape.

REQUIRED_INVARIANTS: exact `build_jaccard_clusters` parity; canonical state only accepts complete fresh artifact-consumption inputs; no partial/stale result is published; graph analytics and canonical state remain independently failure-safe; compact report IDs are not accidentally stored as canonical qualified identities.

### Lower-ranked measurable candidate

`TestContextIndex.find_test_files` has a stable **183.738 ms** median except one 624 ms contaminated-looking run. A reverse import-to-module map built once per `TestContextIndex` could remove most of the repeated `files_info` scan, with an estimated **150–190 ms** whole-analysis saving and low-medium semantic risk. It ranks below the three candidates above.

## Non-candidates and unavoidable work

- `index_repository` remains a large warm stage at 1625.410 ms, but current evidence describes it as the index/cache freshness owner. No duplicated semantic pass or safe elimination was isolated in this remap; moving its work would only relocate required validation.
- `collect_module_artifacts` remains variable at 1199.710 ms median, with 728.1–1393.6 ms observed. The post-0J2 normal warm path already uses available facts and adaptive serial execution; the spread is not enough evidence for a new elimination target.
- `build_artifact_index`, `get_shared_artifact_keys`, `filter_shared_artifacts`, `build_shared_usage_clusters`, and `build_core_extraction_candidates` were all below approximately 13 ms exclusive median individually. They are not targets.
- `save_engine_state`, file-state updates, report writes, and identity initialization are required persistence/contract boundaries. Their measured cost is real but no safe removal was established.
- Graph metrics, cycles, debt, hotspots, topology analytics, dependency matrix, and individual graph-analytics metric helpers were below the material exclusive threshold in this remap, except for the separately identified Jaccard-family aggregation and canonical Shared Usage Cluster recomputation.

## Contamination and confidence

The authoritative wall-time run had six warm observations with a 4.0% peak-to-peak range and no analysis errors. The detailed run contained one elevated `artifact_pipeline` exclusive observation (464.5 ms) and one elevated `global_pipeline` observation in an earlier instrumented pass; these were retained in variance rather than silently discarded. The profiled run is explicitly not used for absolute timing. Candidate ranking is based on repeated normal-path measurements plus Contextor-confirmed ownership and data flow.

## Worktree and change accounting

The repository was already dirty from the preceding post-0J2 work and an unrelated runtime-log modification. The observed pre-existing task-related paths included the prior production changes, prior reference-fusion tests, and `walkthrough.md`; the runtime logs were not touched. No production or test file was changed by this discovery task. External benchmark scripts and outputs are outside the repository and are not task files.

FILES_CHANGED=NONE
DIFFS=NONE

NEXT_TARGET=extract_module_collision_facts
EXPECTED_WHOLE_ANALYSIS_SAVING_MS=800-1050
WHY=It is the largest stable removable-looking leaf: a 1036 ms median AST visitor over module ASTs already traversed by the index worker, with Contextor-confirmed ownership and a clear single-pass fusion shape.
