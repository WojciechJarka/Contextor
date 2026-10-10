# L32H2C final test hardening / L32H2D global writer discovery

## FILES_CHANGED_THIS_TASK

- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py` — the sole source/test change.
- `C:\Temp\Contextor_Repo\walkthrough.md` — report only.
- After edit, `git status --short` reported only `M tests/test_mcp_incremental_hydration.py`. No production file changed.

## EXACT_TEST_PATCH

DIRECT_EVIDENCE: The worker now queues `{"role": "first"|"second", "response": ...}` for either return or exception. The two-process test maps responses by role, requires first `UPDATED`, second `ERROR` containing `stale`, no second candidate entry, and snapshot revision 2. Both replacements are the auditor's exact A1/A2. Contextor returned both updated functions complete at lines 110–153 and 411–479 with workspace_sync=verified.

## CROSS_PROCESS_STRICT_RESULT

`& .\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_incremental_hydration.py::test_two_mcp_processes_cannot_enter_local_candidate_concurrently --tb=short` — **1 passed**. This is isolated-test proof of order-independent attribution and stale rejection, not a real-service race observation.

## FOCUSED_AUTHORITY_REGRESSIONS

Four nodes in `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`: `test_local_writer_rejects_untrusted_authority_before_mutation[active]`, `test_local_domain_fence_blocks_live_acquire_until_persistence_finishes`, `test_local_registry_rollback_completes_before_domain_fence_release`, and `test_local_writer_domain_lock_timeout_preserves_state` — **4 passed**. No other tests run. `git diff --check -- tests/test_mcp_incremental_hydration.py` exit 0; Git emitted only its LF/CRLF warning.

## GLOBAL_WRITER_INVENTORY

Contextor caller/blast-radius discovery and literal confirmation show wrapped full analysis entrypoints in `C:\Temp\Contextor_Repo\contextor\cli.py`, `C:\Temp\Contextor_Repo\contextor\core\analysis\profile_runner.py`, `C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py`, `C:\Temp\Contextor_Repo\contextor\mcp_worker.py`, and `C:\Temp\Contextor_Repo\contextor\ui\gui.py`. The wrapper is `run_full_analysis_exclusive`. Other writer paths: GUI startup publish; queued and direct LIVE incremental updates; LIVE startup legacy migration and module-usage backfill; local MCP fallback; facade layer and single-file registry transactions; `contextor.mcp.query_helpers.read_registries`, which uses a write transaction. This is targeted discovery, not an exhaustive repository scan.

## FULL_ANALYSIS_LOCK_CONTRACT

DIRECT_EVIDENCE: `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py` 121–205, 410–603. Acquisition order: process admission lock → OS `canonical_writer.admission.lock` → process full-analysis lock → OS `runtime/full_analysis.lock`. Admission gate is released after the full-analysis lease is acquired. The OS full-analysis lock stays held until `release_full_analysis`. Exact `writer_kind` allowlist: `full_analysis`, `live_mutation`, `startup_publish`; **none** truthfully denotes local incremental writing. Lock acquisition checks owner/OS lease state, timeout and cancellation; it does **not** check LIVE authority.

CODE_PATH_PROVED: `run_full_analysis_exclusive` 606–693 holds full-analysis lock over `ContextorFacade.analyze_project`; facade 1080–1150 calls `save_engine_state` then `connect(path)` and `client.publish`, while `artifact_pipeline.py` 88–104 mutates registry. Thus inspected wrapped production entrypoints hold the lock over registry, snapshot, and canonical handoff. UNKNOWN universal coverage for arbitrary direct calls to `ContextorFacade.analyze_project`, which has no internal full-analysis lock.

## DESKTOP_STARTUP_LOCK_CONTRACT

DIRECT_EVIDENCE: `C:\Temp\Contextor_Repo\contextor\ui\gui.py` 1782–1801 acquires `full_analysis.lock`, `writer_kind="startup_publish"`, `timeout=0.0`, then calls `client.publish` and releases in `finally`; busy writer means cache publish skipped. `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py` 1263–1298 gives queued LIVE mutation the same OS lock with `writer_kind="live_mutation"`. The IPC publish method itself does not acquire this OS lock; caller coordination matters.

## LOCAL_MCP_LOCK_ORDER

DIRECT_EVIDENCE: `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py` 249–389 takes MCP cache RLock → `RuntimeLeaseManager._lock()` domain OS lock → private generation/lease readers → exact baseline validation → candidate registry checkpoint/update and snapshot persistence → rollback or cache publication → domain release → cache release. It never takes `full_analysis.lock`. LIVE acquisition uses the same domain OS lock; local rejects an active or unresolved generation/lease.

## WRITER_OVERLAP_MATRIX

| Writer / absolute source | OS lock, lifetime | Registry / snapshot / LIVE | Local overlap; failure classification |
|---|---|---|---|
| Wrapped full analysis: `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py`, `C:\Temp\Contextor_Repo\contextor\core\api\facade.py` | admission → full_analysis; full_analysis across facade | artifact registry, snapshot, possible LIVE publish | **PROVED_OVERLAP** at outer-lock level with local domain section; inner resource locks serialize individual writes. Concrete runtime interleaving not observed. |
| Desktop startup publish: `C:\Temp\Contextor_Repo\contextor\ui\gui.py` | admission → full_analysis during publish | canonical handoff, server committed snapshot reader | **CONDITIONAL** overlap with local: distinct outer locks, inner snapshot reader may serialize. |
| Queued LIVE update: `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py`, `C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py` | full_analysis during updater/persister; LIVE lease previously acquired via domain | registry, snapshot, canonical RAM | **PROVED_EXCLUDED** from admitted local by active LIVE lease. |
| Direct LIVE IPC `update_file`: `C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py` 1866–2065 | server mutation/state locks; no queued mutation guard | configured updater/persister, active production lease | **CONDITIONAL** bypass of full-analysis guard; local rejects active LIVE lease. Direct caller exists in `LiveStateClient.update_file` and MCP tool. |
| Local MCP: `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py` | cache → domain across candidate/persist/rollback | registry checkpoint/transaction, exact snapshot, no LIVE lease | **PROVED_EXCLUDED** from another local writer using same fence; **PROVED_OVERLAP** in lock-domain terms with full analysis. |
| LIVE startup migration/backfill: `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py` 1412–1499, `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py` 2370–2409 | lease acquired through domain; no outer full/domain OS lock visibly held during write | legacy snapshot migration and backfill snapshot | **PROVED_EXCLUDED** from correctly admitted local by active/reserved LIVE generation. |
| Facade report and MCP registry read: `C:\Temp\Contextor_Repo\contextor\core\api\facade.py` 1428/1674, `C:\Temp\Contextor_Repo\contextor\mcp\query_helpers.py` 81–96 | registry's own lock; no proved domain/full-analysis wrapper | registry JSON physically rewritten by successful transaction | **CONDITIONAL** report reachability; **PROVED_OVERLAP** at outer-lock level for independent read_registries call; own registry lock serializes each transaction. |

## REGISTRY_AND_SNAPSHOT_EXCLUSION

CODE_PATH_PROVED: The local domain OS lock and full-analysis OS lock are different. Full analysis can reach a registry transaction and `save_engine_state` while local holds domain. Registry's transaction lock and snapshot store lock/exact revision serialize their own commits, not the complete cross-resource registry+snapshot+canonical transaction. `PersistentIdentityRegistry.transaction` at `C:\Temp\Contextor_Repo\contextor\core\reporting_engine\persistent_registry.py` 199–263 writes temp JSON, transaction journal and replaces files on successful exit; `read_registries` is therefore a physical writer. No real-runtime corruption race was induced.

## LOCK_TIMEOUT_AND_RECOVERY

DIRECT_EVIDENCE: Coordinator checks cancellation and timeout while acquiring process and OS locks; OS lock ownership is authoritative, metadata diagnostic. A dead process releases the OS lock; next acquirer can log orphan recovery. Unknown owner waits and times out. Wrapper releases in `finally`; GUI startup timeout=0 skips busy publish. Domain lock default acquisition timeout is 10 seconds. UNKNOWN whether 10 seconds fits actual production update durations: none measured here. CODE_PATH_PROVED blocking hazard for concurrent LIVE acquisition when local holds domain longer than timeout. Separate registry and snapshot commit boundaries mean interrupted publication can leave temporary generation divergence; exact snapshot revision guards snapshot conflict, not every earlier registry write.

## DEADLOCK_RISK

CODE_PATH_PROVED: wrapped full analysis holds `full_analysis.lock`, then `ContextorFacade.analyze_project` calls `connect(path)` after snapshot; connection reads lease/generation under domain lock. Thus an existing path has full_analysis → domain. Current local is cache → domain, with no full-analysis acquisition, so that specific two-lock cycle is absent. A future domain → full_analysis nested acquisition would invert this observed order and risk deadlock; no such code was added or proposed. No MCP cache RLock acquisition appears in inspected full-analysis path; dynamic uses are UNKNOWN. Acquiring full-analysis lock does not substitute for a LIVE authority check. No single safe global order can be certified for all current writers from existing code.

## EXACT_SOURCE_HANDOFF

Literal decisive source, obtained as complete Contextor implementations or exact requested ranges:

```python
# contextor/core/analysis/full_analysis_coordinator.py:425
if writer_kind not in {"full_analysis", "live_mutation", "startup_publish"}:
    raise ValueError(
        "writer_kind must be 'full_analysis', 'live_mutation', or 'startup_publish'"
    )

