# Runtime performance certification: `extract_indexed_report_context`

DECISION=FINAL_PASS

## Runtime freshness and LIVE evidence

The deferred Contextor MCP tools are present and the deployed documentation identifies `extract_indexed_report_context` as `[OPTIMIZED]`. The running tool accepted the exact requested indexed query and returned the fresh active identity `module_id=266/1` for the target path.

CANONICAL_REVISION=252
PROVENANCE=NOT_EXPOSED_BY_PUBLIC_RUNTIME_SURFACE
RESYNC_REQUIRED=false
LIVE_EVIDENCE=After the restart epoch `3156833e30514c96805e21d6df55f64e`, a current-cursor `get_live_events(after_revision=252)` response reported `continuity=continuous`, `resync_required=false`, and `activity_resync_required=false`.

The initial request with the pre-restart cursor `251` correctly reported `event_retention_gap`; it was not used as fresh-LIVE evidence. The current canonical cursor was then used and is continuous.

No runtime child trace fields were exposed by the public tool surface. Consequently the following ownership counts are unavailable rather than inferred:

```text
get_or_init_engine=NOT_EXPOSED
engine.registry.read_transaction=NOT_EXPOSED
catalog_from_registry fallback=NOT_EXPOSED
```

## Exact real-MCP benchmark

Exact request:

```json
{
  "repo_path":"C:\\Temp\\Contextor_Repo",
  "query":"contextor/mcp/tools/extract_indexed_report_context.py",
  "report_path":"",
  "resolve_indices":false,
  "public_api_only":false,
  "max_items":20,
  "fields":null,
  "evidence_limit":3,
  "representation":"indexed"
}
```

One discarded warm-up was followed by three sequential, identical calls. An earlier measurement-collector attempt failed after completing calls but before it could retain its results; it is discarded and not used below. The valid certification cohort is the warm-up plus the three calls reported here.

```text
RUNS_MS=181,444,180
MEDIAN_MS=181
RESPONSE_BYTES=7121
RESPONSE_PARITY=EXACT: all three complete response strings were identical; each is ASCII-only JSON, so character length equals UTF-8 byte length (7121).
CANONICAL_REVISION=252
PROVENANCE=NOT_EXPOSED_BY_PUBLIC_RUNTIME_SURFACE
RESYNC_REQUIRED=false
IMPROVEMENT_MS=18
IMPROVEMENT_PERCENT=9.05%
```

The one 444 ms observation is an outlier, but the requested median is 181 ms: 18 ms (9.05%) below the 199 ms baseline, so there is no median latency regression.

## Exact semantic and byte parity

```text
module_id=266/1
artifact_count=12
total_artifact_count=12
truncated=false
representation=indexed
resolve_via=lookup_index_entries
response_bytes=7121
```

MCP_RESTART_REQUIRED=NO
LIVE_RESTART_REQUIRED=NO
RUNTIME_PERFORMANCE_CERTIFICATION_PENDING=NO
FILES_CHANGED=NONE
DIFFS=NONE
FULL_SUITE_RUN_BY_AGENT=NO
