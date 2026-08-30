# Post-0J4 warm cost remap

## Scope and outcome

Discovery/measurement only. No production or test file was edited. No benchmark file was created in the repository; the harness and all runtime artifacts were kept under C:\Temp\Contextor_Benchmarks.

Current warm whole-analysis median: 6559.137 ms from the latest six-observation run. Accepted post-0J4 reference from the prior thread: approximately 6516.110 ms. Accepted post-0J3 median: approximately 7703.149 ms. The latest result is consistent with the accepted post-0J4 range and does not show a regression attributable to this turn.

The largest remaining removable candidate is a duplicate pure-RAM Shared Usage Clusters computation in canonical-state persistence. The recommended next target is a raw-cluster handoff from the already executed global graph-analytics computation into canonical-state construction, while preserving the compact public report and full-name canonical state. The lower-risk alternative is the repeated TestContextIndex.find_test_files scan.

## Contextor evidence

Contextor MCP was used before textual verification.

Current canonical state:
- canonical revision: 68
- canonical state: fresh
- workspace synchronization: verified
- provenance: live
- fresh families: module, graph, topology, artifact_consumption, cycles, collisions
- architecture: 320 modules, 7 layers, 0 cycles, 0 name collisions
- graph_analytics: live canonical topology, fan-in 16, fan-out 6
- test_context: live canonical topology, fan-in 6, fan-out 2
- indexer: live canonical topology, fan-in 21, fan-out 10

Contextor resolved the complete path as:
ContextorFacade.analyze_project -> index_repository -> assemble_reference_index_or_fallback -> assemble_collision_facts_or_fallback -> graph/trie/validation/metrics -> execute_global_pipeline -> build_artifact_pipeline -> generate_artifact_usage_report -> collect_module_artifacts -> artifact index/test-context construction -> global graph analytics -> layer pipelines -> report writes and incremental state update -> canonical-state construction -> compute_shared_usage_clusters_from_state -> save_engine_state.

Contextor resolved build_jaccard_clusters callers exactly:
- generate_graph_analytics_report line 1838;
- compute_shared_usage_clusters line 2222;
- compute_shared_usage_clusters_from_state reaches it through compute_shared_usage_clusters line 2264.

Contextor resolved collect_module_artifacts as a direct callee only of generate_artifact_usage_report line 729.

Contextor source confirms build_artifact_pipeline calls generate_artifact_usage_report, then registry synchronization/compaction, then generate_graph_analytics_report(scope="global"). The global graph-analytics result is retained in ArtifactPipelineResult.graph_analytics_data and returned through execute_global_pipeline.

Contextor source confirms layer pipelines call the same graph-analytics authority with scope="layer" and scope_modules. Layer work is semantically distinct.

Contextor source confirms compute_shared_usage_clusters_from_state builds a pure-RAM projection from state.artifacts and state.artifact_consumption, then invokes build_jaccard_clusters. The projection contract states zero filesystem reads, zero report reads, and zero AST parsing.

Existing parity evidence in tests/test_matrix_clusters_ram_parity.py asserts exact equality between snapshot build_jaccard_clusters(production_artifact_data, min_jaccard=0.30) and canonical compute_shared_usage_clusters_from_state(state, min_jaccard=0.30). The same test asserts field-by-field artifact and usage-sidecar parity before the cluster comparison.

Contextor source confirms _compact_clusters converts modules and shared_artifact_keys to registry-compacted IDs for the public graph report. The public graph_analytics_data shared_usage_clusters cannot be assigned directly to canonical state. Any fusion must retain a pre-compaction raw result in an internal in-memory handoff and must not expose raw IDs in the public report.

Contextor source confirms index_repository owns the current per-file collection of modules, symbol facts, reference facts, collision facts, and test facts, and uses a normal ProcessPoolExecutor unless disabled. Contextor source confirms _process_single_artifact_module reuses available symbol facts, projects references through the existing RepositoryReferenceIndex, and classifies API consumers; it only falls back to source symbol extraction when facts are unavailable.

## Benchmark protocol

Harness: C:\Temp\Contextor_Benchmarks\post0J4_warm_cost_remap.py
Latest result: C:\Temp\Contextor_Benchmarks\post0J4_warm_cost_remap_scoped_20260830\results.json
Command:
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' 'C:\Temp\Contextor_Benchmarks\post0J4_warm_cost_remap.py'

