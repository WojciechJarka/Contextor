# CPA_FULL_AST_SEMANTIC_COVERAGE_AUDIT — PERSISTENCE_HYDRATION

STATUS=PARTIAL
HEAD=3b64374c4ed39b438b6391196edbbeb72729bc4a
WORKTREE_STATE=CLEAN before this report was written; no source/test/docs changes. The report file itself is excluded by the requested reporting contract.
RUNTIME_FRESHNESS=Contextor implementation reads returned canonical_state=fresh, canonical_revision=1599, provenance=live, workspace_sync=verified. The lineage query freshness contract reports workspace_sync=unverified by design; do not treat that as repository-wide sync proof.

PERSISTENCE_HYDRATION_STATUS=PARTIAL

## PERSISTENCE_OWNERS

- Full analysis: ContextorFacade.analyze_project builds RepositoryAnalysisState; builds a FileState payload for target_revision; calls save_engine_state with exact_revision; only after save succeeds does it connect and call client.publish. A failed LIVE publish is retained as warning/status and does not roll back the already-published snapshot.
- LIVE incremental update: IPC captures previous state/revision, clones a candidate, runs the updater, validates/binds the exact next revision, calls the persister, then under lock swaps _state and _revision, then records the update event. The runtime persister calls save_snapshot(exact_revision=...) and advances persisted_state only after a matching revision is saved.
- Load/hydration: repository identity → legacy cache-path migration/check → LIVE connect/ping/snapshot if available → otherwise metadata-validated load_engine_state snapshot fallback → module/graph minimum checks → IncrementalAnalysisEngine with separately loaded PersistentIdentityRegistry and FileStateManager. Hydration does not run full analysis or parse source.
- Separate scoped-analysis path: hydrates an engine, calls engine.update_file, and can call hydrated.client.publish directly; that path has no save_snapshot call between update and publish.

CODE_PATH_PROVED: contextor/core/api/facade.py:956-989,1091-1115,1130-1179,1570-1596; contextor/core/live_state/runtime.py:1078-1198; contextor/core/live_state/ipc.py:1203-1259,1271-1514; contextor/core/live_state/hydration.py:29-112.

## SNAPSHOT_SCHEMA_CONTRACT

- CURRENT_SCHEMA_VERSION=1.4 (LIVE_STATE_SCHEMA_VERSION).
- LINEAGE_MANIFEST_SCHEMA_VERSION=1.0.
- SUPPORTED_SCHEMA_VERSIONS=1.0, 1.1, 1.2, 1.3, 1.4, literally accepted by read_metadata.
- REJECTED_SCHEMA_VERSIONS=all other/malformed outer metadata versions. read_metadata returns None; load_snapshot returns None; load_engine_state converts load exceptions to None. Hydration tries the LIVE snapshot first, then the snapshot cache when needed; if neither yields a usable state, hydration returns None. The store itself does not set a resync flag or launch analysis.- MIGRATION_OR_NORMALIZATION_POLICY=legacy cache-path copy/migration plus in-memory normalizers and explicit deferred/not_materialized defaults; no general transform that makes arbitrary old canonical families current. Schema 1.2 monolithic state is still loadable when the payload satisfies current validators. A schema 1.3 canonical state missing the now-required re-export family is rejected.
- For missing legacy analytics fields, the loader defaults to empty payload plus deferred; missing syntax diagnostics default to empty plus not_materialized; missing lineage defaults to empty plus not_materialized. Unsupported lineage version, malformed family state, corrupt split generation, incomplete re-export coverage, or identity/revision mismatch fail closed as None.
- SNAPSHOT_SCHEMA_FAIL_CLOSED=PARTIAL. Outer unsupported-version rejection is proved. The envelope loader compares embedded revision and lineage-manifest filename to outer metadata, but does not compare embedded schema_version, state_id, repo_id, root_path, state_file, or file_state_file as a complete metadata tuple. A raw state with absent identity can therefore reach assignment from embedded metadata without an explicit embedded-vs-outer identity equality check. This boundary is a GAP_CANDIDATE; no fault-injection probe was run.

DIRECT_EVIDENCE: store.py:41-45,1410-1441,1910-1935,2044-2063,2170-2273; tests/test_live_state_consistency.py::test_schema_mismatch; tests/test_live_state_store.py::test_schema_12_monolithic_snapshot_remains_loadable and ::test_legacy_canonical_snapshot_without_reexport_facts_is_rejected.

## PERSISTENCE_HYDRATION_MATRIX

