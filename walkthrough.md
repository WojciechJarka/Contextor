# lookup_artifact_by_symbol — discovery/profiling only

## Scope and authority

- Production code was not changed.
- Contextor was present in the deferred-tool inventory and explicitly made available before investigation.
- Ownership/dataflow are from Contextor MCP documentation and the current runtime source; `rg` was used only to verify exact implementation locations.
- Historical screening median: approximately 1636 ms. This fresh-LIVE run is not a cross-process comparison claim.

## Current runtime contract

`lookup_artifact_by_symbol(repo_path, symbol_name="", limit=20, evidence_limit=20, compact=true, fields=null, symbol=null)` accepts an active artifact ID, full canonical `module::symbol`, or leaf symbol. `symbol` aliases `symbol_name`; both must agree if supplied. Exact matches are preferred, and consumer evidence is bounded.

```ini
data_source=live_canonical_state
canonical_state=fresh
workspace_sync=unverified (expected for repo-wide registry lookup)
canonical_revision=3
provenance=live
resync_required=false
artifact_consumption=fresh
```

Representative deterministic request, chosen from a canonical projection:

```json
{"repo_path":"C:\\Temp\\Contextor_Repo","symbol_name":"contextor.__main__::main","limit":20,"evidence_limit":20,"compact":true}
```

It took the normal successful path and returned one nonempty artifact: `A2968/1`, `contextor.__main__::main`, with one consumer (`main`). Response: 1370 UTF-8 bytes.

## Exact current dataflow

1. MCP wrapper dispatches to `contextor/mcp/tools/lookup_artifact_by_symbol.py:9`.
2. It resolves the path; trims `symbol_name` and alias `symbol`; rejects conflicting aliases; selects the effective query.
3. Before engine acquisition it calls `query_helpers.read_registries(root)` (`:42`): a new `PersistentIdentityRegistry` read transaction returns four maps.
4. It calls `mcp_runtime.get_or_init_engine(root)`, rejecting unavailable/resync-required state.
5. It case-folds the query and scans sorted `state.artifacts` module-by-module (`:48-62`), checking module truth and calling `canonical_symbol_catalog`.
6. It sorts candidates, prefers exact leaf matches, preserves ambiguity behavior, and only after a scan miss uses `resolve_artifact_identity` with the registry maps. Not-found/similar/ambiguous behavior remains at `:78-137`.
7. It bounds results and projects fresh canonical consumer evidence. Compact mode limits displayed evidence to three; non-compact retains the requested bounded list (`:142-185`).
8. It builds the named artifact object, freshness envelope, optional top-level field projection, and indented JSON (`:187-206`).

No `catalog_from_registry` or `discover_module_paths` call occurs. No named/indexed conversion occurs; the tool emits the named artifact object directly.

## Real MCP benchmark (authority)

One discarded warm-up plus three identical real MCP calls:

```makefile
WARMUP_WALL_MS=663
RUNS_MS=596,753,739
MEDIAN_MS=739
RESPONSE_BYTES=1370,1370,1370
EXACT_FULL_RESPONSE_PARITY=true
```

All returned identical complete JSON. Real-MCP median (739 ms) is the authority.

## Controlled in-process attribution

No child timings were exposed by the runtime, so a read-only harness attributed the already-initialized fresh LIVE Python tool path. It modified only process-local wrappers/counters; no production file, cache, or server state changed. Engine: `PersistentIdentityRegistry` with loaded `_state`, `provenance=live`, `resync_required=false`.

```makefile
HARNESS_WARMUP_MS=492.237
HARNESS_RUNS_MS=486.418,478.666,465.409
HARNESS_MEDIAN_MS=478.666
REGISTRY_READS=1
CATALOG_BUILDS=334
DISCOVER_MODULE_PATHS_CALLS=0
ARTIFACT_SCAN_COUNT=1
ARTIFACTS_SCANNED=332
SOURCE_READS=0
AST_PARSES=0
```

`CATALOG_BUILDS` means `canonical_symbol_catalog` calls (one per scanned module plus target validation), not `catalog_from_registry` materialization. Required fresh-path source/AST counters are zero.

