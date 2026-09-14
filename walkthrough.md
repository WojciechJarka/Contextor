# P0 L3A — lineage reuse gate

## STATUS

BLOCKED — literal test specification conflicts with the literal gate. No
production or test change remains; no full analysis, benchmark, or full pytest
was run.

## CONTEXTOR_DISCOVERY

Contextor MCP confirmed current fresh LIVE owner and call graph:
`materialize_lineage_source_facts` is the existing single-slice materializer,
using `_semantic_anchor_bindings` and `_seed_defining_interface_descriptors`.
`reresolve_materialized_lineage_source_facts` is the existing separate
resolution lifecycle. The requested new predicate would be a pure gate beside
these functions, not a parallel materialization lifecycle.

## LITERAL_CONTRADICTION

`test_materialized_lineage_source_matches_unchanged_resolution` as supplied
creates its only `ExtractedFlowFact` without `owner_local_id`. Current
`materialize_lineage_source_facts` computes:

```python
flow_ownership_materialized = all(
    flow.owner_local_id is not None for flow in extracted.flows
)
```

Therefore its freshly materialized manifest has
`flow_ownership_materialized=False`. The supplied gate itself requires
`manifest.flow_ownership_materialized` to be true before it can return true.
The exact supplied unchanged-resolution assertion therefore fails:

```text
AssertionError: materialized_lineage_source_matches_resolution(...) is True
```

This is a semantic contradiction, not formatting or an import issue. Making
the test pass would require changing the supplied test input to provide an
owner local ID, or weakening/removing the supplied fail-closed gate condition;
neither is authorized by the literal implementation contract.

## VALIDATION

* `py_compile contextor/core/analysis/lineage_materialization.py` passed after
  the mechanical insertion correction.
* Required focused pytest was attempted; collection initially exposed a
  mechanical patch-marker correction, then the exact test ran and failed on
  the contradiction above: `1 failed, 30 passed`.
* All temporary source/test edits were reverted after the failure.

## FILES_CHANGED

NONE (except this required `walkthrough.md` report).

## FULL_DIFFS

NONE. `walkthrough.md` does not report its own diff; no production/test file
remains changed.