| FAMILY_OR_BOUNDARY | BEFORE_SAVE | PERSISTED_FORM | LOAD_NORMALIZATION | AFTER_HYDRATION | FRESHNESS_EFFECT | ROUNDTRIP_VERDICT | EVIDENCE |
|---|---|---|---|---|---|---|---|
| modules | canonical module mapping | core state pickle | no family rebuild; hydration requires non-empty modules | same mapping | stored facts retained | ROUNDTRIP_PROVED | store load; generic snapshot tests |
| artifacts | canonical artifact mapping | core state pickle | no family rebuild | same mapping | stored facts retained | ROUNDTRIP_PROVED | direct pickle path; consumption validator checks target domain when used |
| reexport_facts_by_module | one fact per module | core state pickle | strict structural and exact module-domain validation | same mapping or load rejected | missing/incomplete family is not complete | ROUNDTRIP_PROVED | save/load validators; roundtrip and fail-closed tests |
| module_usages | per-module usage facts | core state pickle | legacy symbol-call entries normalized to sorted primitive tuples; absent legacy family defaults {} | normalized calls and other fields retained | materialized flag preserved | ROUNDTRIP_PROVED | store.py:63-118; state/manifest roundtrip test || module_usages_manifest | per-module source fingerprints | core state pickle | no semantic rebuild; absent legacy field defaults {} | same mapping | no automatic freshness promotion | ROUNDTRIP_PROVED | direct pickle plus compatibility default |
| dependency_graph | canonical graph | core state pickle | no graph rebuild; hydration rejects None | same graph | no source re-analysis | ROUNDTRIP_PROVED | hydration owner |
| artifact_consumption | exact target→consumers/channels mapping | core state pickle | no store normalizer; consumer surfaces re-run exact target-domain validation | same serialized mapping | helper requires state=fresh, exact target-key coverage, valid consumers/channels, and resync_required=false | PARTIAL | state_manager.py:531-683; no dedicated exact persistence assertion found |
| artifact_consumption_state | fresh/stale/deferred marker | core state pickle | preserved verbatim | same marker | marker alone is not sufficient for fresh queries | PARTIAL | helper above; no store-level normalization |
| module_parse_freshness | per-module valid/LKG state | core state pickle | no family normalizer | same stored records | stale stays stale when present; no cross-hydration LKG lifecycle assertion | PARTIAL | syntax lifecycle test is in-process only |
| syntax_diagnostics_by_path | checked-none or checked-with-errors per path | core state pickle | absent legacy field defaults {} | exact diagnostic payload | status preserved | ROUNDTRIP_PROVED | syntax roundtrip blocks source parse and asserts exact facts |
| syntax_diagnostics_state | family freshness marker | core state pickle | absent legacy field defaults not_materialized | same marker | no missing→fresh default | ROUNDTRIP_PROVED | dedicated fresh and legacy assertions |
| collision_facts | canonical collision facts | core state pickle | absent legacy field defaults {} | same facts | state marker controls query availability | ROUNDTRIP_PROVED | loader compatibility path |
| collisions | collision projection | core state pickle | absent legacy field defaults [] | same list | no automatic recompute | ROUNDTRIP_PROVED | loader compatibility path |
| collisions_state | fresh/stale/deferred marker | core state pickle | absent legacy field defaults deferred | same marker | absent does not become fresh | ROUNDTRIP_PROVED | loader compatibility path |
| lineage_facts_by_source | source slices | exact-revision: generation chunks + manifest; non-exact legacy save: monolithic core pickle | every manifest-listed chunk type/key/fingerprint/semantic-version checked; slices revalidated unless cache proves eligible | hydrated slice map from manifest | family marker retained; missing manifest entries are not checked against independent expected source domain | PARTIAL | store.py:1174-1392,1964-2027; roundtrip/corruption tests || lineage_facts_state | family status | core pickle | enum/status checked; materialized status requires current semantic version; not_materialized forbids slices/version | same validated family status | stale/deferred remain family-stale; invalid pair fails closed | PARTIAL | store.py:336-437; partial-generation gap |
| lineage_facts_semantic_version | semantic contract version | core pickle | must equal current version when present/materialized; invalid version fails closed | same validated version | no unsupported semantic version accepted | ROUNDTRIP_PROVED | store.py:376-393; lineage lifecycle tests |
| lineage_owner_source_index | derived owner→source index | core pickle as a cache | rebuilt from hydrated source slices | deterministic derived index | recomputed, not authoritative persisted projection | REBUILT_DETERMINISTICALLY | store.py:440-465 |
| lineage_source_owner_index | derived source→owner index | core pickle as a cache | rebuilt from hydrated source slices | deterministic derived index | recomputed | REBUILT_DETERMINISTICALLY | store.py:440-465 |
| lineage_query_index_state | derived-index status | core pickle as a cache | not_materialized if family absent; otherwise builder succeeds then set fresh | status rebuilt | can be fresh for a derived index even when family status stale/deferred; family status independently gates exact query capability | PARTIAL | store.py:440-465; live capability checks both statuses |
| lineage_semantic_anchor_bindings_complete | derived completeness bit | core pickle as a cache | recomputed by build_lineage_query_indexes(hydrated_sources) | deterministic for loaded slices | subset-completeness risk follows split manifest domain gap | PARTIAL | store.py:454-464 |
| dependency_matrix | derived matrix | core state pickle | no rebuild in snapshot loader | same payload | state retained | ROUNDTRIP_PROVED | state field and store path |
| dependency_matrix_state | fresh/stale/deferred marker | core state pickle | absent legacy field defaults deferred | same marker | absent does not become fresh | ROUNDTRIP_PROVED | store compatibility defaults |
| shared_usage_clusters | derived clusters | core state pickle | no rebuild in snapshot loader | same payload | state retained | ROUNDTRIP_PROVED | state field and store path |
| shared_usage_clusters_state | marker | core state pickle | absent legacy field defaults deferred | same marker | absent does not become fresh | ROUNDTRIP_PROVED | store compatibility defaults |
| cached_analytics | cached analytics payload | core state pickle | no rebuild in snapshot loader | same payload | state retained | ROUNDTRIP_PROVED | state field and store path |
| cached_analytics_state | marker | core state pickle | absent legacy field defaults deferred | same marker | absent does not become fresh | ROUNDTRIP_PROVED | store compatibility defaults || topology_analytics | topology payload | core state pickle | no rebuild in snapshot loader | same payload | state retained | ROUNDTRIP_PROVED | state field and store path |
| topology_metrics_state | marker | core state pickle | absent legacy field defaults deferred | same marker | absent does not become fresh | ROUNDTRIP_PROVED | store compatibility defaults |
| cycles | cycle payload | core state pickle | no rebuild in snapshot loader | same payload | state retained | ROUNDTRIP_PROVED | state field and store path |
| cycles_state | marker | core state pickle | absent legacy field defaults deferred | same marker | absent does not become fresh | ROUNDTRIP_PROVED | store compatibility defaults |
| trie | derived trie object | core state pickle | no rebuild in hydration | same object/value | no freshness marker | ROUNDTRIP_PROVED | direct pickle |
| package_root | package-root string | core state pickle | no rebuild | same string | no freshness marker | ROUNDTRIP_PROVED | direct pickle |

