# F2F0 runtime certification

DECISION=PASS

RUNTIME_FRESHNESS=PASS

MCP_RESTART_REQUIRED=NO

LIVE_RESTART_REQUIRED=NO

RUNTIME_CERTIFICATION_NOT_YET_PERFORMED=NO

FILES_CHANGED=NONE

DIFFS=NONE

FULL_SUITE_RUN_BY_AGENT=NO

## Loaded tool/schema evidence

The live MCP `get_mcp_documentation(tool="get_symbol_call_context")` response exposes `get_symbol_call_context` with version `1.0.0` and the current eight-parameter schema, including `representation` and `allow_large_output`.

Its live behavior text contains the corrected loaded contract: explicit named output over 51,200 bytes returns `large_named_output_requires_indexed_representation` without edges; `allow_large_output` does not bypass this ceiling; explicit named never switches to indexed; auto above the ceiling requires complete indexed identities. The freshness text also states no repository scan, no `ast.parse`, and no source-derived call reconstruction while allowing target-local fingerprint/hash work for `workspace_sync`.

This is runtime-served documentation, not repository-source evidence, so it proves that the running server is not serving the pre-correction schema/contract.

## LIVE evidence

`get_live_events(after_revision=216)` returned:

```text
revision=217
latest_revision=217
continuity=continuous
resync_required=false
resync_reason=null
origin=desktop_analysis
operation=publish
status=PUBLISHED
```

The representative tool responses all used `canonical_revision=217`, `provenance=live`, `canonical_state=fresh`, `workspace_sync=verified`, and `advisory_warning=null`.

## Representative runtime query

Root: `contextor.mcp.tools.get_symbol_call_context::get_symbol_call_context`.

```text
direction=callees depth=1 max_items=5
```

Named response: `status=ok`, `total_edges=28`, `returned_edges=5`, `truncated=true`, with canonical qualified caller/callee identities, direct call facts, and source lines 223/226/228/230/235. `data_source=live_canonical_module_usages_symbol_calls`.

Indexed response: `status=ok`, same 28/5 topology, persistent endpoint IDs (`A2407/1` → `A2411/1`) and `resolver.resolve_via=lookup_index_entries`.

Auto response: `status=ok`, selected `named`, `requested_representation=auto`, `bytes_saved=430`, `reason=auto_named`; this is the unchanged below-ceiling behavior because the saving is below 512 bytes.

No source-derived call reconstruction or AST analysis is claimed or observed: the runtime response’s loaded freshness contract expressly forbids them, and the response identifies only materialized LIVE canonical `symbol_calls` as its data source.

## Boundary exercise

BOUNDARY_RUNTIME_EXERCISE=NOT_PRACTICAL

The real runtime candidate for the representative symbol is only 1,908 named bytes at the requested five-edge bound. No sufficiently large real candidate was manufactured, and no repository/LIVE state was mutated to force one. The freshly loaded runtime schema explicitly exposes the explicit-named hard-ceiling and auto/indexed precedence; focused source tests remain the authority for synthetic 51,200-byte boundary cases.
