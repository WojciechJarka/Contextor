# CONTEXTOR_B0G2D2_INCREMENTAL_VS_FULL_COMPLETE_DIFF_AUDIT

MODE: STRICT READ-ONLY DISCOVERY. No source/test edit, pytest, new analysis, LIVE mutation, restart or Git history operation.

## FILES_CHANGED

- C:\Temp\Contextor_Repo\walkthrough.md (this report only).
- Production/test/docs: NONE.

## ACTUAL_DIFF

ACTUAL_DIFF=DIFFS=NONE for production/test/docs. The report is excluded from source diffs by the task contract.

## SOURCE_IDENTITY

DIRECT_EVIDENCE: HEAD `e3497a255f3733d9f7ece18e0a000ff92b716c70`; pre-report `git status --short --untracked-files=all` empty. Contextor `get_symbol_implementation(mode=fetch, include=[implementation])` returned complete implementations with `source_contract.implementation_is_complete=true` and `state_freshness.workspace_sync=verified` for `prepare_source_update`, `_prepare_candidate_state`, `_apply_delta_and_commit`, `_process_single_artifact_module`, `extract_api_consumers`, `build_symbol_references_from_canonical`, and `build_module_usage_baseline_with_reuse`. `execute_refresh_plan` was obtained through contiguous, nontruncated `get_source_range` chunks covering lines 769–1305. Source ranges cited below are from current workspace and Contextor.

## PRESERVED_EVIDENCE_IDENTITY

DIRECT_EVIDENCE: root `C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-555\test_real_desktop_watcher_and_0\b0g2d_canonical_mismatch_evidence`.

| Capture | SHA-256 of pickle | revision | state_id | writer |
|---|---|---:|---|---|
| initial_full.pickle | 179927c90b37db8fc25d2eff4c8a542211c792c5f51cad188a4d3e9ab01b9346 | 1 | 20261012_130208 | desktop |
| desktop_incremental.pickle | e1b22ac4662118b3362939f0e90b29ea3c784d582372e9914a61c0b3974c27bc | 2 | 20261012_130208 | live-service |
| fresh_full_a.pickle | 06aebb75edfbd83a0edcec8553c4be95cabe0b8cf44bcc1b66bdf3021d4c856a | 3 | 20261012_130209 | desktop |

All captures contain `state`, `metadata`, `file_states`, `file_state_payload`, `source_bytes`. Same `repo_id=ctx_aa7ae0e9` and same isolated repository root. This audit did not create another capture.

## COMPARISON_METHOD

DIRECT_EVIDENCE: unpickled preserved captures offline using repository .venv Python. Applied existing `_state_projection(state, normalize_report_timestamps=True)` from `C:\Temp\Contextor_Repo\tests\test_desktop_mcp_canonical_parity.py:476`. Its `_project` preserves dataclass fields, mapping keys and types, ordered sequences, set membership, trie structure, primitive types and values. Only `layer_information.summary_data.generated_at` and `layer_information.summary_data.report_header.generated_at` were normalized, per `_normalize_proved_report_timestamps` at line 430. Recursive comparison walked all 36 declared `RepositoryAnalysisState` fields. A missing subtree is one structural difference site, retained as MISSING versus its complete value; no missing-to-empty equivalence. Separate comparison covered FileState, source bytes, SHA-256, and each capture's metadata/FileState linkage.

## TOTAL_DIFFERING_LEAVES

16 exact structural difference sites across 5 of 36 top-level fields; other 31 fields equal under the stated two-timestamp normalization. No set membership or sequence-order differences. A missing consumer record or cached mapping is counted once at its missing-key path, with its full content preserved below.

## DIFFERENCES_BY_CANONICAL_FAMILY

| Top-level field | Difference sites | Character |
|---|---:|---|
| `artifacts` | 1 | missing `child` consumer record |
| `cached_analytics` | 4 | incremental eager mapping versus FULL empty mapping |
| `cached_analytics_state` | 1 | `fresh` versus `deferred` |
| `layer_information` | 9 | debt and summary graph metrics stale versus FULL recomputation |
| `module_usages_manifest` | 1 | old versus current source SHA-256 |

