# L32H2F2_REGISTRY_CONSTRUCTOR_RECOVERY_LOCK

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\core\reporting_engine\persistent_registry.py
- C:\Temp\Contextor_Repo\tests\test_persistent_registry.py

Only the authorized production and test files changed. No edits were made to tests/test_mcp_regressions.py or tests/mcp/tools/test_minimal_registry_read_path.py. walkthrough.md is the requested report and is excluded from the source/test change list.

## SOURCE_CONTRACT_VERIFICATION

Contextor MCP was used first. Its documentation was read for symbol implementation, lineage, call context, source ranges, file-edit context, search, blast radius, and LIVE events. No standalone deferred tests_covering tool was registered; get_file_edit_context exposes tests_covering. That field reported 128 statically reachable test modules (static dependency reachability, depth 6). Relevant targeted consumers were selected from that evidence and source call sites.

Contextor fetched the complete PersistentIdentityRegistry class methods with implementation_is_complete=true and no_partial_symbol_source=true at revision 254, workspace_sync=verified. It returned complete implementations of __init__, _lock, _unlock, _recover_transaction, _load_all, transaction, read_transaction, _load_json, and _repair_kind. After the patch, it fetched the complete updated __init__ with implementation_is_complete=true at revision 257, workspace_sync=verified. The updated source is:

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).expanduser().resolve()
        from contextor.core.repository_identity import ensure_repository_identity

        identity, self.registry_dir = ensure_repository_identity(self.repo_path)
        self.repo_id = identity.repo_id

        self.meta_file = self.registry_dir / "repo.meta.json"

        self.lock_file = self.registry_dir / ".lock"
        self.transaction_file = self.registry_dir / "transaction.tmp"

        self.files = {
            "module_slots": self.registry_dir / "module_slots.json",
            "artifact_slots": self.registry_dir / "artifact_slots.json",
            "module_recovery": self.registry_dir / "module_recovery.json",
            "artifact_recovery": self.registry_dir / "artifact_recovery.json",
            "output_references": self.registry_dir / "output_references.json",
            "module_registry": self.registry_dir / "module_registry.json",
            "artifact_registry": self.registry_dir / "artifact_registry.json",
        }

        self._state = {}
        self._in_transaction = False
        self._transaction_mode: str | None = None
        self._lock_file_obj = None

        self._lock()
        try:
            self._recover_transaction()
            self._load_all()
        finally:
            self._unlock()

Source contracts verified:

- lock_file and _lock_file_obj exist before constructor recovery.
- _lock opens the existing repository registry .lock file and obtains the existing OS byte lock on Windows (msvcrt) or flock on POSIX. _unlock releases that lock and closes the file.
- _recover_transaction and _load_all do not acquire a lock internally. _load_all reads JSON and applies _repair_kind to in-memory state.
- transaction and read_transaction already use the same _lock around recovery and loading. transaction retains its existing write/commit behavior; read_transaction retains its non-committing behavior. Both release via finally.
- Existing same-object nested transaction/read_transaction behavior is preserved by their _in_transaction fast paths.
- Contextor call context showed constructor-local callees, while artifact blast radius for the exact constructor symbol reported zero direct static artifact consumers. File-level Contextor context reported 58 module consumers and 128 test-covering modules, with truncated evidence in the compact projection.
- Contextor literal search and targeted workspace text search located production constructor call sites in MCP runtime hydration, query_helpers.read_registries, LIVE _repository_updater, hydrate_repository_engine, get_file_edit_context, facade repository identity initialization, catalog_from_registry, and build_artifact_pipeline. The inspected caller order places construction before read_transaction/transaction/checkpoint usage. _repository_updater is called inside the distinct full-analysis writer lease; it does not already hold the registry OS lock. No confirmed production constructor call recursively constructs another registry for the same repository while already holding that registry OS lock.
- Allowed source/test paths were clean before this task's edits. The exact patch anchor matched.

## F2_RED_RESULT

Before the production edit, the newly added targeted regressions produced 5 failed and 1 passed in 17.59 seconds:

- Constructor recovery ran while a spawned process held the registry OS lock.
- A second process acquired the registry lock while constructor recovery was paused.
- A constructor entered recovery and consumed the active writer's staged transaction generation.
- Both recovery-failure and load-failure workers showed the constructor had not acquired the lock.
- The independent-instance lock-path assertion passed, as expected because both instances already derived the same path.

The RED results demonstrate the constructor's recovery/load sequence was not serialized by the registry lock.

