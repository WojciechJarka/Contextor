# CONTEXTOR C16-B03-P1D3G18-P2-D0 — SCC CLASS DEFINITION BARRIER DISCOVERY

## CURRENT_CANONICAL_AND_WORKSPACE_STATUS

DIRECT_EVIDENCE — Contextor MCP first: canonical revision 1084, canonical_state fresh, workspace_sync verified for `package_model.py` and `scenarios.py`, syntax errors 0, structural DFS cycles 16, active_warning_count 16, model_pass_count 0, cycle_semantics stale. Canonical snapshot: state_id `20261106_195021`, repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`; optional /3 receipt absent. Repository interpreter `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` reports CPython 3.15.2. Git HEAD `eb8134e60dfa5568a516c3cac09bcba3e32f1829` is not the LIVE revision. Worktree had no source/test changes before this report; no existing modifications were overwritten.

## VERIFIED_307_MODULE_CENSUS

DIRECT_EVIDENCE — Physical production inventory: 306 `.py` files under `contextor/` plus root `main.py`; exclude tests/, virtual environments, caches and generated copies. All 307 paths had canonical Module IDs and source-byte SHA-256 matching the revision-1084 FileState. Rebuilt OPTIONAL_NAMED_CHILDREN closures from current hard_edges and Module.imports: SCC1 44 members/201 sources, SCC2 9 members/221 sources, union 221, outside both 86. Repeated `_compile` diagnostic with `annotation_semantics="DEFERRED"`, current `recognize_typing_guard`, and successive prefixes of the same AST statement objects. No analyzed repository module was imported or executed, and no AST was changed.

| Group | Accepted | Rejected | ClassDef first | Other first |
|---|---:|---:|---:|---:|
| All production (307) | 158 | 149 | 88 | 61 |
| SCC1 (201) | 94 | 107 | 69 | 38 |
| SCC2/union (221) | 107 | 114 | 72 | 42 |
| Outside union (86) | 51 | 35 | 16 | 19 |

Complete first-failure distribution for all production: ClassDef 88, Assign 47, AnnAssign 4, If 1, FunctionDef 5, AsyncFunctionDef 1, Expr 3. This matches the G18-P1 checkpoint by fresh measurement, not assumption. These are compiler-acceptance counts, never a whole-project MODEL_PASS.

## CLASSDEF_MECHANISM_MATRIX

Mechanisms are independent and can overlap in one class. Counts refer to modules whose *first* rejected top-level statement is ClassDef; `package_model.py:_safe_passive_class_definition` at lines 141-221, `_safe_passive_function_definition` at 63-138, `_safe_annassign` at 413 onward, `_pure_literal_expression` at 301 onward, and ClassDef compilation at 623 onward are the current guards.

| Independent mechanism | All modules | SCC union | Outside | Example (repo-relative source) | Current guard |
|---|---:|---:|---:|---|---|
| Class decorator | 61 | 49 | 12 | `contextor/core/analysis/full_analysis_lease.py:27-28` `@dataclass(frozen=True, slots=True)` | nonempty `decorator_list` rejects; decorator expressions evaluate at class creation |
| Class base | 20 | 17 | 3 | `contextor/core/analysis/function_analysis.py:11` `class ControlFlowAnalyzer(ast.NodeVisitor)` | nonempty `bases` rejects; base expressions evaluate at class creation |
| Class keyword/metaclass | 0 | 0 | 0 | not observed in first-rejected cohort | nonempty `keywords` guard remains |
| Class type parameters | 0 | 0 | 0 | not observed | `type_params` guard remains |
| Invalid/dunder class name | 0 | 0 | 0 | not observed | name guard remains |
| Class-body AnnAssign rejected | 15 | 11 | 4 | `contextor/core/analysis/incremental/engine.py:119` `affected_modules: list[str] = field(default_factory=list)` within decorated class | `_safe_annassign` requires simple Name target and no value or pure literal value |
| Class-body Assign rejected | 2 | 2 | 0 | `contextor/core/graph/resolver.py:48` `__slots__ = (...)` | single permitted Name target without reserved dunder and pure literal value |
| Method definition rejected | 8 | 7 | 1 | `contextor/core/analysis/refresh_planner.py:81` `@staticmethod` method | passive method guard rejects definition-time decorators/nonliteral defaults and other effects |
| Unsupported other class-body statement | 0 | 0 | 0 | not observed as independent reason in this cohort | class-body fallback rejects |

Subforms by affected module (independent counts): decorators Call 55 (union 44/outside 11), Name 6 (5/1), Attribute 0, other 0. Bases Name 11 (9/2), Attribute 9 (8/1), Subscript/Call/other 0. Rejected class-body AnnAssign value Name 9 (6/3), Call 6 (5/1); no-value, pure literal, Attribute, Subscript and other unsupported value 0 in this cohort. Rejected class-body Assign: unsupported target 1 (union 1), Call value 1 (union 1); no rejected literal, Name-alias or Attribute value in this cohort. Invalid methods include Name-form decorators in 8 affected modules (union 7/outside 1); defaults are present in 3 such modules, but presence alone is not a refusal. Annotation syntax is present in 8 invalid-method modules but is accepted under explicit DEFERRED and is not itself the observed reason. The one method with a nonliteral default is `contextor/core/reporting_engine/persistent_registry.py:529`; other invalid-method cases have decorators. No class decorator was invoked during discovery.

## SCC_COHORT_OVERLAP

SCC1 is contained in SCC2 by exact module IDs. SCC2 equals union (221); outside union is disjoint (86). ClassDef-first counts partition 72 union + 16 outside = 88 all production, not 69+72. Overlapping mechanism counts likewise must not be summed across SCC1 and SCC2. The per-module appendix below records each class's SCC1/SCC2 membership explicitly.

## MINIMAL_BARRIER_COHORTS

| Cohort | One mechanism | Two | Three or more | Decorator only | Base only | Method only | AnnAssign only | Assign only | Mixed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All production | 71 | 16 | 1 | 44 | 20 | 5 | 0 | 2 | 17 |
| SCC1 | 56 | 12 | 1 | 35 | 15 | 4 | 0 | 2 | 13 |
| SCC2/union | 59 | 12 | 1 | 36 | 17 | 4 | 0 | 2 | 13 |
| Outside union | 12 | 4 | 0 | 8 | 3 | 1 | 0 | 0 | 4 |

Representative exact single-mechanism cases: decorator only `contextor/core/analysis/full_analysis_lease.py:27-28` (`@dataclass(...)`, `class FullAnalysisLease:`); base only `contextor/core/analysis/function_analysis.py:11` (`class ControlFlowAnalyzer(ast.NodeVisitor):`); method only `contextor/core/analysis/refresh_planner.py:70,81` (`class RefreshPlanner:`, `@staticmethod`); class-body Assign only `contextor/core/graph/resolver.py:47-48` (`class TrieNode:`, `__slots__ = (...)`) and `contextor/core/single_file/builders/layer0_builders.py:9-11` (`requires = set()`). There is no AnnAssign-only class in the current first-rejection cohort. These examples show current guards, not claims that the rejected constructs are safe.

## EXACT_SOURCE_EXAMPLES

The appendix `PER_MODULE_CLASSDEF_RECORDS` below contains all 88 ClassDef-first modules with repo-relative path, canonical Module ID, class line/name, zero-based top-level statement index, SCC1/SCC2 membership, and the complete independent mechanism set. Additional source-grounded examples: `contextor/core/analysis/incremental/engine.py:100,119` has a decorated `IncrementalUpdateResult` and a `field(default_factory=list)` initializer; `contextor/core/single_file/builders/layer0_builders.py:9-12` has `requires = set()` in a class body; `contextor/core/reporting_engine/persistent_registry.py:529` has a nonliteral method default expression. None was executed.

## SEMANTIC_TIMING_AND_NAMESPACE_EVIDENCE

CODE_PATH_PROVED — `_safe_passive_class_definition` checks class decorator, base, keyword/metaclass, type parameter, name and body before `_compile` emits steps. In actual Python, decorator/base/keyword expressions and class-body instructions are definition-time effects; the restricted model declines to simulate rejected forms. For accepted restricted classes, `_compile` emits class-local import and BIND steps in body order, then `DEFINE_PASSIVE_CLASS` (`package_model.py:623-787`); the interpreter binds the class name only at that last step (`package_model.py:1500-1514`). Accepted class-local Assign/AnnAssign BIND emits `CLASS_LOCAL_BIND` and does not write the module namespace (`package_model.py:1551-1562`). The model does not retain general class-attribute values or support arbitrary class-attribute reads. Passive method bodies remain deferred; method decorators and dynamic defaults are definition-time guards. Class-local imported references are represented as class-local events and do not automatically become module exports (`package_model.py:1351-1468`). The simulator checks initializing versus ready state for FROM/ATTR reads and emits `EARLY_BINDING_HAZARD` or UNKNOWN as appropriate (`package_model.py:1433 onward, 1600 onward`). Package-child shadowing guards and source binding remain separate gates. These code paths do not certify runtime finder identity.

## ACTUAL_SCC_MODEL_GATES

DIRECT_EVIDENCE — Read-only replay of both current FileState-bound closures: SCC1 graph consistency `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`, 4 namespace records, 605 opaque external records; SCC2 same reason, 4 namespace records, 723 opaque external records. Each has `internal_graph_state=INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES` for its selected sources. Static package layout for each has `contextor.core.git` as `NAMESPACE_CANDIDATE`, outside the restricted regular-package layout (`package_model.py:996-1008`). `analyze_cycle_scenarios` returns INDETERMINATE, coverage NONE, 0 entry assessments for both; it stops at `consistency.status != CONSISTENT` (`scenarios.py:282-286`) before `evaluate_package_import_order` and ClassDef simulation. Source SHA-256 matched FileState and no ambiguity or source unavailability was observed in the selected cohorts. Thus ClassDef is a confirmed *diagnostic `_compile` barrier* in 69/72 selected modules, but is **not** the earliest actually reached SCC scenario gate. The real earlier gate is namespace import resolution; external imports remain opaque. `scenarios.py:304-309` calls the package evaluator without explicit `annotation_semantics`, so target-version-dependent annotation acceptance is not established there; this later gate is not reached. The retained cycle_semantics snapshot is stale, preventing current semantic-generation certification. No hypothetical MODEL_PASS is reported as observed.

## EXISTING_REGRESSION_INVENTORY

Source-inspected tests, not executed: `tests/test_cycle_semantics_package_model.py::test_p1d3_d1_unsupported_class_effects` covers rejected decorators/bases/body effects; `::test_p1d3_d1_class_import_timing`, `::test_p1d3_d1_class_local_binding_does_not_escape`, `::test_p1d3_d1_class_local_reentrant_child_from`, and `::test_p1d3_d1_uncalled_method_import_is_deferred` cover class timing/scope; `::test_package_early_from_import_hazard`, `::test_warn_5h_namespace_rejected_before_ast_compilation`, and `::test_namespace_ambiguous_external_unknown` cover fail-closed gates. `tests/test_cycle_semantics_package_model_annotations315.py::test_unknown_effects_remain_unknown`, `::test_class_annotations_have_separate_binding_and_import_order`, and `::test_restricted_class_annotation_does_not_leak_module_binding` cover annotation/method effects. `tests/test_cycle_semantics_package_model_literals.py::test_class_local_literal_bindings`, `::test_class_local_order`, `::test_class_binding_does_not_export_module_name`, `::test_g18_p1_arithmetic_class_local_binding`, and `::test_early_binding_hazard_not_hidden` cover class-local binding. `tests/test_cycle_semantics_package_model_async_alias.py::test_passive_async_class_method`, `::test_decorated_async_class_method_unknown`, `::test_class_body_name_alias_still_unknown`, `::test_external_import_still_unknown`, and `::test_namespace_layout_still_unknown` cover async methods and continued UNKNOWN boundaries. No pytest was run.

## UNRESOLVED_EVIDENCE_GAPS

No runtime import finder/path/module identity, external loader effects, target interpreter identity for analyzed project, decorator/metaclass effects, or general class namespace semantics was established. The 88-row diagnostic does not establish that any rejected construct is safe. `cycle_semantics` remains stale. No implementation design, production/test edit, FULL, update_file, restart, warning-policy mutation, Git mutation, receipt publication, or MODEL_PASS override was performed.

## FILES_CHANGED_AND_FULL_DIFFS

FILES_CHANGED: `walkthrough.md` only. FULL_DIFFS=NONE for source, tests and docs. This report is excluded from its own diff.

## FINAL_VERDICT

DISCOVERY_COMPLETE — current FileState-bound census and all 88 ClassDef-first mechanism sets were collected, and the earlier actual SCC scenario gate was distinguished from diagnostic compiler barriers.

## PER_MODULE_CLASSDEF_RECORDS

Fields: `repo_relative_path | canonical_module_id | class_lineno | class_name | zero_based_top_level_index | SCC1 | SCC2 | independent_mechanisms`. `A`/`B` denote membership; `-` denotes absence. This is the complete current ClassDef-first cohort, not all ClassDef nodes in the repository.

```text
contextor/core/analysis/full_analysis_lease.py | contextor.core.analysis.full_analysis_lease | 28 | FullAnalysisLease | 15 | A | B | DECORATOR
contextor/core/analysis/function_analysis.py | contextor.core.analysis.function_analysis | 11 | ControlFlowAnalyzer | 2 | A | B | BASE
contextor/core/analysis/import_analysis.py | contextor.core.analysis.import_analysis | 17 | ImportUsageVisitor | 2 | A | B | BASE
contextor/core/analysis/incremental/engine.py | contextor.core.analysis.incremental.engine | 100 | IncrementalUpdateResult | 20 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/analysis/incremental/graph_ops.py | contextor.core.analysis.incremental.graph_ops | 18 | LocalDegreeDeltaResult | 5 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/analysis/incremental/plan_executor.py | contextor.core.analysis.incremental.plan_executor | 46 | CandidateState | 17 | A | B | DECORATOR
contextor/core/analysis/incremental/preparation.py | contextor.core.analysis.incremental.preparation | 25 | PreparedSourceUpdate | 10 | A | B | DECORATOR/METHOD
contextor/core/analysis/lineage_extraction_state.py | contextor.core.analysis.lineage_extraction_state | 10 | _ParameterInfo | 4 | A | B | DECORATOR
contextor/core/analysis/refresh_planner.py | contextor.core.analysis.refresh_planner | 70 | RefreshPlanner | 6 | A | B | METHOD
contextor/core/analysis/state_analysis.py | contextor.core.analysis.state_analysis | 12 | StateMutationAnalyzer | 2 | A | B | BASE
contextor/core/analysis/state_manager.py | contextor.core.analysis.state_manager | 15 | FileState | 8 | A | B | DECORATOR/METHOD
contextor/core/analysis/test_context.py | contextor.core.analysis.test_context | 214 | TestFileInfo | 16 | A | B | DECORATOR
contextor/core/api/facade.py | contextor.core.api.facade | 551 | ContextorFacade | 42 | A | B | METHOD
contextor/core/api_surface/visitor.py | contextor.core.api_surface.visitor | 52 | APISurfaceVisitor | 6 | A | B | BASE
contextor/core/cycle_semantics/binding_order.py | contextor.core.cycle_semantics.binding_order | 16 | CycleBindingCandidate | 5 | - | - | DECORATOR
contextor/core/cycle_semantics/closure_witness.py | contextor.core.cycle_semantics.closure_witness | 17 | NonDirectClosureWitness | 6 | A | B | DECORATOR
contextor/core/cycle_semantics/conditional_discovery.py | contextor.core.cycle_semantics.conditional_discovery | 27 | DiscoveredConditionalReexport | 10 | A | B | DECORATOR
contextor/core/cycle_semantics/conditional_export.py | contextor.core.cycle_semantics.conditional_export | 17 | ConditionalImportHop | 5 | A | B | DECORATOR
contextor/core/cycle_semantics/conditional_grouping.py | contextor.core.cycle_semantics.conditional_grouping | 20 | ConditionalReexportGroup | 4 | A | B | DECORATOR
contextor/core/cycle_semantics/cycle_warning_projection.py | contextor.core.cycle_semantics.cycle_warning_projection | 15 | InstalledCycleWarningProjection | 6 | A | B | DECORATOR
contextor/core/cycle_semantics/cycle_warning_transitions.py | contextor.core.cycle_semantics.cycle_warning_transitions | 16 | CycleWarningTransition | 4 | A | B | DECORATOR
contextor/core/cycle_semantics/diagnostic_view.py | contextor.core.cycle_semantics.diagnostic_view | 29 | CycleDiagnosticEdge | 7 | A | B | DECORATOR
contextor/core/cycle_semantics/edge_sites.py | contextor.core.cycle_semantics.edge_sites | 22 | LexicalEdgeSite | 9 | A | B | DECORATOR
contextor/core/cycle_semantics/evidence.py | contextor.core.cycle_semantics.evidence | 43 | ComponentSourceEvidence | 20 | A | B | DECORATOR
contextor/core/cycle_semantics/execution_context.py | contextor.core.cycle_semantics.execution_context | 21 | ImportExecutionContext | 5 | - | - | DECORATOR
contextor/core/cycle_semantics/generation_manifest.py | contextor.core.cycle_semantics.generation_manifest | 46 | PreparedSCCSourceBinding | 16 | A | B | DECORATOR
contextor/core/cycle_semantics/guards.py | contextor.core.cycle_semantics.guards | 16 | GuardFrameEvidence | 5 | - | - | DECORATOR
contextor/core/cycle_semantics/initialization_model.py | contextor.core.cycle_semantics.initialization_model | 15 | ModelStep | 5 | A | B | DECORATOR
contextor/core/cycle_semantics/model_source_closure.py | contextor.core.cycle_semantics.model_source_closure | 21 | CycleModelSourceClosure | 8 | A | B | DECORATOR
contextor/core/cycle_semantics/namespace_path_model.py | contextor.core.cycle_semantics.namespace_path_model | 13 | SearchPortion | 3 | - | - | DECORATOR
contextor/core/cycle_semantics/namespace_source_binding.py | contextor.core.cycle_semantics.namespace_source_binding | 38 | IndexedSourcePath | 14 | - | - | DECORATOR
contextor/core/cycle_semantics/optional_generation_anchor.py | contextor.core.cycle_semantics.optional_generation_anchor | 33 | OptionalPreparedGenerationAnchor | 7 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/cycle_semantics/optional_scc_publication.py | contextor.core.cycle_semantics.optional_scc_publication | 43 | CanonicalOptionalSCCReceipt | 10 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/cycle_semantics/optional_store_generation.py | contextor.core.cycle_semantics.optional_store_generation | 46 | OptionalStoredGenerationAssessment | 9 | - | - | BODY_ANNASSIGN/DECORATOR
contextor/core/cycle_semantics/original_worker_preparation.py | contextor.core.cycle_semantics.original_worker_preparation | 34 | OriginalWorkerManifestPreparation | 9 | A | B | DECORATOR
contextor/core/cycle_semantics/original_worker_reindex_planning.py | contextor.core.cycle_semantics.original_worker_reindex_planning | 28 | OriginalWorkerReindexPlan | 9 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/cycle_semantics/package_graph_consistency.py | contextor.core.cycle_semantics.package_graph_consistency | 19 | PackageGraphConsistency | 7 | A | B | DECORATOR
contextor/core/cycle_semantics/package_layout.py | contextor.core.cycle_semantics.package_layout | 15 | PackageLayoutNode | 5 | A | B | DECORATOR
contextor/core/cycle_semantics/package_model.py | contextor.core.cycle_semantics.package_model | 22 | PackageModelEvent | 7 | A | B | DECORATOR
contextor/core/cycle_semantics/partial_scc_publication.py | contextor.core.cycle_semantics.partial_scc_publication | 29 | CanonicalPartialSCCReceipt | 10 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/cycle_semantics/provenance.py | contextor.core.cycle_semantics.provenance | 14 | ScopeFrame | 4 | A | B | DECORATOR
contextor/core/cycle_semantics/registered_store_binding.py | contextor.core.cycle_semantics.registered_store_binding | 47 | RegisteredStoreWorkerAssessment | 12 | - | - | BODY_ANNASSIGN/DECORATOR
contextor/core/cycle_semantics/scc.py | contextor.core.cycle_semantics.scc | 13 | CyclicImportComponent | 4 | A | B | DECORATOR
contextor/core/cycle_semantics/scenarios.py | contextor.core.cycle_semantics.scenarios | 33 | CycleComponentScenarios | 14 | A | B | DECORATOR
contextor/core/cycle_semantics/selective_source_replay.py | contextor.core.cycle_semantics.selective_source_replay | 41 | SCCSourceReplay | 12 | - | - | BODY_ANNASSIGN/DECORATOR
contextor/core/cycle_semantics/source_cohort.py | contextor.core.cycle_semantics.source_cohort | 32 | CycleSourceIssue | 9 | A | B | DECORATOR
contextor/core/cycle_semantics/source_proof.py | contextor.core.cycle_semantics.source_proof | 48 | SCCSourceByteAssessment | 13 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/cycle_semantics/typing_guard.py | contextor.core.cycle_semantics.typing_guard | 10 | RecognizedTypingGuard | 4 | A | B | DECORATOR
contextor/core/domain/graph.py | contextor.core.domain.graph | 11 | ProjectGraph | 2 | A | B | DECORATOR
contextor/core/domain/imports.py | contextor.core.domain.imports | 12 | ImportRef | 2 | A | B | DECORATOR
contextor/core/domain/lineage_facts.py | contextor.core.domain.lineage_facts | 22 | LineageRelation | 9 | A | B | BASE
contextor/core/domain/resolution.py | contextor.core.domain.resolution | 12 | ResolutionResult | 3 | A | B | DECORATOR
contextor/core/domain/validation.py | contextor.core.domain.validation | 11 | ValidationError | 2 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/errors.py | contextor.core.errors | 12 | ContextorError | 1 | A | B | BASE
contextor/core/facts/context.py | contextor.core.facts.context | 39 | RepositoryContext | 5 | - | - | DECORATOR
contextor/core/facts/references.py | contextor.core.facts.references | 37 | SymbolReference | 4 | - | - | BODY_ANNASSIGN/DECORATOR
contextor/core/facts/symbol_index.py | contextor.core.facts.symbol_index | 73 | SymbolIndexVisitor | 5 | - | - | BASE
contextor/core/graph/resolver.py | contextor.core.graph.resolver | 47 | TrieNode | 4 | A | B | BODY_ASSIGN
contextor/core/lineage_query/index.py | contextor.core.lineage_query.index | 17 | ReexportLineageHop | 5 | A | B | DECORATOR
contextor/core/lineage_query/live_query.py | contextor.core.lineage_query.live_query | 48 | LiveSymbolLineageQueryResult | 12 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/live_state/hydration.py | contextor.core.live_state.hydration | 11 | HydratedRepositoryEngine | 5 | A | B | DECORATOR
contextor/core/live_state/ipc.py | contextor.core.live_state.ipc | 30 | LiveEndpoint | 21 | A | B | BODY_ANNASSIGN/DECORATOR/METHOD
contextor/core/live_state/runtime.py | contextor.core.live_state.runtime | 56 | EndpointSchemaError | 21 | A | B | BASE
contextor/core/live_state/store.py | contextor.core.live_state.store | 54 | _SnapshotUnpickler | 22 | A | B | BASE
contextor/core/profiling/registry.py | contextor.core.profiling.registry | 13 | ScopeSpec | 6 | - | - | DECORATOR
contextor/core/reference/index.py | contextor.core.reference.index | 45 | CallEvent | 10 | A | B | DECORATOR
contextor/core/reference/visitor.py | contextor.core.reference.visitor | 33 | SymbolReferenceVisitor | 6 | A | B | BASE
contextor/core/reporting_engine/artifact_pipeline.py | contextor.core.reporting_engine.artifact_pipeline | 29 | ArtifactPipelineResult | 12 | A | B | DECORATOR
contextor/core/reporting_engine/dictionary.py | contextor.core.reporting_engine.dictionary | 11 | IndexDictionary | 3 | A | B | METHOD
contextor/core/reporting_engine/graph_analytics.py | contextor.core.reporting_engine.graph_analytics | 66 | SharedUsageClustersHandoff | 7 | A | B | DECORATOR
contextor/core/reporting_engine/persistent_registry.py | contextor.core.reporting_engine.persistent_registry | 12 | PersistentIdentityRegistry | 9 | A | B | METHOD
contextor/core/repository_identity.py | contextor.core.repository_identity | 15 | RepositoryIdentityError | 10 | A | B | BASE
contextor/core/single_file/builders/layer0_builders.py | contextor.core.single_file.builders.layer0_builders | 9 | ModuleIntentBuilder | 3 | A | B | BODY_ASSIGN
contextor/core/single_file/builders/registry.py | contextor.core.single_file.builders.registry | 8 | ContextPayload | 4 | A | B | DECORATOR
contextor/core/source.py | contextor.core.source | 22 | SourceError | 8 | A | B | BASE
contextor/core/symbol_engine/domain.py | contextor.core.symbol_engine.domain | 5 | SymbolFacts | 1 | A | B | BODY_ANNASSIGN/DECORATOR
contextor/core/symbol_engine/extractor.py | contextor.core.symbol_engine.extractor | 64 | SymbolVisitor | 8 | A | B | BASE
contextor/core/symbol_engine/usage.py | contextor.core.symbol_engine.usage | 6 | UsageVisitor | 2 | A | B | BASE
contextor/core/validator/collisions.py | contextor.core.validator.collisions | 96 | CollisionFactKeys | 13 | A | B | BASE
contextor/mcp/lineage_response.py | contextor.mcp.lineage_response | 24 | SymbolLineageResponsePlan | 11 | - | - | DECORATOR
contextor/mcp_backend_autostart.py | contextor.mcp_backend_autostart | 29 | BackendAutostartError | 15 | - | - | BASE
contextor/mcp_backend_http_headers.py | contextor.mcp_backend_http_headers | 23 | BackendHttpHeadersError | 5 | - | - | BASE
contextor/mcp_backend_job.py | contextor.mcp_backend_job | 12 | BackendJobError | 7 | A | B | BASE
contextor/mcp_backend_secret.py | contextor.mcp_backend_secret | 39 | BackendSecretError | 24 | - | B | BASE
contextor/mcp_backend_state.py | contextor.mcp_backend_state | 56 | BackendStateError | 21 | - | B | BASE
contextor/mcp_process_registry.py | contextor.mcp_process_registry | 19 | ProcessIdentityProbe | 13 | A | B | DECORATOR
contextor/ui/single_instance.py | contextor.ui.single_instance | 31 | DesktopSingleInstance | 13 | - | - | METHOD
contextor/ui/theme.py | contextor.ui.theme | 45 | Palette | 5 | - | B | DECORATOR
```
