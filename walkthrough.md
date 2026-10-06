# CPA_FILE_UPDATE_CANONICAL_REEXPORT_FACTS_PERSISTENCE_DISCOVERY

## 1. STATUS
STATUS=DISCOVERY_COMPLETE_READY_FOR_DESIGN
TESTS=NOT_RUN (source/Contextor discovery; user preferred ZERO pytest)
IMPLEMENTATION=NONE
PRODUCTION_OR_TEST_EDITS=NONE

Evidence labels: DIRECT_EVIDENCE = literal source/Git/Contextor result; CODE_PATH_PROVED = traced source path; CONTRACT_PROVED = source behavior or existing tests; INFERENCE = derived conclusion; UNKNOWN = not established.

## 2. HEAD
HEAD=93ae0ea98ec3466c9bdfa2e372b8b59c70325fbd

## 3. WORKTREE_STATE
WORKTREE_STATE=CLEAN
SOURCE_DRIFT=NONE
DIRECT_EVIDENCE: git status --short and git diff --stat were empty before this report. Accepted prior work is included in current HEAD.
CONTEXTOR: get_file_edit_context returned preparation.py workspace_sync=verified, fresh state, revision 1491; plan_executor.py workspace_sync=verified, fresh state, revision 1492. Both had no syntax errors.
CONTEXTOR SCOPE: contextor_fact_lineage v1 accepts only artifact_consumption, syntax_diagnostics, symbol_calls. No re-export family anchor is supported. Its artifact_consumption trace is only neighboring lifecycle evidence, not re-export lineage.

## 4. FULL_ANALYSIS_MATERIALIZATION_OWNER
DIRECT_EVIDENCE:
- index_repository returns RepositoryIndex.reference_facts_by_module (indexer.py:947-961, 964+, 1753-1762, 1990-1999).
- ContextorFacade.analyze_project has index immediately after index_repository and passes index.reference_facts_by_module into assemble_reference_index_or_fallback (facade.py:678-692).
- RepositoryAnalysisState is constructed at facade.py:937-978. Current constructor installs modules, artifacts, usages, lineage, collision and analytics, but no reference/re-export facts.
- Full canonical save calls save_engine_state at facade.py:1087-1096.
CANONICAL_OWNER=RepositoryAnalysisState in state_manager.py; exact full materialization insertion point is ContextorFacade.analyze_project state construction, while current-run index is available.
1. AVAILABLE_AT_STATE_CONSTRUCTION=YES.
2. COMPLETE_CURRENT_MODULE_DOMAIN=NOT GUARANTEED BY AN EXPLICIT INDEXER ASSERTION. Normal successful worker results attach reference facts to indexed modules. Parse-invalid files become skipped and are not in index.modules. The indexer inserts only non-None reference_facts and has no final key-set assertion; facade compact assembly is the existing coverage gate.
3. ENVELOPE_STATUSES=available | unavailable | failure.
4. SOURCE-FREE PROJECTION=YES if every current module has an available envelope and dict facts; then module_id -> facts["reexports"] is directly available. Not unconditional: unavailable has no facts and failure has facts=None.
5. FULL ANALYSIS HANDLING:
   - assemble_reference_index_or_fallback uses compact facts only if keys exactly match modules and all statuses are available/unavailable; otherwise it calls the AST-backed RepositoryReferenceIndex.build fallback (reference/index.py:669-686).
   - failure routes to that full fallback.
   - unavailable is accepted in the compact route but from_compact_facts skips that module and excludes its re-export slice (index.py:440-455, 472-477).
   - missing keys fail the exact-domain gate and route to AST fallback.
DIRECT_EVIDENCE: extract_compact_reference_facts returns unavailable if tree is None and failure with error metadata if extraction raises (reference/index.py:307-359). test_reference_fusion_integration.py:149-170 proves failure is represented in the run result but not persisted to the per-file cache.
INFERENCE: A new required re-export family should extract its slice independently from generic reference visitor success; an unrelated visitor failure can hide reexports despite an already parsed source tree.

## 5. MINIMAL_SUFFICIENT_CANONICAL_PAYLOAD
VARIANTS:

| Concern | A. Full reference_facts_by_module | B. Source-local reexport_facts_by_module |
|---|---|---|
| Re-export correctness | Sufficient only for complete available envelopes; broad-family failure/unavailable complicates coverage | Sufficient: assembler consumes exporter, explicit_all, bindings, star_sources |
| Persisted size | Larger: aliases, calls, callbacks, events, inheritance, qualified_refs, imports, reexports | Small: one four-field slice per module |
| Coupling | REFERENCE_FACTS_SCHEMA_VERSION, SinglePassConsumerVisitor and reference-index schema | Shared re-export extractor/assembler only |
| Validation | Envelope status/schema and broad generic facts plus nested reexports | Exact module coverage and four-field shape/identity |
| Single-file update | Broad visitor overlaps usage extraction | Replace one slice from the already parsed tree |
| Future reuse | Higher for rebuilding broader reference index | Narrow, directly matches this incremental resolver need |

