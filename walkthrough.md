# CPA_REEXPORT_LINEAGE_QUERY_INTEGRATION_DISCOVERY

## STATUS
STATUS=DISCOVERY_COMPLETE
SCOPE=DISCOVERY_ONLY
HEAD_BEFORE=239c609beef6bc92ef661024ef014c0b640b215d
SOURCE_DRIFT=NONE_OBSERVED
FILES_CHANGED=NONE
DIFFS=NONE
TESTS_RUN=NONE
FULL_REPOSITORY_PYTEST=NOT_RUN
REPORT_NOTE=walkthrough.md is the requested report and is excluded from FILES_CHANGED.

Evidence labels:
- DIRECT_EVIDENCE = observed current Contextor response, direct fixture result, or literal persisted/source facts.
- CODE_PATH_PROVED = current implementation path was retrieved through Contextor and corroborated against source anchors.
- CONTRACT_PROVED = tool/schema/docs/test contract directly states the behavior.
- INFERENCE = evidence-based integration implication, not an implemented or certified design.
- UNKNOWN = not established in this discovery.

## RUNTIME_FRESHNESS
MCP_RUNTIME_FRESH=YES
CURRENT_CANONICAL_STATE_FRESH=YES
RESYNC_REQUIRED=NO
WORKSPACE_SYNC=verified
REEXPORT_FACT_DOMAIN_EQUALS_MODULE_DOMAIN=YES
LIVE_REVISION=1528
ARCHITECTURE_REPORT_COMMIT=239c609beef6bc92ef661024ef014c0b640b215d
ARCHITECTURE_REPORT_GENERATED_AT=2026-10-06T17:38:59.679438

DIRECT_EVIDENCE: Contextor LIVE returned retained event revision 1528, latest revision 1528, continuous events, resync_required=false, and DESKTOP_ANALYSIS PUBLISHED. The current architecture report commit equals HEAD. Current source lookups reported revision 1528, canonical_state=fresh, workspace_sync=verified. The current fixture also established set(reexport_facts_by_module) == set(modules).

CODE_PATH_PROVED: These four current source symbols were resolved by Contextor at the fresh revision and their current source anchors were checked:
- C:\Temp\Contextor_Repo\contextor\core\reference\shared.py::_canonicalize_package_reference_target (lines 41-103)
- C:\Temp\Contextor_Repo\contextor\core\reference\shared.py::_assemble_module_export_surfaces (lines 434-441)
- C:\Temp\Contextor_Repo\contextor\core\analysis\refresh_planner.py::_find_dependent_consumers (lines 14-67)
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py::_rebuild_consumer_slice (lines 401-678)

UNKNOWN/LIMITATION: The older global get_analysis_status record was dated 2026-09-25 / revision 1414. It was treated as historical and was not used as evidence of current runtime freshness. The Contextor tool registry exposed the active 27 mcp__contextor__* tools; no separate deferred-tool inventory lister was exposed in the available tool metadata.

## CANONICAL_LINEAGE_MODEL
LINEAGE_CANONICAL_OWNER=C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py::RepositoryAnalysisState.lineage_facts_by_source (lines 83-168)
LINEAGE_FULL_MATERIALIZER=C:\Temp\Contextor_Repo\contextor\core\api\facade.py::_materialize_full_analysis_lineage (lines 264-425; state assembly lines 905-980)
LINEAGE_INCREMENTAL_UPDATER=C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py::IncrementalAnalysisEngine._update_candidate_lineage_slice (lines 208-390; candidate commit/update path lines 149-196, 956-993)
LINEAGE_QUERY_INDEX_OWNER=C:\Temp\Contextor_Repo\contextor\core\lineage_query\index.py::build_lineage_query_indexes / patch_lineage_query_indexes (lines 38-112)
LINEAGE_FRESHNESS_OWNER=C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py::_update_candidate_lineage_slice plus C:\Temp\Contextor_Repo\contextor\core\live_state\store.py::_normalize_lineage_facts_state / _normalize_lineage_query_index_state (lines 336-465)

DIRECT_EVIDENCE: RepositoryAnalysisState keeps source-keyed canonical materialized lineage slices and separate owner/source indexes, query-index state, semantic anchor completeness, lineage family state/version, modules/artifacts, and reexport_facts_by_module. Full analysis extracts source slices, resolves them against active module/artifact/owner/interface identities, builds query indexes, and assembles state. Incremental update replaces/removes the edited source slice and patches/rebuilds query indexes; identity synchronization can re-resolve retained slices without reparsing unchanged sources.

CODE_PATH_PROVED: The full LineageResolutionContext contains active_module_ids, active_artifact_ids, active_owner_ids, and interface_descriptors. The context does not receive reexport_facts_by_module. Incremental _update_candidate_lineage_slice uses the analogous active identity/descriptor inputs and likewise does not receive the canonical reexport map. Reexport facts are maintained on a separate update/materialization path.

