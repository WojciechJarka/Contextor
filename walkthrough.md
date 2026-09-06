# Runtime performance certification — `search_source`

## Runtime freshness and deployed implementation

The directly running Contextor MCP returned the current `SourceSpanResolver` implementation containing all three resolver-local line indexes:

```text
comments_by_line
strings_by_line
statements_by_line
```

The fetched running-MCP implementation also shows `resolve(line_no, column)` selecting candidates with the three `.get(line_no, ())` maps while retaining `_contains`, the existing `min(...)` keys, precedence, and fallback.

LIVE evidence at certification:

```text
CANONICAL_REVISION=257
PROVENANCE=live
CANONICAL_STATE=fresh
WORKSPACE_SYNC=verified
RESYNC_REQUIRED=false
RESYNC_REASON=null
LATEST_REVISION=257
```

## Exact real-MCP benchmark

Request:

```text
search_source(
    repo_path="C:\\Temp\\Contextor_Repo",
    search_term="def ",
    limit=20,
    case_sensitive=false,
    allow_large_output=false
)
```

One discarded warm-up plus three sequential identical real MCP calls:

```text
DISCARDED_WARMUP_MS=15487
RUNS_MS=13625,13014,12805
MEDIAN_MS=13014
RESPONSE_BYTES=14808
RESPONSE_SHA256=fd5f97b387d9f7518608d6b40aeb51e3e89051aa11f67191ae9c9ba38298b270
RESPONSE_PARITY=EXACT: all warm responses, including discarded warm-up, were byte-identical
TOTAL_MATCHES=3908
FULL_OUTPUT_BYTES=45419
RETURNED_COUNT=5
AUTO_BOUNDED=true
CANONICAL_REVISION=257
PROVENANCE=live
RESYNC_REQUIRED=false
```

## Baseline comparison and parity

```text
BASELINE_MEDIAN_MS=14546
POST_CHANGE_MEDIAN_MS=13014
IMPROVEMENT_MS=1532
IMPROVEMENT_PERCENT=10.53%
```

The entire returned JSON is byte-identical to the approved baseline:

```text
total_matches=3908
response_bytes=14808
sha256=fd5f97b387d9f7518608d6b40aeb51e3e89051aa11f67191ae9c9ba38298b270
full_output_bytes=45419
returned_count=5
auto_bounded=true
ordering/spans/match_kind/text/line_maps unchanged
```

## Remaining latency interpretation

The line index removes the previously measured repeated per-occurrence full-collection scans and delivers a material real-MCP improvement with exact parity. The remaining roughly 13 seconds still includes per-file `SourceSpanResolver.__init__` work (tokenization, AST parse, and construction of the required semantic facts) across the canonical source set.

The approved lazy-construction experiment saved only about 179 ms / 1.3%, so it is not a remaining optimization path to revisit. No persistent AST/source cache was added, and no further refactor was designed or profiled in this certification turn. Raw source reads remain the already-approved single-read-per-candidate path; no new removable owner is established by this runtime cohort.

## Decision

```text
DECISION=FINAL_PASS
MCP_RESTART_REQUIRED=NO
LIVE_RESTART_REQUIRED=NO
RUNTIME_PERFORMANCE_CERTIFICATION_PENDING=NO
FILES_CHANGED=NONE
DIFFS=NONE
FULL_SUITE_RUN_BY_AGENT=NO
```
