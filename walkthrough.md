ARCHITECTURAL_OWNER_MAP=
`contextor.core.analysis.state_manager.RepositoryAnalysisState` is the canonical mutable state owner. `contextor.core.analysis.incremental.plan_executor.CandidateState` is the isolated mutable COW candidate. Full installation is `contextor.core.api.facade.ContextorFacade.analyze_project`; incremental installation is `contextor.core.analysis.incremental.engine.IncrementalAnalysisEngine._apply_delta_and_commit`; snapshot ownership is `contextor.core.live_state.store.save_snapshot`/`load_snapshot`, wrapped by `state_manager.save_engine_state`/`load_engine_state`; engine hydration is `contextor.core.live_state.hydration.resolve_authoritative_repository_state` then `hydrate_repository_engine`.

STATE_OWNER=`contextor/core/analysis/state_manager.py:RepositoryAnalysisState`. Existing optional family convention is a sparse mutable container plus a separate string state, e.g. `artifact_consumption`/`artifact_consumption_state`, `syntax_diagnostics_by_path`/`syntax_diagnostics_state`, `topology_analytics`/`topology_metrics_state`, `cached_analytics`/`cached_analytics_state`, `cycles`/`cycles_state`, `collision_facts`+`collisions`/`collisions_state`, `dependency_matrix`/`dependency_matrix_state`, and `shared_usage_clusters`/`shared_usage_clusters_state`. Defaults are mostly `{}` or `[]` plus `deferred`; syntax diagnostics is the relevant explicit `not_materialized` precedent.

CANDIDATE_STATE_OWNER=`contextor/core/analysis/incremental/plan_executor.py:CandidateState`; construction is `_prepare_candidate_state`. It copies top-level mutable containers with `dict(...)`/`list(...)`, then `_apply_delta_and_commit` assigns each candidate field back to the canonical state after the refresh-plan outcome.

STATE_CONSTRUCTION_PATHS=
1. Full/bootstrap: `ContextorFacade.analyze_project` constructs `RepositoryAnalysisState` at `contextor/core/api/facade.py:526` from completed index/graph/fact outputs, then `state_manager.save_engine_state` at facade line 614 delegates to `live_state.store.save_snapshot`.
2. Startup/disk: `hydration.resolve_authoritative_repository_state` calls `migrate_legacy_snapshot`, then `state_manager.load_engine_state`, then `live_state.store.load_snapshot`; it can instead use the current LIVE service snapshot. `hydrate_repository_engine` constructs `IncrementalAnalysisEngine` around the already-hydrated state.
3. Incremental normal source: `IncrementalAnalysisEngine` calls `preparation.prepare_source_update`, builds the refresh plan, then `_apply_delta_and_commit`; that invokes `plan_executor.execute_refresh_plan`, whose first operation is `_prepare_candidate_state`.
4. Incremental deletion: the engine uses `preparation.prepare_deleted_module_update` before the same `execute_refresh_plan`/commit route. Current deletion branches remove known per-module families in the candidate; Stage 1A2 must only preserve the lineage-state representation and define the later deletion invariant.
5. Commit order: `execute_refresh_plan` computes the candidate without disk I/O/state mutation; `_apply_delta_and_commit` performs any required registry sync, applies syntax deltas, assigns candidate fields to `self.state`, updates `FileStateManager`, and returns. A future lineage field must participate in both `_prepare_candidate_state` and these assignments.

SNAPSHOT_WRITE_OWNER=`contextor/core/live_state/store.py:save_snapshot`, reached from `state_manager.save_engine_state` and also from the LIVE runtime publisher. It atomically writes `engine_state.pkl` as `pickle.dump({"metadata": asdict(metadata), "state": state})`, writes JSON metadata, and publishes by replace. There is no per-family JSON mapper.

HYDRATION_OWNER=`contextor/core/live_state/store.py:load_snapshot` performs unpickle, envelope/revision/repository-identity checks, and in-RAM legacy-field normalization; `state_manager.load_engine_state` unwraps it. `contextor/core/live_state/hydration.py:resolve_authoritative_repository_state` selects LIVE-service state first and disk snapshot second; `hydrate_repository_engine` only instantiates the incremental engine and does not analyze the repository.