DIRECT_EVIDENCE: Deleted-source invalidation removes that source's lineage slice and rebuilds indexes; changed-source update replaces the slice, then patches/rebuilds indexes. Snapshot hydration normalizes source slices and reconstructs query indexes.

## LINEAGE_FACT_SCHEMA
Schema source: C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py. Canonical container and index state: C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py.

| FULL_PATH / SYMBOL | FIELDS | PERSISTED | CANONICAL | DERIVED |
|---|---|---:|---:|---:|
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: ExtractedLineageSourceFacts (315-333) | source_key, source_fingerprint, anchors, flows, surfaces, status, resource_limit_reason | NO | NO | YES |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: ExtractedOccurrenceRef | local_id | NO | NO | YES, source-slice local identity |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: ExtractedSymbolicRef | kind, module_name, symbol_name, source_local_id | NO | NO | YES, symbolic import/callee/definition target |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: ExtractedAnchorFact | local_id, kind, span, owner_local_id | NO | NO | YES |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: ExtractedFlowFact | local_id, source, target, relation, evidence, resolution_kind, confidence, dynamic_boundary, provider, owner_local_id | NO | NO | YES |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: ExtractedSurfaceFact | local_id, kind, exposed, evidence, resolution_kind, confidence, declared_name, dynamic_boundary, provider, declaration_evidence | NO | NO | YES |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: MaterializedOccurrenceRef | source_key, source_fingerprint, local_id | YES, nested in materialized slice | YES, canonical source-local occurrence | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: ProviderRef | provider_id, provider_version | YES, nested when present | YES, provider provenance | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: SourceLineageManifest (427-465) | source_key, source_fingerprint, semantic_version, status, anchor_count, flow_count, surface_count, resource_limit_reason, semantic_anchor_bindings_materialized, anchor_ownership_materialized, flow_ownership_materialized, interface_descriptors_materialized | YES | YES, as the persisted slice manifest | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: MaterializedLineageSourceFacts (483-596) | manifest, anchors, flows, surfaces, interface_descriptors, semantic_endpoint_origins, semantic_anchors | YES | YES, per source slice | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: MaterializedAnchorFact | local_id, reference, kind, span, owner_local_id | YES | YES, within its source slice | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: MaterializedFlowFact | local_id, source, target, relation, evidence, resolution_kind, confidence, dynamic_boundary, provider, owner_local_id | YES | YES, within its source slice | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: MaterializedSurfaceFact | local_id, kind, exposed, evidence, resolution_kind, confidence, declared_name, dynamic_boundary, provider, declaration_evidence | YES | YES, within its source slice | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: SemanticAnchorBinding | owner_id, qualified_name, reference | YES, nested in materialized slice | YES, within source slice | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: MaterializedSymbolicRef | source_key, source_fingerprint, kind, module_name, symbol_name, source_local_id | YES, nested in materialized slice | YES, symbolic unresolved/local reference | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: SemanticEndpoint | owner_id, slot | YES, nested in materialized slice | YES, canonical identity reference | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: SemanticEndpointOrigin | source_key, source_fingerprint, fact_local_id, endpoint_role, kind, module_name, symbol_name, source_local_id | YES, nested in materialized slice | YES, origin/provenance of a semantic endpoint | NO |
| C:\Temp\Contextor_Repo\contextor\core\domain\lineage_facts.py :: SemanticInterfaceDescriptor | owner_id, slots, signature_digest | YES, nested in materialized slice | YES, canonical owner interface | NO |
| C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py :: RepositoryAnalysisState.lineage_facts_by_source (83-168) | source_key -> MaterializedLineageSourceFacts | YES | YES | NO |
| C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py :: lineage_owner_source_index / lineage_source_owner_index | owner_id -> source keys; source key -> owner IDs | YES in state snapshot | derived from materialized source slices | YES |
| C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py :: lineage_query_index_state | query-index freshness/version and index coverage state | YES in state snapshot; rebuilt on hydration | derived | YES |
| C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py :: lineage_semantic_anchor_bindings_complete | semantic anchor binding completeness | YES in state snapshot; revalidated on hydration | derived/completeness contract | YES |
| C:\Temp\Contextor_Repo\contextor\core\lineage_query\index.py :: build_lineage_query_indexes / patch_lineage_query_indexes (38-112) | semantic owner IDs <-> source keys plus index freshness/coverage | index state serialized; recomputed on hydration | NO, derived query projection | YES |
| C:\Temp\Contextor_Repo\contextor\core\analysis\lineage_materialization.py :: LineageResolutionContext | active module IDs, artifact IDs, owner IDs, interface descriptors | NO | NO | YES, transient resolver input |