Controls:
- disposable source copy outside the repository;
- isolated cache, state, output, and registry directories outside the repository;
- one cold setup run followed by six warm observations;
- normal ProcessPool enabled;
- detached LIVE publication by patching only the benchmark process live_state.connect;
- no benchmark artifacts inside C:\Temp\Contextor_Repo;
- inclusive/exclusive wall timing with nested child time removed;
- parent-process CPU timing collected in the latest run; ProcessPool worker CPU is not included in that parent counter.

Latest six raw warm whole-analysis observations (ms):
6558.905321988277, 6445.370152010582, 6516.624249983579, 6559.3692770344205, 6768.302326032426, 6853.282959025819

Latest warm median: 6559.137299511349 ms
Latest range: 6445.370152010582-6853.282959025819 ms (407.913 ms)

A prior scoped instrumentation run was materially contaminated and is retained:
6582.641369954217, 7597.543053969275, 7662.665017996915, 7926.3252730015665, 6593.813459039666, 6533.0025180010125
Contaminated-run median: 7095.6782565044705 ms

## Derived unexplained buckets

These are inclusive residuals, not extra additive stages. The detailed stage records use exclusive timings to avoid double counting.

- generate_artifact_usage_report inclusive median: 1600.657 ms.
- collect_module_artifacts inclusive median: 943.040 ms.
- generate_artifact_usage_report excluding collect_module_artifacts: 657.617 ms inclusive residual. Its fully exclusive outer remainder is 5.118 ms; the residual is explained by test-directory discovery, test-index construction, 320 test-context calls, and nested find_test_files.
- execute_global_pipeline inclusive median: 3046.604 ms.
- execute_global_pipeline excluding complete artifact-usage stage: 1445.947 ms inclusive residual.
- fully exclusive execute_global_pipeline remainder: 125.383 ms.
- build_artifact_pipeline exclusive remainder after instrumented children: 357.149 ms. This is registry/compaction/graph-report/layer/report preparation residual and is not one proven eliminable operation.

## Material stage records

All timings are latest six-run warm medians. RUN_VARIANCE gives the six-value min-max range. Exclusive timing subtracts all instrumented child time.

### Initialization, index, and references

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\api\facade.py
OWNER_SYMBOL=_initialize_repository_identity
CALL_PATH=ContextorFacade.analyze_project -> _initialize_repository_identity
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=109.951
EXCLUSIVE_MEDIAN_MS=109.263
RUN_VARIANCE=101.595-121.401 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=NO
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=PARTIAL
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=LOW + repository identity and registry setup are required

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\symbol_engine\indexer.py
OWNER_SYMBOL=index_repository
CALL_PATH=ContextorFacade.analyze_project -> index_repository -> ProcessPoolExecutor -> _process_single_file
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=1793.122
EXCLUSIVE_MEDIAN_MS=1793.122
RUN_VARIANCE=1697.302-1926.639 ms
SOURCE_OR_AST_DEPENDENT=YES + worker freshness/index extraction can use source/AST; current warm facts are reused where valid
RECOMPUTES_ALREADY_AVAILABLE_STATE=PARTIAL + validates/reassembles current per-file state while rebuilding RepositoryIndex
DUPLICATED_WITH_OTHER_STAGE=NO proven duplicate
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=PARTIAL
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-50 without new proof
SEMANTIC_RISK=HIGH + freshness, failure handling, and complete-domain assembly are correctness contracts

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reference\index.py
OWNER_SYMBOL=assemble_reference_index_or_fallback
CALL_PATH=ContextorFacade.analyze_project -> assemble_reference_index_or_fallback -> RepositoryReferenceIndex.from_compact_facts
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=512.785
EXCLUSIVE_MEDIAN_MS=512.785
RUN_VARIANCE=408.338-555.043 ms
SOURCE_OR_AST_DEPENDENT=NO on the normal warm current-facts path
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO + assembles a query index from current compact reference facts
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + the resulting index is shared by artifact assembly
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0 without a new validated persistent derived-index contract
SEMANTIC_RISK=HIGH + this is the shared repository reference-index authority

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\api\facade.py
OWNER_SYMBOL=execute_global_pipeline
CALL_PATH=ContextorFacade.analyze_project -> execute_global_pipeline
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=3046.604
EXCLUSIVE_MEDIAN_MS=125.383
RUN_VARIANCE=2995.529-3396.438 ms inclusive; 110.223-139.432 ms exclusive
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=PARTIAL
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + contains artifact pipeline and canonical persistence
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=PARTIAL
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-125
SEMANTIC_RISK=HIGH + owns report, layer, incremental-state, and result contracts

