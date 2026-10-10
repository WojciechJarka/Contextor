# L32H2B_LOCAL_CANDIDATE_BEFORE_CACHE_PUBLICATION

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py — private candidate transaction helper and local fallback call site.
- C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py — real-engine isolation, failure, success, LKG and serialization regressions.
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py — preexisting fake-engine fixtures changed to real engine/manager/registry fixtures while retaining response, status, persister invocation and LIVE delegation assertions.
- C:\Temp\Contextor_Repo\walkthrough.md — this report only; excluded from source/test diff accounting.
- No other source, test or documentation files were edited.

## SOURCE_CONTRACT_VERIFICATION

DIRECT_EVIDENCE: Contextor MCP, before edits, returned complete current implementations of `update_file`, `_persist_live_engine`, `_engine_cache_transaction`, `IncrementalAnalysisEngine.__init__`, `RepositoryAnalysisState.clone_for_update`, `FileStateManager.update_state`, and `PersistentIdentityRegistry.create_checkpoint`/`restore_checkpoint`. Each resolved symbol reported complete AST implementation, canonical revision 207, `canonical_state=fresh`, `workspace_sync=verified`, `provenance=live`. The L32H2A persister used one exact-revision snapshot with generation FileState payload. `mcp_runtime._live_engines` is the engine cache. Its per-root lock is `threading.RLock`, so the helper can call the exact persister while retaining the same lock. Registry checkpoint/restore reject calls inside an active registry transaction; the candidate helper uses them outside such a transaction.

Contextor call context and blast radius located the public `update_file` call site and static consumers. After edits, the helper has one direct caller (`update_file` at line 391) and one direct callee (`_persist_live_engine` at line 238). Public `update_file` has five confirmed direct static consumers, including `contextor.mcp_server` and test modules; its module has six inbound dependency entries, including the MCP server and the two changed test modules. These are static facts, not a claim about all dynamic Python uses. No source-contract mismatch was found.

## RED_RESULT

Before production edits, `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_incremental_hydration.py -k local_candidate` returned **8 failed, 1 passed, 16 deselected**. Failures showed successful `UPDATED` responses after rejected persistence, in-place cache/fact mutation, no candidate replacement, no registry rollback or disk-ahead eviction, and two local update/persist phases interleaving. The passing real-engine COW probe showed that constructing and updating a detached candidate did not mutate the inspected original nested provider facts or tracked-file mapping. This was the required pre-implementation isolation gate.

## GREEN_RESULT

The first focused run after the production edit returned **8 passed, 1 failed**. The failure was a test assumption that a first mtime-only reconciliation must be `UNCHANGED`; the existing regression allows `UPDATED` or `UNCHANGED`, followed by a parsed semantic no-op. The test was aligned with that existing contract and then passed. The first complete two-file run exposed **17 failing cases caused by obsolete fake-engine fixtures** in `tests/test_mcp_regressions.py`; the revised real-engine fixtures passed as a focused 17-case selection. A further real-engine precommit persister-exception test was added and passed.

Final authorized gate: `.venv\Scripts\python.exe -m pytest -q tests/test_mcp_incremental_hydration.py tests/test_mcp_regressions.py tests/test_persistent_registry.py::test_checkpoint_restore_persists_exact_registry_state tests/test_live_state_store.py::test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock tests/test_live_state_store.py::test_exact_snapshot_revision_rules_and_disk_ahead_without_overwrite tests/test_live_state_store.py::test_exact_snapshot_rejects_file_state_payload_mismatches tests/test_live_state_store.py::test_exact_snapshot_revision_binds_embedded_state_and_metadata tests/test_live_state_store.py::test_referenced_filestate_generation_fail_closed_without_legacy_fallback tests/test_live_state_store.py::test_referenced_filestate_without_meta_fails_closed tests/test_live_state_store.py::test_legacy_filestate_without_meta_loads_entries_but_remains_unverified` returned **142 passed, 0 failed, 1 external Authlib deprecation warning** in 43.05 seconds. No full repository suite was run.

Read-only `compile(...)` succeeded for all three changed Python files. Scoped `git diff --check` exited 0; only LF/CRLF working-copy conversion notices appeared. Worktree status listed only the three authorized source/test files and `walkthrough.md`.

## CANDIDATE_ISOLATION_MATRIX

