# CPA_CANONICAL_STAR_IMPORT_SEMANTIC_PARITY_DISCOVERY

STATUS=DISCOVERY_COMPLETE_WITH_UNSPECIFIED_METADATA_CONTRACT
HEAD=45d130810c705f1b9260268524ce88c638c92265
WORKTREE_STATE=CLEAN at task start and after diagnostics; git status --short emitted no entries.
ACCEPTED_UNCOMMITTED_BASELINE=The prior re-export implementation was accepted by instruction and was not reverted. In this checkout it is already represented at HEAD; no uncommitted changes were present.
CONTEXTOR_EVIDENCE=Contextor LIVE revision 1511; canonical_state=fresh, artifact_consumption=fresh, lineage=fresh, resync_required=false, provenance=live. Fact-lineage query reports workspace_sync=unverified by design. Contextor call-context for _rebuild_consumer_slice reports workspace_sync=verified at the same revision.
CANONICAL_OWNER=RepositoryAnalysisState.artifact_consumption. Contextor contextor_fact_lineage confirmed full producer state_manager.build_canonical_artifact_consumption, full materializer ContextorFacade.analyze_project, incremental producer plan_executor._rebuild_consumer_slice, incremental updater IncrementalAnalysisEngine._apply_delta_and_commit, and live-snapshot persistence/hydration. Public projections include get_artifact_blast_radius and get_module_blast_radius. No lineage gaps were returned.
CALL_CONTEXT=Contextor get_symbol_call_context resolved A2180/1 as contextor.core.analysis.incremental.plan_executor::_rebuild_consumer_slice. execute_refresh_plan calls it at lines 855 and 948; it calls _resolve_canonical_target_keys at line 467. get_symbol_lineage resolved the same active artifact but returned a preview because the complete candidate was 148193 bytes; no semantic payload was fetched from that preview.

FULL_SCAN_STAR_IMPORT_PATH:
1. ImportRef is defined in contextor/core/domain/imports.py. It stores module, level, names, is_from_import, is_local, and type_only. The indexer visitor constructs it for ast.ImportFrom in contextor/core/symbol_engine/indexer.py::visit_ImportFrom; for the fixture c, the raw source fact is module='b', names=['*'], level=0, is_from_import=True.
2. contextor.core.reference.index::extract_compact_reference_facts copies each ImportRef's module, names, and level into compact facts['imports']; the source-local facts also include re-export facts.
3. contextor.core.symbol_engine.indexer::index_repository collects worker reference_facts into IndexResult.reference_facts_by_module. ContextorFacade.analyze_project passes that map to contextor.core.reference.index::assemble_reference_index_or_fallback.
4. assemble_reference_index_or_fallback uses RepositoryReferenceIndex.from_compact_facts when the module domain is complete. In from_compact_facts, an imported name '*' is placed in star_imports_by_source[source_module].append(importer_module), yielding source b -> consumer c for the fixture. This branch does not consult __all__.
5. RepositoryReferenceIndex.build_symbol_references projects a target S as imported_from by c when S starts with source_prefix + '.'. Independently, it adds c when a visible re-export-map key starts with source_prefix + '.' and maps to S. The first condition is an unconditional module-prefix test; it does not check explicit_all or underscore visibility. The second condition uses the re-export map.
6. contextor.core.reporting_layer.artifact_usage_report invokes contextor.core.api.api_consumers::extract_api_consumers. That function copies references['imported_from'] into usage['api_imports'] and includes api_imports in the consumers union.
7. ContextorFacade.analyze_project calls state_manager.build_canonical_artifact_consumption on the raw artifact report and materializes RepositoryAnalysisState.artifact_consumption.

FULL_SCAN_STAR_IMPORT_SEMANTICS:
- Direct star-import projection does not filter a target in source module b by b.__all__ and does not exclude underscore names. Every canonical target whose qualified spelling starts b. receives c through the first prefix condition, including b::__all__ when that artifact exists.
- Re-exported original targets such as a::imported are projected through the reexports map. _assemble_reexport_map uses each module's explicit_all, bindings, and star_sources: explicit_all restricts re-exported bindings; when explicit_all is absent, leading-underscore re-export names are filtered; star_sources are expanded by a fixed-point loop and cyclic mappings are discarded by the visited-set resolver.
- Thus full scanning uses __all__ for visible/transitive re-export aliases, but not for direct canonical targets in the star-imported module. The full canonical artifact-consumer behavior is broader than the re-export map's exported-name set.
- b::__all__ is not handled by a special metadata branch in build_symbol_references. It matches the same b. prefix as other module targets.

