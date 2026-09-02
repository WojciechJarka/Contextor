# Canonical ModuleUsageFacts lifecycle hardening — Stage 3 real reseed certification

Read-only certification after the user-owned fresh full Analyze Repository.

## A. Real canonical baseline

CANONICAL_REVISION=158
CANONICAL_STATE=fresh
MODULE_COUNT=325
MODULE_USAGE_COUNT=325
MISSING_MODULE_USAGE_MODULES=NONE
EXTRA_MODULE_USAGE_MODULES=NONE
SYMBOL_CALLS_MATERIALIZED_TRUE=325
SYMBOL_CALLS_MATERIALIZED_FALSE=0
REFERENCE_EVIDENCE_MATERIALIZED_TRUE=325
REFERENCE_EVIDENCE_MATERIALIZED_FALSE=0

The hydrated authoritative state satisfies `set(state.module_usages) == set(state.modules)`. All 325 current slices have both materialization flags true.

## B. Persistence/hydration proof

A normal authoritative hydration of revision 158 returned the complete 325-slice mapping. `module_usages_require_materialization(state)` returned `False`. No `ensure_module_usages` call was made.

MODULE_USAGES_REQUIRE_MATERIALIZATION_AFTER_FULL_SEED=NO
HYDRATION_LEGACY_USAGE_BACKFILL_REQUIRED=NO

## C. Canonical reference projection

Real seeded state projection selected `contextor.__main__::main`, which has current confirmed consumers. `build_symbol_references_from_canonical` completed with canonical data; the result contains `called_by=["main"]`, source detail line 27, and `imported_from=["main"]`.

The direct projector has no reference-index invocation, source read, or AST parse path; it consumed the already loaded canonical artifacts and module usages.

CANONICAL_REFERENCE_PROJECTION=PASS
REFERENCE_INDEX_FALLBACK_REQUIRED=NO
SOURCE_READ_REQUIRED_FOR_PROJECTION=NO
AST_PARSE_REQUIRED_FOR_PROJECTION=NO

## D. Symbol-call canonical consumer

Symbol: `contextor.core.reporting_engine.graph_analytics::generate_graph_analytics_report`.

`get_symbol_call_context(direction="callees", depth=1, max_items=10)` returned `status="ok"`, 16 total intra-module edges (10 returned due to requested bound), and `data_source="live_canonical_module_usages_symbol_calls"`. The state envelope reported `canonical_revision=158`, `canonical_state="fresh"`, and `workspace_sync="verified"`. No unmaterialized-state error occurred.

## E. LIVE publication

The LIVE service was reachable. Its current authoritative revision is 158. The retained journal includes desktop full-analysis publishes:
- revision 157, `desktop_analysis`, status `PUBLISHED`;
- revision 158, `desktop_analysis`, status `PUBLISHED`.

The authoritative revision matches the latest full-analysis publication.

LIVE_SERVICE_REACHABLE=YES
FULL_ANALYSIS_PUBLICATION_EVENT_PRESENT=YES
FULL_ANALYSIS_PUBLICATION_REVISION=158
AUTHORITATIVE_REVISION_MATCHES_PUBLICATION=YES

## F. Parse-cost diagnostic

The completed full-analysis event/snapshot does not retain instrumentation distinguishing a warm `Module.ast_tree` cache hit from a cache miss that called `parse_source`. The Stage 2 helper itself passes `module.ast_tree` and does not call `ast.parse`, but retrospective evidence cannot prove how the property was populated during the completed run.

BASELINE_ADDITIONAL_AST_PARSE_COUNT=UNKNOWN
FUTURE_CONTROLLED_INSTRUMENTED_FULL_ANALYSIS_REQUIRED=YES

This uncertainty does not affect lifecycle correctness.

STAGE2_CODE_STATUS=PASS
REAL_FULL_SEED_CERTIFIED=YES
MODULE_COUNT=325
MODULE_USAGE_COUNT=325
FULL_USAGE_DOMAIN_MATCH=YES
ALL_SYMBOL_CALLS_MATERIALIZED=YES
ALL_REFERENCE_EVIDENCE_MATERIALIZED=YES
HYDRATION_LEGACY_USAGE_BACKFILL_REQUIRED=NO
CANONICAL_REFERENCE_PROJECTION=PASS
REFERENCE_INDEX_FALLBACK_REQUIRED=NO
GET_SYMBOL_CALL_CONTEXT_CANONICAL=PASS
LIVE_SERVICE_REACHABLE=YES
FULL_ANALYSIS_PUBLICATION_EVENT_PRESENT=YES
BASELINE_ADDITIONAL_AST_PARSE_COUNT=UNKNOWN
MCP_RESTART_REQUIRED=NO
FILES_CHANGED=NONE
DIFFS=NONE
NEXT_TARGET=residual canonical LIVE completeness audit

Wait for proceduj.