CONTRACT_PROVED: ExtractedLineageSourceFacts is parsed-AST output, source-local, and not canonical cross-source data. MaterializedLineageSourceFacts enforces same-slice occurrence references; foreign occurrence references are not accepted. Materialized semantic endpoints are canonical identity boundaries. Extracted facts are transient; materialized lineage slices are persisted, with large lineage state eligible for sidecar storage.

DIRECT_EVIDENCE: The relation enum includes binding/assignment/argument/return/call/state/alias/callback/inheritance/override/exposure/default/public-name relations. It has no import/reexport relation family. Import/reexport appears as surface facts and symbolic references, where extraction/materialization emitted them; there is no general multi-hop reexport chain fact.

## CURRENT_REEXPORT_LINEAGE
DIRECT_EVIDENCE: Current lineage can expose some one-hop reexport surfaces when the consumer has a materialized REEXPORT surface whose target resolves to a provider SemanticEndpoint. It does not have an authoritative complete graph for multi-hop aliases. In the three-module fixture, b's direct public_foo surface was attached to a.foo; c's exported surface remained a symbolic reference to b.public_foo and did not attach to a.foo's semantic owner.

CODE_PATH_PROVED: Full and incremental lineage resolution receive canonical owner/interface identity inputs but no reexport_facts_by_module. This is the source boundary where current lineage materialization does not consume canonical reexport facts.

| Case | Current result | Classification |
|---|---|---|
| from x import y | A one-hop REEXPORT surface may be materialized and visible from the provider query; not a recursive import graph | PARTIAL |
| from x import y as z | Direct alias can appear as declared_name plus provider SemanticEndpoint; exact query by alias is not generally a catalog target | PARTIAL |
| from .x import y | Canonical reexport fact resolves package-relative provider identity; lineage/query only exposes a direct surface where materialized | PARTIAL |
| from x import * | Export-surface/reexport machinery handles visibility; lineage surfaces do not consistently connect importer aliases to target owner | PARTIAL |
| __all__ | Canonical export surfaces use it; lineage surfaces are only partial and source-dependent | PARTIAL |
| transitive re-export | Immediate facts are preserved; query lineage does not traverse all hops | PARTIAL |
| package __init__ façade | Canonical reexport facts normalize façade/exporter and origin; alias query is not represented as an exact lineage target | PARTIAL |

## QUERY_SURFACES
The active Contextor registry was inspected; applicable MCP documentation was read before tracing. Rows describe direct source of truth at the query surface. "Indirect" means the tool consumes a canonical projection derived using reexports, rather than reading reexport_facts_by_module itself.

| TOOL | CURRENT_SOURCE_OF_TRUTH | USES_LINEAGE | USES_REEXPORT_FACTS | CAN_RETURN_REEXPORT_CHAIN | PACKAGE_INIT_IDENTITY_AWARE | STAR_IMPORT_AWARE |
|---|---|---:|---:|---:|---:|---:|
| get_symbol_lineage | canonical lineage slices, semantic anchors, owner/source query indexes | YES | NO directly; may return a materialized one-hop REEXPORT surface | PARTIAL | NO for façade alias query | NO for importer chain |
| get_symbol_call_context | ModuleUsageFacts.symbol_calls/direct call context | NO | NO directly | NO | NO | NO; wildcard bare call may be ambiguous |
| get_symbol_implementation | canonical artifact registry and module/source range | NO | NO | NO | NO alias-chain resolution | NO |
| get_artifact_blast_radius | canonical artifact_consumption and dependent graph | NO | YES, indirectly through artifact-consumption projection | NO semantic hop chain | YES for normalized canonical origin in consumption; no alias node chain | YES for export/consumption projection; no lineage chain |
| get_module_context | canonical modules and dependency_graph | NO | NO directly | NO | NO alias-chain resolution | NO symbol visibility chain |
| search_artifacts | canonical artifact registry/modules/dependency projection | NO | NO directly | NO | NO alias-chain resolution | NO symbol visibility chain |
| get_file_edit_context | modules, dependency_graph and consumer projection | NO | NO directly | NO | NO alias-chain resolution | NO symbol visibility chain |
| contextor_fact_lineage | supported fact families: artifact_consumption, syntax_diagnostics, symbol_calls | NO for symbol lineage/reexport chain | NO for reexport facts | NO | NO | NO |

DIRECT_EVIDENCE: The registry included 27 Contextor tools. contextor_fact_lineage documents only the three fact families above; it is not the symbol-lineage or reexport-chain API. get_artifact_blast_radius can reflect reexport-aware artifact consumption, but that output is not a lineage edge trace.