DIRECT_EVIDENCE: _assemble_reexport_map(reexport_facts_by_module) reads only the four named fields and documents RAM-only/no-source-I/O behavior (reference/shared.py:139-147, 154-200). extract_compact_reference_facts packages generic visitor facts plus reexports (reference/index.py:320-351).
MINIMAL_SUFFICIENT_CANONICAL_PAYLOAD={module_id: {exporter: str, explicit_all: list[str] | None, bindings: dict[str, str], star_sources: list[str]}} for every current state.modules key, plus explicit family completeness/freshness or equivalent coverage validation. The marker prevents missing facts from being confused with a legitimate empty-export module.
This identifies the minimum for RAM-only re-export assembly; it does not discard the greater future reuse value of variant A.

## 6. DOMAIN_COMPLETENESS_INVARIANT
REQUIRED_FOR_FRESH_COMPLETE_FAMILY:
set(reexport_facts_by_module) == set(state.modules) = YES.
Every module needs a slice, including empty-but-valid modules.
- Valid empty .py: parsed tree; exporter, explicit_all=None, bindings={}, star_sources=[].
- Source with no public exports: retain a per-module slice; assembler may produce no mapping entries.
- Syntax-invalid / last-known-good: full indexing skips the invalid file; incremental parse failure retains previous modules/artifacts/usages and marks module_parse_freshness stale. Preserve its previous re-export slice as LKG.
- New file: insert one slice.
- Delete: remove one slice.
- Package __init__.py: key remains aligned to module domain (e.g. pkg.__init__); exporter normalizes to pkg.
- status=unavailable: not successful empty facts. Current compact assembly may accept the envelope but omits that module's reexports; new family must be incomplete/stale unless independent source-local extraction produced a valid slice.
- status=failure: also not successful empty facts.
DIRECT_EVIDENCE:
- _export_module_name is exactly module_id.removesuffix(".__init__") (shared.py:28-45).
- Module.ast_tree is lazy and may return None if stat/read/parse cannot produce a tree (domain/module.py:16-38, 58-60).
- incremental parse failure retains facts as last-known-good (engine.py:568-592; state_manager.py:245-263).
- deletion removes module/artifact/usage candidate slices (plan_executor.py:707-724).
UNKNOWN: No current canonical re-export family/status exists to label retained slices stale/LKG. Next design must relate that meaning to module_parse_freshness or an equivalent explicit family contract.

## 7. SINGLE_FILE_EXTRACTION_CONTRACT
CHANGED_FILE_EXTRA_PARSE_REQUIRED=NO
CHANGED_FILE_EXTRA_SOURCE_READ_REQUIRED=NO
DIRECT_EVIDENCE:
- prepare_source_update parses once with parse_source_with_fingerprint and retains parsed_tree (preparation.py:162-165).
- read_imports and extract_file_symbols receive that tree (preparation.py:206-255); extract_module_usage_facts also receives it (281-286).
- _extract_reexport_facts(module_id, tree) needs only module ID and AST and does no source/stat/parse work (shared.py:33-48).
OPTIONS:
- Direct shared extractor: minimal payload; scans top-level AST; no extra broad visitor.
- extract_compact_reference_facts(module_id, tree=parsed_tree, imports=new_imports): no extra parse/read/stat when called with these inputs, but runs SinglePassConsumerVisitor over the AST, packages broader facts, then calls re-export extraction (reference/index.py:320-351).
- new_usage invokes SymbolReferenceVisitor.visit(tree), local-symbol scanning, and later ast.walk(tree) (reference/engine.py:543-603, 643+). Compact extraction therefore adds a further broad visitor pass overlapping usage work; direct helper avoids this extra pass.
FAILURE: compact extraction catches and returns status=failure; shared direct helper itself has no try/except. Re-export extraction can fail independently of other preparation facts and needs its own failure semantics. No prepared re-export field/status currently exists.

## 8. ADD_CHANGE_DELETE_CONTRACT
Existing file change=replace one module slice before downstream assembly.
New file=insert one module slice before assembly.
Delete=remove one module slice before assembly.
DIRECT_EVIDENCE: plan_executor.py:707-736 pre-populates candidate modules/artifacts/usages for delete or changed/new modules; _apply_delta_and_commit manually publishes selected families at engine.py:944-990.
NO-OP EDGE: update_file returns from plan.is_empty at engine.py:623-657 without execute_refresh_plan or installing prep.new_artifacts. A top-level __all__-only change can change re-export facts while symbol/import/usage/collision facts remain equal. The new family must still replace its slice on this path.
DELETE: plan_executor.py:708-713 currently purges module/artifact/usage entries; no re-export family exists.
PARSE_FAILURE_REEXPORT_EXPECTATION=KEEP_LAST_KNOWN_GOOD

