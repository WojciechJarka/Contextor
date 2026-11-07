# C16-B03-P1D3G18-P2-D7 — discovery

## CURRENT_CANONICAL_STATE

DIRECT_EVIDENCE: Contextor MCP first for `namespace_bound_model`, `namespace_source_binding`, `namespace_path_model`, `package_model`, `package_layout`, `model_source_closure`, `scenarios`: revision 1097, `canonical_state=fresh`, each `workspace_sync=verified`, advisory warning null, syntax errors 0, structural DFS cycles 16, active warning count 16, `cycle_semantics=stale`. Snapshot metadata: state_id `20261106_195021`, repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`. Current HEAD `aac06a93db15e77862e589c810d20623aa4b469f`; worktree clean before report. Repository `.venv\Scripts\python.exe` reports CPython 3.15.2. Git HEAD and LIVE revision are distinct authorities.

## SOURCE_DOMAIN_AND_SCC_CLOSURES

DIRECT_EVIDENCE: Read-only `load_snapshot`, canonical `hard_edges` and `Module.imports`, followed by production `compute_cycle_model_source_closures_with_optional_children`. Physical production `.py` files: 308 (`contextor` 307 plus root `main.py`); all 308 occur in the canonical index. Canonical indexed graph has 626 module IDs including tests. SCC1: 44 members, 202 selected sources. SCC2: 9 members, 222 selected sources. Union 222; SCC1 is contained in SCC2. Indexed production modules outside union: 86; outside SCC1: 106. Metadata-selected FileState and snapshot both reported revision 1097/state_id `20261106_195021`. Current byte SHA-256 matched FileState for all 308 full-production files and all selected sources; zero missing or mismatched. Both SCCs encounter four namespace records, all under `contextor.core.git`.

## EXACT_CAPACITY_GUARDS

CODE_PATH_PROVED — `contextor/core/cycle_semantics/namespace_source_binding.py:24-27,95-105,168-209`: `_MAX_SOURCES=256`, `_MAX_SOURCE_BYTES=2*1024*1024`, `_MAX_TOTAL_BYTES=32*1024*1024`, `_MAX_INVENTORY_FILES=16384`. The binder first resolves the requested path, then rejects empty/non-tuple/>256 bindings or non-mapping fingerprints/snapshots with `SOURCE_BINDING_INPUT_INVALID`; checks inventory count; validates root IDs, binding identity and exact `module_id.replace('.', '/') + '.py'` path; requires exact equality of binding IDs, fingerprint keys and snapshot keys (`SOURCE_INDEX_DOMAIN_MISMATCH`); requires every supplied `.py` inventory entry to have a binding (`INVENTORY_SOURCE_BINDING_MISMATCH`); then checks per-source bytes, cumulative bytes and hashes. `contextor/core/cycle_semantics/package_model.py:1704-1714` separately rejects a conditional AST cohort over 256 as `INVALID_CONDITIONAL_SOURCE_COHORT`. These are distinct from path ambiguity, finder uncertainty and restricted AST execution. The selected cohorts stay below all measured count/byte limits; full production inventory exceeds only the source-count limit among these measured limits.

## FULL_PRODUCTION_INVENTORY_REPLAY

DIRECT_EVIDENCE: Supplied 308 canonical indexed physical production `.py` sources, exact repo-relative paths, current bytes and FileState-matching SHA-256; total 3,430,300 bytes; 308 inventory `.py` files. Entry `contextor.core.api.facade` is an indexed SCC1 member. `resolve_namespace_path(..., standard_finder_assumed=True)` returned `CONDITIONAL`, selected a `MODULE_FILE` from the supplied inventory. `bind_indexed_namespace_resolution` returned `INDETERMINATE / SOURCE_BINDING_INPUT_INVALID` at the `len(bindings)>256` guard. Source-bound wrapper returned `UNKNOWN / SOURCE_BINDING_INPUT_INVALID`, no digest, no conditional assessment, and no model execution. It did not reach source parsing or the separate conditional-model 256 guard. No limit was changed.

## SCC1_SELECTED_COHORT_REPLAY

DIRECT_EVIDENCE: Supplied exactly 202 selected indexed sources and matching `.py` inventory entries, 2,373,594 bytes, 202/202 FileState-matching hashes. Same indexed entry `contextor.core.api.facade`. Path resolution `CONDITIONAL / MODULE_FILE`; binder `SOURCE_BOUND_CONDITIONAL` with digest. Wrapper returned `UNKNOWN / RESTRICTED_MODEL_UNKNOWN` with a conditional assessment. Its nested package assessment was `UNKNOWN`, first target `contextor.core.analysis.cache_manager`, symbol null, 0 events. CPython AST `compile(..., dont_inherit=True)` succeeds for that target, while the restricted `_compile` returns None; model evaluation reached AST compilation but not import-order execution. Inventory equality is proven only relative to these 202 supplied paths; 106 indexed production sources are omitted.

## SCC2_SELECTED_COHORT_REPLAY

DIRECT_EVIDENCE: Supplied exactly 222 selected indexed sources and matching `.py` inventory entries, 2,659,738 bytes, 222/222 FileState-matching hashes. Same indexed SCC1 entry, also present in SCC2's selected cohort. Path resolution `CONDITIONAL / MODULE_FILE`; binder `SOURCE_BOUND_CONDITIONAL` with digest. Wrapper returned `UNKNOWN / RESTRICTED_MODEL_UNKNOWN`; nested package assessment `UNKNOWN`, first target `contextor.core.analysis.cache_manager`, symbol null, 0 events. The same target passed CPython compile but failed restricted `_compile` in read-only diagnostic. Inventory equality is relative to 222 supplied paths; 86 indexed production sources are omitted. Neither selected-cohort result is a complete interpreter search-environment proof.

## NAMESPACE_PATH_RELEVANCE

DIRECT_EVIDENCE: Both SCCs have the same four records: `contextor.core.analysis.git_context:13` and `contextor.core.reporting_engine.header:2` request `contextor.core.git.repo_state`; `contextor.core.reporting_engine.io_manager:21` requests `contextor.core.git.diff_engine`; `contextor.core.reporting_engine.pipeline:114` requests `contextor.core.git.repo_state`. Candidate namespace parent is `contextor.core.git`. The physical directory contains indexed `repo_state.py` and `diff_engine.py`, with no `__init__.py`, no colliding `git.py`, and no `.pyd`/`.so` file there. Both requested children resolve under the supplied selected inventories as `CONDITIONAL / MODULE_FILE`, with a `NAMESPACE_PACKAGE` parent and corresponding selected source. No indexed production module outside the SCC union is at `contextor.core.git` or under either requested child path. These are local physical and supplied-inventory facts; the resolver's standard-finder assumption does not establish actual runtime selection or exclude unindexed/external portions.

## RUNTIME_AUTHORITY_BOUNDARY

CODE_PATH_PROVED — `contextor/core/cycle_semantics/namespace_path_model.py:40-223` requires `standard_finder_assumed=True`, models `.py`/regular-package/namespace precedence and rejects tagged alternative loader candidates. It does not authenticate `sys.path`, `sys.meta_path`, `sys.modules`, loaders, dynamic path mutation or external portions. `namespace_source_binding.py:56-260` hashes caller-supplied inventory and bytes, not an actual interpreter environment. `namespace_bound_model.py` exposes only conditional outcomes. The actual SCCs remain `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`, despite successful conditional resolution of two individual requested paths. No MODEL_PASS or warning suppression follows.

## MISSING_SOURCE_NEGATIVE_CASE

DIRECT_EVIDENCE: An in-memory copy of SCC1 bindings omitted the selected indexed entry `contextor.core.api.facade` while retaining its fingerprint, snapshot and inventory path. The existing binder returned `INDETERMINATE / SOURCE_INDEX_DOMAIN_MISMATCH`, with no positive conditional assessment. No physical file was changed.

## REGRESSION_TEST_COVERAGE

Source inspected only; no pytest run. `tests/test_cycle_semantics_namespace_bound_model.py`: `test_p6_source_bound_conditional_pass`, `test_p6_changed_bytes_fail_closed`, `test_p6_missing_indexed_snapshot_fails`, `test_p6_finder_assumption_is_required`, `test_p6_unindexed_shadowing_source_rejected`, `test_p6_two_portions_source_bound`, `test_p6_eager_external_import_unknown`. `tests/test_cycle_semantics_namespace_source_binding.py`: `test_m01_namespace_source_bytes_are_bound`, `test_m02_two_portions_bind_distinct_children`, `test_m03_finder_assumption_is_not_automatic`, `test_m04_modified_raw_bytes_are_rejected`, `test_m05_forged_fingerprint_is_rejected`, `test_m07_unbound_python_inventory_entry_is_rejected`, `test_m08_missing_capture_is_rejected`, `test_m10_alternative_loader_remains_indeterminate`, `test_m12_source_byte_budget_fails_closed`, `test_m14_unindexed_shadowing_source_blocks_binding`. `tests/test_cycle_semantics_namespace_path_model.py`: `test_t03_two_namespace_portions`, `test_t04_regular_package_shadows_earlier_namespace`, `test_t06_finder_environment_not_proved`, `test_t08b_tagged_alternative_loaders_fail_closed`. `tests/test_cycle_semantics_namespace_pep420_contract.py`: `test_t03_namespace_with_two_portions`, `test_t04_later_regular_package_shadows_namespace`, `test_t05_namespace_path_changes_dynamically`, `test_t06_meta_path_finder_can_override_resolution`. The exact 308>256 full-inventory boundary, 32 MiB cumulative source limit and 16,384 inventory-file limit have no named targeted regression in these four modules; the first was observed directly here. No test was added.

## UNRESOLVED_FACTS

The supplied full inventory is the local indexed physical `.py` domain, not authenticated runtime `sys.path` or all loaders. The selected cohorts omit 106/86 indexed production files respectively and cannot certify absence of shadowing outside supplied inventory. Exact unsupported AST statement in `cache_manager.py` was not classified here; direct evidence is only restricted `_compile=None` after successful CPython compile. Actual runtime finder state, dynamic imports, external namespace portions and LIVE adoption remain unknown. Canonical cycle semantics remains stale. No analyzed repository source was executed; diagnostics parsed AST and invoked only model functions.

## FILES_CHANGED_AND_FULL_DIFFS

Production/test/docs changes: NONE. `ACTUAL_DIFF=DIFFS=FULL_DIFFS=NONE`. Only this root `walkthrough.md` report was overwritten. No FULL, update_file, restart, interpreter switch, dependency installation, pytest, Git mutation, warning change or /3 publication occurred.

## FINAL_VERDICT

DISCOVERY_COMPLETE — all three caller-supplied inventories were measured against one FileState-bound generation; the full inventory fails at the 256-source capacity guard, while both selected cohorts bind and then fail at the restricted AST model without granting runtime authority.
