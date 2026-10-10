# L32H2G — bounded canonical writer audit

## FILES_CHANGED
NONE (source/test/docs); report overwritten only at C:\Temp\Contextor_Repo\walkthrough.md.

## ACTUAL_DIFF
DIFFS=NONE (source/test/docs).

## SOURCE_SYNC
DIRECT_EVIDENCE: Contextor MCP get_symbol_implementation and get_source_range returned complete current source, canonical_state=fresh and workspace_sync=verified at revision 287. Literal workspace text was checked after Contextor discovery. No truncated source was used as complete evidence.

## LIVE_REVISION
DIRECT_EVIDENCE: get_live_events(after_revision=287) returned revision=287, latest_revision=287, activity_epoch=9e9a2a2edcb046bba00df0850244ad36, continuity=continuous, resync_required=false, events=[].

## STARTUP_BACKFILL_WRITER_BOUNDARY
CODE_PATH_PROVED: run_service acquires a persistent RuntimeLease at line 1417. RuntimeLeaseManager.acquire holds its domain OS lock only during the acquire call; the context exits before migration, hydration, materialization and save_snapshot. run_service does not acquire full_analysis.lock around backfill. migrate_legacy_snapshot has its own conditional coordination, but returns before this separate backfill. ensure_module_usages mutates hydrated RAM state; save_snapshot performs the durable write with exact_revision=loaded_metadata.revision+1 and a FileState payload tagged with that revision. save_snapshot holds the snapshot store lock during metadata/state/FileState generation publication, not throughout materialization. No registry write is in this backfill sequence; require_repository_identity reads identity before it. An independent full/scoped writer can own full_analysis.lock and execute concurrently with materialization and can reach the snapshot store. The store lock serializes the final writes and exact_revision prevents silent replacement after another revision has committed. It does not exclude the overlap itself.

Failure contract: a concurrent committed generation makes backfill's exact_revision invalid and raises SnapshotRevisionConflict; run_service startup exception handling aborts service bootstrap and releases/fences the runtime lease. The previous durable generation remains authoritative for this conflict. If backfill commits first, a competing writer may reject its now-stale exact revision. A retry of startup can reload the newer generation; automatic retry behavior was not proved from this path. Source does not prove divergent committed metadata/FileState from the exact-revision conflict. No actual production overlap was observed in this read-only audit.

## STARTUP_CONCURRENT_WRITER_MATRIX

| Writer B | Lock overlap | Shared state | Outcome from source |
|---|---|---|---|
| full analysis | full_analysis.lock held by B, not startup backfill; snapshot lock serializes commit | snapshot generation and revision | CONDITIONAL_CODE_PATH: one exact-revision commit can make other's expected revision stale; no silent overwrite proved |
| scoped analysis | same lock separation | snapshot generation and revision | CONDITIONAL_CODE_PATH: same conflict |
| LIVE queued/direct update_file | server not yet initialized during backfill; another authority for same domain excluded by RuntimeLease acquisition | snapshot generation | PROVED_SAFE for same-domain second LIVE authority; external writer overlap remains separately possible |
| registry-only writer | no registry mutation by backfill shown | identity registry | no shared registry write at this boundary |

## DIRECT_PUBLISH_COMPLETE_CALLERS
Contextor blast-radius and bounded post-discovery textual verification: three production client.publish call sites were found. Static blast radius alone undercounts dynamic method dispatch.
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1150, ContextorFacade.analyze_project, FULL_LEASE_ALREADY_HELD by run_full_analysis_exclusive.
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py:1690, _analyze_single_file_uncoordinated via public analyze_single_file wrapper at 1531-1577, SCOPED_LEASE_ALREADY_HELD.
- C:\Temp\Contextor_Repo\contextor\ui\gui.py:1796, startup publish, FULL_LEASE_ALREADY_HELD with writer_kind=startup_publish.
No additional production client.publish or raw request("publish") call was found in the bounded contextor tree search. Raw LiveStateClient.publish remains callable by an independent client without a lease; an actual unleased production caller was not proved.

## DIRECT_PUBLISH_MUTATION_BOUNDARY
CODE_PATH_PROVED: _dispatch routes publish directly to _execute_publish, unlike update_file which passes through _mutation_guard. _execute_publish holds _mutation_execution_lock, serializing its RAM commit body with _execute_update_file and queued mutations. Production run_service supplies committed_snapshot_reader, so publish uses _execute_committed_publish. That path acquires the server state lock and snapshot store lock, verifies a previously committed exact generation, then updates in-memory state, revision, event and activity sequence. It does not write snapshot metadata/state/FileState or registry. Memory-only fallback has different next-revision behavior and is not the production run_service construction. Client publish is synchronous.

## PUBLISH_EXISTING_GENERATION_VALIDATION
CONTRACT_PROVED: committed publish compares the request candidate to a generation read by locked_committed_snapshot under the snapshot store OS lock. It checks state_id and revision, requires committed revision newer than LIVE RAM revision, and binds the actual committed disk object. A stale/mismatched generation is rejected without a RAM/event commit. It can catch up over more than one revision. Source does not require proof that caller owns full_analysis.lock. A raw unleased publish of a committed generation can therefore be accepted during the durable writer's lease, before that writer sends its own publish; the later owner's publish can then receive non_monotonic_revision. This is a conditional code path, not an observed runtime race or durable corruption.

## CANONICAL_LEASE_OWNERSHIP_MATRIX

| Route | Lease at publish | Server admission | Durable mutation |
|---|---|---|---|
| facade full | full_analysis | no new full lease | prior save_engine_state; publish RAM only |
| facade scoped single-file | scoped_analysis | no new full lease | prior persistence; publish RAM only |
| GUI startup | startup_publish | no new full lease | prior committed generation; publish RAM only |
| raw direct IPC client | UNKNOWN / may have none | no full lease | publish RAM only if exact committed generation accepted |
| direct/queued update_file | live_mutation via _mutation_guard | full lease before updater | updater/persister can write snapshot |

## DEADLOCK_AND_IPC_TIMEOUT_HAZARDS
CONTRACT_PROVED: _get_process_lock returns threading.Lock, and full_analysis.lock is an OS byte lock. Existing full/scoped/startup publish callers hold the canonical lease across a synchronous client.publish request. A universal server-side attempt to acquire that same lease before responding would wait behind the caller that is waiting for the server, a lock cycle. Client request defaults to 30 seconds; scoped publish explicitly uses timeout=5.0. LiveStateClient.request waits for a response and raises TimeoutError, then closes connection; it does not cancel a server operation. Thus a delayed server-side admission could outlive client timeout. Existing safe boundaries proved by source are caller-held lease for confirmed production routes, server mutation_execution_lock, committed snapshot store lock and exact-generation validation. This is source classification only, not a patch design.

