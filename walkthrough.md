# CONTEXTOR PY315-M3C-R1 — real LIVE single-owner concurrency certification

## PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP was queried first. `tests.test_live_authority_bootstrap` was fresh at canonical revision 958 with `workspace_sync=verified` before the edit. Contextor returned exact implementations for the insertion target, `_repo`, `_stop`, and both existing desktop admission tests. HEAD was `6f1003ef2d2340d575bb979787920005b41016cb`; only pre-existing worktree modification was `walkthrough.md`. The insertion anchor occurred once. Lab Python was 3.15.2, production `.venv` Python was 3.10.9, and lab `pip check` passed.

## SOURCE_EVIDENCE

CODE_PATH_PROVED: `_repo` creates a `tmp_path` repository and sets cache/state beneath `tmp_path`; `tests/conftest.py` isolates the registry beneath `tmp_path`. `connect_or_start` launches the real LIVE child through the calling interpreter's `sys.executable`, uses an exclusive startup lock, and verifies an existing endpoint against repository and authority identity. `_stop` requests shutdown and polls for disconnection. The selected cross-process lease test uses two spawned processes and asserts exactly one winner and one `LeaseAlreadyHeld`; it does not launch a LIVE service.

## EXACT_TEST_ADDITION

Inserted the architect-supplied complete `test_concurrent_cold_start_has_one_real_live_authority` immediately before `test_protocol_attach_ignores_broken_desktop_claim_storage_and_desktop_admission_fails`. Existing tests and production source were untouched. Python 3.15 `py_compile` passed with `.pyc` written outside the repository to `C:\Temp\Contextor_PY315_M2_Lab\test_live_authority_bootstrap.pyc`.

## CONCURRENT_COLD_START

PASS: The new test uses a three-party barrier to release two `connect_or_start` calls concurrently. Both returned authenticated clients and equal service PID, service instance ID, lease generation, and endpoint fingerprint. It asserted an active generation 1, live lease, and endpoint during the test. It passed alone on Python 3.15 (`1 passed in 9.22s`) and again in the four-test gate. After shutdown, retained Python 3.15 gate evidence shows one repository identity `ctx_e295a6f5`, service PID 14700, start identity `134379338813945673`, generation 1, final status `released`, and read-only process state `dead`.

## EXISTING_DESKTOP_ADMISSION_TESTS

PASS: `test_verified_existing_authority_attaches_and_second_desktop_is_rejected` and `test_protocol_first_authority_has_single_durable_desktop_claim` passed in the Python 3.15 four-test gate. The first retained real LIVE service PID was 8440 with repo ID `ctx_50cb4a7d`, start identity `134379338894815284`, final `released`, and dead postcheck. The second retained final service PID was 1508 with repo ID `ctx_d163ad7b`, start identity `134379339017985423`, final generation 2 and `released`; it was dead at postcheck. The second test intentionally starts a successor generation after shutdown, so final generation 2 is expected.

## CROSS_PROCESS_LEASE_ARBITRATION

PASS: `tests/live_state/test_runtime_lease.py::test_cross_process_acquisitions_have_exactly_one_winner` passed. Its source asserts two spawned process exit codes zero, one `winner`, and one `LeaseAlreadyHeld`. Its separate synthetic test-domain lease artifact remains `active` with recorded PID 14616 and synthetic start identity `child-1`; that PID was `dead` at postcheck. This artifact is a lease-arbitration fixture, not an uncleaned LIVE service. No endpoint was left in that test directory.

## PY315_FOUR_TEST_GATE

PASS: The exact new test plus three specified existing tests ran with lab Python and `-q -rs -p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`, and external `--basetemp C:\Temp\Contextor_PY315_M2_Lab\pytest-m3c-r1`: `4 passed in 30.40s`, exit code 0.

## PY310_REGRESSION

PASS: The new single test ran once with production Python 3.10 and separate external `--basetemp C:\Temp\Contextor_PY315_M2_Lab\pytest-m3c-r1-py310`: `1 passed in 7.77s`, exit code 0. Its retained repo ID was `ctx_df11c285`, service PID 9668, start identity `134379339311050199`, generation 1, final `released`, dead process, no endpoint, and no live lease.

## LIVE_SERVICE_IDENTITIES

DIRECT_EVIDENCE: Retained generation metadata after the four-test Python 3.15 gate identified real LIVE services for the new concurrency test (PID 14700), verified existing authority test (PID 8440), and protocol-first test's final generation (PID 1508). Their repo IDs and start identities are listed above. The initial predecessor service in the protocol-first test was not retained as a separate generation artifact, but the test's assertions and subsequent successful generation 2 prove its lifecycle contract. The single-test Python 3.15 run was audited before the gate replaced its `--basetemp`: PID 9596, start identity `134379338549102640`, repo ID `ctx_435ae7d8`, generation 1, `released`, dead. The Python 3.10 run's PID 9668 is separately retained.

