# Contextor Stage 1E0 — surface lineage architectural discovery + implementation design

## Scope and authority

DISCOVERY_ONLY; requested source revision a350f1a7d86e059ebdff82a91d20932a7fb9e9e4.

Contextor MCP was used first: active-pool inspection, centralized documentation, canonical search_source, and exact get_source_range; rg then verified owners, consumers, and tests. The active pool contains the applicable architecture/source tools. No deferred-pool discovery tool (tool_search or deferred Contextor tool) is injected in this task, so there was no callable deferred pool to inspect.

The worktree was already dirty in three tests and this report. This task changed no production, test, schema, or configuration file.

## CURRENT_STATE

### Source-local lineage

* contextor/core/analysis/lineage_extraction.py::_AnchorExtractor owns the sole recursive AST traversal and one LineageExtractionState. It delegates to lineage_extraction_* helpers and finalizes captures.
* extract_lineage_source_facts validates input, indexes AST paths once, and currently returns surfaces=() at lines 265–279. It does no I/O after receiving the AST; tests/analysis/test_lineage_extraction.py freezes this.
* contextor/core/analysis/lineage_extraction_state.py is canonical lexical state. Owner-keyed _bindings, _imports, and _ImportInfo(module_name, symbol_name, binding_id) provide existing binding identity/import authority.
* Existing visit_import and visit_import_from emit import anchors/bindings. A from-import alias surface must reference its existing local binding, never a new identity. Plain import is only an import binding.

### Public/export/reexport ownership

* contextor/core/analysis/export_analysis.py::_is_public defines the current public-name rule: nonempty and no leading underscore.
* export_analysis.extract_exports is the only production owner that combines that convention with literal top-level __all__: assignment detection, list/tuple literal strings, sorted output. PublicApiBuilder and ExportContextBuilder consume it for single-file reporting.
* import_analysis.extract_import_usage repeats limited literal-__all__ parsing to label import usage re_exported; it is not a lineage producer.
* contextor/core/reference/shared.py::_build_reexport_map and reference/resolution.py::_resolve_reexport are canonical repository-wide resolution. They handle transitive aliases, package init, explicit-__all__ stars, cycles, and local shadowing. They require all modules, so are not source-local.
* Graph analytics export degree explicitly means artifact degree, not Python __all__.

### Entrypoints, registrations, visibility

* The only ENTRYPOINT producer is reporting_engine/summary_generator.py name-pattern classification of isolated modules. It is report heuristic, not exact exposure.
* No framework/plugin registration producer exists. Stage 1D CALLBACK_REGISTERS models local callable passing to an invoked callback parameter; tests distinguish generic register(callback=...) from that relation. It is not SurfaceKind.REGISTRATION.
* Artifact visibility is report/filter behavior, not a Python export canonical contract.

### Domain/state/materialization

* core/domain/lineage_facts.py already defines SurfaceKind, SurfaceDeclarationEvidence, ExtractedSurfaceFact, and MaterializedSurfaceFact.
* Both extracted/materialized source slices contain sorted/unique surfaces; fresh manifests validate count. Extracted targets are occurrence/symbolic refs; materialized targets are local occurrences or semantic endpoints.
* Domain tests freeze: LITERAL_ALL_DECLARATION is legal only on EXPORT, and confirmed exact materialized targets require semantic endpoints.
* EXPOSES and DECLARES_PUBLIC_NAMES exist but have no Stage 1E producer.
* RepositoryAnalysisState, incremental candidate copy/commit, and live_state/store.py own/persist/load/validate lineage_facts_by_source and materialized surfaces. tests/test_lineage_state_lifecycle.py freezes lifecycle.
* No extracted-to-materialized resolver, writer feeding that state, or public MCP surface projection exists. Persistence is implemented but unfed; canonical materialization/query belongs to 1F+, not 1E.

## REUSE_MAP