## COMPLETE_DIFFERENCE_CATEGORIES

All paths below use Desktop incremental on the left and fresh FULL A on the right. `MISSING` means absent dictionary key, not an empty value.

1. `state.artifacts['pkg.__init__']['consumers']['child']`: MISSING / `{'signature': '', 'consumers': [], 'usage': {'direct_calls': [], 'direct_calls_detail': [], 'callback_calls': [], 'callback_calls_detail': [], 'event_bindings': [], 'event_bindings_detail': [], 'runtime_calls': [], 'qualified_refs': [], 'qualified_refs_detail': [], 'api_imports': [], 'inheritance': [], 'inheritance_detail': [], 'ambiguous_calls': []}, 'consumer_count': {'total': 0, 'direct_calls': 0, 'callbacks': 0, 'events': 0, 'qualified_refs': 0, 'api_imports': 0, 'inheritance': 0}}`.
2. `state.cached_analytics['export_degree']`: `{'consumer': 1, 'pkg.__init__': 1, 'pkg.child': 1, 'unrelated': 1}` / MISSING.
3. `state.cached_analytics['layer_violations']`: `[]` / MISSING.
4. `state.cached_analytics['module_layers']`: `{'consumer': 'adapter', 'pkg.__init__': 'adapter', 'pkg.child': 'adapter', 'unrelated': 'adapter'}` / MISSING.
5. `state.cached_analytics['visibility']`: `{'consumer': 'private', 'pkg.__init__': 'private', 'pkg.child': 'internal', 'unrelated': 'private'}` / MISSING.
6. `state.cached_analytics_state`: `fresh` / `deferred`.
7. `state.layer_information['debt']['interpretation']['breakdown']['soft_edges']`: `1 soft edges (+0.5)` / `none`.
8. `state.layer_information['debt']['interpretation']['label']`: `critical` / `low`.
9. `state.layer_information['debt']['normalized']`: `0.5` / `0.0`.
10. `state.layer_information['debt']['score']`: `0.5` / `0.0`.
11. `state.layer_information['debt']['soft_edge_penalty']`: `0.5` / `0.0`.
12. `state.layer_information['debt']['soft_edges_count']`: `1` / `0`.
13. `state.layer_information['summary_data']['debt_summary']['total_score']`: `0.5` / `0.0`.
14. `state.layer_information['summary_data']['metrics']['edges_soft']`: `1` / `0`.
15. `state.layer_information['summary_data']['metrics']['edges_total']`: `2` / `1`.
16. `state.module_usages_manifest['pkg.__init__']['sha256']`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `f00db78ab6749353708d53435633caaef82718c2d474db99949177f49a3de056`.

## ARTIFACT_OWN_SYMBOL_PARITY

DIRECT_EVIDENCE: both updated states have `artifacts['pkg.__init__']['own_symbols'] == ['child']`; symbol facts for all modules are structurally equal. Initial FULL had no own symbol in the empty initializer. Answer A: YES for this observed newly defined symbol.

## ARTIFACT_CONSUMER_RECORD_PARITY

DIRECT_EVIDENCE: Desktop incremental `pkg.__init__` has `consumers={}`; fresh FULL has the explicit zero-consumer `child` record in item 1. Initial FULL also had `consumers={}`. CODE_PATH_PROVED: `prepare_source_update` copies `old_consumers` into `new_artifacts` and never constructs records for new own symbols. FULL `_process_single_artifact_module` calls `extract_api_consumers` for every own symbol; that function creates the zero-use record. Answer C: no stale removed-symbol record exists in this capture, because this update only added `child`; retaining an old record after symbol removal is a CONDITIONAL_CODE_PATH concern, not runtime proved here. Answer D: unchanged defining modules are not rematerialized by `_rebuild_consumer_slice`, which updates the separate `artifact_consumption` mapping; whether a concrete unchanged definer's `artifacts[*]['consumers']` becomes stale on a reexport change is UNKNOWN for this fixture.

