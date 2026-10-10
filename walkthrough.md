# L32H2G2 — direct publish generation ownership evidence

## FILES_CHANGED_THIS_TASK
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only)
No production file changed in this task. git status --short at completion showed only these two modified paths.

## SOURCE_PREFLIGHT
DIRECT_EVIDENCE: Contextor MCP returned complete AST-bounded current implementations with workspace_sync=verified at revision 292 for CanonicalLiveServer._execute_committed_publish (C:\Temp\Contextor_Repo\contextor\core\live_state\ipc.py:1297), _execute_publish (:1506), _dispatch (:2131), LiveStateClient.publish (:2556), and locked_committed_snapshot (C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1949). Existing durable_harness uses actual locked_committed_snapshot, save_snapshot(exact_revision=...), versioned FileState payload, and CanonicalLiveServer with committed_snapshot_reader. No source preview was treated as complete. G1/F1/F2/F3 findings were not reopened.

## REAL_IPC_INTERLEAVING
A test fixture initialized disk generation R=1 and a real listening CanonicalLiveServer at revision 1. The parent acquired the actual repository full_analysis.lock as legitimate-full-writer, then committed exact disk generation R+1=2 with FileState revision 2. The parent deliberately withheld its IPC publish. A spawned independent process attempted acquire_full_analysis(timeout=0.0), observed FullAnalysisBusyError, and nevertheless used LiveStateClient.publish through the real IPC endpoint. Its response was received before the parent resumed its own publish. Spawn, queue timeout, process join and server thread join were bounded; no sleeps or fake publish response were used.

## ACTUAL_LEASE_OWNERSHIP
DIRECT_EVIDENCE from the passing spawned-process test: the legitimate writer retained its FullAnalysisLease across commit, raw client request and owner request. The raw process could not acquire the same OS lease. _dispatch("publish") has no _mutation_guard admission; _execute_publish uses the server mutation execution lock, and committed publish validates the locked durable generation. Thus A=NO: raw publish did not require a caller-held canonical lease; B=YES: it front-ran the owner.

## RAW_PUBLISH_RESPONSE
Exact response asserted and observed through real LiveStateClient.publish:
```python
{"status": "ok", "revision": 2, "seq": 1, "source": "committed_snapshot"}
```
Immediately afterward LIVE RAM held the disk-loaded state_id="sid", revision=2, value="owner-generation"; activity_seq=1 and one publish event existed.

## OWNER_PUBLISH_RESPONSE
The same still-leased writer then called LiveStateClient.publish for its own committed generation 2. Exact response:
```python
{"status": "error", "error": "non_monotonic_canonical_revision",
 "revision": 2, "candidate_revision": 2, "expected_revision": 3}
```
C=YES, E=YES: owner receives an error although its committed generation is already installed in LIVE RAM. This is a response/ownership semantic hazard, not proof of durable corruption.

## RAM_DISK_FILESTATE_PARITY
D=YES: after both requests, LIVE RAM revision/state_id=2/"sid"; load_snapshot metadata and state revision/state_id=2/"sid"; FileStateManager.revision=2; read_metadata equals loaded metadata. The raw publish did not write another generation. The test also sent uncommitted revision 3 and mismatched state_id="wrong" before the raw request; both returned committed_publish_generation_mismatch without changing RAM, activity seq or events. H=NO for these tested invalid/mismatched candidates; complete source requires exact committed revision/state_id under snapshot lock.

## EVENT_SEQUENCE_AND_ORIGIN
F=YES: the sole event for revision 2 had origin="unleased_raw_ipc" rather than "legitimate_full_writer". G=NO extra event on rejected owner publish or its duplicate retry: activity_seq stayed 1 and event count stayed 1. Event operation was publish and canonical_revision=2.

## DUPLICATE_RETRY_BEHAVIOR
The legitimate writer retried the identical state_id and revision while the committed generation remained current. Response was the identical non_monotonic_canonical_revision error with expected_revision=3. The server state, event list and activity_seq were unchanged. Existing test_r3_r5_r8_r9_r15_rejections_leave_live_and_event_unchanged explicitly requires duplicate rejection; this task did not change that public behavior. EXPECTED_IDEMPOTENT_BEHAVIOR applies only to state/event nonmutation, not to an ok acknowledgement.