| Contract | Evidence | Result |
| --- | --- | --- |
| Cached engine not passed to local incremental update | Real-engine success test records candidate identity at persister; helper constructs a new `IncrementalAnalysisEngine`. | PROVED in focused test and code path. |
| Different state holder | `clone_for_update()` and explicit identity rejection; real COW and success tests assert separate state. | PROVED. |
| Nested fact-bearing original values preserved on rejected update | Real candidate COW probe checks provider module/artifact object identity and deep content; rejected update checks original modules/artifacts. | PROVED for tested source changes. |
| Original manager RAM mapping preserved | Candidate manager receives `dict(original._state)`; rejection and COW tests check mapping identity/content. | PROVED. |
| Original revision/cache revision preserved on precommit rejection | False, metadata-failure, engine-error and persister-exception tests check revision 1 and prior cache engine. | PROVED for tested failures. |
| Registry mappings restored on rejected precommit update | Real new-module false-persist test compares complete registry checkpoint; selected registry checkpoint test passes. | PROVED for tested transaction. |
| No unrelated module COW mutation | Existing focused incremental/hydration regressions pass; the real candidate probe preserves a provider module while updating a candidate. | Bounded test evidence, not a global proof for every nested object. |

## FILESTATE_RAM_ISOLATION

The helper uses `copy.copy(manager)` and then a new outer `_state` dict; it carries the original cache directory, file path, identity, revision and baseline status in the copied object. It does not call `FileStateManager.save` or reload older disk tracking into the candidate. The real COW and rejected-persistence tests assert the original mapping object and content remain unchanged. L32H2A exact generation remains the only local snapshot/FileState publication path.

## REGISTRY_CHECKPOINT_AND_ROLLBACK

The same real registry object is supplied to the candidate engine. Its checkpoint is captured before candidate construction/update. On a rejected precommit result, metadata is reread first, then `restore_checkpoint` runs outside any registry transaction. A real new-module rejected candidate restored the checkpoint mapping. A forced `restore_checkpoint` exception evicted engine and revision cache entries and returned a distinct rollback ERROR; the test did not claim clean rollback. The selected existing registry checkpoint persistence test passed.

## PRECOMMIT_FAILURE_ATOMICITY

| Failure | Expected public/cache/disk outcome | Evidence |
| --- | --- | --- |
| `_persist_live_engine` returns False | `ERROR`, explicit `live_state_persisted=false`; original cached engine/state/manager/revision and prior metadata pointer retained; registry restored. | Real engine/registry test passed. |
| Exact metadata `os.replace` fails | `ERROR`; original cache, revision 1 snapshot pointer and registry checkpoint retained. | Real snapshot failure injection passed. |
| Persister raises before commit | `ERROR` with original exception; original cache, FileState RAM, revision, pointer and registry retained. | Real engine/registry injection passed. |
| Engine raises after candidate-side update/publication | `ERROR`; original cached engine and snapshot retained, registry restored. | Real candidate-side injection passed. |
| Registry restore raises | Distinct rollback ERROR; engine/revision cache evicted; no candidate publication. | Focused injection passed. |

These are precommit process-level checks. Crash atomicity is outside this gate.

## DISK_AHEAD_FAIL_CLOSED

The helper captures metadata identity/revision and pointer existence before candidate work. On any failure it rereads metadata before registry restoration. If the pointer changed, it evicts cache engine/revision/provenance and raises an explicit possible disk/cache divergence ERROR; it does not restore an older registry checkpoint. A focused test committed exact revision 2 and then simulated a false persister result; it proved the no-restore branch, cache eviction, revision-2 metadata and ERROR response. This does not certify exclusion of another LIVE writer.

## CACHE_PUBLICATION_ORDER

A real UPDATED test observed the original cached engine both immediately before and immediately after successful exact-generation persister return. Only then did the helper replace `_live_engines[root_key]` with the candidate. The resulting engine had a different state object and manager mapping; original facts stayed unchanged; snapshot metadata and cache revision both became 2. On success, engine/state/cache provenance are set to `snapshot` per the existing local hydration vocabulary. The public wrapper uses the returned candidate engine for post-update semantic diff and response shaping.

## LOCAL_REQUEST_SERIALIZATION

The per-root `RLock` is held from ownership check through candidate construction, incremental update, persistence, rollback if needed and cache replacement. In a two-thread real local update test, the first persister was paused before snapshot write; the second request did not enter engine update during that interval. Both requests then completed as UPDATED and exact metadata reached revision 3. The same test failed RED on the old branch because the second update entered while the first persistence was paused.

## L32H1_STATUS_COMPATIBILITY

The complete local fallback test retains every returned-status persister invocation: UPDATED, DELETED, SYNTAX_ERROR, RECOVERED, parsed UNCHANGED, early UNCHANGED and structured ERROR. Its 14 synthetic-result persisted/not-persisted dispatch cases now use real engine/manager/registry candidate construction with a stubbed persister. For the stubbed persisted cases, the original status and response fields remain; for a rejected candidate, the response is ERROR with `live_state_persisted=false`, never an uncommitted successful status. Real syntax/LKG/recovery and both UNCHANGED modes passed with candidate engine replacement after persistence.

## L32H2A_GENERATION_COMPATIBILITY

The unchanged `_persist_live_engine` still performs one exact-revision `save_engine_state` with generation FileState payload. All new and existing exact-generation, failure-pointer, hydration, stale-revision, legacy-migration, syntax/recovery and FileState integrity regressions in the selected gate passed. No independent manager save or second snapshot transaction was introduced.