LEGACY_NORMALIZATION_OWNER=`live_state.store.load_snapshot`. It has explicit `hasattr` normalizers in both envelope and pre-envelope branches for old `module_usages`, syntax, topology, cached analytics, cycles, collision, matrix, and cluster fields. No lineage normalizer exists yet. Stage 1A2 must add the lineage absence and validation normalization at these two exact branches, before returning the state.

CURRENT_SERIALIZATION_CONTRACT=Full-state Python pickle, not `to_dict`/`from_dict`, with a small custom `_SnapshotUnpickler` only for the historical `SymbolCallFact` class and `_normalize_symbol_call_facts` for that legacy payload. Frozen dataclasses, enums, tuples, and concrete union members retain their Python classes through pickle. Therefore `MaterializedOccurrenceRef` and `SemanticEndpoint` are already unambiguous concrete values; no generic tagged-union encoding is necessary.

CURRENT_VERSIONING_CONTRACT=`LIVE_STATE_SCHEMA_VERSION="1.2"` is the snapshot-envelope compatibility field accepted by `read_metadata` along with `1.0` and `1.1`; `ENGINE_CACHE_SCHEMA_VERSION="1.1"` is a separate state-manager cache constant. Persistent registry schema versions are separate registry contracts. `LINEAGE_FACTS_SEMANTIC_VERSION="1"` has no persisted state owner today.

PROPOSED_LINEAGE_STATE_SHAPE=Add only to `RepositoryAnalysisState`: `lineage_facts_by_source: Dict[str, MaterializedLineageSourceFacts] = field(default_factory=dict)`, `lineage_facts_state: str = "not_materialized"`, and `lineage_facts_semantic_version: str | None = None`. `lineage_facts_state` is repository/family coverage status, not a duplicate of each slice manifest: the manifest is per-source status/count/fingerprint; the family status distinguishes never materialized from an authoritative mapping that happens to be empty. `lineage_facts_semantic_version` is `None` until first actual lineage materialization and is then exactly `LINEAGE_FACTS_SEMANTIC_VERSION`.

EXTRACTED_FACTS_IN_REPOSITORY_STATE=NO. `ExtractedLineageSourceFacts` is parsed-source staging input. Persisting it would blur the two-phase contract and create a hydration dependency on source-local extraction representation. Stage 1A2 state holds only materialized slices.

MATERIALIZED_FACTS_STATE_MODEL=Sparse source-key mapping only: `source_key -> MaterializedLineageSourceFacts`. The value already contains `SourceLineageManifest`, anchors, flows, surfaces, and any `SemanticInterfaceDescriptor`; no parallel per-source manifest/status map is needed. Keys must equal `slice.manifest.source_key`; duplicate/mismatched keys fail closed during snapshot normalization. The outer dict is mutable only as the canonical/COW container; values are frozen tuple-backed records.

LEGACY_ABSENCE_NORMALIZATION=
A. Legacy payload without all lineage attributes: normalize in `load_snapshot` to `{}`, `"not_materialized"`, and `None`.
B. Hydrated repository before first lineage materialization: the same canonical triple `{}`, `"not_materialized"`, `None`; it is explicitly not empty `fresh`.
C. Partially/materialized repository: non-empty or authoritative-empty mapping, family status set by future materializer (`fresh`, `stale`, `deferred`, or `resource_limit` under the established state-string convention), and version `"1"`; each source slice retains its own manifest status.
D. Later canonical source delete: remove exactly that source-key slice in the candidate, preserve the family version, and never reinterpret an empty remaining mapping as `not_materialized` if the family had already materialized. The delete lifecycle is deferred beyond 1A2.

LINEAGE_SEMANTIC_VERSION_PERSISTENCE=Persist `lineage_facts_semantic_version` inside the pickled `RepositoryAnalysisState`, adjacent to mapping/state; do not put it in `LiveStateMetadata.schema_version` or registry schema. Normalization must accept only `None` for pre-lineage/not-materialized state or exact `"1"` for known materialized lineage. Any non-`None` mismatch is a fail-closed snapshot rejection, not a coerced version. Legacy absence remains `None`, never a fabricated `"1"`.

