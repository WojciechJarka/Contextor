# L32H2F3C2 — no-legacy fast-path regression

## FILES_CHANGED_THIS_TASK

- `C:\Temp\Contextor_Repo\contextor\mcp\runtime.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`

`C:\Temp\Contextor_Repo\walkthrough.md` is the task report and is excluded from source/test changes.

## SOURCE_PREFLIGHT

DIRECT_EVIDENCE: Contextor MCP fetched the complete current `_get_or_init_engine_locked`, `legacy_repo_cache_dir`, and `read_metadata` implementations at revision 284 with `workspace_sync=verified`. `load_snapshot` calls `read_metadata(cache_dir)` before loading state and returns `None` when metadata is absent; therefore a snapshot accepted by that loader cannot have metadata rejected by this gate. Exact replacement anchor matched the workspace. The source/test worktree was clean before this task; the prior L32H2F3C baseline was retained.

## NO_LEGACY_RED_RESULT

Two new parameterized regressions failed before production edit, as expected: `absent` and `invalid_metadata` each reached `acquire_full_analysis` and triggered the explicit forbidden-call assertion. Conditions included registered identity, no cached engine/LIVE, absent target metadata, and absent/invalid legacy metadata.

## EXACT_PATCH

Only the auditor-supplied replacement in `C:\Temp\Contextor_Repo\contextor\mcp\runtime.py::_get_or_init_engine_locked` was applied. It checks `legacy_repo_cache_dir(root) != Path(cache_dir)` and `read_metadata(legacy_dir) is not None` before returning `_MIGRATION_NEEDED` or invoking admitted migration. Existing metadata read, `load_engine_state`, cache hydration, lease, sentinel, and nested caller code remain unchanged.

## NO_LEGACY_GREEN_RESULT

The two new regressions pass. Each calls `get_or_init_engine` twice and observes `None` both times, no sentinel in public return, no full-analysis admission, no migration call, no FileStateManager/registry construction, no identity rewrite, and byte/mtime equality of the fixture's repository/cache files before and after.

## CANDIDATE_GATE_COMPATIBILITY

CONTRACT_PROVED from source: `load_snapshot` requires `read_metadata` to succeed. Metadata is only a candidate test, not proof that a complete legacy snapshot is valid; `migrate_legacy_snapshot` still validates via `load_snapshot` and rechecks target state after protected admission. Initial focused compatibility run exposed two old cold-path fixtures that had no legacy snapshot at all. Only those fixtures were given a valid legacy snapshot and an absent-target assertion; their lock-order and recheck assertions were not weakened.

## WARM_PATH_NO_ADMISSION

The warm cached-engine and healthy-LIVE tests pass with valid legacy metadata and absent target metadata; neither path invokes migration or requests a writer lease.

## REAL_MIGRATION_ADMISSION

Race C and concurrent cold migration tests pass after the fixture correction. Actual migration candidates still acquire the full-analysis lease and execute migration under the post-admission MCP cache lock. The cross-process waiting test confirms the cache lock remains available while admission waits.

## RACE_A_B_C_COMPATIBILITY

