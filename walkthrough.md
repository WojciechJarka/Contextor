# TASK: CONTEXTOR_B0G4C13_REAL_SINGLE_EDGE_CLOSURE_DOGFOOD

## HEAD
- HEAD before report write: 7a1b751120026fdca0c0970741472568a7ca65ed
- GIT_STATUS before report write: CLEAN
- Repository identity: ctx_8efc50d8

## LIVE_REVISION_BEFORE_AFTER
- IPC ping/snapshot/ping revision: 439 / 439 / 439
- IPC status: ok / ok / ok; available_before_snapshot=True
- Activity epoch from current Contextor event query: 1beab26da2ff4932852caa7db6ff4242
- Current Contextor pre-analysis event query: revision/latest=439/439; continuity=continuous; resync_required=false; events after 439=0.
- Post-analysis Contextor recheck: revision/latest=439/439; activity_epoch=1beab26da2ff4932852caa7db6ff4242 (unchanged); continuity=continuous; resync_required=false; syntax, collision and cycle diagnostics fresh; events after 439=0.
- Authority identity stable before/after: PASS
- Nonsecret authority identity: {"endpoint_fingerprint": "400455f6441657fd707580fc96f070c2f304a83bcdec0056d4ee91cabbe6e21e", "lease_generation": 29, "process_start_identity": "134364430448216858", "repo_id": "ctx_8efc50d8", "root_path": "C:\\Temp\\Contextor_Repo", "runtime_domain_id": "rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654", "service_instance_id": "fe7c7039aa964f518106a217e4a34679", "service_pid": 7920}
- LiveStateClient constructed with is_owner=False; no owner mutation request was sent.

## CANONICAL_FRESHNESS
- Contextor LIVE diagnostic evidence at revision 439: graph/topology/cycles/collisions fresh; syntax errors=0, name collisions=0, reported cycles=16; resync_required=false.
- Canonical IPC cycles_state=fresh; resync_required=False; state.cycles count=16.
- The three function implementations were fetched from LIVE at revision 439 with workspace_sync=verified.
- All 33 current cyclic SCC members were individually verified through Contextor get_module_context at revision 439 with workspace_sync=verified.
- Ownership/blast-radius evidence at revision 439: functions are defined in the adapter layer and have only direct static test consumers listed below; no production downstream consumers reported.

## SOURCE_SNAPSHOT_COHERENCE
- Parsed exactly 33 current cyclic SCC source files using contextor.core.source.parse_source_with_fingerprint after resolving canonical module identities through state.modules.
- Every parsed source fingerprint matched a second byte read: PASS, 33/33.
- Canonical file-state fingerprint entries in the IPC snapshot: 0.
- Atomic cross-file source-to-revision fingerprint binding: UNKNOWN. The snapshot exposed no canonical per-file fingerprints; individual module workspace synchronization was verified at revision 439, all source reads were byte-stable, and the IPC revision remained stable through analysis.

## STRUCTURAL_SCC_INVENTORY
- Complete in-memory copy of canonical hard graph: nodes=468, distinct directed hard edges=1789.
- Cyclic structural SCC count=2; cyclic member count=33; internal hard edge count=72.
- SCC ids follow the existing topology analyzer's deterministic ordering.
- Every internal edge pair occurs exactly once in the site and activation reports and matches the complete graph's edges internal to each cyclic component.

## GLOBAL_ACCOUNTING_INVARIANTS
- STRUCTURAL_SCC_COUNT=2 (cyclic SCC count)
- STRUCTURAL_MEMBER_COUNT=33
- STRUCTURAL_INTERNAL_EDGE_COUNT=72
- LEXICAL_EDGE_RECORD_COUNT=72
- LEXICAL_SITE_OCCURRENCE_COUNT=117
- LEXICAL_MATCHED_EDGE_COUNT=72
- LEXICAL_UNRESOLVED_EDGE_COUNT=0
- ACTIVATION_EDGE_COUNT=72
- DIRECT_CANDIDATE_EDGE_COUNT=46
- NON_DIRECT_CANDIDATE_EDGE_COUNT=26
- SINGLE_EDGE_WITNESS_COUNT=2
- NON_DIRECT_WITHOUT_DIRECT_RETURN_COUNT=24
- Invariants: lexical edge records = structural internal edges; activation edge records = structural internal edges; no structural edge disappeared; direct + non-direct = structural; per-SCC non-direct = witness + no-direct-return. PASS.