### Artifact and test-context stages

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\artifact_pipeline.py
OWNER_SYMBOL=build_artifact_pipeline
CALL_PATH=execute_global_pipeline -> build_artifact_pipeline
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=2359.972
EXCLUSIVE_MEDIAN_MS=357.149
RUN_VARIANCE=2324.767-2696.202 ms inclusive; 332.338-385.929 ms exclusive
SOURCE_OR_AST_DEPENDENT=NO on the normal warm current-facts path
RECOMPUTES_ALREADY_AVAILABLE_STATE=PARTIAL
DUPLICATED_WITH_OTHER_STAGE=PARTIAL
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=PARTIAL
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-150, exact owner unknown
SEMANTIC_RISK=MEDIUM + fuses registry, compaction, graph report, and returned bundle contracts

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py
OWNER_SYMBOL=generate_artifact_usage_report
CALL_PATH=build_artifact_pipeline -> generate_artifact_usage_report
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=1600.657
EXCLUSIVE_MEDIAN_MS=5.118
RUN_VARIANCE=1565.537-1902.169 ms inclusive; 4.729-6.740 ms exclusive
SOURCE_OR_AST_DEPENDENT=NO on normal warm current-facts path; inner worker has source fallback when facts are unavailable
RECOMPUTES_ALREADY_AVAILABLE_STATE=PARTIAL
DUPLICATED_WITH_OTHER_STAGE=PARTIAL
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-205 only through a proven child fusion
SEMANTIC_RISK=MEDIUM + report payload and traceability shape must remain identical

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py
OWNER_SYMBOL=collect_module_artifacts
CALL_PATH=generate_artifact_usage_report -> collect_module_artifacts -> _process_single_artifact_module
CALL_COUNT=1 per run; one internal module task per eligible module
INCLUSIVE_MEDIAN_MS=943.040
EXCLUSIVE_MEDIAN_MS=943.040
RUN_VARIANCE=900.302-1166.244 ms
SOURCE_OR_AST_DEPENDENT=YES + source symbol fallback exists; warm path reused available symbol facts
RECOMPUTES_ALREADY_AVAILABLE_STATE=PARTIAL + derives own-symbol/reference/API-consumer artifact records
DUPLICATED_WITH_OTHER_STAGE=NO proven duplicate
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-100 without an equivalent prebuilt consumer projection
SEMANTIC_RISK=HIGH + artifact identity, consumer channels, failures, and usage sidecar must not change

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py
OWNER_SYMBOL=build_artifact_index
CALL_PATH=generate_artifact_usage_report -> build_artifact_index
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=11.033
EXCLUSIVE_MEDIAN_MS=11.033
RUN_VARIANCE=9.412-14.416 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=NO
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=LOW + required deterministic report assembly

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py
OWNER_SYMBOL=discover_test_dirs
CALL_PATH=generate_artifact_usage_report -> discover_test_dirs
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=179.159
EXCLUSIVE_MEDIAN_MS=179.159
RUN_VARIANCE=163.243-239.611 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=YES + filters/resolves the already assembled allowed Python path set
DUPLICATED_WITH_OTHER_STAGE=PARTIAL
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=PARTIAL
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=PARTIAL
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=120-175 if exact candidate map is fused
SEMANTIC_RISK=MEDIUM + root naming, tests/test rules, exclusions, and explicit test_dirs semantics must remain exact

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py
OWNER_SYMBOL=TestContextIndex.build
CALL_PATH=generate_artifact_usage_report -> build_test_context_index -> TestContextIndex.build
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=228.872
EXCLUSIVE_MEDIAN_MS=228.872
RUN_VARIANCE=200.165-235.756 ms
SOURCE_OR_AST_DEPENDENT=NO on normal warm supplied test facts
RECOMPUTES_ALREADY_AVAILABLE_STATE=PARTIAL
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + one-time indexing is separate from repeated lookup
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-30 after accepted 0J4 fusion
SEMANTIC_RISK=MEDIUM + candidate membership and supplied-directory compatibility are public behavior

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py
OWNER_SYMBOL=TestContextIndex.build_test_context
CALL_PATH=generate_artifact_usage_report -> build_test_context -> TestContextIndex.build_test_context
CALL_COUNT=320 per run
INCLUSIVE_MEDIAN_MS=232.635 aggregate
EXCLUSIVE_MEDIAN_MS=7.105 aggregate
RUN_VARIANCE=212.948-244.213 ms inclusive; 6.593-8.355 ms exclusive
SOURCE_OR_AST_DEPENDENT=NO on normal warm fact-index path
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + inclusive time contains find_test_files
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-205 only through nested lookup
SEMANTIC_RISK=MEDIUM + output classification must remain exact

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py
OWNER_SYMBOL=TestContextIndex.find_test_files
CALL_PATH=TestContextIndex.build_test_context -> TestContextIndex.find_test_files
CALL_COUNT=320 per run
INCLUSIVE_MEDIAN_MS=217.302
EXCLUSIVE_MEDIAN_MS=217.302
RUN_VARIANCE=199.258-227.480 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=YES + scans the same files_info imported-module sets for every module
DUPLICATED_WITH_OTHER_STAGE=YES + repeated scan over one run-scoped in-memory index
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=150-205 net
SEMANTIC_RISK=LOW + reverse lookup can preserve equality, dotted-prefix, dedupe, and sort semantics

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py
OWNER_SYMBOL=build_shared_usage_clusters
CALL_PATH=generate_artifact_usage_report -> build_shared_usage_clusters
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=10.429
EXCLUSIVE_MEDIAN_MS=10.429
RUN_VARIANCE=8.913-14.666 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=NO
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=LOW + small report-local cluster assembly

