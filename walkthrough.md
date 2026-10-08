# L37_L38_A2_INITIAL_LOCK_CREATION_RACE

## CURRENT_HEAD

`1d8f71309b770b39a3918a91e68aaea842c74e7d` at `C:\Temp\Contextor_Repo`. The worktree was clean before this task. No production file changed. `git diff --check` passed.

## CONTEXTOR_EVIDENCE

Contextor MCP was used before Git/source inspection. `get_file_edit_context` resolved `C:\Temp\Contextor_Repo\tests\test_live_state_store.py` as `tests.test_live_state_store`, with fresh syntax diagnostics at LIVE revision 5. `get_symbol_implementation` fetched complete existing `_snapshot_lock_holder` and `test_snapshot_lock_old_mtime_does_not_steal_ownership`, both `workspace_sync=verified`. The existing module-level imports already include `multiprocessing`, `time`, and `Path`; no import edit was needed.

## EXACT_TEST_ADDITION

The supplied module-level `_snapshot_lock_simultaneous_worker` was appended at `C:\Temp\Contextor_Repo\tests\test_live_state_store.py:2142`, immediately before the supplied `test_snapshot_lock_concurrent_initial_creation` at line 2166. The test uses `multiprocessing.get_context("spawn")`, starts from a nonexistent `engine_state.lock` pathname, and requires exact sorted outcomes `["acquired", "timeout"]` plus a remaining lock file. The code is shown in FULL_DIFFS.

## TEN_CONSECUTIVE_WINDOWS_RUNS

Each row is a separate project-venv pytest invocation of only `tests/test_live_state_store.py::test_snapshot_lock_concurrent_initial_creation`; each test invocation received its own `tmp_path` and asserted the lock pathname was initially absent.

| Run | Result | Pytest time | Exit |
| --- | --- | ---: | ---: |
| 1 | 1 passed | 3.29s | 0 |
| 2 | 1 passed | 2.94s | 0 |
| 3 | 1 passed | 2.68s | 0 |
| 4 | 1 passed | 2.51s | 0 |
| 5 | 1 passed | 2.86s | 0 |
| 6 | 1 passed | 2.47s | 0 |
| 7 | 1 passed | 2.51s | 0 |
| 8 | 1 passed | 2.47s | 0 |
| 9 | 1 passed | 2.52s | 0 |
| 10 | 1 passed | 2.49s | 0 |

No unexpected exception or result occurred in these ten runs.

## EXISTING_EIGHT_TARGETED_RESULTS

The eight existing snapshot-lock and persistence tests were rerun once, in a single focused invocation:

- `test_snapshot_lock_sequential_acquisition_leaves_stable_file`
- `test_snapshot_lock_same_process_contention_times_out`
- `test_snapshot_lock_cross_process_exclusion`
- `test_snapshot_lock_process_death_releases_ownership`
- `test_snapshot_lock_old_mtime_does_not_steal_ownership`
- `test_concurrent_writers_publish_complete_monotonic_snapshots`
- `test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock`
- `test_snapshot_roundtrip_increments_revision_and_records_writer`

Result: `8 passed in 10.45s`, exit code 0. The full pytest suite was not run.

## LIVE_WATCHER

Before editing, latest canonical LIVE revision was 5. After editing, `get_live_events(after_revision=5)` returned continuous revision 6, `resync_required=false`, with `operation=update_file`, `origin=desktop_watcher`, `status=UPDATED`, and exact path `C:\Temp\Contextor_Repo\tests\test_live_state_store.py`. The event reported `blast_radius_state=deferred`; syntax diagnostics were fresh with zero errors. No manual `update_file` call was made.

## FILES_CHANGED

- `C:\Temp\Contextor_Repo\tests\test_live_state_store.py`

No production file was edited. `walkthrough.md` is the required report.

## FULL_DIFFS

Complete actual diff for the only task-changed source/test file:

```diff
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 650149c..681d7a5 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -2137,3 +2137,68 @@ def test_mcp_and_desktop_resolve_the_same_repository_cache(monkeypatch, tmp_path
     monkeypatch.setattr("contextor.core.paths.app_cache_dir", lambda: tmp_path)
 
     assert analysis_jobs._mcp_cache_root(tmp_path / "repo") == tmp_path
+
+
+def _snapshot_lock_simultaneous_worker(lock_path, start, results):
+    import contextor.core.live_state.store as store
+
+    start.wait(10)
+
+    try:
+        fd = store._acquire_lock(
+            Path(lock_path),
+            timeout=0.3,
+        )
+    except TimeoutError:
+        results.put("timeout")
+        return
+    except BaseException as exc:
+        results.put(f"unexpected:{type(exc).__name__}:{exc}")
+        return
+
+    try:
+        time.sleep(0.6)
+        results.put("acquired")
+    finally:
+        store._release_lock(fd)
+
+
+def test_snapshot_lock_concurrent_initial_creation(tmp_path):
+    ctx = multiprocessing.get_context("spawn")
+    lock_path = tmp_path / "engine_state.lock"
+
+    assert not lock_path.exists()
+
+    start = ctx.Event()
+    results = ctx.Queue()
+
+    def verify(result_list):
+        assert sorted(result_list) == ["acquired", "timeout"]
+        assert lock_path.is_file()
+
+    processes = [
+        ctx.Process(
+            target=_snapshot_lock_simultaneous_worker,
+            args=(str(lock_path), start, results),
+        )
+        for _ in range(2)
+    ]
+
+    for process in processes:
+        process.start()
+
+    try:
+        start.set()
+        outcomes = [
+            results.get(timeout=15)
+            for _ in processes
+        ]
+        for process in processes:
+            process.join(10)
+        assert all(process.exitcode == 0 for process in processes)
+        verify(outcomes)
+    finally:
+        for process in processes:
+            if process.is_alive():
+                process.terminate()
+                process.join(5)
```

## ACTUAL_DIFF

The full actual task diff is reproduced verbatim in FULL_DIFFS.

## VERDICT

`TARGETED_PASS`: ten separate concurrent-initial-creation runs and the eight existing focused regressions passed on Windows with the project venv. This result is limited to the executed runs.