### Complete internal hard-edge accounting, one record per structural edge
### SCC01
- contextor.core.analysis.full_analysis_coordinator -> contextor.core.api.facade | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental.engine -> contextor.core.analysis.incremental.materialization | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental.engine -> contextor.core.analysis.incremental.plan_executor | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental.engine -> contextor.core.analysis.incremental.preparation | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental.engine -> contextor.core.analysis.refresh_planner | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.analysis.incremental.engine -> contextor.core.analysis.state_manager | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=2 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.analysis.incremental.materialization -> contextor.core.analysis.state_manager | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=5
- contextor.core.analysis.incremental.plan_executor -> contextor.core.analysis.incremental.materialization | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental.plan_executor -> contextor.core.analysis.refresh_planner | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental.plan_executor -> contextor.core.analysis.state_manager | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=4
- contextor.core.analysis.incremental.preparation -> contextor.core.analysis.lineage_extraction | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental.preparation -> contextor.core.analysis.state_manager | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental.preparation -> contextor.core.symbol_engine.indexer | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.incremental_engine -> contextor.core.analysis.incremental.engine | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.lineage_extraction -> contextor.core.analysis.state_manager | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.refresh_planner -> contextor.core.analysis.state_manager | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.analysis.state_manager -> contextor.core.live_state.__init__ | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.api.facade -> contextor.core.analysis.incremental.materialization | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=3
- contextor.core.api.facade -> contextor.core.analysis.state_manager | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.api.facade -> contextor.core.live_state.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=3
- contextor.core.api.facade -> contextor.core.live_state.store | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.api.facade -> contextor.core.reference.module_usage_reuse | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.api.facade -> contextor.core.reporting_engine.pipeline | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.api.facade -> contextor.core.single_file.single_file_analysis | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.api.facade -> contextor.core.symbol_engine.indexer | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.lineage_query.live_query -> contextor.core.analysis.state_manager | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.__init__ -> contextor.core.live_state.hydration | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.__init__ -> contextor.core.live_state.ipc | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.__init__ -> contextor.core.live_state.runtime | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.__init__ -> contextor.core.live_state.store | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.__init__ -> contextor.core.live_state.watcher | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.hydration -> contextor.core.analysis.incremental_engine | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.hydration -> contextor.core.analysis.state_manager | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.live_state.hydration -> contextor.core.live_state.runtime | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.hydration -> contextor.core.live_state.store | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.ipc -> contextor.core.live_state.store | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.runtime -> contextor.core.analysis.full_analysis_coordinator | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.live_state.runtime -> contextor.core.analysis.incremental.materialization | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.runtime -> contextor.core.analysis.incremental_engine | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.runtime -> contextor.core.analysis.state_manager | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=3
- contextor.core.live_state.runtime -> contextor.core.lineage_query.live_query | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.runtime -> contextor.core.live_state.ipc | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.runtime -> contextor.core.live_state.store | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.live_state.store -> contextor.core.analysis.state_manager | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.live_state.watcher -> contextor.core.analysis.state_manager | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.core.live_state.watcher -> contextor.core.api.facade | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.watcher -> contextor.core.live_state.ipc | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.live_state.watcher -> contextor.core.live_state.runtime | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.reference.module_usage_reuse -> contextor.core.analysis.state_manager | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.reporting_engine.pipeline -> contextor.core.analysis.state_manager | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.single_file.builders.__init__ -> contextor.core.single_file.builders.layer0_builders | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.single_file.builders.__init__ -> contextor.core.single_file.builders.layer2_builders | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.single_file.builders.layer0_builders -> contextor.core.analysis.state_manager | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.single_file.builders.layer2_builders -> contextor.core.analysis.state_manager | classification=CALL_DEPENDENT_CANDIDATE | direct_site_count=0 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.single_file.single_file_analysis -> contextor.core.single_file.builders.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.core.symbol_engine.indexer -> contextor.core.analysis.lineage_extraction | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
### SCC02
- contextor.repo_generator.__init__ -> contextor.repo_generator.main | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.repo_generator.filters -> contextor.ui.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=3
- contextor.repo_generator.icons -> contextor.ui.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.repo_generator.main -> contextor.repo_generator.filters | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.repo_generator.main -> contextor.repo_generator.icons | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.repo_generator.main -> contextor.ui.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=3
- contextor.ui.__init__ -> contextor.ui.gui | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.ui.exclude_gui -> contextor.ui.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=4
- contextor.ui.gui -> contextor.repo_generator.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.ui.gui -> contextor.ui.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=11
- contextor.ui.gui -> contextor.ui.exclude_gui | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.ui.gui -> contextor.ui.gui_parser | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=2
- contextor.ui.gui -> contextor.ui.progress_widget | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.ui.gui_parser -> contextor.ui.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=4
- contextor.ui.gui_parser -> contextor.ui.progress_widget | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1
- contextor.ui.progress_widget -> contextor.ui.__init__ | classification=UNGUARDED_DIRECT_CANDIDATE | direct_site_count=1 | site_status=LEXICAL_CANDIDATES | lexical_occurrences=1

