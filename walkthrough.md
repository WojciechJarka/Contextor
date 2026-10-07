STATUS=CONFIRMED_DIVERGENCE
HEAD=44fb7ce2b043c8ffc52ad5bcea616d5f82f6e329
WORKTREE_STATE=CLEAN before report write; no source/tests/docs/schema files changed

CROSS_STORE_ATOMICITY_STATUS=CONFIRMED_DIVERGENCE

PRODUCTION_CONTROL_FLOW
- Contextor discovery completed first. Contextor canonical state was fresh at revision 1599 with workspace_sync=verified.
- Contextor get_symbol_call_context confirmed IncrementalAnalysisEngine.update_file calls _apply_delta_and_commit (engine.py lines 520 and 677).
- contextor/core/analysis/incremental/engine.py:760-1018 executes the refresh plan; when outcome.identity_sync_required is true it enters PersistentIdentityRegistry.transaction(), calls sync_with_workspace(), and finishes lineage work before the registry transaction exits. The canonical in-memory engine state is published after that transaction.
- contextor/core/reporting_engine/persistent_registry.py:198-262 writes transaction payloads, fsyncs, replaces registry files, removes the transaction marker, and then exits the transaction. sync_with_workspace is at lines 376-383; active module/artifact mappings are synchronized by _sync_kind at lines 385-435.
- contextor/core/live_state/runtime.py:1078-1106 creates a real FileStateManager and IncrementalAnalysisEngine with PersistentIdentityRegistry(root), then calls engine.update_file().
- contextor/core/live_state/runtime.py:1109-1203 persists a canonical snapshot through save_snapshot and maps SnapshotRevisionConflict to CanonicalPersistenceConflict.
- contextor/core/live_state/ipc.py:1271-1514 clones the canonical state, calls updater, validates the candidate revision, then calls persister. Active state/revision replacement and event publication occur only after persister succeeds. A generic persistence exception returns canonical_persistence_failed at the old revision; resync_required is added only when the exception exposes current_revision.
- contextor/core/live_state/hydration.py:29-82 resolves LIVE first, otherwise loads the persisted snapshot; lines 85-112 constructs a new registry and engine from that resolution.

IDENTITY_SYNC_PRECONDITION
- Used a real single-file incremental module add (added.py) in a temporary repository.
- Captured the production incremental phase trace from the real update. INCREMENTAL_EXECUTE_PLAN_END reported identity_sync_required=True, with identity_registry in patch_families.
- INCREMENTAL_REGISTRY_SYNC_END ran with missing_after_sync empty. The newly active module ID was 2/1, and the new artifact ID was A2/1.
- Thus the failure injection happened only after the real identity-sync path and persistent registry transaction completed.

FAULT_INJECTION
- Temporary root: C:\Users\DafoO\AppData\Local\Temp\contextor_cross_store_probe_7m3jsowv (TemporaryDirectory; verified removed after process exit).
- CONTEXTOR_CACHE_DIR and CONTEXTOR_REGISTRY_DIR both pointed under that temporary root. The temporary repository had no .contextor directory. C:\Temp\Contextor_Repo\.contextor and the current LIVE Contextor were not touched.
- Seeded one canonical module using the real production updater and real _repository_persister at revision 1. Constructed a real CanonicalLiveServer and invoked its _execute_update_file mutation executor with the real _repository_updater.
- The controlled persister callback ran after the updater returned. At callback entry, a newly loaded PersistentIdentityRegistry already contained the committed added module/artifact IDs, while persisted canonical snapshot metadata still reported revision 1. The callback then raised OSError("controlled cross-store atomicity probe failure").
- Trace sinks were replaced in-process with collectors/no-ops only to prevent external runtime-log writes; no repository source was patched.

STATE_BEFORE
- CANONICAL_REVISION_BEFORE=1
- CANONICAL_MODULES_BEFORE=["seed"]
- persisted canonical snapshot revision=1
- REGISTRY_ACTIVE_BEFORE:
  modules={"seed":"1/1"}
  artifacts={"seed::SEED_VALUE":"A1/1"}
- REGISTRY_RECOVERY_BEFORE:
  modules={"schema_version":1}
  artifacts={"schema_version":1}

STATE_AFTER_FAILURE
- UPDATE_RESULT_OR_EXCEPTION={"status":"error","error":"canonical_persistence_failed","revision":1,"expected_revision":2}
- Persister callback observed candidate modules=["added","seed"] and requested revision=2.
- CANONICAL_REVISION_AFTER=1
- CANONICAL_MODULES_AFTER=["seed"]
- persisted canonical snapshot revision after failure=1
- EVENT_SEQUENCE_AFTER={"activity_seq":0,"events":[]}
- REGISTRY_ACTIVE_AFTER:
  modules={"seed":"1/1","added":"2/1"}
  artifacts={"seed::SEED_VALUE":"A1/1","added::ADDED_VALUE":"A2/1"}
- REGISTRY_RECOVERY_AFTER:
  modules={"schema_version":1}
  artifacts={"schema_version":1}
