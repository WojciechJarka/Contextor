# ISSUE 2 / STAGE A — legacy `symbol_calls` backfill

## Summary

Implemented an explicit per-`ModuleUsageFacts` compatibility marker: `symbol_calls_materialized`. New/full/incremental extraction produces `True` even when `symbol_calls == ()`; legacy instances and legacy dictionaries without the stored marker resolve to `False`. Empty data is therefore never used as a proxy for missing materialization.

The existing incremental materialization owner now rebuilds only missing usage slices and slices whose marker is absent/false, using `extract_module_usage_facts`. LIVE startup invokes this narrow backfill after loading a snapshot and persists it once. A subsequent startup sees materialized markers and performs no repeat backfill or snapshot write.

The previous `_LegacySymbolCallFact` unpickling compatibility remains intact. Its normalization now also preserves whether the marker was genuinely stored; compatibility objects never enter canonical state.

## Implementation

- `contextor/core/domain/usage_facts.py`: added the persisted marker, legacy-instance false behavior, and dictionary round-trip support. Default `True` makes all current producers materialized, including valid empty graphs.
- `contextor/core/analysis/incremental/materialization.py`: added a materialization-needed predicate and extended `ensure_module_usages` to rebuild missing or explicitly legacy slices only.
- `contextor/core/live_state/store.py`: retained legacy class-to-tuple migration and carried the real stored marker through normalization; marker absence remains false.
- `contextor/core/live_state/runtime.py`: normal LIVE startup performs and atomically saves the narrow legacy backfill before publishing canonical state.
- `tests/test_symbol_call_facts.py`: added regressions for legacy backfill, real local edge extraction, idempotent materialized-empty handling, snapshot persistence, incremental create/update, graph-analytics edges, unrelated-slice preservation, and the existing artifact-consumption contract.

No MCP contract, standalone index, identity registry, or artifact-consumption semantics changed.

## Evidence

Targeted validation:

`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_symbol_call_facts.py tests/test_module_usage_facts.py tests/test_reference_regressions.py`

Result: `28 passed in 4.85s`.

Owning LIVE snapshot validation:

`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_consistency.py`

Result: `13 passed in 55.55s`.

Authoritative LIVE certification after required restart:

- `ping.available=true`
- `graph_analytics.symbol_calls_materialized=true`
- canonical graph-analytics call facts: 54
- required edges present with canonical line/call kind:
  - `generate_graph_analytics_report -> _compute_pagerank`, line 1648, `direct`
  - `_compute_pagerank -> _normalized_edges`, line 737, `direct`
  - `compute_topology_analytics -> _compute_pagerank`, line 1930, `direct`
- subsequent save/restart/load: revision remained `1314 -> 1314`, proving startup did not save/rebuild again
- 157 correctly materialized modules with `symbol_calls == ()` remained materialized-empty after restart

## Verdict

`LEGACY_SYMBOL_CALLS_BACKFILL=PASS`

`MATERIALIZED_EMPTY_DISTINGUISHED=PASS`

`BACKFILL_OWNER=ensure_module_usages`

`AUTHORITATIVE_EXTRACTOR=extract_module_usage_facts`

`GRAPH_ANALYTICS_REQUIRED_EDGES=PASS`

`BACKFILL_IDEMPOTENT_ACROSS_RESTART=PASS`

`INCREMENTAL_CURRENT_FACTS_MARKED=PASS`

`UNRELATED_MODULE_USAGES_PRESERVED=PASS`

`ARTIFACT_CONSUMPTION_UNCHANGED=PASS`

`IDENTITY_REGISTRY_CHANGED=NO`

`CURRENT_SYMBOL_CALL_REPRESENTATION=PRIMITIVE_TUPLES`

`MCP_RESTART_REQUIRED=NO`

`LIVE_RESTART_REQUIRED=DONE`

`ISSUE_2_STAGE_A_VERDICT=CLOSED`

## Diffs

`FILES_CHANGED=contextor/core/domain/usage_facts.py,contextor/core/analysis/incremental/materialization.py,contextor/core/live_state/store.py,contextor/core/live_state/runtime.py,tests/test_symbol_call_facts.py`

```diff
+ ModuleUsageFacts.symbol_calls_materialized: bool = True
+ legacy marker absence resolves and serializes as false
+ ModuleUsageFacts dictionary round-trip persists the marker
+ module_usages_require_materialization(state)
- ensure_module_usages rebuilds only missing entries
+ ensure_module_usages rebuilds missing entries and legacy unmaterialized slices
+ snapshot normalization preserves stored marker provenance
+ LIVE startup backfills and saves only when required
+ targeted compatibility, idempotence, incremental, graph, isolation, and contract regressions
```

No other production/test files were changed by this task. `walkthrough.md` is the required reporting artifact and is excluded from `FILES_CHANGED`.