### Graph analytics and persistence

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
OWNER_SYMBOL=build_jaccard_clusters
CALL_PATHS=build_artifact_pipeline -> generate_graph_analytics_report(scope=global) -> build_jaccard_clusters; layer_pipeline -> generate_graph_analytics_report(scope=layer) -> build_jaccard_clusters; facade persistence -> compute_shared_usage_clusters_from_state -> compute_shared_usage_clusters -> build_jaccard_clusters
CALL_COUNT=4 per run
INCLUSIVE_MEDIAN_MS=665.592 aggregate
EXCLUSIVE_MEDIAN_MS=665.592 aggregate
RUN_VARIANCE=654.363-727.774 ms aggregate
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=YES + pure-RAM complete-linkage computation
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + global/canonical are parity-equivalent before compaction; layer calls are distinct
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=PARTIAL
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=280-320 for canonical state only; 0 for layer calls
SEMANTIC_RISK=MEDIUM + public compact IDs differ from canonical full IDs

Observed Jaccard input shapes:
- global/full report: 634 artifacts, 320 module-artifact entries, private keys present;
- layer scope: 634 artifacts with scoped report keys;
- empty layer scope: 0 artifacts;
- canonical-state projection: 634 artifacts with projection/sidecar keys.

Thus the full 665.592 ms is not one removable duplicate. Only the global/canonical pair is a candidate.

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
OWNER_SYMBOL=compute_shared_usage_clusters_from_state
CALL_PATH=ContextorFacade.analyze_project -> canonical state construction -> compute_shared_usage_clusters_from_state -> compute_shared_usage_clusters
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=317.092
EXCLUSIVE_MEDIAN_MS=0.498
RUN_VARIANCE=295.509-363.600 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=YES
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + exact pre-compaction cluster semantics are already computed in global graph analytics
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES after exact projection/parity validation
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=280-320
SEMANTIC_RISK=MEDIUM + coverage validation and raw/full-ID handoff must remain authoritative

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
OWNER_SYMBOL=build_artifact_data_projection
CALL_PATH=compute_shared_usage_clusters_from_state -> compute_shared_usage_clusters -> build_artifact_data_projection
CALL_COUNT=2 per run aggregate with dependency-matrix path
INCLUSIVE_MEDIAN_MS=63.174 aggregate
EXCLUSIVE_MEDIAN_MS=63.174 aggregate
RUN_VARIANCE=48.983-211.431 ms aggregate
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=PARTIAL
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-40 in the selected cluster fusion
SEMANTIC_RISK=MEDIUM + projection parity is a tested contract

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
OWNER_SYMBOL=generate_graph_analytics_report
CALL_PATH=build_artifact_pipeline -> generate_graph_analytics_report(scope=global)
CALL_COUNT=1 direct global call per run; two additional layer calls use the same symbol
INCLUSIVE_MEDIAN_MS=387.782 direct global alias
EXCLUSIVE_MEDIAN_MS=26.710 direct global alias
RUN_VARIANCE=364.864-428.611 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=PARTIAL
DUPLICATED_WITH_OTHER_STAGE=PARTIAL
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=PARTIAL
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-320 only by preserving raw clusters already computed
SEMANTIC_RISK=MEDIUM + report schema, scope, compact IDs, matrix, and visibility must remain unchanged

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
OWNER_SYMBOL=_compute_pagerank
CALL_PATH=generate_graph_analytics_report -> _compute_pagerank
CALL_COUNT=4 per run
INCLUSIVE_MEDIAN_MS=70.695 aggregate
EXCLUSIVE_MEDIAN_MS=70.695 aggregate
RUN_VARIANCE=66.298-81.472 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + distinct global/layer scopes
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=PARTIAL
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=LOW + scope-specific RAM metric

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
OWNER_SYMBOL=_compute_hub_authority
CALL_PATH=generate_graph_analytics_report -> _compute_hub_authority
CALL_COUNT=4 per run
INCLUSIVE_MEDIAN_MS=63.711 aggregate
EXCLUSIVE_MEDIAN_MS=63.711 aggregate
RUN_VARIANCE=59.936-76.528 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + distinct scopes
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=PARTIAL
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=LOW + scope-specific RAM metric

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
OWNER_SYMBOL=compute_topology_analytics
CALL_PATH=facade persistence -> compute_topology_analytics
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=95.503
EXCLUSIVE_MEDIAN_MS=27.799
RUN_VARIANCE=82.371-117.701 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=YES
DUPLICATED_WITH_OTHER_STAGE=PARTIAL
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=MEDIUM + canonical topology must remain independently valid

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py
OWNER_SYMBOL=build_module_dependency_matrix
CALL_PATH=generate_graph_analytics_report -> build_module_dependency_matrix
CALL_COUNT=4 per run
INCLUSIVE_MEDIAN_MS=45.460
EXCLUSIVE_MEDIAN_MS=45.460
RUN_VARIANCE=38.633-203.123 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=YES
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + global/layer/state scopes
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=PARTIAL
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=MEDIUM + exact matrix scope parity required

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py
OWNER_SYMBOL=save_engine_state
CALL_PATH=ContextorFacade.analyze_project -> canonical state construction -> save_engine_state
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=277.812
EXCLUSIVE_MEDIAN_MS=277.812
RUN_VARIANCE=232.238-323.883 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=NO proven duplicate
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=PARTIAL
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=HIGH + persistence, revision, and file-state synchronization are required

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py
OWNER_SYMBOL=FileStateManager.update_state
CALL_PATH=execute_global_pipeline -> FileStateManager.update_state for each indexed module
CALL_COUNT=320 per run
INCLUSIVE_MEDIAN_MS=138.744 aggregate
EXCLUSIVE_MEDIAN_MS=138.744 aggregate
RUN_VARIANCE=125.673-154.348 ms aggregate
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=NO proven duplicate
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=PARTIAL
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=HIGH + freshness and incremental invalidation persistence

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine/header.py
OWNER_SYMBOL=build_report_header
CALL_PATH=execute_global_pipeline -> build_report_header
CALL_COUNT=1 per run
INCLUSIVE_MEDIAN_MS=103.051
EXCLUSIVE_MEDIAN_MS=103.051
RUN_VARIANCE=92.619-116.600 ms
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=NO
DUPLICATED_WITH_OTHER_STAGE=NO
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=PARTIAL
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=YES
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=LOW + report metadata contract

