# L32H2D1 local/full-analysis writer coordination

## FILES_CHANGED_THIS_TASK

- `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py`
- `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py`
- `C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_incremental_hydration.py`
- `C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py`
- `C:\Temp\Contextor_Repo\walkthrough.md` (report, excluded from production/test diffs).

`git status --short` shows precisely those five source/test files plus this report as modified. No other production or test file changed.

## SOURCE_CONTRACT_VERIFICATION

DIRECT_EVIDENCE: Before editing, Contextor fetched complete current `acquire_full_analysis`, `release_full_analysis`, `_execute_local_candidate_update`, `_execute_local_candidate_update_unfenced`, and `_engine_cache_transaction`; every response reported `implementation_is_complete=true`, `workspace_sync=verified`, revision 223. Exact auditor anchors matched. `acquire_full_analysis` uses nonreentrant per-repository `threading.Lock`; `release_full_analysis` unlocks its OS fd and process lock. Local helper entered cache RLock before domain OS lock; the candidate/registry/snapshot chain had no internal full-analysis acquisition. Wrapped full analysis can hold full_analysis.lock while `connect(path)` reads the LIVE domain. No additional production owner was needed for the authorized stage. Existing direct registry writers remain outside its scope.

## RED_RESULT

New focused nodes before production patch: **9 failed as expected**. Exact failures: `test_local_incremental_writer_kind_is_accepted` raised the old ValueError; `test_local_incremental_lease_precedes_cache_domain_and_spans_commit` saw cache entry before lease; timeout test reached forbidden checkpoint; three parameterized failure tests observed rollback but no lease acquisition/release; same-process and cross-process full-analysis bodies entered during paused local persistence; waiting-local test entered cache while full-analysis lease was held. RED command exited 1 after 9 failed in 16.19s. The existing LIVE-branch compatibility assertion was not part of RED because it is a preservation check.

## GREEN_RESULT

New focused nodes plus LIVE-branch check: **10 passed** in 17.05s. Full required targeted gate: complete `tests/test_mcp_incremental_hydration.py`, complete `tests/test_mcp_regressions.py`, and selected `tests/test_full_analysis_coordination.py` nodes for writer-kind validation, nonreentry, cross-process lock/process death, cancellation, timeout, and full-analysis/LIVE-mutation ordering: **166 passed, 0 failed** in 87.67s. Both runs reported only an unrelated Authlib deprecation warning. No full repository suite.

## LOCAL_INCREMENTAL_WRITER_KIND

CODE_PATH_PROVED: `acquire_full_analysis` now admits exactly `full_analysis`, `live_mutation`, `startup_publish`, `local_incremental`. No other acquisition/OS lock or metadata behavior changed. Local wrapper calls it with `owner="mcp_local_incremental"`, `writer_kind="local_incremental"`, `timeout=10.0`; focused test observes exact kwargs and coordinator test accepts the kind. Other writer kinds remain tested in the selected coordinator subset.

## FULL_ANALYSIS_LEASE_LIFETIME

CODE_PATH_PROVED: Wrapper acquires lease before calling renamed domain-fenced helper and releases it in `finally`. The renamed function's entire body is unchanged. The call includes cache RLock, domain fence, baseline, candidate construction/update, registry transaction, snapshot persistence, rollback and cache publication. The order/commit test sees lease acquired first and released only after domain/cache exit; failure parameterization sees rollback before release for persistence, update and rollback exceptions. Subsequent same-repository acquisition succeeds after failure.

## LOCK_ORDER_VERIFICATION

DIRECT_EVIDENCE from current source and focused event test: full_analysis.lock → MCP per-repository cache RLock → LIVE domain OS lock → registry checkpoint/transaction → exact snapshot publication. The nested cache RLock in `_execute_local_candidate_update_unfenced` remains reentrant. No LIVE public lease readers are called while domain OS lock is held: existing private `_read_generation` and `_read_live_lease` remain unchanged. The 10-second timeout bounds acquisition, not lease hold.

## LOCAL_VS_FULL_ANALYSIS_EXCLUSION