## PER_SCC_CLOSURE_SUMMARY
### SCC01
- CANONICAL_MEMBERS (24): contextor.core.analysis.full_analysis_coordinator, contextor.core.analysis.incremental.engine, contextor.core.analysis.incremental.materialization, contextor.core.analysis.incremental.plan_executor, contextor.core.analysis.incremental.preparation, contextor.core.analysis.incremental_engine, contextor.core.analysis.lineage_extraction, contextor.core.analysis.refresh_planner, contextor.core.analysis.state_manager, contextor.core.api.facade, contextor.core.lineage_query.live_query, contextor.core.live_state.__init__, contextor.core.live_state.hydration, contextor.core.live_state.ipc, contextor.core.live_state.runtime, contextor.core.live_state.store, contextor.core.live_state.watcher, contextor.core.reference.module_usage_reuse, contextor.core.reporting_engine.pipeline, contextor.core.single_file.builders.__init__, contextor.core.single_file.builders.layer0_builders, contextor.core.single_file.builders.layer2_builders, contextor.core.single_file.single_file_analysis, contextor.core.symbol_engine.indexer
- STRUCTURAL_EDGE_COUNT=56
- DIRECT_EDGE_COUNT=30
- NON_DIRECT_EDGE_COUNT=26
- DIRECT_CYCLIC_SCC_COUNT=0
- SINGLE_EDGE_WITNESS_COUNT=2
- NON_DIRECT_WITHOUT_DIRECT_RETURN_COUNT=24
### SCC02
- CANONICAL_MEMBERS (9): contextor.repo_generator.__init__, contextor.repo_generator.filters, contextor.repo_generator.icons, contextor.repo_generator.main, contextor.ui.__init__, contextor.ui.exclude_gui, contextor.ui.gui, contextor.ui.gui_parser, contextor.ui.progress_widget
- STRUCTURAL_EDGE_COUNT=16
- DIRECT_EDGE_COUNT=16
- NON_DIRECT_EDGE_COUNT=0
- DIRECT_CYCLIC_SCC_COUNT=1
- SINGLE_EDGE_WITNESS_COUNT=0
- NON_DIRECT_WITHOUT_DIRECT_RETURN_COUNT=0

## COMPLETE_SINGLE_EDGE_WITNESS_INVENTORY
### SCC01: SINGLE_NON_DIRECT_LEXICAL_CLOSURE
- Closing edge: contextor.core.analysis.state_manager -> contextor.core.live_state.__init__
- Activation classification: CALL_DEPENDENT_CANDIDATE
- Closing edge present in unguarded_direct_edges: false
- Exact closing source path: C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py
- Every closing-edge lexical occurrence:
  - line=517, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "save_engine_state", "line": 506}], control_frames=[]
  - line=541, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "load_engine_state", "line": 534}], control_frames=[]
- Direct return path: contextor.core.live_state.__init__ -> contextor.core.live_state.runtime -> contextor.core.lineage_query.live_query -> contextor.core.analysis.state_manager
- Closed walk: contextor.core.analysis.state_manager -> contextor.core.live_state.__init__ -> contextor.core.live_state.runtime -> contextor.core.lineage_query.live_query -> contextor.core.analysis.state_manager
- Direct return-path edge evidence:
  - contextor.core.live_state.__init__ -> contextor.core.live_state.runtime; unguarded_direct_edges=true; source=C:\Temp\Contextor_Repo\contextor\core\live_state\__init__.py
    - line=12, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state.runtime', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.core.live_state.runtime -> contextor.core.lineage_query.live_query; unguarded_direct_edges=true; source=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
    - line=19, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.lineage_query.live_query', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.core.lineage_query.live_query -> contextor.core.analysis.state_manager; unguarded_direct_edges=true; source=C:\Temp\Contextor_Repo\contextor\core\lineage_query\live_query.py
    - line=6, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
### SCC01: SINGLE_NON_DIRECT_LEXICAL_CLOSURE
- Closing edge: contextor.core.live_state.watcher -> contextor.core.api.facade
- Activation classification: CALL_DEPENDENT_CANDIDATE
- Closing edge present in unguarded_direct_edges: false
- Exact closing source path: C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py
- Every closing-edge lexical occurrence:
  - line=486, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.api.facade', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "DesktopLiveWatcher", "line": 110}, {"kind": "FUNCTION", "name": "_load_watch_filters", "line": 485}], control_frames=[]
