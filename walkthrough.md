# Contextor get_module_context post-restart runtime certification

## Walkthrough

VERDICT=RUNTIME_PASS
RUNTIME_FRESHNESS=PASS
MCP_TOOL_COUNT=25
GET_MODULE_CONTEXT_CALLABLE=YES
CANONICAL_STATE_USABLE=YES
R0=4440
R1=4440
CANONICAL_MUTATION_FROM_QUERY=NO

FIRST_CALL_MS=27760
MIN_MS=107
MEDIAN_MS=131
P95_MS=348
MAX_MS=27760
WARM_MEDIAN_MS=131
INDIVIDUAL_MS=[27760,131,137,122,107,139,109,110,165,115,121,348,133,179,130,144,143,117,128,136]
BEFORE_MEDIAN_MS=4339
PERFORMANCE_IMPROVEMENT_FACTOR=33.1x
REPEATED_COLD_REBUILD_PATTERN=NO

RESPONSE_SEMANTIC_VALID=YES
DIAGNOSTICS_SUMMARY_PRESENT=YES
LIVE_ERROR_DETECTED=NO
OWNER_TEMPORARILY_UNREACHABLE=NO
ACTIVITY_GAP_CAUSED_BY_BENCHMARK=NO
ACTIVITY_SEQUENCE_AFTER=24
POST_QUERY_CONTINUITY=continuous
POST_QUERY_RESYNC_REQUIRED=false

The first call exercised the restarted runtime's cold state and took 27.760 seconds. Calls 2-20 remained between 107 and 348 ms, with no recurring multi-second rebuild pattern. The baseline observation before timing reported an existing retention gap/resync_required=true at after_revision=0; the post-benchmark cursor at revision 4440 was continuous with resync_required=false, so no new gap was caused by this benchmark.

FILES_CHANGED=NONE
TESTS_RUN=NONE
MANUAL_RESTART_REQUIRED=NO (restart was already performed by the user before certification)