Isolated same-process tests prove both directions: paused local persistence prevents `run_full_analysis_exclusive` from entering its analysis body; a held full-analysis lease prevents local candidate/cache/domain entry until release. On timeout injection the public MCP response is `ERROR`, candidate update/checkpoint/snapshot are not invoked, and cache/registry/snapshot metadata remain prior state. These are test proofs under isolated repositories, not serving-process certification.

## CROSS_PROCESS_OS_LOCK_EXCLUSION

The new `spawn` process regression holds local persistence while a different process runs `run_full_analysis_exclusive`; its body cannot enter until local release. The existing strict two-MCP-process stale rejection and selected coordinator cross-process OS lock/process-death tests also pass. This proves the shared lock in the tested process boundaries, without claiming crash/power-loss atomicity.

## FULL_ANALYSIS_TIMEOUT

The wrapper specifies `timeout=10.0`. Acquisition exception occurs before entering the candidate helper and is converted by public `update_file` to `ERROR`; no success response is emitted. The selected coordinator timeout/cancellation tests pass. The timeout applies only to acquisition, not transaction duration.

## PERSISTENCE_FAILURE_LEASE_RELEASE

Isolated failure test forces persister rejection; response `ERROR`, registry rollback occurs before lease release, old cache and snapshot metadata remain, and another writer can acquire the lease. The unchanged candidate helper preserves the prior exact-revision/persistence rejection behavior.

## REGISTRY_ROLLBACK_LEASE_RELEASE

The isolated update-exception and rollback-exception cases both record `acquire → rollback → release`. When rollback raises, existing cache eviction occurs; snapshot metadata remains prior state. The outer lease release still runs in `finally`.

## LIVE_BRANCH_COMPATIBILITY

`tests/test_mcp_regressions.py::test_mcp_update_file_live_branch_delegates_without_local_persistence` now fails if the LIVE-connected path calls `acquire_full_analysis`; it passed. The public LIVE branch still invokes its client and does not take a second local_incremental lease. Public response schema is unchanged.

## L32H2A_B_C_COMPATIBILITY

The complete targeted hydration file passed, including exact-generation persistence, COW/cache publication, syntax LKG/recovery, domain fencing, rollback, active authority rejection, lock timeout, and strict two-MCP-process stale rejection. This is compatibility evidence for those test owners only; no universal registry-writer exclusion is claimed.

## TARGETED_TEST_RESULTS

- RED: 9 failed expected before production patch.
- New tests plus LIVE branch: 10 passed.
- Required GREEN gate: 166 passed, 0 failed.
- `& .\.venv\Scripts\python.exe -m py_compile` on the two production files and three test files: exit 0.
- `git diff --check` on those five files: exit 0 (only Git LF/CRLF warning).

## SOURCE_SYNC_VERIFICATION

Post-edit Contextor fetched complete `acquire_full_analysis`, wrapper, renamed domain-fenced helper and unfenced candidate; all `implementation_is_complete=true`, `workspace_sync=verified`, canonical revision 228. Call context shows public `update_file` → wrapper → renamed helper → unfenced helper; renamed helper has no unexpected direct caller. Blast radius for `acquire_full_analysis` lists `contextor.mcp.tools.update_file` as a new direct consumer alongside runtime/GUI and tests. No source preview was accepted as complete. Source indexing does not prove existing serving processes imported new code.

## LIVE_REVISION_BEFORE_AFTER

Before 223; after 228. `get_live_events(after_revision=223)` returned continuous revisions 224–228, each `desktop_watcher` `UPDATED`, respectively for the three authorized test files and two authorized production files. `resync_required=false`, activity epoch unchanged (`9e9a2a2edcb046bba00df0850244ad36`). No manual update_file, restart or full analysis.

## FULL_DIFFS

Full raw Git diff for every changed production/test file follows, without truncation:

```diff
diff --git a/contextor/core/analysis/full_analysis_coordinator.py b/contextor/core/analysis/full_analysis_coordinator.py
index a39e9df..5b43d1f 100644
--- a/contextor/core/analysis/full_analysis_coordinator.py
+++ b/contextor/core/analysis/full_analysis_coordinator.py
@@ -423,9 +423,15 @@ def acquire_full_analysis(
     Blocks if another process or thread holds the lease until released,
     timed out, or cancelled.
     """
-    if writer_kind not in {"full_analysis", "live_mutation", "startup_publish"}:
+    if writer_kind not in {
+        "full_analysis",
+        "live_mutation",
+        "startup_publish",
+        "local_incremental",
+    }:
         raise ValueError(
-            "writer_kind must be 'full_analysis', 'live_mutation', or 'startup_publish'"
+            "writer_kind must be 'full_analysis', 'live_mutation', "
+            "'startup_publish', or 'local_incremental'"
         )
 
     lock_file, key, repo_id = _resolve_lock_path(repo_path)
diff --git a/contextor/mcp/tools/update_file.py b/contextor/mcp/tools/update_file.py
index acf5ab0..ee7a3dc 100644
--- a/contextor/mcp/tools/update_file.py
+++ b/contextor/mcp/tools/update_file.py
@@ -250,6 +250,31 @@ def _assert_local_committed_baseline(root: Path, engine, root_key: str) -> None:
 
 def _execute_local_candidate_update(
     root: Path, target_file: Path, engine
+):
+    """Coordinate local updates with repository canonical writers."""
+    from contextor.core.analysis.full_analysis_coordinator import (
+        acquire_full_analysis,
+        release_full_analysis,
+    )
+
+    lease = acquire_full_analysis(
+        root,
+        owner="mcp_local_incremental",
+        writer_kind="local_incremental",
+        timeout=10.0,
+    )
+    try:
+        return _execute_local_candidate_update_with_domain_fence(
+            root,
+            target_file,
+            engine,
+        )
+    finally:
+        release_full_analysis(lease)
+
+
+def _execute_local_candidate_update_with_domain_fence(
+    root: Path, target_file: Path, engine
 ):
     """Fence LIVE authority before executing a local candidate transaction."""
     from contextor.core.live_state.runtime import _production_domain
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index f0ad176..5aa1566 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -67,6 +67,21 @@ def test_startup_publish_writer_kind_is_accepted(tmp_path: Path):
         acquire_full_analysis(repo, writer_kind="invalid")
 
 
+def test_local_incremental_writer_kind_is_accepted(tmp_path: Path):
+    repo = tmp_path / "local_incremental"
+    repo.mkdir()
+    lease = acquire_full_analysis(
+        repo,
+        owner="mcp_local_incremental",
+        writer_kind="local_incremental",
+        timeout=1.0,
+    )
+    try:
+        assert lease.owner == "mcp_local_incremental"
+    finally:
+        release_full_analysis(lease)
+
+
 def test_live_mutation_admission_trace_fields_are_correlated_and_whitelisted(
     tmp_path: Path,
 ):
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index 6cf9952..96671e6 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -8,11 +8,13 @@ from pathlib import Path
 import pytest
 import threading
 import multiprocessing
+from contextlib import contextmanager
 from dataclasses import replace
 from types import SimpleNamespace
 
 from contextor import mcp_server
 from contextor.core.analysis.incremental import engine as incremental_engine_module
+from contextor.core.analysis import full_analysis_coordinator as coordinator
 from contextor.mcp import report_helpers
 from contextor.mcp import runtime as mcp_runtime
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
@@ -153,6 +155,345 @@ def _cross_process_local_candidate_worker(
         })
 
 
+def _cross_process_full_writer_worker(repo_text, ready, entered, release, results):
+    def body(_root, **_kwargs):
+        entered.set()
+        if not release.wait(10):
+            raise TimeoutError("full-analysis body hold expired")
+
+    ready.set()
+    try:
+        coordinator.run_full_analysis_exclusive(
+            repo_text, owner="test_full_writer", analysis_fn=body, timeout=10.0
+        )
+        results.put("completed")
+    except BaseException as exc:
+        results.put(repr(exc))
+
+
+def test_local_incremental_lease_precedes_cache_domain_and_spans_commit(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    events = []
+    real_acquire = coordinator.acquire_full_analysis
+    real_release = coordinator.release_full_analysis
+    real_cache = mcp_runtime._engine_cache_transaction
+    real_domain = RuntimeLeaseManager._lock
+    real_checkpoint = engine.registry.create_checkpoint
+    real_update = IncrementalAnalysisEngine.update_file
+    real_persist = update_file_module._persist_live_engine
+
+    def acquire(*args, **kwargs):
+        assert kwargs == {
+            "owner": "mcp_local_incremental",
+            "writer_kind": "local_incremental",
+            "timeout": 10.0,
+        }
+        lease = real_acquire(*args, **kwargs)
+        events.append("lease_acquired")
+        return lease
+
+    def release(lease):
+        assert mcp_runtime._live_engines[str(repo.resolve())] is not engine
+        events.append("lease_released")
+        return real_release(lease)
+
+    @contextmanager
+    def cache(root):
+        events.append("cache_enter")
+        with real_cache(root) as key:
+            yield key
+        events.append("cache_exit")
+
+    @contextmanager
+    def domain(self):
+        events.append("domain_enter")
+        with real_domain(self):
+            yield
+        events.append("domain_exit")
+
+    def checkpoint():
+        events.append("checkpoint")
+        return real_checkpoint()
+
+    def update(self, path):
+        events.append("update")
+        return real_update(self, path)
+
+    def persist(root, candidate):
+        events.append("persist")
+        return real_persist(root, candidate)
+
+    monkeypatch.setattr(coordinator, "acquire_full_analysis", acquire)
+    monkeypatch.setattr(coordinator, "release_full_analysis", release)
+    monkeypatch.setattr(mcp_runtime, "_engine_cache_transaction", cache)
+    monkeypatch.setattr(RuntimeLeaseManager, "_lock", domain)
+    monkeypatch.setattr(engine.registry, "create_checkpoint", checkpoint)
+    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", update)
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist)
+
+    result, candidate, _, persisted = update_file_module._execute_local_candidate_update(
+        repo, provider, engine
+    )
+
+    assert result.status == "UPDATED" and persisted is True
+    assert candidate is mcp_runtime._live_engines[str(repo.resolve())]
+    assert events[0:3] == ["lease_acquired", "cache_enter", "domain_enter"]
+    assert events.index("checkpoint") < events.index("update") < events.index("persist")
+    assert events[-3:] == ["domain_exit", "cache_exit", "lease_released"]
+
+
+def test_local_incremental_timeout_does_not_start_candidate(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
+    before_registry = engine.registry.create_checkpoint()
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    observed = []
+
+    def reject(*args, **kwargs):
+        observed.append(kwargs)
+        raise coordinator.FullAnalysisBusyError("full-analysis lease busy")
+
+    def forbidden(*_args, **_kwargs):
+        pytest.fail("candidate, registry, or snapshot started after lease rejection")
+
+    monkeypatch.setattr(coordinator, "acquire_full_analysis", reject)
+    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", forbidden)
+    monkeypatch.setattr(engine.registry, "create_checkpoint", forbidden)
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", forbidden)
+    response = _local_update(repo, provider)
+
+    assert observed == [{
+        "owner": "mcp_local_incremental",
+        "writer_kind": "local_incremental",
+        "timeout": 10.0,
+    }]
+    assert response["status"] == "ERROR"
+    assert "busy" in response["error"]
+    assert mcp_runtime._live_engines[str(repo.resolve())] is engine
+    assert engine.registry._state == before_registry
+    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta
+
+
+@pytest.mark.parametrize("failure", ["persistence", "update", "rollback"])
+def test_local_incremental_lease_released_after_candidate_failure(
+    tmp_path, monkeypatch, failure
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    before_meta = (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes()
+    before_registry = engine.registry.create_checkpoint()
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    events = []
+    real_acquire = coordinator.acquire_full_analysis
+    real_release = coordinator.release_full_analysis
+    real_restore = engine.registry.restore_checkpoint
+
+    def acquire(*args, **kwargs):
+        lease = real_acquire(*args, **kwargs)
+        events.append("acquire")
+        return lease
+
+    def release(lease):
+        events.append("release")
+        return real_release(lease)
+
+    def restore(checkpoint):
+        events.append("rollback")
+        if failure == "rollback":
+            raise RuntimeError("forced rollback failure")
+        return real_restore(checkpoint)
+
+    monkeypatch.setattr(coordinator, "acquire_full_analysis", acquire)
+    monkeypatch.setattr(coordinator, "release_full_analysis", release)
+    monkeypatch.setattr(engine.registry, "restore_checkpoint", restore)
+    if failure in {"persistence", "rollback"}:
+        monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_: False)
+    else:
+        def fail_update(*_args):
+            raise RuntimeError("forced update failure")
+        monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", fail_update)
+
+    response = _local_update(repo, provider)
+
+    assert response["status"] == "ERROR"
+    assert events == ["acquire", "rollback", "release"]
+    assert (repo_cache_dir(repo) / "engine_state.meta.json").read_bytes() == before_meta
+    if failure == "rollback":
+        assert str(repo.resolve()) not in mcp_runtime._live_engines
+    else:
+        assert mcp_runtime._live_engines[str(repo.resolve())] is engine
+        assert engine.registry._state == before_registry
+    subsequent = real_acquire(repo, owner="after_failure", timeout=1.0)
+    real_release(subsequent)
+
+
+def test_local_incremental_blocks_wrapped_full_analysis_through_persistence(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    real_persist = update_file_module._persist_live_engine
+    entered = threading.Event()
+    release = threading.Event()
+    full_body = threading.Event()
+    results = {}
+
+    def persist(root, candidate):
+        entered.set()
+        assert release.wait(10)
+        return real_persist(root, candidate)
+
+    def full_analysis():
+        try:
+            coordinator.run_full_analysis_exclusive(
+                repo,
+                analysis_fn=lambda *_args, **_kwargs: full_body.set(),
+                timeout=5.0,
+            )
+            results["full"] = "completed"
+        except BaseException as exc:
+            results["full"] = repr(exc)
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist)
+    local = threading.Thread(target=lambda: results.setdefault("local", _local_update(repo, provider)))
+    full = threading.Thread(target=full_analysis)
+    try:
+        local.start()
+        assert entered.wait(10)
+        full.start()
+        assert not full_body.wait(0.25)
+    finally:
+        release.set()
+        local.join(10)
+        full.join(10)
+
+    assert not local.is_alive() and not full.is_alive()
+    assert results["local"]["status"] == "UPDATED"
+    assert results["full"] == "completed" and full_body.is_set()
+
+
+def test_local_wait_for_full_analysis_holds_neither_cache_nor_domain(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    held = coordinator.acquire_full_analysis(repo, owner="holder", timeout=1.0)
+    cache_entered = threading.Event()
+    domain_entered = threading.Event()
+    update_entered = threading.Event()
+    real_cache = mcp_runtime._engine_cache_transaction
+    real_domain = RuntimeLeaseManager._lock
+    real_update = IncrementalAnalysisEngine.update_file
+    results = {}
+
+    @contextmanager
+    def cache(root):
+        cache_entered.set()
+        with real_cache(root) as key:
+            yield key
+
+    @contextmanager
+    def domain(self):
+        domain_entered.set()
+        with real_domain(self):
+            yield
+
+    def update(self, path):
+        update_entered.set()
+        return real_update(self, path)
+
+    monkeypatch.setattr(mcp_runtime, "_engine_cache_transaction", cache)
+    monkeypatch.setattr(RuntimeLeaseManager, "_lock", domain)
+    monkeypatch.setattr(IncrementalAnalysisEngine, "update_file", update)
+    local = threading.Thread(
+        target=lambda: results.setdefault(
+            "local", update_file_module._execute_local_candidate_update(repo, provider, engine)
+        )
+    )
+    try:
+        local.start()
+        assert not cache_entered.wait(0.3)
+        assert not domain_entered.is_set()
+        assert not update_entered.is_set()
+    finally:
+        coordinator.release_full_analysis(held)
+        local.join(10)
+
+    assert not local.is_alive()
+    assert results["local"][0].status == "UPDATED"
+    assert cache_entered.is_set() and domain_entered.is_set() and update_entered.is_set()
+
+
+def test_full_analysis_os_lock_excludes_other_process_during_local_persistence(
+    tmp_path, monkeypatch
+):
+    repo, provider, engine = _build_local_fallback_engine(
+        tmp_path, monkeypatch, "def run():\n    return 1\n"
+    )
+    assert update_file_module._persist_live_engine(repo, engine) is True
+    provider.write_text("def run():\n    return 2\n", encoding="utf-8")
+    entered = threading.Event()
+    release_local = threading.Event()
+    real_persist = update_file_module._persist_live_engine
+    results = {}
+
+    def persist(root, candidate):
+        entered.set()
+        assert release_local.wait(10)
+        return real_persist(root, candidate)
+
+    monkeypatch.setattr(update_file_module, "_persist_live_engine", persist)
+    ctx = multiprocessing.get_context("spawn")
+    ready = ctx.Event()
+    full_body = ctx.Event()
+    release_full = ctx.Event()
+    full_results = ctx.Queue()
+    full = ctx.Process(
+        target=_cross_process_full_writer_worker,
+        args=(str(repo), ready, full_body, release_full, full_results),
+    )
+    local = threading.Thread(target=lambda: results.setdefault("local", _local_update(repo, provider)))
+    try:
+        local.start()
+        assert entered.wait(10)
+        full.start()
+        assert ready.wait(15)
+        assert not full_body.wait(0.3)
+    finally:
+        release_local.set()
+        local.join(10)
+        release_full.set()
+        if full.pid is not None:
+            full.join(15)
+        if full.is_alive():
+            full.terminate()
+            full.join(5)
+
+    assert not local.is_alive() and full.exitcode == 0
+    assert results["local"]["status"] == "UPDATED"
+    assert full_body.is_set()
+    assert full_results.get(timeout=5) == "completed"
+
+
 @pytest.mark.parametrize("prior_generation", ["never_acquired", "released"])
 def test_local_writer_accepts_only_clean_absence_states(
     tmp_path, monkeypatch, prior_generation
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index 1b4969b..e47921e 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -2903,6 +2903,10 @@ def test_mcp_update_file_live_branch_delegates_without_local_persistence(
         "_persist_live_engine",
         lambda *_args: pytest.fail("LIVE path called the local persister"),
     )
+    monkeypatch.setattr(
+        "contextor.core.analysis.full_analysis_coordinator.acquire_full_analysis",
+        lambda *_args, **_kwargs: pytest.fail("LIVE path acquired local writer lease"),
+    )
     monkeypatch.setattr(
         update_file_module, "_mcp_runtime_restart_required", lambda _path: False
     )
```

## REMAINING_GLOBAL_WRITER_BYPASSES

This stage coordinates local fallback with writers using `full_analysis.lock`. Existing registry-only `read_registries` write transaction, direct `analyze_layer` and `analyze_single_file` registry writes, and unwrapped direct `analyze_project` calls remain outside this proof. Long local transactions may delay queued LIVE mutation/full analysis. No crash or power-loss atomicity claim.

## RESTART_REQUIRED

YES for serving-process certification: the MCP server must reload `contextor.mcp.tools.update_file` and `full_analysis_coordinator`; any LIVE/Desktop process that imports the changed coordinator needs an applicable manual reload. No process was restarted here. The passing fresh-process pytest gate and workspace_sync evidence do not certify imported code in already-running services.

## FINAL_VERDICT

**TARGETED_CODE_PASS; RUNTIME_RELOAD_UNVERIFIED.** The exact two-file production patch and focused regressions satisfy this stage's tested lock-order/exclusion contract. Await `proceduj`; do not expand to global registry writers without separate auditor authorization.