## F2_GREEN_RESULT

The same new regressions passed after the exact patch: 6 passed in 13.27 seconds.

The complete tests/test_persistent_registry.py passed: 22 passed in 14.57 seconds.

Additional targeted existing tests passed: 7 passed in 6.00 seconds, covering the complete minimal registry read-path file, read_registries committed-write/error handling, same-root engine hydration serialization, and persisted-update snapshot hydration.

The complete tests/test_repository_identity_initialization.py passed: 4 passed in 2.28 seconds.

Across the final green runs, 33 distinct targeted tests passed. No full repository pytest suite was run.

## CONSTRUCTOR_LOCK_ORDER

Initialization still resolves the repository identity and sets registry paths/fields first. It then acquires the same existing registry OS lock used by transaction and read_transaction, runs _recover_transaction followed by _load_all while holding that lock, and releases in finally. No full_analysis.lock, second mutex, schema change, path change, or transaction semantic change was introduced.

## CROSS_PROCESS_RECOVERY_EXCLUSION

The tests use multiprocessing spawn and real PersistentIdentityRegistry._lock calls against isolated temporary repositories.

- A constructor process cannot enter _recover_transaction while another process holds the .lock byte lock.
- The lock-probe process cannot acquire during either a paused recovery phase or a paused _load_all phase.
- A writer process pauses after writing its committing marker and all staged JSON files but before the first staged-file replace. While the writer still holds the registry lock, an independent constructor cannot enter recovery; marker bytes and every staged file remain unchanged.
- After writer release, the writer commits generation 2/1, the constructor then loads both seed.py=1/1 and during_write.py=2/1, and transaction marker/staging files are cleared.

## RECOVERY_AND_LOAD_ATOMICITY

The new phase-barrier regression proves another process cannot enter the same OS lock while recovery or _load_all is active. Existing transaction/read_transaction paths continue to use the same lock around both operations. Constructor now uses that existing lock once around both operations, with no unlocked interval between its recovery and load steps.

## INTERRUPTED_COMMIT_COMPATIBILITY

Existing tests/test_persistent_registry.py::test_read_registries_recovers_interrupted_commit passed. It creates a real committing marker and staged module registry file, calls read_registries (whose constructor now performs the recovery under the lock), then verifies the recovered mapping and removal of both the staged file and transaction marker.

## HEALTHY_READ_NO_WRITE

Existing tests/test_persistent_registry.py::test_read_registries_healthy_read_keeps_bytes_mtime_and_ids passed. It compares registry JSON bytes and mtimes before and after repeated healthy read_registries calls, checks that marker and temporary files remain absent, and verifies IDs after reload. No unconditional registry JSON rewrite was observed.

## EXCEPTION_LOCK_RELEASE

New parametrized recovery and load failure cases inject an exception after confirming the constructor acquired the OS lock. The failing process retains the exception traceback and stays alive while a separate spawned process constructs another registry for the same repository. That second constructor succeeds in each case, proving the first constructor's finally released the lock. The injected exception itself remains propagated.

## NESTED_LOCK_GATE

No production same-repository constructor-under-registry-lock call site was confirmed in the inspected direct production constructor usages. The change adds no constructor recursion and no new lock acquisition to transaction/read_transaction. Existing write-inside-read rejection and read-inside-write generation visibility tests passed in the complete registry test file.

## PERSISTENT_ID_COMPATIBILITY

Persistent identity, slot-generation, recovery, checkpoint/restore, garbage-collection, and multi-repository isolation tests passed as part of the complete test_persistent_registry.py file. The active writer/constructor regression also verifies the expected 1/1 and 2/1 module identities across commit and subsequent constructor load.

## TARGETED_TEST_RESULTS

Commands used the repository .venv Python. No full suite was run.

RED command selected the five newly added test functions (the exception test has two parameters): 5 failed, 1 passed.

New F2 regression command after patch: 6 passed:
- tests/test_persistent_registry.py::test_constructor_waits_for_registry_lock_held_by_another_process
- tests/test_persistent_registry.py::test_constructor_holds_registry_os_lock_during_recovery_and_load
- tests/test_persistent_registry.py::test_constructor_does_not_consume_active_writer_staging_and_loads_commit
- tests/test_persistent_registry.py::test_constructor_releases_registry_lock_after_recovery_or_load_failure[recovery]
- tests/test_persistent_registry.py::test_constructor_releases_registry_lock_after_recovery_or_load_failure[load]
- tests/test_persistent_registry.py::test_independent_registry_instances_share_the_same_os_lock_path

