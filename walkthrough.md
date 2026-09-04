# F2F0 — final contract and implementation handoff for `get_symbol_call_context`

## Status

`F2E get_symbol_implementation` is FINAL PASS. The performance branch remains closed (`NO_GO_FULL_ANALYSIS_OPTIMAL`); this work does not reopen lifecycle, materialization, or performance.

The endpoint already exists in the current LIVE runtime. At canonical revision `209`, provenance `live`, it returned fresh canonical/module truth and verified target-file freshness. A bounded query for `contextor.mcp.tools.get_symbol_call_context::get_symbol_call_context` found 27 canonical direct callee facts; with `max_items=5` it truthfully reported `total_edges=27`, `returned_edges=5`, and `truncated=true`. This is a contract-certification/design task, not a new graph implementation.

## Canonical authority

| Owner / producer | Canonical data | Contract sufficiency |
| --- | --- | --- |
| `contextor/core/domain/usage_facts.py` → `ModuleUsageFacts` | persisted immutable `symbol_calls` and `symbol_calls_materialized` | Sufficient. Wire format preserves `caller`, `callee`, `line`, `call_kind`; bit distinguishes empty truth from unavailable truth. |
| `contextor/core/reference/engine.py` → `extract_module_usage_facts` | production visitor emits qualified `(caller, callee, line, "direct")` tuples | Sufficient for static intra-module direct calls. |
| `contextor/core/analysis/incremental/materialization.py` → `ensure_module_usages` | incremental/history backfill | Sufficient; do not modify without a demonstrated F2F0 regression. |
| `module_current_truth` and `query_helpers.build_state_freshness` | currentness, revision, provenance, file-sync envelope | Sufficient for LIVE fail-closed behavior. Target-local fingerprinting is not a repository scan nor AST parse. |
| active artifact registry / `resolve_artifact_identity` | existing persistent IDs and canonical qualified identities | Sufficient for exact resolution and indexed output; no new identity layer is justified. |

The following information is absent by design and must never be inferred: inter-module call edges, dynamic/reflection dispatch, receiver/type resolution, arguments, column/end ranges, and richer call kinds. The present producer emits `call_kind="direct"`; the endpoint must not claim callback, event, async, dynamic, or polymorphic facts.

## Final contract

### Request and identity resolution

```text
get_symbol_call_context(
  repo_path: str,
  symbol: str,
  direction: "callers" | "callees" | "both" = "both",
  depth: int = 1,                    # exact integer 1..3; bool rejected
  max_items: positive int | null = 20,
  representation: "named" | "indexed" | "auto" = "auto",
  allow_large_output: bool = false,
)
```

`symbol` is an exact `module::symbol` identity or active artifact ID (`A…` or lowercase `a…`). Plain leaves are rejected even if globally unique. Resolve syntactic artifact IDs before engine lookup. A missing ID returns exact `not_found` with no fuzzy recovery. A qualified textual miss may return at most five current/materialized/queryable suggestions, but they are suggestion-only and never start traversal. Ambiguity never guesses a root.

Invalid request values return controlled `exact_qualified_symbol_required`, `invalid_direction`, `invalid_depth`, `invalid_max_items`, `invalid_representation`, or `invalid_allow_large_output` responses and no edges.

### Traversal and cycles

Response scope is explicitly `intra_module`. `callees` follows facts where `caller` is in the frontier; `callers` follows facts where `callee` is in the frontier; `both` performs both walks independently and takes their deduplicated union.

Use deterministic BFS. Sort candidate facts by `(caller, callee, line, call_kind)`, keep `seen_nodes` and `seen_edges`, and stop after depth 1–3. This terminates cycles. An edge is `{caller, callee, line, call_kind, depth}`; its deduplication identity excludes `depth`, and a shared `both` edge retains the lower depth. Final union ordering is `(depth, caller, callee, line, call_kind)`.

`max_items` is a global deterministic prefix across both directions, never a per-side budget. `null` returns all relevant edges from the already materialized module graph before output-size protection. The current finite module tuple, depth cap, and output limits are the only supported bounds. Do not add a pretend CPU/work cap without separately defining truthful partial-traversal semantics.

The query reads canonical `module_usages[module].symbol_calls`. It performs no `ast.parse`, source search, report parsing, or query-time AST/graph reconstruction. A target-local freshness fingerprint may read/hash that one target file, solely to provide `workspace_sync`; documentation must say “no repository scan and no source-derived call reconstruction,” not “no source read.”

### Freshness and failure

Require available `module_current_truth`, the target module in `module_usages`, and `symbol_calls_materialized=true` before walking.

* unavailable engine/resync: `canonical_live_state_unavailable`, no edges;
* stale/unavailable module: `status="stale"`, `available=false`, truth diagnostics, no edges;
* unmaterialized facts: `symbol_calls_unmaterialized`, `available=false`, no edges;
* known symbol with a materialized empty tuple: `status="ok"`, zero totals and empty collections.