## ARTIFACT_CONSUMPTION_PARITY

DIRECT_EVIDENCE: entire `artifact_consumption` mapping, types, targets, channels and ordering projection are equal. Both have `pkg.__init__::child -> {'consumers': [], 'channels': {}}` and `pkg.child::VALUE -> {'consumers': ['consumer'], 'channels': {'consumer': ['qualified_refs']}}`. Both `artifact_consumption_state='fresh'`. Answer B: YES, expected child target exists. Answer F: YES, current fresh coverage validator checks target-key equality and consumption structure, not `artifacts[module]['consumers']` completeness; this observed state is fresh in that family while the embedded record is absent.

## REFERENCE_AND_REEXPORT_PARITY

DIRECT EVIDENCE: `reexport_facts_by_module` and `module_usages` are equal; initializer binding `child -> pkg.child` exists in both. All four incremental module usages have `reference_evidence_materialized=True`. Offline read-only invocation of `build_symbol_references_from_canonical(definer_module='pkg.__init__', symbols=['child'], artifact_consumption=incremental.artifact_consumption, module_usages=incremental.module_usages, current_modules=set(incremental.modules))`, followed by `extract_api_consumers(..., signatures=incremental.artifacts['pkg.__init__']['symbols']['signatures'])`, reproduced the exact FULL `child` consumer record (`EQUAL_FULL=True`), without source file reads. Answer E: YES for the captured state and exact zero-use record; broader module-domain guarantee is subject to the helper's explicit materialized-evidence preconditions.

## LINEAGE_PARITY

DIRECT_EVIDENCE: `lineage_facts_by_source`, lineage marker, semantic version, both query indexes and anchor-completeness flag equal. No lineage leaf difference.

## GRAPH_AND_CYCLES_PARITY

DIRECT_EVIDENCE: `dependency_graph` including hard/soft edges, `trie`, `package_root`, `cycles`, `cycles_state`, dependency matrix and shared clusters equal. In both updated captures the consumer hard edge points to `pkg.__init__` and no soft edge remains. Graph state and cycles do not explain the stale incremental `layer_information` values.

## METRICS_AND_ANALYTICS_PARITY

DIRECT_EVIDENCE: `metrics`, `topology_analytics`, topology marker, dependency matrix and clusters equal. `cached_analytics` differs in four keys and marker as listed: incremental has an eagerly computed fresh cache; fresh FULL has `{}` and `deferred`. This is an execution/materialization-policy difference under the current source, still a strict 36-field inequality. Answer G: YES: besides incomplete artifact consumer records, `module_usages_manifest` and `layer_information` differ; cached analytics also differs despite valid `fresh` on the incremental side.

## FRESHNESS_AND_COMPLETENESS_PARITY

DIRECT_EVIDENCE: module parse freshness, syntax diagnostics, artifact consumption, lineage, graph/topology, cycles, collisions, dependency matrix and shared cluster markers match. Both preserved states have `resync_required=False`. Incremental `cached_analytics_state='fresh'` versus FULL `deferred`. The `artifact_consumption_state='fresh'` predicate does not certify the separate per-symbol `artifacts[*]['consumers']` shape. The initializer usage manifest points to the old empty-file hash despite current usage facts and current FileState.

## LAYER_INFORMATION_PARITY

DIRECT_EVIDENCE: only the two approved report timestamps were normalized. The nine remaining exact semantic differences are items 7–15. Desktop incremental retained the initial graph report's soft-edge count 1, total edges 2 and score 0.5; current graph and fresh FULL report have soft-edge count 0, total edges 1 and score 0.0. CODE_PATH_PROVED: FULL `ContextorFacade.analyze_project` installs `layer_information` from current `analysis_result`; complete `execute_refresh_plan` and `_apply_delta_and_commit` do not assign this field. Thus this snapshot proves stale layer report content after an otherwise updated graph; do not classify the field as operational metadata.