Complete registry suite:
- tests/test_persistent_registry.py: 22 passed.

Contextor-selected existing targeted regressions:
- tests/mcp/tools/test_minimal_registry_read_path.py: 4 passed.
- tests/test_mcp_regressions.py::test_read_registries_observes_committed_write_and_propagates_read_error: passed.
- tests/test_mcp_regressions.py::test_same_root_double_hydration_is_serialized: passed.
- tests/test_mcp_incremental_hydration.py::test_update_persist_restart_hydrate_keeps_live_reverse_context: passed.

Facade repository identity consumer:
- tests/test_repository_identity_initialization.py: 4 passed.

py_compile passed for the modified production and test files. git diff --check passed. Git emitted LF-to-CRLF advisories only; there were no whitespace errors.

## SOURCE_SYNC_VERIFICATION

Post-edit Contextor source retrieval for PersistentIdentityRegistry.__init__ was complete and workspace_sync=verified at canonical revision 257. get_file_edit_context also reported workspace_sync=verified. Contextor reported cycles.count=0 with fresh availability.

Desktop watcher events after starting revision 254 were continuous:
- revision 255: tests/test_persistent_registry.py UPDATED.
- revision 256: tests/test_persistent_registry.py UNCHANGED.
- revision 257: contextor/core/reporting_engine/persistent_registry.py UPDATED; blast-radius analytics were deferred for that event.
LIVE reported continuity=continuous, resync_required=false, and unchanged activity_epoch 9e9a2a2edcb046bba00df0850244ad36.

## LIVE_REVISION_BEFORE_AFTER

254 -> 257. Event continuity was continuous and resync_required=false. No manual update_file or full analysis was used.

## REMAINING_F3_RISKS

F3 migration coordination remains outside this task and was not changed or certified. This result covers constructor recovery/load serialization under the existing registry OS lock; it does not claim completion of the broader writer-coverage program.

## RESTART_REQUIRED

No MCP, Desktop, or LIVE restart was performed. A serving-process runtime reload is still required before claiming those running processes imported this production change; watcher source events and verified indexing do not prove process reload.

## FINAL_VERDICT

F2 exact constructor-lock patch and targeted regressions: PASS. The existing registry OS lock now serializes constructor recovery and loading, including against active cross-process staged commits. Registry recovery, healthy read behavior, transaction semantics, identities, exception propagation, and selected hydration consumers passed. This is not an L32H final pass, and no serving-process reload certification is claimed.

## FULL_DIFFS

diff --git a/contextor/core/reporting_engine/persistent_registry.py b/contextor/core/reporting_engine/persistent_registry.py
index c7644a5..e622237 100644
--- a/contextor/core/reporting_engine/persistent_registry.py
+++ b/contextor/core/reporting_engine/persistent_registry.py
@@ -39,8 +39,12 @@ class PersistentIdentityRegistry:
         self._transaction_mode: str | None = None
         self._lock_file_obj = None
 
-        self._recover_transaction()
-        self._load_all()
+        self._lock()
+        try:
+            self._recover_transaction()
+            self._load_all()
+        finally:
+            self._unlock()
 
     def _lock(self):
         self._lock_file_obj = open(self.lock_file, "w")
diff --git a/tests/test_persistent_registry.py b/tests/test_persistent_registry.py
index c985889..b850799 100644
--- a/tests/test_persistent_registry.py
+++ b/tests/test_persistent_registry.py
@@ -2,6 +2,7 @@ import os
 import json
 import shutil
 import copy
+import multiprocessing
 import pytest
 from pathlib import Path
 
@@ -15,6 +16,167 @@ def temp_repo(tmp_path):
     yield str(repo_dir)
     shutil.rmtree(repo_dir, ignore_errors=True)
 
