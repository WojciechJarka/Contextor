# CPA10_SPIRAL_LOAD_SNAPSHOT_PHASE_TELEMETRY

STATUS=PARTIAL (literal patches and requested validation PASS; LIVE certification unavailable)
FILES_CHANGED=
- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py
- C:\Temp\Contextor_Repo\contextor\core\runtime_trace.py
- C:\Temp\Contextor_Repo\tests\test_live_state_store.py
- C:\Temp\Contextor_Repo\tests\test_runtime_trace.py
FULL_DIFFS=COMPLETE_BELOW
PY_COMPILE=PASS (exit 0)
TARGETED_TESTS=PASS (3 passed in 19.04s; exit 0)
TARGETED_TEST_COUNT=3
TARGETED_FAILURES=0
PHASE_SEQUENCE_EXACT=YES
SPLIT_LINEAGE_COUNT_RECORDED=YES (split load=2; lineage normalization=2)
NO_PER_CHUNK_TELEMETRY=YES
LOAD_SNAPSHOT_BEHAVIOR_CHANGED=NO
SNAPSHOT_SCHEMA_CHANGED=NO
TRACE_SCHEMA_CHANGED=NO
WORKSPACE_SYNC=out_of_sync (all four changed files, canonical revision 1454)
CANONICAL_STATE=fresh (snapshot provenance; does not certify edited source)
MCP_SERVER_RESTART_REQUIRED=YES
DESKTOP_RUNTIME_RESTART_REQUIRED=YES
FIX_DESIGNED_BY_AGENT=NO
HEAD=23e28f84c7c71f05aa719893b8bf41cd5d16c607

## Findings and evidence

DIRECT_EVIDENCE: Before modification, Contextor edit contexts returned workspace_sync=verified for both production files at revision 1454, provenance=snapshot. Initial Git status contained only a pre-existing walkthrough.md change. Exact replacement anchors matched once. All nine user patches were applied literally.

CODE_PATH_PROVED: Snapshot loading owner is store::load_snapshot; event-header owner is runtime_trace::_header_records. Emission uses existing trace_event. The normalization order remains unchanged. Split-lineage loader, normalizer implementations, query-index builder, legacy branch body, snapshot schemas, TRACE_SCHEMA and key_map were not edited.

DIRECT_EVIDENCE: Store blast-radius aggregate returned 34 canonical artifacts, 26 direct artifact consumers and 177 additional downstream modules (59 production, 118 tests), with no aggregate truncation. Consumers include hydration, IPC, runtime, state_manager, facade, MCP runtime/query_helpers and GUI. runtime_trace edit context supplies compact API/consumer/test evidence; its samples do not constitute exhaustive consumer review.

CONTRACT_PROVED: The requested new test passed the exact seven-phase sequence, repo_id propagation, nonnegative numeric durations, both counts=2 and timing_semantics equality. Schema-1.3 roundtrip and trace-header event registration passed.

DIRECT_EVIDENCE: Post-edit Contextor read-only verification returned workspace_sync=out_of_sync for all four files; canonical_state=fresh, revision=1454, provenance=snapshot. Before and after get_live_events returned no_live_service with no events. get_symbol_lineage returned canonical_live_unavailable. contextor_fact_lineage(symbol_calls, downstream, depth=2) returned confirmed installation edges and full 419-module coverage, with snapshot provenance.

UNKNOWN: Current LIVE symbol lineage, desktop_watcher events, a new LIVE revision and runtime execution of edited telemetry are unavailable. Canonical checked_and_none refers to the old snapshot; py_compile and pytest validate current source. No FINAL PASS is claimed.

INFERENCE: No cause for LIVE unavailability or runtime performance improvement is inferred.

## Actions and validation

Applied exactly the requested nine patches to the four allowed files. No additional measurements, fix design, refactor, per-chunk telemetry, schema change, update_file, analyze_project, full suite, Spiral-Prophet load or manual restart.

Executed the requested py_compile against the four absolute paths; exit=0. Then executed one physical pytest command line:
```powershell
& C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_store.py::test_split_snapshot_load_emits_non_overlapping_phase_timings tests/test_live_state_store.py::test_exact_schema_13_splits_lineage_and_roundtrips tests/test_runtime_trace.py::test_desktop_trace_session_headers_and_finish
```
Result: 3 passed in 19.04s; exit=0. No passing tests were repeated.

## Next step / STOP

STOP. Await proceduj. Required MCP/Desktop runtime reloads have not been performed. After manual reload, verify runtime freshness/schema/version and canonical synchronization before LIVE certification.

## Contextor raw evidence