TAGGED_UNION_SERIALIZATION_REQUIRED=NO. Pickle preserves the concrete class for `MaterializedOccurrenceRef | SemanticEndpoint`, so occurrence and endpoint cannot merge on round trip. A small lineage-specific load validator is still required: pickle bypasses dataclass `__post_init__`, so `load_snapshot` must validate the mapping/key/value/endpoint shapes and reject unknown or malformed materialized lineage state before it is returned.

MINIMAL_SERIALIZATION_ADAPTER=Add private `live_state.store._normalize_lineage_facts_state(state)` and call it in both current `load_snapshot` normalization branches after `_normalize_symbol_call_facts`. It must: install the A/B triple when attributes are absent; require a dict keyed by non-empty source key; require `MaterializedLineageSourceFacts` values whose manifest source key matches the dict key; structurally revalidate nested materialized anchor/flow/surface references and `SemanticEndpoint` slots through their existing constructors/validators; preserve `ProviderRef`, `SurfaceDeclarationEvidence`, dynamic boundary, and slot strings unchanged; reject an unrecognized endpoint object, invalid version/status pairing, or malformed data by raising `pickle.UnpicklingError` so `load_snapshot` returns `None`. This is a targeted hydration validator, not a new generic serializer and performs no registry/source/AST work.

COW_IMPACT=YES. Add `lineage_facts_by_source`, `lineage_facts_state`, and `lineage_facts_semantic_version` to `CandidateState`; `_prepare_candidate_state` must create `dict(getattr(state, "lineage_facts_by_source", {}) or {})` and copy scalar fields with legacy defaults. `_apply_delta_and_commit` must assign all three candidate values back to `self.state`. Never share the outer dict; frozen `MaterializedLineageSourceFacts` values and tuple contents may be shared safely. No Stage 1A2 branch may mutate an existing slice or construct registry identities.

DELETE_STATE_INVARIANT=Future source deletion removes `candidate.lineage_facts_by_source[canonical_source_key]` only. All remaining slices must still satisfy their own manifest/source key/fingerprint invariant; a cross-source edge remains represented through `SemanticEndpoint`, not a retained foreign occurrence. Family state/version are not reset merely because the mapping becomes empty after a real deletion.

CACHE_VERSIONING_IMPACT=`LIVE_STATE_SCHEMA_VERSION`: no bump in 1A2; the generic pickle envelope remains readable and the new reader explicitly normalizes legacy missing attributes. `ENGINE_CACHE_SCHEMA_VERSION`: no bump; it does not serialize a field-specific state schema. Persistent registry schema: no bump; hydration does not allocate or mutate identities. `LINEAGE_FACTS_SEMANTIC_VERSION`: remains `"1"` and becomes the persisted lineage-family value only after materialization. No other cache/version/fingerprint contract has a demonstrated need to change.

REAL_LEGACY_TEST_PATH=Existing closest real snapshot fixture is `tests/test_cycles_live_lifecycle.py:LegacySnapshotStateWithoutCycles` plus `test_legacy_snapshot_hydration_recomputes_cycles_in_ram`, which writes with production `save_snapshot` and reloads through production `load_snapshot`; analogous fixtures exist for topology and cached analytics. None currently verifies a missing family through `hydrate_repository_engine`. The Stage 1A2 focused test should use a minimal `LegacyStateWithoutLineage` with valid `modules` and non-None `ProjectGraph`, write it using production `save_snapshot` into the repo-id cache, then invoke production `hydrate_repository_engine`; it exercises `migrate_legacy_snapshot -> load_engine_state -> load_snapshot -> normalizer -> IncrementalAnalysisEngine` without a source/AST scan.

LEGACY_SNAPSHOT_COMPATIBILITY_GAP=YES. Current production loader has the correct extension point and real legacy-load tests, but no existing lineage-absence normalizer or real `hydrate_repository_engine` regression test for this new family. Stage 1A2 closes this gap.

FULL_SCAN_REQUIRED_FOR_HYDRATION=NO

