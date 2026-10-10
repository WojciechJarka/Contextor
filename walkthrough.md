# L32H2F3A_MIGRATION_RACE_RED_REGRESSIONS

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\tests\test_live_state_store.py — test-only changes.
- C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py — test-only changes.
- C:\Temp\Contextor_Repo\walkthrough.md — report only; excluded from source/test change accounting.

Git worktree has exactly the two authorized test files modified. Production files are clean. No changes were made to tests\test_full_analysis_coordination.py.

## SOURCE_VERIFICATION

Contextor MCP was used first. The current source was fetched with get_symbol_implementation(mode="fetch", include=["implementation"]); the FileState consumer methods were fetched with the documented methods selection. All fetches reported implementation_is_complete=true and no_partial_symbol_source=true. The latest fetches report canonical_state=fresh, workspace_sync=verified, canonical_revision=260, and fresh diagnostics with zero cycles.

Exact current source locations:

- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py::migrate_legacy_snapshot, lines 2375–2409.
- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py::save_snapshot, lines 1507–1874.
- C:\Temp\Contextor_Repo\contextor\mcp\runtime.py::_engine_cache_transaction, lines 286–295.
- C:\Temp\Contextor_Repo\contextor\mcp\runtime.py::get_or_init_engine, lines 311–419.
- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py::acquire_full_analysis, lines 410–588; release_full_analysis, lines 591–610.
- C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py::FileStateManager.__init__, lines 317–323; _load, lines 325–407.

The complete current migration implementation is:

~~~~python
def migrate_legacy_snapshot(repo_root: str | Path) -> Path:
    """Copy a verified path-keyed snapshot into its repo-ID cache directory."""

    from contextor.core.paths import legacy_repo_cache_dir, repo_cache_dir
    from contextor.core.repository_identity import require_repository_identity

    root = Path(repo_root).expanduser().resolve()
    identity = require_repository_identity(root)
    target = repo_cache_dir(root)
    if read_metadata(target) is not None:
        return target

    legacy = legacy_repo_cache_dir(root)
    if legacy == target:
        return target
    loaded = load_snapshot(legacy)
    if loaded is None:
        return target

    state, metadata = loaded
    save_snapshot(
        state,
        target,
        metadata.state_id,
        writer=f"migration:{metadata.writer}",
        repo_id=identity.repo_id,
        root_path=identity.root_path,
        revision_floor=metadata.revision,
    )
    legacy_file_state = legacy / "file_state.json"
    target_file_state = target / "file_state.json"
    if legacy_file_state.is_file() and not target_file_state.exists():
        target_file_state.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_file_state, target_file_state)
    return target
~~~~

The cache transaction source is:

~~~~python
@contextmanager
def _engine_cache_transaction(root: Path | str) -> Iterator[str]:
    root_key = _engine_cache_key(root)
    with _engine_cache_locks_guard:
        lock = _engine_cache_locks.get(root_key)
        if lock is None:
            lock = threading.RLock()
            _engine_cache_locks[root_key] = lock
    with lock:
        yield root_key
~~~~

The complete get_or_init_engine body is 109 lines and was fetched without preview/truncation. The relevant literal control-flow anchors are:

~~~~python
root = Path(root).expanduser().resolve()
with _engine_cache_transaction(root) as root_key:
    ...
    if not engine:
        ...
        from contextor.core.live_state import migrate_legacy_snapshot, read_metadata
        ...
        cache_dir = str(migrate_legacy_snapshot(root))
~~~~

migrate_legacy_snapshot does not acquire full_analysis.lock; it calls save_snapshot directly, then copies the legacy unversioned FileState if the target file_state.json path does not exist. get_or_init_engine enters _engine_cache_transaction before this fallback call.

save_snapshot was fetched completely. Its actual writer acquires the per-snapshot lock with _acquire_lock(lock_file). Exact-generation writes create versioned state/FileState files, replace the metadata pointer, set committed=True, return metadata, then release the snapshot lock in finally. Migration calls it without exact_revision, so migration publishes the ordinary target snapshot before its separate legacy FileState copy.

The complete FileState loader was fetched. It selects engine_state.meta.json["file_state_file"] when present; otherwise it reads file_state.json. A referenced generation must contain _meta and match the engine metadata revision/state ID to become trusted. This source contract matches the Race B assertions.

## RACE_A_RED_EVIDENCE

New test: tests/test_live_state_store.py::test_migration_does_not_enter_snapshot_write_while_full_analysis_lease_is_held.