## FILESTATE_AND_SOURCE_PARITY

DIRECT_EVIDENCE: desktop and fresh FULL captures have exactly equal `file_states`, equal `file_state_payload['files']`, and identical source byte maps. Each source SHA-256 equals the corresponding FileState SHA-256 in both captures. `pkg/__init__.py` is 12 bytes, SHA-256 `f00db78ab6749353708d53435633caaef82718c2d474db99949177f49a3de056`; other source hashes: `pkg/child.py=e13df8c44af5dea1e412403910b99cc5a48f2ccbf68a66b3374d6ab9cef9fc65`, `consumer.py=f27844feb13dbf2be6ad1165353c90050aeb5f4cf6c9704dd40dcbb404f0ec58`, `unrelated.py=538b8f634480bc5c532cf1f5a1ff6a3b0d21105689b2b52298afaad3605361bd`. Each generation's metadata `revision`/`state_id` matches its own FileState payload `_meta`. Both metadata records name generation-specific engine/FileState/lineage files. Different revision, state_id, writer and versioned filenames are evaluated as generation linkage, not waived canonical fields. The preserved pickle evidence does not prove that the named versioned files still exist on disk now. Manifest `pkg.__init__` SHA mismatch is internal canonical provenance, not a source-byte difference.

## FULL_VS_INCREMENTAL_OWNER_CONTRACTS

Contextor `contextor_fact_lineage(family='artifact_consumption')` identifies FULL producer `build_canonical_artifact_consumption` and installer `ContextorFacade.analyze_project`, versus incremental producer `_rebuild_consumer_slice` and installer `IncrementalAnalysisEngine._apply_delta_and_commit`. FULL artifact owner `_process_single_artifact_module` builds references and explicit consumer records. Incremental preparation owner `prepare_source_update` carries forward old consumer records, while refresh plan updates consumption targets/channels. FULL usage owner `build_module_usage_baseline_with_reuse` returns both usages and a per-current-file-SHA manifest; incremental candidate/commit owners update usages but have no `module_usages_manifest` assignment. FULL report owner installs `layer_information`; incremental plan/commit does not refresh it. FULL leaves cached analytics deferred by state default; incremental plan may compute and certify it fresh.

## INCOMPLETE_FRESH_STATE_EVIDENCE

CONTRACT_PROVED: `validate_canonical_artifact_consumption_coverage` at `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:680` validates consumption structure and exact canonical target set. It does not compare keys of `artifacts[*]['consumers']` to `own_symbols`. DIRECT_EVIDENCE: captured incremental has `artifact_consumption_state='fresh'`, exact child consumption target, and missing child consumer record. The package initializer `module_usages_manifest` also remains bound to the initial empty source hash while FileState/source bytes bind to the changed file. This is the observed incomplete/stale canonical content; no broader runtime reachability claim is needed.

## EXACT_SOURCE_FRAGMENTS

All paths below are absolute Windows paths. Relevant complete symbols were fetched with Contextor; `execute_refresh_plan` was retrieved in nontruncated contiguous ranges.

`C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\preparation.py:263-279`:
```python
raw_symbols = extract_file_symbols(str(path), tree=parsed_tree)
own_symbols = _module_own_symbols(raw_symbols)
old_consumers = (old_artifacts or {}).get("consumers", {})
new_artifacts = {
    "symbols": raw_symbols,
    "own_symbols": own_symbols,
    "consumers": old_consumers,
}
```

`C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py:145-190`:
```python
own_symbols = _module_own_symbols(symbols)
if not own_symbols:
    return module_id, {
        "symbols": symbols,
        "own_symbols": own_symbols,
        "consumers": {},
    }
references = build_symbol_references(
    _WORKER_MODULES,
    own_symbols,
    _WORKER_ROOT,
    definer_module=module_id,
    reference_index=_WORKER_REFERENCE_INDEX,
)
signatures = symbols.get("signatures", {})
consumers = extract_api_consumers(
    own_symbols,
    references,
    signatures=signatures,
)
```