## REEXPORT_PERSISTENCE

- Save of a RepositoryAnalysisState rejects re-export facts unless validation succeeds and their module keys exactly cover state.modules.
- Load repeats this validation before returning a canonical state. A missing family in a legacy canonical state fails closed and requires fresh full analysis; accepting an older outer schema does not waive the required family contract.
- Lineage query backend lazily builds the re-export alias index from that same hydrated state's reexport_facts_by_module after revalidating against the same modules.
- REEXPORT_ROUNDTRIP=PROVED. Dedicated test asserts exact persisted mapping equality; separate tests assert incomplete save and missing legacy family rejection.

## LINEAGE_SPLIT_GENERATION

- Exact-revision save creates revision/token-specific core pickle, FileState payload, manifest, and source chunks. It fsyncs generation files, publishes outer metadata with os.replace last, then treats that as commit. On caught save failure, exact-revision generation files are removed; prior metadata/generation remains selected. Old committed generations are retained.
- Load selects generation only through outer metadata. Core envelope revision and manifest filename are checked against outer metadata; manifest checks schema, state ID, revision, safe child paths, and each chunk's source key/fingerprint/semantic version/type. Missing/corrupt/mismatched listed chunks fail closed.
- Rebuilt owner/source/query indexes use precisely the hydrated lineage_facts_by_source slices; the query index is not trusted from the pickle.
- Missing manifest entry/source-domain completeness is not checked: core pickle deliberately has an empty slice map, loader accepts each source listed by the manifest, and normalizer validates only those slices. If the manifest loses one entry but remaining entries are internally valid, core lineage_facts_state can remain fresh and the index is rebuilt as fresh over only the remaining slices.- LINEAGE_SPLIT_GENERATION_ATOMICITY=PARTIAL. Atomic publication of the selected generation and fail-closed handling of corruption are covered; completeness of the source-key domain and abrupt power-loss durability of directory-entry replacement are not proved.

## ARTIFACT_CONSUMPTION_ROUNDTRIP

- Values are core-pickled without store normalization. The canonical freshness helper recomputes exact target-domain coverage against hydrated artifacts, rejects malformed consumer/channel data and resync_required, and returns false unless persisted family state is exactly fresh.
- Fresh mappings remain value-preserved and can be declared genuinely fresh only if they validate against the loaded target domain. Stale/deferred markers remain non-fresh.
- No direct save→hydrate assertion was found for exact consumers/channels; this is CODE_PATH_PROVED, not BEHAVIORALLY_PROVED.
- ARTIFACT_CONSUMPTION_ROUNDTRIP=PARTIAL.