- Process A acquired the real full_analysis.lock through acquire_full_analysis and signaled the parent only after acquisition.
- Process B began migrate_legacy_snapshot against the same verified-identity temporary repository.
- A wrapper signaled entry at the migration's save_snapshot boundary and then delegated to the real save_snapshot; it did not replace writer coordination.
- snapshot_write_entered=true while Process A still held the lease. The assertion failed at tests/test_live_state_store.py:2675, proving entry by synchronization events rather than by comparing final revisions.
- After that observation, both holds were released; both spawned processes exited cleanly and reported released / completed. No worker remained alive.

Result: expected RED. The valid legacy snapshot had revision 1 and target snapshot metadata was absent before the race.

## RACE_B_RED_EVIDENCE

New test: tests/test_live_state_store.py::test_migration_does_not_publish_legacy_filestate_after_newer_generation_commit.

Controlled order:

1. Migration's real save_snapshot returned after committing the migrated target snapshot. A wrapper paused before returning to the caller and before the legacy FileState conditional.
2. The test committed a newer exact generation through the real save_snapshot.
3. The test resumed migration and observed the legacy shutil.copy2.

Observed order from the test: migration_snapshot_saved → newer_generation_committed → legacy_file_state_copy_committed. The test failed at tests/test_live_state_store.py:2827 because the stale legacy copy was published after the newer generation.

Recorded state:

- Migration metadata before the interleaving: revision 2, state ID legacy-state, empty file_state_file; target file_state.json absent.
- New generation: revision 3, same state ID, metadata pointer to file_state.r3.<token>.json.
- After migration: metadata still referenced the revision-3 versioned FileState; the versioned FileState bytes were unchanged.
- The stale legacy bytes were copied into physical target file_state.json after the revision-3 commit.
- FileStateManager loaded the metadata-referenced versioned file, reported revision 3 and baseline_status="trusted", and contained current.py size 11.

Classification: stale physical unversioned extra is proved; consumer-visible inconsistency is not observed. The metadata-referenced current FileState remained trusted.

## RACE_C_RED_EVIDENCE

New test: tests/test_mcp_incremental_hydration.py::test_legacy_migration_writer_admission_precedes_mcp_cache_lock.

The real get_or_init_engine fallback was run with only the migration callback instrumented to pause. A second thread attempted the same actual _engine_cache_transaction.

Recorded event sequence:

cache_acquired(mcp-hydration) → migration_callback(mcp-hydration) → cache_acquired(same-cache-probe).

The second cache transaction remained blocked until the paused callback resumed, then acquired the lock. The observed callback state was full_analysis_held_at_migration=false; there was no full_analysis_acquired event from the initializer. The regression failed at tests/test_mcp_incremental_hydration.py:1515 because the current path has no writer admission before the cache RLock.

The test does not itself acquire a full-analysis lease while a cache lock is held. Its wrappers only delegate if production code invokes the real coordinator API.

Result: expected RED; the source and test establish cache-before-migration ordering and absence of an outer full-analysis lease on this current path.

## LEGACY_COMPATIBILITY_BASELINE

Selected migration/FileState compatibility command result: 5 passed, 1 warning (5.64s).

Selected nodes:

- tests/test_live_state_store.py::test_legacy_snapshot_migrates_to_repo_id_cache_without_deleting_source — extended assertions pass for repository identity, valid state ID, revision increment, loaded state, copied FileState bytes/content, and legacy source retention.
- tests/test_live_state_store.py::test_migration_does_not_write_when_valid_target_metadata_exists — pass; the writer was replaced with a forbidden-call assertion and was not called.
- tests/test_live_state_store.py::test_legacy_filestate_without_meta_loads_entries_but_remains_unverified — pass.
- tests/test_mcp_incremental_hydration.py::test_local_exact_generation_migrates_legacy_filestate_and_state_id — both existing_state_id parameters pass.

The new focused gate ran only three race nodes and the existing-target no-write node: 3 failed, 1 passed. The three failures are the expected RED observations above; the no-write regression passed. Race C was rerun after improving its failure evidence and remained expected RED (1 failed). The only warning was an Authlib deprecation warning from the installed test dependency.

## EXACT_INTERLEAVING_SCHEDULES

