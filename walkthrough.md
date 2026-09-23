# CPA10L3_CANONICAL_STATE_CLONE_COST_DISCOVERY

## STATUS

STATUS=DISCOVERY_COMPLETE

Discovery-only checkpoint. The current clone path, actual LIVE state type, all declared and observed dynamic state fields, incremental mutation writers, inner COW boundaries, transaction ordering, test contracts, and directly available cardinalities were inspected. Unknown shapes and unavailable counts are explicitly labeled.

Evidence classes used:
- DIRECT_EVIDENCE: Contextor symbol/call-context/lineage and bounded canonical projections; current LIVE revision/freshness; snapshot metadata and static pickle opcode inspection; source/test implementations.
- CODE_PATH_PROVED: clone → updater → persistence → canonical commit; engine constructor/materialization → inner COW ordering.
- CONTRACT_PROVED: listed test assertions, type declarations, and copy-returning helper implementations.
- INFERENCE: not used to fill missing cardinalities or claim timing.
- UNKNOWN: nested shapes and counts not directly exposed.

## CURRENT_CLONE_PATH

| Required item | Result |
|---|---|
| CLONE_CALLER | C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py::CanonicalLiveServer._execute_update_file |
| CLONE_HELPER | C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py::_clone_state_for_update |
| CURRENT_STATE_TYPE | C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py::RepositoryAnalysisState |
| CUSTOM_CLONE_METHOD_EXISTS | NO |
| DEEPCOPY_FALLBACK_ACTIVE | YES |

CanonicalLiveServer._execute_update_file captures the prior canonical state/revision under the server lock and calls _clone_state_for_update(previous_state) before invoking the updater. The helper invokes a callable clone_for_update when present; otherwise it calls copy.deepcopy(state), then rejects an identity-equal candidate. RepositoryAnalysisState has no clone_for_update method. Contextor source search found only the helper's getattr use.

The actual LIVE type was checked against the active Contextor state, not inferred from source alone. LIVE revision 1361 and repo id ctx_8efc50d8 matched engine_state.meta.json at C:\Users\DafoO\AppData\Local\Contextor\cache\repositories\ctx_8efc50d8\engine_state.meta.json. Metadata identifies state id 20260923_200134 and snapshot engine_state.r1361.5589a5b15a234ea2988cf4bc58c2962a.pkl. Static pickletools inspection identified pickle global contextor.core.analysis.state_manager::RepositoryAnalysisState; the snapshot was not unpickled for this check. The runtime load_snapshot → run_service → CanonicalLiveServer path forwards the loaded object directly; _repository_updater forwards that object to IncrementalAnalysisEngine.

The bounded LIVE view was revision 1361, provenance live, with inspected code families fresh and workspace_sync=verified. The event query after revision 1361 returned no newer events, continuous history, and no resync request. No out-of-sync conclusion is drawn.

## STATE_FIELD_INVENTORY

RepositoryAnalysisState declares 35 fields. The table distinguishes existing inner CandidateState COW from the outer LIVE clone. Today, outer deepcopy isolates every field before the updater runs. SAFE_TO_SHARE_WITH_PREVIOUS_CANONICAL_STATE describes whether the traced incremental path proves a reference/value could remain shared if an outer clone did so; it does not claim that current deepcopy shares fields.

Path keys:
- STATE = C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py
- ENGINE = C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py
- PLAN = C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- MATERIALIZATION = C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\materialization.py
- IPC = C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py
- RUNTIME = C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py