Every successful response includes module-scoped `state_freshness`: canonical state, workspace sync, revision, provenance, family availability, and advisory warning. Disk `out_of_sync` or `metadata_match` is advisory here: the graph remains explicitly T0 canonical evidence, never an invented T1 answer.

### Response, representation, and output bounds

```json
{
  "status": "ok",
  "symbol": "pkg.mod::handler",
  "module": "pkg.mod",
  "direction": "both",
  "depth": 1,
  "representation": "named",
  "requested_representation": "auto",
  "scope": "intra_module",
  "total_edges": 17,
  "returned_edges": 10,
  "truncated": true,
  "callers": {"total": 8, "truncated": true, "items": []},
  "callees": {"total": 9, "truncated": false, "items": []},
  "expand": {"same_query_with": {"max_items": 20}},
  "data_source": "live_canonical_module_usages_symbol_calls",
  "state_freshness": {},
  "representation_decision": {}
}
```

`indexed` replaces endpoint identities with existing artifact IDs and adds `resolver: {index_kind: "artifact", resolve_via: "lookup_index_entries"}`. If an endpoint lacks an ID, explicit indexed fails `indexed_identity_unavailable`; do not mint IDs. `auto` selects indexed only when serialized saving is at least 512 bytes. Named candidates strictly over 51,200 bytes require indexed identities; without them return `large_named_output_requires_indexed_identities`.

Choose representation before output protection. Preflight exact selected JSON at 15,360 UTF-8 bytes. Without `allow_large_output`, return the largest deterministic fitting edge prefix with `_output.auto_bounded=true`, `full_output_bytes`, `requested_count`, `returned_count`, and retry details. If one edge cannot fit, return compact confirmation metadata with no edges. With `allow_large_output=true`, return the complete selected candidate. Totals and all truncation flags remain truthful.

Current implementation and dedicated tests already cover directions, deterministic depth 2/3 BFS, dedupe, invalid inputs, stale/unmaterialized versus materialized-empty, ID resolution/fuzzy containment, named/indexed/auto boundaries, 15,360-byte prefixing, and no AST/source-derived reconstruction.

## Recommendation

Adopt this as the final F2F0 contract. Do not redesign graph traversal, producer, incremental materialization, or performance code. The only identified narrow audit target is a documentation/test wording mismatch: `build_state_freshness` may hash the target file, so a promise of “no source read” would be inaccurate; it must instead preserve the stronger relevant promise of no repository scan and no source-derived call reconstruction.

No production or test file changed in this task. The only dirty files observed are watcher runtime logs, untouched here. Therefore there is no production/test unified diff to include.

## First prompt for the external implementation agent

```text
Implement only the narrow F2F0 contract-certification patch in C:\\Temp\\Contextor_Repo. Do not change lifecycle, incremental materialization, reference-engine extraction, performance code, or traversal/representation/output algorithms unless a focused failing test proves a defect.

Use Contextor MCP first for the ownership/dataflow of `get_symbol_call_context`, `ModuleUsageFacts`, and `query_helpers.build_state_freshness`; use grep only for exact textual verification. Do not use MCP `update_file`. Let the active Desktop LIVE watcher publish edits and verify watcher continuity/no resync afterwards. Do not restart MCP yourself: if a loaded MCP runtime/schema file changes, report `MCP_RESTART_REQUIRED=YES`, `LIVE_RESTART_REQUIRED=NO`, and `RUNTIME_CERTIFICATION_NOT_YET_PERFORMED=YES` after local validation.

Keep the public contract exactly: exact qualified identity or active artifact ID; callers/callees/both; deterministic BFS depth 1..3; global `max_items`; current named/indexed/auto policy; 15,360-byte output protection; no AST parse, source search, report parse, or query-time call reconstruction. Preserve all fail-closed gates and suggestion-only fuzzy behavior.

Audit docs and tests against actual `query_helpers.build_state_freshness`. It can perform O(1) target-file fingerprint/hash work for `workspace_sync`, while traversal reads only materialized canonical facts. If wording/tests prohibit that allowed freshness check by promising “no source read,” narrowly replace it with “no repository scan and no source-derived call reconstruction.” Do not weaken the no-`ast.parse` or no-reconstruction guarantee. If no mismatch exists, make no production change and report the contract is already conformant.

If a test is needed, add it only in `tests/mcp/tools/test_get_symbol_call_context.py` and retain `tests/mcp/tools/__init__.py`. It should make `ast.parse` and any call-fact reconstruction path fail, then prove a materialized graph remains queryable; it must not prohibit the documented target-local fingerprint helper. Run only the focused changed module(s), plus `tests/test_get_symbol_call_context.py` if shared behavior changes.

Before an independent GitHub audit after changes, say exactly: `Zakomituj aktualny stan repo i daj znać.` and wait. At task end overwrite root `walkthrough.md`, include exact pytest summary and a COMPLETE RAW UNIFIED DIFF (`git diff --no-ext-diff --unified=80 --`) for every changed production/test file, omit the walkthrough’s own diff, and send no chat progress or summary.
```