+
+def _hold_registry_lock_process(repo_path, acquired, release):
+    registry = PersistentIdentityRegistry(repo_path)
+    registry._lock()
+    try:
+        acquired.set()
+        release.wait(timeout=10)
+    finally:
+        if registry._lock_file_obj is not None:
+            registry._unlock()
+
+
+def _observe_registry_constructor_process(
+    repo_path, started, recovery_entered, completed, outcome
+):
+    original_recover = PersistentIdentityRegistry._recover_transaction
+
+    def observe_recovery(self):
+        recovery_entered.set()
+        return original_recover(self)
+
+    PersistentIdentityRegistry._recover_transaction = observe_recovery
+    started.set()
+    try:
+        registry = PersistentIdentityRegistry(repo_path)
+        module_ids = dict(
+            registry._state.get("module_registry", {}).get("path_to_id", {})
+        )
+        outcome.put(("ok", module_ids))
+    except BaseException as exc:
+        outcome.put(("error", f"{type(exc).__name__}: {exc}"))
+    finally:
+        completed.set()
+
+
+def _pause_registry_constructor_process(
+    repo_path,
+    recovery_entered,
+    release_recovery,
+    load_entered,
+    release_load,
+    completed,
+    outcome,
+):
+    original_recover = PersistentIdentityRegistry._recover_transaction
+    original_load = PersistentIdentityRegistry._load_all
+
+    def pause_recovery(self):
+        recovery_entered.set()
+        if not release_recovery.wait(timeout=10):
+            raise TimeoutError("recovery phase was not released")
+        return original_recover(self)
+
+    def pause_load(self):
+        load_entered.set()
+        if not release_load.wait(timeout=10):
+            raise TimeoutError("load phase was not released")
+        return original_load(self)
+
+    PersistentIdentityRegistry._recover_transaction = pause_recovery
+    PersistentIdentityRegistry._load_all = pause_load
+    try:
+        PersistentIdentityRegistry(repo_path)
+        outcome.put("constructed")
+    except BaseException as exc:
+        outcome.put(f"error:{type(exc).__name__}:{exc}")
+    finally:
+        completed.set()
+
+
+def _probe_registry_lock_process(
+    repo_path, ready, attempt, attempted, acquired
+):
+    registry = PersistentIdentityRegistry(repo_path)
+    ready.set()
+    if not attempt.wait(timeout=10):
+        return
+    attempted.set()
+    registry._lock()
+    try:
+        acquired.set()
+    finally:
+        registry._unlock()
+
+
+def _pause_registry_writer_replace_process(
+    repo_path, staged, release, completed, outcome
+):
+    import contextor.core.reporting_engine.persistent_registry as registry_module
+
+    original_replace = registry_module.os.replace
+    paused = False
+
+    def pause_first_registry_replace(source, destination):
+        nonlocal paused
+        if not paused and Path(source).name.endswith(".json.tmp"):
+            paused = True
+            staged.set()
+            if not release.wait(timeout=10):
+                raise TimeoutError("staged transaction was not released")
+        return original_replace(source, destination)
+
+    registry_module.os.replace = pause_first_registry_replace
+    try:
+        registry = PersistentIdentityRegistry(repo_path)
+        with registry.transaction():
+            registry.sync_with_workspace({"seed.py", "during_write.py"}, set())
+        outcome.put(("committed", registry.get_module_id("during_write.py")))
+    except BaseException as exc:
+        outcome.put(("error", f"{type(exc).__name__}: {exc}"))
+    finally:
+        registry_module.os.replace = original_replace
+        completed.set()
+
+
+def _fail_registry_constructor_process(
+    repo_path, failure_stage, lock_acquired, failed, release, outcome
+):
+    original_lock = PersistentIdentityRegistry._lock
+
+    def observe_lock(self):
+        original_lock(self)
+        lock_acquired.set()
+
+    PersistentIdentityRegistry._lock = observe_lock
+    if failure_stage == "recovery":
+        def fail_recovery(self):
+            raise RuntimeError("injected recovery failure")
+
+        PersistentIdentityRegistry._recover_transaction = fail_recovery
+    else:
+        def fail_load(self):
+            raise RuntimeError("injected load failure")
+
+        PersistentIdentityRegistry._load_all = fail_load
+
+    captured_exception = None
+    try:
+        PersistentIdentityRegistry(repo_path)
+        outcome.put("unexpected_success")
+    except BaseException as exc:
+        captured_exception = exc
+        outcome.put(("failed", failure_stage, str(exc)))
+        failed.set()
+        release.wait(timeout=10)
+    finally:
+        # Retain the traceback (and failed constructor instance) until the
+        # parent has checked that another process can acquire the same lock.
+        _ = captured_exception
+
+
+def _probe_registry_constructor_process(repo_path, started, completed, outcome):
+    started.set()
+    try:
+        registry = PersistentIdentityRegistry(repo_path)
+        outcome.put(("ok", registry.lock_file.as_posix()))
+    except BaseException as exc:
+        outcome.put(("error", f"{type(exc).__name__}: {exc}"))
+    finally:
+        completed.set()
+
 def test_checkpoint_restore_persists_exact_registry_state(temp_repo):
     registry = PersistentIdentityRegistry(temp_repo)
     with registry.transaction():