| FIELD_NAME | RUNTIME_TYPE_SHAPE | TOP_LEVEL_MUTATED_DURING_INCREMENTAL | NESTED_CONTENT_MUTATED_DURING_INCREMENTAL | MUTATION_OWNER_PATH::SYMBOL | CURRENT_EXISTING_COW | SAFE_TO_SHARE_WITH_PREVIOUS_CANONICAL_STATE |
|---|---|---|---|---|---|---|
| modules | Dict[str, Any] | YES | No old Module nested write found; Module.imports is mutable | PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | YES, shallow map copy; changed Module replaced | UNKNOWN, Any values and shallow-frozen Module |
| artifacts | Dict[str, Any] | YES | UNKNOWN for arbitrary artifact values; candidate entries replaced | PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | YES, shallow map copy | UNKNOWN |
| dependency_graph | Optional[Any], current ProjectGraph | YES, replaced on graph changes | No old graph mutation found; internals are mutable dict/set | PLAN::execute_refresh_plan; ProjectGraph.with_module_edges; ProjectGraph.without_module | Functional replacement; otherwise carried by reference | UNKNOWN as a general contract |
| artifact_consumption | Dict[target, entry] | YES | YES, affected consumers/channels are copied before edits | PLAN::_prepare_candidate_state; PLAN::_get_copy_of_entry; PLAN::_remove_consumer_slice; PLAN::_rebuild_consumer_slice | YES, map copy plus entry-level COW | PROVEN_YES for traced consumer/channel update paths |
| artifact_consumption_state | str | YES, scalar assignment | NO | MATERIALIZATION::ensure_artifact_consumption; ENGINE::update_file; PLAN::execute_refresh_plan | Candidate scalar; outer clone isolates holder | PROVEN_YES for scalar value |
| layer_information | Dict[str, Any] | NO writer found in traced path | NO writer found in traced path | No incremental writer found | NO CandidateState field | PROVEN_YES for traced path only |
| metrics | Dict[str, Any] | YES, computed value replaced | No old metrics mutation found | PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | Shared until computed replacement | PROVEN_YES for traced replacement path |
| file_state | Dict[str, FileState] | NO on RepositoryAnalysisState in traced path | NO on this field; separate FileStateManager map changes | ENGINE::update_file; RUNTIME::_repository_updater; FileStateManager::update_state | NO CandidateState field | UNKNOWN, mutable values and separate owner boundary |
| module_parse_freshness | Dict[str, Dict[str, Any]] | YES, set/pop | Existing path dict replaced, not edited in place by traced helpers | STATE::mark_module_parse_failure; STATE::clear_module_parse_failure; ENGINE::_commit_syntax_candidate; PLAN::_prepare_candidate_state | YES, top map copy; path values replaced | PROVEN_YES for unchanged path values in traced update |
| syntax_diagnostics_by_path | Dict[str, Dict[str, Any]] | YES, set/pop | UNKNOWN for nested payload shape; traced path replaces entries | ENGINE::_commit_syntax_candidate; ENGINE::_apply_delta_and_commit; PLAN::_prepare_candidate_state | YES, top map copy | UNKNOWN |
| syntax_diagnostics_state | str | YES, scalar assignment | NO | ENGINE::_commit_syntax_candidate; ENGINE::_apply_delta_and_commit; PLAN::execute_refresh_plan | Candidate scalar | PROVEN_YES for scalar value |
| module_usages | Dict[path, ModuleUsageFacts or mapping] | YES, including pre-plan in-place insertion for missing modules | Existing ModuleUsageFacts are frozen tuples; missing path gets empty mapping | MATERIALIZATION::ensure_module_usages; PLAN::_prepare_candidate_state; PLAN::execute_refresh_plan | YES, map copied inside CandidateState after constructor materialization | PROVEN_MUST_ISOLATE outer mapping before engine construction; unchanged ModuleUsageFacts values PROVEN_YES |
| module_usages_manifest | Dict[path, Dict[str, str]] | NO writer found in traced path | NO writer found in traced path | No incremental writer found | NO CandidateState field | UNKNOWN, nested mutable dict shape |
| lineage_facts_by_source | Dict[source, MaterializedLineageSourceFacts] | YES, per-source set/pop | Values frozen; source slice replaced | ENGINE::_update_candidate_lineage_slice; PLAN::_prepare_candidate_state | YES, map copy and per-source replacement | PROVEN_YES for unchanged immutable source records |
| lineage_facts_state | str | YES, scalar assignment | NO | ENGINE::_commit_syntax_candidate; ENGINE::_apply_delta_and_commit; PLAN::execute_refresh_plan | Candidate scalar | PROVEN_YES for scalar value |
| lineage_facts_semantic_version | Optional[str] | YES, scalar assignment | NO | ENGINE::_commit_syntax_candidate; ENGINE::_apply_delta_and_commit | Candidate scalar | PROVEN_YES for scalar value |
| lineage_owner_source_index | Dict[key, tuple[source,...]] | YES, index map replacement | Tuple values immutable | ENGINE::_update_candidate_lineage_slice; PLAN::_prepare_candidate_state | YES, copied/patched map | PROVEN_YES for tuple values and unchanged keys |
| lineage_source_owner_index | Dict[source, tuple[owner,...]] | YES, index map replacement | Tuple values immutable | ENGINE::_update_candidate_lineage_slice; PLAN::_prepare_candidate_state | YES, copied/patched map | PROVEN_YES for tuple values and unchanged keys |
| lineage_query_index_state | str | YES, scalar assignment | NO | ENGINE::_update_candidate_lineage_slice; ENGINE::_apply_delta_and_commit | Candidate scalar | PROVEN_YES for scalar value |
| lineage_semantic_anchor_bindings_complete | bool | YES, scalar assignment | NO | ENGINE::_update_candidate_lineage_slice; ENGINE::_apply_delta_and_commit | Candidate scalar | PROVEN_YES for scalar value |
| topology_analytics | Dict[str, Any] | YES, computed value replaced | No old result mutation found; nested analytics are mutable | MATERIALIZATION::ensure_topology_analytics; PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | YES, map copy; recomputed/replaced | UNKNOWN, nested result shape |
| topology_metrics_state | str | YES, scalar assignment | NO | MATERIALIZATION::ensure_topology_analytics; PLAN::execute_refresh_plan | Candidate scalar | PROVEN_YES for scalar value |
| cached_analytics | Dict[str, Any] | YES, computed value replaced | No old result mutation found | MATERIALIZATION::ensure_cached_analytics; PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | YES, map copy; recomputed/replaced | UNKNOWN, nested result shape |
| cached_analytics_state | str | YES, scalar assignment | NO | MATERIALIZATION::ensure_cached_analytics; PLAN::execute_refresh_plan | Candidate scalar | PROVEN_YES for scalar value |
| cycles | list | YES, list replaced | No old item mutation found; item shape not uniformly immutable | MATERIALIZATION::ensure_cycles; PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | YES, list copy; recomputed/replaced | UNKNOWN |
| cycles_state | str | YES, scalar assignment | NO | MATERIALIZATION::ensure_cycles; PLAN::execute_refresh_plan | Candidate scalar | PROVEN_YES for scalar value |
| collision_facts | Dict[key, list[dict]] | YES, set/pop | Candidate facts replaced; resolver copies records before resolution edits | MATERIALIZATION::ensure_collisions; PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state; validator/collisions.py::resolve_collision_candidate_codes | YES, shallow map copy and per-key replacement | UNKNOWN, nested lists/dicts mutable |
| collisions | list | YES, list replaced | Existing records not edited in traced computation; ValidationError is mutable | MATERIALIZATION::ensure_collisions; PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | YES, list copy; recomputed/replaced | UNKNOWN |
| collisions_state | str | YES, scalar assignment | NO | MATERIALIZATION::ensure_collisions; PLAN::execute_refresh_plan | Candidate scalar | PROVEN_YES for scalar value |
| dependency_matrix | Dict[str, Any] | YES, computed value replaced | No old matrix mutation found; nested shape broad | PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | YES, map copy; recomputed/replaced | UNKNOWN |
| dependency_matrix_state | str | YES, scalar assignment | NO | PLAN::execute_refresh_plan | Candidate scalar | PROVEN_YES for scalar value |
| shared_usage_clusters | list | YES, list replaced | No old item mutation found; nested shape broad | PLAN::execute_refresh_plan; PLAN::_prepare_candidate_state | YES, list copy; recomputed/replaced | UNKNOWN |
| shared_usage_clusters_state | str | YES, scalar assignment | NO | PLAN::execute_refresh_plan | Candidate scalar | PROVEN_YES for scalar value |
| trie | Optional[Any], current TrieNode | YES, replaced on graph-changing paths | Existing mutable nodes read; no old node edits found | PLAN::execute_refresh_plan; resolver::build_trie | Reference carried when unchanged; rebuilt for add/delete | UNKNOWN, mutable node tree |
| package_root | str | YES, scalar replacement on graph change | NO | PLAN::execute_refresh_plan | Shared scalar until replacement | PROVEN_YES for scalar value |
| revision (dynamic) | int | YES, scalar assignment | NO | IPC::_execute_update_file; IPC::_bind_state_revision; live store::save_snapshot | Not in CandidateState; outer clone isolates holder | PROVEN_YES for scalar value |
| provenance (dynamic) | str | YES, scalar assignment when marking/publishing LIVE state | NO | IPC::_mark_live_state_provenance; runtime full-analysis publication path | Not in CandidateState | PROVEN_YES for scalar value |
| state_id (dynamic) | str | YES, scalar assignment during snapshot generation | NO | live store::save_snapshot | Not in CandidateState | PROVEN_YES for scalar value |
| resync_required (dynamic) | bool | YES, may be retained/set on candidate; read before plan | NO | ENGINE::update_file; ENGINE::_apply_delta_and_commit | Not in CandidateState | PROVEN_YES for scalar value |

