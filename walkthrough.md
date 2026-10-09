# L14_SEMANTIC_FIXPOINT_CURRENT_CODE_DISCOVERY

MODE=READ_ONLY
NO_IMPLEMENTATION
NO_TESTS_RUN

CURRENT_HEAD
- `faf62a71591147f8757f58da851428db7a9bffb5`
- Contextor MCP resolved the exact target `contextor.core.analysis.incremental.plan_executor::execute_refresh_plan` at lines 758-1273. Its implementation preview reported canonical revision 114, canonical state fresh, and `workspace_sync=verified`; the exact source ranges below came from Contextor `get_source_range`.
- Git status before this report showed only pre-existing modifications to `CHANGELOG.md` and `walkthrough.md`; target source and test files were clean. No source/test/docs file was changed for this task.
- Contextor discovery: inspected the available tool inventory for Contextor/deferred/tool-search entries, read current MCP documentation before use, and used implementation, source-range, lineage, call-context, and module-context queries. No separate deferred-tool discovery endpoint was exposed. `get_symbol_call_context` returned zero intra-module call edges for this function; it is not evidence that there are no cross-module callers. Contextor module context separately lists `incremental.engine` and `incremental.__init__` as inbound module dependencies.

CURRENT_ALGORITHM
- Before RECOMPUTE, `execute_refresh_plan` copies the state, applies the delta module's candidate module/artifact/usage/re-export facts, and validates the candidate re-export domain (`plan_executor.py:789-878`).
- It then derives `expected_targets`, the dotted-target index, and the consumer-to-target reverse index once (`879-885`). When recomputation or artifact-consumption patching is planned, it assembles the re-export map and module export surfaces once from the candidate re-export facts (`895-904`).
- The queue starts with `deque(plan.recompute_modules)`; `scheduled_recompute` and `processed_recompute` are execution-local sets (`914-916`). Each consumer is popped, skipped if already processed, marked processed, and rebuilt from its `ModuleUsageFacts` (`918-952`).
- The canonical slice signature is taken before and after rebuilding. Equal signatures stop propagation for that node; a changed signature discovers consumers of that module from candidate module usages (`932-968`). The executor sorts discoveries, excludes the changed delta module, and queues only paths that are neither processed nor already scheduled (`970-984`).

EXACT_SYMBOLS_AND_PATHS
- `contextor.core.analysis.incremental.plan_executor::execute_refresh_plan`: `contextor/core/analysis/incremental/plan_executor.py:758-1273`.
- `_build_consumer_target_index`: same file, lines 108-158; execution-local reverse index, not persisted state.
- `_consumer_slice_signature`: same file, lines 160-238.
- `_resolve_canonical_target_keys` and singular compatibility wrapper `_resolve_canonical_target_key`: same file, lines 277-390.
- `_rebuild_consumer_slice`: same file, lines 401-678.
- `_find_dependent_consumers`: `contextor/core/analysis/refresh_planner.py:14-67`; the planner uses it to seed recomputation and the executor uses it for downstream expansion.
- Relevant oracle and regression code: `tests/test_completeness_freshness_parity_proof.py:40-111` and lines 1023-1560.

PROCESSED_RECOMPUTE_SEMANTICS
- Lifetime: `processed_recompute` is initialized once before the while-loop and is never cleared (`plan_executor.py:914-924`). A module is added before its facts are checked or its slice is rebuilt.
- A later discovery of an already processed consumer is explicitly discarded at lines 975-976. Therefore a previously processed consumer cannot be scheduled or recomputed a second time in this execution. A scheduled-but-not-yet-processed consumer is also not duplicated (`978-984`).
- This is at-most-once traversal, not a repeated-until-no-signature-changes loop. In the current implementation this does not leave a stale consumer slice: the candidate artifacts, usages, expected target domain, dotted index, and re-export/export-surface maps are prepared before the queue and are not changed by its iterations (`789-910`). `_rebuild_consumer_slice` reconstructs one consumer from its own fixed usage facts and those shared fixed inputs (`401-678`). Target resolution receives the already-built `expected_targets` and `dotted_target_index` at every rebuild call, so resolution does not consult another consumer's slice. Its mutations remove/install only the named consumer's membership/channels and update that consumer's reverse-index entry.
- Consequently, rebuilding consumer X cannot change the canonical result that rebuilding consumer Y would produce. If Y was processed before X's downstream discovery, Y already saw the final candidate inputs; it also already performed its own changed-slice downstream discovery on that first pass. If Y's slice did not change, its dependents are not invalidated by Y's unchanged slice. This is the source-level reason an at-most-once visited set is sufficient here.

FAN_IN_ORDERING_EVIDENCE
- `test_semantic_fan_in_recompute_is_once_only_and_order_independent` (`tests/test_completeness_freshness_parity_proof.py:1023-1234`) starts with the direct queue `("m_consumer", "z_bridge")`, then forcibly runs both that order and its reverse.
- In the m-before-z case, processing `z_bridge` later discovers `m_consumer` after it was already processed (`1190-1199`); the test asserts each module was rebuilt exactly once (`1178-1183`). It then compares each ordered result to a real full-analysis oracle and asserts the two ordered snapshots are equal (`1200-1226`).
- This fixture is a direct witness that a late discovery does occur and is skipped, while the resulting exact artifact-consumption map still matches the full oracle. The general order-independence conclusion comes from the fixed-input/per-consumer-local transform above; the test alone covers this fixture, not every possible repository.