```json
{
  "before_0": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"file\": \"contextor/core/live_state/store.py\",\n  \"file_exists\": true,\n  \"target\": \"contextor/core/live_state/store.py\",\n  \"target_kind\": \"module\",\n  \"status\": \"available\",\n  \"module\": \"contextor.core.live_state.store\",\n  \"module_id\": \"225/1\",\n  \"layer\": \"adapter\",\n  \"entrypoint\": false,\n  \"risk_score\": 0.1787,\n  \"syntax_diagnostics\": {\n    \"status\": \"checked_and_none\",\n    \"availability\": \"fresh\",\n    \"materialized\": true,\n    \"source_path\": \"contextor/core/live_state/store.py\",\n    \"errors\": [],\n    \"total\": 0,\n    \"truncated\": false\n  },\n  \"dependency_data_source\": \"live_canonical_graph\",\n  \"artifact_data_source\": \"live_registry_and_symbol_state\",\n  \"state_freshness\": {\n    \"canonical_state\": \"fresh\",\n    \"workspace_sync\": \"verified\",\n    \"canonical_revision\": 1454,\n    \"provenance\": \"snapshot\",\n    \"families\": {\n      \"module\": \"fresh\",\n      \"graph\": \"fresh\",\n      \"topology\": \"fresh\",\n      \"artifact_consumption\": \"fresh\",\n      \"cycles\": \"fresh\",\n      \"collisions\": \"fresh\",\n      \"lineage\": \"fresh\"\n    },\n    \"advisory_warning\": null\n  },\n  \"warnings\": [],\n  \"public_api\": {\n    \"total\": 10,\n    \"truncated\": true,\n    \"unresolved_total\": 0,\n    \"evidence\": {\n      \"A1072/1\": \"contextor.core.live_state.store::save_snapshot\",\n      \"A1259/1\": \"contextor.core.live_state.store::SnapshotRevisionConflict.__init__\",\n      \"A141/1\": \"contextor.core.live_state.store::LIVE_STATE_SCHEMA_VERSION\"\n    },\n    \"expand\": {\n      \"compact\": false,\n      \"max_items\": null\n    }\n  },\n  \"imports\": {\n    \"total\": 5,\n    \"truncated\": true,\n    \"evidence\": [\n      {\n        \"module_id\": \"171/1\",\n        \"module\": \"contextor.core.domain.usage_facts\"\n      },\n      {\n        \"module_id\": \"238/1\",\n        \"module\": \"contextor.core.paths\"\n      },\n      {\n        \"module_id\": \"339/3\",\n        \"module\": \"contextor.core.domain.lineage_facts\"\n      }\n    ],\n    \"expand\": {\n      \"compact\": false,\n      \"max_items\": null\n    }\n  },\n  \"consumers\": {\n    \"total\": 22,\n    \"truncated\": true,\n    \"evidence\": [\n      {\n        \"module_id\": \"106/1\",\n        \"module\": \"contextor.core.live_state.ipc\"\n      },\n      {\n        \"module_id\": \"108/1\",\n        \"module\": \"contextor.core.live_state.__init__\"\n      },\n      {\n        \"module_id\": \"139/1\",\n        \"module\": \"tests.test_h3a_workspace_canonical_freshness\"\n      }\n    ],\n    \"expand\": {\n      \"compact\": false,\n      \"max_items\": null\n    }\n  },\n  \"tests_covering\": {\n    \"available\": true,\n    \"total\": 98,\n    \"truncated\": true,\n    \"evidence_scope\": \"static_dependency_reachability\",\n    \"max_depth\": 6,\n    \"evidence\": [\n      {\n        \"module_id\": \"377/1\",\n        \"module\": \"tests.live_state.test_ipc_canonical_query\",\n        \"distance\": 2,\n        \"evidence_path\": [\n          \"tests.live_state.test_ipc_canonical_query\",\n          \"contextor.core.live_state.ipc\",\n          \"contextor.core.live_state.store\"\n        ],\n        \"evidence_scope\": \"static_dependency_reachability\"\n      },\n      {\n        \"module_id\": \"380/1\",\n        \"module\": \"tests.live_state.test_runtime_canonical_query\",\n        \"distance\": 2,\n        \"evidence_path\": [\n          \"tests.live_state.test_runtime_canonical_query\",\n          \"contextor.core.live_state.ipc\",\n          \"contextor.core.live_state.store\"\n        ],\n        \"evidence_scope\": \"static_dependency_reachability\"\n      },\n      {\n        \"module_id\": \"398/1\",\n        \"module\": \"tests.mcp.test_get_symbol_implementation_input_boundary\",\n        \"distance\": 3,\n        \"evidence_path\": [\n          \"tests.mcp.test_get_symbol_implementation_input_boundary\",\n          \"contextor.mcp_server\",\n          \"contextor.mcp.query_helpers\",\n          \"contextor.core.live_state.store\"\n        ],\n        \"evidence_scope\": \"static_dependency_reachability\"\n      }\n    ],\n    \"expand\": {\n      \"compact\": false,\n      \"max_items\": null\n    }\n  },\n  \"diagnostics_summary\": {\n    \"syntax_errors\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"name_collisions\": {\n      \"count\": 0,\n      \"critical\": null,\n      \"warning\": null,\n      \"info\": null,\n      \"availability\": \"fresh\"\n    },\n    \"cycles\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"attention_required\": false,\n    \"availability\": {\n      \"syntax_errors\": \"fresh\",\n      \"name_collisions\": \"fresh\",\n      \"cycles\": \"fresh\"\n    }\n  },\n  \"diagnostics_attention_required\": false\n}"
        }
      ],
      "isError": false
    }
  },
  "before_1": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"file\": \"contextor/core/runtime_trace.py\",\n  \"file_exists\": true,\n  \"target\": \"contextor/core/runtime_trace.py\",\n  \"target_kind\": \"module\",\n  \"status\": \"available\",\n  \"module\": \"contextor.core.runtime_trace\",\n  \"module_id\": \"85/1\",\n  \"layer\": \"adapter\",\n  \"entrypoint\": false,\n  \"risk_score\": 0.1444,\n  \"syntax_diagnostics\": {\n    \"status\": \"checked_and_none\",\n    \"availability\": \"fresh\",\n    \"materialized\": true,\n    \"source_path\": \"contextor/core/runtime_trace.py\",\n    \"errors\": [],\n    \"total\": 0,\n    \"truncated\": false\n  },\n  \"dependency_data_source\": \"live_canonical_graph\",\n  \"artifact_data_source\": \"live_registry_and_symbol_state\",\n  \"state_freshness\": {\n    \"canonical_state\": \"fresh\",\n    \"workspace_sync\": \"verified\",\n    \"canonical_revision\": 1454,\n    \"provenance\": \"snapshot\",\n    \"families\": {\n      \"module\": \"fresh\",\n      \"graph\": \"fresh\",\n      \"topology\": \"fresh\",\n      \"artifact_consumption\": \"fresh\",\n      \"cycles\": \"fresh\",\n      \"collisions\": \"fresh\",\n      \"lineage\": \"fresh\"\n    },\n    \"advisory_warning\": null\n  },\n  \"warnings\": [],\n  \"public_api\": {\n    \"total\": 31,\n    \"truncated\": true,\n    \"unresolved_total\": 0,\n    \"evidence\": {\n      \"A1310/1\": \"contextor.core.runtime_trace::trace_operation\",\n      \"A1506/1\": \"contextor.core.runtime_trace::TRACE_SCHEMA\",\n      \"A1722/1\": \"contextor.core.runtime_trace::finish_desktop_trace_session\"\n    },\n    \"expand\": {\n      \"compact\": false,\n      \"max_items\": null\n    }\n  },\n  \"imports\": {\n    \"total\": 1,\n    \"truncated\": false,\n    \"evidence\": [\n      {\n        \"module_id\": \"238/1\",\n        \"module\": \"contextor.core.paths\"\n      }\n    ]\n  },\n  \"consumers\": {\n    \"total\": 22,\n    \"truncated\": true,\n    \"evidence\": [\n      {\n        \"module_id\": \"106/1\",\n        \"module\": \"contextor.core.live_state.ipc\"\n      },\n      {\n        \"module_id\": \"13/1\",\n        \"module\": \"contextor.core.live_state.watcher\"\n      },\n      {\n        \"module_id\": \"188/1\",\n        \"module\": \"tests.test_full_analysis_coordination\"\n      }\n    ],\n    \"expand\": {\n      \"compact\": false,\n      \"max_items\": null\n    }\n  },\n  \"tests_covering\": {\n    \"available\": true,\n    \"total\": 126,\n    \"truncated\": true,\n    \"evidence_scope\": \"static_dependency_reachability\",\n    \"max_depth\": 6,\n    \"evidence\": [\n      {\n        \"module_id\": \"352/1\",\n        \"module\": \"tests.analysis.test_lineage_extraction\",\n        \"distance\": 2,\n        \"evidence_path\": [\n          \"tests.analysis.test_lineage_extraction\",\n          \"contextor.core.symbol_engine.indexer\",\n          \"contextor.core.runtime_trace\"\n        ],\n        \"evidence_scope\": \"static_dependency_reachability\"\n      },\n      {\n        \"module_id\": \"377/1\",\n        \"module\": \"tests.live_state.test_ipc_canonical_query\",\n        \"distance\": 2,\n        \"evidence_path\": [\n          \"tests.live_state.test_ipc_canonical_query\",\n          \"contextor.core.live_state.ipc\",\n          \"contextor.core.runtime_trace\"\n        ],\n        \"evidence_scope\": \"static_dependency_reachability\"\n      },\n      {\n        \"module_id\": \"380/1\",\n        \"module\": \"tests.live_state.test_runtime_canonical_query\",\n        \"distance\": 2,\n        \"evidence_path\": [\n          \"tests.live_state.test_runtime_canonical_query\",\n          \"contextor.core.live_state.ipc\",\n          \"contextor.core.runtime_trace\"\n        ],\n        \"evidence_scope\": \"static_dependency_reachability\"\n      }\n    ],\n    \"expand\": {\n      \"compact\": false,\n      \"max_items\": null\n    }\n  },\n  \"diagnostics_summary\": {\n    \"syntax_errors\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"name_collisions\": {\n      \"count\": 0,\n      \"critical\": null,\n      \"warning\": null,\n      \"info\": null,\n      \"availability\": \"fresh\"\n    },\n    \"cycles\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"attention_required\": false,\n    \"availability\": {\n      \"syntax_errors\": \"fresh\",\n      \"name_collisions\": \"fresh\",\n      \"cycles\": \"fresh\"\n    }\n  },\n  \"diagnostics_attention_required\": false\n}"
        }
      ],
      "isError": false
    }
  },
  "before_2": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\"module\":\"contextor.core.live_state.store\",\"aggregate\":{\"artifact_count_total\":34,\"artifact_count_returned\":0,\"unique_direct_consumers\":{\"total\":26,\"truncated\":false,\"items\":[\"contextor.core.analysis.state_manager\",\"contextor.core.api.facade\",\"contextor.core.live_state.__init__\",\"contextor.core.live_state.hydration\",\"contextor.core.live_state.ipc\",\"contextor.core.live_state.runtime\",\"contextor.mcp.query_helpers\",\"contextor.mcp.runtime\",\"contextor.ui.gui\",\"tests.test_cached_facts_live_analytics\",\"tests.test_cached_target_resolution\",\"tests.test_cycles_live_lifecycle\",\"tests.test_graph_only_live_analytics\",\"tests.test_h3a_workspace_canonical_freshness\",\"tests.test_lineage_state_lifecycle\",\"tests.test_live_mutation_coordinator\",\"tests.test_live_state_ipc\",\"tests.test_live_state_store\",\"tests.test_live_watcher_startup_reconciliation\",\"tests.test_matrix_clusters_state_lifecycle\",\"tests.test_mcp_regressions\",\"tests.test_module_usage_facts\",\"tests.test_persistent_topology_provenance\",\"tests.test_symbol_call_facts\",\"tests.test_syntax_diagnostics_full_analysis\",\"tests.test_topology_bootstrap_and_consumer_truth\"]},\"unique_downstream_consumers\":{\"available\":true,\"total\":177,\"total_downstream_count\":177,\"items\":[\"contextor.__main__\",\"contextor.cli\",\"contextor.core.__init__\",\"contextor.core.analysis.full_analysis_coordinator\",\"contextor.core.analysis.incremental.__init__\",\"contextor.core.analysis.incremental.engine\",\"contextor.core.analysis.incremental.materialization\",\"contextor.core.analysis.incremental.plan_executor\",\"contextor.core.analysis.incremental.preparation\",\"contextor.core.analysis.incremental_engine\",\"contextor.core.analysis.lineage_extraction\",\"contextor.core.analysis.profile_runner\",\"contextor.core.analysis.profile_worker\",\"contextor.core.analysis.refresh_planner\",\"contextor.core.canonical_state_query.__init__\",\"contextor.core.canonical_state_query.runtime\",\"contextor.core.facts.build\",\"contextor.core.lineage_query.live_query\",\"contextor.core.live_state.watcher\",\"contextor.core.reference.module_usage_reuse\",\"contextor.core.reporting_engine.__init__\",\"contextor.core.reporting_engine.pipeline\",\"contextor.core.single_file.builders.__init__\",\"contextor.core.single_file.builders.layer0_builders\",\"contextor.core.single_file.builders.layer2_builders\",\"contextor.core.symbol_engine.indexer\",\"contextor.mcp.analysis_jobs\",\"contextor.mcp.diagnostics\",\"contextor.mcp.tools.analyze_layer\",\"contextor.mcp.tools.analyze_project\",\"contextor.mcp.tools.analyze_single_file\",\"contextor.mcp.tools.contextor_fact_lineage\",\"contextor.mcp.tools.extract_indexed_report_context\",\"contextor.mcp.tools.get_analysis_status\",\"contextor.mcp.tools.get_artifact_blast_radius\",\"contextor.mcp.tools.get_artifacts_for_module\",\"contextor.mcp.tools.get_file_edit_context\",\"contextor.mcp.tools.get_layer_isolation\",\"contextor.mcp.tools.get_live_events\",\"contextor.mcp.tools.get_module_blast_radius\",\"contextor.mcp.tools.get_module_context\",\"contextor.mcp.tools.get_name_collisions\",\"contextor.mcp.tools.get_project_architecture\",\"contextor.mcp.tools.get_report_diff\",\"contextor.mcp.tools.get_source_range\",\"contextor.mcp.tools.get_symbol_call_context\",\"contextor.mcp.tools.get_symbol_implementation\",\"contextor.mcp.tools.get_symbol_lineage\",\"contextor.mcp.tools.lookup_artifact_by_symbol\",\"contextor.mcp.tools.query_canonical_projection\",\"contextor.mcp.tools.search_artifacts\",\"contextor.mcp.tools.search_source\",\"contextor.mcp.tools.update_file\",\"contextor.mcp_main\",\"contextor.mcp_server\",\"contextor.mcp_worker\",\"contextor.ui.__init__\",\"contextor.ui.exclude_gui\",\"main\",\"tests.analysis.test_lineage_cache_codec\",\"tests.analysis.test_lineage_extraction\",\"tests.analysis.test_lineage_extraction_equivalence\",\"tests.analysis.test_lineage_live_query\",\"tests.analysis.test_lineage_materialization\",\"tests.live_state.test_ipc_canonical_query\",\"tests.live_state.test_runtime_canonical_query\",\"tests.mcp.test_get_symbol_implementation_input_boundary\",\"tests.mcp.test_live_diagnostics_narrow\",\"tests.mcp.test_runtime_lineage_query\",\"tests.mcp.tools.test_analysis_status_concurrency\",\"tests.mcp.tools.test_analysis_trigger_docs\",\"tests.mcp.tools.test_architecture_context_contracts\",\"tests.mcp.tools.test_auto_bounded_output\",\"tests.mcp.tools.test_canonical_projection_single_call\",\"tests.mcp.tools.test_compact_evidence_contract\",\"tests.mcp.tools.test_contextor_fact_lineage\",\"tests.mcp.tools.test_extract_indexed_report_context\",\"tests.mcp.tools.test_get_artifact_blast_radius\",\"tests.mcp.tools.test_get_artifacts_for_module\",\"tests.mcp.tools.test_get_file_edit_context_syntax\",\"tests.mcp.tools.test_get_layer_isolation_registry_reuse\",\"tests.mcp.tools.test_get_module_blast_radius\",\"tests.mcp.tools.test_get_module_context\",\"tests.mcp.tools.test_get_project_architecture_full_reports\",\"tests.mcp.tools.test_get_source_range_direct_lookup\",\"tests.mcp.tools.test_get_symbol_call_context\",\"tests.mcp.tools.test_get_symbol_implementation\",\"tests.mcp.tools.test_get_symbol_lineage\",\"tests.mcp.tools.test_lineage_freshness\",\"tests.mcp.tools.test_minimal_registry_read_path\",\"tests.mcp.tools.test_public_mcp_docs_parity\",\"tests.mcp.tools.test_search_artifacts\",\"tests.mcp.tools.test_search_source\",\"tests.mcp.tools.test_specialized_tool_contracts\",\"tests.mcp.tools.test_status_live_update_contracts\",\"tests.test_artifact_parallelism\",\"tests.test_artifact_report\",\"tests.test_cancellation\",\"tests.test_canonical_reference_projection\",\"tests.test_canonical_state_contract\",\"tests.test_channel_parity_and_cow\",\"tests.test_collision_facts_fusion\",\"tests.test_collisions_live_lifecycle\",\"tests.test_completeness_freshness_parity_proof\",\"tests.test_derived_analytics_parity\",\"tests.test_facade_progress_staging\",\"tests.test_freshness_preservation\",\"tests.test_full_analysis_coordination\",\"tests.test_full_analysis_lineage_materialization\",\"tests.test_generators\",\"tests.test_get_symbol_call_context\",\"tests.test_gui_live_startup\",\"tests.test_gui_single_instance\",\"tests.test_h2a_complexity_regression\",\"tests.test_h2a_hard_reset_regression\",\"tests.test_h2a_reference_index_equivalence\",\"tests.test_h2c_collision_equivalence\",\"tests.test_h2c_complexity_regression\",\"tests.test_incremental_artifact_consumption\",\"tests.test_incremental_equivalence\",\"tests.test_incremental_local_metrics\",\"tests.test_incremental_phase_trace\",\"tests.test_incremental_plan_executor_complexity\",\"tests.test_incremental_reverse_context\",\"tests.test_index_fusion\",\"tests.test_indexer_profile_evidence\",\"tests.test_jaccard_handoff_0j5\",\"tests.test_layer_collision_reuse\",\"tests.test_layer_state_only_hydration\",\"tests.test_lineage_index_cache\",\"tests.test_live_activity_status\",\"tests.test_live_authority_bootstrap\",\"tests.test_live_desktop_integration\",\"tests.test_live_e2e_corrections\",\"tests.test_live_job_object\",\"tests.test_live_single_file_reuse\",\"tests.test_live_state_consistency\",\"tests.test_live_watcher_watchdog\",\"tests.test_matrix_clusters_ram_parity\",\"tests.test_mcp_backend_cli\",\"tests.test_mcp_child_process_cleanup\",\"tests.test_mcp_diagnostics\",\"tests.test_mcp_documentation\",\"tests.test_mcp_identity_resolution\",\"tests.test_mcp_incremental_hydration\",\"tests.test_mcp_shared_backend_server_mode\",\"tests.test_mcp_split_s2a\",\"tests.test_mcp_split_s2b\",\"tests.test_mcp_split_s2c\",\"tests.test_mcp_split_s2d\",\"tests.test_mcp_split_s2e\",\"tests.test_mcp_transport_output\",\"tests.test_module_usage_reuse\",\"tests.test_no_double_parse\",\"tests.test_non_python_files\",\"tests.test_parity_and_freshness_proof\",\"tests.test_payload_isolation\",\"tests.test_pipeline\",\"tests.test_process_pool_lifecycle\",\"tests.test_profile_runner\",\"tests.test_profile_worker\",\"tests.test_reexport_reference_semantics\",\"tests.test_reference_fusion_integration\",\"tests.test_reference_fusion_semantic_core\",\"tests.test_refresh_plan_execution\",\"tests.test_refresh_planner\",\"tests.test_reporting_single_file\",\"tests.test_repository_identity_initialization\",\"tests.test_repository_scope_guards\",\"tests.test_runtime_authority_events\",\"tests.test_search_source\",\"tests.test_shadow_planning_integration\",\"tests.test_staged_progress\",\"tests.test_test_context_ast_reuse_0f2g\",\"tests.test_test_context_discovery_map_0j7\",\"tests.test_test_context_fusion\",\"tests.test_test_runner\"],\"truncated\":false,\"classification_available\":true,\"layer_classification_available\":true,\"production\":59,\"tests\":118,\"unknown\":0,\"production_downstream_count\":59,\"test_downstream_count\":118,\"unknown_layer_downstream_count\":0},\"consumed_artifact_ids\":[\"A3234/1\",\"A2173/1\",\"A615/1\",\"A3370/1\",\"A2597/1\",\"A1072/1\",\"A920/1\"],\"unconsumed_artifact_ids\":[\"A1360/1\",\"A5372/1\",\"A3886/1\",\"A4564/1\",\"A1272/1\",\"A3039/1\",\"A5374/1\",\"A5382/1\",\"A3874/1\",\"A3887/1\",\"A3866/1\",\"A3870/1\",\"A3865/1\",\"A4462/2\",\"A3863/1\",\"A4548/1\",\"A3873/1\",\"A3878/1\",\"A3882/1\",\"A5373/1\",\"A1134/1\",\"A325/1\",\"A5375/1\",\"A5376/1\",\"A5371/1\",\"A141/1\",\"A1259/1\"],\"highest_impact_artifact_ids\":[\"A615/1\",\"A1072/1\",\"A2597/1\",\"A3370/1\",\"A920/1\",\"A2173/1\",\"A3234/1\",\"A5371/1\",\"A141/1\",\"A1259/1\",\"A1134/1\",\"A325/1\",\"A1360/1\",\"A5372/1\",\"A3886/1\",\"A4564/1\",\"A1272/1\",\"A3039/1\",\"A5374/1\",\"A5382/1\",\"A3874/1\",\"A3887/1\",\"A3866/1\",\"A3870/1\",\"A3865/1\",\"A4462/2\",\"A3863/1\",\"A4548/1\",\"A3873/1\",\"A3878/1\",\"A3882/1\",\"A5373/1\",\"A5375/1\",\"A5376/1\"]},\"state_freshness\":{\"canonical_state\":\"fresh\",\"workspace_sync\":\"unverified\",\"canonical_revision\":1454,\"provenance\":\"snapshot\",\"families\":{\"module\":\"fresh\",\"graph\":\"fresh\",\"topology\":\"fresh\",\"artifact_consumption\":\"fresh\",\"cycles\":\"fresh\",\"collisions\":\"fresh\",\"lineage\":\"fresh\"},\"advisory_warning\":null},\"consumer_representation\":{\"representation\":\"named\",\"requested_representation\":\"auto\"}}"
        }
      ],
      "isError": false
    }
  },
  "before_3": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"status\": \"error\",\n  \"error\": \"canonical_live_unavailable\"\n}"
        }
      ],
      "isError": false
    }
  },
  "before_4": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"status\": \"ok\",\n  \"family\": \"symbol_calls\",\n  \"owner\": [\n    \"state:RepositoryAnalysisState.module_usages[*].symbol_calls\"\n  ],\n  \"entry_points\": [\n    \"family:symbol_calls\"\n  ],\n  \"nodes\": [\n    {\n      \"id\": \"state:RepositoryAnalysisState.module_usages[*].symbol_calls\",\n      \"type\": \"canonical_state_field\",\n      \"name\": \"module_usages[*].symbol_calls\",\n      \"state_owner\": \"RepositoryAnalysisState\",\n      \"state_field\": \"module_usages[*].symbol_calls\",\n      \"family_state_field\": \"module_usages[*].symbol_calls_materialized\"\n    },\n    {\n      \"id\": \"family:symbol_calls\",\n      \"type\": \"data_family\",\n      \"name\": \"symbol_calls\",\n      \"role\": \"anchor\"\n    },\n    {\n      \"id\": \"symbol:A1421/1\",\n      \"type\": \"symbol\",\n      \"name\": \"contextor.core.api.facade::ContextorFacade.analyze_project\",\n      \"qualified_name\": \"contextor.core.api.facade::ContextorFacade.analyze_project\",\n      \"module\": \"contextor.core.api.facade\",\n      \"artifact_id\": \"A1421/1\",\n      \"module_id\": \"286/1\"\n    },\n    {\n      \"id\": \"symbol:A2343/1\",\n      \"type\": \"symbol\",\n      \"name\": \"contextor.core.analysis.incremental.engine::IncrementalAnalysisEngine._apply_delta_and_commit\",\n      \"qualified_name\": \"contextor.core.analysis.incremental.engine::IncrementalAnalysisEngine._apply_delta_and_commit\",\n      \"module\": \"contextor.core.analysis.incremental.engine\",\n      \"artifact_id\": \"A2343/1\",\n      \"module_id\": \"68/1\"\n    }\n  ],\n  \"edges\": [\n    {\n      \"source\": \"family:symbol_calls\",\n      \"target\": \"symbol:A1421/1\",\n      \"type\": \"READS\",\n      \"confidence\": \"confirmed\",\n      \"evidence\": {\n        \"kind\": \"canonical_installation_input\",\n        \"qualified_symbol\": \"contextor.core.api.facade::ContextorFacade.analyze_project\",\n        \"branch\": \"full_baseline_reuse\",\n        \"canonical_state_field\": \"RepositoryAnalysisState.module_usages[*].symbol_calls\"\n      }\n    },\n    {\n      \"source\": \"family:symbol_calls\",\n      \"target\": \"symbol:A2343/1\",\n      \"type\": \"READS\",\n      \"confidence\": \"confirmed\",\n      \"evidence\": {\n        \"kind\": \"canonical_installation_input\",\n        \"qualified_symbol\": \"contextor.core.analysis.incremental.engine::IncrementalAnalysisEngine._apply_delta_and_commit\",\n        \"branch\": \"incremental_prepared_usage\",\n        \"canonical_state_field\": \"RepositoryAnalysisState.module_usages[*].symbol_calls\"\n      }\n    },\n    {\n      \"source\": \"symbol:A1421/1\",\n      \"target\": \"state:RepositoryAnalysisState.module_usages[*].symbol_calls\",\n      \"type\": \"MATERIALIZES\",\n      \"confidence\": \"confirmed\",\n      \"evidence\": {\n        \"kind\": \"canonical_state_installation_owner\",\n        \"qualified_symbol\": \"contextor.core.api.facade::ContextorFacade.analyze_project\",\n        \"canonical_state_field\": \"RepositoryAnalysisState.module_usages[*].symbol_calls\"\n      }\n    },\n    {\n      \"source\": \"symbol:A2343/1\",\n      \"target\": \"state:RepositoryAnalysisState.module_usages[*].symbol_calls\",\n      \"type\": \"UPDATES\",\n      \"confidence\": \"confirmed\",\n      \"evidence\": {\n        \"kind\": \"incremental_state_installation_owner\",\n        \"qualified_symbol\": \"contextor.core.analysis.incremental.engine::IncrementalAnalysisEngine._apply_delta_and_commit\",\n        \"canonical_state_field\": \"RepositoryAnalysisState.module_usages[*].symbol_calls\"\n      }\n    }\n  ],\n  \"public_projections\": [],\n  \"unresolved\": [],\n  \"freshness\": {\n    \"canonical_state\": \"fresh\",\n    \"workspace_sync\": \"unverified\",\n    \"canonical_revision\": 1454,\n    \"provenance\": \"snapshot\",\n    \"families\": {\n      \"module\": \"fresh\",\n      \"graph\": \"fresh\",\n      \"topology\": \"fresh\",\n      \"artifact_consumption\": \"fresh\",\n      \"cycles\": \"fresh\",\n      \"collisions\": \"fresh\",\n      \"lineage\": \"fresh\",\n      \"symbol_calls\": \"fresh\",\n      \"module_usages\": \"fresh\"\n    },\n    \"advisory_warning\": null,\n    \"resync_required\": false\n  },\n  \"data_source\": \"snapshot_canonical_state\",\n  \"coverage\": {\n    \"canonical_module_count\": 419,\n    \"symbol_calls_materialized_count\": 419,\n    \"reference_evidence_materialized_count\": 419,\n    \"missing_symbol_calls_materialization_count\": 0,\n    \"missing_reference_evidence_count\": 0,\n    \"stale_module_count\": 0\n  },\n  \"diagnostics_summary\": {\n    \"syntax_errors\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"name_collisions\": {\n      \"count\": 0,\n      \"critical\": null,\n      \"warning\": null,\n      \"info\": null,\n      \"availability\": \"fresh\"\n    },\n    \"cycles\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"attention_required\": false,\n    \"availability\": {\n      \"syntax_errors\": \"fresh\",\n      \"name_collisions\": \"fresh\",\n      \"cycles\": \"fresh\"\n    }\n  },\n  \"diagnostics_attention_required\": false\n}"
        }
      ],
      "isError": false
    }
  },
  "before_5": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"status\": \"no_live_service\",\n  \"repo_path\": \"C:\\\\Temp\\\\Contextor_Repo\",\n  \"events\": [],\n  \"total\": 0,\n  \"truncated\": false,\n  \"diagnostics_summary\": {\n    \"syntax_errors\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"name_collisions\": {\n      \"count\": 0,\n      \"critical\": null,\n      \"warning\": null,\n      \"info\": null,\n      \"availability\": \"fresh\"\n    },\n    \"cycles\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"attention_required\": false,\n    \"availability\": {\n      \"syntax_errors\": \"fresh\",\n      \"name_collisions\": \"fresh\",\n      \"cycles\": \"fresh\"\n    }\n  },\n  \"diagnostics_attention_required\": false\n}"
        }
      ],
      "isError": false
    }
  },
  "after_0": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"file\": \"contextor/core/live_state/store.py\",\n  \"status\": \"available\",\n  \"state_freshness\": {\n    \"canonical_state\": \"fresh\",\n    \"workspace_sync\": \"out_of_sync\",\n    \"canonical_revision\": 1454,\n    \"provenance\": \"snapshot\",\n    \"families\": {\n      \"module\": \"fresh\",\n      \"graph\": \"fresh\",\n      \"topology\": \"fresh\",\n      \"artifact_consumption\": \"fresh\",\n      \"cycles\": \"fresh\",\n      \"collisions\": \"fresh\",\n      \"lineage\": \"fresh\"\n    },\n    \"advisory_warning\": \"Target file on disk has been modified since canonical state revision was generated.\"\n  },\n  \"syntax_diagnostics\": {\n    \"status\": \"checked_and_none\",\n    \"availability\": \"fresh\",\n    \"materialized\": true,\n    \"source_path\": \"contextor/core/live_state/store.py\",\n    \"errors\": [],\n    \"total\": 0,\n    \"truncated\": false\n  },\n  \"warnings\": [\n    \"Target file on disk is out of sync with canonical state (revision 1454).\"\n  ]\n}"
        }
      ],
      "isError": false
    }
  },
  "after_1": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"file\": \"contextor/core/runtime_trace.py\",\n  \"status\": \"available\",\n  \"state_freshness\": {\n    \"canonical_state\": \"fresh\",\n    \"workspace_sync\": \"out_of_sync\",\n    \"canonical_revision\": 1454,\n    \"provenance\": \"snapshot\",\n    \"families\": {\n      \"module\": \"fresh\",\n      \"graph\": \"fresh\",\n      \"topology\": \"fresh\",\n      \"artifact_consumption\": \"fresh\",\n      \"cycles\": \"fresh\",\n      \"collisions\": \"fresh\",\n      \"lineage\": \"fresh\"\n    },\n    \"advisory_warning\": \"Target file on disk has been modified since canonical state revision was generated.\"\n  },\n  \"syntax_diagnostics\": {\n    \"status\": \"checked_and_none\",\n    \"availability\": \"fresh\",\n    \"materialized\": true,\n    \"source_path\": \"contextor/core/runtime_trace.py\",\n    \"errors\": [],\n    \"total\": 0,\n    \"truncated\": false\n  },\n  \"warnings\": [\n    \"Target file on disk is out of sync with canonical state (revision 1454).\"\n  ]\n}"
        }
      ],
      "isError": false
    }
  },
  "after_2": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"file\": \"tests/test_live_state_store.py\",\n  \"status\": \"available\",\n  \"state_freshness\": {\n    \"canonical_state\": \"fresh\",\n    \"workspace_sync\": \"out_of_sync\",\n    \"canonical_revision\": 1454,\n    \"provenance\": \"snapshot\",\n    \"families\": {\n      \"module\": \"fresh\",\n      \"graph\": \"fresh\",\n      \"topology\": \"fresh\",\n      \"artifact_consumption\": \"fresh\",\n      \"cycles\": \"fresh\",\n      \"collisions\": \"fresh\",\n      \"lineage\": \"fresh\"\n    },\n    \"advisory_warning\": \"Target file on disk has been modified since canonical state revision was generated.\"\n  },\n  \"syntax_diagnostics\": {\n    \"status\": \"checked_and_none\",\n    \"availability\": \"fresh\",\n    \"materialized\": true,\n    \"source_path\": \"tests/test_live_state_store.py\",\n    \"errors\": [],\n    \"total\": 0,\n    \"truncated\": false\n  },\n  \"warnings\": [\n    \"Target file on disk is out of sync with canonical state (revision 1454).\"\n  ]\n}"
        }
      ],
      "isError": false
    }
  },
  "after_3": {
    "status": "fulfilled",
    "value": {
      "content": [
        {
          "type": "text",
          "text": "{\n  \"file\": \"tests/test_runtime_trace.py\",\n  \"status\": \"available\",\n  \"state_freshness\": {\n    \"canonical_state\": \"fresh\",\n    \"workspace_sync\": \"out_of_sync\",\n    \"canonical_revision\": 1454,\n    \"provenance\": \"snapshot\",\n    \"families\": {\n      \"module\": \"fresh\",\n      \"graph\": \"fresh\",\n      \"topology\": \"fresh\",\n      \"artifact_consumption\": \"fresh\",\n      \"cycles\": \"fresh\",\n      \"collisions\": \"fresh\",\n      \"lineage\": \"fresh\"\n    },\n    \"advisory_warning\": \"Target file on disk has been modified since canonical state revision was generated.\"\n  },\n  \"syntax_diagnostics\": {\n    \"status\": \"checked_and_none\",\n    \"availability\": \"fresh\",\n    \"materialized\": true,\n    \"source_path\": \"tests/test_runtime_trace.py\",\n    \"errors\": [],\n    \"total\": 0,\n    \"truncated\": false\n  },\n  \"warnings\": [\n    \"Target file on disk is out of sync with canonical state (revision 1454).\"\n  ]\n}"
        }
      ],
      "isError": false
    }
  },
  "post_events": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"status\": \"no_live_service\",\n  \"repo_path\": \"C:\\\\Temp\\\\Contextor_Repo\",\n  \"events\": [],\n  \"total\": 0,\n  \"truncated\": false,\n  \"diagnostics_summary\": {\n    \"syntax_errors\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"name_collisions\": {\n      \"count\": 0,\n      \"critical\": null,\n      \"warning\": null,\n      \"info\": null,\n      \"availability\": \"fresh\"\n    },\n    \"cycles\": {\n      \"count\": 0,\n      \"availability\": \"fresh\"\n    },\n    \"attention_required\": false,\n    \"availability\": {\n      \"syntax_errors\": \"fresh\",\n      \"name_collisions\": \"fresh\",\n      \"cycles\": \"fresh\"\n    }\n  },\n  \"diagnostics_attention_required\": false\n}"
      }
    ],
    "isError": false
  }
}
```

