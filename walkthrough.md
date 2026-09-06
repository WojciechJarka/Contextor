# lookup_artifact_by_symbol — runtime performance certification

## Runtime freshness / LIVE evidence

The restarted MCP runtime exposes current documentation marked [OPTIMIZED]. The served request completed through live_canonical_state.

    LIVE_STATUS=ok
    LIVE_ACTIVITY_EPOCH=c7274cbd4f27422f9b694cdb56a2f2bb
    LIVE_EVENT_CONTINUITY=continuous
    LIVE_EVENTS_RESYNC_REQUIRED=false
    CANONICAL_STATE=fresh
    WORKSPACE_SYNC=unverified (expected documented repo-wide lookup behavior)
    CANONICAL_REVISION=5
    PROVENANCE=live
    RESYNC_REQUIRED=false

The live-event query used after_revision=5 and yielded continuous state with resync_required=false. The lookup response independently reports fresh canonical state, live provenance, revision 5, and all required freshness families fresh.

## Real MCP benchmark

Exact request:

    {"repo_path":"C:\\Temp\\Contextor_Repo","symbol_name":"contextor.__main__::main","limit":20,"evidence_limit":20,"compact":true}

One discarded warm-up, then three identical real MCP calls:

    DISCARDED_WARMUP_MS=1110
    RUNS_MS=195,185,342
    MEDIAN_MS=195
    RESPONSE_BYTES=1370,1370,1370
    RESPONSE_PARITY=true (exact complete bytes across all three measured calls)
    ARTIFACT_ID=A2968/1
    FULL_IDENTITY=contextor.__main__::main
    CONSUMER_EVIDENCE=total=1,truncated=false,evidence=[main]
    CANONICAL_REVISION=5
    PROVENANCE=live
    RESYNC_REQUIRED=false

## Baseline comparison

    BASELINE_MEDIAN_MS=739
    CURRENT_MEDIAN_MS=195
    IMPROVEMENT_MS=544
    IMPROVEMENT_PERCENT=73.61
    BASELINE_RESPONSE_BYTES=1370
    CURRENT_RESPONSE_BYTES=1370

Current artifact ID remains A2968/1, so identity continuity is direct; no ID-remapping qualification is needed.

## Semantic and response parity

    EXACT_ONE_SUCCESSFUL_ARTIFACT=true
    FULL_IDENTITY_MATCH=true
    STATUS_MATCH=true
    ORDERING_MATCH=true
    CONSUMER_EVIDENCE_MATCH=true
    COMPACT_EVIDENCE_SEMANTICS_MATCH=true
    FRESHNESS_OUTPUT_SHAPE_MATCH=true
    RESPONSE_BYTES_MATCH_BASELINE=true

Complete response bytes are exactly equal among the three current measured calls. Baseline-to-current full-byte equality is not asserted because canonical revision legitimately advanced from 3 to 5; response shape and all requested lookup semantics are preserved.

No runtime trace exposed child counters, so no instrumentation was performed. Focused regression tests remain the ownership authority:

    GET_OR_INIT_ENGINE=1
    ENGINE_REGISTRY_READ_TRANSACTION=1
    READ_REGISTRIES=0
    SOURCE_READS=0
    AST_PARSES=0

## Decision

    DECISION=FINAL_PASS
    RATIONALE=fresh LIVE runtime, complete semantic parity, byte-stable measured responses, and 544 ms / 73.61% median improvement versus authority baseline.
    MCP_RESTART_REQUIRED=NO
    LIVE_RESTART_REQUIRED=NO
    RUNTIME_PERFORMANCE_CERTIFICATION_PENDING=NO
    FILES_CHANGED=NONE
    DIFFS=NONE
    FULL_SUITE_RUN_BY_AGENT=NO