TERMINATION_INVARIANT
- `_find_dependent_consumers` returns paths from the finite `module_usages` mapping and excludes the source path itself (`refresh_planner.py:31-67`). The queue's scheduled set admits each path once and the processed set prevents revisits (`plan_executor.py:914-984`). Thus the loop terminates after at most the finite number of initially planned and discoverable consumer paths; cycles cannot cause repeat work.
- The cycle regression `test_transitive_propagation_cycle_terminates_without_duplicate_recompute` asserts the execution trace has no duplicates and matches the full oracle (`tests/test_completeness_freshness_parity_proof.py:1308-1386`).

AMBIGUITY_REEXPORT_AND_INVALIDATION
- Signature: sorted canonical target rows encode target identity, consumer membership, and sorted channel set (`plan_executor.py:160-238`). The reverse index is updated to the rebuilt target set for that consumer by `_rebuild_consumer_slice` (`401-678`), so additions and removals participate in the before/after comparison.
- Ambiguous dotted spellings: the plural resolver preserves every exact canonical identity sharing the spelling (`277-357`); the singular compatibility helper reports `ambiguous` when multiple identities match (`359-390`). Rebuilding uses the plural resolver. The tests cover a late second provider and consumer-last ordering with parity to full analysis (`test_natural_dotted_identity_ambiguity_transition_lifecycle`, lines 355-477; `test_natural_dotted_identity_ambiguity_consumer_last`, lines 479-526).
- Re-exports: candidate maps/surfaces are assembled before the queue (`895-904`). Rebuild handles star-import surfaces and explicit `__all__` (`465-524`), then resolves aliases/re-export chains for usage references (`526-567`). The invalidation selector scans imports, aliases, direct/runtime calls, qualified refs, callback calls, event bindings, and inheritance refs with alias/package canonicalization (`refresh_planner.py:14-67`).
- Existing invalidation regressions include unchanged-slice stop (`test_transitive_propagation_stops_when_direct_consumer_slice_is_unchanged`, lines 1237-1305), transitive re-export late-provider parity (line 954), re-export symbol removal (lines 1390-1465), retargeting (lines 1468-1560), star visibility (lines 2428-2524), and package-init star visibility (lines 2525-2615).

FULL_VERSUS_INCREMENTAL_PARITY
- The test oracle invokes the real `ContextorFacade.analyze_project`, then hydrates the repository engine (`tests/test_completeness_freshness_parity_proof.py:40-50`). `_assert_full_parity` compares canonical modules, artifacts, usage facts, re-export facts, and exact artifact-consumption target/consumer/channel data (`52-111`).
- The fan-in test compares the full exact snapshot for both forced queue orders (above). Separate ambiguity and re-export regressions also compare to that oracle.
- These are focused parity contracts for the listed static fact paths; this audit did not run tests and does not claim that those tests exhaust all possible inputs or prove parity for unrelated state families.

EXISTING_REGRESSIONS
- `test_semantic_fan_in_recompute_is_once_only_and_order_independent`: both queue orders, late downstream discovery after prior processing, one rebuild per consumer, exact full-oracle parity (1023-1234).
- `test_transitive_propagation_stops_when_direct_consumer_slice_is_unchanged`: unchanged slice does not expand work; full-oracle parity (1237-1305).
- `test_transitive_propagation_cycle_terminates_without_duplicate_recompute`: cycle termination/no duplicate trace/full-oracle parity (1308-1386).
- Ambiguous dotted target tests: late provider transition and consumer-last order (355-526); plural backfill resolver regression (2120-2197).
- Re-export regressions: late provider (954-1019), removal and retargeting (1390-1560), star visibility and package-init star visibility (2428-2615).
- `test_true_order_independence_three_way_equality` also compares full analysis, provider-first, and consumer-first update histories (2014-2065); it is file-update order coverage, distinct from the forced worklist-order fan-in test.
- Tests run in this task: NONE (read-only discovery).

MINIMAL_COUNTEREXAMPLE
- NONE found in the current implementation for consumer-slice recomputation. The closest apparent counterexample is the committed fan-in fixture: `m_consumer` is rebuilt, then `z_bridge` changes and discovers it late; the visited-set guard suppresses a second rebuild. It still matches full analysis because the changed bridge slice is not an input to m_consumer's deterministic rebuild; both consumers already rebuild against the final candidate target/re-export context.
- No source/test execution was performed to manufacture another case. A gap would require another consumer's rebuild to mutate an input read by a previously processed consumer; the inspected executor/helper path does not do that.

EVIDENCE_CLASSIFICATION
- DIRECT_EVIDENCE: HEAD hash, clean target/test paths in Git status, Contextor freshness envelope (`workspace_sync=verified`), exact source ranges, and existing test assertions.
- CODE_PATH_PROVED: processed-once guard; before/after slice comparison; fixed candidate inputs; per-consumer updates; finite queue domain.
- CONTRACT_PROVED: focused tests assert exact artifact-consumption parity against full analysis for the forced fan-in orders, ambiguity transitions, and selected re-export/cycle scenarios.
- INFERENCE: general order independence for this consumer-slice pass follows from the inspected fixed-input, per-consumer-local rebuild contract.
- UNKNOWN: exhaustive parity over all potential static/dynamic repository facts was not established; tests were not run in this read-only task.

L14_VERDICT
CLOSED_BY_CURRENT_CODE

Rationale: `processed_recompute` prevents a second visit, but current consumer-slice rebuilding is a deterministic per-consumer projection over candidate inputs fixed before queue execution. A later rebuild mutates only its own consumer rows and cannot invalidate a previously completed row. Changed signatures still expand discovery to downstream consumers, while the visited set terminates cycles. The forced-order fan-in regression demonstrates the precise late-discovery case and compares both results with full analysis.

FILES_CHANGED=NONE
ACTUAL_DIFF=NONE