CODE_PATH_PROVED: get_symbol_call_context reads module usage symbol_calls; get_symbol_implementation resolves artifacts/modules; get_module_context reads modules/dependency_graph; search_artifacts searches artifact/module projections; get_file_edit_context uses modules/dependency/consumer context. These paths do not directly read the canonical reexport fact map or lineage slices.

## GET_SYMBOL_LINEAGE_TRACE
MCP entrypoint: C:\Temp\Contextor_Repo\contextor\mcp\tools\get_symbol_lineage.py::get_symbol_lineage (88-168)
Runtime narrow query: C:\Temp\Contextor_Repo\contextor\core\lineage_query\live_query.py::query_live_symbol_lineage (467-551)
Exact target catalog: same file, build_live_lineage_target_catalog (334-424)
Canonical query service: C:\Temp\Contextor_Repo\contextor\core\lineage_query\service.py::LineageQueryService.resolve_target / direct_facts / semantic_sections (485-642, 848-911)

CODE_PATH_PROVED:
MCP request
-> normalize and validate request/sections
-> validate repository path and canonical exact target
-> mcp_runtime.query_live_symbol_lineage_narrow(root, query, sections)
-> RepositoryStateLineageBackend(state)
-> exact artifact ID or exact module::symbol target catalog
-> LineageQueryService resolves target and selects direct facts from source slices
-> selected facts are rendered as the response.
The catalog does not include reexport facts and uses exact identity lookup, not fuzzy/recursive alias search. The direct query collects source-slice semantic anchors/flows/surfaces; it does not walk canonical reexport facts recursively. Lexical traversal is a bounded local-scope traversal, not reexport traversal. Query is narrow LIVE canonical RAM; docs/source do not provide snapshot/disk fallback for this tool.

Fixture observations:
- a::foo resolves. Its selected direct surfaces include b's REEXPORT public_foo, exposed as the canonical foo SemanticEndpoint.
- c::exported is not_found. c's exported surface refers symbolically to b.public_foo; the chain c.exported -> b.public_foo -> a.foo is not returned.
- pkg.provider::run resolves and includes the package-init REEXPORT public_run surface.
- pkg::public_run and pkg.__init__::public_run are not_found.
- star_src::visible resolves; star_mid::visible and star_dst::visible are not_found.
- No observed resolved query edge pointed to a wrong canonical target.

CURRENT_LINEAGE_RESULT=provider may expose an immediate REEXPORT surface; reexport aliases are not first-class exact targets and transitive targets are not followed.
MISSING_RELATIONS=c.exported -> b.public_foo and b.public_foo -> a.foo as a traversable authoritative chain; package facade alias identity -> provider origin as query target; star importer alias -> visible canonical origin.
WRONG_RELATIONS=NONE_OBSERVED
AMBIGUOUS_RELATIONS=NONE_OBSERVED_IN_FIXTURE; cyclic aliases are omitted from resolved map rather than arbitrarily selected.
DIRECT_EVIDENCE: Fixture query results above were observed from the core live query on canonical hydrated/incremental states.
CONTRACT_PROVED: MCP API narrows to exact canonical target and selected lineage facts; no recursive alias traversal contract is documented.

## CANONICAL_REEXPORT_SOURCE
REEXPORT_CANONICAL_OWNER=C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py::RepositoryAnalysisState.reexport_facts_by_module (lines 83-168)
REEXPORT_FACT_COMPLETENESS=FULL_DOMAIN_FOR_CURRENT_MODULES
REEXPORT_FACT_PERSISTENCE=YES
REEXPORT_FACT_INCREMENTAL_FRESHNESS=YES, on the exercised add/change/delete and downstream propagation paths

DIRECT_EVIDENCE: Each current module ID has a facts entry; each entry contains exporter, explicit_all, bindings, star_sources. The fresh fixture verified exact module/fact key-domain equality. The facts retain immediate bindings such as b.public_foo -> a.foo and c.exported -> b.public_foo.

CODE_PATH_PROVED:
- contextor\core\reference\shared.py::validate_reexport_facts_by_module checks exact key-domain equality and per-fact shape (154-175).
- materialize_reexport_facts_by_module builds the full facts map and validates it (176-230).
- Full facade materializes canonical reexport facts separately from lineage (facade.py:687-700; state assembly 947-969).
- Incremental plan executor removes entries on deletion and replaces entries on add/change, then validates and assembles the candidate map (plan_executor.py:779-904, 944-960, 1039).
- Snapshot save validates and persists the state; hydration normalizes/validates reexport facts (store.py:121-153, 1462-1487, 1866-2045).
- Package relative import normalization uses _canonicalize_package_reference_target (shared.py:41-103); in fixture the package init fact exporter was pkg, target was pkg.provider.run.

