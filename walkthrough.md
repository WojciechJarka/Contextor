# L32H2F3B_LEGACY_FILESTATE_STORE_COMMIT

## FILES_CHANGED_THIS_TASK

- `C:\Temp\Contextor_Repo\contextor\core\live_state\store.py`
- `C:\Temp\Contextor_Repo\tests\test_live_state_store.py`

`walkthrough.md` is the requested report and is excluded from source/test changes.

## SOURCE_PREFLIGHT

- Contextor MCP was discovered first, including available deferred tools. Current documentation was read for symbol implementation, call context, lineage, file edit context, live events, and source ranges. An initial documentation query used two unsupported section names; the corrected query used the documented sections and succeeded.
- Pre-edit Contextor fetched complete, non-partial implementations of `migrate_legacy_snapshot`, `save_snapshot`, `_acquire_lock`, `_release_lock`, and `read_metadata`. Each source response reported `workspace_sync=verified`, `canonical_state=fresh`, LIVE revision 261.
- Old-source anchors matched: no migration parameters; re-export validation before lock setup; `read_metadata(cache_dir)` after lock acquisition; non-exact state replace before metadata replace; separate legacy FileState copy after `save_snapshot` returns.
- Existing Race B node: `test_migration_does_not_publish_legacy_filestate_after_newer_generation_commit`.
- Pre-edit HEAD: `b231f7fe75cedf191ede17ad36b661f079714877`; pre-edit worktree clean. No source mismatch.

## CORRECTED_RACE_B_RED

The deterministic pause remains immediately after real migration `save_snapshot` returns. The test now distinguishes `copy2` staging from stable-target publication and observes the metadata replace boundary.