# contextor/core/api/facade.py:1108, 1135-1149
meta = save_engine_state(
    state, cache_dir, datestamp, writer=writer,
    repo_id=registry.repo_id, root_path=path,
    exact_revision=target_revision, file_state_payload=file_state_payload,
)
if meta is not None:
    from contextor.core.live_state import connect
    ...
    client = connect(path)
    if client is not None:
        published = client.publish(state, origin=origin)

# contextor/core/live_state/ipc.py:2158-2169
if operation == "submit_update_file":
    return self._mutation_coordinator.submit(request)
...
if operation == "update_file":
    return self._execute_update_file(request)

# contextor/core/live_state/ipc.py:1856-1864
if self._mutation_guard is None:
    return self._execute_update_file(request, allow_recovery_fence=True)
with self._mutation_guard(request, self._stop):
    return self._execute_update_file(request, allow_recovery_fence=True)

# contextor/mcp/tools/update_file.py:254-272
with mcp_runtime._engine_cache_transaction(root) as root_key:
    ...
    with lease_manager._lock():
        generation = lease_manager._read_generation()
        live_lease = lease_manager._read_live_lease()
        if live_lease is not None or generation.status not in {"never_acquired", "released"}:
            raise RuntimeError(...)
        _assert_local_committed_baseline(root, engine, root_key)
        return _execute_local_candidate_update_unfenced(root, target_file, engine)