CONTRACT_PROVED: Existing add/change/delete and parse-failure LKG tests in tests\test_completeness_freshness_parity_proof.py:1470-1544 exercise incremental facts lifecycle. Existing package and star semantics are covered by tests\test_reexport_reference_semantics.py.

## REEXPORT_GRAPH_CAPABILITY
CURRENT_REEXPORT_MAP_PRESERVES_INTERMEDIATE_HOPS=NO
CURRENT_FACTS_CAN_DERIVE_INTERMEDIATE_HOPS=YES

DIRECT_EVIDENCE:
- _assemble_reexport_map follows raw edges with a visited set and returns only a resolved final target when traversal exits the raw map (shared.py:444-468). For the fixture it returns c.exported -> a.foo, not the intermediate b.public_foo hop.
- The persisted canonical facts retain immediate source identities: b.public_foo -> a.foo and c.exported -> b.public_foo. Thus the existing facts contain enough edge-by-edge information to derive the intermediate path without AST/source reread. This is an evidence statement about the facts, not a proposal for a new data structure.
- _assemble_module_export_surfaces consumes reexport facts for visible export surfaces (shared.py:335-441).

## PACKAGE_LINEAGE
PACKAGE_LINEAGE_CURRENT_STATE=PARTIAL
PACKAGE_EXTERNAL_IDENTITY_RESOLUTION=canonical reexport facts normalize package façade exporter to pkg and relative provider to pkg.provider.run; exact lineage query for pkg::public_run is not found
PACKAGE_CANONICAL_OWNER_RESOLUTION=provider pkg.provider::run resolves; pkg.__init__::public_run and pkg::public_run do not resolve as façade aliases

DIRECT_EVIDENCE: Fixture:
pkg/__init__.py: from .provider import run as public_run, __all__ = ["public_run"].
Facts record exporter pkg, binding public_run -> pkg.provider.run. The package canonicalizer uses longest real module prefix and package .__init__ fallback. Query of the provider resolves and sees the direct package REEXPORT surface; queries by package façade identity return not_found.

CODE_PATH_PROVED: The MCP lineage target catalog is based on exact artifact IDs or exact module::symbol anchors. It does not consult _canonicalize_package_reference_target or canonical reexport facts. That canonicalizer is used in reference/reexport identity normalization, not in the exact lineage target catalog.

## STAR_IMPORT_LINEAGE
STAR_IMPORT_LINEAGE=PARTIAL
STAR_IMPORT_VISIBILITY_USES_EXPLICIT_ALL=YES
STAR_IMPORT_PRIVATE_FILTER=YES

DIRECT_EVIDENCE: Reexport export-surface assembly applies explicit __all__; when explicit_all is absent it filters names beginning with underscore. In fixture, star_mid and star_dst canonical export surfaces both resolve visible to star_src.visible, while lineage queries for star_mid/star_dst::visible are not_found. A separate no-__all__ fixture confirmed the default underscore filter in canonical export visibility, but b/c/d lineage source slices contained caller facts without REEXPORT surfaces.

CODE_PATH_PROVED: shared.py::_assemble_export_surface_state (335-431) propagates star-visible surfaces iteratively and applies explicit __all__/default private filtering. Incremental _rebuild_consumer_slice uses existing reexport facts and module export surfaces to rebuild affected consumers. Existing parity and AST-forbidden tests demonstrate this consumer/usage path is distinct from lineage query coverage.

BOUNDARY: No canonical artifact c::foo was invented. Current star export visibility is represented by canonical export surfaces and reexport facts, not by a complete importer-owned lineage alias chain.

## ALIAS_LINEAGE
ALIAS_LINEAGE_INTERMEDIATE_HOPS=NO
ALIAS_LINEAGE_FINAL_ORIGIN=NO

DIRECT_EVIDENCE: Canonical reexport facts preserve immediate edges, while _assemble_reexport_map flattens to the final origin. Lineage query sees b's direct alias surface from a's provider query, but c's alias remains symbolic and is not attached to a's semantic owner. Querying c's alias does not resolve. Therefore lineage/query currently exposes neither a complete intermediate chain nor consistent final origin for aliases. The underlying reexport facts do retain the individual hops.

## CYCLE_POLICY
REEXPORT_LINEAGE_CYCLE_POLICY_CURRENT=Cycle-safe reexport resolution; cyclic aliases are omitted from the flattened map and remain unresolved in lineage/query; no arbitrary target or ambiguity is produced.

DIRECT_EVIDENCE: Synthetic a<->b reexport cycle returns no resolved entries from _assemble_reexport_map; existing tests\test_reexport_reference_semantics.py::test_cyclic_reexports_are_not_resolved_arbitrarily asserts that cyclic aliases are not arbitrarily resolved. Canonical facts retain cycle edges. The fixture did not observe a wrong target or an explicit query ambiguity object.