## INCREMENTAL_MUTATION_WRITERS

Mutation labels: A = top-level field replacement; B = top-level dict/list mutation; C = nested object mutation; D = immutable object replacement only.

| State family | Writer/path and observed operation |
|---|---|
| modules | B: PLAN::_prepare_candidate_state and PLAN::execute_refresh_plan pop/replace candidate map entries. D: changed Module newly constructed. |
| artifacts | B: PLAN::_prepare_candidate_state and PLAN::execute_refresh_plan pop/replace candidate entries. Arbitrary retained values remain UNKNOWN. |
| module_parse_freshness | B: STATE::mark_module_parse_failure / clear_module_parse_failure and engine syntax path set/pop path entries; path payload is assigned as a new mapping. |
| syntax_diagnostics_by_path | B: ENGINE::_commit_syntax_candidate and ENGINE::_apply_delta_and_commit pop/set candidate paths; nested payload shape UNKNOWN. |
| module_usages | B before inner COW: MATERIALIZATION::ensure_module_usages inserts an empty mapping for missing modules. B after inner COW: PLAN updates candidate entries. |
| module_usages_manifest | No writer found in traced update_file → constructor/materialization → plan path. Nested shape remains mutable/unknown for sharing. |
| lineage_facts_by_source | B: ENGINE::_update_candidate_lineage_slice replaces/removes source entries. Values are immutable materialized slices. |
| lineage_owner_source_index / lineage_source_owner_index | A/B: ENGINE::_update_candidate_lineage_slice uses patch/rebuild returning new maps and tuple values. |
| artifact_consumption | B: PLAN consumer removal/rebuild updates candidate target map. C: affected consumers and channel lists are copied by PLAN::_get_copy_of_entry before edits. |
| dependency_graph | A/D: PLAN builds a new graph through ProjectGraph.with_module_edges/without_module; no old graph mutation found. |
| metrics | A: computed metrics object replaced; no old nested mutation found. |
| topology_analytics | A: MATERIALIZATION/PLAN assigns fresh analytics; no old result mutation found. |
| dependency_matrix | A: PLAN computes and assigns result; nested shape is not fully immutable. |
| shared_usage_clusters | A: PLAN computes and assigns result. |
| cached_analytics | A: MATERIALIZATION/PLAN assigns computed result; traced atomicity test covers failure behavior. |
| cycles | A: MATERIALIZATION/PLAN assigns computed list; no old item mutation found. |
| collision_facts | B: PLAN candidate map set/pop; collision resolver copies affected records before resolution edits. |
| collisions | A: collision computation creates/replaces candidate list and records. ValidationError values are mutable. |
| file_state | No mutation of RepositoryAnalysisState.file_state found in plan. ENGINE::update_file calls FileStateManager::update_state on a separate manager-owned map. |
| trie | A/D: PLAN uses a newly built trie when graph membership changes; unchanged trie is read, not modified, in traced path. |
| package_root | A: scalar replacement on graph-changing plan. |
| freshness/state flags | A: scalar assignments in MATERIALIZATION, ENGINE syntax/apply, and PLAN family computations. |
| revision/provenance/resync | A: dynamic scalar assignments/read-retention on detached candidate and server snapshot/commit path. |