## FRESHNESS_ROUNDTRIP

- Existing state markers and per-module parse records are normally preserved verbatim by pickle. No general loader converts a missing analytic/syntax field to fresh; missing legacy analytics default to deferred and missing syntax/lineage to not_materialized.
- Re-export coverage and lineage schema/status/version are validated and fail closed.
- Artifact-consumption effective freshness is recomputed by exact target coverage at consuming projections, not by the loader itself.
- Lineage owner/source indexes and anchor-binding completeness are recomputed from persisted hydrated slices. lineage_query_index_state becomes fresh whenever lineage family is anything except not_materialized; callers still require lineage_facts_state=fresh as well.
- Unknown/non-enum lineage state/version fails closed. Other families' arbitrary pre-existing state strings have no uniform snapshot-time enum validation.
- FRESHNESS_ROUNDTRIP=PARTIAL.

## SYNTAX_LKG_ROUNDTRIP

- Existing incremental assertions prove valid→invalid retains the prior symbol artifact, records current syntax errors, sets that module parse state stale, and valid recovery clears the diagnostic and parse-freshness entry.
- Separate snapshot roundtrip asserts exact syntax diagnostic persistence without source parsing; legacy absence stays not_materialized.
- No existing assertion combines invalid transition → persisted snapshot → fresh-process hydration → retained LKG/parse stale/diagnostic triple. The requested end-to-end invariant remains PARTIAL; no probe was run.

## FILESTATE_WORKSPACE_AUTHORITY

- Exact-revision save requires FileState payload _meta.state_id and _meta.revision to match state ID/revision; outer metadata points to that file generation.
- FileStateManager loads only the referenced generation when present. Missing/incomplete/mismatched referenced generation becomes empty/untrusted and does not fall back to legacy file_state.json. Matching generation identity/revision yields a trusted baseline, not proof of current workspace equality.- Later has_changed checks missing path, new path, mtime/size change, and SHA-256 if stat tuple matches; missing tracked SHA is changed. Hydration itself does not scan/reconcile actual workspace content.
- Startup watcher reconciliation verifies authoritative generation identity and defers/requires resync when it cannot trust the baseline; it compares current candidate fingerprints before accepting. No real Contextor workspace resync was run.
- FILESTATE_CANONICAL_AUTHORITY_CONSISTENCY=PARTIAL: snapshot/FileState generation pairing is proved, but actual source truth becomes authoritative only after watcher reconciliation.

## PERSISTENT_IDENTITY_ROUNDTRIP

- Registry loads active mappings, recovery/orphan maps and slot generations independently of the canonical snapshot. It repairs one-sided entries into recovery; active IDs are persisted via temp JSON + committing manifest + os.replace files. Same-path return restores recovery ID; different path allocation uses an incremented slot generation; module and artifact IDs share this lifecycle.
- Hydration constructs PersistentIdentityRegistry separately from loaded RepositoryAnalysisState; there is no joint snapshot+registry commit marker or loader comparison of canonical IDs to registry generation.
- In incremental updates, identity sync transaction commits inside IncrementalAnalysisEngine._apply_delta_and_commit before _repository_updater returns; IPC calls the canonical snapshot persister only after updater returns. If that later persistence fails, IPC retains previous canonical state while the registry transaction has already committed. Generic persistence error does not inherently attach resync_required (revision conflict may do so).
- PERSISTENT_IDENTITY_ROUNDTRIP=PARTIAL. ID continuity/recovery is asserted; cross-store atomicity for later snapshot failure is not.

## REVISION_ATOMICITY

- update_file path with configured persister: candidate remains invisible while persisting; persistence failure leaves canonical pointer/revision/event journal unchanged. Successful persister returns before state/revision swap; event is appended after swap.
- Full-analysis path: snapshot save precedes LIVE publish; failed/not-attempted publish does not roll back the already saved metadata revision.
- Scoped single-file path: in-memory incremental update may be published directly without a preceding snapshot save. _execute_publish swaps RAM state and appends an event but does not call a persister.
- CAN_NEW_REVISION_BECOME_VISIBLE_WITHOUT_DURABLE_SNAPSHOT=YES for direct scoped/generic publish paths; NO for update_file when its configured persister succeeds before commit.
- CAN_SNAPSHOT_ADVANCE_WITHOUT_RUNTIME_STATE_SWAP=YES when full-analysis snapshot save succeeds but LIVE publish is unavailable/rejected/fails.
- CAN_EVENT_REPORT_COMMIT_THAT_WAS_NOT_DURABLE=YES on scoped/generic publish without a prior durable snapshot; NO for the normal persisted incremental update path.
- REVISION_COMMIT_ATOMICITY=PARTIAL.
## TORN_WRITE_BOUNDARIES