## ENDPOINT_AND_LEASE_CLEANUP

DIRECT_EVIDENCE: Following the standalone Python 3.15 run, generation was `released`, PID 9596 was dead, and no endpoint or live lease remained. Following the four-test gate, all three real LIVE generation artifacts were `released`, PIDs 14700, 8440, and 1508 were dead, and no LIVE endpoint remained. The only retained lease was the deliberately active synthetic cross-process arbitration fixture with a dead recorded PID; it is not associated with a running LIVE endpoint. Following the Python 3.10 regression, generation was `released`, PID 9668 was dead, and no endpoint or live lease remained. Read-only process listing found no Python command line referencing either M3C-R1 temp tree. No process was terminated during postcheck.

## PRODUCTION_ISOLATION

Lab remained Python 3.15.2; production `.venv` remained Python 3.10.9; lab `pip check` still passed. Git showed only the specified test and this report modified. No backend or production LIVE restart, production configuration/dependency change, `update_file`, commit, or full suite occurred. All test repositories/cache/state/registry resources were under external `--basetemp` roots.

## MCP_POSTCHANGE_AUDIT

BLOCKED: Read-only Contextor MCP module context for the edited `tests.test_live_authority_bootstrap` returned `canonical_revision=958`, `canonical_state=fresh`, `workspace_sync=out_of_sync`, and advisory warning `Target file on disk has been modified since canonical state revision was generated.` The same result repeated after a short wait. Thus the required post-change `workspace_sync=verified` was not obtained. The task forbids `update_file`; no manual sync or restart was performed. Test PASS is direct runtime evidence for the isolated tests, but does not satisfy this separate freshness gate.

## FILES_CHANGED

- `tests/test_live_authority_bootstrap.py`

`walkthrough.md` is the required report and excluded from source/test diff accounting.

## FULL_DIFFS

### tests/test_live_authority_bootstrap.py — complete actual diff

```diff
diff --git a/tests/test_live_authority_bootstrap.py b/tests/test_live_authority_bootstrap.py
index 706a8fb..767a505 100644
--- a/tests/test_live_authority_bootstrap.py
+++ b/tests/test_live_authority_bootstrap.py
@@ -214,6 +214,75 @@ def test_verified_existing_authority_attaches_and_second_desktop_is_rejected(
         _stop(first)
 
 
+def test_concurrent_cold_start_has_one_real_live_authority(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+):
+    from concurrent.futures import ThreadPoolExecutor
+
+    repo = _repo(tmp_path, monkeypatch)
+    barrier = threading.Barrier(3)
+    clients = []
+
+    def attach():
+        barrier.wait(timeout=10)
+        return connect_or_start(
+            repo,
+            client_kind="protocol",
+            timeout=10,
+            cold_start_timeout=20,
+        )
+
+    try:
+        with ThreadPoolExecutor(max_workers=2) as pool:
+            futures = [pool.submit(attach) for _ in range(2)]
+            barrier.wait(timeout=10)
+            for future in futures:
+                clients.append(future.result(timeout=30))
+
+        first, second = clients
+
+        assert first.ping()["status"] == "ok"
+        assert second.ping()["status"] == "ok"
+
+        assert first.service_pid == second.service_pid
+        assert (
+            first.endpoint.service_instance_id
+            == second.endpoint.service_instance_id
+        )
+        assert (
+            first.endpoint.lease_generation
+            == second.endpoint.lease_generation
+        )
+        assert (
+            first.endpoint.fingerprint()
+            == second.endpoint.fingerprint()
+        )
+
+        identity = read_repository_identity(repo)
+        assert identity is not None
+
+        domain = RuntimeDomain.from_identity(
+            identity, mode="production"
+        )
+        manager = RuntimeLeaseManager(domain)
+        generation = manager.read_generation()
+
+        assert generation.status == "active"
+        assert generation.last_lease_generation == 1
+        assert manager.read_live_lease() is not None
+        assert endpoint_file(repo).is_file()
+
+    finally:
+        for client in clients:
+            _stop(client)
+
+        attached = connect(repo)
+        if attached is not None:
+            _stop(attached)
+
+    assert not endpoint_file(repo).exists()
+
+
 def test_protocol_attach_ignores_broken_desktop_claim_storage_and_desktop_admission_fails(
     tmp_path: Path, monkeypatch: pytest.MonkeyPatch
 ):
```

## REMAINING_UNKNOWN

Whether the Desktop watcher will ingest the edited test and advance Contextor's canonical revision; the mandatory post-change workspace sync is currently out of sync. Production LIVE adoption of Python 3.15 was outside scope.

## FINAL_VERDICT

`BLOCKED_WITH_EXACT_EVIDENCE`: focused Python 3.15 and 3.10 tests and real LIVE cleanup passed, but the mandatory Contextor post-change `workspace_sync=verified` gate did not. STOP.