IncrementalAnalysisEngine.__init__ stores its input as self.state and calls materialize_incremental_state(self.state) before update_file reaches execute_refresh_plan and CandidateState. ensure_module_usages mutates state.module_usages in place for missing paths. The current outer LIVE deepcopy prevents this write from reaching the prior canonical state.

FileStateManager.update_state(file_path) changes the manager's own _state, not RepositoryAnalysisState.file_state. Runtime constructs and passes that manager separately.

## EXISTING_COW_BOUNDARIES

| Required item | Result |
|---|---|
| PLAN_EXECUTOR_TOP_LEVEL_COPIES | modules, artifacts, module_parse_freshness, syntax_diagnostics_by_path, module_usages, lineage_facts_by_source, lineage_owner_source_index, lineage_source_owner_index, artifact_consumption, topology_analytics, dependency_matrix, cached_analytics, collision_facts, shared_usage_clusters, cycles, collisions |
| PLAN_EXECUTOR_SHARED_OBJECTS | dependency_graph, trie, package_root, metrics; unchanged values inside copied collections can also remain shared |
| PLAN_EXECUTOR_ENTRY_LEVEL_COW | artifact_consumption entries: consumers and each channels list copied via PLAN::_get_copy_of_entry; lineage source facts replaced per source; lineage index maps copied/patched with tuple values |
| ENGINE_PRE_PLAN_MUTATIONS | materialize_incremental_state in IncrementalAnalysisEngine.__init__, including ensure_module_usages top-map insertions and family/state normalization/replacements; ENGINE::update_file may set artifact_consumption_state=stale when resync_required is already true |
| ENGINE_POST_PLAN_MUTATIONS | After plan/registry/lineage checks, ENGINE::_apply_delta_and_commit publishes CandidateState fields onto updater-owned self.state; FileStateManager::update_state then changes its separate manager state. IPC binds revision, persists, then commits canonical object. |