INCREMENTAL_STAR_IMPORT_FACTS:
Observed ModuleUsageFacts for c in the failing fixture, both before and after changing b.__all__ from ['foo'] to []:
imports=['b', 'b.*']
aliases=[('*', 'b.*')]
direct_calls=['foo']
runtime_calls=[]
qualified_refs=[]
reference_evidence=[('b.*', 'api_imports', '', 1), ('foo', 'direct_calls', 'run', 4)]
The consumer module's exact source import remains from b import *. The raw ImportRef is module='b', names=['*'], level=0. ModuleUsageFacts preserves the wildcard as b.* and as alias '*' -> 'b.*'; it also preserves the canonical api_imports reference evidence for b.*.

INCREMENTAL_RESOLUTION_TRACE:
- STAR_IMPORT_RAW_FACT='b'; AFTER_ALIAS_RESOLUTION='b'; AFTER_REEXPORT_RESOLUTION='b'; CANONICAL_TARGET_KEYS=[]; status=unresolved; if resolved, its channel would be api_imports.
- STAR_IMPORT_RAW_FACT='b.*'; AFTER_ALIAS_RESOLUTION='b.*'; AFTER_REEXPORT_RESOLUTION='b.*'; CANONICAL_TARGET_KEYS=[]; status=unresolved; if resolved, its channel would be api_imports.
- _resolve_alias only follows an exact alias or longest alias prefix; the stored '*' alias does not expand b or b.*.
- _resolve_reexport only follows an exact or longest dotted re-export prefix; the post-update relevant re-export map is empty, so b.* remains b.*.
- _resolve_canonical_target_keys accepts an exact canonical target or a complete dotted target that matches canonical identities. It does not expand a wildcard. Neither b nor b.* names a canonical artifact target, so the api_imports channel is not installed for these facts.
- _rebuild_consumer_slice tags consumer_facts.imports as api_imports facts, resolves each fact through those three resolvers, and installs only resolved canonical keys. There is no wildcard expansion step in this function.

FAILING_FIXTURE_DIAGNOSTIC:
Fixture: a.py defines foo; b.py imports foo and initially declares __all__=['foo']; c.py does from b import * and defines run() returning foo(); the existing fixture also has noise_1.py through noise_3.py.
Fresh baseline full analysis errors=[]; initial canonical b::__all__ entry={'consumers':['c'],'channels':{'c':['api_imports']}}.
After b changes to __all__=[]:
INCREMENTAL_STATUS=UPDATED
INCREMENTAL_SHADOW_PATCH_FAMILIES=['reexport_facts','artifact_consumption','cached_analytics']
INCREMENTAL_EXECUTION_TRACE={'graph_recomputations': [], 'patch_families': ['reexport_facts','artifact_consumption','cached_analytics'], 'recompute_modules': ['c'], 'reparse_modules': []}
INCREMENTAL_B_ALL_ENTRY={'consumers': [], 'channels': {}}
FULL_ANALYSIS_ERRORS=[]
FULL_B_ALL_ENTRY={'consumers': ['c'], 'channels': {'c': ['api_imports']}}
INCREMENTAL_REEXPORT_FACTS_ABC:
a={'exporter':'a','explicit_all':None,'bindings':{'foo':'a.foo'},'star_sources':[]}
b={'exporter':'b','explicit_all':[],'bindings':{'foo':'a.foo'},'star_sources':[]}
c={'exporter':'c','explicit_all':None,'bindings':{'run':'c.run'},'star_sources':['b']}
FULL_REEXPORT_FACTS_ABC=equal to incremental for a, b, and c.
INCREMENTAL_REEXPORT_MAP_ABC={}
FULL_REFERENCE_INDEX_REEXPORT_MAP_ABC={}
INCREMENTAL_C_TARGETS=[]
FULL_C_TARGETS=['b::__all__']
Therefore the mismatch is not caused by different current re-export facts/maps. The full canonical target b::__all__ is included through the generic b. prefix rule; the incremental star-import facts do not resolve to any canonical target.

MICRO_ORACLE_RESULTS:
Each row is a fresh ContextorFacade full analysis on a separate temporary directory. All three returned errors=[].

MICRO_EXPLICIT: b has from a import imported, PUBLIC=1, _PRIVATE=2, __all__=['imported','PUBLIC'].
- a::imported={'consumers':['b','c'],'channels':{'b':['api_imports'],'c':['api_imports']}}
- b::PUBLIC={'consumers':['c'],'channels':{'c':['api_imports']}}
- b::_PRIVATE={'consumers':['c'],'channels':{'c':['api_imports']}}
- b::__all__={'consumers':['c'],'channels':{'c':['api_imports']}}
- All targets with c as consumer: ['a::imported','b::PUBLIC','b::_PRIVATE','b::__all__']
- Full reference-index re-export map for a/b/c: {'b.imported':'a.imported','c.PUBLIC':'b.PUBLIC','c.imported':'a.imported'}