`C:\Temp\Contextor_Repo\contextor\core\api\api_consumers.py:115-119`:
```python
result = {}
for symbol in symbols:
    reference = references.get(symbol, {})
```

`C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py:930-961,1056-1086,1093-1107`: `_rebuild_consumer_slice(... candidate.artifact_consumption ... candidate.artifacts ...)` writes `candidate.artifact_consumption`; the `artifact_consumption` patch invokes it for changed module and validates coverage. The cached analytics patch invokes `compute_cached_analytics(modules=candidate.modules, artifacts=candidate.artifacts, artifact_consumption=candidate.artifact_consumption, hard_edges=hard_edges)`. Complete `execute_refresh_plan` lines 769–1305 contain no per-artifact consumer-record rebuild, no manifest assignment, and no layer-information assignment.

`C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py:955-1008`:
```python
self.state.artifacts = candidate.artifacts
self.state.cached_analytics = candidate.cached_analytics
self.state.cached_analytics_state = candidate.cached_analytics_state
self.state.artifact_consumption = candidate.artifact_consumption
if (
    candidate.artifact_consumption_state != "stale"
    and not resync_required
    and validate_canonical_artifact_consumption_coverage(
        candidate.artifact_consumption, candidate.artifacts
    )
):
    self.state.artifact_consumption_state = "fresh"
else:
    self.state.artifact_consumption_state = "stale"
self.state.module_usages = candidate.module_usages
```
The complete fetched `_apply_delta_and_commit` contains no manifest or layer-information assignment.

`C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py:680-696`:
```python
if not validate_canonical_artifact_consumption(consumption):
    return False
expected = canonical_artifact_consumption_targets(artifacts)
actual = set(consumption.keys()) if isinstance(consumption, dict) else set()
return actual == expected
```

`C:\Temp\Contextor_Repo\contextor\core\reference\engine.py:824-993`: `build_symbol_references_from_canonical` requires materialized usage evidence for every current module, initializes `result[symbol] = _empty_reference()` for each own symbol, and projects references from canonical consumption and usage facts, with no source I/O. Its complete implementation was fetched.

`C:\Temp\Contextor_Repo\contextor\core\reference\module_usage_reuse.py:35-47`:
```python
for module_id,module in modules.items():
    path=_path(module); sha=_tracked_sha256(current_file_state_manager,path)
    old=usages.get(module_id); entry=old_manifest.get(module_id)
    fact=old if _can_reuse(module_id,module,previous_state,old,entry,sha) else _require_materialized(module_id,extract_module_usage_facts(module_id,module.ast_tree,imports=module.imports))
    facts[module_id]=fact; manifest[module_id]={"module_id":module_id,"path":path,"sha256":sha,"semantic_version":MODULE_USAGE_FACTS_SEMANTIC_VERSION}
```

`C:\Temp\Contextor_Repo\contextor\core\api\facade.py:966-1001`: FULL `RepositoryAnalysisState(... module_usages_manifest=module_usages_manifest, ... layer_information={'layer_index': ..., 'hotspots': ..., 'debt': ..., 'summary_data': ...})`; `cached_analytics` is not passed, leaving the state default deferred.

## EXISTING_TARGETED_REGRESSIONS

Exact current test owners/nodes (identified, not executed):

