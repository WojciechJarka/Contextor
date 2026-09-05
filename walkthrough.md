# Runtime performance certification — get_file_edit_context(mode=minimal)

DECISION=FINAL_PASS

## Runtime freshness evidence

Certification used the running Contextor MCP tool only, not source from disk and not a direct Python call. The live endpoint served the current minimal in-memory decision projection at revision 237 and completed the discarded warm-up plus three identical calls in 479–511 ms. This is materially inconsistent with the pre-fast-path baseline of 5.5–8.3 s and confirms the running MCP has the accepted minimal fast path loaded.

The public runtime does not expose child-level transaction counters or an implementation/version hash. It therefore cannot independently expose the internal `read/write` transaction-mode field or distinguish the catalog helper's read scope. Their ownership-count proof remains the focused regression authority; no artificial runtime instrumentation was added. The observed endpoint behavior is compatible with the loaded fast path and has no catalog/discovery-scale delay.

## Canonical LIVE health

`get_module_context(contextor.cli)` returned:

```text
canonical_state=fresh
workspace_sync=verified
canonical_revision=237
provenance=live
families=module, graph, topology, artifact_consumption, cycles, collisions: fresh
```

Canonical engine health is therefore fresh LIVE at revision 237; no engine `resync_required` condition was reported by the canonical query. `get_live_events(after_revision=236)` separately reported `continuity=gap` and `resync_reason=event_retention_gap`. This is an event-stream retention condition, not evidence of canonical-engine resync.

## Real MCP benchmark

Request (identical to baseline):

```json
{"repo_path":"C:\\Temp\\Contextor_Repo","file_path":"contextor\\cli.py","mode":"minimal","max_items":10,"compact":true}
```

One warm-up was discarded, followed by three real MCP calls.

```text
BASELINE_RUNS_MS=8294, 5489, 5667
BASELINE_MEDIAN_MS=5667
BASELINE_RESPONSE_BYTES=1338

RUNS_MS=479, 502, 511
MEDIAN_MS=502
RESPONSE_BYTES=1338
RESPONSE_PARITY=true
CANONICAL_REVISION=237
PROVENANCE=live
RESYNC_REQUIRED=false (canonical engine)
```

Median improvement: `5165 ms` (`91.14%` faster).

Semantic parity was checked against the baseline contract: `resolved_as=module`, `module=contextor.cli`, `module_id=135/1`, `file=contextor/cli.py`, `layer=cli`, direct/transitive consumers `1/2` with sample `contextor.__main__`, `tests_covering=0`, and `warnings=[]`. The response was not shortened to obtain the performance result.

## Ownership counts

```text
read_transaction count=not exposed by running runtime trace
mutating registry transaction count=not exposed by running runtime trace
discover_module_paths count=not exposed by running runtime trace
```

No synthetic runtime patching was used. Focused tests remain the authority for the previously verified fresh-minimal invariants: one read transaction, zero mutating transactions, zero discovery calls, and response parity.

MCP_RESTART_REQUIRED=NO

LIVE_RESTART_REQUIRED=NO

RUNTIME_PERFORMANCE_CERTIFICATION_PENDING=NO

FILES_CHANGED=NONE

DIFFS=NONE

FULL_SUITE_RUN_BY_AGENT=NO