OWNER_FILE=C:\Temp\Contextor_Repo\contextor\core\reporting_engine/layer_pipeline.py
OWNER_SYMBOL=execute_layer_pipeline
CALL_PATH=execute_global_pipeline -> execute_layer_pipeline -> generate_graph_analytics_report(scope=layer)
CALL_COUNT=2 per run
INCLUSIVE_MEDIAN_MS=177.603 aggregate
EXCLUSIVE_MEDIAN_MS=32.142 aggregate
RUN_VARIANCE=158.683-224.770 ms aggregate
SOURCE_OR_AST_DEPENDENT=NO
RECOMPUTES_ALREADY_AVAILABLE_STATE=PARTIAL
DUPLICATED_WITH_OTHER_STAGE=PARTIAL + each layer has a distinct scope
CAN_REUSE_CURRENT_INDEX_CACHE_RAM_FACTS=YES
SEMANTIC_SCOPE_SAME_AS_POTENTIAL_SOURCE=NO for global/canonical reuse
LIKELY_REMOVABLE_WHOLE_ANALYSIS_MS=0-0
SEMANTIC_RISK=MEDIUM + layer-specific report scope

## Index-repository inspection

index_repository resolves the root, walks current Python files, applies excludes/ignored directories, and submits one _process_single_file task per selected file through the normal ProcessPool path. The worker result carries module/path/import data plus symbol, reference, collision, and test facts.