UNKNOWN: The API does not surface a dedicated cycle/unknown lineage result for those aliases; current observed exact query outcome is not_found.

## FULL_LIVE_LINEAGE
FULL_LINEAGE_RESULT=Fresh full oracle exposes the same direct provider surfaces and the same alias/package/star not_found gaps.
LIVE_LINEAGE_RESULT=Incrementally updated canonical state exposes the same direct provider surfaces and the same alias/package/star not_found gaps.
FULL_LIVE_LINEAGE_PARITY=PASS

Fixture protocol and direct output:
1. Fresh full analysis of a temporary fixture containing a provider a with foo/bar, b re-exporting foo as public_foo, c re-exporting b.public_foo as exported, plus package/star/implicit-export cases.
2. Hydrate canonical repository state.
3. Change b's reexport target from a.foo to a.bar and execute engine.update_file(b.py); status UPDATED, affected modules were b and c.
4. Run fresh full analysis for final files and hydrate the oracle.
5. Compare ten query_live_symbol_lineage identities across incremental and full states: a::foo, a::bar, b::public_foo, c::exported, pkg.__init__::public_run, pkg.provider::run, pkg::public_run, star_src::visible, star_mid::visible, star_dst::visible. Compare target statuses and semantic payload, normalizing only revision/provenance metadata.
6. Also compare canonical reexport facts and assembled reexport maps.

DIRECT_EVIDENCE: All ten query results matched; canonical reexport facts and flattened maps also matched. Both analyses returned no validation errors in this main fixture. b::public_foo, c::exported, package façade aliases, star importer aliases were not_found in both. Provider queries that resolve and direct surfaces matched.

LIMITATION: The core query_live_symbol_lineage path was exercised on hydrated/incremental temporary states; the public MCP IPC wrapper was not dispatched against the temporary root. The public wrapper's source path and live runtime contract were traced separately. The fixture's c module was a downstream re-export alias, so evidence is for a three-module provider-to-alias-to-transitive-alias query chain; it does not claim a separate ordinary function-call consumer parity case.

INTERPRETATION: PASS certifies full-vs-incremental parity for queried canonical payloads, not completeness of reexport lineage. This is common-bug parity: both sides omit the same chain/package/star alias targets.

## SEMANTIC_GAP_MATRIX
Status vocabulary is limited to FULL / PARTIAL / ABSENT / INCORRECT / UNKNOWN.

| Case | CANONICAL_REEXPORT_FACTS | LINEAGE_FACTS | QUERY_VISIBLE | FULL | LIVE | STATUS |
|---|---|---|---|---|---|---|
| direct import | FULL: immediate binding retained | PARTIAL: direct REEXPORT surface only where materialized | PARTIAL: provider query can expose surface | PARTIAL | PARTIAL | PARTIAL |
| aliased import | FULL: declared alias and immediate target | PARTIAL: alias surface can bind to provider | PARTIAL: provider surface visible, alias exact query may not resolve | PARTIAL | PARTIAL | PARTIAL |
| relative import | FULL: package-relative target normalized | PARTIAL: direct provider surface in tested package fixture | PARTIAL: provider resolves; alias query does not | PARTIAL | PARTIAL | PARTIAL |
| package __init__ façade | FULL: exporter and provider origin canonicalized | PARTIAL: direct façade surface only | PARTIAL: provider query sees surface; façade exact query not_found | PARTIAL | PARTIAL | PARTIAL |
| explicit __all__ | FULL: explicit export list retained/applied | PARTIAL: some direct surfaces materialized | PARTIAL: export surfaces exist, exact importer alias queries do not | PARTIAL | PARTIAL | PARTIAL |
| implicit public export | FULL: public bindings retained, underscore default filter | ABSENT in tested lineage slices for implicit-import consumers | ABSENT for those consumer aliases | ABSENT | ABSENT | ABSENT |
| star import | FULL: star sources and resolved export surfaces | PARTIAL: importer lineage chain missing | PARTIAL: canonical export visibility works, lineage alias query not_found | PARTIAL | PARTIAL | PARTIAL |
| transitive re-export | FULL: each immediate hop retained | PARTIAL: first direct hop can bind; downstream remains symbolic | PARTIAL: c alias not_found | PARTIAL | PARTIAL | PARTIAL |
| multi-hop aliases | FULL: immediate edge facts retain hops | PARTIAL: no traversable lineage path | PARTIAL: no complete alias result | PARTIAL | PARTIAL | PARTIAL |
| cycles | FULL: cycle edges retained | PARTIAL: no resolved lineage chain | PARTIAL: unresolved/not_found, no wrong target | PARTIAL | PARTIAL | PARTIAL |

DIRECT_EVIDENCE: Matrix reflects fixture facts and query results above. FULL and LIVE columns describe observed analysis/query surfaces, not a claim that either path implements complete reexport lineage.