- Direct return path: contextor.core.api.facade -> contextor.core.live_state.__init__ -> contextor.core.live_state.watcher
- Closed walk: contextor.core.live_state.watcher -> contextor.core.api.facade -> contextor.core.live_state.__init__ -> contextor.core.live_state.watcher
- Direct return-path edge evidence:
  - contextor.core.api.facade -> contextor.core.live_state.__init__; unguarded_direct_edges=true; source=C:\Temp\Contextor_Repo\contextor\core\api\facade.py
    - line=61, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=823, column=12, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.core.live_state.store', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorFacade", "line": 551}, {"kind": "FUNCTION", "name": "analyze_project", "line": 559}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 811, "expression": "Name(id='analysis_result', ctx=Load())"}]
    - line=1149, column=16, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorFacade", "line": 551}, {"kind": "FUNCTION", "name": "analyze_project", "line": 559}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 811, "expression": "Name(id='analysis_result', ctx=Load())"}, {"kind": "IF", "branch": "BODY", "line": 1148, "expression": "Compare(left=Name(id='meta', ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)])"}]
  - contextor.core.live_state.__init__ -> contextor.core.live_state.watcher; unguarded_direct_edges=true; source=C:\Temp\Contextor_Repo\contextor\core\live_state\__init__.py
    - line=19, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state.watcher', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]

## DIRECT_RETURN_PATH_SOURCE_EVIDENCE
- For each witness, the return path and every direct edge are listed with canonical module IDs, absolute source path, line, column, import form, lexical match kind, activation scope, scope frames, and control frames.
- Every return edge was checked in its SCC's unguarded_direct_edges and against the full canonical hard graph.
- Each closed walk was checked as connected, directed, and closed at its starting module.

## NON_DIRECT_WITHOUT_RETURN_INVENTORY
- SCC01: contextor.core.analysis.full_analysis_coordinator -> contextor.core.api.facade; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py; lexical_occurrences=1
  - line=88, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.api.facade', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "run_full_analysis_exclusive", "line": 41}], control_frames=[{"kind": "TRY", "branch": "BODY", "line": 68, "expression": null}, {"kind": "IF", "branch": "ELSE", "line": 77, "expression": "Compare(left=Name(id='analysis_fn', ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)])"}]
- SCC01: contextor.core.analysis.incremental.engine -> contextor.core.analysis.refresh_planner; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py; lexical_occurrences=2
  - line=615, column=16, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.refresh_planner', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "IncrementalAnalysisEngine", "line": 150}, {"kind": "FUNCTION", "name": "update_file", "line": 564}], control_frames=[{"kind": "WITH", "branch": "BODY", "line": 569, "expression": null}, {"kind": "IF", "branch": "BODY", "line": 602, "expression": "UnaryOp(op=Not(), operand=Name(id='current_state', ctx=Load()))"}]
  - line=734, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.refresh_planner', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "IncrementalAnalysisEngine", "line": 150}, {"kind": "FUNCTION", "name": "update_file", "line": 564}], control_frames=[{"kind": "WITH", "branch": "BODY", "line": 569, "expression": null}]
- SCC01: contextor.core.analysis.incremental.plan_executor -> contextor.core.analysis.incremental.materialization; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py; lexical_occurrences=1
  - line=1475, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.incremental.materialization', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "execute_refresh_plan", "line": 1108}], control_frames=[{"kind": "FOR", "branch": "BODY", "line": 1342, "expression": "Attribute(value=Name(id='plan', ctx=Load()), attr='patch_families', ctx=Load())"}, {"kind": "IF", "branch": "ELSE", "line": 1343, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='modules')])"}, {"kind": "IF", "branch": "ELSE", "line": 1346, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='definitions')])"}, {"kind": "IF", "branch": "ELSE", "line": 1349, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='module_usages')])"}, {"kind": "IF", "branch": "ELSE", "line": 1352, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='reexport_facts')])"}, {"kind": "IF", "branch": "ELSE", "line": 1355, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='dependency_graph')])"}, {"kind": "IF", "branch": "ELSE", "line": 1394, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='artifact_consumption')])"}, {"kind": "IF", "branch": "ELSE", "line": 1448, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='identity_registry')])"}, {"kind": "IF", "branch": "ELSE", "line": 1452, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='cached_analytics')])"}, {"kind": "IF", "branch": "ELSE", "line": 1463, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='collision_facts')])"}, {"kind": "IF", "branch": "BODY", "line": 1474, "expression": "Compare(left=Name(id='family', ctx=Load()), ops=[Eq()], comparators=[Constant(value='collisions')])"}]