## 9. PARSE_FAILURE_CONTRACT
PARSE_FAILURE_REEXPORT_EXPECTATION=KEEP_LAST_KNOWN_GOOD
CODE_PATH_PROVED: prepare_source_update returns on SourceError before replacement facts (preparation.py:162-181). update_file routes that error to _commit_syntax_candidate (engine.py:568-599). That commit updates syntax/parse freshness/lineage but does not assign modules, artifacts or usages (engine.py:126-205). mark_module_parse_failure explicitly marks retained facts last-known-good (state_manager.py:245-263).
REQUIREMENT: preserve old re-export slice and LKG meaning; absence caused by parse failure is not deletion.

## 10. COW_CONTRACT
- RepositoryAnalysisState.clone_for_update loops declared dataclass fields and shallow-copies each top-level dict/list/set (state_manager.py:130-167). A declared dict gets its own outer map.
- Nested per-module values are shared; replace/delete a module slice, do not mutate nested data in place.
- CandidateState is a separate explicit dataclass and _prepare_candidate_state manually lists copied fields (plan_executor.py:37-70, 598-664).
- _apply_delta_and_commit also manually installs fields (engine.py:944-990).
MANUAL_FAMILY_SITES:
1. CandidateState field declaration.
2. _prepare_candidate_state copy/default.
3. execute_refresh_plan add/change/delete before RECOMPUTE.
4. _apply_delta_and_commit canonical installation.
5. Empty-plan and parse-failure paths, which bypass normal family patch execution.
COW nested sharing is safe only with replace-slice semantics.

## 11. SNAPSHOT_SCHEMA_CONTRACT
LIVE_STATE_SCHEMA_VERSION=1.3 (store.py:41).
OLDER_METADATA_VERSIONS_ACCEPTED=1.0, 1.1, 1.2 plus current 1.3 (store.py:1375-1403).
SERIALIZATION: save_snapshot pickles the full state object (store.py:1620-1650); new snapshots automatically include the new attribute.
OLD OBJECT BEHAVIOR: pickle restores serialized instance state; it does not backfill a newly added dataclass field. load_snapshot currently has explicit hasattr defaults for known old fields rather than a generic dataclass migration (store.py:1991-2082 and 2112-2198).
NORMALIZERS: specialized symbol-call, lineage and lineage-query-index normalizers exist; no generic RepositoryAnalysisState field normalizer found.
A new default_factory field is absent from an old unpickled instance unless load code explicitly initializes it. The class default_factory does not replace current explicit load compatibility code.
{} is unsafe as completeness default: with nonempty modules it lacks slices; a whole empty map is not equivalent to a module domain where every module has valid empty facts.

## 12. OLD_SNAPSHOT_COMPATIBILITY
OLD_SNAPSHOT_WITHOUT_REEXPORT_FACTS_CAN_BE_SAFELY_USED_INCREMENTALLY=NO
DIRECT_EVIDENCE:
- load_snapshot accepts current legacy metadata versions and has no re-export completeness check (store.py:1381-1386, 1991-2082).
- hydrate_repository_engine accepts loaded modules/graph and creates IncrementalAnalysisEngine (hydration.py:69-112).
- mcp.runtime.get_or_init_engine installs a loaded snapshot into an engine without a re-export-family guard (runtime.py:378-419).
INFERENCE: Old snapshots cannot supply the complete RAM map. Defaulting absence to {} would silently give incomplete resolver input; failing closed may block incremental use but is not usable compatibility.

## 13. HYDRATION_CONTRACT
1. resolve_authoritative_repository_state tries LIVE snapshot, then load_engine_state (hydration.py:39-68).
2. If load returns None or modules/graph are absent, it returns None; hydrate_repository_engine returns None (hydration.py:69-99).
3. MCP get_or_init_engine explicitly does not silently call analyze_project; if neither LIVE nor snapshot loads, engine cache is cleared and None returned (runtime.py:311-419).
4. LIVE runtime startup calls load_snapshot; the inspected startup path continues with state=None and does not trigger full analysis (live_state/runtime.py:1341-1361, 1428-1463).
5. No re-export completeness guard or load-time resync_required marking was found.
HYDRATION_RISK=YES until old/incomplete snapshots are rejected or explicitly marked before incremental execution.