## INTEGRATION_BOUNDARY
The following are evidence-derived comparisons only; no architecture is selected or designed.

### A. During lineage materialization
EXISTING_OWNER_SUPPORT=YES for source-local extraction, cross-source endpoint resolution, semantic surfaces, full materialization, and incremental slice replacement.
COUPLING=HIGH relative to current contract: both full and incremental materializers currently receive identity/descriptor context but not canonical reexport facts.
PERSISTENCE_IMPACT=If reexport hops become materialized lineage facts, persisted lineage payload/semantic-version validation is implicated; schema impact is UNKNOWN until exact representation is chosen.
INCREMENTAL_UPDATE_IMPACT=Changed/affected slices would need refreshed derived materialization; could use current RAM facts, but existing consumer propagation only proves artifact-consumption/export-surface updates.
QUERY_COST=LOW after materialization.
RISK=Duplicating authoritative reexport semantics in lineage slices and requiring complete invalidation/version rules.

### B. In derived lineage query index/backend
EXISTING_OWNER_SUPPORT=YES; owner/source index builder, patcher, query-index freshness state, and hydration rebuild already exist.
COUPLING=MEDIUM; query backend can combine persisted lineage slices with canonical reexport facts already on RepositoryAnalysisState.
PERSISTENCE_IMPACT=NO for a pure derived RAM query projection under current persisted inputs; existing indexes are rebuilt on hydration.
INCREMENTAL_UPDATE_IMPACT=YES in principle using already patched reexport facts and affected canonical state; no unchanged-source AST read is needed by the existing update path.
QUERY_COST=One-time/revision-scoped index derivation, then bounded query traversal; exact complexity is UNKNOWN pending implementation.
RISK=Freshness/cycle/ambiguity and package/star identity rules must be explicit; index must invalidate/rebuild when either input domain changes.

### C. Directly in the MCP query tool
EXISTING_OWNER_SUPPORT=PARTIAL; get_symbol_lineage already validates requests and dispatches the narrow query, but semantic traversal is owned by the core query/backend.
COUPLING=HIGH to one API surface; other core consumers would remain inconsistent and tool code would need repository semantics.
PERSISTENCE_IMPACT=NO.
INCREMENTAL_UPDATE_IMPACT=Reads latest canonical RAM state, but does not itself maintain update freshness.
QUERY_COST=Repeated traversal per request.
RISK=API-specific duplicate semantics, incomplete reuse by non-MCP callers, and policy logic at transport boundary.

### D. Existing canonical reexport/reference owner
EXISTING_OWNER_SUPPORT=YES for immediate bindings, explicit_all, star visibility, package identity normalization, flattening, and cycle-safe export maps.
COUPLING=MEDIUM/HIGH to reference/export-surface semantics; current owner is not a lineage query service or owner/source lineage index.
PERSISTENCE_IMPACT=NO for current facts; changing persisted reexport schema is not evidenced as necessary.
INCREMENTAL_UPDATE_IMPACT=Current reexport facts and export surfaces already patch from candidate RAM facts and consumer propagation.
QUERY_COST=Low for materialized surfaces/maps; query traversal behavior is not an existing contract here.
RISK=Serving lineage directly from this owner could bypass lineage ownership/provenance/freshness guarantees and duplicate query target handling.

BEST_EXISTING_INTEGRATION_BOUNDARY=B, the existing derived lineage query index/backend, is the strongest evidence-derived candidate: it already owns query index freshness/build/patch/hydration lifecycle while canonical reexport facts are persisted alongside lineage state. This is a candidate boundary only, not an architecture selection.

INFERENCE: Option B has the least evidence of requiring a persisted schema change while keeping semantics in the core query path. The exact graph representation, traversal policy, and API payload remain undecided.

## PERSISTENCE_IMPACT
PERSISTENCE_CHANGE_REQUIRED=NO for the evidence-derived pure RAM query-index/backend candidate
SNAPSHOT_SCHEMA_CHANGE_REQUIRED=NO for that candidate

DIRECT_EVIDENCE: Canonical reexport facts and materialized lineage slices are already persisted. Query indexes are derived from materialized lineage facts and rebuilt on hydration. This discovery found enough immediate-edge facts to derive hops without persisting a second copy.

INFERENCE/BOUNDARY: These NO values apply only to a derived query projection. If a future design instead adds reexport relations to persisted MaterializedLineageSourceFacts, persistence, lineage semantic-version and normalization behavior must be reassessed. No schema design or bump is proposed here.

## INCREMENTAL_IMPACT
CAN_LINEAGE_REEXPORT_UPDATE_BE_RAM_ONLY=YES
UNCHANGED_SOURCE_READ_REQUIRED=NO
UNCHANGED_AST_ACCESS_REQUIRED=NO

