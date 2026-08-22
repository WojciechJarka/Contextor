# ISSUE 2 / STAGE A — final materialization marker fix

## Summary

The domain default now means “not proven materialized”: `ModuleUsageFacts.symbol_calls_materialized=False`. Only successful authoritative extraction from a valid source/AST sets it to `True`. Missing source and syntax-error paths retain `False`; a valid module retains `True` even when its correct graph is empty.

No backfill policy, LIVE startup ownership, tuple representation, snapshot schema, legacy migration, identity registry, artifact consumption, MCP contract, or documentation changed.

## Implementation

- `contextor/core/domain/usage_facts.py`: changed the marker default from `True` to `False`.
- `contextor/core/reference/engine.py`: the successful final `extract_module_usage_facts` return explicitly sets `symbol_calls_materialized=True`; early `None` and `SyntaxError` returns use the false domain default.
- `tests/test_symbol_call_facts.py`: added direct regressions for missing source, invalid source, valid materialized-empty source, valid source with an edge, and preserved snapshot/restart behavior.

## Evidence

Required targeted tests:

`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_symbol_call_facts.py tests/test_module_usage_facts.py`

Result: `25 passed in 4.38s`.

Owning LIVE-state tests:

`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_live_state_consistency.py`

Result: `13 passed in 51.82s`.

Post-change LIVE restart certification:

- `ping.available=true`, revision 1317
- `graph_analytics.symbol_calls_materialized=true`
- all three required canonical edges remain present:
  - `generate_graph_analytics_report -> _compute_pagerank`, line 1648, `direct`
  - `_compute_pagerank -> _normalized_edges`, line 737, `direct`
  - `compute_topology_analytics -> _compute_pagerank`, line 1930, `direct`
- 157 correctly materialized-empty modules remain marked `True`
- restart metadata revision remained `1317 -> 1317`; no unnecessary backfill/save occurred

## Verdict

`MISSING_SOURCE_MATERIALIZED=FALSE`

`SYNTAX_ERROR_MATERIALIZED=FALSE`

`VALID_EMPTY_MATERIALIZED=TRUE`

`VALID_EDGE_MATERIALIZED=TRUE`

`PERSISTED_MATERIALIZED_EMPTY_PRESERVED=PASS`

`LEGACY_BACKFILL_REGRESSIONS=PASS`

`LIVE_RESTART_REQUIRED=DONE`

`MCP_RESTART_REQUIRED=NO`

`ISSUE_2_STAGE_A_VERDICT=CLOSED`

## Diffs

`FILES_CHANGED=contextor/core/domain/usage_facts.py,contextor/core/reference/engine.py,tests/test_symbol_call_facts.py`

```diff
- symbol_calls_materialized: bool = True
+ symbol_calls_materialized: bool = False

  return ModuleUsageFacts(
      ...
      symbol_calls=symbol_calls,
+     symbol_calls_materialized=True,
  )

+ targeted marker-semantics and persistence regressions
```

No other production/test files were changed by this task. `walkthrough.md` is the required reporting artifact and is excluded from `FILES_CHANGED`.