Evidence for ordering: PLAN::_prepare_candidate_state is called by execute_refresh_plan and CandidateState creation precedes plan mutations. Engine construction/materialization occurs earlier: ENGINE::__init__ → MATERIALIZATION::materialize_incremental_state → ensure_*; only afterward update_file → execute_refresh_plan. Therefore inner top-level copies do not protect pre-plan module_usages insertion.

Additional boundaries:
- PLAN::_get_copy_of_entry copies the target entry, consumers list, and each channels list before nested edits.
- PLAN::_remove_consumer_slice and PLAN::_rebuild_consumer_slice update through copied/replaced entries.
- resolve_collision_candidate_codes returns copied records when it resolves codes; with no candidate mutation it returns input unchanged.
- ProjectGraph.with_module_edges and without_module return new graph objects and copy edge maps/sets.
- mark_module_parse_failure and clear_module_parse_failure update the candidate mapping using new per-path values.
- patch_lineage_query_indexes copies maps and returns new tuple-valued indexes.

## OBJECT_IMMUTABILITY_CONTRACTS

| TYPE | IMMUTABLE_BY_CONTRACT | MUTATING_METHODS_USED_BY_INCREMENTAL | SAFE_REFERENCE_SHARING |
|---|---|---|---|
| ProjectGraph | NO for deep contents: frozen dataclass, but hard_edges/soft_edges contain mutable dicts/sets | NO; incremental uses with_module_edges/without_module returning new graphs | UNKNOWN globally; traced path does not mutate old graph |
| Module | NO for deep contents: frozen dataclass, imports is mutable list | NO old Module/imports mutation found; changed Module is newly built | UNKNOWN due nested imports |
| ModuleUsageFacts | YES: frozen dataclass with tuple-shaped fact collections and immutable fact values | NO; values read/replaced | PROVEN_YES for unchanged values in traced update |
| MaterializedLineageSourceFacts | YES: frozen dataclass with tuple facts and post-init invariants | NO; source slice replaced | PROVEN_YES for unchanged source slices in traced update |
| CollisionFact / ValidationError | NO blanket immutable contract: collision facts have dict/list shapes; ValidationError is mutable dataclass with list/dict members; CollisionFact is custom source-backed record | Resolver copies records before resolution edits; no old canonical collision record mutation found | UNKNOWN |
| TrieNode | NO: ordinary mutable slotted node with mutable children dict | NO old trie mutation found; rebuilt for membership changes | UNKNOWN as a general shared object |
| Metrics result | NO: ordinary dict | NO old result mutation found; recomputed/replaced | PROVEN_YES for traced replacement path only |
| Topology analytics | NO: ordinary nested dict/list result | NO old result mutation found; recomputed/replaced | UNKNOWN due nested result shape |
| FileState | NO: mutable dataclass of scalar fields | State field not mutated by traced updater; separate FileStateManager map updated | UNKNOWN due mutable values and separate ownership boundary |