- Exact generations use unique filenames and per-file flush/fsync. Metadata temp file is fsynced and atomically replaced last. Caught pre-commit failure cleans newly written exact-generation files; dedicated test injects metadata replacement failure and asserts old revision plus no new generation files.
- Crash before metadata publication leaves old selected generation authoritative; unreferenced new files may remain after abrupt process loss because cleanup is in finally, not a crash-recovery scan. Loader selects only metadata-referenced names.
- Crash/corruption in a referenced manifest/chunk returns no snapshot. Previous committed generations are retained but no automatic fallback to an earlier generation was observed.
- No parent-directory fsync after replace was found; power-loss durability of the rename itself is UNKNOWN. No fault injection beyond existing test assertions was run.

## HYDRATED_QUERY_PARITY

- get_module_context, get_artifacts_for_module, get_artifact_blast_radius, get_name_collisions, get_symbol_call_context and related cache-backed MCP tools obtain one get_or_init_engine state. On live session/revision change the runtime pings then snapshots current LIVE state and replaces the per-root engine; with no live service, it hydrates from snapshot. No query-time repository analysis is launched.
- get_symbol_lineage uses canonical IPC query rather than a separate cache copy. IPC holds its state lock while invoking the query handler and returns the server revision with result. Transport checks result freshness revision and selected facts metadata revision against that same response revision.
- Hydrated lineage owner/source indexes rebuild from loaded source slices; re-export alias index lazily rebuilds from the same hydrated modules/re-export facts. Backend metadata and selected lineage facts refer to one canonical state revision.
- Existing assertion proves selected lineage metadata revision equals freshness canonical revision. The contract reports workspace_sync=unverified for that lineage query, so revision coherence does not certify current workspace content.
- HYDRATED_QUERY_REVISION_CONSISTENCY=PROVED for the inspected public surfaces' single-state/revision path, with workspace synchronization remaining a separate gate.

## EXISTING_TARGETED_TEST_EVIDENCE

Tests were read for assertion semantics only. None were executed in this task.

1. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
   TEST_NODE_ID=tests/test_live_state_store.py::test_snapshot_roundtrip_increments_revision_and_records_writer
   CERTIFIES=state+metadata roundtrip, revision increments 1→2, writer and metadata equality.
   DOES_NOT_CERTIFY=RepositoryAnalysisState family completeness or hydration after process loss.

2. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
   TEST_NODE_ID=tests/test_live_state_store.py::test_exact_snapshot_revision_binds_embedded_state_and_metadata   CERTIFIES=embedded state and outer metadata revision both equal exact revision.
   DOES_NOT_CERTIFY=all embedded metadata identity/schema fields are cross-compared.

3. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
   TEST_NODE_ID=tests/test_live_state_store.py::test_current_schema_14_splits_lineage_and_roundtrips
   CERTIFIES=1.4 exact-revision save writes empty core slice map, manifest domain/chunks, then restores source slices.
   DOES_NOT_CERTIFY=manifest source-domain omission detection.

4. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
   TEST_NODE_ID=tests/test_live_state_store.py::test_current_schema_reexport_facts_roundtrip
   CERTIFIES=exact re-export mapping equality across save/load.
   DOES_NOT_CERTIFY=missing-domain load rejection (separate test).

5. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
   TEST_NODE_ID=tests/test_live_state_store.py::test_save_snapshot_rejects_incomplete_canonical_reexport_facts
   CERTIFIES=save rejects re-export facts that do not cover current module domain.
   DOES_NOT_CERTIFY=load behavior.

6. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
   TEST_NODE_ID=tests/test_live_state_store.py::test_legacy_canonical_snapshot_without_reexport_facts_is_rejected
   CERTIFIES=legacy 1.3 canonical payload missing the family loads as None.
   DOES_NOT_CERTIFY=all pre-1.4 schemas are rejected; some valid old snapshots remain loadable.

7. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_consistency.py
   TEST_NODE_ID=tests/test_live_state_consistency.py::test_schema_mismatch
   CERTIFIES=unsupported outer schema 999.999 causes load_engine_state to return None.
   DOES_NOT_CERTIFY=embedded envelope schema mismatch.

8. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
   TEST_NODE_ID=tests/test_live_state_store.py::test_split_lineage_corruption_fails_closed
   CERTIFIES=missing listed chunk, wrong manifest revision, and corrupt chunk return None.
   DOES_NOT_CERTIFY=valid but incomplete manifest source list.

9. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
   TEST_NODE_ID=tests/test_live_state_store.py::test_split_lineage_failed_metadata_commit_cleans_new_generation
   CERTIFIES=injected metadata replace failure leaves old revision selected and removes failed new generation files.
   DOES_NOT_CERTIFY=abrupt process/power loss during replace.

10. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_state_store.py
    TEST_NODE_ID=tests/test_live_state_store.py::test_schema_12_monolithic_snapshot_remains_loadable
    CERTIFIES=valid schema 1.2 monolithic envelope is loadable with correct state ID and revision.
    DOES_NOT_CERTIFY=old canonical snapshots missing currently-required re-export facts.

11. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py    TEST_NODE_ID=tests/test_syntax_diagnostics_full_analysis.py::test_syntax_diagnostics_snapshot_roundtrip_needs_no_source_reconstruction
    CERTIFIES=diagnostic payload/state roundtrip; hydration does not parse source.
    DOES_NOT_CERTIFY=LKG module-parse freshness roundtrip.

12. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py
    TEST_NODE_ID=tests/test_syntax_diagnostics_full_analysis.py::test_legacy_snapshot_marks_syntax_family_not_materialized
    CERTIFIES=legacy missing syntax family defaults to empty/not_materialized.
    DOES_NOT_CERTIFY=other missing families or invalid syntax LKG.

13. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py
    TEST_NODE_ID=tests/test_syntax_diagnostics_full_analysis.py::test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic
    CERTIFIES=valid→invalid retains old symbol artifact, records current diagnostic, marks parse state stale; valid recovery clears errors/state.
    DOES_NOT_CERTIFY=process-loss snapshot hydration across that invalid interval.

14. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py
    TEST_NODE_ID=tests/test_syntax_diagnostics_full_analysis.py::test_live_persistence_failure_does_not_publish_half_updated_syntax_fact
    CERTIFIES=failed persister leaves old canonical syntax/parse state/revision visible while candidate has syntax error and stale parse state.
    DOES_NOT_CERTIFY=registry side effects or successful snapshot→fresh-process hydration.

15. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py
    TEST_NODE_ID=tests/test_lineage_state_lifecycle.py::test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild
    CERTIFIES=legacy absent lineage normalizes to empty/not_materialized through fresh-process hydration without source rebuild.
    DOES_NOT_CERTIFY=materialized split manifest completeness.

16. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py
    TEST_NODE_ID=tests/test_lineage_state_lifecycle.py::test_fresh_process_hydrates_materialized_symbolic_lineage_without_analysis
    CERTIFIES=snapshot hydration preserves materialized symbolic lineage without AST parsing or analysis.
    DOES_NOT_CERTIFY=partial source-domain detection.

17. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_persistent_registry.py
    TEST_NODE_ID=tests/test_persistent_registry.py::test_identity_preservation
    CERTIFIES=same-path recovery preserves ID; different path reuses slot with next generation.
    DOES_NOT_CERTIFY=atomicity with canonical snapshot save.

18. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_persistent_registry.py
    TEST_NODE_ID=tests/test_persistent_registry.py::test_write_transaction_allocates_and_persists_missing_ids
    CERTIFIES=module and artifact mappings survive registry reload.
    DOES_NOT_CERTIFY=snapshot/registry joint commit.
19. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_lineage_state_lifecycle.py
    TEST_NODE_ID=tests/test_lineage_state_lifecycle.py::test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_state
    CERTIFIES=exception during registry-sync lineage revalidation restores in-memory registry view and canonical state.
    DOES_NOT_CERTIFY=registry transaction succeeds, then later snapshot persister fails.

20. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_mutation_coordinator.py
    TEST_NODE_ID=tests/test_live_mutation_coordinator.py::test_candidate_is_invisible_during_slow_persistence
    CERTIFIES=candidate/revision/event remain invisible until persister returns, then state and revision publish.
    DOES_NOT_CERTIFY=durability of direct publish calls without persister.

21. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_mutation_coordinator.py
    TEST_NODE_ID=tests/test_live_mutation_coordinator.py::test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnostics_unchanged
    CERTIFIES=persistence conflict leaves active state/revision/event sequence unchanged.
    DOES_NOT_CERTIFY=registry changes committed before a generic later persistence error.

22. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_watcher_startup_reconciliation.py
    TEST_NODE_ID=tests/test_live_watcher_startup_reconciliation.py::test_full_analysis_publishes_current_filestate_generation
    CERTIFIES=full analysis publishes tracked FileState paths with matching trusted state ID/revision.
    DOES_NOT_CERTIFY=workspace remained unchanged after snapshot; asserts tracking, not a full source diff.

23. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\test_live_watcher_startup_reconciliation.py
    TEST_NODE_ID=tests/test_live_watcher_startup_reconciliation.py::test_filestate_is_not_trusted_without_authoritative_live_generation_identity
    CERTIFIES=missing authoritative generation identity makes watcher baseline untrusted and requires resync.
    DOES_NOT_CERTIFY=all startup reconciliation races or canonical snapshot correctness.

24. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py
    TEST_NODE_ID=tests/analysis/test_lineage_live_query.py::test_live_lineage_state_freshness_is_ram_only_and_revision_bound
    CERTIFIES=lineage freshness metadata carries backend revision/provenance and both lineage/query-index status.
    DOES_NOT_CERTIFY=workspace content freshness; contract labels workspace_sync unverified.