- A: Parent creates identity and valid legacy snapshot; spawned A acquires the actual repository lease and signals; spawned B signals start and attempts migration; B signals at the real snapshot-writer boundary; parent records whether that happened while A still owns the lease; parent releases both events; processes join with bounded waits and unconditional release/terminate cleanup.
- B: Migration's real snapshot writer returns and signals a pause before the caller reaches its FileState conditional; the test commits revision 3 with the real exact-generation writer and records metadata/FileState bytes; it releases migration; the copy wrapper records any physical unversioned copy; the thread joins.
- C: Initializer enters the real per-root cache transaction and pauses in the actual fallback callback; second thread signals immediately before entering the same real transaction; the test records non-acquisition during the pause; release lets both threads finish. All waits are bounded.

No timing sleep is used to create the interleavings. Bounded event waits only observe exclusion while the opposing owner is explicitly held.

## ACTUAL_FILESTATE_AND_METADATA_OBSERVATIONS

| Observation | Before competing generation | Newer generation committed | After migration resumes |
|---|---|---|---|
| engine_state.meta.json revision | 2 | 3 | 3 |
| state_id | legacy-state | legacy-state | legacy-state |
| file_state_file | empty | file_state.r3.<token>.json | same revision-3 filename |
| metadata-referenced FileState bytes | none | recorded versioned bytes | same bytes |
| target file_state.json | absent | absent | present with original stale legacy bytes |
| FileState consumer | not yet loaded | points to revision 3 | trusted revision 3; current.py size 11 |

The final combined focused run recorded the exact metadata pointer filename as file_state.r3.3c26d1bb6a3b4934b011ca38b178d57c.json. The legacy unversioned FileState bytes, UTF-8 without a trailing newline, were:

~~~~json
{
  "_meta": {
    "state_id": "legacy-state",
    "revision": 1
  },
  "files": {
    "legacy.py": {
      "size": 6
    }
  }
}
~~~~

The metadata-referenced revision-3 FileState bytes, also UTF-8 without a trailing newline, were:

~~~~json
{
  "_meta": {
    "state_id": "legacy-state",
    "revision": 3
  },
  "files": {
    "current.py": {
      "size": 11
    }
  }
}
~~~~

The test records and byte-compares both payloads before and after migration resumes. The legacy source bytes and copied target bytes are identical; the versioned FileState bytes and metadata file bytes remain unchanged after the stale extra copy.

## LOCK_ORDER_PROOF

- Contextor returned the complete _engine_cache_transaction and get_or_init_engine symbols with workspace_sync=verified.
- Current get_or_init_engine acquires the per-repository threading.RLock before entering its if not engine fallback.
- Current migration calls the real snapshot writer inside that fallback and contains no full-analysis acquisition.
- Race C records cache acquisition before migration callback; a second cache transaction cannot acquire until callback release.
- Race A uses the actual acquire_full_analysis API in a separate process and observes the migration writer boundary while that lease remains held.

## NESTED_LEASE_HAZARD

Current source proves no nested full-analysis acquisition: neither get_or_init_engine nor migrate_legacy_snapshot calls acquire_full_analysis. The proved current condition is cache-first migration without the canonical full-analysis lease. No test performed an acquisition from inside the held cache transaction. Whether later code adds a nested acquisition is outside this current-source result.

## MINIMUM_PATCH_BOUNDARIES

Source boundaries implicated by the regressions; this is evidence scope, not an implementation proposal:

- C:\Temp\Contextor_Repo\contextor\core\live_state\store.py, migrate_legacy_snapshot lines 2375–2409; actual snapshot commit owner save_snapshot lines 1507–1874.
- C:\Temp\Contextor_Repo\contextor\mcp\runtime.py, _engine_cache_transaction lines 286–295 and get_or_init_engine lines 311–419.
- C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_lease.py, acquire_full_analysis lines 410–588 and release_full_analysis lines 591–610.
- C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py, FileStateManager.__init__ lines 317–323 and _load lines 325–407.

No production file is authorized or changed by this task.

## SOURCE_SYNC_VERIFICATION

Contextor complete-source fetches after the test runs reported workspace_sync=verified for migrate_legacy_snapshot, save_snapshot, get_or_init_engine, _engine_cache_transaction, acquire_full_analysis, release_full_analysis, and FileStateManager.__init__ / _load. The canonical state remained fresh at revision 260, with cycles count 0 and availability fresh.

LIVE revision advanced from 257 to 260. get_live_events(after_revision=257) reported continuity="continuous", resync_required=false, and three desktop_watcher UPDATED events only for the two authorized Python test files (the hydration test file was updated twice). The final hydration-file event had blast_radius_state="deferred" with zero affected modules; this did not set resync. This is direct watcher evidence for the authorized test edits, not a production-code edit.