## EXISTING_CLONE_SNAPSHOT_MECHANISMS

CUSTOM_CLONE_METHOD_EXISTS=NO
DEEPCOPY_FALLBACK_ACTIVE=YES
EXISTING_SELECTIVE_CLONE_CONTRACT=YES

YES means an execution-local selective COW mechanism exists; it is not a whole-RepositoryAnalysisState clone method or an IPC clone_for_update contract.

Exact mechanisms and semantics:
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py::CandidateState — mutable candidate container with copied top-level collections and selected shared references.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py::_prepare_candidate_state — makes the top-level mapping/list copies listed above and carries selected fields by reference.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py::_get_copy_of_entry — copies artifact-consumption entry, consumers list, and channel lists before nested edits.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py::_remove_consumer_slice and ::_rebuild_consumer_slice — update consumer slices through copied/replaced entries.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py::_update_candidate_lineage_slice and C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\lineage_indexes.py::patch_lineage_query_indexes — replace one source slice and produce copied index maps.
- C:\Temp\Contextor_Repo\contextor\core\domain\graph.py::ProjectGraph.with_module_edges and ::without_module — functional graph replacement.
- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py::_clone_state_for_update — only outer clone dispatch; callable clone_for_update or deepcopy fallback.

Contextor discovery followed by exact text search found no clone_for_update definition, no copy_for_update hits, and no relevant whole-state dataclasses.replace or copy.copy mechanism. save_snapshot/load_snapshot persist and hydrate pickle generations; they are not selective cloning. Other deepcopy uses for event/response shaping are unrelated to canonical state cloning.

## TRANSACTION_FAILURE_BOUNDARY

| Failure point | Observed order/effect |
|---|---|
| A. updater raises | Updater receives only detached candidate. _execute_update_file records failure and exits before persistence/canonical commit. Prior canonical object and revision remain. |
| B. execute_refresh_plan raises | Engine traces and rethrows before candidate publication. Registry/lineage failures occur before assignments. Constructor/pre-plan mutations affect only outer deepcopy candidate. |
| C. persistence raises | Persister runs before canonical commit. Exception returns error without assigning self._state or advancing canonical revision. In-memory canonical state remains unchanged. Disk is not proven unchanged for every partial/post-write failure. |
| D. canonical commit fails | Under lock, captured revision and object identity are checked. Mismatch returns canonical_revision_changed_during_update before this request assigns candidate or publishes its event. Persistence already ran, so disk/current parity is not guaranteed. |
| E. diagnostic delta calculation raises | Runs after canonical state/revision commit. Exception is swallowed, delta becomes empty, and update remains committed; this is not rollback. |

CANONICAL_STATE_REMAINS_UNCHANGED_ON_UPDATER_FAILURE=PROVEN_YES
CANONICAL_STATE_REMAINS_UNCHANGED_ON_PERSIST_FAILURE=PROVEN_YES

“Unchanged” means in-memory canonical state object/revision. Persistence failure does not prove that disk has no side effect after every possible partial/post-write exception.

Isolation specifically dependent on the current full deepcopy:
1. Candidate-side state field writes before inner COW.
2. materialize_incremental_state mutating module_usages before CandidateState creation.
3. update_file applying the pre-plan resync-required status write.
4. Nested mutable objects not covered by CandidateState shallow top-level copies.
5. Updater exceptions before inner COW publication.

## EXISTING_TEST_CONTRACTS