| Requirement | Canonical owner | 1E usage |
|---|---|---|
| One parsed AST traversal | _AnchorExtractor and LineageExtractionState | Collect surfaces in it; no reread/reparse/walk. |
| Source-local identity | occurrence, anchor, binding/import frames | Existing definition/import occurrence only. |
| Default public predicate | export_analysis._is_public | Shared narrow semantic rule; preserve underscore behavior. |
| Literal __all__ | export_analysis.extract_exports | Migrate literal recognizer to one-pass collection; do not call it from extractor. |
| Provider resolution | _build_reexport_map | Do not call in 1E; defer to 1F/1G. |
| Surface boundaries | domain facts, PUBLIC_TARGET, build_public_slot | Extracted facts only; 1F maps endpoints. |
| Storage lifecycle | state manager, plan executor, live store | Leave unchanged in 1E.1. |

## GAPS

1. No surface collection, deterministic local-ID namespace, or emission helper.
2. No shared one-pass literal-__all__ recognizer. Calling extract_exports creates a second top-level scan.
3. No canonical materializer/writer/MCP projection: 1F.
4. No exact source-local entrypoint or plugin/framework registration owner. No schema/version hole is proven.

## SEMANTIC_DECISIONS A–K

### A. Ordinary module-level def/class

Existing rule: nonempty/no-leading-underscore. In 1E.1 only top-level def/class yields PUBLIC_SYMBOL, STATIC_DECLARATION, PYTHON_NAME_CONVENTION, INFERRED. Nested symbols and assignments are excluded.

### B. Literal __all__

Literal __all__ = ["f", "C"] overrides default convention. Emit only deduplicated EXPORT, LITERAL_ALL_DECLARATION, LITERAL_CONTAINER_EXACT, CONFIRMED records, deterministically sorted.

### C. From-import exposure

A literal exported current from-import binding becomes REEXPORT, STATIC_DECLARATION, IMPORT_EXACT, CONFIRMED, pointed at that existing occurrence. Rebinding/shadowing defeats it. Provider artifact resolution is 1F.

### D. Plain import

Plain import x never creates a surface alone. Even literal module-object exports are deferred; do not label them reexports.

### E. Unresolved literal name

Emit EXPORT with ExtractedSymbolicRef(PUBLIC_TARGET, current module, declared name, None), LITERAL_ALL_DECLARATION, UNRESOLVED_NAME, UNRESOLVED. No fake occurrence/ID or flow.

### F. Mutation/dynamic construction

Plus-equals, append, concatenation, starred lists, comprehensions, calls/reflection, conditional merge, and non-string members lack an exact evaluator. They are outside 1E.1; add no heuristic.

### G. ENTRYPOINT

Emit none. Current owner is a report-only name heuristic; console scripts, decorators, and main guards lack an exact source-local contract.

### H. REGISTRATION

Emit none. Generic callback relations are not framework/plugin registration.

### I. EXPOSES/DECLARES_PUBLIC_NAMES

Emit neither in 1E.1. ExtractedSurfaceFact is the declaration record. 1F can emit EXPOSES as public declaration/slot -> exposed semantic endpoint once materialized; DECLARES_PUBLIC_NAMES needs a concrete public/module boundary too.

### J. Determinism

Use private deterministic ID surface:v1:{kind}:{ast_path}:name:{name}:i:{ordinal}, based on existing indexed AST paths. Track _surface_ids, append state.surfaces, return tuple(sorted(...)); targets never determine identity.

### K. Safe source-local scope

1E.1: top-level def/class defaults; literal list/tuple __all__ exports of current local bindings/unresolved names; authoritative explicit-import reexports. Defer provider resolution, star/module imports, entrypoints, registrations, mutations, metadata, persistence/materialization, MCP.

## PROPOSED_SUBSTAGES

### 1E.1 — exact source-local declarations

One-pass public top-level defs/classes and literal list/tuple __all__ records; emit PUBLIC_SYMBOL, EXPORT, REEXPORT, unresolved exports. Stop at dynamic/mutated/conditional construction, plain/star imports, nested scope, provider resolution, entrypoints, registrations, persistence, MCP.