## EXISTING_TEST_CONTRACTS
Selected existing passing nodes:
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r2_r11_committed_publish_installs_disk_object_and_isolates_candidate
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r3_r5_r8_r9_r15_rejections_leave_live_and_event_unchanged
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r4_r12_r29_durable_catch_up_after_earlier_publish_failure
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r10_committed_publish_respects_cross_process_store_lock
- C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py::test_r30_publish_does_not_persist_another_revision
- C:\Temp\Contextor_Repo\tests\test_live_mutation_coordinator.py::test_publish_and_queued_update_are_single_writer_serialized
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py::test_lease_is_held_during_publication
- C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py::test_scoped_single_file_publishes_to_real_live_server_under_writer_lease

## TARGETED_TEST_RESULTS
New real IPC interleaving test: 1 passed in 4.18 s. Eight selected existing compatibility tests: 8 passed in 12.28 s. py_compile on changed test file: PASS. git diff --check on changed test file: PASS. No full repository suite, analysis, process restart or manual update_file.

## SEMANTIC_HAZARD_CLASSIFICATION
PROVED_ACK_ORIGIN_SEMANTIC_HAZARD in an isolated real IPC, real OS lease, committed-generation fixture. Raw unleased request installed the valid durable generation and supplied its origin; the legitimate owner's subsequent publication was rejected as non-monotonic. PROVED_CORRUPTION: NO; RAM, snapshot metadata/state and FileState remained consistent. Uncommitted or mismatched candidate acceptance: not observed and rejected in targeted checks. No claim is made that this exact race occurred in a serving production environment.

## PRODUCTION_CALLER_REACHABILITY
Source audit confirms existing facade full, scoped and GUI startup publish call sites hold their full/scoped/startup lease across synchronous publication. No unleased production caller was confirmed. A raw LiveStateClient can reach the real IPC endpoint without the lease, as proved by the spawned fixture. Deployment reachability of such a client outside tests is UNKNOWN.

## SOURCE_SYNC
Post-test Contextor get_file_edit_context for the changed test file and get_symbol_implementation for _execute_committed_publish returned canonical_state=fresh, workspace_sync=verified, canonical_revision=293, cycles.count=0. No production source was edited.

## LIVE_REVISION_BEFORE_AFTER
Before 292. After 293. get_live_events(after_revision=292) returned one desktop_watcher update_file event at revision 293 for C:\Temp\Contextor_Repo\tests\test_durable_verified_publish.py, continuity=continuous, resync_required=false.

## FULL_DIFFS

