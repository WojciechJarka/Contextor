# Regression fix — event callback full/incremental parity

## Result

`ROOT_CAUSE=Stage A added local methods to SymbolReferenceVisitor.target_symbols so canonical intra-module calls could be captured. For e.subscribe/e.on/e.bind, unresolved instance-method matching classified the local method (for example consumer.Emitter.subscribe) as called_ambiguous. extract_module_usage_facts promoted that local-only ambiguous fact into runtime_calls. The incremental artifact-consumption refresh then resolved it to consumer::Emitter.subscribe and installed consumer as its own ordinary runtime consumer. Full analysis correctly excluded this self-consumer. The actual event_fn fact remained correctly and disjointly classified as event_bindings in both paths.`

`AUTHORITATIVE_SEMANTICS=Event callback arguments remain event_bindings, not callback_calls or ordinary direct/runtime calls. Local intra-module method identities belong to symbol_calls when confirmed; they must not leak into outbound runtime_calls through ambiguous fallback.`

`WHY_INCREMENTAL_ADDED_CONSUMER=plan_executor rebuilds artifact consumption from every ModuleUsageFacts usage channel. The spurious runtime_calls=('consumer.Emitter.subscribe',) therefore created consumer::Emitter.subscribe -> consumer, while the full oracle had no such consumer.`

`FIX=Filter local_resolved_names out of visitor.called_ambiguous when materializing runtime_calls, matching the existing local-name exclusion already applied to direct_calls. Event binding extraction and symbol_called were not changed.`

This was a regression introduced by the Stage A local-symbol target expansion, not an older parity defect exposed by backfill. No changes were required in `visitor.py`, `usage_facts.py`, materialization, snapshot compatibility, or LIVE startup.

## Validation

Targeted parity selector:

`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_completeness_freshness_parity_proof.py -k "event_callback_disjoint_contract_e1_all_event_forms or full_static_channel_domain_all_six_channels_parity"`

Result: `4 passed, 27 deselected in 12.55s`.

Stage A/reference regressions:

`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe -m pytest -q tests/test_symbol_call_facts.py tests/test_reference_regressions.py tests/test_module_usage_facts.py`

Result: `29 passed in 4.22s`.

Current LIVE canonical control:

- `graph_analytics.symbol_calls_materialized=true`
- canonical facts: 54
- all three required graph-analytics edges remain present

## Verdict

`EVENT_CALLBACK_PARITY=PASS`

`SIX_CHANNEL_PARITY=PASS`

`SYMBOL_CALL_GRAPH_REGRESSION=PASS`

`OPEN_P0=NONE`

`OPEN_P1=NONE`

`OPEN_P2=NONE`

`VERDICT=PASS`

Stage B runtime certification was not resumed.

## Diffs

`FILES_CHANGED=contextor/core/reference/engine.py`

`ACTUAL_DIFF=`

```diff
 dyn_calls = set(
     item[0] if isinstance(item, tuple) else item
     for item in visitor.called_ambiguous
+    if (item[0] if isinstance(item, tuple) else item) not in local_resolved_names
 )
```

`walkthrough.md` is the required reporting artifact and is excluded from `FILES_CHANGED`.