## LIVE_BRANCH_COMPATIBILITY

The LIVE-connected branch of public `update_file` was not edited. Existing `test_mcp_update_file_live_branch_delegates_without_local_persistence` passed in the complete two-file gate, retaining remote delegation and no local persister call. No LIVE IPC or Desktop watcher production owner was modified.

## SOURCE_SYNC_VERIFICATION

After edits, Contextor MCP returned complete AST implementations for `_execute_local_candidate_update` (lines 186-271), public `update_file` (355-466) and unchanged `_persist_live_engine` (74-179), each with `implementation_is_complete=true`, `no_partial_symbol_source=true`, `canonical_state=fresh`, `workspace_sync=verified`, canonical revision 213. The final added test was separately fetched complete at revision 214 with `workspace_sync=verified`. The current source/test worktree has only the three authorized files plus this report modified. Source indexing confirms workspace identity; it does not attest that the already-running MCP serving process reimported the edited Python module.

## LIVE_REVISION_BEFORE_AFTER

Before edits: revision 207, activity epoch `9e9a2a2edcb046bba00df0850244ad36`, `resync_required=false`. After edits: revision 214 in the same epoch. `get_live_events(after_revision=207)` returned continuous events 208-213; the subsequent call with `after_revision=213` returned event 214. Both reported `resync_required=false`. These `desktop_watcher` events cover the two changed test files and the production owner. No manual `update_file`, process restart or full analysis was performed.

## REMAINING_RISKS

Authority-transition exclusion is not part of L32H2B. This gate also does not establish power-loss durability or crash recovery if process termination occurs after registry writes but before snapshot pointer publication. COW isolation evidence covers the exercised provider/new-module paths and current targeted regressions, not every possible nested object graph. Existing MCP process import reload remains unverified.

## RESTART_REQUIRED

Yes: `contextor\mcp\tools\update_file.py` is imported MCP runtime code. A manual MCP serving-process reload followed by runtime identity verification is required for serving-process certification. No MCP, LIVE or Desktop restart was performed.

## FINAL_VERDICT

**L32H2B_TARGETED_CODE_GATE_PASS; MCP_RUNTIME_RELOAD_PENDING.** The authorized candidate-before-cache transaction, rollback/error behavior, exact-generation compatibility and targeted tests pass. No authority-transition or crash-atomicity certification is claimed.

## FULL_DIFFS

The following are full, unabridged source/test diffs for every changed production or test file. `walkthrough.md` is excluded from source/test diff accounting.
### contextor/mcp/tools/update_file.py

