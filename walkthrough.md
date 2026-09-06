# `get_symbol_call_context` runtime performance certification

## Running MCP / LIVE evidence

```text
RUNTIME_MCP_DOC_VERSION=1.0.0
LIVE_LATEST_REVISION=259
LIVE_RESYNC_REQUIRED=false
RESPONSE_CANONICAL_STATE=fresh
RESPONSE_WORKSPACE_SYNC=verified
RESPONSE_CANONICAL_REVISION=259
RESPONSE_PROVENANCE=live
RESPONSE_ADVISORY_WARNING=null
DATA_SOURCE=live_canonical_module_usages_symbol_calls
```

The post-restart deployed runtime is materially faster than the pre-change authority baseline, which is runtime evidence that the fresh-LIVE identity-projection path is deployed. The public runtime response/trace does not expose internal counters, so `get_or_init_engine=1`, `engine.registry.read_transaction=1`, and `read_registries=0` remain supported by the focused regression rather than independently observable from this real-MCP call. No instrumentation was added.

## Exact benchmark request

```json
{"repo_path":"C:\\Temp\\Contextor_Repo","symbol":"contextor.mcp.tools.get_symbol_call_context::_ordered_union","direction":"both","depth":3,"max_items":100,"representation":"auto","allow_large_output":true}
```

One discarded warm-up plus three identical real MCP calls:

```text
WARMUP_MS=1745
RUNS_MS=183,186,162
MEDIAN_MS=183
RESPONSE_BYTES=1893,1893,1893
RESPONSE_PARITY=YES (exact full payload across the three measured responses)
CANONICAL_REVISION=259
PROVENANCE=live
RESYNC_REQUIRED=false
IMPROVEMENT_MS=1183 (1366 - 183)
IMPROVEMENT_PERCENT=86.60%
```

## Semantic comparison

Stable post-restart semantics across all three responses:

```text
symbol=contextor.mcp.tools.get_symbol_call_context::_ordered_union
depth=3
direction=both
edges=3/3
representation=named
named_bytes=1336
indexed_bytes=1120
bytes_saved=216
truncated=false
data_source=live canonical symbol_calls
caller=get_symbol_call_context -> _ordered_union @ line 330
callees=_ordered_union -> _identity @ lines 94,100
```

Topology, direction/depth, representation selection, edge count, ordering, and truncation match the baseline. However, this is **not** complete required semantic parity with the supplied baseline:

```text
BASELINE_LINES=329;93,99
POST_RESTART_LINES=330;94,100
BASELINE_NAMED_INDEXED_BYTES=1335;1119
POST_RESTART_NAMED_INDEXED_BYTES=1336;1120
```

The one-byte response/candidate change is stable across all post-restart responses and is not caused by dynamic freshness fields: all three have identical fresh envelope values at revision 259. It follows the shifted canonical call-evidence line numbers (the last callee changed `99 -> 100`), so it cannot be dismissed as the permitted new-revision freshness-envelope variation.

## Source / AST counters

The public runtime response and trace do not expose `SOURCE_READS` or `AST_PARSES`; therefore real-MCP values are `NOT_EXPOSED`, not asserted. No instrumentation was added. The running contract continues to state that this query performs no source-derived call reconstruction or `ast.parse`, but that is contract evidence rather than a runtime counter.

```text
SOURCE_READS=NOT_EXPOSED_BY_PUBLIC_RUNTIME_TRACE
AST_PARSES=NOT_EXPOSED_BY_PUBLIC_RUNTIME_TRACE
```

## Decision

```text
DECISION=FIX_REQUIRED
REASON=real deployed response changes public caller/callee line evidence and representation candidate byte fields; this is not a dynamic freshness-only delta
PERFORMANCE_RESULT=materially improved real-MCP median (1366 -> 183 ms)
MCP_RESTART_REQUIRED=NO
LIVE_RESTART_REQUIRED=NO
RUNTIME_PERFORMANCE_CERTIFICATION_PENDING=NO
FILES_CHANGED=NONE
DIFFS=NONE
FULL_SUITE_RUN_BY_AGENT=NO
```
