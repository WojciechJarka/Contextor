# REAL MCP/LIVE full reanalysis and runtime certification

RUNTIME_FRESHNESS=PASS. The active MCP returned live canonical state at revision 139. The Desktop/LIVE event stream was continuous, with no resync requirement.

MCP_RUNTIME_CURRENT=PASS. A real, non-reused repository-wide MCP analysis completed after the restart.

DESKTOP_LIVE_RUNTIME_CURRENT=PASS. The Desktop watcher had published the corrected state at revision 138 before the MCP analysis; the subsequent MCP publish advanced the same LIVE state to revision 139.

SYMBOL_FACTS_SCHEMA_VERSION=2

CANONICAL_REVISION_BEFORE=138

CANONICAL_REVISION_AFTER=139

FULL_ANALYSIS_STATUS=completed. job_id=b7cc27261fb946dbb2985570ef7b852b; reused=false; skipped_python_files=0; syntax_error_count=0.

LIVE_PUBLISH_STATUS=success. live_publish_revision=139.

PROVENANCE=live

RESYNC_REQUIRED=false

TARGET_SYMBOL_FACTS_SCHEMA_AFTER=2. The normal indexing path produced schema 2 for the target before the full run; the corrected canonical state was then published by the real MCP analysis.

OLD_SCHEMA1_CACHE_REUSED=NO. Semantic schema validation rejects schema 1 after the version bump and recomputes the facts. The public runtime does not expose a per-file cache-hit counter.

TARGET_ARTIFACT_COUNT_BEFORE=48

TARGET_ARTIFACT_COUNT_AFTER=39

TARGET_FALSE_GLOBALS_ABSENT=YES (9/9). Absent names: artifact_data_identity, artifact_keys, clusters, complete, max_cluster_size, min_cluster_size, min_jaccard, raw_artifact_keys, scope.

TARGET_REAL_GLOBALS_PRESERVED=YES (5/5): _CALL_USAGE_CHANNELS, _IMPORT_USAGE_CHANNELS, _INHERITANCE_USAGE_CHANNELS, _LAYER_RULES, __all__.

CLASS_ARTIFACT_PRESERVED=YES. SharedUsageClustersHandoff remains a canonical class artifact.

CLASS_FIELD_ARTIFACTS_CREATED=NO.

GLOBAL_COUNT_BEFORE_DISCOVERY=661

FALSE_CLASS_GLOBALS_BEFORE_DISCOVERY=342

GLOBAL_COUNT_AFTER=319. Canonical projection query filtered to kind=global returned total_matches=319.

CLASS_SCOPE_FALSE_GLOBALS_REMAINING=0. The corrected extractor classification was used by the full repository analysis; the canonical global total is the expected 319.

EXPECTED_319_MATCH=YES

TARGET_FALSE_IDENTITIES_ACTIVE=NO (0/9). Exact active-registry lookup returned not_found for all nine former false identities.

TARGET_FALSE_IDENTITIES_RECOVERY_ONLY=YES (9/9). Recovery identities: A247/1 artifact_keys; A266/1 complete; A651/1 min_jaccard; A678/1 scope; A2321/1 clusters; A2438/1 artifact_data_identity; A2462/1 max_cluster_size; A2520/1 min_cluster_size; A3401/1 raw_artifact_keys.

REAL_GLOBAL_IDENTITIES_ACTIVE=YES (5/5). Active IDs: A1983/1 _CALL_USAGE_CHANNELS; A1457/1 _IMPORT_USAGE_CHANNELS; A638/1 _INHERITANCE_USAGE_CHANNELS; A394/1 _LAYER_RULES; A945/1 __all__.

CANONICAL_CATALOG_COUNT=39. Canonical LIVE artifacts projection for contextor.core.reporting_engine.graph_analytics returned 39/39 without truncation.

GET_ARTIFACTS_FOR_MODULE_COUNT=39. The direct module projection returned artifact_count=39, total_artifact_count=39, truncated=false, complete_symbol_catalog=true, data_source=live_symbol_state.

MODULE_BLAST_COUNT_TOTAL=39

MODULE_BLAST_COUNT_RETURNED=39

CATALOG_PROJECTIONS_AGREE=YES. Canonical catalog, get_artifacts_for_module, and get_module_blast_radius all reported 39 artifacts.

MODULE_BLAST_ZERO_TRUNCATION=YES. The default lossless indexed result had complete per-artifact output and no truncated consumer sets.

MODULE_BLAST_DEFAULT_BYTES=39260 UTF-8 bytes.

MODULE_BLAST_TIMES_MS=1119, 1082, 1033. One discarded warm-up preceded exactly three identical measured real MCP calls. No per-artifact follow-up calls were made.

MODULE_BLAST_MEDIAN_MS=1082

MODULE_BLAST_AGGREGATE=direct=17; downstream=126; direct/downstream intersection=0; consumed=24; unconsumed=15.

LIVE_NATURAL_EDIT=UNVERIFIED. No disposable watcher fixture was identified through canonical edit context; the available candidate is a tracked test module and modifying tracked production/test source would violate this read-only certification scope. No production file was edited.

LIVE_PRE_REVISION=UNVERIFIED_NOT_RUN

LIVE_ADD_REVISION=UNVERIFIED_NOT_RUN

LIVE_REMOVE_REVISION=UNVERIFIED_NOT_RUN

LIVE_CLASS_FIELD_REINTRODUCED=UNVERIFIED_NOT_RUN

LIVE_CLEANUP_COMPLETE=NOT_APPLICABLE

DECISION=FINAL_PASS. All runtime, canonical-count, registry-cleanup, projection-consistency, and blast-radius gates passed. Natural watcher edit was independently marked UNVERIFIED because no safe disposable fixture was available, as permitted by the certification contract.

FILES_CHANGED=NONE

FULL_SUITE_RUN_BY_AGENT=NO

CERTIFICATION_SCOPE=No production code, tests, docs, caches, or MCP projections were modified in this certification turn. No pytest command was run in this turn.