25. FULL_WINDOWS_PATH=C:\Temp\Contextor_Repo\tests\analysis\test_lineage_live_query.py
    TEST_NODE_ID=tests/analysis/test_lineage_live_query.py::test_live_symbol_lineage_result_carries_selected_owner_names_and_same_revision_freshness
    CERTIFIES=selected facts metadata revision equals freshness canonical revision.
    DOES_NOT_CERTIFY=split manifest completeness.

## BEHAVIORAL_PROBES

BEHAVIORAL_PROBES=NOT_RUN
TEST_EXECUTION=NONENo pytest, runtime restart, full repository analysis, actual Contextor .contextor read/write, or behavioral probe was performed. Source plus inspected existing assertions were sufficient to classify identified gaps as PARTIAL; partial-manifest behavior and embedded-envelope mismatch were not dynamically exercised.

## GAP_CANDIDATES

### GAP 1 — SPLIT_LINEAGE_SOURCE_DOMAIN_COMPLETENESS

CASE=Manifest omits one otherwise-valid materialized source entry while remaining manifest/chunks and outer/core revision references agree.
EXPECTED=Every source slice included in the saved canonical lineage generation is present, or hydrated lineage must not be advertised fresh.
PERSISTENCE_BEHAVIOR=Exact save writes chunks and manifest; core pickle lineage source map is cleared. Loader validates only manifest-listed entries and has no independent expected-source-domain equality check.
HYDRATION_BEHAVIOR=Core family state/version remain fresh/current; only present slices are normalized; owner/source/query indexes rebuild from that subset and query-index state is set fresh.
CANONICAL_RISK=Some persisted lineage facts are absent after hydration.
FRESHNESS_RISK=Subset may be surfaced as fresh; semantic_anchor_bindings_complete is recomputed over subset.
QUERY_RISK=Missing owners/flows may appear as clean negative or incomplete lineage result.
SEVERITY_CANDIDATE=High; source-path proof, not dynamically probed.

### GAP 2 — EMBEDDED_METADATA_TUPLE_NOT_FULLY_BOUND

CASE=Outer metadata and embedded pickle metadata disagree in schema or an identity/path field while revision and lineage-manifest filename match; raw state lacks its own identity field.
EXPECTED=All generation identity and schema fields match before state is accepted.
PERSISTENCE_BEHAVIOR=Normal save writes one metadata object to both locations; loader does not compare the complete embedded metadata tuple to outer metadata.
HYDRATION_BEHAVIOR=Loader explicitly checks embedded revision and lineage-manifest filename, then validates raw state revision/state ID only when present; it does not compare every embedded schema/identity/path field to outer metadata.
CANONICAL_RISK=State identity/schema/path may be accepted from a different envelope than the selected outer metadata.
FRESHNESS_RISK=Loaded state can be assigned snapshot provenance/revision/identity without proving every envelope field matched.
QUERY_RISK=Potential wrong state identity or compatibility path; exact acceptance was not behaviorally exercised.
SEVERITY_CANDIDATE=Medium; direct missing-comparison evidence, runtime effect partly unknown.

### GAP 3 — REGISTRY_COMMIT_PRECEDES_CANONICAL_SNAPSHOT_COMMIT

CASE=Incremental update requires identity sync; registry transaction succeeds; later exact snapshot persistence raises a non-revision I/O error.
EXPECTED=Canonical snapshot and active ID registry remain aligned, or divergence is explicitly fail-closed/resync-required.PERSISTENCE_BEHAVIOR=Registry files commit inside updater before updater returns; canonical snapshot is saved later by IPC persister. These are separate commit boundaries.
HYDRATION_BEHAVIOR=Snapshot state and registry are loaded independently; no joint generation check compares canonical IDs to registry IDs.
CANONICAL_RISK=Previous active canonical state can coexist with newer active/recovery ID mappings.
FRESHNESS_RISK=Generic persistence error path does not inherently attach resync_required.
QUERY_RISK=Identity resolution can be incomplete or refer to registry generation newer than canonical state.
SEVERITY_CANDIDATE=High; code-path proof of ordering, no injected later persister failure.

### GAP 4 — SNAPSHOT_AND_LIVE_PUBLISH_ARE_NOT_ONE_COMMIT