```diff
diff --git a/tests/test_durable_verified_publish.py b/tests/test_durable_verified_publish.py
index 304ea9c..1825161 100644
--- a/tests/test_durable_verified_publish.py
+++ b/tests/test_durable_verified_publish.py
@@ -1,6 +1,7 @@
 """Focused durable-generation publication contract."""
 
 import copy
+import threading
 from contextlib import contextmanager
 from multiprocessing import get_context
 from pathlib import Path
@@ -9,7 +10,7 @@ from types import SimpleNamespace
 import pytest
 
 from contextor.core.live_state import ipc as ipc_module
-from contextor.core.live_state.ipc import CanonicalLiveServer
+from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
 from contextor.core.live_state.store import (
     load_snapshot,
     locked_committed_snapshot,
@@ -30,6 +31,30 @@ def _hold_snapshot_lock(lock_path, ready, release):
         _release_lock(fd)
 
 
+def _raw_publish_without_writer_lease(repo_path, endpoint, response_queue):
+    from contextor.core.analysis.full_analysis_lease import (
+        FullAnalysisBusyError,
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+
+    try:
+        lease = acquire_full_analysis(
+            repo_path, owner="raw-publish-lease-probe", timeout=0.0
+        )
+    except FullAnalysisBusyError:
+        lease_denied = True
+    else:
+        release_full_analysis(lease)
+        lease_denied = False
+    response = LiveStateClient(endpoint).publish(
+        SimpleNamespace(state_id="sid", revision=2),
+        origin="unleased_raw_ipc",
+        timeout=10.0,
+    )
+    response_queue.put((lease_denied, response))
+
+
 @pytest.fixture
 def durable_harness(tmp_path):
     repo = tmp_path / "repo"
@@ -166,6 +191,112 @@ def test_r3_r5_r8_r9_r15_rejections_leave_live_and_event_unchanged(durable_harne
     _assert_unchanged(server, latest)
 
 
+def test_raw_ipc_publish_front_runs_lease_owner_same_committed_generation(
+    durable_harness,
+):
+    from contextor.core.analysis.full_analysis_lease import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+    from contextor.core.analysis.state_manager import FileStateManager
+
+    durable_harness.commit(1)
+    initial = load_snapshot(
+        durable_harness.cache,
+        expected_repo_id=durable_harness.identity.repo_id,
+        expected_root_path=durable_harness.identity.root_path,
+    )
+    server = durable_harness.server(state=initial[0], revision=initial[1].revision)
+    thread = threading.Thread(target=server.serve_forever, daemon=True)
+    thread.start()
+    client = LiveStateClient(server.endpoint)
+    lease = acquire_full_analysis(
+        durable_harness.repo, owner="legitimate-full-writer", timeout=5.0
+    )
+    try:
+        candidate, committed = durable_harness.commit(2, value="owner-generation")
+        before = _unchanged(server)
+        assert client.publish(
+            SimpleNamespace(state_id="sid", revision=3),
+            origin="invalid_uncommitted",
+            timeout=10.0,
+        )["error"] == "committed_publish_generation_mismatch"
+        _assert_unchanged(server, before)
+        assert client.publish(
+            SimpleNamespace(state_id="wrong", revision=2),
+            origin="invalid_identity",
+            timeout=10.0,
+        )["error"] == "committed_publish_generation_mismatch"
+        _assert_unchanged(server, before)
+
+        context = get_context("spawn")
+        response_queue = context.Queue()
+        raw = context.Process(
+            target=_raw_publish_without_writer_lease,
+            args=(str(durable_harness.repo), server.endpoint, response_queue),
+        )
+        raw.start()
+        try:
+            lease_denied, raw_response = response_queue.get(timeout=12.0)
+            raw.join(5.0)
+        finally:
+            if raw.is_alive():
+                raw.terminate()
+                raw.join(5.0)
+        assert raw.exitcode == 0
+        assert lease_denied is True
+        assert raw_response == {
+            "status": "ok",
+            "revision": 2,
+            "seq": 1,
+            "source": "committed_snapshot",
+        }
+        assert server._revision == 2
+        assert server._state.state_id == committed.state_id
+        assert server._state.revision == 2
+        assert server._state.value == "owner-generation"
+        assert server._activity_seq == 1
+        assert len(server._events) == 1
+        assert server._events[0]["origin"] == "unleased_raw_ipc"
+        assert server._events[0]["canonical_revision"] == 2
+
+        owner_response = client.publish(
+            candidate, origin="legitimate_full_writer", timeout=10.0
+        )
+        assert owner_response == {
+            "status": "error",
+            "error": "non_monotonic_canonical_revision",
+            "revision": 2,
+            "candidate_revision": 2,
+            "expected_revision": 3,
+        }
+        before_retry = _unchanged(server)
+        assert client.publish(
+            candidate, origin="legitimate_full_writer", timeout=10.0
+        ) == owner_response
+        _assert_unchanged(server, before_retry)
+
+        disk = load_snapshot(
+            durable_harness.cache,
+            expected_repo_id=durable_harness.identity.repo_id,
+            expected_root_path=durable_harness.identity.root_path,
+        )
+        assert disk[1].revision == committed.revision == 2
+        assert disk[1].state_id == committed.state_id == "sid"
+        assert disk[0].revision == server._state.revision == 2
+        assert disk[0].state_id == server._state.state_id
+        assert FileStateManager(str(durable_harness.cache)).revision == 2
+        assert read_metadata(durable_harness.cache) == disk[1]
+        assert server._activity_seq == 1
+        assert len(server._events) == 1
+        assert server._events[0]["origin"] == "unleased_raw_ipc"
+    finally:
+        release_full_analysis(lease)
+        server.close()
+        thread.join(5.0)
+    assert not thread.is_alive()
+
+
 def test_r4_r12_r29_durable_catch_up_after_earlier_publish_failure(durable_harness):
     durable_harness.commit(1)
     failed = durable_harness.server(
```

## FINAL_VERDICT
PROVED_ACK_ORIGIN_SEMANTIC_HAZARD

