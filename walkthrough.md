# L32H2G1 — startup backfill canonical writer gate

## FILES_CHANGED_THIS_TASK
- C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only; excluded from source/test diff)

## SOURCE_PREFLIGHT
DIRECT_EVIDENCE: Contextor MCP get_source_range returned complete runtime.py lines 1412–1560 and 1715–1820 with the exact auditor anchors. get_file_edit_context and blast radius identified tests.test_live_state_ipc and tests.test_live_authority_bootstrap as direct static test consumers. Canonical state was fresh, workspace_sync=verified, revision=287, resync_required=false. The source/test worktree was initially clean; only walkthrough.md had the previous task report. Pre-edit report named both planned changed files and the exact gate.

## RED_RESULTS
DIRECT_EVIDENCE: After valid fixture setup and before production patch, seven new targeted test cases failed (0 passed, 89 deselected). Most direct RED: test_startup_backfill_fails_fast_behind_cross_process_writer reached CanonicalLiveServer while a spawned competing process held the actual full_analysis OS lease; expected FullAnalysisBusyError was absent. The lease-scope test recorded zero canonical lease acquisitions. The four injected-failure variants also recorded zero backfill lease acquisitions. The recheck scenario initially failed on the test fixture's missing versioned FileState payload; fixture was corrected before GREEN, so this run does not independently prove a RED recheck assertion. The first RED attempt failed during fixture setup due incomplete re-export facts; fixture was corrected before the meaningful RED run.

## BACKFILL_WRITER_ADMISSION
CODE_PATH_PROVED: runtime.run_service preserves the initial module_usages_require_materialization check and existing timing measurement. Only when needed it acquires full_analysis with owner=live_startup_module_usages_backfill, writer_kind=full_analysis, timeout=0.0. Lease covers reload, recheck, existing ensure_module_usages, FileState payload build, and exact snapshot save. finally releases it. No additional runtime authority acquisition.

## FAIL_FAST_BOOTSTRAP_POLICY
CONTRACT_PROVED: timeout=0.0 was preserved literally. Spawn-based cross-process test used ready/release Event barriers; startup failed before materialization or server construction, metadata revision stayed unchanged, and no delayed write appeared after competing lease release. Runtime bootstrap exception/finally cleanup was exercised.

## RELOAD_AFTER_ADMISSION
CODE_PATH_PROVED: load_snapshot is repeated under the canonical lease, with expected repo_id/root_path. None raises the specified RuntimeError. The reloaded state and loaded tuple replace stale pre-admission variables before materialization and server construction. The targeted recheck fixture committed a newer, already materialized generation between initial load and admission; server saw that state/revision and no ensure or backfill save occurred.

## NO_BACKFILL_FAST_PATH
The second healthy startup in the lease-scope test acquired no backfill full-analysis lease and made no new snapshot generation. Existing startup hydration and timing branch remained in place.

## ACTUAL_CROSS_PROCESS_EXCLUSION
A spawned Windows process acquired full_analysis.lock using acquire_full_analysis and signaled an Event. The parent started LIVE bootstrap while the lock was held. Parent admission failed promptly (asserted less than 5 seconds); ensure_module_usages was not called, CanonicalLiveServer was not reached, metadata revision and endpoint remained unchanged. Barrier release, child join, zero exit code and unchanged revision after release were asserted. This is actual OS exclusion evidence in an isolated fixture, not a serving-process certification.

## FILESTATE_REVISION_PARITY
The preexisting parity regression test passed. Existing body retains FileStateManager.build_payload(state_id, target_revision), exact_revision=target_revision, writer name and timing fields without duplication. Snapshot exact revision and FileState mismatch regressions passed.

## FAILURE_RELEASE
Parameterized tests injected exceptions from second load_snapshot, ensure_module_usages, FileStateManager.build_payload and save_snapshot. All four passed. They asserted one canonical lease acquire/release, unchanged durable revision, absent endpoint and immediate ability to reacquire full_analysis.lock.

## RUNTIME_AUTHORITY_CLEANUP
Bootstrap failure tests and runtime failure/finally source confirmed authority cleanup remains in the outer finally. Cross-process contention and four injected-failure tests assert no endpoint publication. Existing authority bootstrap/restart/reconciliation tests passed. No service restart was performed.

## TARGETED_GREEN_RESULTS
- Complete C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py: 96 passed, 1 unrelated AuthlibDeprecationWarning, 75.38 s.
- Seven selected direct startup/authority/snapshot/lease regressions: 7 passed, 23.70 s.
- py_compile for both changed Python files: PASS.
- git diff --check for both changed files: PASS.
- No full repository pytest suite was run.