## FULL_DIFFS / ACTUAL_DIFF


### contextor/core/live_state/store.py

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index a3ff5a1..db775d3 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -1379,6 +1379,34 @@ def save_snapshot(
                 pass
 
 
+def _trace_snapshot_load_phase(
+    component: str,
+    started: float,
+    *,
+    repo_id: str = "",
+    count: int | None = None,
+) -> None:
+    try:
+        from contextor.core.runtime_trace import trace_event
+
+        trace_event(
+            "LIVE",
+            "LIVE_SNAPSHOT_LOAD_PHASE",
+            repo_id=repo_id or None,
+            component=component,
+            elapsed_ms=round(
+                (time.monotonic() - started) * 1000.0,
+                3,
+            ),
+            count=count,
+            timing_semantics=(
+                "non_overlapping_load_snapshot_phase"
+            ),
+        )
+    except Exception:
+        pass
+
+
 def load_snapshot(
     cache_dir: str | Path,
     expected_state_id: str = "",
@@ -1389,7 +1417,14 @@ def load_snapshot(
     """Load one complete published snapshot, rejecting incompatible identities."""
 
     state_file, _, _ = _paths(cache_dir)
+
+    phase_started = time.monotonic()
     metadata = read_metadata(cache_dir)
+    _trace_snapshot_load_phase(
+        "metadata_read",
+        phase_started,
+        repo_id=expected_repo_id,
+    )
     normalized_root = (
         str(Path(expected_root_path).expanduser().resolve())
         if expected_root_path
@@ -1407,8 +1442,15 @@ def load_snapshot(
     if metadata.state_file:
         state_file = state_file.parent / metadata.state_file
     try:
+        phase_started = time.monotonic()
         with state_file.open("rb") as stream:
             payload = _SnapshotUnpickler(stream).load()
+        _trace_snapshot_load_phase(
+            "core_pickle_unpickle",
+            phase_started,
+            repo_id=expected_repo_id,
+        )
+
         if isinstance(payload, dict) and set(payload) == {"metadata", "state"}:
             embedded = payload["metadata"]
             embedded_metadata = LiveStateMetadata(
@@ -1459,12 +1501,19 @@ def load_snapshot(
                 ):
                     return None
 
+                phase_started = time.monotonic()
                 split_lineage = (
                     _load_split_lineage_generation(
                         cache_dir,
                         metadata,
                     )
                 )
+                _trace_snapshot_load_phase(
+                    "split_lineage_load",
+                    phase_started,
+                    repo_id=expected_repo_id,
+                    count=len(split_lineage),
+                )
 
                 try:
                     setattr(
@@ -1475,13 +1524,47 @@ def load_snapshot(
                 except AttributeError:
                     return None
 
-            state_obj = _normalize_lineage_query_index_state(
-                _normalize_lineage_facts_state(
-                    _normalize_symbol_call_facts(
-                        raw_state
+            phase_started = time.monotonic()
+            state_obj = _normalize_symbol_call_facts(
+                raw_state
+            )
+            _trace_snapshot_load_phase(
+                "normalize_symbol_call_facts",
+                phase_started,
+                repo_id=expected_repo_id,
+            )
+
+            phase_started = time.monotonic()
+            state_obj = _normalize_lineage_facts_state(
+                state_obj
+            )
+            _trace_snapshot_load_phase(
+                "normalize_lineage_facts_state",
+                phase_started,
+                repo_id=expected_repo_id,
+                count=len(
+                    getattr(
+                        state_obj,
+                        "lineage_facts_by_source",
+                        {},
                     )
+                    or {}
+                ),
+            )
+
+            phase_started = time.monotonic()
+            state_obj = (
+                _normalize_lineage_query_index_state(
+                    state_obj
                 )
             )
+            _trace_snapshot_load_phase(
+                "normalize_lineage_query_index_state",
+                phase_started,
+                repo_id=expected_repo_id,
+            )
+
+            phase_started = time.monotonic()
             state_revision = (
                 state_obj.get("revision") if isinstance(state_obj, dict)
                 else getattr(state_obj, "revision", None)
@@ -1586,6 +1669,12 @@ def load_snapshot(
                         setattr(state_obj, "shared_usage_clusters_state", "deferred")
                     except AttributeError:
                         pass
+
+            _trace_snapshot_load_phase(
+                "post_normalization_finalize",
+                phase_started,
+                repo_id=expected_repo_id,
+            )
             return state_obj, metadata
         if metadata.lineage_manifest_file:
             return None
```

### contextor/core/runtime_trace.py

```diff
diff --git a/contextor/core/runtime_trace.py b/contextor/core/runtime_trace.py
index 2ebfcaf..6f67f18 100644
--- a/contextor/core/runtime_trace.py
+++ b/contextor/core/runtime_trace.py
@@ -1683,6 +1683,7 @@ def _header_records(sid: str, started_at: str, desktop_pid: int, file_name: str)
     )
     records[4]["events"]["LIVE"].extend(
         [
+            "LIVE_SNAPSHOT_LOAD_PHASE",
             "LIVE_SERVICE_PRE_ENDPOINT_TIMING",
             "LIVE_DIAGNOSTIC_SYNTAX_ERROR",
             "LIVE_DIAGNOSTIC_SYNTAX_RECOVERED",
```

### tests/test_live_state_store.py

```diff
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 8aa692a..6400355 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -280,6 +280,95 @@ def test_exact_schema_13_splits_lineage_and_roundtrips(tmp_path):
     )
 
 
+def test_split_snapshot_load_emits_non_overlapping_phase_timings(tmp_path):
+    import contextor.core.runtime_trace as runtime_trace
+
+    state = _split_lineage_test_state(
+        "pkg/a.py",
+        "pkg/b.py",
+    )
+
+    save_snapshot(
+        state,
+        tmp_path,
+        "sid",
+        exact_revision=1,
+        repo_id="repo-test",
+        root_path=str(tmp_path),
+        file_state_payload={
+            "_meta": {
+                "state_id": "sid",
+                "revision": 1,
+            },
+            "files": {},
+        },
+    )
+
+    with runtime_trace.capture_trace_events() as events:
+        loaded = load_snapshot(
+            tmp_path,
+            "sid",
+            expected_repo_id="repo-test",
+            expected_root_path=str(tmp_path),
+        )
+
+    assert loaded is not None
+
+    phase_events = [
+        item
+        for item in events
+        if item.get("ev")
+        == "LIVE_SNAPSHOT_LOAD_PHASE"
+    ]
+
+    assert [
+        item["component"]
+        for item in phase_events
+    ] == [
+        "metadata_read",
+        "core_pickle_unpickle",
+        "split_lineage_load",
+        "normalize_symbol_call_facts",
+        "normalize_lineage_facts_state",
+        "normalize_lineage_query_index_state",
+        "post_normalization_finalize",
+    ]
+
+    assert all(
+        item["repo_id"] == "repo-test"
+        for item in phase_events
+    )
+
+    assert all(
+        isinstance(item["elapsed_ms"], (int, float))
+        and item["elapsed_ms"] >= 0
+        for item in phase_events
+    )
+
+    split_event = next(
+        item
+        for item in phase_events
+        if item["component"]
+        == "split_lineage_load"
+    )
+
+    lineage_normalize_event = next(
+        item
+        for item in phase_events
+        if item["component"]
+        == "normalize_lineage_facts_state"
+    )
+
+    assert split_event["count"] == 2
+    assert lineage_normalize_event["count"] == 2
+
+    assert all(
+        item["timing_semantics"]
+        == "non_overlapping_load_snapshot_phase"
+        for item in phase_events
+    )
+
+
 def test_exact_split_lineage_reuses_unchanged_source_chunks_by_identity(
     tmp_path,
 ):
```

### tests/test_runtime_trace.py

```diff
diff --git a/tests/test_runtime_trace.py b/tests/test_runtime_trace.py
index 1b1d4f0..226e47f 100644
--- a/tests/test_runtime_trace.py
+++ b/tests/test_runtime_trace.py
@@ -47,6 +47,7 @@ def test_desktop_trace_session_headers_and_finish(tmp_path, monkeypatch):
     assert not (tmp_path / "logs" / "contextor_runtime_active.json").exists()
     assert len(records[6]["err"]) == 500
     fields, events = records[1]["fields"], records[4]["events"]["LIVE"]
+    assert "LIVE_SNAPSHOT_LOAD_PHASE" in events
     assert {"attempt", "attempts", "attempts_used", "retry_delay", "runtime_domain_id", "repo_id", "endpoint_fingerprint", "service_pid", "lease_generation", "service_instance_id", "reason_code", "exception_class", "errno", "winerror", "error", "pid_alive", "endpoint_changed", "process_alive", "process_identity_matches", "endpoint_available", "endpoint_matches", "reason", "result", "side", "operation_or_request_type", "prior_endpoint_fingerprint", "prior_service_pid", "new_endpoint_fingerprint", "new_service_pid", "recovery_operation_id", "owner", "writer_kind"} <= set(fields)
     assert "ANALYSIS" in records[2]["domains"]
     assert {"LIVE_CONNECT_ATTEMPT", "LIVE_CONNECT_REJECT", "LIVE_CONNECT_RESULT", "LIVE_LIVENESS_RESULT", "LIVE_WATCHER_RECOVERY_START", "LIVE_WATCHER_RECOVERY_RESULT", "LIVE_IPC_FAILURE", "LIVE_SERVICE_THREAD_FAILURE"} <= set(events)
```