```diff
diff --git a/contextor/mcp/tools/update_file.py b/contextor/mcp/tools/update_file.py
index a26645f..8703e41 100644
--- a/contextor/mcp/tools/update_file.py
+++ b/contextor/mcp/tools/update_file.py
@@ -1,5 +1,6 @@
 import hashlib
 import json
+import copy
 from pathlib import Path
 
 from contextor.mcp import query_helpers
@@ -178,6 +179,98 @@ def _persist_live_engine(root: Path, engine) -> bool:
         return True
 
 
+class _LocalCandidatePersistenceRejected(RuntimeError):
+    """The local candidate was discarded because its snapshot was not committed."""
+
+
+def _execute_local_candidate_update(root: Path, target_file: Path, engine):
+    """Commit a local update candidate before replacing the cached engine."""
+    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+    from contextor.core.live_state import read_metadata
+    from contextor.core.paths import repo_cache_dir
+
+    with mcp_runtime._engine_cache_transaction(root) as root_key:
+        if mcp_runtime._live_engines.get(root_key) is not engine:
+            raise RuntimeError("Local cached engine ownership changed.")
+
+        rel_path = target_file.relative_to(root)
+        module_path = ".".join(rel_path.with_suffix("").parts)
+        old_artifacts = engine.state.artifacts.get(module_path, {})
+
+        state = getattr(engine, "state", None)
+        if not callable(getattr(state, "clone_for_update", None)):
+            raise RuntimeError("Local canonical state cannot be cloned for update.")
+        manager = getattr(engine, "state_manager", None)
+        if manager is None or not isinstance(getattr(manager, "_state", None), dict):
+            raise RuntimeError("Local FileStateManager has no tracked-file mapping.")
+        registry = getattr(engine, "registry", None)
+        if (
+            registry is None
+            or not callable(getattr(registry, "create_checkpoint", None))
+            or not callable(getattr(registry, "restore_checkpoint", None))
+        ):
+            raise RuntimeError("Local identity registry has no checkpoint capability.")
+
+        cache_dir = repo_cache_dir(root)
+        metadata_path = cache_dir / "engine_state.meta.json"
+        previous_metadata = read_metadata(cache_dir)
+        previous_metadata_exists = metadata_path.exists()
+
+        candidate_state = state.clone_for_update()
+        if candidate_state is state:
+            raise RuntimeError("Local update candidate shares the canonical state holder.")
+        candidate_manager = copy.copy(manager)
+        candidate_manager._state = dict(manager._state)
+        checkpoint = registry.create_checkpoint()
+
+        try:
+            candidate_engine = IncrementalAnalysisEngine(
+                candidate_state,
+                registry,
+                candidate_manager,
+                str(root),
+            )
+            for name in ("revision", "provenance"):
+                if hasattr(engine, name):
+                    setattr(candidate_engine, name, getattr(engine, name))
+
+            res = candidate_engine.update_file(str(target_file))
+            persisted = _persist_live_engine(root, candidate_engine)
+            if not persisted:
+                raise _LocalCandidatePersistenceRejected(
+                    "Local candidate snapshot persistence failed."
+                )
+        except Exception as failure:
+            current_metadata = read_metadata(cache_dir)
+            if (
+                current_metadata != previous_metadata
+                or metadata_path.exists() != previous_metadata_exists
+            ):
+                mcp_runtime._live_engines.pop(root_key, None)
+                mcp_runtime._live_engine_revisions.pop(root_key, None)
+                mcp_runtime._live_engine_provenance.pop(root_key, None)
+                raise RuntimeError(
+                    "Local snapshot metadata changed during a rejected candidate; "
+                    "possible disk/cache divergence."
+                ) from failure
+            try:
+                registry.restore_checkpoint(checkpoint)
+            except Exception as rollback_failure:
+                mcp_runtime._live_engines.pop(root_key, None)
+                mcp_runtime._live_engine_revisions.pop(root_key, None)
+                mcp_runtime._live_engine_provenance.pop(root_key, None)
+                raise RuntimeError(
+                    "Local registry rollback failed after a rejected candidate."
+                ) from rollback_failure
+            raise
+
+        mcp_runtime._live_engines[root_key] = candidate_engine
+        candidate_engine.provenance = "snapshot"
+        candidate_engine.state.provenance = "snapshot"
+        mcp_runtime._live_engine_provenance[root_key] = "snapshot"
+        return res, candidate_engine, old_artifacts, True
+
+
 def _semantic_artifact_diff(old_artifacts: dict, new_artifacts: dict) -> dict:
     """Return a compact, JSON-safe semantic delta from cached symbol facts."""
     old_symbols = old_artifacts.get("symbols", {}) if old_artifacts else {}
@@ -294,10 +387,12 @@ def update_file(
                 engine = mcp_runtime.get_or_init_engine(root)
             live_state_persisted = True
         else:
-            res = engine.update_file(str(target_file))
-            live_state_persisted = _persist_live_engine(
-                root,
-                engine,
+            res, engine, old_artifacts, live_state_persisted = (
+                _execute_local_candidate_update(
+                    root,
+                    target_file,
+                    engine,
+                )
             )
         new_artifacts = engine.state.artifacts.get(module_path, {})
         semantic_diff = _semantic_artifact_diff(old_artifacts, new_artifacts)
@@ -365,4 +460,7 @@ def update_file(
             result = {field: result[field] for field in fields}
         return json.dumps(result, indent=2)
     except Exception as e:
-        return json.dumps({"status": "ERROR", "file_path": str(target_file), "error": str(e)}, indent=2)
+        error_result = {"status": "ERROR", "file_path": str(target_file), "error": str(e)}
+        if isinstance(e, _LocalCandidatePersistenceRejected):
+            error_result["live_state_persisted"] = False
+        return json.dumps(error_result, indent=2)
```

### tests/test_mcp_incremental_hydration.py