- SCC01: contextor.core.analysis.incremental.plan_executor -> contextor.core.analysis.refresh_planner; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py; lexical_occurrences=1
  - line=1260, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.refresh_planner', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "execute_refresh_plan", "line": 1108}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 1259, "expression": "Attribute(value=Name(id='plan', ctx=Load()), attr='recompute_modules', ctx=Load())"}]
- SCC01: contextor.core.analysis.incremental.preparation -> contextor.core.symbol_engine.indexer; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\preparation.py; lexical_occurrences=1
  - line=229, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.symbol_engine.indexer', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "prepare_source_update", "line": 147}], control_frames=[{"kind": "TRY", "branch": "BODY", "line": 228, "expression": null}]
- SCC01: contextor.core.api.facade -> contextor.core.analysis.incremental.materialization; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\api\facade.py; lexical_occurrences=3
  - line=117, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.incremental.materialization', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "_assemble_layer_collision_facts", "line": 102}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 116, "expression": "Compare(left=Name(id='state', ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)])"}]
  - line=850, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.incremental.materialization', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorFacade", "line": 551}, {"kind": "FUNCTION", "name": "analyze_project", "line": 559}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 811, "expression": "Name(id='analysis_result', ctx=Load())"}]
  - line=1010, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.incremental.materialization', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorFacade", "line": 551}, {"kind": "FUNCTION", "name": "analyze_project", "line": 559}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 811, "expression": "Name(id='analysis_result', ctx=Load())"}]
- SCC01: contextor.core.api.facade -> contextor.core.analysis.state_manager; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\api\facade.py; lexical_occurrences=2
  - line=812, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorFacade", "line": 551}, {"kind": "FUNCTION", "name": "analyze_project", "line": 559}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 811, "expression": "Name(id='analysis_result', ctx=Load())"}]
  - line=1666, column=16, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorFacade", "line": 551}, {"kind": "FUNCTION", "name": "_analyze_single_file_uncoordinated", "line": 1609}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 1645, "expression": "Compare(left=Name(id='resolved', ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)])"}, {"kind": "IF", "branch": "BODY", "line": 1665, "expression": "Name(id='state_only_candidate', ctx=Load())"}]
- SCC01: contextor.core.api.facade -> contextor.core.live_state.store; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\api\facade.py; lexical_occurrences=1
  - line=823, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state.store', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorFacade", "line": 551}, {"kind": "FUNCTION", "name": "analyze_project", "line": 559}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 811, "expression": "Name(id='analysis_result', ctx=Load())"}]
- SCC01: contextor.core.api.facade -> contextor.core.reference.module_usage_reuse; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\api\facade.py; lexical_occurrences=1
  - line=878, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.reference.module_usage_reuse', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorFacade", "line": 551}, {"kind": "FUNCTION", "name": "analyze_project", "line": 559}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 811, "expression": "Name(id='analysis_result', ctx=Load())"}]
- SCC01: contextor.core.live_state.hydration -> contextor.core.analysis.incremental_engine; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py; lexical_occurrences=1
  - line=94, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.incremental_engine', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "hydrate_repository_engine", "line": 87}], control_frames=[]
- SCC01: contextor.core.live_state.hydration -> contextor.core.analysis.state_manager; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py; lexical_occurrences=2
  - line=36, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "resolve_authoritative_repository_state", "line": 29}], control_frames=[]
  - line=95, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "hydrate_repository_engine", "line": 87}], control_frames=[]
- SCC01: contextor.core.live_state.hydration -> contextor.core.live_state.runtime; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py; lexical_occurrences=1
  - line=37, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state.runtime', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "resolve_authoritative_repository_state", "line": 29}], control_frames=[]
- SCC01: contextor.core.live_state.hydration -> contextor.core.live_state.store; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\hydration.py; lexical_occurrences=1
  - line=38, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state.store', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "resolve_authoritative_repository_state", "line": 29}], control_frames=[]
- SCC01: contextor.core.live_state.ipc -> contextor.core.live_state.store; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py; lexical_occurrences=1
  - line=2032, column=20, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state.store', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "CanonicalLiveServer", "line": 728}, {"kind": "FUNCTION", "name": "_execute_update_file", "line": 1884}], control_frames=[{"kind": "WITH", "branch": "BODY", "line": 1896, "expression": null}, {"kind": "IF", "branch": "BODY", "line": 2026, "expression": "Compare(left=Name(id='persister', ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)])"}, {"kind": "EXCEPT", "branch": "0", "line": 2031, "expression": "Name(id='Exception', ctx=Load())"}]