Command before the production edit:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_live_state_store.py::test_migration_does_not_publish_legacy_filestate_after_newer_generation_commit -q
```

Expected RED observed: exit 1, `1 failed`. Old production had published migration metadata before target FileState. Exact failure evidence:

```
AssertionError: migration save_snapshot returned before legacy FileState publication;
order=['migration_metadata_published', 'migration_snapshot_save_returned']
assert None == <legacy_file_state_bytes>
```

The corrected invariant no longer requires a late copy after the competing generation commit.

## FILESTATE_PRE_METADATA_COMMIT

`save_snapshot` stages the legacy FileState to a token-scoped temp, flushes/fsyncs, atomically replaces the stable unversioned target, then performs the existing metadata replace. Race B asserts FileState exists at return, stable publication precedes migration metadata, exactly one publication precedes the competing revision-3 commit, source bytes are unchanged, metadata and versioned revision-3 FileState bytes stay unchanged, and `FileStateManager` reads the revision-3 generation as trusted.

The test records the `copy2` destination as staging `.file_state.*.tmp`; it records final publication separately at `os.replace(..., target/file_state.json)`.

## STORE_LOCK_EXCLUSION

Source order is: acquire the existing OS store lock, read metadata, then evaluate `migration_only_if_absent`. The guard returns current metadata from inside the locked try/finally region.

The deterministic C regression pauses after migration's initial target check but before the real store call, commits a competing exact revision-1 generation, then resumes migration. It verifies unchanged metadata, state, versioned FileState bytes, no unversioned stale copy, and trusted FileState loading.

## MIGRATION_IF_ABSENT

The existing valid-target fast return remains. Migration passes the legacy FileState source and `migration_only_if_absent=True`; the locked second check closes the interval after the initial check. Existing valid-target no-write coverage and the concurrent-target barrier regression passed.

## FAILURE_ROLLBACK

Both injected failure regressions passed:

- FileState staging-copy failure raises before metadata publication; metadata and stable FileState are absent, and `load_snapshot` returns `None`.
- Metadata replace failure after stable FileState publication raises; the newly created stable FileState and staging temp are removed, metadata remains absent, and `load_snapshot` returns `None`.

The failure cleanup only removes the stable FileState when this transaction created it. The pre-existing non-exact state replace occurs earlier; an unreferenced `engine_state.pkl` may remain after a later failure. The tests establish no authoritative metadata/snapshot load, not orphan-file cleanup.

## LEGACY_COMPATIBILITY

Existing migration coverage passed: legacy source bytes are retained, source is not deleted, and the existing untrusted-baseline semantics remain for unversioned legacy data. New no-legacy-FileState coverage passed: migration succeeds without fabricating target `file_state.json`.

## EXACT_GENERATION_COMPATIBILITY

The migration source option is rejected when paired with an exact revision or without migration-only mode, before store mutation. Existing exact-generation state/FileState and split-lineage paths remain unchanged.

Passed regressions include exact revision binding/rules, FileState payload validation, schema-1.4 split-lineage roundtrip. Race B confirms revision-3 metadata and referenced FileState bytes are unchanged after migration resumes.

## GREEN_TEST_RESULTS

Corrected Race B, all new migration scenarios, and related migration/exact-generation checks:

```
9 passed in 2.70s
```

Covered Race B; target generation appearing before locked check; copy failure; metadata rollback; migration without legacy FileState; normal legacy migration; valid-target no-op; exact snapshot binding; schema-1.4 split-lineage roundtrip.

The first authoring run had two `RepositoryIdentityError` fixture failures before reaching injected persistence failures. Repository registration was added to those two fixtures; the final nine-node run passed.

Additional focused lock, FileState-loading, exact-revision, and exact FileState validation selection:

```
14 passed in 12.46s
```

It covered sequential/same-process/cross-process/dead-owner/stale-mtime lock behavior; concurrent snapshot writers; referenced-generation fail-closed and legacy FileState loading; exact revision rules and FileState metadata validation.

Static checks passed:

- `.venv\Scripts\python.exe -m py_compile contextor/core/live_state/store.py tests/test_live_state_store.py`
- `git diff --check -- contextor/core/live_state/store.py tests/test_live_state_store.py`

No full repository pytest run.

## REMAINING_RACE_A_C

Race A and Race C were not run or changed, as directed:

- `tests/test_live_state_store.py::test_migration_does_not_enter_snapshot_write_while_full_analysis_lease_is_held`
- `tests/test_mcp_incremental_hydration.py::test_legacy_migration_writer_admission_precedes_mcp_cache_lock`

This patch does not claim to resolve either admission/lock-order race. Their F3A baseline status is retained; no new execution result is claimed.

## SOURCE_SYNC

Post-edit Contextor fetched complete `save_snapshot` and `migrate_legacy_snapshot` implementations. Both reported `implementation_is_complete=true`, `no_partial_symbol_source=true`, `workspace_sync=verified`, revision 265. The modified test symbol fetch was complete and also verified.

Module context reported fresh syntax diagnostics with zero errors. Diagnostics reported cycles fresh/count zero. Call context was complete/untruncated; lineage returned a complete metadata-consistent preview.

## LIVE_REVISION

The attachment listed revision 260. Actual first current pre-edit LIVE read was revision 261, with a continuous event for the prior `tests/test_mcp_incremental_hydration.py` edit. Post-edit events:

- 262: `tests/test_live_state_store.py` UPDATED
- 263: `contextor/core/live_state/store.py` UPDATED
- 264: `tests/test_live_state_store.py` UPDATED
- 265: `tests/test_live_state_store.py` UNCHANGED

Final event evidence: activity epoch `9e9a2a2edcb046bba00df0850244ad36`, `continuity=continuous`, `resync_required=false`. No process restart.

## FINAL_VERDICT

`L32H2F3B_SCOPED_PATCH_AND_TARGETED_REGRESSIONS_PASS`.

Corrected Race B failed on old production and passed after the patch. New migration scenarios and selected existing lock, FileState, and exact-generation regressions passed. Compile and whitespace checks passed. Race A/C remain open by scope; this is not an F3 or overall L32H final pass.

## FULL_DIFFS

Complete task diff for every changed source/test file follows. The report file is excluded.

```diff
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 4db0456..88666c8 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -1516,6 +1516,8 @@ def save_snapshot(
     exact_revision: int | None = None,
     file_state_payload: dict[str, Any] | None = None,
     previous_state: Any = None,
+    migration_file_state_source: str | Path | None = None,
+    migration_only_if_absent: bool = False,
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
@@ -1539,6 +1541,15 @@ def save_snapshot(
             "canonical re-export facts."
         )
 
+    if migration_file_state_source is not None and (
+        exact_revision is not None
+        or not migration_only_if_absent
+    ):
+        raise ValueError(
+            "Migration FileState source requires a non-exact "
+            "migration-only snapshot commit."
+        )
+
     state_file, meta_file, lock_file = _paths(cache_dir)
     state_file.parent.mkdir(parents=True, exist_ok=True)
     lock_fd = _acquire_lock(lock_file)
@@ -1551,9 +1562,15 @@ def save_snapshot(
     generation_lineage_chunks: list[Path] = []
     reusable_lineage_sources: dict[str, Any] = {}
     committed = False
+    migration_file_state_target = state_file.parent / "file_state.json"
+    migration_file_state_temp = state_file.parent / f".file_state.{token}.tmp"
+    migration_file_state_created = False
 
     try:
         current = read_metadata(cache_dir)
+        if migration_only_if_absent and current is not None:
+            return current
+
         normalized_root = (
             str(Path(root_path).expanduser().resolve())
             if root_path
@@ -1832,6 +1849,22 @@ def save_snapshot(
                 state_file,
             )
 
+        if migration_file_state_source is not None:
+            source_file = Path(migration_file_state_source)
+            if (
+                source_file.is_file()
+                and not migration_file_state_target.exists()
+            ):
+                shutil.copy2(source_file, migration_file_state_temp)
+                with migration_file_state_temp.open("ab") as stream:
+                    stream.flush()
+                    os.fsync(stream.fileno())
+                os.replace(
+                    migration_file_state_temp,
+                    migration_file_state_target,
+                )
+                migration_file_state_created = True
+
         os.replace(
             meta_tmp,
             meta_file,
@@ -1871,6 +1904,17 @@ def save_snapshot(
                 except OSError:
                     pass
 
+        if not committed and migration_file_state_created:
+            try:
+                migration_file_state_target.unlink(missing_ok=True)
+            except OSError:
+                pass
+
+        try:
+            migration_file_state_temp.unlink(missing_ok=True)
+        except OSError:
+            pass
+
         _release_lock(lock_fd)
 
 
@@ -2400,10 +2444,7 @@ def migrate_legacy_snapshot(repo_root: str | Path) -> Path:
         repo_id=identity.repo_id,
         root_path=identity.root_path,
         revision_floor=metadata.revision,
+        migration_file_state_source=legacy / "file_state.json",
+        migration_only_if_absent=True,
     )
-    legacy_file_state = legacy / "file_state.json"
-    target_file_state = target / "file_state.json"
-    if legacy_file_state.is_file() and not target_file_state.exists():
-        target_file_state.parent.mkdir(parents=True, exist_ok=True)
-        shutil.copy2(legacy_file_state, target_file_state)
     return target
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 7b47623..18e8548 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -2714,16 +2714,17 @@ def test_migration_does_not_publish_legacy_filestate_after_newer_generation_comm
 
     real_store_save = store.save_snapshot
     real_copy2 = store.shutil.copy2
+    real_replace = store.os.replace
     migration_snapshot_returned = threading.Event()
     resume_migration = threading.Event()
-    observations = {"order": [], "copy": []}
+    observations = {"order": [], "copy": [], "publication": []}
     migration_outcome = []
 
     def pause_after_migration_snapshot_save(*args, **kwargs):
         metadata = real_store_save(*args, **kwargs)
         if threading.current_thread().name == "legacy-migration":
             observations["migration_metadata"] = metadata
-            observations["order"].append("migration_snapshot_saved")
+            observations["order"].append("migration_snapshot_save_returned")
             migration_snapshot_returned.set()
             if not resume_migration.wait(10):
                 raise TimeoutError("migration resume hold expired")
@@ -2731,14 +2732,40 @@ def test_migration_does_not_publish_legacy_filestate_after_newer_generation_comm
 
     def observe_legacy_file_state_copy(src, dst, *args, **kwargs):
         result = real_copy2(src, dst, *args, **kwargs)
+        destination = Path(dst)
+        event = (
+            "legacy_file_state_published"
+            if destination == target / "file_state.json"
+            else "legacy_file_state_staged"
+        )
         observations["copy"].append(
-            {"src": str(src), "dst": str(dst), "bytes": Path(dst).read_bytes()}
+            {"src": str(src), "dst": str(destination), "bytes": destination.read_bytes()}
         )
-        observations["order"].append("legacy_file_state_copy_committed")
+        if event == "legacy_file_state_published":
+            observations["publication"].append(
+                {"src": str(src), "dst": str(destination), "bytes": destination.read_bytes()}
+            )
+        observations["order"].append(event)
+        return result
+
+    def observe_replace(src, dst):
+        result = real_replace(src, dst)
+        destination = Path(dst)
+        if destination == target / "file_state.json":
+            observations["publication"].append(
+                {"src": str(src), "dst": str(destination), "bytes": destination.read_bytes()}
+            )
+            observations["order"].append("legacy_file_state_published")
+        elif (
+            destination.name == "engine_state.meta.json"
+            and threading.current_thread().name == "legacy-migration"
+        ):
+            observations["order"].append("migration_metadata_published")
         return result
 
     monkeypatch.setattr(store, "save_snapshot", pause_after_migration_snapshot_save)
     monkeypatch.setattr(store.shutil, "copy2", observe_legacy_file_state_copy)
+    monkeypatch.setattr(store.os, "replace", observe_replace)
 
     def run_migration():
         try:
@@ -2756,7 +2783,11 @@ def test_migration_does_not_publish_legacy_filestate_after_newer_generation_comm
         assert migration_metadata.revision == legacy_metadata.revision + 1
         assert migration_metadata.state_id == legacy_metadata.state_id
         assert migration_metadata.file_state_file == ""
-        assert not (target / "file_state.json").exists()
+        target_file_state = target / "file_state.json"
+        observations["file_state_at_migration_return"] = (
+            target_file_state.read_bytes() if target_file_state.is_file() else None
+        )
+        observations["order_at_migration_return"] = list(observations["order"])
 
         next_revision = migration_metadata.revision + 1
         new_file_state_payload = {
@@ -2786,11 +2817,26 @@ def test_migration_does_not_publish_legacy_filestate_after_newer_generation_comm
 
     assert not migration.is_alive(), "migration thread did not terminate"
     assert len(migration_outcome) == 1 and isinstance(migration_outcome[0], Path), migration_outcome
-    assert observations["order"].index("newer_generation_committed") < (
-        observations["order"].index("legacy_file_state_copy_committed")
-        if "legacy_file_state_copy_committed" in observations["order"]
-        else len(observations["order"])
+    migration_return_order = observations["order_at_migration_return"]
+    assert observations["file_state_at_migration_return"] == legacy_file_state_bytes, (
+        "migration save_snapshot returned before legacy FileState publication; "
+        f"order={migration_return_order}"
     )
+    assert (
+        "legacy_file_state_published" in migration_return_order
+        and "migration_metadata_published" in migration_return_order
+        and "migration_snapshot_save_returned" in migration_return_order
+        and migration_return_order.index("legacy_file_state_published")
+        < migration_return_order.index("migration_metadata_published")
+        < migration_return_order.index("migration_snapshot_save_returned")
+    ), f"FileState/metadata publication order was incorrect: {migration_return_order}"
+    assert observations["order"].count("legacy_file_state_published") == 1, (
+        "migration copied or replaced the unversioned target FileState again; "
+        f"order={observations['order']}"
+    )
+    assert observations["order"].index("legacy_file_state_published") < (
+        observations["order"].index("newer_generation_committed")
+    ), f"legacy FileState publication occurred after the competing commit: {observations['order']}"
 
     final_metadata = read_metadata(target)
     assert final_metadata == newer_metadata
@@ -2804,13 +2850,23 @@ def test_migration_does_not_publish_legacy_filestate_after_newer_generation_comm
     legacy_target_file_state = target / "file_state.json"
     assert legacy_target_file_state.is_file()
     assert legacy_target_file_state.read_bytes() == legacy_file_state_bytes
+    assert observations["publication"] == [
+        {
+            "src": str(observations["publication"][0]["src"]),
+            "dst": str(legacy_target_file_state),
+            "bytes": legacy_file_state_bytes,
+        }
+    ]
     assert observations["copy"] == [
         {
             "src": str(legacy_file_state),
-            "dst": str(legacy_target_file_state),
+            "dst": str(observations["copy"][0]["dst"]),
             "bytes": legacy_file_state_bytes,
         }
     ]
+    assert Path(observations["copy"][0]["dst"]).parent == target
+    assert Path(observations["copy"][0]["dst"]).name.startswith(".file_state.")
+    assert Path(observations["copy"][0]["dst"]).name.endswith(".tmp")
 
     loaded = load_snapshot(
         target,
@@ -2824,12 +2880,221 @@ def test_migration_does_not_publish_legacy_filestate_after_newer_generation_comm
     assert loaded_file_state.baseline_status == "trusted"
     assert loaded_file_state._state["current.py"].size == 11
 
-    assert "legacy_file_state_copy_committed" not in observations["order"], (
-        "migration published the stale unversioned legacy FileState after a newer "
-        f"generation committed; order={observations['order']}; "
-        f"metadata_file_state={final_metadata.file_state_file!r}; "
-        "the metadata-referenced FileState consumer remained trusted"
+
+
+def test_migration_preserves_target_generation_created_before_store_lock_check(
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
+    real_save = store.save_snapshot
+    migration_save_entered = threading.Event()
+    resume_migration_save = threading.Event()
+    migration_result = []
+
+    def pause_before_store_lock(*args, **kwargs):
+        if threading.current_thread().name == "migration-before-store-check":
+            migration_save_entered.set()
+            if not resume_migration_save.wait(10):
+                raise TimeoutError("migration store-lock hold expired")
+        return real_save(*args, **kwargs)
+
+    monkeypatch.setattr(store, "save_snapshot", pause_before_store_lock)
+
+    def run_migration():
+        try:
+            migration_result.append(migrate_legacy_snapshot(repo))
+        except BaseException as exc:
+            migration_result.append(exc)
+
+    migration = threading.Thread(
+        target=run_migration,
+        name="migration-before-store-check",
+    )
+    try:
+        migration.start()
+        assert migration_save_entered.wait(5), "migration did not pass its initial target check"
+        assert read_metadata(target) is None
+
+        target_payload = {
+            "_meta": {"state_id": "concurrent-target", "revision": 1},
+            "files": {"current.py": {"size": 11}},
+        }
+        target_metadata = real_save(
+            {"value": "concurrent-target"},
+            target,
+            "concurrent-target",
+            writer="concurrent-target-writer",
+            repo_id=identity.repo_id,
+            root_path=identity.root_path,
+            exact_revision=1,
+            file_state_payload=target_payload,
+        )
+        metadata_bytes = (target / "engine_state.meta.json").read_bytes()
+        generation_state_bytes = (target / target_metadata.state_file).read_bytes()
+        generation_file_state_bytes = (target / target_metadata.file_state_file).read_bytes()
+
+        resume_migration_save.set()
+        migration.join(timeout=10)
+    finally:
+        resume_migration_save.set()
+        migration.join(timeout=5)
+
+    assert not migration.is_alive(), "migration thread did not terminate"
+    assert migration_result == [target], migration_result
+    assert read_metadata(target) == target_metadata
+    assert (target / "engine_state.meta.json").read_bytes() == metadata_bytes
+    assert (target / target_metadata.state_file).read_bytes() == generation_state_bytes
+    assert (target / target_metadata.file_state_file).read_bytes() == generation_file_state_bytes
+    assert not (target / "file_state.json").exists()
+    assert legacy_file_state.read_bytes() == legacy_file_state_bytes
+
+    loaded = load_snapshot(
+        target,
+        expected_repo_id=identity.repo_id,
+        expected_root_path=identity.root_path,
+    )
+    assert loaded is not None and loaded[0]["value"] == "concurrent-target"
+    loaded_file_state = FileStateManager(str(target))
+    assert loaded_file_state.baseline_status == "trusted"
+    assert loaded_file_state._state["current.py"].size == 11
+
+
+def test_migration_file_state_copy_failure_does_not_publish_metadata(
+    tmp_path, monkeypatch
+):
+    import contextor.core.live_state.store as store
+
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    legacy = legacy_repo_cache_dir(repo)
+    target = repo_cache_dir(repo)
+    save_snapshot({"value": "legacy"}, legacy, "legacy-state", writer="desktop")
+    legacy_file_state = legacy / "file_state.json"
+    legacy_file_state.write_text(
+        json.dumps({"legacy.py": {"size": 6}}, indent=2),
+        encoding="utf-8",
+    )
+
+    def fail_file_state_copy(*_args, **_kwargs):
+        raise OSError("injected migration FileState copy failure")
+
+    monkeypatch.setattr(store.shutil, "copy2", fail_file_state_copy)
+    with pytest.raises(OSError, match="injected migration FileState copy failure"):
+        migrate_legacy_snapshot(repo)
+
+    assert read_metadata(target) is None
+    assert not (target / "engine_state.meta.json").exists()
+    assert not (target / "file_state.json").exists()
+    assert not list(target.glob(".file_state.*.tmp"))
+    assert load_snapshot(target) is None
+
+
+def test_migration_metadata_failure_removes_newly_published_file_state(
+    tmp_path, monkeypatch
+):
+    import contextor.core.live_state.store as store
+
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    PersistentIdentityRegistry(str(repo))
+    legacy = legacy_repo_cache_dir(repo)
+    target = repo_cache_dir(repo)
+    save_snapshot({"value": "legacy"}, legacy, "legacy-state", writer="desktop")
+    legacy_file_state = legacy / "file_state.json"
+    legacy_file_state.write_text(
+        json.dumps({"legacy.py": {"size": 6}}, indent=2),
+        encoding="utf-8",
+    )
+
+    real_replace = store.os.replace
+    file_state_published = threading.Event()
+
+    def fail_metadata_replace_after_file_state(source, destination):
+        destination = Path(destination)
+        if destination == target / "file_state.json":
+            result = real_replace(source, destination)
+            file_state_published.set()
+            return result
+        if destination.name == "engine_state.meta.json":
+            raise OSError("injected migration metadata publication failure")
+        return real_replace(source, destination)
+
+    monkeypatch.setattr(store.os, "replace", fail_metadata_replace_after_file_state)
+    with pytest.raises(OSError, match="injected migration metadata publication failure"):
+        migrate_legacy_snapshot(repo)
+
+    assert file_state_published.is_set()
+    assert read_metadata(target) is None
+    assert not (target / "engine_state.meta.json").exists()
+    assert not (target / "file_state.json").exists()
+    assert not list(target.glob(".file_state.*.tmp"))
+    assert load_snapshot(target) is None
+
+
+def test_legacy_snapshot_migrates_without_legacy_file_state(tmp_path, monkeypatch):
+    cache_root = tmp_path / "cache"
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    legacy = legacy_repo_cache_dir(repo)
+    legacy_metadata = save_snapshot(
+        {"value": "legacy-without-file-state"},
+        legacy,
+        "legacy-state",
+        writer="desktop",
     )
+    registry = PersistentIdentityRegistry(str(repo))
+
+    target = migrate_legacy_snapshot(repo)
+    loaded = load_snapshot(
+        target,
+        expected_repo_id=registry.repo_id,
+        expected_root_path=str(repo),
+    )
+
+    assert loaded is not None and loaded[0]["value"] == "legacy-without-file-state"
+    assert loaded[1].state_id == legacy_metadata.state_id
+    assert loaded[1].revision == legacy_metadata.revision + 1
+    assert loaded[1].file_state_file == ""
+    assert not (target / "file_state.json").exists()
+    assert (legacy / "engine_state.pkl").is_file()
 
 
 def test_migration_does_not_write_when_valid_target_metadata_exists(
```
