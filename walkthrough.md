# L33/L34 startup backfill test fixture repair

## CURRENT_HEAD
`99f9f0aac13e8f9c96a3eef1498b564e585a66ca` (`main`, `origin/main`). The test file matched its HEAD blob before editing.

## ROOT_CAUSE_CONFIRMATION
DIRECT_EVIDENCE: Contextor confirmed that the split-lineage loader in `contextor/core/live_state/store.py:2054` reads `module.path` from every active module in `raw_state.modules` and returns `None` on `AttributeError`. Both affected fixtures had `modules={"a.py": SimpleNamespace()}` with no path. The real `Module` dataclass supplies the required path; production validation remained unchanged.

## FILES_CHANGED
- `tests/test_live_state_ipc.py` — corrected only the two named startup backfill fixtures, added real-loader preconditions and a metadata-commit hit marker.
- `walkthrough.md` is this task report and is excluded from changed-file diffs.

## FULL_DIFFS
```diff
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 6a47ec6..ab6ec5b 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -1299,6 +1299,7 @@ def test_persistence_trace_operation_is_propagated_across_successful_real_update
 def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_path, monkeypatch):
     import contextor.core.live_state.runtime as runtime
     from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
+    from contextor.core.domain.module import Module
     from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
     from contextor.core.paths import repo_cache_dir
     from contextor.core.repository_identity import ensure_repository_identity
@@ -1309,7 +1310,14 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
     monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
     cache = repo_cache_dir(repo)
     state = RepositoryAnalysisState(
-        modules={"a.py": SimpleNamespace()},
+        modules={
+            "a.py": Module(
+                module_id="a.py",
+                path="a.py",
+                absolute_path=str(repo / "a.py"),
+                imports=[],
+            )
+        },
         reexport_facts_by_module={
             "a.py": {
                 "exporter": "a.py",
@@ -1328,6 +1336,20 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
         repo_id=identity.repo_id,
         root_path=identity.root_path,
     )
+    initial = load_snapshot(
+        cache,
+        "sid",
+        expected_repo_id=identity.repo_id,
+        expected_root_path=identity.root_path,
+    )
+    assert initial is not None
+    initial_state, initial_metadata = initial
+    assert initial_metadata.repo_id == identity.repo_id
+    assert initial_metadata.root_path == identity.root_path
+    assert initial_metadata.revision == metadata.revision
+    assert initial_state.modules["a.py"].path == "a.py"
+    assert initial_state.lineage_facts_state == "not_materialized"
+    assert initial_state.lineage_facts_by_source == {}
     manager = FileStateManager(str(cache))
     manager._state = {
         "a.py": FileState(10, 3, "aaa"),
@@ -1395,6 +1417,7 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
 def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_path, monkeypatch):
     import contextor.core.live_state.runtime as runtime
     from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
+    from contextor.core.domain.module import Module
     from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
     from contextor.core.paths import repo_cache_dir
     from contextor.core.repository_identity import ensure_repository_identity
@@ -1405,7 +1428,14 @@ def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_p
     monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
     cache = repo_cache_dir(repo)
     state = RepositoryAnalysisState(
-        modules={"a.py": SimpleNamespace()},
+        modules={
+            "a.py": Module(
+                module_id="a.py",
+                path="a.py",
+                absolute_path=str(repo / "a.py"),
+                imports=[],
+            )
+        },
         reexport_facts_by_module={
             "a.py": {
                 "exporter": "a.py",
@@ -1417,6 +1447,20 @@ def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_p
     )
     state.revision = 1
     metadata = save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
+    initial = load_snapshot(
+        cache,
+        "sid",
+        expected_repo_id=identity.repo_id,
+        expected_root_path=identity.root_path,
+    )
+    assert initial is not None
+    initial_state, initial_metadata = initial
+    assert initial_metadata.repo_id == identity.repo_id
+    assert initial_metadata.root_path == identity.root_path
+    assert initial_metadata.revision == metadata.revision
+    assert initial_state.modules["a.py"].path == "a.py"
+    assert initial_state.lineage_facts_state == "not_materialized"
+    assert initial_state.lineage_facts_by_source == {}
     manager = FileStateManager(str(cache))
     manager._state = {"a.py": FileState(10, 3, "aaa"), "b.py": FileState(20, 4, "bbb")}
     manager.save("sid", revision=metadata.revision)
@@ -1427,13 +1471,17 @@ def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_p
     monkeypatch.setattr(materialization, "ensure_module_usages", lambda _state: None)
     import contextor.core.live_state.store as store
     original_replace = store.os.replace
+    metadata_commit_hit = False
     def fail_only_authoritative_metadata_commit(source, target):
+        nonlocal metadata_commit_hit
         if Path(target).name == "engine_state.meta.json":
+            metadata_commit_hit = True
             raise RuntimeError("synthetic metadata commit failure")
         return original_replace(source, target)
     monkeypatch.setattr(store.os, "replace", fail_only_authoritative_metadata_commit)
     with pytest.raises(RuntimeError, match="synthetic metadata commit failure"):
         runtime.run_service(repo)
+    assert metadata_commit_hit
     assert read_metadata(cache).revision == metadata.revision
     assert load_snapshot(cache, "sid")[1].revision == metadata.revision
     reloaded = FileStateManager(str(cache))
```

## INITIAL_SNAPSHOT_LOAD_RESULT
PASS in both named tests: immediately after `save_snapshot`, the real `load_snapshot` returned the committed generation with the expected repository ID, root path and revision. Each loaded module has `path == "a.py"`; lineage state is `not_materialized` and the source mapping is `{}`.

## BACKFILL_SUCCESS_RESULT
PASS: `test_startup_backfill_preserves_filestate_content_and_revision_parity` retained its committed-reader identity checks and all existing FileState content/count and revision-parity assertions. The committed generation advanced by one revision.

## BACKFILL_FAILURE_INJECTION_RESULT
PASS: the local `metadata_commit_hit` marker was asserted after the synthetic `os.replace` error at `engine_state.meta.json`. Existing assertions confirmed the previous metadata/snapshot revision and FileState content/revision remained authoritative.

## TARGETED_TEST_RESULTS
- Exact two named startup backfill tests: `2 passed in 5.24s`.
- `tests/test_live_state_ipc.py`, `tests/test_live_state_store.py`, `tests/test_lineage_state_lifecycle.py`: `196 passed, 1 warning in 85.23s`. The warning is an external `AuthlibDeprecationWarning` from FastMCP's Authlib import.
- No full repository pytest suite was run.

## FINAL_VERDICT
`PASS` for the approved test-only correction and the specified targeted gate. `git diff --check` exited successfully. No production file, `store.py`, LIVE IPC, runtime code or snapshot schema changed; no service restart or manual `update_file` occurred.