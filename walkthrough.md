# L32H2A_LOCAL_EXACT_GENERATION_PERSISTENCE

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py — exact literal replacement of `_persist_live_engine` only.
- C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py — focused exact-generation and failure regressions.
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py — existing roundtrip test now uses real `FileStateManager` instead of a legacy state-id-only stub; its persisted-state assertions remain and the tracked file roundtrip is asserted.
- C:\Temp\Contextor_Repo\walkthrough.md — this report; excluded from source/test diff accounting.
- C:\Temp\Contextor_Repo\tests\test_live_state_store.py — unchanged.

## SOURCE_CONTRACT_VERIFICATION

DIRECT_EVIDENCE: Before edits, Contextor MCP returned complete `_persist_live_engine` at lines 73-104, canonical revision 204, `canonical_state=fresh`, `workspace_sync=verified`, `provenance=live`. It used `save_engine_state` without exact revision, then `FileStateManager.save` as an independent write. Contextor returned complete `save_engine_state` with `exact_revision` and `file_state_payload`; complete `RepositoryAnalysisState.clone_for_update`; complete `FileStateManager.build_payload`; complete `read_metadata`. `read_metadata` is exported by `contextor.core.live_state.__init__`.

Contextor call context confirms the sole direct intra-module caller `contextor.mcp.tools.update_file::update_file` at the local fallback branch (line 224 before edit); blast radius reports two confirmed test consumers, `tests.test_mcp_incremental_hydration` and `tests.test_mcp_regressions`. Dynamic Python consumers are outside that static claim. No source mismatch with the literal patch was found. The public `update_file` wrapper and its persist-all-returned-statuses policy were not edited.

## RED_RESULT

Before the production edit, `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_incremental_hydration.py -k local_exact_generation` returned **10 failed, 6 deselected**. The new tests failed on old behavior: independent `FileStateManager.save`, absent exact generation, stale revision acceptance, invalid metadata bootstrap, mutation of original state during failed serialization, failed staging behavior, and missing legacy migration. The RED run was completed before the literal production replacement.

## GREEN_RESULT

After the literal replacement, the same focused selection returned **10 passed, 6 deselected**. The complete scoped gate then initially returned **130 passed, 1 failed**: `tests/test_mcp_regressions.py::test_incremental_live_state_persistence_roundtrips_for_restart` used a `SimpleNamespace` manager without the now-required `build_payload`. This was an obsolete storage fixture, so the test was changed to use real `FileStateManager` and to check tracked-file recovery. Its isolated rerun passed.

Final scoped gate: `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_incremental_hydration.py tests/test_mcp_regressions.py tests/test_live_state_store.py::test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock tests/test_live_state_store.py::test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite tests/test_live_state_store.py::test_exact_snapshot_rejects_file_state_payload_mismatches tests/test_live_state_store.py::test_exact_snapshot_revision_binds_embedded_state_and_metadata tests/test_live_state_store.py::test_referenced_filestate_generation_fail_closed_without_legacy_fallback tests/test_live_state_store.py::test_referenced_filestate_without_meta_fails_closed tests/test_live_state_store.py::test_legacy_filestate_without_meta_loads_entries_but_remains_unverified` returned **131 passed, 0 failed, 1 external Authlib deprecation warning** in 35.91 seconds. This includes the L32H1 returned-status test and the syntax-error/recovery hydration regression. No full repository suite was run.

Read-only `compile(...)` of `contextor\mcp\tools\update_file.py` returned `COMPILE_OK`. `git diff --check` on all authorized files returned exit 0, with only Git's working-copy LF/CRLF conversion notices.

## INITIAL_AND_SUCCESSOR_REVISIONS

DIRECT TEST EVIDENCE: With no existing metadata, local exact persistence commits revision 1. A hydrated engine then commits revision 2, retaining its state identity. Tests reject stale revisions independently in engine, state, and MCP cache before a new metadata pointer is published. The literal helper checks type and previous revision before building the candidate.

## STATE_ID_COMPATIBILITY

