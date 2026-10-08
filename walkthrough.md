# L37_L38_A2_OS_OWNED_SNAPSHOT_LOCK_IMPLEMENTATION

## CURRENT_HEAD

- Repository: `C:\Temp\Contextor_Repo`
- Pre-edit and current HEAD: `eab8c5bf9646d0e139c2c5e82e6b26b0ef04a066`.
- Pre-edit `git status --short` was empty. The two requested production SEARCH anchors each matched exactly once.
- Post-edit source verification: `contextor/core/live_state/store.py` equals HEAD plus the two supplied literal replacements, byte-for-byte after newline normalization. `git diff --check` passed.
- No MCP or LIVE restart was performed.

## PRE_EDIT_CONTEXTOR_EVIDENCE

- Contextor MCP was used before source/Git inspection. `get_symbol_implementation` returned complete `_acquire_lock` at `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1444-1459` and complete `save_snapshot` at lines 1462-1835, both with `workspace_sync=verified`, LIVE revision 1 and live provenance.
- `get_symbol_call_context` reported the one intra-module direct caller `save_snapshot` at original line 1499. A subsequent repository textual check found only this production call and the definition; no new production caller had appeared.
- `get_file_edit_context` identified module `contextor.core.live_state.store`, 22 direct module consumers and 144 transitive consumers. `get_artifact_blast_radius` identified 17 direct static consumers of `save_snapshot`; its artifact result for private `_acquire_lock` listed zero cross-module consumers. These static projections do not claim exhaustive dynamic-call coverage.
- The three retained snapshot regressions were fetched as complete test symbols from `C:\Temp\Contextor_Repo\tests\test_live_state_store.py` before editing: `test_snapshot_roundtrip_increments_revision_and_records_writer`, `test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock`, and `test_concurrent_writers_publish_complete_monotonic_snapshots`.
- Pre-edit `get_live_events` reported latest canonical revision 1, `resync_required=false`.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py`
- `C:\Temp\Contextor_Repo\tests\test_live_state_store.py`

`walkthrough.md` is this task report and is excluded from the production/test changed-file list under the repository instruction.

## OS_LOCK_BEHAVIOR

- The literal replacement at `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py:1444-1503` opens a stable lock pathname with `O_RDWR | O_CREAT`, initializes a one-byte region when empty, and acquires `msvcrt.locking(..., LK_NBLCK, 1)` on Windows or `fcntl.flock(..., LOCK_EX | LOCK_NB)` elsewhere. The returned integer is the owning descriptor.
- `_release_lock` unlocks and closes that descriptor. `save_snapshot` invokes it in its existing `finally` at line 1873. The pathname is not unlinked by this path.
- Test A acquired, released, reacquired and verified the file remains present. Test B verified same-process acquisition times out at 0.1 seconds while a separate descriptor owns the lock, then succeeds after release.
- The pre-existing failure-injection test now raises an assertion if cleanup attempts to unlink `engine_state.lock`. Its original persistence failure, unchanged metadata revision, and subsequent successful save assertions remain intact.

## CROSS_PROCESS_EXCLUSION

- `C:\Temp\Contextor_Repo\tests\test_live_state_store.py:199` uses `multiprocessing.get_context("spawn")`. Process A holds the descriptor; process B reports `TimeoutError` at 0.1 seconds. A remains alive. After A releases, a fresh spawned process acquires successfully and the lock pathname remains present.
- This test passed on Windows/Python 3.10.9. No unexpected locking `errno` or `winerror` occurred.

## PROCESS_DEATH_RECOVERY

- `C:\Temp\Contextor_Repo\tests\test_live_state_store.py:218` terminates process A while it owns the descriptor and without calling `_release_lock` in A. The lock pathname remains present. A new spawned process acquires successfully; no pathname unlink or timestamp manipulation occurs in this test.
- The first combined run was manually interrupted after three passing cases because the process-death test harness called `Event.set()` after the event-waiting owner had been terminated. Instrumentation reached successful acquisition by process B before that cleanup call. The obsolete test-harness call was removed. The isolated process-death case then passed, followed by the complete eight-test run.

## AGE_INDEPENDENCE

- `C:\Temp\Contextor_Repo\tests\test_live_state_store.py:234` sets the held lock file mtime one hour into the past. A second spawned process still times out; the original holder remains alive. After release, another spawned process acquires. No lock-path unlink occurs.
- This targeted Windows test passed.

## TARGETED_TEST_RESULTS

Command: `& .\.venv\Scripts\python.exe -m pytest -q` with only the eight exact `tests/test_live_state_store.py::` nodes below:

1. `test_snapshot_lock_sequential_acquisition_leaves_stable_file`
2. `test_snapshot_lock_same_process_contention_times_out`
3. `test_snapshot_lock_cross_process_exclusion`
4. `test_snapshot_lock_process_death_releases_ownership`
5. `test_snapshot_lock_old_mtime_does_not_steal_ownership`
6. `test_concurrent_writers_publish_complete_monotonic_snapshots`
7. `test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock`
8. `test_snapshot_roundtrip_increments_revision_and_records_writer`

Final result: `8 passed in 10.57s` (exit code 0). No full suite was run.

Post-edit Contextor `get_live_events(after_revision=1)` reported continuous revision progression 2-5, `resync_required=false`, with `desktop_watcher` `UPDATED` events for `store.py` at revision 2 and `test_live_state_store.py` at revisions 3-5. The store event reported `blast_radius_state=fresh`; later test-file events reported `deferred` blast radius. Subsequent `get_file_edit_context` calls at LIVE revision 5 reported fresh syntax diagnostics and no warnings for both files.

## UNRESOLVED_RISKS

- The POSIX `fcntl` branch was not executed on this Windows host.
- The running LIVE/backend process has not been restarted and may retain its previously imported `store.py`. A manual LIVE/backend restart is required before integration certification. This task did not authorize that restart.
- These tests establish the specified lock behavior; they do not certify power-loss durability or the broader L37/L38 publication transaction.

## IMPLEMENTATION_VERDICT

`TARGETED_PASS`: the two production replacements match the supplied literal patch, tests A-H pass, and the watcher observed both edited files. Integration certification remains pending a manual LIVE/backend restart.

## FULL_DIFFS

Complete raw `git diff --no-ext-diff -- contextor/core/live_state/store.py tests/test_live_state_store.py`:

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 2fb6986..393eeed 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -1442,22 +1442,66 @@ def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
 
 
 def _acquire_lock(lock_file: Path, timeout: float = 5.0) -> int:
+    """Acquire an OS-owned cross-process lock on a stable file."""
     deadline = time.monotonic() + timeout
-    while True:
-        try:
-            return os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
-        except (FileExistsError, PermissionError):
-            try:
-                if time.time() - lock_file.stat().st_mtime > 30:
-                    lock_file.unlink()
-                    continue
+    lock_file.parent.mkdir(parents=True, exist_ok=True)
+
+    fd = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o600)
+
+    try:
+        if os.fstat(fd).st_size == 0:
+            os.write(fd, b"\0")
+            os.fsync(fd)
+
+        while True:
+            os.lseek(fd, 0, os.SEEK_SET)
+
+            if os.name == "nt":
+                import msvcrt
+
+                try:
+                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
+                    return fd
+                except OSError:
+                    pass
+            else:
+                import fcntl
+
+                try:
+                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
+                    return fd
+                except BlockingIOError:
+                    pass
 
-            except FileNotFoundError:
-                continue
             if time.monotonic() >= deadline:
-                raise TimeoutError(f"Timed out waiting for LIVE state lock: {lock_file}")
+                raise TimeoutError(
+                    f"Timed out waiting for LIVE state lock: {lock_file}"
+                )
+
             time.sleep(0.02)
 
+    except BaseException:
+        os.close(fd)
+        raise
+
+
+def _release_lock(fd: int) -> None:
+    """Release the OS lock and close its owning descriptor."""
+    try:
+        os.lseek(fd, 0, os.SEEK_SET)
+
+        if os.name == "nt":
+            import msvcrt
+
+            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
+        else:
+            import fcntl
+
+            fcntl.flock(fd, fcntl.LOCK_UN)
+
+    finally:
+        os.close(fd)
+
 
 def save_snapshot(
     state: Any,
@@ -1826,13 +1870,7 @@ def save_snapshot(
                 except OSError:
                     pass
 
-        try:
-            os.close(lock_fd)
-        finally:
-            try:
-                lock_file.unlink()
-            except OSError:
-                pass
+        _release_lock(lock_fd)
 
 
 def _trace_snapshot_load_phase(
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 1e556a8..650149c 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -1,7 +1,10 @@
 """Unit and integration boundaries for the shared canonical LIVE snapshot store."""
 
 from concurrent.futures import ThreadPoolExecutor
+import multiprocessing
+import os
 from pathlib import Path
+import time
 from types import SimpleNamespace
 
 import pytest
@@ -98,6 +101,158 @@ def test_snapshot_roundtrip_increments_revision_and_records_writer(tmp_path):
     assert read_metadata(tmp_path) == metadata
 
 
+
+def _snapshot_lock_holder(lock_path, ready, release):
+    import contextor.core.live_state.store as store
+
+    fd = store._acquire_lock(Path(lock_path))
+    try:
+        ready.set()
+        release.wait(30)
+    finally:
+        store._release_lock(fd)
+
+
+def _snapshot_lock_probe(lock_path, timeout, connection):
+    import contextor.core.live_state.store as store
+
+    try:
+        try:
+            fd = store._acquire_lock(Path(lock_path), timeout=timeout)
+        except BaseException as exc:
+            connection.send(
+                (type(exc).__name__, str(exc), getattr(exc, "errno", None), getattr(exc, "winerror", None))
+            )
+        else:
+            try:
+                store._release_lock(fd)
+            except BaseException as exc:
+                connection.send(
+                    (type(exc).__name__, str(exc), getattr(exc, "errno", None), getattr(exc, "winerror", None))
+                )
+            else:
+                connection.send(("acquired",))
+    finally:
+        connection.close()
+
+
+def _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout):
+    receiving, sending = ctx.Pipe(duplex=False)
+    process = ctx.Process(target=_snapshot_lock_probe, args=(str(lock_path), timeout, sending))
+    process.start()
+    sending.close()
+    try:
+        assert receiving.poll(15), f"snapshot lock probe exited without a result: {process.exitcode}"
+        result = receiving.recv()
+        process.join(15)
+        assert process.exitcode == 0, result
+        return result
+    finally:
+        receiving.close()
+        if process.is_alive():
+            process.terminate()
+            process.join(5)
+
+
+def _start_spawned_snapshot_lock_holder(ctx, lock_path):
+    ready = ctx.Event()
+    release = ctx.Event()
+    process = ctx.Process(target=_snapshot_lock_holder, args=(str(lock_path), ready, release))
+    process.start()
+    if not ready.wait(15):
+        process.terminate()
+        process.join(5)
+        pytest.fail(f"snapshot lock holder did not acquire the lock: exitcode={process.exitcode}")
+    assert process.is_alive()
+    return process, release
+
+
+def test_snapshot_lock_sequential_acquisition_leaves_stable_file(tmp_path):
+    import contextor.core.live_state.store as store
+
+    lock_path = tmp_path / "engine_state.lock"
+    first = store._acquire_lock(lock_path)
+    store._release_lock(first)
+    assert lock_path.is_file()
+
+    second = store._acquire_lock(lock_path)
+    store._release_lock(second)
+    assert lock_path.is_file()
+
+
+def test_snapshot_lock_same_process_contention_times_out(tmp_path):
+    import contextor.core.live_state.store as store
+
+    lock_path = tmp_path / "engine_state.lock"
+    first = store._acquire_lock(lock_path)
+    try:
+        with pytest.raises(TimeoutError):
+            store._acquire_lock(lock_path, timeout=0.1)
+    finally:
+        store._release_lock(first)
+
+    second = store._acquire_lock(lock_path)
+    store._release_lock(second)
+    assert lock_path.is_file()
+
+
+def test_snapshot_lock_cross_process_exclusion(tmp_path):
+    ctx = multiprocessing.get_context("spawn")
+    lock_path = tmp_path / "engine_state.lock"
+    holder, release = _start_spawned_snapshot_lock_holder(ctx, lock_path)
+    try:
+        result = _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=0.1)
+        assert result[0] == "TimeoutError", result
+        assert holder.is_alive()
+    finally:
+        release.set()
+        holder.join(10)
+        if holder.is_alive():
+            holder.terminate()
+            holder.join(5)
+    assert holder.exitcode == 0
+    assert lock_path.is_file()
+    assert _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=1.0) == ("acquired",)
+
+
+def test_snapshot_lock_process_death_releases_ownership(tmp_path):
+    ctx = multiprocessing.get_context("spawn")
+    lock_path = tmp_path / "engine_state.lock"
+    holder, _ = _start_spawned_snapshot_lock_holder(ctx, lock_path)
+    try:
+        holder.terminate()
+        holder.join(10)
+        assert not holder.is_alive()
+        assert lock_path.is_file()
+        assert _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=1.0) == ("acquired",)
+    finally:
+        if holder.is_alive():
+            holder.terminate()
+            holder.join(5)
+
+
+def test_snapshot_lock_old_mtime_does_not_steal_ownership(tmp_path):
+    ctx = multiprocessing.get_context("spawn")
+    lock_path = tmp_path / "engine_state.lock"
+    holder, release = _start_spawned_snapshot_lock_holder(ctx, lock_path)
+    try:
+        old = time.time() - 3600
+        os.utime(lock_path, (old, old))
+        assert lock_path.stat().st_mtime < time.time() - 30
+        result = _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=0.1)
+        assert result[0] == "TimeoutError", result
+        assert holder.is_alive()
+    finally:
+        release.set()
+        holder.join(10)
+        if holder.is_alive():
+            holder.terminate()
+            holder.join(5)
+    assert holder.exitcode == 0
+    assert lock_path.is_file()
+    assert _run_spawned_snapshot_lock_probe(ctx, lock_path, timeout=1.0) == ("acquired",)
+
+
 def test_default_snapshot_publishes_final_pickle_via_temp_replace(tmp_path, monkeypatch):
     import contextor.core.live_state.store as store
 
@@ -125,7 +280,7 @@ def test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock(tmp_path,
     monkeypatch.setattr(store.os, "replace", failing_replace)
     def failing_unlink(self, *args, **kwargs):
         if self.name == "engine_state.lock":
-            return original_unlink(self, *args, **kwargs)
+            raise AssertionError("stable snapshot lock must not be unlinked")
         raise OSError("cleanup failure")
     monkeypatch.setattr(type(tmp_path), "unlink", failing_unlink)
     with pytest.raises(RuntimeError, match="authoritative persistence failure"):
```

## ACTUAL_DIFF

The complete actual diff for every production/test file listed in FILES_CHANGED is reproduced verbatim in FULL_DIFFS above.