```diff
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index fe37c79..b98f902 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -1,8 +1,9 @@
 """End-to-end MCP test for incremental state persistence and live context hydration."""
 
 import json
-from copy import deepcopy
+from copy import copy, deepcopy
 import os
+from pathlib import Path
 
 import pytest
 import threading
@@ -91,6 +92,384 @@ def _rehydrate_local_engine(repo):
     return mcp_runtime.get_or_init_engine(repo.resolve())
 
 
+def test_local_candidate_cow_keeps_original_nested_facts_and_tracked_files(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    original_state = engine.state
+    original_artifacts = original_state.artifacts["provider"]
+    original_module = original_state.modules["provider"]
+    artifact_content = deepcopy(original_artifacts)
+    original_tracked = engine.state_manager._state
+    tracked_content = deepcopy(original_tracked)
+    checkpoint = engine.registry.create_checkpoint()
+
+    candidate_state = original_state.clone_for_update()
+    candidate_manager = copy(engine.state_manager)
+    candidate_manager._state = dict(original_tracked)
+    candidate = IncrementalAnalysisEngine(
+        candidate_state, engine.registry, candidate_manager, str(repo)
+    )
+    assert candidate.state is not original_state
+    assert candidate.state_manager._state is not original_tracked
+
+    provider.write_text(
+        "def run():\n    return 1\n\ndef added():\n    return 2\n",
+        encoding="utf-8",
+    )
+    try:
+        assert candidate.update_file(str(provider)).status == "UPDATED"
+        assert original_state.modules["provider"] is original_module
+        assert original_state.artifacts["provider"] is original_artifacts
+        assert original_state.artifacts["provider"] == artifact_content
+        assert engine.state_manager._state is original_tracked
+        assert engine.state_manager._state == tracked_content
+    finally:
+        engine.registry.restore_checkpoint(checkpoint)
+
+
+def test_local_candidate_rejected_persistence_preserves_cache_state_manager_and_registry(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    key = str(repo.resolve())
+    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
+    before_modules = dict(engine.state.modules)
+    before_artifacts = deepcopy(engine.state.artifacts)
+    provider_module = engine.state.modules["provider"]
+    provider_artifacts = engine.state.artifacts["provider"]
+    before_tracked = engine.state_manager._state
+    before_tracked_content = deepcopy(before_tracked)
+    before_registry = engine.registry.create_checkpoint()
+
+    extra = repo / "extra.py"
+    extra.write_text("def added():\n    return 2\n", encoding="utf-8")
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: False)
+    response = _local_update(repo, extra)
+
+    assert response["status"] == "ERROR"
+    assert response["live_state_persisted"] is False
+    assert mcp_runtime._live_engines[key] is engine
+    assert engine.state.modules == before_modules
+    assert engine.state.modules["provider"] is provider_module
+    assert engine.state.artifacts == before_artifacts
+    assert engine.state.artifacts["provider"] is provider_artifacts
+    assert engine.state_manager._state is before_tracked
+    assert engine.state_manager._state == before_tracked_content
+    assert engine.revision == engine.state.revision == 1
+    assert mcp_runtime._live_engine_revisions[key] == 1
+    assert engine.registry._state == before_registry
+    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta
+    assert str(provider) in engine.state_manager.tracked_paths()
+
+
+def test_local_candidate_metadata_commit_failure_keeps_prior_cache_and_snapshot(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    key = str(repo.resolve())
+    cache_dir = repo_cache_dir(repo)
+    before_meta = (cache_dir / "engine_state.meta.json").read_bytes()
+    before_artifacts = deepcopy(engine.state.artifacts)
+    before_registry = engine.registry.create_checkpoint()
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    original_replace = snapshot_store.os.replace
+
+    def failing_replace(source, target):
+        if target.name == "engine_state.meta.json":
+            raise OSError("injected metadata commit failure")
+        return original_replace(source, target)
+
+    monkeypatch.setattr(snapshot_store.os, "replace", failing_replace)
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "ERROR"
+    assert mcp_runtime._live_engines[key] is engine
+    assert engine.state.artifacts == before_artifacts
+    assert engine.state_manager.revision == engine.state.revision == 1
+    assert engine.registry._state == before_registry
+    assert (cache_dir / "engine_state.meta.json").read_bytes() == before_meta
+    assert read_metadata(cache_dir).revision == 1
+
+
+def test_local_candidate_persister_exception_before_commit_restores_registry(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    key = str(repo.resolve())
+    cache_dir = repo_cache_dir(repo)
+    before_meta = (cache_dir / "engine_state.meta.json").read_bytes()
+    before_artifacts = deepcopy(engine.state.artifacts)
+    before_tracked = deepcopy(engine.state_manager._state)
+    before_registry = engine.registry.create_checkpoint()
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+
+    def fail_persist(*_args):
+        raise OSError("injected precommit persistence exception")
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", fail_persist)
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "ERROR"
+    assert "precommit persistence exception" in response["error"]
+    assert mcp_runtime._live_engines[key] is engine
+    assert engine.state.artifacts == before_artifacts
+    assert engine.state_manager._state == before_tracked
+    assert engine.registry._state == before_registry
+    assert engine.state.revision == mcp_runtime._live_engine_revisions[key] == 1
+    assert (cache_dir / "engine_state.meta.json").read_bytes() == before_meta
+
+
+def test_local_candidate_engine_error_after_candidate_publication_preserves_prior_cache(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    key = str(repo.resolve())
+    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
+    before_artifacts = deepcopy(engine.state.artifacts)
+    before_registry = engine.registry.create_checkpoint()
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    real_update = IncrementalAnalysisEngine.update_file
+
+    def update_then_raise(self, file_path):
+        result = real_update(self, file_path)
+        assert result.status == "UPDATED"
+        raise RuntimeError("injected post-publication engine failure")
+
+    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", update_then_raise)
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "ERROR"
+    assert "post-publication engine failure" in response["error"]
+    assert mcp_runtime._live_engines[key] is engine
+    assert engine.state.artifacts == before_artifacts
+    assert engine.state_manager.revision == engine.state.revision == 1
+    assert engine.registry._state == before_registry
+    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta
+
+
+def test_local_candidate_updated_installs_only_after_exact_persistence(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    key = str(repo.resolve())
+    original_artifacts = deepcopy(engine.state.artifacts)
+    provider.write_text(
+        "def run():\n    return 1\n\ndef added():\n    return 2\n", encoding="utf-8"
+    )
+    real_persist = update_file_module._persist_live_engine
+    seen = []
+
+    def assert_before_publish(root, candidate):
+        seen.append((mcp_runtime._live_engines[key] is engine, candidate is not engine))
+        persisted = real_persist(root, candidate)
+        seen.append((mcp_runtime._live_engines[key] is engine, candidate is not engine))
+        return persisted
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", assert_before_publish)
+    response = _local_update(repo, provider)
+    published = mcp_runtime._live_engines[key]
+
+    assert response["status"] == "UPDATED"
+    assert response["live_state_persisted"] is True
+    assert seen == [(True, True), (True, True)]
+    assert published is not engine
+    assert published.state is not engine.state
+    assert published.state_manager._state is not engine.state_manager._state
+    assert engine.state.artifacts == original_artifacts
+    assert published.state.artifacts != original_artifacts
+    assert read_metadata(repo_cache_dir(repo)).revision == 2
+    assert published.revision == mcp_runtime._live_engine_revisions[key] == 2
+
+
+def test_local_candidate_syntax_lkg_recovery_and_unchanged_publish_after_persist(
+    tmp_path, monkeypatch
+):
+    repo, provider, original = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, original) is True
+    key = str(repo.resolve())
+    original_module = original.state.modules["provider"]
+    real_persist = update_file_module._persist_live_engine
+    calls = []
+
+    def assert_before_publish(root, candidate):
+        calls.append((mcp_runtime._live_engines[key], candidate))
+        return real_persist(root, candidate)
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", assert_before_publish)
+    early = _local_update(repo, provider)
+    assert early["status"] == "UNCHANGED"
+    assert early["live_state_persisted"] is True
+    assert calls[-1][0] is original
+    early_engine = mcp_runtime._live_engines[key]
+    assert early_engine is not original
+
+    stat = provider.stat()
+    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
+    reconciled = _local_update(repo, provider)
+    assert reconciled["status"] in {"UPDATED", "UNCHANGED"}
+    assert reconciled["live_state_persisted"] is True
+    reconciled_engine = mcp_runtime._live_engines[key]
+    assert reconciled_engine is not early_engine
+    assert calls[-1][0] is early_engine
+
+    stat = provider.stat()
+    os.utime(provider, (stat.st_atime, stat.st_mtime + 2))
+    parsed = _local_update(repo, provider)
+    assert parsed["status"] == "UNCHANGED"
+    assert parsed["live_state_persisted"] is True
+    parsed_engine = mcp_runtime._live_engines[key]
+    assert parsed_engine is not reconciled_engine
+    assert calls[-1][0] is reconciled_engine
+
+    provider.write_text("def run(:\n    return 1\n", encoding="utf-8")
+    syntax = _local_update(repo, provider)
+    assert syntax["status"] == "SYNTAX_ERROR"
+    assert syntax["live_state_persisted"] is True
+    stale_engine = mcp_runtime._live_engines[key]
+    assert stale_engine is not parsed_engine
+    assert calls[-1][0] is parsed_engine
+    assert stale_engine.state.modules["provider"] is original_module
+    assert stale_engine.state.module_parse_freshness["provider"]["state"] == "stale"
+    assert "provider" not in original.state.module_parse_freshness
+
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    recovered = _local_update(repo, provider)
+    assert recovered["status"] == "RECOVERED"
+    assert recovered["live_state_persisted"] is True
+    fresh_engine = mcp_runtime._live_engines[key]
+    assert fresh_engine is not stale_engine
+    assert calls[-1][0] is stale_engine
+    assert "provider" not in fresh_engine.state.module_parse_freshness
+    assert stale_engine.state.module_parse_freshness["provider"]["state"] == "stale"
+    assert read_metadata(repo_cache_dir(repo)).revision == 6
+
+
+def test_local_candidate_rollback_failure_evicts_cache(tmp_path, monkeypatch):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    key = str(repo.resolve())
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: False)
+
+    def failed_restore(_checkpoint):
+        raise OSError("injected registry rollback failure")
+
+    monkeypatch.setattr(engine.registry, "restore_checkpoint", failed_restore)
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "ERROR"
+    assert "rollback" in response["error"].lower()
+    assert key not in mcp_runtime._live_engines
+    assert key not in mcp_runtime._live_engine_revisions
+    assert read_metadata(repo_cache_dir(repo)).revision == 1
+
+
+def test_local_candidate_disk_ahead_does_not_restore_older_registry(tmp_path, monkeypatch):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    key = str(repo.resolve())
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    real_persist = update_file_module._persist_live_engine
+    restore_calls = []
+
+    def commit_then_report_failure(root, candidate):
+        assert real_persist(root, candidate) is True
+        return False
+
+    def record_restore(checkpoint):
+        restore_calls.append(checkpoint)
+        raise AssertionError("older registry checkpoint must not be restored")
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", commit_then_report_failure)
+    monkeypatch.setattr(engine.registry, "restore_checkpoint", record_restore)
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "ERROR"
+    assert "divergence" in response["error"].lower()
+    assert restore_calls == []
+    assert key not in mcp_runtime._live_engines
+    assert key not in mcp_runtime._live_engine_revisions
+    assert read_metadata(repo_cache_dir(repo)).revision == 2
+
+
+def test_local_candidate_serializes_update_through_persistence(tmp_path, monkeypatch):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    extra = repo / "extra.py"
+    extra.write_text("value = 3\n", encoding="utf-8")
+    real_update = IncrementalAnalysisEngine.update_file
+    real_persist = update_file_module._persist_live_engine
+    persist_entered = threading.Event()
+    release_persist = threading.Event()
+    second_update_entered = threading.Event()
+    results = {}
+    calls = []
+
+    def observe_update(self, path):
+        if Path(path).name == "extra.py":
+            second_update_entered.set()
+        return real_update(self, path)
+
+    def block_first_persistence(root, candidate):
+        calls.append(candidate)
+        if len(calls) == 1:
+            persist_entered.set()
+            assert release_persist.wait(10)
+        return real_persist(root, candidate)
+
+    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", observe_update)
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", block_first_persistence)
+    first = threading.Thread(
+        target=lambda: results.setdefault("first", _local_update(repo, provider)), daemon=True
+    )
+    second = threading.Thread(
+        target=lambda: results.setdefault("second", _local_update(repo, extra)), daemon=True
+    )
+    try:
+        first.start()
+        assert persist_entered.wait(10)
+        second.start()
+        assert second_update_entered.wait(0.3) is False
+    finally:
+        release_persist.set()
+        first.join(10)
+        second.join(10)
+
+    assert not first.is_alive() and not second.is_alive()
+    assert results["first"]["status"] == "UPDATED"
+    assert results["second"]["status"] == "UPDATED"
+    assert second_update_entered.is_set()
+    assert len(calls) == 2
+    assert read_metadata(repo_cache_dir(repo)).revision == 3
+
+
 def test_local_exact_generation_initial_successor_and_filestate_hydration(
     tmp_path, monkeypatch
 ):
```

