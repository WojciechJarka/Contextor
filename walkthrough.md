# Contextor MCP latency discovery: `extract_indexed_report_context`

Discovery/profiling only. No production code, tests, report/cache, or LIVE state changed; `update_file` was not called. MCP is present in current deferred-tool inventory.

## Current runtime contract and request

Current MCP docs define:
```text
repo_path:string required; query:string required (artifact/module ID, .py path, module::symbol, or explicit prefix)
report_path:string default ""; resolve_indices:bool default true; public_api_only:bool default false
max_items:int|null default 20; fields:string[]|null default null; evidence_limit:int|null default 3
representation:string|null default null; named|indexed|auto take precedence when non-null
```
Behavior: index-first GUI-shared resolution; ambiguous/missing identities explicit; active plus recovery dictionaries; nested-evidence bounds/retry descriptors; read-only. Auto negotiates response size.

Exact deterministic representative normal indexed request:
```json
{"repo_path":"C:\\Temp\\Contextor_Repo","query":"contextor/mcp/tools/extract_indexed_report_context.py","report_path":"","resolve_indices":false,"public_api_only":false,"max_items":20,"fields":null,"evidence_limit":3,"representation":"indexed"}
```
It produced exact file match / module ID `266/1`, 12 complete artifact blocks, selection + diagnostics + expand, `truncated=false`, `representation=indexed`, `resolve_via=lookup_index_entries`.

## Freshness and real MCP benchmark

Before and after: canonical revision=246; activity_epoch=d2ba45aff622421c9a47ea3367543769; continuity=continuous; resync_required=false; no events after revision 246. Default report: `output/Contextor_Repo_artifacts_compact.json`, 116,520 bytes.

```text
discarded warm-up=271 ms
warm raw wall=[192,199,219] ms
median=199 ms
response bytes=[7121,7121,7121]
exact output parity=PASS (including discarded warm-up)
```
This is below historical screening median ~2112 ms. Real MCP wall remains authority.

## Dataflow

```text
MCP wrapper -> extract_indexed_report_context
 -> canonical report path/is_file -> one read_text + json.loads
 -> get_or_init_engine (LIVE ping/current engine)
 -> engine.state.modules -> in-memory module_paths
 -> catalog_from_registry -> new PersistentIdentityRegistry/read transaction
 -> catalog_from_registry_state
 -> query_indexed_report -> bound blocks/consumer evidence
 -> rewrite_selected_indices(resolve_names=false) -> projection/expand -> json.dumps
```

Explicit indexed representation performs one indexed rewrite, no named->indexed->named roundtrip. public_api_only=false, so no filter. Engine paths bypass `discover_module_paths()`, hence no repo-wide scan.

## Child attribution

Controlled warmed in-process profile only (not real MCP authority); profiled total 676 ms is perturbed. Nested inclusive timings below are not additive.