py_compile passed for both changed test files. git diff --check passed. Git emitted only the line-ending notice that LF in tests/test_mcp_incremental_hydration.py will be replaced by CRLF on a future Git touch. git diff --quiet confirmed no diff in the production files listed above.

No full repository pytest, full analysis, restart, commit, reset, checkout, or manual update_file was run.

## FILES_CHANGED

- C:\Temp\Contextor_Repo\tests\test_live_state_store.py
- C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py

walkthrough.md is the report-only file.

## ACTUAL_DIFF

## FULL_DIFFS

The following are the complete Git diffs for every changed test file. walkthrough.md is excluded.

~~~~diff
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index b084f20..7b47623 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -2,9 +2,11 @@
 
 from concurrent.futures import ThreadPoolExecutor
 from copy import deepcopy
+import json
 import multiprocessing
 import os
 from pathlib import Path
+import threading
 import time
 from types import SimpleNamespace
 
@@ -2503,8 +2505,15 @@ def test_legacy_snapshot_migrates_to_repo_id_cache_without_deleting_source(
     repo = tmp_path / "repo"
     repo.mkdir()
     legacy = legacy_repo_cache_dir(repo)
-    save_snapshot({"value": 7}, legacy, "legacy-state", writer="desktop")
-    (legacy / "file_state.json").write_text('{"files": {}}', encoding="utf-8")
+    legacy_metadata = save_snapshot(
+        {"value": 7}, legacy, "legacy-state", writer="desktop"
+    )
+    legacy_file_state = legacy / "file_state.json"
+    legacy_file_state.write_text(
+        json.dumps({"legacy.py": {"size": 4}}, indent=2),
+        encoding="utf-8",
+    )
+    legacy_file_state_bytes = legacy_file_state.read_bytes()
     registry = PersistentIdentityRegistry(str(repo))
 
     target = migrate_legacy_snapshot(repo)
@@ -2517,10 +2526,352 @@ def test_legacy_snapshot_migrates_to_repo_id_cache_without_deleting_source(
     assert target == repo_cache_dir(repo)
     assert loaded is not None and loaded[0] == {"value": 7}
     assert loaded[1].repo_id == registry.repo_id
+    assert loaded[1].state_id == "legacy-state"
+    assert loaded[1].revision == legacy_metadata.revision + 1
     assert (target / "file_state.json").is_file()
+    assert (target / "file_state.json").read_bytes() == legacy_file_state_bytes
+    migrated_file_state = FileStateManager(str(target))
+    assert "legacy.py" in migrated_file_state._state
+    assert migrated_file_state.baseline_status == "untrusted"
     assert (legacy / "engine_state.pkl").is_file()
 
 
+def _migration_race_full_analysis_holder(
+    repo_text, cache_text, lease_held, release_lease, results
+):
+    os.environ["CONTEXTOR_CACHE_DIR"] = cache_text
+    from contextor.core.analysis.full_analysis_coordinator import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+
+    lease = None
+    try:
+        lease = acquire_full_analysis(
+            repo_text,
+            owner="migration_race_full_writer",
+            writer_kind="full_analysis",
+            timeout=5.0,
+        )
+        lease_held.set()
+        if not release_lease.wait(15):
+            raise TimeoutError("full-analysis lease hold expired")
+        results.put({"worker": "lease", "status": "released"})
+    except BaseException as exc:
+        results.put({"worker": "lease", "status": "error", "error": repr(exc)})
+    finally:
+        if lease is not None:
+            release_full_analysis(lease)
+
+
+def _migration_race_migrate_worker(
+    repo_text,
+    cache_text,
+    migration_started,
+    snapshot_write_entered,
+    allow_snapshot_write,
+    results,
+):
+    os.environ["CONTEXTOR_CACHE_DIR"] = cache_text
+    import contextor.core.live_state.store as store
+
+    real_save_snapshot = store.save_snapshot
+
+    def observe_snapshot_write(*args, **kwargs):
+        snapshot_write_entered.set()
+        if not allow_snapshot_write.wait(15):
+            raise TimeoutError("migration snapshot write hold expired")
+        return real_save_snapshot(*args, **kwargs)
+
+    store.save_snapshot = observe_snapshot_write
+    try:
+        migration_started.set()
+        target = store.migrate_legacy_snapshot(repo_text)
+        results.put({"worker": "migration", "status": "completed", "target": str(target)})
+    except BaseException as exc:
+        results.put({"worker": "migration", "status": "error", "error": repr(exc)})
+    finally:
+        store.save_snapshot = real_save_snapshot
+
+
+def test_migration_does_not_enter_snapshot_write_while_full_analysis_lease_is_held(
+    tmp_path, monkeypatch
+):
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = PersistentIdentityRegistry(str(repo))
+    assert identity.repo_id
+
+    legacy = legacy_repo_cache_dir(repo)
+    legacy_metadata = save_snapshot(
+        {"value": 7}, legacy, "legacy-state", writer="desktop"
+    )
+    assert load_snapshot(legacy) is not None
+    target = repo_cache_dir(repo)
+    assert read_metadata(target) is None
+
+    context = multiprocessing.get_context("spawn")
+    lease_held = context.Event()
+    release_lease = context.Event()
+    migration_started = context.Event()
+    snapshot_write_entered = context.Event()
+    allow_snapshot_write = context.Event()
+    results = context.Queue()
+    holder = context.Process(
+        target=_migration_race_full_analysis_holder,
+        args=(str(repo), str(cache_root), lease_held, release_lease, results),
+    )
+    migrator = context.Process(
+        target=_migration_race_migrate_worker,
+        args=(
+            str(repo),
+            str(cache_root),
+            migration_started,
+            snapshot_write_entered,
+            allow_snapshot_write,
+            results,
+        ),
+    )
+    processes = (holder, migrator)
+    early_snapshot_write = False
+    migration_reached_write = False
+    worker_results = []
+    try:
+        holder.start()
+        assert lease_held.wait(5), "Process A did not acquire full_analysis.lock"
+
+        migrator.start()
+        assert migration_started.wait(5), "Process B did not start legacy migration"
+        early_snapshot_write = snapshot_write_entered.wait(1.0)
+
+        # Release both explicit holds only after recording whether the real
+        # migration writer boundary was entered while Process A owned the lease.
+        release_lease.set()
+        allow_snapshot_write.set()
+        migration_reached_write = snapshot_write_entered.wait(5)
+
+        for process in processes:
+            process.join(timeout=10)
+        worker_results = [results.get(timeout=2) for _ in range(2)]
+    finally:
+        release_lease.set()
+        allow_snapshot_write.set()
+        for process in processes:
+            if process.pid is not None:
+                process.join(timeout=5)
+                if process.is_alive():
+                    process.terminate()
+                    process.join(timeout=5)
+        results.close()
+        results.join_thread()
+
+    assert migration_reached_write, f"migration did not reach save_snapshot: {worker_results}"
+    assert all(not process.is_alive() for process in processes)
+    assert all(process.exitcode == 0 for process in processes), worker_results
+    assert {result["status"] for result in worker_results} == {"released", "completed"}, worker_results
+    assert legacy_metadata.revision == 1
+    assert not early_snapshot_write, (
+        "migration entered the real save_snapshot boundary while another process "
+        "held the repository full_analysis.lock"
+    )
+
+
+def test_migration_does_not_publish_legacy_filestate_after_newer_generation_commit(
+    tmp_path, monkeypatch
+):
+    import contextor.core.live_state.store as store
+
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    registry = PersistentIdentityRegistry(str(repo))
+    identity = read_repository_identity(repo)
+    assert identity is not None and identity.repo_id == registry.repo_id
+
+    legacy = legacy_repo_cache_dir(repo)
+    target = repo_cache_dir(repo)
+    legacy_metadata = save_snapshot(
+        {"value": "legacy"}, legacy, "legacy-state", writer="desktop"
+    )
+    legacy_file_state = legacy / "file_state.json"
+    legacy_file_state.write_text(
+        json.dumps(
+            {
+                "_meta": {
+                    "state_id": legacy_metadata.state_id,
+                    "revision": legacy_metadata.revision,
+                },
+                "files": {"legacy.py": {"size": 6}},
+            },
+            indent=2,
+        ),
+        encoding="utf-8",
+    )
+    legacy_file_state_bytes = legacy_file_state.read_bytes()
+
+    real_store_save = store.save_snapshot
+    real_copy2 = store.shutil.copy2
+    migration_snapshot_returned = threading.Event()
+    resume_migration = threading.Event()
+    observations = {"order": [], "copy": []}
+    migration_outcome = []
+
+    def pause_after_migration_snapshot_save(*args, **kwargs):
+        metadata = real_store_save(*args, **kwargs)
+        if threading.current_thread().name == "legacy-migration":
+            observations["migration_metadata"] = metadata
+            observations["order"].append("migration_snapshot_saved")
+            migration_snapshot_returned.set()
+            if not resume_migration.wait(10):
+                raise TimeoutError("migration resume hold expired")
+        return metadata
+
+    def observe_legacy_file_state_copy(src, dst, *args, **kwargs):
+        result = real_copy2(src, dst, *args, **kwargs)
+        observations["copy"].append(
+            {"src": str(src), "dst": str(dst), "bytes": Path(dst).read_bytes()}
+        )
+        observations["order"].append("legacy_file_state_copy_committed")
+        return result
+
+    monkeypatch.setattr(store, "save_snapshot", pause_after_migration_snapshot_save)
+    monkeypatch.setattr(store.shutil, "copy2", observe_legacy_file_state_copy)
+
+    def run_migration():
+        try:
+            migration_outcome.append(migrate_legacy_snapshot(repo))
+        except BaseException as exc:
+            migration_outcome.append(exc)
+
+    migration = threading.Thread(target=run_migration, name="legacy-migration")
+    try:
+        migration.start()
+        assert migration_snapshot_returned.wait(5), "migration did not return from snapshot save"
+
+        migration_metadata = read_metadata(target)
+        assert migration_metadata is not None
+        assert migration_metadata.revision == legacy_metadata.revision + 1
+        assert migration_metadata.state_id == legacy_metadata.state_id
+        assert migration_metadata.file_state_file == ""
+        assert not (target / "file_state.json").exists()
+
+        next_revision = migration_metadata.revision + 1
+        new_file_state_payload = {
+            "_meta": {"state_id": migration_metadata.state_id, "revision": next_revision},
+            "files": {"current.py": {"size": 11}},
+        }
+        newer_metadata = save_snapshot(
+            {"value": "newer"},
+            target,
+            migration_metadata.state_id,
+            writer="competing_snapshot_writer",
+            repo_id=identity.repo_id,
+            root_path=identity.root_path,
+            exact_revision=next_revision,
+            file_state_payload=new_file_state_payload,
+        )
+        observations["order"].append("newer_generation_committed")
+        newer_metadata_bytes = (target / "engine_state.meta.json").read_bytes()
+        newer_file_state_path = target / newer_metadata.file_state_file
+        newer_file_state_bytes = newer_file_state_path.read_bytes()
+
+        resume_migration.set()
+        migration.join(timeout=10)
+    finally:
+        resume_migration.set()
+        migration.join(timeout=5)
+
+    assert not migration.is_alive(), "migration thread did not terminate"
+    assert len(migration_outcome) == 1 and isinstance(migration_outcome[0], Path), migration_outcome
+    assert observations["order"].index("newer_generation_committed") < (
+        observations["order"].index("legacy_file_state_copy_committed")
+        if "legacy_file_state_copy_committed" in observations["order"]
+        else len(observations["order"])
+    )
+
+    final_metadata = read_metadata(target)
+    assert final_metadata == newer_metadata
+    assert final_metadata.revision == next_revision
+    assert final_metadata.state_id == legacy_metadata.state_id
+    assert final_metadata.file_state_file == newer_metadata.file_state_file
+    assert (target / "engine_state.meta.json").read_bytes() == newer_metadata_bytes
+    assert newer_file_state_path.read_bytes() == newer_file_state_bytes
+    assert legacy_file_state_bytes == legacy_file_state.read_bytes()
+
+    legacy_target_file_state = target / "file_state.json"
+    assert legacy_target_file_state.is_file()
+    assert legacy_target_file_state.read_bytes() == legacy_file_state_bytes
+    assert observations["copy"] == [
+        {
+            "src": str(legacy_file_state),
+            "dst": str(legacy_target_file_state),
+            "bytes": legacy_file_state_bytes,
+        }
+    ]
+
+    loaded = load_snapshot(
+        target,
+        expected_repo_id=identity.repo_id,
+        expected_root_path=identity.root_path,
+    )
+    assert loaded is not None and loaded[0]["value"] == "newer"
+    loaded_file_state = FileStateManager(str(target))
+    assert loaded_file_state.state_id == newer_metadata.state_id
+    assert loaded_file_state.revision == newer_metadata.revision
+    assert loaded_file_state.baseline_status == "trusted"
+    assert loaded_file_state._state["current.py"].size == 11
+
+    assert "legacy_file_state_copy_committed" not in observations["order"], (
+        "migration published the stale unversioned legacy FileState after a newer "
+        f"generation committed; order={observations['order']}; "
+        f"metadata_file_state={final_metadata.file_state_file!r}; "
+        "the metadata-referenced FileState consumer remained trusted"
+    )
+
+
+def test_migration_does_not_write_when_valid_target_metadata_exists(
+    tmp_path, monkeypatch
+):
+    import contextor.core.live_state.store as store
+
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = read_repository_identity(repo)
+    if identity is None:
+        registry = PersistentIdentityRegistry(str(repo))
+        identity = read_repository_identity(repo)
+        assert identity is not None and identity.repo_id == registry.repo_id
+
+    legacy = legacy_repo_cache_dir(repo)
+    target = repo_cache_dir(repo)
+    save_snapshot({"value": "legacy"}, legacy, "legacy-state", writer="desktop")
+    target_metadata = save_snapshot(
+        {"value": "already-current"},
+        target,
+        "target-state",
+        writer="existing-target",
+        repo_id=identity.repo_id,
+        root_path=identity.root_path,
+    )
+    metadata_bytes = (target / "engine_state.meta.json").read_bytes()
+    state_bytes = (target / "engine_state.pkl").read_bytes()
+
+    def forbidden_migration_write(*_args, **_kwargs):
+        pytest.fail("migration wrote despite valid target metadata")
+
+    monkeypatch.setattr(store, "save_snapshot", forbidden_migration_write)
+    assert migrate_legacy_snapshot(repo) == target
+    assert read_metadata(target) == target_metadata
+    assert (target / "engine_state.meta.json").read_bytes() == metadata_bytes
+    assert (target / "engine_state.pkl").read_bytes() == state_bytes
+    assert not (target / "file_state.json").exists()
+
+
 def test_concurrent_writers_publish_complete_monotonic_snapshots(tmp_path):
     def publish(value):
         return save_snapshot({"value": value}, tmp_path, "same", writer=str(value)).revision
~~~~

### C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py

~~~~diff
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index 96671e6..644b570 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -1375,6 +1375,154 @@ def test_local_exact_generation_migrates_legacy_filestate_and_state_id(
     assert hydrated.state_manager.get_tracked_sha256(str(provider)) == tracked_sha
 
 
+def test_legacy_migration_writer_admission_precedes_mcp_cache_lock(
+    tmp_path, monkeypatch
+):
+    from contextlib import contextmanager
+    from contextor.core.analysis import full_analysis_lease
+
+    repo = tmp_path / "repo_migration_lock_order"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_provenance", {})
+    monkeypatch.setattr(mcp_runtime, "_live_sessions", {})
+    monkeypatch.setattr(mcp_runtime, "_live_journal_revisions", {})
+
+    callback_entered = threading.Event()
+    resume_callback = threading.Event()
+    cache_probe_attempted = threading.Event()
+    cache_probe_acquired = threading.Event()
+    initializer_cache_acquired = threading.Event()
+    events = []
+    active_leases = {}
+    observations = {}
+    event_lock = threading.Lock()
+    real_cache_transaction = mcp_runtime._engine_cache_transaction
+    real_acquire = coordinator.acquire_full_analysis
+    real_release = coordinator.release_full_analysis
+
+    def record(event, thread_name=None):
+        with event_lock:
+            events.append((event, thread_name or threading.current_thread().name))
+
+    @contextmanager
+    def observe_cache_transaction(root):
+        thread_name = threading.current_thread().name
+        if thread_name == "same-cache-probe":
+            cache_probe_attempted.set()
+        with real_cache_transaction(root) as root_key:
+            record("cache_acquired", thread_name)
+            if thread_name == "mcp-hydration":
+                initializer_cache_acquired.set()
+            elif thread_name == "same-cache-probe":
+                cache_probe_acquired.set()
+            yield root_key
+
+    def observe_acquire(*args, **kwargs):
+        lease = real_acquire(*args, **kwargs)
+        thread_id = threading.get_ident()
+        with event_lock:
+            active_leases[thread_id] = lease
+            events.append(("full_analysis_acquired", threading.current_thread().name))
+        return lease
+
+    def observe_release(lease):
+        thread_id = threading.get_ident()
+        with event_lock:
+            events.append(("full_analysis_released", threading.current_thread().name))
+        try:
+            return real_release(lease)
+        finally:
+            with event_lock:
+                active_leases.pop(thread_id, None)
+
+    def pause_migration(_root):
+        thread_id = threading.get_ident()
+        with event_lock:
+            events.append(("migration_callback", threading.current_thread().name))
+            observations["full_analysis_held_at_migration"] = thread_id in active_leases
+        callback_entered.set()
+        if not resume_callback.wait(10):
+            raise TimeoutError("migration callback hold expired")
+        raise RuntimeError("intentional migration callback stop")
+
+    monkeypatch.setattr(mcp_runtime, "_engine_cache_transaction", observe_cache_transaction)
+    monkeypatch.setattr(coordinator, "acquire_full_analysis", observe_acquire)
+    monkeypatch.setattr(coordinator, "release_full_analysis", observe_release)
+    monkeypatch.setattr(full_analysis_lease, "acquire_full_analysis", observe_acquire)
+    monkeypatch.setattr(full_analysis_lease, "release_full_analysis", observe_release)
+    monkeypatch.setattr(
+        "contextor.core.live_state.migrate_legacy_snapshot",
+        pause_migration,
+    )
+
+    initializer_outcome = []
+
+    def run_initializer():
+        try:
+            mcp_runtime.get_or_init_engine(repo.resolve())
+        except BaseException as exc:
+            initializer_outcome.append(exc)
+
+    def probe_same_cache_transaction():
+        with mcp_runtime._engine_cache_transaction(repo):
+            cache_probe_acquired.set()
+
+    initializer = threading.Thread(target=run_initializer, name="mcp-hydration")
+    cache_probe = threading.Thread(
+        target=probe_same_cache_transaction,
+        name="same-cache-probe",
+    )
+    try:
+        initializer.start()
+        assert callback_entered.wait(5), "get_or_init_engine did not reach migration fallback"
+        assert initializer_cache_acquired.is_set()
+
+        cache_probe.start()
+        assert cache_probe_attempted.wait(5), "second thread did not attempt the same cache transaction"
+        cache_probe_was_blocked = not cache_probe_acquired.wait(0.5)
+    finally:
+        resume_callback.set()
+        initializer.join(timeout=5)
+        if cache_probe.ident is not None:
+            cache_probe.join(timeout=5)
+
+    assert not initializer.is_alive(), "hydration thread did not terminate"
+    assert not cache_probe.is_alive(), "same-cache probe thread did not terminate"
+    assert len(initializer_outcome) == 1
+    assert isinstance(initializer_outcome[0], RuntimeError)
+    lease_positions = [
+        index for index, (event, owner) in enumerate(events)
+        if event == "full_analysis_acquired" and owner == "mcp-hydration"
+    ]
+    cache_positions = [
+        index for index, (event, owner) in enumerate(events)
+        if event == "cache_acquired" and owner == "mcp-hydration"
+    ]
+    migration_positions = [
+        index for index, (event, owner) in enumerate(events)
+        if event == "migration_callback" and owner == "mcp-hydration"
+    ]
+    assert cache_positions and migration_positions and cache_positions[0] < migration_positions[0], (
+        f"migration callback did not execute inside the MCP cache transaction: events={events}"
+    )
+    assert cache_probe_was_blocked, (
+        f"second thread acquired the same MCP cache RLock while migration was paused: {events}"
+    )
+    assert lease_positions and cache_positions and lease_positions[0] < cache_positions[0], (
+        "full_analysis.lock must be acquired before the MCP cache RLock; "
+        f"callback_had_full_analysis_lease={observations.get('full_analysis_held_at_migration')}; "
+        f"events={events}"
+    )
+    assert observations.get("full_analysis_held_at_migration") is True, (
+        "migration callback ran without a full_analysis lease owned by the "
+        f"get_or_init_engine thread; events={events}"
+    )
+
+
 def test_mcp_refreshes_its_engine_from_a_newer_shared_live_revision(tmp_path, monkeypatch):
     first = RepositoryAnalysisState(modules={"old": object()})
     second = RepositoryAnalysisState(modules={"new": object()})
~~~~

## FINAL_VERDICT

Three deterministic race regressions are RED against current production code; the selected migration compatibility baseline passes. No production or unauthorized test files changed. The race-B observation is a physical stale legacy FileState extra without consumer-visible corruption.

F3_RED_EVIDENCE_READY