## SOURCE_SYNC
Post-edit Contextor get_source_range returned the full changed backfill block through server construction. Blast radius reported workspace_sync=verified, canonical_state=fresh, canonical_revision=292, cycles.count=0. This certifies indexed source identity, not imported-code reload.

## LIVE_REVISION_BEFORE_AFTER
Before: 287, continuity=continuous, resync_required=false. After: 292, continuity=continuous, resync_required=false. get_live_events(after_revision=287) returned desktop_watcher update_file events 288–292 for the changed test and runtime files, including runtime.py at revision 291. The watcher activity included intermediate test edits. No manual update_file was called.

## RESTART_REQUIRED
YES for serving Contextor MCP/LIVE processes that import runtime.py. No process was restarted, and these test results do not certify existing serving processes reloaded the implementation.

## FINAL_VERDICT
TARGETED_PASS_FOR_L32H2G1_SOURCE_AND_TESTS. No L32H FINAL PASS or serving-process certification claimed. Await auditor command proceduj.

## FULL_DIFFS_FOR_ALL_CHANGED_FILES

```diff
diff --git a/contextor/core/live_state/runtime.py b/contextor/core/live_state/runtime.py
index 9cb2c40..4952fe4 100644
--- a/contextor/core/live_state/runtime.py
+++ b/contextor/core/live_state/runtime.py
@@ -1465,51 +1465,83 @@ def run_service(
             )
 
             if materialization_required:
-                loaded_metadata = loaded[1]
-                step_started = time.monotonic()
-                from contextor.core.analysis.state_manager import FileStateManager
-                startup_timings_ms["file_state_manager_import_ms"] = round(
-                    (time.monotonic() - step_started) * 1000.0,
-                    3,
+                from contextor.core.analysis.full_analysis_lease import (
+                    acquire_full_analysis,
+                    release_full_analysis,
                 )
 
-                step_started = time.monotonic()
-                file_state_manager = FileStateManager(str(cache))
-                startup_timings_ms["file_state_manager_load_ms"] = round(
-                    (time.monotonic() - step_started) * 1000.0,
-                    3,
-                )
-                step_started = time.monotonic()
-                ensure_module_usages(state)
-                startup_timings_ms["ensure_module_usages_ms"] = round(
-                    (time.monotonic() - step_started) * 1000.0,
-                    3,
-                )
-                target_revision = loaded_metadata.revision + 1
-                step_started = time.monotonic()
-                file_state_payload = file_state_manager.build_payload(
-                    loaded_metadata.state_id,
-                    target_revision,
-                )
-                startup_timings_ms["file_state_build_payload_ms"] = round(
-                    (time.monotonic() - step_started) * 1000.0,
-                    3,
-                )
-                step_started = time.monotonic()
-                save_snapshot(
-                    state,
-                    cache,
-                    loaded_metadata.state_id,
-                    writer="live-service-symbol-calls-backfill",
-                    repo_id=identity.repo_id,
-                    root_path=identity.root_path,
-                    exact_revision=target_revision,
-                    file_state_payload=file_state_payload,
-                )
-                startup_timings_ms["backfill_save_snapshot_ms"] = round(
-                    (time.monotonic() - step_started) * 1000.0,
-                    3,
+                backfill_lease = acquire_full_analysis(
+                    root,
+                    owner="live_startup_module_usages_backfill",
+                    writer_kind="full_analysis",
+                    timeout=0.0,
                 )
+                try:
+                    reloaded = load_snapshot(
+                        cache,
+                        expected_repo_id=identity.repo_id,
+                        expected_root_path=identity.root_path,
+                    )
+                    if reloaded is None:
+                        raise RuntimeError(
+                            "Canonical snapshot disappeared during "
+                            "LIVE startup backfill admission."
+                        )
+
+                    loaded = reloaded
+                    state = loaded[0]
+                    materialization_required = (
+                        module_usages_require_materialization(state)
+                    )
+
+                    if materialization_required:
+                        loaded_metadata = loaded[1]
+                        step_started = time.monotonic()
+                        from contextor.core.analysis.state_manager import FileStateManager
+                        startup_timings_ms["file_state_manager_import_ms"] = round(
+                            (time.monotonic() - step_started) * 1000.0,
+                            3,
+                        )
+
+                        step_started = time.monotonic()
+                        file_state_manager = FileStateManager(str(cache))
+                        startup_timings_ms["file_state_manager_load_ms"] = round(
+                            (time.monotonic() - step_started) * 1000.0,
+                            3,
+                        )
+                        step_started = time.monotonic()
+                        ensure_module_usages(state)
+                        startup_timings_ms["ensure_module_usages_ms"] = round(
+                            (time.monotonic() - step_started) * 1000.0,
+                            3,
+                        )
+                        target_revision = loaded_metadata.revision + 1
+                        step_started = time.monotonic()
+                        file_state_payload = file_state_manager.build_payload(
+                            loaded_metadata.state_id,
+                            target_revision,
+                        )
+                        startup_timings_ms["file_state_build_payload_ms"] = round(
+                            (time.monotonic() - step_started) * 1000.0,
+                            3,
+                        )
+                        step_started = time.monotonic()
+                        save_snapshot(
+                            state,
+                            cache,
+                            loaded_metadata.state_id,
+                            writer="live-service-symbol-calls-backfill",
+                            repo_id=identity.repo_id,
+                            root_path=identity.root_path,
+                            exact_revision=target_revision,
+                            file_state_payload=file_state_payload,
+                        )
+                        startup_timings_ms["backfill_save_snapshot_ms"] = round(
+                            (time.monotonic() - step_started) * 1000.0,
+                            3,
+                        )
+                finally:
+                    release_full_analysis(backfill_lease)
         step_started = time.monotonic()
         startup_metadata = read_metadata(cache)
         startup_timings_ms["read_metadata_ms"] = round(
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 6e5dcab..ee0aa92 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -5,6 +5,7 @@ import sys
 import threading
 import time
 import multiprocessing.connection as mpc
+import multiprocessing
 from pathlib import Path
 from types import SimpleNamespace
 
@@ -41,6 +42,86 @@ def _poll_until_reconciled(watcher, expected, timeout=10.0):
 pytestmark = pytest.mark.live
 
 
+def _hold_full_analysis_lease_for_startup(repo_path, ready, release):
+    from contextor.core.analysis.full_analysis_lease import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+
+    lease = acquire_full_analysis(
+        repo_path, owner="startup-backfill-competing-writer", timeout=5.0
+    )
+    try:
+        ready.set()
+        if not release.wait(10.0):
+            raise RuntimeError("startup backfill test release barrier timed out")
+    finally:
+        release_full_analysis(lease)
+
+
+def _startup_backfill_case(tmp_path, monkeypatch):
+    from contextor.core.analysis.state_manager import RepositoryAnalysisState
+    from contextor.core.domain.module import Module
+    from contextor.core.live_state.store import save_snapshot
+    from contextor.core.repository_identity import ensure_repository_identity
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    identity = ensure_repository_identity(repo)[0]
+    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
+    monkeypatch.setenv("CONTEXTOR_STATE_DIR", str(tmp_path / "state"))
+    cache = repo_cache_dir(repo)
+    state = RepositoryAnalysisState(
+        modules={
+            "a.py": Module(
+                module_id="a.py",
+                path="a.py",
+                absolute_path=str(repo / "a.py"),
+                imports=[],
+            )
+        },
+        reexport_facts_by_module={
+            "a.py": {
+                "exporter": "a.py",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            }
+        },
+    )
+    state.revision = 1
+    metadata = save_snapshot(
+        state, cache, "sid",
+        repo_id=identity.repo_id, root_path=identity.root_path,
+    )
+    return repo, cache, identity, metadata
+
+
+def _ready_then_stop_startup_server(monkeypatch, runtime, captured):
+    class StubServer:
+        def __init__(self, state, revision, **_kwargs):
+            captured["state"] = state
+            captured["revision"] = revision
+            self.endpoint = SimpleNamespace(host="127.0.0.1", port=1, authkey_hex="00")
+            self._stop = threading.Event()
+            self.activity_epoch = "startup-backfill-gate"
+
+        def serve_forever(self):
+            if not self._stop.wait(5.0):
+                raise RuntimeError("startup backfill test server did not stop")
+
+        def record_authority_event(self, event):
+            if event.get("event_type") == "RUNTIME_AUTHORITY_READY":
+                self._stop.set()
+            return {"accepted": True, "duplicate": False, "activity_epoch": self.activity_epoch}
+
+        def close(self, **_kwargs):
+            self._stop.set()
+            return True
+
+    monkeypatch.setattr(runtime, "CanonicalLiveServer", StubServer)
+
+
 def _diagnostic_state(*, syntax=None, collisions=None, cycles=None, freshness="fresh"):
     return SimpleNamespace(
         revision=0,
@@ -1296,6 +1377,215 @@ def test_persistence_trace_operation_is_propagated_across_successful_real_update
     assert FileStateManager(str(cache)).revision == expected
 
 
+def test_startup_backfill_fails_fast_behind_cross_process_writer(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    import contextor.core.analysis.incremental.materialization as materialization
+    from contextor.core.analysis.full_analysis_lease import FullAnalysisBusyError
+    from contextor.core.live_state.store import read_metadata
+
+    repo, cache, _identity, metadata = _startup_backfill_case(tmp_path, monkeypatch)
+    context = multiprocessing.get_context("spawn")
+    ready = context.Event()
+    release = context.Event()
+    owner = context.Process(
+        target=_hold_full_analysis_lease_for_startup,
+        args=(str(repo), ready, release),
+    )
+    owner.start()
+    try:
+        assert ready.wait(8.0), "competing writer did not acquire OS lease"
+        calls = []
+        monkeypatch.setattr(
+            materialization, "ensure_module_usages",
+            lambda _state: calls.append("materialize"),
+        )
+        monkeypatch.setattr(
+            runtime, "CanonicalLiveServer",
+            lambda *_args, **_kwargs: pytest.fail("server started despite writer contention"),
+        )
+        started = time.monotonic()
+        with pytest.raises(FullAnalysisBusyError):
+            runtime.run_service(repo)
+        assert time.monotonic() - started < 5.0
+        assert calls == []
+        assert read_metadata(cache).revision == metadata.revision
+        assert not endpoint_file(repo).exists()
+    finally:
+        release.set()
+        owner.join(8.0)
+        if owner.is_alive():
+            owner.terminate()
+            owner.join(5.0)
+    assert owner.exitcode == 0
+    assert read_metadata(cache).revision == metadata.revision
+
+
+def test_startup_backfill_reloads_newer_materialized_generation(tmp_path, monkeypatch):
+    import copy
+    import contextor.core.live_state.runtime as runtime
+    import contextor.core.analysis.incremental.materialization as materialization
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.live_state.store import load_snapshot, read_metadata, save_snapshot
+
+    repo, cache, identity, metadata = _startup_backfill_case(tmp_path, monkeypatch)
+    original_load = runtime.load_snapshot
+    calls = {"loads": 0, "ensure": 0}
+    newer = {}
+
+    def load_with_intervening_commit(*args, **kwargs):
+        calls["loads"] += 1
+        result = original_load(*args, **kwargs)
+        if calls["loads"] == 1:
+            committed_state = copy.deepcopy(result[0])
+            committed_state.module_usages = {
+                "a.py": SimpleNamespace(
+                    symbol_calls_materialized=True,
+                    reference_evidence_materialized=True,
+                )
+            }
+            newer["metadata"] = save_snapshot(
+                committed_state, cache, metadata.state_id,
+                writer="intervening-canonical-writer",
+                repo_id=identity.repo_id,
+                root_path=identity.root_path,
+                exact_revision=metadata.revision + 1,
+                file_state_payload=FileStateManager(str(cache)).build_payload(
+                    metadata.state_id, metadata.revision + 1
+                ),
+            )
+        return result
+
+    monkeypatch.setattr(runtime, "load_snapshot", load_with_intervening_commit)
+    monkeypatch.setattr(
+        materialization, "ensure_module_usages",
+        lambda _state: calls.__setitem__("ensure", calls["ensure"] + 1),
+    )
+    captured = {}
+    _ready_then_stop_startup_server(monkeypatch, runtime, captured)
+    runtime.run_service(repo)
+
+    assert calls == {"loads": 2, "ensure": 0}
+    assert read_metadata(cache).revision == newer["metadata"].revision
+    assert captured["revision"] == newer["metadata"].revision
+    assert captured["state"].module_usages["a.py"].symbol_calls_materialized
+    assert load_snapshot(cache, "sid")[1].state_id == newer["metadata"].state_id
+
+
+def test_startup_backfill_lease_scope_and_healthy_fast_path(tmp_path, monkeypatch):
+    import contextor.core.live_state.runtime as runtime
+    import contextor.core.analysis.incremental.materialization as materialization
+    import contextor.core.analysis.full_analysis_lease as lease_module
+    from contextor.core.live_state.store import read_metadata
+
+    repo, cache, _identity, metadata = _startup_backfill_case(tmp_path, monkeypatch)
+    acquired = []
+    released = []
+    original_acquire = lease_module.acquire_full_analysis
+    original_release = lease_module.release_full_analysis
+
+    def acquire(*args, **kwargs):
+        assert kwargs["timeout"] == 0.0
+        acquired.append(kwargs)
+        return original_acquire(*args, **kwargs)
+
+    def release(lease):
+        released.append(lease)
+        return original_release(lease)
+
+    monkeypatch.setattr(lease_module, "acquire_full_analysis", acquire)
+    monkeypatch.setattr(lease_module, "release_full_analysis", release)
+    def ensure_under_lease(state):
+        assert len(acquired) == 1 and len(released) == 0
+        state.module_usages = {
+            "a.py": SimpleNamespace(
+                symbol_calls_materialized=True,
+                reference_evidence_materialized=True,
+            )
+        }
+
+    monkeypatch.setattr(materialization, "ensure_module_usages", ensure_under_lease)
+    captured = {}
+    _ready_then_stop_startup_server(monkeypatch, runtime, captured)
+    runtime.run_service(repo)
+    assert len(acquired) == len(released) == 1
+    assert acquired[0]["owner"] == "live_startup_module_usages_backfill"
+    assert read_metadata(cache).revision == metadata.revision + 1
+    assert captured["revision"] == metadata.revision + 1
+
+    acquired.clear()
+    released.clear()
+    captured.clear()
+    runtime.run_service(repo)
+    assert acquired == released == []
+    assert read_metadata(cache).revision == metadata.revision + 1
+    assert captured["revision"] == metadata.revision + 1
+
+
+@pytest.mark.parametrize("failure_site", ["reload", "ensure", "payload", "save"])
+def test_startup_backfill_failure_releases_writer_and_runtime_authority(
+    tmp_path, monkeypatch, failure_site
+):
+    import contextor.core.live_state.runtime as runtime
+    import contextor.core.analysis.incremental.materialization as materialization
+    import contextor.core.analysis.full_analysis_lease as lease_module
+    from contextor.core.analysis.state_manager import FileStateManager
+    from contextor.core.live_state.store import read_metadata
+
+    repo, cache, _identity, metadata = _startup_backfill_case(tmp_path, monkeypatch)
+    acquired = []
+    released = []
+    original_acquire = lease_module.acquire_full_analysis
+    original_release = lease_module.release_full_analysis
+    monkeypatch.setattr(
+        runtime, "CanonicalLiveServer",
+        lambda *_args, **_kwargs: pytest.fail("server started despite injected backfill failure"),
+    )
+
+    def acquire(*args, **kwargs):
+        acquired.append(original_acquire(*args, **kwargs))
+        return acquired[-1]
+
+    def release(lease):
+        released.append(lease)
+        return original_release(lease)
+
+    monkeypatch.setattr(lease_module, "acquire_full_analysis", acquire)
+    monkeypatch.setattr(lease_module, "release_full_analysis", release)
+    if failure_site == "reload":
+        original_load = runtime.load_snapshot
+        loads = [0]
+
+        def fail_reload(*args, **kwargs):
+            loads[0] += 1
+            if loads[0] == 2:
+                raise RuntimeError("injected reload failure")
+            return original_load(*args, **kwargs)
+
+        monkeypatch.setattr(runtime, "load_snapshot", fail_reload)
+    elif failure_site == "ensure":
+        monkeypatch.setattr(
+            materialization, "ensure_module_usages",
+            lambda _state: (_ for _ in ()).throw(RuntimeError("injected ensure failure")),
+        )
+    elif failure_site == "payload":
+        monkeypatch.setattr(
+            FileStateManager, "build_payload",
+            lambda *_args: (_ for _ in ()).throw(RuntimeError("injected payload failure")),
+        )
+    else:
+        monkeypatch.setattr(
+            runtime, "save_snapshot",
+            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("injected save failure")),
+        )
+    with pytest.raises(RuntimeError, match=f"injected {failure_site} failure"):
+        runtime.run_service(repo)
+    assert len(acquired) == len(released) == 1
+    assert read_metadata(cache).revision == metadata.revision
+    assert not endpoint_file(repo).exists()
+    lease = original_acquire(repo, owner="after-startup-failure", timeout=0.0)
+    original_release(lease)
+
+
 def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_path, monkeypatch):
     import contextor.core.live_state.runtime as runtime
     from contextor.core.analysis.state_manager import FileState, FileStateManager, RepositoryAnalysisState
```