- SCC01: contextor.core.live_state.runtime -> contextor.core.analysis.full_analysis_coordinator; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py; lexical_occurrences=2
  - line=1266, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.full_analysis_coordinator', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "_repository_mutation_guard", "line": 1263}, {"kind": "FUNCTION", "name": "guard", "line": 1265}], control_frames=[]
  - line=1309, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.full_analysis_coordinator', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "_repository_recovery_verification_guard", "line": 1306}, {"kind": "FUNCTION", "name": "guard", "line": 1308}], control_frames=[]
- SCC01: contextor.core.live_state.runtime -> contextor.core.analysis.incremental.materialization; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py; lexical_occurrences=1
  - line=1449, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.incremental.materialization', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "run_service", "line": 1329}], control_frames=[{"kind": "TRY", "branch": "BODY", "line": 1396, "expression": null}, {"kind": "IF", "branch": "BODY", "line": 1447, "expression": "Compare(left=Name(id='state', ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)])"}]
- SCC01: contextor.core.live_state.runtime -> contextor.core.analysis.incremental_engine; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py; lexical_occurrences=1
  - line=1116, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.incremental_engine', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "_repository_updater", "line": 1108}, {"kind": "FUNCTION", "name": "update", "line": 1112}], control_frames=[]
- SCC01: contextor.core.live_state.runtime -> contextor.core.analysis.state_manager; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py; lexical_occurrences=3
  - line=1117, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "_repository_updater", "line": 1108}, {"kind": "FUNCTION", "name": "update", "line": 1112}], control_frames=[]
  - line=1172, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "_repository_persister", "line": 1153}, {"kind": "FUNCTION", "name": "persist", "line": 1163}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 1171, "expression": "Compare(left=Name(id='manager', ctx=Load()), ops=[Is()], comparators=[Constant(value=None)])"}]
  - line=1500, column=24, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "run_service", "line": 1329}], control_frames=[{"kind": "TRY", "branch": "BODY", "line": 1396, "expression": null}, {"kind": "IF", "branch": "BODY", "line": 1447, "expression": "Compare(left=Name(id='state', ctx=Load()), ops=[IsNot()], comparators=[Constant(value=None)])"}, {"kind": "IF", "branch": "BODY", "line": 1467, "expression": "Name(id='materialization_required', ctx=Load())"}, {"kind": "TRY", "branch": "BODY", "line": 1479, "expression": null}, {"kind": "IF", "branch": "BODY", "line": 1497, "expression": "Name(id='materialization_required', ctx=Load())"}]
- SCC01: contextor.core.live_state.store -> contextor.core.analysis.state_manager; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\store.py; lexical_occurrences=2
  - line=128, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "_normalize_reexport_facts_state", "line": 122}], control_frames=[]
  - line=1524, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "save_snapshot", "line": 1507}], control_frames=[]
- SCC01: contextor.core.live_state.watcher -> contextor.core.analysis.state_manager; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py; lexical_occurrences=2
  - line=514, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "DesktopLiveWatcher", "line": 110}, {"kind": "FUNCTION", "name": "_startup_reconciliation_paths", "line": 498}], control_frames=[]
  - line=535, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "DesktopLiveWatcher", "line": 110}, {"kind": "FUNCTION", "name": "_trusted_file_state", "line": 533}], control_frames=[]
- SCC01: contextor.core.live_state.watcher -> contextor.core.live_state.runtime; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\live_state\watcher.py; lexical_occurrences=1
  - line=372, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.live_state.runtime', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "DesktopLiveWatcher", "line": 110}, {"kind": "FUNCTION", "name": "_recover_client", "line": 350}], control_frames=[{"kind": "TRY", "branch": "BODY", "line": 371, "expression": null}]
- SCC01: contextor.core.reporting_engine.pipeline -> contextor.core.analysis.state_manager; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\reporting_engine\pipeline.py; lexical_occurrences=1
  - line=106, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "execute_global_pipeline", "line": 34}], control_frames=[]
- SCC01: contextor.core.single_file.builders.layer0_builders -> contextor.core.analysis.state_manager; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\single_file\builders\layer0_builders.py; lexical_occurrences=1
  - line=26, column=4, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "_canonical_state_module_is_current", "line": 18}], control_frames=[]
- SCC01: contextor.core.single_file.builders.layer2_builders -> contextor.core.analysis.state_manager; classification=CALL_DEPENDENT_CANDIDATE; source=C:\Temp\Contextor_Repo\contextor\core\single_file\builders\layer2_builders.py; lexical_occurrences=1
  - line=11, column=8, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.core.analysis.state_manager', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "TestContextBuilder", "line": 4}, {"kind": "FUNCTION", "name": "build", "line": 9}], control_frames=[]

