# get_module_blast_radius — REAL MCP runtime certification

Zakres: wyłącznie read-only runtime certification. Nie zmieniano production code, tests ani docs. Runtime calls used active Contextor MCP tools, not direct-process substitution. Nie uruchamiano pytest.

RUNTIME_FRESHNESS=PASS; active Contextor MCP returned the current lossless implementation and current docs.
ACTIVE_TOOL_COUNT=26; verified by active get_mcp_documentation() tool registry.
PUBLIC_SIGNATURE=PASS; docs/runtime contract exactly (repo_path: str, module: str = '', compact: bool = True, fields: list[str] | None = None, representation: str = 'auto', allow_large_output: bool = False) -> str; no max_artifacts/max_consumers/max_items.
RUNTIME_DOCS_CURRENT=PASS; active docs contain complete/lossless contract, complete_compact, persistent module+artifact IDs, and 64 KiB local ceiling.
CANONICAL_REVISION=125
PROVENANCE=live
RESYNC_REQUIRED=false
MODULE_TRUTH=fresh; get_module_context returned live canonical topology with export_degree=48 and workspace_sync=verified.
ARTIFACT_CONSUMPTION_STATE=fresh
GRAPH_STATE=fresh/available; state_freshness.families.graph=fresh and aggregate downstream available=true.
CACHED_ANALYTICS_STATE=fresh/available for the target module; per-artifact architecture and downstream layer classification were available. The project-level optional hotspot/debt summaries remain deferred, but did not make target module classification unavailable.

DEFAULT_STATUS=success
DEFAULT_SCHEMA=module_blast_radius.lossless.v1
DEFAULT_REPRESENTATION=indexed
ARTIFACT_COUNT_TOTAL=48
ARTIFACT_COUNT_RETURNED=48
ALL_ARTIFACTS_PRESENT=PASS; 48 serialized entries, canonical catalog total=48 and complete_symbol_catalog=true.
TRUNCATED_COLLECTIONS=NONE; no true truncated flag in the default payload.
FOLLOWUP_ARTIFACT_CALLS_REQUIRED=NO; complete per-artifact blast facts are in the single module projection.
DEFAULT_BYTES=45642 UTF-8 bytes (raw active MCP response).

MODULE_INDEX_VALID=PASS; all 143 module_index values are canonical persistent numeric IDs and all resolved active through one lookup_index_entries call.
ARTIFACT_IDS_CANONICAL=PASS; every artifact key equals entry.artifact_id, every ID is canonical A<number>/<generation>, and no module::symbol substitutes an artifact ID.
SET_REFS_VALID=PASS; all refs point into sets and sets[0]=[].
LOCAL_ORDINALS_VALID=PASS; every set ordinal is an integer within module_index bounds.
MODULE_LAYERS_DECODABLE=PASS; module_layers codes length matches module_index and every code resolves deterministically through dictionary.

PER_ARTIFACT_PARITY_compute_cached_analytics=PASS on identity, kind/signature, complete direct consumers, downstream total, architecture/layer classification, bounded production/test evidence, evidence_scope and freshness. The artifact tool contract exposes only bounded downstream samples (even with max_items=null), so a second full downstream identity-list comparison is UNVERIFIED_BY_ARTIFACT_TOOL_CONTRACT; the module payload itself contains the complete set.
PER_ARTIFACT_PARITY_compute_dependency_matrix_from_state=PASS on the same comparable fields; full downstream identity-list comparison is UNVERIFIED_BY_ARTIFACT_TOOL_CONTRACT for the same reason.
PER_ARTIFACT_PARITY___all__=PASS on the same comparable fields; zero direct/downstream and classification parity matched; full downstream identity-list comparison is UNVERIFIED_BY_ARTIFACT_TOOL_CONTRACT for the same reason.

AGGREGATE_DIRECT_COUNT=17
AGGREGATE_DOWNSTREAM_COUNT=126
AGGREGATE_INTERSECTION_SIZE=0
CONSUMED_ARTIFACT_COUNT=24
UNCONSUMED_ARTIFACT_COUNT=24
TOP10_HIGHEST_IMPACT=["A2642/1","A2087/1","A2018/1","A582/1","A1880/1","A29/1","A640/1","A2996/1","A2881/1","A1965/1"]
AGGREGATE_DISJOINT=PASS; decoded direct and downstream sets are disjoint.

AUTO_COMPACT_TRUE=PASS; default auto+compact=true returned complete lossless indexed output without confirmation_required or representation_decision_required.
AUTO_COMPACT_FALSE=PASS; auto+compact=false with allow_large_output=true returned full named 48/48 output.
EXPLICIT_INDEXED=PASS; indexed lossless 48/48 output.
EXPLICIT_NAMED_GUARD=PASS/EXPECTED; without allow_large_output returned confirmation_required (estimated_output_bytes=222886), which is allowed by the contract.
FIELDS_MODULE_NO_ORPHAN_TABLES=PASS; indexed fields=[module] returned only module and no schema/module_index/module_layers/sets.
FIELDS_AGGREGATE_DECODABLE=PASS; indexed fields=[aggregate] retained schema, representation, module_index (143), module_layers and sets (29; sets[0]=[]).

REAL_MCP_TIMES_MS=[1271,1307,1424] after one discarded warm-up
REAL_MCP_MEDIAN_MS=1307

SOURCE_READS=UNVERIFIED_BY_RUNTIME_TELEMETRY; active tool docs explicitly state no source/AST query-time reads, but no read counter is exposed.
AST_PARSES=UNVERIFIED_BY_RUNTIME_TELEMETRY
REPORT_FILE_READS=UNVERIFIED_BY_RUNTIME_TELEMETRY
REGISTRY_READ_PATH=canonical active registry/read-only snapshot observed by current live result; exact transaction count is UNVERIFIED without instrumentation.
INTERNAL_ARTIFACT_TOOL_N_PLUS_ONE=UNVERIFIED_BY_RUNTIME_TELEMETRY; active docs state no internal get_artifact_blast_radius calls, but runtime exposes no internal-call counter.

DECISION=FINAL_PASS
FILES_CHANGED=NONE
FULL_SUITE_RUN_BY_AGENT=NO
