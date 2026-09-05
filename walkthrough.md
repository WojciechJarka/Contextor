# Contextor MCP latency discovery: get_artifact_blast_radius

## Scope

- Discovery/profiling only: no production source, tests, MCP state, or watcher behavior changed.
- Desktop LIVE watcher remained authoritative; `update_file` was not called.
- Contextor MCP supplied contract, ownership, dataflow, source spans, and LIVE proof. Text search only verified concrete paths.
- Historical screen (median about 2285 ms, response about 925 B) is comparison only; all results below are current.

## Exact current runtime public contract

Runtime docs: version `1.0.0`, tool `get_artifact_blast_radius`.

| Parameter | Contract |
|---|---|
| `repo_path` | required canonical repository root |
| `artifact_name` | optional string (default empty); active artifact ID, full canonical identity, or leaf symbol |
| `artifact` | alias for `artifact_name`; both must match when supplied |
| `max_items` | integer or null; default 30 |
| `compact` | boolean; default true |
| `fields` | optional top-level projection |
| `representation` | `named`, `indexed`, or `auto`; default named |

Resolution: exact active artifact ID; canonical LIVE full identity/unique leaf; module redirect; bounded fuzzy suggestions; legacy not-found. Direct consumers are confirmed static symbol consumers; downstream reachability is conservative module-level reachability seeded from direct consumer modules. Freshness reports canonical state, workspace sync, revision, provenance, family flags, and warning.

## Reproduced request and LIVE proof

The historical 925-byte response identifies the representative request:

```text
get_artifact_blast_radius(
  repo_path="C:\\Temp\\Contextor_Repo",
  artifact_name="main",
  compact=true,
  max_items=10,
  representation="named",
)
```

It deterministically returns ambiguity for seven canonical `main` artifacts. Current response is exactly 925 ASCII/UTF-8 bytes.

```text
canonical_revision=243
provenance=live
canonical_state=fresh
workspace_sync=verified (successful artifact responses)
families.module=graph=topology=artifact_consumption=cycles=collisions=fresh
get_live_events(after_revision=243): continuity=continuous; resync_required=false
```

## Real MCP benchmark (authority)

One warm-up was discarded; three following calls were sequential and identical.

| Call | Wall time | Response bytes | Exact response parity |
|---|---:|---:|---|
| discarded warm-up | 3720 ms | 925 B | baseline |
| warm 1 | 3960 ms | 925 B | yes |
| warm 2 | 5989 ms | 925 B | yes |
| warm 3 | 10348 ms | 925 B | yes |
| median warm | **5989 ms** | **925 B** | **exact** |

Current runtime is slower than the historical screen; no historical conclusion was reused as current evidence.

## Exact dataflow

```text
MCP wrapper/decorator
  -> get_artifact_blast_radius
     -> normalize/validate representation and aliases
     -> query_helpers.read_registries(root)
        -> new PersistentIdentityRegistry(root), transaction, module/artifact maps
     -> mcp_runtime.get_or_init_engine(root)
        -> current desktop LIVE engine/state
     -> scan engine.state.artifacts
        -> canonical_symbol_catalog
        -> canonical_symbol_consumers
     -> seven main matches -> deterministic candidate sort -> ambiguity serialization
```

This ambiguity return occurs before architecture aggregation, reachability, `calculate_affected_set`, catalog/module-path fallback, consumer representation conversion, and `fields` projection.

## Child attribution

No runtime child timings are exposed. A controlled read-only in-process harness was used only for attribution: same direct function request, one discarded warm-up, then three warm calls. It did not modify source or persisted state. Direct function core JSON is 388 characters; MCP adds the diagnostics envelope seen in the real 925-B response. Baseline/experiments are exact hash-equal: `a3c42fae6ee647a4a462f1a73841b8fd12fc3d0f336532a7dd833c98a30de66b`.

Nested/inclusive timings are not summed.