CASE=Full-analysis save succeeds but LIVE publish is unavailable/rejected, or scoped analysis updates an engine and publishes without saving.
EXPECTED=Visible LIVE revision, durable snapshot revision and event refer to one durable generation.
PERSISTENCE_BEHAVIOR=Full-analysis snapshot metadata commits before LIVE publish; scoped path has no snapshot save before direct publish.
HYDRATION_BEHAVIOR=Restart prefers newer snapshot; an already-running LIVE service may still expose its prior revision after failed publish.
CANONICAL_RISK=Disk and active LIVE state can represent different revisions; direct scoped publication can be RAM-only.
FRESHNESS_RISK=Each side can independently look fresh for its own revision.
QUERY_RISK=Queries routed to LIVE versus snapshot-backed engine can observe different coherent revisions.
SEVERITY_CANDIDATE=High; direct caller/control-flow evidence.

### GAP 5 — WORKSPACE_TRUTH_IS_DEFERRED_TO_RECONCILIATION

CASE=Workspace files change after a matching FileState generation is persisted but before startup reconciliation checks current content.
EXPECTED=No query advertises workspace-current canonical truth before content reconciliation.
PERSISTENCE_BEHAVIOR=Snapshot/FileState ID+revision pair is structurally checked; trusted baseline alone does not compare current bytes.
HYDRATION_BEHAVIOR=Hydration returns LIVE or snapshot canonical state without scanning files; watcher later hashes/reconciles missing/new/changed paths.
CANONICAL_RISK=Snapshot can be internally consistent but stale against current workspace until reconciliation.
FRESHNESS_RISK=Revision freshness is not workspace freshness.
QUERY_RISK=Early queries may serve the coherent prior snapshot; no actual timing probe was run.
SEVERITY_CANDIDATE=Medium; authority boundary is explicit, pre-reconciliation behavior not probed.

## CARRY_FORWARD_GAPS

- STALE_RECEIVER_REFERENCE_EVIDENCE
- FACT_LINEAGE_ARTIFACT_CONSUMPTION_DISCREPANCY
- SEMANTIC_FIXPOINT_MECHANISM_PARTIAL
- INITIAL_GRAPH_CLOSURE_NOT_SEMANTIC_FIXPOINT
- STALE_LEGACY_CONSUMER_TARGET_AFTER_CONTENT_CHANGE=CLOSED

No carry-forward finding was reinterpreted or reopened.

## REQUIRED VERDICTS

PERSISTENCE_HYDRATION_STATUS=PARTIAL
SNAPSHOT_SCHEMA_FAIL_CLOSED=PARTIAL
REEXPORT_ROUNDTRIP=PROVED
LINEAGE_SPLIT_GENERATION_ATOMICITY=PARTIAL
FRESHNESS_ROUNDTRIP=PARTIAL
FILESTATE_CANONICAL_AUTHORITY_CONSISTENCY=PARTIAL
PERSISTENT_IDENTITY_ROUNDTRIP=PARTIAL
REVISION_COMMIT_ATOMICITY=PARTIAL
HYDRATED_QUERY_REVISION_CONSISTENCY=PROVED

## EVIDENCE LABELS

DIRECT_EVIDENCE:
- Current HEAD 3b64374c4ed39b438b6391196edbbeb72729bc4a; Git worktree was clean before writing this report.
- Contextor LIVE source context at revision 1599 was fresh; implementation reads had workspace_sync verified.
- Read-only source and assertion inspection only; no source/test/docs modified and no tests executed.

CODE_PATH_PROVED:
- Snapshot schema acceptance, normalizers, split-generation loader, metadata-last publication, and failure cleanup.
- Re-export save/load validation and same-state lazy alias-index construction.
- LIVE incremental candidate→persister→state swap→event order.
- Full-analysis save-before-publish and scoped update/publish path.
- Separate FileState and registry persistence/hydration paths.
- Lineage query IPC revision binding and hydrated index reconstruction.

CONTRACT_PROVED:
- Supported outer snapshot schemas are 1.0–1.4; 1.4 is current.
- Re-export family must cover canonical module domain.
- Artifact-consumption effective freshness requires exact target-domain coverage and no resync.
- Lineage query capability requires fresh family and fresh query index; response revision is checked against selected fact metadata.

BEHAVIORALLY_PROVED:
- Existing tests assert the cases enumerated under EXISTING_TARGETED_TEST_EVIDENCE. They were read only, not run in this task.
- No new behavior was dynamically proved during this audit.

INFERENCE:
- Partial manifest omission can produce fresh subset lineage because loader has no external source-domain equality check.
- A later snapshot failure after a committed identity transaction can leave registry and canonical state on different generations.
- Full/scoped publish paths can create snapshot/LIVE revision divergence as described above.

UNKNOWN:
- Actual runtime acceptance of an envelope with mismatched embedded metadata tuple.
- Abrupt power-loss durability of directory-entry replacements.
- Exact workspace-content state in the interval before watcher reconciliation.
- Whether an independent external operator guarantees repair of the identified cross-store divergence cases.

NEXT_UNEXECUTED_SECTION=FULL_LIVE_EXPECTED_PROOFS

FILES_CHANGED=NONE
DIFFS=NONE