DIRECT_EVIDENCE: The incremental reexport patch consumes fresh candidate facts, replaces/deletes the affected module entry, rebuilds export surfaces/consumer slices, and propagates to dependents. Existing focused parity proof covers reexport __all__ changes and an AST-forbidden incremental update; tests\test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle plus the adjacent no-AST-access proof demonstrate the existing update path can update these derived facts in RAM without reading unchanged ASTs.

INFERENCE: A derived lineage query view can consume the resulting canonical RAM maps and indexes without reopening unchanged source. Exact invalidation behavior for a future new lineage projection is not implemented/certified by this discovery.

## TEST_LOCATIONS
No tests were run or changed. Best existing focused locations:
- Lineage fact schema/extraction: C:\Temp\Contextor_Repo\tests\domain\test_lineage_facts.py; C:\Temp\Contextor_Repo\tests\analysis\test_lineage_extraction.py
- Lineage materialization: C:\Temp\Contextor_Repo\tests\analysis\test_lineage_materialization.py; C:\Temp\Contextor_Repo\tests\test_full_analysis_lineage_materialization.py
- Lineage query service/index/live query: C:\Temp\Contextor_Repo\tests\analysis\test_lineage_query_service.py; C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py; C:\Temp\Contextor_Repo\tests\analysis\test_lineage_query_backend.py
- MCP get_symbol_lineage contract/response/runtime: C:\Temp\Contextor_Repo\tests\mcp\tools\test_get_symbol_lineage.py; C:\Temp\Contextor_Repo\tests\mcp\test_runtime_lineage_query.py; C:\Temp\Contextor_Repo\tests\mcp\test_lineage_response.py
- Full/LIVE lineage lifecycle: C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py; C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py
- Reexport semantics, package identity, star, alias, cycle: C:\Temp\Contextor_Repo\tests\test_reexport_reference_semantics.py
Relevant existing node IDs:
tests/test_reexport_reference_semantics.py::test_transitive_aliased_reexport_resolves_to_original_artifact
tests/test_reexport_reference_semantics.py::test_relative_package_init_reexport_resolves_to_provider
tests/test_reexport_reference_semantics.py::test_star_reexport_uses_explicit_all_and_remains_transitive
tests/test_reexport_reference_semantics.py::test_cyclic_reexports_are_not_resolved_arbitrarily
tests/test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle

## DEFERRED_STAR_BOUND_CALL
STAR_BOUND_BARE_CALL_BLOCKS_REEXPORT_LINEAGE_INTEGRATION=NO

DIRECT_EVIDENCE: Existing incremental artifact-consumption/export-surface path uses ModuleUsageFacts.reference_evidence for star sources, resolves visible targets using canonical export surfaces/explicit __all__, and handles a bare call from a wildcard importer without unchanged AST access. The focused reexport parity proof and AST-forbidden test cover that path.

BOUNDARY: This is artifact-consumption/reexport propagation evidence, not evidence that get_symbol_lineage understands a wildcard-bound bare call or emits the import-to-provider lineage chain.

DEFERRED_ITEM=FULL AST SEMANTIC COVERAGE AUDIT

## FINAL_ANSWERS
CURRENT_LINEAGE_HAS_AUTHORITATIVE_REEXPORT_CHAIN=NO
CURRENT_QUERY_HAS_AUTHORITATIVE_REEXPORT_CHAIN=NO
CURRENT_REEXPORT_MAP_PRESERVES_INTERMEDIATE_HOPS=NO
CURRENT_FACTS_CAN_DERIVE_INTERMEDIATE_HOPS=YES
PACKAGE_REEXPORT_LINEAGE_CORRECT=PARTIAL
STAR_IMPORT_LINEAGE=PARTIAL
FULL_LIVE_LINEAGE_PARITY=PASS
PERSISTENCE_CHANGE_REQUIRED=NO
SNAPSHOT_SCHEMA_CHANGE_REQUIRED=NO
CAN_LINEAGE_REEXPORT_UPDATE_BE_RAM_ONLY=YES
STAR_BOUND_BARE_CALL_BLOCKS_REEXPORT_LINEAGE_INTEGRATION=NO
READY_FOR_DESIGN=YES

READY_FOR_DESIGN rationale: DIRECT_EVIDENCE establishes the exact missing relations and the full/incremental query behavior; CODE_PATH_PROVED establishes the existing derived lineage query index/backend lifecycle and the independent canonical reexport facts owner. B is recorded only as the best evidence-derived integration-boundary candidate; no design or implementation has been selected. The deferred bare-star-call audit is not a blocker for the reexport-lineage discovery boundary.

## FILES_CHANGED
FILES_CHANGED=NONE

## DIFFS
DIFFS=NONE