# contextor/core/reporting_engine/persistent_registry.py:212-260
self._lock()
...
yield
for name, path in self.files.items():
    tmp_path = path.with_suffix(".json.tmp")
    ...
    tmp_path.write_text(data_str, encoding="utf-8")
...
os.replace(tmp_path, path)
```

Contextor blast radius returned confirmed direct static consumers of `acquire_full_analysis` in runtime/GUI and tests; `run_full_analysis_exclusive` in CLI, profile runner, MCP analysis jobs/worker, GUI and tests. Dynamic reachability beyond these is UNKNOWN. No preview/truncated source was accepted as a complete implementation.

## TARGETED_REGRESSION_OWNERS

- `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py`: writer-kind validation, timeout/cancellation, process death/orphan recovery, full/LIVE precedence.
- `C:\Temp\Contextor_Repo\tests\test_live_desktop_integration.py`: startup publish and busy-skip.
- `C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py`: committed publish/update, startup backfill, watcher retry, real service ownership.
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`: local authority, stale revision, domain fence, rollback, timeout, strict two-process writer.

## SOURCE_SYNC_VERIFICATION

Contextor updated-test fetches: implementation_is_complete=true, no_partial_symbol_source=true, workspace_sync=verified, canonical revision 223. Production requests were exact source ranges. Textual status shows only authorized test modified. This establishes indexed-source/workspace identity, not serving-process reload.