```makefile
BOUNDARY=wrapper/self excluding measured children
RUNS_MS=~44,~48,~36
MEDIAN_MS=~44
COUNT_PER_CALL=1
INCLUSIVE_OR_SELF=self
DISK_IO=no direct source IO
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=canonical envelope/projection/serialization
REDUNDANCY_PROOF=not established

BOUNDARY=read_registries -> new PersistentIdentityRegistry read transaction
RUNS_MS=406.848,394.732,398.553
MEDIAN_MS=398.553
COUNT_PER_CALL=1
INCLUSIVE_OR_SELF=inclusive
DISK_IO=yes (registry read)
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=recomputed duplicate of available fresh LIVE registry state
REDUNDANCY_PROOF=fresh engine.registry._state produces byte-identical maps/output in Experiment A

BOUNDARY=full artifact scan + canonical_symbol_catalog
RUNS_MS=12.098,12.908,9.021
MEDIAN_MS=12.098
COUNT_PER_CALL=334 catalogs; one scan
INCLUSIVE_OR_SELF=inclusive summed child time
DISK_IO=no
REPO_WIDE=yes (332 modules)
CANONICAL_OR_RECOMPUTED=recomputed per-module symbol catalogs
REDUNDANCY_PROOF=exact full identity is registry-resolvable, but no production-equivalent direct-index branch was implemented in this diagnostic

BOUNDARY=canonical consumer resolution
RUNS_MS=23.118,22.811,19.759
MEDIAN_MS=22.811
COUNT_PER_CALL=1
INCLUSIVE_OR_SELF=inclusive
DISK_IO=no
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=canonical fresh consumption facts
REDUNDANCY_PROOF=not established; required output evidence
```

Do not sum nested inclusive times. Harness median differs from real wall because real MCP also includes transport/server scheduling.

## Diagnostic experiments (no production patch)

### A. Reuse fresh engine.registry

Only the harness's separate `read_registries(root)` was replaced with `registry_maps_from_state(engine.registry._state)`. Preconditions were live provenance, fresh state, no resync, `PersistentIdentityRegistry`, and loaded dictionary state. Any future implementation must retain the existing disk-read fallback for unavailable/non-LIVE/resync/missing-registry state.

```makefile
EXPERIMENT=A_fresh_engine_registry_maps
WARMUP_MS=64.961
RUNS_MS=67.289,66.890,66.825
MEDIAN_MS=66.890
BASELINE_MEDIAN_MS=478.666
DELTA_MS=411.776
REGISTRY_READS=0
CATALOG_BUILDS=334
ARTIFACTS_SCANNED=332
SOURCE_READS=0
AST_PARSES=0
EXACT_FULL_OUTPUT_PARITY=true
SAME_ARTIFACT_ID=true
SAME_FULL_IDENTITY=true
SAME_STATUS=true
SAME_ORDERING=true
SAME_REPRESENTATION=true
REMOVABLE_OWNER=separate PersistentIdentityRegistry/read_registries acquisition
```

Both sources represent the same loaded registry generation in the measured fresh-LIVE state. The removable 411.776 ms attribution delta exceeds 300 ms and 5% of 739 ms real-MCP median.

### B/C/D assessment

- B: not applicable; `catalog_from_registry` and `discover_module_paths` counters are zero.
- C: full scan is a secondary candidate for exact identity lookups, but its 12.098 ms attribution is below threshold; no standalone experiment/recommendation now.
- D: two trims plus one casefold are negligible; named response is produced once. No duplicate named/indexed conversion or removable normalization/projection owner was observed.

## Removable vs unavoidable wall and decision

Removable now: duplicate persistent-registry acquisition before the fresh LIVE engine lookup. Not established removable: real MCP transport/scheduling, required fresh consumer evidence, envelope/serialization, and small scan/catalog work.

```makefile
DECISION=GO_OPTIMIZE
RATIONALE=fresh-LIVE registry reuse has exact full-output parity and removes 411.776 ms median in controlled attribution; exceeds 300 ms and 5% real MCP wall.
FILES_CHANGED=NONE
DIFFS=NONE
FULL_SUITE_RUN_BY_AGENT=NO
```