### tests/test_mcp_regressions.py

```diff
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 19eca67..f93e3bf 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -2647,12 +2647,42 @@ def test_fastmcp_schema_exposes_analysis_parameters():
     assert "exclude_paths" in signature.parameters
     assert "job_id" in status_signature.parameters
     assert "public_api_only" in extraction_signature.parameters
-def test_update_file_marks_running_mcp_server_as_requiring_restart(monkeypatch):
-    server_path = Path(mcp_server.__file__).resolve()
-    repo = server_path.parents[1]
-    engine = SimpleNamespace(
-        state=SimpleNamespace(artifacts={"contextor.mcp_server": {}}),
-        update_file=lambda file_path: SimpleNamespace(
+def _real_local_update_fixture(root, monkeypatch):
+    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.paths import repo_cache_dir
+
+    root = root.resolve()
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(root / "cache"))
+    state = RepositoryAnalysisState(
+        modules={},
+        artifacts={},
+        dependency_graph=None,
+        trie={},
+        package_root=None,
+        artifact_consumption={},
+    )
+    registry = PersistentIdentityRegistry(str(root))
+    manager = FileStateManager(str(repo_cache_dir(root)))
+    engine = IncrementalAnalysisEngine(state, registry, manager, str(root))
+    monkeypatch.setattr(mcp_runtime, "_live_engines", {str(root): engine})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_revisions", {})
+    monkeypatch.setattr(mcp_runtime, "_live_engine_provenance", {})
+    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
+    return engine
+
+
+def test_update_file_marks_running_mcp_server_as_requiring_restart(tmp_path, monkeypatch):
+    repo = tmp_path.resolve()
+    server_path = repo / "mcp_server.py"
+    server_path.write_text("value = 1\n", encoding="utf-8")
+    _real_local_update_fixture(repo, monkeypatch)
+    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+
+    monkeypatch.setattr(
+        IncrementalAnalysisEngine,
+        "update_file",
+        lambda self, file_path: SimpleNamespace(
             status="UPDATED",
             file_path=file_path,
             graph_state="fresh",
@@ -2665,7 +2695,6 @@ def test_update_file_marks_running_mcp_server_as_requiring_restart(monkeypatch):
             delta=None,
         ),
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
     monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: True)
     monkeypatch.setattr(
         update_file_module,
@@ -2697,9 +2726,13 @@ def test_update_file_marks_running_mcp_server_as_requiring_restart(monkeypatch):
 def test_mcp_update_file_shapes_affected_modules_compact_full_and_fields(tmp_path, monkeypatch):
     target = tmp_path / "provider.py"
     target.write_text("def run(): pass\n", encoding="utf-8")
-    engine = SimpleNamespace(
-        state=SimpleNamespace(artifacts={"provider": {}}),
-        update_file=lambda file_path: SimpleNamespace(
+    _real_local_update_fixture(tmp_path, monkeypatch)
+    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+
+    monkeypatch.setattr(
+        IncrementalAnalysisEngine,
+        "update_file",
+        lambda self, file_path: SimpleNamespace(
             status="UPDATED",
             file_path=file_path,
             graph_state="fresh",
@@ -2712,7 +2745,6 @@ def test_mcp_update_file_shapes_affected_modules_compact_full_and_fields(tmp_pat
             delta=None,
         ),
     )
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
     monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: True)
 
     compact = json.loads(
@@ -2763,6 +2795,8 @@ def test_mcp_update_file_shapes_affected_modules_compact_full_and_fields(tmp_pat
 def test_mcp_update_file_local_fallback_persists_every_returned_status(
     tmp_path, monkeypatch, result_status, path_kind, persisted
 ):
+    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+
     root = tmp_path.resolve()
     target = root / "provider.py"
     target.write_text("def run():\n    return 1\n", encoding="utf-8")
@@ -2783,14 +2817,12 @@ def test_mcp_update_file_local_fallback_persists_every_returned_status(
         delta=None,
     )
 
-    class FakeEngine:
-        state = SimpleNamespace(artifacts={"provider": {}})
-
-        def update_file(self, file_path):
-            update_calls.append(file_path)
-            return result
+    engine = _real_local_update_fixture(root, monkeypatch)
 
-    engine = FakeEngine()
+    def candidate_update(self, file_path):
+        assert self is not engine
+        update_calls.append(file_path)
+        return result
 
     def connect(_root):
         connect_calls.append(_root)
@@ -2801,7 +2833,7 @@ def test_mcp_update_file_local_fallback_persists_every_returned_status(
         return persisted
 
     monkeypatch.setattr("contextor.core.live_state.connect", connect)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", candidate_update)
     monkeypatch.setattr(update_file_module, "_persist_live_engine", persist)
     monkeypatch.setattr(
         update_file_module, "_mcp_runtime_restart_required", lambda _path: False
@@ -2815,9 +2847,15 @@ def test_mcp_update_file_local_fallback_persists_every_returned_status(
     assert connect_calls
     assert all(call_root == root for call_root in connect_calls)
     assert update_calls == [str(target)]
-    assert persist_calls == [(root, engine)]
-    assert response["status"] == result_status
+    assert len(persist_calls) == 1
+    assert persist_calls[0][0] == root
+    assert persist_calls[0][1] is not engine
+    assert response["status"] == (result_status if persisted else "ERROR")
     assert response["live_state_persisted"] is persisted
+    if persisted:
+        assert mcp_runtime._live_engines[str(root)] is persist_calls[0][1]
+    else:
+        assert mcp_runtime._live_engines[str(root)] is engine
 
 
 def test_mcp_update_file_live_branch_delegates_without_local_persistence(
@@ -2880,6 +2918,8 @@ def test_mcp_update_file_live_branch_delegates_without_local_persistence(
 def test_mcp_update_file_local_persistence_exception_keeps_error_response(
     tmp_path, monkeypatch
 ):
+    from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+
     root = tmp_path.resolve()
     target = root / "provider.py"
     target.write_text("def run():\n    return 1\n", encoding="utf-8")
@@ -2895,16 +2935,14 @@ def test_mcp_update_file_local_persistence_exception_keeps_error_response(
         affected_modules=[],
         delta=None,
     )
-    engine = SimpleNamespace(
-        state=SimpleNamespace(artifacts={"provider": {}}),
-        update_file=lambda _path: result,
-    )
+    engine = _real_local_update_fixture(root, monkeypatch)
 
     def fail_persist(*_args):
         raise OSError("snapshot persistence failed")
 
-    monkeypatch.setattr("contextor.core.live_state.connect", lambda _root: None)
-    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+    monkeypatch.setattr(
+        IncrementalAnalysisEngine, "update_file", lambda self, _path: result
+    )
     monkeypatch.setattr(update_file_module, "_persist_live_engine", fail_persist)
 
     response = json.loads(
@@ -2914,6 +2952,7 @@ def test_mcp_update_file_local_persistence_exception_keeps_error_response(
     assert response["status"] == "ERROR"
     assert "snapshot persistence failed" in response["error"]
     assert "live_state_persisted" not in response
+    assert mcp_runtime._live_engines[str(root)] is engine
```