The warm stage is wall median 1793.122 ms and parent CPU median 734.375 ms. The difference is consistent with worker execution. The source proves per-file fingerprint/cache validation and current facts must remain authoritative. No evidence proves that removing path resolution, JSON decoding, schema validation, or worker setup would preserve freshness and failure behavior.

Later reference-index assembly consumes worker compact reference facts; it is not a second AST traversal on the normal warm path. Later artifact assembly reuses symbol/reference facts but performs distinct consumer classification needed for report content. No safe indexer elimination was established.

## Candidate ranking

### 1. Canonical shared-usage cluster raw-result handoff

CURRENT_EVIDENCE=The same pure-RAM complete-linkage authority runs for global, two layer scopes, and canonical persistence. The canonical call is 317.092 ms inclusive. Existing parity tests prove snapshot/canonical equality. The public global result is compacted, so direct public-field reuse is invalid.

OWNER=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\graph_analytics.py::generate_graph_analytics_report, with consumption in C:\Temp\Contextor_Repo\contextor\core\api\facade.py::ContextorFacade.analyze_project.

REMOVABLE_WORK=The second canonical projection plus Jaccard traversal for already validated global current-run facts; retain layer calls and canonical coverage validation.

SAFE_OPTIMIZATION_SHAPE=Capture the pre-_compact_clusters raw global list in an internal in-memory side-channel owned by the artifact pipeline. After canonical artifact-consumption coverage is validated, use that raw list for canonical state. Keep the compact public graph report unchanged. If the side-channel is absent, parameters/scope differ, or coverage validation fails, retain the existing canonical computation.

EXPECTED_WHOLE_ANALYSIS_SAVING_MS=280-320
SEMANTIC_RISK=MEDIUM + full IDs and compact IDs must remain separate
REQUIRED_INVARIANTS=exact existing parity; identical cluster parameters; no reuse on incomplete/stale consumption; unchanged public schema/compact IDs; unchanged canonical full-name payload; no source/AST reads; existing fallback retained

### 2. TestContextIndex.find_test_files reverse lookup

CURRENT_EVIDENCE=320 calls scan the same files_info imported-module sets. Aggregate exclusive median is 217.302 ms with no nested work. The predicate is exact equality or dotted-prefix matching, followed by filename candidates, set de-duplication, and sorting.

OWNER=C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py::TestContextIndex

REMOVABLE_WORK=Repeated O(number of test files) scans for every analyzed module.

SAFE_OPTIMIZATION_SHAPE=Build a run-scoped reverse lookup from each imported module and its dotted prefixes while constructing files_info. Preserve filename lookup, exact/prefix semantics, dedupe, sorted output, and the compatibility wrapper.

EXPECTED_WHOLE_ANALYSIS_SAVING_MS=150-205
SEMANTIC_RISK=LOW + deterministic in-memory lookup with focused parity tests
REQUIRED_INVARIANTS=all current files_info entries; exact matches; dotted child matches; unrelated prefixes excluded; sorted unique paths; standalone wrapper unchanged

### 3. discover_test_dirs candidate-map fusion