DIRECT TEST EVIDENCE: A legacy empty `state_id` is initialized from repository identity; a valid nonempty `legacy-valid-id` is retained. Both migrate to exact generation and hydrate with matching engine/FileState identity. CODE_PATH_PROVED: when committed metadata has a nonempty state ID, a conflicting nonempty engine or manager state ID raises before publication. That mismatch branch was inspected in the complete post-edit implementation but not separately failure-injected.

## EXACT_GENERATION_PUBLICATION

DIRECT TEST EVIDENCE: The metadata pointer references `engine_state.r1.*.pkl` and `file_state.r1.*.json`; both exist and the FileState `_meta` matches revision and state ID. Revision 2 uses different generation files. `FileStateManager.save` was patched to raise in the initial publication test and was not called. The helper passes a cloned state plus `manager.build_payload(state_id, next_revision)` to one exact `save_engine_state` call.

## FILESTATE_HYDRATION

DIRECT TEST EVIDENCE: After clearing the MCP engine cache, hydration restores matching state and manager revisions/state IDs and the tracked source file SHA-256. `has_changed` is false for the unchanged tracked file. Existing UPDATED, SYNTAX_ERROR, RECOVERED, early UNCHANGED, parsed UNCHANGED and structured ERROR fallback hydration regressions passed in the complete targeted file.

## SNAPSHOT_FAILURE_MATRIX

| Injected/checked condition | Result and evidence |
| --- | --- |
| Missing metadata | Exact generation 1 is committed with both generation files; tested. |
| Engine/state/cache revision stale | `RuntimeError` before publication; previous pointer bytes unchanged; three cases tested. |
| Existing invalid metadata file | `RuntimeError`; invalid file remains; tested. |
| Serializer failure | `save_engine_state` returns `None`, helper returns `False`; original engine state's revision/state_id and absent metadata remain unchanged; tested. |
| FileState generation write failure | Helper returns `False`; prior pointer bytes and prior generation remain loadable; original engine/manager revisions remain 1; tested. |
| Metadata `os.replace` failure | Helper returns `False`; prior pointer bytes and prior generation remain loadable; original engine/manager revisions remain 1; tested. |
| `FileStateManager.save` attempted | Test raises; initial exact publication succeeds, proving this old separate write is not called. |
| Exact snapshot revision/payload mismatch | Existing selected `test_live_state_store.py` regressions passed. |

The failure injections use isolated temporary repositories. They do not certify crash durability or concurrent writer exclusion.

## LEGACY_MIGRATION

DIRECT TEST EVIDENCE: Both blank-ID and valid nonempty-ID legacy non-exact snapshots with a separately stored `file_state.json` migrate on the next local persistence to revision 2 with referenced generation-specific FileState. The tracked SHA-256 survives hydration. No legacy file or snapshot was manipulated outside temporary test fixtures.

## SOURCE_SYNC_VERIFICATION

After edits, Contextor MCP returned the complete `_persist_live_engine` at lines 73-178 with `implementation_is_complete=true`, `no_partial_symbol_source=true`, canonical revision 207, `canonical_state=fresh`, `workspace_sync=verified`, and `provenance=live`. Its returned implementation matches the literal authorized replacement. The post-edit blast radius still reports the same two confirmed test consumer modules. The worktree inspection showed only the three authorized source/test files plus `walkthrough.md` modified; `tests/test_live_state_store.py` remained unchanged. Contextor source indexing does not prove the already-running MCP process reimported edited Python code.

## LIVE_REVISION_BEFORE_AFTER

Before edit: LIVE revision 204, activity epoch `9e9a2a2edcb046bba00df0850244ad36`, `resync_required=false`. After edit: revision 207 in the same activity epoch. `get_live_events(after_revision=204)` returned `continuity=continuous`, `resync_required=false` and three `desktop_watcher` UPDATED events: revision 205 for `tests\test_mcp_incremental_hydration.py`, revision 206 for `contextor\mcp\tools\update_file.py`, and revision 207 for `tests\test_mcp_regressions.py`. No manual `update_file` was called.

## REMAINING_LOCAL_ATOMICITY_RISKS

This stage does not establish rollback of a previously mutated local engine, isolation of `engine.update_file`, registry rollback, inter-request update/persist serialization, exclusion of an active LIVE writer, or power-loss durability. No claim of `LOCAL_ATOMICITY_FINAL_PASS` is made.