## SCC01_FOCUSED_FUNCTION_EVIDENCE
- state_manager.save_engine_state: Contextor implementation starts at line 506; function-local import from contextor.core.live_state of save_snapshot at line 517. The function body invokes it. Scope is function-scoped; controls are empty.
- state_manager.load_engine_state: implementation starts at line 534; function-local import of load_snapshot at line 541. The function body invokes it. Scope is function-scoped; controls are empty.
- DesktopLiveWatcher._load_watch_filters: method starts at line 485; function-local facade import at line 486. DesktopLiveWatcher.__init__ calls the method at line 155. Whether the constructor is invoked during module initialization remains UNKNOWN.
- Actual qualifying SCC01 edges are those listed in the witness inventory; all their lexical occurrences and shortest direct return paths are included there.
- Lexical closure is confirmed; import-time activation and runtime binding outcome remain UNKNOWN.

## SCC02_DIRECT_CYCLE_CONTEXT
### SCC02: DIRECT_CANDIDATE_CYCLE_PRESENT
- SINGLE_NON_DIRECT_CLOSURE_PRESENT=False
- Direct cyclic component 1: members (9): contextor.repo_generator.__init__, contextor.repo_generator.filters, contextor.repo_generator.icons, contextor.repo_generator.main, contextor.ui.__init__, contextor.ui.exclude_gui, contextor.ui.gui, contextor.ui.gui_parser, contextor.ui.progress_widget
- Complete internal direct edge inventory (16):
  - contextor.repo_generator.__init__ -> contextor.repo_generator.main; source=C:\Temp\Contextor_Repo\contextor\repo_generator\__init__.py; lexical_occurrences=1
    - line=1, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.repo_generator.main', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.repo_generator.filters -> contextor.ui.__init__; source=C:\Temp\Contextor_Repo\contextor\repo_generator\filters.py; lexical_occurrences=3
    - line=5, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=6, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.path_memory', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=7, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.theme', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.repo_generator.icons -> contextor.ui.__init__; source=C:\Temp\Contextor_Repo\contextor\repo_generator\icons.py; lexical_occurrences=2
    - line=4, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=5, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.theme', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.repo_generator.main -> contextor.repo_generator.filters; source=C:\Temp\Contextor_Repo\contextor\repo_generator\main.py; lexical_occurrences=1
    - line=8, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.repo_generator.filters', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.repo_generator.main -> contextor.repo_generator.icons; source=C:\Temp\Contextor_Repo\contextor\repo_generator\main.py; lexical_occurrences=1
    - line=9, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.repo_generator.icons', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.repo_generator.main -> contextor.ui.__init__; source=C:\Temp\Contextor_Repo\contextor\repo_generator\main.py; lexical_occurrences=3
    - line=11, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=12, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.path_memory', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=13, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.theme', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.ui.__init__ -> contextor.ui.gui; source=C:\Temp\Contextor_Repo\contextor\ui\__init__.py; lexical_occurrences=1
    - line=5, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui.gui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.ui.exclude_gui -> contextor.ui.__init__; source=C:\Temp\Contextor_Repo\contextor\ui\exclude_gui.py; lexical_occurrences=4
    - line=16, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=17, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.theme', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=127, column=4, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.path_memory', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "find_repo_root", "line": 125}], control_frames=[]
    - line=148, column=4, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.path_memory', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "FUNCTION", "name": "run_exclude_window", "line": 142}], control_frames=[]
  - contextor.ui.gui -> contextor.repo_generator.__init__; source=C:\Temp\Contextor_Repo\contextor\ui\gui.py; lexical_occurrences=1
    - line=43, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.repo_generator', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.ui.gui -> contextor.ui.__init__; source=C:\Temp\Contextor_Repo\contextor\ui\gui.py; lexical_occurrences=11
    - line=52, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=53, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.exclude_check', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=54, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.exclude_gui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=55, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.gui_parser', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=56, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.path_memory', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=57, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.progress_widget', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=64, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.system_actions', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=69, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.test_runner', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=74, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.theme', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=411, column=12, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.gui_parser', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorGUI", "line": 91}, {"kind": "FUNCTION", "name": "open_rewrite_tool", "line": 399}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 410, "expression": "Name(id='json_path', ctx=Load())"}]
    - line=440, column=20, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.exclude_gui', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorGUI", "line": 91}, {"kind": "FUNCTION", "name": "_check_stale_excludes", "line": 418}, {"kind": "FUNCTION", "name": "worker", "line": 426}, {"kind": "FUNCTION", "name": "prompt", "line": 433}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 439, "expression": "Name(id='answer', ctx=Load())"}]
  - contextor.ui.gui -> contextor.ui.exclude_gui; source=C:\Temp\Contextor_Repo\contextor\ui\gui.py; lexical_occurrences=2
    - line=54, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui.exclude_gui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=440, column=20, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui.exclude_gui', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorGUI", "line": 91}, {"kind": "FUNCTION", "name": "_check_stale_excludes", "line": 418}, {"kind": "FUNCTION", "name": "worker", "line": 426}, {"kind": "FUNCTION", "name": "prompt", "line": 433}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 439, "expression": "Name(id='answer', ctx=Load())"}]
  - contextor.ui.gui -> contextor.ui.gui_parser; source=C:\Temp\Contextor_Repo\contextor\ui\gui.py; lexical_occurrences=2
    - line=55, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui.gui_parser', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=411, column=12, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui.gui_parser', matched_member=None, activation_scope=FUNCTION_SCOPED, scope_frames=[{"kind": "CLASS", "name": "ContextorGUI", "line": 91}, {"kind": "FUNCTION", "name": "open_rewrite_tool", "line": 399}], control_frames=[{"kind": "IF", "branch": "BODY", "line": 410, "expression": "Name(id='json_path', ctx=Load())"}]
  - contextor.ui.gui -> contextor.ui.progress_widget; source=C:\Temp\Contextor_Repo\contextor\ui\gui.py; lexical_occurrences=1
    - line=57, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui.progress_widget', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.ui.gui_parser -> contextor.ui.__init__; source=C:\Temp\Contextor_Repo\contextor\ui\gui_parser.py; lexical_occurrences=4
    - line=20, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=21, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.path_memory', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=22, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.progress_widget', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
    - line=23, column=0, form=IMPORT_FROM, match_kind=PARENT_INITIALIZER, requested='contextor.ui.theme', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.ui.gui_parser -> contextor.ui.progress_widget; source=C:\Temp\Contextor_Repo\contextor\ui\gui_parser.py; lexical_occurrences=1
    - line=22, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui.progress_widget', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
  - contextor.ui.progress_widget -> contextor.ui.__init__; source=C:\Temp\Contextor_Repo\contextor\ui\progress_widget.py; lexical_occurrences=1
    - line=15, column=0, form=IMPORT_FROM, match_kind=FROM_BASE, requested='contextor.ui', matched_member=None, activation_scope=MODULE_TOP_LEVEL, scope_frames=[], control_frames=[]