CURRENT_EVIDENCE=One warm call is 179.159 ms and resolves/filters the already allowed Python path set from RepositoryIndex.modules. It is repository-level candidate classification, not AST parsing.

OWNER=C:\Temp\Contextor_Repo\contextor\core\analysis\test_context.py::discover_test_dirs, with possible RepositoryIndex result plumbing.

REMOVABLE_WORK=Repeated normalization and candidate filtering over a path domain already held by the indexer result.

SAFE_OPTIMIZATION_SHAPE=Produce an exact candidate directory/file-name map at the existing indexer/result boundary and consume it from artifact reporting. Keep one automatic-discovery predicate; do not apply it to caller-supplied authoritative test_dirs.

EXPECTED_WHOLE_ANALYSIS_SAVING_MS=120-175
SEMANTIC_RISK=MEDIUM + exclusions, root naming, nested behavior, and explicit test_dirs compatibility
REQUIRED_INVARIANTS=same allowed path domain; root test_<name> and <name>_test.py rules; tests/test rules; nested exclusions; conftest handling; absolute/relative normalization; explicit test_dirs authoritative

## Non-candidates

collect_module_artifacts is large but derives own symbols, reference projections, consumer channels, failures, and module-artifact payloads. No complete equivalent prebuilt projection was proven.

assemble_reference_index_or_fallback is a one-time current-facts assembly and is explicitly shared by artifact workers. A new persisted derived-index contract would expand freshness semantics.

save_engine_state and FileStateManager.update_state are required persistence/freshness work. Skipping or relocating writes is not elimination.

The two layer Jaccard calls are scope-specific. PageRank, hubs/authorities, betweenness, topology, matrices, compaction, registry synchronization, and report serialization are required or scope-specific. Their local cost alone is not evidence for safe elimination.

No parallelism or micro-optimization is recommended.

## Acceptance gate for the next implementation

- Public reports, compact reports, canonical state, and API results remain equivalent except for an internal non-persisted handoff.
- Raw global clusters before compaction equal the existing canonical-state clusters.
- Layer graph analytics retains its original scope and count.
- Incomplete/stale artifact-consumption coverage retains the existing fallback and cannot mark partial data fresh.
- The canonical duplicate Jaccard computation count decreases by one; global/layer counts do not change.
- Six or more clean warm observations show a material whole-analysis reduction near 280-320 ms, with all raw observations retained.
- No source/AST traversal, freshness validation, report field, persistence write, LIVE behavior, or canonical authority is weakened.

## Commands and results

Read task:
Get-Content -LiteralPath C:\Temp\Contextor_Repo\task.txt -TotalCount 80
Result: task.txt contains the earlier 0J4 test-context design task; the latest pasted user task was followed as the current instruction.

Contextor MCP tools used:
get_symbol_implementation, get_symbol_call_context, get_source_range, get_module_context, get_project_architecture.
All decision-critical responses used revision 68, canonical_state=fresh, workspace_sync=verified, provenance=live.

Benchmark command:
& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' 'C:\Temp\Contextor_Benchmarks\post0J4_warm_cost_remap.py'
Result: warm_total_median_ms=6559.137299511349

No production/test pytest, py_compile, or mutation command was run because this task was discovery/measurement only.

## Files and diffs

The current working tree contains pre-existing 0J4 production/test and runtime-log changes from the accepted prior task. This turn did not edit a production or test file. The external harness is outside the repository.

FILES_CHANGED=NONE
DIFFS=NONE

walkthrough.md is the required report artifact and is excluded from task-file accounting. No production/test unified diff exists for this discovery-only turn.

CURRENT_WHOLE_ANALYSIS_MEDIAN_MS=6559.137299511349
NEXT_TARGET=ContextorFacade.analyze_project
EXPECTED_WHOLE_ANALYSIS_SAVING_MS=280-320
SECOND_CANDIDATE=TestContextIndex.find_test_files
THIRD_CANDIDATE=discover_test_dirs
FILES_CHANGED=NONE
DIFFS=NONE
WHY=The global graph report already computes raw full-name Jaccard clusters from the same validated current-run facts later projected and recomputed for canonical state; preserving that raw result before public ID compaction can remove the measured 317 ms canonical duplicate while leaving layer scopes, report schemas, freshness gates, and fallback behavior unchanged.