## RESTART_REQUIRED

The edited owner is imported MCP runtime code. A manual MCP serving-process reload is required before runtime certification of this new helper; it was not performed. LIVE watcher source synchronization and fresh-process pytest do not attest to imported-code reload in the existing MCP process. No Desktop or LIVE restart was performed.

## FINAL_VERDICT

**L32H2A_TARGETED_CODE_GATE_PASS; RUNTIME_RELOAD_PENDING.** The exact local snapshot/FileState generation publication contract and selected failure behavior pass the authorized targeted tests. This is not `LOCAL_ATOMICITY_FINAL_PASS`.

## FULL_DIFFS

The following are full, unabridged source/test diffs for every file modified in this task. `walkthrough.md` is the report and is excluded from source/test diff accounting.
### contextor/mcp/tools/update_file.py

```diff
diff --git a/contextor/mcp/tools/update_file.py b/contextor/mcp/tools/update_file.py
index 8bcde7e..a26645f 100644
--- a/contextor/mcp/tools/update_file.py
+++ b/contextor/mcp/tools/update_file.py
@@ -71,37 +71,111 @@ def _mcp_runtime_restart_required(target_file: Path) -> bool:
 
 
 def _persist_live_engine(root: Path, engine) -> bool:
-    """Persist incremental canonical state so the next MCP process can hydrate it."""
+    """Persist local state and FileState in one exact snapshot generation."""
     from contextor.core.analysis.state_manager import save_engine_state
+    from contextor.core.live_state import read_metadata
     from contextor.core.paths import repo_cache_dir
     from contextor.core.repository_identity import require_repository_identity
 
     identity = require_repository_identity(root)
     cache_dir = repo_cache_dir(root)
     cache_dir.mkdir(parents=True, exist_ok=True)
-    meta = save_engine_state(
-        engine.state,
-        str(cache_dir),
-        getattr(engine.state_manager, "state_id", ""),
-        writer="mcp",
-        repo_id=identity.repo_id,
-        root_path=identity.root_path,
-    )
-    if meta is not None:
-        new_rev = int(meta.revision)
-        with mcp_runtime._engine_cache_transaction(root) as root_key:
-            engine.revision = new_rev
-            if hasattr(engine.state, "revision"):
-                engine.state.revision = new_rev
-            mcp_runtime._live_engine_revisions[root_key] = new_rev
-            if hasattr(engine, "state_manager") and engine.state_manager:
-                engine.state_manager.revision = new_rev
-                if hasattr(engine.state_manager, "save"):
-                    engine.state_manager.save(
-                        getattr(engine.state_manager, "state_id", ""), revision=new_rev
+
+    manager = getattr(engine, "state_manager", None)
+    if manager is None or not callable(getattr(manager, "build_payload", None)):
+        raise RuntimeError(
+            "Local persistence requires a FileStateManager with build_payload."
+        )
+
+    with mcp_runtime._engine_cache_transaction(root) as root_key:
+        current = read_metadata(cache_dir)
+        metadata_path = cache_dir / "engine_state.meta.json"
+
+        if current is None and metadata_path.exists():
+            raise RuntimeError(
+                "Existing canonical snapshot metadata is invalid; "
+                "local persistence cannot bootstrap over it."
+            )
+
+        expected_previous_revision = (
+            int(current.revision) if current is not None else None
+        )
+
+        for revision_name, value in (
+            ("engine", getattr(engine, "revision", None)),
+            ("state", getattr(engine.state, "revision", None)),
+            ("cache", mcp_runtime._live_engine_revisions.get(root_key)),
+        ):
+            if value is None:
+                continue
+            if isinstance(value, bool) or type(value) is not int:
+                raise RuntimeError(
+                    f"Local {revision_name} revision is invalid."
+                )
+            if expected_previous_revision is None:
+                if value != 0:
+                    raise RuntimeError(
+                        f"Local {revision_name} revision has no committed baseline."
                     )
+            elif value != expected_previous_revision:
+                raise RuntimeError(
+                    f"Local {revision_name} revision differs from "
+                    "committed snapshot revision."
+                )
+
+        state_id = str(
+            (current.state_id if current is not None else "")
+            or getattr(engine.state, "state_id", "")
+            or getattr(manager, "state_id", "")
+            or identity.repo_id
+        )
+
+        if current is not None and current.state_id:
+            for existing_id in (
+                getattr(engine.state, "state_id", None),
+                getattr(manager, "state_id", None),
+            ):
+                if existing_id and str(existing_id) != current.state_id:
+                    raise RuntimeError(
+                        "Local state identity differs from committed snapshot."
+                    )
+
+        next_revision = (
+            expected_previous_revision + 1
+            if expected_previous_revision is not None
+            else 1
+        )
+
+        candidate = engine.state.clone_for_update()
+        payload = manager.build_payload(state_id, next_revision)
+
+        meta = save_engine_state(
+            candidate,
+            str(cache_dir),
+            state_id,
+            writer="mcp",
+            repo_id=identity.repo_id,
+            root_path=identity.root_path,
+            exact_revision=next_revision,
+            file_state_payload=payload,
+        )
+
+        if meta is None:
+            return False
+
+        if meta.revision != next_revision or meta.state_id != state_id:
+            raise RuntimeError(
+                "Exact local snapshot returned mismatching commit identity."
+            )
+
+        engine.revision = next_revision
+        engine.state.revision = next_revision
+        engine.state.state_id = state_id
+        manager.state_id = state_id
+        manager.revision = next_revision
+        mcp_runtime._live_engine_revisions[root_key] = next_revision
+
         return True
-    return False
 
 
 def _semantic_artifact_diff(old_artifacts: dict, new_artifacts: dict) -> dict:
```