```text
BOUNDARY=MCP wrapper/self
RUNS_MS=real 3960,5989,10348; direct 1596.116,2216.203,2278.471
MEDIAN_MS=5989 real; 2216.203 direct
COUNT_PER_CALL=1
INCLUSIVE_OR_SELF=real inclusive; wrapper self unavailable
DISK_IO=not separately exposed
REPO_WIDE=yes
CANONICAL_OR_RECOMPUTED=canonical LIVE request path
REDUNDANCY_PROOF=not asserted

BOUNDARY=read_registries -> fresh PersistentIdentityRegistry transaction
RUNS_MS=1382.146,2011.658,2065.153
MEDIAN_MS=2011.658
COUNT_PER_CALL=1
INCLUSIVE_OR_SELF=self child timing
DISK_IO=yes
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=re-reads registry maps despite fresh engine.registry in same request
REDUNDANCY_PROOF=Experiment A exact parity using current engine.registry maps

BOUNDARY=get_or_init_engine
RUNS_MS=7.271,9.746,9.090
MEDIAN_MS=9.090
COUNT_PER_CALL=1 baseline; 2 in simple Experiment-A harness replacement
INCLUSIVE_OR_SELF=self child timing
DISK_IO=not observed fresh; may consult LIVE session/journal metadata
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=current LIVE engine acquisition
REDUNDANCY_PROOF=not removable; owns freshness/current state

BOUNDARY=canonical artifact scan / target identity resolution
RUNS_MS=catalog helper sums 10.282,17.129,12.277; contained in direct total
MEDIAN_MS=12.277 helper-only
COUNT_PER_CALL=330 catalogs; 7 main matches
INCLUSIVE_OR_SELF=scan contained in parent; child numbers not additive
DISK_IO=no observed
REPO_WIDE=yes
CANONICAL_OR_RECOMPUTED=canonical LIVE artifacts, no AST/source reconstruction
REDUNDANCY_PROOF=not asserted: unqualified leaf requires ambiguity detection

BOUNDARY=canonical artifact-consumer lookup
RUNS_MS=187.771,168.250,184.068 inclusive sums
MEDIAN_MS=184.068
COUNT_PER_CALL=7
INCLUSIVE_OR_SELF=inclusive sum; not additive
DISK_IO=no
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=canonical artifact_consumption maps
REDUNDANCY_PROOF=discarded on ambiguity; Experiment D exact parity, but below GO threshold

BOUNDARY=direct consumer projection / sorting / bounding
RUNS_MS=not separately exposed
MEDIAN_MS=not separately exposed
COUNT_PER_CALL=0 consumer representation conversions; candidate sort once
INCLUSIVE_OR_SELF=contained in direct total
DISK_IO=no
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=canonical candidate identities
REDUNDANCY_PROOF=consumer projection not reached; deterministic sort required

BOUNDARY=reachability/transitive traversal and reverse adjacency
RUNS_MS=0 calls
MEDIAN_MS=0
COUNT_PER_CALL=0 calculate_affected_set
INCLUSIVE_OR_SELF=not reached
DISK_IO=no
REPO_WIDE=no execution
CANONICAL_OR_RECOMPUTED=would use current dependency graph for unique artifact
REDUNDANCY_PROOF=not applicable; traversal is not called redundant

BOUNDARY=catalog_from_registry/discover_module_paths fallback
RUNS_MS=0 calls
MEDIAN_MS=0
COUNT_PER_CALL=0
INCLUSIVE_OR_SELF=not reached
DISK_IO=not reached
REPO_WIDE=not reached
CANONICAL_OR_RECOMPUTED=legacy/module-diagnosis fallback
REDUNDANCY_PROOF=not applicable to successful-live ambiguity path

BOUNDARY=serialization/representation
RUNS_MS=not separately exposed
MEDIAN_MS=not separately exposed
COUNT_PER_CALL=1 JSON serialization; 0 named/indexed consumer conversions
INCLUSIVE_OR_SELF=contained in direct total
DISK_IO=no
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=one final serialization
REDUNDANCY_PROOF=no duplicate conversion observed
```

## Experiments (no production patch)

### A. Reuse fresh engine.registry

Harness-only replacement returned module/artifact `path_to_id` and `id_to_path` maps from the current `engine.registry._state` instead of calling `read_registries`. It retained current LIVE engine acquisition.

| Variant | Warm 1 | Warm 2 | Warm 3 | Median | Exact parity |
|---|---:|---:|---:|---:|---|
| direct baseline | 1304.304 | 2342.586 | 2037.102 | 2037.102 ms | baseline |
| A: current engine registry | 179.761 | 210.660 | 210.553 | 210.553 ms | yes |

Output parity: same SHA-256 and 388 chars. Direct-harness recovery is **1826.549 ms** median. The existing order performs a disk-backed registry acquisition before obtaining the current engine that already owns an equivalent active registry. This removable owner exceeds 300 ms and 5% of the real 5989-ms MCP median.

Implementation constraint: obtain/validate usable non-resync engine first; use its registry maps only then; retain independent-registry/recovery behavior when no engine is available and preserve exact ID/currentness failure behavior.

### B. Catalog/module-path discovery

Not mutated: ownership proves `catalog_from_registry()` and fallback module-path discovery are not reached after seven canonical LIVE matches. No recovery claim.

### C. Reverse adjacency/reachability reuse

Not mutated: ambiguity returns before traversal. No evidence permits calling required unique-artifact graph walking redundant.

### D. Defer consumer lookup until uniqueness

Harness-only replacement omitted the seven pre-ambiguity consumer values, which are discarded before output.

| Variant | Warm 1 | Warm 2 | Warm 3 | Median | Exact parity |
|---|---:|---:|---:|---:|---|
| direct baseline | 2011.104 | 2061.320 | 2054.592 | 2054.592 ms | baseline |
| D: omit discarded lookups | 1877.433 | 2120.145 | 2406.055 | 2120.145 ms | yes |

Although attribution is about 184 ms, end-to-end harness results are noisy and do not show a median recovery. D is below both GO thresholds alone; it may be considered only after A, never as the target itself.

## Conclusion

Approved candidate: **A, reuse fresh engine registry**. It preserves current LIVE ownership, IDs, ambiguity candidates, ordering, limits, named representation, and exact output for this request while removing a duplicate disk-backed registry read.

Expected recoverable wall-clock is bounded evidence, not a promise: **about 1.83 s direct-harness median**. Real MCP remains authority; re-run the real MCP benchmark after any production change because wrapper/transport variance means harness child time cannot be subtracted exactly from real wall clock.

```text
DECISION=GO_OPTIMIZE
FILES_CHANGED=NONE
DIFFS=NONE
FULL_SUITE_RUN_BY_AGENT=NO
```