## ACTUAL_RACE_EVIDENCE

| RISK_ID | WRITER_A / WRITER_B | ENTRYPOINTS | ACTUAL_LOCK_OWNERSHIP | SHARED_MUTABLE_STATE | POSSIBLE_INTERLEAVING | CURRENT_EXCLUSION_OR_VALIDATION | CLASS | REQUIRED_INVARIANT | EXACT_SOURCE_LINES | TARGETED_REGRESSION_OWNER |
|---|---|---|---|---|---|---|---|---|---|---|
| G-STARTUP-BACKFILL | LIVE startup / full or scoped analysis | run_service / facade analysis | LIVE owns persistent runtime lease; B owns full_analysis.lock; only snapshot write takes store lock | snapshot generation, revision, FileState metadata | both hydrate old generation; one exact commit wins and other conflicts | store lock plus exact_revision | CONDITIONAL_CODE_PATH, overlap source-proved; actual race not observed | one authoritative generation and FileState revision parity; no silent overwrite | runtime.py:1412-1510; store.py:1553-1636,1774-1871 | tests/test_live_state_ipc.py:1299,1417; tests/test_live_state_store.py:483,500 |
| G-DIRECT-PUBLISH | unleased direct client / full or scoped writer | LiveStateClient.publish / _execute_publish | raw client may hold none; owner retains full/scoped lease; server holds mutation lock and store lock during validation | LIVE RAM revision/events; committed snapshot generation | raw client publishes owner's already committed generation before owner does | exact committed-generation validation; monotonic LIVE RAM check | CONDITIONAL_CODE_PATH; no confirmed unleased production caller; no durable overwrite | only committed generation installed; owner publication outcome coherent | ipc.py:1297-1576,2131-2172,2556-2565; facade.py:1150,1690 | tests/test_durable_verified_publish.py:128,169,204,352; tests/test_full_analysis_coordination.py:582 |
| G-PUBLISH-UPDATE | publish / queued or direct update_file | _dispatch / mutation coordinator | update guard obtains canonical full lease; publish has no full lease; both hold mutation_execution_lock for RAM commit body | LIVE RAM revision/events | publish can run before queued job starts or after it completes | same mutation_execution_lock; queued job starts from current revision; committed publish verifies disk | PROVED_SAFE for simultaneous RAM mutation; fairness/order semantics UNKNOWN | no concurrent RAM commit body | ipc.py:1506-1513,1866-1878,2131-2172 | tests/test_live_mutation_coordinator.py:762,909 |

## CONDITIONAL_OR_UNKNOWN_FINDINGS
- DIRECT_EVIDENCE of a missing startup full-analysis lease, but no runtime collision observed. Exact-revision conflict is an availability/retry issue, not proof of corrupted snapshot.
- No production caller of direct publish without a lease was confirmed. External/raw IPC use is possible by API, but runtime reachability in deployed clients is UNKNOWN.
- Whether startup backfill should wait, fail, or be skipped while another writer holds the lease is not decided by this audit.
- Queued update fairness relative to direct publish is UNKNOWN; simultaneous RAM commit is excluded.
- Source proof of startup automatic retry after SnapshotRevisionConflict was not found in inspected path.
- No new contrary evidence reopening approved F1/F2/F3 findings.

## FOCUSED_TEST_OWNERS
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py::test_startup_backfill_preserves_filestate_content_and_revision_parity
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py::test_startup_backfill_failure_leaves_previous_generation_authoritative
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py::test_client_request_timeout_closes_connection
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py::test_two_clients_observe_one_in_ram_state_and_revision
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r2_r11_committed_publish_installs_disk_object_and_isolates_candidate
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r4_r12_r29_durable_catch_up_after_earlier_publish_failure
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r10_committed_publish_respects_cross_process_store_lock
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r30_publish_does_not_persist_another_revision
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py::test_lease_is_held_during_publication
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py::test_scoped_facade_excludes_cross_process_canonical_writer
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py::test_startup_publish_writer_kind_is_accepted
- C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py::test_scoped_single_file_publishes_to_real_live_server_under_writer_lease
- C:\Temp\Contextor_Repo\tests\test_live_mutation_coordinator.py::test_publish_and_queued_update_are_single_writer_serialized
- C:\Temp\Contextor_Repo\tests\test_live_state_store.py::test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite

## MINIMUM_LITERAL_PATCH_BOUNDARIES
Source boundaries only, no implementation design: startup run_service runtime.py:1412-1512 around authority acquisition, backfill materialization and exact save; full/scoped lease owner full_analysis_lease.py:410-610; committed publish admission/commit ipc.py:1297-1576 and _dispatch ipc.py:2131-2172; confirmed caller-held lease boundaries facade.py:1150,1531-1577,1690 and gui.py:1745-1820. Any literal change must preserve existing committed-generation validation and avoid reacquiring a non-reentrant full-analysis lease from the serving request for an already-leased synchronous caller.

## RESTART_REQUIRED
NONE for this read-only task. Any future production patch to runtime.py/ipc.py would require serving-process reload verification; no restart performed.

## COMPLETE RELEVANT SOURCE FRAGMENTS
The following are literal current workspace excerpts after complete Contextor symbol/range retrieval and workspace_sync=verified. Contextor retrieval: run_service 1329-1820 via get_source_range; _dispatch 2131-2377, _execute_publish 1506-1576, _execute_committed_publish 1297-1504, _execute_update_file 1866-2129, _serve_requests 1226-1295 via complete retrieval; RuntimeLeaseManager.acquire 1363-1441, _DomainFileLock 757-834, _LeaseEmissionLock 840-856, acquire_full_analysis 410-588, release_full_analysis 591-610, save_snapshot 1507-1918 and migrate_legacy_snapshot 2419-2474 via complete retrieval. No preview was treated as full.

### C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py : 1412-1510