### tests/test_mcp_incremental_hydration.py

```diff
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index 9bf8523..fe37c79 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -13,7 +13,12 @@ from contextor.core.analysis.incremental import engine as incremental_engine_mod
 from contextor.mcp import report_helpers
 from contextor.mcp import runtime as mcp_runtime
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
-from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
+from contextor.core.analysis.state_manager import (
+    FileStateManager,
+    RepositoryAnalysisState,
+    load_engine_state,
+    save_engine_state,
+)
 from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
 from contextor.core.paths import repo_cache_dir
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
@@ -26,7 +31,9 @@ from contextor.core.reference.shared import (
     materialize_reexport_facts_by_module,
     validate_reexport_facts_by_module,
 )
-from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
+from contextor.core.live_state import CanonicalLiveServer, LiveStateClient, read_metadata
+from contextor.core.live_state import store as snapshot_store
+from contextor.core.repository_identity import require_repository_identity
 from contextor.mcp.tools import update_file as update_file_module
 
 pytestmark = pytest.mark.live
@@ -84,6 +91,183 @@ def _rehydrate_local_engine(repo):
     return mcp_runtime.get_or_init_engine(repo.resolve())
 
 
+def test_local_exact_generation_initial_successor_and_filestate_hydration(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    cache_dir = repo_cache_dir(repo)
+    tracked_sha = engine.state_manager.get_tracked_sha256(str(provider))
+    assert tracked_sha
+
+    def forbidden_save(*_args, **_kwargs):
+        raise AssertionError("FileStateManager.save must not be called")
+
+    monkeypatch.setattr(engine.state_manager, "save", forbidden_save)
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    initial = read_metadata(cache_dir)
+    assert initial.revision == 1
+    assert initial.state_file.startswith("engine_state.r1.")
+    assert initial.file_state_file.startswith("file_state.r1.")
+    assert (cache_dir / initial.state_file).is_file()
+    initial_payload = json.loads((cache_dir / initial.file_state_file).read_text())
+    assert initial_payload["_meta"] == {"state_id": initial.state_id, "revision": 1}
+    assert initial_payload["files"][str(provider)]["sha256"] == tracked_sha
+    assert not (cache_dir / "file_state.json").exists()
+
+    hydrated = _rehydrate_local_engine(repo)
+    assert hydrated is not None
+    assert hydrated.state.revision == hydrated.state_manager.revision == 1
+    assert hydrated.state.state_id == hydrated.state_manager.state_id == initial.state_id
+    assert hydrated.state_manager.get_tracked_sha256(str(provider)) == tracked_sha
+    assert hydrated.state_manager.has_changed(str(provider)) is False
+
+    assert update_file_module._persist_live_engine(repo, hydrated) is True
+    successor = read_metadata(cache_dir)
+    assert successor.revision == 2
+    assert successor.state_id == initial.state_id
+    assert successor.state_file != initial.state_file
+    assert successor.file_state_file != initial.file_state_file
+    assert json.loads((cache_dir / successor.file_state_file).read_text())["_meta"] == {
+        "state_id": initial.state_id,
+        "revision": 2,
+    }
+
+
+@pytest.mark.parametrize("revision_owner", ["engine", "state", "cache"])
+def test_local_exact_generation_rejects_stale_revision_before_publication(
+    tmp_path, monkeypatch, revision_owner
+):
+    repo, _provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    cache_dir = repo_cache_dir(repo)
+    before = (cache_dir / "engine_state.meta.json").read_bytes()
+    if revision_owner == "engine":
+        engine.revision = 0
+    elif revision_owner == "state":
+        engine.state.revision = 0
+    else:
+        mcp_runtime._live_engine_revisions[str(repo.resolve())] = 0
+
+    with pytest.raises(RuntimeError, match="revision"):
+        update_file_module._persist_live_engine(repo, engine)
+    assert (cache_dir / "engine_state.meta.json").read_bytes() == before
+
+
+def test_local_exact_generation_rejects_invalid_existing_metadata(
+    tmp_path, monkeypatch
+):
+    repo, _provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    cache_dir = repo_cache_dir(repo)
+    metadata_path = cache_dir / "engine_state.meta.json"
+    metadata_path.write_text("{invalid", encoding="utf-8")
+    with pytest.raises(RuntimeError, match="metadata is invalid"):
+        update_file_module._persist_live_engine(repo, engine)
+    assert metadata_path.read_text(encoding="utf-8") == "{invalid"
+
+
+def test_local_exact_generation_serializer_failure_preserves_original_identity(
+    tmp_path, monkeypatch
+):
+    repo, _provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    before_revision = getattr(engine.state, "revision", None)
+    before_state_id = getattr(engine.state, "state_id", None)
+
+    def failing_dump(*_args, **_kwargs):
+        raise OSError("injected serializer failure")
+
+    monkeypatch.setattr(snapshot_store.pickle, "dump", failing_dump)
+    assert update_file_module._persist_live_engine(repo, engine) is False
+    assert getattr(engine.state, "revision", None) == before_revision
+    assert getattr(engine.state, "state_id", None) == before_state_id
+    assert read_metadata(repo_cache_dir(repo)) is None
+
+
+@pytest.mark.parametrize("failure_stage", ["file_state", "metadata_pointer"])
+def test_local_exact_generation_staging_failure_preserves_prior_generation(
+    tmp_path, monkeypatch, failure_stage
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    cache_dir = repo_cache_dir(repo)
+    before = (cache_dir / "engine_state.meta.json").read_bytes()
+    previous = read_metadata(cache_dir)
+    tracked_sha = engine.state_manager.get_tracked_sha256(str(provider))
+
+    if failure_stage == "file_state":
+        original_dump = snapshot_store.json.dump
+
+        def failing_dump(value, stream, *args, **kwargs):
+            if stream.name.endswith(".json") and "file_state.r2." in stream.name:
+                raise OSError("injected FileState generation failure")
+            return original_dump(value, stream, *args, **kwargs)
+
+        monkeypatch.setattr(snapshot_store.json, "dump", failing_dump)
+    else:
+        original_replace = snapshot_store.os.replace
+
+        def failing_replace(source, target):
+            if target.name == "engine_state.meta.json":
+                raise OSError("injected metadata pointer failure")
+            return original_replace(source, target)
+
+        monkeypatch.setattr(snapshot_store.os, "replace", failing_replace)
+
+    assert update_file_module._persist_live_engine(repo, engine) is False
+    assert (cache_dir / "engine_state.meta.json").read_bytes() == before
+    assert read_metadata(cache_dir) == previous
+    assert engine.state.revision == engine.revision == 1
+    assert engine.state_manager.revision == 1
+    loaded = load_engine_state(
+        str(cache_dir), previous.state_id,
+        expected_repo_id=require_repository_identity(repo).repo_id,
+        expected_root_path=repo,
+    )
+    assert loaded is not None and loaded.revision == 1
+    reloaded_manager = FileStateManager(str(cache_dir))
+    assert reloaded_manager.revision == 1
+    assert reloaded_manager.get_tracked_sha256(str(provider)) == tracked_sha
+
+
+@pytest.mark.parametrize("existing_state_id", ["", "legacy-valid-id"])
+def test_local_exact_generation_migrates_legacy_filestate_and_state_id(
+    tmp_path, monkeypatch, existing_state_id
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    cache_dir = repo_cache_dir(repo)
+    identity = require_repository_identity(repo)
+    baseline = save_engine_state(
+        engine.state, str(cache_dir), existing_state_id,
+        writer="mcp", repo_id=identity.repo_id, root_path=identity.root_path,
+    )
+    assert baseline is not None and baseline.revision == 1
+    engine.state_manager.save(existing_state_id, revision=1)
+    tracked_sha = engine.state_manager.get_tracked_sha256(str(provider))
+    assert not read_metadata(cache_dir).file_state_file
+
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    migrated = read_metadata(cache_dir)
+    assert migrated.revision == 2
+    assert migrated.state_id == (existing_state_id or identity.repo_id)
+    assert migrated.file_state_file.startswith("file_state.r2.")
+    assert (cache_dir / migrated.file_state_file).is_file()
+    hydrated = _rehydrate_local_engine(repo)
+    assert hydrated.state.state_id == hydrated.state_manager.state_id == migrated.state_id
+    assert hydrated.state_manager.revision == 2
+    assert hydrated.state_manager.get_tracked_sha256(str(provider)) == tracked_sha
+
+
 def test_mcp_refreshes_its_engine_from_a_newer_shared_live_revision(tmp_path, monkeypatch):
     first = RepositoryAnalysisState(modules={"old": object()})
     second = RepositoryAnalysisState(modules={"new": object()})
```