PERSISTENT_ID_ALLOCATION_DURING_HYDRATION=NO. The Stage 1A2 lineage normalizer must not import or call `PersistentIdentityRegistry`; it only structurally validates already-persisted opaque IDs/slots. `hydrate_repository_engine` continues to construct the existing registry object for the engine, but lineage hydration performs no `transaction`, `sync_with_workspace`, or identity allocation.

EXACT_FILES_FOR_STAGE_1A2=
`contextor/core/analysis/state_manager.py`; `contextor/core/analysis/incremental/plan_executor.py`; `contextor/core/analysis/incremental/engine.py`; `contextor/core/live_state/store.py`; new focused `tests/test_lineage_state_lifecycle.py`. `contextor/core/domain/lineage_facts.py`, `contextor/core/domain/__init__.py`, `contextor/core/api/facade.py`, and `contextor/core/live_state/hydration.py` need no Stage 1A2 production modification: the domain is closed, full bootstrap uses state defaults, and hydration already routes through `load_snapshot`.

EXACT_SYMBOLS_FOR_STAGE_1A2=`RepositoryAnalysisState`; `CandidateState`; `_prepare_candidate_state`; `IncrementalAnalysisEngine._apply_delta_and_commit`; `load_snapshot`; new private `_normalize_lineage_facts_state`; focused legacy fixture/test helpers only.

PLANNED_DIFF=
1. In `RepositoryAnalysisState`, add the three sparse lineage fields with B defaults.
2. In `CandidateState` and `_prepare_candidate_state`, carry a copied outer mapping, family status, and optional version.
3. In `_apply_delta_and_commit`, publish the three candidate fields exactly once with the existing field assignments. Do not add a lineage refresh-plan family, extractor, materializer, index, or delete code.
4. In `load_snapshot`, invoke the private lineage normalizer in both envelope and legacy-payload paths. It normalizes absence, validates known materialized data, and rejects bad lineage payloads fail-closed.
5. Add one focused lifecycle test module covering only state, snapshot/load/hydration, and COW contracts.

FOCUSED_TESTS=
1. `RepositoryAnalysisState` and `_prepare_candidate_state` default to `{}`, `not_materialized`, `None`; candidate outer mapping is not aliased.
2. Production-written legacy object without lineage attributes -> production `hydrate_repository_engine` -> B triple, with source/AST analysis functions guarded to fail if called.
3. One valid `MaterializedLineageSourceFacts` slice -> `save_snapshot` -> `load_snapshot`/hydration -> exact equality of mapping, manifest, facts, and version `"1"`.
4. Occurrence and `SemanticEndpoint` surfaces/flows round-trip as their original distinct concrete classes.
5. `SurfaceDeclarationEvidence`, `ProviderRef`, non-empty dynamic boundary, and semantic slot string survive exact round trip.
6. Unknown endpoint object, mismatched source-key/manifest, malformed slot, invalid status/version pair, and lineage version mismatch make `load_snapshot` return `None` (fail closed).
7. Candidate copy/commit changes a replacement outer mapping without mutating/aliasing canonical lineage mapping; no materialized slice mutation.
8. Patch/spy registry allocation APIs and source/AST/full-analysis entry points: lineage normalization calls neither.

RISKS=
1. Pickle does not execute dataclass post-init during load; omitting targeted revalidation would accept malformed typed lineage values.
2. Adding a default field alone would make new in-memory state safe but would not normalize old pickled instances, so both `load_snapshot` branches are mandatory.
3. Copying the outer mapping shallowly is correct only because Stage 1A records are frozen; future code must replace slices rather than mutate nested values.
4. Existing hydration creates the registry object for engine operation; tests must distinguish that construction from prohibited identity allocation/synchronization.
5. Do not set family state to `fresh` from `{}`: that would violate the legacy absence contract and could create false LIVE readiness.

READY_FOR_CONCRETE_STAGE_1A2_PATCH=YES. The actual state/COW/snapshot/hydration owners and the current real legacy normalization seam are confirmed; the remaining compatibility gap is exactly the scoped Stage 1A2 patch and focused regression test.

FILES_CHANGED=NONE
TESTS_RUN=NONE
DIFFS=NONE