```python
1412:         manager = RuntimeLeaseManager(
1413:             domain,
1414:             liveness_verifier=AuthorityLivenessVerifier(domain),
1415:             authority_event_emitter=authority_emitter.emit,
1416:         )
1417:         lease = manager.acquire()
1418:         if desktop_instance_id is not None:
1419:             if owner_pid is None or desktop_process_start_identity is None:
1420:                 raise RuntimeLeaseError("Desktop claim process identity is required")
1421:             desktop_claim = manager.claim_desktop(
1422:                 lease,
1423:                 desktop_instance_id,
1424:                 ProcessIdentity(owner_pid, desktop_process_start_identity),
1425:             )
1426:         startup_timing_started = time.monotonic()
1427:         startup_timings_ms: dict[str, float] = {}
1428:         materialization_required = False
1429:
1430:         step_started = time.monotonic()
1431:         cache = migrate_legacy_snapshot(root)
1432:         startup_timings_ms["migrate_legacy_snapshot_ms"] = round(
1433:             (time.monotonic() - step_started) * 1000.0,
1434:             3,
1435:         )
1436:         step_started = time.monotonic()
1437:         loaded = load_snapshot(
1438:             cache,
1439:             expected_repo_id=identity.repo_id,
1440:             expected_root_path=identity.root_path,
1441:         )
1442:         startup_timings_ms["load_snapshot_ms"] = round(
1443:             (time.monotonic() - step_started) * 1000.0,
1444:             3,
1445:         )
1446:         state = loaded[0] if loaded else None
1447:         if state is not None:
1448:             step_started = time.monotonic()
1449:             from contextor.core.analysis.incremental.materialization import (
1450:                 ensure_module_usages,
1451:                 module_usages_require_materialization,
1452:             )
1453:             startup_timings_ms["materialization_import_ms"] = round(
1454:                 (time.monotonic() - step_started) * 1000.0,
1455:                 3,
1456:             )
1457:
1458:             step_started = time.monotonic()
1459:             materialization_required = module_usages_require_materialization(state)
1460:             startup_timings_ms[
1461:                 "module_usages_require_materialization_ms"
1462:             ] = round(
1463:                 (time.monotonic() - step_started) * 1000.0,
1464:                 3,
1465:             )
1466:
1467:             if materialization_required:
1468:                 loaded_metadata = loaded[1]
1469:                 step_started = time.monotonic()
1470:                 from contextor.core.analysis.state_manager import FileStateManager
1471:                 startup_timings_ms["file_state_manager_import_ms"] = round(
1472:                     (time.monotonic() - step_started) * 1000.0,
1473:                     3,
1474:                 )
1475:
1476:                 step_started = time.monotonic()
1477:                 file_state_manager = FileStateManager(str(cache))
1478:                 startup_timings_ms["file_state_manager_load_ms"] = round(
1479:                     (time.monotonic() - step_started) * 1000.0,
1480:                     3,
1481:                 )
1482:                 step_started = time.monotonic()
1483:                 ensure_module_usages(state)
1484:                 startup_timings_ms["ensure_module_usages_ms"] = round(
1485:                     (time.monotonic() - step_started) * 1000.0,
1486:                     3,
1487:                 )
1488:                 target_revision = loaded_metadata.revision + 1
1489:                 step_started = time.monotonic()
1490:                 file_state_payload = file_state_manager.build_payload(
1491:                     loaded_metadata.state_id,
1492:                     target_revision,
1493:                 )
1494:                 startup_timings_ms["file_state_build_payload_ms"] = round(
1495:                     (time.monotonic() - step_started) * 1000.0,
1496:                     3,
1497:                 )
1498:                 step_started = time.monotonic()
1499:                 save_snapshot(
1500:                     state,
1501:                     cache,
1502:                     loaded_metadata.state_id,
1503:                     writer="live-service-symbol-calls-backfill",
1504:                     repo_id=identity.repo_id,
1505:                     root_path=identity.root_path,
1506:                     exact_revision=target_revision,
1507:                     file_state_payload=file_state_payload,
1508:                 )
1509:                 startup_timings_ms["backfill_save_snapshot_ms"] = round(
1510:                     (time.monotonic() - step_started) * 1000.0,
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py : 1532-1554

```python
1532:         }
1533:         step_started = time.monotonic()
1534:         server = CanonicalLiveServer(
1535:             state,
1536:             revision=revision,
1537:             updater=_repository_updater(root, adapter_holder),
1538:             persister=_repository_persister(
1539:                 root,
1540:                 adapter_holder,
1541:                 previous_state=state,
1542:             ),
1543:             committed_snapshot_reader=lambda: locked_committed_snapshot(
1544:                 cache,
1545:                 expected_repo_id=identity.repo_id,
1546:                 expected_root_path=identity.root_path,
1547:             ),
1548:             canonical_query_handler=(
1549:                 _repository_canonical_query_handler
1550:             ),
1551:             mutation_guard=_repository_mutation_guard(root),
1552:             recovery_verification_guard=_repository_recovery_verification_guard(root),
1553:             repository_identity_reader=lambda: read_repository_identity(root),
1554:             authority_identity=authority_identity,
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py : 1720-1753

```python
1720:
1721:             threading.Thread(
1722:                 target=_owner_watchdog,
1723:                 name=f"contextor-live-watchdog-{owner_pid}",
1724:                 daemon=True,
1725:             ).start()
1726:         server_thread.join()
1727:         _raise_if_service_terminated("service lifetime")
1728:     except Exception as exc:
1729:         if authority_emitter is not None:
1730:             try:
1731:                 authority_emitter.emit(
1732:                     "RUNTIME_AUTHORITY_BOOTSTRAP_FAIL",
1733:                     source="runtime",
1734:                     service_instance_id=getattr(lease, "service_instance_id", None),
1735:                     lease_generation=getattr(lease, "lease_generation", None),
1736:                     status="FAILED",
1737:                     decision="FAIL_CLOSED",
1738:                     reason="authority bootstrap failed",
1739:                     error=str(exc),
1740:                 )
1741:             except Exception:
1742:                 pass
1743:         raise
1744:     finally:
1745:         if authority_emitter is not None:
1746:             authority_emitter.detach_live_sink()
1747:         mutation_worker_drained = True
1748:         if server is not None:
1749:             mutation_worker_drained = server.close(mutation_join_timeout=30.0)
1750:         if server_thread is not None and server_thread.is_alive():
1751:             server_thread.join(timeout=1.0)
1752:         if lease is not None and mutation_worker_drained:
1753:             if published_endpoint is not None:
```

### C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\materialization.py : 49-118

```python
49: def module_usages_require_materialization(state: RepositoryAnalysisState) -> bool:
50:     """Return whether a missing or legacy usage slice needs canonical extraction."""
51:     usages = getattr(state, "module_usages", None)
52:     if not isinstance(usages, dict):
53:         return bool(getattr(state, "modules", {}))
54:     return any(
55:         module_name not in usages
56:         or not bool(
57:             vars(usages[module_name]).get(
58:                 "symbol_calls_materialized",
59:                 False,
60:             )
61:         )
62:         or not bool(
63:             vars(usages[module_name]).get(
64:                 "reference_evidence_materialized",
65:                 False,
66:             )
67:         )
68:         for module_name in getattr(state, "modules", {})
69:     )
70:
71:
72: def ensure_module_usages(state: RepositoryAnalysisState) -> None:
73:     """
74:     Initializes state.module_usages for pre-existing state.modules if missing or legacy.
75:     Source-backed legacy reconstruction: only missing or unmaterialized modules read source from disk.
76:     """
77:     if not hasattr(state, "module_usages") or state.module_usages is None:
78:         state.module_usages = {}
79:
80:     missing_modules = set(state.modules.keys()) - set(state.module_usages.keys())
81:     legacy_usage_modules = {
82:         module_name
83:         for module_name, facts in state.module_usages.items()
84:         if module_name in state.modules
85:         and (
86:             not bool(
87:                 vars(facts).get(
88:                     "symbol_calls_materialized",
89:                     False,
90:                 )
91:             )
92:             or not bool(
93:                 vars(facts).get(
94:                     "reference_evidence_materialized",
95:                     False,
96:                 )
97:             )
98:         )
99:     }
100:     modules_to_materialize = missing_modules | legacy_usage_modules
101:     if modules_to_materialize:
102:         from contextor.core.reference.engine import extract_module_usage_facts
103:
104:         for mod_path in modules_to_materialize:
105:             mod = state.modules[mod_path]
106:             mod_abs = getattr(mod, "absolute_path", None) or getattr(mod, "path", None)
107:             source_text = None
108:             if mod_abs and Path(mod_abs).exists():
109:                 try:
110:                     source_text = Path(mod_abs).read_text(encoding="utf-8")
111:                 except OSError:
112:                     source_text = None
113:             imports = getattr(mod, "imports", [])
114:             state.module_usages[mod_path] = extract_module_usage_facts(
115:                 mod_path,
116:                 source_text,
117:                 imports=imports,
118:             )
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\runtime_lease.py : 1363-1441

```python
1363:     def acquire(self) -> RuntimeLease:
1364:         self._emit_authority(
1365:             "RUNTIME_LEASE_ACQUIRE",
1366:             decision="REQUEST",
1367:             status="REQUESTED",
1368:             reason="authority lease acquisition requested",
1369:         )
1370:         while True:
1371:             with self._lock():
1372:                 record = self._read_generation()
1373:                 live = self._read_live_lease()
1374:                 if live is None:
1375:                     if record.status == "active":
1376:                         self._emit_authority(
1377:                             "RUNTIME_LEASE_RECOVERY_REQUIRED",
1378:                             decision="REJECT_TAKEOVER",
1379:                             status="RECOVERY_REQUIRED",
1380:                             reason="active durable authority has no live lease",
1381:                         )
1382:                         raise LeaseRecoveryRequired(
1383:                             "active durable authority has no live lease; recovery is required before takeover"
1384:                         )
1385:                     return self._allocate_next_locked(record)
1386:                 if record.status in {"released", "fenced"}:
1387:                     same_fenced = (
1388:                         record.fenced_service_instance_id == live.service_instance_id
1389:                         and record.fenced_lease_generation == live.lease_generation
1390:                     )
1391:                     same_released = (
1392:                         record.last_service_instance_id == live.service_instance_id
1393:                         and record.last_lease_generation == live.lease_generation
1394:                     )
1395:                     same_identity = (
1396:                         record.service_pid == live.service_pid
1397:                         and record.process_start_identity == live.process_start_identity
1398:                         and record.endpoint_fingerprint == live.endpoint_fingerprint
1399:                     )
1400:                     if not (same_fenced or same_released) or not same_identity:
1401:                         raise ForeignLeaseError("fenced/released live lease does not match durable record")
1402:                     self._remove_desktop_claim_if_owner(live)
1403:                     self._remove_live_lease()
1404:                     return self._allocate_next_locked(record)
1405:                 self._validate_live_record_parity(record, live)
1406:                 observed_record = record
1407:                 observed_live = live
1408:
1409:             evidence = self.liveness_verifier.verify(observed_live)
1410:
1411:             with self._lock():
1412:                 current_record = self._read_generation()
1413:                 current_live = self._read_live_lease()
1414:                 if current_record != observed_record or current_live != observed_live:
1415:                     continue
1416:                 if evidence.status is LivenessStatus.LIVE:
1417:                     self._emit_authority(
1418:                         "RUNTIME_LEASE_TAKEOVER_REJECT",
1419:                         service_instance_id=observed_live.service_instance_id,
1420:                         lease_generation=observed_live.lease_generation,
1421:                         process_id=observed_live.service_pid,
1422:                         decision="REJECT_LIVE",
1423:                         status="LIVE",
1424:                         reason=evidence.reason,
1425:                     )
1426:                     raise LeaseAlreadyHeld(evidence.reason)
1427:                 if not evidence.confirmed_stale:
1428:                     self._emit_authority(
1429:                         "RUNTIME_LEASE_TAKEOVER_REJECT",
1430:                         service_instance_id=observed_live.service_instance_id,
1431:                         lease_generation=observed_live.lease_generation,
1432:                         process_id=observed_live.service_pid,
1433:                         decision="REJECT_AMBIGUOUS",
1434:                         status=evidence.status.value.upper(),
1435:                         reason=evidence.reason,
1436:                     )
1437:                     raise LeaseLivenessUnknown(
1438:                         f"authority takeover rejected: {evidence.status.value}: {evidence.reason}"
1439:                     )
1440:                 fenced = self._fence_stale_lease(current_record, current_live)
1441:                 return self._allocate_next_locked(fenced)
```

### C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py : 80-88

```python
80: def _get_process_lock(
81:     repo_key_str: str,
82: ) -> threading.Lock:
83:     with _PROCESS_LOCKS_GUARD:
84:         lock = _PROCESS_LOCKS.get(repo_key_str)
85:         if lock is None:
86:             lock = threading.Lock()
87:             _PROCESS_LOCKS[repo_key_str] = lock
88:         return lock
```

### C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py : 410-445

```python
410: def acquire_full_analysis(
411:     repo_path: str | Path,
412:     *,
413:     owner: str = "desktop_analysis",
414:     writer_kind: str = "full_analysis",
415:     timeout: float | None = None,
416:     poll_interval: float = 0.25,
417:     is_cancelled: Callable[[], bool] | None = None,
418:     log: Callable[[str], None] | None = None,
419:     admission_trace_fields: Mapping[str, Any] | None = None,
420: ) -> FullAnalysisLease:
421:     """
422:     Acquire exclusive single-writer lease for full repository analysis.
423:     Blocks if another process or thread holds the lease until released,
424:     timed out, or cancelled.
425:     """
426:     if writer_kind not in {
427:         "full_analysis",
428:         "live_mutation",
429:         "startup_publish",
430:         "local_incremental",
431:         "scoped_analysis",
432:     }:
433:         raise ValueError(
434:             "writer_kind must be 'full_analysis', 'live_mutation', "
435:             "'startup_publish', 'local_incremental', or 'scoped_analysis'"
436:         )
437:
438:     lock_file, key, repo_id = _resolve_lock_path(repo_path)
439:     proc_lock = _get_process_lock(key)
440:
441:     start_time = time.monotonic()
442:     deadline = (
443:         start_time + timeout
444:         if timeout is not None
445:         else None
```

### C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py : 591-610

```python
591: def release_full_analysis(
592:     lease: FullAnalysisLease,
593: ) -> None:
594:     """Release the full analysis lease."""
595:     if not isinstance(
596:         lease,
597:         FullAnalysisLease,
598:     ):
599:         return
600:
601:     try:
602:         _unlock_fd(lease.lock_fd)
603:     finally:
604:         proc_lock = _get_process_lock(
605:             lease.repo_key
606:         )
607:         try:
608:             proc_lock.release()
609:         except RuntimeError:
610:             pass
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py : 1297-1350

```python
1297:     def _execute_committed_publish(
1298:         self,
1299:         request: dict[str, Any],
1300:     ) -> dict[str, Any]:
1301:         """Install only a committed durable snapshot generation."""
1302:         with self._lock:
1303:             previous_revision = self._revision
1304:             candidate = request.get("state")
1305:
1306:             try:
1307:                 candidate_revision = _extract_state_revision(candidate)
1308:             except ValueError:
1309:                 return {
1310:                     "status": "error",
1311:                     "error": "invalid_canonical_revision",
1312:                     "revision": previous_revision,
1313:                 }
1314:
1315:             candidate_state_id = getattr(
1316:                 candidate, "state_id", None
1317:             )
1318:
1319:             if (
1320:                 candidate_revision is None
1321:                 or not isinstance(candidate_state_id, str)
1322:                 or not candidate_state_id
1323:             ):
1324:                 return {
1325:                     "status": "error",
1326:                     "error": "committed_publish_identity_required",
1327:                     "revision": previous_revision,
1328:                 }
1329:
1330:             origin = request.get("origin", "unknown")
1331:             if not isinstance(origin, str):
1332:                 return {
1333:                     "status": "error",
1334:                     "error": "invalid_publish_origin",
1335:                     "revision": previous_revision,
1336:                 }
1337:
1338:             trace_op = request.get("trace_op")
1339:             if trace_op is not None and not isinstance(
1340:                 trace_op, str
1341:             ):
1342:                 return {
1343:                     "status": "error",
1344:                     "error": "invalid_publish_trace_op",
1345:                     "revision": previous_revision,
1346:                 }
1347:
1348:             committed = False
1349:             committed_revision = None
1350:             committed_seq = None
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py : 1390-1504

```python
1390:                             "resync_required": True,
1391:                         }
1392:
1393:                     if (
1394:                         candidate_revision != committed_revision
1395:                         or candidate_state_id != committed_state_id
1396:                     ):
1397:                         return {
1398:                             "status": "error",
1399:                             "error": "committed_publish_generation_mismatch",
1400:                             "revision": previous_revision,
1401:                             "candidate_revision": candidate_revision,
1402:                             "committed_revision": committed_revision,
1403:                             "resync_required": True,
1404:                         }
1405:
1406:                     if committed_revision <= previous_revision:
1407:                         return {
1408:                             "status": "error",
1409:                             "error": "non_monotonic_canonical_revision",
1410:                             "revision": previous_revision,
1411:                             "candidate_revision": candidate_revision,
1412:                             "expected_revision": previous_revision + 1,
1413:                         }
1414:
1415:                     next_seq = self._activity_seq + 1
1416:                     source = origin or "unknown"
1417:
1418:                     event = {
1419:                         "seq": next_seq,
1420:                         "timestamp": datetime.now(
1421:                             timezone.utc
1422:                         ).isoformat(),
1423:                         "category": "LIVE_STATE",
1424:                         "operation": "publish",
1425:                         "source": source,
1426:                         "origin": source,
1427:                         "canonical_revision": committed_revision,
1428:                         "revision": committed_revision,
1429:                         "status": "PUBLISHED",
1430:                     }
1431:
1432:                     if trace_op is not None:
1433:                         event["trace_op"] = trace_op
1434:
1435:                     next_events = (
1436:                         self._events + [event]
1437:                     )[-self._retention:]
1438:
1439:                     _mark_live_state_provenance(committed_state)
1440:
1441:                     # COMMIT BOUNDARY
1442:                     #
1443:                     # All event construction and validation
1444:                     # is complete.
1445:                     #
1446:                     # The store lock and server mutation lock
1447:                     # are both held at this point.
1448:
1449:                     self._state = committed_state
1450:                     self._revision = committed_revision
1451:                     self._events = next_events
1452:                     self._activity_seq = next_seq
1453:
1454:                     committed_seq = next_seq
1455:                     committed = True
1456:
1457:             except Exception as exc:
1458:                 if committed:
1459:                     # The generation is already installed.
1460:                     # Never report a rejected publication.
1461:                     try:
1462:                         _safe_trace_event(
1463:                             "LIVE",
1464:                             "COMMITTED_PUBLISH_RELEASE_FAIL",
1465:                             rev=committed_revision,
1466:                             seq=committed_seq,
1467:                             err=exc,
1468:                         )
1469:                     except Exception:
1470:                         pass
1471:
1472:                     return {
1473:                         "status": "ok",
1474:                         "revision": committed_revision,
1475:                         "seq": committed_seq,
1476:                         "source": "committed_snapshot",
1477:                         "resync_required": True,
1478:                         "warning": "snapshot_lock_release_unverified",
1479:                     }
1480:
1481:                 try:
1482:                     _safe_trace_event(
1483:                         "LIVE",
1484:                         "COMMITTED_PUBLISH_FAIL",
1485:                         rev=previous_revision,
1486:                         status="committed_publish_failed",
1487:                         err=exc,
1488:                     )
1489:                 except Exception:
1490:                     pass
1491:
1492:                 return {
1493:                     "status": "error",
1494:                     "error": "committed_publish_failed",
1495:                     "revision": previous_revision,
1496:                     "resync_required": True,
1497:                 }
1498:
1499:             return {
1500:                 "status": "ok",
1501:                 "revision": committed_revision,
1502:                 "seq": committed_seq,
1503:                 "source": "committed_snapshot",
1504:             }
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py : 1506-1576

```python
1506:     def _execute_publish(self, request: dict[str, Any]) -> dict[str, Any]:
1507:         if self._mutation_coordinator.recovery_verification_active():
1508:             return {
1509:                 "status": "error",
1510:                 "error": "recovery_verification_in_progress",
1511:                 "resync_required": True,
1512:             }
1513:         with self._mutation_execution_lock:
1514:             if self._mutation_coordinator.recovery_verification_active():
1515:                 return {
1516:                     "status": "error",
1517:                     "error": "recovery_verification_in_progress",
1518:                     "resync_required": True,
1519:                 }
1520:             if self._committed_snapshot_reader is not None:
1521:                 return self._execute_committed_publish(request)
1522:             with self._lock:
1523:                 previous_revision = self._revision
1524:                 trace_op = _safe_trace_op(request, "p")
1525:                 if trace_op is not None:
1526:                     request = {**request, "trace_op": trace_op}
1527:                 _safe_trace_event("LIVE", "PUBLISH_RECEIVED", op=trace_op, rev=previous_revision)
1528:                 state = request.get("state")
1529:                 try:
1530:                     state_rev = _extract_state_revision(state)
1531:                 except ValueError as exc:
1532:                     _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="invalid_canonical_revision", candidate_rev=_raw_state_revision(state))
1533:                     return {
1534:                         "status": "error",
1535:                         "error": "invalid_canonical_revision",
1536:                         "revision": self._revision,
1537:                         "candidate_revision": _raw_state_revision(state),
1538:                     }
1539:                 expected_revision = self._revision + 1
1540:
1541:                 if state_rev is not None:
1542:                     if state_rev < expected_revision:
1543:                         _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="non_monotonic_canonical_revision", candidate_rev=state_rev)
1544:                         return {
1545:                             "status": "error",
1546:                             "error": "non_monotonic_canonical_revision",
1547:                             "revision": self._revision,
1548:                             "candidate_revision": state_rev,
1549:                             "expected_revision": expected_revision,
1550:                         }
1551:                     if state_rev > expected_revision:
1552:                         _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="canonical_revision_discontinuity", candidate_rev=state_rev)
1553:                         return {
1554:                             "status": "error",
1555:                             "error": "canonical_revision_discontinuity",
1556:                             "revision": self._revision,
1557:                             "candidate_revision": state_rev,
1558:                             "expected_revision": expected_revision,
1559:                         }
1560:                 else:
1561:                     if not _bind_state_revision(state, expected_revision):
1562:                         _safe_trace_event("LIVE", "PUBLISH_FAIL", op=trace_op, rev=previous_revision, status="canonical_revision_binding_failed", candidate_rev=None)
1563:                         return {
1564:                             "status": "error",
1565:                             "error": "canonical_revision_binding_failed",
1566:                             "revision": self._revision,
1567:                             "candidate_revision": None,
1568:                         }
1569:                     state_rev = expected_revision
1570:
1571:                 _mark_live_state_provenance(state)
1572:                 self._state = state
1573:                 self._revision = state_rev
1574:                 evt = self._record_event("publish", request, category="LIVE_STATE")
1575:                 _safe_trace_event("LIVE", "CANONICAL_PUBLISH", op=trace_op, rev_before=previous_revision, rev_after=self._revision, seq=evt["seq"], origin=request.get("origin"))
1576:                 return {"status": "ok", "revision": self._revision, "seq": evt["seq"]}
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py : 1861-1884

```python
1861:         if self._mutation_guard is None:
1862:             return self._execute_update_file(request, allow_recovery_fence=True)
1863:         with self._mutation_guard(request, self._stop):
1864:             return self._execute_update_file(request, allow_recovery_fence=True)
1865:
1866:     def _execute_update_file(
1867:         self, request: dict[str, Any], *, allow_recovery_fence: bool = False
1868:     ) -> dict[str, Any]:
1869:         if (
1870:             not allow_recovery_fence
1871:             and self._mutation_coordinator.recovery_verification_active()
1872:         ):
1873:             return {
1874:                 "status": "error",
1875:                 "error": "recovery_verification_in_progress",
1876:                 "accepted": False,
1877:             }
1878:         with self._mutation_execution_lock:
1879:             if (
1880:                 not allow_recovery_fence
1881:                 and self._mutation_coordinator.recovery_verification_active()
1882:             ):
1883:                 return {
1884:                     "status": "error",
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py : 2150-2176

```python
2150:             return self._dispatch_desktop_claim_status()
2151:         if operation == "claim_desktop":
2152:             return self._dispatch_claim_desktop(request)
2153:         if operation == "release_desktop_claim":
2154:             return self._dispatch_release_desktop_claim(request)
2155:         if operation == "submit_update_file":
2156:             return self._mutation_coordinator.submit(request)
2157:         if operation == "mutation_status":
2158:             return self._mutation_coordinator.status(request.get("job_id"))
2159:         if operation == "verify_recovery":
2160:             return self._execute_recovery_verification(request)
2161:         if operation == "complete_recovery_verification":
2162:             return self._finish_recovery_verification(request, cancelled=False)
2163:         if operation == "cancel_recovery_verification":
2164:             return self._finish_recovery_verification(request, cancelled=True)
2165:         if operation == "update_file":
2166:             if self._mutation_guard is None:
2167:                 return self._execute_update_file(request)
2168:             with self._mutation_guard(request, self._stop):
2169:                 return self._execute_update_file(request)
2170:         if operation == "publish":
2171:             return self._execute_publish(request)
2172:
2173:         with self._lock:
2174:             if operation == "canonical_query":
2175:                 if self._state is None:
2176:                     return {
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py : 2459-2494

```python
2459:     def request(
2460:         self, operation: str, *, timeout: float = 30.0, **payload: Any
2461:     ) -> dict[str, Any]:
2462:         started = time.monotonic()
2463:         try:
2464:             connection = Client(
2465:                 self.endpoint.address,
2466:                 family="AF_INET",
2467:                 authkey=self.endpoint.authkey,
2468:             )
2469:             try:
2470:                 connection.send({"operation": operation, **payload})
2471:                 import multiprocessing.connection as mpc
2472:                 ready = mpc.wait([connection], timeout=timeout)
2473:                 if not ready:
2474:                     raise TimeoutError(
2475:                         "Canonical LIVE service did not respond within "
2476:                         f"{timeout:g}s for op={operation}"
2477:                     )
2478:                 response = connection.recv()
2479:             finally:
2480:                 connection.close()
2481:         except (OSError, EOFError, ConnectionError, TimeoutError) as exc:
2482:             _safe_trace_event(
2483:                 "LIVE", "LIVE_IPC_FAILURE",
2484:                 side="client", operation_or_request_type=operation,
2485:                 host=getattr(self.endpoint, "host", self.endpoint.address[0]),
2486:                 port=getattr(self.endpoint, "port", self.endpoint.address[1]),
2487:                 exception_class=type(exc).__name__, errno=getattr(exc, "errno", None),
2488:                 winerror=getattr(exc, "winerror", None), error=str(exc)[:500],
2489:                 elapsed_ms=(time.monotonic() - started) * 1000.0,
2490:             )
2491:             raise
2492:         if not isinstance(response, dict):
2493:             raise RuntimeError("Canonical LIVE service returned an invalid response.")
2494:         return response
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py : 2556-2565

```python
2556:     def publish(
2557:         self,
2558:         state: Any,
2559:         *,
2560:         origin: str = "unknown",
2561:         timeout: float = 30.0,
2562:     ) -> dict[str, Any]:
2563:         return self.request(
2564:             "publish", timeout=timeout, state=state, origin=origin
2565:         )
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1553-1575

```python
1553:     state_file, meta_file, lock_file = _paths(cache_dir)
1554:     state_file.parent.mkdir(parents=True, exist_ok=True)
1555:     lock_fd = _acquire_lock(lock_file)
1556:     token = uuid.uuid4().hex
1557:     state_tmp = state_file.with_name(f".{state_file.name}.{token}.tmp")
1558:     meta_tmp = meta_file.with_name(f".{meta_file.name}.{token}.tmp")
1559:     generation_state = state_tmp
1560:     generation_file_state: Path | None = None
1561:     generation_lineage_manifest: Path | None = None
1562:     generation_lineage_chunks: list[Path] = []
1563:     reusable_lineage_sources: dict[str, Any] = {}
1564:     committed = False
1565:     migration_file_state_target = state_file.parent / "file_state.json"
1566:     migration_file_state_temp = state_file.parent / f".file_state.{token}.tmp"
1567:     migration_file_state_created = False
1568:
1569:     try:
1570:         current = read_metadata(cache_dir)
1571:         if migration_only_if_absent and current is not None:
1572:             return current
1573:
1574:         normalized_root = (
1575:             str(Path(root_path).expanduser().resolve())
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1601-1636

```python
1601:         if exact_revision is not None:
1602:             if (
1603:                 isinstance(exact_revision, bool)
1604:                 or not isinstance(exact_revision, int)
1605:                 or exact_revision < 0
1606:             ):
1607:                 raise ValueError(
1608:                     "exact_revision must be a non-negative integer."
1609:                 )
1610:
1611:             current_revision = (
1612:                 current.revision
1613:                 if current is not None
1614:                 else None
1615:             )
1616:
1617:             if (
1618:                 current_revision is None
1619:                 and exact_revision != 1
1620:             ):
1621:                 raise SnapshotRevisionConflict(
1622:                     None,
1623:                     exact_revision,
1624:                 )
1625:
1626:             if (
1627:                 current_revision is not None
1628:                 and exact_revision
1629:                 != current_revision + 1
1630:             ):
1631:                 raise SnapshotRevisionConflict(
1632:                     current_revision,
1633:                     exact_revision,
1634:                 )
1635:
1636:             next_revision = exact_revision
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1774-1826

```python
1774:         if generation_file_state is not None:
1775:             if (
1776:                 not isinstance(
1777:                     file_state_payload,
1778:                     dict,
1779:                 )
1780:                 or not isinstance(
1781:                     file_state_payload.get(
1782:                         "_meta"
1783:                     ),
1784:                     dict,
1785:                 )
1786:             ):
1787:                 raise ValueError(
1788:                     "file_state_payload must contain a _meta mapping."
1789:                 )
1790:
1791:             payload_meta = file_state_payload[
1792:                 "_meta"
1793:             ]
1794:
1795:             if (
1796:                 payload_meta.get(
1797:                     "state_id",
1798:                     "",
1799:                 )
1800:                 != state_id
1801:             ):
1802:                 raise ValueError(
1803:                     "FileState payload state_id does not match snapshot state_id."
1804:                 )
1805:
1806:             if (
1807:                 payload_meta.get(
1808:                     "revision"
1809:                 )
1810:                 != exact_revision
1811:             ):
1812:                 raise ValueError(
1813:                     "FileState payload revision does not match exact_revision."
1814:                 )
1815:
1816:             with generation_file_state.open(
1817:                 "w",
1818:                 encoding="utf-8",
1819:             ) as stream:
1820:                 json.dump(
1821:                     file_state_payload,
1822:                     stream,
1823:                     indent=2,
1824:                 )
1825:                 stream.flush()
1826:                 os.fsync(
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1840-1875

```python
1840:             )
1841:             stream.flush()
1842:             os.fsync(
1843:                 stream.fileno()
1844:             )
1845:
1846:         if exact_revision is None:
1847:             os.replace(
1848:                 generation_state,
1849:                 state_file,
1850:             )
1851:
1852:         if migration_file_state_source is not None:
1853:             source_file = Path(migration_file_state_source)
1854:             if (
1855:                 source_file.is_file()
1856:                 and not migration_file_state_target.exists()
1857:             ):
1858:                 shutil.copy2(source_file, migration_file_state_temp)
1859:                 with migration_file_state_temp.open("ab") as stream:
1860:                     stream.flush()
1861:                     os.fsync(stream.fileno())
1862:                 os.replace(
1863:                     migration_file_state_temp,
1864:                     migration_file_state_target,
1865:                 )
1866:                 migration_file_state_created = True
1867:
1868:         os.replace(
1869:             meta_tmp,
1870:             meta_file,
1871:         )
1872:
1873:         committed = True
1874:
1875:         return metadata
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 1949-1967

```python
1949: @contextmanager
1950: def locked_committed_snapshot(
1951:     cache_dir: str | Path,
1952:     *,
1953:     expected_repo_id: str,
1954:     expected_root_path: str,
1955: ):
1956:     """Read one durable generation under the snapshot store lock."""
1957:     _, _, lock_file = _paths(cache_dir)
1958:     fd = _acquire_lock(lock_file)
1959:
1960:     try:
1961:         yield load_snapshot(
1962:             cache_dir,
1963:             expected_repo_id=expected_repo_id,
1964:             expected_root_path=expected_root_path,
1965:         )
1966:     finally:
1967:         _release_lock(fd)
```

### C:\Temp\Contextor_Repo\contextor\core\api\facade.py : 1531-1577

```python
1531:     @staticmethod
1532:     def analyze_single_file(
1533:         file_path: str,
1534:         repo_root: str,
1535:         log=None,
1536:         progress_callback=None,
1537:         additional_excludes: list[str] | None = None,
1538:         publication_result: dict[str, Any] | None = None,
1539:     ) -> str:
1540:         if publication_result is not None:
1541:             publication_result.update(
1542:                 status="not_attempted",
1543:                 revision=None,
1544:                 warning=None,
1545:             )
1546:         from contextor.core.analysis.full_analysis_lease import (
1547:             acquire_full_analysis,
1548:             release_full_analysis,
1549:         )
1550:
1551:         root_resolved, target = _resolve_repository_target(
1552:             repo_root,
1553:             file_path,
1554:             target_kind="file",
1555:         )
1556:         if target.suffix.lower() != ".py":
1557:             raise ValueError(
1558:                 f"Selected file is not a Python file: {target}"
1559:             )
1560:
1561:         lease = acquire_full_analysis(
1562:             root_resolved,
1563:             owner="scoped_single_file_analysis",
1564:             writer_kind="scoped_analysis",
1565:             timeout=10.0,
1566:         )
1567:         try:
1568:             return ContextorFacade._analyze_single_file_uncoordinated(
1569:                 file_path,
1570:                 repo_root,
1571:                 log=log,
1572:                 progress_callback=progress_callback,
1573:                 additional_excludes=additional_excludes,
1574:                 publication_result=publication_result,
1575:             )
1576:         finally:
1577:             release_full_analysis(lease)
```

### C:\Temp\Contextor_Repo\contextor\core\api\facade.py : 1139-1157

```python
1139:
1140:                 client = None
1141:                 try:
1142:                     component_started = time.monotonic()
1143:                     try:
1144:                         client = connect(path)
1145:                     finally:
1146:                         connect_ms = (time.monotonic() - component_started) * 1000.0
1147:                     if client is not None:
1148:                         component_started = time.monotonic()
1149:                         try:
1150:                             published = client.publish(state, origin=origin)
1151:                         finally:
1152:                             publish_ms = (time.monotonic() - component_started) * 1000.0
1153:                         component_started = time.monotonic()
1154:                         if (
1155:                             isinstance(published, dict)
1156:                             and published.get("status") == "ok"
1157:                             and published.get("revision") is not None
```

### C:\Temp\Contextor_Repo\contextor\core\api\facade.py : 1681-1700

```python
1681:                 raise ValueError(
1682:                     f"Cannot analyze {file.name}{location}: {update_result.error}"
1683:                 )
1684:             analysis_state = hydrated.engine.state
1685:             modules = analysis_state.modules
1686:             graph = analysis_state.dependency_graph
1687:             cache_hit = True
1688:             if update_result.status == "UPDATED" and hydrated.client is not None:
1689:                 try:
1690:                     published = hydrated.client.publish(
1691:                         analysis_state,
1692:                         origin="scoped_analysis",
1693:                         timeout=5.0,
1694:                     )
1695:                     if isinstance(published, dict) and published.get("status") == "ok":
1696:                         if published.get("resync_required") is True:
1697:                             status = "recovery_required"
1698:                             warning = published.get("warning") or "LIVE recovery verification required."
1699:                         else:
1700:                             status = "success"
```

### C:\Temp\Contextor_Repo\contextor\ui\gui.py : 1763-1808

```python
1763:                     if ContextorGUI._is_selected_live_repository(self, path):
1764:                         if self._live_recovery_incident(path) is None:
1765:                             self._set_live_status("LIVE: shared state attached; watcher active")
1766:                         else:
1767:                             self._set_live_status(
1768:                                 "LIVE: recovery required; incremental updates are deferred."
1769:                             )
1770:                 else:
1771:                     if ContextorGUI._is_selected_live_repository(self, path):
1772:                         self._set_live_status(
1773:                             "LIVE: generation conflict; analysis required"
1774:                         )
1775:                         self._request_full_analysis_recovery(
1776:                             path,
1777:                             "Canonical state identity mismatch.",
1778:                         )
1779:             else:
1780:                 startup_lease = None
1781:                 try:
1782:                     startup_lease = acquire_full_analysis(
1783:                         path,
1784:                         owner="desktop_startup_publish",
1785:                         writer_kind="startup_publish",
1786:                         timeout=0.0,
1787:                         poll_interval=0.01,
1788:                     )
1789:                 except FullAnalysisBusyError:
1790:                     if ContextorGUI._is_selected_live_repository(self, path):
1791:                         self._set_live_status(
1792:                             "LIVE: canonical writer busy; cache publish skipped"
1793:                         )
1794:                 else:
1795:                     try:
1796:                         published = client.publish(
1797:                             state,
1798:                             origin="desktop_analysis",
1799:                         )
1800:                     finally:
1801:                         release_full_analysis(startup_lease)
1802:                     if (
1803:                         isinstance(published, dict)
1804:                         and published.get("resync_required") is True
1805:                     ):
1806:                         outcome = (
1807:                             "accepted" if published.get("status") == "ok"
1808:                             else "rejected"
```

### C:\Temp\Contextor_Repo\contextor\core\live_state\store.py : 2419-2474

```python
2419: def migrate_legacy_snapshot(
2420:     repo_root: str | Path,
2421:     *,
2422:     _lease_held: bool = False,
2423: ) -> Path:
2424:     """Copy a verified path-keyed snapshot into its repo-ID cache directory."""
2425:
2426:     from contextor.core.paths import legacy_repo_cache_dir, repo_cache_dir
2427:     from contextor.core.repository_identity import require_repository_identity
2428:
2429:     root = Path(repo_root).expanduser().resolve()
2430:     identity = require_repository_identity(root)
2431:     target = repo_cache_dir(root)
2432:     if read_metadata(target) is not None:
2433:         return target
2434:
2435:     legacy = legacy_repo_cache_dir(root)
2436:     if legacy == target:
2437:         return target
2438:     loaded = load_snapshot(legacy)
2439:     if loaded is None:
2440:         return target
2441:
2442:     if not _lease_held:
2443:         from contextor.core.analysis.full_analysis_lease import (
2444:             acquire_full_analysis,
2445:             release_full_analysis,
2446:         )
2447:
2448:         lease = acquire_full_analysis(
2449:             root,
2450:             owner="legacy_snapshot_migration",
2451:             writer_kind="full_analysis",
2452:             timeout=10.0,
2453:         )
2454:         try:
2455:             return migrate_legacy_snapshot(
2456:                 root,
2457:                 _lease_held=True,
2458:             )
2459:         finally:
2460:             release_full_analysis(lease)
2461:
2462:     state, metadata = loaded
2463:     save_snapshot(
2464:         state,
2465:         target,
2466:         metadata.state_id,
2467:         writer=f"migration:{metadata.writer}",
2468:         repo_id=identity.repo_id,
2469:         root_path=identity.root_path,
2470:         revision_floor=metadata.revision,
2471:         migration_file_state_source=legacy / "file_state.json",
2472:         migration_only_if_absent=True,
2473:     )
2474:     return target
```

## FINAL_VERDICT
READY_FOR_L32H2G_LITERAL_FIX

This verdict is readiness for auditor-supplied literal work at the source-proved startup overlap and direct-publish admission boundary. It is not a claim that a runtime collision, durable corruption, or an unleased production publish caller was observed. L32H FINAL PASS is not claimed.