MICRO_EMPTY: b has from a import imported, PUBLIC=1, _PRIVATE=2, __all__=[].
- a::imported={'consumers':['b'],'channels':{'b':['api_imports']}}
- b::PUBLIC={'consumers':['c'],'channels':{'c':['api_imports']}}
- b::_PRIVATE={'consumers':['c'],'channels':{'c':['api_imports']}}
- b::__all__={'consumers':['c'],'channels':{'c':['api_imports']}}
- All targets with c as consumer: ['b::PUBLIC','b::_PRIVATE','b::__all__']
- Full reference-index re-export map for a/b/c: {}

MICRO_IMPLICIT: b has from a import imported, PUBLIC=1, _PRIVATE=2, and no __all__.
- a::imported={'consumers':['b','c'],'channels':{'b':['api_imports'],'c':['api_imports']}}
- b::PUBLIC={'consumers':['c'],'channels':{'c':['api_imports']}}
- b::_PRIVATE={'consumers':['c'],'channels':{'c':['api_imports']}}
- b::__all__=MISSING because the module has no such artifact.
- All targets with c as consumer: ['a::imported','b::PUBLIC','b::_PRIVATE']
- Full reference-index re-export map for a/b/c: {'b.imported':'a.imported','c.PUBLIC':'b.PUBLIC','c.imported':'a.imported'}

EXPLICIT_ALL_BEHAVIOR=NO for the direct full canonical star-consumer projection: MICRO_EMPTY still attributes c to b::PUBLIC and b::_PRIVATE. YES only for the distinct re-export-map alias expansion, which omits a::imported when b.__all__ is empty.
UNDERSCORE_BEHAVIOR=NO for direct full canonical star-consumer projection: b::_PRIVATE has c as consumer with explicit, empty, and absent __all__. The re-export-map path does filter private names when __all__ is absent, unless explicitly listed in __all__.
FULL_STAR_IMPORT_TRACKS_ALL_METADATA_DEPENDENCY=YES in observed canonical output: c is a consumer of b::__all__ both when its value lists foo and when it is empty. This is produced by the generic b. prefix match, not a dedicated metadata-dependency rule.

B_ALL_ENTRY_PARITY:
Failing fixture after __all__=[]:
incremental artifact_consumption['b::__all__']={'consumers': [], 'channels': {}}
full artifact_consumption['b::__all__']={'consumers': ['c'], 'channels': {'c': ['api_imports']}}
Micro-oracle confirms the full entry remains for explicit and empty __all__, and is absent when b has no __all__ artifact.

EXPLICIT_ALL_DEPENDENCY_AND_EXISTING_CONTRACTS:
- tests/test_reexport_reference_semantics.py::test_star_reexport_uses_explicit_all_and_remains_transitive asserts the filtered re-export map (hidden binding absent) and a transitive imported_from result.
- tests/test_reexport_reference_semantics.py::test_direct_star_reexport_includes_public_source_definition asserts re-export-map contents for a star re-export; it does not assert direct canonical artifact visibility for hidden/private names.
- tests/test_reference_fusion_semantic_core.py includes a star_consumer fixture and asserts AST-build/compact-facts equivalence, not an exact visible consumer set for direct star imports.
- tests/test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle asserts c is recomputed and compares incremental state with a fresh full oracle, but does not specify a dedicated __all__ metadata edge rule.
ALL_METADATA_DEPENDENCY_CONTRACT=UNSPECIFIED; no inspected test/comment/docs states whether b::__all__ is intentionally a special dependency. Current observed behavior treats it as an ordinary module-qualified artifact target.

REEXPORT_MAP_SUFFICIENCY=NO.
_assemble_reexport_map contains the filtered transitive re-export alias map. It does not itself contain direct local artifact targets or the per-module explicit_all state needed to decide visibility of local definitions. The necessary visibility inputs remain in reexport_facts_by_module (explicit_all, bindings, star_sources) and candidate.artifacts. The map alone cannot perform the complete direct-star target projection.