@@ -383,3 +545,257 @@ def test_read_transaction_repairs_in_memory_without_persisting_projection(temp_r
         assert registry._state["module_slots"]["9"] == 3
 
     assert registry_file.read_bytes() == before
+
+
+def test_constructor_waits_for_registry_lock_held_by_another_process(temp_repo):
+    registry = PersistentIdentityRegistry(temp_repo)
+    context = multiprocessing.get_context("spawn")
+    holder_acquired = context.Event()
+    release_holder = context.Event()
+    constructor_started = context.Event()
+    recovery_entered = context.Event()
+    constructor_completed = context.Event()
+    outcome = context.Queue()
+    holder = context.Process(
+        target=_hold_registry_lock_process,
+        args=(temp_repo, holder_acquired, release_holder),
+    )
+    constructor = context.Process(
+        target=_observe_registry_constructor_process,
+        args=(
+            temp_repo,
+            constructor_started,
+            recovery_entered,
+            constructor_completed,
+            outcome,
+        ),
+    )
+    try:
+        holder.start()
+        assert holder_acquired.wait(timeout=5)
+        constructor.start()
+        assert constructor_started.wait(timeout=5)
+        assert recovery_entered.wait(timeout=0.5) is False
+
+        release_holder.set()
+        assert recovery_entered.wait(timeout=5)
+        assert constructor_completed.wait(timeout=5)
+        assert outcome.get(timeout=2)[0] == "ok"
+        constructor.join(timeout=5)
+        holder.join(timeout=5)
+        assert constructor.exitcode == 0
+        assert holder.exitcode == 0
+    finally:
+        release_holder.set()
+        for process in (constructor, holder):
+            if process.pid is not None:
+                process.join(timeout=3)
+                if process.is_alive():
+                    process.terminate()
+                    process.join(timeout=2)
+
+
+def test_constructor_holds_registry_os_lock_during_recovery_and_load(temp_repo):
+    PersistentIdentityRegistry(temp_repo)
+    context = multiprocessing.get_context("spawn")
+    probe_ready = context.Event()
+    attempt_probe = context.Event()
+    probe_attempted = context.Event()
+    probe_acquired = context.Event()
+    probe = context.Process(
+        target=_probe_registry_lock_process,
+        args=(temp_repo, probe_ready, attempt_probe, probe_attempted, probe_acquired),
+    )
+    recovery_entered = context.Event()
+    release_recovery = context.Event()
+    load_entered = context.Event()
+    release_load = context.Event()
+    constructor_completed = context.Event()
+    outcome = context.Queue()
+    constructor = context.Process(
+        target=_pause_registry_constructor_process,
+        args=(
+            temp_repo,
+            recovery_entered,
+            release_recovery,
+            load_entered,
+            release_load,
+            constructor_completed,
+            outcome,
+        ),
+    )
+    try:
+        probe.start()
+        assert probe_ready.wait(timeout=5)
+        constructor.start()
+        assert recovery_entered.wait(timeout=5)
+
+        attempt_probe.set()
+        assert probe_attempted.wait(timeout=5)
+        assert probe_acquired.wait(timeout=0.5) is False
+
+        release_recovery.set()
+        assert load_entered.wait(timeout=5)
+        assert probe_acquired.wait(timeout=0.5) is False
+
+        release_load.set()
+        assert constructor_completed.wait(timeout=5)
+        assert outcome.get(timeout=2) == "constructed"
+        assert probe_acquired.wait(timeout=5)
+        constructor.join(timeout=5)
+        probe.join(timeout=5)
+        assert constructor.exitcode == 0
+        assert probe.exitcode == 0
+    finally:
+        release_recovery.set()
+        release_load.set()
+        attempt_probe.set()
+        for process in (constructor, probe):
+            if process.pid is not None:
+                process.join(timeout=3)
+                if process.is_alive():
+                    process.terminate()
+                    process.join(timeout=2)
+
+
+def test_constructor_does_not_consume_active_writer_staging_and_loads_commit(temp_repo):
+    initial = PersistentIdentityRegistry(temp_repo)
+    with initial.transaction():
+        initial.sync_with_workspace({"seed.py"}, set())
+    assert initial.get_module_id("seed.py") == "1/1"
+
+    context = multiprocessing.get_context("spawn")
+    staged = context.Event()
+    release_writer = context.Event()
+    writer_completed = context.Event()
+    writer_outcome = context.Queue()
+    writer = context.Process(
+        target=_pause_registry_writer_replace_process,
+        args=(temp_repo, staged, release_writer, writer_completed, writer_outcome),
+    )
+    constructor_started = context.Event()
+    recovery_entered = context.Event()
+    constructor_completed = context.Event()
+    constructor_outcome = context.Queue()
+    constructor = context.Process(
+        target=_observe_registry_constructor_process,
+        args=(
+            temp_repo,
+            constructor_started,
+            recovery_entered,
+            constructor_completed,
+            constructor_outcome,
+        ),
+    )
+    try:
+        writer.start()
+        assert staged.wait(timeout=5)
+
+        marker = initial.transaction_file
+        temporary_files = {
+            name: path.with_suffix(".json.tmp")
+            for name, path in initial.files.items()
+        }
+        assert marker.exists()
+        assert all(path.exists() for path in temporary_files.values())
+        marker_before = marker.read_bytes()
+        staged_before = {
+            name: path.read_bytes() for name, path in temporary_files.items()
+        }
+
+        constructor.start()
+        assert constructor_started.wait(timeout=5)
+        assert recovery_entered.wait(timeout=0.5) is False
+        assert marker.read_bytes() == marker_before
+        assert {
+            name: path.read_bytes() for name, path in temporary_files.items()
+        } == staged_before
+
+        release_writer.set()
+        assert writer_completed.wait(timeout=5)
+        writer_result = writer_outcome.get(timeout=2)
+        assert writer_result == ("committed", "2/1")
+        assert recovery_entered.wait(timeout=5)
+        assert constructor_completed.wait(timeout=5)
+        constructor_result = constructor_outcome.get(timeout=2)
+        assert constructor_result == (
+            "ok",
+            {"seed.py": "1/1", "during_write.py": "2/1"},
+        )
+        assert not marker.exists()
+        assert not any(path.exists() for path in temporary_files.values())
+        writer.join(timeout=5)
+        constructor.join(timeout=5)
+        assert writer.exitcode == 0
+        assert constructor.exitcode == 0
+    finally:
+        release_writer.set()
+        for process in (constructor, writer):
+            if process.pid is not None:
+                process.join(timeout=3)
+                if process.is_alive():
+                    process.terminate()
+                    process.join(timeout=2)
+
+
+@pytest.mark.parametrize("failure_stage", ["recovery", "load"])
+def test_constructor_releases_registry_lock_after_recovery_or_load_failure(
+    temp_repo, failure_stage
+):
+    PersistentIdentityRegistry(temp_repo)
+    context = multiprocessing.get_context("spawn")
+    lock_acquired = context.Event()
+    failed = context.Event()
+    release_failure = context.Event()
+    failure_outcome = context.Queue()
+    failing_process = context.Process(
+        target=_fail_registry_constructor_process,
+        args=(
+            temp_repo,
+            failure_stage,
+            lock_acquired,
+            failed,
+            release_failure,
+            failure_outcome,
+        ),
+    )
+    probe_started = context.Event()
+    probe_completed = context.Event()
+    probe_outcome = context.Queue()
+    probe = context.Process(
+        target=_probe_registry_constructor_process,
+        args=(temp_repo, probe_started, probe_completed, probe_outcome),
+    )
+    try:
+        failing_process.start()
+        assert lock_acquired.wait(timeout=5)
+        assert failed.wait(timeout=5)
+        assert failure_outcome.get(timeout=2) == (
+            "failed",
+            failure_stage,
+            f"injected {failure_stage} failure",
+        )
+
+        probe.start()
+        assert probe_started.wait(timeout=5)
+        assert probe_completed.wait(timeout=2)
+        assert probe_outcome.get(timeout=2)[0] == "ok"
+        probe.join(timeout=5)
+        assert probe.exitcode == 0
+    finally:
+        release_failure.set()
+        for process in (probe, failing_process):
+            if process.pid is not None:
+                process.join(timeout=3)
+                if process.is_alive():
+                    process.terminate()
+                    process.join(timeout=2)
+
+
+def test_independent_registry_instances_share_the_same_os_lock_path(temp_repo):
+    first = PersistentIdentityRegistry(temp_repo)
+    second = PersistentIdentityRegistry(temp_repo)
+
+    assert first.registry_dir == second.registry_dir
+    assert first.lock_file == second.lock_file
+    assert first.lock_file.resolve() == second.lock_file.resolve()