Race A (independent migration versus another process's full-analysis lease), Race B (newer generation/FileState preservation), and corrected Race C (two-phase cache/lease ordering) all pass. Cold fallback recheck and engine/revision pair tests pass.

## TARGETED_TEST_RESULTS

Final exact focused gate: **15 passed, 0 failed** across the new no-legacy cases and existing warm, LIVE, missing identity, genuine cold, concurrent, recheck, pair, Race A/B/C, cross-process lock exclusion, analysis-job cold refresh, and direct LIVE update cold refresh tests. `py_compile contextor/mcp/runtime.py`: PASS. `git diff --check` for both changed files: PASS, exit 0 (Git emitted only line-ending normalization warnings). No full repository suite was run.

## SOURCE_SYNC

Post-edit Contextor returned the complete patched `_get_or_init_engine_locked` implementation with `workspace_sync=verified` at canonical revision 287. The public getter blast radius reported 23 complete direct static consumers with verified source. Diagnostics: `cycles.count=0`, syntax errors 0.

## LIVE_REVISION_BEFORE_AFTER

Before 284, after 287. Desktop watcher recorded revisions 285 (test), 286 (production), and 287 (test); `continuity=continuous`, `resync_required=false`. No manual `update_file`, full analysis, or restart occurred.

## RESTART_REQUIRED

YES for existing serving processes that imported `contextor.mcp.runtime` before this edit. Source indexing and fresh pytest processes do not certify imported-code reload.

## FINAL_VERDICT

**L32H2F3C2 TARGETED PASS.** The no-legacy metadata fast path avoids writer admission, while real migration coordination and targeted races remain GREEN. L32H FINAL PASS is not claimed.

## FULL_DIFFS_FOR_ALL_CHANGED_FILES

### `C:\Temp\Contextor_Repo\contextor\mcp\runtime.py`

```diff
diff --git a/contextor/mcp/runtime.py b/contextor/mcp/runtime.py
index edbc74f..80d2a19 100644
--- a/contextor/mcp/runtime.py
+++ b/contextor/mcp/runtime.py
@@ -390,13 +390,22 @@ def _get_or_init_engine_locked(
         identity = read_repository_identity(root)
         if identity is None:
             return None
-        from contextor.core.paths import repo_cache_dir
+        from contextor.core.paths import (
+            legacy_repo_cache_dir,
+            repo_cache_dir,
+        )
 
         cache_dir = str(repo_cache_dir(root))
         if read_metadata(cache_dir) is None:
-            if not allow_migration:
-                return _MIGRATION_NEEDED
-            migrate_legacy_snapshot(root, _lease_held=True)
+            legacy_dir = legacy_repo_cache_dir(root)
+            migration_candidate = (
+                legacy_dir != Path(cache_dir)
+                and read_metadata(legacy_dir) is not None
+            )
+            if migration_candidate:
+                if not allow_migration:
+                    return _MIGRATION_NEEDED
+                migrate_legacy_snapshot(root, _lease_held=True)
         metadata = read_metadata(cache_dir)
         state = load_engine_state(
             cache_dir,
```

### `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`

```diff
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index b47eaf4..87d3002 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -1380,10 +1380,16 @@ def test_legacy_migration_writer_admission_precedes_mcp_cache_lock(
 ):
     from contextlib import contextmanager
     from contextor.core.analysis import full_analysis_lease
+    from contextor.core.paths import legacy_repo_cache_dir
 
     repo = tmp_path / "repo_migration_lock_order"
     repo.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
     PersistentIdentityRegistry(str(repo))
+    snapshot_store.save_snapshot(
+        {"legacy": True}, legacy_repo_cache_dir(repo), "legacy", writer="test"
+    )
+    assert read_metadata(repo_cache_dir(repo)) is None
     monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
     monkeypatch.setattr(mcp_runtime, "_live_engines", {})
     monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
@@ -1612,10 +1618,16 @@ def test_healthy_live_hydration_does_not_attempt_legacy_migration_or_writer_admi
 def test_cold_fallback_rechecks_cache_after_writer_admission(tmp_path, monkeypatch):
     from contextor.core import live_state
     from contextor.core.analysis import full_analysis_lease
+    from contextor.core.paths import legacy_repo_cache_dir
 
     root = tmp_path / "repo"
     root.mkdir()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
     PersistentIdentityRegistry(str(root))
+    snapshot_store.save_snapshot(
+        {"legacy": True}, legacy_repo_cache_dir(root), "legacy", writer="test"
+    )
+    assert read_metadata(repo_cache_dir(root)) is None
     root_key = str(root.resolve())
     cached = SimpleNamespace(state=SimpleNamespace(revision=9))
     admission_entered = threading.Event()
@@ -1790,6 +1802,77 @@ def test_missing_identity_and_missing_legacy_do_not_publish_migration(
     assert read_metadata(repo_cache_dir(root)) is None
 
 
+@pytest.mark.parametrize("legacy_dir_state", ["absent", "invalid_metadata"])
+def test_cold_getter_without_legacy_metadata_never_requests_writer_admission(
+    tmp_path, monkeypatch, legacy_dir_state
+):
+    from contextor.core import live_state
+    from contextor.core.analysis import full_analysis_lease, state_manager
+    from contextor.core.paths import legacy_repo_cache_dir
+    from contextor.core.repository_identity import read_repository_identity
+    from contextor.core.reporting_engine import persistent_registry
+
+    root = tmp_path / "repo"
+    root.mkdir()
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    PersistentIdentityRegistry(str(root))
+    identity = read_repository_identity(root)
+    assert identity is not None
+    legacy_dir = legacy_repo_cache_dir(root)
+    if legacy_dir_state == "invalid_metadata":
+        legacy_dir.mkdir(parents=True)
+        (legacy_dir / "engine_state.meta.json").write_text(
+            "{invalid-json", encoding="utf-8"
+        )
+    assert read_metadata(repo_cache_dir(root)) is None
+    assert read_metadata(legacy_dir) is None
+
+    def files_before_or_after():
+        return {
+            (str(path.relative_to(tmp_path)), path.read_bytes(), path.stat().st_mtime_ns)
+            for path in tmp_path.rglob("*")
+            if path.is_file()
+        }
+
+    before = files_before_or_after()
+    monkeypatch.setattr(live_state, "connect", lambda _root: None)
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+    monkeypatch.setattr(
+        full_analysis_lease,
+        "acquire_full_analysis",
+        lambda *_a, **_k: pytest.fail("no legacy metadata requires no writer lease"),
+    )
+    monkeypatch.setattr(
+        live_state,
+        "migrate_legacy_snapshot",
+        lambda *_a, **_k: pytest.fail("no legacy metadata requires no migration"),
+    )
+    monkeypatch.setattr(state_manager, "load_engine_state", lambda *_a, **_k: None)
+    monkeypatch.setattr(
+        state_manager,
+        "FileStateManager",
+        lambda *_a, **_k: pytest.fail("no state should construct FileStateManager"),
+    )
+    monkeypatch.setattr(
+        persistent_registry,
+        "PersistentIdentityRegistry",
+        lambda *_a, **_k: pytest.fail("no state should construct registry"),
+    )
+
+    for _ in range(2):
+        result = mcp_runtime.get_or_init_engine(root)
+        assert result is None
+        assert result is not mcp_runtime._MIGRATION_NEEDED
+
+    assert files_before_or_after() == before
+    assert read_repository_identity(root) == identity
+    assert read_metadata(repo_cache_dir(root)) is None
+    assert mcp_runtime._live_engines == {}
+    assert mcp_runtime._live_engine_revisions == {}
+
+
 def test_concurrent_cold_hydration_commits_one_migration_and_one_engine(
     tmp_path, monkeypatch
 ):
```