CANONICAL_FACT_SUFFICIENCY=YES for deterministic RAM-only repository-static projection:
- ModuleUsageFacts for the consumer records the star source/wildcard (imports b and b.*, alias '*' -> b.*, reference_evidence b.* / api_imports).
- reexport_facts_by_module records exporter, explicit_all including the distinction None vs [], bindings, and star_sources.
- candidate.artifacts supplies canonical target identities and the direct module artifact domain, including b::__all__ when present.
These facts are sufficient to decide visibility and map imported/re-exported names without reopening source/AST. The current _rebuild_consumer_slice does not use them to expand the wildcard; sufficiency is not an implementation claim.

PROPAGATION_CLASSIFICATION:
STAR_IMPORT_RECOMPUTE_SEED=PASS; after __all__ changed from ['foo'] to [], execution_trace.recompute_modules=['c'].
STAR_IMPORT_SLICE_REBUILD=FAIL; c was recomputed, but the rebuilt incremental consumer slice had no resolved target for b or b.*, producing no consumer entry for b::__all__ while the full canonical entry contains c/api_imports.

REEXPORT_MAP_SUFFICIENCY=NO
CURRENT_FACTS_SUFFICIENT_FOR_RAM_ONLY_STAR_IMPORT_PARITY=YES

DIRECT_EVIDENCE:
- Five fresh full analyses (baseline and post-update oracle for the failing fixture, plus three micro-oracle variants) completed with errors=[]; all fixtures were created under temporary directories outside tracked repository files.
- Exact incremental/full entries, full/incremental re-export facts/maps, ModuleUsageFacts values, canonical resolver outcomes, execution trace, and complete micro-oracle consumer target sets are recorded above.
- Contextor artifact-consumption fact lineage at revision 1511 returned status=ok, fresh canonical state/family, resync_required=false, and no unresolved lifecycle gaps.
- Contextor caller/callee evidence at revision 1511 showed execute_refresh_plan -> _rebuild_consumer_slice and its call to _resolve_canonical_target_keys.
- No pytest node and no full repository test suite were run. No code, test, schema, snapshot, or docs file was edited. Temporary diagnostic script was removed.

CODE_PATH_PROVED:
- Full direct star projection is the unconditional source-prefix branch in RepositoryReferenceIndex.build_symbol_references; re-export expansion is a separate visible-alias branch.
- Incremental consumer reconstruction has no star expansion step; its facts pass through alias resolution, re-export resolution, then exact canonical target resolution.
- Full canonical consumption is installed from the artifact report; incremental execution installs the rebuilt consumer slice into RepositoryAnalysisState.artifact_consumption.

CONTRACT_PROVED:
- Existing re-export tests prove explicit_all filtering for the re-export map and transitive imported_from attribution.
- Existing tests prove full/incremental parity is checked for the all-only update and c is expected to be recomputed.
- Existing tests inspected do not establish a separate direct-star visible-name or __all__ metadata-dependency contract.

INFERENCE:
- Relative to Python star-import exported-name visibility, the full canonical direct-star consumer projection is overbroad, while incremental projection omits the star-import targets. That yields a two-path semantic gap. This classification describes the observed projection against exported-name visibility; it does not establish whether the project intentionally chose a conservative dependency policy.
- The exact implemented cause of the failing b::__all__ mismatch is proven: c recomputes, but b and b.* remain unresolved by the incremental exact-target pipeline; the full path matches b::__all__ by module prefix.

UNKNOWN:
- Intended policy for a dedicated __all__ metadata dependency is not specified by the inspected repository contracts. No decision about preserving that edge as a special canonical relation is inferred.
- No dynamic/runtime star-import behavior is claimed beyond the observed source-static full and incremental paths.

FILES_CHANGED=NONE
DIFFS=NONE
PYTEST=NOT_RUN
FULL_REPOSITORY_PYTEST=NOT_RUN
MCP_DESKTOP_BACKEND_RESTART=NOT_PERFORMED

STAR_IMPORT_GAP=BOTH_PATHS

FULL_STAR_IMPORT_RESPECTS_EXPLICIT_ALL=NO
FULL_STAR_IMPORT_RESPECTS_UNDERSCORE_VISIBILITY=NO
FULL_STAR_IMPORT_TRACKS_ALL_METADATA_DEPENDENCY=YES
ALL_METADATA_DEPENDENCY_CONTRACT=UNSPECIFIED
REEXPORT_MAP_SUFFICIENT_FOR_PRECISE_STAR_IMPORT_PROJECTION=NO
CURRENT_FACTS_SUFFICIENT_FOR_RAM_ONLY_STAR_IMPORT_PARITY=YES
STAR_IMPORT_RECOMPUTE_SEED=PASS
STAR_IMPORT_SLICE_REBUILD=FAIL
READY_FOR_DESIGN=NO