Tests inspected; no tests run.

| ABSOLUTE WINDOWS PATH | TEST NAME | INVARIANT |
|---|---|---|
| C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py | test_update_clone_failure_uses_update_fail_not_publish_fail | Clone failure emits update failure, not publish failure, and returns controlled error. |
| C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py | test_persister_runs_after_validation_before_canonical_exposure | Persister observes prior canonical state/revision; candidate appears only after successful persistence. |
| C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py | test_persistence_conflict_fails_closed_without_live_event | Conflict retains identical prior state object/revision/activity sequence and publishes no event. |
| C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py | test_updater_failure_does_not_kill_the_service | Updater error is returned and service stays alive; test does not assert old-state identity. |
| C:\Temp\Contextor_Repo\tests\test_cached_facts_live_analytics.py | test_atomicity_and_isolation_on_failure | Cached analytics failure leaves cached analytics and same engine.state object untouched. |
| C:\Temp\Contextor_Repo\tests\test_channel_parity_and_cow.py | test_cow_immutability_non_empty_old_state | Prior artifact-consumption entries, consumers, and channels remain unchanged through update. |
| C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py | test_natural_dotted_identity_ambiguity_transition_lifecycle | Ambiguity transition removes affected consumer slice; unrelated entry and old snapshot remain unchanged. |
| C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py | test_cow_atomicity_on_provider_add | Prior artifact-consumption/modules references remain unchanged on provider addition. |
| C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py | test_cow_atomicity_across_families | Retained module/artifact/usage/consumption references remain unchanged across consumer update. |
| C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py | test_fail_closed_on_unsupported_plan_item | Unsupported plan item raises before publication; inspected assertion does not prove every nested identity. |
| C:\Temp\Contextor_Repo\tests\test_collisions_live_lifecycle.py | test_missing_payload_transaction_failure | Missing planned collision facts fail transaction without replacing prior canonical collision state/facts. |
| C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py | test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_state | Revalidation failure preserves canonical modules/artifacts/lineage and registry mappings; no FileState acknowledgement. |
| C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py | test_incremental_lineage_modify_replaces_only_changed_candidate_slice | Modification replaces only changed lineage source slice. |
| C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py | test_incremental_lineage_delete_removes_only_deleted_slice | Deletion removes only deleted lineage source slice. |

get_file_edit_context supplied bounded static test reachability evidence (engine 94, plan 96, IPC 58 tests covering); these are not exact direct caller/test counts. get_artifact_blast_radius was queried for relevant writers; artifact-consumer output is not treated as a call graph.

## STATE_CARDINALITIES

Current directly available values are from LIVE canonical projections at revision 1361; graph/module counts also agree with the architecture LIVE overlay. No values are extrapolated from timing.

| CARDINALITY | VALUE | EVIDENCE / LIMIT |
|---|---:|---|
| MODULE_COUNT | 413 | Bounded canonical projection modules total_matches=413; architecture overlay agrees. |
| ARTIFACT_MODULE_COUNT | UNKNOWN | Not directly exposed by queried projection. |
| ARTIFACT_TARGET_COUNT | 5383 | Bounded canonical projection artifacts total_matches=5383. |
| ARTIFACT_CONSUMPTION_TARGET_COUNT | UNKNOWN | Not directly exposed. |
| MODULE_USAGE_COUNT | UNKNOWN | Not directly exposed. |
| LINEAGE_FACT_COUNT | UNKNOWN | Not directly exposed. |
| GRAPH_NODE_COUNT | 413 | Current graph/canonical module projection; overlay agrees. |
| GRAPH_EDGE_COUNT | 1542 | Bounded dependency projection and LIVE architecture overlay. |
| DEPENDENCY_MATRIX_SIZE | UNKNOWN | Not directly exposed. |
| CLUSTER_COUNT | UNKNOWN | Not directly exposed. |
| COLLISION_COUNT | 0 | Current diagnostics summary at revision 1361 reports zero collisions. |
| FILE_STATE_COUNT | UNKNOWN | Not directly exposed. |

CLONE_BASELINE_PRIMARY_MS=28036
CLONE_BASELINE_SECONDARY_MS=29714