### 1E.2 — narrow semantic extraction

Move only _is_public and literal-container recognition into a shared owner used by extract_exports and 1E.1. Do not migrate reporting consumers. Stop on legacy public-report equivalence drift.

### 1E.3 — reexport authority hardening

Test relative imports, aliases, rebinding/shadowing, rejected star/plain paths. Proves source-local authority only; no provider resolution.

### 1F / 1G / 1H — out of 1E

1F materializes targets/populates state/emits canonical relations. 1G owns metadata/package/provider reexports via _build_reexport_map. 1H adds provider-specific registration contracts then considers MCP.

## First implementation substage

### Exact targets

* lineage_extraction_state.py: add surfaces list, _surface_ids, minimal helpers; reuse existing frames/import metadata.
* lineage_extraction_emit.py: private emit_surface using existing span/path, collision guard, deterministic ID.
* lineage_extraction_visitors.py::visit_module: capture module statements in existing execution order; no new visitor, ast.walk, or post-pass.
* lineage_extraction.py::_AnchorExtractor.extract: return sorted anchors/flows/surfaces and pass existing result constructor.
* export_analysis.py: no behavior change in 1E.1; helper migration is 1E.2.
* tests/analysis/test_lineage_extraction.py and test_lineage_extraction_equivalence.py: behavior-named, no-I/O/determinism compatibility tests.

### Shapes

* Default: PUBLIC_SYMBOL, existing definition occurrence, definition span, PYTHON_NAME_CONVENTION/INFERRED, static declaration.
* Literal local: EXPORT, existing occurrence, literal span, LITERAL_CONTAINER_EXACT/CONFIRMED, literal-all declaration.
* Literal explicit import: REEXPORT, existing import occurrence, literal span, IMPORT_EXACT/CONFIRMED, static declaration.
* Literal unresolved: EXPORT, PUBLIC_TARGET symbolic ref, literal span, UNRESOLVED_NAME/UNRESOLVED, literal-all declaration.
* No 1E.1 declaration flows.

### Test matrix

Positive: public def/class and underscore exclusion; literal __all__ only confirmed sorted exports; local existing-anchor reuse; relative/aliased from-import reexports; missing literal symbolic export; repeat-run equality/no filesystem I/O.

Negative: plain/unexported imports and nested defs create no surface; local shadow after import is EXPORT not REEXPORT; star/module/rebound imports do not make confirmed reexports; mutated/dynamic __all__ gets no exact export; main guards/decorator-looking calls/register(callback=...) yield neither ENTRYPOINT nor REGISTRATION; resource limit stays empty.

## DO_NOT_DO

* No parallel public/reexport analyzer, second NodeVisitor, ast.walk, reparse, or source reread.
* No repository _build_reexport_map from source-local extractor.
* No duplicate identity; reuse anchors/import bindings/symbolic refs.
* No heuristic exports, CLI detection, plugins, registrations, or callback conflation.
* No enum/schema/version, persistence, materialization, or MCP changes in 1E.1.
* No 1F/1G/1H before 1E.1 acceptance.

## Frozen contracts/tests

* tests/analysis/test_lineage_extraction.py: source-local/no-I/O determinism, limits, Stage 1D callbacks.
* tests/analysis/test_lineage_extraction_equivalence.py: public extractor API/parity.
* tests/domain/test_lineage_facts.py: validation, evidence, ordering, exact endpoints.
* tests/test_lineage_state_lifecycle.py: candidate/commit/persistence.
* tests/test_reexport_reference_semantics.py: project-level transitive/relative/star/cycle/shadow behavior; preserve as reference tests, not 1E behavior.
* tests/test_h2a_reference_index_equivalence.py and tests/test_reference_fusion_*: legacy __all__ public/report behavior.

FILES_CHANGED=NONE

DIFFS=NONE
