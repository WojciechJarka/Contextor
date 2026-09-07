# Full reanalysis and REAL MCP/LIVE certification report

RUNTIME_FRESHNESS=FAIL

MCP_RUNTIME_CURRENT=UNVERIFIED/STALE. The active MCP source preview at canonical revision 134 exposed the corrected `visit_Assign` implementation with `function_depth == 0` plus `not class_stack`, and `workspace_sync=verified`; however, a subsequent `analyze_project` with `reused=false` completed and published successfully while still materializing the old 48-artifact target catalog. The active full-analysis path therefore did not produce corrected canonical facts.

LIVE_RUNTIME_CURRENT=UNVERIFIED/STALE. LIVE accepted the full-analysis publication at revision 135, but the published target state still contains all nine class-body false globals. This is sufficient to fail closed; it does not distinguish stale imported MCP code from stale symbol-facts/cache hydration.

CANONICAL_REVISION_BEFORE_FULL_ANALYSIS=134

CANONICAL_REVISION_AFTER_FULL_ANALYSIS=135

FULL_ANALYSIS_STATUS=COMPLETED_BUT_RUNTIME_FRESHNESS_FAILED. Job `4897245c0fed4e15a9e52cba9ed1ca8d` reported `status=completed`, `live_publish_status=success`, `live_publish_revision=135`, zero skipped Python files, and zero syntax errors. `get_live_events(after_revision=134)` reported a continuous `mcp_analysis` publish at revision 135 with `resync_required=false`.

PROVENANCE=live

RESYNC_REQUIRED=false

ARTIFACT_CONSUMPTION_STATE=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

GRAPH_STATE=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

TARGET_ARTIFACT_COUNT_BEFORE=48

TARGET_ARTIFACT_COUNT_AFTER=48

TARGET_FALSE_GLOBALS_ABSENT=NO. Post-publication canonical projection returned all 9/9 names: `artifact_data_identity`, `artifact_keys`, `clusters`, `complete`, `max_cluster_size`, `min_cluster_size`, `min_jaccard`, `raw_artifact_keys`, `scope`.

TARGET_REAL_GLOBALS_PRESERVED=YES. Post-publication canonical projection still contained `_CALL_USAGE_CHANNELS`, `_IMPORT_USAGE_CHANNELS`, `_INHERITANCE_USAGE_CHANNELS`, `_LAYER_RULES`, and `__all__`.

CLASS_ARTIFACT_PRESERVED=YES. `SharedUsageClustersHandoff` remained present as `kind=class`.

CLASS_FIELD_ARTIFACTS_CREATED=NO_NEW_BUT_EXISTING_FALSE_GLOBALS_REMAINED

MODULE_BLAST_COUNT_TOTAL=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

MODULE_BLAST_COUNT_RETURNED=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

MODULE_BLAST_ZERO_TRUNCATION=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

MODULE_BLAST_DEFAULT_BYTES=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

MODULE_BLAST_TIMES_MS=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

MODULE_BLAST_MEDIAN_MS=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

GLOBAL_COUNT_BEFORE_DISCOVERY=661

FALSE_CLASS_GLOBALS_BEFORE_DISCOVERY=342

GLOBAL_COUNT_AFTER=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

CLASS_SCOPE_FALSE_GLOBALS_REMAINING=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE. The target projection proves the defect remains in the published canonical state; repo-wide recount was intentionally not continued after the freshness gate failed.

EXPECTED_319_MATCH=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

TARGET_FALSE_IDENTITIES_ACTIVE=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

TARGET_FALSE_IDENTITIES_RECOVERY_ONLY=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

REAL_GLOBAL_IDENTITIES_ACTIVE=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

LIVE_NATURAL_EDIT=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

LIVE_PRE_REVISION=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

LIVE_ADD_REVISION=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

LIVE_REMOVE_REVISION=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

LIVE_CLASS_FIELD_REINTRODUCED=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

LIVE_CLEANUP_COMPLETE=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

CANONICAL_CATALOG_COUNT=48 at revision 135

BLAST_RADIUS_CATALOG_COUNT=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

CATALOG_PROJECTIONS_AGREE=UNVERIFIED_STOPPED_AFTER_RUNTIME_STALE

DECISION=RUNTIME_STALE

FILES_CHANGED=NONE

FULL_SUITE_RUN_BY_AGENT=NO

## Freshness gate and stop reason

The disk source and MCP source preview are current, but the required stronger proof is absent: the real MCP full-analysis owner was run after the fix and published a fresh LIVE revision, yet the canonical target remained exactly at the pre-fix count 48 and retained every known class-body false global. No blast-radius certification, registry certification, repo-wide post-reanalysis recount, or natural LIVE edit was executed after this contradiction. No pytest was run.

The next permitted action requires resolving the MCP/LIVE freshness problem (restart/reload the MCP server and ensure symbol-facts/cache hydration cannot reuse the pre-fix classification), then rerunning full analysis before any certification. No code, tests, or docs were changed in this certification turn; only this report was written.