## LIVE_REVISION_BEFORE_AFTER

Before 222 (task handoff); after 223. `get_live_events(after_revision=222)` returned one `desktop_watcher` `UPDATED` event for `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`, continuity=continuous, resync_required=false, activity epoch `9e9a2a2edcb046bba00df0850244ad36`. No manual update_file.

## FULL_DIFFS_FOR_CHANGED_FILES

Complete raw Git diff for the only source/test file changed this task:

```diff
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index 9476dfb..6cf9952 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -138,9 +138,19 @@ def _cross_process_local_candidate_worker(
         if not first:
             assert mcp_runtime.get_or_init_engine(Path(repo_text)) is not None
             ready.set()
-        results.put(_local_update(Path(repo_text), Path(target_text)))
+        response = _local_update(Path(repo_text), Path(target_text))
+        results.put({
+            "role": "first" if first else "second",
+            "response": response,
+        })
     except BaseException as exc:
-        results.put({"status": "WORKER_ERROR", "error": repr(exc)})
+        results.put({
+            "role": "first" if first else "second",
+            "response": {
+                "status": "WORKER_ERROR",
+                "error": repr(exc),
+            },
+        })
 
 
 @pytest.mark.parametrize("prior_generation", ["never_acquired", "released"])
@@ -449,10 +459,22 @@ def test_two_mcp_processes_cannot_enter_local_candidate_concurrently(
 
     assert first.exitcode == 0
     assert second.exitcode == 0
-    first_result = results.get(timeout=5)
-    second_result = results.get(timeout=5)
+    received = [
+        results.get(timeout=5),
+        results.get(timeout=5),
+    ]
+    by_role = {
+        item["role"]: item["response"]
+        for item in received
+    }
+    assert set(by_role) == {"first", "second"}
+
+    first_result = by_role["first"]
+    second_result = by_role["second"]
+
     assert first_result["status"] == "UPDATED"
-    assert second_result["status"] in {"ERROR", "UPDATED"}
+    assert second_result["status"] == "ERROR"
+    assert "stale" in second_result.get("error", "").lower()
     assert not update_started.is_set()
     assert read_metadata(repo_cache_dir(repo)).revision == 2
```

## UNRESOLVED_INVARIANTS

- UNKNOWN whether all possible direct facade/report calls have outer full-analysis admission.
- CODE_PATH_PROVED distinct outer locks allow local/full overlap; no real-runtime corruption schedule was observed.
- UNKNOWN actual local transaction duration distribution relative to the 10-second domain timeout.
- CODE_PATH_PROVED direct LIVE update dispatch bypasses queued mutation guard; local admission still rejects active LIVE lease.
- No unified current lock order spans full analysis, local MCP and every registry writer. This task includes no design or production edit.

## FINAL_VERDICT

**PART_A_PASS; PART_B_DISCOVERY_COMPLETE_WITH_UNRESOLVED_GLOBAL_WRITER_EXCLUSION.** The strict cross-process regression and four authority regressions pass. The current code does not prove complete local/full-analysis transaction exclusion. Stop and await `proceduj`.