- `C:\Temp\Contextor_Repo\tests\test_desktop_mcp_live_incremental_parity.py::test_real_desktop_watcher_and_public_mcp_incremental_match_fresh_full` — strict real entrypoint parity; currently exposes first mismatch.
- `C:\Temp\Contextor_Repo\tests\test_desktop_mcp_canonical_parity.py::test_real_desktop_and_mcp_full_entrypoints_have_identical_canonical_state`; same file's `test_report_timestamp_normalization_has_no_wildcard_exclusion` and `test_report_timestamp_normalization_preserves_semantic_difference_and_fields`.
- `C:\Temp\Contextor_Repo\tests\test_refresh_plan_execution.py::test_case_d_symbol_removal`, `test_case_e_module_add`, `test_prepare_candidate_state_preserves_legacy_and_valid_parse_freshness_cow`.
- `C:\Temp\Contextor_Repo\tests\test_incremental_artifact_consumption.py::test_case_7_reexport_retarget_no_reread`.
- `C:\Temp\Contextor_Repo\tests\test_package_initializer_graph_refresh.py::test_initializer_binding_updates_incremental_graph_and_recovers_child_edge`.
- `C:\Temp\Contextor_Repo\tests\test_canonical_reference_projection.py::test_golden_parity_matrix`, `test_zero_io_and_zero_ast_parses_during_canonical_projection`, `test_incremental_update_file_materializes_reference_evidence`.
- `C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py::test_definition_add_backfill_without_reread`, `test_content_change_removes_obsolete_consumption_target_and_matches_full_oracle`, `test_package_init_module_addition_recomputes_existing_consumer`.
- `C:\Temp\Contextor_Repo\tests\test_cached_facts_live_analytics.py::test_incremental_lifecycle_and_plan_equality`, `test_production_parity_for_layer_visibility_export_degree_and_validation`.

Coverage gap: no identified focused test asserts exact `artifacts[module]['consumers']` keys and zero-use record parity after an own-symbol addition/removal or reexport-only change together with manifest SHA and all semantic `layer_information` fields. Existing strict real-entrypoint parity test now detects the gap; do not weaken it.

## REQUIRED_PRODUCTION_FILE_SCOPE

Evidence-supported responsibility locations only, not a patch design: `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\preparation.py` (new artifact facts), `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py` (candidate refresh/consumption/cache/graph), `C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py` (canonical commit and FileState), `C:\Temp\Contextor_Repo\contextor\core\reporting_layer\artifact_usage_report.py` and `C:\Temp\Contextor_Repo\contextor\core\api\api_consumers.py` (FULL consumer-record contract), `C:\Temp\Contextor_Repo\contextor\core\reference\engine.py` (RAM reference projection), `C:\Temp\Contextor_Repo\contextor\core\reference\module_usage_reuse.py` (FULL usage manifest contract), `C:\Temp\Contextor_Repo\contextor\core\api\facade.py` (FULL layer report materialization), `C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py` (freshness coverage predicate). Which of these must change is reserved for auditor decision.

## UNRESOLVED_QUESTIONS

- UNKNOWN: whether unchanged defining modules exhibit stale `artifacts[*]['consumers']` after a particular reexport retarget; this fixture proves the new symbol case, and source shows no rebuild in the inspected incremental path.
- UNKNOWN: whether historical snapshots exist on disk now at the metadata-named generation paths; preserved pickle metadata/payload linkage is verified.
- UNKNOWN: whether the product contract intends eager incremental versus deferred FULL `cached_analytics` to be canonical-equal; the strict current test contract says they differ and has no exception.
- No tests were run; no new runtime publication or mutation was performed.

## LIVE_REVISION_BEFORE_AFTER

DIRECT_EVIDENCE: Contextor `get_live_events(after_revision=360)` before and after offline work returned revision/latest_revision 360, activity_epoch `6899cce3f9224c428b6ef04a542d3abf`, continuity `continuous`, no new events. No inference of event propagation from an empty window.

## WORKSPACE_SYNC_POSTCHECK

`get_symbol_implementation` for current `prepare_source_update` after analysis: `workspace_sync=verified`, complete source contract, canonical revision 360.

## RESYNC_REQUIRED

Current Contextor LIVE: `false` per `get_live_events`. Preserved fixture states: `false` in both compared generations.

## RESTART_REQUIRED

No source/runtime changes in this task; NO.

## FINAL_VERDICT

B0G2D2_COMPLETE_DIFF_INVENTORY_READY

Awaiting auditor command: `proceduj`.