## 14. FULL_ANALYSIS_TO_RESTART_CHAIN
CURRENT_CHAIN=NOT_YET_PRESENT_FOR_REEXPORT_FACTS
- Full run has current-run reference facts at the facade canonical materialization point; state construction does not install them.
- save_snapshot pickles the full state; a populated new field would persist.
- Restart hydration loads state without source scan, but current load has no family completeness check.
- Incremental executor still reconstructs reexports by scanning candidate modules through _build_reexport_map.
TARGET_CHAIN=full analysis -> complete facts installed at state construction -> snapshot -> load-time completeness/schema gate -> hydrate -> incremental replace one slice -> RAM-only assembly -> propagation -> persist/publish.
GAP: Generic reference extraction failure/unavailable must not mark the new re-export family complete. Full worker already has a parsed tree; separate extraction can use it. Old snapshot rejection also needs explicit full-analysis recovery; current get_or_init_engine does not provide it.

## 15. VALIDATION_REQUIREMENTS
Evidence-derived per-module shape:
- exporter: str and exactly module_id.removesuffix(".__init__").
- explicit_all: list[str] | None. None without a supported static assignment; list for supported list/tuple/set; [] for non-literal assignment. Last supported top-level assignment wins (shared.py:40-70).
- bindings: dict[str, str]; later source-order assignment overwrites earlier binding (shared.py:71-129).
- star_sources: list[str]; relative imports normalized against module/package identity (shared.py:71-84).
- Domain key exactly canonical module ID, retaining __init__ suffix.
- Validate exact key coverage, types, and exporter identity; reject missing/unexpected modules and malformed facts.
- Empty module slice is valid; unavailable/failure is not empty success.
- Preserve source-order semantics for __all__ assignment, binding overwrites, and star import collection.
DETERMINISTIC ORDER: Semantic equality does not require arbitrary sorting: explicit_all is consumed as membership; extraction and assembly are source-derived. Existing pickle contract does not promise byte-canonical serialization. Stable map-key ordering may be specified for reproducible representation, but current evidence does not make global sorting a semantic requirement; do not sort order-sensitive source facts.

## 16. SOURCE_SCAN_ELIMINATION_TEST_TARGET
BEST_EXISTING_FILE=tests/test_completeness_freshness_parity_proof.py
BEST_NEARBY_CASE=test_transitive_reexport_late_provider_matches_full_oracle (lines 933-1000): temp repo, normal update_file, re-export chain and fresh ContextorFacade/hydration oracle. Helpers _build_full_static_state and _assert_full_parity are at lines 33-80.
RELATED_BASELINE=tests/test_reference_fusion_integration.py::test_compact_reexport_oracle_and_artifact_output_parity (188-235) proves compact assembly equals legacy AST map for package/cycle fixture.
FUTURE_GATE:
1. Many modules; fresh full canonical baseline; assert facts key domain equals modules.
2. Change only one provider/re-export module.
3. During normal update_file allow changed source parse, trap all unchanged Module.ast_tree accesses, require zero.
4. Guard _assemble_reexport_map to prove it receives complete candidate RAM facts and performs no disk/source operation.
5. Compare new family and affected canonical outputs with fresh full oracle; current _assert_full_parity does not include this family.
6. Disable AST trap before creating the full oracle so only incremental path is measured.
NO TEST WAS ADDED OR RUN.

## 17. REMAINING_LEGACY_REEXPORT_CALLERS
DIRECT_EVIDENCE:
- plan_executor.py:774 (RECOMPUTE) and :880 (artifact_consumption) call _build_reexport_map(candidate.modules).
- shared.py:271-287 loops all modules and accesses ast_tree; Module.ast_tree invokes _get_cached_ast, which stats and parses on a cache miss (domain/module.py:16-38, 58-60).
- reference/engine.py:218 calls it from _legacy_build_symbol_references, explicitly documented as a legacy reference/test helper.
- Tests directly use the adapter: test_reexport_reference_semantics.py, test_reference_fusion_semantic_core.py, test_reference_fusion_integration.py:216-218.
CONCLUSION: Retain _build_reexport_map/cache as legacy/reference adapter if those paths remain. Incremental executor can stop using it after a validated complete canonical facts map is available and it calls _assemble_reexport_map directly. Two incremental call sites exist today.

## 18. IMPLEMENTATION_BLOCKERS
DISCOVERY_EVIDENCE_BLOCKERS=NONE
REQUIRED_NEXT_DESIGN_GATES:
- Invalidate every previously accepted snapshot generation that lacks the required family; adding default {} alone is unsafe.
- Define explicit full-analysis recovery before incremental work when an old snapshot is rejected. Current loaders do not automatically analyze.
- Keep re-export completeness independent of broad reference visitor availability/failure.
- Ensure __all__-only changes update the facts despite the current empty-plan early return.
These are source-backed constraints, not unresolved discovery evidence.

## 19. FILES_CHANGED
FILES_CHANGED=NONE (production/test/docs)
walkthrough.md is the required report output and excluded from source/test diff accounting.
ACTUAL_DIFF=DIFFS=NONE