### tests/test_mcp_regressions.py

```diff
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 010bdeb..19eca67 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -2596,9 +2596,17 @@ def test_file_edit_context_prefers_fresh_live_graph_over_stale_saved_matrix(
 def test_incremental_live_state_persistence_roundtrips_for_restart(
     tmp_path, monkeypatch
 ):
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.paths import repo_cache_dir
+
     cache_root = tmp_path / "cache"
     monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
     registry = PersistentIdentityRegistry(str(tmp_path))
+    tracked_file = tmp_path / "tracked.py"
+    tracked_file.write_text("value = 1\n", encoding="utf-8")
+    state_manager = FileStateManager(str(repo_cache_dir(tmp_path)))
+    state_manager.update_state(str(tracked_file))
+    state_manager.state_id = "after-incremental-update"
     state = RepositoryAnalysisState(
         modules={},
         artifacts={"new.module": {"symbols": {"functions": ["run"]}}},
@@ -2609,13 +2617,11 @@ def test_incremental_live_state_persistence_roundtrips_for_restart(
     )
     engine = SimpleNamespace(
         state=state,
-        state_manager=SimpleNamespace(state_id="after-incremental-update"),
+        state_manager=state_manager,
     )
 
     persisted = update_file_module._persist_live_engine(tmp_path, engine)
 
-    from contextor.core.paths import repo_cache_dir
-
     loaded = load_engine_state(
         str(repo_cache_dir(tmp_path)),
         "after-incremental-update",
@@ -2625,6 +2631,10 @@ def test_incremental_live_state_persistence_roundtrips_for_restart(
     assert persisted is True
     assert loaded is not None
     assert loaded.artifacts == state.artifacts
+    reloaded_manager = FileStateManager(str(repo_cache_dir(tmp_path)))
+    assert reloaded_manager.state_id == "after-incremental-update"
+    assert reloaded_manager.revision == 1
+    assert reloaded_manager.has_changed(str(tracked_file)) is False
 
 
 def test_fastmcp_schema_exposes_analysis_parameters():
```