The durations are user-provided CPA10L2A comparable-run facts. No benchmark was run for this checkpoint.

## PROVEN_SAFE_TO_SHARE

PROVEN_SAFE_TO_SHARE_FIELDS=artifact_consumption_state; syntax_diagnostics_state; lineage_facts_state; lineage_facts_semantic_version; lineage_query_index_state; lineage_semantic_anchor_bindings_complete; topology_metrics_state; cached_analytics_state; cycles_state; collisions_state; dependency_matrix_state; shared_usage_clusters_state; package_root; revision; provenance; state_id; resync_required; unchanged ModuleUsageFacts values; unchanged MaterializedLineageSourceFacts values; lineage index tuple values

Scope: scalar values and listed immutable values are safe to share along the traced update path. The containing RepositoryAnalysisState object is not shareable because revision/provenance/state metadata and flags are assigned on the candidate.

## PROVEN_MUST_ISOLATE

PROVEN_MUST_ISOLATE_FIELDS=RepositoryAnalysisState outer object; module_usages outer mapping before IncrementalAnalysisEngine construction

Evidence for module_usages is the in-place insertion in ensure_module_usages, called during constructor materialization before _prepare_candidate_state copies the map. The outer state object must be distinct because update/persistence binds revision/state metadata and candidate field assignments.

## UNKNOWNS

UNKNOWN_SHARING_FIELDS=artifacts nested values; dependency_graph nested dict/set contents as a general contract; file_state values; module_usages_manifest nested dicts; syntax diagnostic payloads; topology_analytics nested values; cached_analytics nested values; cycles members; collision_facts nested lists/dicts; collisions records; dependency_matrix nested values; shared_usage_clusters members; trie nodes; arbitrary modules/artifacts values

- revision, provenance, state_id, and resync_required are dynamic attributes, not declared RepositoryAnalysisState fields.
- Counts for artifact module count, consumption targets, usages, lineage facts, matrix size, clusters, and file-state entries were not exposed; they remain UNKNOWN.
- Nested shapes for broad Any, collision, cycle, matrix, and cluster values are not uniformly immutable.
- Existing tests prove several COW/transaction invariants. test_updater_failure_does_not_kill_the_service does not directly assert old-state identity; IPC control flow proves the in-memory boundary.
- Persistence failure preserves in-memory canonical state, but absence of every possible post-write disk side effect is not proven.

## FILES_AND_SYMBOLS_FOR_NEXT_IMPLEMENTATION

Discovery anchors only. No implementation or clone design is included.

- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py::CanonicalLiveServer._execute_update_file — canonical transaction boundary and clone caller.
- C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py::_clone_state_for_update — current outer clone dispatch/fallback.
- C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py::RepositoryAnalysisState — canonical state declaration.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py::IncrementalAnalysisEngine.__init__ — materialization-before-plan ordering.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\materialization.py::materialize_incremental_state and ::ensure_module_usages — pre-inner-COW writer.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py::update_file, ::_commit_syntax_candidate, ::_update_candidate_lineage_slice, and ::_apply_delta_and_commit — engine mutation/publication sequence.
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py::CandidateState, ::_prepare_candidate_state, ::_get_copy_of_entry, ::_remove_consumer_slice, ::_rebuild_consumer_slice, and ::execute_refresh_plan — inner COW and plan writers.
- C:\Temp\Contextor_Repo\contextor\core\domain\graph.py::ProjectGraph.with_module_edges and ::without_module — functional graph update boundary.
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py::_repository_updater and ::run_service; live store::save_snapshot/load_snapshot — runtime type forwarding and persistence order.

## CHECKPOINT_RESULT

PROFILE_RUN_COUNT=0
CODE_CHANGED=NO
TEST_CODE_CHANGED=NO
TESTS_RUN=NO
FULL_ANALYSIS_RUN=NO
FIX_DESIGNED=NO
IMPLEMENTATION_ATTEMPTED=NO
FILES_CHANGED=walkthrough.md (report only)
SOURCE_TEST_DOC_FILES_CHANGED=NONE
ACTUAL_DIFF=DIFFS=NONE

STOP=WAITING_FOR_PROCEDUJ