```text
BOUNDARY=MCP wrapper/self
RUNS_MS=[192,199,219] real MCP
MEDIAN_MS=199
COUNT_PER_CALL=1
INCLUSIVE_OR_SELF=real end-to-end inclusive
DISK_IO=telemetry only
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=canonical MCP surface
REDUNDANCY_PROOF=none

BOUNDARY=report/file resolution
RUNS_MS=not isolated
MEDIAN_MS=N/A
COUNT_PER_CALL=1 selection + 1 is_file
INCLUSIVE_OR_SELF=self/setup
DISK_IO=path/stat
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=canonical
REDUNDANCY_PROOF=required identity/fail-closed validation

BOUNDARY=physical report read + JSON parse
RUNS_MS=not isolated
MEDIAN_MS=N/A
COUNT_PER_CALL=1 read_text + 1 json.loads
INCLUSIVE_OR_SELF=extractor inclusive
DISK_IO=yes, 116520-byte report
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=canonical materialization
REDUNDANCY_PROOF=none; exactly one read and no proven equivalent partial accessor

BOUNDARY=get_or_init_engine
RUNS_MS=[13] profiler
MEDIAN_MS=13 attribution only
COUNT_PER_CALL=1
INCLUSIVE_OR_SELF=inclusive
DISK_IO=LIVE ping
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=LIVE engine; observed provenance=live, revision=246
REDUNDANCY_PROOF=none; current/freshness owner

BOUNDARY=index dictionary/catalog acquisition
RUNS_MS=profiler catalog=[537]; direct baseline=[120.040,122.775,126.894]
MEDIAN_MS=122.775 direct harness
COUNT_PER_CALL=1 catalog; 1 PersistentIdentityRegistry; 14 registry _load_json; 18 aggregate json.loads
INCLUSIVE_OR_SELF=catalog inclusive; catalog_from_registry_state=[13] profiler
DISK_IO=yes, second registry read
REPO_WIDE=no; engine paths bypass discover_module_paths
CANONICAL_OR_RECOMPUTED=canonical catalog recomputed from second registry
REDUNDANCY_PROOF=Experiment A has exact output and byte parity using engine.registry + existing catalog_from_registry_state

BOUNDARY=indexed ID resolution
RUNS_MS=[96] profiler
MEDIAN_MS=96 attribution only
COUNT_PER_CALL=1 query_indexed_report
INCLUSIVE_OR_SELF=inclusive
DISK_IO=no additional read shown
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=index-first GUI-shared resolver
REDUNDANCY_PROOF=none; required exact resolution/diagnostics

BOUNDARY=requested-context extraction/bounds/projection
RUNS_MS=_build_candidate_response=[6], rewrite_selected_indices=[10] profiler
MEDIAN_MS=N/A (nested inclusive)
COUNT_PER_CALL=12 selected blocks; rewrite=1
INCLUSIVE_OR_SELF=nested inclusive
DISK_IO=no
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=public bounds/order/truncation semantics
REDUNDANCY_PROOF=none

BOUNDARY=serialization
RUNS_MS=[15] profiler
MEDIAN_MS=15 attribution only
COUNT_PER_CALL=1 json.dumps
INCLUSIVE_OR_SELF=inclusive
DISK_IO=no
REPO_WIDE=no
CANONICAL_OR_RECOMPUTED=public serialization
REDUNDANCY_PROOF=none
```

`query_helpers.read_registries()` is not on this path. No duplicate compact-report read: one report read; the separate persistent registry acquisition is the duplicate identity source.

## Experiments (no production patch)

A — reusing fresh `engine.registry`: harness acquired current LIVE engine, temporarily used existing `catalog_from_registry_state(engine.registry._state,module_paths)`, then restored original behavior.

```text
engine=live revision=246
baseline direct=[120.040,122.775,126.894] ms; median=122.775
A direct=[32.088,27.470,29.848] ms; median=29.848
recoverable direct median=92.926 ms
exact parity: PASS across 3 baseline + 3 A outputs
byte parity: PASS, 7121 bytes
```

This proves a new PersistentIdentityRegistry plus 14 JSON loads occurs despite fresh engine registry, while the existing canonical projection is semantically equivalent in this runtime. Production must retain catalog_from_registry fallback when no usable current engine/registry exists, and retain report/index consistency, recovery, and fail-closed behavior.

B — skip discovery: no candidate; engine module paths already avoid `discover_module_paths()` / `rglob("*.py")`.
C — reuse report parse: no candidate; report is read/parsed once.
D — partial accessor: no experiment/no redundancy claim; no accessor was proven to preserve full blocks, resolution, diagnostics, ordering, bounds, recovery, and fail-closed validation.

## Decision

DECISION=GO_OPTIMIZE

Removable parity-proven direct owner: 92.926 ms, about 46.7% of real MCP median 199 ms, exceeding >=5% gate. Existing equivalent canonical path exists. Expected recoverable real wall-clock is an estimate only: up to ~93 ms; it is not post-patch evidence. After any patch rerun this exact request, exact-byte parity, LIVE revision/continuity/resync, and absent/stale-engine fallback tests.

FILES_CHANGED=NONE

DIFFS=NONE

FULL_SUITE_RUN_BY_AGENT=NO