- A zero single-non-direct witness count does not mean zero cycles.
- B0G4C9 entry-order evidence is synthetic evidence only and does not establish production GUI runtime behavior.

## IMPLEMENTATION_OWNERSHIP_AND_CONSUMERS
- edge_sites.analyze_cyclic_import_sites (edge_sites.py lines 214-383): joins all canonical internal SCC edges with lexical AST candidates, preserving edges even without usable source/site evidence; no runtime import execution or source reads. Direct static consumer: tests.test_cycle_semantics_edge_sites.
- activation_view.analyze_cycle_activation_view (activation_view.py lines 49-165): classifies every internal edge and builds the unguarded direct candidate subgraph. Direct static consumers: tests.test_cycle_semantics_activation_view and tests.test_cycle_semantics_closure_witness.
- closure_witness.analyze_single_edge_cycle_closures (closure_witness.py lines 70-173): validates topology, member, edge and site-count identity; finds a deterministic shortest direct return path for each non-direct edge. Direct static consumer: tests.test_cycle_semantics_closure_witness.
- Contextor blast radius scope is direct static artifact consumption; no production downstream consumers were reported.

## REMAINING_RUNTIME_UNCERTAINTIES
- A witness is SINGLE_NON_DIRECT_LEXICAL_CLOSURE. It does not prove function activation during import, guard evaluation, Python import resolution, ImportError, successful initialization, or runtime safety.
- Each shortest return path is one deterministic witness, not an enumeration of all simple cycles.
- Edges lacking a direct-only return are retained; multiple non-direct edges may jointly participate in cycles.
- No analyzed SCC module was imported or executed. The process used read-only IPC, AST parsing of SCC source, and the three existing cycle-semantics functions.

## NO_SAFETY_CERTIFICATION
- NO_SAFETY_CERTIFICATION=YES. No cycle is classified as safe, harmless, erroneous, false-positive, or resolved.

## NO_WARNING_SUPPRESSION
- NO_WARNING_SUPPRESSION=YES. No graph policy, warning, diagnostic, or canonical state was modified.

## FILES_CHANGED
- FILES_CHANGED=NONE (the required walkthrough report artifact is excluded).
- ACTUAL_DIFF=DIFFS=NONE for source, test, and documentation files.

## FINAL_VERDICT
- B0G4C13_DOGFOOD_PASS — all graph accounting and witness gates passed on one stable canonical snapshot. Cross-file source atomic binding limitation is explicitly recorded above.