- REGISTRY_SLOT_GENERATIONS_AFTER:
  modules={"schema_version":1,"1":1,"2":1}
  artifacts={"schema_version":1,"1":1,"2":1}
- RESYNC_GATE=false. Generic OSError response had no resync_required field, and the retained canonical state did not set resync_required.

FRESH_HYDRATION_RESULT
- A separate Python process called hydrate_repository_engine() and constructed a separate PersistentIdentityRegistry from persisted stores; no in-memory probe objects were reused.
- Hydration source=snapshot; canonical modules=["seed"]. The on-disk canonical snapshot metadata remained revision 1.
- HydratedRepositoryEngine.revision returned 0 on the snapshot fallback path; this is distinct from the persisted snapshot metadata revision 1. hydration.py initializes the resolver revision to 0 and only replaces it in the LIVE branch. Do not interpret this wrapper field as the durable snapshot revision.
- Fresh registry view contained active modules seed=1/1 and added=2/1.

NEXT_OPERATION_IMPACT
- Fresh-process PersistentIdentityRegistry.get_module_id("added") returned "2/1".
- "added" was active in the persisted registry but absent from hydrated canonical state modules=["seed"]. This behaviorally confirms that a subsequent ID lookup can treat the new identity as active alongside the old canonical snapshot.
- NEXT_OPERATION_RISK=stale active identity may be surfaced/resolved against canonical facts that do not contain the corresponding module/artifact. A subsequent incremental update was not executed.

EXISTING_TEST_COVERAGE
- tests/test_lineage_state_lifecycle.py:1326 test_identity_sync_revalidation_failure_rolls_back_registry_and_canonical_state uses _LifecycleRegistry, a small transactional registry model. It injects revalidation failure while identity-sync work remains inside the registry transaction and asserts canonical modules/artifacts/lineage and the original IDs remain unchanged. It does not test a successful durable PersistentIdentityRegistry commit followed by a later canonical persister failure.
- tests/test_live_mutation_coordinator.py:528 test_persistence_failure_leaves_canonical_state_revision_journal_and_diagnostics_unchanged uses an updater that only changes syntax diagnostics and a persister that raises SnapshotRevisionConflict. It asserts the old canonical object/revision, activity sequence, event list, and diagnostic trace remain unchanged. It does not perform a real identity-sync commit and does not use a generic I/O failure.
- These assertions cover rollback before registry commit and canonical isolation on a persistence conflict, respectively; neither covers the cross-store ordering reproduced here.
- Tests were read for assertion cross-check only; no pytest command was run because the behavioral probe directly exercised the requested path.

DIRECT_EVIDENCE
- Exact probe output showed identity_sync_required=True and INCREMENTAL_REGISTRY_SYNC_END before entering the failing persister callback.
- Fresh registry reload inside the callback and after failure showed added=2/1 and added::ADDED_VALUE=A2/1.
- The callback read canonical snapshot metadata revision=1, then raised controlled OSError for requested revision 2.
- Server response retained revision 1, active state modules=["seed"], activity_seq=0, and no events; no resync_required flag was returned.
- Fresh-process hydration read snapshot modules=["seed"] while a fresh registry lookup returned added=2/1.
- Temporary probe root was removed after the process exited.

CODE_PATH_PROVED
- Contextor implementation and call-context responses were fresh at canonical revision 1599 and workspace_sync=verified.
- Contextor and exact local source inspection establish the ordering: incremental registry transaction commit -> updater return -> persister -> canonical state/revision swap -> event publication.
- Exact test assertions establish that existing tests fail to cover the post-registry-commit/pre-snapshot-commit boundary.

CONTRACT_PROVED
- The requested fail-closed outcomes were OLD canonical + OLD registry, or OLD canonical + NEW registry with an explicit resync gate.
- Observed result was OLD canonical + NEW registry with no resync gate. This violates both allowed invariants.

BEHAVIORALLY_PROVED
- CROSS_STORE_ATOMICITY_STATUS=CONFIRMED_DIVERGENCE
- CANONICAL_AFTER_FAILURE=OLD (revision 1; module seed)
- REGISTRY_AFTER_FAILURE=NEW (module added and artifact added::ADDED_VALUE active)
- RESYNC_GATE=false
- FRESH_HYDRATION_RESULT=snapshot contains only seed; fresh registry contains added=2/1
- NEXT_OPERATION_RISK=persistent ID lookup returns an active identity missing from hydrated canonical modules
- SEVERITY_CANDIDATE=P2

INFERENCE
- P2 is a severity candidate because one failed incremental update leaves a durable active identity inconsistent with canonical facts and the inconsistency is observable by later ID lookup. The probe did not establish broader user-visible impact, data loss, or behavior of a subsequent incremental update.

UNKNOWN
- Whether and how each public ID-consuming query handles an active registry identity whose module/artifact is absent from canonical state.
- Whether the next successful incremental update fully reconciles all registry and canonical facts.
- Broader frequency or operational reach of this failure path.
- No fix was designed or implemented.

FILES_CHANGED=NONE
DIFFS=NONE
ACTUAL_DIFF=DIFFS=NONE

